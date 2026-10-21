"""049 normal-only sword thread. Re-running this migration is a no-op."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from host.difficulty import overlay_fingerprint, validate_difficulty

ROOT = Path(__file__).resolve().parents[2]
REVISION = "2026-10-21-sword-049"
HOLY_DAMAGE = "1d8+78"
HOLY_ACCURACY = 95
LOCK_TEXT = "【仮】致命の一撃――だが、あなたは倒れなかった。"
AWAKEN_TEXT = "【仮】鉄の剣が白く輝き、勇者の聖剣へと姿を変えた。傷がふさがっていく。"
REVEAL_TEXT = "【仮】……もっとも、貴様の剣ならすでに我が手にある。我を脅かしうる唯一の刃だ"
START_TEXT = "【仮】ドラコは勇者の聖剣を装備している。"
# TODO(design): Replace all 【仮】 text and select dedicated sword art.
IRON_HINT = "【仮】"


def migrate(pack: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(pack)
    normal = {"difficulty_only": ["normal"]}
    requirement_b = {"all": [{"character_id": "hero"}, {"flag": "accepted_sword_fusion"}]}
    previous = next((item for item in result["items"] if item["id"] == "hero_holy_sword"), {})
    sword = {**deepcopy(previous), "id": "hero_holy_sword", "name": "勇者の聖剣", **normal,
             "description": "【仮】眠っていた力を取り戻した、勇者のための剣。",
             "effect": "【仮】通常攻撃が光属性になる", "category": "equipment", "slot": "weapon",
             "key_item": True, "non_removable": True, "awakening_only": True,
             "awakening_origin": {"item": "iron_sword", "description_suffix": IRON_HINT},
             "icon": "/static/images/icon_dawn_sword.png",
             "combat": {"kind": "weapon", "name": "勇者の聖剣", "element": "holy",
                        "damage": HOLY_DAMAGE, "accuracy": HOLY_ACCURACY, "ignores_resistance": True}}
    result["items"] = [item for item in result["items"] if item["id"] != sword["id"]]
    insertion = next((i for i, item in enumerate(result["items"]) if item["id"] == "travel_potion"), len(result["items"]))
    result["items"].insert(insertion, sword)
    locations = {location["id"]: location for location in result["locations"]}
    encounter = locations["draco_battle"]["combat"]
    additions = [
        {"id": "hero_holy_sword", **normal,
         "requirements": {"all": [{"character_id": "hero"}, {"flag": "defeated_ignis"},
                                  {"equipped_item": "鉄の剣"}]},
         "lethal_awakening": {"id": "hero_holy_sword", "transform_item": {"from": "鉄の剣", "to": "hero_holy_sword"},
                             "restore": {"hp": "full"}, "set_flag": "holy_sword_awakened",
                             "lock_text": LOCK_TEXT, "text": AWAKEN_TEXT}},
        {"id": "draco_holy_sword", **normal, "enemy_ids": ["draco_human"],
         "requirements": requirement_b, "enemy_damage_multiplier": 1.3,
         "text": START_TEXT, "log_kind": "warning",
         "extra_enemy_skills": [{"id": "stolen_holy_blade", "name": "【仮】聖剣の一閃", "kind": "attack",
                                 "damage": "1d8+5", "accuracy": 90, "element": "holy", "ai_weight": 2}]},
    ]
    encounter["encounter_modifiers"] = [entry for entry in encounter["encounter_modifiers"]
                                         if entry["id"] not in {a["id"] for a in additions}] + additions
    report = next(a for a in locations["castle_report"]["actions"] if a["id"] == "report_with_evidence")
    originals = [v for v in report["result_variants"] if not v.get("id", "").startswith("holy_sword_")]
    diary_text = next(v["text"] for v in originals if v["requirements"] == {"has_item": "白竜の日誌"})
    # The existing prepared draft is the canonical neutral reveal text in both packs.
    neutral = diary_text.split("あなたが日誌を掲げると、")[0]
    report["result_variants"] = [
        {"id": "holy_sword_diary", **normal, "requirements": {"all": [requirement_b, {"has_item": "白竜の日誌"}]},
         "text": diary_text + REVEAL_TEXT},
        {"id": "holy_sword_neutral", **normal, "requirements": requirement_b, "text": neutral + REVEAL_TEXT},
        *originals,
    ]
    result["meta"]["content_revision"] = max(result["meta"]["content_revision"], REVISION)
    validate_difficulty(result)
    return result


def main() -> None:
    manifest = {}
    for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / name
        original = json.loads(path.read_text(encoding="utf-8"))
        updated = migrate(original)
        if updated != original:
            path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest[name] = {"content_revision": updated["meta"]["content_revision"], "overlay_sha256": overlay_fingerprint(updated)}
    (ROOT / "host/prompt/processed/difficulty/overlay_revision.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
