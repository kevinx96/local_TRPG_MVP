from __future__ import annotations

import argparse
import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .gm_contract import build_gm_contract_prompt
from .scenario_context import load_scenario_pack, normalize_scenario_pack, scene_title
from .scenario_converter import load_gemini_api_key, parse_json_response
from .state import DEFAULT_CHARACTER, build_llm_messages


HOST_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = HOST_ROOT / "prompt" / "processed"
DEFAULT_SOURCE = PROCESSED_DIR / "dragon_rpg.json"
DEFAULT_OUTPUT = PROCESSED_DIR / "dragon_rpg_hybrid.json"
DEFAULT_MODELS = (
    os.environ.get("GEMINI_MODELS")
    or os.environ.get("GEMINI_MODEL")
    or "gemini-flash-latest,gemini-flash-lite-latest,gemini-2.5-flash,gemini-2.0-flash,gemini-1.5-flash"
)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a Semi/Hybrid prepared-response scenario pack from dragon_rpg.json with Gemini."
    )
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="Input scenario pack JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT), help="Output hybrid scenario pack JSON.")
    parser.add_argument("--model", default="", help="Single Gemini model name. Kept for compatibility.")
    parser.add_argument(
        "--models",
        default=DEFAULT_MODELS,
        help="Comma-separated Gemini fallback models. First available model wins.",
    )
    parser.add_argument("--start-scene", default="", help="Skip scenes until this scene id is reached.")
    parser.add_argument("--max-scenes", type=int, default=0, help="Process at most N scenes. 0 means all.")
    parser.add_argument("--force", action="store_true", help="Regenerate scenes that already have hybrid data.")
    parser.add_argument("--dry-run", action="store_true", help="Write prompts only; do not call Gemini.")
    parser.add_argument(
        "--prompt-dir",
        default=str(PROCESSED_DIR / ".hybrid_prompts"),
        help="Directory for prompt/raw Gemini debug files.",
    )
    args = parser.parse_args(argv)

    source = Path(args.source).resolve()
    output = Path(args.out).resolve()
    prompt_dir = Path(args.prompt_dir).resolve()

    source_pack = load_scenario_pack(source)
    hybrid_pack = _load_or_seed_output(source_pack, output)
    prompt_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    started = not bool(args.start_scene)
    for scene in source_pack.get("scenes", []):
        scene_id = str(scene.get("id") or "").strip()
        if not scene_id:
            continue
        if not started:
            started = scene_id == args.start_scene
            if not started:
                continue
        if args.max_scenes and processed >= args.max_scenes:
            break

        target_scene = _scene_by_id(hybrid_pack, scene_id)
        if target_scene and target_scene.get("hybrid") and not args.force:
            print(f"skip {scene_id}: hybrid data already exists")
            continue

        messages = build_scene_messages(source_pack, scene_id)
        prompt = build_gemini_prompt(messages, source_pack, scene)
        (prompt_dir / f"{scene_id}.prompt.txt").write_text(prompt, encoding="utf-8")
        print(f"scene {scene_id}: prompt_chars={len(prompt)}")

        if args.dry_run:
            processed += 1
            continue

        raw, payload = call_gemini_payload(
            prompt,
            model_names_from_args(args.model, args.models),
            raw_path_prefix=prompt_dir / scene_id,
        )
        (prompt_dir / f"{scene_id}.raw.txt").write_text(raw, encoding="utf-8")

        apply_hybrid_scene(hybrid_pack, scene_id, payload)
        _stamp_hybrid_meta(hybrid_pack, source)
        write_pack(output, hybrid_pack)
        print(f"scene {scene_id}: written {output}")
        processed += 1

    if args.dry_run:
        print(f"dry run complete: prompts written to {prompt_dir}")
    else:
        write_pack(output, hybrid_pack)
        print(f"hybrid scenario complete: {output}")
    return 0


