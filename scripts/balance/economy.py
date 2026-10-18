"""Measure optional-battle costs and fit ordinary gold rewards without changing enemies."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import patch

from host import combat, state
from scripts.scenario.rewards_battlefield import BATTLEFIELD
from . import battlefield, checkpoints, ch5, rewards, sim

BONUSES = checkpoints.ROOT / "eval/balance/rewards_economy.json"
EXCLUDED = {"dark_forest_loc", "dragon_valley_loc", "draco_battle", "xanxus_battle", "warlock_rescue_battle"}


def prices(pack: dict[str, Any]) -> dict[str, int]:
    catalog = {i["id"]: i for i in pack["items"]}
    result = {}
    for shop in pack["shops"]:
        for offer in shop["items"]:
            item = catalog[offer["item_id"]]
            if combat.item_combat_spec(item).get("consumable", False) and combat.item_combat_spec(item).get("kind") != "permanent":
                # A replacement at the undiscounted shop price is a conservative cost.
                result[item["id"]] = result[item["name"]] = max(result.get(item["id"], 0), offer["price"])
    return result


def chapter(location: str) -> int:
    if location == "merchant_battle":
        return 1
    if location in {"inn_night_ambush", "mansion_corridor"}:
        return 5
    if location.startswith(("valley_", "xanxus_phantom")):
        return 4
    if location in BATTLEFIELD or location.startswith(("village_", "ice_elemental", "frost_wolf", "gorge_")):
        return 3
    return 2


def encounter_checkpoint(pack: dict[str, Any], cp: dict[str, Any], location: str, character: str) -> dict[str, Any]:
    if location in BATTLEFIELD or location.startswith("gorge_"):
        session = battlefield.forest_exit(pack, cp, character)
        state._set_companion(session, None)
        if location in {"ghoul_marsh", "grave_chapel"}:
            cloak = next(i for i in pack["items"] if i["id"] == "gravekeeper_cloak")
            state.apply_state_delta(session, {"inventory_add": [{**cloak, "quantity": 1}], "equip_item": cloak["name"]})
        cell = rewards.snapshot(session)
    else:
        source = location if location in cp["encounters"] else "draco_battle"
        cell = deepcopy(cp["encounters"][source]["characters"][character])
    return {"encounters": {location: {"characters": {character: cell}}}}


def measure(pack: dict[str, Any], cp: dict[str, Any], location: str, character: str,
            n: int, seed: int, shop_prices: dict[str, int]) -> dict[str, Any]:
    point = encounter_checkpoint(pack, cp, location, character)
    template = sim.prepare_session(pack, location, character, point)
    rewards.consume_boosts(template)
    template["combat_start_requested"] = True
    actor = template["character"]
    for resource in ("hp", "mp", "sp"):
        actor[resource] = actor[f"max_{resource}"]
    isolated = template["scenario_pack"]
    encounter = combat._encounter_for_session(template, isolated)
    enemies = [next(e for e in isolated["enemies"] if e["id"] == eid) for eid in encounter["enemy_ids"]]
    encounter.pop("victory_gold_bonus", None)
    delta = combat._victory_delta(template, enemies, encounter)
    reward = delta.get("gold_change", 0) + sum(
        shop_prices.get(i.get("id") or i["name"], 0)*i.get("quantity", 1) for i in delta.get("inventory_add", []))
    used: Counter = Counter()
    hp_lost = mp_lost = wins = 0
    rng = random.Random()
    with patch.object(combat, "random", rng):
        for index in range(n):
            rng.seed(sim.trial_seed(seed, location, character, index))
            session = deepcopy(template, {id(isolated): isolated})
            if not combat.ensure_combat_started(session):
                raise ValueError(f"Encounter did not start: {location}")
            while combat.combat_is_active(session):
                action, target = sim.choose_action(session, "heuristic", purify=False)
                if action["type"] == "item":
                    item = combat._find_entry(session["character"]["inventory"], action["id"], "item")
                    if combat.item_combat_spec(item).get("consumable", True):
                        used[item.get("id") or item["name"]] += 1
                combat.perform_combat_action(session, action["type"], action["id"], target, rng=rng)
            wins += session["combat"]["status"] == "victory"
            hp_lost += max(0, actor["hp"] - max(0, session["character"]["hp"]))
            mp_lost += max(0, actor["mp"] - session["character"]["mp"])
    consumed = sum(shop_prices.get(item, 0)*quantity/n for item, quantity in used.items())
    chapter_id = chapter(location)
    # Literal chapter minimum includes conditional / single-use free rest.
    cheapest = {1: 10, 2: 0, 3: 0, 4: 5, 5: 0}[chapter_id]
    paid = {1: 10, 2: 10, 3: 5, 4: 5, 5: 10}[chapter_id]
    missing_ratio = hp_lost/n/actor["max_hp"] + (mp_lost/n/actor["max_mp"] if actor["max_mp"] else 0)
    return dict(location=location, character=character, chapter=chapter_id, win_rate=wins/n,
                hp_lost=hp_lost/n, mp_lost=mp_lost/n, max_hp=actor["max_hp"], max_mp=actor["max_mp"],
                consumables={k: v/n for k, v in used.items()}, consumable_cost=consumed,
                rest_price=cheapest, paid_rest_price=paid, cost=consumed+cheapest*missing_ratio,
                conservative_cost=consumed+paid*missing_ratio, reward_on_victory_before=reward,
                revenue_before=wins/n*reward, snapshot=point["encounters"][location]["characters"][character])


def fit(rows: list[dict[str, Any]]) -> dict[str, int]:
    bonuses: dict[str, int] = {}
    for row in rows:
        if not row["win_rate"]:
            raise ValueError(f"No victories: {row['location']}/{row['character']}; gold cannot fix this checkpoint")
        needed = max(0, 1.3*row["conservative_cost"]/row["win_rate"]-row["reward_on_victory_before"])
        amount = (math.ceil(needed/5)*5+5) if needed else 0
        bonuses[row["location"]] = max(bonuses.get(row["location"], 0), amount)
    return bonuses


def markdown(result: dict[str, Any]) -> str:
    lines = ["# 031 非主线战斗经济（2026-10-13）", "",
        f"每战每职业 N={result['n']}，seed={result['seed']}，离线真实引擎、heuristic、不净化。",
        "排除主干入口史莱姆、两场最终战、剧情必败和guest；火史莱姆也列入，覆盖可选分支的普通战。四职业分别核算，掉落按最不利职业统一补偿。",
        "成本=消耗品商店买价+休息价格×(战后HP缺口/检查点最大HP+战后MP缺口/检查点最大MP)。MP上限0时该项为0；药草治疗后的净缺口避免重复计费。",
        "收益=胜率×(金币+可购买普通消耗品的买价)。败北也计入消耗，且不发收益。永久品、装备、任务物品按0估值。",
        "按章最低休息费：1章宿10G，2章精霊の泉0G，3章塔一次休息0G，4章避難所5G，5章信任后的王城0G。",
        "免费休息有剧情/次数条件，另列保守成本：按可重复付费休息10/10/5/5/10G计费，并以此更高成本调金币。商店多价格取未打折最高买价，成本与奖励同价。",
        "只有新增遭遇级金币；原普通物品和敌人强度不变。若需补偿，向上取5G再留5G抽样余量；相同规则覆盖区域果实已领完的精英。",
        "检查点：旧遭遇沿用既有到达快照；屋敷/宿袭用5章最终战前快照；古戦場用森林出口，沼地/骑士带塔中外套，无诅咒。各场补满、背包有限，不假装连续通关。", "",
        "|遭遇|职业|胜率|HP损失|MP损失|成本|保守成本|期望收益前|期望收益后|新增金币|收益/保守成本|",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in result["rows"]:
        ratio = r["revenue_after"]/r["conservative_cost"] if r["conservative_cost"] else None
        ratio_text = f"{ratio:.2f}" if ratio is not None else "成本0"
        lines.append(f"|{r['location']}|{r['character']}|{r['win_rate']*100:.1f}%|{r['hp_lost']:.2f}|{r['mp_lost']:.2f}|"
                     f"{r['cost']:.2f}|{r['conservative_cost']:.2f}|{r['revenue_before']:.2f}|{r['revenue_after']:.2f}|"
                     f"{r['gold_bonus']}|{ratio_text}|")
    lines += ["", f"低于1.3倍目标：{len(result['violations'])}组（按更严格的保守成本）。", "",
              "JSON提供价格表、消耗明细、输入快照与指纹；金币不改变本场战术和消耗，因此改前/改后收益使用同一批战斗样本配对计算。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261013)
    parser.add_argument("--fit", action="store_true", help="Write gold schedule; apply with scenario generator")
    parser.add_argument("--output", type=Path, default=checkpoints.ROOT / "eval/reports/battle-economy-2026-10-13")
    args = parser.parse_args()
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    locations = [l["id"] for l in pack["locations"] if l.get("combat", {}).get("encounter_class")
                 and l["id"] not in EXCLUDED]
    shop_prices = prices(pack)
    rows = []
    for location in locations:
        for character in ch5.CHARACTERS:
            row = measure(pack, cp, location, character, args.n, args.seed, shop_prices)
            rows.append(row)
            print(location, character, round(row["conservative_cost"], 2), flush=True)
    bonuses = fit(rows) if args.fit else json.loads(BONUSES.read_text(encoding="utf-8"))["gold_bonus"]
    if args.fit:
        BONUSES.write_text(json.dumps(dict(gold_bonus=bonuses, n=args.n, seed=args.seed), ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    for row in rows:
        row["gold_bonus"] = bonuses[row["location"]]
        row["revenue_after"] = row["revenue_before"] + row["win_rate"]*row["gold_bonus"]
    result = dict(n=args.n, seed=args.seed, rows=rows, prices=shop_prices, gold_bonus=bonuses,
                  violations=[dict(location=r["location"], character=r["character"]) for r in rows
                              if r["revenue_after"]+1e-9 < 1.3*r["conservative_cost"]])
    result["fingerprints"] = {str(p.relative_to(checkpoints.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (Path(__file__), checkpoints.DEFAULT_SCENARIO)}
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    return int(bool(result["violations"]))


if __name__ == "__main__":
    raise SystemExit(main())
