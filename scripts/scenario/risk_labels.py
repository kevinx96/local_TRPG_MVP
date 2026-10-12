"""Derive each leaf action's visible risk label from its real mechanics, so players choose with accurate information."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
COMBAT_LABEL = "危険（戦闘）"


def _walk(actions):
    for action in actions:
        yield action
        yield from _walk(action.get("children") or [])


def _starts_combat(action: dict[str, Any]) -> bool:
    blocks = [action.get(key) or [] for key in ("effects", "success_effects")]
    return any(isinstance(effect, dict) and effect.get("start_combat") for block in blocks for effect in block)


def expected_risk(action: dict[str, Any], location: dict[str, Any], items: dict[str, str]) -> Optional[str]:
    """Return the label the mechanics imply, or None when the current label should be kept."""
    risk = str(action.get("risk") or "")
    if risk.startswith("未知"):
        return None  # deliberately hidden checks
    if "以上で" in risk:
        return None  # labels that also state an eligibility requirement are written by hand
    roll = action.get("roll")
    if isinstance(roll, dict) and roll.get("dc") is not None:
        if int(roll["dc"]) >= 999:
            return None  # scripted impossible checks keep their own wording
        return f"{roll.get('dice_type') or '1d20'}判定（DC{roll['dc']}）"
    free = action.get("free_action")
    if isinstance(free, dict):
        obstacle = next((o for o in location.get("obstacles") or [] if o.get("id") == free.get("target_id")), {})
        if free.get("operation") == "sneak" and obstacle.get("sneak_dc"):
            return f"1d20+dex判定（DC{obstacle['sneak_dc']}）・SP1消費"
        if free.get("operation") == "distract" and free.get("item_id"):
            return f"{items.get(free['item_id'], free['item_id'])}を1つ消費"
    if _starts_combat(action):
        return COMBAT_LABEL
    return None


def fix_pack(path: Path) -> list[tuple[str, str, str, str]]:
    pack = json.loads(path.read_text(encoding="utf-8"))
    items = {item["id"]: item["name"] for item in pack.get("items", []) if item.get("id")}
    changes = []
    for location in pack["locations"]:
        for action in _walk(location.get("actions") or []):
            if action.get("children"):
                continue
            label = expected_risk(action, location, items)
            if label and label != action.get("risk"):
                changes.append((location["id"], action["id"], str(action.get("risk")), label))
                action["risk"] = label
    text = path.read_text(encoding="utf-8")
    indent = 2 if '\n  "' in text[:200] else None
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=indent) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    return changes


if __name__ == "__main__":
    for name in PACKS:
        for change in fix_pack(ROOT / "host/prompt/processed" / name):
            print(name, *change, sep=" | ")
