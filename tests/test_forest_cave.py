from __future__ import annotations

import json
import random
import unittest
from copy import deepcopy
from unittest.mock import patch

from host import app, combat, free_actions, state
from host.maps import public_maps
from scripts.balance import checkpoints


class ForestCaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)

    def session(self, location, character="hero"):
        s = checkpoints.fresh_session(deepcopy(self.pack), character)
        s["world_state"] = {"scene_id": "dark_forest", "location_id": location}
        return s

    def act(self, s, aid, success=True):
        a = state.resolve_action(s, action_id=aid)
        self.assertIsNotNone(a, aid)
        self.assertTrue(state.action_requirement_status(a, s)[0], aid)
        return state.apply_action_result(s, a, {"dc": 15, "success": success} if a.get("roll") else {})

    def test_forest_connections_and_optional_branches(self):
        s = self.session("lost_goblin_crossroads")
        self.act(s, "help_lost_goblin")
        self.assertEqual(state.current_location_id(s), "lost_goblin_crossroads")
        self.act(s, "enter_goblin_fort")
        self.assertEqual(public_maps(s)["current_map_id"], "goblin_fort")
        s = self.session("slime_king_battle")
        checkpoints.replay_step(s, "@victory")
        self.assertEqual(state.current_location_id(s), "elf_spring")
        self.assertEqual(s["character"]["level"], 1)
        self.act(s, "continue_from_elf_spring")
        self.assertFalse(combat.ensure_combat_started(s))
        self.act(s, "distract_forest_wolves")
        self.assertEqual(state.current_location_id(s), "forest_exit")
        self.assertEqual(s["character"]["level"], 2)
        self.assertTrue(s["flags"]["saved_gald"])

    def test_seal_paths_conditional_dc_and_costs(self):
        for aid, resource, cost in (("decode_seal", "sp", 2), ("pray_at_seal", "sp", 2), ("force_seal", "hp", 4)):
            s = self.session("cave_seal")
            before = s["character"][resource]
            self.act(s, aid, False)
            self.assertEqual(s["character"][resource], before - cost)
            self.assertEqual(state.current_location_id(s), "cave_seal")
            self.act(s, aid)
            self.assertTrue(s["flags"]["cave_seal_broken"])
            self.assertEqual(state.current_location_id(s), "cave_heat_corridor")
        for flag in ("seal_pattern_known", "heard_seal_lore"):
            s = self.session("cave_seal")
            a = state.resolve_action(s, action_id="decode_seal")
            self.assertEqual(state.action_dice_settings(a, session=s)[1], 15)
            s["flags"][flag] = True
            self.assertEqual(state.action_dice_settings(a, session=s)[1], 8)
        s = self.session("cave_seal")
        state.apply_state_delta(s, {"inventory_add": [{"name": "聖水", "quantity": 1}]})
        self.act(s, "pour_holy_water_on_seal")
        self.assertFalse(any(i["name"] == "聖水" for i in s["character"]["inventory"]))

    def test_all_cave_defeats_return_alive_and_allow_retry(self):
        for lid in ("cave_heat_corridor", "cave_lava_room", "cave_crystal_corridor", "cave_prism_tree"):
            s = self.session(lid)
            s["combat_start_requested"] = True
            combat.ensure_combat_started(s)
            s["character"]["hp"] = 0
            combat._check_victory_or_defeat(s)
            state.apply_state_delta(s, combat.consume_combat_state_delta(s), allow_world_transition=True)
            combat.clear_combat_after_resolution(s)
            self.assertEqual(s["character"]["hp"], 1)
            self.assertFalse(s["game_over"])
            self.assertEqual(state.current_location_id(s), "elf_spring")
            state.commit_world_position(s, location_id=lid)
            s["combat_start_requested"] = True
            self.assertTrue(combat.ensure_combat_started(s))

    def test_prism_phases_periodic_heal_and_chill(self):
        s = self.session("cave_prism_tree")
        combat.ensure_combat_started(s)
        enemy = s["combat"]["enemies"][0]
        for turn, element in ((1, "fire"), (2, "fire"), (3, "ice"), (4, "ice"), (5, "earth"), (7, "fire")):
            s["combat"]["round"] = turn
            combat._apply_round_start_effects(s, random.Random(1))
            self.assertEqual(enemy["element"], element)
            self.assertEqual(enemy["resistances"][element], .25)
        self.assertEqual(sum(e["kind"] == "resistance_cycle" for e in s["combat"]["log"]), 3)
        s["combat"]["round"] = 3
        self.assertEqual(combat._choose_enemy_ability(enemy, s, random.Random(1))["name"], "根の吸収")
        combat._apply_status(s["character"], {"id": "chill", "name": "凍え", "accuracy_penalty": 15, "remaining_rounds": 2})
        with patch.object(combat, "_roll_formula", return_value=(1, {})):
            combat._resolve_attack(s, s["character"], enemy, {"accuracy": 100, "damage": "1"}, "player", random.Random(1))
        self.assertEqual(s["combat"]["log"][-1]["data"]["hit_chance"], 85)

    def test_rest_chest_and_class_weapons(self):
        s = self.session("cave_hot_spring")
        s["character"].update(hp=1, mp=0, sp=0)
        self.act(s, "rest_hot_spring")
        self.assertEqual(s["character"]["hp"], 11)
        self.assertFalse(state.action_requirement_status(state.resolve_action(s, action_id="rest_hot_spring") or {}, s)[0] if state.resolve_action(s, action_id="rest_hot_spring") else False)
        for char in ("hero", "cleric", "mage", "thief"):
            s = self.session("magic_shop", char)
            state.apply_state_delta(s, {"inventory_add": [{"name": "虹晶の欠片", "quantity": 1}]})
            self.act(s, "forge_prism_weapon")
            self.assertEqual(combat._equipped_weapon_attack(s["character"])["element"], "counter")
        self.assertEqual(public_maps(self.session("cave_fork"))["current_map_id"], "sealed_cave")

    def test_exact_seal_result_and_auto_battle_use_api_without_model(self):
        s = self.session("cave_seal")
        with patch.object(app, "save_session"), patch.object(app, "roll_dice", return_value={"dc": 15, "success": False}), patch.object(app, "chat_completion", side_effect=AssertionError("network")):
            result = app._run_turn(s, app.TurnRequest(text="魔法陣を解読する", action_id="decode_seal"))
        self.assertEqual(result["messages"][-1]["text"], "光が弾け、指先に痺れが走った。もう一度試すこともできる。")
