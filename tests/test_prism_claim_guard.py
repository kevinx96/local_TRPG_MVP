from __future__ import annotations

import json
import random
import unittest
from copy import deepcopy

from host import combat, free_actions, state
from scripts.balance import checkpoints, forest_v3, route, sim
from scripts.eval.requests import evaluation_config
from scripts.eval.snapshots import ROOT, load_snapshot
from scripts.eval.variants import VARIANTS


class PrismWeaknessTests(unittest.TestCase):
    def test_highest_multiplier_and_physical_fallback(self):
        for resistances, expected in (({"fire": .2, "ice": 1.5}, "ice"),
                                      ({"water": 1.2, "wind": 2}, "wind"),
                                      ({"arcane": 2}, "arcane"),
                                      ({"physical": 2, "ice": 1.5}, "physical"),
                                      ({"fire": .5, "ice": 1}, "physical"),
                                      ({"physical": .5, "fire": .25}, "physical"),
                                      ({}, "physical")):
            with self.subTest(resistances=resistances):
                actor = {"resistances": resistances}
                before = deepcopy(actor)
                self.assertEqual(combat.weakness_attack_element(actor), expected)
                self.assertEqual(actor, before)
        self.assertEqual(combat.counter_attack_element({"element": "fire"}), "water")
        self.assertEqual(combat.weakness_attack_element({"element": "fire"}), "physical")

    def test_item_multipliers_equipment_and_immunity(self):
        actor = {"resistances": {"ice": 2, "water": 1.5}, "inventory": [
            {"name": "氷の護符", "combat": {"kind": "passive", "requires_equipped": True,
             "damage_taken_multipliers": {"ice": .25, "arcane": 3}}}], "equipment": []}
        self.assertEqual(combat.weakness_attack_element(actor), "ice")
        actor["equipment"] = ["氷の護符"]
        self.assertEqual(combat.weakness_attack_element(actor), "arcane")
        actor["combat_immunities"] = ["arcane"]
        self.assertEqual(combat.weakness_attack_element(actor), "water")
        actor["inventory"].append({"combat": {"kind": "passive", "damage_taken_multipliers": {"water": .5}}})
        self.assertEqual(combat.weakness_attack_element(actor), "physical")

    def test_rotation_attack_resolution_and_estimate_agree(self):
        pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        session = checkpoints.fresh_session(pack, "hero")
        state.commit_world_position(session, location_id="cave_prism_tree")
        combat.ensure_combat_started(session)
        enemy = session["combat"]["enemies"][0]
        action = {"type": "attack", "element": "weakness", "damage": "10", "accuracy": 100}
        for turn, expected in ((1, "ice"), (3, "fire"), (5, "fire"), (7, "ice")):
            session["combat"]["round"] = turn
            combat._apply_round_start_effects(session, random.Random(1))
            self.assertEqual(combat.weakness_attack_element(enemy), expected)
            estimate = sim.expected_damage(action, session["character"], enemy, combat._combat_rules(session))
            before = enemy["hp"]
            combat._resolve_attack(session, session["character"], enemy, action, "player", random.Random(1))
            self.assertEqual(before - enemy["hp"], estimate)

    def test_optional_target_bounds_are_selected_without_changing_main(self):
        targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
        for optional, value, valid in ((False, .90, True), (False, .901, False),
                                       (True, .95, True), (True, .951, False),
                                       (False, .549, False), (True, .549, False)):
            result = {"encounters": [], "weapons": [], "routes": [
                {"character": "hero", "sidequests": optional, "completion_rate": value}]}
            self.assertEqual(not forest_v3.check_results(result, targets), valid)
        rows = [dict(route="dragon_valley_loc", character=c, policy="heuristic", completion_rate=.95)
                for c in forest_v3.CHARACTERS]
        self.assertEqual(route.check_results(rows, targets, target_key="route_targets_with_optional"), [])
        rows[0]["completion_rate"] = .951
        self.assertEqual(route.check_results(rows, targets, target_key="route_targets_with_optional")[0]["metric"],
                         "completion_rate")


class ClaimGuardTests(unittest.TestCase):
    def test_exact_suffix_hidden_evidence_action_and_default_isolation(self):
        session = load_snapshot("v2_scenario_report_no_evidence")
        config = evaluation_config({"backends": {"gemini": {"api_key": "fake"}}}, "gemini", "fixture", rpm=0)
        original = deepcopy(session)
        text = "証拠なら持っています。将軍こそ白竜です。"
        default, default_config = VARIANTS["default"].prepare(session, text, config)
        guarded, guarded_config = VARIANTS["guard_claims"].prepare(session, text, config)
        spec = (ROOT / "docs/specs/017-prism-weakness-and-claim-guard.md").read_text(encoding="utf-8")
        exact = spec.split("```\n", 1)[1].split("\n```", 1)[0]
        self.assertEqual(guarded[0]["content"], free_actions.PLAN_PROMPT + "\n" + exact)
        self.assertEqual(guarded[1:], default[1:])
        self.assertEqual(guarded_config, default_config)
        self.assertEqual(VARIANTS["default"].prepare(session, text, config)[0], default)
        self.assertEqual(session, original)
        self.assertNotIn("report_with_evidence", default[1]["content"])
