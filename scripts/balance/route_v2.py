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
from copy import deepcopy
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from statistics import mean, median
from typing import Any, Optional
from unittest.mock import patch

from host import combat, state, progression
from host.shops import trade
from host import shops
from . import budget, checkpoints, class_aware, route, sim
from .archetypes import (ARCHETYPES, CHARACTERS, COMPLETION_TITLE, IGNIS_FLAGS,
                         MAINLINE_NODES, TERMINAL_LOCATION, Archetype,
                         LevelModel, MilestoneLevelModel, ExpLevelModel, PassivePicker)

DEFAULT_OUTPUT = checkpoints.ROOT / ".tmp-test/053/053-route-v3.json"
BERSERKER = checkpoints.ROOT / "eval/balance/checkpoints_berserker.json"
SUPPORTED_ARCHETYPES = tuple(ARCHETYPES)

# Ordered proposals, not authored narrative or balance targets. Unavailable one-shot
# actions are logged as such; movement and combat still go through the real engine.
QUEST_STEPS = {
    "sarah": {"opening": ("ask_sarah_request", "accept_sarah_scarf", "help_sarah_shelves"),
              "town": ("give_moss_to_sarah", "deliver_sarah_scarf")},
    "mina": {"magic": ("ask_mina_missing",), "hot_spring": ("talk_mina", "leave_mina_wait"),
             "after_tree": ("prism_back", "crystal_back", "escort_mina", "hot_spring_back", "fork_back", "heat_back", "leave_seal"),
             "magic_return": ("report_mina_safe",)},
    "town_errands": {"forge": ("ask_robert_hammer", "ask_blacksmith_weakness"),
                     "forge_return": ("return_robert_hammer", "forge_ice_charm"),
                     "magic_return": ("forge_prism_weapon",)},
    "robin": {"inn": ("ask_robin_rumor", "accept_robin_goblin_quest")},
    "hearth": {"village": ("accept_refuge_hearth", "deliver_refuge_hearth"),
               "workshop": ("ask_workshop_hearth", "deliver_baked_lava_stone")},
    "nameless_soldiers": {"chapel": ("ask_battlefield_bell", "accept_nameless_soldiers", "deliver_nameless_soldiers")},
    "fire_seed": {"frozen_before": ("skip_frozen_clue_before_xanxus", "bluff_xanxus", "accept_xanxus_fire_seed"),
                  "nest": ("cleanse_fire_seed", "obey_xanxus_core")},
    "purification": {"castle": ("ask_king_ten_years",), "spring": ("draw_spirit_spring_water",),
                     "inn": ("ask_ian_dragon_tale",),
                     "frozen": ("inspect_frost_core",), "ian": ("read_ian_grief",)},
}

