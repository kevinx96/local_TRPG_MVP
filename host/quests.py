from __future__ import annotations

from typing import Any


def public_quests(session: dict[str, Any]) -> list[dict[str, Any]]:
    flags = session.get("flags", {})
    result = []
    for quest in session.get("scenario_pack", {}).get("quests", []):
        start = quest.get("start_flag", "")
        starts = start if isinstance(start, list) else [start]
        start_items = quest.get('start_items', [quest.get('start_item')])
        has_start_item = any(i.get('id') and i.get('id') in start_items and i.get('quantity', 1) > 0
                             for i in session.get('character', {}).get('inventory', []) if isinstance(i, dict))
        completed = bool(quest.get("complete_flags")) and all(flags.get(f) for f in quest["complete_flags"])
        if start and not any(flags.get(flag) for flag in starts) and not has_start_item and not completed:
            continue
        complete = quest.get("complete_flags", [])
        status = "active"
        if complete and all(flags.get(flag) for flag in complete):
            status = "completed"
        if any(flags.get(flag) for flag in quest.get("fail_flags", [])):
            status = "failed"
        stages = quest.get("stages", [])
        def stage_done(stage: dict[str, Any]) -> bool:
            value = stage.get("done_flag")
            return any(flags.get(flag) for flag in (value if isinstance(value, list) else [value]))

        done = [stage["text"] for stage in stages if stage_done(stage)]
        current = next((stage["text"] for stage in stages if not stage_done(stage)), "")
        entry = {key: quest[key] for key in ("id", "title", "description", "kind")}
        entry.update(status=status, current_objective=current if status == "active" else "",
                     completed_stages=done)
        if "clue_flags" in quest:
            entry["clue_count"] = sum(bool(flags.get(flag)) for flag in quest["clue_flags"])
            entry["clue_count"] += int(any(
                item.get("id") in quest.get('clue_items', [quest.get('clue_item')]) and item.get("quantity", 1) > 0
                for item in session.get("character", {}).get("inventory", []) if isinstance(item, dict)))
        result.append(entry)
    return result


def record_quest_changes(session: dict[str, Any], before: list[dict[str, Any]]) -> None:
    from .state import record_state_event

    previous = {quest["id"]: quest for quest in before}
    for quest in public_quests(session):
        old = previous.get(quest["id"], {})
        if old and all(old.get(key) == quest[key] for key in ("status", "current_objective", "completed_stages")):
            continue
        label = "クエスト達成" if quest["status"] == "completed" else "クエスト更新"
        record_state_event(session, "quest_updated", f"{label}：{quest['title']}",
                           {"quest_id": quest["id"], "status": quest["status"]})
