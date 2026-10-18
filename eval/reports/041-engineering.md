# 041 工程汇报

## 1. 完成了什么

已实现当前人物的 attack 自由行动、引擎二次确认、分类保护/反逆/守护者战斗、同伴离队、死亡或逃走的跨场所后果、商店关闭与柜台结算、城镇血债及尾声。确认和取消均不调用模型；普通人物战后沿用现有单次叙述流程，设计给定的倒下文本另写入系统日志。

已加入ガレス的四段轮换对话、血债强制战斗、イグニス两种战后出口的无休息拦截、两阶段 next_phase、胜败及区域重来。确认后即使已有未匹配意图，也先结束该意图，避免战后叙述沿用旧偏离状态。NPC 战斗不会把同场怪物误标为已解决。

两份剧本由幂等迁移生成；重跑文件 SHA-256 不变。新增 24 条 proposed 候选及 13 个快照，gold 留空。三项人物素材各两张候选、灰竜の鱗图标及总览图均已交付；候选 01 装入游戏，全部 approved: false。

## 2. 改动的文件

|范围|文件|
|---|---|
|引擎|host/npc_combat.py；host/free_actions.py；host/app.py；host/combat.py；host/state.py；host/scenario_context.py；host/shops.py；host/quests.py；host/maps.py；host/area_retry.py|
|剧本及兼容迁移|scripts/scenario/npc_combat.py；两份 host/prompt/processed/dragon_rpg*.json；scripts/scenario/ruby_names.py；scripts/scenario/checks_e.py；scripts/scenario/loot_economy.py|
|评测与试玩|scripts/eval/run.py；scripts/eval/npc_combat_candidates.py；scripts/balance/npc_combat.py；scripts/playtest/npc_combat.py；eval/balance/checkpoints.json；eval/candidates/041-npc-attacks.jsonl；eval/snapshots/041_npc_*.json|
|美术与缓存|scripts/scenario/npc_combat_assets.py；scripts/scenario/item_icons.py；assets/manifest.json；assets/candidates/041/；client/images/npc_dragon_knight.png、enemy_dragon_knight_mounted.png、enemy_dragon_knight.png、icon_grey_dragon_scale.png；client/index.html|
|测试|tests/test_npc_combat.py；test_balance_pass2.py；test_epilogue.py；test_rumbling_gorge.py；test_schema_encoding.py；test_item_icons.py|
|报告|本报告；041-balance.json；041-murder-route.json；041-cache-replay.json；041-absence-texts.json；041-playtest/；本次 guard_rules JSON/Markdown；screens/041/dragon-knight-sheet.png|

未改 docs/、eval/benchmark/、个人配置、第三方 raw 资料。未引入依赖；素材缩放与总览沿用仓库已有 Pillow。缓存键更新为 20261019-npc-combat-041。

完整逐文件清单见 [041-files.json](041-files.json)。

## 3. 验证结果

全量测试：`python -m unittest discover -s tests -q`，695 项，258.324 秒，OK (skipped=1)。全量运行使用本机权限以满足既有 Windows 临时目录/进程管道测试；未修改系统权限或 ACL。

|命令|结果|
|---|---|
|python -m unittest tests.test_npc_combat -q|25 项通过，覆盖分类、确认不调用 LLM、守护者、儿童逃走、库存、跨场所消失、区域重来、无视防御、后续出口、地图和上下文|
|python -m unittest tests.test_item_icons tests.test_rumbling_gorge.RumblingGorgeTests.test_both_packs_synchronized_and_reapplication_preserves_existing_content tests.test_observe_supplement -q|17 项通过|
|node --check client/app.js|通过|
|python -m scripts.scenario.npc_combat|两份剧本重复运行文件字节不变|
|python -m scripts.worker_fingerprints --write；python -m scripts.worker_fingerprints|已生成，up to date|
|git diff --check|通过|

冻结回放命令：

```powershell
python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --backend gemini --model gemini-3.1-flash-lite --variant guard_rules --split dev
```

194/194 命中缓存，live=false；S0=173、S1=12、S2=8、S3=1、S4=0，与 2026-10-12T062656092753Z 的报告一致。证据见 [041-cache-replay.json](041-cache-replay.json) 和 [完整回放](2026-10-18T222457933717Z-intent-gemini-gemini-3.1-flash-lite-guard_rules.md)。冻结模式保留旧 prompt、schema 的 operation 枚举和解析枚举。

