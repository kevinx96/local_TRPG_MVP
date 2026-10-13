from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable
from unittest.mock import patch

from host import combat, state
from host.scenario_context import current_action_choices
from scripts.balance import checkpoints, class_aware

SCENES = {"throne_room", "dark_forest"}
DEFAULT_OUTPUT = checkpoints.ROOT / "eval/reports/choice-visibility-2026-10-13.md"
LABELS = {"available": "可选", "known": "已知但不可选", "unknown": "未知"}


def walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def navigation_actions(pack: dict[str, Any]) -> tuple[set[str], set[str], set[str]]:
    """Keep moves/combat and the transitive prerequisites of those actions."""
    locations = [loc for loc in pack["locations"] if loc["scene_id"] in SCENES]
    actions = [node for loc in locations for node in walk(loc.get("actions", [])) if "text" in node and "id" in node]
    selected = {a["id"] for a in actions if any(
        node.get("current_location") or node.get("start_combat") for node in walk(a)) or a.get("free_action")}
    flags: set[str] = set()
    items: set[str] = set()
    while True:
        before = (len(selected), len(flags), len(items))
        for action in actions:
            if action["id"] not in selected:
                continue
            for node in walk(action):
                for key in ("flag", "not_flag", "visible_after", "hidden_after", "once", "disabled_after"):
                    if isinstance(node.get(key), str):
                        flags.add(node[key])
                for key in ("has_item", "inventory_has", "requires_item", "lacks_item", "not_item", "missing_item"):
                    if isinstance(node.get(key), str):
                        items.add(node[key])
        for action in actions:
            for node in walk(action):
                item = node.get("add_item", {})
                if (node.get("set_flag") in flags or any(f in flags for f in node.get("flags_set", []))
                        or isinstance(item, dict) and item.get("name") in items):
                    selected.add(action["id"])
        if before == (len(selected), len(flags), len(items)):
            return selected, flags, items


def signature(session: dict[str, Any], flags: set[str], items: set[str]) -> tuple:
    actor = session["character"]
    return (state.current_location_id(session),
            tuple(sorted(f for f in flags if session["flags"].get(f))),
            tuple(sorted(i["name"] for i in actor["inventory"] if i["name"] in items)),
            (session.get("companion") or {}).get("id"),
            bool(session.get("combat_start_requested")), session.get("combat_blocked_location"))


def first_arrivals(pack: dict[str, Any], character: str) -> dict[str, dict[str, Any]]:
    selected, flags, items = navigation_actions(pack)
    targets = {loc["id"] for loc in pack["locations"] if loc["scene_id"] in SCENES}
    initial = checkpoints.fresh_session(pack, character)
    state.apply_opening_effects(initial)
    queue = deque([(initial, [])])
    visited = {signature(initial, flags, items)}
    arrivals: dict[str, dict[str, Any]] = {}
    while queue and len(arrivals) < len(targets):
        session, path = queue.popleft()
        location = state.current_location_id(session)
        pending = class_aware.combat_pending(session)
        if location not in arrivals:
            arrivals[location] = {"session": session, "path": path, "combat": pending}
        successors = []
        if pending:
            copy = deepcopy(session, {id(pack): pack})
            checkpoints.replay_step(copy, "@victory")
            successors.append((copy, "@victory"))
        else:
            for action in class_aware.available_actions(session).values():
                if action["id"] not in selected:
                    continue
                for _, face in class_aware.outcome_faces(session, action):
                    copy = deepcopy(session, {id(pack): pack})
                    # Free-action checks use state.random; ordinary checks accept a die face.
                    with patch.object(state, "random", class_aware.FixedDice(face or 20)):
                        class_aware.apply_action(copy, action, face)
                    outcome = copy.get("last_action_result", {}).get("outcome", "")
                    step = action["id"] + (":" + outcome if face is not None else "")
                    successors.append((copy, step))
        for copy, step in successors:
            if state.current_location_id(copy) not in targets or copy.get("game_over"):
                continue
            key = signature(copy, flags, items)
            if key in visited:
                continue
            visited.add(key)
            # The history cache preserves item knowledge without retaining every event.
            copy["event_log"] = []
            copy["dice_log"] = []
            copy["choices"] = []
            queue.append((copy, [*path, step]))
        if len(visited) > 100000:
            raise RuntimeError(f"Navigation search exceeded 100000 states: {character}")
    if targets - arrivals.keys():
        raise ValueError(f"Unreached chapter locations for {character}: {sorted(targets - arrivals.keys())}")
    return arrivals


