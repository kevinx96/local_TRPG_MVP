from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Optional
from unittest.mock import patch

from host import combat, state
from host.scenario_context import current_action_choices
from . import checkpoints, sim

# 027: continuous mainline where displayed options are chosen by expected outcome.
QUEST_ORDER = ("gald", "riku", "cave_chest", "cave_full", "fort")
QUESTS_PATH = checkpoints.ROOT / "eval/balance/class_aware_quests.json"
ESTIMATE_N = 40
EVAL_DEPTH = 2
MAX_NODE_DECISIONS = 10
QUEST_LOSS_LIMIT = .02

NODES: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "lost_goblin_crossroads": [("ignore", ("ignore_lost_goblin", "crossroads_forward")),
                               ("forward", ("crossroads_forward",))],
    "forest_wolves": [("fight", ("fight_forest_wolves",)), ("distract", ("distract_forest_wolves",)),
                      ("sneak", ("sneak_forest_wolves",)), ("abandon", ("abandon_gald",))],
    "village_approach": [("careful", ("approach_burning_village_carefully",)),
                         ("direct", ("enter_burning_village_directly",))],
    "burning_house": [("leave", ("leave_burning_house",)), ("beam", ("break_burning_beam",)),
                      ("climb", ("climb_to_window",)), ("douse", ("douse_with_ice",))],
    "ice_elemental_encounter": [("fight", ("fight_ice_elemental",)), ("bypass", ("bypass_ice_elemental",))],
    "valley_entrance": [("fight", ("fight_ash_wraiths",)), ("sneak", ("sneak_through_ash",))],
    "valley_lava_bridge": [("bridge", ("cross_lava_bridge",)), ("ledge", ("take_ledge_path",))],
    "goblin_fort": [("fight", ("fight_fort_first_guard",)), ("bypass", ("fort_first_bypass",))],
    "goblin_fort_first_second": [("fight", ("fight_fort_second_guards",)), ("bypass", ("fort_second_bypass",))],
    "goblin_fort_second_choice": [("right", ("explore_fort_right",)),
                                  ("left", ("explore_fort_left", "use_fort_healing_circle"))],
    "goblin_fort_second_right": [("fight", ("fight_hobgoblin",)), ("bypass", ("bypass_hobgoblin",))],
    "goblin_fort_chest_choice": [("return", ("return_lost_goblin_box",)), ("steal", ("steal_lost_goblin_box",))],
    "cave_seal": [("decode", ("decode_seal",)), ("pray", ("pray_at_seal",)), ("force", ("force_seal",)),
                  ("holy_water", ("pour_holy_water_on_seal",))],
    "cave_heat_corridor": [("fight", ("fight_heat",)), ("sneak", ("sneak_heat",))],
    "cave_crystal_corridor": [("fight", ("fight_crystal",)), ("sneak", ("sneak_crystal",))],
}
# Fixed 021/022 route choice at each mainline node (hp70 reference).
BACKBONE = {"lost_goblin_crossroads": "ignore", "forest_wolves": "fight", "village_approach": "careful",
            "burning_house": "leave", "ice_elemental_encounter": "fight", "valley_entrance": "fight",
            "valley_lava_bridge": "bridge"}
# A side quest toggles which options exist; the method inside it is still chosen by value.
QUEST_SKIPS = {"gald": ("forest_wolves", {"abandon"}), "riku": ("burning_house", {"leave"})}
GIVE_UP = {"burning_house": "leave_burning_house", "cave_seal": "leave_seal"}
STUCK_FALLBACK = {**GIVE_UP, "forest_wolves": "fight_forest_wolves"}
FORT_LOCATIONS = {"goblin_fort", "goblin_fort_first_second", "goblin_fort_second_choice",
                  "goblin_fort_second_right", "goblin_fort_second_left", "goblin_fort_healing_circle",
                  "goblin_fort_third_gate", "goblin_fort_third_guards", "goblin_fort_fourth",
                  "goblin_fort_chest_choice", "goblin_fort_chest_fight"}


