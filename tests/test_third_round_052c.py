from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from host import state
from host.difficulty import apply_difficulty, validate_difficulty
from scripts.balance import metrics_v3
from scripts.scenario import normal_tuning_052, status_content_054
import valley_ledge_case as case


class ThirdRound052cTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = apply_difficulty(state.load_scenario_pack(Path('host/prompt/processed/dragon_rpg.json')), 'normal')
        cls.fixture = json.loads((Path(case.__file__).parent/'fixtures/valley_ledge_052c3.json').read_text(encoding='utf-8'))

    def test_real_engine_opening_mean_within_elite_band(self):
        values = []
        for character, entry in self.fixture['characters'].items():
            session = case.started(self.pack, entry, self.fixture['choices'][character])
            result = case.decompose(session)
            self.assertAlmostEqual(result['total'], result['estimator']['expected_damage'])
            self.assertAlmostEqual(result['total'], result['without_burn'])
            self.assertEqual(sum(result['forced_shared_cap_hits']), result['cap'])
            values.append(result['ratio'])
        self.assertGreaterEqual(sum(values)/4, .18)
        self.assertLessEqual(sum(values)/4, .25)

    def test_original_claw_reproduces_lethal_opening(self):
        pack = deepcopy(self.pack)
        enemy = next(e for e in pack['enemies'] if e['id'] == 'lava_drake')
        next(s for s in enemy['skills'] if s['id'] == 'hook_claw')['damage'] = '1d56'
        session = case.started(pack, self.fixture['characters']['hero'], self.fixture['choices']['hero'])
        result = case.decompose(session)
        self.assertAlmostEqual(result['ordinary'], 31.58857142857142)
        self.assertAlmostEqual(result['percentage'], 3.2)
        self.assertGreater(result['ratio'], .9)

    def test_local_goblin_modifier_is_scoped_and_normal_only(self):
        base = state.load_scenario_pack(Path('host/prompt/processed/dragon_rpg.json'))
        baby = apply_difficulty(base, 'baby')
        normal_location = next(l for l in self.pack['locations'] if l['id'] == 'lost_goblin_crossroads')
        baby_location = next(l for l in baby['locations'] if l['id'] == 'lost_goblin_crossroads')
        self.assertEqual(normal_location['combat']['encounter_modifiers'],
                         [{'id': 'lost_goblin_052c3', 'enemy_damage_multiplier': .8}])
        self.assertNotIn('encounter_modifiers', baby_location['combat'])
        enemy = next(e for e in self.pack['enemies'] if e['id'] == 'goblin')
        self.assertEqual(enemy['combat']['basic_attack']['damage'], '1d2+2')
        entry = next(e for e in base['difficulty_overlays']['normal']
                     if e['id'] == 'lost_goblin_crossroads' and e['path'] == 'combat.encounter_modifiers')
        for fields in ({'id': 'forest_wolves'}, {'set': [{'id': 'wrong', 'enemy_damage_multiplier': .8}]},
                       {'set': [{'id': 'lost_goblin_052c3', 'enemy_damage_multiplier': 1.1}]}):
            invalid = deepcopy(base)
            invalid['difficulty_overlays']['normal'] = [{**entry, **fields}]
            with self.assertRaises(ValueError):
                validate_difficulty(invalid)

    def test_latest_review_classification(self):
        targets = json.loads(Path('eval/balance/targets.json').read_text(encoding='utf-8'))
        data = dict(difficulty='normal', measurement_scope='052', targets=targets, records=[],
                    boss_policy_probes=[dict(character='hero', encounter=e, policy='heuristic_v3', rounds=[n])
                                        for e,n in [('draco_battle',31),('merchant_battle',38)]],
                    damage_budget_v2=[dict(character=c, encounter=e, encounter_class='elite', ratio=ratio,
                                          expected_damage=ratio*100, variance=0, cv=0)
                                      for e,ratio in [('mansion_corridor',.1),('valley_ledge',.27),('bone_field',.4)]
                                      for c in ('hero','cleric','mage','thief')])
        metrics = {m['id']:m for m in metrics_v3.evaluate(data)}
        rows = {r['encounter']:r for r in metrics['M4']['value']}
        self.assertEqual(rows['draco_battle']['status'], 'accepted_boundary')
        self.assertEqual(rows['merchant_battle']['limit'], 18)
        self.assertFalse(rows['merchant_battle']['hard_gate'])
        self.assertEqual(rows['merchant_battle']['status'], 'optional_exception')
        rows = {r['encounter']:r for r in metrics['M9']['value']}
        self.assertEqual(rows['mansion_corridor']['status'], 'accepted_easy_exception')
        self.assertEqual(rows['valley_ledge']['status'], 'fail')
        self.assertEqual(rows['bone_field']['status'], 'hard_report')

    def test_periodic_override_waits_for_054_and_removes_stale_reference(self):
        base = state.load_scenario_pack(Path('host/prompt/processed/dragon_rpg.json'))
        previous = deepcopy(base)
        worm = next(e for e in previous['enemies'] if e['id'] == 'earth_worm')
        worm['skills'] = [s for s in worm['skills'] if s['id'] != 'gravel_spray']
        intermediate = normal_tuning_052.migrate(previous)
        self.assertFalse(any(e['id'] == 'earth_worm' and e['path'] == 'skills.@id=gravel_spray.damage'
                             for e in intermediate['difficulty_overlays']['normal']))
        self.assertEqual(normal_tuning_052.migrate(status_content_054.migrate(intermediate)), base)


if __name__ == '__main__':
    unittest.main()
