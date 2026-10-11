from __future__ import annotations

import argparse
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from typing import Any

from host import state
from . import checkpoints, route, sim
from .pass1 import apply_parameters


def apply(pack: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    result = apply_parameters(pack, parameters.get("enemies", {}))
    for enemy in result["enemies"]:
        if enemy["id"] in parameters.get("rewards", {}):
            quantities = parameters["rewards"][enemy["id"]]
            items = enemy["rewards"]["items"]
            for name, quantity in quantities.items():
                items[:] = [i for i in items if i["name"] != name]
                if quantity:
                    items.append(dict(name=name, quantity=quantity))
    if parameters.get("inn_restore"):
        inn = next(l for l in result["locations"] if l["id"] == "inn")
        action = next(a for parent in inn["actions"] for a in parent.get("children", []) if a["id"] == "rest_at_inn")
        if {"restore_full": True} not in action["effects"]:
            action["effects"].append({"restore_full": True})
    return result


def snapshots(pack: dict[str, Any], cp: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(cp)
    for entry in result["encounters"].values():
        for character, cell in entry["characters"].items():
            session = checkpoints.fresh_session(pack, character)
            cell["sources"] = [checkpoints.replay_step(session, s["step"]) for s in cell["sources"]]
            for key in ("inventory", "equipment", "gold", "skills", "attributes", "max_hp", "max_mp", "max_sp", "level"):
                cell[key] = deepcopy(session["character"][key])
    return result


def evaluate(pack: dict[str, Any], cp: dict[str, Any], targets: dict[str, Any], n: int,
             endpoints: list[str]) -> dict[str, Any]:
    rows = [route.simulate_route(pack, cp, c, encounter=e, n=n)
            for e in endpoints for c in targets["route_targets"]["characters"]]
    selected = deepcopy(targets)
    selected["route_targets"]["routes"] = {e: targets["route_targets"]["routes"][e] for e in endpoints}
    violations = route.check_results(rows, selected)
    score = sum(max(v["target"][0] - v["value"], 0, v["value"] - v["target"][1]) ** 2 for v in violations)
    return dict(score=score, rows=rows, violations=violations)


def evaluate_candidate(args: tuple) -> dict[str, Any]:
    pack, cp, targets, n, endpoints, proposal, single_check = args
    candidate = apply(pack, proposal["parameters"])
    result = evaluate(candidate, cp, targets, n, endpoints)
    for row in result["rows"]:
        row.pop("sample_trial", None)
    if single_check:
        candidate_cp = snapshots(candidate, cp)
        singles = [sim.simulate(candidate, e, c, p, checkpoints=candidate_cp, n=n)
                   for e in targets["encounters"] for c in sim.selected_characters(candidate, e, ["all"])
                   for p in ("heuristic", "attack_only")]
        violations = sim.check_results(singles, targets)
        result.update(single_rows=singles, single_violations=violations,
                      single_score=sum(max(v["target"][0] - v["value"], 0,
                                           v["value"] - v["target"][1]) ** 2 for v in violations))
    return {**proposal, **result}


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline route-first search; candidates never modify the scenario")
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--n", type=int, default=16)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--single-check", action="store_true")
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--routes", nargs="+", default=["dragon_valley_loc", "goblin_fort_fourth"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.n < 1 or args.workers < 1 or args.shards < 1 or not 0 <= args.shard < args.shards:
        parser.error("invalid n, workers or shard")
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    result = dict(n=args.n, seed=20261011, baseline_commit=subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True).strip(), candidates=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tasks = [(pack, cp, targets, args.n, args.routes, p, args.single_check)
             for p in json.loads(args.candidates.read_text(encoding="utf-8"))]
    tasks = tasks[args.shard::args.shards]
    with ProcessPoolExecutor(max_workers=args.workers) if args.workers > 1 else nullcontext() as pool:
        run = pool.map if pool else map
        for evaluated in run(evaluate_candidate, tasks):
            result["candidates"].append(evaluated)
            print(evaluated["name"], round(evaluated["score"], 4),
                  [r["completion_rate"] for r in evaluated["rows"]], flush=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
