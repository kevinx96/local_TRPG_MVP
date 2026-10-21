"""Normal battle instrumentation, without consuming random numbers."""
from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from typing import Any
from unittest.mock import patch

from host import combat, progression, state, status_effects
from . import budget, sim


def fast_fight(session: dict[str, Any], policy: str, rng: random.Random, *, purify: bool = False,
               recovery_threshold: float = .30) -> dict[str, Any]:
    from .route_v2 import resources
    from .archetypes import COMPLETION_TITLE
    location, before = state.current_location_id(session), resources(session)
    session["combat_start_requested"] = True
    session["_balance_free_actions"] = {}
    if not combat.ensure_combat_started(session):
        raise ValueError(f"Encounter did not start: {location}")
    while combat.combat_is_active(session):
        action, target = sim.choose_action(session, policy, purify=purify, reserve_purification=purify,
                                           recovery_threshold=recovery_threshold if policy == "best_free" else None)
        sim.perform_action(session, action, target, rng)
    battle = session["combat"]
    summary = {"encounter": location, "encounter_class": battle["encounter"].get("encounter_class"),
               "status": battle["status"], "rounds": battle["round"], "before": before,
               "skill_usage": {}, "statuses": []}
    continuing = (battle["status"] in {"victory", "purified"} or summary["encounter_class"] == "scripted_loss"
                  or recoverable_defeat(session, battle))
    state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
    combat.clear_combat_after_resolution(session)
    summary["continue"] = continuing and not session.get("game_over") and session["character"]["hp"] > 0
    if (session.get("game_over") or {}).get("title") == COMPLETION_TITLE:
        summary["continue"] = True
    return summary


def recoverable_defeat(session: dict[str, Any], battle: dict[str, Any]) -> bool:
    effects = battle["encounter"].get("defeat_effects", {})
    return (session.get("difficulty") == "normal" and battle["status"] == "defeat"
            and effects.get("hp", 0) > 0 and bool(effects.get("current_location"))
            and not effects.get("game_over"))


def sustain(session: dict[str, Any]) -> float:
    actor = session["character"]
    total = actor["max_hp"] * progression.effects(session).get("regen_ratio", 0)
    companion = session.get("companion") or {}
    if companion.get("id") in session["combat"]["encounter"].get("disable_companion_healing", []):
        return total
    enemies = combat._alive_enemies(session["combat"])
    for effect in companion.get("round_start_effects", []):
        if effect.get("kind") != "heal_player" or not state._session_requirement_passes(effect.get("requirements"), session):
            continue
        if effect.get("scale_from_damage"):
            # Engine targets the first living foe for this companion's fire breath.
            target = enemies[0] if enemies else None
            attacks = [e for e in companion.get("round_start_effects", []) if e.get("kind") == "damage_enemy"
                       and state._session_requirement_passes(e.get("requirements"), session)]
            amount = 0.0
            if target and combat._resistance_multiplier(target, "fire") >= 1:
                for attack in attacks:
                    raw = attack.get("damage", attack.get("amount", "0"))
                    ability = {"accuracy": 100, "element": attack.get("element", "fire")}
                    chance = combat.attack_chance(session, companion, target, ability, "companion") / 100
                    amount += chance * sum(p * math.floor(min(abs(target["hp"]), combat.damage_after_defense(value,
                        combat._resistance_multiplier(target, ability["element"]), combat._actor_defense(target), combat._combat_rules(session)))
                        * effect["scale_from_damage"]["ratio"] + .5) for value, p in budget.formula_distribution(str(raw), companion).items())
        else:
            amount = math.floor(actor["max_hp"] * effect["max_hp_ratio"] + .5) if "max_hp_ratio" in effect else sim.formula_mean(str(effect.get("amount", "0")), actor)
        total += amount / max(1, int(effect.get("every_n_rounds", 1)))
    return total


