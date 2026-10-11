from __future__ import annotations

import random
import unittest
from copy import deepcopy
from unittest.mock import patch

from host import combat, free_actions, state
from host.quests import public_quests
from host.shops import ShopError, public_shop, trade
from scripts.balance import checkpoints


class SidequestTests(unittest.TestCase):
    def setUp(self):
        self.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        self.s = checkpoints.fresh_session(deepcopy(self.pack), "hero")

    def at(self, location):
        loc = next(l for l in self.pack["locations"] if l["id"] == location)
        self.s["world_state"] = dict(scene_id=loc["scene_id"], location_id=location)
        self.s.pop("combat_start_requested", None)

    def act(self, aid):
        action = state.resolve_action(self.s, action_id=aid)
        self.assertIsNotNone(action, aid)
        self.assertTrue(state.action_requirement_status(action, self.s)[0], aid)
        return state.apply_action_result(self.s, action, {})

    def observe(self, oid):
        with patch.object(state.random, "randint", return_value=20):
            return free_actions.adjudicate(self.s, dict(kind="interact", operation="observe", target_id=oid, item_id="", advance=False, approach="観察する", reply="", action_id=""))

    def give(self, item_id, quantity=1):
        state.apply_state_delta(self.s, {"inventory_add": [{**next(i for i in self.pack["items"] if i["id"] == item_id), "quantity": quantity}]})

    def quest(self, qid):
        return next(q for q in public_quests(self.s) if q["id"] == qid)

    def test_each_mina_start_and_both_rescue_paths(self):
        for start in ("shop", "tracks", "encounter"):
            for wait in (False, True):
                with self.subTest(start=start, wait=wait):
                    self.setUp()
                    if start == "shop":
                        self.at("magic_shop")
                        self.act("ask_mina_missing")
                        self.assertTrue(self.s["flags"]["heard_seal_lore"])
                        self.assertEqual(self.quest("side_mina")["status"], "active")
                    elif start == "tracks":
                        self.at("elf_spring")
                        self.observe("small_footprints")
                        self.assertEqual(self.quest("side_mina")["status"], "active")
                    self.at("cave_hot_spring")
                    self.act("talk_mina")
                    self.assertEqual(self.quest("side_mina")["status"], "active")
                    if wait:
                        self.act("leave_mina_wait")
                        self.act("hot_spring_forward")
                        checkpoints.replay_step(self.s, "@victory")
                        checkpoints.replay_step(self.s, "@victory")
                        for aid in ("prism_back", "crystal_back", "cave_right"):
                            self.act(aid)
                    self.act("escort_mina")
                    self.assertEqual(self.s["companion"]["id"], "mina")
                    self.at("magic_shop")
                    self.act("report_mina_safe")
                    self.assertIsNone(self.s["companion"])
                    self.assertEqual(self.quest("side_mina")["status"], "completed")
                    self.give("prism_shard")
                    result = self.act("forge_prism_weapon")
                    self.assertEqual(result["result_text"], "「師匠の代わりに私がやります！助けてもらったお礼です」")
                    self.assertEqual(combat._equipped_weapon_attack(self.s["character"])["accuracy"], 95)

    def test_all_moss_sources_delivery_without_request_and_discount(self):
        for source in ("glowing_moss_patch", "battle", "moss_on_wall"):
            for request in (False, True):
                self.setUp()
                if request:
                    self.at("item_shop")
                    self.act("ask_sarah_request")
                    self.assertEqual(self.quest("side_sarah")["status"], "active")
                self.at({"glowing_moss_patch": "elf_spring", "battle": "cave_heat_corridor", "moss_on_wall": "cave_hot_spring"}[source])
                if source == "battle":
                    checkpoints.replay_step(self.s, "@victory")
                else:
                    self.assertEqual(self.observe(source)["outcome"], "success")
                    self.assertNotEqual(self.observe(source)["outcome"], "success")
                self.at("item_shop")
                self.act("give_moss_to_sarah")
                self.assertEqual(self.quest("side_sarah")["status"], "completed")
                self.s["character"]["gold"] = 100
                prices = public_shop(self.s, "sarah_shop")["items"]
                shop = next(s for s in self.pack["shops"] if s["id"] == "sarah_shop")
                for offer, original in zip(prices, shop["items"]):
                    self.assertEqual(offer["price"], int(original["price"] * .8))
                trade(self.s, "sarah_shop", "herb", 2)
                self.assertEqual(self.s["character"]["gold"], 84)

    def test_gald_every_rescue_and_abandonment(self):
        for method in ("battle", "distract_forest_wolves", "sneak_forest_wolves", "abandon_gald"):
            self.setUp()
            self.at("forest_wolves")
            if method == "battle":
                checkpoints.replay_step(self.s, "@victory")
            else:
                with patch.object(state.random, "randint", return_value=20):
                    self.act(method)
            self.assertEqual(state.current_location_id(self.s), "forest_exit")
            self.at("village")
            if method == "abandon_gald":
                self.assertNotIn("saved_gald", self.s["flags"])
                with self.assertRaises(ShopError):
                    public_shop(self.s, "gald_shop")
                self.assertEqual(self.observe("gald_cart")["outcome"], "success")
                self.assertNotEqual(self.observe("gald_cart")["outcome"], "success")
            else:
                self.assertEqual(self.quest("side_gald")["status"], "active")
                self.s["character"]["gold"] = 0
                with self.assertRaises(ShopError):
                    trade(self.s, "gald_shop", "herb", 1)
                self.assertNotIn("visited_gald_shop", self.s["flags"])
                self.s["character"]["gold"] = 100
                self.act("open_gald_shop")
                trade(self.s, "gald_shop", "herb", 1)
                self.assertEqual(self.quest("side_gald")["status"], "completed")
                self.assertEqual(self.observe("gald_cart")["outcome"], "rejected")
                self.at("castle")
                self.act("ask_gald_rumor")
                self.assertTrue(self.s["flags"]["heard_gald_rumor"])

    def test_robert_both_starts_and_already_bought_reward(self):
        for request in (False, True):
            for bought in (False, True):
                self.setUp()
                self.at("forge")
                if request:
                    self.act("ask_robert_hammer")
                    self.assertEqual(self.quest("side_robert")["status"], "active")
                if bought:
                    self.s["character"]["gold"] = 500
                    trade(self.s, "forge_shop", "adamantite_armor", 1)
                    trade(self.s, "forge_shop", "adamantite_armor", 1, selling=True)
                self.at("goblin_fort_fourth")
                checkpoints.replay_step(self.s, "@victory")
                self.assertEqual(self.quest("side_robert")["status"], "active")
                self.at("forge")
                before = self.s["character"]["gold"]
                self.act("return_robert_hammer")
                self.assertEqual(self.quest("side_robert")["status"], "completed")
                self.assertEqual(self.s["character"]["gold"] - before, 100 if bought else 0)
                self.assertEqual("アダマンタイトの鎧" in self.s["character"]["equipment"], not bought)

    def test_gald_rumor_counts_for_accusation(self):
        self.at("castle_report")
        self.give("white_dragon_scale")
        self.s["flags"].update(heard_gald_rumor=True, heard_treaty_lore=True, defeated_ignis=True)
        self.act("report_with_evidence")
        self.assertTrue(self.s["flags"]["draco_revealed"])

    def test_mina_attacks_every_second_round(self):
        self.at("cave_prism_tree")
        self.s["companion"] = deepcopy(next(c for c in self.pack["companions"] if c["id"] == "mina"))
        combat.ensure_combat_started(self.s)
        self.assertFalse(any(e["actor"] == "companion" for e in self.s["combat"]["log"]))
        self.s["combat"]["round"] = 2
        combat._apply_round_start_effects(self.s, random.Random(4))
        log = next(e for e in self.s["combat"]["log"] if e["actor"] == "companion")
        self.assertEqual(log["data"]["element"], "ice")
