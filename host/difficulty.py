"""Difficulty overlays: base values are frozen baby values; do not rebalance them.

Balance normal by appending {entity, id, path, set/add/mul} entries to
pack["difficulty_overlays"]["normal"] in BOTH packs, and bump content_revision.
NUMERIC_FIELDS is the single numeric path whitelist (* matches one component).
Add new numeric paths here; existing patterns cover new records automatically.
EXP tables use ID-keyed objects or records with IDs, never array positions.
Records with difficulty_only are recursively filtered from effective packs.
Normal-only records carry their normal numeric values in the base pack; 052
may tune those records directly. They are absent from the effective baby pack.
MECHANIC_FIELDS is a separate entity/path -> allowed-values whitelist, empty
until a design spec authorizes difficulty-changing rules. Only these fields
may be created with set, and their parent must already exist.

Top-level entities use their ID; singleton objects (combat_rules, npc_combat,
progression, exp_table) use id="$". Nested list paths use @id=..., @item_id=...,
or @name=... (percent-encoded). Anonymous legacy effects use @shape=<sha256>
of their nonnumeric structure. numeric_snapshot exposes all valid addresses.
Ambiguous selectors fail; never use array indexes. Repeated destinations warn
and execute sequentially; repository tests promote warnings to errors.

apply_difficulty takes a BASE pack and returns a deep copy. Do not apply it to
an already effective session snapshot. Old saves are baby and retain their
snapshot until a later content_revision is loaded. Every overlay change MUST
bump content_revision; overlay_revision.json guards the recorded baseline.
Update that overlay manifest with the new hash/revision (not the baby freeze).
Tests also compare the Git base so updating the manifest alone cannot hide a
missing revision bump.

baby_numeric_freeze.json is under host/prompt/processed/difficulty/ because
of the 047 retry brief. Balance specs must NOT update it. Only an explicit
"adjust baby" task may change it; adding shared numeric fields requires an
explicit snapshot update and an explanation in the commit. Freeze tests also
audit numeric leaves outside the whitelist so new fields cannot go unnoticed.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import warnings
from copy import deepcopy
from typing import Any, Iterator
from urllib.parse import quote

NUMERIC_FIELDS: dict[str, tuple[str, ...]] = {
    'combat_rules': (
        'basic_attack.accuracy',
        'basic_attack.damage',
        'defend_multiplier',
        'enemy_basic_attack.accuracy',
        'enemy_basic_attack.damage',
        'flee_dc',
        'flee_formula',
        'max_rounds',
        'sp_regen_per_round',
    ),
    'locations': (
        'actions.*.children.*.effects.*.add_item.quantity',
        'actions.*.children.*.roll.dc',
        'actions.*.children.*.roll.dice_type',
        'actions.*.critical_failure_effects.*.hp_change',
        'actions.*.effects.*.add_item.quantity',
        'actions.*.effects.*.attribute_set.*',
        'actions.*.effects.*.branch.else.*.add_item.quantity',
        'actions.*.effects.*.branch.else.*.mp_change',
        'actions.*.effects.*.branch.then.*.add_item.quantity',
        'actions.*.effects.*.branch.then.*.branch.else.*.add_item.combat.accuracy',
        'actions.*.effects.*.branch.then.*.branch.else.*.add_item.combat.damage',
        'actions.*.effects.*.branch.then.*.branch.else.*.add_item.combat.skill_healing_bonus',
        'actions.*.effects.*.branch.then.*.branch.else.*.add_item.quantity',
        'actions.*.effects.*.branch.then.*.branch.then.*.add_item.combat.accuracy',
        'actions.*.effects.*.branch.then.*.branch.then.*.add_item.combat.damage',
        'actions.*.effects.*.branch.then.*.branch.then.*.add_item.combat.skill_healing_bonus',
        'actions.*.effects.*.branch.then.*.branch.then.*.add_item.quantity',
        'actions.*.effects.*.branch.then.*.gold_change',
        'actions.*.effects.*.branch.then.*.remove_item.quantity',
        'actions.*.effects.*.gold_change',
        'actions.*.effects.*.reforge_armor.defense_bonus',
        'actions.*.effects.*.remove_item.quantity',
        'actions.*.effects.*.restore_ratio',
        'actions.*.failure_effects.*.gold_change',
        'actions.*.failure_effects.*.hp_change',
        'actions.*.failure_effects.*.sp_change',
        'actions.*.roll.dc',
        'actions.*.roll.dice_type',
        'actions.*.roll_bonuses.*.total_gte',
        'actions.*.success_effects.*.add_item.quantity',
        'actions.*.success_effects.*.gold_change',
        'actions.*.success_effects.*.hp_change',
        'actions.*.success_effects.*.sp_change',
        'combat.defeat_effects.hp',
        'combat.defeat_effects.inventory_remove.*.quantity',
        'combat.encounter_modifiers.*.basic_followup.accuracy',
        'combat.encounter_modifiers.*.basic_followup.damage',
        'combat.encounter_modifiers.*.damage_multiplier',
        'combat.encounter_modifiers.*.enemy_defense',
        'combat.encounter_modifiers.*.enemy_hp_multiplier',
        'combat.encounter_modifiers.*.enemy_skip_rounds',
        'combat.encounter_modifiers.*.received_multiplier',
        'combat.encounter_modifiers.*.round_start_attack.accuracy',
        'combat.encounter_modifiers.*.round_start_attack.damage',
        'combat.flee_dc',
        'combat.one_time_reward.items.*.quantity',
        'combat.phase_allies.*.round_start_effects.*.damage',
        'combat.special_actions.*.cost',
        'combat.special_actions.*.enemy_hp_ratio_lte',
        'combat.start_grant.items.*.quantity',
        'combat.victory_effects.*.branch.else.*.add_item.quantity',
        'combat.victory_effects.*.remove_item.quantity',
        'combat.victory_effects.gold_change',
        'combat.victory_effects.inventory_add.*.quantity',
        'combat.victory_effects_by_character.mage.inventory_remove.*.quantity',
        'combat.victory_gold_bonus',
        'combat.victory_reward.items.*.quantity',
        'hybrid.prepared_turns.*.draft.choices.*.requirements.all.*.gold_gte',
        'hybrid.prepared_turns.*.draft.choices.*.requirements.gold_gte',
        'hybrid.prepared_turns.*.draft.dice_dc',
        'hybrid.prepared_turns.*.draft.dice_type',
        'hybrid.prepared_turns.*.draft.state_delta.gold_change',
        'hybrid.prepared_turns.*.draft.state_delta.hp_change',
        'hybrid.prepared_turns.*.draft.state_delta.inventory_add.*.quantity',
        'hybrid.prepared_turns.*.draft.state_delta.inventory_remove.*.quantity',
        'hybrid.prepared_turns.*.draft.state_delta.mp_change',
        'hybrid.prepared_turns.*.draft.state_delta.sp_change',
        'objects.*.observe_reveals.roll.dc',
        'objects.*.observe_reveals.roll.dice_type',
        'objects.*.observe_reveals.success_effects.*.add_item.quantity',
        'objects.*.observe_reveals.success_effects.*.gold_change',
        'obstacles.*.sneak_dc',
        'opening_effects.*.add_item.quantity',
        'opening_effects.*.gold_change',
    ),
    'npcs': (
        'npc_combat.fallen_effects.*.branch.then.*.remove_item.quantity',
        'npc_combat.guardians.*.count',
    ),
    'items': (
        'combat.accuracy',
        'combat.amount',
        'combat.attribute',
        'combat.basic_attack_followup.accuracy',
        'combat.basic_attack_followup.damage',
        'combat.chance',
        'combat.conditional_defense.amount',
        'combat.damage',
        'combat.damage_multiplier',
        'combat.damage_taken_multipliers.*',
        'combat.defense',
        'combat.extra_actions_per_round',
        'combat.grants_skills.*.accuracy',
        'combat.grants_skills.*.check.dc',
        'combat.grants_skills.*.check.formula',
        'combat.grants_skills.*.cost',
        'combat.grants_skills.*.damage',
        'combat.healing',
        'combat.healing_multiplier',
        'combat.max_hp_ratio',
        'combat.on_hit_status.damage',
        'combat.self_damage',
        'combat.skill_healing_bonus',
        'sell_price',
    ),
    'enemies': (
        'attributes.*',
        'combat.basic_attack.accuracy',
        'combat.basic_attack.damage',
        'combat.basic_attack.damage_multiplier',
        'combat.basic_attack.on_hit_status.accuracy_penalty',
        'combat.basic_attack.on_hit_status.damage',
        'combat.basic_attack.on_hit_status.remaining_rounds',
        'combat.defense',
        'combat.evade',
        'hp',
        'loot.quantity',
        'max_hp',
        'max_mp',
        'max_sp',
        'mp',
        'resistance_cycle.every',
        'resistance_cycle.phases.*.resistances.*',
        'resistances.*',
        'rewards.gold',
        'rewards.items.*.quantity',
        'skills.*.accuracy',
        'skills.*.ai_weight',
        'skills.*.auto_trigger_below_hp_ratio',
        'skills.*.cost',
        'skills.*.damage',
        'skills.*.damage_multiplier',
        'skills.*.dice_type',
        'skills.*.duration',
        'skills.*.every_n_rounds',
        'skills.*.guard_multiplier',
        'skills.*.healing',
        'skills.*.healing_multiplier_below_hp_ratio',
        'skills.*.hits',
        'skills.*.hits_per_element',
        'skills.*.low_hp_multiplier',
        'skills.*.max_uses_per_battle',
        'skills.*.on_hit_status.damage',
        'skills.*.on_hit_status.remaining_rounds',
        'skills.*.round_damage',
        'skills.*.use_below_hp_ratio',
        'skills.*.use_on_round',
        'sp',
    ),
    'attribute_defs': (
        'initial_value',
    ),
    'characters': (
        'attributes.*',
        'combat.basic_attack.accuracy',
        'combat.basic_attack.damage',
        'combat.defense',
        'combat.evade',
        'gold',
        'hp',
        'inventory.*.combat.accuracy',
        'inventory.*.combat.cost_reduction.*',
        'inventory.*.combat.damage',
        'inventory.*.combat.defense',
        'inventory.*.combat.skill_damage_bonus',
        'inventory.*.combat.skill_healing_bonus',
        'inventory.*.quantity',
        'level_skills.*.accuracy',
        'level_skills.*.cost',
        'level_skills.*.damage',
        'level_skills.*.guard_multiplier',
        'level_skills.*.healing',
        'level_skills.*.unlock_level',
        'max_hp',
        'max_mp',
        'max_sp',
        'mp',
        'resistances.*',
        'skills.*.accuracy',
        'skills.*.cost',
        'skills.*.damage',
        'skills.*.dice_type',
        'skills.*.guard_multiplier',
        'skills.*.healing',
        'skills.*.hits_per_element',
        'sp',
    ),
    'companions': (
        'round_start_effects.*.amount',
        'round_start_effects.*.damage',
        'round_start_effects.*.every_n_rounds',
        'round_start_effects.*.max_hp_ratio',
        'round_start_effects.*.multiplier',
        'round_start_effects.*.requirements.player_hp_ratio_gte',
        'round_start_effects.*.requirements.player_hp_ratio_lt',
    ),
    'milestones': (
        'gains.cleric.attributes.*',
        'gains.cleric.max_hp',
        'gains.cleric.max_mp',
        'gains.cleric.max_sp',
        'gains.hero.attributes.*',
        'gains.hero.max_hp',
        'gains.hero.max_mp',
        'gains.hero.max_sp',
        'gains.mage.attributes.*',
        'gains.mage.max_hp',
        'gains.mage.max_mp',
        'gains.mage.max_sp',
        'gains.thief.attributes.*',
        'gains.thief.max_hp',
        'gains.thief.max_mp',
        'gains.thief.max_sp',
        'level',
    ),
    'shops': (
        'counter_gold',
        'discount.multiplier',
        'items.*.price',
        'items.*.stock',
    ),
    'npc_combat': (
        'dragon_encounter.defeat_effects.hp',
        'dragon_encounter.victory_effects.gold_change',
        'dragon_encounter.victory_effects.inventory_add.*.quantity',
    ),
}
NON_BALANCE_FIELDS = ('locations.*.actions.*.failure_effects.*.branch.requirements.gold_lte', 'locations.*.actions.*.requirements.all.*.gold_gte', 'locations.*.actions.*.requirements.all.*.item_quantity_gte', 'locations.*.actions.*.requirements.any.*.all.*.mp_gte', 'locations.*.actions.*.requirements.any.*.flags_count_gte.count', 'locations.*.actions.*.requirements.gold_gte', 'locations.*.actions.*.visible_requirements.item_quantity_gte', 'locations.*.choices.*.requirements.all.*.gold_gte', 'locations.*.choices.*.requirements.all.*.item_quantity_gte', 'locations.*.choices.*.requirements.gold_gte', 'locations.*.choices.*.visible_requirements.item_quantity_gte', 'maps.*.nodes.*.x', 'maps.*.nodes.*.y', 'shops.*.items.*.requirements.all.*.attribute', 'shops.*.items.*.requirements.all.*.gte')

# Future EXP/level fields are opt-in by structural name, not by current values.
for _group in ("characters", "enemies", "milestones"):
    NUMERIC_FIELDS[_group] += ("exp", "xp", "level", "max_level", "exp_to_next_level",
                               "rewards.exp", "rewards.xp", "exp_table.*", "xp_table.*")
NUMERIC_FIELDS["progression"] = ("max_level", "exp_table.*", "xp_table.*", "levels.*.exp", "levels.*.xp")
NUMERIC_FIELDS["exp_table"] = ("*", "level", "exp", "xp", "required_exp")
NUMERIC_FIELDS["items"] += (
    "price", "buy_price", "effect.amount", "effect.damage", "effect.healing",
    "effect.accuracy", "effect.cost", "effect.multiplier",
)
NUMERIC_FIELDS["locations"] += (
    "actions.*.roll.dc_overrides.*.dc", "actions.*.children.*.roll.dc_overrides.*.dc",
    "objects.*.observe_reveals.roll.dc_overrides.*.dc",
    "actions.*.roll_bonuses.*.effects.*.hp_change",
    "actions.*.roll_bonuses.*.effects.*.mp_change",
    "actions.*.roll_bonuses.*.effects.*.sp_change",
    "actions.*.roll_bonuses.*.effects.*.gold_change",
)
MECHANIC_FIELDS: dict[str, dict[str, tuple[Any, ...]]] = {
    "combat_rules": {
        "evade_model": ("fixed", "dex"),
        "evade_formula": ({"base": 4, "per_dex": 1.5, "cap": 20},),
        "enemy_accuracy_override": (None, 100),
    },
    "characters": {"skills.*.cooldown": (1,)},
    "items": {"combat.requires_target_weakness": ("ice",)},
    "companions": {"round_start_effects.*.scale_from_damage": (
        {"source": "previous_damage_enemy", "ratio": 0.75},
        {"source": "previous_damage_enemy", "ratio": 1.5},
    )},
}
MECHANIC_FIELDS["progression"] = {key: () for key in
                                ("level_model", "max_level", "exp_table", "exp_rewards", "level_gains")}
MECHANIC_FIELDS["characters"].update({"skills.*.conditional_bonus": (), "skills.*.spell_tier": ("basic",)})
NUMERIC_FIELDS["progression"] += ("exp_rewards.*", "level_gains.*.max_hp", "level_gains.*.max_mp",
                                 "level_gains.*.max_sp", "level_gains.*.attributes.*")
_SKILL_NUMBERS = (
    "cost", "costs.*", "accuracy", "damage", "healing", "amount", "cooldown", "hits_per_element",
    "max_hits", "max_uses_per_battle", "conditional_bonus.*.ratio", "conditional_bonus.*.damage",
    "conditional_multipliers.*.x", "conditional_multipliers.*.ratio", "conditional_multipliers.*.conditions.*.value",
    "on_hit_status.duration", "on_hit_status.stacks", "overflow_shield.max_hp_ratio",
    "self_status.duration", "self_status.modifiers.*", "self_status.*.modifiers.*",
)
NUMERIC_FIELDS["characters"] += tuple("skills.*." + p for p in ("conditional_bonus.*.ratio", "conditional_bonus.*.damage"))
NUMERIC_FIELDS["items"] += tuple("learn_skill." + p for p in _SKILL_NUMBERS)
NUMERIC_FIELDS["class_progression"] = (
    "actives.*.level", "passive_groups.*.level", "passives.*.tiers.*.tier",
    *(f"actives.*.skill.{p}" for p in _SKILL_NUMBERS),
    *(f"passives.*.tiers.*.effects.{p}" for p in (
        "opening_rounds", "opening_sp", "armor_min", "armor_bonus", "skill_overrides.*.cooldown",
        "hit_followup.accuracy", "low_hp.ratio", "low_hp.cost_multiplier", "low_hp.damage_multiplier",
        "physical_penetration", "taken_elements.*", "weakness_followup.damage", "weakness_followup.accuracy",
        "regen_ratio", "overflow_ratio", "sp_for_mp.rate", "sp_for_mp.max_ratio", "round_attack.hp_ratio_gt",
        "round_attack.damage", "round_attack.accuracy", "mana_cycle.amount", "mana_cycle.cap_ratio",
        "shield_regain.every", "shield_regain.max", "shield_regain.status.modifiers.shield.max_hp_ratio",
        "resonance.multiplier", "resonance.refund", "mana_armor", "weak_multiplier",
        "evade_bonus", "miss_sp", "miss_sp_cap", "hit_status.stacks", "hit_status.max_stacks",
        "free_item_uses", "counter_attack.damage", "counter_attack.accuracy", "encounter_damage.*",
    )),
)
# Inert definitions are shared metadata, never active baby balance values.
NON_BALANCE_FIELDS += ("status_defs.*.*", "status_defs.*.*.*", "status_defs.*.*.*.*", "status_defs.*.*.*.*.*")
DIFFICULTY_LABELS = {"baby": "やさしい", "normal": "ふつう"}

FORMULA = re.compile(
    r"-?(?:\d+(?:\.\d+)?d\d+|\d+(?:\.\d+)?|str|dex|int|wis|end|agi)"
    r"(?:[+*/-](?:\d+(?:\.\d+)?d\d+|\d+(?:\.\d+)?|str|dex|int|wis|end|agi))*$"
)


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _numeric(value: Any) -> bool:
    return _number(value) or isinstance(value, str) and bool(FORMULA.fullmatch(value))


def _identity(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _identity(child) for key, child in value.items() if not _numeric(child)}
    if isinstance(value, list):
        return [_identity(child) for child in value]
    return value


def _selector(record: Any) -> str:
    if not isinstance(record, dict):
        raise ValueError("Difficulty paths require object records in lists")
    for key in ("id", "item_id", "name"):
        if isinstance(record.get(key), str) and record[key]:
            return "@" + key + "=" + quote(record[key], safe="").replace(".", "%2E")
    encoded = json.dumps(_identity(record), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "@shape=" + hashlib.sha256(encoded).hexdigest()


def _matches(path: str, pattern: str) -> bool:
    parts, expected = path.split("."), pattern.split(".")
    return len(parts) == len(expected) and all(b == "*" or a == b for a, b in zip(parts, expected))


def _leaves(value: Any, path: str = "", pattern: str = "") -> Iterator[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _leaves(child, f"{path}.{key}".lstrip("."), f"{pattern}.{key}".lstrip("."))
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, dict):
                yield from _leaves(child, f"{path}.{_selector(child)}".lstrip("."), f"{pattern}.*".lstrip("."))
    else:
        yield path, pattern, value


def numeric_snapshot(pack: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    """Return every allowed leaf, retaining entity IDs and stable nested selectors."""
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for group, patterns in NUMERIC_FIELDS.items():
        records = pack.get(group, [])
        entries = [(str(record["id"]), record) for record in records] if isinstance(records, list) else [("$", records)]
        for identifier, record in entries:
            values = {}
            for path, pattern, value in _leaves(record):
                if any(_matches(pattern, allowed) for allowed in patterns):
                    if value in (None, "", "none", "null") and path.endswith(".dice_type"):
                        continue
                    if not _numeric(value) and not (value is None and path.endswith(".stock")):
                        raise ValueError(f"Non-numeric difficulty field: {group}/{identifier}/{path}")
                    if path in values:
                        raise ValueError(f"Ambiguous difficulty address: {group}/{identifier}/{path}")
                    values[path] = value
            if values:
                if identifier in result.setdefault(group, {}):
                    raise ValueError(f"Duplicate entity ID: {group}/{identifier}")
                result[group][identifier] = values
    return result


def _entity(pack: dict[str, Any], group: str, identifier: str) -> Any:
    records = pack.get(group)
    if isinstance(records, dict) and identifier == "$":
        return records
    if isinstance(records, list):
        matches = [record for record in records if isinstance(record, dict) and record.get("id") == identifier]
        if len(matches) == 1:
            return matches[0]
    raise ValueError(f"Missing or ambiguous difficulty entity: {group}/{identifier}")


def _destination(record: Any, path: str) -> tuple[dict[str, Any], str, str]:
    parts = path.split(".")
    pattern = []
    current = record
    for part in parts[:-1]:
        if isinstance(current, list):
            matches = [child for child in current if _selector(child) == part]
            if not part.startswith("@") or len(matches) != 1:
                raise ValueError(f"Missing or ambiguous list selector: {path}")
            current = matches[0]
            pattern.append("*")
        elif isinstance(current, dict) and part in current:
            current = current[part]
            pattern.append(part)
        else:
            raise ValueError(f"Unresolved difficulty path: {path}")
    if not isinstance(current, dict) or not parts[-1]:
        raise ValueError(f"Difficulty destination must be an object field: {path}")
    return current, parts[-1], ".".join(pattern + [parts[-1]])


def _apply_overlays(pack: dict[str, Any]) -> None:
    overlays = pack.get("difficulty_overlays", {"normal": []})
    if not isinstance(overlays, dict) or set(overlays) != {"normal"} or not isinstance(overlays["normal"], list):
        raise ValueError("difficulty_overlays must contain only the normal list")
    destinations = []
    seen = set()
    for entry in overlays["normal"]:
        if not isinstance(entry, dict):
            raise ValueError("Difficulty overlay entry must be an object")
        operations = set(entry) & {"set", "add", "mul"}
        if len(operations) != 1 or set(entry) != {"entity", "id", "path"} | operations:
            raise ValueError("Difficulty overlay requires entity, id, path and exactly one set/add/mul")
        group, identifier, path = (entry.get(key) for key in ("entity", "id", "path"))
        if not all(isinstance(value, str) and value for value in (group, identifier, path)):
            raise ValueError("Difficulty addresses must be nonempty strings")
        record = _entity(pack, group, identifier)
        parent, key, pattern = _destination(record, path)
        operation = next(iter(operations))
        value = entry[operation]
        mechanics = [values for allowed, values in MECHANIC_FIELDS.get(group, {}).items()
                     if _matches(pattern, allowed)]
        if mechanics:
            valid = any(type(value) is type(candidate) and value == candidate
                        for values in mechanics for candidate in values)
            # Numeric rule parameters remain tunable in data without changing baby.
            if group == "combat_rules" and pattern == "evade_formula":
                valid = (isinstance(value, dict) and set(value) == {"base", "per_dex", "cap"}
                         and all(_number(item) for item in value.values())
                         and value["per_dex"] >= 0 and 0 <= value["cap"] <= 40)
            elif group == "combat_rules" and pattern == "enemy_accuracy_override":
                valid = value is None or (type(value) is int and 0 <= value <= 100)
            elif group == "characters" and pattern == "skills.*.cooldown":
                valid = type(value) is int and value >= 1
            elif group == "companions" and pattern == "round_start_effects.*.scale_from_damage":
                valid = (isinstance(value, dict) and set(value) == {"source", "ratio"}
                         and value["source"] == "previous_damage_enemy"
                         and _number(value["ratio"]) and value["ratio"] >= 0)
            elif group == "progression":
                if pattern == "level_model":
                    valid = value == "exp"
                elif pattern == "max_level":
                    valid = type(value) is int and value >= 2
                elif pattern in {"exp_table", "exp_rewards"}:
                    valid = (isinstance(value, dict) and bool(value)
                             and all(type(n) is int and n >= 0 for n in value.values()))
                elif pattern == "level_gains":
                    valid = (isinstance(value, dict) and set(value) == {"hero", "cleric", "mage", "thief"}
                             and all(isinstance(g, dict) and set(g) == {"max_hp", "max_mp", "max_sp", "attributes"}
                                     and isinstance(g["attributes"], dict)
                                     and all(type(n) is int and n >= 0 for k, n in g.items() if k != "attributes")
                                     and all(type(n) is int and n >= 0 for n in g["attributes"].values())
                                     for g in value.values()))
            elif group == "characters" and pattern == "skills.*.conditional_bonus":
                valid = (isinstance(value, list) and bool(value)
                         and all(isinstance(c, dict) and c.get("if") in {"target_hp_full", "target_hp_ratio_lte"}
                                 and isinstance(c.get("damage"), str) and bool(FORMULA.fullmatch(c["damage"]))
                                 and (c["if"] != "target_hp_ratio_lte"
                                      or _number(c.get("ratio")) and 0 <= c["ratio"] <= 1) for c in value))
            if operation != "set" or not valid:
                raise ValueError(f"Invalid mechanic setting: {group}/{path}")
        else:
            if not any(_matches(pattern, allowed) for allowed in NUMERIC_FIELDS.get(group, ())):
                raise ValueError(f"Difficulty path is not whitelisted: {group}/{path}")
            if key not in parent:
                raise ValueError(f"Numeric difficulty field must already exist: {group}/{path}")
            old = parent[key]
            if not _numeric(old) and not (old is None and key == "stock"):
                raise ValueError(f"Difficulty field is not numeric: {group}/{path}")
            if operation == "set":
                valid = _numeric(value) if isinstance(old, str) else _number(value)
                if key == "stock" and value is None:
                    valid = True
                if not valid:
                    raise ValueError(f"Invalid numeric setting: {group}/{path}")
            elif not _number(value):
                raise ValueError(f"{operation} requires numeric operands: {group}/{path}")
        address = (group, identifier, path)
        if address in seen:
            warnings.warn(f"Repeated difficulty destination: {address}", RuntimeWarning, stacklevel=3)
        seen.add(address)
        destinations.append((parent, key, operation, value))
    # Resolve selectors against the base before any arithmetic changes anonymous records.
    for parent, key, operation, value in destinations:
        if operation == "set":
            parent[key] = deepcopy(value)
        else:
            if not _number(parent[key]):
                raise ValueError(f"{operation} requires a numeric current value")
            result = parent[key] + value if operation == "add" else parent[key] * value
            if not _number(result):
                raise ValueError("Difficulty arithmetic must produce a finite number")
            parent[key] = result
    config = pack.get("progression", {})
    if config.get("level_model") == "exp":
        maximum, table = config.get("max_level", 0), config.get("exp_table", {})
        if set(table) != {str(n) for n in range(2, maximum + 1)}:
            raise ValueError("EXP table must cover levels 2 through max_level")
        thresholds = [0] + [table[str(n)] for n in range(2, maximum + 1)]
        if any(a >= b for a, b in zip(thresholds, thresholds[1:])):
            raise ValueError("EXP thresholds must be strictly increasing")
        if not {"trash", "elite", "boss", "unclassified", "quest", "scripted_loss", "guest"} <= set(config.get("exp_rewards", {})):
            raise ValueError("Missing EXP reward source")


def validate_difficulty(pack: dict[str, Any]) -> None:
    """Validate even unused normal overlays when loading or saving a base pack."""
    if pack.get("difficulty_overlays", {"normal": []}) == {"normal": []}:
        return
    _apply_overlays(deepcopy(pack))


def apply_difficulty(pack: dict[str, Any], mode: str) -> dict[str, Any]:
    if not isinstance(mode, str) or mode not in DIFFICULTY_LABELS:
        raise ValueError(f"Unknown difficulty: {mode!r}")
    result = deepcopy(pack)
    if mode == "normal":
        _apply_overlays(result)
    else:
        validate_difficulty(pack)
    def filtered(value: Any) -> Any:
        if isinstance(value, list):
            return [filtered(entry) for entry in value
                    if not isinstance(entry, dict) or mode in entry.get("difficulty_only", [mode])]
        if isinstance(value, dict):
            return {key: filtered(child) for key, child in value.items()}
        return value

    result = filtered(result)
    if not result.get("class_progression"):
        result.pop("class_progression", None)
    return result


def overlay_fingerprint(pack: dict[str, Any]) -> str:
    payload = json.dumps(pack.get("difficulty_overlays", {"normal": []}), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
