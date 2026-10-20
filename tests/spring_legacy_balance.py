"""Pin the pre-048 spring topology for historical numeric simulator comparisons.

048 forbids scripts/balance changes. These helpers are for legacy harness tests;
test_spring_postgame exercises the actual current pack without this adaptation.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def legacy_spring_balance_pack(pack: dict[str, Any]) -> dict[str, Any]:
    pack = deepcopy(pack)
    locations = {loc['id']: loc for loc in pack['locations']}
    action = next(a for a in locations['elf_spring']['actions'] if a['id'] == 'rest_at_elf_spring')
    for key in ('once', 'hidden_after', 'visible_requirements'):
        action.pop(key, None)
    action['effects'] = [
        {'restore_full': True},
        {'branch': {'requirements': {'flag': 'defeated_slime_king'}, 'then': [],
                    'else': [{'current_location': 'slime_ambush_one'}, {'start_combat': True}]}},
    ]
    locations['slime_king_battle']['combat']['victory_effects']['current_location'] = 'elf_spring'
    return pack
