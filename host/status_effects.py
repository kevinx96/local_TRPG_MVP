"""Definition-backed statuses; legacy inline statuses keep their original rules."""
from __future__ import annotations

import math
from copy import deepcopy
from typing import Any


def modern(status: dict[str, Any]) -> bool:
    return bool(status.get("status_v2"))


def modifiers(actor: dict[str, Any], key: str) -> list[Any]:
    return [status["modifiers"][key] for status in actor.get("statuses", [])
            if modern(status) and key in status.get("modifiers", {})]


def product(actor: dict[str, Any], key: str) -> float:
    return math.prod(float(value) for value in modifiers(actor, key))


def is_boss(session: dict[str, Any], actor: dict[str, Any]) -> bool:
    if actor is session.get("character"):
        return False
    return actor.get("encounter_class", (session.get("combat") or {}).get("encounter", {}).get("encounter_class")) == "boss"


def apply(session: dict[str, Any], actor: dict[str, Any], spec: Any,
          source: dict[str, Any], rng: Any) -> bool:
    from . import combat

    spec = {"id": spec} if isinstance(spec, str) else deepcopy(spec)
    if not isinstance(spec, dict):
        return False
    # Inline damage/remaining_rounds are the frozen pre-v2 representation.
    if ("damage" in spec or "remaining_rounds" in spec or "accuracy_penalty" in spec) and "kind" not in spec:
        combat._apply_status(actor, spec)
        return True
    definition = next((entry for entry in session.get("scenario_pack", {}).get("status_defs", [])
                       if entry["id"] == spec.get("id")), {})
    status = {**deepcopy(definition), **spec}
    if not status.get("kind"):
        return False
    identifier = str(status["id"])
    if actor is not session.get("character"):
        if identifier in actor.get("status_immunity", []):
            return False
        if identifier == "stun" and is_boss(session, actor):
            if identifier not in actor.get("status_allow", []) or actor.get("status_uses", {}).get(identifier, 0) >= 1:
                return False
    if identifier == "stun" and int(actor.get("status_immunity_until", {}).get(identifier, -1)) >= int(actor.get("status_turn", 0)):
        return False
    chance = max(0, min(100, int(status.get("chance", 100))))
    if chance <= 0 or (chance < 100 and rng.randint(1, 100) > chance):
        return False
    if identifier == "stun" and is_boss(session, actor):
        actor.setdefault("status_uses", {})[identifier] = 1
    status["status_v2"] = True
    status["source"] = {"attributes": deepcopy(source.get("attributes", {}))}
    status["modifiers"] = deepcopy(status.get("modifiers", {}))
    status["tick"] = deepcopy(status.get("tick", {}))
    player_source = source is session.get("character")
    source_overrides = status.get("by_source", {}).get("player" if player_source else "enemy", {})
    for key, value in source_overrides.items():
        if key in {"tick", "modifiers"}:
            status[key].update(deepcopy(value))
        else:
            status[key] = deepcopy(value)
    if is_boss(session, actor):
        status["modifiers"].update(status.get("boss_modifiers", {}))
    duration = status.get("duration")
    if "evade_bonus" in status["modifiers"]:
        duration = min(int(duration or 2), int(combat._combat_rules(session)["temporary_evade_max_rounds"]))
    if duration is not None:
        status["remaining_rounds"] = max(1, int(duration))
    statuses = actor.setdefault("statuses", [])
    existing = next((item for item in statuses if modern(item) and item["id"] == identifier), None)
    if existing and status.get("no_reapply"):
        return False
    if existing and "original_max_hp" in existing:
        status["original_max_hp"] = existing["original_max_hp"]
    stacks = max(1, int(status.get("stacks", 1)))
    if existing and status.get("stackable"):
        stacks += int(existing.get("stacks", 1))
    status["stacks"] = min(stacks, max(1, int(status.get("max_stacks", 1))))
    shield = status["modifiers"].get("shield")
    if shield:
        maximum = int(actor["max_hp"])
        capacity = float(shield.get("amount", maximum if shield.get("block_one_attack") else 0))
        if "max_hp_ratio" in shield:
            capacity = min(capacity, maximum * float(shield["max_hp_ratio"]))
        status["shield_remaining"] = max(int(capacity), int((existing or {}).get("shield_remaining", 0)))
    if existing:
        existing.clear()
        existing.update(status)
    else:
        statuses.append(status)
        hp_multiplier = float(status["modifiers"].get("max_hp_multiplier", 1))
        if hp_multiplier != 1:
            status["original_max_hp"] = int(actor["max_hp"])
            actor["max_hp"] = max(1, round(actor["max_hp"] * hp_multiplier))
            combat._heal_actor(actor, max(0, actor["max_hp"] - status["original_max_hp"]))
    extra = int(status["modifiers"].get("extra_actions_per_round", 0))
    if extra and not existing and actor is session.get("character") and combat.combat_is_active(session):
        session["combat"]["actions_remaining"] += extra
    if combat.combat_is_active(session):
        combat._log(session, "status", "status", f"{actor.get('name', '敵')}は{status.get('name', identifier)}を受けた。",
                    {"status": public(status)}, target=actor)
    return True


def public(status: dict[str, Any], definitions: Any = ()) -> dict[str, Any]:
    definition = next((entry for entry in definitions if entry["id"] == status.get("id") or entry["name"] == status.get("name")), {})
    resolved = {**definition, **status}
    return {key: deepcopy(resolved[key]) for key in
            ("id", "name", "icon", "description", "stacks", "remaining_rounds", "shield_remaining") if key in resolved}


