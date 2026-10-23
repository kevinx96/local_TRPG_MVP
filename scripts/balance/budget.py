from __future__ import annotations

import re
import math
from collections import defaultdict
from copy import deepcopy
from typing import Any

from host import combat
from .sim import formula_mean, prepare_session, selected_characters


def attack_moments(ability: dict[str, Any], enemy: dict[str, Any],
                   session: dict[str, Any]) -> tuple[float, float]:
    """Mean/variance of HP damage, including zero damage on a miss and integer rounding."""
    if session.get("difficulty") == "normal":
        from .policy_v3 import strike_moments
        elements = ability.get("multi_elements") or [ability.get("element", "physical")]
        moments = [strike_moments(session, enemy, session["character"], {**ability, "element": e}, enemy["id"]) for e in elements]
        hits = max(1, int(ability.get("hits_per_element" if ability.get("multi_elements") else "hits", 1)))
        return sum(m[0] for m in moments)*hits, sum(m[1] for m in moments)*hits
    actor, rules = session["character"], combat._combat_rules(session)
    mean, variance = 0.0, 0.0
    elements = ability.get("multi_elements") or [ability.get("element", "physical")]
    for element in elements:
        if element == "current":
            element = combat._primary_element(enemy)
        elif element == "counter":
            element = combat.counter_attack_element(actor)
        elif element == "weakness":
            element = combat.weakness_attack_element(actor)
        accuracy = int(ability.get("accuracy", 85)) + sum(int(m.get("accuracy", 0))
            for m in combat._encounter_modifiers(session, enemy)
            if m.get("enemy_skill") in (ability.get("id"), ability.get("name")))
        accuracy -= sum(int(s.get("accuracy_penalty", 0)) for s in enemy.get("statuses", []))
        chance = 1.0 if ability.get("true_damage") else max(5, min(100, accuracy -
            int(actor.get("combat", {}).get("evade", 0)))) / 100
        values = []
        for raw, probability in formula_distribution(str(ability.get("damage") or ability.get("dice_type") or "1d4"), enemy).items():
            raw = max(0, round(raw * float(ability.get("damage_multiplier", 1) or 1)))
            amount = raw
            if not ability.get("true_damage"):
                amount = combat.damage_after_defense(raw, combat._resistance_multiplier(actor, element),
                    0 if ability.get("ignores_defense") else combat._actor_defense(actor), rules)
                amount = combat._modified_received_damage(session, amount, element, enemy,
                    ability.get("name", ""), ability.get("id", ""))
                status = session.get("combat", {}).get("player_status", {})
                guard = status.get("guard_multiplier", 1) if status.get("guard_disabled_round", 0) < session["combat"]["round"] else 1
                amount = max(0, round(amount * guard))
            values.append((amount, probability * chance))
        mu = sum(value * probability for value, probability in values)
        var = max(0.0, sum(value ** 2 * probability for value, probability in values) - mu ** 2)
        hits = max(1, int(ability.get("hits_per_element" if ability.get("multi_elements") else "hits", 1)))
        mean += hits * mu
        variance += hits * var
    return mean, variance


def phase_moments(session: dict[str, Any], *, damaging_only: bool = False) -> dict[str, Any]:
    """Current enemy phase, with exact AI availability and without consuming game RNG."""
    total, variance, notes = 0.0, 0.0, set()
    cap = combat._combat_rules(session).get("elite_percentage_round_cap")
    states = {0: (1.0, 0.0, 0.0)}
    for original in combat._alive_enemies(session["combat"]):
        if original.get("skip_rounds_remaining", 0) > 0:
            continue
        skip = 0.0
        if session.get("difficulty") == "normal":
            statuses = original.get("statuses", [])
            skip = 1.0 if any(s.get("kind") == "skip_turn" for s in statuses) else 1-math.prod(
                1-float(s.get("modifiers", {}).get("skip_chance", 0)) for s in statuses)
            if skip >= 1:
                continue
        choices = []

        class CaptureChoices:
            def choices(self, entries, *, weights, k):
                choices.extend(zip(entries, weights))
                return entries[:1]

        charging = original.get("charging")
        if charging:
            if session["combat"]["round"] < charging["release_round"]:
                continue
            chosen = {k: v for k, v in charging["ability"].items() if k != "telegraph"}
        else:
            chosen = combat._choose_enemy_ability(deepcopy(original), session, CaptureChoices())
        choices = choices or [(chosen, 1)]
        if damaging_only:
            choices = [(ability, weight) for ability, weight in choices
                       if combat._ability_kind(ability) not in {"heal", "field", "status", "defend", "stance"}]
        if not choices:
            continue
        weight = sum(w for _, w in choices)
        mu, second = 0.0, 0.0
        outcomes = []
        for ability, w in choices:
            if ability.get("telegraph"):
                notes.add("telegraph_charge")
                am, av = 0.0, 0.0
            elif combat._ability_kind(ability) in {"heal", "field", "status", "defend", "stance"}:
                notes.add(combat._ability_kind(ability))
                am, av = 0.0, 0.0
            else:
                am, av = attack_moments(ability, original, session)
            mu += am * w / weight
            second += (av + am ** 2) * w / weight
            if cap is not None:
                percent = (ability.get("damage_max_hp_ratio") is not None and not ability.get("telegraph")
                           and original.get("encounter_class", session["combat"]["encounter"].get("encounter_class")) == "elite")
                chance = combat.attack_chance(session, original, session["character"], ability, original["id"]) / 100
                if percent:
                    outcomes.extend([(w/weight * (1-skip) * chance, round(am/chance), 0, True),
                                     (w/weight * (1-skip) * (1-chance), 0, 0, True)])
                else:
                    outcomes.append((w/weight * (1-skip), am, av, False))
        if cap is not None:
            outcomes.append((skip, 0, 0, False))
            updated = defaultdict(lambda: [0.0, 0.0, 0.0])
            for spent, (probability, first, square) in states.items():
                for chance, amount, var, percent in outcomes:
                    if percent:
                        amount = min(amount, max(0, int(session["character"]["max_hp"] * cap)-spent))
                    key = spent + amount if percent else spent
                    values = updated[key]
                    values[0] += probability * chance
                    values[1] += chance * (first + probability * amount)
                    values[2] += chance * (square + 2*amount*first + probability*(var+amount*amount))
            states = dict(updated)
        mu, second = mu*(1-skip), second*(1-skip)
        total += mu
        variance += max(0.0, second - mu ** 2)
    if cap is not None:
        total = sum(value[1] for value in states.values())
        variance = max(0, sum(value[2] for value in states.values())-total*total)
    return {"expected_damage": total, "variance": variance,
            "cv": math.sqrt(variance) / total if total else None,
            "ratio": total / session["character"]["max_hp"], "notes": sorted(notes)}


