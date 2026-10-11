from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from host import app, state
from host.quests import public_quests
from host.shops import ShopError, public_shop, trade, use_item
from scripts.balance import checkpoints, route
from scripts.scenario.upgrade_services import REST_TEXT


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)

    def session(self, location="item_shop"):
        session = checkpoints.fresh_session(deepcopy(self.pack), "hero")
        loc = next(loc for loc in self.pack["locations"] if loc["id"] == location)
        session["world_state"] = dict(scene_id=loc["scene_id"], location_id=location)
        session["character"]["gold"] = 200
        return session

    def give(self, session, item_id, quantity=1):
        item = next(item for item in self.pack["items"] if item["id"] == item_id)
        state.apply_state_delta(session, {"inventory_add": [{**item, "quantity": quantity}]})

    def test_each_quest_visibility_progress_completion_and_failure(self):
        for quest in self.pack["quests"]:
            with self.subTest(quest=quest["id"]):
                session = self.session()
                start = quest["start_flag"]
                self.assertEqual(any(q["id"] == quest["id"] for q in public_quests(session)), not bool(start))
                if start:
                    state.apply_state_delta(session, {"flags_set": [start[0] if isinstance(start, list) else start]})
                for index, stage in enumerate(quest["stages"]):
                    current = next(q for q in public_quests(session) if q["id"] == quest["id"])
                    self.assertEqual(current["current_objective"], stage["text"])
                    self.assertEqual(current["completed_stages"], [s["text"] for s in quest["stages"][:index]])
                    state.apply_state_delta(session, {"flags_set": [stage["done_flag"]]})
                completed = next(q for q in public_quests(session) if q["id"] == quest["id"])
                self.assertEqual(completed["status"], "completed")
                self.assertEqual(completed["current_objective"], "")
                self.assertIn(f"クエスト達成：{quest['title']}", [log["text"] for log in session["system_logs"]])
                for fail in quest["fail_flags"]:
                    state.apply_state_delta(session, {"flags_set": [fail]})
                    failed = next(q for q in public_quests(session) if q["id"] == quest["id"])
                    self.assertEqual(failed["status"], "failed")
                count = len(session["system_logs"])
                state.public_session(session)
                state.apply_state_delta(session, {})
                self.assertEqual(len(session["system_logs"]), count)
                self.assertNotIn("quests", session)

    def test_mystery_any_start_and_clue_count_no_total(self):
        quest = self.pack["quests"][-1]
        for flag in quest["start_flag"]:
            session = self.session()
            session["flags"][flag] = True
            mystery = public_quests(session)[-1]
            self.assertEqual(mystery["id"], "mystery_frost")
            self.assertEqual(mystery["clue_count"], 1)
        state.apply_state_delta(session, {"flags_set": quest["clue_flags"]})
        self.give(session, "white_dragon_scale", 3)
        self.assertEqual(public_quests(session)[-1]["clue_count"], 6)
        self.assertNotIn("clue_flags", public_quests(session)[-1])

    def test_once_flag_and_entry_effect_log_only_once(self):
        session = self.session("inn")
        session["flags"]["recruited_robin"] = True
        checkpoints.replay_step(session, "accept_robin_goblin_quest")
        logs = [log["text"] for log in session["system_logs"]]
        self.assertEqual(logs.count("クエスト更新：義賊ロビンの依頼"), 1)
        session = self.session("village")
        checkpoints.replay_step(session, "go_dragon_valley")
        self.assertEqual(sum(log["text"] == "クエスト更新：紅き邪竜の討伐" for log in session["system_logs"]), 1)

    def test_reports_complete_main_and_old_flags_are_safe(self):
        for action_id in ("report_normally", "report_with_evidence"):
            session = self.session("castle_report")
            session["flags"].update(defeated_ignis=True, reached_village=True, entered_dragon_valley=True,
                                    frost_trace_seen=True, heard_ignis_last_words=True)
            self.give(session, "white_dragon_scale")
            self.assertEqual(public_quests(session)[0]["status"], "active")
            checkpoints.replay_step(session, action_id)
            self.assertTrue(session["flags"]["reported_to_king"])
            self.assertEqual(public_quests(session)[0]["status"], "completed")

    def test_rest_cost_and_exact_result_without_llm(self):
        session = self.session("inn")
        session["character"].update(gold=9, hp=1, mp=0, sp=0)
        with self.assertRaises(ValueError):
            checkpoints.replay_step(session, "rest_at_inn")
        self.assertEqual(session["character"]["hp"], 1)
        session["character"]["gold"] = 10
        with patch.object(app, "chat_completion", side_effect=AssertionError("LLM called")), patch.object(app, "save_session"):
            result = app._run_turn(session, app.TurnRequest(text="宿で休む（10G）", action_id="rest_at_inn"))
        self.assertEqual(result["messages"][-1]["text"], REST_TEXT)
        self.assertEqual(session["character"]["gold"], 0)
        for resource in ("hp", "mp", "sp"):
            self.assertEqual(session["character"][resource], session["character"][f"max_{resource}"])

    def test_optional_paid_rest_in_route(self):
        def fight(session, policy, rng):
            return {"encounter": "inn", "continue": True, "status": "victory"}
        for enabled, expected in ((False, 0), (True, 1)):
            session = self.session("inn")
            session["character"].update(hp=1, gold=10)
            with patch.object(checkpoints, "fresh_session", return_value=session), patch.object(route, "fight", side_effect=fight):
                result = route.trial(self.pack, [], "inn", "hero", 1, rest_at_inn=enabled)
            self.assertEqual(result["paid_rests"], expected)
            self.assertEqual(session["character"]["gold"], 10 - expected * 10)

    def test_item_healing_is_capped_and_full_refuses_without_consumption(self):
        for item_id, resource in (("herb", "hp"), ("mp_potion", "mp")):
            session = self.session()
            self.give(session, item_id)
            actor = session["character"]
            actor[resource] = actor[f"max_{resource}"] - 3
            message = use_item(session, item_id)
            self.assertIn(f"{resource.upper()}が3回復した。", message)
            before = deepcopy(actor)
            self.give(session, item_id)
            before = deepcopy(actor)
            with self.assertRaisesRegex(ShopError, "これ以上回復する必要はない。"):
                use_item(session, item_id)
            self.assertEqual(actor, before)

    def test_items_and_shops_reject_combat_ending_and_wrong_location(self):
        for field, value in (("combat", {"status": "active"}), ("combat", {"status": "victory"}),
                             ("game_over", {"reason": "敗北"}), ("combat_start_requested", True)):
            session = self.session()
            session[field] = value
            for operation in (lambda: use_item(session, "herb"), lambda: public_shop(session, "sarah_shop"),
                              lambda: trade(session, "sarah_shop", "herb", 1)):
                with self.assertRaises(ShopError):
                    operation()
        with self.assertRaises(ShopError):
            public_shop(self.session("inn"), "sarah_shop")
        for item_id in ("iron_sword", "fireball_scroll", "absent"):
            session = self.session()
            if item_id == "fireball_scroll":
                self.give(session, item_id)
            with self.assertRaises(ShopError):
                use_item(session, item_id)

    def test_buy_stock_money_quantity_and_sell_prices(self):
        session = self.session()
        trade(session, "sarah_shop", "herb", 3)
        self.assertEqual(session["character"]["gold"], 170)
        self.assertEqual(session["shop_stock"]["sarah_shop"]["herb"], 0)
        for item, qty in (("herb", 1), ("holy_water", 100), ("absent", 1), ("holy_water", 0),
                          ("holy_water", -1), ("holy_water", True), ("holy_water", 1.5)):
            before = deepcopy(session)
            with self.assertRaises(ShopError):
                trade(session, "sarah_shop", item, qty)
            self.assertEqual(session, before)
        trade(session, "sarah_shop", "herb", 2, selling=True)
        self.assertEqual(session["character"]["gold"], 180)
        trade(session, "sarah_shop", "holy_water", 1)
        trade(session, "sarah_shop", "holy_water", 1, selling=True)
        self.assertEqual(session["character"]["gold"], 172)
        self.give(session, "rusted_crown")
        trade(session, "sarah_shop", "rusted_crown", 1, selling=True)
        self.assertEqual(session["character"]["gold"], 177)
        self.assertEqual(session["shop_stock"]["sarah_shop"]["herb"], 0)
        self.assertIsNone(session["shop_stock"]["sarah_shop"]["holy_water"])

    def test_key_items_not_sellable_and_purchase_requirements_preserved(self):
        session = self.session()
        for item_id in ("white_dragon_scale", "red_dragon_core", "fire_seed"):
            self.give(session, item_id)
            before = deepcopy(session["character"])
            with self.assertRaises(ShopError):
                trade(session, "sarah_shop", item_id, 1, selling=True)
            self.assertEqual(session["character"], before)
        self.assertFalse(any(item.get("key_item") for item in public_shop(session, "sarah_shop")["sell_items"]))
        session = self.session("forge")
        session["character"]["attributes"]["end"] = 7
        with self.assertRaises(ShopError):
            trade(session, "forge_shop", "adamantite_armor", 1)
        session["character"]["attributes"]["end"] = 8
        trade(session, "forge_shop", "adamantite_armor", 1)
        session = self.session("magic_shop")
        trade(session, "magic_shop", "earth_staff", 1)
        self.assertIn("大地の杖", session["character"]["equipment"])

    def test_save_reload_stock_and_legacy_pack_refresh(self):
        session = self.session()
        with tempfile.TemporaryDirectory() as directory, patch.object(state, "SAVE_DIR", Path(directory)):
            trade(session, "sarah_shop", "herb", 2)
            state.save_session(session)
            loaded = state.load_session(session["id"])
            self.assertEqual(public_shop(loaded, "sarah_shop")["items"][0]["stock"], 1)
            loaded.pop("shop_stock")
            loaded["scenario_path"] = str(checkpoints.DEFAULT_SCENARIO)
            loaded["scenario_pack"]["meta"]["content_revision"] = "2026-10-12-scenario-v2"
            loaded["scenario_pack"].pop("shops")
            loaded["scenario_pack"].pop("quests")
            state.save_session(loaded)
            legacy = state.load_session(session["id"])
            self.assertEqual(public_shop(legacy, "sarah_shop")["items"][0]["stock"], 3)
            self.assertEqual(state.public_session(legacy)["quests"][0]["status"], "active")

    def test_api_validation_no_llm_and_open_shop_existing(self):
        session = self.session()
        session["character"]["hp"] = 1
        with patch.object(app, "load_session", return_value=session), \
                patch.object(app, "save_session"), patch.object(app, "chat_completion", side_effect=AssertionError("LLM called")):
            self.assertEqual(app.api_get_shop("balance", "sarah_shop")["id"], "sarah_shop")
            for qty in (0, -1, True, "1", 1.5):
                with self.assertRaises(ValidationError):
                    app.ShopTradeRequest(item_id="herb", quantity=qty)
            request = app.ShopTradeRequest(item_id="herb", quantity=1)
            self.assertIn("shop", app.api_buy("balance", "sarah_shop", request))
            self.assertIn("shop", app.api_sell("balance", "sarah_shop", request))
            self.assertIn("message", app.api_use_item("balance", app.ItemUseRequest(item_id="herb")))
            result = app.api_turn("balance", app.TurnRequest(text="店に入る", action_id="open_sarah_shop"))
            self.assertEqual(result["last_action_result"]["open_shop"], "sarah_shop")
        plan = dict(kind="existing", action_id="open_sarah_shop", operation="", target_id="", item_id="", advance=False, approach="", reply="")
        with patch.object(app, "chat_completion", return_value=json.dumps(plan)), patch.object(app, "save_session"):
            result = app._run_free_turn(session, app.TurnRequest(text="薬草を買いたい"))
        self.assertEqual(result["last_action_result"]["open_shop"], "sarah_shop")

    def test_two_packs_service_data_and_no_purchase_children(self):
        other = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name("dragon_rpg_hybrid.json"))
        for key in ("quests", "shops"):
            self.assertEqual(self.pack[key], other[key])
        for pack in (self.pack, other):
            for location in pack["locations"]:
                ids = {action["id"] for action in state._iter_actions(location.get("actions", []))}
                self.assertFalse(ids & {"sarah_shop", "blue_mage_shop", "buy_equipment", "buy_ice_amulet"})
            self.assertEqual(len(pack["quests"]), 5)
            self.assertEqual(len(pack["shops"]), 4)


if __name__ == "__main__":
    unittest.main()