class Defeat(Exception):
    def __init__(self, location: str):
        super().__init__(location)
        self.location = location


class FixedDice:
    """Stand-in for state.random while enumerating a known die face."""

    def __init__(self, value: int):
        self.value = value

    def randint(self, low: int, high: int) -> int:
        return max(low, min(high, self.value))


def clone(session: dict[str, Any]) -> dict[str, Any]:
    pack = session["scenario_pack"]
    logs = {k: session.get(k) for k in ("event_log", "dice_log", "messages", "system_logs")}
    for key in logs:
        session[key] = []
    try:
        copy = deepcopy(session, {id(pack): pack})
    finally:
        session.update(logs)
    return copy


def available_actions(session: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Displayed, enabled actions at the current location (children flattened)."""
    def walk(choices: Iterable[dict[str, Any]]) -> Iterable[str]:
        for choice in choices:
            yield str(choice.get("id") or "")
            yield from walk(choice.get("children") or [])
    result = {}
    for action_id in walk(current_action_choices(session)):
        action = state.resolve_action(session, action_id=action_id) if action_id else None
        if action is not None and state.action_requirement_status(action, session)[0]:
            result[action_id] = action
    return result


def combat_pending(session: dict[str, Any]) -> bool:
    """Pure mirror of combat.ensure_combat_started's start conditions (consumes no RNG)."""
    if session.get("game_over") or (session.get("combat") or {}).get("status"):
        return False
    location = state.current_location_id(session)
    requested = bool(session.get("combat_start_requested"))
    if session.get("combat_blocked_location") == location and not requested:
        return False
    encounter = combat._encounter_for_session(session, session["scenario_pack"])
    if encounter.get("auto_start", True) is False and not requested:
        return False
    flags = session.get("flags", {})
    known = {e["id"] for e in session["scenario_pack"].get("enemies", [])}
    return any(e in known and not flags.get(combat._defeated_flag(e, location)) for e in encounter["enemy_ids"])


def _dice(expression: str) -> tuple[int, str]:
    match = state._DICE_ATTR_RE.match(expression)
    if not match:
        raise ValueError(f"Unsupported dice expression: {expression}")
    count, sides = state._parse_dice_expression(match.group(1))
    if count != 1:
        raise ValueError("Only single-die checks are modelled")
    return sides, expression


def check_distribution(session: dict[str, Any], expression: str, dc: int, *,
                       critical: bool = True, natural_one_fails: bool = False) -> dict[str, tuple[float, int]]:
    """P(outcome) for one die + full attribute value against dc, with a representative face per outcome."""
    sides, _ = _dice(expression)
    match = state._DICE_ATTR_RE.match(expression)
    modifier = match.group(3) or ""
    sign = -1 if match.group(2) == "-" else 1
    if modifier.isdigit():
        bonus = sign * int(modifier)
    elif modifier:
        attrs = state._normalize_attribute_map(session["character"].get("attributes", {}))
        bonus = sign * state._attr_value(attrs, state._canonical_attr_key(modifier))
    else:
        bonus = 0
    outcomes: dict[str, list[int]] = {}
    for face in range(1, sides + 1):
        if critical and face == sides:
            label = "critical_success"
        elif critical and face == 1:
            label = "critical_failure"
        elif natural_one_fails and face == 1:
            label = "failure"
        else:
            label = "success" if face + bonus >= dc else "failure"
        outcomes.setdefault(label, []).append(face)
    return {label: (len(faces) / sides, faces[0]) for label, faces in outcomes.items()}


def sneak_check(session: dict[str, Any], action: dict[str, Any]) -> Optional[tuple[str, int]]:
    """Displayed obstacle sneak: same dc rule as free_actions._adjudicate."""
    from host.free_actions import _obstacles, location_changes

    plan = action["free_action"]
    target = next((o for o in _obstacles(session) if o["id"] == plan["target_id"]), {})
    target_state = location_changes(session).get(target.get("id"), {})
    if not target or target_state.get("distracted"):
        return None
    dc = int(target.get("sneak_dc", 14)) + min(3, int(target_state.get("alertness", 0))) * 2
    return "1d20+dex", dc - int(target_state.get("prepared", {}).get("bonus", 0))


def outcome_faces(session: dict[str, Any], action: dict[str, Any]) -> list[tuple[float, Optional[int]]]:
    if action.get("free_action"):
        if action["free_action"].get("operation") == "sneak":
            check = sneak_check(session, action)
            if check:
                distribution = check_distribution(session, *check, critical=False, natural_one_fails=True)
                return list(distribution.values())
        return [(1.0, None)]
    dice, dc = state.action_dice_settings(action, session=session)
    if dc <= 0:
        return [(1.0, None)]
    return list(check_distribution(session, dice, dc, critical=action.get("critical_enabled") is not False).values())


def apply_action(session: dict[str, Any], action: dict[str, Any], face: Optional[int]) -> None:
    """Apply one action with a given die face; free actions read state.random (patched by caller)."""
    if action.get("free_action"):
        state.apply_action_result(session, action, {})
        return
    dice, dc = state.action_dice_settings(action, session=session)
    roll = state.roll_dice(session, dice, dc, client_rolls=[face]) if dc > 0 else {}
    state.apply_action_result(session, action, roll)


def item_pool(actor: dict[str, Any]) -> tuple[float, float]:
    """HP-equivalent of carried consumables (healing and damage), and MP restoration."""
    hp, mp = 0.0, 0.0
    for item in actor.get("inventory", []):
        spec = combat.item_combat_spec(item)
        if not spec or not spec.get("consumable", True):
            continue
        quantity = int(item.get("quantity", 1))
        if spec.get("kind") == "heal":
            amount = actor["max_hp"] * float(spec["max_hp_ratio"]) if "max_hp_ratio" in spec else \
                sim.formula_mean(str(spec.get("healing") or "10"), actor)
            hp += amount * quantity
        elif spec.get("kind") == "damage":
            hp += sim.formula_mean(str(spec.get("damage") or "1"), actor) * quantity
        elif spec.get("kind") == "restore" and spec.get("resource") == "mp":
            mp += sim.formula_mean(str(spec.get("amount") or "0"), actor) * quantity
    return hp, mp


def resource_score(session: dict[str, Any]) -> float:
    """0 when dead; otherwise mean of HP(+item pool)/MP/SP fractions of their maxima."""
    actor = session["character"]
    if session.get("game_over") or actor.get("hp", 0) <= 0:
        return 0.0
    hp_items, mp_items = item_pool(actor)
    parts = [(actor["hp"] + hp_items) / max(1, actor["max_hp"])]
    if actor.get("max_mp", 0) > 0:
        parts.append((actor["mp"] + mp_items) / actor["max_mp"])
    if actor.get("max_sp", 0) > 0:
        parts.append(actor["sp"] / actor["max_sp"])
    return mean(parts)


def visible_key(session: dict[str, Any]) -> str:
    """Everything a player can see that affects the estimate; never RNG state."""
    actor = session["character"]
    location = state.current_location_id(session)
    return json.dumps(dict(
        location=location, character=actor.get("character_id"), level=actor.get("level"),
        resources=[actor.get(k) for k in ("hp", "mp", "sp", "max_hp", "max_mp", "max_sp")],
        attributes=actor.get("attributes"), equipment=actor.get("equipment"),
        inventory=sorted((i["name"], i.get("quantity", 1)) for i in actor.get("inventory", [])),
        skills=sorted(str(s.get("id") or s.get("name")) for s in actor.get("skills", [])),
        companion=session.get("companion"), flags=sorted(k for k, v in session.get("flags", {}).items() if v),
        requested=[bool(session.get("combat_start_requested")), bool(session.get("enemy_first_requested"))],
        changes=session.get("scene_changes", {}).get(location)), sort_keys=True, ensure_ascii=False, default=str)


def stable_seed(*parts: Any) -> int:
    text = "\x1f".join(str(p) for p in parts).encode()
    return int.from_bytes(hashlib.sha256(text).digest()[:8], "big")


def node_options(session: dict[str, Any], node: str, quests: frozenset[str]) -> list[tuple[str, tuple[str, ...]]]:
    actions = available_actions(session)
    options = [(name, macro) for name, macro in NODES[node] if macro[0] in actions
               and not ((actions[macro[0]].get("free_action") or {}).get("operation") == "sneak"
                        and session["character"].get("sp", 0) < 1)]
    for quest, (quest_node, skips) in QUEST_SKIPS.items():
        if quest_node != node:
            continue
        if quest in quests:
            kept = [o for o in options if o[0] not in skips]
            options = kept or options
        else:
            kept = [o for o in options if o[0] in skips]
            options = kept or options
    if node in GIVE_UP:
        # Retryable checks with a way out: do not attempt one whose failure would drop HP to 0.
        hp = session["character"]["hp"]
        safe = [o for o in options if hp + failure_hp_change(actions[o[1][0]]) > 0]
        options = safe if safe else []
    return options


def risky(session: dict[str, Any], macro: tuple[str, ...]) -> bool:
    action = available_actions(session).get(macro[0], {})
    effects = [*(action.get("effects") or []), *(action.get("success_effects") or [])]
    return bool(action.get("roll") or (action.get("free_action") or {}).get("operation") == "sneak"
                or any(isinstance(e, dict) and e.get("start_combat") for e in effects))


def best_option(values: dict[str, float], options: dict[str, tuple[str, ...]], session: dict[str, Any]) -> str:
    """Highest value; exact ties go to an option without a check or combat, then to listing order."""
    top = max(values.values())
    tied = [name for name in options if name in values and values[name] >= top - 1e-9]
    return next((name for name in tied if not risky(session, options[name])), tied[0])


def failure_hp_change(action: dict[str, Any]) -> int:
    effects = action.get("failure_effects") or []
    return sum(int(e.get("hp_change", 0)) for e in effects if isinstance(e, dict))


class Evaluator:
    """Expected value of an option = E[alive x resource_score] after the node, per visible state.

    Checks enumerate die faces (P(1d20+attribute >= DC)); combats are estimated with the existing
    heuristic simulator from the current resources using an RNG seeded only by the visible state.
    """

    def __init__(self, quests: Iterable[str] = (), *, n: Optional[int] = None, policy: str = "heuristic",
                 depth: Optional[int] = None):
        self.quests = frozenset(quests)
        self.n = ESTIMATE_N if n is None else n
        self.depth = EVAL_DEPTH if depth is None else depth
        self.policy = policy
        self.combat_cache: dict[tuple, float] = {}
        self.decision_cache: dict[tuple, dict[str, float]] = {}

    def values(self, session: dict[str, Any], node: str) -> dict[str, float]:
        key = (node, visible_key(session))
        if key not in self.decision_cache:
            with patch.object(combat, "random", random.Random(0)), patch.object(state, "random", FixedDice(1)):
                result = {}
                for name, macro in node_options(session, node, self.quests):
                    value = self.option_value(session, node, macro, self.depth)
                    if value is not None:
                        result[name] = value
            self.decision_cache[key] = result
        return dict(self.decision_cache[key])

    def option_value(self, session: dict[str, Any], node: str, macro: tuple[str, ...], depth: int) -> Optional[float]:
        action = available_actions(session).get(macro[0])
        if action is None:
            return None
        total = 0.0
        for probability, face in outcome_faces(session, action):
            copy = clone(session)
            with patch.object(state, "random", FixedDice(face or 1)):
                apply_action(copy, action, face)
            total += probability * self.after_value(copy, node, macro[1:], depth)
        return total

    def after_value(self, session: dict[str, Any], node: str, rest: tuple[str, ...], depth: int) -> float:
        if session.get("game_over") or session["character"].get("hp", 0) <= 0:
            return 0.0
        if combat_pending(session):
            return self.combat_value(session, rest)
        if rest:
            rng = random.Random(stable_seed(visible_key(session), rest))
            with patch.object(combat, "random", rng), patch.object(state, "random", rng):
                try:
                    play(session, rest, rng, self.policy)
                except Defeat:
                    return 0.0
        if state.current_location_id(session) == node:
            # Still blocked: re-decide; past the lookahead an unresolved node is worth nothing.
            if depth <= 0:
                return 0.0
            values = [v for v in (self.option_value(session, node, macro, depth - 1)
                                  for _, macro in node_options(session, node, self.quests)) if v is not None]
            return max(values, default=0.0)
        return resource_score(session)

    def combat_value(self, session: dict[str, Any], rest: tuple[str, ...] = ()) -> float:
        key = (visible_key(session), rest)
        if key not in self.combat_cache:
            from . import route

            rng = random.Random(stable_seed(*key))
            total = 0.0
            with patch.object(combat, "random", rng), patch.object(state, "random", rng):
                for _ in range(self.n):
                    copy = clone(session)
                    try:
                        resolve(copy, rng, self.policy, route.fight)
                        play(copy, rest, rng, self.policy)
                    except Defeat:
                        continue
                    total += resource_score(copy)
            self.combat_cache[key] = total / self.n
        return self.combat_cache[key]


def resolve(session: dict[str, Any], rng: random.Random, policy: str, fight, battles: Optional[list] = None) -> None:
    while combat_pending(session):
        battle = fight(session, policy, rng)
        if battles is not None:
            battles.append(battle)
        if not battle["continue"]:
            raise Defeat(battle["encounter"])


def act(session: dict[str, Any], action_id: str, rng: random.Random, *, forced: bool = False) -> dict[str, Any]:
    action = available_actions(session).get(action_id)
    if action is None:
        raise ValueError(f"Unavailable action: {state.current_location_id(session)}/{action_id}")
    if action.get("free_action"):
        state.apply_action_result(session, action, {})
        return action
    dice, dc = state.action_dice_settings(action, session=session)
    if dc <= 0:
        roll: dict[str, Any] = {}
    elif forced:
        roll = {"dc": dc, "success": True}
    else:
        roll = state.roll_dice(session, dice, dc, client_rolls=[rng.randint(1, _dice(dice)[0])])
    state.apply_action_result(session, action, roll)
    return action


def play(session: dict[str, Any], actions: Iterable[str], rng: random.Random, policy: str) -> None:
    from . import route

    for action_id in actions:
        act(session, action_id, rng)
        resolve(session, rng, policy, route.fight)


def resources(session: dict[str, Any]) -> dict[str, Any]:
    from . import route

    return route.resources(session)


class Run:
    def __init__(self, pack: dict[str, Any], prelude: list[str], character: str, seed: int, *,
                 quests: Iterable[str] = (), decisions: str = "class_aware", dice: str = "real",
                 policy: str = "heuristic", rest_policy: str = "hp70", evaluator: Optional[Evaluator] = None):
        if decisions not in {"class_aware", "backbone"} or dice not in {"real", "forced"}:
            raise ValueError("unknown decision or dice mode")
        self.session = checkpoints.fresh_session(pack, character)
        self.rng = random.Random(seed)
        self.prelude, self.policy, self.rest_policy = prelude, policy, rest_policy
        self.quests = frozenset(quests)
        if decisions == "backbone" and self.quests:
            raise ValueError("backbone route has no side quests")
        self.decisions, self.dice = decisions, dice
        self.evaluator = evaluator or (Evaluator(self.quests, policy=policy) if decisions == "class_aware" else None)
        self.battles: list[dict[str, Any]] = []
        self.rests: list[dict[str, Any]] = []
        self.choices: list[dict[str, Any]] = []
        self.arrival: Optional[dict[str, Any]] = None

    @property
    def location(self) -> str:
        return state.current_location_id(self.session)

    def act(self, action_id: str, *, settle: bool = True) -> None:
        from . import route

        forced = self.dice == "forced" and action_id != "cross_lava_bridge"
        act(self.session, action_id, self.rng, forced=forced)
        if settle:
            resolve(self.session, self.rng, self.policy, route.fight, self.battles)

    def rest_point(self) -> None:
        from . import route

        if self.rest_policy != "hp70":
            return
        location = self.location
        while rest := route.rest_if_needed(self.session):
            self.rests.append(rest)
            while self.location != location:
                battle = route.fight(self.session, self.policy, self.rng)
                self.battles.append(battle)
                if not battle["continue"]:
                    raise Defeat(battle["encounter"])

    def decide(self, node: str) -> None:
        for _ in range(MAX_NODE_DECISIONS):
            if self.location != node:
                return
            if self.decisions == "backbone":
                actions = available_actions(self.session)
                options = {name: macro for name, macro in NODES[node] if macro[0] in actions}
            else:
                options = dict(node_options(self.session, node, self.quests))
            if not options:
                break
            values: dict[str, float] = {}
            if self.decisions == "backbone":
                name = BACKBONE[node]
            elif len(options) == 1:
                name = next(iter(options))
            else:
                values = self.evaluator.values(self.session, node)
                name = best_option(values, options, self.session)
            self.choices.append(dict(node=node, option=name, values=values))
            for action_id in options[name]:
                self.act(action_id)
        if self.location == node:
            fallback = STUCK_FALLBACK.get(node)
            if not fallback:
                raise ValueError(f"Stuck at {node}")
            self.choices.append(dict(node=node, option="give_up", values={}))
            self.act(fallback)

    def play(self) -> None:
        for step in self.prelude:
            checkpoints.replay_step(self.session, step)
        self.act("go_dark_forest")
        self.act("attack_slime")
        if "fort" in self.quests:
            self.act("help_lost_goblin")
            self.act("enter_goblin_fort")
            self.fort()
            self.act("crossroads_forward")
        else:
            self.decide("lost_goblin_crossroads")
        self.rest_point()
        self.act("continue_from_elf_spring")
        self.decide("forest_wolves")
        if self.quests & {"cave_chest", "cave_full"}:
            for step in ("exit_back", "wolves_back"):
                self.act(step)
            self.rest_point()
            self.cave()
            self.rest_point()
            self.act("continue_from_elf_spring")
            self.act("pass_cleared_wolves")
        self.town_trip()
        self.act("leave_forest_for_village")
        self.decide("village_approach")
        self.decide("burning_house")
        self.act("visit_village")
        self.rest_point()
        if "return_riku" in available_actions(self.session):
            self.act("return_riku")
        self.act("return_frozen_clue")
        self.act("investigate_frozen_village")
        self.decide("ice_elemental_encounter")
        self.act("accept_ian_request")
        self.decide("valley_entrance")
        self.decide("valley_lava_bridge")
        while self.location == "warlock_at_nest":
            self.act("continue_after_warlock")
        self.act("enter_dragon_nest", settle=False)
        self.arrival = resources(self.session)
        from . import route

        battle = route.fight(self.session, self.policy, self.rng)
        self.battles.append(battle)
        if not battle["continue"]:
            raise Defeat(battle["encounter"])

    def fort(self) -> None:
        for _ in range(20):
            location = self.location
            if location not in FORT_LOCATIONS:
                return
            if location in NODES:
                self.decide(location)
            elif location == "goblin_fort_healing_circle":
                self.act("use_fort_healing_circle")
            elif location == "goblin_fort_third_gate":
                self.act("give_correct_password")
            else:
                raise ValueError(f"Unexpected fort location: {location}")
        raise ValueError("Fort did not finish")

    def cave(self) -> None:
        self.act("inspect_spring_wall")
        self.decide("cave_seal")
        if self.location != "cave_heat_corridor":
            return
        self.decide("cave_heat_corridor")
        self.act("cave_left")
        self.act("open_lava_chest")
        self.act("lava_back")
        if "cave_full" in self.quests:
            self.act("cave_right")
            self.rest_point()
            self.act("hot_spring_forward")
            self.decide("cave_crystal_corridor")
            self.act("leave_prism_tree")
        else:
            for step in ("fork_back", "heat_back", "leave_seal"):
                self.act(step)

    def town_trip(self) -> None:
        inventory = {i["name"] for i in self.session["character"]["inventory"]}
        errands = [steps for item, steps in (
            ("刻印のハンマー", ("go_forge", "return_robert_hammer", "return_castle_from_forge")),
            ("虹晶の欠片", ("go_magic_shop", "forge_prism_weapon", "return_castle_from_magic_shop")))
            if item in inventory]
        if not errands:
            return
        self.act("return_inn_after_forest")
        self.act("go_inn")
        self.rest_point()
        self.act("return_castle_from_inn")
        for steps in errands:
            for step in steps:
                self.act(step)
        self.act("go_inn")
        self.rest_point()
        self.act("return_castle_from_inn")
        self.act("return_forest_exit")

    def result(self, failed_at: Optional[str]) -> dict[str, Any]:
        return {"completed": failed_at is None, "failed_at": failed_at, "boss_arrival": self.arrival,
                "battles": self.battles, "paid_rests": sum(r["cost"] > 0 for r in self.rests),
                "rests": self.rests, "choices": self.choices, "quests": sorted(self.quests),
                "ending": (self.session.get("game_over") or {}).get("ending")}


def prelude_steps(cp: dict[str, Any], character: str, encounter: str = "dragon_valley_loc") -> list[str]:
    steps = [s["step"] for s in cp["encounters"][encounter]["characters"][character]["sources"]]
    return steps[:next(i for i, step in enumerate(steps) if step.split(":")[0] == "go_dark_forest")]


def trial(pack: dict[str, Any], cp: dict[str, Any], character: str, seed: int, **kwargs: Any) -> dict[str, Any]:
    run = Run(pack, prelude_steps(cp, character), character, seed, **kwargs)
    with patch.object(combat, "random", run.rng), patch.object(state, "random", run.rng):
        try:
            run.play()
        except Defeat as defeat:
            return run.result(defeat.location)
    return run.result(None)


def load_quests(path: Path = QUESTS_PATH) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))["selected"]


