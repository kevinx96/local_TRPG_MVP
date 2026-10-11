from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from functools import partial
from itertools import product
from pathlib import Path
from typing import Any
from unittest.mock import patch

from host import state
from . import ch34, checkpoints, route, sim

BASELINE = {
    "valley_entrance": dict(enemy="ash_wraith", count=2, hp=22, damage="1d24", accuracy=40, physical=.5),
    "valley_ledge": dict(enemy="lava_drake", count=2, hp=25, damage="1d20", accuracy=75, physical=.5),
}


def apply_parameters(pack: dict[str, Any], parameters: dict[str, Any]) -> None:
    for location_id, values in parameters.items():
        location = next(l for l in pack["locations"] if l["id"] == location_id)
        location["combat"]["enemy_ids"] = [values["enemy"]] * values["count"]
        enemy = next(e for e in pack["enemies"] if e["id"] == values["enemy"])
        enemy.update(hp=values["hp"], max_hp=values["hp"])
        enemy["resistances"]["physical"] = values["physical"]
        for attack in [enemy["combat"]["basic_attack"], *enemy["skills"]]:
            if attack is enemy["combat"]["basic_attack"] or attack.get("kind") == "attack":
                attack.update(damage=values["damage"], accuracy=values["accuracy"])


def violations(result: dict[str, Any]) -> list[dict[str, Any]]:
    failures = ch34.violations(result)
    rows = [r for r in result["routes"] if r["preparation"] == "paid_rest"]
    total = sum(sum(row["failure_counts"].values()) for row in rows)
    d1 = sum(row["failure_counts"].get("valley_entrance", 0) for row in rows)
    if d1 * 3 > total:
        failures.append(dict(character="all", metric="d1_failure_share",
                             value=d1 / total, target=[0, 1 / 3]))
    if rows:
        spread = max(r["completion_rate"] for r in rows) - min(r["completion_rate"] for r in rows)
        if spread > .25 + 1e-12:
            failures.append(dict(character="all", metric="class_spread", value=spread, target=[0, .25]))
    return failures


def evaluate(pack: dict[str, Any], cp: dict[str, Any], n: int, seed: int, elite_holy: bool) -> dict[str, Any]:
    result: dict[str, Any] = dict(encounters=[], routes=[])
    with patch.object(sim, "choose_action", partial(sim.choose_action, elite_holy_water=elite_holy)):
        for encounter in BASELINE:
            for character in ch34.CHARACTERS:
                row = sim.simulate(pack, encounter, character, checkpoints=cp, n=n, seed=seed)
                result["encounters"].append(row)
                print(encounter, character, row["win_rate"], flush=True)
        for character in ch34.CHARACTERS:
            row = route.simulate_route(pack, cp, character, n=n, seed=seed, rest_policy="hp70")
            row["preparation"] = "paid_rest"
            result["routes"].append(row)
            print("hp70", character, row["completion_rate"], flush=True)
    result["violations"] = violations(result)
    return result


def search(pack: dict[str, Any], cp: dict[str, Any], n: int, seed: int, output: Path,
           refine: bool = False, boundary: bool = False) -> None:
    rows = []
    for encounter, baseline in BASELINE.items():
        grid = (product((1, 2), (18, 22, 26, 30), (20, 24, 28), (40,), (.7,))
                if encounter == "valley_entrance" else
                product((2,), (12, 16, 20, 25), (8, 12, 16, 20), (55, 75), (.7,)))
        if refine:
            grid = product((2,), (8, 12, 16), (24, 32, 40, 48), (30, 40, 55), (.7,))
        if boundary:
            grid = (list(product((2,), (4, 6, 8), (24, 32, 40, 48, 56), (20, 30, 35), (.7,)))
                    + list(product((1,), (51, 54, 58), (12, 20, 28), (40, 60), (.7,)))
                    if encounter == "valley_entrance" else
                    product((2,), (6, 8, 10, 12), (18, 20, 22, 24, 26), (40, 45, 50, 55), (.7,)))
        for count, hp, damage, accuracy, physical in grid:
            values = dict(baseline, count=count, hp=hp, damage=f"1d{damage}", accuracy=accuracy, physical=physical)
            candidate = deepcopy(pack)
            apply_parameters(candidate, {encounter: values})
            rates = [sim.simulate(candidate, encounter, c, checkpoints=cp, n=n, seed=seed)["win_rate"]
                     for c in ch34.CHARACTERS]
            penalty = sum(max(.75 - r, 0, r - .90) for r in rates)
            row = dict(encounter=encounter, parameters=values, rates=rates, penalty=penalty)
            rows.append(row)
            print(encounter, values, rates, round(penalty, 3), flush=True)
            output.write_text(json.dumps(dict(n=n, seed=seed, characters=ch34.CHARACTERS, rows=rows),
                                         ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="022 offline balance search and policy ablation")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--refine", action="store_true")
    parser.add_argument("--boundary", action="store_true")
    parser.add_argument("--stages", nargs="+", choices=("baseline", "policy_only", "final"),
                        default=["baseline", "policy_only", "final"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.n < 1:
        parser.error("n must be positive")
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.search:
        search(pack, cp, args.n, args.seed, args.output, args.refine, args.boundary)
        return
    paths = (checkpoints.DEFAULT_SCENARIO, checkpoints.DEFAULT_CHECKPOINTS, Path(__file__),
             Path(sim.__file__), Path(route.__file__), checkpoints.ROOT / "scripts/scenario/tune_ch34.py")
    result: dict[str, Any] = dict(n=args.n, seed=args.seed, baseline_parameters=BASELINE, stages={},
        fingerprints={p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    for stage in args.stages:
        candidate = deepcopy(pack)
        if stage != "final":
            apply_parameters(candidate, BASELINE)
        print(stage, flush=True)
        result["stages"][stage] = evaluate(candidate, cp, args.n, args.seed, stage != "baseline")
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.check and result["stages"].get("final", {}).get("violations"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
