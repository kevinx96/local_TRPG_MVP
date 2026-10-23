from __future__ import annotations

import json
import random
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

from host import combat, shops, state
from host.item_mechanics import (effective_ability, effective_ability_cost,
                                 equipped_basic_attack_followups, equipped_item_specs, item_slot)
from scripts.balance.checkpoints import DEFAULT_SCENARIO, fresh_session
from scripts.scenario.equipment_slots import SLOTS, apply


class EquipmentSlotsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(DEFAULT_SCENARIO)

    def session(self, character="hero"):
        return fresh_session(deepcopy(self.pack), character)

    def give(self, session, identifier):
        item = next(item for item in self.pack["items"] if item["id"] == identifier)
        state.apply_state_delta(session, {"inventory_add": [{**item, "quantity": 1}]})
        return next(item for item in session["character"]["inventory"] if item.get("id") == identifier)

    def assert_slots(self, actor):
        selected = [item for item in actor["inventory"] if item["name"] in actor["equipment"]]
        slots = [item_slot(item) for item in selected]
        self.assertNotIn("", slots)
        self.assertEqual(len(slots), len(set(slots)))

    def test_pack_slots_price_and_idempotence(self):
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = state.load_scenario_pack(DEFAULT_SCENARIO.with_name(name))
            with self.subTest(pack=name):
                original = deepcopy(pack)
                apply(pack)
                self.assertEqual(pack, original)
                items = pack["items"] + [item for char in pack["characters"] for item in char["inventory"]]
                for item in items:
                    expected = "weapon" if item.get("combat", {}).get("kind") == "weapon" else ({"清めの鈴": "accessory"} | SLOTS).get(item["name"], "")
                    self.assertEqual(item_slot(item), expected, item["name"])
                offer = next(i for s in pack["shops"] if s["id"] == "forge_shop"
                             for i in s["items"] if i["item_id"] == "adamantite_armor")
                self.assertEqual(offer["price"], 60)
                robin = next(c for c in pack["companions"] if c["id"] == "robin")
                self.assertEqual(robin["round_start_effects"][0]["damage"], "2d4+1")
                self.assertEqual(robin["round_start_effects"][0]["target"], "highest_hp")

    def test_bag_replaces_each_slot_keeps_inventory_and_logs_once(self):
        session = self.session()
        actor = session["character"]
        for identifier, previous in (("ice_iron_greatsword", "鉄の剣"),
                                      ("adamantite_armor", "革の鎧"),
                                      ("activated_ice_charm", None),
                                      ("ruby_charm", "氷の護符(活性化済)")):
            item = self.give(session, identifier)
            before = deepcopy(actor["inventory"])
            count = sum(e["kind"] == "item_equipped" for e in session["event_log"])
            text = shops.use_item(session, identifier)
            prefix = f"{previous}を外し、" if previous else ""
            self.assertEqual(text, f"{prefix}{item['name']}を装備した。")
            self.assertEqual(session["system_logs"][-1]["text"], text)
            self.assertEqual(sum(e["kind"] == "item_equipped" for e in session["event_log"]), count + 1)
            self.assertEqual(actor["inventory"], before)
            self.assertIn(item["name"], actor["equipment"])
            if previous:
                self.assertNotIn(previous, actor["equipment"])
            self.assert_slots(actor)
        self.assertEqual(combat._actor_defense(actor), 3)
        self.assertEqual(equipped_basic_attack_followups(actor), [])

    def test_all_equip_on_buy_offers_replace_their_slot(self):
        offers = [(shop, offer) for shop in self.pack["shops"] for offer in shop["items"] if offer.get("equip_on_buy")]
        self.assertTrue(offers)
        for shop, offer in offers:
            session = self.session("mage")
            state.commit_world_position(session, location_id=shop["location_id"])
            session["character"]["gold"] = 1000
            shops.trade(session, shop["id"], offer["item_id"], 1)
            # The tome is an aid, so a bought weapon fills the empty weapon slot instead of replacing it.
            self.assertIn("魔導書", session["character"]["equipment"])
            self.assert_slots(session["character"])
            self.assertNotIn("を外し、", session["system_logs"][-1]["text"])

    def test_story_equip_effects_replace_all_slots(self):
        identifiers = [item["id"] for item in self.pack["items"] if item_slot(item)]
        session = self.session("cleric")
        for identifier in identifiers:
            item = self.give(session, identifier)
            action = {"id": "equip", "effects": [{"equip_item": item["name"]}]}
            state.apply_action_result(session, action, {})
            self.assertIn(item["name"], session["character"]["equipment"])
            self.assert_slots(session["character"])

    def test_no_slot_cannot_equip_but_combat_and_passive_items_still_work(self):
        session = self.session()
        for identifier in ("ice_charm", "shrinking_gun", "frost_seal_charm"):
            item = self.give(session, identifier)
            with self.assertRaises(shops.ShopError):
                shops.use_item(session, identifier)
            state.apply_state_delta(session, {"equip_item": item["name"]})
            self.assertNotIn(item["name"], session["character"]["equipment"])
        gun = next(i for i in session["character"]["inventory"] if i.get("id") == "shrinking_gun")
        self.assertTrue(combat.item_is_combat_usable(gun))
        self.give(session, "fire_seed")
        self.assertEqual(combat._resistance_multiplier(session["character"], "fire"), .5)

    def test_unequipped_modifiers_skills_resistance_and_attacks_are_removed(self):
        session = self.session("cleric")
        actor = session["character"]
        base = deepcopy(actor["combat"]["basic_attack"])
        self.give(session, "cursed_holy_staff")  # an empty weapon slot is filled on pickup
        self.assertIn("呪われた聖杖", actor["equipment"])
        self.assertEqual(combat._player_actions_per_round(session), 2)
        self.give(session, "earth_staff")
        shops.use_item(session, "earth_staff")
        self.assertEqual(combat._player_actions_per_round(session), 1)
        self.assertIsNone(combat._equipped_effect(actor, "healing_harms_humans"))
        self.assertNotEqual(actor["combat"]["basic_attack"], base)
        self.assertNotIn("呪われた聖杖", actor["equipment"])
        heal = effective_ability(actor, {"kind": "heal", "healing": "10"})
        self.assertNotIn("healing_multiplier", heal)
        self.assertEqual(heal["healing"], "10+2")
        self.give(session, "adamantite_armor")
        shops.use_item(session, "adamantite_armor")
        self.assertEqual(effective_ability_cost(actor, {"kind": "heal", "cost": 4, "cost_type": "mp"}), 4)
        for identifier in ("cursed_crystal_ball", "ruby_charm", "activated_ice_charm"):
            self.give(session, identifier)
            shops.use_item(session, identifier)
        self.assertFalse(any(s["id"] == "dark_orb" for s in combat._available_skills(actor)))
        self.assertEqual(combat._resistance_multiplier(actor, "fire"), 1)
        self.assertEqual(len(equipped_item_specs(actor)), 3)

    def test_legacy_save_last_equipped_wins_and_is_persisted(self):
        session = self.session("mage")
        session["scenario_path"] = str(DEFAULT_SCENARIO)
        session["scenario_title"] = self.pack["meta"]["title"]
        session["scenario_pack"]["meta"]["content_revision"] = "2026-10-13-v031"
        old_cloak = next(i for i in session["scenario_pack"]["items"] if i["id"] == "gravekeeper_cloak")
        old_cloak["combat"]["defense"] = 2
        old_cloak["combat"]["conditional_defense"]["amount"] = 1
        session["companion"] = {"id": "robin", "description": "ロビン", "round_start_effects": []}
        for identifier in ("earth_staff", "adamantite_armor", "gravekeeper_cloak", "activated_ice_charm", "ruby_charm", "ice_charm"):
            self.give(session, identifier)
        session["character"]["equipment"] += ["earth_staff", "アダマンタイトの鎧", "gravekeeper_cloak",
                                                "activated_ice_charm", "紅玉の護符", "氷の護符", "魔導書"]
        for item in session["character"]["inventory"]:
            item.pop("slot", None)
        session["character"]["combat"].pop("base_attack", None)
        session["area_snapshots"] = {"forest": {"state": {"character": deepcopy(session["character"])}}}
        with tempfile.TemporaryDirectory() as directory, patch.object(state, "SAVE_DIR", Path(directory)):
            state.save_session(session)
            loaded = state.load_session(session["id"])
            robin = next(c for c in self.pack["companions"] if c["id"] == "robin")
            self.assertEqual(loaded["companion"]["description"], robin["description"])
            self.assertEqual(loaded["companion"]["round_start_effects"], robin["round_start_effects"])
            self.assertEqual(loaded["character"]["equipment"], ["大地の杖", "墓守の外套", "魔導書"])
            self.assertEqual(combat._actor_defense(loaded["character"]), 1)
            cloak = next(i for i in loaded["character"]["inventory"] if i.get("id") == "gravekeeper_cloak")
            self.assertEqual(cloak["combat"]["conditional_defense"]["amount"], 2)
            self.assertEqual(loaded["area_snapshots"]["forest"]["state"]["character"]["equipment"],
                             loaded["character"]["equipment"])
            persisted = json.loads((Path(directory) / f"{session['id']}.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["character"], loaded["character"])
            self.assertEqual(state.load_session(session["id"])["character"], loaded["character"])

    def test_armor_cost_leaves_insufficient_gold_for_charm(self):
        session = self.session()
        state.commit_world_position(session, location_id="forge")
        session["character"]["gold"] = 100
        shops.trade(session, "forge_shop", "adamantite_armor", 1)
        self.assertEqual(session["character"]["gold"], 40)
        with self.assertRaises(shops.ShopError):
            shops.trade(session, "forge_shop", "ice_charm", 1)

    def test_robin_highest_current_hp_alive_stable_tie_and_random_unchanged(self):
        session = self.session()
        robin = next(c for c in self.pack["companions"] if c["id"] == "robin")
        enemies = [dict(id="slime", hp=4, max_hp=100), dict(id="goblin", hp=9, max_hp=10),
                   dict(id="forest_wolf", hp=9, max_hp=30), dict(id="hobgoblin", hp=0, max_hp=50)]
        session["combat"] = {"round": 1, "enemies": enemies}
        rng = Mock(wraps=random.Random(5))
        with patch.object(combat, "_resolve_attack") as attack:
            combat._apply_ally_round_start_effects(session, robin, rng)
            self.assertIs(attack.call_args.args[2], enemies[1])
            self.assertEqual(attack.call_args.args[3]["damage"], "2d4+1")
            rng.choice.assert_not_called()
            enemies[1]["hp"] = 3
            combat._apply_ally_round_start_effects(session, robin, rng)
            self.assertIs(attack.call_args.args[2], enemies[2])
            random_ally = {"round_start_effects": [{"kind": "damage_enemy", "random_target": True}]}
            rng.choice.return_value = enemies[0]
            combat._apply_ally_round_start_effects(session, random_ally, rng)
            rng.choice.assert_called_once_with(enemies[:3])
            self.assertIs(attack.call_args.args[2], enemies[0])
            for enemy in enemies:
                enemy["hp"] = 0
            attack.reset_mock()
            combat._apply_ally_round_start_effects(session, robin, rng)
            attack.assert_not_called()

    def test_robin_opening_kill_commits_rewards_and_exit_once(self):
        from host import app
        from fastapi import HTTPException
        from scripts.playtest.explore import offline_runtime

        with offline_runtime(1):
            session = self.session("cleric")
            state.commit_world_position(session, location_id="goblin_fort_chest_fight")
            state._set_companion(session, "robin")
            encounter = combat._encounter_for_session(session, session["scenario_pack"])
            for enemy in session["scenario_pack"]["enemies"]:
                if enemy["id"] in encounter["enemy_ids"]:
                    enemy.update(hp=1, max_hp=1)
            session["combat_start_requested"] = True
            combat.ensure_combat_started(session)
            self.assertTrue(combat.combat_needs_resolution(session))
            delta = deepcopy(session["combat"]["pending_state_delta"])
            before_gold = session["character"]["gold"]
            state.save_session(session)
            public = app.api_combat_resolve(session["id"])
            self.assertEqual(public["current_location"], delta["current_location"])
            self.assertEqual(public["character"]["gold"], before_gold + delta["gold_change"])
            self.assertTrue(public["choices"])
            with self.assertRaises(HTTPException):
                app.api_combat_resolve(session["id"])
            self.assertEqual(state.load_session(session["id"])["character"]["gold"], public["character"]["gold"])


if __name__ == "__main__":
    unittest.main()
