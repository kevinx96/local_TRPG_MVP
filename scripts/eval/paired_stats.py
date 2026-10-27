"""Paired significance tests between two intent-eval runs. Offline only: never sends a model request.

Per-case outcomes are recomputed with the CURRENT scoring (scoring v1.2: scripts/eval/metrics.severity,
current gold labels, current free_actions.parse_plan contract normalization), not read from the old reports.
Raw model responses come from the run's cases.jsonl when it still exists, otherwise from eval/cache
(the same replay `scripts.eval.run` does without --live).
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import dataclass, field, replace
from math import comb
from pathlib import Path
from typing import Any, Iterator, Optional
from unittest.mock import patch

from host import free_actions, gm_contract, item_mechanics, llm_client, state
from .audit import costly_plan
from .cache import cache_key, read_cache
from .metrics import percentile, severity
from .requests import evaluation_config
from .run import engine_result, evaluate_case
from .snapshots import ROOT, load_snapshot
from .variants import VARIANTS, clean_lenient

SEED = 20261027
RESAMPLES = 10_000
EVALUATED = {"ok", "invalid_plan", "json_error"}
METRICS = ("S0+S1", "S3")
FROZEN_DIR = ROOT / "eval" / "benchmark"

# System prompts the default-family variants have had; replay picks the one whose cache keys hit.
PROMPT_CANDIDATES = (("as defined in variants.py", None),
                     ("pre_guard (PLAN_PROMPT_BASE)", free_actions.PLAN_PROMPT_BASE),
                     ("guard_rules (PRE_SEQUENCE)", free_actions.PLAN_PROMPT_PRE_SEQUENCE),
                     ("pre_offtopic", free_actions.PLAN_PROMPT_PRE_OFFTOPIC),
                     ("legacy default (+offtopic)", free_actions.LEGACY_PLAN_PROMPT))


@dataclass
class RunData:
    run_id: str
    report: dict[str, Any]
    source: str                      # "stored cases.jsonl" or "cache replay"
    prompt: str                      # which system prompt the cache keys matched (replay) or n/a
    hits: Optional[tuple[int, int]]  # cache hits / cases (replay only)
    records: dict[str, dict[str, Any]]
    severity: dict[str, str] = field(default_factory=dict)
    engine_recomputed: int = 0       # stored runs: records whose plan changed and were re-adjudicated


@contextmanager
def frozen_context(frozen: bool) -> Iterator[None]:
    """Same patches scripts.eval.run applies for the frozen benchmark (cached with legacy ids/prompt)."""
    with ExitStack() as stack:
        stack.enter_context(patch.object(item_mechanics, "LEGACY_ELEMENT_IDS", frozen))
        stack.enter_context(patch.object(free_actions, "LEGACY_PLAN", frozen))
        stack.enter_context(patch.object(free_actions, "OPERATIONS",
                                         free_actions.LEGACY_OPERATIONS if frozen else free_actions.OPERATIONS))
        # Belt and braces: replay must never reach a model.
        stack.enter_context(patch.object(llm_client, "chat_completion",
                                         side_effect=AssertionError("paired_stats is offline only")))
        yield


def resolve_report(prefix: str) -> tuple[str, dict[str, Any]]:
    matches = sorted(p for p in (ROOT / "eval" / "reports").glob(f"{prefix}*.json") if "schema-smoke" not in p.name)
    if len(matches) != 1:
        raise SystemExit(f"run id {prefix!r}: expected one report JSON in eval/reports, found {len(matches)}")
    return matches[0].stem, json.loads(matches[0].read_text(encoding="utf-8"))


def load_cases(report: dict[str, Any]) -> tuple[Path, list[dict[str, Any]]]:
    path = (ROOT / Path(report["cases"].replace("\\", "/"))).resolve()
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return path, [c for c in cases if report["split"] == "all" or c["split"] == report["split"]]


class Sessions:
    def __init__(self) -> None:
        self.cache: dict[str, dict[str, Any]] = {}

    def get(self, snapshot: str) -> dict[str, Any]:
        if snapshot not in self.cache:
            self.cache[snapshot] = load_snapshot(snapshot)
        return self.cache[snapshot]


def character_id(snapshot: str) -> str:
    """Read the recipe only; building the snapshot would load the scenario pack, which may be mid-edit."""
    recipe = json.loads((ROOT / "eval" / "snapshots" / f"{snapshot}.json").read_text(encoding="utf-8"))
    return recipe["character_id"]


def rescore_stored(stored: dict[str, Any], case: dict[str, Any], variant: str, sessions: Sessions) -> tuple[dict[str, Any], bool]:
    """Re-run the post-response half of evaluate_case on a stored raw response with current code and labels."""
    record = {**deepcopy(case), "status": stored["status"], "raw_response": stored.get("raw_response"),
              "plan": None, "engine": None, "usage": stored.get("usage", {})}
    if stored["status"] not in EVALUATED or record["raw_response"] is None:
        return record, False
    session_id = case["snapshot"]
    cleaned = gm_contract._strip_thinking_text(record["raw_response"]).strip()
    if variant == "lenient":
        cleaned, record["lenient"] = clean_lenient(cleaned)
    recomputed = False
    try:
        cleaned = VARIANTS[variant].unwrap(cleaned)
        plan = free_actions.parse_plan(cleaned, character_id(session_id))
        record["plan"] = plan
        if stored.get("plan") == plan and stored.get("engine") is not None:
            record["engine"] = stored["engine"]
            if case.get("harmful") is None:  # severity reads costs only without an explicit harmful rule
                same_gold = stored.get("gold") == case["gold"] and stored.get("costs")
                record["costs"] = stored["costs"] if same_gold else {
                    "plan": costly_plan(sessions.get(session_id), plan),
                    "gold": [costly_plan(sessions.get(session_id), g) for g in case["gold"]]}
        else:
            session = sessions.get(session_id)
            record["costs"] = {"plan": costly_plan(session, plan), "gold": [costly_plan(session, g) for g in case["gold"]]}
            record["engine"] = engine_result(session, plan, case["input"])
            recomputed = True
        record["status"] = "ok"
    except free_actions.InvalidPlan as exc:
        record["status"] = "json_error" if str(exc) == "invalid JSON" else "invalid_plan"
        record["invalid_plan_reason"] = str(exc)
        record["engine"] = {"outcome": "rejected", "attack_or_combat": False, "changes": {}}
    return record, recomputed


def pick_prompt(cases: list[dict[str, Any]], config: dict[str, Any], backend: str, model: str, variant: str,
                sessions: Sessions, expected_tokens: Optional[float]) -> tuple[str, Optional[str], int, str]:
    """Choose the system prompt behind a historical run from its cache keys (key-only check, no engine).

    Several prompts can have complete cache entries under the same variant name (e.g. the 10-12 test split holds
    both the pre_guard and the final default responses), so hits alone are ambiguous. Among candidates covering
    at least 90% of the cases, take the one whose cached input-token mean is closest to the run report's mean.
    """
    base = VARIANTS[variant]
    candidates = PROMPT_CANDIDATES if base.system_prompt is None else PROMPT_CANDIDATES[:1]
    scored = []
    for label, prompt in candidates:
        probe = replace(base, system_prompt=prompt) if prompt is not None else base
        tokens = []
        for case in cases:
            messages, request_config = probe.prepare(sessions.get(case["snapshot"]), case["input"], config)
            entry = read_cache(ROOT / "eval" / "cache", cache_key(backend, model, variant, messages, request_config))
            if entry is not None and entry.get("usage", {}).get("input_tokens") is not None:
                tokens.append(entry["usage"]["input_tokens"])
            elif entry is not None:
                tokens.append(None)
        known = [t for t in tokens if t is not None]
        scored.append((label, prompt, len(tokens), sum(known) / len(known) if known else None))
    complete = [c for c in scored if c[2] >= 0.9 * len(cases)] or sorted(scored, key=lambda c: -c[2])[:1]
    if expected_tokens is not None and any(c[3] is not None for c in complete):
        complete = sorted((c for c in complete if c[3] is not None), key=lambda c: abs(c[3] - expected_tokens))
    label, prompt, hits, mean = complete[0]
    evidence = (f"cached input-token mean {mean:.1f} vs report {expected_tokens:.1f}"
                if mean is not None and expected_tokens is not None else "hits only")
    others = "; ".join(f"{c[0]}: {c[2]} hits" for c in scored if c[2])
    return label, prompt, hits, f"{evidence} ({others})"


def load_run(prefix: str, sessions: Sessions) -> RunData:
    run_id, report = resolve_report(prefix)
    cases_path, cases = load_cases(report)
    frozen = FROZEN_DIR in cases_path.parents
    variant, backend, model = report["variant"], report["backend"], report["model"]
    stored_path = ROOT / "eval" / "runs" / run_id / "cases.jsonl"
    with frozen_context(frozen):
        if stored_path.exists():
            stored = {r["id"]: r for r in (json.loads(l) for l in stored_path.read_text(encoding="utf-8").splitlines() if l.strip())}
            records: dict[str, dict[str, Any]] = {}
            recomputed = 0
            for case in cases:
                if case["id"] not in stored:
                    continue
                records[case["id"]], again = rescore_stored(stored[case["id"]], case, variant, sessions)
                recomputed += again
            data = RunData(run_id, report, "stored cases.jsonl", "n/a (stored responses)", None, records,
                           engine_recomputed=recomputed)
        else:
            config = evaluation_config(state.load_config(), backend, model, rpm=0)
            label, prompt, hits, evidence = pick_prompt(
                cases, config, backend, model, variant, sessions,
                report["metrics"]["tokens"]["input_tokens"]["mean"])
            if hits == 0:
                raise SystemExit(f"{run_id}: no cache entries match any known prompt; cannot replay")
            patched = replace(VARIANTS[variant], system_prompt=prompt) if prompt is not None else VARIANTS[variant]
            records = {}
            with patch.dict(VARIANTS, {variant: patched}):
                for case in cases:
                    records[case["id"]] = evaluate_case(case, sessions.get(case["snapshot"]), config, backend, model,
                                                        variant, ROOT / "eval" / "cache", live=False)
            data = RunData(run_id, report, "cache replay", f"{label}; {evidence}", (hits, len(cases)), records)
    data.severity = {i: severity(r) for i, r in data.records.items() if r["status"] in EVALUATED}
    return data


def exact_mcnemar(b: int, c: int) -> float:
    """Two-sided exact McNemar: binomial test of the discordant pairs against p = 0.5."""
    m = b + c
    if m == 0:
        return 1.0
    return min(1.0, 2 * sum(comb(m, i) for i in range(min(b, c) + 1)) / 2 ** m)


def outcome(level: str, metric: str) -> int:
    return int(level in {"S0", "S1"}) if metric == "S0+S1" else int(level == "S3")


@dataclass
class PairResult:
    label: str
    a: RunData
    b: RunData
    n: int
    dropped: list[str]
    rows: list[dict[str, Any]]


def compare(label: str, a: RunData, b: RunData, tag: Optional[str] = None,
            resamples: int = RESAMPLES, seed: int = SEED) -> PairResult:
    scope = {i for i in {**a.records, **b.records} if tag is None or tag in {**a.records, **b.records}[i]["tags"]}
    ids = sorted(i for i in scope if i in a.severity and i in b.severity)
    dropped = sorted(scope - set(ids))
    if not ids:
        raise SystemExit(f"{label}: no case is evaluated in both runs")
    diffs: dict[str, list[int]] = {}
    rows = []
    for metric in METRICS:
        xs = [outcome(a.severity[i], metric) for i in ids]
        ys = [outcome(b.severity[i], metric) for i in ids]
        diffs[metric] = [y - x for x, y in zip(xs, ys)]
        only_a, only_b = sum(x > y for x, y in zip(xs, ys)), sum(y > x for x, y in zip(xs, ys))
        rows.append({"metric": metric, "a": sum(xs), "b": sum(ys), "only_a": only_a, "only_b": only_b,
                     "p": exact_mcnemar(only_a, only_b)})
    rng = random.Random(seed)
    n = len(ids)
    boot: dict[str, list[float]] = {metric: [] for metric in METRICS}
    for _ in range(resamples):
        sample = [rng.randrange(n) for _ in range(n)]
        for metric in METRICS:
            boot[metric].append(sum(diffs[metric][i] for i in sample) / n)
    for row in rows:
        values = boot[row["metric"]]
        row["diff"] = (row["b"] - row["a"]) / n
        row["ci"] = (percentile(values, 0.025), percentile(values, 0.975))
    return PairResult(label, a, b, n, dropped, rows)


def rate(count: int, n: int) -> str:
    return f"{count / n:.1%} ({count}/{n})"


def format_p(p: float) -> str:
    return f"{p:.4f}" if p >= 0.0001 else f"{p:.1e}"


def table_rows(result: PairResult) -> list[str]:
    lines = []
    for row in result.rows:
        low, high = row["ci"]
        lines.append(f"| {result.label} | {result.n} | {row['metric']} | {rate(row['a'], result.n)} | {rate(row['b'], result.n)} | "
                     f"{row['only_a']}/{row['only_b']} | {format_p(row['p'])} | "
                     f"{row['diff'] * 100:+.1f} pp [{low * 100:+.1f}, {high * 100:+.1f}] |")
    return lines


HEADER = ["| 对比 | n | 指标 | A 率 | B 率 | 不一致 b/c | McNemar 精确 p | B−A 自助法 95% CI |",
          "|---|---:|---|---|---|---|---|---|"]


# (label, run A, run B, optional tag filter, note). A and B are run-id prefixes; B-A is reported.
PAPER_PAIRS: list[tuple[str, str, str, Optional[str], str]] = [
    ("(a) E1 test: pre_guard→guard_rules", "2026-10-11T121040703064Z", "2026-10-11T195057330510Z", None,
     "A 是 008 的原始 pre_guard test 运行（当时以 default 名实跑），B 是 v1.2 评分后的离线重放（5.1.3 节的“后”）"),
    ("(b) E1 dev: pre_guard→guard_rules", "2026-10-11T120159376587Z", "2026-10-11T195050287754Z", None,
     "A 是 008 的原始 pre_guard dev 运行，B 是 v1.2 评分后的离线重放"),
    ("(c) E2 test: guard_rules→guard_sequence_item", "2026-10-12T062915606413Z", "2026-10-12T062927141458Z", None, ""),
    ("(d) E2 dev: guard_rules→guard_sequence_item", "2026-10-12T062656092753Z", "2026-10-12T062704069819Z", None, ""),
    ("(e1) E3 Gemini dev: default→lenient", "2026-10-11T112514831356Z", "2026-10-11T112526523573Z", None,
     "同一批响应，只有解析不同"),
    ("(e2) E3 qwen3-swallow dev: default→union_schema", "2026-10-11T112514831499Z", "2026-10-11T114851107708Z", None,
     "缓存对冻结剧本只命中 190/194（4 条地点描述漂移，两端都缺），所以 n=190 而不是论文的 194"),
    ("(f1) E5 补充集: default→guard_claims（均为秘密动作前）", "2026-10-11T191145950026Z", "2026-10-11T191200091981Z", None,
     "同一分钟先后实跑；基线 default 此时已含 guard_rules"),
    ("(f2) E5 补充集: default(秘密动作前)→default(秘密动作后)", "2026-10-11T191145950026Z", "2026-10-11T193956473760Z", None,
     "秘密动作是系统改动，两次运行的 planner 动作列表不同；采样随机性与动作列表变化混在一起"),
    ("(f3) E5 补充集: default(16:11, 秘密动作前)→default(秘密动作后)", "2026-10-11T161151095000Z", "2026-10-11T193956473760Z", None, ""),
    ("(f4) E5 补充集 evidence_claim 子集 (f2)", "2026-10-11T191145950026Z", "2026-10-11T193956473760Z", "evidence_claim", "子集分析，事后选择，仅供参考"),
    ("(g) 头条: pre_guard→最终 default（test）", "2026-10-11T121040703064Z", "2026-10-13T072950363331Z", None,
     "HEADLINE"),
]


def git_version() -> str:
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h %ad", "--date=short", "--", "scripts/eval/metrics.py",
                              "scripts/eval/audit.py", "host/free_actions.py"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.strip()
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
        return f"HEAD {head}; scoring/contract files last changed in {out}"
    except (OSError, subprocess.CalledProcessError):
        return "git unavailable"


def run_table(runs: dict[str, RunData]) -> list[str]:
    lines = ["| run id | variant / split | 来源 | 匹配的 system prompt | 缓存命中 | 原报告 S0+S1 / S3 | v1.2 重算 S0+S1 / S3（全部可评测条） |",
             "|---|---|---|---|---|---|---|"]
    for data in runs.values():
        metrics = data.report["metrics"]
        evaluated = len(data.severity)
        s01 = sum(v in {"S0", "S1"} for v in data.severity.values())
        s3 = sum(v == "S3" for v in data.severity.values())
        old = f"{metrics['s0_s1_rate']:.1%} / {metrics['s3_rate']:.1%}" if metrics.get("s0_s1_rate") is not None else "n/a"
        hits = f"{data.hits[0]}/{data.hits[1]}" if data.hits else "n/a"
        extra = f"（{data.engine_recomputed} 条因计划变化重新裁定）" if data.engine_recomputed else ""
        lines.append(f"| `{data.run_id}` | {data.report['variant']} / {data.report['split']} | {data.source}{extra} | {data.prompt} | "
                     f"{hits} | {old} | {s01 / evaluated:.1%} / {s3 / evaluated:.1%}（n={evaluated}） |")
    return lines


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline paired McNemar + paired bootstrap between two eval runs (scoring v1.2).")
    parser.add_argument("runs", nargs="*", help="two run ids (prefix of the timestamp is enough): A then B")
    parser.add_argument("--tag", help="restrict to cases carrying this tag")
    parser.add_argument("--paper", action="store_true", help="run every pair used in the paper and write the report")
    parser.add_argument("--out", type=Path, default=ROOT / "eval" / "reports" / "paper-paired-stats.md")
    parser.add_argument("--resamples", type=int, default=RESAMPLES)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.paper == bool(args.runs) or (args.runs and len(args.runs) != 2):
        parser.error("give exactly two run ids, or --paper")
    sessions = Sessions()
    loaded: dict[str, RunData] = {}

    def run(prefix: str) -> RunData:
        if prefix not in loaded:
            loaded[prefix] = load_run(prefix, sessions)
        return loaded[prefix]

    pairs = PAPER_PAIRS if args.paper else [("custom", args.runs[0], args.runs[1], args.tag, "")]
    results = []
    for label, a, b, tag, note in pairs:
        result = compare(label, run(a), run(b), tag, args.resamples, args.seed)
        results.append((result, note))
        print(f"{label}: n={result.n}", flush=True)
    if not args.paper:
        print("\n".join(HEADER + table_rows(results[0][0])))
        return 0
    lines = ["# 论文配对显著性检验（离线）", "",
             f"生成：`python -m scripts.eval.paired_stats --paper`（`scripts/eval/paired_stats.py`，仅标准库，不联网）。"
             f"自助法 {args.resamples} 次重采样，固定种子 {args.seed}，对子 (A,B) 同一组重采样索引。", "",
             f"**评分口径**：所有运行都用当前评分 v1.2 重算（{git_version()}）。逐条结果取自各运行的原始模型响应"
             "（`eval/runs/<id>/cases.jsonl`；该目录已不存在的运行，则按原运行的 backend/model/变体名和匹配到的 system prompt "
             "离线重放 `eval/cache`），再用当前的 `parse_plan`（含 existing 归一化）、当前 gold 标签（`eval/benchmark/intent_v2.jsonl`、"
             "`eval/candidates/intent_v2_scenario.jsonl`）和 `metrics.severity` 评分。因此本表的比例不同于论文各表中的 v1.1 数字，"
             "不能与它们混用；“原报告”列保留了原运行报告里的数字（当时的评分口径）以便核对。", "",
             "**指标**：S0+S1 = 严重度为 S0 或 S1 的条数 / 配对可评测条数；S3 = 严重度为 S3 的条数 / 配对可评测条数。"
             "b = 仅 A 达到该指标（A 记 1、B 记 0）的条数，c = 仅 B 达到的条数；McNemar 精确 p 为对 b+c 条不一致对做 p=0.5 的二项检验（双侧）。"
             "CI 为 B−A 的比例差（百分点）的配对自助法 95% 百分位区间。S3 的“事件”是出现 S3，所以 c>b 表示 B 的 S3 更多。", "",
             "## 结果", "", *HEADER]
    for result, _ in results:
        lines += table_rows(result)
    lines += ["", "## 对比说明与对齐情况", ""]
    for result, note in results:
        if note == "HEADLINE":
            old_a = result.a.report["metrics"]["s0_s1_rate"]
            old_b = result.b.report["metrics"]["s0_s1_rate"]
            a_new = sum(v in {"S0", "S1"} for v in result.a.severity.values())
            note = (f"论文头条的 {old_a:.1%}（pre_guard，v1.1 评分）和 {old_b:.1%}（最终 default，v1.2 评分）口径不同，不能配对；"
                    f"这里 A 取 008 的原始 pre_guard test 运行（离线重放，system prompt 为 PLAN_PROMPT_BASE），"
                    f"B 取 2026-10-13 的最终 default test 运行（offtopic 规则后，v1.2 之后实跑），两端都按 v1.2 重算。"
                    f"A 在 v1.2 下为 {a_new / len(result.a.severity):.1%}，即评分、标注与契约修订单独就带来 "
                    f"{old_a:.1%}→{a_new / len(result.a.severity):.1%}，其余才是三次提示词修改的贡献")
        lines.append(f"- {result.label}：A=`{result.a.run_id}`，B=`{result.b.run_id}`；n={result.n}"
                     + (f"；从两端剔除（任一端未评测）的用例：{', '.join(result.dropped)}" if result.dropped else "")
                     + (f"。{note}。" if note else "。"))
    lines += ["", "## 注意事项", "",
              "- p 值与 CI 未做多重比较校正；本表共 11 个对比、22 行，单个 p 接近 0.05 的结果不应单独当作显著证据。",
              "- 每个配置只采样一次（temperature 0.2），配对检验只覆盖“同一批用例上的差异”，不含采样随机性；不同运行之间的差异混有采样噪声。",
              "- E5（f 组）n=50，标签状态为 proposed，且 f4 是事后选取的子集（n=8），仅供参考。",
              "- E5 的 3 条原 InvalidPlan（existing 带多余字段）在 v1.2 归一化后可执行，其引擎裁定在当前剧本包上重算；"
              "严重度只由 plan、gold 和 harmful 决定（该集合每条都有 harmful），各运行 S4 均为 0。",
              "", "## 运行来源与回放核对", "", *run_table({r.a.run_id: r.a for r, _ in results} | {r.b.run_id: r.b for r, _ in results})]
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
