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
LOCK_TEXT = "致命の一撃――だが、剣の温もりがあなたを踏みとどまらせた。"
AWAKEN_TEXT = (
    "握り続けた鉄の剣からまばゆい白光が溢れ出し、古い地金を脱ぎ捨てるように"
    "『勇者の聖剣』へと姿を変えた。あたたかな光が全身を駆け巡り、"
    "深く刻まれた傷口がたちまち塞がっていく。「……まだ、終わらせはしない」"
)
SWORD_DESCRIPTION = "鉄の剣が真の輝きを取り戻した姿。盟約を乱す者を討つ、聖なる光の刃。"
SWORD_EFFECT = "通常攻撃が敵の耐性を貫く光属性の大ダメージになる。"
REVEAL_NO_DIARY_TEXT = (
    "「……もっとも、お前が手放したあの古びた剣は、すでに我が手にある。"
    "眠れる力を宿した唯一の刃も、もはや我には届かぬ」"
)
REVEAL_DIARY_TEXT = (
    "「……だが、お前が鍛冶屋に預けたあの剣は、すでに我が手にある。"
    "我を脅かしうる唯一の刃を手放すとは、愚かなことだ」"
)
START_TEXT = "ドラコは奪い取った『勇者の聖剣』を携えている。"
IRON_HINT = "手に馴染むほど、なぜか手放してはならない気がしてくる。"
BLACKSMITH_HINT = (
    "ローベルトは剣の重みを確かめ、ふと眉をひそめた。"
    "「……妙だな。ただの安物にしちゃ、芯に不思議な馴染みがある。"
    "手放すなら、よく考えてからにしな」"
)
STOLEN_SKILL_NAME = "簒奪の聖光斬"


def migrate(pack: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(pack)
    normal = {"difficulty_only": ["normal"]}
    requirement_b = {"all": [{"character_id": "hero"}, {"flag": "accepted_sword_fusion"}]}
    previous = next((item for item in result["items"] if item["id"] == "hero_holy_sword"), {})
    sword = {**deepcopy(previous), "id": "hero_holy_sword", "name": "勇者の聖剣", **normal,
             "description": SWORD_DESCRIPTION, "effect": SWORD_EFFECT,
             "category": "equipment", "slot": "weapon",
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
         "extra_enemy_skills": [{"id": "stolen_holy_blade", "name": STOLEN_SKILL_NAME, "kind": "attack",
                                 "damage": "1d8+5", "accuracy": 90, "element": "holy", "ai_weight": 2}]},
    ]
    encounter["encounter_modifiers"] = [entry for entry in encounter["encounter_modifiers"]
                                         if entry["id"] not in {a["id"] for a in additions}] + additions
    report = next(a for a in locations["castle_report"]["actions"] if a["id"] == "report_with_evidence")
    originals = [v for v in report["result_variants"] if not v.get("id", "").startswith("holy_sword_")]
    diary_text = next(v["text"] for v in originals if v["requirements"] == {"has_item": "白竜の日誌"})
    neutral = diary_text.split("あなたが日誌を掲げると、")[0]
    report["result_variants"] = [
        {"id": "holy_sword_diary", **normal, "requirements": {"all": [requirement_b, {"has_item": "白竜の日誌"}]},
         "text": diary_text + REVEAL_DIARY_TEXT},
        {"id": "holy_sword_neutral", **normal, "requirements": requirement_b,
         "text": neutral + REVEAL_NO_DIARY_TEXT},
        *originals,
    ]

    blacksmith = next(a for a in locations["forge"]["actions"] if a["id"] == "show_sword_to_blacksmith")
    blacksmith_variants = [v for v in blacksmith.get("result_variants", [])
                           if v.get("id") != "holy_sword_blacksmith_hint"]
    blacksmith_variants.append({"id": "holy_sword_blacksmith_hint", **normal,
                                "text": str(blacksmith.get("result_text") or "") + BLACKSMITH_HINT})
    blacksmith["result_variants"] = blacksmith_variants

    hybrid = locations["castle_report"].get("hybrid")
    if isinstance(hybrid, dict):
        prepared_turns = [turn for turn in hybrid.get("prepared_turns", [])
                          if turn.get("id") not in {"holy_sword_reveal_neutral", "holy_sword_reveal_diary"}]
        neutral_requirements = {"all": [{"character_id": "hero"}, {"flag": "accepted_sword_fusion"},
                                        {"lacks_item": "白竜の日誌"}]}
        diary_requirements = {"all": [{"character_id": "hero"}, {"flag": "accepted_sword_fusion"},
                                      {"has_item": "白竜の日誌"}]}
        prepared_turns[:0] = [
            {"id": "holy_sword_reveal_neutral", "action_id": "report_with_evidence", "outcome": "neutral",
             "difficulty_only": ["normal"], "requirements": neutral_requirements,
             "draft": {"gm_text": neutral + REVEAL_NO_DIARY_TEXT}},
            {"id": "holy_sword_reveal_diary", "action_id": "report_with_evidence", "outcome": "neutral",
             "difficulty_only": ["normal"], "requirements": diary_requirements,
             "draft": {"gm_text": diary_text + REVEAL_DIARY_TEXT}},
        ]
        hybrid["prepared_turns"] = prepared_turns
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
    overlay_revision = ROOT / "host/prompt/processed/difficulty/overlay_revision.json"
    with overlay_revision.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
