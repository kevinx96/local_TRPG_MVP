"""Pure M1–M13 reducers over one experiment bundle; no engine mutation or IO."""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import mean, median
from typing import Any, Callable

EPSILON = 1e-12


def _result(data: dict[str, Any], identifier: str, value: Any, checks: list[bool], *,
            reason: str = "", applicable: bool = True) -> dict[str, Any]:
    spec = data["targets"]["metrics_v2"][identifier]
    meets = all(checks) if checks else None
    status = ("pass" if meets else "fail") if spec["hard_gate"] else "report"
    if not applicable:
        status, meets = "not_applicable", None
    return {"id": identifier, "value": value, "target": spec["target"], "status": status,
            "hard_gate": spec["hard_gate"], "meets_target": meets, "reason": reason or None}


def _records(data):
    return data.get("records", [])


def _battles(data, archetype=None, category="boss"):
    return [(t, b) for t in _records(data) if archetype is None or t["archetype"] == archetype
            for b in t.get("battles", []) if b.get("encounter_class") == category]


def _interval(value, interval):
    return interval[0] - EPSILON <= value <= interval[1] + EPSILON


def m1(data: dict[str, Any]) -> dict[str, Any]:
    groups = defaultdict(list)
    for record in _records(data):
        if record["archetype"] in {"P0a", "P0b"}:
            groups[record["archetype"], record["character"]].append(record)
    rows, checks = [], []
    target = data["targets"]["metrics_v2"]["M1"]["target"]
    for (archetype, character), trials in sorted(groups.items()):
        value = mean(t["completed"] for t in trials)
        limit = target["mage_max"] if character == "mage" else target["p0_max"]
        checks.append(value <= limit + EPSILON)
        rows.append(dict(archetype=archetype, character=character, value=value, limit=limit,
                         excess_pp=max(0, value - limit) * 100))
    return _result(data, "M1", rows, checks, applicable=bool(rows), reason="冒険完了为主口径；试玩 checkpoint 不计入原型门槛。")


def m1_prime(data: dict[str, Any]) -> dict[str, Any]:
    rates = defaultdict(dict)
    for record in _records(data):
        rates[record["character"]].setdefault(record["archetype"], []).append(record["completed"])
    rows, checks = [], []
    limit = data["targets"]["metrics_v2"]["M1'"]["target"]["adjacent_gap_min"]
    for character, values in sorted(rates.items()):
        for low, high in (("P0a", "P1"), ("P0b", "P1"), ("P1", "P2"), ("P2", "P3")):
            if low in values and high in values:
                gap = mean(values[high]) - mean(values[low])
                checks.append(gap + EPSILON >= limit)
                rows.append(dict(character=character, lower=low, upper=high, gap_pp=gap * 100,
                                 shortfall_pp=max(0, limit - gap) * 100))
    return _result(data, "M1'", rows, checks, applicable=bool(rows), reason="分别以 P0a、P0b 检查 P0→P1，避免自行合并两种 P0。")


def m2(data: dict[str, Any]) -> dict[str, Any]:
    rows, checks = data.get("preparation_probes", []), []
    target = data["targets"]["metrics_v2"]["M2"]["target"]
    for row in rows:
        checks.append(row["uplift"] + EPSILON >= target["critical_uplift_min"] if row["critical"]
                      else row["uplift"] <= target["noncritical_uplift_max"] + EPSILON)
    return _result(data, "M2", rows, checks, applicable=bool(rows), reason="准备清单为 proposed；净化按达成目标遭遇成功计（victory/purified）。")


