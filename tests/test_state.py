import tempfile
import unittest
from pathlib import Path

from host import state


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.original_save_dir = state.SAVE_DIR
        state.SAVE_DIR = self.tmp_path / "saves"

    def tearDown(self):
        state.SAVE_DIR = self.original_save_dir
        self.tmp.cleanup()

    def test_create_apply_and_persist_session(self):
        scenario = self.tmp_path / "scenario.txt"
        scenario.write_text("あなたはGMです。", encoding="utf-8")

        public = state.create_session(str(scenario))
        session = state.load_session(public["id"])
        state.add_player_message(session, "扉を開ける")
        roll = state.roll_dice(session, "2d6")
        state.apply_gm_payload(
            session,
            "冷たい風が吹き込む。",
            {
                "system_log": "罠によりHPが2減少。",
                "state_delta": {
                    "hp_change": -2,
                    "inventory_add": ["古い鍵"],
                    "current_scene": "玄関ホール",
                },
                "choices": ["奥へ進む"],
            },
        )
        state.save_session(session)
        loaded = state.load_session(public["id"])

        self.assertGreaterEqual(roll["total"], 2)
        self.assertEqual(loaded["character"]["hp"], 18)
        self.assertIn("古い鍵", loaded["character"]["inventory"])
        self.assertEqual(loaded["current_scene"], "玄関ホール")
        self.assertEqual(loaded["messages"][-1]["speaker"], "GM")

    def test_public_session_removes_prompt(self):
        scenario = self.tmp_path / "scenario.txt"
        scenario.write_text("秘密の資料", encoding="utf-8")

        public = state.create_session(str(scenario))

        self.assertNotIn("scenario_prompt", public)

    def test_create_session_adds_opening_message(self):
        scenario = self.tmp_path / "opening.txt"
        scenario.write_text("あなたはGMです。", encoding="utf-8")

        public = state.create_session(str(scenario))

        self.assertEqual(public["messages"][0]["role"], "assistant")
        self.assertEqual(public["messages"][0]["speaker"], "GM")
        self.assertIn("最初の行動", public["messages"][0]["text"])


if __name__ == "__main__":
    unittest.main()
