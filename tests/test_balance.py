from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import unittest
from copy import deepcopy
from unittest.mock import patch

from host import combat, state
from host.difficulty import apply_difficulty
from spring_legacy_balance import legacy_spring_balance_pack
from scripts.balance import checkpoints, sim
from scripts.balance import report


class BalanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cls.checkpoints = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))

    def test_defense_formulas_and_original_defaults(self):
        for raw in range(21):
            for mult in (0, .5, 1, 1.5, 2):
                for defense in (0, 1, 5, 20):
                    original = 0 if mult <= 0 else max(1, round(raw * mult) - defense)
                    self.assertEqual(combat.damage_after_defense(raw, mult, defense, {}), original)
        self.assertEqual(combat.damage_after_defense(10, 1.5, 20, {"defense_mode": "floor"}), 4)
        self.assertEqual(combat.damage_after_defense(10, 1, 20, {"defense_mode": "floor", "floor_ratio": .5}), 5)
        self.assertEqual(combat.damage_after_defense(10, 1, 10, {"defense_mode": "ratio"}), 5)
        self.assertEqual(combat.damage_after_defense(10, 1, 10, {"defense_mode": "ratio", "k": 20}), 7)
        self.assertEqual(combat.damage_after_defense(10, 0, 0, {"defense_mode": "floor"}), 0)

    def test_actual_engine_uses_defense_mode_on_both_sides(self):
        for mode, expected in (("flat", 5), ("floor", 5), ("ratio", 8)):
            session = sim.prepare_session(self.pack, "dark_forest_loc", "hero", defense_mode=mode)
            combat.ensure_combat_started(session)
            actor, enemy = session["character"], session["combat"]["enemies"][0]
            actor["inventory"] = []
            for defender in (actor, enemy):
                defender.update(hp=100, max_hp=100, combat={"defense": 15})
                attacker = enemy if defender is actor else actor
                combat._resolve_attack(session, attacker, defender, {"damage": "20", "accuracy": 100}, "player", random.Random(1))
                self.assertEqual(defender["hp"], 100 - expected)

    def test_same_seed_and_inputs_are_unchanged(self):
        original = deepcopy(self.pack)
        kwargs = dict(n=15, seed=31, checkpoints=self.checkpoints)
        a = sim.simulate(self.pack, "forest_wolves", "mage", **kwargs)
        b = sim.simulate(self.pack, "forest_wolves", "mage", **kwargs)
        self.assertEqual(a, b)
        self.assertEqual(self.pack, original)

    def test_policy_only_uses_enabled_visible_actions_without_rng(self):
        session = sim.prepare_session(self.pack, "slime_king_battle", "hero", self.checkpoints)
        combat.ensure_combat_started(session)
        for policy in sim.POLICIES:
            visible = combat.combat_actions(session)
            with patch.object(combat, "_roll_formula", side_effect=AssertionError("policy must not roll")):
                action, target = sim.choose_action(session, policy)
            self.assertIn(action, visible)
            self.assertTrue(action["enabled"])
            self.assertNotEqual(action["type"], "flee")
            self.assertIn(target, [e["id"] for e in session["combat"]["enemies"]])
        with patch.object(combat, "combat_actions", return_value=[visible[0]]):
            self.assertEqual(sim.choose_action(session, "heuristic")[0], visible[0])

    def test_heuristic_heals_before_guard_and_greedy_respects_resistance(self):
        session = sim.prepare_session(self.pack, "slime_king_battle", "hero", self.checkpoints)
        combat.ensure_combat_started(session)
        session["character"]["hp"] = 1
        self.assertEqual(sim.choose_action(session, "heuristic")[0]["kind"], "heal")
        session["character"]["hp"] = session["character"]["max_hp"]
        self.assertEqual(sim.choose_action(session, "heuristic")[0]["kind"], "defend")
        actor = {"attributes": {"int": 16}}
        self.assertEqual(sim.formula_mean("2d6+int/4", actor), 11)
        enemy = {"combat": {"defense": 0}, "resistances": {"fire": 0}}
        attack = {"type": "skill", "kind": "attack", "damage": "2d6+int/4", "accuracy": 80, "element": "fire"}
        self.assertEqual(sim.expected_damage(attack, actor, enemy, {}), 0)
        attack["element"] = "ice"
        self.assertAlmostEqual(sim.expected_damage(attack, actor, enemy, {}), 8.8)

    def test_guest_scaling_and_companion_removed_at_village(self):
        session = sim.prepare_session(self.pack, "warlock_rescue_battle", "hero", self.checkpoints,
                                      stat_scaling={"hp_mult": 2, "attr_add": {"int": 1}})
        combat.ensure_combat_started(session)
        self.assertEqual(session["character"]["character_id"], "warlock")
        self.assertEqual(session["character"]["max_hp"], 200)
        self.assertEqual(session["character"]["attributes"]["int"], 101)
        self.assertEqual(sim.selected_characters(self.pack, "warlock_rescue_battle", ["all"]), ["warlock"])
        forest = sim.prepare_session(self.pack, "forest_wolves", "hero", self.checkpoints)
        village = sim.prepare_session(self.pack, "village_fire_slime", "hero", self.checkpoints)
        self.assertEqual(forest["companion"]["id"], "blue_robed_mage")
        self.assertIsNone(village["companion"])

    def test_checkpoints_regenerate_and_classifications_match(self):
        with patch.object(state, "load_scenario_pack", return_value=apply_difficulty(legacy_spring_balance_pack(self.pack), "baby")):
            generated = checkpoints.generate()
        expected = deepcopy(self.checkpoints)
        # 051 adds inert definitions and normal overlays; baby checkpoint payload stays frozen.
        expected["scenario_sha256"] = generated["scenario_sha256"]
        self.assertEqual(generated, expected)
        targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(name))
            for location in pack["locations"]:
                if location["id"] in targets["encounters"]:
                    self.assertEqual(location["combat"]["encounter_class"], targets["encounters"][location["id"]])
        self.assertEqual(set(self.checkpoints["encounters"]), set(targets["encounters"]))
        self.assertTrue(all(e["status"] == "proposed" for e in self.checkpoints["encounters"].values()))

    def test_check_detects_non_win_targets_and_class_spread(self):
        targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
        row = dict(encounter="forest_wolves", encounter_class="elite", character="hero", policy="heuristic",
                   defense_mode="flat", win_rate=.8, hp_left_mean=.9, rounds_median=2)
        violations = sim.check_results([row, {**row, "character": "mage", "win_rate": .5}], targets,
                                       check_resource_metrics=True)
        self.assertEqual({v["metric"] for v in violations}, {"win_rate", "hp_left", "rounds", "class_spread"})
        boundary = [dict(row, character="hero", win_rate=.90, hp_left_mean=.4, rounds_median=5),
                    dict(row, character="mage", win_rate=.75, hp_left_mean=.4, rounds_median=5)]
        self.assertEqual(sim.check_results(boundary, targets), [])

    def test_undead_game_over_is_not_misattributed_to_prior_attack(self):
        session = sim.prepare_session(self.pack, "merchant_battle", "mage", self.checkpoints)
        combat.ensure_combat_started(session)
        session["character"]["undead_parts"] = ["左腕", "右腕", "左脚", "右脚", "胴体"]
        combat._apply_undead_conversion(session, "zebok:1")
        self.assertEqual(sim.defeat_cause(session), "zebok:1:undead_archmage")

    def test_skill_unlock_resolves_existing_catalog_without_mutating_it(self):
        actor = deepcopy(self.pack["characters"][0])
        sim.scale_actor(actor, {"skill_unlocks": ["earth_spikes"]}, self.pack)
        self.assertIn("earth_spikes", [s["id"] for s in actor["skills"]])
        self.assertNotIn("earth_spikes", [s["id"] for s in self.pack["characters"][0]["skills"]])

    def test_grid_search_does_not_assume_monotonic_win_rates(self):
        job = dict(kind="search", scenario=str(checkpoints.DEFAULT_SCENARIO), checkpoint=str(checkpoints.DEFAULT_CHECKPOINTS),
                   encounter="forest_wolves", character="hero", mode="flat", n=2, seed=1, target=[.75, .9])
        with patch.object(sim, "simulate", side_effect=[{"win_rate": 1.0}, {"win_rate": .8}]) as run:
            result = report.run_job(job)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(result["minimum"]["hp_mult"], 1)
        self.assertEqual(result["minimum"]["attr_add"], 1)

    def test_spending_is_gross_not_net_resource_change(self):
        pack = deepcopy(self.pack)
        actor = next(c for c in pack["characters"] if c["id"] == "hero")
        actor.update(sp=1, max_sp=1, hp=100, max_hp=100, inventory=[], equipment=[],
                     combat={"basic_attack": {"damage": "1", "accuracy": 100}},
                     skills=[{"id": "power_slash", "name": "渾身斬り", "kind": "attack", "damage": "10",
                              "accuracy": 100, "cost": 1, "cost_type": "sp"}])
        enemy = next(e for e in pack["enemies"] if e["id"] == "slime")
        enemy.update(hp=30, max_hp=30, combat={"defense": 0}, resistances={}, skills=[])
        row = sim.simulate(pack, "dark_forest_loc", "hero", "greedy", n=1, seed=5)
        self.assertEqual(row["sp_spent_mean"], 3)
        self.assertEqual(row["mp_spent_mean"], 0)
        self.assertEqual(row["win_rate"], 1)

    def test_report_contains_all_sections_and_tied_worst_classes(self):
        targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
        results = []
        for encounter, cls in targets["encounters"].items():
            rows = []
            for mode in sim.MODES:
                for character in sim.selected_characters(self.pack, encounter, ["all"]):
                    row = dict(experiment="matrix", encounter=encounter, encounter_class=cls, character=character,
                               policy="heuristic", defense_mode=mode, n=1, win_rate=0.0, rounds_median=1,
                               hp_left_mean=None, healing_items_mean={}, mp_spent_mean=0, sp_spent_mean=0,
                               defeat_rounds={1: 1}, defeat_causes={"max_rounds": 1})
                    rows.append(row)
                    if mode == "flat":
                        rows.append({**row, "experiment": "without_companion"})
            results.append({"job": {"kind": "matrix"}, "rows": rows})
        meta = dict(n=1, seed=1, workers=1, elapsed_seconds=1, matrix_worker_seconds=1,
                    search_worker_seconds=0, fingerprint="fixture")
        output = report.markdown(results, meta, targets, self.checkpoints)
        for heading in ("1. flat", "2. floor", "3. 缩放", "4. 职业", "5. flat", "同伴对照"):
            self.assertIn(heading, output)
        for character in ("hero", "cleric", "mage", "thief"):
            self.assertIn(f"| forest_wolves | {character} | 0.000 | max_rounds (1) |", output)

    @unittest.skipUnless(os.environ.get("BALANCE_ENFORCE") == "1", "BALANCE_ENFORCE=1 required")
    def test_balance_enforced_cli(self):
        result = subprocess.run([sys.executable, "-m", "scripts.balance.sim", "--check", "--n", "10"],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
