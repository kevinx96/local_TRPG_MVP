from __future__ import annotations

import json
import re
from typing import Any


STATE_MARKER = "---TRPG_JSON---"


def build_gm_contract_prompt() -> str:
    return (
        "あなたはTRPGのゲームマスターです。すべて自然な日本語で応答してください。\n"
        "プレイヤーの行動を代行せず、状況描写のあとに次の行動を待ってください。\n"
        "応答形式は必ず次の通りです。\n"
        "1. まずプレイヤーに見せるGM本文だけを書く。\n"
        f"2. 最後に改行して {STATE_MARKER} を書き、その後にJSONを1つだけ書く。\n"
        "JSON形式:\n"
        "{\n"
        '  "gm_text": "GM本文と同じ内容",\n'
        '  "system_log": "判定や状態変化の短い説明",\n'
        '  "state_delta": {\n'
        '    "hp_change": 0,\n'
        '    "mp_change": 0,\n'
        '    "sp_change": 0,\n'
        '    "inventory_add": [],\n'
        '    "inventory_remove": [],\n'
        '    "current_scene": null,\n'
        '    "background_image": null,\n'
        '    "character_image": null\n'
        "  },\n"
        '  "choices": []\n'
        "}\n"
        "JSON以外の補足をマーカーの後ろに書いてはいけません。"
    )


def split_visible_and_json(text: str) -> tuple[str, dict[str, Any] | None, str | None]:
    if STATE_MARKER in text:
        visible, raw_json = text.split(STATE_MARKER, 1)
        parsed = _parse_json_object(raw_json)
        if parsed is None:
            return visible.strip(), None, "GM応答のJSONを解析できませんでした。"
        return visible.strip(), parsed, None

    parsed = _parse_json_object(text)
    if parsed is not None and "gm_text" in parsed:
        return str(parsed.get("gm_text", "")).strip(), parsed, None

    return text.strip(), None, "GM応答に状態JSONが含まれていませんでした。"


def _parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = _strip_json_fence(text).strip()
    candidates = [cleaned]
    extracted = _extract_last_json_object(cleaned)
    if extracted and extracted != cleaned:
        candidates.insert(0, extracted)

    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _strip_json_fence(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else text


def _extract_last_json_object(text: str) -> str | None:
    end = text.rfind("}")
    if end == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(end, -1, -1):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "}":
            depth += 1
        elif char == "{":
            depth -= 1
            if depth == 0:
                return text[index : end + 1]
    return None
