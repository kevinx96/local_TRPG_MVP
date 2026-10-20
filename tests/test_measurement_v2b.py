from __future__ import annotations

import hashlib
import json
import unittest
from copy import deepcopy
from dataclasses import replace

from host import combat, state
from scripts.balance import archetypes, checkpoints, metrics_v2, probes_v2, route_v2, sim
from scripts.playtest import save_telemetry


class MetricsV2Tests(unittest.TestCase):
    def setUp(self):
        self.targets = json.loads((checkpoints.ROOT / 'eval/balance/targets.json').read_text(encoding='utf-8'))
        self.data = {'targets': self.targets, 'records': []}

    def record(self, archetype='P0b', character='hero', completed=True, **extra):
        record = dict(archetype=archetype, character=character, completed=completed, battles=[], **extra)
        self.data['records'].append(record)
        return record

    def battle(self, record, **extra):
        battle = dict(encounter='dragon_valley_loc', encounter_class='boss', policy='best_free', rounds=14,
                      status='victory', before={'hp': 20, 'max_hp': 40, 'healing_hp': 0},
                      opening={'expected_damage': 10}, expected_healing=4, expected_hp_loss=28)
        battle.update(extra)
        record['battles'].append(battle)
        return battle

    def test_every_metric_has_uniform_missing_data_contract(self):
        results = metrics_v2.evaluate(self.data)
        self.assertEqual([r['id'] for r in results], list(self.targets['metrics_v2']))
        self.assertTrue(all(r['status'] == 'not_applicable' for r in results))
        self.assertIn('050/051', results[-2]['reason'])
        for r in results: self.assertTrue({'id', 'value', 'target', 'status', 'hard_gate'} <= r.keys())

    def test_m1_class_exception_and_inclusive_upper_bound(self):
        for i in range(20): self.record(completed=i == 0)
        self.assertEqual(metrics_v2.m1(self.data)['status'], 'pass')
        self.data['records'][1]['completed'] = True
        self.assertEqual(metrics_v2.m1(self.data)['status'], 'fail')
        for r in self.data['records']: r['character'] = 'mage'
        self.assertEqual(metrics_v2.m1(self.data)['status'], 'pass')

    def test_gradient_keeps_both_p0_baselines(self):
        for a, wins in (('P0a', 0), ('P0b', 1), ('P1', 4), ('P2', 7), ('P3', 10)):
            for i in range(20): self.record(a, completed=i < wins)
        result = metrics_v2.m1_prime(self.data)
        self.assertTrue(result['meets_target'])
        self.assertEqual(len(result['value']), 4)

    def test_m2_critical_and_noncritical_boundaries(self):
        self.data['preparation_probes'] = [{'critical': True, 'uplift': .1}, {'critical': False, 'uplift': .25}]
        self.assertTrue(metrics_v2.m2(self.data)['meets_target'])
        self.data['preparation_probes'][0]['uplift'] = .099
        self.assertFalse(metrics_v2.m2(self.data)['meets_target'])
        self.assertEqual(metrics_v2.m2(self.data)['status'], 'report')

    def test_m3_strict_and_zero_incoming(self):
        battle = self.battle(self.record(), expected_healing=5)
        self.assertEqual(metrics_v2.m3(self.data)['status'], 'fail')
        battle['expected_healing'] = 4.999
        self.assertEqual(metrics_v2.m3(self.data)['status'], 'pass')
        battle['opening']['expected_damage'] = 0
        self.assertIsNone(metrics_v2.m3(self.data)['value'][0]['value'])

    def test_race_infinite_resources_and_censored_deaths(self):
        battle = self.battle(self.record(), expected_healing=10)
        self.assertEqual(metrics_v2.m3_prime(self.data)['value'][0]['value'], 0)
        battle['status'] = 'defeat'
        row = metrics_v2.m3_prime(self.data)['value'][0]
        self.assertIsNone(row['value'])
        self.assertEqual(row['censored_defeats'], 1)

    def test_round_boundary_and_sandbag(self):
        battle = self.battle(self.record())
        self.assertEqual(metrics_v2.m4(self.data)['status'], 'pass')
        battle['rounds'] = 18
        self.assertEqual(metrics_v2.m4(self.data)['status'], 'fail')
        self.assertFalse(metrics_v2.m4(self.data)['value'][0]['sandbag'])
        battle['rounds'] = 19
        self.assertTrue(metrics_v2.m4(self.data)['value'][0]['sandbag'])

    def test_resource_pressure_ignores_nonarrival_and_nonhealing_consumables(self):
        self.record('P1')
        record = self.record('P1', boss_arrivals={'dragon_valley_loc': {'healing_hp': 60, 'max_hp': 40}},
                             final={'gold': 30, 'inventory': {'薬草': 1}}, healing_item_names=['薬草'],
                             purchases=[{'before': {'gold': 100}, 'after': {'gold': 30}}])
        self.battle(record, consumables={'薬草': 1, '火球術の巻物': 10})
        result = metrics_v2.m5(self.data)
        self.assertTrue(result['meets_target'])
        self.assertEqual(result['value'][0]['n'], 1)
        self.assertEqual(result['value'][0]['healing_usage'], .5)

    def test_free_dominance_requires_strict_threshold_and_p0_agreement(self):
        battle = self.battle(self.record(), actions={'item:ice_charm': 7, 'attack:attack': 3},
                            action_specs={'item:ice_charm': {'free': True}}, p0_choice='item:ice_charm')
        self.assertTrue(metrics_v2.m6(self.data)['meets_target'])
        battle['actions']['item:ice_charm'] = 8
        self.assertFalse(metrics_v2.m6(self.data)['meets_target'])
        battle['p0_choice'] = 'attack:attack'
        self.assertTrue(metrics_v2.m6(self.data)['meets_target'])

    def test_paired_check_resource_loss_boundary(self):
        record = self.record(check_probes=[{'action': 'cross_lava_bridge', 'success': 1, 'failure': .85}])
        self.assertTrue(metrics_v2.m7(self.data)['meets_target'])
        record['check_probes'][0]['failure'] = .851
        self.assertFalse(metrics_v2.m7(self.data)['meets_target'])

    def test_companion_has_both_bounds(self):
        self.data['companion_probes'] = [{'uplift': .1}, {'uplift': .2}]
        self.assertTrue(metrics_v2.m8(self.data)['meets_target'])
        self.data['companion_probes'].append({'uplift': .201})
        self.assertFalse(metrics_v2.m8(self.data)['meets_target'])

    def test_damage_bandwidth_lower_bound_and_cv_boundary(self):
        self.data['damage_budget_v2'] = [{'encounter': 'forest_wolves', 'character': 'hero',
                                        'encounter_class': 'elite', 'ratio': .18, 'cv': .5}]
        self.assertEqual(metrics_v2.m9(self.data)['status'], 'pass')
        self.assertTrue(metrics_v2.m10(self.data)['meets_target'])
        self.data['damage_budget_v2'][0].update(ratio=.179, cv=.501)
        self.assertEqual(metrics_v2.m9(self.data)['status'], 'fail')
        self.assertFalse(metrics_v2.m10(self.data)['meets_target'])

    def test_lifetime_damage_is_not_opening_damage_times_rounds(self):
        self.battle(self.record(), expected_hp_loss=28)
        result = metrics_v2.m11(self.data)
        self.assertAlmostEqual(result['value'][0]['value'], .7)
        self.assertTrue(result['meets_target'])

    def test_new_mechanism_placeholders_and_numeric_level_probes(self):
        self.assertIsNone(metrics_v2.m12(self.data)['value']['dead_options'])
        self.assertEqual(metrics_v2.m13(self.data)['status'], 'not_applicable')
        self.data['level_probes'] = [{'uplift': .08}, {'uplift': .15}]
        self.assertTrue(metrics_v2.m13(self.data)['meets_target'])
        self.assertIsNone(metrics_v2.m13(self.data)['value']['p0_p2_arrival_level_gap'])


