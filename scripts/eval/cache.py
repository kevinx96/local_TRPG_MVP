from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional


def cache_key(backend: str, model: str, variant: str, messages: list, config: dict[str, Any]) -> str:
    if variant == "lenient":
        variant = "default"
    value = {"backend": backend, "model": model, "variant": variant, "messages": messages,
             "config": {k: config.get(k) for k in ("temperature", "max_tokens", "response_format")}}
    if "disable_thinking" in config:
        value["config"]["disable_thinking"] = config["disable_thinking"]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def read_cache(directory: Path, key: str) -> Optional[dict[str, Any]]:
    try:
        record = json.loads((directory / f"{key}.json").read_text(encoding="utf-8"))
        if record.get("key") == key and isinstance(record.get("raw_response"), str):
            return record
    except (OSError, ValueError, AttributeError):
        pass
    return None


def write_cache(directory: Path, key: str, record: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / f"{key}.tmp"
    temporary.write_text(json.dumps({"key": key, **record}, ensure_ascii=False), encoding="utf-8")
    temporary.replace(directory / f"{key}.json")
