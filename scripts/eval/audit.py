from __future__ import annotations

from copy import deepcopy
from typing import Any

from host import combat, free_actions, state


def costly_plan(session: dict[str, Any], plan: dict[str, Any]) -> bool:
    """Derive risk from action data or a disposable free-action adjudication."""
    if plan.get("kind") == "existing":
        action = state.resolve_action(session, action_id=plan.get("action_id", ""))
        if not action:
            return False
        if state.action_dice_settings(action)[1] > 0:
            return True
        actor = session["character"]
        for key, effects in action.items():
            if key != "effects" and not key.endswith("_effects"):
                continue
            delta = state._effects_to_state_delta(state._as_list(effects), session)
            if (any(delta.get(k, 0) < 0 for k in state.MODEL_RESOURCE_DELTA_KEYS)
                    or any(delta.get(k, actor.get(k, 0)) < actor.get(k, 0) for k in ("hp", "mp", "sp", "gold"))
                    or any(delta.get(k) for k in ("inventory_remove", "start_combat", "game_over", "clear_skills"))
                    or any(delta.get(k) and delta[k] != session["world_state"][world_key]
                           for k, world_key in (("current_location", "location_id"), ("current_scene", "scene_id")))
                    or any(value < actor.get("attributes", {}).get(attr, 0)
                           for attr, value in delta.get("attribute_set", {}).items())
                    or any(value < 0 for value in delta.get("attribute_changes", {}).values())):
                return True
        return False
    if plan.get("kind") != "interact":
        return False
    trial = deepcopy(session)
    # The engine owns resource costs and check requirements; do not duplicate an operation table.
    from .snapshots import isolated_engine
    with isolated_engine("cost-probe"):
        result = free_actions.adjudicate(trial, {"approach": "", "reply": "", **plan})
    before, after = session["character"], trial["character"]
    return bool(result.get("roll") or trial["world_state"] != session["world_state"]
                or any(after.get(k, 0) < before.get(k, 0) for k in ("hp", "sp", "mp", "gold"))
                or any(sum(int(i.get("quantity", 1)) for i in after["inventory"]
                           if free_actions._item_id(i) == free_actions._item_id(item)) < int(item.get("quantity", 1))
                       for item in before["inventory"]))


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
    if operation == "observe" and outcome in {"success", "failure"} and not plan["item_id"] and not plan["advance"]:
        target = free_actions._observe_target(expected, plan["target_id"])
        reveal = target.get("observe_reveals")
        if isinstance(reveal, dict) and result.get("roll"):
            once = str(reveal.get("once") or "")
            if not once or not expected.get("flags", {}).get(once):
                roll = result["roll"]
                branch = "success" if roll.get("success") and not roll.get("critical_failure") else "failure"
                delta = state._effects_to_state_delta(reveal.get(f"{branch}_effects", []), expected)
                if once:
                    delta.setdefault("flags_set", []).append(once)
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
