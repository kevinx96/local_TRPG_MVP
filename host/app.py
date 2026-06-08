from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .gm_contract import STATE_MARKER, build_gm_contract_prompt, build_opening_prompt, split_visible_and_json
from .llm_client import LLMClientError, chat_completion, debug_log
from .scenario_context import (
    fallback_choices_for_session,
    has_hybrid_prepared_turn,
    hybrid_context_debug,
    normalize_scenario_pack,
    scenario_context_debug,
    scene_title,
    select_hybrid_context,
    select_scenario_context,
)
from .state import (
    HOST_ROOT,
    PROJECT_ROOT,
    add_player_message,
    add_system_log,
    apply_gm_payload,
    auto_transition_scene,
    build_llm_messages,
    choice_requirement_status,
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
DEBUG_COMPLETION_DIR = HOST_ROOT / "debug" / "completions"
SCENARIO_SCHEMA_FILENAME = "scenario_pack.schema.json"

app = FastAPI(title="Local TRPG Host", version="0.2.0")
app.mount("/static", StaticFiles(directory=CLIENT_ROOT), name="static")


class CreateSessionRequest(BaseModel):
    scenario_path: Optional[str] = None
    gm_mode: Optional[str] = None
    character_id: Optional[str] = None
    character: Optional[dict[str, Any]] = None


class TurnRequest(BaseModel):
    text: str
    speaker: str = "プレイヤー"
    client_dice: Optional[dict[str, Any]] = None


class ScenarioSaveRequest(BaseModel):
    scenario: dict[str, Any]


class ScenarioCreateRequest(BaseModel):
    filename: str
    scenario: dict[str, Any]


class ClientDebugRequest(BaseModel):
    event: str
    detail: dict[str, Any] = {}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(
        CLIENT_ROOT / "index.html",
        headers={"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"},
    )


@app.get("/editor")
def editor() -> FileResponse:
    return FileResponse(
        CLIENT_ROOT / "editor.html",
        headers={"Cache-Control": "no-store, max-age=0", "Pragma": "no-cache"},
    )


@app.post("/api/client-debug")
def api_client_debug(request: ClientDebugRequest) -> dict[str, bool]:
    detail = json.dumps(request.detail, ensure_ascii=False, default=str)
    if len(detail) > 1200:
        detail = detail[:1200] + "...(truncated)"
    debug_log(f"Client choice debug event={request.event} detail={detail}")
    return {"ok": True}


def _ollama_proxy_info() -> tuple[str, dict[str, str]]:
    """Return (proxy_base_url, extra_headers) for the Ollama backend."""
    config = load_config()
    backend = (config.get("backends") or {}).get("ollama", {})
    base = backend.get("base_url", "http://localhost:11434/v1")
    # Remove the /v1 (or /v1/) suffix to get the root proxy address
    if base.rstrip("/").endswith("/v1"):
        base = base.rstrip("/")[:-3]
    headers = backend.get("headers") or {}
    return base.rstrip("/"), {str(k): str(v) for k, v in headers.items()}


@app.post("/api/ollama/shutdown")
def api_ollama_shutdown() -> dict[str, Any]:
    """Relay shutdown request to the Ollama tunnel proxy."""
    import requests as _requests

    proxy_base, headers = _ollama_proxy_info()
    proxy_url = proxy_base + "/api/shutdown"
    headers["Content-Type"] = "application/json"
    try:
        resp = _requests.post(
            proxy_url,
            json={"delay_seconds": 30},
            headers=headers,
            timeout=10,
        )
        return resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"无法连接 Ollama 机器: {exc}") from exc


@app.get("/api/ollama/shutdown/ping")
def api_ollama_shutdown_ping() -> dict[str, Any]:
    """Check if the Ollama tunnel proxy is reachable."""
    import requests as _requests

    proxy_base, headers = _ollama_proxy_info()
    proxy_url = proxy_base + "/api/shutdown/ping"
    try:
        resp = _requests.get(proxy_url, headers=headers, timeout=5)
        return resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ollama 机器不可达: {exc}") from exc


