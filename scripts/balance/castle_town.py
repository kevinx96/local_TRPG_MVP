from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from host import state
from . import checkpoints, route

REPORTS = checkpoints.ROOT / "eval/reports"
OLD = REPORTS / "balance-2026-10-12-class-aware.json"
NEW = REPORTS / "balance-2026-10-13-castle-town.json"
CONTROL = REPORTS / "balance-2026-10-13-castle-town-control.json"


def control_job(job: tuple) -> dict[str, Any]:
    label, character, n, seed, rest, quests, decisions, dice = job
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    # Reproduce the old simulator's omission of the king's opening reward.
    castle = next(loc for loc in pack["locations"] if loc["id"] == "castle")
    castle["opening_effects"] = [{"gold_change": 50}]
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    row = route.simulate_route(pack, cp, character, n=n, seed=seed, rest_policy=rest,
                               quests=quests, decisions=decisions, dice=dice)
    row.pop("sample_trial", None)
    row["policy_label"] = label
    return row


def generate_control(workers: int) -> dict[str, Any]:
    current = json.loads(NEW.read_text(encoding="utf-8"))
    jobs = []
    for row in current["rows"]:
        label, character = row["policy_label"], row["character"]
        quests = tuple(current["quests"].get(character, ())) if label == "class_aware" else ()
        decisions = "class_aware" if label in {"class_aware", "class_aware_no_quests"} else "backbone"
        dice = "forced" if label in {"none", "hp70"} else "real"
        jobs.append((label, character, current["n"], current["seed"], row["rest_policy"], quests, decisions, dice))
    if workers == 1:
        rows = [control_job(job) for job in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(control_job, jobs))
    return {"n": current["n"], "seed": current["seed"], "quests": current["quests"],
            "control": "Current navigation with old simulator resources: 50G, no opening herb, holy water x2.",
            "fingerprints": current["fingerprints"], "rows": rows}


def write_report() -> None:
    old, new, control = [json.loads(path.read_text(encoding="utf-8")) for path in (OLD, NEW, CONTROL)]
    names = {"hero": "勇者", "cleric": "僧侶", "mage": "魔法使い", "thief": "盗賊"}
    lines = ["# 028 城下町平衡复跑", "",
        f"每个职业 / 策略 N={new['n']}，seed={new['seed']}；沿用上一份报告的 5 个策略和支线选择，不重新挑选支线。全部离线，没有模型调用。", "",
        "## 与上一份报告比较", "",
        "旧报告为 `balance-2026-10-12-class-aware.json`。表中百分比为连续主线通关率；差值为百分点。", "",
        "| 策略 | 职业 | 旧报告 | 本次 | 差值 | 旧资源口径对照 |", "|---|---|---:|---:|---:|---:|"]
    all_equal = True
    for previous, current, reference in zip(old["rows"], new["rows"], control["rows"]):
        assert (previous["policy_label"], previous["character"]) == (current["policy_label"], current["character"])
        before, after, matched = [row["completion_rate"] * 100 for row in (previous, current, reference)]
        all_equal &= previous == reference
        lines.append(f"| {current['policy_label']} | {names[current['character']]} | {before:.1f}% | {after:.1f}% | {after-before:+.1f} | {matched:.1f}% |")
    rate_equal = all(a["completion_rate"] == b["completion_rate"] for a, b in zip(old["rows"], control["rows"]))
    lines += ["", "## 变化来源", "",
        "spec 的实际游戏资源总额保持 100G：原设计为国王 50G + check_supplies 50G，本次为国王 100G + check_supplies 0G；薬草和聖水总量没有改动。",
        "旧模拟只从 0G 角色模板执行 check_supplies，漏掉了国王的 50G 和开场薬草，实际以 50G 开始。本次 checkpoint 显式重放 @opening，修正为 100G + 开场薬草，再领取聖水×2。额外药品、可支付宿泊次数和 class_aware 基于可见资源状态的估值种子可能改变路线选择，因此主报告不能直接当作纯导航 A/B。",
        "对照组仅在内存中把开场奖励设为 50G、去掉开场薬草，保留本次城下町导航、所有战斗数值及其它变更；从而复现旧模拟的资源口径，未修改提交的剧本。",
        f"对照结果：20 组通关率{'全部与旧报告一致' if rate_equal else '未全部与旧报告一致，需结合原始 JSON 检查差异'}；全部聚合指标{'也逐项一致' if all_equal else '并非逐项一致（含休息、到达资源和消耗统计），详见 JSON'}。",
        "N=500 时单组通关率的抽样误差仍为数个百分点；这些小幅差值不支持平衡目标变化的结论。没有调整 DC、战斗参数、价格或成长值。", "",
        "## 复现", "", "```powershell",
        "python -m scripts.balance.checkpoints",
        "python -m scripts.balance.class_aware --n 500 --seed 20261012 --workers 20 --output eval/reports/balance-2026-10-13-castle-town.json",
        "python -m scripts.balance.castle_town --workers 20",
        "```", "",
        "第三条命令生成旧资源对照 JSON 和本文；`--report-only` 只根据现有 JSON 重建 Markdown。输入 SHA-256 见两个本次 JSON 的 fingerprints。",
        "尚未解决的上游模拟限制：战斗采用既有 heuristic 策略，路线判定沿用各配置 forced / real 规则；本次没有重新验证 027 的策略最优性。", ""]
    (REPORTS / "balance-2026-10-13-castle-town.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="028 offline navigation/resource control")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if not args.report_only:
        CONTROL.write_text(json.dumps(generate_control(args.workers), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report()


if __name__ == "__main__":
    main()