CHECK_PREFERENCES = {
    "lost_goblin_crossroads": ("crossroads_forward", "ignore_lost_goblin"),
    "forest_wolves": ("pass_cleared_wolves", "fight_forest_wolves"),
    "village_approach": ("approach_burning_village_carefully", "enter_burning_village_directly"),
    "burning_house": ("douse_with_ice", "break_burning_beam", "climb_to_window"),
    "ice_elemental_encounter": ("fight_ice_elemental",),
    "valley_entrance": ("fight_ash_wraiths",),
    "valley_lava_bridge": ("cross_lava_bridge", "take_ledge_path"),
    "goblin_fort": ("fort_first_bypass", "fight_fort_first_guard"),
    "goblin_fort_first_second": ("fort_second_bypass", "fight_fort_second_guards"),
    "goblin_fort_second_choice": ("explore_fort_right", "explore_fort_left"),
    "goblin_fort_second_right": ("fight_hobgoblin",),
    "goblin_fort_chest_choice": ("return_lost_goblin_box", "take_abandoned_goblin_box", "leave_without_goblin"),
    "cave_seal": ("enter_open_cave", "decode_seal", "pray_at_seal", "pour_holy_water_on_seal", "force_seal"),
    "cave_heat_corridor": ("pass_heat_corridor", "fight_heat"),
    "cave_crystal_corridor": ("pass_crystal_corridor", "fight_crystal"),
}
AVOID_PREFERENCES = {
    "forest_wolves": ("pass_cleared_wolves", "sneak_forest_wolves", "distract_forest_wolves", "fight_forest_wolves"),
    "ice_elemental_encounter": ("bypass_ice_elemental", "fight_ice_elemental"),
    "valley_entrance": ("sneak_through_ash", "turn_ash_wraiths", "fight_ash_wraiths"),
    "valley_lava_bridge": ("cross_lava_bridge", "take_ledge_path"),
    "goblin_fort_second_right": ("bypass_hobgoblin", "fight_hobgoblin"),
    "cave_heat_corridor": ("pass_heat_corridor", "sneak_heat", "fight_heat"),
    "cave_crystal_corridor": ("pass_crystal_corridor", "sneak_crystal", "fight_crystal"),
}


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
          recovery_threshold: float = .30, instrument: bool = True) -> dict[str, Any]:
    if session.get("difficulty") == "normal":
        from .battle_v3 import fight as measured_fight, fast_fight
        normal_fight = measured_fight if instrument else fast_fight
        return normal_fight(session, policy, rng, purify=purify, recovery_threshold=recovery_threshold)
    location, before = state.current_location_id(session), resources(session)
    opening: dict[str, Any] = {}
    expected_healing = 0.0
    actions, action_specs, consumables = Counter(), {}, Counter()
    expected_loss = 0.0
    phase_count = 0
    original_phase = combat._enemy_phase
    original_start = combat._apply_round_start_effects

    def measured_start(current, source_rng):
        nonlocal expected_healing
        if not opening:
            opening.update(budget.phase_moments(current))
            expected_healing = sustain(current)
        return original_start(current, source_rng)

    def measured_phase(current, source_rng):
        nonlocal expected_loss, phase_count
        expected_loss += budget.phase_moments(current)["expected_damage"]
        phase_count += 1
        return original_phase(current, source_rng)

    with patch.object(combat, "_enemy_phase", measured_phase), patch.object(combat, "_apply_round_start_effects", measured_start):
        session["combat_start_requested"] = True
        if not combat.ensure_combat_started(session):
            raise ValueError(f"Encounter did not start: {location}")
        free_action = sim.choose_action(session, "best_free")[0] if combat.combat_is_active(session) else None
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
               "p0_choice": f"{free_action['type']}:{free_action['id']}" if free_action else None,
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
                 *, level_model: Optional[LevelModel] = None, difficulty: str = "baby",
                 spring: str = "current", passive_table: Optional[dict[str, str]] = None,
                 branches: Optional[dict[str, str]] = None, effective: bool = False, measure: bool = True):
        super().__init__(pack, [], character, seed, quests=archetype.sidequests, decisions="class_aware",
                         policy=archetype.combat_policy, rest_policy="none",
                         evaluator=object(), difficulty=difficulty, effective=effective)
        self.spring = spring
        self.measure = measure
        self.branches = branches or {}
        self.escort_audit: list[dict[str, Any]] = []
        if difficulty == "normal" and archetype.id in {"P1", "P2", "P3", "P2s"}:
            self.policy = "heuristic_v3"
        self.archetype = archetype
        self.level_model = level_model or (ExpLevelModel() if difficulty == "normal" else MilestoneLevelModel())
        self.passive_picker = PassivePicker(archetype.passive_mode, passive_table)
        self.levels: dict[str, int] = {}
        self.exp_nodes: dict[str, Any] = {}
        self.snapshots: dict[str, Any] = {}
        self.level_costs: list[dict[str, Any]] = []
        self.last_level_resource = (self.session["character"].get("level", 1), class_aware.resource_score(self.session))
        self.scrolls: list[dict[str, Any]] = []
        self.cleared_spells: list[str] = []
        self.spring_visits = 0
        self.steps: list[dict[str, Any]] = []
        self.boss_arrivals: dict[str, Any] = {}
        self.optional_count = self.spring_rests = 0
        self.equipment_changes = 0
        self.initial_equipment = list(self.session["character"].get("equipment", []))
        self.seen_equipment = {i["name"] for i in self.session["character"]["inventory"]}
        self.initial = resources(self.session)
        self.purchases: list[dict[str, Any]] = []
        self.quest_attempts: list[dict[str, Any]] = []
        self.check_probes: list[dict[str, Any]] = []
        self.record_node()

    def record_node(self) -> None:
        if self.location in MAINLINE_NODES and self.location not in self.levels:
            self.levels[self.location] = self.level_model.observe(self.session, self.location)
            if isinstance(self.level_model, ExpLevelModel):
                self.exp_nodes.setdefault(self.location, self.level_model.snapshot(self.session))

    def choose_passives(self) -> None:
        self.session = self.passive_picker.apply(self.session)

    def settle(self) -> None:
        while class_aware.combat_pending(self.session):
            encounter = combat._encounter_for_session(self.session, self.session["scenario_pack"])
            if self.session.get("difficulty") == "normal" and self.measure:
                from .snapshots_v3 import capture
                self.snapshots.setdefault(self.location, capture(self.session))
                self.exp_nodes.setdefault(self.location, self.level_model.snapshot(self.session))
                self.levels.setdefault(self.location, self.level_model.observe(self.session, self.location))
            if encounter.get("encounter_class") == "boss":
                self.boss_arrivals.setdefault(self.location, resources(self.session))
            battle = fight(self.session, self.policy, self.rng, purify="purification" in self.quests,
                           recovery_threshold=self.archetype.recovery_threshold, instrument=self.measure)
            self.battles.append(battle)
            self.choose_passives()
            if self.session.get("difficulty") == "normal":
                level = self.session["character"]["level"]
                if level > self.last_level_resource[0]:
                    score = class_aware.resource_score(self.session)
                    self.level_costs.append({"from_level": self.last_level_resource[0], "to_level": level,
                                             "resource_cost_per_level": (self.last_level_resource[1]-score)/(level-self.last_level_resource[0]),
                                             "includes_level_refill_and_rewards": True})
                    self.last_level_resource = (level, score)
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
        spells_before = set(self.session["character"].get("learned_spells", []))
        available = class_aware.available_actions(self.session)
        selected = available.get(action_id)
        if self.measure and selected and selected.get("roll") and state.action_failure_risk(selected, self.session).get("crucial"):
            self.probe_check(selected)
        action = class_aware.act(self.session, action_id, self.rng)
        if self.session.get("difficulty") == "normal" and self.branches.get("escort_order") and action_id in {
                "borrow_fire_bat_dragon", "borrow_fire_bat_dragon_again", "escort_mina", "report_mina_safe"}:
            self.escort_audit.append({"action": action_id, "location": source,
                                      "companion_after": (self.session.get("companion") or {}).get("id"),
                                      "mina_quest_done": bool(self.session["flags"].get("mina_quest_done")),
                                      "borrowed": bool(self.session["flags"].get("borrowed_fire_bat_dragon"))})
        self.cleared_spells.extend(sorted(spells_before-set(self.session["character"].get("learned_spells", []))))
        if not self.session.get("combat"):
            self.choose_passives()
        self.equip_acquired()
        after = resources(self.session)
        self.equipment_changes += before["equipment"] != after["equipment"]
        self.steps.append({"location": source, "action": action_id, "before": before, "after": after,
                           "crucial": bool(selected and state.action_failure_risk(selected, self.session).get("crucial"))})
        self.record_node()
        if settle:
            self.settle()
        if self.session["character"]["hp"] <= 0 or (self.session.get("game_over") and
                self.session["game_over"].get("title") != COMPLETION_TITLE):
            raise class_aware.Defeat(source)

    def probe_check(self, action: dict[str, Any]) -> None:
        """Paired ordinary branches through forced combat; never advance the route RNG."""
        if any(p["action"] == action["id"] for p in self.check_probes):
            return
        values = {}
        for label in ("success", "failure"):
            copy = class_aware.clone(self.session)
            rng = random.Random()
            rng.setstate(self.rng.getstate())
            with patch.object(combat, "random", rng), patch.object(state, "random", rng):
                dice, dc = state.action_dice_settings(action, session=copy)
                # No criticals: measure the two ordinary authored effects.
                state.apply_action_result(copy, action, {"dc": dc, "success": label == "success",
                                                        "outcome": label})
                if copy.get("difficulty") == "normal" and not copy.get("combat"):
                    copy = self.passive_picker.apply(copy)
                for _ in range(12):
                    if not class_aware.combat_pending(copy):
                        break
                    result = fight(copy, self.policy, rng, purify="purification" in self.quests)
                    if copy.get("difficulty") == "normal":
                        copy = self.passive_picker.apply(copy)
                    if not result["continue"]:
                        break
            values[label] = class_aware.resource_score(copy)
        self.check_probes.append({"action": action["id"], "location": self.location, **values,
                                  "scope": "ordinary_branch_through_forced_combats"})

    def try_act(self, action: str) -> bool:
        if action in class_aware.available_actions(self.session):
            self.act(action)
            return True
        return False

    def decide(self, node: str) -> None:
        preferences = dict(CHECK_PREFERENCES)
        if "riku" not in self.quests:
            preferences["burning_house"] = ("leave_burning_house",)
        if self.archetype.avoid_battles:
            preferences.update(AVOID_PREFERENCES)
        rejected = set()
        for _ in range(class_aware.MAX_NODE_DECISIONS):
            if self.location != node:
                return
            available = class_aware.available_actions(self.session)
            choices = [a for a in preferences[node] if a in available and a not in rejected
                       and not ((available[a].get("free_action") or {}).get("operation") == "sneak"
                                and self.session["character"].get("sp", 0) < 1)]
            if not choices:
                raise ValueError(f"No v2 option at {node}")
            action = choices[0]
            if self.archetype.decision_rule == "checks" and node in {"burning_house", "cave_seal"}:
                def success_probability(identifier):
                    candidate = available[identifier]
                    dice, dc = state.action_dice_settings(candidate, session=self.session)
                    if dc <= 0:
                        return 1.0
                    return sum(weight for label, (weight, _) in class_aware.check_distribution(
                        self.session, dice, dc, roll=candidate.get("roll")).items() if "success" in label)
                action = max(choices, key=success_probability)
            self.choices.append({"node": node, "option": action})
            before = resources(self.session)
            self.act(action)
            if self.location == node and resources(self.session) == before:
                rejected.add(action)
        fallback = class_aware.STUCK_FALLBACK.get(node)
        if self.location == node and fallback:
            self.act(fallback)
        elif self.location == node:
            raise ValueError(f"Unresolved v2 node: {node}")

    def rest_point(self) -> None:
        location = self.location
        if self.archetype.rest_rule == "none" or location not in route.REST_ACTIONS:
            return
        identifier, cost = route.REST_ACTIONS[location]
        if cost:
            return
        if location == "elf_spring" and self.spring == "current":
            self.spring_visits += 1
            mode = self.archetype.spring_rest
            if self.spring_rests or mode == "never" or mode == "last_visit_once" and not getattr(self, "spring_last_visit", False):
                return
            if mode == "first_hp70" and (self.spring_visits > 1 or self.session["character"]["hp"] >= self.session["character"]["max_hp"] * .70):
                return
            before = resources(self.session)
            if self.try_act(identifier):
                self.spring_rests += 1
                self.rests.append({"location": location, "action": identifier, "cost": 0, "before": before, "after": resources(self.session)})
            return
        # Spring is unlimited in the scenario; partial hot-spring recovery may
        # need two visits, but full HP immediately stops this rule.
        while self.location == location and self.session["character"]["hp"] < self.session["character"]["max_hp"] * .70:
            before = resources(self.session)
            if not self.try_act(identifier):
                break
            self.spring_rests += int(location == "elf_spring")
            self.rests.append({"location": location, "action": identifier, "cost": 0,
                               "before": before, "after": resources(self.session)})
            if resources(self.session) == before:
                break

    def buy(self, shop: str, item: str) -> bool:
        before = resources(self.session)
        try:
            trade(self.session, shop, item, 1)
        except ValueError:
            return False
        self.equip_acquired()
        self.purchases.append({"shop": shop, "item": item, "before": before, "after": resources(self.session)})
        return True

    def hook(self, phase: str) -> None:
        for quest in self.archetype.sidequests:
            for identifier in QUEST_STEPS.get(quest, {}).get(phase, ()):
                if self.session.get("difficulty") == "normal" and quest == "mina" and identifier == "escort_mina" and self.location == "cave_fork":
                    self.act("cave_right")
                if self.session.get("difficulty") == "normal" and quest == "fire_seed" and identifier == "accept_xanxus_fire_seed" and self.branches.get("fire_seed") == "refuse":
                    identifier = "refuse_xanxus_with_rescue"
                    if self.location == "xanxus_ultimatum" and identifier not in class_aware.available_actions(self.session):
                        identifier = "refuse_xanxus_without_rescue"
                if self.session.get("difficulty") == "normal" and identifier == "accept_robin_goblin_quest":
                    # Accepting teleports directly into the fort; handle it in the route macro.
                    continue
                self.quest_attempts.append({"quest": quest, "action": identifier, "available": self.try_act(identifier)})
        if self.session.get("difficulty") == "normal" and phase == "spring" and "sarah" in self.quests:
            from host.free_actions import adjudicate
            if not self.session["flags"].get("sarah_moss_done"):
                adjudicate(self.session, dict(kind="interact", operation="observe", target_id="glowing_moss_patch", item_id="", action_id="", advance=False, approach="観察する", reply=""))

    def shop_here(self) -> None:
        if self.archetype.shopping_rule == "all_shops":
            for shop in self.session["scenario_pack"].get("shops", []):
                if shop["location_id"] == self.location:
                    # Unlimited stock is not an instruction to buy forever.
                    # One of each listing per shop per playthrough is the proposal.
                    for listing in shop["items"]:
                        if listing["item_id"].startswith("spellbook_"):
                            continue
                        if not any(p["shop"] == shop["id"] and p["item"] == listing["item_id"] for p in self.purchases):
                            self.buy(shop["id"], listing["item_id"])
        elif self.archetype.shopping_rule == "preparations":
            for shop, item in (("forge_shop", "adamantite_armor"), ("sarah_shop", "holy_water")):
                if not any(p["shop"] == shop and p["item"] == item for p in self.purchases):
                    self.buy(shop, item)
        self.buy_scrolls()

    def buy_scrolls(self) -> None:
        if self.session.get("difficulty") != "normal" or self.session["character"]["character_id"] != "mage" or self.archetype.id not in {"P1", "P2", "P3", "P2s"} or self.location != "magic_shop":
            return
        for identifier in ("spellbook_lightning", "spellbook_arcane_lance"):
            item = next(i for i in self.session["scenario_pack"]["items"] if i["id"] == identifier)
            if any(s["id"] == item["learn_skill"]["id"] for s in self.session["character"]["skills"]) or any(s["item"] == identifier for s in self.scrolls):
                continue
            if self.buy("magic_shop", identifier):
                self.session = progression.learn_spell(self.session, identifier)
                self.scrolls.append({"item": identifier, "skill": item["learn_skill"]["id"], "location": self.location,
                                     "level": self.session["character"]["level"], "before_encounter": self.battles[-1]["encounter"] if self.battles else None,
                                     "after_battles": len(self.battles)})

    def visit_scroll_shop(self) -> None:
        if self.session.get("difficulty") != "normal" or self.session["character"]["character_id"] != "mage" or self.archetype.id not in {"P1", "P2", "P3", "P2s"}:
            return
        shop = next(s for s in self.session["scenario_pack"]["shops"] if s["id"] == "magic_shop")
        purchased = {s["item"] for s in self.scrolls}
        stock = self.session.get("shop_stock", {}).get("magic_shop", {})
        eligible = [offer for offer in shop["items"] if offer["item_id"].startswith("spellbook_")
                    and offer["item_id"] not in purchased and stock.get(offer["item_id"], offer.get("stock")) != 0
                    and self.session["character"]["gold"] >= shops._price(self.session, shop, offer)]
        if eligible and self.try_act("go_magic_shop"):
            self.buy_scrolls()
            self.act("return_castle_from_magic_shop")

    def play(self) -> None:
        checkpoints.replay_step(self.session, "@opening")
        self.initial = resources(self.session)
        self.last_level_resource = (self.session["character"].get("level", 1), class_aware.resource_score(self.session))
        if "ask_king_info" in self.archetype.optional_interactions:
            self.act("ask_king_info")
            self.optional_count += 1
        self.hook("castle")
        self.act("go_castle_town")
        if self.archetype.shopping_rule != "none":
            self.act("go_item_shop")
            self.optional_count += int(self.buy("sarah_shop", "ice_charm"))
            if self.archetype.companion_rule == "fire_bat_dragon" and not (
                    self.session.get("difficulty") == "normal" and self.archetype.id == "P3"
                    and self.branches.get("escort_order") == "borrow_after_report"):
                self.act("borrow_fire_bat_dragon")
                self.optional_count += 1
            self.hook("opening")
            self.shop_here()
            self.act("return_castle_from_item_shop")
        if self.quests & {"preparations", "purification", "town_errands", "mina"}:
            self.town_shops()
        else:
            self.visit_scroll_shop()
        # Reuse the existing continuous route; the prelude has already run.
        self.run_mainline()

    def run_mainline(self) -> None:
        # Run.play's final fight uses route.fight; the overridden act/settle records it here instead.
        if self.session.get("difficulty") == "normal" and "robin" in self.quests:
            self.act("go_inn")
            self.try_act("invite_robin")
            if self.try_act("accept_robin_goblin_quest"):
                self.fort()
                self.act("crossroads_forward")
            else:
                self.act("return_castle_from_inn")
                self.start_forest()
        else:
            self.start_forest()
        self.forest_and_beyond()

    def start_forest(self) -> None:
        self.act("go_dark_forest")
        self.act("attack_slime")
        if "fort" in self.quests:
            self.act("help_lost_goblin")
            self.act("enter_goblin_fort")
            self.fort()
            self.act("crossroads_forward")
        else:
            self.decide("lost_goblin_crossroads")

    def forest_and_beyond(self) -> None:
        self.rest_point()
        if self.location == "forest_wolves" and self.quests & {"cave_full", "purification"}:
            self.act("wolves_back")
        self.hook("spring")
        if "cave_full" in self.quests:
            self.cave()
        self.spring_last_visit = True
        if self.spring == "current" or "cave_full" in self.quests:
            self.rest_point()
        if self.archetype.grind:
            self.grind_repeatable()
        if self.location == "elf_spring":
            self.act("continue_from_elf_spring")
        self.decide("forest_wolves")
        if self.quests & {"town_errands", "purification"}:
            self.act("return_inn_after_forest")
            self.town_shops(returning=True)
            self.act("return_forest_exit")
        if "battlefield" in self.quests:
            self.battlefield_trip()
        if "merchant" in self.quests:
            self.act("return_inn_after_forest")
            self.act("go_alley")
            self.act("wait_for_night_in_alley")
            character = self.session["character"]["character_id"]
            self.try_act("hear_curse_offer_" + character)
            self.try_act("accept_curse_offer_" + character)
            if self.session.get("difficulty") == "normal" and self.branches.get("merchant") == "pay":
                self.try_act("pay_curse_price_" + character)
            else:
                self.act("betray_cursed_merchant")
            self.act("return_castle_after_curse")
            self.act("return_forest_exit")
        self.act("leave_forest_for_village")
        self.decide("village_approach")
        self.decide("burning_house")
        self.act("visit_village")
        self.try_act("return_riku") if "riku" in self.quests else None
        if self.session.get("difficulty") == "normal" and "gald" in self.quests:
            self.try_act("open_gald_shop")
        self.hook("village")
        self.shop_here()
        self.act("return_frozen_clue")
        self.hook("frozen_before")
        self.hook("frozen")
        self.act("investigate_frozen_village")
        self.decide("ice_elemental_encounter")
        self.hook("ian")
        self.act("accept_ian_request")
        self.decide("valley_entrance")
        self.decide("valley_lava_bridge")
        self.hook("nest")
        if self.location == "warlock_at_nest":
            self.act("continue_after_warlock")
        self.act("enter_dragon_nest")
        if self.location == "ignis_purified":
            for action in ("hear_ignis_testimony", "receive_ignis_scale", "ask_ignis_aid"):
                self.try_act(action)
        elif "purification" in self.quests:
            self.try_act("examine_ignis_wound")
        self.act("return_to_castle_report")
        self.act("enter_festival_town")
        self.shop_here()
        if "mansion" in self.quests:
            self.act("go_general_mansion")
            self.act("sneak_into_mansion")
            self.act("fight_ice_sentinels")
            if self.session.get("difficulty") != "normal" or self.location == "mansion_study":
                self.act("take_draco_journal")
                self.try_act("open_scale_box")
                self.act("leave_mansion_study")
        if "town_errands" in self.quests:
            self.town_shops(returning=True)
        self.visit_scroll_shop()
        self.act("go_report_hall")
        # Ordinary players do not automatically expose Draco just because a clue exists.
        if "purification" in self.quests and "report_with_evidence" in class_aware.available_actions(self.session):
            self.act("report_with_evidence")
        else:
            self.act("report_normally")

    def cave(self) -> None:
        self.act("inspect_spring_wall")
        self.decide("cave_seal")
        if self.location != "cave_heat_corridor":
            return
        self.decide("cave_heat_corridor")
        if self.session.get("difficulty") == "normal" and self.location == "elf_spring":
            return
        self.act("cave_left")
        if self.session.get("difficulty") == "normal" and self.location == "elf_spring":
            return
        if "hearth" in self.quests:
            self.try_act("pick_baked_lava_stone")
        self.act("open_lava_chest")
        if self.session.get("difficulty") == "normal" and self.location == "elf_spring":
            return
        self.act("lava_back")
        self.act("cave_right")
        self.rest_point()
        self.hook("hot_spring")
        self.act("hot_spring_forward")
        self.decide("cave_crystal_corridor")
        if self.session.get("difficulty") == "normal" and self.location == "elf_spring":
            return
        self.hook("after_tree")
        if self.location == "cave_prism_tree":
            self.act("leave_prism_tree")

    def fort(self) -> None:
        for _ in range(30):
            node = self.location
            if node not in class_aware.FORT_LOCATIONS:
                return
            if node in CHECK_PREFERENCES:
                self.decide(node)
            elif node == "goblin_fort_healing_circle":
                self.act("use_fort_healing_circle")
            elif node == "goblin_fort_third_gate":
                if not self.try_act("give_correct_password"):
                    self.act("admit_no_password")
            else:
                raise ValueError(f"Unexpected fort location: {node}")
        raise ValueError("Fort did not finish")

    def town_shops(self, returning: bool = False) -> None:
        for enter, back, phase in (("go_item_shop", "return_castle_from_item_shop", "town"),
                                   ("go_forge", "return_castle_from_forge", "forge_return" if returning else "forge"),
                                   ("go_magic_shop", "return_castle_from_magic_shop", "magic_return" if returning else "magic")):
            self.act(enter)
            self.hook(phase)
            if phase == "forge" and "purification" in self.quests:
                self.try_act("ask_blacksmith_weakness")
            self.shop_here()
            self.act(back)
        if (returning and self.session.get("difficulty") == "normal" and self.archetype.id == "P3"
                and self.session["flags"].get("mina_quest_done")):
            borrow = None
            flags = self.session["flags"]
            if self.branches.get("escort_order") == "borrow_after_report" and not flags.get("asked_to_borrow_fire_bat_dragon"):
                borrow = "borrow_fire_bat_dragon"
            elif (self.branches.get("escort_order") == "borrow_before_escort"
                  and flags.get("borrowed_fire_bat_dragon") and not self.session.get("companion")
                  and not flags.get("asked_to_borrow_fire_bat_dragon_again")):
                borrow = "borrow_fire_bat_dragon_again"
            if borrow:
                self.act("go_item_shop")
                if self.try_act(borrow):
                    self.optional_count += 1
                self.act("return_castle_from_item_shop")
        if self.quests & {"robin", "purification"} and not returning:
            self.act("go_inn")
            self.hook("inn")
            self.act("return_castle_from_inn")

    def battlefield_trip(self) -> None:
        self.act("enter_old_battlefield")
        self.act("battlefield_to_bones")
        self.act("fight_skeleton_soldiers")
        self.act("bones_to_tower")
        for identifier in ("talk_old_soldier", "search_watchtower", "pray_for_ghost"):
            self.try_act(identifier)
        self.act("tower_to_bones")
        self.act("bones_to_marsh")
        self.act("fight_ghoul")
        self.act("marsh_to_chapel")
        self.try_act("read_knight_epitaph")
        self.act("fight_grave_knight")
        self.try_act("ring_battlefield_bell")
        for identifier in ("chapel_to_marsh", "marsh_to_bones", "bones_to_battlefield"):
            self.act(identifier)
        if "oaksdawn" in self.quests:
            self.oaksdawn_trip()
        self.act("battlefield_to_forest")

    def oaksdawn_trip(self) -> None:
        self.act("battlefield_to_oaksdawn")
        self.act("square_to_hq")
        for identifier in ("greet_walter", "ask_guardian_refusal", "request_guardian_letter", "report_battlefield_bell_hq", "open_gorge_path"):
            self.try_act(identifier)
        self.act("hq_to_square")
        self.act("square_to_chapel")
        self.hook("chapel")
        self.try_act("report_battlefield_bell_chapel")
        self.shop_here()
        self.act("chapel_to_square")
        self.act("square_to_workshop")
        self.shop_here()
        self.hook("workshop")
        self.try_act("forge_dawn_weapon")
        self.act("workshop_to_square")
        self.act("square_to_inn")
        self.try_act("ask_oaksdawn_rumor")
        self.act("inn_to_square")
        self.act("square_to_wall")
        self.try_act("talk_dragon_knight")
        self.try_act("challenge_dragon_knight")
        if "gorge" in self.quests:
            if "oaksdawn_east_pass_open" not in class_aware.available_actions(self.session):
                self.try_act("oaksdawn_east_pass")
            self.act("oaksdawn_east_pass_open")
            self.gorge_trip()
        else:
            self.act("oaksdawn_to_battlefield")

    def gorge_trip(self) -> None:
        for identifier in ("gorge_to_rockfall", "fight_gorge_rockfall_path", "rockfall_to_camp", "search_miner_camp",
                           "camp_to_rockfall", "rockfall_to_cliff", "inspect_white_claw", "cliff_to_giant",
                           "fight_gorge_giant_path", "giant_to_worm", "fight_gorge_worm_lair", "worm_to_giant",
                           "giant_to_cliff", "cliff_to_rockfall", "rockfall_to_entrance", "gorge_to_wall", "oaksdawn_to_battlefield"):
            self.act(identifier)

    def grind_repeatable(self) -> None:
        # Current engine persists every encounter's defeated flags. Revisiting
        # it or resting cannot respawn enemies. Do not clear flags to invent EXP.
        self.grinding = {"repeatable_encounters": [], "fights": 0, "levels_gained": 0,
                         "resource_cost_per_level": None, "status": "not_applicable",
                         "reason": "当前无可重复获益战斗；不重置 defeated flags。normal 使用 P0b 升级间净资源差估计。"}

    def result(self, failed_at: Optional[str]) -> dict[str, Any]:
        ending = self.session.get("game_over") or {}
        final = resources(self.session)
        return {"archetype": self.archetype.id, "character": self.session["character"]["character_id"],
                **({"escort_audit": self.escort_audit} if self.session.get("difficulty") == "normal" and self.branches.get("escort_order") else {}),
                "completed": ending.get("title") == COMPLETION_TITLE,
                "ignis_defeated": any(self.session["flags"].get(flag) for flag in IGNIS_FLAGS),
                "reached_terminal": TERMINAL_LOCATION in self.levels or bool(ending.get("ending")),
                "ending": ending.get("ending"), "failed_at": failed_at,
                "battles": self.battles, "boss_arrivals": self.boss_arrivals,
                "levels": self.levels, "rests": self.rests, "choices": self.choices,
                "optional_interactions": self.optional_count, "equipment_changes": self.equipment_changes,
                "steps": self.steps, "purchases": self.purchases, "initial": self.initial,
                "healing_item_names": [i["name"] for i in self.session["scenario_pack"].get("items", [])
                                       if combat.item_combat_spec(i).get("kind") == "heal"],
                "quest_attempts": self.quest_attempts, "check_probes": self.check_probes,
                "passives": self.session["character"].get("passive_history", []), "final": final,
                "exp_nodes": self.exp_nodes, "snapshots": self.snapshots, "level_costs": self.level_costs,
                "scrolls": [{**s, "uses": sum(b.get("skill_usage", {}).get(s["skill"], {}).get("uses", 0) for b in self.battles[s["after_battles"]:])} for s in self.scrolls],
                "cleared_spells": self.cleared_spells,
                "grinding": getattr(self, "grinding", {"status": "not_applicable", "reason": "待 050/051：无战斗 EXP。"}) if self.archetype.grind else None}


