from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
# A parent with children only expands a menu, so any effect on it would silently never run.
EFFECT_KEYS = ("effects", "success_effects", "failure_effects", "roll", "open_shop", "start_combat")


def _walk(actions, location_id):
    for action in actions:
        yield location_id, action
        yield from _walk(action.get("children") or [], location_id)


class ScenarioInvariantTests(unittest.TestCase):
    def test_menu_parents_carry_no_effects(self):
        for filename in PACKS:
            pack = json.loads((ROOT / "host/prompt/processed" / filename).read_text(encoding="utf-8"))
            for location in pack["locations"]:
                for location_id, action in _walk(location.get("actions") or [], location["id"]):
                    if action.get("children"):
                        with self.subTest(pack=filename, location=location_id, action=action["id"]):
                            self.assertEqual([key for key in EFFECT_KEYS if action.get(key)], [])


if __name__ == "__main__":
    unittest.main()
