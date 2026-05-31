from __future__ import annotations

import json
import sys
from typing import Any, Iterable

import requests


class LLMClientError(RuntimeError):
    pass


def debug_log(message: str) -> None:
    message = message.encode("ascii", "backslashreplace").decode("ascii")
    print(f"[TRPG-DEBUG] {message}", file=sys.stderr, flush=True)


def active_backend(config: dict[str, Any]) -> dict[str, Any]:
    name = config.get("active_backend", "ollama")
    backends = config.get("backends") or {}
    backend = backends.get(name)
    if not isinstance(backend, dict):
        raise LLMClientError(f"Unknown backend profile: {name}")
    return backend


def stream_chat_completion(
    config: dict[str, Any],
    messages: list[dict[str, str]],
) -> Iterable[str]:
    debug_enabled = bool(config.get("debug_llm", True))
    backend = active_backend(config)
    backend_name = config.get("active_backend", "ollama")
    base_url = str(backend.get("base_url", "")).rstrip("/")
    if not base_url:
        raise LLMClientError("LLM backend base_url is empty.")
    payload = {
        "model": backend.get("model"),
        "messages": messages,
        "temperature": config.get("temperature", 0.8),
        "max_tokens": config.get("max_tokens", 900),
        "stream": True,
    }
    headers = {"Content-Type": "application/json"}
    api_key = backend.get("api_key") or "local"
    headers["Authorization"] = f"Bearer {api_key}"
    timeout = int(config.get("request_timeout_seconds", 120))
    url = f"{base_url}/chat/completions"

    if debug_enabled:
        total_chars = sum(len(message.get("content", "")) for message in messages)
        debug_log(
            "LLM request "
            f"backend={backend_name} url={url} model={payload['model']} "
            f"messages={len(messages)} chars={total_chars} stream=True timeout={timeout}s"
        )

    try:
        with requests.post(
            url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=timeout,
        ) as response:
            if debug_enabled:
                debug_log(
                    "LLM response headers "
                    f"status={response.status_code} content_type={response.headers.get('content-type', '')}"
                )
            if response.status_code >= 400:
                preview = response.text[:1000]
                if debug_enabled:
                    debug_log(f"LLM HTTP error body={preview!r}")
                    hint = _backend_diagnostic_hint(base_url)
                    if hint:
                        debug_log(hint)
                response.raise_for_status()
            chunk_count = 0
            content_chars = 0
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    line = line[6:]
                if line.strip() == "[DONE]":
                    if debug_enabled:
                        debug_log("LLM stream done marker received")
                    break
                content = _content_from_sse(line)
                if content:
                    chunk_count += 1
                    content_chars += len(content)
                    if debug_enabled and chunk_count <= 3:
                        debug_log(f"LLM chunk[{chunk_count}]={content[:160]!r}")
                    yield content
                elif debug_enabled:
                    debug_log(f"LLM stream line without content={line[:300]!r}")
            if debug_enabled:
                debug_log(f"LLM stream complete chunks={chunk_count} content_chars={content_chars}")
    except requests.RequestException as exc:
        if debug_enabled:
            debug_log(f"LLM request exception={exc!r}")
        raise LLMClientError(str(exc)) from exc


def _content_from_sse(line: str) -> str:
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return ""
    choices = data.get("choices") or []
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    if isinstance(delta.get("content"), str):
        return delta["content"]
    message = choices[0].get("message") or {}
    if isinstance(message.get("content"), str):
        return message["content"]
    return ""


def _backend_diagnostic_hint(base_url: str) -> str:
    if "localhost:11434" not in base_url and "127.0.0.1:11434" not in base_url:
        return ""
    try:
        tags = requests.get("http://localhost:11434/api/tags", timeout=3)
        tags.raise_for_status()
        models = tags.json().get("models") or []
    except requests.RequestException as exc:
        return f"Ollama diagnostic failed: {exc}"
    names = [str(model.get("name")) for model in models if model.get("name")]
    if not names:
        return "Ollama diagnostic: no models installed. Run `ollama pull <model>` or update host/config.json to an installed model."
    return "Ollama diagnostic: installed models=" + ", ".join(names)