平衡命令：`python -m scripts.balance.npc_combat --n 1000`。每职业每场 1000 次，seed=20261019，heuristic，purify=false。ガレス沿用 dragon_valley_loc 的 Lv5 检查点；ドラコ沿用既有 draco_battle 的 Lv5 检查点（含ヴァイス）。均满 HP/MP/SP，保留各检查点既有装备、物品及同行者。

|职业|イグニス|竜騎士|ドラコ＋ヴァイス|连续打赢两场 / 1000|イグニス战后存活者中打赢竜騎士|
|---|---:|---:|---:|---:|---:|
|hero|84.8%|85.6%|61.4%|579 / 1000 = 57.9%|579 / 889 = 65.13%|
|cleric|75.1%|60.6%|58.7%|307 / 1000 = 30.7%|307 / 780 = 39.36%|
|mage|70.2%|32.5%|69.0%|298 / 1000 = 29.8%|298 / 704 = 42.33%|
|thief|77.6%|86.1%|63.6%|523 / 1000 = 52.3%|523 / 799 = 65.46%|
|四职业等权平均|76.925%|66.200%|63.175%|42.675%|合并分母 1707 / 3172 = 53.81%|

连续战使用独立的确定性种子序列，因此首战存活率与独立单场列不同；应用真实イグニス结算，不在两战之间补血、使用物品、购物或休息。两战内部仍使用既有 heuristic 的正常战斗行动。详见 [041-balance.json](041-balance.json)。

仅调整了允许的 HP 与伤害骰：骑乘阶段 HP 150→90，三招分别由 1d10+6、1d12+6、2d8+4 调为 1d8+4；人形 HP 100→65，两招由 1d10+9、1d8+8 调为 1d10+5。防御、回避、命中、属性、抗性、两阶段机制均保留。难度排序按四职业等权平均验收，未声称逐职业都满足。

离线通玩：

```powershell
python -m scripts.playtest.explore --characters hero cleric mage thief --seeds 20261013 20261014 102 --workers 3 --output eval/reports/041-playtest/summary.md
python -m scripts.playtest.npc_combat --seeds 41 42 43 44 45 46 47 48 49 50 51 52
```

普通路线 12 局，5 局完成，异常=0、非战斗死路=0、异常兜底叙述=0；覆盖村、古戦場、峡谷。杀店主路线 12 局全部杀死王都鍛冶屋店主，6 局到达拦截、4 局击败ガレス并以 ignis_defeated 完成（45、47、48、50）。其余为正常战斗败北，异常和非战斗死路均为 0。攻击识别的单次模型返回被 mock，确认走公开 API；战斗与后续行动均由真实引擎结算，没有注入属性或资源。脚本按游戏规则购买并装备铠甲，氷鉄の大剣由既有剧情自动装备。成功局进入拦截时 HP 为 22、27、37、25 / 40，未在イグニス结算后休息。见 [普通路线报告](041-playtest/summary.md)、[杀店主路线日志](041-murder-route.json)。

原有 eval/reports/playtest-* 未被覆写，无须恢复。测试与试玩无外部模型网络调用；全量测试保留既有本机 HTTP fixture。

美术已逐张查看并复核 [总览图](screens/041/dragon-knight-sheet.png)。两张立绘与两张人形战斗图为 1024×1536 RGBA，骑乘图保留生成原生尺寸，图标 128×128 RGBA。全部道具图标合计 1,705,679 字节，小于 2MB。完整提示词和参考路径见 assets/candidates/041/generation.json。

## 4. TODO(design) 清单

1. 审定下表中的缺席占位文本。原文不改写，运行时只替换迁移清单中列出的完整原文；多个相关人物中只列实际已离场者。两个剧本分别登记 98 / 102 条原文映射，逐条的原文、来源路径及替换文本见 [041-absence-texts.json](041-absence-texts.json)。替换格式为「{人物名}はもうここにはいない。」；人名采用设计文档/原剧本现有称呼。占位仅保证不重新演出离场者，不作为最终叙事稿。
2. 审定六张人物候选及灰竜の鱗图标。已按要求安装 01，未作最终选图；飞竜的金色装饰、徽章细节、人物年龄与面部一致性需设计最终检查。
3. 守護団の衛兵缺少城堡士兵立绘，按 spec 使用 npc_walter.png。礼拝堂の老司祭原始 NPC 没有 image，保留无图显示，不擅自制作或指定人物外观。
4. 审定 24 条攻击候选的标准答案；gold 未填写。
5. 确认平均胜率验收口径及下列职业差异：hero/thief 的ガレス略易于イグニス，mage 明显难于ドラコ。已询问逐职业要求，未收到额外约束，继续按平均值执行。
6. Worker 需要由设计负责人重新部署。本次已重生成指纹；生成器只取 prompt 首行，该首行未变，故 fingerprints.ts 没有内容差异。未执行部署。

