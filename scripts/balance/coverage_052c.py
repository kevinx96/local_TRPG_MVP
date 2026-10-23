"""Supplemental P2-policy routes; all checks and fights use ordinary engine results."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from .archetypes import ARCHETYPES, CHARACTERS

VARIANTS = ("fort_alternatives", "lost_goblin", "ledge", "merchant", "optional_areas",
            "fire_seed", "postgame_inn")


def archetype(variant: str):
    if variant not in VARIANTS:
        raise ValueError(variant)
    base = ARCHETYPES["P2"]
    if variant == "merchant":
        return replace(base, sidequests=(*base.sidequests, "merchant", "robin"))
    if variant == "fire_seed":
        return replace(base, sidequests=(*base.sidequests, "fire_seed"))
    if variant == "postgame_inn":
        return replace(base, sidequests=(*base.sidequests, "mansion"))
    if variant == "optional_areas":
        return replace(base, sidequests=(*base.sidequests, "battlefield", "oaksdawn", "gorge",
                                        "mansion", "merchant", "fire_seed", "robin"))
    return base


def supplement(args, settings, defaults, run_stage, cp: dict[str, Any]) -> dict[str, Any]:
    from host import state
    from host.difficulty import apply_difficulty
    from . import probes_v3
    jobs = [(args.scenario, "P2", character, args.n, args.seed,
             {**settings, "passive_table": defaults["characters"][character]["choices"],
              "coverage_variant": variant, "branches": {"coverage_variant": variant,
                  "merchant": "pay" if variant == "optional_areas" else "betray"}})
            for variant in VARIANTS for character in CHARACTERS]
    records = run_stage("coverage_routes", jobs)
    additions = []
    for variant in VARIANTS:
        candidates = probes_v3.export_checkpoints(
            [r for r in records if r.get("coverage_variant") == variant], {})
        for encounter, point in candidates["encounters"].items():
            existing = cp["encounters"].setdefault(encounter, {"characters": {}})["characters"]
            for character, entry in point["characters"].items():
                if character in existing:
                    continue
                existing[character] = {**entry, "source": "supplemental_P2_policy_route",
                                       "coverage_variant": variant}
                additions.append({"encounter": encounter, "character": character, "variant": variant,
                                  "level": entry["snapshot"]["character"]["level"],
                                  "arrival_count": entry["arrival_count"]})
    pack = apply_difficulty(state.load_scenario_pack(args.scenario), "normal")
    missing = [{"encounter": location["id"], "character": character, "status": "unverified"}
               for location in pack["locations"]
               if location.get("combat", {}).get("encounter_class") in {"trash", "elite", "boss"}
               for character in CHARACTERS
               if character not in cp["encounters"].get(location["id"], {}).get("characters", {})]
    return {"added": additions, "unverified": missing, "definition": "Actual median-level openings on independent optional P2-policy branches; primary route samples take precedence; no forced victories or level substitution."}
