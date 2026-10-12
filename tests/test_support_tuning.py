from __future__ import annotations

import random
import unittest
from copy import deepcopy
from unittest.mock import Mock, patch

from host import combat, state
from scripts.balance import checkpoints, support
from scripts.scenario.tune_ch5 import tune_support


class SupportTuningTests(unittest.TestCase):
    def sessions(self, enabled: bool = True, location: str = 'draco_battle'):
        for filename in ('dragon_rpg.json', 'dragon_rpg_hybrid.json'):
            pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(filename))
            s = checkpoints.fresh_session(pack, 'hero')
            s['world_state'] = dict(scene_id='castle_return', location_id=location)
            s['flags'].update(king_trust=enabled, recruited_robin=enabled, cleared_goblin_fort=enabled)
            s['combat_start_requested'] = True
            with patch.object(combat, 'random', random.Random(1)):
                combat.ensure_combat_started(s)
            yield s

    def test_guard_is_removed_from_choices_only_when_king_active(self):
        for enabled in (False, True):
            for s in self.sessions(enabled):
                enemy = s['combat']['enemies'][0]
                original = deepcopy(enemy['skills'])
                rng = Mock()
                rng.choices.side_effect = lambda entries, **kwargs: [entries[-1]]
                combat._choose_enemy_ability(enemy, s, rng)
                choices = rng.choices.call_args.args[0]
                self.assertEqual('guard_stance' in [a['id'] for a in choices], not enabled)
                self.assertEqual(enemy['skills'], original)
                if enabled:
                    guard = next(a for a in enemy['skills'] if a['id'] == 'guard_stance')
                    guard['every_n_rounds'] = 1
                    self.assertNotEqual(combat._choose_enemy_ability(enemy, s, rng)['id'], 'guard_stance')

    def test_king_round_damage_defense_and_phase_boundary(self):
        for s in self.sessions():
            enemy = s['combat']['enemies'][0]
            self.assertEqual(enemy['hp'], 12)
            attacks = [e for e in s['combat']['log'] if e['actor'] == 'king' and e['kind'] == 'damage']
            self.assertEqual(len(attacks), 1)
            self.assertEqual(attacks[0]['data']['damage'], 13)
            enemy['combat']['defense'] = 6
            combat._resolve_attack(s, s['character'], enemy,
                                   dict(name='攻撃', damage='10', accuracy=100, element='physical'),
                                   'player', random.Random(1))
            self.assertEqual(s['combat']['log'][-1]['data']['damage'], 8)
            enemy['combat']['defense'] = 2
            combat._apply_round_start_effects(s, random.Random(1))
            dragon = s['combat']['enemies'][0]
            self.assertEqual(dragon['template_id'], 'draco_dragon')
            self.assertEqual(dragon['hp'], dragon['max_hp'])
            index = len(s['combat']['log'])
            combat._apply_round_start_effects(s, random.Random(1))
            self.assertFalse(any(e['actor'] == 'king' for e in s['combat']['log'][index:]))
            self.assertNotIn('king', [m['id'] for m in s['combat']['active_modifiers']])

    def test_support_disabled_and_other_encounters_keep_original_behavior(self):
        for s in self.sessions(False):
            self.assertEqual(s['combat']['enemies'][0]['hp'], 25)
            self.assertEqual(s['combat']['active_modifiers'], [])
        for s in self.sessions(location='mansion_corridor'):
            self.assertFalse(any(e['actor'] in ('king', 'robin') for e in s['combat']['log']))
            enemy = combat._runtime_enemy(next(e for e in s['scenario_pack']['enemies'] if e['id'] == 'draco_human'), 0)
            rng = Mock()
            rng.choices.side_effect = lambda entries, **kwargs: [entries[-1]]
            self.assertEqual(combat._choose_enemy_ability(enemy, s, rng)['id'], 'guard_stance')
            self.assertEqual(combat._modified_received_damage(s, 100, 'physical', enemy, '剣聖の一閃'), 100)

    def test_robin_accuracy_damage_and_same_named_basic_attack(self):
        for enabled in (False, True):
            for s in self.sessions(enabled):
                enemy = s['combat']['enemies'][0]
                original = deepcopy(enemy)
                s['character']['combat'] = dict(defense=0, evade=0)
                s['character']['equipment'] = []
                s['character']['resistances'] = {}
                s['character']['hp'] = 100
                for ability in (enemy['skills'][0], enemy['combat']['basic_attack']):
                    attack = {**ability, 'damage': '10'}
                    combat._resolve_attack(s, enemy, s['character'], attack, enemy['id'], Mock(randint=Mock(return_value=65)))
                    self.assertEqual(s['combat']['log'][-1]['kind'], 'miss' if enabled else 'damage')
                    combat._resolve_attack(s, enemy, s['character'], attack, enemy['id'], Mock(randint=Mock(return_value=1)))
                    data = s['combat']['log'][-1]['data']
                    self.assertEqual(data['hit_chance'], 60 if enabled else 90)
                    self.assertEqual(data['damage'], 8 if enabled else 10)
                self.assertEqual(enemy, original)
                self.assertEqual(combat._modified_received_damage(s, 100, 'ice', enemy, '氷刃'), 100)

    def test_tuning_is_idempotent_and_preserves_other_support_and_text(self):
        packs = []
        for s in self.sessions():
            pack = s['scenario_pack']
            before = deepcopy(pack)
            tune_support(pack)
            self.assertEqual(pack, before)
            modifiers = next(l for l in pack['locations'] if l['id'] == 'draco_battle')['combat']['encounter_modifiers']
            packs.append(modifiers)
        self.assertEqual(*packs)


