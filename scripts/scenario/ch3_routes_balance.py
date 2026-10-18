"""Apply only the design-approved second- and third-round changes for spec 037."""
from __future__ import annotations

import json
from typing import Any

from .risk_labels import PACKS, ROOT
from .oaksdawn import LIESE_DESCRIPTION, RECRUIT_PREVIEW
from .rumbling_gorge import ELIO_DESCRIPTION, ELIO_RECRUIT_PREVIEW

CLOAK_DESCRIPTION = "死者を鎮める祈りの文句が縫い込まれた古い外套。被ダメージを1軽減し、古戦場の亡者からの被ダメージはさらに2軽減する。"


def apply(pack: dict[str, Any]) -> None:
    pack["meta"]["content_revision"] = max(pack["meta"].get("content_revision", ""), "2026-10-18-v037-r3")
    cloak = next(i for i in pack["items"] if i["id"] == "gravekeeper_cloak")
    cloak["description"] = CLOAK_DESCRIPTION
    cloak["combat"]["defense"] = 1
    cloak["combat"]["conditional_defense"].update(amount=2, description="霧の古戦場：被ダメージをさらに2軽減")
    tower = next(loc for loc in pack["locations"] if loc["id"] == "ruined_watchtower")
    search = next(a for a in tower["actions"] if a["id"] == "search_watchtower")
    for effect in search["effects"]:
        if effect.get("equip_item") == cloak["name"]:
            effect["equip_item_if_empty"] = effect.pop("equip_item")
    liese = next(c for c in pack["companions"] if c["id"] == "paladin_liese")
    liese["description"] = LIESE_DESCRIPTION
    liese["round_start_effects"][0]["max_hp_ratio"] = .20
    liese["round_start_effects"][1]["damage"] = "2d6"
    elio = next(c for c in pack["companions"] if c["id"] == "hydromancer_elio")
    elio["description"] = ELIO_DESCRIPTION
    elio["round_start_effects"][0]["damage"] = "2d6"
    elio["round_start_effects"][1]["every_n_rounds"] = 4
    for location in pack["locations"]:
        previews = {}
        for entry in location.get("actions", []):
            for prefix, preview in (("recruit_liese_", RECRUIT_PREVIEW), ("recruit_elio_", ELIO_RECRUIT_PREVIEW)):
                if entry["id"].startswith(prefix):
                    entry["preview"] = preview
                    previews[entry["text"]] = preview
        for choice in location.get("choices", []):
            if choice["text"] in previews:
                choice["preview"] = previews[choice["text"]]


def main() -> None:
    for filename in PACKS:
        path = ROOT / "host/prompt/processed" / filename
        pack = json.loads(path.read_text(encoding="utf-8"))
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
