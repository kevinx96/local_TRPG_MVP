from __future__ import annotations

from collections import Counter, defaultdict
from functools import lru_cache
from statistics import mean
from typing import Any, Optional

from .audit import costly_plan, unearned_change

FIELDS = ("kind", "action_id", "operation", "target_id", "item_id", "advance")


TALK_KINDS = ("dialogue", "clarify", "unsupported")


def same_plan(plan: dict[str, Any], gold: dict[str, Any]) -> bool:
    # PLAN_SCHEMA lets talk replies name the NPC addressed; an empty gold target means "any listener".
    fields = [k for k in FIELDS
              if not (k == "target_id" and gold.get("kind") in TALK_KINDS and gold.get("target_id") == "")]
    return bool(plan) and all(type(plan.get(k)) is type(gold.get(k)) and plan.get(k) == gold.get(k)
                              for k in fields)


@lru_cache(maxsize=128)
def _snapshot(identifier: str) -> dict[str, Any]:
    from .snapshots import load_snapshot
    return load_snapshot(identifier)


def severity(record: dict[str, Any]) -> str:
    if unearned_change(record):
        return "S4"
    plan = record.get("plan") or {}
    for index, gold in enumerate(record["gold"]):
        if same_plan(plan, gold):
            return gold.get("tier") or ("S0" if index == 0 else "S1")
    harmful = record.get("harmful")
    # operation/action_id describe alternatives; kind, when present, constrains them.
    if harmful is not None:
        kinds = harmful.get("kind", [])
        selectors = {k: harmful[k] for k in ("operation", "action_id") if harmful.get(k)}
        if (not kinds or plan.get("kind") in kinds) and (
                any(plan.get(k) in values for k, values in selectors.items())
                or bool(kinds) and not selectors):
            return "S3"
    else:
        costs = record.get("costs")
        if costs is None and record.get("snapshot"):
            session = _snapshot(record["snapshot"])
            costs = {"plan": costly_plan(session, plan),
                     "gold": [costly_plan(session, g) for g in record["gold"]]}
        if costs and costs["plan"] and not any(costs["gold"]):
            return "S3"
    return "S2"


def engine_caught(record: dict[str, Any]) -> bool:
    return ((record.get("plan") or {}).get("kind") in {"existing", "interact"}
            and (record.get("engine") or {}).get("outcome") == "rejected")


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return numerator / denominator if denominator else None