def trial(pack: dict[str, Any], character: str, seed: int, archetype: Archetype, **kwargs: Any) -> dict[str, Any]:
    from .snapshots_v3 import ExpObserver
    run = MeasurementRun(pack, character, seed, archetype, **kwargs)
    failed = None
    with patch.object(combat, "random", run.rng), patch.object(state, "random", run.rng), ExpObserver():
        try:
            run.play()
        except class_aware.Defeat as error:
            failed = error.location
    result = run.result(failed)
    result["difficulty"] = run.session.get("difficulty", "baby")
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
    if str(job[0]).endswith("_probes"):
        if str(job[0]).startswith("normal_") or job[0] == "enumerate_probes":
            from . import probes_v3
            return probes_v3.run_job(job)
        from . import probes_v2
        return probes_v2.run_job(job)
    path, archetype, character, n, seed, *options = job
    settings = options[0] if options else {}
    difficulty, spring = settings.get("difficulty", "baby"), settings.get("spring", "current")
    from .legacy_spring import select_spring
    from host.difficulty import apply_difficulty
    pack = state.load_scenario_pack(Path(path))
    pack = select_spring(apply_difficulty(pack, difficulty), spring)
    records = []
    candidates: dict[str, dict[int, dict[str, Any]]] = {}
    histograms: dict[str, Counter] = {}
    for index in range(n):
        record = trial(pack, character, sim.trial_seed(seed, "route_v2", character, index), ARCHETYPES[archetype],
                       difficulty=difficulty, spring=spring, effective=True,
                       passive_table=settings.get("passive_table"), branches=settings.get("branches"), measure=settings.get("measure", True))
        if settings.get("branch_proposal"):
            record["branch_proposal"] = settings["branch_proposal"]
        for encounter, snapshot in record.pop("snapshots", {}).items():
            level = snapshot["character"]["level"]
            candidates.setdefault(encounter, {}).setdefault(level, {"snapshot": snapshot, "seed": record["seed"], "trial_index": index})
            histograms.setdefault(encounter, Counter())[level] += 1
        if index:
            # Keep one full audit trace per cell, the remaining records retain
            # every input used by the reducers without three inventory copies.
            record.pop("steps")
            record.pop("quest_attempts")
            for battle in record["battles"]:
                battle.pop("after_combat", None)
                battle.pop("after_resolution", None)
                battle["before"].pop("inventory")
                battle["before"].pop("equipment")
        records.append(record)
    if candidates:
        records[0]["checkpoint_candidates"] = {}
        for encounter, by_level in candidates.items():
            values = list(histograms[encounter].elements())
            middle = median(values)
            level = min(by_level, key=lambda level: (abs(level-middle), by_level[level]["trial_index"]))
            records[0]["checkpoint_candidates"][encounter] = {**by_level[level], "median_level": middle,
                "arrival_count": len(values), "level_histogram": {str(level): count for level, count in sorted(histograms[encounter].items())}}
    return records