@app.get("/api/config")
def config_info() -> dict[str, Any]:
    config = load_config()
    backend_name = config.get("active_backend", "ollama")
    backend = (config.get("backends") or {}).get(backend_name, {})
    return {
        "active_backend": backend_name,
        "base_url": backend.get("base_url"),
        "model": backend.get("model"),
        "backends": _public_backends(config.get("backends", {})),
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


def _public_backends(backends: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(backends, dict):
        return {}
    public: dict[str, dict[str, Any]] = {}
    for name, backend in backends.items():
        if not isinstance(backend, dict):
            continue
        public[str(name)] = {
            "base_url": backend.get("base_url"),
            "model": backend.get("model"),
            "fallback_models": backend.get("fallback_models") or [],
        }
    return public


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
        session_public = create_session(
            request.scenario_path,
            request.character,
            gm_mode=request.gm_mode,
            character_id=request.character_id,
        )
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
    messages = build_llm_messages(session, latest_roll, build_gm_contract_prompt(opening=True))
    opening_prompt = _opening_prompt_for_mode(session)
    messages.append({"role": "user", "content": opening_prompt})

    if debug_enabled:
        debug_log(f"Opening generation start session={session['id']}")
        context_debug = _context_debug_for_mode(session, "", opening=True)
        debug_log(
            "Opening scenario context "
            f"chars={context_debug['chars']} scene={context_debug['scene']} "
            f"matches={context_debug['matches']}"
        )

    full_response = ""
    completion_source = "llm"
    t0 = time.time()
    try:
        full_response = chat_completion(config, messages)
    except LLMClientError as exc:
        completion_source = "demo_fallback"
        if debug_enabled:
            debug_log(f"Opening LLM failure; demo_fallback={config.get('demo_fallback_on_error', True)} error={exc}")
        if not config.get("demo_fallback_on_error", True):
            raise HTTPException(status_code=502, detail=f"LLM接続エラー: {exc}") from exc
        full_response = _demo_opening(session, str(exc))
    if debug_enabled and full_response:
        completion_path = _save_completion_debug(session, "opening", full_response, completion_source)
        debug_log(f"Opening completion saved path={completion_path}")

    visible_text, payload, warning = split_visible_and_json(full_response)
    visible_text = _visible_text_from_payload(visible_text, payload)
    if not visible_text.strip():
        if debug_enabled:
            debug_log(
                "Opening model returned no player-visible text; using local fallback. "
                f"payload_keys={_payload_keys(payload)} raw_preview={_raw_preview(full_response)}"
            )
        full_response = _demo_opening(session, "opening response had no player-visible text")
        visible_text, payload, warning = split_visible_and_json(full_response)
        visible_text = _visible_text_from_payload(visible_text, payload)
    if debug_enabled:
        elapsed_ms = (time.time() - t0) * 1000
        debug_log(
            "Opening model result "
            f"raw_chars={len(full_response)} visible_chars={len(visible_text)} "
            f"json_ok={payload is not None} warning={warning!r} elapsed_ms={elapsed_ms:.0f}"
        )
    apply_gm_payload(session, visible_text, payload, warning)
    session["needs_opening"] = False
    save_session(session)
    return public_session(session)


def _run_turn(session: dict[str, Any], request: TurnRequest) -> dict[str, Any]:
    action_text = request.text.strip()
    choice = _matching_choice(session.get("choices"), action_text)
    if choice:
        enabled, reason = choice_requirement_status(choice, session.get("character", {}))
        if not enabled:
            add_system_log(session, reason or "この行動は条件を満たしていません。")
            save_session(session)
            return public_session(session)

    add_player_message(session, action_text, request.speaker)

    auto_transition_scene(session, action_text)

    dice_type, dice_dc = _dice_settings_for_turn(session, action_text)
    client_dice = request.client_dice
    if isinstance(client_dice, dict) and isinstance(client_dice.get("rolls"), list) and len(client_dice["rolls"]) > 0:
        latest_roll = roll_dice(session, dice_type, int(dice_dc) if isinstance(dice_dc, (int, float)) else None, client_rolls=client_dice["rolls"])
    else:
        latest_roll = roll_dice(session, dice_type, int(dice_dc) if isinstance(dice_dc, (int, float)) else None)

    config = load_config()
    messages = build_llm_messages(session, latest_roll, build_gm_contract_prompt())
    debug_enabled = bool(config.get("debug_llm", True))

    if debug_enabled:
        context_debug = _context_debug_for_mode(session, request.text.strip(), opening=False)
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

    t0 = time.time()
    completion_source = "llm"
    try:
        full_response = chat_completion(config, messages)
    except LLMClientError as exc:
        completion_source = "demo_fallback"
        if debug_enabled:
            debug_log(f"LLM failure; demo_fallback={config.get('demo_fallback_on_error', True)} error={exc}")
        if not config.get("demo_fallback_on_error", True):
            raise HTTPException(status_code=502, detail=f"LLM接続エラー: {exc}") from exc
        full_response = _demo_response(session, request.text, latest_roll, str(exc))
    if debug_enabled and full_response:
        completion_path = _save_completion_debug(session, "turn", full_response, completion_source)
        debug_log(f"Turn completion saved path={completion_path}")

    visible_text, payload, warning = split_visible_and_json(full_response)
    visible_text = _visible_text_from_payload(visible_text, payload)
    if debug_enabled and not visible_text.strip():
        debug_log(
            "Turn model returned no player-visible text. "
            f"payload_keys={_payload_keys(payload)} raw_preview={_raw_preview(full_response)}"
        )
    if debug_enabled:
        elapsed_ms = (time.time() - t0) * 1000
        debug_log(
            "Turn model result "
            f"raw_chars={len(full_response)} visible_chars={len(visible_text)} "
            f"json_ok={payload is not None} warning={warning!r} elapsed_ms={elapsed_ms:.0f}"
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


def _dice_settings_for_turn(session: dict[str, Any], action_text: str) -> tuple[str, int]:
    dice_type = str(session.get("next_dice_type") or "1d20")
    dice_dc = int(session.get("next_dice_dc", 10) or 0)
    choice = _matching_choice(session.get("choices"), action_text)
    if not choice:
        return dice_type, max(dice_dc, 10)

    risk = str(choice.get("risk") or "")
    if "判定不要" in risk:
        return dice_type, 0

    expr_match = re.search(r"(\d+d\d+(?:\+[A-Za-z_][A-Za-z0-9_]*)?)", risk, re.IGNORECASE)
    if expr_match:
        dice_type = expr_match.group(1)

    dc_match = re.search(r"DC\s*(\d+)", risk, re.IGNORECASE)
    if dc_match:
        dice_dc = int(dc_match.group(1))
    elif "判定" in risk and dice_dc <= 0:
        dice_dc = 10
    return dice_type, dice_dc


def _matching_choice(raw_choices: Any, action_text: str) -> Optional[dict[str, Any]]:
    if not isinstance(raw_choices, list) or not action_text:
        return None
    normalized_action = action_text.strip()
    for choice in raw_choices:
        if not isinstance(choice, dict):
            continue
        if str(choice.get("text") or "").strip() == normalized_action:
            return choice
    return None


def _visible_text_from_payload(visible_text: str, payload: Optional[dict[str, Any]]) -> str:
    if visible_text.strip() or not isinstance(payload, dict):
        return visible_text
    gm_text = payload.get("gm_text")
    return str(gm_text or "")


def _payload_keys(payload: Optional[dict[str, Any]]) -> list[str]:
    if not isinstance(payload, dict):
        return []
    return sorted(str(key) for key in payload.keys())[:20]


def _raw_preview(text: str, limit: int = 320) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:limit]


def _save_completion_debug(session: dict[str, Any], phase: str, completion: str, source: str) -> str:
    DEBUG_COMPLETION_DIR.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc)
    timestamp = created_at.strftime("%Y%m%dT%H%M%S%fZ")
    session_id = re.sub(r"[^A-Za-z0-9_-]+", "_", str(session.get("id") or "unknown"))[:64]
    safe_phase = re.sub(r"[^A-Za-z0-9_-]+", "_", phase)[:32]
    safe_source = re.sub(r"[^A-Za-z0-9_-]+", "_", source)[:32]
    path = DEBUG_COMPLETION_DIR / f"{timestamp}_{session_id}_{safe_phase}_{safe_source}.json"
    path.write_text(
        json.dumps(
            {
                "session_id": session.get("id"),
                "phase": phase,
                "source": source,
                "created_at": created_at.isoformat(),
                "chars": len(completion),
                "completion": completion,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(path)


def _opening_prompt_for_mode(session: dict[str, Any]) -> str:
    if session.get("gm_mode") == "semi" and has_hybrid_prepared_turn(session, "", opening=True):
        return (
            "SEMI/HYBRIDモードのprepared openingターンを完成済みのGM応答として扱ってください。"
            "キャラクター名など現在状態に矛盾する最小部分だけを書き換えてください。"
            "開始時は文体・出来事・NPC台詞・報酬内容・選択肢を原則として変えないでください。"
            "gm_text, system_log, choices は日本語だけで出力してください。英語を混ぜないでください。"
            "出力はGM JSONオブジェクト1つだけにしてください。"
        )
    return build_opening_prompt(session)


def _context_debug_for_mode(session: dict[str, Any], player_text: str, opening: bool = False) -> dict[str, Any]:
    if session.get("gm_mode") == "semi" and has_hybrid_prepared_turn(session, player_text, opening=opening):
        debug = hybrid_context_debug(select_hybrid_context(session, player_text, opening=opening, include_debug=True))
        return {
            "chars": debug["chars"],
            "scene": debug["scene"],
            "matches": {"prepared_turn": [str(debug.get("prepared_turn") or "")], "purpose": [str(debug.get("purpose") or "")]},
        }
    return scenario_context_debug(select_scenario_context(session, player_text))


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
            "attribute_changes": {},
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
            "attribute_changes": {},
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
