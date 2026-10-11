from __future__ import annotations

import math
import time
from copy import deepcopy
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Optional
from urllib.parse import urlsplit

import requests


def retry_delay(response: requests.Response, fallback: float) -> float:
    value = response.headers.get("Retry-After")
    if value is not None:
        try:
            seconds = float(value)
        except ValueError:
            try:
                seconds = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError, OverflowError):
                seconds = float("nan")
        if math.isfinite(seconds):
            return max(0.0, seconds)
    try:
        for detail in response.json().get("error", {}).get("details", []):
            if str(detail.get("@type", "")).endswith("google.rpc.RetryInfo"):
                seconds = float(str(detail["retryDelay"]).removesuffix("s"))
                if math.isfinite(seconds) and seconds >= 0:
                    return seconds
    except (ValueError, TypeError, KeyError, AttributeError):
        pass
    return fallback


class RequestPolicy:
    """Shared across copied eval configs; rate-limit every HTTP attempt, including fallback."""
    def __init__(self, rpm: float, *, clock: Callable = time.monotonic, sleep: Callable = time.sleep):
        self.interval = 60 / rpm if rpm else 0
        self.clock = clock
        self.sleep = sleep
        self.last_request: Optional[float] = None
        self.warmed = False

    def __deepcopy__(self, memo: dict) -> RequestPolicy:
        return self

    def post(self, *args: Any, **kwargs: Any) -> requests.Response:
        for retry in range(6):
            if self.last_request is not None:
                wait = self.last_request + self.interval - self.clock()
                if wait > 0:
                    self.sleep(wait)
            self.last_request = self.clock()
            response = requests.post(*args, **kwargs)
            if response.status_code not in {429, 503} or retry == 5:
                return response
            delay = retry_delay(response, 2 ** retry)
            response.close()
            self.sleep(delay)
        raise AssertionError("unreachable")


def evaluation_config(config: dict[str, Any], backend: str, model: str, *,
                      rpm: Optional[float] = None, timeout: Optional[int] = None,
                      base_url: Optional[str] = None) -> dict[str, Any]:
    result = deepcopy(config)
    profile = result["backends"][backend]
    profile.update(model=model, fallback_models=[])
    if base_url:
        if urlsplit(base_url).hostname != urlsplit(profile.get("base_url", "")).hostname:
            profile.pop("headers", None)
            profile.pop("api_key", None)
        profile["base_url"] = base_url.rstrip("/")
        if backend == "ollama" and not profile["base_url"].endswith("/v1"):
            profile["base_url"] += "/v1"
    settings = result.get("eval", {})
    rpm = settings.get("rpm", {}).get(backend, 14 if backend == "gemini" else 0) if rpm is None else rpm
    timeout = timeout if timeout is not None else (60 if backend == "ollama" else result.get("request_timeout_seconds", 15))
    if not math.isfinite(float(rpm)) or rpm < 0 or timeout <= 0:
        raise ValueError("rpm must be nonnegative and timeout must be positive")
    result.update(active_backend=backend, debug_llm=False, trace_llm=False,
                  eval_ollama_schema_fallback=True, eval_timeout_seconds=timeout,
                  request_timeout_seconds=timeout, gameplay_timeout_seconds=timeout,
                  _request_policy=RequestPolicy(rpm))
    if backend == "ollama":
        result["disable_thinking"] = settings.get("disable_thinking", profile.get("disable_thinking", result.get("disable_thinking", True)))
    return result
