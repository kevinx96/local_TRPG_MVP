from __future__ import annotations

import json
import unittest
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import free_actions, llm_client, state
from scripts.eval.audit import costly_plan
from scripts.eval.benchmark_v2 import OUTPUT, TAGS, answer, assign_splits, recipes, similarity_violations
from scripts.eval.metrics import engine_caught, severity, summarize
from scripts.eval.run import engine_result, evaluate_case, report_markdown
from scripts.eval.snapshots import build_snapshot, load_snapshot


class SeverityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forest = build_snapshot(recipes()["H"])
        cls.castle = build_snapshot(recipes()["C"])

    def row(self, prediction: str, gold: str = "dialogue", **updates):
        return dict(status="ok", tags=["negation"], plan=answer(prediction),
                    gold=[answer(g) for g in gold.split(",")], **updates)

    def test_s0_s1_s2_and_gold_precedes_harmful(self):
        row = self.row("dialogue", "dialogue,clarify", harmful={"kind": ["dialogue"]})
        self.assertEqual(severity(row), "S0")
        row["plan"] = answer("clarify")
        self.assertEqual(severity(row), "S1")
        row["plan"] = answer("unsupported")
        self.assertEqual(severity(row), "S2")
        row["plan"] = None
        self.assertEqual(severity(row), "S2")

    def test_talk_kinds_ignore_listener_when_gold_target_is_empty(self):
        row = self.row("dialogue", "dialogue")
        row["plan"]["target_id"] = "sarah"
        self.assertEqual(severity(row), "S0")
        row["gold"][0]["target_id"] = "king"
        self.assertNotEqual(severity(row), "S0")

    def test_explicit_gold_tier_overrides_position(self):
        row = self.row("clarify", "dialogue,clarify")
        row["gold"][1]["tier"] = "S0"
        self.assertEqual(severity(row), "S0")

    def test_harmful_alternatives_and_kind_constraint(self):
        for prediction, harmful in [("pass", {"operation": ["distract"]}),
                                    ("e:attack_slime", {"kind": ["existing"], "action_id": ["attack_slime"]}),
                                    ("e:attack_slime", {"action_id": ["attack_slime"]})]:
            self.assertEqual(severity(self.row(prediction, harmful=harmful)), "S3")
        self.assertEqual(severity(self.row("observe", harmful={"operation": ["sneak"]})), "S2")
        self.assertEqual(severity(self.row("e:attack_slime", harmful={"kind": ["existing"], "action_id": ["other"]})), "S2")
        self.assertEqual(severity(self.row("pass", harmful={"kind": ["existing"], "operation": ["distract"]})), "S2")
        self.assertEqual(severity(self.row("e:attack_slime", harmful={"operation": ["distract"], "action_id": ["attack_slime"]})), "S3")

    def test_default_cost_rule_and_explicit_empty_harmful(self):
        row = self.row("pass", snapshot="v2_dark_forest_loc_hero")
        self.assertEqual(severity(row), "S3")
        row["gold"].append(answer("sneak"))
        self.assertEqual(severity(row), "S2")
        row["gold"] = [answer("dialogue")]
        row["harmful"] = {}
        self.assertEqual(severity(row), "S2")

    def test_checks_combat_movement_and_negative_effects_from_action_data(self):
        for action in ("e:attack_slime",):
            self.assertTrue(costly_plan(self.forest, answer(action)))
        for action in ("e:go_inn", "e:ask_general_advice"):
            self.assertTrue(costly_plan(self.castle, answer(action)))
        self.assertFalse(costly_plan(self.castle, answer("e:ask_king_info")))
        for effect in ({"mp_change": -2}, {"sp_change": -1}, {"gold_change": -5},
                       {"remove_item": {"name": "薬草"}}, {"start_combat": True},
                       {"current_location": "inn"}, {"game_over": {"ending": "test"}}):
            with self.subTest(effect=effect), patch.object(state, "resolve_action", return_value={
                    "id": "never_seen_id", "failure_effects": [{"branch": {"then": [effect]}}]}):
                self.assertTrue(costly_plan(self.castle, answer("e:never_seen_id")))
        with patch.object(state, "resolve_action", return_value={"effects": [{"mp_change": 3}]}):
            self.assertFalse(costly_plan(self.castle, answer("e:never_seen_id")))
        with patch.object(state, "resolve_action", return_value={"dice_type": "1d20", "dice_dc": 12}):
            self.assertTrue(costly_plan(self.castle, answer("e:never_seen_id")))
        with patch.object(state, "resolve_action", return_value={"roll": {"dc": 0}}):
            self.assertFalse(costly_plan(self.castle, answer("e:never_seen_id")))
        with patch.object(state, "resolve_action", return_value={"effects": [{"next_location": "inn"}]}):
            self.assertTrue(costly_plan(self.castle, answer("e:never_seen_id")))

    def test_free_costs_follow_engine_and_do_not_mutate_snapshot(self):
        before = deepcopy(self.forest)
        for code in ("distract", "pass", "sneak", "heal"):
            self.assertTrue(costly_plan(self.forest, answer(code)), code)
        for code in ("observe", "prepare", "dialogue", "clarify"):
            self.assertFalse(costly_plan(self.forest, answer(code)), code)
        self.assertEqual(self.forest, before)
        full = deepcopy(self.forest)
        full["character"]["hp"] = full["character"]["max_hp"]
        self.assertFalse(costly_plan(full, answer("heal")))
        distracted = deepcopy(self.forest)
        distracted["scene_changes"] = {"dark_forest_loc": {"forest_slime": {"distracted": True}}}
        self.assertFalse(costly_plan(distracted, answer("distract")))
        self.assertTrue(costly_plan(distracted, answer("sneak")))

    def test_free_inference_has_no_operation_name_table(self):
        def adjudicate(trial, plan):
            trial["character"]["mp"] -= 1
            return {"outcome": "success"}
        with patch.object(free_actions, "adjudicate", side_effect=adjudicate):
            self.assertTrue(costly_plan(self.forest, {"kind": "interact", "operation": "future_operation"}))
        with patch.object(free_actions, "adjudicate", return_value={"outcome": "failure", "roll": {"success": False}}):
            self.assertTrue(costly_plan(self.forest, {"kind": "interact", "operation": "future_operation"}))

    def test_missing_item_is_model_error_even_when_engine_catches_it(self):
        session = build_snapshot(recipes()["T"])
        raw = {**answer("heal"), "approach": "", "reply": ""}
        case = dict(input="薬草で回復する", tags=["missing_item"],
                    gold=[answer("unsupported"), answer("clarify")], harmful={"operation": ["use_item"]})
        with patch("scripts.eval.run.read_cache", return_value={"raw_response": json.dumps(raw)}), \
             patch.object(llm_client, "chat_completion", side_effect=AssertionError("network")):
            row = evaluate_case(case, session, {}, "gemini", "fake", "default", Path(".tmp-test/unused"))
        self.assertEqual(row["status"], "ok")
        self.assertEqual(severity(row), "S3")
        self.assertTrue(engine_caught(row))
        self.assertFalse(any(row["engine"]["changes"].values()))

    def test_missing_existing_action_is_caught_but_parse_failure_is_not(self):
        for code, expected in (("e:absent", True), ("dialogue", False)):
            row = self.row(code, engine={"outcome": "rejected"})
            self.assertEqual(engine_caught(row), expected)
        self.assertFalse(engine_caught({"plan": None, "engine": {"outcome": "rejected"}}))

    def test_normalization_is_preserved_in_new_scores(self):
        raw = {**answer("heal"), "target_id": "hero", "approach": "", "reply": ""}
        row = self.row("heal", "heal")
        row["plan"] = free_actions.parse_plan(json.dumps(raw), "hero")
        self.assertEqual(severity(row), "S0")
        raw = {**answer("e:go_inn"), "advance": True, "approach": "", "reply": ""}
        row = self.row("e:go_inn", "e:go_inn")
        row["plan"] = free_actions.parse_plan(json.dumps(raw), "hero")
        self.assertEqual(severity(row), "S0")

    def test_legal_declared_attempt_and_s4_audit(self):
        row = self.row("pass", "unsupported,dialogue,pass")
        row["engine"] = engine_result(self.forest, {**row["plan"], "approach": "", "reply": ""}, "通れた")
        self.assertEqual(severity(row), "S1")
        row["engine"]["after"]["resources"]["gold"] += 100
        self.assertEqual(severity(row), "S4")

    def test_reports_rates_tag_counts_and_legacy_metrics(self):
        rows = [self.row("dialogue"), self.row("clarify", "dialogue,clarify"),
                self.row("observe"), self.row("pass", harmful={"operation": ["distract"]}, engine={"outcome": "rejected"})]
        result = summarize(rows + [{"status": "skipped"}, {"status": "request_error"}])
        self.assertEqual(result["severity"], {"S0": 1, "S1": 1, "S2": 1, "S3": 1, "S4": 0})
        self.assertEqual(result["s0_s1_rate"], .5)
        self.assertEqual(result["s3_rate"], .25)
        self.assertEqual(result["exact"], .5)
        self.assertEqual(result["engine_caught"], 1)
        self.assertEqual(result["by_tag"]["negation"]["s3_count"], 1)
        report = report_markdown(dict(run_id="offline", metrics=result, errors=[]))
        self.assertIn("s0_s1_rate", report)
        self.assertIn("engine_caught", report)
        self.assertIsNone(summarize([])["s3_rate"])
        self.assertEqual(summarize(rows * 2)["severity"]["S3"], 2)
        for key in ("severity", "s0_s1_rate", "s3_rate", "engine_caught"):
            result.pop(key)
        for group in result["by_tag"].values():
            group.pop("s3_count")
            group.pop("engine_caught")
        self.assertIn("s3_rate | n/a", report_markdown(dict(run_id="v1", metrics=result, errors=[])))


