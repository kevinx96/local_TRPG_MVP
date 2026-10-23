"""052a normal numeric tuning; base baby data remains untouched."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from host.difficulty import overlay_fingerprint, validate_difficulty

ROOT = Path(__file__).resolve().parents[2]
REVISION = "2026-10-23-tuning-052a"

# L1: bounded EXP search and approved integer / per-level growth.
PROGRESSION: dict[str, Any] = {'level_gains': {'hero': {'max_hp': 3,
                          'max_mp': 1,
                          'max_sp': 1,
                          'attributes': {'str': 2, 'end': 1},
                          'by_level': {'2': {'max_sp': 2},
                                       '4': {'max_sp': 2,
                                             'attributes': {'dex': 1}},
                                       '6': {'max_sp': 2,
                                             'attributes': {'dex': 1}},
                                       '8': {'attributes': {'dex': 1}}}},
                 'cleric': {'max_hp': 3,
                            'max_mp': 2,
                            'max_sp': 1,
                            'attributes': {'wis': 2, 'int': 1}},
                 'mage': {'max_hp': 2,
                          'max_mp': 3,
                          'max_sp': 1,
                          'attributes': {'int': 2, 'wis': 1},
                          'by_level': {'2': {'max_hp': 3},
                                       '4': {'max_hp': 3,
                                             'attributes': {'dex': 1}},
                                       '8': {'attributes': {'dex': 1}}}},
                 'thief': {'max_hp': 2,
                           'max_mp': 1,
                           'max_sp': 2,
                           'attributes': {'dex': 2, 'str': 1}}},
 'exp_table': {'2': 20,
               '3': 50,
               '4': 54,
               '5': 99,
               '6': 171,
               '7': 319,
               '8': 679},
 'exp_rewards': {'trash': 4,
                 'elite': 12,
                 'boss': 25,
                 'quest': 30,
                 'unclassified': 4,
                 'scripted_loss': 0,
                 'guest': 0}}


# L2: numeric-only candidate; unresolved gates are recorded in the 052 report.
ENEMIES: dict[str, dict[str, Any]] = {'ash_wraith': {'skills.@id=ash_embrace.damage': '1',
                'skills.@id=resentment.damage': '1d2+9'},
 'draco_human': {'skills.@id=ice_blade.damage': '1d2+24',
                 'skills.@id=sword_flash.damage': '1d2+8',
                 'hp': 15,
                 'max_hp': 15},
 'emerald_spider': {'combat.basic_attack.damage': '1'},
 'fire_elemental': {'combat.basic_attack.damage': '1d2+12'},
 'fire_slime': {'combat.basic_attack.damage': '1d2+2'},
 'forest_wolf': {'combat.basic_attack.damage': '2d4+2'},
 'frost_dire_wolf': {'combat.basic_attack.damage': '2d4+8',
                     'hp': 56,
                     'max_hp': 56},
 'goblin': {'combat.basic_attack.damage': '1d2+2'},
 'goblin_archer': {'combat.basic_attack.damage': '1'},
 'goblin_king': {'combat.basic_attack.damage': '1d2+4', 'hp': 51, 'max_hp': 51},
 'heat_lizard': {'combat.basic_attack.damage': '1d2+2'},
 'hobgoblin': {'combat.basic_attack.damage': '1d2+3'},
 'ice_elemental': {'combat.basic_attack.damage': '1d2+8'},
 'ignis': {'skills.@id=fire_breath.damage': '2d4+17', 'hp': 149, 'max_hp': 149},
 'prism_tree': {'skills.@id=crystal_rain.damage': '2d4+6',
                'hp': 78,
                'max_hp': 78,
                'combat.defense': 0},
 'ruby_golem': {'skills.@id=ruby_fist.damage': '1d2+5'},
 'sapphire_moth': {'combat.basic_attack.damage': '1'},
 'slime': {'combat.basic_attack.damage': '4'},
 'slime_king': {'combat.basic_attack.damage': '2d4+5', 'hp': 93, 'max_hp': 93},
 'draco_dragon': {'hp': 132, 'max_hp': 132}}


def migrate(pack: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(pack)
    entries = [{"entity": "progression", "id": "$", "path": key, "set": deepcopy(value)}
               for key, value in PROGRESSION.items()]
    entries.extend({"entity": "enemies", "id": identifier, "path": path, "set": value}
                   for identifier, paths in ENEMIES.items() for path, value in paths.items())
    destinations = {(e["entity"], e["id"], e["path"]): e for e in entries}
    updated = []
    for entry in result["difficulty_overlays"]["normal"]:
        key = entry["entity"], entry["id"], entry["path"]
        updated.append(destinations.pop(key, entry))
    result["difficulty_overlays"]["normal"] = updated + list(destinations.values())
    result["meta"]["content_revision"] = max(result["meta"]["content_revision"], REVISION)
    validate_difficulty(result)
    return result


def main() -> None:
    manifest = {}
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / name
        original = json.loads(path.read_text(encoding="utf-8"))
        updated = migrate(original)
        if updated != original:
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(updated, ensure_ascii=False, indent=2) + "\n")
        manifest[name] = {"content_revision": updated["meta"]["content_revision"],
                          "overlay_sha256": overlay_fingerprint(updated)}
    path = ROOT / "host/prompt/processed/difficulty/overlay_revision.json"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
