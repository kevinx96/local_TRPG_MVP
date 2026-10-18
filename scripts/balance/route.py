from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any, Optional
from unittest.mock import patch

from host import combat, state
from . import checkpoints, sim

REST_ACTIONS = {"inn": ("rest_at_inn", 10), "village": ("rest_at_refuge", 5),
                "elf_spring": ("rest_at_elf_spring", 0), "cave_hot_spring": ("rest_hot_spring", 0)}


def rest_if_needed(session: dict[str, Any]) -> Optional[dict[str, Any]]:
    location = state.current_location_id(session)
    if location not in REST_ACTIONS:
        return None
    identifier, cost = REST_ACTIONS[location]
    actor = session["character"]
    if actor["hp"] * 10 >= actor["max_hp"] * 7 or actor.get("gold", 0) < cost:
        return None
    action = state.resolve_action(session, action_id=identifier)
    if action is None or not state.action_requirement_status(action, session)[0]:
        return None
    before = resources(session)
    checkpoints.replay_step(session, identifier)
    return dict(location=location, action=identifier, cost=cost, before=before, after=resources(session))


def resources(session: dict[str, Any]) -> dict[str, Any]:
    actor = session["character"]
    return {**{r: actor[r] for r in ("hp", "mp", "sp")}, "level": actor.get("level", 1),
            "inventory": {i["name"]: i.get("quantity", 1) for i in actor["inventory"]}}


def fight(session: dict[str, Any], policy: str, rng: random.Random, *, purify: bool = False) -> dict[str, Any]:
    location = state.current_location_id(session)
    before = resources(session)
    session["combat_start_requested"] = True
    if not combat.ensure_combat_started(session):
        raise ValueError(f"Route encounter did not start: {location}")
    used: Counter = Counter()
    while combat.combat_is_active(session):
        action, target = sim.choose_action(session, policy, purify=purify,
                                          reserve_purification=purify and not session.get("flags", {}).get("ignis_purified"))
        if action["type"] == "special" and action.get("cost_item"):
            item = combat._find_entry(session["character"]["inventory"], action["cost_item"], "item")
            used[item["name"]] += int(action.get("cost", 1))
        if action["type"] == "item":
            item = combat._find_entry(session["character"]["inventory"], action["id"], "item")
            if combat.item_combat_spec(item).get("consumable", True):
                used[action["name"]] += 1
        combat.perform_combat_action(session, action["type"], action["id"], target, rng=rng)
    battle = session["combat"]
    status = battle["status"]
    continuing = status in {"victory", "purified"} or battle["encounter"].get("encounter_class") == "scripted_loss"
    after_combat = resources(session)
    state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
    combat.clear_combat_after_resolution(session)
    return {"encounter": location, "status": status,
            "continue": continuing and (status in {"victory", "purified"} or not session.get("game_over")),
            "before": before, "after_combat": after_combat, "after_resolution": resources(session),
            "consumables": dict(used)}


def trial(pack: dict[str, Any], sources: list[dict[str, Any]], encounter: str, character: str,
          seed: int, policy: str = "heuristic", rest_at_inn: bool = False, purify: bool = False,
          rest_policy: str = "none") -> dict[str, Any]:
    if rest_policy not in {"none", "hp70"}:
        raise ValueError("unknown rest policy")
    session = checkpoints.fresh_session(pack, character)
    rng = random.Random(seed)
    battles = []
    arrival = None
    paid_rests = 0
    rests = []
    with patch.object(combat, "random", rng):
        for source in [*sources, {"location": encounter, "step": "@final"}]:
            if state.current_location_id(session) != source["location"]:
                raise ValueError(f"Route diverged before {source['step']}")
            actor = session["character"]
            if rest_policy == "hp70" and source["step"] not in {a for a, _ in REST_ACTIONS.values()}:
                while rest := rest_if_needed(session):
                    rests.append(rest)
                    paid_rests += int(rest["cost"] > 0)
                    # The spring's first rest triggers the authored slime ambush chain.
                    while state.current_location_id(session) != source["location"]:
                        battle = fight(session, policy, rng, purify=purify)
                        battles.append(battle)
                        if not battle["continue"]:
                            return dict(completed=False, failed_at=battle["encounter"], boss_arrival=arrival,
                                        battles=battles, paid_rests=paid_rests, rests=rests)
            if (rest_at_inn and source["location"] == "inn" and source["step"] != "rest_at_inn"
                    and actor.get("gold", 0) >= 10
                    and any(actor[r] < actor[f"max_{r}"] for r in ("hp", "mp", "sp"))):
                checkpoints.replay_step(session, "rest_at_inn")
                paid_rests += 1
            if source["step"].startswith("@") and source["step"] not in {"@recover_hp", "@opening"}:
                if source["step"] == "@final" and combat._encounter_for_session(
                        session, pack).get("encounter_class") == "boss":
                    arrival = resources(session)
                battle = fight(session, policy, rng, purify=True) if purify else fight(session, policy, rng)
                battles.append(battle)
                if not battle["continue"] or (purify and battle["encounter"] == "dragon_valley_loc" and battle["status"] != "purified"):
                    return {"completed": False, "failed_at": battle["encounter"],
                            "boss_arrival": arrival, "battles": battles, "paid_rests": paid_rests, "rests": rests}
            else:
                if source["step"].split(":", 1)[0] == "cross_lava_bridge":
                    action = state.resolve_action(session, action_id="cross_lava_bridge")
                    dice, dc = state.action_dice_settings(action, session=session)
                    roll = state.roll_dice(session, dice, dc, client_rolls=[rng.randint(1, 20)])
                    state.apply_action_result(session, action, roll)
                else:
                    checkpoints.replay_step(session, source["step"])
                if source["step"] in {"rest_at_refuge", "rest_at_inn"}:
                    paid_rests += 1
    ending = (session.get("game_over") or {}).get("ending")
    completed = not purify or ending == "draco_defeated_with_ignis"
    return {"completed": completed, "failed_at": None if completed else encounter,
            "boss_arrival": arrival, "battles": battles, "paid_rests": paid_rests, "ending": ending, "rests": rests}