def remove(actor: dict[str, Any], status: dict[str, Any]) -> None:
    if "original_max_hp" in status:
        actor["max_hp"] = status["original_max_hp"]
        actor["hp"] = min(actor["hp"], actor["max_hp"])
    actor["statuses"].remove(status)


def clear(actor: dict[str, Any]) -> None:
    for status in list(actor.get("statuses", [])):
        if modern(status):
            remove(actor, status)
    actor.pop("status_immunity_until", None)
    actor.pop("status_turn", None)
    actor.pop("status_uses", None)


def cleanse(session: dict[str, Any], actor: dict[str, Any], spec: dict[str, Any]) -> None:
    from . import combat

    tags = set(spec.get("tags", ["debuff"]))
    count = spec.get("count", "all")
    candidates = [status for status in actor.get("statuses", [])
                  if status.get("cleansable", not modern(status) and ("damage" in status or "accuracy_penalty" in status))
                  and (not tags or tags.intersection(status.get("tags", ["debuff"]))) ]
    for status in candidates if count == "all" else candidates[:max(0, int(count))]:
        remove(actor, status)
        combat._log(session, "status", "status", f"{status.get('name', status['id'])}が解除された。",
                    {"removed_status": status["id"]}, target=actor)


def skip_action(session: dict[str, Any], actor: dict[str, Any], rng: Any) -> bool:
    from . import combat

    for status in list(actor.get("statuses", [])):
        if not modern(status):
            continue
        chance = float(status.get("modifiers", {}).get("skip_chance", 0))
        if status.get("kind") == "skip_turn" or (chance > 0 and rng.random() < chance):
            combat._log(session, "status", "status", f"{actor.get('name', '敵')}は{status.get('name', status['id'])}で行動できなかった。",
                        {"status_id": status["id"], "skipped": True}, target=actor)
            if status.get("kind") == "skip_turn":
                immunity = int(status.get("immunity_after", 0))
                if immunity:
                    actor.setdefault("status_immunity_until", {})[status["id"]] = int(actor.get("status_turn", 0)) + immunity
                remove(actor, status)
            return True
    return False


def tick(session: dict[str, Any], actor: dict[str, Any], rng: Any) -> None:
    from . import combat

    active = [status for status in actor.get("statuses", []) if modern(status)]
    if not active:
        if actor.get("status_immunity_until"):
            actor["status_turn"] = int(actor.get("status_turn", 0)) + 1
        return
    limit = None
    category = actor.get("encounter_class", (session.get("combat") or {}).get("encounter", {}).get("encounter_class"))
    if actor is not session.get("character") and category in {"elite", "boss"}:
        limit = max(0, int(abs(actor["max_hp"]) * .05))
    for status in active:
        tick_spec = status.get("tick", {})
        if tick_spec and actor.get("hp", 0) > 0:
            damage, detail = combat._roll_formula(str(tick_spec.get("damage", "0")), status["source"], rng)
            damage *= int(status.get("stacks", 1))
            element = tick_spec.get("element", "physical")
            multiplier = combat._resistance_multiplier(actor, element)
            damage = (max(0, round(damage * multiplier)) if tick_spec.get("ignore_defense", True)
                      else combat.damage_after_defense(damage, multiplier, combat._actor_defense(actor), combat._combat_rules(session)))
            if limit is not None:
                damage = min(damage, limit)
                limit -= damage
            if actor is session.get("character"):
                damage = combat._round_received_damage(session, damage, element)
                combat._damage_player(session, damage)
            else:
                actor["hp"] = max(0, actor["hp"] - damage)
            combat._log(session, "status", "status_damage", f"{actor.get('name', '敵')}は{status.get('name', status['id'])}で{damage}ダメージを受けた。",
                        {"damage": damage, "stacks": status["stacks"], "formula": detail, "element": element}, target=actor)
        if "remaining_rounds" in status and status.get("expires") != "enemy_phase_end":
            status["remaining_rounds"] -= 1
            if status["remaining_rounds"] <= 0:
                remove(actor, status)
    actor["status_turn"] = int(actor.get("status_turn", 0)) + 1


def absorb(actor: dict[str, Any], damage: int) -> int:
    for status in list(actor.get("statuses", [])):
        if not modern(status) or "shield_remaining" not in status:
            continue
        shield = status["modifiers"]["shield"]
        unlimited = shield.get("block_one_attack") and "max_hp_ratio" not in shield and "amount" not in shield
        absorbed = damage if unlimited else min(damage, status["shield_remaining"])
        damage -= absorbed
        status["shield_remaining"] -= absorbed
        if absorbed and (shield.get("block_one_attack") or status["shield_remaining"] <= 0):
            remove(actor, status)
    return max(0, damage)


def after_damage(session: dict[str, Any], actor: dict[str, Any], damage: int) -> None:
    from . import combat

    for status in actor.get("statuses", []):
        if not modern(status):
            continue
        ratio = float(status.get("modifiers", {}).get("heal_after_attack_ratio", 0))
        if not ratio:
            continue
        round_number = session["combat"]["round"]
        if status.get("healing_round") != round_number:
            status["healing_round"], status["healing_count"] = round_number, 0
        if damage > 0 and actor.get("hp", 0) > 0 and ratio and status.get("healing_count", 0) < int(status["modifiers"].get("heal_limit_per_round", 2)):
            amount = max(0, math.floor(status.get("original_max_hp", actor["max_hp"]) * ratio + .5))
            healed = combat._heal_actor(actor, amount)
            status["healing_count"] += 1
            combat._log(session, "status", "heal", f"{status['name']}でHPを{healed}回復した。", {"amount": healed}, target=actor)
