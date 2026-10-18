from __future__ import annotations

import shutil
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import app, state
from scripts.balance.checkpoints import DEFAULT_SCENARIO, fresh_session


class PlayerDiceRollTests(unittest.TestCase):
    def setUp(self):
        self.session = fresh_session(state.load_scenario_pack(DEFAULT_SCENARIO), "hero")
        self.session["character"]["attributes"] = {"str": 8, "dex": 5, "int": 6, "wis": 7, "end": 9}

    def choices(self, *choices):
        self.session["choices"] = list(choices)
        return state.public_session(self.session)["choices"]

    def test_public_check_matches_server_roll_for_each_attribute(self):
        for attribute, label in (("str", "筋力"), ("dex", "敏捷"), ("int", "知力"),
                                 ("wis", "知恵"), ("end", "耐久")):
            with self.subTest(attribute=attribute):
                expression = f"1d20+{attribute}"
                check = self.choices(dict(text="周囲を見る", roll=dict(dice_type=expression, dc=14)))[0]["check"]
                self.assertEqual(check, {"dice": "1d20", "attribute": attribute, "attribute_label": label,
                                         "modifier": 0, "dc": 14, "skill": "", "proficiency_bonus": 0,
                                         "advantage": None, "advantage_reasons": []})
                with patch.object(state.random, "randint", return_value=14):
                    roll = state.roll_dice(self.session, expression, 14)
                self.assertEqual(check["modifier"], roll["attr_mod"])
                self.assertEqual(roll["total"], 14 + check["modifier"])
                self.assertEqual(check["dc"], roll["dc"])

    def test_no_attribute_has_zero_modifier_and_preview_does_not_roll(self):
        with patch.object(state.random, "randint", side_effect=AssertionError("Preview must not roll")):
            check = self.choices(dict(text="周囲を見る", roll=dict(dice="1d20", dc=10)))[0]["check"]
        self.assertEqual(check, {"dice": "1d20", "attribute": "", "attribute_label": "", "modifier": 0, "dc": 10,
                                 "skill": "", "proficiency_bonus": 0, "advantage": None, "advantage_reasons": []})
        self.assertEqual(self.session["dice_log"], [])
        with patch.object(state.random, "randint", return_value=12):
            roll = state.roll_dice(self.session, "1d20", 10)
        self.assertEqual(roll["total"], 12 + check["modifier"])

    def test_preview_and_actual_turn_apply_clue_advantage(self):
        for known, expected_dc in ((False, 10), (True, 10)):
            with self.subTest(known=known):
                state.commit_world_position(self.session, location_id="cave_seal")
                self.session["flags"] = {"seal_pattern_known": known}
                self.session["choices"] = state.fallback_choices_for_session(self.session)
                choice = next(c for c in state.public_session(self.session)["choices"] if c.get("id") == "decode_seal")
                check = choice["check"]
                self.assertEqual(check["dc"], expected_dc)
                self.assertEqual(check["advantage"], "advantage" if known else None)
                with patch.object(state.random, "randint", return_value=10), patch.object(app, "save_session"):
                    result = app._run_turn(self.session, app.TurnRequest(text=choice["text"], action_id=choice["id"]),
                                           allow_narration=False)
                self.assertEqual(result["dice_log"][-1]["dc"], check["dc"])
                self.assertEqual(result["dice_log"][-1]["attr_mod"], check["modifier"])
                self.assertEqual(result["dice_log"][-1]["advantage"], check["advantage"])
                self.assertEqual(len(result["dice_log"][-1]["rolls"]), 2 if known else 1)

    def test_current_attributes_and_aliases_share_the_roll_calculation(self):
        for expression, expected in (("1d20+agi", 0), ("1d20-dex", 0), ("1d20+3", 3), ("1d20-2", -2)):
            with self.subTest(expression=expression):
                check = self.choices(dict(text="周囲を見る", roll=dict(dice=expression, dc=10)))[0]["check"]
                with patch.object(state.random, "randint", return_value=10):
                    roll = state.roll_dice(self.session, expression, 10)
                self.assertEqual(check["modifier"], expected)
                self.assertEqual(roll["total"], 10 + expected)
        self.session["character"]["attributes"]["dex"] = 11
        check = self.choices(dict(text="周囲を見る", roll=dict(dice="1d20+dex", dc=10)))[0]["check"]
        self.assertEqual(check["modifier"], 0)

    def test_presentation_receives_actual_outcome_without_changing_critical_rules(self):
        self.session["character"]["attributes"]["dex"] = 20
        for critical_enabled, expected in ((False, "success"), (True, "critical_failure")):
            with self.subTest(critical_enabled=critical_enabled):
                with patch.object(state.random, "randint", return_value=1):
                    roll = state.roll_dice(self.session, "1d20+dex", 5)
                action = dict(id="observe", text="周囲を見る", critical_enabled=critical_enabled)
                result = state.apply_action_result(self.session, action, roll)
                self.assertTrue(roll["success"])
                self.assertEqual(result["outcome"], expected)
                self.assertEqual(state.public_session(self.session)["dice_log"][-1]["outcome"], expected)
                self.assertEqual(roll["critical_enabled"], critical_enabled)

    def test_no_preview_for_unknown_impossible_or_non_roll_choices(self):
        result = self.choices(
            dict(text="周囲を見る", roll=dict(dice="1d20", dc=999)),
            dict(text="周囲を見る", roll=dict(dice="1d20", dc=100)),
            dict(text="周囲を見る", roll=dict(dice="none", dc=0)),
            dict(text="周囲を見る", risk="1d20判定（DC10）"),
            dict(text="？？？", roll=dict(dice="1d20+dex", dc=14)),
            dict(text="虹晶の欠片", requirements={"has_item": "虹晶の欠片"}, roll=dict(dice="1d20+dex", dc=14)),
        )
        self.assertTrue(all("check" not in choice for choice in result))
        self.assertEqual(result[-1], {"text": "？？？", "visibility": "unknown", "enabled": False,
                                      "disabled_reason": "まだ知らない何かが必要なようだ。"})

    def test_nested_checks_do_not_mutate_internal_actions_or_leak_unknown_data(self):
        source = dict(text="周囲を見る", children=[
            dict(text="周囲を見る", roll=dict(dice_type="1d20+dex", dc=14)),
            dict(text="虹晶の欠片", requirements={"flag": "heard_seal_lore"}, roll=dict(dice="1d20", dc=14)),
        ])
        original = deepcopy(source)
        choices = self.choices(source)
        self.assertEqual(choices[0]["children"][0]["check"]["modifier"], 0)
        self.assertNotIn("check", choices[0]["children"][1])
        self.assertEqual(source, original)
        self.assertEqual(self.session["choices"], [original])

    def test_invalid_roll_does_not_break_public_session(self):
        for expression in ("none", "1d20+missing"):
            with self.subTest(expression=expression):
                choice = self.choices(dict(text="周囲を見る", roll=dict(dice=expression, dc=10)))[0]
                self.assertNotIn("check", choice)
                with self.assertRaises(ValueError):
                    state.roll_dice(self.session, expression, 10)

    def test_public_crucial_check_is_engine_derived_and_redacts_failure_details(self):
        for effects, reason in (([{"start_combat": True}], "combat"),
                                ([{"game_over": {"ending": "defied_xanxus"}}, {"start_combat": True}], "game_over")):
            with self.subTest(reason=reason):
                source = dict(text="周囲を見る", roll=dict(dice="1d20", dc=10), failure_effects=effects)
                self.session["choices"] = [source]
                state.ensure_world_state(self.session)
                original = deepcopy(self.session)
                with patch.object(state.random, "randint", side_effect=AssertionError("Preview must not roll")):
                    public = state.public_session(self.session)["choices"][0]
                self.assertTrue(public["check"]["crucial"])
                self.assertEqual(public["check"]["crucial_reason"], reason)
                self.assertNotIn("failure_effects", public)
                self.assertNotIn("defied_xanxus", str(public))
                self.assertEqual(self.session, original)

    def test_crucial_risk_uses_only_the_active_failure_branch(self):
        source = dict(text="周囲を見る", roll=dict(dice="1d20", dc=10), failure_effects=[
            {"branch": {"requirements": {"gold_lte": 30}, "then": [{"start_combat": True}],
                        "else": [{"set_flag": "seal_pattern_known"}]}}])
        for gold, expected in ((30, True), (31, False)):
            with self.subTest(gold=gold):
                self.session["character"]["gold"] = gold
                check = self.choices(source)[0]["check"]
                self.assertEqual(check.get("crucial", False), expected)
        for key in ("success_effects", "critical_failure_effects"):
            source = dict(text="周囲を見る", roll=dict(dice="1d20", dc=10), **{key: [{"start_combat": True}]})
            self.assertNotIn("crucial", self.choices(source)[0]["check"])

    def test_failure_destination_reuses_encounter_rules_without_mutating_session(self):
        session = {"world_state": {"scene_id": "forest", "location_id": "trail"},
                   "visited_locations": ["trail"], "flags": {}, "character": {},
                   "scenario_pack": {"scenes": [{"id": "forest", "location_ids": ["trail", "ambush", "safe"]}],
                                     "locations": [{"id": "trail", "scene_id": "forest"},
                                                   {"id": "ambush", "scene_id": "forest", "enemy_ids": ["goblin"]},
                                                   {"id": "safe", "scene_id": "forest"}],
                                     "enemies": [{"id": "goblin"}]}}
        for key in ("current_location", "next_location"):
            for destination, expected in (("ambush", True), ("safe", False), ("missing", False)):
                with self.subTest(key=key, destination=destination):
                    original = deepcopy(session)
                    risk = state.action_failure_risk({"failure_effects": [{key: destination}]}, session)
                    self.assertEqual(risk.get("crucial", False), expected)
                    self.assertEqual(session, original)
        action = {"failure_effects": [{"next_location": "ambush"}]}
        session["flags"]["combat_defeated:ambush:goblin"] = True
        self.assertEqual(state.action_failure_risk(action, session), {})
        session["flags"].clear()
        encounter = session["scenario_pack"]["locations"][1].setdefault("combat", {})
        encounter["auto_start"] = False
        self.assertEqual(state.action_failure_risk(action, session), {})
        encounter.update(auto_start=True, enemy_variants=[{"requirements": {"flag": "seal_pattern_known"}, "enemy_ids": []}])
        action["effects"] = [{"set_flag": "seal_pattern_known"}]
        self.assertEqual(state.action_failure_risk(action, session), {})
        self.assertEqual(session["flags"], {})

    def test_crucial_preview_survives_real_failure_into_combat(self):
        for natural, outcome in ((7, "failure"), (1, "critical_failure"), (20, "critical_success")):
            with self.subTest(natural=natural):
                session = deepcopy(self.session)
                accepted, reason = state.commit_world_position(session, location_id="goblin_fort")
                self.assertTrue(accepted, reason)
                session["choices"] = state.fallback_choices_for_session(session)
                choice = next(c for c in state.public_session(session)["choices"] if c.get("id") == "fort_first_bypass")
                self.assertTrue(choice["check"]["crucial"])
                with patch.object(state.random, "randint", return_value=natural), patch.object(app, "save_session"):
                    result = app._run_turn(session, app.TurnRequest(text=choice["text"], action_id=choice["id"]),
                                           allow_narration=False)
                roll = result["dice_log"][-1]
                self.assertTrue(roll["crucial"])
                self.assertEqual(roll["crucial_reason"], "combat")
                self.assertEqual(roll["outcome"], outcome)
                self.assertEqual(result["in_combat"], natural != 20)

    def test_crucial_ending_metadata_is_recorded_before_state_changes(self):
        action = dict(id="observe", text="周囲を見る", critical_enabled=False,
                      roll={"dice": "1d20", "dc": 10}, failure_effects=[
                          {"branch": {"requirements": {"not_flag": "seal_pattern_known"},
                                      "then": [{"game_over": {"reason": "物語はここで終わりました。"}},
                                               {"set_flag": "seal_pattern_known"}]}}])
        roll = state.roll_dice(self.session, "1d20", 10, client_rolls=[7], critical_enabled=False)
        result = state.apply_action_result(self.session, action, roll)
        self.assertTrue(roll["crucial"])
        self.assertEqual(roll["crucial_reason"], "game_over")
        self.assertEqual(result["outcome"], "failure")
        self.assertTrue(state.public_session(self.session)["dice_log"][-1]["crucial"])
        self.assertTrue(self.session["game_over"])


class PlayerDiceClientTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is required for client behavior tests")
    def test_client_dice_flow(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(["node", "tests/player_dice_roll.test.js"], cwd=root,
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