class CandidateV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [json.loads(line) for line in OUTPUT.read_text(encoding="utf-8").splitlines()]

    def test_distribution_families_and_literal_inputs(self):
        rows = self.rows
        self.assertTrue(450 <= len(rows) <= 550)
        self.assertEqual(len({r["input"] for r in rows}), len(rows))
        counts = Counter(tag for row in rows for tag in row["tags"])
        self.assertTrue(all(counts[t] >= 20 for t in TAGS))
        self.assertTrue(.08 <= counts["language_mix"] / len(rows) <= .12)
        families = defaultdict(set)
        for row in rows:
            families[row["family"]].add(row["split"])
            self.assertTrue(row["gold_note"].startswith("依据 LABELING.md 第 "))
            self.assertEqual(row["label_status"], "proposed")
        self.assertTrue(all(len(s) == 1 for s in families.values()))
        splits = assign_splits(rows)
        self.assertEqual(splits, assign_splits(list(reversed(rows))))
        self.assertTrue(all(r["split"] == splits[r["family"]] for r in rows))
        for tag in TAGS:
            group = [r for r in rows if r["primary_tag"] == tag]
            self.assertLessEqual(abs(sum(r["split"] == "dev" for r in group) / len(group) - .4), .1)

    def test_character_ngrams_find_cross_family_leakage(self):
        self.assertEqual(similarity_violations(self.rows), [])
        pair = [dict(id="a", input="abcdefghijk", family="a"), dict(id="b", input="abcdefghijk!", family="b")]
        self.assertEqual(len(similarity_violations(pair)), 1)
        pair[1]["family"] = "a"
        self.assertEqual(similarity_violations(pair), [])

    def test_snapshots_cover_actions_scenes_actors_contexts_and_inventories(self):
        counts = Counter(r["snapshot"] for r in self.rows)
        self.assertGreaterEqual(len(counts), 20)
        actors, scenes, contexts = set(), set(), set()
        for identifier, count in counts.items():
            session = load_snapshot(identifier)
            actors.add(session["character"]["character_id"])
            scenes.add(session["world_state"]["scene_id"])
            if session["messages"]:
                contexts.add(identifier)
            self.assertTrue(json.loads(free_actions.build_plan_messages(session, "")[1]["content"])["actions"])
            if session["world_state"]["location_id"] == "dark_forest_loc":
                self.assertLessEqual(count / len(self.rows), .25)
        self.assertEqual(actors, {"hero", "mage", "thief"})
        self.assertEqual(len(scenes), 4)
        self.assertGreaterEqual(len(contexts), 5)
        for row in self.rows:
            if row["primary_tag"] == "context_followup":
                self.assertIn(row["snapshot"], contexts)
        thief = load_snapshot("v2_dark_forest_loc_thief")
        self.assertFalse(free_actions._owned_item(thief, "薬草"))
        self.assertTrue(free_actions._owned_item(load_snapshot("v2_dark_forest_loc_mage"), "薬草"))


if __name__ == "__main__":
    unittest.main()
