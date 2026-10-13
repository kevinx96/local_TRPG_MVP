"""Offline boss checkpoint comparison; previous-report gate is in rewards_gate.py."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

from host import combat, shops, state
from scripts.scenario.rewards_battlefield import DROPS
from . import ch5, checkpoints, sim


BASE_COMMIT = "b653265"
CHARACTERS = ch5.CHARACTERS
FINAL_STEPS = ["@victory", "examine_ignis_wound", "return_to_castle_report",
               "enter_festival_town", "go_report_hall", "report_with_evidence"]
MAIN_STEPS = ["go_dark_forest", "@victory", "crossroads_forward", "continue_from_elf_spring",
              "distract_forest_wolves", "leave_forest_for_village", "approach_burning_village_carefully:success",
              "@victory", "leave_burning_house", "inspect_frost_core:success", "skip_frozen_clue_before_xanxus",
              "bluff_xanxus:failure", "@defeat", "refuse_xanxus_with_rescue", "@victory",
              "skip_frozen_clue_after_xanxus", "sneak_through_ash:success", "cross_lava_bridge:success",
              "continue_after_warlock", "enter_dragon_nest"]


def consume_boosts(session: dict[str, Any]) -> None:
    session.pop("combat_start_requested", None)
    for item in list(session["character"]["inventory"]):
        if combat.item_combat_spec(item).get("kind") == "permanent":
            for _ in range(item.get("quantity", 1)):
                shops.use_item(session, item["id"])


def snapshot(session: dict[str, Any]) -> dict[str, Any]:
    actor = session["character"]
    return {**{key: deepcopy(actor[key]) for key in (
        "level", "inventory", "equipment", "gold", "skills", "attributes", "max_hp", "max_mp", "max_sp")},
        "completed_milestones": deepcopy(session.get("completed_milestones", [])),
        "companion": deepcopy(session.get("companion"))}


def build_snapshot(pack: dict[str, Any], cp: dict[str, Any], character: str, boss: str,
                   mode: str) -> tuple[dict[str, Any], list[str]]:
    session = checkpoints.fresh_session(pack, character)
    if mode == "main":
        steps = ["@opening", "check_supplies", "go_castle_town", "go_magic_shop", "invite_blue_mage",
                 "return_castle_from_magic_shop"]
        if character == "hero":
            steps += ["go_forge", "show_sword_to_blacksmith", "accept_sword_fusion", "return_castle_from_forge"]
        steps += MAIN_STEPS
    else:
        steps = [source["step"] for source in cp["encounters"]["dragon_valley_loc"]["characters"][character]["sources"]]
        index = steps.index("ignore_lost_goblin:success")
        # Returning the box now closes the ignore branch; continue directly from the crossroads.
        steps[index:index + 2] = ["help_lost_goblin", "enter_goblin_fort", "@victory", "@victory",
            "explore_fort_right", "@victory", "admit_no_password", "@victory", "@victory", "return_lost_goblin_box"]
        steps.insert(steps.index("continue_from_elf_spring"), "observe:glowing_moss_patch")
        index = steps.index("leave_forest_for_village")
        steps[index:index] = ["exit_back", "wolves_back", "inspect_spring_wall", "decode_seal:success", "@victory",
            "cave_left", "@victory", "open_lava_chest", "lava_back", "cave_right", "talk_mina", "escort_mina",
            "hot_spring_forward", "@victory", "@victory", "leave_prism_tree", "continue_from_elf_spring",
            "pass_cleared_wolves", "return_inn_after_forest", "go_item_shop", "give_moss_to_sarah",
            "return_castle_from_item_shop", "go_forge", "return_robert_hammer", "return_castle_from_forge",
            "go_magic_shop", "report_mina_safe", "forge_prism_weapon", "return_castle_from_magic_shop", "return_forest_exit"]
    if boss == "draco_battle":
        steps += FINAL_STEPS
    for step in steps:
        checkpoints.replay_step(session, step)
        consume_boosts(session)
    if state.current_location_id(session) != boss:
        raise ValueError(f"Snapshot route did not reach {boss}")
    if mode == "explore":
        # As in earlier reward-only controls: prior optional victories are assumed.
        # Complete the reward pool without using the final boss's own drop in its fight.
        for location_id in DROPS:
            if boss == "dragon_valley_loc" and location_id in {"mansion_corridor", "inn_night_ambush"}:
                continue
            location = next((loc for loc in pack["locations"] if loc["id"] == location_id), None)
            if location is None:
                continue
            staging = deepcopy(session, {id(pack): pack})
            staging["world_state"] = {"scene_id": location["scene_id"], "location_id": location_id}
            encounter = combat._encounter_for_session(staging, pack)
            if all(session["flags"].get(combat._defeated_flag(e, location_id)) for e in encounter["enemy_ids"]):
                continue
            enemies = [next(e for e in pack["enemies"] if e["id"] == eid) for eid in encounter["enemy_ids"]]
            reward = combat._victory_delta(staging, enemies, encounter)
            delta = {key: value for key, value in reward.items() if key in {"inventory_add", "gold_change", "flags_set"}}
            state.apply_state_delta(session, delta)
            consume_boosts(session)
        if "gravekeeper_cloak" in {i["id"] for i in pack["items"]}:
            cloak = next(i for i in pack["items"] if i["id"] == "gravekeeper_cloak")
            state.apply_state_delta(session, {"inventory_add": [{**cloak, "quantity": 1}], "equip_item": cloak["name"]})
        if boss == "draco_battle":
            state.apply_state_delta(session, ch5.cases()["all_kill"])
    cell = snapshot(session)
    cell["sources"] = steps
    cell["flags"] = deepcopy(session["flags"])
    return cell, steps


def evaluate(n: int, seed: int) -> dict[str, Any]:
    root = checkpoints.ROOT
    baseline_path = root / ".tmp-test/031/baseline.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_bytes(subprocess.check_output(
        ["git", "show", f"{BASE_COMMIT}:host/prompt/processed/dragon_rpg.json"], cwd=root))
    paths = {"before": baseline_path, "after": checkpoints.DEFAULT_SCENARIO}
    packs = {label: state.load_scenario_pack(path) for label, path in paths.items()}
    snapshots = {label: checkpoints.generate(path) for label, path in paths.items()}
    result: dict[str, Any] = dict(n=n, seed=seed, baseline_commit=BASE_COMMIT, rows=[], violations=[], snapshots={},
        fruit_amount=next(i["combat"]["amount"] for i in packs["after"]["items"] if i["id"] == "fruit_life"))
    for mode in ("main", "explore"):
        for boss in ("dragon_valley_loc", "draco_battle"):
            for character in CHARACTERS:
                rates = {}
                for label, pack in packs.items():
                    cell, _ = build_snapshot(pack, snapshots[label], character, boss, mode)
                    trial_cp = {"encounters": {boss: {"characters": {character: cell}}}}
                    row = sim.simulate(pack, boss, character, n=n, seed=seed, checkpoints=trial_cp,
                                       purify=False, initial_delta={"flags_set": [f for f, v in cell["flags"].items() if v]})
                    rates[label] = row
                    result["snapshots"][f"{mode}/{boss}/{character}/{label}"] = cell
                uplift = 100 * (rates["after"]["win_rate"] - rates["before"]["win_rate"])
                row = dict(mode=mode, encounter=boss, character=character, before=rates["before"],
                           after=rates["after"], uplift_pp=round(uplift, 6), limit_pp=5 if mode == "main" else 15)
                result["rows"].append(row)
                if uplift > row["limit_pp"] + 1e-9:
                    result["violations"].append({k: row[k] for k in ("mode", "encounter", "character", "uplift_pp", "limit_pp")})
                print(f"{mode}/{boss}/{character}: {rates['before']['win_rate']:.3f} -> {rates['after']['win_rate']:.3f} ({uplift:+.2f}pp)", flush=True)
    result["fingerprints"] = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in (checkpoints.DEFAULT_SCENARIO, Path(__file__), root / "host/combat.py", root / "host/shops.py")}
    return result


def markdown(result: dict[str, Any]) -> str:
    lines = ["# 031 永久奖励：最终战配对检查", "",
        "注意：本报告的准备条件与上一报告不同，不能据此判定任务第1.3节未触发。区域方案以 balance-2026-10-13-regional-plus5.md、regional-plus3.md 的旧口径复核为准。", "",
        f"N={result['n']}/职业/条件，seed={result['seed']}；离线真实引擎、heuristic、关闭净化。",
        f"修改前为提交 `{result['baseline_commit']}` 的剧本，修改后为本次剧本。每场HP/MP/SP补满；前序战斗假定获胜，继承真实动作产生的等级、装备和有限背包。",
        "这是到达最终战后的条件胜率，不是从开局连续通关率。每种玩家的前后使用相同路线和准备规则。", "",
        "- 主线：只打入口史莱姆和村庄成功判定分支的火史莱姆；十字路直接前进，携帯食引狼，结冰处取证，经历原有Xanxus剧情战和ワーロック操控战，潜行穿过煤の亡霊。判定按检查点惯例取成功，未取得可选战斗掉落。潜行成功按031拿一枚魔力果实并使用。",
        "- 全探索：沿用015/017实际砦、洞窟、交付与虹晶武器路线；在已获得奖励之外补齐所有可选遭遇的胜利掉落。イグニス前排除第5章掉落；ドラコ前加入已有全部击杀路线支援。保留自然火系技能，不使用旧报告的去火标准准备。新外套自动装备，永久品全部使用。",
        "- 全探索补齐部分是奖励条件上界，部分路线互斥/回访或取得前的消耗与死亡没有建模；不会把这些条件胜率标成全探索连续通关率。同行者取原检查点路线，不额外指定火コウモリ竜。", "",
        "|玩家|最终战|职业|修改前|031|增幅pp|上限pp|", "|---|---|---|---:|---:|---:|---:|"]
    for row in result["rows"]:
        lines.append(f"|{row['mode']}|{row['encounter']}|{row['character']}|{row['before']['win_rate']*100:.2f}%|{row['after']['win_rate']*100:.2f}%|{row['uplift_pp']:+.2f}|{row['limit_pp']}|")
    previous_prism = json.loads((checkpoints.ROOT / "eval/reports/balance-2026-10-12-prism.json").read_text(encoding="utf-8"))
    previous_support = json.loads((checkpoints.ROOT / "eval/reports/balance-2026-10-12-support3.json").read_text(encoding="utf-8"))
    ignis = {r["character"]: r for r in previous_prism["weapons"]}
    draco = {(r["character"], r["case"]): r for r in previous_support["supports"]}
    lines += ["", "## 与上一份单场报告的差（口径有变化）", "",
        "イグニス参照017的原装备/虹晶武器，ドラコ参照026的none/all_kill。旧报告不含031全探索掉落池，且026剔除了其他火系手段，故下表不是纯数值因果差；需按旧准备条件另行复核停止阈值。最新029报告只到イグニス，统计连续路线通关率，不能直接冒充两场Boss的单场胜率。", "",
        "|玩家|最终战|职业|上一报告|031|差pp|", "|---|---|---|---:|---:|---:|"]
    for row in result["rows"]:
        if row["encounter"] == "dragon_valley_loc":
            old = ignis[row["character"]]["before" if row["mode"] == "main" else "after"]
        else:
            old = draco[(row["character"], "none" if row["mode"] == "main" else "all_kill")]["win_rate"]
        new = row["after"]["win_rate"]
        lines.append(f"|{row['mode']}|{row['encounter']}|{row['character']}|{old*100:.2f}%|{new*100:.2f}%|{(new-old)*100:+.2f}|")
    lines += ["", f"本报告配对差超过数值上限的组数：{len(result['violations'])}；不代表任务停止阈值通过。", "",
              f"JSON包含全部输入快照、路线、物品数量、旗标、消耗、败因及文件SHA-256。霊薬+2，果实+{result['fruit_amount']}。", "",
              "```powershell", f"python -X utf8 -m scripts.balance.rewards --n {result['n']} --seed {result['seed']}", "```", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--output", type=Path, default=checkpoints.ROOT / "eval/reports/balance-2026-10-13-rewards")
    args = parser.parse_args()
    result = evaluate(args.n, args.seed)
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    return int(bool(result["violations"]))


if __name__ == "__main__":
    raise SystemExit(main())
