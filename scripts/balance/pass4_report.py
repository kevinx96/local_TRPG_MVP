from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from . import checkpoints, route, sim
from .pass3_report import changes, dump, fmt

ROOT = checkpoints.ROOT
REPORT = ROOT / "eval/reports/balance-2026-10-11-pass4"


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    result = read(REPORT.with_suffix(".json"))
    routes = read(REPORT.with_name(REPORT.name + "-routes.json"))
    previous = read(ROOT / "eval/reports/balance-2026-10-11-pass3.json")
    old_routes = read(ROOT / "eval/reports/balance-2026-10-11-pass3-routes.json")
    search = read(ROOT / "eval/balance/pass4-search.json")
    targets = read(sim.TARGETS)
    rows = [r for r in result["rows"] if r["companion"]]
    old_rows = [r for r in previous["rows"] if r["companion"]]
    bad = sim.check_results(rows, targets)
    old_bad = sim.check_results(old_rows, targets)
    route_bad = route.check_results(routes["rows"], targets)
    old_by_route = {(r["route"], r["character"]): r for r in old_routes["rows"]}
    old_by_cell = {(r["encounter"], r["character"], r["policy"]): r for r in old_rows}
    base = search["baseline_commit"]
    raw = read(checkpoints.DEFAULT_SCENARIO)
    original = json.loads(subprocess.check_output(
        ["git", "show", base + ":host/prompt/processed/dragon_rpg.json"], cwd=ROOT).decode("utf-8"))
    delta = changes(original, raw)
    result.update(route_violations=route_bad, violations_after=bad, check_exit_code=int(bool(bad)),
                  comparison=dict(pass3_hard_violations=len(old_bad), pass4_hard_violations=len(bad)), changes=delta)
    lines = ["# 数值第四轮：连续流程优先", "",
             f"**route_targets：{8 - sum(v['metric'] == 'completion_rate' for v in route_bad)}/8 个职业通关率达标；"
             f"{2 - sum(v['metric'] == 'class_spread' for v in route_bad)}/2 条路线职业差距达标。**",
             f"**单场硬指标：pass3 {len(old_bad)} 项越界 → pass4 {len(bad)} 项越界。"
             "存在越界即未满足全部硬性要求，不能按全部验收通过处理。**", "",
             "全部确认 N=500，seed=20261011，离线真实引擎、heuristic 策略。路线与 pass3 完全相同：主线经过森林狼；"
             "砦路线沿右路并战斗通过三层警卫，终点为第四层ゴブリン王，不冒称整个游戏通关。", "",
             "## 1. 路线目标与前后对比", "",
             "| 路线 | 职业 | pass3 | pass4 | 目标 | 达标 |", "|---|---|---:|---:|---|---|"]
    for r in routes["rows"]:
        old = old_by_route[r["route"], r["character"]]
        bounds = targets["route_targets"]["routes"][r["route"]]["completion_rate"]
        lines.append(f"| {r['route']} | {r['character']} | {old['completion_rate']:.1%} | {r['completion_rate']:.1%} | {bounds} | "
                     f"{'是' if bounds[0] <= r['completion_rate'] <= bounds[1] else '否'} |")
    for endpoint in targets["route_targets"]["routes"]:
        old = [r["completion_rate"] for r in old_routes["rows"] if r["route"] == endpoint]
        new = [r["completion_rate"] for r in routes["rows"] if r["route"] == endpoint]
        lines.append(f"\n{endpoint} 职业差距：{max(old)-min(old):.1%} → **{max(new)-min(new):.1%}**，上限20%。")
    lines += ["", "路线未达标项：", "", *["- " + dump(v) for v in route_bad]] if route_bad else ["", "路线目标全部达标。"]
    if route_bad:
        lines += ["", "原因：锁定候选在N=64满足路线目标，但N=500扩大样本后部分职业越界；小样本筛选存在乐观偏差。"
                  "本轮保持锁定参数，不用确认样本继续追调。主线进入最终Boss时升级回满HP/MP/SP，"
                  "剩余差距不能全部归因于缺少休息点，还包括装备、技能和消耗品库存差异；具体失败次数见下表。"]
    lines += ["", "## 2. 失败点分布", "", "每行以500次起步为分母；次数相加等于该路线失败数。", "",
              "| 路线 | 职业 | pass3 失败次数 | pass4 失败次数 |", "|---|---|---|---|"]
    for r in routes["rows"]:
        lines.append(f"| {r['route']} | {r['character']} | {dump(old_by_route[r['route'], r['character']]['failure_counts'])} | {dump(r['failure_counts'])} |")
    lines += ["", "## 3. 抵达路线最终 Boss 时的资源", "",
              "只统计抵达者，不包含途中死亡者；HP/MP/SP 是绝对值，未人为回满。主线进入竜の谷仍由既有Lv5里程碑回满。"
              "本轮补充砦终点Boss的到达统计；pass3只记录竜の谷，因此砦没有历史资源均值。", "",
              "| 路线 | 职业 | 到达次数 前→后 | HP/MP/SP 前→后 | pass4 背包均值 |", "|---|---|---|---|---|"]
    for r in routes["rows"]:
        old = old_by_route[r["route"], r["character"]]
        before, after = old["boss_resources_mean"], r["boss_resources_mean"]
        resource = lambda x: "/".join(fmt(x[k]) for k in ("hp", "mp", "sp")) if x else "未记录/未抵达"
        old_arrivals = old["boss_arrivals"] if r["route"] == "dragon_valley_loc" else "未记录"
        inventory = {k: round(v, 3) for k, v in after["inventory"].items()} if after else None
        lines.append(f"| {r['route']} | {r['character']} | {old_arrivals} → {r['boss_arrivals']} | "
                     f"{resource(before)} → {resource(after)} | {dump(inventory) if after else '—'} |")
    lines += ["", "## 4. 回复点、补给与搜索", "",
              "- 王城宿屋现有 `rest_at_inn`：扣1G但无回复 → 扣1G并 `restore_full`，补齐现有休息语义。两条确认路线都不经过宿屋，因此不把通关率变化归功于它。",
              "- 精霊の泉、砦回复阵保留已有 `restore_full`；泉会转入史莱姆支线，砦回复阵位于左路，不能偷偷插入既定右路。",
              "- 战斗奖励只加入已有的薬草、治療の巻物，回复量、稀有标记、使用策略不变；每个敌人分别发奖，多敌场按数量累计。商店价格和库存未改。",
              "- N=16粗筛回复品数量与敌人数值，N=32/64复核候选；最后锁定参数才运行N=500。搜索主要分数为路线通关区间/职业差距的越界距离平方和，单场完整矩阵独立核验。",
              f"- 已保存搜索记录 `{search['candidate_count']}` 个候选评价，选中 `{search['selected_name']}`；参数和分阶段分数见 `eval/balance/pass4-search.json`。",
              "- 只增加回复品的候选收益见顶，尤其砦魔法使的MP不会被HP回复品恢复。降低敌方HP可减少累计消耗，但会抬高单场胜率/普攻胜率；这种冲突如实列于第5节，没有放宽单场目标。", "",
              "## 5. 单场胜率变化与硬指标", "",
              "HP余量、回合数仍保存在确认JSON；默认不判定，加 `--check-resource-metrics` 可恢复两项检查。"
              "pass3也按本轮同一硬指标口径重算，避免用删去软指标造成的数量下降充当数值改进。", "",
              "| 遭遇 | 职业 | heuristic 前→后 | 普攻 前→后 | HP均值 | 回合中位数 |", "|---|---|---|---|---:|---:|"]
    for r in rows:
        if r["policy"] != "heuristic":
            continue
        key = (r["encounter"], r["character"])
        old = old_by_cell[(*key, "heuristic")]
        attack = next(x for x in rows if (x["encounter"], x["character"], x["policy"]) == (*key, "attack_only"))
        old_attack = old_by_cell[(*key, "attack_only")]
        lines.append(f"| {r['encounter']} | {r['character']} | {old['win_rate']:.3f} → {r['win_rate']:.3f} | "
                     f"{old_attack['win_rate']:.3f} → {attack['win_rate']:.3f} | {fmt(r['hp_left_mean'])} | {r['rounds_median']} |")
    old_keys = {(v["encounter"], v["character"], v["metric"]) for v in old_bad}
    new_bad = [v for v in bad if (v["encounter"], v["character"], v["metric"]) not in old_keys]
    lines += ["", f"共有 {len(new_bad)} 项新增越界，"
              f"其中 {sum(v['metric'] == 'win_rate' for v in new_bad)} 项胜率、"
              f"{sum(v['metric'] == 'attack_only_win_rate' for v in new_bad)} 项Boss普攻上限。"
              "本轮胜率越界均为高于上限：缩短战斗、增加回复奖励解决了连续消耗，却使部分独立满资源战斗过易。"
              "低HP的霜狼更容易被普攻击败；累积的回复品又提高后续Boss胜率。"
              "因此单场区间确实被部分候选改动破坏，本轮没有实现这项硬性要求，不能只凭砦路线达标接受全部数值。"]
    lines += ["", "全部硬指标越界（“新增”指pass3同口径下该cell/指标原本达标）：", "",
              "| 遭遇 | 职业 | 指标 | 值 | 目标 | 状态 |", "|---|---|---|---:|---|---|"]
    for v in bad:
        lines.append(f"| {v['encounter']} | {v['character']} | {v['metric']} | {v['value']:.3f} | {v['target']} | "
                     f"{'既有' if (v['encounter'],v['character'],v['metric']) in old_keys else '新增'} |")
    lines += ["", "## 6. 剧本完整改动清单", "", "两份剧本相同字段同步修改；未改文本、角色、技能、里程碑、敌人种类与数量、xanxus/warlock战。", "",
              "| 对象 / JSON路径 | 原值 | 新值 | 原因 |", "|---|---|---|---|"]
    for d in delta:
        reason = "补齐宿屋已有休息语义" if d["path"].startswith("/locations") else (
            "增加跨战斗HP补给；保持回复品原效果" if "/rewards/" in d["path"] else
            "路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节")
        parts = d["path"].split("/")
        object_id = raw[parts[1]][int(parts[2])]["id"]
        lines.append(f"| {object_id} `{d['path']}` | {dump(d['before'])} | {dump(d['after'])} | {reason} |")
    lines += ["", "## 7. TODO(design)、推断和限制", "",
              "- TODO(design): 霜狼战前没有可用的既有休息动作；需要在凍結した村或氷の精霊战后审定新动作及文本，本轮不擅自添加。",
              "- TODO(design): 竜の谷前没有现成休息动作，但进入时Lv5已全回复；若仍需独立休息点，请审定イアン战后地点的新动作。",
              "- TODO(design): 保持现有右路砦战斗序列是否代表目标路线？若要使用现成回复阵，需要设计审定左路替代方案；Lv2技能在砦前仍不可用，未改里程碑。",
              "- TODO(design): 审定尚未满足的单场硬指标与路线目标之间的冲突。满资源单场上限约束会压低多次连续精英/Boss流程成功率；这只是当前路线/策略下的实测权衡，未证明允许参数空间无解。",
              "- 推断：哥布林砦通关指pass3的 `goblin_fort_fourth` 终点；每条路线分别约束职业差距，不把两个不同难度路线混成一组。",
              "- 推断：回复品获取允许从原本空奖励列表增加已有回复品；无新增道具，按敌人模板发放；宿屋的回复使用已有 `restore_full`，含HP/MP/SP。",
              "- 推断：保留checkpoint的固定非战斗判定、同伴和装备选择，不自行添加购物、休息或更换路线；结果不代表所有玩家路径。",
              "- 推断：spec未指定粗筛N、搜索分数、候选网格和并列规则；采用N=16/32/64、越界距离平方和、固定搜索seed与有限候选网格。两个最终候选的路线分数均为0时，先取单场越界项较少者，再比较单场越界距离；这不是证明硬指标存在可行解。",
              "- 推断：沿用pass3已有的每cell seed=20261011便于前后对照；只需确认目标文件列出的两条路线，其余分支仍用完整21场单场矩阵检查。",
              "- 偏离/未完成目标：存在的硬指标越界已完整列出；未改目标掩盖问题，也未声称全部达标。未新增设计专属动作。",
              "- 已知限制：稀有治療の巻物只在Boss可用；HP回复品不恢复MP/SP。单场checkpoint继承全部历史奖励且不扣历史消耗，可能高估实际到达Boss的库存。",
              "- N=500是每cell的蒙特卡洛确认，最大标准误约2.24个百分点，不保证换seed仍落在边界内。小N使用相同seed的前缀，N=500包含筛选样本，不是独立留出集。", "",
              "## 8. 实现、验证和复现", "",
              "- 新增route_targets与完整cell检查，缺失/重复职业也判失败；`route --check`统一运行目标文件列出的两条路线，禁止分片直接验收。",
              "- `sim --check-resource-metrics`显式恢复HP/回合判定；新增离线测试覆盖配置读取、边界、职业差距、缺失cell、CLI、真实休息/发奖、砦Boss资源记录。无新增依赖。",
              "- 既有氷の護符追击测试原先依赖哥布林存活到追加攻击；降低HP后首击已击杀。该测试固定目标HP=100以验证追击机制，不再依赖当前平衡数值。",
              "- 全量测试曾在沙箱内遭遇TemporaryDirectory的WinError 5；最终使用获准的本地沙箱外测试执行，见下面实际验证记录。",
              *["- " + str(v) for v in result.get("validation", [])], "", "```powershell",
              "python -m scripts.balance.checkpoints",
              "python -m scripts.balance.route --check --n 500 --output eval/reports/balance-2026-10-11-pass4-routes.json",
              "python -m scripts.balance.sim --check --n 500 --output eval/reports/balance-2026-10-11-pass4.json",
              "python -m unittest discover -s tests -q", "node --check client/app.js", "python -m scripts.balance.pass4_report", "```", "",
              "搜索候选参数可从pass4-search.json导出为name/parameters数组，使用 `python -m scripts.balance.pass4 --n 16 --candidates <文件> --output <结果>` 重放；加 `--single-check` 同时复核单场。支持独立分片，默认单进程兼容Windows沙箱。", ""]
    paths = [checkpoints.DEFAULT_SCENARIO, checkpoints.DEFAULT_SCENARIO.with_name("dragon_rpg_hybrid.json"),
             checkpoints.DEFAULT_CHECKPOINTS, sim.TARGETS, *[ROOT / p for p in (
                 "host/state.py", "host/combat.py", "host/item_mechanics.py", "scripts/balance/checkpoints.py",
                 "scripts/balance/route.py", "scripts/balance/sim.py", "scripts/balance/pass4.py")]]
    result["fingerprints"] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    REPORT.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
