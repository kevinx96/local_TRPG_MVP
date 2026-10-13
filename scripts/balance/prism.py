from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from host import state
from . import checkpoints, forest_v3, route, sim


def route_violations(rows: list[dict[str, Any]], targets: dict[str, Any]) -> list[dict[str, Any]]:
    violations = []
    for group in ("main", "optional", "reward_only"):
        selected = [r for r in rows if ("reward_only" if r.get("reward_only") else
                    "optional" if r["sidequests"] else "main") == group]
        key = "route_targets" if group == "main" else "route_targets_with_optional"
        scoped = deepcopy(targets)
        scoped[key]["routes"] = {"dragon_valley_loc": targets[key]["routes"]["dragon_valley_loc"]}
        violations.extend({**v, "group": group} for v in route.check_results(selected, scoped, target_key=key))
    return violations


def evaluate(n: int, seed: int) -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    previous_path = checkpoints.ROOT / "eval/reports/balance-2026-10-12-forest-v3.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8"))
    result: dict[str, Any] = {"n": n, "seed": seed, "weapons": [], "routes": [],
        "previous_routes_rejudged": route_violations(previous["routes"], targets),
        "fingerprints": {str(p.relative_to(checkpoints.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in (checkpoints.DEFAULT_SCENARIO, sim.TARGETS, previous_path, Path(__file__),
                                   checkpoints.ROOT / "host/combat.py", Path(sim.__file__), Path(route.__file__),
                                   Path(forest_v3.__file__), Path(checkpoints.__file__))}}
    for character in forest_v3.CHARACTERS:
        before = sim.simulate(pack, "dragon_valley_loc", character, n=n, seed=seed, checkpoints=cp, purify=False)
        after = sim.simulate(pack, "dragon_valley_loc", character, n=n, seed=seed,
                             checkpoints=forest_v3.weapon_checkpoints(pack, cp, character), purify=False)
        weapon = next(i for i in pack["items"] if i["id"] == f"prism_weapon_{character}")
        row = dict(character=character, formula=weapon["combat"]["damage"], before=before["win_rate"],
                   after=after["win_rate"], uplift=after["win_rate"] - before["win_rate"])
        result["weapons"].append(row)
        print("weapon", row, flush=True)
        for optional in (False, True):
            snapshot = forest_v3.reward_route(pack, cp, character) if optional else cp
            row = route.simulate_route(pack, snapshot, character, n=n, seed=seed)
            row["sidequests"] = optional
            result["routes"].append(row)
            print("route", character, optional, row["completion_rate"], flush=True)
        row = forest_v3.reward_only_route(pack, cp, character, n=n, seed=seed)
        result["routes"].append(row)
        print("reward_only", character, row["completion_rate"], flush=True)
    result["weapon_violations"] = forest_v3.check_results(
        {"encounters": [], "weapons": result["weapons"], "routes": []}, targets)
    result["route_violations"] = route_violations(result["routes"], targets)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline prism weapon uplift and route target reassessment")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--output", type=Path, default=Path("eval/reports/balance-2026-10-12-prism.json"))
    args = parser.parse_args()
    result = evaluate(args.n, args.seed)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"weapon violations: {len(result['weapon_violations'])}; route violations: {len(result['route_violations'])}")


if __name__ == "__main__":
    main()
