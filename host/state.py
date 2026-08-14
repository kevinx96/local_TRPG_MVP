from __future__ import annotations

import json
import math
import os
import random
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from .intent_resolver import resolve_intent
from .item_mechanics import item_combat_spec, structured_item_effect
from .scenario_context import (
    current_actions_for_session,
    fallback_choices_for_session,
    find_scene,
    has_hybrid_prepared_turn,
    load_scenario_pack,
    scene_title,
    select_hybrid_context,
    select_scenario_context,
)
from .combat import ensure_combat_started, public_combat
from .world_state import (
    commit_world_position,
    current_location_id,
    current_location_title,
    current_scene_id,
    ensure_world_state,
)


HOST_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = HOST_ROOT.parent
SAVE_DIR = HOST_ROOT / "saves"
DEFAULT_SCENARIO = HOST_ROOT / "prompt" / "processed" / "dragon_rpg.json"


DEFAULT_ITEM_CATALOG: dict[str, dict[str, Any]] = {
    "鉄の剣": {
        "description": "鍛冶屋で打たれた頑丈な剣。冒険者の基本装備。",
        "combat": {"kind": "weapon", "name": "鉄の剣", "damage": "1d8+str/3", "accuracy": 90, "element": "physical"},
    },
    "革の鎧": {
        "description": "なめした革で作られた軽量の鎧。動きやすさと防御力を両立。",
        "combat": {"kind": "armor", "defense": 1},
    },
    "薬草": {
        "description": "森で採れる癒しの薬草。苦い味がするが、傷を癒す力がある。",
        "combat": {"kind": "heal", "healing": "10", "consumable": True},
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
        {"name": "鉄の剣", "description": DEFAULT_ITEM_CATALOG["鉄の剣"]["description"], "effect": "通常攻撃 1d8+str/3ダメージ / 命中率90% / physical属性", "combat": deepcopy(DEFAULT_ITEM_CATALOG["鉄の剣"]["combat"]), "quantity": 1},
        {"name": "革の鎧", "description": DEFAULT_ITEM_CATALOG["革の鎧"]["description"], "effect": "被ダメージを1軽減", "combat": deepcopy(DEFAULT_ITEM_CATALOG["革の鎧"]["combat"]), "quantity": 1},
        {"name": "薬草", "description": DEFAULT_ITEM_CATALOG["薬草"]["description"], "effect": "HPを10回復 / 消耗品", "combat": deepcopy(DEFAULT_ITEM_CATALOG["薬草"]["combat"]), "quantity": 1},
    ],
    "equipment": ["鉄の剣", "革の鎧"],
    "background_image": "/static/images/bg_dragon_rpg.png",
    "character_image": "/static/images/char_male_hero.png",
}


PROTOCOL_WARNING_LOGS = (
    "GM応答のJSONを解析できませんでした。",
    "GM応答に状態JSONが含まれていませんでした。",
)

MODEL_RESOURCE_DELTA_KEYS = ("hp_change", "mp_change", "sp_change", "gold_change")
MODEL_MAX_ATTRIBUTE_DELTA = 3
MODEL_MAX_GOLD_DELTA = 10_000
MODEL_MAX_ITEM_QUANTITY = 99
FREEFORM_TURN_LIMIT = 3

