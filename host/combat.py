from __future__ import annotations

from . import progression

import random
import math
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional

from . import status_effects
from .gm_contract import sanitize_visible_text
from .item_mechanics import (
    equipped_basic_attack_followups,
    equipped_item_specs,
    equipped_items,
    item_slot,
    effective_ability,
    effective_ability_cost,
    item_combat_spec,
    item_is_combat_usable,
    one_time_reward,
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
    "evade_model": "fixed",
    "evade_formula": {"base": 4, "per_dex": 1.5, "cap": 20},
    "total_evade_cap": 40,
    "temporary_evade_max_rounds": 2,
    "enemy_accuracy_override": None,
}

# TODO(design): Finalize the placeholder UI text and the activated_ice_charm restriction.
COOLDOWN_REASON = "あと{rounds}ラウンド"
WEAKNESS_REASON = "{element}に弱い相手にしか使えない。"
STATUS_ACTIVE_REASON = "{name}の効果が持続している。"


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


def ensure_combat_started(session: dict[str, Any], intro_text: str = "") -> bool:
    if session.get("game_over"):
        return False
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
    for change in (session.get("scene_changes") or {}).get(location_id, {}).values():
        if isinstance(change, dict):
            change.pop("distracted", None)
            change.pop("prepared", None)
    location = next(
        (
            item for item in pack.get("locations", [])
            if isinstance(item, dict) and str(item.get("id") or "") == location_id
        ),
        {},
    )
    resolved_intro = sanitize_visible_text(
        str(intro_text or encounter.get("intro_text") or location.get("description") or "")
    ).strip()
    _grant_start_items(session, encounter)
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
        "intro_text": resolved_intro,
        "created_at": utc_now(),
        "event_cursor": len(session.get("event_log") or []),
    }
    if original_character is not None:
        session["combat"]["original_character"] = original_character
    if progression.enabled(session):
        session["combat"]["passive_state"] = {}
        shield = progression.effects(session).get("battle_shield")
        if shield:
            status_effects.apply(session, session["character"], shield, session["character"], random)
    session["choices"] = []
    session.pop("combat_start_requested", None)
    _log(session, "system", "start", f"戦闘開始: {'、'.join(enemy['name'] for enemy in enemies)}")
    _activate_phase_allies(session)
    _activate_encounter_modifiers(session)
    from .state import _session_requirement_passes
    for event in encounter.get('start_events', []):
        if _session_requirement_passes(event.get('requirements'), session):
            _log(session, 'system', 'warning', event['text'])
    _apply_round_start_effects(session, random)
    enemy_first = session.pop('enemy_first_requested', False)
    if encounter.get('enemy_first_requirements'):
        enemy_first = enemy_first or _session_requirement_passes(encounter['enemy_first_requirements'], session)
    if encounter.get('player_first_requirements') and _session_requirement_passes(encounter['player_first_requirements'], session):
        enemy_first = False
    if enemy_first and combat_is_active(session):
        _enemy_phase(session, random)
        session['combat']['turn'] = 'player'
    _check_victory_or_defeat(session)
    return True


def _grant_start_items(session: dict[str, Any], encounter: dict[str, Any]) -> None:
    # The tutorial slips its items into the bag once, before the first round; the log stays quiet.
    grant = encounter.get("start_grant")
    if not isinstance(grant, dict) or not grant.get("flag"):
        return
    flags = session.setdefault("flags", {})
    if flags.get(grant["flag"]):
        return
    from .state import apply_state_delta
    apply_state_delta(session, {"inventory_add": [dict(item, silent=True) for item in grant.get("items", [])]})
    flags[grant["flag"]] = True


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
    if normalized_type not in {"attack", "skill", "item", "defend", "flee", "special"}:
        raise CombatError("不明な戦闘行動です。")

    _validate_player_ability(session, normalized_type, action_id, target_id)
    free_action = False
    passive_state = combat.get("passive_state", {})
    if progression.enabled(session):
        passive_state["action_followups"] = []
        if normalized_type == "skill":
            free_action = bool(_player_ability(session, "skill", action_id).get("free_action"))
        elif normalized_type == "item":
            ability = _player_ability(session, "item", action_id)
            free_action = (ability.get("consumable", True)
                           and passive_state.get("free_items_used", 0) < progression.effects(session).get("free_item_uses", 0))

    previous_events = combat.get("action_events")
    combat["action_events"] = []
    try:
        if status_effects.skip_action(session, session["character"], random_source):
            free_action = False
        elif normalized_type == "attack":
            _player_attack(session, target_id, random_source)
        elif normalized_type == "skill":
            _player_skill(session, action_id, target_id, random_source)
        elif normalized_type == "item":
            _player_item(session, action_id, target_id, random_source)
        elif normalized_type == "defend":
            _player_defend(session)
        elif normalized_type == "special":
            _player_special_action(session, action_id)
        else:
            _player_flee(session, random_source)
    except CombatError:
        if previous_events is None:
            combat.pop("action_events", None)
        else:
            combat["action_events"] = previous_events
        raise

    combat.setdefault("player_action_types", []).append(normalized_type)
    if free_action and normalized_type == "item":
        passive_state["free_items_used"] = passive_state.get("free_items_used", 0) + 1
    if combat.get("status") == "active":
        _check_victory_or_defeat(session)
    if combat.get("status") == "active":
        combat["actions_remaining"] = max(0, _safe_int(combat.get("actions_remaining"), 1) - int(not free_action))
    player_continues = combat.get("status") == "active" and _safe_int(combat.get("actions_remaining"), 0) > 0
    if combat.get("status") == "active" and not player_continues:
        status_effects.tick(session, session["character"], random_source)
        _check_victory_or_defeat(session)
    if combat.get("status") == "active" and not player_continues:
        _enemy_phase(session, random_source)
    if combat.get("status") == "active" and not player_continues:
        _check_victory_or_defeat(session)
    if combat.get("status") == "active" and not player_continues:
        _passive_round_end(session)
        _tick_cooldowns(session)
        combat["round"] = int(combat.get("round", 1)) + 1
        combat["turn"] = "player"
        combat["actions_remaining"] = _player_actions_per_round(session)
        _regenerate_round_resources(session)
        _apply_round_start_effects(session, random_source)
        _check_victory_or_defeat(session)
        max_rounds = int(_combat_rules(session).get("max_rounds", 100) or 100)
        if int(combat["round"]) > max_rounds:
            _finish_combat(session, "defeat", "長期戦に耐えきれず敗北した。")

    events = deepcopy(combat.get("action_events") or [])
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
        session["character"].pop("statuses", None)
    original_character = combat.get("original_character")
    if isinstance(original_character, dict):
        session["character"] = deepcopy(original_character)
    session["last_combat_result"] = result
    session["combat"] = None
    progression.initialize(session)
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
        "log": deepcopy(combat.get("log") or []),
        "pending_resolution": bool(combat.get("pending_resolution")),
        "result": deepcopy(combat.get("result")),
        "intro_text": str(combat.get("intro_text") or ""),
        "actions": [],
        "events": deepcopy(combat.get("action_events") or []),
        "presentation_state": _presentation_state(session),
    }
    if (combat.get("encounter") or {}).get("tutorial"):
        public["tutorial"] = {
            "player_actions": list(combat.get("player_action_types") or []),
            "enemy_skill_used": any(sum((enemy.get("skill_uses") or {}).values()) for enemy in combat.get("enemies") or []),
        }
    if combat.get("status") == "active":
        public["actions"] = combat_actions(session)
    definitions = session.get("scenario_pack", {}).get("status_defs", [])
    public["player_statuses"] = [status_effects.public(status, definitions) for status in session.get("character", {}).get("statuses", [])]
    for enemy in public["enemies"]:
        enemy["statuses"] = [{**status, **status_effects.public(status, definitions)} for status in enemy.get("statuses", [])]
    if _combat_rules(session).get("evade_model") == "dex" or _combat_rules(session).get("enemy_accuracy_override") is not None:
        for enemy, original in zip(public["enemies"], combat["enemies"]):
            for ability in enemy.get("skills", []):
                if _ability_kind(ability) == "attack":
                    ability["accuracy"] = attack_chance(session, original, session["character"], ability, original["id"])
    return public


