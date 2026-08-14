from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent / "prompt" / "processed"
SCENARIOS = (ROOT / "dragon_rpg.json", ROOT / "dragon_rpg_hybrid.json")

BACKGROUND_IMAGES = {
    "castle": "/static/images/bg_dragon_rpg.png",
    "forge": "/static/images/bg_forge.png",
    "inn": "/static/images/bg_inn.png",
    "village": "/static/images/bg_village.png",
    "dragon_valley_loc": "/static/images/bg_dragon_valley.png",
    "magic_shop": "/static/images/bg_magic_shop.png",
    "item_shop": "/static/images/bg_item_shop.png",
    "alley": "/static/images/bg_alley_day.png",
    "alley_night": "/static/images/bg_alley_night.png",
    "merchant_battle": "/static/images/bg_alley_night.png",
    "alley_after": "/static/images/bg_alley_night.png",
    "dark_forest_loc": "/static/images/bg_dark_forest.png",
    "lost_goblin_crossroads": "/static/images/bg_dark_forest.png",
    "elf_spring": "/static/images/bg_elf_spring.png",
    "forest_wolves": "/static/images/bg_dark_forest.png",
    "slime_ambush_one": "/static/images/bg_elf_spring.png",
    "slime_ambush_two": "/static/images/bg_elf_spring.png",
    "slime_king_battle": "/static/images/bg_elf_spring.png",
    "forest_exit": "/static/images/bg_dark_forest.png",
    "goblin_fort": "/static/images/bg_goblin_fort.png",
    "goblin_fort_first_second": "/static/images/bg_goblin_fort.png",
    "goblin_fort_second_choice": "/static/images/bg_goblin_fort.png",
    "goblin_fort_second_right": "/static/images/bg_goblin_fort.png",
    "goblin_fort_second_left": "/static/images/bg_goblin_fort.png",
    "goblin_fort_healing_circle": "/static/images/bg_goblin_fort.png",
    "goblin_fort_third_gate": "/static/images/bg_goblin_fort.png",
    "goblin_fort_third_guards": "/static/images/bg_goblin_fort.png",
    "goblin_fort_fourth": "/static/images/bg_goblin_treasure.png",
    "goblin_fort_chest_choice": "/static/images/bg_goblin_treasure.png",
    "goblin_fort_chest_fight": "/static/images/bg_goblin_treasure.png",
    "village_approach": "/static/images/bg_burning_village.png",
    "village_fire_slime": "/static/images/bg_burning_village.png",
    "village_fire_elemental": "/static/images/bg_burning_village.png",
    "xanxus_confrontation": "/static/images/bg_burning_village.png",
    "xanxus_battle": "/static/images/bg_burning_village.png",
    "xanxus_ultimatum": "/static/images/bg_burning_village.png",
    "warlock_rescue_battle": "/static/images/bg_burning_village.png",
    "village_frozen_clue": "/static/images/bg_frozen_village.png",
    "ice_elemental_encounter": "/static/images/bg_frozen_village.png",
    "frost_wolf_battle": "/static/images/bg_frozen_village.png",
    "ian_ice_katana_aftermath": "/static/images/bg_frozen_village.png",
}

NPC_IMAGES = {
    "king": "/static/images/npc_king.png",
    "blacksmith": "/static/images/npc_blacksmith.png",
    "elder": "/static/images/npc_elder.png",
    "shopkeeper": "/static/images/npc_shopkeeper.png",
    "general": "/static/images/npc_general.png",
    "ian": "/static/images/npc_ian.png",
    "robin": "/static/images/npc_robin.png",
    "blue_robed_mage": "/static/images/npc_warlock.png",
    "sarah": "/static/images/npc_sarah.png",
    "suspicious_merchant": "/static/images/npc_suspicious_merchant.png",
    "lost_goblin": "/static/images/npc_lost_goblin.png",
    "xanxus": "/static/images/npc_xanxus.png",
    "warlock": "/static/images/npc_warlock.png",
    "fire_bat_dragon": "/static/images/companion_fire_bat_dragon.png",
}

CHARACTER_IMAGES = {
    "hero": "/static/images/char_male_hero_v2.png",
    "cleric": "/static/images/char_cleric_v2.png",
    "mage": "/static/images/char_mage_v2.png",
    "thief": "/static/images/char_thief_v2.png",
}

ENEMY_IMAGES = {
    "slime": "/static/images/enemy_slime.png",
    "ignis": "/static/images/enemy_ignis.png",
    "goblin": "/static/images/enemy_goblin.png",
    "goblin_archer": "/static/images/enemy_goblin_archer.png",
    "hobgoblin": "/static/images/enemy_hobgoblin.png",
    "war_hound": "/static/images/enemy_war_hound.png",
    "forest_wolf": "/static/images/enemy_forest_wolf.png",
    "slime_king": "/static/images/enemy_slime_king.png",
    "goblin_king": "/static/images/enemy_goblin_king.png",
    "zebok": "/static/images/enemy_zebok.png",
    "fire_slime": "/static/images/enemy_fire_slime.png",
    "fire_elemental": "/static/images/enemy_fire_elemental.png",
    "ice_elemental": "/static/images/enemy_ice_elemental.png",
    "frost_dire_wolf": "/static/images/enemy_frost_dire_wolf.png",
    "xanxus": "/static/images/npc_xanxus.png",
}

COMPANION_IMAGES = {
    "robin": "/static/images/npc_robin.png",
    "blue_robed_mage": "/static/images/npc_warlock.png",
    "fire_bat_dragon": "/static/images/companion_fire_bat_dragon.png",
}

LOCATION_PORTRAITS = {
    "castle": "/static/images/npc_king.png",
    "forge": "/static/images/npc_blacksmith.png",
    "inn": "/static/images/npc_ian.png",
    "village": "/static/images/npc_elder.png",
    "magic_shop": "/static/images/npc_warlock.png",
    "item_shop": "/static/images/npc_sarah.png",
    "alley_night": "/static/images/npc_suspicious_merchant.png",
    "merchant_battle": "/static/images/enemy_zebok.png",
    "lost_goblin_crossroads": "/static/images/npc_lost_goblin.png",
    "goblin_fort_chest_choice": "/static/images/npc_lost_goblin.png",
    "goblin_fort_chest_fight": "/static/images/npc_lost_goblin.png",
    "xanxus_confrontation": "/static/images/npc_xanxus.png",
    "xanxus_battle": "/static/images/npc_xanxus.png",
    "xanxus_ultimatum": "/static/images/npc_xanxus.png",
    "warlock_rescue_battle": "/static/images/npc_warlock.png",
    "ian_ice_katana_aftermath": "/static/images/npc_ian_serious.png",
}

LOCATION_NPC_PORTRAIT_OVERRIDES = {
    "ian_ice_katana_aftermath": {"ian": "/static/images/npc_ian_serious.png"},
}

ACTION_PORTRAITS = {
    "ask_king_info": "/static/images/npc_king.png",
    "ask_general_advice": "/static/images/npc_general.png",
    "buy_equipment": "/static/images/npc_blacksmith.png",
    "buy_adamantite_armor": "/static/images/npc_blacksmith.png",
    "buy_ice_amulet": "/static/images/npc_blacksmith.png",
    "ask_blacksmith_weakness": "/static/images/npc_blacksmith.png",
    "show_sword_to_blacksmith": "/static/images/npc_blacksmith.png",
    "accept_sword_fusion": "/static/images/npc_blacksmith.png",
    "activate_ice_charm": "/static/images/npc_blacksmith.png",
    "ask_ian": "/static/images/npc_ian.png",
    "ask_ian_legend": "/static/images/npc_ian.png",
    "ask_ian_advice": "/static/images/npc_ian.png",
    "rest_at_inn": "/static/images/npc_ian.png",
    "ask_robin": "/static/images/npc_robin.png",
    "invite_robin": "/static/images/npc_robin.png",
    "ask_robin_rumor": "/static/images/npc_robin.png",
    "accept_robin_goblin_quest": "/static/images/npc_robin.png",
    "ask_elder_weakness": "/static/images/npc_elder.png",
    "blue_mage_shop": "/static/images/npc_warlock.png",
    "buy_earth_staff": "/static/images/npc_warlock.png",
    "buy_healing_scroll": "/static/images/npc_warlock.png",
    "buy_fireball_scroll": "/static/images/npc_warlock.png",
    "ask_blue_mage_rumor": "/static/images/npc_warlock.png",
    "invite_blue_mage": "/static/images/npc_warlock.png",
    "sarah_shop": "/static/images/npc_sarah.png",
    "buy_sarah_herb_1": "/static/images/npc_sarah.png",
    "buy_sarah_herb_2": "/static/images/npc_sarah.png",
    "buy_sarah_herb_3": "/static/images/npc_sarah.png",
    "buy_smoke_bomb": "/static/images/npc_sarah.png",
    "buy_poison_dart": "/static/images/npc_sarah.png",
    "borrow_fire_bat_dragon": "/static/images/companion_fire_bat_dragon.png",
    "help_lost_goblin": "/static/images/npc_lost_goblin.png",
    "ignore_lost_goblin": "/static/images/npc_lost_goblin.png",
    "return_lost_goblin_box": "/static/images/npc_lost_goblin.png",
    "steal_lost_goblin_box": "/static/images/npc_lost_goblin.png",
    "bluff_xanxus": "/static/images/npc_xanxus.png",
    "ambush_xanxus": "/static/images/npc_xanxus.png",
    "flee_from_xanxus": "/static/images/npc_xanxus.png",
    "accept_xanxus_fire_seed": "/static/images/npc_xanxus.png",
    "refuse_xanxus_with_rescue": "/static/images/npc_xanxus.png",
    "refuse_xanxus_without_rescue": "/static/images/npc_xanxus.png",
    "accept_ian_request": "/static/images/npc_ian_serious.png",
    "refuse_ian_after_xanxus": "/static/images/npc_ian_serious.png",
    "refuse_ian_before_xanxus": "/static/images/npc_ian_serious.png",
}

for _merchant_action in (
    "hear_curse_offer_hero", "accept_curse_offer_hero",
    "hear_curse_offer_cleric", "accept_curse_offer_cleric",
    "hear_curse_offer_mage", "accept_curse_offer_mage",
    "hear_curse_offer_thief", "accept_curse_offer_thief",
    "pay_curse_price_hero", "pay_curse_price_cleric",
    "pay_curse_price_mage", "pay_curse_price_thief",
    "betray_cursed_merchant", "leave_night_alley",
):
    ACTION_PORTRAITS[_merchant_action] = "/static/images/npc_suspicious_merchant.png"


def upsert(records: list[dict[str, Any]], record: dict[str, Any]) -> None:
    for index, existing in enumerate(records):
        if existing.get("id") == record.get("id"):
            records[index] = deepcopy(record)
            return
    records.append(deepcopy(record))


def action(action_id: str, text: str, preview: str = "", risk: str = "判定不要", **extra: Any) -> dict[str, Any]:
    result = {
        "id": action_id,
        "text": text,
        "preview": preview,
        "risk": risk,
        "intent_keywords": [text],
    }
    result.update(extra)
    return result


def prepared(
    turn_id: str,
    action_id: str,
    text: str,
    outcome: str = "neutral",
    notes: list[str] | None = None,
    combat_text: str = "",
) -> dict[str, Any]:
    draft = {"gm_text": text, "system_log": "", "state_delta": {}, "choices": []}
    if combat_text:
        draft["combat_text"] = combat_text
    return {
        "id": turn_id,
        "purpose": "choice_response",
        "source_choice": "",
        "player_intent": action_id,
        "trigger_keywords": [],
        "action_id": action_id,
        "outcome": outcome,
        "draft": draft,
        "rewrite_notes": notes or ["確定済みのアクション結果だけを自然な日本語で描写してください。"],
    }


