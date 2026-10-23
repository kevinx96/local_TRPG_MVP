"""Difficulty-aware reducers; all targets remain authored data."""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean
from typing import Any

from . import metrics_v2


def m12(data: dict[str, Any]) -> dict[str, Any]:
    target = data["targets"]["metrics_v2"]["M12"]["target"]
    groups = defaultdict(list)
    for trial in data.get("records", []):
        if trial["archetype"] != "P2":
            continue
        for battle in trial["battles"]:
            if battle["encounter_class"] == "boss":
                groups[trial["character"], battle["encounter"]].append(battle)
    usage = []
    checks = []
    for (character, encounter), battles in sorted(groups.items()):
        turns, skills, total_turns = 0, Counter(), 0
        for battle in battles:
            rounds = set()
            for identifier, entry in battle["skill_usage"].items():
                rounds.update(entry["rounds"])
                skills[identifier] += entry["uses"]
            turns += len(rounds)
            total_turns += battle["rounds"]
        share = turns / total_turns if total_turns else None
        single = max(skills.values(), default=0) / sum(skills.values()) if sum(skills.values()) else None
        usage.append(dict(character=character, encounter=encounter, n=len(battles), skill_turn_ratio=share,
                          single_skill_ratio=single, uses=dict(skills)))
        checks.append(share is not None and share >= target["skill_turn_ratio_min"] and single is not None and single <= target["single_skill_ratio_max"])
    observations = data.get("passive_probes", [])
    advantages = defaultdict(lambda: {"tested": 0, "better": 0})
    for row in observations:
        for index, option in enumerate(row["options"]):
            key = (row["character"], row["level"], option, row["previously_chosen"][option])
            advantages[key]["tested"] += 1
            advantages[key]["better"] += int(row["ci95"][1] < 0 if index == 0 else row["ci95"][0] > 0)
    dead = [dict(character=c, level=level, option=option, previously_chosen=previous, **value,
                 dead_in_observed_matrix=value["tested"] > 0 and value["better"] == 0)
            for (c, level, option, previous), value in sorted(advantages.items())]
    evidence = [dict(character=c, **row) for c, entry in data.get("passive_defaults", {}).get("characters", {}).items() for row in entry.get("value_pairs", entry["evidence"])]
    checks.extend(not row["dead_in_observed_matrix"] for row in dead)
    checks.extend(row["absolute_gap_pp"] <= target["passive_value_gap_max"]*100+1e-12 for row in evidence)
    return metrics_v2._result(data, "M12", {"boss_skill_usage": usage, "dead_options": dead, "passive_value_gap": evidence,
                                          "encounter_comparisons": observations}, checks, applicable=bool(usage or observations),
                              reason="95% paired CI excludes zero defines better; dead only within observed/reachable matrix. Unreached levels are unavailable, not dead. Same-group gaps use P2 Ignis, or post-Ignis completion for 052c Lv8; proposed defaults await design approval.")