def m3(data: dict[str, Any]) -> dict[str, Any]:
    groups = defaultdict(list)
    for trial, battle in _battles(data, "P0b"):
        groups[trial["character"], battle["encounter"], battle.get("companion") or "none",
               battle["expected_healing"]].append(battle)
    rows, checks = [], []
    for (character, encounter, companion, _), battles in sorted(groups.items()):
        incoming = mean(b["opening"]["expected_damage"] for b in battles)
        healing = mean(b["expected_healing"] for b in battles)
        value = healing / incoming if incoming else None
        checks.append(value is not None and value < data["targets"]["metrics_v2"]["M3"]["target"]["p0b_sustain_lt"])
        rows.append(dict(character=character, encounter=encounter, companion=companion, value=value,
                         zero_incoming=not incoming, n=len(battles), healing=healing, incoming=incoming))
    return _result(data, "M3", rows, checks, applicable=bool(rows), reason="可持续回复能力（未扣过量回复）/开场完整敌方每回合期望伤害；消耗品计入 M3'。")


def m3_prime(data: dict[str, Any]) -> dict[str, Any]:
    groups = defaultdict(list)
    for trial, battle in _battles(data):
        if trial["archetype"] not in {"P0b", "P2"}:
            continue
        incoming = battle["opening"]["expected_damage"] - battle["expected_healing"]
        pool = battle["before"]["hp"] + battle["before"].get("healing_hp", 0)
        depletion = pool / incoming if incoming > 0 else None
        ratio = battle["rounds"] / depletion if depletion else 0.0 if incoming <= 0 else None
        groups[trial["archetype"], trial["character"], battle["encounter"]].append((ratio, depletion, battle["status"]))
    rows, checks = [], []
    target = data["targets"]["metrics_v2"]["M3'"]["target"]
    for (archetype, character, encounter), values in sorted(groups.items()):
        finite = [value for value, _, status in values if status in {"victory", "purified"} and value is not None]
        value = mean(finite) if finite else None
        checks.append(value is not None and (value > target["p0b_race_gt"] if archetype == "P0b" else _interval(value, target["p2_race"])))
        rows.append(dict(archetype=archetype, character=character, encounter=encounter, value=value,
                         n=len(values), kill_time_samples=len(finite),
                         censored_defeats=sum(status not in {"victory", "purified"} for _, _, status in values),
                         infinite_depletion=sum(depletion is None for _, depletion, _ in values)))
    return _result(data, "M3'", rows, checks, applicable=bool(rows),
                   reason="击杀回合只取胜利/净化样本；失败为右删失。耗尽按当前 HP+库存回复与净开场伤害估计；有限 MP/SP 主动回复未换算进此静态资源池，实际使用仍影响击杀回合。净伤害≤0时耗尽为无限，赛跑比0。")


def m4(data: dict[str, Any]) -> dict[str, Any]:
    groups = defaultdict(list)
    for trial, battle in _battles(data):
        groups[trial["archetype"], trial["character"], battle["encounter"], battle["policy"]].append(battle["rounds"])
    for row in data.get("boss_policy_probes", []):
        groups["checkpoint", row["character"], row["encounter"], row["policy"]].extend(row["rounds"])
    target = data["targets"]["metrics_v2"]["M4"]["target"]
    rows = [dict(archetype=a, character=c, encounter=e, policy=p, median=median(values), n=len(values),
                 sandbag=median(values) > target["sandbag_gt"])
            for (a, c, e, p), values in sorted(groups.items())]
    return _result(data, "M4", rows, [r["median"] <= target["median_rounds_max"] for r in rows], applicable=bool(rows))


