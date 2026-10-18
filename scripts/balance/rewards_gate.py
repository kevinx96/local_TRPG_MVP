"""Compare regional rewards against the original final-boss preparation, offline."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from host import shops, state
from scripts.scenario.rewards_battlefield import DROPS, ELITE_REGIONS
from . import ch5, checkpoints, forest_v3, rewards, sim


def reward_pool(mode: str, boss: str) -> dict[str, int]:
    if mode == "main":
        return {"fruit_mana": 1}
    quantities: Counter = Counter()
    elite_locations = {loc for group in ELITE_REGIONS.values() for loc in group}
    selected = [loc for loc in DROPS if loc not in elite_locations]
    selected += [group[0] for group in ELITE_REGIONS.values()]
    for location in selected:
        if boss == "dragon_valley_loc" and location in {"mansion_corridor", "inn_night_ambush"}:
            continue
        item, quantity = DROPS[location]
        quantities[item] += quantity
    return dict(quantities)


def boosted_checkpoint(pack: dict[str, Any], cp: dict[str, Any], character: str,
                       mode: str, boss: str = "draco_battle") -> dict[str, Any]:
    result = deepcopy(cp)
    cell = result["encounters"][boss]["characters"][character]
    session = checkpoints.fresh_session(pack, character)
    for key in ("level", "attributes", "max_hp", "max_mp", "max_sp", "inventory", "equipment", "gold"):
        session["character"][key] = deepcopy(cell[key])
    state._normalize_character(session["character"])
    quantities = reward_pool(mode, boss)
    for identifier, quantity in quantities.items():
        item = next(i for i in pack["items"] if i["id"] == identifier)
        state.apply_state_delta(session, {"inventory_add": [{**deepcopy(item), "quantity": quantity}]})
        for _ in range(quantity):
            shops.use_item(session, identifier)
    for key in ("attributes", "max_hp", "max_mp", "max_sp", "inventory", "equipment", "gold"):
        cell[key] = deepcopy(session["character"][key])
    cell["permanent_reward_quantities"] = quantities
    return result


def evaluate(n: int, seed: int, characters: list[str], fruit_amount: int) -> dict[str, Any]:
    root = checkpoints.ROOT
    baseline_path = root / ".tmp-test/031/baseline.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_bytes(subprocess.check_output([
        "git", "show", f"{rewards.BASE_COMMIT}:host/prompt/processed/dragon_rpg.json"], cwd=root))
    old_pack = state.load_scenario_pack(baseline_path)
    new_pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    for item in new_pack["items"]:
        if item["id"] in {"fruit_life", "fruit_mana"}:
            item["combat"]["amount"] = fruit_amount
    cp = checkpoints.generate(baseline_path)
    support = json.loads((root / "eval/reports/balance-2026-10-12-support3.json").read_text(encoding="utf-8"))
    prism = json.loads((root / "eval/reports/balance-2026-10-12-prism.json").read_text(encoding="utf-8"))
    rows = []
    snapshots = {}
    for boss in ("dragon_valley_loc", "draco_battle"):
        for character in characters:
            for mode, case in (("main", "none"), ("explore", "all_kill")):
                original_cp = forest_v3.weapon_checkpoints(old_pack, cp, character) if (
                    boss == "dragon_valley_loc" and mode == "explore") else cp
                modified_cp = boosted_checkpoint(new_pack, original_cp, character, mode, boss)
                options = dict(n=n, seed=seed, purify=False)
                if boss == "draco_battle":
                    options.update(preparation="standard", initial_delta=ch5.cases()[case])
                    historical = next(r["win_rate"] for r in support["supports"]
                                      if r["character"] == character and r["case"] == case)
                else:
                    historical = next(r["before" if mode == "main" else "after"] for r in prism["weapons"]
                                      if r["character"] == character)
                before = sim.simulate(old_pack, boss, character, checkpoints=original_cp, **options)
                after = sim.simulate(new_pack, boss, character, checkpoints=modified_cp, **options)
                row = dict(encounter=boss, character=character, mode=mode, previous=historical,
                    before=before, after=after, uplift_pp=round(100*(after["win_rate"]-before["win_rate"]), 6),
                    previous_diff_pp=round(100*(after["win_rate"]-historical), 6),
                    limit_pp=5 if mode == "main" else 15)
                rows.append(row)
                for label, snapshot in (("before", original_cp), ("after", modified_cp)):
                    snapshots[f"{boss}/{character}/{mode}/{label}"] = snapshot["encounters"][boss]["characters"][character]
                print(f"+{fruit_amount} {boss}/{character}/{mode}: old={historical:.4f}, "
                      f"reproduced={before['win_rate']:.4f}, new={after['win_rate']:.4f}, "
                      f"delta={row['previous_diff_pp']:+.2f}pp", flush=True)
    return dict(n=n, seed=seed, fruit_amount=fruit_amount, baseline_commit=rewards.BASE_COMMIT,
        rows=rows, snapshots=snapshots, regions=ELITE_REGIONS,
        violations=[r for r in rows if max(r["uplift_pp"], r["previous_diff_pp"]) > r["limit_pp"] + 1e-9],
        fingerprints={p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (checkpoints.DEFAULT_SCENARIO, Path(__file__), Path(sim.__file__), root / "host/combat.py")})


def markdown(result: dict[str, Any]) -> str:
    lines = [f"# 031 区域首枚果实 +{result['fruit_amount']}：第1.3节复核", "",
        f"N={result['n']}/条件，seed={result['seed']}；离线真实引擎、heuristic、关闭净化。",
        "イグニス沿用017原装备/虹晶武器；ドラコ沿用026 Lv5检查点、standard准备（移除其他火系手段，保留1个紅竜の炎核）、none/all_kill支援。",
        "前后仅加入并使用031永久奖励；不加入新外套，不追加普通战利品，不改变同行者。",
        "主线仅拿潜行煤の亡霊的一枚魔力果实。全探索按各区首遇选择果实：森狼、砦二层、熱岩トカゲ、火の精霊、屍鬼、煤の亡霊、氷の番兵、宿屋刺客。",
        "Boss奖励保持：五种霊薬各1，分身魔力果实2，墓守生命果实2；イグニス之前不含屋敷和宿屋袭击。",
        "全探索是奖励获取条件上界；不同支线有互斥条件，未计算取得前的消耗/死亡。这里报告单场条件胜率，不是连续通关率。",
        "旧报告样本量可能不同，故同时列配对差与相对旧报告差，任一超限均按超限处理。", "",
        "|最终战|职业|模式|上一报告|旧剧本复现|031|配对差pp|相对旧报告pp|上限pp|",
        "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in result["rows"]:
        lines.append(f"|{row['encounter']}|{row['character']}|{row['mode']}|{row['previous']*100:.2f}%|"
                     f"{row['before']['win_rate']*100:.2f}%|{row['after']['win_rate']*100:.2f}%|"
                     f"{row['uplift_pp']:+.2f}|{row['previous_diff_pp']:+.2f}|{row['limit_pp']}|")
    lines += ["", f"超限组数：{len(result['violations'])}。", "",
        "设计负责人本轮授权：+5仍超限则在相同区域发放方式下改+3，复跑后采用并继续；霊薬始终+2。",
        "JSON包含每组输入快照、领取数量、消耗、败因及代码指纹。旧031全量发放报告已被本区域方案取代。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--fruit-amount", type=int, choices=(3, 5), default=5)
    parser.add_argument("--characters", nargs="+", choices=ch5.CHARACTERS, default=list(ch5.CHARACTERS))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.n, args.seed, args.characters, args.fruit_amount)
    output = args.output or checkpoints.ROOT / f"eval/reports/balance-2026-10-13-regional-plus{args.fruit_amount}"
    output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    return int(bool(result["violations"]))


if __name__ == "__main__":
    raise SystemExit(main())
