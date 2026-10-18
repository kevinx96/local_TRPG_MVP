from __future__ import annotations

import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from fastapi import HTTPException

from host import app, area_retry, combat, state
from scripts.playtest.explore import offline_runtime


class AreaRetryTests(unittest.TestCase):
    def setUp(self):
        runtime = offline_runtime(29)
        self.root = runtime.__enter__()
        self.addCleanup(runtime.__exit__, None, None, None)
        public = app.api_create_session(app.CreateSessionRequest(character_id="hero"))
        self.session = state.load_session(public["id"])

    def move(self, location):
        state.apply_state_delta(self.session, {"current_location": location}, allow_world_transition=True)

    def defeat(self, location="forest_wolves"):
        self.move(location)
        self.session["combat_start_requested"] = True
        combat.ensure_combat_started(self.session)
        self.session["character"]["hp"] = 1
        self.session["companion"] = None
        for enemy in self.session["combat"]["enemies"]:
            enemy["skills"] = []
            enemy["combat"] = {"basic_attack": {"name": "攻撃", "damage": "999", "accuracy": 100}}
        self.session["character"].setdefault("combat", {})["evade"] = 0
        state.save_session(self.session)
        public = app.api_combat_action(self.session["id"], app.CombatActionRequest(action_type="defend"))
        self.session = state.load_session(self.session["id"])
        return public

    def test_opening_snapshot_and_map_boundary_overwrite(self):
        snapshots = self.session["area_snapshots"]
        self.assertEqual(snapshots["capital"]["state"]["character"]["gold"], 100)
        self.session["character"]["hp"] = 7
        self.move("dark_forest_loc")
        forest = deepcopy(snapshots["forest"])
        self.move("lost_goblin_crossroads")
        self.session["character"]["gold"] = 23
        self.move("goblin_fort")
        self.assertEqual(snapshots["forest"], forest)
        self.assertEqual(snapshots["goblin_fort"]["state"]["character"]["gold"], 23)
        self.move("lost_goblin_crossroads")
        self.assertEqual(snapshots["forest"], forest)
        self.move("castle_town")
        self.session["character"]["hp"] = 9
        self.move("dark_forest_loc")
        self.assertEqual(snapshots["forest"]["state"]["character"]["hp"], 9)
        self.assertNotEqual(snapshots["forest"], forest)

    def test_retry_restores_all_gameplay_state_and_keeps_history(self):
        self.session["character"]["hp"] = 11
        self.session.update(shop_stock={"sarah_shop": {"herb": 2}}, known_item_names=["薬草"],
                            scene_changes={"forest_wolves": {"wolves": {"alertness": 1}}})
        self.move("dark_forest_loc")
        snapshot = deepcopy(self.session["area_snapshots"]["forest"]["state"])
        self.session["character"]["gold"] = 999
        self.session["shop_stock"] = {}
        self.session["known_item_names"].append("紅竜の心臓")
        state.record_state_event(self.session, "item_added", "", {"item": "紅竜の心臓"}, visible=False)
        self.session["flags"]["saved_gald"] = True
        self.session["scene_changes"] = {}
        public = self.defeat()
        self.assertTrue(public["can_retry_area"])
        public = app.api_combat_resolve(self.session["id"])
        before = state.load_session(self.session["id"])
        public = app.api_retry_area(self.session["id"])
        saved = state.load_session(self.session["id"])
        self.assertEqual({k: saved[k] for k in area_retry.GAME_STATE_FIELDS if k in saved}, snapshot)
        self.assertEqual(saved["character"]["hp"], 11)
        self.assertNotIn("紅竜の心臓", state.known_item_names(saved))
        self.assertIsNone(saved["game_over"])
        self.assertIsNone(saved["combat"])
        self.assertEqual(public["retry_count"], 1)
        self.assertFalse(public["can_retry_area"])
        self.assertNotIn("area_snapshots", public)
        self.assertEqual(saved["messages"][:-1], before["messages"])
        self.assertEqual(saved["dice_log"], before["dice_log"])
        self.assertEqual(saved["system_logs"][:-1], before["system_logs"])
        self.assertEqual(saved["messages"][-1]["text"], "運命の糸がほどけ、あなたは再び闇の森の入口に立っていた。")
        self.assertEqual(saved["system_logs"][-1]["text"], "闇の森の入口からやり直しました。")
        traces = [json.loads(line) for path in (self.root / "traces").glob("*.jsonl") for line in path.read_text(encoding="utf-8").splitlines()]
        retry = next(row for row in traces if row["call_type"] == "area_retry")
        self.assertEqual(retry["retry_count"], 1)
        self.assertEqual(retry["death_location"], "forest_wolves")
        self.assertEqual(retry["area_id"], "forest")
        with self.assertRaises(HTTPException) as error:
            app.api_retry_area(self.session["id"])
        self.assertEqual(error.exception.status_code, 409)

    def test_submap_retry_and_repeated_death_counter(self):
        self.move("goblin_fort")
        public = self.defeat("goblin_fort_first_second")
        self.assertTrue(public["can_retry_area"])
        public = app.api_retry_area(self.session["id"])
        self.assertEqual(public["current_location"], "goblin_fort")
        self.session = state.load_session(self.session["id"])
        self.session["combat"] = None
        self.defeat("goblin_fort_first_second")
        public = app.api_retry_area(self.session["id"])
        self.assertEqual(public["retry_count"], 2)

    def test_story_ending_and_scripted_loss_cannot_retry(self):
        self.session["game_over"] = {"ending": "draco_defeated", "reason": "物語はここで終わりました。"}
        state.save_session(self.session)
        self.assertFalse(app.api_get_session(self.session["id"])["can_retry_area"])
        with self.assertRaises(HTTPException):
            app.api_retry_area(self.session["id"])
        self.session["game_over"] = None
        public = self.defeat("xanxus_battle")
        self.assertFalse(public["game_over"])
        self.assertFalse(public["can_retry_area"])
        self.session["game_over"] = {"combat_defeat": True}
        self.assertIsNone(area_retry.retry_snapshot(self.session))

    def test_unmapped_location_uses_latest_arrival(self):
        for area in self.session["scenario_pack"]["maps"]:
            for node in area["nodes"]:
                node["location_ids"] = [i for i in node["location_ids"] if i not in {"forest_wolves", "forest_exit"}]
        self.move("forest_exit")
        self.move("forest_wolves")
        snapshot = self.session["area_snapshots"]["location:forest_wolves"]
        self.session["game_over"] = {"combat_defeat": True}
        self.session["last_combat_result"] = {"outcome": "defeat", "location_id": "forest_wolves"}
        self.assertIs(area_retry.retry_snapshot(self.session), snapshot)
        self.assertEqual(snapshot["state"]["world_state"]["location_id"], "forest_wolves")


if __name__ == "__main__":
    unittest.main()
