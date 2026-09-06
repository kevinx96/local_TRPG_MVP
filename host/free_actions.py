"""Interpretation protocol and engine-owned rules for free exploration actions.

The model selects a method and existing entities. It never supplies effects,
DCs, rewards, destinations, or arbitrary world facts.
"""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from . import state
from .gm_contract import sanitize_visible_text
from .item_mechanics import item_combat_spec
from .scenario_context import current_actions_for_session
from .world_state import current_location_id, current_location_title


KINDS = ("existing", "interact", "dialogue", "clarify", "unsupported")
OPERATIONS = ("", "observe", "distract", "sneak", "prepare", "use_item")
PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": list(KINDS)},
        "action_id": {"type": "string", "description": "existing の時だけ actions の ID。他の種類では空文字。"},
        "operation": {"type": "string", "enum": list(OPERATIONS)},
        "target_id": {"type": "string", "description": "existing は必ず空文字。prepare/distract/sneak は obstacles の ID、observe は観察対象の ID、use_item は self。dialogue は NPC の ID または空文字。"},
        "item_id": {"type": "string", "description": "existing は必ず空文字。prepare は使う素材の objects ID、distract/use_item は inventory ID。その他は空文字。"},
        "advance": {"type": "boolean"},
        "approach": {"type": "string"},
        "reply": {"type": "string"},
    },
    "required": ["kind", "action_id", "operation", "target_id", "item_id", "advance", "approach", "reply"],
    "additionalProperties": False,
}

PLAN_PROMPT = (
    "プレイヤーの自由入力を一つの行動案に解釈する。結果の裁定はゲームエンジンが行う。\n"
    "否定・条件・対象・方法を保つ。『攻撃しない』『餌で誘う』を攻撃に変えない。"
    "複数の独立した行動や曖昧な対象は clarify で一つだけ質問。\n"
    "既存の行動と方法まで同じなら existing と action_id。対象名が同じだけでは選ばない。"
    "新しい方法は interact。operation は observe(観察)、distract(餌で誘導)、"
    "sneak(潜行)、prepare(周囲の素材で足止めや遮蔽を準備)、use_item(所持品で自分を回復)。"
    "対象と素材は提示された ID だけを使い、手段や物が足りなければ質問する。"
    "advance は誘導や潜行の後に通り抜けたいと明示された時だけ true。\n"
    "会話・拒否・感想は dialogue。reply は既知の人物の短い反応だけを日本語で書く。"
    "新しい約束、情報、アイテム獲得、移動や成功を会話で確定しない。"
    "不可能・未対応なら unsupported と理由。プレイヤーが宣言した成功を既成事実にしない。\n"
    "approach は意図と方法を日本語80字以内。reply は dialogue/clarify/unsupported のみ120字以内。"
    "JSON一つだけ。該当しない文字列は空、advance は false。"
    "changes_here と last_result は確定済みで、古い場所の描写より優先する。"
)


class InvalidPlan(ValueError):
    pass


def planner_config(config: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(config)
    result.update({
        "temperature": 0.2,
        "max_tokens": 700,
        "request_timeout_seconds": min(15, max(1, int(config.get("request_timeout_seconds", 15)))),
        "max_model_attempts": 1,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "exploration_plan", "strict": True, "schema": deepcopy(PLAN_SCHEMA)},
        },
    })
    return result


def parse_plan(raw: str) -> dict[str, Any]:
    try:
        plan = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise InvalidPlan("invalid JSON") from exc
    if not isinstance(plan, dict) or set(plan) != set(PLAN_SCHEMA["required"]):
        raise InvalidPlan("unexpected plan fields")
    for key in PLAN_SCHEMA["required"]:
        if key == "advance":
            if not isinstance(plan[key], bool):
                raise InvalidPlan("advance must be a boolean")
        elif not isinstance(plan[key], str) or len(plan[key]) > (240 if key in {"approach", "reply"} else 100):
            raise InvalidPlan("invalid plan value")
    if plan["kind"] not in KINDS or plan["operation"] not in OPERATIONS:
        raise InvalidPlan("unknown plan kind or operation")
    if plan["kind"] == "existing":
        if not plan["action_id"] or plan["operation"] or plan["target_id"] or plan["item_id"] or plan["advance"]:
            raise InvalidPlan("existing action cannot include another operation")
    elif plan["action_id"]:
        raise InvalidPlan("unexpected action ID")
    if plan["kind"] == "interact":
        if not plan["operation"] or not plan["target_id"]:
            raise InvalidPlan("missing interaction")
    elif plan["kind"] != "existing" and (plan["operation"] or plan["item_id"] or plan["advance"]):
        raise InvalidPlan("conversation cannot contain an action")
    return plan