def choice_stats(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    decisions: dict[str, Counter] = {}
    trials: dict[str, Counter] = {}
    for result in results:
        first: dict[str, str] = {}
        for choice in result.get("choices", []):
            decisions.setdefault(choice["node"], Counter())[choice["option"]] += 1
            first.setdefault(choice["node"], choice["option"])
        for node, option in first.items():
            trials.setdefault(node, Counter())[option] += 1
    return {"decisions": {k: dict(v) for k, v in sorted(decisions.items())},
            "first_choice_per_trial": {k: dict(v) for k, v in sorted(trials.items())}}


def _route_job(args: tuple) -> dict[str, Any]:
    from . import route

    character, n, seed, rest_policy, quests, decisions, dice = args
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    row = route.simulate_route(pack, cp, character, n=n, seed=seed, rest_policy=rest_policy,
                               quests=quests, decisions=decisions, dice=dice)
    row.pop("sample_trial", None)
    return row


def run_jobs(jobs: list[tuple], workers: int) -> list[dict[str, Any]]:
    if workers <= 1:
        return [_route_job(job) for job in jobs]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_route_job, jobs))


def _pilot_job(args: tuple) -> dict[str, Any]:
    character, quests, n, seed, shard, shards = args
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding="utf-8"))
    evaluator = Evaluator(quests)
    completed, failures = 0, Counter()
    for index in range(shard, n, shards):
        result = trial(pack, cp, character, sim.trial_seed(seed, "dragon_valley_loc", character, index),
                       quests=quests, evaluator=evaluator)
        completed += result["completed"]
        if result["failed_at"]:
            failures[result["failed_at"]] += 1
    return dict(character=character, quests=list(quests), completed=completed, failures=dict(failures))


