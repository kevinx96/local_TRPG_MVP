"""Shared offline-first helpers for spec 056 (no game defaults are changed)."""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

from host import free_actions, item_mechanics
from .snapshots import ROOT, load_snapshot

V2 = ROOT / "eval/benchmark/intent_v2.jsonl"
HIGH_RISK = frozenset({"injection", "declared_success", "impossible", "missing_item", "negation", "conditional"})
MODELS = (("gemini", "gemini-3.1-flash-lite"), ("gemini", "gemini-3.6-flash"),
          ("ollama", "qwen3-swallow-8b-rl-local"), ("ollama", "qwen2.5-7b-instruct-local"))


def read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


@contextmanager
def frozen_rules() -> Iterator[None]:
    with patch.object(item_mechanics, "LEGACY_ELEMENT_IDS", True), \
            patch.object(free_actions, "LEGACY_PLAN", True), \
            patch.object(free_actions, "OPERATIONS", free_actions.LEGACY_OPERATIONS):
        yield


def frozen_sessions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    sessions = {}
    for identifier in sorted({row["snapshot"] for row in rows}):
        if Path(identifier).name != identifier or not identifier.startswith("v2_"):
            raise ValueError("Expected a frozen v2 snapshot ID")
        recipe = json.loads((ROOT / "eval/snapshots" / f"{identifier}.json").read_text(encoding="utf-8"))
        if recipe["scenario"] != "eval/benchmark/scenario_frozen/dragon_rpg@f41af9d.json":
            raise ValueError("Snapshot does not use the frozen scenario")
        sessions[identifier] = load_snapshot(identifier)
    return sessions


def estimate(messages: list[list[dict[str, str]]], model: str, output_tokens: int,
             prices_path: Path = ROOT / "eval/prices.json", *, schema: dict[str, Any] = None) -> dict[str, Any]:
    rates = json.loads(prices_path.read_text(encoding="utf-8"))["models"].get(model)
    # Explicit approximation, not a tokenizer or a provider quotation. No cached-input discount.
    schema_chars = len(json.dumps(schema, ensure_ascii=False)) if schema is not None else 0
    input_tokens = sum((sum(len(m["content"]) for m in request) + schema_chars + 1) // 2 for request in messages)
    output_total = len(messages) * output_tokens
    cost = None if rates is None else (input_tokens * rates["input_per_million"] +
                                      output_total * rates["output_per_million"]) / 1_000_000
    result = {"calls": len(messages), "estimated_input_tokens": input_tokens,
              "output_token_budget": output_total, "estimated_cost_usd": cost,
              "prices_sha256": sha256(prices_path), "schema_chars_per_call": schema_chars,
              "assumption": "ceil((prompt + schema) characters / 2), output=max_tokens; retries/schema fallback excluded"}
    print(json.dumps({"estimate": result}, ensure_ascii=False), flush=True)
    return result
