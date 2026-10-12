from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from host import state
from . import checkpoints, sim

CHARACTERS = ('hero', 'cleric', 'mage', 'thief')
SUPPORTS = {
    'king': dict(flags_set=['king_trust']),
    'robin': dict(flags_set=['recruited_robin', 'cleared_goblin_fort']),
    'mina': dict(flags_set=['mina_quest_done']),
    'robert': dict(flags_set=['robert_hammer_returned']),
    'gald': dict(flags_set=['saved_gald'], inventory_add=[dict(name='火竜の油', quantity=2)]),
    'charm': dict(inventory_add=[dict(name='霜封じの護符', quantity=1)]),
    'ignis': dict(flags_set=['ignis_ally']),
}


def cases() -> dict[str, dict[str, Any]]:
    result = {'none': {}, **deepcopy(SUPPORTS)}
    for name, keys in [('all_kill', list(SUPPORTS)[:-1]), ('all', list(SUPPORTS))]:
        result[name] = {field: [entry for key in keys for entry in SUPPORTS[key].get(field, [])]
                        for field in ('flags_set', 'inventory_add')}
    return result


def evaluate(n: int, seed: int, *, elites_only: bool = False) -> dict[str, Any]:
    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    result: dict[str, Any] = dict(n=n, seed=seed, supports=[], elites=[], violations=[])
    for character in CHARACTERS:
        if not elites_only:
            baseline = 0.0
            for case, delta in cases().items():
                row = sim.simulate(pack, 'draco_battle', character, n=n, seed=seed, checkpoints=cp,
                                   preparation='standard', initial_delta=delta, purify=False)
                if case == 'none':
                    baseline = row['win_rate']
                row.update(case=case, contribution_pp=round((row['win_rate'] - baseline) * 100, 2))
                result['supports'].append(row)
                print(f"{character}/{case}: {row['win_rate']:.3f} ({row['contribution_pp']:+.2f}pp)", flush=True)
                if case == 'none' and not .5 <= row['win_rate'] <= .7:
                    result['violations'].append(f'{character}/{case}: baseline outside [0.50,0.70]')
                if case in SUPPORTS and not 3 <= row['contribution_pp'] <= 8:
                    result['violations'].append(f"{character}/{case}: {row['contribution_pp']}pp outside [3,8]")
                if case.startswith('all') and row['win_rate'] > .92:
                    result['violations'].append(f'{character}/{case}: win rate above 0.92')
        for encounter in ('mansion_corridor', 'inn_night_ambush'):
            # Same Lv5 arrival inventory as the final encounter, with no chapter-five rewards.
            cp['encounters'][encounter] = deepcopy(cp['encounters']['draco_battle'])
            for preparation, delta in [('normal', {}), ('robin' if encounter == 'inn_night_ambush' else 'alert',
                                           {'flags_set': ['recruited_robin' if encounter == 'inn_night_ambush' else 'mansion_alert']})]:
                row = sim.simulate(pack, encounter, character, n=n, seed=seed, checkpoints=cp, initial_delta=delta, purify=False)
                row['preparation'] = preparation
                result['elites'].append(row)
                print(f"{character}/{encounter}/{preparation}: {row['win_rate']:.3f}", flush=True)
                if preparation == 'normal' and not .75 <= row['win_rate'] <= .90:
                    result['violations'].append(f"{character}/{encounter}: {row['win_rate']} outside [0.75,0.90]")
    result['fingerprints'] = {str(p.relative_to(checkpoints.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (checkpoints.DEFAULT_SCENARIO, Path(__file__), Path(sim.__file__), checkpoints.ROOT / 'host/combat.py')}
    return result


def search(n: int, seed: int, refine: bool = False, variance: bool = False, burst: bool = False) -> dict[str, Any]:
    from scripts.scenario.tune_ch5 import apply

    pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
    cp = checkpoints.generate()
    result = dict(n=n, seed=seed, candidates=[])
    for encounter, enemy in [('mansion_corridor', 'ice_sentinel'), ('inn_night_ambush', 'ice_assassin')]:
        if burst and enemy != 'ice_sentinel':
            continue
        cp['encounters'][encounter] = deepcopy(cp['encounters']['draco_battle'])
        if burst:
            sizes, strengths = (28, 32, 36), (20, 24, 28)
        elif variance:
            sizes = (32, 36, 40) if enemy == 'ice_sentinel' else (20, 24, 28)
            strengths = (35, 45, 55)
        elif refine:
            sizes = (28, 32, 36) if enemy == 'ice_sentinel' else (20, 22, 24)
            strengths = (1.1, 1.2, 1.3)
        else:
            sizes, strengths = (24, 32, 40), (1.0, 1.5, 2.0, 2.5)
        for hp in sizes:
            for multiplier in strengths:
                candidate = deepcopy(pack)
                record = next(e for e in candidate['enemies'] if e['id'] == enemy)
                record['combat']['basic_attack'].update(damage='1d6+2', accuracy=75)
                record['resistances'] = {'fire': 1.5, **({'physical': .6} if enemy == 'ice_sentinel' else {})}
                record['skills'][0].update(damage='1d10+3' if enemy == 'ice_sentinel' else '1d4+2', accuracy=70 if enemy == 'ice_sentinel' else 80)
                if enemy == 'ice_assassin':
                    record['skills'][1].update(damage='1d4', accuracy=80)
                apply(candidate, hp, multiplier, enemy)
                if refine:
                    record = next(e for e in candidate['enemies'] if e['id'] == enemy)
                    record['resistances']['fire'] = 1.2 if enemy == 'ice_sentinel' else 1.4
                    if enemy == 'ice_assassin':
                        record['resistances']['physical'] = .8
                if variance or burst:
                    record = next(e for e in candidate['enemies'] if e['id'] == enemy)
                    record['resistances']['fire'] = 1.5
                    if enemy == 'ice_assassin':
                        record['resistances']['physical'] = .6
                    for ability in [record['combat']['basic_attack'], *record['skills']]:
                        if 'damage' in ability:
                            ability.update(damage='1d40' if burst else ('1d32' if enemy == 'ice_sentinel' else '1d12'), damage_multiplier=1, accuracy=multiplier)
                rates = [sim.simulate(candidate, encounter, c, n=n, seed=seed, checkpoints=cp, purify=False)['win_rate'] for c in CHARACTERS]
                error = sum(max(0, .75 - r, r - .90) for r in rates)
                row = dict(enemy=enemy, hp=hp, strength=multiplier, refine=refine, variance=variance, burst=burst, rates=rates, error=error)
                result['candidates'].append(row)
                print(row, flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Offline chapter-five support ablations and Lv5 elites')
    parser.add_argument('--n', type=int, default=500)
    parser.add_argument('--seed', type=int, default=20261012)
    parser.add_argument('--elites-only', action='store_true')
    parser.add_argument('--search', action='store_true')
    parser.add_argument('--refine', action='store_true')
    parser.add_argument('--variance', action='store_true')
    parser.add_argument('--burst', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path, default=checkpoints.ROOT / 'eval/reports/balance-2026-10-12-ch5.json')
    args = parser.parse_args()
    result = search(args.n, args.seed, args.refine, args.variance, args.burst) if args.search else evaluate(args.n, args.seed, elites_only=args.elites_only)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    raise SystemExit(int(args.check and bool(result['violations'])))
