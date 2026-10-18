"""Offline, continuous chapter-three route comparison through the Ignis result."""
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

from host import combat, shops, state
from . import checkpoints, gorge, liese, rewards, route, sim

CHARACTERS = liese.CHARACTERS
COMPANIONS = (*liese.COMPANIONS, gorge.ELIO)
COUNTERS = {"battlefield": "paladin_liese", "gorge": gorge.ELIO}
OUTPUT = checkpoints.ROOT / "eval/reports/balance-2026-10-18-ch3-routes"


def starting_checkpoint(pack: dict[str, Any], cp: dict[str, Any], character: str) -> dict[str, Any]:
    steps = [s["step"] for s in cp["encounters"]["forest_wolves"]["characters"][character]["sources"]]
    index = steps.index("ignore_lost_goblin:success")
    steps[index:index + 2] = ["help_lost_goblin", "enter_goblin_fort", "@victory", "@victory",
        "explore_fort_right", "@victory", "admit_no_password", "@victory", "@victory", "return_lost_goblin_box"]
    steps += ["@victory", "return_inn_after_forest", "go_inn", "rest_at_inn", "return_castle_from_inn", "return_forest_exit"]
    session = checkpoints.fresh_session(pack, character)
    sources = []
    for step in steps:
        sources.append(checkpoints.replay_step(session, step))
        rewards.consume_boosts(session)
    if state.current_location_id(session) != "forest_exit":
        raise ValueError("Chapter-two checkpoint did not reach forest_exit")
    session["checkpoint_sources"] = sources
    return session


def conditions() -> list[dict[str, Any]]:
    return [dict(path="village", prepared=False, cursed=False, companion=cid)
            for cid in ("none", "blue_robed_mage", "fire_bat_dragon")] + [
        dict(path=path, prepared=prepared, cursed=cursed, companion=cid)
        for path in ("battlefield", "gorge") for prepared in (False, True)
        for cursed in ((False, True) if path == "battlefield" else (False,)) for cid in COMPANIONS]


def action(session: dict[str, Any], identifier: str, rng: random.Random) -> dict[str, Any]:
    location = state.current_location_id(session)
    entry = state.resolve_action(session, action_id=identifier)
    if entry is None or not state.action_requirement_status(entry, session)[0]:
        raise ValueError(f"Unavailable action: {location}/{identifier}")
    roll = {}
    if entry.get("roll"):
        dice, dc = state.action_dice_settings(entry, session=session)
        roll = state.roll_dice(session, dice, dc, client_rolls=[rng.randint(1, 20)])
    state.apply_action_result(session, entry, roll)
    return dict(location=location, action=identifier, roll=roll)


def prepare(template: dict[str, Any], condition: dict[str, Any]) -> dict[str, Any]:
    pack = template["scenario_pack"]
    session = deepcopy(template, {id(pack): pack})
    cid = condition["companion"]
    state._set_companion(session, None if cid == "none" else "fire_bat_dragon" if cid == "fire_bat_empowered" else cid)
    session["flags"]["fire_bat_empowered"] = cid == "fire_bat_empowered"
    if condition["cursed"]:
        item = next(i for i in pack["items"] if i["id"] == "cursed_dagger")
        state.apply_state_delta(session, {"inventory_add": [{**item, "quantity": 1}]})
    steps = []

    def replay(identifier: str) -> None:
        steps.append(checkpoints.replay_step(session, identifier))

    if condition["path"] == "village":
        replay("leave_forest_for_village")
    else:
        replay("enter_old_battlefield")
        if condition["prepared"] or condition["path"] == "gorge":
            replay("battlefield_to_oaksdawn")
            if condition["prepared"]:
                replay("square_to_workshop")
                replay("shop:oaksdawn_workshop_shop:holy_silver")
                replay("forge_dawn_weapon")
                replay("shop:oaksdawn_workshop_shop:guardian_chainmail")
                shops.use_item(session, "guardian_chainmail")
                steps.append(dict(location=state.current_location_id(session), step="equip:guardian_chainmail"))
                replay("workshop_to_square")
                replay("square_to_chapel")
                replay("pray_oaksdawn")
                replay("chapel_to_square")
            if condition["path"] == "gorge":
                replay("square_to_hq")
                replay("greet_walter")
                replay("open_gorge_path")
                replay("hq_to_square")
            replay("square_to_wall")
            replay("oaksdawn_east_pass_open" if condition["path"] == "gorge" else "oaksdawn_to_battlefield")
    session["preparation_sources"] = steps
    session["event_log"] = []
    return session


