"""Offline paired-seed companion comparison for spec 033."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any
from unittest.mock import patch

from host import combat, state
from . import battlefield, checkpoints, sim

CHARACTERS = ("hero", "cleric", "mage", "thief")
BATTLEFIELD = ("bone_field", "ghoul_marsh", "grave_chapel")
OUTSIDE = {
    "forest": ("dark_forest_loc", "lost_goblin_crossroads", "forest_wolves", "slime_ambush_one", "slime_ambush_two", "slime_king_battle",
               "goblin_fort", "goblin_fort_first_second", "goblin_fort_second_right", "goblin_fort_second_left",
               "goblin_fort_third_guards", "goblin_fort_fourth", "goblin_fort_chest_fight",
               "cave_heat_corridor", "cave_lava_room", "cave_crystal_corridor", "cave_prism_tree"),
    "village": ("village_fire_slime", "village_fire_elemental", "ice_elemental_encounter", "frost_wolf_battle"),
    "dragon_valley": ("valley_entrance", "valley_ledge", "xanxus_phantom_battle", "dragon_valley_loc"),
    "final": ("draco_battle",),
}
COMPANIONS = ("none", "robin", "blue_robed_mage", "fire_bat_dragon", "fire_bat_empowered", "mina", "paladin_liese")
SEARCH_VARIANTS = (("2d5", .2), ("2d4", .2), ("2d4", .25), ("2d5", .15), ("2d6", .1), ("1d10", .2))


def trial(template: dict[str, Any], companion: str, seed: int) -> dict[str, Any]:
    pack = template["scenario_pack"]
    session = deepcopy(template, {id(pack): pack})
    state._set_companion(session, None if companion == "none" else "fire_bat_dragon" if companion == "fire_bat_empowered" else companion)
    session["flags"]["fire_bat_empowered"] = companion == "fire_bat_empowered"
    rng = random.Random(seed)
    start_hp = session["character"]["hp"]
    session["combat_start_requested"] = True
    with patch.object(combat, "random", rng):
        if not combat.ensure_combat_started(session):
            raise ValueError(f"No combat at {state.current_location_id(session)}")
        while combat.combat_is_active(session):
            action, target = sim.choose_action(session, "heuristic", purify=False)
            combat.perform_combat_action(session, action["type"], action["id"], target, rng=rng)
    battle = session["combat"]
    return dict(won=battle["status"] == "victory", hp_loss=max(0, start_hp - session["character"]["hp"]),
                rounds=battle["round"], status=battle["status"])


def templates(pack: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    cp = checkpoints.generate()
    result = {}
    for character in CHARACTERS:
        base = battlefield.forest_exit(pack, cp, character)
        for location in BATTLEFIELD:
            session = deepcopy(base, {id(pack): pack})
            state.apply_state_delta(session, {"current_location": location}, allow_world_transition=True)
            result[location, character] = session
        for locations in OUTSIDE.values():
            for location in locations:
                result[location, character] = sim.prepare_session(pack, location, character, cp, companion=False)
    return result


def evaluate(pack: dict[str, Any], n: int, seed: int, *, only_battlefield: bool = False) -> dict[str, Any]:
    rows = []
    starts = templates(pack)
    for (location, character), template in starts.items():
        if only_battlefield and location not in BATTLEFIELD:
            continue
        companions = ("none", "paladin_liese") if location in BATTLEFIELD else COMPANIONS
        for companion in companions:
            trials = [trial(template, companion, sim.trial_seed(seed, location, character, index)) for index in range(n)]
            rows.append(dict(location=location, character=character, companion=companion, n=n,
                             win_rate=mean(t["won"] for t in trials), hp_loss=mean(t["hp_loss"] for t in trials),
                             rounds=mean(t["rounds"] for t in trials),
                             nonterminal=sum(t["status"] not in {"victory", "defeat"} for t in trials)))
        print(location, character, {r["companion"]: round(r["win_rate"], 3) for r in rows if r["location"] == location and r["character"] == character}, flush=True)
    comparisons = []
    for (location, character), template in starts.items():
        candidates = [r for r in rows if r["location"] == location and r["character"] == character]
        if not candidates:
            continue
        by_id = {r["companion"]: r for r in candidates}
        baseline, liese = by_id["none"], by_id["paladin_liese"]
        row = dict(location=location, character=character, baseline=baseline["win_rate"], liese=liese["win_rate"],
                   uplift_pp=100*(liese["win_rate"]-baseline["win_rate"]), baseline_hp_loss=baseline["hp_loss"],
                   liese_hp_loss=liese["hp_loss"], hp_loss_reduction=1-liese["hp_loss"]/baseline["hp_loss"] if baseline["hp_loss"] else None)
        if location not in BATTLEFIELD:
            best = max((r for r in candidates if r["companion"] not in {"none", "paladin_liese"}), key=lambda r: r["win_rate"])
            row.update(best=best["companion"], best_rate=best["win_rate"], excess_pp=100*(liese["win_rate"]-best["win_rate"]))
        comparisons.append(row)
    return dict(n=n, seed=seed, rows=rows, comparisons=comparisons,
                liese=next(c for c in pack["companions"] if c["id"] == "paladin_liese"))


def markdown(result: dict[str, Any]) -> str:
    healing, attack = result["liese"]["round_start_effects"]
    lines = ["# 033 リーゼ平衡评测", "", f"N={result['n']}／组合，seed={result['seed']}；四职业；离线真实引擎、heuristic、有限背包、配对随机种子。",
        f"本次リーゼ：半血以下回复{healing['max_hp_ratio']:.0%}，否则{attack['damage']} holy；七种不死标签及统一holy抗性1.5。",
        "", "## 口径与推断", "",
        "- 古戦場三场各自从可达的森出口Lv2检查点开始，HP/MP/SP全满、无诅咒，不预取墓守外套，不执行潜行；独立强制战斗，避免只统计通关者的幸存偏差。",
        "- HP损失=开战HP减战斗结束HP（最低0），包含死亡样本，结算奖励与自动移动前采样；这是净损失，包含职业/物品/同行者的回复。",
        "- 城外复用既有逐战可达检查点与背包，逐战补满，不表示整章连续通关率；逐职业逐战比较胜率贡献。同行者强制切换以隔离效果，包含火コウモリ竜普通及虹晶强化两种状态。",
        "- 不将Xanxus必败剧情战及替换玩家、禁用同行者的ワーロック救援算作普通比较。最终战采用draco_battle完整形态流程。",
        "- 同一组合与对照共享初始随机种子；同行者会消耗不同随机数，不能解释为完全相同的逐次骰序列。经验胜率存在抽样误差，+3pp边界应结合样本量复核。",
        "", "## 古戦場", "", "|职业|战斗|无同行胜率|リーゼ胜率|提升pp|无同行HP损失|リーゼHP损失|损失降低|", "|---|---|---:|---:|---:|---:|---:|---:|"]
    issues = []
    for row in result["comparisons"]:
        if row["location"] not in BATTLEFIELD:
            continue
        reduction = row["hp_loss_reduction"]
        lines.append(f"|{row['character']}|{row['location']}|{row['baseline']:.1%}|{row['liese']:.1%}|{row['uplift_pp']:+.1f}|{row['baseline_hp_loss']:.2f}|{row['liese_hp_loss']:.2f}|{reduction:.1%}|" if reduction is not None else f"|{row['character']}|{row['location']}|{row['baseline']:.1%}|{row['liese']:.1%}|{row['uplift_pp']:+.1f}|0|0|不适用（基准零损失）|")
        if row["location"] == "grave_chapel" and row["baseline"] < 1 and row["uplift_pp"] < 10-1e-9:
            issues.append(f"{row['character']}骑士战提升{row['uplift_pp']:.1f}pp，未达10pp；基准{row['baseline']:.1%}。")
    lines += ["", "三场合计平均净损失：", ""]
    for character in CHARACTERS:
        rows = [r for r in result["comparisons"] if r["location"] in BATTLEFIELD and r["character"] == character]
        before, after = mean(r["baseline_hp_loss"] for r in rows), mean(r["liese_hp_loss"] for r in rows)
        lines.append(f"- {character}: {before:.2f} → {after:.2f}，降低{1-after/before:.1%}。" if before else f"- {character}: 基准零损失。")
        if before and 1-after/before < .3:
            issues.append(f"{character}古戦場三场平均HP损失降低{1-after/before:.1%}，未达30%。")
    lines += ["", "## 城外（现有最强同行者 +3pp 上限）", "", "|职业|战斗|无同行|リーゼ|现有最强|最强胜率|超出pp|", "|---|---|---:|---:|---|---:|---:|"]
    for r in result["comparisons"]:
        if r["location"] in BATTLEFIELD:
            continue
        lines.append(f"|{r['character']}|{r['location']}|{r['baseline']:.1%}|{r['liese']:.1%}|{r['best']}|{r['best_rate']:.1%}|{r['excess_pp']:+.1f}|")
        if r["excess_pp"] > 3+1e-9:
            issues.append(f"{r['character']}/{r['location']}超出现有最强{r['excess_pp']:.1f}pp。")
    lines += ["", "## 未达标与设计待办", "", *[f"- TODO(design): {issue}" for issue in issues]]
    if not issues:
        lines.append("全部可计算目标通过；基准零HP损失的单场无法计算相对降幅。")
    lines += ["", "只调リーゼ自己的回复比例与伤害骰；未改现有敌人（不死标签及holy统一除外）或其他同行者数值。原始每组统计见同名JSON。",
              "调参过程与候选比较见 [调参记录](balance-2026-10-17-liese-tuning.md)。", "", "## 复现", "", "```powershell",
              f"python -m scripts.balance.liese --n {result['n']} --seed {result['seed']}", "```", "", "指纹：", ""]
    lines += [f"- {name}: `{digest}`" for name, digest in result.get("fingerprints", {}).items()]
    return "\n".join(lines) + "\n"


def search(pack: dict[str, Any], n: int, seed: int, variants: tuple[tuple[str, float], ...] = SEARCH_VARIANTS) -> dict[str, Any]:
    starts = templates(deepcopy(pack))
    rows = []
    for damage, ratio in variants:
        for (location, character), template in starts.items():
            if location not in {*BATTLEFIELD, "valley_ledge", "goblin_fort_fourth", "xanxus_phantom_battle"}:
                continue
            ally = next(c for c in template["scenario_pack"]["companions"] if c["id"] == "paladin_liese")
            ally["round_start_effects"][0]["max_hp_ratio"] = ratio
            ally["round_start_effects"][1]["damage"] = damage
            trials = [trial(template, "paladin_liese", sim.trial_seed(seed, location, character, i)) for i in range(n)]
            rows.append(dict(damage=damage, heal_ratio=ratio, location=location, character=character,
                             win_rate=mean(t["won"] for t in trials), hp_loss=mean(t["hp_loss"] for t in trials)))
        print(damage, ratio, "complete", flush=True)
    return dict(n=n, seed=seed, rows=rows)


def parse_variant(value: str) -> tuple[str, float]:
    try:
        damage, ratio = value.split(":")
        amount = float(ratio)
        if not re.fullmatch(r"[1-9]\d*d[1-9]\d*", damage) or not 0 < amount <= 1:
            raise ValueError
        return damage, amount
    except ValueError as error:
        raise argparse.ArgumentTypeError("Expected DICE:HEAL_RATIO, e.g. 2d4:0.2") from error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261017)
    parser.add_argument("--only-battlefield", action="store_true")
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--variant", action="append", type=parse_variant, help="Search only: DICE:HEAL_RATIO, repeatable")
    parser.add_argument("--output", type=Path, default=checkpoints.ROOT / "eval/reports/balance-2026-10-17-liese")
    args = parser.parse_args()
    if args.n < 1:
        parser.error("--n must be positive")
    if args.search:
        result = search(state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO), args.n, args.seed,
                        tuple(args.variant) if args.variant else SEARCH_VARIANTS)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return
    result = evaluate(state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO), args.n, args.seed, only_battlefield=args.only_battlefield)
    result["fingerprints"] = {str(p.relative_to(checkpoints.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (Path(__file__), checkpoints.DEFAULT_SCENARIO, checkpoints.ROOT / "host/combat.py")}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