受影响场景逐项表：

|场景|人物|处理及保留的出口|
|---|---|---|
|inn|イアン、ロビン；谈话中提到長老|相关对话、休息、委托和入队隐藏；缺席占位；回城出口、砦路线与其他客人闲谈保留|
|forge|ローベルト|店铺、锻造、家传锤委托及其分组选项隐藏；回城保留|
|item_shop|サラ、火コウモリ竜|守护兽死亡使サラ逃走；店铺/借用/委托隐藏；回城保留|
|alley_night、alley_after|怪しい商人|交易/相关选项隐藏；旧剧情战斗也登记死亡；回城保留|
|castle_town、festival_town|ガルド|全部场所的商店和对话一起隐藏；城市移动、匿名露店与群众闲谈保留|
|village|長老、リク、ガルド、店主|各自的对话、店铺、休息、交还儿童入口隐藏；往谷、王都、结冰地点的出口保留；匿名村民炊事与救护保留|
|burning_house|リク|离场后救援选项隐藏，儿童相关演出使用占位；「先を急ぐ」保留|
|ian_ice_katana_aftermath|イアン|拒绝/接受请求及 E 洞察选项隐藏，严肃立绘去除；补「先へ進む」到 valley_entrance，不授予武器或完成委托|
|cave_hot_spring|ミーナ|对话、救援、等待、入队及 E 选项隐藏；温泉休息与前后/水路出口保留|
|magic_shop|ミーナ|相关询问/报平安与立绘隐藏；ワーロック及独立魔法店功能保留|
|forest_wolves|ガルド|缺席占位；不再授予 saved_gald；森狼仍需独立解决，不因杀 NPC 被判已清场；返回泉和正常战斗/通行保留|
|lost_goblin_crossroads|迷子のゴブリン|相关对话/援助隐藏；直行、返回、砦入口保留|
|goblin_fort_chest_choice|迷子のゴブリン|交箱/争箱相关入口隐藏，补「森の出口へ向かう」；无主箱原有分支保留其原条件|
|goblin_fort_chest_fight|迷子のゴブリン|原剧情战斗同步死亡后果，战后缺席占位；原回程结算保留|
|goblin_fort_third_gate|ロビン|涉及ロビン的叙述使用占位；机关、楼层出口及其原条件不变|
|mansion_garden|ロビン|涉及ロビン的叙述使用占位；庭院潜行与通道保留|
|oaksdawn_hq|ヴァルター；提及リーゼ|団长相关选项隐藏；地图观察与返回大街保留；相关叙述用占位|
|oaksdawn_chapel|リーゼ、老司祭|招募、委托/交付、祈祷或圣水店按所属人物隐藏；描述变体及地图同步缺席；返回大街保留|
|oaksdawn_workshop|ブリギッテ|锻造、工房商店、火床委托隐藏；返回大街保留|
|oaksdawn_inn|エリオ|对话/入队/E 选项隐藏，描述变体及地图同步缺席；匿名旅店服务、其他客人传闻、返回大街保留|
|gorge_worm_lair|エリオ|同行者放水选项关联 elio；战斗、退路和原通行条件保留|
|oaksdawn_wall|ガレス|四段对话/血债挑战随状态切换；击败后人物与选项消失，城塞出口保留|
|ignis_last_breath、ignis_purified、dragon_valley_return|ガレス|未击败且有血债时回城必经拦截；获胜到 royal_gate；曾击败则直接回城|

场景之外的缺席映射还包括 dark_forest 场景摘要、四张地图的相关说明、火コウモリ竜同伴说明，以及守護団の推薦状、聖銀、ローベルトのハンマー的说明。道具本身保留；是否应保留这些历史人物提及，交设计定稿时细化。已有尾声中重新描写离场人物的条目被过滤，最后追加设计给定的血债文本。

## 5. 推断清单

