"""Keep scenario text pure Japanese and list the English spellings the client shows with katakana ruby."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from host.item_mechanics import ELEMENT_LABELS

ROOT = Path(__file__).resolve().parents[2]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
# Katakana in the text -> English base shown over it. The player's own name is never annotated.
NAMES = {
    "エドワード": "Edward", "ローベルト": "Robert", "ドラコ": "Draco", "イアン": "Ian", "ロビン": "Robin",
    "ワーロック": "Warlock", "サラ": "Sarah", "ミーナ": "Mina", "ガルド": "Gald", "イグニス": "Ignis",
    "リク": "Riku", "ヴァルター": "Walter", "リーゼ": "Liese", "ブリギッテ": "Brigitte", "エリオ": "Elio",
    "ゼボク": "Zebok", "ヴァイス": "Weiss", "ザンザス": "Xanxus",
}
ENGLISH_ELEMENT = re.compile(r"(?<![A-Za-z])(" + "|".join(ELEMENT_LABELS) + r")属性")
REVISION = "2026-10-19-ruby"


def _text(value: str) -> str:
    value = value.replace("Xanxus", "ザンザス")
    return ENGLISH_ELEMENT.sub(lambda match: ELEMENT_LABELS[match.group(1)] + "属性", value)


def _walk(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {k: _walk(v, k) for k, v in value.items()}
    if isinstance(value, list):
        if key == "keywords":
            # Players may still type the Latin spelling, so keywords keep both forms.
            return list(dict.fromkeys(v if v == "Xanxus" else _walk(v) for v in value))
        return [_walk(v, key) for v in value]
    if isinstance(value, str):
        return _text(value)
    return value


def apply(pack: dict[str, Any]) -> None:
    updated = _walk(pack)
    pack.clear()
    pack.update(updated)
    pack["meta"]["ruby_names"] = dict(NAMES)
    pack["meta"]["content_revision"] = max(pack["meta"].get("content_revision", ""), REVISION)


def main() -> None:
    for name in PACKS:
        path = ROOT / "host" / "prompt" / "processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ruby_names] updated {name}")


if __name__ == "__main__":
    main()
