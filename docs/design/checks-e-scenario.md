# 判定覆盖率扩充（E）：社交、调查、侦察

设计负责人，2026-10-19。规则见 `checks-v2.md`。日文为定稿文本。

## 原则
- 全部是**新增**的选项，不替换任何现有路径；每个判定只能做一次（`once`）。
- 成功给小好处：道具、金币、情报，或者给之后某个判定带来**优势**（侦察 → 潜行，这是让非盗賊职业也能过潜行判定的主要途径）。
- 失败只有轻微代价：什么都没发生、HP −1〜3，或者给之后某个判定带来劣势。永远不是死路。
- 一部分成功会顺带给出**已有的线索 flag**，作为真结局证据的又一个来源（多条路径的原则），不新增证据种类。

## 优势/劣势的联动（写进对应判定的 `roll.advantage` / `roll.disadvantage`）
| flag | 理由文字 | 给哪些判定优势 |
|---|---|---|
| scouted_fort_patrol | 見張りの交代を知っている | fort_first_bypass、fort_second_bypass、bypass_hobgoblin |
| fort_alerted（劣势） | 見張りが警戒している | fort_first_bypass |
| heat_rhythm_known | 熱風の切れ目を知っている | sneak_heat |
| calmed_crystals | 水晶の共鳴を知っている | sneak_crystal |
| fire_upwind_known | 風上を知っている | approach_burning_village_carefully |
| child_at_window | 子どもが窓辺にいる | climb_to_window、break_burning_beam |
| read_battlefield_mist | 霧の流れを知っている | sneak_bone_field、sneak_ghoul_marsh |
| marsh_path_known | 沈まない足場を知っている | sneak_ghoul_marsh |
| gorge_tremor_rhythm | 地鳴りの間隔を知っている | sneak_gorge_rockfall_path、sneak_gorge_giant_path、sneak_gorge_worm_lair |
| knows_ash_wind | 煤の流れを知っている | sneak_through_ash |
| mansion_patrol_known | 夜番の交代を知っている | sneak_into_mansion、evade_ice_sentinels |
| mansion_alerted（劣势） | 番犬に気づかれている | sneak_into_mansion |

## 新增选项（48）
格式：id ｜ 场所 ｜ 选项文字 ｜ 技能・档 ｜ 成功 ｜ 失败。人物相关的选项在该人物不在（041 倒下或逃走）时隐藏。