def combat_actions(session: dict[str, Any]) -> list[dict[str, Any]]:
    character = session.get("character") if isinstance(session.get("character"), dict) else {}
    rules = _combat_rules(session)
    basic = _merge_dict(rules.get("basic_attack"), character.get("combat", {}).get("basic_attack") if isinstance(character.get("combat"), dict) else None)
    basic = _merge_dict(basic, _equipped_weapon_attack(character))
    basic_followups = equipped_basic_attack_followups(character)
    basic_followups += [deepcopy(m['basic_followup']) for m in (session.get('combat') or {}).get('active_modifiers', []) if m.get('basic_followup')]
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
        resolved_skill = _normal_skill(session, effective_ability(character, skill))
        cost = effective_ability_cost(character, skill)
        cost_type = str(skill.get("cost_type") or "").lower()
        available = _safe_int(character.get(cost_type), 0) if cost_type in {"mp", "sp", "hp"} else cost
        enabled = available >= cost
        if progression.enabled(session):
            enabled = _can_pay_cost(character, resolved_skill)
            costs = resolved_skill.get("_resolved_costs", {})
            cost = costs.get(cost_type, 0)
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
            **({"costs": resolved_skill.get("_resolved_costs", {}),
                "free_action": bool(resolved_skill.get("free_action"))} if progression.enabled(session) else {}),
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
            **({"icon": normalized["icon"]} if normalized.get("icon") else {}),
            "kind": spec.get("kind"),
            "enabled": True,
            **_combat_action_details(spec),
        })
    for special in (session.get("combat") or {}).get("encounter", {}).get("special_actions", []):
        if _special_action_available(session, special):
            item = _find_entry(character.get("inventory", []), special.get("cost_item", ""), "item")
            actions.append({**deepcopy(special), "type": "special", "enabled": True,
                            "cost_item_name": item.get("name", "") if item else ""})
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
    for action in actions:
        ability = (_player_ability(session, action["type"], action["id"])
                   if action["type"] in {"skill", "item"} else basic)
        if rules.get("evade_model") == "dex" and (action["type"] == "attack" or action.get("kind") in {"attack", "damage"}):
            action["hit_chance_by_target"] = {enemy["id"]: attack_chance(session, character, enemy, ability, "player")
                                               for enemy in _alive_enemies(session["combat"])}
        if action["type"] not in {"skill", "item"}:
            continue
        reason = _ability_disabled_reason(session, action["type"], action["id"], ability)
        if reason:
            action.update(enabled=False, disabled_reason=reason)
        remaining = _cooldown_remaining(session, action["type"], action["id"])
        if remaining:
            action["cooldown_remaining"] = remaining
        if ability.get("requires_target_weakness"):
            action["valid_target_ids"] = [enemy["id"] for enemy in _alive_enemies(session["combat"])
                                          if _target_requirement_passes(ability, enemy)]
            action["target_disabled_reason"] = _weakness_reason(ability)
    return actions


def _player_ability(session: dict[str, Any], action_type: str, action_id: str) -> dict[str, Any]:
    actor = session["character"]
    entry = _find_entry(_available_skills(actor) if action_type == "skill" else actor.get("inventory", []),
                        action_id, action_type)
    return _normal_skill(session, effective_ability(actor, entry)) if entry and action_type == "skill" else item_combat_spec(entry)


