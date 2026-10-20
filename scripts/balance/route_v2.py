from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
import uuid
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from statistics import mean, median
from typing import Any, Optional
from unittest.mock import patch

from host import combat, state
from host.shops import trade
from . import budget, checkpoints, class_aware, sim
from .archetypes import (ARCHETYPES, CHARACTERS, COMPLETION_TITLE, IGNIS_FLAGS,
                         MAINLINE_NODES, TERMINAL_LOCATION, Archetype,
                         LevelModel, MilestoneLevelModel, PassivePicker)

DEFAULT_OUTPUT = checkpoints.ROOT / "eval/reports/046-measurement-v2-baseline.json"
BERSERKER = checkpoints.ROOT / "eval/balance/checkpoints_berserker.json"
SUPPORTED_ARCHETYPES = ("P0a", "P0b")


def resources(session: dict[str, Any]) -> dict[str, Any]:
    actor = session["character"]
    healing = 0.0
    for item in actor["inventory"]:
        spec = combat.item_combat_spec(item)
        if spec.get("kind") == "heal" and spec.get("consumable", True):
            amount = actor["max_hp"] * spec["max_hp_ratio"] if "max_hp_ratio" in spec else sim.formula_mean(str(spec.get("healing") or "10"), actor)
            healing += amount * item.get("quantity", 1)
    return {**class_aware.resources(session), "max_hp": actor["max_hp"], "gold": actor.get("gold", 0),
            "healing_hp": healing, "equipment": list(actor.get("equipment", []))}


def sustain(session: dict[str, Any]) -> float:
    """Uncapped, repeatable companion healing per round; overheal is not removed."""
    companion = session.get("companion") or {}
    if companion.get("id") in session["combat"]["encounter"].get("disable_companion_healing", []):
        return 0.0
    total = 0.0
    for effect in companion.get("round_start_effects", []):
        if effect.get("kind") != "heal_player" or not state._session_requirement_passes(effect.get("requirements"), session):
            continue
        amount = math.floor(session["character"]["max_hp"] * effect["max_hp_ratio"] + .5) if "max_hp_ratio" in effect else sim.formula_mean(str(effect.get("amount", "0")), session["character"])
        total += amount / max(1, int(effect.get("every_n_rounds", 1)))
    return total


def fight(session: dict[str, Any], policy: str, rng: random.Random, *, purify: bool = False,
          recovery_threshold: float = .30) -> dict[str, Any]:
    location, before = state.current_location_id(session), resources(session)
    session["combat_start_requested"] = True
    if not combat.ensure_combat_started(session):
        raise ValueError(f"Encounter did not start: {location}")
    opening = budget.phase_moments(session)
    expected_healing = sustain(session)
    actions, action_specs, consumables = Counter(), {}, Counter()
    expected_loss = 0.0
    phase_count = 0
    original_phase = combat._enemy_phase

    def measured_phase(current, source_rng):
        nonlocal expected_loss, phase_count
        expected_loss += budget.phase_moments(current)["expected_damage"]
        phase_count += 1
        return original_phase(current, source_rng)

    with patch.object(combat, "_enemy_phase", measured_phase):
        while combat.combat_is_active(session):
            action, target = sim.choose_action(session, policy, purify=purify, reserve_purification=purify,
                                               recovery_threshold=recovery_threshold)
            key = f"{action['type']}:{action['id']}"
            actions[key] += 1
            free = int(action.get("cost", 0)) == 0
            if action["type"] == "item":
                item = combat._find_entry(session["character"]["inventory"], action["id"], "item")
                consumed = combat.item_combat_spec(item).get("consumable", True)
                free = free and not consumed
                if consumed:
                    consumables[item["name"]] += 1
            action_specs[key] = {"type": action["type"], "id": action["id"], "free": free,
                                 "kind": action.get("kind", "attack")}
            combat.perform_combat_action(session, action["type"], action["id"], target, rng=rng)
    battle = session["combat"]
    status, rounds = battle["status"], battle["round"]
    summary = {"encounter": location, "encounter_class": battle["encounter"].get("encounter_class"),
               "status": status, "rounds": rounds, "policy": policy, "before": before,
               "after_combat": resources(session), "actions": dict(actions), "action_specs": action_specs,
               "consumables": dict(consumables), "opening": opening, "expected_healing": expected_healing,
               "expected_hp_loss": expected_loss, "enemy_phases": phase_count,
               "companion": (session.get("companion") or {}).get("id"),
               "statuses": [], "skill_usage": {}}
    state.apply_state_delta(session, combat.consume_combat_state_delta(session), allow_world_transition=True)
    combat.clear_combat_after_resolution(session)
    summary["after_resolution"] = resources(session)
    summary["continue"] = (status in {"victory", "purified"} or
        summary["encounter_class"] == "scripted_loss") and not session.get("game_over") and session["character"]["hp"] > 0
    if (session.get("game_over") or {}).get("title") == COMPLETION_TITLE:
        summary["continue"] = True
    return summary


