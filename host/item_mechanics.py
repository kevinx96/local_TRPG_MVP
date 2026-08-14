from __future__ import annotations

from copy import deepcopy
from typing import Any


USABLE_ITEM_KINDS = {"heal", "restore", "damage", "flee", "status", "shrink"}
EQUIPMENT_ITEM_KINDS = {"weapon", "armor", "equipment"}
PASSIVE_ITEM_KINDS = {"passive"}
SUPPORTED_ITEM_KINDS = USABLE_ITEM_KINDS | EQUIPMENT_ITEM_KINDS | PASSIVE_ITEM_KINDS


def item_combat_spec(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict) or not isinstance(item.get("combat"), dict):
        return {}
    spec = deepcopy(item["combat"])
    return spec if str(spec.get("kind") or "").lower() in SUPPORTED_ITEM_KINDS else {}


def item_is_combat_usable(item: Any) -> bool:
    return str(item_combat_spec(item).get("kind") or "").lower() in USABLE_ITEM_KINDS


def structured_item_effect(item: Any) -> str:
    spec = item_combat_spec(item)
    if not spec:
        return ""
    kind = str(spec.get("kind") or "").lower()
    parts: list[str] = []
    if kind == "weapon":
        damage = str(spec.get("damage") or "").strip()
        if damage:
            parts.append(f"通常攻撃 {damage}ダメージ")
        if spec.get("accuracy") is not None:
            parts.append(f"命中率{_as_int(spec.get('accuracy'), 100)}%")
        if spec.get("element"):
            parts.append(f"{spec['element']}属性")
    elif kind == "armor":
        defense = max(0, _as_int(spec.get("defense"), 0))
        if defense:
            parts.append(f"被ダメージを{defense}軽減")
    elif kind == "heal":
        healing = str(spec.get("healing") or spec.get("amount") or "").strip()
        if healing:
            parts.append(f"HPを{healing}回復")
    elif kind == "restore":
        resource = str(spec.get("resource") or "mp").lower()
        amount = str(spec.get("amount") or spec.get("formula") or "").strip()
        if resource in {"hp", "mp", "sp"} and amount:
            parts.append(f"{resource.upper()}を{amount}回復")
    elif kind == "damage":
        damage = str(spec.get("damage") or "").strip()
        if damage:
            parts.append(f"{damage}ダメージ")
        if spec.get("accuracy") is not None:
            parts.append(f"命中率{_as_int(spec.get('accuracy'), 100)}%")
        if spec.get("element"):
            parts.append(f"{spec['element']}属性")
    elif kind == "flee":
        parts.append("戦闘から確実に離脱")
    elif kind == "status":
        parts.append(str(spec.get("description") or "状態効果を付与"))
    elif kind == "shrink":
        parts.append(f"{_as_int(spec.get('chance'), 2)}%で敵のHPと最大HPを1/10")

    modifiers = _modifier_parts(spec)
    parts.extend(modifiers)
    if kind in USABLE_ITEM_KINDS and bool(spec.get("consumable", True)):
        parts.append("消耗品")
    return " / ".join(parts)


def item_mechanic_warning(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    has_claim = bool(str(item.get("description") or "").strip() or str(item.get("effect") or "").strip())
    if has_claim and not structured_item_effect(item):
        return "描述或效果存在，但引擎没有对应的结构化机制。"
    return ""


def effective_ability(actor: dict[str, Any], ability: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(ability)
    kind = _ability_kind(result)
    damage_bonus = 0
    healing_bonus = 0
    healing_multiplier = 1.0
    for spec in equipped_item_specs(actor):
        if not _modifier_applies(spec, kind):
            continue
        damage_bonus += _as_int(spec.get("skill_damage_bonus"), 0)
        healing_bonus += _as_int(spec.get("skill_healing_bonus"), 0)
        try:
            healing_multiplier *= float(spec.get("healing_multiplier", 1) or 1)
        except (TypeError, ValueError):
            pass
    if damage_bonus and kind == "attack":
        result["damage"] = _add_formula_bonus(str(result.get("damage") or result.get("dice_type") or "1"), damage_bonus)
    if healing_bonus and kind == "heal":
        result["healing"] = _add_formula_bonus(str(result.get("healing") or result.get("dice_type") or "1"), healing_bonus)
    if kind == "heal" and healing_multiplier != 1:
        result["healing_multiplier"] = healing_multiplier
    return result


def effective_ability_cost(actor: dict[str, Any], ability: dict[str, Any]) -> int:
    cost = max(0, _as_int(ability.get("cost"), 0))
    resource = str(ability.get("cost_type") or "").lower()
    kind = _ability_kind(ability)
    reduction = 0
    for spec in equipped_item_specs(actor):
        if not _modifier_applies(spec, kind):
            continue
        reductions = spec.get("cost_reduction") if isinstance(spec.get("cost_reduction"), dict) else {}
        reduction += max(0, _as_int(reductions.get(resource), 0))
    return max(0, cost - reduction)


def equipped_item_specs(actor: dict[str, Any]) -> list[dict[str, Any]]:
    equipped = set(str(value) for value in actor.get("equipment", []) if str(value))
    specs: list[dict[str, Any]] = []
    for raw in actor.get("inventory", []) if isinstance(actor.get("inventory"), list) else []:
        item = raw if isinstance(raw, dict) else {"name": str(raw)}
        if str(item.get("name") or "") not in equipped and str(item.get("id") or "") not in equipped:
            continue
        spec = item_combat_spec(item)
        if spec:
            specs.append(spec)
    return specs


def equipped_basic_attack_followups(actor: dict[str, Any]) -> list[dict[str, Any]]:
    followups: list[dict[str, Any]] = []
    for spec in equipped_item_specs(actor):
        raw = spec.get("basic_attack_followup")
        entries = raw if isinstance(raw, list) else [raw]
        for entry in entries:
            if isinstance(entry, dict) and str(entry.get("damage") or "").strip():
                followups.append(deepcopy(entry))
    return followups


def _modifier_parts(spec: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    followup = spec.get("basic_attack_followup")
    if isinstance(followup, dict) and followup.get("damage"):
        element = str(followup.get("element") or "").strip()
        suffix = f"({element}属性)" if element else ""
        parts.append(f"通常攻撃時に{followup['damage']}追撃{suffix}")
    reductions = spec.get("cost_reduction") if isinstance(spec.get("cost_reduction"), dict) else {}
    for resource in ("hp", "mp", "sp"):
        amount = max(0, _as_int(reductions.get(resource), 0))
        if amount:
            parts.append(f"{resource.upper()}消費を{amount}軽減")
    damage_bonus = _as_int(spec.get("skill_damage_bonus"), 0)
    healing_bonus = _as_int(spec.get("skill_healing_bonus"), 0)
    if damage_bonus:
        parts.append(f"攻撃技能ダメージ+{damage_bonus}")
    if healing_bonus:
        parts.append(f"回復技能回復量+{healing_bonus}")
    return parts


def _modifier_applies(spec: dict[str, Any], ability_kind: str) -> bool:
    applies_to = spec.get("applies_to")
    if not isinstance(applies_to, list) or not applies_to:
        return True
    return ability_kind in {str(value).lower() for value in applies_to}


def _ability_kind(ability: dict[str, Any]) -> str:
    kind = str(ability.get("kind") or ability.get("type") or "attack").lower()
    return "attack" if kind == "damage" else kind


def _add_formula_bonus(formula: str, bonus: int) -> str:
    if not bonus:
        return formula
    sign = "+" if bonus > 0 else ""
    return f"{formula}{sign}{bonus}"


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
