from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

from host import combat, state

ROOT = Path(__file__).resolve().parents[2]
FIXED_TIME = "2000-01-01T00:00:00+00:00"


@contextmanager
def isolated_engine(identity: str = "eval") -> Iterator[None]:
    """Single-process evaluation only: isolate engine globals and all save writes."""
    root = ROOT / ".tmp-test"
    root.mkdir(exist_ok=True)
    counter = 0

    def next_uuid() -> uuid.UUID:
        nonlocal counter
        counter += 1
        return uuid.UUID(hashlib.sha256(f"{identity}:{counter}".encode()).hexdigest()[:32])

    directory = root / f"eval-{uuid.uuid4().hex}"
    directory.mkdir()
    try:
        with patch.object(state, "SAVE_DIR", Path(directory)), \
             patch.object(state, "utc_now", return_value=FIXED_TIME), \
             patch.object(combat, "utc_now", return_value=FIXED_TIME), \
             patch.object(state.uuid, "uuid4", side_effect=next_uuid), \
             patch.object(state.random, "randint", side_effect=lambda low, high: min(high, max(low, 10))):
            yield
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def build_snapshot(recipe: dict[str, Any]) -> dict[str, Any]:
    with isolated_engine(recipe["id"]):
        public = state.create_session(str(ROOT / recipe["scenario"]), gm_mode=recipe["gm_mode"],
                                      character_id=recipe["character_id"])
        session = state.load_session(public["id"])
        for location in [*recipe.get("via", []), recipe["location_id"]]:
            moved, reason = state.commit_world_position(session, location_id=location)
            if not moved:
                raise ValueError(reason)
        session["flags"].update(deepcopy(recipe.get("flags", {})))
        actor = session["character"]
        actor["hp"] = max(0, min(actor["max_hp"], actor["hp"] + recipe.get("hp_delta", 0)))
        remove = set(recipe.get("inventory_remove", []))
        actor["inventory"] = [item for item in actor["inventory"] if not {item.get("id"), item.get("name")}.intersection(remove)]
        if recipe.get("inventory_add"):
            state.apply_state_delta(session, {"inventory_add": deepcopy(recipe["inventory_add"])})
        session["messages"] = []
        for message in recipe.get("recent_messages", []):
            add = state.add_assistant_message if message["speaker"] == "GM" else state.add_player_message
            add(session, message["text"], message["speaker"])
        session["needs_opening"] = False
        session["scenario_path"] = recipe["scenario"]
        state.save_session(session)
        return deepcopy(session)


def load_snapshot(identifier: str) -> dict[str, Any]:
    path = ROOT / "eval" / "snapshots" / f"{identifier}.json"
    return build_snapshot(json.loads(path.read_text(encoding="utf-8")))
