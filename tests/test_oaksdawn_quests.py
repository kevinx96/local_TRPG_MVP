from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import combat, shops, state
from host.item_mechanics import effective_ability, equipped_items, steal_reward
from host.quests import public_quests
from host.scenario_context import select_scenario_context
from scripts.balance.checkpoints import DEFAULT_SCENARIO, fresh_session
from scripts.balance import dawn
from scripts.scenario.oaksdawn_quests import BELL_REQUEST, BELL_TEXT, FOG_TEXT, LIESE_THANKS, WEAPONS, apply


class OaksdawnQuestsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(DEFAULT_SCENARIO)

    def session(self, location="oaksdawn_workshop", character="hero"):
        session = fresh_session(deepcopy(self.pack), character)
        self.move(session, location)
        return session

    def move(self, session, location):
        state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)

    def resolve(self, session, identifier):
        action = state.resolve_action(session, action_id=identifier)
        self.assertIsNotNone(action, identifier)
        self.assertTrue(state.action_requirement_status(action, session)[0], identifier)
        return state.apply_action_result(session, action, {})

    def give(self, session, identifier, quantity=1):
        item = next(i for i in self.pack["items"] if i["id"] == identifier)
        state.apply_state_delta(session, {"inventory_add": [{**item, "quantity": quantity}]})

    def quantity(self, session, identifier):
        return sum(i["quantity"] for i in session["character"]["inventory"] if i.get("id") == identifier)

    def choices(self, session):
        choices = state.annotate_choices_for_session(state.fallback_choices_for_session(session), session)
        return {c["action_id"]: c for c in state.player_choices_for_session(choices, session)
                if c.get("action_id")}

    def victory(self, session):
        encounter = state._current_location_record(session)["combat"]
        enemies = [next(e for e in session["scenario_pack"]["enemies"] if e["id"] == identifier)
                   for identifier in encounter["enemy_ids"]]
        delta = combat._victory_delta(session, enemies, encounter)
        state.apply_state_delta(session, delta, allow_world_transition=True)
        return delta

    def test_silver_combat_drop_after_fruit_once_not_from_passing_or_stealing(self):
        for stolen in (False, True):
            session = self.session("grave_chapel")
            if stolen:
                delta, _ = steal_reward(session, "grave_chapel")
                state.apply_state_delta(session, delta)
                self.assertEqual(self.quantity(session, "holy_silver"), 0)
            delta = self.victory(session)
            self.assertEqual([item["name"] for item in delta["inventory_add"][-2:]], ["聖銀", "錆びた兵士の徽章"])
            self.assertEqual(self.quantity(session, "holy_silver"), 1)
            self.victory(session)
            self.assertEqual(self.quantity(session, "holy_silver"), 1)
        session = self.session("grave_chapel")
        self.give(session, "cursed_holy_sword")
        self.resolve(session, "curse_pass_grave_knight")
        self.assertEqual(self.quantity(session, "holy_silver"), 0)
        self.assertIn("ring_battlefield_bell", self.choices(session))

    def test_silver_shop_cost_material_and_craft_visibility(self):
        session = self.session()
        self.assertNotIn("forge_dawn_weapon", self.choices(session))
        session["character"]["gold"] = 119
        with self.assertRaises(shops.ShopError):
            shops.trade(session, "oaksdawn_workshop_shop", "holy_silver", 1)
        session["character"]["gold"] = 120
        shops.trade(session, "oaksdawn_workshop_shop", "holy_silver", 1)
        self.assertEqual(session["character"]["gold"], 0)
        item = shops._owned(session, "holy_silver")
        self.assertEqual(item["category"], "material")
        self.assertFalse(item.get("key_item"))
        self.assertFalse(self.choices(session)["forge_dawn_weapon"]["enabled"])
        session["character"]["gold"] = 30
        self.assertTrue(self.choices(session)["forge_dawn_weapon"].get("enabled", True))

    def test_four_weapons_cost_once_and_replace_only_weapon(self):
        for character, (identifier, name, damage, accuracy, _) in WEAPONS.items():
            with self.subTest(character=character):
                session = self.session(character=character)
                self.give(session, "ice_katana")
                state._equip_inventory_item(session, "ice_katana")
                other = [i["name"] for i in equipped_items(session["character"]) if i["slot"] != "weapon"]
                self.give(session, "holy_silver", 2)
                session["character"]["gold"] = 100
                self.resolve(session, "forge_dawn_weapon")
                self.assertEqual(self.quantity(session, "holy_silver"), 1)
                self.assertEqual(session["character"]["gold"], 70)
                self.assertEqual(self.quantity(session, identifier), 1)
                self.assertEqual(self.quantity(session, "ice_katana"), 1)
                self.assertCountEqual(session["character"]["equipment"], [*other, name])
                attack = session["character"]["combat"]["basic_attack"]
                self.assertEqual((attack["damage"], attack["accuracy"], attack["element"]), (damage, accuracy, "holy"))
                self.assertNotIn("forge_dawn_weapon", self.choices(session))
                heal = effective_ability(session["character"], dict(kind="heal", healing="10"))
                shops.use_item(session, "ice_katana")
                after = effective_ability(session["character"], dict(kind="heal", healing="10"))
                if character == "cleric":
                    self.assertEqual(heal["healing"], "10+4")  # Existing aid +2 and dawn weapon +2.
                    self.assertEqual(after["healing"], "10+2")
                else:
                    self.assertEqual(heal, after)

    def test_bell_acceptance_and_both_report_locations_share_one_reward(self):
        for report in ("chapel", "hq"):
            session = self.session("oaksdawn_chapel")
            self.assertNotIn("ask_battlefield_bell", self.choices(session))
            self.resolve(session, "talk_liese")
            self.resolve(session, "ask_battlefield_bell")
            self.assertNotIn("ask_battlefield_bell", self.choices(session))
            self.assertEqual(next(q for q in public_quests(session) if q["id"] == "side_battlefield_bell")["status"], "active")
            self.move(session, "grave_chapel")
            self.assertNotIn("ring_battlefield_bell", self.choices(session))
            self.give(session, "cursed_holy_sword")
            self.resolve(session, "curse_pass_grave_knight")
            self.assertEqual(self.resolve(session, "ring_battlefield_bell")["result_text"], BELL_TEXT)
            self.assertNotIn("ring_battlefield_bell", self.choices(session))
            self.move(session, f"oaksdawn_{report}")
            gold = session["character"]["gold"]
            self.resolve(session, f"report_battlefield_bell_{report}")
            self.assertEqual(session["character"]["gold"], gold + 100)
            self.assertEqual(self.quantity(session, "holy_silver"), 1)
            self.assertEqual(self.quantity(session, "guardian_small_shield"), 1)
            for other in ("chapel", "hq"):
                self.move(session, f"oaksdawn_{other}")
                self.assertNotIn(f"report_battlefield_bell_{other}", self.choices(session))
            self.assertEqual(next(q for q in public_quests(session) if q["id"] == "side_battlefield_bell")["status"], "completed")

    def test_liese_auto_accepts_once_and_thanks_but_cannot_receive_chapel_report(self):
        session = self.session("ghoul_marsh")
        state._set_companion(session, "paladin_liese")
        state.apply_state_delta(session, {"flags_set": ["passed_ghoul_marsh"]})
        result = self.resolve(session, "marsh_to_chapel")
        self.assertIn(BELL_REQUEST, result["result_text"])
        self.assertTrue(session["flags"]["accepted_battlefield_bell"])
        self.move(session, "ghoul_marsh")
        self.assertNotIn(BELL_REQUEST, self.resolve(session, "marsh_to_chapel")["result_text"])
        self.victory(session)
        self.assertIn(LIESE_THANKS, self.resolve(session, "ring_battlefield_bell")["result_text"])
        self.move(session, "oaksdawn_chapel")
        self.assertNotIn("report_battlefield_bell_chapel", self.choices(session))
        self.move(session, "oaksdawn_hq")
        self.resolve(session, "report_battlefield_bell_hq")

    def test_bell_description_and_unfinished_fixed_encounters_unchanged(self):
        session = self.session("grave_chapel")
        before = {loc["id"]: deepcopy(loc["combat"]) for loc in session["scenario_pack"]["locations"]
                  if loc["id"] in {"bone_field", "ghoul_marsh"}}
        state.apply_state_delta(session, {"flags_set": ["passed_grave_chapel"]})
        self.resolve(session, "ring_battlefield_bell")
        self.move(session, "oaksdawn_wall")
        self.assertIn(FOG_TEXT, self.resolve(session, "oaksdawn_to_battlefield")["result_text"])
        self.assertIn(FOG_TEXT, select_scenario_context(session)["current_location"]["description"])
        self.assertEqual(state._current_location_record(session)["combat"]["enemy_ids"], [])
        for location, encounter in before.items():
            self.move(session, location)
            self.assertEqual(state._current_location_record(session)["combat"], encounter)
            self.assertFalse(session["flags"].get(f"passed_{location}"))

    def test_lava_stone_sources_once_independent_of_elite_fruit_and_acceptance(self):
        session = self.session("cave_lava_room")
        result = self.resolve(session, "pick_baked_lava_stone")
        self.assertEqual(result["roll"], {})
        self.assertEqual(self.quantity(session, "baked_lava_stone"), 1)
        self.assertNotIn("pick_baked_lava_stone", self.choices(session))
        self.move(session, "valley_ledge")
        session["flags"]["elite_fruit_claimed:dragon_valley"] = True
        self.victory(session)
        self.assertEqual(self.quantity(session, "baked_lava_stone"), 2)
        self.move(session, "valley_ledge")
        self.victory(session)
        self.assertEqual(self.quantity(session, "baked_lava_stone"), 2)

    def test_hearth_reforges_current_armor_once_persists_after_swap_and_save_load(self):
        session = self.session()
        self.assertNotIn("ask_workshop_hearth", self.choices(session))
        self.resolve(session, "talk_brigitte")
        self.resolve(session, "ask_workshop_hearth")
        self.assertNotIn("ask_workshop_hearth", self.choices(session))
        delivery = state.resolve_action(session, action_id="deliver_baked_lava_stone")
        self.assertFalse(state.action_requirement_status(delivery, session)[0])
        self.give(session, "baked_lava_stone", 2)
        self.give(session, "adamantite_armor", 2)
        shops.use_item(session, "adamantite_armor")
        self.resolve(session, "deliver_baked_lava_stone")
        upgraded = shops._owned(session, "adamantite_armor_reforged")
        self.assertEqual((upgraded["name"], upgraded["slot"], upgraded["quantity"]), ("アダマンタイトの鎧＋", "armor", 1))
        self.assertEqual(combat._actor_defense(session["character"]), 4)
        self.assertEqual(self.quantity(session, "adamantite_armor"), 1)
        self.assertEqual(self.quantity(session, "baked_lava_stone"), 1)
        self.assertNotIn("deliver_baked_lava_stone", self.choices(session))
        shops.use_item(session, "adamantite_armor")
        self.assertEqual(combat._actor_defense(session["character"]), 3)
        shops.use_item(session, upgraded["id"])
        self.assertEqual(combat._actor_defense(session["character"]), 4)
        session["scenario_path"] = str(DEFAULT_SCENARIO)
        session["scenario_title"] = self.pack["meta"]["title"]
        with tempfile.TemporaryDirectory() as directory, patch.object(state, "SAVE_DIR", Path(directory)):
            state.save_session(session)
            loaded = state.load_session(session["id"])
            self.assertEqual(shops._owned(loaded, upgraded["id"]), upgraded)
            self.assertEqual(combat._actor_defense(loaded["character"]), 4)
            self.assertNotIn("deliver_baked_lava_stone", self.choices(loaded))
        self.assertEqual(next(q for q in public_quests(session) if q["id"] == "side_workshop_hearth")["status"], "completed")

    def test_no_equipped_armor_gets_unmodified_chainmail(self):
        session = self.session()
        session["character"]["equipment"] = ["鉄の剣"]
        self.resolve(session, "talk_brigitte")
        self.resolve(session, "ask_workshop_hearth")
        self.give(session, "baked_lava_stone")
        self.resolve(session, "deliver_baked_lava_stone")
        self.assertIn("守護団の鎖帷子", session["character"]["equipment"])
        self.assertEqual(combat._actor_defense(session["character"]), 2)

    def test_reforged_robe_keeps_passive_and_shield_replaces_existing_aid(self):
        session = self.session(character="cleric")
        self.resolve(session, "talk_brigitte")
        self.resolve(session, "ask_workshop_hearth")
        self.give(session, "baked_lava_stone")
        self.resolve(session, "deliver_baked_lava_stone")
        robe = next(i for i in session["character"]["inventory"] if i["name"] == "ローブ＋")
        self.assertEqual(robe["combat"]["cost_reduction"], {"mp": 1})
        self.assertEqual(robe["combat"]["applies_to"], ["heal"])
        self.assertIn("被ダメージを1軽減", robe["effect"])
        self.assertEqual(combat._actor_defense(session["character"]), 1)
        self.give(session, "guardian_small_shield")
        shops.use_item(session, "guardian_small_shield")
        self.assertNotIn("聖なる杖", session["character"]["equipment"])
        self.assertEqual(combat._actor_defense(session["character"]), 2)
        state._equip_inventory_item(session, "聖なる杖")
        self.assertEqual(combat._actor_defense(session["character"]), 1)

    def test_weapon_trials_repeat_without_mutating_template(self):
        session = self.session("grave_chapel")
        before = deepcopy(session)
        upgraded = dawn.equip(session, "dawn_sword")
        first = dawn.trial(upgraded, 34)
        self.assertEqual(first, dawn.trial(upgraded, 34))
        self.assertIn(first["status"], {"victory", "defeat"})
        self.assertEqual(session, before)
        self.assertGreater(dawn.basic_estimates(upgraded, "grave_chapel")["grave_knight"],
                           dawn.basic_estimates(session, "grave_chapel")["grave_knight"])
        self.assertIn("ignis", dawn.basic_estimates(self.session("dragon_valley_loc"), "dragon_valley_loc"))

    def test_icons_optional_and_both_packs_synchronized_idempotent(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = json.loads(DEFAULT_SCENARIO.with_name(filename).read_text(encoding="utf-8"))
            original = deepcopy(pack)
            apply(pack)
            self.assertEqual(pack, original)
            reference = json.loads(DEFAULT_SCENARIO.read_text(encoding="utf-8"))
            self.assertEqual({i["id"]: i["icon"] for i in pack["items"]},
                             {i["id"]: i["icon"] for i in reference["items"]})
            self.assertTrue(all(i.get("icon") for i in pack["items"]))
            session = fresh_session(pack, "hero")
            self.give(session, "holy_silver")
            public = state.public_session(session)
            silver = next(i for i in public["character"]["inventory"] if i.get("id") == "holy_silver")
            self.assertEqual(silver["icon"], "/static/images/icon_holy_silver.png")
            self.assertEqual(public["character"]["inventory"][0]["icon"], "/static/images/icon_iron_sword.png")
            self.assertNotIn("icon", state._enrich_item({"name": "鉄の剣"}))


if __name__ == "__main__":
    unittest.main()
