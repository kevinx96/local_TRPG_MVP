"""Add Mina escort disclosure and a one-time post-quest fire-bat-dragon loan."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from host.difficulty import apply_difficulty, numeric_snapshot

ROOT = Path(__file__).resolve().parents[2]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")

ESCORT_NOTICE = "【仮】今の同行者とは別れることになる。"
REBORROW_ACTION_ID = "borrow_fire_bat_dragon_again"
REBORROW_ACTION_TEXT = "ペットの火コウモリ竜をもう一度借りる"
REBORROW_PREVIEW = "もう一度、火コウモリ竜を借りる"
REBORROW_ONCE_FLAG = "asked_to_borrow_fire_bat_dragon_again"
# TODO(design): approve the tentative reborrow dialogue before removing its 【仮】 marker.
REBORROW_SUCCESS_TEXT = (
    "火コウモリ竜はあなたの匂いを嗅ぐと肩へ飛び乗った。"
    "サラは嬉しそうに笑い、「【仮】ちゃんと連れて帰ってね」と送り出した。"
)


def _location(pack: dict[str, Any], location_id: str) -> dict[str, Any]:
    return next(location for location in pack["locations"] if location.get("id") == location_id)


def _action(location: dict[str, Any], action_id: str) -> dict[str, Any]:
    return next(action for action in location.get("actions", []) if action.get("id") == action_id)


def _sync_reborrow_absence_text(pack: dict[str, Any]) -> None:
    entries = pack.setdefault("npc_absence_texts", [])
    for outcome in ("success", "failure"):
        source_path = f"/locations/item_shop/hybrid/prepared_turns/fire_bat_borrow_{outcome}/draft/gm_text"
        target_path = f"/locations/item_shop/hybrid/prepared_turns/fire_bat_borrow_again_{outcome}/draft/gm_text"
        source = next((entry for entry in entries if entry.get("path") == source_path), None)
        if source is None:
            source = next((entry for entry in entries if entry.get("path") == target_path), None)
        if source is None:
            raise ValueError(f"missing fire-bat {outcome} absence-text entry")
        replacement = deepcopy(source)
        replacement["path"] = target_path
        if outcome == "success":
            replacement["text"] = REBORROW_SUCCESS_TEXT
        # Inventory generation keeps only the last path for duplicate prose.
        entries[:] = [
            entry for entry in entries
            if entry.get("path") != target_path and entry.get("text") != replacement.get("text")
        ]
        entries.append(replacement)
    entries.sort(key=lambda entry: (-len(str(entry.get("text") or "")), str(entry.get("text") or "")))


def _no_companion_requirements(pack: dict[str, Any]) -> list[dict[str, str]]:
    companion_ids = sorted({str(row["id"]) for row in pack.get("companions", []) if row.get("id")})
    if not companion_ids:
        raise ValueError("scenario pack must define companion IDs")
    return [{"not_companion_id": companion_id} for companion_id in companion_ids]


def migrate(pack: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(pack)
    spring = _location(result, "cave_hot_spring")
    escort = _action(spring, "escort_mina")
    preview = str(escort.get("preview") or "").rstrip()
    if ESCORT_NOTICE not in preview:
        preview = preview.rstrip("。") + "。" + ESCORT_NOTICE
    escort["preview"] = preview

    shop = _location(result, "item_shop")
    original = _action(shop, "borrow_fire_bat_dragon")
    reborrow = deepcopy(original)
    reborrow.update(
        id=REBORROW_ACTION_ID,
        text=REBORROW_ACTION_TEXT,
        preview=REBORROW_PREVIEW,
        intent_keywords=[REBORROW_ACTION_TEXT],
        once=REBORROW_ONCE_FLAG,
        requirements={
            "all": [
                {"flag": "borrowed_fire_bat_dragon"},
                *_no_companion_requirements(result),
                {"flag": "mina_quest_done"},
            ]
        },
    )
    shop["actions"] = [
        action for action in shop.get("actions", []) if action.get("id") != REBORROW_ACTION_ID
    ]
    original_index = next(
        i for i, action in enumerate(shop["actions"]) if action.get("id") == "borrow_fire_bat_dragon"
    )
    shop["actions"].insert(original_index + 1, reborrow)

    prepared_turns = shop.setdefault("hybrid", {}).setdefault("prepared_turns", [])
    sources = {
        "success": "fire_bat_borrow_success",
        "failure": "fire_bat_borrow_failure",
    }
    for outcome, source_id in sources.items():
        source_turn = next(turn for turn in prepared_turns if turn.get("id") == source_id)
        turn = deepcopy(source_turn)
        turn.update(
            id=f"fire_bat_borrow_again_{outcome}",
            player_intent=REBORROW_ACTION_ID,
            action_id=REBORROW_ACTION_ID,
            outcome=outcome,
        )
        if outcome == "success":
            turn.setdefault("draft", {})["gm_text"] = REBORROW_SUCCESS_TEXT
        prepared_turns[:] = [
            row for row in prepared_turns if row.get("id") != turn["id"]
        ]
        prepared_turns.append(turn)
    _sync_reborrow_absence_text(result)
    return result


def _update_baby_numeric_freeze(packs: dict[str, dict[str, Any]]) -> None:
    path = ROOT / "host/prompt/processed/difficulty/baby_numeric_freeze.json"
    frozen = json.loads(path.read_text(encoding="utf-8"))
    updated = deepcopy(frozen)
    source_prefix = "actions.@id=borrow_fire_bat_dragon.roll."
    target_prefix = f"actions.@id={REBORROW_ACTION_ID}.roll."
    for filename, pack in packs.items():
        values = numeric_snapshot(apply_difficulty(pack, "baby"))["locations"]["item_shop"]
        source = {key[len(source_prefix):]: value for key, value in values.items() if key.startswith(source_prefix)}
        target = {key[len(target_prefix):]: value for key, value in values.items() if key.startswith(target_prefix)}
        if source != target:
            raise ValueError(f"{filename}: reborrow action changed the frozen borrow mechanics")
        expected = updated[filename]["locations"]["item_shop"]
        expected.update({target_prefix + key: value for key, value in target.items()})
    if updated != frozen:
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    updated_packs: dict[str, dict[str, Any]] = {}
    for filename in PACKS:
        path = ROOT / "host/prompt/processed" / filename
        original = json.loads(path.read_text(encoding="utf-8"))
        updated = migrate(original)
        if updated != original:
            path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        updated_packs[filename] = updated
        print(f"{filename}: escort disclosure and reborrow action ready")
    _update_baby_numeric_freeze(updated_packs)


if __name__ == "__main__":
    main()
