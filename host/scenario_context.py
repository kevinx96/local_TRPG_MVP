from __future__ import annotations

import json
import re
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
_ENTITY_ID_KEYS = {"npcs": "npc_ids", "items": "item_ids", "clues": "clue_ids", "enemies": "enemy_ids"}


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
    if isinstance(raw.get("enemies"), list):
        pack["enemies"] = [_normalize_enemy_record(e) for e in raw["enemies"] if isinstance(e, dict)]
    else:
        pack["enemies"] = []
    if isinstance(raw.get("combat_choices"), list):
        pack["combat_choices"] = normalize_choices(raw["combat_choices"])
    else:
        pack["combat_choices"] = []
    if isinstance(raw.get("attribute_defs"), list):
        pack["attribute_defs"] = [
            {"id": str(a.get("id", "")), "name": str(a.get("name", "")), "initial_value": _safe_number(a.get("initial_value"), 8)}
            for a in raw["attribute_defs"] if isinstance(a, dict) and a.get("id")
        ]
    else:
        pack["attribute_defs"] = []
    if isinstance(raw.get("characters"), list):
        pack["characters"] = [_normalize_character_record(c) for c in raw["characters"] if isinstance(c, dict)]
    else:
        pack["characters"] = []
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
        )
        if part
    )

    matched: dict[str, list[dict[str, Any]]] = {}
    max_matched = 3 if session.get("gm_mode") == "full" else 6
    location_ids = _as_text_list(scene.get("location_ids"))
    explicit_entity_ids: dict[str, set[str]] = {group: set() for group in (*ENTITY_GROUPS, "enemies")}
    for group, id_key in _ENTITY_ID_KEYS.items():
        for eid in _as_text_list(scene.get(id_key)):
            explicit_entity_ids[group].add(eid)
    for loc_id in location_ids:
        explicit_entity_ids["locations"].add(loc_id)
    for location in pack.get("locations", []):
        if not isinstance(location, dict) or str(location.get("id", "")) not in location_ids:
            continue
        for group, id_key in _ENTITY_ID_KEYS.items():
            for eid in _as_text_list(location.get(id_key)):
                explicit_entity_ids[group].add(eid)
    for group in ENTITY_GROUPS:
        matched[group] = _matched_records(
            pack,
            group,
            searchable_text,
            explicit_entity_ids.get(group, set()),
            max_matched,
            slim_location=(group == "locations"),
        )
    matched["enemies"] = _matched_records(
        pack,
        "enemies",
        searchable_text,
        explicit_entity_ids.get("enemies", set()),
        max_matched,
    )

    context: dict[str, Any] = {
        "meta": pack.get("meta", {}),
        "rules": pack.get("rules", []),
        "current_scene": _trim_record(_public_record(scene)),
        "matched": matched,
        "available_actions": _trim_choices(current_action_choices(session)),
        "fallback_choices": _trim_choices(_merged_choices_for_context(pack, current_scene, str(session.get("current_location") or ""))),
    }
    # Semi mode: inject hybrid hints if available so the LLM has narrative scaffolding
    hybrid = scene.get("hybrid") if isinstance(scene.get("hybrid"), dict) else None
    if session.get("gm_mode") == "semi" and hybrid:
        prepared = select_hybrid_prepared_turn(session, player_text, opening=not bool(player_text))
        if prepared and isinstance(prepared.get("draft"), dict):
            hint_text = str(prepared["draft"].get("gm_text") or "")[:600]
            if hint_text:
                context["narrative_hint"] = hint_text
                context["hint_choices"] = prepared["draft"].get("choices", [])
    return context