def simulate_route(pack: dict[str, Any], cp: dict[str, Any], character: str, *,
                   encounter: str = "dragon_valley_loc", n: int = 500,
                   seed: int = 20261011, policy: str = "heuristic", rest_at_inn: bool = False,
                   purify: bool = False, rest_policy: str = "none",
                   quests: Optional[tuple[str, ...]] = None, decisions: str = "class_aware",
                   dice: str = "real") -> dict[str, Any]:
    if n < 1:
        raise ValueError("n must be positive")
    aware = None
    if rest_policy == "class_aware":
        # 027: hp70 rests plus option choice by expected outcome; quests from the pilot file by default.
        from . import class_aware

        if encounter != "dragon_valley_loc" or purify or rest_at_inn:
            raise ValueError("class_aware covers the plain mainline only")
        if quests is None:
            quests = tuple(class_aware.load_quests().get(character, ()))
        aware = dict(quests=tuple(quests), decisions=decisions, dice=dice, policy=policy,
                     evaluator=class_aware.Evaluator(quests, policy=policy) if decisions == "class_aware" else None)
    sources = cp["encounters"][encounter]["characters"][character]["sources"]
    if rest_policy == "hp70":
        sources = list(sources)
        for index, source in enumerate(sources):
            if source["location"] == "village_frozen_clue":
                if source["step"] != "visit_village":
                    sources[index:index] = [dict(location="village_frozen_clue", step="visit_village"),
                                            dict(location="village", step="return_frozen_clue")]
                break
    if purify:
        if encounter != "draco_battle":
            raise ValueError("Purification route ends at draco_battle")
        original_sources = sources
        sources = []
        for source in original_sources:
            if source["location"] == "ignis_last_breath":
                if source["step"] == "examine_ignis_wound":
                    sources.extend(dict(location="ignis_purified", step=step) for step in
                                   ("hear_ignis_testimony", "receive_ignis_scale", "ask_ignis_aid"))
                else:
                    sources.append({**source, "location": "ignis_purified"})
            else:
                sources.append(source)
    failures: Counter = Counter()
    endings: Counter = Counter()
    reached: Counter = Counter()
    used: dict[str, Counter] = {}
    arrivals = []
    completed = 0
    rest_counts: Counter = Counter()
    rest_gold = 0
    sample = None
    results = []
    for index in range(n):
        trial_seed = sim.trial_seed(seed, encounter, character, index)
        if aware is not None:
            result = class_aware.trial(pack, cp, character, trial_seed, **aware)
            results.append(result)
        else:
            result = trial(pack, sources, encounter, character, trial_seed, policy, rest_at_inn, purify, rest_policy)
        for rest in result["rests"]:
            rest_counts[rest["action"]] += 1
            rest_gold += rest["cost"]
        sample = sample or result
        completed += result["completed"]
        if result.get("ending"):
            endings[result["ending"]] += 1
        if result["failed_at"]:
            failures[result["failed_at"]] += 1
        if result["boss_arrival"] is not None:
            arrivals.append(result["boss_arrival"])
        for battle in result["battles"]:
            key = battle["encounter"]
            reached[key] += 1
            used.setdefault(key, Counter()).update(battle["consumables"])
    items = sorted({k for a in arrivals for k in a["inventory"]})
    return {"character": character, "route": "purification_true_ending" if purify else encounter, "policy": policy, "n": n, "seed": seed,
            "rest_at_inn": rest_at_inn,
            "rest_policy": rest_policy, "rest_counts": dict(rest_counts), "rest_gold": rest_gold,
            "completion_rate": completed / n, "failure_counts": dict(failures),
            "ending_counts": dict(endings),
            "boss_arrivals": len(arrivals),
            "boss_resources_mean": {**{r: mean(a[r] for a in arrivals) for r in ("hp", "mp", "sp", "level")},
                                    "inventory": {k: mean(a["inventory"].get(k, 0) for a in arrivals) for k in items}}
            if arrivals else None,
            "battle_reached": dict(reached),
            "consumables_per_reached_battle": {e: {k: v / reached[e] for k, v in counts.items()}
                                               for e, counts in used.items()},
            **({"quests": list(aware["quests"]), "decisions": aware["decisions"], "dice": aware["dice"],
                "choice_stats": class_aware.choice_stats(results)} if aware is not None else {}),
            "sample_trial": sample}


