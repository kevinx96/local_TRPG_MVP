from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Iterable, Iterator, Optional, Union
from urllib.parse import quote, urlsplit

import requests


class LLMClientError(RuntimeError):
    pass


class LLMKeyError(LLMClientError):
    """A credential failure, including quota exhaustion; retry with the next key."""


class LLMWorkerError(LLMClientError):
    """A proxy rejection that must not retry local credentials or models."""


ALL_KEYS_EXHAUSTED = "すべての API キーが上限に達したか、無効です。"
WORKER_KEYS_EXHAUSTED = "The demo's API keys are all used up. Please try again later."
_session: ContextVar = ContextVar("llm_session", default=None)


@contextmanager
def session_keys(session: dict[str, Any]) -> Iterator[None]:
    token = _session.set(session)
    try:
        yield
    finally:
        _session.reset(token)


def backend_api_keys(backend_name: str, backend: dict[str, Any]) -> list[str]:
    if "api_keys" in backend:
        keys = backend["api_keys"]
        if not isinstance(keys, list) or any(not isinstance(key, str) for key in keys):
            raise LLMClientError("api_keys must be a list of strings.")
        return [key.strip() for key in keys]
    if _is_worker_backend(backend_name, backend):
        # A demo token must never be replaced by a personal Gemini environment key.
        return [str(backend.get("api_key") or "").strip()]
    if _is_gemini_backend(backend_name, backend):
        env_keys = os.environ.get("GEMINI_API_KEYS", "").strip()
        if env_keys:
            return [key.strip() for key in env_keys.split(",")]
    api_key = str(backend.get("api_key") or "").strip()
    if api_key:
        return [api_key]
    if _is_gemini_backend(backend_name, backend):
        from .scenario_converter import load_gemini_api_key
        return [load_gemini_api_key().strip()]
    return [""]


def redact_api_keys(text: str, keys: Iterable[str]) -> str:
    for key in sorted({key for key in keys if key}, key=len, reverse=True):
        text = text.replace(key, "[REDACTED]").replace(quote(key, safe=""), "[REDACTED]")
    return text


def is_key_failure(status: Optional[int], body: str) -> bool:
    if status in {401, 403, 429}:
        return True
    if status != 400:
        return False
    return bool(re.search(r"API[_ ]?KEY[_ ](?:INVALID|EXPIRED)|(?:invalid|expired) API[ _]key|"
                          r"API[ _]key (?:is )?(?:not valid|invalid|expired)", body, re.IGNORECASE))


class KeyRotation:
    def __init__(self, backend_name: str, backend: dict[str, Any],
                 session: Optional[dict[str, Any]] = None):
        self.worker = _is_worker_backend(backend_name, backend)
        self.backend = ({**backend, "_worker_session": session if session is not None else {}}
                        if self.worker else backend)
        self.keys = backend_api_keys(backend_name, backend)
        self.failed = (session.setdefault("llm_failed_keys", {}).setdefault(backend_name, [])
                       if session is not None and not self.worker else [])
        self.last_error: Optional[LLMKeyError] = None

    def attempts(self) -> Iterable[tuple[dict[str, Any], dict[str, Any]]]:
        for index, key in enumerate(self.keys):
            if not key and (len(self.keys) != 1 or "api_keys" in self.backend):
                continue
            marker = {"index": index, "sha256": hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]}
            if any(failed.get("sha256") == marker["sha256"] for failed in self.failed):
                continue
            yield {**self.backend, "_selected_api_key": key, "_redact_keys": self.keys}, marker
            if self.worker:
                return

    def reject(self, marker: dict[str, Any], error: LLMKeyError) -> None:
        if self.worker:
            # Preserve request-policy quota metadata without rejecting the demo token.
            error.args = (redact_api_keys(str(error), self.keys),)
            raise error from None
        if marker not in self.failed:
            self.failed.append(marker)
        # Preserve structured quota metadata used by the evaluation runner.
        if self.last_error is None or not hasattr(self.last_error, "details"):
            self.last_error = error

    def exhausted(self) -> LLMClientError:
        error = self.last_error or LLMClientError(ALL_KEYS_EXHAUSTED)
        error.args = (ALL_KEYS_EXHAUSTED,)
        return error

    def call(self, call: Callable[[dict[str, Any]], str]) -> str:
        for backend, marker in self.attempts():
            try:
                return redact_api_keys(call(backend), self.keys)
            except LLMKeyError as exc:
                self.reject(marker, exc)
            except LLMClientError as exc:
                exc.args = (redact_api_keys(str(exc), self.keys),)
                raise exc from None
        raise self.exhausted() from None

    def sdk_call(self, call: Callable[[dict[str, Any]], str]) -> str:
        def attempt(backend: dict[str, Any]) -> str:
            try:
                return call(backend)
            except LLMClientError:
                raise
            except Exception as exc:
                status = getattr(exc, "code", None)
                detail = f"{exc} {getattr(exc, 'reason', '')}"
                if is_key_failure(status, detail):
                    raise LLMKeyError(f"LLM credential rejected (HTTP {status}).") from None
                raise LLMClientError(redact_api_keys(str(exc), self.keys)) from None
        return self.call(attempt)