def select_hybrid_context(
    session: dict[str, Any],
    player_text: str = "",
    opening: bool = False,
    include_debug: bool = False,
) -> dict[str, Any]:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return {}

    current_scene = str(session.get("current_scene") or pack.get("meta", {}).get("initial_scene") or DEFAULT_SCENE_ID)
    scene = find_scene(pack, current_scene) or (pack.get("scenes") or [{}])[0]
    location_id = str(session.get("current_location") or "")
    location = _find_location_in_pack(pack, location_id) or {}
    prepared_turn = select_hybrid_prepared_turn(session, player_text, opening=opening)
    meta = pack.get("meta", {})
    context = {
        "meta": meta,
        "current_scene": {
            "id": scene.get("id"),
            "title": scene.get("title"),
            "description": scene.get("description"),
            "goals": scene.get("goals", []),
        },
        "current_location": {
            "id": location.get("id"),
            "title": location.get("title"),
        },
        "prepared_turn": _prepared_turn_for_llm(prepared_turn, str(meta.get("language") or "")),
        "action_result": session.get("last_action_result", {}),
        "available_actions": _trim_choices(current_action_choices(session)),
        "fallback_choices": _trim_choices(_merged_choices_for_context(pack, current_scene, location_id)),
    }
    if include_debug:
        context["_debug"] = {
            "prepared_turn": str(prepared_turn.get("id") or "") if isinstance(prepared_turn, dict) else "",
            "purpose": str(prepared_turn.get("purpose") or "") if isinstance(prepared_turn, dict) else "",
        }
    return context


def has_hybrid_prepared_turn(session: dict[str, Any], player_text: str = "", opening: bool = False) -> bool:
    prepared = select_hybrid_prepared_turn(session, player_text, opening=opening)
    draft = prepared.get("draft") if isinstance(prepared.get("draft"), dict) else {}
    return bool(
        str(draft.get("gm_text") or "").strip()
        or str(draft.get("system_log") or "").strip()
        or draft.get("choices")
    )


def select_hybrid_prepared_turn(session: dict[str, Any], player_text: str = "", opening: bool = False) -> dict[str, Any]:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return {}
    location_id = str(session.get("current_location") or "")
    location = _find_location_in_pack(pack, location_id)
    if not location:
        return {}
    hybrid = location.get("hybrid") if isinstance(location.get("hybrid"), dict) else {}
    prepared_turns = hybrid.get("prepared_turns") if isinstance(hybrid.get("prepared_turns"), list) else []
    if not prepared_turns:
        return _legacy_dialogue_turn_as_prepared(hybrid, opening)

    if opening:
        for turn in prepared_turns:
            if _turn_purpose(turn) == "opening":
                return deepcopy(turn)
        return deepcopy(prepared_turns[0]) if prepared_turns else {}

    action_result = session.get("last_action_result") if isinstance(session.get("last_action_result"), dict) else {}
    action_id = str(action_result.get("action_id") or "")
    outcome = str(action_result.get("outcome") or "")
    if action_id:
        exact_matches = [
            turn for turn in prepared_turns
            if isinstance(turn, dict)
            and str(turn.get("action_id") or turn.get("prepared_turn_id") or "") == action_id
            and (not str(turn.get("outcome") or "") or str(turn.get("outcome") or "") == outcome)
        ]
        if exact_matches:
            return deepcopy(exact_matches[0])

    searchable_text = player_text.strip() or _latest_user_text(session)
    latest_outcome = _latest_roll_outcome(session)
    scored = [
        (_prepared_turn_score(turn, searchable_text, latest_outcome), index, turn)
        for index, turn in enumerate(prepared_turns)
    ]
    scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    if scored and scored[0][0] > 0:
        return deepcopy(scored[0][2])
    return {}


def fallback_choices_for_session(session: dict[str, Any]) -> list[dict[str, str]]:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return deepcopy(DEFAULT_FALLBACK_CHOICES)
    action_choices = current_action_choices(session)
    if action_choices:
        return action_choices
    return fallback_choices_for_scene(pack, str(session.get("current_scene") or ""))


def current_actions_for_session(session: dict[str, Any]) -> list[dict[str, Any]]:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict):
        return []
    current_scene = str(session.get("current_scene") or "")
    location_id = str(session.get("current_location") or "")
    scene = find_scene(pack, current_scene)
    location = _find_location_in_pack(pack, location_id)
    actions: list[dict[str, Any]] = []
    for source in (scene, location):
        if isinstance(source, dict):
            actions.extend(normalize_actions(source.get("actions")))
    if actions:
        return _dedupe_actions(actions)
    return []


def current_action_choices(session: dict[str, Any]) -> list[dict[str, Any]]:
    return [_action_as_choice(action) for action in current_actions_for_session(session)]


