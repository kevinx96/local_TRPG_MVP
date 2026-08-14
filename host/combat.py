from __future__ import annotations

import random
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional

from .item_mechanics import (
    equipped_basic_attack_followups,
    effective_ability,
    effective_ability_cost,
    item_combat_spec,
    item_is_combat_usable,
    structured_item_effect,
)
from .scenario_context import find_scene
from .world_state import current_location_id, current_scene_id


DEFAULT_COMBAT_RULES: dict[str, Any] = {
    "basic_attack": {
        "name": "通常攻撃",
        "damage": "1d6+str/4",
        "accuracy": 90,
        "element": "physical",
    },
    "enemy_basic_attack": {
        "name": "攻撃",
        "damage": "1d4+str/4",
        "accuracy": 85,
        "element": "physical",
    },
    "defend_multiplier": 0.5,
    "flee_formula": "1d20+dex/2",
    "flee_dc": 12,
    "sp_regen_per_round": 1,
    "max_rounds": 100,
}


class CombatError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def combat_is_active(session: dict[str, Any]) -> bool:
    combat = session.get("combat")
    return isinstance(combat, dict) and combat.get("status") == "active"


def combat_needs_resolution(session: dict[str, Any]) -> bool:
    combat = session.get("combat")
    return bool(isinstance(combat, dict) and combat.get("pending_resolution"))


def ensure_combat_started(session: dict[str, Any]) -> bool:
    existing = session.get("combat")
    if isinstance(existing, dict) and existing.get("status"):
        return False

    location_id = current_location_id(session)
    start_requested = bool(session.get("combat_start_requested"))
    blocked_location = str(session.get("combat_blocked_location") or "")
    if blocked_location and blocked_location != location_id:
        session.pop("combat_blocked_location", None)
    elif blocked_location and blocked_location == location_id and not start_requested:
        return False
    elif blocked_location and start_requested:
        session.pop("combat_blocked_location", None)

    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return False
    encounter = _encounter_for_session(session, pack)
    if encounter.get("auto_start", True) is False and not start_requested:
        return False
    enemy_ids = encounter.get("enemy_ids") or []
    defeated = session.get("flags") if isinstance(session.get("flags"), dict) else {}
    enemy_catalog = {
        str(enemy.get("id") or ""): enemy
        for enemy in pack.get("enemies", [])
        if isinstance(enemy, dict) and str(enemy.get("id") or "")
    }
    enemy_templates = [
        enemy_catalog[enemy_id]
        for enemy_id in enemy_ids
        if enemy_id in enemy_catalog and not defeated.get(_defeated_flag(enemy_id, location_id))
    ]
    if not enemy_templates:
        if start_requested:
            session.pop("combat_start_requested", None)
        return False

    original_character = None
    player_character_id = str(encounter.get("player_character_id") or "").strip()
    if player_character_id:
        player_template = next(
            (
                character for character in pack.get("characters", [])
                if isinstance(character, dict) and str(character.get("id") or "") == player_character_id
            ),
            None,
        )
        if player_template:
            original_character = deepcopy(session.get("character", {}))
            session["character"] = _runtime_player_character(player_template)

    enemies = [_runtime_enemy(enemy, index) for index, enemy in enumerate(enemy_templates)]
    session["combat"] = {
        "id": uuid.uuid4().hex,
        "status": "active",
        "round": 1,
        "turn": "player",
        "location_id": location_id,
        "scene_id": current_scene_id(session),
        "enemies": enemies,
        "log": [],
        "player_status": {},
        "actions_remaining": _player_actions_per_round(session),
        "encounter": deepcopy(encounter),
        "pending_resolution": False,
        "result": None,
        "created_at": utc_now(),
        "event_cursor": len(session.get("event_log") or []),
    }
    if original_character is not None:
        session["combat"]["original_character"] = original_character
    session["choices"] = []
    session.pop("combat_start_requested", None)
    _log(session, "system", "start", f"戦闘開始: {'、'.join(enemy['name'] for enemy in enemies)}")
    _apply_round_start_effects(session, random)
    _check_victory_or_defeat(session)
    return True


def perform_combat_action(
    session: dict[str, Any],
    action_type: str,
    action_id: str = "",
    target_id: str = "",
    rng: Optional[random.Random] = None,
) -> dict[str, Any]:
    combat = session.get("combat")
    if not isinstance(combat, dict) or combat.get("status") != "active":
        raise CombatError("戦闘中ではありません。")
    if combat.get("turn") != "player":
        raise CombatError("現在はプレイヤーの手番ではありません。")

    random_source = rng or random
    normalized_type = str(action_type or "").strip().lower()
    if normalized_type not in {"attack", "skill", "item", "defend", "flee"}:
        raise CombatError("不明な戦闘行動です。")

    before_index = len(combat.get("log") or [])
    if normalized_type == "attack":
        _player_attack(session, target_id, random_source)
    elif normalized_type == "skill":
        _player_skill(session, action_id, target_id, random_source)
    elif normalized_type == "item":
        _player_item(session, action_id, target_id, random_source)
    elif normalized_type == "defend":
        _player_defend(session)
    else:
        _player_flee(session, random_source)

    if combat.get("status") == "active":
        _check_victory_or_defeat(session)
    if combat.get("status") == "active":
        combat["actions_remaining"] = max(0, _safe_int(combat.get("actions_remaining"), 1) - 1)
    player_continues = combat.get("status") == "active" and _safe_int(combat.get("actions_remaining"), 0) > 0
    if combat.get("status") == "active" and not player_continues:
        _enemy_phase(session, random_source)
    if combat.get("status") == "active" and not player_continues:
        _check_victory_or_defeat(session)
    if combat.get("status") == "active" and not player_continues:
        combat["round"] = int(combat.get("round", 1)) + 1
        combat["turn"] = "player"
        combat["actions_remaining"] = _player_actions_per_round(session)
        _regenerate_round_resources(session)
        _apply_round_start_effects(session, random_source)
        _check_victory_or_defeat(session)
        max_rounds = int(_combat_rules(session).get("max_rounds", 100) or 100)
        if int(combat["round"]) > max_rounds:
            _finish_combat(session, "defeat", "長期戦に耐えきれず敗北した。")

    events = deepcopy((combat.get("log") or [])[before_index:])
    return {
        "status": combat.get("status"),
        "round": combat.get("round"),
        "events": events,
        "pending_resolution": bool(combat.get("pending_resolution")),
    }


def consume_combat_state_delta(session: dict[str, Any]) -> dict[str, Any]:
    combat = session.get("combat")
    if not isinstance(combat, dict):
        return {}
    delta = combat.pop("pending_state_delta", {})
    return deepcopy(delta) if isinstance(delta, dict) else {}


