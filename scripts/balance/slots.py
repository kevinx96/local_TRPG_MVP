"""Spec 032: repeat the existing offline policies and frozen reward preparations."""
from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any

from host import shops, state
from . import ch5, checkpoints, class_aware, route, sim, support


ROOT = checkpoints.ROOT
REPORTS = ROOT / "eval/reports"
CHARACTERS = ("hero", "cleric", "mage", "thief")


def read_report(name: str) -> dict[str, Any]:
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def jobs_for(suite: str, n: int, seed: int) -> list[dict[str, Any]]:
    jobs = []
    if suite == "routes":
        previous = read_report("balance-2026-10-13-playtest.json")
        for label, rest, decisions, dice in (
                ("none", "none", "backbone", "forced"), ("hp70", "hp70", "backbone", "forced"),
                ("class_aware", "class_aware", "class_aware", "real"),
                ("hp70_real_dice", "class_aware", "backbone", "real"),
                ("class_aware_no_quests", "class_aware", "class_aware", "real")):
            for character in CHARACTERS:
                jobs.append(dict(suite=suite, character=character, policy_label=label, rest_policy=rest,
                    decisions=decisions, dice=dice,
                    quests=previous["quests"][character] if label == "class_aware" else []))
    elif suite == "finals":
        for character in CHARACTERS:
            for case in support.cases():
                jobs.append(dict(suite=suite, character=character, case=case, encounter="draco_battle"))
    elif suite == "rewards":
        for encounter in ("dragon_valley_loc", "draco_battle"):
            for character in CHARACTERS:
                for mode in ("main", "explore"):
                    for condition in ("before", "after"):
                        jobs.append(dict(suite=suite, character=character, encounter=encounter,
                                         mode=mode, condition=condition))
    elif suite == "controls":
        for encounter in ("forest_wolves", "goblin_fort_fourth"):
            for character in CHARACTERS:
                for condition in ("old_robin", "damage_only", "highest_hp"):
                    jobs.append(dict(suite=suite, character=character, encounter=encounter, condition=condition))
        for condition in ("initial_armor", "bought_armor"):
            jobs.append(dict(suite=suite, character="hero", encounter="forest_wolves", condition=condition))
    return [{**job, "n": n, "seed": seed} for job in jobs]


_PACK: dict[str, Any] = {}
_CHECKPOINTS: dict[str, Any] = {}


def initialize() -> None:
    global _PACK, _CHECKPOINTS
    _PACK = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    _CHECKPOINTS = checkpoints.generate()


def run_job(job: dict[str, Any]) -> dict[str, Any]:
    pack = deepcopy(_PACK)
    cp = deepcopy(_CHECKPOINTS)
    character, suite = job["character"], job["suite"]
    if suite == "routes":
        row = route.simulate_route(pack, cp, character, n=job["n"], seed=job["seed"],
            rest_policy=job["rest_policy"], quests=tuple(job["quests"]), decisions=job["decisions"], dice=job["dice"])
        row.pop("sample_trial", None)
        return {**row, **job}
    encounter = job["encounter"]
    options: dict[str, Any] = dict(n=job["n"], seed=job["seed"], checkpoints=cp, purify=False)
    if suite == "finals":
        options.update(preparation="purification" if job["case"] == "all_purify" else "standard",
                       initial_delta=support.cases()[job["case"]])
    elif suite == "rewards":
        history = read_report("balance-2026-10-13-regional-plus3.json")
        key = f"{encounter}/{character}/{job['mode']}/{job['condition']}"
        cell = deepcopy(history["snapshots"][key])
        # The frozen 031 snapshots lack companion/skill fields; retain those from
        # the reachable checkpoint. Add slot metadata through the current catalog.
        cp["encounters"][encounter]["characters"][character].update(cell)
        state._merge_inventory_catalog(cp["encounters"][encounter]["characters"][character]["inventory"], pack)
        if encounter == "draco_battle":
            options.update(preparation="standard",
                           initial_delta=ch5.cases()["none" if job["mode"] == "main" else "all_kill"])
    elif suite == "controls":
        cell = cp["encounters"][encounter]["characters"][character]
        condition = job["condition"]
        if condition in {"initial_armor", "bought_armor"}:
            session = checkpoints.fresh_session(pack, character)
            session["character"].update({key: deepcopy(cell[key]) for key in ("inventory", "equipment", "gold")})
            if condition == "bought_armor":
                state.commit_world_position(session, location_id="forge")
                session["character"]["gold"] = 100
                shops.trade(session, "forge_shop", "adamantite_armor", 1)
                shops.use_item(session, "adamantite_armor")
            for key in ("inventory", "equipment", "gold"):
                cell[key] = deepcopy(session["character"][key])
        else:
            robin = deepcopy(next(c for c in pack["companions"] if c["id"] == "robin"))
            effect = dict(kind="damage_enemy", name="援護射撃", element="physical",
                          damage="2d4" if condition == "old_robin" else "2d4+1")
            effect.update(target="highest_hp") if condition == "highest_hp" else effect.update(random_target=True)
            robin["round_start_effects"] = [effect]
            cell["companion"] = robin
    row = sim.simulate(pack, encounter, character, **options)
    row.update(job)
    cell = cp["encounters"][encounter]["characters"][character]
    prepared = sim.prepare_session(pack, encounter, character, cp)
    row["equipment"] = prepared["character"]["equipment"]
    row["inventory"] = cell["inventory"]
    return row


def price_control() -> list[dict[str, Any]]:
    rows = []
    for price in (20, 60):
        pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        forge = next(s for s in pack["shops"] if s["id"] == "forge_shop")
        next(i for i in forge["items"] if i["item_id"] == "adamantite_armor")["price"] = price
        for order in (("adamantite_armor", "ice_charm"), ("ice_charm", "adamantite_armor")):
            session = checkpoints.fresh_session(pack, "hero")
            state.commit_world_position(session, location_id="forge")
            session["character"]["gold"] = 100
            bought = []
            for identifier in order:
                try:
                    shops.trade(session, "forge_shop", identifier, 1)
                    bought.append(identifier)
                except shops.ShopError:
                    break
            rows.append(dict(price=price, order=list(order), bought=bought, gold=session["character"]["gold"]))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("routes", "finals", "rewards", "controls"), required=True)
    parser.add_argument("--n", type=int)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--legacy", action="store_true", help="Skip the unsupported highest_hp controls in the old engine")
    args = parser.parse_args()
    n = args.n or (500 if args.suite == "routes" else 2000)
    jobs = jobs_for(args.suite, n, args.seed)
    if args.legacy and args.suite == "controls":
        jobs = [job for job in jobs if job["condition"] in {"old_robin", "initial_armor", "bought_armor"}]
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize) as pool:
        for row in pool.map(run_job, jobs):
            rows.append(row)
            print(" ".join(str(row.get(k, "")) for k in ("suite", "character", "policy_label", "encounter", "case", "mode", "condition")),
                  row.get("win_rate", row.get("completion_rate")), flush=True)
    paths = [checkpoints.DEFAULT_SCENARIO, ROOT / "host/state.py", ROOT / "host/combat.py",
             ROOT / "host/item_mechanics.py", Path(__file__), Path(sim.__file__), Path(class_aware.__file__)]
    result = dict(suite=args.suite, n=n, seed=args.seed, rows=rows,
                  fingerprints={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    if args.suite == "controls":
        result["prices"] = price_control()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