def fight(session: dict[str, Any], policy: str, rng: random.Random, *, purify: bool = False,
          recovery_threshold: float = .30) -> dict[str, Any]:
    from .route_v2 import resources
    from .archetypes import COMPLETION_TITLE
    location, before = state.current_location_id(session), resources(session)
    opening = {}
    actions, specs, consumables = Counter(), {}, Counter()
    usage = {}
    statuses = defaultdict(lambda: {"applications": 0, "damage": 0, "cleared": 0, "cleansed": 0})
    rounds_seen = set()
    current = None
    current_round = 0
    enemy_phase = False
    incoming = healing = 0.0
    phases = 0
    extra_healing = 0.0
    action_max_hp = session["character"]["max_hp"]
    status_names = {s["name"]: s["id"] for s in session["scenario_pack"].get("status_defs", [])}
    original_start, original_phase = combat._apply_round_start_effects, combat._enemy_phase
    original_log, original_cost = combat._log, combat._pay_cost
    original_remove = status_effects.remove

    def measured_remove(actor, status):
        if actor is session["character"] or any(actor is enemy for enemy in (session.get("combat") or {}).get("enemies", [])):
            statuses["player" if actor is session["character"] else "enemy", status["id"]]["cleared"] += 1
        return original_remove(actor, status)

    def measured_start(value, source_rng):
        nonlocal healing
        if not opening:
            opening.update(budget.phase_moments(value))
            healing = sustain(value)
        return original_start(value, source_rng)

    def measured_phase(value, source_rng):
        nonlocal incoming, phases, enemy_phase
        incoming += budget.phase_moments(value)["expected_damage"]
        phases += 1
        enemy_phase = True
        try:
            return original_phase(value, source_rng)
        finally:
            enemy_phase = False

    def measured_cost(actor, ability):
        if actor is session["character"] and current is not None:
            current["uses"] += 1
            current["rounds"].append(current_round)
            for resource, amount in ability.get("_resolved_costs", {ability.get("cost_type", ""): ability.get("cost", 0)}).items():
                current["costs"][resource] = current["costs"].get(resource, 0) + amount
        return original_cost(actor, ability)

    def measured_log(value, actor, kind, text, data=None, *, target=None):
        nonlocal extra_healing
        data = data or {}
        side = "player" if target is value["character"] or target is None and actor == "player" else "enemy"
        status = data.get("status", {})
        if status.get("id"):
            if status.get("name"):
                status_names[status["name"]] = status["id"]
            statuses[side, status["id"]]["applications"] += 1
            if status["id"] == "gospel" and current is not None and current["id"] == "seraphim_gospel":
                extra_healing += max(0, value["character"]["max_hp"]-action_max_hp)
        if data.get("removed_status"):
            statuses[side, data["removed_status"]]["cleansed"] += 1
        if kind == "status_damage":
            identifier = next((identifier for name, identifier in status_names.items() if f"は{name}で" in text), "unclassified")
            statuses[side, identifier]["damage"] += data.get("damage", 0)
        if current is not None and not enemy_phase and actor == "player" and value["combat"]["round"] == current_round:
            if kind == "damage":
                current["hits"] += 1
                current["damage"] += data.get("damage", 0)
            if kind == "heal" and current["id"] in progression.effects(value).get("free_skills", []):
                extra_healing += data.get("amount", 0)
        if actor == "status" and kind == "heal" and "福音" in text:
            extra_healing += data.get("amount", 0)
        return original_log(value, actor, kind, text, data, target=target)

    session["_balance_free_actions"] = {}
    with patch.object(combat, "_apply_round_start_effects", measured_start), patch.object(combat, "_enemy_phase", measured_phase), patch.object(combat, "_log", measured_log), patch.object(combat, "_pay_cost", measured_cost), patch.object(status_effects, "remove", measured_remove):
        session["combat_start_requested"] = True
        if not combat.ensure_combat_started(session):
            raise ValueError(f"Encounter did not start: {location}")
        free = sim.choose_action(session, "best_free")[0] if combat.combat_is_active(session) else None
        while combat.combat_is_active(session):
            round_number = session["combat"]["round"]
            if round_number not in rounds_seen:
                rounds_seen.add(round_number)
                for option in combat.combat_actions(session):
                    if option["type"] == "skill":
                        entry = usage.setdefault(option["id"], {"id": option["id"], "uses": 0, "attempts": 0, "hits": 0, "damage": 0, "costs": {}, "disabled_cooldown_rounds": 0, "disabled_uses_rounds": 0, "rounds": []})
                        if option.get("cooldown_remaining"):
                            entry["disabled_cooldown_rounds"] += 1
                        ability = combat._player_ability(session, "skill", option["id"])
                        if ability.get("max_uses_per_battle") is not None and session["combat"].get("passive_state", {}).get("uses", {}).get(option["id"], 0) >= ability["max_uses_per_battle"]:
                            entry["disabled_uses_rounds"] += 1
            action, target = sim.choose_action(session, policy, purify=purify, reserve_purification=purify,
                                               recovery_threshold=recovery_threshold if policy == "best_free" else None)
            key = f"{action['type']}:{action['id']}"
            actions[key] += 1
            if action["type"] == "item":
                item = combat._find_entry(session["character"]["inventory"], action["id"], "item")
                consumed = combat.item_combat_spec(item).get("consumable", True)
                if consumed:
                    consumables[item["name"]] += 1
            else:
                consumed = False
            specs[key] = {"type": action["type"], "id": action["id"], "free": not consumed and not any(action.get("costs", {"legacy": action.get("cost", 0)}).values()), "kind": action.get("kind", "attack")}
            current = usage.get(action["id"]) if action["type"] == "skill" else None
            current_round = round_number
            if current is not None:
                current["attempts"] += 1
            action_max_hp = session["character"]["max_hp"]
            sim.perform_action(session, action, target, rng)
            current = None
    battle = session["combat"]
    status, rounds = battle["status"], battle["round"]
    status_rows = [{"side": side, "id": identifier, **counts} for (side, identifier), counts in sorted(statuses.items())]
    status_loss = sum(r["damage"] for r in status_rows if r["side"] == "player")
    summary = {"encounter": location, "encounter_class": battle["encounter"].get("encounter_class"), "status": status, "rounds": rounds,
               "policy": policy, "before": before, "after_combat": resources(session), "actions": dict(actions), "action_specs": specs,
               "consumables": dict(consumables), "opening": opening, "expected_healing": healing,
               "m3b_additional_healing_per_round": extra_healing / max(1, rounds),
               "expected_hp_loss": incoming + status_loss, "direct_expected_hp_loss": incoming, "status_hp_loss": status_loss,
               "enemy_phases": phases, "companion": (session.get("companion") or {}).get("id"),
               "p0_choice": f"{free['type']}:{free['id']}" if free else None, "statuses": status_rows, "skill_usage": usage}
    delta = combat.consume_combat_state_delta(session)
    summary["exp_award"] = {"amount": delta.get("_exp_reward", {}).get("amount", 0), "category": summary["encounter_class"]}
    state.apply_state_delta(session, delta, allow_world_transition=True)
    combat.clear_combat_after_resolution(session)
    summary["after_resolution"] = resources(session)
    summary["continue"] = (status in {"victory", "purified"} or summary["encounter_class"] == "scripted_loss"
                           or recoverable_defeat(session, battle)) and not session.get("game_over") and session["character"]["hp"] > 0
    if (session.get("game_over") or {}).get("title") == COMPLETION_TITLE:
        summary["continue"] = True
    return summary