def next_action(session: dict[str, Any], cursed: bool) -> str:
    location, flags = state.current_location_id(session), session["flags"]
    if location.startswith("gorge_"):
        return gorge.route_action(session)
    if location == "old_battlefield":
        return "battlefield_to_bones"
    if location == "bone_field":
        if not flags.get("passed_bone_field"):
            return "show_curse_to_skeletons" if cursed else "sneak_bone_field"
        return "bones_to_marsh" if flags.get("rested_watchtower") else "bones_to_tower"
    if location == "ruined_watchtower":
        return ("search_watchtower" if not flags.get("found_gravekeeper_cloak") else
                "rest_watchtower" if not flags.get("rested_watchtower") else "tower_to_bones")
    if location == "ghoul_marsh":
        return "marsh_to_chapel" if flags.get("passed_ghoul_marsh") else "sneak_ghoul_marsh"
    if location == "grave_chapel":
        return ("chapel_to_village" if flags.get("passed_grave_chapel") else
                "curse_pass_grave_knight" if cursed else "fight_grave_knight")
    return {"village_approach": "approach_burning_village_carefully", "burning_house": "leave_burning_house",
            "village_frozen_clue": "visit_village", "village": "go_dragon_valley",
            "valley_entrance": "sneak_through_ash", "valley_lava_bridge": "cross_lava_bridge",
            "warlock_at_nest": "continue_after_warlock", "valley_nest_gate": "enter_dragon_nest"}[location]


def trial(template: dict[str, Any], condition: dict[str, Any], seed: int) -> dict[str, Any]:
    pack = template["scenario_pack"]
    session = deepcopy(template, {id(pack): pack})
    rng = random.Random(seed)
    steps, battles, rests = [], [], []
    arrival = None
    with patch.object(combat, "random", rng):
        for _ in range(100):
            location = state.current_location_id(session)
            if session.get("game_over"):
                break
            encounter = combat._encounter_for_session(session, pack)
            if session.get("combat_start_requested") or (encounter.get("auto_start", True) and encounter["enemy_ids"]):
                if location == "dragon_valley_loc":
                    arrival = route.resources(session)
                battle = route.fight(session, "heuristic", rng)
                battles.append(battle)
                if location == "dragon_valley_loc" or not battle["continue"]:
                    return dict(completed=location == "dragon_valley_loc" and battle["status"] == "victory",
                        failed_at=None if battle["continue"] else location, terminal=battle["status"],
                        boss_arrival=arrival, battles=battles, steps=steps, rests=rests)
                rewards.consume_boosts(session)
                continue
            rest = route.rest_if_needed(session)
            if rest:
                rests.append(rest)
            steps.append(action(session, next_action(session, condition["cursed"]), rng))
            if not session.get("combat_start_requested"):
                rewards.consume_boosts(session)
    if not session.get("game_over"):
        raise RuntimeError("Continuous route exceeded its step limit")
    return dict(completed=False, failed_at=state.current_location_id(session), terminal="defeat",
                boss_arrival=arrival, battles=battles, steps=steps, rests=rests)


