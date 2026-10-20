from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from host import state
from . import sim
from .checkpoints import DEFAULT_CHECKPOINTS, DEFAULT_SCENARIO, ROOT, proposed_routes


def run_job(job: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    pack = state.load_scenario_pack(Path(job["scenario"]))
    checkpoints = json.loads(Path(job["checkpoint"]).read_text(encoding="utf-8"))
    common = dict(n=job["n"], seed=job["seed"], checkpoints=checkpoints, defense_mode=job["mode"])
    rows = []
    if job["kind"] == "matrix":
        for policy in (sim.LEGACY_POLICIES if job["mode"] == "flat" else ["heuristic"]):
            rows.append({"experiment": "matrix", **sim.simulate(pack, job["encounter"], job["character"], policy, **common)})
        if job["mode"] == "flat":
            rows.append({"experiment": "without_companion", **sim.simulate(pack, job["encounter"], job["character"],
                                                                         companion=False, **common)})
    else:
        actor = next(c for c in pack["characters"] if c["id"] == job["character"])
        found = None
        for hp_step in range(9):
            for attr in range(7):
                scaling = {"hp_mult": 1 + hp_step * .25, "attr_add": {k: attr for k in actor["attributes"]}, "skill_unlocks": []}
                result = sim.simulate(pack, job["encounter"], job["character"], stat_scaling=scaling, **common)
                result.update(experiment="scaling", hp_mult=scaling["hp_mult"], attr_add=attr)
                rows.append(result)
                if job["target"][0] <= result["win_rate"] <= job["target"][1]:
                    found = result
                    break
            if found is not None:
                break
        return {"job": job, "rows": rows, "minimum": found, "elapsed_seconds": time.perf_counter() - started}
    return {"job": job, "rows": rows, "elapsed_seconds": time.perf_counter() - started}


def f(value: Any) -> str:
    return "n/a" if value is None else f"{value:.3f}" if isinstance(value, float) else str(value)


def markdown(results: list[dict[str, Any]], metadata: dict[str, Any], targets: dict[str, Any], checkpoints: dict[str, Any]) -> str:
    rows = [row for result in results for row in result["rows"]]
    matrix = [r for r in rows if r["experiment"] == "matrix"]
    flat = [r for r in matrix if r["defense_mode"] == "flat"]
    lines = ["# 战斗数值模拟报告", "", "全部为离线真实引擎结算；checkpoint 尚待设计审定。", "",
             f"N={metadata['n']} / cell；seed={metadata['seed']}；进程数={metadata['workers']}；完整执行墙钟 {metadata['elapsed_seconds']:.2f} 秒。",
             f"矩阵/同伴实验累计 worker 时间 {metadata['matrix_worker_seconds']:.2f} 秒；缩放搜索累计 worker 时间 {metadata['search_worker_seconds']:.2f} 秒。",
             f"总计 {len(rows)} 个 cell、{sum(r['n'] for r in rows):,} 场战斗。指纹 `{metadata['fingerprint']}`。", "",
             "复现：`python -m scripts.balance.checkpoints`，然后 `python -m scripts.balance.report --n 500 --seed 20261011 --workers 8`。",
             "同名 CSV 包含完整矩阵、消耗、战败分布、同伴对照及所有已测试的缩放网格点。运行缓存带输入/代码指纹，可中断后续跑。", "",
             "每场独立开始且 HP/MP/SP 回满。先前战斗只推导奖励，不扣估计消耗；这不是连续闯关模拟。",
             "期望伤害以骰子均值、整数属性项、命中率、抗性和防御公式估计；不读取 RNG，不预测敌人下一招。",
             "策略仅选择 combat_actions 返回的 enabled 动作；并列按可见动作/敌人顺序。多目标攻击计全部活敌，负 HP 不死者仅圣/光伤害为正收益。",
             "heuristic 在 HP<35% 时优先最大可见回复，boss 标志的前两回合用首个可用护盾/姿态；其余 greedy。",
             "可见动作未提供的持续伤害、缩小等不纳入贪心评分；不试算战斗。MP/SP 统计实际支付总量，不以战后净差代替（SP 可回复）。",
             "胜率统计普通胜利；scripted_loss 的剧情继续仍计战敗；HP 是奖励/败北恢复前的 HP；无胜利时 hp_left 为 n/a。", "",
             "## 1. flat 现状矩阵", "", "| 遭遇 | 职业 | 策略 | 胜率 | 回合中位数 | 胜利剩余HP | 回复道具均值 | MP消耗 | SP消耗 |",
             "|---|---|---|---:|---:|---:|---|---:|---:|"]
    for r in flat:
        lines.append("| " + " | ".join(f(r[k]) if k != "healing_items_mean" else json.dumps(r[k], ensure_ascii=False)
                                      for k in ("encounter", "character", "policy", "win_rate", "rounds_median", "hp_left_mean", "healing_items_mean", "mp_spent_mean", "sp_spent_mean")) + " |")
    lines += ["", "### 达标计数", "", "严格达标要求该遭遇全部职业满足胜率、HP、回合、职业差距和 boss 普攻上限；仅胜率计数单列，避免把强度与节奏混为一谈。", "",
              "| 类别 | 遭遇数 | 全指标达标 | 全指标越界 | 全职业胜率达标 | 胜率越界 |", "|---|---:|---:|---:|---:|---:|"]
    violations = sim.check_results(flat, targets)
    bad = {v["encounter"] for v in violations}
    bad_win = {v["encounter"] for v in violations if v["metric"] == "win_rate"}
    for cls in targets["classes"]:
        names = {e for e, c in targets["encounters"].items() if c == cls}
        lines.append(f"| {cls} | {len(names)} | {len(names - bad)} | {len(names & bad)} | {len(names - bad_win)} | {len(names & bad_win)} |")
    lines += ["", "## 2. floor / ratio（heuristic）", "", "| 公式 | 遭遇 | 职业 | 胜率 | 回合中位数 | 胜利剩余HP |", "|---|---|---|---:|---:|---:|"]
    for r in matrix:
        if r["defense_mode"] != "flat":
            lines.append("| " + " | ".join(f(r[k]) for k in ("defense_mode", "encounter", "character", "win_rate", "rounds_median", "hp_left_mean")) + " |")
    lines += ["", "### 公式与目标的距离", "", "为公平比较，下表三个公式均仅比较 heuristic 的胜率/HP/回合与职业差距；floor/ratio 未运行普攻，不声称通过 boss 普攻限制。",
              "胜率区间距离为每职业到闭区间最近端点的绝对距离，再取平均；越大越偏离。", "",
              "| 公式 | heuristic 全指标达标遭遇 | 胜率达标 cell | 胜率过低/过高 | 平均胜率区间距离 |", "|---|---:|---:|---|---:|"]
    distances = {}
    for mode in sim.MODES:
        selected = [r for r in matrix if r["defense_mode"] == mode and r["policy"] == "heuristic"]
        low = high = 0
        distance = 0.0
        for r in selected:
            lo, hi = targets["classes"][r["encounter_class"]]["win_rate"]
            low += r["win_rate"] < lo
            high += r["win_rate"] > hi
            distance += max(lo - r["win_rate"], r["win_rate"] - hi, 0)
        distances[mode] = distance / len(selected)
        bad_mode = {v["encounter"] for v in sim.check_results(selected, targets)}
        lines.append(f"| {mode} | {len(targets['encounters']) - len(bad_mode)} | {len(selected)-low-high}/{len(selected)} | {low}/{high} | {distance/len(selected):.4f} |")
    best_distance = min(distances.values())
    best = " / ".join(mode for mode, value in distances.items() if abs(value - best_distance) < 1e-12)
    lines += ["", f"按预先声明的胜率区间距离，最接近的是 **{best}**；这是测量排序，不是默认公式变更建议。",
              "三种公式同时作用于敌我双方，减少防御收益也可能让玩家更快死亡。具体偏易、偏难与职业差距见上表和完整 CSV；不能只看某一职业获益。", "",
              "## 3. 缩放网格搜索", "", "每个 elite/boss、每职业、每公式独立搜索，N 与矩阵相同；hp_mult=1..3 步长0.25，全部既有属性统一+0..6，不解锁技能。",
              "最小定义为字典序：先最小 hp_mult，再最小 attr_add；找到第一个落在**胜率**区间的点即停止，否则穷尽63点。未假定胜率随属性单调。",
              "搜索命中并不表示 HP/回合/职业差距等其他目标通过；区间边缘有 Monte Carlo 误差（N=500 时胜率标准误最大约0.022）。", "",
              "| 遭遇 | 职业 | 公式 | 最小HP倍率 | 属性统一增加 | 胜率 | 已测点数 |", "|---|---|---|---:|---:|---:|---:|"]
    searches = [r for r in results if r["job"]["kind"] == "search"]
    order = {key: index for index, key in enumerate(proposed_routes())}
    searches.sort(key=lambda r: (order[r["job"]["encounter"]], r["job"]["character"], r["job"]["mode"]))
    for result in searches:
        job, minimum = result["job"], result["minimum"]
        lines.append(f"| {job['encounter']} | {job['character']} | {job['mode']} | {f(minimum['hp_mult']) if minimum else '无解'} | {f(minimum['attr_add']) if minimum else 'n/a'} | {f(minimum['win_rate']) if minimum else 'n/a'} | {len(result['rows'])} |")
    missing = Counter(r["job"]["encounter"] for r in searches if r["minimum"] is None)
    lines += ["", "网格内无解的职业×公式数量：" + "；".join(f"{k}={v}" for k, v in missing.items()) + "。",
              "剧情存在并行支线，不能把表格顺序当作唯一升级时间轴。下列相邻主线与砦路径检查仅判断各点的最小解能否直接组成非递减曲线；未搜索所有可行点，不能证明不存在另一条曲线。"]
    chain = ["forest_wolves", "village_fire_elemental", "ice_elemental_encounter", "frost_wolf_battle", "dragon_valley_loc"]
    adjacent = [*zip(chain, chain[1:]), ("goblin_fort_third_guards", "goblin_fort_fourth")]
    minima = {(r["job"]["encounter"], r["job"]["character"], r["job"]["mode"]): r["minimum"] for r in searches}
    inversions = []
    for character in ("hero", "cleric", "mage", "thief"):
        for mode in sim.MODES:
            for earlier, later in adjacent:
                a, b = minima.get((earlier, character, mode)), minima.get((later, character, mode))
                if a and b and (b["hp_mult"] < a["hp_mult"] or b["attr_add"] < a["attr_add"]):
                    inversions.append(f"{character}/{mode}: {earlier}({a['hp_mult']},+{a['attr_add']}) → {later}({b['hp_mult']},+{b['attr_add']})")
    lines += ["", "最小解回落：" + ("；".join(inversions) if inversions else "已找到的相邻最小解未发现回落；无解点仍阻止完整拟合。"),
              "TODO(design): 审定 checkpoint、剧情分支和成长里程碑后再定曲线；商人负HP机制、砦多敌集火、同伴离队均应分开看待。", "",
              "## 4. 职业差距", "", "各公式均比较 heuristic；`!` 表示 >0.15。", "",
              "| 遭遇 | flat | floor | ratio |", "|---|---:|---:|---:|"]
    for encounter in targets["encounters"]:
        values = []
        for mode in sim.MODES:
            rates = [r["win_rate"] for r in matrix if r["encounter"] == encounter and r["defense_mode"] == mode and r["policy"] == "heuristic"]
            spread = max(rates) - min(rates)
            values.append(f"{spread:.3f}" + (" !" if spread > targets["class_spread_max"] + 1e-12 else ""))
        lines.append(f"| {encounter} | " + " | ".join(values) + " |")
    lines += ["", "## 5. flat 最弱职业与战败原因", "", "以下按 heuristic；并列最差全部列出。原因是引擎最后造成致死的攻击/领域/反噬或回合上限，次数及完整战败回合分布见 CSV。", "",
              "| 遭遇 | 最弱职业 | 胜率 | 最常见战败原因及回合 |", "|---|---|---:|---|"]
    for encounter in targets["encounters"]:
        group = [r for r in flat if r["encounter"] == encounter and r["policy"] == "heuristic"]
        worst_rate = min(r["win_rate"] for r in group)
        for r in group:
            if r["win_rate"] == worst_rate:
                cause = next(iter(r["defeat_causes"].items()), ("无战败", 0))
                lines.append(f"| {encounter} | {r['character']} | {r['win_rate']:.3f} | {cause[0]} ({cause[1]}) |")
    lines += ["", "## 同伴对照（flat / heuristic，相同种子）", "", "无同伴组只移除当前 checkpoint 同伴；村庄后已剧情离队，因此差为0。guest 自带 disable_companion。", "",
              "| 遭遇 | 职业 | 有同伴 | 无同伴 | 胜率差 |", "|---|---|---:|---:|---:|"]
    without = {(r["encounter"], r["character"]): r for r in rows if r["experiment"] == "without_companion"}
    for r in flat:
        if r["policy"] == "heuristic":
            other = without[r["encounter"], r["character"]]
            lines.append(f"| {r['encounter']} | {r['character']} | {r['win_rate']:.3f} | {other['win_rate']:.3f} | {r['win_rate']-other['win_rate']:.3f} |")
    lines += ["", "## checkpoint 假设及待审定项", "", *[f"- {note}" for note in checkpoints["notes"]], "",
              "各遭遇、各职业的确切背包、装备、金币、同伴及来源 action/combat delta 见 `eval/balance/checkpoints.json`。",
              "商人战 checkpoint 已拿诅咒装备但未付代价；最终龙战已接受イアン请求。没有提前发放当前战斗奖励，没有修改敌人/技能/剧本数值。", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINTS)
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261011)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/balance-2026-10-11")
    args = parser.parse_args()
    inputs = [args.scenario, args.checkpoint, sim.TARGETS, *Path(__file__).parent.glob("*.py"),
              ROOT / "host/combat.py", ROOT / "host/state.py", ROOT / "host/item_mechanics.py"]
    digest = hashlib.sha256()
    for path in sorted(inputs):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    digest.update(f"{args.n}:{args.seed}".encode())
    fingerprint = digest.hexdigest()
    cache = ROOT / ".tmp-test/balance-runs" / fingerprint
    cache.mkdir(parents=True, exist_ok=True)
    pack = state.load_scenario_pack(args.scenario)
    checkpoints = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    jobs = []
    for encounter, cls in targets["encounters"].items():
        for character in sim.selected_characters(pack, encounter, ["all"]):
            for mode in sim.MODES:
                for kind in (["matrix", "search"] if cls in {"elite", "boss"} else ["matrix"]):
                    jobs.append(dict(kind=kind, encounter=encounter, character=character, mode=mode,
                                     target=targets["classes"][cls]["win_rate"], n=args.n, seed=args.seed,
                                     scenario=str(args.scenario), checkpoint=str(args.checkpoint)))
    results = []
    pending = []
    for index, job in enumerate(jobs):
        path = cache / f"{index}.json"
        if path.exists():
            results.append(json.loads(path.read_text(encoding="utf-8")))
        else:
            pending.append((index, job))
    started = time.perf_counter()
    print(f"{len(jobs)} jobs, {len(results)} cached, N={args.n}, workers={args.workers}", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_job, job): index for index, job in pending}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            (cache / f"{futures[future]}.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            job = result["job"]
            print(f"{len(results)}/{len(jobs)} {job['kind']} {job['encounter']} {job['character']} {job['mode']} {result['elapsed_seconds']:.1f}s", flush=True)
    elapsed = time.perf_counter() - started
    results.sort(key=lambda r: (r["job"]["encounter"], r["job"]["character"], r["job"]["mode"], r["job"]["kind"]))
    metadata = {"n": args.n, "seed": args.seed, "workers": args.workers, "elapsed_seconds": elapsed,
                "fingerprint": fingerprint, "cached_jobs": len(jobs) - len(pending),
                "matrix_worker_seconds": sum(r["elapsed_seconds"] for r in results if r["job"]["kind"] == "matrix"),
                "search_worker_seconds": sum(r["elapsed_seconds"] for r in results if r["job"]["kind"] == "search")}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(results, metadata, targets, checkpoints), encoding="utf-8")
    rows = [{**row, "hp_mult": row.get("hp_mult", 1.0), "attr_add": row.get("attr_add", 0)} for result in results for row in result["rows"]]
    fields = list(rows[0])
    with args.output.with_suffix(".csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, dict) else value for key, value in row.items()})
    print(f"Report saved: {args.output}; wall={elapsed:.2f}s", flush=True)


if __name__ == "__main__":
    main()
