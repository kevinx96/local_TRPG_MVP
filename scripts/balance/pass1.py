from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from host import combat, state
from . import sim
from .budget import incoming_damage_budget
from .checkpoints import DEFAULT_CHECKPOINTS, DEFAULT_SCENARIO


def evaluate(pack: dict[str, Any], checkpoints: dict[str, Any], encounters: list[str], n: int,
             *, skills: str = "none", companion: bool = True, attack_only: bool = True) -> list[dict[str, Any]]:
    rows = []
    for encounter in encounters:
        for character in sim.selected_characters(pack, encounter, ["all"]):
            policies = ["heuristic", "attack_only"] if attack_only else ["heuristic"]
            for policy in policies:
                rows.append(sim.simulate(pack, encounter, character, policy, checkpoints=checkpoints,
                                         n=n, skill_variant=skills, companion=companion))
    return rows


def objective(rows: list[dict[str, Any]], targets: dict[str, Any]) -> float:
    violations = sim.check_results(rows, targets)
    score = len(violations)
    for violation in violations:
        lo, hi = violation["target"]
        value = violation["value"]
        distance = 1 if value is None else max(lo - value, value - hi, 0)
        scale = {"win_rate": 12, "hp_left": 4, "rounds": .25, "class_spread": 10,
                 "attack_only_win_rate": 5}[violation["metric"]]
        score += distance * scale
    return score


def enemy_groups(pack: dict[str, Any], checkpoints: dict[str, Any], targets: dict[str, Any]) -> list[tuple[list[str], list[str]]]:
    groups: list[tuple[set[str], set[str]]] = []
    for encounter, cls in targets["encounters"].items():
        if cls in {"scripted_loss", "guest"}:
            continue
        session = sim.prepare_session(pack, encounter, "hero", checkpoints)
        enemies = set(combat._encounter_for_session(session, session["scenario_pack"])["enemy_ids"])
        names = {encounter}
        remaining = []
        for previous_enemies, previous_names in groups:
            if previous_enemies & enemies:
                enemies |= previous_enemies
                names |= previous_names
            else:
                remaining.append((previous_enemies, previous_names))
        groups = remaining + [(enemies, names)]
    return [(sorted(e), sorted(n)) for e, n in groups]