### 第 1 章（王都、森）
1. `ask_king_ten_years` ｜ castle ｜ 十年前のことを王に尋ねる ｜ 洞察・中 ｜ 王は言葉を選ぶように目を伏せた。「……あの遠征は、わしの過ちだった。竜の谷へ兵を送れと、強く勧めた者がいたのだ」 王の視線が、一瞬だけ将軍へ向いた。→ set heard_human_caused_dragon_return ｜ 「昔の話はよい。今は竜のことだけを考えてくれ」 王はそれ以上語らなかった。
2. `ask_gald_extra` ｜ castle_town ｜ ガルドにおまけを頼み込む ｜ 説得・中 ｜ 「参ったね、あんたには敵わない」 ガルドは笑って、薬草を一束放ってよこした。→ 薬草 ×1 ｜ 「悪いが、これ以上は負けられないね」
3. `dig_forge_scrap` ｜ forge ｜ 鉄くずの山を漁る ｜ 調査・中 ｜ 鉄くずの底から、まだ使えそうな毒矢が一本出てきた。ローベルトは「持っていけ」とだけ言った。→ 毒矢 ×1 ｜ 錆びた鉄片で指を切った。→ HP −1
4. `listen_inn_gossip` ｜ inn ｜ 酔客の話に耳を傾ける ｜ 知覚・中 ｜ 「砦のゴブリンども、見張りの交代は鐘一つごとだってよ。交代の時は、門の前ががら空きになるんだと」→ set scouted_fort_patrol ｜ 酔客の話は、昨日の喧嘩の自慢ばかりだった。
5. `robin_archery` ｜ inn ｜ ロビンに弓の手ほどきを頼む ｜ 軽業・中 ｜ 「筋は悪くないね」 ロビンは笑って、矢筒から毒矢を二本抜いて渡してくれた。→ 毒矢 ×2 ｜ 弦が跳ねて頬を打った。ロビンが肩を震わせて笑っている。→ HP −1
6. `help_sarah_shelves` ｜ item_shop ｜ サラの棚卸しを手伝う ｜ 運動・易 ｜ 重い木箱を棚の上まで運び終えると、サラが小さな袋を差し出した。「ありがとう！ これ、お駄賃！」→ 10G ｜ 木箱を取り落としてしまった。サラは「大丈夫、割れ物じゃないから」と笑ってくれた。
7. `read_magic_tomes` ｜ magic_shop ｜ 棚の魔導書を読み解く ｜ 魔法学・中 ｜ 魔導書の余白に書き込まれた術式を、白紙の巻物に写し取った。ワーロックが片眉を上げる。「……ほう。持っていくといい」→ 魔法の巻物 ×1 ｜ 文字が頭の中でほどけて、軽い眩暈がした。
8. `search_alley_day` ｜ alley ｜ 路地裏の物陰を探る ｜ 知覚・中 ｜ 積まれた樽の陰に、銀貨が数枚落ちていた。→ 15G ｜ 物陰から飛び出したネズミに驚いて、尻もちをついた。
9. `see_through_merchant` ｜ alley_night ｜ 商人の正体を見極める ｜ 洞察・難 ｜ フードの奥で、獣のような目が一瞬だけ光った。この取引には、必ず裏がある。差し出された品から、かすかに死者の匂いがする。（情報のみ） ｜ 商人の顔はフードの影に沈んで、何も読み取れなかった。
10. `read_forest_tracks` ｜ dark_forest_loc ｜ 獣道の足跡を読む ｜ 知覚・易 ｜ 大きな足跡が泉の方へ続いている。森の奥には狼の群れがいるらしい。足跡のそばで、薬草を一株見つけた。→ 薬草 ×1 ｜ 落ち葉に埋もれて、足跡はよく見えなかった。
11. `question_lost_goblin` ｜ lost_goblin_crossroads ｜ ゴブリンの話の真偽を確かめる ｜ 洞察・中 ｜ ゴブリンの目は嘘をついていない。箱は本当にこいつの一族のものだ。「砦の見張りはな、夜明け前がいちばん眠そうなんだ」→ set scouted_fort_patrol ｜ ゴブリンはおびえて口ごもり、それ以上は何も言わなかった。
12. `commune_spring` ｜ elf_spring ｜ 泉の精霊の声に耳を澄ます ｜ 信仰・中 ｜ 水面がかすかに揺れ、冷たい風が頬をなでた。体の芯から疲れが抜けていく。→ HP +5 ｜ 泉は静かなままだった。
13. `survey_from_hill` ｜ forest_exit ｜ 高台から周囲を見渡す ｜ 知覚・中 ｜ 南の街道は白い霧に沈み、東の空は赤く燃えている。霧は谷から吹き下ろす風に沿って流れているようだ。→ set read_battlefield_mist ｜ 木々に遮られて、遠くまでは見えなかった。

