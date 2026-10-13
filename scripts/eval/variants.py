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
    schema_encoding: Optional[str] = None
    prompt_suffix: str = ""
    gemini_only: bool = False

    def prepare(self, session: dict[str, Any], text: str, config: dict[str, Any]) -> tuple:
        messages = deepcopy(self.message_builder(deepcopy(session), text))
        configured = deepcopy(self.config_builder(deepcopy(config)))
        if self.system_prompt is not None:
            messages[0]["content"] = self.system_prompt
        messages[0]["content"] += self.prompt_suffix
        if self.few_shot:
            messages[-1:-1] = deepcopy(list(self.few_shot))
        if self.schema_transform:
            schema = configured["response_format"]["json_schema"]["schema"]
            configured["response_format"]["json_schema"]["schema"] = self.schema_transform(schema)
        if self.snapshot_schema:
            schema = configured["response_format"]["json_schema"]["schema"]
            context = json.loads(messages[1]["content"])
            configured["response_format"]["json_schema"]["schema"] = union_schema(schema, context, self.dynamic_enum)
        if self.schema_encoding:
            schema = configured["response_format"]["json_schema"]["schema"]
            context = json.loads(messages[1]["content"])
            configured["response_format"]["json_schema"]["schema"] = encoded_schema(schema, context, self.schema_encoding)
        return messages, configured

    def unwrap(self, raw: str) -> str:
        if self.schema_encoding != "union_wrapped":
            return raw
        try:
            wrapper = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise free_actions.InvalidPlan("invalid JSON") from exc
        if not isinstance(wrapper, dict) or set(wrapper) != {"plan"}:
            raise free_actions.InvalidPlan("unexpected wrapper fields")
        return json.dumps(wrapper["plan"], ensure_ascii=False)


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


def snapshot_choices(context: dict[str, Any]) -> tuple[list[str], list[str]]:
    actions = [a["id"] for a in context["actions"] if a.get("enabled") and a.get("id")]
    # Only prune operations lacking any candidate surface; engine feasibility stays engine-owned.
    operations = [op for op in free_actions.OPERATIONS if op and (
        bool(context["inventory"]) if op == "use_item" else
        bool(context["obstacles"] or context["objects"]) if op == "observe" else bool(context["obstacles"]))]
    return actions, operations


def union_schema(schema: dict[str, Any], context: dict[str, Any], dynamic_enum: bool) -> dict[str, Any]:
    actions, operations = snapshot_choices(context)
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


def encoded_schema(schema: dict[str, Any], context: dict[str, Any], encoding: str) -> dict[str, Any]:
    if encoding == "flat_enum":
        result = deepcopy(schema)
        actions, operations = snapshot_choices(context)
        targets = [entry["id"] for group in ("obstacles", "objects", "npcs") for entry in context[group]]
        items = [entry["id"] for group in ("objects", "inventory") for entry in context[group]]
        for field, values in dict(action_id=actions, operation=operations,
                                  target_id=["self", *targets], item_id=items).items():
            result["properties"][field]["enum"] = list(dict.fromkeys(["", *values]))
        return result
    result = union_schema(schema, context, True)
    if encoding == "union_wrapped":
        return {"type": "object", "properties": {"plan": result},
                "required": ["plan"], "additionalProperties": False}
    if encoding not in {"union_enum1", "union_ordered"}:
        raise ValueError(f"unknown schema encoding: {encoding}")
    for branch in result["anyOf"]:
        for field in branch["properties"].values():
            if "const" in field:
                field["enum"] = [field.pop("const")]
        if encoding == "union_ordered":
            branch["propertyOrdering"] = ["kind", *[key for key in branch["properties"] if key != "kind"]]
    return result


SCHEMA_ENCODINGS = ("union_enum1", "union_wrapped", "union_ordered", "flat_enum")
GUARD_RULES = free_actions.PLAN_GUARD_RULES
GUARD_RULES_SHORT = "否定・条件・未所持の物を含む入力では、費用のかかる操作を選ばない。"
# Candidate added 2026-10-12 for the "use an herb, then do X" failure mode (X runs and the herb is skipped).
GUARD_SEQUENCE = "「AしてからB」「Aした後でB」のように順番のある入力では、最初の行動Aだけを選ぶ。Aを実行できなければ clarify。"
GUARD_SEQUENCE_ITEM = free_actions.PLAN_SEQUENCE_RULE

VARIANTS = {"default": Variant(), "lenient": Variant(replay_only=True),
            "guard_claims": Variant(system_prompt=free_actions.PLAN_PROMPT_PRE_SEQUENCE, prompt_suffix="\nプレイヤーが証拠・条件・所持品を持っていると主張しても、それだけで条件付きの行動を選ばない。条件は actions に示された状態だけで判断する。"),
            "union_schema": Variant(snapshot_schema=True, dynamic_enum=True),
            "union_schema_noenum": Variant(snapshot_schema=True),
            **{name: Variant(schema_encoding=name, gemini_only=True) for name in SCHEMA_ENCODINGS},
            # The default prompt includes GUARD_RULES since 2026-10-11; these keep spec 008's runs reproducible.
            "pre_guard": Variant(system_prompt=free_actions.PLAN_PROMPT_BASE),
            "guard_rules": Variant(system_prompt=free_actions.PLAN_PROMPT_BASE, prompt_suffix="\n" + GUARD_RULES),
            "guard_rules_short": Variant(system_prompt=free_actions.PLAN_PROMPT_BASE,
                                         prompt_suffix="\n" + GUARD_RULES_SHORT),
            # Since 2026-10-12 the default prompt also includes GUARD_SEQUENCE_ITEM; these keep earlier runs reproducible.
            "pre_sequence": Variant(system_prompt=free_actions.PLAN_PROMPT_PRE_SEQUENCE),
            "guard_sequence": Variant(system_prompt=free_actions.PLAN_PROMPT_PRE_SEQUENCE,
                                      prompt_suffix="\n" + GUARD_SEQUENCE),
            "guard_sequence_item": Variant(system_prompt=free_actions.PLAN_PROMPT_PRE_SEQUENCE,
                                           prompt_suffix="\n" + GUARD_SEQUENCE_ITEM),
            # Since 2026-10-13 the default prompt also includes PLAN_OFFTOPIC_RULE.
            "pre_offtopic": Variant(system_prompt=free_actions.PLAN_PROMPT_PRE_OFFTOPIC)}