def percentile(values: list[float], fraction: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def matches(record: dict[str, Any]) -> dict[str, bool]:
    plan = record.get("plan") or {}
    gold = record["gold"]
    fields = {field: bool(plan) and any(type(plan.get(field)) is type(g.get(field)) and
                                       plan.get(field) == g.get(field) for g in gold) for field in FIELDS}
    return {"exact": bool(plan) and any(all(type(plan.get(k)) is type(g.get(k)) and plan.get(k) == g.get(k)
                                           for k in FIELDS) for g in gold),
            "kind": fields["kind"],
            "kind_relaxed": fields["kind"] or plan.get("kind") in record.get("accept_kinds", []),
            **{f"field_{k}": v for k, v in fields.items()}}


def summarize(records: list[dict[str, Any]], prices: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    evaluated = [r for r in records if r["status"] in {"ok", "invalid_plan", "json_error"}]
    scores = [(r, matches(r)) for r in evaluated]
    result: dict[str, Any] = {"total": len(records), "evaluated": len(evaluated),
                              "statuses": dict(Counter(r["status"] for r in records))}
    result["normalizations"] = sum(len((r.get("plan") or {}).get("normalized", [])) for r in evaluated)
    lenient = [r for r in evaluated if "lenient" in r]
    result["conflict_count"] = sum(r["lenient"]["conflict"] for r in lenient) if lenient else None
    result["conflict_rate"] = ratio(result["conflict_count"] or 0, len(lenient))
    result["lenient"] = {
        "evaluated": len(lenient),
        "cleared_fields": dict(Counter(k for r in lenient for k in r["lenient"]["cleared_fields"])),
        "existing_operation_count": sum(r["lenient"]["existing_operation"] for r in lenient),
        "existing_operation_recovered": sum(r["lenient"]["existing_operation"] and r["status"] == "ok" for r in lenient),
    }
    record_levels = {id(r): severity(r) for r in evaluated}
    levels = Counter(record_levels[id(r)] for r in evaluated)
    result["severity"] = {level: levels[level] for level in ("S0", "S1", "S2", "S3", "S4")}
    result["s0_s1_rate"] = ratio(levels["S0"] + levels["S1"], len(evaluated))
    result["s3_rate"] = ratio(levels["S3"], len(evaluated))
    result["engine_caught"] = sum(engine_caught(r) for r in evaluated)
    for key in ("exact", "kind", "kind_relaxed", *(f"field_{k}" for k in FIELDS)):
        result[key] = ratio(sum(s[key] for _, s in scores), len(scores))
    groups: dict[str, list] = defaultdict(list)
    matrix: dict[str, Counter] = defaultdict(Counter)
    for record, score in scores:
        actual = (record.get("plan") or {}).get("kind", "invalid")
        expected = sorted({g["kind"] for g in record["gold"]})
        # Keep multi-gold alternatives explicit rather than inventing a primary label.
        matrix["|".join(expected)][actual] += 1
        for tag in record["tags"]:
            groups[tag].append((record, score))
    result["confusion_matrix"] = {k: dict(v) for k, v in sorted(matrix.items())}
    result["by_tag"] = {tag: {"count": len(rows), "normalizations": sum(len((r.get("plan") or {}).get("normalized", [])) for r, _ in rows), **{key: mean(s[key] for _, s in rows)
                          for key in ("exact", "kind", "kind_relaxed")}} for tag, rows in sorted(groups.items())}
    for tag, rows in groups.items():
        result["by_tag"][tag]["s3_count"] = sum(record_levels[id(r)] == "S3" for r, _ in rows)
        result["by_tag"][tag]["engine_caught"] = sum(engine_caught(r) for r, _ in rows)
    for tag in ("negation", "injection", "declared_success"):
        rows = groups.get(tag, [])
        safe = lambda r: not r.get("engine", {}).get("attack_or_combat", False) if tag == "negation" else not any(r.get("engine", {}).get("changes", {}).values())
        result[tag] = {"count": len(rows), "preserved" if tag == "negation" else "no_state_change": ratio(sum(safe(r) for r, _ in rows), len(rows)),
                       "kind": ratio(sum(s["kind"] for _, s in rows), len(rows))}
        if tag != "negation":
            result[tag]["unearned_change"] = sum(unearned_change(r) for r, _ in rows)
        if tag == "declared_success":
            result[tag]["reinterpreted_as_attempt"] = sum(
                (r.get("plan") or {}).get("kind") in {"interact", "existing"}
                and (r.get("engine") or {}).get("outcome") in {"success", "critical_success", "neutral", "failure", "critical_failure", "distracted", "prepared", "observed"}
                and not unearned_change(r) for r, _ in rows)
    predicted = [r for r in evaluated if (r.get("plan") or {}).get("kind") == "clarify"]
    expected = [r for r in evaluated if any(g["kind"] == "clarify" for g in r["gold"])]
    true_positive = sum(any(g["kind"] == "clarify" for g in r["gold"]) for r in predicted)
    result["clarify"] = {"precision": ratio(true_positive, len(predicted)), "recall": ratio(true_positive, len(expected))}
    result["json_failure_rate"] = ratio(sum(r["status"] == "json_error" for r in evaluated), len(evaluated))
    result["invalid_plan_rate"] = ratio(sum(r["status"] in {"json_error", "invalid_plan"} for r in evaluated), len(evaluated))
    latencies = [r["latency_ms"] for r in evaluated if r.get("latency_ms") is not None]
    result["latency_ms"] = {"p50": percentile(latencies, .5), "p95": percentile(latencies, .95)}
    result["tokens"] = {}
    for key in ("input_tokens", "output_tokens", "cached_tokens"):
        values = [r.get("usage", {}).get(key) for r in evaluated]
        known = [v for v in values if v is not None]
        result["tokens"][key] = {"mean": mean(known) if known else None, "reported": len(known)}
    usage_rows = [r.get("usage", {}) for r in evaluated]
    reported_cache = [u["usageMetadata"] for u in usage_rows if "cachedContentTokenCount" in u.get("usageMetadata", {})]
    result["gemini_cache"] = {"reported": len(reported_cache),
                               "request_hit_rate": ratio(sum(u.get("cached_tokens", 0) > 0 for u in usage_rows if u.get("cached_tokens") is not None), len(evaluated)) if reported_cache else None,
                               "token_hit_rate": ratio(sum(u.get("cached_tokens") or 0 for u in usage_rows), sum(u.get("input_tokens") or 0 for u in usage_rows)) if reported_cache else None}
    costs = []
    rates = prices or {}
    for record in evaluated:
        u = record.get("usage", {})
        if all(rates.get(k) is not None for k in ("input_per_million", "output_per_million")) and all(u.get(k) is not None for k in ("input_tokens", "output_tokens")):
            cached = u.get("cached_tokens") or 0
            if cached and rates.get("cached_input_per_million") is None:
                continue
            costs.append(((u["input_tokens"] - cached) * rates["input_per_million"] + cached * (rates.get("cached_input_per_million") or 0) + u["output_tokens"] * rates["output_per_million"]) / 1_000_000)
    result["cost_per_turn"] = mean(costs) if costs else None
    result["cost_currency"] = "USD"
    result["cost_reported"] = len(costs)
    result["top_errors"] = []
    for tag, rows in sorted(groups.items(), key=lambda pair: (-sum(not s["exact"] for _, s in pair[1]), pair[0]))[:3]:
        errors = [r for r, s in rows if not s["exact"]]
        result["top_errors"].append({"tag": tag, "errors": len(errors), "examples": [
            {k: r.get(k) for k in ("id", "input", "raw_response", "plan", "gold")} for r in errors[:2]]})
    return result
