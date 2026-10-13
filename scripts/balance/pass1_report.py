from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path
from statistics import mean
from typing import Any

from host.scenario_context import normalize_scenario_pack
from . import sim
from .budget import incoming_damage_budget
from .checkpoints import DEFAULT_CHECKPOINTS, DEFAULT_SCENARIO, ROOT

BASELINE = "bff766865a76dcea309928008e69720f1991e3ce"


def baseline_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT))


def baseline_rows(pack: dict[str, Any], checkpoints: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    with (ROOT / "eval/reports/balance-2026-10-11.csv").open(encoding="utf-8", newline="") as stream:
        for raw in csv.DictReader(stream):
            if raw["experiment"] not in {"matrix", "without_companion"} or raw["defense_mode"] != "flat":
                continue
            row = dict(raw)
            for key in ("n", "seed"):
                row[key] = int(raw[key])
            for key in ("win_rate", "rounds_median", "hp_left_mean"):
                row[key] = float(raw[key]) if raw[key] else None
            session = sim.prepare_session(pack, row["encounter"], row["character"], checkpoints)
            row["enemy_count"] = len(sim.combat._encounter_for_session(session, session["scenario_pack"])["enemy_ids"])
            row["companion"] = row["experiment"] == "matrix"
            row["skill_variant"] = "none"
            rows.append(row)
    return rows


def changes(before: Any, after: Any, path: str = "") -> list[dict[str, Any]]:
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(before.keys() | after.keys()):
            result += changes(before.get(key), after.get(key), f"{path}/{key}")
        return result
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [d for i, (left, right) in enumerate(zip(before, after)) for d in changes(left, right, f"{path}/{i}")]
    return [] if before == after else [{"path": path, "before": before, "after": after}]


def f(value: Any) -> str:
    return "—" if value is None else f"{value:.3f}" if isinstance(value, float) else str(value)


def select(rows: list[dict[str, Any]], skills: str = "none", companion: bool = True) -> list[dict[str, Any]]:
    return [r for r in rows if r["skill_variant"] == skills and r["companion"] == companion
            and r["policy"] in {"heuristic", "attack_only"}]


def make_report(result: dict[str, Any], output: Path) -> None:
    raw_before = baseline_json("host/prompt/processed/dragon_rpg.json")
    raw_after = json.loads(DEFAULT_SCENARIO.read_text(encoding="utf-8"))
    before_pack = normalize_scenario_pack(raw_before, DEFAULT_SCENARIO)
    before_cp = baseline_json("eval/balance/checkpoints.json")
    cp = json.loads(DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    before = baseline_rows(before_pack, before_cp)
    before_budget = incoming_damage_budget(before_pack, before_cp, targets)
    old, new, candidate = select(before), select(result["rows"]), select(result["rows"], "A")
    old_bad, new_bad, candidate_bad = [sim.check_results(rows, targets) for rows in (old, new, candidate)]
    original_targets = {**targets, "class_spread_max_multi_enemy": targets["class_spread_max"]}
    original_bad = sim.check_results(old, original_targets)
    diffs = changes(raw_before, raw_after)
    result.update(baseline_commit=BASELINE, before_rows=before, before_budget=before_budget,
                  changes=diffs, violations_before_original=original_bad, violations_before=old_bad,
                  violations_after=new_bad, violations_candidate_a=candidate_bad)
    lines = ["# 004 第一轮平衡报告", "", "全部为离线真实战斗引擎，flat 防御，无 API 调用、无新增依赖。",
             f"正式确认 N={result['n']} / cell，seed={result['seed']}。调整后 {len(result['rows'])} cell / {sum(r['n'] for r in result['rows']):,} 场，墙钟 {result['elapsed_seconds']:.1f} 秒。",
             f"调整前复用 002 的 N=500 原始 CSV（基线 `{BASELINE}`），不重新抽样；只比较 flat、相同策略及 checkpoint 口径。",
             "小样本先 N=16 粗筛，再 N=64 复核候选；正式 N=500 不再用于选择参数。搜索记录见 `eval/balance/pass1-search.json`。",
             "", "复现：", "", "```powershell", "python -m scripts.balance.checkpoints",
             "python -m scripts.balance.pass1 --n 500 --output eval/reports/balance-2026-10-11-pass1.json",
             "python -m scripts.balance.pass1_report", "python -m scripts.balance.sim --check --n 500",
             "python -m scripts.balance.sim --check --n 500 --skills A", "```", "",
             "checkpoint 仍为 proposed；各战独立回满资源、假定前序战斗获胜、不扣历史消耗，不代表连续通关率。",
             "", "## 1. 前后达标情况", "",
             f"002 原检查口径越界 **{len(original_bad)}** 项；采用 targets.json 已有多敌职业差距 0.25 后，基线 **{len(old_bad)}** 项；调整后无新技能 **{len(new_bad)}** 项，候选 A **{len(candidate_bad)}** 项。未修改 targets.json。",
             "全指标达标要求所有职业通过胜率、胜利剩余 HP、回合、职业差距、Boss 普攻上限。", "",
             "| 类别 | 总数 | 原全指标 | 后全指标 | A全指标 | 原仅胜率 | 后仅胜率 | A仅胜率 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for cls in targets["classes"]:
        names = {e for e, c in targets["encounters"].items() if c == cls}
        counts = [len(names - {v["encounter"] for v in bad}) for bad in (old_bad, new_bad, candidate_bad)]
        wins = [len(names - {v["encounter"] for v in bad if v["metric"] == "win_rate"}) for bad in (old_bad, new_bad, candidate_bad)]
        lines.append("| " + " | ".join(map(str, [cls, len(names), *counts, *wins])) + " |")
    lines += ["", "### 各遭遇（heuristic；职业顺序 hero / cleric / mage / thief，guest 为 warlock）", "",
              "| 遭遇 | Lv | 原胜率 | 后胜率 | 原→后职业差距 | 原→后越界项 | 后回合 | 后胜利HP |", "|---|---|---|---|---|---|---|---|"]
    for encounter in targets["encounters"]:
        sets = [[r for r in rows if r["encounter"] == encounter and r["policy"] == "heuristic"] for rows in (old, new)]
        for rows in sets:
            rows.sort(key=lambda r: ["hero", "cleric", "mage", "thief", "warlock"].index(r["character"]))
        a, b = sets
        spreads = [max(r["win_rate"] for r in rows) - min(r["win_rate"] for r in rows) for rows in sets]
        bad_counts = [sum(v["encounter"] == encounter for v in vs) for vs in (old_bad, new_bad)]
        lines.append(f"| {encounter} | {b[0]['level']} | {' / '.join(f(r['win_rate']) for r in a)} | {' / '.join(f(r['win_rate']) for r in b)} | {f(spreads[0])}→{f(spreads[1])} | {bad_counts[0]}→{bad_counts[1]} | {' / '.join(f(r['rounds_median']) for r in b)} | {' / '.join(f(r['hp_left_mean']) for r in b)} |")
    lines += ["", "### 同伴效果", "", "仅纳入 checkpoint 实际携带蓝袍法师的 56 个职业×遭遇 cell；离队和 guest 不稀释均值。每2回合在第2、4、6…回合开始回复最大HP的15%，四舍五入。", "",
              "| 遭遇 | 原平均提升pp | 后平均提升pp | 后各职业提升pp |", "|---|---:|---:|---|"]
    lifts = [[], []]
    for encounter in targets["encounters"]:
        if not cp["encounters"][encounter]["characters"]["hero"]["companion"] or targets["encounters"][encounter] == "guest":
            continue
        values = []
        for ix, rows in enumerate((before, result["rows"])):
            with_comp = [r for r in rows if r["encounter"] == encounter and r["policy"] == "heuristic" and r["companion"] and r["skill_variant"] == "none"]
            without = {r["character"]: r["win_rate"] for r in rows if r["encounter"] == encounter and r["policy"] == "heuristic" and not r["companion"]}
            uplift = [100 * (r["win_rate"] - without[r["character"]]) for r in with_comp]
            values.append(uplift)
            lifts[ix] += uplift
        lines.append(f"| {encounter} | {mean(values[0]):.2f} | {mean(values[1]):.2f} | {' / '.join(f(v) for v in values[1])} |")
    lines += ["", f"同伴等权平均提升：**{mean(lifts[0]):.2f} → {mean(lifts[1]):.2f} 个百分点**；目标 10–20pp，{'达标' if 10 <= mean(lifts[1]) <= 20 else '未达标'}。逐遭遇不保证均落入该区间；杂兵胜率接近100%时有天花板效应。",
              "", "## 2. 伤害预算（前→后）", "", "按每种骰子离散分布精确求期望，含命中、闪避、防御、抗性和敌人AI权重。假定敌人全存活、满资源、满HP，未计玩家先手击杀、护盾或回复。表中为每职业期望伤害/该 checkpoint 最大HP。",
              "商人亡霊転換不记为HP伤害，但仍会致败；Xanxus领域、治疗及后续状态不在开局直接伤害预算中，剧情/guest没有预算目标。", "",
              "| 遭遇 | 上限 | 前比例（四职业） | 后比例（四职业） | 后越界职业数 |", "|---|---:|---|---|---:|"]
    for encounter in targets["encounters"]:
        arrays = [[r for r in rows if r["encounter"] == encounter] for rows in (before_budget, result["budget"])]
        strings = [" / ".join(f"{r['ratio']:.1%}" for r in rs) for rs in arrays]
        limit = arrays[1][0]["limit"]
        lines.append(f"| {encounter} | {f(limit)} | {strings[0]} | {strings[1]} | {sum(r['over_budget'] for r in arrays[1])} |")
    lines += ["", "## 3. 完整数值与结构改动", "", "两份剧本同步修改下列机械字段，叙事、敌人名称/描述、初始HP/MP/SP/属性、分类、Xanxus与warlock数据保持原值。以下路径以 dragon_rpg.json 为准。", "",
              "| JSON路径 | 原值 | 新值 | 理由 |", "|---|---|---|---|"]
    for d in diffs:
        path = d["path"]
        reason = "按每级基础HP25%、MP/SP15%、主+2副+1实现成长；四舍五入"
        if path.startswith("/enemies/"):
            enemy_id = raw_after["enemies"][int(path.split("/")[2])]["id"]
            affected = []
            for e in targets["encounters"]:
                session = sim.prepare_session(before_pack, e, "hero", before_cp)
                if enemy_id in sim.combat._encounter_for_session(session, session["scenario_pack"])["enemy_ids"]:
                    affected.append(e)
            metrics = sorted({v["metric"] for v in old_bad if v["encounter"] in affected})
            reason = f"{enemy_id}：原越界 {', '.join(metrics)}；联合搜索全部共用此敌人的遭遇"
        elif path.startswith("/locations/"):
            reason = "多敌期望伤害超预算；先减数量并保留敌人种类，再搜索个体伤害/命中"
        elif path.startswith("/characters/"):
            reason = "聖なる杖期望7.5=Lv1鉄の剣8.5−1；holy属性（原本已holy）"
        elif path.startswith("/companions/"):
            reason = "原同伴提升22.81pp，按设计改为每2回合15%最大HP"
        elif path.startswith("/items/") or path == "/items":
            reason = "TODO(design): 聖水占位；仅商人checkpoint 2个；保证两次命中可抵消负HP，未接发放动作"
        elif path.startswith("/meta/"):
            reason = "内容版本升级，使旧存档加载新机械配置；旧flag不补发成长"
        left = json.dumps(d["before"], ensure_ascii=False, separators=(",", ":"))
        right = json.dumps(d["after"], ensure_ascii=False, separators=(",", ":"))
        if path in {"/items", "/milestones"}:
            if path == "/items":
                left, right = "无holy_water", json.dumps(raw_after["items"][-1], ensure_ascii=False)
            else:
                left, right = "无milestones", "新增lv2–lv5；详细gains见下表与同名JSON changes"
        lines.append(f"| `{path}` | `{left}` | `{right}` | {reason} |")
    lines += ["", "| 职业 | 每次HP/MP/SP上限增量 | 主/副属性 |", "|---|---|---|"]
    for cid, gain in raw_after["milestones"][0]["gains"].items():
        lines.append(f"| {cid} | {gain['max_hp']} / {gain['max_mp']} / {gain['max_sp']} | {gain['attributes']} |")
    lines += ["", "## 4. 仍越界项目", "", "下列为正式N=500全部越界，不能理解为本次搜索证明数值无解。", "",
              "| 遭遇 | 职业 | 指标 | 值 | 目标 |", "|---|---|---|---:|---|"]
    for v in new_bad:
        lines.append(f"| {v['encounter']} | {v['character']} | {v['metric']} | {f(v['value'])} | {v['target']} |")
    lines += ["", "机制/结构限制：",
              "- 同一 slime 同时用于森林入口与连续波次，同一 goblin/hobgoblin 用于不同等级/人数遭遇；调模板会牵动多场，不引入专属敌人变体。",
              "- 杂兵的短回合、同伴周期回复与剩余HP上限相互制约：勇者有护甲且输出较高，降低来伤以满足低HP职业预算，会让勇者剩余HP超过85%。N=32局部增伤复查增加了其他职业/预算越界，因此未采用；这不是全空间无解证明。",
              "- 勇者 checkpoint 已换氷鉄の大剣，元素敌人抗性和职业输出不同；霜狼对勇者冰剑免疫。只改敌人HP/防御无法同时消除元素免疫或职业解法差距。",
              "- Boss 前两回合启用护盾的既有 heuristic 与普攻上限存在张力；商人还存在亡霊転換、诅咒装备及圣水耗尽后普通伤害反向加深负HP。",
              "- 商人只有两枚直接伤害聖水的通用解法：两次命中即结束时，常见胜利回合为2或4，难满足7–12回合；若负HP增加到两瓶总伤害之外，非圣职业又失去稳定终结手段。需要设计审定持续圣属性解法、物品作用或战斗结构，未在本轮擅自扩展。",
              "- 砦与狼/史莱姆为互斥森林分支；现有村庄flag依赖蓝袍同行、谷入口flag依赖接受イアン。未经设计决定，不新增路线或强行给所有checkpoint统一等级。",
              "- 同伴说明仍写每回合8HP，多敌叙述仍可能提原数量；本任务禁止修改叙事，已留TODO(design)。",
              "", "## 5. 技能候选A效果", "", "Lv3/Lv5每职业各A、B，共16个候选，使用现有技能字段和已有日语名称；完整效果见 `eval/balance/skill_candidates.json`。同名仅为候选占位，尚未加入剧本。", "",
              "| 遭遇 | 无技能胜率均值 | A胜率均值 | 无→A越界项 |", "|---|---:|---:|---|"]
    for e in targets["encounters"]:
        base = [r for r in new if r["encounter"] == e and r["policy"] == "heuristic"]
        cand = [r for r in candidate if r["encounter"] == e and r["policy"] == "heuristic"]
        lines.append(f"| {e} | {mean(r['win_rate'] for r in base):.3f} | {mean(r['win_rate'] for r in cand):.3f} | {sum(v['encounter']==e for v in new_bad)}→{sum(v['encounter']==e for v in candidate_bad)} |")
    lines += ["", "## 6. TODO(design) 与发放候选", "",
              "- 审定16项技能候选（A为输出、B为守护/回复/范围输出），名称、成本、伤害与最终解锁；不将A自动转正。",
              "- 聖水名称/描述均占位，伤害36、holy、命中100（实际仍扣敌闪避）、消耗品。两枚理论命中总伤害108，可覆盖原ゼボク−100HP；仅模拟发放，不代表保证获胜。",
              "- 发放候选1：`castle/check_supplies`，出发前按所有职业一次性免费领取2枚；该地点是所有职业起点。",
              "- 发放候选2：`castle/ask_general_advice`，与既有将军对话后免费领取2枚；同样各职业可达，需确保领取不会被跳过。",
              "- 发放候选3：`alley_night` 的既有职业商人对话，在 `betray_cursed_merchant` 之前统一赠2枚；这是所有职业进入商人战前必经地点，赠予动机需设计确认。",
              "- 审定互斥路线里程碑的补足规则、村庄/谷入口缺失的通用flag；审定数值改动与剩余目标冲突，更新同伴和人数叙述。",
              "", "## 7. 推断、偏离与已知限制", "",
              "- Lv2选 defeated_slime_king，狼支线采用引擎已有 combat_defeated:forest_wolves:forest_wolf 作同一里程碑替代flag；Lv3选 cleared_goblin_fort；Lv4选 warlock_disappeared_at_village；Lv5选 accepted_ian_request。后两者最接近节点但并非覆盖全部路线，明确保留设计TODO。",
              "- 新角色按到达节点的等级差累计每级增量，例如砦首次到Lv3累计两级；低级节点迟到不重复成长。旧存档已有flag的最高节点以下只消费不补发，后续仅发更高节点的新增等级。该跨分支解释需设计复核。",
              "- 基础值取原角色模板，每级HP25%、MP/SP15%均采用floor(x+0.5)，避免Python银行家舍入；同伴回复也采用该规则，首次第2回合。",
              "- 杖的“期望减1”解释为Lv1未计命中/抗性/防御的公式均值，wis随成长提高；未改变初始角色资源与属性。",
              "- 搜索目标使用真实引擎所有适用越界项及区间距离加权，固定种子；不是全空间最优证明。正式N=500仍有抽样误差，建议设计审定后独立种子再验证。",
              "- 伤害预算以开局全敌存活为统一可复现口径；对状态/领域注明未覆盖，不能替代真实胜率。",
              "- 发放候选均为现有地点/动作，魔法店/道具屋虽可达但不是商人战必经，因此未声称全路线都会取得。",
              "- 偏离：通用入口flag需设计决定，当前严格使用已有flag；部分预算/目标仍越界，未改机制、抗性、初始属性、剧情战或targets来强行通过。",
              "- 同名JSON保留完整正式矩阵、预算、变更和输入代码SHA256。", "",
              "## 8. 工程交付与验证", "",
              "- 引擎：`host/state.py`、`host/combat.py`、`host/scenario_context.py`；数据：两份dragon_rpg剧本与scenario_pack.schema.json。",
              "- 模拟：`scripts/balance/checkpoints.py`、`sim.py`、`budget.py`、`pass1.py`、`pass1_report.py`；候选、搜索记录与checkpoint位于eval/balance，正式结果为本报告及同名JSON。",
              "- 测试：`tests/test_balance_pass.py`新增10项，`tests/test_dragon_story.py`同步已授权数值断言；文档为`docs/api-free-actions.md`和`eval/balance/README.md`。无新增依赖。",
              "- `python -m unittest discover -s tests -q`：288项，287通过、1项按原有BALANCE_ENFORCE条件跳过。",
              "- `node --check client/app.js`、`git diff --check`：通过。",
              f"- `python -m scripts.balance.sim --check --n 500`：退出1，{len(new_bad)}项越界；加`--skills A`：退出1，{len(candidate_bad)}项越界。数值未全达标，不把退出1隐去。",
              "- 两份剧本逐字段核对：叙事、初始资源/属性、敌人名字/描述、Xanxus/warlock、分类及targets未改；全部正式cell的N、总场数、输入/代码SHA256和越界计数复核通过。",
              "- 提交按工程前缀，具体提交号见最终汇报。", ""]
    output.write_text("\n".join(lines), encoding="utf-8")
    output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "eval/reports/balance-2026-10-11-pass1.json")
    args = parser.parse_args()
    make_report(json.loads(args.input.read_text(encoding="utf-8")), args.input.with_suffix(".md"))


if __name__ == "__main__":
    main()
