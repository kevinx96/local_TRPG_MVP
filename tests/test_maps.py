from __future__ import annotations

import unittest
from copy import deepcopy
from unittest.mock import patch

from fastapi import HTTPException

from host import app, state
from host.maps import movement_action, public_maps
from scripts.balance.checkpoints import DEFAULT_SCENARIO, fresh_session


class MapTests(unittest.TestCase):
    def setUp(self):
        self.session = fresh_session(state.load_scenario_pack(DEFAULT_SCENARIO), "hero")
        self.session["scenario_pack"]["maps"] = [dict(id="town", title="王城", nodes=[
            dict(id="a", label="王城", kind="start", x=10, y=20, location_ids=["castle"]),
            dict(id="b", label="城下町", kind="event", x=40, y=20, location_ids=["castle_town"]),
            dict(id="c", label="鍛冶屋", kind="event", x=70, y=20, location_ids=["forge"], locked_until="unlocked"),
        ], edges=[dict(**{"from": "a", "to": "b"}, action_id="go_castle_town"), {"from": "b", "to": "c"}]),
            dict(id="sub", title="路地裏", parent="town", nodes=[
                dict(id="s", label="路地裏", kind="event", x=50, y=50, location_ids=["alley"])], edges=[])]

    def test_visibility_history_and_lock(self):
        data = public_maps(self.session)
        self.assertEqual([n["visibility"] for n in data["maps"][0]["nodes"]], ["visited", "adjacent-unknown", "hidden"])
        self.assertNotIn("label", data["maps"][0]["nodes"][1])
        state.commit_world_position(self.session, location_id="forge")
        self.assertEqual(public_maps(self.session)["maps"][0]["nodes"][2]["visibility"], "locked")
        self.session["flags"]["unlocked"] = True
        self.assertEqual(public_maps(self.session)["maps"][0]["nodes"][2]["visibility"], "visited")
        self.assertEqual(public_maps(self.session)["maps"][0]["nodes"][2]["kind"], "branch")

    def test_move_uses_turn_pipeline(self):
        with patch.object(app, "load_session", return_value=self.session), patch.object(app, "_run_turn", return_value={}) as turn:
            app.api_map_move("balance", app.MapMoveRequest(node_id="b"))
        self.assertEqual(turn.call_args.args[1].action_id, "go_castle_town")
        action = movement_action(self.session, "b")
        state.apply_action_result(self.session, action, {})
        self.assertEqual(state.current_location_id(self.session), "castle_town")
        self.assertIn("castle_town", self.session["visited_locations"])

    def test_failures_do_not_move(self):
        for update, node in (({}, "c"), ({"combat": {"status": "active"}}, "b"), ({"game_over": {"reason": "終了"}}, "b")):
            session = deepcopy(self.session)
            session.update(update)
            with self.assertRaises(ValueError):
                movement_action(session, node)
            self.assertEqual(state.current_location_id(session), "castle")
        state.commit_world_position(self.session, location_id="inn")
        with self.assertRaises(ValueError):
            movement_action(self.session, "c")
        state.commit_world_position(self.session, location_id="castle")
        edge = self.session["scenario_pack"]["maps"][0]["edges"][0]
        edge["action_id"] = "missing"
        with self.assertRaises(ValueError):
            movement_action(self.session, "b")
        edge["action_id"] = "go_castle_town"
        with patch.object(app, "load_session", return_value=self.session), patch.object(state, "action_requirement_status", return_value=(False, "条件を満たしていません")):
            with self.assertRaises(HTTPException) as error:
                app.api_map_move("balance", app.MapMoveRequest(node_id="b"))
        self.assertEqual(error.exception.status_code, 409)

    def test_submap_and_old_save(self):
        self.session["location_history"] = ["inn", {"location_id": "forge"}]
        state.ensure_world_state(self.session)
        self.assertEqual(set(self.session["visited_locations"]), {"castle", "inn", "forge"})
        state.commit_world_position(self.session, location_id="alley")
        self.assertEqual(public_maps(self.session)["current_map_id"], "sub")
        self.assertEqual(public_maps(self.session)["maps"][1]["parent"], "town")
        state.commit_world_position(self.session, location_id="castle")
        self.assertEqual(public_maps(self.session)["current_map_id"], "town")

    def test_unopened_shortcut_does_not_reveal_exit(self):
        s = fresh_session(state.load_scenario_pack(DEFAULT_SCENARIO), "hero")
        state.commit_world_position(s, location_id="lost_goblin_crossroads")
        forest = next(m for m in public_maps(s)["maps"] if m["id"] == "forest")
        self.assertEqual(next(n for n in forest["nodes"] if n["id"] == "F5")["visibility"], "hidden")
        s["flags"]["resolved_lost_goblin_box"] = True
        forest = next(m for m in public_maps(s)["maps"] if m["id"] == "forest")
        self.assertEqual(next(n for n in forest["nodes"] if n["id"] == "F5")["visibility"], "adjacent-unknown")
        with self.assertRaises(ValueError):
            movement_action(s, "F5")
        s["flags"]["passed_forest_wolves"] = True
        self.assertEqual(movement_action(s, "F5")["id"], "fort_shortcut")
