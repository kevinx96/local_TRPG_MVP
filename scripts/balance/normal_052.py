"""052 normal measurements; game rules and frozen baby reducers are unchanged."""
from __future__ import annotations

import random
from copy import deepcopy
from itertools import product
from statistics import mean
from typing import Any
from unittest.mock import patch

from host import combat, state, status_effects
from . import budget, route_v2, snapshots_v3
from .archetypes import CHARACTERS

ESCORT_ORDERS = ("borrow_before_escort", "borrow_after_report")


def opening_moments(session: dict[str, Any]) -> dict[str, Any]:
    """Opening threat without finite shields or the player's defensive stance."""
    if session.get("difficulty") != "normal":
        raise ValueError("052 M9 is normal-only")
    baseline = with_current_dots(session)
    candidate = deepcopy(session)
    candidate["combat"].get("player_status", {}).pop("guard_multiplier", None)
    for status in candidate["character"].get("statuses", []):
        status.pop("shield_remaining", None)
        modifiers = status.get("modifiers", {})
        if modifiers.get("received_damage_multiplier", 1) < 1:
            modifiers.pop("received_damage_multiplier")
    primary = with_current_dots(candidate)
    return {**primary, "max_hp": candidate["character"]["max_hp"],
            "with_shields": baseline, "definition": "opening_without_shields_or_player_stance"}


def with_current_dots(session: dict[str, Any]) -> dict[str, Any]:
    direct = budget.phase_moments(session)
    actor = session["character"]
    damage = variance = 0.0
    for status in actor.get("statuses", []):
        tick = status.get("tick", {})
        if not status_effects.modern(status) or not tick:
            continue
        distribution = budget.formula_distribution(str(tick.get("damage", "0")), status["source"])
        values = []
        for raw, probability in distribution.items():
            raw *= status.get("stacks", 1)
            element = tick.get("element", "physical")
            resistance = combat._resistance_multiplier(actor, element)
            amount = (max(0, round(raw * resistance)) if tick.get("ignore_defense", True) else
                      combat.damage_after_defense(raw, resistance, combat._actor_defense(actor), combat._combat_rules(session)))
            values.append((combat._round_received_damage(session, amount, element), probability))
        mu = sum(v*p for v, p in values)
        damage += mu
        variance += sum(v*v*p for v, p in values)-mu*mu
    total = direct["expected_damage"] + damage
    if not damage:
        return direct
    return {**direct, "direct_expected_damage": direct["expected_damage"], "current_dot_damage": damage,
            "expected_damage": total, "variance": direct["variance"]+variance,
            "ratio": total/actor["max_hp"], "cv": (direct["variance"]+variance)**.5/total if total else None}


def first_three_rounds(pack: dict[str, Any], snapshot: dict[str, Any], seed: int,
                       encounter: str) -> dict[str, Any]:
    """Auxiliary observed starts, replayed in isolation; missing rounds stay missing."""
    session = snapshots_v3.restore(pack, snapshot)
    character = session["character"]["character_id"]
    rng = random.Random(route_v2.sim.trial_seed(seed, "opening:"+encounter, character, 0))
    rows = []
    original = combat._apply_round_start_effects

    def observe(current, source):
        number = current["combat"]["round"]
        if number <= 3:
            rows.append({"round": number, **opening_moments(current)})
        return original(current, source)

    with patch.object(combat, "random", rng), patch.object(state, "random", rng), patch.object(combat, "_apply_round_start_effects", observe):
        session["combat_start_requested"] = True
        session["_balance_free_actions"] = {}
        combat.ensure_combat_started(session)
        while combat.combat_is_active(session) and session["combat"]["round"] <= 3:
            action, target = route_v2.sim.choose_action(session, "heuristic_v3", purify=True, reserve_purification=True)
            route_v2.sim.perform_action(session, action, target, rng)
    return {"rounds": rows, "observed_rounds": len(rows),
            "mean_ratio": mean(row["ratio"] for row in rows) if len(rows) == 3 else None,
            "mean_ratio_with_shields": mean(row["with_shields"]["ratio"] for row in rows) if len(rows) == 3 else None,
            "policy": "heuristic_v3", "seed": route_v2.sim.trial_seed(seed, "opening:"+encounter, character, 0),
            "missing_reason": None if len(rows) == 3 else "Battle ended before three round starts"}


def wilson(wins: int, n: int) -> list[float] | None:
    if not n:
        return None
    z = 1.959963984540054
    p = wins/n
    center = (p+z*z/(2*n))/(1+z*z/n)
    radius = z*((p*(1-p)+z*z/(4*n))/n)**.5/(1+z*z/n)
    return [max(0, center-radius), min(1, center+radius)]


def escort_proposals(args, settings, defaults, run_stage):
    choices = [dict(fire_seed=fire, merchant=merchant, escort_order=escort)
               for fire, merchant, escort in product(("accept", "refuse"), ("betray", "pay"), ESCORT_ORDERS)]
    jobs = [(args.scenario, "P3", character, args.passive_n, args.seed,
             {**settings, "passive_table": defaults["characters"][character]["choices"],
              "branches": choice, "branch_proposal": ":".join(choice.values()), "measure": False})
            for character in CHARACTERS for choice in choices]
    records = run_stage("branch_proposals", jobs)
    result = {}
    for character in CHARACTERS:
        proposals = []
        for choice in choices:
            trials = [r for r in records if r["character"] == character and r["branch_proposal"] == ":".join(choice.values())]
            wins = sum(t["ignis_defeated"] for t in trials)
            proposals.append({"choices": choice, "n": len(trials), "ignis_rate": wins/len(trials),
                              "ignis_ci95": wilson(wins, len(trials)),
                              "completion_rate": mean(t["completed"] for t in trials),
                              "escort_audit": [r.get("escort_audit", {}) for r in trials]})
        best = max(proposals, key=lambda row: row["ignis_rate"])
        result[character] = {"status": "proposed", "selected": best["choices"], "evidence": proposals,
                             "tie": "first listed: accept, betray, borrow_before_escort"}
    return result
