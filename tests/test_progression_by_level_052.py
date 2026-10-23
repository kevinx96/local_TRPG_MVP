from __future__ import annotations

import unittest
from copy import deepcopy

from host import combat, difficulty, progression, state
from scripts.balance import checkpoints, snapshots_v3
from scripts.scenario import normal_tuning_052


class ByLevel052Tests(unittest.TestCase):
    def setUp(self):
        self.base = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        self.pack = difficulty.apply_difficulty(self.base, "normal")
        self.gains = self.pack["progression"]["level_gains"]["hero"]
        self.gains["by_level"] = {"2": {"attributes": {"dex": 1}},
                                  "3": {"max_hp": 7, "attributes": {"str": 0}},
                                  "4": {"max_mp": 0, "attributes": {"dex": 2}}}

    def test_multilevel_rewards_merge_overrides_and_record_resolved_gains(self):
        session = checkpoints.fresh_session(self.pack, "hero", "normal", effective=True)
        before = deepcopy(session["character"])
        config = deepcopy(self.pack["progression"])
        progression.reward(session, config["exp_table"]["4"], "test")
        actor = session["character"]
        self.assertEqual(actor["level"], 4)
        self.assertEqual(actor["max_hp"], before["max_hp"] + self.gains["max_hp"] * 2 + 7)
        self.assertEqual(actor["max_mp"], before["max_mp"] + self.gains["max_mp"] * 2)
        self.assertEqual(actor["attributes"]["dex"], before["attributes"]["dex"] + 3)
        self.assertEqual(actor["attributes"]["str"], before["attributes"]["str"] + self.gains["attributes"]["str"] * 2)
        self.assertEqual(actor["attributes"]["end"], before["attributes"]["end"] + self.gains["attributes"]["end"] * 3)
        self.assertEqual([actor[r] for r in ("hp", "mp", "sp")], [actor["max_"+r] for r in ("hp", "mp", "sp")])
        events = [e["data"]["gains_per_level"] for e in session["event_log"] if e["kind"] == "level_up"]
        self.assertEqual(len(events), 3)
        self.assertTrue(all("by_level" not in e for e in events))
        self.assertEqual(events[1]["attributes"]["str"], 0)
        self.assertEqual(self.pack["progression"], config)

    def test_probe_roundtrip_preserves_nonlevel_gains_and_source(self):
        session = checkpoints.fresh_session(self.pack, "hero", "normal", effective=True)
        progression.reward(session, self.pack["progression"]["exp_table"]["6"], "test")
        session["character"]["max_hp"] += 9
        session["character"]["attributes"]["dex"] += 3
        before = deepcopy(session)
        down = snapshots_v3.at_level(session, 2, {})
        restored = snapshots_v3.at_level(down, 6, {})
        for field in ("max_hp", "max_mp", "max_sp", "attributes"):
            self.assertEqual(restored["character"][field], before["character"][field])
        self.assertEqual(session, before)

    def test_defaults_and_non_exp_modes_are_unchanged(self):
        config = deepcopy(self.pack["progression"])
        expected = deepcopy(config["level_gains"]["hero"])
        expected.pop("by_level")
        self.assertEqual(progression.gains_at_level(config, "hero", 5), expected)
        config["level_model"] = "milestone"
        self.assertEqual(progression.gains_at_level(config, "hero", 3), expected)
        for mode in ("baby", "normal"):
            session = checkpoints.fresh_session(self.pack, "hero", mode, effective=True)
            session["scenario_pack"] = deepcopy(self.pack)
            if mode == "normal":
                session["scenario_pack"]["progression"]["level_model"] = "milestone"
            before = deepcopy(session)
            progression.reward(session, 10000, "test")
            self.assertEqual(session, before)

    def test_validation_rejects_invalid_overrides_and_baby_filters_them(self):
        entry = next(e for e in self.base["difficulty_overlays"]["normal"] if e["entity"] == "progression" and e["path"] == "level_gains")
        entry["set"] = deepcopy(self.pack["progression"]["level_gains"])
        difficulty.validate_difficulty(self.base)
        self.assertNotIn("level_gains", difficulty.apply_difficulty(self.base, "baby")["progression"])
        for invalid in ({"1": {}}, {"9": {}}, {"02": {}}, {"2": {"max_hp": -1}},
                        {"2": {"max_hp": True}}, {"2": {"attributes": {"dex": .5}}},
                        {"2": {"attributes": []}}, {"2": {"unknown": 1}}, [], {"2": {"by_level": {}}}):
            with self.subTest(invalid=invalid):
                candidate = deepcopy(self.base)
                row = next(e for e in candidate["difficulty_overlays"]["normal"] if e["entity"] == "progression" and e["path"] == "level_gains")
                row["set"]["hero"]["by_level"] = invalid
                with self.assertRaises(ValueError):
                    difficulty.validate_difficulty(candidate)

    def test_tuning_migration_is_pure_idempotent_and_baby_unchanged(self):
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            base = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(name))
            original = deepcopy(base)
            updated = normal_tuning_052.migrate(base)
            self.assertEqual(base, original)
            self.assertEqual(normal_tuning_052.migrate(updated), updated)
            before = difficulty.apply_difficulty(base, "baby")
            after = difficulty.apply_difficulty(updated, "baby")
            # apply_difficulty retains the inactive overlay as authoring metadata.
            before.pop("difficulty_overlays")
            after.pop("difficulty_overlays")
            after["meta"]["content_revision"] = before["meta"]["content_revision"]
            self.assertEqual(after, before)
            for key in base:
                if key not in {"meta", "difficulty_overlays"}:
                    self.assertEqual(updated[key], base[key], key)

    def test_tuned_full_level_evasion_meets_approved_bands(self):
        pack = difficulty.apply_difficulty(normal_tuning_052.migrate(self.base), "normal")
        for cid, band in (("hero", (6, 9)), ("cleric", (5, 8)), ("mage", (8, 11)), ("thief", (20, 20))):
            session = checkpoints.fresh_session(pack, cid, "normal", effective=True)
            progression.reward(session, pack["progression"]["exp_table"]["8"], "test")
            evade = combat.actor_evade(session, session["character"])
            self.assertLessEqual(band[0], evade)
            self.assertLessEqual(evade, band[1])


if __name__ == "__main__":
    unittest.main()
