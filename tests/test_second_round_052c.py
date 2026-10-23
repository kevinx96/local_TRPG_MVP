from __future__ import annotations

import unittest
import json
from copy import deepcopy
from pathlib import Path

from host import combat, difficulty, progression
from scripts.balance import metrics_v3, policy_v3
from test_progression_v2 import Rolls, select, session


class SecondRound052cTests(unittest.TestCase):
    def test_reviewed_m4_and_m9_boundaries(self):
        targets = json.loads((Path.cwd()/"eval/balance/targets.json").read_text(encoding="utf-8"))
        data = dict(difficulty="normal", measurement_scope="052", targets=targets, records=[],
                    boss_policy_probes=[dict(character="hero", encounter="draco_battle", policy="heuristic_v3", rounds=[30]),
                                        dict(character="thief", encounter="draco_battle", policy="heuristic_v3", rounds=[31]),
                                        dict(character="mage", encounter="draco_battle", policy="attack_only", rounds=[60])],
                    damage_budget_v2=[dict(character=c, encounter=e, encounter_class="boss", ratio=ratio,
                                          expected_damage=ratio*100, variance=0, cv=0)
                                      for e,ratio in (("near",.27),("outside",.269))
                                      for c in ("hero","cleric","mage","thief")])
        metrics = {m["id"]:m for m in metrics_v3.evaluate(data)}
        rounds = {r["character"]:r for r in metrics["M4"]["value"]}
        self.assertEqual(rounds["hero"]["status"], "pass")
        self.assertEqual(rounds["thief"]["status"], "accepted_boundary")
        self.assertEqual(rounds["mage"]["status"], "report")
        bands = {r["encounter"]:r for r in metrics["M9"]["value"]}
        self.assertEqual(bands["near"]["status"], "accepted_boundary")
        self.assertEqual(bands["outside"]["status"], "fail")

    def test_armor_exhaustion_mp_refill_and_new_battle(self):
        value = session("mage", start=False)
        select(value, "mana_armor")
        actor = value["character"]
        actor.update(hp=100, max_hp=100, mp=100, max_mp=100, equipment=[], statuses=[])
        combat.ensure_combat_started(value)
        foe = value["combat"]["enemies"][0]
        ability = {"damage": "100", "ignores_defense": True, "accuracy": 100}
        for expected in (20, 20, 10, 0):
            actor.update(hp=100, mp=100)
            combat._resolve_attack(value, foe, actor, ability, "enemy", Rolls())
            self.assertEqual(100-actor["mp"], expected)
            self.assertEqual(actor["hp"], expected)
        self.assertEqual(value["combat"]["passive_state"]["mana_armor_absorbed"], 50)
        value["combat"] = None
        actor.update(hp=100, mp=100)
        combat.ensure_combat_started(value)
        self.assertNotIn("mana_armor_absorbed", value["combat"]["passive_state"])
        self.assertEqual(combat._mana_armor_diversion(value, 100, progression.effects(value)), 20)

    def test_estimator_uses_remaining_cap_without_mutating(self):
        value = session("mage")
        select(value, "mana_armor")
        actor = value["character"]
        actor.update(hp=100, max_hp=100, mp=100, equipment=[], statuses=[])
        value["combat"]["passive_state"]["mana_armor_absorbed"] = 49
        foe = value["combat"]["enemies"][0]
        ability = {"damage": "10", "ignores_defense": True, "accuracy": 100}
        before = deepcopy(value)
        expected, _ = policy_v3.strike_moments(value, foe, actor, ability, "enemy")
        self.assertEqual(value, before)
        chance = combat.attack_chance(value, foe, actor, ability, "enemy")/100
        self.assertAlmostEqual(expected, 9*chance)
        combat._resolve_attack(value, foe, actor, ability, "enemy", Rolls())
        self.assertEqual((actor["hp"], actor["mp"]), (91, 99))

    def test_cap_floor_mp_and_absent_field_compatibility(self):
        value = session("mage")
        value["character"].update(max_hp=25, mp=1)
        effects = {"mana_armor": .2, "mana_armor_cap_ratio": .5}
        self.assertEqual(combat._mana_armor_diversion(value, 100, effects), 1)
        value["character"]["mp"] = 100
        self.assertEqual(combat._mana_armor_diversion(value, 100, effects), 12)
        self.assertEqual(combat._mana_armor_diversion(value, 100, {"mana_armor": .25}), 25)
        self.assertEqual(combat._mana_armor_diversion(value, 100, {}), 0)
        self.assertIn("passives.*.tiers.*.effects.mana_armor_cap_ratio", difficulty.NUMERIC_FIELDS["class_progression"])


if __name__ == "__main__":
    unittest.main()