def _job(job: tuple[Any, ...]) -> dict[str, Any]:
    character, template, condition, n, seed = job
    staged = prepare(template, condition)
    wins = arrivals = 0
    failures: Counter = Counter()
    terminals: Counter = Counter()
    consumables: Counter = Counter()
    samples = {}
    arrival_hp = []
    for i in range(n):
        result = trial(staged, condition, sim.trial_seed(seed, "037-route", character, i))
        wins += result["completed"]
        arrivals += result["boss_arrival"] is not None
        terminals[result["terminal"]] += 1
        if result["boss_arrival"]:
            arrival_hp.append(result["boss_arrival"]["hp"])
        if not result["completed"]:
            failures[result["failed_at"]] += 1
        for battle in result["battles"]:
            consumables.update(battle["consumables"])
        samples.setdefault("victory" if result["completed"] else result["failed_at"], dict(index=i, seed=sim.trial_seed(seed, "037-route", character, i), **result))
    return dict(character=character, **condition, n=n, wins=wins, success_rate=wins/n,
        boss_arrivals=arrivals, boss_win_rate=wins/arrivals if arrivals else None,
        mean_arrival_hp=mean(arrival_hp) if arrival_hp else None, failures=dict(failures), terminals=dict(terminals),
        consumables_per_trial={k: v/n for k, v in consumables.items()}, samples=samples,
        preparation_sources=staged["preparation_sources"], start={**rewards.snapshot(staged), **route.resources(staged)})


