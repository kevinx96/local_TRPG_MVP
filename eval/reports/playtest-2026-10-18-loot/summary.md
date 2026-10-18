# 离线试玩回归（summary）

32局，职业：hero, cleric, mage, thief；种子：20261013, 20261014, 101, 102, 103, 104, 105, 106；每局最多250步。战斗每个指令和结算各占一步。
首次战斗死亡后重来一次，选择次数及随机流继续累计。选项、判定和战斗的随机数均固定。
首次死亡包含剧情导致的死亡结局；剧情必败但仍能继续的战斗不计死亡，冒険完了也不计死亡。
037第二轮：路线轮换使用20261013、20261014、102、101、103、104、105、106的顺序，循环村／古戦場／峡谷；仅交换101与102的优先路线，让第一轮能到达第三章的魔法使い/102走峡谷。运行仍按原种子列表，子集映射固定。村优先种子如从洞窟先到城塞，则从古戦場入口返回森林出口走村。古戦場和峡谷保留现行城塞访问、招募与路线内策略，其余仍按选项使用次数、章节推进偏好及固定随机数选择。
实际路线以village_approach／bone_field／gorge_entrance首次进入为准，old_battlefield仅作为城塞通道时不算走古戦場。重来分别记attempt，同行者记录路线入口和全程变化，不以最终同行者代替。
线索flag从凱旋の間告发条件与既有mystery任务读取；曾取得与最终保留分别统计。选择重合率只取实际剧本选项的（地点ID、选项ID）集合，排除无判定、无一次性标记且效果只有移动/背景的纯移动；不含战斗指令。
通关以剧本的冒険完了结局为准。Jaccard取所有通关局的无序两两组合，包含同一局重来前的经历；没有足够通关局时返回null。空集合对定义为1。
LLM 配置指向 127.0.0.1:1，并在请求适配器直接模拟连接失败；禁止真实网络。

