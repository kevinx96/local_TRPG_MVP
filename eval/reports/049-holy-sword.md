049 工程交付报告

1. 完成了什么

normal 勇者在ドラコ开战时登记觉醒资格，全部五类指定伤害来源共用一次性致死钩子；先锁1HP，再原地换剑、回满HP、设flag并提交觉醒事件。多段攻击继续，阶段转换不重置。觉醒先于守护，第二次致死沿用原规则。
实现 equipped_item 名称/id需求、模型禁止授予/移除圣剑及设置觉醒flag、铁剑normal禁售、B分支揭发变体及单次开战提示、人形态直接伤害×1.3及追加技能。两包同步，迁移幂等；未改敌人原有模板数值、默认提示词、既有模拟器或美术。无新增依赖。
按 brief/spec §9 不 git add、不提交、不写.git，不在仓库tests/新建文件。完整049.patch已经包含tests.patch，不要重复应用。

现状核对：
- 勇者初始鉄の剣无id，运行时目录补全iron_sword；只有勇者模板持有，无商店出售。普攻1d8+str/3、命中90、physical，装备鉄の剣+革の鎧。
- forge.show_sword_to_blacksmith→accept_sword_fusion移除铁剑、换装氷鉄の大剣并设accepted_sword_fusion。商人pay_curse_price_hero移除铁剑；接受诅咒剑会改装备；イアン赠送氷鉄の大剣但保留铁剑。未装备铁剑、净化Ignis、商人夺剑、历史已卖剑都不触发A，未融合也不触发B。normal禁止此后卖铁剑；baby保持原状。
- 击杀defeated_ignis与净化ignis_purified分开；B不依赖Ignis结局。合法融合路径移除铁剑，A/B互斥。
- normal有效剣聖ドラコHP25/def2/dex12；剣聖の一閃1d8+5、氷刃1d8+4、護衛の構え，next_phase=draco_dragon。白竜ヴァイスHP220/def2/dex10，fire1.5、ice/physical/holy均0.25，两个1d12+10攻击和break_guard。现有模板与HEAD逐字典相等。敌人命中沿用051的100覆盖，新技能数据90也受覆盖。
- spec的旧模拟器换剑假设不适用于053实测路线：v3不执行accept_sword_fusion，而是使用イアン赠剑；详见R3。

2. 改动文件

- eval/balance/targets.json
- eval/reports/049-holy-sword.json
- eval/reports/049-holy-sword.md
- host/combat.py
- host/difficulty.py
- host/prompt/processed/difficulty/overlay_revision.json
- host/prompt/processed/dragon_rpg.json
- host/prompt/processed/dragon_rpg_hybrid.json
- host/prompt/processed/scenario_pack.schema.json
- host/state.py
- host/status_effects.py
- scripts/balance/holy_sword_049.py
- scripts/scenario/holy_sword_049.py
- tests/test_balance.py
- tests/test_chapter5.py
- tests/test_checks_e.py
- tests/test_combat_mechanics_v2.py
- tests/test_holy_sword_049.py
- tests/test_loot_economy.py
- tests/test_npc_combat.py
- tests/test_oaksdawn.py
- tests/test_oaksdawn_quests.py
- tests/test_progression_v2.py
- tests/test_rewards_battlefield.py
- tests/test_rumbling_gorge.py
- tests/test_spring_postgame.py
- tests/test_tutorial_slime.py

新增报告另见 eval/reports/049-holy-sword.json / .md；最终完整文件列表和SHA256以manifest.json为准。
测试补丁中除新增049测试，还更新了旧迁移链测试（补跑最新049迁移）、baby checkpoint难度过滤、旧支援专用测试范围和048占位文本审计；未削弱已有数值金标。

3. 验证与测量

G：normal、Lv6、attack_only、鉄の剣+革の鎧、无消耗品/同伴/支援，flags只有defeated_ignis；每组合N=2000，seed20261021。逐组合共用sim.trial_seed(seed,'049:G','hero',index)，没有把组合或worker编号混入随机种子。
属性实读：{"attributes": {"dex": 5, "end": 15, "int": 5, "str": 22, "wis": 5}, "exp": 200, "hp": 45, "level": 6, "mp": 13, "sp": 20}；DEX闪避=2%。与spec一致。
最终圣剑：damage=1d8+78，accuracy=95，ignores_resistance=true。期望原始伤害82.5（未计被动、命中、防御），量级明显高于普通武器；仅修改这三项许可参数中的damage，未修改ドラコ或ヴァイス。

