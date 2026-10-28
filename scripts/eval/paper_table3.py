"""Recompute the paper's schema-shape grid (Table 3) and the E4 table under scoring v1.2. Offline only.

Each cell is a historical v2-dev run, loaded with paired_stats.load_run (stored cases.jsonl, else cache replay with
the matching system prompt) and summarized with the current metrics.summarize. Cases without a cached response are
dropped from the denominator, never re-requested.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Optional

from .metrics import summarize
from .paired_stats import RunData, Sessions, frozen_context, load_run
from .snapshots import ROOT

COLUMNS = ("Flat-Strict", "Flat-Lenient", "Union-Enum", "Union-NoEnum")
# (model label, run-id prefixes in COLUMNS order). All are v2 dev, prompt P0, 2026-10-11.
GRID: list[tuple[str, tuple[str, str, str, str]]] = [
    ("Gemini 3.1 Flash-Lite", ("2026-10-11T112514831356Z", "2026-10-11T112526523573Z",
                               "2026-10-11T112538606761Z", "2026-10-11T113141950061Z")),
    ("qwen3-swallow-8b-rl", ("2026-10-11T112514831499Z", "2026-10-11T114837268186Z",
                             "2026-10-11T114851107708Z", "2026-10-11T121149336492Z")),
    ("elyza-jp-8b", ("2026-10-11T122755485947Z", "2026-10-11T124207361839Z",
                     "2026-10-11T124213992341Z", "2026-10-11T125600553788Z")),
    ("qwen2.5-3b-q8", ("2026-10-11T130923957822Z", "2026-10-11T132243419395Z",
                       "2026-10-11T132250297569Z", "2026-10-11T133323873595Z")),
    ("qwen2.5-7b", ("2026-10-11T134405010054Z", "2026-10-11T135915630752Z",
                    "2026-10-11T135922712080Z", "2026-10-11T141110622073Z")),
]
PAIRED_REPORT = ROOT / "eval" / "reports" / "paper-paired-stats.md"


def cell(data: RunData) -> dict[str, Any]:
    with frozen_context(True):
        metrics = summarize(list(data.records.values()))
    levels = metrics["severity"]
    return {"run_id": data.run_id, "n": metrics["evaluated"], "total": metrics["total"],
            "s01": levels["S0"] + levels["S1"], "s3": levels["S3"], "s4": levels["S4"],
            "invalid": round((metrics["invalid_plan_rate"] or 0) * metrics["evaluated"]),
            "conflict": metrics["conflict_count"], "source": data.source, "prompt": data.prompt,
            "old": data.report["metrics"]}


def pct(count: int, n: int) -> str:
    return f"{count / n:.1%}" if n else "n/a"


def cell_text(c: dict[str, Any], column: str) -> str:
    extra = f"冲突 {pct(c['conflict'], c['n'])}" if column == "Flat-Lenient" else f"IP {pct(c['invalid'], c['n'])}"
    return f"{pct(c['s01'], c['n'])} / {pct(c['s3'], c['n'])}（{extra}）"


def old_text(c: dict[str, Any], column: str) -> str:
    m = c["old"]
    extra = (f"冲突 {m['conflict_rate']:.1%}" if column == "Flat-Lenient" else f"IP {m['invalid_plan_rate']:.1%}")
    return f"{m['s0_s1_rate']:.1%} / {m['s3_rate']:.1%}（{extra}）"


def paired_report_cells(path: Path = PAIRED_REPORT) -> dict[str, tuple[str, str, int]]:
    """v1.2 S0+S1 / S3 / n per run id, as printed in the paired-stats report's run table."""
    found = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\| `([^`]+)` \|.*\| ([\d.]+%) / ([\d.]+%)（n=(\d+)） \|$", line)
        if match:
            found[match.group(1)] = (match.group(2), match.group(3), int(match.group(4)))
    return found


def check_against_paired(cells: dict[str, dict[str, Any]], reported: dict[str, tuple[str, str, int]]) -> list[str]:
    problems = []
    for run_id, (s01, s3, n) in reported.items():
        if run_id not in cells:
            continue
        c = cells[run_id]
        mine = (pct(c["s01"], c["n"]), pct(c["s3"], c["n"]), c["n"])
        if mine != (s01, s3, n):
            problems.append(f"{run_id}: recomputed {mine} vs paired-stats {(s01, s3, n)}")
    return problems


def best(row: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    # Highest S0+S1 rate; ties go to the lower S3 count, then to column order.
    order = {name: i for i, name in enumerate(COLUMNS)}
    return min(row.items(), key=lambda kv: (-kv[1]["s01"] / kv[1]["n"], kv[1]["s3"] / kv[1]["n"], order[kv[0]]))


def latency(c: dict[str, Any]) -> str:
    lat = c["old"]["latency_ms"]
    return f"{lat['p50'] / 1000:.2f} / {lat['p95'] / 1000:.2f} s"


def render(grid: dict[str, dict[str, dict[str, Any]]], problems: list[str], checked: int) -> list[str]:
    head = "| 模型 | " + " | ".join(COLUMNS) + " |"
    rule = "|---|" + "---|" * len(COLUMNS)
    lines = ["# 表 3 与 E4 表的 v1.2 重算（离线）", "",
             "生成：`python -m scripts.eval.paper_table3`（不联网，不调用模型）。逐格用 `scripts.eval.paired_stats.load_run` "
             "读取原运行的模型响应（有 `eval/runs/<id>/cases.jsonl` 时读逐条记录，否则按原 backend/model/变体名与匹配的 "
             "system prompt 离线重放 `eval/cache`），再用当前 `parse_plan`（含 existing 归一化）、当前 gold 与 "
             "`metrics.summarize` 评分，即评分 v1.2。缓存缺失的条目不计入分母。", "",
             "## 表 3（v2 dev，评分 v1.2）", "",
             "每格为“S0+S1 / S3”，括号内为 InvalidPlan 率（IP），Flat-Lenient 列为冲突率。", "", head, rule]
    for model, row in grid.items():
        lines.append(f"| {model} | " + " | ".join(cell_text(row[c], c) for c in COLUMNS) + " |")
    lines += ["", "### 分母与条数", "", "| 模型 | " + " | ".join(COLUMNS) + " |", rule]
    for model, row in grid.items():
        lines.append(f"| {model} | " + " | ".join(
            f"n={row[c]['n']}/{row[c]['total']}；S0+S1 {row[c]['s01']}，S3 {row[c]['s3']}，IP {row[c]['invalid']}"
            + (f"，冲突 {row[c]['conflict']}" if c == "Flat-Lenient" else "") + f"，S4 {row[c]['s4']}"
            for c in COLUMNS) + " |")
    lines += ["", "## 表 3（v2 dev，评分 v1.1，原运行报告）", "", head, rule]
    for model, row in grid.items():
        lines.append(f"| {model} | " + " | ".join(old_text(row[c], c) for c in COLUMNS) + " |")
    lines += ["", "## E4：各模型 v1.2 下 S0+S1 最高的配置", "",
              "延迟取自 Flat-Strict 原运行报告（194 次请求的 p50 / p95，与评分无关）；成本同原报告。", "",
              "| 模型 | 最佳配置 | n | S0+S1 | S3 | p50 / p95（Flat-Strict 请求） | 每回合成本 |",
              "|---|---|---:|---|---|---|---|"]
    for model, row in sorted(grid.items(), key=lambda kv: -best(kv[1])[1]["s01"] / best(kv[1])[1]["n"]):
        name, c = best(row)
        cost = row["Flat-Strict"]["old"].get("cost_per_turn")
        lines.append(f"| {model} | {name} | {c['n']} | {pct(c['s01'], c['n'])}（{c['s01']}） | {pct(c['s3'], c['n'])}（{c['s3']}） | "
                     f"{latency(row['Flat-Strict'])} | {f'${cost:.6f}' if cost else '0'} |")
    lines += ["", "## 与配对检验报告的核对", "",
              f"`eval/reports/paper-paired-stats.md` 运行表中与本网格重合的 {checked} 个运行，其 v1.2 S0+S1 / S3 / n "
              + ("与本表逐一一致。" if not problems else "与本表不一致：") ]
    lines += [f"- {p}" for p in problems]
    lines += ["", "## 运行来源", "", "| 模型 | 列 | run id | 来源 | 匹配的 system prompt |", "|---|---|---|---|---|"]
    for model, row in grid.items():
        for c in COLUMNS:
            lines.append(f"| {model} | {c} | `{row[c]['run_id']}` | {row[c]['source']} | {row[c]['prompt']} |")
    return lines


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Recompute the paper's Table 3 / E4 table under scoring v1.2 (offline).")
    parser.add_argument("--out", type=Path, default=ROOT / "eval" / "reports" / "paper-table3-v12.md")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sessions = Sessions()
    grid: dict[str, dict[str, dict[str, Any]]] = {}
    by_run: dict[str, dict[str, Any]] = {}
    for model, prefixes in GRID:
        grid[model] = {}
        for column, prefix in zip(COLUMNS, prefixes):
            c = cell(load_run(prefix, sessions))
            grid[model][column] = by_run[c["run_id"]] = c
            print(f"{model} {column}: {cell_text(c, column)} n={c['n']}", flush=True)
    reported = paired_report_cells()
    problems = check_against_paired(by_run, reported)
    checked = sum(run_id in by_run for run_id in reported)
    args.out.write_text("\n".join(render(grid, problems, checked)) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {args.out}; checked {checked} runs against paired stats; mismatches: {len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
