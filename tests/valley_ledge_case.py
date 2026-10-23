"""Deterministic real-engine damage decomposition on observed 052c2 snapshots."""
from __future__ import annotations

import json
import random
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from host import combat, state
from host.difficulty import apply_difficulty
from scripts.balance import budget, normal_052, probes_v3, snapshots_v3


def started(pack, entry, choices):
    session = probes_v3.with_passives(snapshots_v3.restore(pack, entry['snapshot']), choices)
    session['combat_start_requested'] = True
    captured = []
    def capture(current, rng):
        if not captured:
            captured.append(deepcopy(current))
    with patch.object(combat, '_apply_round_start_effects', capture):
        combat.ensure_combat_started(session)
    current = captured[0]
    current['combat']['player_status'].pop('guard_multiplier', None)
    for status in current['character'].get('statuses', []):
        status.pop('shield_remaining', None)
        if status.get('modifiers', {}).get('received_damage_multiplier', 1) < 1:
            status['modifiers'].pop('received_damage_multiplier')
    return current


def engine_damage(session, ability, raw=0, *, twice=False):
    current = dict(session)
    current['character'] = deepcopy(session['character'])
    current['character']['hp'] = 10000
    current['combat'] = deepcopy(session['combat'])
    current['combat']['log'] = []
    current['combat'].pop('percentage_damage', None)
    amounts = []
    with patch.object(combat, '_roll_formula', return_value=(raw, {})), patch.object(combat, '_enemy_reaction'):
        for enemy in current['combat']['enemies'][:2 if twice else 1]:
            amounts.append(combat._resolve_attack(current, enemy, current['character'], ability,
                                                  enemy['id'], random.Random(1)))
    return amounts


def decompose(session):
    enemy = session['combat']['enemies'][0]
    skills = {s['id']: s for s in enemy['skills']}
    claw, breath = skills['hook_claw'], skills['lava_breath']
    chance = combat.attack_chance(session, enemy, session['character'], claw, enemy['id'])/100
    distribution = budget.formula_distribution(claw['damage'], enemy)
    ordinary = 2 * (2/3) * chance * sum(p*engine_damage(session, claw, raw)[0] for raw,p in distribution.items())
    chance_percent = combat.attack_chance(session, enemy, session['character'], breath, enemy['id'])/100
    one = engine_damage(session, breath)[0]
    pair = engine_damage(session, breath, twice=True)
    percent = 2*(1/3)*chance_percent*one - ((1/3)*chance_percent)**2*(2*one-sum(pair))
    no_burn = deepcopy(session)
    for foe in no_burn['combat']['enemies']:
        for skill in foe['skills']:
            skill.pop('on_hit_status', None)
    no_cap = deepcopy(session)
    no_cap['scenario_pack']['combat_rules']['elite_percentage_round_cap'] = 1
    forced = dict(breath, element='physical', damage_max_hp_ratio=.25)
    return dict(max_hp=session['character']['max_hp'], ordinary=ordinary, percentage=percent,
                total=ordinary+percent, ratio=(ordinary+percent)/session['character']['max_hp'],
                estimator=normal_052.opening_moments(session),
                without_burn=normal_052.opening_moments(no_burn)['expected_damage'],
                without_cap=normal_052.opening_moments(no_cap)['expected_damage'],
                forced_shared_cap_hits=engine_damage(session, forced, twice=True),
                cap=int(session['character']['max_hp']*.3))