def check_results(rows: list[dict[str, Any]], targets: dict[str, Any], *,
                  target_key: str = "route_targets") -> list[dict[str, Any]]:
    violations = []
    for endpoint, spec in targets[target_key]["routes"].items():
        group = [r for r in rows if r["route"] == endpoint and r["policy"] == spec["policy"]]
        for character in targets[target_key]["characters"]:
            matched = [r for r in group if r["character"] == character]
            if len(matched) != 1:
                violations.append(dict(route=endpoint, character=character, metric="missing_or_duplicate",
                                       value=len(matched), target=[1, 1]))
                continue
            value = matched[0]["completion_rate"]
            if not spec["completion_rate"][0] <= value <= spec["completion_rate"][1]:
                violations.append(dict(route=endpoint, character=character, metric="completion_rate",
                                       value=value, target=spec["completion_rate"]))
        values = [r["completion_rate"] for r in group]
        limit = targets[target_key]["class_spread_max"]
        if values and max(values) - min(values) > limit + 1e-12:
            violations.append(dict(route=endpoint, character="all", metric="class_spread",
                                   value=max(values) - min(values), target=[0, limit]))
    return violations


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Offline continuous checkpoint routes; no implicit refill")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261011)
    parser.add_argument("--routes", nargs="+", default=["dragon_valley_loc"])
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--targets", type=Path, default=sim.TARGETS)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--rest-at-inn", action="store_true", help="Pay 10G to recover when the route visits the inn")
    parser.add_argument("--rest-policy", choices=("none", "hp70", "class_aware", "both", "all"), default="both",
                        help="Rest below 70%% HP at available stops; check hp70 and report no-rest as reference. "
                             "class_aware adds option choice by expected outcome on top of hp70; all = none/hp70/class_aware")
    parser.add_argument("--purify", action="store_true", help="Reserve holy water and take purification to the true ending")
    args = parser.parse_args(argv)
    if args.n < 1 or args.shards < 1 or not 0 <= args.shard < args.shards:
        parser.error("invalid n or shard")
    if args.check and args.shards != 1:
        parser.error("--check requires an unsharded result")
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    routes = list(targets["route_targets"]["routes"]) if args.check else (
        list(cp["encounters"]) if args.routes == ["all"] else args.routes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    fingerprints = {p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (checkpoints.DEFAULT_SCENARIO, checkpoints.DEFAULT_CHECKPOINTS, Path(__file__),
                              Path(__file__).with_name("class_aware.py"), checkpoints.ROOT / "eval/balance/class_aware_quests.json")
                    if p.exists()}
    fingerprints[str(args.targets)] = hashlib.sha256(args.targets.read_bytes()).hexdigest()
    for endpoint in routes:
        for index, character in enumerate(cp["encounters"][endpoint]["characters"]):
            if index % args.shards != args.shard:
                continue
            policy = targets.get("route_targets", {}).get("routes", {}).get(endpoint, {}).get("policy", "heuristic")
            policies = {"both": ("none", "hp70"), "all": ("none", "hp70", "class_aware")}.get(
                args.rest_policy, (args.rest_policy,))
            if endpoint != "dragon_valley_loc" or args.purify or args.rest_at_inn:
                policies = tuple(p for p in policies if p != "class_aware")
            for rest_policy in policies:
                rows.append(simulate_route(pack, cp, character, encounter=endpoint, n=args.n, seed=args.seed,
                                           policy=policy, rest_at_inn=args.rest_at_inn, purify=args.purify,
                                           rest_policy=rest_policy))
                rows[-1]["rest_policy"] = rest_policy
                print(f"{endpoint} {character} {rest_policy}: {rows[-1]['completion_rate']:.3f}", flush=True)
                args.output.write_text(json.dumps({"rows": rows, "fingerprints": fingerprints}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"rows": rows, "fingerprints": fingerprints}
    if args.check:
        checked = [r for r in rows if r["rest_policy"] == "hp70"]
        result["violations"] = check_results(checked, targets) if checked else []
        print(f"route violations: {len(result['violations'])}")
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(bool(result.get("violations")))


if __name__ == "__main__":
    raise SystemExit(main())
