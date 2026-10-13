from __future__ import annotations

import json
import random
import unittest
from copy import deepcopy

from host import combat, state
from scripts.balance import ch34c, checkpoints, sim


class Chapter34BalanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cls.cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))

    def session(self):
        session = sim.prepare_session(self.pack, "valley_entrance", "thief", self.cp)
        combat.ensure_combat_started(session)
        return session

    def test_elite_holy_water_requires_weakness_and_spare_bottle(self):
        for policy in ("greedy", "heuristic"):
            for kind, resistance, quantity, legacy, expected in (
                ("elite", 1.4, 2, False, True),
                ("elite", 1.4, 1, False, False),
                ("elite", 1, 2, False, False),
                ("elite", .5, 2, False, False),
                ("trash", 1.4, 2, False, False),
                ("elite", 1.4, 2, True, False),
            ):
                with self.subTest(policy=policy, kind=kind, resistance=resistance, quantity=quantity, legacy=legacy):
                    session = self.session()
                    session["combat"]["encounter"]["encounter_class"] = kind
                    for enemy in session["combat"]["enemies"]:
                        enemy["resistances"]["holy"] = resistance
                    item = next(i for i in session["character"]["inventory"] if i.get("id") == "holy_water")
                    item["quantity"] = quantity
                    action, _ = sim.choose_action(session, policy, elite_holy_water=not legacy)
                    self.assertEqual(action["type"] == "item" and action["id"] == "holy_water", expected)

    def test_actual_consumption_keeps_last_bottle(self):
        session = self.session()
        action, target = sim.choose_action(session, "heuristic", reserve_purification=True)
        self.assertEqual(action["id"], "holy_water")
        combat.perform_combat_action(session, action["type"], action["id"], target, rng=random.Random(17))
        item = next(i for i in session["character"]["inventory"] if i.get("id") == "holy_water")
        self.assertEqual(item["quantity"], 1)
        if combat.combat_is_active(session):
            action, _ = sim.choose_action(session, "heuristic")
            self.assertNotEqual(action["id"], "holy_water")

    def test_attack_only_remains_attack(self):
        action, _ = sim.choose_action(self.session(), "attack_only")
        self.assertEqual(action["type"], "attack")

    def test_weakness_on_dead_enemy_does_not_allow_water(self):
        session = self.session()
        enemy = session["combat"]["enemies"][0]
        dead = deepcopy(enemy)
        dead.update(id="dead", hp=0)
        session["combat"]["enemies"].append(dead)
        for living in session["combat"]["enemies"][:-1]:
            living["resistances"]["holy"] = 1
        action, _ = sim.choose_action(session, "heuristic")
        self.assertNotEqual(action["id"], "holy_water")

    def test_failure_share_and_class_spread_boundaries(self):
        def row(character, rate, d1, other):
            return dict(character=character, completion_rate=rate, preparation="paid_rest",
                        failure_counts=dict(valley_entrance=d1, dragon_valley_loc=other))
        result = dict(encounters=[], routes=[row("hero", .85, 5, 10)])
        self.assertEqual(ch34c.violations(result), [])
        result["routes"][0]["failure_counts"]["valley_entrance"] = 6
        self.assertEqual(ch34c.violations(result)[0]["metric"], "d1_failure_share")
        result = dict(encounters=[], routes=[row("hero", .85, 5, 10), row("thief", .60, 0, 40)])
        self.assertEqual(ch34c.violations(result), [])
        result["routes"][0]["failure_counts"]["valley_entrance"] = 26
        result["routes"][1]["completion_rate"] = .59
        self.assertEqual([v["metric"] for v in ch34c.violations(result)], ["d1_failure_share", "class_spread"])
        result["routes"] = [row("hero", 1, 0, 0)]
        self.assertEqual(len(ch34c.violations(result)), 1)


if __name__ == "__main__":
    unittest.main()
