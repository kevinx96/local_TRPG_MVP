"""Apply spec 040's noncombat checks to both scenario packs, idempotently."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from host.state import CHECK_ATTRIBUTE_LABELS, CHECK_SKILLS

ROOT = Path(__file__).resolve().parents[2]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
# action: skill, DC, chapter level (also used by the offline probability report).
CHECKS = {
    "ask_general_advice": ("運動", 10, 1),
    "ask_blue_mage_rumor": ("洞察", 10, 1),
    "borrow_fire_bat_dragon": ("説得", 10, 1),
    "ignore_lost_goblin": ("洞察", 10, 1),
    "fort_first_bypass": ("隠密", 10, 2),
    "fort_second_bypass": ("隠密", 12, 2),
    "bypass_hobgoblin": ("隠密", 12, 2),
    "invent_goblin_password": ("はったり", 12, 2),
    "decode_seal": ("魔法学", 10, 2),
    "pray_at_seal": ("信仰", 10, 2),
    "force_seal": ("運動", 12, 2),
    "sneak_heat": ("隠密", 10, 2),
    "sneak_crystal": ("知覚", 10, 2),
    "approach_burning_village_carefully": ("知覚", 10, 3),
    "inspect_frost_core": ("調査", 10, 3),
    "bypass_ice_elemental": ("魔法学", 10, 3),
    "break_burning_beam": ("運動", 10, 3),
    "climb_to_window": ("軽業", 10, 3),
    "sneak_through_ash": ("隠密", 10, 3),
    "sneak_bone_field": ("隠密", 10, 3),
    "sneak_ghoul_marsh": ("隠密", 12, 3),
    "recruit_liese_persuade": ("説得", 10, 3),
    "recruit_elio_persuade": ("説得", 10, 3),
    "sneak_gorge_rockfall_path": ("隠密", 10, 3),
    "sneak_gorge_giant_path": ("隠密", 12, 3),
    "sneak_gorge_worm_lair": ("隠密", 12, 3),
    "cross_lava_bridge": ("軽業", 12, 4),
    "evade_ice_sentinels": ("知覚", 12, 4),
    "sneak_into_mansion": ("隠密", 12, 5),
}
SUPPLEMENTAL_CHECKS = {
    "ask_ian_legend": ("洞察", 8),
    "invite_robin": ("説得", 10),
}
OBSERVATIONS = {
    ("castle", "general_breath"): ("知覚", 12),
    ("elf_spring", "small_footprints"): ("知覚", 8),
    ("goblin_fort_third_gate", "iron_gate_window"): ("知覚", 10),
    ("ice_elemental_encounter", "frost_crystal"): ("知覚", 10),
    ("cave_seal", "seal_glyphs"): ("魔法学", 10),
    ("valley_lava_bridge", "bridge_ropes"): ("知覚", 8),
}
PROFICIENCIES = {
    "hero": ["運動", "説得", "知覚"], "cleric": ["信仰", "洞察", "説得"],
    "mage": ["魔法学", "調査", "知覚"], "thief": ["隠密", "軽業", "はったり"],
}
ASSISTANCE = {
    "robin": (["隠密", "知覚"], "ロビンの助言"),
    "blue_robed_mage": (["魔法学", "調査"], "ワーロックの助言"),
    "fire_bat_dragon": (["運動"], "火コウモリ竜の助言"),
    "mina": (["魔法学"], "ミーナの助言"),
    "paladin_liese": (["信仰", "説得"], "リーゼの助言"),
    "hydromancer_elio": (["知覚", "調査"], "エリオの助言"),
}
CLUE_REASONS = {"decode_seal": "封印の知識", "cross_lava_bridge": "焦げた縄"}


def walk(actions: list[dict[str, Any]]):
    for action in actions:
        yield action
        yield from walk(action.get("children", []))


def risk_label(skill: str, dc: int) -> str:
    return f"{skill}（{CHECK_ATTRIBUTE_LABELS[CHECK_SKILLS[skill]]}）判定・DC{dc}"


def convert_roll(roll: dict[str, Any], skill: str, dc: int) -> None:
    roll.update(skill=skill, dice_type=f"1d20+{CHECK_SKILLS[skill]}", dc=dc)


def upgrade(pack: dict[str, Any]) -> None:
    pack["meta"]["checks_v2_v040"] = True
    for character in pack["characters"]:
        if character["id"] in PROFICIENCIES:
            character["check_proficiencies"] = list(PROFICIENCIES[character["id"]])
    for companion in pack["companions"]:
        if companion["id"] in ASSISTANCE:
            skills, reason = ASSISTANCE[companion["id"]]
            companion["check_assistance"] = {"skills": list(skills), "reason": reason}
    for location in pack["locations"]:
        for obstacle in location.get("obstacles", []):
            if "sneak_dc" in obstacle:
                obstacle["sneak_dc"] = 10
                if "hint" in obstacle:
                    obstacle["hint"] = obstacle["hint"].replace("次の潜行の難度が3下がる", "次の潜行判定が有利になる")
        for action in walk(location.get("actions", [])):
            identifier = action["id"]
            assignment = CHECKS.get(identifier) or SUPPLEMENTAL_CHECKS.get(identifier)
            if assignment:
                skill, dc = assignment[:2]
                convert_roll(action["roll"], skill, dc)
                for variant in action["roll"].pop("dc_overrides", []):
                    condition = {"requirements": variant["requirements"], "reason": CLUE_REASONS[identifier]}
                    if condition not in action["roll"].setdefault("advantage", []):
                        action["roll"]["advantage"].append(condition)
                cost = "・SP1消費" if "SP1消費" in action.get("risk", "") else ""
                action["risk"] = risk_label(skill, dc) + cost
                if identifier == "ask_general_advice":
                    action["risk"] = "筋力または耐久が10以上で" + action["risk"]
            free = action.get("free_action", {})
            if free.get("operation") == "sneak":
                action["risk"] = risk_label("隠密", 10) + "・SP1消費"
        for obj in location.get("objects", []):
            key = (location["id"], obj["id"])
            if key in OBSERVATIONS:
                convert_roll(obj["observe_reveals"]["roll"], *OBSERVATIONS[key])


def fix_pack(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    pack = json.loads(text)
    upgrade(pack)
    indent = 2 if '\n  "' in text[:200] else None
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=indent) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")


if __name__ == "__main__":
    for name in PACKS:
        fix_pack(ROOT / "host/prompt/processed" / name)
