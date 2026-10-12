from __future__ import annotations

import json
from typing import Any

from .upgrade_forest import ROOT


def apply(pack: dict[str, Any], hp: int, damage_multiplier: float, enemy_id: str) -> None:
    enemy = next(e for e in pack['enemies'] if e['id'] == enemy_id)
    enemy['hp'] = enemy['max_hp'] = hp
    for ability in [enemy['combat']['basic_attack'], *enemy['skills']]:
        if 'damage' in ability:
            ability['damage_multiplier'] = damage_multiplier


def tune(pack: dict[str, Any]) -> None:
    for enemy_id, hp, damage, accuracy in [('ice_sentinel', 32, '1d40', 20), ('ice_assassin', 30, '1d12', 39)]:
        apply(pack, hp, 1, enemy_id)
        enemy = next(e for e in pack['enemies'] if e['id'] == enemy_id)
        enemy['resistances'].update(fire=1.45 if enemy_id == 'ice_sentinel' else 1.5,
                                    physical=.6 if enemy_id == 'ice_sentinel' else .55)
        for ability in [enemy['combat']['basic_attack'], *enemy['skills']]:
            if 'damage' in ability:
                ability.update(damage=damage, accuracy=accuracy)
    next(i for i in pack['items'] if i['id'] == 'fire_dragon_oil')['combat']['damage'] = '2d6'
    tune_support(pack)


def tune_support(pack: dict[str, Any]) -> None:
    modifiers = next(loc for loc in pack['locations'] if loc['id'] == 'draco_battle')['combat']['encounter_modifiers']
    next(m for m in modifiers if m['id'] == 'king').update(
        enemy_defense=-4, disabled_enemy_skills=['guard_stance'],
        round_start_attack=dict(name='近衛兵', damage='13', accuracy=100, element='physical'))
    next(m for m in modifiers if m['id'] == 'robin').update(accuracy=-30, damage_multiplier=.8)
    pack['meta']['content_revision'] = max(pack['meta'].get('content_revision', ''), '2026-10-12-v025-support')


if __name__ == '__main__':
    for name in ('dragon_rpg.json', 'dragon_rpg_hybrid.json'):
        path = ROOT / 'host/prompt/processed' / name
        pack = json.loads(path.read_text(encoding='utf-8'))
        tune(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
