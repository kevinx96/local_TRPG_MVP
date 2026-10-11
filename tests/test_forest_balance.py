from __future__ import annotations

import json
import unittest

from host import state
from scripts.balance import checkpoints, forest_v3, sim


class ForestBalanceTests(unittest.TestCase):
    def test_prism_damage_tier_at_recommended_and_final_levels(self):
        pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cp = checkpoints.generate()
        items = {i["id"]: i for i in pack["items"]}
        for encounter in ("cave_prism_tree", "dragon_valley_loc"):
            for char in forest_v3.CHARACTERS:
                actor = cp["encounters"][encounter]["characters"][char]
                mean = lambda item: sim.formula_mean(items[item]["combat"]["damage"], actor)
                self.assertLess(mean("iron_sword"), mean(f"prism_weapon_{char}"))
                self.assertLess(mean(f"prism_weapon_{char}"), mean("ice_katana"))

    def test_early_level_strict_limit_weapon_uplift_and_route_limit(self):
        targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
        result = {"encounters": [{"level": 1, "encounter": "cave_prism_tree", "character": "hero", "win_rate": .35}],
                  "weapons": [{"character": "mage", "uplift": .09}],
                  "routes": [{"character": "hero", "sidequests": True, "completion_rate": .802}]}
        self.assertEqual({v["metric"] for v in forest_v3.check_results(result, targets)},
                         {"early_prism_tree", "prism_weapon_ignis_uplift", "main_completion_rate"})
        result["encounters"][0]["win_rate"] = .348
        result["weapons"][0]["uplift"] = .1
        result["routes"][0]["completion_rate"] = .8
        self.assertEqual(forest_v3.check_results(result, targets), [])
