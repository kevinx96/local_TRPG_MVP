from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import sys
import unittest
import uuid
from contextlib import ExitStack, redirect_stderr
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import requests
from fastapi import HTTPException
from pydantic import ValidationError

from host import app, generate_hybrid_scenario, llm_client, llm_trace, scenario_converter, state
from scripts import build_exe
from scripts.eval.requests import QuotaExhausted, evaluation_config

KEYS = ["fake-first-key-043", "fake-second-key-043"]
MESSAGES = [{"role": "user", "content": "少し考えよう。"}]


def response(status=200, body=None):
    result = requests.Response()
    result.status_code = status
    result.url = "https://fixture.invalid/generateContent"
    result.headers["content-type"] = "application/json"
    if body is None:
        body = {"candidates": [{"content": {"parts": [{"text": "少し考えよう。"}]}}]}
    result._content = json.dumps(body, ensure_ascii=False).encode("utf-8")
    result.encoding = "utf-8"
    return result


def completion(text):
    return response(body={"candidates": [{"content": {"parts": [{"text": text}]}}]})


class APIKeyRotationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.directory = Path.cwd() / ".tmp-test" / ("keys-043-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        self.config = {"active_backend": "gemini", "max_model_attempts": 2, "debug_llm": True,
                       "backends": {"gemini": {"model": "primary", "fallback_models": ["fallback"], "api_keys": list(KEYS)}}}
        self.stderr = io.StringIO()
        enter = self.stack.enter_context
        enter(redirect_stderr(self.stderr))
        enter(patch.dict(os.environ, {"GEMINI_API_KEYS": "", "GEMINI_API_KEY": "offline-key-043"}))
        enter(patch.object(state, "SAVE_DIR", self.directory / "saves"))
        enter(patch.object(llm_trace, "TRACE_DIR", self.directory / "traces"))
        enter(patch.object(app, "DEBUG_COMPLETION_DIR", self.directory / "completions"))
        self.post = enter(patch.object(llm_client.requests, "post", side_effect=AssertionError("unexpected HTTP")))
        enter(patch.object(llm_client.requests, "get", side_effect=AssertionError("unexpected HTTP")))

    def keys_used(self):
        return [call.kwargs["headers"].get("x-goog-api-key", call.kwargs["headers"].get("Authorization"))
                for call in self.post.call_args_list]

    def session(self):
        return state.load_session(state.create_session(gm_mode="full", character_id="hero")["id"])

    def test_rotation_same_model_persists_session_and_new_session_restarts(self):
        session = self.session()
        self.post.side_effect = [response(429, {"error": {"status": "RESOURCE_EXHAUSTED"}}), response(), response(), response()]
        llm_client.chat_completion(self.config, MESSAGES, session=session)
        state.save_session(session)
        llm_client.chat_completion(self.config, MESSAGES, session=state.load_session(session["id"]))
        llm_client.chat_completion(self.config, MESSAGES, session=self.session())
        self.assertEqual(self.keys_used(), [KEYS[0], KEYS[1], KEYS[1], KEYS[0]])
        self.assertTrue(all("/models/primary:" in call.args[0] for call in self.post.call_args_list))
        self.assertEqual(self.post.call_args_list[0].kwargs["json"], self.post.call_args_list[1].kwargs["json"])
        self.assertEqual(session["llm_failed_keys"], {"gemini": [{
            "index": 0, "sha256": hashlib.sha256(KEYS[0].encode()).hexdigest()[:8]}]})

    def test_without_session_each_call_starts_from_first_key(self):
        before = deepcopy(self.config)
        self.post.side_effect = [response(429), response(), response(429), response()]
        for _ in range(2):
            llm_client.chat_completion(self.config, MESSAGES)
        self.assertEqual(self.keys_used(), KEYS * 2)
        self.assertEqual(self.config, before)

    def test_all_keys_exhausted_does_not_retry_models_or_leak_keys(self):
        session = {}
        self.post.side_effect = [response(429, {"error": " ".join(KEYS)}) for _ in KEYS]
        for _ in range(2):
            with self.assertRaises(llm_client.LLMClientError) as caught:
                llm_client.chat_completion(self.config, MESSAGES, session=session)
            self.assertEqual(str(caught.exception), llm_client.ALL_KEYS_EXHAUSTED)
            for key in KEYS:
                self.assertNotIn(key, str(caught.exception) + self.stderr.getvalue() + json.dumps(session))
        self.assertEqual(self.keys_used(), KEYS)

    def test_authentication_errors_switch_keys(self):
        for status, reason in [(401, "unauthenticated"), (403, "denied"), (400, "API_KEY_INVALID"),
                               (400, "API key not valid. Please pass a valid API key."),
                               (400, "invalid API key"), (400, "API_KEY_EXPIRED")]:
            with self.subTest(status=status, reason=reason):
                self.post.reset_mock()
                self.post.side_effect = [response(status, {"error": {"message": reason}}), response()]
                llm_client.chat_completion(self.config, MESSAGES)
                self.assertEqual(self.keys_used(), KEYS)

    def test_non_key_errors_use_model_fallback_without_marking_keys(self):
        for failure in [response(500), response(503), response(404), response(400, {"error": "invalid schema"}),
                        requests.Timeout("timeout " + KEYS[0]), requests.ConnectionError("connection " + KEYS[1])]:
            with self.subTest(failure=type(failure).__name__):
                self.post.reset_mock()
                self.post.side_effect = [failure, response()]
                session = {}
                llm_client.chat_completion(self.config, MESSAGES, session=session)
                self.assertEqual(self.keys_used(), [KEYS[0], KEYS[0]])
                self.assertIn("/models/fallback:", self.post.call_args.args[0])
                self.assertFalse(session["llm_failed_keys"]["gemini"])
        for key in KEYS:
            self.assertNotIn(key, self.stderr.getvalue())

    def test_model_fallback_skips_key_rejected_within_same_call(self):
        self.post.side_effect = [response(429), response(500), response()]
        llm_client.chat_completion(self.config, MESSAGES)
        self.assertEqual(self.keys_used(), [KEYS[0], KEYS[1], KEYS[1]])
        self.assertIn("/models/primary:", self.post.call_args_list[1].args[0])
        self.assertIn("/models/fallback:", self.post.call_args_list[2].args[0])

    def test_model_attempt_limit_does_not_limit_keys(self):
        self.config["max_model_attempts"] = 1
        self.post.side_effect = [response(429), response()]
        llm_client.chat_completion(self.config, MESSAGES)
        self.assertEqual(self.keys_used(), KEYS)

    def test_streaming_shares_rotation_and_memory(self):
        session = {}
        self.post.side_effect = [response(401), response(), response()]
        self.assertEqual(list(llm_client.stream_chat_completion(self.config, MESSAGES, session)), ["少し考えよう。"])
        list(llm_client.stream_chat_completion(self.config, MESSAGES, session))
        self.assertEqual(self.keys_used(), [KEYS[0], KEYS[1], KEYS[1]])

    def test_legacy_single_key_and_list_precedence(self):
        backend = self.config["backends"]["gemini"]
        backend["api_key"] = "fake-legacy-key-043"
        self.post.side_effect = [response(), response()]
        llm_client.chat_completion(self.config, MESSAGES)
        del backend["api_keys"]
        llm_client.chat_completion(self.config, MESSAGES)
        self.assertEqual(self.keys_used(), [KEYS[0], "fake-legacy-key-043"])

    def test_environment_list_and_legacy_single(self):
        backend = self.config["backends"]["gemini"]
        del backend["api_keys"]
        backend["api_key"] = "legacy-key"
        self.post.side_effect = [response(429), response(), response()]
        with patch.dict(os.environ, {"GEMINI_API_KEYS": f"  {KEYS[0]}, , {KEYS[1]}  ", "GEMINI_API_KEY": "unused-single"}):
            llm_client.chat_completion(self.config, MESSAGES)
        del backend["api_key"]
        with patch.dict(os.environ, {"GEMINI_API_KEY": KEYS[0]}):
            llm_client.chat_completion(self.config, MESSAGES)
        self.assertEqual(self.keys_used(), [KEYS[0], KEYS[1], KEYS[0]])

    def test_changed_order_or_key_does_not_skip_different_key(self):
        session = {}
        self.post.side_effect = [response(429), response(), response(), response()]
        llm_client.chat_completion(self.config, MESSAGES, session=session)
        self.config["backends"]["gemini"]["api_keys"] = list(reversed(KEYS))
        llm_client.chat_completion(self.config, MESSAGES, session=session)
        self.config["backends"]["gemini"]["api_keys"] = ["replacement-key", KEYS[1]]
        llm_client.chat_completion(self.config, MESSAGES, session=session)
        self.assertEqual(self.keys_used(), [KEYS[0], KEYS[1], KEYS[1], "replacement-key"])

    def test_memory_is_isolated_by_backend(self):
        self.config["backends"]["other"] = {**self.config["backends"]["gemini"], "type": "gemini"}
        self.post.side_effect = [response(429), response(), response()]
        session = {}
        llm_client.chat_completion(self.config, MESSAGES, session=session)
        self.config["active_backend"] = "other"
        llm_client.chat_completion(self.config, MESSAGES, session=session)
        self.assertEqual(self.keys_used(), [KEYS[0], KEYS[1], KEYS[0]])

    def test_openai_backend_rotates_authorization(self):
        self.config["active_backend"] = "remote"
        self.config["backends"]["remote"] = {"model": "primary", "base_url": "https://fixture.invalid/v1", "api_keys": KEYS}
        self.post.side_effect = [response(403), response(body={"choices": [{"message": {"content": "少し考えよう。"}}]})]
        llm_client.chat_completion(self.config, MESSAGES)
        self.assertEqual(self.keys_used(), [f"Bearer {key}" for key in KEYS])

    def test_empty_or_invalid_list_does_not_use_legacy_secret(self):
        backend = self.config["backends"]["gemini"]
        backend["api_key"] = KEYS[0]
        for value in ([], ["", " "], "invalid", [123]):
            with self.subTest(value=value):
                backend["api_keys"] = value
                with self.assertRaises(llm_client.LLMClientError):
                    llm_client.chat_completion(self.config, MESSAGES)
        self.post.assert_not_called()

    def test_game_paths_share_memory_and_never_serialize_secrets(self):
        session = self.session()
        narration = json.dumps({"gm_text": "少し考えよう。", "state_delta": {}, "choices": []}, ensure_ascii=False)
        plan = json.dumps({"kind": "dialogue", "action_id": "", "operation": "", "target_id": "", "item_id": "",
                           "advance": False, "approach": "", "reply": "少し考えよう。"}, ensure_ascii=False)
        self.post.side_effect = [response(429, {"error": " ".join(KEYS)}), completion(narration),
                                 completion(plan), completion(narration), completion(narration)]
        with patch.object(app, "load_config", side_effect=lambda: deepcopy(self.config)):
            app._run_opening(session)
            session = state.load_session(session["id"])
            app._run_free_turn(session, app.TurnRequest(text="少し考えよう。"))
            session = state.load_session(session["id"])
            with patch.object(app, "resolve_player_intent", return_value={"status": "legacy"}):
                app._run_turn(session, app.TurnRequest(text="少し考えよう。"))
            with patch.object(app, "combat_result_for_llm", return_value={"outcome": "fled"}), \
                 patch.object(app, "consume_combat_state_delta", return_value={}):
                app._run_combat_resolution(state.load_session(session["id"]))
            public_config = app.config_info()
        self.assertEqual(self.keys_used(), [KEYS[0]] + [KEYS[1]] * 4)
        traces = [json.loads(line) for path in (self.directory / "traces").glob("*.jsonl")
                  for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([record["call_type"] for record in traces], ["opening", "plan", "narration", "narration"])
        serialized = json.dumps([state.public_session(session), public_config]) + self.stderr.getvalue()
        serialized += "".join(path.read_text(encoding="utf-8") for path in self.directory.rglob("*.json*"))
        for key in KEYS:
            self.assertNotIn(key, serialized)
        self.assertNotIn("llm_failed_keys", state.public_session(session))

    def test_failure_still_saves_memory_and_safe_client_error(self):
        session = self.session()
        self.config["demo_fallback_on_error"] = False
        self.post.side_effect = [response(429, {"error": " ".join(KEYS)}) for _ in KEYS]
        with patch.object(app, "load_config", return_value=self.config):
            with self.assertRaises(HTTPException) as caught:
                app._run_opening(session)
        self.assertEqual(caught.exception.status_code, 502)
        saved = state.load_session(session["id"])
        self.assertEqual(len(saved["llm_failed_keys"]["gemini"]), 2)
        for key in KEYS:
            self.assertNotIn(key, caught.exception.detail + self.stderr.getvalue() + json.dumps(saved))
        self.post.side_effect = [response()]
        llm_client.chat_completion(self.config, MESSAGES)
        self.assertEqual(self.keys_used()[-1], KEYS[0])

    def test_config_writes_list_and_hides_keys_in_read_and_write_responses(self):
        config = deepcopy(self.config)
        config["backends"]["gemini"]["api_key"] = "legacy-key"
        saved_path = self.directory / "config.json"
        with patch.object(app, "load_config", return_value=config), \
             patch.object(app, "save_config", side_effect=lambda value: state.save_config(value, saved_path)):
            result = app.api_update_config(app.UpdateConfigRequest(active_backend="gemini", api_keys=list(reversed(KEYS))))
            public = app.config_info()
        self.assertEqual(json.loads(saved_path.read_text(encoding="utf-8"))["backends"]["gemini"]["api_keys"], list(reversed(KEYS)))
        self.assertNotIn("api_keys", result["backends"]["gemini"])
        for key in KEYS + ["legacy-key"]:
            self.assertNotIn(key, json.dumps([result, public]))
        for invalid in ("not-a-list", [123], [None]):
            with self.assertRaises(ValidationError):
                app.UpdateConfigRequest(active_backend="gemini", api_keys=invalid)

    def test_eval_daily_and_rate_quotas_rotate_without_retries(self):
        config = evaluation_config(self.config, "gemini", "primary", rpm=0)
        quota = {"error": {"quotaId": "PerDay", "retryDelay": "46800s", "message": " ".join(KEYS)}}
        self.post.side_effect = [response(429, quota), response(), response(429), response()]
        with patch("scripts.eval.requests.time.sleep", side_effect=AssertionError("unexpected sleep")):
            llm_client.chat_completion(config, MESSAGES)
            llm_client.chat_completion(config, MESSAGES)
        self.assertEqual(self.keys_used(), KEYS * 2)
        for key in KEYS:
            self.assertNotIn(key, json.dumps(config["_request_policy"].http_errors))

    def test_eval_all_daily_quotas_preserve_stop_metadata(self):
        config = evaluation_config(self.config, "gemini", "primary", rpm=0)
        quota = {"error": {"quotaId": "PerDay", "retryDelay": "46800s"}}
        self.post.side_effect = [response(429, quota), response(429, quota)]
        with self.assertRaises(QuotaExhausted) as caught:
            llm_client.chat_completion(config, MESSAGES)
        self.assertEqual(str(caught.exception), llm_client.ALL_KEYS_EXHAUSTED)
        self.assertEqual(caught.exception.details["retry_after_seconds"], 46800)
        self.assertEqual(self.keys_used(), KEYS)

    def test_eval_host_override_removes_key_list(self):
        original = {"backends": {"ollama": {"api_keys": KEYS, "api_key": "legacy", "base_url": "https://old/v1"}}}
        config = evaluation_config(original, "ollama", "primary", base_url="http://localhost:11434")
        self.assertNotIn("api_keys", config["backends"]["ollama"])
        self.assertNotIn("api_key", config["backends"]["ollama"])

    def test_packaging_audit_checks_all_config_and_environment_keys(self):
        host_dir = self.directory / "host"
        host_dir.mkdir()
        (host_dir / "local_config.json").write_text(json.dumps({"backends": {
            "gemini": {"api_keys": KEYS, "api_key": "legacy-key"}, "other": {"api_keys": ["short-key"]}}}), encoding="utf-8")
        with patch.object(build_exe, "ROOT", self.directory), \
             patch.dict(os.environ, {"GEMINI_API_KEYS": "env-first, env-second", "GEMINI_API_KEY": "env-single"}):
            secrets = build_exe._secrets()
        for key in KEYS + ["legacy-key", "short-key", "env-first", "env-second", "env-single"]:
            self.assertIn(key.encode(), secrets)

    def test_reordered_failed_key_is_not_retried_at_another_index(self):
        session = {}
        self.post.side_effect = [response(429), response(), response(429)]
        llm_client.chat_completion(self.config, MESSAGES, session=session)
        self.config["backends"]["gemini"]["api_keys"] = list(reversed(KEYS))
        with self.assertRaises(llm_client.LLMClientError):
            llm_client.chat_completion(self.config, MESSAGES, session=session)
        self.assertEqual(self.keys_used(), [KEYS[0], KEYS[1], KEYS[1]])

    def test_returned_content_usage_and_transport_errors_are_redacted(self):
        self.post.side_effect = [response(body={"usageMetadata": {"promptTokenCount": 10, "detail": KEYS[0]},
            "candidates": [{"content": {"parts": [{"text": KEYS[1]}]}}]})]
        usage = {}
        result = llm_client.chat_completion(self.config, MESSAGES, usage)
        for key in KEYS:
            self.assertNotIn(key, result + json.dumps(usage) + self.stderr.getvalue())
        self.post.side_effect = requests.ConnectionError(" ".join(KEYS))
        with self.assertRaises(llm_client.LLMClientError) as caught:
            llm_client.chat_completion(self.config, MESSAGES)
        for key in KEYS:
            self.assertNotIn(key, str(caught.exception) + self.stderr.getvalue())
        self.config["max_model_attempts"] = 1
        self.post.side_effect = [response(body={"usageMetadata": {"detail": KEYS[1]},
                                               "error": {"message": KEYS[0]}})]
        with self.assertRaises(llm_client.LLMClientError) as caught:
            llm_client.chat_completion(self.config, MESSAGES, usage)
        for key in KEYS:
            self.assertNotIn(key, json.dumps(usage) + str(caught.exception))

    def sdk(self, replies):
        google = ModuleType("google")
        sdk = ModuleType("google.generativeai")
        sdk.configure = Mock()
        sdk.GenerativeModel = Mock(return_value=Mock(generate_content=Mock(side_effect=replies)))
        google.generativeai = sdk
        self.stack.enter_context(patch.dict(sys.modules, {"google": google, "google.generativeai": sdk}))
        self.stack.enter_context(patch.object(state, "load_config", return_value=self.config))
        self.stack.enter_context(patch.object(generate_hybrid_scenario, "load_config", return_value=self.config, create=True))
        return sdk

    def sdk_error(self, code, message="", reason=""):
        error = RuntimeError(message)
        error.code = code
        error.reason = reason
        return error

    def test_scenario_conversion_rotates_keys_and_resets_each_call(self):
        reply = SimpleNamespace(text=json.dumps({"title": "冒険", "summary": "少し考えよう。"}))
        sdk = self.sdk([self.sdk_error(429), reply, self.sdk_error(400, reason="API_KEY_INVALID"), reply])
        for _ in range(2):
            result = scenario_converter.convert_with_gemini(Path("scenario.txt"), "少し考えよう。")
            self.assertEqual(result["title"], "冒険")
        self.assertEqual([call.kwargs["api_key"] for call in sdk.configure.call_args_list], KEYS * 2)
        self.assertTrue(all(call.kwargs["request_options"] == {"retry": None}
                            for call in sdk.GenerativeModel.return_value.generate_content.call_args_list))

    def test_hybrid_generation_remembers_keys_across_model_fallback_only_within_call(self):
        reply = SimpleNamespace(text=json.dumps({"hybrid": {"summary": "少し考えよう。"}}))
        sdk = self.sdk([self.sdk_error(429), self.sdk_error(503, "unavailable"), reply, reply])
        for _ in range(2):
            generate_hybrid_scenario.call_gemini_payload("少し考えよう。", ["primary", "fallback"])
        self.assertEqual([call.kwargs["api_key"] for call in sdk.configure.call_args_list],
                         [KEYS[0], KEYS[1], KEYS[1], KEYS[0]])
        self.assertEqual([call.args[0] for call in sdk.GenerativeModel.call_args_list],
                         ["primary", "primary", "fallback", "primary"])

    def test_authoring_all_keys_exhausted_raises_safe_client_error(self):
        sdk = self.sdk([self.sdk_error(429, KEYS[0]), self.sdk_error(403, KEYS[1])])
        with self.assertRaises(llm_client.LLMClientError) as caught:
            generate_hybrid_scenario.call_gemini_payload("少し考えよう。", ["primary", "fallback"])
        self.assertEqual(str(caught.exception), llm_client.ALL_KEYS_EXHAUSTED)
        self.assertEqual(sdk.configure.call_count, 2)


if __name__ == "__main__":
    unittest.main()