def names(pack: dict[str, Any]) -> dict[str, set[tuple[str, str]]]:
    catalog: dict[str, set[tuple[str, str]]] = {}

    def add(name: str, kind: str, identifier: str) -> None:
        if len(name) >= 2:
            catalog.setdefault(name, set()).add((kind, identifier))

    for loc in pack["locations"]:
        add(loc["title"], "地点", loc["id"])
        for fragment in loc["title"].split("・"):
            add(fragment, "地点", loc["id"])
    for layout in pack.get("maps", []):
        for node in layout.get("nodes", []):
            for loc in node.get("location_ids", []):
                add(node.get("label", ""), "地点", loc)
    for npc in pack.get("npcs", []):
        add(npc.get("name", ""), "NPC", npc["id"])
        for alias in npc.get("aliases", []):
            add(alias, "NPC", npc["id"])
    for node in walk(pack):
        if node.get("name") and ("quantity" in node or "category" in node or node.get("combat", {}).get("kind")):
            add(str(node["name"]), "道具", str(node["name"]))
    return catalog


def encountered(pack: dict[str, Any], session: dict[str, Any], path: list[str]) -> set[tuple[str, str]]:
    seen = {("道具", name) for name in state.known_item_names(session)}
    replay = checkpoints.fresh_session(pack, session["character"]["character_id"])
    state.apply_opening_effects(replay)

    def arrival() -> None:
        location_id = state.current_location_id(replay)
        seen.add(("地点", location_id))
        loc = next(loc for loc in pack["locations"] if loc["id"] == location_id)
        for npc in loc.get("npc_ids", []):
            if state._session_requirement_passes(loc.get("npc_requirements", {}).get(npc), replay):
                seen.add(("NPC", npc))

    arrival()
    for step in path:
        if step == "@victory":
            checkpoints.replay_step(replay, step)
        else:
            action_id, _, outcome = step.partition(":")
            action = state.resolve_action(replay, action_id=action_id)
            face = None
            if outcome:
                dice, dc = state.action_dice_settings(action, session=replay)
                distribution = class_aware.check_distribution(replay, dice, dc,
                    critical=action.get("critical_enabled") is not False)
                face = distribution[outcome][1]
            with patch.object(state, "random", class_aware.FixedDice(face or 20)):
                class_aware.apply_action(replay, action, face)
        arrival()
    return seen


def flatten(choices: list[dict[str, Any]], prefix: str = "") -> Iterable[tuple[str, dict[str, Any]]]:
    for choice in choices:
        text = prefix + choice["text"]
        yield text, choice
        yield from flatten(choice.get("children", []), text + " / ")


def inspect_arrival(pack: dict[str, Any], record: dict[str, Any], catalog: dict) -> dict[str, Any]:
    session = record["session"]
    raw = state.annotate_choices_for_session(current_action_choices(session), session)
    choices = state.player_choices_for_session(state.annotate_choices_for_character(raw, session["character"]), session)
    if record["combat"]:
        combat_session = {**session, "combat": {"encounter": combat._encounter_for_session(session, pack)}}
        choices = [{"text": action["name"], "preview": action.get("description", ""),
                    "disabled_reason": action.get("disabled_reason", ""),
                    "visibility": "available" if action.get("enabled", True) else "known"}
                   for action in combat.combat_actions(combat_session)]
    seen = encountered(pack, session, record["path"])
    hits = []
    for title, choice in flatten(choices):
        text = " ".join(str(choice.get(key, "")) for key in ("text", "preview", "risk", "disabled_reason"))
        matches = [name for name, entities in catalog.items() if name in text and not entities & seen]
        for name in sorted(matches):
            if not any(name != other and name in other for other in matches):
                hits.append((title, name, " / ".join(sorted({kind for kind, _ in catalog[name]}))))
    return {"choices": choices, "hits": hits}


