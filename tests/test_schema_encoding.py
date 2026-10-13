from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import requests

from host import free_actions, llm_client, state
from scripts.eval import run, schema_smoke
from scripts.eval.cache import cache_key, write_cache
from scripts.eval.requests import evaluation_config
from scripts.eval.snapshots import ROOT, load_snapshot
from scripts.eval.variants import SCHEMA_ENCODINGS, VARIANTS, encoded_schema, union_schema


class SchemaEncodingTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".tmp-test").mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / ".tmp-test")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.session = load_snapshot("forest_entrance_hero")
        self.config = evaluation_config({"backends": {"gemini": {"api_key": "fake", "base_url": "http://fixture"}}},
                                        "gemini", "fake", rpm=0)
        self.plan = dict(kind="dialogue", action_id="", operation="", target_id="", item_id="",
                         advance=False, approach="", reply="少し考えよう。")
        self.case = dict(id="fixture", snapshot="forest_entrance_hero", input="少し考えよう。",
                         gold=[self.plan], tags=[], split="dev")

    def evaluate(self, variant, **kwargs):
        return run.evaluate_case(self.case, self.session, self.config, "gemini", "fake", variant,
                                 self.directory / "cache", **kwargs)

    def test_guard_suffixes_match_spec_verbatim_and_only_append(self):
        spec = (ROOT / "docs/specs/008-union-encoding-and-guard-prompt.md").read_text(encoding="utf-8")
        original_schema = deepcopy(free_actions.PLAN_SCHEMA)
        baseline, baseline_config = VARIANTS["default"].prepare(self.session, self.case["input"], self.config)
        for name in ("guard_rules", "guard_rules_short"):
            with self.subTest(variant=name):
                quoted = spec.split(f"`{name}`：\n```\n", 1)[1].split("\n```", 1)[0]
                messages, config = VARIANTS[name].prepare(self.session, self.case["input"], self.config)
                self.assertEqual(messages[0]["content"], free_actions.PLAN_PROMPT_BASE + "\n" + quoted)
                self.assertEqual(messages[1:], baseline[1:])
                self.assertEqual(config, baseline_config)
                self.assertEqual(VARIANTS[name].unwrap(json.dumps(self.plan)), json.dumps(self.plan))
        self.assertEqual(free_actions.PLAN_SCHEMA, original_schema)
        self.assertEqual(baseline[0]["content"], free_actions.PLAN_PROMPT)
        guarded, _ = VARIANTS["guard_rules"].prepare(self.session, self.case["input"], self.config)
        pre_guard, _ = VARIANTS["pre_guard"].prepare(self.session, self.case["input"], self.config)
        self.assertEqual(guarded[0]["content"], free_actions.PLAN_PROMPT_PRE_SEQUENCE)
        self.assertEqual(pre_guard[0]["content"], free_actions.PLAN_PROMPT_BASE)
        sequenced, _ = VARIANTS["guard_sequence_item"].prepare(self.session, self.case["input"], self.config)
        self.assertEqual(sequenced[0]["content"], free_actions.PLAN_PROMPT_PRE_OFFTOPIC)
        pre_offtopic, _ = VARIANTS["pre_offtopic"].prepare(self.session, self.case["input"], self.config)
        self.assertEqual(pre_offtopic[0]["content"], free_actions.PLAN_PROMPT_PRE_OFFTOPIC)
        self.assertEqual(free_actions.PLAN_PROMPT, free_actions.PLAN_PROMPT_PRE_OFFTOPIC + "\n" + free_actions.PLAN_OFFTOPIC_RULE)

    def test_all_encodings_on_all_dev_snapshots_preserve_defaults_and_descriptions(self):
        cases = [json.loads(line) for line in (ROOT / "eval/benchmark/intent_v2.jsonl").read_text(encoding="utf-8").splitlines()]
        original = deepcopy(free_actions.PLAN_SCHEMA)
        for name in sorted({c["snapshot"] for c in cases if c["split"] == "dev"}):
            session = load_snapshot(name)
            before = deepcopy(session)
            baseline, _ = VARIANTS["default"].prepare(session, self.case["input"], self.config)
            context = json.loads(baseline[1]["content"])
            union = union_schema(original, context, True)
            for variant in SCHEMA_ENCODINGS:
                with self.subTest(snapshot=name, variant=variant):
                    messages, config = VARIANTS[variant].prepare(session, self.case["input"], self.config)
                    self.assertEqual(messages, baseline)
                    schema = config["response_format"]["json_schema"]["schema"]
                    if variant == "union_wrapped":
                        self.assertEqual(schema, dict(type="object", properties={"plan": union},
                                                      required=["plan"], additionalProperties=False))
                        branches = schema["properties"]["plan"]["anyOf"]
                    elif variant == "flat_enum":
                        self.assertNotIn("anyOf", schema)
                        branches = [schema]
                        for field in ("action_id", "operation", "target_id", "item_id"):
                            self.assertIn("", schema["properties"][field]["enum"])
                    else:
                        self.assertNotIn('"const"', json.dumps(schema))
                        branches = schema["anyOf"]
                        for old, branch in zip(union["anyOf"], branches):
                            for field, definition in old["properties"].items():
                                if "const" in definition:
                                    self.assertEqual(branch["properties"][field]["enum"], [definition["const"]])
                            if variant == "union_ordered":
                                self.assertEqual(branch["propertyOrdering"], original["required"])
                            else:
                                self.assertNotIn("propertyOrdering", branch)
                    for branch in branches:
                        self.assertEqual(branch["required"], original["required"])
                        for field, definition in original["properties"].items():
                            self.assertEqual(branch["properties"][field].get("description"), definition.get("description"))
            self.assertEqual(session, before)
        self.assertEqual(free_actions.PLAN_SCHEMA, original)

    def test_flat_enums_use_snapshot_ids_and_empty_snapshots_are_valid(self):
        context = dict(actions=[dict(id="enabled", enabled=True), dict(id="disabled", enabled=False)],
                       obstacles=[dict(id="obstacle")], objects=[dict(id="material")],
                       npcs=[dict(id="npc")], inventory=[dict(id="item")])
        schema = encoded_schema(free_actions.PLAN_SCHEMA, context, "flat_enum")
        expected = dict(action_id=["", "enabled"], operation=list(free_actions.OPERATIONS),
                        target_id=["", "self", "obstacle", "material", "npc"], item_id=["", "material", "item"])
        for field, enum in expected.items():
            self.assertEqual(schema["properties"][field]["enum"], enum)
        for field in set(free_actions.PLAN_SCHEMA["properties"]) - set(expected):
            self.assertEqual(schema["properties"][field], free_actions.PLAN_SCHEMA["properties"][field])
        empty = {key: [] for key in context}
        for variant in SCHEMA_ENCODINGS:
            schema = encoded_schema(free_actions.PLAN_SCHEMA, empty, variant)
            self.assertNotIn('"enum": []', json.dumps(schema))
        self.assertEqual(encoded_schema(free_actions.PLAN_SCHEMA, empty, "flat_enum")["properties"]["operation"]["enum"], [""])

    def test_wrapped_strict_parse_and_raw_cache_replay(self):
        raw = json.dumps({"plan": self.plan}, ensure_ascii=False)
        with patch.object(llm_client, "chat_completion", return_value=raw) as call:
            record = self.evaluate("union_wrapped", live=True)
            self.assertEqual(record["status"], "ok")
            self.assertEqual(record["plan"], self.plan)
            self.assertEqual(record["raw_response"], raw)
            self.assertIn("plan", call.call_args.args[0]["response_format"]["json_schema"]["schema"]["properties"])
        with patch.object(llm_client, "chat_completion", side_effect=AssertionError("network")):
            replay = self.evaluate("union_wrapped")
            self.assertTrue(replay["cache_hit"])
            self.assertEqual(replay["plan"], record["plan"])
        for malformed in ("{", "{}", "[]", '{"plan":null}', json.dumps(self.plan),
                          json.dumps({"plan": self.plan, "extra": True}),
                          json.dumps({"plan": {**self.plan, "operation": "sneak"}})):
            with self.subTest(raw=malformed), patch.object(llm_client, "chat_completion", return_value=malformed):
                self.assertIn(self.evaluate("union_wrapped", live=True, no_cache=True)["status"], {"invalid_plan", "json_error"})

    def test_guard_still_uses_strict_parser_and_measures_matched_token_delta(self):
        messages, config = VARIANTS["default"].prepare(self.session, self.case["input"], self.config)
        write_cache(self.directory / "cache", cache_key("gemini", "fake", "default", messages, config),
                    {"raw_response": json.dumps(self.plan), "usage": {"input_tokens": 100}})

        def completion(config, messages, usage_out):
            usage_out.update(input_tokens=120)
            return json.dumps({**self.plan, "operation": "sneak"})

        for name in ("guard_rules", "guard_rules_short"):
            with patch.object(llm_client, "chat_completion", side_effect=completion):
                record = self.evaluate(name, live=True)
            self.assertEqual(record["status"], "invalid_plan")
            self.assertEqual(record["prompt_delta"], dict(chars=len(VARIANTS[name].prompt_suffix), input_tokens=20))

    def test_failure_shapes_and_gemini_only(self):
        rows = [dict(status="json_error", raw_response=raw) for raw in (" \n", "{  \n", '{ "plan": {\n',
                                                                       "{ }", '{"plan": { }}', '[]', '{"kind":')]
        rows += [dict(status="skipped", raw_response=None), dict(status="ok", raw_response=json.dumps(self.plan))]
        self.assertEqual(run.response_failures(rows, "union_wrapped"),
                         dict(whitespace=3, empty_object=2, other=2, no_response=1))
        for variant in SCHEMA_ENCODINGS:
            with self.assertRaises(ValueError):
                run.evaluate_case(self.case, self.session, self.config, "ollama", "fake", variant, self.directory)

    def test_gemini_transmits_each_schema_encoding_unchanged(self):
        for name in SCHEMA_ENCODINGS:
            with self.subTest(variant=name):
                messages, config = VARIANTS[name].prepare(self.session, self.case["input"], self.config)
                response = requests.Response()
                response.status_code = 200
                raw = json.dumps({"plan": self.plan} if name == "union_wrapped" else self.plan)
                response._content = json.dumps({"candidates": [{"content": {"parts": [{"text": raw}]}}]}).encode("utf-8")
                with patch.object(llm_client.requests, "post", return_value=response) as post:
                    self.assertEqual(llm_client.chat_completion(config, messages), raw)
                self.assertEqual(post.call_args.kwargs["json"]["generationConfig"]["responseJsonSchema"],
                                 config["response_format"]["json_schema"]["schema"])

    def test_smoke_is_offline_by_default_and_saves_all_four_reports(self):
        (self.directory / "eval").mkdir()
        (self.directory / "eval/prices.json").write_text('{"models":{}}', encoding="utf-8")
        with patch.object(run, "ROOT", self.directory), patch.object(schema_smoke, "ROOT", self.directory), \
             patch.object(state, "load_config", return_value=self.config), \
             patch.object(llm_client, "chat_completion", side_effect=AssertionError("network")), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(schema_smoke.main(["--cases", str(ROOT / "eval/benchmark/intent_v2.jsonl"), "--full-dev"]), 1)
        self.assertEqual(output.getvalue().count("不可用"), 4)
        reports = list((self.directory / "eval/reports").glob("*.json"))
        self.assertEqual(len(reports), 5)
        for path in (self.directory / "eval/runs").glob("*/cases.jsonl"):
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 20)
            self.assertTrue(all(row["status"] == "skipped" for row in rows))

    def test_smoke_full_dev_gate_shared_policy_and_quota_stop(self):
        calls = []

        def evaluate(args, config):
            calls.append((deepcopy(args), config["_request_policy"]))
            success = args.variant in {"union_enum1", "flat_enum"}
            quota = args.variant == "union_ordered"
            return dict(run_id=f"fixture-{len(calls)}", quota_exhausted={"retry_after_seconds": 999} if quota else None,
                        metrics=dict(total=args.limit or 194, evaluated=args.limit or 194,
                                     statuses={"ok": 20} if success else {"invalid_plan": 20}),
                        response_failures=dict(whitespace=0, empty_object=0 if success else 20, other=0, no_response=0))

        with patch.object(schema_smoke, "ROOT", self.directory), patch.object(state, "load_config", return_value=self.config), \
             patch.object(schema_smoke, "run_evaluation", side_effect=evaluate), redirect_stdout(io.StringIO()):
            self.assertEqual(schema_smoke.main(["--cases", str(ROOT / "eval/benchmark/intent_v2.jsonl"), "--live", "--full-dev"]), 1)
        self.assertEqual([args.variant for args, _ in calls], [*SCHEMA_ENCODINGS, "union_enum1", "flat_enum"])
        self.assertEqual([args.live for args, _ in calls], [True, True, True, False, False, False])
        self.assertEqual([args.limit for args, _ in calls], [20, 20, 20, 20, None, None])
        self.assertTrue(all(policy is calls[0][1] for _, policy in calls))


if __name__ == "__main__":
    unittest.main()
