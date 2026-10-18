from __future__ import annotations

import json
import random
import unittest
from copy import deepcopy
from unittest.mock import patch

from host import combat, maps, state
from host.scenario_context import select_scenario_context
from scripts.balance import gorge, liese
from scripts.balance.checkpoints import DEFAULT_SCENARIO, fresh_session
from scripts.scenario.rumbling_gorge import BATTLES, CLUES, DESCRIPTIONS, ENEMIES, apply
from tests.test_map_layout import edge_node_collisions


class RumblingGorgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(DEFAULT_SCENARIO)

    def session(self, location="gorge_entrance"):
        session = fresh_session(deepcopy(self.pack), "hero")
        state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)
        return session

    def resolve(self, session, identifier, roll=None):
        action = state.resolve_action(session, action_id=identifier)
        self.assertIsNotNone(action, identifier)
        self.assertTrue(state.action_requirement_status(action, session)[0], identifier)
        if roll is not None and action.get("roll"):
            roll = {**roll, "dc": action["roll"]["dc"]}
        return state.apply_action_result(session, action, roll or {})

    def choices(self, session):
        return state.player_choices_for_session(state.fallback_choices_for_session(session), session)

    def give(self, session, identifier):
        item = next(i for i in self.pack["items"] if i["id"] == identifier)
        state.apply_state_delta(session, {"inventory_add": [{**item, "quantity": 1}]})

    def battle(self, location="gorge_worm_lair", companion="hydromancer_elio"):
        session = self.session(location)
        session["character"].update(hp=500, max_hp=500)
        state._set_companion(session, companion)
        self.resolve(session, f"fight_{location}")
        with patch.object(combat, "random", random.Random(35)):
            self.assertTrue(combat.ensure_combat_started(session))
        return session

    def test_pass_requires_walter_and_keeps_known_blocked_reason(self):
        session = self.session("oaksdawn_hq")
        self.assertNotIn("open_gorge_path", [c.get("action_id") for c in self.choices(session)])
        self.resolve(session, "hq_to_square")
        self.resolve(session, "square_to_wall")
        blocked = next(c for c in self.choices(session) if c.get("action_id") == "oaksdawn_east_pass")
        self.assertFalse(blocked["enabled"])
        self.assertEqual(blocked["visibility"], "known")
        self.assertEqual(blocked["disabled_reason"], "峠は崩れた大岩で塞がれていて、今は通れない。")
        self.resolve(session, "wall_to_square")
        self.resolve(session, "square_to_hq")
        self.resolve(session, "greet_walter")
        self.resolve(session, "open_gorge_path")
        self.assertTrue(session["flags"]["gorge_path_open"])
        self.assertNotIn("open_gorge_path", [c.get("action_id") for c in self.choices(session)])
        self.resolve(session, "hq_to_square")
        self.resolve(session, "square_to_wall")
        self.assertIn("どけられ", select_scenario_context(session)["current_location"]["description"])
        self.assertEqual(maps.movement_action(session, "gorge")["id"], "oaksdawn_east_pass_open")
        self.resolve(session, "oaksdawn_east_pass_open")
        self.resolve(session, "gorge_to_wall")
        self.resolve(session, "oaksdawn_east_pass_open")
        self.assertEqual(state.current_location_id(session), "gorge_entrance")

    def test_roundtrip_rest_clues_steal_and_village_exit(self):
        session = self.session()
        self.assertEqual(maps.public_maps(session)["current_map_id"], "rumbling_gorge")
        for identifier in ("gorge_to_rockfall", "sneak_gorge_rockfall_path", "rockfall_to_entrance", "gorge_to_rockfall",
                           "rockfall_to_camp", "search_miner_camp", "rest_miner_camp", "camp_to_rockfall",
                           "rockfall_to_cliff", "inspect_white_claw", "cliff_to_rockfall", "rockfall_to_cliff",
                           "cliff_to_giant", "sneak_gorge_giant_path", "giant_to_cliff", "cliff_to_giant",
                           "giant_to_worm", "sneak_gorge_worm_lair", "worm_to_giant", "giant_to_worm", "gorge_to_village"):
            self.resolve(session, identifier, {"success": True})
            self.assertFalse(combat.ensure_combat_started(session))
        self.assertEqual(state.current_location_id(session), "village")
        self.assertTrue(all(session["flags"].get(c) for c in CLUES))
        self.assertTrue(session["flags"]["elite_fruit_claimed:rumbling_gorge"])
        self.assertTrue(session["flags"]["reward_claimed:gorge_giant_path"])
        self.assertEqual(sum(i.get("quantity", 1) for i in session["character"]["inventory"] if i.get("id") == "fruit_life"), 1)
        self.assertFalse(session["flags"].get("reward_claimed:gorge_worm_lair"))

    def test_camp_and_spring_are_single_use(self):
        session = self.session("gorge_miner_camp")
        for resource in ("hp", "mp", "sp"):
            session["character"][resource] = 1
        self.resolve(session, "rest_miner_camp")
        for resource in ("hp", "mp", "sp"):
            self.assertEqual(session["character"][resource], session["character"][f"max_{resource}"])
        self.assertNotIn("rest_miner_camp", [c.get("action_id") for c in self.choices(session)])
        session = self.session("elf_spring")
        self.resolve(session, "draw_spirit_spring_water")
        self.assertNotIn("draw_spirit_spring_water", [c.get("action_id") for c in self.choices(session)])
        self.assertEqual(sum(i.get("quantity", 1) for i in session["character"]["inventory"] if i.get("id") == "spirit_spring_water"), 1)

    def test_three_recruitment_methods_and_hiding_after_replacement(self):
        for method in ("gold", "water", "persuade"):
            with self.subTest(method=method):
                session = self.session("oaksdawn_inn")
                self.assertFalse(any(c.get("action_id", "").startswith("recruit_elio_") for c in self.choices(session)))
                session["character"]["gold"] = 80
                self.give(session, "spirit_spring_water")
                self.resolve(session, "talk_elio")
                self.resolve(session, f"recruit_elio_{method}", {"success": True})
                self.assertEqual(session["companion"]["id"], "hydromancer_elio")
                self.assertEqual(session["character"]["gold"], 30 if method == "gold" else 80)
                self.assertEqual(any(i.get("id") == "spirit_spring_water" for i in session["character"]["inventory"]), method != "water")
                state._set_companion(session, "robin")
                self.assertFalse(any(c.get("action_id", "").startswith("recruit_elio_") for c in self.choices(session)))
                self.assertNotIn("水差し", state._current_location_record(session)["description"])

    def test_failed_persuasion_is_once_other_methods_remain_available(self):
        session = self.session("oaksdawn_inn")
        session["character"]["gold"] = 49
        self.resolve(session, "talk_elio")
        self.resolve(session, "recruit_elio_persuade", {"success": False})
        action = state.resolve_action(session, action_id="recruit_elio_persuade")
        self.assertFalse(state.action_requirement_status(action, session)[0])
        self.assertIsNone(session["companion"])
        gold = state.resolve_action(session, action_id="recruit_elio_gold")
        self.assertFalse(state.action_requirement_status(gold, session)[0])
        session["character"]["gold"] = 50
        self.resolve(session, "recruit_elio_gold")
        self.assertEqual(session["character"]["gold"], 0)

    def test_elio_worm_bypass_is_hidden_without_companion_and_never_rewards(self):
        session = self.session("gorge_worm_lair")
        self.assertNotIn("elio_flood_worm", [c.get("action_id") for c in self.choices(session)])
        session["flags"]["recruited_elio"] = True
        self.assertNotIn("elio_flood_worm", [c.get("action_id") for c in self.choices(session)])
        state._set_companion(session, "hydromancer_elio")
        before = deepcopy(session["character"])
        self.resolve(session, "elio_flood_worm")
        self.assertFalse(combat.ensure_combat_started(session))
        self.assertEqual(session["character"], before)
        self.assertFalse(session["flags"].get("reward_claimed:gorge_worm_lair"))
        self.resolve(session, "gorge_to_village")
        self.assertEqual(state.current_location_id(session), "village")

    def test_failure_starts_combat_and_only_elite_boss_have_enemy_first(self):
        for location in BATTLES:
            session = self.session(location)
            self.resolve(session, f"sneak_{location}", {"success": False})
            self.assertTrue(session["combat_start_requested"])
            self.assertEqual(bool(session.get("enemy_first_requested")), location != "gorge_rockfall_path")
            with patch.object(combat, "random", random.Random(35)):
                combat.ensure_combat_started(session)
            enemy_ids = {e["id"] for e in session["combat"]["enemies"]}
            self.assertEqual(any(e["actor"] in enemy_ids for e in session["combat"]["log"]), location != "gorge_rockfall_path")

    def test_combat_rewards_once_and_no_double_fruit_after_steal(self):
        for location, item in (("gorge_giant_path", "fruit_life"), ("gorge_worm_lair", "elixir_end")):
            session = self.battle(location, None)
            for enemy in session["combat"]["enemies"]:
                enemy["hp"] = 0
            combat._check_victory_or_defeat(session)
            state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
            combat.clear_combat_after_resolution(session)
            self.assertTrue(session["flags"][f"passed_{location}"])
            self.assertTrue(session["flags"][f"reward_claimed:{location}"])
            self.assertEqual(sum(i.get("quantity", 1) for i in session["character"]["inventory"] if i.get("id") == item), 1)
        session = self.session("gorge_giant_path")
        self.resolve(session, "sneak_gorge_giant_path", {"success": True})
        # Directly request the same encounter to verify the common reward guard, independently of UI hiding.
        session["combat_start_requested"] = True
        combat.ensure_combat_started(session)
        for enemy in session["combat"]["enemies"]:
            enemy["hp"] = 0
        combat._check_victory_or_defeat(session)
        state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
        combat.clear_combat_after_resolution(session)
        self.assertEqual(sum(i.get("quantity", 1) for i in session["character"]["inventory"] if i.get("id") == "fruit_life"), 1)

    def test_new_clues_count_toward_accusation(self):
        session = self.session("castle_report")
        entry = state.resolve_action(session, action_id="report_with_evidence")
        self.assertFalse(state.action_requirement_status(entry, session)[0])
        for clue in CLUES:
            session["flags"][clue] = True
        self.assertTrue(state.action_requirement_status(entry, session)[0])

    def test_unknown_destinations_do_not_hide_current_encounter_checks(self):
        session = self.session()
        self.assertEqual(next(c for c in self.choices(session) if c.get("action_id") == "gorge_to_rockfall")["risk"], "不明")
        self.resolve(session, "gorge_to_rockfall")
        choices = {c["action_id"]: c for c in self.choices(session)}
        self.assertEqual(choices["fight_gorge_rockfall_path"]["risk"], "危険（戦闘）")
        self.assertEqual(choices["sneak_gorge_rockfall_path"]["risk"], "1d20+dex判定（DC13）")
        self.assertFalse(combat.ensure_combat_started(session))

    def test_water_curtain_reduces_actual_multi_hit_attacks_without_affecting_outgoing_damage(self):
        session = self.battle()
        actor, battle = session["character"], session["combat"]
        actor.update(inventory=[], attributes={}, combat={"defense": 0, "evade": 0}, resistances={})
        enemy = battle["enemies"][0]
        session["companion"]["round_start_effects"] = [dict(kind="received_damage_multiplier", name="水の帳", multiplier=.5, every_n_rounds=3)]
        ability = dict(id="test", name="攻撃", damage="12", accuracy=100, element="water", hits=2)
        for number, loss in ((3, 12), (4, 24), (6, 12)):
            battle["round"] = number
            combat._apply_round_start_effects(session, random.Random(1))
            before = actor["hp"]
            combat._execute_enemy_ability(session, enemy, ability, random.Random(1))
            self.assertEqual(before - actor["hp"], loss)
        enemy["hp"] = 100
        combat._resolve_attack(session, actor, enemy, ability, "player", random.Random(1))
        self.assertEqual(enemy["hp"], 82)  # 12 water * 1.5; protection only belongs to the player.

    def test_weakness_target_uses_effective_resistance_and_living_highest_hp_fallback(self):
        for element in ("water", "ice"):
            session = self.battle()
            enemies = [dict(id="dead", name="岩の巨人", hp=0, max_hp=100, resistances={element: 2}),
                       dict(id="large", name="岩の巨人", hp=100, max_hp=100, resistances={}),
                       dict(id="small", name="石肌のトカゲ", hp=20, max_hp=20, resistances={element: 1.5}),
                       dict(id="weak", name="砂礫の甲虫", hp=30, max_hp=30, resistances={element: 1.5}),
                       dict(id="immune", name="土喰らいの大ワーム", hp=50, max_hp=50, resistances={element: 2}, combat_immunities=[element])]
            effect = dict(id="test_ally", name="同行者", round_start_effects=[dict(kind="damage_enemy", damage="4", element=element, target=f"weak_to:{element}")])
            for weak, expected in ((True, "weak"), (False, "large")):
                session["combat"]["enemies"] = deepcopy(enemies)
                if not weak:
                    for enemy in session["combat"]["enemies"]:
                        enemy["resistances"] = {}
                before = {e["id"]: e["hp"] for e in session["combat"]["enemies"]}
                combat._apply_ally_round_start_effects(session, effect, random.Random(1))
                self.assertEqual([e["id"] for e in session["combat"]["enemies"] if e["hp"] < before[e["id"]]], [expected])

    def test_round_protection_applies_to_recoil_and_healing_converted_to_damage(self):
        session = self.battle()
        actor, battle = session["character"], session["combat"]
        actor.update(inventory=[], attributes={}, combat={})
        actor["skills"] = [dict(id="test_heal", name="回復", kind="heal", healing="10", cost=0)]
        enemy = battle["enemies"][0]
        for multiplier, expected in ((.5, 5), (1.0, 10)):
            battle["round_received_multiplier"] = multiplier
            before = actor["hp"]
            combat._resolve_attack(session, actor, enemy,
                dict(name="攻撃", damage="2", accuracy=100, self_damage=10), "player", random.Random(1))
            self.assertEqual(before - actor["hp"], expected)
            before = actor["hp"]
            with patch.object(combat, "_equipped_effect", return_value=True):
                combat._player_skill(session, "test_heal", enemy["id"], random.Random(1))
            self.assertEqual(before - actor["hp"], expected)

    def test_round_protection_covers_attacks_fields_statuses_and_expires(self):
        session = self.battle()
        actor, battle = session["character"], session["combat"]
        actor["inventory"] = []
        actor["equipped_items"] = {}
        actor["combat"] = {"defense": 0, "evade": 0}
        actor["resistances"] = {}
        # Use a different ally ID: protection must be fully data-driven.
        session["companion"] = dict(id="test_ally", name="同行者", round_start_effects=[
            dict(kind="received_damage_multiplier", name="水の帳", multiplier=.5, every_n_rounds=3)])
        enemy = battle["enemies"][0]
        battle["fields"] = [dict(id="test", source_id=enemy["id"], damage="10", element="water", name="領域")]
        actor["statuses"] = [dict(id="burn", name="火傷", damage="10", remaining_rounds=4)]
        for number, expected in ((2, 20), (3, 10), (4, 20)):
            battle["round"] = number
            before = actor["hp"]
            combat._apply_round_start_effects(session, random.Random(1))
            self.assertEqual(before - actor["hp"], expected)
            self.assertEqual(combat._modified_received_damage(session, 10, "physical", enemy, "攻撃"), 5 if number == 3 else 10)
        self.assertEqual(len([e for e in battle["log"] if e["kind"] == "support"]), 1)
        battle["round"] = 6
        battle["encounter"]["disable_companion"] = True
        combat._apply_round_start_effects(session, random.Random(1))
        self.assertEqual(battle["round_received_multiplier"], 1)

    def test_trials_are_deterministic_and_do_not_mutate_template(self):
        session = self.session("gorge_worm_lair")
        before = deepcopy(session)
        self.assertEqual(liese.trial(session, "hydromancer_elio", 35), liese.trial(session, "hydromancer_elio", 35))
        with patch.object(state, "utc_now", return_value="2026-10-18T00:00:00Z"):
            self.assertEqual(gorge.route_trial(session, 35), gorge.route_trial(session, 35))
        self.assertEqual(session, before)

    def test_outside_comparison_covers_every_non_scripted_companion_encounter(self):
        locations = set(gorge.outside_locations(self.pack))
        self.assertEqual(len(locations), 32)
        self.assertTrue({"merchant_battle", "mansion_corridor", "inn_night_ambush", "grave_chapel", "draco_battle"} <= locations)
        self.assertFalse(locations & {"xanxus_battle", "warlock_rescue_battle", *gorge.BATTLES})

    def test_both_packs_synchronized_and_reapplication_preserves_existing_content(self):
        packs = []
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = json.loads(DEFAULT_SCENARIO.with_name(filename).read_text(encoding="utf-8"))
            upgraded = deepcopy(pack)
            apply(upgraded)
            self.assertEqual(upgraded, pack)
            for loc in pack["locations"]:
                if loc["id"] in DESCRIPTIONS:
                    self.assertEqual(loc["description"], DESCRIPTIONS[loc["id"]][1])
                    self.assertEqual(loc["enemy_ids"], loc["combat"]["enemy_ids"])
            for enemy in pack["enemies"]:
                if enemy["id"] in {row[0] for row in ENEMIES}:
                    self.assertEqual(enemy["resistances"], {"physical": .6, "water": 1.5})
                    self.assertIn("earth", enemy["tags"])
            for m in pack["maps"]:
                for width, height, radius in ((198, 138, 9.5), (268.8, 300, 20), (1152, 600, 20)):
                    self.assertEqual(edge_node_collisions(m, width, height, radius), [])
            packs.append(pack)
        for key, ids in (("locations", DESCRIPTIONS), ("enemies", [e[0] for e in ENEMIES]),
                         ("companions", ["hydromancer_elio"]), ("maps", ["rumbling_gorge"])):
            self.assertEqual([x for x in packs[0][key] if x["id"] in ids], [x for x in packs[1][key] if x["id"] in ids])


if __name__ == "__main__":
    unittest.main()
