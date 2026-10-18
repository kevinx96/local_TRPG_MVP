"""Chapter-three route coverage and pairwise playthrough metrics."""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from statistics import mean
from typing import Any


ROUTES = ("village", "battlefield", "gorge")
ROUTE_LOCATIONS = {"village_approach": "village", "bone_field": "battlefield", "gorge_entrance": "gorge"}


def clue_flags(pack: dict[str, Any]) -> list[str]:
    report = next(loc for loc in pack["locations"] if loc["id"] == "castle_report")
    action = next(a for a in report["actions"] if a["id"] == "report_with_evidence")
    found = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if "flags_count_gte" in value:
                found.update(value["flags_count_gte"]["flags"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(action["requirements"])
    for quest in pack.get("quests", []):
        found.update(quest.get("clue_flags", []))
    return sorted(found)


def pure_movement(action: dict[str, Any]) -> bool:
    if any(action.get(k) for k in ("roll", "once", "success_effects", "failure_effects", "critical_success_effects", "open_shop")):
        return False
    effects = action.get("effects", [])
    allowed = {"current_location", "current_scene", "background_image"}
    if not isinstance(effects, list):
        return False
    return any("current_location" in e or "current_scene" in e for e in effects) and all(
        all(k in allowed or (k == "flags_set" and not v) for k, v in e.items()) for e in effects)


def jaccard(left: set, right: set) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def summarize(results: list[dict[str, Any]], pack: dict[str, Any]) -> dict[str, Any]:
    completed = [r for r in results if r["completed"]]
    pairs = []
    for left, right in combinations(completed, 2):
        choices = [{(c["location"], c["action_id"]) for c in r["scenario_choices"] if not c["pure_movement"]} for r in (left, right)]
        pairs.append(dict(left=f"{left['character']}/{left['seed']}", right=f"{right['character']}/{right['seed']}",
            choices=jaccard(*choices), locations=jaccard(set(left["visited_locations"]), set(right["visited_locations"]))))

    def stats(key: str) -> dict[str, Any]:
        values = [p[key] for p in pairs]
        return dict(pairs=len(values), mean=mean(values) if values else None,
                    min=min(values) if values else None, max=max(values) if values else None)

    visited = {loc for r in results for loc in r["visited_locations"]}
    return dict(runs=len(results), completed=len(completed),
        endings=dict(Counter(r["ending"] for r in results)),
        first_deaths=dict(Counter(r["first_death"]["location"] for r in results if r["first_death"])),
        retries=dict(Counter(str(r["retry_count"]) for r in results)),
        route_counts={path: sum(path in r["chapter3_routes"] for r in results) for path in ROUTES},
        route_counts_by_character={character: {
            path: sum(path in r["chapter3_routes"] for r in results if r["character"] == character) for path in ROUTES}
            for character in dict.fromkeys(r["character"] for r in results)},
        clue_counts={flag: sum(flag in r["clue_flags"] for r in results) for flag in clue_flags(pack)},
        final_clue_counts={flag: sum(flag in r["final_clue_flags"] for r in results) for flag in clue_flags(pack)},
        never_visited=[dict(id=loc["id"], title=loc["title"]) for loc in pack["locations"] if loc["id"] not in visited],
        overlap=dict(choices=stats("choices"), locations=stats("locations"), pairwise=pairs),
        invariants={kind: sum(r["invariants"][kind] for r in results) for kind in ("exceptions", "noncombat_dead_ends", "fallback_narrations")})
