from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

from host import area_retry, combat, free_actions, npc_combat, shops, state
from host.scenario_context import current_actions_for_session, fallback_choices_for_session, select_scenario_context
from scripts.balance.checkpoints import fresh_session
from scripts.scenario import npc_combat as migration

app = importlib.import_module("host.app")
ROOT = Path(__file__).resolve().parents[1]


class NpcCombatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(ROOT / "host/prompt/processed/dragon_rpg.json")

    def session(self, location="inn"):
        session = fresh_session(deepcopy(self.pack), "hero")
        state.commit_world_position(session, location_id=location)
        session["needs_opening"] = False
        return session

    def request(self, session, identifier):
        return free_actions.adjudicate(session, dict(kind="interact", action_id="", operation="attack", target_id=identifier,
                                                    item_id="", advance=False, approach="攻撃する", reply=""))

    def settle(self, session, *, killed=None, outcome="victory"):
        for enemy in session["combat"]["enemies"]:
            if killed is None or enemy.get("npc_id") in killed:
                enemy["hp"] = 0
        if outcome == "victory":
            combat._check_victory_or_defeat(session)
        else:
            combat._finish_combat(session, outcome, "戦闘終了")
        delta = combat.consume_combat_state_delta(session)
        state.apply_state_delta(session, delta, allow_world_transition=True)
        combat.clear_combat_after_resolution(session)
        return delta

    def test_protected_categories_exact_text_and_no_confirmation(self):
        for location, identifier, expected in (("castle", "king", "treason"), ("castle", "general", "treason"),
                ("magic_shop", "blue_robed_mage", "warlock"), ("magic_shop", "mina", "mina"),
                ("ruined_watchtower", "old_soldier_ghost", "old_soldier_ghost"),
                ("ignis_purified", "ignis_calm", "generic"), ("xanxus_confrontation", "xanxus", "generic")):
            with self.subTest(identifier=identifier):
                session = self.session(location)
                if identifier == "mina":
                    session["flags"].update(mina_rescued=True, mina_quest_done=True)
                result = self.request(session, identifier)
                if expected == "treason":
                    self.assertEqual(result["outcome"], "confirmation")
                    npc_combat.resolve_confirmation(session, "npc_attack_confirm")
                    self.assertEqual(session["game_over"]["ending"], "treason")
                    self.assertEqual(session["game_over"]["reason"], migration.TREASON[identifier])
                else:
                    self.assertEqual(result["text"], migration.BLOCKED[expected])
                    self.assertNotIn("pending_npc_attack", session)
                self.assertFalse(combat.combat_is_active(session))
                self.assertFalse(session["flags"].get("town_blood"))

    def test_confirmation_and_cancel_are_engine_only_in_both_modes(self):
        for mode in ("full", "semi"):
            for choice in ("npc_attack_confirm", "npc_attack_cancel"):
                with self.subTest(mode=mode, choice=choice):
                    session = self.session()
                    session["gm_mode"] = mode
                    original = [a["id"] for a in current_actions_for_session(session)]
                    self.request(session, "ian")
                    session["choices"] = fallback_choices_for_session(session)
                    public = state.public_session(session)
                    self.assertEqual([a["action_id"] for a in public["choices"]], ["npc_attack_confirm", "npc_attack_cancel"])
                    with patch.object(app, "chat_completion") as llm, patch.object(app, "save_session"):
                        app._run_turn(session, app.TurnRequest(text="", action_id=choice))
                    llm.assert_not_called()
                    self.assertEqual(session["last_turn_metrics"]["model_calls"], 0)
                    self.assertEqual(combat.combat_is_active(session), choice == "npc_attack_confirm")
                    if choice == "npc_attack_cancel":
                        self.assertEqual(session["messages"][-1]["text"], "あなたは武器を下ろした。")
                        self.assertEqual([a["id"] for a in current_actions_for_session(session)], original)

    def test_pending_confirmation_blocks_other_actions_and_inventory(self):
        session = self.session()
        self.request(session, "ian")
        with patch.object(app, "chat_completion") as llm, patch.object(app, "save_session"):
            app._run_turn(session, app.TurnRequest(text="", action_id="return_castle_from_inn"))
        llm.assert_not_called()
        self.assertEqual(state.current_location_id(session), "inn")
        with self.assertRaises(shops.ShopError):
            shops.use_item(session, "herb")

    def test_guardians_and_companion_departure(self):
        for location, target, companion, expected in (("inn", "ian", "robin", ["ian", "robin"]),
                ("item_shop", "sarah", "fire_bat_dragon", ["fire_bat_dragon"]),
                ("oaksdawn_hq", "walter", None, ["walter", "guardian_guard", "guardian_guard"]),
                ("oaksdawn_workshop", "brigitte", None, ["brigitte", "guardian_guard"])):
            session = self.session(location)
            if companion:
                state._set_companion(session, companion)
            self.request(session, target)
            npc_combat.resolve_confirmation(session, "npc_attack_confirm")
            self.assertEqual([e["npc_id"] for e in session["combat"]["enemies"]], expected)
            self.assertIsNone(session["companion"])

    def test_priest_guardian_only_before_liese_recruited(self):
        for recruited in (False, True):
            session = self.session("oaksdawn_chapel")
            session["flags"]["recruited_liese"] = recruited
            self.request(session, "oaksdawn_priest")
            npc_combat.resolve_confirmation(session, "npc_attack_confirm")
            self.assertEqual(len(session["combat"]["enemies"]), 1 if recruited else 2)

    def test_children_flee_and_counter_uses_remaining_stock_without_duplicates(self):
        session = self.session("item_shop")
        session["shop_stock"] = {"sarah_shop": {"herb": 1}}
        self.request(session, "sarah")
        npc_combat.resolve_confirmation(session, "npc_attack_confirm")
        delta = self.settle(session)
        self.assertTrue(npc_combat.gone(session, "sarah"))
        self.assertTrue(npc_combat.gone(session, "fire_bat_dragon"))
        self.assertTrue(session["flags"]["town_blood"])
        self.assertEqual(delta["gold_change"], 30)
        self.assertEqual({i["id"]: i["quantity"] for i in delta["inventory_add"]}, {"herb": 1, "ice_charm": 1, "fireball_scroll": 1})
        with self.assertRaises(shops.ShopError):
            shops.public_shop(session, "sarah_shop")
        self.assertEqual(self.request(session, "sarah")["outcome"], "rejected")
        self.assertEqual([a["id"] for a in current_actions_for_session(session)], ["return_castle_from_item_shop"])

    def test_finite_expensive_counter_stock_not_awarded_twice(self):
        session = self.session("forge")
        session["shop_stock"] = {"forge_shop": {"adamantite_armor": 0, "ice_charm": 1}}
        self.request(session, "blacksmith")
        npc_combat.resolve_confirmation(session, "npc_attack_confirm")
        delta = self.settle(session)
        self.assertEqual([(i["id"], i["quantity"]) for i in delta["inventory_add"]], [("ice_charm", 1)])

    def test_partial_casualties_persist_after_flee(self):
        session = self.session()
        self.request(session, "ian")
        npc_combat.resolve_confirmation(session, "npc_attack_confirm")
        self.settle(session, killed=["ian"], outcome="fled")
        self.assertTrue(npc_combat.gone(session, "ian"))
        self.assertFalse(npc_combat.gone(session, "robin"))
        self.assertTrue(session["flags"]["town_blood"])

    def test_non_town_mina_and_goblin_do_not_set_blood(self):
        for location, target in (("cave_hot_spring", "mina"), ("lost_goblin_crossroads", "lost_goblin")):
            session = self.session(location)
            self.request(session, target)
            npc_combat.resolve_confirmation(session, "npc_attack_confirm")
            self.settle(session)
            self.assertFalse(session["flags"].get("town_blood"))
            self.assertTrue(npc_combat.gone(session, target))
            self.assertTrue(fallback_choices_for_session(session))

    def test_gone_people_hidden_in_all_surfaces_and_stale_checks_rejected(self):
        session = self.session("inn")
        stale = state.resolve_action(session, action_id="robin_archery")
        session["flags"].update(npc_gone_ian=True, npc_gone_robin=True)
        self.assertFalse(state.action_requirement_status(stale, session)[0])
        self.assertIsNone(state.resolve_action(session, action_id="robin_archery"))
        self.assertEqual(state.public_session(session)["location_npc_portraits"], [])
        self.assertEqual(json.loads(free_actions.build_plan_messages(session, "攻撃する")[1]["content"])["npcs"], [])
        self.assertNotIn("ian", [n["id"] for n in select_scenario_context(session)["matched"]["npcs"]])
        state.commit_world_position(session, location_id="ian_ice_katana_aftermath")
        self.assertIsNotNone(state.resolve_action(session, action_id="leave_without_ian"))
        self.assertAbsentProse(select_scenario_context(session)["current_location"]["description"])

    def test_dragon_dialogue_rotation_and_forced_fight(self):
        session = self.session("oaksdawn_wall")
        for index in range(5):
            self.assertEqual(npc_combat.dragon_action(session), migration.DIALOGUE[index % 4])
        session["flags"]["town_blood"] = True
        self.assertNotIn("talk_dragon_knight", [a["action_id"] for a in fallback_choices_for_session(session)])
        with patch.object(app, "chat_completion") as llm, patch.object(app, "save_session"):
            app._run_turn(session, app.TurnRequest(text="", action_id="challenge_dragon_knight"))
        llm.assert_not_called()
        self.assertTrue(combat.combat_is_active(session))
        self.assertFalse(session["combat"]["encounter"]["flee_allowed"])

    def test_interception_both_endings_no_rest_and_skip_after_defeat(self):
        for location in ("ignis_last_breath", "ignis_purified"):
            for defeated in (False, True):
                session = self.session(location)
                session["flags"].update(town_blood=True, dragon_knight_defeated=defeated)
                session["character"].update(hp=8, mp=1, sp=2)
                before = deepcopy(session["character"])
                action = state.resolve_action(session, action_id="return_to_castle_report")
                state.apply_action_result(session, action, {})
                self.assertEqual(state.current_location_id(session), "royal_gate" if defeated else "dragon_valley_return")
                if not defeated:
                    combat.ensure_combat_started(session)
                    self.assertEqual(session["combat"]["intro_text"], migration.INTERCEPTION)
                    self.assertEqual(session["character"]["hp"], before["hp"])
                    self.assertFalse(session["choices"])

    def test_direct_dragon_attack_two_phases_reward_and_disappearance(self):
        session = self.session("oaksdawn_wall")
        self.request(session, "dragon_knight")
        npc_combat.resolve_confirmation(session, "npc_attack_confirm")
        session["combat"]["enemies"][0]["hp"] = 0
        combat._check_victory_or_defeat(session)
        self.assertEqual(session["combat"]["enemies"][0]["template_id"], "dragon_knight_human")
        self.assertEqual(session["combat"]["enemies"][0]["hp"], session["combat"]["enemies"][0]["max_hp"])
        delta = self.settle(session)
        self.assertEqual(delta["gold_change"], 30)
        self.assertEqual(delta["inventory_add"][0]["id"], "grey_dragon_scale")
        self.assertTrue(session["flags"]["dragon_knight_defeated"])
        self.assertFalse(session["flags"].get("town_blood"))
        self.assertFalse(npc_combat.present(session, "dragon_knight"))

    def test_migration_idempotent_and_pack_parity(self):
        results = []
        for name in migration.PACKS:
            pack = json.loads((ROOT / "host/prompt/processed" / name).read_text(encoding="utf-8"))
            before = deepcopy(pack)
            migration.apply(pack)
            self.assertEqual(before, pack)
            results.append(pack)
        self.assertEqual(results[0]["npc_combat"], results[1]["npc_combat"])
        self.assertEqual(results[0]["npcs"], results[1]["npcs"])

    def test_riku_flees_without_ever_becoming_an_enemy(self):
        session = self.session("village")
        session["flags"]["riku_rescued"] = True
        self.assertEqual(self.request(session, "riku")["outcome"], "confirmation")
        npc_combat.resolve_confirmation(session, "npc_attack_confirm")
        self.assertEqual([enemy["npc_id"] for enemy in session["combat"]["enemies"]], ["elder"])
        self.settle(session)
        self.assertTrue(npc_combat.gone(session, "riku"))
        self.assertIsNone(state.resolve_action(session, action_id="return_riku"))

    def test_guard_casualty_sets_blood_even_when_walter_survives(self):
        session = self.session("oaksdawn_hq")
        self.request(session, "walter")
        npc_combat.resolve_confirmation(session, "npc_attack_confirm")
        self.settle(session, killed=["guardian_guard"], outcome="fled")
        self.assertTrue(session["flags"]["town_blood"])
        self.assertFalse(npc_combat.gone(session, "walter"))

    def test_gald_counter_once_and_disappears_from_all_locations(self):
        session = self.session("village")
        session["flags"]["saved_gald"] = True
        self.request(session, "gald")
        npc_combat.resolve_confirmation(session, "npc_attack_confirm")
        self.assertEqual(self.settle(session)["gold_change"], 50)
        for location in ("village", "castle_town", "festival_town", "forest_wolves"):
            state.commit_world_position(session, location_id=location)
            self.assertFalse(npc_combat.present(session, "gald"))
            self.assertEqual(self.request(session, "gald")["outcome"], "rejected")
            self.assertFalse(any(a.get("npc_id") == "gald" for a in current_actions_for_session(session)))
        self.assertIn(migration.EPILOGUE, state._epilogue_lines(session, {"ending": "ignis_defeated"}))

    def assertAbsentProse(self, description):
        # The design lead's final prose replaced every passage that showed the person (FINAL_ABSENCE).
        self.assertTrue(description)
        self.assertFalse([text for text in migration.FINAL_ABSENCE if text in description])

    def test_absent_narratives_portraits_and_exits(self):
        for location, identifiers, exit_id in (
                ("ian_ice_katana_aftermath", ["ian"], "leave_without_ian"),
                ("cave_hot_spring", ["mina"], "hot_spring_back"),
                ("forest_wolves", ["gald"], "wolves_back"),
                ("goblin_fort_chest_choice", ["lost_goblin"], "leave_without_goblin"),
                ("oaksdawn_chapel", ["liese"], "chapel_to_square"),
                ("oaksdawn_inn", ["elio"], "inn_to_square")):
            with self.subTest(location=location):
                session = self.session(location)
                session["flags"].update({f"npc_gone_{identifier}": True for identifier in identifiers})
                context = select_scenario_context(session)
                self.assertAbsentProse(context["current_location"]["description"])
                self.assertIsNotNone(state.resolve_action(session, action_id=exit_id))
                for identifier in identifiers:
                    self.assertNotIn(identifier, [npc["id"] for npc in context["matched"]["npcs"]])
                for choice in context["fallback_choices"]:
                    if choice.get("action_id"):
                        self.assertIsNotNone(state.resolve_action(session, action_id=choice["action_id"]))
        session = self.session("ian_ice_katana_aftermath")
        session["flags"]["npc_gone_ian"] = True
        session["last_action_result"] = {"arrival_portrait_image": "/static/images/npc_ian_serious.png"}
        self.assertEqual(state.public_session(session)["active_portrait_image"], "")

    def test_npc_victory_does_not_resolve_the_locations_monsters(self):
        session = self.session("forest_wolves")
        self.request(session, "gald")
        npc_combat.resolve_confirmation(session, "npc_attack_confirm")
        session["combat"]["enemies"][0]["hp"] = 0
        combat._check_victory_or_defeat(session)
        app._record_obstacle_victory(session)
        self.assertFalse(session.get("scene_changes", {}).get("forest_wolves", {}).get("forest_wolves", {}).get("enemy_defeated"))
        self.assertFalse(session["flags"].get("saved_gald"))

    def test_gone_child_rescue_and_map_descriptions_are_filtered(self):
        from host.maps import public_maps

        session = self.session("burning_house")
        session["flags"]["npc_gone_riku"] = True
        self.assertIsNone(state.resolve_action(session, action_id="douse_with_ice"))
        self.assertIsNotNone(state.resolve_action(session, action_id="leave_burning_house"))
        session = self.session("oaksdawn_chapel")
        session["flags"]["npc_gone_liese"] = True
        session["visited_locations"] = ["oaksdawn_chapel"]
        mapped = json.dumps(public_maps(session), ensure_ascii=False)
        self.assertNotIn("若い女騎士が祈りを捧げている", mapped)
        self.assertIn(migration.FINAL_ABSENCE["高い窓から朝の光が差し込む礼拝堂。祭壇の前で、銀の鎧をまとった若い女騎士が祈りを捧げている。"][1], mapped)

    def test_confirmation_survives_save_reload(self):
        session = self.session()
        self.request(session, "ian")
        with tempfile.TemporaryDirectory(dir=ROOT / ".tmp-test") as temporary, patch.object(state, "SAVE_DIR", Path(temporary)):
            state.save_session(session)
            restored = state.load_session(session["id"])
        self.assertEqual(restored["pending_npc_attack"], session["pending_npc_attack"])
        self.assertEqual([a["id"] for a in current_actions_for_session(restored)], ["npc_attack_confirm", "npc_attack_cancel"])

    def test_combat_result_narrates_once_and_retains_exact_system_prose(self):
        session = self.session("forge")
        self.request(session, "blacksmith")
        with patch.object(app, "save_session"), patch.object(app, "chat_completion") as llm:
            app._run_turn(session, app.TurnRequest(action_id="npc_attack_confirm", text=""))
            llm.assert_not_called()
            session["combat"]["enemies"][0]["hp"] = 0
            combat._check_victory_or_defeat(session)
            llm.return_value = "戦闘が終わった。"
            with patch.object(app, "load_config", return_value={"debug_llm": False}):
                app._run_combat_resolution(session)
            llm.assert_called_once()
        self.assertIn(migration.FALLEN["blacksmith"], [entry["text"] for entry in session["system_logs"]])

    def test_ignores_defense_preserves_resistance_and_guard(self):
        session = self.session("oaksdawn_wall")
        self.request(session, "dragon_knight")
        npc_combat.resolve_confirmation(session, "npc_attack_confirm")
        defender = dict(name="テスト", hp=100, combat={"defense": 100}, resistances={"physical": .5}, statuses=[{"guard_multiplier": .5}])
        attacker = session["combat"]["enemies"][0]
        rng = Mock()
        rng.randint.return_value = 1
        combat._resolve_attack(session, attacker, defender,
                               dict(name="穿竜突き", damage="20", accuracy=100, element="physical", ignores_defense=True),
                               attacker["id"], rng)
        self.assertEqual(defender["hp"], 95)

    def test_dragon_defeat_uses_existing_area_retry(self):
        session = self.session("village")
        session["area_snapshots"] = {}
        session["flags"]["town_blood"] = True
        state.apply_state_delta(session, {"current_location": "valley_entrance"}, allow_world_transition=True)
        state.apply_state_delta(session, {"current_location": "dragon_valley_return"}, allow_world_transition=True)
        combat.ensure_combat_started(session)
        session["character"]["hp"] = 0
        combat._finish_combat(session, "defeat", migration.DEFEAT)
        state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
        self.assertEqual(area_retry.retry_snapshot(session)["location_id"], "valley_entrance")
        area_retry.retry_area(session)
        self.assertEqual(state.current_location_id(session), "valley_entrance")
        self.assertTrue(session["flags"]["town_blood"])
        self.assertFalse(session.get("game_over"))

    def test_prompt_authorized_additions_and_proposed_candidates(self):
        self.assertIn("attack(人物への攻撃。target_id は npcs の ID)", free_actions.PLAN_PROMPT)
        self.assertIn("冗談・脅し・仮定・否定の攻撃は attack にしない。攻撃の意思がはっきりしている時だけ attack。", free_actions.PLAN_PROMPT)
        self.assertNotIn("attack(", free_actions.LEGACY_PLAN_PROMPT)
        candidates = [json.loads(line) for line in (ROOT / "eval/candidates/041-npc-attacks.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(candidates), 24)
        self.assertTrue(all(case["label_status"] == "proposed" and not case["gold"] for case in candidates))


if __name__ == "__main__":
    unittest.main()
