"""Copy frozen v2 labels and recipes into an explicitly unreviewed current-scenario suite."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .snapshots import ROOT

SOURCE = ROOT / "eval/benchmark/intent_v2.jsonl"
OUTPUT = ROOT / "eval/candidates/intent_v2_current.jsonl"
CURRENT_SCENARIO = "host/prompt/processed/dragon_rpg.json"


def current_copy(rows: list[dict[str, Any]], recipes: dict[str, dict[str, Any]]) -> tuple:
    copied_rows = deepcopy(rows)
    copied_recipes = {}
    for identifier, recipe in recipes.items():
        if not identifier.startswith("v2_") or recipe["id"] != identifier:
            raise ValueError(f"Expected a v2 snapshot: {identifier}")
        current_id = "v2cur_" + identifier.removeprefix("v2_")
        copied_recipes[current_id] = {**deepcopy(recipe), "id": current_id, "scenario": CURRENT_SCENARIO}
    for row in copied_rows:
        if row["snapshot"] not in recipes:
            raise ValueError(f"Missing snapshot: {row['snapshot']}")
        row["id"] = "v2cur-" + row["id"].removeprefix("v2-")
        row["snapshot"] = "v2cur_" + row["snapshot"].removeprefix("v2_")
        row["label_status"] = "needs_review"
    return copied_rows, copied_recipes


def generate(root: Path = ROOT) -> tuple[int, int]:
    rows = [json.loads(line) for line in (root / SOURCE.relative_to(ROOT)).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    recipes = {name: json.loads((root / "eval/snapshots" / f"{name}.json").read_text(encoding="utf-8"))
               for name in sorted({row["snapshot"] for row in rows})}
    copied_rows, copied_recipes = current_copy(rows, recipes)
    for name, recipe in copied_recipes.items():
        (root / "eval/snapshots" / f"{name}.json").write_text(
            json.dumps(recipe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output = root / OUTPUT.relative_to(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in copied_rows), encoding="utf-8")
    return len(copied_rows), len(copied_recipes)


if __name__ == "__main__":
    rows, snapshots = generate()
    print(f"Generated {rows} needs_review cases and {snapshots} current-scenario snapshots.")