def generate(pack: dict[str, Any]) -> str:
    characters = [c for c in pack["characters"] if c.get("selectable", True)]
    catalog = names(pack)
    runs = {}
    for character in characters:
        runs[character["id"]] = first_arrivals(pack, character["id"])
        print(f"{character['id']}: {len(runs[character['id']])} locations reached", flush=True)
    locations = [loc for loc in pack["locations"] if loc["scene_id"] in SCENES]
    lines = ["# 028 第 1–2 章首次到达选项可见性", "",
        f"覆盖 {len(locations)} 个地点 × {len(characters)} 个职业；Base / Hybrid 的 actions、条件、entry_effects 已由同步测试核对。", "",
        "## 方法与边界", "",
        "- 在确定性引擎上广度优先搜索最少操作路线；开场 100G + 薬草不计操作，每个选项和整场胜利各计一步。只在第 1–2 章内行进。判定枚举所有可发生结果；战斗假定获胜，不消耗药品。这是剧情可达性路线，不是生存率或推荐攻略。",
        "- 保留移动、开战，以及它们依赖的 flag / 道具的前置动作；不为无关对话、购物和装备优化绕路。等长路线按剧本选项顺序、骰面结果顺序取首条。状态按导航相关 flag、道具、同伴、战斗阻挡去重，因此报告提供一条最短导航见证，不穷举所有等长路线的可见性差异。",
        "- 到达后立即使用 public session 同一套过滤和脱敏函数。列出所有可见子项；职业不匹配、secret、visible_after、hidden_after 隐藏的内容不列入玩家选项。战斗自动开始的地点改列 combat_actions 指令（按入场资源，未计算抢攻伤害）；不把战斗期间隐藏的探索卡片当成可见选项。",
        "- 专名词典来自地点标题（含「・」分段）、地图 label、NPC name / aliases、道具 name。按文字子串扫描标题、preview、risk、不可选原因；重叠名称取最长。已到过的地点、到达时满足 npc_requirements 的 NPC、当前或曾持有的道具记作已遇到。只听说过但尚未到访/见到/持有，仍列待核对；未识别别称、同名和普通词可能漏报或误报。",
        "- 自动列出的名称只是 TODO(design) 审查候选，导航目的地、承诺奖励、NPC 请求提到的物品可能合理。没有据此修改其他剧本内容。", ""]
    total_hits: set[tuple[str, str]] = set()
    for loc in locations:
        lines += [f"## {loc['title']} (`{loc['id']}`)", ""]
        groups: dict[str, dict[str, Any]] = {}
        for character in characters:
            record = runs[character["id"]][loc["id"]]
            result = inspect_arrival(pack, record, catalog)
            key = json.dumps([record["path"], record["combat"], result], ensure_ascii=False, sort_keys=True)
            group = groups.setdefault(key, dict(record=record, result=result, characters=[]))
            group["characters"].append(character.get("class") or character.get("name") or character["id"])
        for group in groups.values():
            record, result = group["record"], group["result"]
            lines += [f"职业：{' / '.join(group['characters'])}。最少 {len(record['path'])} 步。", "",
                      "路线：`@opening" + (" → " + " → ".join(record["path"]) if record["path"] else "") + "`。", ""]
            if record["combat"]:
                lines += ["到达即进入战斗；下表为战斗指令。", ""]
            lines += ["| 可见标题 | 类别 |", "|---|---|"]
            for title, choice in flatten(result["choices"]):
                lines.append(f"| {title.replace('|', '／')} | {LABELS[choice['visibility']]} |")
            if not result["choices"]:
                lines.append("| （无探索选项） | — |")
            lines += [""]
            if result["hits"]:
                lines += ["待核对名称：", "", "| 名称 | 类型 | 出现于选项 |", "|---|---|---|"]
                for title, name, kind in result["hits"]:
                    total_hits.add((loc["id"], name))
                    lines.append(f"| {name} | {kind} | {title} |")
                lines += [""]
            else:
                lines += ["词典内未发现尚未遇到的名称。", ""]
    lines += ["## 待设计审查", "", f"共 {len(total_hits)} 个「地点 × 名称」候选（职业间去重）。",
              "TODO(design): 逐项判断是否属于合理的目的地/任务预告，或需要 secret / visible_after 等叙事门槛；本任务只修正 spec 指定的 ask_seal_lore。", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline first-arrival visibility audit")
    parser.add_argument("--scenario", type=Path, default=checkpoints.DEFAULT_SCENARIO)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    pack = state.load_scenario_pack(args.scenario)
    report = generate(pack)
    report += "\nScenario SHA-256: `" + hashlib.sha256(args.scenario.read_bytes()).hexdigest() + "`\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
