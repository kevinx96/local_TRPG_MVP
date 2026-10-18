"""Offline continuous route comparison from the chapter-two forest-exit checkpoint."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import patch

from host import combat, state
from . import checkpoints, ch5, rewards, route, sim


def forest_exit(pack: dict[str, Any], cp: dict[str, Any], character: str) -> dict[str, Any]:
    session = checkpoints.fresh_session(pack, character)
    sources = cp["encounters"]["forest_wolves"]["characters"][character]["sources"]
    for step in [*[source["step"] for source in sources], "@victory"]:
        checkpoints.replay_step(session, step)
        rewards.consume_boosts(session)
    assert state.current_location_id(session) == "forest_exit"
    for resource in ("hp", "mp", "sp"):
        session["character"][resource] = session["character"][f"max_{resource}"]
    session["event_log"] = []
    return session


def trial(template: dict[str, Any], path: str, cursed: bool, warlock: bool, seed: int) -> dict[str, Any]:
    pack = template["scenario_pack"]
    session = deepcopy(template, {id(pack): pack})
    start = "old_battlefield" if path == "battlefield" else "village_approach"
    state.apply_state_delta(session, {"current_location": start}, allow_world_transition=True)
    state._set_companion(session, "blue_robed_mage" if warlock else None)
    if cursed:
        item = next(i for i in pack["items"] if i["id"] == "cursed_dagger")
        state.apply_state_delta(session, {"inventory_add": [{**item, "quantity": 1}]})
    rng = random.Random(seed)
    battles = []
    steps = []
    with patch.object(combat, "random", rng):
        for _ in range(40):
            location = state.current_location_id(session)
            if location == "village_frozen_clue":
                return dict(completed=True, battles=battles, steps=steps)
            if session.get("game_over"):
                break
            if session.get("combat_start_requested"):
                battle = route.fight(session, "heuristic", rng)
                battles.append(battle)
                if not battle["continue"]:
                    break
                rewards.consume_boosts(session)
                continue
            flags = session["flags"]
            if location == "old_battlefield":
                identifier = "battlefield_to_bones"
            elif location == "bone_field":
                if not flags.get("passed_bone_field"):
                    identifier = "show_curse_to_skeletons" if cursed else "sneak_bone_field"
                else:
                    identifier = "bones_to_marsh" if flags.get("rested_watchtower") else "bones_to_tower"
            elif location == "ruined_watchtower":
                identifier = ("search_watchtower" if not flags.get("found_gravekeeper_cloak") else
                              "rest_watchtower" if not flags.get("rested_watchtower") else "tower_to_bones")
            elif location == "ghoul_marsh":
                identifier = "marsh_to_chapel" if flags.get("passed_ghoul_marsh") else "sneak_ghoul_marsh"
            elif location == "grave_chapel":
                identifier = ("chapel_to_village" if flags.get("passed_grave_chapel") else
                              "curse_pass_grave_knight" if cursed else "fight_grave_knight")
            elif location == "village_approach":
                identifier = "approach_burning_village_carefully"
            elif location == "burning_house":
                identifier = "leave_burning_house"
            elif location in {"village_fire_slime", "village_fire_elemental"}:
                session["combat_start_requested"] = True
                continue
            else:
                raise ValueError(f"Unexpected route location: {location}")
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
    return dict(completed=False, failed_at=state.current_location_id(session), battles=battles, steps=steps)


def evaluate(pack: dict[str, Any], n: int, seed: int) -> dict[str, Any]:
    cp = checkpoints.generate()
    rows = []
    snapshots = {}
    for character in ch5.CHARACTERS:
        template = forest_exit(pack, cp, character)
        snapshots[character] = rewards.snapshot(template)
        for path, cursed in (("village", False), ("battlefield", False), ("battlefield", True)):
            for warlock in (False, True):
                failures: Counter = Counter()
                wins = 0
                sample = None
                for index in range(n):
                    result = trial(template, path, cursed, warlock, sim.trial_seed(seed, "031-route", character, index))
                    wins += result["completed"]
                    if not result["completed"]:
                        failures[result["failed_at"]] += 1
                    sample = sample or result
                row = dict(character=character, path=path, cursed=cursed, warlock=warlock,
                           n=n, success_rate=wins / n, failures=dict(failures), sample=sample)
                rows.append(row)
                print(character, path, cursed, warlock, row["success_rate"], flush=True)
    comparisons = []
    for character in ch5.CHARACTERS:
        def rate(path: str, cursed: bool = False, warlock: bool = False) -> float:
            return next(r["success_rate"] for r in rows if (r["character"], r["path"], r["cursed"], r["warlock"]) ==
                        (character, path, cursed, warlock))
        comparisons.append(dict(character=character, village=rate("village"), plain=rate("battlefield"),
            cursed=rate("battlefield", True), difference_pp=100*(rate("battlefield")-rate("village")),
            curse_uplift_pp=100*(rate("battlefield", True)-rate("battlefield")),
            warlock_uplift_pp=100*(rate("battlefield", warlock=True)-rate("battlefield")),
            village_warlock_pp=100*(rate("village", warlock=True)-rate("village"))))
    return dict(n=n, seed=seed, rows=rows, comparisons=comparisons, snapshots=snapshots,
                enemies=[e for e in pack["enemies"] if e["id"] in {"skeleton_soldier", "ghoul", "wraith", "grave_knight"}])


def markdown(result: dict[str, Any]) -> str:
    lines = ["# 031 古戦場路线难度", "", f"N={result['n']}，seed={result['seed']}，四职业、真实连续战斗、真实d20、有限背包、heuristic。",
        "起点为第2章森の出口可达检查点（森林既有路线，前战假定胜利，永久品使用，HP/MP/SP补满）。",
        "古戦場：非持有者骨野潜行，塔取外套并休息一次，沼地潜行，礼拝堂战斗；持有者骨野举物、礼拝堂让路。潜行失败立即实战；消耗跨战继承。",
        "诅咒控制只在背包加入呪われた短剣、不装备；对照的ワーロック在路线起点强制加入，用来隔离治疗作用。正常村庄入口剧情会让他离队，此为指定同行的机制对照。",
        "村庄：慎重接近的真实判定、失败精英/成功史莱姆/大成功跳过、离开民家直至结冰线索，不冒险救人。", "",
        "|职业|村庄|古戦場无诅咒|差pp（±5）|持有诅咒|提升pp（≥15）|古戦場同行提升pp（≤3）|村庄同行提升pp|",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in result["comparisons"]:
        lines.append(f"|{r['character']}|{r['village']*100:.2f}%|{r['plain']*100:.2f}%|{r['difference_pp']:+.2f}|"
                     f"{r['cursed']*100:.2f}%|{r['curse_uplift_pp']:+.2f}|{r['warlock_uplift_pp']:+.2f}|{r['village_warlock_pp']:+.2f}|")
    lines += ["", "调参：仅将新骑士HP45→60、攻击2d6+3→2d8+5；其余新敌人初值与潜行DC14/15保留。",
              "TODO(design): 当前村庄基准成功率过高，‘古戦場相差±5pp’与‘诅咒再提高≥15pp’不能同时满足：村庄>90%时，古戦場最低仍>85%，而成功率上限为100%。未降低旧敌人强度、未虚构诅咒提升。",
              "已完成骑士HP/伤害、沼地DC、骑士防御三组网格共18套参数试跑（各职业N250），见search、dc-search、defense-search三个JSON。采用接近村庄基准的参数，并如实保留未达目标。"]
    return "\n".join(lines) + "\n"


def search(pack: dict[str, Any], n: int, seed: int, grid: str = "knight") -> list[dict[str, Any]]:
    cp = checkpoints.generate()
    starts = {c: forest_exit(pack, cp, c) for c in ch5.CHARACTERS}
    rows = []
    parameters = {
        "knight": [dict(hp=hp, damage=damage) for damage in ("2d6+4", "2d8+5") for hp in (60, 75, 90)],
        "dc": [dict(hp=hp, damage=damage, marsh_dc=dc) for dc in (25, 30)
               for hp, damage in ((45, "2d6+3"), (60, "2d6+4"), (45, "2d8+5"))],
        "defense": [dict(hp=60, damage=damage, defense=defense) for damage in ("2d6+3", "2d6+4")
                    for defense in (2, 4, 6)],
    }
    marsh = next(loc for loc in pack["locations"] if loc["id"] == "ghoul_marsh")
    for parameter in parameters[grid]:
        enemy = next(e for e in pack["enemies"] if e["id"] == "grave_knight")
        enemy.update(hp=parameter["hp"], max_hp=parameter["hp"])
        enemy["combat"]["basic_attack"]["damage"] = parameter["damage"]
        enemy["combat"]["defense"] = parameter.get("defense", 0)
        next(a for a in marsh["actions"] if a["id"] == "sneak_ghoul_marsh")["roll"]["dc"] = parameter.get("marsh_dc", 15)
        row = dict(**parameter, rates={})
        for character, template in starts.items():
            row["rates"][character] = sum(trial(template, "battlefield", False, False,
                sim.trial_seed(seed, "031-route", character, index))["completed"] for index in range(n))/n
        rows.append(row)
        print(row, flush=True)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261013)
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--search-grid", choices=("knight", "dc", "defense"), default="knight")
    parser.add_argument("--output", type=Path, default=checkpoints.ROOT / "eval/reports/battlefield-2026-10-13")
    args = parser.parse_args()
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    if args.search:
        result = search(pack, args.n, args.seed, args.search_grid)
        args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        return
    result = evaluate(pack, args.n, args.seed)
    result["fingerprints"] = {str(p.relative_to(checkpoints.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (Path(__file__), checkpoints.DEFAULT_SCENARIO)}
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")


if __name__ == "__main__":
    main()
