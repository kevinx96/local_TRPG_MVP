from __future__ import annotations

import json
import random
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import combat, difficulty, state, status_effects
from scripts.balance import budget, checkpoints, policy_v3
from scripts.scenario import normal_tuning_052


class Telegraph052Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cls.pack = difficulty.apply_difficulty(cls.base, "normal")

    def session(self, character="hero"):
        session = checkpoints.fresh_session(deepcopy(self.pack), character, "normal", effective=True)
        session["world_state"] = {"scene_id": "forest_wolves", "location_id": "forest_wolves"}
        session["combat_start_requested"] = True
        combat.ensure_combat_started(session)
        actor = session["character"]
        actor.update(hp=100, max_hp=100, statuses=[], equipment=[], inventory=[])
        session["combat"]["encounter"] = {"encounter_class": "elite"}
        enemy = session["combat"]["enemies"][0]
        enemy.update(hp=1000, max_hp=1000, statuses=[], skills=[])
        enemy["combat"].pop("basic_attack_weight", None)
        session["combat"]["enemies"] = [enemy]
        return session, actor, enemy

    def strike(self, session, enemy, ratio=.25, **fields):
        with patch.object(combat, "_enemy_reaction"):
            return combat._resolve_attack(session, enemy, session["character"],
                {"id": "test", "name": "氷槌", "kind": "attack", "accuracy": 100,
                 "damage_max_hp_ratio": ratio, **fields}, enemy["id"], random.Random(1))

    def test_percentage_floors_current_maximum_and_ignores_flat_defense(self):
        session, actor, enemy = self.session()
        actor.update(max_hp=103, hp=103)
        actor["combat"]["defense"] = 999
        self.assertEqual(self.strike(session, enemy), 25)

    def test_guard_received_multiplier_resistance_and_shield(self):
        for mode, expected in (("guard", 12), ("received", 12), ("resist", 18), ("shield", 0)):
            session, actor, enemy = self.session()
            if mode == "guard":
                session["combat"]["player_status"]["guard_multiplier"] = .5
            if mode == "received":
                actor["statuses"] = [{"status_v2": True, "modifiers": {"received_damage_multiplier": .5}}]
            if mode == "resist":
                actor["resistances"] = {"fire": .7}
            if mode == "shield":
                status_effects.apply(session, actor, "arcane_shield", actor, random.Random(1))
            self.assertEqual(self.strike(session, enemy, element="fire"), expected, mode)

    def test_percentage_can_miss(self):
        session, actor, enemy = self.session()
        with patch.object(combat, "attack_chance", return_value=5):
            self.assertEqual(self.strike(session, enemy), 0)
        self.assertEqual(actor["hp"], 100)

    def test_shared_elite_cap_persists_within_round_and_resets_next_round(self):
        session, actor, enemy = self.session()
        other = deepcopy(enemy)
        other["id"] = "second:1"
        self.assertEqual(self.strike(session, enemy), 25)
        self.assertEqual(self.strike(session, other), 5)
        self.assertEqual(self.strike(session, enemy), 0)
        session["combat"]["round"] += 1
        self.assertEqual(self.strike(session, other), 25)
        enemy["encounter_class"] = "boss"
        actor["hp"] = 100
        self.assertEqual(self.strike(session, enemy, .45), 45)

    def test_charge_warns_without_damage_then_releases_without_reselecting(self):
        session, actor, enemy = self.session()
        enemy["skills"] = [{"id": "charge", "name": "炎の息", "kind": "attack", "damage_max_hp_ratio": .20,
                            "telegraph": {"charge_rounds": 1, "warning": "【仮】{enemy}"}, "max_uses_per_battle": 1}]
        combat._enemy_phase(session, random.Random(1))
        self.assertEqual(actor["hp"], 100)
        self.assertEqual(enemy["skill_uses"]["charge"], 1)
        self.assertIn("charging", combat.public_combat(session)["enemies"][0])
        self.assertEqual(budget.phase_moments(session)["expected_damage"], 0)
        session["combat"]["round"] += 1
        self.assertGreater(budget.phase_moments(session)["expected_damage"], 0)
        combat._enemy_phase(session, random.Random(1))
        self.assertEqual(actor["hp"], 80)
        self.assertNotIn("charging", enemy)
        self.assertEqual(enemy["skill_uses"]["charge"], 1)

    def test_stun_cancels_pending_charge(self):
        session, actor, enemy = self.session()
        enemy["charging"] = {"release_round": 2, "ability": {"damage_max_hp_ratio": .25, "kind": "attack"}}
        status_effects.apply(session, enemy, "stun", actor, random.Random(1))
        session["combat"]["round"] = 2
        combat._enemy_phase(session, random.Random(1))
        self.assertEqual(actor["hp"], 100)
        self.assertNotIn("charging", enemy)

    def test_weight_includes_basic_only_when_explicit(self):
        session, actor, enemy = self.session()
        skill = {"id": "percent", "kind": "attack", "damage_max_hp_ratio": .2, "ai_weight": 1}
        enemy["skills"] = [skill]
        class Capture:
            def choices(self, entries, *, weights, k):
                self.weights = weights
                return entries[:1]
        rng = Capture()
        combat._choose_enemy_ability(enemy, session, rng)
        self.assertEqual(rng.weights, [1])
        enemy["combat"]["basic_attack_weight"] = 2
        combat._choose_enemy_ability(enemy, session, rng)
        self.assertEqual(rng.weights, [1, 2])

    def test_strategy_responds_with_enabled_action_for_every_class(self):
        for cid in ("hero", "cleric", "mage", "thief"):
            session, actor, enemy = self.session(cid)
            enemy["encounter_class"] = "boss"
            enemy["charging"] = {"release_round": 1, "ability": {"kind": "attack", "damage_max_hp_ratio": .45}}
            action, target = policy_v3.choose(session, "heuristic_v3")
            self.assertTrue(action["enabled"])
            self.assertIn(action["type"], {"skill", "defend"})
            combat.perform_combat_action(session, action["type"], action["id"], target, rng=random.Random(1))

    def test_moves_normal_only_and_three_054_hooks_have_no_stun(self):
        baby = difficulty.apply_difficulty(self.base, "baby")
        baby_enemies = {e["id"]: e for e in baby["enemies"]}
        normal_enemies = {e["id"]: e for e in self.pack["enemies"]}
        for move in normal_tuning_052.MOVES_052B:
            enemy = normal_enemies[move["enemy"]]
            skill = next(s for s in enemy["skills"] if s["id"] == move["id"])
            self.assertIn(skill["kind"], {"attack", "damage"})
            self.assertGreater(skill["damage_max_hp_ratio"], 0)
            old = next((s for s in baby_enemies[enemy["id"]]["skills"] if s["id"] == skill["id"]), {})
            self.assertNotIn("damage_max_hp_ratio", old)
            self.assertNotIn("telegraph", old)
            if enemy["id"] in {"hobgoblin", "rock_giant", "ice_sentinel"}:
                self.assertNotEqual(skill.get("on_hit_status", {}).get("id"), "stun")
        self.assertEqual(normal_tuning_052.migrate(self.base), self.base)

    def test_invalid_new_mechanic_values_rejected(self):
        for path, value in (("skills.@id=ice_hammer.damage_max_hp_ratio", -1),
                            ("skills.@id=ice_hammer.telegraph", {"charge_rounds": 0, "warning": "【仮】"}),
                            ("combat.basic_attack_weight", 1.5)):
            pack = deepcopy(self.base)
            pack["difficulty_overlays"]["normal"] = [{"entity": "enemies", "id": "ice_sentinel", "path": path, "set": value}]
            with self.assertRaises(ValueError):
                difficulty.validate_difficulty(pack)

    def test_empty_rule_set_skips_new_records_without_rng_changes(self):
        session, actor, enemy = self.session()
        session["scenario_pack"]["combat_rules"].pop("elite_percentage_round_cap")
        enemy["skills"] = [{"id": "new", "kind": "attack", "requires_combat_rule": "elite_percentage_round_cap",
                            "damage_max_hp_ratio": .2}]
        rng = random.Random(12)
        before = rng.getstate()
        ability = combat._choose_enemy_ability(enemy, session, rng)
        self.assertNotEqual(ability.get("id"), "new")
        self.assertEqual(rng.getstate(), before)
        self.assertNotIn("skill_uses", enemy)

    def test_cap_expectation_matches_enumerated_two_enemy_outcomes(self):
        session, actor, enemy = self.session()
        actor["combat"]["defense"] = 0
        enemy["skills"] = [{"id": "percent", "kind": "attack", "damage_max_hp_ratio": .25, "ai_weight": 1}]
        enemy["combat"].update(basic_attack_weight=2, basic_attack={"damage": "1", "accuracy": 100, "kind": "attack"})
        other = deepcopy(enemy)
        other["id"] = "second:1"
        session["combat"]["enemies"].append(other)
        with patch.object(combat, "attack_chance", return_value=100):
            result = budget.phase_moments(session)
        expected = 30/9 + 26*4/9 + 2*4/9
        self.assertAlmostEqual(result["expected_damage"], expected)

    def test_normal_boss_flags_phases_and_scripted_classification(self):
        for category in ("boss", "guest", "scripted_loss"):
            session = checkpoints.fresh_session(deepcopy(self.pack), "hero", "normal", effective=True)
            session["npc_encounter_override"] = {"enemy_ids": ["ignis"], "encounter_class": category}
            session["combat_start_requested"] = True
            combat.ensure_combat_started(session)
            self.assertEqual(session["combat"]["encounter"]["encounter_class"], category)
            self.assertEqual(session["combat"]["enemies"][0]["encounter_class"], category)
        session, _, enemy = self.session()
        session["combat"]["encounter"]["encounter_class"] = "boss"
        enemy.update(encounter_class="boss", next_phase="draco_dragon", hp=0)
        combat._check_victory_or_defeat(session)
        self.assertEqual(session["combat"]["enemies"][0]["encounter_class"], "boss")

    def test_reclassification_and_boss_tuning_do_not_reach_baby(self):
        baby = difficulty.apply_difficulty(self.base, "baby")
        for pack, category in ((baby, "elite"), (self.pack, "trash")):
            encounter = next(l for l in pack["locations"] if l["id"] == "goblin_fort_first_second")["combat"]
            self.assertEqual(encounter["encounter_class"], category)
        tree = next(e for e in self.pack["enemies"] if e["id"] == "prism_tree")
        self.assertTrue(90 <= tree["hp"] <= 110)
        self.assertTrue(all(ratio == 0 or ratio > 1 for phase in tree["resistance_cycle"]["phases"] for ratio in phase["resistances"].values()))
        dragon = next(e for e in self.pack["enemies"] if e["id"] == "draco_dragon")
        self.assertTrue(140 <= dragon["hp"] <= 220)
        self.assertEqual(dragon["resistances"]["physical"], .25)


if __name__ == "__main__":
    unittest.main()
