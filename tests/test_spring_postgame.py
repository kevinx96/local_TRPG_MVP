from __future__ import annotations

from scripts.scenario.holy_sword_049 import migrate as holy_sword
from scripts.scenario.levels_skills_v2 import migrate as levels
from scripts.scenario.combat_mechanics_v2 import migrate as migrate_combat_mechanics

import json
import unittest
import subprocess
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from host import combat, free_actions, state
from host.difficulty import apply_difficulty, numeric_snapshot
from host.scenario_context import current_action_choices, select_scenario_context
from scripts.balance import checkpoints
from scripts.scenario.spring_postgame import (
    CHAT_TEXTS, CHATS, GUIDANCE, HIDE, PACKS, ROOT, apply, placeholder_rows, recovery_audit, walk_actions,
)


class SpringPostgameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packs = {name: json.loads((ROOT / 'host/prompt/processed' / name).read_text(encoding='utf-8'))
                     for name in PACKS}

    def session(self, pack, location, flag=None):
        session = checkpoints.fresh_session(deepcopy(pack), 'hero')
        record = next(loc for loc in pack['locations'] if loc['id'] == location)
        session['world_state'] = {'scene_id': record['scene_id'], 'location_id': location}
        if flag:
            session['flags'][flag] = True
        return session

    def choices(self, session):
        session['choices'] = state.fallback_choices_for_session(session)
        return list(walk_actions(state.public_session(session)['choices']))

    def test_spring_three_waves_one_rest_and_forward_for_both_modes(self):
        for pack in self.packs.values():
            for mode in ('baby', 'normal'):
                session = self.session(apply_difficulty(pack, mode), 'elf_spring')
                session['character']['hp'] = 1
                self.assertIn('continue_from_elf_spring', {c['id'] for c in self.choices(session)})
                checkpoints.replay_step(session, 'rest_at_elf_spring')
                self.assertEqual(session['character']['hp'], session['character']['max_hp'])
                for source, dest in [('slime_ambush_one', 'slime_ambush_two'),
                                     ('slime_ambush_two', 'slime_king_battle'),
                                     ('slime_king_battle', 'forest_wolves')]:
                    self.assertEqual(state.current_location_id(session), source)
                    checkpoints.replay_step(session, '@victory')
                    self.assertEqual(state.current_location_id(session), dest)
                self.assertTrue(session['flags']['defeated_slime_king'])
                self.assertTrue(any(i['name'] == '鉄壁の霊薬' for i in session['character']['inventory']))
                state.commit_world_position(session, location_id='elf_spring')
                self.assertNotIn('rest_at_elf_spring', {c['id'] for c in self.choices(session)})
                self.assertIsNone(state.resolve_action(session, action_id='rest_at_elf_spring'))

    def test_old_save_and_interrupted_rest_are_not_stuck(self):
        for pack in self.packs.values():
            for flag in ('defeated_slime_king', 'rested_at_elf_spring'):
                session = self.session(pack, 'elf_spring', flag)
                ids = {c['id'] for c in self.choices(session)}
                self.assertNotIn('rest_at_elf_spring', ids)
                self.assertTrue({'continue_from_elf_spring', 'spring_back', 'inspect_spring_wall'} <= ids)
                checkpoints.replay_step(session, 'continue_from_elf_spring')
                self.assertEqual(state.current_location_id(session), 'forest_wolves')

    def test_old_saved_pack_refresh_rebuilds_the_spring_menu(self):
        for name, pack in self.packs.items():
            session = self.session(pack, 'elf_spring', 'defeated_slime_king')
            session['scenario_path'] = str(ROOT / 'host/prompt/processed' / name)
            session['scenario_pack']['meta']['content_revision'] = '2026-10-20-mechanics-051'
            session['choices'] = [{'id': 'rest_at_elf_spring', 'text': '精霊の泉で休む'}]
            saved_path = state.SAVE_DIR / (session['id'] + '.json')
            original_read = Path.read_text
            def read(path, *args, **kwargs):
                return json.dumps(session) if path == saved_path else original_read(path, *args, **kwargs)
            with patch.object(Path, 'exists', return_value=True), patch.object(Path, 'read_text', read), \
                    patch.object(state, 'save_session'):
                loaded = state.load_session(session['id'])
            ids = {c.get('id') for c in state.public_session(loaded)['choices']}
            self.assertNotIn('rest_at_elf_spring', ids)
            self.assertIn('continue_from_elf_spring', ids)

    def test_client_guidance_ordinary_disabled_and_unknown_rendering(self):
        result = subprocess.run(['node', str(Path(__file__).with_name('guidance_choices.test.js'))],
                                capture_output=True, text=True, encoding='utf-8', check=True)
        self.assertIn('4 rendering states passed', result.stdout)

    def test_guidance_only_after_either_flag_and_never_in_model_context(self):
        for pack in self.packs.values():
            for location, identifiers in GUIDANCE.items():
                for flag in (None, 'defeated_ignis', 'ignis_purified'):
                    session = self.session(pack, location, flag)
                    # Exercise evidence-gated branches as well as the normal report.
                    session['flags'].update(heard_treaty_lore=True, noticed_general_frost=True,
                                            saved_gald=True, recruited_robin=True)
                    for surface in (current_action_choices(session), self.choices(session)):
                        for choice in walk_actions(surface):
                            if choice.get('id') in identifiers:
                                self.assertEqual(choice.get('guidance', False), bool(flag), (location, choice))
                    for mode in ('semi', 'full'):
                        session['gm_mode'] = mode
                        self.assertNotIn('"guidance"', json.dumps(select_scenario_context(session)))
                        self.assertNotIn('"guidance"', json.dumps(state.build_llm_messages(session, {}, '契約')))
                        self.assertNotIn('"guidance"', json.dumps(free_actions.build_plan_messages(session, '周囲を見る')))
        session = self.session(next(iter(self.packs.values())), 'castle_report', 'defeated_ignis')
        self.assertTrue(next(c for c in self.choices(session) if c['id'] == 'report_normally')['guidance'])
        for pack in self.packs.values():
            for flag in ('defeated_ignis', 'ignis_purified'):
                for location, action in (('castle_town', 'return_castle_from_town'),
                                         ('village', 'return_castle_from_village')):
                    session = self.session(pack, location, flag)
                    checkpoints.replay_step(session, action)
                    self.assertEqual(state.current_location_id(session), 'festival_town')
                    self.assertTrue(session['flags']['returned_to_capital'])

    def test_obsolete_questions_and_new_chats_both_routes(self):
        for pack in self.packs.values():
            for location, identifiers in HIDE.items():
                session = self.session(pack, location)
                self.assertTrue(set(identifiers) <= {c.get('id') for c in self.choices(session)})
                for flag in ('defeated_ignis', 'ignis_purified'):
                    session['flags'] = {flag: True}
                    self.assertTrue(set(identifiers).isdisjoint(c.get('id') for c in self.choices(session)))
                    for identifier in identifiers:
                        action = state.resolve_action(session, action_id=identifier)
                        self.assertIsNone(action)
            for location in ('village_frozen_clue', 'ian_ice_katana_aftermath'):
                for flag in ('defeated_ignis', 'ignis_purified'):
                    ids = {c.get('id') for c in self.choices(self.session(pack, location, flag))}
                    self.assertNotIn('visit_village', ids)
                    self.assertIn('visit_village_postgame', ids)
            for location, npc, _ in CHATS:
                session = self.session(pack, location)
                session['flags'].update(saved_gald=True, mina_quest_done=True)
                aid = 'postgame_chat_' + npc
                self.assertNotIn(aid, {c.get('id') for c in self.choices(session)})
                button, defeated_text, purified_text = CHAT_TEXTS[(location, npc)]
                for flag, expected_text in (('defeated_ignis', defeated_text), ('ignis_purified', purified_text)):
                    session = self.session(pack, location, flag)
                    session['flags'].update(saved_gald=True, mina_quest_done=True)
                    self.assertIn(aid, {c.get('id') for c in self.choices(session)})
                    action = state.resolve_action(session, action_id=aid)
                    self.assertEqual(action['text'], button)
                    self.assertEqual(action['result_text'], defeated_text)
                    self.assertEqual(action['result_variants'], [
                        {'requirements': {'flag': 'ignis_purified'}, 'text': purified_text},
                    ])
                    self.assertEqual(action['effects'], [])
                    old_flags = set(session['flags'])
                    checkpoints.replay_step(session, aid)
                    self.assertEqual(session['last_action_result']['result_text'], expected_text)
                    self.assertEqual(set(session['flags']) - old_flags, {action['once']})

    def test_postgame_every_location_has_an_action_or_forced_battle(self):
        for pack in self.packs.values():
            for flag in ('defeated_ignis', 'ignis_purified'):
                for location in pack['locations']:
                    session = self.session(pack, location['id'], flag)
                    choices = self.choices(session)
                    if not choices:
                        self.assertTrue(combat.ensure_combat_started(session), location['id'])
                    else:
                        self.assertTrue(any(c.get('enabled', True) for c in choices), location['id'])

    def test_migration_idempotence_sync_freeze_and_placeholder_inventory(self):
        frozen = json.loads((ROOT / 'host/prompt/processed/difficulty/baby_numeric_freeze.json').read_text(encoding='utf-8'))
        rows = []
        for name, pack in self.packs.items():
            actual = deepcopy(pack)
            apply(actual)
            actual = migrate_combat_mechanics(actual)
            actual = holy_sword(levels(actual))
            from scripts.scenario.mina_reborrow_055 import migrate as mina_reborrow
            actual = mina_reborrow(actual)
            self.assertEqual(actual, pack)
            apply(actual)
            actual = migrate_combat_mechanics(actual)
            actual = holy_sword(levels(actual))
            from scripts.scenario.mina_reborrow_055 import migrate as mina_reborrow
            actual = mina_reborrow(actual)
            self.assertEqual(actual, pack)
            self.assertEqual(numeric_snapshot(apply_difficulty(actual, 'baby')), frozen[name])
            legacy = deepcopy(actual)
            legacy['status_defs'] = [s for s in legacy['status_defs'] if s['id'] != 'mana_veil']
            from scripts.scenario.mina_reborrow_055 import ESCORT_NOTICE, REBORROW_SUCCESS_TEXT
            rows.extend(
                (name, path, text)
                for path, text in placeholder_rows(legacy)
                if not (
                    path == '/locations/cave_hot_spring/actions/escort_mina/preview'
                    and ESCORT_NOTICE in text
                )
                and text != REBORROW_SUCCESS_TEXT
            )

        status_ids = {
            'burn', 'poison', 'weaken', 'paralysis', 'stun', 'holy_mark', 'blind', 'haste',
            'holy_afterglow', 'arcane_shield', 'gospel', 'holy_blessing', 'magic_focus', 'suffocation',
        }
        spring_paths = {
            '/locations/elf_spring/description', '/locations/elf_spring/choices/0/preview',
            '/locations/elf_spring/hybrid/summary', '/locations/elf_spring/actions/rest_at_elf_spring/preview',
            '/locations/slime_king_battle/combat/result_texts/victory',
            '/locations/village_frozen_clue/actions/visit_village_postgame/text',
            '/locations/ian_ice_katana_aftermath/actions/visit_village_postgame/text',
            '/maps/forest/nodes/F3/description',
        }
        def is_048_placeholder(path):
            if '/actions/postgame_chat_' in path:
                return path.endswith(('/text', '/result_text'))
            if path.startswith('/status_defs/') and path.endswith('/description'):
                return path.split('/')[2] in status_ids
            return path in spring_paths

        self.assertFalse([(name, path) for name, path, _ in rows if is_048_placeholder(path)])
        paths_049 = {
            '/locations/castle_report/actions/report_with_evidence/result_variants/holy_sword_diary/text',
            '/locations/castle_report/actions/report_with_evidence/result_variants/holy_sword_neutral/text',
            '/locations/draco_battle/combat/encounter_modifiers/hero_holy_sword/lethal_awakening/lock_text',
            '/locations/draco_battle/combat/encounter_modifiers/hero_holy_sword/lethal_awakening/text',
            '/locations/draco_battle/combat/encounter_modifiers/draco_holy_sword/text',
            '/locations/draco_battle/combat/encounter_modifiers/draco_holy_sword/extra_enemy_skills/stolen_holy_blade/name',
            '/items/hero_holy_sword/description', '/items/hero_holy_sword/effect',
            '/items/hero_holy_sword/awakening_origin/description_suffix',
        }
        for pack_name in self.packs:
            self.assertEqual({path for name, path, _ in rows if name == pack_name and path in paths_049}, set())
        placeholders_050 = [(name, path, text) for name, path, text in rows
                            if not is_048_placeholder(path) and path not in paths_049]
        self.assertEqual(len(placeholders_050), 0)
        self.assertTrue(all(sum(name == pack_name for name, _, _ in placeholders_050) == 0 for pack_name in self.packs))
        self.assertTrue(all(path.startswith('/class_progression/') or path.startswith('/items/spellbook_')
                            for _, path, _ in placeholders_050))
        self.assertTrue(all(text == '\u3010\u4eee\u3011' for _, _, text in placeholders_050))
        report = (ROOT / 'eval/reports/048-engineering.md').read_text(encoding='utf-8')
        self.assertEqual(sum(line.startswith('| P') for line in report.splitlines()), 96)
        first, second = self.packs.values()
        for a, b in zip(first['locations'], second['locations']):
            self.assertEqual(a['id'], b['id'])
            self.assertEqual(a.get('actions'), b.get('actions'), a['id'])
            self.assertEqual(a.get('combat'), b.get('combat'), a['id'])

    def test_audit_lists_repeated_recovery_and_detects_respawn_loop(self):
        for pack in self.packs.values():
            rows = recovery_audit(pack)
            self.assertFalse(any(r['action'] == 'rest_at_elf_spring' for r in rows))
            self.assertFalse(any(r['free_repeatable_battle_loop'] for r in rows))
            self.assertTrue(any(r['action'] == 'ask_king_rest' and not r['gold_cost'] for r in rows))
        fixture = dict(locations=[
            dict(id='spring', actions=[dict(id='rest', effects=[dict(restore_full=True)]),
                                      dict(id='fight', effects=[dict(current_location='battle')])]),
            dict(id='battle', actions=[dict(id='return', effects=[dict(current_location='spring'),
                      dict(unset_flag='combat_defeated:battle:slime')])], combat=dict(enemy_ids=['slime'])),
        ])
        self.assertTrue(recovery_audit(fixture)[0]['free_repeatable_battle_loop'])
        fixture['locations'][0]['actions'][0]['once'] = 'rested'
        self.assertEqual(recovery_audit(fixture), [])


if __name__ == '__main__':
    unittest.main()
