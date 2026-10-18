"""Offline chapter cash-flow accounting and the existing 031 battle-economy gate."""
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
from scripts.scenario.loot_economy import LOOT
from . import ch3_routes, checkpoints, economy, gorge, rewards, route, sim


OUTPUT = checkpoints.ROOT / "eval/reports/economy-2026-10-18-loot"
FIGHT_ACTIONS = {"bone_field": "fight_skeleton_soldiers", "ghoul_marsh": "fight_ghoul",
                 "gorge_rockfall_path": "fight_gorge_rockfall_path", "gorge_giant_path": "fight_gorge_giant_path",
                 "gorge_worm_lair": "fight_gorge_worm_lair", "valley_entrance": "fight_ash_wraiths"}


def loot_inventory(session: dict[str, Any]) -> Counter:
    return Counter({i["id"]: i.get("quantity", 1) for i in session["character"]["inventory"] if i.get("category") == "loot"})


def settle(session: dict[str, Any], chapter: int, start_gold: int, rest_cost: int) -> dict[str, Any]:
    actor = session["character"]
    prices = {i["id"]: i["sell_price"] for i in session["scenario_pack"]["items"] if i.get("category") == "loot"}
    loot = loot_inventory(session)
    value = sum(quantity * prices[item] for item, quantity in loot.items())
    cash = actor["gold"] - start_gold
    # Cash-flow budget: reserve two herbs at the undiscounted 10G, without inventing shop stock or adding healing.
    herb_budget = 20
    state.apply_state_delta(session, {"gold_change": value - herb_budget,
        "inventory_remove": [{"name": i["name"], "quantity": i.get("quantity", 1)}
                             for i in actor["inventory"] if i.get("category") == "loot"]})
    return dict(chapter=chapter, start_gold=start_gold, end_gold=actor["gold"], cash_change=cash,
                rest_cost=rest_cost, loot=dict(loot), loot_value=value, herb_budget=herb_budget,
                net=cash + value - herb_budget, ceiling_net=cash + sum(loot.values()) * 20 - herb_budget)


def early_trial(pack: dict[str, Any], sources: list[dict[str, Any]], character: str, seed: int) -> dict[str, Any]:
    session = checkpoints.fresh_session(pack, character)
    rng = random.Random(seed)
    ledgers, battles = [], []
    start, rest_cost = session["character"]["gold"], 0
    with patch.object(combat, "random", rng):
        for source in sources:
            if state.current_location_id(session) != source["location"]:
                raise ValueError(f"Route diverged before {source['step']}")
            if not ledgers and source["location"] == "dark_forest_loc":
                ledgers.append(settle(session, 1, start, 0))
                start = session["character"]["gold"]
            if source["step"] == "@victory":
                battle = route.fight(session, "heuristic", rng)
                battles.append(battle)
                if not battle["continue"]:
                    return dict(ledgers=ledgers, failed_at=battle["encounter"], battles=battles)
            else:
                before = session["character"]["gold"]
                checkpoints.replay_step(session, source["step"])
                if source["step"] == "rest_at_inn":
                    rest_cost += before - session["character"]["gold"]
            rewards.consume_boosts(session)
        ledgers.append(settle(session, 2, start, rest_cost))
    return dict(ledgers=ledgers, failed_at=None, battles=battles)


