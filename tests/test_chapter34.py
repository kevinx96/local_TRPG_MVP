from __future__ import annotations

import json
import random
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import combat, free_actions, state, shops
from host.maps import movement_action, public_maps
from host.scenario_context import select_scenario_context
from scripts.balance import ch34, checkpoints
from scripts.scenario.upgrade_ch34 import ANGER, BETRAYAL, STOLEN, WARLOCK
from scripts.scenario import tune_ch34, upgrade_ch34


class Chapter34Tests(unittest.TestCase):
    def sessions(self, location, character="hero"):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            session = checkpoints.fresh_session(state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(filename)), character)
            scene = next(l["scene_id"] for l in session["scenario_pack"]["locations"] if l["id"] == location)
            session["world_state"] = dict(scene_id=scene, location_id="fixture")
            state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)
            yield session

    def act(self, session, identifier, success=True):
        action = state.resolve_action(session, action_id=identifier)
        self.assertIsNotNone(action, identifier)
        self.assertTrue(state.action_requirement_status(action, session)[0], identifier)
        _, dc = state.action_dice_settings(action, session=session)
        return state.apply_action_result(session, action, dict(dc=dc, success=success))

    def add(self, session, name):
        state.apply_state_delta(session, {"inventory_add": [{"name": name, "quantity": 1}]})

    def has(self, session, name):
        return any(i["name"] == name for i in session["character"]["inventory"])

    def finish(self, session, victory=True):
        session["combat_start_requested"] = True
        self.assertTrue(combat.ensure_combat_started(session))
        if victory:
            for enemy in session["combat"]["enemies"]:
                enemy["hp"] = 0
        else:
            session["character"]["hp"] = 0
        combat._check_victory_or_defeat(session)
        delta = combat.consume_combat_state_delta(session)
        state.apply_state_delta(session, delta, allow_world_transition=True)
        combat.clear_combat_after_resolution(session)

    def seed(self, session):
        self.add(session, "火種")
        session["flags"]["accepted_fire_seed"] = True

    def gate(self, session):
        state.apply_state_delta(session, {"current_location": "valley_nest_gate"}, allow_world_transition=True)

    def test_house_both_arrivals_rescue_methods_reward_once_and_abandonment(self):
        for encounter in ("village_fire_slime", "village_fire_elemental"):
            for method in ("break_burning_beam", "climb_to_window", "douse_with_ice", "leave_burning_house"):
                for session in self.sessions(encounter):
                    with self.subTest(encounter=encounter, method=method):
                        self.finish(session)
                        self.assertEqual(state.current_location_id(session), "burning_house")
                        self.assertTrue(session["flags"]["found_burning_house"])
                        if method == "douse_with_ice":
                            self.add(session, "氷の結晶")
                        self.act(session, method)
                        self.assertEqual(state.current_location_id(session), "village_frozen_clue")
                        self.act(session, "visit_village")
                        if method == "leave_burning_house":
                            self.assertTrue(session["flags"]["riku_abandoned"])
                            self.assertIsNone(state.resolve_action(session, action_id="return_riku"))
                            self.assertIn("長老は焼け跡を見つめ、黙り込んでいる", [e["text"] for e in session["event_log"]])
                        else:
                            self.assertTrue(session["flags"]["riku_rescued"])
                            self.act(session, "return_riku")
                            self.assertEqual(next(i["quantity"] for i in session["character"]["inventory"] if i.get("id") == "dragon_elixir"), 2)
                            self.assertTrue(session["flags"]["heard_treaty_lore"])
                            self.assertFalse(state.action_requirement_status(state.resolve_action(session, action_id="return_riku"), session)[0])
                        session["character"].update(hp=1, mp=0, sp=0, gold=5)
                        self.act(session, "rest_at_refuge")
                        self.assertEqual(session["character"]["gold"], 0)
                        for resource in ("hp", "mp", "sp"):
                            self.assertEqual(session["character"][resource], session["character"][f"max_{resource}"])
                        self.assertFalse(state.action_requirement_status(state.resolve_action(session, action_id="rest_at_refuge"), session)[0])
                        self.act(session, "go_dragon_valley")
                        self.assertEqual(state.current_location_id(session), "valley_entrance")

    def test_house_failed_checks_retry_and_cold_requirements(self):
        for identifier, loss in (("break_burning_beam", 5), ("climb_to_window", 3)):
            for s in self.sessions("burning_house"):
                before = s["character"]["hp"]
                self.act(s, identifier, False)
                self.assertEqual(s["character"]["hp"], before - loss)
                self.assertEqual(state.current_location_id(s), "burning_house")
                self.act(s, identifier)
                self.assertTrue(s["flags"]["riku_rescued"])
        for s in self.sessions("burning_house"):
            action = state.resolve_action(s, action_id="douse_with_ice")
            self.assertFalse(state.action_requirement_status(action, s)[0])
            for item_id in ("ice_charm", "activated_ice_charm", "ice_iron_greatsword", "ice_katana", "ice_crystal"):
                copy = deepcopy(s)
                self.add(copy, next(i["name"] for i in s["scenario_pack"]["items"] if i["id"] == item_id))
                self.assertTrue(state.action_requirement_status(action, copy)[0])
        for s in self.sessions("burning_house", "mage"):
            self.act(s, "douse_with_ice")

    def test_force_remove_is_story_only(self):
        for s in self.sessions("village"):
            self.seed(s)
            raw = {"inventory_remove": [{"name": "火種", "force": True}]}
            # Untrusted model deltas strip the story-only override.
            delta = state.sanitize_model_state_delta(s, raw)
            state.apply_state_delta(s, delta)
            self.assertTrue(self.has(s, "火種"))
            state.apply_state_delta(s, {"inventory_remove": [{"name": "火種"}]})
            self.assertTrue(self.has(s, "火種"))
            state.apply_state_delta(s, raw)
            self.assertFalse(self.has(s, "火種"))

    def test_nest_branches_and_once(self):
        for accepted, rescued, expected in ((True, False, "xanxus_at_nest"), (False, True, "warlock_at_nest"), (False, False, "valley_nest_gate")):
            for s in self.sessions("valley_lava_bridge"):
                if accepted:
                    self.seed(s)
                s["flags"]["warlock_rescue_triggered"] = rescued
                self.gate(s)
                self.assertEqual(state.current_location_id(s), expected)
                if accepted:
                    self.act(s, "obey_xanxus_core")
                    self.assertTrue(s["flags"]["promised_core_to_xanxus"])
                elif rescued:
                    self.assertTrue(s["flags"][BETRAYAL])
                    self.assertIn(WARLOCK, [e["text"] for e in s["event_log"]])
                    self.act(s, "continue_after_warlock")
                else:
                    self.assertNotIn(BETRAYAL, s["flags"])
                state.apply_state_delta(s, {"current_location": "valley_lava_bridge"}, allow_world_transition=True)
                self.gate(s)
                self.assertEqual(state.current_location_id(s), "valley_nest_gate")

    def test_cleanse_costs_phantom_win_loss_and_call_warlock(self):
        for win in (True, False):
            for s in self.sessions("valley_lava_bridge"):
                self.seed(s)
                self.add(s, "聖水")
                self.gate(s)
                self.act(s, "cleanse_fire_seed")
                self.assertFalse(self.has(s, "聖水"))
                self.assertFalse(next(l for l in s["scenario_pack"]["locations"] if l["id"] == "xanxus_phantom_battle")["combat"]["flee_allowed"])
                self.finish(s, win)
                self.assertEqual(state.current_location_id(s), "valley_nest_gate")
                self.assertIsNone(s.get("game_over"))
                self.assertEqual(self.has(s, "火種"), not win)
                if win:
                    self.assertTrue(s["flags"]["fire_seed_removed"])
                    self.assertTrue(s["flags"][BETRAYAL])
                else:
                    self.assertEqual(s["character"]["hp"], 1)
                    self.assertTrue(s["flags"]["promised_core_to_xanxus"])
        for s in self.sessions("valley_lava_bridge", "cleric"):
            self.seed(s)
            self.gate(s)
            s["character"]["mp"] = 5
            a = state.resolve_action(s, action_id="cleanse_fire_seed")
            self.assertFalse(state.action_requirement_status(a, s)[0])
            s["character"]["mp"] = 6
            self.act(s, "cleanse_fire_seed")
            self.assertEqual(s["character"]["mp"], 0)
        for s in self.sessions("valley_lava_bridge"):
            self.seed(s)
            s["flags"]["warlock_rescue_triggered"] = True
            self.gate(s)
            self.act(s, "call_warlock")
            self.assertFalse(self.has(s, "火種"))
            self.assertTrue(s["flags"][BETRAYAL])

    def test_ignis_core_and_purification_after_promise(self):
        for promised, removed in ((False, False), (True, False), (True, True)):
            for s in self.sessions("dragon_valley_loc"):
                s["flags"].update(promised_core_to_xanxus=promised, fire_seed_removed=removed)
                self.finish(s)
                stolen = promised and not removed
                self.assertEqual(self.has(s, "紅竜の炎核"), not stolen)
                self.assertEqual(bool(s["flags"].get("xanxus_took_core")), stolen)
                self.assertEqual(STOLEN in [e["text"] for e in s["event_log"]], stolen)
        for s in self.sessions("dragon_valley_loc", "cleric"):
            s["flags"].update(promised_core_to_xanxus=True, frost_trace_seen=True)
            s["character"]["mp"] = 6
            self.assertTrue(combat.ensure_combat_started(s))
            s["combat"]["enemies"][0]["hp"] = 1
            combat.perform_combat_action(s, "special", "purify_ignis_prayer", rng=random.Random(1))
            state.apply_state_delta(s, combat.consume_combat_state_delta(s), allow_world_transition=True)
            self.assertEqual(state.current_location_id(s), "ignis_purified")
            self.assertFalse(self.has(s, "紅竜の炎核"))
            self.assertNotIn("xanxus_took_core", s["flags"])
            self.assertIn(ANGER, [e["text"] for e in s["event_log"]])

    def test_bridge_checks_ledge_and_enemy_first(self):
        for s in self.sessions("valley_entrance"):
            self.assertEqual(s["character"]["level"], 5)
            self.act(s, "sneak_through_ash", False)
            self.assertTrue(s["enemy_first_requested"])
            self.finish(s)
            self.assertEqual(state.current_location_id(s), "valley_lava_bridge")
            a = state.resolve_action(s, action_id="cross_lava_bridge")
            self.assertEqual(state.action_dice_settings(a, session=s)[1], 12)
            with patch.object(state.random, "randint", return_value=20):
                checkpoints.replay_step(s, "observe:bridge_ropes")
            self.assertEqual(state.action_dice_settings(a, session=s)[1], 6)
            before = s["character"]["hp"]
            self.act(s, "cross_lava_bridge", False)
            self.assertEqual(s["character"]["hp"], before - 6)
            self.assertEqual(state.current_location_id(s), "valley_nest_gate")
        for s in self.sessions("valley_lava_bridge"):
            self.act(s, "take_ledge_path")
            self.finish(s)
            self.assertEqual(state.current_location_id(s), "valley_nest_gate")

    def test_elixir_heals_half_max_hp_in_and_out_of_combat(self):
        for battle in (True, False):
            for s in self.sessions("dragon_valley_loc" if battle else "village"):
                self.add(s, "竜の秘薬")
                s["character"].update(hp=1, max_hp=51)
                if battle:
                    combat.ensure_combat_started(s)
                    combat._player_item(s, "dragon_elixir", "", random.Random(1))
                else:
                    free_actions.adjudicate(s, dict(kind="interact", operation="use_item", target_id="self", item_id="dragon_elixir", action_id="", advance=False, approach="竜の秘薬を使う", reply=""))
                self.assertEqual(s["character"]["hp"], 26)
                self.assertFalse(self.has(s, "竜の秘薬"))
        for s in self.sessions("village"):
            self.add(s, "竜の秘薬")
            s["character"].update(hp=1, max_hp=51)
            shops.use_item(s, "dragon_elixir")
            self.assertEqual(s["character"]["hp"], 26)

    def test_maps_clicks_visibility_and_legacy_d4(self):
        for location, map_id, node, action in (("village_frozen_clue", "burning_village", "V8", "visit_village"), ("village", "burning_village", "V3", "return_frozen_clue"), ("valley_lava_bridge", "dragon_valley", "D2b", "take_ledge_path"), ("valley_nest_gate", "dragon_valley", "D4", "enter_dragon_nest")):
            for s in self.sessions(location):
                maps = public_maps(s)
                self.assertEqual(maps["current_map_id"], map_id)
                m = next(m for m in maps["maps"] if m["id"] == map_id)
                self.assertEqual(next(n for n in m["nodes"] if n["id"] == node)["visibility"], "adjacent-unknown")
                self.assertEqual(movement_action(s, node)["id"], action)
                self.act(s, action)
        for s in self.sessions("dragon_valley_loc"):
            s.pop("visited_locations", None)
            state.ensure_world_state(s)
            self.assertEqual(public_maps(s)["current_map_id"], "dragon_valley")
            self.assertEqual(state.current_location_id(s), "dragon_valley_loc")
            self.assertTrue(combat.ensure_combat_started(s))

    def test_all_legacy_destinations_redirect_and_clue_counts(self):
        for s in self.sessions("castle"):
            for loc in s["scenario_pack"]["locations"]:
                if loc["id"] == "valley_nest_gate":
                    continue
                self.assertNotIn('"current_location": "dragon_valley_loc"', json.dumps(loc.get("actions", [])))
            s["flags"].update(heard_xanxus_betrayal=True, heard_treaty_lore=True)
            s["world_state"] = dict(scene_id="castle_return", location_id="castle_report")
            self.assertTrue(state.action_requirement_status(state.resolve_action(s, action_id="report_with_evidence"), s)[0])

    def test_legacy_save_loads_at_d4_without_replaying_entry_or_milestone(self):
        for s in self.sessions("dragon_valley_loc"):
            s["scenario_path"] = s["scenario_pack"]["source_path"]
            s["scenario_pack"]["meta"]["content_revision"] = "2026-10-12-v018"
            s["flags"]["entered_dragon_valley"] = True
            state.apply_state_delta(s, {})
            s["character"]["hp"] = 7
            before = deepcopy(s["character"])
            with tempfile.TemporaryDirectory() as directory, patch.object(state, "SAVE_DIR", Path(directory)):
                state.save_session(s)
                loaded = state.load_session("balance")
            self.assertEqual(state.current_location_id(loaded), "dragon_valley_loc")
            self.assertEqual(loaded["character"], before)
            self.assertNotIn("nest_event_seen", loaded["flags"])

    def test_authored_entry_text_is_narrated_without_llm(self):
        for s in self.sessions("valley_lava_bridge"):
            self.seed(s)
            result = self.act(s, "cross_lava_bridge")
            description = state._current_location_record(s)["description"]
            self.assertTrue(result["result_text"].endswith(description))
        for s in self.sessions("dragon_valley_loc"):
            s["flags"]["promised_core_to_xanxus"] = True
            combat.ensure_combat_started(s)
            s["combat"]["enemies"][0]["hp"] = 0
            combat._check_victory_or_defeat(s)
            state.apply_state_delta(s, combat.consume_combat_state_delta(s), allow_world_transition=True)
            self.assertTrue(combat.combat_result_for_llm(s)["prepared_text"].endswith(STOLEN))

    def test_balance_checker_keeps_unmet_targets_visible(self):
        result = {"encounters": [dict(encounter="xanxus_phantom_battle", character="hero", win_rate=.76)],
                  "routes": [dict(preparation="riku", character="mage", completion_rate=.94),
                             dict(preparation="refuge", character="thief", completion_rate=.54)]}
        self.assertEqual(len(ch34.violations(result)), 2)
        for s in self.sessions("valley_nest_gate"):
            s["character"].update(hp=1, max_hp=40, inventory=[])
            self.add(s, "竜の秘薬")
            checkpoints.replay_step(s, "@recover_hp")
            self.assertEqual(s["character"]["hp"], 21)
            self.assertFalse(self.has(s, "竜の秘薬"))
            checkpoints.replay_step(s, "@recover_hp")
            self.assertEqual(s["character"]["hp"], 21)

    def test_pack_sync_idempotence_and_elder_description(self):
        packs = [s["scenario_pack"] for s in self.sessions("village")]
        for group in ("maps", "quests"):
            self.assertEqual(packs[0][group], packs[1][group])
        self.assertEqual(*[next(i for i in p["items"] if i["id"] == "dragon_elixir") for p in packs])
        for identifier in ("ash_wraith", "lava_drake", "xanxus_phantom"):
            self.assertEqual(*[next(e for e in p["enemies"] if e["id"] == identifier) for p in packs])
        for s in self.sessions("village"):
            copy = deepcopy(s["scenario_pack"])
            upgrade_ch34.upgrade(copy)
            tune_ch34.tune(copy)
            self.assertEqual(copy, s["scenario_pack"])
            s["flags"]["riku_abandoned"] = True
            elder = next(n for n in select_scenario_context(s)["matched"]["npcs"] if n["id"] == "elder")
            self.assertTrue(elder["description"].endswith("長老は焼け跡を見つめ、黙り込んでいる"))


if __name__ == "__main__":
    unittest.main()
