"""Offline success rates for the 29 checks, using design 040's chapter-level convention."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any

from host import state
from scripts.balance import checkpoints
from scripts.scenario.checks_v2 import CHECKS, walk

CHARACTERS = ("hero", "cleric", "mage", "thief")


def chapter_session(pack: dict[str, Any], character: str, level: int) -> dict[str, Any]:
    session = checkpoints.fresh_session(pack, character)
    actor = session["character"]
    actor["level"] = level
    growth = next(m["gains"][character]["attributes"] for m in pack["milestones"] if m["level"] == 2)
    for attribute, amount in growth.items():
        actor["attributes"][attribute] += amount * (level - 1)
    return session


def rates(pack: dict[str, Any], *, legacy: bool = False) -> list[dict[str, Any]]:
    actions = {a["id"]: a for loc in pack["locations"] for a in walk(loc.get("actions", []))}
    rows = []
    for action_id, (skill, _dc, level) in CHECKS.items():
        action = actions[action_id]
        spec = deepcopy(action["roll"])
        spec.pop("advantage", None)
        spec.pop("disadvantage", None)
        row: dict[str, Any] = {"action": action_id, "skill": skill, "level": level, "dc": spec["dc"], "rates": {}}
        for character in CHARACTERS:
            session = chapter_session(pack, character, level)
            if legacy:
                match = state._DICE_ATTR_RE.match(spec["dice_type"])
                attribute = match.group(3)
                modifier = session["character"]["attributes"].get(attribute, 0)
            else:
                modifier = state.dice_check_info(session, spec["dice_type"], spec["dc"], roll=spec)["modifier"]
            successes = sum(face == 20 or (face != 1 and face + modifier >= spec["dc"]) for face in range(1, 21))
            row["rates"][character] = successes / 20
        rows.append(row)
    return rows


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for character in CHARACTERS:
        values = [row["rates"][character] for row in rows]
        result[character] = {"average": mean(values), "only_natural_one_fails": values.count(.95),
                             "at_most_40_percent": sum(value <= .4 for value in values)}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    before = rates(json.loads(args.baseline.read_text(encoding="utf-8")), legacy=True)
    after = rates(pack)
    result = {"before": before, "after": after, "summary_before": summary(before), "summary_after": summary(after)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    names = [next(c["name"] for c in pack["characters"] if c["id"] == identifier) for identifier in CHARACTERS]
    lines = ["# 040 判定成功率（无优势）", "",
             "按设计第6节：29项等权、章节等级，使用剧本每级属性成长（主属性+2、次属性+1），不计装备、线索、同伴、准备与伤势。自然1失败、20成功；按数值判定计算，不把行动可选条件计入概率。",
             "`borrow_fire_bat_dragon`禁用极值，但这张表中的属性与DC使其数值成功率与上述口径相同。", "",
             "|职业|改前平均|改前仅1失败|v2平均|v2仅1失败|v2 ≤40%|", "|---|---:|---:|---:|---:|---:|"]
    for identifier, name in zip(CHARACTERS, names):
        old, new = result["summary_before"][identifier], result["summary_after"][identifier]
        lines.append(f"|{name}|{old['average']:.2%}|{old['only_natural_one_fails']}|{new['average']:.2%}|{new['only_natural_one_fails']}|{new['at_most_40_percent']}|")
    lines += ["", "|行动|技能|等级|DC|" + "|".join(names) + "|", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in after:
        lines.append(f"|{row['action']}|{row['skill']}|{row['level']}|{row['dc']}|" + "|".join(f"{row['rates'][c]:.0%}" for c in CHARACTERS) + "|")
    args.output.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k.startswith("summary")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