def fallback_choices_for_scene(pack: dict[str, Any], scene_id: str) -> list[dict[str, str]]:
    scene = find_scene(pack, scene_id)
    if _scene_has_enemies(pack, scene):
        combat = normalize_choices(pack.get("combat_choices"))
        if combat:
            return combat
    if scene:
        choices = normalize_choices(scene.get("fallback_choices") or scene.get("choice_seeds"))
        if choices:
            return choices
    return normalize_choices(pack.get("fallback_choices")) or deepcopy(DEFAULT_FALLBACK_CHOICES)


def _merged_choices_for_context(pack: dict[str, Any], scene_id: str, location_id: str) -> list[dict[str, Any]]:
    if not location_id:
        return _global_fallback_choices(pack)
    location = _find_location_in_pack(pack, location_id)
    if not location:
        return _global_fallback_choices(pack)
    location_choices = normalize_choices(location.get("choices") or [])
    if location_choices:
        return location_choices
    return _global_fallback_choices(pack)


def _global_fallback_choices(pack: dict[str, Any]) -> list[dict[str, Any]]:
    return normalize_choices(pack.get("fallback_choices")) or deepcopy(DEFAULT_FALLBACK_CHOICES)


def _find_location_in_pack(pack: dict[str, Any], location_id: str) -> Optional[dict[str, Any]]:
    for loc in pack.get("locations", []):
        if isinstance(loc, dict) and str(loc.get("id") or "") == location_id:
            return loc
    return None


def _scene_has_enemies(pack: dict[str, Any], scene: Optional[dict[str, Any]]) -> bool:
    if not scene:
        return False
    location_ids = _as_text_list(scene.get("location_ids")) if scene else []
    for loc in pack.get("locations", []):
        if str(loc.get("id", "")) in location_ids:
            if _as_text_list(loc.get("enemy_ids")):
                return True
    return False


def resolve_scene_id(pack: dict[str, Any], value: str) -> str:
    scene = find_scene(pack, value)
    if scene:
        return str(scene.get("id"))
    for s in pack.get("scenes", []):
        if not isinstance(s, dict):
            continue
        loc_ids = _as_text_list(s.get("location_ids"))
        if value in loc_ids or value.replace("_loc", "") in loc_ids:
            return str(s.get("id"))
    return value


def infer_scene_from_text(session: dict[str, Any], text: str) -> Optional[str]:
    pack = session.get("scenario_pack")
    if not isinstance(pack, dict) or not text:
        return None
    for scene in pack.get("scenes", []):
        if _record_matches(scene, text):
            return str(scene.get("id"))
    for scene in pack.get("scenes", []):
        for loc_id in _as_text_list(scene.get("location_ids", [])):
            loc = None
            for location in pack.get("locations", []):
                if isinstance(location, dict) and str(location.get("id", "")) == loc_id:
                    loc = location
                    break
            if loc and _record_matches(loc, text):
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


def hybrid_context_debug(context: dict[str, Any]) -> dict[str, Any]:
    prepared = context.get("prepared_turn") if isinstance(context.get("prepared_turn"), dict) else {}
    debug = context.get("_debug") if isinstance(context.get("_debug"), dict) else {}
    llm_context = {key: value for key, value in context.items() if key != "_debug"}
    return {
        "chars": len(json.dumps(llm_context, ensure_ascii=False)),
        "scene": (context.get("current_scene") or {}).get("id") if isinstance(context.get("current_scene"), dict) else "",
        "prepared_turn": debug.get("prepared_turn") or prepared.get("id", ""),
        "purpose": debug.get("purpose") or prepared.get("purpose", ""),
    }


def _prepared_turn_for_llm(turn: Any, language: str = "") -> dict[str, Any]:
    if not isinstance(turn, dict):
        return {}
    draft = turn.get("draft") if isinstance(turn.get("draft"), dict) else {}
    result: dict[str, Any] = {
        "draft": {
            "gm_text": draft.get("gm_text", ""),
            "system_log": draft.get("system_log", ""),
            "dice_type": draft.get("dice_type", "null"),
            "dice_dc": draft.get("dice_dc", 0),
            "state_delta": draft.get("state_delta", {}),
            "choices": draft.get("choices", []),
        },
    }
    notes = _as_text_list(turn.get("rewrite_notes"))
    if language.lower().startswith("ja"):
        notes = [note for note in notes if _contains_japanese(note)]
    if notes:
        result["rewrite_notes"] = notes
    return result


