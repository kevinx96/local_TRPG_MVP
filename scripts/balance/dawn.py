"""Offline paired-seed weapon comparisons for spec 034; never tune scenario values."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any
from unittest.mock import patch

from host import combat, state
from host.item_mechanics import equipped_basic_attack_followups, equipped_items
from scripts.scenario.oaksdawn_quests import WEAPONS
from . import battlefield, checkpoints, liese, sim


FINALS = ("dragon_valley_loc", "draco_battle")


def equip(template: dict[str, Any], identifier: str) -> dict[str, Any]:
    pack = template["scenario_pack"]
    session = deepcopy(template, {id(pack): pack})
    item = next(i for i in pack["items"] if i["id"] == identifier)
    state.apply_state_delta(session, {"inventory_add": [{**item, "quantity": 1}], "equip_item": item["name"]})
    return session


def trial(template: dict[str, Any], seed: int) -> dict[str, Any]:
    pack = template["scenario_pack"]
    session = deepcopy(template, {id(pack): pack})
    state._set_companion(session, None)
    rng = random.Random(seed)
    start_hp = session["character"]["hp"]
    actions: Counter = Counter()
    session["combat_start_requested"] = True
    with patch.object(combat, "random", rng):
        if not combat.ensure_combat_started(session):
            raise ValueError(state.current_location_id(session))
        while combat.combat_is_active(session):
            action, target = sim.choose_action(session, "heuristic", purify=False)
            actions[action["type"]] += 1
            combat.perform_combat_action(session, action["type"], action["id"], target, rng=rng)
    battle = session["combat"]
    return dict(won=battle["status"] == "victory", hp_loss=max(0, start_hp - session["character"]["hp"]),
                rounds=battle["round"], status=battle["status"], basic_attacks=actions["attack"])


def basic_estimates(session: dict[str, Any], location: str) -> dict[str, float]:
    pack = session["scenario_pack"]
    actor = session["character"]
    attack = {**actor["combat"]["basic_attack"], "type": "attack", "followups": equipped_basic_attack_followups(actor)}
    identifiers = ("draco_human", "draco_dragon") if location == "draco_battle" else tuple(
        combat._encounter_for_session(session, pack)["enemy_ids"])
    return {identifier: sim.expected_damage(attack, actor, next(e for e in pack["enemies"] if e["id"] == identifier),
                                           combat._combat_rules(session)) for identifier in dict.fromkeys(identifiers)}


def evaluate(pack: dict[str, Any], n: int, seed: int) -> dict[str, Any]:
    cp = checkpoints.generate()
    rows = []
    for character in liese.CHARACTERS:
        forest = battlefield.forest_exit(pack, cp, character)
        for location in (*liese.BATTLEFIELD, *FINALS):
            if location in liese.BATTLEFIELD:
                template = deepcopy(forest, {id(pack): pack})
                state.apply_state_delta(template, {"current_location": location}, allow_world_transition=True)
                variants = {"baseline": template, "dawn": equip(template, WEAPONS[character][0])}
            else:
                template = sim.prepare_session(pack, location, character, cp, companion=False)
                variants = {"ice_iron_greatsword": equip(template, "ice_iron_greatsword"),
                            "ice_katana": equip(template, "ice_katana"), "dawn": equip(template, WEAPONS[character][0])}
            for variant, start in variants.items():
                trials = [trial(start, sim.trial_seed(seed, location, character, index)) for index in range(n)]
                rows.append(dict(location=location, character=character, weapon=variant, n=n,
                    win_rate=mean(t["won"] for t in trials), hp_loss=mean(t["hp_loss"] for t in trials),
                    rounds=mean(t["rounds"] for t in trials),
                    basic_attacks=mean(t["basic_attacks"] for t in trials), basic_estimates=basic_estimates(start, location),
                    nonterminal=sum(t["status"] not in {"victory", "defeat"} for t in trials),
                    equipment=[i["name"] for i in equipped_items(start["character"])],
                    level=start["character"]["level"], max_hp=start["character"]["max_hp"]))
            print(character, location, {r["weapon"]: round(r["win_rate"], 3) for r in rows
                                       if r["location"] == location and r["character"] == character}, flush=True)
    return dict(n=n, seed=seed, rows=rows)


def markdown(result: dict[str, Any]) -> str:
    lines = ["# 034 暁光の武器平衡评测", "", f"每组合 N={result['n']}，seed={result['seed']}；四职业、真实确定性战斗引擎、离线 heuristic 策略。",
        "", "## 方法与推断", "",
        "- 古戦場沿用033的森出口Lv2可达检查点；三个固定战斗分别补满HP/MP/SP后测试，不预取墓守外套，不潜行。",
        "- 最终战沿用现有逐战可达检查点，draco_battle包含ドラコ与ヴァイス完整形态流程；イグニス关闭净化分支。",
        "- 所有组合均无同行者，其他装备、技能与有限消耗品相同；仅替换weapon部位，保留原武器在背包。",
        "- 暁光武器通过控制变量加入，未模拟购买/任务的时间和经济成本；不是从游戏开局的路线胜率。冰武器同时列氷鉄の大剣与氷の太刀，避免任意指定唯一对照。",
        "- HP损失为开战至战斗结束的净损失，包含死亡、技能/道具回复；不应用战后奖励。相同初始随机种子，行动数改变后骰序列不再逐次相同。",
        "- spec未给“明显变容易”的数值阈值；下表直接报告胜率、净损失与回合数，不自设验收线。胜率为抽样估计。",
        "", "## 古戦場：现有武器 / 暁光", "", "|职业|战斗|现有胜率|暁光胜率|变化pp|现有HP损失|暁光HP损失|现有回合|暁光回合|",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    issues = []
    for character in liese.CHARACTERS:
        for location in liese.BATTLEFIELD:
            by = {r["weapon"]: r for r in result["rows"] if r["character"] == character and r["location"] == location}
            a, b = by["baseline"], by["dawn"]
            lines.append(f"|{character}|{location}|{a['win_rate']:.1%}|{b['win_rate']:.1%}|{100*(b['win_rate']-a['win_rate']):+.1f}|{a['hp_loss']:.2f}|{b['hp_loss']:.2f}|{a['rounds']:.2f}|{b['rounds']:.2f}|")
            if b["win_rate"] <= a["win_rate"] and b["hp_loss"] >= a["hp_loss"] and b["rounds"] >= a["rounds"]:
                issues.append(f"{character}/{location}：三项指标均未改善。")
    lines += ["", "## 最终战：冰武器 / 暁光", "", "|职业|战斗|武器|胜率|HP损失|回合|", "|---|---|---|---:|---:|---:|"]
    for character in liese.CHARACTERS:
        for location in FINALS:
            rows = [r for r in result["rows"] if r["character"] == character and r["location"] == location]
            for row in rows:
                lines.append(f"|{character}|{location}|{row['weapon']}|{row['win_rate']:.1%}|{row['hp_loss']:.2f}|{row['rounds']:.2f}|")
            dawn = next(r for r in rows if r["weapon"] == "dawn")
            for ice in (r for r in rows if r["weapon"] != "dawn"):
                uplift = 100*(dawn["win_rate"]-ice["win_rate"])
                if uplift > 0:
                    issues.append(f"{character}/{location}：暁光胜率比{ice['weapon']}高{uplift:.1f}pp，未满足“不能更好”。")
                elif uplift == 0 and dawn["hp_loss"] < ice["hp_loss"]:
                    issues.append(f"{character}/{location}：胜率持平，但暁光净HP损失比{ice['weapon']}少{ice['hp_loss']-dawn['hp_loss']:.2f}，请确认是否符合目标。")
    lines += ["", "## 普通攻击对照与策略影响", "",
        "伤害列复用现有heuristic的期望伤害估算（骰子均值、命中、抗性、减伤及补助追击），不是完整骰子分布的精确数学期望，也不含战中状态。",
        "平均普通攻击次数来自上面的实际模拟。普通攻击次数很少或为零时，强技能/道具会掩盖武器差异。",
        "", "|职业|战斗|武器|平均普通攻击次数|每次普通攻击伤害估算（敌人）|", "|---|---|---|---:|---|"]
    for row in result["rows"]:
        estimates = "；".join(f"{enemy}: {amount:.2f}" for enemy, amount in row["basic_estimates"].items())
        lines.append(f"|{row['character']}|{row['location']}|{row['weapon']}|{row['basic_attacks']:.2f}|{estimates}|")
    lines += ["", "## 目标偏离", "", *[f"- TODO(design): {issue}" for issue in issues]]
    if not issues:
        lines.append("本次抽样未发现目标偏离；“明显”的定性验收仍由设计负责人判断。")
    lines += ["", "未调整任何既有敌人强度或spec武器数值。原始统计、装备与等级见同名JSON。",
              f"非终局样本：{sum(r['nonterminal'] for r in result['rows'])}。", "", "## 复现", "", "```powershell",
              f"python -m scripts.balance.dawn --n {result['n']} --seed {result['seed']}", "```", "", "代码与数据指纹：", ""]
    lines += [f"- {path}: `{digest}`" for path, digest in result["fingerprints"].items()]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument("--output", type=Path, default=checkpoints.ROOT / "eval/reports/balance-2026-10-17-dawn")
    args = parser.parse_args()
    if args.n < 1:
        parser.error("--n must be positive")
    result = evaluate(state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO), args.n, args.seed)
    paths = [Path(__file__), checkpoints.DEFAULT_SCENARIO, *[checkpoints.ROOT / p for p in
             ("host/combat.py", "host/state.py", "host/item_mechanics.py", "scripts/balance/sim.py", "scripts/balance/liese.py", "scripts/balance/checkpoints.py")]]
    result["fingerprints"] = {str(p.relative_to(checkpoints.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
