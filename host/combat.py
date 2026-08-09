from __future__ import annotations

import random
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional

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
    blocked_location = str(session.get("combat_blocked_location") or "")
    if blocked_location and blocked_location != location_id:
        session.pop("combat_blocked_location", None)
    elif blocked_location and blocked_location == location_id:
        return False

    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return False
    encounter = _encounter_for_session(session, pack)
    enemy_ids = encounter.get("enemy_ids") or []
    defeated = session.get("flags") if isinstance(session.get("flags"), dict) else {}
    enemy_templates = [
        enemy
        for enemy in pack.get("enemies", [])
        if isinstance(enemy, dict)
        and str(enemy.get("id") or "") in enemy_ids
        and not defeated.get(_defeated_flag(str(enemy.get("id") or ""), location_id))
    ]
    if not enemy_templates:
        return False

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
        "encounter": deepcopy(encounter),
        "pending_resolution": False,
        "result": None,
        "created_at": utc_now(),
    }
    session["choices"] = []
    _log(session, "system", "start", f"戦闘開始: {'、'.join(enemy['name'] for enemy in enemies)}")
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
        _enemy_phase(session, random_source)
    if combat.get("status") == "active":
        _check_victory_or_defeat(session)
    if combat.get("status") == "active":
        combat["round"] = int(combat.get("round", 1)) + 1
        combat["turn"] = "player"
        _regenerate_round_resources(session)
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
    return deepcopy(result)


