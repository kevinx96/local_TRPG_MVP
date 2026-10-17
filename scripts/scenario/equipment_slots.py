"""Apply spec 032 equipment slots and the forge price, idempotently."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PACK_DIR = Path(__file__).resolve().parents[2] / "host/prompt/processed"
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
SLOTS = {
    # Design decision (2026-10-15): the cleric's staff and the mage's tome are aids, not weapons, so a gifted
    # weapon such as イアン's ice blade still fills the empty weapon slot; the trade-off moves to the aid slot.
    "聖なる杖": "accessory", "魔導書": "accessory",
    "革の鎧": "armor", "ローブ": "armor", "魔法のローブ": "armor",
    "アダマンタイトの鎧": "armor", "墓守の外套": "armor", "守護団の鎖帷子": "armor",
    "氷の護符(活性化済)": "accessory", "紅玉の護符": "accessory",
    "呪われた水晶球": "accessory", "暗黒の水晶球": "accessory",
}


def apply(pack: dict[str, Any]) -> None:
    slots = dict(SLOTS)
    items = list(pack.get("items", []))
    items += [item for character in pack.get("characters", []) for item in character.get("inventory", [])]
    for item in items:
        if item.get("combat", {}).get("kind") == "weapon":
            slots[item["name"]] = "weapon"

    def annotate_item(item: dict[str, Any]) -> None:
        if item.get("name") in slots:
            item["slot"] = slots[item["name"]]

    def annotate(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "add_item" and isinstance(child, dict):
                    annotate_item(child)
                elif key == "inventory_add" and isinstance(child, list):
                    for item in child:
                        if isinstance(item, dict):
                            annotate_item(item)
                else:
                    annotate(child)
        elif isinstance(value, list):
            for child in value:
                annotate(child)

    # Item copies inside story rewards must carry the same explicit slot.
    for item in items:
        annotate_item(item)
    annotate(pack)
    forge_location = next(location for location in pack["locations"] if location["id"] == "forge")
    fusion = next(action for action in forge_location["actions"] if action["id"] == "accept_sword_fusion")
    if not any("equip_item" in effect for effect in fusion["effects"]):
        fusion["effects"].append({"equip_item": "氷鉄の大剣"})
    forge = next(shop for shop in pack["shops"] if shop["id"] == "forge_shop")
    next(offer for offer in forge["items"] if offer["item_id"] == "adamantite_armor")["price"] = 60
    pack["meta"]["content_revision"] = max(pack["meta"].get("content_revision", ""), "2026-10-15-v032")


def main() -> None:
    for name in PACKS:
        path = PACK_DIR / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[equipment_slots] updated {name}")


if __name__ == "__main__":
    main()