class SupportReportTests(unittest.TestCase):
    def rows(self):
        return [dict(case=case, character=c, win_rate=.6, contribution_pp=5)
                for case in support.cases() for c in support.CHARACTERS]

    def test_acceptance_uses_mean_and_only_caps_kill_route(self):
        rows = self.rows()
        for r in rows:
            if r['case'] == 'all_purify':
                r['win_rate'] = 1.0
            if r['case'] == 'king':
                r['contribution_pp'] = 20 if r['character'] == 'hero' else 0
            if r['case'] == 'ignis':
                r['contribution_pp'] = 40
        self.assertEqual(support.check_results(rows), [])
        next(r for r in rows if r['case'] == 'all_kill')['win_rate'] = .921
        self.assertEqual(len(support.check_results(rows)), 1)
        next(r for r in rows if r['case'] == 'king')['contribution_pp'] = 11
        self.assertEqual(len(support.check_results(rows)), 2)

    def test_acceptance_rejects_missing_and_duplicate_cells(self):
        rows = self.rows()
        rows.pop()
        self.assertTrue(support.check_results(rows))
        rows.append(deepcopy(rows[0]))
        self.assertTrue(support.check_results(rows))

    def test_net_purification_preparation_and_baseline_pairing(self):
        def fake(pack, encounter, character, **kwargs):
            rate = .6 if not kwargs['initial_delta'] else .65
            return dict(character=character, win_rate=rate, preparation=kwargs['preparation'])
        with patch.object(support.sim, 'simulate', side_effect=fake) as simulate, patch('builtins.print'):
            result = support.evaluate(2, 123)
        self.assertEqual(result['violations'], [])
        for row, call in zip(result['supports'], simulate.call_args_list):
            self.assertEqual(call.kwargs['seed'], 123)
            self.assertEqual(call.kwargs['preparation'], 'purification' if row['case'] == 'all_purify' else 'standard')
            self.assertEqual(row['contribution_pp'], 0 if row['case'] == 'none' else 5)
        self.assertIn('净化路线全满', support.markdown(result))


if __name__ == '__main__':
    unittest.main()