def _contains_japanese(text: str) -> bool:
    return any(
        "\u3040" <= char <= "\u30ff"
        or "\u3400" <= char <= "\u9fff"
        for char in text
    )


def find_scene(pack: dict[str, Any], scene_id_or_title: str) -> Optional[dict[str, Any]]:
    return _find_scene(pack.get("scenes") or [], scene_id_or_title)


def normalize_choices(raw: Any) -> list[dict[str, Any]]:
    choices: list[dict[str, Any]] = []
    for item in _as_list(raw):
        if isinstance(item, str):
            text = item.strip()
            if text:
                choices.append({"text": text, "preview": "", "risk": ""})
        elif isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if text:
                choice: dict[str, Any] = {
                    "text": text,
                    "preview": str(item.get("preview") or ""),
                    "risk": str(item.get("risk") or ""),
                }
                for key in (
                    "id", "action_id", "intent_keywords", "roll", "effects",
                    "success_effects", "failure_effects", "once", "disabled_after",
                    "prepared_turn_id", "outcome",
                ):
                    if key in item:
                        choice[key] = deepcopy(item[key])
                if "requirements" in item:
                    choice["requirements"] = deepcopy(item["requirements"])
                if "children" in item and isinstance(item["children"], list):
                    choice["children"] = normalize_choices(item["children"])
                choices.append(choice)
    return choices[:5]


def normalize_actions(raw: Any) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for index, item in enumerate(_as_list(raw)):
        if isinstance(item, str):
            text = item.strip()
            if text:
                actions.append({"id": f"action_{index + 1}", "text": text, "preview": "", "risk": ""})
            continue
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("label") or item.get("name") or "").strip()
        action_id = str(item.get("id") or item.get("action_id") or "").strip()
        if not text or not action_id:
            continue
        action = deepcopy(item)
        action["id"] = action_id
        action["text"] = text
        action["preview"] = str(action.get("preview") or "")
        action["risk"] = str(action.get("risk") or "")
        action["intent_keywords"] = _as_text_list(action.get("intent_keywords") or action.get("keywords"))
        actions.append(action)
    return actions[:12]


def _legacy_choice_as_action(choice: dict[str, Any], fallback_id: str) -> dict[str, Any]:
    action = deepcopy(choice)
    action["id"] = str(action.get("id") or action.get("action_id") or fallback_id)
    action["action_id"] = action["id"]
    action["intent_keywords"] = _as_text_list(action.get("intent_keywords"))
    return action


def _action_as_choice(action: dict[str, Any]) -> dict[str, Any]:
    choice = deepcopy(action)
    action_id = str(choice.get("id") or choice.get("action_id") or "")
    choice["id"] = action_id
    choice["action_id"] = action_id
    if isinstance(choice.get("roll"), dict):
        roll = choice["roll"]
        dice = str(roll.get("dice_type") or roll.get("dice") or "1d20")
        dc = roll.get("dc", roll.get("dice_dc", 0))
        choice["risk"] = str(choice.get("risk") or (f"{dice}判定 (DC{int(dc)})" if isinstance(dc, (int, float)) and int(dc) > 0 else "判定不要"))
    return choice


def _dedupe_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for action in actions:
        action_id = str(action.get("id") or action.get("action_id") or "")
        if not action_id or action_id in seen:
            continue
        seen.add(action_id)
        result.append(action)
    return result


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
        if "choices" in record:
            record["choices"] = normalize_choices(record.get("choices"))
        if "actions" in record:
            record["actions"] = normalize_actions(record.get("actions"))
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
    return any(_text_contains_needle(text, needle) for needle in needles)


def _text_contains_needle(text: str, needle: str) -> bool:
    needle = str(needle or "").strip()
    if not needle:
        return False
    if re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_-]*", needle):
        return re.search(rf"(?<![A-Za-z0-9_-]){re.escape(needle)}(?![A-Za-z0-9_-])", text, re.IGNORECASE) is not None
    return needle in text


