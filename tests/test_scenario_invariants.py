from __future__ import annotations

import json
import unittest
from pathlib import Path
from copy import deepcopy

from host import state
from scripts.balance.checkpoints import fresh_session
from scripts.scenario.portraits_risk_fx import upgrade

ROOT = Path(__file__).resolve().parents[1]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
# A parent with children only expands a menu, so any effect on it would silently never run.
EFFECT_KEYS = ("effects", "success_effects", "failure_effects", "roll", "open_shop", "start_combat")


def _walk(actions, location_id):
    for action in actions:
        yield location_id, action
        yield from _walk(action.get("children") or [], location_id)


class ScenarioInvariantTests(unittest.TestCase):
    def test_portrait_inheritance_and_encounter_lists(self):
        for filename in PACKS:
            pack = json.loads((ROOT / "host/prompt/processed" / filename).read_text(encoding="utf-8"))
            for location in pack["locations"]:
                encounter = location.get("combat", {})
                if "enemy_ids" in encounter:
                    self.assertEqual(location.get("enemy_ids"), encounter["enemy_ids"], location["id"])
                for _, action in _walk(location.get("actions", []), location["id"]):
                    if action.get("portrait_image"):
                        for child in action.get("children", []):
                            self.assertIn(child.get("portrait_image"), (None, action["portrait_image"]), child["id"])
            migrated = deepcopy(pack)
            upgrade(migrated)
            self.assertEqual(migrated, pack)

    def test_unknown_destination_risk_and_action_risk(self):
        cases = [
            ("goblin_fort_second_choice", "explore_fort_right", "goblin_fort_second_right", "不明", "危険（戦闘）"),
            ("goblin_fort_second_choice", "explore_fort_left", "goblin_fort_second_left", "不明", "危険（戦闘）"),
            ("cave_fork", "cave_right", "cave_hot_spring", "不明", "判定不要"),
            ("goblin_fort", "fort_first_bypass", "goblin_fort_first_second", "1d20+dex判定（DC13）", "1d20+dex判定（DC13）"),
            ("goblin_fort", "fight_fort_first_guard", "goblin_fort", "危険（戦闘）", "危険（戦闘）"),
            ("goblin_fort_third_gate", "admit_no_password", "goblin_fort_third_guards", "危険（戦闘）", "危険（戦闘）"),
            ("castle_town", "go_inn", "inn", "判定不要", "判定不要"),
            ("festival_town", "go_inn", "inn", "不明", "判定不要"),
            ("elf_spring", "rest_at_elf_spring", "slime_ambush_one", "休息中に襲われる恐れあり", "休息中に襲われる恐れあり"),
        ]
        for filename in PACKS:
            pack = state.load_scenario_pack(ROOT / "host/prompt/processed" / filename)
            for location_id, action_id, destination, unknown, known in cases:
                session = fresh_session(deepcopy(pack), "hero")
                session["world_state"] = {"location_id": location_id}
                session["flags"]["returned_to_capital"] = location_id == "festival_town"
                action = next(a for loc, a in _walk(next(l for l in pack["locations"] if l["id"] == location_id)["actions"], location_id) if a["id"] == action_id)
                with self.subTest(pack=filename, location=location_id, action=action_id):
                    self.assertEqual(state.player_choices_for_session([action], session)[0]["risk"], unknown)
                    session["visited_locations"] = [destination]
                    self.assertEqual(state.player_choices_for_session([action], session)[0]["risk"], known)
                    self.assertNotIn("effects", state.player_choices_for_session([action], session)[0])
                    if action.get("risk_source") == "destination" and known == "危険（戦闘）":
                        encounter = next(l for l in pack["locations"] if l["id"] == destination)["combat"]
                        session["flags"].update({f"combat_defeated:{destination}:{enemy}": True for enemy in encounter["enemy_ids"]})
                        self.assertEqual(state.player_choices_for_session([action], session)[0]["risk"], "判定不要")

    def test_portrait_is_available_on_public_choices(self):
        for filename in PACKS:
            session = fresh_session(state.load_scenario_pack(ROOT / "host/prompt/processed" / filename), "hero")
            session["world_state"] = {"location_id": "inn"}
            public = state.public_session(session)
            ian = next(c for c in public["choices"] if c["action_id"] == "ask_ian")
            self.assertEqual(ian["portrait_image"], "/static/images/npc_ian.png")
            self.assertEqual({c["portrait_image"] for c in ian["children"]}, {ian["portrait_image"]})
    def test_menu_parents_carry_no_effects(self):
        for filename in PACKS:
            pack = json.loads((ROOT / "host/prompt/processed" / filename).read_text(encoding="utf-8"))
            for location in pack["locations"]:
                for location_id, action in _walk(location.get("actions") or [], location["id"]):
                    if action.get("children"):
                        with self.subTest(pack=filename, location=location_id, action=action["id"]):
                            self.assertEqual([key for key in EFFECT_KEYS if action.get(key)], [])


    def test_risk_labels_match_mechanics(self):
        from scripts.scenario.risk_labels import _walk as walk_actions, expected_risk
        for filename in PACKS:
            pack = json.loads((ROOT / "host/prompt/processed" / filename).read_text(encoding="utf-8"))
            items = {item["id"]: item["name"] for item in pack.get("items", []) if item.get("id")}
            for location in pack["locations"]:
                for action in walk_actions(location.get("actions") or []):
                    if action.get("children"):
                        continue
                    label = expected_risk(action, location, items, {l["id"]: l for l in pack["locations"]})
                    if label:
                        with self.subTest(pack=filename, location=location["id"], action=action["id"]):
                            self.assertEqual(action.get("risk"), label)


if __name__ == "__main__":
    unittest.main()
