"""Offline save telemetry. Missing history stays unknown; prose is never an action log."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Optional

from scripts.balance import checkpoints, sim

DEFAULT_SAVE = checkpoints.ROOT / "eval/playtests/e2b9fdd9631c441298685da5d75d6cfb.json"
PREPARATIONS = checkpoints.ROOT / "eval/balance/preparations.json"
GAPS = [
    "combat_id 关联的完整战斗开始/结束快照、遭遇 ID、类别和等级；event_log 当前会截断。",
    "逐回合玩家行动 ID、目标、消耗、伤害/回复，以及状态/冷却；recent_events 只有末尾文本。",
    "道具移除的原因（使用、交易或剧情交付）及其 action_id/combat_id；移除不能直接算回复使用。",
    "带 action_id 的完整判定和其失败资源变化/后续战斗关联；dice_log 本身没有地点或 action_id。",
    "完整配装/同伴/休息流水，以及准备项在具体战斗中生效的记录。",
    "存档所用引擎版本及剧本指纹；区域回退快照不是某场 Boss 的开战快照。",
]


def _actions(pack: dict[str, Any]) -> list[dict[str, Any]]:
    def walk(entries):
        for entry in entries:
            yield entry
            yield from walk(entry.get("children", []))
    return [a for loc in pack.get("locations", []) for a in walk(loc.get("actions", []))]


def _log_event(log: dict[str, Any]) -> dict[str, Any]:
    text = log.get("text", "")
    kind, data = "text_only", {}
    match = re.fullmatch(r"(\d+)ゴールドを(獲得|消費)しました。", text)
    if match:
        kind, data = "gold_changed", {"change": int(match[1]) * (1 if match[2] == "獲得" else -1)}
    match = re.fullmatch(r"(.+) x(\d+)を(入手しました|失いました)。", text)
    if match:
        kind, data = ("item_added" if match[3] == "入手しました" else "item_removed"), {"item": match[1], "quantity": int(match[2])}
    match = re.search(r"HP (\d+)/(\d+)、MP (\d+)/(\d+)、SP (\d+)/(\d+)", text)
    if match and text.startswith("戦闘"):
        kind = "combat_resolved"
        data = {"outcome": "victory" if "勝利" in text else "unknown", "rounds": None,
                "player": dict(zip(("hp", "max_hp", "mp", "max_mp", "sp", "max_sp"), map(int, match.groups())))}
    if text.startswith("現在地が") and text.endswith("になりました。"):
        kind, data = "position_text", {"name": text[len("現在地が"):-len("になりました。")]}
    match = re.fullmatch(r"レベルが(\d+)に上がりました。", text)
    if match:
        kind, data = "level_up", {"level": int(match[1])}
    if text == "HP・MP・SPが全回復しました。":
        kind = "resources_restored"
    return {"id": log.get("event_id"), "kind": kind, "data": data, "text": text,
            "created_at": log.get("created_at", ""), "evidence": "system_log_text"}


def merged_events(save: dict[str, Any], auxiliary: Iterable[dict[str, Any]] = ()) -> list[dict[str, Any]]:
    events = []
    for container in [save, *auxiliary]:
        for event in container.get("event_log", container.get("events", [])):
            events.append({**event, "evidence": "structured_event"})
    ids = {e.get("id") for e in events if e.get("id")}
    events += [_log_event(log) for log in save.get("system_logs", []) if not log.get("event_id") or log["event_id"] not in ids]
    seen, result = set(), []
    for event in sorted(events, key=lambda e: e.get("created_at", "")):
        key = event.get("id") or json.dumps(event, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            result.append(event)
            seen.add(key)
    return result


def healing_capacity(player: dict[str, Any], catalog: dict[str, Any]) -> Optional[float]:
    if "inventory" not in player:
        return None
    result = 0.0
    for item in player["inventory"]:
        spec = item.get("combat") or catalog.get(item.get("id") or item.get("name"), {}).get("combat", {})
        if spec.get("kind") == "heal" and spec.get("consumable", True):
            amount = player.get("max_hp", 0) * spec["max_hp_ratio"] if "max_hp_ratio" in spec else sim.formula_mean(str(spec.get("healing", "10")), player)
            result += amount * item.get("quantity", 1)
    return result


def extract(save: dict[str, Any], auxiliary: Iterable[dict[str, Any]] = (), *,
            preparations: Optional[dict[str, Any]] = None,
            archetype_rows: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    pack, actor = save.get("scenario_pack", {}), save.get("character", {})
    auxiliary = [r for r in auxiliary if r.get("session_id") == save.get("id")]
    events = merged_events(save, auxiliary)
    catalog = {key: i for i in [*pack.get("items", []), *actor.get("inventory", [])]
               for key in (i.get("id"), i.get("name")) if key}
    locations = {loc["id"]: loc for loc in pack.get("locations", [])}
    by_name = {loc.get("title", loc.get("name")): loc["id"] for loc in locations.values()}
    def enemy_ids(location):
        loc = locations.get(location, {})
        return loc.get("combat", {}).get("enemy_ids", loc.get("enemy_ids", []))
    battles, history, ledger = [], [], []
    equipment, rests, checks = [], [], []
    arrivals: dict[str, Any] = {}
    latest_player: dict[str, Any] = {}
    observed_level = None
    transition_before = None
    def arrival_value():
        return {"hp": latest_player.get("hp"), "max_hp": latest_player.get("max_hp"),
                "healing_hp": healing_capacity(latest_player, catalog), "level": observed_level,
                "inventory": deepcopy(latest_player.get("inventory")),
                "evidence": "reconstructed_from_previous_resolution_and_resource_events",
                "reason": "非开战直接快照；按可观察流水重建，未记录的变化不可排除。"}
    for event in events:
        data, kind = event.get("data", {}), event.get("kind")
        stamp = event.get("created_at")
        if kind == "position_changed":
            transition_before = data.get("before", {}).get("location_id")
            for position in (data.get("before", {}), data.get("after", {})):
                if position.get("location_id"):
                    history.append(position["location_id"])
        elif kind == "position_text":
            if data.get("name") in by_name:
                transition_before = history[-1] if history else None
                history.append(by_name[data["name"]])
        elif kind == "level_up":
            observed_level = data.get("level")
            gains = data.get("gains_per_level", {})
            levels_gained = data.get("levels_gained", 1)
            for resource in ("hp", "mp", "sp"):
                maximum = "max_"+resource
                if maximum in latest_player and maximum in gains:
                    latest_player[maximum] += gains[maximum]*levels_gained
                    latest_player[resource] = latest_player[maximum]
        if kind == "resources_restored":
            for resource in ("hp", "mp", "sp"):
                if "max_"+resource in latest_player:
                    latest_player[resource] = latest_player["max_"+resource]
        if kind == "resource_changed" and data.get("resource"):
            latest_player[data["resource"]] = data.get("after")
        if kind in {"item_added", "item_removed"} and "inventory" in latest_player:
            name = data.get("item") or data.get("item_id")
            entry = next((i for i in latest_player["inventory"] if name in (i.get("name"), i.get("id"))), None)
            change = data.get("quantity", 1) * (1 if kind == "item_added" else -1)
            if entry:
                entry["quantity"] = max(0, entry.get("quantity", 1)+change)
            elif change > 0:
                latest_player["inventory"].append({"name": name, "quantity": change})
        if kind in {"position_changed", "position_text"} and history:
            current = history[-1]
            if locations.get(current, {}).get("combat", {}).get("encounter_class") == "boss":
                arrivals.setdefault(current, arrival_value())
        if kind == "combat_resolved":
            enemies = sorted(e["id"] for e in data.get("enemies", []))
            encounter = data.get("location_id")
            if not encounter:
                candidates = [transition_before, *reversed(history)]
                encounter = next((loc for loc in candidates if enemy_ids(loc)
                                  and (not enemies or sorted(enemy_ids(loc)) == enemies)), None)
            player = data.get("player", {})
            battle = {"event_id": event.get("id"), "encounter": encounter,
                      "encounter_class": locations.get(encounter, {}).get("combat", {}).get("encounter_class"),
                      "rounds": data.get("rounds"), "outcome": data.get("outcome"),
                      "end_hp": player.get("hp"), "max_hp": player.get("max_hp"),
                      "actions": None, "actions_coverage": "missing", "created_at": stamp,
                      "evidence": event["evidence"], "location_evidence": "explicit" if data.get("location_id") else "position_history_and_enemy_ids"}
            battles.append(battle)
            if battle["encounter_class"] == "boss":
                arrivals.setdefault(str(encounter), arrival_value())
            latest_player = deepcopy(player)
            # The engine commits the victory transition before the previous
            # battle's resolution event. Its result is the next encounter's
            # arrival state, not that next encounter's ending HP.
            if history and history[-1] != encounter and locations.get(history[-1], {}).get("combat", {}).get("encounter_class") == "boss":
                arrivals[history[-1]] = arrival_value()
        if kind in {"item_added", "item_removed", "gold_changed"}:
            ledger.append({"event_id": event.get("id"), "kind": kind, "created_at": stamp,
                           "evidence": event["evidence"], **data})
        if kind == "item_equipped":
            equipment.append({"created_at": stamp, **data})
        if kind == "action_resolved":
            action_id = data.get("action_id", "")
            if action_id in {"rest_at_elf_spring", "rest_hot_spring", "rest_at_inn", "rest_at_refuge"}:
                rests.append({"action": action_id, "created_at": stamp, "evidence": "action_resolved"})
            roll = data.get("roll", {})
            if roll.get("dc", 0) > 0:
                checks.append({"action": action_id, "outcome": data.get("outcome"), "created_at": stamp,
                               "failure_cost": None, "reason": "资源事件缺少 action_id，不能作因果归属。"})
    # Recover rest actions from exact user choice labels when the event ring has
    # dropped them. Count by timestamp, not by adding both evidence streams.
    rest_actions = {a["text"]: a["id"] for a in _actions(pack) if a.get("id") in
                    {"rest_at_elf_spring", "rest_hot_spring", "rest_at_inn", "rest_at_refuge"} and a.get("text")}
    for message in save.get("messages", []):
        if message.get("role") == "user" and message.get("text") in rest_actions:
            action = rest_actions[message["text"]]
            stamp = message.get("created_at", "")
            # User message and its action event are milliseconds apart; use
            # the interval until the next user message to join them.
            following = next((m.get("created_at", "") for m in save.get("messages", [])
                              if m.get("role") == "user" and m.get("created_at", "") > stamp), "9999")
            if not any(r["action"] == action and stamp <= r["created_at"] < following for r in rests):
                rests.append({"action": action, "created_at": stamp, "evidence": "exact_user_choice"})
    # Full combat records in explicitly supplied local traces may enrich the
    # save, but the current LLM metadata format supplies no player actions.
    for record in auxiliary:
        for entry in record.get("battles", []):
            target = next((b for b in battles if entry.get("event_id") and entry["event_id"] == b["event_id"]), None)
            if target and isinstance(entry.get("actions"), dict):
                target.update(actions=entry["actions"], actions_coverage="trace")
            if entry.get("encounter") and entry.get("before"):
                arrivals[entry["encounter"]] = {**entry["before"], "evidence": "trace_before_snapshot"}
    dice = [r for r in save.get("dice_log", []) if r.get("dc", 0) > 0]
    failed = [r for r in dice if r.get("success") is False]
    item_added, item_removed = Counter(), Counter()
    gold_earned = gold_spent = 0
    for entry in ledger:
        if entry["kind"] == "gold_changed":
            change = int(entry.get("change", 0))
            gold_earned += max(change, 0)
            gold_spent += max(-change, 0)
        else:
            name = entry.get("item") or entry.get("item_id")
            (item_added if entry["kind"] == "item_added" else item_removed)[str(name)] += entry.get("quantity", 1)
    heal_names = {i.get("name") for i in catalog.values() if i.get("combat", {}).get("kind") == "heal"}
    prep_rows = []
    for encounter, group in (preparations or {}).get("encounters", {}).items():
        for prep in group["items"]:
            ids = set(prep.get("item_ids", []))
            names = {catalog[key]["name"] for key in ids if key in catalog}
            owned = any(i.get("id") in ids or i.get("name") in names for i in actor.get("inventory", []))
            flags = prep.get("flags", [])
            acquired = owned or any(item_added[name] for name in names) or (bool(flags) and any(save.get("flags", {}).get(f) for f in flags))
            used = None
            if prep.get("remove", {}).get("kind") == "equipment":
                used = any(e.get("item_id") in ids for e in equipment)
            if "fire_bat_empowered" in flags:
                used = bool(save.get("flags", {}).get("fire_bat_empowered"))
            prep_rows.append({"encounter": encounter, "preparation": prep["id"], "acquired": acquired,
                              "used_anywhere_observed": used, "used_in_target_battle": None,
                              "acquired_by_target_battle": None})
            row = prep_rows[-1]
            arrival_inventory = arrivals.get(encounter, {}).get("inventory")
            if ids and arrival_inventory is not None:
                row["acquired_by_target_battle"] = any(i.get("id") in ids or i.get("name") in names for i in arrival_inventory)
            target_battle = next((b for b in battles if b["encounter"] == encounter), None)
            if target_battle and prep.get("remove", {}).get("kind") == "equipment":
                equipped = list(actor.get("equipment", []))
                for event in reversed(events):
                    if event.get("kind") == "item_equipped" and event.get("created_at", "") > target_battle["created_at"]:
                        change = event["data"]
                        changed_name = catalog.get(change.get("item_id"), {}).get("name")
                        equipped = [name for name in equipped if name != changed_name]
                        if change.get("removed"):
                            equipped.append(change["removed"])
                row["used_in_target_battle"] = any(name in names for name in equipped)
                row["usage_evidence"] = "end_equipment_rollback_after_target; exploration_only_equipping"
    for rest in rests:
        rest["location"] = {"rest_at_elf_spring": "elf_spring", "rest_hot_spring": "cave_hot_spring",
                            "rest_at_inn": "inn", "rest_at_refuge": "village"}[rest["action"]]
    flags = save.get("flags", {})
    features = {"sidequests": sum(bool(flags.get(k)) for k in
                 ("cleared_goblin_fort", "cleared_cave_prism_tree", "saved_gald", "riku_rescued", "sarah_moss_done", "draco_journal")),
                "cave": bool(flags.get("cleared_cave_prism_tree")), "fort": bool(flags.get("cleared_goblin_fort")),
                "purification": bool(flags.get("ignis_purified"))}
    # Behavioural classification, not the result of one stochastic playthrough.
    nearest = "P2" if features["cave"] or features["fort"] else "P1" if features["sidequests"] else "P0b" if save.get("companion") else "P0a"
    return {"version": 2, "session_id": save.get("id"),
            "available_fields": {key: {"type": type(value).__name__, "count": len(value) if isinstance(value, (list, dict)) else None}
                                 for key, value in save.items()},
            "coverage": {"event_log": len(save.get("event_log", [])), "event_log_may_be_truncated": len(save.get("event_log", [])) >= 240,
                         "system_logs": len(save.get("system_logs", [])), "matched_auxiliary": len(auxiliary),
                         "combat_action_history": "missing" if not any(b["actions"] is not None for b in battles) else "partial"},
            "battles": battles, "boss_arrivals": arrivals, "resource_ledger": ledger,
            "healing_items": {"obtained_observed": {k: v for k, v in item_added.items() if k in heal_names},
                              "removed_observed": {k: v for k, v in item_removed.items() if k in heal_names},
                              "used": None, "reason": "移除不等于使用，且日志可能截断。",
                              "final_healing_hp": healing_capacity(actor, catalog)},
            "gold": {"earned_observed": gold_earned, "spent_observed": gold_spent, "final": actor.get("gold"),
                     "coverage": "system_logs_and_structured_events_deduplicated"},
            "checks": {"count": len(dice), "successes": sum(r.get("success") is True for r in dice),
                       "success_rate": sum(r.get("success") is True for r in dice) / len(dice) if dice else None,
                       "failures": failed, "attributed": checks},
            "equipment_changes": {"count_observed": len(equipment), "events": equipment},
            "rests": sorted(rests, key=lambda r: r["created_at"]), "preparations": prep_rows,
            "comparison": {"nearest": nearest, "status": "proposed", "features": features,
                           "reason": "按可观察支线行为归类；洞窟/砦超过 P0b 的三次交互预算，未完成全部准备链。",
                           "rows": [r for r in archetype_rows if r.get("character") == actor.get("character_id")],
                           "completed": (save.get("game_over") or {}).get("title") == "冒険完了"},
            "engine_recording_gaps": GAPS}


def markdown(report: dict[str, Any]) -> str:
    lines = ["# 046b 人类试玩遥测", "", f"存档：`{report['session_id']}`。原始字段先列如下；缺失量保留 null。", "",
             "| 字段 | 类型 | 条目数 |", "|---|---|---:|"]
    for key, value in report["available_fields"].items():
        lines.append(f"| {key} | {value['type']} | {value['count']} |")
    lines += ["", "| 遭遇 | 类别 | 回合 | 结束 HP | 行动记录 |", "|---|---|---:|---|---|"]
    for battle in report["battles"]:
        lines.append(f"| {battle['encounter']} | {battle['encounter_class']} | {battle['rounds']} | {battle['end_hp']}/{battle['max_hp']} | {battle['actions_coverage']} |")
    lines += ["", f"判定：{report['checks']['successes']}/{report['checks']['count']}；失败代价无法完整关联。",
              f"金币：可观察收入 {report['gold']['earned_observed']}G，支出 {report['gold']['spent_observed']}G，最终 {report['gold']['final']}G。",
              f"回复：{json.dumps(report['healing_items'], ensure_ascii=False)}",
              f"配装变更可观察到 {report['equipment_changes']['count_observed']} 次。",
              f"休息：{json.dumps(report['rests'], ensure_ascii=False)}", "",
              "| 准备 | 全程已获得 | 目标战前持有 | 可观察使用（全程） | 目标战使用 |", "|---|---|---|---|---|"]
    for row in report["preparations"]:
        lines.append(f"| {row['preparation']} | {row['acquired']} | {row['acquired_by_target_battle']} | {row['used_anywhere_observed']} | {row['used_in_target_battle']} |")
    lines += ["", "Boss 开战 HP/库存回复/等级：", "", json.dumps(report["boss_arrivals"], ensure_ascii=False, indent=2), "",
              "| 原型 | 职业 | 通关率 |", "|---|---|---:|"]
    for row in report["comparison"]["rows"]:
        lines.append(f"| {row['archetype']} | {row['character']} | {row['completion_rate']:.1%} |")
    lines += ["", f"最接近 {report['comparison']['nearest']}（提案）：{report['comparison']['reason']}",
              "这只比较行为，不能把这一局的胜利替代原型的抽样通关率。", "", "需要引擎侧补记录：", ""]
    lines += ["- " + gap for gap in report["engine_recording_gaps"]]
    return "\n".join(lines) + "\n"


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline save telemetry; no model calls")
    parser.add_argument("save", type=Path)
    parser.add_argument("--traces", type=Path, nargs="*", default=[])
    parser.add_argument("--completions", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, default=checkpoints.ROOT / "eval/reports/046b-save-telemetry.json")
    args = parser.parse_args(argv)
    save = json.loads(args.save.read_text(encoding="utf-8-sig"))
    auxiliary = []
    for source in args.traces:
        paths = sorted(source.glob("*.jsonl")) if source.is_dir() else sorted(source.parent.glob(source.name))
        if not paths:
            parser.error(f"No trace files: {source}")
        for path in paths:
            auxiliary.extend(json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip())
    if args.completions:
        auxiliary.extend(json.loads(path.read_text(encoding="utf-8-sig")) for path in sorted(args.completions.glob("*.json")))
    preparations = json.loads(PREPARATIONS.read_text(encoding="utf-8")) if PREPARATIONS.exists() else {}
    rows = json.loads(args.baseline.read_text(encoding="utf-8"))["rows"] if args.baseline else []
    result = extract(save, auxiliary, preparations=preparations, archetype_rows=rows)
    result["save_sha256"] = hashlib.sha256(args.save.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"battles": len(result["battles"]), "checks": result["checks"]["count"],
                      "rests": len(result["rests"]), "nearest": result["comparison"]["nearest"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