def _matched_records(
    pack: dict[str, Any],
    group: str,
    searchable_text: str,
    explicit_ids: set[str],
    limit: int,
    slim_location: bool = False,
) -> list[dict[str, Any]]:
    explicit_matches: list[dict[str, Any]] = []
    keyword_matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    records = pack.get(group, [])
    if not isinstance(records, list):
        return []

    for record in records:
        if not isinstance(record, dict):
            continue
        record_id = str(record.get("id", ""))
        if record_id in explicit_ids:
            explicit_matches.append(_trim_record(_public_record(record), slim_location))
            seen.add(record_id)

    for record in records:
        if not isinstance(record, dict):
            continue
        record_id = str(record.get("id", ""))
        if record_id not in seen and _record_matches(record, searchable_text):
            keyword_matches.append(_trim_record(_public_record(record), slim_location))
            seen.add(record_id)

    effective_limit = max(limit, len(explicit_matches))
    return [*explicit_matches, *keyword_matches][:effective_limit]


def _trim_record(record: dict[str, Any], slim_location: bool = False) -> dict[str, Any]:
    trimmed: dict[str, Any] = {}
    for key in ("id", "title", "name", "effect"):
        if key in record and record[key]:
            trimmed[key] = record[key]
    if not slim_location and "description" in record and record["description"]:
        trimmed["description"] = record["description"]
    if "goals" in record and record["goals"]:
        trimmed["goals"] = record["goals"]
    for key in ("hp", "max_hp", "mp", "max_mp", "sp", "max_sp"):
        if key in record:
            trimmed[key] = record[key]
    if "attributes" in record and record["attributes"]:
        trimmed["attributes"] = record["attributes"]
    if "skills" in record and record["skills"]:
        trimmed["skills"] = [
            {k: v for k, v in skill.items() if k in ("name", "effect", "dice_type", "cost", "cost_type")}
            for skill in record["skills"] if isinstance(skill, dict)
        ]
    if "fallback_choices" in record and record["fallback_choices"]:
        trimmed["fallback_choices"] = _trim_choices(record["fallback_choices"])
    return trimmed


def _trim_choices(choices: list[dict[str, str]]) -> list[dict[str, Any]]:
    trimmed = []
    for choice in choices:
        if not choice.get("text"):
            continue
        item: dict[str, Any] = {"text": choice.get("text", ""), "risk": choice.get("risk", "")}
        for key in (
            "id", "action_id", "intent_keywords", "roll", "effects",
            "success_effects", "failure_effects", "requirements",
            "once", "disabled_after", "prepared_turn_id", "outcome",
        ):
            if key in choice:
                item[key] = deepcopy(choice[key])
        if choice.get("preview"):
            item["preview"] = choice["preview"]
        if "children" in choice and isinstance(choice.get("children"), list):
            item["children"] = _trim_choices(choice["children"])
        trimmed.append(item)
    return trimmed


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "id", "title", "name", "description", "summary", "goals", "keywords",
        "fallback_choices", "preview", "risk", "effect",
        "hp", "max_hp", "mp", "max_mp", "sp", "max_sp", "attributes", "skills",
        "actions", "choices",
    )
    result = {key: deepcopy(record[key]) for key in allowed if key in record}
    result.pop("keywords", None)
    result.pop("preview", None)
    return result


def _latest_user_text(session: dict[str, Any]) -> str:
    for message in reversed(session.get("messages", [])):
        if message.get("role") == "user":
            return str(message.get("text") or "")
    return ""


def _latest_assistant_text(session: dict[str, Any]) -> str:
    for message in reversed(session.get("messages", [])):
        if message.get("role") == "assistant":
            return str(message.get("text") or "")
    return ""


def _turn_purpose(turn: Any) -> str:
    return str(turn.get("purpose") or "").strip().lower() if isinstance(turn, dict) else ""


def _prepared_turn_score(turn: Any, text: str, latest_outcome: str = "") -> int:
    if not isinstance(turn, dict) or not text:
        return 0
    score = 0
    # Exact choice-text match gets highest priority (+10)
    source_choice = str(turn.get("source_choice") or "").strip()
    if source_choice and source_choice == text.strip():
        score += 10
    elif source_choice and _text_contains_needle(text, source_choice):
        score += 3
    # Keyword matches
    for keyword in _as_text_list(turn.get("trigger_keywords")):
        if _text_contains_needle(text, keyword):
            score += 2
    # Player intent
    intent = str(turn.get("player_intent") or "")
    if intent and _text_contains_needle(text, intent):
        score += 1
    turn_outcome = _turn_outcome_hint(turn)
    if latest_outcome and turn_outcome:
        score += 6 if latest_outcome == turn_outcome else -6
    return score


