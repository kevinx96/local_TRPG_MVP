from __future__ import annotations

import json
import os
import random
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from .scenario_context import (
    fallback_choices_for_session,
    find_scene,
    has_hybrid_prepared_turn,
    infer_scene_from_text,
    load_scenario_pack,
    resolve_scene_id,
    scene_title,
    select_hybrid_context,
    select_scenario_context,
)


HOST_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = HOST_ROOT.parent
SAVE_DIR = HOST_ROOT / "saves"
DEFAULT_SCENARIO = HOST_ROOT / "prompt" / "processed" / "dragon_rpg.json"


DEFAULT_ITEM_CATALOG: dict[str, dict[str, str]] = {
    "鉄の剣": {
        "description": "鍛冶屋で打たれた頑丈な剣。冒険者の基本装備。",
        "effect": "通常攻撃に使用",
    },
    "革の鎧": {
        "description": "なめした革で作られた軽量の鎧。動きやすさと防御力を両立。",
        "effect": "被ダメージを軽減",
    },
    "薬草": {
        "description": "森で採れる癒しの薬草。苦い味がするが、傷を癒す力がある。",
        "effect": "HPを10回復",
    },
}


DEFAULT_CHARACTER: dict[str, Any] = {
    "name": "アルス",
    "description": "世界を救うため旅立つ若き冒険者。",
    "character_id": "",
    "hp": 20,
    "max_hp": 20,
    "mp": 8,
    "max_mp": 8,
    "sp": 10,
    "max_sp": 10,
    "gold": 0,
    "attributes": {},
    "skills": [],
    "inventory": [
        {"name": "鉄の剣", "description": DEFAULT_ITEM_CATALOG["鉄の剣"]["description"], "effect": DEFAULT_ITEM_CATALOG["鉄の剣"]["effect"], "quantity": 1},
        {"name": "革の鎧", "description": DEFAULT_ITEM_CATALOG["革の鎧"]["description"], "effect": DEFAULT_ITEM_CATALOG["革の鎧"]["effect"], "quantity": 1},
        {"name": "薬草", "description": DEFAULT_ITEM_CATALOG["薬草"]["description"], "effect": DEFAULT_ITEM_CATALOG["薬草"]["effect"], "quantity": 1},
    ],
    "equipment": ["鉄の剣", "革の鎧"],
    "background_image": "/static/images/bg_dragon_rpg.png",
    "character_image": "/static/images/char_male_hero.png",
}


PROTOCOL_WARNING_LOGS = (
    "GM応答のJSONを解析できませんでした。",
    "GM応答に状態JSONが含まれていませんでした。",
)