def pilot(configs: dict[str, tuple[str, ...]], n: int, seed: int, workers: int, shards: int) -> dict[str, dict[str, Any]]:
    jobs = [(c, quests, n, seed, shard, shards) for c, quests in configs.items() for shard in range(shards)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        parts = list(pool.map(_pilot_job, jobs))
    rows: dict[str, dict[str, Any]] = {}
    for part in parts:
        row = rows.setdefault(part["character"], dict(completed=0, failures=Counter()))
        row["completed"] += part["completed"]
        row["failures"].update(part["failures"])
    return {c: dict(completion_rate=r["completed"] / n, failure_counts=dict(r["failures"])) for c, r in rows.items()}


def select_quests(characters: list[str], n: int, seed: int, workers: int, shards: int = 6) -> dict[str, Any]:
    """Greedy per-class side quest adoption: keep a quest when completion drops by < 2pp."""
    current: dict[str, tuple[str, ...]] = {c: () for c in characters}
    base = pilot(current, n, seed, workers, shards)
    log = [dict(step="base", character=c, quests=[], **base[c]) for c in characters]
    print("base", {c: base[c]["completion_rate"] for c in characters}, flush=True)
    for quest in QUEST_ORDER:
        candidates = {}
        for c in characters:
            quests = [q for q in current[c] if not (quest == "cave_full" and q == "cave_chest")] + [quest]
            candidates[c] = tuple(q for q in QUEST_ORDER if q in quests)
        rows = pilot(candidates, n, seed, workers, shards)
        for c in characters:
            loss = base[c]["completion_rate"] - rows[c]["completion_rate"]
            adopted = loss < QUEST_LOSS_LIMIT - 1e-12
            log.append(dict(step=quest, character=c, quests=list(candidates[c]),
                            reference_quests=list(current[c]), reference_rate=base[c]["completion_rate"],
                            loss=loss, adopted=adopted, **rows[c]))
            if adopted:
                current[c], base[c] = candidates[c], rows[c]
        print(quest, {c: (rows[c]["completion_rate"], current[c]) for c in characters}, flush=True)
    return {"n": n, "seed": seed, "loss_limit": QUEST_LOSS_LIMIT, "order": list(QUEST_ORDER),
            "selected": {c: list(q) for c, q in current.items()}, "log": log}


def report(characters: list[str], n: int, seed: int, workers: int, quests: dict[str, list[str]]) -> dict[str, Any]:
    configs = [("none", "none", (), "backbone", "forced"), ("hp70", "hp70", (), "backbone", "forced"),
               ("class_aware", "class_aware", None, "class_aware", "real"),
               ("hp70_real_dice", "class_aware", (), "backbone", "real"),
               ("class_aware_no_quests", "class_aware", (), "class_aware", "real")]
    jobs, labels = [], []
    for label, rest_policy, quest_set, decisions, dice in configs:
        for c in characters:
            selected = tuple(quests.get(c, ())) if quest_set is None else quest_set
            jobs.append((c, n, seed, rest_policy, selected, decisions, dice))
            labels.append(label)
    rows = run_jobs(jobs, workers)
    for label, row in zip(labels, rows):
        row["policy_label"] = label
    return {"n": n, "seed": seed, "quests": quests, "rows": rows}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="027 class-aware continuous route (offline)")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--characters", nargs="+", default=["hero", "cleric", "mage", "thief"])
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--shards", type=int, default=6, help="Pilot shards per class")
    parser.add_argument("--select-quests", action="store_true",
                        help="Run the greedy side quest pilot and write --output (use a seed other than the report's)")
    parser.add_argument("--quests", type=Path, default=QUESTS_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.n < 1 or args.workers < 1:
        parser.error("invalid n or workers")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    paths = [checkpoints.DEFAULT_SCENARIO, checkpoints.DEFAULT_CHECKPOINTS, Path(__file__),
             Path(sim.__file__), Path(__file__).with_name("route.py")]
    if args.select_quests:
        result = select_quests(args.characters, args.n, args.seed, args.workers, args.shards)
    else:
        result = report(args.characters, args.n, args.seed, args.workers, load_quests(args.quests))
        paths.append(args.quests)
    result["fingerprints"] = {p.relative_to(checkpoints.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in paths if p.exists()}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
