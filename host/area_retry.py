from __future__ import annotations

from copy import deepcopy
from typing import Any, Optional

from .world_state import current_location_id, current_location_title


GAME_STATE_FIELDS = (
    "character", "world_state", "flags", "companion", "completed_milestones",
    "visited_locations", "shop_stock", "known_item_names", "scene_changes",
    "opening_effects_applied", "next_dice_type", "next_dice_dc",
)
TURN_STATE_FIELDS = (
    "combat_start_requested", "enemy_first_requested", "combat_blocked_location",
    "needs_client_resync", "last_intent_resolution", "deviation_state",
    "last_free_action", "last_turn_metrics",
)


def areas_here(session: dict[str, Any]) -> list[dict[str, Any]]:
    from .state import _session_requirement_passes

    location = current_location_id(session)
    maps = [area for area in session.get("scenario_pack", {}).get("maps", [])
            if _session_requirement_passes(area.get("requirements"), session)
            and any(location in node.get("location_ids", []) for node in area.get("nodes", []))]
    return sorted(maps, key=lambda area: not bool(area.get("parent")))


def capture_entries(session: dict[str, Any], previous_location: Optional[str], previous_areas: set[str]) -> None:
    from .state import known_item_names

    if "area_snapshots" not in session or session.get("game_over"):
        return
    location = current_location_id(session)
    areas = areas_here(session)
    if not areas:
        areas = [{"id": "location:" + location, "title": current_location_title(session)}]
    for area in areas:
        if area["id"] in previous_areas and previous_location is not None:
            continue
        session["known_item_names"] = sorted(known_item_names(session))
        session["area_snapshots"][area["id"]] = {
            "area_id": area["id"], "title": area["title"], "location_id": location,
            "state": {key: deepcopy(session[key]) for key in GAME_STATE_FIELDS if key in session},
        }


def retry_snapshot(session: dict[str, Any]) -> Optional[dict[str, Any]]:
    ending = session.get("game_over") or {}
    if not ending.get("combat_defeat"):
        return None
    result = (session.get("combat") or {}).get("result") or session.get("last_combat_result") or {}
    if result.get("outcome") != "defeat":
        return None
    location = next((loc for loc in session.get("scenario_pack", {}).get("locations", [])
                     if loc.get("id") == result.get("location_id")), {})
    if location.get("combat", {}).get("encounter_class") == "scripted_loss":
        return None
    areas = areas_here(session)
    key = areas[0]["id"] if areas else "location:" + current_location_id(session)
    return session.get("area_snapshots", {}).get(key)


def retry_area(session: dict[str, Any]) -> None:
    from . import llm_trace
    from .scenario_context import fallback_choices_for_session
    from .state import add_assistant_message, record_state_event, utc_now

    snapshot = retry_snapshot(session)
    if snapshot is None:
        raise ValueError("このエリアの入口からやり直すことはできません。")
    death_location = current_location_id(session)
    for key in (*GAME_STATE_FIELDS, *TURN_STATE_FIELDS):
        session.pop(key, None)
    session.update(deepcopy(snapshot["state"]))
    session.update(game_over=None, combat=None, last_combat_result={}, last_action_result={},
                   last_turn_narrated=True, needs_opening=False)
    session["retry_count"] = int(session.get("retry_count", 0)) + 1
    session["choices"] = fallback_choices_for_session(session)
    title = snapshot["title"]
    add_assistant_message(session, f"運命の糸がほどけ、あなたは再び{title}の入口に立っていた。")
    data = {"area_id": snapshot["area_id"], "death_location": death_location,
            "location_id": current_location_id(session), "retry_count": session["retry_count"]}
    record_state_event(session, "area_retry", f"{title}の入口からやり直しました。", data)
    llm_trace.append_trace({"session_id": session["id"], "timestamp": utc_now(), "gm_mode": session.get("gm_mode"),
                            "turn": sum(m.get("role") == "user" for m in session.get("messages", [])),
                            "call_type": "area_retry", "outcome": "retry", **data})
