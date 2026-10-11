from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from host import combat, free_actions, state
from host.shops import trade
from scripts.balance import checkpoints

MANIFEST = ROOT / "eval/scenario/key_items.json"


def replay(pack: dict[str, Any], steps: list[str], character: str = "hero") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    session = checkpoints.fresh_session(pack, character)
    events = []
    for step in steps:
        location = state.current_location_id(session)
        if session.get("game_over"):
            raise ValueError(f"route continues after ending: {location}/{step}")
        if step.startswith("shop:"):
            _, shop_id, item_id = step.split(":")
            delta = trade(session, shop_id, item_id, 1)
        elif step == "@entry":
            hint = next((e for e in reversed(session["event_log"]) if e["kind"] == "location_hint"
                         and e["data"].get("location_id") == location), {})
            delta = hint.get("data", {}).get("state_delta", {})
            if not all(session["flags"].get(f) for f in delta.get("flags_set", [])):
                raise ValueError("entry effects not applied")
        elif step.startswith("@skill:"):
            delta = {}
        elif step.endswith(":high"):
            action = state.resolve_action(session, action_id=step.split(":")[0])
            if not action or not state.action_requirement_status(action, session)[0]:
                raise ValueError(f"unavailable action: {location}/{step}")
            roll = state.roll_dice(session, *state.action_dice_settings(action), client_rolls=[20])
            delta = state.apply_action_result(session, action, roll)["state_delta"]
        elif step.startswith("observe:"):
            target = step.split(":", 1)[1]
            plan = dict(kind="interact", operation="observe", target_id=target, item_id="", advance=False, approach="観察する", reply="", action_id="")
            with patch.object(state.random, "randint", return_value=20):
                result = free_actions.adjudicate(session, plan)
            if result["outcome"] != "success":
                raise ValueError(f"observation unavailable: {location}/{step}")
            delta = result["state_delta"]
        else:
            if step == "@victory":
                encounter = combat._encounter_for_session(session, pack)
                if any(session["flags"].get(combat._defeated_flag(e, location)) for e in encounter.get("enemy_ids", [])):
                    raise ValueError(f"repeated victory: {location}")
            delta = checkpoints.replay_step(session, step)["delta"]
        events.append(dict(location=location, step=step, delta=delta))
    return session, events


def grants(delta: dict[str, Any], reward: dict[str, str]) -> bool:
    if "flag" in reward:
        return reward["flag"] in delta.get("flags_set", [])
    if "companion" in reward:
        return delta.get("set_companion") == reward["companion"]
    if "gold" in reward:
        return delta.get("gold_change", 0) >= int(reward["gold"])
    return any((reward.get("item") and i.get("id") == reward["item"])
               or (reward.get("name") and i.get("name") == reward["name"])
               for i in delta.get("inventory_add", []) if isinstance(i, dict))


def finish_witness(pack: dict[str, Any], steps: list[str], character: str) -> list[str]:
    session, _ = replay(pack, steps, character)
    suffix = []
    navigation = {
        "inn": "return_forest_exit", "forge": "return_castle_from_forge",
        "item_shop": "return_castle_from_item_shop", "magic_shop": "return_castle_from_magic_shop",
        "alley_night": "leave_night_alley", "forest_exit": "leave_forest_for_village",
        "village_approach": "approach_burning_village_carefully:success",
        "village": "go_dragon_valley", "village_frozen_clue": "investigate_frozen_village",
        "ian_ice_katana_aftermath": "accept_ian_request", "ignis_last_breath": "return_to_castle_report",
        "goblin_fort_second_choice": "explore_fort_right", "goblin_fort_third_gate": "give_correct_password",
        "goblin_fort_chest_choice": "return_lost_goblin_box",
        "lost_goblin_crossroads": "crossroads_forward", "elf_spring": "continue_from_elf_spring",
        "cave_seal": "leave_seal", "cave_fork": "cave_right", "cave_hot_spring": "hot_spring_forward",
        "cave_prism_tree": "leave_prism_tree",
    }
    for _ in range(40):
        location = state.current_location_id(session)
        if location == "castle_report":
            return steps + suffix
        if location == "castle":
            step = "return_village" if session["flags"].get("returned_from_village") else "go_inn"
        elif location == "forest_wolves" and session["flags"].get("passed_forest_wolves"):
            step = "pass_cleared_wolves"
        elif location in navigation:
            step = navigation[location]
        else:
            step = "@victory"
        checkpoints.replay_step(session, step)
        suffix.append(step)
    raise ValueError("witness did not reach chapter five")