def _normal_skill(session: dict[str, Any], ability: dict[str, Any]) -> dict[str, Any]:
    if not progression.enabled(session):
        return ability
    result = deepcopy(ability)
    actor, passive = session["character"], progression.effects(session)
    result.update(passive.get("skill_overrides", {}).get(result.get("id"), {}))
    raw = result.get("costs", {result.get("cost_type", ""): result.get("cost", 0)})
    costs = {key: effective_ability_cost(actor, {**result, "cost_type": key, "cost": value})
             for key, value in raw.items() if key in {"hp", "mp", "sp"}}
    low = passive.get("low_hp", {})
    if low and _hp_ratio(actor) < low["ratio"]:
        costs = {key: math.ceil(value * low["cost_multiplier"]) for key, value in costs.items()}
        result["damage_multiplier"] = result.get("damage_multiplier", 1) * low["damage_multiplier"]
    if result.get("id") in passive.get("free_skills", []):
        costs["mp"] = 0
    exchange = passive.get("sp_for_mp")
    if exchange and costs.get("mp", 0):
        count = min(math.floor(costs["mp"] * exchange["max_ratio"]),
                    max(0, actor.get("sp", 0) - costs.get("sp", 0)) // exchange["rate"])
        costs["mp"] -= count
        costs["sp"] = costs.get("sp", 0) + count * exchange["rate"]
    result["_resolved_costs"] = costs
    return result


def _condition(session: dict[str, Any], condition: dict[str, Any], target: dict[str, Any]) -> bool:
    kind = condition.get("if")
    if kind == "any":
        return any(_condition(session, child, target) for child in condition["conditions"])
    if kind == "target_hp_full":
        return target.get("hp", 0) == target.get("max_hp")
    if kind == "target_hp_ratio_lte":
        return _hp_ratio(target) <= condition["ratio"]
    if kind == "single_enemy":
        return len(_alive_enemies(session["combat"])) == 1
    if kind == "target_boss":
        return status_effects.is_boss(session, target)
    if kind == "target_id_in":
        return target.get("template_id", target.get("id")) in condition["ids"]
    if kind == "target_max_hp_gte":
        return target.get("max_hp", 0) >= condition["value"]
    return False


def _learned_elements(actor: dict[str, Any], target: dict[str, Any], maximum: int) -> list[str]:
    spells = {s.get("id"): s for s in actor.get("skills", []) if s.get("spell_tier") == "basic"}
    elements = list(dict.fromkeys(spells[s]["element"] for s in actor.get("learned_spells", []) if s in spells))
    if len(elements) > maximum:
        elements.sort(key=lambda element: -_resistance_multiplier(target, element))
    return elements[:maximum]


def _prepare_spell(session: dict[str, Any], ability: dict[str, Any]) -> None:
    if not ability.get("spell_tier"):
        return
    actor = session["character"]
    for status in list(actor.get("statuses", [])):
        multiplier = status.get("modifiers", {}).get("next_spell_damage_multiplier")
        if status_effects.modern(status) and multiplier:
            ability["damage_multiplier"] = ability.get("damage_multiplier", 1) * multiplier
            status_effects.remove(actor, status)
    if ability.get("resonance_exempt"):
        return
    memory = session["combat"]["passive_state"]
    elements = ability.get("multi_elements") or [ability.get("element")]
    previous = memory.get("spell_elements")
    resonance = progression.effects(session).get("resonance")
    if resonance and previous and previous != elements:
        ability["damage_multiplier"] = ability.get("damage_multiplier", 1) * resonance["multiplier"]
        _restore_actor_resource(actor, "mp", resonance["refund"])
    memory["spell_elements"] = deepcopy(elements)


def _passive_attack(session: dict[str, Any], target: dict[str, Any], attack: dict[str, Any], rng: Any) -> None:
    if session["character"].get("hp", 0) > 0 and not _enemy_is_defeated(target):
        _resolve_attack(session, session["character"], target, {**attack, "status_followup": True}, "player", rng)


def _heal_overflow(session: dict[str, Any], overflow: int, ability: dict[str, Any], rng: Any) -> None:
    if not progression.enabled(session) or overflow <= 0:
        return
    actor = session["character"]
    shield = ability.get("overflow_shield")
    if shield:
        status_effects.apply(session, actor, {"id": shield["id"], "modifiers": {
            "shield": {"amount": overflow, "max_hp_ratio": shield["max_hp_ratio"]}}}, actor, rng)
    ratio = progression.effects(session).get("overflow_ratio", 0)
    targets = _alive_enemies(session["combat"])
    if ratio and targets:
        _passive_attack(session, rng.choice(targets), {"damage": str(round(overflow * ratio)),
                        "accuracy": 100, "element": "holy"}, rng)


def _passive_hit(session: dict[str, Any], target: dict[str, Any], ability: dict[str, Any], rng: Any) -> None:
    if not progression.enabled(session) or _enemy_is_defeated(target) or ability.get("status_on_hit"):
        return
    actor, passive = session["character"], progression.effects(session)
    if passive.get("hit_status"):
        status_effects.apply(session, target, passive["hit_status"], actor, rng)
    used = session["combat"].setdefault("passive_state", {}).setdefault("action_followups", [])
    followup = passive.get("hit_followup", {})
    if followup and "hit" not in used and (ability.get("_basic_action") and followup.get("basic")
                                         or ability.get("id") in followup.get("skills", [])):
        used.append("hit")
        attack = deepcopy(followup)
        if attack.get("weapon_half_dice"):
            weapon = _equipped_weapon_attack(actor)
            dice = re.search(r"(\d+)d(\d+)", weapon.get("damage", ""))
            attack["damage"] = f"{dice[1]}d{max(1, int(dice[2]) // 2)}" if dice else "0"
        _passive_attack(session, target, attack, rng)
    if (passive.get("weakness_followup") and "weakness" not in used
            and any(_resistance_multiplier(target, element) > 1 for element in target.get("resistances", {}))):
        used.append("weakness")
        _passive_attack(session, target, passive["weakness_followup"], rng)


def _enemy_reaction(session: dict[str, Any], enemy: dict[str, Any], rng: Any, *, missed: bool) -> None:
    if not progression.enabled(session):
        return
    passive, actor = progression.effects(session), session["character"]
    memory = session["combat"]["passive_state"]
    if missed and passive.get("miss_sp"):
        amount = min(passive["miss_sp"], max(0, passive["miss_sp_cap"] - memory.get("miss_sp", 0)))
        memory["miss_sp"] = memory.get("miss_sp", 0) + amount
        _restore_actor_resource(actor, "sp", amount)
    guarded = bool(session["combat"].get("player_status", {}).get("guard_multiplier"))
    guard_skill = next((s for s in actor.get("skills", []) if s.get("id") == memory.get("guard_skill")), {})
    if passive.get("counter_attack") and (missed or guarded and guard_skill.get("name") == "影隠れ"):
        _passive_attack(session, enemy, passive["counter_attack"], rng)


def _passive_round_start(session: dict[str, Any], rng: Any) -> None:
    if not progression.enabled(session):
        return
    battle, actor, passive = session["combat"], session["character"], progression.effects(session)
    memory = battle.setdefault("passive_state", {})
    memory["miss_sp"] = 0
    memory.pop("guard_skill", None)
    if actor.get("hp", 0) <= 0:
        return
    if battle["round"] <= passive.get("opening_rounds", 0):
        actor["sp"] += passive["opening_sp"]
    cycle = passive.get("mana_cycle")
    if cycle:
        amount = min(cycle["amount"], max(0, math.floor(actor["max_mp"] * cycle["cap_ratio"]) - memory.get("mana_restored", 0)))
        restored = _restore_actor_resource(actor, "mp", amount)
        memory["mana_restored"] = memory.get("mana_restored", 0) + restored
    regain = passive.get("shield_regain")
    if (regain and "shield_broken_round" in memory
            and battle["round"] - memory["shield_broken_round"] >= regain["every"]
            and memory.get("shield_regains", 0) < regain["max"]
            and not any(s.get("id") == "arcane_shield" for s in actor.get("statuses", []))):
        status_effects.apply(session, actor, regain["status"], actor, rng)
        memory["shield_regains"] = memory.get("shield_regains", 0) + 1
        memory.pop("shield_broken_round", None)
    attack = passive.get("round_attack")
    targets = _alive_enemies(battle)
    if attack and _hp_ratio(actor) > attack["hp_ratio_gt"] and targets:
        _passive_attack(session, rng.choice(targets), attack, rng)


def _passive_round_end(session: dict[str, Any]) -> None:
    if not progression.enabled(session) or session["character"].get("hp", 0) <= 0:
        return
    ratio = progression.effects(session).get("regen_ratio", 0)
    if ratio:
        memory, actor = session["combat"]["passive_state"], session["character"]
        value = memory.get("regen_fraction", 0) + actor["max_hp"] * ratio
        amount = math.floor(value + 1e-9)
        memory["regen_fraction"] = value - amount
        healed = _heal_actor(actor, amount)
        if healed:
            _log(session, "player", "heal", "【仮】", {"amount": healed})


def _weakness_reason(ability: dict[str, Any]) -> str:
    from .item_mechanics import element_label

    return WEAKNESS_REASON.format(element=element_label(ability["requires_target_weakness"]))


def _target_requirement_passes(ability: dict[str, Any], enemy: dict[str, Any]) -> bool:
    element = ability.get("requires_target_weakness")
    return not element or _resistance_multiplier(enemy, str(element)) > 1


def _cooldown_remaining(session: dict[str, Any], action_type: str, action_id: str) -> int:
    entry = (session.get("combat") or {}).get("cooldowns", {}).get(f"{action_type}:{action_id}", {})
    return max(0, int(entry.get("remaining", 0)))


def _start_cooldown(session: dict[str, Any], action_type: str, action_id: str, ability: dict[str, Any]) -> None:
    rounds = max(0, int(ability.get("cooldown", 0)))
    if rounds:
        session["combat"].setdefault("cooldowns", {})[f"{action_type}:{action_id}"] = {
            "remaining": rounds, "used_round": session["combat"]["round"],
        }


def _tick_cooldowns(session: dict[str, Any]) -> None:
    for entry in session["combat"].get("cooldowns", {}).values():
        if entry["used_round"] < session["combat"]["round"]:
            entry["remaining"] = max(0, entry["remaining"] - 1)


def _ability_disabled_reason(session: dict[str, Any], action_type: str, action_id: str,
                             ability: dict[str, Any], target_id: Optional[str] = None) -> str:
    remaining = _cooldown_remaining(session, action_type, action_id)
    if remaining:
        return COOLDOWN_REASON.format(rounds=remaining)
    if progression.enabled(session):
        if action_type == "skill" and not _can_pay_cost(session["character"], ability):
            return "【仮】リソースが不足しています。"
        uses = session["combat"].get("passive_state", {}).get("uses", {}).get(action_id, 0)
        if ability.get("max_uses_per_battle") is not None and uses >= ability["max_uses_per_battle"]:
            return "【仮】この戦闘ではこれ以上使用できません。"
    raw = ability.get("self_status")
    for spec in raw if isinstance(raw, list) else [raw]:
        identifier = spec if isinstance(spec, str) else (spec or {}).get("id")
        existing = next((status for status in session["character"].get("statuses", [])
                         if status.get("id") == identifier and status.get("no_reapply")), None)
        if existing:
            return STATUS_ACTIVE_REASON.format(name=existing["name"])
    if ability.get("requires_target_weakness"):
        enemies = _alive_enemies(session["combat"])
        if target_id is not None:
            enemies = [_target_enemy(session["combat"], target_id)]
        if not any(_target_requirement_passes(ability, enemy) for enemy in enemies):
            return _weakness_reason(ability)
    return ""


def _validate_player_ability(session: dict[str, Any], action_type: str, action_id: str, target_id: str) -> None:
    if action_type not in {"skill", "item"}:
        return
    ability = _player_ability(session, action_type, action_id)
    reason = _ability_disabled_reason(session, action_type, action_id, ability, target_id)
    if reason:
        raise CombatError(reason)


def _apply_utility_effects(session: dict[str, Any], actor: dict[str, Any], ability: dict[str, Any], rng: Any) -> None:
    if ability.get("cleanse"):
        status_effects.cleanse(session, actor, ability["cleanse"])
    raw = ability.get("self_status")
    for spec in raw if isinstance(raw, list) else [raw]:
        if spec:
            status_effects.apply(session, actor, spec, actor, rng)


def _special_action_available(session: dict[str, Any], action: dict[str, Any]) -> bool:
    from .state import _session_requirement_passes

    if not combat_is_active(session) or not _session_requirement_passes(action.get("requirements"), session):
        return False
    enemies = [enemy for enemy in _alive_enemies(session["combat"])
               if not action.get("enemy_id") or enemy["template_id"] == action["enemy_id"]]
    if not enemies or any(_hp_ratio(enemy) > action.get("enemy_hp_ratio_lte", 1) for enemy in enemies):
        return False
    actor = session["character"]
    if action.get("cost_item"):
        item = _find_entry(actor.get("inventory", []), action["cost_item"], "item")
        return item is not None and _safe_int(item.get("quantity"), 1) >= max(1, _safe_int(action.get("cost"), 1))
    resource = str(action.get("cost_type") or "")
    return not resource or _safe_int(actor.get(resource), 0) >= max(0, _safe_int(action.get("cost"), 0))


def _player_special_action(session: dict[str, Any], action_id: str) -> None:
    from .state import _effects_to_state_delta

    action = next((a for a in session["combat"]["encounter"].get("special_actions", [])
                   if a.get("id") == action_id), None)
    if action is None or not _special_action_available(session, action):
        raise CombatError("戦闘行動の条件を満たしていません。")
    actor = session["character"]
    if action.get("cost_item"):
        item = _find_entry(actor["inventory"], action["cost_item"], "item")
        for _ in range(max(1, _safe_int(action.get("cost"), 1))):
            _consume_inventory_item(actor, item)
    elif action.get("cost_type"):
        resource = action["cost_type"]
        actor[resource] -= max(0, _safe_int(action.get("cost"), 0))
    _finish_combat(session, action["outcome"], action["log_text"])
    session["combat"]["pending_state_delta"] = _effects_to_state_delta(action.get("effects", []), session)
    session["combat"]["result"]["prepared_text"] = action["log_text"]


def _combat_action_details(ability: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "damage", "healing", "max_hp_ratio", "accuracy", "element", "all_targets", "check",
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
    attack["_basic_action"] = True
    passive = progression.effects(session)
    if passive.get("basic_element"):
        attack.update(element=passive["basic_element"], fallback_element=passive.get("fallback_element", "physical"),
                      weakness_multiplier=passive.get("weak_multiplier", 1))
    _resolve_attack(session, character, target, attack, "player", rng)
    followups = equipped_basic_attack_followups(character) + [m['basic_followup'] for m in _encounter_modifiers(session, target) if m.get('basic_followup')]
    for followup in followups:
        if _enemy_is_defeated(target):
            break
        _resolve_attack(session, character, target, followup, "player", rng)


def _player_skill(session: dict[str, Any], skill_id: str, target_id: str, rng: Any) -> None:
    character = session["character"]
    skill = _find_entry(_available_skills(character), skill_id, "skill")
    if not skill:
        raise CombatError("技能が見つかりません。")
    resolved_skill = _normal_skill(session, effective_ability(character, skill))
    resolved_skill["_skill_action"] = True
    _validate_player_ability(session, "skill", skill_id, target_id)
    _pay_cost(character, resolved_skill)
    _start_cooldown(session, "skill", skill_id, resolved_skill)
    if progression.enabled(session):
        uses = session["combat"].setdefault("passive_state", {}).setdefault("uses", {})
        uses[skill_id] = uses.get(skill_id, 0) + 1
        _prepare_spell(session, resolved_skill)
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
    _apply_utility_effects(session, character, resolved_skill, rng)
    if kind == "heal":
        amount, detail = _roll_formula(str(resolved_skill.get("healing") or resolved_skill.get("dice_type") or "1d6+int/4"), character, rng)
        amount = max(0, int(round(amount * float(resolved_skill.get("healing_multiplier", 1) or 1))))
        if _equipped_effect(character, "healing_harms_humans") and not character.get("undead_parts"):
            amount = _round_received_damage(session, amount)
            character["hp"] = max(0, _safe_int(character.get("hp"), 0) - amount)
            _log(session, "player", "self_damage", f"呪われた治癒でHPを{amount}失った。", {"amount": amount, "formula": detail})
        else:
            healed = _heal_actor(character, amount)
            _heal_overflow(session, max(0, amount - healed), resolved_skill, rng)
            _log(session, "player", "heal", f"{resolved_skill.get('name', '技能')}でHPを{healed}回復した。", {"amount": healed, "formula": detail})
    elif kind == "restore":
        amount, detail = _roll_formula(str(resolved_skill.get("amount", "0")), character, rng)
        restored = _restore_actor_resource(character, resolved_skill.get("resource", "mp"), amount)
        _log(session, "player", "restore", "【仮】" + resolved_skill["name"], {"amount": restored, "formula": detail})
    elif kind == "defend":
        multiplier = float(resolved_skill.get("guard_multiplier", _combat_rules(session).get("defend_multiplier", 0.5)) or 0.5)
        session["combat"].setdefault("player_status", {})["guard_multiplier"] = max(0.0, min(1.0, multiplier))
        session["combat"]["player_status"]["survive_at_one"] = bool(resolved_skill.get("survive_at_one", True))
        if progression.enabled(session):
            session["combat"]["passive_state"]["guard_skill"] = skill_id
        _log(session, "player", "defend", f"{resolved_skill.get('name', '防御技能')}を使用し、守りを固めた。")
    elif kind == "stance":
        target = _target_enemy(session["combat"], target_id)
        if resolved_skill.get("immunity_from_target_element"):
            element = _primary_element(target)
            character["combat_immunities"] = [element]
            _log(session, "player", "stance", f"{resolved_skill.get('name', '構え')}で{element}属性を無効化した。", {"element": element})
    elif kind not in {"status", "cleanse"}:
        if resolved_skill.get("learned_elements"):
            target = _target_enemy(session["combat"], target_id)
            resolved_skill["multi_elements"] = _learned_elements(character, target, resolved_skill["max_hits"])
        if resolved_skill.get("multi_elements"):
            target = _target_enemy(session["combat"], target_id)
            resolved_skill["_target_snapshot"] = deepcopy(target)
        multi_elements = resolved_skill.get("multi_elements")
        if isinstance(multi_elements, list) and (multi_elements or resolved_skill.get("learned_elements")):
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
    _validate_player_ability(session, "item", item_id, target_id)
    kind = str(spec.get("kind") or "heal")
    if kind == "heal":
        if "max_hp_ratio" in spec:
            amount = int(character["max_hp"] * float(spec["max_hp_ratio"]))
            detail = {"max_hp_ratio": spec["max_hp_ratio"]}
        else:
            amount, detail = _roll_formula(str(spec.get("healing") or spec.get("formula") or "10"), character, rng)
        healed = _heal_actor(character, amount)
        _heal_overflow(session, max(0, amount - healed), spec, rng)
        _log(session, "player", "item", f"{item.get('name', '道具')}を使い、HPを{healed}回復した。", {"amount": healed, "formula": detail})
    elif kind == "restore":
        resource = str(spec.get("resource") or "mp").lower()
        if resource not in {"hp", "mp", "sp"}:
            raise CombatError("未対応の回復対象です。")
        amount, detail = _roll_formula(str(spec.get("amount") or spec.get("formula") or "10"), character, rng)
        restored = _restore_actor_resource(character, resource, amount)
        if resource == "hp":
            _heal_overflow(session, max(0, amount - restored), spec, rng)
        _log(
            session,
            "player",
            "item",
            f"{item.get('name', '道具')}を使い、{resource.upper()}を{restored}回復した。",
            {"resource": resource, "amount": restored, "formula": detail},
        )
    elif kind == "damage":
        targets = list(_alive_enemies(session["combat"])) if spec.get("all_targets") else [_target_enemy(session["combat"], target_id)]
        for target in targets:
            if _target_requirement_passes(spec, target):
                _resolve_attack(session, character, target, spec, "player", rng, display_name=str(item.get("name") or "道具"))
    elif kind in {"status", "cleanse"}:
        pass
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
            _log(session, "player", "status", f"{target.get('name', '敵')}が縮小した。", {"roll": roll, "chance": chance}, target=target)
        else:
            _log(session, "player", "miss", f"{item.get('name', '道具')}は効かなかった。", {"roll": roll, "chance": chance}, target=target)
    else:
        raise CombatError("未対応の道具効果です。")
    _apply_utility_effects(session, character, spec, rng)
    _start_cooldown(session, "item", item_id, spec)
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
        if enemy.get("skip_rounds_remaining", 0) > 0:
            enemy["skip_rounds_remaining"] -= 1
            if enemy["skip_rounds_remaining"] == 0 and enemy.get("skip_recovery_text"):
                _log(session, enemy["id"], "status", enemy["skip_recovery_text"], target=enemy)
            status_effects.tick(session, enemy, rng)
            continue
        if not status_effects.skip_action(session, enemy, rng):
            ability = _choose_enemy_ability(enemy, session, rng)
            _pay_cost(enemy, ability)
            _execute_enemy_ability(session, enemy, ability, rng)
        status_effects.tick(session, enemy, rng)
        if session.get("game_over"):
            break
    disabled_round = combat.get("player_status", {}).get("guard_disabled_round", 0)
    combat["player_status"] = {"guard_disabled_round": disabled_round} if disabled_round > combat["round"] else {}
    for actor in [session["character"], *combat.get("enemies", [])]:
        for status in list(actor.get("statuses", [])):
            if status_effects.modern(status) and status.get("expires") == "enemy_phase_end":
                status_effects.remove(actor, status)


def _execute_enemy_ability(session: dict[str, Any], enemy: dict[str, Any], ability: dict[str, Any], rng: Any) -> None:
    actor_id = str(enemy.get("id") or "enemy")
    if ability.get("element") == "current":
        ability = {**ability, "element": _primary_element(enemy)}
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
    elif kind == "defend":
        _apply_status(enemy, {"id": str(ability["id"]), "name": str(ability["name"]),
                              "guard_multiplier": ability.get("guard_multiplier", 0.5),
                              "remaining_rounds": int(ability.get("duration", 2)) + 1})
        _log(session, actor_id, "defend", f"{enemy.get('name')}は{ability['name']}で守りを固めた。")
    elif kind == "status" and ability.get("status_effect") == "break_guard":
        session["combat"].setdefault("player_status", {})["guard_disabled_round"] = session["combat"]["round"] + 1
        _log(session, actor_id, "status", f"{enemy.get('name')}は{ability['name']}を使用した。", target=session["character"])
    elif kind == "stance":
        if ability.get("immunity_from_target_element"):
            element = _primary_element(session["character"])
            enemy["combat_immunities"] = [element]
            _log(session, actor_id, "stance", f"{ability.get('name', '構え')}で{element}属性を無効化した。", {"element": element})
    elif isinstance(ability.get("multi_elements"), list) and ability["multi_elements"]:
        for element in ability["multi_elements"]:
            for _ in range(max(1, _safe_int(ability.get("hits_per_element"), 1))):
                if session["character"]["hp"] <= 0:
                    return
                strike = {**ability, "element": str(element)}
                _resolve_attack(session, enemy, session["character"], strike, actor_id, rng,
                                f"{ability.get('name')}・{element}")
    else:
        for _ in range(max(1, int(ability.get('hits', 1)))):
            if session['character']['hp'] <= 0:
                break
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
    if defender is session.get('character'):
        damage = _modified_received_damage(session, damage, element, attacker, name)
    defender["hp"] = max(0, _safe_int(defender.get("hp"), 0) - damage)
    _log(session, str(attacker.get("id") or "enemy"), "field_damage", f"{name}が{damage}ダメージを与えた。", {"damage": damage, "formula": detail, "element": element}, target=defender)


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
) -> int:
    name = display_name or str(ability.get("name") or "攻撃")
    true_damage = bool(ability.get("true_damage"))
    chance = attack_chance(session, attacker, defender, ability, actor_id)
    hit_roll = rng.randint(1, 100)
    defender_name = str(defender.get("name") or "敵")
    if hit_roll > chance:
        _log(session, actor_id, "miss", f"{name}は{defender_name}に当たらなかった。", {"roll": hit_roll, "chance": chance, "element": ability.get("element", "physical")}, target=defender)
        if defender is session.get("character"):
            _enemy_reaction(session, attacker, rng, missed=True)
        return 0

    formula = str(ability.get("damage") or ability.get("dice_type") or "1d4")
    raw_damage, detail = _roll_formula(formula, attacker, rng)
    snapshot = ability.get("_target_snapshot", defender)
    for bonus in ability.get("conditional_bonus", []):
        if _condition(session, bonus, snapshot):
            extra, _ = _roll_formula(bonus["damage"], attacker, rng)
            raw_damage += extra
    for condition in ability.get("conditional_multipliers", []):
        if (not condition.get("element") or condition["element"] == ability.get("element")) and _condition(session, condition, snapshot):
            raw_damage *= condition["x"]
    raw_damage = max(0, int(round(raw_damage * float(ability.get("damage_multiplier", 1) or 1))))
    if not ability.get("true_damage"):
        if not progression.enabled(session) and actor_id == "player" and ability.get("_skill_action") and ability.get("element") not in {None, "physical"} and not ability.get("status_followup"):
            for status in list(attacker.get("statuses", [])):
                multiplier = status.get("modifiers", {}).get("next_spell_damage_multiplier")
                if status_effects.modern(status) and multiplier:
                    raw_damage = max(0, round(raw_damage * float(multiplier)))
                    status_effects.remove(attacker, status)
    element = str(ability.get("element") or "physical")
    if element == "counter":
        element = counter_attack_element(defender)
    elif element == "weakness":
        element = weakness_attack_element(defender)
        if _resistance_multiplier(defender, element) <= 1:
            element = ability.get("fallback_element", element)
    multiplier = _resistance_multiplier(defender, element)
    if ability.get("ignores_resistance"):
        multiplier = max(1.0, multiplier)
    if multiplier > 1:
        raw_damage *= ability.get("weakness_multiplier", 1)
    defense = _actor_defense(defender)
    passive = progression.effects(session)
    if actor_id == "player":
        penetration = passive.get("physical_penetration", 0) if element == "physical" or ability.get("_basic_action") else 0
        if penetration:
            defense *= 1 - penetration
        if element == "physical" and multiplier < 1:
            multiplier += (1 - multiplier) * penetration
    elif defender is session.get("character") and passive.get("armor_bonus"):
        armor = [item_combat_spec(item) for item in equipped_items(defender) if item.get("slot") == "armor"]
        if any(spec.get("defense", 0) >= passive.get("armor_min", 1) for spec in armor):
            defense += passive["armor_bonus"]
    if defender is not session.get('character'):
        defense = max(0, defense + sum(int(m.get('enemy_defense', 0)) for m in _encounter_modifiers(session, defender)))
    if ability.get("ignores_defense"):
        defense = 0
    damage = damage_after_defense(raw_damage, multiplier, defense, _combat_rules(session))
    if not isinstance(damage, int):
        damage = round(damage)
    if ability.get("status_on_hit"):
        damage = 0
    if actor_id == "player" and not true_damage:
        encounter_class = defender.get("encounter_class", session["combat"].get("encounter", {}).get("encounter_class"))
        damage = round(damage * passive.get("encounter_damage", {}).get(encounter_class, 1))
    if not true_damage:
        damage = max(0, round(damage * status_effects.product(attacker, "damage_dealt_multiplier")))
    if true_damage:
        # True damage always hits and ignores defense, resistances, guarding and damage modifiers.
        damage = raw_damage
    elif defender is session.get("character"):
        damage = _modified_received_damage(session, damage, element, attacker, ability.get('name', ''), ability.get('id', ''))
        unguarded_damage = damage
        status = session["combat"].get("player_status") or {}
        guard = float(status.get("guard_multiplier", 1.0) or 1.0)
        if status.get("guard_disabled_round", 0) >= session["combat"]["round"]:
            guard = 1.0
        damage = max(0, int(round(damage * guard)))
    else:
        for status in defender.get("statuses", []):
            damage = max(0, int(round(damage * float(status.get("guard_multiplier", 1.0)))))
    if not true_damage:
        received = max(.25, status_effects.product(defender, "received_damage_multiplier"))
        if defender is session.get("character") and status_effects.modifiers(defender, "received_damage_multiplier"):
            damage = max(0, round(unguarded_damage * max(.25, guard * received)))
        else:
            damage = max(0, round(damage * received))
        had_shield = any(s.get("id") == "arcane_shield" for s in defender.get("statuses", []))
        damage = status_effects.absorb(defender, damage)
        if defender is session.get("character"):
            if had_shield and not any(s.get("id") == "arcane_shield" for s in defender.get("statuses", [])) and progression.enabled(session):
                session["combat"]["passive_state"]["shield_broken_round"] = session["combat"]["round"]
            diverted = min(defender.get("mp", 0), math.floor(damage * passive.get("mana_armor", 0) + .5))
            if diverted:
                defender["mp"] -= diverted
            damage -= diverted
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
        f"{name}が{defender_name}に{damage}{'光属性' if element == 'holy' else ''}ダメージ{'（防御無視）' if true_damage else ''}。",
        {"damage": damage, "raw_damage": raw_damage, "formula": detail, "element": element, "hit_roll": hit_roll, "hit_chance": chance,
         "weakness": multiplier > 1 or ability.get("element") == "weakness" or bool(ability.get("multi_elements"))},
        target=defender,
    )
    status_spec = ability.get("on_hit_status")
    if isinstance(status_spec, dict) and (damage > 0 or ability.get("status_on_hit")):
        if passive.get("hit_status") and status_spec.get("id") == passive["hit_status"]["id"]:
            status_spec = {**status_spec, "max_stacks": passive["hit_status"].get("max_stacks", 3)}
        recipient = attacker if status_spec.get("target") == "self" else defender
        if ("damage" in status_spec or "remaining_rounds" in status_spec or "accuracy_penalty" in status_spec) and "kind" not in status_spec:
            chance = max(0, min(100, int(status_spec.get("chance", 100))))
            if chance == 100 or (chance > 0 and rng.randint(1, 100) <= chance):
                _apply_status(recipient, status_spec)
                _log(session, actor_id, "status", f"{recipient.get('name', defender_name)}は{status_spec.get('name') or status_spec.get('id') or '状態異常'}を受けた。",
                     {"status": deepcopy(status_spec)}, target=recipient)
        else:
            status_effects.apply(session, recipient, status_spec, attacker, rng)
    self_damage = max(0, _safe_int(ability.get("self_damage"), 0))
    if self_damage and attacker is session.get("character"):
        self_damage = _round_received_damage(session, self_damage)
        attacker["hp"] = max(0, _safe_int(attacker.get("hp"), 0) - self_damage)
        _log(session, actor_id, "self_damage", f"反動でHPを{self_damage}失った。", {"damage": self_damage})
    if defender is not session.get("character") and damage > 0:
        _trigger_enemy_auto_abilities(session, defender, rng)
    actual_damage = max(0, min(damage, before_hp)) if not _negative_undead(defender) else 0
    status_effects.after_damage(session, defender, actual_damage)
    if actor_id == "player" and (ability.get("_basic_action") or ability.get("_skill_action")) and not ability.get("status_followup"):
        _passive_hit(session, defender, ability, rng)
    elif defender is session.get("character") and not ability.get("status_followup"):
        _enemy_reaction(session, attacker, rng, missed=False)
    if actor_id == "player" and (ability.get("_basic_action") or ability.get("_skill_action")) and actual_damage > 0 and not ability.get("status_followup") and not _enemy_is_defeated(defender):
        for status in list(defender.get("statuses", [])):
            followup = status.get("modifiers", {}).get("on_damage_followup")
            if status_effects.modern(status) and followup:
                _resolve_attack(session, attacker, defender, {**followup, "status_followup": True}, actor_id, rng, status["name"])
    return actual_damage