def clear_combat_after_resolution(session: dict[str, Any]) -> dict[str, Any]:
    combat = session.get("combat")
    if not isinstance(combat, dict):
        return {}
    result = deepcopy(combat.get("result") or {})
    status = str(combat.get("status") or "")
    location_id = str(combat.get("location_id") or current_location_id(session))
    if status in {"fled", "defeat"} and location_id:
        session["combat_blocked_location"] = location_id
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
    actions: list[dict[str, Any]] = [
        {
            "type": "attack",
            "id": "basic_attack",
            "name": str(basic.get("name") or "通常攻撃"),
            "description": str(basic.get("description") or "装備中の武器で攻撃する。"),
            "cost": 0,
            "cost_type": "",
            "enabled": True,
        }
    ]
    for index, skill in enumerate(character.get("skills") or []):
        if not isinstance(skill, dict):
            continue
        skill_id = _entry_id(skill, "skill", index)
        cost = max(0, _safe_int(skill.get("cost"), 0))
        cost_type = str(skill.get("cost_type") or "").lower()
        available = _safe_int(character.get(cost_type), 0) if cost_type in {"mp", "sp", "hp"} else cost
        enabled = available >= cost
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
        })
    for index, item in enumerate(character.get("inventory") or []):
        normalized = item if isinstance(item, dict) else {"name": str(item), "quantity": 1}
        spec = _item_combat_spec(normalized)
        if not spec or _safe_int(normalized.get("quantity"), 1) <= 0:
            continue
        item_id = _entry_id(normalized, "item", index)
        actions.append({
            "type": "item",
            "id": item_id,
            "name": str(normalized.get("name") or item_id),
            "description": str(normalized.get("description") or normalized.get("effect") or ""),
            "quantity": _safe_int(normalized.get("quantity"), 1),
            "kind": spec.get("kind"),
            "enabled": True,
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


def _player_attack(session: dict[str, Any], target_id: str, rng: Any) -> None:
    combat = session["combat"]
    character = session["character"]
    target = _target_enemy(combat, target_id)
    rules = _combat_rules(session)
    char_combat = character.get("combat") if isinstance(character.get("combat"), dict) else {}
    attack = _merge_dict(rules.get("basic_attack"), char_combat.get("basic_attack"))
    attack = _merge_dict(attack, _equipped_weapon_attack(character))
    _resolve_attack(session, character, target, attack, "player", rng)


def _player_skill(session: dict[str, Any], skill_id: str, target_id: str, rng: Any) -> None:
    character = session["character"]
    skill = _find_entry(character.get("skills"), skill_id, "skill")
    if not skill:
        raise CombatError("技能が見つかりません。")
    _pay_cost(character, skill)
    kind = _ability_kind(skill)
    if kind == "heal":
        amount, detail = _roll_formula(str(skill.get("healing") or skill.get("dice_type") or "1d6+int/4"), character, rng)
        healed = _heal_actor(character, amount)
        _log(session, "player", "heal", f"{skill.get('name', '技能')}でHPを{healed}回復した。", {"amount": healed, "formula": detail})
    elif kind == "defend":
        multiplier = float(skill.get("guard_multiplier", _combat_rules(session).get("defend_multiplier", 0.5)) or 0.5)
        session["combat"].setdefault("player_status", {})["guard_multiplier"] = max(0.0, min(1.0, multiplier))
        session["combat"]["player_status"]["survive_at_one"] = bool(skill.get("survive_at_one", True))
        _log(session, "player", "defend", f"{skill.get('name', '防御技能')}を使用し、守りを固めた。")
    else:
        target = _target_enemy(session["combat"], target_id)
        _resolve_attack(session, character, target, skill, "player", rng)


def _player_item(session: dict[str, Any], item_id: str, target_id: str, rng: Any) -> None:
    character = session["character"]
    inventory = character.get("inventory") if isinstance(character.get("inventory"), list) else []
    item = _find_entry(inventory, item_id, "item")
    if not item:
        raise CombatError("道具が見つかりません。")
    spec = _item_combat_spec(item)
    if not spec:
        raise CombatError("この道具は戦闘中に使用できません。")
    kind = str(spec.get("kind") or "heal")
    if kind == "heal":
        amount, detail = _roll_formula(str(spec.get("healing") or spec.get("formula") or "10"), character, rng)
        healed = _heal_actor(character, amount)
        _log(session, "player", "item", f"{item.get('name', '道具')}を使い、HPを{healed}回復した。", {"amount": healed, "formula": detail})
    elif kind == "damage":
        target = _target_enemy(session["combat"], target_id)
        _resolve_attack(session, character, target, spec, "player", rng, display_name=str(item.get("name") or "道具"))
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
        if _safe_int(enemy.get("hp"), 0) <= 0 or _safe_int(session["character"].get("hp"), 0) <= 0:
            continue
        ability = _choose_enemy_ability(enemy, session, rng)
        _pay_cost(enemy, ability)
        kind = _ability_kind(ability)
        if kind == "heal":
            amount, detail = _roll_formula(str(ability.get("healing") or ability.get("dice_type") or "1d4"), enemy, rng)
            healed = _heal_actor(enemy, amount)
            _log(session, enemy.get("id", "enemy"), "heal", f"{enemy.get('name')}は{ability.get('name')}でHPを{healed}回復した。", {"amount": healed, "formula": detail})
        else:
            _resolve_attack(session, enemy, session["character"], ability, str(enemy.get("id") or "enemy"), rng)
    combat["player_status"] = {}


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
    element = str(ability.get("element") or "physical")
    multiplier = _resistance_multiplier(defender, element)
    defense = _actor_defense(defender)
    damage = max(1, int(round(raw_damage * multiplier)) - defense)
    if defender is session.get("character"):
        status = session["combat"].get("player_status") or {}
        guard = float(status.get("guard_multiplier", 1.0) or 1.0)
        damage = max(0, int(round(damage * guard)))
    before_hp = _safe_int(defender.get("hp"), 0)
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


def _check_victory_or_defeat(session: dict[str, Any]) -> None:
    combat = session["combat"]
    if _safe_int(session["character"].get("hp"), 0) <= 0:
        _finish_combat(session, "defeat", "プレイヤーは戦闘不能になった。")
        return
    enemies = combat.get("enemies") or []
    if enemies and all(_safe_int(enemy.get("hp"), 0) <= 0 for enemy in enemies):
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
    extra = encounter.get("victory_effects") if isinstance(encounter.get("victory_effects"), dict) else {}
    delta["gold_change"] += _safe_int(extra.get("gold_change"), 0)
    delta["inventory_add"].extend(deepcopy(extra.get("inventory_add") or []))
    delta["flags_set"].extend(str(flag) for flag in (extra.get("flags_set") or []) if flag)
    for key in ("current_scene", "current_location", "hp_change", "mp_change", "sp_change"):
        if key in extra:
            delta[key] = deepcopy(extra[key])
    if not delta["gold_change"]:
        delta.pop("gold_change")
    if not delta["inventory_add"]:
        delta.pop("inventory_add")
    if not delta["flags_set"]:
        delta.pop("flags_set")
    return delta


def _regenerate_round_resources(session: dict[str, Any]) -> None:
    character = session["character"]
    amount = max(0, _safe_int(_combat_rules(session).get("sp_regen_per_round"), 1))
    if amount:
        character["sp"] = min(_safe_int(character.get("max_sp"), 0), _safe_int(character.get("sp"), 0) + amount)


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
    enemy["max_hp"] = max(1, _safe_int(template.get("max_hp"), enemy["hp"]))
    enemy["mp"] = _safe_int(template.get("mp"), _safe_int(template.get("max_mp"), 0))
    enemy["max_mp"] = max(0, _safe_int(template.get("max_mp"), enemy["mp"]))
    enemy["sp"] = _safe_int(template.get("sp"), _safe_int(template.get("max_sp"), 0))
    enemy["max_sp"] = max(0, _safe_int(template.get("max_sp"), enemy["sp"]))
    enemy["skills"] = deepcopy(template.get("skills") or [])
    return enemy


def _choose_enemy_ability(enemy: dict[str, Any], session: dict[str, Any], rng: Any) -> dict[str, Any]:
    affordable: list[dict[str, Any]] = []
    weights: list[int] = []
    for skill in enemy.get("skills") or []:
        if not isinstance(skill, dict) or not _can_pay_cost(enemy, skill):
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
    cost = max(0, _safe_int(ability.get("cost"), 0))
    cost_type = str(ability.get("cost_type") or "").lower()
    if cost and cost_type in {"hp", "mp", "sp"}:
        actor[cost_type] = max(0, _safe_int(actor.get(cost_type), 0) - cost)


def _can_pay_cost(actor: dict[str, Any], ability: dict[str, Any]) -> bool:
    cost = max(0, _safe_int(ability.get("cost"), 0))
    cost_type = str(ability.get("cost_type") or "").lower()
    return not cost_type or cost_type not in {"hp", "mp", "sp"} or _safe_int(actor.get(cost_type), 0) >= cost


def _target_enemy(combat: dict[str, Any], target_id: str) -> dict[str, Any]:
    alive = [enemy for enemy in combat.get("enemies") or [] if _safe_int(enemy.get("hp"), 0) > 0]
    if not alive:
        raise CombatError("攻撃可能な敵がいません。")
    if target_id:
        target = next((enemy for enemy in alive if target_id in {str(enemy.get("id") or ""), str(enemy.get("template_id") or "")}), None)
        if target:
            return target
        raise CombatError("対象の敵が見つかりません。")
    return alive[0]


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


def _item_combat_spec(item: dict[str, Any]) -> dict[str, Any]:
    if isinstance(item.get("combat"), dict):
        spec = deepcopy(item["combat"])
        return spec if str(spec.get("kind") or "") in {"heal", "damage"} else {}
    effect = str(item.get("effect") or "")
    heal_match = re.search(r"HP[^0-9]*(\d+)[^0-9]*(?:回復|heal)", effect, re.IGNORECASE)
    if heal_match:
        return {"kind": "heal", "healing": heal_match.group(1)}
    return {}


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
    if explicit in {"attack", "damage", "heal", "defend", "status"}:
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
            continue
        match = re.search(r"(?:軽減|reduce)[^0-9]*(\d+)", str(item.get("effect") or ""), re.IGNORECASE)
        if match:
            derived += int(match.group(1))
    return max(0, explicit + derived)


def _resistance_multiplier(actor: dict[str, Any], element: str) -> float:
    resistances = actor.get("resistances") if isinstance(actor.get("resistances"), dict) else {}
    raw = resistances.get(element, 1.0)
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 1.0


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
