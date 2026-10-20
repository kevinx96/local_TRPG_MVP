"""048: one spring rest and data-driven post-Ignis guidance (offline, idempotent)."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")
POSTGAME = {"any": [{"flag": "defeated_ignis"}, {"flag": "ignis_purified"}]}
BEFORE = {"all": [{"not_flag": "defeated_ignis"}, {"not_flag": "ignis_purified"}]}
GUIDANCE = {
    "ignis_last_breath": ("return_to_castle_report",),
    "ignis_purified": ("return_to_castle_report",),
    "royal_gate": ("enter_festival_town",),
    "festival_town": ("go_report_hall", "go_general_mansion", "request_king_audience"),
    "castle_report": ("report_normally", "report_with_evidence"),
    "mansion_garden": ("sneak_into_mansion", "robin_picks_lock"),
    "mansion_corridor": ("fight_ice_sentinels", "evade_ice_sentinels", "pass_cleared_sentinels"),
    "mansion_study": ("take_draco_journal", "leave_mansion_study"),
    "king_private_room": ("confide_in_king", "leave_king_room"),
    "forge": ("return_castle_from_forge",),
    "magic_shop": ("return_castle_from_magic_shop",),
    "inn": ("return_castle_from_inn",),
    "item_shop": ("return_castle_from_item_shop",),
    "alley": ("return_castle_from_alley",),
    "alley_night": ("leave_night_alley",),
    "alley_after": ("return_castle_after_curse",),
    "castle": ("go_castle_town",),
    "castle_town": ("return_castle_from_town",),
}
HIDE = {
    "castle": ("ask_king_info", "ask_general_advice", "check_supplies"),
    "forge": ("ask_blacksmith_weakness",),
    "magic_shop": ("ask_blue_mage_rumor",),
    "village": ("ask_elder_weakness",),
}
# (location, NPC ID, existing name). Shops and unrelated quests remain available.
CHATS = (
    ("castle", "king", "国王"), ("castle", "general", "将軍ドラコ"),
    ("castle_town", "gald", "行商人ガルド"),
    ("festival_town", "gald", "行商人ガルド"),
    ("forge", "blacksmith", "鍛冶師ローベルト"),
    ("magic_shop", "warlock", "青いローブの魔法使い"),
    ("magic_shop", "mina", "ミーナ"), ("inn", "ian", "イアン"),
    ("inn", "robin", "ロビン"), ("item_shop", "sarah", "サラ"),
    ("alley_night", "suspicious_merchant", "怪しい商人"),
    ("village", "elder", "長老"), ("village", "shopkeeper", "道具屋の店主"),
)
TRANSITION = "【仮】泉でのひと休みを終え、先へ進む。"


def walk_actions(actions: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for action in actions:
        yield action
        yield from walk_actions(action.get("children", []))


def both(first: Any, second: Any) -> dict[str, Any]:
    if not first or first == second:
        return deepcopy(second)
    if isinstance(first, dict) and second in first.get("all", []):
        return deepcopy(first)
    return {"all": [deepcopy(first), deepcopy(second)]}


def apply(pack: dict[str, Any]) -> None:
    pack["meta"]["content_revision"] = "2026-10-21-guidance-048"
    locations = {loc["id"]: loc for loc in pack["locations"]}
    spring = locations["elf_spring"]
    rest = next(a for a in spring["actions"] if a["id"] == "rest_at_elf_spring")
    rest.update(once="rested_at_elf_spring", hidden_after="rested_at_elf_spring",
                visible_requirements={"not_flag": "defeated_slime_king"},
                risk="危険（戦闘）",
                effects=[{"restore_full": True}, {"current_location": "slime_ambush_one"}, {"start_combat": True}])
    # Reuse the existing description, making the authorized one-use limit explicit.
    rest["preview"] = "【仮】泉で休めるのは一度だけで、休息中に襲われる恐れがある。"
    spring["description"] = "【仮】精霊の泉では一度だけ休める。"
    if isinstance(spring.get("hybrid"), dict):
        spring["hybrid"]["summary"] = spring["description"]
    for game_map in pack.get("maps", []):
        for node in game_map.get("nodes", []):
            if node.get("location_id") == "elf_spring" or "elf_spring" in node.get("location_ids", []):
                node["description"] = spring["description"]
    boss = locations["slime_king_battle"]["combat"]
    boss["victory_effects"]["current_location"] = "forest_wolves"
    texts = boss.setdefault("result_texts", {})
    original = texts.get("victory", "")
    if TRANSITION not in original:
        texts["victory"] = original + ("\n" if original else "") + TRANSITION

    for location_id, ids in HIDE.items():
        for action in walk_actions(locations[location_id]["actions"]):
            if action["id"] in ids:
                action["visible_requirements"] = both(action.get("visible_requirements"), BEFORE)
    for location_id in ("village_frozen_clue", "ian_ice_katana_aftermath"):
        action = next(a for a in locations[location_id]["actions"] if a["id"] == "visit_village")
        action["visible_requirements"] = both(action.get("visible_requirements"), BEFORE)
        replacement = deepcopy(action)
        replacement.update(id="visit_village_postgame", text="【仮】長老のいる村へ向かう。",
                           intent_keywords=[], visible_requirements=deepcopy(POSTGAME))
        if not any(a["id"] == replacement["id"] for a in locations[location_id]["actions"]):
            locations[location_id]["actions"].append(replacement)

    for location_id, npc_id, name in CHATS:
        actions = locations[location_id]["actions"]
        identifier = "postgame_chat_" + npc_id
        if any(a["id"] == identifier for a in actions):
            existing = next(a for a in actions if a["id"] == identifier)
            existing.update(result_text="【仮】邪竜の脅威が去った後の話をする。", risk_source="action")
            continue
        action = dict(id=identifier, text=f"【仮】{name}と討伐後の話をする。",
                      npc_id=npc_id, once=f"{location_id}:{identifier}", effects=[],
                      visible_requirements=deepcopy(POSTGAME),
                      result_text="【仮】邪竜の脅威が去った後の話をする。", risk_source="action")
        if npc_id == "gald":
            action["visible_after"] = "saved_gald"
        if npc_id == "mina":
            action["visible_after"] = "mina_quest_done"
        actions.append(action)

    # Legacy saves can revisit the original capital without returned_to_capital.
    # Keep the existing pre-Ignis destinations and use the same two postgame flags.
    for location_id, action_id, destination in (
        ("castle_town", "return_castle_from_town", "castle"),
        ("village", "return_castle_from_village", "castle_town"),
    ):
        action = next(a for a in locations[location_id]["actions"] if a["id"] == action_id)
        for effect in action["effects"]:
            branch = effect.get("branch", {})
            if branch.get("requirements") == POSTGAME:
                branch["then"] = [{"set_flag": "returned_to_capital"}, {"current_location": "festival_town"}]
        if not any("branch" in e and e["branch"].get("requirements") == POSTGAME for e in action["effects"]):
            for effect in action["effects"]:
                if effect.get("current_location") == destination:
                    effect.pop("current_location")
                    effect["branch"] = dict(requirements=deepcopy(POSTGAME),
                                            then=[{"set_flag": "returned_to_capital"}, {"current_location": "festival_town"}],
                                            **{"else": [{"current_location": destination}]})

    for location_id, ids in GUIDANCE.items():
        found = {a["id"]: a for a in walk_actions(locations[location_id]["actions"])}
        for identifier in ids:
            found[identifier]["guidance"] = True

    # Older migrations reappend their own actions; keep new dialogue after them.
    for loc in locations.values():
        actions = loc.get("actions", [])
        is_new = lambda action: action["id"].startswith("postgame_chat_") or action["id"] == "visit_village_postgame"
        loc["actions"] = [a for a in actions if not is_new(a)] + [a for a in actions if is_new(a)]

    # Synchronize display-only legacy menus, including prepared-turn fallbacks.
    # Avoid copying effects/numbers: 047's baby snapshot must stay identical.
    by_text = {a["text"]: a for loc in locations.values() for a in walk_actions(loc.get("actions", []))}
    changed_ids = {identifier for identifiers in HIDE.values() for identifier in identifiers}
    changed_ids.update(("rest_at_elf_spring", "visit_village"))
    def sync(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ("choices", "fallback_choices") and isinstance(child, list):
                    for choice in walk_actions([c for c in child if isinstance(c, dict)]):
                        source = by_text.get(choice.get("text", ""))
                        if source and source["id"] in changed_ids:
                            for field in ("visible_requirements",):
                                if field in source:
                                    choice[field] = deepcopy(source[field])
                            if source["id"] == "rest_at_elf_spring":
                                choice["preview"] = rest["preview"]
                                choice["once"] = rest["once"]
                                choice["hidden_after"] = rest["hidden_after"]
                sync(child)
        elif isinstance(value, list):
            for child in value:
                sync(child)
    sync(pack)


def placeholder_rows(pack: dict[str, Any], path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(pack, dict):
        for key, value in pack.items():
            yield from placeholder_rows(value, path + "/" + key)
    elif isinstance(pack, list):
        for index, value in enumerate(pack):
            label = value.get("id", index) if isinstance(value, dict) else index
            yield from placeholder_rows(value, path + "/" + str(label))
    elif isinstance(pack, str) and "【仮】" in pack:
        yield path, pack


def recovery_audit(pack: dict[str, Any]) -> list[dict[str, Any]]:
    """Conservative movement cycles, then the engine's permanent defeat guard.

    Branches are over-approximated; paid and item-consuming branches are listed
    separately. A location cycle alone does not make defeated enemies respawn.
    """
    from scripts.playtest.audit import branches

    locations = {loc["id"]: loc for loc in pack["locations"]}
    edges: dict[str, set[str]] = {identifier: set() for identifier in locations}
    resets: dict[str, set[str]] = {identifier: set() for identifier in locations}
    for identifier, loc in locations.items():
        effects = [a.get(key, []) for a in walk_actions(loc.get("actions", []))
                   for key in ("effects", "success_effects", "failure_effects")]
        victory = loc.get("combat", {}).get("victory_effects", {})
        effects.append(victory if isinstance(victory, list) else [victory])
        for effect_list in effects:
            for path in branches(effect_list):
                for effect in path:
                    dest = effect.get("current_location") or effect.get("next_location")
                    if dest in locations:
                        edges[identifier].add(dest)
                    if effect.get("unset_flag"):
                        resets[identifier].add(effect["unset_flag"])
                    resets[identifier].update(effect.get("flags_unset", []))

    def reachable(start: str) -> set[str]:
        visited, pending = set(), [start]
        while pending:
            current = pending.pop()
            if current not in visited:
                visited.add(current)
                pending.extend(edges[current] - visited)
        return visited

    reach = {identifier: reachable(identifier) for identifier in locations}
    results = []
    def visit(actions: list[dict[str, Any]], limited: bool = False) -> Iterator[dict[str, Any]]:
        for action in actions:
            gated = limited or bool(action.get("once") or action.get("disabled_after"))
            if not gated:
                yield action
            yield from visit(action.get("children", []), gated)

    for identifier, loc in locations.items():
        cycle = {other for other in reach[identifier] if identifier in reach[other]}
        cycle_battles = sorted(other for other in cycle
                               if locations[other].get("combat", {}).get("enemy_ids")
                               or locations[other].get("enemy_ids"))
        reset_flags = set().union(*(resets[other] for other in cycle))
        repeatable = []
        for other in cycle_battles:
            enemies = locations[other].get("combat", {}).get("enemy_ids") or locations[other].get("enemy_ids", [])
            if any(f"combat_defeated:{other}:{enemy}" in reset_flags for enemy in enemies):
                repeatable.append(other)
        for action in visit(loc.get("actions", [])):
            for key in ("effects", "success_effects", "failure_effects"):
                for index, path in enumerate(branches(action.get(key, []))):
                    healing = [effect for effect in path if effect.get("restore_full") is True
                               or effect.get("restore_ratio", 0) > 0
                               or any(effect.get(resource + "_change", 0) > 0 for resource in ("hp", "mp", "sp"))]
                    if not healing:
                        continue
                    cost = sum(-min(0, effect.get("gold_change", 0)) for effect in path)
                    consumes = any(effect.get("remove_item") or effect.get("inventory_remove") for effect in path)
                    results.append(dict(location=identifier, action=action["id"], branch=f"{key}/{index}",
                                        recovery=healing, gold_cost=cost, consumes_item=consumes,
                                        cycle_battles=cycle_battles, repeatable_battles=repeatable,
                                        free_repeatable_battle_loop=not cost and not consumes and bool(repeatable)))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true", help="Read-only recovery cycle audit")
    args = parser.parse_args()
    if args.audit:
        for name in PACKS:
            pack = json.loads((ROOT / "host/prompt/processed" / name).read_text(encoding="utf-8"))
            print(json.dumps(dict(pack=name, actions=recovery_audit(pack)), ensure_ascii=False))
        return
    for name in PACKS:
        path = ROOT / "host/prompt/processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"048: {name}: {len(list(placeholder_rows(pack)))} placeholders")
    guard_path = ROOT / "host/prompt/processed/difficulty/overlay_revision.json"
    guard = json.loads(guard_path.read_text(encoding="utf-8"))
    for entry in guard.values():
        entry["content_revision"] = "2026-10-21-guidance-048"
    guard_path.write_text(json.dumps(guard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