def m5(data: dict[str, Any]) -> dict[str, Any]:
    rows, checks = [], []
    target = data["targets"]["metrics_v2"]["M5"]["target"]
    for trial in _records(data):
        if trial["archetype"] != "P1":
            continue
        arrivals = trial.get("boss_arrivals", {})
        arrival = arrivals.get("draco_battle") or arrivals.get("dragon_valley_loc")
        if not arrival:
            continue
        initial = trial.get("initial", {})
        healing_names = set(trial.get("healing_item_names", []))
        used = sum(n for b in trial["battles"] for item, n in b.get("consumables", {}).items() if item in healing_names)
        remaining = sum(n for item, n in trial["final"]["inventory"].items() if item in healing_names)
        usage = used / (used + remaining) if used + remaining else None
        spent = sum(max(0, p["before"]["gold"] - p["after"]["gold"]) for p in trial.get("purchases", []))
        spent += sum(r.get("cost", 0) for r in trial.get("rests", []))
        earned = trial["final"]["gold"] + spent
        unspent = trial["final"]["gold"] / earned if earned else None
        inventory = arrival["healing_hp"] / arrival["max_hp"]
        row = dict(character=trial["character"], seed=trial.get("seed"),
                   healing_hp_ratio=inventory, healing_usage=usage, unspent_gold_ratio=unspent)
        checks.append(inventory <= target["healing_hp_ratio_max"] + EPSILON and usage is not None and
                      _interval(usage, target["healing_usage"]) and unspent is not None and
                      unspent <= target["unspent_gold_ratio_max"] + EPSILON)
        rows.append(row)
    summary = []
    for character in sorted({r["character"] for r in rows}):
        values = [r for r in rows if r["character"] == character]
        summary.append({"character": character, "n": len(values), **{
            k: mean(r[k] for r in values if r[k] is not None) if any(r[k] is not None for r in values) else None
            for k in ("healing_hp_ratio", "healing_usage", "unspent_gold_ratio")}})
    return _result(data, "M5", summary, checks, applicable=bool(rows), reason="只统计到达最终 Boss 的 P1；道具使用率=消耗/(消耗+结余)，金币含开局支给。")


def m6(data: dict[str, Any]) -> dict[str, Any]:
    groups = defaultdict(list)
    for trial, battle in _battles(data):
        counts = battle.get("actions", {})
        if not counts:
            continue
        action = max(counts, key=counts.get)
        share = counts[action] / sum(counts.values())
        red = bool(battle.get("action_specs", {}).get(action, {}).get("free")) and action == battle.get("p0_choice") and share > .70 + EPSILON
        groups[trial["archetype"], trial["character"], battle["encounter"]].append((share, red, action))
    rows = [dict(archetype=a, character=c, encounter=e, dominant_share=mean(v[0] for v in values),
                 flagged_battles=sum(v[1] for v in values), n=len(values), actions=dict(Counter(v[2] for v in values)))
            for (a, c, e), values in sorted(groups.items())]
    return _result(data, "M6", rows, [r["flagged_battles"] == 0 for r in rows], applicable=bool(rows))


def m7(data: dict[str, Any]) -> dict[str, Any]:
    groups = defaultdict(list)
    for trial in _records(data):
        for probe in trial.get("check_probes", []):
            groups[trial["archetype"], trial["character"], probe["action"]].append(probe)
    rows, checks = [], []
    for (a, c, action), values in sorted(groups.items()):
        success, failure = mean(p["success"] for p in values), mean(p["failure"] for p in values)
        loss = (success - failure) / success if success else None
        checks.append(loss is not None and loss + EPSILON >= data["targets"]["metrics_v2"]["M7"]["target"]["resource_loss_min"])
        rows.append(dict(archetype=a, character=c, action=action, n=len(values), success_resources=success,
                         failure_resources=failure, resource_loss_ratio=loss))
    return _result(data, "M7", rows, checks, applicable=bool(rows), reason="成对普通成功/失败分支，沿真实后果打完被迫战斗后比较 resource_score；不是观察性分组，也不估整路线通关差。")


def m8(data: dict[str, Any]) -> dict[str, Any]:
    rows = data.get("companion_probes", [])
    interval = data["targets"]["metrics_v2"]["M8"]["target"]["companion_uplift"]
    return _result(data, "M8", rows, [_interval(r["uplift"], interval) for r in rows], applicable=bool(rows),
                   reason="每职业/每同伴/每 Boss，与同配置无同伴成对比较；负提升也保留。")


