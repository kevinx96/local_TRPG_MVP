from __future__ import annotations

import json
import random
import unittest
import uuid
from copy import deepcopy
from unittest.mock import patch

from host import app, free_actions, state
from scripts.balance import checkpoints, class_aware
from scripts.scenario import checks_e, checks_v2


class ChecksV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)

    def session(self, character="thief", location="castle"):
        session = checkpoints.fresh_session(deepcopy(self.pack), character)
        state.commit_world_position(session, location_id=location)
        return session

    def check(self, session, skill="隠密", **conditions):
        spec = {"skill": skill, "dc": 10, **conditions}
        return state.dice_check_info(session, "1d20+str", 10, roll=spec)

    def plan(self, operation="observe", target="general_breath", **changes):
        return dict(kind="interact", action_id="", operation=operation, target_id=target,
                    item_id="", advance=operation == "sneak", approach="周囲を見る", reply="", **changes)

    def test_modifier_floor_proficiency_levels_and_skill_attribute(self):
        session = self.session()
        for attribute, expected in ((5, 2), (9, 2), (10, 2), (11, 2), (12, 3), (16, 5), (17, 5)):
            session["character"]["attributes"]["dex"] = attribute
            with self.subTest(attribute=attribute):
                info = self.check(session)
                self.assertEqual(info["modifier"], expected)
                self.assertEqual(info["attribute"], "dex")
        for level, expected in ((1, 5), (3, 5), (4, 6), (5, 6)):
            session["character"].update(level=level)
            session["character"]["attributes"]["dex"] = 16
            self.assertEqual(self.check(session)["modifier"], expected)
        hero = self.session("hero")
        hero["character"]["attributes"]["dex"] = 16
        self.assertEqual(self.check(hero)["modifier"], 3)
        hero["scenario_pack"]["characters"][0]["check_proficiencies"].append("隠密")
        self.assertEqual(self.check(hero)["modifier"], 5)

    def test_missing_attributes_use_zero_modifier_and_preserve_proficiency(self):
        session = {"character": {"attributes": {}}, "dice_log": []}
        for attribute in state.CHECK_ATTRIBUTE_LABELS:
            with self.subTest(attribute=attribute):
                expression = f"1d20+{attribute}"
                info = state.dice_check_info(session, expression, 10)
                rolled = state.roll_dice(session, expression, 10, client_rolls=[10])
                self.assertEqual(info["modifier"], 0)
                self.assertEqual(rolled["attr_mod"], 0)
                self.assertEqual(rolled["total"], 10)
        hero = self.session("hero")
        hero["character"]["attributes"].pop("str")
        self.assertEqual(self.check(hero, "運動")["modifier"], 2)
        with self.assertRaisesRegex(ValueError, "Unknown dice attribute"):
            state.dice_check_info(session, "1d20+unknown", 10)

    def test_all_companion_assistance_is_data_driven_and_requires_present_companion(self):
        session = self.session("hero")
        for companion in session["scenario_pack"]["companions"]:
            session["companion"] = {"id": companion["id"]}
            expected = companion["check_assistance"]
            for skill in state.CHECK_SKILLS:
                with self.subTest(companion=companion["id"], skill=skill):
                    info = self.check(session, skill)
                    self.assertEqual(info["advantage"], "advantage" if skill in expected["skills"] else None)
                    self.assertEqual(info["advantage_reasons"], [expected["reason"]] if skill in expected["skills"] else [])
        session["companion"] = None
        self.assertIsNone(self.check(session, "知覚")["advantage"])

    def test_injury_is_strictly_below_quarter_and_only_physical_skills(self):
        session = self.session()
        session["character"].update(max_hp=20)
        for hp in (4, 5, 6):
            session["character"]["hp"] = hp
            for skill in state.CHECK_SKILLS:
                info = self.check(session, skill)
                expected = hp == 4 and skill in {"運動", "軽業", "隠密"}
                self.assertEqual(info["advantage"], "disadvantage" if expected else None)
                self.assertEqual(info["advantage_reasons"], ["傷が痛む"] if expected else [])

    def test_conditions_cancellation_multiple_sources_and_selected_critical(self):
        session = self.session()
        condition = {"requirements": {"flag": "seal_pattern_known"}, "reason": "封印の知識"}
        spec = {"skill": "隠密", "advantage": [condition, condition]}
        self.assertIsNone(self.check(session, **{"advantage": [condition]})["advantage"])
        session["flags"]["seal_pattern_known"] = True
        for mode, faces, selected, critical in (
                ("advantage", [1, 20], 20, "critical_success"),
                ("disadvantage", [20, 1], 1, "critical_failure")):
            source = {"skill": "隠密", mode: [condition]}
            with patch.object(state.random, "randint", side_effect=faces) as rng:
                roll = state.roll_dice(session, "1d20", 10, roll=source)
            self.assertEqual(rng.call_count, 2)
            self.assertEqual(roll["rolls"], faces)
            self.assertEqual(roll["selected_roll"], selected)
            self.assertEqual(roll["selected_index"], 1)
            self.assertTrue(roll[critical])
            self.assertEqual(roll["total"], selected + 5)
        session["character"].update(hp=1)
        info = state.dice_check_info(session, "1d20", 10, roll=spec)
        self.assertIsNone(info["advantage"])
        self.assertEqual(info["advantage_reasons"], ["封印の知識", "傷が痛む"])
        with patch.object(state.random, "randint", return_value=12) as rng:
            roll = state.roll_dice(session, "1d20", 10, roll=spec)
        rng.assert_called_once()
        self.assertEqual(roll["rolls"], [12])
        session["character"]["hp"] = session["character"]["max_hp"]
        spec["disadvantage"] = [condition]
        self.assertIsNone(state.dice_check_info(session, roll=spec)["advantage"])

    def test_preview_matches_real_endpoint_for_every_authored_skill_check(self):
        for location in self.pack["locations"]:
            for action in checks_v2.walk(location.get("actions", [])):
                if action["id"] not in checks_v2.CHECKS and action["id"] not in {"ask_ian_legend", "invite_robin"}:
                    continue
                session = self.session("thief", location["id"])
                session["character"]["attributes"]["str"] = 12
                session["flags"].update(seal_pattern_known=True, bridge_safe_side_known=True)
                if action.get("visible_after"):
                    session["flags"][action["visible_after"]] = True
                session["choices"] = [action]
                choice = state.player_choices_for_session([action], session)[0]
                with self.subTest(action=action["id"]), patch.object(state.random, "randint", return_value=10), patch.object(app, "save_session"):
                    self.assertIn("check", choice)
                    response = app._run_turn(session, app.TurnRequest(text=action["text"], action_id=action["id"]), allow_narration=False)
                    roll = response["dice_log"][-1]
                    for key, actual in (("modifier", "attr_mod"), ("dc", "dc"), ("skill", "skill"),
                                        ("advantage", "advantage"), ("advantage_reasons", "advantage_reasons")):
                        self.assertEqual(choice["check"][key], roll[actual])

    def test_prepare_alert_consumption_cancellation_and_target_scope(self):
        session = self.session("hero", "dark_forest_loc")
        prepare = self.plan("prepare", "forest_slime")
        prepare["item_id"] = "fallen_branches"
        self.assertEqual(free_actions.adjudicate(session, prepare)["outcome"], "prepared")
        self.assertEqual(session["dice_log"], [])
        sneak = self.plan("sneak", "forest_slime")
        with patch.object(state.random, "randint", side_effect=[1, 2]):
            self.assertEqual(free_actions.adjudicate(session, sneak)["outcome"], "failure")
        previous = session["scene_changes"]["dark_forest_loc"]["forest_slime"]
        self.assertNotIn("prepared", previous)
        self.assertEqual(previous["alertness"], 1)
        self.assertEqual(session["dice_log"][-1]["advantage"], "advantage")
        other = free_actions.sneak_roll_spec({"sneak_dc": 10}, {})
        self.assertNotIn("disadvantage", other)
        free_actions.adjudicate(session, prepare)
        with patch.object(state.random, "randint", return_value=10) as rng:
            self.assertEqual(free_actions.adjudicate(session, sneak)["outcome"], "success")
        rng.assert_called_once()
        self.assertEqual(session["dice_log"][-1]["dc"], 10)
        self.assertIsNone(session["dice_log"][-1]["advantage"])
        current = session["scene_changes"]["dark_forest_loc"]["forest_slime"]
        self.assertNotIn("prepared", current)
        self.assertNotIn("alertness", current)
        self.assertEqual(session["character"]["sp"], 8)

    def test_alert_alone_rolls_twice_and_failed_retry_renews_only_one_penalty(self):
        session = self.session("hero", "dark_forest_loc")
        sneak = self.plan("sneak", "forest_slime")
        for faces in ([2], [20, 2], [19, 2]):
            with patch.object(state.random, "randint", side_effect=faces):
                self.assertEqual(free_actions.adjudicate(session, sneak)["outcome"], "failure")
            self.assertEqual(session["dice_log"][-1]["dc"], 10)
            self.assertEqual(session["scene_changes"]["dark_forest_loc"]["forest_slime"]["alertness"], 1)
        self.assertEqual(session["dice_log"][-1]["advantage_reasons"], ["相手の警戒"])

    def test_observation_conditions_once_and_no_dice_objects(self):
        for (location, target), (skill, dc) in checks_v2.OBSERVATIONS.items():
            for face, branch in ((1, "failure"), (20, "success")):
                session = self.session("hero", location)
                obj = next(o for o in state._current_location_record(session)["objects"] if o["id"] == target)
                obj["observe_reveals"]["roll"]["advantage"] = [{"requirements": {"flag": "seal_pattern_known"}, "reason": "封印の知識"}]
                session["flags"]["seal_pattern_known"] = True
                with self.subTest(target=target, face=face), patch.object(state.random, "randint", return_value=face) as rng:
                    result = free_actions.adjudicate(session, self.plan(target=target))
                    self.assertEqual(result["outcome"], branch)
                    self.assertEqual(result["roll"]["skill"], skill)
                    self.assertEqual(result["roll"]["dc"], dc)
                    self.assertEqual(result["roll"]["advantage"], "advantage")
                    self.assertIn("observe_check", session["scene_changes"][location][target])
                    repeat = free_actions.adjudicate(session, self.plan(target=target))
                    self.assertEqual(repeat["text"], "完了済みです。")
                    self.assertEqual(rng.call_count, 2)
                    self.assertEqual(len(session["dice_log"]), 1)
        session = self.session("hero", "elf_spring")
        with patch.object(state, "roll_dice", side_effect=AssertionError("No roll for dice_type none")):
            self.assertEqual(free_actions.adjudicate(session, self.plan(target="glowing_moss_patch"))["outcome"], "success")

    def test_observation_failure_carries_crucial_metadata_to_the_short_presentation(self):
        (location, target), _ = next(iter(checks_v2.OBSERVATIONS.items()))
        session = self.session("hero", location)
        obj = next(o for o in state._current_location_record(session)["objects"] if o["id"] == target)
        obj["observe_reveals"]["failure_effects"] = [{"game_over": {"reason": "物語はここで終わりました。"}}]
        with patch.object(state.random, "randint", return_value=2):
            result = free_actions.adjudicate(session, self.plan(target=target))
        self.assertEqual(result["outcome"], "failure")
        self.assertTrue(result["roll"]["crucial"])
        self.assertEqual(result["roll"]["crucial_reason"], "game_over")
        self.assertTrue(state.public_session(session)["dice_log"][-1]["crucial"])

    def test_simulation_uses_exact_advantage_probabilities_and_seeded_rng(self):
        session = self.session("hero")
        for mode, expected in (("advantage", .7975), ("disadvantage", .3025)):
            spec = {"skill": "隠密", mode: [{"requirements": {}, "reason": "封印の知識"}]}
            distribution = class_aware.check_distribution(session, "1d20+dex", 10, roll=spec)
            self.assertAlmostEqual(sum(weight for weight, _ in distribution.values()), 1)
            self.assertAlmostEqual(sum(weight for outcome, (weight, _) in distribution.items() if outcome in {"success", "critical_success"}), expected)
            with patch.object(state.random, "randint", side_effect=AssertionError("Use supplied RNG")):
                rolls = [state.roll_dice(session, "1d20", 10, roll=spec, rng=random.Random(40))["rolls"] for _ in range(2)]
            self.assertEqual(rolls[0], rolls[1])

    def test_migration_is_idempotent_and_preserves_checks_outside_assignment(self):
        for filename in checks_v2.PACKS:
            path = checkpoints.DEFAULT_SCENARIO.with_name(filename)
            original = json.loads(path.read_text(encoding="utf-8"))
            migrated = deepcopy(original)
            checks_v2.upgrade(migrated)
            self.assertEqual(original, migrated)
            actions = {a["id"]: a for loc in migrated["locations"] for a in checks_v2.walk(loc.get("actions", []))}
            self.assertEqual(sum(a.get("roll", {}).get("dc") == 999 for a in actions.values()), 3)
            extra = len(checks_e.CHECKS) if migrated["meta"].get("checks_e") else 0
            self.assertEqual(sum(bool(a.get("roll", {}).get("skill")) for a in actions.values()), 31 + extra)
            for identifier, skill, dc in (("ask_ian_legend", "洞察", 8), ("invite_robin", "説得", 10)):
                self.assertEqual(actions[identifier]["roll"], {"dice_type": "1d20+wis", "skill": skill, "dc": dc})
                self.assertEqual(actions[identifier]["risk"], f"{skill}（知恵）判定・DC{dc}")
            output = checkpoints.ROOT / ".tmp-test" / f"checks-v2-{uuid.uuid4().hex}.json"
            self.addCleanup(output.unlink, missing_ok=True)
            output.write_bytes(path.read_bytes())
            checks_v2.fix_pack(output)
            first = output.read_bytes()
            checks_v2.fix_pack(output)
            self.assertEqual(output.read_bytes(), first)
            self.assertFalse(first.startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
