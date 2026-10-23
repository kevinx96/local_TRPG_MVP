"""053 offline measurement pipeline. No balance tuning and no model calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any
from unittest.mock import patch

from host import combat, state
from host.difficulty import apply_difficulty, overlay_fingerprint
from scripts.playtest import save_telemetry
from . import budget, checkpoints, metrics_v3, probes_v2, probes_v3, reproduction_v2, route_v2, snapshots_v3
from .archetypes import ARCHETYPES, CHARACTERS, COMPLETION_TITLE
from .legacy_spring import select_spring

OUTPUT_ROOT = checkpoints.ROOT / ".tmp-test/053"
FROZEN = (checkpoints.DEFAULT_CHECKPOINTS, route_v2.BERSERKER,
          checkpoints.ROOT / "eval/balance/046-legacy-output.json")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def frozen_write(path: Path, text: str) -> None:
    payload = text.encode("utf-8")
    if not path.exists() or (path.read_bytes() != payload and json.loads(path.read_text(encoding="utf-8")) != json.loads(text)):
        raise ValueError(f"Frozen historical artifact differs: {path}")


def arrival_rows(records, targets):
    result = []
    for archetype in ARCHETYPES:
        target_id = "P0" if archetype.startswith("P0") else "P2" if archetype == "P2s" else archetype
        target = targets["ignis_level"].get(target_id)
        static = {"P0": 4, "P1": 4, "P2": 7, "P3": 8}.get(target_id)
        for character in CHARACTERS:
            group = [t for t in records if t["archetype"] == archetype and t["character"] == character]
            arrivals = [t["exp_nodes"]["dragon_valley_loc"] for t in group if "dragon_valley_loc" in t.get("exp_nodes", {})]
            levels = [r["level"] for r in arrivals]
            arrived_trials = [t for t in group if "dragon_valley_loc" in t.get("exp_nodes", {})]
            spring_exp = [sum(b.get("exp_award", {}).get("amount", 0) for b in t["battles"]
                              if b["encounter"] in {"slime_ambush_one", "slime_ambush_two", "slime_king_battle"}) for t in arrived_trials]
            quests = Counter(q for r in arrivals for q in r.get("quest_ids", []))
            static_exp = {"P0": 100, "P1": 120, "P2": 310, "P3": 640}.get(target_id)
            result.append({"archetype": archetype, "character": character, "n": len(group), "arrivals": len(arrivals),
                           "arrival_rate": len(arrivals)/len(group) if group else 0,
                           "mean": mean(levels) if levels else None, "median": median(levels) if levels else None,
                           "min": min(levels) if levels else None, "max": max(levels) if levels else None,
                           "histogram": dict(sorted(Counter(levels).items())), "static_050": static, "target": target,
                           "target_gap": mean(levels)-target if levels and target else None,
                           "exp_mean": mean(r["exp"] for r in arrivals) if arrivals else None,
                           "static_050_exp": static_exp,
                           "exp_difference_from_static": mean(r["exp"] for r in arrivals)-static_exp if arrivals and static_exp else None,
                           "spring_chain_exp_mean": mean(spring_exp) if spring_exp else None,
                           "completed_quest_counts_at_arrival": dict(sorted(quests.items())),
                           "exp_sources_mean": {source: mean(r["sources"].get(source, 0) for r in arrivals) for source in ("trash", "elite", "boss", "unclassified", "quest")} if arrivals else {},
                           "explanation": "Observed survivors only; spring chain adds EXP, checks/bypasses omit defeated foes, quests pay only on actual completion; static 050 assumes all listed victories and quest successes. No Ignis EXP included." if levels else "No trial reached Ignis; no level estimate substituted."})
    return result


def deltas(rows, other_rows):
    old = {(r["archetype"], r["character"]): r for r in other_rows}
    result = []
    for row in rows:
        before = old.get((row["archetype"], row["character"]))
        if before:
            result.append({"archetype": row["archetype"], "character": row["character"],
                           **{key+"_delta_pp": (row[key]-before[key])*100 for key in ("completion_rate", "ignis_rate", "terminal_rate")}})
    return result


def stats(records):
    statuses = defaultdict(Counter)
    skills = defaultdict(Counter)
    scrolls = []
    for trial in records:
        for battle in trial["battles"]:
            for row in battle.get("statuses", []):
                statuses[trial["archetype"], trial["character"], row["side"], row["id"]].update({key: row[key] for key in ("applications", "damage", "cleared")})
            for identifier, row in battle.get("skill_usage", {}).items():
                skills[trial["archetype"], trial["character"], identifier].update({k: row[k] for k in ("uses", "hits", "damage", "disabled_cooldown_rounds", "disabled_uses_rounds")})
                skills[trial["archetype"], trial["character"], identifier].update({"cost_"+k: v for k, v in row["costs"].items()})
        for scroll in trial.get("scrolls", []):
            scrolls.append({"archetype": trial["archetype"], "character": trial["character"], "seed": trial["seed"], **scroll,
                            "cleared_by_curse": scroll["skill"] in trial.get("cleared_spells", [])})
    return {"statuses": [dict(archetype=a, character=c, side=side, id=i, **counts) for (a, c, side, i), counts in sorted(statuses.items())],
            "skills": [dict(archetype=a, character=c, id=i, **counts) for (a, c, i), counts in sorted(skills.items())], "scrolls": scrolls}


def markdown(result):
    title = "052 normal 测量" if result.get("measurement_scope") == "052" else "053 模拟器 v3"
    lines = [f"# {title}：{result['difficulty']} / {result['spring']}（调参前）", "",
             "主通关口径：冒険完了；终局含引擎失败结局。所有统计来自离线确定性引擎。", "",
             f"N={result['n']}，probe-n={result['probe_n']}，passive-n={result['passive_n']}，seed={result['seed']}。", "",
             "| 原型 | 职业 | 通关 | Ignis | 终局 | Ignis回合中位 | baby通关 | baby Ignis |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    baby = {(r["archetype"], r["character"]): r for r in result.get("baby_rows", [])}
    for row in result["rows"]:
        compare = baby.get((row["archetype"], row["character"]), {})
        lines.append(f"| {row['archetype']} | {row['character']} | {row['completion_rate']:.2%} | {row['ignis_rate']:.2%} | {row['terminal_rate']:.2%} | {row['ignis_rounds_median']} | {compare.get('completion_rate')} | {compare.get('ignis_rate')} |")
    lines += ["", "| 原型 | 职业 | 到达数/总数 | 等级均值/中位/最小/最大 | 分布 | 050估算 | 目标 | 差 | EXP来源均值 |", "|---|---|---|---|---|---|---|---|---|"]
    for row in result["ignis_levels"]:
        lines.append(f"| {row['archetype']} | {row['character']} | {row['arrivals']}/{row['n']} | {row['mean']}/{row['median']}/{row['min']}/{row['max']} | {row['histogram']} | {row['static_050']} | {row['target']} | {row['target_gap']} | {row['exp_sources_mean']} |")
    lines += ["", "等级差异逐项说明（实际胜利/绕行、史莱姆链、任务完成台账）：", ""]
    for row in result["ignis_levels"]:
        lines.append(f"- {row['archetype']}/{row['character']}: EXP={row['exp_mean']}，050={row['static_050_exp']}，差={row['exp_difference_from_static']}，泉连战={row['spring_chain_exp_mean']}，完成任务计数={row['completed_quest_counts_at_arrival']}。{row['explanation']}")
    lines += ["", "| 原型 | 职业 | 指标 | 值 | 目标 | 状态 | 原因 |", "|---|---|---|---|---|---|---|"]
    for row in result["cell_metrics"]:
        encoded = json.dumps(row["value"], ensure_ascii=False, separators=(",", ":")).replace("|", "／")
        lines.append(f"| {row['archetype']} | {row['character']} | {row['id']} | {encoded} | {row['target']} | {row['status']} | {row['reason'] or ''} |")
    for title, key in (("被动默认表及逐格依据", "passive_defaults"), ("被动16组合结果", "passive_enumeration"), ("P3互斥分支试跑", "branch_proposals"),
                       ("技能、状态与卷轴购买/使用", "usage"), ("baby历史复现", "checkpoint_probes"), ("与046b每格差异", "legacy_comparison"),
                       ("策略参数", "strategy_parameters"), ("无法表达与缺失样本", "limitations"), ("各阶段墙钟秒", "timings")):
        lines += ["", title, "", "```json", json.dumps(result.get(key), ensure_ascii=False, indent=2), "```"]
    lines += ["", "M3b（含零消耗主动治疗、福音实际使用率）详见 JSON.m3b；P0g 每级资源差详见 JSON.grinding。", "",
              "历史比较超差不能自动归因；验收结论和证据见 053-report.txt。未达到门槛的数字作为052调参输入保留。", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="053 offline measurement, no game tuning")
    parser.add_argument("--difficulty", choices=("baby", "normal"), default="baby")
    parser.add_argument("--spring", choices=("legacy", "current"), default="current")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--probe-n", type=int, default=500)
    parser.add_argument("--passive-n", type=int)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--scenario", type=Path, default=checkpoints.DEFAULT_SCENARIO)
    parser.add_argument("--save", type=Path, default=save_telemetry.DEFAULT_SAVE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--records-output", type=Path)
    parser.add_argument("--checkpoint-output", type=Path)
    parser.add_argument("--passive-output", type=Path)
    parser.add_argument("--passive-table", type=Path, help="Read-only frozen normal passive defaults")
    parser.add_argument("--skip-passive-enumeration", action="store_true")
    parser.add_argument("--skip-passive-probes", action="store_true")
    parser.add_argument("--tuning-052", action="store_true", help="Normal-only corrected M9 and escort branch measurement")
    parser.add_argument("--baby-reference", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.skip_passive_enumeration != bool(args.passive_table):
        parser.error("--passive-table and --skip-passive-enumeration must be used together")
    if args.difficulty != "normal" and (args.passive_table or args.tuning_052 or args.skip_passive_probes):
        parser.error("052 options apply only to normal")
    if args.tuning_052 and not args.passive_table:
        parser.error("052a/b require a frozen --passive-table")
    normal_output = args.output.parent if args.output else checkpoints.ROOT / ".tmp-test/052a"
    args.checkpoint_output = args.checkpoint_output or normal_output / "checkpoints-normal.json"
    args.passive_output = args.passive_output or normal_output / "passive-defaults.json"
    if args.difficulty == "normal":
        protected = {checkpoints.ROOT / "eval/balance/checkpoints_normal_053.json",
                     checkpoints.ROOT / "eval/balance/passive_defaults.json"}
        if args.checkpoint_output.resolve() in protected or (not args.passive_table and args.passive_output.resolve() in protected):
            parser.error("053 checkpoints and passive defaults are frozen")
    passive_digest = hashlib.sha256(args.passive_table.read_bytes()).hexdigest() if args.passive_table else None
    args.passive_n = args.passive_n or min(200, args.n)
    if min(args.n, args.probe_n, args.passive_n, args.workers) < 1:
        parser.error("sample sizes and workers must be positive")
    label = "baby-legacy" if args.difficulty == "baby" and args.spring == "legacy" else args.difficulty
    args.output = args.output or (normal_output / "measurement-normal.json" if args.difficulty == "normal" else OUTPUT_ROOT / f"053-measurement-v3-{label}.json")
    destinations = [args.output, args.output.with_suffix(".md"), args.records_output]
    if args.difficulty == "normal":
        destinations.append(args.checkpoint_output)
        if not args.passive_table:
            destinations.append(args.passive_output)
        if any(path and path.resolve() in protected for path in destinations):
            parser.error("Output paths cannot overwrite frozen 053 artifacts")
    if args.passive_table:
        if any(path and path.resolve() == args.passive_table.resolve() for path in destinations):
            parser.error("Output paths cannot overwrite the read-only passive table")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    from .measurement_v2 import input_fingerprints, variant_comparison
    started = time.perf_counter()
    frozen = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in FROZEN}
    fingerprints = input_fingerprints(args.scenario, args.save)
    base = state.load_scenario_pack(args.scenario)
    pack = select_spring(apply_difficulty(base, args.difficulty), args.spring)
    targets = json.loads((checkpoints.ROOT / "eval/balance/targets.json").read_text(encoding="utf-8"))
    settings = dict(difficulty=args.difficulty, spring=args.spring)
    timings = {"workers": args.workers}
    enumeration, defaults, branches = [], {}, {}

    def run_stage(name, jobs):
        stage = time.perf_counter()
        rows = route_v2.run_jobs(jobs, args.workers)
        timings[name] = time.perf_counter()-stage
        print(f"{name}: {len(rows)} rows, {timings[name]:.2f}s", flush=True)
        return rows

    if args.difficulty == "normal":
        if args.passive_table:
            defaults = json.loads(args.passive_table.read_text(encoding="utf-8"))
            for character in CHARACTERS:
                if defaults["characters"][character]["choices"] not in probes_v3.combinations(pack, character):
                    raise ValueError(f"Invalid frozen passive choices: {character}")
        else:
            enumeration = run_stage("passive_enumeration", [("enumerate_probes", args.scenario, c, args.passive_n, args.seed, {**settings, "choices": choices}) for c in CHARACTERS for choices in probes_v3.combinations(pack, c)])
            defaults = probes_v3.choose_defaults(pack, enumeration)
            args.passive_output.parent.mkdir(parents=True, exist_ok=True)
            args.passive_output.write_text(json.dumps(defaults, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        if args.tuning_052:
            from .normal_052 import escort_proposals
            branches = escort_proposals(args, settings, defaults, run_stage)
        else:
            branch_jobs = []
            for character in CHARACTERS:
                for fire_seed in ("accept", "refuse"):
                    for merchant in ("betray", "pay"):
                        choice = dict(fire_seed=fire_seed, merchant=merchant)
                        branch_jobs.append((args.scenario, "P3", character, args.passive_n, args.seed,
                            {**settings, "passive_table": defaults["characters"][character]["choices"], "branches": choice,
                             "branch_proposal": fire_seed+":"+merchant, "measure": False}))
            branch_records = run_stage("branch_proposals", branch_jobs)
            for character in CHARACTERS:
                proposals = []
                table = defaults["characters"][character]["choices"]
                # Use the same start seeds for the four mutually exclusive branch proposals.
                for fire_seed in ("accept", "refuse"):
                    for merchant in ("betray", "pay"):
                        choice = dict(fire_seed=fire_seed, merchant=merchant)
                        records = [r for r in branch_records if r["character"] == character and r["branch_proposal"] == fire_seed+":"+merchant]
                        proposals.append({"choices": choice, "n": len(records), "ignis_rate": mean(t["ignis_defeated"] for t in records)})
                best = max(proposals, key=lambda row: row["ignis_rate"])
                branches[character] = {"status": "proposed", "selected": best["choices"], "evidence": proposals, "tie": "first listed: accept then betray"}
            del branch_records
    jobs = [(args.scenario, a, c, args.n, args.seed, {**settings,
             "passive_table": defaults.get("characters", {}).get(c, {}).get("choices", {}),
             "branches": branches.get(c, {}).get("selected", {})}) for a in ARCHETYPES for c in CHARACTERS]
    records = run_stage("routes", jobs)
    metadata = {"spring": args.spring, "effective_pack_fingerprint": digest(pack), "overlay_fingerprint": overlay_fingerprint(base),
                "code_fingerprint": digest({k: v for k, v in fingerprints.items() if k.endswith(".py")}), "seed": args.seed, "seed_rule": probes_v3.SEED_RULE}
    if args.passive_table:
        metadata.update(passive_table_sha256=passive_digest, passive_table_mode="frozen_read_only")
    if args.tuning_052:
        metadata["measurement_scope"] = "052"
    bundle = {"records": records, "targets": targets, "difficulty": args.difficulty, "passive_defaults": defaults}
    if args.tuning_052:
        bundle["measurement_scope"] = "052"
    if args.difficulty == "normal":
        cp = probes_v3.export_checkpoints(records, metadata)
        args.checkpoint_output.parent.mkdir(parents=True, exist_ok=True)
        args.checkpoint_output.write_text(json.dumps(cp, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        bundle["damage_budget_v2"] = []
        for encounter, point in cp["encounters"].items():
            for character, entry in point["characters"].items():
                session = snapshots_v3.restore(pack, entry["snapshot"])
                opening = {}
                original = combat._apply_round_start_effects
                def capture_opening(current, rng):
                    if not opening:
                        if args.tuning_052:
                            from .normal_052 import opening_moments
                            opening.update(opening_moments(current))
                        else:
                            opening.update(budget.phase_moments(current))
                    return original(current, rng)
                rng = random.Random(route_v2.sim.trial_seed(args.seed, "opening:"+encounter, character, 0))
                session["combat_start_requested"] = True
                with patch.object(combat, "random", rng), patch.object(state, "random", rng), patch.object(combat, "_apply_round_start_effects", capture_opening):
                    combat.ensure_combat_started(session)
                if opening:
                    if args.tuning_052:
                        from .normal_052 import first_three_rounds
                        opening["first_three_rounds"] = first_three_rounds(pack, entry["snapshot"], args.seed, encounter)
                    bundle["damage_budget_v2"].append({"character": character, "encounter": encounter,
                        "encounter_class": session["combat"]["encounter"].get("encounter_class"), "level": session["character"]["level"],
                        "source": "P2 observed median-level opening, before first round-start attacks", **opening})
        for kind in ("preparation_probes", "companion_probes", "level_probes", "boss_policy_probes", "passive_probes"):
            if kind == "passive_probes" and args.skip_passive_probes:
                bundle[kind] = []
                continue
            bundle[kind] = run_stage(kind, [("normal_"+kind, args.scenario, c, args.probe_n, args.seed,
                {**settings, "checkpoint_path": str(args.checkpoint_output), "passive_table": defaults["characters"][c]["choices"], "encounter": encounter})
                for encounter, point in cp["encounters"].items() for c in CHARACTERS if c in point["characters"]])
        profiles = {}
    else:
        cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
        points, probe_targets = probes_v2.extended_inputs(pack, cp, targets)
        bundle["damage_budget_v2"] = probes_v2.damage_budget(pack, points, probe_targets)
        probe_inputs = args.output.with_name(args.output.stem+"-probe-inputs.json")
        probe_inputs.write_text(json.dumps({"checkpoints": points, "targets": probe_targets}, ensure_ascii=False)+"\n", encoding="utf-8")
        for kind in ("preparation_probes", "companion_probes", "level_probes", "boss_policy_probes"):
            encounters = [None] if kind == "preparation_probes" else [e for e, category in probe_targets["encounters"].items() if category == "boss"]
            bundle[kind] = run_stage(kind, [(kind, args.scenario, c, args.probe_n, args.seed,
                {**settings, "probe_inputs_path": str(probe_inputs), **({"encounter": encounter} if encounter else {})})
                for c in CHARACTERS for encounter in encounters])
        human = probes_v2.observed_checkpoint(json.loads(args.save.read_text(encoding="utf-8")))
        frozen_write(route_v2.BERSERKER, json.dumps(human, ensure_ascii=False, indent=2)+"\n")
        profiles = {row["profile"]: {key: value for key, value in row.items() if key != "profile"}
                    for row in run_stage("human_checkpoint", [("checkpoint_probes", args.scenario, "hero", args.n, args.seed,
                        {**settings, "profile": name, "checkpoint_entry": entry}) for name, entry in human["profiles"].items()])}
    rows = route_v2.summarize(records)
    baseline_path = checkpoints.ROOT / "eval/reports/046-measurement-v2-baseline.json"
    old = json.loads(baseline_path.read_text(encoding="utf-8"))
    baby = json.loads(args.baby_reference.read_text(encoding="utf-8"))["rows"] if args.baby_reference else []
    from .policy_v3 import PARAMETERS
    result = {"version": 3, "status": "measurement_complete", "difficulty": args.difficulty, **metadata,
        "n": args.n, "probe_n": args.probe_n, "passive_n": args.passive_n,
        "completion_definition": COMPLETION_TITLE, "rows": rows, "baby_rows": baby,
        "ignis_levels": arrival_rows(records, targets), "metrics": metrics_v3.evaluate(bundle), "cell_metrics": metrics_v3.per_cell(bundle),
        "targets": targets, "archetypes": {key: {**value.to_dict(),
            "effective_combat_policy": "heuristic_v3" if args.difficulty == "normal" and key in {"P1", "P2", "P3", "P2s"} else value.combat_policy,
            "effective_recovery_threshold": PARAMETERS["healing_threshold"] if args.difficulty == "normal" and key in {"P1", "P2", "P3", "P2s"} else value.recovery_threshold} for key, value in ARCHETYPES.items()},
        "passive_defaults": defaults, "passive_enumeration": enumeration, "branch_proposals": branches,
        "usage": stats(records), "strategy_parameters": PARAMETERS, "checkpoint_probes": profiles,
        "legacy_comparison": deltas(rows, old["rows"]), "p2s_comparison": variant_comparison(rows),
        "m3b": [dict(archetype=t["archetype"], character=t["character"], encounter=b["encounter"],
            value=(b["expected_healing"]+b.get("m3b_additional_healing_per_round", 0))/b["opening"]["expected_damage"] if b["opening"]["expected_damage"] else None)
                 for t in records for b in t["battles"] if b["encounter_class"] == "boss"],
        "grinding": [dict(character=t["character"], seed=t["seed"], costs=t.get("level_costs", [])) for t in records if t["archetype"] == "P0b"],
        "samples": [t for t in records if "steps" in t], "fingerprints": fingerprints,
        "limitations": ["052 percentage attacks and visible telegraphs use engine settlement; no new hazard content." if args.tuning_052 else "No hazard or percentage-damage route handling; no such hazard in current pack.",
                         "Opening expectations use current living foes; multi-hit kill truncation and sequential shield depletion are approximations in policy scoring, actual combat remains engine-exact.",
                         "No checkpoints fabricated for unobserved encounters/classes; proposed passive table and branches require design review.",
                         "P0g has no repeatable encounters; its paired outcomes equal P0b; resource cost is net resource_score change including rewards and level refill."],
        "timings": timings, "elapsed_seconds": time.perf_counter()-started}
    if args.tuning_052:
        from .policy_v3 import TELEGRAPH_PARAMETERS
        result["telegraph_strategy_parameters"] = TELEGRAPH_PARAMETERS
    if input_fingerprints(args.scenario, args.save) != fingerprints:
        raise RuntimeError("Measurement inputs changed during run")
    if args.passive_table and hashlib.sha256(args.passive_table.read_bytes()).hexdigest() != passive_digest:
        raise RuntimeError("Frozen passive table changed during run")
    if frozen != {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in FROZEN}:
        raise RuntimeError("Frozen historical artifact changed")
    if args.records_output:
        args.records_output.parent.mkdir(parents=True, exist_ok=True)
        args.records_output.write_text(json.dumps(bundle, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "metrics": {m["id"]: m["status"] for m in result["metrics"]}, "elapsed_seconds": result["elapsed_seconds"]}), flush=True)
    return int(args.check and args.difficulty == "normal" and any(m["hard_gate"] and m["status"] == "fail" for m in result["metrics"]))


if __name__ == "__main__":
    raise SystemExit(main())
