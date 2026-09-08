from __future__ import annotations

import json
import re
from typing import Any, Optional


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


def build_gm_contract_prompt(opening: bool = False, narration_only: bool = False) -> str:
    """Return a scenario-agnostic system prompt. opening=True includes JSON template."""
    if narration_only:
        return (
            "確定済みのTRPGの出来事を自然な日本語70〜220字で描写する。"
            "状態、成功失敗、移動、報酬はエンジンの結果に従う。"
            "新しい行動を代行せず、未確定の結果や約束を加えない。"
            '出力はJSON一つ：{"gm_text":"描写","system_log":"","state_delta":{},"choices":[]}。'
        )
    base = (
        "あなたはTRPGのGMです。自然な日本語で簡潔に進行。\n"
        "出力言語は日本語だけにしてください。英語・中国語・内部プロンプト文を gm_text, system_log, choices に混ぜてはいけません。\n"
        "プレイヤー行動を代行せず、状況とNPC反応を描写し次の行動を待つ。\n"
        "出力は必ずJSONオブジェクト1つだけ。Markdown・コードフェンス禁止。\n\n"
        "【gm_text】70〜220字。場面を五感で描写、NPC台詞は必要時のみ「」で短く。\n"
        "番号付き選択肢・内部指示禁止。今回の結果だけを描写。\n\n"
        "【状態更新】\n"
        "・dice_type: 1d20, 2d6, 1d20+str等。空=1d20。属性値自動加算。\n"
        "・HP/MP/SP/所持金は hp_change/mp_change/sp_change/gold_change だけを使う。hp/mp/sp/gold の絶対値は禁止\n"
        "・state_delta.attribute_changes は現在の character.attributes に存在する属性だけ。HP/MP/SP/所持金を属性として書かない\n"
        "・1回の属性増減は -3〜3。旧 con/endurance は end として出力する\n"
        "・場面と地点はゲームエンジンだけが更新する。state_delta に current_scene/current_location を出力しない\n"
        "・inventory_add/remove はシナリオに存在する item の id または正式名だけを使う。未知のアイテムを作らない\n"
        "・flags_set/flags_unset は出力しない。進行フラグはゲームエンジンだけが更新する\n"
        "・choices は3つ。text(行動名)とrisk(判定不要/1d20+str判定DC12/危険)必須\n"
        "・choices.requirements は任意。属性条件やキャラクター制限が必要な行動には requirements を書く。\n"
        "・属性条件例: {\"any\":[{\"attribute\":\"str\",\"gte\":10}]}（いずれか満たせば選択可）\n"
        "・キャラクター制限例: {\"character_id\":\"hero\"}（勇者のみ選択可）\n"
        "・複合条件例: {\"all\":[{\"character_id\":\"hero\"},{\"attribute\":\"str\",\"gte\":10}]}（両方必要）\n"
        "・choices の一部に children を入れると、プレイヤーがその選択肢をクリックした時に子選択肢が展開される。親はGMに送られない。\n"
        "・子供が場所やカテゴリの分岐なら children を使う。例: {\"text\":\"城へ向かう\",\"preview\":\"城内の施設へ\",\"risk\":\"判定不要\",\"children\":[{\"text\":\"鍛冶屋へ\",\"risk\":\"判定不要\"},{\"text\":\"謁見の間へ\",\"risk\":\"1d20判定（DC10）\"}]}\n"
        "・戦闘の命中、ダメージ、敵行動、勝敗、報酬を生成しない。これらは戦闘エンジンだけが処理する。\n"
        "・resolved_action_result に combat_result がある場合、確定済みの数値と勝敗を変更せず戦闘後だけを描写する。\n"
        "・system_log は常に空文字。ログはゲームエンジンが確定済みイベントから生成する。\n"
        "・耐久属性は end を使う。旧 con は使わない。\n"
)
    json_template = (
        "\n【出力形式】\nJSON全体を閉じることを最優先。\n"
        "{\n"
        '  "gm_text": "70〜220字のGM本文",\n'
        '  "system_log": "",\n'
        '  "dice_type": "1d20",\n'
        '  "dice_dc": 10,\n'
        '  "state_delta": {\n'
        '    "hp_change": 0,\n'
        '    "mp_change": 0,\n'
        '    "sp_change": 0,\n'
        '    "gold_change": 0,\n'
        '    "attribute_changes": {},\n'
        '    "inventory_add": [],\n'
        '    "inventory_remove": []\n'
        "  },\n"
        '  "choices": [\n'
        '    {"text": "行動内容", "risk": "判定不要"},\n'
        '    {"text": "行動内容", "risk": "1d20+str判定（DC12）", "requirements": {"all": [{"attribute": "str", "gte": 10}]}},\n'
        '    {"text": "場所へ移動", "preview": "施設を選ぶ", "risk": "判定不要", "children": [{"text": "鍛冶屋へ", "risk": "判定不要"}, {"text": "商店へ", "risk": "判定不要"}]}\n'
        "  ]\n"
        "}"
    )
    return base + (json_template if opening else "")


