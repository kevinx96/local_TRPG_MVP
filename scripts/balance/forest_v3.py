from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import patch

from host import state
from . import checkpoints, route, sim

ENCOUNTERS = ("cave_heat_corridor", "cave_lava_room", "cave_crystal_corridor", "cave_prism_tree")
CHARACTERS = ("hero", "cleric", "mage", "thief")


def early_checkpoints(pack: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"encounters": {}}
    for encounter in ENCOUNTERS:
        result["encounters"][encounter] = {"characters": {}}
        for char in CHARACTERS:
            session = checkpoints.fresh_session(pack, char)
            for step in ("check_supplies", "go_magic_shop", "invite_blue_mage", "return_castle_from_magic_shop"):
                checkpoints.replay_step(session, step)
            actor = session["character"]
            result["encounters"][encounter]["characters"][char] = {
                **{key: deepcopy(actor[key]) for key in ("level", "inventory", "equipment", "gold", "skills", "attributes", "max_hp", "max_mp", "max_sp")},
                "companion": deepcopy(session["companion"]), "completed_milestones": []}
    return result


def weapon_checkpoints(pack: dict[str, Any], cp: dict[str, Any], char: str) -> dict[str, Any]:
    modified = deepcopy(cp)
    actor = modified["encounters"]["dragon_valley_loc"]["characters"][char]
    weapon = deepcopy(next(i for i in pack["items"] if i["id"] == f"prism_weapon_{char}"))
    actor["inventory"].append({**weapon, "quantity": 1})
    actor["equipment"] = [name for name in actor["equipment"] if not any(
        i["name"] == name and i.get("combat", {}).get("kind") == "weapon" for i in actor["inventory"])] + [weapon["name"]]
    return modified


def reward_route(pack: dict[str, Any], cp: dict[str, Any], char: str) -> dict[str, Any]:
    modified = deepcopy(cp)
    sources = modified["encounters"]["dragon_valley_loc"]["characters"][char]["sources"]
    steps = [s["step"] for s in sources]
    # Every optional reward is earned by replaying its actual source and delivery.
    index = steps.index("ignore_lost_goblin:success")
    steps[index:index] = ["help_lost_goblin", "enter_goblin_fort", "@victory", "@victory", "explore_fort_right",
        "bypass_hobgoblin:success", "give_correct_password", "@victory", "return_lost_goblin_box"]
    index = steps.index("continue_from_elf_spring")
    steps.insert(index, "observe:glowing_moss_patch")
    index = steps.index("leave_forest_for_village")
    steps[index:index] = ["exit_back", "wolves_back", "inspect_spring_wall", "decode_seal:success", "@victory",
        "cave_right", "talk_mina", "escort_mina", "hot_spring_forward", "@victory", "@victory", "leave_prism_tree",
        "continue_from_elf_spring", "pass_cleared_wolves", "return_inn_after_forest", "return_castle_from_inn", "go_item_shop",
        "give_moss_to_sarah", "return_castle_from_item_shop", "go_forge", "return_robert_hammer", "return_castle_from_forge",
        "go_magic_shop", "report_mina_safe", "forge_prism_weapon", "return_castle_from_magic_shop", "go_inn", "return_forest_exit"]
    session = checkpoints.fresh_session(pack, char)
    new_sources = [checkpoints.replay_step(session, step) for step in steps]
    modified["encounters"]["dragon_valley_loc"]["characters"][char]["sources"] = new_sources
    return modified