def attack_chance(session: dict[str, Any], attacker: dict[str, Any], defender: dict[str, Any],
                  ability: dict[str, Any], actor_id: str) -> int:
    if ability.get("true_damage"):
        return 100
    if actor_id == "player" and progression.enabled(session):
        if ability.get("status_followup") or session["combat"]["round"] <= progression.effects(session).get("opening_rounds", 0):
            return 100
    accuracy = _safe_int(ability.get("accuracy"), 90 if actor_id == "player" else 85)
    override = _combat_rules(session).get("enemy_accuracy_override")
    if override is not None and any(attacker is enemy for enemy in session["combat"].get("enemies", [])):
        accuracy = int(override)
    if defender is session.get("character"):
        accuracy += sum(int(modifier.get("accuracy", 0)) for modifier in _encounter_modifiers(session, attacker)
                        if modifier.get("enemy_skill") in (ability.get("id"), ability.get("name")))
    accuracy -= sum(_safe_int(status.get("accuracy_penalty"), 0) for status in attacker.get("statuses", []))
    accuracy -= sum(int(value) for value in status_effects.modifiers(attacker, "accuracy_penalty"))
    return max(5, min(100, accuracy - actor_evade(session, defender)))


def actor_evade(session: dict[str, Any], actor: dict[str, Any]) -> int:
    rules = _combat_rules(session)
    if rules.get("evade_model") == "dex":
        formula = rules["evade_formula"]
        cap = float(actor.get("combat", {}).get("evade_cap", formula["cap"]))
        base = max(0, min(cap, round((float(actor.get("attributes", {}).get("dex", 0)) - float(formula["base"])) * float(formula["per_dex"]))))
    else:
        base = _safe_int((actor.get("combat") or {}).get("evade", actor.get("evade", 0)), 0)
    bonus = sum(float(value) for value in status_effects.modifiers(actor, "evade_bonus"))
    if actor is session.get("character"):
        bonus += progression.effects(session).get("evade_bonus", 0)
    if rules.get("evade_model") == "fixed" and not bonus:
        return base
    return max(0, min(int(rules["total_evade_cap"]), round(base + bonus)))


