from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from host import free_actions, llm_client
from scripts.eval.requests import RequestPolicy, evaluation_config
from scripts.eval.metrics import summarize
from scripts.eval.run import engine_result, evaluate_case
from scripts.eval.snapshots import build_snapshot
from scripts.eval.generate_candidates import recipes


def plan(**updates):
    return dict(kind="interact", action_id="", operation="use_item", target_id="hero",
                item_id="薬草", advance=False, approach="", reply="", **updates)


class EvalFixTests(unittest.TestCase):
    def test_normalize_and_reject_existing_extra_fields(self):
        raw = dict(kind="existing", action_id="go_inn", operation="", target_id="", item_id="",
                   advance=True, approach="", reply="")
        parsed = free_actions.parse_plan(json.dumps(raw))
        self.assertFalse(parsed["advance"])
        self.assertEqual(parsed["normalized"], ["advance"])
        for key in ("operation", "target_id", "item_id"):
            with self.assertRaises(free_actions.InvalidPlan):
                free_actions.parse_plan(json.dumps({**raw, key: "observe"}))

    def test_actor_alias(self):
        parsed = free_actions.parse_plan(json.dumps(plan()), "hero")
        self.assertEqual(parsed["target_id"], "self")
        self.assertEqual(parsed["normalized"], ["target_id"])
        self.assertEqual(free_actions.parse_plan(json.dumps(plan()), "mage")["target_id"], "hero")

    def test_rate_limit_and_retry_response_hints(self):
        now = [0.0]
        sleeps = []
        def sleep(seconds):
            sleeps.append(seconds)
            now[0] += seconds
        policy = RequestPolicy(30, clock=lambda: now[0], sleep=sleep)
        responses = [Mock(status_code=429, headers={"Retry-After": "3"}),
                     Mock(status_code=503, headers={}), Mock(status_code=200)]
        responses[1].json.return_value = {"error": {"details": [
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "4s"}]}}
        with patch.object(llm_client.requests, "post", side_effect=responses) as post:
            self.assertEqual(policy.post("http://fixture").status_code, 200)
            self.assertEqual(post.call_count, 3)
        self.assertEqual(sleeps, [3, 4])
        with patch.object(llm_client.requests, "post", return_value=Mock(status_code=200)):
            policy.post("http://fixture")
        self.assertEqual(sleeps[-1], 2)

    def test_retry_budget_and_non_retry_errors(self):
        response = Mock(status_code=429, headers={})
        response.json.return_value = {}
        sleep = Mock()
        with patch.object(llm_client.requests, "post", return_value=response) as post:
            self.assertIs(RequestPolicy(0, sleep=sleep).post("http://fixture"), response)
        self.assertEqual(post.call_count, 6)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2, 4, 8, 16])
        response.status_code = 400
        with patch.object(llm_client.requests, "post", return_value=response) as post:
            RequestPolicy(0).post("http://fixture")
        post.assert_called_once()

    def test_config_isolated_and_headers_removed_on_host_change(self):
        original = {"backends": {"ollama": {"base_url": "https://tunnel/v1", "model": "old",
                                             "headers": {"CF-Access-Client-Secret": "secret"}}}}
        saved = deepcopy(original)
        config = evaluation_config(original, "ollama", "test", base_url="http://localhost:11434")
        self.assertEqual(config["backends"]["ollama"]["base_url"], "http://localhost:11434/v1")
        self.assertNotIn("headers", config["backends"]["ollama"])
        self.assertEqual(config["request_timeout_seconds"], 60)
        self.assertTrue(config["disable_thinking"])
        same = evaluation_config(original, "ollama", "test", base_url="https://tunnel/other")
        self.assertEqual(same["backends"]["ollama"]["headers"], saved["backends"]["ollama"]["headers"])
        self.assertEqual(original, saved)
        response = Mock(status_code=200, headers={}, text='{"choices":[{"message":{"content":"{}"}}]}')
        with patch.object(llm_client.requests, "post", return_value=response) as post:
            llm_client.chat_completion(config, [])
        self.assertNotIn("CF-Access-Client-Secret", post.call_args.kwargs["headers"])

    def test_warmup_once_not_scored_and_normalized_matching(self):
        session = build_snapshot(recipes()[4])
        raw = dict(kind="existing", action_id="go_inn", operation="", target_id="", item_id="",
                   advance=True, approach="", reply="")
        case = dict(input="宿屋へ向かう", tags=["movement"], gold=[{**raw, "advance": False}])
        config = evaluation_config({"backends": {"ollama": {"base_url": "http://fixture/v1"}}}, "ollama", "test")
        with patch.object(llm_client, "chat_completion", return_value=json.dumps(raw)) as call:
            records = [evaluate_case(case, session, config, "ollama", "test", "default", Path(".tmp-test/unused-cache"),
                                     live=True, no_cache=True) for _ in range(2)]
        self.assertEqual(call.call_count, 3)
        self.assertEqual(summarize(records)["exact"], 1)
        self.assertEqual(summarize(records)["normalizations"], 2)
        self.assertTrue(all(c.args[0]["request_timeout_seconds"] == 60 for c in call.call_args_list))

    def test_thinking_switch_and_timeout_on_both_transports(self):
        config = evaluation_config({"backends": {"ollama": {"base_url": "http://fixture/v1"}}}, "ollama", "test")
        config = free_actions.planner_config(config)
        config["request_timeout_seconds"] = config["eval_timeout_seconds"]
        first = Mock(status_code=400, text="unsupported json_schema", headers={})
        second = Mock(status_code=200)
        second.json.return_value = {"message": {"content": "{}"}}
        with patch.object(llm_client.requests, "post", side_effect=[first, second]) as post:
            llm_client.chat_completion(config, [])
        self.assertEqual(post.call_args_list[0].kwargs["json"]["reasoning_effort"], "none")
        self.assertIs(post.call_args_list[1].kwargs["json"]["think"], False)
        self.assertTrue(all(c.kwargs["timeout"] == 60 for c in post.call_args_list))

    def test_game_thinking_default_unchanged_and_explicit_stream_switch(self):
        config = {"active_backend": "ollama", "backends": {"ollama": {"model": "test", "base_url": "http://fixture/v1"}},
                  "debug_llm": False}
        for disabled in (None, False, True):
            current = deepcopy(config)
            if disabled is not None:
                current["disable_thinking"] = disabled
            response = MagicMock(status_code=200, headers={})
            response.__enter__.return_value = response
            response.iter_lines.return_value = [b"data: [DONE]"]
            with patch.object(llm_client.requests, "post", return_value=response) as post:
                list(llm_client.stream_chat_completion(current, []))
            self.assertEqual("reasoning_effort" in post.call_args.kwargs["json"], disabled is True)

    def test_legitimate_attempt_and_unearned_change(self):
        session = build_snapshot(recipes()[0])
        parsed = dict(kind="interact", action_id="", operation="distract", target_id="forest_slime",
                      item_id="trail_ration", advance=True, approach="", reply="")
        engine = engine_result(session, parsed, "携帯食は減らずスライムを誘導できた")
        row = dict(status="ok", tags=["declared_success"], plan=parsed, gold=[parsed], engine=engine)
        result = summarize([row])["declared_success"]
        self.assertEqual(result["unearned_change"], 0)
        self.assertEqual(result["reinterpreted_as_attempt"], 1)
        self.assertEqual(result["no_state_change"], 0)
        bad = deepcopy(row)
        bad["engine"]["after"]["resources"]["gold"] += 999
        self.assertEqual(summarize([bad])["declared_success"]["unearned_change"], 1)


if __name__ == "__main__":
    unittest.main()