_DICE_ATTR_RE = re.compile(r"^(\d+d\d+)(?:\+(\w+))?$", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config(path: Optional[Path] = None) -> dict[str, Any]:
    config_path = path or HOST_ROOT / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    local_path = _local_config_path(config_path)
    if local_path.exists():
        _deep_update(config, json.loads(local_path.read_text(encoding="utf-8")))
    _apply_config_env_overrides(config)
    return config


def save_config(config: dict[str, Any], path: Optional[Path] = None) -> None:
    base_config_path = path or HOST_ROOT / "config.json"
    target_path = base_config_path if path else _local_config_path(base_config_path)
    target_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def _local_config_path(config_path: Path) -> Path:
    env_path = os.environ.get("TRPG_LOCAL_CONFIG")
    if env_path:
        return resolve_local_path(env_path, default=config_path)
    return config_path.with_name("local_config.json")


def _apply_config_env_overrides(config: dict[str, Any]) -> None:
    active_backend = os.environ.get("TRPG_ACTIVE_BACKEND")
    if active_backend:
        config["active_backend"] = active_backend.strip()

    backend_name = str(config.get("active_backend") or "ollama")
    backends = config.setdefault("backends", {})
    backend = backends.setdefault(backend_name, {})
    if not isinstance(backend, dict):
        backend = {}
        backends[backend_name] = backend

    base_url = os.environ.get("TRPG_LLM_BASE_URL") or os.environ.get("TRPG_OLLAMA_BASE_URL")
    if base_url:
        backend["base_url"] = _normalize_openai_base_url(base_url)

    model = os.environ.get("TRPG_LLM_MODEL") or os.environ.get("TRPG_OLLAMA_MODEL")
    if model:
        backend["model"] = model.strip()

    fallbacks = os.environ.get("TRPG_LLM_FALLBACK_MODELS") or os.environ.get("TRPG_OLLAMA_FALLBACK_MODELS")
    if fallbacks:
        backend["fallback_models"] = [item.strip() for item in fallbacks.split(",") if item.strip()]

    api_key = os.environ.get("TRPG_LLM_API_KEY") or os.environ.get("TRPG_OLLAMA_API_KEY")
    if api_key:
        backend["api_key"] = api_key


def _normalize_openai_base_url(value: str) -> str:
    url = value.strip().rstrip("/")
    return url if url.endswith("/v1") else f"{url}/v1"


def resolve_local_path(value: Optional[str], default: Path = DEFAULT_SCENARIO) -> Path:
    if not value:
        return default
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def read_scenario_prompt(path: Path) -> str:
    """Compatibility helper for older callers; returns the normalized pack as text."""
    return json.dumps(load_scenario_pack(path), ensure_ascii=False)


def create_session(
    scenario_path: Optional[str] = None,
    character_overrides: Optional[dict[str, Any]] = None,
    gm_mode: Optional[str] = None,
    character_id: Optional[str] = None,
) -> dict[str, Any]:
    normalized_gm_mode = _normalize_gm_mode(gm_mode)
    path = _scenario_path_for_gm_mode(resolve_local_path(scenario_path), normalized_gm_mode)
    scenario_pack = load_scenario_pack(path)
    character = deepcopy(DEFAULT_CHARACTER)

    if character_id:
        char_template = _find_character_in_pack(scenario_pack, character_id)
        if char_template:
            character = _character_from_template(char_template)
        else:
            character["character_id"] = character_id

    if character_overrides:
        if "name" in character_overrides:
            character["name"] = character_overrides["name"]
        other = {k: v for k, v in character_overrides.items() if k != "name"}
        if other:
            _deep_update(character, other)
        _normalize_character(character)

    meta = scenario_pack.get("meta", {})
    session = {
        "id": uuid.uuid4().hex,
        "scenario_path": str(path),
        "scenario_title": str(meta.get("title") or path.stem),
        "gm_mode": normalized_gm_mode,
        "scenario_pack": scenario_pack,
        "current_scene": str(meta.get("initial_scene") or "start"),
        "character": character,
        "messages": [],
        "system_logs": [],
        "dice_log": [],
        "choices": [],
        "next_dice_type": "1d20",
        "next_dice_dc": 10,
        "needs_opening": True,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    save_session(session)
    return public_session(session)


def _normalize_gm_mode(value: Optional[str]) -> str:
    mode = str(value or "semi").strip().lower()
    return mode if mode in {"semi", "full"} else "semi"


def _scenario_path_for_gm_mode(path: Path, gm_mode: str) -> Path:
    if gm_mode != "semi" or path.stem.endswith("_hybrid"):
        return path
    hybrid_path = path.with_name(f"{path.stem}_hybrid{path.suffix}")
    return hybrid_path.resolve() if hybrid_path.exists() else path


def load_session(session_id: str) -> dict[str, Any]:
    path = SAVE_DIR / f"{session_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_session(session: dict[str, Any]) -> None:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    session["updated_at"] = utc_now()
    (SAVE_DIR / f"{session['id']}.json").write_text(
        json.dumps(session, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def public_session(session: dict[str, Any]) -> dict[str, Any]:
    scene_context = select_scenario_context(session, "")
    matched = scene_context.get("matched") if isinstance(scene_context, dict) else {}
    enemies = matched.get("enemies") if isinstance(matched, dict) else []
    public = deepcopy(session)
    public.pop("scenario_prompt", None)
    public.pop("scenario_pack", None)
    public["current_scene_title"] = scene_title(session)
    public["enemies"] = enemies if isinstance(enemies, list) else []
    public["in_combat"] = bool(public["enemies"])

    from .gm_contract import extract_text_choices, sanitize_visible_text

    recovered_choices: list[dict[str, str]] = []
    for message in public.get("messages", []):
        if message.get("role") == "assistant":
            original_text = str(message.get("text", ""))
            text_choices = extract_text_choices(original_text)
            if text_choices:
                recovered_choices = text_choices
            message["text"] = sanitize_visible_text(original_text)
    if recovered_choices and len(recovered_choices) > len(public.get("choices") or []):
        public["choices"] = recovered_choices
    public["choices"] = annotate_choices_for_character(public.get("choices"), public.get("character", {}))
    public["system_logs"] = [
        log for log in public.get("system_logs", [])
        if not _is_protocol_warning_log(str(log.get("text", "")))
    ]
    return public


def add_player_message(session: dict[str, Any], text: str, speaker: str = "プレイヤー") -> None:
    session["messages"].append({"role": "user", "speaker": speaker, "text": text, "created_at": utc_now()})


def add_assistant_message(session: dict[str, Any], text: str, speaker: str = "GM") -> None:
    session["messages"].append({"role": "assistant", "speaker": speaker, "text": text, "created_at": utc_now()})


def add_system_log(session: dict[str, Any], text: str) -> None:
    if text:
        session["system_logs"].append({"text": text, "created_at": utc_now()})


def _is_protocol_warning_log(text: str) -> bool:
    return text in PROTOCOL_WARNING_LOGS


def roll_dice(session: dict[str, Any], expression: str = "1d20", dc: Optional[int] = None, client_rolls: Optional[list[int]] = None) -> dict[str, Any]:
    expr = str(expression or "").strip() or "1d20"
    dice_part = expr
    attr_key = ""
    dice_match = _DICE_ATTR_RE.match(expr)
    if dice_match:
        dice_part = dice_match.group(1)
        attr_key = _canonical_attr_key(dice_match.group(2) or "")
    count, sides = _parse_dice_expression(dice_part)
    if client_rolls and isinstance(client_rolls, list) and len(client_rolls) == count and all(1 <= int(r) <= sides for r in client_rolls):
        rolls = [int(r) for r in client_rolls]
    else:
        rolls = [random.randint(1, sides) for _ in range(count)]
    base_total = sum(rolls)
    attr_mod = 0
    if attr_key:
        character = session.get("character", {})
        attrs = character.get("attributes", {}) if isinstance(character.get("attributes"), dict) else {}
        attr_mod = _attr_value(attrs, attr_key)
    total = base_total + attr_mod
    entry: dict[str, Any] = {"expression": expr, "rolls": rolls, "total": total, "created_at": utc_now()}
    if isinstance(dc, int):
        entry["dc"] = dc
        if dc > 0:
            entry["success"] = total >= dc
    if attr_key:
        entry["base_total"] = base_total
        entry["attr_mod"] = attr_mod
        entry["attr_key"] = attr_key
    session["dice_log"].append(entry)
    return entry


def apply_gm_payload(
    session: dict[str, Any],
    gm_text: str,
    payload: Optional[dict[str, Any]],
    parse_warning: Optional[str] = None,
) -> None:
    current_dice_dc = session.get("next_dice_dc", 0)
    roll_failed = _latest_roll_failed(session, current_dice_dc)
    if roll_failed and _should_coerce_failed_roll_text(gm_text, payload, parse_warning):
        gm_text = _failed_roll_text(session)
    if gm_text.strip():
        add_assistant_message(session, gm_text)

    if not payload:
        session["choices"] = _fallback_choices_after_model_failure(session, current_dice_dc)
        add_system_log(session, "choices fallback: model returned no usable JSON.")
        return

    add_system_log(session, str(payload.get("system_log") or "").strip())

    dice_type = payload.get("dice_type")
    if isinstance(dice_type, str) and dice_type.strip():
        session["next_dice_type"] = dice_type.strip()
    dice_dc = payload.get("dice_dc")
    if isinstance(dice_dc, (int, float)):
        session["next_dice_dc"] = int(dice_dc)

    state_delta = payload.get("state_delta") or {}
    if not isinstance(state_delta, dict):
        add_system_log(session, "GM応答のstate_deltaが不正だったため無視しました。")
        return
    _infer_state_delta_from_text(gm_text, session, state_delta)
    _infer_scene_delta_from_text(gm_text, session, state_delta)
    apply_state_delta(session, state_delta)

    raw_choices = payload.get("choices")
    if isinstance(raw_choices, list) and raw_choices:
        choices = _normalize_choices(raw_choices)
        if choices:
            session["choices"] = choices
            return
        add_system_log(session, "choices fallback: model choices were empty after normalization.")
    else:
        add_system_log(session, "choices fallback: model did not provide choices.")
    session["choices"] = _fallback_choices_after_model_failure(session, current_dice_dc)


def _normalize_choices(raw: list[Any]) -> list[dict[str, Any]]:
    choices = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            choices.append({"text": item.strip(), "preview": "", "risk": ""})
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("option") or item.get("action") or item.get("label") or "").strip()
            if text:
                choices.append({
                    "text": text,
                    "preview": str(item.get("preview", "")),
                    "risk": str(item.get("risk", "")),
                    **({"requirements": deepcopy(item["requirements"])} if "requirements" in item else {}),
                })
    return choices[:5]


def annotate_choices_for_character(raw_choices: Any, character: dict[str, Any]) -> list[dict[str, Any]]:
    choices: list[dict[str, Any]] = []
    for item in raw_choices if isinstance(raw_choices, list) else []:
        choice = {"text": str(item), "preview": "", "risk": ""} if isinstance(item, str) else deepcopy(item)
        if not isinstance(choice, dict):
            continue
        enabled, reason = choice_requirement_status(choice, character)
        choice["enabled"] = enabled
        if reason:
            choice["disabled_reason"] = reason
        else:
            choice.pop("disabled_reason", None)
        choices.append(choice)
    return choices


def choice_requirement_status(choice: dict[str, Any], character: dict[str, Any]) -> tuple[bool, str]:
    requirements = choice.get("requirements")
    if requirements is None:
        requirements = _requirements_from_risk(str(choice.get("risk") or ""))
    if not requirements:
        return True, ""

    attrs = character.get("attributes", {}) if isinstance(character.get("attributes"), dict) else {}
    if isinstance(requirements, list):
        passed = all(_requirement_passes(req, attrs) for req in requirements)
        return (True, "") if passed else (False, _requirement_reason(requirements, "all"))
    if not isinstance(requirements, dict):
        return True, ""
    if isinstance(requirements.get("any"), list):
        reqs = requirements["any"]
        passed = any(_requirement_passes(req, attrs) for req in reqs)
        return (True, "") if passed else (False, _requirement_reason(reqs, "any"))
    if isinstance(requirements.get("all"), list):
        reqs = requirements["all"]
        passed = all(_requirement_passes(req, attrs) for req in reqs)
        return (True, "") if passed else (False, _requirement_reason(reqs, "all"))
    passed = _requirement_passes(requirements, attrs)
    return (True, "") if passed else (False, _requirement_reason([requirements], "all"))


def _requirements_from_risk(risk: str) -> dict[str, Any]:
    threshold_match = re.search(r"(\d+)\s*(?:以上|or higher|以上で)", risk, re.IGNORECASE)
    if not threshold_match:
        return {}
    threshold = int(threshold_match.group(1))
    attr_keys = _attribute_keys_from_text(risk)
    if not attr_keys:
        return {}
    if "または" in risk or "or" in risk.lower() or "/" in risk:
        return {"any": [{"attribute": key, "gte": threshold} for key in attr_keys]}
    return {"all": [{"attribute": key, "gte": threshold} for key in attr_keys]}


def _attribute_keys_from_text(text: str) -> list[str]:
    keyword_map = {
        "str": ("\u7b4b\u529b", "strength"),
        "dex": ("\u654f\u6377", "\u5668\u7528", "dexterity"),
        "int": ("\u77e5\u529b", "\u77e5\u6027", "intelligence"),
        "wis": ("\u5224\u65ad", "\u77e5\u6075", "\u77e5\u6167", "wisdom"),
        "end": ("\u8010\u4e45", "\u4f53\u529b", "endurance", "con"),
        "cha": ("\u9b45\u529b", "charisma"),
    }
    lower = text.lower()
    keys: list[str] = []
    for key, keywords in keyword_map.items():
        if re.search(rf"\b{re.escape(key)}\b", lower) or any(keyword in lower for keyword in keywords):
            keys.append(key)
    return [key for index, key in enumerate(keys) if key not in keys[:index]]


def _requirement_passes(requirement: Any, attrs: dict[str, Any]) -> bool:
    if not isinstance(requirement, dict):
        return True
    attr_key = _canonical_attr_key(str(requirement.get("attribute") or requirement.get("attr") or ""))
    if not attr_key:
        return True
    value = _attr_value(attrs, attr_key)
    if isinstance(requirement.get("gte"), (int, float)):
        return value >= int(requirement["gte"])
    if isinstance(requirement.get("min"), (int, float)):
        return value >= int(requirement["min"])
    if isinstance(requirement.get("gt"), (int, float)):
        return value > int(requirement["gt"])
    return True


def _requirement_reason(requirements: list[Any], mode: str) -> str:
    labels = [_requirement_label(req) for req in requirements if isinstance(req, dict)]
    labels = [label for label in labels if label]
    if not labels:
        return "\u6761\u4ef6\u3092\u6e80\u305f\u3057\u3066\u3044\u307e\u305b\u3093"
    joiner = "\u307e\u305f\u306f" if mode == "any" else "\u3068"
    return f"{joiner.join(labels)}\u304c\u5fc5\u8981"


def _requirement_label(requirement: dict[str, Any]) -> str:
    attr_key = _canonical_attr_key(str(requirement.get("attribute") or requirement.get("attr") or ""))
    if not attr_key:
        return ""
    label_map = {"str": "\u7b4b\u529b", "dex": "\u654f\u6377", "int": "\u77e5\u529b", "wis": "\u5224\u65ad", "end": "\u8010\u4e45", "cha": "\u9b45\u529b"}
    threshold = requirement.get("gte", requirement.get("min", requirement.get("gt", "")))
    suffix = f"{int(threshold)}\u4ee5\u4e0a" if isinstance(threshold, (int, float)) else ""
    return f"{label_map.get(attr_key, attr_key)}{suffix}"


def _canonical_attr_key(key: str) -> str:
    mapping = {"con": "end", "endurance": "end", "\u8010\u4e45": "end", "\u4f53\u529b": "end", "\u7b4b\u529b": "str"}
    return mapping.get(key.strip().lower(), key.strip().lower())


def _attr_value(attrs: dict[str, Any], attr_key: str) -> int:
    keys = [attr_key]
    if attr_key == "end":
        keys.append("con")
    elif attr_key == "con":
        keys.append("end")
    for key in keys:
        value = attrs.get(key)
        if isinstance(value, (int, float)):
            return int(value)
    return 0


def _fallback_choices_after_model_failure(session: dict[str, Any], current_dice_dc: Any = None) -> list[dict[str, str]]:
    choices = fallback_choices_for_session(session)
    if not _latest_roll_failed(session, current_dice_dc):
        return choices
    failed_action = _latest_player_text(session).strip()
    filtered = [
        choice for choice in choices
        if str(choice.get("text") or "").strip() != failed_action
    ]
    recovery = {
        "text": "助言を受け流して別の準備に移る",
        "preview": "判定に失敗したため、有用な助言は得られませんでした",
        "risk": "判定不要",
    }
    return [recovery, *filtered][:5]


def _should_coerce_failed_roll_text(gm_text: str, payload: Optional[dict[str, Any]], parse_warning: Optional[str]) -> bool:
    if parse_warning:
        return True
    if not gm_text.strip():
        return True
    if not isinstance(payload, dict):
        return True
    if _looks_like_mechanical_roll_text(gm_text):
        return True
    raw_choices = payload.get("choices")
    return not (isinstance(raw_choices, list) and _normalize_choices(raw_choices))


def _looks_like_mechanical_roll_text(text: str) -> bool:
    lowered = text.lower()
    patterns = (
        "判定は届かなかった",
        "判定に失敗",
        "dc",
        "1d20",
        "roll",
        "dice",
    )
    return any(pattern in lowered for pattern in patterns)


def _failed_roll_text(session: dict[str, Any]) -> str:
    action = _latest_player_text(session).strip() or "その行動"
    character_name = str(session.get("character", {}).get("name") or "冒険者")
    return (
        f"{character_name}は「{action}」についてさらに踏み込んだ。"
        "しかし相手は表情を曇らせ、言葉を選ぶばかりで核心には触れない。"
        "返ってきたのは噂と曖昧な忠告だけで、確かな手がかりは得られなかった。"
    )


def _latest_roll_failed(session: dict[str, Any], current_dice_dc: Any = None) -> bool:
    dice_log = session.get("dice_log")
    if not isinstance(dice_log, list) or not dice_log:
        return False
    latest = dice_log[-1]
    if not isinstance(latest, dict):
        return False
    dc = current_dice_dc if current_dice_dc is not None else session.get("next_dice_dc", 0)
    if not isinstance(dc, (int, float)) or int(dc) <= 0:
        return False
    total = latest.get("total")
    return isinstance(total, (int, float)) and int(total) < int(dc)


def apply_state_delta(session: dict[str, Any], delta: dict[str, Any]) -> None:
    character = session["character"]
    for stat in ("hp", "mp", "sp"):
        before = int(character.get(stat, 0))
        if isinstance(delta.get(f"{stat}_change"), (int, float)):
            character[stat] = int(character.get(stat, 0) + delta[f"{stat}_change"])
        if isinstance(delta.get(stat), (int, float)):
            character[stat] = int(delta[stat])
        max_key = f"max_{stat}"
        character[stat] = max(0, min(int(character.get(max_key, character[stat])), int(character[stat])))
        actual_change = int(character[stat]) - before
        if actual_change > 0:
            add_system_log(session, f"{stat.upper()}が{actual_change}回復しました。")
        elif actual_change < 0:
            add_system_log(session, f"{stat.upper()}が{abs(actual_change)}減少しました。")

    if isinstance(delta.get("gold_change"), (int, float)):
        before = int(character.get("gold", 0))
        character["gold"] = max(0, before + int(delta["gold_change"]))
        actual_change = int(character["gold"]) - before
        if actual_change > 0:
            add_system_log(session, f"{actual_change}ゴールドを獲得しました。")
        elif actual_change < 0:
            add_system_log(session, f"{abs(actual_change)}ゴールドを消費しました。")
    if isinstance(delta.get("gold"), (int, float)):
        before = int(character.get("gold", 0))
        character["gold"] = max(0, int(delta["gold"]))
        if int(character["gold"]) != before:
            add_system_log(session, f"所持金が{int(character['gold'])}ゴールドになりました。")

    for item in _as_item_list(delta.get("inventory_add")):
        item_name = str(item["name"]).strip()
        add_qty = _safe_quantity(item.get("quantity"), 1)
        existing = next(
            (inv_item for inv_item in character["inventory"] if (inv_item.get("name") if isinstance(inv_item, dict) else inv_item) == item_name),
            None,
        )
        if isinstance(existing, dict):
            existing["quantity"] = int(existing.get("quantity", 1)) + add_qty
        else:
            enriched = _enrich_item(item if isinstance(item, dict) else {"name": item})
            enriched["quantity"] = add_qty
            character["inventory"].append(enriched)
        add_system_log(session, f"{item_name} x{add_qty}を入手しました。")

    for item in _as_text_list(delta.get("inventory_remove")):
        removed_qty = 0
        new_inv = []
        for existing in character["inventory"]:
            ename = existing.get("name") if isinstance(existing, dict) else existing
            if ename == item and isinstance(existing, dict):
                existing["quantity"] = int(existing.get("quantity", 1)) - 1
                removed_qty += 1
                if existing["quantity"] > 0:
                    new_inv.append(existing)
            else:
                new_inv.append(existing)
        character["inventory"] = new_inv
        if removed_qty:
            add_system_log(session, f"{item} x{removed_qty}を失いました。")

    for image_key in ("background_image", "character_image"):
        if isinstance(delta.get(image_key), str):
            character[image_key] = delta[image_key]

    attr_changes = delta.get("attribute_changes")
    if isinstance(attr_changes, dict):
        attrs = character.setdefault("attributes", {})
        for attr_key, attr_change in attr_changes.items():
            if isinstance(attr_change, (int, float)):
                before = int(attrs.get(attr_key, 0))
                attrs[attr_key] = before + int(attr_change)
                actual_change = int(attrs[attr_key]) - before
                if actual_change > 0:
                    add_system_log(session, f"{attr_key}が{actual_change}上昇しました。")
                elif actual_change < 0:
                    add_system_log(session, f"{attr_key}が{abs(actual_change)}減少しました。")

    if isinstance(delta.get("current_scene"), str) and delta["current_scene"].strip():
        pack = session.get("scenario_pack") if isinstance(session.get("scenario_pack"), dict) else None
        current_scene = delta["current_scene"].strip()
        resolved_scene = resolve_scene_id(pack, current_scene) if pack else current_scene
        if _scene_transition_allowed(session, resolved_scene):
            session["current_scene"] = resolved_scene
        else:
            add_system_log(session, f"不正な場面遷移を無視しました: {resolved_scene}")


def _enrich_item(item: dict[str, Any]) -> dict[str, Union[str, int]]:
    name = _item_name_from_dict(item) or "不明"
    catalog_entry = DEFAULT_ITEM_CATALOG.get(name, {})
    return {
        "name": name,
        "description": str(item.get("description") or catalog_entry.get("description", "")),
        "effect": str(item.get("effect") or catalog_entry.get("effect", "")),
        "quantity": _safe_quantity(item.get("quantity"), 1),
    }


def build_llm_messages(session: dict[str, Any], latest_roll: dict[str, Any], contract_prompt: str) -> list[dict[str, str]]:
    if _should_use_hybrid_messages(session, latest_roll):
        return _build_hybrid_llm_messages(session, latest_roll, contract_prompt)

    config = load_config()
    prompting = config.get("prompting") if isinstance(config.get("prompting"), dict) else {}
    history_messages = _bounded_int(prompting.get("history_messages"), default=4, minimum=0, maximum=12)
    memory_max_chars = _bounded_int(prompting.get("memory_max_chars"), default=1200, minimum=0, maximum=4000)
    action_history_max = _bounded_int(prompting.get("action_history_max"), default=40, minimum=0, maximum=200)
    action_history_item_chars = _bounded_int(prompting.get("action_history_item_chars"), default=80, minimum=20, maximum=240)
    context_max_chars = _bounded_int(prompting.get("context_max_chars"), default=3500, minimum=500, maximum=8000)
    if session.get("gm_mode") == "full":
        history_messages = min(history_messages, 2)
        memory_max_chars = min(memory_max_chars, 600)
        action_history_max = min(action_history_max, 20)
        action_history_item_chars = min(action_history_item_chars, 60)

    character = session["character"]
    player_text = _latest_player_text(session)
    scenario_context = select_scenario_context(session, player_text)
    state_summary = _current_state_summary(session, character, latest_roll)
    context_json = json.dumps(scenario_context, ensure_ascii=False)
    context_json = _trim_context_to_budget(context_json, context_max_chars)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": contract_prompt},
        {"role": "system", "content": "シナリオコンテキスト:\n" + context_json},
        {"role": "system", "content": "現在のゲーム状態:\n" + state_summary},
    ]
    memory_summary = _conversation_memory_summary(session, keep_last=history_messages, max_chars=memory_max_chars)
    if memory_summary:
        messages.append({"role": "system", "content": "これまでの会話要約:\n" + memory_summary})
    action_history = _player_action_history(session, max_items=action_history_max, item_chars=action_history_item_chars)
    if action_history:
        messages.append({"role": "system", "content": "プレイヤー行動履歴:\n" + action_history})

    recent_messages = session["messages"][-history_messages:] if history_messages else []
    for message in recent_messages:
        role = "assistant" if message["role"] == "assistant" else "user"
        messages.append({"role": role, "content": f"{message['speaker']}: {message['text']}"})
    return messages


def _should_use_hybrid_messages(session: dict[str, Any], latest_roll: dict[str, Any]) -> bool:
    if session.get("gm_mode") != "semi":
        return False
    opening = str(latest_roll.get("expression") or "") == "opening"
    return has_hybrid_prepared_turn(session, _latest_player_text(session), opening=opening)


def _build_hybrid_llm_messages(session: dict[str, Any], latest_roll: dict[str, Any], contract_prompt: str) -> list[dict[str, str]]:
    character = session["character"]
    player_text = _latest_player_text(session)
    opening = str(latest_roll.get("expression") or "") == "opening"
    hybrid_context = select_hybrid_context(session, player_text, opening=opening)
    state_summary = _current_state_summary(session, character, latest_roll)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": contract_prompt},
        {
            "role": "system",
            "content": (
                "【SEMI/HYBRIDモード】\n"
                "prepared_turn.draft を完成済みのGM応答として扱ってください。\n"
                "gm_text は原則として draft.gm_text を維持し、プレイヤー名・直前の発言・現在状態に矛盾する最小部分だけを書き換えてください。\n"
                "ユーザーが名前を入力しただけ、または開始操作だけの場合は、文体・出来事・NPC台詞・報酬内容を変えないでください。\n"
                "draft.state_delta, dice_type, dice_dc, choices はプレイヤーの行動が明らかに結果と異なる場合のみ調整してください。\n"
                "新しい展開、未指定のアイテム、未指定の選択肢を追加しないでください。\n"
                "gm_text, system_log, choices は日本語だけで出力してください。英語のIDや補助語を本文へコピーしないでください。\n"
                "出力は通常のGM JSONオブジェクト1つだけにしてください。\n\n"
                + json.dumps(hybrid_context, ensure_ascii=False)
            ),
        },
        {"role": "system", "content": "現在のゲーム状態:\n" + state_summary},
    ]
    if player_text:
        messages.append({"role": "user", "content": f"プレイヤー: {player_text}"})
    return messages


def _current_state_summary(session: dict[str, Any], character: dict[str, Any], latest_roll: dict[str, Any]) -> str:
    inventory_summary = [i["name"] if isinstance(i, dict) else i for i in character.get("inventory", [])]
    skills_summary = [
        {"name": s.get("name", ""), "cost": s.get("cost", 0), "cost_type": s.get("cost_type", "")}
        for s in character.get("skills", []) if isinstance(s, dict)
    ]
    return json.dumps(
        {
            "current_scene": session["current_scene"],
            "character": {
                "name": character.get("name"),
                "hp": character.get("hp"),
                "max_hp": character.get("max_hp"),
                "mp": character.get("mp"),
                "max_mp": character.get("max_mp"),
                "sp": character.get("sp"),
                "max_sp": character.get("max_sp"),
                "gold": character.get("gold", 0),
                "attributes": character.get("attributes", {}),
                "skills": skills_summary if skills_summary else None,
                "inventory": inventory_summary,
            },
            "latest_dice_roll": latest_roll,
        },
        ensure_ascii=False,
        default=lambda _: None,
    )


def _deep_update(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _conversation_memory_summary(session: dict[str, Any], keep_last: int, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    messages = session.get("messages", [])
    if not isinstance(messages, list) or len(messages) <= keep_last:
        return ""
    older_messages = messages[:-keep_last] if keep_last else messages
    lines: list[str] = []
    for message in older_messages[-8:]:
        if not isinstance(message, dict):
            continue
        speaker = str(message.get("speaker") or message.get("role") or "不明")
        text = _one_line(str(message.get("text") or ""), limit=140)
        if text:
            lines.append(f"- {speaker}: {text}")
    summary = "\n".join(lines)
    if len(summary) <= max_chars:
        return summary
    return summary[-max_chars:].lstrip()


def _player_action_history(session: dict[str, Any], max_items: int, item_chars: int) -> str:
    if max_items <= 0:
        return ""
    actions: list[str] = []
    for message in session.get("messages", []):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        text = _one_line(str(message.get("text") or ""), limit=item_chars)
        if text:
            actions.append(text)
    if not actions:
        return ""
    recent_actions = actions[-max_items:]
    start_index = len(actions) - len(recent_actions) + 1
    return "\n".join(f"{index}. {text}" for index, text in enumerate(recent_actions, start=start_index))


def _one_line(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _trim_context_to_budget(context_json: str, max_chars: int) -> str:
    if len(context_json) <= max_chars:
        return context_json
    try:
        ctx = json.loads(context_json)
    except json.JSONDecodeError:
        return context_json[:max_chars]
    if isinstance(ctx.get("matched"), dict):
        groups = list(ctx["matched"].items())
        groups.sort(key=lambda item: len(item[1]) if isinstance(item[1], list) else 0, reverse=True)
        removed = []
        for key, value in groups:
            if len(ctx["matched"]) <= 1:
                break
            del ctx["matched"][key]
            removed.append(key)
            if len(json.dumps(ctx, ensure_ascii=False)) <= max_chars:
                break
        if len(json.dumps(ctx, ensure_ascii=False)) > max_chars:
            for key in removed:
                ctx["matched"][key] = []
    if isinstance(ctx.get("rules"), list):
        ctx.pop("rules", None)
    ctx.pop("source_path", None)
    result = json.dumps(ctx, ensure_ascii=False)
    return result[:max_chars] if len(result) > max_chars else result


def _normalize_character(character: dict[str, Any]) -> None:
    for stat in ("hp", "mp", "sp"):
        max_key = f"max_{stat}"
        character[max_key] = int(character.get(max_key, character.get(stat, 0)))
        character[stat] = max(0, min(character[max_key], int(character.get(stat, character[max_key]))))
    character["equipment"] = _as_text_list(character.get("equipment"))
    character["gold"] = max(0, int(character.get("gold", 0)))
    character["character_id"] = str(character.get("character_id") or "")
    attrs = character.get("attributes") if isinstance(character.get("attributes"), dict) else {}
    character["attributes"] = _normalize_attribute_map(attrs)
    if not isinstance(character.get("skills"), list):
        character["skills"] = []
    raw_inv = character.get("inventory", [])
    if isinstance(raw_inv, list):
        character["inventory"] = [_ensure_item_object(i) for i in raw_inv]


def _ensure_item_object(item: Any) -> dict[str, Union[str, int]]:
    if isinstance(item, dict):
        return _enrich_item(item)
    name = str(item).strip() if item else "不明"
    return _enrich_item({"name": name})


def _find_character_in_pack(pack: dict[str, Any], character_id: str) -> Optional[dict[str, Any]]:
    characters = pack.get("characters")
    if not isinstance(characters, list):
        return None
    for char in characters:
        if isinstance(char, dict) and str(char.get("id")) == character_id:
            return char
    return None


def _character_from_template(template: dict[str, Any]) -> dict[str, Any]:
    character = deepcopy(DEFAULT_CHARACTER)
    character["character_id"] = str(template.get("id", ""))
    character["name"] = str(template.get("default_name") or template.get("name") or character["name"])
    character["description"] = str(template.get("description") or character["description"])
    if template.get("image") or template.get("character_image"):
        character["character_image"] = str(template.get("image") or template.get("character_image") or "")
    for stat in ("hp", "max_hp", "mp", "max_mp", "sp", "max_sp", "gold"):
        if isinstance(template.get(stat), (int, float)):
            character[stat] = int(template[stat])
    attrs = template.get("attributes")
    if isinstance(attrs, dict):
        character["attributes"] = _normalize_attribute_map(attrs)
    if isinstance(template.get("inventory"), list):
        character["inventory"] = deepcopy(template["inventory"])
    if isinstance(template.get("equipment"), list):
        character["equipment"] = _as_text_list(template["equipment"])
    if isinstance(template.get("skills"), list):
        character["skills"] = deepcopy(template["skills"])
    _normalize_character(character)
    return character


def _normalize_attribute_map(attrs: dict[str, Any]) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for key, value in attrs.items():
        canonical = _canonical_attr_key(str(key))
        parsed = int(value) if isinstance(value, (int, float)) else 0
        normalized[canonical] = max(parsed, normalized.get(canonical, parsed))
    return normalized


def _as_item_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, str):
        return [{"name": value.strip()}] if value.strip() else []
    if isinstance(value, dict):
        normalized = _normalize_item_delta(value)
        return [normalized] if normalized else []
    if isinstance(value, list):
        items: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                items.append({"name": item.strip()})
            elif isinstance(item, dict):
                normalized = _normalize_item_delta(item)
                if normalized:
                    items.append(normalized)
        return items
    return []


def _normalize_item_delta(item: dict[str, Any]) -> Optional[dict[str, Any]]:
    name = _item_name_from_dict(item)
    if not name:
        return None
    normalized = dict(item)
    normalized["name"] = name
    normalized["quantity"] = _safe_quantity(item.get("quantity"), 1)
    return normalized


def _item_name_from_dict(item: dict[str, Any]) -> str:
    for key in ("name", "item_name", "item", "title", "label", "id"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _safe_quantity(value: Any, default: int = 1) -> int:
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        quantity = default
    return max(1, quantity)


def _as_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _infer_state_delta_from_text(gm_text: str, session: dict[str, Any], delta: dict[str, Any]) -> None:
    if isinstance(delta.get("gold"), (int, float)):
        return
    if isinstance(delta.get("gold_change"), (int, float)) and int(delta["gold_change"]) != 0:
        return
    if int(session.get("character", {}).get("gold", 0)) > 0:
        return
    if not any(marker in gm_text for marker in ("与え", "受け取", "獲得", "入手", "報酬", "gold", "ゴールド")):
        return
    match = re.search(r"(\d+)\s*(?:ゴールド|gold|g|金貨|金币|金幣)", gm_text, re.IGNORECASE)
    if match:
        delta["gold_change"] = int(match.group(1))


def _infer_scene_delta_from_text(gm_text: str, session: dict[str, Any], delta: dict[str, Any]) -> None:
    if isinstance(delta.get("current_scene"), str) and delta["current_scene"].strip():
        return
    player_text = _latest_player_text(session)
    explicit_scene = infer_scene_from_text(session, player_text)
    if explicit_scene:
        delta["current_scene"] = explicit_scene


def _scene_transition_allowed(session: dict[str, Any], target_scene: str) -> bool:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return True
    target = find_scene(pack, target_scene)
    if not target:
        return False
    current_scene_id = str(session.get("current_scene") or "")
    if str(target.get("id") or "") == current_scene_id:
        return True
    current_scene = find_scene(pack, current_scene_id)
    if not current_scene:
        return True
    next_scene_ids = _as_text_list(current_scene.get("next_scene_ids"))
    if not next_scene_ids:
        return True
    allowed = {resolve_scene_id(pack, scene_id) for scene_id in next_scene_ids}
    return str(target.get("id") or "") in allowed


def _latest_player_text(session: dict[str, Any]) -> str:
    for message in reversed(session.get("messages", [])):
        if message.get("role") == "user":
            return str(message.get("text") or "")
    return ""


def _parse_dice_expression(expression: str) -> tuple[int, int]:
    parts = expression.lower().split("d", 1)
    if len(parts) != 2:
        return 1, 20
    try:
        count = max(1, min(20, int(parts[0] or "1")))
        sides = max(2, min(1000, int(parts[1])))
    except ValueError:
        return 1, 20
    return count, sides
