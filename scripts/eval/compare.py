from __future__ import annotations

import argparse
import json

from .run import display
from .snapshots import ROOT


def compare(reports: list[dict]) -> str:
    lines = ["拟定标签下的初步数字；n/a 表示没有可评测数据。", "",
             "| run | responses/total | exact | kind | injection no_state_change | p50 ms | p95 ms | input tokens | output tokens | cached tokens | 归一化次数 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for report in reports:
        m = report["metrics"]
        values = [report["run_id"], f"{m['evaluated']}/{m['total']}", m["exact"], m["kind"], m["injection"].get("no_state_change", m["injection"].get("immune")),
                  m["latency_ms"]["p50"], m["latency_ms"]["p95"],
                  *[m["tokens"][key]["mean"] for key in ("input_tokens", "output_tokens", "cached_tokens")], m.get("normalizations", 0)]
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
