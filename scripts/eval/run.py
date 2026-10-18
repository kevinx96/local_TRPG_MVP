from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

from host import app, combat, free_actions, gm_contract, item_mechanics, llm_client, state
from host.llm_trace import prompt_metadata
from .cache import cache_key, read_cache, write_cache
from .metrics import summarize
from .requests import QuotaExhausted, evaluation_config
from .audit import allowed_state, costly_plan
from .snapshots import ROOT, isolated_engine, load_snapshot
from .variants import VARIANTS, clean_lenient


def protected_state(session: dict[str, Any]) -> dict[str, Any]:
    actor = session["character"]
    return deepcopy({"position": session["world_state"], "flags": session["flags"],
                     "items": actor["inventory"],
                     "resources": {k: v for k, v in actor.items() if k not in {"inventory", "name", "description"}}})


def engine_result(session: dict[str, Any], plan: dict[str, Any], text: str) -> dict[str, Any]:
    trial = deepcopy(session)
    before = protected_state(trial)
    with isolated_engine("adjudication"), patch.object(app, "load_config", return_value={"debug_llm": False, "trace_llm": False}), \
         patch.object(app, "chat_completion", side_effect=AssertionError("Evaluation adjudication must not call an LLM")):
        if plan["kind"] == "existing":
            resolution = state.resolve_player_intent(trial, action_id=plan["action_id"])
            if resolution.get("status") != "resolved":
                raise free_actions.InvalidPlan("unavailable action")
            app._run_turn(trial, app.TurnRequest(text=text, action_id=plan["action_id"]), allow_narration=False)
            result = trial.get("last_action_result") or {"outcome": "rejected"}
        else:
            result = free_actions.adjudicate(trial, plan)
        authorized = protected_state(allowed_state(session, plan, result))
    after = protected_state(trial)
    action = trial.get("last_action_result") or {}
    return {"outcome": result.get("outcome"), "result": result,
            "changes": {k: before[k] != after[k] for k in before},
            "before": before, "after": after, "allowed_after": authorized,
            "attack_or_combat": bool(combat.combat_is_active(trial) or trial.get("combat_start_requested")
                                     or action.get("state_delta", {}).get("start_combat"))}


