from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Iterator, NamedTuple

from host.combat import _ability_kind

SCENARIO_DIR = Path(__file__).resolve().parents[1] / "host" / "prompt" / "processed"
SCENARIO_PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")

VALID_KINDS = {
    "attack",
    "damage",
    "heal",
    "restore",
    "cleanse",
    "defend",
    "status",
    "field",
    "stance",
}

# Purify actions go through the purify_chance branch and have no explicit kind.
# _ability_kind is expected to fall back to "attack" for them.
WHITELIST: dict[tuple[str, str], str] = {
    ("locations.dragon_valley_loc.combat.special_actions", "purify_ignis_holy_water"): "attack",
    ("locations.dragon_valley_loc.combat.special_actions", "purify_ignis_prayer"): "attack",
}

# Minimum entry counts per category, checked for each pack.
MIN_CATEGORY_COUNTS: dict[str, int] = {
    "enemies.skills": 30,
    "characters.skills": 8,
    "items.learn_skill": 2,
    "locations.special_actions": 2,
}

# Exact entry counts per category, checked for each pack.
EXACT_CATEGORY_COUNTS: dict[str, int] = {
    "class_progression.actives": 12,
}


class SkillEntry(NamedTuple):
    category: str  # structure the entry came from, e.g. "enemies.skills"
    path: str  # concrete location, e.g. "enemies.<enemy_id>.skills"
    skill_id: str
    entry: dict[str, Any]


def iter_skill_entries(data: dict[str, Any]) -> Iterator[SkillEntry]:
    """Yield every pack structure that feeds _ability_kind."""
    # 1. enemies[*].skills
    for enemy in data.get("enemies") or []:
        if not isinstance(enemy, dict):
            continue
        enemy_id = str(enemy.get("id") or "<unknown_enemy>")
        for skill in enemy.get("skills") or []:
            if isinstance(skill, dict):
                skill_id = str(skill.get("id") or skill.get("name") or "<unnamed>")
                yield SkillEntry("enemies.skills", f"enemies.{enemy_id}.skills", skill_id, skill)

    # 2. characters[*].skills and 3. characters[*].level_skills
    for char in data.get("characters") or []:
        if not isinstance(char, dict):
            continue
        char_id = str(char.get("id") or "<unknown_char>")
        for field in ("skills", "level_skills"):
            for skill in char.get(field) or []:
                if isinstance(skill, dict):
                    skill_id = str(skill.get("id") or skill.get("name") or "<unnamed>")
                    yield SkillEntry(
                        f"characters.{field}", f"characters.{char_id}.{field}", skill_id, skill
                    )

    # 4. class_progression: a list of {"id": <class_id>, "actives": [{"skill": {...}}]}
    for prog in data.get("class_progression") or []:
        if not isinstance(prog, dict):
            continue
        class_id = str(prog.get("id") or "<unknown_class>")
        for active in prog.get("actives") or []:
            if not isinstance(active, dict):
                continue
            skill = active.get("skill")
            if isinstance(skill, dict):
                skill_id = str(
                    skill.get("id") or active.get("id") or skill.get("name") or "<unnamed>"
                )
                yield SkillEntry(
                    "class_progression.actives",
                    f"class_progression.{class_id}.actives",
                    skill_id,
                    skill,
                )

    # 5. items[*].learn_skill and 6. items[*].combat.grants_skills
    for item in data.get("items") or []:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id") or "<unknown_item>")
        learn_skill = item.get("learn_skill")
        if isinstance(learn_skill, dict):
            skill_id = str(learn_skill.get("id") or learn_skill.get("name") or "<unnamed>")
            yield SkillEntry(
                "items.learn_skill", f"items.{item_id}.learn_skill", skill_id, learn_skill
            )

        combat_cfg = item.get("combat")
        if isinstance(combat_cfg, dict):
            for skill in combat_cfg.get("grants_skills") or []:
                if isinstance(skill, dict):
                    skill_id = str(skill.get("id") or skill.get("name") or "<unnamed>")
                    yield SkillEntry(
                        "items.grants_skills",
                        f"items.{item_id}.combat.grants_skills",
                        skill_id,
                        skill,
                    )

    # 7. locations[*].combat.special_actions and 8. locations[*].combat.encounter_modifiers[*].extra_enemy_skills
    for loc in data.get("locations") or []:
        if not isinstance(loc, dict):
            continue
        loc_id = str(loc.get("id") or "<unknown_loc>")
        combat_cfg = loc.get("combat")
        if not isinstance(combat_cfg, dict):
            continue

        for action in combat_cfg.get("special_actions") or []:
            if isinstance(action, dict):
                action_id = str(action.get("id") or action.get("name") or "<unnamed>")
                yield SkillEntry(
                    "locations.special_actions",
                    f"locations.{loc_id}.combat.special_actions",
                    action_id,
                    action,
                )

        for mod in combat_cfg.get("encounter_modifiers") or []:
            if not isinstance(mod, dict):
                continue
            mod_id = str(mod.get("id") or "<unknown_mod>")
            for skill in mod.get("extra_enemy_skills") or []:
                if isinstance(skill, dict):
                    skill_id = str(skill.get("id") or skill.get("name") or "<unnamed>")
                    yield SkillEntry(
                        "locations.extra_enemy_skills",
                        f"locations.{loc_id}.combat.encounter_modifiers.{mod_id}.extra_enemy_skills",
                        skill_id,
                        skill,
                    )


