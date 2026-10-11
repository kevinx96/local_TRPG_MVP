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
          seed: int, policy: str = "heuristic", rest_at_inn: bool = False, purify: bool = False) -> dict[str, Any]:
    session = checkpoints.fresh_session(pack, character)
    rng = random.Random(seed)
    battles = []
    arrival = None
    paid_rests = 0
    with patch.object(combat, "random", rng):
        for source in [*sources, {"location": encounter, "step": "@final"}]:
            if state.current_location_id(session) != source["location"]:
                raise ValueError(f"Route diverged before {source['step']}")
            actor = session["character"]
            if (rest_at_inn and source["location"] == "inn" and source["step"] != "rest_at_inn"
                    and actor.get("gold", 0) >= 10
                    and any(actor[r] < actor[f"max_{r}"] for r in ("hp", "mp", "sp"))):
                checkpoints.replay_step(session, "rest_at_inn")
                paid_rests += 1
            if source["step"].startswith("@"):
                if source["step"] == "@final" and combat._encounter_for_session(
                        session, pack).get("encounter_class") == "boss":
                    arrival = resources(session)
                battle = fight(session, policy, rng, purify=True) if purify else fight(session, policy, rng)
                battles.append(battle)
                if not battle["continue"] or (purify and battle["encounter"] == "dragon_valley_loc" and battle["status"] != "purified"):
                    return {"completed": False, "failed_at": battle["encounter"],
                            "boss_arrival": arrival, "battles": battles, "paid_rests": paid_rests}
            else:
                checkpoints.replay_step(session, source["step"])
    ending = (session.get("game_over") or {}).get("ending")
    completed = not purify or ending == "draco_defeated_with_ignis"
    return {"completed": completed, "failed_at": None if completed else encounter,
            "boss_arrival": arrival, "battles": battles, "paid_rests": paid_rests, "ending": ending}


def simulate_route(pack: dict[str, Any], cp: dict[str, Any], character: str, *,
                   encounter: str = "dragon_valley_loc", n: int = 500,
                   seed: int = 20261011, policy: str = "heuristic", rest_at_inn: bool = False,
                   purify: bool = False) -> dict[str, Any]:
    if n < 1:
        raise ValueError("n must be positive")
    sources = cp["encounters"][encounter]["characters"][character]["sources"]
    if purify:
        if encounter != "draco_battle":
            raise ValueError("Purification route ends at draco_battle")
        sources = []
        for source in cp["encounters"][encounter]["characters"][character]["sources"]:
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
    sample = None
    for index in range(n):
        result = trial(pack, sources, encounter, character,
                       sim.trial_seed(seed, encounter, character, index), policy, rest_at_inn, purify)
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
            "completion_rate": completed / n, "failure_counts": dict(failures),
            "ending_counts": dict(endings),
            "boss_arrivals": len(arrivals),
            "boss_resources_mean": {**{r: mean(a[r] for a in arrivals) for r in ("hp", "mp", "sp", "level")},
                                    "inventory": {k: mean(a["inventory"].get(k, 0) for a in arrivals) for k in items}}
            if arrivals else None,
            "battle_reached": dict(reached),
            "consumables_per_reached_battle": {e: {k: v / reached[e] for k, v in counts.items()}
                                               for e, counts in used.items()},
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
                    for p in (checkpoints.DEFAULT_SCENARIO, checkpoints.DEFAULT_CHECKPOINTS, Path(__file__))}
    fingerprints[str(args.targets)] = hashlib.sha256(args.targets.read_bytes()).hexdigest()
    for endpoint in routes:
        for index, character in enumerate(cp["encounters"][endpoint]["characters"]):
            if index % args.shards != args.shard:
                continue
            policy = targets.get("route_targets", {}).get("routes", {}).get(endpoint, {}).get("policy", "heuristic")
            rows.append(simulate_route(pack, cp, character, encounter=endpoint, n=args.n, seed=args.seed,
                                       policy=policy, rest_at_inn=args.rest_at_inn, purify=args.purify))
            print(f"{endpoint} {character}: {rows[-1]['completion_rate']:.3f}", flush=True)
            args.output.write_text(json.dumps({"rows": rows, "fingerprints": fingerprints}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"rows": rows, "fingerprints": fingerprints}
    if args.check:
        result["violations"] = check_results(rows, targets)
        print(f"route violations: {len(result['violations'])}")
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(bool(result.get("violations")))


if __name__ == "__main__":
    raise SystemExit(main())
