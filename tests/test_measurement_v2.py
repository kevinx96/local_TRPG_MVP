from __future__ import annotations

import contextlib
import io
import json
import math
import random
import unittest
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

from host import combat, state
from spring_legacy_balance import legacy_spring_balance_pack
from scripts.balance import archetypes, budget, checkpoints, class_aware, report, reproduction_v2, route, route_v2, sim


class MeasurementV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = legacy_spring_balance_pack(state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO))
        cls.cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
        cls.human = reproduction_v2.berserker_checkpoints(cls.pack)

    def session(self):
        session = reproduction_v2.checkpoint_session(self.pack, self.human["profiles"]["human_berserker"])
        combat.ensure_combat_started(session)
        return session

    def test_archetypes_are_explicit_and_validate_budgets(self):
        archetypes.validate()
        self.assertEqual(set(archetypes.ARCHETYPES), {"P0a", "P0b", "P1", "P2", "P3", "P2s", "P0g"})
        self.assertEqual(len(archetypes.P0B.optional_interactions), 3)
        self.assertEqual(archetypes.P0A.sidequests, ())
        for value in archetypes.ARCHETYPES.values():
            self.assertEqual(value.recovery_threshold, .30)
            self.assertEqual(value.rest_rule, "free_hp70")
        for bad in (replace(archetypes.P0B, optional_limit=2),
                    replace(archetypes.P0A, recovery_threshold=1.1),
                    replace(archetypes.P0A, equipment_rule="invented")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                archetypes.validate([bad])
        with self.assertRaises(ValueError):
            archetypes.validate([archetypes.P0A, archetypes.P0A])

    def test_all_archetypes_are_enabled_after_046b_acceptance(self):
        self.assertEqual(route_v2.SUPPORTED_ARCHETYPES, tuple(archetypes.ARCHETYPES))

    def test_level_model_and_passive_extension_contracts(self):
        session = self.session()
        before = deepcopy(session)
        self.assertEqual(archetypes.MilestoneLevelModel().observe(session, "dragon_valley_loc"), 5)
        self.assertEqual(session, before)
        for mode in ("first", "battle_best", "enumerate"):
            self.assertEqual(archetypes.PassivePicker(mode).pick([]), [])
        self.assertEqual(archetypes.PassivePicker("first").pick(["a", "b"]), ["a"])
        self.assertEqual(archetypes.PassivePicker("battle_best").pick(["a", "b"], {"a": 1, "b": 2}), ["b"])
        picker = archetypes.PassivePicker("enumerate")
        self.assertEqual(picker.combinations([["a", "b"], ["c", "d"]]), [["a", "c"], ["a", "d"], ["b", "c"], ["b", "d"]])
        self.assertEqual(picker.combinations([]), [[]])
        self.assertEqual(picker.combinations([[]]), [])

    def test_best_free_uses_weakness_and_rejects_paid_attacks(self):
        session = self.session()
        actor = session["character"]
        actor["skills"].append({"id": "paid", "name": "渾身斬り", "kind": "attack", "damage": "999", "accuracy": 100, "cost": 1, "cost_type": "mp"})
        actor["inventory"].append({"id": "rare", "name": "火球術の巻物", "quantity": 1,
                                   "combat": {"kind": "damage", "damage": "999", "accuracy": 100, "consumable": True}})
        self.assertEqual(sim.choose_action(session, "best_free")[0]["id"], "ice_charm")
        actor["skills"].append({"id": "free", "name": "渾身斬り", "kind": "attack", "damage": "999", "accuracy": 100, "cost": 0})
        self.assertEqual(sim.choose_action(session, "best_free")[0]["id"], "free")

    def test_best_free_healing_threshold_is_strict_and_configurable(self):
        session = self.session()
        actor = session["character"]
        actor["hp"] = 12
        self.assertNotEqual(sim.choose_action(session, "best_free")[0].get("kind"), "heal")
        actor["hp"] = 11
        self.assertEqual(sim.choose_action(session, "best_free")[0]["id"], "healing_scroll")
        actor["hp"] = 12
        self.assertEqual(sim.choose_action(session, "best_free", recovery_threshold=.5)[0].get("kind"), "heal")

    def test_expected_damage_uses_discrete_rounding(self):
        session = self.session()
        actor, enemy = session["character"], session["combat"]["enemies"][0]
        ability = {"damage": "1d4", "element": "ice", "accuracy": 100}
        rules = combat._combat_rules(session)
        chance = (100 - enemy.get("combat", {}).get("evade", 0)) / 100
        expected = chance * sum(combat.damage_after_defense(raw, combat._resistance_multiplier(enemy, "ice"), combat._actor_defense(enemy), rules) for raw in range(1, 5)) / 4
        self.assertAlmostEqual(sim.free_action_damage(ability, actor, enemy, rules), expected)

    def test_moments_include_misses_zero_damage_and_ai_mixture(self):
        session = self.session()
        session["character"]["equipment"] = []
        session["character"]["combat"] = {"defense": 0, "evade": 0}
        enemy = {"id": "test", "hp": 10, "max_hp": 10, "skills": [
            {"id": "attack", "kind": "attack", "damage": "10", "accuracy": 50, "ai_weight": 1},
            {"id": "guard", "name": "護衛の構え", "kind": "defend", "ai_weight": 1}]}
        session["combat"]["enemies"] = [enemy]
        before = deepcopy(session)
        stats = budget.phase_moments(session)
        self.assertEqual(session, before)
        self.assertAlmostEqual(stats["expected_damage"], 2.5)
        self.assertAlmostEqual(stats["variance"], 18.75)
        self.assertAlmostEqual(stats["cv"], math.sqrt(18.75) / 2.5)
        conditioned = budget.phase_moments(session, damaging_only=True)
        self.assertAlmostEqual(conditioned["expected_damage"], 5)
        self.assertAlmostEqual(conditioned["variance"], 25)
        session["combat"]["enemies"].append({**deepcopy(enemy), "id": "test2"})
        self.assertAlmostEqual(budget.phase_moments(session)["variance"], 37.5)
        enemy["skills"] = [enemy["skills"][1]]
        session["combat"]["enemies"] = [enemy]
        self.assertEqual(budget.phase_moments(session)["expected_damage"], 0)
        self.assertIsNone(budget.phase_moments(session)["cv"])

    def test_scheduled_true_damage_does_not_spend_uses(self):
        session = sim.prepare_session(self.pack, "dark_forest_loc", "hero", self.cp)
        combat.ensure_combat_started(session)
        before = deepcopy(session)
        self.assertEqual(budget.phase_moments(session)["expected_damage"], 8)
        self.assertEqual(budget.phase_moments(session)["cv"], 0)
        self.assertEqual(session, before)
        session["combat"]["round"] = 2
        self.assertLess(budget.phase_moments(session)["expected_damage"], 8)

    def test_document_checkpoint_and_separate_probes(self):
        entry = self.human["profiles"]["human_berserker"]
        self.assertEqual((entry["level"], entry["attributes"]["str"], entry["max_hp"], entry["gold"]), (5, 20, 40, 706))
        self.assertEqual({i["id"]: i["quantity"] for i in entry["inventory"] if i.get("id")}.get("healing_scroll"), 9)
        self.assertTrue(entry["flags"]["fire_bat_empowered"])
        self.assertIn("原始存档已丢失", entry["source"])
        self.assertEqual(self.human["unresolved_inventory"][0]["distinct_types"], 4)
        self.assertIsNone(self.human["profiles"]["无同伴"]["companion"])
        self.assertIn("氷鉄の大剣", self.human["profiles"]["P0b + 氷鉄の大剣"]["equipment"])
        self.assertEqual(route_v2.sustain(self.session()), 6)
        standard = sim.prepare_session(self.pack, "dragon_valley_loc", "hero", self.human)
        self.assertTrue(standard["flags"]["fire_bat_empowered"])
        expected = .55 * (.4 * sum(max(1, round(raw * .7) - 1) for raw in range(1, 22)) / 21
                          + .6 * sum(max(1, raw - 1) for raw in range(1, 22)) / 21)
        self.assertAlmostEqual(budget.phase_moments(self.session())["expected_damage"], expected)

    def test_instrumentation_preserves_outcomes_and_rng(self):
        entry = self.human["profiles"]["human_berserker"]
        original = reproduction_v2.checkpoint_session(self.pack, entry)
        measured = reproduction_v2.checkpoint_session(self.pack, entry)
        rng1, rng2 = random.Random(46), random.Random(46)
        with patch.object(combat, "random", rng1), patch.object(state, "random", rng1):
            expected = route.fight(original, "best_free", rng1)
        with patch.object(combat, "random", rng2), patch.object(state, "random", rng2):
            actual = route_v2.fight(measured, "best_free", rng2)
        self.assertEqual(actual["status"], expected["status"])
        self.assertEqual(rng1.getstate(), rng2.getstate())
        for stage in ("before", "after_combat", "after_resolution"):
            self.assertEqual({key: actual[stage][key] for key in expected[stage]}, expected[stage])
        self.assertEqual(actual["statuses"], [])
        self.assertEqual(actual["skill_usage"], {})

    def test_legacy_outputs_match_pre_edit_bytes(self):
        baseline = json.loads((checkpoints.ROOT / "eval/balance/046-legacy-output.json").read_text(encoding="utf-8"))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), patch.object(sim.time, "perf_counter", return_value=0):
            status = sim.main(["--check", "--encounters", "forest_wolves", "--characters", "hero", "--n", "3", "--seed", "46001"])
        self.assertEqual(status, baseline["sim_check_exit"])
        self.assertEqual(stdout.getvalue().encode("utf-8"), baseline["sim_check_stdout"].encode("utf-8"))
        actual = route.simulate_route(self.pack, self.cp, "hero", n=3, seed=46001, rest_policy="hp70")
        aware = class_aware.trial(self.pack, self.cp, "hero", sim.trial_seed(46001, "dragon_valley_loc", "hero", 0), quests=(), decisions="backbone")
        for value, key in ((actual, "route_hp70"), (aware, "class_aware_backbone")):
            self.assertEqual(json.dumps(value, ensure_ascii=False).encode("utf-8"), json.dumps(baseline[key], ensure_ascii=False).encode("utf-8"))

    def test_legacy_all_policy_selection_is_unchanged(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            sim.main(["--encounters", "forest_wolves", "--characters", "hero", "--policies", "all", "--n", "1"])
        self.assertEqual([r["policy"] for r in json.loads(output.getvalue())["rows"]], list(sim.LEGACY_POLICIES))
        matrix = report.run_job({"kind": "matrix", "mode": "flat", "scenario": str(checkpoints.DEFAULT_SCENARIO),
                                 "checkpoint": str(checkpoints.DEFAULT_CHECKPOINTS), "n": 1, "seed": 46001,
                                 "encounter": "forest_wolves", "character": "hero"})
        self.assertEqual([r["policy"] for r in matrix["rows"] if r["experiment"] == "matrix"], list(sim.LEGACY_POLICIES))

    def test_process_and_serial_results_are_byte_identical(self):
        jobs = [(checkpoints.DEFAULT_SCENARIO, a, "hero", 2, 46001) for a in ("P0a", "P0b")]
        serial = route_v2.run_jobs(jobs, 1)
        parallel = route_v2.run_jobs(jobs, 2)
        self.assertEqual(json.dumps(serial, ensure_ascii=False).encode("utf-8"), json.dumps(parallel, ensure_ascii=False).encode("utf-8"))
        for result in serial:
            self.assertLessEqual(result["optional_interactions"], 3)
            self.assertEqual(result["levels"]["castle"], 1)
            self.assertEqual(result["passives"], [])

    def test_gate_boundaries_keep_checkpoint_and_route_separate(self):
        profiles = {"human_berserker": {"rounds_median": 17, "sustain_coverage": 1.01}}
        rows = [{"archetype": "P0b", "character": "hero", "completion_rate": .90}]
        gates = reproduction_v2.gates(rows, profiles, [{"status": "pass"}])
        self.assertFalse(gates[0]["pass"])
        self.assertTrue(gates[1]["pass"])
        self.assertTrue(gates[2]["pass"])
        rows[0]["completion_rate"] = .90001
        profiles["human_berserker"].update(rounds_median=22, sustain_coverage=1)
        gates = reproduction_v2.gates(rows, profiles, [{"status": "fail"}])
        self.assertTrue(gates[0]["pass"])
        self.assertTrue(gates[1]["pass"])
        self.assertFalse(gates[2]["pass"])
        self.assertFalse(gates[3]["pass"])
        profiles["human_berserker"]["rounds_median"] = 22.01
        self.assertFalse(reproduction_v2.gates(rows, profiles, [])[1]["pass"])


if __name__ == "__main__":
    unittest.main()
