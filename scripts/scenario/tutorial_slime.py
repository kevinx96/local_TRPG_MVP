"""The forest-entrance slime becomes the combat tutorial: attack, then heal after its one acid spit, then a skill."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
POTION = {
    "id": "travel_potion", "name": "旅の治療薬", "category": "consumable",
    "description": "旅人が持ち歩く小瓶の治療薬。気づけば背嚢に入っていた。",
    "effect": "HPを8回復 / 消耗品",
    "combat": {"kind": "heal", "healing": "8", "consumable": True},
    "icon": "/static/images/icon_travel_potion.png",
}
ACID = {
    "id": "slime_acid", "name": "溶解液", "kind": "attack",
    "description": "酸を吐きかける。防御を無視して8ダメージ。",
    "damage": "8", "accuracy": 100, "element": "physical", "true_damage": True,
    "use_on_round": 1, "max_uses_per_battle": 1,
}


def tutorial_slime(slime: dict[str, Any]) -> dict[str, Any]:
    enemy = deepcopy(slime)
    enemy.update(id="tutorial_slime", hp=30, max_hp=30,
                 description="森の入口に棲みついたスライム。妙に酸っぱい匂いがする。", skills=[deepcopy(ACID)])
    enemy["combat"]["basic_attack"] = {"name": "体当たり", "damage": "1", "accuracy": 80, "element": "physical"}
    return enemy


def apply(pack: dict[str, Any]) -> None:
    enemies = pack["enemies"]
    slime = next(enemy for enemy in enemies if enemy["id"] == "slime")
    enemies[:] = [enemy for enemy in enemies if enemy["id"] != "tutorial_slime"] + [tutorial_slime(slime)]
    pack["items"] = [item for item in pack["items"] if item["id"] != POTION["id"]] + [deepcopy(POTION)]

    location = next(loc for loc in pack["locations"] if loc["id"] == "dark_forest_loc")
    location["enemy_ids"] = ["tutorial_slime"]
    location["combat"]["enemy_ids"] = ["tutorial_slime"]
    location["combat"]["tutorial"] = True
    for obstacle in location.get("obstacles", []):
        if obstacle.get("enemy_id") == "slime":
            obstacle["enemy_id"] = "tutorial_slime"
    # The potion is slipped into the bag once when the first fight starts; keeping it unused is fine.
    location["combat"]["start_grant"] = {"flag": "tutorial_potion_given",
                                         "items": [{"id": POTION["id"], "name": POTION["name"], "quantity": 1}]}
    attack = next(action for action in location["actions"] if action["id"] == "attack_slime")
    attack["effects"] = [effect for effect in attack.get("effects", [])
                         if not (isinstance(effect, dict) and "branch" in effect
                                 and effect["branch"].get("requirements") == {"not_flag": "tutorial_potion_given"})]

def main() -> None:
    for name in PACKS:
        path = ROOT / "host" / "prompt" / "processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[tutorial_slime] updated {name}")


if __name__ == "__main__":
    main()
