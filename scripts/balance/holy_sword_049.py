"""049 paired probes using simulator v3 decisions and engine-only settlement."""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import sys
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any
from unittest.mock import patch

from host import combat, progression, state
from host.difficulty import apply_difficulty
from . import checkpoints, probes_v3, sim, snapshots_v3

ROOT = Path(__file__).resolve().parents[2]


def gate_session(pack: dict[str, Any], choices: dict[str, str]) -> dict[str, Any]:
    session = checkpoints.fresh_session(pack, "hero", "normal", effective=True)
    session = snapshots_v3.at_level(session, 6, choices)
    session["character"]["inventory"] = [item for item in session["character"]["inventory"]
                                         if item["name"] in {"鉄の剣", "革の鎧"}]
    session["character"]["equipment"] = ["鉄の剣", "革の鎧"]
    session["flags"] = {"defeated_ignis": True}
    session["world_state"] = {"scene_id": "castle_return", "location_id": "draco_battle"}
    session["companion"] = None
    return session


def battles(template: dict[str, Any], n: int, seed: int, key: str, policy: str) -> list[dict[str, Any]]:
    results = []
    for index in range(n):
        session = deepcopy(template, {id(template["scenario_pack"]): template["scenario_pack"]})
        rng = random.Random(sim.trial_seed(seed, key, "hero", index))
        awakening = None
        human_damage = 0

        def log(current, actor, kind, text, data=None, **kwargs):
            nonlocal awakening, human_damage
            battle = current["combat"]
            if kind == "awakening":
                awakening = {"round": battle["round"], "phase": data["enemy_ids"][0]}
            if kind == "damage" and kwargs.get("target") is current["character"]:
                if any(e["template_id"] == "draco_human" for e in battle["enemies"]):
                    human_damage += data["damage"]

        with patch.object(combat, "random", rng), patch.object(state, "random", rng), patch.object(combat, "_log", log):
            session["combat_start_requested"] = True
            session["_balance_free_actions"] = {}
            if not combat.ensure_combat_started(session):
                raise ValueError("Draco encounter did not start")
            while combat.combat_is_active(session):
                action, target = sim.choose_action(session, policy, purify=False)
                sim.perform_action(session, action, target, rng)
        battle = session["combat"]
        dragon = next((enemy for enemy in battle["enemies"] if enemy["template_id"] == "draco_dragon"), None)
        results.append({"won": int(battle["status"] == "victory"), "rounds": battle["round"],
                        "awakening": awakening, "rounds_after_awakening": battle["round"]-awakening["round"] if awakening else None,
                        "dragon_remaining_hp": max(0, dragon["hp"]) if dragon else None,
                        "human_damage": human_damage, "human_defeat": int(battle["status"] == "defeat" and dragon is None)})
    return results


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n, wins = len(rows), sum(row["won"] for row in rows)
    rate, z = wins/n, 1.959963984540054
    middle = (rate+z*z/(2*n))/(1+z*z/n)
    radius = z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/(1+z*z/n)
    def histogram(values):
        return dict(sorted(Counter(map(str, values)).items()))
    awakened = [row for row in rows if row["awakening"]]
    return {"n": n, "wins": wins, "win_rate": rate, "wilson95": [middle-radius, middle+radius],
            "rounds_mean": mean(row["rounds"] for row in rows),
            "awakening_phase_round": histogram(f"{r['awakening']['phase']}:{r['awakening']['round']}" for r in awakened),
            "no_awakening_win_rate": sum(r["won"] for r in rows if not r["awakening"])/n,
            "no_awakening_loss_rate": sum(1-r["won"] for r in rows if not r["awakening"])/n,
            "rounds_after_awakening": histogram(r["rounds_after_awakening"] for r in awakened),
            "rounds_after_awakening_mean": mean(r["rounds_after_awakening"] for r in awakened) if awakened else None,
            "dragon_remaining_hp": histogram(r["dragon_remaining_hp"] for r in rows),
            "human_damage_mean": mean(r["human_damage"] for r in rows),
            "human_defeat_rate": mean(r["human_defeat"] for r in rows)}


def run_job(job: dict[str, Any]) -> dict[str, Any]:
    pack = apply_difficulty(state.load_scenario_pack(Path(job["scenario"])), "normal")
    sword = next(item for item in pack["items"] if item["id"] == "hero_holy_sword")
    sword["combat"].update(job.get("sword", {}))
    template = (snapshots_v3.restore(pack, job["snapshot"]) if "snapshot" in job
                else gate_session(pack, job["choices"]))
    rows = battles(template, job["n"], job["seed"], job["key"], job["policy"])
    return {"label": job["label"], "choices": job.get("choices"), "summary": summarize(rows), "rows": rows}


