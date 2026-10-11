from __future__ import annotations

import json
import random
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import combat, free_actions, state
from host.scenario_context import select_hybrid_prepared_turn
from scripts.balance import checkpoints, route, sim
from scripts.scenario import key_items, redundancy
from scripts.scenario.upgrade_v2 import CLUES


class ScenarioV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cls.manifest = json.loads(redundancy.MANIFEST.read_text(encoding="utf-8"))
        cls.cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))

    def session(self, location="castle", character="hero"):
        session = checkpoints.fresh_session(self.pack, character)
        owner = next(l["scene_id"] for l in self.pack["locations"] if l["id"] == location)
        session["world_state"] = dict(scene_id=owner, location_id=location)
        return session

    def action(self, session, identifier, roll=None):
        action = state.resolve_action(session, action_id=identifier)
        self.assertIsNotNone(action, identifier)
        self.assertTrue(state.action_requirement_status(action, session)[0], identifier)
        return state.apply_action_result(session, action, roll or {})

    def win_draco(self, session):
        combat.ensure_combat_started(session)
        self.assertTrue(combat.combat_is_active(session))
        session["combat"]["enemies"][0]["hp"] = 0
        combat._check_victory_or_defeat(session)
        self.assertTrue(combat.combat_is_active(session))
        self.assertEqual(session["combat"]["enemies"][0]["template_id"], "draco_dragon")
        session["combat"]["enemies"][0]["hp"] = 0
        combat._check_victory_or_defeat(session)
        state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
        self.assertEqual(session["game_over"]["ending"], "draco_defeated")

    def test_phase_preserves_player_and_clears_enemy_status_and_only_final_wins(self):
        session = self.session("draco_battle")
        combat.ensure_combat_started(session)
        session["character"].update(hp=17, mp=3, sp=7)
        session["character"]["statuses"] = [{"id": "fixture"}]
        session["combat"]["player_status"] = {"guard_multiplier": .5}
        actor = deepcopy(session["character"])
        old = session["combat"]["enemies"][0]
        old["hp"] = 0
        old["statuses"] = [{"id": "poison", "damage": "3"}]
        combat._check_victory_or_defeat(session)
        new = session["combat"]["enemies"][0]
        self.assertEqual(new["hp"], new["max_hp"])
        self.assertEqual(new["statuses"], [])
        self.assertEqual(session["character"], actor)
        self.assertEqual(session["combat"]["player_status"], {"guard_multiplier": .5})
        self.assertFalse(combat.combat_needs_resolution(session))
        self.assertFalse(any(k.startswith("defeated_draco") for k in session["flags"]))
        self.assertEqual(session["combat"]["log"][-1]["text"], old["phase_transition_text"])
        public = combat.public_combat(session)["enemies"][0]
        self.assertEqual(public["name"], "白竜ヴァイス")
        self.assertEqual(public["image"], new["image"])
        new["hp"] = 0
        combat._check_victory_or_defeat(session)
        self.assertEqual(session["combat"]["status"], "victory")
        delta = combat.consume_combat_state_delta(session)
        self.assertIn("combat_defeated:draco_battle:draco_human", delta["flags_set"])
        self.assertEqual(combat.consume_combat_state_delta(session), {})

    def test_phase_transition_from_poison_and_companion(self):
        for source in ("poison", "companion"):
            with self.subTest(source=source):
                session = self.session("draco_battle")
                combat.ensure_combat_started(session)
                enemy = session["combat"]["enemies"][0]
                enemy["hp"] = 1
                if source == "poison":
                    enemy["statuses"] = [dict(id="poison", damage="99")]
                else:
                    session["companion"] = dict(name="火コウモリ竜", round_start_effects=[dict(kind="damage_enemy", damage="99", element="fire")])
                combat._apply_round_start_effects(session, random.Random(2))
                self.assertTrue(combat.combat_is_active(session))
                self.assertEqual(session["combat"]["enemies"][0]["template_id"], "draco_dragon")

    def test_defeat_in_either_phase_has_draco_ending(self):
        for phase in (1, 2):
            session = self.session("draco_battle")
            combat.ensure_combat_started(session)
            if phase == 2:
                session["combat"]["enemies"][0]["hp"] = 0
                combat._check_victory_or_defeat(session)
            session["character"]["hp"] = 0
            combat._check_victory_or_defeat(session)
            self.assertEqual(combat.consume_combat_state_delta(session)["game_over"]["ending"], "draco_victory")

    def test_enemy_guard_and_roar(self):
        session = self.session("draco_battle")
        combat.ensure_combat_started(session)
        enemy = session["combat"]["enemies"][0]
        combat._execute_enemy_ability(session, enemy, enemy["skills"][2], random.Random(0))
        self.assertEqual(enemy["statuses"][0]["remaining_rounds"], 3)
        enemy["combat"]["defense"] = 0
        before = enemy["hp"]
        combat._resolve_attack(session, session["character"], enemy, dict(name="攻撃", damage="10", accuracy=100), "player", random.Random(0))
        self.assertEqual(before - enemy["hp"], 6)
        roar = next(e for e in self.pack["enemies"] if e["id"] == "draco_dragon")["skills"][2]
        combat._execute_enemy_ability(session, enemy, roar, random.Random(0))
        session["combat"]["round"] += 1
        session["combat"]["player_status"]["guard_multiplier"] = .25
        session["character"].update(hp=100, max_hp=100, inventory=[], combat={"defense": 0})
        combat._resolve_attack(session, enemy, session["character"], dict(name="攻撃", damage="10", accuracy=100), enemy["id"], random.Random(0))
        self.assertEqual(session["character"]["hp"], 90)

    def test_observe_success_failure_and_once_uses_host_roll_and_ignores_model_reply(self):
        for value, outcome in [(20, "success"), (1, "failure")]:
            session = self.session("ice_elemental_encounter")
            plan = dict(kind="interact", operation="observe", target_id="frost_crystal", item_id="", advance=False, approach="結晶を拾う", reply="白い竜鱗を手に入れた。", action_id="")
            with patch.object(state.random, "randint", return_value=value) as roll:
                result = free_actions.adjudicate(session, plan)
                self.assertEqual(result["outcome"], outcome)
                self.assertNotIn("白い竜鱗", result["text"])
                before = deepcopy(session["character"]["inventory"])
                repeat = free_actions.adjudicate(session, plan)
                roll.assert_called_once()
            self.assertEqual(repeat["text"], "完了済みです。")
            self.assertEqual(session["character"]["inventory"], before)
            crystals = [i for i in before if i.get("id") == "ice_crystal"]
            self.assertEqual(len(crystals), int(value == 20))

    def test_observation_context_does_not_expose_hidden_reward(self):
        session = self.session("castle")
        context = json.loads(free_actions.build_plan_messages(session, "将軍を見る")[1]["content"])
        target = next(o for o in context["objects"] if o["id"] == "general_breath")
        self.assertNotIn("observe_reveals", target)
        self.assertNotIn("noticed_general_frost", json.dumps(target))

    def test_shop_prices_and_forge_resource_payment(self):
        session = self.session("item_shop")
        for aid, price in [("buy_sarah_herb_1", 10), ("buy_sarah_holy_water", 15),
                           ("buy_sarah_ice_charm", 80), ("buy_sarah_fireball_scroll", 40)]:
            session["character"]["gold"] = price - 1
            action = state.resolve_action(session, action_id=aid)
            self.assertFalse(state.action_requirement_status(action, session)[0])
            session["character"]["gold"] = price
            self.action(session, aid)
            self.assertEqual(session["character"]["gold"], 0)
        session = self.session("forge")
        session["character"]["gold"] = 20
        action = state.resolve_action(session, action_id="forge_ice_charm")
        self.assertFalse(state.action_requirement_status(action, session)[0])
        state.apply_state_delta(session, {"inventory_add": [{"id": "ice_crystal", "name": "氷の結晶", "quantity": 1}]})
        self.action(session, "forge_ice_charm")
        self.assertEqual(session["character"]["gold"], 0)
        self.assertFalse(any(i.get("id") == "ice_crystal" for i in session["character"]["inventory"]))
        self.assertTrue(any(i.get("id") == "ice_charm" for i in session["character"]["inventory"]))

    def test_every_scale_source_alone_can_trigger_true_ending(self):
        key = next(k for k in self.manifest["keys"] if k["id"] == "white_dragon_scale")
        for source in key["sources"]:
            with self.subTest(source=source["id"]):
                session, _ = redundancy.replay(self.pack, source["witnesses"]["fort"])
                # Discard all other evidence and retain only this source's one scale.
                session["flags"] = {}
                scale = next(i for i in session["character"]["inventory"] if i.get("id") == "white_dragon_scale")
                session["character"]["inventory"] = [{**scale, "quantity": 1}]
                session["world_state"] = dict(scene_id="castle_return", location_id="castle_report")
                self.action(session, "report_with_evidence")
                self.win_draco(session)

    def test_flag_pairs_single_flag_and_duplicate_count(self):
        for flags in ([CLUES[0], CLUES[1]], [CLUES[2], CLUES[4]]):
            session = self.session("castle_report")
            session["flags"] = dict.fromkeys(flags, True)
            self.action(session, "report_with_evidence")
            self.win_draco(session)
        for flag in CLUES:
            session = self.session("castle_report")
            session["flags"] = {flag: True}
            action = state.resolve_action(session, action_id="report_with_evidence")
            self.assertFalse(state.action_requirement_status(action, session)[0])
            choices = state.annotate_choices_for_session([action], session)
            self.assertFalse(choices[0]["enabled"])
            self.assertFalse(state._session_requirement_passes({"flags_count_gte": {"flags": [flag, flag], "count": 2}}, session))

    def test_evidence_does_not_block_normal_report(self):
        session = self.session("castle_report")
        session["flags"] = dict.fromkeys(CLUES, True)
        self.action(session, "report_normally")
        self.assertEqual(session["game_over"]["ending"], "ignis_defeated")

    def test_normal_ending_reachable_on_each_forest_route(self):
        key = next(k for k in self.manifest["keys"] if k["id"] == "fire_options")
        source = next(s for s in key["sources"] if s["id"] == "core")
        for branch, steps in source["witnesses"].items():
            with self.subTest(branch=branch):
                session, _ = redundancy.replay(self.pack, steps + ["report_normally"])
                self.assertEqual(session["game_over"]["ending"], "ignis_defeated")

    def test_general_high_roll_and_exact_prepared_text(self):
        session = self.session()
        self.action(session, "ask_general_advice", dict(total=18, dc=15, success=True))
        self.assertTrue(session["flags"]["noticed_general_frost"])
        text = select_hybrid_prepared_turn(session)["draft"]["gm_text"]
        self.assertTrue(text.endswith("話し終えた将軍の吐息が、なぜか白く凍っていた。"))
        self.assertEqual(next(i["quantity"] for i in session["character"]["inventory"] if i.get("id") == "holy_water"), 1)

    def test_password_requires_flag_and_robin_automatically_supplies_it(self):
        session = self.session("goblin_fort_third_gate")
        self.assertFalse(state.action_requirement_status(state.resolve_action(session, action_id="give_correct_password"), session)[0])
        session["companion"] = {"id": "robin"}
        session["world_state"]["location_id"] = "goblin_fort_second_right"
        state.apply_state_delta(session, {"current_location": "goblin_fort_third_gate"}, allow_world_transition=True)
        self.assertTrue(session["flags"]["knows_fort_password"])
        self.assertTrue(any(e["kind"] == "location_hint" for e in session["event_log"]))
        self.action(session, "give_correct_password")

    def test_legacy_completed_ignis_save_loads(self):
        session = self.session("dragon_valley_loc")
        session["scenario_pack"] = deepcopy(self.pack)
        session["scenario_pack"]["meta"]["content_revision"] = "2026-10-11-balance-pass3"
        session["scenario_path"] = str(checkpoints.DEFAULT_SCENARIO)
        session["game_over"] = dict(ending="ignis_defeated", reason="冒険完了")
        session["flags"] = {"defeated_ignis": True}
        with tempfile.TemporaryDirectory() as directory, patch.object(state, "SAVE_DIR", Path(directory)):
            Path(directory, "balance.json").write_text(json.dumps(session), encoding="utf-8")
            loaded = state.load_session("balance")
        self.assertEqual(loaded["game_over"]["ending"], "ignis_defeated")

    def test_redundancy_pack_parity_and_negative_mutations(self):
        self.assertEqual(key_items.generate(), self.manifest)
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(filename))
            result = redundancy.check(pack, self.manifest)
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["counts"]["spring"]["white_dragon_scale"], 5)
        manifest = deepcopy(self.manifest)
        key = next(k for k in manifest["keys"] if k["id"] == "white_dragon_scale")
        key["sources"] = key["sources"][:2]
        self.assertTrue(redundancy.check(self.pack, manifest)["errors"])
        pack = deepcopy(self.pack)
        loc = next(l for l in pack["locations"] if l["id"] == "ignis_last_breath")
        loc["actions"][0]["effects"] = []
        self.assertTrue(redundancy.check(pack, self.manifest)["errors"])

    def test_simulation_two_phases_preparation_and_continuous_route(self):
        rows = [sim.simulate(self.pack, "draco_battle", "hero", n=5, seed=8, checkpoints=self.cp, preparation=p)
                for p in ("standard", "no_fire")]
        self.assertIn("draco_dragon", rows[0]["phase_rounds_mean"])
        self.assertIn("紅竜の炎核", rows[0]["consumables_mean"])
        self.assertNotIn("紅竜の炎核", rows[1]["consumables_mean"])
        result = route.simulate_route(self.pack, self.cp, "hero", encounter="draco_battle", n=2, seed=4)
        self.assertEqual(result["route"], "draco_battle")

    def test_section_four_japanese_strings_are_copied_verbatim(self):
        import re
        design = (checkpoints.ROOT / "docs/design/scenario-v2.md").read_text(encoding="utf-8")
        section = design.split("## 4.", 1)[1].split("## 5.", 1)[0]
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            text = checkpoints.DEFAULT_SCENARIO.with_name(name).read_text(encoding="utf-8")
            for line in section.splitlines():
                for label in ("- description：", "- title：", "结果文："):
                    if label in line:
                        sentence = line.split(label, 1)[1].strip()
                        if "（结果文追加" not in line and sentence:
                            self.assertIn(sentence, text, (name, sentence))
            for phrase in re.findall(r"preview：([^｜\n]+)", section):
                self.assertIn(phrase.strip(), text)


if __name__ == "__main__":
    unittest.main()
