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
    "hp": 20,
    "max_hp": 20,
    "mp": 8,
    "max_mp": 8,
    "sp": 10,
    "max_sp": 10,
    "gold": 0,
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
) -> dict[str, Any]:
    normalized_gm_mode = _normalize_gm_mode(gm_mode)
    path = _scenario_path_for_gm_mode(resolve_local_path(scenario_path), normalized_gm_mode)
    scenario_pack = load_scenario_pack(path)
    character = deepcopy(DEFAULT_CHARACTER)
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
    if gm_mode != "full" or path.stem.endswith("_hybrid"):
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
    public = deepcopy(session)
    public.pop("scenario_prompt", None)
    public.pop("scenario_pack", None)
    public["current_scene_title"] = scene_title(session)

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


def roll_dice(session: dict[str, Any], expression: str = "1d20") -> dict[str, Any]:
    count, sides = _parse_dice_expression(expression)
    rolls = [random.randint(1, sides) for _ in range(count)]
    entry = {"expression": expression, "rolls": rolls, "total": sum(rolls), "created_at": utc_now()}
    session["dice_log"].append(entry)
    return entry


def apply_gm_payload(
    session: dict[str, Any],
    gm_text: str,
    payload: Optional[dict[str, Any]],
    parse_warning: Optional[str] = None,
) -> None:
    if gm_text.strip():
        add_assistant_message(session, gm_text)

    if not payload:
        session["choices"] = fallback_choices_for_session(session)
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
    session["choices"] = fallback_choices_for_session(session)


def _normalize_choices(raw: list[Any]) -> list[dict[str, str]]:
    choices = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            choices.append({"text": item.strip(), "preview": "", "risk": ""})
        elif isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            if text:
                choices.append({
                    "text": text,
                    "preview": str(item.get("preview", "")),
                    "risk": str(item.get("risk", "")),
                })
    return choices[:5]


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

    if isinstance(delta.get("current_scene"), str) and delta["current_scene"].strip():
        pack = session.get("scenario_pack") if isinstance(session.get("scenario_pack"), dict) else None
        current_scene = delta["current_scene"].strip()
        session["current_scene"] = resolve_scene_id(pack, current_scene) if pack else current_scene


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
    if session.get("gm_mode") == "full":
        return _build_hybrid_llm_messages(session, latest_roll, contract_prompt)

    config = load_config()
    prompting = config.get("prompting") if isinstance(config.get("prompting"), dict) else {}
    history_messages = _bounded_int(prompting.get("history_messages"), default=4, minimum=0, maximum=12)
    memory_max_chars = _bounded_int(prompting.get("memory_max_chars"), default=1200, minimum=0, maximum=4000)
    action_history_max = _bounded_int(prompting.get("action_history_max"), default=40, minimum=0, maximum=200)
    action_history_item_chars = _bounded_int(prompting.get("action_history_item_chars"), default=80, minimum=20, maximum=240)

    character = session["character"]
    player_text = _latest_player_text(session)
    scenario_context = select_scenario_context(session, player_text)
    state_summary = _current_state_summary(session, character, latest_roll)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": contract_prompt},
        {"role": "system", "content": "シナリオコンテキスト:\n" + json.dumps(scenario_context, ensure_ascii=False)},
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
                "【FULL/HYBRIDモード】\n"
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
    inventory_summary = [(i["name"] if isinstance(i, dict) else i) for i in character.get("inventory", [])]
    return json.dumps(
        {
            "gm_mode": session.get("gm_mode", "semi"),
            "current_scene": session["current_scene"],
            "current_scene_title": scene_title(session),
            "character": {
                "name": character.get("name"),
                "hp": character.get("hp"),
                "max_hp": character.get("max_hp"),
                "mp": character.get("mp"),
                "max_mp": character.get("max_mp"),
                "sp": character.get("sp"),
                "max_sp": character.get("max_sp"),
                "gold": character.get("gold", 0),
                "inventory": inventory_summary,
                "equipment": character.get("equipment", []),
            },
            "latest_dice_roll": latest_roll,
        },
        ensure_ascii=False,
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


def _normalize_character(character: dict[str, Any]) -> None:
    for stat in ("hp", "mp", "sp"):
        max_key = f"max_{stat}"
        character[max_key] = int(character.get(max_key, character.get(stat, 0)))
        character[stat] = max(0, min(character[max_key], int(character.get(stat, character[max_key]))))
    character["equipment"] = _as_text_list(character.get("equipment"))
    character["gold"] = max(0, int(character.get("gold", 0)))
    raw_inv = character.get("inventory", [])
    if isinstance(raw_inv, list):
        character["inventory"] = [_ensure_item_object(i) for i in raw_inv]


def _ensure_item_object(item: Any) -> dict[str, Union[str, int]]:
    if isinstance(item, dict):
        return _enrich_item(item)
    name = str(item).strip() if item else "不明"
    return _enrich_item({"name": name})


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
    explicit_scene = infer_scene_from_text(session, player_text) or infer_scene_from_text(session, gm_text)
    if explicit_scene:
        delta["current_scene"] = explicit_scene


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
