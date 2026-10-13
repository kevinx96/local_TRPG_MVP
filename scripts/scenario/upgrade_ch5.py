from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .upgrade_forest import ROOT, action, move, observe, upsert
from .upgrade_ch34 import branch


def upgrade(pack: dict[str, Any]) -> None:
    from .tune_ch5 import tune

    if pack['meta'].get('chapter5_v5'):
        tune(pack)
        return
    pack['meta'].update(chapter5_v5=True, content_revision='2026-10-12-v023-ch5')
    loc = {entry['id']: entry for entry in pack['locations']}
    report = loc['castle_report']['actions'][0]
    clues = report['requirements']['any'][1]['flags_count_gte']['flags']
    for flag in ('heard_xanxus_betrayal', 'has_assassin_crest'):
        if flag not in clues:
            clues.append(flag)
    evidence = {'any': [{'has_item': '白い竜鱗'}, {'has_item': '白竜の日誌'}]}
    report['requirements']['any'].append({'has_item': '白竜の日誌'})
    original = next(t['draft']['gm_text'] for t in loc['castle_report']['hybrid']['prepared_turns'] if t['action_id'] == 'report_with_evidence')
    report['result_variants'] = [dict(requirements={'has_item': '白竜の日誌'}, text=original + 'あなたが日誌を掲げると、ドラコの表情から初めて笑みが消えた。')]
    suspicion = {'any': [{'flag': f} for f in ('heard_gald_rumor', 'noticed_general_frost', 'heard_xanxus_betrayal')] + [{'has_item': '白い竜鱗'}]}
    audience = {'any': [{'flag': f} for f in clues] + evidence['any']}

    def location(identifier: str, title: str, description: str, image: str, **extra: Any) -> dict[str, Any]:
        result = dict(id=identifier, title=title, description=description, scene_id='castle_return', actions=[],
                      npc_ids=[], enemy_ids=[], connected_location_ids=[], background_image=f'/static/images/{image}.png', **extra)
        result.update(entry_text=description, narrate_entry=True)
        result.setdefault('entry_effects', [{'set_flag': f'entered_{identifier}'}])
        upsert(pack['locations'], result)
        loc[identifier] = result
        return result

    gate = location('royal_gate', '凱旋の城門', '城門をくぐると、花びらと歓声があなたを迎えた。邪竜の脅威が去ったことは、すでに城下町じゅうに知れ渡っている。人混みの向こうで、将軍ドラコが穏やかに手を振っていた。', 'bg_royal_gate', entry_effects=[{'set_flag': 'returned_to_capital'}])
    gate['actions'] = [move('enter_festival_town', '城下町へ進む', 'festival_town')]
    town = location('festival_town', '凱旋の城下町', '城下町は祝祭の飾りで埋め尽くされている。祝杯をあげる人々の間を、王国の近衛兵たちが慌ただしく行き来していた。', 'bg_festival_town')
    town['entry_events'] = [dict(requirements={'flag': f}, once=f'ch5_thanks_{f}', text=t) for f, t in [
        ('mina_quest_done', 'ミーナが駆け寄ってきた。「無事でよかった！ 師匠と一緒に、とっておきの術を用意してあるんです」'),
        ('riku_returned', '人混みの中から、リクが手を振っている。避難していた村の人たちも、王都まで凱旋を見に来たらしい。'),
        ('saved_gald', '「よう、英雄！」ガルドが荷車の上から叫んだ。「とっておきの品を仕入れてきたぜ。道具屋の隣で店を広げてる」'),
        ('robert_hammer_returned', '鍛冶屋の前で、ローベルトが無言で手招きしている。')]]
    town['actions'] = [move(f'go_{i}', text, i) for i, text in [('inn', '宿屋へ向かう'), ('item_shop', '道具屋へ向かう'), ('magic_shop', '魔法店へ向かう'), ('forge', '鍛冶屋へ向かう')]] + [
        move('go_general_mansion', '将軍の屋敷へ向かう', 'mansion_garden', requirements=suspicion, secret=True, unlock_flag='mansion_unlocked'),
        move('request_king_audience', '国王に内密の謁見を願い出る', 'king_private_room', requirements=audience, secret=True),
        move('go_report_hall', '凱旋の間へ向かう', 'castle_report')]
    garden = location('mansion_garden', '将軍の屋敷・夜の庭', '夜更けの将軍の屋敷は、祝祭の喧騒が嘘のように静まり返っている。庭の噴水だけが、なぜか凍りついていた。', 'bg_mansion_garden')
    garden['actions'] = [action('sneak_into_mansion', '裏口から忍び込む', roll=dict(dice_type='1d20+dex', dc=13),
        success_effects=[{'unset_flag': 'mansion_alert'}, {'current_location': 'mansion_corridor'}],
        failure_effects=[{'set_flag': 'mansion_alert'}, {'current_location': 'mansion_corridor'}],
        result_texts=dict(success='物音ひとつ立てず、裏口の錠を外した。', failure='扉が軋み、屋敷の奥で何かが動く気配がした。')),
        action('robin_picks_lock', 'ロビンに錠を開けてもらう', [{'unset_flag': 'mansion_alert'}, {'current_location': 'mansion_corridor'}], requirements={'flag': 'recruited_robin'}, result_text='ロビンが細い針金を差し込むと、錠はあっさりと外れた。「将軍様の屋敷ってのは、案外ちょろいもんだね」'),
        move('leave_mansion', '城下町へ戻る', 'festival_town')]
    garden['actions'][0]['risk'] = '1d20判定（DC13）'
    garden['objects'] = [observe('frozen_fountain', '凍った噴水', '真夏の夜だというのに、噴水の水は芯まで凍りついている。', [{'set_flag': 'noticed_general_frost'}], once='observed_frozen_fountain')]
    corridor = location('mansion_corridor', '将軍の屋敷・凍てつく回廊', '廊下の壁も床も、薄い氷に覆われている。突き当たりの扉の前に、氷でできた鎧の番兵が二体、無言で立っていた。', 'bg_mansion_corridor')
    corridor['actions'] = [action('fight_ice_sentinels', '戦う', [{'start_combat': True}]),
        action('evade_ice_sentinels', '番兵の巡回の隙を突く', roll=dict(dice_type='1d20+wis', dc=15),
               success_effects=[{'current_location': 'mansion_study'}], failure_effects=[{'start_combat': True}, {'enemy_first': True}])]
    corridor['actions'][1]['risk'] = '1d20判定（DC15）'
    corridor['enemy_ids'] = ['ice_sentinel', 'ice_sentinel']
    corridor['combat'] = dict(auto_start=False, enemy_ids=corridor['enemy_ids'], flee_allowed=False, encounter_class='elite',
        enemy_first_requirements={'flag': 'mansion_alert'}, victory_effects={'current_location': 'mansion_study'},
        defeat_effects=dict(hp=1, current_location='festival_town'), result_texts=dict(defeat='氷の拳に打ち据えられ、気がつくと城下町の路地裏に倒れていた。'))
    # Cleared optional guards remain passable on subsequent visits.
    corridor['actions'].append(move('pass_cleared_sentinels', '先へ進む', 'mansion_study', visible_after='combat_defeated:mansion_corridor:ice_sentinel'))
    study = location('mansion_study', '将軍の屋敷・書斎', '書斎には古い書物が積み上げられ、机の上に一冊の日誌が開かれたまま置かれていた。部屋の奥には、白い鱗で飾られた小箱がある。', 'bg_mansion_study')
    study['actions'] = [action('take_draco_journal', '日誌を手に取る', [{'add_item': {'id': 'draco_journal', 'name': '白竜の日誌'}}], once='draco_journal', result_text='日誌には、十年前に紅竜の傷へ霜を打ち込んだこと、Xanxusと交わした密約、そして王国を手に入れる計画が、几帳面な文字で記されていた。'),
        action('open_scale_box', '小箱を開ける', [{'add_item': {'id': 'frost_seal_charm', 'name': '霜封じの護符'}}], once='opened_scale_box', result_text='小箱の中には、白い鱗を編み込んだ護符が収められていた。添えられた札には「我が冷気を鎮めるもの」とある。'),
        move('leave_mansion_study', '屋敷を出る', 'festival_town')]
    king = location('king_private_room', '王の私室', '豪奢な寝室の窓辺で、国王エドワードが一人、月を見上げていた。あなたに気づくと、王は静かに人払いをした。', 'bg_king_room')
    king['npc_ids'] = ['king']
    king['actions'] = [action('confide_in_king', '将軍への疑いを打ち明ける', once='king_trust', result_text='王は長い沈黙の後、重い口を開いた。「……十年前、竜の谷へ兵を送れと進言したのは、ドラコだった。わしはそれを信じ、紅竜を怒らせてしまった。もしそなたの言う通りなら……その時は、わしが近衛兵に命じよう。そなたを守れ、と」'),
        action('ask_king_rest', '城に泊めていただけないか頼む', [{'restore_full': True}], requirements={'flag': 'king_trust'}, result_text='王の計らいで、城の客室に通された。衛兵が扉の前に立ち、あなたは久しぶりに安心して眠った。'),
        move('leave_king_room', '城下町へ戻る', 'festival_town')]
    for identifier in ('ignis_last_breath', 'ignis_purified'):
        next(a for a in loc[identifier]['actions'] if a['id'] == 'return_to_castle_report')['effects'] = [{'current_location': 'royal_gate'}]
        loc[identifier]['connected_location_ids'] = ['royal_gate']
    for identifier in ('inn', 'item_shop', 'magic_shop', 'forge'):
        for a in loc[identifier]['actions']:
            if a['id'] == f'return_castle_from_{identifier}':
                a['effects'] = [branch({'flag': 'returned_to_capital'}, [{'current_location': 'festival_town'}], a['effects'])]
            elif a['id'] in ('return_forest_exit', 'accept_robin_goblin_quest'):
                a['requirements'] = {'all': [a.get('requirements', {}), {'not_flag': 'returned_to_capital'}]}
                a['secret'] = True

    ambush = location('inn_night_ambush', '宿屋・深夜の襲撃', '真夜中、部屋の窓が音もなく凍りつき、砕け散った。白い装束の刺客が二人、氷の刃を手に滑り込んでくる。', 'bg_inn_night')
    ambush['enemy_ids'] = ['ice_assassin', 'ice_assassin']
    ambush['combat'] = dict(auto_start=True, enemy_ids=ambush['enemy_ids'], encounter_class='elite', flee_allowed=False,
        enemy_first_requirements={'not_flag': 'recruited_robin'}, player_first_requirements={'flag': 'recruited_robin'},
        start_events=[dict(requirements={'flag': 'recruited_robin'}, text='「起きな！ 窓の外に誰かいる！」ロビンの声で飛び起きると、すでに刺客が窓に手をかけていた。')],
        victory_effects=dict(inventory_add=[dict(id='assassin_crest', name='刺客の徽章', quantity=1)], flags_set=['assassins_defeated'], restore_full=True, current_location='inn'),
        defeat_effects=dict(hp=1, inventory_remove=[dict(name='白い竜鱗', quantity=99)], flags_set=['scale_stolen'], current_location='inn'),
        result_texts=dict(victory='倒れた刺客の懐から、白い竜を象った徽章がこぼれ落ちた。将軍家の紋章だ。', defeat='気がつくと朝だった。部屋は荒らされ、白い鱗だけが消えていた。'))
    rest = next(a for a in loc['inn']['actions'] if a['id'] == 'rest_at_inn')
    trigger = {'all': [{'flag': 'returned_to_capital'}, evidence, {'not_flag': 'draco_revealed'}, {'not_flag': 'assassins_attacked'}]}
    rest['effects'] = [{'gold_change': -10}, branch(trigger, [{'set_flag': 'assassins_attacked'}, {'current_location': 'inn_night_ambush'}], [{'restore_full': True}])]
    rest['result_variants'] = [dict(requirements=trigger, text='')]

    for identifier, name, desc, effect in [
        ('draco_journal', '白竜の日誌', '将軍ドラコの日誌。紅竜への呪いとXanxusとの密約が記されている。', '証拠品'),
        ('frost_seal_charm', '霜封じの護符', '白い鱗を編み込んだ護符。白竜の冷気を鎮めるという。', '凍てつく吐息のダメージを軽減'),
        ('assassin_crest', '刺客の徽章', '白い竜を象った徽章。将軍家の紋章だ。', '証拠品'),
        ('fire_dragon_oil', '火竜の油', '竜の谷の火山で採れる油。白い竜に効くという。', '火属性の大ダメージ（消耗品）')]:
        item = dict(id=identifier, name=name, description=desc, effect=effect, category='key', key_item=True)
        if identifier == 'fire_dragon_oil':
            item.update(category='consumable', key_item=False, combat=dict(kind='damage', damage='4d6', accuracy=95, element='fire', consumable=True))
        upsert(pack['items'], item)
    pack['item_flags'] = {**pack.get('item_flags', {}), 'assassin_crest': 'has_assassin_crest', 'draco_journal': dict(flag='draco_journal', persistent=True)}
    gald = deepcopy(next(s for s in pack['shops'] if s['id'] == 'gald_shop'))
    gald.update(id='gald_capital_shop', location_id='festival_town', greeting='とっておきだ。白い竜には火が一番効くって話だぜ', items=[dict(item_id='fire_dragon_oil', price=40, stock=2)])
    upsert(pack['shops'], gald)
    town['npc_ids'] = ['gald']
    town['npc_requirements'] = {'gald': {'flag': 'saved_gald'}}
    town['actions'].append(action('open_gald_capital_shop', gald['title'], requirements={'flag': 'saved_gald'}, secret=True, open_shop='gald_capital_shop'))
    upsert(pack['quests'], dict(id='side_general_mansion', title='将軍の屋敷', description='屋敷を調べる', kind='side', start_flag='mansion_unlocked', complete_flags=['draco_journal'], fail_flags=[], stages=[dict(text='屋敷を調べる', done_flag='draco_journal')]))
    mystery = next(q for q in pack['quests'] if q['id'] == 'mystery_frost')
    mystery.update(clue_flags=list(clues), clue_items=['white_dragon_scale', 'draco_journal'], start_flag=list(clues), start_items=['white_dragon_scale', 'draco_journal'])
    mystery.pop('clue_item', None)

    for identifier, name, description, hp, evade, resistances, skills in [
        ('ice_sentinel', '氷の番兵', '将軍の冷気から作られた、氷の鎧の番兵。', 26, 0, {'physical': .6, 'fire': 1.5}, [
            dict(id='ice_hammer', name='氷槌', kind='attack', damage='1d10+3', accuracy=70, element='physical', ai_weight=3),
            dict(id='frozen_stance', name='凍結の構え', kind='defend', guard_multiplier=.6, duration=2, ai_weight=1)]),
        ('ice_assassin', '氷の刺客', '将軍に仕える白装束の刺客。氷の刃を操る。', 22, 15, {'fire': 1.5}, [
            dict(id='ice_blade_combo', name='氷刃の連撃', kind='attack', damage='1d4+2', accuracy=80, element='ice', hits=2, ai_weight=3),
            dict(id='frozen_poison', name='凍てつく毒', kind='attack', damage='1d4', accuracy=80, element='ice', ai_weight=1, on_hit_status=dict(id='frozen_poison', name='凍てつく毒', damage='2', remaining_rounds=2))])]:
        upsert(pack['enemies'], dict(id=identifier, name=name, description=description, hp=hp, max_hp=hp, element='ice', attributes=dict(str=12, dex=6 if identifier == 'ice_sentinel' else 16, int=10, end=12),
            combat=dict(defense=1, evade=evade, basic_attack=dict(name=skills[0]['name'], damage='1d6+2', accuracy=75, element='physical' if identifier == 'ice_sentinel' else 'ice')),
            resistances=resistances, skills=skills, rewards=dict(gold=0, items=[], flags=[]), image=f'/static/images/enemy_{identifier}.png'))
    loc['draco_battle']['combat']['encounter_modifiers'] = [
        dict(id='king', enemy_ids=['draco_human'], requirements={'flag': 'king_trust'}, enemy_defense=-2, text='「近衛兵、将軍を囲め！」国王の号令が王の間に響いた。'),
        dict(id='robin', enemy_ids=['draco_human'], requirements={'all': [{'flag': 'recruited_robin'}, {'flag': 'cleared_goblin_fort'}]}, text='「昨夜のうちに、あんたの部屋から妙な首飾りをくすねといたよ。白い竜の力の源なんだろ？」柱の陰からロビンの声がした。'),
        dict(id='mina', enemy_ids=['draco_dragon'], requirements={'flag': 'mina_quest_done'}, received_element='ice', received_multiplier=.8, text='「今です、師匠！」ミーナと青いローブの魔法使いが、あなたの周りに炎の結界を張った。'),
        dict(id='robert', enemy_ids=['draco_dragon'], requirements={'flag': 'robert_hammer_returned'}, basic_followup=dict(name='霜断ちの刻印', damage='1d6', accuracy=100, element='fire'), text='剣の刻印が赤く輝いた。ローベルトが打ち込んだ霜断ちの刻印だ。'),
        dict(id='charm', enemy_ids=['draco_dragon'], requirements={'has_item': '霜封じの護符'}, enemy_skill='凍てつく吐息', damage_multiplier=.7, text='胸の護符が白く光り、吹きつける冷気を和らげた。')]
    # Existing Ignis assistance also belongs exclusively to this encounter.
    dragon = next(e for e in pack['enemies'] if e['id'] == 'draco_dragon')
    allies = dragon.pop('phase_allies', [])
    for ally in allies:
        ally['enemy_ids'] = ['draco_dragon']
    loc['draco_battle']['combat']['phase_allies'] = allies
    scene = next(s for s in pack['scenes'] if s['id'] == 'castle_return')
    scene['location_ids'] += [i for i in loc if loc[i]['scene_id'] == 'castle_return' and i not in scene['location_ids']]
    pack['chapter_locks'] = [dict(flag='returned_to_capital', location_ids=scene['location_ids'] + ['inn', 'item_shop', 'magic_shop', 'forge'])]

    def map_record(identifier: str, title: str, rows: list, edges: list, **extra: Any) -> dict[str, Any]:
        return dict(id=identifier, title=title, nodes=[dict(id=i, label=label, kind=kind, x=x, y=y, location_ids=ids, description=loc[ids[0]]['description'], **more) for i, label, kind, x, y, ids, more in rows],
                    edges=[{'from': a, 'to': b, 'action_id': c} for a, b, c in edges], **extra)
    upsert(pack['maps'], map_record('royal_return', '王城への帰還', [
        ('R1', '凱旋の城門', 'start', 10, 50, ['royal_gate'], {}), ('R2', '凱旋の城下町', 'event', 35, 50, ['festival_town'], {}),
        ('R3', '将軍の屋敷', 'branch', 60, 20, ['mansion_garden'], {'submap': 'general_mansion'}),
        ('R4', '王の私室', 'rest', 60, 50, ['king_private_room'], {}), ('R5', '凱旋の間', 'boss', 85, 20, ['castle_report', 'draco_battle'], {}),
        ('inn', '宿屋', 'rest', 20, 85, ['inn', 'inn_night_ambush'], {}), ('item_shop', '道具屋', 'event', 40, 85, ['item_shop'], {}),
        ('magic_shop', '魔法店', 'event', 60, 85, ['magic_shop'], {}), ('forge', '鍛冶屋', 'event', 80, 85, ['forge'], {})],
        [('R1', 'R2', 'enter_festival_town'), ('R2', 'R3', 'go_general_mansion'), ('R2', 'R4', 'request_king_audience'), ('R2', 'R5', 'go_report_hall'), ('R3', 'R2', 'leave_mansion'), ('R4', 'R2', 'leave_king_room')] +
        [(a, b, c) for i in ('inn', 'item_shop', 'magic_shop', 'forge') for a, b, c in [('R2', i, f'go_{i}'), (i, 'R2', f'return_castle_from_{i}')]], requirements={'flag': 'returned_to_capital'}))
    upsert(pack['maps'], map_record('general_mansion', '将軍の屋敷', [
        ('R3a', '夜の庭', 'start', 15, 50, ['mansion_garden'], {}), ('R3b', '凍てつく回廊', 'battle', 50, 50, ['mansion_corridor'], {}), ('R3c', '将軍の書斎', 'event', 85, 50, ['mansion_study'], {})],
        [('R3a', 'R3b', 'sneak_into_mansion'), ('R3b', 'R3c', 'evade_ice_sentinels')], parent='royal_return'))
    tune(pack)


if __name__ == '__main__':
    for name in ('dragon_rpg.json', 'dragon_rpg_hybrid.json'):
        path = ROOT / 'host/prompt/processed' / name
        pack = json.loads(path.read_text(encoding='utf-8'))
        upgrade(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
