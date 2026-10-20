from __future__ import annotations

import argparse
import hashlib
import json
import time
from copy import deepcopy
from pathlib import Path
from statistics import mean, median
from typing import Any, Optional

from host import combat, state
from . import budget, checkpoints, route_v2, sim
from .archetypes import ARCHETYPES

SOURCE = "docs/design/balance-v2-decision-metrics.md §§1.1, 1.2, 1.4 (原始存档已丢失)"
HUMAN_TIMELINE = (
    ("slime_king_battle", "スライム王", "boss", 9, 20, 30),
    ("cave_heat_corridor", "熱岩トカゲ×2", "elite", 5, 18, 30),
    ("cave_crystal_corridor", "炎のウィスプ×3", "elite", 5, 11, 30),
    ("cave_prism_tree", "虹晶樹", "boss", 26, 26, 30),
    ("forest_wolves", "森狼", "elite", 2, 30, 30),
    ("ice_elemental_encounter", "氷の精霊", "elite", 2, 27, 35),
    ("frost_wolf_battle", "氷霜の巨狼", "boss", 3, 35, 35),
    ("dragon_valley_loc", "邪竜イグニス", "boss", 20, 29, 40),
    ("mansion_corridor", "氷の番兵×2", None, 4, 40, 40),
)
THREAT_REFERENCES = {
    "lost_goblin_crossroads": ([.04, .11], [.5, .9]),
    "slime_ambush_one": ([.04, .11], [.5, .9]),
    "slime_ambush_two": ([.04, .11], [.5, .9]),
    "village_fire_slime": ([.04, .04], [1.18, 1.18]),
    "goblin_fort_second_right": ([.08, .08], [1.09, 1.09]),
    "forest_wolves": ([.17, .17], [.9, 1.1]),
    "goblin_fort_second_left": ([.17, .17], [.9, 1.1]),
    "ice_elemental_encounter": ([.16, .16], [.9, .9]),
    "slime_king_battle": ([.23, .23], [.59, .59]),
    "merchant_battle": ([.18, .18], [.83, .83]),
    "frost_wolf_battle": ([.10, .10], [1.12, 1.12]),
    "dragon_valley_loc": ([.14, .14], [1.21, 1.21]),
    "draco_battle": ([.18, .18], [.45, .45]),
    "cave_heat_corridor": ([.30, .41], [.3, .5]),
    "cave_lava_room": ([.30, .41], [.3, .5]),
    "cave_crystal_corridor": ([.30, .41], [.3, .5]),
    "goblin_fort_fourth": ([.41, .41], [.94, .94]),
}


def berserker_checkpoints(pack: dict[str, Any]) -> dict[str, Any]:
    """Observed human configuration, separate from the at-most-three-interaction route."""
    session = checkpoints.fresh_session(pack, "hero")
    for milestone in sorted(pack["milestones"], key=lambda m: m["level"]):
        state.apply_state_delta(session, {"flags_set": [milestone["trigger_flag"]]})
    actor = session["character"]
    # The document fixes this inventory, rather than claiming to reconstruct missing actions.
    wanted = {"iron_sword": 1, "ruby_charm": 1, "ice_charm": 1, "herb": 7,
              "healing_scroll": 9, "fruit_life": 3}
    catalog = {item["id"]: item for item in pack["items"]}
    leather = next(item for item in actor["inventory"] if item["name"] == "革の鎧")
    actor["inventory"] = [deepcopy(leather), *[{**deepcopy(catalog[key]), "quantity": quantity}
                                            for key, quantity in wanted.items()]]
    actor["gold"] = 706
    actor["equipment"] = ["鉄の剣", "革の鎧", "紅玉の護符"]
    state._normalize_character(actor)
    companion = deepcopy(next(c for c in pack["companions"] if c["id"] == "fire_bat_dragon"))
    entry = {key: deepcopy(actor[key]) for key in ("level", "attributes", "inventory", "equipment", "gold", "max_hp", "max_mp", "max_sp")}
    entry.update(companion=companion, completed_milestones=session["completed_milestones"],
                 flags={"fire_bat_empowered": True}, source=SOURCE)
    greatsword = deepcopy(entry)
    greatsword["inventory"].append({**deepcopy(catalog["ice_iron_greatsword"]), "quantity": 1})
    greatsword["equipment"][0] = catalog["ice_iron_greatsword"]["name"]
    alone = {**deepcopy(entry), "companion": None}
    return {"version": 2, "source": SOURCE, "status": "document_reconstruction",
            "notes": ["未取得原始存档；仅复原明确记录的资源，不推造遗漏的支线和行动。",
                      "TODO(design): 四种霊薬的具体品种未记录，剧本中有五种；保留未知清单，不任选四种加入可用背包。",
                      "706G 和回复库存来自通关后清单，非 Ignis 开战前的独立快照。"],
            "unresolved_inventory": [{"type": "霊薬", "distinct_types": 4, "quantity_each": 1}],
            "encounters": {"dragon_valley_loc": {"status": "document_reconstruction", "characters": {"hero": entry}}},
            "profiles": {"human_berserker": entry, "P0b + 氷鉄の大剣": greatsword, "无同伴": alone}}