def formula_distribution(formula: str, actor: dict[str, Any]) -> dict[int, float]:
    distribution = {0: 1.0}
    for term in re.findall(r"[+-]?[^+-]+", combat._normalize_formula(formula) or "1"):
        sign = -1 if term.startswith("-") else 1
        token = term.lstrip("+-")
        dice = re.fullmatch(r"(\d*)d(\d+)", token)
        if dice:
            count, sides = max(1, min(int(dice[1] or 1), 20)), max(2, int(dice[2]))
            terms = [{sign * face: 1 / sides for face in range(1, sides + 1)}] * count
        else:
            terms = [{sign * int(formula_mean(token, actor)): 1.0}]
        for values in terms:
            combined: dict[int, float] = defaultdict(float)
            for left, lp in distribution.items():
                for right, rp in values.items():
                    combined[left + right] += lp * rp
            distribution = dict(combined)
    result: dict[int, float] = defaultdict(float)
    for value, probability in distribution.items():
        result[max(0, value)] += probability
    return dict(result)


def attack_expectation(ability: dict[str, Any], enemy: dict[str, Any], actor: dict[str, Any], rules: dict[str, Any]) -> float:
    chance = max(5, min(100, int(ability.get("accuracy", 85)) - int(actor.get("combat", {}).get("evade", 0)))) / 100
    multiplier = combat._resistance_multiplier(actor, ability.get("element", "physical"))
    defense = combat._actor_defense(actor)
    return chance * sum(probability * combat.damage_after_defense(
        max(0, round(raw * float(ability.get("damage_multiplier", 1)))), multiplier, defense, rules)
        for raw, probability in formula_distribution(str(ability.get("damage") or ability.get("dice_type") or "1d4"), enemy).items())


def incoming_damage_budget(pack: dict[str, Any], checkpoints: dict[str, Any], targets: dict[str, Any]) -> list[dict[str, Any]]:
    """Full-health opening enemy phase, all foes alive, before player guard/heal/kills.

    Weights and affordability match enemy AI. Status conversion is not HP damage;
    fields/heals are recorded separately, so scripted battles are not certified.
    """
    rows = []
    catalog = {e["id"]: e for e in pack["enemies"]}
    for encounter, cls in targets["encounters"].items():
        for character in selected_characters(pack, encounter, ["all"]):
            session = prepare_session(pack, encounter, character, checkpoints)
            actor = session["character"]
            location = session["scenario_pack"]["locations"][0]
            guest = location["combat"].get("player_character_id")
            if guest:
                actor = combat._runtime_player_character(next(c for c in pack["characters"] if c["id"] == guest))
            total, notes = 0.0, set()
            for eid in combat._encounter_for_session(session, session["scenario_pack"])["enemy_ids"]:
                enemy = catalog[eid]
                skills = [s for s in enemy.get("skills", []) if combat._can_pay_cost(enemy, s)
                          and float(s.get("use_below_hp_ratio", 1)) >= 1]
                if not skills:
                    skills = [combat._merge_dict(combat._combat_rules(session)["enemy_basic_attack"], enemy.get("combat", {}).get("basic_attack"))]
                weight_sum = sum(max(1, int(s.get("ai_weight", 1))) for s in skills)
                for skill in skills:
                    kind = combat._ability_kind(skill)
                    if kind in {"heal", "field", "status"}:
                        notes.add(kind)
                        continue
                    total += max(1, int(skill.get("ai_weight", 1))) / weight_sum * attack_expectation(skill, enemy, actor, combat._combat_rules(session))
            limit = targets.get("incoming_damage_budget", {}).get(cls)
            ratio = total / actor["max_hp"]
            rows.append(dict(encounter=encounter, character=character, level=actor.get("level", 1),
                             max_hp=actor["max_hp"], expected_damage=total, ratio=ratio, limit=limit,
                             over_budget=limit is not None and ratio > limit + 1e-12, notes=sorted(notes)))
    return rows