class MeasurementV2IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cls.cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding='utf-8'))
        cls.save = json.loads(save_telemetry.DEFAULT_SAVE.read_text(encoding='utf-8'))

    def test_hp70_strict_free_rest_is_not_limited_to_three(self):
        run = route_v2.MeasurementRun(self.pack, 'hero', 1, archetypes.P0B)
        run.session['world_state'] = {'scene_id': 'dark_forest', 'location_id': 'elf_spring'}
        run.session['flags']['defeated_slime_king'] = True
        actor = run.session['character']; actor['hp'] = actor['max_hp'] * .7
        run.rest_point(); self.assertEqual(run.rests, [])
        for _ in range(4):
            actor['hp'] = 1; run.rest_point()
        self.assertEqual(len(run.rests), 4)

    def test_parameters_and_grinding_preserve_engine_state(self):
        archetypes.validate()
        self.assertEqual(route_v2.SUPPORTED_ARCHETYPES, tuple(archetypes.ARCHETYPES))
        with self.assertRaises(ValueError): archetypes.validate([replace(archetypes.P0A, decision_rule='unknown')])
        run = route_v2.MeasurementRun(self.pack, 'hero', 1, archetypes.ARCHETYPES['P0g'])
        before = deepcopy(run.session); run.grind_repeatable()
        self.assertEqual(run.session, before)
        self.assertIsNone(run.grinding['resource_cost_per_level'])

    def test_p2s_changes_only_battle_avoidance(self):
        prepared = archetypes.P2.to_dict()
        bypass = archetypes.ARCHETYPES['P2s'].to_dict()
        prepared.pop('id'); bypass.pop('id')
        self.assertFalse(prepared.pop('avoid_battles'))
        self.assertTrue(bypass.pop('avoid_battles'))
        self.assertEqual(prepared, bypass)

    def test_save_checkpoint_rolls_back_armour_and_uses_actual_elixirs(self):
        entry = probes_v2.observed_checkpoint(self.save)['profiles']['human_berserker']
        self.assertIn('革の鎧', entry['equipment']); self.assertNotIn('アダマンタイトの鎧', entry['equipment'])
        self.assertEqual(entry['gold'], 601)
        self.assertEqual(next(i['quantity'] for i in entry['inventory'] if i.get('id') == 'healing_scroll'), 8)
        self.assertEqual({i['id'] for i in entry['inventory'] if str(i.get('id', '')).startswith('elixir_')},
                         {'elixir_str', 'elixir_end', 'elixir_int', 'elixir_dex'})

    def test_preparation_removal_isolates_one_variable_and_never_refunds_gold(self):
        session = probes_v2.prepared_session(self.pack, self.cp, 'hero')
        data = json.loads(probes_v2.PREPARATIONS.read_text(encoding='utf-8'))
        for prep in data['encounters']['dragon_valley_loc']['items']:
            clone = probes_v2.class_clone(session); probes_v2.remove_preparation(clone, prep)
            self.assertEqual(clone['character']['gold'], session['character']['gold'])
            self.assertNotEqual(clone, session)

    def test_explicit_recovery_threshold_keeps_legacy_default(self):
        session = probes_v2.prepared_session(self.pack, self.cp, 'hero')
        combat.ensure_combat_started(session)
        session['character']['hp'] = 13
        self.assertEqual(sim.choose_action(session, 'heuristic')[0].get('kind'), 'heal')
        self.assertNotEqual(sim.choose_action(session, 'heuristic', recovery_threshold=.30)[0].get('kind'), 'heal')

    def test_real_save_timeline_and_evidence_limits(self):
        result = save_telemetry.extract(self.save)
        self.assertEqual((result['checks']['count'], result['checks']['successes']), (14, 10))
        self.assertEqual(len(result['rests']), 3)
        self.assertEqual((result['gold']['final'], result['gold']['spent_observed']), (706, 100))
        self.assertEqual(result['equipment_changes']['count_observed'], 2)
        ignis = next(b for b in result['battles'] if b['encounter'] == 'dragon_valley_loc')
        self.assertEqual((ignis['rounds'], ignis['end_hp']), (20, 29))
        self.assertIsNone(ignis['actions']); self.assertIsNone(result['healing_items']['used'])
        self.assertEqual(result['comparison']['nearest'], 'P2')
        self.assertEqual((result['boss_arrivals']['dragon_valley_loc']['hp'], result['boss_arrivals']['dragon_valley_loc']['level']), (40, 5))
        slimes = [b['encounter'] for b in result['battles'] if b['encounter'] in {'slime_ambush_one', 'slime_ambush_two'}]
        self.assertEqual(slimes, ['slime_ambush_one', 'slime_ambush_two'])
        preps = json.loads(probes_v2.PREPARATIONS.read_text(encoding='utf-8'))
        prepared = save_telemetry.extract(self.save, preparations=preps)
        used = {p['preparation']: p['used_in_target_battle'] for p in prepared['preparations']}
        self.assertTrue(used['ruby_charm'])
        self.assertFalse(used['adamantite_armor'])
        self.assertFalse(used['ice_iron_greatsword'])

    def test_matching_trace_enriches_battle_actions_and_arrival(self):
        save = {'id': 'synthetic', 'character': {'inventory': []}, 'scenario_pack': {
            'locations': [{'id': 'dragon_valley_loc', 'combat': {'encounter_class': 'boss'}}]},
            'event_log': [{'id': 'battle', 'kind': 'combat_resolved', 'created_at': '1',
                           'data': {'location_id': 'dragon_valley_loc', 'rounds': 2, 'player': {'hp': 17, 'max_hp': 20}}}]}
        trace = {'session_id': 'synthetic', 'battles': [{'event_id': 'battle', 'encounter': 'dragon_valley_loc',
                 'actions': {'attack:attack': 2}, 'before': {'hp': 20, 'healing_hp': 10, 'level': 1}}]}
        result = save_telemetry.extract(save, [trace])
        self.assertEqual(result['battles'][0]['actions'], {'attack:attack': 2})
        self.assertEqual(result['boss_arrivals']['dragon_valley_loc']['hp'], 20)

    def test_synthetic_logs_deduplicate_and_foreign_traces_are_rejected(self):
        save = {'id': 'synthetic', 'character': {'inventory': []}, 'scenario_pack': {},
                'event_log': [{'id': 'gold', 'kind': 'gold_changed', 'data': {'change': 10}, 'created_at': '1'}],
                'system_logs': [{'event_id': 'gold', 'text': '10ゴールドを獲得しました。', 'created_at': '1'}]}
        result = save_telemetry.extract(save, [{'session_id': 'other', 'events': [{'id': 'wrong', 'kind': 'gold_changed', 'data': {'change': 999}}]}])
        self.assertEqual(result['gold']['earned_observed'], 10)
        self.assertEqual(result['coverage']['matched_auxiliary'], 0)
        self.assertIsNone(result['checks']['success_rate'])

    def test_every_legacy_target_value_is_unchanged(self):
        current = json.loads((checkpoints.ROOT / 'eval/balance/targets.json').read_text(encoding='utf-8'))
        old_keys = ('_note', 'classes', 'class_spread_max', 'class_spread_max_multi_enemy', 'companion_uplift',
                    'incoming_damage_budget', 'encounters', 'encounter_overrides', 'route_targets', 'forest_v3', 'route_targets_with_optional')
        digest = hashlib.sha256(json.dumps({k: current[k] for k in old_keys}, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
        self.assertEqual(digest, '79e8ad1a5304c88fcc5e67b23ae226c5c190813bbffa5e10766759380a45232a')
        self.assertEqual({k for k, v in current['metrics_v2'].items() if v['hard_gate']}, {'M1', 'M3', 'M4', 'M9'})


if __name__ == '__main__':
    unittest.main()
