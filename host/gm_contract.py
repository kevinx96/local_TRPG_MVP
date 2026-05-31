from __future__ import annotations

import json
import re
from typing import Any


STATE_MARKER = "---TRPG_JSON---"
_CHOICE_HEADING_RE = re.compile(
    r"^\s*(?:以下の)?(?:次の)?(?:選択肢(?:から行動を選んでください。?)?|行動を選択(?:してください。?)?|次の行動|次に、?どうする[？?]?)\s*[:：]?\s*$"
)
_NUMBERED_CHOICE_RE = re.compile(r"^\s*(?:[-*]\s*)?(\d{1,2})[\.．、\)]\s*(.+?)\s*$")
_CHOICE_NUMBER_ONLY_RE = re.compile(r"^\s*(\d{1,2})\s*$")
_SPEAKER_PREFIX_RE = re.compile(r"^\s*(?:GM|ＧＭ|ゲームマスター)\s*[:：]\s*", re.IGNORECASE)
_INTERNAL_LINE_PATTERNS = (
    "GM本文の後",
    "GM本文を書き",
    "JSON形式",
    "状態JSON",
    "TRPG_JSON",
    "ゲーム状況は上記JSON",
    "次のステップは何をしますか",
    STATE_MARKER,
    '"gm_text"',
    '"system_log"',
    '"state_delta"',
    '"choices"',
    '"dice_type"',
    '"dice_dc"',
    "```",
)
_PROTOCOL_TAIL_RE = re.compile(r"^(?:JSON|状態JSON|出力JSON)\s*[:：]?\s*$", re.IGNORECASE)
_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_UNCLOSED_THINK_RE = re.compile(r"<think>.*", re.IGNORECASE | re.DOTALL)


def build_gm_contract_prompt() -> str:
    """Return the system prompt that tells the LLM how to behave as GM.

    Kept concise so that small (7-8B) local models can follow reliably.
    """
    return (
        "あなたはTRPGのゲームマスター（GM）です。自然な日本語で応答してください。\n"
        "プレイヤーの行動を代行せず、状況描写のあとにプレイヤーの行動を待ってください。\n\n"
        "【応答ルール】\n"
        "・GM本文は200文字以上で、場面を五感で描写し、NPCの台詞は「」で囲んでください。\n"
        "・ダイスの種類はGMが決定します（通常判定1d20、スキル2d6、確率1d100）。\n"
        "・行動選択肢は本文に書かず、JSONのchoicesにだけ3つ入れてください。\n"
        "・state_delta.current_sceneには現在の章名を毎回入れてください。\n"
        "・アイテム追加時は name, description, effect を含めてください。\n\n"
        "【応答形式】\n"
        "まずGM本文を書き、最後に次のJSON形式で状態を出力してください。\n"
        f"GM本文の後に改行して {STATE_MARKER} を書き、続けてJSONを書いてください。\n\n"
        "```\n"
        f"{STATE_MARKER}\n"
        "{\n"
        '  "gm_text": "GM本文と同じ",\n'
        '  "system_log": "判定結果の短い説明",\n'
        '  "dice_type": "1d20",\n'
        '  "dice_dc": 10,\n'
        '  "state_delta": {\n'
        '    "hp_change": 0, "mp_change": 0, "sp_change": 0, "gold_change": 0,\n'
        '    "inventory_add": [], "inventory_remove": [],\n'
        '    "current_scene": null\n'
        "  },\n"
        '  "choices": [\n'
        '    {"text": "行動内容", "preview": "予想結果", "risk": "リスク説明"},\n'
        '    {"text": "行動内容", "preview": "予想結果", "risk": "リスク説明"},\n'
        '    {"text": "行動内容", "preview": "予想結果", "risk": "リスク説明"}\n'
        "  ]\n"
        "}\n"
        "```\n"
        "JSONのchoicesは必ず3つ含めてください。各選択肢のriskには「判定不要」「1d20判定（DC12）」「危険」などを書いてください。\n"
        "GM本文には「以下の選択肢」や番号付き選択肢を書かないでください。\n"
        "GM本文には「JSON:」「現在あなたは」「次のステップは何をしますか」などの内部指示を書かないでください。\n"
        "JSON以外の補足をマーカーの後ろに書かないでください。"
    )


def build_opening_prompt(session: dict[str, Any]) -> str:
    """Return a user-role prompt that asks the GM to generate an immersive opening."""
    character = session["character"]
    name = character.get("name") or "冒険者"
    return (
        f"ゲームを開始してください。プレイヤーキャラクターの名前は「{name}」です。\n"
        "シナリオの最初の場面を豊かに描写してください：\n"
        "・場面の詳細な情景描写（建物、光、音、空気の匂いなど）\n"
        "・その場にいるNPCの外見と最初の台詞\n"
        "・プレイヤーキャラクターの状況説明\n"
        "・GM本文は300文字以上で書いてください\n"
        "・行動選択肢は本文に書かず、最後に必ず3つの行動選択肢を含むJSONを出力してください\n"
        "・本文の最後に「どうしますか」「次のステップは何をしますか」「JSON:」などの進行指示や内部注釈を書かないでください"
    )