def check(pack: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    counts = {route: {} for route in manifest["routes"]}
    errors = []
    locations = {l["id"]: l for l in pack["locations"]}
    for key in manifest["keys"]:
        for route, route_spec in manifest["routes"].items():
            found = 0
            seen = set()
            for source in key["sources"]:
                identity = (source["location"], source["step"])
                if identity in seen:
                    errors.append(f"{key['id']}: duplicate source {identity}")
                    continue
                seen.add(identity)
                steps = source.get("witnesses", {}).get(route)
                if steps is None:
                    continue
                try:
                    session, events = replay(pack, steps, source.get("character", "hero"))
                    if not any(e["location"] == route_spec["landmark"] for e in events):
                        raise ValueError("witness does not traverse route landmark")
                    if state.current_location_id(session) != "castle_report":
                        raise ValueError("witness does not reach chapter five")
                    matching = [e for e in events if (e["location"], e["step"]) == identity]
                    if not matching:
                        raise ValueError("declared source was not executed")
                    if source["type"] == "companion_hint":
                        valid = any(grants(e["delta"], source["reward"]) for e in matching)
                    elif source["type"] == "class_skill":
                        state._unlock_level_skills(session)
                        valid = any(s.get("id") == source["skill"] and s.get("element") == source["element"] for s in session["character"]["skills"])
                    elif source["type"] == "class_special":
                        valid = source.get("special_action") == "purify_ignis_prayer" and session["character"]["character_id"] == "cleric"
                    else:
                        valid = any(grants(e["delta"], source["reward"]) for e in matching)
                    if not valid:
                        raise ValueError("source does not grant declared reward")
                    if key["id"] in {"purification_knowledge", "purification_means"}:
                        arrival = next(i for i, e in enumerate(events) if e["location"] == "dragon_valley_loc" and e["step"] == "@victory")
                        if not any(e in events[:arrival] for e in matching):
                            raise ValueError("purification resource acquired after Ignis")
                        before, _ = replay(pack, steps[:arrival], source.get("character", "hero"))
                        combat.ensure_combat_started(before)
                        enemy = before["combat"]["enemies"][0]
                        enemy["hp"] = int(enemy["max_hp"] * .4)
                        specials = [a["id"] for a in combat.combat_actions(before) if a["type"] == "special"]
                        if not specials or (source.get("special_action") and source["special_action"] not in specials):
                            raise ValueError("purification unavailable with declared resource")
                    if source.get("crafted_item") and not any(i.get("id") == source["crafted_item"] for i in session["character"]["inventory"]):
                        raise ValueError("crafting destination/item unreachable")
                    found += 1
                except (ValueError, KeyError, StopIteration) as exc:
                    errors.append(f"{route}/{key['id']}/{source['id']}: {exc}")
            counts[route][key["id"]] = found
            if found < key.get("minimum", 0):
                errors.append(f"{route}/{key['id']}: {found} < {key['minimum']}")
    return dict(counts=counts, errors=errors)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline source reachability witnesses; battles assume victory, actions enforce requirements")
    parser.add_argument("--scenario", type=Path, default=checkpoints.DEFAULT_SCENARIO)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args(argv)
    result = check(state.load_scenario_pack(args.scenario), json.loads(args.manifest.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
