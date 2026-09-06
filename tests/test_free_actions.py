import json
import uuid
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from host import app as app_module, combat, free_actions, state
from host.llm_client import LLMClientError, _gemini_payload, chat_completion
from host.scenario_context import fallback_choices_for_session, select_scenario_context


def plan(**changes):
    value = {"kind": "interact", "action_id": "", "operation": "distract", "target_id": "forest_slime",
             "item_id": "trail_ration", "advance": True, "approach": "携帯食で誘って通り抜ける", "reply": ""}
    value.update(changes)
    return value


class FreeActionTests(unittest.TestCase):
    def setUp(self):
        root = Path.cwd() / ".tmp-test"
        root.mkdir(exist_ok=True)
        self.temp_path = root / f"free-actions-{uuid.uuid4().hex}"
        self.temp_path.mkdir()
        self.save_patch = patch.object(state, "SAVE_DIR", self.temp_path)
        self.save_patch.start()
        self.addCleanup(self.save_patch.stop)
        self.config_patch = patch.object(app_module, "load_config", return_value={"debug_llm": False})
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)

    def session(self, mode="full"):
        public = state.create_session(str(Path("host/prompt/processed/dragon_rpg.json")), gm_mode=mode, character_id="hero")
        session = state.load_session(public["id"])
        state.commit_world_position(session, location_id="dark_forest_loc")
        session["needs_opening"] = False
        return session

    def turn(self, session, response, text="携帯食を投げて、戦わずに通り抜ける"):
        raw = json.dumps(response, ensure_ascii=False) if isinstance(response, dict) else response
        with patch.object(app_module, "chat_completion", return_value=raw) as completion:
            result = app_module._run_turn(session, app_module.TurnRequest(text=text, client_dice={"rolls": [20]}))
        self.assertEqual(completion.call_count, 1)
        self.assertEqual(result["last_turn_metrics"]["model_calls"], 1)
        return result

    def test_negation_and_new_method_never_execute_from_lexical_overlap(self):
        for text in ("スライムを攻撃しない", "スライムに餌を投げて通り抜ける", "スライムと戦う？"):
            session = self.session()
            if not text.endswith("？"):
                self.assertNotEqual(state.resolve_player_intent(session, text)["status"], "resolved")
            self.turn(session, plan(kind="dialogue", operation="", target_id="", item_id="", advance=False,
                                    reply="戦わずに進む方法を考えよう。"), text)
            self.assertFalse(combat.combat_is_active(session))
            self.assertEqual(session["dice_log"], [])

    def test_food_bypass_consumes_one_and_persists_without_kill_or_reward(self):
        session = self.session()
        before_gold = session["character"]["gold"]
        self.turn(session, plan())
        saved = state.load_session(session["id"])
        self.assertEqual(state.current_location_id(saved), "lost_goblin_crossroads")
        food = next(x for x in saved["character"]["inventory"] if x.get("id") == "trail_ration")
        self.assertEqual(food["quantity"], 1)
        self.assertEqual(saved["character"]["gold"], before_gold)
        self.assertNotIn("defeated_slime", saved["flags"])
        self.assertFalse(combat.combat_is_active(saved))
        change = saved["scene_changes"]["dark_forest_loc"]["forest_slime"]
        self.assertEqual(change["resolution"], "distracted")
        self.assertFalse(change["enemy_defeated"])
        self.assertTrue(change["source_event_id"])
        self.assertEqual(change["actor_id"], "hero")
        state.commit_world_position(saved, location_id="dark_forest_loc")
        choices = fallback_choices_for_session(saved)
        self.assertEqual([x["action_id"] for x in choices], ["pass_cleared_forest"])
        context = json.loads(free_actions.build_plan_messages(saved, "戻ってきた")[1]["content"])
        self.assertEqual(context["changes_here"]["forest_slime"]["resolution"], "distracted")

    def test_missing_food_rejects_without_spending_or_accepting_success_prose(self):
        session = self.session()
        session["character"]["inventory"] = [x for x in session["character"]["inventory"] if x.get("id") != "trail_ration"]
        before = deepcopy(session["character"])
        result = self.turn(session, plan(reply="成功！敵を倒して千枚の金貨を手にした。"))
        self.assertEqual(session["character"], before)
        self.assertEqual(state.current_location_id(session), "dark_forest_loc")
        self.assertNotIn("千枚", result["messages"][-1]["text"])

    def test_invalid_destination_rolls_back_food_and_events(self):
        session = self.session()
        location = state._current_location_record(session)
        location["obstacles"][0]["destination"] = "does_not_exist"
        before = deepcopy(session)
        result = free_actions.adjudicate(session, plan())
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(session, before)

    def test_distraction_then_pass_uses_only_one_ration(self):
        session = self.session()
        self.turn(session, plan(advance=False), "携帯食を投げて気を引く")
        self.assertEqual(state.current_location_id(session), "dark_forest_loc")
        self.turn(session, plan(operation="sneak", item_id=""), "その隙に通り抜ける")
        self.assertEqual(state.current_location_id(session), "lost_goblin_crossroads")
        self.assertEqual(session["dice_log"], [])
        self.assertEqual(next(x for x in session["character"]["inventory"] if x.get("id") == "trail_ration")["quantity"], 1)

    def test_sneak_uses_server_roll_and_failure_has_persistent_cost(self):
        session = self.session()
        sp = session["character"]["sp"]
        with patch.object(state.random, "randint", return_value=1):
            self.turn(session, plan(operation="sneak", item_id=""), "茂みを通ってこっそり進む")
        self.assertEqual(session["dice_log"][-1]["rolls"], [1])
        self.assertEqual(session["character"]["sp"], sp - 1)
        self.assertEqual(state.current_location_id(session), "dark_forest_loc")
        self.assertEqual(session["scene_changes"]["dark_forest_loc"]["forest_slime"]["alertness"], 1)
        self.turn(session, plan())
        self.assertEqual(state.current_location_id(session), "lost_goblin_crossroads")

    def test_preparation_generalizes_to_new_object_and_is_used_once(self):
        session = self.session()
        location = state._current_location_record(session)
        location["objects"].append({"id": "wooden_crate", "name": "木箱", "traits": ["movable"], "description": "動かせる空の木箱。"})
        self.turn(session, plan(operation="prepare", item_id="wooden_crate", advance=False), "木箱を動かして視界を遮る準備をする")
        self.turn(session, plan(operation="prepare", item_id="wooden_crate", advance=False), "さらに箱を積む")
        with patch.object(state.random, "randint", return_value=6):
            self.turn(session, plan(operation="sneak", item_id=""), "箱の陰から進む")
        self.assertEqual(session["dice_log"][-1]["dc"], 11)
        self.assertEqual(state.current_location_id(session), "lost_goblin_crossroads")
        self.assertNotIn("prepared", session["scene_changes"]["dark_forest_loc"]["forest_slime"])

    def test_conversation_has_no_three_turn_limit_and_preserves_preparation(self):
        session = self.session()
        self.turn(session, plan(operation="prepare", item_id="fallen_branches", advance=False))
        for _ in range(5):
            self.turn(session, plan(kind="dialogue", operation="", target_id="", item_id="", advance=False, reply="静かな森だね。"), "静かな森だね")
        self.assertNotIn("deviation_state", session)
        self.assertIn("prepared", session["scene_changes"]["dark_forest_loc"]["forest_slime"])
        self.assertEqual(session["dice_log"], [])

    def test_healing_item_consumes_only_when_it_can_heal(self):
        session = self.session()
        healing = plan(operation="use_item", target_id="self", item_id="薬草", advance=False)
        before = deepcopy(session["character"]["inventory"])
        self.turn(session, healing, "薬草を使う")
        self.assertEqual(session["character"]["inventory"], before)
        session["character"]["hp"] -= 3
        self.turn(session, healing, "薬草で傷を手当てする")
        self.assertEqual(session["character"]["hp"], session["character"]["max_hp"])
        self.assertFalse(any(x.get("name") == "薬草" for x in session["character"]["inventory"]))

    def test_invalid_plan_or_arbitrary_effects_cannot_change_state(self):
        for response in ("{broken", {**plan(), "state_delta": {"gold_change": 1000}}, plan(advance="true"), plan(target_id="unknown")):
            session = self.session()
            before = deepcopy(session["character"])
            self.turn(session, response)
            self.assertEqual(session["character"], before)
            self.assertEqual(state.current_location_id(session), "dark_forest_loc")
            self.assertEqual(session["dice_log"], [])

    def test_api_failure_keeps_state_and_does_not_retry_or_invent_success(self):
        session = self.session()
        before = deepcopy(session["character"])
        with patch.object(app_module, "chat_completion", side_effect=LLMClientError("offline")) as completion:
            result = app_module._run_turn(session, app_module.TurnRequest(text="罠を作る"))
        self.assertEqual(completion.call_count, 1)
        self.assertEqual(session["character"], before)
        self.assertIn("状況は変わっていません", result["messages"][-1]["text"])

    def test_existing_action_interpreted_by_api_does_not_call_a_second_model(self):
        session = self.session()
        self.turn(session, plan(kind="existing", operation="", target_id="", item_id="", advance=False,
                                action_id="attack_slime"), "剣を抜いてスライムに斬りかかる")
        self.assertTrue(combat.combat_is_active(session))
        self.assertEqual(len([m for m in session["messages"] if m["role"] == "user"]), 1)

    def test_button_combat_needs_no_model_and_cancels_distraction(self):
        session = self.session(mode="semi")
        self.turn(session, plan(advance=False))
        with patch.object(app_module, "chat_completion") as completion:
            app_module._run_turn(session, app_module.TurnRequest(text="スライムと戦う", action_id="attack_slime"))
        completion.assert_not_called()
        self.assertTrue(combat.combat_is_active(session))
        self.assertNotIn("distracted", session["scene_changes"]["dark_forest_loc"]["forest_slime"])

    def test_context_budget_keeps_every_location_as_complete_json(self):
        session = self.session()
        for location in session["scenario_pack"]["locations"]:
            session["world_state"] = {"scene_id": location["scene_id"], "location_id": location["id"]}
            raw = json.dumps(select_scenario_context(session), ensure_ascii=False)
            trimmed = state._trim_context_to_budget(raw, 3500)
            parsed = json.loads(trimmed)
            self.assertEqual(parsed["current_location"]["id"], location["id"])
            self.assertLessEqual(len(trimmed), 3500)

    def test_numeric_dice_modifiers_and_invalid_formulas(self):
        session = self.session()
        self.assertEqual(state.roll_dice(session, "1d20+2", client_rolls=[10])["total"], 12)
        self.assertEqual(state.roll_dice(session, "1d20-2", client_rolls=[10])["total"], 8)
        size = len(session["dice_log"])
        for expression in ("1d20+unknown", "1d20+str/3", "not a die"):
            with self.assertRaises(ValueError):
                state.roll_dice(session, expression)
        self.assertEqual(len(session["dice_log"]), size)

    def test_ending_blocks_stale_actions(self):
        session = self.session()
        session["world_state"] = {"scene_id": "dragon_valley", "location_id": "dragon_valley_loc"}
        ending = state._current_location_record(session)["combat"]["victory_effects"]
        state.apply_state_delta(session, ending, allow_world_transition=True)
        self.assertEqual(session["game_over"]["ending"], "ignis_defeated")
        self.assertEqual(fallback_choices_for_session(session), [])
        hp = session["character"]["hp"]
        with self.assertRaises(HTTPException):
            app_module._run_turn(session, app_module.TurnRequest(text="攻撃", action_id="attack_ignis_with_sword"))
        self.assertEqual(session["character"]["hp"], hp)

    def test_planner_uses_gemini_schema_and_one_attempt_budget(self):
        config = free_actions.planner_config({"request_timeout_seconds": 1800, "max_model_attempts": 5})
        payload = _gemini_payload(free_actions.build_plan_messages(self.session(), "通りたい"), config)
        self.assertEqual(payload["generationConfig"]["responseJsonSchema"], free_actions.PLAN_SCHEMA)
        self.assertEqual(config["request_timeout_seconds"], 15)
        self.assertEqual(config["max_model_attempts"], 1)
        with patch("host.llm_client._chat_completion_once", side_effect=LLMClientError("timeout")) as completion:
            with self.assertRaises(LLMClientError):
                chat_completion({"active_backend": "gemini", "debug_llm": False,
                                 "backends": {"gemini": {"model": "primary", "fallback_models": ["fallback"]}}}, [])
        completion.assert_called_once()

    def test_actual_combat_victory_records_obstacle_and_boss_ending(self):
        for location_id in ("dark_forest_loc", "dragon_valley_loc"):
            session = self.session()
            if location_id == "dragon_valley_loc":
                session["world_state"] = {"scene_id": "dragon_valley", "location_id": location_id}
            session["combat_start_requested"] = True
            self.assertTrue(combat.ensure_combat_started(session))
            for enemy in session["combat"]["enemies"]:
                enemy["hp"] = 1
            target = session["combat"]["enemies"][0]["id"]
            with patch.object(combat.random, "randint", return_value=1):
                combat.perform_combat_action(session, "attack", target_id=target)
            state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
            with patch.object(app_module, "chat_completion") as completion:
                result = app_module._run_combat_resolution(session)
            completion.assert_not_called()
            if location_id == "dark_forest_loc":
                self.assertEqual(result["current_location"], "lost_goblin_crossroads")
                self.assertEqual(session["scene_changes"][location_id]["forest_slime"]["resolution"], "defeated")
                self.assertTrue(session["scene_changes"][location_id]["forest_slime"]["enemy_defeated"])
            else:
                self.assertEqual(result["game_over"]["ending"], "ignis_defeated")
                self.assertEqual(result["choices"], [])
                self.assertIn("邪竜イグニスは倒れ", result["messages"][-1]["text"])

    def test_ollama_environment_cannot_override_api_destination(self):
        config = {"active_backend": "gemini", "backends": {"gemini": {"type": "gemini", "model": "configured-api", "base_url": "https://generativelanguage.googleapis.com/v1beta"}}}
        with patch.dict(state.os.environ, {"TRPG_ACTIVE_BACKEND": "gemini", "TRPG_LLM_BASE_URL": "", "TRPG_LLM_MODEL": "",
                                          "TRPG_OLLAMA_BASE_URL": "https://offline.example", "TRPG_OLLAMA_MODEL": "local"}):
            state._apply_config_env_overrides(config)
        self.assertEqual(config["backends"]["gemini"]["model"], "configured-api")
        self.assertEqual(config["backends"]["gemini"]["base_url"], "https://generativelanguage.googleapis.com/v1beta")

    def test_archived_backends_are_not_offered_in_game_settings(self):
        config = {"active_backend": "gemini", "archived_backends": ["ollama"],
                  "backends": {"gemini": {"model": "api"}, "ollama": {"model": "local"}}}
        with patch.object(app_module, "load_config", return_value=config):
            self.assertEqual(list(app_module.config_info()["backends"]), ["gemini"])
            with self.assertRaises(HTTPException):
                app_module.api_update_config(app_module.UpdateConfigRequest(active_backend="ollama"))

    def test_invalid_authored_die_is_rejected_before_effects(self):
        session = self.session()
        state._current_location_record(session)["actions"].append({"id": "bad_rule", "text": "設定不備の行動",
                                                                 "roll": {"dice_type": "1d20+unknown", "dc": 12},
                                                                 "effects": [{"gold_change": 999}]})
        gold = session["character"]["gold"]
        with self.assertRaises(HTTPException) as caught:
            app_module._run_turn(session, app_module.TurnRequest(text="設定不備の行動", action_id="bad_rule"))
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(session["character"]["gold"], gold)
        self.assertEqual(session["dice_log"], [])


if __name__ == "__main__":
    unittest.main()
