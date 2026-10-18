"""E: new social, investigation and scouting checks (docs/design/checks-e-scenario.md). Idempotent; both packs."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACKS = ("dragon_rpg.json", "dragon_rpg_hybrid.json")

# flag -> (reason, action ids that gain advantage); entries marked "dis" give disadvantage instead.
LINKS = {
    "scouted_fort_patrol": ("見張りの交代を知っている", ["fort_first_bypass", "fort_second_bypass", "bypass_hobgoblin"], "advantage"),
    "fort_alerted": ("見張りが警戒している", ["fort_first_bypass"], "disadvantage"),
    "heat_rhythm_known": ("熱風の切れ目を知っている", ["sneak_heat"], "advantage"),
    "calmed_crystals": ("水晶の共鳴を知っている", ["sneak_crystal"], "advantage"),
    "fire_upwind_known": ("風上を知っている", ["approach_burning_village_carefully"], "advantage"),
    "child_at_window": ("子どもが窓辺にいる", ["climb_to_window", "break_burning_beam"], "advantage"),
    "read_battlefield_mist": ("霧の流れを知っている", ["sneak_bone_field", "sneak_ghoul_marsh"], "advantage"),
    "marsh_path_known": ("沈まない足場を知っている", ["sneak_ghoul_marsh"], "advantage"),
    "gorge_tremor_rhythm": ("地鳴りの間隔を知っている",
                            ["sneak_gorge_rockfall_path", "sneak_gorge_giant_path", "sneak_gorge_worm_lair"], "advantage"),
    "knows_ash_wind": ("煤の流れを知っている", ["sneak_through_ash"], "advantage"),
    "mansion_patrol_known": ("夜番の交代を知っている", ["sneak_into_mansion", "evade_ice_sentinels"], "advantage"),
    "mansion_alerted": ("番犬に気づかれている", ["sneak_into_mansion"], "disadvantage"),
}


def item(identifier: str, name: str, quantity: int = 1) -> dict[str, Any]:
    return {"add_item": {"id": identifier, "name": name, "quantity": quantity}}


def flag(name: str) -> dict[str, Any]:
    return {"set_flag": name}


def gold(amount: int) -> dict[str, Any]:
    return {"gold_change": amount}


def hp(amount: int) -> dict[str, Any]:
    return {"hp_change": amount}


# (id, location, text, skill, band, success_text, success_effects, failure_text, failure_effects, npc_id, extra)
CHECKS = [
    ("ask_king_ten_years", "castle", "十年前のことを王に尋ねる", "洞察", "中",
     "王は言葉を選ぶように目を伏せた。「……あの遠征は、わしの過ちだった。竜の谷へ兵を送れと、強く勧めた者がいたのだ」 王の視線が、一瞬だけ将軍へ向いた。",
     [flag("heard_human_caused_dragon_return")], "「昔の話はよい。今は竜のことだけを考えてくれ」 王はそれ以上語らなかった。", [], "king", {}),
    ("ask_gald_extra", "castle_town", "ガルドにおまけを頼み込む", "説得", "中",
     "「参ったね、あんたには敵わない」 ガルドは笑って、薬草を一束放ってよこした。", [item("herb", "薬草")],
     "「悪いが、これ以上は負けられないね」", [], "gald", {}),
    ("dig_forge_scrap", "forge", "鉄くずの山を漁る", "調査", "中",
     "鉄くずの底から、まだ使えそうな毒矢が一本出てきた。ローベルトは「持っていけ」とだけ言った。", [item("poison_dart", "毒矢")],
     "錆びた鉄片で指を切った。", [hp(-1)], "blacksmith", {}),
    ("listen_inn_gossip", "inn", "酔客の話に耳を傾ける", "知覚", "中",
     "「砦のゴブリンども、見張りの交代は鐘一つごとだってよ。交代の時は、門の前ががら空きになるんだと」", [flag("scouted_fort_patrol")],
     "酔客の話は、昨日の喧嘩の自慢ばかりだった。", [], None, {}),
    ("robin_archery", "inn", "ロビンに弓の手ほどきを頼む", "軽業", "中",
     "「筋は悪くないね」 ロビンは笑って、矢筒から毒矢を二本抜いて渡してくれた。", [item("poison_dart", "毒矢", 2)],
     "弦が跳ねて頬を打った。ロビンが肩を震わせて笑っている。", [hp(-1)], "robin", {}),
    ("help_sarah_shelves", "item_shop", "サラの棚卸しを手伝う", "運動", "易",
     "重い木箱を棚の上まで運び終えると、サラが小さな袋を差し出した。「ありがとう！ これ、お駄賃！」", [gold(10)],
     "木箱を取り落としてしまった。サラは「大丈夫、割れ物じゃないから」と笑ってくれた。", [], "sarah", {}),
    ("read_magic_tomes", "magic_shop", "棚の魔導書を読み解く", "魔法学", "中",
     "魔導書の余白に書き込まれた術式を、白紙の巻物に写し取った。ワーロックが片眉を上げる。「……ほう。持っていくといい」",
     [item("magic_scroll", "魔法の巻物")], "文字が頭の中でほどけて、軽い眩暈がした。", [], "blue_robed_mage", {}),
    ("search_alley_day", "alley", "路地裏の物陰を探る", "知覚", "中",
     "積まれた樽の陰に、銀貨が数枚落ちていた。", [gold(15)],
     "物陰から飛び出したネズミに驚いて、尻もちをついた。", [], None, {}),
    ("see_through_merchant", "alley_night", "商人の正体を見極める", "洞察", "難",
     "フードの奥で、獣のような目が一瞬だけ光った。この取引には、必ず裏がある。差し出された品から、かすかに死者の匂いがする。", [],
     "商人の顔はフードの影に沈んで、何も読み取れなかった。", [], "suspicious_merchant", {}),
    ("read_forest_tracks", "dark_forest_loc", "獣道の足跡を読む", "知覚", "易",
     "大きな足跡が泉の方へ続いている。森の奥には狼の群れがいるらしい。足跡のそばで、薬草を一株見つけた。", [item("herb", "薬草")],
     "落ち葉に埋もれて、足跡はよく見えなかった。", [], None, {}),
    ("question_lost_goblin", "lost_goblin_crossroads", "ゴブリンの話の真偽を確かめる", "洞察", "中",
     "ゴブリンの目は嘘をついていない。箱は本当にこいつの一族のものだ。「砦の見張りはな、夜明け前がいちばん眠そうなんだ」",
     [flag("scouted_fort_patrol")], "ゴブリンはおびえて口ごもり、それ以上は何も言わなかった。", [], "lost_goblin", {}),
    ("commune_spring", "elf_spring", "泉の精霊の声に耳を澄ます", "信仰", "中",
     "水面がかすかに揺れ、冷たい風が頬をなでた。体の芯から疲れが抜けていく。", [hp(5)],
     "泉は静かなままだった。", [], None, {}),
    ("survey_from_hill", "forest_exit", "高台から周囲を見渡す", "知覚", "中",
     "南の街道は白い霧に沈み、東の空は赤く燃えている。霧は谷から吹き下ろす風に沿って流れているようだ。", [flag("read_battlefield_mist")],
     "木々に遮られて、遠くまでは見えなかった。", [], None, {}),
    ("scout_fort_walls", "goblin_fort", "砦の外壁を偵察する", "隠密", "中",
     "外壁に張りついて覗くと、見張りが交代する短い隙が見えた。", [flag("scouted_fort_patrol")],
     "小石を蹴ってしまい、見張りがこちらの茂みを睨んだ。", [flag("fort_alerted")], None, {}),
    ("listen_fort_corridors", "goblin_fort_second_choice", "通路の奥に耳を澄ます", "知覚", "中",
     "右の通路からは重い足音が一つ。左からは水の滴る音と、かすかな呻き声が聞こえる。", [],
     "砦の喧騒に紛れて、何も聞き分けられなかった。", [], None, {}),
    ("study_healing_circle", "goblin_fort_healing_circle", "法陣の紋様を読み解く", "魔法学", "中",
     "紋様の流れをなぞると、法陣の光が一段強まった。息が軽くなる。", [{"sp_change": 3}],
     "紋様は古すぎて、意味が読み取れなかった。", [], None, {}),
    ("appraise_goblin_box", "goblin_fort_chest_choice", "箱の作りを確かめる", "調査", "中",
     "箱の底を叩くと、乾いた音がした。二重底の隠しに、金貨が数枚挟まっている。", [gold(20)],
     "ただの古い木箱にしか見えなかった。", [], None, {}),
    ("read_heat_flow", "cave_heat_corridor", "熱風の流れを読む", "知覚", "中",
     "熱風は一定の間隔で弱まる。その切れ目なら、岩陰を伝って抜けられそうだ。", [flag("heat_rhythm_known")],
     "熱気にあてられて、頭がくらくらした。", [hp(-2)], None, {}),
    ("listen_cave_fork", "cave_fork", "分かれ道の奥を探る", "知覚", "易",
     "左の通路からは熱気。右からは湯気と、少女のすすり泣くような声がする。", [],
     "水音が反響して、どちらからの音か分からなかった。", [], None, {}),
    ("search_lava_room", "cave_lava_room", "溶岩の縁を探る", "軽業", "難",
     "溶岩の縁に身を乗り出し、冷えかけた赤い欠片をすくい上げた。", [item("ember_shard", "残り火の欠片")],
     "熱で指先を焼いた。", [hp(-3)], None, {}),
    ("calm_mina", "cave_hot_spring", "ミーナを落ち着かせる", "説得", "易",
     "ミーナは深呼吸して、ぽつりぽつりと話し始めた。「あの水晶の木、近づくと共鳴するの。でも、じっとしてれば襲ってこない」",
     [flag("calmed_crystals")], "ミーナは膝に顔を埋めたまま、泣き止まなかった。", [], "mina", {}),
    ("tune_crystals", "cave_crystal_corridor", "水晶の音色を聴き分ける", "魔法学", "中",
     "共鳴には周期がある。音が途切れる瞬間を数えられるようになった。", [flag("calmed_crystals")],
     "甲高い音に、頭が割れそうになった。", [hp(-2)], None, {}),
    ("read_fire_spread", "village_approach", "炎の広がり方を見極める", "調査", "中",
     "炎は風下へ流れている。風上から回り込めば、焼けずに村へ入れそうだ。", [flag("fire_upwind_known")],
     "煙を吸い込んで、激しくむせた。", [hp(-2)], None, {}),
    ("call_to_child", "burning_house", "中の子どもに声をかける", "説得", "中",
     "「窓のところまで来られるか！」 泣き声がやみ、二階の窓辺へ這ってくる小さな影が見えた。", [flag("child_at_window")],
     "炎の音にかき消されて、声は届かなかった。", [], None, {}),
    ("tend_refugees", "village", "負傷者の手当てを手伝う", "信仰", "中",
     "祈りながら包帯を巻くうちに、傷の浅い者から立ち上がり始めた。村の女が、礼にと聖水を差し出す。", [item("holy_water", "聖水")],
     "慣れない手当てに手間取ってしまった。村人は黙って頭を下げた。", [], None, {}),
    ("ask_elder_legend", "village", "長老に昔話をせがむ", "洞察", "中",
     "「氷の太刀を打ったのは、この村の鍛冶屋じゃった。……今は王都で宿をやっとると聞く」", [],
     "長老は咳き込み、話を途中でやめてしまった。", [], "elder", {}),
    ("read_ian_grief", "ian_ice_katana_aftermath", "イアンの様子をうかがう", "洞察", "中",
     "「……あの太刀は、俺の最後の仕事だった。砕いたのは氷の精霊じゃない。誰かが、芯に霜を仕込んでいたんだ」", [flag("frost_trace_seen")],
     "イアンは砕けた刃を見つめたまま、何も言わなかった。", [], "ian", {}),
    ("read_mist_flow", "old_battlefield", "霧の流れを読む", "知覚", "中",
     "霧は谷からの風に沿って、骨の野から沼へ流れている。霧の濃い側を選べば、気づかれずに進めそうだ。", [flag("read_battlefield_mist")],
     "霧の中で、一瞬方角を見失いかけた。", [], None, {}),
    ("identify_old_banner", "bone_field", "折れた軍旗を調べる", "調査", "中",
     "色あせた紋章は、王国軍の第三軍団のものだ。十年前、竜の谷へ送られた部隊。旗の根元に、錆びた徽章が一つ落ちていた。",
     [item("rusted_badge", "錆びた兵士の徽章")], "泥にまみれて、紋章は読み取れなかった。", [], None, {}),
    ("pray_for_ghost", "ruined_watchtower", "亡霊のために祈る", "信仰", "中",
     "亡霊の表情が、少しだけ和らいだ。「……ありがとう。沼を渡るなら、縁の苔を踏め。あそこだけは沈まない」", [flag("marsh_path_known")],
     "祈りの言葉は、冷たい風に吹き散らされた。", [], "old_soldier_ghost", {}),
    ("probe_marsh_depth", "ghoul_marsh", "枝で沼の深さを探る", "調査", "中",
     "枝を差し込んでいくと、縁の苔の下にだけ硬い地面があった。", [flag("marsh_path_known")],
     "足を取られ、膝まで泥に沈んだ。", [hp(-2)], None, {}),
    ("read_knight_epitaph", "grave_chapel", "騎士の墓碑を読む", "調査", "中",
     "苔をぬぐうと、古い文字が現れた。「我が剣、竜と人の盟約を守る者にのみ譲らん」", [],
     "文字はすり減って、ほとんど読めなかった。", [], None, {}),
    ("chat_guardsmen", "oaksdawn_square", "守護団員と雑談する", "説得", "中",
     "「峠の岩か？ 団長に頼めば、すぐどけてくれるさ」 若い団員は、干し肉を一切れ分けてくれた。", [item("trail_ration", "携帯食")],
     "「悪いが、今は見回り中だ」と追い払われた。", [], None, {}),
    ("study_war_map", "oaksdawn_hq", "卓上の地図を読み解く", "調査", "中",
     "峡谷の地図の余白に、鉱夫が記した書き込みがある。「地鳴り、二十数えるごとに一度」", [flag("gorge_tremor_rhythm")],
     "地図の書き込みは細かすぎて、読み取れなかった。", [], None, {}),
    ("assist_brigitte", "oaksdawn_workshop", "ブリギッテの槌打ちを手伝う", "運動", "中",
     "交互に槌を振るううちに、刃がまっすぐに伸びていった。「筋がいいね。礼だよ」", [gold(25)],
     "火の粉が腕に飛んだ。", [hp(-2)], "brigitte", {}),
    ("swap_tales_elio", "oaksdawn_inn", "エリオと旅の話を交わす", "洞察", "易",
     "「峡谷の地鳴りには間がある。水脈が詰まって、また流れる。その繰り返しさ」", [flag("gorge_tremor_rhythm")],
     "話は弾んだが、役に立ちそうなことは聞けなかった。", [], "elio", {"hidden_after": "recruited_elio"}),
    ("watch_from_wall", "oaksdawn_wall", "峠の向こうを見張る", "知覚", "中",
     "峠をふさぐ大岩の断面に、白く光る三本の爪痕が見えた。", [flag("saw_white_claw")],
     "峠には霞がかかって、何も見えなかった。", [], None, {}),
    ("count_tremors", "gorge_entrance", "地鳴りの間隔を数える", "知覚", "中",
     "地鳴りと地鳴りの間に、決まった静けさがある。その間に動けばいい。", [flag("gorge_tremor_rhythm")],
     "落石が肩をかすめた。", [hp(-2)], None, {}),
    ("search_miner_tent", "gorge_miner_camp", "天幕の下を探る", "調査", "中",
     "崩れた天幕の下から、鉱夫が隠していた小袋が出てきた。", [gold(20)],
     "天幕の支柱が崩れて、埃をかぶった。", [], None, {}),
    ("read_ash_wind", "valley_entrance", "煤の流れを読む", "知覚", "難",
     "煤は谷底から吹き上げる熱風に乗って、一定の向きに流れている。その流れに紛れれば、亡霊の目を逃れられる。", [flag("knows_ash_wind")],
     "煤を吸い込み、喉が焼けるように痛んだ。", [hp(-3)], None, {}),
    ("turn_ash_wraiths", "valley_entrance", "祈りで亡霊を鎮める", "信仰", "中",
     "聖句を唱えると、煤の亡霊たちは苦しげに身をよじり、霧の奥へ退いていった。", [{"current_location": "valley_lava_bridge"}],
     "祈りは煤にかき消された。亡霊たちが一斉にこちらへ向き直る。", [{"start_combat": True}, {"enemy_first": True}], None,
     {"repeatable": True}),
    ("steel_resolve", "valley_nest_gate", "呼吸を整え、覚悟を決める", "信仰", "中",
     "目を閉じて呼吸を数えると、震えが静まっていった。今なら、どんな炎にも向き合える。", [hp(5)],
     "震えは止まらなかった。それでも、前に進むしかない。", [], None, {}),
    ("read_crowd_rumor", "festival_town", "祝宴の噂に耳を傾ける", "知覚", "中",
     "「将軍様の屋敷じゃ、夜番の交代が真夜中に一度きりだとさ」", [flag("mansion_patrol_known")],
     "祝宴の喧騒で、何も聞き取れなかった。", [], None, {}),
    ("case_mansion", "mansion_garden", "屋敷の窓明かりを観察する", "知覚", "難",
     "窓明かりが消える順番で、夜番の巡回路が読めた。", [flag("mansion_patrol_known")],
     "足音に気づいた番犬が、低く唸り始めた。", [flag("mansion_alerted")], None, {}),
    ("search_hidden_drawer", "mansion_study", "机の隠し引き出しを探す", "調査", "難",
     "引き出しの奥の板を外すと、封書が一通出てきた。宛名は「ザンザス殿」。", [flag("heard_xanxus_betrayal")],
     "引き出しは空だった。", [], None, {}),
    ("gauge_king_resolve", "king_private_room", "王の決意を確かめる", "洞察", "難",
     "王は震える手を握りしめた。「……もしドラコが偽りの者なら、わしの前で正体を暴いてくれ。わしが証人になろう」", [],
     "王の表情からは、何も読み取れなかった。", [], "king", {}),
    ("bless_before_report", "royal_gate", "城門の祠で祈る", "信仰", "中",
     "古い祠に手を合わせると、温かな光が胸に灯った。", [hp(5)],
     "祠は苔むして、祈りは届かなかったようだ。", [], None, {}),
    ("appraise_festival_goods", "festival_town", "露店の品を目利きする", "調査", "中",
     "安値で並んでいた古い瓶は、本物の竜の秘薬だった。店主は気づかずに笑っている。", [item("dragon_elixir", "竜の秘薬"), gold(-20)],
     "どれも本物に見えて、決めきれなかった。", [], None, {"requirements": {"gold_gte": 20}}),
]

# (location, object id, name, skill, band, success_text, success_effects, failure_text)
OBSERVES = [
    ("inn", "inn_notice_board", "宿屋の掲示板", "知覚", "易",
     "古い手配書の間に、ゴブリン砦の見取り図が挟まっていた。", [flag("scouted_fort_patrol")], "色あせた張り紙ばかりだった。"),
    ("castle_town", "town_well", "広場の井戸", "知覚", "中",
     "井戸の縁に、誰かが落とした銅貨が引っかかっていた。", [gold(5)], "暗い水面が揺れているだけだ。"),
    ("lost_goblin_crossroads", "crossroads_signpost", "古い道標", "調査", "易",
     "東は砦、北は泉。かすれた文字の横に、誰かが「狼注意」と刻んでいる。", [], "文字はかすれて読めない。"),
    ("goblin_fort", "fort_drain", "砦の排水口", "知覚", "中",
     "排水口の奥から、見張りの寝息が聞こえる。交代までは間がありそうだ。", [flag("scouted_fort_patrol")], "汚水の臭いしかしない。"),
    ("cave_fork", "fork_markings", "壁の刻み目", "調査", "中",
     "小さな刃物で付けたような、新しい刻み目が右の通路へ続いている。", [flag("mina_tracks_found")], "古い傷と見分けがつかない。"),
    ("old_battlefield", "rusted_helmets", "錆びた兜", "調査", "中",
     "兜の内側に、錆びた徽章が引っかかっていた。", [item("rusted_badge", "錆びた兵士の徽章")], "中は泥で詰まっていた。"),
    ("festival_town", "parade_banners", "祝宴の旗", "知覚", "中",
     "王国の旗に並ぶ将軍家の旗だけ、竜の刺繍が霜のような白糸で縫われている。", [flag("noticed_general_frost")],
     "色とりどりの旗が風に揺れているだけだ。"),
    ("mansion_corridor", "frozen_armor", "番兵の鎧", "魔法学", "中",
     "氷の番兵の首の後ろに、魔力の核が透けて見える。", [], "氷の鎧は、ただ冷たく光っている。"),
]

# Neutral descriptions shown before the object is examined.
OBJECT_DESCRIPTIONS = {
    "inn_notice_board": "宿屋の壁の掲示板。依頼や手配書が何枚も重ねて貼られている。",
    "town_well": "広場の古い石の井戸。",
    "crossroads_signpost": "十字路に立つ、傾いた古い道標。",
    "fort_drain": "砦の外壁の根元に開いた、格子付きの排水口。",
    "fork_markings": "分かれ道の岩壁に残る、細かな刻み目。",
    "rusted_helmets": "草むらに転がる、錆びた兜。",
    "parade_banners": "大通りに掲げられた、王国と諸侯の祝宴の旗。",
    "frozen_armor": "回廊に立つ、氷の番兵の鎧。",
}
# Extra visibility for checks tied to someone who is not always in the scene.
VISIBILITY = {
    "ask_gald_extra": {"visible_after": "saved_gald"},
    "robin_archery": {"hidden_after": "recruited_robin"},
    "calm_mina": {"visible_after": "met_mina", "hidden_after": "mina_rescued"},
    "swap_tales_elio": {"visible_after": "met_elio", "hidden_after": "recruited_elio"},
    "appraise_goblin_box": {"hidden_after": "resolved_lost_goblin_box"},
}
CHOICE_KEYS = {"text", "preview", "risk", "requirements", "visible_requirements", "visible_after", "hidden_after", "once",
               "secret", "disabled_reason"}
DC = {"易": 8, "中": 10, "難": 12, "至難": 14}
REVISION = "2026-10-19-checks-e"


def roll(skill: str, band: str) -> dict[str, Any]:
    from host.state import CHECK_SKILLS

    return {"dice_type": f"1d20+{CHECK_SKILLS[skill]}", "dc": DC[band], "skill": skill}


def risk(skill: str, band: str) -> str:
    from host.state import CHECK_ATTRIBUTE_LABELS, CHECK_SKILLS

    return f"{skill}（{CHECK_ATTRIBUTE_LABELS[CHECK_SKILLS[skill]]}）判定・DC{DC[band]}"


def check_action(entry: tuple) -> dict[str, Any]:
    identifier, _, text, skill, band, ok_text, ok_effects, ng_text, ng_effects, npc_id, extra = entry
    extra = dict(extra)
    repeatable = extra.pop("repeatable", False)
    action: dict[str, Any] = {
        "id": identifier, "text": text, "preview": "", "risk": risk(skill, band), "intent_keywords": [text],
        "effects": [], "roll": roll(skill, band),
        "success_effects": deepcopy(ok_effects), "failure_effects": deepcopy(ng_effects),
        "result_texts": {"success": ok_text, "failure": ng_text}, "risk_source": "action",
    }
    if not repeatable:
        action["once"] = f"{identifier}_done"
    if npc_id:
        action["npc_id"] = npc_id
    action.update(VISIBILITY.get(identifier, {}))
    action.update(deepcopy(extra))
    return action


def observe_object(entry: tuple) -> dict[str, Any]:
    _, identifier, name, skill, band, ok_text, ok_effects, ng_text = entry
    return {
        "id": identifier, "name": name, "description": OBJECT_DESCRIPTIONS[identifier], "traits": [],
        "observe_reveals": {"roll": roll(skill, band), "success_text": ok_text, "failure_text": ng_text,
                            "success_effects": deepcopy(ok_effects), "failure_effects": [], "once": f"observed_{identifier}"},
    }


def _add_condition(action: dict[str, Any], kind: str, flag_name: str, reason: str) -> None:
    conditions = action["roll"].setdefault(kind, [])
    if not any(item.get("reason") == reason for item in conditions):
        conditions.append({"requirements": {"flag": flag_name}, "reason": reason})


def apply(pack: dict[str, Any]) -> None:
    locations = {location["id"]: location for location in pack["locations"]}
    new_ids = {entry[0] for entry in CHECKS}
    for location in pack["locations"]:
        location["actions"] = [action for action in location.get("actions", []) if action.get("id") not in new_ids]
    new_texts = {entry[2] for entry in CHECKS}
    for location in pack["locations"]:
        if "choices" in location:
            location["choices"] = [choice for choice in location["choices"] if choice.get("text") not in new_texts]
    for entry in CHECKS:
        action = check_action(entry)
        location = locations[entry[1]]
        location["actions"].append(action)
        # Legacy choice lists mirror actions; older migrations rebuild them from actions.
        if "choices" in location:
            location["choices"].append({key: deepcopy(value) for key, value in action.items() if key in CHOICE_KEYS})
    object_ids = {entry[1] for entry in OBSERVES}
    for location in pack["locations"]:
        if "objects" in location:
            location["objects"] = [item for item in location["objects"] if item.get("id") not in object_ids]
    for entry in OBSERVES:
        locations[entry[0]].setdefault("objects", []).append(observe_object(entry))
    actions = {action["id"]: action for location in pack["locations"] for action in location.get("actions", [])}
    for flag_name, (reason, targets, kind) in LINKS.items():
        for target in targets:
            _add_condition(actions[target], kind, flag_name, reason)
    pack["meta"]["checks_e"] = True
    pack["meta"]["content_revision"] = max(pack["meta"].get("content_revision", ""), REVISION)
    if pack["meta"].get("npc_combat_v041"):
        from .npc_combat import apply as apply_npc_combat

        apply_npc_combat(pack)


def main() -> None:
    for name in PACKS:
        path = ROOT / "host" / "prompt" / "processed" / name
        pack = json.loads(path.read_text(encoding="utf-8"))
        apply(pack)
        path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[checks_e] updated {name}")


if __name__ == "__main__":
    main()
