"""Install empty normal overlays without changing the frozen baby values."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from host.difficulty import DIFFICULTY_LABELS, validate_difficulty

ROOT = Path(__file__).resolve().parents[2]
REVISION = "2026-10-20-difficulty-047"


def migrate(pack: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(pack)
    meta = result.setdefault("meta", {})
    if "difficulty" not in meta:
        meta["difficulty"] = {
            "default": "normal",
            "base": "baby",
            "modes": [{"id": mode, "label": label} for mode, label in DIFFICULTY_LABELS.items()],
        }
        meta["content_revision"] = max(str(meta.get("content_revision", "")), REVISION)
    result.setdefault("difficulty_overlays", {"normal": []})
    validate_difficulty(result)
    return result


def main() -> None:
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / name
        original = json.loads(path.read_text(encoding="utf-8"))
        updated = migrate(original)
        if updated != original:
            path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{name}: {updated['meta']['content_revision']}")


if __name__ == "__main__":
    main()