|职业|种子|首次死亡|重来次数|结局|步数|第三章路线（入口同行者）|线索flag|
|---|---:|---|---:|---|---:|---|---|
|hero|20261013|无|0|ignis_purified @ castle_report|117|village (paladin_liese, attempt 0)|heard_guardian_refusal, heard_pass_rumor, heard_treaty_lore, noticed_general_frost|
|hero|20261014|无|0|ignis_purified @ castle_report|118|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_testimony, heard_old_soldier_ghost, heard_pass_rumor, heard_xanxus_betrayal, noticed_general_frost|
|hero|101|无|0|ignis_purified @ castle_report|95|village (fire_bat_dragon, attempt 0)|heard_ignis_testimony, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost|
|hero|102|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|95|未到达|heard_human_caused_dragon_return|
|hero|103|无|0|ignis_defeated @ castle_report|152|battlefield (paladin_liese, attempt 0)|heard_guardian_refusal, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore|
|hero|104|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|91|未到达|无|
|hero|105|无|0|ignis_purified @ castle_report|71|village (robin, attempt 0)|heard_human_caused_dragon_return, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost|
|hero|106|无|0|draco_defeated @ draco_battle|160|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|cleric|20261013|draco_battle|1|ignis_purified @ castle_report|121|village (robin, attempt 0)|frost_trace_seen, heard_human_caused_dragon_return, heard_treaty_lore, noticed_general_frost|
|cleric|20261014|无|0|ignis_purified @ castle_report|144|battlefield (paladin_liese, attempt 0)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_testimony, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost|
|cleric|101|draco_battle|1|ignis_purified @ castle_report|179|village (fire_bat_dragon, attempt 0)|has_assassin_crest, heard_human_caused_dragon_return, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost|
|cleric|102|xanxus_ultimatum|0|defied_xanxus @ xanxus_ultimatum|107|gorge (hydromancer_elio, attempt 0)|frost_trace_seen, heard_gald_rumor, heard_guardian_refusal, heard_pass_rumor, heard_treaty_lore, read_miner_diary, saw_white_claw|
|cleric|103|ice_elemental_encounter|1|dragon_valley_defeat @ valley_entrance|105|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_old_soldier_ghost, heard_pass_rumor|
|cleric|104|dragon_valley_loc|1|ignis_purified @ castle_report|151|gorge (hydromancer_elio, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, read_miner_diary, saw_white_claw|
|cleric|105|无|0|ignis_purified @ castle_report|81|village (robin, attempt 0)|heard_human_caused_dragon_return, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost|
|cleric|106|frost_wolf_battle|1|draco_victory @ draco_battle|191|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_testimony, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|mage|20261013|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|79|未到达|heard_human_caused_dragon_return|
|mage|20261014|lost_goblin_crossroads|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|75|未到达|heard_human_caused_dragon_return, heard_treaty_lore|
|mage|101|无|0|draco_defeated @ draco_battle|121|village (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_last_words, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|mage|102|slime_king_battle|1|draco_victory @ draco_battle|167|gorge (hydromancer_elio, attempt 1)|heard_guardian_refusal, heard_ignis_last_words, heard_pass_rumor, heard_treaty_lore, read_miner_diary, saw_white_claw|
|mage|103|slime_king_battle|1|ignis_defeated @ castle_report|133|battlefield (paladin_liese, attempt 1)|heard_gald_rumor, heard_guardian_refusal, heard_ignis_last_words, heard_old_soldier_ghost, heard_pass_rumor, heard_xanxus_betrayal|
|mage|104|goblin_fort_fourth|1|draco_defeated @ draco_battle|117|gorge (hydromancer_elio, attempt 1)|heard_guardian_refusal, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, read_miner_diary, saw_white_claw|
|mage|105|无|0|draco_defeated @ draco_battle|75|village (none, attempt 0)|heard_ignis_last_words, heard_xanxus_betrayal|
|mage|106|goblin_fort_fourth|1|dragon_valley_defeat @ valley_ledge|133|battlefield (paladin_liese, attempt 1)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_old_soldier_ghost, heard_pass_rumor|
|thief|20261013|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|87|未到达|heard_human_caused_dragon_return|
|thief|20261014|无|0|ignis_defeated @ castle_report|152|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|thief|101|draco_battle|1|ignis_defeated @ castle_report|147|village (paladin_liese, attempt 0)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_last_words, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|thief|102|无|0|ignis_purified @ castle_report|124|gorge (hydromancer_elio, attempt 0)|heard_guardian_refusal, heard_ignis_testimony, heard_pass_rumor, heard_treaty_lore, read_miner_diary, saw_white_claw|
|thief|103|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|68|未到达|无|
|thief|104|goblin_fort_second_left|1|slime_king_battle_defeat @ slime_king_battle|106|未到达|无|
|thief|105|无|0|ignis_defeated @ castle_report|97|village (none, attempt 0)|frost_trace_seen, heard_ignis_last_words, heard_xanxus_betrayal|
|thief|106|goblin_fort_second_left|1|combat_defeat @ grave_chapel|136|battlefield (paladin_liese, attempt 1)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_old_soldier_ghost, heard_pass_rumor|

最远地点口径：按主线章节、地图节点顺序取最大值；砦/洞窟归森林章、屋敷归王城归还章。同级支线没有唯一剧情顺序，完整到访记录见逐步日志。

最终分布：{"ignis_purified": 10, "goblin_fort_fourth_defeat": 6, "ignis_defeated": 5, "draco_defeated": 4, "defied_xanxus": 1, "dragon_valley_defeat": 2, "draco_victory": 2, "slime_king_battle_defeat": 1, "combat_defeat": 1}

首次死亡地点：{"goblin_fort_fourth": 7, "draco_battle": 3, "xanxus_ultimatum": 1, "ice_elemental_encounter": 1, "dragon_valley_loc": 1, "frost_wolf_battle": 1, "lost_goblin_crossroads": 1, "slime_king_battle": 2, "goblin_fort_second_left": 2}

重来后分布：{"goblin_fort_fourth_defeat": 6, "ignis_purified": 3, "dragon_valley_defeat": 2, "draco_victory": 2, "ignis_defeated": 2, "draco_defeated": 1, "slime_king_battle_defeat": 1, "combat_defeat": 1}

## 不变量检查

- 异常、非战斗死路及兜底叙述：0 项。
- 古戦場到访：16/32局。
- 城塞到访：18/32局。
- 峡谷到访：5/32局；完成峡谷：5局。
- 经礼拝堂到村后门：9/32局。
- 同一地点重来后再次死亡（仅作为循环候选，不能据此证明必死）：hero/102 @ goblin_fort_fourth, hero/104 @ goblin_fort_fourth, mage/20261013 @ goblin_fort_fourth, thief/20261013 @ goblin_fort_fourth, thief/103 @ goblin_fort_fourth

不变量分类：{"exceptions": 0, "noncombat_dead_ends": 0, "fallback_narrations": 0}

各职业实际路线覆盖：{"hero": {"village": 3, "battlefield": 3, "gorge": 0}, "cleric": {"village": 3, "battlefield": 3, "gorge": 2}, "mage": {"village": 2, "battlefield": 2, "gorge": 2}, "thief": {"village": 2, "battlefield": 2, "gorge": 1}}

## 通关局重合率

通关局19局。

|集合|配对数|均值|最小|最大|
|---|---:|---:|---:|---:|
|choices|171|0.3341|0.1429|0.8438|
|locations|171|0.5410|0.2879|0.9020|

## 线索覆盖

|flag|曾取得局数|最终保留局数|
|---|---:|---:|
|frost_trace_seen|10|9|
|has_assassin_crest|1|1|
|heard_gald_rumor|2|2|
|heard_guardian_refusal|18|18|
|heard_human_caused_dragon_return|16|16|
|heard_ignis_last_words|6|6|
|heard_ignis_testimony|5|5|
|heard_old_soldier_ghost|10|10|
|heard_pass_rumor|18|18|
|heard_treaty_lore|19|19|
|heard_xanxus_betrayal|16|16|
|noticed_general_frost|8|8|
|read_miner_diary|5|5|
|saw_white_claw|5|5|

## 从未到达的地点

- `merchant_battle`：夜の路地・亡霊戦
- `alley_after`：静まり返った夜の路地
- `cave_prism_tree`：虹晶樹の間
- `xanxus_phantom_battle`：Xanxusの分身

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
python -m scripts.playtest.explore --characters hero cleric mage thief --seeds 20261013 20261014 101 102 103 104 105 106 --steps 250 --output "eval/reports/playtest-2026-10-18-loot/summary.md"
```

剧本 SHA-256：

- dragon_rpg.json: `0092c020d4804752647f9c5eac0fb2595164059eeb01b5e93a645cbdf78e23ce`
- dragon_rpg_hybrid.json: `e43cc7a19a366f841b6855b10f4b0003a775b5f2e9854c5a49013616ea2b7d7e`