def _backend_debug_log(backend: dict[str, Any], message: str) -> None:
    debug_log(redact_api_keys(message, backend.get("_redact_keys", [])))


def _check_key_failure(response: requests.Response) -> None:
    if is_key_failure(response.status_code, response.text):
        raise LLMKeyError(f"LLM credential rejected (HTTP {response.status_code}).")


def _post(config: dict[str, Any], *args: Any, **kwargs: Any) -> requests.Response:
    policy = config.get("_request_policy")
    if policy is not None:
        keys = backend_api_keys(config.get("active_backend", "gemini"), active_backend(config))
        return policy.post(*args, key_rotation=True, redact_keys=keys, **kwargs)
    return requests.post(*args, **kwargs)


class LLMBlockedError(LLMClientError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"LLM response blocked: {reason}")


def debug_log(message: str) -> None:
    message = message.encode("ascii", "backslashreplace").decode("ascii")
    print(f"[TRPG-DEBUG] {message}", file=sys.stderr, flush=True)


def active_backend(config: dict[str, Any]) -> dict[str, Any]:
    name = config.get("active_backend", "gemini")
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
    session: Optional[dict[str, Any]] = None,
) -> Iterable[str]:
    debug_enabled = bool(config.get("debug_llm", True))
    backend = active_backend(config)
    backend_name = config.get("active_backend", "gemini")
    candidates = model_candidates(backend)[:max(1, int(config.get("max_model_attempts", 1)))]
    if not candidates:
        raise LLMClientError("No LLM model configured.")

    rotation = KeyRotation(backend_name, backend, session if session is not None else _session.get())
    last_error: Optional[LLMClientError] = None
    for index, model in enumerate(candidates, start=1):
        try:
            for selected, marker in rotation.attempts():
                try:
                    for content in _stream_chat_completion_once(config, selected, backend_name, model, messages, index, len(candidates)):
                        yield redact_api_keys(content, rotation.keys)
                    return
                except LLMKeyError as exc:
                    rotation.reject(marker, exc)
            raise rotation.exhausted()
        except LLMWorkerError:
            raise
        except LLMClientError as exc:
            if (rotation.worker and isinstance(exc, LLMKeyError)) or not any(rotation.attempts()):
                raise
            exc.args = (redact_api_keys(str(exc), rotation.keys),)
            last_error = exc
            if debug_enabled and index < len(candidates):
                debug_log(f"LLM model fallback triggered failed_model={model} next_model={candidates[index]}")
    if last_error:
        raise last_error
    raise LLMClientError("LLM request failed before any model was attempted.")


