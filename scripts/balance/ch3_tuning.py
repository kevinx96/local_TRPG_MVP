"""Offline in-memory companion search for spec 037; never writes scenario packs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any

from host import state
from . import ch3_routes, checkpoints, gorge


def variants() -> list[dict[str, Any]]:
    return [dict(companion="paladin_liese", damage=f"2d{sides}", heal_ratio=ratio)
            for sides in range(3, 7) for ratio in (.15, .20, .25)] + [
        dict(companion=gorge.ELIO, damage=f"2d{sides}", period=period)
        for sides in range(3, 7) for period in (2, 3, 4)]


def critical_ratios() -> list[float]:
    # This cursed route skips the life-fruit knight; only Lv3/4/5 HP caps occur.
    caps = (28, 32, 36)
    ratios = [percent/100 for percent in range(15, 26)]
    profile = lambda ratio: tuple(math.floor(hp * ratio + .5) for hp in caps)
    seen = {profile(ratio) for ratio in ratios}
    boundaries = sorted({.15, .25, *((amount+.5)/hp for hp in caps for amount in range(hp)
                                    if .15 < (amount+.5)/hp < .25)})
    for left, right in zip(boundaries, boundaries[1:]):
        ratio = (left + right) / 2
        if profile(ratio) not in seen:
            ratios.append(ratio)
            seen.add(profile(ratio))
    return sorted(ratios)


def configure(pack: dict[str, Any], variant: dict[str, Any]) -> None:
    effects = next(c for c in pack["companions"] if c["id"] == variant["companion"])["round_start_effects"]
    for effect in effects:
        if effect["kind"] == "damage_enemy":
            effect["damage"] = variant["damage"]
        elif "max_hp_ratio" in effect:
            effect["max_hp_ratio"] = variant["heal_ratio"]
        elif "every_n_rounds" in effect:
            effect["every_n_rounds"] = variant["period"]


def parse_variant(value: str) -> dict[str, Any]:
    try:
        companion, damage, number = value.split(":")
        if damage not in {"2d3", "2d4", "2d5", "2d6"}:
            raise ValueError
        if companion == "liese" and .15 <= float(number) <= .25:
            return dict(companion="paladin_liese", damage=damage, heal_ratio=float(number))
        if companion == "elio" and int(number) in (2, 3, 4):
            return dict(companion=gorge.ELIO, damage=damage, period=int(number))
        raise ValueError
    except ValueError as error:
        raise argparse.ArgumentTypeError("Expected liese:2d3..2d6:0.15..0.25 or elio:2d3..2d6:2..4") from error


def _job(job: tuple[Any, ...]) -> dict[str, Any]:
    variant, arguments = job
    row = ch3_routes._job(arguments)
    for key in ("samples", "preparation_sources", "start"):
        row.pop(key)
    return dict(variant=variant, **row)


def rank_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    controls = [r for r in rows if r["variant"] is None and r["companion"] not in ch3_routes.COUNTERS.values()]
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["variant"]:
            groups.setdefault(json.dumps(row["variant"], sort_keys=True), []).append(row)
    complete = [group for group in groups.values() if len(group) == 24]
    result = []
    for left in complete:
        if left[0]["companion"] != "paladin_liese":
            continue
        for right in complete:
            if right[0]["companion"] != gorge.ELIO:
                continue
            comparisons = ch3_routes.comparisons([*controls, *left, *right])["counters"]
            result.append(dict(liese=left[0]["variant"], elio=right[0]["variant"],
                passed=sum(r["passed"] for r in comparisons), total=len(comparisons),
                min_margin_pp=min(r["margin_pp"] for r in comparisons),
                failures=[r for r in comparisons if not r["passed"]]))
    return sorted(result, key=lambda r: (-r["passed"], -r["min_margin_pp"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20261018)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--variant", type=parse_variant, action="append")
    parser.add_argument("--no-controls", action="store_true")
    parser.add_argument("--critical-thief", action="store_true", help="Unprepared cursed battlefield; all distinct healing amounts")
    parser.add_argument("--output", type=Path, default=checkpoints.ROOT / "eval/reports/037-companion-search.json")
    args = parser.parse_args()
    if min(args.n, args.workers) < 1:
        parser.error("n and workers must be positive")
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    jobs = []
    candidates = args.variant or ([dict(companion="paladin_liese", damage=f"2d{sides}", heal_ratio=ratio)
        for sides in range(3, 7) for ratio in critical_ratios()] if args.critical_thief else variants())
    for variant in [*([None] if not args.no_controls else []), *candidates]:
        candidate = deepcopy(pack)
        if variant:
            configure(candidate, variant)
        for character in ch3_routes.CHARACTERS:
            if args.critical_thief and character != "thief":
                continue
            start = ch3_routes.starting_checkpoint(candidate, cp, character)
            for condition in ch3_routes.conditions():
                if args.critical_thief and (condition["path"], condition["prepared"], condition["cursed"]) != ("battlefield", False, True):
                    continue
                if variant and condition["companion"] != variant["companion"]:
                    continue
                jobs.append((variant, (character, start, condition, args.n, args.seed)))
    result = dict(n=args.n, seed=args.seed, workers=args.workers, rows=[],
                  fingerprints={str(p.relative_to(checkpoints.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (Path(__file__), Path(ch3_routes.__file__), checkpoints.DEFAULT_SCENARIO, checkpoints.ROOT / "host/state.py")})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(gorge._map_jobs(_job, jobs, args.workers), 1):
        result["rows"].append(row)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if index % 24 == 0 or index == len(jobs):
            print(f"{index}/{len(jobs)}", flush=True)
    result["pairs"] = rank_pairs(result["rows"])
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
