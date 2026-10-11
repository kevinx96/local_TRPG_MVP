"""Best-effort metadata traces. Never serialize config, prompts, or exceptions."""
from __future__ import annotations

import hashlib
import json
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from .gm_contract import split_visible_and_json

TRACE_DIR = Path(__file__).resolve().parent / "debug" / "traces"
_records: ContextVar = ContextVar("llm_trace_records", default=None)


def prompt_metadata(messages: list[dict[str, str]]) -> dict[str, Any]:
    encoded = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"prompt_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            "prompt_chars": sum(len(m.get("content", "")) for m in messages)}


def append_trace(record: dict[str, Any]) -> None:
    try:
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        path = TRACE_DIR / (datetime.now(timezone.utc).date().isoformat() + ".jsonl")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def game_trace(function: Callable) -> Callable:
    @wraps(function)
    def wrapped(session: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        records: list[dict[str, Any]] = []
        token = _records.set(records)
        try:
            return function(session, *args, **kwargs)
        finally:
            _records.reset(token)
            for record in records:
                if record["outcome"] is None:
                    record["outcome"] = (session.get("last_action_result") or {}).get("outcome")
                append_trace(record)
    return wrapped


def annotate(**values: Any) -> None:
    records = _records.get()
    if records:
        records[-1].update(values)


def completion(call: Callable, session: dict[str, Any], config: dict[str, Any],
               messages: list[dict[str, str]], call_type: str) -> str:
    usage: dict[str, Any] = {}
    backend = str(config.get("active_backend", "gemini"))
    record = {"session_id": session["id"], "turn": sum(m.get("role") == "user" for m in session.get("messages", [])),
              "gm_mode": session.get("gm_mode"), "call_type": call_type, "backend": backend,
              "model": (config.get("backends", {}).get(backend) or {}).get("model"),
              **prompt_metadata(messages), "usage": usage, "latency_ms": None,
              "parse_status": "not_parsed", "plan": None, "outcome": None, "fallback": False}
    if call_type == "plan":
        record["turn"] += 1
    records = _records.get()
    if config.get("trace_llm", True) and records is not None:
        records.append(record)
    started = time.monotonic()
    try:
        raw = call(config, messages, usage_out=usage)
        if call_type != "plan":
            _visible, payload, warning = split_visible_and_json(raw)
            record["parse_status"] = "ok" if payload is not None else "invalid_json"
            record["parse_warning"] = warning
            record["fallback"] = payload is None
        return raw
    except Exception as exc:
        record.update(parse_status="request_error", error_type=type(exc).__name__, fallback=True)
        raise
    finally:
        record["latency_ms"] = round((time.monotonic() - started) * 1000, 3)
        record["model"] = usage.get("model", record["model"])
