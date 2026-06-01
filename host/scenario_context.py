from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional


DEFAULT_SCENE_ID = "start"
DEFAULT_FALLBACK_CHOICES = [
    {"text": "周囲を詳しく調べる", "preview": "手がかりや危険を探します", "risk": "判定が必要な場合があります"},
    {"text": "近くの人物に話を聞く", "preview": "状況を整理できるかもしれません", "risk": "判定不要"},
    {"text": "装備と持ち物を確認する", "preview": "次の行動に備えます", "risk": "判定不要"},
]

ENTITY_GROUPS = ("locations", "npcs", "items", "clues")


def load_scenario_pack(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict):
            raise ValueError(f"Scenario JSON must be an object: {path}")
        return normalize_scenario_pack(raw, path)
    return legacy_text_pack(path)


def legacy_text_pack(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    return normalize_scenario_pack(
        {
            "meta": {
                "title": path.stem,
                "summary": "Legacy plain-text scenario.",
                "language": "ja",
                "initial_scene": DEFAULT_SCENE_ID,
            },
            "rules": [],
            "scenes": [
                {
                    "id": DEFAULT_SCENE_ID,
                    "title": "開始",
                    "description": text,
                    "goals": [],
                    "keywords": [],
                    "fallback_choices": DEFAULT_FALLBACK_CHOICES,
                }
            ],
            "locations": [],
            "npcs": [],
            "items": [],
            "clues": [],
            "fallback_choices": DEFAULT_FALLBACK_CHOICES,
        },
        path,
    )


def normalize_scenario_pack(raw: dict[str, Any], path: Optional[Path] = None) -> dict[str, Any]:
    meta_raw = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
    meta = {key: deepcopy(value) for key, value in meta_raw.items()}
    meta.update({
        "title": str(meta_raw.get("title") or raw.get("title") or (path.stem if path else "scenario")),
        "summary": str(meta_raw.get("summary") or raw.get("summary") or ""),
        "language": str(meta_raw.get("language") or raw.get("language") or "ja"),
        "initial_scene": str(
            meta_raw.get("initial_scene")
            or (raw.get("initial_state_hints") or {}).get("current_scene")
            or DEFAULT_SCENE_ID
        ),
    })
    scenes = _normalize_records(raw.get("scenes"), default_id=DEFAULT_SCENE_ID)
    if not scenes:
        scenes = [
            {
                "id": DEFAULT_SCENE_ID,
                "title": "開始",
                "description": str(raw.get("gm_prompt") or raw.get("summary") or ""),
                "goals": [],
                "keywords": [],
                "fallback_choices": [],
            }
        ]
    initial_scene = _find_scene(scenes, meta["initial_scene"])
    if initial_scene:
        meta["initial_scene"] = str(initial_scene.get("id"))
    else:
        meta["initial_scene"] = str(scenes[0]["id"])

    pack = {
        "meta": meta,
        "rules": [str(rule) for rule in _as_list(raw.get("rules"))],
        "scenes": scenes,
        "fallback_choices": normalize_choices(raw.get("fallback_choices")) or DEFAULT_FALLBACK_CHOICES,
        "source_path": str(path) if path else "",
    }
    for group in ENTITY_GROUPS:
        pack[group] = _normalize_records(raw.get(group))
    return pack


def select_scenario_context(session: dict[str, Any], player_text: str = "") -> dict[str, Any]:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return {}

    current_scene = str(session.get("current_scene") or pack.get("meta", {}).get("initial_scene") or DEFAULT_SCENE_ID)
    scene = find_scene(pack, current_scene) or (pack.get("scenes") or [{}])[0]
    searchable_text = " ".join(
        part
        for part in (
            player_text,
            _latest_user_text(session),
            str(scene.get("id", "")),
            str(scene.get("title", "")),
            str(scene.get("description", "")),
        )
        if part
    )

    matched: dict[str, list[dict[str, Any]]] = {}
    for group in ENTITY_GROUPS:
        explicit_ids = _as_text_list(scene.get(f"{group[:-1]}_ids") or scene.get(f"{group}_ids"))
        matched[group] = [
            _public_record(record)
            for record in pack.get(group, [])
            if _record_matches(record, searchable_text) or str(record.get("id", "")) in explicit_ids
        ][:6]

    context = {
        "meta": pack.get("meta", {}),
        "rules": pack.get("rules", []),
        "current_scene": _public_record(scene),
        "matched": matched,
        "fallback_choices": fallback_choices_for_scene(pack, current_scene),
    }
    return context


def fallback_choices_for_session(session: dict[str, Any]) -> list[dict[str, str]]:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return deepcopy(DEFAULT_FALLBACK_CHOICES)
    return fallback_choices_for_scene(pack, str(session.get("current_scene") or ""))


def fallback_choices_for_scene(pack: dict[str, Any], scene_id: str) -> list[dict[str, str]]:
    scene = find_scene(pack, scene_id)
    if scene:
        choices = normalize_choices(scene.get("fallback_choices") or scene.get("choice_seeds"))
        if choices:
            return choices
    return normalize_choices(pack.get("fallback_choices")) or deepcopy(DEFAULT_FALLBACK_CHOICES)


def resolve_scene_id(pack: dict[str, Any], value: str) -> str:
    scene = find_scene(pack, value)
    return str(scene.get("id")) if scene else value


def infer_scene_from_text(session: dict[str, Any], text: str) -> Optional[str]:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict) or not text:
        return None
    for scene in pack.get("scenes", []):
        if _record_matches(scene, text):
            return str(scene.get("id"))
    return None


