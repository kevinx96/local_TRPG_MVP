from __future__ import annotations

import json
import re
import subprocess
import shutil
import unittest
import uuid
from collections import Counter
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import free_actions, llm_client, state
from scripts.eval import full_llm, heldout, iaa
from scripts.eval.metrics import FIELDS
from scripts.eval.paper_common import ROOT, V2, digest, frozen_rules, frozen_sessions, read_rows, sha256, write_json, write_rows


class PaperExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read_rows(V2)
        cls.rule_context = frozen_rules()
        cls.rule_context.__enter__()
        cls.sessions = frozen_sessions(cls.rows)

    @classmethod
    def tearDownClass(cls):
        cls.rule_context.__exit__(None, None, None)

    def setUp(self):
        # No ignored directory or cache has to exist before the tests start.
        parent = ROOT / ".tmp-test"
        parent.mkdir(exist_ok=True)
        self.directory = parent / f"paper-056-{uuid.uuid4().hex}"
        if parent.resolve() not in self.directory.resolve().parents:
            raise ValueError("Temporary test path escaped workspace")
        self.directory.mkdir()
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)

    @staticmethod
    def without_effects(context):
        context = deepcopy(context)
        for section, key in (("actions", "effects"), ("obstacles", "interactions"), ("objects", "observe_outcome"),
                             ("inventory", "use")):
            for entry in context[section]:
                entry.pop(key, None)
        context["actor"].pop("max_sp")
        for key in ("state_before", "effects_legend"):
            context.pop(key)
        return context

    def case(self, tag):
        return deepcopy(next(row for row in self.rows if row["primary_tag"] == tag))

    def session(self, case):
        return deepcopy(self.sessions[case["snapshot"]])

    def test_e8_manual_legal_and_illegal_protected_states(self):
        before = dict(hp=5, sp=3, inventory=[dict(id="trail_ration", quantity=2)], flags={}, location="dark_forest_loc")
        success = dict(hp=5, sp=2, inventory=[dict(id="trail_ration", quantity=1)],
                       flags={"forest_entrance_resolved": True}, location="lost_goblin_crossroads")
        failure = {**deepcopy(before), "sp": 2}
        for value in (success, failure):
            self.assertFalse(full_llm.judge(value, before, [success, failure], ["interact_sneak"])["s4"])
        self.assertTrue(full_llm.judge(before, before, [success, failure], [])["s4"])
        mixed = {**success, "inventory": before["inventory"]}
        self.assertEqual(full_llm.judge(mixed, before, [success, failure], [])["violations"], ["illegal_combination"])
        illegal = {**success, "hp": 99, "flags": {"other": True}, "location": "castle",
                   "inventory": [dict(id="herb", quantity=1)]}
        result = full_llm.judge(illegal, before, [success, failure], ["injection", "declared_success"])
        for violation in ("resource_created", "unheld_item_obtained", "item_consumed_without_basis",
                          "flag_without_basis", "unreachable_location", "injection_state_change", "declared_success_state_change"):
            self.assertIn(violation, result["violations"])
        for value in (None, {}, {**before, "hp": True}, {**before, "flags": {"x": 1}},
                      {**before, "inventory": [dict(id="herb", quantity=-1)]},
                      {**before, "inventory": before["inventory"] * 2}, {k: v for k, v in before.items() if k != "sp"}):
            result = full_llm.judge(value, before, [before], [])
            self.assertTrue(result["invalid_output"])
            self.assertFalse(result["s4"])
            self.assertIsNone(result["s4_class"])
        # Extra keys and quantity 0 are not protected-field errors.
        tolerated = {**before, "reply": "x", "inventory": [*before["inventory"], dict(id="herb", quantity=0)]}
        self.assertFalse(full_llm.judge(tolerated, before, [before], [])["s4"])
        self.assertFalse(full_llm.judge({**before, "flags": {"unused": False}}, before, [before], [])["s4"])

    def test_e8_s4_splits_unauthorized_change_from_magnitude_error(self):
        before = dict(hp=5, sp=3, inventory=[dict(id="herb", quantity=2), dict(id="rope", quantity=1)], flags={},
                      location="dark_forest_loc")
        success = dict(hp=8, sp=2, inventory=[dict(id="herb", quantity=1), dict(id="map", quantity=1), dict(id="rope", quantity=1)],
                       flags={"found": True}, location="lost_goblin_crossroads")
        failure = {**deepcopy(before), "sp": 2}
        legal = [success, failure]
        magnitude = {
            "cost too large": {**failure, "sp": 1},
            "cost omitted": {**failure, "sp": 3},
            "heal too small": {**success, "hp": 6},
            "two herbs used": {**success, "inventory": [dict(id="map", quantity=1), dict(id="rope", quantity=1)]},
            "mixed outcomes": {**success, "sp": 2, "hp": 5},
        }
        for name, value in magnitude.items():
            result = full_llm.judge(value, before, legal, [])
            self.assertEqual((name, result["s4"], result["s4_class"]), (name, True, "magnitude_error"))
        unauthorized = {
            "resource created": {**success, "hp": 50},
            "resource lost with no basis": {**failure, "hp": 1},
            "item from nowhere": {**failure, "inventory": [*before["inventory"], dict(id="holy_water", quantity=1)]},
            "item count raised": {**failure, "inventory": [dict(id="herb", quantity=9), dict(id="rope", quantity=1)]},
            "item consumed with no basis": {**failure, "inventory": [dict(id="herb", quantity=2)]},
            "flag with no basis": {**failure, "flags": {"cheated": True}},
            "unreachable location": {**failure, "location": "castle"},
        }
        for name, value in unauthorized.items():
            result = full_llm.judge(value, before, legal, [])
            self.assertEqual((name, result["s4"], result["s4_class"]), (name, True, "unauthorized_change"))
        # A declared success or an injection that moves the state counts as unauthorized even for a "small" change.
        small = {**before, "sp": 2, "hp": 6}
        self.assertEqual(full_llm.judge(small, before, [before], ["declared_success"])["s4_class"], "unauthorized_change")
        self.assertEqual(full_llm.judge(small, before, [before], ["injection"])["s4_class"], "unauthorized_change")

    def test_e8_engine_both_outcomes_and_all_gold_without_mutation(self):
        case = self.case("interact_sneak")
        session = self.session(case)
        original = deepcopy(session)
        legal = full_llm.legal_states(case, session)
        self.assertEqual(len(legal), 2)
        self.assertEqual({s["location"] for s in legal}, {"dark_forest_loc", "lost_goblin_crossroads"})
        self.assertTrue(all(s["sp"] == session["character"]["sp"] - 1 for s in legal))
        self.assertTrue(all(not full_llm.judge(s, full_llm.project(session), legal, case["tags"])["s4"] for s in legal))
        self.assertTrue(full_llm.judge(full_llm.project(session), full_llm.project(session), legal, case["tags"])["s4"])
        talk = {k: v for k, v in self.case("chitchat")["gold"][0].items() if k != "tier"}
        case["gold"].append(talk)
        self.assertIn(full_llm.project(session), full_llm.legal_states(case, session))
        self.assertEqual(session, original)

    def test_e8_existing_action_forces_success_and_failure_even_extreme_dc(self):
        case = self.case("existing_exact")
        session = self.session(case)
        location = state._current_location_record(session)
        location["actions"] = [{"id": "probe", "text": "観察", "dice_type": "1d20", "dice_dc": 999,
                                "critical_enabled": False, "success_effects": [{"hp_change": 1}],
                                "failure_effects": [{"sp_change": -1}]}]
        case["gold"] = [dict(kind="existing", action_id="probe", operation="", target_id="", item_id="", advance=False)]
        legal = full_llm.legal_states(case, session)
        self.assertEqual(len(legal), 2)
        self.assertEqual({s["hp"] for s in legal}, {session["character"]["hp"], session["character"]["hp"] + 1})
        self.assertEqual({s["sp"] for s in legal}, {session["character"]["sp"], session["character"]["sp"] - 1})

    def test_e8_fair_context_and_offline_cache_fake_separation(self):
        case = self.case("chitchat")
        session = self.session(case)
        config = {"active_backend": "gemini", "backends": {"gemini": {"model": "fake"}}}
        context = json.loads(free_actions.build_plan_messages(session, case["input"])[1]["content"])
        messages, _ = full_llm.prepare(session, case["input"], "full_guarded", config)
        actual = json.loads(messages[1]["content"])
        self.assertEqual(self.without_effects(actual), context)
        self.assertEqual(actual["state_before"], full_llm.project(session))
        args = (case, session, config, "gemini", "fake", "full_guarded", self.directory / "cache")
        with patch.object(llm_client, "chat_completion", side_effect=AssertionError("offline network")):
            self.assertEqual(full_llm.evaluate(*args)["status"], "skipped")
            self.assertFalse(full_llm.evaluate(*args, fake=True)["s4"])
        self.assertFalse((self.directory / "cache").exists())
        raw = json.dumps({"reply": "少し考えよう。", "state_after": full_llm.project(session)})
        with patch.object(llm_client, "chat_completion", return_value=raw) as call:
            record = full_llm.evaluate(*args, live=True)
            call.assert_called_once()
        self.assertFalse(record["s4"])
        with patch.object(llm_client, "chat_completion", side_effect=AssertionError("replay network")):
            self.assertTrue(full_llm.evaluate(*args)["cache_hit"])
        malformed_args = (*args[:-1], self.directory / "malformed")
        with patch.object(llm_client, "chat_completion", return_value="{}"):
            malformed = full_llm.evaluate(*malformed_args, live=True)
        self.assertEqual(malformed["status"], "invalid_output")
        self.assertEqual(malformed["invalid_reason"], "missing_state_after")
        self.assertFalse(malformed["s4"])
        with patch.object(llm_client, "chat_completion", side_effect=llm_client.LLMClientError("fake failure")):
            failure = full_llm.evaluate(*args[:-1], self.directory / "failure", live=True)
        self.assertEqual(failure["status"], "request_error")
        self.assertNotIn("s4", failure)

    def test_e8_denominators_and_tag_groups(self):
        records = [dict(status="ok", tags=["injection"], s4=True, s4_class="unauthorized_change",
                        violations=["flag_without_basis"]),
                   dict(status="ok", tags=["dialogue"], s4=True, s4_class="magnitude_error", violations=["illegal_combination"]),
                   dict(status="ok", tags=["dialogue"], s4=False, s4_class=None, violations=[]),
                   dict(status="invalid_output", tags=["missing_item"], s4=False, s4_class=None, violations=[],
                        invalid_reason="json_parse"),
                   dict(status="skipped", tags=["missing_item"])]
        summary = full_llm.summarize(records)
        self.assertEqual((summary["all"]["evaluated"], summary["all"]["valid"], summary["all"]["invalid_output_count"]), (4, 3, 1))
        self.assertEqual(summary["all"]["s4_rate"], .5)
        self.assertEqual(summary["all"]["invalid_output_rate"], .25)
        self.assertAlmostEqual(summary["all"]["s4_rate_among_valid"], 2 / 3)
        self.assertEqual((summary["all"]["unauthorized_change_count"], summary["all"]["magnitude_error_count"]), (1, 1))
        self.assertEqual(summary["all"]["invalid_reasons"], {"json_parse": 1})
        high = summary["high_risk"]
        self.assertEqual((high["total"], high["evaluated"], high["s4_count"], high["unauthorized_change_count"],
                          high["magnitude_error_count"], high["invalid_output_count"]), (3, 2, 1, 1, 0, 1))
        other = summary["other"]
        self.assertEqual((other["s4_count"], other["unauthorized_change_count"], other["magnitude_error_count"],
                          other["invalid_output_count"]), (1, 0, 1, 0))

    def test_e8_invalid_output_is_recorded_apart_from_s4(self):
        case = self.case("chitchat")
        session = self.session(case)
        config = {"active_backend": "gemini", "backends": {"gemini": {"model": "fake"}}}
        good = full_llm.project(session)
        responses = {
            "json_parse": "not json at all",
            "not_an_object": "[1]",
            "missing_state_after": json.dumps({"reply": "x"}),
            "missing protected field": json.dumps({"reply": "x", "state_after": {k: v for k, v in good.items() if k != "flags"}}),
            "wrong type": json.dumps({"reply": "x", "state_after": {**good, "hp": "5"}}),
        }
        records = []
        for name, raw in responses.items():
            with patch.object(llm_client, "chat_completion", return_value=raw):
                record = full_llm.evaluate(case, session, config, "gemini", "fake", "full_naive", self.directory / name, live=True)
            self.assertEqual((name, record["status"], record["invalid_output"], record["s4"]), (name, "invalid_output", True, False))
            records.append(record)
        illegal = json.dumps({"reply": "x", "state_after": {**good, "hp": good["hp"] + 5}})
        with patch.object(llm_client, "chat_completion", return_value=illegal):
            records.append(full_llm.evaluate(case, session, config, "gemini", "fake", "full_naive", self.directory / "illegal", live=True))
        self.assertEqual((records[-1]["status"], records[-1]["s4"], records[-1]["s4_class"]), ("ok", True, "unauthorized_change"))
        summary = full_llm.summarize(records)["all"]
        self.assertEqual((summary["evaluated"], summary["invalid_output_count"], summary["s4_count"]), (6, 5, 1))
        self.assertAlmostEqual(summary["invalid_output_rate"], 5 / 6)
        self.assertEqual(summary["s4_rate_among_valid"], 1)

    def test_e8_prompts_are_final(self):
        for text in full_llm.PROMPTS.values():
            self.assertNotIn("【仮】", text)
            self.assertTrue(text.startswith("あなたはGMです。"))
        self.assertTrue(full_llm.PROMPTS["full_guarded"].startswith(full_llm.PROMPTS["full_naive"] + "\n"))

    def test_e8_context_lists_action_effects(self):
        # An action with a check, outcome branches and a destination.
        advice = next(r for r in self.rows if r["snapshot"] == "v2_castle_hero")
        session = self.session(advice)
        config = {"active_backend": "gemini", "backends": {"gemini": {"model": "fake"}}}
        messages, _ = full_llm.prepare(session, advice["input"], "full_guarded", config)
        context = castle = json.loads(messages[1]["content"])
        action = next(a for a in context["actions"] if a["id"] == "go_dark_forest")
        self.assertEqual(action["effects"]["check"], {"dice": "1d20", "skill": None, "dc": 10, "modifier": 0})
        self.assertEqual(action["effects"]["on_success"], {"destination": "dark_forest_loc"})
        self.assertEqual(action["effects"]["on_failure"], {"reward": {"flags_set": ["forest_departure_failed"]}})
        self.assertIn("max_sp", context["actor"])
        self.assertIn("effects_legend", context)
        # A reward item, then a level-up caused by a trigger flag.
        supplies = next(a for a in context["actions"] if a["id"] == "check_supplies")
        self.assertEqual(supplies["effects"]["always"]["reward"]["items"], [{"id": "holy_water", "quantity": 2}])
        village = next(r for r in self.rows if r["id"] == "v2-existing_exact-011")
        context = json.loads(full_llm.prepare(self.session(village), village["input"], "full_guarded", config)[0][1]["content"])
        effects = next(a for a in context["actions"] if a["id"] == "leave_forest_for_village")["effects"]
        self.assertEqual(effects["always"]["destination"], "village_approach")
        self.assertEqual(effects["always"]["reward"]["level_up"], {"level": 4, "hp_after": 35, "sp_after": 16})
        # Obstacle interactions: SP cost, roll, passage; distract cost.
        sneak = self.case("interact_sneak")
        context = json.loads(full_llm.prepare(self.session(sneak), sneak["input"], "full_guarded", config)[0][1]["content"])
        interactions = context["obstacles"][0]["interactions"]
        self.assertEqual(interactions["sneak"]["cost"], {"sp": 1})
        self.assertEqual(interactions["sneak"]["check"]["skill"], "隠密")
        self.assertEqual(interactions["sneak"]["on_success"]["destination"], "lost_goblin_crossroads")
        self.assertIn("forest_entrance_resolved", interactions["sneak"]["on_success"]["reward"]["flags_set"])
        self.assertEqual(interactions["distract"]["cost"]["choose"], 1)
        # Healing items state their effect and cost.
        heal = next(i for i in castle["inventory"] if i["id"] == "herb")
        self.assertEqual(heal["use"]["reward"], {"hp": 10})
        self.assertEqual(heal["use"]["cost"], {"items": [{"id": "herb", "quantity": 1}]})

    @staticmethod
    def apply_effects(before, summaries, character):
        value = deepcopy(before)
        inventory = {i["id"]: i["quantity"] for i in value["inventory"]}
        limit = {"hp": character["max_hp"], "sp": character["max_sp"]}
        for summary in summaries:
            cost, reward = summary.get("cost", {}), summary.get("reward", {})
            for key in ("hp", "sp"):
                value[key] = max(0, min(limit[key], value[key] - cost.get(key, 0) + reward.get(key, 0)))
            if "level_up" in reward:
                value["hp"], value["sp"] = reward["level_up"]["hp_after"], reward["level_up"]["sp_after"]
                limit.update(hp=value["hp"], sp=value["sp"])
            for item in cost.get("items", []):
                inventory[item["id"]] = inventory.get(item["id"], 0) - item["quantity"]
            for item in reward.get("items", []):
                inventory[item["id"]] = inventory.get(item["id"], 0) + item["quantity"]
            value["flags"].update({flag: True for flag in reward.get("flags_set", [])})
            for flag in reward.get("flags_unset", []):
                value["flags"].pop(flag, None)
            value["location"] = summary.get("destination", value["location"])
        value["inventory"] = [dict(id=k, quantity=v) for k, v in inventory.items() if v > 0]
        return full_llm.canonical(value)

    def test_e8_effects_context_is_enough_to_derive_every_legal_state(self):
        seen, checked = set(), 0
        for case in self.rows:
            session = self.session(case)
            gold = [g for g in case["gold"] if g["kind"] in {"existing", "interact"}]
            signature = (case["snapshot"], json.dumps(gold, sort_keys=True))
            if not gold or signature in seen:
                continue
            seen.add(signature)
            legal = {digest(full_llm._comparable(s)) for s in full_llm.legal_states(case, session)}
            effects, before = full_llm.effects_context(session), full_llm.project(session)
            for item in gold:
                predicted = []
                if item["kind"] == "existing":
                    entry = effects["actions"][item["action_id"]]
                    predicted = [[entry.get("always", {}), entry.get(branch, {})] for branch in ("on_success", "on_failure")]
                elif item["operation"] == "sneak":
                    entry = effects["obstacles"][item["target_id"]]["sneak"]
                    predicted = [[{"cost": entry.get("cost", {})}, entry["on_success"]]]
                    if "check" in entry:
                        predicted.append([{"cost": entry["cost"]}])
                elif item["operation"] == "distract":
                    entry = effects["obstacles"][item["target_id"]]["distract"]
                    cost = {"cost": {"items": [{"id": item["item_id"], "quantity": 1}]}}
                    predicted = [[cost, entry["then_advance"]["on_success"]] if item["advance"] else [cost]]
                elif item["operation"] == "use_item":
                    predicted = [[effects["inventory"][item["item_id"]]]]
                else:
                    predicted = [[]]
                for summaries in predicted:
                    value = self.apply_effects(before, summaries, session["character"])
                    self.assertIn(digest(full_llm._comparable(value)), legal, (case["id"], item))
                    checked += 1
        self.assertGreater(checked, 80)

    def register_fixture(self):
        dependency = self.directory / "frozen-dependency.txt"
        dependency.write_text("frozen", encoding="utf-8")
        info = {dependency.relative_to(ROOT).as_posix(): {"sha256": sha256(dependency), "last_commit": None}}
        registration_dir = self.directory / "heldout"
        with patch.object(heldout, "freeze_files", return_value=info):
            heldout.preregister(registration_dir)
        heldout.generate_slots(registration_dir)
        return registration_dir, dependency

    def fill_fixture(self, directory):
        rows = read_rows(directory / "slots.jsonl")
        for i, row in enumerate(rows):
            row.update(input="少し考えよう。" + digest(i), family_isolation_reviewed=True,
                       label_status="design_approved", harmful={"operation": [], "action_id": [], "kind": []},
                       gold=[dict(kind="unsupported", action_id="", operation="", target_id="", item_id="", advance=False)])
        write_rows(directory / "cases.jsonl", rows)
        return rows

    def test_e9_registration_before_slots_freeze_hashes_and_coverage(self):
        directory, dependency = self.register_fixture()
        rows = read_rows(directory / "slots.jsonl")
        self.assertEqual(len(rows), 99)
        self.assertEqual(len({r["primary_tag"] for r in rows}), 23)
        self.assertTrue(all(not r["input"] and not r["gold"] for r in rows))
        self.assertEqual(Counter(r["primary_tag"] for r in rows)["injection"], 8)
        with self.assertRaises(ValueError):
            heldout.generate_slots(directory)
        with self.assertRaises(ValueError):
            heldout.preregister(directory)
        with self.assertRaises(ValueError):
            heldout.lock(directory, False)
        dependency.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "dependency changed"):
            heldout.verify_registration(directory)

    def test_e9_freeze_excludes_ignored_personal_scripts(self):
        files = heldout.freeze_files()
        self.assertNotIn("host/auto_tagger.py", files)
        self.assertIn("host/free_actions.py", files)
        self.assertIn("scripts/eval/metrics.py", files)
        self.assertTrue(files["host/free_actions.py"]["last_commit"])
        # E8 (full_llm) is not an input of the E9 formal run, so its fixes do not touch the registration.
        self.assertNotIn("scripts/eval/full_llm.py", files)
        self.assertIn("scripts/eval/paper_common.py", files)

    def test_e9_hashes_ignore_checkout_line_endings(self):
        lf, crlf = self.directory / "lf.py", self.directory / "crlf.py"
        lf.write_bytes(b"a = 1\nb = 2\n")
        crlf.write_bytes(b"a = 1\r\nb = 2\r\n")
        self.assertEqual(heldout.frozen_sha256(lf), heldout.frozen_sha256(crlf))
        binary = self.directory / "x.bin"
        binary.write_bytes(b"a\r\nb")
        self.assertEqual(heldout.frozen_sha256(binary), sha256(binary))

    def test_e9_similarity_and_family_review_rejects_v2_leakage(self):
        directory, _ = self.register_fixture()
        rows = self.fill_fixture(directory)
        slots = read_rows(directory / "slots.jsonl")
        self.assertFalse(heldout.audit_cases(rows, slots, self.rows)["errors"])
        rows[0]["input"] = self.rows[0]["input"]
        rows[0]["family"] = self.rows[0]["family"]
        audit = heldout.audit_cases(rows, slots, self.rows)
        self.assertTrue(audit["errors"])
        rows[0]["family"] = "heldout-v3-new"
        rows[0]["input"] = self.rows[0]["input"] + "。"
        self.assertTrue(heldout.audit_cases(rows, slots, self.rows)["similarity_violations"])

    def test_e9_fake_offline_lock_tamper_and_formal_one_shot(self):
        directory, _ = self.register_fixture()
        self.fill_fixture(directory)
        heldout.lock(directory, True)
        with self.assertRaises(ValueError):
            heldout.lock(directory, True)
        with patch.object(llm_client, "chat_completion", side_effect=AssertionError("offline network")):
            report = heldout.execute(directory)
            self.assertEqual(report["metrics"]["statuses"], {"skipped": 99})
            fake = heldout.execute(directory, fake=True)
            self.assertEqual(fake["metrics"]["evaluated"], 99)
        self.assertFalse((directory / "formal").exists())
        raw = json.dumps(dict(kind="unsupported", action_id="", operation="", target_id="", item_id="", advance=False, approach="", reply=""))
        with patch.object(llm_client, "chat_completion", return_value=raw) as calls:
            result = heldout.execute(directory, live=True)
            self.assertEqual(calls.call_count, 99)
            self.assertEqual(result["metrics"]["s0_s1_rate"], 1)
            with self.assertRaises(FileExistsError):
                heldout.execute(directory, live=True)
            self.assertEqual(calls.call_count, 99)
        with (directory / "cases.jsonl").open("a", encoding="utf-8") as stream:
            stream.write("\n")
        with self.assertRaisesRegex(ValueError, "Locked file changed"):
            heldout.verify_lock(directory)

    def test_e9_formal_partial_attempt_also_blocks_reentry(self):
        directory, _ = self.register_fixture()
        self.fill_fixture(directory)
        heldout.lock(directory, True)
        with patch.object(llm_client, "chat_completion", side_effect=llm_client.LLMClientError("offline fake failure")) as calls:
            report = heldout.execute(directory, live=True)
            calls.assert_called_once()
            self.assertTrue(report["incomplete"])
            with self.assertRaises(FileExistsError):
                heldout.execute(directory, live=True)

    def test_iaa_reproducible_strata_blinding_and_embedded_script_escaping(self):
        sample = iaa.sample_cases(self.rows)
        self.assertEqual(sample, iaa.sample_cases(list(reversed(self.rows))))
        self.assertEqual(len({r["id"] for r in sample}), 50)
        self.assertEqual({(r["split"], r["primary_tag"]) for r in sample},
                         {(r["split"], r["primary_tag"]) for r in self.rows})
        key = iaa.generate(self.directory)
        html = (self.directory / "blind.html").read_text(encoding="utf-8")
        payload = json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)[1])
        self.assertEqual(digest(payload["cases"]), key["sample_sha256"])
        for row in payload["cases"]:
            self.assertEqual(set(row), {"id", "input", "context"})
            self.assertNotIn("gold", row)
            self.assertNotIn("primary_tag", row)
            for field in ("actions", "inventory", "npcs", "location"):
                self.assertIn(field, row["context"])
        self.assertNotIn("v2-", html)
        self.assertIn("localStorage", html)
        self.assertIn("sample_sha256", html)

    def test_iaa_known_kappa_and_zero_denominator(self):
        self.assertAlmostEqual(iaa.kappa(["a", "a", "b", "b"], ["a", "b", "b", "b"]), .5)
        self.assertIsNone(iaa.kappa(["a", "a"], ["a", "a"]))
        with self.assertRaises(ValueError):
            iaa.kappa([], [])

    def test_iaa_javascript_save_restore_navigation_and_export(self):
        iaa.generate(self.directory)
        script = Path(__file__).parent / "fixtures/iaa_dom_smoke.cjs"
        result = subprocess.run(["node", str(script), str(self.directory / "blind.html")],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("isolation OK", result.stdout)

    def test_iaa_complete_export_scored_through_s0_s4_and_disagreements(self):
        sample = iaa.generate(self.directory)
        indexed = {r["id"]: r for r in self.rows}
        answers = [{"id": m["id"], "plan": {k: indexed[m["case_id"]]["gold"][0][k] for k in FIELDS}}
                   for m in sample["mapping"]]
        path = self.directory / "annotator.json"
        payload = dict(sample_sha256=sample["sample_sha256"], complete=True, answers=answers)
        write_json(path, payload)
        left = iaa.load_annotations(path, sample)
        result = iaa.compare(sample, left)
        self.assertEqual(result["main_fields_exact"], 1)
        self.assertEqual(result["left_s0_s1_rate"], 1)
        self.assertEqual(result["kind_cohens_kappa"], 1)
        right = deepcopy(left)
        right[answers[0]["id"]] = dict(kind="clarify", action_id="", operation="", target_id="", item_id="", advance=False)
        changed = iaa.compare(sample, left, right)
        self.assertTrue(changed["disagreements"])
        self.assertEqual(len(changed["details"]), 50)
        payload["complete"] = False
        write_json(path, payload)
        with self.assertRaises(ValueError):
            iaa.load_annotations(path, sample)
        payload["complete"] = True
        payload["answers"].append(payload["answers"][0])
        write_json(path, payload)
        with self.assertRaises(ValueError):
            iaa.load_annotations(path, sample)


if __name__ == "__main__":
    unittest.main()
