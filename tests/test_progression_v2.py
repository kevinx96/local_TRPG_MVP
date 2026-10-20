from __future__ import annotations

import json
import random
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from host import app, combat, difficulty, progression, state, status_effects
from host.scenario_context import load_scenario_pack
from scripts.scenario.levels_skills_v2 import migrate

ROOT = Path.cwd()
BASE = load_scenario_pack(ROOT / "host/prompt/processed/dragon_rpg.json")
NORMAL = difficulty.apply_difficulty(BASE, "normal")


class Rolls:
    def randint(self, low, high):
        return low

    def choice(self, values):
        return values[0]


def session(cid="hero", level=1, start=True, mode="normal"):
    pack = deepcopy(NORMAL if mode == "normal" else difficulty.apply_difficulty(BASE, "baby"))
    actor = state._character_from_template(next(c for c in pack["characters"] if c["id"] == cid), pack)
    actor["level"] = level
    pack["locations"] = [{"id": "arena", "scene_id": "arena", "enemy_ids": ["dummy"],
                          "combat": {"encounter_class": "trash"}}]
    pack["scenes"] = [{"id": "arena", "location_ids": ["arena"]}]
    pack["enemies"] = [{"id": "dummy", "name": "【仮】", "hp": 1000, "max_hp": 1000, "skills": [],
                        "combat": {"basic_attack": {"damage": "1", "accuracy": 100}, "evade": 0},
                        "resistances": {"physical": 1, "fire": 1, "ice": 1, "holy": 1, "arcane": 1}}]
    pack["combat_rules"].update(evade_model="fixed", sp_regen_per_round=0)
    s = {"id": "test", "character": actor, "scenario_pack": pack, "difficulty": mode, "flags": {},
         "world_state": {"scene_id": "arena", "location_id": "arena"}, "event_log": [], "system_logs": [],
         "messages": [], "combat": None, "area_snapshots": {}, "choices": [], "next_dice_dc": 0}
    progression.initialize(s)
    if start:
        combat.ensure_combat_started(s)
    return s


def select(s, identifier, tier=1):
    s["character"]["passives"] = [{"id": identifier, "tier": tier}]


def use(s, identifier):
    s["character"].update(mp=200, sp=200, max_mp=200, max_sp=200)
    s["combat"]["actions_remaining"] = 20
    return combat.perform_combat_action(s, "skill", identifier, rng=Rolls())


