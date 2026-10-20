"""Idempotent 050 data migration. Shared baby records remain unchanged."""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from host.difficulty import overlay_fingerprint, validate_difficulty

REVISION = "2026-10-21-levels-skills-v2"


def skill(identifier: str, name: str, cost: int = 0, cost_type: str = "mp", **fields: Any) -> dict[str, Any]:
    return {"id": identifier, "name": name, "description": "【仮】", "cost": cost, "cost_type": cost_type, **fields}


def passive(identifier: str, name: str, *tiers: dict[str, Any]) -> dict[str, Any]:
    return {"id": identifier, "name": name, "stackable": len(tiers) > 1,
            "tiers": [{"id": str(i), "tier": i, "description": "【仮】", "effects": effects}
                      for i, effects in enumerate(tiers, 1)]}


def classes() -> list[dict[str, Any]]:
    hero = [
        skill("holy_sword_art", "聖光の剣技", 2, damage="1d6+str/4", accuracy=92,
              multi_elements=["physical", "holy"], hits_per_element=1, self_status="holy_blessing"),
        skill("sweep", "薙ぎ払い", 3, "sp", damage="1d6+str/4", accuracy=90, element="physical", all_targets=True,
              conditional_multipliers=[{"if": "single_enemy", "x": 1.75}]),
        skill("dragon_slash", "竜断ちの一太刀", costs={"sp": 7, "mp": 5}, damage="2d10+str/2+5",
              accuracy=100, element="physical", ignores_defense=True, ignores_resistance=True,
              conditional_multipliers=[{"if": "any", "conditions": [
                  {"if": "target_boss"}, {"if": "target_id_in", "ids": ["ignis", "draco_dragon", "dragon_knight_mounted", "lava_drake"]},
                  {"if": "target_max_hp_gte", "value": 80}], "x": 1.35}]),
    ]
    cleric = [
        skill("atonement_mark", "贖罪の印", 2, "sp", kind="attack", damage="0", accuracy=95, element="holy",
              status_on_hit=True, on_hit_status={"id": "holy_mark", "duration": 3}),
        skill("great_heal_cleanse", "大いなる癒し・浄化", 14, kind="heal", healing="2d6+wis/2",
              replaces="大いなる癒し", cleanse={"tags": ["debuff"], "count": "all"}, overflow_shield={"id": "holy_afterglow", "max_hp_ratio": .25}),
        skill("seraphim_gospel", "セラフィムの福音", 12, kind="status", max_uses_per_battle=1,
              self_status={"id": "gospel", "duration": 3, "modifiers": {
                  "max_hp_multiplier": 2, "heal_after_attack_ratio": .08, "heal_limit_per_round": 2}}),
    ]
    mage = [
        skill("mana_condense", "魔力凝縮", 3, "sp", kind="restore", resource="mp", amount="int/3+2",
              self_status=[{"id": "magic_focus", "modifiers": {"next_spell_damage_multiplier": 1.3}},
                           {"id": "mana_veil", "modifiers": {"received_damage_multiplier": .5}}]),
        skill("twin_storm", "氷炎の双嵐", 7, damage="1d6+int/6", accuracy=92, spell_tier="advanced",
              multi_elements=["fire", "ice"], hits_per_element=1,
              conditional_multipliers=[{"if": "target_hp_full", "element": "fire", "x": 2},
                                      {"if": "target_hp_ratio_lte", "ratio": .5, "element": "ice", "x": 2}]),
        skill("elemental_collapse", "元素崩壊", 18, damage="1d4+int/5", accuracy=95, spell_tier="advanced",
              learned_elements=True, max_hits=4, resonance_exempt=True),
    ]
    thief = [
        skill("blinding_throw", "目潰し投げ", 2, damage="1d4+dex/4", accuracy=95, element="physical",
              on_hit_status={"id": "blind", "duration": 2}),
        skill("blade_dance", "刃の乱舞", 4, "sp", damage="1d4+dex/4", accuracy=95, element="physical",
              all_targets=True, on_hit_status={"id": "poison", "stacks": 1}),
        skill("shadow_haste", "神速の影分身", costs={"sp": 8, "mp": 4}, kind="status", cooldown=5,
              self_status={"id": "haste", "duration": 3}),
    ]
    hp = [
        passive("departure_spirit", "旅立ちの気概",
                {"opening_rounds": 1, "opening_sp": 3}, {"opening_rounds": 2, "opening_sp": 3}),
        passive("heavy_armor_lore", "重装の心得", {"armor_min": 1, "armor_bonus": 1}),
        passive("unsinkable_shield", "不沈の盾", {"skill_overrides": {"divine_guard": {"free_action": True, "cooldown": 2}}}),
        passive("sword_followup", "追い打ちの剣", {"hit_followup": {"weapon_half_dice": True, "element": "physical",
                "accuracy": 100, "skills": ["power_slash", "holy_sword_art", "dragon_slash"], "basic": True}}),
        passive("adversity_flame", "逆境の焔", {"low_hp": {"ratio": .5, "cost_multiplier": .5, "damage_multiplier": 1.25}}),
        passive("sword_saint", "剣聖の境地", {"physical_penetration": .3}),
        passive("dragon_destiny", "竜殺しの宿命", {"taken_elements": {"fire": .8, "ice": .8, "wind": .8, "dark": .8},
                "weakness_followup": {"element": "weakness", "damage": "1d4+str/6", "accuracy": 100}}),
    ]
    cp = [
        passive("pious_heart", "敬虔なる心", *[{"regen_ratio": n} for n in (.03, .05, .07)]),
        passive("overflow_mercy", "溢れる慈愛", *[{"overflow_ratio": n} for n in (.75, 1.25)]),
        passive("ascetic_wisdom", "苦行の悟り", {"sp_for_mp": {"rate": 2, "max_ratio": .5}}),
        passive("holy_halo", "光輪の加護", {"round_attack": {"hp_ratio_gt": .7, "damage": "1d3+wis/8",
                "element": "holy", "accuracy": 100, "target": "random_enemy"}}),
        passive("immortal_sanctuary", "不滅の聖域", {"free_skills": ["healing_prayer"]}),
    ]
    mp = [
        passive("mana_cycle", "魔力循環", *[{"mana_cycle": {"amount": n, "cap_ratio": cap}}
                                           for n, cap in ((1, .2), (2, .3), (3, .4))]),
        passive("arcane_guard", "魔導の盾", {"battle_shield": {"id": "arcane_shield"}},
                {"battle_shield": {"id": "arcane_shield"}, "shield_regain": {"every": 3, "max": 2,
                 "status": {"id": "arcane_shield", "modifiers": {"shield": {"block_one_attack": True, "max_hp_ratio": .2}}}}}),
        passive("element_resonance", "元素共鳴", {"resonance": {"multiplier": 1.15, "refund": 1}}),
        passive("mana_armor", "マナ・アーマー", {"mana_armor": .25}),
        passive("omni_master", "万象の支配者", {"basic_element": "weakness", "fallback_element": "arcane", "weak_multiplier": 1.25}),
    ]
    tp = [
        passive("acrobatics", "軽業の身のこなし", *[{"evade_bonus": evade, "miss_sp": sp, "miss_sp_cap": cap}
                                                 for evade, sp, cap in ((5, 1, 2), (8, 1, 3), (10, 2, 4))]),
        passive("poison_craft", "毒使いの技", *[{"hit_status": {"id": "poison", "stacks": 1, "max_stacks": cap}} for cap in (3, 5)]),
        passive("hidden_weapon_master", "暗器の達人", {"free_item_uses": 1}),
        passive("counter_sight", "見切り反撃", {"counter_attack": {"damage": "1d6", "element": "physical", "accuracy": 100}}),
        passive("unseen_assassin", "無明の暗殺者", {"encounter_damage": {"elite": 1.15, "boss": 1.15}}),
    ]
    groups = [
        [("departure_spirit", "heavy_armor_lore"), ("departure_spirit", "unsinkable_shield"),
         ("sword_followup", "adversity_flame"), ("sword_saint", "dragon_destiny")],
        [("pious_heart", "overflow_mercy"), ("pious_heart", "ascetic_wisdom"),
         ("overflow_mercy", "holy_halo"), ("immortal_sanctuary", "pious_heart")],
        [("mana_cycle", "arcane_guard"), ("element_resonance", "mana_cycle"),
         ("mana_armor", "arcane_guard"), ("omni_master", "mana_cycle")],
        [("acrobatics", "poison_craft"), ("hidden_weapon_master", "acrobatics"),
         ("counter_sight", "poison_craft"), ("unseen_assassin", "acrobatics")],
    ]
    return [{"id": cid, "difficulty_only": ["normal"],
             "actives": [{"id": str(level), "level": level, "skill": s} for level, s in zip((3, 5, 7), actives)],
             "passive_groups": [{"id": str(level), "level": level, "options": list(options)}
                                for level, options in zip((2, 4, 6, 8), pairs)], "passives": passives}
            for cid, actives, passives, pairs in zip(("hero", "cleric", "mage", "thief"),
                                                    (hero, cleric, mage, thief), (hp, cp, mp, tp), groups)]


