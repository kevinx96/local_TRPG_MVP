from __future__ import annotations

import unittest
from copy import deepcopy

from host import state
from host.maps import movement_action, public_maps
from host.scenario_context import select_hybrid_prepared_turn
from scripts.balance import checkpoints
from scripts.scenario.castle_town import SUPPLIES_TEXT, TOWN_DESCRIPTION, upgrade


class CastleTownTests(unittest.TestCase):
    def sessions(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            yield checkpoints.fresh_session(state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(filename)), "hero")

    def test_opening_and_supplies_are_engine_owned_and_once(self):
        for session in self.sessions():
            actor = session["character"]
            herbs = sum(i.get("quantity", 1) for i in actor["inventory"] if i["name"] == "薬草")
            session["needs_opening"] = True
            payload = {"state_delta": {"gold_change": 50, "inventory_add": ["薬草"]}}
            state.apply_gm_payload(session, "", payload)
            state.apply_gm_payload(session, "", payload)
            self.assertEqual(actor["gold"], 100)
            self.assertEqual(sum(i.get("quantity", 1) for i in actor["inventory"] if i["name"] == "薬草"), herbs + 1)
            session["needs_opening"] = False
            result = checkpoints.replay_step(session, "check_supplies")
            self.assertNotIn("gold_change", result["delta"])
            self.assertEqual(actor["gold"], 100)
            self.assertEqual(next(i["quantity"] for i in actor["inventory"] if i["name"] == "聖水"), 2)
            self.assertEqual(select_hybrid_prepared_turn(session)["draft"]["gm_text"], SUPPLIES_TEXT)
            with self.assertRaises(ValueError):
                checkpoints.replay_step(session, "check_supplies")

    def test_town_connections_and_gate_departure_without_roll(self):
        for session in self.sessions():
            self.assertIsNone(state.resolve_action(session, action_id="go_dark_forest"))
            checkpoints.replay_step(session, "go_castle_town")
            self.assertEqual(state.current_scene_id(session), "throne_room")
            self.assertEqual(state._current_location_record(session)["description"], TOWN_DESCRIPTION)
            self.assertEqual(public_maps(session)["current_map_id"], "capital")
            for location in ("forge", "inn", "magic_shop", "item_shop", "alley"):
                state.apply_action_result(session, movement_action(session, location), {})
                self.assertEqual(state.current_location_id(session), location)
                if location == "forge":
                    self.assertIsNone(state.resolve_action(session, action_id="go_dark_forest"))
                action = movement_action(session, "C2")
                self.assertEqual((action["text"], action["preview"]), ("城下町に戻る", "大通りへ戻る"))
                state.apply_action_result(session, action, {})
                self.assertEqual(state.current_location_id(session), "castle_town")
            action = movement_action(session, "gate")
            self.assertNotIn("roll", action)
            self.assertEqual(action["risk"], "判定不要")
            state.apply_action_result(session, action, {})
            self.assertEqual(state.current_location_id(session), "dark_forest_loc")

    def test_facilities_and_alley_variants_keep_chapter_five_returns(self):
        for session in self.sessions():
            for returned in (False, True):
                session["flags"]["returned_to_capital"] = returned
                for location, action in [(i, "return_castle_from_" + i) for i in ("forge", "inn", "magic_shop", "item_shop", "alley")] + [
                        ("alley_night", "leave_night_alley"), ("alley_after", "return_castle_after_curse")]:
                    session["world_state"] = {"scene_id": "throne_room", "location_id": location}
                    if not returned:
                        self.assertEqual(movement_action(session, "C2")["id"], action)
                    checkpoints.replay_step(session, action)
                    self.assertEqual(state.current_location_id(session), "festival_town" if returned else "castle_town")

    def test_seal_lore_hidden_until_heard_or_visited(self):
        for session in self.sessions():
            state.commit_world_position(session, location_id="magic_shop")
            self.assertNotIn("泉の封印", str(state.public_session(session)["choices"]))
            for flag in ("mina_missing_heard", "seen_cave_seal"):
                session["flags"] = {flag: True}
                self.assertTrue(any(c.get("action_id") == "ask_seal_lore" for c in state.public_session(session)["choices"]))
            session["flags"] = {}
            state.apply_state_delta(session, {"current_location": "cave_seal"}, allow_world_transition=True)
            self.assertTrue(session["flags"]["seen_cave_seal"])

    def test_pack_migration_idempotent_and_shared_actions_match(self):
        sessions = list(self.sessions())
        for session in sessions:
            raw = deepcopy(session["scenario_pack"])
            upgrade(raw)
            expected = deepcopy(raw)
            upgrade(raw)
            self.assertEqual(raw, expected)
        for location in (loc["id"] for loc in sessions[0]["scenario_pack"]["locations"]
                         if loc["scene_id"] in {"throne_room", "dark_forest"}):
            records = [next(l for l in s["scenario_pack"]["locations"] if l["id"] == location) for s in sessions]
            for field in ("actions", "entry_effects", "opening_effects", "npc_requirements"):
                self.assertEqual(records[0].get(field), records[1].get(field), (location, field))


if __name__ == "__main__":
    unittest.main()
