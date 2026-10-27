from __future__ import annotations

import json
import random
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import app, combat, difficulty, progression, state, status_effects
from host.item_mechanics import equipped_items
from host.scenario_context import select_hybrid_prepared_turn
from host.shops import _can_sell
from scripts.balance import checkpoints, probes_v3
from scripts.balance.holy_sword_049 import gate_session, run_jobs
from scripts.scenario.holy_sword_049 import (
    AWAKEN_TEXT,
    BLACKSMITH_HINT,
    E1_TEXT,
    E2_TEXT,
    IRON_HINT,
    LOCK_TEXT,
    REVEAL_DIARY_TEXT,
    REVEAL_NO_DIARY_TEXT,
    SWORD_DESCRIPTION,
    SWORD_EFFECT,
    START_TEXT,
    STOLEN_SKILL_NAME,
    V1_TEXT,
    V2_TEXT,
    migrate,
)

ROOT = Path.cwd()
BASE = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
NORMAL = difficulty.apply_difficulty(BASE, "normal")
CHOICES = {k: v for k, v in probes_v3.combinations(NORMAL, "hero")[0].items() if int(k) <= 6}


class Rolls:
    def randint(self, low, high):
        return low

    def choices(self, values, weights, k):
        return [values[-1]]


def session(start=True):
    value = gate_session(NORMAL, CHOICES)
    if start:
        combat.ensure_combat_started(value)
    return value


def hit(value, damage=999):
    enemy = value["combat"]["enemies"][0]
    return combat._resolve_attack(value, enemy, value["character"],
                                  {"name": "【仮】", "damage": str(damage), "accuracy": 100}, enemy["id"], Rolls())


