from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .gm_contract import STATE_MARKER, build_gm_contract_prompt, build_opening_prompt, split_visible_and_json
from .llm_client import LLMClientError, chat_completion, debug_log
from .scenario_context import fallback_choices_for_session, normalize_scenario_pack, scenario_context_debug, scene_title, select_scenario_context
from .state import (
    HOST_ROOT,
    PROJECT_ROOT,
    add_player_message,
    apply_gm_payload,
    build_llm_messages,
    create_session,
    load_config,
    load_session,
    public_session,
    roll_dice,
    save_config,
    save_session,
)


CLIENT_ROOT = PROJECT_ROOT / "client"
PROCESSED_SCENARIO_DIR = HOST_ROOT / "prompt" / "processed"
SCENARIO_SCHEMA_FILENAME = "scenario_pack.schema.json"

app = FastAPI(title="Local TRPG Host", version="0.2.0")
app.mount("/static", StaticFiles(directory=CLIENT_ROOT), name="static")


class CreateSessionRequest(BaseModel):
    scenario_path: Optional[str] = None
    gm_mode: Optional[str] = None
    character: Optional[dict[str, Any]] = None


class TurnRequest(BaseModel):
    text: str
    speaker: str = "プレイヤー"


class ScenarioSaveRequest(BaseModel):
    scenario: dict[str, Any]


class ScenarioCreateRequest(BaseModel):
    filename: str
    scenario: dict[str, Any]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(CLIENT_ROOT / "index.html")


@app.get("/editor")
def editor() -> FileResponse:
    return FileResponse(CLIENT_ROOT / "editor.html")


@app.get("/api/config")
def config_info() -> dict[str, Any]:
    config = load_config()
    backend_name = config.get("active_backend", "ollama")
    backend = (config.get("backends") or {}).get(backend_name, {})
    return {
        "active_backend": backend_name,
        "base_url": backend.get("base_url"),
        "model": backend.get("model"),
        "backends": config.get("backends", {}),
    }


class UpdateConfigRequest(BaseModel):
    active_backend: str
    model: Optional[str] = None


@app.put("/api/config")
def api_update_config(request: UpdateConfigRequest) -> dict[str, Any]:
    config = load_config()
    backends = config.get("backends", {})
    if request.active_backend not in backends:
        raise HTTPException(status_code=400, detail="Invalid backend selected.")
    config["active_backend"] = request.active_backend
    backend = backends[request.active_backend]
    if request.model:
        candidates = _configured_model_candidates(backend)
        if request.model not in candidates:
            raise HTTPException(status_code=400, detail="Invalid model selected.")
        backend["model"] = request.model
        backend["fallback_models"] = [model for model in candidates if model != request.model]
    save_config(config)
    return config_info()


def _configured_model_candidates(backend: dict[str, Any]) -> list[str]:
    candidates = [backend.get("model"), *(backend.get("fallback_models") or [])]
    return [str(model) for index, model in enumerate(candidates) if model and model not in candidates[:index]]


@app.get("/api/scenarios")
def api_list_scenarios() -> dict[str, Any]:
    scenarios = []
    PROCESSED_SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(PROCESSED_SCENARIO_DIR.glob("*.json"), key=lambda item: item.name.lower()):
        if path.name == SCENARIO_SCHEMA_FILENAME:
            continue
        summary = _scenario_summary(path)
        if summary:
            scenarios.append(summary)
    return {"scenarios": scenarios}


@app.post("/api/scenarios")
def api_create_scenario(request: ScenarioCreateRequest) -> dict[str, Any]:
    path = _resolve_scenario_editor_path(request.filename, must_exist=False)
    if path.exists():
        raise HTTPException(status_code=409, detail="Scenario file already exists.")
    _validate_editor_scenario(request.scenario)
    _write_scenario_json(path, request.scenario)
    return api_get_scenario(path.name)


@app.get("/api/scenarios/{filename}")
def api_get_scenario(filename: str) -> dict[str, Any]:
    path = _resolve_scenario_editor_path(filename)
    try:
        scenario = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Scenario JSON is invalid: {exc}") from exc
    if not isinstance(scenario, dict):
        raise HTTPException(status_code=400, detail="Scenario JSON must be an object.")
    return {"filename": path.name, "scenario": scenario, "summary": _scenario_summary(path)}


