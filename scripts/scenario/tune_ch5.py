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
    tune_maps(pack)


def tune_support(pack: dict[str, Any]) -> None:
    modifiers = next(loc for loc in pack['locations'] if loc['id'] == 'draco_battle')['combat']['encounter_modifiers']
    next(m for m in modifiers if m['id'] == 'king').update(
        enemy_defense=-4, disabled_enemy_skills=['guard_stance'],
        round_start_attack=dict(name='近衛兵', damage='13', accuracy=100, element='physical'))
    robin = next(m for m in modifiers if m['id'] == 'robin')
    for key in ('enemy_skill', 'accuracy', 'damage_multiplier'):
        robin.pop(key, None)
    robin['text'] = '「昨夜のうちに、あんたの部屋から妙な首飾りをくすねといたよ。白い竜の力の源なんだろ？」柱の陰からロビンの声がした。'
    # TODO(design): .90 still exceeds +8pp; approve a wider HP range or revise the target.
    phase2 = dict(id='robin_dragon', enemy_ids=['draco_dragon'], requirements=robin['requirements'],
                  enemy_hp_multiplier=.90, text='白竜の巨体から、一瞬だけ光が抜け落ちた。ロビンが盗んだ首飾りの効果らしい。')
    modifiers[:] = [m for m in modifiers if m['id'] != 'robin_dragon']
    modifiers.insert(modifiers.index(robin) + 1, phase2)
    pack['meta']['content_revision'] = max(pack['meta'].get('content_revision', ''), '2026-10-12-v026-support2')


def tune_maps(pack: dict[str, Any]) -> None:
    positions = {'royal_return': {'R5': (85, 20)}, 'forest': {'F3': (50, 85), 'F4': (70, 85)}}
    for map_data in pack['maps']:
        for node in map_data['nodes']:
            position = positions.get(map_data['id'], {}).get(node['id'])
            if position:
                node['x'], node['y'] = position


if __name__ == '__main__':
    for name in ('dragon_rpg.json', 'dragon_rpg_hybrid.json'):
        path = ROOT / 'host/prompt/processed' / name
        pack = json.loads(path.read_text(encoding='utf-8'))
        tune(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
