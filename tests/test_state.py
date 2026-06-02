import json
import os
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from host import state
from host.gm_contract import split_visible_and_json


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp_root = Path.cwd() / ".tmp-test"
        self.tmp_root.mkdir(exist_ok=True)
        self.tmp_path = self.tmp_root / f"state-{uuid.uuid4().hex}"
        self.tmp_path.mkdir()
        self.original_save_dir = state.SAVE_DIR
        state.SAVE_DIR = self.tmp_path / "saves"

    def tearDown(self):
        state.SAVE_DIR = self.original_save_dir

    def write_pack(self) -> Path:
        path = self.tmp_path / "scenario.json"
        path.write_text(
            json.dumps(
                {
                    "meta": {
                        "title": "鍛冶の町",
                        "summary": "町を拠点に手掛かりを集める短い冒険。",
                        "language": "ja",
                        "initial_scene": "start",
                    },
                    "rules": ["プレイヤーの行動を代行しない。"],
                    "scenes": [
                        {
                            "id": "start",
                            "title": "広場",
                            "description": "冒険者は町の広場に立っている。",
                            "goals": ["依頼の準備を整える"],
                            "keywords": ["広場", "町"],
                            "location_ids": ["forge"],
                            "fallback_choices": [
                                {"text": "鍛冶屋へ向かう", "preview": "装備を整える", "risk": "判定不要"},
                            ],
                        },
                        {
                            "id": "forest",
                            "title": "森の入口",
                            "description": "薄暗い森の入口。",
                            "keywords": ["森", "入口"],
                            "fallback_choices": [
                                {"text": "森へ進む", "preview": "探索を始める", "risk": "1d20判定が必要"},
                            ],
                        },
                    ],
                    "locations": [
                        {
                            "id": "forge",
                            "title": "鍛造屋",
                            "description": "武具の修理と購入ができる店。",
                            "keywords": ["鍛造屋", "鍛冶屋", "forge", "武具", "修理"],
                        }
                    ],
                    "npcs": [
                        {
                            "id": "smith",
                            "name": "鍛冶師",
                            "description": "装備の状態を見抜く職人。",
                            "keywords": ["鍛造屋", "鍛冶屋", "職人"],
                        }
                    ],
                    "items": [
                        {
                            "id": "iron_shield",
                            "name": "鉄の盾",
                            "description": "手頃な防具。",
                            "keywords": ["鍛造屋", "鍛冶屋", "盾"],
                        }
                    ],
                    "clues": [
                        {
                            "id": "scar",
                            "title": "焦げ跡",
                            "description": "竜の炎に似た痕跡。",
                            "keywords": ["焦げ跡", "竜"],
                        }
                    ],
                    "fallback_choices": [
                        {"text": "周囲を調べる", "preview": "手掛かりを探す", "risk": "判定不要"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return path

    def test_create_session_from_structured_json_uses_initial_scene(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])

        self.assertEqual(session["current_scene"], "start")
        self.assertEqual(public["current_scene_title"], "広場")
        self.assertNotIn("scenario_pack", public)

    def test_scenario_pack_preserves_meta_extensions(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["meta"]["hybrid_mode"] = "full"
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        self.assertEqual(session["scenario_pack"]["meta"]["hybrid_mode"], "full")

    def test_load_config_merges_local_config_and_env_base_url(self):
        config_path = self.tmp_path / "config.json"
        local_path = self.tmp_path / "local_config.json"
        config_path.write_text(
            json.dumps({
                "active_backend": "ollama",
                "backends": {"ollama": {"base_url": "http://localhost:11434/v1", "model": "local"}},
            }),
            encoding="utf-8",
        )
        local_path.write_text(
            json.dumps({"backends": {"ollama": {"model": "remote-model"}}}),
            encoding="utf-8",
        )

        with patch.dict(os.environ, {"TRPG_OLLAMA_BASE_URL": "https://ollama.example.com"}, clear=False):
            config = state.load_config(config_path)

        self.assertEqual(config["backends"]["ollama"]["model"], "remote-model")
        self.assertEqual(config["backends"]["ollama"]["base_url"], "https://ollama.example.com/v1")

    def test_select_scenario_context_matches_keywords(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        context = state.select_scenario_context(session, "前往鍛造屋 / 鍛冶屋で修理する")

        self.assertEqual(context["current_scene"]["id"], "start")
        self.assertEqual([item["id"] for item in context["matched"]["locations"]], ["forge"])
        self.assertEqual([item["id"] for item in context["matched"]["npcs"]], ["smith"])
        self.assertEqual([item["id"] for item in context["matched"]["items"]], ["iron_shield"])
        self.assertEqual(context["matched"]["clues"], [])

    def test_model_choices_do_not_trigger_fallback(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])

        state.apply_gm_payload(
            session,
            "鍛冶師は新しい道を示した。",
            {
                "state_delta": {},
                "choices": [{"text": "地下水路を調べる", "preview": "独自分岐", "risk": "判定不要"}],
            },
        )

        self.assertEqual(session["choices"][0]["text"], "地下水路を調べる")
        self.assertFalse(any("choices fallback" in log["text"] for log in session["system_logs"]))

    def test_recovered_text_choices_do_not_trigger_fallback(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        visible, payload, warning = split_visible_and_json(
            "霧が晴れた。\n\n"
            "次の選択肢:\n"
            "1. 扉を調べる\n"
            "2. 鍛冶屋へ向かう\n"
        )

        state.apply_gm_payload(session, visible, payload, warning)

        self.assertEqual([choice["text"] for choice in session["choices"]], ["扉を調べる", "鍛冶屋へ向かう"])
        self.assertFalse(any("choices fallback" in log["text"] for log in session["system_logs"]))

    def test_missing_choices_uses_scenario_fallback(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])

        state.apply_gm_payload(session, "広場にはまだ情報が残っている。", {"state_delta": {}})

        self.assertEqual(session["choices"][0]["text"], "鍛冶屋へ向かう")
        self.assertTrue(any("choices fallback: model did not provide choices." in log["text"] for log in session["system_logs"]))

    def test_legacy_txt_scenario_still_builds_context(self):
        scenario = self.tmp_path / "legacy.txt"
        scenario.write_text("古い形式のシナリオ本文です。", encoding="utf-8")

        public = state.create_session(str(scenario))
        session = state.load_session(public["id"])
        messages = state.build_llm_messages(session, {"expression": "opening", "rolls": [], "total": 0}, "contract")

        self.assertEqual(session["current_scene"], "start")
        self.assertEqual(public["current_scene_title"], "開始")
        self.assertIn("シナリオコンテキスト", messages[1]["content"])
        self.assertIn("古い形式のシナリオ本文です。", messages[1]["content"])

    def test_build_llm_messages_uses_short_history_and_memory_summary(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        for index in range(4):
            state.add_player_message(session, f"行動{index}")
            state.add_assistant_message(session, f"結果{index}")

        messages = state.build_llm_messages(session, {"expression": "1d20", "rolls": [10], "total": 10}, "contract")

        roles = [message["role"] for message in messages]
        self.assertEqual(roles.count("user"), 2)
        self.assertEqual(roles.count("assistant"), 2)
        self.assertTrue(any("これまでの会話要約" in message["content"] for message in messages if message["role"] == "system"))
        self.assertFalse(any("行動0" in message["content"] for message in messages if message["role"] != "system"))

    def test_build_llm_messages_includes_player_action_history(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        state.add_player_message(session, "国王に話を聞く")
        state.add_assistant_message(session, "国王は頷いた。")
        state.add_player_message(session, "森へ向かう")

        messages = state.build_llm_messages(session, {"expression": "1d20", "rolls": [10], "total": 10}, "contract")
        action_history = next(message["content"] for message in messages if "プレイヤー行動履歴" in message["content"])

        self.assertIn("1. 国王に話を聞く", action_history)
        self.assertIn("2. 森へ向かう", action_history)

    def test_public_session_sanitizes_saved_assistant_text(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        state.add_assistant_message(
            session,
            "王の間。\n\n次の選択肢:\n1. 扉を調べる\n\nGM本文の後には次のJSON形式で状態を出力してください。",
        )

        sanitized = state.public_session(session)

        self.assertEqual(sanitized["messages"][-1]["text"], "王の間。")
        self.assertEqual(sanitized["choices"][0]["text"], "扉を調べる")

    def test_create_session_needs_opening_flag(self):
        public = state.create_session(str(self.write_pack()))

        self.assertTrue(public.get("needs_opening"))
        self.assertEqual(len(public["messages"]), 0)
        self.assertEqual(public["current_scene"], "start")

    def test_create_session_stores_gm_mode(self):
        public = state.create_session(str(self.write_pack()), gm_mode="full")
        session = state.load_session(public["id"])
        messages = state.build_llm_messages(session, {"expression": "opening", "rolls": [], "total": 0}, "contract")

        self.assertEqual(public["gm_mode"], "full")
        self.assertIn('"gm_mode": "full"', messages[2]["content"])

        fallback = state.create_session(str(self.write_pack()), gm_mode="unknown")
        self.assertEqual(fallback["gm_mode"], "semi")

    def test_full_mode_prefers_sibling_hybrid_pack(self):
        semi_path = self.write_pack()
        hybrid_path = semi_path.with_name("scenario_hybrid.json")
        hybrid = json.loads(semi_path.read_text(encoding="utf-8"))
        hybrid["meta"]["title"] = "Hybrid pack"
        hybrid_path.write_text(json.dumps(hybrid, ensure_ascii=False), encoding="utf-8")

        public = state.create_session(str(semi_path), gm_mode="full")
        session = state.load_session(public["id"])

        self.assertEqual(Path(session["scenario_path"]).name, "scenario_hybrid.json")
        self.assertEqual(public["scenario_title"], "Hybrid pack")

    def test_full_mode_uses_prepared_turn_context(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["scenes"][0]["hybrid"] = {
            "mode": "prepared_gm_turns",
            "prepared_turns": [
                {
                    "id": "opening",
                    "purpose": "opening",
                    "trigger_keywords": ["開始"],
                    "draft": {
                        "gm_text": "GM opening draft.",
                        "system_log": "opening",
                        "dice_type": "1d20",
                        "dice_dc": 10,
                        "state_delta": {},
                        "choices": [{"text": "鍛冶屋へ向かう", "preview": "", "risk": ""}],
                    },
                },
                {
                    "id": "forge_response",
                    "purpose": "choice_response",
                    "source_choice": "鍛冶屋へ向かう",
                    "trigger_keywords": ["鍛冶屋"],
                    "rewrite_notes": ["Keep this English note out of the LLM context."],
                    "draft": {
                        "gm_text": "GM forge draft.",
                        "system_log": "forge",
                        "dice_type": "1d20",
                        "dice_dc": 12,
                        "state_delta": {"current_scene": "start"},
                        "choices": [{"text": "剣を修理する", "preview": "", "risk": ""}],
                    },
                },
            ],
        }
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path), gm_mode="full")
        session = state.load_session(public["id"])
        state.add_player_message(session, "鍛冶屋へ向かう")

        messages = state.build_llm_messages(session, {"expression": "1d20", "rolls": [7], "total": 7}, "contract")
        combined = "\n".join(message["content"] for message in messages)

        self.assertIn("FULL/HYBRID", messages[1]["content"])
        self.assertIn("GM forge draft.", combined)
        self.assertNotIn("trigger_keywords", combined)
        self.assertNotIn("Keep this English note", combined)
        self.assertNotIn("forge_response", combined)
        self.assertNotIn('"matched"', combined)
        self.assertEqual(len(messages), 4)

    def test_inventory_items_are_objects(self):
        public = state.create_session(str(self.write_pack()))

        for item in public["character"]["inventory"]:
            self.assertIsInstance(item, dict)
            self.assertIn("name", item)
            self.assertIn("description", item)
            self.assertIn("effect", item)
            self.assertIn("quantity", item)
            self.assertGreaterEqual(item["quantity"], 1)

    def test_character_name_override(self):
        public = state.create_session(str(self.write_pack()), {"name": "エリス"})
        self.assertEqual(public["character"]["name"], "エリス")

    def test_item_quantity_increment_and_decrement(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])

        state.apply_gm_payload(session, "薬草を拾った。", {"state_delta": {"inventory_add": [{"name": "薬草"}]}})
        herb = next(i for i in session["character"]["inventory"] if i["name"] == "薬草")
        self.assertEqual(herb["quantity"], 2)

        state.apply_gm_payload(session, "薬草を使った。", {"state_delta": {"inventory_remove": ["薬草"]}})
        herb = next(i for i in session["character"]["inventory"] if i["name"] == "薬草")
        self.assertEqual(herb["quantity"], 1)

        state.apply_gm_payload(session, "薬草を使った。", {"state_delta": {"inventory_remove": ["薬草"]}})
        names = [i["name"] for i in session["character"]["inventory"]]
        self.assertNotIn("薬草", names)

    def test_malformed_inventory_add_is_ignored_or_normalized(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])

        state.apply_gm_payload(
            session,
            "道具を受け取った。",
            {
                "state_delta": {
                    "inventory_add": [
                        {},
                        {"name": ""},
                        {"item": "氷の護符", "quantity": "2"},
                        {"item_name": "古い鍵"},
                    ],
                },
            },
        )

        inventory = {item["name"]: item["quantity"] for item in session["character"]["inventory"]}
        self.assertEqual(inventory["氷の護符"], 2)
        self.assertEqual(inventory["古い鍵"], 1)
        self.assertNotIn("", inventory)

    def test_system_logs_are_state_events_not_protocol_warnings(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        state.apply_gm_payload(
            session,
            "国王は支度金として50ゴールドと薬草を手渡した。",
            {
                "state_delta": {
                    "hp_change": -2,
                    "gold_change": 50,
                    "inventory_add": [{"name": "薬草", "quantity": 1}],
                },
            },
            "GM応答のJSONを解析できませんでした。",
        )

        logs = [entry["text"] for entry in state.public_session(session)["system_logs"]]
        self.assertIn("HPが2減少しました。", logs)
        self.assertIn("50ゴールドを獲得しました。", logs)
        self.assertIn("薬草 x1を入手しました。", logs)
        self.assertNotIn("GM応答のJSONを解析できませんでした。", logs)

    def test_choices_normalization(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        state.apply_gm_payload(
            session,
            "分岐を提示する。",
            {
                "choices": [
                    "単純な文字列の選択",
                    {"text": "構造化選択", "preview": "結果", "risk": "危険"},
                ],
            },
        )

        self.assertEqual(len(session["choices"]), 2)
        self.assertEqual(session["choices"][0]["text"], "単純な文字列の選択")
        self.assertEqual(session["choices"][1]["risk"], "危険")

    def test_gold_delta_and_text_inference(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        state.apply_gm_payload(session, "国王は支度金として50ゴールドを与える。", {"state_delta": {}})

        self.assertEqual(session["character"]["gold"], 50)

        state.apply_gm_payload(session, "追加の報酬として10ゴールドを与える。", {"state_delta": {"gold_change": 10}})
        self.assertEqual(session["character"]["gold"], 60)

        session["character"]["gold"] = 0
        state.apply_gm_payload(session, "国王から支度金として50goldを受け取った。", {"state_delta": {"gold_change": 0}})
        self.assertEqual(session["character"]["gold"], 50)

    def test_advance_choice_infers_next_scene(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        state.add_player_message(session, "森の入口へ向かう")
        state.apply_gm_payload(session, "冒険者は森へ進んだ。", {"state_delta": {}})

        self.assertEqual(session["current_scene"], "forest")
        self.assertEqual(session["choices"][0]["text"], "森へ進む")


if __name__ == "__main__":
    unittest.main()
