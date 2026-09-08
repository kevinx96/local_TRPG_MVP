from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from typing import Any, Optional


MIN_SEMANTIC_SCORE = 0.66
AMBIGUITY_MARGIN = 0.08

_PARTICLE_RE = re.compile(r"(?:について|に対して|へ|に|を|で|と|から|まで|の|が|は|も)")
_SCRIPT_TERM_RE = re.compile(r"[A-Za-z0-9_-]+|[一-鿿々]+|[ァ-ヶー]+|[ぁ-ゖー]+")
_TRAILING_FORMS = (
    "してもらいたい",
    "してください",
    "してほしい",
    "してみたい",
    "してみる",
    "したい",
    "行ってみる",
    "行きたい",
    "向かいたい",
    "します",
    "する",
    "して",
    "した",
    "たい",
)
_GENERIC_TERMS = {
    "お願い",
    "行く",
    "向かう",
    "訪れる",
    "戻る",
    "進む",
    "見る",
    "見せる",
    "聞く",
    "話す",
    "調べる",
    "探す",
    "確認",
    "買う",
    "購入",
    "使う",
    "求める",
    "行動",
    "場所",
    "これ",
    "それ",
}
_GENERIC_FRAGMENTS = {
    "する",
    "した",
    "して",
    "たい",
    "ます",
    "行く",
    "向か",
    "聞く",
    "話す",
    "調べ",
    "買う",
    "から",
    "まで",
}
_GENERIC_FRAGMENT_PARTS = ("話を聞",)