| 组 | Lv2 / Lv4 / Lv6被动ID | 胜率 | Wilson 95% | 总回合均值 | 觉醒后剩余回合均值 |
|---|---|---:|---|---:|---:|
| G1 | departure_spirit / departure_spirit / sword_followup | 82.75% | [0.8103, 0.8434] | 8.5155 | 3.2710 |
| G2 | departure_spirit / departure_spirit / adversity_flame | 84.95% | [0.8332, 0.8645] | 8.7045 | 3.2890 |
| G3 | departure_spirit / unsinkable_shield / sword_followup | 83.00% | [0.8129, 0.8458] | 8.6625 | 3.2805 |
| G4 | departure_spirit / unsinkable_shield / adversity_flame | 83.95% | [0.8228, 0.8549] | 8.8575 | 3.2940 |
| G5 | heavy_armor_lore / departure_spirit / sword_followup | 87.05% | [0.8551, 0.8845] | 9.0425 | 3.3295 |
| G6 | heavy_armor_lore / departure_spirit / adversity_flame | 88.00% | [0.8650, 0.8935] | 9.2425 | 3.3260 |
| G7 | heavy_armor_lore / unsinkable_shield / sword_followup | 86.95% | [0.8540, 0.8836] | 9.2045 | 3.3350 |
| G8 | heavy_armor_lore / unsinkable_shield / adversity_flame | 87.30% | [0.8577, 0.8869] | 9.3730 | 3.3290 |

最低82.75%≥70%，最高88.00%≤90%。1与4 worker完整JSON逐字节一致，SHA256=532cee34dafb7a34a8599589a11926f4cb4cae94b2e4918e7606a46badce8bfe。
调参：命中95、无视抗性固定。1d8+70试跑N100的八组胜率为83/66/83/63/83/73/82/73%；同值N2000为76.65/65.25/75.90/64.40/82.20/73.10/81.90/72.40%，未过最低门槛。第二轮1d8+78、N2000即上述结果；最终w1/w4复跑相同。没有其他候选数值。