def reward_only_route(pack: dict[str, Any], cp: dict[str, Any], char: str, *, n: int, seed: int) -> dict[str, Any]:
    replay = checkpoints.replay_step

    def apply_rewards(session: dict[str, Any], step: str) -> dict[str, Any]:
        if step == "leave_forest_for_village":
            # A conditional control: acquisition costs excluded, actual delivery actions retained.
            donor = deepcopy(session)
            donor["flags"]["mina_rescued"] = True
            state.apply_state_delta(donor, {"inventory_add": [
                {**next(i for i in pack["items"] if i["id"] == item_id), "quantity": 1}
                for item_id in ("prism_shard", "robert_hammer", "glowing_moss")]})
            for location, steps in (("magic_shop", ("report_mina_safe", "forge_prism_weapon")),
                                    ("item_shop", ("give_moss_to_sarah",)), ("forge", ("return_robert_hammer",))):
                state.commit_world_position(donor, location_id=location)
                for action in steps:
                    replay(donor, action)
            session["character"] = donor["character"]
            session["flags"] = donor["flags"]
        return replay(session, step)

    with patch.object(checkpoints, "replay_step", apply_rewards):
        result = route.simulate_route(pack, cp, char, n=n, seed=seed)
    result.update(sidequests=True, reward_only=True)
    return result


def evaluate(n: int = 500, seed: int = 20261012) -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    early = early_checkpoints(pack)
    result: dict[str, Any] = {"n": n, "seed": seed, "encounters": [], "weapons": [], "routes": [],
        "fingerprints": {str(path.relative_to(checkpoints.ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in (checkpoints.DEFAULT_SCENARIO, sim.TARGETS, Path(__file__))}}
    for level, snapshot in ((1, early), (2, cp)):
        for encounter in ENCOUNTERS:
            for char in CHARACTERS:
                row = sim.simulate(pack, encounter, char, n=n, seed=seed, checkpoints=snapshot)
                result["encounters"].append(row)
                print(level, encounter, char, row["win_rate"], flush=True)
    for char in CHARACTERS:
        before = sim.simulate(pack, "dragon_valley_loc", char, n=n, seed=seed, checkpoints=cp, purify=False)
        after = sim.simulate(pack, "dragon_valley_loc", char, n=n, seed=seed, checkpoints=weapon_checkpoints(pack, cp, char), purify=False)
        result["weapons"].append(dict(character=char, before=before["win_rate"], after=after["win_rate"], uplift=after["win_rate"]-before["win_rate"]))
        for rewards in (False, True):
            snapshot = reward_route(pack, cp, char) if rewards else cp
            row = route.simulate_route(pack, snapshot, char, n=n, seed=seed)
            row["sidequests"] = rewards
            result["routes"].append(row)
            print("route", char, rewards, row["completion_rate"], flush=True)
        row = reward_only_route(pack, cp, char, n=n, seed=seed)
        result["routes"].append(row)
        print("reward-only control", char, row["completion_rate"], flush=True)
    return result


def check_results(result: dict[str, Any], targets: dict[str, Any]) -> list[dict[str, Any]]:
    violations = sim.check_results([r for r in result["encounters"] if r["level"] == 2], targets)
    specs = targets["forest_v3"]
    limit = specs["early_prism_tree"]["win_rate_lt"]
    for row in result["encounters"]:
        if row["level"] == 1 and row["encounter"] == "cave_prism_tree" and row["win_rate"] >= limit:
            violations.append(dict(character=row["character"], metric="early_prism_tree", value=row["win_rate"], target=limit))
    low, high = specs["prism_weapon_ignis_uplift"]
    for row in result["weapons"]:
        if not low - 1e-12 <= row["uplift"] <= high + 1e-12:
            violations.append(dict(character=row["character"], metric="prism_weapon_ignis_uplift", value=row["uplift"], target=[low, high]))
    limit = specs["rewarded_main_completion_rate_max"]
    for row in result["routes"]:
        if row["completion_rate"] > limit:
            violations.append(dict(character=row["character"], metric="main_completion_rate", sidequests=row["sidequests"],
                                   value=row["completion_rate"], target=limit))
    return violations


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline forest-v3 encounters, prism uplift, and continuous routes")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--output", type=Path, default=Path("eval/reports/balance-2026-10-12-forest-v3.json"))
    parser.add_argument("--check", action="store_true", help="Return a failing exit code for unmet design targets")
    args = parser.parse_args()
    result = evaluate(args.n, args.seed)
    result["violations"] = check_results(result, json.loads(sim.TARGETS.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"forest-v3 target violations: {len(result['violations'])}")
    if args.check and result["violations"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
