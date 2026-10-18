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
        roll = state.roll_dice(session, dice, dc, roll=entry.get("roll"), rng=rng,
                               critical_enabled=entry.get("critical_enabled") is not False)
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
                        required=not prepared and not cursed, passed=rates[counter] > rates[best]))
    return dict(route_gaps=gaps, rankings=rankings, counters=counter_rows)


def counter_gate(counters: list[dict[str, Any]]) -> dict[str, Any]:
    core = [r for r in counters if not r["prepared"] and not r["cursed"]]
    expected = {(character, path) for character in CHARACTERS for path in COUNTERS}
    complete = len(core) == len(expected) and {(r["character"], r["path"]) for r in core} == expected
    return dict(required=len(expected), evaluated=len(core), passed_count=sum(r["passed"] for r in core),
                passed=complete and all(r["passed"] for r in core))


def markdown(result: dict[str, Any]) -> str:
    gate = counter_gate(result["comparisons"]["counters"])
    lines = ["# 037 第三章三条路线连续平衡（第三轮）", "",
        f"N={result['n']}／职业／条件；seed={result['seed']}；{len(result['rows'])}组，共{sum(r['n'] for r in result['rows']):,}条连续路线。完全离线。", "",
        "按设计负责人第三轮决定，采用第二轮筛选中唯一核心8项全通过的组合：リーゼ回复20%、聖光の一撃2d6；エリオ水刃2d6、水の帳每4回合。两份剧本的说明与招募preview同步。未继续搜索或调参。", "",
        f"本轮对策同行者门槛：未准备、无诅咒的4职业×2路线严格领先，共{gate['passed_count']}/{gate['required']}项通过；完整覆盖={gate['evaluated'] == gate['required']}，门槛通过={gate['passed']}。准备组和诅咒组仅报告，不作为这一门槛。", "",
        "24项全部严格领先在第二轮授权范围内无法满足；设计据大多数玩家处境改用核心8项。第二轮N=300筛选用于选定参数，本轮N=2000独立复核，核心若失败也只报告。", "",
        "## 口径与推断", "",
        "- 起点为第2章结束的森の出口。复用可达检查点回放，先完成ゴブリン砦并归还箱子，再通过森林、回城支付10G休息后返回出口；Lv3、240G，四职业具体背包和全部前置动作见JSON。前置战斗假定获胜、不估算消耗，结论条件于这个检查点，不是从新游戏开始的通关率。",
        "- 原主线Lv2起点只有125G，不能支付195G整套准备；为避免凭空补钱，所有组统一采用上述砦后检查点。准备组实际购买聖銀120G、锻造30G、鎖帷子40G、礼拝堂休息5G；未准备组不购买。第二轮墓守外套仅在防具部位为空时自动装备；本轮不额外加入手动换装策略，保留原有ローブ／革の鎧或准备组鎖帷子。",
        "- 同行者和诅咒采用031/033/035既有的机制对照：起点指定同行者，诅咒组给予呪われた短剣；武器位为空的僧侶／魔法使い会自动装备，勇者／盗賊保留原武器；准备组再由锻造替换武器。第一轮‘只携带、不装备’的文字描述不准确，但三轮实际代码均为上述行为，原始JSON可核对。不计招募费用、获取诅咒代价，不能当成完整招募路线。火コウモリ竜普通／虹晶强化分别列出；其他控制包括ロビン、ミーナ、ワーロック及另一条路线的同行者。",
        "- 保留剧情中的同行者离队；村路线的ワーロック在森林出口离队，所以该组不会强行留住他。",
        "- 村路线慎重接近、离开民家；古戦場骨野潜行（诅咒放行）、塔取外套并休息、沼地潜行、骑士战（诅咒放行）；峡谷潜行、搜营地并休息、查爪痕、巨人潜行、ワーム潜行（エリオ绕过）。",
        "- 三路都汇入避難所。共同后程采用现行hp70付费休息策略、竜の谷亡霊潜行、过桥、イグニス战；不额外走冰元素／Xanxus支线，不净化。所有判定投真实d20、失败实战，HP/MP/SP、金币、背包跨战继承，永久品立即使用，无重来。",
        "- 分母始终是全部起点样本，包含提前死亡；同时列出到Boss的样本数与条件胜率。每组共享初始随机种子，同行者耗骰不同，不代表逐骰配对。判据采用样本点估计，不把抽样误差当成设计容差。",
        "- ‘三路相差≤8pp’对未准备／已准备分别比较（村路线均为未准备），主比较无诅咒；诅咒单列。同率并列最优也计入四职业共同最优。第三轮对策同行者仅核心8项要求严格领先所有其他同行者，相同基线下比较提升等价于比较通关率；并列判为未通过。其他16项沿用严格比较展示结果，但不计入门槛。", "",
        "## 无同行者、无诅咒", "", "|职业|城塞准备|村|古戦場|峡谷|最大差pp|≤8pp|", "|---|---|---:|---:|---:|---:|---|"]
    for r in result["comparisons"]["route_gaps"]:
        rates = r["rates"]
        lines.append(f"|{r['character']}|{r['prepared']}|{rates['village']:.2%}|{rates['battlefield']:.2%}|{rates['gorge']:.2%}|{r['spread_pp']:.2f}|{r['passed']}|")
    for required, heading in ((True, "核心8项：未准备、无诅咒（验收门槛）"), (False, "准备组／诅咒组（仅报告）")):
        lines += ["", f"## 本路线对策同行者——{heading}", "", "|职业|路线|准备|诅咒|对策提升pp|其他最强|其提升pp|领先pp|严格领先|", "|---|---|---|---|---:|---|---:|---:|---|"]
        for r in result["comparisons"]["counters"]:
            if r["required"] == required:
                lines.append(f"|{r['character']}|{r['path']}|{r['prepared']}|{r['cursed']}|{r['uplift_pp']:+.2f}|{r['best_other']}|{r['other_uplift_pp']:+.2f}|{r['margin_pp']:+.2f}|{r['passed']}|")
    baseline = result.get("baseline", {})
    baseline2 = result.get("baseline_round2", {})
    if baseline and baseline2:
        lines += ["", "## 第一、二轮对照", "", "第一轮：[报告](balance-2026-10-18-ch3-routes-round1.md)、[JSON](balance-2026-10-18-ch3-routes-round1.json)；第二轮：[报告](balance-2026-10-18-ch3-routes-round2.md)、[JSON](balance-2026-10-18-ch3-routes-round2.json)。204组起点、策略、种子和N不变；本轮仅改变两名同行者的指定参数。", "",
                  "|职业|准备|第一轮最大差pp|第二轮最大差pp|第三轮最大差pp|", "|---|---|---:|---:|---:|"]
        for first, second, current in zip(baseline["comparisons"]["route_gaps"], baseline2["comparisons"]["route_gaps"], result["comparisons"]["route_gaps"]):
            lines.append(f"|{current['character']}|{current['prepared']}|{first['spread_pp']:.2f}|{second['spread_pp']:.2f}|{current['spread_pp']:.2f}|")
    lines += ["", "## 各组原始统计", "", "|职业|路线|准备|诅咒|同行者|胜/N|第三轮通关率|第一轮|第二轮|较第二轮变化pp|到达Boss|Boss条件胜率|首次败北地点|", "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    previous = {(r['character'], r['path'], r['prepared'], r['cursed'], r['companion']): r for r in baseline.get("rows", [])}
    previous2 = {(r['character'], r['path'], r['prepared'], r['cursed'], r['companion']): r for r in baseline2.get("rows", [])}
    for r in result["rows"]:
        conditional = f"{r['boss_win_rate']:.2%}" if r["boss_win_rate"] is not None else "—"
        old = previous.get((r['character'], r['path'], r['prepared'], r['cursed'], r['companion']))
        before = f"{old['success_rate']:.2%}" if old else "—"
        old2 = previous2.get((r['character'], r['path'], r['prepared'], r['cursed'], r['companion']))
        before2 = f"{old2['success_rate']:.2%}" if old2 else "—"
        change = f"{100*(r['success_rate']-old2['success_rate']):+.2f}" if old2 else "—"
        lines.append(f"|{r['character']}|{r['path']}|{r['prepared']}|{r['cursed']}|{r['companion']}|{r['wins']}/{r['n']}|{r['success_rate']:.2%}|{before}|{before2}|{change}|{r['boss_arrivals']}|{conditional}|{json.dumps(r['failures'], ensure_ascii=False)}|")
    lines += ["", "## 结论与设计待办", ""]
    for r in result["comparisons"]["rankings"]:
        lines.append(f"- 准备={r['prepared']}，四职业共同最优路线：{', '.join(r['universal_best']) or '无'}；达标={r['passed']}。")
    core_failures = [r for r in result["comparisons"]["counters"] if r["required"] and not r["passed"]]
    optional_failures = [r for r in result["comparisons"]["counters"] if not r["required"] and not r["passed"]]
    gap_failures = [r for r in result["comparisons"]["route_gaps"] if not r["passed"]]
    lines += [f"- 核心门槛通过={gate['passed']}；核心未严格领先{len(core_failures)}项。准备／诅咒仅报告组未严格领先{len(optional_failures)}/16项，不阻止核心门槛通过。",
        f"- 三路线≤8pp仍有{len(gap_failures)}/8项越界；保留全部结果，按设计决定不修改旧内容。"]
    for r in core_failures:
        lines.append(f"- TODO(design): 核心{r['character']}/{r['path']}未严格领先{r['best_other']}（{r['margin_pp']:+.2f}pp）；如实报告，不继续调参。")
    lines += ["- 墓守外套沿用第二轮决定；两人的正式参数采用第三轮指定组合。第二轮完整筛选与24项边界证据见[调参报告](037-companion-tuning.md)。未改旧路线敌人、DC、奖励或提示词。", "",
        "## 两名同行者路线外复核", "",
        "每人排除各自本路线的三场遭遇，仍按现有最强同行者+3pp逐职业逐场比较。リーゼ沿用033对照集合，エリオ沿用035（包含本轮リーゼ）；独立满资源逐战检查，不混同连续路线通关率。完整结果见[第三轮路线外报告](037-companion-outside.md)、[JSON](037-companion-outside.json)；[第二轮对照](037-companion-outside-round2.md)保留。"]
    if result.get("outside"):
        outside = result["outside"]
        failures = [r for r in outside["comparisons"] if not r["passed"]]
        lines += ["", f"N={outside['n']}；共{len(outside['comparisons'])}项上限比较，越界{len(failures)}项。",
                  "", "|同行者|职业|遭遇|本轮胜率|现有最强|对照胜率|超出pp|", "|---|---|---|---:|---|---:|---:|"]
        for r in failures:
            lines.append(f"|{r['companion']}|{r['character']}|{r['location']}|{r['win_rate']:.2%}|{r['best']}|{r['best_rate']:.2%}|{r['excess_pp']:+.2f}|")
        if failures:
            lines += ["", "TODO(design): 上表超出+3pp的项目如实保留，本轮不再调参。"]
    lines += ["",
        "## 路线差距定位", "", "|职业|路线|准备|通关率|路线段死亡|煤の亡霊死亡|イグニス死亡|", "|---|---|---|---:|---:|---:|---:|"]
    for r in result["rows"]:
        if r["companion"] != "none" or r["cursed"]:
            continue
        failures = r["failures"]
        early = sum(v for k, v in failures.items() if k not in {"valley_entrance", "dragon_valley_loc"})
        lines.append(f"|{r['character']}|{r['path']}|{r['prepared']}|{r['success_rate']:.2%}|{early}|{failures.get('valley_entrance', 0)}|{failures.get('dragon_valley_loc', 0)}|")
    lines += ["", "设计负责人已明确：未准备、无同行者、无诅咒的三路线差距中，魔法使い的9.95pp（村70.45%、古戦場80.40%、峡谷77.00%）来自村路线本身，属于旧内容，本轮不改。该比较不使用033–035新增的可调敌人、DC、同行者、装备或奖励金币；034聖銀只入背包，古戦場两颗生命の果実来自031墓守骑士。",
        "", "上述死亡地点是差异定位，不是单因素因果实验。不同路线的永久增益、装备与消耗品进入共同后程时不同；保留的逐战样本提供资源证据。村路线及共同后程属于旧内容，不通过修改这些数值来达成8pp。",
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
    parser.add_argument("--baseline-round2", type=Path, default=OUTPUT.with_name(OUTPUT.name + "-round2").with_suffix(".json"))
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
    for key, path in (("baseline", args.baseline), ("baseline_round2", args.baseline_round2)):
        if path.exists():
            baseline = json.loads(path.read_text(encoding="utf-8"))
            result[key] = dict(file=path.as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
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
    result["counter_gate"] = counter_gate(result["comparisons"]["counters"])
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