_DICE_ATTR_RE = re.compile(r"^(\d+d\d+)(?:\+(\w+))?$", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config(path: Optional[Path] = None) -> dict[str, Any]:
    config_path = path or HOST_ROOT / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    local_path = _local_config_path(config_path)
    if local_path.exists():
        _deep_update(config, json.loads(local_path.read_text(encoding="utf-8-sig")))
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
            character = _character_from_template(char_template, scenario_pack)
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
        "world_state": {
            "scene_id": str(meta.get("initial_scene") or "start"),
            "location_id": _resolve_initial_location(scenario_pack, str(meta.get("initial_scene") or "start")),
        },
        "character": character,
        "messages": [],
        "system_logs": [],
        "event_log": [],
        "dice_log": [],
        "choices": [],
        "flags": {},
        "companion": None,
        "game_over": None,
        "last_action_result": {},
        "last_turn_narrated": False,
        "combat": None,
        "last_combat_result": {},
        "next_dice_type": "1d20",
        "next_dice_dc": 0,
        "needs_opening": True,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    ensure_combat_started(session)
    save_session(session)
    return public_session(session)


def _resolve_initial_location(pack: dict[str, Any], scene_id: str) -> str:
    scene = find_scene(pack, scene_id)
    if scene:
        loc_ids = [str(lid) for lid in (scene.get("location_ids") or []) if lid]
        if loc_ids:
            return loc_ids[0]
    return scene_id


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
    session = json.loads(path.read_text(encoding="utf-8"))
    ensure_world_state(session)
    session.setdefault("event_log", [])
    character = session.get("character") if isinstance(session.get("character"), dict) else {}
    inventory = character.get("inventory") if isinstance(character.get("inventory"), list) else []
    _merge_inventory_catalog(inventory, session.get("scenario_pack"))
    _normalize_character(character)
    return session


def save_session(session: dict[str, Any]) -> None:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    ensure_world_state(session)
    session["updated_at"] = utc_now()
    (SAVE_DIR / f"{session['id']}.json").write_text(
        json.dumps(session, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def public_session(session: dict[str, Any]) -> dict[str, Any]:
    world = ensure_world_state(session)
    combat = public_combat(session)
    public = deepcopy(session)
    public.pop("scenario_prompt", None)
    public.pop("scenario_pack", None)
    public.pop("last_intent_resolution", None)
    public.pop("deviation_state", None)
    public.pop("event_log", None)
    public["current_scene"] = world["scene_id"]
    public["current_location"] = world["location_id"]
    public["current_scene_title"] = scene_title(session)
    public["current_location_title"] = current_location_title(session)
    location = _current_location_record(session)
    if location:
        public["location_background_image"] = str(location.get("background_image") or "")
        public["location_portrait_image"] = str(location.get("portrait_image") or "")
    else:
        public["location_background_image"] = ""
        public["location_portrait_image"] = ""
    last_action_id = str((session.get("last_action_result") or {}).get("action_id") or "")
    action = next(
        (
            entry for entry in _iter_actions(current_actions_for_session(session))
            if str(entry.get("id") or entry.get("action_id") or "") == last_action_id
        ),
        None,
    )
    public["combat"] = combat
    public["enemies"] = deepcopy(combat.get("enemies") or []) if isinstance(combat, dict) else []
    public["in_combat"] = bool(isinstance(combat, dict) and combat.get("status"))
    combat_portrait = ""
    if public["in_combat"]:
        active_enemy = next(
            (
                enemy for enemy in public["enemies"]
                if isinstance(enemy, dict) and _safe_int(enemy.get("hp"), 0) > 0 and enemy.get("image")
            ),
            None,
        )
        combat_portrait = str((active_enemy or {}).get("image") or "")
    public["active_portrait_image"] = str(
        combat_portrait
        or (action or {}).get("portrait_image")
        or public["location_portrait_image"]
    )

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
    public["choices"] = annotate_choices_for_session(public.get("choices"), public)
    public["choices"] = annotate_choices_for_character(public.get("choices"), public.get("character", {}))
    public["system_logs"] = [
        log for log in public.get("system_logs", [])
        if log.get("source") == "engine"
        and not _is_protocol_warning_log(str(log.get("text", "")))
    ]
    return public


def _current_location_record(session: dict[str, Any]) -> Optional[dict[str, Any]]:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return None
    location_id = current_location_id(session)
    return next(
        (
            location for location in pack.get("locations", [])
            if isinstance(location, dict) and str(location.get("id") or "") == location_id
        ),
        None,
    )


def annotate_choices_for_session(raw_choices: Any, session: dict[str, Any]) -> list[dict[str, Any]]:
    flags = session.get("flags") if isinstance(session.get("flags"), dict) else {}
    choices: list[dict[str, Any]] = []
    for item in raw_choices if isinstance(raw_choices, list) else []:
        choice = {"text": str(item), "preview": "", "risk": ""} if isinstance(item, str) else deepcopy(item)
        if not isinstance(choice, dict):
            continue
        visible_flag = str(choice.get("visible_after") or "")
        if visible_flag and not flags.get(visible_flag):
            continue
        hidden_flag = str(choice.get("hidden_after") or "")
        if hidden_flag and flags.get(hidden_flag):
            continue
        disabled_flag = str(choice.get("disabled_after") or "")
        once_flag = str(choice.get("once") or "")
        if disabled_flag and flags.get(disabled_flag):
            choice["enabled"] = False
            choice["disabled_reason"] = str(choice.get("disabled_reason") or "完了済みです。")
        elif once_flag and flags.get(once_flag):
            choice["enabled"] = False
            choice["disabled_reason"] = str(choice.get("disabled_reason") or "完了済みです。")
        if "children" in choice and isinstance(choice["children"], list):
            choice["children"] = annotate_choices_for_session(choice["children"], session)
        choices.append(choice)
    return choices


def _current_scene_enemies(session: dict[str, Any]) -> list[dict[str, Any]]:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return []
    scene = find_scene(pack, current_scene_id(session))
    if not scene:
        return []

    enemy_ids = set(_as_text_list(scene.get("enemy_ids")))
    location_ids = _as_text_list(scene.get("location_ids"))
    for location in pack.get("locations", []):
        if not isinstance(location, dict) or str(location.get("id") or "") not in location_ids:
            continue
        enemy_ids.update(_as_text_list(location.get("enemy_ids")))

    enemies = []
    for enemy in pack.get("enemies", []):
        if isinstance(enemy, dict) and str(enemy.get("id") or "") in enemy_ids:
            enemies.append(deepcopy(enemy))
    return enemies


def add_player_message(session: dict[str, Any], text: str, speaker: str = "プレイヤー") -> None:
    session["messages"].append({"role": "user", "speaker": speaker, "text": text, "created_at": utc_now()})


def add_assistant_message(session: dict[str, Any], text: str, speaker: str = "GM") -> None:
    session["messages"].append({"role": "assistant", "speaker": speaker, "text": text, "created_at": utc_now()})
    session["last_turn_narrated"] = bool(str(text).strip())


def add_system_log(session: dict[str, Any], text: str) -> None:
    if text:
        session["system_logs"].append({"text": text, "source": "diagnostic", "created_at": utc_now()})


def record_state_event(
    session: dict[str, Any],
    kind: str,
    text: str,
    data: Optional[dict[str, Any]] = None,
    *,
    visible: bool = True,
) -> dict[str, Any]:
    event = {
        "id": uuid.uuid4().hex,
        "kind": str(kind),
        "text": str(text),
        "data": deepcopy(data) if isinstance(data, dict) else {},
        "source": "engine",
        "created_at": utc_now(),
    }
    events = session.setdefault("event_log", [])
    events.append(event)
    if len(events) > 240:
        session["event_log"] = events[-240:]
    if visible and text:
        session.setdefault("system_logs", []).append({
            "text": str(text),
            "source": "engine",
            "event_id": event["id"],
            "created_at": event["created_at"],
        })
    return event


def _is_protocol_warning_log(text: str) -> bool:
    return text in PROTOCOL_WARNING_LOGS


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _valid_client_roll(val: Any, sides: int) -> bool:
    try:
        n = int(val)
        return 1 <= n <= sides
    except (TypeError, ValueError):
        return False


def roll_dice(session: dict[str, Any], expression: str = "1d20", dc: Optional[int] = None, client_rolls: Optional[list[int]] = None) -> dict[str, Any]:
    expr = str(expression or "").strip() or "1d20"
    dice_part = expr
    attr_key = ""
    dice_match = _DICE_ATTR_RE.match(expr)
    if dice_match:
        dice_part = dice_match.group(1)
        attr_key = _canonical_attr_key(dice_match.group(2) or "")
    count, sides = _parse_dice_expression(dice_part)
    if client_rolls and isinstance(client_rolls, list) and len(client_rolls) == count and all(_valid_client_roll(r, sides) for r in client_rolls):
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
    entry["critical_success"] = bool(rolls and all(value == sides for value in rolls))
    entry["critical_failure"] = bool(rolls and all(value == 1 for value in rolls))
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

    payload = validate_model_payload_for_action(session, payload)

    if str(payload.get("system_log") or "").strip():
        add_system_log(session, "model system_log ignored: logs are derived from committed engine events.")

    dice_type = payload.get("dice_type")
    if isinstance(dice_type, str) and dice_type.strip():
        normalized_dice_type = dice_type.strip()
        if normalized_dice_type.lower() in {"null", "none", "no", "なし"}:
            session["next_dice_type"] = "1d20"
        else:
            session["next_dice_type"] = normalized_dice_type
    elif dice_type is None:
        session["next_dice_type"] = "1d20"
    dice_dc = payload.get("dice_dc")
    if isinstance(dice_dc, (int, float)):
        session["next_dice_dc"] = int(dice_dc)
    else:
        session["next_dice_dc"] = 0

    state_delta = payload.get("state_delta") or {}
    if not isinstance(state_delta, dict):
        add_system_log(session, "GM応答のstate_deltaが不正だったため無視しました。")
        return
    if _model_state_mutations_allowed(session):
        _infer_state_delta_from_text(gm_text, session, state_delta)
        apply_state_delta(session, sanitize_model_state_delta(session, state_delta))

    intent = session.get("last_intent_resolution") if isinstance(session.get("last_intent_resolution"), dict) else {}
    if intent.get("status") == "unmatched":
        session["choices"] = fallback_choices_for_session(session)
        return

    if current_actions_for_session(session):
        session["choices"] = fallback_choices_for_session(session)
        return

    raw_choices = payload.get("choices")
    if isinstance(raw_choices, list) and raw_choices:
        choices = _normalize_choices(raw_choices)
        if choices:
            _restore_choice_children_from_scenario(choices, session)
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
                choice: dict[str, Any] = {
                    "text": text,
                    "preview": str(item.get("preview", "")),
                    "risk": str(item.get("risk", "")),
                    **({"requirements": deepcopy(item["requirements"])} if "requirements" in item else {}),
                }
                children = item.get("children")
                if isinstance(children, list) and children:
                    normalized_children = _normalize_choices(children)
                    if normalized_children:
                        choice["children"] = normalized_children
                choices.append(choice)
    return choices[:5]


def _restore_choice_children_from_scenario(choices: list[dict[str, Any]], session: dict[str, Any]) -> None:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return
    scene = find_scene(pack, current_scene_id(session))
    if not isinstance(scene, dict):
        return
    fallback: list[Any] = scene.get("fallback_choices", [])
    if not isinstance(fallback, list) or not fallback:
        fallback = pack.get("fallback_choices", [])
    if not isinstance(fallback, list):
        return
    normalized_fallback = _normalize_choices(fallback)
    parent_map: dict[str, dict[str, Any]] = {}
    child_to_parent: dict[str, str] = {}
    for fc in normalized_fallback:
        if isinstance(fc, dict) and "children" in fc and isinstance(fc["children"], list):
            parent_map[fc["text"]] = fc
            for child in fc["children"]:
                if isinstance(child, dict):
                    child_to_parent[child.get("text", "")] = fc["text"]
    if not parent_map:
        return
    reconstructed: list[dict[str, Any]] = []
    used_parents: set[str] = set()
    for choice in choices:
        text = choice.get("text", "") if isinstance(choice, dict) else str(choice)
        if isinstance(choice, dict) and "children" in choice:
            reconstructed.append(choice)
            continue
        matched_parent = False
        for parent_text, parent_choice in parent_map.items():
            if parent_text in used_parents:
                continue
            if text == parent_text:
                reconstructed.append(deepcopy(parent_choice))
                used_parents.add(parent_text)
                matched_parent = True
                break
            if text in child_to_parent and child_to_parent[text] == parent_text:
                reconstructed.append(deepcopy(parent_choice))
                used_parents.add(parent_text)
                matched_parent = True
                break
        if not matched_parent and text not in child_to_parent:
            reconstructed.append(choice)
    if used_parents:
        choices[:] = reconstructed


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
        if "children" in choice and isinstance(choice["children"], list):
            choice["children"] = annotate_choices_for_character(choice["children"], character)
        choices.append(choice)
    return choices


def choice_requirement_status(choice: dict[str, Any], character: dict[str, Any]) -> tuple[bool, str]:
    if choice.get("enabled") is False:
        return False, str(choice.get("disabled_reason") or "この行動は現在選択できません。")
    requirements = choice.get("requirements")
    if requirements is None:
        requirements = _requirements_from_choice_text(choice)
    if not requirements:
        return True, ""

    attrs = character.get("attributes", {}) if isinstance(character.get("attributes"), dict) else {}
    if isinstance(requirements, list):
        passed = all(_requirement_passes(req, attrs, character) for req in requirements)
        return (True, "") if passed else (False, _requirement_reason(requirements, "all", character))
    if not isinstance(requirements, dict):
        return True, ""
    if isinstance(requirements.get("any"), list):
        reqs = requirements["any"]
        passed = any(_requirement_passes(req, attrs, character) for req in reqs)
        return (True, "") if passed else (False, _requirement_reason(reqs, "any", character))
    if isinstance(requirements.get("all"), list):
        reqs = requirements["all"]
        passed = all(_requirement_passes(req, attrs, character) for req in reqs)
        return (True, "") if passed else (False, _requirement_reason(reqs, "all", character))
    passed = _requirement_passes(requirements, attrs, character)
    return (True, "") if passed else (False, _requirement_reason([requirements], "all", character))


def resolve_player_intent(
    session: dict[str, Any],
    action_text: str = "",
    action_id: Optional[str] = None,
) -> dict[str, Any]:
    raw_actions = current_actions_for_session(session)
    if not raw_actions:
        return {
            "status": "legacy",
            "method": "legacy",
            "confidence": 0.0,
            "action_id": "",
            "candidate_action_ids": [],
            "scores": [],
            "action": None,
        }
    actions, groups = _intent_action_surfaces(session, raw_actions)
    wanted_id = str(action_id or "").strip()
    if wanted_id:
        matched_group = next((group for group in groups if str(group.get("id") or group.get("action_id") or "") == wanted_id), None)
        if matched_group:
            return _group_intent_resolution(matched_group, 1.0, "action_group_id")
    resolution = resolve_intent(actions, action_text, action_id)
    if resolution.get("status") == "resolved" or wanted_id or not groups:
        return resolution
    group_resolution = resolve_intent(groups, action_text)
    if group_resolution.get("status") == "resolved" and isinstance(group_resolution.get("action"), dict):
        group_confidence = float(group_resolution.get("confidence") or 0.0)
        if resolution.get("status") == "unmatched" or group_confidence >= float(resolution.get("confidence") or 0.0):
            return _group_intent_resolution(
                group_resolution["action"],
                group_confidence,
                "action_group",
            )
    if group_resolution.get("status") == "ambiguous":
        group_ids = set(group_resolution.get("candidate_action_ids", []))
        candidates = [group for group in groups if str(group.get("id") or "") in group_ids]
        child_ids = [
            str(child.get("id") or child.get("action_id") or "")
            for group in candidates
            for child in _iter_actions(group.get("children", []))
            if isinstance(child, dict) and not child.get("children") and str(child.get("id") or child.get("action_id") or "")
        ]
        resolution = deepcopy(group_resolution)
        resolution["candidate_action_ids"] = list(dict.fromkeys(child_ids))
        resolution["action"] = None
        return resolution
    return resolution


def _intent_action_surfaces(
    session: dict[str, Any],
    raw_actions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    flags = session.get("flags") if isinstance(session.get("flags"), dict) else {}
    executable: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []

    def visit(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        visible: list[dict[str, Any]] = []
        character = session.get("character", {}) if isinstance(session.get("character"), dict) else {}
        character_id = str(character.get("id") or character.get("character_id") or "")
        for action in actions:
            if not isinstance(action, dict):
                continue
            visible_after = str(action.get("visible_after") or "")
            if visible_after and not flags.get(visible_after):
                continue
            hidden_after = str(action.get("hidden_after") or "")
            if hidden_after and flags.get(hidden_after):
                continue
            visible_character = str(action.get("visible_for_character") or "")
            if visible_character and visible_character != character_id:
                continue
            children = action.get("children")
            if isinstance(children, list) and children:
                visible_children = visit(children)
                if visible_children:
                    group = deepcopy(action)
                    group["children"] = visible_children
                    groups.append(group)
                    visible.append(group)
            else:
                executable.append(action)
                visible.append(action)
        return visible

    visit(raw_actions)
    return executable, groups


def _group_intent_resolution(group: dict[str, Any], confidence: float, method: str) -> dict[str, Any]:
    child_ids = [
        str(action.get("id") or action.get("action_id") or "")
        for action in _iter_actions(group.get("children", []))
        if isinstance(action, dict) and not action.get("children") and str(action.get("id") or action.get("action_id") or "")
    ]
    return {
        "status": "ambiguous",
        "method": method,
        "confidence": round(confidence, 3),
        "action_id": "",
        "candidate_action_ids": list(dict.fromkeys(child_ids)),
        "scores": [{"action_id": str(group.get("id") or ""), "score": round(confidence, 3)}],
        "action": None,
    }


def resolve_action(session: dict[str, Any], action_text: str = "", action_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    resolution = resolve_player_intent(session, action_text, action_id)
    action = resolution.get("action")
    return deepcopy(action) if resolution.get("status") == "resolved" and isinstance(action, dict) else None


def track_intent_resolution(
    session: dict[str, Any],
    resolution: dict[str, Any],
    player_text: str,
) -> dict[str, Any]:
    status = str(resolution.get("status") or "unmatched")
    tracked = {
        "status": status,
        "method": str(resolution.get("method") or ""),
        "confidence": float(resolution.get("confidence") or 0.0),
        "action_id": str(resolution.get("action_id") or ""),
        "candidate_action_ids": [str(value) for value in resolution.get("candidate_action_ids", []) if str(value)],
        "scores": deepcopy(resolution.get("scores", [])),
        "player_text": str(player_text or "")[:240],
    }
    if status in {"resolved", "legacy"}:
        session.pop("deviation_state", None)
        tracked["phase"] = "on_track"
    elif status == "unmatched":
        previous = session.get("deviation_state") if isinstance(session.get("deviation_state"), dict) else {}
        previous_turns = int(previous.get("turns", 0) or 0)
        turns = min(FREEFORM_TURN_LIMIT, previous_turns + 1)
        phase = "blocked" if previous_turns >= FREEFORM_TURN_LIMIT else ("recovery" if turns >= FREEFORM_TURN_LIMIT else "improvise")
        deviation = {
            "turns": turns,
            "phase": phase,
            "last_player_text": tracked["player_text"],
            "candidate_action_ids": tracked["candidate_action_ids"],
        }
        session["deviation_state"] = deviation
        tracked.update(deviation)
    elif status == "ambiguous":
        tracked["phase"] = "clarify"
    else:
        tracked["phase"] = "rejected"
    session["last_intent_resolution"] = tracked
    return tracked


def intent_control_prompt(session: dict[str, Any]) -> str:
    resolution = session.get("last_intent_resolution")
    if not isinstance(resolution, dict) or resolution.get("status") != "unmatched":
        return ""
    phase = str(resolution.get("phase") or "improvise")
    turns = int(resolution.get("turns", 1) or 1)
    common = (
        "【自由入力制御】\n"
        f"現在の action surface には未解決です（{turns}/{FREEFORM_TURN_LIMIT}ターン）。\n"
        "この入力を新しい主線や確定事実として採用せず、現在地で起きる短く可逆的な反応だけを描写してください。\n"
        "場面、場所、フラグ、所持品、数値は変更せず、現在の available_actions へ自然に戻してください。\n"
        "choices はゲームエンジンが確定するため、新規選択肢を作らないでください。"
    )
    if phase == "recovery":
        return common + "\nこれが即興の最終ターンです。今回で必ず収束させ、available_actions のいずれかを選べる状態に戻してください。"
    return common


def action_requirement_status(action: dict[str, Any], session: dict[str, Any]) -> tuple[bool, str]:
    flags = session.get("flags") if isinstance(session.get("flags"), dict) else {}
    visible_flag = str(action.get("visible_after") or "")
    if visible_flag and not flags.get(visible_flag):
        return False, "この行動はまだ選択できません。"
    disabled_flag = str(action.get("disabled_after") or "")
    once_flag = str(action.get("once") or "")
    if disabled_flag and flags.get(disabled_flag):
        return False, "完了済みです。"
    if once_flag and flags.get(once_flag):
        return False, "完了済みです。"
    return choice_requirement_status(action, session.get("character", {}))


def action_dice_settings(action: Optional[dict[str, Any]], default_type: str = "1d20", default_dc: int = 0) -> tuple[str, int]:
    if not isinstance(action, dict):
        return default_type, max(int(default_dc or 0), 0)
    roll = action.get("roll") if isinstance(action.get("roll"), dict) else {}
    dice_type = str(roll.get("dice_type") or roll.get("dice") or action.get("dice_type") or default_type or "1d20")
    dice_dc = roll.get("dc", roll.get("dice_dc", action.get("dice_dc", default_dc)))
    try:
        normalized_dc = int(dice_dc or 0)
    except (TypeError, ValueError):
        normalized_dc = 0
    return dice_type, max(normalized_dc, 0)


def apply_action_result(session: dict[str, Any], action: dict[str, Any], latest_roll: dict[str, Any]) -> dict[str, Any]:
    outcome = _action_outcome(latest_roll, action.get("critical_enabled") is not False)
    base_effects = _as_list(action.get("effects"))
    branch_outcome = {
        "critical_success": "success",
        "critical_failure": "failure",
    }.get(outcome, outcome)
    replaces_branch = branch_outcome != outcome and action.get(f"{outcome}_replaces_branch") is True
    outcome_effects = [] if replaces_branch else _as_list(action.get(f"{branch_outcome}_effects"))
    if branch_outcome != outcome:
        outcome_effects.extend(_as_list(action.get(f"{outcome}_effects")))
    delta = _effects_to_state_delta([*base_effects, *outcome_effects], session)
    flags = session.setdefault("flags", {})
    if isinstance(flags, dict):
        if action.get("once"):
            flag = str(action["once"])
            if not flags.get(flag):
                flags[flag] = True
                record_state_event(session, "flag_set", "", {"flag": flag, "value": True}, visible=False)
    apply_state_delta(session, delta, allow_world_transition=True)
    if delta.get("start_combat") is True:
        session["combat_start_requested"] = True
    result = {
        "action_id": str(action.get("id") or action.get("action_id") or ""),
        "text": str(action.get("text") or ""),
        "outcome": outcome,
        "roll": latest_roll,
        "state_delta": delta,
        "prepared_turn_id": str(action.get("prepared_turn_id") or ""),
    }
    record_state_event(
        session,
        "action_resolved",
        "",
        {
            "action_id": result["action_id"],
            "text": result["text"],
            "outcome": result["outcome"],
            "roll": deepcopy(latest_roll),
        },
        visible=False,
    )
    session["last_action_result"] = result
    session["choices"] = fallback_choices_for_session(session)
    return result


def validate_model_payload_for_action(session: dict[str, Any], payload: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not isinstance(payload, dict):
        return payload
    action_result = session.get("last_action_result") if isinstance(session.get("last_action_result"), dict) else {}
    if not action_result.get("action_id"):
        intent = session.get("last_intent_resolution") if isinstance(session.get("last_intent_resolution"), dict) else {}
        if intent.get("status") != "unmatched":
            return payload
        sanitized = deepcopy(payload)
        if isinstance(sanitized.get("state_delta"), dict) and sanitized["state_delta"]:
            add_system_log(session, "model state_delta ignored: unresolved free input cannot mutate game state.")
        sanitized["state_delta"] = {}
        if "choices" in sanitized:
            add_system_log(session, "model choices ignored: unresolved free input uses the current action surface.")
        sanitized["choices"] = fallback_choices_for_session(session)
        return sanitized
    sanitized = deepcopy(payload)
    if isinstance(sanitized.get("state_delta"), dict) and sanitized["state_delta"]:
        add_system_log(session, "model state_delta ignored: action engine already applied the resolved action.")
    sanitized["state_delta"] = {}
    if "choices" in sanitized:
        add_system_log(session, "model choices ignored: action engine rebuilt choices from current action surface.")
        sanitized["choices"] = []
    return sanitized


def _model_state_mutations_allowed(session: dict[str, Any]) -> bool:
    action_result = session.get("last_action_result") if isinstance(session.get("last_action_result"), dict) else {}
    if action_result.get("action_id"):
        return False
    intent = session.get("last_intent_resolution") if isinstance(session.get("last_intent_resolution"), dict) else {}
    return intent.get("status") != "unmatched"


def sanitize_model_state_delta(session: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """Allow only bounded, scenario-known model mutations outside resolved actions."""
    sanitized: dict[str, Any] = {}
    rejected: list[str] = []

    for key in MODEL_RESOURCE_DELTA_KEYS:
        if key not in delta:
            continue
        value = _strict_int(delta.get(key))
        if value is None or not _model_resource_delta_allowed(session, key, value):
            rejected.append(key)
            continue
        if value:
            sanitized[key] = value

    attr_changes = delta.get("attribute_changes")
    if attr_changes is not None:
        normalized_attrs, rejected_attrs = _validated_attribute_changes(
            session,
            attr_changes,
            max_abs=MODEL_MAX_ATTRIBUTE_DELTA,
        )
        if normalized_attrs:
            sanitized["attribute_changes"] = normalized_attrs
        rejected.extend(f"attribute_changes.{key}" for key in rejected_attrs)

    for key in ("inventory_add", "inventory_remove"):
        if key not in delta:
            continue
        items, rejected_items = _validated_model_items(session, delta.get(key), removing=(key == "inventory_remove"))
        if items:
            sanitized[key] = items
        rejected.extend(f"{key}.{name}" for name in rejected_items)

    world_keys = [key for key in ("current_scene", "current_location") if delta.get(key)]
    if world_keys:
        add_system_log(session, "model world transition ignored: only the action engine may change position.")

    supported = {*MODEL_RESOURCE_DELTA_KEYS, "attribute_changes", "inventory_add", "inventory_remove", "current_scene", "current_location"}
    rejected.extend(str(key) for key in delta if key not in supported)
    if rejected:
        unique = list(dict.fromkeys(rejected))
        add_system_log(session, "model state_delta rejected: " + ", ".join(unique))
    return sanitized


def _model_resource_delta_allowed(session: dict[str, Any], key: str, value: int) -> bool:
    if key == "gold_change":
        return abs(value) <= MODEL_MAX_GOLD_DELTA
    stat = key.removesuffix("_change")
    character = session.get("character") if isinstance(session.get("character"), dict) else {}
    maximum = _strict_int(character.get(f"max_{stat}"))
    return maximum is not None and maximum > 0 and abs(value) <= maximum


def _validated_attribute_changes(
    session: dict[str, Any],
    raw_changes: Any,
    *,
    max_abs: Optional[int] = None,
) -> tuple[dict[str, int], list[str]]:
    if not isinstance(raw_changes, dict):
        return {}, ["invalid"] if raw_changes is not None else []
    allowed = _allowed_attribute_keys(session)
    normalized: dict[str, int] = {}
    rejected: list[str] = []
    for raw_key, raw_value in raw_changes.items():
        key = _canonical_attr_key(str(raw_key))
        value = _strict_int(raw_value)
        if not key or key not in allowed or value is None or (max_abs is not None and abs(value) > max_abs):
            rejected.append(str(raw_key))
            continue
        if value:
            combined = normalized.get(key, 0) + value
            if max_abs is not None and abs(combined) > max_abs:
                rejected.append(str(raw_key))
                continue
            normalized[key] = combined
    return normalized, rejected


def _allowed_attribute_keys(session: dict[str, Any]) -> set[str]:
    character = session.get("character") if isinstance(session.get("character"), dict) else {}
    attrs = character.get("attributes") if isinstance(character.get("attributes"), dict) else {}
    keys = {_canonical_attr_key(str(key)) for key in attrs if str(key).strip()}
    if keys:
        return keys
    pack = session.get("scenario_pack") if isinstance(session.get("scenario_pack"), dict) else {}
    return {
        _canonical_attr_key(str(item.get("id") or ""))
        for item in pack.get("attribute_defs", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }


def _validated_model_items(session: dict[str, Any], raw_items: Any, *, removing: bool) -> tuple[list[dict[str, Any]], list[str]]:
    catalog = _model_item_catalog(session, include_owned=True)
    validated: list[dict[str, Any]] = []
    rejected: list[str] = []
    for raw in _as_list(raw_items):
        item = raw if isinstance(raw, dict) else {"name": raw}
        requested_id = str(item.get("id") or "").strip()
        requested_name = _item_name_from_dict(item)
        source = catalog.get(requested_id) if requested_id else None
        if source is None and requested_name:
            source = catalog.get(requested_name)
        label = requested_id or requested_name or "invalid"
        quantity = _strict_int(item.get("quantity", 1))
        if source is None or quantity is None or quantity < 1 or quantity > MODEL_MAX_ITEM_QUANTITY:
            rejected.append(label)
            continue
        if removing:
            validated.append({"name": str(source.get("name") or source.get("title") or label), "quantity": quantity})
            continue
        normalized = _enrich_item(source)
        normalized["name"] = str(source.get("name") or source.get("title") or label)
        normalized["quantity"] = quantity
        validated.append(normalized)
    return validated, rejected


def _model_item_catalog(session: dict[str, Any], *, include_owned: bool) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}

    def register(raw: Any) -> None:
        item = raw if isinstance(raw, dict) else {"name": str(raw)}
        name = str(item.get("name") or item.get("title") or "").strip()
        item_id = str(item.get("id") or "").strip()
        if not name and not item_id:
            return
        canonical = deepcopy(item)
        canonical["name"] = name or item_id
        if name:
            catalog[name] = canonical
        if item_id:
            catalog[item_id] = canonical

    pack = session.get("scenario_pack") if isinstance(session.get("scenario_pack"), dict) else {}
    for item in pack.get("items", []):
        register(item)
    for name, details in DEFAULT_ITEM_CATALOG.items():
        register({"name": name, **details})
    if include_owned:
        character = session.get("character") if isinstance(session.get("character"), dict) else {}
        for item in character.get("inventory", []):
            register(item)
    return catalog


def _strict_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
        return None
    return int(value)


def _iter_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        result.append(action)
        if isinstance(action.get("children"), list):
            result.extend(_iter_actions(action["children"]))
    return result


def _action_outcome(latest_roll: dict[str, Any], allow_critical: bool = True) -> str:
    dc = latest_roll.get("dc")
    if isinstance(dc, (int, float)) and int(dc) > 0:
        if allow_critical and latest_roll.get("critical_success"):
            return "critical_success"
        if allow_critical and latest_roll.get("critical_failure"):
            return "critical_failure"
        return "success" if bool(latest_roll.get("success")) else "failure"
    return "neutral"


def _effects_to_state_delta(effects: list[Any], session: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    effects = _expand_conditional_effects(effects, session)
    delta: dict[str, Any] = {"attribute_changes": {}}
    inventory_add: list[Any] = []
    inventory_remove: list[Any] = []
    flags_set: list[str] = []
    flags_unset: list[str] = []
    for effect in effects:
        if not isinstance(effect, dict):
            continue
        if isinstance(effect.get("gold_change"), (int, float)):
            delta["gold_change"] = int(delta.get("gold_change", 0)) + int(effect["gold_change"])
        if isinstance(effect.get("gold"), (int, float)):
            delta["gold"] = int(effect["gold"])
        for stat in ("hp", "mp", "sp"):
            if isinstance(effect.get(f"{stat}_change"), (int, float)):
                delta[f"{stat}_change"] = int(delta.get(f"{stat}_change", 0)) + int(effect[f"{stat}_change"])
        if effect.get("add_item") is not None:
            inventory_add.append(effect["add_item"])
        if effect.get("inventory_add") is not None:
            inventory_add.extend(_as_list(effect["inventory_add"]))
        if effect.get("remove_item") is not None:
            inventory_remove.append(effect["remove_item"])
        if effect.get("inventory_remove") is not None:
            inventory_remove.extend(_as_list(effect["inventory_remove"]))
        if isinstance(effect.get("current_scene"), str):
            delta["current_scene"] = effect["current_scene"]
        if isinstance(effect.get("next_scene"), str):
            delta["current_scene"] = effect["next_scene"]
        if isinstance(effect.get("current_location"), str):
            delta["current_location"] = effect["current_location"]
        if isinstance(effect.get("next_location"), str):
            delta["current_location"] = effect["next_location"]
        for image_key in ("background_image", "character_image"):
            if isinstance(effect.get(image_key), str):
                delta[image_key] = effect[image_key]
        if effect.get("start_combat") is True:
            delta["start_combat"] = True
        if isinstance(effect.get("set_companion"), (str, dict)):
            delta["set_companion"] = deepcopy(effect["set_companion"])
        if effect.get("clear_companion") is True:
            delta["clear_companion"] = True
        if isinstance(effect.get("attribute_set"), dict):
            delta.setdefault("attribute_set", {}).update(deepcopy(effect["attribute_set"]))
        if effect.get("clear_skills") is True:
            delta["clear_skills"] = True
        if isinstance(effect.get("equip_item"), str):
            delta["equip_item"] = effect["equip_item"]
        if isinstance(effect.get("game_over"), (str, dict)):
            delta["game_over"] = deepcopy(effect["game_over"])
        if effect.get("restore_full") is True:
            delta["restore_full"] = True
        if isinstance(effect.get("set_flag"), str):
            flags_set.append(effect["set_flag"])
        if isinstance(effect.get("unset_flag"), str):
            flags_unset.append(effect["unset_flag"])
        if isinstance(effect.get("attribute_changes"), dict):
            for key, value in effect["attribute_changes"].items():
                if isinstance(value, (int, float)):
                    delta["attribute_changes"][key] = int(delta["attribute_changes"].get(key, 0)) + int(value)
    if inventory_add:
        delta["inventory_add"] = inventory_add
    if inventory_remove:
        delta["inventory_remove"] = inventory_remove
    if flags_set:
        delta["flags_set"] = flags_set
    if flags_unset:
        delta["flags_unset"] = flags_unset
    if not delta["attribute_changes"]:
        delta.pop("attribute_changes", None)
    return delta


def _expand_conditional_effects(effects: list[Any], session: Optional[dict[str, Any]]) -> list[Any]:
    expanded: list[Any] = []
    for effect in effects:
        if not isinstance(effect, dict) or not isinstance(effect.get("branch"), dict):
            expanded.append(effect)
            continue
        branch = effect["branch"]
        requirements = branch.get("requirements")
        passed = _session_requirement_passes(requirements, session)
        selected = branch.get("then" if passed else "else")
        expanded.extend(_expand_conditional_effects(_as_list(selected), session))
    return expanded


def _session_requirement_passes(requirement: Any, session: Optional[dict[str, Any]]) -> bool:
    if not isinstance(requirement, dict):
        return True
    if isinstance(requirement.get("any"), list):
        return any(_session_requirement_passes(item, session) for item in requirement["any"])
    if isinstance(requirement.get("all"), list):
        return all(_session_requirement_passes(item, session) for item in requirement["all"])
    flags = session.get("flags", {}) if isinstance(session, dict) and isinstance(session.get("flags"), dict) else {}
    if isinstance(requirement.get("flag"), str):
        return bool(flags.get(requirement["flag"]))
    if isinstance(requirement.get("not_flag"), str):
        return not bool(flags.get(requirement["not_flag"]))
    if isinstance(requirement.get("companion_id"), str):
        companion = session.get("companion", {}) if isinstance(session, dict) and isinstance(session.get("companion"), dict) else {}
        return str(companion.get("id") or "") == str(requirement["companion_id"])
    character = session.get("character", {}) if isinstance(session, dict) and isinstance(session.get("character"), dict) else {}
    attrs = character.get("attributes", {}) if isinstance(character.get("attributes"), dict) else {}
    return _requirement_passes(requirement, attrs, character)


def _requirements_from_choice_text(choice: dict[str, Any]) -> dict[str, Any]:
    source = " ".join(
        str(choice.get(key) or "")
        for key in ("text", "preview", "risk")
    )
    explicit = _requirements_from_risk(source)
    purchase_requirements = _purchase_requirements_from_text(source)
    if explicit and purchase_requirements:
        if isinstance(explicit.get("all"), list):
            return {"all": [*explicit["all"], *purchase_requirements]}
        return {"all": [explicit, *purchase_requirements]}
    if purchase_requirements:
        return {"all": purchase_requirements} if len(purchase_requirements) > 1 else purchase_requirements[0]
    return explicit


def _purchase_requirements_from_text(text: str) -> list[dict[str, Any]]:
    if not any(token in text for token in ("買う", "購入")):
        return []
    requirements: list[dict[str, Any]] = []
    gold_match = re.search(r"(\d+)\s*(?:G|g|ゴールド|gold)", text, re.IGNORECASE)
    if gold_match:
        requirements.append({"gold_gte": int(gold_match.group(1))})
    item_match = re.search(r"(.+?)を(?:買う|購入)", text)
    if item_match:
        item_name = item_match.group(1).split("で")[-1].strip(" 　「」『』（）()")
        if item_name:
            requirements.append({"lacks_item": item_name})
    return requirements


def _requirements_from_risk(risk: str) -> dict[str, Any]:
    if not risk:
        return {}
    char_req = _character_id_from_risk(risk)
    threshold_match = re.search(r"(\d+)\s*(?:以上|or higher|以上で)", risk, re.IGNORECASE)
    if not threshold_match:
        return char_req
    threshold = int(threshold_match.group(1))
    attr_keys = _attribute_keys_from_text(risk)
    if not attr_keys:
        return char_req
    attr_req: dict[str, Any]
    if "または" in risk or "or" in risk.lower() or "/" in risk:
        attr_req = {"any": [{"attribute": key, "gte": threshold} for key in attr_keys]}
    else:
        attr_req = {"all": [{"attribute": key, "gte": threshold} for key in attr_keys]}
    if char_req:
        return {"all": [char_req, attr_req]}
    return attr_req


def _character_id_from_risk(risk: str) -> dict[str, Any]:
    char_map = {
        "勇者": "hero",
        "僧侶": "cleric",
        "魔法使い": "mage",
        "盗賊": "thief",
    }
    for name, char_id in char_map.items():
        if name in risk and ("のみ" in risk or "必要" in risk):
            return {"character_id": char_id}
    return {}


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


def _requirement_passes(requirement: Any, attrs: dict[str, Any], character: dict[str, Any]) -> bool:
    if not isinstance(requirement, dict):
        return True
    if isinstance(requirement.get("any"), list):
        return any(_requirement_passes(req, attrs, character) for req in requirement["any"])
    if isinstance(requirement.get("all"), list):
        return all(_requirement_passes(req, attrs, character) for req in requirement["all"])
    if "character_id" in requirement:
        char_id = str(character.get("id") or character.get("character_id") or "")
        if str(requirement["character_id"]) != char_id:
            return False
        return True
    min_gold = requirement.get("gold_gte", requirement.get("min_gold"))
    if isinstance(min_gold, (int, float)):
        return int(character.get("gold", 0)) >= int(min_gold)
    max_gold = requirement.get("gold_lte", requirement.get("max_gold"))
    if isinstance(max_gold, (int, float)):
        return int(character.get("gold", 0)) <= int(max_gold)
    has_item = _requirement_item_name(requirement, ("has_item", "inventory_has", "requires_item"))
    if has_item:
        return has_item in _inventory_item_names(character)
    lacks_item = _requirement_item_name(requirement, ("lacks_item", "not_item", "missing_item"))
    if lacks_item:
        return lacks_item not in _inventory_item_names(character)
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


def _requirement_reason(requirements: list[Any], mode: str, character: dict[str, Any]) -> str:
    labels = [_requirement_label(req) for req in requirements if isinstance(req, dict)]
    labels = [label for label in labels if label]
    if not labels:
        return "条件を満たしていません"
    joiner = "または" if mode == "any" else "と"
    return f"{joiner.join(labels)}が必要"


def _requirement_label(requirement: dict[str, Any]) -> str:
    if isinstance(requirement.get("any"), list):
        labels = [_requirement_label(req) for req in requirement["any"] if isinstance(req, dict)]
        labels = [label for label in labels if label]
        if not labels:
            return ""
        joined = "または".join(labels)
        return f"({joined})" if len(labels) > 1 else joined
    if isinstance(requirement.get("all"), list):
        labels = [_requirement_label(req) for req in requirement["all"] if isinstance(req, dict)]
        labels = [label for label in labels if label]
        if not labels:
            return ""
        return "と".join(labels)
    if "character_id" in requirement:
        char_id = str(requirement["character_id"])
        char_names = {"hero": "勇者のみ", "cleric": "僧侶のみ", "mage": "魔法使いのみ", "thief": "盗賊のみ"}
        return char_names.get(char_id, f"キャラクター({char_id})のみ")
    min_gold = requirement.get("gold_gte", requirement.get("min_gold"))
    if isinstance(min_gold, (int, float)):
        return f"{int(min_gold)}ゴールド以上"
    max_gold = requirement.get("gold_lte", requirement.get("max_gold"))
    if isinstance(max_gold, (int, float)):
        return f"{int(max_gold)}ゴールド以下"
    has_item = _requirement_item_name(requirement, ("has_item", "inventory_has", "requires_item"))
    if has_item:
        return f"{has_item}所持"
    lacks_item = _requirement_item_name(requirement, ("lacks_item", "not_item", "missing_item"))
    if lacks_item:
        return f"{lacks_item}未所持"
    attr_key = _canonical_attr_key(str(requirement.get("attribute") or requirement.get("attr") or ""))
    if not attr_key:
        return ""
    label_map = {"str": "筋力", "dex": "敏捷", "int": "知力", "wis": "判断", "end": "耐久", "cha": "魅力"}
    threshold = requirement.get("gte", requirement.get("min", requirement.get("gt", "")))
    suffix = f"{int(threshold)}以上" if isinstance(threshold, (int, float)) else ""
    return f"{label_map.get(attr_key, attr_key)}{suffix}"


def _requirement_item_name(requirement: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = requirement.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _inventory_item_names(character: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    inventory = character.get("inventory")
    if not isinstance(inventory, list):
        return names
    for item in inventory:
        if isinstance(item, dict):
            if int(item.get("quantity", 1) or 0) <= 0:
                continue
            name = str(item.get("name") or "").strip()
        else:
            name = str(item or "").strip()
        if name:
            names.add(name)
    return names


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
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                continue
    return 0


def _fallback_choices_after_model_failure(session: dict[str, Any], current_dice_dc: Any = None) -> list[dict[str, Any]]:
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


def apply_state_delta(
    session: dict[str, Any],
    delta: dict[str, Any],
    *,
    allow_world_transition: bool = False,
) -> None:
    character = session["character"]
    if delta.get("restore_full") is True:
        for stat in ("hp", "mp", "sp"):
            character[stat] = int(character.get(f"max_{stat}", character.get(stat, 0)))
        record_state_event(session, "resources_restored", "HP・MP・SPが全回復しました。", {})
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
            record_state_event(
                session,
                "resource_changed",
                f"{stat.upper()}が{actual_change}回復しました。",
                {"resource": stat, "before": before, "after": int(character[stat]), "change": actual_change},
            )
        elif actual_change < 0:
            record_state_event(
                session,
                "resource_changed",
                f"{stat.upper()}が{abs(actual_change)}減少しました。",
                {"resource": stat, "before": before, "after": int(character[stat]), "change": actual_change},
            )

    if isinstance(delta.get("gold_change"), (int, float)):
        before = int(character.get("gold", 0))
        character["gold"] = max(0, before + int(delta["gold_change"]))
        actual_change = int(character["gold"]) - before
        if actual_change > 0:
            record_state_event(
                session,
                "gold_changed",
                f"{actual_change}ゴールドを獲得しました。",
                {"before": before, "after": int(character["gold"]), "change": actual_change},
            )
        elif actual_change < 0:
            record_state_event(
                session,
                "gold_changed",
                f"{abs(actual_change)}ゴールドを消費しました。",
                {"before": before, "after": int(character["gold"]), "change": actual_change},
            )
    if isinstance(delta.get("gold"), (int, float)):
        before = int(character.get("gold", 0))
        character["gold"] = max(0, int(delta["gold"]))
        if int(character["gold"]) != before:
            record_state_event(
                session,
                "gold_changed",
                f"所持金が{int(character['gold'])}ゴールドになりました。",
                {"before": before, "after": int(character["gold"]), "change": int(character["gold"]) - before},
            )

    flags = session.setdefault("flags", {})
    if isinstance(flags, dict):
        for flag in _as_text_list(delta.get("flags_set")):
            if not flags.get(flag):
                flags[flag] = True
                record_state_event(session, "flag_set", "", {"flag": flag, "value": True}, visible=False)
        for flag in _as_text_list(delta.get("flags_unset")):
            if flag in flags:
                flags.pop(flag, None)
                record_state_event(session, "flag_unset", "", {"flag": flag, "value": False}, visible=False)

    if delta.get("clear_companion") is True:
        _set_companion(session, None)
    elif isinstance(delta.get("set_companion"), (str, dict)):
        _set_companion(session, delta["set_companion"])

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
            enriched = _enrich_item(item if isinstance(item, dict) else {"name": item}, session.get("scenario_pack"))
            enriched["quantity"] = add_qty
            character["inventory"].append(enriched)
        record_state_event(
            session,
            "item_added",
            f"{item_name} x{add_qty}を入手しました。",
            {"item": item_name, "quantity": add_qty},
        )

    for item in _as_item_list(delta.get("inventory_remove")):
        item_name = str(item["name"]).strip()
        remaining = _safe_quantity(item.get("quantity"), 1)
        removed_qty = 0
        new_inv = []
        for existing in character["inventory"]:
            ename = existing.get("name") if isinstance(existing, dict) else existing
            if ename == item_name and remaining > 0:
                existing_spec = item_combat_spec(existing) if isinstance(existing, dict) else {}
                if isinstance(existing, dict) and (existing.get("non_removable") is True or existing_spec.get("non_removable") is True):
                    new_inv.append(existing)
                    continue
                existing_qty = int(existing.get("quantity", 1)) if isinstance(existing, dict) else 1
                remove_qty = min(existing_qty, remaining)
                remaining -= remove_qty
                removed_qty += remove_qty
                if isinstance(existing, dict) and existing_qty > remove_qty:
                    existing["quantity"] = existing_qty - remove_qty
                    new_inv.append(existing)
            else:
                new_inv.append(existing)
        character["inventory"] = new_inv
        if removed_qty:
            record_state_event(
                session,
                "item_removed",
                f"{item_name} x{removed_qty}を失いました。",
                {"item": item_name, "quantity": removed_qty},
            )

    _synchronize_equipment(character)
    equip_item = str(delta.get("equip_item") or "").strip()
    if equip_item:
        _equip_inventory_item(character, equip_item)

    if delta.get("clear_skills") is True:
        removed_skills = len(character.get("skills") or [])
        character["skills"] = []
        record_state_event(
            session,
            "skills_cleared",
            "すべての技能を失いました。",
            {"removed": removed_skills},
        )

    for image_key in ("background_image", "character_image"):
        if isinstance(delta.get(image_key), str):
            character[image_key] = delta[image_key]

    attr_changes = delta.get("attribute_changes")
    if isinstance(attr_changes, dict):
        attrs = character.setdefault("attributes", {})
        validated_attrs, rejected_attrs = _validated_attribute_changes(session, attr_changes)
        if rejected_attrs:
            add_system_log(session, "state_delta attribute rejected: " + ", ".join(rejected_attrs))
        for attr_key, attr_change in validated_attrs.items():
            before = int(attrs.get(attr_key, 0))
            attrs[attr_key] = before + attr_change
            actual_change = int(attrs[attr_key]) - before
            if actual_change > 0:
                record_state_event(
                    session,
                    "attribute_changed",
                    f"{attr_key}が{actual_change}上昇しました。",
                    {"attribute": attr_key, "before": before, "after": int(attrs[attr_key]), "change": actual_change},
                )
            elif actual_change < 0:
                record_state_event(
                    session,
                    "attribute_changed",
                    f"{attr_key}が{abs(actual_change)}減少しました。",
                    {"attribute": attr_key, "before": before, "after": int(attrs[attr_key]), "change": actual_change},
                )

    attr_set = delta.get("attribute_set")
    if isinstance(attr_set, dict):
        attrs = character.setdefault("attributes", {})
        for raw_key, raw_value in attr_set.items():
            key = _canonical_attr_key(str(raw_key))
            value = _strict_int(raw_value)
            if not key or value is None:
                continue
            before = int(attrs.get(key, 0))
            attrs[key] = value
            record_state_event(
                session,
                "attribute_changed",
                f"{key}が{value}になりました。",
                {"attribute": key, "before": before, "after": value, "change": value - before},
            )

    if isinstance(delta.get("game_over"), (str, dict)):
        raw_game_over = delta["game_over"]
        game_over = deepcopy(raw_game_over) if isinstance(raw_game_over, dict) else {"reason": str(raw_game_over)}
        game_over.setdefault("reason", "物語はここで終わりました。")
        game_over.setdefault("created_at", utc_now())
        session["game_over"] = game_over
        session["choices"] = []
        record_state_event(session, "game_over", str(game_over["reason"]), game_over)

    requested_scene = str(delta.get("current_scene") or "").strip()
    requested_location = str(delta.get("current_location") or "").strip()
    if requested_scene or requested_location:
        if not allow_world_transition:
            add_system_log(session, "model world transition ignored: only the action engine may change position.")
        else:
            before_position = deepcopy(ensure_world_state(session))
            accepted, reason = commit_world_position(
                session,
                scene_id=requested_scene or None,
                location_id=requested_location or None,
            )
            if not accepted:
                add_system_log(session, f"world transition rejected: {reason}")
            else:
                after_position = deepcopy(ensure_world_state(session))
                if after_position != before_position:
                    record_state_event(
                        session,
                        "position_changed",
                        f"現在地が{current_location_title(session)}になりました。",
                        {"before": before_position, "after": after_position},
                    )


def _set_companion(session: dict[str, Any], raw_companion: Any) -> None:
    previous = session.get("companion") if isinstance(session.get("companion"), dict) else None
    companion: Optional[dict[str, Any]] = None
    if isinstance(raw_companion, dict):
        companion = deepcopy(raw_companion)
    elif isinstance(raw_companion, str) and raw_companion.strip():
        companion_id = raw_companion.strip()
        pack = session.get("scenario_pack") if isinstance(session.get("scenario_pack"), dict) else {}
        companion = next(
            (
                deepcopy(candidate)
                for candidate in pack.get("companions", [])
                if isinstance(candidate, dict) and str(candidate.get("id") or "") == companion_id
            ),
            None,
        )
        if companion is None:
            companion = {"id": companion_id, "name": companion_id}

    previous_id = str(previous.get("id") or "") if previous else ""
    companion_id = str(companion.get("id") or "") if companion else ""
    if previous and previous_id != companion_id:
        previous_name = str(previous.get("name") or previous_id)
        record_state_event(
            session,
            "companion_left",
            f"{previous_name}がパーティーから離脱しました。",
            {"companion_id": previous_id, "name": previous_name},
        )
    session["companion"] = companion
    if companion and previous_id != companion_id:
        companion_name = str(companion.get("name") or companion_id)
        record_state_event(
            session,
            "companion_joined",
            f"{companion_name}がパーティーに加入しました。",
            {"companion_id": companion_id, "name": companion_name},
        )


def _equip_inventory_item(character: dict[str, Any], item_name_or_id: str) -> None:
    inventory = character.get("inventory") if isinstance(character.get("inventory"), list) else []
    target = next(
        (
            item for item in inventory
            if isinstance(item, dict)
            and item_name_or_id in {str(item.get("name") or ""), str(item.get("id") or "")}
        ),
        None,
    )
    if not target:
        return
    target_name = str(target.get("name") or target.get("id") or "").strip()
    equipment = _as_text_list(character.get("equipment"))
    target_kind = str(item_combat_spec(target).get("kind") or "").lower()
    if target_kind == "weapon":
        weapon_names = {
            str(item.get("name") or item.get("id") or "")
            for item in inventory
            if isinstance(item, dict) and str(item_combat_spec(item).get("kind") or "").lower() == "weapon"
        }
        equipment = [name for name in equipment if name not in weapon_names]
    if target_name and target_name not in equipment:
        equipment.append(target_name)
    character["equipment"] = equipment
    _synchronize_equipment(character)


def _enrich_item(item: dict[str, Any], scenario_pack: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    name = _item_name_from_dict(item) or "不明"
    catalog_entry: dict[str, Any] = deepcopy(DEFAULT_ITEM_CATALOG.get(name, {}))
    if isinstance(scenario_pack, dict):
        scenario_item = next(
            (
                candidate for candidate in scenario_pack.get("items", [])
                if isinstance(candidate, dict)
                and (
                    str(candidate.get("name") or candidate.get("title") or "") == name
                    or (item.get("id") and str(candidate.get("id") or "") == str(item.get("id")))
                )
            ),
            None,
        )
        if scenario_item:
            catalog_entry.update(deepcopy(scenario_item))
    merged = deepcopy(catalog_entry)
    merged.update(item)
    enriched: dict[str, Any] = {
        "name": name,
        "description": str(merged.get("description") or ""),
        "effect": structured_item_effect(merged),
        "quantity": _safe_quantity(item.get("quantity"), 1),
    }
    for key in ("id", "icon", "combat"):
        if key in merged:
            enriched[key] = deepcopy(merged[key])
    return enriched


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
    action_result = session.get("last_action_result")
    if isinstance(action_result, dict) and action_result.get("action_id"):
        messages.append({"role": "system", "content": "resolved_action_result:\n" + json.dumps(action_result, ensure_ascii=False)})
        messages.append({
            "role": "system",
            "content": (
                "【解決済みアクションの出力制約】\n"
                "state_delta は空オブジェクト、choices は空配列にしてください。状態と選択肢はエンジンが確定済みです。\n"
                "available_actions に存在しない取引、報酬、アイテム、追加行動を約束または確定しないでください。\n"
                "未登録の取引を提案せず、resolved_action_result と available_actions に沿った結果だけを描写してください。"
            ),
        })
    control_prompt = intent_control_prompt(session)
    if control_prompt:
        messages.append({"role": "system", "content": control_prompt})
    if session.get("gm_mode") == "full":
        messages.append({"role": "system", "content": _full_progression_prompt(session)})
    memory_summary = _structured_event_memory(session, max_chars=memory_max_chars)
    if memory_summary:
        messages.append({"role": "system", "content": "確定済みイベント履歴:\n" + memory_summary})
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
    if not opening and current_actions_for_session(session):
        action_result = session.get("last_action_result") if isinstance(session.get("last_action_result"), dict) else {}
        if not action_result.get("action_id"):
            return False
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
                "prepared_turn.draft.gm_text を完成済みのGM叙述として扱ってください。\n"
                "gm_text は原則として draft.gm_text を維持し、プレイヤー名・直前の発言・現在状態に矛盾する最小部分だけを書き換えてください。\n"
                "ユーザーが名前を入力しただけ、または開始操作だけの場合は、文体・出来事・NPC台詞・報酬内容を変えないでください。\n"
                "action_result、現在のゲーム状態、確定済みイベントだけが事実です。prepared draft 内の古い数値表現と矛盾する場合は必ず事実側に合わせてください。\n"
                "system_log は空文字、state_delta は空オブジェクト、choices は空配列にしてください。これらはゲームエンジンが確定します。\n"
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
            "current_scene": current_scene_id(session),
            "current_location": current_location_id(session),
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
            "flags": session.get("flags", {}),
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


def _structured_event_memory(session: dict[str, Any], max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    events = session.get("event_log")
    if not isinstance(events, list) or not events:
        return ""
    selected: list[dict[str, Any]] = []
    for event in reversed(events[-40:]):
        if not isinstance(event, dict):
            continue
        compact = {
            "kind": str(event.get("kind") or ""),
            "text": _one_line(str(event.get("text") or ""), limit=100),
            "data": _compact_event_data(str(event.get("kind") or ""), event.get("data")),
        }
        candidate = [compact, *selected]
        encoded = json.dumps(candidate, ensure_ascii=False, separators=(",", ": "))
        if len(encoded) > max_chars:
            break
        selected = candidate
    return json.dumps(selected, ensure_ascii=False, separators=(",", ": ")) if selected else ""


def _compact_event_data(kind: str, value: Any) -> dict[str, Any]:
    data = deepcopy(value) if isinstance(value, dict) else {}
    if kind != "combat_resolved":
        return data
    player = data.get("player") if isinstance(data.get("player"), dict) else {}
    return {
        "outcome": data.get("outcome"),
        "rounds": data.get("rounds"),
        "player": {
            key: player.get(key)
            for key in ("hp", "max_hp", "mp", "max_mp", "sp", "max_sp", "gold")
        },
        "enemies": [
            {
                "id": enemy.get("id"),
                "hp": enemy.get("hp"),
                "max_hp": enemy.get("max_hp"),
            }
            for enemy in data.get("enemies", [])[:4]
            if isinstance(enemy, dict)
        ],
    }


def _full_progression_prompt(session: dict[str, Any]) -> str:
    scene = find_scene(session.get("scenario_pack", {}), current_scene_id(session)) or {}
    goals = [str(value) for value in scene.get("goals", []) if str(value).strip()]
    actions = [
        {
            "action_id": str(action.get("id") or action.get("action_id") or ""),
            "text": str(action.get("text") or ""),
        }
        for action in _iter_actions(current_actions_for_session(session))
        if isinstance(action, dict) and not action.get("children")
    ][:8]
    return (
        "【FULLモード進行制御】\n"
        "現在場面の goals を進行先、available_actions を許可された行動面として扱ってください。\n"
        "resolved_action_result がある時はその直後だけを描写し、次に実行可能な action へ明確な手掛かりを置いてください。\n"
        "シナリオコンテキストにない遠隔地、NPC、敵、報酬、主線を新しく確定しないでください。\n"
        "選択肢と状態変化はエンジンが生成するため、物語を進めるために捏造しないでください。\n"
        + json.dumps({"goals": goals, "action_surface": actions}, ensure_ascii=False)
    )


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
        serialized = json.dumps(ctx, ensure_ascii=False)
        if len(serialized) > max_chars:
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
    else:
        character["inventory"] = []
    _synchronize_equipment(character)


def _synchronize_equipment(character: dict[str, Any]) -> None:
    inventory = character.get("inventory") if isinstance(character.get("inventory"), list) else []
    inventory_items = [item for item in inventory if isinstance(item, dict)]

    equipped_items: list[dict[str, Any]] = []
    normalized_equipment: list[str] = []
    for equipped_value in _as_text_list(character.get("equipment")):
        matched = next(
            (
                item for item in inventory_items
                if equipped_value in {str(item.get("name") or ""), str(item.get("id") or "")}
            ),
            None,
        )
        if not matched:
            continue
        canonical_name = str(matched.get("name") or matched.get("id") or "").strip()
        if canonical_name and canonical_name not in normalized_equipment:
            normalized_equipment.append(canonical_name)
            equipped_items.append(matched)

    equipped_weapon = next(
        (item for item in equipped_items if str(item_combat_spec(item).get("kind") or "").lower() == "weapon"),
        None,
    )
    if not equipped_weapon:
        equipped_weapon = next(
            (item for item in inventory_items if str(item_combat_spec(item).get("kind") or "").lower() == "weapon"),
            None,
        )
        if equipped_weapon:
            weapon_name = str(equipped_weapon.get("name") or equipped_weapon.get("id") or "").strip()
            if weapon_name and weapon_name not in normalized_equipment:
                normalized_equipment.append(weapon_name)

    character["equipment"] = normalized_equipment
    if equipped_weapon:
        weapon_attack = item_combat_spec(equipped_weapon)
        weapon_attack.pop("kind", None)
        combat = character.setdefault("combat", {})
        if not isinstance(combat, dict):
            combat = {}
            character["combat"] = combat
        combat["basic_attack"] = weapon_attack


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


def _character_from_template(template: dict[str, Any], scenario_pack: Optional[dict[str, Any]] = None) -> dict[str, Any]:
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
        _merge_inventory_catalog(character["inventory"], scenario_pack)
    if isinstance(template.get("equipment"), list):
        character["equipment"] = _as_text_list(template["equipment"])
    if isinstance(template.get("skills"), list):
        character["skills"] = deepcopy(template["skills"])
    if isinstance(template.get("combat"), dict):
        character["combat"] = deepcopy(template["combat"])
    _normalize_character(character)
    return character


def _merge_inventory_catalog(inventory: list[Any], scenario_pack: Optional[dict[str, Any]]) -> None:
    if not isinstance(scenario_pack, dict):
        return
    catalog = [item for item in scenario_pack.get("items", []) if isinstance(item, dict)]
    for index, raw in enumerate(inventory):
        entry = raw if isinstance(raw, dict) else {"name": str(raw), "quantity": 1}
        name = str(entry.get("name") or "")
        item_id = str(entry.get("id") or "")
        source = next(
            (
                item for item in catalog
                if (item_id and str(item.get("id") or "") == item_id)
                or (name and str(item.get("name") or item.get("title") or "") == name)
            ),
            None,
        )
        if source:
            merged = deepcopy(source)
            merged.update(entry)
            merged["effect"] = structured_item_effect(merged)
            inventory[index] = merged
        elif not isinstance(raw, dict):
            inventory[index] = entry
        elif isinstance(entry, dict):
            entry["effect"] = structured_item_effect(entry)


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


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


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
