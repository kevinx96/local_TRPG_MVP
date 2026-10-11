"""Assemble individually authored rows and audit the proposed v2 benchmark offline."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from host import free_actions, state
from .audit import costly_plan
from .generate_candidates import gold
from .snapshots import ROOT, build_snapshot, load_snapshot

SOURCE = ROOT / "eval/candidates/intent_v2_authored.txt"
OUTPUT = ROOT / "eval/candidates/intent_v2.jsonl"
TAGS = ("existing_exact existing_paraphrase negation conditional interact_observe interact_distract "
        "interact_sneak interact_prepare interact_use_item missing_item dialogue chitchat impossible "
        "declared_success injection colloquial language_mix context_followup deixis_unique deixis_multi "
        "sequential parallel excluded_means").split()
LOCATIONS = {
    "C": ("castle", "hero"), "F": ("forge", "hero"), "I": ("inn", "mage"),
    "M": ("magic_shop", "mage"), "S": ("item_shop", "thief"), "A": ("alley", "thief"),
    "N": ("alley_night", "mage"), "Z": ("alley_after", "thief"),
    "H": ("dark_forest_loc", "hero"), "W": ("dark_forest_loc", "mage"),
    "T": ("dark_forest_loc", "thief"), "G": ("lost_goblin_crossroads", "thief"),
    "P": ("elf_spring", "mage"), "E": ("forest_exit", "hero"),
    "B": ("goblin_fort", "thief"), "B2": ("goblin_fort_first_second", "mage"),
    "J": ("goblin_fort_second_choice", "hero"), "R": ("goblin_fort_second_right", "thief"),
    "O": ("goblin_fort_healing_circle", "mage"), "K": ("goblin_fort_third_gate", "hero"),
    "Q": ("goblin_fort_chest_choice", "thief"), "V": ("village", "mage"),
    "U": ("village_approach", "thief"), "X": ("xanxus_confrontation", "hero"),
    "Y": ("xanxus_ultimatum", "mage"), "L": ("village_frozen_clue", "thief"),
    "D": ("ice_elemental_encounter", "mage"), "B3": ("ian_ice_katana_aftermath", "hero"),
    "DR": ("dragon_valley_loc", "hero"),
}
# Context questions name an existing action/method without adding scenario facts.
CONTEXTS = {
    "CH": ("H", "携帯食を一つ投げてスライムを誘い、その間に通り抜けますか？"),
    "CW": ("W", "倒れた枝でスライムの足止めを準備しますか？"),
    "CC": ("C", "国王に邪竜の詳しい話を聞きますか？"),
    "CF": ("F", "鍛冶師に剣を見せますか？"),
    "CI": ("I", "イアンに邪竜を倒すアドバイスを求めますか？"),
    "CD": ("D", "氷の精霊を迂回しますか？"),
    "CJ": ("J", "右の通路を探索しますか？"),
    "CP": ("P", "精霊の泉で休みますか？"),
    "CR": ("H", "スライムは食べ物の匂いに敏感で、視野は狭い。携帯食で誘えば確実に道を空ける。"),
}


def recipes() -> dict[str, dict[str, Any]]:
    result = {}
    for alias, (location, actor) in LOCATIONS.items():
        result[alias] = dict(id=f"v2_{location}_{actor}", scenario="host/prompt/processed/dragon_rpg.json",
                             gm_mode="full", character_id=actor, location_id=location,
                             hp_delta=-5, flags={}, inventory_add=[], inventory_remove=[], recent_messages=[])
    for alias, (base, question) in CONTEXTS.items():
        result[alias] = {**result[base], "id": f"v2_context_{alias.lower()}",
                         "recent_messages": [{"speaker": "GM", "text": question}]}
    result["CR"]["recent_messages"].insert(0, {"speaker": "勇者", "text": "スライムを観察する。"})
    return result


def answer(code: str) -> dict[str, Any]:
    if code in {"dialogue", "clarify", "unsupported"}:
        return gold(code)
    if code.startswith("talk:"):
        return gold("dialogue", target_id=code[5:])
    if code.startswith("e:"):
        return gold("existing", action_id=code[2:])
    if code == "observe":
        return gold("interact", operation="observe", target_id="forest_slime")
    if code == "branches":
        return gold("interact", operation="observe", target_id="fallen_branches")
    if code in {"distract", "pass"}:
        return gold("interact", operation="distract", target_id="forest_slime", item_id="trail_ration", advance=code == "pass")
    if code == "sneak":
        return gold("interact", operation="sneak", target_id="forest_slime", advance=True)
    if code == "prepare":
        return gold("interact", operation="prepare", target_id="forest_slime", item_id="fallen_branches")
    if code == "heal":
        return gold("interact", operation="use_item", target_id="self", item_id="薬草")
    raise ValueError(code)


def assign_splits(rows: list[dict[str, Any]]) -> dict[str, str]:
    families: dict[str, Counter] = defaultdict(Counter)
    totals = Counter(r["primary_tag"] for r in rows)
    for row in rows:
        families[row["family"]][row["primary_tag"]] += 1
    counts: Counter = Counter()
    result = {}
    for family in sorted(families, key=lambda f: hashlib.sha256(f.encode()).hexdigest()):
        bucket = families[family]
        # Hash order plus stratified deficit minimization keeps cross-tag families intact.
        before = sum((counts[t] - .4 * totals[t]) ** 2 / totals[t] for t in bucket)
        after = sum((counts[t] + n - .4 * totals[t]) ** 2 / totals[t] for t, n in bucket.items())
        result[family] = "dev" if after < before else "test"
        if result[family] == "dev":
            counts.update(bucket)
    return result


def assemble() -> list[dict[str, Any]]:
    recipe_map = recipes()
    sessions = {k: build_snapshot(v) for k, v in recipe_map.items()}
    for recipe in recipe_map.values():
        (ROOT / "eval/snapshots" / (recipe["id"] + ".json")).write_text(
            json.dumps(recipe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = []
    tag = ""
    counts: Counter = Counter()
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            tag = line[1:]
            continue
        alias, codes, harm, family, rules, text = line.split("|", 5)
        counts[tag] += 1
        identifier = f"v2-{tag}-{counts[tag]:03d}"
        harmful: dict[str, list[str]] = {"operation": [], "kind": [], "action_id": []}
        session = sessions[alias]
        if harm == "cost":
            actions = json.loads(free_actions.build_plan_messages(session, "")[1]["content"])["actions"]
            harmful["action_id"] = [a["id"] for a in actions if costly_plan(session, answer("e:" + a["id"]))]
            harmful["operation"] = [op for op in ("distract", "sneak", "use_item")
                                    if costly_plan(session, answer({"use_item": "heal"}.get(op, op)))]
        elif harm == "all":
            harmful["kind"] = ["existing", "interact"]
        elif harm != "-":
            for feature in harm.split(","):
                key, value = feature.split(":", 1)
                harmful[{"op": "operation", "e": "action_id", "kind": "kind"}[key]].append(value)
        rows.append(dict(id=identifier, family=family if family != "-" else identifier,
                         snapshot=recipe_map[alias]["id"], input=text, tags=[tag], primary_tag=tag,
                         gold=[answer(code) for code in codes.split(",")], harmful=harmful,
                         gold_note=f"依据 LABELING.md 第 {rules} 条；答案按当前快照的对象、方法、可用物品拟定。",
                         label_status="proposed"))
    splits = assign_splits(rows)
    for row in rows:
        row["split"] = splits[row["family"]]
    OUTPUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return rows


def similarity_violations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grams = [{r["input"][i:i+3] for i in range(max(1, len(r["input"]) - 2))} for r in rows]
    result = []
    for i, left in enumerate(rows):
        for j in range(i):
            right = rows[j]
            score = len(grams[i] & grams[j]) / len(grams[i] | grams[j])
            if score > .6 and left["family"] != right["family"]:
                result.append(dict(left=left["id"], right=right["id"], similarity=score))
    return result


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(r["primary_tag"] for r in rows)
    errors = []
    if not 450 <= len(rows) <= 550:
        errors.append("case count outside 450..550")
    for tag in TAGS:
        if sum(tag in r["tags"] for r in rows) < 20:
            errors.append(f"tag {tag} has fewer than 20 rows")
    if len({r["id"] for r in rows}) != len(rows) or len({r["input"] for r in rows}) != len(rows):
        errors.append("duplicate id/input")
    splits = assign_splits(rows)
    sessions = {r["snapshot"]: None for r in rows}
    actors: Counter = Counter()
    scenes: Counter = Counter()
    matrix: dict[str, Counter] = defaultdict(Counter)
    contextual = set()
    from .run import engine_result
    for identifier in sessions:
        sessions[identifier] = load_snapshot(identifier)
    for row in rows:
        session = sessions[row["snapshot"]]
        actors[session["character"]["character_id"]] += 1
        scenes[session["world_state"]["scene_id"]] += 1
        matrix[row["snapshot"]].update(row["tags"])
        if session.get("messages"):
            contextual.add(row["snapshot"])
        if row["split"] != splits[row["family"]]:
            errors.append(f"{row['id']}: non-deterministic family split")
        if row["primary_tag"] not in row["tags"] or row["label_status"] != "proposed":
            errors.append(f"{row['id']}: metadata")
        if set(row["harmful"]) != {"operation", "kind", "action_id"} or not row["gold"]:
            errors.append(f"{row['id']}: gold/harmful schema")
        if "context_followup" in row["tags"] and not session.get("messages"):
            errors.append(f"{row['id']}: missing context")
        for g in row["gold"]:
            try:
                plan = free_actions.parse_plan(json.dumps({**g, "approach": "", "reply": ""}), session["character"]["character_id"])
                if engine_result(session, plan, row["input"])["outcome"] == "rejected":
                    errors.append(f"{row['id']}: rejected gold {g}")
            except free_actions.InvalidPlan as exc:
                errors.append(f"{row['id']}: {exc}")
    if len(sessions) < 20 or len(contextual) < 5 or not {"hero", "mage", "thief"} <= actors.keys() or len(scenes) < 4:
        errors.append("snapshot/actor/scene/context coverage")
    for identifier, tags in matrix.items():
        if sessions[identifier]["world_state"]["location_id"] == "dark_forest_loc" and sum(tags.values()) > len(rows) * .25:
            errors.append(f"{identifier}: exceeds 25%")
    violations = similarity_violations(rows)
    return dict(total=len(rows), errors=errors, violations=violations, violation_count=len(violations),
                snapshots=len(sessions), contextual_snapshots=len(contextual), primary_tags=dict(counts),
                actors=dict(actors), scenes=dict(scenes), split=dict(Counter(r["split"] for r in rows)),
                tag_split={t: dict(Counter(r["split"] for r in rows if r["primary_tag"] == t)) for t in TAGS},
                snapshot_tags={k: dict(v) for k, v in sorted(matrix.items())})


def distribution_markdown(rows: list[dict[str, Any]], result: dict[str, Any]) -> str:
    labels = {tag: f"T{i:02d}" for i, tag in enumerate(TAGS, 1)}
    lines = ["# intent_v2 候选分布（离线）", "",
             "由 `python -m scripts.eval.benchmark_v2 --assemble` 重建。标签尚未审定。",
             "输入句均保存在 intent_v2_authored.txt 中；组装器只展开标注，不生成或改写句子。", "",
             f"总数 {len(rows)}；快照 {result['snapshots']}；上下文快照 {result['contextual_snapshots']}；"
             f"字符 3-gram Jaccard > 0.6 的跨 family 违规 {result['violation_count']}。",
             f"句式家族 {len({r['family'] for r in rows})}；dev/test：{result['split']}。", "",
             "| 代号 | primary_tag | 数量 | dev | test |", "|---|---|---:|---:|---:|"]
    for tag in TAGS:
        counts = result["tag_split"][tag]
        lines.append(f"| {labels[tag]} | {tag} | {result['primary_tags'][tag]} | {counts.get('dev', 0)} | {counts.get('test', 0)} |")
    lines += ["", "标签一条一个；下表为完整快照 × 标签非零计数，未列出的组合均为 0。", "",
              "| 快照 | 职业 | 场景 | 数量 | dev | test | 标签：数量 |", "|---|---|---|---:|---:|---:|---|"]
    for identifier, tags in result["snapshot_tags"].items():
        recipe = json.loads((ROOT / "eval/snapshots" / f"{identifier}.json").read_text(encoding="utf-8"))
        session = load_snapshot(identifier)
        counts = Counter(r["split"] for r in rows if r["snapshot"] == identifier)
        text = ", ".join(f"{labels[t]}:{n}" for t, n in sorted(tags.items(), key=lambda pair: labels[pair[0]]))
        lines.append(f"| {identifier} | {recipe['character_id']} | {session['world_state']['scene_id']} | {sum(tags.values())} | {counts['dev']} | {counts['test']} | {text} |")
    for title, key in (("职业", "actors"), ("场景", "scenes"), ("split", "split")):
        lines += ["", f"| {title} | 数量 |", "|---|---:|"]
        lines += [f"| {name} | {count} |" for name, count in result[key].items()]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assemble", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "eval/candidates/intent_v2_audit.json")
    args = parser.parse_args()
    rows = assemble() if args.assemble else [json.loads(l) for l in OUTPUT.read_text(encoding="utf-8").splitlines()]
    result = audit(rows)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT.with_name("intent_v2_distribution.md").write_text(distribution_markdown(rows, result), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "snapshot_tags"}, ensure_ascii=False, indent=2))
    return int(bool(result["errors"] or result["violations"]))


if __name__ == "__main__":
    raise SystemExit(main())
