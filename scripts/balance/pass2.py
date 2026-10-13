from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import subprocess
import time
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any

from host import state
from . import sim
from .budget import incoming_damage_budget
from .checkpoints import DEFAULT_CHECKPOINTS, DEFAULT_SCENARIO, ROOT
from .pass1 import apply_parameters, enemy_groups, evaluate, objective


def configured(pack: dict[str, Any], checkpoints: dict[str, Any], parameters: dict[str, Any],
               ratio: float) -> tuple[dict[str, Any], dict[str, Any]]:
    pack = apply_parameters(pack, parameters)
    checkpoints = deepcopy(checkpoints)
    companion = next(c for c in pack["companions"] if c["id"] == "blue_robed_mage")
    companion["round_start_effects"][0]["max_hp_ratio"] = ratio
    for entry in checkpoints["encounters"].values():
        for actor in entry["characters"].values():
            if actor["companion"] and actor["companion"]["id"] == companion["id"]:
                actor["companion"] = deepcopy(companion)
    return pack, checkpoints


def score(rows: list[dict[str, Any]], targets: dict[str, Any], budgets: list[dict[str, Any]]) -> float:
    return objective(rows, targets) + 10 * sum(max(0, b["ratio"] - (b["limit"] or 1)) for b in budgets)


def search_rows(pack: dict[str, Any], cp: dict[str, Any], encounters: list[str], n: int,
                targets: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for e in encounters for r in evaluate(pack, cp, [e], n, attack_only=targets["encounters"][e] == "boss")]


def search_group(args: tuple) -> dict[str, Any]:
    pack, cp, targets, enemies, encounters, iterations = args
    rng = random.Random(5 + sum(map(ord, enemies[0])))
    parameters: dict[str, Any] = {}
    ratio = .20
    catalog = {e["id"]: e for e in pack["enemies"]}
    local_targets = {**targets, "encounters": {e: targets["encounters"][e] for e in encounters}}
    proposals = []
    best_params: dict[str, Any] = {}
    best_score = float("inf")
    for index in range(iterations + 1):
        proposal = deepcopy(best_params)
        if index:
            for eid in enemies:
                source = catalog[eid]
                previous = best_params.get(eid, {})
                if index < iterations // 2:
                    hp = rng.choice([40, 48, 56, 64, 72, 80, 88, 100, 112, 128, 144])
                    defense = rng.choice([0, 0, 1, 2, 3])
                    damage = rng.choice(["1d4", "1d6", "1d6+1", "1d8", "1d8+2", "1d10"])
                    accuracy = rng.choice([65, 80, 90, 100])
                    evade = rng.choice([0, 5, 10, 15])
                else:
                    hp = max(4, abs(previous.get("hp", source["hp"])) + rng.choice([-8, -4, 0, 4, 8]))
                    defense = max(0, previous.get("defense", source["combat"].get("defense", 0)) + rng.choice([-1, 0, 0, 1]))
                    damage = rng.choice([previous.get("damage", source["combat"]["basic_attack"]["damage"])] * 4 + ["1d4", "1d6", "1d6+1", "1d8", "1d8+2"])
                    accuracy = max(40, min(100, previous.get("accuracy", 85) + rng.choice([-5, 0, 5])))
                    evade = max(0, min(25, previous.get("evade", source["combat"].get("evade", 0)) + rng.choice([-2, 0, 2])))
                proposal[eid] = dict(hp=-hp if source["hp"] < 0 else hp, defense=defense,
                                     damage=damage, accuracy=accuracy, evade=evade)
        tested, checkpoint = configured(pack, cp, {**parameters, **proposal}, ratio)
        rows = search_rows(tested, checkpoint, encounters, 16, targets)
        budgets = incoming_damage_budget(tested, checkpoint, local_targets)
        value = score(rows, targets, budgets)
        proposals.append(dict(parameters=proposal, score=value))
        if value < best_score:
            best_score, best_params = value, proposal
    finalists = sorted(proposals, key=lambda p: p["score"])[:6]
    for finalist in finalists:
        tested, checkpoint = configured(pack, cp, {**parameters, **finalist["parameters"]}, ratio)
        rows = search_rows(tested, checkpoint, encounters, 64, targets)
        finalist["refined_score"] = score(rows, targets, incoming_damage_budget(tested, checkpoint, local_targets))
        finalist["win_rates"] = [r["win_rate"] for r in rows if r["policy"] == "heuristic"]
    best = min(finalists, key=lambda p: p["refined_score"])
    return dict(enemies=enemies, encounters=encounters, proposals=proposals, selected=best)


