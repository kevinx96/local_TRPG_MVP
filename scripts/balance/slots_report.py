"""Build the spec 032 comparison and an isolated, exact pre-change engine."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from statistics import mean

from . import checkpoints, support


ROOT = checkpoints.ROOT
REPORTS = ROOT / "eval/reports"
BASELINE = "c27b97f"
HISTORY = {"routes": "balance-2026-10-13-playtest.json", "finals": "balance-2026-10-12-support3.json",
           "rewards": "balance-2026-10-13-regional-plus3.json"}


def prepare_baseline() -> Path:
    destination = ROOT / ".tmp-test/032-baseline"
    files = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASELINE,
                                     "host", "scripts", "eval/balance"], cwd=ROOT, text=True).splitlines()
    selected = [name for name in files if name.endswith(".py") or name.startswith("eval/balance/")
                or name in {"host/prompt/processed/dragon_rpg.json", "host/prompt/processed/dragon_rpg_hybrid.json"}]
    selected += ["eval/reports/" + name for name in HISTORY.values()]
    for name in selected:
        target = (destination / name).resolve()
        if not target.is_relative_to(destination.resolve()):
            raise ValueError(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(["git", "show", f"{BASELINE}:{name}"], cwd=ROOT))
    (destination / "scripts/balance/slots.py").write_bytes(Path(__file__).with_name("slots.py").read_bytes())
    return destination


def read(name: str) -> dict:
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def percentage(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-baseline", action="store_true")
    args = parser.parse_args()
    if args.prepare_baseline:
        print(prepare_baseline())
        return
    current = {suite: read(f"slots-{suite}.json") for suite in (*HISTORY, "controls")}
    legacy = {suite: read(f"slots-{suite}-baseline.json") for suite in (*HISTORY, "controls")}
    history = {suite: read(name) for suite, name in HISTORY.items()}
    lines = ["# 032 装备部位、鎧价格与ロビン：平衡复核", "",
        "日期：2026-10-15。全程离线、固定 seed=20261012、真实引擎、heuristic，不调任何任务外数值。",
        "职业路线每职业/策略 N=500，最终战与奖励/机制对照每条件 N=2000。沿用既有五种路线策略、已选支线和最终战十种支援条件，不重新寻找最优策略。",
        f"旧引擎列在隔离目录重放任务前提交 `{BASELINE}`；历史列分别来自最后一份职业路线、最终战、031 区域+3报告。JSON保存各组数据、装备与指纹。", "",
        "## 职业路线", "", "|策略|职业|上一报告|旧引擎复跑|032|相对历史pp|相对旧引擎pp|",
        "|---|---|---:|---:|---:|---:|---:|"]
    warnings = []
    for row in current["routes"]["rows"]:
        key = (row["policy_label"], row["character"])
        old = next(r for r in history["routes"]["rows"] if (r["policy_label"], r["character"]) == key)
        base = next(r for r in legacy["routes"]["rows"] if (r["policy_label"], r["character"]) == key)
        value, previous, baseline = row["completion_rate"], old["completion_rate"], base["completion_rate"]
        lines.append(f"|{'|'.join(key)}|{percentage(previous)}|{percentage(baseline)}|{percentage(value)}|{100*(value-previous):+.2f}|{100*(value-baseline):+.2f}|")
        if abs(value-previous) > .05 + 1e-9:
            warnings.append(f"路线 {'/'.join(key)} 相对历史 {100*(value-previous):+.2f}pp")
    targets = json.loads((ROOT / "eval/balance/targets.json").read_text(encoding="utf-8"))["route_targets"]
    low, high = targets["routes"]["dragon_valley_loc"]["completion_rate"]
    route_rows = [r for r in current["routes"]["rows"] if r["policy_label"] == "class_aware"]
    lines += ["", f"现行主线目标按class_aware评价：{percentage(low)}–{percentage(high)}；职业差距≤{targets['class_spread_max']*100:g}pp。",
              "", "|职业|032|距目标区间pp|", "|---|---:|---:|"]
    for row in route_rows:
        value = row["completion_rate"]
        gap = max(low-value, value-high, 0) * 100
        lines.append(f"|{row['character']}|{percentage(value)}|{gap:.2f}|")
        if gap > 5 + 1e-9:
            warnings.append(f"主线目标 {row['character']} 偏离区间{gap:.2f}pp")
    spread = max(r["completion_rate"] for r in route_rows) - min(r["completion_rate"] for r in route_rows)
    lines.append(f"\n职业差距{spread*100:.2f}pp，超过上限{max(0,spread-targets['class_spread_max'])*100:.2f}pp。")
    if spread-targets["class_spread_max"] > .05 + 1e-9:
        warnings.append(f"主线职业差距{spread*100:.2f}pp，超过20pp上限{(spread-targets['class_spread_max'])*100:.2f}pp")
    lines += ["", "路线为连续通关率，保持前战损失、有限背包及实际金币；未使用区域重来。现行策略没有购买アダマンタイトの鎧、没有带ロビン同行；因此这两项对这套固定策略的直接影响为0。", "",
        "## 最终战 ドラコ/ヴァイス", "", "|支援条件|职业|上一报告|旧引擎复跑|032|相对历史pp|相对旧引擎pp|",
        "|---|---|---:|---:|---:|---:|---:|"]
    finals = current["finals"]["rows"]
    for row in finals:
        key = (row["case"], row["character"])
        old = next(r for r in history["finals"]["supports"] if (r["case"], r["character"]) == key)
        base = next(r for r in legacy["finals"]["rows"] if (r["case"], r["character"]) == key)
        value, previous, baseline = row["win_rate"], old["win_rate"], base["win_rate"]
        lines.append(f"|{'|'.join(key)}|{percentage(previous)}|{percentage(baseline)}|{percentage(value)}|{100*(value-previous):+.2f}|{100*(value-baseline):+.2f}|")
        none = next(r for r in finals if r["character"] == row["character"] and r["case"] == "none")
        row["contribution_pp"] = (value-none["win_rate"]) * 100
        if abs(value-previous) > .05 + 1e-9:
            warnings.append(f"最终战 {'/'.join(key)} 相对历史 {100*(value-previous):+.2f}pp")
    lines += ["", "单场满资源，standard 只保留1枚紅竜の炎核；all_purify沿用净化准备。最终战的ロビン条件是支援旗标，不是同行者，援護射撃的修改不会直接改动此条件。", "",
              "现行最终战目标检查：", ""]
    violations = support.check_results(finals)
    lines += [f"- {v}" for v in violations] or ["- 无违规。"]
    for case in ("king", "robin"):
        contribution = mean(r["contribution_pp"] for r in finals if r["case"] == case)
        lines.append(f"- {case}平均独立支援贡献：{contribution:+.2f}pp，目标[3,8]pp。")
    lines += ["", "## 031 区域+3奖励复核", "",
        "保持上一轮冻结的奖励池、属性、装备/背包和支援准备；通过当前物品目录补slot后规整装备，未把历史快照中的无slot装备误作不可装备。旧引擎复跑相同快照，只有新引擎应用部位约束。",
        "主线1枚魔力果实；全探索沿用各区首枚与Boss总量。全探索是条件上界，包含互斥分支的奖励控制，不是连续生存率。", "",
        "|最终战|职业|模式|031上一报告|旧引擎复跑|032|相对031pp|032无奖励|奖励提升pp|031原上限pp|",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    reward_violations = []
    for row in current["rewards"]["rows"]:
        if row["condition"] != "after":
            continue
        key = (row["encounter"], row["character"], row["mode"])
        matches = lambda r: (r["encounter"], r["character"], r["mode"]) == key
        old = next(r for r in history["rewards"]["rows"] if matches(r))
        base = next(r for r in legacy["rewards"]["rows"] if matches(r) and r["condition"] == "after")
        before = next(r for r in current["rewards"]["rows"] if matches(r) and r["condition"] == "before")
        value, previous = row["win_rate"], old["after"]["win_rate"]
        uplift = 100*(value-before["win_rate"])
        limit = old["limit_pp"]
        lines.append(f"|{'|'.join(key)}|{percentage(previous)}|{percentage(base['win_rate'])}|{percentage(value)}|{100*(value-previous):+.2f}|{percentage(before['win_rate'])}|{uplift:+.2f}|{limit}|")
        if abs(value-previous) > .05 + 1e-9:
            warnings.append(f"031奖励 {'/'.join(key)} 相对历史 {100*(value-previous):+.2f}pp")
        historical_uplift = 100*(value-old["previous"])
        if max(uplift, historical_uplift) > limit + 1e-9:
            reward_violations.append(f"{'/'.join(key)}：配对奖励提升{uplift:+.2f}pp，较031原历史基准{historical_uplift:+.2f}pp，上限+{limit}pp")
        if max(uplift, historical_uplift) - limit > 5 + 1e-9:
            warnings.append(f"031奖励目标 {'/'.join(key)} 超过上限{max(uplift,historical_uplift)-limit:.2f}pp")
    lines += ["", "031原目标同时检查奖励前后配对差与原历史基准差（任一超限即列出）：", "", *[f"- {v}" for v in reward_violations]]
    if not reward_violations:
        lines.append("- 无违规。")
    lines += ["", "## 三项影响分开列出", "", "### 部位制", "",
        "旧引擎可让防具与初始装备叠加，也会在已有聖なる杖/魔導書时自动装上背包中的kind:weapon。032按显式slot保留一件；未装备的武器不再挤入已占用部位。虹晶武器会替换聖なる杖/魔導書，护符、水晶球同属装饰品，只保留最后装备者。",
        "上面的旧引擎配对列衡量这项机制影响；各固定路线/最终战准备未购鎧且不携带ロビン，价格/援護射撃没有直接介入。僧侶连续路线保持聖なる杖后，不再自动叠装イアン赠送的氷鉄の大剣；イグニス对冰的倍率为1.75，固定策略没有从背包主动换装，因此这一准备差异影响很大。", "",
        "僧侶class_aware的500局中：イグニス失败263局，谷入口59局，スライム王48局，村火精灵及霜狼各1局；128局连续通关。031冻结快照保留的是当时最后装备的氷鉄の大剣，故该条件复核不能替代新规则下重走路线的结果。", "",
        "额外对照：森狼检查点勇者，按实际商店购买并从背包装备鎧，其余准备不变：", "",
        "|条件|旧装备减伤|032装备减伤|旧胜率|032胜率|旧剩余HP比例|032剩余HP比例|", "|---|---:|---:|---:|---:|---:|---:|"]
    for condition in ("initial_armor", "bought_armor"):
        old = next(r for r in legacy["controls"]["rows"] if r["condition"] == condition)
        new = next(r for r in current["controls"]["rows"] if r["condition"] == condition)
        defense = lambda r: sum(i.get("combat", {}).get("defense", 0) for i in r["inventory"] if i["name"] in r["equipment"])
        lines.append(f"|{condition}|{defense(old)}|{defense(new)}|{percentage(old['win_rate'])}|{percentage(new['win_rate'])}|{percentage(old['hp_left_mean'])}|{percentage(new['hp_left_mean'])}|")
    lines += ["", "### 鎧价格", "",
        "仅forge_shop的鎧从20G变60G；其他价格不变。下表通过真实交易接口按两种购买顺序重放开局100G：", "",
        "|鎧价|购买顺序|成功购买|剩余G|", "|---:|---|---|---:|"]
    for row in current["controls"]["prices"]:
        lines.append(f"|{row['price']}|{' → '.join(row['order'])}|{'、'.join(row['bought'])}|{row['gold']}|")
    lines += ["", "固定报告策略未购买此鎧，因此不能用它们估计玩家在鎧与50G護符之间选择后的通关率变化；此处明确报告预算约束，不擅自选定购买政策或调整目标。", "",
        "### ロビン", "",
        "相同032装备/种子，仅变更同行ロビン的援護射撃：旧2d4随机、仅伤害改为2d4+1随机、最终2d4+1打当前HP最高（同值取列表最前）。随机取目标会额外消耗RNG，因此配对差包含战斗序列变化。", "",
        "|遭遇|职业|旧射击|仅伤害+1|最高HP目标|伤害差pp|目标差pp|总差pp|", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in current["controls"]["rows"]:
        if row["condition"] != "highest_hp":
            continue
        group = [r for r in current["controls"]["rows"] if r["encounter"] == row["encounter"] and r["character"] == row["character"]]
        old = next(r for r in group if r["condition"] == "old_robin")["win_rate"]
        damage = next(r for r in group if r["condition"] == "damage_only")["win_rate"]
        value = row["win_rate"]
        lines.append(f"|{row['encounter']}|{row['character']}|{percentage(old)}|{percentage(damage)}|{percentage(value)}|{100*(damage-old):+.2f}|{100*(value-damage):+.2f}|{100*(value-old):+.2f}|")
        if abs(value-old) > .05 + 1e-9:
            warnings.append(f"ロビン机制对照 {row['encounter']}/{row['character']} 改动{100*(value-old):+.2f}pp")
    lines += ["", "## 超过5pp的历史变化与设计待审", "",
        "以下按绝对差>5pp逐项列出，不将机械回归通过等同于平衡通过：", "", *[f"- {w}" for w in warnings]]
    if not warnings:
        lines.append("- 无历史变化超过5pp。")
    lines += ["", "TODO(design): 审阅上述历史变化和主线/031现行目标未达项；工程没有改数值补齐。", "",
        "## 复现与边界", "", "```powershell",
        "python -m scripts.balance.checkpoints",
        "python -m scripts.balance.slots_report --prepare-baseline",
        *[f"python -X utf8 -m scripts.balance.slots --suite {suite} --workers 8 --output eval/reports/slots-{suite}.json" for suite in current],
        "# 在 .tmp-test/032-baseline 中对相同四套suite运行同一命令，使用 --legacy，输出至主仓库的 slots-<suite>-baseline.json",
        "python -m scripts.balance.slots_report", "```", "",
        "N=500路线的单组标准误上界约2.24pp，N=2000单场约1.12pp；固定策略/条件模拟不能代表所有人类策略或自由行动。没有付费API或外网请求。", "",
        "JSON的指纹保留结果落盘时的源文件版本；随后补齐了旧存档快照/基础攻击及同行者说明的刷新，并给控制脚本增加仅供旧引擎使用的--legacy开关。这些不改变本轮模拟调用的战斗逻辑或采样策略，未改写历史指纹。", "",
        "输入与结果：" + "、".join(f"[{suite}](slots-{suite}.json) / [旧引擎](slots-{suite}-baseline.json)" for suite in current), ""]
    (REPORTS / "balance-2026-10-15-slots.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