class MeasurementRun(class_aware.Run):
    """Run's authored mainline/fort/cave macros, with observable deterministic engine calls."""

    def __init__(self, pack: dict[str, Any], character: str, seed: int, archetype: Archetype,
                 *, level_model: Optional[LevelModel] = None):
        if archetype.id not in SUPPORTED_ARCHETYPES:
            raise ValueError("046 reproduction gate must pass before implementing other archetypes")
        super().__init__(pack, [], character, seed, quests=archetype.sidequests, decisions="class_aware",
                         policy=archetype.combat_policy, rest_policy="none",
                         evaluator=object())
        self.archetype = archetype
        self.level_model = level_model or MilestoneLevelModel()
        self.passive_picker = PassivePicker(archetype.passive_mode)
        self.levels: dict[str, int] = {}
        self.steps: list[dict[str, Any]] = []
        self.boss_arrivals: dict[str, Any] = {}
        self.optional_count = self.spring_rests = 0
        self.equipment_changes = 0
        self.initial_equipment = list(self.session["character"].get("equipment", []))
        self.seen_equipment = {i["name"] for i in self.session["character"]["inventory"]}
        self.record_node()

    def record_node(self) -> None:
        if self.location in MAINLINE_NODES and self.location not in self.levels:
            self.levels[self.location] = self.level_model.observe(self.session, self.location)

    def settle(self) -> None:
        while class_aware.combat_pending(self.session):
            encounter = combat._encounter_for_session(self.session, self.session["scenario_pack"])
            if encounter.get("encounter_class") == "boss":
                self.boss_arrivals.setdefault(self.location, resources(self.session))
            battle = fight(self.session, self.policy, self.rng, purify="purification" in self.quests,
                           recovery_threshold=self.archetype.recovery_threshold)
            self.battles.append(battle)
            self.equip_acquired()
            self.record_node()
            if not battle["continue"]:
                raise class_aware.Defeat(battle["encounter"])

    def equip_acquired(self) -> None:
        actor = self.session["character"]
        if self.archetype.equipment_rule == "initial":
            actor["equipment"] = [name for name in self.initial_equipment if any(i["name"] == name for i in actor["inventory"])]
            state._synchronize_equipment(actor)
            return
        for item in list(actor["inventory"]):
            if item.get("slot") and item["name"] not in self.seen_equipment:
                # Acquisition order is the explicit P0 rule; no optimisation against hidden foes.
                try:
                    state._equip_inventory_item(self.session, item.get("id") or item["name"])
                except ValueError:
                    continue
        self.seen_equipment.update(i["name"] for i in actor["inventory"])

    def act(self, action_id: str, *, settle: bool = True) -> None:
        before = resources(self.session)
        source = self.location
        action = class_aware.act(self.session, action_id, self.rng)
        self.equip_acquired()
        after = resources(self.session)
        self.equipment_changes += before["equipment"] != after["equipment"]
        self.steps.append({"location": source, "action": action_id, "before": before, "after": after,
                           "crucial": bool(action.get("roll", {}).get("crucial"))})
        self.record_node()
        if settle:
            self.settle()

    def try_act(self, action: str) -> bool:
        if action in class_aware.available_actions(self.session):
            self.act(action)
            return True
        return False

    def decide(self, node: str) -> None:
        preferences = {
            "lost_goblin_crossroads": ("crossroads_forward", "ignore_lost_goblin"),
            "forest_wolves": ("fight_forest_wolves",),
            "village_approach": ("approach_burning_village_carefully", "enter_burning_village_directly"),
            "burning_house": ("leave_burning_house",),
            "ice_elemental_encounter": ("fight_ice_elemental",),
            "valley_entrance": ("fight_ash_wraiths",),
            "valley_lava_bridge": ("cross_lava_bridge", "take_ledge_path"),
        }
        for _ in range(class_aware.MAX_NODE_DECISIONS):
            if self.location != node:
                return
            available = class_aware.available_actions(self.session)
            choices = [a for a in preferences[node] if a in available]
            if not choices:
                raise ValueError(f"No v2 option at {node}")
            action = choices[0]
            self.choices.append({"node": node, "option": action})
            self.act(action)
        fallback = class_aware.GIVE_UP.get(node)
        if self.location == node and fallback:
            self.act(fallback)
        elif self.location == node:
            raise ValueError(f"Unresolved v2 node: {node}")

    def rest_point(self) -> None:
        if self.location != "elf_spring" or self.archetype.rest_rule == "none":
            return
        while self.spring_rests < 3:
            before = resources(self.session)
            self.spring_rests += 1
            self.act("rest_at_elf_spring")
            self.rests.append({"location": "elf_spring", "action": "rest_at_elf_spring", "cost": 0,
                               "before": before, "after": resources(self.session)})

    def buy(self, shop: str, item: str) -> bool:
        try:
            trade(self.session, shop, item, 1)
        except ValueError:
            return False
        self.equip_acquired()
        return True

    def play(self) -> None:
        checkpoints.replay_step(self.session, "@opening")
        if "ask_king_info" in self.archetype.optional_interactions:
            self.act("ask_king_info")
            self.optional_count += 1
        self.act("go_castle_town")
        if self.archetype.shopping_rule != "none":
            self.act("go_item_shop")
            self.optional_count += int(self.buy("sarah_shop", "ice_charm"))
            if self.archetype.companion_rule == "fire_bat_dragon":
                self.act("borrow_fire_bat_dragon")
                self.optional_count += 1
            self.act("return_castle_from_item_shop")
        # Reuse the existing continuous route; the prelude has already run.
        self.run_mainline()

    def run_mainline(self) -> None:
        # Run.play's final fight uses route.fight; the overridden act/settle records it here instead.
        self.act("go_dark_forest")
        self.act("attack_slime")
        self.decide("lost_goblin_crossroads")
        self.rest_point()
        self.act("continue_from_elf_spring")
        self.decide("forest_wolves")
        self.act("leave_forest_for_village")
        self.decide("village_approach")
        self.decide("burning_house")
        self.act("visit_village")
        self.act("return_frozen_clue")
        self.act("investigate_frozen_village")
        self.decide("ice_elemental_encounter")
        self.act("accept_ian_request")
        self.decide("valley_entrance")
        self.decide("valley_lava_bridge")
        if self.location == "warlock_at_nest":
            self.act("continue_after_warlock")
        self.act("enter_dragon_nest")
        if self.location == "ignis_purified":
            for action in ("hear_ignis_testimony", "receive_ignis_scale", "ask_ignis_aid"):
                self.try_act(action)
        self.act("return_to_castle_report")
        self.act("enter_festival_town")
        self.act("go_report_hall")
        # Ordinary players do not automatically expose Draco just because a clue exists.
        self.act("report_normally")

    def result(self, failed_at: Optional[str]) -> dict[str, Any]:
        ending = self.session.get("game_over") or {}
        final = resources(self.session)
        return {"archetype": self.archetype.id, "character": self.session["character"]["character_id"],
                "completed": ending.get("title") == COMPLETION_TITLE,
                "ignis_defeated": any(self.session["flags"].get(flag) for flag in IGNIS_FLAGS),
                "reached_terminal": TERMINAL_LOCATION in self.levels or ending.get("title") == COMPLETION_TITLE,
                "ending": ending.get("ending"), "failed_at": failed_at,
                "battles": self.battles, "boss_arrivals": self.boss_arrivals,
                "levels": self.levels, "rests": self.rests, "choices": self.choices,
                "optional_interactions": self.optional_count, "equipment_changes": self.equipment_changes,
                "passives": self.passive_picker.pick([]), "final": final,
                "grinding": None}


