from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import time
from collections import Counter
from copy import deepcopy
from pathlib import Path
from statistics import mean, median
from typing import Any, Optional
from unittest.mock import patch

from host import combat, state
from .checkpoints import DEFAULT_CHECKPOINTS, DEFAULT_SCENARIO, ROOT, fresh_session

POLICIES = ("attack_only", "greedy", "heuristic")
MODES = ("flat", "floor", "ratio")
TARGETS = ROOT / "eval/balance/targets.json"
SKILL_CANDIDATES = ROOT / "eval/balance/skill_candidates.json"


def formula_mean(formula: str, actor: dict[str, Any]) -> float:
    total = 0.0
    for term in re.findall(r"[+-]?[^+-]+", combat._normalize_formula(formula) or "1"):
        sign = -1 if term.startswith("-") else 1
        term = term.lstrip("+-")
        dice = re.fullmatch(r"(\d*)d(\d+)", term)
        attr = re.fullmatch(r"([a-z_]+)(?:/(\d+))?", term)
        if dice:
            value = max(1, min(int(dice[1] or 1), 20)) * (max(2, int(dice[2])) + 1) / 2
        elif attr:
            key = combat._canonical_attr(attr[1])
            attrs = actor.get("attributes", {})
            value = int(attrs.get(key, attrs.get("con", 0) if key == "end" else 0)) // max(1, int(attr[2] or 1))
        else:
            value = int(float(term))
        total += sign * value
    return max(0.0, total)


def expected_damage(action: dict[str, Any], actor: dict[str, Any], enemy: dict[str, Any], rules: dict[str, Any]) -> float:
    if action.get("type") != "attack" and action.get("kind") not in {"attack", "damage"}:
        return 0.0
    raw = formula_mean(str(action.get("damage") or "1d4"), actor)
    chance = max(5, min(100, int(action.get("accuracy", 90)) - int(enemy.get("combat", {}).get("evade", 0)))) / 100
    elements = action.get("multi_elements") or [action.get("element", "physical")]
    damage = 0.0
    for element in elements:
        if element == "counter":
            element = combat.counter_attack_element(enemy)
        elif element == "weakness":
            element = combat.weakness_attack_element(enemy)
        multiplier = combat._resistance_multiplier(enemy, element)
        amount = combat.damage_after_defense(raw, multiplier, combat._actor_defense(enemy), rules)
        if combat._negative_undead(enemy) and element not in {"holy", "light"}:
            amount = -amount
        damage += amount * chance * int(action.get("hits_per_element", 1))
    for followup in action.get("followups", []):
        damage += expected_damage({**followup, "type": "attack"}, actor, enemy, rules)
    return damage


def rare_consumable(session: dict[str, Any], action: dict[str, Any]) -> bool:
    if action["type"] != "item":
        return False
    item = combat._find_entry(session["character"]["inventory"], action["id"], "item")
    spec = combat.item_combat_spec(item)
    if not spec.get("consumable", True):
        return False
    if item.get("rare") or {spec.get("element"), *spec.get("multi_elements", [])} & {"holy", "light"}:
        return True
    return any(expected_damage(action, session["character"], enemy, combat._combat_rules(session))
               >= abs(enemy["max_hp"]) * .30
               for enemy in combat._alive_enemies(session["combat"]))