觉醒统计（回合使用整场累计编号；剩余回合=结束回合−触发回合）：
- G1: 阶段:回合→次数 {"draco_dragon:10": 6, "draco_dragon:11": 1, "draco_dragon:3": 36, "draco_dragon:4": 557, "draco_dragon:5": 692, "draco_dragon:6": 425, "draco_dragon:7": 200, "draco_dragon:8": 62, "draco_dragon:9": 17, "draco_human:5": 1, "draco_human:6": 3}；觉醒后剩余回合分布 {"3": 1518, "4": 428, "5": 49, "6": 4, "7": 1}。未觉醒赢/输均为0.00%/0.00%。
- G2: 阶段:回合→次数 {"draco_dragon:10": 8, "draco_dragon:11": 3, "draco_dragon:3": 9, "draco_dragon:4": 472, "draco_dragon:5": 674, "draco_dragon:6": 513, "draco_dragon:7": 204, "draco_dragon:8": 79, "draco_dragon:9": 24, "draco_human:5": 6, "draco_human:6": 7, "draco_human:7": 1}；觉醒后剩余回合分布 {"3": 1501, "4": 423, "5": 73, "6": 3}。未觉醒赢/输均为0.00%/0.00%。
- G3: 阶段:回合→次数 {"draco_dragon:10": 6, "draco_dragon:11": 2, "draco_dragon:3": 27, "draco_dragon:4": 478, "draco_dragon:5": 667, "draco_dragon:6": 489, "draco_dragon:7": 225, "draco_dragon:8": 73, "draco_dragon:9": 22, "draco_human:5": 3, "draco_human:6": 8}；觉醒后剩余回合分布 {"3": 1502, "4": 443, "5": 49, "6": 4, "7": 2}。未觉醒赢/输均为0.00%/0.00%。
- G4: 阶段:回合→次数 {"draco_dragon:10": 9, "draco_dragon:11": 3, "draco_dragon:13": 1, "draco_dragon:3": 4, "draco_dragon:4": 384, "draco_dragon:5": 658, "draco_dragon:6": 547, "draco_dragon:7": 251, "draco_dragon:8": 79, "draco_dragon:9": 34, "draco_human:5": 10, "draco_human:6": 16, "draco_human:7": 2, "draco_human:8": 2}；觉醒后剩余回合分布 {"3": 1493, "4": 429, "5": 75, "6": 3}。未觉醒赢/输均为0.00%/0.00%。
- G5: 阶段:回合→次数 {"draco_dragon:10": 10, "draco_dragon:11": 3, "draco_dragon:3": 11, "draco_dragon:4": 301, "draco_dragon:5": 646, "draco_dragon:6": 562, "draco_dragon:7": 309, "draco_dragon:8": 117, "draco_dragon:9": 36, "draco_human:6": 4, "draco_human:7": 1}；觉醒后剩余回合分布 {"3": 1428, "4": 494, "5": 71, "6": 5, "7": 2}。未觉醒赢/输均为0.00%/0.00%。
- G6: 阶段:回合→次数 {"draco_dragon:10": 15, "draco_dragon:11": 7, "draco_dragon:13": 2, "draco_dragon:3": 4, "draco_dragon:4": 218, "draco_dragon:5": 596, "draco_dragon:6": 626, "draco_dragon:7": 339, "draco_dragon:8": 130, "draco_dragon:9": 55, "draco_human:6": 5, "draco_human:7": 2, "draco_human:8": 1}；觉醒后剩余回合分布 {"3": 1434, "4": 482, "5": 82, "6": 2}。未觉醒赢/输均为0.00%/0.00%。
- G7: 阶段:回合→次数 {"draco_dragon:10": 15, "draco_dragon:11": 5, "draco_dragon:3": 8, "draco_dragon:4": 241, "draco_dragon:5": 606, "draco_dragon:6": 589, "draco_dragon:7": 331, "draco_dragon:8": 139, "draco_dragon:9": 49, "draco_human:5": 4, "draco_human:6": 6, "draco_human:7": 3, "draco_human:8": 1, "draco_human:9": 3}；觉醒后剩余回合分布 {"3": 1419, "4": 500, "5": 75, "6": 4, "7": 2}。未觉醒赢/输均为0.00%/0.00%。
- G8: 阶段:回合→次数 {"draco_dragon:10": 17, "draco_dragon:11": 10, "draco_dragon:13": 1, "draco_dragon:3": 2, "draco_dragon:4": 178, "draco_dragon:5": 547, "draco_dragon:6": 641, "draco_dragon:7": 369, "draco_dragon:8": 158, "draco_dragon:9": 57, "draco_human:5": 3, "draco_human:6": 6, "draco_human:7": 6, "draco_human:8": 2, "draco_human:9": 3}；觉醒后剩余回合分布 {"3": 1436, "4": 475, "5": 84, "6": 5}。未觉醒赢/输均为0.00%/0.00%。
ヴァイス剩余HP逐值分布见JSON.gate_results[].summary.dragon_remaining_hp，0包含胜利；若未进二阶段则记None。完整逐样本保存在.tmp-test/049/gate-w1.json。

R1：053 P2实测中位Lv8开战快照，保留其等级、被动、铠甲、饰品及补给，改装铁剑；双方同行者均清空，击杀路线不设ignis_ally。无支援移除六条遭遇支援；全支援启用国王、Robin两条、Mina、Robert、霜封じの護符。两臂唯一觉醒资格差异是defeated_ignis。每格N2000。

| 支援 | 策略 | 普通胜率 | A胜率 | 差值(pp) | 普通/A回合 | >0.92 |
|---|---|---:|---:|---:|---|---|
| none | heuristic_v3 | 7.60% | 100.00% | +92.40 | 22.5515/23.7985 | A超过 |
| none | attack_only | 0.00% | 95.00% | +95.00 | 22.1585/25.9095 | A超过 |
| all | heuristic_v3 | 80.05% | 100.00% | +19.95 | 25.0975/25.3040 | A超过 |
| all | attack_only | 1.25% | 100.00% | +98.75 | 31.4635/33.0930 | A超过 |

R2：P2同一开战快照原有standard准备，武器氷鉄の大剣，同行者和支援保留，heuristic_v3，只切换accepted_sword_fusion。N2000。

