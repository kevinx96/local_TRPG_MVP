"""Paired normal probes starting only from observed P2/P0b openings."""
from __future__ import annotations

import json
import math
import random
from copy import deepcopy
from itertools import product
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any
from unittest.mock import patch

from host import combat, progression, state
from host.difficulty import apply_difficulty
from . import budget, checkpoints, probes_v2, route_v2, sim, snapshots_v3
from .archetypes import ARCHETYPES, CHARACTERS, PassivePicker, default_passive_choices
from .legacy_spring import select_spring

SEED_RULE = "sha256(f'{seed}:{key}:{character}:{trial_index}')[:8] big-endian; variants omit passive/companion/level/preparation; route key=route_v2"


def combinations(pack: dict[str, Any], character: str) -> list[dict[str, str]]:
    groups = next(c for c in pack["class_progression"] if c["id"] == character)["passive_groups"]
    return [dict(zip((str(g["level"]) for g in groups), values)) for values in product(*(g["options"] for g in groups))]


def choose_defaults(pack: dict[str, Any], rows: list[dict[str, Any]], *, postgame: bool = False) -> dict[str, Any]:
    result = {"status": "proposed", "seed_rule": SEED_RULE, "characters": {}}
    if postgame:
        result.update(version=2, source="052c: re-enumerated after 054 and normal tuning")
    for character in CHARACTERS:
        definition = next(c for c in pack["class_progression"] if c["id"] == character)
        table = {str(g["level"]): g["options"][0] for g in definition["passive_groups"]}
        evidence = []
        for group in definition["passive_groups"]:
            rates = []
            for option in group["options"]:
                candidate = {**table, str(group["level"]): option}
                row = next(r for r in rows if r["character"] == character and r["choices"] == candidate)
                terminal = postgame and group["level"] == 8
                rates.append({"option": option, "wins": sum(row["completed_outcomes"]) if terminal else row["ignis_wins"],
                              "n": row["n"], "rate": row["completion_rate"] if terminal else row["ignis_rate"],
                              "endpoint": "completion" if terminal else "ignis",
                              "reached_level": row["reached_levels"].get(str(group["level"]), 0)})
            selected = max(range(len(rates)), key=lambda i: rates[i]["rate"])
            table[str(group["level"])] = group["options"][selected]
            evidence.append({"level": group["level"], "selected": table[str(group["level"])], "comparisons": rates,
                             "absolute_gap_pp": abs(rates[0]["rate"]-rates[1]["rate"])*100,
                             "rule": "previous choices fixed; later choices A; tie A; " +
                             ("P2 Ignis for Lv2/4/6, post-Ignis completion for Lv8" if postgame else "P2 Ignis")})
        value_pairs = []
        for group in definition["passive_groups"]:
            alternatives = [next(r for r in rows if r["character"] == character and r["choices"] == {**table, str(group["level"]): option}) for option in group["options"]]
            outcome_key = "completed_outcomes" if postgame and group["level"] == 8 else "outcomes"
            comparison = paired(*[[{"won": won} for won in row[outcome_key]] for row in alternatives])
            value_pairs.append({"level": group["level"], "options": group["options"], "n": alternatives[0]["n"],
                                "other_choices": {key: value for key, value in table.items() if key != str(group["level"])},
                                "absolute_gap_pp": abs(comparison["b_minus_a"])*100, **comparison})
        result["characters"][character] = {"choices": table, "evidence": evidence, "value_pairs": value_pairs}
    return result


def enumerate_job(job: tuple) -> list[dict[str, Any]]:
    _, path, character, n, seed, options = job
    pack = select_spring(apply_difficulty(state.load_scenario_pack(Path(path)), "normal"), options.get("spring", "current"))
    rows = []
    for choices in ([options["choices"]] if "choices" in options else combinations(pack, character)):
        wins, completed, reached = [], [], {str(level): 0 for level in (2, 4, 6, 8)}
        for index in range(n):
            record = route_v2.trial(pack, character, sim.trial_seed(seed, "route_v2", character, index), ARCHETYPES["P2"],
                                    difficulty="normal", spring=options.get("spring", "current"), passive_table=choices, effective=True, measure=False)
            wins.append(int(record["ignis_defeated"]))
            completed.append(int(record["completed"]))
            maximum = max(max(record["levels"].values()), record.get("final", {}).get("level", 1))
            for level in reached:
                reached[level] += maximum >= int(level)
        rows.append({"character": character, "choices": choices, "n": n, "ignis_wins": sum(wins), "ignis_rate": mean(wins),
                     "completion_rate": mean(completed), "outcomes": wins, "completed_outcomes": completed, "reached_levels": reached})
    return rows