def combat_result_for_llm(session: dict[str, Any]) -> dict[str, Any]:
    combat = session.get("combat")
    if not isinstance(combat, dict) or not combat.get("pending_resolution"):
        raise CombatError("LLMへ渡す戦闘結果がありません。")
    result = combat.get("result")
    if not isinstance(result, dict):
        raise CombatError("戦闘結果が不正です。")
    resolved = deepcopy(result)
    resolved.pop("rewards", None)
    character = session.get("character") if isinstance(session.get("character"), dict) else {}
    resolved["player"] = {
        "name": character.get("name"),
        "hp": character.get("hp"),
        "max_hp": character.get("max_hp"),
        "mp": character.get("mp"),
        "max_mp": character.get("max_mp"),
        "sp": character.get("sp"),
        "max_sp": character.get("max_sp"),
        "gold": character.get("gold", 0),
        "inventory": [
            {
                "name": str(item.get("name") or ""),
                "quantity": _safe_int(item.get("quantity"), 1),
            }
            for item in character.get("inventory", [])
            if isinstance(item, dict) and str(item.get("name") or "")
        ],
    }
    cursor = max(0, _safe_int(combat.get("event_cursor"), 0))
    resolved["committed_events"] = [
        {
            "kind": str(event.get("kind") or ""),
            "text": str(event.get("text") or ""),
            "data": deepcopy(event.get("data") if isinstance(event.get("data"), dict) else {}),
        }
        for event in (session.get("event_log") or [])[cursor:]
        if isinstance(event, dict)
    ]
    return resolved


def clear_combat_after_resolution(session: dict[str, Any]) -> dict[str, Any]:
    combat = session.get("combat")
    if not isinstance(combat, dict):
        return {}
    result = deepcopy(combat.get("result") or {})
    status = str(combat.get("status") or "")
    location_id = str(combat.get("location_id") or current_location_id(session))
    if status in {"fled", "defeat"} and location_id:
        session["combat_blocked_location"] = location_id
    if isinstance(session.get("character"), dict):
        session["character"].pop("combat_immunities", None)
    original_character = combat.get("original_character")
    if isinstance(original_character, dict):
        session["character"] = deepcopy(original_character)
    session["last_combat_result"] = result
    session["combat"] = None
    return result


def public_combat(session: dict[str, Any]) -> Optional[dict[str, Any]]:
    combat = session.get("combat")
    if not isinstance(combat, dict) or not combat.get("status"):
        return None
    public = {
        "id": combat.get("id"),
        "status": combat.get("status"),
        "round": combat.get("round"),
        "turn": combat.get("turn"),
        "enemies": deepcopy(combat.get("enemies") or []),
        "log": deepcopy((combat.get("log") or [])[-40:]),
        "pending_resolution": bool(combat.get("pending_resolution")),
        "result": deepcopy(combat.get("result")),
        "actions": [],
    }
    if combat.get("status") == "active":
        public["actions"] = combat_actions(session)
    return public


def combat_actions(session: dict[str, Any]) -> list[dict[str, Any]]:
    character = session.get("character") if isinstance(session.get("character"), dict) else {}
    rules = _combat_rules(session)
    basic = _merge_dict(rules.get("basic_attack"), character.get("combat", {}).get("basic_attack") if isinstance(character.get("combat"), dict) else None)
    basic = _merge_dict(basic, _equipped_weapon_attack(character))
    basic_followups = equipped_basic_attack_followups(character)
    actions: list[dict[str, Any]] = [
        {
            "type": "attack",
            "id": "basic_attack",
            "name": str(basic.get("name") or "通常攻撃"),
            "description": str(basic.get("description") or "装備中の武器で攻撃する。"),
            "cost": 0,
            "cost_type": "",
            "enabled": True,
            **_combat_action_details(basic),
            **({"followups": basic_followups} if basic_followups else {}),
        }
    ]
    for index, skill in enumerate(_available_skills(character)):
        if not isinstance(skill, dict):
            continue
        skill_id = _entry_id(skill, "skill", index)
        cost = effective_ability_cost(character, skill)
        cost_type = str(skill.get("cost_type") or "").lower()
        available = _safe_int(character.get(cost_type), 0) if cost_type in {"mp", "sp", "hp"} else cost
        enabled = available >= cost
        resolved_skill = effective_ability(character, skill)
        actions.append({
            "type": "skill",
            "id": skill_id,
            "name": str(skill.get("name") or skill_id),
            "description": str(skill.get("description") or skill.get("effect") or ""),
            "cost": cost,
            "cost_type": cost_type,
            "kind": _ability_kind(skill),
            "enabled": enabled,
            "disabled_reason": "リソースが不足しています。" if not enabled else "",
            **_combat_action_details(resolved_skill),
        })
    for index, item in enumerate(character.get("inventory") or []):
        normalized = item if isinstance(item, dict) else {"name": str(item), "quantity": 1}
        spec = item_combat_spec(normalized)
        if not item_is_combat_usable(normalized) or _safe_int(normalized.get("quantity"), 1) <= 0:
            continue
        item_id = _entry_id(normalized, "item", index)
        actions.append({
            "type": "item",
            "id": item_id,
            "name": str(normalized.get("name") or item_id),
            "description": structured_item_effect(normalized),
            "quantity": _safe_int(normalized.get("quantity"), 1),
            "kind": spec.get("kind"),
            "enabled": True,
            **_combat_action_details(spec),
        })
    actions.extend([
        {
            "type": "defend",
            "id": "defend",
            "name": "防御",
            "description": "次の敵フェーズに受けるダメージを軽減する。",
            "enabled": True,
        },
        {
            "type": "flee",
            "id": "flee",
            "name": "逃走",
            "description": "敏捷を使って戦闘から離脱する。",
            "enabled": bool((session.get("combat") or {}).get("encounter", {}).get("flee_allowed", True)),
            "disabled_reason": "この戦闘からは逃走できません。" if not (session.get("combat") or {}).get("encounter", {}).get("flee_allowed", True) else "",
        },
    ])
    return actions


def _combat_action_details(ability: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "damage", "healing", "accuracy", "element", "all_targets", "check",
        "guard_multiplier", "multi_elements", "hits_per_element",
    )
    return {key: deepcopy(ability[key]) for key in fields if ability.get(key) not in (None, "", [], {})}


def _player_attack(session: dict[str, Any], target_id: str, rng: Any) -> None:
    combat = session["combat"]
    character = session["character"]
    target = _target_enemy(combat, target_id)
    rules = _combat_rules(session)
    char_combat = character.get("combat") if isinstance(character.get("combat"), dict) else {}
    attack = _merge_dict(rules.get("basic_attack"), char_combat.get("basic_attack"))
    attack = _merge_dict(attack, _equipped_weapon_attack(character))
    _resolve_attack(session, character, target, attack, "player", rng)
    for followup in equipped_basic_attack_followups(character):
        if _enemy_is_defeated(target):
            break
        _resolve_attack(session, character, target, followup, "player", rng)