| 分支 | 胜率 | 回合均值 | 人形态受伤均值 | 人形态败北率 |
|---|---:|---:|---:|---:|
| ordinary | 99.80% | 18.4930 | 0.5455 | 0.00% |
| B | 99.85% | 18.4830 | 0.7730 | 0.00% |
B与普通胜率差+0.05pp，人形态受伤均值+0.2275；小幅胜率倒挂是该组有限样本观测，不能解释为B更弱或改变数值。B没有胜率门槛。
P0b勇者在053的500条路线均未到达ドラコ，导出快照为空；R1/R2的P0b行无法测量，没有伪造快照。

R3：053 accepted normal路线（每原型勇者N500）

| 原型 | 到达ドラコ | A | B | 都不是 | 原基线条件胜率 |
|---|---:|---:|---:|---:|---|
| P0a | 0/500 | 0 | 0 | 0 | 缺样本 |
| P0b | 0/500 | 0 | 0 | 0 | 缺样本 |
| P0g | 0/500 | 0 | 0 | 0 | 缺样本 |
| P1 | 0/500 | 0 | 0 | 0 | 缺样本 |
| P2 | 117/500 | 0 | 0 | 117 | 88.89% |
| P2s | 77/500 | 0 | 0 | 77 | 89.61% |
| P3 | 45/500 | 0 | 0 | 45 | 0.00% |
这三组到达者全部装备イアン赠送的氷鉄の大剣。原型计数由accepted-records-normal.json的最终装备、Ignis结果及路线不执行融合的代码交叉核对；ドラコ胜败结算不换装备。
normal开战基线：79个已观测职业×遭遇格，每格N200，seed20261021，heuristic_v3，HEAD与修改后逐样本胜败和回合全部一致（含ドラコ）；不同格=[]。这是开战快照回归，不冒称重跑了053的完整14000条路线。
A的R1最高100%超过旧standard、no_fire与0.92限制，按Q10仅受新目标约束。G最高88%满足独立上限。

验证命令与输出：
- python -m unittest discover -s tests -q（仓库原地，未应用测试补丁）：Ran 919 tests in 1341.535s  FAILED (failures=13, errors=40, skipped=1)
- python .tmp-test/049/run_tests.py（首次原地叠加运行，期间修复迁移测试）：Ran 937 tests in 1363.173s  FAILED (failures=14, errors=1, skipped=1)
- 从HEAD归档实际应用补丁，cwd=.tmp-test/049/validation-shard-{0,1,2,3}，python D:/TRPG_Game/.tmp-test/049/run_tests.py --shard I 4（050叠加执行器，按文件索引取模、不重不漏覆盖全套）：937 tests; all_passed=True; 4 isolated shards
原地失败不能标为通过：未应用的旧测试不认识049的迁移链/授权占位文本，普通tempfile在沙箱遇到拒绝访问，同时根目录快照测试受到其他验证创建临时目录影响。测试补丁与050临时目录执行器解决前两类；最终四个独立目录消除快照交叉干扰。中间两次未完成的独立全套记录保留，最终结论以validation-shards.json为准。
- node --check client/app.js：exit 0；客户端未改，无需改?v=。
- 更新后的相关测试：226 tests / 128.847s / OK (skipped=1)；049新增18项全部通过。完整分片的唯一skip仍是既有BALANCE_ENFORCE=1可选门槛。
- python .tmp-test/049/golden.py baby / normal_empty：各113×200，全部逐项相等，SHA256=14d374747913957829d5162d7aa6d52dfd3ce9ec9b3f8560d1e5f96f0fd1caee。
- python tests/baby_levels_golden.py --verify：四职业/四里程碑/诅咒/存读档一致，SHA256=7a03eb88f5f3dc7d4d5c6d89a288f7a99803fbb624a9bfa1c3eb9b84c66f63f9。
- difficulty冻结和未分类数值叶子审计、G3一次性觉醒测试、迁移幂等/同步均通过。baby有效包相对HEAD只差meta.content_revision；baby_numeric_freeze.json原样保留。
- python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --backend gemini --model gemini-3.1-flash-lite --variant guard_rules --split dev：194/194缓存命中，live=false，冻结metrics一致；未调用付费API。
- scripts/playtest/explore.py经只读包装选择baby/normal，各四职业seed20261013、最多330步，exceptions=0、noncombat_dead_ends=0；baby完整summary和runs与HEAD相等。
- python -m scripts.balance.holy_sword_049 --n 2000 --seed 20261021 --workers 1/4 --output ...：G门槛与确定性通过；R1/R2加--report-checkpoints eval/balance/checkpoints_normal_053.json。

