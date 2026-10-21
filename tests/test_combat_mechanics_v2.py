from __future__ import annotations

import json
import random
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from host import app, combat, difficulty, free_actions, state, status_effects
from host.scenario_context import load_scenario_pack, normalize_scenario_pack, select_scenario_context
from scripts.balance import checkpoints, sim
from scripts.scenario.combat_mechanics_v2 import migrate, status_definitions

ROOT = Path.cwd()


def session(mode="normal", category="trash", *, start=True):
    actor = {"id": "hero", "name": "勇者", "attributes": {"dex": 16, "str": 8, "wis": 8},
             "hp": 100, "max_hp": 100, "mp": 20, "max_mp": 20, "sp": 20, "max_sp": 20,
             "skills": [], "inventory": [], "combat": {"evade": 8, "basic_attack": {"damage": "1", "accuracy": 100}}}
    enemy = {"id": "slime", "name": "スライム", "hp": 100, "max_hp": 100,
             "attributes": {"dex": 8, "str": 8}, "combat": {"evade": 2, "basic_attack": {"damage": "1", "accuracy": 0}},
             "resistances": {"ice": 1}, "skills": []}
    pack = {"meta": {"initial_scene": "arena"}, "characters": [actor], "enemies": [enemy],
            "scenes": [{"id": "arena", "location_ids": ["arena"]}], "locations": [{"id": "arena", "scene_id": "arena",
                "enemy_ids": ["slime"], "combat": {"encounter_class": category}}],
            "status_defs": status_definitions(), "combat_rules": {"sp_regen_per_round": 0,
                "evade_model": "dex" if mode == "normal" else "fixed"}}
    value = checkpoints.fresh_session(normalize_scenario_pack(pack), "hero")
    value["difficulty"] = mode
    if start:
        with patch.object(combat, "random", random.Random(51)):
            combat.ensure_combat_started(value)
    return value


def apply(value, actor, identifier, source=None, **spec):
    return status_effects.apply(value, actor, {"id": identifier, **spec}, source or value["character"], random.Random(51))

from scripts.scenario.spring_postgame import apply as apply_spring_postgame


class EvadeTests(unittest.TestCase):
    def test_fixed_dex_and_boundaries(self):
        value = session()
        actor = value["character"]
        self.assertEqual(combat.actor_evade(value, actor), 18)
        for dex, expected in ((0, 0), (4, 0), (8, 6), (100, 20)):
            actor["attributes"]["dex"] = dex
            self.assertEqual(combat.actor_evade(value, actor), expected)
        actor["combat"]["evade_cap"] = 7
        self.assertEqual(combat.actor_evade(value, actor), 7)
        value["scenario_pack"]["combat_rules"]["evade_model"] = "fixed"
        self.assertEqual(combat.actor_evade(value, actor), 8)

    def test_temporary_evade_cap_and_duration(self):
        value = session()
        actor = value["character"]
        apply(value, actor, "haste", duration=20, modifiers={"evade_bonus": 80})
        self.assertEqual(combat.actor_evade(value, actor), 40)
        self.assertEqual(actor["statuses"][0]["remaining_rounds"], 2)
        status_effects.tick(value, actor, random.Random(1))
        status_effects.tick(value, actor, random.Random(1))
        self.assertEqual(combat.actor_evade(value, actor), 18)
        apply(value, actor, "haste", modifiers={"evade_bonus": -50})
        self.assertEqual(combat.actor_evade(value, actor), 0)

    def test_accuracy_override_penalty_floor_and_true_damage(self):
        value = session()
        enemy, actor = value["combat"]["enemies"][0], value["character"]
        ability = {"damage": "1", "accuracy": 50}
        self.assertEqual(combat.attack_chance(value, enemy, actor, ability, enemy["id"]), 32)
        value["scenario_pack"]["combat_rules"]["enemy_accuracy_override"] = 100
        self.assertEqual(combat.attack_chance(value, enemy, actor, ability, enemy["id"]), 82)
        apply(value, enemy, "blind")
        self.assertEqual(combat.attack_chance(value, enemy, actor, ability, enemy["id"]), 52)
        enemy["statuses"][0]["modifiers"]["accuracy_penalty"] = 500
        self.assertEqual(combat.attack_chance(value, enemy, actor, ability, enemy["id"]), 5)
        self.assertEqual(combat.attack_chance(value, enemy, actor, {**ability, "true_damage": True}, enemy["id"]), 100)

    def test_log_ui_share_chance_and_model_keeps_its_existing_fields(self):
        value = session()
        enemy = value["combat"]["enemies"][0]
        action = combat.combat_actions(value)[0]
        expected = action["hit_chance_by_target"][enemy["id"]]
        combat.perform_combat_action(value, "attack", rng=random.Random(1))
        event = next(event for event in value["combat"]["log"] if event["kind"] == "damage" and event["actor"] == "player")
        self.assertEqual(event["data"]["hit_chance"], expected)
        record = select_scenario_context(value)["matched"]["enemies"][0]
        self.assertNotIn("combat", record)
        self.assertEqual(record["attributes"]["dex"], enemy["attributes"]["dex"])


