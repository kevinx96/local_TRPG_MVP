from __future__ import annotations

import json
import random
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import combat, progression, state
from host.difficulty import apply_difficulty
from scripts.balance import archetypes, battle_v3, budget, checkpoints, measurement_v3, normal_052, route_v2, snapshots_v3


class Normal052Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = apply_difficulty(state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO), "normal")

    def session(self, character="mage", level=2):
        session = checkpoints.fresh_session(deepcopy(self.pack), character, "normal", effective=True)
        progression.reward(session, self.pack["progression"]["exp_table"].get(str(level), 0), "test")
        session = archetypes.PassivePicker("table", archetypes.default_passive_choices(character)).apply(session)
        session["world_state"] = {"scene_id": "forest_wolves", "location_id": "forest_wolves"}
        session["combat_start_requested"] = True
        return session

    def test_m9_removes_shield_and_guard_without_mutating_snapshot_or_rng(self):
        session = self.session()
        combat.ensure_combat_started(session)
        self.assertTrue(any("shield_remaining" in s for s in session["character"]["statuses"]))
        session["combat"]["player_status"]["guard_multiplier"] = .25
        before, rng = deepcopy(session), random.getstate()
        result = normal_052.opening_moments(session)
        self.assertGreater(result["ratio"], 0)
        self.assertEqual(result["with_shields"], budget.phase_moments(session))
        self.assertLess(result["with_shields"]["ratio"], result["ratio"])
        self.assertEqual(session, before)
        self.assertEqual(random.getstate(), rng)
        session["combat"]["player_status"].pop("guard_multiplier")
        for status in session["character"]["statuses"]:
            status.pop("shield_remaining", None)
        self.assertEqual(result["ratio"], budget.phase_moments(session)["ratio"])

    def test_m9_keeps_actual_defense_and_dex_evasion(self):
        session = self.session("hero", 2)
        combat.ensure_combat_started(session)
        original = normal_052.opening_moments(session)["ratio"]
        session["character"]["combat"]["defense"] += 3
        self.assertLess(normal_052.opening_moments(session)["ratio"], original)
        session["character"]["combat"]["defense"] -= 3
        session["character"]["attributes"]["dex"] += 10
        self.assertLess(normal_052.opening_moments(session)["ratio"], original)

    def test_auxiliary_replay_is_deterministic_and_keeps_original_snapshot(self):
        snapshot = snapshots_v3.capture(self.session())
        before, rng = deepcopy(snapshot), random.getstate()
        first = normal_052.first_three_rounds(self.pack, snapshot, 20261022, "forest_wolves")
        self.assertEqual(first, normal_052.first_three_rounds(self.pack, snapshot, 20261022, "forest_wolves"))
        self.assertEqual(snapshot, before)
        self.assertEqual(random.getstate(), rng)
        self.assertLessEqual(first["observed_rounds"], 3)
        if first["observed_rounds"] != 3:
            self.assertIsNone(first["mean_ratio"])
            self.assertIsNotNone(first["missing_reason"])

    def test_baby_rejects_normal_only_measurement_options(self):
        with self.assertRaises(ValueError):
            normal_052.opening_moments({"difficulty": "baby"})
        for args in (["--tuning-052"], ["--skip-passive-enumeration"],
                     ["--difficulty", "baby", "--skip-passive-probes"],
                     ["--difficulty", "normal", "--checkpoint-output", str(checkpoints.ROOT / "eval/balance/checkpoints_normal_053.json")]):
            with self.subTest(args=args), self.assertRaises(SystemExit) as raised:
                measurement_v3.main(args)
            self.assertEqual(raised.exception.code, 2)

    def test_frozen_table_is_not_written_by_normal_measurement(self):
        table = checkpoints.ROOT / "eval/balance/passive_defaults.json"
        before = table.read_bytes()
        with patch.object(route_v2, "run_jobs", side_effect=RuntimeError("stop before trials")), \
                patch.object(Path, "write_text", side_effect=AssertionError("unexpected write")):
            with self.assertRaisesRegex(RuntimeError, "stop before trials"):
                measurement_v3.main(["--difficulty", "normal", "--passive-table", str(table),
                                    "--skip-passive-enumeration", "--tuning-052", "--n", "1"])
        self.assertEqual(table.read_bytes(), before)

    def test_output_alias_of_read_only_table_is_rejected(self):
        table = checkpoints.ROOT / "eval/balance/passive_defaults.json"
        before = table.read_bytes()
        for option in ("--output", "--records-output", "--checkpoint-output"):
            with self.subTest(option=option), self.assertRaises(SystemExit) as raised:
                measurement_v3.main(["--difficulty", "normal", "--passive-table", str(table),
                                    "--skip-passive-enumeration", option, str(table)])
            self.assertEqual(raised.exception.code, 2)
        self.assertEqual(table.read_bytes(), before)

    def test_escort_report_then_borrow_is_reachable_and_once_only(self):
        run = route_v2.MeasurementRun(self.pack, "hero", 53, archetypes.ARCHETYPES["P3"],
                                     difficulty="normal", effective=True,
                                     branches={"escort_order": "borrow_after_report"})
        run.session["world_state"] = {"scene_id": "cave_prism_tree", "location_id": "cave_prism_tree"}
        run.session["flags"].update(cleared_cave_prism_tree=True, cleared_cave_crystal_corridor=True,
                                    cleared_cave_heat_corridor=True, met_mina=True, mina_waiting=True)
        run.hook("after_tree")
        self.assertTrue(run.session["flags"]["mina_rescued"])
        run.session["world_state"] = {"scene_id": "castle_town", "location_id": "castle_town"}
        run.town_shops(returning=True)
        actions = [row["action"] for row in run.steps]
        self.assertLess(actions.index("report_mina_safe"), actions.index("borrow_fire_bat_dragon"))
        self.assertTrue(run.session["flags"]["asked_to_borrow_fire_bat_dragon"])
        self.assertEqual(run.location, "castle_town")
        self.assertEqual(run.optional_count, 1)
        run.town_shops(returning=True)
        self.assertEqual(sum(r["action"] == "borrow_fire_bat_dragon" for r in run.steps), 1)
        self.assertEqual(run.optional_count, 1)

    def test_wilson_uses_trials_and_reports_unavailable_empty_sample(self):
        self.assertIsNone(normal_052.wilson(0, 0))
        low, high = normal_052.wilson(0, 500)
        self.assertAlmostEqual(low, 0)
        self.assertLess(high, .01)
        self.assertEqual(normal_052.wilson(250, 500), normal_052.wilson(250, 500))

    def test_before_escort_branch_uses_055_reborrow_only_after_report(self):
        run = route_v2.MeasurementRun(self.pack, "hero", 53, archetypes.ARCHETYPES["P3"],
                                     difficulty="normal", effective=True,
                                     branches={"escort_order": "borrow_before_escort"})
        run.session["world_state"] = {"scene_id": "cave_prism_tree", "location_id": "cave_prism_tree"}
        run.session["flags"].update(cleared_cave_prism_tree=True, cleared_cave_crystal_corridor=True,
                                    cleared_cave_heat_corridor=True, met_mina=True, mina_waiting=True,
                                    borrowed_fire_bat_dragon=True, asked_to_borrow_fire_bat_dragon=True)
        run.hook("after_tree")
        run.session["world_state"] = {"scene_id": "castle_town", "location_id": "castle_town"}
        run.town_shops(returning=True)
        actions = [r["action"] for r in run.steps]
        self.assertLess(actions.index("report_mina_safe"), actions.index("borrow_fire_bat_dragon_again"))
        self.assertTrue(run.session["flags"]["asked_to_borrow_fire_bat_dragon_again"])
        run.town_shops(returning=True)
        self.assertEqual(sum(r["action"] == "borrow_fire_bat_dragon_again" for r in run.steps), 1)

    def test_engine_soft_defeat_is_recorded_as_loss_but_route_can_continue(self):
        for fight in (battle_v3.fight, battle_v3.fast_fight):
            for encounter, expected in (("mansion_corridor", True), ("goblin_fort_fourth", False)):
                with self.subTest(fight=fight.__name__, encounter=encounter):
                    session = self.session("hero", 1)
                    session["world_state"] = {"scene_id": encounter, "location_id": encounter}
                    session["character"]["hp"] = 1
                    for enemy in session["scenario_pack"]["enemies"]:
                        enemy["hp"] = enemy["max_hp"] = 10000
                    rng = random.Random(52)
                    with patch.object(combat, "random", rng), patch.object(state, "random", rng):
                        result = fight(session, "attack_only", rng)
                    self.assertEqual(result["status"], "defeat")
                    self.assertEqual(result["continue"], expected)
                    self.assertEqual(session["character"]["hp"], 1 if expected else 0)
                    if expected:
                        self.assertEqual(state.current_location_id(session), "festival_town")

    def test_f6_real_p3_seed_continues_after_mansion_loss(self):
        # Pin the pre-tuning numerical fixture for this historical F6 seed.
        pack = deepcopy(self.pack)
        pack["combat_rules"].pop("elite_percentage_round_cap", None)
        raw = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        originals = {e["id"]: e for e in raw["enemies"]}
        for enemy in pack["enemies"]:
            enemy["combat"].pop("basic_attack_weight", None)
            enemy["skills"] = deepcopy(originals[enemy["id"]].get("skills", []))
            if enemy["id"] == "prism_tree":
                enemy["resistances"] = deepcopy(originals[enemy["id"]]["resistances"])
                enemy["resistance_cycle"] = deepcopy(originals[enemy["id"]]["resistance_cycle"])
        guards = next(l for l in pack["locations"] if l["id"] == "goblin_fort_first_second")["combat"]
        guards["encounter_class"] = "elite"
        guards.pop("encounter_modifiers", None)
        pack["progression"].update({'exp_table': {'2': 20, '3': 50, '4': 90, '5': 140, '6': 200, '7': 280, '8': 380},
         'exp_rewards': {'trash': 5,
                         'elite': 15,
                         'boss': 40,
                         'unclassified': 5,
                         'quest': 10,
                         'scripted_loss': 0,
                         'guest': 0},
         'level_gains': {'hero': {'max_hp': 5,
                                  'max_mp': 1,
                                  'max_sp': 2,
                                  'attributes': {'str': 2, 'end': 1}},
                         'cleric': {'max_hp': 5,
                                    'max_mp': 2,
                                    'max_sp': 1,
                                    'attributes': {'wis': 2, 'int': 1}},
                         'mage': {'max_hp': 3,
                                  'max_mp': 3,
                                  'max_sp': 1,
                                  'attributes': {'int': 2, 'wis': 1}},
                         'thief': {'max_hp': 4,
                                   'max_mp': 1,
                                   'max_sp': 2,
                                   'attributes': {'dex': 2, 'str': 1}}}})
        enemy_fields = {'slime': {'combat.basic_attack.damage': '1d6'},
         'ignis': {'hp': 168, 'max_hp': 168, 'skills.@id=fire_breath.damage': '1d21'},
         'goblin': {'combat.basic_attack.damage': '1d6'},
         'goblin_archer': {'combat.basic_attack.damage': '1d6'},
         'hobgoblin': {'combat.basic_attack.damage': '1d6'},
         'forest_wolf': {'combat.basic_attack.damage': '1d12'},
         'slime_king': {'hp': 80, 'max_hp': 80, 'combat.basic_attack.damage': '1d10'},
         'goblin_king': {'hp': 56, 'max_hp': 56, 'combat.basic_attack.damage': '1d24'},
         'fire_slime': {'combat.basic_attack.damage': '1d6'},
         'fire_elemental': {'combat.basic_attack.damage': '2d10'},
         'ice_elemental': {'combat.basic_attack.damage': '1d16'},
         'frost_dire_wolf': {'hp': 48, 'max_hp': 48, 'combat.basic_attack.damage': '1d12'},
         'draco_human': {'hp': 25,
                         'max_hp': 25,
                         'skills.@id=sword_flash.damage': '1d8+5',
                         'skills.@id=ice_blade.damage': '1d8+4'},
         'draco_dragon': {'hp': 220, 'max_hp': 220},
         'heat_lizard': {'combat.basic_attack.damage': '2d5+1'},
         'ruby_golem': {'skills.@id=ruby_fist.damage': '1d12'},
         'sapphire_moth': {'combat.basic_attack.damage': '1d3'},
         'emerald_spider': {'combat.basic_attack.damage': '1d3'},
         'prism_tree': {'hp': 130,
                        'max_hp': 130,
                        'combat.defense': 2,
                        'skills.@id=crystal_rain.damage': '1d14'},
         'ash_wraith': {'skills.@id=ash_embrace.damage': '1d64', 'skills.@id=resentment.damage': '1d64'}}
        for enemy in pack["enemies"]:
            for path, value in enemy_fields.get(enemy["id"], {}).items():
                parts = path.split(".")
                node = enemy
                for part in parts[:-1]:
                    node = next(row for row in node if row["id"] == part[4:]) if part.startswith("@id=") else node[part]
                node[parts[-1]] = value
        result = route_v2.trial(pack, "hero", 4295220851872844824, archetypes.ARCHETYPES["P3"],
                               difficulty="normal", effective=True, measure=False,
                               passive_table=archetypes.default_passive_choices("hero"),
                               branches={"fire_seed": "accept", "merchant": "pay"})
        self.assertNotEqual(result["failed_at"], "mansion_corridor")
        mansion = next(b for b in result["battles"] if b["encounter"] == "mansion_corridor")
        self.assertEqual(mansion["status"], "defeat")
        self.assertTrue(mansion["continue"])
        self.assertEqual(result["battles"][-1]["encounter"], "draco_battle")


if __name__ == "__main__":
    unittest.main()