def run_jobs(jobs: list[dict[str, Any]], workers: int) -> list[dict[str, Any]]:
    if workers == 1:
        return [run_job(job) for job in jobs]
    # File IPC also works in Windows sandboxes that prohibit multiprocessing pipes.
    directory = ROOT / ".tmp-test/049/workers" / uuid.uuid4().hex
    directory.mkdir(parents=True)
    def launch(index_job):
        index, job = index_job
        source, output = directory / f"{index}.json", directory / f"{index}.out.json"
        source.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        with (directory / f"{index}.log").open("w", encoding="utf-8") as log:
            subprocess.run([sys.executable, "-m", "scripts.balance.holy_sword_049", "--worker-job", str(source),
                            "--output", str(output)], cwd=ROOT, stdout=log, stderr=log, check=True)
        return json.loads(output.read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(launch, enumerate(jobs)))


def report_jobs(pack: dict[str, Any], checkpoint_path: Path, scenario: Path, n: int, seed: int) -> tuple[list, list]:
    checkpoints_data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    jobs, missing = [], []
    supports = ("king_trust", "recruited_robin", "cleared_goblin_fort", "mina_quest_done", "robert_hammer_returned")
    for profile in ("P2", "P0b"):
        entry = checkpoints_data["profiles"][profile]["encounters"].get("draco_battle", {}).get("characters", {}).get("hero")
        if entry is None:
            missing.append({"profile": profile, "reason": "053 did not observe a hero Draco opening"})
            continue
        def template(weapon):
            current = snapshots_v3.restore(pack, entry["snapshot"])
            actor = current["character"]
            actor["inventory"] = [i for i in actor["inventory"] if i.get("id") != "hero_holy_sword"]
            current["flags"].pop("holy_sword_awakened", None)
            current["flags"].pop("accepted_sword_fusion", None)
            state.apply_state_delta(current, {"inventory_add": [{"name": weapon}], "equip_item": weapon})
            return current
        def add(label, current, policy, key):
            jobs.append({"label": label, "scenario": str(scenario.resolve()), "n": n, "seed": seed,
                         "key": key, "policy": policy, "snapshot": snapshots_v3.capture(current)})
        for support in ("none", "all"):
            for policy in ("heuristic_v3", "attack_only"):
                for branch in ("ordinary", "A"):
                    current = template("鉄の剣")
                    current["companion"] = None
                    current["flags"].pop("ignis_ally", None)
                    for flag in supports:
                        current["flags"].pop(flag, None)
                    current["character"]["inventory"] = [i for i in current["character"]["inventory"] if i["name"] != "霜封じの護符"]
                    if support == "all":
                        current["flags"].update(dict.fromkeys(supports, True))
                        state.apply_state_delta(current, {"inventory_add": [{"name": "霜封じの護符"}]})
                    current["flags"].pop("defeated_ignis", None)
                    if branch == "A":
                        current["flags"]["defeated_ignis"] = True
                    add(f"R1:{profile}:{support}:{policy}:{branch}", current, policy, f"049:R1:{profile}")
        for branch in ("ordinary", "B"):
            current = template("氷鉄の大剣")
            current["character"]["inventory"] = [i for i in current["character"]["inventory"] if i["name"] != "鉄の剣"]
            if branch == "B":
                current["flags"]["accepted_sword_fusion"] = True
            add(f"R2:{profile}:{branch}", current, "heuristic_v3", f"049:R2:{profile}")
    return jobs, missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261021)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--damage")
    parser.add_argument("--accuracy", type=int)
    parser.add_argument("--scenario", type=Path, default=checkpoints.DEFAULT_SCENARIO)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=Path)
    parser.add_argument("--worker-job", type=Path)
    parser.add_argument("--report-checkpoints", type=Path)
    args = parser.parse_args()
    if args.worker_job:
        result = run_job(json.loads(args.worker_job.read_text(encoding="utf-8")))
        args.output.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return
    if min(args.n, args.workers) < 1:
        parser.error("n and workers must be positive")
    pack = apply_difficulty(state.load_scenario_pack(args.scenario), "normal")
    choices = [c for c in probes_v3.combinations(pack, "hero") if len(c) >= 3]
    choices = list({tuple((k, v) for k, v in c.items() if int(k) <= 6): None for c in choices})
    choices = [dict(c) for c in choices]
    override = {k: v for k, v in {"damage": args.damage, "accuracy": args.accuracy}.items() if v is not None}
    jobs = json.loads(args.jobs.read_text(encoding="utf-8")) if args.jobs else [
        {"label": f"G{i+1}", "scenario": str(args.scenario.resolve()), "n": args.n, "seed": args.seed,
         "key": "049:G", "policy": "attack_only", "choices": c, "sword": override} for i, c in enumerate(choices)]
    missing = []
    if args.report_checkpoints:
        jobs, missing = report_jobs(pack, args.report_checkpoints, args.scenario, args.n, args.seed)
    results = run_jobs(jobs, args.workers)
    actor = gate_session(pack, choices[0])["character"]
    result = {"seed": args.seed, "n": args.n, "sword": {**next(i for i in pack["items"] if i["id"] == "hero_holy_sword")["combat"], **override},
              "level6": {k: actor[k] for k in ("hp", "mp", "sp", "attributes", "level", "exp")}, "results": results}
    if args.report_checkpoints:
        result["missing_checkpoints"] = missing
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    print(json.dumps([{k: row[k] for k in ("label", "summary")} for row in results], ensure_ascii=False))


if __name__ == "__main__":
    main()