def evaluate_case(case: dict[str, Any], session: dict[str, Any], config: dict[str, Any],
                  backend: str, model: str, variant: str, cache_dir: Path, *, live: bool = False,
                  no_cache: bool = False) -> dict[str, Any]:
    if VARIANTS[variant].gemini_only and backend != "gemini":
        raise ValueError(f"{variant} is only available for Gemini evaluation")
    messages, request_config = VARIANTS[variant].prepare(session, case["input"], config)
    if "eval_timeout_seconds" in config:
        request_config["request_timeout_seconds"] = config["eval_timeout_seconds"]
        request_config["gameplay_timeout_seconds"] = config["eval_timeout_seconds"]
    key = cache_key(backend, model, variant, messages, request_config)
    record = {**deepcopy(case), "status": "skipped", "cache_key": key, "cache_hit": False,
              **prompt_metadata(messages), "latency_ms": None, "usage": {}, "raw_response": None,
              "plan": None, "invalid_plan_reason": None, "engine": None,
              "structured_output": "openai_json_schema" if backend == "ollama" else "gemini_responseJsonSchema"}
    cached = None if no_cache else read_cache(cache_dir, key)
    if cached is not None:
        record.update({k: cached[k] for k in ("raw_response", "usage", "latency_ms", "structured_output", "http_errors") if k in cached})
        record["cache_hit"] = True
    elif not live or VARIANTS[variant].replay_only:
        record["skip_reason"] = ("default_cache_required" if VARIANTS[variant].replay_only else
                                 "cache_miss" if not no_cache else "cache_disabled")
        return record
    else:
        usage: dict[str, Any] = {}
        started = time.monotonic()
        policy = request_config.get("_request_policy")
        error_start = len(policy.http_errors) if policy is not None else 0
        try:
            if backend == "ollama" and policy is not None and not policy.warmed:
                llm_client.chat_completion(request_config, messages)
                policy.warmed = True
                started = time.monotonic()
            raw = llm_client.chat_completion(request_config, messages, usage_out=usage)
        except llm_client.LLMClientError as exc:
            record.update(status="quota_exhausted" if isinstance(exc, QuotaExhausted) else
                          "blocked" if isinstance(exc, llm_client.LLMBlockedError) else "request_error",
                          error_type=type(exc).__name__, error=app._redact_secrets(str(exc)), usage=usage,
                          latency_ms=round((time.monotonic() - started) * 1000, 3))
            if isinstance(exc, QuotaExhausted):
                record["quota"] = exc.details
            return record
        finally:
            if policy is not None:
                record["http_errors"] = [{"status_code": e["status_code"],
                                          "body": app._redact_secrets(str(e["body"]))}
                                         for e in policy.http_errors[error_start:]]
        record.update(raw_response=raw, usage=usage, latency_ms=round((time.monotonic() - started) * 1000, 3),
                      structured_output=usage.get("transport", record["structured_output"]))
        if not no_cache:
            write_cache(cache_dir, key, {k: record[k] for k in ("raw_response", "usage", "latency_ms", "structured_output", "http_errors") if k in record})
    cleaned = gm_contract._strip_thinking_text(record["raw_response"]).strip()
    record["thinking_stripped"] = cleaned != record["raw_response"].strip()
    if VARIANTS[variant].prompt_suffix:
        baseline_messages, baseline_config = VARIANTS["default"].prepare(session, case["input"], config)
        baseline = read_cache(cache_dir, cache_key(backend, model, "default", baseline_messages, baseline_config))
        current_tokens = record["usage"].get("input_tokens")
        baseline_tokens = (baseline or {}).get("usage", {}).get("input_tokens")
        record["prompt_delta"] = {
            "chars": len(VARIANTS[variant].prompt_suffix),
            "input_tokens": current_tokens - baseline_tokens
            if current_tokens is not None and baseline_tokens is not None else None}
    if variant == "lenient":
        cleaned, record["lenient"] = clean_lenient(cleaned)
    try:
        cleaned = VARIANTS[variant].unwrap(cleaned)
        plan = free_actions.parse_plan(cleaned, session.get("character", {}).get("character_id", ""))
        record["plan"] = plan
        record["costs"] = {"plan": costly_plan(session, plan),
                           "gold": [costly_plan(session, g) for g in case["gold"]]}
        record["engine"] = engine_result(session, plan, case["input"])
        record["status"] = "ok"
    except free_actions.InvalidPlan as exc:
        record["status"] = "json_error" if str(exc) == "invalid JSON" else "invalid_plan"
        record["invalid_plan_reason"] = str(exc)
        record["engine"] = {"outcome": "rejected", "attack_or_combat": False,
                            "changes": {k: False for k in protected_state(session)}}
    return record


def response_failures(records: list[dict[str, Any]], variant: str) -> dict[str, int]:
    counts = dict(whitespace=0, empty_object=0, other=0, no_response=0)
    for record in records:
        if record["status"] == "ok":
            continue
        raw = record.get("raw_response")
        if raw is None:
            counts["no_response"] += 1
            continue
        cleaned = gm_contract._strip_thinking_text(raw).strip()
        # Includes the observed failure: an opening brace followed only by whitespace.
        if cleaned in {"", "{"} or (variant == "union_wrapped" and re.fullmatch(r'\{\s*"plan"\s*:\s*\{', cleaned)):
            counts["whitespace"] += 1
            continue
        try:
            value = json.loads(cleaned)
        except ValueError:
            value = None
        empty = value == {} or variant == "union_wrapped" and value == {"plan": {}}
        counts["empty_object" if empty else "other"] += 1
    return counts