def later_trial(template: dict[str, Any], path: str, policy: str, seed: int) -> dict[str, Any]:
    session = ch3_routes.prepare(template, dict(path=path, prepared=False, cursed=False, companion="none"))
    rng = random.Random(seed)
    start = session["character"]["gold"]
    rest_cost = 0
    chapter, ledgers, battles, steps = 3, [], [], []
    with patch.object(combat, "random", rng):
        for _ in range(100):
            location = state.current_location_id(session)
            if session.get("game_over"):
                break
            if location == "village" and chapter == 3:
                rest = route.rest_if_needed(session)
                if rest:
                    rest_cost += rest["cost"]
                ledgers.append(settle(session, 3, start, rest_cost))
                start, rest_cost, chapter = session["character"]["gold"], 0, 4
            encounter = combat._encounter_for_session(session, session["scenario_pack"])
            if session.get("combat_start_requested") or (encounter.get("auto_start", True) and encounter["enemy_ids"]):
                battle = route.fight(session, "heuristic", rng)
                battles.append(battle)
                if not battle["continue"]:
                    return dict(ledgers=ledgers, failed_at=location, battles=battles, steps=steps)
                rewards.consume_boosts(session)
                if location == "dragon_valley_loc":
                    ledgers.append(settle(session, 4, start, rest_cost))
                    start = session["character"]["gold"]
                    for identifier in ("return_to_castle_report", "enter_festival_town", "go_report_hall", "report_normally"):
                        steps.append(ch3_routes.action(session, identifier, rng))
                    ledgers.append(settle(session, 5, start, 0))
                    return dict(ledgers=ledgers, failed_at=None, battles=battles, steps=steps)
                continue
            identifier = ch3_routes.next_action(session, False)
            if policy == "fight" and location == "village_approach":
                identifier = "enter_burning_village_directly"
            if policy == "fight" and location in FIGHT_ACTIONS:
                candidate = state.resolve_action(session, action_id=FIGHT_ACTIONS[location])
                if candidate and state.action_requirement_status(candidate, session)[0]:
                    identifier = candidate["id"]
            steps.append(ch3_routes.action(session, identifier, rng))
            if not session.get("combat_start_requested"):
                rewards.consume_boosts(session)
    raise RuntimeError("Chapter economy route did not terminate")


def _route_job(job: tuple[Any, ...]) -> dict[str, Any]:
    template, character, path, policy, n, seed = job
    chapters: dict[int, list[dict[str, Any]]] = {}
    failures: Counter = Counter()
    samples = {}
    pack = template["scenario_pack"]
    for index in range(n):
        trial_seed = sim.trial_seed(seed, "038-economy", character, index)
        trial = (early_trial(pack, template["checkpoint_sources"], character, trial_seed) if path == "chapters12" else
                 later_trial(template, path, policy, trial_seed))
        for ledger in trial["ledgers"]:
            chapters.setdefault(ledger["chapter"], []).append(ledger)
        if trial["failed_at"]:
            failures[trial["failed_at"]] += 1
        samples.setdefault(trial["failed_at"] or "complete", dict(index=index, seed=trial_seed, **trial))
    rows = []
    for chapter, ledgers in chapters.items():
        totals: Counter = Counter()
        for ledger in ledgers:
            totals.update(ledger["loot"])
        rows.append(dict(chapter=chapter, finished=len(ledgers),
            **{key: mean(row[key] for row in ledgers) for key in
               ("start_gold", "end_gold", "cash_change", "rest_cost", "loot_value", "herb_budget", "net", "ceiling_net")},
            min_net=min(row["net"] for row in ledgers), max_net=max(row["net"] for row in ledgers),
            loot_per_finish={key: value / len(ledgers) for key, value in totals.items()}))
    return dict(character=character, path=path, policy=policy, n=n, chapters=rows, failures=dict(failures), samples=samples)


def _battle_job(job: tuple[Any, ...]) -> dict[str, Any]:
    pack, cp, location, character, n, seed = job
    prices = economy.prices(pack)
    prices.update({i["id"]: i["sell_price"] for i in pack["items"] if i.get("category") == "loot"})
    row = economy.measure(pack, cp, location, character, n, seed, prices)
    encounter = next(l for l in pack["locations"] if l["id"] == location)["combat"]
    bonus = encounter.get("victory_gold_bonus", 0)
    row["revenue_after"] = row["win_rate"] * (row["reward_on_victory_before"] + bonus)
    row["gold_bonus"] = bonus
    row["passed"] = row["revenue_after"] + 1e-9 >= 1.3 * row["conservative_cost"]
    return row


