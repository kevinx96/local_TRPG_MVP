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
             checkpoints.ROOT / "eval/balance/targets.json", checkpoints.ROOT / "eval/balance/strategy_v3.json"}
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
    from .measurement_v3 import main as measure
    return measure(argv)


if __name__ == "__main__":
    raise SystemExit(main())
