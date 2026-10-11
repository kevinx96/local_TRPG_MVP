from __future__ import annotations

import json
import random
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import combat, state
from scripts.balance import budget, checkpoints, sim


class BalancePassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)

    def session(self, character="hero"):
        return checkpoints.fresh_session(deepcopy(self.pack), character)

    def test_milestones_trigger_once_and_fill_all_resources(self):
        for cid in ("hero", "cleric", "mage", "thief"):
            session = self.session(cid)
            actor = session["character"]
            original = deepcopy(actor)
            for milestone in self.pack["milestones"]:
                actor.update(hp=1, mp=0, sp=0)
                state.apply_state_delta(session, {"flags_set": [milestone["trigger_flag"]]})
                self.assertEqual(actor["level"], milestone["level"])
                gains = milestone["gains"][cid]
                for r in ("hp", "mp", "sp"):
                    self.assertEqual(actor[f"max_{r}"], original[f"max_{r}"] + (actor["level"] - 1) * gains[f"max_{r}"])
                    self.assertEqual(actor[r], actor[f"max_{r}"])
                after = deepcopy(actor)
                state.apply_state_delta(session, {"flags_set": [milestone["trigger_flag"]]})
                state.apply_state_delta(session, {"flags_unset": [milestone["trigger_flag"]]})
                state.apply_state_delta(session, {"flags_set": [milestone["trigger_flag"]]})
                self.assertEqual(actor, after)
            self.assertEqual(len(session["completed_milestones"]), 4)
            self.assertEqual(len([e for e in session["event_log"] if e["kind"] == "level_up"]), 4)

    def test_legacy_flags_do_not_award_retroactive_growth(self):
        session = self.session()
        del session["character"]["level"]
        milestone = self.pack["milestones"][0]
        session["flags"][milestone["trigger_flag"]] = True
        original = deepcopy(session["character"])
        state.apply_state_delta(session, {})
        self.assertEqual(session["character"], {**original, "level": 1})
        state.apply_state_delta(session, {"flags_unset": [milestone["trigger_flag"]]})
        state.apply_state_delta(session, {"flags_set": [milestone["trigger_flag"]]})
        self.assertEqual(session["character"]["max_hp"], original["max_hp"])
        state.apply_state_delta(session, {"flags_set": [self.pack["milestones"][1]["trigger_flag"]]})
        self.assertEqual(session["character"]["max_hp"], original["max_hp"] + 5)

    def test_loading_legacy_save_refreshes_mechanics_without_growth(self):
        pack = deepcopy(self.pack)
        pack["meta"]["content_revision"] = "2026-09-08-death-game-over"
        cleric = next(c for c in pack["characters"] if c["id"] == "cleric")
        cleric["combat"]["basic_attack"]["damage"] = "1d4+str/4"
        session = checkpoints.fresh_session(pack, "cleric")
        session["scenario_path"] = str(checkpoints.DEFAULT_SCENARIO)
        del session["character"]["level"]
        session["flags"][pack["milestones"][0]["trigger_flag"]] = True
        session["companion"] = {"id": "blue_robed_mage", "round_start_effects": [{"kind": "heal_player", "amount": "8"}]}
        serialized = json.dumps(session)
        original_read = Path.read_text
        original_exists = Path.exists
        with patch.object(Path, "read_text", lambda p, *a, **kw: serialized if p.name == "balance.json" else original_read(p, *a, **kw)), \
             patch.object(Path, "exists", lambda p: p.name == "balance.json" or original_exists(p)), \
             patch.object(state, "save_session"):
            loaded = state.load_session("balance")
            state.apply_state_delta(loaded, {})
        self.assertEqual(loaded["character"]["level"], 1)
        self.assertEqual(loaded["character"]["max_hp"], 18)
        self.assertEqual(loaded["character"]["combat"]["basic_attack"]["damage"], "1d8+wis/4")
        self.assertEqual(loaded["companion"]["round_start_effects"][0]["every_n_rounds"], 2)

    def test_forest_branch_victory_and_round_trip(self):
        session = self.session()
        for step in checkpoints.proposed_routes()["forest_wolves"] + ["@victory"]:
            checkpoints.replay_step(session, step)
        self.assertEqual(session["character"]["level"], 2)
        restored = json.loads(json.dumps(session))
        hp = restored["character"]["max_hp"]
        state.apply_state_delta(restored, {})
        self.assertEqual(restored["character"]["max_hp"], hp)

    def test_model_cannot_award_levels_caps_or_milestone_flags(self):
        session = self.session()
        delta = dict(level=5, max_hp=999, max_mp=999, max_sp=999,
                     flags_set=[self.pack["milestones"][0]["trigger_flag"]], completed_milestones=[])
        self.assertEqual(state.sanitize_model_state_delta(session, delta), {})
        state.apply_state_delta(session, state.sanitize_model_state_delta(session, delta))
        self.assertEqual(session["character"]["level"], 1)

    def test_periodic_proportional_heal_and_guest_disable(self):
        session = sim.prepare_session(self.pack, "dark_forest_loc", "hero")
        session["companion"] = {"name": "ワーロック", "round_start_effects": [
            {"kind": "heal_player", "every_n_rounds": 2, "max_hp_ratio": .15}]}
        combat.ensure_combat_started(session)
        session["character"].update(hp=1, max_hp=30)
        for turn, expected in [(1, 1), (2, 6), (3, 6), (4, 11)]:
            session["combat"]["round"] = turn
            combat._apply_round_start_effects(session, random.Random(1))
            self.assertEqual(session["character"]["hp"], expected)
        session["combat"]["encounter"]["disable_companion"] = True
        combat._apply_round_start_effects(session, random.Random(1))
        self.assertEqual(session["character"]["hp"], 11)

    def test_new_character_skips_levels_without_late_double_growth(self):
        session = self.session()
        state.apply_state_delta(session, {"flags_set": [self.pack["milestones"][1]["trigger_flag"]]})
        self.assertEqual(session["character"]["level"], 3)
        self.assertEqual(session["character"]["max_hp"], 30)
        actor = deepcopy(session["character"])
        state.apply_state_delta(session, {"flags_set": [self.pack["milestones"][0]["trigger_flag"]]})
        self.assertEqual(session["character"], actor)

    def test_candidates_are_simulation_only_and_level_gated(self):
        cp = checkpoints.generate()
        pack_before = deepcopy(self.pack)
        for level in (3, 5):
            for cid in ("hero", "cleric", "mage", "thief"):
                entries = [c for c in json.loads(sim.SKILL_CANDIDATES.read_text(encoding="utf-8"))["candidates"]
                           if c["character"] == cid and c["level"] == level]
                self.assertEqual({c["variant"] for c in entries}, {"A", "B"})
        early = sim.prepare_session(self.pack, "dark_forest_loc", "mage", cp, skill_variant="A")
        late = sim.prepare_session(self.pack, "dragon_valley_loc", "mage", cp, skill_variant="A")
        self.assertFalse(any("_lv" in s["id"] for s in early["character"]["skills"]))
        self.assertEqual(sum("_lv" in s["id"] for s in late["character"]["skills"]), 2)
        self.assertEqual(self.pack, pack_before)

    def test_exact_budget_respects_min_damage_misses_and_defense(self):
        actor = {"combat": {"defense": 2, "evade": 10}}
        self.assertAlmostEqual(budget.attack_expectation({"damage": "1d4", "accuracy": 90}, {}, actor, {}), 1.0)
        self.assertAlmostEqual(sum(budget.formula_distribution("2d6+str/2", {"attributes": {"str": 8}}).values()), 1)
        cp = checkpoints.generate()
        targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
        rows = budget.incoming_damage_budget(self.pack, cp, targets)
        self.assertEqual(len(rows), 101)

    def test_multi_enemy_spread_uses_existing_target(self):
        targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
        row = dict(encounter="forest_wolves", encounter_class="elite", policy="heuristic", defense_mode="flat",
                   hp_left_mean=.4, rounds_median=5, enemy_count=2)
        rows = [{**row, "character": "hero", "win_rate": .95}, {**row, "character": "mage", "win_rate": .75}]
        self.assertNotIn("class_spread", [v["metric"] for v in sim.check_results(rows, targets)])
        for row in rows:
            row["enemy_count"] = 1
        self.assertIn("class_spread", [v["metric"] for v in sim.check_results(rows, targets)])


if __name__ == "__main__":
    unittest.main()