class CooldownAndRestrictionTests(unittest.TestCase):
    def add_guard(self, value, cooldown=1):
        value["character"]["skills"] = [{"id": "divine_guard", "name": "神聖の庇護", "kind": "defend",
                                           "cost": 0, "survive_at_one": True, "cooldown": cooldown}]

    def charm(self, value, limited=True):
        spec = {"kind": "damage", "damage": "2", "accuracy": 100, "element": "ice", "consumable": False}
        if limited:
            spec["requires_target_weakness"] = "ice"
        value["character"]["inventory"] = [{"id": "ice_charm", "name": "氷の護符", "quantity": 1, "combat": spec}]

    def test_cooldown_next_round_then_recovers_and_starts_clean(self):
        value = session()
        self.add_guard(value)
        combat.perform_combat_action(value, "skill", "divine_guard", rng=random.Random(1))
        reason = combat.combat_actions(value)[1]["disabled_reason"]
        self.assertEqual(reason, "あと1ラウンド")
        before = deepcopy(value)
        with self.assertRaisesRegex(combat.CombatError, reason):
            combat.perform_combat_action(value, "skill", "divine_guard")
        self.assertEqual(value, before)
        combat.perform_combat_action(value, "defend", rng=random.Random(1))
        self.assertTrue(combat.combat_actions(value)[1]["enabled"])
        value["combat"] = None
        combat.ensure_combat_started(value)
        self.assertEqual(combat._cooldown_remaining(value, "skill", "divine_guard"), 0)

    def test_cooldown_counts_rounds_not_extra_actions(self):
        value = session()
        self.add_guard(value, 2)
        value["combat"]["actions_remaining"] = 2
        combat.perform_combat_action(value, "skill", "divine_guard", rng=random.Random(1))
        self.assertEqual(value["combat"]["round"], 1)
        self.assertEqual(combat._cooldown_remaining(value, "skill", "divine_guard"), 2)
        for expected in (2, 1, 0):
            combat.perform_combat_action(value, "defend", rng=random.Random(1))
            self.assertEqual(combat._cooldown_remaining(value, "skill", "divine_guard"), expected)

    def test_api_and_free_mapping_reject_same_reason(self):
        for action_type, identifier in (("skill", "divine_guard"), ("item", "ice_charm")):
            value = session()
            self.add_guard(value)
            self.charm(value)
            if action_type == "skill":
                combat.perform_combat_action(value, "skill", identifier, rng=random.Random(1))
            before = deepcopy(value)
            with patch.object(app, "load_session", return_value=value), patch.object(app, "save_session") as save:
                with self.assertRaises(HTTPException) as caught:
                    app.api_combat_action("test", app.CombatActionRequest(action_type=action_type, action_id=identifier))
                self.assertEqual(caught.exception.status_code, 409)
                save.assert_not_called()
            with self.assertRaises(HTTPException) as text_error:
                app._run_turn(value, app.TurnRequest(text=identifier, action_id=identifier))
            self.assertEqual(text_error.exception.detail, caught.exception.detail)
            result = free_actions.adjudicate(value, {"kind": "existing", "action_id": identifier,
                "operation": "use_item" if action_type == "item" else "", "item_id": identifier,
                "target_id": "", "advance": False, "approach": "", "reply": ""})
            self.assertEqual(result["outcome"], "rejected")
            self.assertEqual(result["text"], caught.exception.detail)
            self.assertEqual(value, before)

    def test_ice_charm_current_weakness_multi_target_and_baby(self):
        value = session()
        self.charm(value)
        first = value["combat"]["enemies"][0]
        second = deepcopy(first)
        second.update(id="slime:2", resistances={"ice": 1.5})
        value["combat"]["enemies"].append(second)
        action = next(action for action in combat.combat_actions(value) if action["id"] == "ice_charm")
        self.assertTrue(action["enabled"])
        self.assertEqual(action["valid_target_ids"], [second["id"]])
        with self.assertRaises(combat.CombatError):
            combat.perform_combat_action(value, "item", "ice_charm", first["id"])
        combat.perform_combat_action(value, "item", "ice_charm", second["id"], rng=random.Random(1))
        apply(value, first, "holy_blessing", modifiers={"damage_taken_multipliers": {"ice": 1.5}})
        self.assertTrue(combat._target_requirement_passes(value["character"]["inventory"][0]["combat"], first))
        baby = session("baby")
        self.charm(baby, False)
        combat.perform_combat_action(baby, "item", "ice_charm", rng=random.Random(1))

    def test_prism_tree_rotation(self):
        pack = difficulty.apply_difficulty(load_scenario_pack(checkpoints.DEFAULT_SCENARIO), "normal")
        tree = next(enemy for enemy in pack["enemies"] if enemy["id"] == "prism_tree")
        value = session()
        self.charm(value)
        value["combat"]["enemies"] = [combat._runtime_enemy(tree, 0)]
        value["combat"]["enemies"][0]["hp"] = 10000
        for number, phase in enumerate(tree["resistance_cycle"]["phases"]):
            value["combat"]["round"] = 1 + number * tree["resistance_cycle"]["every"]
            combat._apply_round_start_effects(value, random.Random(1))
            action = next(action for action in combat.combat_actions(value) if action["id"] == "ice_charm")
            self.assertEqual(action["enabled"], phase["resistances"].get("ice", 1) > 1)

    def test_normal_survive_at_one_audit_and_baby_freeze(self):
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            base = load_scenario_pack(ROOT / "host/prompt/processed" / name)
            pack = difficulty.apply_difficulty(base, "normal")
            found = []
            def walk(value, parents=()):
                if isinstance(value, dict):
                    if value.get("survive_at_one"):
                        found.append(value)
                        self.assertTrue(any(record.get("cost", 0) > 0 or record.get("cooldown", 0) >= 1 for record in (*parents, value)), value)
                    for child in value.values():
                        walk(child, (*parents, value))
                elif isinstance(value, list):
                    for child in value:
                        walk(child, parents)
            for key in ("characters", "items", "status_defs", "companions", "combat_rules"):
                walk(pack.get(key, []))
            self.assertGreaterEqual(len(found), 4)
            baby = difficulty.apply_difficulty(base, "baby")
            guard = next(skill for skill in baby["characters"][0]["skills"] if skill["id"] == "divine_guard")
            self.assertNotIn("cooldown", guard)


