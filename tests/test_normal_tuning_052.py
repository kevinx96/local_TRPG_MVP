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

    def test_f6_engine_defeat_returns_to_town_and_route_can_continue(self):
        # Isolate the recoverable encounter from changing shopping and hazard RNG.
        run = route_v2.MeasurementRun(deepcopy(self.pack), "hero", 20261022,
                                     archetypes.ARCHETYPES["P3"], difficulty="normal", effective=True)
        run.session["world_state"] = {"scene_id": "general_mansion", "location_id": "mansion_corridor"}
        actor = run.session["character"]
        actor.update(hp=1, max_hp=100, inventory=[], equipment=[], skills=[], statuses=[])
        actor["attributes"]["dex"] = 0
        run.session["companion"] = None
        run.session["combat_start_requested"] = True
        run.settle()
        self.assertEqual(run.battles[-1]["status"], "defeat")
        self.assertTrue(run.battles[-1]["continue"])
        self.assertEqual(run.location, "festival_town")
        self.assertEqual(run.session["character"]["hp"], 1)
        self.assertFalse(run.session.get("game_over"))
        self.assertTrue(route_v2.class_aware.available_actions(run.session))


if __name__ == "__main__":
    unittest.main()
