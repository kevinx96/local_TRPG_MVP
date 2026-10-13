from __future__ import annotations

import json
import random
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import combat, state
from scripts.balance import checkpoints, route, sim


class BalancePass3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cls.cp = checkpoints.generate()

    def test_overrides_merge_without_mutating_class_targets(self):
        targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
        original = deepcopy(targets)
        row = dict(encounter="merchant_battle", encounter_class="boss", character="hero",
                   policy="heuristic", defense_mode="flat", win_rate=.7, hp_left_mean=.8, rounds_median=3)
        self.assertEqual(sim.check_results([row], targets), [])
        row["win_rate"] = .9
        self.assertEqual([v["metric"] for v in sim.check_results([row], targets)], ["win_rate"])
        row.update(policy="attack_only", win_rate=.3)
        self.assertEqual(sim.check_results([row], targets)[0]["metric"], "attack_only_win_rate")
        self.assertEqual(targets, original)

    def test_rare_consumables_reserved_by_both_policies(self):
        for encounter in ("dark_forest_loc", "forest_wolves", "slime_king_battle"):
            session = sim.prepare_session(self.pack, encounter, "hero", self.cp)
            combat.ensure_combat_started(session)
            for policy in ("heuristic", "greedy"):
                # Avoid the boss's opening defense to exercise offensive selection.
                session["combat"]["round"] = 3
                action, _ = sim.choose_action(session, policy)
                self.assertEqual(action["type"] == "item", encounter == "slime_king_battle")
        session = sim.prepare_session(self.pack, "dark_forest_loc", "hero", self.cp)
        combat.ensure_combat_started(session)
        item = next(i for i in session["character"]["inventory"] if i.get("id") == "holy_water")
        item.pop("rare", None)
        action = next(a for a in combat.combat_actions(session) if a["type"] == "item" and a["name"] == item["name"])
        self.assertTrue(sim.rare_consumable(session, action))
        item["combat"].update(element="physical", damage="1", accuracy=100)
        action.update(element="physical", damage="1", accuracy=100)
        enemy = session["combat"]["enemies"][0]
        enemy["combat"]["defense"] = 0
        enemy["combat"]["evade"] = 0
        enemy["max_hp"] = 100
        self.assertFalse(sim.rare_consumable(session, action))
        action["damage"] = "30"
        self.assertTrue(sim.rare_consumable(session, action))
        action["damage"] = "1"
        item["rare"] = True
        self.assertTrue(sim.rare_consumable(session, action))
        item["combat"]["consumable"] = False
        self.assertFalse(sim.rare_consumable(session, action))

    def test_upgrades_replace_legacy_duplicates_and_keep_order(self):
        for cid in ("hero", "mage", "thief"):
            session = checkpoints.fresh_session(deepcopy(self.pack), cid)
            actor = session["character"]
            template = next(c for c in self.pack["characters"] if c["id"] == cid)
            for s in template["level_skills"]:
                old = deepcopy(s)
                old["name"] = s.get("replaces", s["name"])
                actor["skills"].append(old)
            actor["level"] = 5
            state._unlock_level_skills(session, restoring=True)
            for s in template["level_skills"]:
                self.assertEqual(sum(x.get("id") == s["id"] for x in actor["skills"]), 1)
                self.assertFalse(any(x["name"] == s.get("replaces") for x in actor["skills"]))
            self.assertEqual(actor["skills"][0]["id"], template["level_skills"][0]["id"])
            before = deepcopy(actor)
            state._unlock_level_skills(session, restoring=True)
            self.assertEqual(actor, before)

    def load_saved(self, session):
        temporary_root = checkpoints.ROOT / ".tmp-test"
        temporary_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as directory, patch.object(state, "SAVE_DIR", Path(directory)):
            Path(directory, "balance.json").write_text(json.dumps(session), encoding="utf-8")
            return state.load_session("balance")

    def test_old_save_backfill_and_clear_event_order(self):
        for cleared_before in (False, True):
            session = checkpoints.fresh_session(deepcopy(self.pack), "mage")
            session["character"]["level"] = 5
            session["character"]["skills"] = []
            up = {"kind": "level_up", "data": {"level": 5}}
            clear = {"kind": "skills_cleared", "data": {"removed": 2}}
            session["event_log"] = [clear, up] if cleared_before else [up, clear]
            loaded = self.load_saved(session)
            self.assertEqual(len(loaded["character"]["skills"]), 2 if cleared_before else 0)
        session["event_log"] = [{"kind": "level_up", "data": {"level": 3}}, clear, up]
        loaded = self.load_saved(session)
        self.assertEqual([s["unlock_level"] for s in loaded["character"]["skills"]], [5])
        session["event_log"] = []
        loaded = self.load_saved(session)
        self.assertEqual(len(loaded["character"]["skills"]), 2)
        session["event_log"] = [clear]
        self.assertEqual(self.load_saved(session)["character"]["skills"], [])
        session["event_log"] = []
        session["character"].pop("level")
        self.assertEqual(self.load_saved(session)["character"]["skills"], [])

    def test_clear_tombstone_survives_event_log_truncation_and_level_up(self):
        session = checkpoints.fresh_session(deepcopy(self.pack), "mage")
        state.apply_state_delta(session, {"flags_set": ["reached_village"]})
        state.apply_state_delta(session, {"clear_skills": True})
        session["event_log"] = []
        state.apply_state_delta(session, {"flags_set": ["nest_event_seen"]})
        self.assertEqual([s["unlock_level"] for s in session["character"]["skills"]], [5])
        self.assertEqual([s["unlock_level"] for s in self.load_saved(session)["character"]["skills"]], [5])

    def test_route_seed_determinism_and_resource_continuity(self):
        first = route.simulate_route(self.pack, self.cp, "hero", n=4, seed=17)
        self.assertEqual(first, route.simulate_route(self.pack, self.cp, "hero", n=4, seed=17))
        self.assertEqual(sum(first["failure_counts"].values()) + first["completion_rate"] * 4, 4)
        pack = deepcopy(self.pack)
        for enemy in pack["enemies"]:
            if enemy["id"] == "slime":
                enemy.update(hp=1, max_hp=1)
        session = checkpoints.fresh_session(pack, "hero")
        checkpoints.replay_step(session, "go_dark_forest:success")
        session["character"]["hp"] = 12
        session["character"]["mp"] = 0
        with patch.object(combat, "random", random.Random(1)):
            one = route.fight(session, "heuristic", random.Random(1))
            two = route.fight(session, "heuristic", random.Random(2))
        self.assertEqual(two["before"], one["after_resolution"])
        self.assertEqual(two["before"]["mp"], 0)
        self.assertLess(two["before"]["hp"], session["character"]["max_hp"])

    def test_route_consumption_failure_and_scripted_defeat(self):
        session = sim.prepare_session(self.pack, "slime_king_battle", "mage", self.cp)
        with patch.object(combat, "random", random.Random(7)):
            result = route.fight(session, "greedy", random.Random(7))
        self.assertGreater(sum(result["consumables"].values()), 0)
        self.assertLess(result["after_combat"]["inventory"].get("聖水", 0), 2)
        session = checkpoints.fresh_session(deepcopy(self.pack), "hero")
        for source in self.cp["encounters"]["xanxus_battle"]["characters"]["hero"]["sources"]:
            checkpoints.replay_step(session, source["step"])
        with patch.object(combat, "random", random.Random(1)):
            result = route.fight(session, "heuristic", random.Random(1))
        self.assertEqual(result["status"], "defeat")
        self.assertTrue(result["continue"])
        self.assertGreater(session["character"]["hp"], 0)
        self.assertNotEqual(state.current_location_id(session), "xanxus_battle")

    def test_route_applies_real_recovery_and_level_up(self):
        session = checkpoints.fresh_session(deepcopy(self.pack), "hero")
        sources = self.cp["encounters"]["slime_ambush_one"]["characters"]["hero"]["sources"]
        for source in sources[:-1]:
            checkpoints.replay_step(session, source["step"])
        session["character"].update(hp=1, mp=0, sp=0)
        checkpoints.replay_step(session, sources[-1]["step"])
        self.assertEqual(session["character"]["hp"], session["character"]["max_hp"])
        pack = deepcopy(self.pack)
        king = next(e for e in pack["enemies"] if e["id"] == "slime_king")
        king.update(hp=1, max_hp=1)
        session = checkpoints.fresh_session(pack, "hero")
        for source in self.cp["encounters"]["slime_king_battle"]["characters"]["hero"]["sources"]:
            checkpoints.replay_step(session, source["step"])
        session["character"].update(hp=10, mp=0)
        with patch.object(combat, "random", random.Random(17)):
            result = route.fight(session, "attack_only", random.Random(17))
        self.assertEqual(result["status"], "victory")
        self.assertEqual(result["after_resolution"]["level"], 1)
        self.assertEqual(state.current_location_id(session), "elf_spring")
        checkpoints.replay_step(session, "continue_from_elf_spring")
        checkpoints.replay_step(session, "@victory")
        self.assertEqual(session["character"]["level"], 2)
        self.assertEqual(session["character"]["hp"], session["character"]["max_hp"])


    def test_route_final_victory_ending_counts_as_completion(self):
        pack = deepcopy(self.pack)
        enemy = next(e for e in pack["enemies"] if e["id"] == "ignis")
        enemy.update(hp=1, max_hp=1)
        session = checkpoints.fresh_session(pack, "mage")
        for source in self.cp["encounters"]["dragon_valley_loc"]["characters"]["mage"]["sources"]:
            checkpoints.replay_step(session, source["step"])
        with patch.object(combat, "random", random.Random(17)):
            result = route.fight(session, "heuristic", random.Random(17))
        self.assertEqual(result["status"], "victory")
        self.assertIsNone(session["game_over"])
        self.assertEqual(state.current_location_id(session), "ignis_last_breath")
        self.assertTrue(result["continue"])


if __name__ == "__main__":
    unittest.main()
