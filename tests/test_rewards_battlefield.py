from __future__ import annotations

from scripts.scenario.holy_sword_049 import migrate as holy_sword
from scripts.scenario.levels_skills_v2 import migrate as levels

import json
import random
import unittest
from copy import deepcopy
from unittest.mock import patch

from host import combat, free_actions, maps, shops, state
from host.scenario_context import select_hybrid_prepared_turn
from scripts.balance.checkpoints import DEFAULT_SCENARIO, fresh_session
from scripts.scenario.rewards_battlefield import BOOSTS, DROPS, ELITE_REGIONS, FRUIT_AMOUNT, STEALS, ZEBOK_TEXTS, upgrade

from scripts.scenario.spring_postgame import apply as apply_spring_postgame


class RewardsBattlefieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(DEFAULT_SCENARIO)

    def session(self, location="forest_exit", character="hero"):
        session = fresh_session(deepcopy(self.pack), character)
        state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)
        return session

    def give(self, session, identifier, quantity=1):
        item = next(i for i in session["scenario_pack"]["items"] if i["id"] == identifier)
        state.apply_state_delta(session, {"inventory_add": [{**item, "quantity": quantity}]})

    def resolve(self, session, identifier, success=True):
        action = state.resolve_action(session, action_id=identifier)
        self.assertIsNotNone(action, identifier)
        self.assertTrue(state.action_requirement_status(action, session)[0], identifier)
        return state.apply_action_result(session, action, {"success": success, "dc": 1} if action.get("roll") else {})

    def victory(self, session):
        encounter = combat._encounter_for_session(session, session["scenario_pack"])
        enemies = [next(e for e in session["scenario_pack"]["enemies"] if e["id"] == eid)
                   for eid in encounter["enemy_ids"]]
        delta = combat._victory_delta(session, enemies, encounter)
        state.apply_state_delta(session, delta, allow_world_transition=True)
        return delta

    def test_permanent_items_all_classes_missing_attributes_and_consumption(self):
        for character in ("hero", "cleric", "mage", "thief"):
            for identifier, name, stat, _ in BOOSTS:
                with self.subTest(character=character, item=identifier):
                    session = self.session(character=character)
                    actor = session["character"]
                    actor["attributes"].pop(stat, None)
                    self.give(session, identifier, 2)
                    before = deepcopy(actor)
                    text = shops.use_item(session, identifier)
                    if stat in {"hp", "mp"}:
                        self.assertEqual(actor[f"max_{stat}"], before[f"max_{stat}"] + FRUIT_AMOUNT)
                        self.assertEqual(actor[stat], before[stat] + FRUIT_AMOUNT)
                    else:
                        self.assertEqual(actor["attributes"][stat], 2)
                    self.assertIn("永続的に", text)
                    self.assertEqual(next(i for i in actor["inventory"] if i.get("id") == identifier)["quantity"], 1)
                    shops.use_item(session, identifier)
                    self.assertFalse(any(i.get("id") == identifier for i in actor["inventory"]))
                    with self.assertRaises(shops.ShopError):
                        shops.use_item(session, identifier)
                    state._normalize_character(actor)
                    if stat not in {"hp", "mp"}:
                        self.assertEqual(actor["attributes"][stat], 4)
        boost_ids = {b[0] for b in BOOSTS}
        self.assertFalse(any(offer["item_id"] in boost_ids for shop in self.pack["shops"] for offer in shop["items"]))

    def test_every_encounter_reward_is_once_and_not_per_enemy(self):
        for location, (item, quantity) in DROPS.items():
            with self.subTest(location=location):
                session = self.session(location)
                first = self.victory(session)
                added = [i for i in first.get("inventory_add", []) if i.get("id") == item]
                self.assertEqual(sum(i["quantity"] for i in added), quantity)
                state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)
                second = self.victory(session)
                self.assertFalse(any(i.get("id") == item for i in second.get("inventory_add", [])))
        for location in ("dragon_valley_loc", "draco_battle", "xanxus_battle", "warlock_rescue_battle"):
            self.assertNotIn("one_time_reward", next(l for l in self.pack["locations"] if l["id"] == location)["combat"])

    def test_steals_and_victories_share_flags_in_both_orders(self):
        for location, action_id in STEALS.items():
            for first in ("steal", "victory"):
                with self.subTest(location=location, first=first):
                    session = self.session(location)
                    if first == "steal":
                        result = self.resolve(session, action_id)
                        self.assertIn("くすねた。", result["extra_text"])
                        prepared = select_hybrid_prepared_turn(session)
                        if prepared:
                            self.assertIn("くすねた。", prepared["draft"]["gm_text"])
                    else:
                        self.victory(session)
                    state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)
                    action = next(a for l in self.pack["locations"] if l["id"] == location
                                  for a in l["actions"] if a["id"] == action_id)
                    result = state.apply_action_result(session, action, {"dc": 1, "success": True})
                    self.assertNotIn("くすねた。", result["extra_text"])
                    state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)
                    self.victory(session)
                    item, quantity = DROPS[location]
                    self.assertEqual(next(i for i in session["character"]["inventory"] if i.get("id") == item)["quantity"], quantity)
            session = self.session(location)
            result = self.resolve(session, action_id, False)
            self.assertNotIn("くすねた。", result["extra_text"])
            self.assertNotIn(f"reward_claimed:{location}", session["flags"])

    def test_free_sneak_grants_reward_but_food_alone_does_not(self):
        for operation in ("sneak", "distract"):
            session = self.session("forest_wolves")
            plan = dict(kind="interact", operation=operation, target_id="forest_wolves",
                        item_id="trail_ration" if operation == "distract" else "", advance=True,
                        action_id="", approach="潜行する", reply="")
            with patch.object(state.random, "randint", return_value=20):
                result = free_actions.adjudicate(session, plan)
            self.assertEqual(result["outcome"], "success")
            self.assertEqual(bool(session["flags"].get("reward_claimed:forest_wolves")), operation == "sneak")

    def test_elites_share_only_their_map_reward_in_any_order_and_legacy_saves(self):
        from host.item_mechanics import steal_reward

        for region, locations in ELITE_REGIONS.items():
            for first in locations:
                for source in ("victory", "steal", "legacy"):
                    with self.subTest(region=region, first=first, source=source):
                        session = self.session(first)
                        if source == "victory":
                            self.victory(session)
                        elif source == "steal":
                            delta, _ = steal_reward(session, first)
                            state.apply_state_delta(session, delta)
                        else:
                            session["flags"][f"reward_claimed:{first}"] = True
                        for other in locations:
                            self.assertEqual(steal_reward(session, other), ({}, ""))
                            state.apply_state_delta(session, {"current_location": other}, allow_world_transition=True)
                            delta = self.victory(session)
                            self.assertFalse(any(i.get("id", "").startswith("fruit_") for i in delta.get("inventory_add", [])))
                        different = next(group[0] for key, group in ELITE_REGIONS.items() if key != region)
                        self.assertTrue(steal_reward(session, different)[0])
                        boss = self.session("grave_chapel")
                        boss["flags"].update(session["flags"])
                        self.assertEqual(sum(i["quantity"] for i in self.victory(boss).get("inventory_add", [])
                                             if i.get("id") == "fruit_life"), 2)

    def test_robin_stuns_only_target_for_two_rounds_and_never_reapplies(self):
        session = self.session("goblin_fort_fourth")
        state._set_companion(session, "robin")
        combat.ensure_combat_started(session)
        king = session["combat"]["enemies"][0]
        self.assertEqual(king["skip_rounds_remaining"], 2)
        with patch.object(combat, "_execute_enemy_ability") as execute:
            for _ in range(2):
                combat._enemy_phase(session, random.Random(1))
                combat._activate_encounter_modifiers(session)
            self.assertEqual([call.args[1]["template_id"] for call in execute.call_args_list], ["goblin_archer"] * 2)
            combat._enemy_phase(session, random.Random(1))
            self.assertEqual(execute.call_args_list[-2].args[1], king)
        self.assertEqual(sum(e["text"] == "ゴブリン王が頭を振りながら起き上がった。" for e in session["combat"]["log"]), 1)

    def test_ordinary_gold_is_awarded_after_regional_fruit_was_claimed(self):
        session = self.session("cave_heat_corridor")
        self.victory(session)
        state.apply_state_delta(session, {"current_location": "cave_lava_room"}, allow_world_transition=True)
        before = session["character"]["gold"]
        encounter = combat._encounter_for_session(session, session["scenario_pack"])
        original = sum(e.get("rewards", {}).get("gold", 0) for e in self.pack["enemies"]
                       if e["id"] in encounter["enemy_ids"])
        delta = self.victory(session)
        self.assertEqual(session["character"]["gold"] - before, original + encounter["victory_gold_bonus"])
        self.assertFalse(any(i.get("id", "").startswith("fruit_") for i in delta.get("inventory_add", [])))

    def test_fire_bat_empowerment_requires_companion_and_persists(self):
        for companion in (None, "fire_bat_dragon"):
            session = self.session("cave_prism_tree")
            state._set_companion(session, companion)
            combat.ensure_combat_started(session)
            combat._finish_combat(session, "victory", "勝利")
            prepared = session["combat"]["result"].get("prepared_text", "")
            state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
            self.assertEqual(bool(session["flags"].get("fire_bat_empowered")), bool(companion))
            self.assertEqual("嬉しそう" in prepared, bool(companion))
            if companion:
                session["combat"]["status"] = "active"
                session["combat"]["enemies"] = []
                session["character"]["hp"] = 1
                combat._apply_ally_round_start_effects(session, session["companion"], random.Random(1))
                self.assertEqual(session["character"]["hp"], 7)
                session["flags"].pop("fire_bat_empowered")
                combat._apply_ally_round_start_effects(session, session["companion"], random.Random(1))
                self.assertEqual(session["character"]["hp"], 10)

    def test_cursed_visibility_marsh_strength_and_knight_pass(self):
        for item in (None, "cursed_holy_sword", "cursed_holy_staff", "cursed_crystal_ball", "cursed_dagger"):
            session = self.session("bone_field")
            if item:
                self.give(session, item)
            choices = state.public_session(session)["choices"]
            self.assertEqual(any(c.get("action_id") == "show_curse_to_skeletons" for c in choices), bool(item))
            state.apply_state_delta(session, {"current_location": "ghoul_marsh"}, allow_world_transition=True)
            self.resolve(session, "fight_ghoul")
            combat.ensure_combat_started(session)
            enemies = session["combat"]["enemies"]
            self.assertEqual([e["template_id"] for e in enemies], ["ghoul"] if item else ["ghoul", "wraith"])
            template_hp = next(e["hp"] for e in self.pack["enemies"] if e["id"] == "ghoul")
            self.assertEqual(enemies[0]["hp"], round(template_hp * .6) if item else template_hp)
            combat.clear_combat_after_resolution(session)
            state.apply_state_delta(session, {"current_location": "grave_chapel"}, allow_world_transition=True)
            if item:
                self.resolve(session, "curse_pass_grave_knight")
                self.assertFalse(session["flags"].get("reward_claimed:grave_chapel"))
                self.resolve(session, "chapel_to_village")
                self.assertEqual(state.current_location_id(session), "village_frozen_clue")
                self.assertFalse(session["flags"].get("found_burning_house"))

    def test_zebok_four_entries_narrate_once_and_hostile_initiative(self):
        for index in range(4):
            session = self.session("ghoul_marsh")
            if index < 2:
                self.give(session, "cursed_dagger")
                session["flags"]["curse_bargain_pending" if index == 0 else "curse_price_paid"] = True
            if index == 2:
                session["flags"]["fought_cursed_merchant"] = True
            session["flags"]["passed_ghoul_marsh"] = True
            result = self.resolve(session, "marsh_to_chapel")
            self.assertIn(ZEBOK_TEXTS[index], result["result_text"])
            self.assertEqual(sum(text in result["result_text"] for text in ZEBOK_TEXTS), 1)
            self.assertEqual(state.public_session(session)["dialogue_portrait_image"], "/static/images/npc_zebok_merchant.png")
            self.resolve(session, "chapel_to_marsh")
            result = self.resolve(session, "marsh_to_chapel")
            self.assertFalse(any(text in result["result_text"] for text in ZEBOK_TEXTS))
            self.assertFalse(state.public_session(session)["dialogue_portrait_image"])
            session["combat_start_requested"] = True
            with patch.object(combat, "_enemy_phase") as phase:
                combat.ensure_combat_started(session)
            self.assertEqual(phase.call_count, int(index == 2))

    def test_peaceful_battlefield_locations_never_inherit_scene_enemies(self):
        for location in ("old_battlefield", "ruined_watchtower"):
            session = self.session(location)
            self.assertEqual(combat._encounter_for_session(session, session["scenario_pack"])["enemy_ids"], [])
            self.assertFalse(combat.ensure_combat_started(session))
            session["combat_start_requested"] = True
            self.assertFalse(combat.ensure_combat_started(session))

    def test_warlock_disabled_holy_weakness_cloak_and_watchtower_once(self):
        session = self.session("ruined_watchtower")
        self.resolve(session, "search_watchtower")
        shops.use_item(session, "gravekeeper_cloak")
        self.resolve(session, "talk_old_soldier")
        session["character"]["hp"] = 1
        self.resolve(session, "rest_watchtower")
        for action_id in ("search_watchtower", "rest_watchtower"):
            self.assertFalse(state.action_requirement_status(state.resolve_action(session, action_id=action_id), session)[0])
        self.assertEqual(session["character"]["hp"], session["character"]["max_hp"])
        state._set_companion(session, "blue_robed_mage")
        state.apply_state_delta(session, {"current_location": "bone_field"}, allow_world_transition=True)
        session["combat_start_requested"] = True
        combat.ensure_combat_started(session)
        session["combat"]["round"] = 2
        session["character"]["hp"] = 1
        combat._apply_ally_round_start_effects(session, session["companion"], random.Random(1))
        self.assertEqual(session["character"]["hp"], 1)
        enemy = session["combat"]["enemies"][0]
        self.assertIn("墓守の外套", session["character"]["equipment"])
        defense = combat._actor_defense(session["character"])
        session["character"]["equipment"].remove("墓守の外套")
        self.assertEqual(defense - combat._actor_defense(session["character"]), 1)
        session["character"]["equipment"].append("墓守の外套")
        self.assertEqual(combat._modified_received_damage(session, 5, "physical", enemy, "攻撃"), 3)
        for identifier in ("skeleton_soldier", "ghoul", "wraith", "grave_knight"):
            template = next(e for e in self.pack["enemies"] if e["id"] == identifier)
            self.assertEqual(combat._resistance_multiplier(template, "holy"), 1.5)
            self.assertEqual(combat._resistance_multiplier(template, "physical"), 1)
            self.assertEqual(combat._resistance_multiplier(template, "ice"), 1)

    def test_cloak_pickup_preserves_armor_and_only_fills_empty_slot(self):
        from scripts.scenario.ch3_routes_balance import CLOAK_DESCRIPTION, apply

        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = state.load_scenario_pack(DEFAULT_SCENARIO.with_name(filename))
            before = deepcopy(pack)
            apply(pack)
            apply_spring_postgame(pack)
            pack = holy_sword(levels(pack))
            from scripts.scenario.mina_reborrow_055 import migrate as mina_reborrow
            pack = mina_reborrow(pack)
            from scripts.scenario.normal_tuning_052 import migrate as normal_tuning
            pack = normal_tuning(pack)
            # Legacy migrations reappend overrides; compare their full content in the source order.
            order = {(e["entity"], e["id"], e["path"]): i
                     for i, e in enumerate(before["difficulty_overlays"]["normal"])}
            pack["difficulty_overlays"]["normal"].sort(
                key=lambda e: order.get((e["entity"], e["id"], e["path"]), len(order)))
            self.assertEqual(pack, before)
            for character in ("hero", "cleric", "mage", "thief"):
                for empty in (False, True):
                    with self.subTest(filename=filename, character=character, empty=empty):
                        session = fresh_session(pack, character)
                        session["world_state"] = {"location_id": "ruined_watchtower"}
                        actor = session["character"]
                        if empty:
                            actor["equipment"] = [i["name"] for i in state.equipped_items(actor) if state.item_slot(i) != "armor"]
                        equipment = list(actor["equipment"])
                        self.resolve(session, "search_watchtower")
                        cloak = next(i for i in actor["inventory"] if i.get("id") == "gravekeeper_cloak")
                        self.assertEqual(cloak["description"], CLOAK_DESCRIPTION)
                        self.assertEqual(actor["equipment"], equipment + [cloak["name"]] if empty else equipment)
                        if not empty:
                            shops.use_item(session, "gravekeeper_cloak")
                        self.assertIn(cloak["name"], actor["equipment"])
                        self.assertEqual(sum(state.item_slot(i) == "armor" for i in state.equipped_items(actor)), 1)
                        self.assertEqual(combat._actor_defense(actor), 1)
                        state.commit_world_position(session, location_id="bone_field")
                        session["combat_start_requested"] = True
                        self.assertTrue(combat.ensure_combat_started(session))
                        undead = session["combat"]["enemies"][0]
                        self.assertEqual(combat._modified_received_damage(session, 9, "physical", undead, "攻撃"), 7)
                        other = {"template_id": "rock_giant"}
                        self.assertEqual(combat._modified_received_damage(session, 9, "physical", other, "攻撃"), 9)
                        session["world_state"] = {"location_id": "valley_entrance"}
                        self.assertEqual(combat._modified_received_damage(session, 9, "physical", undead, "攻撃"), 9)

    def test_both_packs_map_edges_and_migration_idempotence(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = json.loads(DEFAULT_SCENARIO.with_name(filename).read_text(encoding="utf-8"))
            upgraded = deepcopy(pack)
            upgrade(upgraded)
            apply_spring_postgame(upgraded)
            upgraded = holy_sword(levels(upgraded))
            from scripts.scenario.mina_reborrow_055 import migrate as mina_reborrow
            upgraded = mina_reborrow(upgraded)
            from scripts.scenario.normal_tuning_052 import migrate as normal_tuning
            upgraded = normal_tuning(upgraded)
            # Legacy migrations reappend overrides; compare their full content in the source order.
            order = {(e["entity"], e["id"], e["path"]): i
                     for i, e in enumerate(pack["difficulty_overlays"]["normal"])}
            upgraded["difficulty_overlays"]["normal"].sort(
                key=lambda e: order.get((e["entity"], e["id"], e["path"]), len(order)))
            self.assertEqual(upgraded, pack)
            pack = state.load_scenario_pack(DEFAULT_SCENARIO.with_name(filename))
            session = fresh_session(pack, "hero")
            state.apply_state_delta(session, {"current_location": "forest_exit"}, allow_world_transition=True)
            state.apply_state_delta(session, {"current_location": "old_battlefield"}, allow_world_transition=True)
            session["choices"] = state.fallback_choices_for_session(session)
            self.assertEqual(maps.movement_action(session, "B2")["id"], "battlefield_to_bones")
            self.assertEqual(next(c for c in state.public_session(session)["choices"] if c["action_id"] == "battlefield_to_bones")["risk"], "不明")
            session["flags"]["passed_grave_chapel"] = True
            state.apply_state_delta(session, {"current_location": "grave_chapel"}, allow_world_transition=True)
            self.assertEqual(maps.movement_action(session, "B6")["id"], "chapel_to_village")


if __name__ == "__main__":
    unittest.main()
