from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from itertools import product
from typing import Any, Iterable, Optional, Protocol

CHARACTERS = ("hero", "cleric", "mage", "thief")
COMPLETION_TITLE = "冒険完了"
IGNIS_FLAGS = ("defeated_ignis", "ignis_purified")
TERMINAL_LOCATION = "draco_battle"
MAINLINE_NODES = ("castle", "dark_forest_loc", "elf_spring", "forest_exit",
                  "village_frozen_clue", "ian_ice_katana_aftermath", "valley_entrance",
                  "dragon_valley_loc", "royal_gate", "draco_battle")


@dataclass(frozen=True)
class Archetype:
    id: str
    optional_interactions: tuple[str, ...]
    companion_rule: str
    equipment_rule: str
    shopping_rule: str
    sidequests: tuple[str, ...]
    combat_policy: str
    rest_rule: str = "spring_three"
    recovery_threshold: float = .30
    optional_limit: Optional[int] = None
    avoid_battles: bool = False
    grind: bool = False
    passive_mode: str = "first"
    status: str = "proposed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


P0A = Archetype("P0a", (), "none", "initial", "none", (), "best_free", optional_limit=0)
P0B = Archetype("P0b", ("ask_king_info", "shop:sarah_shop:ice_charm", "borrow_fire_bat_dragon"),
               "fire_bat_dragon", "equip_acquired", "hinted_one", (), "best_free", optional_limit=3)
P1 = replace(P0B, id="P1", sidequests=("gald", "riku"), optional_limit=None,
             combat_policy="heuristic")
P2 = replace(P1, id="P2", sidequests=(*P1.sidequests, "cave_full", "fort", "purification"),
             shopping_rule="preparations", passive_mode="battle_best")
P3 = replace(P2, id="P3", sidequests=(*P2.sidequests, "town_errands", "mina", "battlefield",
                                    "oaksdawn", "gorge", "mansion", "merchant"),
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
        if a.rest_rule not in {"spring_three", "none"} or a.passive_mode not in {"first", "battle_best", "enumerate"}:
            raise ValueError("unknown extension policy")


class LevelModel(Protocol):
    """Observe engine growth; a future EXP implementation may settle awards here."""

    def observe(self, session: dict[str, Any], node: str) -> int: ...


class MilestoneLevelModel:
    name = "engine_milestones"

    def observe(self, session: dict[str, Any], node: str) -> int:
        return int(session["character"].get("level", 1))


class PassivePicker:
    """No passive choices exist yet. Scores are supplied by a future evaluator."""

    def __init__(self, mode: str = "first"):
        if mode not in {"first", "battle_best", "enumerate"}:
            raise ValueError("unknown passive mode")
        self.mode = mode

    def pick(self, options: Iterable[str], scores: Optional[dict[str, float]] = None) -> list[str]:
        options = list(options)
        if not options:
            return []
        if self.mode == "enumerate":
            return options
        if self.mode == "battle_best" and scores is not None:
            return [max(options, key=lambda option: scores.get(option, float("-inf")))]
        return options[:1]

    def combinations(self, groups: Iterable[Iterable[str]]) -> list[list[str]]:
        groups = [list(group) for group in groups]
        return [list(choices) for choices in product(*groups)] if groups else [[]]


validate()
