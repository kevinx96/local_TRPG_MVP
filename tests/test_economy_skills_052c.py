from __future__ import annotations

import random
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from host import app, combat, difficulty, free_actions, state, status_effects
from scripts.balance import archetypes, checkpoints, class_aware, normal_052, policy_v3, probes_v3, route_v2, snapshots_v3


class EconomySkills052cTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cls.pack = difficulty.apply_difficulty(cls.base, "normal")

    def session(self, character="hero"):
        value = checkpoints.fresh_session(deepcopy(self.pack), character, "normal", effective=True)
        value["world_state"] = {"scene_id": "forest_wolves", "location_id": "forest_wolves"}
        value["combat_start_requested"] = True
        combat.ensure_combat_started(value)
        value["character"].update(hp=100, max_hp=100, statuses=[], skills=[], equipment=[], inventory=[])
        enemy = value["combat"]["enemies"][0]
        enemy.update(hp=1000, max_hp=1000, statuses=[], skills=[], resistances={"physical": 0})
        value["combat"]["enemies"] = [enemy]
        return value

    def test_cleansing_items_match_tags_and_remove_status_through_engine(self):
        value = self.session()
        state.apply_state_delta(value, {"inventory_add": [{"id": "antidote_herb"}, {"id": "burn_salve"}]})
        status_effects.apply(value, value["character"], {"id": "poison", "stacks": 2},
                             value["combat"]["enemies"][0], random.Random(1))
        with patch.dict(policy_v3.PARAMETERS, {"cleanse_hp_ratio": 0}):
            action, target = policy_v3.choose(value, "heuristic_v3")
        self.assertEqual(action["id"], "antidote_herb")
        combat.perform_combat_action(value, action["type"], action["id"], target, rng=random.Random(1))
        self.assertFalse(any(s["id"] == "poison" for s in value["character"].get("statuses", [])))

    def test_haze_and_powder_are_legal_telegraph_responses(self):
        for item in ("haze_ball", "blinding_powder"):
            value = self.session()
            state.apply_state_delta(value, {"inventory_add": [{"id": item}]})
            enemy = value["combat"]["enemies"][0]
            enemy["charging"] = {"release_round": value["combat"]["round"]}
            pairs = [(a, t) for a, t in policy_v3.legal_pairs(value) if a["id"] == item]
            with patch("scripts.balance.budget.phase_moments", return_value={"expected_damage": 60}):
                action, target = policy_v3.telegraph_response(value, pairs)
            self.assertEqual(action["id"], item)
            self.assertFalse(combat._ability_disabled_reason(value, "item", item,
                              policy_v3.ability_for(value, action), target))

    def test_prayer_cleanses_relevant_debuff_and_respects_server_legality(self):
        value = self.session("cleric")
        bell = next(i for i in self.pack["items"] if i["id"] == "purifying_bell")
        value["character"]["skills"] = deepcopy(bell["combat"]["grants_skills"])
        status_effects.apply(value, value["character"], {"id": "poison", "stacks": 3},
                             value["combat"]["enemies"][0], random.Random(1))
        with patch.dict(policy_v3.PARAMETERS, {"cleanse_hp_ratio": 0}):
            action, target = policy_v3.choose(value, "heuristic_v3")
        self.assertEqual(action["id"], "purify_prayer")
        combat.perform_combat_action(value, "skill", action["id"], target, rng=random.Random(1))
        self.assertFalse(any(s["id"] == "poison" for s in value["character"].get("statuses", [])))

    def test_m9_current_burn_matches_engine_tick_and_is_pure(self):
        value = self.session()
        status_effects.apply(value, value["character"], "burn", value["combat"]["enemies"][0], random.Random(1))
        before, rng = deepcopy(value), random.getstate()
        result = normal_052.opening_moments(value)
        copy = deepcopy(value)
        hp = copy["character"]["hp"]
        status_effects.tick(copy, copy["character"], random.Random(1))
        self.assertEqual(result["current_dot_damage"], hp-copy["character"]["hp"])
        self.assertEqual(result["expected_damage"], result["direct_expected_damage"]+result["current_dot_damage"])
        self.assertEqual(value, before)
        self.assertEqual(random.getstate(), rng)

    def test_level8_defaults_use_post_ignis_results(self):
        rows = []
        for definition in self.pack["class_progression"]:
            for choices in probes_v3.combinations(self.pack, definition["id"]):
                terminal = int(choices["8"] == definition["passive_groups"][-1]["options"][1])
                rows.append(dict(character=definition["id"], choices=choices, n=2, ignis_wins=2,
                                 ignis_rate=1, completion_rate=terminal, outcomes=[1, 1],
                                 completed_outcomes=[terminal, terminal], reached_levels={"8": 2}))
        result = probes_v3.choose_defaults(self.pack, rows, postgame=True)
        for definition in self.pack["class_progression"]:
            self.assertEqual(result["characters"][definition["id"]]["choices"]["8"],
                             definition["passive_groups"][-1]["options"][1])

    def run_at_trap(self, character, prototype):
        run = route_v2.MeasurementRun(deepcopy(self.pack), character, 1, archetypes.ARCHETYPES[prototype],
                                       difficulty="normal", effective=True, measure=False)
        run.session["world_state"] = {"scene_id": "goblin_fort_scene", "location_id": "goblin_fort_second_choice"}
        return run

    def test_hazards_p0_takes_p2_requires_advantage_and_only_once(self):
        for character, prototype, expected in (("hero", "P0b", True), ("hero", "P2", False), ("thief", "P2", True)):
            run = self.run_at_trap(character, prototype)
            run.hazards_here()
            self.assertEqual("hazard_054_01" in run.hazard_attempts, expected)
            before = deepcopy(run.session)
            run.hazards_here()
            self.assertEqual(run.session, before)

    def test_p2_buys_cures_without_changing_baby_or_p0(self):
        for mode, prototype, expected in (("normal", "P2", True), ("normal", "P0b", False), ("baby", "P2", False)):
            run = route_v2.MeasurementRun(deepcopy(self.base), "hero", 1, archetypes.ARCHETYPES[prototype], difficulty=mode)
            run.session["world_state"] = {"scene_id": "castle_town", "location_id": "item_shop"}
            run.session["character"]["gold"] = 1000
            run.shop_here()
            cures = {p["item"] for p in run.purchases} & {"antidote_herb", "burn_salve", "smelling_salts"}
            self.assertEqual(bool(cures), expected)
            if expected:
                self.assertEqual(len(cures), 3)

    def test_shadow_cooldown_rejected_by_api_and_free_action_then_recovers(self):
        value = self.session("thief")
        thief = next(c for c in self.pack["characters"] if c["id"] == "thief")
        value["character"]["skills"] = deepcopy(thief["skills"])
        value["character"].update(sp=30, max_sp=30)
        combat.perform_combat_action(value, "skill", "hide_in_shadow", rng=random.Random(2))
        before = deepcopy(value)
        with patch.object(app, "load_session", return_value=value), patch.object(app, "save_session") as save:
            with self.assertRaises(HTTPException) as error:
                app.api_combat_action("test", app.CombatActionRequest(action_type="skill", action_id="hide_in_shadow"))
            self.assertEqual(error.exception.status_code, 409)
            save.assert_not_called()
        result = free_actions.adjudicate(value, {"kind": "existing", "action_id": "hide_in_shadow",
            "operation": "", "item_id": "", "target_id": "", "advance": False, "approach": "", "reply": ""})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(value, before)
        combat.perform_combat_action(value, "defend", rng=random.Random(2))
        self.assertTrue(next(a for a in combat.combat_actions(value) if a["id"] == "hide_in_shadow")["enabled"])
        baby = difficulty.apply_difficulty(self.base, "baby")
        old = next(s for c in baby["characters"] if c["id"] == "thief" for s in c["skills"] if s["id"] == "hide_in_shadow")
        self.assertNotIn("cooldown", old)

    def test_level8_probe_requires_post_ignis_flag_not_just_level(self):
        value = checkpoints.fresh_session(deepcopy(self.pack), "hero", "normal", effective=True)
        value = snapshots_v3.at_level(value, 8, archetypes.default_passive_choices("hero"))
        value["world_state"] = {"scene_id": "cave_prism_tree", "location_id": "cave_prism_tree"}
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/"checkpoints.json"
            for postgame in (False, True):
                value["flags"] = {"defeated_ignis": True} if postgame else {}
                source.write_text(json.dumps({"encounters": {"cave_prism_tree": {"characters": {
                    "hero": {"snapshot": snapshots_v3.capture(value)}}}}}), encoding="utf-8")
                job = ("normal_passive_probes", checkpoints.DEFAULT_SCENARIO, "hero", 1, 20261020,
                       {"difficulty": "normal", "checkpoint_path": str(source), "postgame_passives": True})
                with patch.object(probes_v3, "battles", return_value=[{"won": 1, "rounds": 1}]):
                    rows = probes_v3.run_job(job)
                self.assertEqual(any(r["level"] == 8 for r in rows), postgame)


if __name__ == "__main__":
    unittest.main()