def _location(session: dict[str, Any]) -> dict[str, Any]:
    return state._current_location_record(session) or {}


def _obstacles(session: dict[str, Any]) -> list[dict[str, Any]]:
    return [x for x in _location(session).get("obstacles", []) if isinstance(x, dict) and x.get("id")]


def _objects(session: dict[str, Any]) -> list[dict[str, Any]]:
    return [x for x in _location(session).get("objects", []) if isinstance(x, dict) and x.get("id")]


def _inventory(session: dict[str, Any]) -> list[dict[str, Any]]:
    return [x for x in session.get("character", {}).get("inventory", []) if isinstance(x, dict) and int(x.get("quantity", 1)) > 0]


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("name") or "")


def location_changes(session: dict[str, Any]) -> dict[str, Any]:
    return deepcopy((session.get("scene_changes") or {}).get(current_location_id(session), {}))


def build_plan_messages(session: dict[str, Any], player_text: str) -> list[dict[str, str]]:
    location = _location(session)
    actions, _groups = state._intent_action_surfaces(session, current_actions_for_session(session))
    action_surface = []
    for action in actions:
        enabled, reason = state.action_requirement_status(action, session)
        action_surface.append({
            "id": str(action.get("id") or action.get("action_id") or ""),
            "text": str(action.get("text") or ""),
            "risk": str(action.get("risk") or ""),
            "enabled": enabled,
            **({"reason": reason} if not enabled else {}),
        })
    npcs = [
        {key: npc[key] for key in ("id", "name", "description") if key in npc}
        for npc in session.get("scenario_pack", {}).get("npcs", [])
        if npc.get("id") in location.get("npc_ids", [])
    ]
    obstacles = []
    for obstacle in _obstacles(session):
        obstacles.append({key: deepcopy(obstacle[key]) for key in (
            "id", "name", "description", "traits", "bypassable", "hint",
        ) if key in obstacle})
    inventory = []
    for item in _inventory(session):
        inventory.append({
            "id": _item_id(item), "name": str(item.get("name") or ""),
            "quantity": int(item.get("quantity", 1)), "traits": item.get("traits", []),
            "effect": state.structured_item_effect(item),
        })
    actor = session.get("character", {})
    context = {
        "actor": {"id": actor.get("character_id") or "self", "name": actor.get("name"),
                  "hp": actor.get("hp"), "max_hp": actor.get("max_hp"), "sp": actor.get("sp")},
        "location": {"id": current_location_id(session), "name": current_location_title(session),
                     "description": str(location.get("description") or "")[:400]},
        "actions": action_surface,
        "obstacles": obstacles,
        "objects": _objects(session),
        "npcs": npcs,
        "inventory": inventory,
        "changes_here": location_changes(session),
        "last_result": {
            key: deepcopy(session.get("last_free_action", {}).get(key))
            for key in ("operation", "target_id", "outcome", "text")
            if key in session.get("last_free_action", {})
        },
        "recent_dialogue": [
            {"role": m.get("role"), "text": str(m.get("text") or "")[:200]}
            for m in session.get("messages", [])[-4:]
        ],
    }
    return [
        {"role": "system", "content": PLAN_PROMPT},
        {"role": "system", "content": json.dumps(context, ensure_ascii=False, separators=(",", ":"))},
        {"role": "user", "content": player_text},
    ]


def _result(text: str, outcome: str = "rejected", **data: Any) -> dict[str, Any]:
    return {"text": text, "outcome": outcome, **data}