class StatusTests(unittest.TestCase):
    def test_poison_stacks_refresh_and_symmetric_source_damage(self):
        value = session()
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        for target, source, damage in ((actor, enemy, 3), (enemy, actor, 6)):
            for _ in range(8):
                self.assertTrue(apply(value, target, "poison", source))
            self.assertEqual(target["statuses"][0]["stacks"], 3)
            status_effects.tick(value, target, random.Random(1))
            self.assertEqual(target["hp"], 100 - damage)
            apply(value, target, "poison", source)
            self.assertEqual(target["statuses"][0]["remaining_rounds"], 3)

    def test_burn_refresh_resistance_and_own_turn_expiry(self):
        value = session()
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        actor["resistances"] = {"fire": .5}
        apply(value, actor, "burn", enemy)
        status_effects.tick(value, actor, random.Random(1))
        self.assertEqual(actor["hp"], 99)
        apply(value, actor, "burn", enemy)
        self.assertEqual(actor["statuses"][0]["remaining_rounds"], 2)
        for _ in range(2):
            status_effects.tick(value, actor, random.Random(1))
        self.assertEqual(actor["statuses"], [])

    def test_damage_weakening_and_received_multiplier(self):
        value = session()
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        apply(value, actor, "weaken")
        damage = combat._resolve_attack(value, actor, enemy, {"damage": "20", "accuracy": 100}, "player", random.Random(1))
        self.assertEqual(damage, 15)
        enemy["combat"]["defense"] = 4
        damage = combat._resolve_attack(value, actor, enemy, {"damage": "20", "accuracy": 100}, "player", random.Random(1))
        self.assertEqual(damage, 12)
        enemy["combat"]["defense"] = 0
        apply(value, enemy, "holy_blessing", modifiers={"received_damage_multiplier": .5})
        damage = combat._resolve_attack(value, actor, enemy, {"damage": "20", "accuracy": 100}, "player", random.Random(1))
        self.assertEqual(damage, 8)

    def test_paralysis_skip_spends_no_resources_or_cooldown(self):
        value = session()
        actor = value["character"]
        actor["skills"] = [{"id": "holy_guard", "name": "聖なる守護", "kind": "defend", "cost": 6, "cost_type": "mp", "cooldown": 1}]
        apply(value, actor, "paralysis", modifiers={"skip_chance": 1})
        combat.perform_combat_action(value, "skill", "holy_guard", rng=random.Random(1))
        self.assertEqual(actor["mp"], 20)
        self.assertEqual(combat._cooldown_remaining(value, "skill", "holy_guard"), 0)
        self.assertEqual(value["combat"]["round"], 2)

    def test_stun_boss_immunity_allow_and_two_turn_recovery(self):
        value = session(category="boss")
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        self.assertFalse(apply(value, enemy, "stun"))
        enemy["status_allow"] = ["stun"]
        self.assertTrue(apply(value, enemy, "stun"))
        self.assertTrue(status_effects.skip_action(value, enemy, random.Random(1)))
        self.assertFalse(apply(value, enemy, "stun"))
        value = session()
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        self.assertTrue(apply(value, enemy, "stun"))
        self.assertTrue(status_effects.skip_action(value, enemy, random.Random(1)))
        for _ in range(2):
            self.assertFalse(apply(value, enemy, "stun"))
            status_effects.tick(value, enemy, random.Random(1))
        status_effects.tick(value, enemy, random.Random(1))
        self.assertTrue(apply(value, enemy, "stun"))
        enemy["status_immunity"] = ["poison"]
        self.assertFalse(apply(value, enemy, "poison"))
        self.assertTrue(apply(value, actor, "stun", enemy))

    def test_cleanse_count_all_tags_and_uncleansable(self):
        value = session()
        actor = value["character"]
        for identifier in ("burn", "poison", "stun", "holy_blessing"):
            apply(value, actor, identifier)
        status_effects.cleanse(value, actor, {"count": 1, "tags": ["debuff"]})
        self.assertEqual([status["id"] for status in actor["statuses"]], ["poison", "stun", "holy_blessing"])
        status_effects.cleanse(value, actor, {"count": "all", "tags": ["debuff"]})
        self.assertEqual([status["id"] for status in actor["statuses"]], ["stun", "holy_blessing"])
        value = session()
        actor = value["character"]
        actor["skills"] = [{"id": "cleric_lv5_b", "name": "大いなる癒し・浄化", "kind": "heal", "healing": "2d6+wis/2",
                            "cost": 14, "cost_type": "mp", "cleanse": {"count": "all", "tags": ["debuff"]}}]
        apply(value, actor, "burn")
        apply(value, actor, "poison")
        combat.perform_combat_action(value, "skill", "cleric_lv5_b", rng=random.Random(1))
        self.assertEqual(actor["statuses"], [])
        self.assertEqual(actor["mp"], 6)

    def test_dot_source_attributes_and_boss_combined_cap(self):
        value = session(category="boss")
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        actor["attributes"]["wis"] = 80
        apply(value, enemy, "holy_mark")
        apply(value, enemy, "poison", stacks=3)
        status_effects.tick(value, enemy, random.Random(1))
        self.assertEqual(enemy["hp"], 95)
        events = [event for event in value["combat"]["log"] if event["kind"] == "status_damage"]
        self.assertEqual(sum(event["data"]["damage"] for event in events), 5)
        self.assertIn("wis", events[0]["data"]["formula"]["formula"])

    def test_enemy_application_waits_for_player_turn_and_hits_only(self):
        value = session("baby")
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        enemy["combat"]["basic_attack"] = {"damage": "4", "accuracy": 100, "on_hit_status": {"id": "burn"}}
        combat.perform_combat_action(value, "defend", rng=random.Random(1))
        self.assertEqual(actor["statuses"][0]["remaining_rounds"], 2)
        hp = actor["hp"]
        enemy["combat"]["basic_attack"] = {"damage": "1", "accuracy": 0}
        combat.perform_combat_action(value, "defend", rng=random.Random(1))
        self.assertEqual(actor["hp"], hp - 2)
        for ability in ({"damage": "0", "accuracy": 100}, {"damage": "1", "accuracy": 0}):
            actor.pop("statuses", None)
            combat._resolve_attack(value, enemy, actor, {**ability, "element": "fire", "on_hit_status": {"id": "burn"}}, enemy["id"], random.Random(10))
            if ability["accuracy"] == 0:
                self.assertFalse(actor.get("statuses"))

    def test_chance_self_stacks_and_end_clear(self):
        value = session()
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        ability = {"damage": "1", "accuracy": 100, "on_hit_status": {"id": "poison", "target": "self", "stacks": 2, "chance": 100}}
        combat._resolve_attack(value, actor, enemy, ability, "player", random.Random(1))
        self.assertEqual(actor["statuses"][0]["stacks"], 2)
        self.assertFalse(enemy.get("statuses"))
        self.assertFalse(apply(value, enemy, "burn", chance=0))
        combat._finish_combat(value, "fled", "戦闘から離脱した。")
        self.assertEqual(actor["statuses"], [])
        self.assertEqual(combat.combat_result_for_llm(value)["outcome"], "fled")

    def test_extended_definitions_shields_haste_gospel_focus_mark(self):
        value = session()
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        apply(value, actor, "haste")
        self.assertEqual(value["combat"]["actions_remaining"], 2)
        self.assertFalse(apply(value, actor, "haste"))
        actor["hp"] = 30
        apply(value, actor, "gospel")
        self.assertEqual((actor["hp"], actor["max_hp"]), (130, 200))
        apply(value, actor, "arcane_shield")
        self.assertEqual(status_effects.absorb(actor, 1000), 0)
        apply(value, actor, "arcane_shield", modifiers={"shield": {"block_one_attack": True, "max_hp_ratio": .2}})
        self.assertEqual(status_effects.absorb(actor, 1000), 960)
        apply(value, actor, "holy_afterglow", modifiers={"shield": {"amount": 100, "max_hp_ratio": .25}})
        self.assertEqual(status_effects.absorb(actor, 60), 10)
        status_effects.clear(actor)
        self.assertEqual((actor["hp"], actor["max_hp"]), (100, 100))
        apply(value, actor, "magic_focus")
        damage = combat._resolve_attack(value, actor, enemy, {"damage": "10", "element": "holy", "accuracy": 100, "_skill_action": True}, "player", random.Random(1))
        self.assertEqual(damage, 13)
        self.assertFalse(actor.get("statuses"))
        apply(value, enemy, "holy_mark")
        combat._resolve_attack(value, actor, enemy, {"damage": "1", "accuracy": 100, "_basic_action": True}, "player", random.Random(1))
        self.assertEqual(sum(event["text"].startswith("聖印が") for event in value["combat"]["log"]), 1)

    def test_old_save_without_statuses_loads(self):
        value = session()
        value["character"].pop("statuses", None)
        self.assertNotIn("statuses", value["character"])
        saved = ROOT / ".tmp-test/051/old-save"
        saved.mkdir(parents=True, exist_ok=True)
        value["id"] = "old"
        (saved / "old.json").write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        with patch.object(state, "SAVE_DIR", saved):
            value = state.load_session("old")
        combat.perform_combat_action(value, "defend", rng=random.Random(1))
        self.assertTrue(combat.combat_is_active(value))

    def test_legacy_cleanse_and_ui_descriptions(self):
        value = session()
        actor = value["character"]
        combat._apply_status(actor, {"id": "burn", "name": "火傷", "damage": "1", "remaining_rounds": 2})
        label = combat.public_combat(value)["player_statuses"][0]
        self.assertEqual(label["description"], status_definitions()[0]["description"])
        status_effects.cleanse(value, actor, {"count": "all", "tags": ["debuff"]})
        self.assertEqual(actor["statuses"], [])

    def test_phase_end_buffs_survive_player_tick_and_damage_floor(self):
        value = session()
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        apply(value, actor, "holy_blessing")
        value["combat"]["player_status"] = {"guard_multiplier": .25}
        status_effects.tick(value, actor, random.Random(1))
        self.assertTrue(actor["statuses"])
        combat._resolve_attack(value, enemy, actor, {"damage": "100", "accuracy": 100}, enemy["id"], random.Random(1))
        self.assertEqual(actor["hp"], 75)
        combat._enemy_phase(value, random.Random(1))
        self.assertFalse(actor["statuses"])

    def test_gospel_heals_only_hp_loss_twice_and_rest_restores_original_cap(self):
        value = session()
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        actor["hp"] = 50
        apply(value, actor, "gospel")
        for _ in range(3):
            combat._resolve_attack(value, enemy, actor, {"damage": "10", "accuracy": 100}, enemy["id"], random.Random(1))
        self.assertEqual(actor["hp"], 136)
        state.apply_state_delta(value, {"restore_full": True})
        self.assertEqual((actor["hp"], actor["max_hp"]), (100, 100))