1. 未规定逐职业排序，按四职业等权平均判定难度；每场各自使用既有 Lv5 检查点，ガレス复制イグニス检查点。连续战也用该检查点并关闭浄化，以实测击败イグニス后状态。
2. 战士模板未给每人的命中：ロビン、エリオ、ミーナ取 85，リーゼ、ヴァルター取 90；普通攻击均 1d8+3。リーゼ的自疗为 7（36 HP 的约 20%），半血以下可用，与攻击按既有技能选择器等权选取。
3. 未指定的普通人物防御/回避/抗性沿用空模板默认；怪しい商人保留明确给出的回避 15。普通 NPC 遭遇取 elite 且允许逃跑，ガレス明确禁止逃跑。
4. 部分敌人死亡后逃跑或败北，已死亡的具名人物仍永久离场。匿名衛兵死亡也产生 town_blood，但不新增全局的某一位衛兵死亡人物记录；再次挑战时按守护者模板生成。
5. 血债按实际场所判定。村中的「砕けた氷の太刀」按城镇计；森林里的ガルド不计城镇，温泉ミーナ与迷子ゴブリン不计城镇。
6. 長老死亡即让リク离场，包括尚未完成救援的状态；此后燃烧民家的救援入口隐藏并保留出口。守护兽死亡同样始终触发サラ逃走。
7. ガルド只结算当前场所对应商店；当前场所没有商店时使用其第一份商店定义。两家店一起关闭，钱箱只得 50G 一次。商品重叠条件不累加：限量商品取剩余库存，非限量高价商品取一件。
8. 柜台高价依据商店 offer.price（购买标价）判断，不把物品转卖价作为 40G 阈值，也不受购买折扣影响。
9. 对未写 npc_id 的旧选项按直接对话/店主关系补关联，分组选项向下继承；visit_village 的标签明确是询问長老，故关联 elder。匿名旅店、群众、露店、难民炊事不归属已命名 NPC，保留。
10. 旧的迷子ゴブリン与怪しい商人剧情战斗也走具名人物后果，以避免另一条战斗入口杀死后人物仍出现。
11. イアン离场后新增出口直接去 valley_entrance，不补发其武器、委托完成或奖励；无主箱新增出口到 forest_exit，不自动发放箱子奖励。
12. 采用按整段原文登记、运行时替换的最小占位方案，暂时连同段落中的环境或历史描述一起替换；缺席人物映射只改变展示和上下文，不改既有剧情正文。
13. 新拦截位置加入龙谷既有 D4 节点，以沿用区域重来入口；未新画地图节点。新固定文本按设计原文，直接攻击ガレス时沿用挑战开场，即使尚无血债。
14. 守护者优先看存活与设计给定条件，不要求它仍显示在本地 NPC 列表；因此已同行的ロビン/火コウモリ竜也能离队护主。礼拝堂リーゼ以未 recruited_liese 为守护条件。
15. 美术未指定的发色、发型、短胡须、枪/徽章细节及灰鳞形状属于候选生成推断；参考 Walter/Robin，并以立绘作为两种战斗形态的身份参考，全部待选图。
16. 没有独立 NPC 记录的剧情敌人不额外增设对话面；已有剧情 NPC 默认 generic 保护，战斗期间仍由既有战斗 API 管控行动。
17. ガレス的 NPC 简介用现有势力、人物与场所名称组成最短资料摘要；灰竜の鱗说明暂时只重复道具名，匿名守护衛兵说明只重复其名称。均未扩写人物背景，需设计补充定稿。

## 6. 偏离 spec 的地方及原因

无超出授权范围的功能变更。HP/伤害骰调整、缺席占位文字、守护衛兵使用 Walter 占位以及候选 01 临时安装，均为 spec 明确允许。难度的“介于两者之间”采用平均胜率口径，属于上节已披露的解释；不等同于每职业满足排序。

唯一素材缺口是老司祭原始记录没有立绘，现有工程素材无法直接复用为该人物；保留无图，列 TODO(design)，未自行决定人物外观。

## 7. 已知问题

- 缺席叙述是短占位，人物在历史叙述中的提及也可能被一并删掉，需要设计定稿。
- 按平均胜率达到目标，但 mage 的ガレス胜率偏低；hero/thief 的相对排序与平均不同。模拟是既有 heuristic 和指定检查点的结果，不代表全部玩家策略。
- 老司祭尚无立绘；匿名衛兵暂用 Walter。候选均未批准。
- 新攻击候选尚未作真实模型测试；其标准答案待设计审定。本任务仅进行了冻结缓存回放、离线引擎测试和模拟。
- Worker 尚未重新部署，须由设计负责人执行。