def markdown(result: dict[str, Any]) -> str:
    lines = ["# 038 战利品经济检查（2026-10-18）", "",
        "**每章净增≥30G未达标，且仅将战利品售价调到20G仍无法达标。已停止调价，保留038表中的原售价；不修改敌人、现有奖励、商店库存或路线设计。**", "",
        f"四职业；连续路线每组N={result['n']}，031逐战复核N={result['battle_n']}；seed={result['seed']}。全部离线。", "",
        "## 口径与边界", "",
        "- 第1–2章从角色模板和国王开场奖励开始，重放037起点的既有路线，前序战斗改为真实heuristic结算：森林入口、ゴブリン砦右路和警卫、归还箱子、森狼、回宿屋支付10G休息。不额外刷怪或交新收集任务。",
        "- 第3章起沿用037的可达森の出口检查点，无同行者、无诅咒、未购买城塞准备。前两章已持有的战利品先换算为现金并预留40G薬草预算，不计入第三章收益；这不是从第一章生还样本继续跑的总体通关率。",
        "- 037组原样保留潜行／绕行；fight组把沿途可选择的战斗改为正面战斗，村选择直接进入并迎战火の精霊。塔／营地免费恢复、永久品使用、战斗heuristic保持原策略。",
        "- 第3章在避難所执行既有HP<70%的5G休息后结算；第4章到イグニス胜利；第5章补上原有回城正常报告结局，未额外选择屋敷、宿袭或ドラコ支线。只卖category=loot，不卖原装备或消耗品。",
        "- 这是现金流预算：逐章按引擎sell_price换算并移除全部战利品、预留薬草2×10G，未凭空补商店库存，也未把预算假充为新增可用药草。战斗背包仅含原有获得和消耗；交易可达性与库存限制见下面待办。",
        "- 净变动=章节实际金币变化（含付费休息）+战利品卖价−20G；20G上限列仅重估同一批掉落，不改变掉落数或战斗。统计只针对活着完成该章的样本，finished/N和失败地点同时给出，不把死亡当成零成本通关。",
        "- 准备组整套195G属于额外支出，只会进一步降低第三章净值；收集任务不强制完成，也不把同一批依赖品同时算成交付和卖出。", "",
        "## 不可达证明与设计待办", "",
        "1. 村路线第三章最多打一只ファイアスライム（6G）或火の精霊（12G+现有10G奖励），均固定掉一件残り火の欠片；慎重接近的大成功还会绕过战斗。即使卖20G、完全不休息，两种战斗的净值上限分别为6G／22G，距离30G仍差24G／8G；即使按最低药草8G采购，上限也只有10G／26G。",
        "2. 这条路线只取得一件残り火の欠片，不能完成需要两件的炊き出しの火。要求回头增加洞窟战斗、改变数量、原金币奖励或目标均超出038的调价权限。",
        "3. 第5章直接回城报告没有金币或战利品收入，预留两株薬草后净值−20G，缺口50G；ドラコ／ヴァイス本身也明确不掉战利品。是否要求所有路线每章达标、将支线收入计入或改用累计预算，需要设计决定。",
        "4. 实际采购还有限制：サラ的薬草总库存3株；037路线不一定救下ガルド，普通村店不卖薬草。‘每章实际买2株’不能由当前路线和库存保证。本报告没有通过补库存或换商品规避问题。", "",
        "## 每章金币变化", "", "|职业|路线|策略|章|完成/N|原金币净变|其中休息费|战利品|薬草预算|净变化|20G上限净变化|最小～最大净值|",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for group in result["routes"]:
        for row in group["chapters"]:
            lines.append(f"|{group['character']}|{group['path']}|{group['policy']}|{row['chapter']}|{row['finished']}/{group['n']}|"
                f"{row['cash_change']:.2f}|{row['rest_cost']:.2f}|{row['loot_value']:.2f}|{row['herb_budget']:.0f}|"
                f"{row['net']:+.2f}|{row['ceiling_net']:+.2f}|{row['min_net']:+.0f}～{row['max_net']:+.0f}|")
    lines += ["", "## 031 非主线战斗复核", "",
        "沿用031的真实引擎、检查点、消耗品买价及更保守的可重复付费休息成本；本次把战利品按卖价计入收益。永久品不估值；胜率乘收益，败北消耗计成本。包含035峡谷新增遭遇，未调用fit或更改金币。", "",
        "|遭遇|职业|胜率|保守成本|期望收益|收益/成本|≥1.3|", "|---|---|---:|---:|---:|---:|---|"]
    for row in result["battles"]:
        ratio = f"{row['revenue_after']/row['conservative_cost']:.2f}" if row["conservative_cost"] else "成本0"
        lines.append(f"|{row['location']}|{row['character']}|{row['win_rate']:.2%}|{row['conservative_cost']:.2f}|{row['revenue_after']:.2f}|{ratio}|{row['passed']}|")
    failed = [r for r in result["battles"] if not r["passed"]]
    lines += ["", f"031复核未通过：{len(failed)}/{len(result['battles'])}组。", "",
        "## 复现", "", "```powershell",
        f"python -m scripts.balance.loot_economy --n {result['n']} --battle-n {result['battle_n']} --seed {result['seed']} --workers {result['workers']}",
        "```", "", "退出码1表示经济目标未达标，不是执行异常。JSON包含每章样本数、掉落数量、失败地点、首个完整胜败样本、031消耗／快照与文件指纹。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=2000)
    parser.add_argument("--battle-n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261018)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if min(args.n, args.battle_n, args.workers) < 1:
        parser.error("n, battle-n and workers must be positive")
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    templates = {c: ch3_routes.starting_checkpoint(pack, cp, c) for c in ch3_routes.CHARACTERS}
    jobs = [(template, character, "chapters12", "fight", args.n, args.seed) for character, template in templates.items()]
    for character, template in templates.items():
        later = deepcopy(template, {id(pack): pack})
        settle(later, 0, later["character"]["gold"], 0)
        state.apply_state_delta(later, {"gold_change": -20})
        jobs.extend((later, character, path, policy, args.n, args.seed)
                    for path in ("village", "battlefield", "gorge") for policy in ("037", "fight"))
    result = dict(n=args.n, battle_n=args.battle_n, seed=args.seed, workers=args.workers, routes=[], battles=[],
        prices={identifier: price for identifier, (_, price, _, _) in LOOT.items()},
        checkpoint_sources={c: t["checkpoint_sources"] for c, t in templates.items()})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for row in gorge._map_jobs(_route_job, jobs, args.workers):
        result["routes"].append(row)
        print(row["character"], row["path"], row["policy"], [(r["chapter"], round(r["net"], 2)) for r in row["chapters"]], flush=True)
    jobs = [(pack, cp, loc["id"], c, args.battle_n, args.seed) for loc in pack["locations"]
            if loc.get("combat", {}).get("encounter_class") and loc["id"] not in economy.EXCLUDED
            for c in ch3_routes.CHARACTERS]
    for row in gorge._map_jobs(_battle_job, jobs, args.workers):
        result["battles"].append(row)
        print("battle", row["location"], row["character"], row["passed"], flush=True)
    result["fingerprints"] = {p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__), Path(ch3_routes.__file__), Path(checkpoints.__file__), Path(economy.__file__), Path(sim.__file__),
         Path(route.__file__), Path(combat.__file__), Path(state.__file__), checkpoints.DEFAULT_SCENARIO,
         checkpoints.DEFAULT_SCENARIO.with_name("dragon_rpg_hybrid.json")]}
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    return int(any(row["net"] < 30 for group in result["routes"] for row in group["chapters"])
               or any(not row["passed"] for row in result["battles"]))


if __name__ == "__main__":
    raise SystemExit(main())