def trial(pack: dict[str, Any], character: str, seed: int, archetype: Archetype) -> dict[str, Any]:
    run = MeasurementRun(pack, character, seed, archetype)
    failed = None
    with patch.object(combat, "random", run.rng), patch.object(state, "random", run.rng):
        try:
            run.play()
        except class_aware.Defeat as error:
            failed = error.location
    result = run.result(failed)
    result["seed"] = seed
    return result


def summarize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault((record["archetype"], record["character"]), []).append(record)
    for (archetype, character), trials in groups.items():
        battles = [b for t in trials for b in t["battles"] if b["encounter"] == "dragon_valley_loc"]
        nodes = sorted({node for t in trials for node in t["levels"]})
        rows.append({"archetype": archetype, "character": character, "n": len(trials),
                     "completion_rate": mean(t["completed"] for t in trials),
                     "ignis_rate": mean(t["ignis_defeated"] for t in trials),
                     "terminal_rate": mean(t["reached_terminal"] for t in trials),
                     "ignis_rounds_median": median(b["rounds"] for b in battles) if battles else None,
                     "levels_mean": {node: mean(t["levels"][node] for t in trials if node in t["levels"]) for node in nodes},
                     "failures": dict(Counter(t["failed_at"] for t in trials if t["failed_at"]))})
    return rows