@app.put("/api/scenarios/{filename}")
def api_save_scenario(filename: str, request: ScenarioSaveRequest) -> dict[str, Any]:
    path = _resolve_scenario_editor_path(filename)
    _validate_editor_scenario(request.scenario)
    _write_scenario_json(path, request.scenario)
    return api_get_scenario(path.name)


def _scenario_summary(path: Path) -> Optional[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, dict):
            return None
        pack = normalize_scenario_pack(raw, path)
    except Exception:
        return {
            "filename": path.name,
            "title": path.stem,
            "summary": "Invalid JSON",
            "initial_scene": "",
            "scene_count": 0,
            "modified_at": path.stat().st_mtime,
            "valid": False,
        }
    meta = pack.get("meta", {})
    return {
        "filename": path.name,
        "title": meta.get("title") or path.stem,
        "summary": meta.get("summary") or "",
        "initial_scene": meta.get("initial_scene") or "",
        "scene_count": len(pack.get("scenes") or []),
        "modified_at": path.stat().st_mtime,
        "valid": True,
    }


def _resolve_scenario_editor_path(filename: str, must_exist: bool = True) -> Path:
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename or safe_name == SCENARIO_SCHEMA_FILENAME:
        raise HTTPException(status_code=400, detail="Invalid scenario filename.")
    if not safe_name.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Scenario filename must end with .json.")
    root = PROCESSED_SCENARIO_DIR.resolve()
    path = (root / safe_name).resolve()
    if path.parent != root:
        raise HTTPException(status_code=400, detail="Invalid scenario path.")
    if must_exist and not path.exists():
        raise HTTPException(status_code=404, detail="Scenario file not found.")
    return path


def _validate_editor_scenario(scenario: dict[str, Any]) -> None:
    try:
        normalize_scenario_pack(scenario)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Scenario pack is invalid: {exc}") from exc
    if not isinstance(scenario.get("meta"), dict):
        raise HTTPException(status_code=400, detail="Scenario pack requires a meta object.")
    if not isinstance(scenario.get("scenes"), list) or not scenario["scenes"]:
        raise HTTPException(status_code=400, detail="Scenario pack requires at least one scene.")


def _write_scenario_json(path: Path, scenario: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scenario, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@app.post("/api/sessions")
def api_create_session(request: CreateSessionRequest) -> dict[str, Any]:
    try:
        session_public = create_session(request.scenario_path, request.character, request.gm_mode)
        session = load_session(session_public["id"])
        if session.get("needs_opening"):
            return _run_opening(session)
        return public_session(session)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}")
