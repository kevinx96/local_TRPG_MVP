from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def tune(pack: dict[str, Any]) -> None:
    enemies = {e["id"]: e for e in pack["enemies"]}
    for identifier, hp, damage, accuracy, fire_resistance in (
        ("heat_lizard", 18, "2d5+1", 86, .25),
        ("fire_wisp", 12, "1d7", 100, .8),
        ("ruby_golem", 33, "1d12", 75, .35),
        ("prism_tree", 130, "1d14", 78, None),
    ):
        enemy = enemies[identifier]
        enemy.update(hp=hp, max_hp=hp)
        enemy["combat"]["basic_attack"].update(damage=damage, accuracy=accuracy)
        for skill in enemy["skills"]:
            if skill.get("kind") != "heal":
                skill.update(damage=damage, accuracy=accuracy)
        if fire_resistance is not None:
            enemy["resistances"]["fire"] = fire_resistance
        if identifier == "fire_wisp":
            enemy["combat"]["evade"] = 30
        if identifier == "prism_tree":
            enemy["resistances"]["physical"] = .6
            enemy["resistances"]["holy"] = .75
            for phase in enemy["resistance_cycle"]["phases"]:
                phase["resistances"]["physical"] = .6
                phase["resistances"]["holy"] = .75
                if phase["element"] == "earth":
                    phase["resistances"]["ice"] = .5

    formulas = {"hero": "3d6+str/3", "cleric": "1d20+wis/3",
                "mage": "1d20+int/3", "thief": "4d4+dex/4"}

    def update_weapons(value: Any) -> None:
        if isinstance(value, list):
            for child in value:
                update_weapons(child)
        elif isinstance(value, dict):
            identifier = str(value.get("id", ""))
            if identifier.startswith("prism_weapon_") and "combat" in value:
                value["combat"]["damage"] = formulas[identifier.removeprefix("prism_weapon_")]
            for child in value.values():
                update_weapons(child)

    # The catalogue and both forge reward branches carry complete item records.
    update_weapons(pack)


def main() -> None:
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        tune(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
