from __future__ import annotations

import json
import shutil
import unittest
import uuid
from collections import Counter
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from host import app, free_actions, llm_client, llm_trace, state
from scripts.eval.cache import cache_key
from scripts.eval.compare import compare
from scripts.eval.generate_candidates import generate, recipes
from scripts.eval.metrics import matches, summarize
from scripts.eval.run import engine_result, evaluate_case, report_markdown
from scripts.eval import run as run_module
from scripts.eval.snapshots import ROOT, build_snapshot, isolated_engine
from scripts.eval.variants import VARIANTS, Variant
from scripts.evaluate_free_actions import CASES


def valid_plan(**updates):
    value = {"kind": "dialogue", "action_id": "", "operation": "", "target_id": "", "item_id": "",
             "advance": False, "approach": "", "reply": "少し考えよう。"}
    value.update(updates)
    return value


class InfrastructureTests(unittest.TestCase):
    def setUp(self):
        self.directory = ROOT / ".tmp-test" / f"infra-{uuid.uuid4().hex}"
        self.directory.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        self.session = build_snapshot(recipes()[0])
        self.config = {"active_backend": "gemini", "backends": {"gemini": {"model": "fake", "api_key": "fake"}}, "debug_llm": False}
        self.case = {"id": "fixture", "snapshot": "forest_entrance_hero", "input": "少し考えよう。", "tags": ["dialogue"],
                     "gold": [{k: v for k, v in valid_plan().items() if k not in {"reply", "approach"}}],
                     "accept_kinds": ["dialogue"], "label_status": "proposed", "split": "dev"}

    def evaluate(self, **kwargs):
        return evaluate_case(self.case, self.session, self.config, "gemini", "fake", "default", self.directory, **kwargs)

    def test_all_snapshots_are_identical_across_builds_and_restore_globals(self):
        save_dir = state.SAVE_DIR
        for recipe in recipes():
            with self.subTest(recipe=recipe["id"]):
                first = build_snapshot(recipe)
                self.assertEqual(first, build_snapshot(recipe))
                self.assertEqual(first["world_state"]["location_id"], recipe["location_id"])
        self.assertEqual(save_dir, state.SAVE_DIR)

    def test_snapshot_cleanup_even_on_invalid_location(self):
        root = ROOT / ".tmp-test"
        before = set(root.iterdir())
        with self.assertRaises(ValueError):
            build_snapshot({**recipes()[0], "location_id": "nonexistent"})
        self.assertEqual(before, set(root.iterdir()))

    def test_inventory_and_low_hp_fixtures(self):
        missing = build_snapshot(recipes()[8])
        self.assertFalse(any(i.get("id") == "trail_ration" or i["name"] == "薬草" for i in missing["character"]["inventory"]))
        low = build_snapshot(recipes()[6])
        self.assertLess(low["character"]["hp"], low["character"]["max_hp"])
        self.assertFalse(any(i["name"] == "氷の護符" for i in build_snapshot(recipes()[7])["character"]["inventory"]))

    def test_key_covers_every_output_input_but_not_credentials(self):
        config = {"temperature": .2, "max_tokens": 700, "response_format": {"type": "json_object"}}
        messages = [{"role": "user", "content": "観察"}]
        key = cache_key("gemini", "fake", "default", messages, config)
        self.assertEqual(key, cache_key("gemini", "fake", "default", messages, {**config, "api_key": "secret"}))
        self.assertEqual(key, cache_key("gemini", "fake", "default", messages, dict(reversed(list(config.items())))))
        for field, value in (("temperature", 1), ("max_tokens", 800), ("response_format", {})):
            self.assertNotEqual(key, cache_key("gemini", "fake", "default", messages, {**config, field: value}))
        for args in [("ollama", "fake", "default", messages), ("gemini", "other", "default", messages),
                     ("gemini", "fake", "other", messages), ("gemini", "fake", "default", messages + messages)]:
            self.assertNotEqual(key, cache_key(*args, config))

    def test_offline_miss_and_no_cache_never_request(self):
        with patch.object(llm_client, "chat_completion", side_effect=AssertionError("network")):
            self.assertEqual(self.evaluate()["status"], "skipped")
            self.assertEqual(self.evaluate(no_cache=True)["status"], "skipped")
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_cache_replay_rescores_labels_without_model_calls(self):
        raw = json.dumps(valid_plan())
        def completion(config, messages, usage_out=None):
            usage_out.update(input_tokens=100, output_tokens=10, cached_tokens=30)
            return raw
        with patch.object(llm_client, "chat_completion", side_effect=completion) as call:
            live = self.evaluate(live=True)
            self.assertEqual(call.call_count, 1)
        self.case["gold"][0]["kind"] = "clarify"
        with patch.object(llm_client, "chat_completion", side_effect=AssertionError("network")):
            replay = self.evaluate()
        self.assertTrue(replay["cache_hit"])
        self.assertEqual(replay["raw_response"], raw)
        self.assertEqual(live["latency_ms"], replay["latency_ms"])
        self.assertEqual(summarize([replay])["exact"], 0)

    def test_no_cache_live_does_not_write(self):
        with patch.object(llm_client, "chat_completion", return_value=json.dumps(valid_plan())):
            self.assertEqual(self.evaluate(live=True, no_cache=True)["status"], "ok")
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_thinking_removed_before_shared_parser(self):
        raw = "<think>internal</think>" + json.dumps(valid_plan())
        with patch.object(llm_client, "chat_completion", return_value=raw):
            result = self.evaluate(live=True)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["thinking_stripped"])
        self.assertEqual(result["raw_response"], raw)

    def test_invalid_json_and_invalid_plan_are_distinct(self):
        for raw, expected in [("bad", "json_error"), ('{"kind":"interact"}', "invalid_plan")]:
            with patch.object(llm_client, "chat_completion", return_value=raw):
                result = self.evaluate(live=True, no_cache=True)
            self.assertEqual(result["status"], expected)
            self.assertEqual(result["engine"]["outcome"], "rejected")

    def test_existing_attack_and_movement_use_game_engine_without_api(self):
        attack = engine_result(self.session, valid_plan(kind="existing", action_id="attack_slime"), "スライムと戦う")
        self.assertTrue(attack["attack_or_combat"])
        castle = build_snapshot(recipes()[4])
        movement = engine_result(castle, valid_plan(kind="existing", action_id="go_castle_town"), "城下町へ出る")
        self.assertTrue(movement["changes"]["position"])
        self.assertEqual(castle["world_state"]["location_id"], "castle")

    def test_interaction_resource_changes_and_fixed_dice_are_reproducible(self):
        plan = valid_plan(kind="interact", operation="distract", target_id="forest_slime", item_id="trail_ration", advance=True)
        result = engine_result(self.session, plan, "携帯食で誘って通る")
        self.assertTrue(result["changes"]["items"])
        self.assertTrue(result["changes"]["position"])
        self.assertEqual(result, engine_result(self.session, plan, "携帯食で誘って通る"))
        plan.update(operation="sneak", item_id="")
        self.assertEqual(engine_result(self.session, plan, "静かに通る"), engine_result(self.session, plan, "静かに通る"))

    def test_variant_hooks_leave_default_prompt_and_schema_unchanged(self):
        original = deepcopy(free_actions.PLAN_SCHEMA)
        variant = Variant(system_prompt="variant", few_shot=({"role": "assistant", "content": "example"},),
                          schema_transform=lambda schema: {**schema, "description": "variant"})
        messages, config = variant.prepare(self.session, "入力", self.config)
        self.assertEqual(messages[0]["content"], "variant")
        self.assertEqual(messages[-2]["content"], "example")
        self.assertEqual(free_actions.PLAN_SCHEMA, original)
        default, _ = VARIANTS["default"].prepare(self.session, "入力", self.config)
        self.assertEqual(default, free_actions.build_plan_messages(self.session, "入力"))

    def test_metrics_multi_gold_type_safety_rates_and_missing_data(self):
        row = {**deepcopy(self.case), "status": "ok", "plan": valid_plan(), "tags": ["negation", "injection", "declared_success"],
               "engine": {"changes": {"items": False}, "attack_or_combat": False}, "latency_ms": 10,
               "usage": {"input_tokens": 100, "output_tokens": 20, "cached_tokens": 40,
                         "usageMetadata": {"cachedContentTokenCount": 40}}}
        other = deepcopy(row)
        other.update(plan=valid_plan(kind="clarify"), latency_ms=30)
        other["gold"] = [{**row["gold"][0], "kind": "unsupported"}, {**row["gold"][0], "kind": "clarify"}]
        other["engine"] = {"changes": {"items": True}, "attack_or_combat": True}
        broken = deepcopy(row)
        broken.update(status="json_error", plan=None, latency_ms=20)
        result = summarize([row, other, broken, {**self.case, "status": "skipped"}],
                           {"input_per_million": 1, "output_per_million": 2, "cached_input_per_million": .5})
        self.assertAlmostEqual(result["exact"], 2 / 3)
        self.assertAlmostEqual(result["injection"]["no_state_change"], 2 / 3)
        self.assertAlmostEqual(result["negation"]["preserved"], 2 / 3)
        self.assertEqual(result["latency_ms"], {"p50": 20, "p95": 29})
        self.assertEqual(result["clarify"], {"precision": 1, "recall": 1})
        self.assertAlmostEqual(result["cost_per_turn"], .00012)
        self.assertEqual(result["gemini_cache"]["token_hit_rate"], .4)
        self.assertIsNone(summarize([{**self.case, "status": "skipped"}])["exact"])
        row["plan"]["advance"] = 0
        self.assertFalse(matches(row)["exact"])

    def test_relaxed_kind_not_exact_and_report_no_data(self):
        row = {**self.case, "status": "ok", "plan": valid_plan(kind="clarify"), "accept_kinds": ["clarify"]}
        score = matches(row)
        self.assertFalse(score["exact"])
        self.assertFalse(score["kind"])
        self.assertTrue(score["kind_relaxed"])
        report = {"run_id": "fixture", "metrics": summarize([]), "errors": []}
        self.assertIn("n/a", report_markdown(report))
        self.assertIn("n/a", compare([report]))

    def test_candidate_distribution_legacy_and_regeneration(self):
        rows = generate()
        saved = [json.loads(line) for line in (ROOT / "eval/candidates/intent_v1.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows, saved)
        self.assertTrue(400 <= len(rows) <= 600)
        self.assertEqual(len({r["id"] for r in rows}), len(rows))
        counts = Counter(tag for r in rows for tag in r["tags"])
        self.assertEqual(len(counts), 20)
        self.assertTrue(all(count >= 20 for tag, count in counts.items() if tag != "legacy"))
        self.assertAlmostEqual(counts["language_mix"] / len(rows), .1)
        self.assertTrue(all(r["label_status"] == "proposed" for r in rows))
        for name, text, destination, combat, operation in CASES:
            row = next(r for r in rows if r["id"] == "legacy-" + name)
            self.assertEqual(row["input"], text)
            self.assertEqual(row["legacy_expectation"], dict(case=name, location=destination, in_combat=combat, operation=operation))

    def test_gold_entity_ids_exist_in_prompt_surfaces(self):
        contexts = {r["id"]: json.loads(free_actions.build_plan_messages(build_snapshot(r), "")[1]["content"]) for r in recipes()}
        for row in generate():
            context = contexts[row["snapshot"]]
            ids = {item["id"] for key in ("obstacles", "objects", "npcs", "inventory") for item in context[key]}
            actions = {a["id"] for a in context["actions"]}
            for answer in row["gold"]:
                with self.subTest(case=row["id"]):
                    if answer["target_id"]:
                        self.assertIn(answer["target_id"], ids | {"self"})
                    if answer["item_id"]:
                        self.assertIn(answer["item_id"], ids)
                    if answer["action_id"]:
                        self.assertIn(answer["action_id"], actions)

    def test_cli_offline_and_live_connection_circuit_breaker(self):
        cases = self.directory / "cases.jsonl"
        cases.write_text("\n".join(json.dumps({**self.case, "id": f"case-{i}"}) for i in range(3)), encoding="utf-8")
        price_dir = self.directory / "eval"
        price_dir.mkdir()
        (price_dir / "prices.json").write_text('{"models":{}}', encoding="utf-8")
        config = {**self.config, "archived_backends": ["ollama"], "backends": {"ollama": {"model": "old", "base_url": "http://fixture/v1"}}}
        args = ["--suite", "intent", "--cases", str(cases), "--backend", "ollama", "--model", "chosen", "--variant", "default"]
        with patch.object(run_module, "ROOT", self.directory), patch.object(state, "load_config", return_value=config), \
             patch.object(run_module, "load_snapshot", return_value=self.session), patch.object(llm_client, "chat_completion") as completion:
            self.assertEqual(run_module.main(args), 0)
            completion.assert_not_called()
            completion.side_effect = llm_client.LLMClientError("connection refused")
            self.assertEqual(run_module.main(args + ["--live"]), 1)
            completion.assert_called_once()
            called_config = completion.call_args.args[0]
            self.assertEqual(called_config["active_backend"], "ollama")
            self.assertEqual(called_config["backends"]["ollama"]["model"], "chosen")
        reports = [json.loads(p.read_text(encoding="utf-8")) for p in (price_dir / "reports").glob("*.json")]
        live = next(r for r in reports if r["live"])
        self.assertEqual(live["metrics"]["statuses"], {"request_error": 1, "skipped": 2})
        self.assertIsNone(live["metrics"]["exact"])
        self.assertEqual(len(live["cases_sha256"]), 64)

    def test_trace_appends_utf8_json_and_ignores_open_failure(self):
        record = {"session_id": "fixture", "plan": valid_plan()}
        with patch.object(llm_trace, "TRACE_DIR", self.directory):
            llm_trace.append_trace(record)
            llm_trace.append_trace(record)
            lines = next(self.directory.glob("*.jsonl")).read_text(encoding="utf-8").splitlines()
            self.assertEqual([json.loads(line) for line in lines], [record, record])
            with patch.object(Path, "open", side_effect=OSError("disk full")):
                llm_trace.append_trace(record)

    def test_gemini_blocks_and_max_tokens(self):
        for reason in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION"):
            for body in ({"promptFeedback": {"blockReason": reason}}, {"candidates": [{"finishReason": reason}]}):
                with self.assertRaises(llm_client.LLMBlockedError) as caught:
                    llm_client._content_from_gemini_response(json.dumps(body))
                self.assertEqual(caught.exception.reason, reason)
                self.assertIsInstance(caught.exception, llm_client.LLMClientError)
        with patch.object(llm_client, "debug_log") as log:
            self.assertEqual(llm_client._content_from_gemini_response(json.dumps({"candidates": [
                {"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "partial"}]}}]})), "partial")
        log.assert_called_once()

    def test_provider_usage_is_optional_and_preserves_cached_counter(self):
        body = {"usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20, "cachedContentTokenCount": 40},
                "candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        response = Mock(status_code=200, headers={}, text=json.dumps(body))
        with patch.object(llm_client.requests, "post", return_value=response):
            usage = {}
            self.assertEqual(llm_client.chat_completion(self.config, [], usage), "ok")
            self.assertEqual(llm_client.chat_completion(self.config, []), "ok")
        self.assertEqual(usage["cached_tokens"], 40)
        self.assertEqual(usage["usageMetadata"], body["usageMetadata"])
        usage = {}
        llm_client._collect_usage({"prompt_eval_count": 11, "eval_count": 3}, usage, "qwen")
        self.assertEqual((usage["input_tokens"], usage["output_tokens"]), (11, 3))

    def test_ollama_schema_rejection_uses_native_format_only_in_eval(self):
        config = {**self.config, "active_backend": "ollama", "eval_ollama_schema_fallback": True,
                  "backends": {"ollama": {"base_url": "http://localhost:11434/v1", "model": "qwen"}}}
        config = free_actions.planner_config(config)
        first = Mock(status_code=400, text="unsupported response_format json_schema", headers={})
        second = Mock(status_code=200)
        second.json.return_value = {"message": {"content": "{}"}, "prompt_eval_count": 10, "eval_count": 2}
        with patch.object(llm_client.requests, "post", side_effect=[first, second]) as post:
            usage = {}
            self.assertEqual(llm_client.chat_completion(config, [], usage), "{}")
        self.assertEqual(post.call_args.args[0], "http://localhost:11434/api/chat")
        self.assertEqual(post.call_args.kwargs["json"]["format"], free_actions.PLAN_SCHEMA)
        self.assertEqual(usage["transport"], "ollama_native_format")

    def test_trace_failure_cannot_break_game_and_disabled_trace_is_empty(self):
        with patch.object(llm_trace, "TRACE_DIR", self.directory / "trace"), patch.object(Path, "mkdir", side_effect=OSError("denied")):
            llm_trace.append_trace({"session_id": "fixture"})
        with isolated_engine(), patch.object(app, "load_config", return_value={**self.config, "trace_llm": False}), \
             patch.object(app, "chat_completion", return_value=json.dumps(valid_plan())), patch.object(llm_trace, "append_trace") as trace:
            app._run_free_turn(self.session, app.TurnRequest(text="考える。"))
        trace.assert_not_called()

    def test_blocked_free_action_uses_existing_visible_fallback_and_trace(self):
        before = deepcopy(self.session["character"])
        with isolated_engine(), patch.object(app, "load_config", return_value=self.config), \
             patch.object(app, "chat_completion", side_effect=llm_client.LLMBlockedError("SAFETY")), \
             patch.object(llm_trace, "append_trace") as trace:
            result = app._run_free_turn(self.session, app.TurnRequest(text="攻撃しない。"))
        self.assertEqual(self.session["character"], before)
        self.assertIn("行動を読み取れませんでした", result["messages"][-1]["text"])
        record = trace.call_args.args[0]
        self.assertTrue(record["fallback"])
        self.assertEqual(record["outcome"], "rejected")
        self.assertEqual(record["call_type"], "plan")
        self.assertNotIn("api_key", json.dumps(record))

    def test_transport_failure_tells_player_it_was_not_their_wording(self):
        before = deepcopy(self.session["character"])
        with isolated_engine(), patch.object(app, "load_config", return_value=self.config), \
             patch.object(app, "chat_completion", side_effect=llm_client.LLMClientError("429 Too Many Requests")), \
             patch.object(llm_trace, "append_trace"):
            result = app._run_free_turn(self.session, app.TurnRequest(text="攻撃しない。"))
        self.assertEqual(self.session["character"], before)
        self.assertIn("GMとの通信に失敗しました", result["messages"][-1]["text"])

    def test_trace_plan_and_outcome_and_request_only_latency(self):
        plan = valid_plan(kind="interact", operation="observe", target_id="forest_slime")
        with isolated_engine(), patch.object(app, "load_config", return_value=self.config), \
             patch.object(app, "chat_completion", return_value=json.dumps(plan)), patch.object(llm_trace, "append_trace") as trace:
            app._run_free_turn(self.session, app.TurnRequest(text="スライムを観察する。"))
        record = trace.call_args.args[0]
        self.assertEqual(record["plan"], plan)
        self.assertEqual(record["parse_status"], "ok")
        self.assertEqual(record["outcome"], "observed")
        self.assertEqual(record["turn"], 1)
        self.assertEqual(len(record["prompt_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