def chat_completion(
    config: dict[str, Any],
    messages: list[dict[str, str]],
    usage_out: Optional[dict[str, Any]] = None,
    session: Optional[dict[str, Any]] = None,
) -> str:
    debug_enabled = bool(config.get("debug_llm", True))
    backend = active_backend(config)
    backend_name = config.get("active_backend", "gemini")
    candidates = model_candidates(backend)[:max(1, int(config.get("max_model_attempts", 1)))]
    if not candidates:
        raise LLMClientError("No LLM model configured.")

    rotation = KeyRotation(backend_name, backend, session if session is not None else _session.get())
    last_error: Optional[LLMClientError] = None
    for index, model in enumerate(candidates, start=1):
        try:
            return rotation.call(lambda selected: _chat_completion_once(
                config, selected, backend_name, model, messages, index, len(candidates), usage_out))
        except LLMWorkerError:
            raise
        except LLMClientError as exc:
            if (rotation.worker and isinstance(exc, LLMKeyError)) or not any(rotation.attempts()):
                raise
            last_error = exc
            if debug_enabled and index < len(candidates):
                debug_log(f"LLM model fallback triggered failed_model={model} next_model={candidates[index]}")
        finally:
            if usage_out is not None:
                sanitized = json.loads(redact_api_keys(json.dumps(usage_out), rotation.keys))
                usage_out.clear()
                usage_out.update(sanitized)
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
    usage_out: Optional[dict[str, Any]] = None,
) -> str:
    if _is_gemini_backend(backend_name, backend):
        return _gemini_chat_completion_once(config, backend, backend_name, model, messages, attempt, total_attempts, usage_out)

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
    if backend_name == "ollama" and config.get("disable_thinking", backend.get("disable_thinking", False)):
        payload["reasoning_effort"] = "none"
    headers = _request_headers(backend)
    timeout = min(int(config.get("request_timeout_seconds", 15)), int(config.get("gameplay_timeout_seconds", 15)))
    url = f"{base_url}/chat/completions"

    if debug_enabled:
        total_chars = sum(len(message.get("content", "")) for message in messages)
        role_summary = _message_role_summary(messages)
        _backend_debug_log(backend,
            "LLM request "
            f"backend={backend_name} url={url} model={model} attempt={attempt}/{total_attempts} "
            f"messages={len(messages)} roles={role_summary} chars={total_chars} stream=False timeout={timeout}s"
        )

    try:
        start_time = time.time()
        response = _post(config, url, headers=headers, json=payload, timeout=timeout)
        ttfb_ms = (time.time() - start_time) * 1000
        if debug_enabled:
            _backend_debug_log(backend,
                "LLM response headers "
                f"status={response.status_code} content_type={response.headers.get('content-type', '')} "
                f"ttfb_ms={ttfb_ms:.0f}"
            )
        if response.status_code >= 400:
            _check_key_failure(response)
            preview = redact_api_keys(response.text, backend.get("_redact_keys", []))[:1000]
            if (backend_name == "ollama" and config.get("eval_ollama_schema_fallback")
                    and response.status_code in {400, 422}
                    and any(word in response.text.lower() for word in ("response_format", "json_schema"))):
                return _ollama_native_completion(config, backend, model, messages, usage_out)
            if debug_enabled:
                _backend_debug_log(backend, f"LLM HTTP error body={preview!r}")
                hint = _backend_diagnostic_hint(base_url)
                if hint:
                    _backend_debug_log(backend, hint)
                remote_hint = _remote_gateway_hint(response.text)
                if remote_hint:
                    _backend_debug_log(backend, remote_hint)
                forbidden_hint = _remote_forbidden_hint(response.status_code, response.text, base_url)
                if forbidden_hint:
                    _backend_debug_log(backend, forbidden_hint)
            response.raise_for_status()
        unexpected_error = _unexpected_llm_body_error(response.text, response.headers.get("content-type", ""))
        if unexpected_error:
            if debug_enabled:
                _backend_debug_log(backend, unexpected_error)
                _backend_debug_log(backend, f"LLM unexpected body preview={response.text[:500]!r}")
            raise LLMClientError(unexpected_error)
        content = _content_from_completion(response.text)
        if usage_out is not None:
            _collect_usage(json.loads(response.text), usage_out, model)
        if debug_enabled:
            total_ms = (time.time() - start_time) * 1000
            _backend_debug_log(backend, f"LLM completion received content_chars={len(content)} ttfb_ms={ttfb_ms:.0f} total_ms={total_ms:.0f}")
        return content
    except requests.RequestException as exc:
        if debug_enabled:
            _backend_debug_log(backend, f"LLM request exception={exc!r}")
        raise LLMClientError(redact_api_keys(str(exc), backend.get("_redact_keys", []))) from None


