from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .gm_contract import STATE_MARKER, build_gm_contract_prompt, split_visible_and_json
from .llm_client import LLMClientError, chat_completion, debug_log
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
    save_session,
)


CLIENT_ROOT = PROJECT_ROOT / "client"

app = FastAPI(title="Local TRPG Host", version="0.1.0")
app.mount("/static", StaticFiles(directory=CLIENT_ROOT), name="static")


class CreateSessionRequest(BaseModel):
    scenario_path: str | None = None
    character: dict[str, Any] | None = None


class TurnRequest(BaseModel):
    text: str
    speaker: str = "プレイヤー"
    dice: str = "1d20"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(CLIENT_ROOT / "index.html")


@app.get("/api/config")
def config_info() -> dict[str, Any]:
    config = load_config()
    backend_name = config.get("active_backend", "ollama")
    backend = (config.get("backends") or {}).get(backend_name, {})
    return {
        "active_backend": backend_name,
        "base_url": backend.get("base_url"),
        "model": backend.get("model"),
    }


@app.post("/api/sessions")
def api_create_session(request: CreateSessionRequest) -> dict[str, Any]:
    try:
        return create_session(request.scenario_path, request.character)
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


def _run_turn(session: dict[str, Any], request: TurnRequest) -> dict[str, Any]:
    add_player_message(session, request.text.strip(), request.speaker)
    latest_roll = roll_dice(session, request.dice)
    config = load_config()
    messages = build_llm_messages(session, latest_roll, build_gm_contract_prompt())
    full_response = ""
    debug_enabled = bool(config.get("debug_llm", True))

    if debug_enabled:
        debug_log(
            "Turn start "
            f"session={session['id']} speaker={request.speaker!r} "
            f"text_len={len(request.text.strip())} dice={latest_roll['expression']} total={latest_roll['total']}"
        )

    try:
        full_response = chat_completion(config, messages)
    except LLMClientError as exc:
        if debug_enabled:
            debug_log(f"LLM failure; demo_fallback={config.get('demo_fallback_on_error', True)} error={exc}")
        if not config.get("demo_fallback_on_error", True):
            raise HTTPException(status_code=502, detail=f"LLM接続エラー: {exc}") from exc
        full_response = _demo_response(request.text, latest_roll, str(exc))

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

def _demo_response(player_text: str, roll: dict[str, Any], error: str) -> str:
    gm_text = (
        "接続中のローカルLLMから応答を取得できませんでした。"
        "ただし、デモ進行として物語を続けます。\n\n"
        f"あなたの行動「{player_text}」に対して、運命の出目は{roll['total']}。"
        "周囲の空気が張りつめ、次の一手を促すように場面が静かに動き出します。"
    )
    payload = {
        "gm_text": gm_text,
        "system_log": f"デモ応答を使用しました。直近の判定: {roll['expression']} = {roll['total']}",
        "state_delta": {
            "hp_change": 0,
            "mp_change": 0,
            "sp_change": 0,
            "inventory_add": [],
            "inventory_remove": [],
            "current_scene": None,
            "background_image": None,
            "character_image": None,
        },
        "choices": [],
        "debug_error": error,
    }
    return gm_text + "\n" + STATE_MARKER + "\n" + json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    from .run_server import main

    main()
