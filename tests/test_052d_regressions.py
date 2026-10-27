from __future__ import annotations

import random
import unittest
from copy import deepcopy

from host import combat, difficulty, state
from scripts.balance import checkpoints
from scripts.scenario import levels_skills_v2, normal_tuning_052


class SkillCooldownAndManaCycle052dTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)

    def _guard_action(self, mode):
        pack = difficulty.apply_difficulty(self.base, mode)
        value = checkpoints.fresh_session(deepcopy(pack), "hero", mode, effective=True)
        value["world_state"] = {"scene_id": "forest_wolves", "location_id": "forest_wolves"}
        value["combat_start_requested"] = True
        hero = next(character for character in pack["characters"] if character["id"] == "hero")
        value["character"].update(skills=deepcopy(hero["skills"]), hp=100, max_hp=100,
                                   statuses=[], equipment=[], inventory=[])
        combat.ensure_combat_started(value)
        return value

    def test_mana_cycle_three_tiers_increase_in_order(self):
        tuned = normal_tuning_052.migrate(deepcopy(self.base))
        mage = next(definition for definition in tuned["class_progression"] if definition["id"] == "mage")
        cycle = next(passive for passive in mage["passives"] if passive["id"] == "mana_cycle")
        actual = [(tier["effects"]["mana_cycle"]["amount"], tier["effects"]["mana_cycle"]["cap_ratio"])
                  for tier in cycle["tiers"]]
        self.assertEqual(actual, [(2, .3), (3, .4), (4, .5)])
        self.assertEqual(normal_tuning_052.migrate(tuned), tuned)

    def test_shared_base_skill_descriptions_are_migrated(self):
        migrated = levels_skills_v2.migrate(deepcopy(self.base))
        hero = next(character for character in migrated["characters"] if character["id"] == "hero")
        thief = next(character for character in migrated["characters"] if character["id"] == "thief")
        guard = next(skill for skill in hero["skills"] if skill["id"] == "divine_guard")
        shadow = next(skill for skill in thief["skills"] if skill["id"] == "hide_in_shadow")
        self.assertEqual(guard["description"], "被ダメージを半減し、致死ダメージもHP1で耐える。")
        self.assertEqual(shadow["description"],
                         "影に溶けて身を隠し、被ダメージを0.25倍にする。致死ダメージもHP1で耐える。")

    def test_combat_actions_expose_cooldown_and_keep_remaining_round_hint(self):
        normal = self._guard_action("normal")
        guard = next(action for action in combat.combat_actions(normal) if action["id"] == "divine_guard")
        self.assertEqual(guard["cooldown"], 1)
        combat.perform_combat_action(normal, "skill", "divine_guard", rng=random.Random(1))
        cooling_guard = next(action for action in combat.combat_actions(normal) if action["id"] == "divine_guard")
        self.assertEqual(cooling_guard["cooldown"], 1)
        self.assertEqual(cooling_guard["cooldown_remaining"], 1)
        self.assertEqual(cooling_guard["disabled_reason"], "あと1ラウンド")

        baby = self._guard_action("baby")
        baby_guard = next(action for action in combat.combat_actions(baby) if action["id"] == "divine_guard")
        self.assertNotIn("cooldown", baby_guard)


if __name__ == "__main__":
    unittest.main()
