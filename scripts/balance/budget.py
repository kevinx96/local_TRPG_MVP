from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from host import combat
from .sim import formula_mean, prepare_session, selected_characters


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
