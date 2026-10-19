from __future__ import annotations

import io
import json
import os
import shutil
import unittest
import uuid
from contextlib import ExitStack, redirect_stderr
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import requests
from fastapi import HTTPException

from host import app, llm_client, llm_trace, state
from scripts.eval.requests import QuotaExhausted, evaluation_config


TOKEN = "fake-demo-token-044"
MESSAGES = [{"role": "user", "content": "少し考えよう。"}]


def response(status: int = 200, slot: str | None = "1", message: str = "", proxy_limit: bool = False) -> requests.Response:
    result = requests.Response()
    result.status_code = status
    result.url = "https://demo.example.invalid/v1beta/models/primary:generateContent"
    result.headers["content-type"] = "application/json"
    if slot is not None:
        result.headers["x-trpg-key-slot"] = slot
    if proxy_limit:
        result.headers["x-trpg-proxy-limit"] = "1"
    body = ({"error": {"message": message, "status": "RESOURCE_EXHAUSTED"}} if status >= 400
            else {"candidates": [{"content": {"parts": [{"text": message or "少し考えよう。"}]}}]})
    result._content = json.dumps(body, ensure_ascii=False).encode("utf-8")
    result.encoding = "utf-8"
    return result


class WorkerKeyRotationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.config = {"active_backend": "gemini", "max_model_attempts": 2, "debug_llm": True,
                       "backends": {"gemini": {"model": "primary", "fallback_models": ["fallback"],
                                               "base_url": "https://demo.example.invalid/v1beta", "api_key": TOKEN}}}
        self.stderr = io.StringIO()
        enter = self.stack.enter_context
        enter(redirect_stderr(self.stderr))
        enter(patch.dict(os.environ, {"GEMINI_API_KEYS": "", "GEMINI_API_KEY": "offline-key-044"}))
        self.post = enter(patch.object(llm_client.requests, "post", side_effect=AssertionError("unexpected HTTP")))
        enter(patch.object(llm_client.requests, "get", side_effect=AssertionError("unexpected HTTP")))

    def test_tokenless_demo_config_sends_no_key_header(self):
        del self.config["backends"]["gemini"]["api_key"]
        self.post.side_effect = [response(slot="0", message="ようこそ。")]
        self.assertEqual(llm_client.chat_completion(self.config, MESSAGES, session={}), "ようこそ。")
        headers = self.post.call_args.kwargs["headers"]
        self.assertNotIn("x-goog-api-key", headers)
        self.assertEqual(headers["x-trpg-key-start"], "0")

    def test_build_writes_tokenless_demo_config(self):
        from scripts import build_exe

        folder = Path.cwd() / ".tmp-test" / ("demo-build-" + uuid.uuid4().hex)
        folder.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, folder, True)
        with patch.object(build_exe.shutil, "copy2"):
            build_exe.write_demo_config(folder, "https://demo.example.invalid", "")
        config = json.loads((folder / "local_config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["backends"]["gemini"], {"base_url": "https://demo.example.invalid/v1beta"})

    def starts(self):
        return [call.kwargs["headers"].get("x-trpg-key-start") for call in self.post.call_args_list]

    def game_session(self):
        self.directory = Path.cwd() / ".tmp-test" / ("worker-044-" + uuid.uuid4().hex)
        self.directory.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        for module, name, folder in [(state, "SAVE_DIR", "saves"), (llm_trace, "TRACE_DIR", "traces"),
                                      (app, "DEBUG_COMPLETION_DIR", "completions")]:
            self.stack.enter_context(patch.object(module, name, self.directory / folder))
        return state.load_session(state.create_session(gm_mode="full", character_id="hero")["id"])

    def test_remembers_slot_in_serialized_session_and_resets_for_new_session(self):
        session = {}
        self.post.side_effect = [response(slot="2"), response(slot="2"), response(slot="0")]
        llm_client.chat_completion(self.config, MESSAGES, session=session)
        llm_client.chat_completion(self.config, MESSAGES, session=json.loads(json.dumps(session)))
        llm_client.chat_completion(self.config, MESSAGES, session={})
        self.assertEqual(self.starts(), ["0", "2", "0"])
        self.assertEqual(session, {"llm_worker_key_slot": {"gemini": 2}})

    def test_without_session_calls_start_at_zero_and_do_not_change_config(self):
        before = deepcopy(self.config)
        self.post.side_effect = [response(slot="2"), response(slot="1")]
        for _ in range(2):
            llm_client.chat_completion(self.config, MESSAGES)
        self.assertEqual(self.starts(), ["0", "0"])
        self.assertEqual(self.config, before)

    def test_context_session_is_shared_with_streaming_and_isolated_by_backend(self):
        session = {}
        self.config["backends"]["other"] = {**self.config["backends"]["gemini"], "type": "gemini"}
        self.post.side_effect = [response(slot="2"), response(slot="2"), response(slot="1"), response(slot="2")]
        with llm_client.session_keys(session):
            llm_client.chat_completion(self.config, MESSAGES)
            self.assertEqual(list(llm_client.stream_chat_completion(self.config, MESSAGES)), ["少し考えよう。"])
            self.config["active_backend"] = "other"
            llm_client.chat_completion(self.config, MESSAGES)
        self.config["active_backend"] = "gemini"
        llm_client.chat_completion(self.config, MESSAGES)
        self.assertEqual(self.starts(), ["0", "2", "0", "0"])
        self.assertEqual(session["llm_worker_key_slot"], {"gemini": 2, "other": 1})

    def test_proxy_limit_keeps_slot_and_token_available_without_immediate_retries(self):
        for message in ["Too many requests from this address. Please wait a minute.",
                        "The demo's daily request budget is used up. Please try again tomorrow (UTC)."]:
            with self.subTest(message=message):
                self.post.reset_mock()
                session = {"llm_worker_key_slot": {"gemini": 1}}
                self.post.side_effect = [response(429, None, message, proxy_limit=True), response()]
                with self.assertRaises(llm_client.LLMClientError) as caught:
                    llm_client.chat_completion(self.config, MESSAGES, session=session)
                self.assertEqual(str(caught.exception), message)
                self.assertEqual(self.post.call_count, 1)
                self.assertEqual(session, {"llm_worker_key_slot": {"gemini": 1}})
                llm_client.chat_completion(self.config, MESSAGES, session=session)
                self.assertEqual(self.starts(), ["1", "1"])

    def test_all_exhausted_preserves_error_and_does_not_retry_until_new_session(self):
        session = {}
        self.post.side_effect = [response(429, "3", llm_client.WORKER_KEYS_EXHAUSTED), response(slot="0")]
        with self.assertRaises(llm_client.LLMClientError) as caught:
            llm_client.chat_completion(self.config, MESSAGES, session=session)
        self.assertEqual(str(caught.exception), llm_client.WORKER_KEYS_EXHAUSTED)
        with self.assertRaises(llm_client.LLMClientError) as caught:
            list(llm_client.stream_chat_completion(self.config, MESSAGES, json.loads(json.dumps(session))))
        self.assertEqual(str(caught.exception), llm_client.WORKER_KEYS_EXHAUSTED)
        self.assertEqual(self.post.call_count, 1)
        self.assertEqual(session["llm_worker_key_slot"], {"gemini": 3})
        self.assertNotIn("llm_failed_keys", session)
        llm_client.chat_completion(self.config, MESSAGES, session={})
        self.assertEqual(self.starts(), ["0", "0"])

    def test_all_exhausted_without_session_does_not_persist_between_calls(self):
        self.post.side_effect = [response(429, "3", llm_client.WORKER_KEYS_EXHAUSTED), response()]
        with self.assertRaises(llm_client.LLMClientError):
            llm_client.chat_completion(self.config, MESSAGES)
        llm_client.chat_completion(self.config, MESSAGES)
        self.assertEqual(self.starts(), ["0", "0"])

    def test_errors_without_slot_do_not_poison_demo_token_or_rotate_local_keys(self):
        self.config["backends"]["gemini"]["api_keys"] = [TOKEN, "unused-demo-token"]
        for status, message in [(429, "Please wait a minute."), (401, "Invalid demo token."),
                                (403, "This endpoint only serves the game client."), (400, "API_KEY_INVALID")]:
            with self.subTest(status=status):
                self.post.reset_mock()
                self.post.side_effect = [response(status, None, message)]
                session = {}
                with self.assertRaises(llm_client.LLMClientError) as caught:
                    llm_client.chat_completion(self.config, MESSAGES, session=session)
                self.assertEqual(str(caught.exception), message)
                self.assertEqual(self.post.call_count, 1)
                self.assertEqual(session, {})

    def test_non_key_errors_keep_model_fallback_and_use_last_attempted_slot(self):
        for failure in [response(503, "2"), response(404, "2"), response(400, "2", "Invalid schema"),
                        requests.Timeout("timeout"), requests.ConnectionError("offline")]:
            with self.subTest(failure=type(failure).__name__):
                self.post.reset_mock()
                self.post.side_effect = [failure, response(slot="2")]
                session = {}
                llm_client.chat_completion(self.config, MESSAGES, session=session)
                self.assertEqual(self.starts(), ["0", "0" if isinstance(failure, Exception) else "2"])
                self.assertIn("/models/fallback:", self.post.call_args.args[0])
                self.assertNotIn("llm_failed_keys", session)
                self.assertNotIn("llm_worker_keys_exhausted", session)

    def test_missing_and_malformed_slot_headers_leave_memory_unchanged(self):
        for slot in [None, "", "-1", "1.5", "no-slot", "9" * 100]:
            with self.subTest(slot=slot):
                session = {"llm_worker_key_slot": {"gemini": 2}}
                self.post.side_effect = [response(slot=slot)]
                llm_client.chat_completion(self.config, MESSAGES, session=session)
                self.assertEqual(session, {"llm_worker_key_slot": {"gemini": 2}})

    def test_demo_token_takes_precedence_over_personal_environment_keys(self):
        self.post.side_effect = [response()]
        with patch.dict(os.environ, {"GEMINI_API_KEYS": "personal-first,personal-second"}):
            llm_client.chat_completion(self.config, MESSAGES)
        self.assertEqual(self.post.call_args.kwargs["headers"]["x-goog-api-key"], TOKEN)

    def test_direct_google_keeps_043_rotation_and_never_sends_worker_headers(self):
        self.config["backends"]["gemini"].update(base_url="https://generativelanguage.googleapis.com/v1beta",
                                                api_keys=["fake-first-044", "fake-second-044"])
        session = {}
        self.post.side_effect = [response(429), response()]
        llm_client.chat_completion(self.config, MESSAGES, session=session)
        self.assertEqual(self.starts(), [None, None])
        self.assertEqual(len(session["llm_failed_keys"]["gemini"]), 1)
        self.assertNotIn("llm_worker_key_slot", session)

    def test_request_policy_quota_metadata_survives_without_rotating_demo_token(self):
        config = evaluation_config(self.config, "gemini", "primary", rpm=0)
        config["max_model_attempts"] = 2
        config["backends"]["gemini"]["fallback_models"] = ["fallback"]
        quota = response(429, None)
        quota._content = json.dumps({"error": {"quotaId": "PerDay", "retryDelay": "46800s"}}).encode("utf-8")
        self.post.side_effect = [quota]
        session = {}
        with self.assertRaises(QuotaExhausted) as caught:
            llm_client.chat_completion(config, MESSAGES, session=session)
        self.assertEqual(caught.exception.details["retry_after_seconds"], 46800)
        self.assertEqual(self.post.call_count, 1)
        self.assertEqual(session, {})

    def test_token_never_appears_in_session_logs_output_usage_or_error(self):
        session = {}
        good = response(message=TOKEN)
        body = good.json()
        body["usageMetadata"] = {"detail": TOKEN}
        good._content = json.dumps(body).encode("utf-8")
        self.post.side_effect = [good, response(429, None, f"Please wait a minute. {TOKEN}", proxy_limit=True)]
        usage = {}
        text = llm_client.chat_completion(self.config, MESSAGES, usage, session)
        with self.assertRaises(llm_client.LLMClientError) as caught:
            llm_client.chat_completion(self.config, MESSAGES, session=session)
        self.assertNotIn(TOKEN, text + json.dumps([session, usage]) + str(caught.exception) + self.stderr.getvalue())

    def test_game_calls_share_saved_slots_without_tokens_in_saves_or_traces(self):
        session = self.game_session()
        narration = json.dumps({"gm_text": "少し考えよう。", "state_delta": {}, "choices": []}, ensure_ascii=False)
        plan = json.dumps({"kind": "dialogue", "action_id": "", "operation": "", "target_id": "", "item_id": "",
                           "advance": False, "approach": "", "reply": "少し考えよう。"}, ensure_ascii=False)
        self.post.side_effect = [response(message=narration), response(message=plan), response(message=narration),
                                 response(message=narration)]
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
        self.assertEqual(self.starts(), ["0", "1", "1", "1"])
        self.assertEqual(state.load_session(session["id"])["llm_worker_key_slot"], {"gemini": 1})
        traces = [json.loads(line) for path in (self.directory / "traces").glob("*.jsonl")
                  for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([record["call_type"] for record in traces], ["opening", "plan", "narration", "narration"])
        serialized = self.stderr.getvalue() + json.dumps(state.public_session(session))
        serialized += "".join(path.read_text(encoding="utf-8") for path in self.directory.rglob("*.json*"))
        self.assertNotIn(TOKEN, serialized)

    def test_exhaustion_is_saved_even_when_game_request_fails(self):
        session = self.game_session()
        self.config["demo_fallback_on_error"] = False
        self.post.side_effect = [response(429, "3", llm_client.WORKER_KEYS_EXHAUSTED)]
        with patch.object(app, "load_config", return_value=self.config):
            with self.assertRaises(HTTPException) as caught:
                app._run_opening(session)
        self.assertIn(llm_client.WORKER_KEYS_EXHAUSTED, caught.exception.detail)
        saved = state.load_session(session["id"])
        self.assertEqual(saved["llm_worker_key_slot"], {"gemini": 3})
        with self.assertRaises(llm_client.LLMClientError):
            llm_client.chat_completion(self.config, MESSAGES, session=saved)
        self.assertEqual(self.post.call_count, 1)
        self.assertNotIn(TOKEN, json.dumps(saved) + caught.exception.detail + self.stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
