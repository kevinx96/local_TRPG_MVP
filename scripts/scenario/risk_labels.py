"""Derive each leaf action's visible risk label from its real mechanics, so players choose with accurate information."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
COMBAT_LABEL = "危険（戦闘）"
# These location changes represent an action in the current scene, not exploration.
ACTION_RISK_IDS = {
    "rest_at_elf_spring", "rest_at_inn", "admit_no_password", "steal_lost_goblin_box",
    "betray_cursed_merchant", "refuse_xanxus_with_rescue", "report_with_evidence",
    "cleanse_fire_seed",
    "regroup_from_fort_third_gate",
}


def movement_destinations(action: dict[str, Any]) -> list[str]:
    def walk(value):
        if isinstance(value, dict):
            if value.get("current_location"):
                yield str(value["current_location"])
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)
    return sorted(set(walk([action.get(key) for key in ("effects", "success_effects", "failure_effects")])))


def risk_source(action: dict[str, Any]) -> str:
    if action.get("roll") or action.get("free_action") or action.get("id") in ACTION_RISK_IDS:
        return "action"
    return "destination" if movement_destinations(action) else "action"


def annotate_risks(pack: dict[str, Any]) -> list[dict[str, Any]]:
    locations = {location["id"]: location for location in pack["locations"]}
    items = {item["id"]: item["name"] for item in pack.get("items", []) if item.get("id")}
    classification = []
    for location in pack["locations"]:
        for action in _walk(location.get("actions") or []):
            if action.get("children"):
                continue
            source = risk_source(action)
            action["risk_source"] = source
            destinations = movement_destinations(action)
            label = expected_risk(action, location, items, locations)
            if label:
                action["risk"] = label
            classification.append({"location": location["id"], "action": action["id"],
                                   "source": source, "destinations": destinations, "risk": action.get("risk", "")})
    return classification


def _walk(actions):
    for action in actions:
        yield action
        yield from _walk(action.get("children") or [])


def _starts_combat(action: dict[str, Any]) -> bool:
    blocks = [action.get(key) or [] for key in ("effects", "success_effects")]
    return bool(action.get("start_combat")) or any(isinstance(effect, dict) and effect.get("start_combat") for block in blocks for effect in block)


def expected_risk(action: dict[str, Any], location: dict[str, Any], items: dict[str, str],
                  locations: Optional[dict[str, Any]] = None) -> Optional[str]:
    """Return the label the mechanics imply, or None when the current label should be kept."""
    risk = str(action.get("risk") or "")
    roll = action.get("roll")
    if isinstance(roll, dict) and int(roll.get("dc") or 0) >= 100:
        return "危険"
    if risk.startswith("未知"):
        return None  # deliberately hidden checks
    if "以上で" in risk:
        return None  # labels that also state an eligibility requirement are written by hand
    if isinstance(roll, dict) and roll.get("dc") is not None:
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
    if locations and location.get("scene_id") != "throne_room" and risk_source(action) == "destination":
        for destination in movement_destinations(action):
            target = locations.get(destination, {})
            if target.get("combat", {}).get("enemy_ids", target.get("enemy_ids")):
                return COMBAT_LABEL
    return None


def fix_pack(path: Path) -> list[tuple[str, str, str, str]]:
    pack = json.loads(path.read_text(encoding="utf-8"))
    changes = []
    before = {(loc["id"], a["id"]): a.get("risk") for loc in pack["locations"] for a in _walk(loc.get("actions") or [])}
    annotate_risks(pack)
    for location in pack["locations"]:
        for action in _walk(location.get("actions") or []):
            if action.get("children"):
                continue
            previous = before.get((location["id"], action["id"]))
            if action.get("risk") != previous:
                changes.append((location["id"], action["id"], str(previous), action["risk"]))
    text = path.read_text(encoding="utf-8")
    indent = 2 if '\n  "' in text[:200] else None
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=indent) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    return changes


if __name__ == "__main__":
    for name in PACKS:
        for change in fix_pack(ROOT / "host/prompt/processed" / name):
            print(name, *change, sep=" | ")