### 第 2 章（砦、洞窟）
14. `scout_fort_walls` ｜ goblin_fort ｜ 砦の外壁を偵察する ｜ 隠密・中 ｜ 外壁に張りついて覗くと、見張りが交代する短い隙が見えた。→ set scouted_fort_patrol ｜ 小石を蹴ってしまい、見張りがこちらの茂みを睨んだ。→ set fort_alerted
15. `listen_fort_corridors` ｜ goblin_fort_second_choice ｜ 通路の奥に耳を澄ます ｜ 知覚・中 ｜ 右の通路からは重い足音が一つ。左からは水の滴る音と、かすかな呻き声が聞こえる。（情報のみ） ｜ 砦の喧騒に紛れて、何も聞き分けられなかった。
16. `study_healing_circle` ｜ goblin_fort_healing_circle ｜ 法陣の紋様を読み解く ｜ 魔法学・中 ｜ 紋様の流れをなぞると、法陣の光が一段強まった。息が軽くなる。→ SP +3 ｜ 紋様は古すぎて、意味が読み取れなかった。
17. `appraise_goblin_box` ｜ goblin_fort_chest_choice ｜ 箱の作りを確かめる ｜ 調査・中 ｜ 箱の底を叩くと、乾いた音がした。二重底の隠しに、金貨が数枚挟まっている。→ 20G ｜ ただの古い木箱にしか見えなかった。
18. `read_heat_flow` ｜ cave_heat_corridor ｜ 熱風の流れを読む ｜ 知覚・中 ｜ 熱風は一定の間隔で弱まる。その切れ目なら、岩陰を伝って抜けられそうだ。→ set heat_rhythm_known ｜ 熱気にあてられて、頭がくらくらした。→ HP −2
19. `listen_cave_fork` ｜ cave_fork ｜ 分かれ道の奥を探る ｜ 知覚・易 ｜ 左の通路からは熱気。右からは湯気と、少女のすすり泣くような声がする。（情報のみ） ｜ 水音が反響して、どちらからの音か分からなかった。
20. `search_lava_room` ｜ cave_lava_room ｜ 溶岩の縁を探る ｜ 軽業・難 ｜ 溶岩の縁に身を乗り出し、冷えかけた赤い欠片をすくい上げた。→ 残り火の欠片 ×1 ｜ 熱で指先を焼いた。→ HP −3
21. `calm_mina` ｜ cave_hot_spring ｜ ミーナを落ち着かせる ｜ 説得・易 ｜ ミーナは深呼吸して、ぽつりぽつりと話し始めた。「あの水晶の木、近づくと共鳴するの。でも、じっとしてれば襲ってこない」→ set calmed_crystals ｜ ミーナは膝に顔を埋めたまま、泣き止まなかった。
22. `tune_crystals` ｜ cave_crystal_corridor ｜ 水晶の音色を聴き分ける ｜ 魔法学・中 ｜ 共鳴には周期がある。音が途切れる瞬間を数えられるようになった。→ set calmed_crystals ｜ 甲高い音に、頭が割れそうになった。→ HP −2