def choose_action(session: dict[str, Any], policy: str, *, purify: bool = True,
                  reserve_purification: bool = False,
                  elite_holy_water: bool = True) -> tuple[dict[str, Any], str]:
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy: {policy}")
    actions = [a for a in combat.combat_actions(session) if a.get("enabled")]
    actor = session["character"]
    enemies = combat._alive_enemies(session["combat"])
    first_target = enemies[0]["id"]
    if policy == "attack_only":
        return next(a for a in actions if a["type"] == "attack"), first_target
    if session["combat"]["encounter"].get("encounter_class") in {"trash", "elite"}:
        allow_holy = (elite_holy_water
                      and session["combat"]["encounter"].get("encounter_class") == "elite"
                      and any(combat._resistance_multiplier(e, "holy") > 1 for e in enemies))
        actions = [a for a in actions if not rare_consumable(session, a)
                   or (allow_holy and a["type"] == "item" and a["id"] == "holy_water"
                       and a.get("quantity", 1) > 1)]
    if policy == "heuristic":
        specials = [a for a in actions if a["type"] == "special" and a.get("outcome") == "purified"]
        if purify and specials:
            return specials[0], first_target
        available = [a for a in session["combat"]["encounter"].get("special_actions", [])
                     if a.get("outcome") == "purified" and combat._special_action_available(
                         session, {**a, "enemy_hp_ratio_lte": 1})] if purify else []
        reserved_items = {a["cost_item"] for a in available if a.get("cost_item")}
        if reserve_purification:
            reserved_items.add("holy_water")
        actions = [a for a in actions if not (a["type"] == "item" and a["id"] in reserved_items
                                             and a.get("quantity", 1) <= 1)]
        if available and not reserved_items:
            reserve_mp = max((a.get("cost", 0) for a in available if a.get("cost_type") == "mp"), default=0)
            actions = [a for a in actions if a.get("cost_type") != "mp" or actor["mp"] - a.get("cost", 0) >= reserve_mp]
        catalog = {enemy["id"]: enemy for enemy in session["scenario_pack"].get("enemies", [])}
        # Save elemental consumables for the declared next phase's greater weakness.
        actions = [a for a in actions if not (a["type"] == "item" and a.get("kind") == "damage"
                   and combat.item_combat_spec(combat._find_entry(actor["inventory"], a["id"], "item")).get("consumable", True)
                   and any(e.get("next_phase") in catalog and
                           combat._resistance_multiplier(catalog[e["next_phase"]], a.get("element", "physical")) >
                           combat._resistance_multiplier(e, a.get("element", "physical")) for e in enemies))]
        healing = [a for a in actions if a.get("kind") == "heal"]
        if combat._equipped_effect(actor, "healing_harms_humans") and not actor.get("undead_parts"):
            healing = [a for a in healing if a["type"] == "item"]
        if actor["hp"] < actor["max_hp"] * .35 and healing:
            best = max(healing, key=lambda a: min(actor["max_hp"] - actor["hp"],
                int(actor["max_hp"] * a["max_hp_ratio"]) if "max_hp_ratio" in a
                else formula_mean(str(a.get("healing") or "10"), actor)))
            return best, first_target
        encounter = session["combat"]["encounter"]
        if encounter.get("boss") and session["combat"]["round"] <= 2:
            buffs = [a for a in actions if a["type"] == "skill" and a.get("kind") in {"defend", "stance"}]
            if buffs:
                return buffs[0], first_target
    attacks = [a for a in actions if a["type"] == "attack" or a.get("kind") in {"attack", "damage"}]
    rules = combat._combat_rules(session)
    candidates = [(a, e["id"], sum(expected_damage(a, actor, t, rules) for t in enemies)
                   if a.get("all_targets") else expected_damage(a, actor, e, rules))
                  for a in attacks for e in enemies]
    action, target, _ = max(candidates, key=lambda c: c[2])
    return action, target


def scale_actor(actor: dict[str, Any], scaling: dict[str, Any], pack: dict[str, Any]) -> None:
    hp_mult = float(scaling.get("hp_mult", 1))
    if not math.isfinite(hp_mult) or hp_mult <= 0:
        raise ValueError("hp_mult must be positive")
    actor["max_hp"] = max(1, round(actor["max_hp"] * hp_mult))
    for key, addition in scaling.get("attr_add", {}).items():
        if key not in actor["attributes"]:
            raise ValueError(f"Unknown actor attribute: {key}")
        actor["attributes"][key] += int(addition)
    skills = {s["id"]: s for c in pack["characters"] for s in c.get("skills", []) if "id" in s}
    skills.update({s["id"]: s for item in pack.get("items", [])
                   for s in item.get("combat", {}).get("grants_skills", []) if "id" in s})
    for skill_id in scaling.get("skill_unlocks", []):
        if skill_id not in skills:
            raise ValueError(f"Unknown skill_unlock: {skill_id}")
        if not any(s.get("id") == skill_id for s in actor["skills"]):
            actor["skills"].append(deepcopy(skills[skill_id]))
    for resource in ("hp", "mp", "sp"):
        actor[resource] = actor[f"max_{resource}"]


