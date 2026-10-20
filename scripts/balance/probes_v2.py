"""Paired deterministic-engine probes for measurement v2, separate from routes."""
from __future__ import annotations

import json
import random
from pathlib import Path
from copy import deepcopy
from statistics import mean
from typing import Any
from unittest.mock import patch

from host import combat, state
from . import budget, checkpoints, economy, route_v2, sim
from .archetypes import CHARACTERS

PREPARATIONS = checkpoints.ROOT / "eval/balance/preparations.json"


def extended_inputs(pack, cp, targets):
    """Use 036's existing regional checkpoints for bosses absent from the old matrix."""
    expanded = {**targets, "encounters": {loc["id"]: loc["combat"]["encounter_class"]
                for loc in pack["locations"] if loc.get("combat", {}).get("encounter_class")}}
    points = deepcopy(cp)
    for encounter in expanded["encounters"]:
        if encounter not in points["encounters"]:
            entries = {}
            for character in sim.selected_characters(pack, encounter, ["all"]):
                entries[character] = economy.encounter_checkpoint(pack, cp, encounter, character)["encounters"][encounter]["characters"][character]
            points["encounters"][encounter] = {"characters": entries, "source": "scripts.balance.economy.encounter_checkpoint"}
    return points, expanded


def observed_checkpoint(save: dict[str, Any]) -> dict[str, Any]:
    """Recover Ignis gear/resources with explicit evidence, never use final armour."""
    final = deepcopy(save["character"])
    events = save.get("event_log", [])
    ignis = next(e for e in events if e.get("kind") == "combat_resolved" and
                 any(enemy.get("id") == "ignis" for enemy in e.get("data", {}).get("enemies", [])))
    end_time = ignis["created_at"]
    from scripts.playtest import save_telemetry

    player = deepcopy(ignis["data"]["player"])
    arrival = save_telemetry.extract(save)["boss_arrivals"]["dragon_valley_loc"]
    if arrival["inventory"] is None:
        raise ValueError("Ignis arrival inventory could not be reconstructed")
    inventory = []
    catalog = {i["name"]: i for i in [*save["scenario_pack"]["items"], *final["inventory"]]}
    for entry in arrival["inventory"]:
        inventory.append({**deepcopy(catalog.get(entry["name"], entry)), "quantity": entry.get("quantity", 1)})
    equipment = list(final["equipment"])
    for event in reversed(events):
        if event.get("kind") == "item_equipped" and event["created_at"] > end_time:
            item_id = event["data"]["item_id"]
            item = next((i for i in final["inventory"] if i.get("id") == item_id), {})
            equipment = [name for name in equipment if name != item.get("name")]
            if event["data"].get("removed"):
                equipment.append(event["data"]["removed"])
    final.update(inventory=inventory, equipment=equipment, gold=player["gold"] - 100)
    entry = {key: deepcopy(final[key]) for key in ("level", "attributes", "inventory", "equipment", "gold", "max_hp", "max_mp", "max_sp")}
    entry.update(companion=deepcopy(save.get("companion")), completed_milestones=save["completed_milestones"],
                 flags={"fire_bat_empowered": True},
                 source="eval/playtests/e2b9fdd9631c441298685da5d75d6cfb.json: pre-Ignis inventory reconstructed from resolution/resource ledger, rollback later equipment changes; full-resource probe")
    greatsword = deepcopy(entry)
    greatsword["equipment"] = [name for name in entry["equipment"] if name != "鉄の剣"] + ["氷鉄の大剣"]
    return {"version": 2, "status": "save_verified_configuration", "source": entry["source"],
            "notes": ["这是满资源独立配置探针，不是已证实的 Ignis 开战快照。", "Ignis 前流水重建为薬草×7/治療の巻物×8，通关时为×7/×9；金币601G由结算701G减实际奖励100G。",
                      "四种霊薬按存档为剛力/鉄壁/叡智/迅速；Ignis后才装备アダマンタイトの鎧。"],
            "encounters": {"dragon_valley_loc": {"characters": {"hero": entry}}},
            "profiles": {"human_berserker": entry, "P0b + 氷鉄の大剣": greatsword,
                         "无同伴": {**deepcopy(entry), "companion": None}}}


