from __future__ import annotations

from scripts.scenario.holy_sword_049 import migrate as holy_sword

import json
import random
import unittest
from copy import deepcopy
from unittest.mock import patch

from host import combat, maps, shops, state
from scripts.balance import liese
from scripts.balance.checkpoints import DEFAULT_SCENARIO, fresh_session
from scripts.scenario.oaksdawn import CLUES, DESCRIPTIONS, UNDEAD, apply
from tests.test_map_layout import edge_node_collisions

from scripts.scenario.spring_postgame import apply as apply_spring_postgame


class OaksdawnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(DEFAULT_SCENARIO)

    def session(self, location="cave_hot_spring"):
        session = fresh_session(deepcopy(self.pack), "hero")
        state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)
        self.assertEqual(state.current_location_id(session), location)
        return session

    def resolve(self, session, identifier, roll=None):
        action = state.resolve_action(session, action_id=identifier)
        self.assertIsNotNone(action, identifier)
        self.assertTrue(state.action_requirement_status(action, session)[0], identifier)
        return state.apply_action_result(session, action, roll or {})

    def choices(self, session):
        return state.player_choices_for_session(state.fallback_choices_for_session(session), session)

    def give(self, session, identifier, quantity=1):
        item = next(i for i in self.pack["items"] if i["id"] == identifier)
        state.apply_state_delta(session, {"inventory_add": [{**item, "quantity": quantity}]})

    def test_waterway_roundtrip_and_gate_greeting_once(self):
        session = self.session()
        self.assertEqual(next(c for c in self.choices(session) if c.get("action_id") == "follow_hot_spring_water")["preview"], "")
        for action, destination in [("follow_hot_spring_water", "cave_waterway"), ("waterway_to_spring", "cave_hot_spring"),
                                    ("follow_hot_spring_water", "cave_waterway"), ("waterway_to_gate", "oaksdawn_water_gate"),
                                    ("open_oaksdawn_gate", "oaksdawn_square"), ("square_to_water_gate", "oaksdawn_water_gate")]:
            self.resolve(session, action)
            self.assertEqual(state.current_location_id(session), destination)
            self.assertFalse(combat.ensure_combat_started(session))
        self.assertEqual([c["text"] for c in self.choices(session)], ["城塞へ入る", "水路へ戻る"])
        first = next(a for l in self.pack["locations"] for a in l.get("actions", []) if a["id"] == "open_oaksdawn_gate")
        self.assertFalse(state.action_requirement_status(first, session)[0])
        self.assertEqual(maps.movement_action(session, "G1")["id"], "enter_oaksdawn")
        self.resolve(session, "enter_oaksdawn")
        self.resolve(session, "square_to_water_gate")
        self.resolve(session, "gate_back")
        self.assertEqual(state.current_location_id(session), "cave_waterway")

    def test_hq_letter_chain_and_new_clues_count(self):
        session = self.session("oaksdawn_hq")
        self.assertNotIn("request_guardian_letter", [c.get("action_id") for c in self.choices(session)])
        for identifier in ("greet_walter", "ask_guardian_refusal", "request_guardian_letter"):
            self.resolve(session, identifier)
        self.assertTrue(session["flags"]["heard_guardian_refusal"])
        self.assertTrue(shops._owned(session, "guardian_letter")["key_item"])
        self.resolve(session, "hq_to_square")
        self.resolve(session, "square_to_inn")
        self.resolve(session, "ask_oaksdawn_rumor")
        self.assertTrue(session["flags"]["heard_pass_rumor"])
        accusation = next(a for l in self.pack["locations"] for a in l.get("actions", []) if a["id"] == "report_with_evidence")
        for flags, expected in [({CLUES[0]: True}, False), ({CLUES[1]: True}, False),
                                (dict.fromkeys(CLUES, True), True),
                                ({CLUES[0]: True, "heard_old_soldier_ghost": True}, True)]:
            session["flags"] = flags
            self.assertEqual(state.action_requirement_status(accusation, session)[0], expected)

    def test_three_recruitment_routes_hide_all_choices_and_cannot_repeat(self):
        for route in ("letter", "water", "persuade"):
            with self.subTest(route=route):
                session = self.session("oaksdawn_chapel")
                self.assertFalse(any(c.get("action_id", "").startswith("recruit_liese") for c in self.choices(session)))
                self.resolve(session, "talk_liese")
                self.give(session, "guardian_letter")
                self.give(session, "holy_water", 2)
                before = shops._owned(session, "holy_water")["quantity"]
                self.resolve(session, f"recruit_liese_{route}", {"success": True, "dc": 13})
                self.assertEqual(session["companion"]["id"], "paladin_liese")
                self.assertTrue(session["flags"]["recruited_liese"])
                self.assertEqual(shops._owned(session, "holy_water")["quantity"], before - (route == "water"))
                self.assertEqual(shops._owned(session, "guardian_letter")["quantity"], 1)
                self.assertFalse(any(c.get("action_id", "").startswith("recruit_liese") for c in self.choices(session)))
                self.assertEqual(state.public_session(session)["location_npc_portraits"], [])
                for entry in next(l for l in self.pack["locations"] if l["id"] == "oaksdawn_chapel")["actions"]:
                    if entry["id"].startswith("recruit_liese"):
                        self.assertFalse(state.action_requirement_status(entry, session)[0])

    def test_failed_persuasion_can_use_water_but_not_retry_check(self):
        session = self.session("oaksdawn_chapel")
        self.resolve(session, "talk_liese")
        check = state.resolve_action(session, action_id="recruit_liese_persuade")
        self.assertEqual(state.action_dice_settings(check, session=session), ("1d20+wis", 10))
        self.resolve(session, "recruit_liese_persuade", {"success": False, "dc": 13})
        self.assertIsNone(session["companion"])
        self.assertFalse(state.action_requirement_status(check, session)[0])
        self.give(session, "holy_water")
        self.resolve(session, "recruit_liese_water")
        self.assertEqual(session["companion"]["id"], "paladin_liese")

    def test_rest_and_shop_prices_equipment_slot_and_insufficient_gold(self):
        for location, identifier, cost in [("oaksdawn_chapel", "pray_oaksdawn", 5), ("oaksdawn_inn", "rest_oaksdawn", 10)]:
            session = self.session(location)
            session["character"].update(hp=1, mp=0, sp=0, gold=cost)
            self.resolve(session, identifier)
            for resource in ("hp", "mp", "sp"):
                self.assertEqual(session["character"][resource], session["character"][f"max_{resource}"])
            self.assertEqual(session["character"]["gold"], 0)
            self.assertFalse(state.action_requirement_status(state.resolve_action(session, action_id=identifier), session)[0])
        for suffix, item, price in [("chapel", "holy_water", 12), ("workshop", "guardian_chainmail", 40)]:
            session = self.session(f"oaksdawn_{suffix}")
            session["character"]["gold"] = price
            shops.trade(session, f"oaksdawn_{suffix}_shop", item, 1)
            self.assertEqual(session["character"]["gold"], 0)
            with self.assertRaises(shops.ShopError):
                shops.trade(session, f"oaksdawn_{suffix}_shop", item, 1)
            if suffix == "workshop":
                self.assertEqual(shops._owned(session, item)["slot"], "armor")
                shops.use_item(session, item)
                self.assertEqual(combat._actor_defense(session["character"]), 2)

    def test_known_blocked_pass_and_unknown_north_road(self):
        session = self.session("old_battlefield")
        north = lambda: next(c for c in self.choices(session) if c.get("action_id") == "battlefield_to_oaksdawn")
        self.assertEqual(north()["risk"], "不明")
        self.resolve(session, "battlefield_to_oaksdawn")
        self.resolve(session, "square_to_wall")
        blocked = next(c for c in self.choices(session) if c.get("action_id") == "oaksdawn_east_pass")
        self.assertEqual(blocked["text"], "東の峠へ向かう")
        self.assertEqual(blocked["visibility"], "known")
        self.assertEqual(blocked["disabled_reason"], "峠は崩れた大岩で塞がれていて、今は通れない。")
        self.assertFalse(blocked["enabled"])
        self.resolve(session, "oaksdawn_to_battlefield")
        self.assertEqual(north()["risk"], "判定不要")
        # Arriving by road makes the guards know you, so the water gate opens without the first challenge.
        self.assertTrue(session["flags"].get("opened_oaksdawn_gate"))
        for map_id in ("sealed_cave", "old_battlefield"):
            map_data = next(m for m in maps.public_maps(session)["maps"] if m["id"] == map_id)
            city = next(n for n in map_data["nodes"] if n["id"] == "oaksdawn")
            self.assertEqual(city["visibility"], "visited")

    def battle(self, hp):
        session = self.session("grave_chapel")
        session["character"].update(hp=hp, max_hp=100)
        state._set_companion(session, "paladin_liese")
        session["combat_start_requested"] = True
        with patch.object(combat, "random", random.Random(1)):
            self.assertTrue(combat.ensure_combat_started(session))
        return session

    def test_hp_threshold_exclusive_each_round_including_crossing_after_heal(self):
        for hp in (1, 49, 50, 100):
            with self.subTest(hp=hp):
                session = self.battle(hp)
                entries = [e for e in session["combat"]["log"] if e["actor"] == "companion"]
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]["kind"], "heal" if hp < 50 else "damage")
                self.assertEqual(session["character"]["hp"], hp + 20 if hp < 50 else hp)
                self.assertIn("癒しの祈り" if hp < 50 else "聖光の一撃", entries[0]["text"])
                if hp >= 50:
                    self.assertIn("光属性", entries[0]["text"])
        session = self.battle(49)
        session["combat"]["round"] = 2
        combat._apply_round_start_effects(session, random.Random(1))
        self.assertEqual([e["kind"] for e in session["combat"]["log"] if e["actor"] == "companion"], ["heal", "damage"])
        self.assertFalse(state._session_requirement_passes({"player_hp_ratio_lt": .5}, {"character": {"max_hp": 0}}))

    def test_undead_first_living_highest_hp_and_fallback(self):
        for undead, expected in [(True, "wraith"), (False, "goblin")]:
            session = self.battle(100)
            session["combat"]["enemies"] = [
                dict(id="dead", name="骸骨兵", hp=0, max_hp=100, tags=["undead"]),
                dict(id="skeleton", name="骸骨兵", hp=20, max_hp=20, tags=["undead"] if undead else []),
                dict(id="wraith", name="怨霊", hp=25, max_hp=25, tags=["undead"] if undead else []),
                dict(id="goblin", name="ゴブリン", hp=90, max_hp=90, tags=[])]
            before = {e["id"]: e["hp"] for e in session["combat"]["enemies"]}
            combat._apply_ally_round_start_effects(session, session["companion"], random.Random(1))
            self.assertEqual([e["id"] for e in session["combat"]["enemies"] if e["hp"] < before[e["id"]]], [expected])

    def test_offline_balance_trials_are_repeatable_and_keep_start_unchanged(self):
        session = self.session("grave_chapel")
        before = deepcopy(session)
        first = liese.trial(session, "paladin_liese", 20261017)
        self.assertEqual(liese.trial(session, "paladin_liese", 20261017), first)
        self.assertIn(first["status"], {"victory", "defeat"})
        self.assertGreaterEqual(first["hp_loss"], 0)
        liese.trial(session, "none", 20261017)
        self.assertEqual(session, before)

    def test_both_packs_synchronized_idempotent_undead_and_map_geometry(self):
        packs = []
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = json.loads(DEFAULT_SCENARIO.with_name(filename).read_text(encoding="utf-8"))
            upgraded = deepcopy(pack)
            apply(upgraded)
            apply_spring_postgame(upgraded)
            from scripts.scenario.levels_skills_v2 import migrate as levels
            upgraded = holy_sword(levels(upgraded))
            from scripts.scenario.mina_reborrow_055 import migrate as mina_reborrow
            upgraded = mina_reborrow(upgraded)
            from scripts.scenario.normal_tuning_052 import migrate as normal_tuning
            upgraded = normal_tuning(upgraded)
            # Legacy migrations reappend overrides; compare their full content in the source order.
            order = {(e["entity"], e["id"], e["path"]): i
                     for i, e in enumerate(pack["difficulty_overlays"]["normal"])}
            upgraded["difficulty_overlays"]["normal"].sort(
                key=lambda e: order.get((e["entity"], e["id"], e["path"]), len(order)))
            self.assertEqual(upgraded, pack)
            for enemy in pack["enemies"]:
                if enemy["id"] in UNDEAD:
                    self.assertIn("undead", enemy["tags"])
                    self.assertEqual(enemy["resistances"]["holy"], 1.5)
            for m in pack["maps"]:
                for width, height, radius in ((198, 138, 9.5), (268.8, 300, 20), (1152, 600, 20)):
                    self.assertEqual(edge_node_collisions(m, width, height, radius), [])
            session = fresh_session(pack, "hero")
            state.apply_state_delta(session, {"current_location": "cave_hot_spring"}, allow_world_transition=True)
            for identifier in ("follow_hot_spring_water", "waterway_to_gate", "open_oaksdawn_gate"):
                self.resolve(session, identifier)
            self.assertEqual(state.current_location_id(session), "oaksdawn_square")
            self.resolve(session, "square_to_water_gate")
            self.resolve(session, "gate_back")
            self.assertEqual(state.current_location_id(session), "cave_waterway")
            packs.append(pack)
        for key, identifiers in [("locations", DESCRIPTIONS), ("companions", ["paladin_liese"]), ("maps", ["oaksdawn"])]:
            self.assertEqual([x for x in packs[0][key] if x["id"] in identifiers], [x for x in packs[1][key] if x["id"] in identifiers])
        session = self.session("oaksdawn_square")
        self.assertEqual(maps.public_maps(session)["current_map_id"], "oaksdawn")
        self.assertEqual(maps.movement_action(session, "G3")["id"], "square_to_chapel")
        session = self.session("oaksdawn_water_gate")
        self.assertEqual(maps.movement_action(session, "G1")["id"], "open_oaksdawn_gate")


if __name__ == "__main__":
    unittest.main()
