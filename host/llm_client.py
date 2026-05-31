from __future__ import annotations

import json
from typing import Any, Iterable

import requests


class LLMClientError(RuntimeError):
    pass


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
    backend = active_backend(config)
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

    try:
        with requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    line = line[6:]
                if line.strip() == "[DONE]":
                    break
                content = _content_from_sse(line)
                if content:
                    yield content
    except requests.RequestException as exc:
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