def damage_budget(pack: dict[str, Any], cp: dict[str, Any], targets: dict[str, Any]) -> list[dict[str, Any]]:
    legacy = {(r["encounter"], r["character"]): r for r in budget.incoming_damage_budget(pack, cp, targets)}
    rows = []
    for (encounter, character), old in legacy.items():
        session = sim.prepare_session(pack, encounter, character, cp)
        opening = {}
        original = combat._apply_round_start_effects
        def capture(current, rng):
            if not opening:
                opening.update(budget.phase_moments(current))
            return original(current, rng)
        with patch.object(combat, "random", random.Random(0)), patch.object(combat, "_apply_round_start_effects", capture):
            combat.ensure_combat_started(session)
        rows.append({"encounter": encounter, "character": character,
                     "encounter_class": targets["encounters"][encounter], "level": old["level"],
                     "max_hp": session["character"]["max_hp"], **opening,
                     "legacy_ratio": old["ratio"], "legacy_upper_limit": old["limit"],
                     "bandwidth": targets["incoming_damage_bandwidth"].get(targets["encounters"][encounter])})
    return rows


def remove_preparation(session: dict[str, Any], preparation: dict[str, Any]) -> None:
    actor, removal = session["character"], preparation["remove"]
    if removal["kind"] == "equipment":
        ids = set(preparation["item_ids"])
        names = {i["name"] for i in actor["inventory"] if i.get("id") in ids}
        actor["inventory"] = [i for i in actor["inventory"] if i.get("id") not in ids]
        actor["equipment"] = [name for name in actor["equipment"] if name not in names]
        fallback = removal.get("fallback")
        if fallback and any(i["name"] == fallback for i in actor["inventory"]):
            state._equip_inventory_item(session, fallback)
        state._synchronize_equipment(actor)
    elif removal["kind"] == "companion":
        session["companion"] = None
    elif removal["kind"] == "flag":
        session["flags"].pop(removal["flag"], None)
    elif removal["kind"] == "purification_route":
        # Disable the whole route, including the cleric's MP alternative. This
        # is not the same experiment as removing one bottle of holy water.
        for flag in ("frost_trace_seen", "noticed_general_frost", "heard_treaty_lore"):
            session["flags"].pop(flag, None)
        actor["inventory"] = [i for i in actor["inventory"] if i.get("id") not in {"holy_water", "white_dragon_scale"}]
    else:
        raise ValueError("Unknown preparation removal")


def prepared_session(pack, cp, character):
    session = sim.prepare_session(pack, "dragon_valley_loc", character, cp)
    actor = session["character"]
    catalog = {i["id"]: i for i in pack["items"]}
    for identifier in ("ruby_charm", "adamantite_armor", "holy_water", "ice_iron_greatsword"):
        if not any(i.get("id") == identifier for i in actor["inventory"]):
            actor["inventory"].append({**deepcopy(catalog[identifier]), "quantity": 1})
    for identifier in ("ruby_charm", "adamantite_armor", "ice_iron_greatsword"):
        state._equip_inventory_item(session, identifier)
    session["companion"] = deepcopy(next(c for c in pack["companions"] if c["id"] == "fire_bat_dragon"))
    session["flags"].update(fire_bat_empowered=True, frost_trace_seen=True, heard_treaty_lore=True)
    return session


def _battles(template, n, seed, key, *, policy="heuristic", purify=False):
    results = []
    for index in range(n):
        session = class_clone(template)
        rng = random.Random(sim.trial_seed(seed, key, template["character"]["character_id"], index))
        with patch.object(combat, "random", rng), patch.object(state, "random", rng):
            session["combat_start_requested"] = True
            if not combat.ensure_combat_started(session):
                raise ValueError("Probe encounter did not start")
            while combat.combat_is_active(session):
                action, target = sim.choose_action(session, policy, purify=purify, reserve_purification=purify)
                combat.perform_combat_action(session, action["type"], action["id"], target, rng=rng)
        results.append({"status": session["combat"]["status"], "rounds": session["combat"]["round"]})
    return results


def class_clone(session):
    return deepcopy(session, {id(session["scenario_pack"]): session["scenario_pack"]})


def _win(results):
    return mean(r["status"] in {"victory", "purified"} for r in results)