def migrate(pack: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(pack)
    result.setdefault("progression", {})
    result["class_progression"] = classes()
    # Use the existing Lv1 IDs for passive targets.
    templates = {c["id"]: c for c in result["characters"]}
    hero_attack = templates["hero"]["skills"][0]["id"]
    heal_id = next(s["id"] for s in templates["cleric"]["skills"] if s.get("healing"))
    result["class_progression"][0]["passives"][3]["tiers"][0]["effects"]["hit_followup"]["skills"][0] = hero_attack
    result["class_progression"][1]["passives"][4]["tiers"][0]["effects"]["free_skills"] = [heal_id]
    entries = [{"entity": "progression", "id": "$", "path": key, "set": value} for key, value in {
        "level_model": "exp", "max_level": 8,
        "exp_table": dict(zip(map(str, range(2, 9)), (20, 50, 90, 140, 200, 280, 380))),
        "exp_rewards": {"trash": 5, "elite": 15, "boss": 40, "unclassified": 5, "quest": 10, "scripted_loss": 0, "guest": 0},
        "level_gains": deepcopy(result["milestones"][0]["gains"]),
    }.items()]
    for identifier, condition in (("fireball", {"if": "target_hp_full", "damage": "1d6"}),
                                  ("ice_arrow", {"if": "target_hp_ratio_lte", "ratio": .5, "damage": "1d6"})):
        for key, value in (("conditional_bonus", [condition]), ("spell_tier", "basic")):
            entries.append({"entity": "characters", "id": "mage", "path": f"skills.@id={identifier}.{key}", "set": value})
    existing = result["difficulty_overlays"]["normal"]
    addresses = {(e["entity"], e["id"], e["path"]) for e in entries}
    result["difficulty_overlays"]["normal"] = [e for e in existing if (e["entity"], e["id"], e["path"]) not in addresses] + entries
    books = [
        ("spellbook_lightning", "雷撃の術式巻物", 60,
         skill("lightning", "雷撃", 5, damage="1d4+int/4", accuracy=90, element="lightning", all_targets=True, spell_tier="basic")),
        ("spellbook_arcane_lance", "魔力の槍の術式巻物", 45,
         skill("arcane_lance", "魔力の槍", 4, damage="1d6+int/2", accuracy=95, element="arcane", ignores_defense=True, spell_tier="basic")),
    ]
    shop = next(s for s in result["shops"] if s["id"] == "magic_shop")
    for identifier, name, price, spell in books:
        previous = next((i for i in result["items"] if i["id"] == identifier), {})
        item = {**deepcopy(previous), "id": identifier, "name": name, "description": "【仮】", "category": "spellbook",
                "icon": "/static/images/icon_magic_scroll.png",
                "difficulty_only": ["normal"], "learn_skill": spell, "learnable_by": ["mage"],
                "consumable": True, "sell_price": price // 2}
        result["items"] = [i for i in result["items"] if i["id"] != identifier] + [item]
        shop["items"] = [i for i in shop["items"] if i.get("item_id") != identifier] + [
            {"item_id": identifier, "price": price, "stock": 1, "difficulty_only": ["normal"]}]
    if not any(s["id"] == "mana_veil" for s in result["status_defs"]):
        result["status_defs"].append({"id": "mana_veil", "name": "凝縮の構え", "description": "【仮】",
                                     "kind": "modifier", "duration": 1, "tags": ["buff"], "cleansable": False,
                                     "expires": "enemy_phase_end", "modifiers": {"received_damage_multiplier": .5}})
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
    (ROOT / "host/prompt/processed/difficulty/overlay_revision.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