def resolve_intent(
    actions: list[dict[str, Any]],
    player_text: str = "",
    action_id: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve input against an executable action surface without guessing ties."""
    wanted_id = str(action_id or "").strip()
    wanted_text = str(player_text or "").strip()

    if wanted_id:
        matches = [action for action in actions if wanted_id in _action_ids(action)]
        if len(matches) == 1:
            return _resolved(matches[0], "action_id", 1.0)
        return _unresolved("invalid_action_id", [], [])

    normalized_input = _compact(wanted_text)
    if not normalized_input:
        return _unresolved("unmatched", [], [])

    exact = [action for action in actions if normalized_input == _compact(action.get("text"))]
    if len(exact) == 1:
        return _resolved(exact[0], "exact_text", 1.0)
    if len(exact) > 1:
        return _unresolved("ambiguous", exact, [(action, 1.0) for action in exact])

    scored = sorted(
        ((action, _action_score(action, wanted_text)) for action in actions),
        key=lambda item: item[1],
        reverse=True,
    )
    scored = [(action, score) for action, score in scored if score > 0]
    if not scored or scored[0][1] < MIN_SEMANTIC_SCORE:
        return _unresolved("unmatched", [], scored)

    top_score = scored[0][1]
    contenders = [
        action
        for action, score in scored
        if score >= MIN_SEMANTIC_SCORE and top_score - score < AMBIGUITY_MARGIN
    ]
    if len(contenders) > 1:
        return _unresolved("ambiguous", contenders, scored)
    # Lexical overlap only supplies candidates. It cannot distinguish a method,
    # negation or conditional intent, so only explicit IDs / exact labels execute.
    return _unresolved("unmatched", [], scored)


def _resolved(
    action: dict[str, Any],
    method: str,
    confidence: float,
    scored: Optional[list[tuple[dict[str, Any], float]]] = None,
) -> dict[str, Any]:
    return {
        "status": "resolved",
        "method": method,
        "confidence": round(confidence, 3),
        "action_id": _primary_action_id(action),
        "candidate_action_ids": [_primary_action_id(action)],
        "scores": _public_scores(scored or [(action, confidence)]),
        "action": deepcopy(action),
    }


def _unresolved(
    status: str,
    candidates: list[dict[str, Any]],
    scored: list[tuple[dict[str, Any], float]],
) -> dict[str, Any]:
    candidate_records = candidates or ([action for action, _score in scored[:3]] if status == "unmatched" else [])
    return {
        "status": status,
        "method": "",
        "confidence": round(scored[0][1], 3) if scored else 0.0,
        "action_id": "",
        "candidate_action_ids": [_primary_action_id(action) for action in candidate_records if _primary_action_id(action)],
        "scores": _public_scores(scored),
        "action": None,
    }


def _public_scores(scored: list[tuple[dict[str, Any], float]]) -> list[dict[str, Any]]:
    return [
        {"action_id": _primary_action_id(action), "score": round(score, 3)}
        for action, score in scored[:5]
        if _primary_action_id(action)
    ]


def _action_score(action: dict[str, Any], player_text: str) -> float:
    sources = [str(action.get("text") or "")]
    keywords = action.get("intent_keywords")
    if isinstance(keywords, list):
        sources.extend(str(keyword) for keyword in keywords if str(keyword).strip())
    return max((_source_score(source, player_text) for source in sources), default=0.0)


def _source_score(source: str, player_text: str) -> float:
    source_compact = _compact(source)
    input_compact = _compact(player_text)
    if not source_compact or not input_compact:
        return 0.0
    if source_compact == input_compact:
        return 1.0
    shorter = min(len(source_compact), len(input_compact))
    if re.fullmatch(r"[a-z0-9_-]+", source_compact):
        source_contains_input = source_compact == input_compact
        input_contains_source = _contains_term(_normalize(player_text), source_compact)
    else:
        source_contains_input = input_compact in source_compact
        input_contains_source = source_compact in input_compact
    if shorter >= 2 and (input_contains_source or source_contains_input):
        ratio = shorter / max(len(source_compact), len(input_compact))
        return min(0.98, 0.88 + ratio * 0.1)

    terms = _meaningful_terms(source)
    matched = [term for term in terms if _contains_term(input_compact, term)]
    term_score = 0.0
    if matched:
        longest = max(len(term) for term in matched)
        coverage = sum(len(term) for term in matched) / max(1, sum(len(term) for term in terms))
        term_score = min(0.9, 0.58 + min(0.2, max(0, longest - 1) * 0.05) + coverage * 0.15)
    fragment = _longest_common_japanese_fragment(source_compact, input_compact)
    fragment_score = 0.0
    if fragment:
        ratio = len(fragment) / max(1, min(len(source_compact), len(input_compact)))
        fragment_score = min(0.86, 0.64 + min(0.12, max(0, len(fragment) - 2) * 0.04) + ratio * 0.1)
    return max(term_score, fragment_score)


def _meaningful_terms(text: str) -> list[str]:
    normalized = _normalize(text)
    chunks = _PARTICLE_RE.sub(" ", normalized)
    terms: list[str] = []
    for raw_chunk in _SCRIPT_TERM_RE.findall(chunks):
        chunk = _strip_trailing_form(raw_chunk)
        if len(chunk) < 2 or chunk in _GENERIC_TERMS:
            continue
        if chunk not in terms:
            terms.append(chunk)
    return terms


def _strip_trailing_form(term: str) -> str:
    for suffix in _TRAILING_FORMS:
        if term.endswith(suffix) and len(term) > len(suffix):
            return term[: -len(suffix)]
    return term


def _contains_term(text: str, term: str) -> bool:
    if re.fullmatch(r"[a-z0-9_-]+", term):
        return re.search(rf"(?<![a-z0-9_-]){re.escape(term)}(?![a-z0-9_-])", text) is not None
    return term in text


def _longest_common_japanese_fragment(left: str, right: str) -> str:
    if not left or not right:
        return ""
    previous = [0] * (len(right) + 1)
    best = ""
    for left_index, left_char in enumerate(left, start=1):
        current = [0] * (len(right) + 1)
        for right_index, right_char in enumerate(right, start=1):
            if left_char != right_char:
                continue
            current[right_index] = previous[right_index - 1] + 1
            length = current[right_index]
            if length > len(best):
                best = left[left_index - length:left_index]
        previous = current
    if len(best) < 2 or best in _GENERIC_FRAGMENTS or any(part in best for part in _GENERIC_FRAGMENT_PARTS):
        return ""
    if not re.search(r"[一-鿿々ァ-ヶ]", best):
        return ""
    return best


def _normalize(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().lower()


def _compact(value: Any) -> str:
    return re.sub(r"[^a-z0-9_\-ぁ-ゖァ-ヶー一-鿿々]+", "", _normalize(value))


def _action_ids(action: dict[str, Any]) -> set[str]:
    return {
        str(value).strip()
        for value in (action.get("id"), action.get("action_id"))
        if str(value or "").strip()
    }


def _primary_action_id(action: dict[str, Any]) -> str:
    return str(action.get("id") or action.get("action_id") or "").strip()