def _job(job: tuple) -> list[dict[str, Any]]:
    path, archetype, character, n, seed = job
    pack = state.load_scenario_pack(Path(path))
    return [trial(pack, character, sim.trial_seed(seed, "route_v2", character, index), ARCHETYPES[archetype])
            for index in range(n)]


def run_jobs(jobs: list[tuple], workers: int) -> list[dict[str, Any]]:
    if workers < 1:
        raise ValueError("workers must be positive")
    if workers == 1:
        batches = map(_job, jobs)
        return [record for batch in batches for record in batch]
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            return [record for batch in pool.map(_job, jobs) for record in batch]
    except PermissionError:
        # Windows restricted tokens may forbid multiprocessing's named pipes.
        # Independent Python processes with file IPC retain process isolation.
        return _file_workers(jobs, workers)


def _file_workers(jobs: list[tuple], workers: int) -> list[dict[str, Any]]:
    folder = checkpoints.ROOT / "eval/reports" / f"046-workers-{uuid.uuid4().hex}"
    folder.mkdir()
    try:
        def execute(index_job):
            index, job = index_job
            source, output = folder / f"{index}-in.json", folder / f"{index}-out.json"
            source.write_text(json.dumps([str(job[0]), *job[1:]]), encoding="utf-8")
            subprocess.run([sys.executable, "-X", "utf8", "-m", "scripts.balance.route_v2",
                            "--worker-job", str(source), "--worker-output", str(output)],
                           cwd=checkpoints.ROOT, check=True, stdout=subprocess.DEVNULL)
            return json.loads(output.read_text(encoding="utf-8"))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            return [record for batch in pool.map(execute, enumerate(jobs)) for record in batch]
    finally:
        for index in range(len(jobs)):
            (folder / f"{index}-in.json").unlink(missing_ok=True)
            (folder / f"{index}-out.json").unlink(missing_ok=True)
        folder.rmdir()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="046 offline measurement; deterministic engine only")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--scenario", type=Path, default=checkpoints.DEFAULT_SCENARIO)
    parser.add_argument("--archetypes", nargs="+", choices=SUPPORTED_ARCHETYPES, default=list(SUPPORTED_ARCHETYPES))
    parser.add_argument("--characters", nargs="+", choices=CHARACTERS, default=list(CHARACTERS))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--worker-job", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker-output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker_job:
        if not args.worker_output:
            parser.error("worker output is required")
        job = json.loads(args.worker_job.read_text(encoding="utf-8"))
        args.worker_output.write_text(json.dumps(_job(tuple(job)), ensure_ascii=False), encoding="utf-8")
        return 0
    if args.n < 1 or args.workers < 1:
        parser.error("n and workers must be positive")
    started = time.perf_counter()
    records = run_jobs([(args.scenario, a, c, args.n, args.seed) for a in args.archetypes for c in args.characters], args.workers)
    result = {"version": 2, "n": args.n, "seed": args.seed, "workers": args.workers,
              "completion_definition": COMPLETION_TITLE, "rows": summarize(records), "records": records,
              "elapsed_seconds": time.perf_counter() - started,
              "scenario_sha256": hashlib.sha256(args.scenario.read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": result["rows"], "elapsed_seconds": result["elapsed_seconds"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
