from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from statistics import mean
from typing import Any

from . import sim
from .checkpoints import DEFAULT_CHECKPOINTS, DEFAULT_SCENARIO, ROOT
from .pass1_report import changes, f, select

BASELINE = "6abff336d6c7795cde2465e8f48eba06324c9dad"


def lifts(rows: list[dict[str, Any]], cp: dict[str, Any], targets: dict[str, Any]) -> dict[str, list[float]]:
    result = {}
    for encounter, category in targets["encounters"].items():
        if category == "guest" or not cp["encounters"][encounter]["characters"]["hero"]["companion"]:
            continue
        with_comp = [r for r in select(rows) if r["policy"] == "heuristic" and r["encounter"] == encounter]
        without = {r["character"]: r["win_rate"] for r in select(rows, companion=False)
                   if r["policy"] == "heuristic" and r["encounter"] == encounter}
        result[encounter] = [100 * (r["win_rate"] - without[r["character"]]) for r in with_comp]
    return result


def make_report(result: dict[str, Any], output: Path) -> None:
    before = json.loads((ROOT / "eval/reports/balance-2026-10-11-pass1.json").read_text(encoding="utf-8"))
    cp = json.loads(DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    targets = json.loads(sim.TARGETS.read_text(encoding="utf-8"))
    pack = json.loads(DEFAULT_SCENARIO.read_text(encoding="utf-8"))
    baseline = BASELINE
    result.setdefault("execution_commit", result["baseline_commit"])
    result["baseline_commit"] = baseline
    original = json.loads(subprocess.check_output(["git", "show", f"{baseline}:host/prompt/processed/dragon_rpg.json"], cwd=ROOT))
    old, new = select(before["rows"]), select(result["rows"])
    old_bad, new_bad = [sim.check_results(rows, targets) for rows in (old, new)]
    old_lifts, new_lifts = [lifts(rows, cp, targets) for rows in (before["rows"], result["rows"])]
    ratio = next(c for c in pack["companions"] if c["id"] == "blue_robed_mage")["round_start_effects"][0]["max_hp_ratio"]
    result.update(changes=changes(original, pack), violations_before=old_bad, violations_after=new_bad,
                  companion_uplift_pp=mean(v for values in new_lifts.values() for v in values))
    count = len(result["rows"]) + len(result["without_new_skills"])
    lines = ["# 005 第二轮平衡报告", "", "离线真实战斗引擎，flat 防御，无外部 API、无新增依赖。",
             f"正式 N={result['n']} / cell，seed={result['seed']}，共 {count} cell / {count * result['n']:,} 场；墙钟 {result['elapsed_seconds']:.1f} 秒。",
             f"pass1 基线提交 `{baseline}`，复用 pass1 的 N=500 结果。先 N=16 粗筛、N=64 复核，再锁定参数做 N=500 确认；搜索与补充复核记录见 eval/balance/pass2-search.json。",
             "checkpoint 仍为 proposed；每场回满 HP/MP/SP，不扣历史道具消耗，不能视作连续通关率。本轮所有 checkpoint 经真实 check_supplies 领取两瓶聖水，移除原先只对商人战的模拟注入。",
             "因此 pass1→pass2 同时包含设计指定的技能、补给口径及数值变化；不是纯敌人数值的因果对照。另提供同一最终配置下去掉8个新技能的消融。", "",
             "复现：", "", "```powershell", "python -m scripts.balance.checkpoints",
             "python -m scripts.balance.pass2 --n 500 --output eval/reports/balance-2026-10-11-pass2.json",
             "python -m scripts.balance.pass2_report",
             "python -m scripts.balance.sim --check --n 500 --output .tmp-test/balance-pass2-check.json", "```", "",
             "## 1. 前后达标情况", "", f"`--check` 越界：**{len(old_bad)} → {len(new_bad)}**；targets.json 未修改。",
             "全指标包含所有职业的胜率、胜利剩余HP均值、全部战斗（含失败）的回合中位数、职业差距和Boss普攻上限；伤害预算、同伴提升另行列出，不混入 --check 计数。", "",
             "| 类别 | 总数 | pass1全指标 | pass2全指标 | pass1仅胜率 | pass2仅胜率 |", "|---|---:|---:|---:|---:|---:|"]
    for category in targets["classes"]:
        names = {e for e, c in targets["encounters"].items() if c == category}
        counts = [len(names - {v["encounter"] for v in bad}) for bad in (old_bad, new_bad)]
        wins = [len(names - {v["encounter"] for v in bad if v["metric"] == "win_rate"}) for bad in (old_bad, new_bad)]
        lines.append("| " + " | ".join(map(str, [category, len(names), *counts, *wins])) + " |")
    lines += ["", "职业顺序为 hero / cleric / mage / thief；guest 为 warlock。", "",
              "| 遭遇 | Lv | pass1胜率 | pass2胜率 | 职业差距前→后 | 越界前→后 | pass2回合 | pass2胜利HP |", "|---|---|---|---|---|---|---|---|"]
    for encounter in targets["encounters"]:
        a, b = [[r for r in rows if r["encounter"] == encounter and r["policy"] == "heuristic"] for rows in (old, new)]
        rates = [" / ".join(f(r["win_rate"]) for r in rows) for rows in (a, b)]
        spreads = [max(r["win_rate"] for r in rows) - min(r["win_rate"] for r in rows) for rows in (a, b)]
        counts = [sum(v["encounter"] == encounter for v in bad) for bad in (old_bad, new_bad)]
        lines.append(f"| {encounter} | {b[0]['level']} | {rates[0]} | {rates[1]} | {f(spreads[0])}→{f(spreads[1])} | {counts[0]}→{counts[1]} | {' / '.join(f(r['rounds_median']) for r in b)} | {' / '.join(f(r['hp_left_mean']) for r in b)} |")
    lines += ["", "### 同伴效果", "", f"每2回合（第2、4、6…回合开始）回复最大HP的 **{ratio:.0%}**，沿用四舍五入。只纳入实际携带蓝袍法师的56个职业×遭遇cell，离队及guest不稀释均值。", "",
              "| 遭遇 | pass1提升pp | pass2提升pp | pass2各职业提升pp |", "|---|---:|---:|---|"]
    for e, values in new_lifts.items():
        lines.append(f"| {e} | {mean(old_lifts[e]):.2f} | {mean(values):.2f} | {' / '.join(f(v) for v in values)} |")
    lines += ["", f"等权平均提升 **{mean(v for vs in old_lifts.values() for v in vs):.2f} → {result['companion_uplift_pp']:.2f}pp**，目标10–20pp。", "",
              "N=64回复比例复核（正式N=500前完成选择）：", "",
              "| 每2回合回复比例 | 平均提升pp | 越界数 |", "|---|---:|---:|"]
    search = json.loads((ROOT / "eval/balance/pass2-search.json").read_text(encoding="utf-8"))
    for candidate in search["ratio_candidates"]:
        lines.append(f"| {candidate['ratio']:.0%} | {100 * candidate['uplift']:.2f} | {candidate['violations']} |")
    lines += ["",
              "### 最终Boss", "", "| 职业 | 胜率 | 距离目标区间[0.60,0.75] | 最常见败因 |", "|---|---:|---:|---|"]
    for row in new:
        if row["encounter"] == "dragon_valley_loc" and row["policy"] == "heuristic":
            distance = max(.60 - row["win_rate"], row["win_rate"] - .75, 0)
            cause = next(iter(row["defeat_causes"]), "—")
            lines.append(f"| {row['character']} | {row['win_rate']:.3f} | {100 * distance:.1f}pp | {cause} |")
    lines += ["", "Boss抗性仍为physical 0.65、fire 0、ice 1.75。职业武器与元素差别、原heuristic前两回合优先第一个防御技能，会影响输出窗口；未更改抗性、旧技能或策略以迎合指标。败因计数见JSON，不把有限搜索解释为无解证明。",
              "胜率之外仍有HP/回合越界。机制解释：低命中、大伤害骰子的配置使来伤更分散，既可能早败，也可能在多次未命中后高HP获胜；治疗进一步抬高胜利条件下的剩余HP。冰弱点、聖水与新技能爆发缩短输出窗口，而回合中位数也包含早败。上述为机制推断，不能把胜率达标等同于节奏达标。", "",
              "## 2. 伤害预算（前→后）", "", "精确骰子期望，含命中、闪避、防御、抗性与AI权重；开局全敌存活、满资源，不计先手击杀、护盾、回复和后续领域/状态。亡霊転換不属于HP伤害但仍会致败。", "",
              "| 遭遇 | 上限 | pass1比例 | pass2比例 | pass2越界职业数 |", "|---|---:|---|---|---:|"]
    for e in targets["encounters"]:
        a, b = [[r for r in rows if r["encounter"] == e] for rows in (before["budget"], result["budget"])]
        lines.append(f"| {e} | {f(b[0]['limit'])} | {' / '.join(format(r['ratio'], '.1%') for r in a)} | {' / '.join(format(r['ratio'], '.1%') for r in b)} | {sum(r['over_budget'] for r in b)} |")
    lines += ["", "## 3. 完整数值与结构改动", "", "两份剧本同步；下表路径以dragon_rpg.json为准。只修改005允许的文本、机械字段和内容版本；初始属性/资源、敌人名称/描述、抗性、遭遇类别、Xanxus/warlock战斗定义与targets保持不变。", "",
              "| JSON路径 | 原值 | 新值 | 理由 |", "|---|---|---|---|"]
    for change in result["changes"]:
        path = change["path"]
        reason = "005指定的正式技能、聖水或统一入口flag"
        if path.startswith("/enemies/"):
            eid = pack["enemies"][int(path.split("/")[2])]["id"]
            reason = f"{eid}：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额"
        elif path.startswith("/companions/"):
            reason = "将同伴平均提升调入10–20pp"
        elif path.startswith("/meta/"):
            reason = "加载新版机械配置"
        values = [json.dumps(change[k], ensure_ascii=False, separators=(",", ":")).replace("|", "&#124;") for k in ("before", "after")]
        lines.append(f"| `{path}` | `{values[0]}` | `{values[1]}` | {reason} |")
    lines += ["", "技能使用独立level_skills表，保持已有Lv1技能；在真实升级时按实际等级追加，跳到Lv4/Lv5时补齐低等级技能，同ID不重复。保留旧存档不追溯成长的规则。", "",
              "## 4. 仍越界项目", "", "| 遭遇 | 职业 | 指标 | 值 | 目标 |", "|---|---|---|---:|---|"]
    for v in new_bad:
        lines.append(f"| {v['encounter']} | {v['character']} | {v['metric']} | {f(v['value'])} | {v['target']} |")
    lines += ["", "共享模板约束：slime覆盖三场，goblin/hobgoblin覆盖不同等级、数量的遭遇；单一模板不能分别拟合每个checkpoint。护甲、元素抗性、有限MP/SP和同伴周期回复共同造成职业差别。", "",
              "## 5. 正式技能效果", "", "使用最终敌人、同伴与补给配置，仅移除8个新技能；不回退成长或旧技能。消融计算全部heuristic与Boss attack_only；其他类别没有普攻胜率上限，不重复计算。正式--check矩阵仍覆盖全部162cell。", "",
              "| 遭遇 | 无新技能平均胜率 | 正式技能平均胜率 | 越界无→有 |", "|---|---:|---:|---|"]
    ablation_bad = sim.check_results(result["without_new_skills"], targets)
    for e in targets["encounters"]:
        a, b = [[r for r in rows if r["encounter"] == e and r["policy"] == "heuristic"] for rows in (result["without_new_skills"], new)]
        lines.append(f"| {e} | {mean(r['win_rate'] for r in a):.3f} | {mean(r['win_rate'] for r in b):.3f} | {sum(v['encounter']==e for v in ablation_bad)}→{sum(v['encounter']==e for v in new_bad)} |")
    lines += ["", "## 6. TODO(design)", "",
              "- TODO(design): 建议将商人战单列目标：现有两瓶聖水的通用解法要求两次命中，胜利通常2或4回合。建议回合[2,5]、胜利HP[0.50,1.00]，胜率目标仍保留[0.60,0.75]；或另行设计持续圣属性解法。未改targets。",
              "- TODO(design): 建议把杂兵回合改为[1,4]并区分消耗强力道具的胜利HP（可放宽至1.00），同时单独报告道具消耗。现在一瓶固定36伤害会秒杀低HP敌人，单战满补给要求敌人HP明显提高才能满足下限，可能扭曲连续冒险。",
              "- TODO(design): 建议对proposed checkpoint增加跨战斗消耗路线对照；两瓶聖水在每场都存在且策略直接按伤害优先使用，不能外推为全流程通关表现。本轮严格执行指定补给，不擅自新增保留物品的策略。",
              "- TODO(design): 建议同伴10–20pp继续按有同伴的56cell等权均值验收；杂兵接近100%存在天花板，不要求每场单独达到10pp。",
              "- TODO(design): 同伴旧叙述仍写每回合8HP，历史多敌叙述可能与004的数量调整不一致；需设计统一文本。005未授权修改这些叙述。",
              "- TODO(design): 新技能和旧技能有同名（渾身斬り、影隠れ、火球、氷の矢、急所突き），新防御技能位于旧技能之后，既有heuristic常选择旧技能。建议另行审定替换/升级关系与策略；本轮保留指定名字、原技能与原策略。", "",
              "- TODO(design): 审定已达Lv5旧存档的新技能迁移；自动补发需要区分历史clear_skills等剧情效果，本轮未追溯补发。", "",
              "- TODO(design): 当前proposed路线的多敌砦战发生于Lv1，Lv3全体火球在这组checkpoint中缺少多敌施展窗口；如需验证范围攻击的定位，请审定后续多敌遭遇或路线。", "",
              "## 7. 推断、偏离与已知限制", "",
              "- 将“商人战之前的遭遇”解释为主路线出发先check_supplies；所有非guest checkpoint因此持有2瓶，后期也不假设历史消耗。来源是实际动作重放，不额外注入。",
              "- 现有村庄入口为forest_exit→village_approach；竜の谷有village、post_xanxus、ian_clearing接受/拒绝共4条入口。只补flags_set，不改入口文本或增设路线。",
              "- 新技能作为增量技能保留Lv1技能；原候选ID沿用，以unlock_level表示门槛，未将同名技能隐式替换。技能/物品名与提示文字按005定稿，技能一句描述为005授权撰写。",
              "- 将军成功与失败结果都加指定提示，均不发物品；check_supplies沿用once，并在物品效果中加not_flag条件，防直接重复执行造成补发。",
              "- 搜索按共享敌人分组，以越界数量、区间距离及伤害预算超额评分；有限搜索不是全局最优。正式N=500是确认样本，闭区间附近有抽样不确定性，约70%胜率的标准误差约2pp。",
              "- 旧存档没有level仍视为Lv1且不追溯成长；已到Lv5的旧存档不会自动补发新技能，需要设计审定迁移方式，当前交付按新游戏路径验证。",
              "- 未改变数值目标、玩家初始数值、抗性、原技能、AI策略或剧情战定义；部分目标仍越界，属于未达到的数值目标，不伪报全通过。", "",
              "## 8. 工程交付与验证", "",
              "- 引擎host/state.py；两份dragon_rpg剧本及schema；checkpoint与模拟技能还原；pass2搜索、正式矩阵、消融和本报告生成器；对应离线测试与README。无新增依赖。",
              "- 文件清单：`host/state.py`；`host/prompt/processed/dragon_rpg.json`、`dragon_rpg_hybrid.json`、`scenario_pack.schema.json`。",
              "- 模拟代码：`scripts/balance/checkpoints.py`、`sim.py`、`pass2.py`、`pass2_report.py`；测试：`tests/test_balance_pass2.py`、`tests/test_dragon_story.py`。",
              "- 评测文件：`eval/balance/README.md`、`checkpoints.json`、`pass2-search.json`；报告：`eval/reports/balance-2026-10-11-pass2.md`及同名JSON。",
              "- `python -m unittest discover -s tests -q`：295项，294通过、1项按原有BALANCE_ENFORCE条件跳过；`node --check client/app.js`与`git diff --check`通过。",
              f"- `python -m scripts.balance.sim --check --n 500`：{len(new_bad)}项越界，预期退出码1；相比pass1的124项{'下降' if len(new_bad)<124 else '未下降'}。",
              "- 正式runner调用sim.main的--check入口，保留真实退出码及矩阵，随后计算同伴/技能对照，避免重复运行同一检查。",
              "- 两份剧本的本轮机械差分一致；初始资源/属性/旧技能、敌人名称/描述/抗性、剧情战与targets均经对照核验。JSON保留正式矩阵、技能消融、伤害预算、完整变更、败因和输入/代码SHA256。", "",
              "## 9. 目标合理性建议", "", "下列只是交由设计负责人审定的建议，未修改targets.json。理由与机制限制详见第4、6节。", "",
              "| 项目 | 建议 | 依据 |", "|---|---|---|",
              "| 商人回合/胜利HP | 单列回合[2,5]、HP[0.50,1.00] | 两瓶聖水的通用解法是两次命中，强行拉长会失去可靠终结手段 |",
              "| 杂兵回合/胜利HP | 回合[1,4]；消耗强力道具时允许HP上限1.00 | 固定36伤害聖水会一击结束弱敌；应额外报告道具消耗 |",
              "| 同伴提升 | 保持56个有同伴cell等权平均10–20pp | 杂兵100%胜率的天花板使逐遭遇要求不合理 |",
              "| 连续流程 | 增加扣除历史消耗的路线评测，暂不设新数值阈值 | 当前满资源、两瓶聖水的独立战斗不能代表连续闯关 |", ""]
    output.write_text("\n".join(lines), encoding="utf-8")
    output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "eval/reports/balance-2026-10-11-pass2.json")
    args = parser.parse_args()
    make_report(json.loads(args.input.read_text(encoding="utf-8")), args.input.with_suffix(".md"))


if __name__ == "__main__":
    main()
