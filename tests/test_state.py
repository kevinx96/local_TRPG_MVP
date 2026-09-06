import json
import os
import unittest
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import patch

from host import app as app_module
from host import state
from host.gm_contract import split_visible_and_json
from host.scenario_context import current_action_choices, hybrid_context_debug


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

        self.assertEqual(state.current_scene_id(session), "start")
        self.assertEqual(state.current_location_id(session), "forge")
        self.assertNotIn("current_scene", session)
        self.assertNotIn("current_location", session)
        self.assertEqual(public["current_scene_title"], "広場")
        self.assertNotIn("scenario_pack", public)

    def test_scenario_pack_preserves_meta_extensions(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["meta"]["hybrid_mode"] = "semi"
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        self.assertEqual(session["scenario_pack"]["meta"]["hybrid_mode"], "semi")

    def test_engine_action_commits_scene_and_location_atomically(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["scenes"][0]["next_scene_ids"] = ["forest"]
        raw["scenes"][1]["location_ids"] = ["forest_gate"]
        raw["locations"][0]["scene_id"] = "start"
        raw["locations"][0]["actions"] = [
            {
                "id": "enter_forest",
                "text": "森へ進む",
                "effects": [{"current_location": "forest_gate"}],
            }
        ]
        raw["locations"].append(
            {
                "id": "forest_gate",
                "scene_id": "forest",
                "title": "森の入口",
            }
        )
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        action = state.resolve_action(session, action_id="enter_forest")
        roll = state.roll_dice(session, *state.action_dice_settings(action), client_rolls=[10])
        state.apply_action_result(session, action, roll)
        public = state.public_session(session)

        self.assertEqual(session["world_state"], {"scene_id": "forest", "location_id": "forest_gate"})
        self.assertEqual(public["current_scene"], "forest")
        self.assertEqual(public["current_location"], "forest_gate")
        self.assertEqual(public["current_location_title"], "森の入口")

    def test_free_turn_and_model_delta_cannot_change_world_position(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["scenes"][1]["location_ids"] = ["forest_gate"]
        raw["locations"].append(
            {"id": "forest_gate", "scene_id": "forest", "title": "森の入口"}
        )
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])
        model_response = json.dumps(
            {
                "gm_text": "森へ向かおうとしたが、まだ広場にいる。",
                "system_log": "",
                "dice_type": "1d20",
                "dice_dc": 0,
                "state_delta": {"current_scene": "forest", "current_location": "forest_gate"},
                "choices": [{"text": "別の方法を探す", "risk": "判定不要"}],
            },
            ensure_ascii=False,
        )

        with patch.object(app_module, "chat_completion", return_value=model_response):
            result = app_module._run_turn(
                session,
                app_module.TurnRequest(text="森の入口へ向かう"),
            )

        self.assertEqual(session["world_state"], {"scene_id": "start", "location_id": "forge"})
        self.assertEqual(result["current_scene"], "start")
        self.assertEqual(result["current_location"], "forge")
        self.assertTrue(any("model world transition ignored" in log["text"] for log in session["system_logs"]))

    def test_silent_return_transition_skips_llm_and_clears_dialogue(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["scenes"][0]["location_ids"] = ["forge", "castle"]
        raw["locations"][0]["actions"] = [
            {
                "id": "return_castle_from_forge",
                "text": "城に戻る",
                "risk": "判定不要",
                "effects": [{"current_location": "castle"}],
            }
        ]
        raw["locations"].append(
            {
                "id": "castle",
                "scene_id": "start",
                "title": "王城",
                "actions": [{"id": "ask_king", "text": "国王に話を聞く", "risk": "判定不要"}],
                "hybrid": {
                    "mode": "prepared_gm_turns",
                    "prepared_turns": [
                        {
                            "id": "ask_general_fail",
                            "source_choice": "将軍ドラコに助言を求める",
                            "trigger_keywords": ["将軍", "助言"],
                            "draft": {"gm_text": "将軍は鼻で笑った。", "choices": []},
                        }
                    ],
                },
            }
        )
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path), gm_mode="semi")
        session = state.load_session(public["id"])
        session["dice_log"].append(
            {"expression": "1d20", "rolls": [2], "total": 2, "dc": 15, "success": False}
        )
        model_response = json.dumps(
            {"gm_text": "誤った将軍の台詞", "system_log": "", "state_delta": {}, "choices": []},
            ensure_ascii=False,
        )

        with patch.object(app_module, "chat_completion", return_value=model_response) as completion:
            result = app_module._run_turn(
                session,
                app_module.TurnRequest(text="城に戻る", action_id="return_castle_from_forge"),
            )

        completion.assert_not_called()
        self.assertEqual(result["current_location"], "castle")
        self.assertEqual([message["role"] for message in result["messages"]], ["user"])
        self.assertFalse(result["last_turn_narrated"])
        self.assertEqual(result["choices"][0]["action_id"], "ask_king")

    def test_hybrid_selector_does_not_use_stale_roll_for_unrelated_action(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["hybrid"] = {
            "mode": "prepared_gm_turns",
            "prepared_turns": [
                {
                    "id": "ask_general_fail",
                    "source_choice": "将軍ドラコに助言を求める",
                    "trigger_keywords": ["将軍", "助言"],
                    "draft": {"gm_text": "将軍は鼻で笑った。", "choices": []},
                }
            ],
        }
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path), gm_mode="semi")
        session = state.load_session(public["id"])
        session["last_action_result"] = {
            "action_id": "return_castle_from_forge",
            "text": "城に戻る",
            "outcome": "neutral",
            "state_delta": {"current_location": "forge"},
        }
        session["dice_log"].append(
            {"expression": "1d20", "rolls": [2], "total": 2, "dc": 15, "success": False}
        )

        self.assertFalse(state.has_hybrid_prepared_turn(session, "城に戻る"))

    def test_legacy_position_fields_migrate_to_world_state(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session.pop("world_state")
        session["current_scene"] = "start"
        session["current_location"] = "forge"

        world = state.ensure_world_state(session)

        self.assertEqual(world, {"scene_id": "start", "location_id": "forge"})
        self.assertNotIn("current_scene", session)
        self.assertNotIn("current_location", session)

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
            json.dumps({"backends": {"ollama": {"model": "remote-model", "fallback_models": ["m2", "m3"]}}}),
            encoding="utf-8-sig",
        )

        with patch.dict(os.environ, {"TRPG_OLLAMA_BASE_URL": "https://ollama.example.com"}, clear=False):
            config = state.load_config(config_path)

        self.assertEqual(config["backends"]["ollama"]["model"], "remote-model")
        self.assertEqual(config["backends"]["ollama"]["fallback_models"], ["m2", "m3"])
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

    def test_select_scenario_context_uses_word_boundaries_for_ascii_keywords(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["npcs"].append({
            "id": "innkeeper",
            "name": "Inn Keeper",
            "description": "Offers a room.",
            "keywords": ["inn", "\u5bbf"],
        })
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        english_context = state.select_scenario_context(session, "We discuss dinner in the valley.")
        japanese_context = state.select_scenario_context(session, "\u5bbf\u5c4b\u3067\u60c5\u5831\u3092\u96c6\u3081\u308b")

        self.assertNotIn("innkeeper", [item["id"] for item in english_context["matched"]["npcs"]])
        self.assertIn("innkeeper", [item["id"] for item in japanese_context["matched"]["npcs"]])

    def test_scene_description_does_not_keyword_match_remote_enemies(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["scenes"][0]["description"] = "王は邪竜イグニスと竜の谷について語る。"
        raw["locations"].append({
            "id": "dragon_valley",
            "title": "竜の谷",
            "description": "遠い谷。",
            "keywords": ["竜", "谷"],
            "enemy_ids": ["ignis"],
        })
        raw["enemies"] = [{"id": "ignis", "name": "イグニス", "description": "紅き邪竜。"}]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        context = state.select_scenario_context(session, "")

        self.assertEqual([item["id"] for item in context["matched"]["locations"]], ["forge"])
        self.assertEqual(context["matched"]["enemies"], [])
        self.assertFalse(public["in_combat"])
        self.assertEqual(public["enemies"], [])

    def test_public_session_does_not_expose_keyword_matched_remote_enemies(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"].append({
            "id": "dragon_valley",
            "title": "竜の谷",
            "description": "遠い谷。",
            "keywords": ["竜", "谷", "イグニス"],
            "enemy_ids": ["ignis"],
        })
        raw["enemies"] = [{"id": "ignis", "name": "イグニス", "description": "紅き邪竜。"}]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])
        session["messages"].append({"role": "assistant", "speaker": "GM", "text": "イグニスの情報を聞いた。"})
        session["choices"] = [{"text": "イグニスについて聞く", "preview": "", "risk": "判定不要"}]

        public = state.public_session(session)

        self.assertFalse(public["in_combat"])
        self.assertEqual(public["enemies"], [])

    def test_full_mode_caps_matched_context_records(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"] = [
            {
                "id": f"market_{index}",
                "title": f"市場{index}",
                "description": "装備を扱う店。",
                "keywords": ["市場"],
            }
            for index in range(6)
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path), gm_mode="full")
        session = state.load_session(public["id"])

        context = state.select_scenario_context(session, "市場を調べる")

        self.assertEqual(len(context["matched"]["locations"]), 3)

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

    def test_failed_roll_fallback_removes_repeated_check_choice(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        state.add_player_message(session, "鍛冶屋へ向かう")
        session["next_dice_dc"] = 15
        session["dice_log"].append({"expression": "1d20", "rolls": [7], "total": 7, "created_at": state.utc_now()})

        state.apply_gm_payload(session, "鍛冶師は首を横に振り、有用な助言を与えなかった。", {"state_delta": {}})

        self.assertEqual(session["choices"][0]["text"], "助言を受け流して別の準備に移る")
        self.assertNotIn("鍛冶屋へ向かう", [choice["text"] for choice in session["choices"]])

    def test_failed_roll_text_avoids_mechanical_terms(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        state.add_player_message(session, "\u5c06\u8ecd\u30c9\u30e9\u30b3\u306b\u52a9\u8a00\u3092\u6c42\u3081\u308b")
        session["next_dice_dc"] = 15
        session["dice_log"].append({"expression": "1d20", "rolls": [5], "total": 5, "dc": 15, "success": False, "created_at": state.utc_now()})

        state.apply_gm_payload(
            session,
            "\u30a2\u30eb\u30b9\u306f\u300c\u5c06\u8ecd\u30c9\u30e9\u30b3\u306b\u52a9\u8a00\u3092\u6c42\u3081\u308b\u300d\u3092\u8a66\u307f\u305f\u304c\u3001\u5224\u5b9a\u306f\u5c4a\u304b\u306a\u304b\u3063\u305f\u3002",
            {"state_delta": {}, "choices": [{"text": "\u5225\u306e\u6e96\u5099\u306b\u79fb\u308b", "risk": "\u5224\u5b9a\u4e0d\u8981"}]},
        )

        latest_gm = session["messages"][-1]["text"]
        self.assertNotIn("\u5224\u5b9a", latest_gm)
        self.assertIn("\u78ba\u304b\u306a\u624b\u304c\u304b\u308a\u306f\u5f97\u3089\u308c\u306a\u304b\u3063\u305f", latest_gm)

    def test_failed_roll_malformed_json_does_not_keep_useful_hint(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        state.add_player_message(session, "鍛冶師に秘密の助言を求める")
        session["next_dice_dc"] = 15
        session["dice_log"].append({"expression": "1d20", "rolls": [7], "total": 7, "created_at": state.utc_now()})
        visible, payload, warning = split_visible_and_json(
            '{"gm_text":"鍛冶師は曖昧に笑う。近隣の洞窟に古代文字があるはずだ。",'
            '"choices":[{"option":"途中で切れた"'
        )

        state.apply_gm_payload(session, visible, payload, warning)

        latest_gm = session["messages"][-1]["text"]
        self.assertIn("確かな手がかりは得られなかった", latest_gm)
        self.assertNotIn("洞窟", latest_gm)
        self.assertNotIn("鍛冶師に秘密の助言を求める", [choice["text"] for choice in session["choices"]])

    def test_public_session_exposes_current_scene_enemies(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["enemy_ids"] = ["slime"]
        raw["enemies"] = [
            {
                "id": "slime",
                "name": "Slime",
                "description": "A weak training enemy.",
                "hp": 5,
                "max_hp": 5,
                "skills": [{"name": "Body Slam"}],
            }
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

        public = state.create_session(str(path))

        self.assertTrue(public["in_combat"])
        self.assertEqual(public["enemies"][0]["template_id"], "slime")
        self.assertEqual(public["combat"]["status"], "active")
        self.assertNotIn("scenario_pack", public)

    def test_combat_uses_engine_actions_instead_of_llm_choices(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["enemy_ids"] = ["slime"]
        raw["enemies"] = [{"id": "slime", "name": "Slime", "hp": 5, "max_hp": 5}]
        raw["combat_choices"] = [{"text": "Legacy LLM attack", "preview": "", "risk": ""}]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        self.assertEqual(public["choices"], [])
        self.assertEqual(public["combat"]["actions"][0]["type"], "attack")
        self.assertNotIn("Legacy LLM attack", [action["name"] for action in public["combat"]["actions"]])

    def test_legacy_txt_scenario_still_builds_context(self):
        scenario = self.tmp_path / "legacy.txt"
        scenario.write_text("古い形式のシナリオ本文です。", encoding="utf-8")

        public = state.create_session(str(scenario))
        session = state.load_session(public["id"])
        messages = state.build_llm_messages(session, {"expression": "opening", "rolls": [], "total": 0}, "contract")

        self.assertEqual(state.current_scene_id(session), "start")
        self.assertEqual(public["current_scene_title"], "開始")
        self.assertIn("シナリオコンテキスト", messages[1]["content"])
        self.assertIn("古い形式のシナリオ本文です。", messages[1]["content"])

    def test_build_llm_messages_uses_short_history_and_memory_summary(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        for index in range(4):
            state.add_player_message(session, f"action {index}")
            state.add_assistant_message(session, f"result {index}")
        state.apply_state_delta(session, {"hp_change": -1})

        messages = state.build_llm_messages(session, {"expression": "1d20", "rolls": [10], "total": 10}, "contract")

        roles = [message["role"] for message in messages]
        self.assertEqual(roles.count("user"), 2)
        self.assertEqual(roles.count("assistant"), 2)
        self.assertTrue(any(message["content"].startswith("確定済みイベント履歴:") for message in messages if message["role"] == "system"))
        self.assertFalse(any("result 0" in message["content"] for message in messages if message["role"] == "system"))
        self.assertFalse(any("action 0" in message["content"] for message in messages if message["role"] != "system"))

    def test_full_mode_caps_history_for_small_models(self):
        public = state.create_session(str(self.write_pack()), gm_mode="full")
        session = state.load_session(public["id"])
        for index in range(4):
            state.add_player_message(session, f"action {index}")
            state.add_assistant_message(session, f"result {index}")
        state.apply_state_delta(session, {"mp_change": -1})

        messages = state.build_llm_messages(session, {"expression": "1d20", "rolls": [10], "total": 10}, "contract")

        roles = [message["role"] for message in messages]
        self.assertEqual(roles.count("user"), 1)
        self.assertEqual(roles.count("assistant"), 1)
        self.assertFalse(any("action 1" in message["content"] for message in messages if message["role"] != "system"))
        self.assertTrue(any(message["content"].startswith("確定済みイベント履歴:") for message in messages if message["role"] == "system"))
        self.assertTrue(any("FULLモード進行制御" in message["content"] for message in messages if message["role"] == "system"))

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

    def test_opening_accepts_json_only_gm_text_without_demo_fallback(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        model_response = json.dumps(
            {
                "gm_text": "王の間に静かな緊張が満ちています。",
                "system_log": "開幕シーンを開始しました。",
                "state_delta": {},
                "choices": [{"text": "国王に話を聞く", "preview": "", "risk": "判定不要"}],
            },
            ensure_ascii=False,
        )

        with patch.object(app_module, "load_config", return_value={"debug_llm": False, "demo_fallback_on_error": True}):
            with patch.object(app_module, "chat_completion", return_value=model_response):
                opened = app_module._run_opening(session)

        self.assertEqual(opened["messages"][-1]["text"], "王の間に静かな緊張が満ちています。")
        self.assertFalse(any("開幕シーンを開始しました。" in log["text"] for log in opened["system_logs"]))
        self.assertEqual(opened["choices"][0]["text"], "国王に話を聞く")
        self.assertFalse(any("デモモード" in log["text"] for log in opened["system_logs"]))

    def test_create_session_stores_gm_mode(self):
        public = state.create_session(str(self.write_pack()), gm_mode="full")
        session = state.load_session(public["id"])
        messages = state.build_llm_messages(session, {"expression": "opening", "rolls": [], "total": 0}, "contract")

        self.assertEqual(public["gm_mode"], "full")
        self.assertIn('"current_scene": "start"', messages[2]["content"])

        fallback = state.create_session(str(self.write_pack()), gm_mode="unknown")
        self.assertEqual(fallback["gm_mode"], "semi")

        positional = state.create_session(str(self.write_pack()), None, "full")
        self.assertEqual(positional["gm_mode"], "full")

    def test_semi_mode_prefers_sibling_hybrid_pack(self):
        semi_path = self.write_pack()
        hybrid_path = semi_path.with_name("scenario_hybrid.json")
        hybrid = json.loads(semi_path.read_text(encoding="utf-8"))
        hybrid["meta"]["title"] = "Hybrid pack"
        hybrid_path.write_text(json.dumps(hybrid, ensure_ascii=False), encoding="utf-8")

        public = state.create_session(str(semi_path), gm_mode="semi")
        session = state.load_session(public["id"])

        self.assertEqual(Path(session["scenario_path"]).name, "scenario_hybrid.json")
        self.assertEqual(public["scenario_title"], "Hybrid pack")

    def test_full_mode_keeps_original_pack_when_hybrid_sibling_exists(self):
        full_path = self.write_pack()
        hybrid_path = full_path.with_name("scenario_hybrid.json")
        hybrid = json.loads(full_path.read_text(encoding="utf-8"))
        hybrid["meta"]["title"] = "Hybrid pack"
        hybrid_path.write_text(json.dumps(hybrid, ensure_ascii=False), encoding="utf-8")

        public = state.create_session(str(full_path), gm_mode="full")
        session = state.load_session(public["id"])

        self.assertEqual(Path(session["scenario_path"]).name, "scenario.json")
        self.assertNotEqual(public["scenario_title"], "Hybrid pack")

    def test_semi_mode_uses_prepared_turn_context(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["hybrid"] = {
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
        public = state.create_session(str(path), gm_mode="semi")
        session = state.load_session(public["id"])
        state.add_player_message(session, "鍛冶屋へ向かう")

        messages = state.build_llm_messages(session, {"expression": "1d20", "rolls": [7], "total": 7}, "contract")
        combined = "\n".join(message["content"] for message in messages)

        self.assertIn("SEMI/HYBRID", messages[1]["content"])
        self.assertIn("GM forge draft.", combined)
        self.assertNotIn("trigger_keywords", combined)
        self.assertNotIn("Keep this English note", combined)
        self.assertNotIn("forge_response", combined)
        self.assertNotIn('"matched"', combined)
        self.assertNotIn("_debug", combined)
        self.assertEqual(len(messages), 4)

        llm_context = state.select_hybrid_context(session, "鍛冶屋へ向かう")
        debug_context = state.select_hybrid_context(session, "鍛冶屋へ向かう", include_debug=True)
        debug = hybrid_context_debug(debug_context)

        self.assertNotIn("_debug", llm_context)
        self.assertEqual(debug["prepared_turn"], "forge_response")
        self.assertEqual(debug["purpose"], "choice_response")

    def test_hybrid_turn_matching_ignores_stale_assistant_text(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["hybrid"] = {
            "mode": "prepared_gm_turns",
            "prepared_turns": [
                {
                    "id": "dragon_info",
                    "purpose": "choice_response",
                    "source_choice": "国王に邪竜の詳しい話を聞く",
                    "trigger_keywords": ["イグニス", "弱点"],
                    "draft": {
                        "gm_text": "イグニスの弱点は冷気だ。",
                        "choices": [{"text": "城内の鍛造屋へ向かう", "preview": "", "risk": ""}],
                    },
                }
            ],
        }
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path), gm_mode="semi")
        session = state.load_session(public["id"])
        state.add_assistant_message(session, "イグニスの弱点は冷気だ。")
        state.add_player_message(session, "城内の鍛造屋へ向かう")

        messages = state.build_llm_messages(session, {"expression": "1d20", "rolls": [7], "total": 7}, "contract")
        combined = "\n".join(message["content"] for message in messages)

        self.assertNotIn("SEMI/HYBRID", combined)
        self.assertIn("シナリオコンテキスト", messages[1]["content"])

    def test_hybrid_turn_matching_uses_current_player_text_only(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["hybrid"] = {
            "mode": "prepared_gm_turns",
            "prepared_turns": [
                {
                    "id": "invite_robin_success",
                    "purpose": "choice_response",
                    "source_choice": "\u30d1\u30fc\u30c6\u30a3\u306b\u52e7\u8a98\u3059\u308b",
                    "trigger_keywords": ["\u30d1\u30fc\u30c6\u30a3", "\u52e7\u8a98"],
                    "draft": {"gm_text": "invite draft", "choices": []},
                },
                {
                    "id": "robin_rumor",
                    "purpose": "choice_response",
                    "source_choice": "\u5642\u8a71\u3092\u805e\u304f",
                    "trigger_keywords": ["\u5642", "\u8a71"],
                    "draft": {"gm_text": "rumor draft", "choices": []},
                },
            ],
        }
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path), gm_mode="semi")
        session = state.load_session(public["id"])
        state.add_player_message(session, "\u30d1\u30fc\u30c6\u30a3\u306b\u52e7\u8a98\u3059\u308b")

        context = state.select_hybrid_context(session, "\u5642\u8a71\u3092\u805e\u304f", include_debug=True)
        debug = hybrid_context_debug(context)

        self.assertEqual(debug["prepared_turn"], "robin_rumor")

    def test_hybrid_turn_matching_prefers_failed_roll_draft(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["hybrid"] = {
            "mode": "prepared_gm_turns",
            "prepared_turns": [
                {
                    "id": "invite_robin_success",
                    "purpose": "choice_response",
                    "source_choice": "\u30d1\u30fc\u30c6\u30a3\u306b\u52e7\u8a98\u3059\u308b",
                    "trigger_keywords": ["\u30d1\u30fc\u30c6\u30a3", "\u52e7\u8a98"],
                    "draft": {"gm_text": "success draft", "choices": []},
                },
                {
                    "id": "invite_robin_fail",
                    "purpose": "choice_response",
                    "source_choice": "\u30d1\u30fc\u30c6\u30a3\u306b\u52e7\u8a98\u3059\u308b",
                    "trigger_keywords": ["\u30d1\u30fc\u30c6\u30a3", "\u52e7\u8a98"],
                    "draft": {"gm_text": "fail draft", "choices": []},
                },
            ],
        }
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path), gm_mode="semi")
        session = state.load_session(public["id"])
        state.add_player_message(session, "\u30d1\u30fc\u30c6\u30a3\u306b\u52e7\u8a98\u3059\u308b")
        session["dice_log"].append({"expression": "1d100", "rolls": [12], "total": 12, "dc": 60, "success": False})

        context = state.select_hybrid_context(session, "\u30d1\u30fc\u30c6\u30a3\u306b\u52e7\u8a98\u3059\u308b", include_debug=True)
        debug = hybrid_context_debug(context)

        self.assertEqual(debug["prepared_turn"], "invite_robin_fail")

    def test_full_mode_ignores_prepared_turn_hints(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["hybrid"] = {
            "mode": "prepared_gm_turns",
            "prepared_turns": [
                {
                    "id": "opening",
                    "purpose": "opening",
                    "draft": {
                        "gm_text": "GM prepared draft should not appear.",
                        "choices": [{"text": "Prepared choice", "preview": "", "risk": ""}],
                    },
                }
            ],
        }
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path), gm_mode="full")
        session = state.load_session(public["id"])

        messages = state.build_llm_messages(session, {"expression": "opening", "rolls": [], "total": 0}, "contract")
        combined = "\n".join(message["content"] for message in messages)

        self.assertNotIn("SEMI/HYBRID", combined)
        self.assertNotIn("GM prepared draft should not appear.", combined)
        self.assertNotIn("Prepared choice", combined)

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

    def test_create_session_uses_character_template(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["characters"] = [
            {
                "id": "mage",
                "name": "魔法使い",
                "default_name": "リリィ",
                "description": "知力に長ける。",
                "image": "/static/images/char_mage.png",
                "hp": 12,
                "max_hp": 12,
                "mp": 20,
                "max_mp": 20,
                "sp": 6,
                "max_sp": 6,
                "attributes": {"int": 16},
                "inventory": [{"name": "魔導書", "quantity": 1}],
                "equipment": ["魔導書"],
            }
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

        public = state.create_session(str(path), character_id="mage")
        character = public["character"]

        self.assertEqual(character["character_id"], "mage")
        self.assertEqual(character["name"], "リリィ")
        self.assertEqual(character["character_image"], "/static/images/char_mage_v2.png")
        self.assertEqual(character["attributes"]["int"], 16)
        self.assertEqual(character["inventory"][0]["name"], "魔導書")

    def test_legacy_con_attribute_normalizes_to_end(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["characters"] = [
            {
                "id": "guard",
                "name": "Guard",
                "attributes": {"con": 12, "end": 10},
            }
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

        public = state.create_session(str(path), character_id="guard")

        self.assertEqual(public["character"]["attributes"]["end"], 12)
        self.assertNotIn("con", public["character"]["attributes"])

    def test_model_state_delta_rejects_unauthorized_fields_and_unknown_entities(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["character"]["attributes"] = {"str": 10, "int": 8, "end": 9}
        starting_mp = session["character"]["mp"]

        state.apply_gm_payload(
            session,
            "鍛冶師の助言を受け、少し疲れた。",
            {
                "state_delta": {
                    "hp_change": -2,
                    "gold": 999,
                    "attribute_changes": {
                        "int": 1,
                        "con": 1,
                        "mp": -3,
                        "luck": 2,
                    },
                    "flags_set": ["boss_defeated"],
                    "inventory_add": [
                        {"id": "iron_shield", "name": "偽名", "quantity": 1},
                        {"name": "存在しない秘宝", "quantity": 1},
                    ],
                    "current_location": "forest_gate",
                },
                "choices": [{"text": "準備を続ける", "risk": "判定不要"}],
            },
        )

        attrs = session["character"]["attributes"]
        inventory_names = [item["name"] for item in session["character"]["inventory"]]
        self.assertEqual(session["character"]["hp"], 18)
        self.assertEqual(session["character"]["mp"], starting_mp)
        self.assertEqual(attrs["int"], 9)
        self.assertEqual(attrs["end"], 10)
        self.assertNotIn("mp", attrs)
        self.assertNotIn("luck", attrs)
        self.assertEqual(session["character"]["gold"], 0)
        self.assertNotIn("boss_defeated", session["flags"])
        self.assertIn("鉄の盾", inventory_names)
        self.assertNotIn("偽名", inventory_names)
        self.assertNotIn("存在しない秘宝", inventory_names)
        self.assertEqual(state.current_location_id(session), "forge")
        self.assertTrue(any("model state_delta rejected" in log["text"] for log in session["system_logs"]))

    def test_model_state_delta_rejects_out_of_range_and_non_integer_values(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["character"]["attributes"] = {"str": 10, "end": 9}
        before = {
            key: session["character"][key]
            for key in ("hp", "mp", "sp", "gold")
        }

        state.apply_gm_payload(
            session,
            "状態は変わらなかった。",
            {
                "state_delta": {
                    "hp_change": session["character"]["max_hp"] + 1,
                    "mp_change": -1.5,
                    "sp_change": True,
                    "gold_change": state.MODEL_MAX_GOLD_DELTA + 1,
                },
            },
        )

        self.assertEqual(
            {key: session["character"][key] for key in before},
            before,
        )
        log_text = "\n".join(log["text"] for log in session["system_logs"])
        for key in ("hp_change", "mp_change", "sp_change", "gold_change"):
            self.assertIn(key, log_text)

    def test_model_attribute_aliases_cannot_stack_past_delta_limit(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["character"]["attributes"] = {"end": 9}

        state.apply_gm_payload(
            session,
            "少しだけ持久力が増した。",
            {
                "state_delta": {
                    "attribute_changes": {"con": 3, "endurance": 3},
                },
            },
        )

        self.assertEqual(session["character"]["attributes"]["end"], 12)
        self.assertTrue(
            any("attribute_changes.endurance" in log["text"] for log in session["system_logs"])
        )

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

    def test_model_inventory_add_accepts_catalog_items_and_rejects_unknown_items(self):
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
                        {"id": "iron_shield", "name": "偽名", "quantity": 2},
                        {"item": "氷の護符", "quantity": "2"},
                        {"item_name": "古い鍵"},
                    ],
                },
            },
        )

        inventory = {item["name"]: item["quantity"] for item in session["character"]["inventory"]}
        self.assertEqual(inventory["鉄の盾"], 2)
        self.assertNotIn("偽名", inventory)
        self.assertNotIn("氷の護符", inventory)
        self.assertNotIn("古い鍵", inventory)
        self.assertNotIn("", inventory)
        self.assertTrue(any("model state_delta rejected" in log["text"] for log in session["system_logs"]))

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

    def test_model_system_log_is_not_a_committed_state_event(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])

        state.apply_gm_payload(
            session,
            "rest ended",
            {"system_log": "HP and MP fully restored", "state_delta": {}, "choices": []},
        )

        public_logs = [entry["text"] for entry in state.public_session(session)["system_logs"]]
        self.assertNotIn("HP and MP fully restored", public_logs)

    def test_structured_memory_uses_engine_events_not_old_gm_claims(self):
        public = state.create_session(str(self.write_pack()), gm_mode="full")
        session = state.load_session(public["id"])
        session["messages"] = [
            {"role": "assistant", "speaker": "GM", "text": "HP and MP fully restored"},
            {"role": "user", "speaker": "player", "text": "continue"},
            {"role": "assistant", "speaker": "GM", "text": "the road continues"},
        ]
        state.apply_state_delta(session, {"mp_change": -3})

        messages = state.build_llm_messages(
            session,
            {"expression": "1d20", "rolls": [10], "total": 10},
            "contract",
        )
        memory = next(message["content"] for message in messages if message["content"].startswith("確定済みイベント履歴:"))

        self.assertIn('"resource": "mp"', memory)
        self.assertIn('"change": -3', memory)
        self.assertNotIn("fully restored", memory)

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
                    {"option": "短いoption選択", "risk": "判定不要"},
                ],
            },
        )

        self.assertEqual(len(session["choices"]), 3)
        self.assertEqual(session["choices"][0]["text"], "単純な文字列の選択")
        self.assertEqual(session["choices"][1]["risk"], "危険")
        self.assertEqual(session["choices"][2]["text"], "短いoption選択")
        self.assertEqual(session["choices"][2]["preview"], "")

    def test_roll_dice_records_dc_and_success(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])

        with patch("host.state.random.randint", return_value=1):
            roll = state.roll_dice(session, "1d20", dc=2)

        self.assertEqual(roll["dc"], 2)
        self.assertFalse(roll["success"])
        self.assertEqual(session["dice_log"][-1]["dc"], 2)

    def test_roll_dice_marks_natural_extremes_and_applies_critical_effects(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["character"]["attributes"] = {"wis": 0}
        action = {
            "id": "rumor",
            "text": "噂を聞く",
            "success_effects": [{"set_flag": "heard_rumor"}],
            "critical_success_effects": [{"set_flag": "heard_xanxus"}],
            "failure_effects": [{"set_flag": "rumor_refused"}],
            "critical_failure_effects": [{"set_flag": "silent_refusal"}],
        }

        maximum = state.roll_dice(session, "1d20+wis", dc=12, client_rolls=[20])
        maximum_result = state.apply_action_result(session, action, maximum)

        self.assertTrue(maximum["critical_success"])
        self.assertEqual(maximum_result["outcome"], "critical_success")
        self.assertTrue(session["flags"]["heard_rumor"])
        self.assertTrue(session["flags"]["heard_xanxus"])

        minimum = state.roll_dice(session, "1d20+wis", dc=12, client_rolls=[1])
        minimum_result = state.apply_action_result(session, action, minimum)

        self.assertTrue(minimum["critical_failure"])
        self.assertEqual(minimum_result["outcome"], "critical_failure")
        self.assertTrue(session["flags"]["rumor_refused"])
        self.assertTrue(session["flags"]["silent_refusal"])

    def test_recruiting_a_companion_replaces_and_logs_the_previous_companion(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["scenario_pack"]["companions"] = [
            {"id": "blue_mage", "name": "青いローブの魔法使い"},
            {"id": "fire_bat_dragon", "name": "火コウモリ竜"},
        ]

        state.apply_state_delta(session, {"set_companion": "blue_mage"})
        state.apply_state_delta(session, {"set_companion": "fire_bat_dragon"})

        self.assertEqual(session["companion"]["id"], "fire_bat_dragon")
        public_logs = [entry["text"] for entry in state.public_session(session)["system_logs"]]
        self.assertTrue(any("青いローブの魔法使い" in text and "離脱" in text for text in public_logs))
        self.assertTrue(any("火コウモリ竜" in text and "加入" in text for text in public_logs))

    def test_choice_risk_overrides_dice_settings_for_turn(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["next_dice_type"] = "1d20"
        session["next_dice_dc"] = 0
        session["choices"] = [
            {"text": "罠を避けて進む", "risk": "1d20+dex判定（DC14）"},
            {"text": "休む", "risk": "判定不要"},
        ]

        dice_type, dice_dc = app_module._dice_settings_for_turn(session, "罠を避けて進む")
        safe_type, safe_dc = app_module._dice_settings_for_turn(session, "休む")

        self.assertEqual(dice_type, "1d20+dex")
        self.assertEqual(dice_dc, 14)
        self.assertEqual(safe_type, "1d20")
        self.assertEqual(safe_dc, 0)

    def test_child_choice_does_not_fall_back_to_default_dice_dc(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["next_dice_type"] = "1d20"
        session["next_dice_dc"] = 0
        session["choices"] = [
            {
                "text": "\u57ce\u4e0b\u753a\u3092\u63a2\u7d22\u3059\u308b",
                "risk": "\u5224\u5b9a\u4e0d\u8981",
                "children": [
                    {"text": "\u935b\u51b6\u5c4b\u3078\u5411\u304b\u3046", "risk": "\u5224\u5b9a\u4e0d\u8981"},
                ],
            }
        ]

        dice_type, dice_dc = app_module._dice_settings_for_turn(session, "\u935b\u51b6\u5c4b\u3078\u5411\u304b\u3046")

        self.assertEqual(dice_type, "1d20")
        self.assertEqual(dice_dc, 0)

    def test_unmatched_action_does_not_create_default_dice_check(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["next_dice_type"] = "1d20"
        session["next_dice_dc"] = 0

        dice_type, dice_dc = app_module._dice_settings_for_turn(session, "\u81ea\u7531\u5165\u529b")

        self.assertEqual(dice_type, "1d20")
        self.assertEqual(dice_dc, 0)

    def test_free_text_paraphrase_is_a_candidate_until_interpreted(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {
                "id": "show_shield_to_smith",
                "text": "鍛冶師に鉄の盾を見せる",
                "intent_keywords": ["鍛冶師に盾を見せる"],
                "effects": [{"set_flag": "showed_shield"}],
            }
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        resolution = state.resolve_player_intent(session, "この鉄の盾を鍛冶師に見てもらいたい")

        self.assertEqual(resolution["status"], "unmatched")
        self.assertIsNone(resolution["action"])
        self.assertIn("show_shield_to_smith", resolution["candidate_action_ids"])

        abbreviated = state.resolve_player_intent(session, "盾を見てもらいたい")
        self.assertEqual(abbreviated["status"], "unmatched")
        self.assertIn("show_shield_to_smith", abbreviated["candidate_action_ids"])

    def test_entity_term_outranks_generic_dialogue_fragment(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {
                "id": "ask_king_info",
                "text": "国王に邪竜の詳しい話を聞く",
                "intent_keywords": ["国王に邪竜の詳しい話を聞く"],
            },
            {
                "id": "ask_general_advice",
                "text": "将軍ドラコに助言を求める",
                "intent_keywords": ["将軍ドラコに助言を求める"],
            },
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        resolution = state.resolve_player_intent(session, "将軍に話を聞きたい")

        self.assertEqual(resolution["status"], "unmatched")
        self.assertEqual(resolution["candidate_action_ids"][0], "ask_general_advice")

    def test_ambiguous_free_text_does_not_choose_between_tied_actions(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {
                "id": "ask_smith_about_weapon",
                "text": "鍛冶師に武器を相談する",
                "intent_keywords": ["鍛冶師", "相談"],
            },
            {
                "id": "ask_smith_about_dragon",
                "text": "鍛冶師に邪竜を相談する",
                "intent_keywords": ["鍛冶師", "相談"],
            },
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        resolution = state.resolve_player_intent(session, "鍛冶師に相談したい")

        self.assertEqual(resolution["status"], "ambiguous")
        self.assertIsNone(resolution["action"])
        self.assertEqual(
            set(resolution["candidate_action_ids"]),
            {"ask_smith_about_weapon", "ask_smith_about_dragon"},
        )

    def test_free_text_does_not_resolve_hidden_child_or_ascii_substring(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {
                "id": "secret_group",
                "text": "秘密の行動",
                "visible_after": "secret_open",
                "children": [
                    {
                        "id": "enter_secret_room",
                        "text": "秘密の部屋に入る",
                        "intent_keywords": ["秘密の部屋"],
                    }
                ],
            },
            {
                "id": "enter_inn",
                "text": "Enter the inn",
                "intent_keywords": ["inn"],
            },
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        hidden = state.resolve_player_intent(session, "秘密の部屋に入る")
        substring = state.resolve_player_intent(session, "We discuss dinner plans")

        self.assertEqual(hidden["status"], "unmatched")
        self.assertEqual(substring["status"], "unmatched")

    def test_free_text_matching_action_group_requests_child_selection(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {
                "id": "buy_equipment",
                "text": "装備を買う",
                "intent_keywords": ["装備を買う", "装備を購入する"],
                "children": [
                    {"id": "buy_armor", "text": "鎧を買う"},
                    {"id": "buy_amulet", "text": "護符を買う"},
                ],
            }
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        resolution = state.resolve_player_intent(session, "装備を買いたい")

        self.assertEqual(resolution["status"], "ambiguous")
        self.assertEqual(resolution["method"], "")
        self.assertEqual(set(resolution["candidate_action_ids"]), {"buy_armor", "buy_amulet"})
        self.assertIsNone(state.resolve_action(session, action_text="装備を買いたい"))

    def test_unmatched_free_text_cannot_mutate_state_or_replace_action_surface(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {
                "id": "inspect_shield",
                "text": "鉄の盾を調べる",
                "intent_keywords": ["鉄の盾", "盾を調べる"],
            }
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])
        captured: dict[str, Any] = {}
        model_response = json.dumps(
            {
                "gm_text": "空へ手を伸ばしたが、ここから月へは行けない。",
                "state_delta": {"gold_change": 5, "flags_set": ["flew_to_moon"]},
                "choices": [{"text": "月の王と話す", "risk": "判定不要"}],
            },
            ensure_ascii=False,
        )

        def fake_completion(_config, messages):
            captured["messages"] = messages
            return model_response

        with patch.object(app_module, "load_config", return_value={"debug_llm": False, "demo_fallback_on_error": True}):
            with patch.object(app_module, "chat_completion", side_effect=fake_completion):
                result = app_module._run_turn(session, app_module.TurnRequest(text="空を飛んで月へ行く"))

        self.assertEqual(session["character"]["gold"], 0)
        self.assertNotIn("flew_to_moon", session["flags"])
        self.assertEqual(session["dice_log"], [])
        self.assertEqual(result["choices"][0]["action_id"], "inspect_shield")
        self.assertNotIn("deviation_state", session)
        self.assertIn("行動案", "\n".join(message["content"] for message in captured["messages"]))
        self.assertNotIn("月へは行けない", result["messages"][-1]["text"])

    def test_unmatched_free_text_is_not_blocked_after_three_llm_turns(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {"id": "inspect_shield", "text": "鉄の盾を調べる", "intent_keywords": ["鉄の盾"]}
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])
        prompts: list[str] = []
        model_response = json.dumps(
            {"gm_text": "試みは主線の手がかりにはつながらなかった。", "state_delta": {}, "choices": []},
            ensure_ascii=False,
        )

        def fake_completion(_config, messages):
            prompts.append("\n".join(message["content"] for message in messages))
            return model_response

        with patch.object(app_module, "load_config", return_value={"debug_llm": False, "demo_fallback_on_error": True}):
            with patch.object(app_module, "chat_completion", side_effect=fake_completion) as completion:
                for index in range(3):
                    app_module._run_turn(session, app_module.TurnRequest(text=f"脱線した行動{index}"))
                fourth = app_module._run_turn(session, app_module.TurnRequest(text="さらに脱線する"))

        self.assertEqual(completion.call_count, 4)
        self.assertNotIn("deviation_state", session)
        self.assertNotIn("今回で必ず収束", prompts[-1])
        self.assertIn("行動を読み取れませんでした", fourth["messages"][-1]["text"])
        self.assertEqual(fourth["choices"][0]["action_id"], "inspect_shield")
        self.assertEqual(session["dice_log"], [])

    def test_resolved_action_clears_deviation_and_applies_engine_effects(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {
                "id": "inspect_shield",
                "text": "鉄の盾を調べる",
                "intent_keywords": ["鉄の盾"],
                "effects": [{"set_flag": "inspected_shield"}],
            }
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])
        session["deviation_state"] = {"turns": 2, "phase": "improvise"}
        model_response = json.dumps(
            {"kind": "existing", "action_id": "inspect_shield", "operation": "", "target_id": "",
             "item_id": "", "advance": False, "approach": "盾を調べる", "reply": ""},
            ensure_ascii=False,
        )

        with patch.object(app_module, "load_config", return_value={"debug_llm": False, "demo_fallback_on_error": True}):
            with patch.object(app_module, "chat_completion", return_value=model_response):
                app_module._run_turn(session, app_module.TurnRequest(text="盾を調べたい"))

        self.assertNotIn("deviation_state", session)
        self.assertTrue(session["flags"]["inspected_shield"])
        self.assertEqual(session["last_action_result"]["action_id"], "inspect_shield")
        self.assertEqual(session["dice_log"], [])

    def test_resolved_roll_action_uses_server_dice_and_engine_outcome(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {
                "id": "read_runes",
                "text": "盾のルーンを読む",
                "roll": {"dice_type": "1d20+wis", "dc": 12},
                "success_effects": [{"set_flag": "read_runes"}],
                "failure_effects": [{"set_flag": "runes_failed"}],
            }
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])
        session["character"]["attributes"] = {"wis": 5}
        model_response = json.dumps(
            {"gm_text": "ルーンの意味を読み解いた。", "state_delta": {}, "choices": []},
            ensure_ascii=False,
        )

        with patch.object(app_module, "load_config", return_value={"debug_llm": False, "demo_fallback_on_error": True}):
            with patch.object(app_module, "chat_completion", return_value=model_response), patch.object(state.random, "randint", return_value=10):
                app_module._run_turn(
                    session,
                    app_module.TurnRequest(
                        text="盾のルーンを読む",
                        action_id="read_runes",
                        client_dice={"rolls": [20]},
                    ),
                )

        self.assertEqual(len(session["dice_log"]), 1)
        self.assertEqual(session["dice_log"][0]["total"], 15)
        self.assertTrue(session["dice_log"][0]["success"])
        self.assertTrue(session["flags"]["read_runes"])
        self.assertNotIn("runes_failed", session["flags"])

    def test_choice_risk_requirement_disables_when_attribute_too_low(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["character"]["attributes"] = {"str": 8, "end": 9}
        session["next_dice_type"] = "1d20"
        session["next_dice_dc"] = 0
        action = "\u5c06\u8ecd\u30c9\u30e9\u30b3\u306b\u52a9\u8a00\u3092\u6c42\u3081\u308b"
        session["choices"] = [
            {"text": action, "risk": "\u7b4b\u529b\u307e\u305f\u306f\u8010\u4e45\u304c10\u4ee5\u4e0a\u30671d20\u5224\u5b9a\uff08DC15\uff09"},
        ]

        dice_type, dice_dc = app_module._dice_settings_for_turn(session, action)
        public_choices = state.public_session(session)["choices"]

        self.assertEqual(dice_type, "1d20")
        self.assertEqual(dice_dc, 15)
        self.assertFalse(public_choices[0]["enabled"])
        self.assertIn("\u8010\u4e45", public_choices[0]["disabled_reason"])

    def test_choice_risk_requirement_allows_end_attribute(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["character"]["attributes"] = {"str": 8, "end": 10}
        session["choices"] = [
            {"text": "\u52a9\u8a00\u3092\u6c42\u3081\u308b", "risk": "\u7b4b\u529b\u307e\u305f\u306f\u8010\u4e45\u304c10\u4ee5\u4e0a\u30671d20\u5224\u5b9a\uff08DC15\uff09"},
        ]

        choice = state.public_session(session)["choices"][0]

        self.assertTrue(choice["enabled"])
        self.assertNotIn("disabled_reason", choice)

    def test_choice_risk_character_requirement_preserves_attribute_or(self):
        public = state.create_session(str(self.write_pack()), character_id="hero")
        session = state.load_session(public["id"])
        session["character"]["attributes"] = {"str": 8, "dex": 12}
        session["choices"] = [
            {
                "text": "\u52c7\u8005\u306e\u5263\u3092\u6383\u3046",
                "risk": "\u52c7\u8005\u306e\u307f\u3001\u7b4b\u529b\u307e\u305f\u306f\u654f\u6377\u304c10\u4ee5\u4e0a\u3067\u5224\u5b9a",
            },
        ]

        choice = state.public_session(session)["choices"][0]

        self.assertTrue(choice["enabled"])

        session["character"]["attributes"] = {"str": 8, "dex": 8}
        choice = state.public_session(session)["choices"][0]

        self.assertFalse(choice["enabled"])
        self.assertIn("\u7b4b\u529b", choice["disabled_reason"])
        self.assertIn("\u654f\u6377", choice["disabled_reason"])
        self.assertIn("\u307e\u305f\u306f", choice["disabled_reason"])

    def test_explicit_nested_choice_requirements_are_recursive(self):
        public = state.create_session(str(self.write_pack()), character_id="hero")
        session = state.load_session(public["id"])
        session["character"]["attributes"] = {"str": 8, "dex": 11}
        session["choices"] = [
            {
                "text": "\u52c7\u8005\u306e\u8a66\u7df4\u3092\u53d7\u3051\u308b",
                "risk": "\u5224\u5b9a",
                "requirements": {
                    "all": [
                        {"character_id": "hero"},
                        {
                            "any": [
                                {"attribute": "str", "gte": 10},
                                {"attribute": "dex", "gte": 10},
                            ]
                        },
                    ]
                },
            }
        ]

        choice = state.public_session(session)["choices"][0]
        self.assertTrue(choice["enabled"])

        session["character"]["attributes"] = {"str": 8, "dex": 8}
        choice = state.public_session(session)["choices"][0]

        self.assertFalse(choice["enabled"])
        self.assertIn("\u307e\u305f\u306f", choice["disabled_reason"])

    def test_choice_preview_character_requirement_disables_wrong_character(self):
        public = state.create_session(str(self.write_pack()), character_id="thief")
        session = state.load_session(public["id"])
        session["choices"] = [
            {
                "text": "\u935b\u51b6\u5e2b\u306b\u5263\u3092\u898b\u305b\u308b",
                "preview": "\u52c7\u8005\u306e\u5263\u306b\u3064\u3044\u3066\u76f8\u8ac7\u3059\u308b\uff08\u52c7\u8005\u306e\u307f\uff09",
                "risk": "\u5224\u5b9a\u4e0d\u8981",
            }
        ]

        choice = state.public_session(session)["choices"][0]

        self.assertFalse(choice["enabled"])
        self.assertIn("\u52c7\u8005\u306e\u307f", choice["disabled_reason"])

    def test_choice_inventory_and_gold_requirements_disable_purchase(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["character"]["gold"] = 0
        session["character"]["inventory"].append({"name": "\u6c37\u306e\u8b77\u7b26", "quantity": 1})
        session["choices"] = [
            {
                "text": "\u6c37\u306e\u8b77\u7b26\u3092\u8cb7\u3046\uff0850G\uff09",
                "risk": "\u5224\u5b9a\u4e0d\u8981",
                "requirements": {
                    "all": [
                        {"gold_gte": 50},
                        {"lacks_item": "\u6c37\u306e\u8b77\u7b26"},
                    ]
                },
            }
        ]

        choice = state.public_session(session)["choices"][0]

        self.assertFalse(choice["enabled"])
        self.assertIn("50", choice["disabled_reason"])
        self.assertIn("\u6c37\u306e\u8b77\u7b26", choice["disabled_reason"])

    def test_purchase_text_infers_inventory_and_gold_requirements(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["character"]["gold"] = 0
        session["character"]["inventory"].append({"name": "\u6c37\u306e\u8b77\u7b26", "quantity": 1})
        session["choices"] = [
            {
                "text": "\u6c37\u306e\u8b77\u7b26\u3092\u8cb7\u3046\uff0850G\uff09",
                "risk": "\u5224\u5b9a\u4e0d\u8981",
            }
        ]

        choice = state.public_session(session)["choices"][0]

        self.assertFalse(choice["enabled"])
        self.assertIn("50", choice["disabled_reason"])
        self.assertIn("\u6c37\u306e\u8b77\u7b26", choice["disabled_reason"])

    def test_disabled_scenario_choice_is_not_sent_to_llm_when_not_in_current_choices(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["character"]["gold"] = 0
        session["character"]["inventory"].append({"name": "\u6c37\u306e\u8b77\u7b26", "quantity": 1})
        session["choices"] = []
        session["scenario_pack"]["locations"][0]["choices"] = [
            {
                "text": "\u6c37\u306e\u8b77\u7b26\u3092\u8cb7\u3046\uff0850G\uff09",
                "risk": "\u5224\u5b9a\u4e0d\u8981",
                "requirements": {
                    "all": [
                        {"gold_gte": 50},
                        {"lacks_item": "\u6c37\u306e\u8b77\u7b26"},
                    ]
                },
            }
        ]

        result = app_module._run_turn(session, app_module.TurnRequest(text="\u6c37\u306e\u8b77\u7b26\u3092\u8cb7\u3046\uff0850G\uff09"))

        self.assertEqual(session["messages"], [])
        self.assertEqual(session["dice_log"], [])
        self.assertTrue(any("\u6c37\u306e\u8b77\u7b26" in log.get("text", "") for log in session["system_logs"]))
        self.assertEqual(result["messages"], [])

    def test_disabled_choice_is_not_sent_to_llm(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["character"]["attributes"] = {"str": 8, "end": 9}
        session["choices"] = [
            {"text": "\u52a9\u8a00\u3092\u6c42\u3081\u308b", "risk": "\u7b4b\u529b\u307e\u305f\u306f\u8010\u4e45\u304c10\u4ee5\u4e0a\u30671d20\u5224\u5b9a\uff08DC15\uff09"},
        ]

        result = app_module._run_turn(session, app_module.TurnRequest(text="\u52a9\u8a00\u3092\u6c42\u3081\u308b"))

        self.assertEqual(session["messages"], [])
        self.assertEqual(session["dice_log"], [])
        self.assertFalse(result["choices"][0]["enabled"])

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

    def test_weapon_replacement_updates_equipment_and_basic_attack(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["items"].append(
            {
                "id": "ice_iron_greatsword",
                "name": "氷鉄の大剣",
                "description": "冷気を帯びた大剣。",
                "combat": {
                    "kind": "weapon",
                    "name": "氷鉄の大剣",
                    "damage": "1d10+str/3+int/4",
                    "accuracy": 88,
                    "element": "ice",
                },
            }
        )
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        state.apply_state_delta(
            session,
            {
                "inventory_add": [{"name": "氷鉄の大剣", "quantity": 1}],
                "inventory_remove": [{"name": "鉄の剣", "quantity": 1}],
            },
        )

        character = session["character"]
        self.assertNotIn("鉄の剣", character["equipment"])
        self.assertIn("氷鉄の大剣", character["equipment"])
        self.assertEqual(character["combat"]["basic_attack"]["name"], "氷鉄の大剣")
        self.assertEqual(character["combat"]["basic_attack"]["element"], "ice")

    def test_loading_stale_save_repairs_equipment_from_inventory(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        session["character"]["inventory"] = [
            item for item in session["character"]["inventory"] if item.get("name") != "鉄の剣"
        ]
        session["character"]["inventory"].append(
            {
                "name": "氷鉄の大剣",
                "quantity": 1,
                "combat": {
                    "kind": "weapon",
                    "name": "氷鉄の大剣",
                    "damage": "1d10+str/3+int/4",
                    "accuracy": 88,
                    "element": "ice",
                },
            }
        )
        session["character"]["equipment"] = ["鉄の剣", "革の鎧"]
        session["character"].setdefault("combat", {})["basic_attack"] = {
            "name": "鉄の剣",
            "damage": "1d8+str/3",
            "accuracy": 90,
            "element": "physical",
        }
        state.save_session(session)

        reloaded = state.load_session(session["id"])

        self.assertEqual(reloaded["character"]["equipment"], ["革の鎧", "氷鉄の大剣"])
        self.assertEqual(reloaded["character"]["combat"]["basic_attack"]["name"], "氷鉄の大剣")

    def test_free_text_does_not_infer_or_commit_a_scene_transition(self):
        public = state.create_session(str(self.write_pack()))
        session = state.load_session(public["id"])
        state.add_player_message(session, "森の入口へ向かう")
        state.apply_gm_payload(session, "冒険者は森へ進んだ。", {"state_delta": {}})

        self.assertEqual(state.current_scene_id(session), "start")
        self.assertEqual(state.current_location_id(session), "forge")
        self.assertEqual(session["choices"][0]["text"], "鍛冶屋へ向かう")

    def test_gm_text_enemy_mention_does_not_infer_remote_scene(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["scenes"][0]["next_scene_ids"] = ["forest"]
        raw["scenes"].append({
            "id": "dragon_valley",
            "title": "竜の谷",
            "description": "イグニスが待つ谷。",
            "keywords": ["イグニス", "竜の谷"],
            "fallback_choices": [{"text": "戦う", "preview": "", "risk": "危険"}],
        })
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])
        state.add_player_message(session, "鍛造屋へ向かう")
        state.apply_gm_payload(
            session,
            "鍛冶場の扉を開けると、鍛冶師はイグニスの弱点は冷気だと告げた。",
            {"state_delta": {}, "choices": [{"text": "準備を続ける", "preview": "", "risk": ""}]},
        )

        self.assertEqual(state.current_scene_id(session), "start")
        self.assertEqual(state.current_location_id(session), "forge")
        self.assertNotIn("current_scene", session)
        self.assertNotIn("current_location", session)

    def test_disallowed_scene_delta_is_ignored_when_next_scenes_are_defined(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["scenes"][0]["next_scene_ids"] = ["forest"]
        raw["scenes"].append({
            "id": "dragon_valley",
            "title": "竜の谷",
            "description": "イグニスが待つ谷。",
            "keywords": ["イグニス", "竜の谷"],
        })
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        state.apply_gm_payload(session, "鍛冶師は氷の短剣を渡した。", {"state_delta": {"current_scene": "dragon_valley"}})

        self.assertEqual(state.current_scene_id(session), "start")
        self.assertTrue(any("model world transition ignored" in log["text"] for log in session["system_logs"]))


    def test_action_purchase_sets_flag_and_disables_repeat(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {
                "id": "buy_ice_amulet",
                "text": "\u6c37\u306e\u8b77\u7b26\u3092\u8cb7\u3046",
                "requirements": {"gold_gte": 50},
                "effects": [
                    {"gold_change": -50},
                    {"add_item": {"name": "\u6c37\u306e\u8b77\u7b26", "quantity": 1}},
                    {"set_flag": "bought_ice_amulet"},
                ],
                "disabled_after": "bought_ice_amulet",
            }
        ]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])
        session["character"]["gold"] = 50

        action = state.resolve_action(session, action_id="buy_ice_amulet")
        roll = state.roll_dice(session, *state.action_dice_settings(action), client_rolls=[10])
        result = state.apply_action_result(session, action, roll)
        choice = state.public_session(session)["choices"][0]

        self.assertEqual(result["action_id"], "buy_ice_amulet")
        self.assertEqual(session["character"]["gold"], 0)
        self.assertTrue(session["flags"]["bought_ice_amulet"])
        self.assertTrue(any(item.get("name") == "\u6c37\u306e\u8b77\u7b26" for item in session["character"]["inventory"]))
        self.assertFalse(choice["enabled"])

    def test_action_failure_branch_does_not_apply_success_effects(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {
                "id": "invite_robin",
                "text": "\u30ed\u30d3\u30f3\u3092\u52e7\u8a98\u3059\u308b",
                "roll": {"dice_type": "1d20", "dc": 15},
                "success_effects": [{"current_scene": "forest"}, {"set_flag": "recruited_robin"}],
                "failure_effects": [{"set_flag": "robin_refused"}],
            }
        ]
        raw["scenes"][0]["next_scene_ids"] = ["forest"]
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])

        action = state.resolve_action(session, action_id="invite_robin")
        roll = state.roll_dice(session, *state.action_dice_settings(action), client_rolls=[3])
        result = state.apply_action_result(session, action, roll)

        self.assertEqual(result["outcome"], "failure")
        self.assertEqual(state.current_scene_id(session), "start")
        self.assertTrue(session["flags"]["robin_refused"])
        self.assertNotIn("recruited_robin", session["flags"])

    def test_hybrid_prepared_turn_matches_action_id_and_outcome(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {
                "id": "invite_robin",
                "text": "\u30ed\u30d3\u30f3\u3092\u52e7\u8a98\u3059\u308b",
                "roll": {"dice_type": "1d20", "dc": 15},
                "failure_effects": [{"set_flag": "robin_refused"}],
            }
        ]
        raw["locations"][0]["hybrid"] = {
            "mode": "prepared_gm_turns",
            "prepared_turns": [
                {"id": "invite_success", "action_id": "invite_robin", "outcome": "success", "draft": {"gm_text": "success draft"}},
                {"id": "invite_fail", "action_id": "invite_robin", "outcome": "failure", "draft": {"gm_text": "failure draft"}},
            ],
        }
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path), gm_mode="semi")
        session = state.load_session(public["id"])
        action = state.resolve_action(session, action_id="invite_robin")
        roll = state.roll_dice(session, *state.action_dice_settings(action), client_rolls=[3])
        state.apply_action_result(session, action, roll)

        context = state.select_hybrid_context(session, "\u30ed\u30d3\u30f3\u3092\u52e7\u8a98\u3059\u308b", include_debug=True)
        debug = hybrid_context_debug(context)
        combined = json.dumps(context, ensure_ascii=False)

        self.assertEqual(debug["prepared_turn"], "invite_fail")
        self.assertIn("failure draft", combined)
        self.assertIn("invite_robin", combined)

    def test_action_result_blocks_model_state_delta_and_choices(self):
        path = self.write_pack()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["locations"][0]["actions"] = [
            {"id": "talk", "text": "\u8a71\u3059", "effects": [{"set_flag": "talked"}]}
        ]
        raw["scenes"].append({"id": "dragon_valley", "title": "Dragon Valley", "description": "", "location_ids": []})
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        public = state.create_session(str(path))
        session = state.load_session(public["id"])
        action = state.resolve_action(session, action_id="talk")
        roll = state.roll_dice(session, *state.action_dice_settings(action), client_rolls=[10])
        state.apply_action_result(session, action, roll)

        state.apply_gm_payload(
            session,
            "GM text",
            {"state_delta": {"current_scene": "dragon_valley", "gold_change": 999}, "choices": [{"text": "bad"}]},
        )

        self.assertEqual(state.current_scene_id(session), "start")
        self.assertEqual(session["character"]["gold"], 0)
        self.assertNotEqual(session["choices"][0]["text"], "bad")

    def test_dragon_rpg_city_actions_stay_nested_under_city_group(self):
        base_path = state.HOST_ROOT / "prompt" / "processed" / "dragon_rpg.json"
        public = state.create_session(str(base_path), gm_mode="full")
        session = state.load_session(public["id"])
        choices = current_action_choices(session)
        choice_texts = [choice["text"] for choice in choices]

        self.assertIn("城下町を探索する", choice_texts)
        self.assertNotIn("鍛冶屋へ向かう", choice_texts)
        city_choice = next(choice for choice in choices if choice.get("action_id") == "explore_castle_town")
        self.assertEqual(
            [child.get("action_id") for child in city_choice.get("children", [])],
            ["go_forge", "go_inn", "go_magic_shop", "go_item_shop", "go_alley"],
        )

        action = state.resolve_action(session, action_id="go_forge")
        self.assertIsNotNone(action)
        self.assertEqual(action["text"], "鍛冶屋へ向かう")

    def test_dragon_rpg_intro_actions_disable_after_use(self):
        expected_once_flags = {
            "ask_king_info": "heard_king_info",
            "ask_general_advice": "asked_general_advice",
            "check_supplies": "checked_supplies",
        }

        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            with self.subTest(filename=filename):
                path = state.HOST_ROOT / "prompt" / "processed" / filename
                public = state.create_session(str(path), gm_mode="semi")
                session = state.load_session(public["id"])

                for action_id, once_flag in expected_once_flags.items():
                    action = state.resolve_action(session, action_id=action_id)
                    self.assertIsNotNone(action)
                    self.assertEqual(action.get("once"), once_flag)
                    roll = state.roll_dice(
                        session,
                        *state.action_dice_settings(action),
                        client_rolls=[20],
                    )
                    state.apply_action_result(session, action, roll)

                choices = {
                    choice.get("action_id"): choice
                    for choice in state.public_session(session)["choices"]
                }
                for action_id, once_flag in expected_once_flags.items():
                    self.assertTrue(session["flags"].get(once_flag))
                    self.assertFalse(choices[action_id]["enabled"])
                    self.assertIn("完了済み", choices[action_id]["disabled_reason"])

    def test_dragon_rpg_action_groups_and_story_once_flags(self):
        expected_groups = {
            "forge": {
                "buy_equipment": ["buy_adamantite_armor", "buy_ice_amulet"],
            },
            "inn": {
                "ask_ian": ["ask_ian_legend", "ask_ian_advice", "rest_at_inn"],
                "ask_robin": ["invite_robin", "ask_robin_rumor"],
            },
        }
        expected_once = {
            "ask_king_info",
            "ask_general_advice",
            "check_supplies",
            "ask_blacksmith_weakness",
            "show_sword_to_blacksmith",
            "accept_sword_fusion",
            "ask_ian_legend",
            "ask_ian_advice",
            "invite_robin",
            "ask_robin_rumor",
            "ask_elder_weakness",
        }

        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            with self.subTest(filename=filename):
                path = state.HOST_ROOT / "prompt" / "processed" / filename
                pack = json.loads(path.read_text(encoding="utf-8-sig"))
                locations = {location["id"]: location for location in pack["locations"]}

                all_actions = {}
                for location in locations.values():
                    for action in self._iter_scenario_actions(location.get("actions")):
                        all_actions[action["id"]] = action

                for location_id, groups in expected_groups.items():
                    top_actions = {
                        action["id"]: action
                        for action in locations[location_id].get("actions", [])
                    }
                    for group_id, child_ids in groups.items():
                        self.assertEqual(
                            [child.get("id") for child in top_actions[group_id].get("children", [])],
                            child_ids,
                        )

                for action_id in expected_once:
                    self.assertTrue(all_actions[action_id].get("once"), action_id)

                show_sword = all_actions["show_sword_to_blacksmith"]
                self.assertEqual(show_sword.get("requirements"), {"character_id": "hero"})

                buy_armor = all_actions["buy_adamantite_armor"]
                self.assertEqual(buy_armor.get("disabled_after"), "bought_adamantite_armor")
                self.assertIn({"gold_change": -20}, buy_armor.get("effects", []))
                self.assertIn(
                    {"add_item": {"name": "アダマンタイトの鎧", "quantity": 1}},
                    buy_armor.get("effects", []),
                )

    def test_dragon_rpg_robin_quest_has_an_executable_route_to_goblin_fort(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            with self.subTest(filename=filename):
                path = state.HOST_ROOT / "prompt" / "processed" / filename
                public = state.create_session(str(path), gm_mode="semi")
                session = state.load_session(public["id"])
                session["world_state"] = {"scene_id": "throne_room", "location_id": "inn"}
                session.setdefault("flags", {})["recruited_robin"] = True
                session["choices"] = state.fallback_choices_for_session(session)
                visible_action_ids = {
                    choice.get("action_id") for choice in state.public_session(session)["choices"]
                }

                action = state.resolve_action(session, action_id="accept_robin_goblin_quest")

                self.assertIn("accept_robin_goblin_quest", visible_action_ids)
                self.assertIsNotNone(action)
                roll = state.roll_dice(session, *state.action_dice_settings(action))
                state.apply_action_result(session, action, roll)
                self.assertEqual(state.current_location_id(session), "goblin_fort")
                self.assertFalse(state.ensure_combat_started(session))

    def test_dragon_rpg_encounters_wait_for_the_player_to_choose_combat(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            with self.subTest(filename=filename):
                path = state.HOST_ROOT / "prompt" / "processed" / filename
                public = state.create_session(str(path), gm_mode="semi")
                session = state.load_session(public["id"])
                session["world_state"] = {
                    "scene_id": "dark_forest",
                    "location_id": "dark_forest_loc",
                }
                session.pop("combat", None)

                self.assertFalse(state.ensure_combat_started(session))
                action = state.resolve_action(session, action_id="attack_slime")
                self.assertIsNotNone(action)
                with patch.object(app_module, "chat_completion") as completion:
                    result = app_module._run_turn(
                        session,
                        app_module.TurnRequest(
                            text=action["text"],
                            action_id="attack_slime",
                        ),
                    )

                completion.assert_not_called()
                self.assertTrue(result["in_combat"])
                self.assertEqual(session["combat"]["status"], "active")
                self.assertIn("スライム", result["combat"]["intro_text"])
                self.assertIn("スライム", result["messages"][-1]["text"])

    def test_combat_resolution_controls_use_player_facing_copy(self):
        html = (state.HOST_ROOT.parent / "client" / "index.html").read_text(encoding="utf-8")
        javascript = (state.HOST_ROOT.parent / "client" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="combatResolveButton" type="button">戦闘終了</button>', html)
        self.assertNotIn("結果をGMへ渡す", html)
        self.assertNotIn("戦闘結果をGMへ渡しています", javascript)

    def test_robin_rumor_unlocks_class_specific_cursed_merchant_trade(self):
        path = state.HOST_ROOT / "prompt" / "processed" / "dragon_rpg_hybrid.json"
        public = state.create_session(str(path), gm_mode="semi", character_id="hero")
        session = state.load_session(public["id"])

        accepted, reason = state.commit_world_position(session, location_id="inn")
        self.assertTrue(accepted, reason)
        rumor = state.resolve_action(session, action_id="ask_robin_rumor")
        state.apply_action_result(
            session,
            rumor,
            {"expression": "none", "rolls": [], "total": 0, "dc": 0},
        )
        self.assertTrue(session["flags"].get("heard_robin_night_rumor"))

        accepted, reason = state.commit_world_position(session, location_id="alley")
        self.assertTrue(accepted, reason)
        session["choices"] = state.fallback_choices_for_session(session)
        visible_ids = {
            choice.get("action_id") for choice in state.public_session(session)["choices"]
        }
        self.assertIn("wait_for_night_in_alley", visible_ids)
        wait = state.resolve_action(session, action_id="wait_for_night_in_alley")
        state.apply_action_result(
            session,
            wait,
            {"expression": "none", "rolls": [], "total": 0, "dc": 0},
        )
        self.assertEqual(state.current_location_id(session), "alley_night")

        night_ids = {
            choice.get("action_id") for choice in state.public_session(session)["choices"]
        }
        self.assertIn("hear_curse_offer_hero", night_ids)
        self.assertNotIn("hear_curse_offer_cleric", night_ids)
        self.assertNotIn("hear_curse_offer_mage", night_ids)
        self.assertNotIn("hear_curse_offer_thief", night_ids)

        offer = state.resolve_action(session, action_id="hear_curse_offer_hero")
        state.apply_action_result(
            session,
            offer,
            {"expression": "none", "rolls": [], "total": 0, "dc": 0},
        )
        accept = state.resolve_action(session, action_id="accept_curse_offer_hero")
        self.assertIsNotNone(accept)
        state.apply_action_result(
            session,
            accept,
            {"expression": "none", "rolls": [], "total": 0, "dc": 0},
        )

        post_offer_ids = {
            choice.get("action_id") for choice in state.public_session(session)["choices"]
        }
        self.assertIn("pay_curse_price_hero", post_offer_ids)
        self.assertIn("betray_cursed_merchant", post_offer_ids)
        self.assertIn("呪われた聖剣", session["character"]["equipment"])
        self.assertNotIn("鉄の剣", session["character"]["equipment"])

        pay = state.resolve_action(session, action_id="pay_curse_price_hero")
        state.apply_action_result(
            session,
            pay,
            {"expression": "none", "rolls": [], "total": 0, "dc": 0},
        )
        inventory_names = {
            item.get("name") for item in session["character"]["inventory"]
            if isinstance(item, dict)
        }
        self.assertNotIn("鉄の剣", inventory_names)
        self.assertIn("呪われた聖剣", inventory_names)
        self.assertEqual(state.current_location_id(session), "alley_after")

    def test_dragon_rpg_action_groups_are_not_executable(self):
        path = state.HOST_ROOT / "prompt" / "processed" / "dragon_rpg_hybrid.json"
        public = state.create_session(str(path), gm_mode="semi", character_id="hero")
        session = state.load_session(public["id"])
        accepted, reason = state.commit_world_position(session, location_id="forge")
        self.assertTrue(accepted, reason)

        self.assertIsNone(state.resolve_action(session, action_id="buy_equipment"))
        self.assertIsNone(state.resolve_action(session, action_text="装備を買う"))
        self.assertIsNotNone(state.resolve_action(session, action_id="buy_adamantite_armor"))
        self.assertIsNotNone(state.resolve_action(session, action_id="buy_ice_amulet"))

    def test_dragon_rpg_forge_purchase_and_hero_choice_runtime(self):
        path = state.HOST_ROOT / "prompt" / "processed" / "dragon_rpg_hybrid.json"
        public = state.create_session(str(path), gm_mode="semi", character_id="hero")
        session = state.load_session(public["id"])
        accepted, reason = state.commit_world_position(session, location_id="forge")
        self.assertTrue(accepted, reason)
        session["character"]["gold"] = 50
        session["character"]["attributes"]["end"] = 10
        session["choices"] = current_action_choices(session)

        public_choices = {
            choice.get("action_id"): choice
            for choice in state.public_session(session)["choices"]
        }
        self.assertTrue(public_choices["show_sword_to_blacksmith"]["enabled"])
        self.assertEqual(
            [child.get("action_id") for child in public_choices["buy_equipment"]["children"]],
            ["buy_adamantite_armor", "buy_ice_amulet"],
        )
        self.assertNotIn("accept_sword_fusion", public_choices)
        before_show_context = state.select_hybrid_context(session, include_debug=True)
        self.assertNotIn(
            "accept_sword_fusion",
            {action.get("action_id") for action in before_show_context["available_actions"]},
        )

        show_sword = state.resolve_action(session, action_id="show_sword_to_blacksmith")
        show_roll = state.roll_dice(
            session,
            *state.action_dice_settings(show_sword),
            client_rolls=[10],
        )
        state.apply_action_result(session, show_sword, show_roll)
        hybrid_context = state.select_hybrid_context(
            session,
            "鍛冶師に剣を見せる",
            include_debug=True,
        )
        self.assertEqual(hybrid_context["_debug"]["prepared_turn"], "show_sword_to_blacksmith")
        post_show_choices = {
            choice.get("action_id"): choice
            for choice in state.public_session(session)["choices"]
        }
        self.assertFalse(post_show_choices["show_sword_to_blacksmith"]["enabled"])
        self.assertTrue(post_show_choices["accept_sword_fusion"]["enabled"])
        self.assertIn(
            "accept_sword_fusion",
            {action.get("action_id") for action in hybrid_context["available_actions"]},
        )

        accept_fusion = state.resolve_action(session, action_id="accept_sword_fusion")
        fusion_roll = state.roll_dice(
            session,
            *state.action_dice_settings(accept_fusion),
            client_rolls=[10],
        )
        state.apply_action_result(session, accept_fusion, fusion_roll)
        fusion_context = state.select_hybrid_context(
            session,
            "提案を受け入れる",
            include_debug=True,
        )
        self.assertEqual(fusion_context["_debug"]["prepared_turn"], "accept_sword_fusion")
        inventory_names = {item.get("name") for item in session["character"]["inventory"]}
        self.assertNotIn("鉄の剣", inventory_names)
        self.assertIn("氷鉄の大剣", inventory_names)

        action = state.resolve_action(session, action_id="buy_adamantite_armor")
        roll = state.roll_dice(session, *state.action_dice_settings(action), client_rolls=[10])
        state.apply_action_result(session, action, roll)
        self.assertEqual(session["character"]["gold"], 30)
        self.assertTrue(
            any(item.get("name") == "アダマンタイトの鎧" for item in session["character"]["inventory"])
        )

        mage_public = state.create_session(str(path), gm_mode="semi", character_id="mage")
        mage = state.load_session(mage_public["id"])
        accepted, reason = state.commit_world_position(mage, location_id="forge")
        self.assertTrue(accepted, reason)
        mage["choices"] = current_action_choices(mage)
        mage_choices = {
            choice.get("action_id"): choice
            for choice in state.public_session(mage)["choices"]
        }
        self.assertFalse(mage_choices["show_sword_to_blacksmith"]["enabled"])

    def test_dragon_rpg_base_and_hybrid_actions_stay_aligned(self):
        processed = state.HOST_ROOT / "prompt" / "processed"
        base = json.loads((processed / "dragon_rpg.json").read_text(encoding="utf-8-sig"))
        hybrid = json.loads((processed / "dragon_rpg_hybrid.json").read_text(encoding="utf-8-sig"))
        base_actions = {location["id"]: location.get("actions", []) for location in base["locations"]}
        hybrid_actions = {location["id"]: location.get("actions", []) for location in hybrid["locations"]}

        self.assertEqual(base_actions, hybrid_actions)

    def test_dragon_rpg_contains_no_ascii_question_mark_placeholders(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            with self.subTest(filename=filename):
                path = state.HOST_ROOT / "prompt" / "processed" / filename
                pack = json.loads(path.read_text(encoding="utf-8-sig"))
                broken_paths = []

                def find_broken(value, value_path="$"):
                    if isinstance(value, dict):
                        for key, item in value.items():
                            find_broken(item, f"{value_path}.{key}")
                    elif isinstance(value, list):
                        for index, item in enumerate(value):
                            find_broken(item, f"{value_path}[{index}]")
                    elif isinstance(value, str) and "??" in value:
                        broken_paths.append(value_path)

                find_broken(pack)
                self.assertEqual(broken_paths, [])

    def test_dragon_rpg_hybrid_action_ids_exist_in_base_pack(self):
        base_path = state.HOST_ROOT / "prompt" / "processed" / "dragon_rpg.json"
        hybrid_path = state.HOST_ROOT / "prompt" / "processed" / "dragon_rpg_hybrid.json"
        base = json.loads(base_path.read_text(encoding="utf-8-sig"))
        hybrid = json.loads(hybrid_path.read_text(encoding="utf-8-sig"))

        def iter_actions(actions):
            for action in actions or []:
                if not isinstance(action, dict):
                    continue
                yield action
                yield from iter_actions(action.get("children"))

        action_ids = {
            action.get("id")
            for location in base.get("locations", [])
            for action in iter_actions(location.get("actions", []))
            if isinstance(action, dict) and action.get("id")
        }
        missing = [
            (location.get("id"), turn.get("id"), turn.get("action_id"))
            for location in hybrid.get("locations", [])
            for turn in (location.get("hybrid") or {}).get("prepared_turns", [])
            if isinstance(turn, dict) and turn.get("action_id") and turn.get("action_id") not in action_ids
        ]

        self.assertFalse(missing)

    def test_debug_errors_redact_api_credentials(self):
        secret = "AIzaSyExampleSecretValue1234567890"
        message = (
            f"https://example.test/generate?key={secret} "
            f"raw={secret} Authorization: Bearer token-value"
        )

        redacted = app_module._redact_secrets(message)

        self.assertNotIn(secret, redacted)
        self.assertNotIn("token-value", redacted)
        self.assertIn("key=[REDACTED]", redacted)
        self.assertIn("Bearer [REDACTED]", redacted)

    @staticmethod
    def _iter_scenario_actions(actions):
        for action in actions or []:
            if not isinstance(action, dict):
                continue
            yield action
            yield from StateTests._iter_scenario_actions(action.get("children"))


if __name__ == "__main__":
    unittest.main()
