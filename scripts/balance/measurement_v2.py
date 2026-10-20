"""Complete offline stage-A measurement, retaining the historical 046 gate report."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

from host import state
from scripts.playtest import save_telemetry
from . import checkpoints, metrics_v2, probes_v2, reproduction_v2, route_v2
from .archetypes import ARCHETYPES, CHARACTERS, COMPLETION_TITLE


def input_fingerprints(scenario: Path, save: Path) -> dict[str, str]:
    paths = {scenario, save, checkpoints.DEFAULT_CHECKPOINTS, probes_v2.PREPARATIONS,
             checkpoints.ROOT / "eval/balance/targets.json"}
    paths.update((checkpoints.ROOT / "host").glob("*.py"))
    paths.update((checkpoints.ROOT / "scripts/balance").glob("*.py"))
    paths.add(checkpoints.ROOT / "scripts/playtest/save_telemetry.py")
    result = {}
    for path in sorted({p.resolve() for p in paths}):
        if path.exists():
            key = path.relative_to(checkpoints.ROOT).as_posix() if path.is_relative_to(checkpoints.ROOT) else path.as_posix()
            result[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def variant_comparison(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for character in CHARACTERS:
        pair = {r["archetype"]: r for r in rows if r["character"] == character and r["archetype"] in {"P2", "P2s"}}
        if len(pair) != 2:
            continue
        left, right = pair["P2"], pair["P2s"]
        levels = {node: abs(left["levels_mean"][node] - right["levels_mean"][node])
                  for node in left["levels_mean"].keys() & right["levels_mean"].keys()}
        result.append(dict(character=character, completion_gap_pp=abs(left["completion_rate"]-right["completion_rate"])*100,
                           level_gaps=dict(sorted(levels.items())),
                           meets_draft=abs(left["completion_rate"]-right["completion_rate"]) <= .10+1e-12 and
                                       all(gap <= 1+1e-12 for gap in levels.values()),
                           missing_nodes=sorted(left["levels_mean"].keys() ^ right["levels_mean"].keys())))
    return result


def markdown(result: dict[str, Any]) -> str:
    lines = ["# 046 测量 v2 完整基线（046b）", "", "主通关口径：冒険完了；击败/净化 Ignis 与进入终局另列。全程离线。",
             "终局列按 draco_battle 或任一 ending 字段统计，包含引擎记录的失败结局，不能当作主线完成率。",
             "046b 设计决定已接受第一轮 Ignis 复现；P0b >90% 不再是复现门槛。M1 的草案上限仍保留。", "",
             "| 原型 | 职业 | N | 通关率 | 草案区间 | Ignis | 终局 | Ignis回合中位数 |",
             "|---|---|---:|---:|---|---:|---:|---:|"]
    for row in result["rows"]:
        target = result["targets"]["archetypes"][row["archetype"]]
        interval = target.get("mage_completion_rate") if row["character"] == "mage" and "mage_completion_rate" in target else target.get("completion_rate")
        lines.append(f"| {row['archetype']} | {row['character']} | {row['n']} | {row['completion_rate']:.1%} | {interval} | {row['ignis_rate']:.1%} | {row['terminal_rate']:.1%} | {row['ignis_rounds_median']} |")
    lines += ["", "| 指标 | 状态 | 硬门槛 | 满足草案目标 | 说明 |", "|---|---|---|---|---|"]
    for metric in result["metrics"]:
        lines.append(f"| {metric['id']} | {metric['status']} | {metric['hard_gate']} | {metric['meets_target']} | {metric['reason'] or ''} |")
    lines += ["", "完整逐配置数值、与目标差距和样本见同名 JSON 的 metrics.value；report 不表示通过。", "",
              "| 存档核对后独立配置 | 胜率 | 回合中位数 | S |", "|---|---:|---:|---:|"]
    for name, probe in result["checkpoint_probes"].items():
        lines.append(f"| {name} | {probe['win_rate']:.1%} | {probe['rounds_median']} | {probe['sustain_coverage']:.4f} |")
    lines += ["", "存档核对：Ignis 时鉄の剣/革の鎧/紅玉の護符；アダマンタイトの鎧在战后才装备。",
              "独立配置采用满资源；库存按此前战斗结算和资源流水重建，不能视为完整开战遥测。", "",
              "| 文档威胁对照 | M9 | CV | 状态 | 超差说明 |", "|---|---:|---:|---|---|"]
    for row in result["threat_scan"]:
        lines.append(f"| {row['encounter']} | {row['ratio']:.2%} | {row['cv']:.4f} | {row['status']} | {row.get('difference_reason') or ''} |")
    lines += ["", "P2s 与 P2：", "", "```json", json.dumps(result["p2s_comparison"], ensure_ascii=False, indent=2), "```", "",
              "P0g：当前没有能保留收益的重复战斗；不清除 defeated flags，EXP 每级资源成本待 050/051。", "",
              "P2/P3 支线清单为 proposed；P3 采用可连通、非互斥的一条全支线提案，不强制判定成功。",
              "P2 包含ガルド、リク、完整洞窟、ゴブリン砦、净化线索；P3 另加城镇交付、ミーナ、旧戦場、オークスドーン、峡谷、屋敷、商人、ロビン和三组收集交付。",
              "P2s 对有绕行选项的战斗优先尝试绕行，失败仍承受真实战斗；同伴不是强制借用成功。", "",
              "遥测详见 046b-save-telemetry.json / .md：17 个可观察战斗结算、14 次判定；较早的4场缺回合数，完整动作记录缺失。", "",
              f"N={result['n']}，探针每格 N={result['probe_n']}，seed={result['seed']}，workers={result['workers']}。",
              f"全量主批次墙钟 {result['elapsed_seconds']:.2f} 秒；分阶段及补充复核 {result['timings']}。补充批次可能与主批次重叠，不将各项直接相加。", ""]
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="046b complete measurement, offline only")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--probe-n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--scenario", type=Path, default=checkpoints.DEFAULT_SCENARIO)
    parser.add_argument("--save", type=Path, default=save_telemetry.DEFAULT_SAVE)
    parser.add_argument("--output", type=Path, default=route_v2.DEFAULT_OUTPUT)
    parser.add_argument("--records-output", type=Path, help="Optional full reducer inputs for auditing/reducing again")
    parser.add_argument("--check", action="store_true", help="Exit 1 for failed hard draft gates")
    args = parser.parse_args(argv)
    if min(args.n, args.probe_n, args.workers) < 1:
        parser.error("n, probe-n and workers must be positive")
    started = time.perf_counter()
    fingerprints = input_fingerprints(args.scenario, args.save)
    targets_path = checkpoints.ROOT / "eval/balance/targets.json"
    targets = json.loads(targets_path.read_text(encoding="utf-8"))
    pack = state.load_scenario_pack(args.scenario)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    probe_cp, probe_targets = probes_v2.extended_inputs(pack, cp, targets)
    save = json.loads(args.save.read_text(encoding="utf-8"))
    timings = {}
    stage = time.perf_counter()
    records = route_v2.run_jobs([(args.scenario, a, c, args.n, args.seed) for a in ARCHETYPES for c in CHARACTERS], args.workers)
    timings["routes"] = time.perf_counter()-stage
    print(f"routes complete: {len(records)} records / {timings['routes']:.2f}s", flush=True)
    rows = route_v2.summarize(records)
    bundle = {"records": records, "targets": targets, "fingerprints": fingerprints,
              "damage_budget_v2": probes_v2.damage_budget(pack, probe_cp, probe_targets)}
    for kind in ("preparation_probes", "companion_probes", "level_probes", "boss_policy_probes"):
        stage = time.perf_counter()
        bundle[kind] = route_v2.run_jobs([(kind, args.scenario, c, args.probe_n, args.seed) for c in CHARACTERS], args.workers)
        timings[kind] = time.perf_counter()-stage
        print(f"{kind}: {len(bundle[kind])} cells / {timings[kind]:.2f}s", flush=True)
    if args.records_output:
        args.records_output.parent.mkdir(parents=True, exist_ok=True)
        args.records_output.write_text(json.dumps(bundle, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    stage = time.perf_counter()
    human = probes_v2.observed_checkpoint(save)
    route_v2.BERSERKER.write_text(json.dumps(human, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    profiles = reproduction_v2.checkpoint_trials(pack, human, args.n, args.seed)
    timings["human_checkpoint"] = time.perf_counter()-stage
    telemetry = save_telemetry.extract(save, preparations=json.loads(probes_v2.PREPARATIONS.read_text(encoding="utf-8")), archetype_rows=rows)
    telemetry["save_sha256"] = hashlib.sha256(args.save.read_bytes()).hexdigest()
    telemetry_path = args.output.parent / "046b-save-telemetry.json"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    telemetry_path.write_text(json.dumps(telemetry, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    telemetry_path.with_suffix(".md").write_text(save_telemetry.markdown(telemetry), encoding="utf-8")
    metrics = metrics_v2.evaluate(bundle)
    if input_fingerprints(args.scenario, args.save) != fingerprints:
        raise RuntimeError("Measurement inputs changed during the run; use a stable checkout or snapshot and rerun")
    result = {"version": 2, "status": "measurement_complete", "reproduction_status": "accepted_by_046b",
              "n": args.n, "probe_n": args.probe_n, "seed": args.seed, "workers": args.workers,
              "completion_definition": COMPLETION_TITLE, "original_save_available": True,
              "terminal_definition": "draco_battle or any engine ending, including defeat endings",
              "rows": rows, "metrics": metrics, "targets": targets,
              "archetypes": {key: value.to_dict() for key, value in ARCHETYPES.items()},
              "checkpoint_probes": profiles, "threat_scan": reproduction_v2.threat_scan(pack, cp),
              "p2s_comparison": variant_comparison(rows),
              "samples": [next(t for t in records if t["archetype"] == row["archetype"] and t["character"] == row["character"]) for row in rows],
              "engine_recording_gaps": telemetry["engine_recording_gaps"],
              "fingerprints": fingerprints,
              "timings": timings, "elapsed_seconds": time.perf_counter()-started}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "elapsed_seconds": result["elapsed_seconds"],
                      "metrics": {m["id"]: m["status"] for m in metrics}}, ensure_ascii=False), flush=True)
    return int(args.check and any(m["hard_gate"] and m["status"] == "fail" for m in metrics))


if __name__ == "__main__":
    raise SystemExit(main())