class CompanionAndHazardTests(unittest.TestCase):
    def companion(self, mode="normal", empowered=False, resistance=1, accuracy=None):
        value = session(mode)
        base = load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        pack = difficulty.apply_difficulty(base, mode)
        value["companion"] = deepcopy(next(entry for entry in pack["companions"] if entry["id"] == "fire_bat_dragon"))
        value["flags"]["fire_bat_empowered"] = empowered
        value["character"]["hp"] = 1
        enemy = value["combat"]["enemies"][0]
        enemy["resistances"]["fire"] = resistance
        enemy["attributes"]["dex"] = 4
        return value

    def test_scaled_healing_rounding_actual_hp_and_legacy_fixed(self):
        for empowered in (False, True):
            value = self.companion(empowered=empowered)
            enemy = value["combat"]["enemies"][0]
            enemy["hp"] = 1
            combat._apply_ally_round_start_effects(value, value["companion"], random.Random(1))
            self.assertEqual(value["character"]["hp"], 1 + (2 if empowered else 1))
            baby = self.companion("baby", empowered)
            combat._apply_ally_round_start_effects(baby, baby["companion"], random.Random(1))
            self.assertEqual(baby["character"]["hp"], 7 if empowered else 4)

    def test_resistance_miss_and_zero_damage_do_not_heal(self):
        for resistance in (.5, 0):
            value = self.companion(resistance=resistance)
            combat._apply_ally_round_start_effects(value, value["companion"], random.Random(1))
            self.assertEqual(value["character"]["hp"], 1)
        value = self.companion()
        value["combat"]["enemies"][0]["attributes"]["dex"] = 100
        with patch.object(random.Random, "randint", return_value=100):
            combat._apply_ally_round_start_effects(value, value["companion"], random.Random(1))
        self.assertEqual(value["character"]["hp"], 1)

    def test_hazard_success_failure_nonlethal_and_pending_status(self):
        action = {"id": "trap", "text": "罠を解除する", "hazard": {"kind": "trap", "warning": "毒"},
                  "roll": {"dice_type": "1d20+dex", "dc": 10, "skill": "隠密"}, "success_effects": [],
                  "failure_effects": [{"damage_player": {"max_hp_ratio": .15}}, {"apply_status": "poison"}]}
        value = session(start=False)
        state.apply_action_result(value, action, {"dc": 10, "total": 20, "rolls": [20], "success": True})
        self.assertEqual(value["character"]["hp"], 100)
        state.apply_action_result(value, action, {"dc": 10, "total": 1, "rolls": [1], "success": False})
        self.assertEqual(value["character"]["hp"], 85)
        self.assertEqual(value["character"]["statuses"][0]["remaining_rounds"], 3)
        combat.ensure_combat_started(value)
        self.assertEqual(value["character"]["hp"], 85)
        combat.perform_combat_action(value, "defend", rng=random.Random(1))
        self.assertEqual(value["character"]["hp"], 84)
        for spec in ({"flat": 10000}, {"dice": "10000"}, {"max_hp_ratio": 10}):
            state.apply_state_delta(value, state._effects_to_state_delta([{"damage_player": spec}], value))
            self.assertEqual(value["character"]["hp"], 1)
        state.apply_state_delta(value, {"restore_full": True})
        self.assertFalse(value["character"].get("statuses"))

    def test_active_items_aoe_cleanse_buff_cooldown(self):
        value = session()
        enemy = value["combat"]["enemies"][0]
        value["combat"]["enemies"].append({**deepcopy(enemy), "id": "slime:2"})
        value["character"]["inventory"] = [{"id": "holy_water", "name": "聖水", "quantity": 2,
            "combat": {"kind": "damage", "damage": "2", "accuracy": 100, "all_targets": True, "cooldown": 1,
                       "on_hit_status": {"id": "poison"}, "cleanse": {"count": "all", "tags": ["debuff"]},
                       "self_status": {"id": "holy_blessing", "modifiers": {"received_damage_multiplier": .75, "evade_bonus": 80}}}}]
        apply(value, value["character"], "burn")
        combat.perform_combat_action(value, "item", "holy_water", rng=random.Random(1))
        self.assertFalse(any(status["id"] == "burn" for status in value["character"]["statuses"]))
        self.assertTrue(all(enemy["hp"] < 100 for enemy in value["combat"]["enemies"]))
        self.assertEqual(combat._cooldown_remaining(value, "item", "holy_water"), 1)


