from __future__ import annotations

import random
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import combat, free_actions, state, shops
from host.maps import public_maps
from host.quests import public_quests
from scripts.balance import checkpoints
from scripts.scenario import upgrade_ch5


class Chapter5Tests(unittest.TestCase):
    def sessions(self, location='festival_town'):
        for filename in ('dragon_rpg.json', 'dragon_rpg_hybrid.json'):
            pack = state.load_scenario_pack(checkpoints.DEFAULT_SCENARIO.with_name(filename))
            s = checkpoints.fresh_session(pack, 'hero')
            s['world_state'] = dict(scene_id='castle_return', location_id='fixture')
            s['flags']['returned_to_capital'] = True
            state.apply_state_delta(s, {'current_location': location}, allow_world_transition=True)
            yield s

    def act(self, s, identifier, success=True):
        a = state.resolve_action(s, action_id=identifier)
        self.assertIsNotNone(a, identifier)
        self.assertTrue(state.action_requirement_status(a, s)[0], identifier)
        return state.apply_action_result(s, a, dict(dc=a.get('roll', {}).get('dc', 0), success=success))

    def add(self, s, *names):
        state.apply_state_delta(s, {'inventory_add': [{'name': name} for name in names]})

    def finish(self, s, victory=True):
        if not s.get('combat'):
            s['combat_start_requested'] = True
            combat.ensure_combat_started(s)
        if victory:
            for e in s['combat']['enemies']:
                e['hp'] = 0
        else:
            s['character']['hp'] = 0
        combat._check_victory_or_defeat(s)
        state.apply_state_delta(s, combat.consume_combat_state_delta(s), allow_world_transition=True)
        combat.clear_combat_after_resolution(s)

    def visible(self, s):
        return {a['id'] for a in state.public_session(s)['choices']}

    def test_both_ignis_routes_and_chapter_lock(self):
        for location in ('ignis_last_breath', 'ignis_purified'):
            for s in self.sessions():
                s['flags'] = {}
                s['world_state'] = dict(scene_id='dragon_valley', location_id=location)
                self.act(s, 'return_to_castle_report')
                self.assertEqual(state.current_location_id(s), 'royal_gate')
                self.assertTrue(s['flags']['returned_to_capital'])
                self.act(s, 'enter_festival_town')
                self.assertEqual(public_maps(s)['current_map_id'], 'royal_return')
                for store in ('inn', 'forge', 'magic_shop', 'item_shop'):
                    self.act(s, f'go_{store}')
                    self.assertFalse(state.commit_world_position(s, location_id='forest_exit')[0])
                    self.assertFalse(state.commit_world_position(s, location_id='castle')[0])
                    self.act(s, f'return_castle_from_{store}')
                    self.assertEqual(state.current_location_id(s), 'festival_town')

    def test_old_report_save_loads(self):
        for s in self.sessions('castle_report'):
            s['flags'] = {}
            s['id'] = 'legacy'
            s['scenario_path'] = str(checkpoints.DEFAULT_SCENARIO)
            s['scenario_pack']['meta']['content_revision'] = '2026-10-01'
            with tempfile.TemporaryDirectory() as tmp, patch.object(state, 'SAVE_DIR', Path(tmp)):
                state.save_session(s)
                restored = state.load_session('legacy')
            self.assertEqual(state.current_location_id(restored), 'castle_report')
            self.assertTrue(restored['flags']['returned_to_capital'])

    def test_mansion_unlock_and_entry_methods(self):
        for s in self.sessions():
            self.assertNotIn('go_general_mansion', self.visible(s))
            for flag in ('heard_gald_rumor', 'noticed_general_frost', 'heard_xanxus_betrayal'):
                t = deepcopy(s)
                state.apply_state_delta(t, {'flags_set': [flag]})
                self.assertIn('go_general_mansion', self.visible(t))
                self.assertTrue(t['flags']['mansion_unlocked'])
            self.add(s, '白い竜鱗')
            self.assertTrue(s['flags']['mansion_unlocked'])
            self.assertEqual(next(q for q in public_quests(s) if q['id'] == 'side_general_mansion')['status'], 'active')
            for identifier, success, robin, alert in [('sneak_into_mansion', True, False, False), ('sneak_into_mansion', False, False, True), ('robin_picks_lock', True, True, False)]:
                t = deepcopy(s)
                t['flags']['recruited_robin'] = robin
                self.act(t, 'go_general_mansion')
                self.assertEqual(public_maps(t)['current_map_id'], 'general_mansion')
                free_actions.adjudicate(t, dict(kind='interact', operation='observe', target_id='frozen_fountain', item_id='', action_id='', advance=False, approach='観察する', reply=''))
                self.assertTrue(t['flags']['noticed_general_frost'])
                self.act(t, identifier, success)
                self.assertEqual(state.current_location_id(t), 'mansion_corridor')
                self.assertEqual(bool(t['flags'].get('mansion_alert')), alert)
                with patch.object(combat, '_enemy_phase') as first:
                    self.act(t, 'fight_ice_sentinels')
                    combat.ensure_combat_started(t)
                self.assertEqual(first.call_count, int(alert))

    def test_corridor_both_outcomes_and_sneak(self):
        for s in self.sessions('mansion_corridor'):
            for win in (True, False):
                t = deepcopy(s)
                self.act(t, 'fight_ice_sentinels')
                self.finish(t, win)
                self.assertEqual(state.current_location_id(t), 'mansion_study' if win else 'festival_town')
                self.assertIsNone(t.get('game_over'))
                if not win:
                    self.assertEqual(t['character']['hp'], 1)
            t = deepcopy(s)
            self.act(t, 'evade_ice_sentinels')
            self.assertEqual(state.current_location_id(t), 'mansion_study')
            self.act(s, 'evade_ice_sentinels', False)
            with patch.object(combat, '_enemy_phase') as first:
                combat.ensure_combat_started(s)
            self.assertEqual(first.call_count, 1)

    def test_study_items_once_and_journal_exposure(self):
        for s in self.sessions('mansion_study'):
            for identifier in ('take_draco_journal', 'open_scale_box'):
                self.act(s, identifier)
                self.assertFalse(state.action_requirement_status(state.resolve_action(s, action_id=identifier), s)[0])
            self.assertEqual(next(q for q in public_quests(s) if q['id'] == 'side_general_mansion')['status'], 'completed')
            self.act(s, 'leave_mansion_study')
            self.act(s, 'go_report_hall')
            self.assertIn('あなたが日誌を掲げると、ドラコの表情から初めて笑みが消えた。', self.act(s, 'report_with_evidence')['result_text'])

    def test_audience_every_evidence_and_clue_and_safe_rest(self):
        for s in self.sessions():
            self.assertNotIn('request_king_audience', self.visible(s))
            clues = next(q['clue_flags'] for q in s['scenario_pack']['quests'] if q['id'] == 'mystery_frost')
            for flag in clues:
                t = deepcopy(s)
                t['flags'][flag] = True
                self.assertIn('request_king_audience', self.visible(t), flag)
            for item in ('白い竜鱗', '白竜の日誌', '刺客の徽章'):
                t = deepcopy(s)
                self.add(t, item)
                self.assertIn('request_king_audience', self.visible(t))
                self.act(t, 'request_king_audience')
                self.act(t, 'confide_in_king')
                t['character'].update(hp=1, mp=0, sp=0)
                self.act(t, 'ask_king_rest')
                self.assertFalse(t['flags'].get('assassins_attacked'))
                for r in ('hp', 'mp', 'sp'):
                    self.assertEqual(t['character'][r], t['character'][f'max_{r}'])

    def test_town_thanks_once_in_order(self):
        for s in self.sessions('royal_gate'):
            flags = ('mina_quest_done', 'riku_returned', 'saved_gald', 'robert_hammer_returned')
            s['flags'].update({f: True for f in flags})
            self.act(s, 'enter_festival_town')
            entries = [e['text'] for e in s['event_log'] if e['kind'] == 'location_hint' and not e['data'].get('narrate')]
            self.assertEqual(len(entries), 4)
            self.assertIn('ミーナ', entries[0])
            self.act(s, 'go_inn')
            self.act(s, 'return_castle_from_inn')
            self.assertEqual(entries, [e['text'] for e in s['event_log'] if e['kind'] == 'location_hint' and not e['data'].get('narrate')])

    def test_assassin_conditions_individually_and_payment(self):
        for s in self.sessions('inn'):
            s['character'].update(hp=1, gold=20)
            for missing in ('returned_to_capital', 'evidence', 'unrevealed', 'first_time', None):
                for item in ('白い竜鱗', '白竜の日誌'):
                    t = deepcopy(s)
                    if missing != 'evidence':
                        self.add(t, item)
                    if missing == 'returned_to_capital':
                        t['flags'].pop('returned_to_capital')
                    if missing == 'unrevealed':
                        t['flags']['draco_revealed'] = True
                    if missing == 'first_time':
                        t['flags']['assassins_attacked'] = True
                    self.act(t, 'rest_at_inn')
                    self.assertEqual(t['character']['gold'], 10)
                    self.assertEqual(state.current_location_id(t), 'inn_night_ambush' if missing is None else 'inn')
                    self.assertEqual(t['character']['hp'], 1 if missing is None else t['character']['max_hp'])
            s['character']['gold'] = 9
            self.assertFalse(state.action_requirement_status(state.resolve_action(s, action_id='rest_at_inn'), s)[0])

    def test_robin_warning_and_both_ambush_results(self):
        for s in self.sessions('inn'):
            for robin in (False, True):
                for win in (False, True):
                    t = deepcopy(s)
                    t['flags']['recruited_robin'] = robin
                    self.add(t, '白い竜鱗', '白竜の日誌')
                    t['character'].update(hp=2, mp=0, sp=0, gold=10)
                    self.act(t, 'rest_at_inn')
                    t['enemy_first_requested'] = True
                    with patch.object(combat, '_enemy_phase') as first:
                        combat.ensure_combat_started(t)
                    self.assertEqual(first.call_count, int(not robin))
                    self.assertEqual(any(e['kind'] == 'warning' for e in t['combat']['log']), robin)
                    self.assertFalse(t['combat']['encounter']['flee_allowed'])
                    self.finish(t, win)
                    self.assertEqual(state.current_location_id(t), 'inn')
                    self.assertIsNone(t['game_over'])
                    self.assertEqual(t['character']['gold'], 40 if win else 0)
                    self.assertTrue(t['flags']['draco_journal'])
                    if win:
                        self.assertTrue(t['flags']['has_assassin_crest'])
                        self.assertTrue(t['flags']['assassins_defeated'])
                        for resource in ('hp', 'mp', 'sp'):
                            self.assertEqual(t['character'][resource], t['character'][f'max_{resource}'])
                    else:
                        self.assertTrue(t['flags']['scale_stolen'])
                        self.assertEqual(t['character']['hp'], 1)
                        self.assertFalse(state._session_requirement_passes({'has_item': '白い竜鱗'}, t))
                    self.act(t, 'return_castle_from_inn')
                    self.act(t, 'go_report_hall')
                    self.act(t, 'report_with_evidence')

    def test_crest_counts_once_and_scale_loss_with_other_clues(self):
        for s in self.sessions('castle_report'):
            self.add(s, '刺客の徽章')
            a = state.resolve_action(s, action_id='report_with_evidence')
            self.assertFalse(state.action_requirement_status(a, s)[0])
            state.apply_state_delta(s, {'flags_set': ['heard_xanxus_betrayal', 'scale_stolen']})
            self.assertTrue(state.action_requirement_status(a, s)[0])
            self.assertEqual(next(q for q in public_quests(s) if q['id'] == 'mystery_frost')['clue_count'], 2)

    def test_actual_scale_theft_without_journal_retains_clue_route(self):
        for s in self.sessions('inn'):
            self.add(s, '白い竜鱗')
            s['character']['gold'] = 10
            s['flags'].update(frost_trace_seen=True, heard_xanxus_betrayal=True)
            self.act(s, 'rest_at_inn')
            with patch.object(combat, '_enemy_phase'):
                combat.ensure_combat_started(s)
            self.finish(s, False)
            self.assertFalse(state._session_requirement_passes({'has_item': '白い竜鱗'}, s))
            self.assertFalse(state._session_requirement_passes({'has_item': '白竜の日誌'}, s))
            self.act(s, 'return_castle_from_inn')
            self.act(s, 'go_report_hall')
            self.act(s, 'report_with_evidence')

    def test_ignis_and_modifiers_do_not_follow_draco_template_elsewhere(self):
        for s in self.sessions('mansion_corridor'):
            s['flags'].update(ignis_ally=True, king_trust=True, mina_quest_done=True)
            encounter = state._current_location_record(s)['combat']
            encounter['enemy_ids'] = ['draco_human']
            s['combat_start_requested'] = True
            combat.ensure_combat_started(s)
            self.assertEqual(s['combat']['active_modifiers'], [])
            s['combat']['enemies'][0]['hp'] = 0
            combat._check_victory_or_defeat(s)
            self.assertEqual(s['combat']['active_modifiers'], [])
            self.assertEqual(s['combat']['phase_allies'], [])

    def test_modifiers_activation_per_phase_and_scope(self):
        for s in self.sessions('draco_battle'):
            modifiers = state._current_location_record(s)['combat']['encounter_modifiers']
            for modifier in modifiers:
                if modifier.get('difficulty_only') == ['normal']:
                    continue  # Normal-only variants are exercised by test_holy_sword_049.
                for enabled in (False, True):
                    t = deepcopy(s)
                    req = modifier['requirements']
                    for r in req.get('all', [req]):
                        if enabled and 'flag' in r:
                            t['flags'][r['flag']] = True
                        if enabled and 'has_item' in r:
                            self.add(t, r['has_item'])
                    combat.ensure_combat_started(t)
                    phase1 = [m['id'] for m in t['combat']['active_modifiers']]
                    self.assertEqual(modifier['id'] in phase1, enabled and modifier['enemy_ids'] == ['draco_human'])
                    t['combat']['enemies'][0]['hp'] = 0
                    combat._check_victory_or_defeat(t)
                    phase2 = [m['id'] for m in t['combat']['active_modifiers']]
                    self.assertEqual(modifier['id'] in phase2, enabled and modifier['enemy_ids'] == ['draco_dragon'])
                    combat._activate_encounter_modifiers(t)
                    self.assertEqual(sum(e['kind'] == 'support' and e['actor'] == modifier['id'] for e in t['combat']['log']), int(enabled))
                    t['combat'] = None
                    t['world_state'] = dict(scene_id='castle_return', location_id='inn_night_ambush')
                    with patch.object(combat, '_enemy_phase'):
                        combat.ensure_combat_started(t)
                    self.assertEqual(t['combat']['active_modifiers'], [])

    def test_actual_damage_accuracy_followup_and_no_template_mutation(self):
        for s in self.sessions('draco_battle'):
            baseline = deepcopy(s['scenario_pack'])
            s['flags'].update(king_trust=True, recruited_robin=True, cleared_goblin_fort=True, mina_quest_done=True, robert_hammer_returned=True)
            self.add(s, '霜封じの護符')
            combat.ensure_combat_started(s)
            enemy = s['combat']['enemies'][0]
            rng = random.Random(1)
            combat._resolve_attack(s, s['character'], enemy, dict(name='攻撃', damage='10', accuracy=100, element='physical'), 'player', rng)
            self.assertEqual(s['combat']['log'][-1]['data']['damage'], 10)
            combat._resolve_attack(s, enemy, s['character'], enemy['skills'][0], enemy['id'], rng)
            data = s['combat']['log'][-1]['data']
            self.assertEqual(data.get('hit_chance', data.get('chance')), 90)
            enemy['hp'] = 0
            combat._check_victory_or_defeat(s)
            dragon = s['combat']['enemies'][0]
            self.assertEqual(combat._modified_received_damage(s, 100, 'ice', dragon, '凍てつく吐息'), 56)
            self.assertEqual(combat._modified_received_damage(s, 100, 'physical', dragon, '白翼の薙ぎ払い'), 100)
            combat._player_attack(s, dragon['id'], rng)
            self.assertTrue(any(e['text'].startswith('霜断ちの刻印が') for e in s['combat']['log']))
            self.assertEqual(s['scenario_pack'], baseline)

    def test_gald_stock_price_condition_and_oil(self):
        for s in self.sessions():
            with self.assertRaises(shops.ShopError):
                shops.public_shop(s, 'gald_capital_shop')
            s['flags']['saved_gald'] = True
            s['character']['gold'] = 80
            shops.trade(s, 'gald_capital_shop', 'fire_dragon_oil', 2)
            self.assertEqual(s['character']['gold'], 0)
            self.assertEqual(shops.public_shop(s, 'gald_capital_shop')['items'][0]['stock'], 0)
            self.assertEqual(next(i for i in s['character']['inventory'] if i.get('id') == 'fire_dragon_oil')['combat']['element'], 'fire')

    def test_enemy_combo_has_two_attacks_and_poison(self):
        for s in self.sessions('inn_night_ambush'):
            s['flags']['recruited_robin'] = True
            combat.ensure_combat_started(s)
            enemy = s['combat']['enemies'][0]
            with patch.object(combat, '_resolve_attack') as attack:
                combat._execute_enemy_ability(s, enemy, enemy['skills'][0], random.Random(1))
            self.assertEqual(attack.call_count, 2)
            self.assertEqual(enemy['skills'][1]['on_hit_status']['damage'], '2')

    def test_enemy_first_returns_control_and_oil_is_usable(self):
        for s in self.sessions('inn_night_ambush'):
            s['character'].update(hp=200, max_hp=200)
            self.add(s, '火竜の油')
            with patch.object(combat, 'random', random.Random(8)):
                combat.ensure_combat_started(s)
            self.assertEqual(s['combat']['turn'], 'player')
            actions = combat.combat_actions(s)
            self.assertTrue(any(a['id'] == 'fire_dragon_oil' for a in actions))
            combat.perform_combat_action(s, 'item', 'fire_dragon_oil', s['combat']['enemies'][0]['id'], rng=random.Random(1))
            self.assertFalse(any(i.get('id') == 'fire_dragon_oil' for i in s['character']['inventory']))

    def test_entry_prose_is_verbatim_and_robin_requires_both_flags(self):
        for s in self.sessions('royal_gate'):
            result = self.act(s, 'enter_festival_town')
            self.assertEqual(result['result_text'], state._current_location_record(s)['description'])
            for flag in ('recruited_robin', 'cleared_goblin_fort'):
                t = deepcopy(s)
                t['flags'][flag] = True
                t['world_state'] = dict(scene_id='castle_return', location_id='draco_battle')
                combat.ensure_combat_started(t)
                self.assertNotIn('robin', [m['id'] for m in t['combat']['active_modifiers']])

    def test_both_packs_identical_new_content(self):
        packs = [s['scenario_pack'] for s in self.sessions()]
        for key in ('maps', 'quests', 'shops', 'chapter_locks', 'item_flags'):
            self.assertEqual(packs[0][key], packs[1][key], key)
        for key, identifiers in [('enemies', ('ice_sentinel', 'ice_assassin')),
                                 ('items', ('draco_journal', 'frost_seal_charm', 'assassin_crest', 'fire_dragon_oil'))]:
            self.assertEqual(*[[e for e in p[key] if e['id'] in identifiers] for p in packs])
        for identifier in ('royal_gate', 'festival_town', 'mansion_garden', 'mansion_corridor', 'mansion_study', 'king_private_room', 'inn_night_ambush'):
            self.assertEqual(*[next(l for l in p['locations'] if l['id'] == identifier) for p in packs])

    def test_upgrade_idempotent_and_exact_descriptions(self):
        doc = (checkpoints.ROOT / 'docs/design/chapter5-v5.md').read_text(encoding='utf-8')
        for s in self.sessions():
            pack = s['scenario_pack']
            before = deepcopy(pack)
            upgrade_ch5.upgrade(pack)
            self.assertEqual(pack, before)
            for loc in pack['locations']:
                if loc['id'] in ('royal_gate', 'festival_town', 'mansion_garden', 'mansion_corridor', 'mansion_study', 'king_private_room', 'inn_night_ambush'):
                    self.assertIn(loc['description'], doc)


if __name__ == '__main__':
    unittest.main()