def _commit(session: dict[str, Any], plan: dict[str, Any], result: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    location_id = current_location_id(session)
    session.setdefault("scene_changes", {})[location_id] = changes
    data = {
        "actor_id": session.get("character", {}).get("character_id") or "self",
        "location_id": location_id, "operation": plan["operation"],
        "target_id": plan["target_id"], "item_id": plan["item_id"],
        "approach": plan["approach"], **deepcopy(result),
    }
    event = state.record_state_event(session, "free_action_resolved", result["text"], data)
    data["source_event_id"] = event["id"]
    session["last_free_action"] = data
    target_state = changes.get(plan["target_id"])
    if isinstance(target_state, dict):
        target_state["source_event_id"] = event["id"]
        target_state["actor_id"] = data["actor_id"]
    return result


def _owned_item(session: dict[str, Any], identifier: str) -> dict[str, Any]:
    return next((item for item in _inventory(session) if identifier in {_item_id(item), str(item.get("name") or "")}), {})


def _consume(session: dict[str, Any], item: dict[str, Any]) -> None:
    state.apply_state_delta(session, {"inventory_remove": [{"name": item["name"], "quantity": 1}]})


def adjudicate(session: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Apply a validated plan atomically; reject plans before spending resources."""
    trial = deepcopy(session)
    result = _adjudicate(trial, plan)
    if result["outcome"] != "rejected":
        session.clear()
        session.update(trial)
    return result


def _adjudicate(session: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    kind = plan["kind"]
    if kind in {"dialogue", "clarify", "unsupported"}:
        if plan["target_id"] and plan["target_id"] not in _location(session).get("npc_ids", []):
            return _result("その相手はここにはいません。誰に話しかけますか？")
        text = sanitize_visible_text(plan["reply"]) or "どの相手に、何をしたいですか？"
        return _result(text, kind)
    if kind != "interact":
        raise InvalidPlan("existing actions must use the action engine")
    operation = plan["operation"]
    changes = location_changes(session)
    if operation == "use_item":
        return _use_item(session, plan, changes)
    target = next((o for o in _obstacles(session) if o["id"] == plan["target_id"]), {})
    if operation == "observe":
        target = target or next((o for o in _objects(session) if o["id"] == plan["target_id"]), {})
        if not target or plan["item_id"] or plan["advance"]:
            return _result("観察する対象を、今見えているものから指定してください。")
        changes.setdefault(target["id"], {})["observed"] = True
        text = str(target.get("description") or target.get("name") or "")
        if target.get("hint"):
            text += " " + str(target["hint"])
        return _commit(session, plan, _result(text, "observed"), changes)
    if not target:
        return _result("その方法を試す対象が、今いる場所では見つかりません。")
    target_state = changes.setdefault(target["id"], {})
    if target_state.get("resolution"):
        return _result("この道はすでに通れると分かっています。先へ進む行動を選べます。")
    if plan["advance"] and (not target.get("bypassable") or not target.get("destination")):
        return _result("この障害から先へ進む道はありません。別の目的を指定してください。")
    if operation == "prepare":
        material = next((o for o in _objects(session) if o["id"] == plan["item_id"]), {})
        if plan["advance"] or not target.get("bypassable"):
            return _result("準備と移動は順番に行います。まず準備する方法を指定してください。")
        if not material or not set(material.get("traits", [])).intersection({"cover_material", "movable"}):
            return _result("足止めや遮蔽に使える、近くの素材を指定してください。")
        if target_state.get("prepared"):
            return _result("準備は整っています。次の潜行で利用でき、重ねても効果は増えません。")
        target_state["prepared"] = {"material_id": material["id"], "bonus": 3, "expires": "next_sneak_attempt"}
        text = f"{material['name']}で足止めと遮蔽の準備を整えた。まだ相手を捕らえてはいないが、次の潜行判定の難度が3下がる。"
        return _commit(session, plan, _result(text, "prepared"), changes)
    if operation == "distract":
        item = _owned_item(session, plan["item_id"])
        if "food_motivated" not in target.get("traits", []):
            return _result("この相手は食べ物で引きつけられる様子がありません。")
        if not item or "food" not in item.get("traits", []):
            return _result("餌にできる食べ物を持っていません。潜行するか、周囲の素材を使う方法を試せます。")
        if target_state.get("distracted"):
            return _result("相手はまだ餌に気を取られています。追加の食べ物は使わずに通れます。")
        _consume(session, item)
        target_state["distracted"] = True
        text = f"{item['name']}を1つ投げると、{target['name']}は道の脇へ寄って食べ始めた。"
        if plan["advance"]:
            return _pass_obstacle(session, plan, target, target_state, changes, text, "distracted")
        text += "次の潜行では判定なしで通れる。戦えばこの隙は失われる。"
        return _commit(session, plan, _result(text, "distracted"), changes)
    if operation == "sneak":
        if not target.get("bypassable") or not plan["advance"] or plan["item_id"]:
            return _result("潜行でどこを通り抜けたいですか？道と対象を指定してください。")
        if target_state.get("distracted"):
            return _pass_obstacle(session, plan, target, target_state, changes,
                                  "相手が餌に気を取られている間に、静かに脇を通り抜けた。", "distracted")
        if int(session.get("character", {}).get("sp", 0)) < 1:
            return _result("潜行する体力が足りません。別の方法を試すか、休息してください。")
        preparation = target_state.pop("prepared", {})
        dc = int(target.get("sneak_dc", 14)) + min(3, int(target_state.get("alertness", 0))) * 2
        dc -= int(preparation.get("bonus", 0))
        roll = state.roll_dice(session, "1d20+dex", dc)
        state.apply_state_delta(session, {"sp_change": -1})
        if roll["success"] and not roll["critical_failure"]:
            return _pass_obstacle(session, plan, target, target_state, changes,
                                  "葉を踏む音を抑え、相手の視界を避けて道を通り抜けた。", "sneaked", roll)
        target_state["alertness"] = min(3, int(target_state.get("alertness", 0)) + 1)
        return _commit(session, plan, _result(
            "枝の音に相手が振り向いた。移動できず、SPを1消費した。相手の警戒が強まったが、餌で誘う方法はまだ使える。",
            "failure", roll=roll), changes)
    return _result("その方法にはまだ対応していません。目的と、使いたいものを具体的に教えてください。")


def _pass_obstacle(session: dict[str, Any], plan: dict[str, Any], target: dict[str, Any],
                   target_state: dict[str, Any], changes: dict[str, Any], text: str,
                   method: str, roll: Any = None) -> dict[str, Any]:
    destination = str(target.get("destination") or "")
    source = current_location_id(session)
    moved, _reason = state.commit_world_position(session, location_id=destination)
    if not moved:
        return _result("この先の道を確認できません。今いる場所に留まりました。")
    # Record the result at its source before exposing the new location.
    session["world_state"]["location_id"] = source
    target_state["resolution"] = method
    target_state["enemy_defeated"] = False
    target_state.pop("distracted", None)
    target_state.pop("prepared", None)
    result = _commit(session, plan, _result(text, "success", resolution=method, roll=roll), changes)
    if target.get("resolved_flag"):
        state.apply_state_delta(session, {"flags_set": [target["resolved_flag"]]})
    state.apply_state_delta(session, {"current_location": destination}, allow_world_transition=True)
    result["text"] += f" {current_location_title(session)}へ進んだ。"
    if target.get("arrival_text"):
        result["text"] += " " + str(target["arrival_text"])
    session["last_free_action"]["text"] = result["text"]
    return result


def _use_item(session: dict[str, Any], plan: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    actor = session.get("character", {})
    if plan["target_id"] not in {"self", actor.get("character_id")} or plan["advance"]:
        return _result("ここでは自分の回復に使う道具を指定してください。")
    item = _owned_item(session, plan["item_id"])
    spec = item_combat_spec(item)
    amount = str(spec.get("healing") or spec.get("amount") or "")
    if spec.get("kind") != "heal" or not amount.isdigit() or int(amount) < 1:
        return _result("その道具は持っていないか、探索中の回復には使えません。")
    missing = int(actor.get("max_hp", 0)) - int(actor.get("hp", 0))
    if missing <= 0:
        return _result("HPは満タンです。道具は消費しませんでした。")
    healed = min(missing, int(amount))
    if spec.get("consumable", True):
        _consume(session, item)
    state.apply_state_delta(session, {"hp_change": healed})
    return _commit(session, plan, _result(f"{item['name']}を使い、HPが{healed}回復した。", "success"), changes)
