from __future__ import annotations

import json
import sys
import time
from typing import Any, Iterable, Optional, Union

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


def model_candidates(backend: dict[str, Any]) -> list[str]:
    candidates: list[str] = []
    primary = backend.get("model")
    if isinstance(primary, str) and primary.strip():
        candidates.append(primary.strip())
    fallbacks = backend.get("fallback_models") or []
    if isinstance(fallbacks, str):
        fallbacks = [fallbacks]
    if isinstance(fallbacks, list):
        for fallback in fallbacks:
            if isinstance(fallback, str) and fallback.strip() and fallback.strip() not in candidates:
                candidates.append(fallback.strip())
    return candidates


def stream_chat_completion(
    config: dict[str, Any],
    messages: list[dict[str, str]],
) -> Iterable[str]:
    debug_enabled = bool(config.get("debug_llm", True))
    backend = active_backend(config)
    backend_name = config.get("active_backend", "ollama")
    candidates = model_candidates(backend)
    if not candidates:
        raise LLMClientError("No LLM model configured.")

    last_error: Optional[LLMClientError] = None
    for index, model in enumerate(candidates, start=1):
        try:
            yield from _stream_chat_completion_once(config, backend, backend_name, model, messages, index, len(candidates))
            return
        except LLMClientError as exc:
            last_error = exc
            if debug_enabled and index < len(candidates):
                debug_log(f"LLM model fallback triggered failed_model={model} next_model={candidates[index]}")
    if last_error:
        raise last_error
    raise LLMClientError("LLM request failed before any model was attempted.")


def chat_completion(
    config: dict[str, Any],
    messages: list[dict[str, str]],
) -> str:
    debug_enabled = bool(config.get("debug_llm", True))
    backend = active_backend(config)
    backend_name = config.get("active_backend", "ollama")
    candidates = model_candidates(backend)
    if not candidates:
        raise LLMClientError("No LLM model configured.")

    last_error: Optional[LLMClientError] = None
    for index, model in enumerate(candidates, start=1):
        try:
            return _chat_completion_once(config, backend, backend_name, model, messages, index, len(candidates))
        except LLMClientError as exc:
            last_error = exc
            if debug_enabled and index < len(candidates):
                debug_log(f"LLM model fallback triggered failed_model={model} next_model={candidates[index]}")
    if last_error:
        raise last_error
    raise LLMClientError("LLM request failed before any model was attempted.")


def _chat_completion_once(
    config: dict[str, Any],
    backend: dict[str, Any],
    backend_name: str,
    model: str,
    messages: list[dict[str, str]],
    attempt: int,
    total_attempts: int,
) -> str:
    debug_enabled = bool(config.get("debug_llm", True))
    base_url = str(backend.get("base_url", "")).rstrip("/")
    if not base_url:
        raise LLMClientError("LLM backend base_url is empty.")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": config.get("temperature", 0.8),
        "max_tokens": config.get("max_tokens", 900),
        "stream": False,
    }
    _apply_response_format(payload, config)
    headers = _request_headers(backend)
    timeout = int(config.get("request_timeout_seconds", 1800))
    url = f"{base_url}/chat/completions"

    if debug_enabled:
        total_chars = sum(len(message.get("content", "")) for message in messages)
        role_summary = _message_role_summary(messages)
        debug_log(
            "LLM request "
            f"backend={backend_name} url={url} model={model} attempt={attempt}/{total_attempts} "
            f"messages={len(messages)} roles={role_summary} chars={total_chars} stream=False timeout={timeout}s"
        )

    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        ttfb_ms = (time.time() - start_time) * 1000
        if debug_enabled:
            debug_log(
                "LLM response headers "
                f"status={response.status_code} content_type={response.headers.get('content-type', '')} "
                f"ttfb_ms={ttfb_ms:.0f}"
            )
        if response.status_code >= 400:
            preview = response.text[:1000]
            if debug_enabled:
                debug_log(f"LLM HTTP error body={preview!r}")
                hint = _backend_diagnostic_hint(base_url)
                if hint:
                    debug_log(hint)
                remote_hint = _remote_gateway_hint(response.text)
                if remote_hint:
                    debug_log(remote_hint)
                forbidden_hint = _remote_forbidden_hint(response.status_code, response.text, base_url)
                if forbidden_hint:
                    debug_log(forbidden_hint)
            response.raise_for_status()
        unexpected_error = _unexpected_llm_body_error(response.text, response.headers.get("content-type", ""))
        if unexpected_error:
            if debug_enabled:
                debug_log(unexpected_error)
                debug_log(f"LLM unexpected body preview={response.text[:500]!r}")
            raise LLMClientError(unexpected_error)
        content = _content_from_completion(response.text)
        if debug_enabled:
            total_ms = (time.time() - start_time) * 1000
            debug_log(f"LLM completion received content_chars={len(content)} ttfb_ms={ttfb_ms:.0f} total_ms={total_ms:.0f}")
        return content
    except requests.RequestException as exc:
        if debug_enabled:
            debug_log(f"LLM request exception={exc!r}")
        raise LLMClientError(str(exc)) from exc


