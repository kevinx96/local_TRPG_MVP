from __future__ import annotations

import unittest
from copy import deepcopy
from unittest.mock import patch

from host import combat, state
from host.difficulty import apply_difficulty
from scripts.balance import archetypes, checkpoints, route_v2


class CaveRetreat052Tests(unittest.TestCase):
    def test_lava_entry_defeat_returns_without_claiming_chest(self):
        pack = apply_difficulty(state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO), "normal")
        enemy = next(e for e in pack["enemies"] if e["id"] == "fire_wisp")
        enemy.update(hp=10000, max_hp=10000)
        enemy["combat"]["basic_attack"].update(damage="100", true_damage=True)
        run = route_v2.MeasurementRun(pack, "hero", 52, archetypes.ARCHETYPES["P3"],
                                     difficulty="normal", effective=True, measure=False)
        run.policy = "attack_only"
        run.session["world_state"] = {"scene_id": "dark_forest", "location_id": "elf_spring"}
        run.session["flags"].update(cave_seal_broken=True, cleared_cave_heat_corridor=True)
        run.session["character"]["hp"] = 1
        before = deepcopy(run.session["character"])
        with patch.object(combat, "random", run.rng), patch.object(state, "random", run.rng):
            run.cave()
        self.assertEqual(run.location, "elf_spring")
        self.assertEqual(run.battles[-1]["status"], "defeat")
        self.assertTrue(run.battles[-1]["continue"])
        self.assertEqual(run.battles[-1]["encounter"], "cave_lava_room")
        self.assertFalse(any(s["action"] == "open_lava_chest" for s in run.steps))
        self.assertEqual(run.session["character"].get("exp"), before.get("exp"))
        self.assertEqual(run.session["character"]["hp"], 1)
        self.assertFalse(run.session.get("game_over"))


if __name__ == "__main__":
    unittest.main()