# ── Fallback choices when the model doesn't provide any ──

FALLBACK_CHOICES_BY_SCENE: dict[str, list[dict[str, str]]] = {
    "default": [
        {"text": "国王に邪竜の詳しい情報を聞く", "preview": "旅の目的と邪竜の手がかりを確認します", "risk": "判定不要"},
        {"text": "支度金と装備を確認する", "preview": "所持金、薬草、装備を整理します", "risk": "判定不要"},
        {"text": "城を出てスライムの森へ向かう", "preview": "第2章へ進みます", "risk": "1d20判定が必要（DC10）"},
    ],
    "王の間": [
        {"text": "国王に邪竜の詳しい情報を聞く", "preview": "邪竜イグニスと竜の谷について聞きます", "risk": "判定不要"},
        {"text": "支度金と装備を確認する", "preview": "50ゴールド、薬草、装備を確認します", "risk": "判定不要"},
        {"text": "城を出てスライムの森へ向かう", "preview": "第2章へ進みます", "risk": "1d20判定が必要（DC10）"},
    ],
    "森": [
        {"text": "鉄の剣でスライムを攻撃する", "preview": "戦闘チュートリアルを進めます", "risk": "1d20判定が必要（DC10）"},
        {"text": "薬草を使って態勢を整える", "preview": "HPを回復して安全を確保します", "risk": "判定不要"},
        {"text": "森を抜けて麓の村へ向かう", "preview": "第3章へ進みます", "risk": "判定不要"},
    ],
    "村": [
        {"text": "長老に邪竜の弱点を聞く", "preview": "冷気の弱点について情報を得ます", "risk": "判定不要"},
        {"text": "道具屋で氷の護符を買う", "preview": "50ゴールドで冷気の護符を入手します", "risk": "判定不要"},
        {"text": "竜の谷へ向かう", "preview": "第4章へ進みます", "risk": "危険"},
    ],
    "竜の谷": [
        {"text": "氷の護符を掲げて攻撃する", "preview": "邪竜の弱点を狙います", "risk": "1d20判定が必要（DC12）"},
        {"text": "鉄の剣で正面から斬り込む", "preview": "危険だが直接ダメージを狙います", "risk": "危険"},
        {"text": "防御して火炎の息に備える", "preview": "次の被害を抑えます", "risk": "判定不要"},
    ],
    "帰還": [
        {"text": "王都へ帰還する", "preview": "エンディングを迎えます", "risk": "判定不要"},
        {"text": "冒険の記録を確認する", "preview": "旅の成果を振り返ります", "risk": "判定不要"},
        {"text": "新たな旅に備える", "preview": "次の冒険へ余韻を残します", "risk": "判定不要"},
    ],
}


def get_fallback_choices(scene: str) -> list[dict[str, str]]:
    """Pick fallback choices based on the current scene name."""
    scene_lower = scene.lower() if scene else ""
    for keyword, choices in FALLBACK_CHOICES_BY_SCENE.items():
        if keyword != "default" and keyword in scene_lower:
            return choices
    return FALLBACK_CHOICES_BY_SCENE["default"]


def split_visible_and_json(text: str) -> tuple[str, dict[str, Any] | None, str | None]:
    if STATE_MARKER in text:
        visible_raw, raw_json = text.split(STATE_MARKER, 1)
        text_choices = extract_text_choices(visible_raw)
        visible = sanitize_visible_text(visible_raw)
        parsed = _parse_json_object(raw_json)
        if parsed is None:
            payload = _payload_from_recovered_choices(text_choices)
            return visible, payload, "GM応答のJSONを解析できませんでした。"
        parsed = _normalize_payload(parsed)
        _merge_recovered_choices(parsed, text_choices)
        if not visible:
            visible = sanitize_visible_text(str(parsed.get("gm_text", "")))
        return visible, parsed, None

    # Try to parse the whole thing as JSON (model might output only JSON)
    parsed = _parse_json_object(text)
    if parsed is not None:
        parsed = _normalize_payload(parsed)
        gm_text = sanitize_visible_text(str(parsed.get("gm_text", "")))
        _merge_recovered_choices(parsed, extract_text_choices(str(parsed.get("gm_text", ""))))
        if gm_text:
            return gm_text, parsed, None

    text_choices = extract_text_choices(text)
    payload = _payload_from_recovered_choices(text_choices)
    return sanitize_visible_text(text), payload, "GM応答に状態JSONが含まれていませんでした。"


