from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from host import combat, state

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIO = ROOT / "host/prompt/processed/dragon_rpg.json"
DEFAULT_CHECKPOINTS = ROOT / "eval/balance/checkpoints.json"


def fresh_session(pack: dict[str, Any], character_id: str) -> dict[str, Any]:
    template = next(c for c in pack["characters"] if c["id"] == character_id)
    scene_id = pack["meta"]["initial_scene"]
    return {"id": "balance", "scenario_pack": pack, "gm_mode": "full",
            "character": state._character_from_template(template, pack),
            "world_state": {"scene_id": scene_id, "location_id": state._resolve_initial_location(pack, scene_id)},
            "flags": {}, "companion": None, "game_over": None, "combat": None,
            "event_log": [], "system_logs": [], "messages": [], "dice_log": [], "choices": []}


def proposed_routes() -> dict[str, list[str]]:
    forest = ["go_dark_forest:success"]
    lost = forest + ["@victory"]
    spring = lost + ["ignore_lost_goblin:success", "@victory"]
    wolves = spring + ["continue_from_elf_spring"]
    slime1 = spring + ["rest_at_elf_spring"]
    fort = lost + ["help_lost_goblin"]
    fort2 = fort + ["@victory"]
    right = fort2 + ["@victory", "explore_fort_right"]
    guards = right + ["@victory", "admit_no_password"]
    fourth = guards + ["@victory"]
    village = wolves + ["@victory", "leave_forest_for_village"]
    fireslime = village + ["approach_burning_village_carefully:success"]
    frozen = fireslime + ["@victory"]
    xanxus = frozen + ["skip_frozen_clue_before_xanxus", "bluff_xanxus:failure"]
    ice = frozen + ["investigate_frozen_village"]
    frost = ice + ["@victory"]
    return {
        "dark_forest_loc": forest, "lost_goblin_crossroads": lost,
        "forest_wolves": wolves, "slime_ambush_one": slime1,
        "slime_ambush_two": slime1 + ["@victory"], "slime_king_battle": slime1 + ["@victory", "@victory"],
        "goblin_fort": fort, "goblin_fort_first_second": fort2,
        "goblin_fort_second_right": right,
        "goblin_fort_second_left": fort2 + ["@victory", "explore_fort_left"],
        "goblin_fort_third_guards": guards, "goblin_fort_fourth": fourth,
        "goblin_fort_chest_fight": fourth + ["@victory", "steal_lost_goblin_box"],
        "village_fire_slime": fireslime,
        "village_fire_elemental": village + ["enter_burning_village_directly"],
        "xanxus_battle": xanxus,
        "warlock_rescue_battle": xanxus + ["@defeat", "refuse_xanxus_with_rescue"],
        "ice_elemental_encounter": ice, "frost_wolf_battle": frost,
        "dragon_valley_loc": frost + ["@victory", "accept_ian_request"],
        "merchant_battle": ["go_inn", "ask_robin_rumor", "return_castle_from_inn", "go_alley",
                            "wait_for_night_in_alley", "hear_curse_offer_{character}",
                            "accept_curse_offer_{character}", "betray_cursed_merchant"],
    }


def replay_step(session: dict[str, Any], step: str) -> dict[str, Any]:
    source = state.current_location_id(session)
    if step.startswith("@"):
        encounter = combat._encounter_for_session(session, session["scenario_pack"])
        if not encounter["enemy_ids"]:
            raise ValueError(f"No encounter at {source}")
        if step == "@victory":
            enemies = [next(e for e in session["scenario_pack"]["enemies"] if e["id"] == enemy_id)
                       for enemy_id in encounter["enemy_ids"]]
            delta = combat._victory_delta(session, enemies, encounter)
        else:
            delta = deepcopy(encounter["defeat_effects"])
        state.apply_state_delta(session, delta, allow_world_transition=True)
    else:
        action_id, _, outcome = step.partition(":")
        action = state.resolve_action(session, action_id=action_id)
        if action is None or not state.action_requirement_status(action, session)[0]:
            raise ValueError(f"Unavailable checkpoint action: {source}/{step}")
        dc = action.get("roll", {}).get("dc", 0)
        roll = {"dc": dc, "success": outcome != "failure"} if dc else {}
        result = state.apply_action_result(session, action, roll)
        delta = result["state_delta"]
    session.pop("combat_start_requested", None)
    return {"location": source, "step": step, "delta": deepcopy(delta)}


def generate(path: Path = DEFAULT_SCENARIO) -> dict[str, Any]:
    pack = state.load_scenario_pack(path)
    characters = [c["id"] for c in pack["characters"] if c.get("selectable", True)]
    output: dict[str, Any] = {
        "scenario": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
        "scenario_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "notes": [
            "TODO(design): 以下路线只是可达的 proposed 装备快照，不能唯一代表正常推进；请审定同伴、支线与装备选择。",
            "从角色模板开始，按列出的动作和战斗奖励推导；先前战斗假定获胜，不估算其药草消耗。每场模拟 HP/MP/SP 回满，不代表连续闯关胜率。",
            "出城前邀请无需付费/判定的 blue_robed_mage；离开森林按剧情 clear_companion。没有叠加互斥同伴。",
            "勇者除商人支线外先完成锻冶师换剑；原装备失去后由现有引擎自动装备新武器。其他职业不臆造购物。",
            "模板金币为 0，check_supplies 没有发钱效果；未把支度金叙述当作金币。未假定回城购买或卖战利品。",
            "森林出口主线选双狼支线；砦三层选择无口令警卫战，即使右路已给出口令也按这条可达路线记录。",
            "TODO(design): 跨战斗消耗、双狼/史莱姆/砦分支、火コウモリ竜及ロビン取舍不能由数据确定。",
        ], "encounters": {}}
    for encounter, route in proposed_routes().items():
        entry: dict[str, Any] = {"status": "proposed", "characters": {}, "notes": []}
        for character_id in characters:
            session = fresh_session(pack, character_id)
            steps = ["go_magic_shop", "invite_blue_mage", "return_castle_from_magic_shop"]
            if character_id == "hero" and encounter != "merchant_battle":
                steps += ["go_forge", "show_sword_to_blacksmith", "accept_sword_fusion", "return_castle_from_forge"]
            steps += [step.format(character=character_id) for step in route]
            sources = [replay_step(session, step) for step in steps]
            if state.current_location_id(session) != encounter:
                raise ValueError(f"Route ended at wrong location: {encounter}")
            actor = session["character"]
            entry["characters"][character_id] = {
                "inventory": deepcopy(actor["inventory"]), "equipment": deepcopy(actor["equipment"]),
                "gold": actor["gold"], "companion": deepcopy(session["companion"]), "sources": sources}
        if encounter == "merchant_battle":
            entry["notes"].append("先拿本职业诅咒装备，再背叛商人；未支付代价，未提前拿胜利奖励暗黒の水晶球。")
        if encounter == "warlock_rescue_battle":
            entry["notes"].append("引擎替换为 player_character_id=warlock，忽略原职业背包并禁用同伴；模拟只计一名 guest。")
        if encounter == "dragon_valley_loc":
            entry["notes"].append("接受イアン请求获得氷鉄の大剣；是否替换已装备武器沿用引擎，不自动优化配装。")
        output["encounters"][encounter] = entry
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--output", type=Path, default=DEFAULT_CHECKPOINTS)
    args = parser.parse_args()
    args.output.write_text(json.dumps(generate(args.scenario), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