def count_by_category(entries: list[SkillEntry]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in entries:
        counts[item.category] = counts.get(item.category, 0) + 1
    return counts


def load_pack(pack_name: str) -> dict[str, Any]:
    pack_path = SCENARIO_DIR / pack_name
    if not pack_path.is_file():
        raise FileNotFoundError(f"Scenario pack not found: {pack_path}")
    return json.loads(pack_path.read_text(encoding="utf-8"))


class AllSkillKindsTest(unittest.TestCase):
    def test_all_scenario_pack_skills_have_explicit_valid_kind(self) -> None:
        for pack_name in SCENARIO_PACKS:
            with self.subTest(pack=pack_name):
                data = load_pack(pack_name)
                entries = list(iter_skill_entries(data))
                self.assertGreater(len(entries), 0, f"{pack_name} yielded no skill entries")

                violations: list[str] = []
                seen_whitelist: set[tuple[str, str]] = set()
                for item in entries:
                    whitelist_key = (item.path, item.skill_id)
                    if whitelist_key in WHITELIST:
                        seen_whitelist.add(whitelist_key)
                        expected_kind = WHITELIST[whitelist_key]
                        actual_kind = _ability_kind(item.entry)
                        if actual_kind != expected_kind:
                            violations.append(
                                f"[{pack_name}] {item.category} {item.path} -> '{item.skill_id}' "
                                f"(whitelisted): expected _ability_kind == '{expected_kind}', "
                                f"got '{actual_kind}'"
                            )
                        continue

                    raw_kind = item.entry.get("kind") or item.entry.get("type")
                    explicit = str(raw_kind or "").strip().lower()
                    if not explicit:
                        violations.append(
                            f"[{pack_name}] {item.category} {item.path} -> '{item.skill_id}': "
                            f"missing explicit 'kind'/'type' "
                            f"(fallback _ability_kind='{_ability_kind(item.entry)}')"
                        )
                    elif explicit not in VALID_KINDS:
                        violations.append(
                            f"[{pack_name}] {item.category} {item.path} -> '{item.skill_id}': "
                            f"invalid kind '{raw_kind}' (not in {sorted(VALID_KINDS)})"
                        )

                # A whitelist key that matches no entry would silently disable its check.
                for key in WHITELIST:
                    if key not in seen_whitelist:
                        violations.append(
                            f"[{pack_name}] whitelist key {key} matched no entry"
                        )

                if violations:
                    self.fail(
                        f"Found {len(violations)} skill kind violation(s) in {pack_name}:\n  - "
                        + "\n  - ".join(violations)
                    )

    def test_each_pack_meets_category_counts(self) -> None:
        for pack_name in SCENARIO_PACKS:
            with self.subTest(pack=pack_name):
                counts = count_by_category(list(iter_skill_entries(load_pack(pack_name))))

                violations: list[str] = []
                for category, floor in MIN_CATEGORY_COUNTS.items():
                    actual = counts.get(category, 0)
                    if actual < floor:
                        violations.append(f"{category}: expected >= {floor}, got {actual}")
                for category, expected in EXACT_CATEGORY_COUNTS.items():
                    actual = counts.get(category, 0)
                    if actual != expected:
                        violations.append(f"{category}: expected == {expected}, got {actual}")

                if violations:
                    self.fail(
                        f"Found {len(violations)} category count violation(s) in {pack_name}:\n  - "
                        + "\n  - ".join(violations)
                    )


if __name__ == "__main__":
    unittest.main()
