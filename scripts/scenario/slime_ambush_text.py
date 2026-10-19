"""Pass 3 cut each spring ambush wave to one slime; make the prose match (pass3 report TODO(design))."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
FIRST_WAVE = "休息を破って、泉の水面からスライムが一匹這い上がってきた。"
FIRST_VICTORY = ("スライムを弾き飛ばした直後、泉の反対側で水音がした。休む間もなく、"
                 "もう一匹のスライムが水面から這い上がり、じりじりと間合いを詰めてくる。")


def apply(pack: dict[str, Any]) -> None:
    location = next(loc for loc in pack["locations"] if loc["id"] == "slime_ambush_one")
    location["description"] = FIRST_WAVE
    location["combat"].setdefault("result_texts", {})["victory"] = FIRST_VICTORY
    if isinstance(location.get("hybrid"), dict):
        location["hybrid"]["summary"] = FIRST_WAVE


def main() -> None:
    for name in PACKS:
        path = ROOT / "host" / "prompt" / "processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[slime_ambush_text] updated {name}")


if __name__ == "__main__":
    main()