def scene_title(session: dict[str, Any]) -> str:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return str(session.get("current_scene") or "")
    scene = find_scene(pack, str(session.get("current_scene") or ""))
    if scene:
        return str(scene.get("title") or scene.get("id") or "")
    return str(session.get("current_scene") or "")


def scenario_context_debug(context: dict[str, Any]) -> dict[str, Any]:
    matched = context.get("matched") if isinstance(context.get("matched"), dict) else {}
    return {
        "chars": len(json.dumps(context, ensure_ascii=False)),
        "scene": (context.get("current_scene") or {}).get("id") if isinstance(context.get("current_scene"), dict) else "",
        "matches": {key: [str(item.get("id") or item.get("name") or item.get("title")) for item in value] for key, value in matched.items()},
    }


def find_scene(pack: dict[str, Any], scene_id_or_title: str) -> Optional[dict[str, Any]]:
    return _find_scene(pack.get("scenes") or [], scene_id_or_title)


def normalize_choices(raw: Any) -> list[dict[str, str]]:
    choices: list[dict[str, str]] = []
    for item in _as_list(raw):
        if isinstance(item, str):
            text = item.strip()
            if text:
                choices.append({"text": text, "preview": "", "risk": ""})
        elif isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if text:
                choices.append({
                    "text": text,
                    "preview": str(item.get("preview") or ""),
                    "risk": str(item.get("risk") or ""),
                })
    return choices[:5]


def _normalize_records(raw: Any, default_id: Optional[str] = None) -> list[dict[str, Any]]:
    records = []
    for index, item in enumerate(_as_list(raw)):
        if not isinstance(item, dict):
            continue
        record = deepcopy(item)
        fallback_id = default_id if index == 0 and default_id else f"entry_{index + 1}"
        record["id"] = str(record.get("id") or record.get("title") or record.get("name") or fallback_id)
        record["title"] = str(record.get("title") or record.get("name") or record["id"])
        record["description"] = str(record.get("description") or record.get("summary") or "")
        record["keywords"] = _as_text_list(record.get("keywords"))
        if "goals" in record:
            record["goals"] = _as_text_list(record.get("goals"))
        if "fallback_choices" in record or "choice_seeds" in record:
            record["fallback_choices"] = normalize_choices(record.get("fallback_choices") or record.get("choice_seeds"))
        records.append(record)
    return records


def _find_scene(scenes: list[dict[str, Any]], scene_id_or_title: str) -> Optional[dict[str, Any]]:
    value = str(scene_id_or_title or "")
    for scene in scenes:
        if value in (str(scene.get("id")), str(scene.get("title"))):
            return scene
    return None


def _record_matches(record: dict[str, Any], text: str) -> bool:
    if not text:
        return False
    needles = [str(record.get("id", "")), str(record.get("title", "")), str(record.get("name", ""))]
    needles.extend(_as_text_list(record.get("keywords")))
    return any(needle and needle in text for needle in needles)


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "id", "title", "name", "description", "summary", "goals", "keywords",
        "fallback_choices", "preview", "risk", "effect",
    )
    return {key: deepcopy(record[key]) for key in allowed if key in record}


def _latest_user_text(session: dict[str, Any]) -> str:
    for message in reversed(session.get("messages", [])):
        if message.get("role") == "user":
            return str(message.get("text") or "")
    return ""


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _as_text_list(value: Any) -> list[str]:
    return [str(item).strip() for item in _as_list(value) if str(item).strip()]
