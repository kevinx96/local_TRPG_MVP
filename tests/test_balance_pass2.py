from __future__ import annotations

import json
import unittest
from copy import deepcopy

from host import combat, state
from host.scenario_context import select_hybrid_prepared_turn
from scripts.balance import checkpoints, sim


class BalancePass2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)

    def test_level_skills_unlock_once_including_skipped_levels(self):
        for cid in ("hero", "cleric", "mage", "thief"):
            for skip in (False, True):
                session = checkpoints.fresh_session(deepcopy(self.pack), cid)
                actor = session["character"]
                initial = len(actor["skills"])
                self.assertFalse(any(s.get("unlock_level") for s in actor["skills"]))
                flags = ["nest_event_seen"] if skip else ["defeated_slime_king", "cleared_goblin_fort", "reached_village", "entered_dragon_valley", "nest_event_seen"]
                for flag in flags:
                    state.apply_state_delta(session, {"flags_set": [flag]})
                    expected = sum(1 for s in next(c for c in self.pack["characters"] if c["id"] == cid)["level_skills"]
                                   if s["unlock_level"] <= actor["level"] and not s.get("replaces"))
                    self.assertEqual(len(actor["skills"]), initial + expected)
                before = deepcopy(actor)
                state.apply_state_delta(session, {"flags_set": flags})
                self.assertEqual(actor, before)
                self.assertEqual(actor["level"], 5)
                restored = json.loads(json.dumps(session))
                state.apply_state_delta(restored, {})
                self.assertEqual(restored["character"]["skills"], actor["skills"])

    def test_approved_skill_names_and_roles_match_both_packs(self):
        expected = {"hero": ["渾身斬り・改", "不屈の構え"], "cleric": ["聖なる裁き", "大いなる癒し"],
                    "mage": ["火球・改", "氷の矢・改"], "thief": ["影隠れ・改", "急所突き・改"]}
        hybrid = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name("dragon_rpg_hybrid.json"))
        for cid, names in expected.items():
            skills = next(c for c in self.pack["characters"] if c["id"] == cid)["level_skills"]
            self.assertEqual(skills, next(c for c in hybrid["characters"] if c["id"] == cid)["level_skills"])
            self.assertEqual([s["name"] for s in skills], names)
            self.assertEqual([s["unlock_level"] for s in skills], [2 if cid == "mage" else 3, 5])
            if cid == "mage":
                self.assertTrue(skills[0]["all_targets"])
                self.assertEqual(skills[0]["element"], "fire")
            if cid == "cleric":
                self.assertEqual(skills[0]["element"], "holy")
                self.assertEqual(skills[1]["kind"], "heal")
            if cid in {"hero", "thief"}:
                guard = skills[1 if cid == "hero" else 0]
                self.assertEqual(guard["guard_multiplier"], .25)
                self.assertTrue(guard["survive_at_one"])
                self.assertEqual(guard["cost"], 2)

    def test_supplies_once_for_every_class_and_pack(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(filename))
            for cid in ("hero", "cleric", "mage", "thief"):
                session = checkpoints.fresh_session(deepcopy(pack), cid)
                action = state.resolve_action(session, action_id="check_supplies")
                gold = session["character"]["gold"]
                state.apply_action_result(session, action, {})
                self.assertIn("聖水", select_hybrid_prepared_turn(session)["draft"]["gm_text"])
                holy = next(i for i in session["character"]["inventory"] if i.get("id") == "holy_water")
                self.assertEqual(holy["quantity"], 2)
                self.assertEqual(holy["combat"]["element"], "holy")
                self.assertEqual(holy["combat"]["damage"], "36")
                self.assertEqual(session["character"]["gold"], gold)
                self.assertFalse(state.action_requirement_status(action, session)[0])
                state.apply_action_result(session, action, {})
                self.assertEqual(next(i for i in session["character"]["inventory"] if i.get("id") == "holy_water")["quantity"], 2)
                state.apply_state_delta(session, {"inventory_remove": [{"name": "聖水", "quantity": 2}]})
                state.apply_action_result(session, action, {})
                self.assertEqual(sum(i.get("quantity", 1) for i in session["character"]["inventory"] if i.get("id") == "holy_water"), 0)

    def test_advice_grants_one_holy_water_only_on_success(self):
        for success in (True, False):
            session = checkpoints.fresh_session(deepcopy(self.pack), "hero")
            action = state.resolve_action(session, action_id="ask_general_advice")
            state.apply_action_result(session, action, {"dc": 15, "success": success})
            self.assertIn("不死の者には聖水が効く", select_hybrid_prepared_turn(session)["draft"]["gm_text"])
            self.assertEqual(sum(i.get("quantity", 1) for i in session["character"]["inventory"] if i.get("id") == "holy_water"), int(success))

    def test_every_entry_effect_sets_flag_and_grants_level(self):
        def transitions(value):
            if isinstance(value, dict):
                if value.get("current_location", value.get("next_location")) in {"village", "village_approach", "valley_entrance"}:
                    yield value
                for child in value.values():
                    yield from transitions(child)
            elif isinstance(value, list):
                for child in value:
                    yield from transitions(child)

        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(filename))
            entries = [(location, effect) for location in pack["locations"] for effect in transitions(location)]
            self.assertEqual(len(entries), 9)
            self.assertEqual(sum(location["id"] == "gorge_worm_lair" for location, _ in entries), 1)
            for location, effect in entries:
                session = checkpoints.fresh_session(deepcopy(pack), "hero")
                session["world_state"] = {"scene_id": location["scene_id"], "location_id": location["id"]}
                dest = effect.get("current_location", effect.get("next_location"))
                flag, level = ("entered_dragon_valley", 1) if dest == "valley_entrance" else ("reached_village", 4)
                if dest != "valley_entrance":
                    self.assertIn(flag, effect["flags_set"])
                state.apply_state_delta(session, state._effects_to_state_delta([effect], session), allow_world_transition=True)
                self.assertEqual(session["character"]["level"], level)
                self.assertEqual(session["character"]["max_hp"], 20 + (level - 1) * 5)
                self.assertEqual(state.current_location_id(session), dest)
                self.assertEqual(state.sanitize_model_state_delta(session, {"flags_set": [flag]}), {})

    def test_checkpoint_has_real_supplies_and_unlocked_combat_skills(self):
        cp = checkpoints.generate()
        for encounter, entry in cp["encounters"].items():
            for cid, actor in entry["characters"].items():
                holy = next(i for i in actor["inventory"] if i.get("id") == "holy_water")
                self.assertEqual(holy["quantity"], 1 if encounter == "xanxus_phantom_battle" else 2)
                self.assertEqual([source["step"] for source in actor["sources"][:2]], ["@opening", "check_supplies"])
                if encounter == "warlock_rescue_battle":
                    continue
                session = sim.prepare_session(self.pack, encounter, cid, cp)
                self.assertEqual(session["character"]["skills"], actor["skills"])
                combat.ensure_combat_started(session)
                ids = {a["id"] for a in combat.combat_actions(session) if a["type"] == "skill"}
                for skill in actor["skills"]:
                    self.assertIn(skill["id"], ids)

    def test_village_without_companion_and_valley_without_ian_reward(self):
        for cid in ("hero", "cleric", "mage", "thief"):
            session = checkpoints.fresh_session(deepcopy(self.pack), cid)
            route = ["go_castle_town"] + checkpoints.proposed_routes()["frost_wolf_battle"] + ["@victory"]
            for step in route:
                checkpoints.replay_step(session, step)
            self.assertTrue(session["flags"]["reached_village"])
            self.assertFalse(session["flags"].get("warlock_disappeared_at_village"))
            self.assertEqual(session["character"]["level"], 4)
            action = next(a for a in state.current_actions_for_session(session)
                          if a["id"] != "accept_ian_request")
            state.apply_action_result(session, action, {})
            self.assertTrue(session["flags"]["entered_dragon_valley"])
            self.assertFalse(session["flags"].get("accepted_ian_request"))
            self.assertEqual(session["character"]["level"], 4)


if __name__ == "__main__":
    unittest.main()
