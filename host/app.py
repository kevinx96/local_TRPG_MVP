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
    save_config,
)


CLIENT_ROOT = PROJECT_ROOT / "client"

app = FastAPI(title="Local TRPG Host", version="0.2.0")
app.mount("/static", StaticFiles(directory=CLIENT_ROOT), name="static")


class CreateSessionRequest(BaseModel):
    scenario_path: Optional[str] = None
    character: Optional[dict[str, Any]] = None


class TurnRequest(BaseModel):
    text: str
    speaker: str = "プレイヤー"


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


@app.post("/api/sessions")
def api_create_session(request: CreateSessionRequest) -> dict[str, Any]:
    try:
        session_public = create_session(request.scenario_path, request.character)
        session = load_session(session_public["id"])
        # Auto-generate opening narrative via LLM
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
    """Generate the opening narrative via LLM instead of canned text."""
    config = load_config()
    debug_enabled = bool(config.get("debug_llm", True))

    latest_roll = {"expression": "opening", "rolls": [], "total": 0}
    contract = build_gm_contract_prompt()
    messages = build_llm_messages(session, latest_roll, contract)
    # Add the opening instruction as a user message for the LLM
    opening_prompt = build_opening_prompt(session)
    messages.append({"role": "user", "content": opening_prompt})

    if debug_enabled:
        debug_log(f"Opening generation start session={session['id']}")

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

    # Use GM-specified dice type from previous turn
    dice_type = session.get("next_dice_type", "1d20")
    latest_roll = roll_dice(session, dice_type)

    config = load_config()
    messages = build_llm_messages(session, latest_roll, build_gm_contract_prompt())
    full_response = ""
    debug_enabled = bool(config.get("debug_llm", True))

    if debug_enabled:
        dice_dc = session.get("next_dice_dc", 10)
        debug_log(
            "Turn start "
            f"session={session['id']} speaker={request.speaker!r} "
            f"text_len={len(request.text.strip())} dice={latest_roll['expression']} "
            f"total={latest_roll['total']} dc={dice_dc}"
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


def _demo_opening(session: dict[str, Any], error: str) -> str:
    """Fallback opening when LLM is unavailable."""
    character = session["character"]
    name = character.get("name", "冒険者")
    gm_text = (
        f"重厚な石造りの城、アルデリア王城の謁見の間――。\n\n"
        f"高い天井からは黄金のシャンデリアが吊り下がり、"
        f"無数の蝋燭の炎が揺れている。磨き上げられた大理石の床に、"
        f"あなたの足音が静かに響く。\n\n"
        f"玉座に座る白髪の国王が、あなた――{name}――に向かって重々しく口を開いた。\n\n"
        f"「{name}よ、よくぞ参った。紅蓮の邪竜イグニスが目覚め、"
        f"我が国は滅亡の危機に瀕しておる。おぬしだけが頼みの綱じゃ」\n\n"
        f"国王は傍らの侍従に目配せし、革袋と小さな包みをあなたに差し出させた。\n\n"
        f"「これは支度金50ゴールドと薬草じゃ。旅の備えにせよ」\n\n"
        f"窓の外では、遠くの山脈の向こうに不吉な赤い光が空を染めている。"
        f"城内の兵士たちの表情にも不安の色が浮かんでいた。"
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
            "gold_change": 50,
            "inventory_add": [],
            "inventory_remove": [],
            "current_scene": "第1章：王の間",
            "background_image": None,
            "character_image": None,
        },
        "choices": [
            {
                "text": "国王に詳しい話を聞く",
                "preview": "邪竜の情報や旅の手がかりが得られるかもしれません",
                "risk": "判定不要",
            },
            {
                "text": "城の周囲を探索する",
                "preview": "有用なアイテムや情報が見つかる可能性があります",
                "risk": "1d20判定が必要（DC10）",
            },
            {
                "text": "すぐに城を出て冒険に出発する",
                "preview": "早速スライムの森へ向かうことになります",
                "risk": "準備不足のリスクあり",
            },
        ],
        "debug_error": error,
    }
    return gm_text + "\n" + STATE_MARKER + "\n" + json.dumps(payload, ensure_ascii=False)


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
        "choices": [
            {
                "text": "周囲を注意深く観察する",
                "preview": "隠された手がかりや危険を発見できるかもしれません",
                "risk": "1d20判定が必要（DC12）",
            },
            {
                "text": "慎重に前へ進む",
                "preview": "物語が次の展開へ進みます",
                "risk": "判定不要",
            },
            {
                "text": "装備を確認して態勢を整える",
                "preview": "次の行動に備えることができます",
                "risk": "判定不要",
            },
        ],
        "debug_error": error,
    }
    return gm_text + "\n" + STATE_MARKER + "\n" + json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    from .run_server import main

    main()