def apply_parameters(pack: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(pack)
    for enemy in result["enemies"]:
        change = parameters.get(enemy["id"])
        if not change:
            continue
        if "hp" in change:
            enemy["hp"] = change["hp"]
            if enemy["max_hp"] > 0:
                enemy["max_hp"] = change["hp"]
        for key in ("defense", "evade"):
            if key in change:
                enemy.setdefault("combat", {})[key] = change[key]
        abilities = [enemy["combat"]["basic_attack"], *enemy.get("skills", [])]
        for ability in abilities:
            if "damage" in ability or ability is abilities[0]:
                if "damage" in change:
                    ability["damage"] = change["damage"]
                    if "dice_type" in ability:
                        ability["dice_type"] = change["damage"]
                if "accuracy" in change:
                    ability["accuracy"] = change["accuracy"]
    for location in result["locations"]:
        if location["id"] in parameters.get("counts", {}):
            location["combat"]["enemy_ids"] = parameters["counts"][location["id"]]
    return result


def search(pack: dict[str, Any], checkpoints: dict[str, Any], targets: dict[str, Any], n: int,
           iterations: int, output: Path) -> None:
    rng = random.Random(4)
    parameters: dict[str, Any] = {"counts": {}}
    # First reduce repeated enemies, retaining every original species.
    for location in pack["locations"]:
        encounter = location.get("combat", {})
        enemies = encounter.get("enemy_ids", [])
        if len(enemies) > 1:
            parameters["counts"][location["id"]] = list(dict.fromkeys(enemies))
    history = []
    for enemies, encounters in enemy_groups(pack, checkpoints, targets):
        best_parameters = deepcopy(parameters)
        current = apply_parameters(pack, parameters)
        best_rows = evaluate(current, checkpoints, encounters, n)
        best_score = objective(best_rows, targets)
        catalog = {e["id"]: e for e in current["enemies"]}
        for index in range(iterations):
            proposal = deepcopy(best_parameters)
            for eid in enemies:
                source = catalog[eid]
                if index < iterations // 2:
                    hp = rng.choice([12, 18, 24, 32, 40, 52, 64, 80, 100])
                    damage = rng.choice(["1d2", "1d3", "1d4", "1d4+1", "1d6", "1d6+1"])
                    defense = rng.choice([0, 0, 1, 2])
                    accuracy = rng.choice([65, 80, 90, 100])
                else:
                    existing = best_parameters.get(eid, {})
                    hp = max(4, abs(existing.get("hp", source["hp"])) + rng.choice([-8, -4, 0, 4, 8]))
                    damage = rng.choice([existing.get("damage", "1d4")] * 3 + ["1d2", "1d3", "1d4", "1d4+1", "1d6", "1d6+1"])
                    defense = max(0, existing.get("defense", source["combat"].get("defense", 0)) + rng.choice([-1, 0, 0, 1]))
                    accuracy = max(30, min(100, existing.get("accuracy", 85) + rng.choice([-5, 0, 5])))
                proposal[eid] = dict(hp=-hp if source["hp"] < 0 else hp, damage=damage, defense=defense, accuracy=accuracy)
            tested = apply_parameters(pack, proposal)
            rows = evaluate(tested, checkpoints, encounters, n)
            score = objective(rows, targets)
            history.append(dict(enemies=enemies, index=index, score=score,
                                parameters={e: proposal[e] for e in enemies}))
            if score < best_score:
                best_score, best_parameters, best_rows = score, proposal, rows
        parameters = best_parameters
        print(json.dumps(dict(enemies=enemies, score=best_score, parameters={e: parameters.get(e) for e in enemies}), ensure_ascii=False), flush=True)
        output.write_text(json.dumps(dict(parameters=parameters, n=n, iterations=iterations, history=history), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def refine(pack: dict[str, Any], checkpoints: dict[str, Any], targets: dict[str, Any], source: Path, output: Path) -> None:
    coarse = json.loads(source.read_text(encoding="utf-8"))
    parameters = coarse["parameters"]
    refined = []
    for enemies, encounters in enemy_groups(pack, checkpoints, targets):
        proposals = [{e: parameters[e] for e in enemies if e in parameters}]
        proposals += [h["parameters"] for h in sorted(coarse["history"], key=lambda h: h["score"])
                      if h["enemies"] == enemies][:5]
        # Inspect low-damage alternatives after the required count reduction.
        for damage in ("1d2", "1d3", "1d4"):
            proposals.append({e: {**parameters.get(e, {}), "damage": damage} for e in enemies})
        if enemies == ["zebok"]:
            # Two holy consumables solve the damage type, not conversion or turn pacing.
            proposals += [{"zebok": {"damage": d, "hp": -100, "defense": 0, "accuracy": a}}
                          for d in ("1d2", "1d4", "1d6") for a in (65, 90)]
        best = None
        for proposal in proposals:
            params = {**parameters, **proposal}
            tested = apply_parameters(pack, params)
            rows = evaluate(tested, checkpoints, encounters, 64)
            local_targets = {**targets, "encounters": {e: targets["encounters"][e] for e in encounters}}
            budgets = incoming_damage_budget(tested, checkpoints, local_targets)
            excess = sum(max(0, b["ratio"] - (b["limit"] or 1)) for b in budgets)
            score = objective(rows, targets) + 20 * excess
            record = dict(enemies=enemies, parameters=proposal, score=score, budget_excess=excess, rows=rows)
            refined.append(record)
            if best is None or score < best["score"]:
                best = record
        parameters.update(best["parameters"])
        print(json.dumps(dict(enemies=enemies, score=best["score"], parameters=best["parameters"])), flush=True)
    output.write_text(json.dumps(dict(coarse=coarse, refinement_n=64, refinement=refined,
                                     parameters=parameters), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline first balance pass: small-N search or final matrix")
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINTS)
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--refine", type=Path)
    parser.add_argument("--iterations", type=int, default=80)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pack = state.load_scenario_pack(args.scenario)
    checkpoints = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    if args.refine:
        refine(pack, checkpoints, targets, args.refine, args.output)
        return
    if args.search:
        search(pack, checkpoints, targets, args.n, args.iterations, args.output)
        return
    started = time.perf_counter()
    paths = [args.scenario, args.checkpoint, sim.TARGETS, sim.SKILL_CANDIDATES,
             Path(__file__), Path(sim.__file__), Path(combat.__file__), Path(state.__file__),
             Path(__file__).with_name("budget.py"), Path(__file__).with_name("checkpoints.py"),
             Path(state.__file__).with_name("scenario_context.py"), Path(state.__file__).with_name("item_mechanics.py")]
    result: dict[str, Any] = {"n": args.n, "seed": 20261011, "rows": [],
                             "fingerprints": {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                             "budget": incoming_damage_budget(pack, checkpoints, targets)}
    for skills, companion in [("none", True), ("A", True), ("none", False)]:
        for encounter in targets["encounters"]:
            result["rows"] += evaluate(pack, checkpoints, [encounter], args.n, skills=skills,
                                       companion=companion, attack_only=companion)
            print(f"skills={skills} companion={companion} {encounter}", flush=True)
        result["elapsed_seconds"] = time.perf_counter() - started
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