def hybrid(turns: list[dict[str, Any]], summary: str = "") -> dict[str, Any]:
    return {"mode": "prepared_gm_turns", "summary": summary, "prepared_turns": turns}


def location(location_id: str, title: str, description: str, actions: list[dict[str, Any]], *,
             npc_ids: list[str] | None = None, item_ids: list[str] | None = None, enemy_ids: list[str] | None = None,
             combat: dict[str, Any] | None = None, turns: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if location_id.startswith(("dark_", "forest_", "elf_", "lost_", "goblin_")):
        scene_id = "dark_forest"
    elif location_id.startswith(("village", "xanxus", "warlock", "ice_", "frost_", "ian_")):
        scene_id = "village"
    else:
        scene_id = "throne_room"
    return {
        "id": location_id,
        "scene_id": scene_id,
        "title": title,
        "description": description,
        "keywords": [title],
        "npc_ids": npc_ids or [],
        "item_ids": item_ids or [],
        "clue_ids": [],
        "enemy_ids": enemy_ids or [],
        "connected_location_ids": [],
        "choices": [],
        "hybrid": hybrid(turns or [], description),
        "combat": combat or {"flee_allowed": True, "victory_effects": {}, "defeat_effects": {}},
        "actions": actions,
    }


def combat_start_action(action_id: str, text: str, preview: str = "戦闘を開始します") -> dict[str, Any]:
    return action(action_id, text, preview, "戦闘開始", silent=True, effects=[{"start_combat": True}])


def apply_visual_assets(pack: dict[str, Any]) -> None:
    for npc in pack.get("npcs", []):
        if isinstance(npc, dict) and str(npc.get("id") or "") in NPC_IMAGES:
            npc["image"] = NPC_IMAGES[str(npc["id"])]
    for enemy in pack.get("enemies", []):
        if isinstance(enemy, dict) and str(enemy.get("id") or "") in ENEMY_IMAGES:
            enemy["image"] = ENEMY_IMAGES[str(enemy["id"])]
    for companion in pack.get("companions", []):
        if isinstance(companion, dict) and str(companion.get("id") or "") in COMPANION_IMAGES:
            companion["image"] = COMPANION_IMAGES[str(companion["id"])]
    for character in pack.get("characters", []):
        if not isinstance(character, dict):
            continue
        character_id = str(character.get("id") or "")
        if character_id in CHARACTER_IMAGES:
            character["image"] = CHARACTER_IMAGES[character_id]
            if character_id == "hero":
                character["image_female"] = "/static/images/char_female_hero_v2.png"
        elif character_id == "warlock":
            character["image"] = "/static/images/npc_warlock.png"
    for place in pack.get("locations", []):
        if not isinstance(place, dict):
            continue
        location_id = str(place.get("id") or "")
        if location_id in BACKGROUND_IMAGES:
            place["background_image"] = BACKGROUND_IMAGES[location_id]
        if location_id in LOCATION_PORTRAITS:
            place["portrait_image"] = LOCATION_PORTRAITS[location_id]
        if location_id in LOCATION_NPC_PORTRAIT_OVERRIDES:
            place["npc_portrait_overrides"] = deepcopy(LOCATION_NPC_PORTRAIT_OVERRIDES[location_id])
        _apply_action_portraits(place.get("actions"))
    for scene in pack.get("scenes", []):
        if isinstance(scene, dict):
            _apply_action_portraits(scene.get("actions"))


def _apply_action_portraits(actions: Any) -> None:
    for entry in actions if isinstance(actions, list) else []:
        if not isinstance(entry, dict):
            continue
        action_id = str(entry.get("id") or entry.get("action_id") or "")
        if action_id == "check_supplies":
            entry.pop("portrait_image", None)
        elif action_id in ACTION_PORTRAITS:
            entry["portrait_image"] = ACTION_PORTRAITS[action_id]
        _apply_action_portraits(entry.get("children"))


def add_catalog(pack: dict[str, Any]) -> None:
    npcs = pack.setdefault("npcs", [])
    for npc in [
        {
            "id": "blue_robed_mage",
            "name": "青いローブの魔法使い",
            "description": "銀髪で、背に素朴な杖を負った三十歳ほどの青いローブの男性魔法使い。",
            "keywords": ["青いローブ", "銀髪", "魔法使い"],
        },
        {
            "id": "sarah",
            "name": "サラ",
            "description": "道具屋を切り盛りする十歳ほどの金髪の少女。火コウモリ竜を大切にしている。",
            "keywords": ["サラ", "金髪", "道具屋"],
        },
        {
            "id": "suspicious_merchant",
            "name": "怪しい商人",
            "description": "黒いローブに包まれた小柄で毛むくじゃらの人物。フードが顔を完全に隠している。",
            "keywords": ["怪しい商人", "黒いローブ", "夜の路地"],
        },
        {
            "id": "lost_goblin",
            "name": "迷子のゴブリン",
            "description": "別の一族に箱を盗まれ、闇の森で助けを求めているゴブリン。",
            "keywords": ["迷子", "ゴブリン", "箱"],
        },
        {
            "id": "fire_bat_dragon",
            "name": "火コウモリ竜",
            "description": "サラが大切にしている、火をまとった小さな翼竜。",
            "keywords": ["火コウモリ竜", "ペット", "翼竜"],
        },
    ]:
        upsert(npcs, npc)

    companions = pack.setdefault("companions", [])
    for companion in [
        {
            "id": "robin",
            "name": "ロビン",
            "description": "闇の森に詳しい女レンジャー。",
            "round_start_effects": [],
        },
        {
            "id": "blue_robed_mage",
            "name": "青いローブの魔法使い",
            "description": "毎ラウンド開始時にプレイヤーのHPを8回復する。",
            "round_start_effects": [{"kind": "heal_player", "amount": "8"}],
        },
        {
            "id": "fire_bat_dragon",
            "name": "火コウモリ竜",
            "description": "毎ラウンド開始時に敵へ2d3の火属性ダメージを与え、プレイヤーのHPを3回復する。",
            "round_start_effects": [
                {"kind": "damage_enemy", "name": "火炎の羽ばたき", "damage": "2d3", "element": "fire"},
                {"kind": "heal_player", "amount": "3"},
            ],
        },
    ]:
        upsert(companions, companion)

    items = pack.setdefault("items", [])
    item_records = [
        {
            "id": "earth_staff", "name": "大地の杖", "description": "大地の魔力を宿す40Gの杖。装備すると裂地尖刺を習得する。",
            "combat": {"kind": "weapon", "name": "大地の杖", "damage": "1d6+int/4", "accuracy": 90, "element": "earth", "grants_skills": [
                {"id": "earth_spikes", "name": "裂地尖刺", "kind": "attack", "description": "地面にいる全ての敵を岩の槍で貫く。", "damage": "1d10+int/2", "accuracy": 90, "element": "earth", "all_targets": True, "cost": 4, "cost_type": "mp"}
            ]},
        },
        {"id": "healing_scroll", "name": "治療の巻物", "description": "使用すると直ちにHPを30回復する。", "combat": {"kind": "heal", "healing": "30", "consumable": True}},
        {"id": "fireball_scroll", "name": "火球術の巻物", "description": "知力10として火球を一度だけ放つ。", "combat": {"kind": "damage", "damage": "1d6+5", "accuracy": 90, "element": "fire", "consumable": True}},
        {"id": "smoke_bomb", "name": "煙幕弾", "description": "通常戦闘から確実に逃走する。ボス戦では無効。", "combat": {"kind": "flee", "consumable": True}},
        {"id": "poison_dart", "name": "毒矢", "description": "1ダメージを与え、戦闘終了まで毎ラウンド4ダメージの毒を付与する。", "combat": {"kind": "damage", "damage": "1", "accuracy": 100, "element": "physical", "consumable": True, "on_hit_status": {"id": "poison_dart", "name": "毒", "damage": "4", "stackable": False}}},
        {"id": "cursed_holy_sword", "name": "呪われた聖剣", "description": "攻撃を倍化するが、攻撃のたびに自身も1ダメージを受ける。", "combat": {"kind": "weapon", "name": "呪われた聖剣", "damage": "1d8+str/3", "damage_multiplier": 2, "accuracy": 90, "element": "cursed", "self_damage": 1}},
        {"id": "cursed_holy_staff", "name": "呪われた聖杖", "description": "一ラウンドに二回行動でき、治癒量が二倍になりさらに10増えるが、人間への治癒はダメージになる。", "combat": {"kind": "weapon", "name": "呪われた聖杖", "damage": "1d4+str/4", "accuracy": 90, "element": "holy", "extra_actions_per_round": 1, "healing_multiplier": 2, "skill_healing_bonus": 10, "healing_harms_humans": True}},
        {"id": "cursed_crystal_ball", "name": "呪われた水晶球", "description": "闇の力と亡霊召喚を授ける水晶球。", "combat": {"kind": "equipment", "grants_skills": [
            {"id": "dark_orb", "name": "暗黒球", "kind": "attack", "damage": "2d6+int/2", "accuracy": 92, "element": "dark", "cost": 3, "cost_type": "mp"},
            {"id": "summon_bone_dragon", "name": "亡霊召喚", "kind": "attack", "damage": "7d4", "accuracy": 100, "element": "dark", "cost": 8, "cost_type": "mp", "check": {"formula": "1d20+int", "dc": 22, "failure_effect": "undead_conversion"}}
        ]}},
        {"id": "dark_crystal_ball", "name": "暗黒の水晶球", "description": "ゼボクの力を奪った水晶球。代価の呪いから解放されている。", "combat": {"kind": "equipment", "grants_skills": [
            {"id": "dark_orb", "name": "暗黒球", "kind": "attack", "damage": "2d6+int/2", "accuracy": 92, "element": "dark", "cost": 3, "cost_type": "mp"},
            {"id": "summon_bone_dragon", "name": "亡霊召喚", "kind": "attack", "damage": "7d4", "accuracy": 100, "element": "dark", "cost": 8, "cost_type": "mp", "check": {"formula": "1d20+int", "dc": 22, "failure_effect": "undead_conversion"}}
        ]}},
        {"id": "cursed_dagger", "name": "呪われた短剣", "description": "攻撃が命中するたび、毎ラウンド3ダメージの毒を重ねる。", "combat": {"kind": "weapon", "name": "呪われた短剣", "damage": "1d6+dex/4", "accuracy": 95, "element": "cursed", "on_hit_status": {"id": "cursed_poison", "name": "累積毒", "damage": "3", "stackable": True}}},
        {"id": "rusted_crown", "name": "錆びた王冠", "description": "スライム王が身につけていた錆びた王冠。今のところ効果はない。"},
        {"id": "shrinking_gun", "name": "縮小の銃", "description": "ごく低確率で敵を縮小し、HPと最大HPを10分の1にする。何度でも使える。", "combat": {"kind": "shrink", "chance": 2, "consumable": False}},
        {
            "id": "activated_ice_charm",
            "name": "氷の護符(活性化済)",
            "description": "鍛冶師が武器へ嵌め込み、真の力を引き出した氷の護符。",
            "effect": "通常攻撃のたびに1d8+INT/2の氷属性追撃を行う。",
            "keywords": ["氷の護符", "活性化", "氷属性"],
            "combat": {
                "kind": "equipment",
                "basic_attack_followup": {
                    "name": "氷の護符の追撃",
                    "damage": "1d8+int/2",
                    "accuracy": 100,
                    "element": "ice",
                },
            },
        },
    ]
    for item in item_records:
        upsert(items, item)

    enemies = pack.setdefault("enemies", [])
    enemy_records = [
        {"id": "goblin", "name": "ゴブリン", "description": "粗末な短剣を持つ小鬼。", "hp": 15, "max_hp": 15, "attributes": {"str": 6, "dex": 8, "int": 2, "end": 6}, "combat": {"basic_attack": {"name": "粗末な短剣", "damage": "1d4+dex/4", "accuracy": 85, "element": "physical"}, "defense": 0, "evade": 8}, "resistances": {}, "rewards": {"gold": 5, "items": [], "flags": []}, "skills": []},
        {"id": "goblin_archer", "name": "弓ゴブリン", "description": "高所から粗末な弓を射るゴブリン。", "hp": 12, "max_hp": 12, "attributes": {"str": 4, "dex": 10, "int": 2, "end": 5}, "combat": {"basic_attack": {"name": "粗末な矢", "damage": "1d6+dex/5", "accuracy": 88, "element": "physical"}, "defense": 0, "evade": 10}, "resistances": {}, "rewards": {"gold": 5, "items": [], "flags": []}, "skills": []},
        {"id": "hobgoblin", "name": "大ゴブリン", "description": "重い棍棒を振るう大柄なゴブリン。", "hp": 30, "max_hp": 30, "attributes": {"str": 12, "dex": 5, "int": 4, "end": 12}, "combat": {"basic_attack": {"name": "大棍棒", "damage": "1d8+str/4", "accuracy": 82, "element": "physical"}, "defense": 2, "evade": 3}, "resistances": {}, "rewards": {"gold": 5, "items": [], "flags": []}, "skills": []},
        {"id": "war_hound", "name": "猛犬", "description": "砦で飼い慣らされた獰猛な犬。", "hp": 10, "max_hp": 10, "attributes": {"str": 7, "dex": 10, "end": 6}, "combat": {"basic_attack": {"name": "噛みつき", "damage": "1d4+str/4", "accuracy": 88, "element": "physical"}, "defense": 0, "evade": 10}, "resistances": {}, "rewards": {"gold": 0, "items": [], "flags": []}, "skills": []},
        {"id": "forest_wolf", "name": "森狼", "description": "闇の森を群れで狩る狼。", "hp": 18, "max_hp": 18, "attributes": {"str": 9, "dex": 11, "end": 8}, "combat": {"basic_attack": {"name": "牙", "damage": "1d6+str/4", "accuracy": 88, "element": "physical"}, "defense": 1, "evade": 10}, "resistances": {}, "rewards": {"gold": 0, "items": [], "flags": []}, "skills": []},
        {"id": "slime_king", "name": "スライム王", "description": "錆びた王冠を載せた巨大なスライム。", "hp": 38, "max_hp": 38, "attributes": {"str": 11, "dex": 2, "int": 3, "end": 14}, "combat": {"basic_attack": {"name": "王の圧潰", "damage": "1d8+str/4", "accuracy": 82, "element": "physical"}, "defense": 2, "evade": 2}, "resistances": {"fire": 1.25}, "rewards": {"gold": 15, "items": [{"name": "錆びた王冠", "quantity": 1}], "flags": ["defeated_slime_king"]}, "skills": []},
        {"id": "goblin_king", "name": "ゴブリン王", "description": "砦の財宝を支配するゴブリンの王。", "hp": 55, "max_hp": 55, "attributes": {"str": 14, "dex": 8, "int": 7, "end": 14}, "combat": {"basic_attack": {"name": "王の戦斧", "damage": "1d10+str/4", "accuracy": 88, "element": "physical"}, "defense": 3, "evade": 5}, "resistances": {}, "rewards": {"gold": 100, "items": [], "flags": ["defeated_goblin_king"]}, "skills": []},
        {"id": "zebok", "name": "亡霊主宰ゼボク", "description": "死を逆向きに生きる亡霊の主。通常攻撃ではHPがさらに負へ沈む。", "hp": -100, "max_hp": 0, "attributes": {"str": 8, "dex": 10, "int": 16, "end": 1}, "combat": {"life_rule": "negative_undead", "basic_attack": {"name": "暗黒の爪", "damage": "1d6+int/4", "accuracy": 88, "element": "dark"}, "defense": 0, "evade": 8}, "resistances": {"holy": 1.5, "light": 1.5}, "rewards": {"gold": 0, "items": [], "flags": ["defeated_zebok"]}, "skills": [
            {"id": "zebok_bone_dragon", "name": "亡霊召喚", "kind": "attack", "damage": "7d4", "accuracy": 82, "element": "dark", "ai_weight": 2},
            {"id": "zebok_conversion", "name": "亡霊転換", "kind": "status", "status_effect": "undead_conversion", "skip_if_mage_undead": True, "ai_weight": 1},
            {"id": "dark_feast", "name": "暗黒の宴", "kind": "attack", "damage": "2d6+int", "accuracy": 85, "element": "dark", "ai_weight": 3},
        ]},
    ]
    for enemy in enemy_records:
        upsert(enemies, enemy)


def add_village_catalog(pack: dict[str, Any]) -> None:
    npcs = pack.setdefault("npcs", [])
    upsert(npcs, {
        "id": "xanxus",
        "name": "赤いローブの魔法使い・Xanxus",
        "description": "赤い法衣をまとい、全身を炎に包まれた骸骨の魔法使い。",
        "keywords": ["Xanxus", "ザンザス", "赤いローブの魔法使い"],
    })
    upsert(npcs, {
        "id": "warlock",
        "name": "青いローブの魔法使い・ワーロック",
        "description": "銀髪で、背に素朴な杖を負った青いローブの男性魔法使い。元素魔法を極めている。",
        "keywords": ["ワーロック", "青いローブの魔法使い"],
    })
    for record in pack.get("npcs", []):
        if isinstance(record, dict) and record.get("id") == "blue_robed_mage":
            record["name"] = "青いローブの魔法使い・ワーロック"
    for record in pack.get("companions", []):
        if isinstance(record, dict) and record.get("id") == "blue_robed_mage":
            record["name"] = "青いローブの魔法使い・ワーロック"

    items = pack.setdefault("items", [])
    upsert(items, {
        "id": "fire_seed",
        "name": "火種",
        "description": "Xanxusが作った火種。受ける炎属性ダメージを半減する一方、氷・水属性ダメージが倍になる。随時爆発しそうな様子をしている。",
        "non_removable": True,
        "combat": {
            "kind": "passive",
            "non_removable": True,
            "damage_taken_multipliers": {"fire": 0.5, "ice": 2.0, "water": 2.0},
        },
    })

    enemies = pack.setdefault("enemies", [])
    village_enemies = [
        {
            "id": "fire_slime", "name": "ファイアスライム", "description": "炎をまとった赤いスライム。",
            "element": "fire", "hp": 24, "max_hp": 24,
            "attributes": {"str": 8, "dex": 5, "int": 7, "end": 8},
            "combat": {"basic_attack": {"name": "火の体当たり", "damage": "1d6+int/4", "accuracy": 86, "element": "fire"}, "defense": 1, "evade": 4},
            "resistances": {"fire": 0.0, "ice": 1.5, "water": 1.5}, "rewards": {"gold": 6, "items": [], "flags": []}, "skills": [],
        },
        {
            "id": "fire_elemental", "name": "火の精霊", "description": "人の形を取った荒れ狂う炎。",
            "element": "fire", "hp": 48, "max_hp": 48,
            "attributes": {"str": 9, "dex": 9, "int": 16, "end": 10},
            "combat": {"basic_attack": {"name": "火炎の腕", "damage": "1d8+int/4", "accuracy": 88, "element": "fire"}, "defense": 2, "evade": 8},
            "resistances": {"fire": 0.0, "ice": 1.5, "water": 1.5}, "rewards": {"gold": 12, "items": [], "flags": []}, "skills": [],
        },
        {
            "id": "ice_elemental", "name": "氷の精霊", "description": "村の火災の中に佇む冷気の塊。",
            "element": "ice", "hp": 52, "max_hp": 52,
            "attributes": {"str": 10, "dex": 8, "int": 18, "end": 12},
            "combat": {"basic_attack": {"name": "氷柱", "damage": "1d8+int/4", "accuracy": 88, "element": "ice"}, "defense": 3, "evade": 7},
            "resistances": {"ice": 0.0, "fire": 1.4}, "rewards": {"gold": 15, "items": [], "flags": []}, "skills": [],
        },
        {
            "id": "frost_dire_wolf", "name": "氷霜の巨狼", "description": "氷の太刀を核として実体化した巨大な霜の狼。",
            "element": "ice", "hp": 140, "max_hp": 140,
            "attributes": {"str": 22, "dex": 18, "int": 12, "end": 22},
            "combat": {"basic_attack": {"name": "凍爪", "damage": "2d8+str/4", "accuracy": 90, "element": "ice"}, "defense": 5, "evade": 12},
            "resistances": {"ice": 0.0, "fire": 1.25}, "rewards": {"gold": 40, "items": [], "flags": ["defeated_frost_dire_wolf"]}, "skills": [],
        },
        {
            "id": "xanxus", "name": "赤炎骸骨Xanxus", "description": "赤い法衣と業火に包まれた骸骨の大魔法使い。",
            "element": "fire", "hp": 999, "max_hp": 999, "mp": 999, "max_mp": 999,
            "attributes": {"str": 10, "dex": 20, "int": 50, "end": 35},
            "combat": {"basic_attack": {"name": "炎弾", "damage": "2d10+int/2", "accuracy": 95, "element": "fire"}, "defense": 4, "evade": 10},
            "resistances": {"fire": 0.0, "dark": 0.0}, "rewards": {"gold": 0, "items": [], "flags": []},
            "skills": [
                {"id": "flame_vortex", "name": "火炎旋渦", "kind": "field", "round_damage": "int/4", "element": "fire", "ai_weight": 3},
                {"id": "summon_meteor", "name": "隕石召喚", "kind": "attack", "damage": "int", "accuracy": 100, "element": "fire", "ai_weight": 4},
                {"id": "rebirth_in_fire", "name": "浴火重生", "kind": "heal", "healing": "int", "use_below_hp_ratio": 0.8, "healing_multiplier_below_hp_ratio": 0.5, "low_hp_multiplier": 2, "auto_trigger_below_hp_ratio": 0.2, "ai_weight": 2},
            ],
        },
    ]
    for enemy in village_enemies:
        upsert(enemies, enemy)

    characters = pack.setdefault("characters", [])
    upsert(characters, {
        "id": "warlock", "name": "青いローブの魔法使い・ワーロック", "default_name": "ワーロック",
        "selectable": False,
        "description": "元素魔法を極めた青いローブの魔法使い。", "hp": 100, "max_hp": 100,
        "mp": 999, "max_mp": 999, "sp": 20, "max_sp": 20, "gold": 0,
        "attributes": {"str": 10, "dex": 30, "int": 100, "wis": 60, "end": 40},
        "inventory": [], "equipment": [],
        "resistances": {"fire": 0.1, "water": 0.1, "lightning": 0.1, "ice": 0.1, "earth": 0.1, "wind": 0.1, "light": 0.1, "dark": 0.1},
        "combat": {"basic_attack": {"name": "元素弾", "damage": "2d10+int/2", "accuracy": 100, "element": "water"}, "defense": 4, "evade": 15},
        "skills": [
            {"id": "element_counter", "name": "元素克制", "kind": "attack", "description": "敵の属性を打ち消す元素で攻撃する。", "damage": "int+10d20", "accuracy": 100, "element": "counter"},
            {"id": "element_switch", "name": "元素切替", "kind": "stance", "description": "水晶球を敵に有利な属性へ切り替え、敵の属性攻撃を無効化する。", "immunity_from_target_element": True},
            {"id": "element_prayer", "name": "元素祈喚", "kind": "attack", "description": "風火水電氷地光闇を各三度、合計24回放つ。", "damage": "3d24", "accuracy": 100, "multi_elements": ["wind", "fire", "water", "lightning", "ice", "earth", "light", "dark"], "hits_per_element": 3},
        ],
    })


def town_locations(pack: dict[str, Any]) -> list[dict[str, Any]]:
    return [magic_shop(pack), item_shop(pack), alley_day(pack), alley_night(pack), merchant_battle(pack), alley_after(pack)]


def magic_shop(pack: dict[str, Any]) -> dict[str, Any]:
    purchases = action("blue_mage_shop", "品物を買う", "魔法の品を選びます", children=[
        action("buy_earth_staff", "大地の杖を買う（40G）", "裂地尖刺を習得する杖", requirements={"gold_gte": 40}, once="bought_earth_staff", effects=[{"gold_change": -40}, {"add_item": {"name": "大地の杖", "quantity": 1}}, {"equip_item": "大地の杖"}]),
        action("buy_healing_scroll", "治療の巻物を買う（10G）", "HPを30回復する消耗品", requirements={"gold_gte": 10}, effects=[{"gold_change": -10}, {"add_item": {"name": "治療の巻物", "quantity": 1}}]),
        action("buy_fireball_scroll", "火球術の巻物を買う（10G）", "知力10相当の火球を封じた巻物", requirements={"gold_gte": 10}, effects=[{"gold_change": -10}, {"add_item": {"name": "火球術の巻物", "quantity": 1}}]),
    ])
    rumor = action(
        "ask_blue_mage_rumor", "邪竜についての噂を聞く", "魔法使いが知る不穏な噂", "1d20+wis判定（DC14）",
        roll={"dice_type": "1d20+wis", "dc": 14}, once="asked_blue_mage_rumor",
        success_effects=[{"set_flag": "heard_human_caused_dragon_return"}],
        failure_effects=[{"set_flag": "blue_mage_discouraged_player"}],
        critical_success_effects=[{"set_flag": "heard_name_xanxus"}, {"set_flag": "warlock_rescue_available"}],
        critical_failure_effects=[{"set_flag": "blue_mage_silent"}],
        silent_outcomes=["critical_failure"],
    )
    invite = action("invite_blue_mage", "パーティーへ招く", "同行者として迎える", once="invited_blue_mage", effects=[{"set_companion": "blue_robed_mage"}, {"set_flag": "warlock_rescue_available"}])
    turns = [
        prepared("blue_mage_buy_earth_staff", "buy_earth_staff", "青いローブの魔法使いは40Gを受け取り、大地の杖を手渡した。杖を装備すると、地面を走る魔力の流れと裂地尖刺の術式が意識に刻まれた。"),
        prepared("blue_mage_buy_healing_scroll", "buy_healing_scroll", "青いローブの魔法使いは10Gを受け取り、HPを30回復する治療の巻物を手渡した。"),
        prepared("blue_mage_buy_fireball_scroll", "buy_fireball_scroll", "青いローブの魔法使いは10Gを受け取り、知力10相当の火球術を封じた巻物を手渡した。"),
        prepared("blue_mage_rumor_success", rumor["id"], "青いローブの魔法使いは声を潜めた。「邪竜の復活は自然なものではない。誰かが意図して呼び戻した、と私は見ています」", "success"),
        prepared("blue_mage_rumor_failure", rumor["id"], "魔法使いは視線を逸らした。「あなたはこの件に巻き込まれるべきではない。邪竜討伐は諦めた方がいい」", "failure"),
        prepared("blue_mage_rumor_critical", rumor["id"], "Xanxus", "critical_success"),
        prepared("blue_mage_rumor_fumble", rumor["id"], "", "critical_failure", ["一言も発させず、gm_textも空にしてください。"]),
        prepared("blue_mage_join", invite["id"], "魔法使いは背の杖を確かめ、静かに頷いた。「しばらく同行しましょう。傷の手当ては任せてください」"),
    ]
    return location("magic_shop", "王城の魔法店", "青いローブの銀髪の魔法使いが、杖を背に店番をしている。", [purchases, rumor, invite, action("return_castle_from_magic_shop", "城に戻る", effects=[{"current_location": "castle"}])], npc_ids=["blue_robed_mage"], turns=turns)


def item_shop(pack: dict[str, Any]) -> dict[str, Any]:
    herb_actions = [
        action(f"buy_sarah_herb_{index}", f"薬草を買う（5G・在庫{index}/3）", "HPを10回復する薬草", requirements={"gold_gte": 5}, once=f"bought_sarah_herb_{index}", effects=[{"gold_change": -5}, {"add_item": {"name": "薬草", "quantity": 1}}])
        for index in range(1, 4)
    ]
    purchases = action("sarah_shop", "品物を買う", "サラの道具を選びます", children=[
        *herb_actions,
        action("buy_smoke_bomb", "煙幕弾を買う（15G）", "ボス以外から確実に逃走", requirements={"gold_gte": 15}, effects=[{"gold_change": -15}, {"add_item": {"name": "煙幕弾", "quantity": 1}}]),
        action("buy_poison_dart", "毒矢を買う（12G）", "1ダメージと継続毒", requirements={"gold_gte": 12}, effects=[{"gold_change": -12}, {"add_item": {"name": "毒矢", "quantity": 1}}]),
    ])
    borrow = action(
        "borrow_fire_bat_dragon", "ペットの火コウモリ竜を借りる", "懐いてくれるか確かめます", "1d20+wis判定（DC13）",
        roll={"dice_type": "1d20+wis", "dc": 13}, once="asked_to_borrow_fire_bat_dragon",
        critical_enabled=False,
        success_effects=[{"set_companion": "fire_bat_dragon"}, {"set_flag": "borrowed_fire_bat_dragon"}],
        failure_effects=[{"set_flag": "fire_bat_dragon_dislikes_player"}],
    )
    turns = [
        *[
            prepared(f"sarah_buy_herb_{index}", f"buy_sarah_herb_{index}", "サラは5Gを受け取り、在庫から薬草を一つ取り出して手渡した。")
            for index in range(1, 4)
        ],
        prepared("sarah_buy_smoke_bomb", "buy_smoke_bomb", "サラは煙幕弾を包み、戦闘から確実に逃げられるがボスには効かないと念を押して手渡した。"),
        prepared("sarah_buy_poison_dart", "buy_poison_dart", "サラは毒矢を慎重に包み、命中後は戦闘が終わるまで毒が相手を蝕むと説明した。"),
        prepared("fire_bat_borrow_success", borrow["id"], "火コウモリ竜はあなたの匂いを嗅ぐと肩へ飛び乗った。サラは嬉しそうに笑い、「ちゃんと連れて帰ってね」と送り出した。", "success"),
        prepared("fire_bat_borrow_failure", borrow["id"], "火コウモリ竜は羽を逆立て、サラの背後へ隠れた。どうやら今は、あなたをあまり気に入っていないようだ。", "failure"),
    ]
    return location("item_shop", "王城の道具屋", "十歳ほどの金髪の少女サラと、小さな火コウモリ竜がいる。", [purchases, borrow, action("return_castle_from_item_shop", "城に戻る", effects=[{"current_location": "castle"}])], npc_ids=["sarah", "fire_bat_dragon"], turns=turns)


def alley_day(pack: dict[str, Any]) -> dict[str, Any]:
    wait = action("wait_for_night_in_alley", "夜まで待つ", "ロビンから聞いた夜の路地を調べる", visible_after="heard_robin_night_rumor", effects=[{"current_location": "alley_night"}])
    return location("alley", "王城の路地裏・昼", "昼の路地には人影がなく、奥へ進む理由も見当たらない。", [
        wait,
        action("return_castle_from_alley", "城に戻る", effects=[{"current_location": "castle"}]),
    ], turns=[prepared("alley_wait_night", wait["id"], "日が沈むまで路地の陰で待つ。街灯が揺らぎ始めると、昼にはなかった黒い人影が奥に立っていた。")])


def curse_offer(character_id: str, item_name: str, flag_suffix: str, requirement: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    hear = action(f"hear_curse_offer_{flag_suffix}", "怪しい商人の取引を聞く", "自分に見合う呪具と代価を聞く", visible_for_character=character_id, once=f"heard_curse_offer_{flag_suffix}", effects=[{"set_flag": "curse_offer_heard"}])
    accept = action(
        f"accept_curse_offer_{flag_suffix}", f"{item_name}を受け取る", "受け取った後に代価を求められる", visible_for_character=character_id,
        visible_after="curse_offer_heard", requirements=requirement or {}, once=f"accepted_curse_offer_{flag_suffix}",
        effects=[{"add_item": {"name": item_name, "quantity": 1}}, {"equip_item": item_name}, {"set_flag": "curse_bargain_pending"}],
    )
    return [hear, accept]


def alley_night(pack: dict[str, Any]) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    actions += curse_offer("hero", "呪われた聖剣", "hero", {"has_item": "鉄の剣"})
    actions += curse_offer("cleric", "呪われた聖杖", "cleric")
    actions += curse_offer("mage", "呪われた水晶球", "mage")
    actions += curse_offer("thief", "呪われた短剣", "thief")
    betray = action(
        "betray_cursed_merchant", "反悔する", "怪しい商人と戦う", "戦闘開始",
        visible_after="curse_bargain_pending",
        effects=[{"current_location": "merchant_battle"}, {"start_combat": True}],
    )
    actions += [
        action("pay_curse_price_hero", "おとなしく代価を払う", "鉄の剣を渡す", visible_for_character="hero", visible_after="curse_bargain_pending", once="paid_curse_price", effects=[{"remove_item": {"name": "鉄の剣", "quantity": 1}}, {"set_flag": "curse_price_paid"}, {"current_location": "alley_after"}]),
        action("pay_curse_price_cleric", "おとなしく代価を払う", "生命力を差し出し、耐久を1にする", visible_for_character="cleric", visible_after="curse_bargain_pending", once="paid_curse_price", effects=[{"attribute_set": {"end": 1}}, {"set_flag": "curse_price_paid"}, {"current_location": "alley_after"}]),
        action("pay_curse_price_mage", "おとなしく代価を払う", "知識を差し出し、全技能を失う", visible_for_character="mage", visible_after="curse_bargain_pending", once="paid_curse_price", effects=[{"clear_skills": True}, {"set_flag": "curse_price_paid"}, {"current_location": "alley_after"}]),
        action("pay_curse_price_thief", "おとなしく代価を払う", "敏捷を差し出し、敏捷を1にする", visible_for_character="thief", visible_after="curse_bargain_pending", once="paid_curse_price", effects=[{"attribute_set": {"dex": 1}}, {"set_flag": "curse_price_paid"}, {"current_location": "alley_after"}]),
        betray,
        action("leave_night_alley", "取引せず城へ戻る", effects=[{"current_location": "castle"}]),
    ]
    offer_texts = {
        "hero": "商人は囁いた。「勇者には呪われた聖剣を。斬撃は倍になりますが、剣は使い手の血も一滴ずつ啜る。代価はその鉄の剣です」",
        "cleric": "商人は囁いた。「僧侶には呪われた聖杖を。二度の行動と強大な治癒を授けましょう。ただし人への治癒は害となる。代価は生命力です」",
        "mage": "商人は囁いた。「魔法使いには呪われた水晶球を。暗黒球と亡霊召喚を授ける。代価は、これまで得た知識の全てです」",
        "thief": "商人は囁いた。「盗賊には呪われた短剣を。傷ごとに毒は深まる。代価はあなたの敏捷さです」",
    }
    turns: list[dict[str, Any]] = []
    for char_id, suffix in (("hero", "hero"), ("cleric", "cleric"), ("mage", "mage"), ("thief", "thief")):
        turns.append(prepared(f"curse_offer_{suffix}", f"hear_curse_offer_{suffix}", offer_texts[char_id]))
        turns.append(prepared(f"curse_received_{suffix}", f"accept_curse_offer_{suffix}", "呪具を受け取ると、商人は黒い袖から手を差し出した。「では、約束の代価を」"))
        turns.append(prepared(f"curse_paid_{suffix}", f"pay_curse_price_{suffix}", "代価が渡されると、怪しい商人は満足そうに身を引き、夜の闇へ溶けていった。"))
    turns.append(prepared(
        "curse_bargain_betrayal",
        betray["id"],
        "差し出しかけた代価を引き戻し、取引を拒絶する。怪しい商人の笑みが消え、黒衣の内側から死霊の気配が噴き出した。『契約を違えるなら、魂で払ってもらおう』小さな姿は膨れ上がり、亡霊主宰ゼボクが正体を現す。",
    ))
    return location("alley_night", "王城の路地裏・夜", "街灯の届かない場所に、黒いローブの小柄で毛むくじゃらな商人が立っている。", actions, npc_ids=["suspicious_merchant"], turns=turns)


def merchant_battle(pack: dict[str, Any]) -> dict[str, Any]:
    combat = {
        "auto_start": False,
        "boss": True,
        "flee_allowed": False,
        "enemy_ids": ["zebok"],
        "victory_effects": {"inventory_add": [{"name": "暗黒の水晶球", "quantity": 1}], "flags_set": ["zebok_escaped"], "current_location": "alley_after"},
        "victory_effects_by_character": {"mage": {"inventory_remove": [{"name": "呪われた水晶球", "quantity": 1}], "equip_item": "暗黒の水晶球", "flags_set": ["curse_price_waived"]}},
        "defeat_effects": {"game_over": {"reason": "亡霊主宰ゼボクに敗れ、亡霊として永遠に使役されました。", "ending": "zebok_servant"}},
    }
    return location("merchant_battle", "夜の路地・亡霊戦", "反悔を告げると、商人は亡霊主宰ゼボクとして正体を現した。", [], enemy_ids=["zebok"], combat=combat)


def alley_after(pack: dict[str, Any]) -> dict[str, Any]:
    return location("alley_after", "静まり返った夜の路地", "怪しい商人の姿は消え、夜風だけが路地を抜けていく。", [action("return_castle_after_curse", "城へ戻る", effects=[{"current_location": "castle"}])])


def forest_locations(pack: dict[str, Any]) -> list[dict[str, Any]]:
    locations: list[dict[str, Any]] = []
    slime_combat = {
        "auto_start": False,
        "flee_allowed": True,
        "flee_dc": 10,
        "enemy_ids": ["slime"],
        "victory_effects": {"flags_set": ["defeated_slime"], "current_location": "lost_goblin_crossroads"},
        "defeat_effects": {"hp_change": 1},
        "result_texts": {
            "victory": "スライムを倒して森を進むと、十字路で一匹のゴブリンが助けを求めていた。別の一族に箱を盗まれ、取り戻してほしいという。",
        },
    }
    locations.append(location("dark_forest_loc", "闇の森・入口", "薄暗い森の入口で、一匹のスライムが道を塞いでいる。", [combat_start_action("attack_slime", "スライムと戦う")], enemy_ids=["slime"], combat=slime_combat, turns=[prepared("dark_forest_opening", "attack_slime", "湿った土を踏みしめて森へ入ると、青いスライムが道を塞いだ。戦う準備を整える。")]))

    ignore = action(
        "ignore_lost_goblin", "迷子のゴブリンを無視する", "背を向けた隙に何か起きるかもしれない", "未知の感知判定",
        roll={"dice_type": "1d20+wis", "dc": 15}, once="ignored_lost_goblin",
        success_effects=[{"set_flag": "caught_goblin_stealing"}, {"start_combat": True}],
        failure_effects=[
            {"gold_change": -30}, {"set_flag": "robbed_by_lost_goblin"},
            {"branch": {"requirements": {"gold_lte": 30}, "then": [{"start_combat": True}], "else": [{"current_location": "elf_spring"}]}},
        ],
    )
    accept = action("help_lost_goblin", "箱を取り戻す手伝いを引き受ける", "ゴブリン砦へ向かう", once="accepted_lost_goblin_quest", effects=[{"set_flag": "lost_goblin_quest"}, {"current_location": "goblin_fort"}])
    lost_combat = {"auto_start": False, "flee_allowed": True, "enemy_ids": ["goblin"], "victory_effects": {"current_location": "elf_spring"}, "defeat_effects": {"hp_change": 1}}
    locations.append(location("lost_goblin_crossroads", "闇の森・迷子のゴブリン", "迷子のゴブリンが、別の一族に盗まれた箱を取り戻してほしいと頼んでいる。", [accept, ignore], npc_ids=["lost_goblin"], enemy_ids=["goblin"], combat=lost_combat, turns=[
        prepared("lost_goblin_accept", accept["id"], "迷子のゴブリンは何度も頭を下げ、木々の奥に隠された砦への道を案内し始めた。"),
        prepared("lost_goblin_ignore_success", ignore["id"], "背後の気配に振り返り、財布へ伸びていたゴブリンの手首を掴む。盗みを見破られたゴブリンは箱の話など忘れたように顔を歪め、短剣を抜いて飛びかかってきた。", "success"),
        prepared(
            "lost_goblin_ignore_failure",
            ignore["id"],
            "泉へ向かって歩き出した後、財布が軽くなっていることに気づいた。迷子を装ったゴブリンに金を盗まれたのだ。",
            "failure",
            combat_text="財布を奪ったゴブリンへ追いつくと、空になった袋を投げ捨てて振り返った。『もう奪える金がないなら、顔を見たお前には消えてもらう』隠していた短剣を抜き、口封じのために襲いかかってくる。",
        ),
    ]))

    rest = action("rest_at_elf_spring", "精霊の泉で休む", "HPとMPを回復して休息する", effects=[{"restore_full": True}, {"current_location": "slime_ambush_one"}, {"start_combat": True}])
    continue_action = action("continue_from_elf_spring", "休まず先へ進む", "二頭の森狼が待ち伏せている", "戦闘開始", effects=[{"current_location": "forest_wolves"}, {"start_combat": True}])
    locations.append(location("elf_spring", "精霊の泉", "淡い光を帯びた泉。休めば力を取り戻せそうだ。", [rest, continue_action], turns=[
        prepared("elf_spring_rest", rest["id"], "泉の水で傷と魔力を癒し、木陰で眠りにつく。目を覚ますと、周囲を多数のスライムが取り囲んでいた。"),
        prepared("elf_spring_continue", continue_action["id"], "泉を横目に休まず進むと、茂みの左右から低い唸り声が重なった。二頭の森狼が退路と行く手を分けて塞ぎ、牙を剥いて間合いを詰めてくる。"),
    ]))
    locations.append(location("forest_wolves", "闇の森・狼の縄張り", "泉を通り過ぎた先で二頭の森狼が襲いかかる。", [], enemy_ids=["forest_wolf", "forest_wolf"], combat={"auto_start": False, "flee_allowed": True, "enemy_ids": ["forest_wolf", "forest_wolf"], "victory_effects": {"current_location": "forest_exit"}, "defeat_effects": {"hp_change": 1}}))
    locations.append(location("slime_ambush_one", "精霊の泉・第一波", "三匹のスライムに包囲されている。", [], enemy_ids=["slime", "slime", "slime"], combat={"auto_start": False, "flee_allowed": False, "enemy_ids": ["slime", "slime", "slime"], "victory_effects": {"current_location": "slime_ambush_two"}, "defeat_effects": {"hp_change": 1}, "result_texts": {"victory": "最後の一匹を弾き飛ばした直後、泉の反対側で水音が三つ重なった。休む間もなく、新たな三匹のスライムが水面から這い上がり、半円を描いて包囲を狭めてくる。"}}))
    locations.append(location("slime_ambush_two", "精霊の泉・第二波", "さらに三匹のスライムが泉から這い出す。", [], enemy_ids=["slime", "slime", "slime"], combat={"auto_start": True, "flee_allowed": False, "enemy_ids": ["slime", "slime", "slime"], "victory_effects": {"current_location": "slime_king_battle"}, "defeat_effects": {"hp_change": 1}, "result_texts": {"victory": "第二波を退けると泉全体が大きく盛り上がった。水を押し分けて現れたのは、錆びた王冠を載せた巨大なスライムだ。スライム王は仲間の残骸を吸収し、重い身体で地面を揺らす。"}}))
    locations.append(location("slime_king_battle", "精霊の泉・スライム王", "錆びた王冠を載せたスライム王が泉を揺らして現れる。", [], enemy_ids=["slime_king"], combat={"auto_start": True, "boss": True, "flee_allowed": False, "enemy_ids": ["slime_king"], "victory_effects": {"current_location": "forest_exit"}, "defeat_effects": {"hp_change": 1}}))
    locations.append(location("forest_exit", "闇の森・出口", "木々の隙間から麓の村と山道が見えている。", [action(
        "leave_forest_for_village", "森を出て麓の村へ向かう",
        effects=[
            {"branch": {"requirements": {"companion_id": "blue_robed_mage"}, "then": [{"clear_companion": True}, {"set_flag": "warlock_disappeared_at_village"}], "else": []}},
            {"background_image": "/static/images/bg_burning_village.png"},
            {"current_location": "village_approach"},
        ],
    )], turns=[prepared("forest_exit_to_village", "leave_forest_for_village", "森を抜けて村へ近づくにつれ、空が赤く染まり、焦げた匂いが濃くなる。村はすでに一面の火海となっていた。同行していた者がいれば、背後から青いローブの気配だけが忽然と消えている。")]))
    return locations


def fort_locations(pack: dict[str, Any]) -> list[dict[str, Any]]:
    locations: list[dict[str, Any]] = []
    first_sneak = action("fort_first_bypass", "見張りを迂回する", "一階最初の戦闘を避ける", "1d20+dex判定（DC13）", roll={"dice_type": "1d20+dex", "dc": 13}, success_effects=[{"current_location": "goblin_fort_first_second"}], failure_effects=[{"start_combat": True}])
    first_combat = {"auto_start": False, "flee_allowed": True, "enemy_ids": ["goblin"], "victory_effects": {"current_location": "goblin_fort_first_second"}, "defeat_effects": {"hp_change": 1}}
    first_fight = combat_start_action("fight_fort_first_guard", "見張りのゴブリンと戦う")
    locations.append(location("goblin_fort", "ゴブリン砦・一階前半", "砦へ入ると、一匹のゴブリンが通路を見張っている。", [first_fight, first_sneak], enemy_ids=["goblin"], combat=first_combat, turns=[
        prepared("fort_first_guard_fight", first_fight["id"], "砦の入口を塞ぐ見張りへ武器を向ける。ゴブリンは侵入者に気づいて警笛へ手を伸ばすが、間に合わないと悟ると短剣を抜き、狭い通路で身構えた。"),
        prepared("fort_first_bypass_success", first_sneak["id"], "物陰と木箱を利用し、見張りに気づかれず一階奥へ進んだ。", "success"),
        prepared("fort_first_bypass_failure", first_sneak["id"], "足元の空き瓶を蹴り、見張りが短剣を抜いて警報を上げた。", "failure"),
    ]))

    second_sneak = action("fort_second_bypass", "三人組を迂回する", "一階後半の戦闘を避ける", "1d20+dex判定（DC16）", roll={"dice_type": "1d20+dex", "dc": 16}, success_effects=[{"current_location": "goblin_fort_second_choice"}], failure_effects=[{"start_combat": True}])
    second_fight = combat_start_action("fight_fort_second_guards", "三人のゴブリンと戦う")
    locations.append(location("goblin_fort_first_second", "ゴブリン砦・一階後半", "通路の先を、一匹のゴブリンと二匹の弓ゴブリンが守っている。", [second_fight, second_sneak], enemy_ids=["goblin", "goblin_archer", "goblin_archer"], combat={"auto_start": False, "flee_allowed": True, "enemy_ids": ["goblin", "goblin_archer", "goblin_archer"], "victory_effects": {"current_location": "goblin_fort_second_choice"}, "defeat_effects": {"hp_change": 1}}, turns=[
        prepared("fort_second_guards_fight", second_fight["id"], "一階奥の角を曲がると、中央のゴブリンが槍を構え、両脇の弓兵が木箱の上へ飛び乗った。矢じりがこちらを向き、三方向から逃げ道を封じてくる。"),
        prepared("fort_second_bypass_success", second_sneak["id"], "巡回の隙を読み、積み上げられた樽の陰を抜けて三人組の背後を通過した。二階へ続く階段まで誰にも気づかれていない。", "success"),
        prepared("fort_second_bypass_failure", second_sneak["id"], "身を隠した木箱が軋み、二匹の弓ゴブリンが同時に振り向いた。退路へ矢が突き刺さり、中央のゴブリンが武器を抜いて迫る。", "failure"),
    ]))
    explore_left = action("explore_fort_left", "左の通路を探索する", effects=[{"current_location": "goblin_fort_second_left"}, {"start_combat": True}])
    locations.append(location("goblin_fort_second_choice", "ゴブリン砦・二階分岐", "二階の通路は左右に分かれている。右から話し声、左から獣の唸り声が聞こえる。", [action("explore_fort_right", "右の通路を探索する", effects=[{"current_location": "goblin_fort_second_right"}]), explore_left], turns=[
        prepared("fort_left_hound_ambush", explore_left["id"], "左の扉を押し開けた瞬間、鉄鎖が床を激しく擦った。暗がりに並んだ五対の目が光り、繋がれていた猛犬たちが一斉に鎖を引きちぎって襲いかかる。"),
    ]))
    avoid_big = action("bypass_hobgoblin", "大ゴブリンを尾行して迂回する", "私室を探る", "1d20+dex判定（DC17）", roll={"dice_type": "1d20+dex", "dc": 17}, success_effects=[{"gold_change": 30}, {"set_flag": "found_hobgoblin_savings"}, {"current_location": "goblin_fort_third_gate"}], failure_effects=[{"start_combat": True}])
    fight_big = combat_start_action("fight_hobgoblin", "大ゴブリンと戦う")
    locations.append(location("goblin_fort_second_right", "ゴブリン砦・二階右", "大ゴブリンが暗号を口ずさみながら私室と廊下を往復している。", [fight_big, avoid_big], enemy_ids=["hobgoblin"], combat={"auto_start": False, "flee_allowed": True, "enemy_ids": ["hobgoblin"], "victory_effects": {"flags_set": ["goblin_password_clue"], "current_location": "goblin_fort_third_gate"}, "defeat_effects": {"hp_change": 1}}, turns=[
        prepared("hobgoblin_direct_fight", fight_big["id"], "大ゴブリンの前へ踏み出すと、相手は口ずさんでいた暗号を止め、壁に立てかけた棍棒を掴んだ。廊下を塞ぐ巨体が床板を鳴らし、正面から突進してくる。"),
        prepared("hobgoblin_bypass_success", avoid_big["id"], "大ゴブリンが離れた隙に私室へ入り、寝台の下から隠し金30Gを見つけた。", "success"),
        prepared("hobgoblin_bypass_failure", avoid_big["id"], "尾行中に床板が沈み、大ゴブリンが振り返った。『誰だ！』怒声とともに重い棍棒が壁を削り、逃げ道へ振り下ろされる。", "failure"),
    ]))
    locations.append(location("goblin_fort_second_left", "ゴブリン砦・二階左", "扉を開けた瞬間、五匹の猛犬が鎖を引きちぎって襲いかかる。", [], enemy_ids=["war_hound"] * 5, combat={"auto_start": False, "flee_allowed": False, "enemy_ids": ["war_hound"] * 5, "victory_effects": {"current_location": "goblin_fort_healing_circle"}, "defeat_effects": {"hp_change": 1}}))
    locations.append(location("goblin_fort_healing_circle", "ゴブリン砦・回復法陣", "猛犬の部屋の奥で、淡い光を放つ回復法陣が稼働している。", [action("use_fort_healing_circle", "回復法陣を使う", "全状態を回復する", effects=[{"restore_full": True}, {"current_location": "goblin_fort_third_gate"}])]))

    correct = action("give_correct_password", "暗号を答える", "入手した暗号で鉄門を開ける", visible_after="goblin_password_clue", effects=[{"current_location": "goblin_fort_fourth"}, {"start_combat": True}])
    bluff = action("invent_goblin_password", "暗号を適当に作る", "知力で門番を騙す", "1d20+int判定（DC18）", roll={"dice_type": "1d20+int", "dc": 18}, success_effects=[{"current_location": "goblin_fort_fourth"}, {"start_combat": True}], failure_effects=[{"current_location": "goblin_fort_third_guards"}, {"start_combat": True}])
    honest = action("admit_no_password", "暗号を知らないと正直に言う", "背後から警備兵が現れる", "戦闘開始", effects=[{"current_location": "goblin_fort_third_guards"}, {"start_combat": True}])
    locations.append(location("goblin_fort_third_gate", "ゴブリン砦・三階鉄門", "四階へ続く鉄門には小窓があり、中から暗号を求める声がする。", [correct, bluff, honest], turns=[
        prepared("password_correct_king_ambush", correct["id"], "覚えた暗号を告げると鉄門が開く。だが財宝庫へ足を踏み入れた途端、玉座代わりの金貨の山からゴブリン王が立ち上がり、左右の弓兵が退路へ照準を合わせた。"),
        prepared("password_bluff_success", bluff["id"], "即興の暗号を堂々と告げると鉄門が開いた。しかし先に待っていたのは財宝ではなく、金貨の山に座るゴブリン王と二匹の弓兵だった。", "success"),
        prepared("password_bluff_failure", bluff["id"], "沈黙の後、警報の鐘が鳴る。退路には三匹の大ゴブリンが立ち塞がっていた。", "failure"),
        prepared("password_honest_guards", honest["id"], "暗号を知らないと答えた瞬間、小窓が勢いよく閉じた。直後に背後の隠し扉が開き、三匹の大ゴブリンが棍棒を構えて退路を塞ぐ。"),
    ]))
    locations.append(location("goblin_fort_third_guards", "ゴブリン砦・三階警備戦", "鉄門の前後を三匹の大ゴブリンに挟まれた。", [], enemy_ids=["hobgoblin"] * 3, combat={"auto_start": False, "flee_allowed": False, "enemy_ids": ["hobgoblin"] * 3, "victory_effects": {"current_location": "goblin_fort_fourth"}, "defeat_effects": {"hp_change": 1}, "result_texts": {"victory": "三匹の警備兵を倒すと、戦闘の衝撃で鉄門の錠が外れた。扉の先は財宝庫だ。金貨の山からゴブリン王が立ち上がり、二匹の弓兵が高台へ散って次の戦いを挑んでくる。"}}))
    locations.append(location("goblin_fort_fourth", "ゴブリン砦・四階財宝庫", "財宝の山の前でゴブリン王と二匹の弓兵が待ち構えている。", [], enemy_ids=["goblin_king", "goblin_archer", "goblin_archer"], combat={"auto_start": True, "boss": True, "flee_allowed": False, "enemy_ids": ["goblin_king", "goblin_archer", "goblin_archer"], "victory_effects": {"flags_set": ["cleared_goblin_fort"], "current_location": "goblin_fort_chest_choice"}, "defeat_effects": {"hp_change": 1}}))
    return_box = action("return_lost_goblin_box", "迷子のゴブリンに箱を返す", "約束を守って砦を出る", once="resolved_lost_goblin_box", effects=[{"set_flag": "returned_lost_goblin_box"}, {"current_location": "forest_exit"}])
    steal_box = action("steal_lost_goblin_box", "ゴブリンの箱を奪う", "箱を巡って戦う", "戦闘開始", once="resolved_lost_goblin_box", effects=[{"set_flag": "betrayed_lost_goblin"}, {"current_location": "goblin_fort_chest_fight"}, {"start_combat": True}])
    locations.append(location("goblin_fort_chest_choice", "ゴブリン砦・奪還した箱", "戦いが終わると迷子のゴブリンが現れ、自分の箱を見つけて抱き寄せようとする。", [return_box, steal_box], npc_ids=["lost_goblin"], turns=[
        prepared("return_goblin_box", return_box["id"], "約束どおり箱を渡すと、ゴブリンは大切そうに抱え、何度も礼を言って森へ去った。"),
        prepared("steal_goblin_box_fight", steal_box["id"], "差し伸べられたゴブリンの手より先に箱を引き寄せる。『それは僕の箱だ！』裏切りを悟ったゴブリンは涙目のまま短剣を抜き、箱を取り戻そうと飛びかかってきた。"),
    ]))
    locations.append(location("goblin_fort_chest_fight", "ゴブリン砦・箱の争奪", "箱を奪われまいと、迷子のゴブリンが短剣を抜く。", [], enemy_ids=["goblin"], combat={"auto_start": False, "flee_allowed": False, "enemy_ids": ["goblin"], "victory_effects": {"inventory_add": [{"name": "縮小の銃", "quantity": 1}], "flags_set": ["stole_shrinking_gun"], "current_location": "forest_exit"}, "defeat_effects": {"hp_change": 1}}))
    return locations


def village_locations(pack: dict[str, Any]) -> list[dict[str, Any]]:
    locations: list[dict[str, Any]] = []

    cautious = action(
        "approach_burning_village_carefully", "慎重に村へ近づく", "炎と怪物の動きを見極めます", "1d20+int判定（DC15）",
        roll={"dice_type": "1d20+int", "dc": 15},
        success_effects=[{"current_location": "village_fire_slime"}, {"start_combat": True}],
        failure_effects=[{"current_location": "village_fire_elemental"}, {"start_combat": True}],
        critical_success_replaces_branch=True,
        critical_success_effects=[{"set_flag": "avoided_village_monsters"}, {"current_location": "village_frozen_clue"}],
        critical_failure_effects=[{"hp_change": -10}, {"set_flag": "burned_at_village_approach"}],
    )
    direct = action(
        "enter_burning_village_directly", "炎の中へ踏み込む", "怪物を退けて村へ入ります", "戦闘開始",
        effects=[{"current_location": "village_fire_elemental"}, {"start_combat": True}],
    )
    escape = action(
        "escape_from_burning_village", "直ちに逃げる", "Xanxusの名を思い出し、村から離れます", visible_after="heard_name_xanxus",
        effects=[{"current_location": "xanxus_confrontation"}],
    )
    locations.append(location(
        "village_approach", "炎上する麓の村・入口",
        "村は一面の火海となり、家々の間を怪物が徘徊している。生存者の姿は見当たらない。",
        [cautious, direct, escape],
        turns=[
            prepared("village_approach_success", cautious["id"], "炎の流れと怪物の配置を読み、比較的手薄な道を選んだ。しかし行く手には一匹のファイアスライムが待ち構えている。", "success"),
            prepared("village_approach_failure", cautious["id"], "炎の揺らぎに判断を乱され、火の精霊の縄張りへ踏み込んでしまった。燃え盛る人影がこちらを振り向く。", "failure"),
            prepared("village_approach_critical", cautious["id"], "炎と怪物の動きを完全に見切り、一度も気づかれず村の中心へ到達した。", "critical_success"),
            prepared("village_approach_fumble", cautious["id"], "崩れた屋根から炎が降り注ぎ、10点の炎ダメージを受けた。さらに火の精霊が退路を塞ぐ。", "critical_failure"),
            prepared("village_direct", direct["id"], "炎の中へ踏み込むと、火の精霊が燃える腕を広げて立ちはだかった。"),
            prepared("village_escape", escape["id"], "Xanxusの名が脳裏をよぎり、村から離れようとする。だがまだ遠くへ行かないうちに、赤い法衣と炎に包まれた骸骨が道を塞いだ。"),
        ],
    ))

    fire_result = {
        "victory": "炎の怪物を打ち倒すと、燃え盛る村の一角に不自然な氷が残っていることに気づいた。炎の中でも溶けず、冷気を放ち続けている。",
        "defeat": "炎の怪物に押し切られ、燃え落ちる村の中で力尽きた。",
    }
    locations.append(location(
        "village_fire_slime", "炎上する麓の村・ファイアスライム戦", "赤熱したスライムが燃える道を塞いでいる。", [],
        enemy_ids=["fire_slime"], combat={"auto_start": False, "flee_allowed": False, "enemy_ids": ["fire_slime"], "victory_effects": {"current_location": "village_frozen_clue"}, "defeat_effects": {"game_over": {"reason": "炎上する村でファイアスライムに敗れました。", "ending": "burning_village_defeat"}}, "result_texts": fire_result},
    ))
    locations.append(location(
        "village_fire_elemental", "炎上する麓の村・火の精霊戦", "火の精霊が炎上する家々から熱を吸い上げている。", [],
        enemy_ids=["fire_elemental"], combat={"auto_start": False, "flee_allowed": False, "enemy_ids": ["fire_elemental"], "victory_effects": {"current_location": "village_frozen_clue"}, "defeat_effects": {"game_over": {"reason": "炎上する村で火の精霊に敗れました。", "ending": "burning_village_defeat"}}, "result_texts": fire_result},
    ))

    impossible_actions = []
    for action_id, text, preview in (
        ("bluff_xanxus", "ごまかして切り抜ける", "何も察知していないふりをします"),
        ("ambush_xanxus", "先手を打って攻撃する", "Xanxusが動く前に仕掛けます"),
        ("flee_from_xanxus", "もう一度逃走を試みる", "全力でその場を離れます"),
    ):
        impossible_actions.append(action(
            action_id, text, preview, "不可能な判定（DC999）", roll={"dice_type": "1d20", "dc": 999},
            critical_enabled=False,
            failure_effects=[{"set_flag": "xanxus_encountered"}, {"current_location": "xanxus_battle"}, {"start_combat": True}],
        ))
    locations.append(location(
        "xanxus_confrontation", "燃える街道・Xanxusの尋問",
        "赤い法衣をまとい、全身を炎に包まれた骸骨の魔法使いXanxusが退路を塞いでいる。",
        impossible_actions, npc_ids=["xanxus"],
        turns=[
            prepared("xanxus_bluff_failed", "bluff_xanxus", "Xanxusは乾いた笑い声を上げた。『その目は何かを知った者の目だ。浅い嘘で私を欺けると思ったか』杖の一振りで炎の壁が街道を閉ざし、燃える骸骨は明確な殺意を向けて戦闘態勢に入る。", "failure"),
            prepared("xanxus_ambush_failed", "ambush_xanxus", "攻撃を放つより早く、Xanxusの炎が武器ごと身体を弾き返した。『先手を取ったつもりか？』着地点を炎の輪が囲み、Xanxusは陨石を呼ぶように片手を天へ掲げる。", "failure"),
            prepared("xanxus_escape_failed", "flee_from_xanxus", "一歩踏み出した瞬間、炎の壁が行く手を封じた。背後にも火柱が立ち、逃げ場は完全に消える。Xanxusは指先をこちらへ向け、『ならば力ずくで進ませよう』と戦いを強いる。", "failure"),
        ],
    ))
    locations.append(location(
        "xanxus_battle", "Xanxus戦", "Xanxusの炎が周囲を閉ざし、逃げ道を焼き払った。", [],
        enemy_ids=["xanxus"], combat={
            "auto_start": False, "boss": True, "flee_allowed": False, "enemy_ids": ["xanxus"],
            "victory_effects": {"flags_set": ["defeated_xanxus", "xanxus_encountered"], "current_location": "village_frozen_clue"},
            "defeat_effects": {"hp": 1, "flags_set": ["lost_to_xanxus", "xanxus_encountered"], "current_location": "xanxus_ultimatum"},
            "result_texts": {
                "victory": "Xanxusを包んでいた炎が次第に消えていく。骸骨は崩れ落ちながら、『まさか、お前は奇術師が化けていたのか……』と呟き、そのまま動かなくなった。",
                "defeat": "Xanxusは倒れたあなたを見下ろした。『大人しく先を探索しろ。そして私の火種を飲め。任務を放棄すれば、その場で爆ぜさせる』",
            },
        },
    ))

    submit = action(
        "accept_xanxus_fire_seed", "大人しく従う", "火種を受け取り、探索を続けます",
        effects=[{"add_item": {"name": "火種", "quantity": 1}}, {"set_flag": "accepted_fire_seed"}, {"current_location": "village_frozen_clue"}],
    )
    resist_saved = action(
        "refuse_xanxus_with_rescue", "死んでも従わない", "Xanxusの要求を拒絶します", visible_after="warlock_rescue_available",
        effects=[{"set_flag": "warlock_rescue_triggered"}, {"current_location": "warlock_rescue_battle"}, {"start_combat": True}],
    )
    resist_doom = action(
        "refuse_xanxus_without_rescue", "死んでも従わない", "Xanxusの要求を拒絶します", hidden_after="warlock_rescue_available",
        effects=[{"game_over": {"reason": "Xanxusの要求を拒み、その炎に焼き尽くされました。", "ending": "defied_xanxus"}}],
    )
    locations.append(location(
        "xanxus_ultimatum", "Xanxusの最後通告", "Xanxusは燃える火種を差し出し、服従を迫っている。",
        [submit, resist_saved, resist_doom], npc_ids=["xanxus"],
        turns=[
            prepared("accept_fire_seed", submit["id"], "火種を飲み込むと胸の奥へ焼ける感覚が沈んだ。炎への耐性を得た一方、氷と水に身体が強く反応する。火種は随時爆発しそうな様子をしている。"),
            prepared("warlock_rescue", resist_saved["id"], "Xanxusがとどめの炎を放とうとした瞬間、青い光が火線を切り裂いた。姿を消していたワーロックがあなたを背後へ庇う。『Xanxus、それは少しやり過ぎだ』青いローブの周囲に八属性の水晶球が展開し、二人の魔法使いの戦闘が始まる。"),
            prepared("xanxus_execution", resist_doom["id"], "Xanxusは一切の躊躇なく炎を解き放った。逃げ場はなく、視界は赤一色に染まった。"),
        ],
    ))

    locations.append(location(
        "warlock_rescue_battle", "ワーロック対Xanxus", "ワーロックがあなたを背後へ庇い、元素の水晶球を展開する。", [],
        npc_ids=["warlock", "xanxus"], enemy_ids=["xanxus"], combat={
            "auto_start": False, "boss": True, "flee_allowed": False, "disable_companion": True,
            "player_character_id": "warlock", "enemy_ids": ["xanxus"],
            "victory_effects": {"flags_set": ["warlock_defeated_xanxus", "xanxus_encountered"], "current_location": "village_frozen_clue"},
            "defeat_effects": {"game_over": {"reason": "Xanxusは『こんなに長くかかったが、ようやく一度お前に勝てた』と笑い、続けてプレイヤーを炎で貫きました。", "ending": "warlock_lost"}},
            "result_texts": {
                "victory": "Xanxusは頭を抱えて炎の彼方へ逃げ去った。ワーロックは、かつて元素・人類・竜が互いを害さない条約を結び、竜と人類は友好関係にあったと説明する。邪竜の暴走には誰かの思惑があり、多くの者が別々の狙いを抱えている。『くれぐれも用心してください。私は背後から見守っています』そう告げると、ワーロックは姿を消した。",
                "defeat": "Xanxusは天を仰いで笑った。『こんなに長くかかったが、ようやく一度お前に勝てた！』ワーロックを退けた炎は、そのまま背後のあなたを貫いた。",
            },
        },
    ))

    investigate = action("investigate_frozen_village", "結氷した場所を探索する", "炎の中に残る冷気を追います", effects=[{"current_location": "ice_elemental_encounter"}])
    skip_after_xanxus = action("skip_frozen_clue_after_xanxus", "探索せず先へ進む", "第4章へ向かいます", visible_after="xanxus_encountered", effects=[{"current_location": "dragon_valley_loc"}])
    skip_before_xanxus = action("skip_frozen_clue_before_xanxus", "探索せず先へ進む", "村を出ようとします", hidden_after="xanxus_encountered", effects=[{"current_location": "xanxus_confrontation"}])
    locations.append(location(
        "village_frozen_clue", "炎の中の結氷", "村の炎の一部だけが凍りつき、火と氷の境界が不自然に残されている。",
        [investigate, skip_after_xanxus, skip_before_xanxus],
        turns=[
            prepared("investigate_ice", investigate["id"], "凍結した道を辿ると、冷気が人の形を取り、氷の精霊となって行く手を塞いだ。"),
            prepared("skip_to_chapter_four", skip_after_xanxus["id"], "これ以上村に留まらず、邪竜を追って竜の谷へ向かう。"),
            prepared("skip_meets_xanxus", skip_before_xanxus["id"], "村を離れようとした街道で、赤い法衣と炎に包まれた骸骨の魔法使いが待ち受けていた。"),
        ],
    ))

    fight_ice = combat_start_action("fight_ice_elemental", "氷の精霊と戦う")
    bypass_ice = action(
        "bypass_ice_elemental", "氷の精霊を迂回する", "冷気の薄い経路を探します", "1d20+int判定（DC14）",
        roll={"dice_type": "1d20+int", "dc": 14},
        success_effects=[{"current_location": "frost_wolf_battle"}], failure_effects=[{"start_combat": True}],
    )
    locations.append(location(
        "ice_elemental_encounter", "凍結した村・氷の精霊", "氷の精霊が凍りついた路地を巡回している。",
        [fight_ice, bypass_ice], enemy_ids=["ice_elemental"], combat={
            "auto_start": False, "flee_allowed": True, "enemy_ids": ["ice_elemental"],
            "victory_effects": {"current_location": "frost_wolf_battle"},
            "defeat_effects": {"game_over": {"reason": "氷の精霊に凍結させられました。", "ending": "ice_elemental_defeat"}},
            "result_texts": {"victory": "氷の精霊が砕けると、奥から巨大な獣の足音が響いた。", "defeat": "氷の精霊の冷気に全身を閉ざされ、動けなくなった。"},
        }, turns=[
            prepared("fight_ice_elemental_intro", fight_ice["id"], "武器を構えて凍った路地へ踏み込むと、氷の精霊がこちらの熱を察知した。人の形をした冷気が鋭い氷片を周囲に浮かべ、正面から行く手を塞ぐ。"),
            prepared("bypass_ice_success", bypass_ice["id"], "冷気の流れを読み、氷の精霊に気づかれず奥の広場へ抜ける。だがそこで巨大な氷霜の狼がファイアスライムを前脚で叩き潰した。砕けた炎を踏み越え、次に冷たい眼があなたを捉える。", "success"),
            prepared("bypass_ice_failure", bypass_ice["id"], "凍った瓦礫を踏み割り、氷の精霊に発見された。", "failure"),
        ],
    ))

    locations.append(location(
        "frost_wolf_battle", "炎上する村・氷霜の巨狼", "氷霜の巨狼が現れ、傍らのファイアスライムを前脚の一撃で叩き潰した。次にその冷たい眼があなたを捉える。", [],
        enemy_ids=["frost_dire_wolf"], combat={
            "auto_start": True, "boss": True, "flee_allowed": False, "enemy_ids": ["frost_dire_wolf"],
            "victory_effects": {"flags_set": ["defeated_frost_dire_wolf"], "current_location": "ian_ice_katana_aftermath"},
            "defeat_effects": {"game_over": {"reason": "氷霜の巨狼に敗れ、村と共に凍りつきました。", "ending": "frost_wolf_defeat"}},
            "result_texts": {
                "victory": "氷霜の巨狼は霧のように消散し、その核だった氷の太刀が地面へ残った。拾おうとした瞬間、空から隕石が落ちて刀を砕く。遠くに全身を炎に包んだ影が一瞬だけ見えた。",
                "defeat": "氷霜の巨狼の牙が守りを砕き、村を覆う冷気の中で力尽きた。",
            },
        },
    ))

    accept_ian = action(
        "accept_ian_request", "イアンの頼みを受ける", "元凶を追う約束をし、武器を受け取ります",
        effects=[{"add_item": {"name": "氷鉄の大剣", "quantity": 1}}, {"set_flag": "accepted_ian_request"}, {"current_location": "dragon_valley_loc"}],
    )
    refuse_ian_after = action("refuse_ian_after_xanxus", "イアンの頼みを断る", "村を出て第4章へ進みます", visible_after="xanxus_encountered", effects=[{"current_location": "dragon_valley_loc"}])
    refuse_ian_before = action("refuse_ian_before_xanxus", "イアンの頼みを断る", "村を出ます", hidden_after="xanxus_encountered", effects=[{"current_location": "xanxus_confrontation"}])
    locations.append(location(
        "ian_ice_katana_aftermath", "砕けた氷の太刀", "店主イアンが現れ、凍死するほどの力が残る破片に触れないよう制止した。",
        [accept_ian, refuse_ian_after, refuse_ian_before], npc_ids=["ian"], item_ids=["ice_katana", "ice_iron_greatsword"],
        turns=[
            prepared("ian_request_accepted", accept_ian["id"], "イアンは、幼い頃に自分の故郷も同じように滅ぼされたと語る。『これを起こした元凶を止めてくれ。太刀は俺が打ち直す』約束を受けると、彼は破片から鍛えた氷鉄の大剣を差し出した。"),
            prepared("ian_request_refused_after", refuse_ian_after["id"], "イアンの頼みを断り、燃える村を後にして竜の谷へ向かった。"),
            prepared("ian_request_refused_before", refuse_ian_before["id"], "イアンの頼みを断って村を離れる。その先の街道で、赤い炎をまとった骸骨の魔法使いが待ち受けていた。"),
        ],
    ))
    return locations


def update_robin(pack: dict[str, Any]) -> None:
    inn = next((entry for entry in pack.get("locations", []) if entry.get("id") == "inn"), None)
    if not inn:
        return
    for top in inn.get("actions", []):
        for child in top.get("children", []) if isinstance(top, dict) else []:
            if child.get("id") == "invite_robin":
                effects = child.setdefault("success_effects", [])
                if {"set_companion": "robin"} not in effects:
                    effects.append({"set_companion": "robin"})
            if child.get("id") == "ask_robin_rumor":
                effects = child.setdefault("effects", [])
                if {"set_flag": "heard_robin_night_rumor"} not in effects:
                    effects.append({"set_flag": "heard_robin_night_rumor"})
    turns = inn.setdefault("hybrid", {}).setdefault("prepared_turns", [])
    for turn in turns:
        if turn.get("action_id") == "ask_robin_rumor":
            turn.setdefault("draft", {})["gm_text"] = "ロビンは声を落とした。「王城の路地裏には、夜だけ現れる黒い商人がいるそうよ。昼に行っても何も見つからないわ」"


def update_castle_departure(pack: dict[str, Any]) -> None:
    castle = next((entry for entry in pack.get("locations", []) if entry.get("id") == "castle"), None)
    if not castle:
        return
    turns = castle.setdefault("hybrid", {}).setdefault("prepared_turns", [])
    turns[:] = [turn for turn in turns if turn.get("action_id") != "go_dark_forest"]
    turns.extend([
        prepared(
            "castle_departure_success",
            "go_dark_forest",
            "城門を抜けると石畳は次第に細い獣道へ変わり、湿った土と苔の匂いが濃くなっていく。やがて木々が陽光を遮り、闇の森の入口で青いスライムが進路を塞いだ。",
            "success",
        ),
        prepared(
            "castle_departure_failure",
            "go_dark_forest",
            "城門を出たところで装備の留め具が外れ、森へ入る前に引き返すことになった。支度を整え直せば、もう一度出発できる。",
            "failure",
        ),
    ])


def update_forge(pack: dict[str, Any]) -> None:
    forge = next((entry for entry in pack.get("locations", []) if entry.get("id") == "forge"), None)
    if not forge:
        return
    activate = action(
        "activate_ice_charm",
        "氷の護符を武器へ嵌め込み活性化する",
        "通常攻撃に1d8+INT/2の氷属性追撃を加えます",
        hidden_for_character="hero",
        once="activated_ice_charm",
        requirements={
            "all": [
                {"has_item": "氷の護符"},
                {"lacks_item": "氷の護符(活性化済)"},
            ],
        },
        effects=[
            {"remove_item": {"name": "氷の護符", "quantity": 1}},
            {"add_item": {"name": "氷の護符(活性化済)", "quantity": 1}},
            {"equip_item": "氷の護符(活性化済)"},
            {"set_flag": "activated_ice_charm"},
        ],
    )
    actions = [entry for entry in forge.get("actions", []) if entry.get("id") != activate["id"]]
    insert_at = next(
        (index for index, entry in enumerate(actions) if entry.get("id") == "return_castle_from_forge"),
        len(actions),
    )
    actions.insert(insert_at, activate)
    forge["actions"] = actions
    turns = forge.setdefault("hybrid", {}).setdefault("prepared_turns", [])
    turns[:] = [turn for turn in turns if turn.get("action_id") != activate["id"]]
    turns.append(prepared(
        "activate_ice_charm_at_forge",
        activate["id"],
        "ローベルトは武器の柄へ氷の護符を嵌め込み、槌で魔力の流れを整えた。青白い光が刃を走る。「活性化は済んだ。これからは斬撃のたびに冷気が追い打ちをかける」",
    ))


def upgrade(pack: dict[str, Any]) -> dict[str, Any]:
    meta = pack.setdefault("meta", {})
    meta["title"] = "紅き邪竜イグニス"
    add_catalog(pack)
    add_village_catalog(pack)
    update_robin(pack)
    update_castle_departure(pack)
    update_forge(pack)
    replacements = {entry["id"]: entry for entry in [*town_locations(pack), *forest_locations(pack), *fort_locations(pack), *village_locations(pack)]}
    retained = [entry for entry in pack.get("locations", []) if entry.get("id") not in replacements and entry.get("id") != "village_shop"]
    pack["locations"] = [*retained, *replacements.values()]
    forest_scene = next((scene for scene in pack.get("scenes", []) if scene.get("id") == "dark_forest"), None)
    if forest_scene:
        forest_scene["description"] = "スライム、迷子のゴブリン、精霊の泉、四階建てのゴブリン砦を巡る分岐章。"
        forest_scene["goals"] = ["闇の森を突破する", "迷子のゴブリンの依頼を解決する", "ゴブリン砦または精霊の泉の危機を乗り越える"]
        forest_scene["location_ids"] = [entry_id for entry_id in replacements if entry_id.startswith(("dark_", "forest_", "elf_", "lost_", "goblin_"))]
    village_scene = next((scene for scene in pack.get("scenes", []) if scene.get("id") == "village"), None)
    if village_scene:
        village_scene["title"] = "第3章：炎上する麓の村"
        village_scene["description"] = "火海となった村でXanxusの陰謀と氷の太刀の痕跡を追う分岐章。"
        village_scene["goals"] = ["炎の怪物を突破する", "Xanxusとの遭遇を生き延びる", "氷霜の巨狼と砕けた氷の太刀の真相を追う"]
        village_scene["location_ids"] = [entry_id for entry_id in replacements if entry_id.startswith(("village", "xanxus", "warlock", "ice_", "frost_", "ian_"))]
        village_scene["actions"] = []
        village_scene.pop("hybrid", None)
    apply_visual_assets(pack)
    meta["content_revision"] = "2026-08-14-story-and-visuals"
    return pack


def align_runtime_data(base: dict[str, Any], hybrid: dict[str, Any]) -> None:
    fields_by_section = {
        "locations": ("enemy_ids", "combat"),
        "enemies": ("hp", "max_hp", "combat", "resistances", "rewards", "skills"),
        "characters": ("combat", "skills", "inventory", "equipment"),
        "items": ("combat",),
    }
    for section, fields in fields_by_section.items():
        base_records = {record.get("id"): record for record in base.get(section, []) if record.get("id")}
        hybrid_records = {record.get("id"): record for record in hybrid.get(section, []) if record.get("id")}
        for record_id, base_record in base_records.items():
            hybrid_record = hybrid_records.get(record_id)
            if not hybrid_record:
                continue
            for field in fields:
                if field in base_record:
                    hybrid_record[field] = deepcopy(base_record[field])
                else:
                    hybrid_record.pop(field, None)
    hybrid["combat_rules"] = deepcopy(base.get("combat_rules", {}))


def main() -> None:
    packs = [upgrade(json.loads(path.read_text(encoding="utf-8-sig"))) for path in SCENARIOS]
    align_runtime_data(packs[0], packs[1])
    for path, pack in zip(SCENARIOS, packs):
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"updated {path.name}")


if __name__ == "__main__":
    main()