def _latest_roll_outcome(session: dict[str, Any]) -> str:
    dice_log = session.get("dice_log")
    if not isinstance(dice_log, list) or not dice_log:
        return ""
    latest = dice_log[-1]
    if not isinstance(latest, dict):
        return ""
    dc = latest.get("dc")
    if not isinstance(dc, (int, float)) or int(dc) <= 0:
        return ""
    success = latest.get("success")
    if isinstance(success, bool):
        return "success" if success else "fail"
    total = latest.get("total")
    if isinstance(total, (int, float)):
        return "success" if int(total) >= int(dc) else "fail"
    return ""


def _turn_outcome_hint(turn: dict[str, Any]) -> str:
    source = " ".join(
        str(turn.get(key) or "").lower()
        for key in ("id", "purpose", "player_intent")
    )
    if any(token in source for token in ("success", "succeed", "passed", "成功")):
        return "success"
    if any(token in source for token in ("fail", "failed", "failure", "失敗")):
        return "fail"
    return ""


def _legacy_dialogue_turn_as_prepared(hybrid: dict[str, Any], opening: bool) -> dict[str, Any]:
    turns = hybrid.get("dialogue_turns") if isinstance(hybrid.get("dialogue_turns"), list) else []
    if not turns:
        return {}
    source = turns[0]
    if not isinstance(source, dict):
        return {}
    return {
        "id": str(source.get("id") or ("opening" if opening else "legacy_turn")),
        "purpose": "opening" if opening else "choice_response",
        "source_choice": "",
        "player_intent": "",
        "trigger_keywords": _as_text_list(source.get("trigger_keywords")),
        "draft": {
            "gm_text": str(source.get("gm_text") or source.get("text") or hybrid.get("opening") or ""),
            "system_log": "",
            "dice_type": "1d20",
            "dice_dc": 10,
            "state_delta": source.get("state_delta") if isinstance(source.get("state_delta"), dict) else {},
            "choices": normalize_choices(source.get("choices")),
        },
        "rewrite_notes": ["Legacy dialogue_turn converted to prepared_turn for compatibility."],
    }


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _as_text_list(value: Any) -> list[str]:
    return [str(item).strip() for item in _as_list(value) if str(item).strip()]


def _safe_number(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_character_record(raw: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": str(raw.get("id", "")),
        "name": str(raw.get("name", "")),
        "default_name": str(raw.get("default_name") or raw.get("name") or ""),
        "description": str(raw.get("description", "")),
        "image": str(raw.get("image", "")) if raw.get("image") else "",
    }
    if raw.get("image_female"):
        record["image_female"] = str(raw["image_female"])
    for stat in ("hp", "max_hp", "mp", "max_mp", "sp", "max_sp", "gold"):
        record[stat] = _safe_number(raw.get(stat), 0)
    attrs = raw.get("attributes")
    record["attributes"] = {str(k): _safe_number(v, 0) for k, v in attrs.items()} if isinstance(attrs, dict) else {}
    if isinstance(raw.get("inventory"), list):
        record["inventory"] = deepcopy(raw["inventory"])
    else:
        record["inventory"] = []
    if isinstance(raw.get("equipment"), list):
        record["equipment"] = _as_text_list(raw["equipment"])
    else:
        record["equipment"] = []
    if isinstance(raw.get("skills"), list):
        record["skills"] = deepcopy(raw["skills"])
    else:
        record["skills"] = []
    return record


def _normalize_enemy_record(raw: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": str(raw.get("id", "")),
        "name": str(raw.get("name", "")),
        "description": str(raw.get("description", "")),
        "image": str(raw.get("image", "")) if raw.get("image") else "",
    }
    for stat in ("hp", "max_hp", "mp", "max_mp", "sp", "max_sp"):
        record[stat] = _safe_number(raw.get(stat), 0)
    attrs = raw.get("attributes")
    record["attributes"] = {str(k): _safe_number(v, 0) for k, v in attrs.items()} if isinstance(attrs, dict) else {}
    if isinstance(raw.get("skills"), list):
        record["skills"] = deepcopy(raw["skills"])
    else:
        record["skills"] = []
    return record
