from __future__ import annotations

import json
from typing import Any

from .upgrade_forest import ROOT


def tune(pack: dict[str, Any]) -> None:
    enemies = {e["id"]: e for e in pack["enemies"]}
    for identifier, hp, damage, accuracy, resistances in (
        ("ash_wraith", 22, "1d24", 40, {"holy": 1.4}),
        ("lava_drake", 25, "1d20", 75, {"physical": .5}),
        ("xanxus_phantom", 147, "1d24", 80, {"physical": .65, "ice": 1.95, "holy": 1.5}),
    ):
        enemy = enemies[identifier]
        enemy.update(hp=hp, max_hp=hp)
        enemy["resistances"].update(resistances)
        enemy["combat"]["basic_attack"].update(damage=damage, accuracy=accuracy)
        for skill in enemy["skills"]:
            if skill["kind"] == "attack":
                skill.update(damage=damage, accuracy=accuracy)
        if identifier == "xanxus_phantom":
            enemy["combat"]["defense"] = 1
            enemy["skills"][0]["round_damage"] = "3"
            enemy["skills"][1].update(damage="2d24", accuracy=85)


if __name__ == "__main__":
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        tune(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
