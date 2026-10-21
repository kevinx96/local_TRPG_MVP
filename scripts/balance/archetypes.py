from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from itertools import product
from pathlib import Path
from typing import Any, Iterable, Optional, Protocol

CHARACTERS = ("hero", "cleric", "mage", "thief")
DEFAULT_PASSIVES = Path(__file__).resolve().parents[2] / "eval/balance/passive_defaults.json"
COMPLETION_TITLE = "冒険完了"
IGNIS_FLAGS = ("defeated_ignis", "ignis_purified")
TERMINAL_LOCATION = "draco_battle"
MAINLINE_NODES = ("castle", "dark_forest_loc", "elf_spring", "forest_exit",
                  "village_frozen_clue", "ian_ice_katana_aftermath", "valley_entrance",
                  "dragon_valley_loc", "royal_gate", "draco_battle")
SIDEQUESTS = {"gald", "riku", "cave_full", "fort", "purification", "town_errands", "mina",
              "battlefield", "oaksdawn", "gorge", "mansion", "merchant", "robin", "sarah",
              "hearth", "nameless_soldiers", "fire_seed"}


@dataclass(frozen=True)
class Archetype:
    id: str
    optional_interactions: tuple[str, ...]
    companion_rule: str
    equipment_rule: str
    shopping_rule: str
    sidequests: tuple[str, ...]
    combat_policy: str
    rest_rule: str = "free_hp70"
    recovery_threshold: float = .30
    optional_limit: Optional[int] = None
    avoid_battles: bool = False
    grind: bool = False
    passive_mode: str = "first"
    decision_rule: str = "backbone"
    status: str = "proposed"
    spring_rest: str = "first_hp70"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


P0A = Archetype("P0a", (), "none", "initial", "none", (), "best_free", optional_limit=0)
P0B = Archetype("P0b", ("ask_king_info", "shop:sarah_shop:ice_charm", "borrow_fire_bat_dragon"),
               "fire_bat_dragon", "equip_acquired", "hinted_one", (), "best_free", optional_limit=3)
P1 = replace(P0B, id="P1", sidequests=("gald", "riku"), optional_limit=None,
             combat_policy="heuristic", decision_rule="checks")
P2 = replace(P1, id="P2", sidequests=(*P1.sidequests, "cave_full", "fort", "purification"),
             shopping_rule="preparations", passive_mode="table", spring_rest="last_visit_once")
P3 = replace(P2, id="P3", sidequests=(*P2.sidequests, "town_errands", "mina", "battlefield",
                                    "oaksdawn", "gorge", "mansion", "merchant", "robin",
                                    "sarah", "hearth", "nameless_soldiers", "fire_seed"),
             shopping_rule="all_shops")
ARCHETYPES = {a.id: a for a in (P0A, P0B, P1, P2, P3,
                              replace(P2, id="P2s", avoid_battles=True),
                              replace(P0B, id="P0g", grind=True))}


def validate(archetypes: Iterable[Archetype] = ARCHETYPES.values()) -> None:
    seen = set()
    for a in archetypes:
        if a.id in seen or not 0 <= a.recovery_threshold <= 1:
            raise ValueError("duplicate archetype or invalid recovery threshold")
        seen.add(a.id)
        if a.optional_limit is not None and len(a.optional_interactions) > a.optional_limit:
            raise ValueError("optional interaction budget exceeded")
        if a.companion_rule not in {"none", "fire_bat_dragon"}:
            raise ValueError("unknown companion rule")
        if a.equipment_rule not in {"initial", "equip_acquired"}:
            raise ValueError("unknown equipment rule")
        if a.shopping_rule not in {"none", "hinted_one", "preparations", "all_shops"}:
            raise ValueError("unknown shopping rule")
        if a.combat_policy not in {"attack_only", "greedy", "heuristic", "best_free", "heuristic_v3"} or not set(a.sidequests) <= SIDEQUESTS:
            raise ValueError("unknown combat policy or side quest")
        if a.rest_rule not in {"free_hp70", "none"} or a.passive_mode not in {"first", "table", "enumerate"}:
            raise ValueError("unknown extension policy")
        if a.spring_rest not in {"first_hp70", "last_visit_once", "never"}:
            raise ValueError("unknown spring rest policy")
        if a.decision_rule not in {"backbone", "checks", "avoid"}:
            raise ValueError("unknown decision rule")


class LevelModel(Protocol):
    """Observe engine growth without awarding EXP or changing levels."""

    def observe(self, session: dict[str, Any], node: str) -> int: ...


class MilestoneLevelModel:
    name = "engine_milestones"

    def observe(self, session: dict[str, Any], node: str) -> int:
        return int(session["character"].get("level", 1))


class ExpLevelModel(MilestoneLevelModel):
    name = "engine_exp_observer"

    def snapshot(self, session: dict[str, Any]) -> dict[str, Any]:
        from collections import Counter
        sources = Counter({k: 0 for k in ("trash", "elite", "boss", "unclassified", "quest")})
        for event in session.get("event_log", []):
            if event.get("kind") == "exp_gained":
                entry = event["data"]
                source = entry["source"].split(":", 1)[0]
                sources[source if source in sources else "unclassified"] += entry["amount"]
        return {"level": self.observe(session, ""), "exp": session["character"].get("exp", 0),
                "sources": dict(session.get("_balance_exp_sources", sources)),
                "quest_ids": list(session["character"].get("exp_rewarded_quests", []))}


def default_passive_choices(character: str) -> dict[str, str]:
    data = json.loads(DEFAULT_PASSIVES.read_text(encoding="utf-8"))
    return dict(data["characters"][character]["choices"])


class PassivePicker:
    """Permanent choices, always applied to the copy returned by the engine."""

    def __init__(self, mode: str = "first", table: Optional[dict[str, str]] = None):
        if mode not in {"first", "table", "enumerate"}:
            raise ValueError("unknown passive mode")
        self.mode = mode
        self.table = table or {}
        self.use_defaults = mode == "table" and table is None
        self.defaults: dict[str, dict[str, str]] = {}

    def pick(self, options: Iterable[str], scores: Optional[dict[str, float]] = None) -> list[str]:
        options = list(options)
        if not options:
            return []
        if self.mode == "enumerate":
            return options
        return options[:1]

    def apply(self, session: dict[str, Any]) -> dict[str, Any]:
        from host import progression
        if not progression.enabled(session):
            return session
        if session.get("combat"):
            raise ValueError("Passive choices require noncombat state")
        table = self.table
        if self.use_defaults and session.get("pending_passive_choices"):
            character = session["character"]["character_id"]
            if character not in self.defaults:
                self.defaults[character] = default_passive_choices(character)
            table = self.defaults[character]
        while session.get("pending_passive_choices"):
            level = min(session["pending_passive_choices"])
            group = progression.public_progression(session)["pending"][0]
            options = [entry["id"] for entry in group["options"]]
            identifier = options[0] if self.mode == "first" else table.get(str(level), options[0])
            session = progression.choose_passive(session, level, identifier)
        return session

    def combinations(self, groups: Iterable[Iterable[str]]) -> list[list[str]]:
        groups = [list(group) for group in groups]
        return [list(choices) for choices in product(*groups)] if groups else [[]]


validate()