def m9(data: dict[str, Any]) -> dict[str, Any]:
    rows, checks = [], []
    intervals = data["targets"]["metrics_v2"]["M9"]["target"]
    for entry in data.get("damage_budget_v2", []):
        category = entry["encounter_class"]
        if category in intervals:
            rows.append(entry)
            checks.append(_interval(entry["ratio"], intervals[category]))
    return _result(data, "M9", rows, checks, applicable=bool(rows), reason="开场全部敌人，未命中/防御等零伤害回合计入；保留旧预算上限接口。")


def m10(data: dict[str, Any]) -> dict[str, Any]:
    rows = [dict(encounter=r["encounter"], character=r["character"], cv=r["cv"], notes=r.get("notes", []))
            for r in data.get("damage_budget_v2", [])]
    maximum = data["targets"]["metrics_v2"]["M10"]["target"]["ordinary_cv_max"]
    return _result(data, "M10", rows, [r["cv"] is not None and r["cv"] <= maximum + EPSILON for r in rows], applicable=bool(rows),
                   reason="当前仍有低命中技能；报告实际 CV。100%命中和预告机制待 050/051，不能据现状认证高 CV 技能已预告。")


def m11(data: dict[str, Any]) -> dict[str, Any]:
    groups = defaultdict(list)
    targets = data["targets"]["metrics_v2"]["M11"]["target"]
    for trial in _records(data):
        for battle in trial.get("battles", []):
            if battle.get("encounter_class") in targets:
                groups[trial["archetype"], trial["character"], battle["encounter"], battle["encounter_class"]].append(
                    battle["expected_hp_loss"] / battle["before"]["max_hp"])
    rows = [dict(archetype=a, character=c, encounter=e, encounter_class=category, value=mean(values), n=len(values))
            for (a, c, e, category), values in sorted(groups.items())]
    return _result(data, "M11", rows, [_interval(r["value"], targets[r["encounter_class"]]) for r in rows], applicable=bool(rows),
                   reason="在实际轨迹每次敌方阶段按当时存活敌人精确求期望并求和；不减回复，保留防御/抗性实际作用。")


def m12(data: dict[str, Any]) -> dict[str, Any]:
    return _result(data, "M12", {"skill_turn_ratio": None, "single_skill_ratio": None,
                                "dead_options": None, "passive_value_gap": None}, [], applicable=False,
                   reason="待 050/051：新主动技能、被动二选一和冷却未实装；不将现有技能冒充新机制样本。")


def m13(data: dict[str, Any]) -> dict[str, Any]:
    rows = data.get("level_probes", [])
    interval = data["targets"]["metrics_v2"]["M13"]["target"]["per_level_uplift"]
    groups = defaultdict(list)
    for record in _records(data):
        if record["archetype"] in {"P0a", "P0b", "P2"} and "dragon_valley_loc" in record.get("levels", {}):
            groups[record["character"], record["archetype"]].append(record["levels"]["dragon_valley_loc"])
    gaps = []
    for character, archetype in sorted(groups):
        if archetype.startswith("P0") and (character, "P2") in groups:
            gaps.append(dict(character=character, p0=archetype, p0_level=mean(groups[character, archetype]),
                             p2_level=mean(groups[character, "P2"]),
                             gap=mean(groups[character, "P2"])-mean(groups[character, archetype])))
    return _result(data, "M13", {"checkpoint_probes": rows, "current_arrival_level_gaps": gaps,
                                "p0_p2_arrival_level_gap": None, "exp_validation_status": "待 050/051"},
                   [_interval(r["uplift"], interval) for r in rows], applicable=bool(rows),
                   reason="当前可做固定装备、每级成长的 ±1 checkpoint 探针；战斗 EXP 与满级8待 050/051，到达等级差只描述现状，不认证 EXP 目标。")


METRICS: tuple[Callable[[dict[str, Any]], dict[str, Any]], ...] = (
    m1, m1_prime, m2, m3, m3_prime, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13)


def evaluate(data: dict[str, Any]) -> list[dict[str, Any]]:
    return [metric(data) for metric in METRICS]
