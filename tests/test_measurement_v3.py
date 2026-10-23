from __future__ import annotations

import json
import random
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from host import combat, progression, state, status_effects
from host.difficulty import apply_difficulty
from host.shops import trade
from scripts.balance import (archetypes, budget, checkpoints, class_aware, measurement_v3,
                             metrics_v3, policy_v3, probes_v2, probes_v3, reproduction_v2,
                             route, route_v2, sim, snapshots_v3, views_v3)


class MeasurementV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO)
        cls.normal = apply_difficulty(cls.pack, 'normal')

    def session(self, character='hero', level=1, encounter='forest_wolves'):
        session = checkpoints.fresh_session(self.normal, character, 'normal', effective=True)
        progression.reward(session, self.normal['progression']['exp_table'].get(str(level), 0), 'test')
        session = archetypes.PassivePicker().apply(session)
        location = next(l for l in self.normal['locations'] if l['id'] == encounter)
        session['world_state'] = {'scene_id': location.get('scene_id', encounter), 'location_id': encounter}
        session['combat_start_requested'] = True
        return session

    def start(self, *args, **kwargs):
        session = self.session(*args, **kwargs)
        combat.ensure_combat_started(session)
        return session

    def test_difficulty_construction_order_and_effective_records(self):
        baby = checkpoints.fresh_session(self.pack, 'mage')
        normal = checkpoints.fresh_session(self.pack, 'mage', 'normal')
        self.assertEqual(baby['difficulty'], 'baby')
        self.assertFalse(progression.enabled(baby))
        self.assertEqual(normal['difficulty'], 'normal')
        self.assertEqual(normal['character']['exp'], 0)
        self.assertEqual(normal['progression_revision'], '050')
        self.assertTrue(normal['scenario_pack']['class_progression'])
        self.assertIn('spellbook_lightning', {i['id'] for i in normal['scenario_pack']['items']})
        with self.assertRaises(ValueError):
            checkpoints.fresh_session(self.pack, 'hero', 'invalid')

    def test_historical_checkpoint_jobs_match_original_profiles_and_workers(self):
        from scripts.balance.legacy_spring import select_spring
        pack = select_spring(apply_difficulty(self.pack, 'baby'), 'legacy')
        human = json.loads(route_v2.BERSERKER.read_text(encoding='utf-8'))
        expected = reproduction_v2.checkpoint_trials(pack, human, 2, 20261020)
        jobs = [('checkpoint_probes', checkpoints.DEFAULT_SCENARIO, 'hero', 2, 20261020,
                 {'difficulty': 'baby', 'spring': 'legacy', 'profile': name, 'checkpoint_entry': entry})
                for name, entry in human['profiles'].items()]
        serial = route_v2.run_jobs(jobs, 1)
        self.assertEqual(serial, route_v2.run_jobs(jobs, 2))
        self.assertEqual(expected, {row['profile']: {k: v for k, v in row.items() if k != 'profile'} for row in serial})

    def test_passive_matrix_reuses_only_identical_complete_histories(self):
        session = self.session('hero', 7, 'forest_wolves')
        groups = progression.definition(session)['passive_groups']
        table = {str(g['level']): g['options'][0] for g in groups}
        calls = []

        def observed_battles(template, n, seed, encounter):
            history = template['character']['passive_history']
            calls.append(tuple(history[str(level)] for level in (2, 4, 6)))
            return [{'won': int('heavy_armor_lore' in history.values()), 'rounds': 1} for _ in range(n)]

        parent = checkpoints.ROOT/'.tmp-test/053'
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as folder:
            path = Path(folder)/'checkpoint.json'
            path.write_text(json.dumps({'encounters': {'forest_wolves': {'characters': {'hero': {
                'snapshot': snapshots_v3.capture(session)}}}}}), encoding='utf-8')
            job = ('normal_passive_probes', checkpoints.DEFAULT_SCENARIO, 'hero', 2, 53,
                   {'difficulty': 'normal', 'spring': 'current', 'checkpoint_path': str(path), 'passive_table': table})
            with patch.object(probes_v3, 'battles', side_effect=observed_battles):
                rows = probes_v3.run_job(job)
        self.assertEqual(len(rows), 7)
        self.assertEqual(len(calls), 8)
        self.assertEqual(len(set(calls)), 8)
        for row in rows:
            expected = []
            for option in row['options']:
                choices = {**table, **row['previous_choices'], str(row['level']): option}
                expected.append(int(any(choices[str(level)] == 'heavy_armor_lore' for level in (2, 4, 6))))
            self.assertEqual([row['a'], row['b']], expected)

    def test_action_metadata_keeps_costs_live_and_follows_actor_replacement(self):
        session = self.session('cleric', 8)
        actor = session['character']
        definition = progression.definition(session)
        identifier, tier = next((p['id'], index + 1) for p in definition['passives']
                                for index, value in enumerate(p['tiers']) if 'sp_for_mp' in value['effects'])
        actor['passives'] = [{'id': identifier, 'tier': tier}]
        skill = next(s for s in actor['skills'] if s.get('cost_type') == 'mp' and s.get('cost', 0) >= 3)
        original_effects = progression.effects
        functions = (combat._combat_rules, combat._available_skills, combat.item_combat_spec)
        hero = self.session('hero', 8)
        hero_effects = original_effects(hero)
        costs = []
        with views_v3.action_rules(session):
            for sp in (0, actor['max_sp']):
                actor['sp'] = sp
                actual = combat._normal_skill(session, skill)
                with patch.object(progression, 'effects', original_effects):
                    expected = combat._normal_skill(session, skill)
                self.assertEqual(actual, expected)
                costs.append(actual['_resolved_costs'])
            session['character'] = hero['character']
            self.assertEqual(progression.effects(session), hero_effects)
        self.assertNotEqual(costs[0], costs[1])
        self.assertIs(progression.effects, original_effects)
        self.assertEqual((combat._combat_rules, combat._available_skills, combat.item_combat_spec), functions)

    def test_default_table_file_is_used_by_picker_and_standalone_probe(self):
        parent = checkpoints.ROOT/'.tmp-test/053'
        parent.mkdir(parents=True, exist_ok=True)
        sessions = {c: self.session(c, 2) for c in ('hero', 'cleric')}
        choices = {}
        for character, session in sessions.items():
            groups = progression.definition(session)['passive_groups']
            choices[character] = {str(g['level']): g['options'][1] for g in groups}
            session['character'].update(passives=[], passive_history={})
            session['pending_passive_choices'] = [2]
        with tempfile.TemporaryDirectory(dir=parent) as folder:
            path = Path(folder)/'defaults.json'
            path.write_text(json.dumps({'status': 'proposed', 'characters': {
                c: {'choices': value} for c, value in choices.items()}}), encoding='utf-8')
            with patch.object(archetypes, 'DEFAULT_PASSIVES', path):
                picker = archetypes.PassivePicker('table')
                for character, session in sessions.items():
                    chosen = picker.apply(session)
                    self.assertEqual(chosen['character']['passive_history']['2'], choices[character]['2'])
                checkpoint = Path(folder)/'checkpoint.json'
                snapshot = snapshots_v3.capture(self.session('hero', 4, 'forest_wolves'))
                checkpoint.write_text(json.dumps({'encounters': {'forest_wolves': {
                    'characters': {'hero': {'snapshot': snapshot}}}}}), encoding='utf-8')
                def outcomes(template, n, seed, encounter):
                    won = template['character']['passive_history']['4'] == choices['hero']['4']
                    return [{'won': int(won), 'rounds': 1} for _ in range(n)]
                settings = {'difficulty': 'normal', 'spring': 'current', 'checkpoint_path': str(checkpoint)}
                job = ('normal_passive_probes', checkpoints.DEFAULT_SCENARIO, 'hero', 1, 53, settings)
                with patch.object(probes_v3, 'battles', side_effect=outcomes):
                    loaded = probes_v3.run_job(job)
                    explicit = {str(g['level']): g['options'][0] for g in progression.definition(sessions['hero'])['passive_groups']}
                    overridden = probes_v3.run_job((*job[:5], {**settings, 'passive_table': explicit}))
                self.assertEqual([loaded[0]['a'], loaded[0]['b']], [1, 1])
                self.assertEqual([overridden[0]['a'], overridden[0]['b']], [0, 0])

    def test_check_probe_chooses_passives_before_and_between_forced_battles(self):
        selected = progression.definition(self.session('hero', 2))['passive_groups'][0]['options'][1]
        run = route_v2.MeasurementRun(self.pack, 'hero', 53, archetypes.ARCHETYPES['P2'],
                                     difficulty='normal', passive_table={'2': selected})
        action = next(a for loc in self.normal['locations'] for a in loc.get('actions', []) if a['id'] == 'force_seal')
        rng_state = run.rng.getstate()
        calls = []

        def apply_result(current, chosen, outcome):
            if outcome['success']:
                progression.reward(current, self.normal['progression']['exp_table']['2'], 'test:probe')

        def forced_battle(current, policy, rng, **kwargs):
            calls.append(current['character']['level'])
            if current['character']['level'] == 1:
                progression.reward(current, self.normal['progression']['exp_table']['2'], 'test:probe')
            else:
                self.assertEqual(current['character']['passive_history']['2'], selected)
                current['_probe_finished'] = True
            return {'continue': True}

        with patch.object(state, 'apply_action_result', side_effect=apply_result), \
             patch.object(class_aware, 'combat_pending', side_effect=lambda current: not current.get('_probe_finished')), \
             patch.object(route_v2, 'fight', side_effect=forced_battle):
            run.probe_check(action)
        self.assertEqual(calls, [2, 1, 2])
        self.assertEqual(run.session['character']['level'], 1)
        self.assertEqual(run.rng.getstate(), rng_state)


    def test_first_visit_does_not_rest_later_if_first_visit_full(self):
        run = route_v2.MeasurementRun(self.pack, 'hero', 1, archetypes.P0B)
        run.session['world_state'] = {'scene_id': 'dark_forest', 'location_id': 'elf_spring'}
        run.rest_point()
        run.session['character']['hp'] = 1
        run.rest_point()
        self.assertEqual(run.spring_rests, 0)


    def test_passive_modes_accept_engine_copy_outside_combat(self):
        for mode in ('first', 'table', 'enumerate'):
            session = self.session(level=2)
            session['character'].update(passives=[], passive_history={})
            session['pending_passive_choices'] = [2]
            before = deepcopy(session)
            picker = archetypes.PassivePicker(mode, {'2': 'heavy_armor_lore'})
            chosen = picker.apply(session)
            self.assertEqual(session, before)
            self.assertEqual(chosen['character']['passive_history']['2'], 'departure_spirit' if mode == 'first' else 'heavy_armor_lore')
            combat.ensure_combat_started(session)
            with self.assertRaises(ValueError):
                picker.apply(session)
        self.assertEqual(len(probes_v3.combinations(self.normal, 'hero')), 16)

    def test_exp_observation_includes_combat_and_quest_without_double_rewards(self):
        session = self.session(level=1, encounter='dark_forest_loc')
        session['character'].update(hp=500, max_hp=500)
        session['character']['attributes']['str'] = 200
        with snapshots_v3.ExpObserver():
            battle = route_v2.fight(session, 'best_free', random.Random(5))
            self.assertEqual(battle['status'], 'victory')
            progression.reward(session, 10, 'quest:test')
        observed = archetypes.ExpLevelModel().snapshot(session)
        self.assertEqual(observed['exp'], self.normal['progression']['exp_rewards']['trash'] + 10)
        self.assertEqual(sum(observed['sources'].values()), observed['exp'])
        self.assertEqual(observed['sources']['trash'], self.normal['progression']['exp_rewards']['trash'])
        self.assertEqual(observed['sources']['quest'], 10)

    def test_level_probes_use_engine_growth_skills_and_table_passives(self):
        session = self.session('mage', level=4)
        table = {str(g['level']): g['options'][0] for g in progression.definition(session)['passive_groups']}
        higher = snapshots_v3.at_level(session, 5, table)
        lower = snapshots_v3.at_level(session, 3, table)
        gains = self.normal['progression']['level_gains']['mage']
        expected = sum(gains.get('by_level', {}).get(str(level), {}).get('max_hp', gains['max_hp'])
                       for level in (4, 5))
        self.assertEqual(higher['character']['max_hp']-lower['character']['max_hp'], expected)
        self.assertIn('twin_storm', {s['id'] for s in higher['character']['skills']})
        self.assertNotIn('twin_storm', {s['id'] for s in lower['character']['skills']})
        self.assertEqual(set(higher['character']['passive_history']), {'2', '4'})

    def test_legal_pairs_target_weakness_cooldown_dual_cost_and_limit(self):
        session = self.start('hero', 8, 'dragon_valley_loc')
        actor = session['character']
        charm = deepcopy(next(i for i in self.normal['items'] if i['id'] == 'ice_charm'))
        actor['inventory'].append({**charm, 'quantity': 1})
        enemy = session['combat']['enemies'][0]
        second = deepcopy(enemy); second['id'] = 'second'; second['resistances']['ice'] = .5
        session['combat']['enemies'].append(second)
        pairs = policy_v3.legal_pairs(session)
        self.assertTrue(any(a['id'] == 'ice_charm' and t['id'] == enemy['id'] for a, t in pairs))
        self.assertFalse(any(a['id'] == 'ice_charm' and t['id'] == 'second' for a, t in pairs))
        actor['mp'] = 0
        self.assertFalse(any(a['id'] == 'dragon_slash' for a, _ in policy_v3.legal_pairs(session)))
        session['combat'].setdefault('cooldowns', {})['skill:divine_guard'] = {'remaining': 1, 'used_round': 1}
        self.assertFalse(any(a['id'] == 'divine_guard' for a, _ in policy_v3.legal_pairs(session)))
        cleric = self.start('cleric', 8)
        cleric['combat']['passive_state'].setdefault('uses', {})['seraphim_gospel'] = 1
        self.assertFalse(any(a['id'] == 'seraphim_gospel' for a, _ in policy_v3.legal_pairs(cleric)))

    def test_cleanse_is_valued_and_sanctuary_heal_is_free(self):
        session = self.start('cleric', 5)
        actor = session['character']
        actor['hp'] = int(actor['max_hp']*.8)
        status_effects.apply(session, actor, {'id': 'burn', 'duration': 2, 'tick': {'damage': '20', 'element': 'fire'}},
                             session['combat']['enemies'][0], random.Random(3))
        action, target = sim.choose_action(session, 'heuristic_v3')
        self.assertEqual(action['id'], 'great_heal_cleanse')
        sim.perform_action(session, action, target, random.Random(53))
        self.assertFalse(any(s['id'] == 'burn' for s in session['character'].get('statuses', [])))
        free = self.start('cleric', 8)
        free['character'].update(hp=1, mp=0, sp=0)
        action, _ = sim.choose_action(free, 'heuristic_v3')
        self.assertEqual(action['id'], 'healing_prayer')
        self.assertFalse(any(action['costs'].values()))

    def test_heuristic_never_rejected_and_free_actions_are_bounded(self):
        for character in archetypes.CHARACTERS:
            session = self.start(character, 8, 'dragon_valley_loc')
            seen = set()
            rng = random.Random(53)
            for _ in range(160):
                if not combat.combat_is_active(session):
                    break
                action, target = sim.choose_action(session, 'heuristic_v3')
                if action.get('free_action'):
                    key = (session['combat']['round'], action['id'])
                    self.assertNotIn(key, seen)
                    seen.add(key)
                sim.perform_action(session, action, target, rng)
            self.assertFalse(combat.combat_is_active(session))

    def test_normal_hit_expectation_matches_engine_and_is_pure(self):
        session = self.start('thief', 1)
        enemy = session['combat']['enemies'][0]
        ability = {'damage': '10', 'accuracy': 10, 'element': 'physical', 'true_damage': False, 'ignores_defense': True}
        before = deepcopy(session)
        mu, _ = policy_v3.strike_moments(session, enemy, session['character'], ability, enemy['id'])
        expected = combat.attack_chance(session, enemy, session['character'], ability, enemy['id']) / 100 * 10
        self.assertAlmostEqual(mu, expected)
        self.assertEqual(session, before)
        self.assertNotEqual(combat.actor_evade(session, session['character']), session['character']['combat'].get('evade', 0))

    def test_policy_decision_is_pure_and_cached_views_do_not_escape(self):
        session = self.start('mage', 7, 'dragon_valley_loc')
        before = deepcopy(session)
        effects, rules = progression.effects, combat._combat_rules
        action, target = sim.choose_action(session, 'heuristic_v3')
        self.assertEqual(session, before)
        self.assertIs(progression.effects, effects)
        self.assertIs(combat._combat_rules, rules)
        combat.perform_combat_action(session, action['type'], action['id'], target, rng=random.Random(53))

    def test_cached_and_uncached_decisions_agree_across_difficulties(self):
        cp = json.loads(checkpoints.DEFAULT_CHECKPOINTS.read_text(encoding='utf-8'))
        for difficulty in ('baby', 'normal'):
            for character in archetypes.CHARACTERS:
                session = self.start(character, 8, 'dragon_valley_loc') if difficulty == 'normal' else sim.prepare_session(self.pack, 'dragon_valley_loc', character, cp)
                if difficulty == 'baby':
                    combat.ensure_combat_started(session)
                rng = random.Random(53)
                for _ in range(8):
                    if not combat.combat_is_active(session):
                        break
                    for policy in (*sim.LEGACY_POLICIES, 'best_free'):
                        before = rng.getstate()
                        cached = sim.choose_action(session, policy)
                        self.assertEqual(cached, sim._choose_action(session, policy))
                        self.assertEqual(rng.getstate(), before)
                    action, target = sim.choose_action(session, 'heuristic_v3' if difficulty == 'normal' else 'heuristic')
                    sim.perform_action(session, action, target, rng)

    def test_current_baby_check_only_reports(self):
        with patch.object(sim, 'simulate', return_value={}), patch('builtins.print'), \
             patch.object(sim, 'check_results', return_value=[{'metric': 'win_rate'}]) as check:
            self.assertEqual(sim.main(['--check', '--encounters', 'forest_wolves', '--characters', 'hero', '--n', '1']), 0)
            check.assert_not_called()

    def test_battle_records_engine_statuses_costs_and_skill_usage(self):
        session = self.session('thief', 5)
        summary = route_v2.fight(session, 'heuristic_v3', random.Random(9))
        self.assertTrue(summary['skill_usage'])
        self.assertTrue(any(r['applications'] for r in summary['statuses']))
        self.assertEqual(summary['expected_hp_loss'], summary['direct_expected_hp_loss']+summary['status_hp_loss'])
        self.assertTrue(any(r['uses'] for r in summary['skill_usage'].values()))

    def test_normal_instrumentation_preserves_character_outcome_and_rng(self):
        left = self.session('thief', 5)
        right = deepcopy(left)
        rng1, rng2 = random.Random(53), random.Random(53)
        with patch.object(combat, 'random', rng1), patch.object(state, 'random', rng1):
            measured = route_v2.fight(left, 'heuristic_v3', rng1)
        with patch.object(combat, 'random', rng2), patch.object(state, 'random', rng2):
            plain = route_v2.fight(right, 'heuristic_v3', rng2, instrument=False)
        self.assertEqual(measured['status'], plain['status'])
        self.assertEqual(left['character'], right['character'])
        self.assertEqual(rng1.getstate(), rng2.getstate())

    def test_skipped_skill_attempt_is_not_an_actual_cast(self):
        session = self.session('hero', 3)
        session['character'].update(hp=500, max_hp=500, mp=500, max_mp=500)
        original_skip = status_effects.skip_action
        skipped = []
        def skip(current, actor, rng):
            if actor is current['character'] and not skipped:
                skipped.append(True)
                return True
            return original_skip(current, actor, rng)
        original_choose = sim.choose_action
        def choose(current, policy, **kwargs):
            if policy == 'best_free':
                current['combat']['enemies'] = current['combat']['enemies'][:1]
                current['combat']['enemies'][0]['hp'] = 1
                return original_choose(current, policy, **kwargs)
            action = next(a for a in combat.combat_actions(current) if a['id'] == 'holy_sword_art')
            return action, current['combat']['enemies'][0]['id']
        with patch.object(status_effects, 'skip_action', side_effect=skip), patch.object(sim, 'choose_action', side_effect=choose):
            result = route_v2.fight(session, 'heuristic_v3', random.Random(53))
        usage = result['skill_usage']['holy_sword_art']
        self.assertEqual((usage['attempts'], usage['uses']), (2, 1))
        self.assertEqual(usage['rounds'], [2])

    def test_next_round_passive_damage_is_not_assigned_to_healing_skill(self):
        session = self.session('cleric', 6)
        session = probes_v3.with_passives(session, {'2': 'pious_heart', '4': 'pious_heart', '6': 'holy_halo'})
        session['character'].update(hp=500, max_hp=500, mp=500, max_mp=500)
        session['scenario_pack']['combat_rules']['max_rounds'] = 1
        original_choose = sim.choose_action
        def choose(current, policy, **kwargs):
            if policy == 'best_free':
                return original_choose(current, policy, **kwargs)
            action = next(a for a in combat.combat_actions(current) if a['id'] == 'healing_prayer')
            return action, current['combat']['enemies'][0]['id']
        with patch.object(sim, 'choose_action', side_effect=choose):
            result = route_v2.fight(session, 'heuristic_v3', random.Random(53))
        usage = result['skill_usage']['healing_prayer']
        self.assertEqual(usage['uses'], 1)
        self.assertEqual(usage['damage'], 0)
        self.assertEqual(usage['hits'], 0)

    def test_scroll_purchase_learning_class_money_and_stock(self):
        for character, gold, expected in [('mage', 75, 2), ('mage', 34, 0), ('mage', 39, 1), ('mage', 74, 1), ('hero', 75, 0)]:
            run = route_v2.MeasurementRun(self.pack, character, 2, archetypes.P1, difficulty='normal')
            run.session['world_state'] = {'scene_id': 'castle_town', 'location_id': 'magic_shop'}
            run.session['character']['gold'] = gold
            run.buy_scrolls()
            self.assertEqual(len(run.scrolls), expected)
            run.buy_scrolls()
            self.assertEqual(len(run.scrolls), expected)
            if expected:
                for scroll in run.scrolls:
                    self.assertIn(scroll['skill'], run.session['character']['learned_spells'])
                run.session['character']['gold'] = 1000
                with self.assertRaises(ValueError):
                    trade(run.session, 'magic_shop', run.scrolls[0]['item'], 1)

    def test_engine_refuses_nonmage_and_duplicate_scroll_learning(self):
        for character in ('hero', 'mage'):
            session = self.session(character)
            session.pop('combat_start_requested', None)
            scroll = deepcopy(next(i for i in self.normal['items'] if i['id'] == 'spellbook_lightning'))
            session['character']['inventory'].append({**scroll, 'quantity': 2})
            if character == 'mage':
                session = progression.learn_spell(session, scroll['id'])
            with self.assertRaises(ValueError):
                progression.learn_spell(session, scroll['id'])

    def test_final_value_gap_holds_other_final_table_choices_fixed(self):
        rows = []
        for definition in self.normal['class_progression']:
            character = definition['id']
            groups = definition['passive_groups']
            for choices in probes_v3.combinations(self.normal, character):
                wins = (2 if choices['2'] == groups[0]['options'][1] else 1) if choices['4'] == groups[1]['options'][1] else 0
                rows.append(dict(character=character, choices=choices, n=2, ignis_wins=wins, ignis_rate=wins/2,
                                 reached_levels={}, outcomes=[int(i < wins) for i in range(2)]))
        defaults = probes_v3.choose_defaults(self.normal, rows)
        hero = defaults['characters']['hero']
        self.assertEqual(hero['evidence'][0]['absolute_gap_pp'], 0)
        self.assertEqual(hero['value_pairs'][0]['absolute_gap_pp'], 50)

    def test_sustain_main_excludes_free_heal_and_respects_fire_resistance(self):
        from scripts.balance.battle_v3 import sustain
        session = self.start('cleric', 8, 'dragon_valley_loc')
        companion = next(c for c in self.normal['companions'] if c['id'] == 'fire_bat_dragon')
        session['companion'] = companion
        expected = session['character']['max_hp']*progression.effects(session)['regen_ratio']
        self.assertAlmostEqual(sustain(session), expected)
        session['combat']['enemies'][0]['resistances']['fire'] = 1
        self.assertGreater(sustain(session), expected)

    def test_snapshot_is_deterministic_and_median_comes_from_observations(self):
        sessions = [self.session('hero', level=level) for level in (2, 4, 4)]
        self.assertEqual(snapshots_v3.capture(sessions[1]), snapshots_v3.capture(sessions[2]))
        snapshot = snapshots_v3.capture(sessions[0])
        self.assertEqual(snapshots_v3.restore(self.normal, snapshot)['character'], sessions[0]['character'])

    def test_checkpoint_selects_first_observed_median_level_sample(self):
        levels = iter((2, 4, 4))
        def sample(pack, character, seed, archetype, **kwargs):
            level = next(levels)
            return dict(archetype='P2', character=character, seed=seed, steps=[], quest_attempts=[], battles=[],
                        snapshots={'dragon_valley_loc': {'character': {'character_id': character, 'level': level}}})
        with patch.object(route_v2, 'trial', side_effect=sample):
            records = route_v2._job((checkpoints.DEFAULT_SCENARIO, 'P2', 'hero', 3, 53,
                                     {'difficulty': 'normal', 'spring': 'current'}))
        entry = records[0]['checkpoint_candidates']['dragon_valley_loc']
        self.assertEqual(entry['median_level'], 4)
        self.assertEqual(entry['trial_index'], 1)
        self.assertEqual(entry['level_histogram'], {'2': 1, '4': 2})
        exported = probes_v3.export_checkpoints(records, {'seed': 53})
        self.assertEqual(exported['encounters']['dragon_valley_loc']['characters']['hero']['snapshot']['character']['level'], 4)

    def test_crn_pairing_and_95_percent_comparison(self):
        rows = probes_v3.paired([{'won': 0}]*100, [{'won': 1}]*100)
        self.assertGreater(rows['ci95'][0], 0)
        self.assertEqual(rows['b_minus_a'], 1)
        seen = []
        def record(pack, character, seed, archetype, **kwargs):
            seen.append(seed)
            return dict(ignis_defeated=False, completed=False, levels={'castle': 1})
        with patch.object(route_v2, 'trial', side_effect=record):
            rows = probes_v3.enumerate_job(('enumerate_probes', checkpoints.DEFAULT_SCENARIO, 'thief', 2, 53, {}))
        self.assertEqual(len(rows), 16)
        self.assertEqual(len(set(seen[:2])), 2)
        self.assertTrue(all(seen[i:i+2] == seen[:2] for i in range(0, len(seen), 2)))

    def test_baby_gates_report_only_and_historical_artifact_never_written(self):
        targets = json.loads((checkpoints.ROOT/'eval/balance/targets.json').read_text(encoding='utf-8'))
        metrics = metrics_v3.evaluate({'difficulty': 'baby', 'targets': targets, 'records': [dict(archetype='P0b', character='hero', completed=True, battles=[])]})
        self.assertEqual(metrics[0]['status'], 'report')
        self.assertFalse(any(m['hard_gate'] for m in metrics))
        before = route_v2.BERSERKER.stat().st_mtime_ns
        measurement_v3.frozen_write(route_v2.BERSERKER, route_v2.BERSERKER.read_text(encoding='utf-8'))
        self.assertEqual(route_v2.BERSERKER.stat().st_mtime_ns, before)
        with self.assertRaises(ValueError):
            measurement_v3.frozen_write(route_v2.BERSERKER, '{}')

    def test_p3_returns_to_hot_spring_and_completes_mina_through_engine(self):
        run = route_v2.MeasurementRun(self.normal, 'hero', 53, archetypes.ARCHETYPES['P3'],
                                      difficulty='normal', effective=True, passive_table={})
        run.session['world_state'] = {'scene_id': 'cave_prism_tree', 'location_id': 'cave_prism_tree'}
        run.session['flags'].update(cleared_cave_prism_tree=True, cleared_cave_crystal_corridor=True,
                                    cleared_cave_heat_corridor=True, met_mina=True, mina_waiting=True)
        run.session['companion'] = deepcopy(next(c for c in self.normal['companions'] if c['id'] == 'fire_bat_dragon'))
        run.hook('after_tree')
        self.assertEqual(run.location, 'elf_spring')
        self.assertTrue(run.session['flags']['mina_rescued'])
        self.assertEqual(run.session['companion']['id'], 'mina')
        self.assertEqual([step['action'] for step in run.steps[:5]],
                         ['prism_back', 'hazard_054_03', 'crystal_back', 'cave_right', 'escort_mina'])
        run.session['world_state'] = {'scene_id': 'magic_shop', 'location_id': 'magic_shop'}
        run.hook('magic_return')
        self.assertTrue(run.session['flags']['mina_quest_done'])
        self.assertIn('side_mina', run.session['character']['exp_rewarded_quests'])
        self.assertIsNone(run.session.get('companion'))

    def test_normal_child_jobs_keep_difficulty_and_match_serial(self):
        jobs = [(checkpoints.DEFAULT_SCENARIO, a, 'hero', 1, 53, {'difficulty': 'normal', 'spring': 'current'}) for a in ('P0b', 'P2')]
        serial = route_v2.run_jobs(jobs, 1)
        self.assertEqual(serial, route_v2.run_jobs(jobs, 2))
        self.assertEqual(serial, route_v2.run_jobs(jobs, 1))
        self.assertTrue(all(r['difficulty'] == 'normal' for r in serial))
        for record in serial:
            for node in record['exp_nodes'].values():
                self.assertEqual(sum(node['sources'].values()), node['exp'])


if __name__ == '__main__':
    unittest.main()
