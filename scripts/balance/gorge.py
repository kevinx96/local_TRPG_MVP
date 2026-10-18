"""Offline paired-seed route, companion and optional-combat economy checks for 035."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any
from unittest.mock import patch

from host import combat, state
from scripts.scenario.rumbling_gorge import BATTLES
from . import battlefield, checkpoints, economy, liese, rewards, route, sim

ELIO = "hydromancer_elio"
BONUSES = checkpoints.ROOT / "eval/balance/gorge_economy.json"


def route_action(session: dict[str, Any]) -> str:
    location, flags = state.current_location_id(session), session["flags"]
    if location == "gorge_entrance":
        return "gorge_to_rockfall"
    if location == "gorge_rockfall_path":
        if not flags.get("passed_gorge_rockfall_path"):
            return "sneak_gorge_rockfall_path"
        return "rockfall_to_cliff" if flags.get("rested_miner_camp") else "rockfall_to_camp"
    if location == "gorge_miner_camp":
        return ("search_miner_camp" if not flags.get("read_miner_diary") else
                "rest_miner_camp" if not flags.get("rested_miner_camp") else "camp_to_rockfall")
    if location == "gorge_claw_cliff":
        return "cliff_to_giant" if flags.get("saw_white_claw") else "inspect_white_claw"
    if location == "gorge_giant_path":
        return "giant_to_worm" if flags.get("passed_gorge_giant_path") else "sneak_gorge_giant_path"
    if location == "gorge_worm_lair":
        if flags.get("passed_gorge_worm_lair"):
            return "gorge_to_village"
        return "elio_flood_worm" if (session.get("companion") or {}).get("id") == ELIO else "sneak_gorge_worm_lair"
    raise ValueError(f"Unexpected gorge location: {location}")


def route_trial(template: dict[str, Any], seed: int, *, companion: bool = False) -> dict[str, Any]:
    pack = template["scenario_pack"]
    session = deepcopy(template, {id(pack): pack})
    state._set_companion(session, ELIO if companion else None)
    state.apply_state_delta(session, {"current_location": "gorge_entrance"}, allow_world_transition=True)
    rng = random.Random(seed)
    steps, battles = [], []
    with patch.object(combat, "random", rng):
        for _ in range(40):
            location = state.current_location_id(session)
            if location == "village":
                return dict(completed=True, steps=steps, battles=battles)
            if session.get("game_over"):
                break
            if session.get("combat_start_requested"):
                result = route.fight(session, "heuristic", rng)
                battles.append(result)
                if not result["continue"]:
                    break
                rewards.consume_boosts(session)
                continue
            identifier = route_action(session)
            action = state.resolve_action(session, action_id=identifier)
            if action is None or not state.action_requirement_status(action, session)[0]:
                raise ValueError(f"Unavailable action: {location}/{identifier}")
            roll = {}
            if action.get("roll"):
                dice, dc = state.action_dice_settings(action, session=session)
                roll = state.roll_dice(session, dice, dc, roll=action.get("roll"), rng=rng,
                                       critical_enabled=action.get("critical_enabled") is not False)
            state.apply_action_result(session, action, roll)
            steps.append(dict(location=location, action=identifier, roll=roll))
            if not session.get("combat_start_requested"):
                rewards.consume_boosts(session)
    return dict(completed=False, failed_at=state.current_location_id(session), steps=steps, battles=battles)


def starts(pack: dict[str, Any], cp: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c: battlefield.forest_exit(pack, cp, c) for c in liese.CHARACTERS}


def _route_job(job: tuple[Any, ...]) -> dict[str, Any]:
    character, template, path, n, seed = job
    trials = [battlefield.trial(template, "village", False, False, sim.trial_seed(seed, "035-route", character, i))
              if path == "village" else route_trial(template, sim.trial_seed(seed, "035-route", character, i),
                                                    companion=path == "gorge_elio") for i in range(n)]
    return dict(character=character, path=path, n=n, success_rate=mean(t["completed"] for t in trials),
                failures=dict(Counter(t["failed_at"] for t in trials if not t["completed"])), sample=trials[0])


def _map_jobs(function: Any, jobs: list[tuple[Any, ...]], workers: int):
    if workers == 1:
        yield from map(function, jobs)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            yield from pool.map(function, jobs)


def route_rows(templates: dict[str, dict[str, Any]], n: int, seed: int, workers: int = 1) -> list[dict[str, Any]]:
    jobs = [(character, template, path, n, seed) for character, template in templates.items()
            for path in ("village", "gorge", "gorge_elio")]
    rows = []
    for row in _map_jobs(_route_job, jobs, workers):
        rows.append(row)
        print(row["character"], row["path"], row["success_rate"], flush=True)
    return rows


def _battle_job(job: tuple[Any, ...]) -> list[dict[str, Any]]:
    location, character, template, companions, n, seed = job
    rows = []
    for companion in companions:
        trials = [liese.trial(template, companion, sim.trial_seed(seed, location, character, i)) for i in range(n)]
        rows.append(dict(location=location, character=character, companion=companion, n=n,
            win_rate=mean(t["won"] for t in trials), hp_loss=mean(t["hp_loss"] for t in trials),
            rounds=mean(t["rounds"] for t in trials), nonterminal=sum(t["status"] not in {"victory", "defeat"} for t in trials)))
    return rows


def outside_locations(pack: dict[str, Any]) -> list[str]:
    return [loc["id"] for loc in pack["locations"] if loc["id"] not in BATTLES
            and loc.get("combat", {}).get("enemy_ids", loc.get("enemy_ids"))
            and loc["combat"].get("encounter_class") != "scripted_loss"
            and not loc["combat"].get("disable_companion")]


def battle_rows(pack: dict[str, Any], templates: dict[str, dict[str, Any]], cp: dict[str, Any],
                n: int, seed: int, outside: bool, workers: int = 1) -> list[dict[str, Any]]:
    rows = []
    jobs = []
    locations = [*BATTLES, *(outside_locations(pack) if outside else [])]
    for location in locations:
        for character in liese.CHARACTERS:
            if location in (*BATTLES, *liese.BATTLEFIELD):
                template = deepcopy(templates[character], {id(pack): pack})
                state.apply_state_delta(template, {"current_location": location}, allow_world_transition=True)
            else:
                point = cp if location in cp["encounters"] else economy.encounter_checkpoint(pack, cp, location, character)
                template = sim.prepare_session(pack, location, character, point, companion=False)
            companions = ("none", ELIO) if location in BATTLES else (*liese.COMPANIONS, ELIO)
            jobs.append((location, character, template, companions, n, seed))
    for group in _map_jobs(_battle_job, jobs, workers):
        rows.extend(group)
        print("battle", group[0]["location"], group[0]["character"], "complete", flush=True)
    return rows


def _economy_job(job: tuple[Any, ...]) -> dict[str, Any]:
    return economy.measure(*job)


def search(pack: dict[str, Any], cp: dict[str, Any], n: int, seed: int, workers: int) -> list[dict[str, Any]]:
    jobs, labels = [], []
    for hp in (24, 30):
        for dc in (21, 24, 27):
            candidate = deepcopy(pack)
            enemy = next(e for e in candidate["enemies"] if e["id"] == "rock_giant")
            enemy.update(hp=hp, max_hp=hp)
            location = next(l for l in candidate["locations"] if l["id"] == "gorge_giant_path")
            next(a for a in location["actions"] if a["id"] == "sneak_gorge_giant_path")["roll"]["dc"] = dc
            for character, template in starts(candidate, cp).items():
                jobs.append((character, template, "gorge", n, seed))
                labels.append(dict(giant_hp=hp, giant_dc=dc))
    rows = []
    for label, result in zip(labels, _map_jobs(_route_job, jobs, workers)):
        rows.append({**label, **result})
        print(label, result["character"], result["success_rate"], flush=True)
    return rows


def markdown(result: dict[str, Any]) -> str:
    lines = ["# 035 峡谷与エリオ平衡（2026-10-18）", "",
        f"独立战斗与经济N={result['n']}／组合，连续路线N={result.get('route_n', result['n'])}／组合，seed={result['seed']}；四职业、真实确定性引擎、有限背包、heuristic，完全离线。", "",
        "## 口径与推断", "",
        "- 起点复用031的森の出口可达Lv2检查点（森林前战按胜利回放、永久品已使用、HP/MP/SP补满）。不预取城塞装备，不带其他同行者。",
        "- 峡谷连续路线：三处潜行使用真实d20；失败立即实战，巨人/ワーム失败敌先手；第一战后营地搜寻并全恢复一次；偷取/战胜巨人共用果实标记，果实立即使用；资源与消耗品跨战继承。到village即成功。",
        "- 村庄沿用031比较路线：慎重接近→实际判定与分支战→离开民家→village_frozen_clue；不救人。两条路线终点依spec，后续村庄内容不纳入。",
        "- エリオ三场战斗从同一满资源检查点分别强制开战；不计其无战绕过。HP损失为开战HP减战后HP、最低0，含败北样本与治疗，避免只看胜者。",
        "- 峡谷外逐职业逐场比较现有所有同行者，含强化火コウモリ竜和リーゼ；使用现有逐战检查点，古戦場使用同一森出口，不携带诅咒。屋敷/宿袭沿用031的最终战前检查点，商人战使用原商人检查点。自动枚举32场遭遇，仅排除必败剧情和禁用同行者的救援战。",
        "- 配对初始种子，但同行者消耗骰序不同。经验胜率存在抽样误差，边界不能解释为精确总体概率。",
        "- 物理普攻沿用岩石系红宝石魔像的既有方式；新敌人本体为earth，物理抗性0.6、水弱点1.5。",
        "", "## 连续路线", "", "|职业|村庄|峡谷无エリオ|差pp|峡谷带エリオ|", "|---|---:|---:|---:|---:|"]
    issues = []
    for c in liese.CHARACTERS:
        rates = {r["path"]: r["success_rate"] for r in result["routes"] if r["character"] == c}
        diff = 100 * (rates["gorge"] - rates["village"])
        lines.append(f"|{c}|{rates['village']:.1%}|{rates['gorge']:.1%}|{diff:+.1f}|{rates['gorge_elio']:.1%}|")
        if abs(diff) > 5 + 1e-9:
            issues.append(f"{c}峡谷/村庄差{diff:+.1f}pp，超出±5pp。")
    lines += ["", "## 峡谷独立战斗", "", "|职业|战斗|无同行胜率|エリオ胜率|无同行HP损失|エリオHP损失|", "|---|---|---:|---:|---:|---:|"]
    for c in liese.CHARACTERS:
        base, elio = [], []
        for loc in BATTLES:
            rows = {r["companion"]: r for r in result["battles"] if r["character"] == c and r["location"] == loc}
            b, e = rows["none"], rows[ELIO]
            base.append(b["hp_loss"])
            elio.append(e["hp_loss"])
            lines.append(f"|{c}|{loc}|{b['win_rate']:.1%}|{e['win_rate']:.1%}|{b['hp_loss']:.2f}|{e['hp_loss']:.2f}|")
        reduction = 1 - mean(elio) / mean(base) if mean(base) else None
        uplift = 100 * (e["win_rate"] - b["win_rate"])
        lines.append(f"\n{c}三场平均HP净损失 {mean(base):.2f} → {mean(elio):.2f}；降低{reduction:.1%}；Boss提升{uplift:+.1f}pp。\n" if reduction is not None else f"\n{c}三场基准净损失0；Boss提升{uplift:+.1f}pp。\n")
        if (reduction is None or reduction < .3) and uplift < 10 - 1e-9 and b["win_rate"] < 1:
            issues.append(f"{c}未满足平均损失降低30%或Boss提高10pp。")
        elif b["win_rate"] == 1 and (reduction is None or reduction < .3):
            lines.append(f"{c}：HP损失降幅未达30%；无同行Boss胜率已为100%，按spec第6节的上限例外处理。\n")
    lines += ["", "## 峡谷外", "", "|职业|遭遇|无同行|エリオ|现有最强|最强胜率|超出pp|", "|---|---|---:|---:|---|---:|---:|"]
    for key in dict.fromkeys((r["character"], r["location"]) for r in result["battles"] if r["location"] not in BATTLES):
        rows = {r["companion"]: r for r in result["battles"] if (r["character"], r["location"]) == key}
        best = max((r for cid, r in rows.items() if cid not in {"none", ELIO}), key=lambda r: r["win_rate"])
        excess = 100 * (rows[ELIO]["win_rate"] - best["win_rate"])
        lines.append(f"|{key[0]}|{key[1]}|{rows['none']['win_rate']:.1%}|{rows[ELIO]['win_rate']:.1%}|{best['companion']}|{best['win_rate']:.1%}|{excess:+.1f}|")
        if excess > 3 + 1e-9:
            issues.append(f"{key[0]}/{key[1]}エリオ超出现有最强{excess:.1f}pp。")
    lines += ["", "## 031经济规则", "",
        "新区域三场均为可选战。复用031成本/拟合器：普通消耗品按商店最高买价，永久品不计收益，败北消耗计入成本且收益0。",
        "最低休息0G（营地一次），另以可重复5G休息的更保守成本拟合；金币取四职业所需最大值、向上到5G并留5G余量。",
        "", "|遭遇|职业|保守成本|金币|期望收益|收益/成本|", "|---|---|---:|---:|---:|---:|"]
    for r in result.get("economy", []):
        revenue = r["win_rate"] * (r["reward_on_victory_before"] + result["gold_bonus"][r["location"]])
        cost = r["conservative_cost"]
        lines.append(f"|{r['location']}|{r['character']}|{cost:.2f}|{result['gold_bonus'][r['location']]}|{revenue:.2f}|{revenue/cost:.2f}|" if cost else f"|{r['location']}|{r['character']}|0|{result['gold_bonus'][r['location']]}|{revenue:.2f}|成本0|")
        if revenue + 1e-9 < cost * 1.3:
            issues.append(f"{r['location']}/{r['character']}经济收益未达1.3倍成本。")
    if any(r["nonterminal"] for r in result["battles"]):
        issues.append("存在未正常结束的模拟战斗。")
    lines += ["", "## 结论与设计待办", "", *([f"- TODO(design): {i}" for i in issues] or ["在上述检查点、策略与样本量下，未发现目标越界；Boss上限例外已逐职业注明。"]),
        "", "未改现有敌人、其他同行者或提示词。原始结果、检查点、敌人参数与指纹见同名JSON。", "", "## 复现", "", "```powershell",
        f"python -m scripts.balance.gorge --n {result['n']} --route-n {result.get('route_n', result['n'])} --seed {result['seed']} --workers 8", "```", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261018)
    parser.add_argument("--route-n", type=int, help="Larger independent sample for route boundaries")
    parser.add_argument("--workers", type=int, default=1, help="Local processes; trial seeds and result order are unchanged")
    parser.add_argument("--quick", action="store_true", help="Omit outside comparisons and economy during tuning")
    parser.add_argument("--search", action="store_true", help="Compare only new giant HP/DC candidates")
    parser.add_argument("--fit-economy", action="store_true", help="Write only the new gorge gold schedule")
    parser.add_argument("--output", type=Path, default=checkpoints.ROOT / "eval/reports/balance-2026-10-18-gorge")
    args = parser.parse_args()
    if args.n < 1 or args.workers < 1 or (args.route_n is not None and args.route_n < 1):
        parser.error("sample counts and workers must be positive")
    fingerprints = {str(p.relative_to(checkpoints.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__), checkpoints.DEFAULT_SCENARIO, checkpoints.ROOT / "host/combat.py", checkpoints.ROOT / "scripts/scenario/rumbling_gorge.py")}
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    if args.search:
        result = dict(n=args.n, seed=args.seed, rows=search(pack, cp, args.n, args.seed, args.workers), fingerprints=fingerprints)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return
    templates = starts(pack, cp)
    result = dict(n=args.n, route_n=args.route_n or args.n, seed=args.seed, fingerprints=fingerprints,
                  snapshots={c: rewards.snapshot(t) for c, t in templates.items()})
    result["routes"] = route_rows(templates, result["route_n"], args.seed, args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".routes.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    result["battles"] = battle_rows(pack, templates, cp, args.n, args.seed, not args.quick, args.workers)
    if not args.quick:
        prices = economy.prices(pack)
        jobs = [(pack, cp, loc, c, args.n, args.seed, prices) for loc in BATTLES for c in liese.CHARACTERS]
        result["economy"] = list(_map_jobs(_economy_job, jobs, args.workers))
        result["gold_bonus"] = economy.fit(result["economy"]) if args.fit_economy else json.loads(BONUSES.read_text(encoding="utf-8"))["gold_bonus"]
        if args.fit_economy:
            BONUSES.parent.mkdir(parents=True, exist_ok=True)
            BONUSES.write_text(json.dumps(dict(gold_bonus=result["gold_bonus"], n=args.n, seed=args.seed), indent=2)+"\n", encoding="utf-8")
    result["enemies"] = [e for e in pack["enemies"] if "earth" in e.get("tags", [])]
    result["elio"] = next(c for c in pack["companions"] if c["id"] == ELIO)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