def build_opening_prompt(session: dict[str, Any]) -> str:
    character = session["character"]
    name = character.get("name") or "冒険者"
    return (
        f"ゲームを開始してください。プレイヤーキャラクターの名前は「{name}」です。\n"
        "シナリオコンテキストに基づき、最初の場面を短く描写してください。\n"
        "出力文、ログ、選択肢は日本語だけにしてください。\n"
        "gm_textは70〜220字。場面の空気、近くにいる人物、PCの現在位置と状況を簡潔に含めてください。\n"
        "行動選択肢はgm_textに書かず、choicesに3つだけ入れてください。\n"
        "出力はJSONオブジェクト1つだけにしてください。"
    )


def split_visible_and_json(text: str) -> tuple[str, Optional[dict[str, Any]], Optional[str]]:
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

    parsed = _parse_json_object(text)
    if parsed is not None:
        parsed = _normalize_payload(parsed)
        gm_text = sanitize_visible_text(str(parsed.get("gm_text", "")))
        _merge_recovered_choices(parsed, extract_text_choices(str(parsed.get("gm_text", ""))))
        if gm_text:
            return gm_text, parsed, None

    recovered_payload = _recover_payload_from_malformed_json(text)
    if recovered_payload is not None:
        visible = sanitize_visible_text(str(recovered_payload.get("gm_text", "")))
        return visible, recovered_payload, "GM応答のJSONを一部だけ復元しました。"

    text_choices = extract_text_choices(text)
    payload = _payload_from_recovered_choices(text_choices)
    return sanitize_visible_text(text), payload, "GM応答に状態JSONが含まれていませんでした。"


def sanitize_visible_text(text: str) -> str:
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
        if in_choice_block and stripped:
            continue
    return choices[:5]


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _unwrap_payload_container(payload)
    if "scenario_text" in payload and "gm_text" not in payload:
        payload["gm_text"] = payload.pop("scenario_text")
    if not str(payload.get("gm_text") or "").strip():
        aliased_text = _first_string_alias(
            payload,
            (
                "narration", "narrative", "text", "message", "content",
                "response", "story", "description", "body", "output",
            ),
        )
        if aliased_text:
            payload["gm_text"] = aliased_text
    if not str(payload.get("system_log") or "").strip():
        aliased_log = _first_string_alias(payload, ("log", "system", "system_message", "event_log"))
        if aliased_log:
            payload["system_log"] = aliased_log
    if "choices" not in payload:
        aliased_choices = _first_alias(payload, ("options", "actions", "next_actions", "choice_options"))
        if isinstance(aliased_choices, list):
            payload["choices"] = aliased_choices
    if "state_delta" not in payload:
        aliased_delta = _first_alias(payload, ("state", "delta", "state_changes", "updates"))
        if isinstance(aliased_delta, dict):
            payload["state_delta"] = aliased_delta

    if "state_delta" not in payload:
        payload["state_delta"] = {}
    delta = payload["state_delta"]
    if not isinstance(delta, dict):
        payload["state_delta"] = {}
        delta = payload["state_delta"]
    for key in ("hp_change", "mp_change", "sp_change", "gold", "gold_change",
                "inventory_add", "inventory_remove", "current_scene"):
        if key in payload and key not in delta:
            delta[key] = payload.pop(key)
    return payload