def sanitize_visible_text(text: str) -> str:
    """Remove protocol instructions and inline choice lists from player-visible text."""
    cleaned = _strip_thinking_text(text.replace(STATE_MARKER, ""))
    lines = cleaned.splitlines()
    kept: list[str] = []
    skipping_choices = False
    choice_block_seen_number = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if skipping_choices:
                continue
            if kept and kept[-1] != "":
                kept.append("")
            continue

        if _is_internal_protocol_line(stripped):
            continue
        if _PROTOCOL_TAIL_RE.match(stripped):
            break
        if _looks_like_action_prompt_leak(stripped):
            continue
        if _CHOICE_HEADING_RE.match(stripped):
            skipping_choices = True
            choice_block_seen_number = False
            continue
        if skipping_choices and _NUMBERED_CHOICE_RE.match(stripped):
            choice_block_seen_number = True
            continue
        if skipping_choices and not choice_block_seen_number:
            continue
        if skipping_choices:
            skipping_choices = False
        if _NUMBERED_CHOICE_RE.match(stripped) and _looks_like_choice_line(stripped):
            continue
        if _looks_like_json_line(stripped):
            continue

        line = _strip_speaker_prefix(line, kept)
        if not line.strip():
            continue
        kept.append(line.rstrip())

    return _collapse_blank_lines("\n".join(kept).strip())


def extract_text_choices(text: str) -> list[dict[str, str]]:
    """Recover numbered choices from visible text when the JSON block is missing or broken."""
    choices: list[dict[str, str]] = []
    in_choice_block = False
    choice_block_seen_number = False
    pending_number = False

    for line in text.splitlines():
        stripped = line.strip()
        if _CHOICE_HEADING_RE.match(stripped):
            in_choice_block = True
            choice_block_seen_number = False
            pending_number = False
            continue
        match = _NUMBERED_CHOICE_RE.match(stripped)
        if match and (in_choice_block or _looks_like_choice_line(stripped)):
            choice_block_seen_number = True
            pending_number = False
            choice_text = _clean_choice_text(match.group(2))
            if choice_text:
                choices.append({"text": choice_text, "preview": "", "risk": ""})
            continue
        if in_choice_block and _CHOICE_NUMBER_ONLY_RE.match(stripped):
            choice_block_seen_number = True
            pending_number = True
            continue
        if in_choice_block and pending_number and stripped:
            choice_text = _clean_choice_text(stripped)
            if choice_text:
                choices.append({"text": choice_text, "preview": "", "risk": ""})
            pending_number = False
            continue
        if in_choice_block and stripped and not choice_block_seen_number:
            continue
        if in_choice_block and stripped:
            continue
        if not stripped:
            continue

    return choices[:5]


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Handle alternate key names that small models might use."""
    # scenario_text → gm_text (old format compatibility)
    if "scenario_text" in payload and "gm_text" not in payload:
        payload["gm_text"] = payload.pop("scenario_text")

    # hp_change at top level → state_delta.hp_change
    if "state_delta" not in payload:
        payload["state_delta"] = {}
    delta = payload["state_delta"]
    for key in ("hp_change", "mp_change", "sp_change", "gold", "gold_change",
                "inventory_add", "inventory_remove", "current_scene"):
        if key in payload and key not in delta:
            delta[key] = payload.pop(key)

    return payload


def _merge_recovered_choices(payload: dict[str, Any], choices: list[dict[str, str]]) -> None:
    existing = payload.get("choices")
    if choices and (
        not isinstance(existing, list)
        or not existing
        or (len(choices) >= 2 and len(existing) < len(choices))
    ):
        payload["choices"] = choices


def _payload_from_recovered_choices(choices: list[dict[str, str]]) -> dict[str, Any] | None:
    if not choices:
        return None
    return {
        "system_log": "",
        "state_delta": {},
        "choices": choices,
    }


def _is_internal_protocol_line(line: str) -> bool:
    return any(pattern in line for pattern in _INTERNAL_LINE_PATTERNS)


def _looks_like_action_prompt_leak(line: str) -> bool:
    if "次のステップ" in line or "何をしますか" in line:
        return True
    return line.startswith("では、") and "べきか" in line and "それとも" in line


def _strip_thinking_text(text: str) -> str:
    text = _THINK_BLOCK_RE.sub("", text)
    return _UNCLOSED_THINK_RE.sub("", text)


def _looks_like_json_line(line: str) -> bool:
    if line in {"{", "}", "[", "]", "},"}:
        return True
    return bool(re.match(r'^\s*["}\]],?', line))


def _looks_like_choice_line(line: str) -> bool:
    match = _NUMBERED_CHOICE_RE.match(line)
    if not match:
        return False
    content = match.group(2)
    choice_markers = (
        "する", "向かう", "進む", "聞く", "探索", "調べる", "使う", "話す",
        "出発", "購入", "訪ねる", "収集", "踏み入れる", "入る", "戻る",
    )
    return any(marker in content for marker in choice_markers) or content.startswith("「")


def _clean_choice_text(text: str) -> str:
    cleaned = text.strip().rstrip("。")
    cleaned = re.sub(r"^[「『](.+)[」』]$", r"\1", cleaned)
    return cleaned


def _collapse_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text)


def _strip_speaker_prefix(line: str, kept: list[str]) -> str:
    if kept:
        return line
    return _SPEAKER_PREFIX_RE.sub("", line, count=1)


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
