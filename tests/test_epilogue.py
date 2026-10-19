from __future__ import annotations

import unittest

from host import state
from scripts.balance import checkpoints
from scripts.scenario.epilogues import EPILOGUES


def _session(filename="dragon_rpg.json"):
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(filename))
    return checkpoints.fresh_session(pack, "hero")


def _end(session, ending, flags=()):
    state.apply_state_delta(session, {"flags_set": list(flags), "game_over": {"title": "冒険完了", "ending": ending, "reason": "fixture"}})
    return session["game_over"]["epilogue"]


def _text(identifier):
    return next(entry["text"] for entry in EPILOGUES if entry["id"] == identifier)


class EpilogueTests(unittest.TestCase):
    def test_both_packs_carry_the_same_epilogues(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            with self.subTest(pack=filename):
                entries = _session(filename)["scenario_pack"]["epilogues"]
                self.assertEqual([{k: v for k, v in entry.items() if k != "npc_ids_required"}
                                  for entry in entries if entry["id"] not in {"town_blood", "defeated_xanxus"}], EPILOGUES)
                self.assertEqual(sum(entry["id"] == "town_blood" for entry in entries), 1)
                self.assertEqual(sum(entry["id"] == "defeated_xanxus" for entry in entries), 1)

    def test_lines_follow_earned_flags_including_flags_set_in_the_final_delta(self):
        lines = _end(_session(), "draco_defeated_with_ignis",
                     ["ignis_purified", "mina_quest_done", "saved_gald", "riku_returned", "returned_lost_goblin_box"])
        for identifier in ("king_confession", "ignis_returns", "mina_done", "gald_saved", "riku_returned", "goblin_returned"):
            self.assertIn(_text(identifier), lines)
        for identifier in ("mina_alone", "gald_abandoned", "riku_abandoned", "goblin_betrayed", "xanxus_core"):
            self.assertNotIn(_text(identifier), lines)

    def test_choices_with_bad_outcomes_are_remembered(self):
        lines = _end(_session(), "ignis_defeated", ["abandoned_gald", "riku_abandoned", "betrayed_lost_goblin", "met_mina"])
        for identifier in ("gald_abandoned", "riku_abandoned", "goblin_betrayed", "mina_alone"):
            self.assertIn(_text(identifier), lines)
        self.assertNotIn(_text("king_confession"), lines)

    def test_order_follows_the_data(self):
        lines = _end(_session(), "draco_defeated", ["saved_gald", "mina_quest_done"])
        order = [entry["text"] for entry in EPILOGUES]
        self.assertEqual(lines, sorted(lines, key=order.index))

    def test_defeat_endings_have_no_epilogue(self):
        self.assertEqual(_end(_session(), "draco_victory", ["saved_gald", "mina_quest_done"]), [])


if __name__ == "__main__":
    unittest.main()
