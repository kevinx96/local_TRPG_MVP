from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from host import free_actions, llm_client, state
from scripts.eval import run
from scripts.eval.cache import cache_key, write_cache
from scripts.eval.compare import compare
from scripts.eval.metrics import summarize
from scripts.eval.requests import QuotaExhausted, RequestPolicy, evaluation_config
from scripts.eval.snapshots import ROOT, load_snapshot
from scripts.eval.variants import VARIANTS, clean_lenient, union_schema


def plan(**updates):
    return {**dict(kind="dialogue", action_id="", operation="", target_id="", item_id="",
                   advance=False, approach="", reply="少し考えよう。"), **updates}


def response(status, body):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(body).encode("utf-8")
    result.url = "http://fixture"
    return result


class SchemaShapeTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".tmp-test").mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / ".tmp-test")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.session = load_snapshot("forest_entrance_hero")
        self.config = evaluation_config({"backends": {"gemini": {"api_key": "fake", "base_url": "http://fixture"}}},
                                        "gemini", "fake", rpm=0)
        self.case = dict(id="fixture", snapshot="forest_entrance_hero", input="少し考えよう。",
                         gold=[plan()], tags=[], split="dev")

    def evaluate(self, variant, **kwargs):
        return run.evaluate_case(self.case, self.session, self.config, "gemini", "fake", variant,
                                 self.directory / "cache", **kwargs)

    def test_price_without_cached_rate_when_no_cached_tokens(self):
        prices = {"input_per_million": .25, "output_per_million": 1.5,
                  "cached_input_per_million": None}
        row = dict(status="invalid_plan", tags=[], gold=[], plan=None,
                   usage={"input_tokens": 1000, "output_tokens": 100})
        self.assertAlmostEqual(summarize([row], prices)["cost_per_turn"], .0004)

    def test_daily_quota_does_not_sleep_or_retry(self):
        response = Mock(status_code=429, headers={})
        response.json.return_value = {"error": {"details": [
            {"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel"}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "46800s"}]}}
        sleep = Mock()
        with patch.object(llm_client.requests, "post", return_value=response) as post:
            with self.assertRaises(llm_client.LLMClientError):
                RequestPolicy(0, sleep=sleep).post("http://fixture")
        post.assert_called_once()
        sleep.assert_not_called()

    def test_quota_threshold_daily_without_delay_and_policy_latch(self):
        bodies = [({"quotaId": "RequestsPerDay"}, None), ({"retryDelay": "120.01s"}, 120.01),
                  ({"retryDelay": "46800s"}, 46800)]
        for body, wait in bodies:
            with self.subTest(body=body):
                policy = RequestPolicy(0, sleep=Mock())
                result = response(429, {"error": body})
                result.headers["Retry-After"] = "1"
                with patch.object(llm_client.requests, "post", return_value=result) as post:
                    for _ in range(2):
                        with self.assertRaises(QuotaExhausted) as caught:
                            policy.post("http://fixture")
                    self.assertEqual(caught.exception.details["retry_after_seconds"], wait or 1)
                post.assert_called_once()
                policy.sleep.assert_not_called()
        sleep = Mock()
        with patch.object(llm_client.requests, "post", side_effect=[
                response(429, {"error": {"details": [{"@type": "google.rpc.RetryInfo", "retryDelay": "120s"}]}}), response(200, {})]):
            RequestPolicy(0, sleep=sleep).post("http://fixture")
        sleep.assert_called_once_with(120)
        with patch.object(llm_client.requests, "post", return_value=response(429, {"error": {"quotaId": "PerDay"}})):
            with self.assertRaises(QuotaExhausted) as caught:
                RequestPolicy(0).post("http://fixture")
        self.assertIsNone(caught.exception.details["retry_after_seconds"])

    def test_prices_cached_unknown_and_local_zero(self):
        rates = json.loads((ROOT / "eval/prices.json").read_text(encoding="utf-8"))["models"]
        row = dict(status="invalid_plan", tags=[], gold=[], plan=None,
                   usage={"input_tokens": 1000, "output_tokens": 100, "cached_tokens": 0})
        self.assertAlmostEqual(summarize([row], rates["gemini-3.1-flash-lite"])["cost_per_turn"], .0004)
        row["usage"]["cached_tokens"] = 50
        summary = summarize([row], rates["gemini-3.1-flash-lite"])
        self.assertIsNone(summary["cost_per_turn"])
        self.assertEqual(summary["cost_reported"], 0)
        self.assertEqual(summarize([row], rates["elyza-jp-8b-local"])["cost_per_turn"], 0)

    def test_lenient_all_kinds_and_conflict_fields(self):
        full = plan(action_id="attack_slime", operation="use_item", target_id="self", item_id="薬草",
                    advance=True, approach="様子を見る。")
        expected = {
            "existing": {"operation", "target_id", "item_id", "advance", "approach", "reply"},
            "interact": {"action_id"},
            "dialogue": {"action_id", "operation", "item_id", "advance"},
            "clarify": {"action_id", "operation", "item_id", "advance", "target_id"},
            "unsupported": {"action_id", "operation", "item_id", "advance", "target_id"},
        }
        for kind, fields in expected.items():
            with self.subTest(kind=kind):
                cleaned, audit = clean_lenient(json.dumps({**full, "kind": kind}))
                parsed = free_actions.parse_plan(cleaned)
                self.assertEqual(set(audit["cleared_fields"]), fields)
                self.assertEqual(set(audit["conflict_fields"]), fields - {"approach", "reply"})
                self.assertTrue(audit["conflict"])
                if kind == "dialogue":
                    self.assertEqual(parsed["target_id"], "self")
        _, audit = clean_lenient(json.dumps(plan(kind="existing", action_id="attack_slime")))
        self.assertFalse(audit["conflict"])
        self.assertEqual(audit["cleared_fields"], {"reply": "少し考えよう。"})

    def test_lenient_does_not_repair_bad_shape_or_relevant_values(self):
        invalid = ["bad", "[]", '{"kind":"dialogue"}', json.dumps({**plan(), "extra": ""}),
                   json.dumps(plan(advance="false")), json.dumps(plan(kind="unknown")),
                   json.dumps(plan(kind="existing")), json.dumps(plan(kind="interact", operation="unknown"))]
        for raw in invalid:
            with self.subTest(raw=raw):
                cleaned, _ = clean_lenient(raw)
                with self.assertRaises(free_actions.InvalidPlan):
                    free_actions.parse_plan(cleaned)

    def test_lenient_reuses_default_key_and_never_calls_on_miss(self):
        original = deepcopy(free_actions.PLAN_SCHEMA)
        default_messages, default_config = VARIANTS["default"].prepare(self.session, self.case["input"], self.config)
        messages, config = VARIANTS["lenient"].prepare(self.session, self.case["input"], self.config)
        self.assertEqual(default_messages, messages)
        self.assertEqual(default_config["response_format"], config["response_format"])
        self.assertEqual(cache_key("gemini", "fake", "default", messages, config),
                         cache_key("gemini", "fake", "lenient", messages, config))
        with patch.object(llm_client, "chat_completion", side_effect=AssertionError("network")):
            self.assertEqual(self.evaluate("lenient", live=True)["skip_reason"], "default_cache_required")
            self.assertEqual(self.evaluate("lenient", live=True, no_cache=True)["status"], "skipped")
        raw = json.dumps(plan(kind="dialogue", operation="observe"))
        with patch.object(llm_client, "chat_completion", return_value=raw):
            strict = self.evaluate("default", live=True)
        self.assertEqual(strict["status"], "invalid_plan")
        before = list((self.directory / "cache").iterdir())
        with patch.object(llm_client, "chat_completion", side_effect=AssertionError("network")):
            tolerant = self.evaluate("lenient", live=True)
        self.assertEqual(tolerant["status"], "ok")
        self.assertEqual(tolerant["raw_response"], raw)
        self.assertEqual(tolerant["cache_key"], strict["cache_key"])
        self.assertEqual(tolerant["latency_ms"], strict["latency_ms"])
        self.assertEqual(list((self.directory / "cache").iterdir()), before)
        summary = summarize([tolerant])
        # existing+operation is now normalized by the strict parser, so this fixture uses a dialogue with an operation.
        self.assertEqual(summary["lenient"]["existing_operation_count"], 0)
        self.assertEqual(summary["conflict_rate"], 1)
        self.assertIsNone(summarize([strict])["conflict_rate"])
        self.assertEqual(free_actions.PLAN_SCHEMA, original)

    def test_union_snapshot_enums_constants_and_description_preservation(self):
        original = deepcopy(free_actions.PLAN_SCHEMA)
        messages, default = VARIANTS["default"].prepare(self.session, self.case["input"], self.config)
        context = json.loads(messages[1]["content"])
        for variant in ("union_schema", "union_schema_noenum"):
            same_messages, config = VARIANTS[variant].prepare(self.session, self.case["input"], self.config)
            self.assertEqual(same_messages, messages)
            schema = config["response_format"]["json_schema"]["schema"]
            self.assertNotEqual(cache_key("gemini", "fake", variant, messages, config),
                                cache_key("gemini", "fake", "default", messages, default))
            self.assertEqual(len(schema["anyOf"]), 5)
            for branch in schema["anyOf"]:
                props = branch["properties"]
                self.assertEqual(branch["required"], original["required"])
                self.assertIs(branch["additionalProperties"], False)
                for field in props:
                    self.assertEqual(props[field].get("description"), original["properties"][field].get("description"))
                kind = props["kind"]["const"]
                if kind != "existing":
                    self.assertEqual(props["action_id"]["const"], "")
                elif variant == "union_schema":
                    self.assertEqual(props["action_id"]["enum"], [a["id"] for a in context["actions"] if a["enabled"]])
                else:
                    self.assertNotIn("enum", props["action_id"])
                if kind not in {"existing", "interact"}:
                    self.assertEqual(props["operation"]["const"], "")
                    self.assertIs(props["advance"]["const"], False)
        self.assertEqual(free_actions.PLAN_SCHEMA, original)
        empty = {"actions": [], "obstacles": [], "objects": [], "inventory": []}
        self.assertEqual(len(union_schema(original, empty, True)["anyOf"]), 3)
        empty.update(actions=[{"id": "go_inn", "enabled": True}, {"id": "locked", "enabled": False}],
                     inventory=[{"id": "薬草"}])
        branches = union_schema(original, empty, True)["anyOf"]
        self.assertEqual(branches[0]["properties"]["action_id"]["enum"], ["go_inn"])
        self.assertEqual(branches[1]["properties"]["operation"]["enum"], ["use_item"])
        self.assertEqual(len(union_schema(original, empty, False)["anyOf"]), 5)

    def test_mocked_provider_union_payloads_and_error_evidence(self):
        messages, config = VARIANTS["union_schema"].prepare(self.session, self.case["input"], self.config)
        schema = config["response_format"]["json_schema"]["schema"]
        success = response(200, {"candidates": [{"content": {"parts": [{"text": json.dumps(plan())}]}}]})
        with patch.object(llm_client.requests, "post", return_value=success) as post:
            llm_client.chat_completion(config, messages)
        self.assertEqual(post.call_args.kwargs["json"]["generationConfig"]["responseJsonSchema"], schema)
        config = evaluation_config({"backends": {"ollama": {"base_url": "http://fixture/v1"}}}, "ollama", "fake")
        messages, config = VARIANTS["union_schema"].prepare(self.session, self.case["input"], config)
        rejected = response(400, {"error": "unsupported response_format json_schema"})
        success = response(200, {"message": {"content": json.dumps(plan())}})
        with patch.object(llm_client.requests, "post", side_effect=[rejected, success]) as post:
            usage = {}
            llm_client.chat_completion(config, messages, usage)
        self.assertEqual(post.call_args_list[0].kwargs["json"]["response_format"]["json_schema"]["schema"], schema)
        self.assertEqual(post.call_args_list[1].kwargs["json"]["format"], schema)
        self.assertEqual(usage["transport"], "ollama_native_format")
        with patch.object(llm_client.requests, "post", return_value=response(400, {"error": "anyOf unsupported"})):
            record = self.evaluate("union_schema", live=True)
        self.assertEqual(record["status"], "request_error")
        self.assertIn("anyOf unsupported", record["http_errors"][0]["body"])

    def test_union_schemas_for_all_dev_snapshots(self):
        cases = [json.loads(line) for line in (ROOT / "eval/benchmark/intent_v2.jsonl").read_text(encoding="utf-8").splitlines()]
        for name in sorted({c["snapshot"] for c in cases if c["split"] == "dev"}):
            session = load_snapshot(name)
            before = deepcopy(session)
            for variant in ("union_schema", "union_schema_noenum"):
                with self.subTest(snapshot=name, variant=variant):
                    messages, config = VARIANTS[variant].prepare(session, "少し考えよう。", self.config)
                    self.assertEqual(messages, free_actions.build_plan_messages(session, "少し考えよう。"))
                    branches = config["response_format"]["json_schema"]["schema"]["anyOf"]
                    for branch in branches:
                        for value in branch["properties"].values():
                            if "enum" in value:
                                self.assertTrue(value["enum"])
            self.assertEqual(session, before)

    def test_cli_quota_stops_requests_saves_results_and_replays_later_cache(self):
        cases = self.directory / "cases.jsonl"
        rows = [{**self.case, "id": f"case-{i}", "input": "少し考えよう。" + "。" * i} for i in range(4)]
        cases.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
        eval_dir = self.directory / "eval"
        eval_dir.mkdir()
        (eval_dir / "prices.json").write_text('{"models":{}}', encoding="utf-8")
        messages, config = VARIANTS["default"].prepare(self.session, rows[3]["input"], self.config)
        key = cache_key("gemini", "fake", "default", messages, config)
        write_cache(eval_dir / "cache", key, {"raw_response": json.dumps(plan()), "usage": {}, "latency_ms": 1})
        success = response(200, {"candidates": [{"content": {"parts": [{"text": json.dumps(plan())}]}}]})
        quota = response(429, {"error": {"quotaId": "PerDay", "retryDelay": "46800s"}})
        args = ["--suite", "intent", "--cases", str(cases), "--backend", "gemini", "--model", "fake", "--rpm", "0", "--live"]
        with patch.object(run, "ROOT", self.directory), patch.object(state, "load_config", return_value=self.config), \
             patch.object(run, "load_snapshot", return_value=self.session), \
             patch.object(llm_client.requests, "post", side_effect=[success, quota]) as post, \
             patch("scripts.eval.requests.time.sleep", side_effect=AssertionError("sleep")):
            self.assertEqual(run.main(args), 1)
        self.assertEqual(post.call_count, 2)
        report = json.loads(next((eval_dir / "reports").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(report["quota_exhausted"]["case_index"], 2)
        self.assertEqual(report["quota_exhausted"]["retry_after_seconds"], 46800)
        self.assertEqual(report["metrics"]["statuses"], {"ok": 2, "quota_exhausted": 1, "skipped": 1})
        self.assertIn("46800", run.report_markdown(report))
        self.assertIn("第 2 条", run.report_markdown(report))
        compared = compare([report, {**report, "variant": "lenient"}])
        for label in ("S0+S1", "S3", "InvalidPlan", "conflict", "default", "lenient", "USD"):
            self.assertIn(label, compared)


if __name__ == "__main__":
    unittest.main()