class ProgressionTests(unittest.TestCase):
    def test_baby_level_golden(self):
        from baby_levels_golden import generate
        expected = json.loads((Path(__file__).parent / "fixtures/baby_levels_golden.json").read_text(encoding="utf-8"))
        self.assertEqual(generate(), expected)

    def test_level_rewards_growth_events_and_cap(self):
        for cid in ("hero", "cleric", "mage", "thief"):
            s = session(cid, start=False)
            before = deepcopy(s["character"])
            progression.reward(s, 500, "combat:test")
            actor = s["character"]
            self.assertEqual((actor["level"], actor["exp"]), (8, 500))
            self.assertEqual(s["pending_passive_choices"], [2, 4, 6, 8])
            self.assertEqual(sum(e["kind"] == "level_up" for e in s["event_log"]), 7)
            for resource in ("hp", "mp", "sp"):
                maximum = "max_" + resource
                self.assertEqual(actor[maximum], before[maximum] + 7 * NORMAL["progression"]["level_gains"][cid][maximum])
                self.assertEqual(actor[resource], actor[maximum])
            self.assertEqual(len([e for e in s["event_log"] if e["kind"] == "skill_gained"]), 3)
            self.assertIsNone(progression.public_progression(s)["exp_to_next"])
            progression.reward(s, 5, "combat:again")
            self.assertEqual(actor["exp"], 505)

    def test_all_encounter_rewards_and_zero_nonvictory(self):
        for category, expected in (("trash", 5), ("elite", 15), ("boss", 40), ("guest", 0), ("scripted_loss", 0), (None, 5)):
            s = session()
            s["combat"]["encounter"]["encounter_class"] = category
            for _ in range(2):
                delta = combat._victory_delta(s, s["combat"]["enemies"], s["combat"]["encounter"])
                state.apply_state_delta(s, delta)
            self.assertEqual(s["character"]["exp"], expected * 2)
        for outcome in ("fled", "defeat", "bypassed"):
            s = session()
            combat._finish_combat(s, outcome, "【仮】")
            self.assertNotIn("_exp_reward", s["combat"].get("pending_state_delta", {}))
            self.assertEqual(s["character"]["exp"], 0)

    def test_quests_once_and_main_excluded(self):
        s = session(start=False)
        s["scenario_pack"]["quests"] = [
            {"id": q, "title": "【仮】", "description": "【仮】", "kind": "side", "complete_flags": [q]}
            for q in ("side", "main_ignis")]
        for _ in range(2):
            state.apply_state_delta(s, {"flags_set": ["side", "main_ignis"]})
        self.assertEqual(s["character"]["exp"], 10)
        s["event_log"] = [{"kind": "other"}] * 240
        state.apply_state_delta(s, {"flags_unset": ["side"]})
        state.apply_state_delta(s, {"flags_set": ["side"]})
        self.assertEqual(s["character"]["exp"], 10)

    def test_committed_progression_events_survive_log_truncation(self):
        s = session(start=False)
        s["event_log"] = [{"kind": "old", "text": "", "data": {}}] * 240
        s["character"]["exp"] = 15
        combat.ensure_combat_started(s)
        combat._finish_combat(s, "victory", "【仮】")
        state.apply_state_delta(s, combat.consume_combat_state_delta(s))
        events = combat.combat_result_for_llm(s)["committed_events"]
        self.assertIn("exp_gained", [e["kind"] for e in events])
        self.assertIn("level_up", [e["kind"] for e in events])
        self.assertIn("passive_choice_pending", [e["kind"] for e in events])
        self.assertNotIn("old", [e["kind"] for e in events])

    def test_milestones_and_model_rejection(self):
        s = session(start=False)
        state.apply_state_delta(s, {"flags_set": ["passed_forest_wolves", "cleared_goblin_fort"]})
        self.assertEqual(s["character"]["level"], 1)
        self.assertFalse(s.get("completed_milestones"))
        keys = ("exp", "level", "passives", "learned_spells", "pending_passive_choices", "_exp_reward")
        self.assertEqual(state.sanitize_model_state_delta(s, {key: 999 for key in keys}), {})
        for key in keys:
            self.assertIn(key, s["system_logs"][-1]["text"])

    def test_choice_order_stack_and_pure_input(self):
        s = session("cleric", 8, start=False)
        before = deepcopy(s)
        with self.assertRaises(ValueError):
            progression.choose_passive(s, 4, "pious_heart")
        with self.assertRaises(ValueError):
            progression.choose_passive(s, 2, "mana_cycle")
        s = progression.choose_passive(s, 2, "pious_heart")
        self.assertEqual(before["character"]["passives"], [])
        s = progression.choose_passive(s, 4, "pious_heart")
        s = progression.choose_passive(s, 6, "overflow_mercy")
        s = progression.choose_passive(s, 8, "pious_heart")
        public = progression.public_progression(s)
        self.assertEqual([p["name"] for p in public["passives"]], ["敬虔なる心+2", "溢れる慈愛"])
        self.assertEqual(public["pending"], [])
        s = session("cleric", 6, start=False)
        s = progression.choose_passive(s, 2, "pious_heart")
        s = progression.choose_passive(s, 4, "ascetic_wisdom")
        s = progression.choose_passive(s, 6, "overflow_mercy")
        self.assertEqual(s["character"]["passives"][-1]["tier"], 1)

    def test_choice_api_and_combat_rejection(self):
        s = session("hero", 2)
        with patch.object(app, "load_session", return_value=s):
            with self.assertRaises(HTTPException) as caught:
                app.api_choose_passive("test", app.PassiveChoiceRequest(level=2, passive_id="departure_spirit"))
        self.assertEqual(caught.exception.status_code, 400)

    def test_migration_levels_curse_deferred_and_idempotence(self):
        for cid in ("hero", "cleric", "mage", "thief"):
            for level in (1, 3, 5):
                s = session(cid, level, start=False, mode="baby")
                state._unlock_level_skills(s)
                old = deepcopy(s["character"])
                s["difficulty"], s["scenario_pack"] = "normal", deepcopy(NORMAL)
                s["combat"] = {"status": "active"}
                self.assertFalse(progression.initialize(s))
                self.assertNotIn("exp", s["character"])
                s["combat"] = None
                self.assertTrue(progression.initialize(s))
                self.assertEqual(s["character"]["exp"], NORMAL["progression"]["exp_table"].get(str(level), 0))
                for key in ("attributes", "max_hp", "max_mp", "max_sp", "hp"):
                    self.assertEqual(s["character"][key], old[key])
                self.assertEqual(s["pending_passive_choices"], [n for n in (2, 4) if n <= level])
                frozen = deepcopy(s)
                self.assertFalse(progression.initialize(s))
                self.assertEqual(s, frozen)
        s = session("mage", 3, start=False)
        select(s, "mana_cycle")
        state.apply_state_delta(s, {"clear_skills": True})
        progression.initialize(s)
        self.assertEqual(s["character"]["skills"], [])
        self.assertEqual(s["character"]["learned_spells"], [])
        progression.reward(s, 100, "test")
        self.assertEqual([x["id"] for x in s["character"]["skills"]], ["twin_storm"])
        self.assertTrue(s["character"]["passives"])

    def test_spellbooks_learning_order_rejections_and_public(self):
        s = session("mage", start=False)
        for identifier in ("spellbook_lightning", "spellbook_arcane_lance"):
            book = deepcopy(next(i for i in NORMAL["items"] if i["id"] == identifier))
            book["quantity"] = 2
            s["character"]["inventory"].append(book)
            s = progression.learn_spell(s, identifier)
            self.assertEqual(next(i for i in s["character"]["inventory"] if i.get("id") == identifier)["quantity"], 1)
            with self.assertRaises(ValueError):
                progression.learn_spell(s, identifier)
        self.assertEqual(s["character"]["learned_spells"], ["fireball", "ice_arrow", "lightning", "arcane_lance"])
        public = state.public_session(s)
        self.assertFalse(next(i for i in public["character"]["inventory"] if i.get("id") == "spellbook_lightning")["learn"]["enabled"])
        for cid in ("hero", "cleric", "thief"):
            other = session(cid, start=False)
            other["character"]["inventory"].append(book)
            with self.assertRaises(ValueError):
                progression.learn_spell(other, book["id"])
        s = session("mage")
        s["character"]["inventory"].append(book)
        with self.assertRaises(ValueError):
            progression.learn_spell(s, book["id"])

    def test_dynamic_elements_two_to_five_and_stable_ranking(self):
        s = session("mage", 7)
        actor, target = s["character"], s["combat"]["enemies"][0]
        for count in (2, 3, 4, 5):
            elements = ["fire", "ice", "lightning", "arcane", "wind"][:count]
            actor["skills"] = [{"id": e, "element": e, "spell_tier": "basic"} for e in elements]
            actor["learned_spells"] = elements
            target["resistances"] = {e: 1 for e in elements}
            self.assertEqual(combat._learned_elements(actor, target, 4), elements[:4])
        target["resistances"]["wind"] = 2
        self.assertEqual(combat._learned_elements(actor, target, 4), ["wind", "fire", "ice", "lightning"])
        s = session("mage", 7)
        s["character"]["learned_spells"] = []
        use(s, "elemental_collapse")
        self.assertFalse(any(e["kind"] == "damage" for e in s["combat"]["log"]))

    def test_filtering_and_migration_script(self):
        for mode in ("baby", "normal"):
            original = deepcopy(BASE)
            result = difficulty.apply_difficulty(BASE, mode)
            self.assertEqual(BASE, original)
            books = [i for i in result["items"] if i.get("category") == "spellbook"]
            self.assertEqual(len(books), 2 if mode == "normal" else 0)
            offers = next(shop for shop in result["shops"] if shop["id"] == "magic_shop")["items"]
            self.assertEqual(sum(i["item_id"].startswith("spellbook_") for i in offers), len(books))
        for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            base = json.loads((ROOT / "host/prompt/processed" / filename).read_text(encoding="utf-8"))
            self.assertEqual(migrate(base), base)
            self.assertEqual(migrate(migrate(base)), base)

    def test_each_active_executes_costs_and_server_rejects(self):
        for definition in NORMAL["class_progression"]:
            for entry in definition["actives"]:
                with self.subTest(cid=definition["id"], skill=entry["skill"]["id"]):
                    s = session(definition["id"], 8)
                    actor = s["character"]
                    actor.update(mp=100, sp=100, max_mp=100, max_sp=100)
                    actor["hp"] = max(1, actor["max_hp"] // 2)
                    s["combat"]["actions_remaining"] = 20
                    skill = entry["skill"]
                    resolved = combat._player_ability(s, "skill", skill["id"])
                    costs = resolved["_resolved_costs"]
                    combat.perform_combat_action(s, "skill", skill["id"], rng=Rolls())
                    for resource, cost in costs.items():
                        expected = 100 - cost
                        if skill.get("resource") == resource:
                            expected = min(100, expected + combat._roll_formula(skill["amount"], actor, Rolls())[0])
                        self.assertEqual(actor[resource], expected)
                    actor.update(mp=0, sp=0)
                    with self.assertRaises(combat.CombatError):
                        combat.perform_combat_action(s, "skill", skill["id"], rng=Rolls())

    def test_afterglow_overflow_cap_none_and_mercy(self):
        for missing in (0, 1, 99):
            s = session("cleric", 5)
            actor = s["character"]
            actor["hp"] = max(1, actor["max_hp"] - missing)
            select(s, "overflow_mercy")
            use(s, "great_heal_cleanse")
            shields = [st for st in actor.get("statuses", []) if st["id"] == "holy_afterglow"]
            if missing < 2:
                self.assertTrue(shields)
                self.assertGreater(shields[0]["shield_remaining"], 0)
                self.assertLessEqual(shields[0]["shield_remaining"], actor["max_hp"] * .25)
                self.assertLess(s["combat"]["enemies"][0]["hp"], 1000)
            else:
                self.assertFalse(shields)

    def test_dual_strike_snapshot_and_basic_bonuses(self):
        s = session("mage", 5)
        use(s, "twin_storm")
        damages = [e["data"] for e in s["combat"]["log"] if e["kind"] == "damage" and e["actor"] == "player"]
        self.assertEqual(damages[0]["raw_damage"], 2 * damages[1]["raw_damage"])
        for skill_id, ratios in (("fireball", (1, .99)), ("ice_arrow", (.5, .51))):
            outputs = []
            for ratio in ratios:
                s = session("mage")
                s["combat"]["enemies"][0]["hp"] = int(1000 * ratio)
                use(s, skill_id)
                outputs.append(next(e["data"]["raw_damage"] for e in s["combat"]["log"] if e["kind"] == "damage"))
            self.assertEqual(outputs[0] - outputs[1], 1)

    def test_dragon_ignores_reduction_preserves_weakness(self):
        amounts = []
        for resistance in (0, .25, 1, 2):
            s = session("hero", 7)
            target = s["combat"]["enemies"][0]
            target["resistances"]["physical"] = resistance
            target["combat"]["defense"] = 100
            use(s, "dragon_slash")
            amounts.append(1000 - target["hp"])
        self.assertEqual(amounts[0], amounts[2])
        self.assertEqual(amounts[1], amounts[2])
        self.assertEqual(amounts[3], amounts[2] * 2)

    def test_gospel_limit_haste_and_free_guard(self):
        s = session("cleric", 7)
        maximum = s["character"]["max_hp"]
        use(s, "seraphim_gospel")
        self.assertEqual(s["character"]["max_hp"], maximum * 2)
        with self.assertRaises(combat.CombatError):
            use(s, "seraphim_gospel")
        s = session("thief", 7)
        use(s, "shadow_haste")
        self.assertEqual(s["combat"]["actions_remaining"], 20)
        with self.assertRaises(combat.CombatError):
            use(s, "shadow_haste")
        s = session()
        select(s, "unsinkable_shield")
        before = s["combat"]["actions_remaining"]
        combat.perform_combat_action(s, "skill", "divine_guard", rng=Rolls())
        self.assertEqual(s["combat"]["actions_remaining"], before)
        self.assertEqual(s["combat"]["round"], 1)
        self.assertEqual(s["combat"]["cooldowns"]["skill:divine_guard"]["remaining"], 2)
        with self.assertRaises(combat.CombatError):
            combat.perform_combat_action(s, "skill", "divine_guard", rng=Rolls())

    def test_all_passive_tiers_have_runtime_effects(self):
        for definition in NORMAL["class_progression"]:
            for entry in definition["passives"]:
                for tier in entry["tiers"]:
                    with self.subTest(cid=definition["id"], passive=entry["id"], tier=tier["tier"]):
                        s = session(definition["id"])
                        select(s, entry["id"], tier["tier"])
                        self.assertEqual(progression.effects(s), tier["effects"])
                        s["character"]["mp"] = 0
                        combat._passive_round_start(s, Rolls())
                        combat._passive_round_end(s)
                        combat._enemy_reaction(s, s["combat"]["enemies"][0], Rolls(), missed=True)
                        self.assertGreater(s["character"]["hp"], 0)

    def test_opening_sp_accuracy_and_regen_each_tier(self):
        for tier in (1, 2):
            s = session()
            select(s, "departure_spirit", tier)
            for n in range(1, 4):
                s["combat"]["round"] = n
                before = s["character"]["sp"]
                combat._passive_round_start(s, Rolls())
                self.assertEqual(s["character"]["sp"] - before, 3 if n <= tier else 0)
                if n <= tier:
                    self.assertEqual(combat.attack_chance(s, s["character"], s["combat"]["enemies"][0], {"accuracy": 1}, "player"), 100)
            combat._finish_combat(s, "fled", "【仮】")
            self.assertEqual(s["character"]["sp"], s["character"]["max_sp"])
        for tier, ratio in enumerate((.03, .05, .07), 1):
            s = session("cleric")
            select(s, "pious_heart", tier)
            s["character"].update(hp=1, max_hp=10)
            for _ in range(10):
                combat._passive_round_end(s)
            self.assertEqual(s["character"]["hp"], 1 + round(100 * ratio))
            s["character"]["hp"] = 0
            combat._passive_round_end(s)
            self.assertEqual(s["character"]["hp"], 0)

    def test_mana_cycle_acrobat_caps_all_tiers(self):
        for tier, cap in enumerate((20, 30, 40), 1):
            s = session("mage")
            select(s, "mana_cycle", tier)
            s["character"].update(mp=0, max_mp=100)
            for n in range(1, 101):
                s["combat"]["round"] = n
                combat._passive_round_start(s, Rolls())
            self.assertEqual(s["character"]["mp"], cap)
        for tier, evade, cap in ((1, 5, 2), (2, 8, 3), (3, 10, 4)):
            s = session("thief")
            base = combat.actor_evade(s, s["character"])
            select(s, "acrobatics", tier)
            self.assertEqual(combat.actor_evade(s, s["character"]), min(40, base + evade))
            s["character"]["sp"] = 0
            for _ in range(10):
                combat._enemy_reaction(s, s["combat"]["enemies"][0], Rolls(), missed=True)
            self.assertEqual(s["character"]["sp"], cap)
            combat._passive_round_start(s, Rolls())
            combat._enemy_reaction(s, s["combat"]["enemies"][0], Rolls(), missed=True)
            self.assertGreater(s["character"]["sp"], cap)

    def test_shield_regain_armor_counter_and_halo(self):
        s = session("mage", start=False)
        select(s, "arcane_guard", 2)
        combat.ensure_combat_started(s)
        actor, enemy = s["character"], s["combat"]["enemies"][0]
        for n in range(3):
            before = actor["hp"]
            combat._resolve_attack(s, enemy, actor, {"damage": "5", "accuracy": 100}, "enemy", Rolls())
            self.assertEqual(before - actor["hp"], 0 if n == 0 else 5 - int(actor["max_hp"] * .2))
            s["combat"]["round"] += 3
            combat._passive_round_start(s, Rolls())
        self.assertFalse(any(st["id"] == "arcane_shield" for st in actor.get("statuses", [])))
        s = session("mage")
        select(s, "mana_armor")
        actor = s["character"]
        before = actor["hp"]
        combat._resolve_attack(s, s["combat"]["enemies"][0], actor, {"damage": "6", "ignores_defense": True}, "enemy", Rolls())
        self.assertEqual(before - actor["hp"], 4)
        s = session("thief")
        select(s, "counter_sight")
        enemy = s["combat"]["enemies"][0]
        for _ in range(5):
            combat._enemy_reaction(s, enemy, Rolls(), missed=True)
        self.assertEqual(enemy["hp"], 995)
        for hp, hit in ((70, False), (71, True)):
            s = session("cleric")
            select(s, "holy_halo")
            s["character"].update(max_hp=100, hp=hp)
            combat._passive_round_start(s, Rolls())
            self.assertEqual(s["combat"]["enemies"][0]["hp"] < 1000, hit)

    def test_free_heal_exchange_adversity_resonance_and_poison(self):
        s = session("cleric")
        select(s, "immortal_sanctuary")
        identifier = progression.effects(s)["free_skills"][0]
        self.assertEqual(combat._player_ability(s, "skill", identifier)["_resolved_costs"]["mp"], 0)
        select(s, "ascetic_wisdom")
        ability = combat._normal_skill(s, {"cost": 9, "cost_type": "mp"})
        self.assertLessEqual(ability["_resolved_costs"]["mp"], 9)
        s = session("hero")
        select(s, "adversity_flame")
        s["character"]["hp"] = 9
        ability = combat._normal_skill(s, {"costs": {"mp": 5, "sp": 7}, "damage": "1"})
        self.assertEqual(ability["_resolved_costs"], {"mp": 3, "sp": 4})
        s["character"]["hp"] = 10
        self.assertNotIn("damage_multiplier", combat._normal_skill(s, {"cost": 1}))
        s = session("mage", 7)
        select(s, "element_resonance")
        first = {"spell_tier": "basic", "element": "fire"}
        combat._prepare_spell(s, first)
        self.assertNotIn("damage_multiplier", first)
        second = {"spell_tier": "basic", "element": "ice"}
        combat._prepare_spell(s, second)
        self.assertEqual(second["damage_multiplier"], 1.15)
        for tier, cap in ((1, 3), (2, 5)):
            s = session("thief")
            select(s, "poison_craft", tier)
            enemy = s["combat"]["enemies"][0]
            for _ in range(8):
                combat._passive_hit(s, enemy, {"_basic_action": True}, Rolls())
            self.assertEqual(enemy["statuses"][0]["stacks"], cap)

    def test_armor_penetration_omni_and_assassin_damage(self):
        for identifier in (None, "heavy_armor_lore"):
            s = session()
            if identifier:
                select(s, identifier)
            actor = s["character"]
            before = actor["hp"]
            combat._resolve_attack(s, s["combat"]["enemies"][0], actor, {"damage": "10"}, "enemy", Rolls())
            if identifier is None:
                base = before - actor["hp"]
            else:
                self.assertEqual(before - actor["hp"], base - 1)
        s = session()
        select(s, "sword_saint")
        enemy = s["combat"]["enemies"][0]
        enemy["combat"]["defense"] = 10
        enemy["resistances"]["physical"] = .5
        amount = combat._resolve_attack(s, s["character"], enemy, {"damage": "40", "element": "physical"}, "player", Rolls())
        self.assertEqual(amount, 19)
        s = session("mage")
        select(s, "omni_master")
        combat._player_attack(s, "", Rolls())
        event = next(e for e in s["combat"]["log"] if e["kind"] == "damage")
        self.assertEqual(event["data"]["element"], "arcane")
        s = session("mage")
        select(s, "omni_master")
        s["combat"]["enemies"][0]["resistances"]["ice"] = 2
        combat._player_attack(s, "", Rolls())
        event = next(e for e in s["combat"]["log"] if e["kind"] == "damage")
        self.assertEqual(event["data"]["element"], "ice")
        s = session("thief")
        select(s, "unseen_assassin")
        s["combat"]["encounter"]["encounter_class"] = "elite"
        amount = combat._resolve_attack(s, s["character"], s["combat"]["enemies"][0], {"damage": "20"}, "player", Rolls())
        self.assertEqual(amount, 23)

    def test_followups_do_not_chain_and_free_item_once(self):
        s = session("hero", 3)
        s["character"]["passives"] = [{"id": "sword_followup", "tier": 1}, {"id": "dragon_destiny", "tier": 1}]
        enemy = s["combat"]["enemies"][0]
        enemy["resistances"]["ice"] = 2
        status_effects.apply(s, enemy, "holy_mark", s["character"], Rolls())
        use(s, "holy_sword_art")
        hits = [e for e in s["combat"]["log"] if e["actor"] == "player" and e["kind"] == "damage"]
        self.assertEqual(len(hits), 6)  # two sword segments + two marks + two passives
        s = session("hero")
        select(s, "dragon_destiny")
        before = s["character"]["hp"]
        combat._resolve_attack(s, s["combat"]["enemies"][0], s["character"],
                               {"damage": "10", "element": "fire", "ignores_defense": True}, "enemy", Rolls())
        self.assertEqual(before - s["character"]["hp"], 8)
        status_effects.apply(s, s["character"], {"id": "burn", "tick": {"damage": "10", "element": "fire"}},
                             enemy, Rolls())
        before = s["character"]["hp"]
        status_effects.tick(s, s["character"], Rolls())
        self.assertEqual(before - s["character"]["hp"], 8)
        s = session("thief")
        select(s, "hidden_weapon_master")
        herb = {"id": "test_herb", "name": "薬草", "quantity": 2, "combat": {"kind": "heal", "healing": "1"}}
        s["character"]["inventory"].append(herb)
        s["combat"]["actions_remaining"] = 3
        combat.perform_combat_action(s, "item", "test_herb", rng=Rolls())
        self.assertEqual(s["combat"]["actions_remaining"], 3)
        combat.perform_combat_action(s, "item", "test_herb", rng=Rolls())
        self.assertEqual(s["combat"]["actions_remaining"], 2)

    def test_mark_miss_blessing_miss_and_conditions(self):
        class Miss(Rolls):
            def randint(self, low, high):
                return high
        s = session("cleric", 3)
        s["combat"]["actions_remaining"] = 5
        combat.perform_combat_action(s, "skill", "atonement_mark", rng=Miss())
        self.assertFalse(s["combat"]["enemies"][0].get("statuses"))
        s = session("hero", 3)
        s["combat"]["actions_remaining"] = 5
        combat.perform_combat_action(s, "skill", "holy_sword_art", rng=Miss())
        self.assertTrue(any(st["id"] == "holy_blessing" for st in s["character"].get("statuses", [])))
        target = s["combat"]["enemies"][0]
        for hp, expected in ((79, False), (80, True)):
            target["max_hp"] = hp
            self.assertEqual(combat._condition(s, {"if": "target_max_hp_gte", "value": 80}, target), expected)
        for identifier in ("ignis", "draco_dragon", "dragon_knight_mounted", "lava_drake"):
            target["template_id"] = identifier
            condition = progression.definition(session("hero"))["actives"][2]["skill"]["conditional_multipliers"][0]
            self.assertTrue(combat._condition(s, condition, target))
        self.assertTrue(combat._condition(s, {"if": "single_enemy"}, target))
        s["combat"]["enemies"].append(deepcopy(target))
        self.assertFalse(combat._condition(s, {"if": "single_enemy"}, target))

    def test_validate_bad_progression_tables(self):
        for path, value in (("exp_table", {"2": 20}), ("exp_table", {str(n): 20 for n in range(2, 9)}),
                            ("exp_rewards", {"trash": -1}), ("level_gains", {"hero": {}})):
            pack = deepcopy(BASE)
            next(e for e in pack["difficulty_overlays"]["normal"] if e["entity"] == "progression" and e["path"] == path)["set"] = value
            with self.assertRaises(ValueError):
                difficulty.apply_difficulty(pack, "normal")

    def test_save_load_snapshots_and_no_new_baby_fields(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory, patch.object(state, "SAVE_DIR", Path(directory)):
            s = session("mage", 5, start=False)
            s["area_snapshots"] = {"arena": {"state": {"character": deepcopy(s["character"])}}}
            state.save_session(s)
            loaded = state.load_session(s["id"])
            self.assertEqual(loaded["pending_passive_choices"], [2, 4])
            self.assertEqual(loaded["character"]["learned_spells"], ["fireball", "ice_arrow"])
            chosen = progression.choose_passive(loaded, 2, "mana_cycle")
            state.save_session(chosen)
            loaded = state.load_session(s["id"])
            self.assertEqual(loaded["pending_passive_choices"], [4])
            for mode in (None, "baby"):
                s = session(start=False, mode="baby")
                if mode is None:
                    s.pop("difficulty")
                before = deepcopy(s["character"])
                state.save_session(s)
                loaded = state.load_session(s["id"])
                self.assertNotIn("exp", loaded["character"])
                self.assertNotIn("progression_revision", loaded)
                self.assertNotIn("progression", state.public_session(loaded))
                self.assertEqual(loaded["character"]["skills"], before["skills"])


if __name__ == "__main__":
    unittest.main()
