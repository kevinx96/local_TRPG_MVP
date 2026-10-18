from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TOWN_DESCRIPTION = "王城の門前から石畳の大通りが延びる城下町。鍛冶屋の煙突からは煙が上がり、宿屋の看板が風に揺れ、魔法店の窓には青い灯りがともる。裏手には細い路地が口を開けている。邪竜の噂のせいか、行き交う人々の声はどこか低い。"
SUPPLIES_TEXT = "侍従が小箱を差し出した。「教会より、邪竜討伐に向かわれる方へ」中には清められた聖水が二本収められている。"


def choice(action: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(value) for key, value in action.items()
            if key in ("text", "preview", "risk", "requirements", "children", "secret", "visible_after", "hidden_after")}


def navigation(identifier: str, text: str, preview: str, destination: str) -> dict[str, Any]:
    return dict(id=identifier, text=text, preview=preview, risk="判定不要",
                intent_keywords=[text], effects=[dict(current_location=destination)])


def upgrade(pack: dict[str, Any]) -> None:
    locations = {entry["id"]: entry for entry in pack["locations"]}
    castle = locations["castle"]
    town = locations.get("castle_town")
    if town is None:
        group = next(a for a in castle["actions"] if a["id"] == "explore_castle_town")
        departure = next(a for a in castle["actions"] if a["id"] == "go_dark_forest")
        town = dict(id="castle_town", scene_id="throne_room", title="アルテリア城下町",
                    description=TOWN_DESCRIPTION, keywords=["城下町", "大通り", "城門"],
                    npc_ids=["gald"], npc_requirements={"gald": {"flag": "saved_gald"}},
                    actions=[*deepcopy(group["children"]),
                             navigation("return_castle_from_town", "王城へ戻る", "王城へ戻る", "castle"),
                             deepcopy(departure)],
                    hybrid={"mode": "prepared_gm_turns", "prepared_turns": []})
        pack["locations"].insert(pack["locations"].index(castle) + 1, town)
        locations["castle_town"] = town
    town["background_image"] = "/static/images/bg_castle_town.png"
    town["connected_location_ids"] = ["forge", "inn", "magic_shop", "item_shop", "alley", "castle", "dark_forest_loc"]
    departure = next(a for a in town["actions"] if a["id"] == "go_dark_forest")
    departure.update(text="城門を出て闇の森へ向かう", preview="第2章へ進みます",
                     intent_keywords=["城門を出て闇の森へ向かう"])
    town["choices"] = [choice(a) for a in town["actions"]]

    castle["actions"] = [a for a in castle["actions"] if a["id"] not in
                         {"explore_castle_town", "go_dark_forest", "go_castle_town"}]
    castle["actions"].insert(3, navigation("go_castle_town", "城下町へ出る", "王城の門前に広がる城下町へ", "castle_town"))
    castle["connected_location_ids"] = ["castle_town", "village"]
    castle["opening_effects"] = [{"gold_change": 100}, {"add_item": {"name": "薬草", "quantity": 1}}]
    supplies = next(a for a in castle["actions"] if a["id"] == "check_supplies")
    supplies.update(text="侍従から旅の支給品を受け取る", preview="教会から届いた聖水を受け取ります",
                    intent_keywords=["侍従から旅の支給品を受け取る"], result_text=SUPPLIES_TEXT)
    supplies["effects"][0]["branch"]["then"] = [
        effect for effect in supplies["effects"][0]["branch"]["then"] if "gold_change" not in effect]
    castle["choices"] = [choice(a) for a in castle["actions"]]

    for source in (castle, locations["forge"]):
        source["actions"] = [a for a in source["actions"] if a["id"] != "go_dark_forest"]
        turns = source.get("hybrid", {}).get("prepared_turns", [])
        moved = [t for t in turns if t.get("action_id") == "go_dark_forest"]
        for turn in moved:
            if not any(t["id"] == turn["id"] for t in town["hybrid"]["prepared_turns"]):
                town["hybrid"]["prepared_turns"].append(turn)
        source.get("hybrid", {})["prepared_turns"] = [t for t in turns if t not in moved]

    for identifier in ("forge", "inn", "magic_shop", "item_shop", "alley", "alley_night", "alley_after"):
        location = locations[identifier]
        for action in location["actions"]:
            if action["id"].startswith("return_castle") or action["id"] == "leave_night_alley":
                action.update(text="城下町に戻る", preview="大通りへ戻る", intent_keywords=["城下町に戻る"])
                action["effects"] = [{"branch": {"requirements": {"flag": "returned_to_capital"},
                                      "then": [{"current_location": "festival_town"}],
                                      "else": [{"current_location": "castle_town"}]}}]
        location["connected_location_ids"] = [
            "castle_town" if destination == "castle" else destination
            for destination in location.get("connected_location_ids", []) if destination != "dark_forest_loc"]
        if "castle_town" not in location["connected_location_ids"]:
            location["connected_location_ids"].append("castle_town")
        location["choices"] = [choice(a) for a in location["actions"]]

    lore = next(a for a in locations["magic_shop"]["actions"] if a["id"] == "ask_seal_lore")
    lore.update(secret=True, requirements={"any": [{"flag": "mina_missing_heard"}, {"flag": "seen_cave_seal"}]})
    locations["magic_shop"]["choices"] = [choice(a) for a in locations["magic_shop"]["actions"]]
    seal = locations["cave_seal"]
    if {"set_flag": "seen_cave_seal"} not in seal.setdefault("entry_effects", []):
        seal["entry_effects"].append({"set_flag": "seen_cave_seal"})

    def sync(value: Any) -> None:
        if isinstance(value, list):
            for child in value:
                sync(child)
        elif isinstance(value, dict):
            if value.get("purpose") == "opening":
                draft = value.get("draft", {})
                draft["gm_text"] = draft.get("gm_text", "").replace("50ゴールド", "100ゴールド")
                if draft.get("state_delta", {}).get("gold_change") == 50:
                    draft["state_delta"]["gold_change"] = 100
            if value.get("action_id") == "check_supplies" and "draft" in value:
                value["draft"]["gm_text"] = SUPPLIES_TEXT
            for key, child in value.items():
                if isinstance(child, str):
                    replacements = {
                        "支度金50ゴールド": "支度金100ゴールド",
                        "支度金と装備を確認する": "侍従から旅の支給品を受け取る",
                        "所持金、薬草、装備を整理します": "教会から届いた聖水を受け取ります",
                        "城を出て闇の森へ向かう": "城門を出て闇の森へ向かう",
                    }
                    for old, new in replacements.items():
                        child = child.replace(old, new)
                    value[key] = child
                else:
                    sync(child)
    sync(pack)
    for location in (castle, locations["forge"]):
        for turn in location.get("hybrid", {}).get("prepared_turns", []):
            if turn.get("draft", {}).get("choices"):
                turn["draft"]["choices"] = deepcopy(location["choices"])
    for identifier in ("inn", "magic_shop", "item_shop", "alley", "alley_night", "alley_after"):
        for turn in locations[identifier].get("hybrid", {}).get("prepared_turns", []):
            for item in turn.get("draft", {}).get("choices", []):
                if item.get("text") in ("城に戻る", "城へ戻る", "取引せず城へ戻る"):
                    item.update(text="城下町に戻る", preview="大通りへ戻る")

    scene = next(s for s in pack["scenes"] if s["id"] == "throne_room")
    if "castle_town" not in scene["location_ids"]:
        scene["location_ids"].append("castle_town")
    if "next_scene_ids" in scene:
        scene["next_scene_ids"] = [s for s in scene["next_scene_ids"] if s != "castle_town"]
    specs = [("C1", "王城", "start", 50, 12, ["castle"]),
             ("C2", "城下町", "event", 50, 48, ["castle_town"]),
             ("forge", "鍛冶屋", "event", 18, 30, ["forge"]),
             ("inn", "宿屋", "rest", 18, 68, ["inn", "inn_night_ambush"]),
             ("magic_shop", "魔法店", "event", 82, 30, ["magic_shop"]),
             ("item_shop", "道具屋", "event", 82, 68, ["item_shop"]),
             ("alley", "路地裏", "branch", 34, 88, ["alley", "alley_night", "alley_after", "merchant_battle"]),
             ("gate", "城門", "branch", 66, 88, [])]
    # TODO(design): 城門 uses branch until a chapter-exit map kind is specified.
    nodes = [dict(id=i, label=label, kind=kind, x=x, y=y, location_ids=ids,
                  description=locations[ids[0]]["description"] if ids else "城下町の南にある大門。その先の街道は、闇の森へと続いている。")
             for i, label, kind, x, y, ids in specs]
    edges = []
    for node, outward, inward in [("C1", "return_castle_from_town", "go_castle_town"),
                                  *[(i, "go_" + i, "return_castle_from_" + i)
                                    for i in ("forge", "inn", "magic_shop", "item_shop", "alley")],
                                  ("gate", "go_dark_forest", "go_castle_town")]:
        edges.extend([dict(**{"from": "C2", "to": node}, action_id=outward),
                      dict(**{"from": node, "to": "C2"}, action_id=inward)])
    capital = dict(id="capital", title="アルテリア城下町", nodes=nodes, edges=edges,
                   requirements={"not_flag": "returned_to_capital"})
    next(e for e in edges if e["from"] == "alley")["action_by_location"] = {
        "alley_night": "leave_night_alley", "alley_after": "return_castle_after_curse"}
    pack["maps"] = [capital, *[m for m in pack["maps"] if m["id"] != "capital"]]
    pack["meta"]["content_revision"] = "2026-10-13-v028-castle-town"


def main() -> None:
    for filename in ("dragon_rpg.json", "dragon_rpg_hybrid.json"):
        path = ROOT / "host/prompt/processed" / filename
        pack = json.loads(path.read_text(encoding="utf-8"))
        upgrade(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
