from __future__ import annotations

from copy import deepcopy
from typing import Any

from host import combat, free_actions, state


def allowed_state(session: dict[str, Any], plan: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Rebuild authorized protected changes from rules, never from the observed after-state."""
    expected = deepcopy(session)
    outcome = result.get("outcome")
    if plan["kind"] == "existing":
        action = state.resolve_action(expected, action_id=plan["action_id"])
        if action and state.action_requirement_status(action, expected)[0]:
            state.apply_action_result(expected, action, result.get("roll") or {})
            combat.ensure_combat_started(expected)
        return expected
    if plan["kind"] != "interact":
        return expected
    operation = plan["operation"]
    delta: dict[str, Any] = {}
    if operation == "use_item" and outcome == "success" and plan["target_id"] in {"self", expected["character"]["character_id"]}:
        item = free_actions._owned_item(expected, plan["item_id"])
        spec = free_actions.item_combat_spec(item)
        if spec.get("kind") == "heal":
            delta["hp_change"] = int(spec.get("healing") or spec.get("amount") or 0)
            if spec.get("consumable", True):
                delta["inventory_remove"] = [{"name": item["name"], "quantity": 1}]
    target = next((t for t in free_actions._obstacles(expected) if t["id"] == plan["target_id"]), {})
    if operation == "distract" and outcome in {"success", "distracted"} and "food_motivated" in target.get("traits", []):
        item = free_actions._owned_item(expected, plan["item_id"])
        if "food" in item.get("traits", []):
            delta["inventory_remove"] = [{"name": item["name"], "quantity": 1}]
    if operation == "sneak" and outcome in {"success", "failure"} and result.get("roll"):
        delta["sp_change"] = -1
    if operation in {"distract", "sneak"} and outcome == "success" and plan["advance"] and target.get("bypassable"):
        delta["current_location"] = target.get("destination")
        if target.get("resolved_flag"):
            delta["flags_set"] = [target["resolved_flag"]]
    state.apply_state_delta(expected, delta, allow_world_transition=True)
    return expected


def unearned_change(record: dict[str, Any]) -> bool:
    engine = record.get("engine") or {}
    if engine.get("before") is not None and engine.get("after") is not None:
        if engine["before"] == engine["after"]:
            return False
        return engine.get("allowed_after") != engine["after"]
    return any(engine.get("changes", {}).values())
