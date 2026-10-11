from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from typing import Any, Callable, Optional

from host import free_actions


@dataclass(frozen=True)
class Variant:
    # Each hook receives fresh data; variants cannot mutate the game's defaults.
    message_builder: Callable = free_actions.build_plan_messages
    config_builder: Callable = free_actions.planner_config
    system_prompt: Optional[str] = None
    few_shot: tuple = ()
    schema_transform: Optional[Callable] = None
    snapshot_schema: bool = False
    dynamic_enum: bool = False
    replay_only: bool = False

    def prepare(self, session: dict[str, Any], text: str, config: dict[str, Any]) -> tuple:
        messages = deepcopy(self.message_builder(deepcopy(session), text))
        configured = deepcopy(self.config_builder(deepcopy(config)))
        if self.system_prompt is not None:
            messages[0]["content"] = self.system_prompt
        if self.few_shot:
            messages[-1:-1] = deepcopy(list(self.few_shot))
        if self.schema_transform:
            schema = configured["response_format"]["json_schema"]["schema"]
            configured["response_format"]["json_schema"]["schema"] = self.schema_transform(schema)
        if self.snapshot_schema:
            schema = configured["response_format"]["json_schema"]["schema"]
            context = json.loads(messages[1]["content"])
            configured["response_format"]["json_schema"]["schema"] = union_schema(schema, context, self.dynamic_enum)
        return messages, configured


def cleared_values(kind: str) -> dict[str, Any]:
    if kind == "existing":
        return dict(operation="", target_id="", item_id="", advance=False, approach="", reply="")
    if kind == "interact":
        return {"action_id": ""}
    if kind in {"dialogue", "clarify", "unsupported"}:
        return {"action_id": "", "operation": "", "item_id": "", "advance": False,
                **({"target_id": ""} if kind != "dialogue" else {})}
    return {}


def clean_lenient(raw: str) -> tuple[str, dict[str, Any]]:
    audit: dict[str, Any] = {"cleared_fields": {}, "conflict_fields": [], "conflict": False,
                             "existing_operation": False}
    try:
        plan = json.loads(raw)
    except (TypeError, ValueError):
        return raw, audit
    # Tolerance only applies to irrelevant values, never to missing/extra keys or wrong types.
    if (not isinstance(plan, dict) or set(plan) != set(free_actions.PLAN_SCHEMA["required"])
            or any(not isinstance(v, bool if k == "advance" else str) for k, v in plan.items())):
        return raw, audit
    audit["existing_operation"] = plan["kind"] == "existing" and bool(plan["operation"])
    for key, empty in cleared_values(plan["kind"]).items():
        if plan[key] != empty:
            audit["cleared_fields"][key] = plan[key]
            if key not in {"approach", "reply"}:
                audit["conflict_fields"].append(key)
            plan[key] = empty
    audit["conflict"] = bool(audit["conflict_fields"])
    return json.dumps(plan, ensure_ascii=False), audit


def union_schema(schema: dict[str, Any], context: dict[str, Any], dynamic_enum: bool) -> dict[str, Any]:
    actions = [a["id"] for a in context["actions"] if a.get("enabled") and a.get("id")]
    # Only prune operations lacking any candidate surface; engine feasibility stays engine-owned.
    operations = [op for op in free_actions.OPERATIONS if op and (
        bool(context["inventory"]) if op == "use_item" else
        bool(context["obstacles"] or context["objects"]) if op == "observe" else bool(context["obstacles"]))]
    branches = []
    for kind in free_actions.KINDS:
        if dynamic_enum and (kind == "existing" and not actions or kind == "interact" and not operations):
            continue
        branch = deepcopy(schema)
        props = branch["properties"]
        props["kind"].pop("enum", None)
        props["kind"]["const"] = kind
        for field, value in cleared_values(kind).items():
            props[field].pop("enum", None)
            props[field]["const"] = value
        if kind == "existing" and dynamic_enum:
            props["action_id"]["enum"] = actions
        if kind == "interact":
            props["operation"]["enum"] = operations if dynamic_enum else [op for op in free_actions.OPERATIONS if op]
        branches.append(branch)
    return {"type": "object", "anyOf": branches}


VARIANTS = {"default": Variant(), "lenient": Variant(replay_only=True),
            "union_schema": Variant(snapshot_schema=True, dynamic_enum=True),
            "union_schema_noenum": Variant(snapshot_schema=True)}
