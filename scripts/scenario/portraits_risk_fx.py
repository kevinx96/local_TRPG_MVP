"""Apply the data-only corrections from spec 030 to both scenario packs."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .risk_labels import PACKS, ROOT, annotate_risks


def upgrade(pack: dict[str, Any]) -> dict[str, Any]:
    portraits = []
    encounters = []

    def inherit(actions, location, portrait=""):
        for action in actions:
            if portrait and not action.get("portrait_image"):
                action["portrait_image"] = portrait
                portraits.append({"location": location, "action": action["id"], "image": portrait})
            inherit(action.get("children", []), location, action.get("portrait_image", ""))

    for location in pack["locations"]:
        inherit(location.get("actions", []), location["id"])
        enemies = location.get("combat", {}).get("enemy_ids")
        if enemies is not None and location.get("enemy_ids") != enemies:
            encounters.append({"location": location["id"], "before": location.get("enemy_ids"), "after": enemies})
            location["enemy_ids"] = deepcopy(enemies)
    return {"portraits": portraits, "encounters": encounters, "risks": annotate_risks(pack)}


def main() -> None:
    report = {}
    for name in PACKS:
        path = ROOT / "host/prompt/processed" / name
        original = path.read_text(encoding="utf-8")
        pack = json.loads(original)
        report[name] = upgrade(pack)
        indent = 2 if '\n  "' in original[:200] else None
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=indent) + ("\n" if original.endswith("\n") else ""), encoding="utf-8")
    target = ROOT / "eval/reports/030-data.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