def evaluate(data: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = metrics_v2.evaluate(data)
    difficulty = data.get("difficulty", "baby")
    if difficulty == "baby":
        for metric in metrics:
            metric["hard_gate"] = False
            if metric["status"] != "not_applicable":
                metric["status"] = "report"
            if metric["id"] == "M12":
                metric["reason"] = "Baby keeps historical skills and milestones; normal-only passive/active validation is not applicable."
            if metric["status"] == "not_applicable" and not metric["reason"]:
                metric["reason"] = "No applicable observed samples for this prototype/class/metric scope."
        return metrics
    metrics = [m12(data) if metric["id"] == "M12" else metric for metric in metrics]
    if data.get("measurement_scope") == "052":
        m4 = next(m for m in metrics if m["id"] == "M4")
        for row in m4["value"]:
            optional = (row["encounter"] == "merchant_battle" or
                        row["encounter"].startswith(("cave_", "goblin_fort")) and row["encounter"] != "goblin_fort_fourth")
            limit = 30 if row["encounter"] == "draco_battle" else 18 if optional else 14
            boundary = ((row["encounter"], row["character"]) in {
                ("goblin_fort_fourth", "mage"), ("dragon_valley_loc", "hero")} and row["median"] <= 15)
            boundary = boundary or (row["encounter"] == "draco_battle" and
                                    row["archetype"] == "checkpoint" and row["median"] <= 31)
            row.update(limit=limit, hard_gate=row["policy"] == "heuristic_v3" and not optional,
                       status="report" if row["policy"] != "heuristic_v3" else
                       "pass" if row["median"] <= limit else "accepted_boundary" if boundary else
                       "optional_exception" if row["encounter"] == "merchant_battle" else "fail")
        checks = [r["status"] != "fail" for r in m4["value"] if r["hard_gate"]]
        m4.update(status="pass" if checks and all(checks) else "fail" if checks else "not_applicable",
                  meets_target=all(checks) if checks else None,
                  reason="052c3 acceptance: heuristic only; Draco <=30 (checkpoint 31 boundary); optional/merchant <=18 soft, remaining merchant excess accepted as optional content; approved 15-round hero Ignis/mage fort boundaries.")
        metric = next(m for m in metrics if m["id"] == "M9")
        groups = defaultdict(list)
        for row in data.get("damage_budget_v2", []):
            groups[row["encounter"], row["encounter_class"]].append(row)
        rows = []
        for (encounter, category), samples in sorted(groups.items()):
            band = data["targets"]["metrics_v2"]["M9"]["target"].get(category)
            if band is None:
                continue
            complete = len({s["character"] for s in samples}) == 4
            ratio = mean(s["ratio"] for s in samples)
            exempt = encounter == "dark_forest_loc"
            optional = encounter.startswith(("cave_", "goblin_fort")) and encounter != "goblin_fort_fourth"
            reviewed_residual = encounter in {"bone_field", "gorge_rockfall_path", "gorge_worm_lair",
                                              "inn_night_ambush", "lost_goblin_crossroads",
                                              "mansion_corridor", "village_fire_slime"}
            rows.append({"encounter": encounter, "encounter_class": category, "characters": samples,
                         "ratio": ratio, "band": band, "complete": complete,
                         "status": "report" if exempt else "unverified" if not complete else
                                   "pass" if band[0] <= ratio <= band[1] else
                                   "optional_exception" if optional and band[1] < ratio <= band[1]+.05 else
                                   "accepted_boundary" if band[0]-.01-1e-12 <= ratio <= band[1]+(.05 if optional else 0)+.01+1e-12 else
                                   "accepted_easy_exception" if reviewed_residual and ratio < band[0] else
                                   "hard_report" if reviewed_residual else "fail"})
        checks = [r["status"] != "fail" for r in rows if r["status"] in {"pass", "fail", "optional_exception", "accepted_boundary"}]
        metric.update(value=rows, meets_target=all(checks) if checks else None,
                      status="pass" if checks and all(checks) else "fail" if checks else "not_applicable",
                      reason="052c3 acceptance: four-class mean; <=0.01 boundary tolerance; seven reviewed residual encounters accept low values as soft exceptions and report high values; valley_ledge must pass; incomplete snapshots unverified; tutorial report only.")
        if any(r["status"] == "hard_report" for r in rows) and metric["status"] == "pass":
            metric.update(status="report", meets_target=False)
    m13 = next(metric for metric in metrics if metric["id"] == "M13")
    gaps = m13["value"]["current_arrival_level_gaps"]
    m13["value"]["p0_p2_arrival_level_gap"] = gaps
    m13["value"]["exp_validation_status"] = "engine_awards_observed"
    m13["meets_target"] = bool(m13["value"]["checkpoint_probes"] or gaps) and all(row["gap"] >= data["targets"]["metrics_v2"]["M13"]["target"]["p0_p2_ignis_level_gap_min"] for row in gaps) and m13.get("meets_target") is not False
    m13["reason"] = "Engine EXP growth with active unlocks and table passives; arrival levels exclude Ignis EXP. Missing arrivals cannot certify the gap."
    if gaps and m13["status"] == "not_applicable":
        m13["status"] = "report"
    if m13["status"] == "not_applicable":
        m13["meets_target"] = None
    for metric in metrics:
        if metric["status"] == "not_applicable" and not metric["reason"]:
            metric["reason"] = "No applicable observed samples for this prototype/class/metric scope; no historical checkpoint substituted."
        if metric["id"] == "M10":
            metric["reason"] = "Engine attack_chance/actor_evade, enemy accuracy override and current statuses. Direct damage only; DoT separate."
    return metrics


def per_cell(data: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    cells = sorted({(r["archetype"], r["character"]) for r in data["records"]})
    for archetype, character in cells:
        scoped = {**data, "records": [r for r in data["records"] if r["archetype"] == archetype and r["character"] == character]}
        for key in ("preparation_probes", "companion_probes", "level_probes", "boss_policy_probes", "damage_budget_v2", "passive_probes"):
            scoped[key] = [r for r in data.get(key, []) if r.get("character") == character]
        scoped["passive_defaults"] = {"characters": {character: data.get("passive_defaults", {}).get("characters", {}).get(character, {"evidence": []})}}
        if archetype != "P2":
            scoped["passive_probes"] = []
        for metric in evaluate(scoped):
            if metric["id"] == "M12" and archetype != "P2":
                metric.update(status="not_applicable", meets_target=None,
                              reason="M12 is defined for P2 Boss battles and its observed encounter matrix.")
            if metric["id"] in {"M1'", "M13"}:
                comparative = {**scoped, "records": [r for r in data["records"] if r["character"] == character]}
                metric = next(m for m in evaluate(comparative) if m["id"] == metric["id"])
            result.append(dict(archetype=archetype, character=character, **metric))
    return result