def damage_after_defense(raw: float, multiplier: float, defense: int, rules: dict[str, Any]) -> int:
    if multiplier <= 0:
        return 0
    scaled = raw * multiplier
    mode = rules.get("defense_mode", "flat")
    if mode == "floor":
        return max(math.ceil(scaled * float(rules.get("floor_ratio", 0.25))), round(scaled) - defense)
    if mode == "ratio":
        k = float(rules.get("k", 10))
        return max(1, round(scaled * k / (k + defense)))
    if mode != "flat":
        raise CombatError(f"Unknown defense_mode: {mode}")
    return max(1, round(scaled) - defense)


def _check_victory_or_defeat(session: dict[str, Any]) -> None:
    combat = session["combat"]
    if _safe_int(session["character"].get("hp"), 0) <= 0:
        _finish_combat(session, "defeat", "プレイヤーは戦闘不能になった。")
        return
    enemies = combat.get("enemies") or []
    catalog = {enemy["id"]: enemy for enemy in session.get("scenario_pack", {}).get("enemies", [])}
    for index, enemy in enumerate(enemies):
        if not _enemy_is_defeated(enemy) or not enemy.get("next_phase"):
            continue
        template = catalog.get(enemy["next_phase"])
        if template is None:
            raise CombatError(f"Unknown next_phase: {enemy['next_phase']}")
        replacement = _runtime_enemy(template, index)
        replacement["hp"] = replacement["max_hp"]
        combat.setdefault("completed_phases", []).append(deepcopy(enemy))
        enemies[index] = replacement
        combat.setdefault("phase_transitions", []).append(
            {"round": combat["round"], "from": enemy["template_id"], "to": replacement["template_id"]})
        _log(session, "system", "phase_transition", str(enemy.get("phase_transition_text") or ""),
             {"from": enemy["template_id"], "to": replacement["template_id"],
              "from_id": enemy["id"], "replacement": deepcopy(replacement)}, target=replacement)
        _activate_phase_allies(session)
        _activate_encounter_modifiers(session)
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
        from .state import _session_requirement_passes

        for event in (combat.get("encounter") or {}).get("victory_events", []):
            if _session_requirement_passes(event.get("requirements"), session):
                result["prepared_text"] = "\n".join(filter(None, [result.get("prepared_text"), event["text"]]))
        defeated_phases = [*combat.get("completed_phases", []), *enemies]
        delta = _victory_delta(session, defeated_phases, combat.get("encounter") or {})
        combat["pending_state_delta"] = delta
        result["rewards"] = deepcopy(delta)
        if isinstance(delta.get("game_over"), dict):
            result["prepared_text"] = delta["game_over"]["reason"]
        flags = session.setdefault("flags", {})
        for enemy in defeated_phases:
            template_id = str(enemy.get("template_id") or enemy.get("id") or "")
            if template_id:
                flags[_defeated_flag(template_id, str(combat.get("location_id") or ""))] = True
    elif status == "defeat":
        defeat_delta = deepcopy((combat.get("encounter") or {}).get("defeat_effects") or {})
        if not isinstance(defeat_delta, dict):
            defeat_delta = {}
        # Continuing after defeat requires an explicit scripted destination.
        if not any(defeat_delta.get(key) for key in ("game_over", "current_location", "current_scene")):
            defeat_delta.pop("hp_change", None)
            defeat_delta.pop("restore_full", None)
            defeat_delta.update({"hp": 0, "game_over": {
                "reason": summary, "ending": "combat_defeat",
            }})
        combat["pending_state_delta"] = defeat_delta
        if isinstance(defeat_delta.get("game_over"), dict) and (combat.get("encounter") or {}).get("encounter_class") != "scripted_loss":
            defeat_delta["game_over"]["combat_defeat"] = True
    from .npc_combat import aftermath

    npc_delta, npc_texts = aftermath(session, combat)
    if npc_delta:
        combat["pending_state_delta"] = _merge_combat_deltas(combat.get("pending_state_delta", {}), npc_delta)
        result["npc_aftermath"] = npc_texts
    combat["result"] = result
    _log(session, "system", status, summary)
    for actor in [session["character"], *enemies]:
        status_effects.clear(actor)
    if progression.enabled(session):
        session["character"]["sp"] = min(session["character"]["sp"], session["character"]["max_sp"])
        combat.pop("passive_state", None)


