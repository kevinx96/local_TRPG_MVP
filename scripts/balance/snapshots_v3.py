"""Portable, deterministic opening snapshots and engine-backed level probes."""
from __future__ import annotations

from copy import deepcopy
from typing import Any
from unittest.mock import patch

from host import progression
from . import checkpoints
from .archetypes import PassivePicker

KEYS = ("character", "world_state", "flags", "companion", "completed_milestones",
        "progression_revision", "pending_passive_choices", "shop_stock", "_balance_exp_sources")


def capture(session: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(session[key]) for key in KEYS if key in session}


def restore(pack: dict[str, Any], snapshot: dict[str, Any], difficulty: str = "normal") -> dict[str, Any]:
    session = checkpoints.fresh_session(pack, snapshot["character"]["character_id"], difficulty, effective=True)
    session.update(deepcopy(snapshot))
    session["combat"] = None
    session["game_over"] = None
    return session


def at_level(session: dict[str, Any], level: int, table: dict[str, str]) -> dict[str, Any]:
    """Rebuild progression through the engine; retain equipment and nonlevel gains."""
    pack = session["scenario_pack"]
    maximum = pack["progression"]["max_level"]
    if not 1 <= level <= maximum:
        raise ValueError("Probe level outside engine cap")
    result = deepcopy(session, {id(pack): pack})
    actor = result["character"]
    previous = actor["level"]
    history = [progression.gains_at_level(pack["progression"], actor["character_id"], old_level)
               for old_level in range(2, previous + 1)]
    for resource in ("hp", "mp", "sp"):
        key = "max_" + resource
        actor[key] -= sum(gains.get(key, 0) for gains in history)
        actor[resource] = actor[key]
    for gains in history:
        for key, value in gains.get("attributes", {}).items():
            actor["attributes"][key] -= value
    active_ids = {a["skill"]["id"] for a in progression.definition(result).get("actives", [])}
    actor["skills"] = [s for s in actor["skills"] if s["id"] not in active_ids]
    actor.update(level=1, exp=0, passives=[], passive_history={})
    result["pending_passive_choices"] = []
    target_exp = pack["progression"]["exp_table"].get(str(level), 0)
    progression.reward(result, target_exp, "probe:level")
    return PassivePicker("table", table).apply(result)


class ExpObserver:
    """Observe awards before the engine's bounded event log can evict them."""
    def __init__(self):
        self.original = progression.reward

    def reward(self, session, amount, source):
        before = session["character"].get("exp", 0)
        self.original(session, amount, source)
        awarded = session["character"].get("exp", 0)-before
        if awarded:
            category = "quest" if source.startswith("quest:") else (session.get("combat") or {}).get("encounter", {}).get("encounter_class", "unclassified")
            if category not in {"trash", "elite", "boss", "quest"}:
                category = "unclassified"
            ledger = session.setdefault("_balance_exp_sources", {k: 0 for k in ("trash", "elite", "boss", "unclassified", "quest")})
            ledger[category] += awarded

    def __enter__(self):
        self.context = patch.object(progression, "reward", self.reward)
        self.context.__enter__()
        return self

    def __exit__(self, *args):
        return self.context.__exit__(*args)
