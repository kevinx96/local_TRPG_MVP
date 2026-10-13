from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from concurrent.futures import ProcessPoolExecutor
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from host import state
from . import checkpoints, forest_v3, route, sim

CHARACTERS = ("hero", "cleric", "mage", "thief")
ENCOUNTERS = ("valley_entrance", "valley_ledge", "xanxus_phantom_battle")


def route_checkpoint(pack: dict[str, Any], cp: dict[str, Any], character: str, preparation: str) -> dict[str, Any]:
    if preparation in {"no_rest", "paid_rest"}:
        return cp
    result = forest_v3.reward_route(pack, cp, character) if preparation == "all_optional" else deepcopy(cp)
    actor = result["encounters"]["dragon_valley_loc"]["characters"][character]
    steps = [s["step"] for s in actor["sources"]]
    index = steps.index("leave_burning_house")
    if preparation in {"riku", "all_optional"}:
        steps[index:index + 1] = ["break_burning_beam:success", "visit_village", "return_riku", "rest_at_refuge", "return_frozen_clue"]
    else:
        steps[index + 1:index + 1] = ["visit_village", "rest_at_refuge", "return_frozen_clue"]
    if preparation in {"refuge_supplies", "refuge_prepared"}:
        index = steps.index("return_frozen_clue")
        steps[index:index] = ["shop:gald_shop:holy_water"] * 3 + ["shop:gald_shop:herb"] * 3
    if preparation == "refuge_prepared":
        steps.insert(steps.index("enter_dragon_nest"), "@recover_hp")
    session = checkpoints.fresh_session(pack, character)
    actor["sources"] = [checkpoints.replay_step(session, step) for step in steps]
    return result


def violations(result: dict[str, Any]) -> list[dict[str, Any]]:
    failures = []
    for row in result["encounters"]:
        bounds = [.60, .75] if row["encounter"] == "xanxus_phantom_battle" else [.75, .90]
        if not bounds[0] <= row["win_rate"] <= bounds[1]:
            failures.append(dict(encounter=row["encounter"], character=row["character"], value=row["win_rate"], target=bounds))
    for row in result["routes"]:
        if row["preparation"] == "no_rest":
            continue
        bounds = [.55, .95 if row["preparation"] in {"riku", "all_optional"} else .90]
        if not bounds[0] <= row["completion_rate"] <= bounds[1]:
            failures.append(dict(route=row["preparation"], character=row["character"], value=row["completion_rate"], target=bounds))
    return failures


def evaluate_task(task: tuple) -> tuple[str, dict[str, Any]]:
    kind, identifier, character, n, seed = task
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    if kind == "encounters":
        return kind, sim.simulate(pack, identifier, character, n=n, seed=seed, checkpoints=cp)
    snapshot = route_checkpoint(pack, cp, character, identifier)
    row = route.simulate_route(pack, snapshot, character, n=n, seed=seed,
                               rest_policy="hp70" if identifier == "paid_rest" else "none")
    row["preparation"] = identifier
    return kind, row


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline chapter 3/4 balance; navigation at the lava bridge uses seeded rolls")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--output", type=Path, default=Path("eval/reports/balance-2026-10-12-ch34b.json"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    result: dict[str, Any] = dict(n=args.n, seed=args.seed, encounters=[], routes=[], fingerprints={
        p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (checkpoints.DEFAULT_SCENARIO, checkpoints.DEFAULT_CHECKPOINTS, sim.TARGETS, Path(__file__), Path(route.__file__), Path(sim.__file__))})
    tasks = [(kind, identifier, character, args.n, args.seed)
             for kind, identifiers in (("encounters", ENCOUNTERS), ("routes", ("no_rest", "paid_rest")))
             for identifier in identifiers for character in CHARACTERS]
    with ProcessPoolExecutor(max_workers=args.workers) if args.workers > 1 else nullcontext() as pool:
        rows = pool.map(evaluate_task, tasks) if pool else map(evaluate_task, tasks)
        for kind, row in rows:
            result[kind].append(row)
            print(row.get("encounter", row.get("preparation")), row["character"], row.get("win_rate", row.get("completion_rate")), flush=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["violations"] = violations(result)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Target violations: {len(result['violations'])}")
    if args.check and result["violations"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