class MigrationAndGoldenTests(unittest.TestCase):
    def test_normal_rule_parameters_can_be_tuned_in_data(self):
        base = load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        for entry in base["difficulty_overlays"]["normal"]:
            if entry["path"] == "evade_formula":
                entry["set"] = {"base": 3, "per_dex": 1.25, "cap": 18}
            elif entry["path"] == "enemy_accuracy_override":
                entry["set"] = 95
            elif entry["path"].endswith(".cooldown"):
                entry["set"] = 2
        self.assertEqual(difficulty.apply_difficulty(base, "normal")["combat_rules"]["enemy_accuracy_override"], 95)
        self.assertNotIn("evade_model", difficulty.apply_difficulty(base, "baby")["combat_rules"])
        entry = next(entry for entry in base["difficulty_overlays"]["normal"] if entry["path"] == "evade_formula")
        for invalid in ({"base": 4, "per_dex": -1, "cap": 20}, {"base": 4, "per_dex": float("nan"), "cap": 20},
                        {"base": 4, "per_dex": 1.5, "cap": 41}):
            entry["set"] = invalid
            with self.assertRaises(ValueError):
                difficulty.validate_difficulty(base)

    def test_old_normal_guard_refreshes_cooldown_baby_does_not(self):
        latest = load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        for mode in ("baby", "normal"):
            base = deepcopy(latest)
            base["difficulty_overlays"] = {"normal": []}
            base["meta"]["content_revision"] = "2026-10-20-difficulty-047"
            value = checkpoints.fresh_session(base, "hero")
            value.update(difficulty=mode, scenario_path=str(checkpoints.DEFAULT_SCENARIO))
            self.assertTrue(state._refresh_session_scenario_pack(value))
            guard = next(skill for skill in value["character"]["skills"] if skill["id"] == "divine_guard")
            self.assertEqual(guard.get("cooldown"), 1 if mode == "normal" else None)

    def test_migration_sync_idempotent_frozen_base_and_schema(self):
        schema = json.loads((ROOT / "host/prompt/processed/scenario_pack.schema.json").read_text(encoding="utf-8"))
        packs = []
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = json.loads((ROOT / "host/prompt/processed" / name).read_text(encoding="utf-8"))
            self.assertEqual(migrate(pack), pack)
            original = deepcopy(pack)
            original.pop("status_defs")
            original["difficulty_overlays"] = {"normal": []}
            original["meta"]["content_revision"] = "2026-10-20-difficulty-047"
            migrated = migrate(original)
            apply_spring_postgame(migrated)
            from scripts.scenario.levels_skills_v2 import migrate as levels
            migrated = levels(migrated)
            from scripts.scenario.holy_sword_049 import migrate as holy_sword
            migrated = holy_sword(migrated)
            from scripts.scenario.mina_reborrow_055 import migrate as mina_reborrow
            migrated = mina_reborrow(migrated)
            self.assertEqual(migrated, pack)
            self.assertEqual(difficulty.numeric_snapshot(original), difficulty.numeric_snapshot(pack))
            try:
                import jsonschema
            except ImportError:
                pass
            else:
                jsonschema.validate(pack, schema)
                jsonschema.validate(difficulty.apply_difficulty(pack, "normal"), schema)
            packs.append(pack)
        self.assertEqual(packs[0]["status_defs"], packs[1]["status_defs"])
        self.assertEqual(packs[0]["difficulty_overlays"], packs[1]["difficulty_overlays"])
        expected_descriptions = {status["id"]: status["description"] for status in status_definitions()}
        self.assertEqual(
            {status["id"]: status["description"] for status in packs[0]["status_defs"]
             if status["id"] in expected_descriptions},
            expected_descriptions,
        )

    def test_full_log_samples_baby_and_empty_normal(self):
        from combat_v2_golden import stable

        golden = json.loads((Path(__file__).parent / "fixtures/baby_combat_golden.json").read_text(encoding="utf-8"))
        base = load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        base["difficulty_overlays"] = {"normal": []}
        cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
        for mode in ("baby", "normal"):
            for sample in golden["battles"]:
                value = sim.prepare_session(difficulty.apply_difficulty(base, mode), sample["encounter"], sample["character"], cp)
                rng = random.Random(sim.trial_seed(golden["seed"], sample["encounter"], sample["character"], 0))
                with patch.object(combat, "random", rng):
                    combat.ensure_combat_started(value)
                    while combat.combat_is_active(value):
                        action, target = sim.choose_action(value, "heuristic")
                        combat.perform_combat_action(value, action["type"], action["id"], target, rng=rng)
                self.assertEqual(stable(value["combat"]["log"]), sample["log"])


if __name__ == "__main__":
    unittest.main()
