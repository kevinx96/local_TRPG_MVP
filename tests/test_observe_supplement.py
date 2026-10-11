from __future__ import annotations

import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from host import free_actions, llm_client, state
from scripts.eval.audit import allowed_state, unearned_change
from scripts.eval import benchmark_v2_scenario as supplement
from scripts.eval.benchmark_v2 import similarity_violations
from scripts.eval.generate_candidates import gold
from scripts.eval.metrics import engine_caught, severity
from scripts.eval.run import engine_result, protected_state
from scripts.eval.snapshots import ROOT, build_snapshot, load_snapshot, isolated_engine
from scripts.scenario.upgrade_v2 import upgrade


class ObserveSupplementTests(unittest.TestCase):
    def test_observe_audit_accepts_rule_effects_but_detects_unearned_changes(self):
        for snapshot, target in (("v2cur_castle_hero", "general"),
                                 ("v2cur_castle_hero", "general_breath"),
                                 ("v2cur_ice_elemental_encounter_mage", "frost_crystal"),
                                 ("v2cur_goblin_fort_third_gate_hero", "iron_gate_window")):
            for value in (20, 1):
                with self.subTest(target=target, roll=value):
                    session = load_snapshot(snapshot)
                    trial = deepcopy(session)
                    plan = {**gold("interact", operation="observe", target_id=target), "approach": "", "reply": ""}
                    with isolated_engine("observe-audit"), patch.object(state.random, "randint", return_value=value):
                        result = free_actions.adjudicate(trial, plan)
                    expected = allowed_state(session, plan, result)
                    self.assertEqual(protected_state(expected), protected_state(trial))
                    self.assertEqual(session, load_snapshot(snapshot))
                    tampered = {**deepcopy(result), "state_delta": {"gold_change": 1000}}
                    self.assertEqual(protected_state(allowed_state(session, plan, tampered)), protected_state(expected))
                    record = {"engine": {"before": protected_state(session), "after": protected_state(trial),
                                         "allowed_after": protected_state(expected)}}
                    self.assertFalse(unearned_change(record))
                    record["engine"]["after"]["resources"]["gold"] += 1
                    self.assertTrue(unearned_change(record))
                    repeated = deepcopy(trial)
                    with isolated_engine("observe-repeat"), patch.object(state, "roll_dice") as roll:
                        repeat_result = free_actions.adjudicate(repeated, plan)
                    roll.assert_not_called()
                    self.assertEqual(protected_state(allowed_state(trial, plan, repeat_result)), protected_state(repeated))

    def test_section_one_text_is_verbatim_in_both_packs_and_generator(self):
        spec = (ROOT / "docs/specs/011-observe-fixes-and-v2-supplement.md").read_text(encoding="utf-8")
        rows = [line.split("|")[1:-1] for line in spec.splitlines() if line.startswith("| `")]
        self.assertEqual(len(rows), 3)
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = state.load_scenario_pack(ROOT / "host/prompt/processed" / filename)
            regenerated = deepcopy(pack)
            upgrade(regenerated)
            for source in (pack, regenerated):
                objects = {o["id"]: o for loc in source["locations"] for o in loc.get("objects", [])}
                for identifier, description, success, failure in rows:
                    obj = objects[identifier.strip().strip("`")]
                    self.assertEqual(obj["description"], description.strip())
                    self.assertEqual(obj["observe_reveals"]["success_text"], success.strip().removesuffix("（不变）"))
                    self.assertEqual(obj["observe_reveals"]["failure_text"], failure.strip())
                self.assertEqual(objects["general_breath"]["npc_id"], "general")

    def test_gate_observation_does_not_open_or_move_through_gate(self):
        session = load_snapshot("v2cur_goblin_fort_third_gate_hero")
        plan = {**gold("interact", operation="observe", target_id="iron_gate_window"), "approach": "", "reply": ""}
        before = deepcopy(session["world_state"])
        with isolated_engine("window"), patch.object(state.random, "randint", return_value=20):
            result = free_actions.adjudicate(session, plan)
        self.assertEqual(result["outcome"], "success")
        self.assertTrue(session["flags"]["knows_fort_password"])
        self.assertEqual(session["world_state"], before)
        self.assertNotIn("開ける", result["text"])

    def test_alias_preserves_rejections_and_is_only_used_for_observe(self):
        original = load_snapshot("v2cur_castle_hero")
        for updates in ({"item_id": "herb"}, {"advance": True}, {"operation": "prepare"},
                        {"operation": "distract"}, {"operation": "sneak"}):
            session = deepcopy(original)
            plan = {**gold("interact", operation="observe", target_id="general"),
                    "approach": "", "reply": "", **updates}
            with self.subTest(updates=updates), patch.object(state, "roll_dice") as roll:
                self.assertEqual(free_actions.adjudicate(session, plan)["outcome"], "rejected")
                self.assertEqual(session, original)
                roll.assert_not_called()
        plan = {**gold("dialogue", target_id="general"), "approach": "", "reply": "少し考えよう。"}
        self.assertEqual(free_actions.adjudicate(original, plan)["outcome"], "dialogue")


class ScenarioCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [json.loads(line) for line in supplement.OUTPUT.read_text(encoding="utf-8").splitlines()]

    def test_authored_candidates_and_all_gold_pass_offline_audit(self):
        self.assertEqual(self.rows, supplement.authored_rows())
        with patch.object(llm_client, "chat_completion", side_effect=AssertionError("network")):
            result = supplement.audit(self.rows)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["total"], 50)
        self.assertEqual(result["split"], {"dev": 50})
        self.assertEqual(result["gold_checked"], sum(len(r["gold"]) for r in self.rows))
        self.assertTrue(all(result["primary_tags"][tag] >= 6 for tag in supplement.TAGS))

    def test_new_snapshots_are_deterministic_and_evidence_is_engine_owned(self):
        for alias, recipe in supplement.recipes().items():
            with self.subTest(snapshot=recipe["id"]):
                checked_in = json.loads((ROOT / "eval/snapshots" / f"{recipe['id']}.json").read_text(encoding="utf-8"))
                self.assertEqual(checked_in, recipe)
                session = build_snapshot(recipe)
                self.assertEqual(session, load_snapshot(recipe["id"]))
                self.assertEqual(session["world_state"]["location_id"], recipe["location_id"])
                if alias in {"E", "N"}:
                    context = json.loads(free_actions.build_plan_messages(session, "")[1]["content"])
                    actions = {a["id"]: a for a in context["actions"]}
                    self.assertEqual("report_with_evidence" in actions, alias == "E")
                    if alias == "E":
                        self.assertTrue(actions["report_with_evidence"]["enabled"])
                    self.assertEqual(bool(free_actions._owned_item(session, "white_dragon_scale")), alias == "E")
                elif alias == "C":
                    self.assertEqual(session["flags"], {})

    def test_claims_cannot_reveal_and_reveal_is_harmful_even_when_caught(self):
        bad = gold("existing", action_id="report_with_evidence")
        for row in self.rows:
            if row["primary_tag"] != "evidence_claim":
                continue
            with self.subTest(case=row["id"]):
                session = load_snapshot(row["snapshot"])
                plan = {**bad, "approach": "", "reply": ""}
                result = engine_result(session, plan, row["input"])
                record = {**row, "plan": plan, "engine": result}
                self.assertEqual(severity(record), "S3")
                self.assertTrue(engine_caught(record))
                self.assertFalse(any(result["changes"].values()))
                for entry in row["gold"]:
                    self.assertIn(entry["kind"], {"unsupported", "dialogue"})
                    self.assertEqual(entry["tier"], "S0")

    def test_waiting_never_finishes_report_or_starts_reveal(self):
        for row in self.rows:
            if row["primary_tag"] != "report_choice" or row["gold"][0]["kind"] != "dialogue":
                continue
            for action_id in ("report_normally", "report_with_evidence"):
                with self.subTest(case=row["id"], action=action_id):
                    self.assertEqual(severity({**row, "plan": gold("existing", action_id=action_id)}), "S3")

    def test_similarity_has_no_cross_family_collisions_with_frozen_benchmark(self):
        frozen = [json.loads(line) for line in (ROOT / "eval/benchmark/intent_v2.jsonl").read_text(encoding="utf-8").splitlines()]
        violations = similarity_violations(frozen + self.rows)
        self.assertEqual([v for v in violations if v["left"].startswith("v2-scenario-")], [])


if __name__ == "__main__":
    unittest.main()
