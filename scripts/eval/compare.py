from __future__ import annotations

import argparse
import json

from .run import display
from .snapshots import ROOT


def compare(reports: list[dict]) -> str:
    lines = ["拟定标签下的初步数字；n/a 表示没有可评测数据。", "",
             "| run | model | variant | responses/total | S0+S1 | S3 | InvalidPlan | conflict | existing.operation 清理/恢复 | exact | kind | injection no_state_change | p50 ms | p95 ms | input tokens | output tokens | cached tokens | cost/turn USD | 归一化次数 |",
             "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for report in reports:
        m = report["metrics"]
        tolerant = m.get("lenient", {})
        existing = (f"{tolerant.get('existing_operation_count', 0)}/{tolerant.get('existing_operation_recovered', 0)}"
                    if report.get("variant") == "lenient" else None)
        values = [report["run_id"], report.get("model"), report.get("variant"), f"{m['evaluated']}/{m['total']}",
                  m.get("s0_s1_rate"), m.get("s3_rate"), m.get("invalid_plan_rate"), m.get("conflict_rate"), existing,
                  m["exact"], m["kind"], m["injection"].get("no_state_change", m["injection"].get("immune")),
                  m["latency_ms"]["p50"], m["latency_ms"]["p95"],
                  *[m["tokens"][key]["mean"] for key in ("input_tokens", "output_tokens", "cached_tokens")],
                  f"{m['cost_per_turn']:.8f}" if m.get("cost_per_turn") is not None else None,
                  m.get("normalizations", 0)]
        lines.append("| " + " | ".join(display(value) for value in values) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_ids", nargs="+")
    args = parser.parse_args()
    reports = [json.loads((ROOT / "eval" / "reports" / f"{identifier}.json").read_text(encoding="utf-8")) for identifier in args.run_ids]
    print(compare(reports), end="")


if __name__ == "__main__":
    main()
