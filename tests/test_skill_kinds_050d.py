from __future__ import annotations

import unittest
from pathlib import Path

from host.combat import _ability_kind
from host.scenario_context import load_scenario_pack

ROOT = Path(__file__).resolve().parents[1]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")

# Intended mechanics of every normal-only active skill (class_progression + scroll learn_skill).
EXPECTED_KINDS = {
    "holy_sword_art": "attack", "sweep": "attack", "dragon_slash": "attack",
    "atonement_mark": "attack", "great_heal_cleanse": "heal", "seraphim_gospel": "status",
    "mana_condense": "restore", "twin_storm": "attack", "elemental_collapse": "attack",
    "blinding_throw": "attack", "blade_dance": "attack", "shadow_haste": "status",
    "lightning": "attack", "arcane_lance": "attack",
}


def normal_only_skills(pack: dict) -> list[tuple[str, dict]]:
    skills = [(f"{c['id']}/{a['id']}", a["skill"]) for c in pack["class_progression"] for a in c["actives"]]
    skills += [(item["id"], item["learn_skill"]) for item in pack["items"] if isinstance(item.get("learn_skill"), dict)]
    return skills


class SkillKindTests(unittest.TestCase):
    def test_every_normal_only_skill_has_explicit_intended_kind(self):
        for name in PACKS:
            pack = load_scenario_pack(ROOT / "host/prompt/processed" / name)
            found = set()
            for where, skill in normal_only_skills(pack):
                with self.subTest(pack=name, skill=where):
                    self.assertIn(skill["id"], EXPECTED_KINDS)
                    self.assertTrue(str(skill.get("kind") or "").strip(), "explicit kind is required")
                    self.assertEqual(skill["kind"], EXPECTED_KINDS[skill["id"]])
                    self.assertEqual(_ability_kind(skill), EXPECTED_KINDS[skill["id"]])
                    found.add(skill["id"])
            self.assertEqual(found, set(EXPECTED_KINDS), name)

    def test_ignore_defense_descriptions_do_not_resolve_as_defend(self):
        for name in PACKS:
            pack = load_scenario_pack(ROOT / "host/prompt/processed" / name)
            by_id = {skill["id"]: skill for _, skill in normal_only_skills(pack)}
            for identifier in ("dragon_slash", "arcane_lance"):
                with self.subTest(pack=name, skill=identifier):
                    self.assertIn("防御", by_id[identifier]["description"])
                    self.assertEqual(_ability_kind(by_id[identifier]), "attack")


if __name__ == "__main__":
    unittest.main()
