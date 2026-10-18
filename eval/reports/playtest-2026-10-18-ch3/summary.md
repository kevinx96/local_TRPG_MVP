# 037 第三轮离线试玩回归

32局，职业：hero, cleric, mage, thief；种子：20261013, 20261014, 101, 102, 103, 104, 105, 106；每局最多250步。战斗每个指令和结算各占一步。
首次战斗死亡后重来一次，选择次数及随机流继续累计。选项、判定和战斗的随机数均固定。
首次死亡包含剧情导致的死亡结局；剧情必败但仍能继续的战斗不计死亡，冒険完了也不计死亡。
路线轮换沿用037第二轮：使用20261013、20261014、102、101、103、104、105、106的顺序，循环村／古戦場／峡谷；仅交换101与102的优先路线，让第一轮能到达第三章的魔法使い/102走峡谷。运行仍按原种子列表，子集映射固定。村优先种子如从洞窟先到城塞，则从古戦場入口返回森林出口走村。古戦場和峡谷保留现行城塞访问、招募与路线内策略，其余仍按选项使用次数、章节推进偏好及固定随机数选择。
实际路线以village_approach／bone_field／gorge_entrance首次进入为准，old_battlefield仅作为城塞通道时不算走古戦場。重来分别记attempt，同行者记录路线入口和全程变化，不以最终同行者代替。
线索flag从凱旋の間告发条件与既有mystery任务读取；曾取得与最终保留分别统计。选择重合率只取实际剧本选项的（地点ID、选项ID）集合，排除无判定、无一次性标记且效果只有移动/背景的纯移动；不含战斗指令。
通关以剧本的冒険完了结局为准。Jaccard取所有通关局的无序两两组合，包含同一局重来前的经历；没有足够通关局时返回null。空集合对定义为1。
LLM 配置指向 127.0.0.1:1，并在请求适配器直接模拟连接失败；禁止真实网络。