### 第 3 章（村、古戦場、城塞、峡谷）
23. `read_fire_spread` ｜ village_approach ｜ 炎の広がり方を見極める ｜ 調査・中 ｜ 炎は風下へ流れている。風上から回り込めば、焼けずに村へ入れそうだ。→ set fire_upwind_known ｜ 煙を吸い込んで、激しくむせた。→ HP −2
24. `call_to_child` ｜ burning_house ｜ 中の子どもに声をかける ｜ 説得・中 ｜ 「窓のところまで来られるか！」 泣き声がやみ、二階の窓辺へ這ってくる小さな影が見えた。→ set child_at_window ｜ 炎の音にかき消されて、声は届かなかった。
25. `tend_refugees` ｜ village ｜ 負傷者の手当てを手伝う ｜ 信仰・中 ｜ 祈りながら包帯を巻くうちに、傷の浅い者から立ち上がり始めた。村の女が、礼にと聖水を差し出す。→ 聖水 ×1 ｜ 慣れない手当てに手間取ってしまった。村人は黙って頭を下げた。
26. `ask_elder_legend` ｜ village ｜ 長老に昔話をせがむ ｜ 洞察・中 ｜ 「氷の太刀を打ったのは、この村の鍛冶屋じゃった。……今は王都で宿をやっとると聞く」（情報のみ） ｜ 長老は咳き込み、話を途中でやめてしまった。
27. `read_ian_grief` ｜ ian_ice_katana_aftermath ｜ イアンの様子をうかがう ｜ 洞察・中 ｜ 「……あの太刀は、俺の最後の仕事だった。砕いたのは氷の精霊じゃない。誰かが、芯に霜を仕込んでいたんだ」→ set frost_trace_seen ｜ イアンは砕けた刃を見つめたまま、何も言わなかった。
28. `read_mist_flow` ｜ old_battlefield ｜ 霧の流れを読む ｜ 知覚・中 ｜ 霧は谷からの風に沿って、骨の野から沼へ流れている。霧の濃い側を選べば、気づかれずに進めそうだ。→ set read_battlefield_mist ｜ 霧の中で、一瞬方角を見失いかけた。
29. `identify_old_banner` ｜ bone_field ｜ 折れた軍旗を調べる ｜ 調査・中 ｜ 色あせた紋章は、王国軍の第三軍団のものだ。十年前、竜の谷へ送られた部隊。旗の根元に、錆びた徽章が一つ落ちていた。→ 錆びた兵士の徽章 ×1 ｜ 泥にまみれて、紋章は読み取れなかった。
30. `pray_for_ghost` ｜ ruined_watchtower ｜ 亡霊のために祈る ｜ 信仰・中 ｜ 亡霊の表情が、少しだけ和らいだ。「……ありがとう。沼を渡るなら、縁の苔を踏め。あそこだけは沈まない」→ set marsh_path_known ｜ 祈りの言葉は、冷たい風に吹き散らされた。
31. `probe_marsh_depth` ｜ ghoul_marsh ｜ 枝で沼の深さを探る ｜ 調査・中 ｜ 枝を差し込んでいくと、縁の苔の下にだけ硬い地面があった。→ set marsh_path_known ｜ 足を取られ、膝まで泥に沈んだ。→ HP −2
32. `read_knight_epitaph` ｜ grave_chapel ｜ 騎士の墓碑を読む ｜ 調査・中 ｜ 苔をぬぐうと、古い文字が現れた。「我が剣、竜と人の盟約を守る者にのみ譲らん」（情報のみ） ｜ 文字はすり減って、ほとんど読めなかった。
33. `chat_guardsmen` ｜ oaksdawn_square ｜ 守護団員と雑談する ｜ 説得・中 ｜ 「峠の岩か？ 団長に頼めば、すぐどけてくれるさ」 若い団員は、干し肉を一切れ分けてくれた。→ 携帯食 ×1 ｜ 「悪いが、今は見回り中だ」と追い払われた。
34. `study_war_map` ｜ oaksdawn_hq ｜ 卓上の地図を読み解く ｜ 調査・中 ｜ 峡谷の地図の余白に、鉱夫が記した書き込みがある。「地鳴り、二十数えるごとに一度」→ set gorge_tremor_rhythm ｜ 地図の書き込みは細かすぎて、読み取れなかった。
35. `assist_brigitte` ｜ oaksdawn_workshop ｜ ブリギッテの槌打ちを手伝う ｜ 運動・中 ｜ 交互に槌を振るううちに、刃がまっすぐに伸びていった。「筋がいいね。礼だよ」→ 25G ｜ 火の粉が腕に飛んだ。→ HP −2
36. `swap_tales_elio` ｜ oaksdawn_inn ｜ エリオと旅の話を交わす ｜ 洞察・易 ｜ 「峡谷の地鳴りには間がある。水脈が詰まって、また流れる。その繰り返しさ」→ set gorge_tremor_rhythm ｜ 話は弾んだが、役に立ちそうなことは聞けなかった。
37. `watch_from_wall` ｜ oaksdawn_wall ｜ 峠の向こうを見張る ｜ 知覚・中 ｜ 峠をふさぐ大岩の断面に、白く光る三本の爪痕が見えた。→ set saw_white_claw ｜ 峠には霞がかかって、何も見えなかった。
38. `count_tremors` ｜ gorge_entrance ｜ 地鳴りの間隔を数える ｜ 知覚・中 ｜ 地鳴りと地鳴りの間に、決まった静けさがある。その間に動けばいい。→ set gorge_tremor_rhythm ｜ 落石が肩をかすめた。→ HP −2
39. `search_miner_tent` ｜ gorge_miner_camp ｜ 天幕の下を探る ｜ 調査・中 ｜ 崩れた天幕の下から、鉱夫が隠していた小袋が出てきた。→ 20G ｜ 天幕の支柱が崩れて、埃をかぶった。

### 第 4 章（竜の谷）
40. `read_ash_wind` ｜ valley_entrance ｜ 煤の流れを読む ｜ 知覚・難 ｜ 煤は谷底から吹き上げる熱風に乗って、一定の向きに流れている。その流れに紛れれば、亡霊の目を逃れられる。→ set knows_ash_wind ｜ 煤を吸い込み、喉が焼けるように痛んだ。→ HP −3
41. `steel_resolve` ｜ valley_nest_gate ｜ 呼吸を整え、覚悟を決める ｜ 信仰・中 ｜ 目を閉じて呼吸を数えると、震えが静まっていった。今なら、どんな炎にも向き合える。→ HP +5 ｜ 震えは止まらなかった。それでも、前に進むしかない。

41b. `turn_ash_wraiths` ｜ valley_entrance ｜ 祈りで亡霊を鎮める ｜ 信仰・中 ｜ 聖句を唱えると、煤の亡霊たちは苦しげに身をよじり、霧の奥へ退いていった。→ 前往 valley_lava_bridge（同潜行成功） ｜ 祈りは煤にかき消された。亡霊たちが一斉にこちらへ向き直る。→ 开战、敌人先手（同潜行失败）
   - 僧侶的专属路线（D&D 的 Turn Undead）：所有职业都能选，信仰是僧侶的熟练技能。不设 `once`（同潜行，可以作为通过这一关的方法）。0412 的 040 测量里僧侶在此处的死亡大增，这条是对策。