def prepare_session(pack: dict[str, Any], encounter: str, character_id: str,
                    checkpoints: Optional[dict[str, Any]] = None, *, defense_mode: str = "flat",
                    stat_scaling: Optional[dict[str, Any]] = None, companion: bool = True,
                    skill_variant: str = "none") -> dict[str, Any]:
    isolated = deepcopy(pack)
    location = next(l for l in isolated["locations"] if l["id"] == encounter)
    guest = location.get("combat", {}).get("player_character_id")
    actual_id = guest or character_id
    session = fresh_session(isolated, actual_id)
    if checkpoints is not None and not guest:
        entry = checkpoints["encounters"][encounter]["characters"][character_id]
        for key in ("inventory", "equipment", "gold"):
            session["character"][key] = deepcopy(entry[key])
        for key in ("level", "attributes", "max_hp", "max_mp", "max_sp"):
            if key in entry:
                session["character"][key] = deepcopy(entry[key])
        session["completed_milestones"] = deepcopy(entry.get("completed_milestones", []))
        session["companion"] = deepcopy(entry["companion"])
        state._merge_inventory_catalog(session["character"]["inventory"], pack)
        state._normalize_character(session["character"])
    if skill_variant not in {"none", "A"}:
        raise ValueError("Unknown skill variant")
    if skill_variant == "none" and not guest:
        state._unlock_level_skills(session)
    if skill_variant == "A" and not guest:
        for candidate in json.loads(SKILL_CANDIDATES.read_text(encoding="utf-8"))["candidates"]:
            if (candidate["variant"] == "A" and candidate["character"] == actual_id
                    and candidate["level"] <= session["character"].get("level", 1)):
                session["character"]["skills"].append(deepcopy(candidate["skill"]))
    if not companion:
        session["companion"] = None
    scale_actor(session["character"], stat_scaling or {}, isolated)
    if guest:
        # ensure_combat_started replaces the actor from the guest template.
        template = next(c for c in isolated["characters"] if c["id"] == guest)
        scale_actor(template, stat_scaling or {}, isolated)
    isolated["locations"] = [location]
    scene_id = location.get("scene_id") or encounter
    isolated["scenes"] = [{"id": scene_id, "location_ids": [encounter]}]
    location["scene_id"] = scene_id
    isolated["meta"]["initial_scene"] = scene_id
    isolated.setdefault("combat_rules", {})["defense_mode"] = defense_mode
    session["world_state"] = {"scene_id": scene_id, "location_id": encounter}
    session["combat_start_requested"] = True
    session["event_log"] = []
    return session


def trial_seed(seed: int, encounter: str, character: str, index: int) -> int:
    value = f"{seed}:{encounter}:{character}:{index}".encode()
    return int.from_bytes(hashlib.sha256(value).digest()[:8], "big")


def defeat_cause(session: dict[str, Any]) -> str:
    battle = session["combat"]
    if session.get("game_over"):
        event = next((e for e in reversed(battle["log"]) if e["kind"] == "game_over"), {})
        return str(event.get("actor", "system")) + ":" + str(session["game_over"].get("ending", "game_over"))
    if battle["round"] > combat._combat_rules(session)["max_rounds"]:
        return "max_rounds"
    for event in reversed(battle["log"]):
        if event["kind"] in {"damage", "field_damage", "self_damage", "undead_conversion"}:
            if event["actor"] not in {"player", "companion"} or event["kind"] == "self_damage":
                return event["actor"] + ":" + event["text"].split("が")[0]
    return "unknown"


