"""Gemini schema encodings: first 20 dev cases, optionally continue usable variants."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from host import state
from .requests import evaluation_config
from .run import run_evaluation
from .snapshots import ROOT
from .variants import SCHEMA_ENCODINGS


def usable(report: dict[str, Any]) -> bool:
    metrics = report["metrics"]
    return metrics["total"] == 20 and metrics["statuses"].get("ok", 0) == 20


def main(argv: list[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "eval/benchmark/intent_v2.jsonl")
    parser.add_argument("--model", default="gemini-3.1-flash-lite")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--full-dev", action="store_true", help="Run all dev cases only for encodings passing all 20 smoke cases.")
    parser.add_argument("--rpm", type=float)
    parser.add_argument("--timeout", type=int)
    args = parser.parse_args(argv)
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    if sum(case["split"] == "dev" for case in cases) < 20:
        parser.error("schema smoke requires at least 20 dev cases")
    try:
        config = evaluation_config(state.load_config(), "gemini", args.model, rpm=args.rpm, timeout=args.timeout)
    except ValueError as exc:
        parser.error(str(exc))
    summaries = []
    quota_stop = False
    for variant in SCHEMA_ENCODINGS:
        settings = argparse.Namespace(suite="intent", cases=args.cases, backend="gemini", model=args.model,
                                      variant=variant, split="dev", limit=20, live=args.live and not quota_stop,
                                      no_cache=False)
        report = run_evaluation(settings, config)
        quota_stop = quota_stop or bool(report["quota_exhausted"])
        passed = usable(report)
        summary = dict(variant=variant, usable=passed, smoke_run_id=report["run_id"],
                       statuses=report["metrics"]["statuses"], failures=report["response_failures"],
                       full_run_id=None, full_complete=None)
        failures = summary["failures"]
        print(f"{variant}: {'可用' if passed else '不可用'}；"
              f"空白输出={failures['whitespace']}，空对象={failures['empty_object']}，"
              f"其他={failures['other']}，无响应={failures['no_response']}；{report['run_id']}", flush=True)
        summaries.append(summary)
    # Complete all four smoke runs before spending the remaining quota on full dev.
    if args.full_dev:
        for summary in summaries:
            if not summary["usable"]:
                continue
            settings = argparse.Namespace(suite="intent", cases=args.cases, backend="gemini", model=args.model,
                                          variant=summary["variant"], split="dev", limit=None,
                                          live=args.live and not quota_stop, no_cache=False)
            report = run_evaluation(settings, config)
            quota_stop = quota_stop or bool(report["quota_exhausted"])
            summary["full_run_id"] = report["run_id"]
            summary["full_complete"] = report["metrics"]["evaluated"] == report["metrics"]["total"]
            print(f"{summary['variant']} dev: {report['run_id']}", flush=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S%fZ")
    path = ROOT / "eval/reports" / f"{stamp}-schema-smoke.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"model": args.model, "live": args.live, "quota_stopped": quota_stop,
                                "criterion": "20/20 status=ok; no semantic accuracy threshold",
                                "variants": summaries}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    return 0 if all(summary["usable"] and summary["full_complete"] is not False for summary in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
