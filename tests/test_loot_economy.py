from __future__ import annotations

import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from host import app, combat, shops, state
from host.quests import public_quests
from scripts.balance import checkpoints
from scripts.balance import loot_economy as budget
from scripts.scenario.loot_economy import BOSSES, LOOT, PACKS, REQUESTS, WARNING, apply

from scripts.scenario.spring_postgame import apply as apply_spring_postgame


class LootEconomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs = [json.loads(checkpoints.DEFAULT_SCENARIO.with_name(name).read_text(encoding="utf-8")) for name in PACKS]

    def session(self, location="item_shop", pack=None):
        session = checkpoints.fresh_session(deepcopy(pack or self.packs[0]), "hero")
        self.move(session, location)
        session["character"]["gold"] = 200
        return session

    def move(self, session, location):
        record = next(loc for loc in session["scenario_pack"]["locations"] if loc["id"] == location)
        session["world_state"] = dict(scene_id=record["scene_id"], location_id=location)

    def give(self, session, identifier, quantity=1):
        item = next(item for item in session["scenario_pack"]["items"] if item["id"] == identifier)
        state.apply_state_delta(session, {"inventory_add": [dict(item, quantity=quantity)]})

    def count(self, session, identifier):
        return sum(i.get("quantity", 1) for i in session["character"]["inventory"] if i.get("id") == identifier)

    def test_each_enemy_fixed_loot_and_boss_quantity_in_both_packs(self):
        for pack in self.packs:
            session = self.session(pack=pack)
            expected = {enemy: (identifier, 2 if enemy in BOSSES else 1)
                        for identifier, (_, _, _, sources) in LOOT.items() for enemy in sources}
            for enemy in pack["enemies"]:
                with self.subTest(pack=pack["meta"]["title"], enemy=enemy["id"]):
                    delta = combat._victory_delta(session, [combat._runtime_enemy(enemy, 0)], {})
                    drops = [(i["id"], i["quantity"]) for i in delta.get("inventory_add", []) if i.get("id") in LOOT]
                    self.assertEqual(drops, [expected[enemy["id"]]] if enemy["id"] in expected else [])
                    original = enemy.get("rewards", {})
                    self.assertEqual(delta.get("gold_change", 0), original.get("gold", 0))
                    self.assertEqual(delta.get("inventory_add", [])[:len(original.get("items", []))], original.get("items", []))

    def test_multiple_enemies_stack_boss_add_has_one_and_rewards_are_consumed_once(self):
        session = self.session("goblin_fort_fourth")
        session["combat_start_requested"] = True
        self.assertTrue(combat.ensure_combat_started(session))
        for enemy in session["combat"]["enemies"]:
            enemy["hp"] = 0
        combat._check_victory_or_defeat(session)
        delta = combat.consume_combat_state_delta(session)
        state.apply_state_delta(session, delta, allow_world_transition=True)
        self.assertEqual(self.count(session, "goblin_trinket"), 3)
        self.assertEqual(session["character"]["gold"], 305)
        state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
        self.assertEqual(self.count(session, "goblin_trinket"), 3)
        self.assertEqual(self.count(session, "elixir_str"), 1)

    def test_scripted_guest_and_defeat_or_flee_do_not_drop_loot(self):
        for kind in ("scripted_loss", "guest"):
            session = self.session()
            enemy = next(e for e in session["scenario_pack"]["enemies"] if e["id"] == "slime")
            delta = combat._victory_delta(session, [enemy], {"encounter_class": kind})
            self.assertFalse(any(i.get("id") in LOOT for i in delta.get("inventory_add", [])))
        for outcome in ("defeat", "fled"):
            session = self.session("dark_forest_loc")
            session["combat_start_requested"] = True
            combat.ensure_combat_started(session)
            combat._finish_combat(session, outcome, "")
            self.assertFalse(any(i.get("id") in LOOT for i in combat.consume_combat_state_delta(session).get("inventory_add", [])))

    def test_explicit_sell_price_ignores_discounts_and_legacy_half_price_stays(self):
        session = self.session()
        self.give(session, "slime_core", 3)
        session["flags"]["sarah_moss_done"] = True
        shop = shops.public_shop(session, "sarah_shop")
        self.assertEqual(next(i["price"] for i in shop["sell_items"] if i["item_id"] == "slime_core"), 3)
        shops.trade(session, "sarah_shop", "slime_core", 2, selling=True)
        self.assertEqual((session["character"]["gold"], self.count(session, "slime_core")), (206, 1))
        self.assertEqual(shops._sell_price(session, {}, {"id": "herb"}), 4)
        self.assertEqual(shops._sell_price(session, {}, {"id": "herb", "sell_price": 0}), 0)
        public = state.public_session(session)
        item = next(i for i in public["character"]["inventory"] if i.get("id") == "slime_core")
        self.assertEqual((item["category"], item["sell_price"]), ("loot", 3))
        self.assertFalse(any(a["type"] == "item" and a["id"] == "slime_core" for a in combat.combat_actions(session)))
        with self.assertRaises(shops.ShopError):
            shops.use_item(session, "slime_core")

    def test_every_buying_shop_accepts_loot_and_workshop_rejects_other_categories(self):
        for pack in self.packs:
            for shop in pack["shops"]:
                if not shop["buys"]:
                    continue
                session = self.session(shop["location_id"], pack)
                session["flags"]["saved_gald"] = True
                for identifier in LOOT:
                    self.give(session, identifier)
                offers = shops.public_shop(session, shop["id"])["sell_items"]
                self.assertTrue(set(LOOT) <= {i["item_id"] for i in offers})
                for identifier in LOOT:
                    shops.trade(session, shop["id"], identifier, 1, selling=True)
                self.assertEqual(session["character"]["gold"], 200 + sum(row[1] for row in LOOT.values()))
        session = self.session("oaksdawn_workshop")
        for identifier in ("herb", "holy_silver", "guardian_chainmail", "white_dragon_scale", "cursed_holy_sword"):
            self.give(session, identifier)
        next(i for i in session["character"]["inventory"] if i.get("id") == "cursed_holy_sword")["non_removable"] = True
        shop_id = "oaksdawn_workshop_shop"
        for identifier in ("herb", "holy_silver", "white_dragon_scale", "cursed_holy_sword"):
            before = deepcopy(session["character"])
            with self.assertRaises(shops.ShopError):
                shops.trade(session, shop_id, identifier, 1, selling=True)
            self.assertEqual(session["character"], before)
        with patch.object(app, "load_session", return_value=session), patch.object(app, "save_session"):
            result = app._shop_trade("fixture", shop_id, app.ShopTradeRequest(item_id="guardian_chainmail", quantity=1), selling=True)
        self.assertIsInstance(result["message"], str)
        self.assertEqual(self.count(session, "guardian_chainmail"), 0)

    def test_sarah_accept_requires_first_request_or_completed_moss(self):
        session = self.session()
        self.assertIsNone(state.resolve_action(session, action_id="accept_sarah_scarf"))
        for flag in ("asked_sarah_request", "sarah_moss_done"):
            session = self.session()
            session["flags"][flag] = True
            checkpoints.replay_step(session, "accept_sarah_scarf")
            self.assertTrue(session["flags"]["accepted_sarah_scarf"])

    def test_collection_accept_threshold_completion_once_and_sale_during_request(self):
        for pack in self.packs:
            for request in REQUESTS:
                with self.subTest(pack=pack["meta"]["title"], quest=request["id"]):
                    session = self.session(request["location"], pack)
                    session["flags"]["asked_sarah_request"] = True
                    deliver = f"deliver_{request['id']}"
                    self.give(session, request["item"], request["quantity"] - 1)
                    self.assertIsNone(state.resolve_action(session, action_id=deliver))
                    checkpoints.replay_step(session, f"accept_{request['id']}")
                    self.assertIsNone(state.resolve_action(session, action_id=deliver))
                    self.give(session, request["item"])
                    self.assertIsNotNone(state.resolve_action(session, action_id=deliver))
                    self.move(session, "item_shop")
                    shops.trade(session, "sarah_shop", request["item"], 1, selling=True)
                    self.move(session, request["location"])
                    self.assertIsNone(state.resolve_action(session, action_id=deliver))
                    self.give(session, request["item"], 2)
                    before_gold = session["character"]["gold"]
                    before_reward = self.count(session, request["reward"])
                    with patch.object(app, "chat_completion", side_effect=AssertionError("LLM called")), patch.object(app, "save_session"):
                        public = app._run_turn(session, app.TurnRequest(text=request["deliver"], action_id=deliver))
                    self.assertEqual(public["messages"][-1]["text"], request["thanks"])
                    self.assertEqual(self.count(session, request["item"]), 1)
                    self.assertEqual(self.count(session, request["reward"]), before_reward + 2)
                    self.assertEqual(session["character"]["gold"], before_gold + request["gold"])
                    self.assertEqual(next(q["status"] for q in public_quests(session) if q["id"] == f"side_{request['id']}"), "completed")
                    self.give(session, request["item"], request["quantity"])
                    self.assertIsNone(state.resolve_action(session, action_id=deliver))
                    self.assertIsNone(state.resolve_action(session, action_id=f"accept_{request['id']}"))

    def test_fort_regroup_and_both_shortcuts_preserve_defeated_floors(self):
        for pack in self.packs:
            for source in ("inn", "lost_goblin_crossroads"):
                session = self.session(source, pack)
                shortcut = f"rush_fort_third_gate_{source}"
                self.assertIsNone(state.resolve_action(session, action_id=shortcut))
                for location in ("goblin_fort", "goblin_fort_first_second", "goblin_fort_second_right"):
                    self.move(session, location)
                    checkpoints.replay_step(session, "@victory")
                self.assertEqual(state.current_location_id(session), "goblin_fort_third_gate")
                retreat = state.resolve_action(session, action_id="regroup_from_fort_third_gate")
                self.assertEqual(state.player_choices_for_session([retreat], session)[0]["risk"], "判定不要")
                checkpoints.replay_step(session, "regroup_from_fort_third_gate")
                self.assertEqual(state.current_location_id(session), "lost_goblin_crossroads")
                before = deepcopy(session["character"])
                self.move(session, source)
                checkpoints.replay_step(session, shortcut)
                self.assertEqual(state.current_location_id(session), "goblin_fort_third_gate")
                self.assertEqual(session["character"], before)
                self.assertFalse(combat.ensure_combat_started(session))
                for location in ("goblin_fort", "goblin_fort_first_second", "goblin_fort_second_right"):
                    self.move(session, location)
                    session["combat_start_requested"] = True
                    self.assertFalse(combat.ensure_combat_started(session))
                self.move(session, source)
                session["flags"]["defeated_goblin_king"] = True
                self.assertIsNone(state.resolve_action(session, action_id=shortcut))

    def test_warning_hp_supply_thresholds_and_no_block(self):
        cases = ((59, 2, True), (60, 2, False), (61, 2, False), (100, 1, True), (0, 0, True))
        actions = (("inn", "accept_robin_goblin_quest", "goblin_fort"),
                   ("lost_goblin_crossroads", "enter_goblin_fort", "goblin_fort"),
                   ("village", "go_dragon_valley", "valley_entrance"),
                   ("festival_town", "go_report_hall", "castle_report"),
                   ("inn", "rush_fort_third_gate_inn", "goblin_fort_third_gate"))
        for location, identifier, destination in actions:
            for hp, supplies, warned in cases:
                session = self.session(location)
                session["flags"].update(recruited_robin=True, lost_goblin_quest=True, fort_third_gate_reached=True)
                actor = session["character"]
                actor.update(max_hp=100, hp=hp, inventory=[])
                for item in ("herb", "healing_scroll")[:supplies]:
                    self.give(session, item)
                checkpoints.replay_step(session, identifier)
                logs = [log for log in state.public_session(session)["system_logs"] if log["text"] == WARNING]
                self.assertEqual(len(logs), int(warned), (identifier, hp, supplies))
                self.assertEqual(state.current_location_id(session), destination)
        session = self.session("village")
        session["character"]["inventory"] = []
        self.give(session, "mp_potion", 2)
        checkpoints.replay_step(session, "go_dragon_valley")
        self.assertNotIn(WARNING, [log["text"] for log in session["system_logs"]])

    def test_apply_idempotent_and_pack_content_synchronized(self):
        for pack in self.packs:
            updated = deepcopy(pack)
            apply(updated)
            apply_spring_postgame(updated)
            from scripts.scenario.levels_skills_v2 import migrate as levels
            updated = levels(updated)
            self.assertEqual(updated, pack)
        for key, identifiers in (("items", set(LOOT)), ("quests", {f"side_{r['id']}" for r in REQUESTS}),
                                 ("shops", {"oaksdawn_workshop_shop"})):
            self.assertEqual([v for v in self.packs[0][key] if v["id"] in identifiers],
                             [v for v in self.packs[1][key] if v["id"] in identifiers])
        self.assertEqual({e["id"]: e.get("loot") for e in self.packs[0]["enemies"]},
                         {e["id"]: e.get("loot") for e in self.packs[1]["enemies"]})

    def test_chapter_budget_counts_only_loot_and_never_sells_it_twice(self):
        session = self.session()
        session["character"]["gold"] = 115
        self.give(session, "goblin_trinket", 2)
        herbs = self.count(session, "herb")
        row = budget.settle(session, 2, 100, 10)
        self.assertEqual((row["cash_change"], row["loot_value"], row["net"], row["ceiling_net"]), (15, 10, 5, 35))
        self.assertEqual(session["character"]["gold"], 105)
        self.assertEqual(self.count(session, "goblin_trinket"), 0)
        self.assertEqual(self.count(session, "herb"), herbs)
        self.assertEqual(budget.settle(session, 3, 105, 0)["net"], -20)

    def test_village_cashflow_cannot_reach_target_at_max_allowed_price(self):
        from scripts.balance import ch3_routes

        pack = self.packs[0]
        template = ch3_routes.starting_checkpoint(pack, checkpoints.generate(), "hero")
        budget.settle(template, 0, template["character"]["gold"], 0)
        result = budget.later_trial(template, "village", "fight", 20261018)
        chapter = next(row for row in result["ledgers"] if row["chapter"] == 3)
        self.assertEqual(chapter["loot"], {"ember_shard": 1})
        self.assertLessEqual(chapter["ceiling_net"], 22)
        self.assertEqual(result["battles"][0]["encounter"], "village_fire_elemental")


if __name__ == "__main__":
    unittest.main()
