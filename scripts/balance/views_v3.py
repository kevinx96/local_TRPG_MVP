"""Read-only metadata scoped to one decision or one normal engine command."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

from host import combat, item_mechanics, progression


@contextmanager
def decision_views(session: dict[str, Any]):
    actor = session["character"]
    original_effects, original_rules = progression.effects, combat._combat_rules
    original_skills = combat._available_skills
    original_specs = item_mechanics.equipped_item_specs
    effects, rules = original_effects(session), original_rules(session)
    skills, specs = original_skills(actor), original_specs(actor)
    cached_specs = lambda value: specs if value is actor else original_specs(value)
    with patch.object(progression, "effects", lambda value: effects if value is session else original_effects(value)), \
         patch.object(combat, "_combat_rules", lambda value: rules if value is session else original_rules(value)), \
         patch.object(combat, "_available_skills", lambda value: skills if value is actor else original_skills(value)), \
         patch.object(combat, "equipped_item_specs", cached_specs), \
         patch.object(item_mechanics, "equipped_item_specs", cached_specs):
        if session.get("difficulty") != "normal":
            yield
            return
        original_item, original_ability = item_mechanics.item_combat_spec, combat._player_ability
        items, abilities = {}, {}

        def item_view(value):
            key = id(value)
            if key not in items:
                # Retain the source object so its identity cannot be recycled.
                items[key] = (value, original_item(value))
            return items[key][1]

        def ability_view(current, action_type, action_id):
            if current is not session:
                return original_ability(current, action_type, action_id)
            key = (action_type, action_id)
            if key not in abilities:
                abilities[key] = original_ability(current, action_type, action_id)
            return abilities[key]

        with patch.object(combat, "item_combat_spec", item_view), \
             patch.object(item_mechanics, "item_combat_spec", item_view), \
             patch.object(combat, "_player_ability", ability_view):
            yield


@contextmanager
def action_rules(session: dict[str, Any]):
    """Reuse catalogs; dynamic costs, statuses and equipment membership stay live."""
    actor = session["character"]
    original_rules, original_effects = combat._combat_rules, progression.effects
    original_skills, original_item = combat._available_skills, item_mechanics.item_combat_spec
    rules, effects, skills = original_rules(session), original_effects(session), original_skills(actor)
    items = {}

    def item_view(value):
        key = id(value)
        if key not in items:
            items[key] = (value, original_item(value))
        return items[key][1]

    with patch.object(combat, "_combat_rules", lambda current: rules if current is session else original_rules(current)), \
         patch.object(progression, "effects", lambda current: effects if current is session and current["character"] is actor else original_effects(current)), \
         patch.object(combat, "_available_skills", lambda current: skills if current is actor else original_skills(current)), \
         patch.object(combat, "item_combat_spec", item_view), \
         patch.object(item_mechanics, "item_combat_spec", item_view):
        yield