def _player_skill(session: dict[str, Any], skill_id: str, target_id: str, rng: Any) -> None:
    character = session["character"]
    skill = _find_entry(_available_skills(character), skill_id, "skill")
    if not skill:
        raise CombatError("技能が見つかりません。")
    resolved_skill = effective_ability(character, skill)
    _pay_cost(character, resolved_skill)
    check = resolved_skill.get("check") if isinstance(resolved_skill.get("check"), dict) else {}
    if check:
        total, detail = _roll_formula(str(check.get("formula") or "1d20+int"), character, rng)
        dc = _safe_int(check.get("dc"), 15)
        succeeded = total >= dc
        _log(session, "player", "check", f"{resolved_skill.get('name', '技能')}の判定 {total} / DC{dc}: {'成功' if succeeded else '失敗'}。", {"total": total, "dc": dc, "formula": detail})
        if not succeeded and check.get("failure_effect") == "undead_conversion":
            _apply_undead_conversion(session, "player")
            if session.get("game_over"):
                return
    kind = _ability_kind(resolved_skill)
    if kind == "heal":
        amount, detail = _roll_formula(str(resolved_skill.get("healing") or resolved_skill.get("dice_type") or "1d6+int/4"), character, rng)
        amount = max(0, int(round(amount * float(resolved_skill.get("healing_multiplier", 1) or 1))))
        if _equipped_effect(character, "healing_harms_humans") and not character.get("undead_parts"):
            character["hp"] = max(0, _safe_int(character.get("hp"), 0) - amount)
            _log(session, "player", "self_damage", f"呪われた治癒でHPを{amount}失った。", {"amount": amount, "formula": detail})
        else:
            healed = _heal_actor(character, amount)
            _log(session, "player", "heal", f"{resolved_skill.get('name', '技能')}でHPを{healed}回復した。", {"amount": healed, "formula": detail})
    elif kind == "defend":
        multiplier = float(resolved_skill.get("guard_multiplier", _combat_rules(session).get("defend_multiplier", 0.5)) or 0.5)
        session["combat"].setdefault("player_status", {})["guard_multiplier"] = max(0.0, min(1.0, multiplier))
        session["combat"]["player_status"]["survive_at_one"] = bool(resolved_skill.get("survive_at_one", True))
        _log(session, "player", "defend", f"{resolved_skill.get('name', '防御技能')}を使用し、守りを固めた。")
    elif kind == "stance":
        target = _target_enemy(session["combat"], target_id)
        if resolved_skill.get("immunity_from_target_element"):
            element = _primary_element(target)
            character["combat_immunities"] = [element]
            _log(session, "player", "stance", f"{resolved_skill.get('name', '構え')}で{element}属性を無効化した。", {"element": element})
    else:
        multi_elements = resolved_skill.get("multi_elements")
        if isinstance(multi_elements, list) and multi_elements:
            target = _target_enemy(session["combat"], target_id)
            hits = max(1, _safe_int(resolved_skill.get("hits_per_element"), 1))
            for element in multi_elements:
                for _ in range(hits):
                    if _enemy_is_defeated(target):
                        break
                    strike = deepcopy(resolved_skill)
                    strike["element"] = str(element)
                    _resolve_attack(session, character, target, strike, "player", rng, f"{resolved_skill.get('name')}・{element}")
                if _enemy_is_defeated(target):
                    break
        elif resolved_skill.get("all_targets"):
            for target in list(_alive_enemies(session["combat"])):
                _resolve_attack(session, character, target, resolved_skill, "player", rng)
        else:
            target = _target_enemy(session["combat"], target_id)
            _resolve_attack(session, character, target, resolved_skill, "player", rng)