4. TODO(design) / 【仮】与美术

- HP锁定日志：【仮】致命の一撃――だが、あなたは倒れなかった。
- 觉醒叙述：【仮】鉄の剣が白く輝き、勇者の聖剣へと姿を変えた。傷がふさがっていく。
- 圣剑description：【仮】眠っていた力を取り戻した、勇者のための剣。
- 圣剑effect：【仮】通常攻撃が光属性になる（运行时道具效果沿用引擎结构化数值显示）。
- 揭发追加句（有/无日誌两处）：【仮】……もっとも、貴様の剣ならすでに我が手にある。我を脅かしうる唯一の刃だ
- 开战提示：【仮】ドラコは勇者の聖剣を装備している。
- 技能名：【仮】聖剣の一閃。
- 铁剑暗示追加：仅【仮】，等待写作线补足意义，不自行创作文案。
以上每包9个文本位置；暂无正式专用剑图，复用现有client/images/icon_dawn_sword.png。ドラコ如何得到剑、铁匠讨伐后台词及结局变体仍交写作线，未擅改现有结局。

5. 推断清单

- 源武器在背包中原地替换且保持装备顺序/数量；资源消耗属于技能成本，按spec枚举的伤害五路径接钩子，未改变其他职业的成本规则。
- HP锁定/觉醒沿用buff/heal视觉，觉醒另记state event进入committed_events；回合分布采用整场累计回合。
- normal铁剑用key_item拦截现有商店逻辑，不设non_removable，因此剧情融合/商人支付仍可移除。normal-only圣剑目录的awakening_origin定义源物品提示和禁售，在两个现有背包补全入口应用；baby过滤后该规则不存在。
- B倍率在普通伤害防御/抗性结算后、受伤倍率/守护/护盾前乘并沿用round取整；原true_damage定义忽略修正，本场现有及新技能均无true_damage。
- R1“全支援”采用现有六条遭遇修正，不把击杀路线不可能拥有的ignis_ally拼入，也不额外引入同行者；R2 standard沿用053原快照。R1/R2样本数未另定，采用每格2000。
- G门槛剩余回合包含觉醒所在回合之后的累计差；单样本不跨配置强制重放相同随机消费序列，仅共用初始种子。

6. 偏离spec与原因

- 为满足baby有效包只差revision且不修改difficulty过滤器，A定义和B开战提示使用既有encounter_modifiers列表的normal-only记录；A登记到运行时combat.lethal_awakenings，不加入会在baby遗留空列表的新顶层键。B modifier一次性warning承担start_event语义，不再额外support重复显示。
- hybrid不新增prepared turn：host/app.py的result_text直接显示分支早于prepared/LLM路径。三个实际API模式（确定性、hybrid、full）×有无日誌共6条输出，均包含追加句，保留日誌句，chat_completion被测试桩禁止；日志见reveal-modes.json。
- 没有浏览器截图：cua.getState实际返回apps=[]、browsers=[]，没有伪造。screens/combat-events.json是引擎真实日志及视觉状态，availability.json记录限制；不能替代浏览器视觉验收。
- P0b无实测开战快照，按053不得伪造的要求标为缺样本。normal完整路线基线未重跑，使用现有实测分支审计与79格成对开战回归。
- 沙箱禁止.git和tests新建，因此只交补丁。多worker使用独立Python进程+文件IPC（命名管道WinError5），没有用共享全局mock的线程进行战斗。
- git archive在本机产生CRLF；验证前仅对待修改源文件规范化LF，再git -c core.autocrlf=false apply；应用结果与交付源文件SHA256逐字节核对。

7. 已知问题

- 旧存档中进行中的ドラコ战没有本次登记快照，不追溯获得觉醒；下一场新建战斗才按新数据登记。
- 文案、美术、真实浏览器视觉验收及P0b补样本待后续。B的胜率只报告；052按用户决定评估大多数正常玩家融合后的价值。
- 依照文件边界没有改053预算/策略实现；其expected_damage估计尚未扩展新enemy_damage_multiplier/extra_enemy_skills字段。本报告B人形态受伤来自实际引擎damage日志，胜败来自完整实战结算，不用预算估计代替。
- A仍保留神聖の庇護状态且不消费旧字段；觉醒后第二次致死的表现保持既有机制。
