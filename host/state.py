from __future__ import annotations

import json
import random
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HOST_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = HOST_ROOT.parent
SAVE_DIR = HOST_ROOT / "saves"
DEFAULT_SCENARIO = HOST_ROOT / "prompt" / "text" / "dragon_rpg.txt"


# ── Default item descriptions (fallback when the model doesn't provide one) ──

DEFAULT_ITEM_CATALOG: dict[str, dict[str, str]] = {
    "鉄の剣": {
        "description": "鍛冶屋で打たれた頑丈な剣。刃はまだ鋭く、冒険者の基本装備。",
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
    "上級薬草": {
        "description": "希少な高山薬草を調合した回復薬。鮮やかな緑色に輝く。",
        "effect": "HPを20回復",
    },
    "魔法の杖": {
        "description": "古代の魔法使いが残した杖。先端の宝石が淡く光る。",
        "effect": "MP消費で魔法攻撃が可能",
    },
    "鋼の剣": {
        "description": "精錬された鋼鉄の剣。鉄の剣より遥かに切れ味が良い。",
        "effect": "攻撃力+5",
    },
    "氷の護符": {
        "description": "冷気の力が封じられた青い護符。触ると指先がひんやりする。",
        "effect": "冷気属性の攻撃が可能",
    },
}


DEFAULT_CHARACTER: dict[str, Any] = {
    "name": "アルス",
    "description": "世界を救うため旅立つ若き勇者。",
    "hp": 20,
    "max_hp": 20,
    "mp": 8,
    "max_mp": 8,
    "sp": 10,
    "max_sp": 10,
    "gold": 0,
    "inventory": [
        {"name": "鉄の剣", "description": "鍛冶屋で打たれた頑丈な剣。刃はまだ鋭く、冒険者の基本装備。", "effect": "通常攻撃に使用", "quantity": 1},
        {"name": "革の鎧", "description": "なめした革で作られた軽量の鎧。動きやすさと防御力を両立。", "effect": "被ダメージを軽減", "quantity": 1},
        {"name": "薬草", "description": "森で採れる癒しの薬草。苦い味がするが、傷を癒す力がある。", "effect": "HPを10回復", "quantity": 1},
    ],
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
        # Handle name override
        if "name" in character_overrides:
            character["name"] = character_overrides["name"]
        # Handle other overrides
        other = {k: v for k, v in character_overrides.items() if k != "name"}
        if other:
            _deep_update(character, other)
        _normalize_character(character)

    session = {
        "id": uuid.uuid4().hex,
        "scenario_path": str(path),
        "scenario_title": path.stem,
        "scenario_prompt": scenario_text,
        "current_scene": "第1章：王の間",
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
    from .gm_contract import FALLBACK_CHOICES_BY_SCENE, extract_text_choices, get_fallback_choices, sanitize_visible_text

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
    elif _choices_match_known_fallback(public.get("choices"), FALLBACK_CHOICES_BY_SCENE):
        public["choices"] = get_fallback_choices(str(public.get("current_scene") or ""))
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
    from .gm_contract import get_fallback_choices

    if gm_text.strip():
        add_assistant_message(session, gm_text)
    if parse_warning:
        add_system_log(session, parse_warning)

    if not payload:
        # Model didn't return JSON — still provide fallback choices
        session["choices"] = get_fallback_choices(session.get("current_scene", ""))
        return

    system_log = str(payload.get("system_log") or "").strip()
    add_system_log(session, system_log)

    # Extract dice specification for next turn
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

    # Extract choices after state changes so fallback choices use the new scene.
    raw_choices = payload.get("choices")
    if isinstance(raw_choices, list) and len(raw_choices) > 0:
        session["choices"] = _normalize_choices(raw_choices)
    else:
        session["choices"] = get_fallback_choices(session.get("current_scene", ""))


def _normalize_choices(raw: list[Any]) -> list[dict[str, str]]:
    """Ensure each choice has text, preview, and risk fields."""
    choices = []
    for item in raw:
        if isinstance(item, str):
            choices.append({"text": item, "preview": "", "risk": ""})
        elif isinstance(item, dict):
            choices.append({
                "text": str(item.get("text", "")),
                "preview": str(item.get("preview", "")),
                "risk": str(item.get("risk", "")),
            })
    return choices[:5]  # Cap at 5 choices max


def _choices_match_known_fallback(raw: Any, fallback_groups: dict[str, list[dict[str, str]]]) -> bool:
    if not isinstance(raw, list) or not raw:
        return False
    texts = [str(item.get("text", "")) if isinstance(item, dict) else str(item) for item in raw]
    for choices in fallback_groups.values():
        if texts == [choice["text"] for choice in choices]:
            return True
    return False


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

    if "gold_change" in delta and isinstance(delta["gold_change"], (int, float)):
        character["gold"] = max(0, int(character.get("gold", 0)) + int(delta["gold_change"]))
    if "gold" in delta and isinstance(delta["gold"], (int, float)):
        character["gold"] = max(0, int(delta["gold"]))

    for item in _as_item_list(delta.get("inventory_add")):
        item_name = item["name"] if isinstance(item, dict) else item
        add_qty = int(item.get("quantity", 1)) if isinstance(item, dict) else 1
        # Find existing item by name
        existing = None
        for inv_item in character["inventory"]:
            ename = inv_item.get("name") if isinstance(inv_item, dict) else inv_item
            if ename == item_name:
                existing = inv_item
                break
        if existing is not None and isinstance(existing, dict):
            existing["quantity"] = existing.get("quantity", 1) + add_qty
        else:
            enriched = _enrich_item(item if isinstance(item, dict) else {"name": item})
            enriched["quantity"] = add_qty
            character["inventory"].append(enriched)

    for item in _as_text_list(delta.get("inventory_remove")):
        new_inv = []
        for existing in character["inventory"]:
            ename = existing.get("name") if isinstance(existing, dict) else existing
            if ename == item and isinstance(existing, dict):
                existing["quantity"] = existing.get("quantity", 1) - 1
                if existing["quantity"] > 0:
                    new_inv.append(existing)
                # else: quantity reached 0, drop the item
            else:
                new_inv.append(existing)
        character["inventory"] = new_inv

    for image_key in ("background_image", "character_image"):
        if isinstance(delta.get(image_key), str):
            character[image_key] = delta[image_key]

    if isinstance(delta.get("current_scene"), str) and delta["current_scene"].strip():
        session["current_scene"] = delta["current_scene"].strip()


def _enrich_item(item: dict[str, Any]) -> dict[str, str | int]:
    """Ensure an item dict has name, description, effect, quantity — using catalog fallback."""
    name = str(item.get("name", "不明"))
    catalog_entry = DEFAULT_ITEM_CATALOG.get(name, {})
    return {
        "name": name,
        "description": str(item.get("description") or catalog_entry.get("description", "")),
        "effect": str(item.get("effect") or catalog_entry.get("effect", "")),
        "quantity": int(item.get("quantity", 1)),
    }


def build_llm_messages(session: dict[str, Any], latest_roll: dict[str, Any], contract_prompt: str) -> list[dict[str, str]]:
    character = session["character"]
    # Serialize inventory names only for state summary to save tokens
    inventory_summary = [
        (i["name"] if isinstance(i, dict) else i) for i in character.get("inventory", [])
    ]
    state_summary = json.dumps(
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
                "inventory": inventory_summary,
                "equipment": character.get("equipment", []),
            },
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
    for key in ("equipment",):
        character[key] = _as_text_list(character.get(key))
    character["gold"] = max(0, int(character.get("gold", 0)))
    # Normalize inventory to item objects
    raw_inv = character.get("inventory", [])
    if isinstance(raw_inv, list):
        character["inventory"] = [_ensure_item_object(i) for i in raw_inv]


def _ensure_item_object(item: Any) -> dict[str, str]:
    """Convert a raw inventory entry (string or dict) to a proper item object."""
    if isinstance(item, dict):
        return _enrich_item(item)
    name = str(item).strip() if item else "不明"
    return _enrich_item({"name": name})


def _as_item_list(value: Any) -> list[Any]:
    """Accept both string items and dict items for inventory_add."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if item]
    return []


def _as_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _infer_state_delta_from_text(gm_text: str, session: dict[str, Any], delta: dict[str, Any]) -> None:
    if "gold" in delta or "gold_change" in delta:
        return
    character = session.get("character", {})
    if int(character.get("gold", 0)) > 0:
        return
    gain_markers = ("与える", "与え", "受け取", "受け取り", "手渡", "預け", "獲得", "入手", "差し出")
    if not any(marker in gm_text for marker in gain_markers):
        return
    match = re.search(r"(\d+)\s*ゴールド", gm_text)
    if match:
        delta["gold_change"] = int(match.group(1))


def _infer_scene_delta_from_text(gm_text: str, session: dict[str, Any], delta: dict[str, Any]) -> None:
    if isinstance(delta.get("current_scene"), str) and delta["current_scene"].strip():
        return

    current_scene = str(session.get("current_scene") or "")
    player_text = _latest_player_text(session)
    if _wants_to_advance(player_text):
        explicit_player_scene = _scene_from_keywords(player_text)
        if explicit_player_scene:
            delta["current_scene"] = explicit_player_scene
            return
        next_scene = _next_story_scene(current_scene)
        if next_scene:
            delta["current_scene"] = next_scene
            return

    explicit_scene = _scene_from_keywords(gm_text)
    if explicit_scene:
        delta["current_scene"] = explicit_scene
        return


def _latest_player_text(session: dict[str, Any]) -> str:
    for message in reversed(session.get("messages", [])):
        if message.get("role") == "user":
            return str(message.get("text") or "")
    return ""


def _scene_from_keywords(text: str) -> str | None:
    if any(keyword in text for keyword in ("竜の谷", "邪竜", "イグニス", "最終決戦")):
        return "第4章：竜の谷"
    if any(keyword in text for keyword in ("麓の村", "村の長老", "長老", "道具屋", "村へ")):
        return "第3章：麓の村"
    if any(keyword in text for keyword in ("スライムの森", "スライム", "森へ", "森に")):
        return "第2章：スライムの森"
    if any(keyword in text for keyword in ("王の間", "謁見", "国王", "玉座")):
        return "第1章：王の間"
    return None


def _wants_to_advance(player_text: str) -> bool:
    return any(keyword in player_text for keyword in ("先へ進", "進む", "出発", "城を出", "向かう", "足を踏み入れる"))


def _next_story_scene(current_scene: str) -> str | None:
    ordered = [
        "第1章：王の間",
        "第2章：スライムの森",
        "第3章：麓の村",
        "第4章：竜の谷",
    ]
    for index, scene in enumerate(ordered[:-1]):
        if scene in current_scene or scene.split("：", 1)[1] in current_scene:
            return ordered[index + 1]
    if current_scene in ("", "開始"):
        return ordered[0]
    return None


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
