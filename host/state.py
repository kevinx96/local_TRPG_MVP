from __future__ import annotations

import json
import random
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HOST_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = HOST_ROOT.parent
SAVE_DIR = HOST_ROOT / "saves"
DEFAULT_SCENARIO = HOST_ROOT / "prompt" / "text" / "dragon_rpg.txt"


DEFAULT_CHARACTER: dict[str, Any] = {
    "name": "アルス",
    "description": "世界を救うため旅立つ若き勇者。",
    "hp": 20,
    "max_hp": 20,
    "mp": 8,
    "max_mp": 8,
    "sp": 10,
    "max_sp": 10,
    "inventory": ["鉄の剣", "革の鎧", "薬草"],
    "equipment": ["鉄の剣", "革の鎧"],
    "background_image": "",
    "character_image": "",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or HOST_ROOT / "config.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def resolve_local_path(value: str | None, default: Path = DEFAULT_SCENARIO) -> Path:
    if not value:
        return default
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def read_scenario_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")
    return path.read_text(encoding="utf-8-sig")


def create_session(
    scenario_path: str | None = None,
    character_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = resolve_local_path(scenario_path)
    scenario_text = read_scenario_prompt(path)
    character = deepcopy(DEFAULT_CHARACTER)
    if character_overrides:
        _deep_update(character, character_overrides)
        _normalize_character(character)

    session = {
        "id": uuid.uuid4().hex,
        "scenario_path": str(path),
        "scenario_title": path.stem,
        "scenario_prompt": scenario_text,
        "current_scene": "開始",
        "character": character,
        "messages": [],
        "system_logs": [],
        "dice_log": [],
        "choices": [],
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    save_session(session)
    return public_session(session)


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
    return public


def add_player_message(session: dict[str, Any], text: str, speaker: str = "プレイヤー") -> None:
    session["messages"].append(
        {
            "role": "user",
            "speaker": speaker,
            "text": text,
            "created_at": utc_now(),
        }
    )


def add_assistant_message(session: dict[str, Any], text: str, speaker: str = "GM") -> None:
    session["messages"].append(
        {
            "role": "assistant",
            "speaker": speaker,
            "text": text,
            "created_at": utc_now(),
        }
    )


def add_system_log(session: dict[str, Any], text: str) -> None:
    if text:
        session["system_logs"].append({"text": text, "created_at": utc_now()})


def roll_dice(session: dict[str, Any], expression: str = "1d20") -> dict[str, Any]:
    count, sides = _parse_dice_expression(expression)
    rolls = [random.randint(1, sides) for _ in range(count)]
    entry = {
        "expression": expression,
        "rolls": rolls,
        "total": sum(rolls),
        "created_at": utc_now(),
    }
    session["dice_log"].append(entry)
    return entry


def apply_gm_payload(
    session: dict[str, Any],
    gm_text: str,
    payload: dict[str, Any] | None,
    parse_warning: str | None = None,
) -> None:
    add_assistant_message(session, gm_text)
    if parse_warning:
        add_system_log(session, parse_warning)
    if not payload:
        return

    system_log = str(payload.get("system_log") or "").strip()
    add_system_log(session, system_log)
    session["choices"] = payload.get("choices") if isinstance(payload.get("choices"), list) else []
    state_delta = payload.get("state_delta") or {}
    if not isinstance(state_delta, dict):
        add_system_log(session, "GM応答のstate_deltaが不正だったため無視しました。")
        return
    apply_state_delta(session, state_delta)


def apply_state_delta(session: dict[str, Any], delta: dict[str, Any]) -> None:
    character = session["character"]
    for stat in ("hp", "mp", "sp"):
        change_key = f"{stat}_change"
        set_key = stat
        if change_key in delta and isinstance(delta[change_key], (int, float)):
            character[stat] = int(character.get(stat, 0) + delta[change_key])
        if set_key in delta and isinstance(delta[set_key], (int, float)):
            character[stat] = int(delta[set_key])
        max_key = f"max_{stat}"
        character[stat] = max(0, min(int(character.get(max_key, character[stat])), int(character[stat])))

    for item in _as_text_list(delta.get("inventory_add")):
        if item not in character["inventory"]:
            character["inventory"].append(item)
    for item in _as_text_list(delta.get("inventory_remove")):
        character["inventory"] = [existing for existing in character["inventory"] if existing != item]

    for image_key in ("background_image", "character_image"):
        if isinstance(delta.get(image_key), str):
            character[image_key] = delta[image_key]

    if isinstance(delta.get("current_scene"), str) and delta["current_scene"].strip():
        session["current_scene"] = delta["current_scene"].strip()


def build_llm_messages(session: dict[str, Any], latest_roll: dict[str, Any], contract_prompt: str) -> list[dict[str, str]]:
    character = session["character"]
    state_summary = json.dumps(
        {
            "current_scene": session["current_scene"],
            "character": character,
            "latest_dice_roll": latest_roll,
        },
        ensure_ascii=False,
    )
    messages: list[dict[str, str]] = [
        {"role": "system", "content": contract_prompt},
        {"role": "system", "content": "シナリオ資料:\n" + session["scenario_prompt"]},
        {"role": "system", "content": "現在のゲーム状態:\n" + state_summary},
    ]
    for message in session["messages"][-12:]:
        role = "assistant" if message["role"] == "assistant" else "user"
        messages.append({"role": role, "content": f"{message['speaker']}: {message['text']}"})
    return messages


def _deep_update(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _normalize_character(character: dict[str, Any]) -> None:
    for stat in ("hp", "mp", "sp"):
        max_key = f"max_{stat}"
        character[max_key] = int(character.get(max_key, character.get(stat, 0)))
        character[stat] = max(0, min(character[max_key], int(character.get(stat, character[max_key]))))
    for key in ("inventory", "equipment"):
        character[key] = _as_text_list(character.get(key))


def _as_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


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
