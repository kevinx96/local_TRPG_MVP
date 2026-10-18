"""Offline public-API route: kill the capital forge keeper, finish Ignis, face the interception."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from host import app, combat, state
from scripts.balance import sim
from .explore import ROOT, offline_runtime


PREPARATION = ["check_supplies", "go_castle_town", "go_magic_shop", "invite_blue_mage", "return_castle_from_magic_shop",
               "go_forge", "show_sword_to_blacksmith", "accept_sword_fusion"]
ROUTE = {"forge": "return_castle_from_forge", "castle_town": "go_dark_forest",
         "dark_forest_loc": "attack_slime",
         "lost_goblin_crossroads": "crossroads_forward", "elf_spring": "continue_from_elf_spring",
         "forest_wolves": "fight_forest_wolves", "forest_exit": "leave_forest_for_village",
         "village_approach": "approach_burning_village_carefully", "burning_house": "leave_burning_house",
         "ice_elemental_encounter": "fight_ice_elemental",
         "village_frozen_clue": "investigate_frozen_village", "ian_ice_katana_aftermath": "accept_ian_request",
         "valley_entrance": "fight_ash_wraiths", "valley_lava_bridge": "cross_lava_bridge",
         "warlock_at_nest": "continue_after_warlock",
         "valley_nest_gate": "enter_dragon_nest", "ignis_last_breath": "return_to_castle_report",
         "ignis_purified": "return_to_castle_report", "royal_gate": "enter_festival_town",
         "festival_town": "go_report_hall", "castle_report": "report_normally"}


def explore(seed: int, max_steps: int = 250) -> dict[str, Any]:
    events = []
    failures = []
    invariants = dict(exceptions=0, noncombat_dead_ends=0)
    with offline_runtime(seed):
        public = app.api_create_session(app.CreateSessionRequest(character_id="hero", character={"name": "テスト"}))
        identifier = public["id"]

        def turn(action_id: str) -> None:
            nonlocal public
            session = state.load_session(identifier)
            action = state.resolve_action(session, action_id=action_id)
            if action is None or not state.action_requirement_status(action, session)[0]:
                raise ValueError(f"Unavailable route action: {state.current_location_id(session)}/{action_id}")
            events.append(dict(location=state.current_location_id(session), action=action_id))
            public = app.api_turn(identifier, app.TurnRequest(text=action["text"], action_id=action_id))

        for action_id in PREPARATION:
            turn(action_id)
        session = state.load_session(identifier)
        if session["character"]["gold"] >= 60:
            from host.shops import trade

            trade(session, "forge_shop", "adamantite_armor", 1)
            state._equip_inventory_item(session, "アダマンタイトの鎧")
            state.save_session(session)
        plan = dict(kind="interact", action_id="", operation="attack", target_id="blacksmith", item_id="",
                    advance=False, approach="ローベルトを攻撃する", reply="")
        with patch.object(app, "chat_completion", return_value=json.dumps(plan, ensure_ascii=False)):
            public = app.api_turn(identifier, app.TurnRequest(text="ローベルトを攻撃する。"))
        turn("npc_attack_confirm")
        started_combats: set[str] = set()
        for step in range(max_steps):
            session = state.load_session(identifier)
            location = state.current_location_id(session)
            try:
                if combat.combat_needs_resolution(session):
                    events.append(dict(location=location, combat=session["combat"]["status"],
                                       resources={key: session["character"].get(key) for key in ("level", "hp", "max_hp", "mp", "sp")}))
                    public = app.api_combat_resolve(identifier)
                elif public.get("game_over"):
                    break
                elif combat.combat_is_active(session):
                    combat_id = session["combat"]["id"]
                    if combat_id not in started_combats:
                        events.append(dict(location=location, combat="started",
                                           resources={key: session["character"].get(key) for key in ("level", "hp", "max_hp", "mp", "sp")}))
                        started_combats.add(combat_id)
                    action, target = sim.choose_action(session, "heuristic", purify=False)
                    public = app.api_combat_action(identifier, app.CombatActionRequest(
                        action_type=action["type"], action_id=action["id"], target_id=target or ""))
                else:
                    action_id = ROUTE.get(location)
                    if action_id is None:
                        invariants["noncombat_dead_ends"] += 1
                        failures.append(f"route missing at {location}")
                        break
                    turn(action_id)
            except Exception as exc:
                invariants["exceptions"] += 1
                failures.append(f"{location}: {type(exc).__name__}: {exc}")
                break
        session = state.load_session(identifier)
        ending = (session.get("game_over") or {}).get("ending")
        result = dict(seed=seed, ending=ending, completed=(session.get("game_over") or {}).get("title") == "冒険完了",
                      town_blood=bool(session["flags"].get("town_blood")),
                      intercepted=any(e["location"] == "dragon_valley_return" for e in events),
                      dragon_knight_defeated=bool(session["flags"].get("dragon_knight_defeated")),
                      invariants=invariants, failures=failures, events=events)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(41, 53)))
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/041-murder-route.json")
    args = parser.parse_args()
    rows = []
    for seed in args.seeds:
        row = explore(seed)
        rows.append(row)
        print(json.dumps({k: v for k, v in row.items() if k != "events"}, ensure_ascii=False), flush=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(any(any(row["invariants"].values()) for row in rows)
               or not any(row["completed"] and row["intercepted"] for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