### 第 5 章（凱旋の城下町、屋敷）
42. `read_crowd_rumor` ｜ festival_town ｜ 祝宴の噂に耳を傾ける ｜ 知覚・中 ｜ 「将軍様の屋敷じゃ、夜番の交代が真夜中に一度きりだとさ」→ set mansion_patrol_known ｜ 祝宴の喧騒で、何も聞き取れなかった。
43. `case_mansion` ｜ mansion_garden ｜ 屋敷の窓明かりを観察する ｜ 知覚・難 ｜ 窓明かりが消える順番で、夜番の巡回路が読めた。→ set mansion_patrol_known ｜ 足音に気づいた番犬が、低く唸り始めた。→ set mansion_alerted
44. `search_hidden_drawer` ｜ mansion_study ｜ 机の隠し引き出しを探す ｜ 調査・難 ｜ 引き出しの奥の板を外すと、封書が一通出てきた。宛名は「ザンザス殿」。→ set heard_xanxus_betrayal ｜ 引き出しは空だった。
45. `gauge_king_resolve` ｜ king_private_room ｜ 王の決意を確かめる ｜ 洞察・難 ｜ 王は震える手を握りしめた。「……もしドラコが偽りの者なら、わしの前で正体を暴いてくれ。わしが証人になろう」（情報のみ） ｜ 王の表情からは、何も読み取れなかった。
46. `bless_before_report` ｜ royal_gate ｜ 城門の祠で祈る ｜ 信仰・中 ｜ 古い祠に手を合わせると、温かな光が胸に灯った。→ HP +5 ｜ 祠は苔むして、祈りは届かなかったようだ。
47. `appraise_festival_goods` ｜ festival_town ｜ 露店の品を目利きする ｜ 調査・中 ｜ 安値で並んでいた古い瓶は、本物の竜の秘薬だった。店主は気づかずに笑っている。→ 竜の秘薬 ×1、−20G（20G 以上持っている時だけ選べる） ｜ どれも本物に見えて、決めきれなかった。

## 新增的观察判定（自由输入「観察」，`objects` 的 `observe_reveals`）
| 场所 | 对象 | 技能・档 | 成功 | 失败 |
|---|---|---|---|---|
| inn | 宿屋の掲示板 | 知覚・易 | 古い手配書の間に、ゴブリン砦の見取り図が挟まっていた。→ set scouted_fort_patrol | 色あせた張り紙ばかりだった。 |
| castle_town | 広場の井戸 | 知覚・中 | 井戸の縁に、誰かが落とした銅貨が引っかかっていた。→ 5G | 暗い水面が揺れているだけだ。 |
| lost_goblin_crossroads | 古い道標 | 調査・易 | 東は砦、北は泉。かすれた文字の横に、誰かが「狼注意」と刻んでいる。（情報のみ） | 文字はかすれて読めない。 |
| goblin_fort | 砦の排水口 | 知覚・中 | 排水口の奥から、見張りの寝息が聞こえる。交代までは間がありそうだ。→ set scouted_fort_patrol | 汚水の臭いしかしない。 |
| cave_fork | 壁の刻み目 | 調査・中 | 小さな刃物で付けたような、新しい刻み目が右の通路へ続いている。→ set mina_tracks_found | 古い傷と見分けがつかない。 |
| old_battlefield | 錆びた兜 | 調査・中 | 兜の内側に、錆びた徽章が引っかかっていた。→ 錆びた兵士の徽章 ×1 | 中は泥で詰まっていた。 |
| festival_town | 祝宴の旗 | 知覚・中 | 王国の旗に並ぶ将軍家の旗だけ、竜の刺繍が霜のような白糸で縫われている。→ set noticed_general_frost | 色とりどりの旗が風に揺れているだけだ。 |
| mansion_corridor | 番兵の鎧 | 魔法学・中 | 氷の番兵の首の後ろに、魔力の核が透けて見える。（情報のみ） | 氷の鎧は、ただ冷たく光っている。 |

## 覆盖率
选项判定：31 → 79（约 297 → 345 个行动中占 23%）；观察判定：6 → 14。