|职业|种子|首次死亡|重来次数|结局|步数|第三章路线（入口同行者）|线索flag|
|---|---:|---|---:|---|---:|---|---|
|hero|20261013|无|0|draco_defeated_with_ignis @ draco_battle|117|village (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_ignis_testimony, heard_pass_rumor, heard_xanxus_betrayal, noticed_general_frost|
|hero|20261014|无|0|ignis_defeated @ castle_report|196|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_last_words, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, noticed_general_frost|
|hero|101|无|0|ignis_defeated @ castle_report|136|village (paladin_liese, attempt 0)|heard_guardian_refusal, heard_ignis_last_words, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost|
|hero|102|无|0|ignis_purified @ castle_report|109|gorge (hydromancer_elio, attempt 0)|heard_guardian_refusal, heard_ignis_testimony, heard_pass_rumor, heard_treaty_lore, read_miner_diary, saw_white_claw|
|hero|103|xanxus_ultimatum|0|defied_xanxus @ xanxus_ultimatum|118|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore|
|hero|104|goblin_fort_fourth|1|ignis_defeated @ castle_report|165|gorge (hydromancer_elio, attempt 1)|frost_trace_seen, heard_guardian_refusal, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, read_miner_diary, saw_white_claw|
|hero|105|village_fire_elemental|1|frost_wolf_defeat @ frost_wolf_battle|118|village (none, attempt 0); village (none, attempt 1); battlefield (paladin_liese, attempt 1)|frost_trace_seen, heard_gald_rumor, heard_guardian_refusal, heard_human_caused_dragon_return, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, noticed_general_frost|
|hero|106|无|0|draco_defeated @ draco_battle|151|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_last_words, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|cleric|20261013|无|0|ignis_purified @ castle_report|122|village (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_pass_rumor, heard_treaty_lore, noticed_general_frost|
|cleric|20261014|draco_battle|1|ignis_purified @ castle_report|186|battlefield (paladin_liese, attempt 0); village (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, noticed_general_frost|
|cleric|101|ice_elemental_encounter|1|ignis_purified @ castle_report|171|village (paladin_liese, attempt 0); village (paladin_liese, attempt 1)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost|
|cleric|102|xanxus_ultimatum|0|defied_xanxus @ xanxus_ultimatum|109|gorge (hydromancer_elio, attempt 0); village (hydromancer_elio, attempt 0)|heard_guardian_refusal, heard_pass_rumor, heard_treaty_lore, read_miner_diary, saw_white_claw|
|cleric|103|dragon_valley_loc|1|ignis_purified @ castle_report|135|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_ignis_testimony, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|cleric|104|draco_battle|1|ignis_purified @ castle_report|174|gorge (hydromancer_elio, attempt 0)|heard_guardian_refusal, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, read_miner_diary, saw_white_claw|
|cleric|105|无|0|ignis_purified @ castle_report|81|village (robin, attempt 0)|heard_human_caused_dragon_return, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost|
|cleric|106|grave_chapel|1|dragon_valley_defeat @ dragon_valley_loc|164|battlefield (paladin_liese, attempt 0); battlefield (paladin_liese, attempt 1)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|mage|20261013|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|86|未到达|heard_human_caused_dragon_return|
|mage|20261014|lost_goblin_crossroads|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|75|未到达|heard_human_caused_dragon_return, heard_treaty_lore|
|mage|101|goblin_fort_second_left|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|68|未到达|heard_human_caused_dragon_return, heard_treaty_lore|
|mage|102|frost_wolf_battle|1|draco_victory @ draco_battle|119|gorge (hydromancer_elio, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_pass_rumor, heard_treaty_lore, read_miner_diary, saw_white_claw|
|mage|103|slime_king_battle|1|combat_defeat @ grave_chapel|81|battlefield (paladin_liese, attempt 1)|heard_guardian_refusal, heard_old_soldier_ghost, heard_pass_rumor|
|mage|104|goblin_fort_fourth|1|slime_king_battle_defeat @ slime_king_battle|74|未到达|无|
|mage|105|无|0|ignis_defeated @ castle_report|85|village (none, attempt 0)|frost_trace_seen, heard_ignis_last_words, heard_xanxus_betrayal|
|mage|106|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|56|未到达|heard_human_caused_dragon_return|
|thief|20261013|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|95|未到达|heard_human_caused_dragon_return|
|thief|20261014|ice_elemental_encounter|1|draco_defeated @ draco_battle|149|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_gald_rumor, heard_guardian_refusal, heard_ignis_last_words, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|thief|101|goblin_fort_second_left|1|draco_victory @ draco_battle|206|village (paladin_liese, attempt 1)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_last_words, heard_pass_rumor, heard_treaty_lore|
|thief|102|frost_wolf_battle|1|draco_defeated @ draco_battle|128|gorge (hydromancer_elio, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_pass_rumor, heard_treaty_lore, read_miner_diary, saw_white_claw|
|thief|103|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|66|未到达|无|
|thief|104|goblin_fort_second_left|1|draco_victory @ draco_battle|140|gorge (hydromancer_elio, attempt 1)|heard_guardian_refusal, heard_ignis_last_words, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, read_miner_diary, saw_white_claw|
|thief|105|无|0|ignis_defeated @ castle_report|116|village (none, attempt 0)|frost_trace_seen, heard_gald_rumor, heard_ignis_last_words, heard_treaty_lore, heard_xanxus_betrayal|
|thief|106|goblin_fort_second_left|1|defied_xanxus @ xanxus_ultimatum|144|battlefield (paladin_liese, attempt 1); village (paladin_liese, attempt 1)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_old_soldier_ghost, heard_pass_rumor|

最远地点口径：按主线章节、地图节点顺序取最大值；砦/洞窟归森林章、屋敷归王城归还章。同级支线没有唯一剧情顺序，完整到访记录见逐步日志。

最终分布：{"draco_defeated_with_ignis": 1, "ignis_defeated": 5, "ignis_purified": 7, "defied_xanxus": 3, "frost_wolf_defeat": 1, "draco_defeated": 3, "dragon_valley_defeat": 1, "goblin_fort_fourth_defeat": 6, "draco_victory": 3, "combat_defeat": 1, "slime_king_battle_defeat": 1}

首次死亡地点：{"xanxus_ultimatum": 2, "goblin_fort_fourth": 6, "village_fire_elemental": 1, "draco_battle": 2, "ice_elemental_encounter": 2, "dragon_valley_loc": 1, "grave_chapel": 1, "lost_goblin_crossroads": 1, "goblin_fort_second_left": 4, "frost_wolf_battle": 2, "slime_king_battle": 1}

重来后分布：{"ignis_defeated": 1, "frost_wolf_defeat": 1, "ignis_purified": 4, "dragon_valley_defeat": 1, "goblin_fort_fourth_defeat": 6, "draco_victory": 3, "combat_defeat": 1, "slime_king_battle_defeat": 1, "draco_defeated": 2, "defied_xanxus": 1}

## 不变量检查

- 异常、非战斗死路及兜底叙述：0 项。
- 古戦場到访：19/32局。
- 城塞到访：22/32局。
- 峡谷到访：7/32局；完成峡谷：7局。
- 经礼拝堂到村后门：9/32局。
- 同一地点重来后再次死亡（仅作为循环候选，不能据此证明必死）：mage/20261013 @ goblin_fort_fourth, mage/106 @ goblin_fort_fourth, thief/20261013 @ goblin_fort_fourth, thief/103 @ goblin_fort_fourth

不变量分类：{"exceptions": 0, "noncombat_dead_ends": 0, "fallback_narrations": 0}

各职业实际路线覆盖：{"hero": {"village": 3, "battlefield": 4, "gorge": 2}, "cleric": {"village": 5, "battlefield": 3, "gorge": 2}, "mage": {"village": 1, "battlefield": 1, "gorge": 1}, "thief": {"village": 3, "battlefield": 2, "gorge": 2}}

## 通关局重合率

通关局16局。

|集合|配对数|均值|最小|最大|
|---|---:|---:|---:|---:|
|choices|120|0.3592|0.1549|0.6000|
|locations|120|0.5474|0.2969|0.9737|

## 线索覆盖

|flag|曾取得局数|最终保留局数|
|---|---:|---:|
|frost_trace_seen|16|13|
|has_assassin_crest|0|0|
|heard_gald_rumor|3|3|
|heard_guardian_refusal|22|22|
|heard_human_caused_dragon_return|15|15|
|heard_ignis_last_words|8|8|
|heard_ignis_testimony|3|3|
|heard_old_soldier_ghost|10|10|
|heard_pass_rumor|22|22|
|heard_treaty_lore|23|23|
|heard_xanxus_betrayal|13|13|
|noticed_general_frost|8|8|
|read_miner_diary|7|7|
|saw_white_claw|7|7|

## 从未到达的地点

- `merchant_battle`：夜の路地・亡霊戦
- `alley_after`：静まり返った夜の路地
- `xanxus_phantom_battle`：Xanxusの分身
- `inn_night_ambush`：宿屋・深夜の襲撃

## 逐步记录

- [hero-20261013.md](logs/hero-20261013.md)
- [hero-20261014.md](logs/hero-20261014.md)
- [hero-101.md](logs/hero-101.md)
- [hero-102.md](logs/hero-102.md)
- [hero-103.md](logs/hero-103.md)
- [hero-104.md](logs/hero-104.md)
- [hero-105.md](logs/hero-105.md)
- [hero-106.md](logs/hero-106.md)
- [cleric-20261013.md](logs/cleric-20261013.md)
- [cleric-20261014.md](logs/cleric-20261014.md)
- [cleric-101.md](logs/cleric-101.md)
- [cleric-102.md](logs/cleric-102.md)
- [cleric-103.md](logs/cleric-103.md)
- [cleric-104.md](logs/cleric-104.md)
- [cleric-105.md](logs/cleric-105.md)
- [cleric-106.md](logs/cleric-106.md)
- [mage-20261013.md](logs/mage-20261013.md)
- [mage-20261014.md](logs/mage-20261014.md)
- [mage-101.md](logs/mage-101.md)
- [mage-102.md](logs/mage-102.md)
- [mage-103.md](logs/mage-103.md)
- [mage-104.md](logs/mage-104.md)
- [mage-105.md](logs/mage-105.md)
- [mage-106.md](logs/mage-106.md)
- [thief-20261013.md](logs/thief-20261013.md)
- [thief-20261014.md](logs/thief-20261014.md)
- [thief-101.md](logs/thief-101.md)
- [thief-102.md](logs/thief-102.md)
- [thief-103.md](logs/thief-103.md)
- [thief-104.md](logs/thief-104.md)
- [thief-105.md](logs/thief-105.md)
- [thief-106.md](logs/thief-106.md)

## 复现

```powershell
python -m scripts.playtest.explore --characters hero cleric mage thief --seeds 20261013 20261014 101 102 103 104 105 106 --steps 250 --output "D:/TRPG_Game/eval/reports/playtest-2026-10-18-ch3/summary.md"
```

剧本 SHA-256：

- dragon_rpg.json: `052d242599d056a4aa13bf459d7d9cf82f6040af4952e58cc2de39bc2aa757af`
- dragon_rpg_hybrid.json: `fd8841ad7dba1c3970328d7a3c764b8e0fca04a6af386b317ecf8a731011b578`

## 历史对照

第一轮：[汇总](round1-summary.md)、[JSON](round1-summary.json)；第二轮：[汇总](round2-summary.md)、[JSON](round2-summary.json)。当前逐局日志为第三轮；第二轮日志可从ca7fa8c取回。
