"""Assemble and audit the hand-authored scenario-v2 supplement, offline only."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from host import free_actions, state
from .benchmark_v2 import similarity_violations
from .generate_candidates import gold, write_json
from .metrics import severity
from .run import engine_result
from .snapshots import ROOT, load_snapshot

SOURCE = ROOT / "eval/candidates/intent_v2_scenario_authored.txt"
OUTPUT = ROOT / "eval/candidates/intent_v2_scenario.jsonl"
TAGS = ("observe_clue", "report_choice", "evidence_claim", "scale_handling", "lore_question")


def recipes() -> dict[str, dict[str, Any]]:
    locations = {
        "C": ("castle_departure", "castle", "hero"),
        "G": ("third_gate", "goblin_fort_third_gate", "thief"),
        "I": ("ice_elemental", "ice_elemental_encounter", "mage"),
        "D": ("ignis_last_breath", "ignis_last_breath", "hero"),
        "E": ("report_evidence", "castle_report", "hero"),
        "N": ("report_no_evidence", "castle_report", "hero"),
        "V": ("elder", "village", "mage"),
        "T": ("ian", "inn", "thief"),
    }
    result = {}
    for alias, (name, location, actor) in locations.items():
        result[alias] = dict(id=f"v2_scenario_{name}", scenario="host/prompt/processed/dragon_rpg.json",
                             gm_mode="full", character_id=actor, location_id=location, hp_delta=0,
                             flags={"defeated_ignis": True} if alias in {"D", "E", "N"} else {},
                             inventory_add=[], inventory_remove=[], recent_messages=[])
    result["E"]["inventory_add"] = [dict(id="white_dragon_scale", name="白い竜鱗", quantity=1)]
    return result


def answer(code: str) -> dict[str, Any]:
    code, _, tier = code.partition("@")
    if code.startswith("e:"):
        result = gold("existing", action_id=code[2:])
    elif code.startswith("o:"):
        result = gold("interact", operation="observe", target_id=code[2:])
    elif code.startswith("talk:"):
        result = gold("dialogue", target_id=code[5:])
    elif code in {"dialogue", "unsupported", "clarify"}:
        result = gold(code)
    else:
        raise ValueError(code)
    if tier:
        if tier not in {"S0", "S1"}:
            raise ValueError(tier)
        result["tier"] = tier
    return result


def authored_rows() -> list[dict[str, Any]]:
    rows = []
    tag = ""
    counts: Counter = Counter()
    recipe_map = recipes()
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            tag = line[1:]
            continue
        alias, codes, harm, family, note, text = line.split("|", 5)
        counts[tag] += 1
        harmful: dict[str, list[str]] = dict(operation=[], kind=[], action_id=[])
        if harm != "-":
            for feature in harm.split(","):
                key, value = feature.split(":", 1)
                harmful[{"op": "operation", "e": "action_id", "kind": "kind"}[key]].append(value)
        rows.append(dict(id=f"v2-scenario-{tag}-{counts[tag]:03d}", family=family,
                         snapshot=recipe_map[alias]["id"], input=text, tags=[tag], primary_tag=tag,
                         gold=[answer(code) for code in codes.split(",")], harmful=harmful,
                         gold_note=f"依据 LABELING.md 第 {note}", label_status="proposed", split="dev"))
    return rows


def assemble() -> list[dict[str, Any]]:
    for recipe in recipes().values():
        write_json(ROOT / "eval/snapshots" / f"{recipe['id']}.json", recipe)
    rows = authored_rows()
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return rows


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = []
    counts = Counter(row["primary_tag"] for row in rows)
    if not 40 <= len(rows) <= 60 or any(counts[tag] < 6 for tag in TAGS):
        errors.append("case/tag count")
    if len({r["id"] for r in rows}) != len(rows) or len({r["input"] for r in rows}) != len(rows):
        errors.append("duplicate id/input")
    sessions = {identifier: load_snapshot(identifier) for identifier in dict.fromkeys(r["snapshot"] for r in rows)}
    matrix: dict[str, Counter] = defaultdict(Counter)
    actors: Counter = Counter()
    gold_count = 0
    for row in rows:
        session = sessions[row["snapshot"]]
        matrix[row["snapshot"]].update(row["tags"])
        actors[session["character"]["character_id"]] += 1
        if (row["split"] != "dev" or row["label_status"] != "proposed" or row["primary_tag"] not in row["tags"]
                or not row["gold"] or set(row["harmful"]) != {"operation", "kind", "action_id"}):
            errors.append(f"{row['id']}: metadata")
        for entry in row["gold"]:
            gold_count += 1
            try:
                plan = free_actions.parse_plan(json.dumps({k: v for k, v in
                    {**entry, "approach": "", "reply": ""}.items() if k != "tier"}), session["character"]["character_id"])
                engine = engine_result(session, plan, row["input"])
                score = severity({**row, "plan": plan, "engine": engine})
                if engine["outcome"] == "rejected" or score not in {"S0", "S1"}:
                    errors.append(f"{row['id']}: gold rejected or scored {score}: {entry}")
            except free_actions.InvalidPlan as exc:
                errors.append(f"{row['id']}: {exc}")
    expected_snapshots = {r["id"] for r in recipes().values()}
    if set(sessions) != expected_snapshots:
        errors.append("snapshot coverage")
    for alias, enabled in (("E", True), ("N", False)):
        session = sessions[recipes()[alias]["id"]]
        action = state.resolve_action(session, action_id="report_with_evidence")
        if state.action_requirement_status(action, session)[0] != enabled:
            errors.append(f"{alias}: evidence gate")
    violations = similarity_violations(rows)
    return dict(total=len(rows), primary_tags=dict(counts), split=dict(Counter(r["split"] for r in rows)),
                actors=dict(actors), snapshot_tags={k: dict(v) for k, v in matrix.items()},
                gold_checked=gold_count, errors=errors, violation_count=len(violations), violations=violations)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assemble", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT.with_name("intent_v2_scenario_audit.json"))
    args = parser.parse_args()
    rows = assemble() if args.assemble else [json.loads(line) for line in OUTPUT.read_text(encoding="utf-8").splitlines()]
    result = audit(rows)
    write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result["errors"] or result["violations"]))


if __name__ == "__main__":
    raise SystemExit(main())