def checkpoint_session(pack: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    cp = {"encounters": {"dragon_valley_loc": {"characters": {"hero": entry}}}}
    session = sim.prepare_session(pack, "dragon_valley_loc", "hero", cp)
    session["flags"].update(entry.get("flags", {}))
    return session


def checkpoint_trials(pack: dict[str, Any], data: dict[str, Any], n: int, seed: int) -> dict[str, Any]:
    import random
    from unittest.mock import patch

    profiles = {}
    for name, entry in data["profiles"].items():
        trials = []
        for index in range(n):
            session = checkpoint_session(pack, entry)
            rng = random.Random(sim.trial_seed(seed, "dragon_valley_loc", "hero", index))
            with patch.object(combat, "random", rng), patch.object(state, "random", rng):
                trials.append(route_v2.fight(session, "best_free", rng))
        incoming = mean(t["opening"]["expected_damage"] for t in trials)
        healing = mean(t["expected_healing"] for t in trials)
        profiles[name] = {"n": n, "win_rate": mean(t["status"] == "victory" for t in trials),
                          "rounds_median": median(t["rounds"] for t in trials),
                          "expected_incoming": incoming, "expected_healing": healing,
                          "sustain_coverage": healing / incoming if incoming else None,
                          "sample": trials[0]}
    return profiles


def distance(value: float, interval: list[float]) -> float:
    return max(interval[0] - value, 0, value - interval[1])


def threat_scan(pack: dict[str, Any], cp: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for encounter, (ratio_target, cv_target) in THREAT_REFERENCES.items():
        session = sim.prepare_session(pack, encounter, "hero", cp, companion=False)
        actor = session["character"]
        actor["equipment"] = ["革の鎧"]
        actor["combat"]["defense"] = 0
        actor["combat"]["evade"] = 0
        combat.ensure_combat_started(session)
        moments = budget.phase_moments(session)
        conditional = budget.phase_moments(session, damaging_only=True)
        passed = distance(moments["ratio"], ratio_target) <= .02 + 1e-12 and moments["cv"] is not None and distance(moments["cv"], cv_target) <= .1 + 1e-12
        rows.append({"encounter": encounter, "level": actor["level"], "max_hp": actor["max_hp"],
                     **moments, "reference_ratio": ratio_target, "reference_cv": cv_target,
                     "status": "pass" if passed else "fail", "attack_conditioned": conditional,
                     "difference_reason": {
                         "merchant_battle": "亡霊転換权重1/6，不直接造成HP伤害；文档18%/0.83近似为只在攻击发生条件下的均值/CV。真实AI的零伤害回合必须计入M9/M10。",
                         "draco_battle": "護衛の構え权重1/6，零直接伤害；文档18%/0.45近似为只在攻击发生条件下的均值/CV。真实AI的防御回合必须计入M9/M10。",
                     }.get(encounter) if not passed else None})
    return rows


def gates(rows: list[dict[str, Any]], profiles: dict[str, Any], threats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hero = next(r for r in rows if r["archetype"] == "P0b" and r["character"] == "hero")
    human = profiles["human_berserker"]
    return [{"id": "A.4.1", "value": hero["completion_rate"], "target": "> 0.90", "pass": hero["completion_rate"] > .90},
            {"id": "A.4.2", "value": human["rounds_median"], "target": [17, 22], "pass": 17 <= human["rounds_median"] <= 22},
            {"id": "A.4.3", "value": human["sustain_coverage"], "target": "> 1", "pass": human["sustain_coverage"] > 1},
            {"id": "A.4.4", "value": sum(t["status"] == "pass" for t in threats), "target": len(threats),
             "pass": all(t["status"] == "pass" for t in threats)}]


def markdown(result: dict[str, Any]) -> str:
    lines = ["# 046 测量 v2：复现门槛诊断", "", "未取得原始存档。参照：" + SOURCE + "。",
             "", "当前状态：" + result["status"] + "。依 spec §6，复现门槛未通过时停止后续扩展。",
             "", "主通关口径：冒険完了；Ignis 击败/净化另列。全部试验离线，不调用 LLM。", "",
             "| 原型 | 职业 | N | 通关率 | Ignis | 到终局 | Ignis 回合中位数 |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for row in result["rows"]:
        lines.append(f"| {row['archetype']} | {row['character']} | {row['n']} | {row['completion_rate']:.1%} | {row['ignis_rate']:.1%} | {row['terminal_rate']:.1%} | {row['ignis_rounds_median']} |")
    lines += ["", "| 复现检查 | 实测 | 目标 | 通过 |", "|---|---|---|---|"]
    for gate in result["gates"]:
        lines.append(f"| {gate['id']} | {gate['value']} | {gate['target']} | {gate['pass']} |")
    lines += ["", "| 配置探针（勇者） | 胜率 | 回合中位数 | 每回合期望受伤 | 每回合回复 | S |",
              "|---|---:|---:|---:|---:|---:|"]
    for name, row in result["checkpoint_probes"].items():
        lines.append(f"| {name} | {row['win_rate']:.1%} | {row['rounds_median']} | {row['expected_incoming']:.4f} | {row['expected_healing']:.1f} | {row['sustain_coverage']:.4f} |")
    lines += ["", "| 威胁对照（勇者，防御1/回避0，无同伴） | 等级/HP | M9 | 文档M9 | M10 CV | 文档CV | 状态 |",
              "|---|---|---:|---|---:|---|---|"]
    for row in result["threat_scan"]:
        lines.append(f"| {row['encounter']} | {row['level']}/{row['max_hp']} | {row['ratio']:.2%} | {row['reference_ratio']} | {row['cv']:.4f} | {row['reference_cv']} | {row['status']} |")
    lines += ["", "威胁表超出容差的逐项说明：", ""]
    for row in result["threat_scan"]:
        if row["status"] == "fail":
            conditioned = row["attack_conditioned"]
            lines.append(f"- {row['encounter']}：{row['difference_reason']} 条件化后为 {conditioned['ratio']:.2%} / CV {conditioned['cv']:.4f}。")
    lines += ["", "教学 tutorial_slime 不属于普通スライム的4–11%行；其首回合固定8点真实伤害（Lv1为40%，CV=0），另行排除。大ゴブリン对照映射为 goblin_fort_second_right，不映射为小ゴブリン加弓手场。"]
    lines += ["", "## 差异与排查", "", *["- " + note for note in result["findings"]],
              "", "## 尚未进行", "", "因 A.4 复现失败，尚未交付完整 P1/P2/P3/P2s/P0g、M1–M13、targets v2、准备移除试验和存档遥测工具。未将未实现的指标伪标为 not_applicable。",
              "", f"运行时长：{result['elapsed_seconds']:.2f} 秒；seed={result['seed']}；workers={result['workers']}。", ""]
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="046 A.4 reproduction gate; stop on failure")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path, default=route_v2.DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if args.n < 1 or args.workers < 1:
        parser.error("n and workers must be positive")
    started = time.perf_counter()
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    data = berserker_checkpoints(pack)
    route_v2.BERSERKER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    records = route_v2.run_jobs([(checkpoints.DEFAULT_SCENARIO, a, c, args.n, args.seed)
                                for a in ("P0a", "P0b") for c in ("hero", "cleric", "mage", "thief")], args.workers)
    rows = route_v2.summarize(records)
    profiles = checkpoint_trials(pack, data, args.n, args.seed)
    threats = threat_scan(pack, cp)
    checks = gates(rows, profiles, threats)
    result = {"version": 2, "status": "reproduced" if all(g["pass"] for g in checks) else "stopped_at_reproduction_gate",
              "source": SOURCE, "original_save_available": False, "seed": args.seed, "n": args.n, "workers": args.workers,
              "rows": rows, "gates": checks, "checkpoint_probes": profiles, "threat_scan": threats,
              "human_timeline": [dict(encounter=e, name=name, encounter_class=kind, rounds=r, hp=hp, max_hp=maximum)
                                 for e, name, kind, r, hp, maximum in HUMAN_TIMELINE],
              "archetypes": {key: value.to_dict() for key, value in ARCHETYPES.items()},
              "samples": [next(t for t in records if t["archetype"] == row["archetype"] and t["character"] == row["character"]) for row in rows],
              "findings": ["严格 P0b 的三项可选交互为：国王提示、购买氷の護符、尝试借火コウモリ竜；借用有真实判定，不强行成功（当前勇者判定成功概率55%）。",
                           "accept_ian_request 作为直接主线路径行动执行，获得的氷鉄の大剣按 P0b 规则装备；P0a 保留初始配装。",
                           "精霊の泉三次休息统一安排在首次到泉时；第一次触发三场スライム连战。该排程是推断，文档未给时间点。",
                           "主线森林之前没有升级旗标，スライム王开战为 Lv1/20HP；试玩参照为30HP，需要额外成长或不同休息排程。",
                           "强化火コウモリ竜和紅玉の護符需要洞窟；严格三次交互 P0b 不包含此链，不能把人类 checkpoint 当作路线原型。",
                           "不补造第四种霊薬；恢复库存为文档通关后快照，只用于独立配置探针。"],
              "fingerprints": {str(path.relative_to(checkpoints.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                               for path in (checkpoints.DEFAULT_SCENARIO, checkpoints.DEFAULT_CHECKPOINTS)},
              "elapsed_seconds": time.perf_counter() - started}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "gates": checks, "elapsed_seconds": result["elapsed_seconds"]}, ensure_ascii=False, indent=2))
    return int(not all(g["pass"] for g in checks))


if __name__ == "__main__":
    raise SystemExit(main())
