from __future__ import annotations

import json
import random
import unittest
from copy import deepcopy
from unittest.mock import Mock, patch

from host import area_retry, combat, free_actions, npc_combat, shops, state
from host.scenario_context import fallback_choices_for_session, select_scenario_context
from scripts.balance.checkpoints import DEFAULT_SCENARIO, fresh_session
from scripts.eval.snapshots import load_snapshot
from scripts.scenario import npc_combat as migration


class AttackableMagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs = [state.load_scenario_pack(DEFAULT_SCENARIO.with_name(name)) for name in migration.PACKS]

    def sessions(self, location):
        for pack in self.packs:
            session = fresh_session(deepcopy(pack), "hero")
            scene = next(loc["scene_id"] for loc in pack["locations"] if loc["id"] == location)
            session["world_state"] = dict(scene_id=scene, location_id=location)
            session["needs_opening"] = False
            yield session

    def attack(self, session, target):
        context = json.loads(free_actions.build_plan_messages(session, "攻撃する")[1]["content"])
        self.assertIn(target, [npc["id"] for npc in context["npcs"]])
        result = free_actions.adjudicate(session, dict(kind="interact", action_id="", operation="attack",
            target_id=target, item_id="", advance=False, approach="攻撃する", reply=""))
        self.assertEqual(result["outcome"], "confirmation")
        self.assertFalse(combat.combat_is_active(session))
        self.assertEqual([a["action_id"] for a in fallback_choices_for_session(session)],
                         ["npc_attack_confirm", "npc_attack_cancel"])
        npc_combat.resolve_confirmation(session, "npc_attack_confirm")
        self.assertTrue(combat.combat_is_active(session))

    def settle(self, session, outcome="victory", casualties=None):
        for enemy in session["combat"]["enemies"]:
            if outcome == "victory" or enemy.get("npc_id") in (casualties or []):
                enemy["hp"] = 0
        if outcome == "defeat":
            session["character"]["hp"] = 0
        if outcome == "fled":
            combat._finish_combat(session, outcome, "戦闘終了")
        else:
            combat._check_victory_or_defeat(session)
        result = deepcopy(session["combat"]["result"])
        delta = combat.consume_combat_state_delta(session)
        state.apply_state_delta(session, delta, allow_world_transition=True)
        combat.clear_combat_after_resolution(session)
        return delta, result

    def act(self, session, identifier):
        action = state.resolve_action(session, action_id=identifier)
        self.assertIsNotNone(action, identifier)
        self.assertTrue(state.action_requirement_status(action, session)[0], identifier)
        return state.apply_action_result(session, action, {})

    def visible(self, session):
        session["choices"] = fallback_choices_for_session(session)
        return {choice["action_id"] for choice in state.public_session(session)["choices"]}

    def seed(self, session):
        state.apply_state_delta(session, {"inventory_add": [{"id": "fire_seed", "name": "火種", "quantity": 1}],
                                          "flags_set": ["accepted_fire_seed"]})

    def test_both_warlock_ids_use_existing_character_and_share_death(self):
        for location, target in (("magic_shop", "blue_robed_mage"), ("warlock_rescue_battle", "warlock")):
            for session in self.sessions(location):
                state._set_companion(session, "blue_robed_mage")
                session["flags"]["warlock_rescue_available"] = True
                self.attack(session, target)
                self.assertIsNone(session["companion"])
                enemy = session["combat"]["enemies"][0]
                source = next(c for c in session["scenario_pack"]["characters"] if c["id"] == "warlock")
                for key in ("hp", "max_hp", "mp", "max_mp", "sp", "max_sp", "attributes", "resistances", "skills", "combat"):
                    self.assertEqual(enemy[key], source[key], key)
                delta, result = self.settle(session)
                self.assertIn(migration.FALLEN["warlock"], result["npc_aftermath"])
                self.assertTrue(session["flags"]["town_blood"])
                for identifier in ("warlock", "blue_robed_mage"):
                    self.assertTrue(session["flags"]["npc_gone_" + identifier])
                    self.assertTrue(npc_combat.gone(session, identifier))
                self.assertFalse(session["flags"].get("warlock_rescue_available"))
                self.assertEqual(delta["gold_change"], 50)
                self.assertEqual([(i["id"], i["quantity"]) for i in delta["inventory_add"]], [("earth_staff", 1)])
                state.commit_world_position(session, location_id="magic_shop")
                with self.assertRaises(shops.ShopError):
                    shops.public_shop(session, "magic_shop")
                for identifier in ("invite_blue_mage", "ask_blue_mage_rumor", "ask_seal_lore", "read_magic_tomes",
                                   "ask_mina_missing", "report_mina_safe", "open_magic_shop"):
                    self.assertIsNone(state.resolve_action(session, action_id=identifier), identifier)
                state._set_companion(session, "blue_robed_mage")
                self.assertIsNone(session["companion"])
                self.assertEqual(select_scenario_context(session)["current_location"]["description"], migration.FALLEN["warlock"])
                self.assertIn("return_castle_from_magic_shop", self.visible(session))

    def test_mina_guardian_and_solo_attack_after_partial_victory(self):
        for session in self.sessions("magic_shop"):
            session["flags"].update(mina_quest_done=True, warlock_rescue_available=True)
            state._set_companion(session, "blue_robed_mage")
            self.attack(session, "mina")
            self.assertIsNone(session["companion"])
            self.assertEqual([e["npc_id"] for e in session["combat"]["enemies"]], ["mina", "warlock"])
            delta, _ = self.settle(session, "fled", ["warlock"])
            self.assertEqual(delta["gold_change"], 50)
            self.assertFalse(npc_combat.gone(session, "mina"))
            self.assertFalse(session["flags"].get("warlock_rescue_available"))
            self.attack(session, "mina")
            self.assertEqual([e["npc_id"] for e in session["combat"]["enemies"]], ["mina"])
            delta, result = self.settle(session)
            self.assertEqual(delta["gold_change"], 0)
            self.assertNotIn(migration.FALLEN["mina"], result["npc_aftermath"])
            self.assertTrue(npc_combat.gone(session, "mina"))

    def test_guardian_survives_mina_and_counter_does_not_duplicate_sold_stock(self):
        for session in self.sessions("magic_shop"):
            session["flags"]["mina_quest_done"] = True
            self.attack(session, "mina")
            delta, _ = self.settle(session, "fled", ["mina"])
            self.assertEqual(delta["gold_change"], 0)
            self.assertFalse(npc_combat.gone(session, "warlock"))
            self.assertTrue(shops.public_shop(session, "magic_shop"))
            session["shop_stock"] = {"magic_shop": {"earth_staff": 0}}
            self.attack(session, "blue_robed_mage")
            delta, _ = self.settle(session)
            self.assertEqual(delta["inventory_add"], [])
            self.assertEqual(delta["gold_change"], 50)

    def test_dead_warlock_removes_rescues_but_ultimatum_and_nest_continue(self):
        for session in self.sessions("magic_shop"):
            session["flags"]["warlock_rescue_available"] = True
            self.attack(session, "blue_robed_mage")
            self.settle(session)
            state.commit_world_position(session, location_id="xanxus_ultimatum")
            self.assertEqual(self.visible(session), {"accept_xanxus_fire_seed", "refuse_xanxus_without_rescue"})
            refusal = deepcopy(session)
            self.act(refusal, "refuse_xanxus_without_rescue")
            self.assertEqual(refusal["game_over"]["ending"], "defied_xanxus")
            self.act(session, "accept_xanxus_fire_seed")
            self.assertEqual(state.current_location_id(session), "village_frozen_clue")
            state.apply_state_delta(session, {"current_location": "valley_nest_gate"}, allow_world_transition=True)
            self.assertEqual(state.current_location_id(session), "xanxus_at_nest")
            self.assertEqual(self.visible(session), {"obey_xanxus_core"})
            state.apply_state_delta(session, {"inventory_add": [{"id": "holy_water", "name": "聖水", "quantity": 1}]})
            self.assertEqual(self.visible(session), {"obey_xanxus_core", "cleanse_fire_seed"})
            self.act(session, "obey_xanxus_core")
            self.assertEqual(state.current_location_id(session), "valley_nest_gate")
            self.assertIn("enter_dragon_nest", self.visible(session))

    def test_stale_rescue_flag_cannot_resurrect_either_warlock_identity(self):
        for identifier in ("warlock", "blue_robed_mage"):
            for session in self.sessions("xanxus_ultimatum"):
                session["flags"].update({"warlock_rescue_available": True, "npc_gone_" + identifier: True})
                self.assertEqual(self.visible(session), {"accept_xanxus_fire_seed", "refuse_xanxus_without_rescue"})
                state.apply_state_delta(session, {"current_location": "valley_nest_gate"}, allow_world_transition=True)
                self.assertEqual(state.current_location_id(session), "valley_nest_gate")
                self.assertFalse(session["flags"].get("heard_xanxus_betrayal"))
                lines = state._epilogue_lines(session, {"ending": "ignis_defeated"})
                original = next(e["text"] for e in session["scenario_pack"]["epilogues"] if e["id"] == "warlock")
                self.assertNotIn(original, lines)

    def test_xanxus_three_victory_destinations_flags_seed_and_epilogue(self):
        for location in ("xanxus_confrontation", "xanxus_ultimatum", "xanxus_at_nest"):
            for seeded in (False, True):
                for session in self.sessions(location):
                    if seeded:
                        self.seed(session)
                    self.attack(session, "xanxus")
                    enemy = session["combat"]["enemies"][0]
                    original = next(e for e in session["scenario_pack"]["enemies"] if e["id"] == "xanxus")
                    for key in ("hp", "max_hp", "mp", "attributes", "combat", "resistances", "skills"):
                        self.assertEqual(enemy[key], original[key])
                    _, result = self.settle(session)
                    self.assertEqual(state.current_location_id(session),
                                     "valley_nest_gate" if location == "xanxus_at_nest" else "village_frozen_clue")
                    self.assertIn(migration.FALLEN["xanxus"], result["npc_aftermath"])
                    for flag in ("defeated_xanxus", "heard_xanxus_betrayal", "xanxus_encountered", "npc_gone_xanxus"):
                        self.assertTrue(session["flags"][flag])
                    self.assertFalse(session["flags"].get("town_blood"))
                    self.assertFalse(any(i.get("id") == "fire_seed" for i in session["character"]["inventory"]))
                    self.assertEqual(bool(session["flags"].get("fire_seed_removed")), seeded)
                    session["flags"].update(fire_seed_removed=True, xanxus_took_core=True)
                    old_lines = [e["text"] for e in session["scenario_pack"]["epilogues"]
                                 if e["id"] in {"fire_seed_removed", "xanxus_core"}]
                    for ending in ("ignis_defeated", "ignis_purified", "draco_defeated", "draco_defeated_with_ignis"):
                        lines = state._epilogue_lines(session, {"ending": ending})
                        self.assertEqual(lines.count(migration.XANXUS_EPILOGUE), 1)
                        self.assertFalse(any(line in lines for line in old_lines))
                    for revisit in ("xanxus_confrontation", "xanxus_ultimatum", "xanxus_at_nest"):
                        state.commit_world_position(session, location_id=revisit)
                        self.assertFalse(npc_combat.present(session, "xanxus"))

    def test_free_attack_defeat_is_death_and_area_retry(self):
        for location, target, entry in (("magic_shop", "blue_robed_mage", "castle_town"),
                ("xanxus_confrontation", "xanxus", "village_approach"),
                ("xanxus_ultimatum", "xanxus", "village_approach"),
                ("xanxus_at_nest", "xanxus", "valley_entrance")):
            for session in self.sessions("castle"):
                session["area_snapshots"] = {}
                scene = next(loc["scene_id"] for loc in session["scenario_pack"]["locations"] if loc["id"] == entry)
                session["world_state"] = dict(scene_id=scene, location_id="fixture")
                state.apply_state_delta(session, {"current_location": entry}, allow_world_transition=True)
                state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)
                self.attack(session, target)
                self.assertNotEqual(session["combat"]["encounter"]["encounter_class"], "scripted_loss")
                self.settle(session, "defeat")
                self.assertEqual(session["character"]["hp"], 0)
                self.assertEqual(session["game_over"]["ending"], "combat_defeat")
                self.assertTrue(session["game_over"]["combat_defeat"])
                self.assertEqual(state.current_location_id(session), location)
                self.assertIsNotNone(area_retry.retry_snapshot(session))
                with patch("host.llm_trace.append_trace"):
                    area_retry.retry_area(session)
                self.assertEqual(state.current_location_id(session), entry)
                self.assertFalse(session.get("game_over"))

    def test_original_scripted_attack_still_loses_to_ultimatum(self):
        for session in self.sessions("xanxus_confrontation"):
            action = state.resolve_action(session, action_id="ambush_xanxus")
            _, dc = state.action_dice_settings(action, session=session)
            state.apply_action_result(session, action, {"dc": dc, "total": 1, "success": False})
            self.assertEqual(state.current_location_id(session), "xanxus_battle")
            combat.ensure_combat_started(session)
            self.assertEqual(session["combat"]["encounter"]["encounter_class"], "scripted_loss")
            self.settle(session, "defeat")
            self.assertEqual(state.current_location_id(session), "xanxus_ultimatum")
            self.assertEqual(session["character"]["hp"], 1)
            self.assertFalse(session.get("game_over"))

    def test_real_enemy_turns_kill_without_scripted_rescue(self):
        for location, target in (("magic_shop", "blue_robed_mage"), ("xanxus_confrontation", "xanxus"),
                                 ("xanxus_ultimatum", "xanxus"), ("xanxus_at_nest", "xanxus")):
            session = next(self.sessions(location))
            self.attack(session, target)
            rng = random.Random(45)
            for _ in range(10):
                if not combat.combat_is_active(session):
                    break
                combat.perform_combat_action(session, "attack", target_id=session["combat"]["enemies"][0]["id"], rng=rng)
            self.assertEqual(session["combat"]["status"], "defeat")
            state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
            self.assertEqual(session["game_over"]["ending"], "combat_defeat")
            self.assertEqual(state.current_location_id(session), location)

    def test_dead_xanxus_is_skipped_at_all_entry_routes_and_core_events(self):
        for session in self.sessions("village_approach"):
            session["flags"].update(defeated_xanxus=True, heard_name_xanxus=True)
            self.act(session, "escape_from_burning_village")
            self.assertEqual(state.current_location_id(session), "village_frozen_clue")
            self.assertNotIn("skip_frozen_clue_before_xanxus", self.visible(session))
            self.act(session, "skip_frozen_clue_after_xanxus")
            self.assertEqual(state.current_location_id(session), "valley_entrance")
            session["world_state"] = dict(scene_id="village", location_id="ian_ice_katana_aftermath")
            self.assertNotIn("refuse_ian_before_xanxus", self.visible(session))
            self.act(session, "refuse_ian_after_xanxus")
            self.assertEqual(state.current_location_id(session), "valley_entrance")
            self.seed(session)
            for origin in ("valley_lava_bridge", "valley_ledge"):
                session["flags"].pop("nest_event_seen", None)
                state.commit_world_position(session, location_id=origin)
                if origin == "valley_lava_bridge":
                    action = state.resolve_action(session, action_id="cross_lava_bridge")
                    _, dc = state.action_dice_settings(action, session=session)
                    state.apply_action_result(session, action, {"dc": dc, "total": 99, "success": True})
                else:
                    combat.ensure_combat_started(session)
                    self.settle(session)
                self.assertEqual(state.current_location_id(session), "valley_nest_gate")
            session["flags"].update(promised_core_to_xanxus=True, xanxus_took_core=True)
            for location in ("ignis_last_breath", "ignis_purified"):
                state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)
            self.assertFalse(session["flags"].get("xanxus_core_scene_seen"))
            self.assertFalse(session["flags"].get("xanxus_denied_core"))

    def test_warlock_enemy_stance_counter_and_all_twenty_four_element_hits(self):
        session = next(self.sessions("magic_shop"))
        self.attack(session, "blue_robed_mage")
        enemy = session["combat"]["enemies"][0]
        actor = session["character"]
        actor.update(hp=10000, max_hp=10000, inventory=[], equipment=[], resistances={},
                     combat={"basic_attack": {"element": "fire"}, "evade": 0, "defense": 0})
        skills = {skill["id"]: skill for skill in enemy["skills"]}
        rng = Mock()
        rng.randint.return_value = 1
        combat._execute_enemy_ability(session, enemy, skills["element_switch"], rng)
        self.assertEqual(actor["hp"], 10000)
        self.assertEqual(enemy["combat_immunities"], ["fire"])
        self.assertEqual(combat._resistance_multiplier(enemy, "fire"), 0)
        combat._execute_enemy_ability(session, enemy, skills["element_counter"], rng)
        self.assertEqual(actor["hp"], 10000 - 110)
        start = len(session["combat"]["log"])
        combat._execute_enemy_ability(session, enemy, skills["element_prayer"], rng)
        hits = [event for event in session["combat"]["log"][start:] if event["kind"] == "damage"]
        self.assertEqual(len(hits), 24)
        self.assertEqual(actor["hp"], 10000 - 110 - 72)
        actor["hp"] = 1
        start = len(session["combat"]["log"])
        combat._execute_enemy_ability(session, enemy, skills["element_prayer"], rng)
        self.assertEqual(len([e for e in session["combat"]["log"][start:] if e["kind"] == "damage"]), 1)

    def test_reviewed_candidates_have_attack_targets_and_engine_confirmation(self):
        path = migration.ROOT / "eval/candidates/041-npc-attacks.jsonl"
        rows = {row["id"]: row for row in map(json.loads, path.read_text(encoding="utf-8").splitlines())}
        for number in (27, 28, 29, 30):
            row = rows[f"041-npc-{number:03}"]
            self.assertEqual(row["label_status"], "design_reviewed_041")
            session = load_snapshot(row["snapshot"])
            self.attack(session, row["gold"][0]["target_id"])


if __name__ == "__main__":
    unittest.main()
