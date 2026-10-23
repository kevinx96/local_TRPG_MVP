from __future__ import annotations

from scripts.scenario.holy_sword_049 import migrate as holy_sword

import json
import unittest
from copy import deepcopy

from host import state
from scripts.balance import checkpoints
from scripts.scenario.checks_e import CHECKS, LINKS, OBSERVES, PACKS, apply

from scripts.scenario.spring_postgame import apply as apply_spring_postgame


class ChecksETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs = [json.loads(checkpoints.DEFAULT_SCENARIO.with_name(name).read_text(encoding="utf-8")) for name in PACKS]

    def actions(self, pack):
        return {action["id"]: (location["id"], action) for location in pack["locations"] for action in location.get("actions", [])}

    def test_idempotent_and_both_packs_match(self):
        for pack in self.packs:
            again = deepcopy(pack)
            apply(again)
            apply_spring_postgame(again)
            from scripts.scenario.levels_skills_v2 import migrate as levels
            again = holy_sword(levels(again))
            from scripts.scenario.mina_reborrow_055 import migrate as mina_reborrow
            again = mina_reborrow(again)
            from scripts.scenario.normal_tuning_052 import migrate as normal_tuning
            again = normal_tuning(again)
            # Legacy migrations reappend overrides; compare their full content in the source order.
            order = {(e["entity"], e["id"], e["path"]): i
                     for i, e in enumerate(pack["difficulty_overlays"]["normal"])}
            again["difficulty_overlays"]["normal"].sort(
                key=lambda e: order.get((e["entity"], e["id"], e["path"]), len(order)))
            self.assertEqual(again, pack)
        ids = {entry[0] for entry in CHECKS}
        first, second = (self.actions(pack) for pack in self.packs)
        self.assertEqual({k: v for k, v in first.items() if k in ids}, {k: v for k, v in second.items() if k in ids})

    def test_every_check_is_placed_with_skill_dc_and_texts(self):
        actions = self.actions(self.packs[0])
        for entry in CHECKS:
            location_id, action = actions[entry[0]]
            self.assertEqual(location_id, entry[1])
            self.assertEqual(action["roll"]["skill"], entry[3])
            self.assertIn(action["roll"]["dc"], (8, 10, 12, 14))
            self.assertTrue(action["result_texts"]["success"] and action["result_texts"]["failure"])
            self.assertEqual("once" in action, entry[0] != "turn_ash_wraiths")

    def test_links_reach_existing_checks_and_observations_exist(self):
        actions = self.actions(self.packs[0])
        for flag, (reason, targets, kind) in LINKS.items():
            for target in targets:
                conditions = actions[target][1]["roll"][kind]
                self.assertIn({"requirements": {"flag": flag}, "reason": reason}, conditions)
        objects = {(loc["id"], obj["id"]) for loc in self.packs[0]["locations"] for obj in loc.get("objects", [])}
        for entry in OBSERVES:
            self.assertIn((entry[0], entry[1]), objects)

    def test_scouting_flag_gives_advantage_in_the_check_card(self):
        session = checkpoints.fresh_session(deepcopy(self.packs[0]), "hero")
        state.apply_state_delta(session, {"current_location": "goblin_fort"}, allow_world_transition=True)
        session["flags"]["scouted_fort_patrol"] = True
        session["choices"] = state.fallback_choices_for_session(session)
        public = state.public_session(session)
        check = next(c["check"] for c in public["choices"] if c.get("check") and c["text"] == "見張りを迂回する")
        self.assertEqual(check["advantage"], "advantage")
        self.assertIn("見張りの交代を知っている", check["advantage_reasons"])


if __name__ == "__main__":
    unittest.main()