def _unwrap_payload_container(payload: dict[str, Any]) -> dict[str, Any]:
    if _looks_like_gm_payload(payload):
        return payload
    for key in ("response", "result", "output", "data", "message"):
        value = payload.get(key)
        if isinstance(value, dict) and _looks_like_gm_payload(value):
            merged = dict(value)
            for outer_key, outer_value in payload.items():
                if outer_key != key and outer_key not in merged:
                    merged[outer_key] = outer_value
            return merged
    return payload


def _looks_like_gm_payload(payload: dict[str, Any]) -> bool:
    keys = {
        "gm_text", "scenario_text", "narration", "narrative", "text", "content",
        "system_log", "state_delta", "choices", "options", "actions",
    }
    return any(key in payload for key in keys)


def _first_alias(payload: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        if alias in payload:
            return payload[alias]
    return None


def _first_string_alias(payload: dict[str, Any], aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        value = payload.get(alias)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            nested = _first_string_alias(
                value,
                ("gm_text", "scenario_text", "narration", "narrative", "text", "content", "message", "response"),
            )
            if nested:
                return nested
    return ""


def _merge_recovered_choices(payload: dict[str, Any], choices: list[dict[str, str]]) -> None:
    existing = payload.get("choices")
    if choices and (
        not isinstance(existing, list)
        or not existing
        or (len(choices) >= 2 and len(existing) < len(choices))
    ):
        payload["choices"] = choices


def _payload_from_recovered_choices(choices: list[dict[str, str]]) -> Optional[dict[str, Any]]:
    if not choices:
        return None
    return {"system_log": "", "state_delta": {}, "choices": choices}


def _recover_payload_from_malformed_json(text: str) -> Optional[dict[str, Any]]:
    gm_text = _extract_json_string_field(text, "gm_text") or _extract_json_string_field(text, "scenario_text")
    if not gm_text:
        gm_text = _extract_json_string_field(text, "narration") or _extract_json_string_field(text, "content")
    if not gm_text:
        return None
    payload: dict[str, Any] = {
        "gm_text": gm_text,
        "system_log": _extract_json_string_field(text, "system_log") or _extract_json_string_field(text, "log"),
        "state_delta": {},
    }
    choices = extract_text_choices(gm_text)
    if choices:
        payload["choices"] = choices
    return _normalize_payload(payload)


def _extract_json_string_field(text: str, field: str) -> str:
    match = re.search(rf'"{re.escape(field)}"\s*:\s*"', text)
    if not match:
        return ""
    index = match.end()
    chars: list[str] = []
    escaped = False
    while index < len(text):
        char = text[index]
        if escaped:
            chars.append("\\" + char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            break
        else:
            chars.append(char)
        index += 1
    raw_value = "".join(chars)
    try:
        return str(json.loads(f'"{raw_value}"'))
    except json.JSONDecodeError:
        return raw_value.replace("\\n", "\n").replace('\\"', '"')


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
        "する", "向かう", "進む", "聞く", "探す", "調べる", "使う", "話す",
        "出発", "購入", "訪ねる", "収集", "入る", "戻る", "攻撃", "確認",
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


def _parse_json_object(text: str) -> Optional[dict[str, Any]]:
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


def _extract_last_json_object(text: str) -> Optional[str]:
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