def _player_item(session: dict[str, Any], item_id: str, target_id: str, rng: Any) -> None:
    character = session["character"]
    inventory = character.get("inventory") if isinstance(character.get("inventory"), list) else []
    item = _find_entry(inventory, item_id, "item")
    if not item:
        raise CombatError("道具が見つかりません。")
    spec = item_combat_spec(item)
    if not item_is_combat_usable(item):
        raise CombatError("この道具は戦闘中に使用できません。")
    kind = str(spec.get("kind") or "heal")
    if kind == "heal":
        amount, detail = _roll_formula(str(spec.get("healing") or spec.get("formula") or "10"), character, rng)
        healed = _heal_actor(character, amount)
        _log(session, "player", "item", f"{item.get('name', '道具')}を使い、HPを{healed}回復した。", {"amount": healed, "formula": detail})
    elif kind == "restore":
        resource = str(spec.get("resource") or "mp").lower()
        if resource not in {"hp", "mp", "sp"}:
            raise CombatError("未対応の回復対象です。")
        amount, detail = _roll_formula(str(spec.get("amount") or spec.get("formula") or "10"), character, rng)
        restored = _restore_actor_resource(character, resource, amount)
        _log(
            session,
            "player",
            "item",
            f"{item.get('name', '道具')}を使い、{resource.upper()}を{restored}回復した。",
            {"resource": resource, "amount": restored, "formula": detail},
        )
    elif kind == "damage":
        target = _target_enemy(session["combat"], target_id)
        _resolve_attack(session, character, target, spec, "player", rng, display_name=str(item.get("name") or "道具"))
    elif kind == "flee":
        encounter = session["combat"].get("encounter") or {}
        if encounter.get("boss") or not encounter.get("flee_allowed", True):
            raise CombatError("この戦闘では煙幕を使って逃走できません。")
        _log(session, "player", "flee", f"{item.get('name', '道具')}を使って戦闘から離脱した。")
        _finish_combat(session, "fled", "戦闘から離脱した。")
    elif kind == "shrink":
        target = _target_enemy(session["combat"], target_id)
        chance = max(1, min(100, _safe_int(spec.get("chance"), 2)))
        roll = rng.randint(1, 100)
        if roll <= chance:
            target["max_hp"] = max(1, int(abs(_safe_int(target.get("max_hp"), 1))) // 10)
            if _negative_undead(target):
                target["hp"] = min(-1, _safe_int(target.get("hp"), -1) // 10)
            else:
                target["hp"] = max(1, _safe_int(target.get("hp"), 1) // 10)
            _log(session, "player", "status", f"{target.get('name', '敵')}が縮小した。", {"roll": roll, "chance": chance})
        else:
            _log(session, "player", "miss", f"{item.get('name', '道具')}は効かなかった。", {"roll": roll, "chance": chance})
    else:
        raise CombatError("未対応の道具効果です。")
    if spec.get("consumable", True):
        _consume_inventory_item(character, item)


def _player_defend(session: dict[str, Any]) -> None:
    multiplier = float(_combat_rules(session).get("defend_multiplier", 0.5) or 0.5)
    session["combat"].setdefault("player_status", {})["guard_multiplier"] = max(0.0, min(1.0, multiplier))
    _log(session, "player", "defend", "防御態勢を取り、次の攻撃に備えた。")


def _player_flee(session: dict[str, Any], rng: Any) -> None:
    encounter = session["combat"].get("encounter") or {}
    if not encounter.get("flee_allowed", True):
        raise CombatError("この戦闘からは逃走できません。")
    rules = _combat_rules(session)
    formula = str(encounter.get("flee_formula") or rules.get("flee_formula") or "1d20+dex/2")
    dc = _safe_int(encounter.get("flee_dc"), _safe_int(rules.get("flee_dc"), 12))
    total, detail = _roll_formula(formula, session["character"], rng)
    if total >= dc:
        _log(session, "player", "flee", f"逃走判定 {total} / DC{dc}: 成功。", {"total": total, "dc": dc, "formula": detail})
        _finish_combat(session, "fled", "戦闘から離脱した。")
    else:
        _log(session, "player", "flee", f"逃走判定 {total} / DC{dc}: 失敗。", {"total": total, "dc": dc, "formula": detail})


def _enemy_phase(session: dict[str, Any], rng: Any) -> None:
    combat = session["combat"]
    combat["turn"] = "enemy"
    for enemy in combat.get("enemies") or []:
        if _enemy_is_defeated(enemy) or _safe_int(session["character"].get("hp"), 0) <= 0:
            continue
        ability = _choose_enemy_ability(enemy, session, rng)
        _pay_cost(enemy, ability)
        _execute_enemy_ability(session, enemy, ability, rng)
        if session.get("game_over"):
            break
    combat["player_status"] = {}


def _execute_enemy_ability(session: dict[str, Any], enemy: dict[str, Any], ability: dict[str, Any], rng: Any) -> None:
    actor_id = str(enemy.get("id") or "enemy")
    kind = _ability_kind(ability)
    if kind == "heal":
        amount, detail = _roll_formula(str(ability.get("healing") or ability.get("dice_type") or "1d4"), enemy, rng)
        threshold = ability.get("healing_multiplier_below_hp_ratio")
        if isinstance(threshold, (int, float)) and _hp_ratio(enemy) <= float(threshold):
            amount = int(round(amount * float(ability.get("low_hp_multiplier", 2) or 2)))
        healed = _heal_actor(enemy, amount)
        _log(session, actor_id, "heal", f"{enemy.get('name')}は{ability.get('name')}でHPを{healed}回復した。", {"amount": healed, "formula": detail})
    elif kind == "field":
        field = {
            "id": str(ability.get("id") or ability.get("name") or "field"),
            "name": str(ability.get("name") or "領域"),
            "source_id": actor_id,
            "damage": str(ability.get("round_damage") or ability.get("damage") or "1"),
            "element": str(ability.get("element") or "physical"),
        }
        session["combat"].setdefault("fields", []).append(field)
        _log(session, actor_id, "field", f"{enemy.get('name')}は{field['name']}を展開した。", field)
    elif kind == "status" and ability.get("status_effect") == "undead_conversion":
        _apply_undead_conversion(session, actor_id)
    else:
        _resolve_attack(session, enemy, session["character"], ability, actor_id, rng)


def _apply_enemy_fields(session: dict[str, Any], rng: Any) -> None:
    combat = session.get("combat")
    if not isinstance(combat, dict):
        return
    enemies = combat.get("enemies") or []
    for field in combat.get("fields") or []:
        if not isinstance(field, dict):
            continue
        source = next((enemy for enemy in enemies if str(enemy.get("id") or "") == str(field.get("source_id") or "")), None)
        if not isinstance(source, dict) or _enemy_is_defeated(source):
            continue
        _apply_direct_formula_damage(
            session,
            source,
            session["character"],
            str(field.get("damage") or "1"),
            str(field.get("element") or "physical"),
            str(field.get("name") or "領域"),
            rng,
        )
        if _safe_int(session["character"].get("hp"), 0) <= 0:
            break


def _apply_direct_formula_damage(
    session: dict[str, Any],
    attacker: dict[str, Any],
    defender: dict[str, Any],
    formula: str,
    element: str,
    name: str,
    rng: Any,
) -> None:
    raw_damage, detail = _roll_formula(formula, attacker, rng)
    multiplier = _resistance_multiplier(defender, element)
    damage = max(0, int(round(max(0, raw_damage) * multiplier)))
    defender["hp"] = max(0, _safe_int(defender.get("hp"), 0) - damage)
    _log(session, str(attacker.get("id") or "enemy"), "field_damage", f"{name}が{damage}ダメージを与えた。", {"damage": damage, "formula": detail, "element": element})


def _trigger_enemy_auto_abilities(session: dict[str, Any], enemy: dict[str, Any], rng: Any) -> None:
    triggered = enemy.setdefault("auto_triggered", [])
    for skill in enemy.get("skills") or []:
        if not isinstance(skill, dict) or not isinstance(skill.get("auto_trigger_below_hp_ratio"), (int, float)):
            continue
        skill_id = str(skill.get("id") or skill.get("name") or "auto")
        if skill_id in triggered or _hp_ratio(enemy) > float(skill["auto_trigger_below_hp_ratio"]):
            continue
        triggered.append(skill_id)
        _execute_enemy_ability(session, enemy, skill, rng)


def _field_is_active(session: dict[str, Any], enemy: dict[str, Any], ability: dict[str, Any]) -> bool:
    wanted = str(ability.get("id") or ability.get("name") or "field")
    source_id = str(enemy.get("id") or "")
    return any(
        isinstance(field, dict)
        and str(field.get("id") or "") == wanted
        and str(field.get("source_id") or "") == source_id
        for field in (session.get("combat") or {}).get("fields") or []
    )


def _hp_ratio(actor: dict[str, Any]) -> float:
    maximum = max(1, _safe_int(actor.get("max_hp"), 1))
    return _safe_int(actor.get("hp"), 0) / maximum


def _resolve_attack(
    session: dict[str, Any],
    attacker: dict[str, Any],
    defender: dict[str, Any],
    ability: dict[str, Any],
    actor_id: str,
    rng: Any,
    display_name: str = "",
) -> None:
    name = display_name or str(ability.get("name") or "攻撃")
    accuracy = _safe_int(ability.get("accuracy"), 90 if actor_id == "player" else 85)
    evade = _safe_int((defender.get("combat") or {}).get("evade") if isinstance(defender.get("combat"), dict) else defender.get("evade"), 0)
    chance = max(5, min(100, accuracy - evade))
    hit_roll = rng.randint(1, 100)
    defender_name = str(defender.get("name") or "敵")
    if hit_roll > chance:
        _log(session, actor_id, "miss", f"{name}は{defender_name}に当たらなかった。", {"roll": hit_roll, "chance": chance})
        return

    formula = str(ability.get("damage") or ability.get("dice_type") or "1d4")
    raw_damage, detail = _roll_formula(formula, attacker, rng)
    raw_damage = max(0, int(round(raw_damage * float(ability.get("damage_multiplier", 1) or 1))))
    element = str(ability.get("element") or "physical")
    if element == "counter":
        element = _counter_element(_primary_element(defender))
    multiplier = _resistance_multiplier(defender, element)
    defense = _actor_defense(defender)
    damage = 0 if multiplier <= 0 else max(1, int(round(raw_damage * multiplier)) - defense)
    if defender is session.get("character"):
        status = session["combat"].get("player_status") or {}
        guard = float(status.get("guard_multiplier", 1.0) or 1.0)
        damage = max(0, int(round(damage * guard)))
    before_hp = _safe_int(defender.get("hp"), 0)
    if _negative_undead(defender):
        if element.lower() in {"holy", "light"} or ability.get("heals_negative_undead"):
            after_hp = before_hp + damage
        else:
            after_hp = before_hp - damage
    else:
        after_hp = max(0, before_hp - damage)
    if defender is session.get("character"):
        status = session["combat"].get("player_status") or {}
        if status.get("survive_at_one") and before_hp > 1 and after_hp <= 0:
            after_hp = 1
            damage = before_hp - 1
    defender["hp"] = after_hp
    _log(
        session,
        actor_id,
        "damage",
        f"{name}が{defender_name}に{damage}ダメージ。",
        {"damage": damage, "raw_damage": raw_damage, "formula": detail, "element": element, "hit_roll": hit_roll, "hit_chance": chance},
    )
    status_spec = ability.get("on_hit_status")
    if isinstance(status_spec, dict) and damage > 0:
        _apply_status(defender, status_spec)
        _log(
            session,
            actor_id,
            "status",
            f"{defender_name}は{status_spec.get('name') or status_spec.get('id') or '状態異常'}を受けた。",
            {"status": deepcopy(status_spec)},
        )
    self_damage = max(0, _safe_int(ability.get("self_damage"), 0))
    if self_damage and attacker is session.get("character"):
        attacker["hp"] = max(0, _safe_int(attacker.get("hp"), 0) - self_damage)
        _log(session, actor_id, "self_damage", f"反動でHPを{self_damage}失った。", {"damage": self_damage})
    if defender is not session.get("character") and damage > 0:
        _trigger_enemy_auto_abilities(session, defender, rng)


def _check_victory_or_defeat(session: dict[str, Any]) -> None:
    combat = session["combat"]
    if _safe_int(session["character"].get("hp"), 0) <= 0:
        _finish_combat(session, "defeat", "プレイヤーは戦闘不能になった。")
        return
    enemies = combat.get("enemies") or []
    if enemies and all(_enemy_is_defeated(enemy) for enemy in enemies):
        _finish_combat(session, "victory", "すべての敵を倒した。")


def _finish_combat(session: dict[str, Any], status: str, summary: str) -> None:
    combat = session["combat"]
    if combat.get("status") != "active":
        return
    combat["status"] = status
    combat["turn"] = "complete"
    combat["pending_resolution"] = True
    enemies = combat.get("enemies") or []
    result: dict[str, Any] = {
        "combat_id": combat.get("id"),
        "outcome": status,
        "rounds": combat.get("round"),
        "location_id": combat.get("location_id"),
        "scene_id": combat.get("scene_id"),
        "summary": summary,
        "player": {
            "name": session["character"].get("name"),
            "hp": session["character"].get("hp"),
            "max_hp": session["character"].get("max_hp"),
            "mp": session["character"].get("mp"),
            "sp": session["character"].get("sp"),
        },
        "enemies": [
            {"id": enemy.get("template_id") or enemy.get("id"), "name": enemy.get("name"), "hp": enemy.get("hp"), "max_hp": enemy.get("max_hp")}
            for enemy in enemies
        ],
        "recent_events": [entry.get("text") for entry in (combat.get("log") or [])[-8:]],
    }
    result_texts = (combat.get("encounter") or {}).get("result_texts")
    if isinstance(result_texts, dict) and isinstance(result_texts.get(status), str):
        result["prepared_text"] = result_texts[status]
    if status == "victory":
        delta = _victory_delta(session, enemies, combat.get("encounter") or {})
        combat["pending_state_delta"] = delta
        result["rewards"] = deepcopy(delta)
        flags = session.setdefault("flags", {})
        for enemy in enemies:
            template_id = str(enemy.get("template_id") or enemy.get("id") or "")
            if template_id:
                flags[_defeated_flag(template_id, str(combat.get("location_id") or ""))] = True
    elif status == "defeat":
        defeat_delta = deepcopy((combat.get("encounter") or {}).get("defeat_effects") or {})
        if isinstance(defeat_delta, dict) and defeat_delta:
            combat["pending_state_delta"] = defeat_delta
    combat["result"] = result
    _log(session, "system", status, summary)


def _victory_delta(session: dict[str, Any], enemies: list[dict[str, Any]], encounter: dict[str, Any]) -> dict[str, Any]:
    delta: dict[str, Any] = {"gold_change": 0, "inventory_add": [], "flags_set": []}
    for enemy in enemies:
        rewards = enemy.get("rewards") if isinstance(enemy.get("rewards"), dict) else {}
        delta["gold_change"] += _safe_int(rewards.get("gold"), 0)
        delta["inventory_add"].extend(deepcopy(rewards.get("items") or []))
        delta["flags_set"].extend(str(flag) for flag in (rewards.get("flags") or []) if flag)
    extra = deepcopy(encounter.get("victory_effects")) if isinstance(encounter.get("victory_effects"), dict) else {}
    by_character = encounter.get("victory_effects_by_character")
    character = session.get("character", {}) if isinstance(session.get("character"), dict) else {}
    character_id = str(character.get("id") or character.get("character_id") or "")
    if isinstance(by_character, dict) and isinstance(by_character.get(character_id), dict):
        extra = _merge_combat_deltas(extra, by_character[character_id])
    delta["gold_change"] += _safe_int(extra.get("gold_change"), 0)
    delta["inventory_add"].extend(deepcopy(extra.get("inventory_add") or []))
    delta["flags_set"].extend(str(flag) for flag in (extra.get("flags_set") or []) if flag)
    for key in (
        "current_scene", "current_location", "hp_change", "mp_change", "sp_change",
        "inventory_remove", "flags_unset", "attribute_changes", "attribute_set",
        "set_companion", "clear_companion", "clear_skills", "equip_item", "game_over",
        "restore_full",
    ):
        if key in extra:
            delta[key] = deepcopy(extra[key])
    if not delta["gold_change"]:
        delta.pop("gold_change")
    if not delta["inventory_add"]:
        delta.pop("inventory_add")
    if not delta["flags_set"]:
        delta.pop("flags_set")
    return delta


def _merge_combat_deltas(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if key in {"inventory_add", "inventory_remove", "flags_set", "flags_unset"}:
            merged[key] = [*deepcopy(merged.get(key) or []), *deepcopy(value or [])]
        elif key in {"gold_change", "hp_change", "mp_change", "sp_change"}:
            merged[key] = _safe_int(merged.get(key), 0) + _safe_int(value, 0)
        elif key in {"attribute_changes", "attribute_set"} and isinstance(value, dict):
            current = merged.get(key) if isinstance(merged.get(key), dict) else {}
            merged[key] = {**deepcopy(current), **deepcopy(value)}
        else:
            merged[key] = deepcopy(value)
    return merged


def _regenerate_round_resources(session: dict[str, Any]) -> None:
    character = session["character"]
    amount = max(0, _safe_int(_combat_rules(session).get("sp_regen_per_round"), 1))
    if amount:
        character["sp"] = min(_safe_int(character.get("max_sp"), 0), _safe_int(character.get("sp"), 0) + amount)


def _apply_round_start_effects(session: dict[str, Any], rng: Any) -> None:
    combat = session.get("combat")
    if not isinstance(combat, dict) or combat.get("status") != "active":
        return
    _apply_enemy_fields(session, rng)
    _tick_enemy_statuses(session, rng)
    if combat.get("status") != "active":
        return
    companion = session.get("companion") if isinstance(session.get("companion"), dict) else {}
    if (combat.get("encounter") or {}).get("disable_companion"):
        companion = {}
    for effect in companion.get("round_start_effects") or []:
        if not isinstance(effect, dict):
            continue
        kind = str(effect.get("kind") or "")
        if kind == "heal_player":
            amount, detail = _roll_formula(str(effect.get("amount") or "0"), session["character"], rng)
            healed = _heal_actor(session["character"], amount)
            if healed > 0:
                _log(session, "companion", "heal", f"{companion.get('name', '同行者')}がHPを{healed}回復した。", {"amount": healed, "formula": detail})
        elif kind == "damage_enemy":
            targets = list(_alive_enemies(combat))
            if not effect.get("all_targets") and targets:
                targets = targets[:1]
            for target in targets:
                ability = {
                    "name": str(effect.get("name") or companion.get("name") or "同行者の攻撃"),
                    "damage": str(effect.get("damage") or "1"),
                    "accuracy": 100,
                    "element": str(effect.get("element") or "physical"),
                }
                _resolve_attack(session, companion, target, ability, "companion", rng)
    _check_victory_or_defeat(session)


def _tick_enemy_statuses(session: dict[str, Any], rng: Any) -> None:
    for enemy in _alive_enemies(session["combat"]):
        active_statuses: list[dict[str, Any]] = []
        for status in enemy.get("statuses") or []:
            if not isinstance(status, dict):
                continue
            stacks = max(1, _safe_int(status.get("stacks"), 1))
            damage, detail = _roll_formula(str(status.get("damage") or "0"), session["character"], rng)
            damage = max(0, damage * stacks)
            if damage:
                next_hp = _safe_int(enemy.get("hp"), 0) - damage
                enemy["hp"] = next_hp if _negative_undead(enemy) else max(0, next_hp)
                _log(
                    session,
                    "status",
                    "status_damage",
                    f"{enemy.get('name', '敵')}は{status.get('name') or status.get('id') or '状態異常'}で{damage}ダメージを受けた。",
                    {"damage": damage, "stacks": stacks, "formula": detail},
                )
            remaining = status.get("remaining_rounds")
            if isinstance(remaining, int):
                status["remaining_rounds"] = remaining - 1
                if status["remaining_rounds"] <= 0:
                    continue
            active_statuses.append(status)
        enemy["statuses"] = active_statuses


def _apply_status(actor: dict[str, Any], status_spec: dict[str, Any]) -> None:
    statuses = actor.setdefault("statuses", [])
    status_id = str(status_spec.get("id") or status_spec.get("name") or "status")
    existing = next((status for status in statuses if isinstance(status, dict) and str(status.get("id") or "") == status_id), None)
    if existing and status_spec.get("stackable"):
        existing["stacks"] = max(1, _safe_int(existing.get("stacks"), 1)) + 1
        return
    if existing:
        existing.update(deepcopy(status_spec))
        return
    status = deepcopy(status_spec)
    status["id"] = status_id
    status.setdefault("stacks", 1)
    statuses.append(status)


def _apply_undead_conversion(session: dict[str, Any], actor_id: str) -> None:
    character = session["character"]
    parts = character.setdefault("undead_parts", [])
    sequence = ["左腕", "右腕", "左脚", "右脚", "胴体"]
    if len(parts) >= len(sequence):
        session["game_over"] = {
            "reason": "全身を亡霊へ変えられ、亡霊大法師として支配されました。",
            "ending": "undead_archmage",
        }
        _log(session, actor_id, "game_over", session["game_over"]["reason"])
        _finish_combat(session, "defeat", session["game_over"]["reason"])
        return
    part = sequence[len(parts)]
    parts.append(part)
    _log(session, actor_id, "status", f"{part}が永久に亡霊化しました。", {"part": part, "count": len(parts)})


def _encounter_for_session(session: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    location_id = current_location_id(session)
    location = next((item for item in pack.get("locations", []) if isinstance(item, dict) and str(item.get("id") or "") == location_id), None)
    scene = find_scene(pack, current_scene_id(session))
    encounter = deepcopy(location.get("combat") if isinstance(location, dict) and isinstance(location.get("combat"), dict) else {})
    enemy_ids = _as_text_list(encounter.get("enemy_ids"))
    if not enemy_ids and isinstance(location, dict):
        enemy_ids = _as_text_list(location.get("enemy_ids"))
    if not enemy_ids and isinstance(scene, dict):
        enemy_ids = _as_text_list(scene.get("enemy_ids"))
    encounter["enemy_ids"] = enemy_ids
    encounter.setdefault("flee_allowed", True)
    return encounter


def _runtime_enemy(template: dict[str, Any], index: int) -> dict[str, Any]:
    enemy = deepcopy(template)
    template_id = str(template.get("id") or f"enemy_{index + 1}")
    enemy["template_id"] = template_id
    enemy["id"] = f"{template_id}:{index + 1}"
    enemy["hp"] = _safe_int(template.get("hp"), _safe_int(template.get("max_hp"), 1))
    enemy["max_hp"] = _safe_int(template.get("max_hp"), enemy["hp"]) if _negative_undead(enemy) else max(1, _safe_int(template.get("max_hp"), enemy["hp"]))
    enemy["mp"] = _safe_int(template.get("mp"), _safe_int(template.get("max_mp"), 0))
    enemy["max_mp"] = max(0, _safe_int(template.get("max_mp"), enemy["mp"]))
    enemy["sp"] = _safe_int(template.get("sp"), _safe_int(template.get("max_sp"), 0))
    enemy["max_sp"] = max(0, _safe_int(template.get("max_sp"), enemy["sp"]))
    enemy["skills"] = deepcopy(template.get("skills") or [])
    enemy["statuses"] = []
    return enemy


def _runtime_player_character(template: dict[str, Any]) -> dict[str, Any]:
    character = deepcopy(template)
    character["character_id"] = str(template.get("id") or template.get("character_id") or "")
    for stat in ("hp", "mp", "sp"):
        maximum = max(0, _safe_int(template.get(f"max_{stat}"), _safe_int(template.get(stat), 0)))
        character[f"max_{stat}"] = maximum
        character[stat] = max(0, min(maximum, _safe_int(template.get(stat), maximum)))
    character.setdefault("inventory", [])
    character.setdefault("equipment", [])
    character.setdefault("skills", [])
    character.setdefault("attributes", {})
    return character


def _choose_enemy_ability(enemy: dict[str, Any], session: dict[str, Any], rng: Any) -> dict[str, Any]:
    affordable: list[dict[str, Any]] = []
    weights: list[int] = []
    for skill in enemy.get("skills") or []:
        if not isinstance(skill, dict) or not _can_pay_cost(enemy, skill):
            continue
        character = session.get("character", {}) if isinstance(session.get("character"), dict) else {}
        character_id = str(character.get("id") or character.get("character_id") or "")
        if skill.get("skip_if_mage_undead") and character_id == "mage" and character.get("undead_parts"):
            continue
        use_below = skill.get("use_below_hp_ratio")
        if isinstance(use_below, (int, float)) and _hp_ratio(enemy) > float(use_below):
            continue
        if _ability_kind(skill) == "field" and _field_is_active(session, enemy, skill):
            continue
        affordable.append(skill)
        weights.append(max(1, _safe_int(skill.get("ai_weight"), 1)))
    if affordable:
        if hasattr(rng, "choices"):
            return deepcopy(rng.choices(affordable, weights=weights, k=1)[0])
        return deepcopy(affordable[rng.randint(0, len(affordable) - 1)])
    enemy_combat = enemy.get("combat") if isinstance(enemy.get("combat"), dict) else {}
    return _merge_dict(_combat_rules(session).get("enemy_basic_attack"), enemy_combat.get("basic_attack"))


def _pay_cost(actor: dict[str, Any], ability: dict[str, Any]) -> None:
    if not _can_pay_cost(actor, ability):
        raise CombatError("リソースが不足しています。")
    cost = effective_ability_cost(actor, ability)
    cost_type = str(ability.get("cost_type") or "").lower()
    if cost and cost_type in {"hp", "mp", "sp"}:
        actor[cost_type] = max(0, _safe_int(actor.get(cost_type), 0) - cost)


def _can_pay_cost(actor: dict[str, Any], ability: dict[str, Any]) -> bool:
    cost = effective_ability_cost(actor, ability)
    cost_type = str(ability.get("cost_type") or "").lower()
    return not cost_type or cost_type not in {"hp", "mp", "sp"} or _safe_int(actor.get(cost_type), 0) >= cost


def _target_enemy(combat: dict[str, Any], target_id: str) -> dict[str, Any]:
    alive = _alive_enemies(combat)
    if not alive:
        raise CombatError("攻撃可能な敵がいません。")
    if target_id:
        target = next((enemy for enemy in alive if target_id in {str(enemy.get("id") or ""), str(enemy.get("template_id") or "")}), None)
        if target:
            return target
        raise CombatError("対象の敵が見つかりません。")
    return alive[0]


def _alive_enemies(combat: dict[str, Any]) -> list[dict[str, Any]]:
    return [enemy for enemy in combat.get("enemies") or [] if not _enemy_is_defeated(enemy)]


def _negative_undead(actor: dict[str, Any]) -> bool:
    combat = actor.get("combat") if isinstance(actor.get("combat"), dict) else {}
    return str(combat.get("life_rule") or actor.get("life_rule") or "") == "negative_undead"


def _enemy_is_defeated(enemy: dict[str, Any]) -> bool:
    hp = _safe_int(enemy.get("hp"), 0)
    return hp >= 0 if _negative_undead(enemy) else hp <= 0


def _player_actions_per_round(session: dict[str, Any]) -> int:
    character = session.get("character") if isinstance(session.get("character"), dict) else {}
    equipped = {str(value) for value in character.get("equipment") or [] if str(value)}
    extra = 0
    for item in character.get("inventory") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("name") or "") not in equipped and str(item.get("id") or "") not in equipped:
            continue
        extra += max(0, _safe_int(item_combat_spec(item).get("extra_actions_per_round"), 0))
    return max(1, 1 + extra)


def _equipped_effect(character: dict[str, Any], key: str) -> Any:
    equipped = {str(value) for value in character.get("equipment") or [] if str(value)}
    for item in character.get("inventory") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("name") or "") not in equipped and str(item.get("id") or "") not in equipped:
            continue
        value = item_combat_spec(item).get(key)
        if value:
            return value
    return None


def _available_skills(character: dict[str, Any]) -> list[dict[str, Any]]:
    skills = [deepcopy(skill) for skill in character.get("skills") or [] if isinstance(skill, dict)]
    equipped = {str(value) for value in character.get("equipment") or [] if str(value)}
    for item in character.get("inventory") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("name") or "") not in equipped and str(item.get("id") or "") not in equipped:
            continue
        spec = item_combat_spec(item)
        for skill in spec.get("grants_skills") or []:
            if not isinstance(skill, dict):
                continue
            skill_id = str(skill.get("id") or "")
            if skill_id and any(str(existing.get("id") or "") == skill_id for existing in skills):
                continue
            skills.append(deepcopy(skill))
    return skills


def _find_entry(entries: Any, wanted_id: str, prefix: str) -> Optional[dict[str, Any]]:
    if not isinstance(entries, list):
        return None
    for index, raw in enumerate(entries):
        entry = raw if isinstance(raw, dict) else {"name": str(raw)}
        if wanted_id in {_entry_id(entry, prefix, index), str(entry.get("id") or ""), str(entry.get("name") or "")}:
            return entry
    return None


def _entry_id(entry: dict[str, Any], prefix: str, index: int) -> str:
    explicit = str(entry.get("id") or "").strip()
    return explicit or f"{prefix}_{index}"


def _equipped_weapon_attack(character: dict[str, Any]) -> dict[str, Any]:
    equipment = character.get("equipment") if isinstance(character.get("equipment"), list) else []
    inventory = character.get("inventory") if isinstance(character.get("inventory"), list) else []
    for raw in inventory:
        item = raw if isinstance(raw, dict) else {"name": str(raw)}
        if str(item.get("name") or "") not in equipment:
            continue
        spec = item.get("combat") if isinstance(item.get("combat"), dict) else {}
        if str(spec.get("kind") or "") == "weapon":
            return deepcopy(spec)
    return {}


def _consume_inventory_item(character: dict[str, Any], item: dict[str, Any]) -> None:
    inventory = character.get("inventory") if isinstance(character.get("inventory"), list) else []
    quantity = max(1, _safe_int(item.get("quantity"), 1))
    if quantity > 1:
        item["quantity"] = quantity - 1
    else:
        inventory.remove(item)


def _ability_kind(ability: dict[str, Any]) -> str:
    explicit = str(ability.get("kind") or ability.get("type") or "").lower()
    if explicit in {"attack", "damage", "heal", "defend", "status", "field", "stance"}:
        return "attack" if explicit == "damage" else explicit
    text = f"{ability.get('name', '')} {ability.get('effect', '')} {ability.get('description', '')}".lower()
    if "回復" in text or "heal" in text:
        return "heal"
    if any(word in text for word in ("半減", "防御", "守護", "guard", "defend")):
        return "defend"
    return "attack"


def _heal_actor(actor: dict[str, Any], amount: int) -> int:
    before = _safe_int(actor.get("hp"), 0)
    maximum = max(before, _safe_int(actor.get("max_hp"), before))
    actor["hp"] = min(maximum, before + max(0, amount))
    return _safe_int(actor.get("hp"), 0) - before


def _restore_actor_resource(actor: dict[str, Any], resource: str, amount: int) -> int:
    before = _safe_int(actor.get(resource), 0)
    maximum = max(before, _safe_int(actor.get(f"max_{resource}"), before))
    actor[resource] = min(maximum, before + max(0, amount))
    return _safe_int(actor.get(resource), 0) - before


def _actor_defense(actor: dict[str, Any]) -> int:
    combat = actor.get("combat") if isinstance(actor.get("combat"), dict) else {}
    explicit = _safe_int(combat.get("defense", actor.get("defense")), 0)
    equipment = actor.get("equipment") if isinstance(actor.get("equipment"), list) else []
    inventory = actor.get("inventory") if isinstance(actor.get("inventory"), list) else []
    derived = 0
    for raw in inventory:
        item = raw if isinstance(raw, dict) else {"name": str(raw)}
        if str(item.get("name") or "") not in equipment:
            continue
        item_combat = item.get("combat") if isinstance(item.get("combat"), dict) else {}
        if isinstance(item_combat.get("defense"), (int, float)):
            derived += int(item_combat["defense"])
    return max(0, explicit + derived)


def _primary_element(actor: dict[str, Any]) -> str:
    explicit = str(actor.get("element") or "").lower()
    if explicit:
        return explicit
    combat = actor.get("combat") if isinstance(actor.get("combat"), dict) else {}
    basic_attack = combat.get("basic_attack") if isinstance(combat.get("basic_attack"), dict) else {}
    return str(basic_attack.get("element") or "physical").lower()


def _counter_element(element: str) -> str:
    return {
        "fire": "water",
        "water": "lightning",
        "lightning": "earth",
        "earth": "wind",
        "wind": "ice",
        "ice": "fire",
        "light": "dark",
        "dark": "light",
    }.get(str(element or "").lower(), "arcane")


def _resistance_multiplier(actor: dict[str, Any], element: str) -> float:
    element = str(element or "physical").lower()
    immunities = {
        str(value).lower() for value in actor.get("combat_immunities") or [] if str(value)
    }
    if element in immunities:
        return 0.0
    resistances = actor.get("resistances") if isinstance(actor.get("resistances"), dict) else {}
    raw = resistances.get(element, 1.0)
    try:
        multiplier = max(0.0, float(raw))
    except (TypeError, ValueError):
        multiplier = 1.0
    for item in actor.get("inventory") or []:
        if not isinstance(item, dict):
            continue
        spec = item_combat_spec(item)
        passive = spec.get("damage_taken_multipliers")
        if not isinstance(passive, dict):
            continue
        try:
            multiplier *= max(0.0, float(passive.get(element, 1.0)))
        except (TypeError, ValueError):
            continue
    return multiplier


def _roll_formula(formula: str, actor: dict[str, Any], rng: Any) -> tuple[int, dict[str, Any]]:
    normalized = _normalize_formula(formula)
    if not normalized:
        normalized = "1"
    terms = re.findall(r"[+-]?[^+-]+", normalized)
    total = 0
    details: list[dict[str, Any]] = []
    for raw_term in terms:
        sign = -1 if raw_term.startswith("-") else 1
        term = raw_term.lstrip("+-")
        dice_match = re.fullmatch(r"(\d*)d(\d+)", term)
        if dice_match:
            count = int(dice_match.group(1) or 1)
            sides = max(2, int(dice_match.group(2)))
            rolls = [rng.randint(1, sides) for _ in range(max(1, min(count, 20)))]
            value = sum(rolls)
            details.append({"term": term, "rolls": rolls, "value": sign * value})
            total += sign * value
            continue
        attr_match = re.fullmatch(r"([a-z_]+)(?:/(\d+))?", term)
        if attr_match:
            key = _canonical_attr(attr_match.group(1))
            divisor = max(1, int(attr_match.group(2) or 1))
            attrs = actor.get("attributes") if isinstance(actor.get("attributes"), dict) else {}
            value = _safe_int(attrs.get(key, attrs.get("con") if key == "end" else 0), 0) // divisor
            details.append({"term": term, "attribute": key, "value": sign * value})
            total += sign * value
            continue
        try:
            value = int(float(term))
        except (TypeError, ValueError):
            value = 0
        details.append({"term": term, "value": sign * value})
        total += sign * value
    return max(0, total), {"formula": formula, "normalized": normalized, "terms": details, "total": max(0, total)}


def _normalize_formula(formula: str) -> str:
    value = str(formula or "").lower().replace(" ", "").replace("％", "%")
    aliases = {
        "筋力": "str",
        "敏捷": "dex",
        "器用": "dex",
        "知力": "int",
        "知性": "int",
        "判断": "wis",
        "知恵": "wis",
        "耐久": "end",
        "体力": "end",
        "魅力": "cha",
        "strength": "str",
        "dexterity": "dex",
        "intelligence": "int",
        "wisdom": "wis",
        "endurance": "end",
        "constitution": "end",
    }
    for source, target in aliases.items():
        value = value.replace(source, target)
    value = re.sub(r"[^0-9a-z_+\-/d.]", "", value)
    return value


def _canonical_attr(key: str) -> str:
    return {"con": "end", "endurance": "end", "constitution": "end"}.get(key, key)


def _combat_rules(session: dict[str, Any]) -> dict[str, Any]:
    pack = session.get("scenario_pack") if isinstance(session.get("scenario_pack"), dict) else {}
    return _merge_dict(DEFAULT_COMBAT_RULES, pack.get("combat_rules"))


def _merge_dict(base: Any, override: Any) -> dict[str, Any]:
    result = deepcopy(base) if isinstance(base, dict) else {}
    if isinstance(override, dict):
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = _merge_dict(result[key], value)
            else:
                result[key] = deepcopy(value)
    return result


def _log(session: dict[str, Any], actor: str, kind: str, text: str, data: Optional[dict[str, Any]] = None) -> None:
    combat = session.get("combat")
    if not isinstance(combat, dict):
        return
    entry = {
        "round": combat.get("round", 1),
        "actor": actor,
        "kind": kind,
        "text": text,
        "created_at": utc_now(),
    }
    if data:
        entry["data"] = deepcopy(data)
    combat.setdefault("log", []).append(entry)
    if len(combat["log"]) > 80:
        combat["log"] = combat["log"][-80:]


def _defeated_flag(enemy_id: str, location_id: str) -> str:
    return f"combat_defeated:{location_id}:{enemy_id}"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value:
        return [value]
    return []