def run_jobs(jobs: list[tuple], workers: int, *, difficulty: Optional[str] = None,
             spring: Optional[str] = None) -> list[dict[str, Any]]:
    if workers < 1:
        raise ValueError("workers must be positive")
    if difficulty is not None or spring is not None:
        if difficulty is not None and difficulty not in {"baby", "normal"} or spring is not None and spring not in {"current", "legacy"}:
            raise ValueError("Invalid measurement mode")
        updated = []
        for job in jobs:
            settings = dict(job[5]) if len(job) > 5 else {}
            if difficulty is not None:
                settings["difficulty"] = difficulty
            if spring is not None:
                settings["spring"] = spring
            updated.append((*job[:5], settings))
        jobs = updated
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
    folder = checkpoints.ROOT / ".tmp-test/053" / f"workers-{uuid.uuid4().hex}"
    folder.parent.mkdir(parents=True, exist_ok=True)
    folder.mkdir()
    try:
        def execute(index_job):
            index, job = index_job
            source, output = folder / f"{index}-in.json", folder / f"{index}-out.json"
            source.write_text(json.dumps([str(value) if isinstance(value, Path) else value for value in job]), encoding="utf-8")
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
    parser.add_argument("--difficulty", choices=("baby", "normal"), default="baby")
    parser.add_argument("--spring", choices=("current", "legacy"), default="current")
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
    settings = dict(difficulty=args.difficulty, spring=args.spring)
    records = run_jobs([(args.scenario, a, c, args.n, args.seed, settings) for a in args.archetypes for c in args.characters], args.workers)
    result = {"version": 3, "difficulty": args.difficulty, "spring": args.spring,
              "n": args.n, "seed": args.seed, "workers": args.workers,
              "completion_definition": COMPLETION_TITLE, "rows": summarize(records), "records": records,
              "elapsed_seconds": time.perf_counter() - started,
              "scenario_sha256": hashlib.sha256(args.scenario.read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"rows": result["rows"], "elapsed_seconds": result["elapsed_seconds"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