def simulate(pack: dict[str, Any], encounter: str, character_id: str, policy: str = "heuristic", *,
             n: int = 500, seed: int = 20261011, checkpoints: Optional[dict[str, Any]] = None,
             defense_mode: str = "flat", stat_scaling: Optional[dict[str, Any]] = None,
             companion: bool = True, skill_variant: str = "none", preparation: str = "default",
             purify: bool = True, initial_delta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if n < 1:
        raise ValueError("n must be positive")
    template = prepare_session(pack, encounter, character_id, checkpoints, defense_mode=defense_mode,
                               stat_scaling=stat_scaling, companion=companion, skill_variant=skill_variant)
    if preparation != "default":
        if preparation not in {"standard", "no_fire", "purification"}:
            raise ValueError("Unknown preparation")
        actor = template["character"]
        def fire_capable(value: Any) -> bool:
            if isinstance(value, dict):
                return value.get("element") in {"fire", "counter", "weakness"} or "fire" in value.get("multi_elements", []) or any(fire_capable(v) for v in value.values())
            return isinstance(value, list) and any(fire_capable(v) for v in value)
        actor["skills"] = [s for s in actor["skills"] if not fire_capable(s)]
        actor["inventory"] = [i for i in actor["inventory"] if not fire_capable(i)]
        if preparation == "standard":
            core = next(i for i in pack["items"] if i["id"] == "red_dragon_core")
            actor["inventory"].append({**deepcopy(core), "quantity": 1})
        elif preparation == "purification":
            template["flags"].update(ignis_purified=True, ignis_ally=True)
        if fire_capable(template.get("companion")):
            template["companion"] = None
        state._synchronize_equipment(actor)
    if initial_delta:
        state.apply_state_delta(template, initial_delta)
    character_id = template["character"]["character_id"]
    shared_pack = template["scenario_pack"]
    rounds, hp_left = [], []
    losses: Counter = Counter()
    causes: Counter = Counter()
    healing_items: Counter = Counter()
    consumables: Counter = Counter()
    spent = {"mp": 0, "sp": 0}
    wins = 0
    outcomes: Counter = Counter()
    threshold_rounds, success_rounds = [], []
    phase_rounds: dict[str, list[int]] = {}
    rng = random.Random()
    with patch.object(combat, "random", rng):
        for index in range(n):
            rng.seed(trial_seed(seed, encounter, character_id, index))
            session = deepcopy(template, {id(shared_pack): shared_pack})
            if not combat.ensure_combat_started(session):
                raise ValueError(f"Encounter did not start: {encounter}")
            while combat.combat_is_active(session):
                action, target_id = choose_action(session, policy, purify=purify)
                resource = action.get("cost_type")
                if resource in spent:
                    spent[resource] += int(action.get("cost", 0))
                if action["type"] == "special" and action.get("cost_item"):
                    item = combat._find_entry(session["character"]["inventory"], action["cost_item"], "item")
                    consumables[item["name"]] += int(action.get("cost", 1))
                if action["type"] == "item":
                    item = combat._find_entry(session["character"]["inventory"], action["id"], "item")
                    if combat.item_combat_spec(item).get("consumable", True):
                        consumables[action["name"]] += 1
                        if action.get("kind") in {"heal", "restore"}:
                            healing_items[action["name"]] += 1
                action_round = session["combat"]["round"]
                combat.perform_combat_action(session, action["type"], action["id"], target_id, rng=rng)
                if encounter == "dragon_valley_loc" and 0 < combat._hp_ratio(session["combat"]["enemies"][0]) <= .4:
                    session["combat"].setdefault("threshold_round", action_round)
            battle = session["combat"]
            for identifier, duration in phase_durations(battle).items():
                phase_rounds.setdefault(identifier, []).append(duration)
            rounds.append(battle["round"])
            outcomes[battle["status"]] += 1
            if "threshold_round" in battle:
                threshold_rounds.append(battle["threshold_round"])
            if battle["status"] in {"victory", "purified"}:
                wins += 1
                success_rounds.append(battle["round"])
                hp_left.append(session["character"]["hp"] / session["character"]["max_hp"])
            else:
                losses[battle["round"]] += 1
                causes[f"{defeat_cause(session)} @ round {battle['round']}"] += 1
    return {"encounter": encounter, "encounter_class": shared_pack["locations"][0]["combat"]["encounter_class"],
            "character": character_id, "policy": policy, "defense_mode": defense_mode,
            "companion": companion, "n": n, "seed": seed, "stat_scaling": stat_scaling or {},
            "skill_variant": skill_variant, "level": template["character"].get("level", 1),
            "enemy_count": len(combat._encounter_for_session(template, shared_pack)["enemy_ids"]),
            "preparation": preparation, "phase_rounds_mean": {k: mean(v) for k, v in phase_rounds.items()},
            "purify": purify, "outcomes": dict(outcomes), "rounds_mean": mean(rounds),
            "success_rounds_mean": mean(success_rounds) if success_rounds else None,
            "threshold_reached": len(threshold_rounds),
            "threshold_rounds_mean": mean(threshold_rounds) if threshold_rounds else None,
            "phase_reached": {k: len(v) for k, v in phase_rounds.items()},
            "win_rate": wins / n, "rounds_median": median(rounds), "hp_left_mean": mean(hp_left) if hp_left else None,
            "healing_items_mean": {k: v / n for k, v in sorted(healing_items.items())},
            "consumables_mean": {k: v / n for k, v in sorted(consumables.items())},
            "mp_spent_mean": spent["mp"] / n, "sp_spent_mean": spent["sp"] / n,
            "defeat_rounds": dict(sorted(losses.items())), "defeat_causes": dict(causes.most_common())}


def phase_durations(battle: dict[str, Any]) -> dict[str, int]:
    transitions = battle.get("phase_transitions", [])
    start = 1
    result = {}
    for event in transitions:
        result[event["from"]] = event["round"] - start + 1
        start = event["round"]
    if battle["enemies"]:
        result[battle["enemies"][0]["template_id"]] = battle["round"] - start + 1
    return result


def check_results(rows: list[dict[str, Any]], targets: dict[str, Any], *,
                  check_resource_metrics: bool = False) -> list[dict[str, Any]]:
    violations = []
    groups: dict[tuple, list] = {}
    for row in rows:
        group = groups.setdefault((row["defense_mode"], row["encounter"]), [])
        group.append(row)
        spec = {**targets["classes"][row["encounter_class"]],
                **targets.get("encounter_overrides", {}).get(row["encounter"], {})}
        preparation = spec.get("preparations", {}).get(row.get("preparation"), {})
        spec.update(preparation)
        if "win_rate_lt" in spec and row["win_rate"] >= spec["win_rate_lt"]:
            violations.append(dict(encounter=row["encounter"], character=row["character"], metric="win_rate_lt",
                                   value=row["win_rate"], target=spec["win_rate_lt"]))
        if "win_rate_lt" in spec:
            spec.pop("win_rate", None)
        if row["policy"] == spec["policy"]:
            for key, field in (("win_rate", "win_rate"), ("hp_left", "hp_left_mean"), ("rounds", "rounds_median")):
                if key in spec and (key == "win_rate" or check_resource_metrics):
                    value = row[field]
                    if value is None or not spec[key][0] <= value <= spec[key][1]:
                        violations.append({"encounter": row["encounter"], "character": row["character"],
                                           "defense_mode": row["defense_mode"], "metric": key, "value": value, "target": spec[key]})
        elif row["policy"] == "attack_only" and "attack_only_win_rate_max" in spec:
            if row["win_rate"] > spec["attack_only_win_rate_max"]:
                violations.append({"encounter": row["encounter"], "character": row["character"],
                                   "defense_mode": row["defense_mode"], "metric": "attack_only_win_rate", "value": row["win_rate"],
                                   "target": [0, spec["attack_only_win_rate_max"]]})
    for (mode, encounter), group in groups.items():
        values = [r["win_rate"] for r in group if r["policy"] == "heuristic"]
        limit = targets.get("class_spread_max_multi_enemy", targets["class_spread_max"]) if group[0].get("enemy_count", 1) > 1 else targets["class_spread_max"]
        if values and max(values) - min(values) > limit + 1e-12:
            violations.append({"encounter": encounter, "character": "all", "defense_mode": mode,
                               "metric": "class_spread", "value": max(values) - min(values),
                               "target": [0, limit]})
    return violations


def selected_characters(pack: dict[str, Any], encounter: str, requested: list[str]) -> list[str]:
    location = next(l for l in pack["locations"] if l["id"] == encounter)
    guest = location["combat"].get("player_character_id")
    if guest:
        return [guest]
    selectable = [c["id"] for c in pack["characters"] if c.get("selectable", True)]
    if requested == ["all"]:
        return selectable
    if not set(requested) <= set(selectable):
        raise ValueError("Unknown or nonselectable character")
    return requested


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic offline combat balance simulation")
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--encounters", "--encounter", nargs="+", default=["all"])
    parser.add_argument("--characters", "--character", nargs="+", default=["all"])
    parser.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINTS), help="JSON path or none")
    parser.add_argument("--policies", "--policy", nargs="+", choices=[*POLICIES, "all"], default=["heuristic"])
    parser.add_argument("--n", "-N", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261011)
    parser.add_argument("--defense-mode", "--defense_mode", choices=MODES, default="flat")
    parser.add_argument("--stat-scaling", "--stat_scaling", default="{}", help="JSON object")
    parser.add_argument("--no-companion", action="store_true")
    parser.add_argument("--skills", choices=["none", "A"], default="none")
    parser.add_argument("--preparation", choices=["default", "standard", "no_fire", "purification"], default="default")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-resource-metrics", action="store_true",
                        help="Also enforce hp_left and rounds (report-only by default)")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    pack = state.load_scenario_pack(args.scenario)
    checkpoints = None if args.checkpoint == "none" else json.loads(Path(args.checkpoint).read_text(encoding="utf-8"))
    targets = json.loads(TARGETS.read_text(encoding="utf-8"))
    encounters = list(targets["encounters"]) if args.encounters == ["all"] else args.encounters
    policies = list(POLICIES) if "all" in args.policies else args.policies
    if args.check:
        policies = list(dict.fromkeys([*policies, "heuristic", "attack_only"]))
    started = time.perf_counter()
    rows = [simulate(pack, encounter, character, policy, n=args.n, seed=args.seed, checkpoints=checkpoints,
                     defense_mode=args.defense_mode, stat_scaling=json.loads(args.stat_scaling), companion=not args.no_companion,
                     skill_variant=args.skills, preparation=args.preparation)
            for encounter in encounters for character in selected_characters(pack, encounter, args.characters) for policy in policies]
    result = {"rows": rows, "elapsed_seconds": time.perf_counter() - started}
    if args.check:
        result["violations"] = check_results(rows, targets, check_resource_metrics=args.check_resource_metrics)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if result.get("violations") else 0


if __name__ == "__main__":
    raise SystemExit(main())