def api_get_session(session_id: str) -> dict[str, Any]:
    try:
        return public_session(load_session(session_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/turn")
def api_turn(session_id: str, request: TurnRequest) -> dict[str, Any]:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="入力が空です。")
    try:
        session = load_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _run_turn(session, request)


def _run_opening(session: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    debug_enabled = bool(config.get("debug_llm", True))

    latest_roll = {"expression": "opening", "rolls": [], "total": 0}
    messages = build_llm_messages(session, latest_roll, build_gm_contract_prompt())
    opening_prompt = build_opening_prompt(session)
    messages.append({"role": "user", "content": opening_prompt})

    if debug_enabled:
        debug_log(f"Opening generation start session={session['id']}")
        context_debug = scenario_context_debug(select_scenario_context(session, ""))
        debug_log(
            "Opening scenario context "
            f"chars={context_debug['chars']} scene={context_debug['scene']} "
            f"matches={context_debug['matches']}"
        )

    full_response = ""
    try:
        full_response = chat_completion(config, messages)
    except LLMClientError as exc:
        if debug_enabled:
            debug_log(f"Opening LLM failure; demo_fallback={config.get('demo_fallback_on_error', True)} error={exc}")
        if not config.get("demo_fallback_on_error", True):
            raise HTTPException(status_code=502, detail=f"LLM接続エラー: {exc}") from exc
        full_response = _demo_opening(session, str(exc))

    visible_text, payload, warning = split_visible_and_json(full_response)
    if not visible_text.strip():
        if debug_enabled:
            debug_log("Opening model returned no player-visible text; using local fallback.")
        full_response = _demo_opening(session, "opening response had no player-visible text")
        visible_text, payload, warning = split_visible_and_json(full_response)
    if debug_enabled:
        debug_log(
            "Opening model result "
            f"raw_chars={len(full_response)} visible_chars={len(visible_text)} "
            f"json_ok={payload is not None} warning={warning!r}"
        )
    apply_gm_payload(session, visible_text, payload, warning)
    session["needs_opening"] = False
    save_session(session)
    return public_session(session)


def _run_turn(session: dict[str, Any], request: TurnRequest) -> dict[str, Any]:
    add_player_message(session, request.text.strip(), request.speaker)

    dice_type = session.get("next_dice_type", "1d20")
    latest_roll = roll_dice(session, dice_type)

    config = load_config()
    messages = build_llm_messages(session, latest_roll, build_gm_contract_prompt())
    debug_enabled = bool(config.get("debug_llm", True))

    if debug_enabled:
        dice_dc = session.get("next_dice_dc", 10)
        context_debug = scenario_context_debug(select_scenario_context(session, request.text.strip()))
        debug_log(
            "Turn start "
            f"session={session['id']} speaker={request.speaker!r} "
            f"text_len={len(request.text.strip())} dice={latest_roll['expression']} "
            f"total={latest_roll['total']} dc={dice_dc}"
        )
        debug_log(
            "Turn scenario context "
            f"chars={context_debug['chars']} scene={context_debug['scene']} "
            f"matches={context_debug['matches']}"
        )

    try:
        full_response = chat_completion(config, messages)
    except LLMClientError as exc:
        if debug_enabled:
            debug_log(f"LLM failure; demo_fallback={config.get('demo_fallback_on_error', True)} error={exc}")
        if not config.get("demo_fallback_on_error", True):
            raise HTTPException(status_code=502, detail=f"LLM接続エラー: {exc}") from exc
        full_response = _demo_response(session, request.text, latest_roll, str(exc))

    visible_text, payload, warning = split_visible_and_json(full_response)
    if debug_enabled:
        debug_log(
            "Turn model result "
            f"raw_chars={len(full_response)} visible_chars={len(visible_text)} "
            f"json_ok={payload is not None} warning={warning!r}"
        )
    apply_gm_payload(session, visible_text, payload, warning)
    save_session(session)
    if debug_enabled:
        debug_log(
            "Turn saved "
            f"session={session['id']} messages={len(session['messages'])} "
            f"logs={len(session['system_logs'])} dice={len(session['dice_log'])}"
        )
    return public_session(session)


def _demo_opening(session: dict[str, Any], error: str) -> str:
    character = session["character"]
    name = character.get("name", "冒険者")
    title = session.get("scenario_title") or "シナリオ"
    current_title = scene_title(session) or "開始"
    gm_text = (
        "ローカルLLMから応答を取得できなかったため、デモ進行で開始します。\n\n"
        f"シナリオ「{title}」の現在地は「{current_title}」。"
        f"{name}は周囲の空気、近くにいる人物、手元の装備を確かめます。"
        "場面は静かに動き出し、次の一手を選べる状態になりました。"
    )
    payload = {
        "gm_text": gm_text,
        "system_log": "デモモードで開幕シーンを生成しました。",
        "dice_type": "1d20",
        "dice_dc": 10,
        "state_delta": {
            "hp_change": 0,
            "mp_change": 0,
            "sp_change": 0,
            "gold_change": 0,
            "inventory_add": [],
            "inventory_remove": [],
            "current_scene": None,
            "background_image": None,
            "character_image": None,
        },
        "choices": fallback_choices_for_session(session),
        "debug_error": error,
    }
    return gm_text + "\n" + STATE_MARKER + "\n" + json.dumps(payload, ensure_ascii=False)


def _demo_response(session: dict[str, Any], player_text: str, roll: dict[str, Any], error: str) -> str:
    gm_text = (
        "接続中のローカルLLMから応答を取得できませんでした。"
        "ただし、デモ進行として物語を続けます。\n\n"
        f"あなたの行動「{player_text}」に対して、運命の出目は{roll['total']}。"
        "状況は変化し、次の一手を選べる状態になりました。"
    )
    payload = {
        "gm_text": gm_text,
        "system_log": f"デモ応答を使用しました。直近の判定: {roll['expression']} = {roll['total']}",
        "dice_type": "1d20",
        "dice_dc": 10,
        "state_delta": {
            "hp_change": 0,
            "mp_change": 0,
            "sp_change": 0,
            "gold_change": 0,
            "inventory_add": [],
            "inventory_remove": [],
            "current_scene": None,
            "background_image": None,
            "character_image": None,
        },
        "choices": fallback_choices_for_session(session),
        "debug_error": error,
    }
    return gm_text + "\n" + STATE_MARKER + "\n" + json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    from .run_server import main

    main()
