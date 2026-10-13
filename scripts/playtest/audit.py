"""Report missing narration and candidates for the design-owned text review."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts.scenario.risk_labels import _walk


ROOT = Path(__file__).resolve().parents[2]


def branches(effects: list[Any]) -> list[list[dict[str, Any]]]:
    paths: list[list[dict[str, Any]]] = [[]]
    for effect in effects:
        if not isinstance(effect, dict):
            continue
        if isinstance(effect.get("branch"), dict):
            branch = effect["branch"]
            options = branches(branch.get("then", [])) + branches(branch.get("else", []))
            paths = [prefix + suffix for prefix in paths for suffix in options]
        else:
            for path in paths:
                path.append(effect)
    return paths


def narration_gaps(pack: dict[str, Any]) -> list[dict[str, str]]:
    gaps = []
    for location in pack["locations"]:
        turns = location.get("hybrid", {}).get("prepared_turns", [])
        for action in _walk(location.get("actions", [])):
            if action.get("children"):
                continue
            outcomes = ("success", "failure") if action.get("roll") else ("neutral",)
            for outcome in outcomes:
                paths = branches([*action.get("effects", []), *action.get(outcome + "_effects", [])])
                stationary = [path for path in paths if not any(e.get("current_location") or e.get("current_scene") for e in path)]
                if not stationary:
                    continue
                text = action.get("result_texts", {}).get(outcome) or action.get("result_text")
                prepared = any((t.get("action_id") == action["id"] or t.get("id") == action.get("prepared_turn_id"))
                               and t.get("outcome", "") in (outcome, "")
                               and (t.get("draft", {}).get("gm_text") or t.get("draft", {}).get("combat_text")) for t in turns)
                ending = all(any(e.get("game_over") for e in path) for path in stationary)
                if text or prepared or ending or action.get("free_action"):
                    continue
                reason = "open_shop" if action.get("open_shop") else "silent" if action.get("silent") else "missing"
                gaps.append(dict(location=location["id"], action=action["id"], outcome=outcome, reason=reason))
    return gaps


def narrative_records(pack: dict[str, Any]):
    def visit(value: Any, path: str):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"gm_text", "combat_text", "result_text", "entry_text", "description"} and isinstance(child, str):
                    yield path + "." + key, child
                elif key == "result_texts" and isinstance(child, dict):
                    for outcome, text in child.items():
                        if isinstance(text, str):
                            yield path + ".result_texts." + outcome, text
                elif key not in {"choices", "intent_keywords", "rewrite_notes"}:
                    yield from visit(child, path + "." + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                yield from visit(child, path + "." + str(child.get("id", index) if isinstance(child, dict) else index))
    yield from visit(pack, "pack")


def style_findings(pack: dict[str, Any]) -> list[dict[str, str]]:
    results = []
    for path, text in narrative_records(pack):
        if not any(field in path for field in ("gm_text", "combat_text", "result_text", "entry_text")):
            continue
        narration = re.sub(r"「[^」]*」|『[^』]*』", "", text)
        if re.search(r"(?:です|でした|でしょう|ます|ました|ません)(?:[。！？\n]|$)", narration):
            results.append(dict(path=path, text=text))
    return results


def quantity_candidates(pack: dict[str, Any]) -> list[dict[str, Any]]:
    locations = {loc["id"]: loc for loc in pack["locations"]}
    numerals = {word: number for number, word in enumerate("零一二三四五六七八九")}
    results = []
    for path, text in narrative_records(pack):
        counts = re.findall(r"([一二三四五六七八九\d]+)(?:匹|体|人(?!影)|つの人影|対の目)", text)
        if not counts or not path.startswith("pack.locations."):
            continue
        location = locations[path.split(".")[2]]
        action_id = path.split(".actions.", 1)[1].split(".")[0] if ".actions." in path else None
        if ".prepared_turns." in path:
            turn_id = path.split(".prepared_turns.", 1)[1].split(".")[0]
            turn = next(t for t in location.get("hybrid", {}).get("prepared_turns", []) if t["id"] == turn_id)
            action_id = turn.get("action_id")
        action = next((a for a in _walk(location.get("actions", [])) if a["id"] == action_id), {})
        destinations = {location["id"]}
        for key in ("effects", "success_effects", "failure_effects"):
            for branch in branches(action.get(key, [])):
                destinations.update(e["current_location"] for e in branch if e.get("current_location"))
        encounters = {dest: locations.get(dest, {}).get("combat", {}).get("enemy_ids", []) for dest in destinations}
        encounters = {dest: ids for dest, ids in encounters.items() if ids}
        declared = sum(int(value) if value.isdigit() else numerals.get(value, 0) for value in counts)
        if encounters and any(len(ids) != declared for ids in encounters.values()):
            results.append(dict(path=path, text=text, stated_count=declared, encounters=encounters))
    return results


def main() -> None:
    reports = {}
    for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        pack = json.loads((ROOT / "host/prompt/processed" / filename).read_text(encoding="utf-8"))
        reports[filename] = dict(narration_gaps=narration_gaps(pack), style=style_findings(pack), quantities=quantity_candidates(pack))
    path = ROOT / "eval/reports/playtest-2026-10-13-audit.json"
    path.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for filename, result in reports.items():
        print(filename, json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