def preparation_probes(pack, cp, character, n, seed):
    items = json.loads(PREPARATIONS.read_text(encoding="utf-8"))["encounters"]["dragon_valley_loc"]["items"]
    template = prepared_session(pack, cp, character)
    full = _win(_battles(template, n, seed, "046-preparation", purify=True))
    rows = []
    for item in items:
        removed = class_clone(template)
        remove_preparation(removed, item)
        without = _win(_battles(removed, n, seed, "046-preparation", purify=True))
        rows.append(dict(character=character, encounter="dragon_valley_loc", preparation=item["id"],
                         critical=item["critical"], n=n, full=full, without=without, uplift=full-without, status="proposed"))
    return rows


def companion_probes(pack, cp, targets, character, n, seed):
    rows = []
    for encounter, category in targets["encounters"].items():
        if category != "boss":
            continue
        template = sim.prepare_session(pack, encounter, character, cp, companion=False)
        template["flags"].pop("fire_bat_empowered", None)
        base = _win(_battles(template, n, seed, encounter))
        for companion in pack.get("companions", []):
            candidate = class_clone(template)
            candidate["companion"] = deepcopy(companion)
            rate = _win(_battles(candidate, n, seed, encounter))
            rows.append(dict(character=character, encounter=encounter, companion=companion["id"],
                             n=n, without=base, with_companion=rate, uplift=rate-base))
        empowered = class_clone(template)
        empowered["companion"] = deepcopy(next(c for c in pack["companions"] if c["id"] == "fire_bat_dragon"))
        empowered["flags"]["fire_bat_empowered"] = True
        rate = _win(_battles(empowered, n, seed, encounter))
        rows.append(dict(character=character, encounter=encounter, companion="fire_bat_dragon:empowered", n=n,
                         without=base, with_companion=rate, uplift=rate-base))
    return rows


def level_probes(pack, cp, targets, character, n, seed):
    rows = []
    for encounter, category in targets["encounters"].items():
        if category != "boss":
            continue
        template = sim.prepare_session(pack, encounter, character, cp)
        actor = template["character"]
        level = actor.get("level", 1)
        # Fixed loadout/skills isolate numeric growth. Lv+1 beyond the existing
        # milestone cap is unavailable, not an invented Lv6.
        maximum = max(m["level"] for m in pack["milestones"])
        rates = {}
        for probe_level in (level-1, level, level+1):
            if not 1 <= probe_level <= maximum:
                continue
            candidate = class_clone(template)
            gains = next(m["gains"][character] for m in pack["milestones"] if character in m.get("gains", {}))
            diff = probe_level-level
            candidate["character"]["level"] = probe_level
            for resource in ("hp", "mp", "sp"):
                key = "max_"+resource
                candidate["character"][key] = max(0, actor[key] + diff*gains.get(key, 0))
                candidate["character"][resource] = candidate["character"][key]
            for key, value in gains.get("attributes", {}).items():
                candidate["character"]["attributes"][key] += diff*value
            rates[probe_level] = _win(_battles(candidate, n, seed, encounter))
        for low in sorted(rates):
            if low+1 in rates:
                rows.append(dict(character=character, encounter=encounter, from_level=low, to_level=low+1,
                                 n=n, before=rates[low], after=rates[low+1], uplift=rates[low+1]-rates[low],
                                 scope="fixed_equipment_and_skills_numeric_growth_only"))
    return rows


def boss_policy_probes(pack, cp, targets, character, n, seed):
    rows = []
    for encounter, category in targets["encounters"].items():
        if category == "boss":
            template = sim.prepare_session(pack, encounter, character, cp)
            for policy in sim.POLICIES:
                result = _battles(template, n, seed, encounter, policy=policy)
                rows.append(dict(encounter=encounter, character=character, policy=policy,
                                 rounds=[r["rounds"] for r in result], win_rate=_win(result)))
    return rows


def run_job(job: tuple) -> list[dict[str, Any]]:
    kind, path, character, n, seed = job
    pack = state.load_scenario_pack(Path(path))
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    targets = json.loads((checkpoints.ROOT / "eval/balance/targets.json").read_text(encoding="utf-8"))
    cp, targets = extended_inputs(pack, cp, targets)
    functions = {"preparation_probes": lambda: preparation_probes(pack, cp, character, n, seed),
                 "companion_probes": lambda: companion_probes(pack, cp, targets, character, n, seed),
                 "level_probes": lambda: level_probes(pack, cp, targets, character, n, seed),
                 "boss_policy_probes": lambda: boss_policy_probes(pack, cp, targets, character, n, seed)}
    return functions[kind]()
