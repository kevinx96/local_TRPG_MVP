from __future__ import annotations

import unittest
from copy import deepcopy

from host import app, state
from host.scenario_context import fallback_choices_for_session, select_scenario_context
from host.maps import movement_action, public_maps
from scripts.balance import checkpoints
from scripts.playtest.audit import narration_gaps
from scripts.playtest.explore import CHARACTERS, SEEDS, explore, offline_runtime
from scripts.scenario.playtest_fixes import ENTRIES, upgrade


PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
PRIVATE_KEYS = {"effects", "success_effects", "failure_effects", "roll_bonuses", "result_text", "result_texts"}


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


class PlaytestFixTests(unittest.TestCase):
    def sessions(self, location="castle"):
        for filename in PACKS:
            session = checkpoints.fresh_session(state.load_scenario_pack(state.DEFAULT_SCENARIO.with_name(filename)), "hero")
            session["world_state"] = {"location_id": location}
            state.ensure_world_state(session)
            yield session

    def choices(self, session):
        session["choices"] = fallback_choices_for_session(session)
        return {c.get("action_id"): c for c in objects(state.public_session(session)["choices"]) if c.get("action_id")}

    def test_cleared_fort_cannot_be_reentered(self):
        for session in self.sessions("lost_goblin_crossroads"):
            session["flags"].update(cleared_goblin_fort=True, defeated_goblin_king=True,
                                    lost_goblin_quest=True, recruited_robin=True)
            self.assertNotIn("enter_goblin_fort", self.choices(session))
            self.assertIsNone(state.resolve_action(session, action_id="enter_goblin_fort"))
            session["world_state"] = {"location_id": "inn"}
            self.assertNotIn("accept_robin_goblin_quest", self.choices(session))

    def test_resolved_or_dead_goblin_no_longer_offers_quest(self):
        for session in self.sessions("lost_goblin_crossroads"):
            for flag in ("resolved_lost_goblin_box", "combat_defeated:lost_goblin_crossroads:goblin"):
                session["flags"] = {flag: True}
                choices = self.choices(session)
                self.assertNotIn("help_lost_goblin", choices)
                self.assertNotIn("ignore_lost_goblin", choices)
                self.assertIn("crossroads_forward", choices)

    def test_dead_goblin_box_has_one_noncombat_loot_action(self):
        for session in self.sessions("goblin_fort_chest_choice"):
            session["flags"]["combat_defeated:lost_goblin_crossroads:goblin"] = True
            choices = self.choices(session)
            self.assertEqual([c["text"] for c in choices.values()], ["箱を持ち帰る"])
            action = state.resolve_action(session, action_id=next(iter(choices)))
            result = state.apply_action_result(session, action, {})
            self.assertTrue(result["result_text"].startswith("主を失った箱は"))
            self.assertFalse(result["state_delta"].get("start_combat"))
            self.assertTrue(session["flags"]["resolved_lost_goblin_box"])
            self.assertTrue(any(i["name"] == "縮小の銃" for i in session["character"]["inventory"]))

    def test_public_session_never_exposes_resolution_fields(self):
        for session in self.sessions():
            checkpoints.replay_step(session, "check_supplies")
            session["last_free_action"] = {"nested": {key: "secret" for key in PRIVATE_KEYS}}
            for obj in objects(state.public_session(session)):
                self.assertFalse(PRIVATE_KEYS.intersection(obj), PRIVATE_KEYS.intersection(obj))
            self.assertIn("result_text", session["last_action_result"])

    def test_dead_goblin_is_absent_from_portraits_and_current_context(self):
        for session in self.sessions("lost_goblin_crossroads"):
            session["flags"]["resolved_lost_goblin_box"] = True
            self.assertFalse(state.public_session(session)["location_npc_portraits"])
            self.assertFalse(state.public_session(session)["location_portrait_image"])
            self.assertNotIn("迷子", select_scenario_context(session)["current_location"]["description"])
            self.assertNotIn("lost_goblin", [npc["id"] for npc in select_scenario_context(session)["matched"]["npcs"]])

    def test_facility_entries_and_conditional_companion_departure(self):
        with offline_runtime(29):
            for location, text in ENTRIES.items():
                public = app.api_create_session(app.CreateSessionRequest(character_id="hero"))
                session = state.load_session(public["id"])
                state.apply_state_delta(session, {"current_location": "castle_town"}, allow_world_transition=True)
                session["choices"] = fallback_choices_for_session(session)
                state.save_session(session)
                result = app.api_turn(session["id"], app.TurnRequest(text="入る", action_id="go_" + location))
                self.assertEqual(result["messages"][-1]["text"], text)
        for session in self.sessions("forest_exit"):
            for companion in (None, {"id": "robin"}, {"id": "blue_robed_mage"}):
                case = deepcopy(session)
                case["companion"] = companion
                action = state.resolve_action(case, action_id="leave_forest_for_village")
                result = state.apply_action_result(case, action, {})
                disappears = companion is not None and companion["id"] == "blue_robed_mage"
                self.assertEqual("青いローブの魔法使いの姿が消えていた" in result["result_text"], disappears)
                self.assertEqual(case["companion"], None if disappears else companion)

    def test_no_stationary_narration_gaps_beyond_documented_exceptions(self):
        shops = {("forge", "open_forge_shop"), ("village", "open_village_shop"), ("village", "open_gald_shop"),
                 ("magic_shop", "open_magic_shop"), ("item_shop", "open_sarah_shop"), ("festival_town", "open_gald_capital_shop")}
        impossible = {("xanxus_confrontation", action, "success")
                      for action in ("bluff_xanxus", "ambush_xanxus", "flee_from_xanxus")}
        for filename, session in zip(PACKS, self.sessions()):
            gaps = narration_gaps(session["scenario_pack"])
            self.assertEqual({(g["location"], g["action"]) for g in gaps if g["reason"] == "open_shop"}, shops)
            missing = {(g["location"], g["action"], g["outcome"]) for g in gaps if g["reason"] == "missing"}
            self.assertEqual(missing, impossible)

    def test_town_return_routes_and_map_visibility(self):
        for session in self.sessions("castle_town"):
            self.assertNotIn("return_forest_exit", self.choices(session))
            state.apply_state_delta(session, {"current_location": "forest_exit"}, allow_world_transition=True)
            checkpoints.replay_step(session, "return_inn_after_forest")
            self.assertEqual(state.current_location_id(session), "castle_town")
            self.assertIn("return_forest_exit", self.choices(session))
            capital = next(m for m in public_maps(session)["maps"] if m["id"] == "capital")
            self.assertEqual(next(n for n in capital["nodes"] if n["id"] == "forest_exit")["label"], "森の出口")
            state.apply_action_result(session, movement_action(session, "forest_exit"), {})
            self.assertEqual(state.current_location_id(session), "forest_exit")
            self.assertEqual(public_maps(session)["current_map_id"], "forest")
            state.apply_state_delta(session, {"current_location": "village"}, allow_world_transition=True)
            checkpoints.replay_step(session, "return_castle_from_village")
            self.assertEqual(state.current_location_id(session), "castle_town")
            self.assertIn("return_village", self.choices(session))
            checkpoints.replay_step(session, "return_village")
            self.assertEqual(state.current_location_id(session), "village")

    def test_data_migration_is_idempotent_and_previews_do_not_repeat_titles(self):
        for session in self.sessions():
            pack = deepcopy(session["scenario_pack"])
            upgrade(pack)
            once = deepcopy(pack)
            upgrade(pack)
            self.assertEqual(pack, once)
            self.assertNotIn("forest_departure_failed", str(pack))
            for obj in objects(pack):
                if obj.get("text"):
                    self.assertNotEqual(obj.get("preview"), obj["text"])

    def test_fixed_seed_app_playthroughs(self):
        for character in CHARACTERS:
            for seed in SEEDS:
                with self.subTest(character=character, seed=seed):
                    result = explore(character, seed, 150)
                    self.assertEqual(result["failures"], [])
                    self.assertLessEqual(result["retry_count"], 1)


if __name__ == "__main__":
    unittest.main()