def _stream_chat_completion_once(
    config: dict[str, Any],
    backend: dict[str, Any],
    backend_name: str,
    model: str,
    messages: list[dict[str, str]],
    attempt: int,
    total_attempts: int,
) -> Iterable[str]:
    if _is_gemini_backend(backend_name, backend):
        content = _gemini_chat_completion_once(config, backend, backend_name, model, messages, attempt, total_attempts)
        if content:
            yield content
        return

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
    if backend_name == "ollama" and config.get("disable_thinking", backend.get("disable_thinking", False)):
        payload["reasoning_effort"] = "none"
    headers = _request_headers(backend)
    timeout = min(int(config.get("request_timeout_seconds", 15)), int(config.get("gameplay_timeout_seconds", 15)))
    url = f"{base_url}/chat/completions"

    if debug_enabled:
        total_chars = sum(len(message.get("content", "")) for message in messages)
        role_summary = _message_role_summary(messages)
        _backend_debug_log(backend,
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
                _backend_debug_log(backend,
                    "LLM response headers "
                    f"status={response.status_code} content_type={response.headers.get('content-type', '')} "
                    f"ttfb_ms={ttfb_ms:.0f}"
                )
            if response.status_code >= 400:
                _check_key_failure(response)
                preview = redact_api_keys(response.text, backend.get("_redact_keys", []))[:1000]
                if debug_enabled:
                    _backend_debug_log(backend, f"LLM HTTP error body={preview!r}")
                    hint = _backend_diagnostic_hint(base_url)
                    if hint:
                        _backend_debug_log(backend, hint)
                    remote_hint = _remote_gateway_hint(response.text)
                    if remote_hint:
                        _backend_debug_log(backend, remote_hint)
                    forbidden_hint = _remote_forbidden_hint(response.status_code, response.text, base_url)
                    if forbidden_hint:
                        _backend_debug_log(backend, forbidden_hint)
                response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type.lower():
                body = response.text
                unexpected_error = _unexpected_llm_body_error(body, content_type)
                if unexpected_error:
                    if debug_enabled:
                        _backend_debug_log(backend, unexpected_error)
                        _backend_debug_log(backend, f"LLM unexpected body preview={body[:500]!r}")
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
                        _backend_debug_log(backend, "LLM stream done marker received")
                    break
                content = _content_from_sse(line)
                if content:
                    chunk_count += 1
                    content_chars += len(content)
                    if debug_enabled and chunk_count <= 3:
                        _backend_debug_log(backend, f"LLM chunk[{chunk_count}]={content[:160]!r}")
                    yield content
                elif debug_enabled:
                    _backend_debug_log(backend, f"LLM stream line without content={line[:300]!r}")
            if debug_enabled:
                total_ms = (time.time() - start_time) * 1000
                _backend_debug_log(backend, f"LLM stream complete chunks={chunk_count} content_chars={content_chars} ttfb_ms={ttfb_ms:.0f} total_ms={total_ms:.0f}")
    except requests.RequestException as exc:
        if debug_enabled:
            _backend_debug_log(backend, f"LLM request exception={exc!r}")
        raise LLMClientError(redact_api_keys(str(exc), backend.get("_redact_keys", []))) from None


def _is_gemini_backend(backend_name: str, backend: dict[str, Any]) -> bool:
    backend_type = str(backend.get("type") or "").strip().lower()
    return backend_name.lower() == "gemini" or backend_type == "gemini"


def _is_worker_backend(backend_name: str, backend: dict[str, Any]) -> bool:
    base_url = str(backend.get("base_url") or "")
    return (_is_gemini_backend(backend_name, backend) and bool(base_url)
            and urlsplit(base_url).hostname != "generativelanguage.googleapis.com")


def _worker_response(response: requests.Response, backend: dict[str, Any], backend_name: str) -> None:
    session = backend.get("_worker_session", {})
    slot_text = response.headers.get("x-trpg-key-slot", "")
    slot = int(slot_text) if re.fullmatch(r"[0-9]{1,16}", slot_text) else None
    if slot is not None:
        session.setdefault("llm_worker_key_slot", {})[backend_name] = slot
    if not is_key_failure(response.status_code, response.text):
        return
    if (response.status_code == 429 and response.headers.get("x-trpg-proxy-limit") != "1"
            and slot is not None):
        # The exhausted slot equals the key count; sending it back would reset to 0.
        session.setdefault("llm_worker_keys_exhausted", {})[backend_name] = True
    try:
        data = response.json()
        message = str(data["error"]["message"])
    except (ValueError, KeyError, TypeError):
        message = f"LLM request failed (HTTP {response.status_code})."
    raise LLMWorkerError(redact_api_keys(message, backend.get("_redact_keys", [])))


def _gemini_chat_completion_once(
    config: dict[str, Any],
    backend: dict[str, Any],
    backend_name: str,
    model: str,
    messages: list[dict[str, str]],
    attempt: int,
    total_attempts: int,
    usage_out: Optional[dict[str, Any]] = None,
) -> str:
    debug_enabled = bool(config.get("debug_llm", True))
    api_key = _gemini_api_key(backend)
    if not api_key:
        raise LLMClientError("Gemini API key is empty. Set GEMINI_API_KEYS / GEMINI_API_KEY, or put api_keys in local_config.json (next to LocalTRPG.exe in the packaged build; host/local_config.json in development).")

    base_url = str(backend.get("base_url") or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    timeout = min(int(config.get("request_timeout_seconds", 15)), int(config.get("gameplay_timeout_seconds", 15)))
    url = f"{base_url}/models/{quote(model, safe='')}:generateContent"
    payload = _gemini_payload(messages, config)
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    worker = _is_worker_backend(backend_name, backend)
    if worker:
        session = backend.get("_worker_session", {})
        if session.get("llm_worker_keys_exhausted", {}).get(backend_name):
            raise LLMWorkerError(WORKER_KEYS_EXHAUSTED)
        slot = session.get("llm_worker_key_slot", {}).get(backend_name, 0)
        headers["x-trpg-key-start"] = str(slot if type(slot) is int and slot >= 0 else 0)

    if debug_enabled:
        total_chars = sum(len(message.get("content", "")) for message in messages)
        role_summary = _message_role_summary(messages)
        _backend_debug_log(backend,
            "LLM request "
            f"backend={backend_name} url={base_url}/models/{model}:generateContent model={model} "
            f"attempt={attempt}/{total_attempts} messages={len(messages)} roles={role_summary} "
            f"chars={total_chars} stream=False timeout={timeout}s"
        )

    try:
        start_time = time.time()
        response = _post(config, url, headers=headers, json=payload, timeout=timeout)
        if worker:
            _worker_response(response, backend, backend_name)
        ttfb_ms = (time.time() - start_time) * 1000
        if debug_enabled:
            _backend_debug_log(backend,
                "LLM response headers "
                f"status={response.status_code} content_type={response.headers.get('content-type', '')} "
                f"ttfb_ms={ttfb_ms:.0f}"
            )
        if response.status_code >= 400:
            if not worker:
                _check_key_failure(response)
            preview = redact_api_keys(response.text, backend.get("_redact_keys", []))[:1000]
            if debug_enabled:
                _backend_debug_log(backend, f"LLM HTTP error body={preview!r}")
            response.raise_for_status()
        if usage_out is not None:
            try:
                _collect_usage(json.loads(response.text), usage_out, model)
            except (ValueError, TypeError):
                pass
        content = _content_from_gemini_response(response.text)
        if debug_enabled:
            total_ms = (time.time() - start_time) * 1000
            _backend_debug_log(backend, f"LLM completion received content_chars={len(content)} ttfb_ms={ttfb_ms:.0f} total_ms={total_ms:.0f}")
        return content
    except requests.RequestException as exc:
        if debug_enabled:
            _backend_debug_log(backend, f"LLM request exception={exc!r}")
        raise LLMClientError(redact_api_keys(str(exc), backend.get("_redact_keys", []))) from None


def _gemini_api_key(backend: dict[str, Any]) -> str:
    if "_selected_api_key" in backend:
        return backend["_selected_api_key"]
    return next((key for key in backend_api_keys("gemini", backend) if key), "")


def _gemini_payload(messages: list[dict[str, str]], config: dict[str, Any]) -> dict[str, Any]:
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role") or "user").strip().lower()
        content = str(message.get("content") or "")
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
            continue
        gemini_role = "model" if role in {"assistant", "model"} else "user"
        contents.append({"role": gemini_role, "parts": [{"text": content}]})
    if not contents:
        contents.append({"role": "user", "parts": [{"text": "開始してください。"}]})

    generation_config: dict[str, Any] = {
        "temperature": config.get("temperature", 0.8),
        "maxOutputTokens": config.get("max_tokens", 900),
    }
    if config.get("response_format") == "json_object":
        generation_config["responseMimeType"] = "application/json"
    response_format = config.get("response_format")
    if isinstance(response_format, dict) and response_format.get("type") == "json_schema":
        schema = (response_format.get("json_schema") or {}).get("schema")
        if isinstance(schema, dict):
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseJsonSchema"] = schema

    payload: dict[str, Any] = {
        "contents": contents,
        "generationConfig": generation_config,
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
    return payload


def _content_from_gemini_response(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMClientError(f"Invalid Gemini JSON response: {exc}") from exc
    if not isinstance(data, dict):
        return ""
    if isinstance(data.get("error"), dict):
        error = data["error"]
        raise LLMClientError(str(error.get("message") or error))
    reason = (data.get("promptFeedback") or {}).get("blockReason")
    if reason:
        raise LLMBlockedError(str(reason))
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        return ""
    reason = candidate.get("finishReason")
    if reason in {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION"}:
        raise LLMBlockedError(str(reason))
    if reason == "MAX_TOKENS":
        debug_log("Gemini finishReason=MAX_TOKENS; returning available content")
    content = candidate.get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    texts = [part.get("text", "") for part in parts if isinstance(part, dict) and isinstance(part.get("text"), str)]
    return "".join(texts)


def _collect_usage(data: dict[str, Any], usage_out: dict[str, Any], model: str) -> None:
    """Keep provider counters and normalize absent counters to null, not zero."""
    gemini = data.get("usageMetadata") or {}
    usage = data.get("usage") or {}
    usage_out.update({
        "model": model,
        "input_tokens": gemini.get("promptTokenCount", data.get("prompt_eval_count", usage.get("prompt_tokens"))),
        "output_tokens": gemini.get("candidatesTokenCount", data.get("eval_count", usage.get("completion_tokens"))),
        "cached_tokens": gemini.get("cachedContentTokenCount", (usage.get("prompt_tokens_details") or {}).get("cached_tokens")),
    })
    if gemini:
        usage_out["usageMetadata"] = gemini
    for key in ("prompt_eval_count", "eval_count"):
        if key in data:
            usage_out[key] = data[key]


def _ollama_native_completion(config: dict[str, Any], backend: dict[str, Any], model: str,
                              messages: list[dict[str, str]], usage_out: Optional[dict[str, Any]]) -> str:
    base_url = str(backend["base_url"]).rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    schema = (config.get("response_format") or {}).get("json_schema", {}).get("schema", "json")
    payload = {"model": model, "messages": messages, "stream": False, "format": schema,
               "options": {"temperature": config.get("temperature", 0.8),
                           "num_predict": config.get("max_tokens", 900)}}
    if config.get("disable_thinking", backend.get("disable_thinking", False)):
        payload["think"] = False
    try:
        response = _post(config, f"{base_url}/api/chat", headers=_request_headers(backend), json=payload,
                                 timeout=min(config.get("request_timeout_seconds", 15), config.get("gameplay_timeout_seconds", 15)))
        _check_key_failure(response)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise LLMClientError(str(data["error"]))
        if usage_out is not None:
            _collect_usage(data, usage_out, model)
            usage_out["transport"] = "ollama_native_format"
        return str((data.get("message") or {}).get("content") or "")
    except (requests.RequestException, ValueError) as exc:
        raise LLMClientError(redact_api_keys(str(exc), backend.get("_redact_keys", []))) from None


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
    api_key = backend.get("_selected_api_key", backend.get("api_key")) or "local"
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
