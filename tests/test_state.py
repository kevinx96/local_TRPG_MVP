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
                    "inventory_add": [{"name": "古い鍵", "description": "錆びた鍵", "effect": "扉を開ける"}],
                    "current_scene": "玄関ホール",
                },
                "choices": [
                    {"text": "奥へ進む", "preview": "先が見える", "risk": "判定不要"},
                ],
            },
        )
        state.save_session(session)
        loaded = state.load_session(public["id"])

        self.assertGreaterEqual(roll["total"], 2)
        self.assertEqual(loaded["character"]["hp"], 18)
        # Inventory items are now objects
        inv_names = [i["name"] if isinstance(i, dict) else i for i in loaded["character"]["inventory"]]
        self.assertIn("古い鍵", inv_names)
        self.assertEqual(loaded["current_scene"], "玄関ホール")
        self.assertEqual(loaded["messages"][-1]["speaker"], "GM")

    def test_public_session_removes_prompt(self):
        scenario = self.tmp_path / "scenario.txt"
        scenario.write_text("秘密の資料", encoding="utf-8")

        public = state.create_session(str(scenario))

        self.assertNotIn("scenario_prompt", public)

    def test_public_session_sanitizes_saved_assistant_text(self):
        scenario = self.tmp_path / "scenario.txt"
        scenario.write_text("秘密の資料", encoding="utf-8")

        public = state.create_session(str(scenario))
        session = state.load_session(public["id"])
        state.add_assistant_message(
            session,
            "王の間。\n\n次の選択肢:\n1. 扉を調べる。\n\nGM本文の後には次のJSON形式で状態を出力してください。",
        )

        sanitized = state.public_session(session)

        self.assertEqual(sanitized["messages"][-1]["text"], "王の間。")
        self.assertEqual(sanitized["choices"][0]["text"], "扉を調べる")

    def test_create_session_needs_opening_flag(self):
        """Session is created with needs_opening=True and no messages."""
        scenario = self.tmp_path / "opening.txt"
        scenario.write_text("あなたはGMです。", encoding="utf-8")

        public = state.create_session(str(scenario))

        self.assertTrue(public.get("needs_opening"))
        self.assertEqual(len(public["messages"]), 0)
        self.assertEqual(public["current_scene"], "第1章：王の間")

    def test_inventory_items_are_objects(self):
        """Default inventory items should be dicts with name/description/effect/quantity."""
        scenario = self.tmp_path / "inv.txt"
        scenario.write_text("テスト", encoding="utf-8")

        public = state.create_session(str(scenario))
        inv = public["character"]["inventory"]
        for item in inv:
            self.assertIsInstance(item, dict)
            self.assertIn("name", item)
            self.assertIn("description", item)
            self.assertIn("effect", item)
            self.assertIn("quantity", item)
            self.assertGreaterEqual(item["quantity"], 1)

    def test_character_name_override(self):
        scenario = self.tmp_path / "name.txt"
        scenario.write_text("テスト", encoding="utf-8")

        public = state.create_session(str(scenario), {"name": "エリナ"})
        self.assertEqual(public["character"]["name"], "エリナ")

    def test_item_quantity_increment_and_decrement(self):
        """Adding a duplicate item increments quantity; removing decrements it."""
        scenario = self.tmp_path / "qty.txt"
        scenario.write_text("テスト", encoding="utf-8")

        public = state.create_session(str(scenario))
        session = state.load_session(public["id"])

        # Add another 薬草 — should increment quantity to 2
        state.apply_gm_payload(
            session, "テスト",
            {"state_delta": {"inventory_add": [{"name": "薬草"}]}},
        )
        herb = next(i for i in session["character"]["inventory"] if i["name"] == "薬草")
        self.assertEqual(herb["quantity"], 2)

        # Remove one 薬草 — should decrement to 1
        state.apply_gm_payload(
            session, "テスト",
            {"state_delta": {"inventory_remove": ["薬草"]}},
        )
        herb = next(i for i in session["character"]["inventory"] if i["name"] == "薬草")
        self.assertEqual(herb["quantity"], 1)

        # Remove last 薬草 — should drop entirely
        state.apply_gm_payload(
            session, "テスト",
            {"state_delta": {"inventory_remove": ["薬草"]}},
        )
        names = [i["name"] for i in session["character"]["inventory"]]
        self.assertNotIn("薬草", names)

    def test_choices_normalization(self):
        """Choices should be normalized to have text/preview/risk."""
        scenario = self.tmp_path / "ch.txt"
        scenario.write_text("テスト", encoding="utf-8")

        public = state.create_session(str(scenario))
        session = state.load_session(public["id"])
        state.apply_gm_payload(
            session,
            "テスト",
            {
                "choices": [
                    "単純な文字列選択",
                    {"text": "構造化選択", "preview": "結果", "risk": "危険"},
                ],
            },
        )
        self.assertEqual(len(session["choices"]), 2)
        self.assertEqual(session["choices"][0]["text"], "単純な文字列選択")
        self.assertEqual(session["choices"][1]["risk"], "危険")

    def test_gold_delta_and_text_inference(self):
        scenario = self.tmp_path / "gold.txt"
        scenario.write_text("テスト", encoding="utf-8")

        public = state.create_session(str(scenario))
        session = state.load_session(public["id"])
        state.apply_gm_payload(
            session,
            "国王は支度金として50ゴールドを与える。",
            {"state_delta": {}},
        )

        self.assertEqual(session["character"]["gold"], 50)

        state.apply_gm_payload(
            session,
            "追加の報酬として10ゴールドを与える。",
            {"state_delta": {"gold_change": 10}},
        )

        self.assertEqual(session["character"]["gold"], 60)

    def test_advance_choice_infers_next_scene(self):
        scenario = self.tmp_path / "advance.txt"
        scenario.write_text("テスト", encoding="utf-8")

        public = state.create_session(str(scenario))
        session = state.load_session(public["id"])
        state.add_player_message(session, "城を出てスライムの森へ向かう")
        state.apply_gm_payload(
            session,
            "アルスは王城の門をくぐり、森へ向けて歩き出した。",
            {"state_delta": {}},
        )

        self.assertEqual(session["current_scene"], "第2章：スライムの森")
        self.assertEqual(session["choices"][0]["text"], "鉄の剣でスライムを攻撃する")


if __name__ == "__main__":
    unittest.main()