def _victory_delta(session: dict[str, Any], enemies: list[dict[str, Any]], encounter: dict[str, Any]) -> dict[str, Any]:
    from .state import _effects_to_state_delta

    delta: dict[str, Any] = {"gold_change": _safe_int(encounter.get("victory_gold_bonus"), 0),
                           "inventory_add": [], "flags_set": []}
    for enemy in enemies:
        rewards = enemy.get("rewards") if isinstance(enemy.get("rewards"), dict) else {}
        delta["gold_change"] += _safe_int(rewards.get("gold"), 0)
        delta["inventory_add"].extend(deepcopy(rewards.get("items") or []))
        delta["flags_set"].extend(str(flag) for flag in (rewards.get("flags") or []) if flag)
        template_id = str(enemy.get("template_id") or enemy.get("id") or "")
        if template_id:
            delta["flags_set"].append(_defeated_flag(template_id, current_location_id(session)))
    extra = deepcopy(encounter.get("victory_effects")) if isinstance(encounter.get("victory_effects"), dict) else {}
    if isinstance(encounter.get("victory_effects"), list):
        extra = _effects_to_state_delta(encounter["victory_effects"], session)
    extra = _merge_combat_deltas(extra, _effects_to_state_delta(encounter.get("victory_bonus_effects", []), session))
    if encounter.get("encounter_class") not in {"scripted_loss", "guest"}:
        extra = _merge_combat_deltas(extra, one_time_reward(session, encounter.get("one_time_reward", {})))
        extra = _merge_combat_deltas(extra, one_time_reward(session, encounter.get("victory_reward", {})))
    by_character = encounter.get("victory_effects_by_character")
    character = session.get("character", {}) if isinstance(session.get("character"), dict) else {}
    character_id = str(character.get("id") or character.get("character_id") or "")
    if isinstance(by_character, dict) and isinstance(by_character.get(character_id), dict):
        extra = _merge_combat_deltas(extra, by_character[character_id])
    delta["gold_change"] += _safe_int(extra.get("gold_change"), 0)
    delta["inventory_add"].extend(deepcopy(extra.get("inventory_add") or []))
    delta["flags_set"].extend(str(flag) for flag in (extra.get("flags_set") or []) if flag)
    if encounter.get("encounter_class") not in {"scripted_loss", "guest"}:
        delta["inventory_add"].extend(deepcopy(enemy["loot"]) for enemy in enemies if enemy.get("loot"))
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
    if progression.enabled(session):
        category = encounter.get("encounter_class", "unclassified")
        rewards = session["scenario_pack"]["progression"]["exp_rewards"]
        amount = rewards.get(category, rewards["unclassified"])
        if amount:
            delta["_exp_reward"] = {"amount": amount, "source": "combat:" + str(session["combat"].get("id", ""))}
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
        maximum = _safe_int(character.get("max_sp"), 0)
        if progression.enabled(session):
            maximum = max(maximum, character.get("sp", 0))
        character["sp"] = min(maximum, _safe_int(character.get("sp"), 0) + amount)