def build_scene_messages(pack: dict[str, Any], scene_id: str) -> list[dict[str, str]]:
    scene = _scene_by_id(pack, scene_id)
    if not scene:
        raise ValueError(f"Unknown scene id: {scene_id}")
    session = {
        "id": "offline-hybrid-generation",
        "scenario_path": str(DEFAULT_SOURCE),
        "scenario_title": str(pack.get("meta", {}).get("title") or "scenario"),
        "gm_mode": "semi",
        "scenario_pack": pack,
        "current_scene": scene_id,
        "character": deepcopy(DEFAULT_CHARACTER),
        "messages": [
            {
                "role": "user",
                "speaker": "Player",
                "text": "Prepare the fixed Semi/Hybrid script material for this scene.",
                "created_at": _now(),
            }
        ],
        "system_logs": [],
        "dice_log": [],
        "choices": [],
        "next_dice_type": "1d20",
        "next_dice_dc": 10,
        "created_at": _now(),
        "updated_at": _now(),
    }
    latest_roll = {"expression": "offline", "rolls": [], "total": 0}
    return build_llm_messages(session, latest_roll, build_gm_contract_prompt())


def build_gemini_prompt(messages: list[dict[str, str]], pack: dict[str, Any], scene: dict[str, Any]) -> str:
    prompt_parts = [
        "The following messages are the same style of context currently sent to the local Ollama GM.",
        "Use them as source context to prepare reusable GM response payloads for this scene.",
        "Do not answer as a live session; produce offline pre-cooked turns that qwen can rewrite later.",
        "",
    ]
    for index, message in enumerate(messages, start=1):
        role = str(message.get("role") or "system").upper()
        content = str(message.get("content") or "")
        prompt_parts.append(f"--- {role} MESSAGE {index} ---")
        prompt_parts.append(content)
        prompt_parts.append("")

    prompt_parts.append("--- OFFLINE HYBRID AUTHORING TASK ---")
    prompt_parts.append(
        json.dumps(
            {
                "task": "Expand one scene into editable Semi/Hybrid script material for a TRPG scenario pack.",
                "language": pack.get("meta", {}).get("language", "ja"),
                "scene_id": scene.get("id"),
                "scene_title": scene.get("title") or scene_title({"scenario_pack": pack, "current_scene": scene.get("id")}),
                "requirements": [
                    "Return JSON only.",
                    "Do not include markdown fences.",
                    "Do not expose these instructions in narrative text.",
                    "Keep the existing scene id stable.",
                    "This is a pre-cooked GM response pack, not a setting expansion.",
                    "Generate prepared_turns that look like complete live GM JSON payloads.",
                    "Each prepared_turn.draft must be usable as the base answer for local qwen to lightly rewrite.",
                    "Include one opening turn plus likely player-response turns for the scene's important choices.",
                    "Do not write generic scene notes as the main artifact.",
                    "Do not decide player actions; describe consequences only after a branch is chosen.",
                    "Keep draft.state_delta machine-readable when gold, inventory, HP, MP, SP, scene, image, or clues change.",
                ],
                "return_schema": {
                    "scene_id": "same scene id",
                    "hybrid": {
                        "mode": "prepared_gm_turns",
                        "summary": "short editor-facing summary",
                        "prepared_turns": [
                            {
                                "id": "stable turn id",
                                "purpose": "opening | choice_response | transition | fallback",
                                "source_choice": "choice text this turn responds to, or empty string",
                                "player_intent": "short intent label",
                                "trigger_keywords": ["player words or choice labels that should select this prepared turn"],
                                "draft": {
                                    "gm_text": "complete GM narration/dialogue shown to the player",
                                    "system_log": "short state/event log",
                                    "dice_type": "1d20",
                                    "dice_dc": 10,
                                    "state_delta": {},
                                    "choices": [
                                        {"text": "choice label", "preview": "expected direction", "risk": "dice or risk"}
                                    ],
                                },
                                "rewrite_notes": [
                                    "what qwen may adapt based on the player's exact wording",
                                    "what qwen must keep unchanged"
                                ],
                            }
                        ],
                        "gm_notes": ["private notes for later human editing"],
                    },
                    "fallback_choices": [
                        {"text": "choice label", "preview": "expected direction", "risk": "dice or risk"}
                    ],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return "\n".join(prompt_parts).strip() + "\n"


def model_names_from_args(model: str, models: str) -> list[str]:
    names = _split_model_names(model) if model else []
    names.extend(_split_model_names(models))
    deduped: list[str] = []
    for name in names:
        if name not in deduped:
            deduped.append(name)
    return deduped or ["gemini-flash-latest"]


def call_gemini(prompt: str, model_names: str | list[str]) -> str:
    raw, _payload = call_gemini_payload(prompt, model_names)
    return raw


def call_gemini_payload(
    prompt: str,
    model_names: str | list[str],
    raw_path_prefix: Optional[Path] = None,
) -> tuple[str, dict[str, Any]]:
    api_key = load_gemini_api_key()
    if not api_key:
        raise RuntimeError("Gemini API key not found. Set GEMINI_API_KEY or host/gemini_api_key.*.")
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError as exc:
        raise RuntimeError("google-generativeai is required. Install it in the active Python env.") from exc

    genai.configure(api_key=api_key)
    names = _split_model_names(model_names) if isinstance(model_names, str) else model_names
    last_error: Optional[BaseException] = None
    for index, model_name in enumerate(names):
        try:
            print(f"Gemini model attempt {index + 1}/{len(names)}: {model_name}")
            model = genai.GenerativeModel(model_name)
            try:
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            except TypeError:
                response = model.generate_content(prompt)
            text = _response_text(response)
            if raw_path_prefix:
                raw_path = raw_path_prefix.with_name(f"{raw_path_prefix.name}.{_safe_model_filename(model_name)}.raw.txt")
                raw_path.write_text(text, encoding="utf-8")
            if text.strip():
                payload = parse_json_response(text)
                if payload and isinstance(payload.get("hybrid"), dict):
                    return text, payload
                raise RuntimeError(f"{model_name} returned malformed or schema-invalid JSON.")
            raise RuntimeError(f"{model_name} returned an empty response.")
        except Exception as exc:
            last_error = exc
            if index >= len(names) - 1:
                break
            if not _should_fallback_gemini_error(exc):
                raise
            print(f"Gemini model fallback: {model_name} failed with {exc.__class__.__name__}: {_one_line(str(exc), 180)}")
    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}") from last_error


def apply_hybrid_scene(pack: dict[str, Any], scene_id: str, payload: dict[str, Any]) -> None:
    scene = _scene_by_id(pack, scene_id)
    if scene is None:
        raise ValueError(f"Output pack no longer has scene id: {scene_id}")
    hybrid = payload.get("hybrid")
    if not isinstance(hybrid, dict):
        raise ValueError(f"Gemini payload for {scene_id} has no hybrid object.")
    scene["hybrid"] = _normalize_hybrid(hybrid)
    choices = _normalize_choices(payload.get("fallback_choices"))
    if choices:
        scene["fallback_choices"] = choices


def write_pack(path: Path, pack: dict[str, Any]) -> None:
    normalized = normalize_scenario_pack(pack, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_or_seed_output(source_pack: dict[str, Any], output: Path) -> dict[str, Any]:
    if output.exists():
        return load_scenario_pack(output)
    seeded = deepcopy(source_pack)
    _stamp_hybrid_meta(seeded, DEFAULT_SOURCE)
    return seeded


def _stamp_hybrid_meta(pack: dict[str, Any], source: Path) -> None:
    meta = pack.setdefault("meta", {})
    meta["hybrid_mode"] = "semi"
    meta["hybrid_source"] = str(source)
    meta["hybrid_updated_at"] = _now()


def _scene_by_id(pack: dict[str, Any], scene_id: str) -> Optional[dict[str, Any]]:
    for scene in pack.get("scenes", []):
        if isinstance(scene, dict) and str(scene.get("id") or "") == scene_id:
            return scene
    return None


def _normalize_hybrid(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": str(value.get("mode") or "prepared_gm_turns"),
        "summary": str(value.get("summary") or ""),
        "prepared_turns": _normalize_prepared_turns(value.get("prepared_turns")),
        "opening": str(value.get("opening") or ""),
        "dialogue_turns": _normalize_dialogue_turns(value.get("dialogue_turns") or value.get("turns")),
        "beats": _normalize_records(value.get("beats")),
        "branches": _normalize_records(value.get("branches")),
        "gm_notes": [str(item) for item in value.get("gm_notes") or [] if str(item).strip()],
    }


def _normalize_prepared_turns(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    turns: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        draft = item.get("draft")
        if not isinstance(draft, dict):
            draft = {}
        normalized = {
            "id": _safe_id(str(item.get("id") or f"prepared_turn_{index}")),
            "purpose": str(item.get("purpose") or "choice_response"),
            "source_choice": str(item.get("source_choice") or item.get("from_choice") or ""),
            "player_intent": str(item.get("player_intent") or ""),
            "trigger_keywords": [
                str(keyword).strip()
                for keyword in item.get("trigger_keywords", [])
                if str(keyword).strip()
            ] if isinstance(item.get("trigger_keywords"), list) else [],
            "draft": _normalize_prepared_draft(draft),
            "rewrite_notes": [str(note) for note in item.get("rewrite_notes") or [] if str(note).strip()],
        }
        if normalized["draft"].get("gm_text") or normalized["draft"].get("choices"):
            turns.append(normalized)
    return turns


def _normalize_prepared_draft(draft: dict[str, Any]) -> dict[str, Any]:
    state_delta = draft.get("state_delta")
    if not isinstance(state_delta, dict):
        state_delta = {}
    return {
        "gm_text": str(draft.get("gm_text") or draft.get("text") or ""),
        "system_log": str(draft.get("system_log") or ""),
        "dice_type": str(draft.get("dice_type") or "1d20"),
        "dice_dc": _safe_int(draft.get("dice_dc"), 10),
        "state_delta": state_delta,
        "choices": _normalize_choices(draft.get("choices")),
    }


def _normalize_dialogue_turns(value: Any) -> list[dict[str, Any]]:
    records = _normalize_records(value)
    for record in records:
        if "gm_text" not in record and "text" in record:
            record["gm_text"] = str(record.get("text") or "")
        record["gm_text"] = str(record.get("gm_text") or "")
        if "followups" in record:
            record["followups"] = _normalize_followups(record.get("followups"))
    return [record for record in records if record.get("gm_text") or record.get("choices")]


def _normalize_followups(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    followups: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        followup = dict(item)
        followup["id"] = _safe_id(str(followup.get("id") or f"followup_{index}"))
        followup["choice_text"] = str(followup.get("choice_text") or followup.get("from_choice") or "")
        followup["gm_text"] = str(followup.get("gm_text") or followup.get("text") or "")
        if "state_delta" in followup and not isinstance(followup["state_delta"], dict):
            followup["state_delta"] = {}
        followups.append(followup)
    return followups


def _normalize_records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    records: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            continue
        record = dict(item)
        record["id"] = _safe_id(str(record.get("id") or f"entry_{index}"))
        if "choices" in record:
            record["choices"] = _normalize_choices(record.get("choices"))
        if "trigger_keywords" in record and isinstance(record["trigger_keywords"], list):
            record["trigger_keywords"] = [str(keyword) for keyword in record["trigger_keywords"] if str(keyword).strip()]
        if "state_delta" in record and not isinstance(record["state_delta"], dict):
            record["state_delta"] = {}
        records.append(record)
    return records


def _normalize_choices(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    choices: list[dict[str, str]] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            choices.append({"text": item.strip(), "preview": "", "risk": ""})
        elif isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if text:
                choices.append({
                    "text": text,
                    "preview": str(item.get("preview") or ""),
                    "risk": str(item.get("risk") or ""),
                })
    return choices


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_")
    return cleaned or "entry"


def _safe_model_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("_") or "model"


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _split_model_names(value: str) -> list[str]:
    return [name.strip() for name in re.split(r"[,;\s]+", value) if name.strip()]


def _should_fallback_gemini_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    retry_markers = (
        "429",
        "quota",
        "rate limit",
        "rate_limit",
        "resource_exhausted",
        "exhausted",
        "unavailable",
        "deadline",
        "timeout",
        "empty response",
        "malformed",
        "schema-invalid",
        "json",
    )
    return any(marker in text for marker in retry_markers)


def _one_line(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if len(cleaned) <= limit else cleaned[: max(0, limit - 1)].rstrip() + "..."


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text)
    chunks: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                chunks.append(str(part_text))
    return "\n".join(chunks)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