def export_checkpoints(records: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    result = {"version": 3, "difficulty": "normal", "status": "observed", "source": "P2 and P0b median-level opening samples; no victory assumptions", **metadata,
              "profiles": {"P2": {"encounters": {}}, "P0b": {"encounters": {}}}}
    for record in records:
        profile = record["archetype"]
        if profile not in result["profiles"]:
            continue
        for encounter, entry in record.get("checkpoint_candidates", {}).items():
            point = result["profiles"][profile]["encounters"].setdefault(encounter, {"characters": {}})
            point["characters"][record["character"]] = entry
    result["encounters"] = result["profiles"]["P2"]["encounters"]
    return result


def with_passives(session: dict[str, Any], table: dict[str, str]) -> dict[str, Any]:
    candidate = probes_v2.class_clone(session)
    actor = candidate["character"]
    actor["passives"], actor["passive_history"] = [], {}
    candidate["pending_passive_choices"] = [g["level"] for g in progression.definition(candidate)["passive_groups"] if g["level"] <= actor["level"]]
    return PassivePicker("table", table).apply(candidate)


def battles(template: dict[str, Any], n: int, seed: int, key: str, policy: str = "heuristic_v3", purify: bool = True):
    result = []
    for index in range(n):
        session = probes_v2.class_clone(template)
        rng = random.Random(sim.trial_seed(seed, key, template["character"]["character_id"], index))
        with patch.object(combat, "random", rng), patch.object(state, "random", rng):
            session["combat_start_requested"] = True
            session["_balance_free_actions"] = {}
            if not combat.ensure_combat_started(session):
                raise ValueError("Probe encounter did not start")
            while combat.combat_is_active(session):
                action, target = sim.choose_action(session, policy, purify=purify, reserve_purification=purify)
                sim.perform_action(session, action, target, rng)
        result.append({"won": int(session["combat"]["status"] in {"victory", "purified"}), "rounds": session["combat"]["round"]})
    return result


def paired(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> dict[str, Any]:
    values = [right["won"]-left["won"] for left, right in zip(a, b)]
    point = mean(values)
    width = 1.96*stdev(values)/math.sqrt(len(values)) if len(values) > 1 else 2
    return {"a": mean(r["won"] for r in a), "b": mean(r["won"] for r in b), "b_minus_a": point,
            "ci95": [max(-1, point-width), min(1, point+width)], "paired_discordant": sum(v != 0 for v in values),
            "ci_method": "paired difference normal approximation; n=1 uninformative"}


def run_job(job: tuple) -> list[dict[str, Any]]:
    kind, path, character, n, seed, options = job
    if kind == "enumerate_probes":
        return enumerate_job(job)
    base = state.load_scenario_pack(Path(path))
    pack = select_spring(apply_difficulty(base, options.get("difficulty", "normal")), options.get("spring", "current"))
    cp = json.loads(Path(options["checkpoint_path"]).read_text(encoding="utf-8"))
    table = options.get("passive_table")
    if table is None:
        table = default_passive_choices(character)
    rows = []
    preparations = json.loads(probes_v2.PREPARATIONS.read_text(encoding="utf-8"))["encounters"]["dragon_valley_loc"]["items"]
    if options.get("difficulty") == "normal":
        preparations.append({"id": "burn_salve", "item_ids": ["burn_salve"],
                             "critical": False, "remove": {"kind": "equipment"}})
    locations = {l["id"]: l for l in pack["locations"]}
    for encounter, point in cp["encounters"].items():
        if options.get("encounter") and options["encounter"] != encounter:
            continue
        entry = point["characters"].get(character)
        if not entry:
            continue
        category = locations[encounter].get("combat", {}).get("encounter_class")
        template = snapshots_v3.restore(pack, entry["snapshot"])
        if kind == "normal_preparation_probes" and encounter == "dragon_valley_loc":
            baseline = battles(template, n, seed, encounter)
            for preparation in preparations:
                candidate = probes_v2.class_clone(template)
                probes_v2.remove_preparation(candidate, preparation)
                results = battles(candidate, n, seed, encounter)
                full, without = mean(r["won"] for r in baseline), mean(r["won"] for r in results)
                rows.append(dict(character=character, encounter=encounter, preparation=preparation["id"], critical=preparation["critical"],
                                 n=n, full=full, without=without, uplift=full-without, status="proposed", source="P2 observed"))
                if preparation["id"] == "burn_salve":
                    quantity = sum(i.get("quantity", 1) for i in template["character"]["inventory"]
                                   if i.get("id") == "burn_salve")
                    rows[-1].update(observed_quantity=quantity,
                                    evidence="paired_removal" if quantity else "absent_in_snapshot")
        elif kind == "normal_companion_probes" and category == "boss":
            template["companion"] = None
            template["flags"].pop("fire_bat_empowered", None)
            baseline = battles(template, n, seed, encounter)
            for companion in pack.get("companions", []) + [{**next(c for c in pack["companions"] if c["id"] == "fire_bat_dragon"), "empowered": True}]:
                candidate = probes_v2.class_clone(template)
                candidate["companion"] = deepcopy(companion)
                if companion.get("empowered"):
                    candidate["flags"]["fire_bat_empowered"] = True
                result = battles(candidate, n, seed, encounter)
                pair = paired(baseline, result)
                rows.append(dict(character=character, encounter=encounter, companion=companion["id"] + (":empowered" if companion.get("empowered") else ""),
                                 n=n, without=pair["a"], with_companion=pair["b"], uplift=pair["b_minus_a"], ci95=pair["ci95"]))
        elif kind == "normal_level_probes" and category == "boss":
            level = template["character"]["level"]
            results = {value: battles(snapshots_v3.at_level(template, value, table), n, seed, encounter) for value in (level-1, level, level+1) if 1 <= value <= pack["progression"]["max_level"]}
            for value in results:
                if value+1 in results:
                    pair = paired(results[value], results[value+1])
                    rows.append(dict(character=character, encounter=encounter, n=n, from_level=value, to_level=value+1,
                                     before=pair["a"], after=pair["b"], uplift=pair["b_minus_a"], ci95=pair["ci95"], scope="engine EXP growth, fixed inventory, table passives, fixed active unlocks"))
        elif kind == "normal_boss_policy_probes" and category == "boss":
            for policy in ("attack_only", "best_free", "heuristic_v3"):
                result = battles(template, n, seed, encounter, policy=policy)
                rows.append(dict(character=character, encounter=encounter, policy=policy, win_rate=mean(r["won"] for r in result), rounds=[r["rounds"] for r in result]))
        elif kind == "normal_passive_probes" and category in {"elite", "boss"}:
            groups = progression.definition(template)["passive_groups"]
            reached = [g for g in groups if g["level"] <= template["character"]["level"]]
            outcomes_by_choices = {}
            for index, group in enumerate(groups):
                if group["level"] > template["character"]["level"]:
                    continue
                if (options.get("postgame_passives") and group["level"] == 8
                        and not any(template["flags"].get(flag) for flag in ("defeated_ignis", "ignis_purified"))):
                    continue
                contexts = list(product(*(g["options"] for g in groups[:index])))
                # Every earlier history is needed to distinguish stacked and first picks.
                for context in contexts:
                    prefix = dict(zip((str(g["level"]) for g in groups[:index]), context))
                    outcomes = []
                    for option in group["options"]:
                        choices = {**table, **prefix, str(group["level"]): option}
                        key = tuple(choices.get(str(g["level"]), g["options"][0]) for g in reached)
                        if key not in outcomes_by_choices:
                            outcomes_by_choices[key] = battles(with_passives(template, choices), n, seed, encounter)
                        outcomes.append(outcomes_by_choices[key])
                    rows.append(dict(character=character, encounter=encounter, level=group["level"], n=n, options=group["options"],
                                     previous_choices=prefix, previously_chosen={option: option in context for option in group["options"]},
                                     **paired(*outcomes)))
    return rows