def _apply_round_start_effects(session: dict[str, Any], rng: Any) -> None:
    combat = session.get("combat")
    if not isinstance(combat, dict) or combat.get("status") != "active":
        return
    combat["round_received_multiplier"] = 1.0
    _passive_round_start(session, rng)
    companion = session.get("companion") if isinstance(session.get("companion"), dict) else {}
    if (combat.get("encounter") or {}).get("disable_companion"):
        companion = {}
    # Round protection must cover fields and statuses before offensive ally effects run.
    _apply_ally_round_start_effects(session, companion, rng, protection_only=True)
    for ally in combat.get("phase_allies", []):
        _apply_ally_round_start_effects(session, ally, rng, str(ally["id"]), protection_only=True)
    for enemy in _alive_enemies(combat):
        cycle = enemy.get("resistance_cycle", {})
        phases = cycle.get("phases", [])
        if phases:
            index = ((combat["round"] - 1) // max(1, int(cycle.get("every", 2)))) % len(phases)
            phase = phases[index]
            if enemy.get("resistance_phase") != index:
                previous = enemy.get("resistance_phase")
                enemy.update(resistance_phase=index, resistances=deepcopy(phase["resistances"]), element=phase["element"])
                if previous is not None:
                    _log(session, enemy["id"], "resistance_cycle", cycle["log"].replace("<色>", phase["name"]))
    _apply_enemy_fields(session, rng)
    _tick_enemy_statuses(session, rng)
    if combat.get("status") != "active":
        return
    _apply_ally_round_start_effects(session, companion, rng)
    for ally in combat.get("phase_allies", []):
        _apply_ally_round_start_effects(session, ally, rng, str(ally["id"]))
    for enemy in _alive_enemies(combat):
        for modifier in _encounter_modifiers(session, enemy):
            attack = modifier.get('round_start_attack')
            if isinstance(attack, dict):
                _resolve_attack(session, modifier, enemy, attack, str(modifier['id']), rng)
                if _enemy_is_defeated(enemy):
                    break
    _check_victory_or_defeat(session)


def _activate_phase_allies(session: dict[str, Any]) -> None:
    from .state import _session_requirement_passes

    battle = session["combat"]
    enemies = _alive_enemies(battle)
    candidates = [*battle["encounter"].get("phase_allies", []),
                  *(ally for enemy in enemies for ally in enemy.get("phase_allies", []))]
    active = []
    for ally in candidates:
        if ally.get("enemy_ids") and not any(e["template_id"] in ally["enemy_ids"] for e in enemies):
            continue
        if not _session_requirement_passes(ally.get("requirements"), session):
            continue
        if any(a["id"] == ally["id"] for a in active):
            continue
        active.append(deepcopy(ally))
        if not any(a["id"] == ally["id"] for a in battle.get("phase_allies", [])):
            _log(session, ally["id"], "phase_ally", ally.get("entry_text", ""))
    battle["phase_allies"] = active


def _encounter_modifiers(session: dict[str, Any], enemy: dict[str, Any]) -> list[dict[str, Any]]:
    return [m for m in session.get('combat', {}).get('active_modifiers', [])
            if not m.get('enemy_ids') or enemy.get('template_id') in m['enemy_ids']]


def _activate_encounter_modifiers(session: dict[str, Any]) -> None:
    from .state import _session_requirement_passes

    battle = session['combat']
    active = []
    for modifier in battle['encounter'].get('encounter_modifiers', []):
        if modifier.get('enemy_ids') and not any(e['template_id'] in modifier['enemy_ids'] for e in _alive_enemies(battle)):
            continue
        if not _session_requirement_passes(modifier.get('requirements'), session):
            continue
        active.append(deepcopy(modifier))
        if 'enemy_skip_rounds' in modifier:
            for enemy in _alive_enemies(battle):
                if modifier.get('enemy_ids') and enemy['template_id'] not in modifier['enemy_ids']:
                    continue
                applied = enemy.setdefault('applied_skip_modifiers', [])
                if modifier['id'] not in applied:
                    enemy['skip_rounds_remaining'] = max(enemy.get('skip_rounds_remaining', 0),
                                                        int(modifier['enemy_skip_rounds']))
                    enemy['skip_recovery_text'] = modifier.get('recovery_text', '')
                    applied.append(modifier['id'])
        if 'enemy_hp_multiplier' in modifier:
            for enemy in _alive_enemies(battle):
                if modifier.get('enemy_ids') and enemy['template_id'] not in modifier['enemy_ids']:
                    continue
                applied = enemy.setdefault('applied_hp_modifiers', [])
                if modifier['id'] in applied:
                    continue
                multiplier = float(modifier['enemy_hp_multiplier'])
                enemy['max_hp'] = max(1, int(round(enemy['max_hp'] * multiplier)))
                enemy['hp'] = min(enemy['max_hp'], max(1, int(round(enemy['hp'] * multiplier))))
                applied.append(modifier['id'])
        seen = battle.setdefault('announced_modifiers', [])
        if modifier['id'] not in seen:
            _log(session, modifier['id'], 'support', modifier['text'])
            seen.append(modifier['id'])
    battle['active_modifiers'] = active


def _modified_received_damage(session: dict[str, Any], damage: int, element: str,
                              enemy: dict[str, Any], name: str, skill_id: str = '') -> int:
    multiplier = progression.effects(session).get("taken_elements", {}).get(element, 1.0)
    for modifier in _encounter_modifiers(session, enemy):
        if modifier.get('received_element') == element:
            multiplier *= float(modifier.get('received_multiplier', 1))
        if modifier.get('enemy_skill') in (name, skill_id):
            multiplier *= float(modifier.get('damage_multiplier', 1))
    reduction = 0
    from .state import _session_requirement_passes

    for spec in equipped_item_specs(session['character']):
        conditional = spec.get('conditional_defense', {})
        if (conditional and _session_requirement_passes(conditional.get('requirements'), session)
                and (not conditional.get('location_ids') or current_location_id(session) in conditional['location_ids'])
                and (not conditional.get('enemy_ids') or enemy.get('template_id') in conditional['enemy_ids'])):
            reduction += int(conditional.get('amount', 0))
    damage = max(0, int(round(damage * multiplier)) - reduction)
    return _round_received_damage(session, damage)


def _round_received_damage(session: dict[str, Any], damage: int, element: str | None = None) -> int:
    multiplier = float((session.get("combat") or {}).get("round_received_multiplier", 1.0))
    if element:
        multiplier *= progression.effects(session).get("taken_elements", {}).get(element, 1.0)
    return max(0, int(round(damage * multiplier)))


def _apply_ally_round_start_effects(session: dict[str, Any], companion: dict[str, Any], rng: Any,
                                  actor_id: str = "companion", *, protection_only: bool = False) -> None:
    from .state import _session_requirement_passes

    combat = session["combat"]
    # Freeze eligibility before healing can cross a conditional HP threshold.
    effects = [effect for effect in companion.get("round_start_effects") or []
               if isinstance(effect, dict) and _session_requirement_passes(effect.get("requirements"), session)]
    previous_damage = 0
    for effect in effects:
        every = max(1, _safe_int(effect.get("every_n_rounds"), 1))
        if int(combat.get("round", 1)) % every:
            continue
        kind = str(effect.get("kind") or "")
        if (kind == "received_damage_multiplier") != protection_only:
            continue
        if kind == "received_damage_multiplier":
            multiplier = max(0.0, float(effect.get("multiplier", 1.0)))
            combat["round_received_multiplier"] = combat.get("round_received_multiplier", 1.0) * multiplier
            _log(session, actor_id, "support", str(effect.get("name") or companion.get("name") or "同行者"),
                 {"received_damage_multiplier": multiplier, "round": combat["round"]}, target=session["character"])
        if kind == "heal_player":
            if companion.get("id") in combat["encounter"].get("disable_companion_healing", []):
                continue
            if effect.get("scale_from_damage"):
                scale = effect["scale_from_damage"]
                amount = max(0, int(math.floor(previous_damage * float(scale["ratio"]) + .5)))
                detail = {"scale_from_damage": deepcopy(scale), "damage": previous_damage}
            elif "max_hp_ratio" in effect:
                ratio = max(0.0, float(effect["max_hp_ratio"]))
                amount = int(math.floor(session["character"]["max_hp"] * ratio + 0.5))
                detail = {"max_hp_ratio": ratio}
            else:
                amount, detail = _roll_formula(str(effect.get("amount") or "0"), session["character"], rng)
            healed = _heal_actor(session["character"], amount)
            if healed > 0:
                name = effect.get("name") or companion.get("name", "同行者")
                _log(session, actor_id, "heal", f"{name}がHPを{healed}回復した。", {"amount": healed, "formula": detail})
        elif kind == "damage_enemy":
            previous_damage = 0
            targets = list(_alive_enemies(combat))
            if not effect.get("all_targets") and targets:
                if effect.get("random_target"):
                    targets = [rng.choice(targets)]
                elif (effect.get("target") in {"highest_hp", "undead_first"}
                      or str(effect.get("target", "")).startswith("weak_to:")):
                    if effect["target"] == "undead_first":
                        targets = [enemy for enemy in targets if "undead" in enemy.get("tags", [])] or targets
                    elif effect["target"].startswith("weak_to:"):
                        element = effect["target"].split(":", 1)[1]
                        targets = [enemy for enemy in targets if _resistance_multiplier(enemy, element) > 1] or targets
                    targets = [max(targets, key=lambda enemy: _safe_int(enemy.get("hp"), 0))]
                else:
                    targets = targets[:1]
            for target in targets:
                ability = {
                    "name": str(effect.get("name") or companion.get("name") or "同行者の攻撃"),
                    "damage": str(effect.get("damage") or "1"),
                    "accuracy": 100,
                    "element": str(effect.get("element") or "physical"),
                }
                actual = _resolve_attack(session, companion, target, ability, actor_id, rng)
                if _resistance_multiplier(target, ability["element"]) >= 1:
                    previous_damage += actual


def _tick_enemy_statuses(session: dict[str, Any], rng: Any) -> None:
    for enemy in [*_alive_enemies(session["combat"]), session["character"]]:
        active_statuses: list[dict[str, Any]] = []
        for status in enemy.get("statuses") or []:
            if not isinstance(status, dict):
                continue
            if status_effects.modern(status):
                active_statuses.append(status)
                continue
            stacks = max(1, _safe_int(status.get("stacks"), 1))
            damage, detail = _roll_formula(str(status.get("damage") or "0"), session["character"], rng)
            damage = max(0, damage * stacks)
            if enemy is session.get("character"):
                damage = _round_received_damage(session, damage, status.get("element"))
            if damage:
                next_hp = _safe_int(enemy.get("hp"), 0) - damage
                enemy["hp"] = next_hp if _negative_undead(enemy) else max(0, next_hp)
                _log(
                    session,
                    "status",
                    "status_damage",
                    f"{enemy.get('name', '敵')}は{status.get('name') or status.get('id') or '状態異常'}で{damage}ダメージを受けた。",
                    {"damage": damage, "stacks": stacks, "formula": detail},
                    target=enemy,
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
    _log(session, actor_id, "status", f"{part}が永久に亡霊化しました。", {"part": part, "count": len(parts)}, target=character)


def _encounter_for_session(session: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    if session.get("npc_encounter_override"):
        return deepcopy(session["npc_encounter_override"])
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
    from .state import _session_requirement_passes

    for variant in encounter.get("enemy_variants", []):
        if _session_requirement_passes(variant.get("requirements"), session):
            encounter["enemy_ids"] = deepcopy(variant["enemy_ids"])
            break
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
    disabled = {skill for modifier in _encounter_modifiers(session, enemy)
                for skill in modifier.get('disabled_enemy_skills', [])}
    for skill in enemy.get("skills") or []:
        if not isinstance(skill, dict) or not _can_pay_cost(enemy, skill):
            continue
        if skill.get('id') in disabled or skill.get('name') in disabled:
            continue
        skill_key = str(skill.get("id") or skill.get("name") or "")
        uses = enemy.setdefault("skill_uses", {})
        limit = skill.get("max_uses_per_battle")
        if limit is not None and _safe_int(uses.get(skill_key), 0) >= _safe_int(limit, 0):
            continue
        if skill.get("use_on_round") is not None:
            if _safe_int(session["combat"]["round"], 1) != _safe_int(skill["use_on_round"], 1):
                continue
            uses[skill_key] = _safe_int(uses.get(skill_key), 0) + 1
            return deepcopy(skill)
        if skill.get("every_n_rounds"):
            if session["combat"]["round"] % int(skill["every_n_rounds"]):
                continue
            return deepcopy(skill)
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
            chosen = rng.choices(affordable, weights=weights, k=1)[0]
        else:
            chosen = affordable[rng.randint(0, len(affordable) - 1)]
        if chosen.get("max_uses_per_battle") is not None:
            key = str(chosen.get("id") or chosen.get("name") or "")
            enemy["skill_uses"][key] = _safe_int(enemy["skill_uses"].get(key), 0) + 1
        return deepcopy(chosen)
    enemy_combat = enemy.get("combat") if isinstance(enemy.get("combat"), dict) else {}
    return _merge_dict(_combat_rules(session).get("enemy_basic_attack"), enemy_combat.get("basic_attack"))


def _pay_cost(actor: dict[str, Any], ability: dict[str, Any]) -> None:
    if not _can_pay_cost(actor, ability):
        raise CombatError("リソースが不足しています。")
    if "_resolved_costs" in ability or "costs" in ability:
        for resource, cost in ability.get("_resolved_costs", ability.get("costs", {})).items():
            actor[resource] -= cost
        return
    cost = effective_ability_cost(actor, ability)
    cost_type = str(ability.get("cost_type") or "").lower()
    if cost and cost_type in {"hp", "mp", "sp"}:
        actor[cost_type] = max(0, _safe_int(actor.get(cost_type), 0) - cost)


def _can_pay_cost(actor: dict[str, Any], ability: dict[str, Any]) -> bool:
    if "_resolved_costs" in ability or "costs" in ability:
        return all(actor.get(key, 0) >= amount for key, amount in ability.get("_resolved_costs", ability.get("costs", {})).items())
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
    extra = sum(max(0, _safe_int(spec.get("extra_actions_per_round"), 0))
                for spec in equipped_item_specs(character))
    extra += sum(int(value) for value in status_effects.modifiers(character, "extra_actions_per_round"))
    return max(1, 1 + extra)


def _equipped_effect(character: dict[str, Any], key: str) -> Any:
    for spec in equipped_item_specs(character):
        value = spec.get(key)
        if value:
            return value
    return None


def _available_skills(character: dict[str, Any]) -> list[dict[str, Any]]:
    skills = [deepcopy(skill) for skill in character.get("skills") or [] if isinstance(skill, dict)]
    for spec in equipped_item_specs(character):
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
    for spec in equipped_item_specs(character):
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
    if explicit in {"attack", "damage", "heal", "restore", "cleanse", "defend", "status", "field", "stance"}:
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
    derived = 0
    for item_combat in equipped_item_specs(actor):
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


def counter_attack_element(defender: dict[str, Any]) -> str:
    preferred = _counter_element(_primary_element(defender))
    elements = [preferred, "fire", "water", "ice", "lightning", "earth", "wind", "light", "dark", "holy"]
    return max(elements, key=lambda element: _resistance_multiplier(defender, element))


def weakness_attack_element(defender: dict[str, Any]) -> str:
    elements = {"physical", *(defender.get("resistances") or {})}
    for item in defender.get("inventory") or []:
        if isinstance(item, dict):
            elements.update(item_combat_spec(item).get("damage_taken_multipliers") or {})
    best = max(sorted(elements), key=lambda element: _resistance_multiplier(defender, element))
    return best if _resistance_multiplier(defender, best) > 1.0 else "physical"


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
    selected = equipped_items(actor)
    for item in actor.get("inventory") or []:
        if not isinstance(item, dict):
            continue
        spec = item_combat_spec(item)
        if (item_slot(item) or spec.get("requires_equipped")) and item not in selected:
            continue
        passive = spec.get("damage_taken_multipliers")
        if not isinstance(passive, dict):
            continue
        try:
            multiplier *= max(0.0, float(passive.get(element, 1.0)))
        except (TypeError, ValueError):
            continue
    for values in status_effects.modifiers(actor, "damage_taken_multipliers"):
        multiplier *= max(0.0, float(values.get(element, 1.0)))
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


def _presentation_state(session: dict[str, Any]) -> dict[str, Any]:
    actors = {"player": session.get("character", {})}
    actors.update({enemy["id"]: enemy for enemy in (session.get("combat") or {}).get("enemies", [])})
    return {actor_id: {**{key: actor.get(key, 0) for key in ("hp", "max_hp", "mp", "max_mp", "sp", "max_sp")},
                       "defeated": (_safe_int(actor.get("hp"), 0) <= 0 if actor_id == "player" else _enemy_is_defeated(actor))}
            for actor_id, actor in actors.items()}


def _log(session: dict[str, Any], actor: str, kind: str, text: str, data: Optional[dict[str, Any]] = None,
         *, target: Optional[dict[str, Any]] = None) -> None:
    combat = session.get("combat")
    if not isinstance(combat, dict):
        return
    combat["event_sequence"] = int(combat.get("event_sequence", 0)) + 1
    entry = {
        "sequence": combat["event_sequence"],
        "round": combat.get("round", 1),
        "actor": actor,
        "kind": kind,
        "text": text,
        "created_at": utc_now(),
        "state": _presentation_state(session),
    }
    if data:
        entry["data"] = deepcopy(data)
    details = data or {}
    enemies = combat.get("enemies", [])
    actor_side = "enemy" if any(enemy["id"] == actor for enemy in enemies) else "party"
    visual_kind = {"damage": "damage", "field_damage": "damage", "status_damage": "damage",
                   "self_damage": "damage", "heal": "heal", "miss": "miss", "defend": "buff",
                   "stance": "buff", "status": "buff", "phase_transition": "phase"}.get(kind)
    if kind == "item" and "amount" in details:
        visual_kind = "heal"
    if target is None and visual_kind:
        target = next((enemy for enemy in enemies if enemy["id"] == actor), session.get("character", {}))
    if visual_kind and target is not None:
        player_target = target is session.get("character")
        target_id = "player" if player_target else target.get("id")
        amount = details.get("damage", details.get("amount", 0))
        entry["visual"] = {
            "kind": visual_kind, "actor_id": actor, "actor_side": actor_side,
            "target_id": target_id, "target_side": "party" if player_target else "enemy",
            "hit": visual_kind != "miss", "critical": False,
            # No critical-hit rule by design (2026-10-13): adding one would shift every balance target.
            "amount": amount, "resource": details.get("resource", "hp"),
            "element": details.get("element", "physical"), "weakness": bool(details.get("weakness")),
            "knocked_down": (_safe_int(target.get("hp"), 0) <= 0 if player_target else _enemy_is_defeated(target)),
            "heavy": visual_kind == "damage" and player_target and actor_side == "enemy"
                     and amount >= max(1, _safe_int(target.get("max_hp"), 1)) * 0.25,
        }
    combat.setdefault("log", []).append(entry)
    if "action_events" in combat:
        combat["action_events"].append(deepcopy(entry))


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
