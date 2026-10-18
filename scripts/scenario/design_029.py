"""Design-lead follow-ups to spec 029: fort exit, Base-pack texts, plain-style defeat lines (idempotent)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / "host" / "prompt" / "processed"
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
BASE_FROM_HYBRID = {("castle", "ask_king_info"), ("forge", "ask_blacksmith_weakness"), ("forge", "show_sword_to_blacksmith"),
                    ("forge", "accept_sword_fusion"), ("inn", "ask_robin_rumor")}
FORT_EXIT = {
    "id": "leave_goblin_fort", "text": "砦を出て十字路へ戻る", "preview": "", "risk": "判定不要",
    "intent_keywords": ["砦を出る", "引き返す", "十字路へ戻る"],
    "effects": [{"current_location": "lost_goblin_crossroads"}],
    "result_text": "見張りに気づかれる前に踵を返し、森の十字路まで引き返した。",
}
VALLEY_OPENING = ("「グルルル…」硫黄の煙が立ち込める谷の奥から、紅き邪竜イグニスが巨大な翼を広げて姿を現した。"
                  "その眼光は激しい怒りに燃え、口元からは凄まじい熱気が漏れ出ている。王国を脅かす邪悪なる存在を前に、いよいよ決戦の時だ。")


def _locations(pack: dict) -> dict:
    return {location["id"]: location for location in pack["locations"]}


def _walk(actions: list) -> list:
    found = []
    for action in actions:
        found.append(action)
        found += _walk(action.get("children") or [])
    return found


def _drafts(pack: dict) -> dict:
    """action_id -> neutral prepared gm_text."""
    drafts = {}
    for location in pack["locations"]:
        for turn in (location.get("hybrid") or {}).get("prepared_turns", []):
            text = (turn.get("draft") or {}).get("gm_text")
            if turn.get("action_id") and text and turn.get("outcome", "neutral") in ("neutral", "", None):
                drafts.setdefault(turn["action_id"], text)
    return drafts


PLAIN_ENDINGS = (("で力尽きました。冒険はここで終わりを迎えます。", "で力尽きた。冒険はここで終わりを迎える。"),
                 ("で力尽きました。", "で力尽きた。"))


def _plain(value):
    """Defeat lines are narration, so they use the plain style everywhere they appear (reasons, result texts)."""
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, str):
        for polite, plain in PLAIN_ENDINGS:
            value = value.replace(polite, plain)
    return value


def apply(pack: dict, hybrid_drafts: dict, is_base: bool) -> None:
    pack["meta"]["content_revision"] = "2026-10-13-v029-design"
    pack["locations"] = _plain(pack["locations"])
    locations = _locations(pack)
    fort = locations["goblin_fort"]
    if not any(action["id"] == FORT_EXIT["id"] for action in fort["actions"]):
        fort["actions"].append(json.loads(json.dumps(FORT_EXIT, ensure_ascii=False)))
    for location in pack["locations"]:
        for turn in (location.get("hybrid") or {}).get("prepared_turns", []):
            if turn.get("id") == "dragon_valley_opening":
                turn["draft"]["gm_text"] = VALLEY_OPENING
    if is_base:  # both packs: their action lists must stay identical
        for location_id, action_id in BASE_FROM_HYBRID:
            action = next(a for a in _walk(locations[location_id]["actions"]) if a["id"] == action_id)
            action.setdefault("result_text", hybrid_drafts[action_id])


def main() -> None:
    hybrid = json.loads((DIR / PACKS[1]).read_text(encoding="utf-8"))
    drafts = _drafts(hybrid)
    for name in PACKS:
        path = DIR / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        apply(pack, drafts, is_base=True)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[design_029] updated {name}")


if __name__ == "__main__":
    main()