def display(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def report_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = ["# 拟定标签下的初步数字", "", f"Run: `{report['run_id']}`", "",
             "候选标签尚未审定。无模型响应时指标为 n/a；skipped、连接错误与拦截不进入意图准确率分母。",
             "缓存重放的延迟和 token 来自原始调用。所有引擎判定骰固定为 10（不超过骰面上限）。", "",
             f"总数 {metrics['total']}；可评测响应 {metrics['evaluated']}；状态 `{json.dumps(metrics['statuses'])}`。", "",
             "| 指标 | 值 |", "|---|---|"]
    for key in ("exact", "kind", "kind_relaxed", "s0_s1_rate", "s3_rate", "engine_caught",
                "severity", "json_failure_rate", "invalid_plan_rate", "conflict_count", "conflict_rate",
                "cost_per_turn", "cost_currency", "cost_reported"):
        value = metrics.get(key)
        rendered = f"{value:.8f}" if key == "cost_per_turn" and value is not None else display(value)
        lines.append(f"| {key} | {rendered} |")
    for key, value in metrics["latency_ms"].items():
        lines.append(f"| latency_ms {key} | {display(value)} |")
    for key, value in metrics["tokens"].items():
        lines.append(f"| {key} mean ({value['reported']} reported) | {display(value['mean'])} |")
    for tag in ("negation", "injection", "declared_success"):
        lines.append(f"| {tag} | {json.dumps(metrics[tag])} |")
    lines.append(f"| 归一化次数 | {metrics['normalizations']} |")
    lines.append(f"| lenient 清理与 existing.operation | {json.dumps(metrics.get('lenient', {}))} |")
    if report.get("prompt_delta"):
        delta = report["prompt_delta"]
        lines += [f"| 相对 default 追加字符 | {delta['chars']} |",
                  f"| 相对 default input token 增量（匹配缓存均值，{delta['matched']} 对） | {display(delta['input_tokens_mean'])} |"]
    if report.get("response_failures"):
        lines.append(f"| 失败形态 | {json.dumps(report['response_failures'])} |")
    if report.get("quota_exhausted"):
        quota = report["quota_exhausted"]
        wait = quota["retry_after_seconds"]
        lines += ["", f"quota_exhausted：停在第 {quota['case_index']} 条（`{quota['id']}`）；"
                  f"需要等待 {str(wait) + ' 秒' if wait is not None else '未知（API 未提供 retryDelay）'}。"
                  "后续只读取已有缓存，不再发起 live 请求。"]
    lines += ["", "## 标签分组", "", "| 标签 | 数量 | exact | kind | relaxed | 归一化次数 | S3 | engine_caught |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for tag, values in metrics["by_tag"].items():
        lines.append(f"| {tag} | {values['count']} | {display(values['exact'])} | {display(values['kind'])} | {display(values['kind_relaxed'])} | {values['normalizations']} | {display(values.get('s3_count'))} | {display(values.get('engine_caught'))} |")
    lines += ["", "## 错误最多的三类与样例", ""]
    if not metrics["top_errors"]:
        lines.append("n/a：没有可评测响应，不能给出模型错误排行或典型错例。")
    for group in metrics["top_errors"]:
        lines += [f"### {group['tag']} ({group['errors']})", "", "```json", json.dumps(group["examples"], ensure_ascii=False, indent=2), "```", ""]
    if report["errors"]:
        lines += ["", "## 调用失败", "", "```json", json.dumps(report["errors"], ensure_ascii=False, indent=2), "```"]
    lines += ["", "完整字段准确率、混淆矩阵、clarify、缓存用量和配置指纹见同名 JSON。", ""]
    return "\n".join(lines)


def main(argv: list[str] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline-first intent evaluation; --live explicitly permits model requests.")
    parser.add_argument("--suite", choices=["intent"], required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--backend", choices=["gemini", "ollama"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--variant", choices=list(VARIANTS), default="default")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="all")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--rpm", type=float, help="Requests per minute; 0 disables pacing")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--base-url")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if VARIANTS[args.variant].gemini_only and args.backend != "gemini":
        parser.error(f"{args.variant} is only available for Gemini evaluation")
    try:
        config = evaluation_config(state.load_config(), args.backend, args.model,
                                   rpm=args.rpm, timeout=args.timeout, base_url=args.base_url)
    except ValueError as exc:
        parser.error(str(exc))
    report = run_evaluation(args, config)
    print(report["run_id"])
    return 1 if any(error["status"] in {"request_error", "quota_exhausted"} for error in report["errors"]) else 0


def run_evaluation(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    # The frozen benchmark was cached with raw element ids in item effects; keep them for replay.
    frozen = (ROOT / "eval" / "benchmark") in args.cases.resolve().parents
    with patch.object(item_mechanics, "LEGACY_ELEMENT_IDS", frozen):
        return _run_evaluation(args, config)


def _run_evaluation(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    case_bytes = args.cases.read_bytes()
    cases = [json.loads(line) for line in case_bytes.decode("utf-8").splitlines() if line.strip()]
    cases = [case for case in cases if args.split == "all" or case["split"] == args.split]
    if args.limit:
        cases = cases[:args.limit]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S%fZ")
    run_id = re.sub(r"[^A-Za-z0-9_.-]", "_", f"{stamp}-{args.suite}-{args.backend}-{args.model}-{args.variant}")
    directory = ROOT / "eval" / "runs" / run_id
    directory.mkdir(parents=True)
    sessions: dict[str, Any] = {}
    records = []
    failed = False
    quota_stop = None
    with (directory / "cases.jsonl").open("w", encoding="utf-8") as output:
        for case in cases:
            if case["snapshot"] not in sessions:
                sessions[case["snapshot"]] = load_snapshot(case["snapshot"])
            record = evaluate_case(case, sessions[case["snapshot"]], config, args.backend, args.model, args.variant,
                                   ROOT / "eval" / "cache", live=args.live and not failed, no_cache=args.no_cache)
            if failed and record["status"] == "skipped":
                record["skip_reason"] = "quota_exhausted" if quota_stop else "backend_unavailable_after_request_error"
            if record["status"] in {"request_error", "quota_exhausted"}:
                failed = True
            if record["status"] == "quota_exhausted":
                quota_stop = {"case_index": len(records) + 1, "id": case["id"], **record["quota"]}
            records.append(record)
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            output.flush()
            if len(records) % 25 == 0 or record["status"] in {"request_error", "quota_exhausted"}:
                print(f"{len(records)}/{len(cases)} {record['status']}", flush=True)
    prices = json.loads((ROOT / "eval" / "prices.json").read_text(encoding="utf-8"))
    report = {"run_id": run_id, "backend": args.backend, "model": args.model, "variant": args.variant,
              "split": args.split, "live": args.live, "labels": "proposed", "cases": str(args.cases),
              "cases_sha256": hashlib.sha256(case_bytes).hexdigest(),
              "quota_exhausted": quota_stop,
              "response_failures": response_failures(records, args.variant),
              "metrics": summarize(records, prices.get("models", {}).get(args.model)),
              "errors": [{k: r.get(k) for k in ("id", "status", "error_type", "error", "http_errors", "quota")}
                         for r in records if r["status"] in {"request_error", "blocked", "quota_exhausted"}]}
    if VARIANTS[args.variant].prompt_suffix:
        deltas = [r["prompt_delta"]["input_tokens"] for r in records
                  if r.get("prompt_delta", {}).get("input_tokens") is not None]
        report["prompt_delta"] = {"chars": len(VARIANTS[args.variant].prompt_suffix), "matched": len(deltas),
                                  "input_tokens_mean": sum(deltas) / len(deltas) if deltas else None}
    report_dir = ROOT / "eval" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"{run_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (report_dir / f"{run_id}.md").write_text(report_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    raise SystemExit(main())