def _stream_chat_completion_once(
    config: dict[str, Any],
    backend: dict[str, Any],
    backend_name: str,
    model: str,
    messages: list[dict[str, str]],
    attempt: int,
    total_attempts: int,
) -> Iterable[str]:
    debug_enabled = bool(config.get("debug_llm", True))
    base_url = str(backend.get("base_url", "")).rstrip("/")
    if not base_url:
        raise LLMClientError("LLM backend base_url is empty.")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": config.get("temperature", 0.8),
        "max_tokens": config.get("max_tokens", 900),
        "stream": True,
    }
    _apply_response_format(payload, config)
    headers = _request_headers(backend)
    timeout = int(config.get("request_timeout_seconds", 1800))
    url = f"{base_url}/chat/completions"

    if debug_enabled:
        total_chars = sum(len(message.get("content", "")) for message in messages)
        role_summary = _message_role_summary(messages)
        debug_log(
            "LLM request "
            f"backend={backend_name} url={url} model={model} attempt={attempt}/{total_attempts} "
            f"messages={len(messages)} roles={role_summary} chars={total_chars} stream=True timeout={timeout}s"
        )

    try:
        start_time = time.time()
        with requests.post(
            url,
            headers=headers,
            json=payload,
            stream=True,
            timeout=timeout,
        ) as response:
            ttfb_ms = (time.time() - start_time) * 1000
            if debug_enabled:
                debug_log(
                    "LLM response headers "
                    f"status={response.status_code} content_type={response.headers.get('content-type', '')} "
                    f"ttfb_ms={ttfb_ms:.0f}"
                )
            if response.status_code >= 400:
                preview = response.text[:1000]
                if debug_enabled:
                    debug_log(f"LLM HTTP error body={preview!r}")
                    hint = _backend_diagnostic_hint(base_url)
                    if hint:
                        debug_log(hint)
                    remote_hint = _remote_gateway_hint(response.text)
                    if remote_hint:
                        debug_log(remote_hint)
                    forbidden_hint = _remote_forbidden_hint(response.status_code, response.text, base_url)
                    if forbidden_hint:
                        debug_log(forbidden_hint)
                response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type.lower():
                body = response.text
                unexpected_error = _unexpected_llm_body_error(body, content_type)
                if unexpected_error:
                    if debug_enabled:
                        debug_log(unexpected_error)
                        debug_log(f"LLM unexpected body preview={body[:500]!r}")
                    raise LLMClientError(unexpected_error)
            chunk_count = 0
            content_chars = 0
            for raw_line in response.iter_lines(decode_unicode=False):
                line = _decode_sse_line(raw_line)
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
                total_ms = (time.time() - start_time) * 1000
                debug_log(f"LLM stream complete chunks={chunk_count} content_chars={content_chars} ttfb_ms={ttfb_ms:.0f} total_ms={total_ms:.0f}")
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


def _content_from_completion(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMClientError(f"Invalid LLM JSON response: {exc}") from exc
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    if isinstance(message.get("content"), str):
        return message["content"]
    text_value = choices[0].get("text")
    if isinstance(text_value, str):
        return text_value
    return ""


def _unexpected_llm_body_error(text: str, content_type: str) -> str:
    lower_type = content_type.lower()
    lower_text = text[:2000].lower()
    if "cloudflare access" in lower_text or "sign in" in lower_text and "cloudflare" in lower_text:
        return (
            "Cloudflare Access returned a sign-in page instead of LLM JSON. "
            "Add a Service Auth policy for this service token on the Access application."
        )
    if "text/html" in lower_type:
        return "LLM backend returned HTML instead of OpenAI-compatible JSON."
    return ""


def _remote_gateway_hint(text: str) -> str:
    lower_text = text[:2000].lower()
    if "cloudflare" in lower_text and "502: bad gateway" in lower_text:
        return (
            "Cloudflare tunnel reached Access but could not reach the origin. "
            "Check the tunnel Public Hostname service URL; for local Ollama it should usually be "
            "`http://127.0.0.1:11434` or `http://localhost:11434`."
        )
    return ""


def _remote_forbidden_hint(status_code: int, text: str, base_url: str) -> str:
    if status_code == 403 and not text.strip() and "localhost" not in base_url and "127.0.0.1" not in base_url:
        return (
            "Remote Ollama returned an empty 403. If this is behind Cloudflare Tunnel, "
            "set the Public Hostname HTTP Host Header to `localhost:11434` because Ollama rejects "
            "requests whose Host header is the public domain."
        )
    return ""


def _decode_sse_line(raw_line: Union[bytes, str]) -> str:
    if isinstance(raw_line, str):
        return raw_line
    return raw_line.decode("utf-8", errors="replace")


def _apply_response_format(payload: dict[str, Any], config: dict[str, Any]) -> None:
    response_format = config.get("response_format")
    if response_format is None:
        return
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}
        return
    if isinstance(response_format, dict):
        payload["response_format"] = response_format


def _request_headers(backend: dict[str, Any]) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = backend.get("api_key") or "local"
    headers["Authorization"] = f"Bearer {api_key}"
    extra_headers = backend.get("headers")
    if isinstance(extra_headers, dict):
        for key, value in extra_headers.items():
            if isinstance(key, str) and key.strip() and value is not None:
                headers[key.strip()] = str(value)
    return headers


def _message_role_summary(messages: list[dict[str, str]]) -> str:
    counts: dict[str, int] = {}
    for message in messages:
        role = str(message.get("role") or "unknown")
        counts[role] = counts.get(role, 0) + 1
    return ",".join(f"{role}:{counts[role]}" for role in sorted(counts))


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
