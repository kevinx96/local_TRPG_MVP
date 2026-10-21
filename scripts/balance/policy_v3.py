"""Normal-only policy estimates; all mutations and settlements remain in host."""
from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from functools import lru_cache
from typing import Any

from host import combat, progression, status_effects
from .checkpoints import ROOT

PARAMETERS = json.loads((ROOT / "eval/balance/strategy_v3.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=4096)
def _distribution(formula: str, attributes: tuple) -> dict[int, float]:
    from .budget import formula_distribution
    return formula_distribution(formula, {"attributes": dict(attributes)})


def ability_for(session: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    if action["type"] in {"skill", "item"}:
        result = combat._player_ability(session, action["type"], action["id"])
        result = {**result, "_skill_action": action["type"] == "skill"}
    else:
        actor = session["character"]
        result = combat._merge_dict(combat._combat_rules(session)["basic_attack"], actor.get("combat", {}).get("basic_attack"))
        result = combat._merge_dict(result, combat._equipped_weapon_attack(actor))
        result["_basic_action"] = True
        passive = progression.effects(session)
        if passive.get("basic_element"):
            result.update(element=passive["basic_element"], fallback_element=passive.get("fallback_element", "physical"),
                          weakness_multiplier=passive.get("weak_multiplier", 1))
    return result


def legal_pairs(session: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    result = []
    used = (session.get("_balance_free_actions") or {})
    for action in combat.combat_actions(session):
        if not action.get("enabled") or action["type"] == "flee":
            continue
        if used.get(f"{action['type']}:{action['id']}") == session["combat"]["round"]:
            continue
        ability = ability_for(session, action) if action["type"] in {"skill", "item"} else {}
        for target in combat._alive_enemies(session["combat"]):
            if action["type"] in {"skill", "item"} and combat._ability_disabled_reason(
                    session, action["type"], action["id"], ability, target["id"]):
                continue
            result.append((action, target))
    return result


def strike_moments(session: dict[str, Any], attacker: dict[str, Any], target: dict[str, Any],
                   ability: dict[str, Any], actor_id: str) -> tuple[float, float]:
    rules = combat._combat_rules(session)
    passive = progression.effects(session)
    attributes = tuple(sorted(attacker.get("attributes", {}).items()))
    distribution = _distribution(str(ability.get("damage") or ability.get("dice_type") or "1d4"), attributes)
    for bonus in ability.get("conditional_bonus", []):
        if combat._condition(session, bonus, target):
            extra = _distribution(bonus["damage"], attributes)
            combined = {}
            for left, lp in distribution.items():
                for right, rp in extra.items():
                    combined[left + right] = combined.get(left + right, 0) + lp * rp
            distribution = combined
    scale = float(ability.get("damage_multiplier", 1) or 1)
    for condition in ability.get("conditional_multipliers", []):
        if (not condition.get("element") or condition["element"] == ability.get("element")) and combat._condition(session, condition, target):
            scale *= condition["x"]
    element = ability.get("element", "physical")
    if element == "current":
        element = combat._primary_element(attacker)
    if element == "counter":
        element = combat.counter_attack_element(target)
    if element == "weakness":
        element = combat.weakness_attack_element(target)
        if combat._resistance_multiplier(target, element) <= 1:
            element = ability.get("fallback_element", element)
    multiplier = combat._resistance_multiplier(target, element)
    if ability.get("ignores_resistance"):
        multiplier = max(1.0, multiplier)
    defense = combat._actor_defense(target)
    if actor_id == "player":
        penetration = passive.get("physical_penetration", 0) if element == "physical" or ability.get("_basic_action") else 0
        defense *= 1 - penetration
        if element == "physical" and multiplier < 1:
            multiplier += (1 - multiplier) * penetration
    elif passive.get("armor_bonus") and any(i.get("slot") == "armor" and combat.item_combat_spec(i).get("defense", 0) >= passive.get("armor_min", 1)
                                             for i in combat.equipped_items(target)):
        defense += passive["armor_bonus"]
    if target is not session["character"]:
        defense = max(0, defense + sum(int(m.get("enemy_defense", 0)) for m in combat._encounter_modifiers(session, target)))
    if ability.get("ignores_defense"):
        defense = 0
    chance = combat.attack_chance(session, attacker, target, ability, actor_id) / 100
    mu = second = 0.0
    for raw, probability in distribution.items():
        raw = max(0, round(raw * scale))
        if multiplier > 1:
            raw *= ability.get("weakness_multiplier", 1)
        damage = combat.damage_after_defense(raw, multiplier, defense, rules)
        if not isinstance(damage, int):
            damage = round(damage)
        if ability.get("status_on_hit"):
            damage = 0
        if actor_id == "player":
            category = target.get("encounter_class", session["combat"]["encounter"].get("encounter_class"))
            damage = round(damage * passive.get("encounter_damage", {}).get(category, 1))
        damage = max(0, round(damage * status_effects.product(attacker, "damage_dealt_multiplier")))
        if ability.get("true_damage"):
            damage = raw
        elif target is session["character"]:
            damage = combat._modified_received_damage(session, damage, element, attacker, ability.get("name", ""), ability.get("id", ""))
            status = session["combat"].get("player_status", {})
            guard = status.get("guard_multiplier", 1) if status.get("guard_disabled_round", 0) < session["combat"]["round"] else 1
            received = status_effects.product(target, "received_damage_multiplier")
            damage = max(0, round(damage * max(.25, guard * received)))
            # A separate clone for each support point keeps this estimator pure.
            if any("shield_remaining" in s for s in target.get("statuses", [])):
                damage = status_effects.absorb(deepcopy(target), damage)
            damage -= min(target.get("mp", 0), math.floor(damage * passive.get("mana_armor", 0) + .5))
        else:
            for status in target.get("statuses", []):
                damage = max(0, round(damage * status.get("guard_multiplier", 1)))
            damage = max(0, round(damage * max(.25, status_effects.product(target, "received_damage_multiplier"))))
            if any("shield_remaining" in s for s in target.get("statuses", [])):
                damage = status_effects.absorb(deepcopy(target), damage)
        if combat._negative_undead(target) and element not in {"holy", "light"}:
            damage = -damage
        mu += probability * chance * damage
        second += probability * chance * damage ** 2
    return mu, max(0.0, second - mu ** 2)


def damage(session: dict[str, Any], action: dict[str, Any], target: dict[str, Any], *, followups: bool = True) -> float:
    actor = session["character"]
    ability = ability_for(session, action)
    if action["type"] != "attack" and combat._ability_kind(ability) not in {"attack", "damage"}:
        return 0.0
    passive = progression.effects(session)
    if ability.get("spell_tier"):
        ability = deepcopy(ability)
        for status in actor.get("statuses", []):
            ability["damage_multiplier"] = ability.get("damage_multiplier", 1) * status.get("modifiers", {}).get("next_spell_damage_multiplier", 1)
        previous = session["combat"].get("passive_state", {}).get("spell_elements")
        elements = ability.get("multi_elements") or [ability.get("element")]
        if previous and previous != elements and not ability.get("resonance_exempt"):
            ability["damage_multiplier"] = ability.get("damage_multiplier", 1) * passive.get("resonance", {}).get("multiplier", 1)
    elements = combat._learned_elements(actor, target, ability["max_hits"]) if ability.get("learned_elements") else ability.get("multi_elements") or [ability.get("element", "physical")]
    total = sum(strike_moments(session, actor, target, {**ability, "element": e}, "player")[0] for e in elements) * int(ability.get("hits_per_element", 1))
    if not followups:
        return total
    extras = list(action.get("followups", []))
    followup = passive.get("hit_followup", {})
    if (action["type"] == "attack" and followup.get("basic") or action["id"] in followup.get("skills", [])):
        followup = deepcopy(followup)
        if followup.get("weapon_half_dice"):
            dice = re.search(r"(\d+)d(\d+)", combat._equipped_weapon_attack(actor).get("damage", ""))
            followup["damage"] = f"{dice[1]}d{max(1, int(dice[2]) // 2)}" if dice else "0"
        extras.append({**followup, "status_followup": True})
    if passive.get("weakness_followup") and any(v > 1 for v in target.get("resistances", {}).values()):
        extras.append({**passive["weakness_followup"], "status_followup": True})
    extras += [{**s["modifiers"]["on_damage_followup"], "status_followup": True} for s in target.get("statuses", []) if s.get("modifiers", {}).get("on_damage_followup")]
    primary_chance = combat.attack_chance(session, actor, target, ability, "player") / 100
    return total + primary_chance * sum(strike_moments(session, actor, target, e, "player")[0] for e in extras)


def status_value(session: dict[str, Any], spec: Any, target: dict[str, Any], survival: float, *, incremental: bool = True) -> float:
    from .sim import formula_mean
    if not spec:
        return 0.0
    spec = {"id": spec} if isinstance(spec, str) else spec
    definition = next((s for s in session["scenario_pack"].get("status_defs", []) if s["id"] == spec.get("id")), {})
    status = {**definition, **spec}
    existing = next((s for s in target.get("statuses", []) if s.get("id") == status.get("id")), {}) if incremental else {}
    if existing and status.get("no_reapply"):
        return 0.0
    turns = min(PARAMETERS["status_horizon_rounds"], status.get("duration") or 3, survival)
    tick = {**status.get("tick", {}), **(status.get("by_source", {}).get("player", {}).get("tick", {}) if target is not session["character"] else {})}
    per_stack = formula_mean(str(tick.get("damage", status.get("damage", "0"))), session["character"]) * combat._resistance_multiplier(target, tick.get("element", "physical"))
    old_stacks = existing.get("stacks", 1) if existing else 0
    new_stacks = min(status.get("max_stacks", 1), old_stacks+status.get("stacks", 1)) if status.get("stackable") else 1
    per_turn, previous_per_turn = per_stack*new_stacks, per_stack*old_stacks
    old_turns = min(existing.get("remaining_rounds", 0), survival, PARAMETERS["status_horizon_rounds"])
    if target is not session["character"] and session["combat"]["encounter"].get("encounter_class") in {"elite", "boss"}:
        per_turn = min(per_turn, int(abs(target["max_hp"]) * .05))
        previous_per_turn = min(previous_per_turn, int(abs(target["max_hp"]) * .05))
    modifiers = {**status.get("modifiers", {}), **(status.get("boss_modifiers", {}) if status_effects.is_boss(session, target) else {})}
    value = max(0, turns * per_turn-old_turns*previous_per_turn)
    followup = modifiers.get("on_damage_followup")
    if followup:
        value += max(0, turns-old_turns) * strike_moments(session, session["character"], target, {**followup, "status_followup": True}, "player")[0]
    if modifiers.get("accuracy_penalty"):
        from . import budget
        if target is session["character"]:
            enemy = combat._alive_enemies(session["combat"])[0]
            basic = {"type": "attack", "id": "basic_attack"}
            value += max(0, turns-old_turns) * damage(session, basic, enemy) * modifiers["accuracy_penalty"] / max(5, combat.attack_chance(session, target, enemy, ability_for(session, basic), "player"))
        else:
            incoming = budget.phase_moments(session)["expected_damage"]
            value += max(0, turns-old_turns) * incoming * modifiers["accuracy_penalty"] / max(5, 100 - combat.actor_evade(session, session["character"]))
    if target is session["character"] and modifiers.get("damage_dealt_multiplier", 1) < 1:
        enemy = combat._alive_enemies(session["combat"])[0]
        value += turns * damage(session, {"type": "attack", "id": "basic_attack"}, enemy) * (1/modifiers["damage_dealt_multiplier"]-1)
    return value * status.get("chance", 100) / 100


def choose(session: dict[str, Any], policy: str, **kwargs: Any):
    return _choose(session, policy, **kwargs)


def _choose(session: dict[str, Any], policy: str, *, purify: bool = True,
           reserve_purification: bool = False, recovery_threshold=None, **_: Any):
    from . import budget, sim
    pairs = legal_pairs(session)
    actor = session["character"]
    specials = [(a, t) for a, t in pairs if a["type"] == "special" and a.get("outcome") == "purified"]
    if policy != "best_free" and purify and specials:
        return specials[0][0], specials[0][1]["id"]
    healing = [(a, t) for a, t in pairs if a.get("kind") == "heal" and not (combat._equipped_effect(actor, "healing_harms_humans") and a["type"] == "skill")]
    threshold = PARAMETERS["p0_healing_threshold"] if policy == "best_free" else PARAMETERS["healing_threshold"]
    if policy == "best_free" and recovery_threshold is not None:
        threshold = recovery_threshold
    if actor["hp"] < actor["max_hp"] * threshold and healing:
        action, target = max(healing, key=lambda pair: min(actor["max_hp"]-actor["hp"], actor["max_hp"] * pair[0]["max_hp_ratio"] if "max_hp_ratio" in pair[0] else sim.formula_mean(str(pair[0].get("healing") or "10"), actor)))
        return action, target["id"]
    attacks = [(a, t) for a, t in pairs if a["type"] == "attack" or a.get("kind") in {"attack", "damage"}]
    if policy == "attack_only":
        return next(a for a, _ in attacks if a["type"] == "attack"), attacks[0][1]["id"]
    if policy == "best_free":
        attacks = [(a, t) for a, t in attacks if not any(ability_for(session, a).get("_resolved_costs", {"legacy": a.get("cost", 0)}).values())
                   and (a["type"] != "item" or not ability_for(session, a).get("consumable", True))]
    incoming = budget.phase_moments(session)["expected_damage"] if policy != "best_free" else 0
    boss = session["combat"]["encounter"].get("encounter_class") in {"boss", "elite"}
    high = incoming >= actor["max_hp"] * PARAMETERS["high_incoming_hp_ratio"] or any(e.get("charging") or e.get("charge") for e in session["combat"]["enemies"])
    high = high or boss and actor["hp"] < actor["max_hp"] * PARAMETERS["boss_defense_hp_ratio"]
    scored = []
    for action, target in attacks:
        if policy != "best_free" and action["id"] in PARAMETERS["ultimate_ids"] and not boss:
            continue
        if reserve_purification and action["type"] == "item" and action["id"] == "holy_water" and action.get("quantity", 1) <= 1:
            continue
        ability = ability_for(session, action)
        value = sum(damage(session, action, t) for t in combat._alive_enemies(session["combat"])) if action.get("all_targets") else damage(session, action, target)
        if policy != "best_free":
            survival = min(PARAMETERS["status_horizon_rounds"], abs(target["hp"]) / max(1, value))
            value += status_value(session, ability.get("on_hit_status"), target, survival) * combat.attack_chance(session, actor, target, ability, "player") / 100
            if action["type"] in {"attack", "skill"} and not ability.get("status_on_hit"):
                value += status_value(session, progression.effects(session).get("hit_status"), target, survival) * combat.attack_chance(session, actor, target, ability, "player") / 100
            value -= sum(ability.get("_resolved_costs", {}).values()) * PARAMETERS["resource_damage_penalty"]
            if high and ability.get("self_status"):
                value += incoming * .25
        scored.append((value, action, target))
    if policy != "best_free":
        debuff_loss = sum(status_value(session, {**s, "duration": s.get("remaining_rounds", 1)}, actor,
            s.get("remaining_rounds", 1), incremental=False) for s in actor.get("statuses", []) if s.get("cleansable"))
        for action, target in pairs:
            if action["type"] != "skill" or action.get("kind") in {"attack", "damage"}:
                continue
            ability = ability_for(session, action)
            value = 0.0
            if ability.get("cleanse") and debuff_loss > actor["max_hp"] * PARAMETERS["cleanse_hp_ratio"]:
                value += debuff_loss
            if action.get("kind") == "restore" and actor.get("mp", 0) < actor.get("max_mp", 0) * PARAMETERS["restore_mp_ratio"]:
                value += min(actor["max_mp"]-actor["mp"], sim.formula_mean(str(ability.get("amount", "0")), actor))
            if high:
                value += incoming * (1-ability.get("guard_multiplier", 1)) * PARAMETERS["defense_value_weight"]
                raw = ability.get("self_status", [])
                for spec in raw if isinstance(raw, list) else [raw]:
                    spec = {"id": spec} if isinstance(spec, str) else spec
                    definition = next((s for s in session["scenario_pack"].get("status_defs", []) if s["id"] == spec.get("id")), {})
                    mods = {**definition.get("modifiers", {}), **spec.get("modifiers", {})}
                    value += incoming * (1 - mods.get("received_damage_multiplier", 1))
                    value += incoming * mods.get("evade_bonus", 0) / 100
                    value += actor["max_hp"] * max(0, mods.get("max_hp_multiplier", 1) - 1)
                    if mods.get("extra_actions_per_round") and boss:
                        value += max((v for v, _, _ in scored), default=0) * (min(3, abs(target["hp"]) / max(1, max((v for v, _, _ in scored), default=1)))-1)
            if ability.get("free_action") and value > 0:
                value += max((v for v, _, _ in scored), default=0)
            if value > 0:
                scored.append((value, action, target))
    _, action, target = max(scored, key=lambda row: row[0])
    return action, target["id"]
