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
from host.shops import _can_sell
from scripts.balance import checkpoints, probes_v3
from scripts.balance.holy_sword_049 import gate_session, run_jobs
from scripts.scenario.holy_sword_049 import AWAKEN_TEXT, REVEAL_TEXT, START_TEXT, migrate

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
        self.assertEqual((actor["hp"], actor["mp"], actor["sp"]), (45, 3, 7))
        self.assertEqual(actor["statuses"], [{"id": "test", "remaining_rounds": 8}])
        self.assertTrue(value["flags"]["holy_sword_awakened"])
        self.assertEqual([i["name"] for i in equipped_items(actor)], ["勇者の聖剣", "革の鎧"])
        entries = [e for e in value["combat"]["log"] if e["kind"].startswith("awakening")]
        self.assertEqual([e["kind"] for e in entries], ["awakening_lock", "awakening"])
        self.assertEqual(entries[0]["state"]["player"]["hp"], 1)
        self.assertEqual(entries[1]["state"]["player"]["hp"], 45)
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
            self.assertEqual(value["character"]["hp"], 45)
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
                self.assertEqual(actor["hp"], 45)

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
            self.assertEqual(value["character"]["hp"], 0 if awaken_first else 45)

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
                self.assertIn(REVEAL_TEXT, text)
                self.assertEqual("日誌を掲げる" in text, diary)
                evidence.append({"mode": mode, "allow_narration": narration, "diary": diary, "text": text})
        (ROOT / ".tmp-test/049/reveal-modes.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_iron_unsellable_normal_but_fusion_and_merchant_removal_work(self):
        value = session(False)
        iron = next(i for i in value["character"]["inventory"] if i.get("id") == "iron_sword")
        self.assertFalse(_can_sell({"buys": True}, iron))
        self.assertIn("【仮】", iron["description"])
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

    def test_baby_effective_diff_only_revision(self):
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            raw = subprocess.check_output(["git", "show", f"HEAD:host/prompt/processed/{filename}"])
            from scripts.scenario.mina_reborrow_055 import migrate as mina_reborrow
            before = difficulty.apply_difficulty(mina_reborrow(json.loads(raw)), "baby")
            after = difficulty.apply_difficulty(json.loads((ROOT / "host/prompt/processed" / filename).read_text(encoding="utf-8")), "baby")
            before["meta"]["content_revision"] = after["meta"]["content_revision"]
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