def comparisons(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gaps, rankings, counter_rows = [], [], []
    for prepared in (False, True):
        best_by_class = []
        for character in CHARACTERS:
            rates = {r["path"]: r["success_rate"] for r in rows if r["character"] == character
                and r["companion"] == "none" and not r["cursed"]
                and r["prepared"] == (prepared if r["path"] != "village" else False)}
            if len(rates) != 3:
                continue
            spread = 100 * (max(rates.values()) - min(rates.values()))
            gaps.append(dict(character=character, prepared=prepared, rates=rates, spread_pp=spread, passed=spread <= 8 + 1e-9))
            best_by_class.append({k for k, v in rates.items() if v == max(rates.values())})
        universal = sorted(set.intersection(*best_by_class)) if len(best_by_class) == 4 else []
        rankings.append(dict(prepared=prepared, universal_best=universal, passed=not universal))
    for path, counter in COUNTERS.items():
        for prepared in (False, True):
            for cursed in ((False, True) if path == "battlefield" else (False,)):
                for character in CHARACTERS:
                    rates = {r["companion"]: r["success_rate"] for r in rows if
                        (r["character"], r["path"], r["prepared"], r["cursed"]) == (character, path, prepared, cursed)}
                    if not rates:
                        continue
                    best = max((cid for cid in rates if cid not in {"none", counter}), key=lambda cid: rates[cid])
                    counter_rows.append(dict(character=character, path=path, prepared=prepared, cursed=cursed,
                        counter=counter, uplift_pp=100*(rates[counter]-rates["none"]), best_other=best,
                        other_uplift_pp=100*(rates[best]-rates["none"]), margin_pp=100*(rates[counter]-rates[best]),
                        passed=rates[counter] > rates[best]))
    return dict(route_gaps=gaps, rankings=rankings, counters=counter_rows)


def markdown(result: dict[str, Any]) -> str:
    lines = ["# 037 第三章三条路线连续平衡（第二轮）", "",
        f"N={result['n']}／职业／条件；seed={result['seed']}；{len(result['rows'])}组，共{sum(r['n'] for r in result['rows']):,}条连续路线。完全离线。", "",
        "## 口径与推断", "",
        "- 起点为第2章结束的森の出口。复用可达检查点回放，先完成ゴブリン砦并归还箱子，再通过森林、回城支付10G休息后返回出口；Lv3、240G，四职业具体背包和全部前置动作见JSON。前置战斗假定获胜、不估算消耗，结论条件于这个检查点，不是从新游戏开始的通关率。",
        "- 原主线Lv2起点只有125G，不能支付195G整套准备；为避免凭空补钱，所有组统一采用上述砦后检查点。准备组实际购买聖銀120G、锻造30G、鎖帷子40G、礼拝堂休息5G；未准备组不购买。第二轮墓守外套仅在防具部位为空时自动装备；本轮不额外加入手动换装策略，保留原有ローブ／革の鎧或准备组鎖帷子。",
        "- 同行者和诅咒采用031/033/035既有的机制对照：起点指定同行者，诅咒组给予呪われた短剣；武器位为空的僧侶／魔法使い会自动装备，勇者／盗賊保留原武器；准备组再由锻造替换武器。第一轮‘只携带、不装备’的文字描述不准确，但两轮实际代码均为上述行为，原始JSON可核对。不计招募费用、获取诅咒代价，不能当成完整招募路线。火コウモリ竜普通／虹晶强化分别列出；其他控制包括ロビン、ミーナ、ワーロック及另一条路线的同行者。",
        "- 保留剧情中的同行者离队；村路线的ワーロック在森林出口离队，所以该组不会强行留住他。",
        "- 村路线慎重接近、离开民家；古戦場骨野潜行（诅咒放行）、塔取外套并休息、沼地潜行、骑士战（诅咒放行）；峡谷潜行、搜营地并休息、查爪痕、巨人潜行、ワーム潜行（エリオ绕过）。",
        "- 三路都汇入避難所。共同后程采用现行hp70付费休息策略、竜の谷亡霊潜行、过桥、イグニス战；不额外走冰元素／Xanxus支线，不净化。所有判定投真实d20、失败实战，HP/MP/SP、金币、背包跨战继承，永久品立即使用，无重来。",
        "- 分母始终是全部起点样本，包含提前死亡；同时列出到Boss的样本数与条件胜率。每组共享初始随机种子，同行者耗骰不同，不代表逐骰配对。判据采用样本点估计，不把抽样误差当成设计容差。",
        "- ‘三路相差≤8pp’对未准备／已准备分别比较（村路线均为未准备），主比较无诅咒；诅咒单列。同率并列最优也计入四职业共同最优。第二轮对策同行者要求严格领先所有其他同行者，相同基线下比较提升等价于比较通关率；并列判为未通过。", "",
        "## 无同行者、无诅咒", "", "|职业|城塞准备|村|古戦場|峡谷|最大差pp|≤8pp|", "|---|---|---:|---:|---:|---:|---|"]
    for r in result["comparisons"]["route_gaps"]:
        rates = r["rates"]
        lines.append(f"|{r['character']}|{r['prepared']}|{rates['village']:.2%}|{rates['battlefield']:.2%}|{rates['gorge']:.2%}|{r['spread_pp']:.2f}|{r['passed']}|")
    lines += ["", "## 本路线对策同行者", "", "|职业|路线|准备|诅咒|对策提升pp|其他最强|其提升pp|达标|", "|---|---|---|---|---:|---|---:|---|"]
    for r in result["comparisons"]["counters"]:
        lines.append(f"|{r['character']}|{r['path']}|{r['prepared']}|{r['cursed']}|{r['uplift_pp']:+.2f}|{r['best_other']}|{r['other_uplift_pp']:+.2f}|{r['passed']}|")
    baseline = result.get("baseline", {})
    if baseline:
        lines += ["", "## 第一轮对照", "", "完整第一轮数据：[报告](balance-2026-10-18-ch3-routes-round1.md)、[JSON](balance-2026-10-18-ch3-routes-round1.json)。204组起点、策略、种子和N不变；仅本轮授权内容变化。", "",
                  "|职业|准备|第一轮最大差pp|第二轮最大差pp|", "|---|---|---:|---:|"]
        for before, after in zip(baseline["comparisons"]["route_gaps"], result["comparisons"]["route_gaps"]):
            lines.append(f"|{after['character']}|{after['prepared']}|{before['spread_pp']:.2f}|{after['spread_pp']:.2f}|")
    lines += ["", "## 各组原始统计", "", "|职业|路线|准备|诅咒|同行者|胜/N|通关率|第一轮|变化pp|到达Boss|Boss条件胜率|首次败北地点|", "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|"]
    previous = {(r['character'], r['path'], r['prepared'], r['cursed'], r['companion']): r for r in baseline.get("rows", [])}
    for r in result["rows"]:
        conditional = f"{r['boss_win_rate']:.2%}" if r["boss_win_rate"] is not None else "—"
        old = previous.get((r['character'], r['path'], r['prepared'], r['cursed'], r['companion']))
        before = f"{old['success_rate']:.2%}" if old else "—"
        change = f"{100*(r['success_rate']-old['success_rate']):+.2f}" if old else "—"
        lines.append(f"|{r['character']}|{r['path']}|{r['prepared']}|{r['cursed']}|{r['companion']}|{r['wins']}/{r['n']}|{r['success_rate']:.2%}|{before}|{change}|{r['boss_arrivals']}|{conditional}|{json.dumps(r['failures'], ensure_ascii=False)}|")
    lines += ["", "## 结论与设计待办", ""]
    for r in result["comparisons"]["rankings"]:
        lines.append(f"- 准备={r['prepared']}，四职业共同最优路线：{', '.join(r['universal_best']) or '无'}；达标={r['passed']}。")
    failures = [dict(metric=key, **r) for key, values in result["comparisons"].items() for r in values if not r["passed"]]
    lines.append(f"- 未通过的比较：{len(failures)}项。")
    if failures:
        lines.append("- TODO(design): 联合目标未全部达到，停止数值修改并交由设计负责人决定；具体越界见上表与JSON。031古戦場敌人、既有村庄与竜の谷敌人均不在033–035允许调参范围。")
    lines += ["- 墓守外套按第二轮决定调整；两人的正式参数保留原值，候选搜索与停止调参依据见[调参报告](037-companion-tuning.md)。未改旧路线敌人、DC、奖励或提示词。", "",
        "## 路线差距定位", "", "|职业|路线|准备|通关率|路线段死亡|煤の亡霊死亡|イグニス死亡|", "|---|---|---|---:|---:|---:|---:|"]
    for r in result["rows"]:
        if r["companion"] != "none" or r["cursed"]:
            continue
        failures = r["failures"]
        early = sum(v for k, v in failures.items() if k not in {"valley_entrance", "dragon_valley_loc"})
        lines.append(f"|{r['character']}|{r['path']}|{r['prepared']}|{r['success_rate']:.2%}|{early}|{failures.get('valley_entrance', 0)}|{failures.get('dragon_valley_loc', 0)}|")
    lines += ["", "上述死亡地点是差异定位，不是单因素因果实验。不同路线的永久增益、装备与消耗品进入共同后程时不同；保留的逐战样本提供资源证据。村路线及共同后程属于旧内容，不通过修改这些数值来达成8pp。",
        "", "## 复现", "", "```powershell",
        f"python -m scripts.balance.ch3_routes --n {result['n']} --seed {result['seed']} --workers {result['workers']}", "```", "",
        "原始JSON包含前置回放、每种条件的准备交易与起点、各失败地点和胜利的首个完整样本、资源继承、消耗、源文件SHA-256。", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261018)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--baseline", type=Path, default=OUTPUT.with_name(OUTPUT.name + "-round1").with_suffix(".json"))
    args = parser.parse_args()
    if min(args.n, args.workers) < 1:
        parser.error("n and workers must be positive")
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    templates = {c: starting_checkpoint(pack, cp, c) for c in CHARACTERS}
    files = [Path(__file__), Path(checkpoints.__file__), Path(gorge.__file__), Path(route.__file__),
             Path(sim.__file__), Path(rewards.__file__), *sorted((checkpoints.ROOT / "host").glob("*.py")),
             checkpoints.DEFAULT_SCENARIO]
    result = dict(n=args.n, seed=args.seed, workers=args.workers, rows=[],
        checkpoints={c: dict(snapshot=rewards.snapshot(t), resources=route.resources(t), sources=t["checkpoint_sources"]) for c, t in templates.items()},
        fingerprints={p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    if args.baseline.exists():
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        result["baseline"] = dict(file=args.baseline.as_posix(), sha256=hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
            comparisons=baseline["comparisons"], rows=[{k: r[k] for k in
                ("character", "path", "prepared", "cursed", "companion", "n", "wins", "success_rate")} for r in baseline["rows"]])
    result["companions"] = [c for c in pack["companions"] if c["id"] in COUNTERS.values()]
    jobs = [(c, template, condition, args.n, args.seed) for c, template in templates.items() for condition in conditions()]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for row in gorge._map_jobs(_job, jobs, args.workers):
        result["rows"].append(row)
        print(row["character"], row["path"], row["prepared"], row["cursed"], row["companion"], row["success_rate"], flush=True)
        args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    result["comparisons"] = comparisons(result["rows"])
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