def search(pack: dict[str, Any], cp: dict[str, Any], targets: dict[str, Any], output: Path,
           iterations: int, shard: int = 0, shards: int = 1) -> None:
    groups = enemy_groups(pack, cp, targets)
    parameters: dict[str, Any] = {}
    records = []
    tasks = [(pack, cp, targets, enemies, encounters, iterations)
             for index, (enemies, encounters) in enumerate(groups) if index % shards == shard]
    for task in tasks:
        record = search_group(task)
        parameters.update(record["selected"]["parameters"])
        records.append(record)
        print(json.dumps(dict(enemies=record["enemies"], selected=record["selected"])), flush=True)
        output.write_text(json.dumps(dict(coarse_n=16, refinement_n=64, ratio=.20,
                                         parameters=parameters, groups=records), indent=2) + "\n", encoding="utf-8")


def confirm(pack: dict[str, Any], cp: dict[str, Any], targets: dict[str, Any], output: Path, n: int) -> None:
    start = time.perf_counter()
    paths = [DEFAULT_SCENARIO, DEFAULT_CHECKPOINTS, sim.TARGETS,
             *[ROOT / p for p in ("host/state.py", "host/combat.py", "host/scenario_context.py",
                                  "host/item_mechanics.py", "scripts/balance/sim.py", "scripts/balance/pass1.py",
                                  "scripts/balance/pass2.py", "scripts/balance/budget.py", "scripts/balance/checkpoints.py")]]
    result = dict(n=n, seed=20261011, rows=[], budget=incoming_damage_budget(pack, cp, targets),
                  baseline_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  fingerprints={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    # Run the actual --check entry point once and retain its matrix and exit status.
    print(f"sim --check --n {n}", flush=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    captured = io.StringIO()
    with redirect_stdout(captured):
        result["check_exit_code"] = sim.main(["--check", "--n", str(n)])
    checked_result = json.loads(captured.getvalue())
    result["rows"] = checked_result["rows"]
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"check_exit_code={result['check_exit_code']} violations={len(checked_result['violations'])}", flush=True)
    for encounter in targets["encounters"]:
        result["rows"] += evaluate(pack, cp, [encounter], n, companion=False, attack_only=False)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"companion=False {encounter}", flush=True)
    # Ablation uses the final numbers and checkpoint resources, removing only the eight new skills.
    without_skills = deepcopy(pack)
    for actor in without_skills["characters"]:
        actor.pop("level_skills", None)
    result["without_new_skills"] = search_rows(without_skills, cp, list(targets["encounters"]), n, targets)
    result["elapsed_seconds"] = time.perf_counter() - start
    result["violations_after"] = sim.check_results([r for r in result["rows"] if r["companion"]], targets)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def refine_boss(pack: dict[str, Any], cp: dict[str, Any], targets: dict[str, Any], output: Path) -> None:
    rng = random.Random(505)
    records = json.loads(output.read_text(encoding="utf-8"))["proposals"] if output.exists() else []
    local = {**targets, "encounters": {"dragon_valley_loc": "boss"}}

    def run(proposal: dict[str, Any], n: int) -> dict[str, Any]:
        tested, checkpoint = configured(pack, cp, {"ignis": proposal["ignis"]}, .20)
        for actor in tested["characters"]:
            for skill in actor.get("level_skills", []):
                skill.update(proposal.get("skills", {}).get(skill["id"], {}))
        rows = evaluate(tested, checkpoint, ["dragon_valley_loc"], n)
        budgets = incoming_damage_budget(tested, checkpoint, local)
        value = score(rows, targets, budgets)
        for row in rows:
            if row["policy"] == "heuristic":
                value += 40 * max(.60 - row["win_rate"], row["win_rate"] - .75, 0)
        return dict(parameters=proposal, score=value, rows=rows)

    for _ in range(0 if records else 120):
        proposal = dict(ignis=dict(hp=rng.choice([88, 100, 112, 124, 136, 148]),
                                   damage=rng.choice(["1d12", "1d20", "2d8", "2d10", "2d12"]),
                                   accuracy=rng.choice([55, 65, 75, 85]), defense=rng.choice([0, 1, 2]),
                                   evade=rng.choice([3, 8, 13])),
                        skills={"thief_lv5_a": dict(damage=rng.choice(["2d6+dex/2", "3d8+dex/2", "4d8+dex/2", "3d10+dex/2"]), cost=rng.choice([3, 4, 5])),
                                "cleric_lv5_b": dict(cost=rng.choice([4, 6, 8, 10])),
                                "mage_lv5_a": dict(damage=rng.choice(["2d6+int/2", "2d8+int/2", "3d6+int/2"]), cost=5)})
        records.append(run(proposal, 16))
    finalists = [run(r["parameters"], 64) for r in sorted(records, key=lambda r: r["score"])[:8]]
    best = deepcopy(min(finalists, key=lambda r: r["score"]))
    focused = []
    # Skills used only at Lv5 can be refined independently for this checkpoint.
    for cid, sid, options in (
        ("cleric", "cleric_lv5_b", [dict(cost=c) for c in (8, 10, 12, 14, 18)]),
        ("thief", "thief_lv5_a", [dict(damage=f"{dice}d8+dex/2", cost=5) for dice in (5, 6, 7, 8, 9, 10)]),
    ):
        tests = []
        for option in options:
            proposal = deepcopy(best["parameters"])
            proposal["skills"][sid] = option
            tested, checkpoint = configured(pack, cp, {"ignis": proposal["ignis"]}, .20)
            for actor in tested["characters"]:
                for skill in actor.get("level_skills", []):
                    skill.update(proposal["skills"].get(skill["id"], {}))
            row = sim.simulate(tested, "dragon_valley_loc", cid, checkpoints=checkpoint, n=64)
            value = 100 * max(.60 - row["win_rate"], row["win_rate"] - .75, 0) + abs(row["win_rate"] - .675)
            tests.append(dict(option=option, score=value, row=row))
        selected = min(tests, key=lambda r: r["score"])
        best["parameters"]["skills"][sid] = selected["option"]
        focused.append(dict(character=cid, tests=tests, selected=selected))
    best = run(best["parameters"], 64)
    output.write_text(json.dumps(dict(coarse_n=16, refinement_n=64, proposals=records,
                                     finalists=finalists, focused=focused, selected=best), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(parameters=best["parameters"], score=best["score"],
                          win_rates=[r["win_rate"] for r in best["rows"] if r["policy"] == "heuristic"])), flush=True)


def select_parameters(pack: dict[str, Any], cp: dict[str, Any], targets: dict[str, Any], output: Path) -> None:
    sources = [json.loads((ROOT / f"eval/balance/pass2-search-{i}.json").read_text(encoding="utf-8")) for i in range(4)]
    boss = json.loads((ROOT / "eval/balance/pass2-boss-search.json").read_text(encoding="utf-8"))
    parameters = {k: v for source in sources for k, v in source["parameters"].items()}
    parameters["ignis"] = boss["selected"]["parameters"]["ignis"]
    skill_changes = boss["selected"]["parameters"]["skills"]
    for actor in pack["characters"]:
        for skill in actor.get("level_skills", []):
            skill.update(skill_changes.get(skill["id"], {}))
    candidates = []
    for ratio in (.15, .20, .25):
        tested, checkpoint = configured(pack, cp, parameters, ratio)
        rows = evaluate(tested, checkpoint, list(targets["encounters"]), 64)
        no_companion = evaluate(tested, checkpoint, list(targets["encounters"]), 64, companion=False, attack_only=False)
        without = {(r["encounter"], r["character"]): r["win_rate"] for r in no_companion}
        uplift = mean(r["win_rate"] - without[r["encounter"], r["character"]] for r in rows
                      if r["policy"] == "heuristic" and r["encounter_class"] != "guest"
                      and checkpoint["encounters"][r["encounter"]]["characters"][r["character"]]["companion"])
        value = score(rows, targets, incoming_damage_budget(tested, checkpoint, targets))
        value += 1000 * max(.10 - uplift, uplift - .20, 0)
        record = dict(ratio=ratio, score=value, uplift=uplift, violations=len(sim.check_results(rows, targets)), rows=rows, without_companion=no_companion)
        candidates.append(record)
        print(json.dumps({k: v for k, v in record.items() if k not in {"rows", "without_companion"}}), flush=True)
    best = min(candidates, key=lambda r: r["score"])
    result = dict(coarse_n=16, refinement_n=64, parameters=parameters, skill_changes=skill_changes,
                  groups=[g for source in sources for g in source["groups"]], boss_search=boss,
                  ratio_candidates=candidates, selected_ratio=best["ratio"])
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = DEFAULT_SCENARIO.with_name(filename)
        raw = json.loads(path.read_text(encoding="utf-8"))
        changed, _ = configured(raw, cp, parameters, best["ratio"])
        for actor in changed["characters"]:
            for skill in actor.get("level_skills", []):
                skill.update(skill_changes.get(skill["id"], {}))
                if skill.get("kind") == "attack":
                    skill["effect"] = ("敵全体に" if skill.get("all_targets") else "敵に") + skill["damage"] + "ダメージを与える。"
        path.write_text(json.dumps(changed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline second balance pass")
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--refine-boss", action="store_true")
    parser.add_argument("--select", action="store_true")
    parser.add_argument("--iterations", type=int, default=120)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pack = state.load_scenario_pack(DEFAULT_SCENARIO)
    cp = json.loads(DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    if args.select:
        select_parameters(pack, cp, targets, args.output)
    elif args.refine_boss:
        refine_boss(pack, cp, targets, args.output)
    elif args.search:
        search(pack, cp, targets, args.output, args.iterations, args.shard, args.shards)
    else:
        confirm(pack, cp, targets, args.output, args.n)


if __name__ == "__main__":
    main()