class HolySwordTests(unittest.TestCase):
    def test_equipped_id_name_and_unequipped(self):
        value = session(False)
        for key in ("iron_sword", "鉄の剣"):
            self.assertTrue(state._session_requirement_passes({"equipped_item": key}, value))
        value["character"]["equipment"] = ["革の鎧"]
        self.assertFalse(state._session_requirement_passes({"equipped_item": "iron_sword"}, value))

    def test_all_branch_cases(self):
        for case in ("A", "purified", "unequipped", "merchant", "sold", "B", "B_purified", "both_swords", "other_class"):
            with self.subTest(case=case):
                value = session(False)
                actor = value["character"]
                if case == "purified":
                    value["flags"] = {"ignis_purified": True}
                if case in {"unequipped", "merchant", "sold", "both_swords"}:
                    actor["equipment"] = ["革の鎧"]
                if case in {"merchant", "sold", "B", "B_purified"}:
                    actor["inventory"] = [item for item in actor["inventory"] if item.get("id") != "iron_sword"]
                if case in {"B", "B_purified"}:
                    value["flags"] = {"accepted_sword_fusion": True, "defeated_ignis" if case == "B" else "ignis_purified": True}
                if case == "other_class":
                    actor["id"] = actor["character_id"] = "mage"
                if case == "both_swords":
                    state.apply_state_delta(value, {"inventory_add": [{"name": "氷鉄の大剣"}], "equip_item": "氷鉄の大剣"})
                combat.ensure_combat_started(value)
                a = bool(value["combat"].get("lethal_awakenings"))
                b = any(m["id"] == "draco_holy_sword" for m in value["combat"]["active_modifiers"])
                self.assertEqual((a, b), (case == "A", case in {"B", "B_purified"}))
                self.assertFalse(a and b)

    def test_both_swords_iron_equipped_qualifies(self):
        value = session(False)
        state.apply_state_delta(value, {"inventory_add": [{"name": "氷鉄の大剣"}]})
        state._equip_inventory_item(value, "鉄の剣")
        combat.ensure_combat_started(value)
        self.assertTrue(value["combat"]["lethal_awakenings"])

    def test_awaken_once_order_resources_status_flag_and_equipment(self):
        value = session()
        actor = value["character"]
        actor["mp"], actor["sp"] = 3, 7
        actor["statuses"] = [{"id": "test", "remaining_rounds": 8}]
        hit(value)
        self.assertEqual((actor["hp"], actor["mp"], actor["sp"]), (actor["max_hp"], 3, 7))
        self.assertEqual(actor["statuses"], [{"id": "test", "remaining_rounds": 8}])
        self.assertTrue(value["flags"]["holy_sword_awakened"])
        self.assertEqual([i["name"] for i in equipped_items(actor)], ["勇者の聖剣", "革の鎧"])
        entries = [e for e in value["combat"]["log"] if e["kind"].startswith("awakening")]
        self.assertEqual([e["kind"] for e in entries], ["awakening_lock", "awakening"])
        self.assertEqual(entries[0]["state"]["player"]["hp"], 1)
        self.assertEqual(entries[1]["state"]["player"]["hp"], actor["max_hp"])
        hit(value)
        self.assertEqual(actor["hp"], 0)
        combat._check_victory_or_defeat(value)
        events = combat.combat_result_for_llm(value)["committed_events"]
        self.assertEqual(sum(e["kind"] == "awakening" for e in events), 1)

    def test_one_hp_and_guard_priority_then_existing_guard(self):
        for hp in (1, 20):
            value = session()
            value["character"]["hp"] = hp
            value["combat"]["player_status"]["survive_at_one"] = True
            hit(value)
            self.assertEqual(value["character"]["hp"], value["character"]["max_hp"])
            self.assertTrue(value["combat"]["player_status"]["survive_at_one"])
            hit(value)
            self.assertEqual(value["character"]["hp"], 1)
            hit(value)
            self.assertEqual(value["character"]["hp"], 0)

    def test_nonlethal_reductions_do_not_awaken(self):
        value = session()
        value["character"]["hp"] = 10
        value["combat"]["player_status"]["guard_multiplier"] = .5
        hit(value, 12)
        self.assertGreater(value["character"]["hp"], 0)
        self.assertNotIn("holy_sword_awakened", value["flags"])

    def test_shield_and_mana_armor_before_trigger(self):
        value = session()
        actor = value["character"]
        actor["hp"], actor["mp"] = 5, 50
        status_effects.apply(value, actor, {"id": "shield", "kind": "modifier", "modifiers": {"shield": {"amount": 20}}}, actor, Rolls())
        hit(value, 15)
        self.assertEqual(actor["hp"], 5)
        self.assertNotIn("holy_sword_awakened", value["flags"])
        actor["statuses"] = []
        with patch.object(progression, "effects", return_value={"mana_armor": 1}):
            hit(value, 15)
        self.assertEqual(actor["hp"], 5)
        self.assertNotIn("holy_sword_awakened", value["flags"])

    def test_multihit_middle_restores_then_remaining_hit(self):
        value = session()
        actor, enemy = value["character"], value["combat"]["enemies"][0]
        actor["hp"] = 21
        combat._execute_enemy_ability(value, enemy, {"id": "test", "name": "【仮】", "kind": "attack",
                                                   "damage": "15", "accuracy": 100, "hits": 3}, Rolls())
        damage = [e["data"]["damage"] for e in value["combat"]["log"] if e["kind"] == "damage"]
        self.assertEqual(len(damage), 3)
        self.assertLess(damage[0], 21)
        self.assertGreaterEqual(sum(damage[:2]), 21)
        self.assertEqual(actor["hp"], actor["max_hp"] - damage[2])

    def test_field_tick_self_damage_cursed_heal(self):
        for kind in ("field", "tick", "self", "curse"):
            with self.subTest(kind=kind):
                value = session()
                actor, enemy = value["character"], value["combat"]["enemies"][0]
                if kind == "field":
                    combat._apply_direct_formula_damage(value, enemy, actor, "999", "physical", "【仮】", Rolls())
                elif kind == "tick":
                    status_effects.apply(value, actor, {"id": "test", "kind": "damage", "tick": {"damage": "999"}}, enemy, Rolls())
                    status_effects.tick(value, actor, Rolls())
                elif kind == "self":
                    combat._resolve_attack(value, actor, enemy, {"damage": "1", "accuracy": 100, "self_damage": 999}, "player", Rolls())
                else:
                    actor["skills"] = [{"id": "heal", "name": "【仮】", "kind": "heal", "healing": "999", "cost": 0}]
                    with patch.object(combat, "_equipped_effect", return_value=True):
                        combat._player_skill(value, "heal", "", Rolls())
                self.assertTrue(value["flags"]["holy_sword_awakened"])
                self.assertEqual(actor["hp"], actor["max_hp"])

    def test_phase_registration_persists_and_transition_does_not_trigger(self):
        for awaken_first in (False, True):
            value = session()
            if awaken_first:
                hit(value)
            value["combat"]["enemies"][0]["hp"] = 0
            combat._check_victory_or_defeat(value)
            self.assertEqual(value["combat"]["enemies"][0]["template_id"], "draco_dragon")
            self.assertEqual(bool(value["flags"].get("holy_sword_awakened")), awaken_first)
            hit(value)
            self.assertEqual(value["character"]["hp"], 0 if awaken_first else value["character"]["max_hp"])

    def test_other_battle_and_old_active_save_have_no_registration(self):
        value = session(False)
        value["world_state"] = {"scene_id": "forest", "location_id": "forest_wolves"}
        value["combat_start_requested"] = True
        combat.ensure_combat_started(value)
        hit(value)
        self.assertEqual(value["character"]["hp"], 0)
        value = session()
        value["combat"].pop("lethal_awakenings")
        combat.ensure_combat_started(value)
        hit(value)
        self.assertEqual(value["character"]["hp"], 0)

    def test_awakened_basic_attack_and_followups(self):
        value = session(False)
        value["flags"]["robert_hammer_returned"] = True
        combat.ensure_combat_started(value)
        hit(value)
        value["combat"]["enemies"][0]["hp"] = 0
        combat._check_victory_or_defeat(value)
        sword = next(i for i in NORMAL["items"] if i["id"] == "hero_holy_sword")
        ability = combat._equipped_weapon_attack(value["character"])
        for key in ("damage", "accuracy", "element", "ignores_resistance"):
            self.assertEqual(ability[key], sword["combat"][key])
        combat._player_attack(value, "", Rolls())
        logs = [e for e in value["combat"]["log"] if e["kind"] == "damage" and e["actor"] == "player"]
        self.assertEqual(logs[0]["data"]["element"], "holy")
        self.assertTrue(any("追い打ち" in e["text"] for e in logs))
        self.assertTrue(any("霜断ち" in e["text"] for e in logs))

    def test_model_cannot_grant_or_remove_sword_or_set_flag(self):
        value = session()
        for item in ({"id": "hero_holy_sword"}, {"name": "勇者の聖剣"}):
            self.assertEqual(state.sanitize_model_state_delta(value, {"inventory_add": [item], "flags_set": ["holy_sword_awakened"]}), {})
        hit(value)
        self.assertEqual(state.sanitize_model_state_delta(value, {"inventory_remove": [{"id": "hero_holy_sword"}]}), {})
        self.assertTrue(value["system_logs"])

    def test_b_modifier_all_direct_attacks_ai_king_and_dragon(self):
        value = session(False)
        value["flags"] = {"accepted_sword_fusion": True, "king_trust": True}
        combat.ensure_combat_started(value)
        enemy = value["combat"]["enemies"][0]
        self.assertEqual(sum(e["text"] == START_TEXT for e in value["combat"]["log"]), 1)
        self.assertEqual(combat._choose_enemy_ability(enemy, value, Rolls())["id"], "stolen_holy_blade")
        self.assertTrue(any(m.get("enemy_defense") == -4 for m in combat._encounter_modifiers(value, enemy)))
        for element in ("physical", "ice", "holy"):
            baseline = deepcopy(value)
            baseline["combat"]["active_modifiers"] = [m for m in baseline["combat"]["active_modifiers"] if m["id"] != "draco_holy_sword"]
            actor = value["character"]
            actor["hp"] = baseline["character"]["hp"] = 999
            ability = {"name": "【仮】", "damage": "20", "accuracy": 100, "element": element}
            a = combat._resolve_attack(baseline, baseline["combat"]["enemies"][0], baseline["character"], ability, enemy["id"], Rolls())
            b = combat._resolve_attack(value, enemy, actor, ability, enemy["id"], Rolls())
            self.assertEqual(b, round(a * 1.3))
        enemy["hp"] = 0
        combat._check_victory_or_defeat(value)
        self.assertFalse(any(m["id"] == "draco_holy_sword" for m in value["combat"]["active_modifiers"]))

    def test_reveal_priority_all_modes_no_model_called(self):
        evidence = []
        for mode, narration in (("semi", False), ("semi", True), ("full", True)):
            for diary in (False, True):
                value = checkpoints.fresh_session(difficulty.apply_difficulty(state.load_scenario_pack(
                    ROOT / "host/prompt/processed/dragon_rpg_hybrid.json"), "normal"), "hero", "normal", effective=True)
                value["gm_mode"] = mode
                value["flags"] = {"accepted_sword_fusion": True}
                value["world_state"] = {"scene_id": "castle_return", "location_id": "castle_report"}
                state.apply_state_delta(value, {"inventory_add": [{"name": "白竜の日誌" if diary else "白い竜鱗"}]})
                with patch.object(app, "save_session"), patch.object(app, "chat_completion", side_effect=AssertionError("network")):
                    app._run_turn(value, app.TurnRequest(text="将軍ドラコの正体を問いただす", action_id="report_with_evidence"), allow_narration=narration)
                text = value["messages"][-1]["text"]
                expected = REVEAL_DIARY_TEXT if diary else REVEAL_NO_DIARY_TEXT
                other = REVEAL_NO_DIARY_TEXT if diary else REVEAL_DIARY_TEXT
                self.assertIn(expected, text)
                self.assertNotIn(other, text)
                self.assertEqual("日誌を掲げる" in text, diary)
                evidence.append({"mode": mode, "allow_narration": narration, "diary": diary, "text": text})
        output = ROOT / ".tmp-test/049/reveal-modes.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_final_holy_sword_texts_and_normal_gating(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            with self.subTest(filename=filename):
                pack = json.loads((ROOT / "host/prompt/processed" / filename).read_text(encoding="utf-8"))
                item = next(item for item in pack["items"] if item["id"] == "hero_holy_sword")
                self.assertEqual(item["description"], SWORD_DESCRIPTION)
                self.assertEqual(item["effect"], SWORD_EFFECT)
                self.assertEqual(item["awakening_origin"]["description_suffix"], IRON_HINT)

                locations = {location["id"]: location for location in pack["locations"]}
                modifiers = {entry["id"]: entry for entry in locations["draco_battle"]["combat"]["encounter_modifiers"]}
                awakening = modifiers["hero_holy_sword"]["lethal_awakening"]
                self.assertEqual(awakening["lock_text"], LOCK_TEXT)
                self.assertEqual(awakening["text"], AWAKEN_TEXT)
                stolen = modifiers["draco_holy_sword"]
                self.assertEqual(stolen["text"], START_TEXT)
                self.assertEqual(stolen["extra_enemy_skills"][0]["name"], STOLEN_SKILL_NAME)

                reveal = {variant["id"]: variant["text"] for variant in
                          next(action for action in locations["castle_report"]["actions"]
                               if action["id"] == "report_with_evidence")["result_variants"]
                          if variant.get("id")}
                self.assertTrue(reveal["holy_sword_diary"].endswith(REVEAL_DIARY_TEXT))
                self.assertTrue(reveal["holy_sword_neutral"].endswith(REVEAL_NO_DIARY_TEXT))
                self.assertNotIn(REVEAL_NO_DIARY_TEXT, reveal["holy_sword_diary"])
                self.assertNotIn(REVEAL_DIARY_TEXT, reveal["holy_sword_neutral"])

                blacksmith = next(action for action in locations["forge"]["actions"]
                                  if action["id"] == "show_sword_to_blacksmith")
                self.assertEqual(blacksmith["requirements"], {"character_id": "hero"})
                hint = next(variant for variant in blacksmith["result_variants"]
                            if variant["id"] == "holy_sword_blacksmith_hint")
                self.assertEqual(hint["difficulty_only"], ["normal"])
                self.assertEqual(hint["text"], blacksmith["result_text"] + BLACKSMITH_HINT)
                self.assertFalse(any("【仮】" in text for text in (
                    item["description"], item["effect"], item["awakening_origin"]["description_suffix"],
                    awakening["lock_text"], awakening["text"], stolen["text"],
                    stolen["extra_enemy_skills"][0]["name"], reveal["holy_sword_diary"],
                    reveal["holy_sword_neutral"], hint["text"],
                )))

                baby = difficulty.apply_difficulty(pack, "baby")
                baby_forge = next(location for location in baby["locations"] if location["id"] == "forge")
                baby_blacksmith = next(action for action in baby_forge["actions"]
                                       if action["id"] == "show_sword_to_blacksmith")
                self.assertFalse(any(variant.get("id") == "holy_sword_blacksmith_hint"
                                     for variant in baby_blacksmith.get("result_variants", [])))

    def test_hybrid_reveal_prepared_turns_follow_diary_inventory(self):
        pack = difficulty.apply_difficulty(state.load_scenario_pack(
            ROOT / "host/prompt/processed/dragon_rpg_hybrid.json"), "normal")
        for diary, expected_id, expected_text in (
            (False, "holy_sword_reveal_neutral", REVEAL_NO_DIARY_TEXT),
            (True, "holy_sword_reveal_diary", REVEAL_DIARY_TEXT),
        ):
            with self.subTest(diary=diary):
                value = checkpoints.fresh_session(pack, "hero", "normal", effective=True)
                value["flags"] = {"accepted_sword_fusion": True}
                value["world_state"] = {"scene_id": "castle_return", "location_id": "draco_battle"}
                if diary:
                    state.apply_state_delta(value, {"inventory_add": [{"name": "白竜の日誌"}]})
                value["last_action_result"] = {
                    "action_id": "report_with_evidence",
                    "outcome": "neutral",
                    "source_location_id": "castle_report",
                    "state_delta": {},
                }
                prepared = select_hybrid_prepared_turn(value, "将軍ドラコの正体を問いただす")
                self.assertEqual(prepared["id"], expected_id)
                self.assertIn(expected_text, prepared["draft"]["gm_text"])

        baby = difficulty.apply_difficulty(state.load_scenario_pack(
            ROOT / "host/prompt/processed/dragon_rpg_hybrid.json"), "baby")
        turns = next(location for location in baby["locations"] if location["id"] == "castle_report")["hybrid"]["prepared_turns"]
        self.assertFalse(any(turn.get("id") in {"holy_sword_reveal_neutral", "holy_sword_reveal_diary"}
                             for turn in turns))

    def test_blacksmith_hint_result_is_normal_only(self):
        base = state.load_scenario_pack(ROOT / "host/prompt/processed/dragon_rpg_hybrid.json")
        for mode, expected in (("normal", True), ("baby", False)):
            with self.subTest(mode=mode):
                pack = difficulty.apply_difficulty(base, mode)
                value = checkpoints.fresh_session(pack, "hero", mode, effective=True)
                forge = next(location for location in pack["locations"] if location["id"] == "forge")
                value["world_state"] = {"scene_id": forge["scene_id"], "location_id": "forge"}
                action = state.resolve_action(value, action_id="show_sword_to_blacksmith")
                self.assertIsNotNone(action)
                result = state.apply_action_result(value, action, {"expression": "none", "rolls": [], "total": 0, "dc": 0})
                self.assertEqual(BLACKSMITH_HINT in result["result_text"], expected)

    def test_iron_unsellable_normal_but_fusion_and_merchant_removal_work(self):
        value = session(False)
        iron = next(i for i in value["character"]["inventory"] if i.get("id") == "iron_sword")
        self.assertFalse(_can_sell({"buys": True}, iron))
        self.assertTrue(iron["description"].endswith(IRON_HINT))
        state.apply_state_delta(value, {"inventory_remove": [{"name": "鉄の剣"}]})
        self.assertFalse(any(i.get("id") == "iron_sword" for i in value["character"]["inventory"]))
        baby = checkpoints.fresh_session(difficulty.apply_difficulty(BASE, "baby"), "hero")
        iron = next(i for i in baby["character"]["inventory"] if i.get("id") == "iron_sword")
        self.assertTrue(_can_sell({"buys": True}, iron))

    def test_migration_idempotent_synced_and_g3_once_per_battle(self):
        sections = []
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            pack = json.loads((ROOT / "host/prompt/processed" / filename).read_text(encoding="utf-8"))
            self.assertEqual(migrate(pack), pack)
            draco = next(l["combat"] for l in pack["locations"] if l["id"] == "draco_battle")
            sections.append((draco, next(i for i in pack["items"] if i["id"] == "hero_holy_sword")))
            trigger = next(m for m in draco["encounter_modifiers"] if "lethal_awakening" in m)
            self.assertNotIn("survive_at_one", trigger["lethal_awakening"])
            self.assertEqual(trigger["difficulty_only"], ["normal"])
        self.assertEqual(*sections)
        value = session()
        hit(value)
        self.assertTrue(value["combat"]["lethal_awakenings"][0]["used"])
        hit(value)
        self.assertEqual(sum(e["kind"] == "awakening" for e in value["combat"]["log"]), 1)

    def test_hidden_endings_and_victory_text_follow_four_flag_combinations(self):
        cases = (
            ("awakened", "hero", {"defeated_ignis": True, "holy_sword_awakened": True},
             {"e1": True, "e2": False, "v1": False, "v2": True}),
            ("awakening_not_triggered", "hero", {},
             {"e1": False, "e2": False, "v1": False, "v2": False}),
            ("fusion_branch", "hero", {"defeated_ignis": True, "accepted_sword_fusion": True},
             {"e1": False, "e2": True, "v1": True, "v2": False}),
            ("non_hero", "mage", {"defeated_ignis": True, "accepted_sword_fusion": True},
             {"e1": False, "e2": False, "v1": False, "v2": False}),
        )
        observed_sections = []
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            source = state.load_scenario_pack(ROOT / "host/prompt/processed" / filename)
            pack = difficulty.apply_difficulty(source, "normal")
            locations = {location["id"]: location for location in pack["locations"]}
            human = next(enemy for enemy in pack["enemies"] if enemy["id"] == "draco_human")
            events = locations["draco_battle"]["combat"]["victory_events"]
            epilogues = {entry["id"]: entry for entry in pack["epilogues"]}
            observed_sections.append((
                [epilogues[key] for key in ("holy_sword_awakened_epilogue", "holy_sword_fusion_epilogue")],
                human["phase_transition_events"], events,
            ))
            self.assertEqual(epilogues["holy_sword_awakened_epilogue"]["text"], E1_TEXT)
            self.assertEqual(epilogues["holy_sword_fusion_epilogue"]["text"], E2_TEXT)
            self.assertTrue(all(entry["difficulty_only"] == ["normal"] for entry in (
                epilogues["holy_sword_awakened_epilogue"], epilogues["holy_sword_fusion_epilogue"],
                human["phase_transition_events"][0], events[-1],
            )))

            baby = difficulty.apply_difficulty(source, "baby")
            baby_location = next(location for location in baby["locations"] if location["id"] == "draco_battle")
            baby_human = next(enemy for enemy in baby["enemies"] if enemy["id"] == "draco_human")
            self.assertFalse(any(entry.get("id", "").startswith("holy_sword_")
                                 for entry in baby.get("epilogues", [])))
            self.assertFalse(any(event.get("id") == "holy_sword_fusion_phase_transition"
                                 for event in baby_human.get("phase_transition_events", [])))
            self.assertFalse(any(event.get("id") == "holy_sword_awakened_victory"
                                 for event in baby_location["combat"].get("victory_events", [])))

            for name, character_id, flags, expected in cases:
                with self.subTest(pack=filename, case=name):
                    value = gate_session(pack, CHOICES)
                    value["flags"] = dict(flags)
                    if character_id != "hero":
                        mage = next(template for template in pack["characters"] if template["id"] == character_id)
                        value["character"] = state._character_from_template(mage, pack)
                    combat.ensure_combat_started(value)

                    value["combat"]["enemies"][0]["hp"] = 0
                    combat._check_victory_or_defeat(value)
                    transition = next(entry for entry in value["combat"]["log"]
                                      if entry["kind"] == "phase_transition")
                    self.assertEqual(V1_TEXT in transition["text"], expected["v1"])

                    value["combat"]["enemies"][0]["hp"] = 0
                    combat._check_victory_or_defeat(value)
                    result = value["combat"]["result"]
                    self.assertEqual(V2_TEXT in result["prepared_text"], expected["v2"])
                    reason = value["combat"]["pending_state_delta"]["game_over"]["reason"]
                    self.assertEqual(V2_TEXT in reason, expected["v2"])
                    reward_reason = result["rewards"]["game_over"]["reason"]
                    self.assertEqual(V2_TEXT in reward_reason, expected["v2"])
                    aftermath = state._epilogue_lines(value, {"ending": "draco_defeated"})
                    self.assertEqual(E1_TEXT in aftermath, expected["e1"])
                    self.assertEqual(E2_TEXT in aftermath, expected["e2"])
        pack = difficulty.apply_difficulty(state.load_scenario_pack(
            ROOT / "host/prompt/processed/dragon_rpg.json"), "normal")
        value = gate_session(pack, CHOICES)
        value["flags"] = {"defeated_ignis": True, "holy_sword_awakened": True, "ignis_ally": True}
        combat.ensure_combat_started(value)
        value["combat"]["enemies"][0]["hp"] = 0
        combat._check_victory_or_defeat(value)
        value["combat"]["enemies"][0]["hp"] = 0
        combat._check_victory_or_defeat(value)
        game_over = value["combat"]["pending_state_delta"]["game_over"]
        self.assertEqual(game_over["ending"], "draco_defeated_with_ignis")
        self.assertIn(V2_TEXT, game_over["reason"])
        self.assertEqual(observed_sections[0], observed_sections[1])

    def test_baby_effective_diff_only_revision(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            raw = subprocess.check_output(["git", "show", f"HEAD:host/prompt/processed/{filename}"])
            from scripts.scenario.mina_reborrow_055 import migrate as mina_reborrow
            before = difficulty.apply_difficulty(mina_reborrow(json.loads(raw)), "baby")
            after = difficulty.apply_difficulty(json.loads((ROOT / "host/prompt/processed" / filename).read_text(encoding="utf-8")), "baby")
            before["meta"]["content_revision"] = after["meta"]["content_revision"]
            # Inactive authoring overlays are retained by apply_difficulty.
            before.pop("difficulty_overlays", None)
            after.pop("difficulty_overlays", None)
            def remove_empty_result_variants(value):
                if isinstance(value, dict):
                    for key, child in list(value.items()):
                        if key == "result_variants" and child == []:
                            value.pop(key)
                        else:
                            remove_empty_result_variants(child)
                elif isinstance(value, list):
                    for child in value:
                        remove_empty_result_variants(child)
            remove_empty_result_variants(before)
            remove_empty_result_variants(after)
            # 054 explicitly adds shared inert definitions; verify only those exact changes.
            old_defs = {s["id"]: s for s in before["status_defs"]}
            new_defs = {s["id"]: s for s in after["status_defs"]}
            self.assertEqual(set(new_defs) - set(old_defs), {"haze"} if "haze" not in old_defs else set())
            for sid in ("poison", "paralysis", "weaken", "blind"):
                old_defs[sid]["tags"] = [sid, "debuff"]
            for sid, definition in old_defs.items():
                self.assertEqual(new_defs[sid], definition)
            before["status_defs"] = after["status_defs"]
            for character_id, skill_id, description in (
                ("hero", "divine_guard", "被ダメージを半減し、致死ダメージもHP1で耐える。"),
                ("thief", "hide_in_shadow", "影に溶けて身を隠し、被ダメージを0.25倍にする。致死ダメージもHP1で耐える。"),
            ):
                current_character = next(character for character in after["characters"]
                                         if character["id"] == character_id)
                old_character = next(character for character in before["characters"]
                                     if character["id"] == character_id)
                current_skill = next(skill for skill in current_character["skills"] if skill["id"] == skill_id)
                old_skill = next(skill for skill in old_character["skills"] if skill["id"] == skill_id)
                self.assertEqual(current_skill["description"], description, filename)
                current_skill["description"] = old_skill["description"]
            old_items = {item["id"]: item for item in before["items"]}
            new_items = {item["id"]: item for item in after["items"]}
            old_items["poison_dart"]["description"] = new_items["poison_dart"]["description"]
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
