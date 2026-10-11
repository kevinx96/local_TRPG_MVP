from __future__ import annotations

import json
import random
import re
import unittest
from copy import deepcopy
from unittest.mock import patch

from host import combat, state
from host import app
from host.quests import public_quests
from host.scenario_context import select_hybrid_prepared_turn
from scripts.balance import checkpoints, route, sim
from scripts.scenario import key_items, redundancy, upgrade_purification


class PurificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cls.manifest = json.loads(redundancy.MANIFEST.read_text(encoding="utf-8"))
        cls.cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))

    def session(self, character="hero", location="dragon_valley_loc", pack=None):
        session = checkpoints.fresh_session(pack or self.pack, character)
        owner = next(l["scene_id"] for l in session["scenario_pack"]["locations"] if l["id"] == location)
        session["world_state"] = dict(scene_id=owner, location_id=location)
        return session

    def give(self, session, item_id, quantity=1):
        item = next(i for i in self.pack["items"] if i["id"] == item_id)
        state.apply_state_delta(session, {"inventory_add": [{**item, "quantity": quantity}]})

    def start(self, session, ratio=.4):
        self.assertTrue(combat.ensure_combat_started(session))
        enemy = session["combat"]["enemies"][0]
        enemy["hp"] = enemy["max_hp"] * ratio

    def specials(self, session):
        return [a["id"] for a in combat.combat_actions(session) if a["type"] == "special"]

    def resolve(self, session):
        state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
        combat.clear_combat_after_resolution(session)

    def action(self, session, aid):
        checkpoints.replay_step(session, aid)

    def purify(self, character="hero"):
        session = self.session(character)
        session["flags"]["frost_trace_seen"] = True
        self.give(session, "holy_water")
        self.start(session)
        combat.perform_combat_action(session, "special", "purify_ignis_holy_water")
        self.resolve(session)
        return session

    def test_every_actual_knowledge_source_with_both_means_in_both_packs(self):
        knowledge = next(k for k in self.manifest["keys"] if k["id"] == "purification_knowledge")
        scales = next(k for k in self.manifest["keys"] if k["id"] == "white_dragon_scale")
        sources = [*knowledge["sources"], next(s for s in scales["sources"] if s["id"] == "frost_core")]
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(filename))
            for source in sources:
                for character, action in [("hero", "purify_ignis_holy_water"), ("cleric", "purify_ignis_prayer")]:
                    with self.subTest(pack=filename, source=source["id"], character=character):
                        steps = source["witnesses"]["spring"]
                        # Stop immediately after this source, retaining only its knowledge.
                        _, all_events = redundancy.replay(pack, steps, character)
                        end = next(i + 1 for i, e in enumerate(all_events)
                                   if (e["location"], e["step"]) == (source["location"], source["step"]))
                        acquired, events = redundancy.replay(pack, steps[:end], character)
                        self.assertTrue(redundancy.grants(events[-1]["delta"], source["reward"]))
                        session = self.session(character, pack=pack)
                        session["character"]["inventory"] = []
                        reward = source["reward"]
                        if "flag" in reward:
                            session["flags"] = {reward["flag"]: True}
                        else:
                            self.give(session, "white_dragon_scale")
                        if character == "hero":
                            self.give(session, "holy_water")
                        session["character"]["mp"] = 6
                        self.start(session)
                        self.assertEqual(self.specials(session), [action])
                        combat.perform_combat_action(session, "special", action)
                        self.assertEqual(session["combat"]["status"], "purified")
                        self.resolve(session)
                        self.assertEqual(state.current_location_id(session), "ignis_purified")

    def test_missing_conditions_hidden_and_forged_request_rejected_without_cost(self):
        for missing in ("knowledge", "means", "hp", "mp", "class"):
            session = self.session("cleric" if missing == "mp" else "hero")
            session["character"]["inventory"] = []
            session["flags"] = {} if missing == "knowledge" else {"frost_trace_seen": True}
            if missing not in {"means", "mp", "class"}:
                self.give(session, "holy_water")
            session["character"]["mp"] = 5 if missing == "mp" else 6
            if missing == "mp":
                session["character"]["inventory"] = [{"name": "大地の杖", "quantity": 1,
                                                       "combat": {"cost_reduction": {"mp": 99}}}]
                session["character"]["equipment"] = ["大地の杖"]
            self.start(session)
            if missing == "hp":
                session["combat"]["enemies"][0]["hp"] += 1
            before = deepcopy(session)
            self.assertEqual(self.specials(session), [], missing)
            for aid in ("purify_ignis_holy_water", "purify_ignis_prayer", "unknown"):
                with self.assertRaises(combat.CombatError):
                    combat.perform_combat_action(session, "special", aid)
                self.assertEqual(session, before)

    def test_cleric_both_costs_and_purification_does_not_grant_rewards(self):
        for aid in ("purify_ignis_holy_water", "purify_ignis_prayer"):
            session = self.session("cleric")
            session["flags"]["heard_treaty_lore"] = True
            self.give(session, "holy_water", 2)
            session["character"]["mp"] = 6
            gold = session["character"]["gold"]
            self.start(session)
            self.assertEqual(len(self.specials(session)), 2)
            combat.perform_combat_action(session, "special", aid)
            self.assertEqual(session["combat"]["result"]["prepared_text"], upgrade_purification.PURIFY_TEXT)
            self.assertNotIn("rewards", session["combat"]["result"])
            self.assertEqual(session["character"]["mp"], 0 if aid.endswith("prayer") else 6)
            self.assertEqual(next(i["quantity"] for i in session["character"]["inventory"] if i.get("id") == "holy_water"),
                             2 if aid.endswith("prayer") else 1)
            self.resolve(session)
            self.assertEqual(session["character"]["gold"], gold)
            self.assertFalse(any(f.startswith("combat_defeated:") or f == "defeated_ignis" for f in session["flags"]))
            self.assertFalse(any(i.get("id") == "red_dragon_core" for i in session["character"]["inventory"]))
            self.assertFalse(combat.ensure_combat_started(session))
            self.assertIsNone(session["game_over"])

    def test_post_purification_evidence_once_and_endings(self):
        for ally in (False, True):
            session = self.purify()
            with self.assertRaises(ValueError):
                self.action(session, "ask_ignis_aid")
            self.action(session, "hear_ignis_testimony")
            self.action(session, "receive_ignis_scale")
            with self.assertRaises(ValueError):
                self.action(session, "receive_ignis_scale")
            if ally:
                self.action(session, "ask_ignis_aid")
            self.action(session, "return_to_castle_report")
            # The guaranteed scale alone must suffice for exposure.
            session["flags"] = {k: v for k, v in session["flags"].items() if k in {"ignis_purified", "ignis_ally"}}
            self.action(session, "report_with_evidence")
            self.start(session)
            for _ in range(2):
                session["combat"]["enemies"][0]["hp"] = 0
                combat._check_victory_or_defeat(session)
            self.resolve(session)
            self.assertEqual(session["game_over"]["ending"], "draco_defeated_with_ignis" if ally else "draco_defeated")
        session = self.purify()
        self.action(session, "return_to_castle_report")
        self.action(session, "report_normally")
        self.assertEqual(session["game_over"]["ending"], "ignis_purified")
        self.assertEqual(select_hybrid_prepared_turn(session)["draft"]["gm_text"], upgrade_purification.NORMAL_ENDING)

    def test_testimony_counts_and_quest_accepts_either_flag(self):
        session = self.session(location="castle_report")
        session["flags"] = {"heard_ignis_testimony": True}
        action = state.resolve_action(session, action_id="report_with_evidence")
        self.assertFalse(state.action_requirement_status(action, session)[0])
        session["flags"]["heard_treaty_lore"] = True
        self.assertTrue(state.action_requirement_status(action, session)[0])
        for flag in ("defeated_ignis", "ignis_purified"):
            session["flags"] = {flag: True, "reached_village": True, "entered_dragon_valley": True}
            quest = public_quests(session)[0]
            self.assertIn("邪竜イグニスを止める", quest["completed_stages"])
            self.assertEqual(quest["current_objective"], "王城へ戻り、国王に報告する")

    def test_api_resolution_returns_exploration_without_llm(self):
        session = self.session()
        session["flags"]["frost_trace_seen"] = True
        self.give(session, "holy_water")
        self.start(session)
        with patch.object(app, "load_session", return_value=session), patch.object(app, "save_session"), \
                patch.object(app, "chat_completion", side_effect=AssertionError("LLM called")):
            app.api_combat_action("balance", app.CombatActionRequest(action_type="special", action_id="purify_ignis_holy_water"))
            app.api_combat_resolve("balance")
        self.assertEqual(state.current_location_id(session), "ignis_purified")
        self.assertIsNone(session["combat"])
        self.assertTrue(session["choices"])
        self.assertEqual(session["last_combat_result"]["outcome"], "purified")

    def test_phase_ally_entry_timing_repeat_damage_and_encounter_declaration(self):
        for declaration in ("phase", "encounter"):
            for enabled in (False, True):
                pack = deepcopy(self.pack)
                dragon = next(e for e in pack["enemies"] if e["id"] == "draco_dragon")
                dragon["phase_allies"][0]["round_start_effects"][0]["damage"] = "10"
                if declaration == "encounter":
                    ally = dragon.pop("phase_allies")[0]
                    ally["enemy_ids"] = ["draco_dragon"]
                    next(l for l in pack["locations"] if l["id"] == "draco_battle")["combat"]["phase_allies"] = [ally]
                session = self.session(location="draco_battle", pack=pack)
                session["flags"]["ignis_ally"] = enabled
                self.start(session)
                self.assertEqual(session["combat"]["phase_allies"], [])
                session["combat"]["enemies"][0]["hp"] = 0
                combat._check_victory_or_defeat(session)
                battle = session["combat"]
                enemy = battle["enemies"][0]
                self.assertEqual(enemy["hp"], enemy["max_hp"])
                self.assertEqual(len(battle["phase_allies"]), int(enabled))
                self.assertEqual(sum(e["kind"] == "phase_ally" for e in battle["log"]), int(enabled))
                if enabled:
                    self.assertEqual(battle["log"][-1]["text"], upgrade_purification.ALLY_TEXT)
                    with self.assertRaises(combat.CombatError):
                        combat._target_enemy(battle, "ignis")
                for _ in range(2):
                    before = enemy["hp"]
                    combat._apply_round_start_effects(session, random.Random(1))
                    self.assertEqual(enemy["hp"] < before, enabled)
                self.assertEqual(sum(e["kind"] == "phase_ally" for e in battle["log"]), int(enabled))
                if enabled:
                    self.assertEqual(battle["log"][-1]["data"]["element"], "fire")

    def test_policy_reserves_means_and_prefers_purification(self):
        session = self.session("cleric")
        session["flags"]["frost_trace_seen"] = True
        session["character"].update(mp=6, hp=1)
        self.give(session, "holy_water")
        self.start(session, .6)
        action, _ = sim.choose_action(session, "heuristic")
        self.assertNotEqual(action["id"], "holy_water")
        session["combat"]["enemies"][0]["hp"] = 1
        action, _ = sim.choose_action(session, "heuristic")
        self.assertEqual(action["type"], "special")

    def test_routes_preparation_manifest_and_verbatim_section_six(self):
        for character in ("hero", "cleric", "mage", "thief"):
            result = route.simulate_route(self.pack, self.cp, character, encounter="draco_battle", n=2, seed=4, purify=True)
            self.assertEqual(result["route"], "purification_true_ending")
        self.assertEqual(key_items.generate(), self.manifest)
        broken = deepcopy(self.pack)
        next(l for l in broken["locations"] if l["id"] == "dragon_valley_loc")["combat"]["special_actions"] = []
        self.assertTrue(redundancy.check(broken, self.manifest)["errors"])
        design = (checkpoints.ROOT / "docs/design/scenario-v2.md").read_text(encoding="utf-8").split("\n## 6.")[1].split("\n## 7.")[0]
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            path = checkpoints.DEFAULT_SCENARIO.with_name(filename)
            text = path.read_text(encoding="utf-8")
            for line in design.splitlines():
                for label in ("description：", "结果文：", "战斗日志文："):
                    if label in line:
                        self.assertIn(line.split(label, 1)[1].strip(), text)
            for phrase in (upgrade_purification.ALLY_TEXT, upgrade_purification.NORMAL_ENDING, upgrade_purification.BEST_ENDING):
                self.assertIn(phrase, design)
                self.assertIn(phrase, text)
            for aid, phrase in re.findall(r'`(purify_ignis_[^`]+)`「([^」]+)」', design):
                self.assertIn(phrase, text)
            pack = json.loads(text)
            before = deepcopy(pack)
            upgrade_purification.upgrade(pack)
            self.assertEqual(pack, before)


if __name__ == "__main__":
    unittest.main()
