from __future__ import annotations

import random
import unittest
from copy import deepcopy

from host import combat, state
from scripts.balance.checkpoints import fresh_session


def battle(location="goblin_fort"):
    session = fresh_session(state.load_scenario_pack(state.DEFAULT_SCENARIO), "hero")
    session["world_state"] = {"location_id": location}
    session["combat_start_requested"] = True
    combat.ensure_combat_started(session)
    return session


class CombatEventTests(unittest.TestCase):
    def test_attack_target_snapshot_and_overflow_cursor(self):
        session = battle()
        for _ in range(90):
            combat._log(session, "system", "warning", "戦闘開始")
        previous = session["combat"]["log"][-1]["sequence"]
        result = combat.perform_combat_action(session, "attack", rng=random.Random(1))
        self.assertTrue(result["events"])
        self.assertTrue(all(e["sequence"] > previous for e in result["events"]))
        hit = next(e for e in result["events"] if e["kind"] == "damage" and e["actor"] == "player")
        self.assertEqual(hit["visual"]["target_id"], session["combat"]["enemies"][0]["id"])
        self.assertEqual(hit["visual"]["amount"], hit["data"]["damage"])
        self.assertFalse(hit["visual"]["critical"])
        self.assertEqual(hit["state"][hit["visual"]["target_id"]]["hp"],
                         max(0, session["combat"]["enemies"][0]["max_hp"] - hit["data"]["damage"]))
        public = combat.public_combat(session)
        self.assertEqual(public["events"], result["events"])
        self.assertEqual(public["presentation_state"]["player"]["sp"], session["character"]["sp"])

    def test_miss_damage_heal_heavy_and_negative_hp_targets(self):
        session = battle()
        player = session["character"]
        enemy = session["combat"]["enemies"][0]
        combat._resolve_attack(session, player, enemy, {"accuracy": 5, "damage": "5"}, "player", random.Random(5))
        miss = session["combat"]["log"][-1]["visual"]
        self.assertEqual((miss["kind"], miss["hit"], miss["target_id"]), ("miss", False, enemy["id"]))
        combat._resolve_attack(session, enemy, player, {"accuracy": 100, "damage": "1000"}, enemy["id"], random.Random(1))
        hit = session["combat"]["log"][-1]["visual"]
        self.assertTrue(hit["heavy"])
        self.assertTrue(hit["knocked_down"])
        self.assertEqual(hit["target_id"], "player")
        item = next(item for item in player["inventory"] if combat.item_combat_spec(item).get("kind") == "heal")
        combat._player_item(session, item["id"], "", random.Random(1))
        heal = session["combat"]["log"][-1]
        self.assertEqual(heal["visual"]["kind"], "heal")
        self.assertEqual(heal["state"]["player"]["hp"], player["hp"])
        enemy.update(hp=-10, max_hp=-10, life_rule="negative_undead")
        # Use the engine's own defeat predicate, including special undead mechanics.
        self.assertEqual(combat._presentation_state(session)[enemy["id"]]["defeated"], combat._enemy_is_defeated(enemy))

    def test_phase_transition_carries_runtime_ids_and_new_portrait(self):
        session = battle("draco_battle")
        old = deepcopy(session["combat"]["enemies"][0])
        session["combat"]["enemies"][0]["hp"] = 0
        combat._check_victory_or_defeat(session)
        phase = next(e for e in session["combat"]["log"] if e["kind"] == "phase_transition")
        replacement = session["combat"]["enemies"][0]
        self.assertEqual(phase["data"]["from_id"], old["id"])
        self.assertEqual(phase["data"]["replacement"]["image"], replacement["image"])
        self.assertEqual(phase["visual"]["target_id"], replacement["id"])
        self.assertEqual(phase["state"][replacement["id"]]["hp"], replacement["hp"])


if __name__ == "__main__":
    unittest.main()
