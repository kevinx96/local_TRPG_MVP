from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from typing import Any

from host import state
from . import checkpoints, sim
from .pass1 import apply_parameters, enemy_groups, objective
from .pass2 import search_rows


def search_group(args: tuple) -> dict[str, Any]:
    pack, cp, targets, enemies, encounters, iterations = args
    rng = random.Random(700 + sum(map(ord, enemies[0])))
    catalog = {e["id"]: e for e in pack["enemies"]}
    proposals = []
    best: dict[str, Any] = {}
    best_score = float("inf")
    for index in range(iterations + 1):
        proposal = deepcopy(best)
        if index:
            for eid in enemies:
                source = catalog[eid]
                previous = best.get(eid, {})
                if index < iterations // 2:
                    hp = rng.choice([12, 18, 24, 32, 40, 48, 56, 64, 80, 100])
                    damage = rng.choice(["1d3", "1d4", "1d6", "1d8", "1d10", "1d12"])
                    accuracy = rng.choice([55, 70, 85, 100])
                    defense = rng.choice([0, 0, 1, 2])
                    evade = rng.choice([0, 5, 10])
                else:
                    hp = max(4, abs(previous.get("hp", source["hp"])) + rng.choice([-8, -4, 0, 4, 8]))
                    damage = rng.choice([previous.get("damage", source["combat"]["basic_attack"]["damage"])] * 4
                                        + ["1d3", "1d4", "1d6", "1d8", "1d10"])
                    accuracy = max(30, min(100, previous.get("accuracy", source["combat"]["basic_attack"].get("accuracy", 85)) + rng.choice([-5, 0, 5])))
                    defense = max(0, previous.get("defense", source["combat"].get("defense", 0)) + rng.choice([-1, 0, 1]))
                    evade = max(0, previous.get("evade", source["combat"].get("evade", 0)) + rng.choice([-2, 0, 2]))
                proposal[eid] = dict(hp=-hp if source["hp"] < 0 else hp, damage=damage,
                                     accuracy=accuracy, defense=defense, evade=evade)
        rows = search_rows(apply_parameters(pack, proposal), cp, encounters, 16, targets)
        value = objective(rows, targets)
        proposals.append(dict(parameters=proposal, score=value))
        if value < best_score:
            best_score, best = value, proposal
    unique = {json.dumps(p["parameters"], sort_keys=True): p for p in sorted(proposals, key=lambda p: -p["score"])}
    finalists = sorted(unique.values(), key=lambda p: p["score"])[:5]
    if not any(not p["parameters"] for p in finalists):
        finalists.append(dict(parameters={}, score=proposals[0]["score"]))
    for p in finalists:
        rows = search_rows(apply_parameters(pack, p["parameters"]), cp, encounters, 64, targets)
        p["refined_score"] = objective(rows, targets)
        p["rows"] = rows
    return dict(enemies=enemies, encounters=encounters, proposals=proposals,
                finalists=finalists, selected=min(finalists, key=lambda p: p["refined_score"]))


def confirm_cell(args: tuple) -> dict[str, Any]:
    pack, cp, encounter, character, policy, companion, n = args
    return sim.simulate(pack, encounter, character, policy, checkpoints=cp, companion=companion, n=n)


def refine_elite(args: tuple) -> dict[str, Any]:
    pack, cp, targets, enemies, encounters = args
    rng = random.Random(703 + sum(map(ord, enemies[0])))
    candidates = []
    for index in range(100):
        params = {} if not index else {eid: dict(hp=rng.choice([24, 28, 32, 36, 40, 44, 48, 56, 64, 72]),
                                                 damage=rng.choice(["1d12", "1d16", "1d20", "2d10", "2d12"]),
                                                 accuracy=rng.choice([35, 45, 55, 65, 75, 85]),
                                                 defense=rng.choice([0, 0, 1]), evade=rng.choice([0, 5, 10]))
                                              for eid in enemies}
        rows = search_rows(apply_parameters(pack, params), cp, encounters, 16, targets)
        candidates.append(dict(parameters=params, score=objective(rows, targets)))
    finalists = sorted(candidates, key=lambda p: p["score"])[:5]
    finalists.append(candidates[0])
    for p in finalists:
        p["rows"] = search_rows(apply_parameters(pack, p["parameters"]), cp, encounters, 64, targets)
        p["refined_score"] = objective(p["rows"], targets)
    return dict(enemies=enemies, encounters=encounters, proposals=candidates,
                finalists=finalists, selected=min(finalists, key=lambda p: p["refined_score"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline pass3 search and confirmation")
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--apply", type=Path)
    parser.add_argument("--refine-elites", type=Path)
    parser.add_argument("--iterations", type=int, default=80)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    if args.apply:
        params = json.loads(args.apply.read_text(encoding="utf-8"))["parameters"]
        for name in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
            path = checkpoints.DEFAULT_SCENARIO.with_name(name)
            raw = json.loads(path.read_text(encoding="utf-8"))
            path.write_text(json.dumps(apply_parameters(raw, params), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        checkpoints.DEFAULT_CHECKPOINTS.write_text(json.dumps(checkpoints.generate(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    started = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) if args.workers > 1 else nullcontext() as pool:
        run_map = pool.map if pool else map
        if args.search or args.refine_elites:
            if args.refine_elites:
                pack = apply_parameters(pack, json.loads(args.refine_elites.read_text(encoding="utf-8"))["parameters"])
            tasks = [(pack, cp, targets, enemies, encounters, args.iterations)
                     for index, (enemies, encounters) in enumerate(enemy_groups(pack, cp, targets))
                     if index % args.shards == args.shard
                     and (not args.refine_elites or all(targets["encounters"][e] == "elite" for e in encounters))]
            result: dict[str, Any] = dict(coarse_n=16, refinement_n=64, groups=[], parameters={})
            for group in run_map(refine_elite if args.refine_elites else search_group,
                                 [t[:-1] for t in tasks] if args.refine_elites else tasks):
                result["groups"].append(group)
                result["parameters"].update(group["selected"]["parameters"])
                print(f"{group['enemies']}: {group['selected']['refined_score']:.3f}", flush=True)
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            tasks = [(pack, cp, e, c, p, companion, args.n) for e in targets["encounters"]
                     for c in sim.selected_characters(pack, e, ["all"])
                     for p, companion in [("heuristic", True), ("attack_only", True), ("heuristic", False)]]
            result = dict(n=args.n, seed=20261011, rows=[])
            tasks = tasks[args.shard::args.shards]
            for row in run_map(confirm_cell, tasks):
                result["rows"].append(row)
                if len(result["rows"]) % 12 == 0:
                    print(f"cells {len(result['rows'])}/{len(tasks)}", flush=True)
            result["violations_after"] = sim.check_results([r for r in result["rows"] if r["companion"]], targets)
            result["check_exit_code"] = int(bool(result["violations_after"]))
    result["elapsed_seconds"] = time.perf_counter() - started
    result["baseline_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkpoints.ROOT, text=True).strip()
    paths = [checkpoints.DEFAULT_SCENARIO, checkpoints.DEFAULT_CHECKPOINTS, sim.TARGETS,
             *[checkpoints.ROOT / p for p in ("host/state.py", "host/combat.py", "host/item_mechanics.py",
               "scripts/balance/sim.py", "scripts/balance/route.py", "scripts/balance/pass3.py")]]
    result["fingerprints"] = {p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
