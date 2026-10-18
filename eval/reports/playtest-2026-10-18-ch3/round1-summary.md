# 离线试玩回归（summary）

32局，职业：hero, cleric, mage, thief；种子：20261013, 20261014, 101, 102, 103, 104, 105, 106；每局最多250步。战斗每个指令和结算各占一步。
首次战斗死亡后重来一次，选择次数及随机流继续累计。选项、判定和战斗的随机数均固定。
首次死亡包含剧情导致的死亡结局；剧情必败但仍能继续的战斗不计死亡，冒険完了也不计死亡。
037：按种子列表顺序轮换村／古戦場／峡谷优先度；村优先种子如从洞窟先到城塞，则从古戦場入口返回森林出口走村。古戦場和峡谷保留现行城塞访问、招募与路线内策略，其余仍按选项使用次数、章节推进偏好及固定随机数选择。
实际路线以village_approach／bone_field／gorge_entrance首次进入为准，old_battlefield仅作为城塞通道时不算走古戦場。重来分别记attempt，同行者记录路线入口和全程变化，不以最终同行者代替。
线索flag从凱旋の間告发条件与既有mystery任务读取；曾取得与最终保留分别统计。选择重合率只取实际剧本选项的（地点ID、选项ID）集合，排除无判定、无一次性标记且效果只有移动/背景的纯移动；不含战斗指令。
通关以剧本的冒険完了结局为准。Jaccard取所有通关局的无序两两组合，包含同一局重来前的经历；没有足够通关局时返回null。空集合对定义为1。
LLM 配置指向 127.0.0.1:1，并在请求适配器直接模拟连接失败；禁止真实网络。

|职业|种子|首次死亡|重来次数|结局|步数|第三章路线（入口同行者）|线索flag|
|---|---:|---|---:|---|---:|---|---|
|hero|20261013|无|0|draco_defeated_with_ignis @ draco_battle|123|village (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_ignis_testimony, heard_pass_rumor, heard_xanxus_betrayal, noticed_general_frost|
|hero|20261014|ice_elemental_encounter|1|ignis_defeated @ castle_report|227|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, noticed_general_frost|
|hero|101|valley_ledge|1|draco_defeated @ draco_battle|159|gorge (hydromancer_elio, attempt 0)|heard_guardian_refusal, heard_ignis_last_words, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost, read_miner_diary, saw_white_claw|
|hero|102|xanxus_ultimatum|0|defied_xanxus @ xanxus_ultimatum|64|village (robin, attempt 0)|heard_treaty_lore|
|hero|103|xanxus_ultimatum|0|defied_xanxus @ xanxus_ultimatum|121|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore|
|hero|104|goblin_fort_fourth|1|ignis_defeated @ castle_report|170|gorge (hydromancer_elio, attempt 1)|frost_trace_seen, heard_guardian_refusal, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, read_miner_diary, saw_white_claw|
|hero|105|village_fire_elemental|1|ignis_defeated @ castle_report|163|village (none, attempt 0); village (none, attempt 1); battlefield (paladin_liese, attempt 1)|frost_trace_seen, heard_gald_rumor, heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_last_words, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, noticed_general_frost|
|hero|106|无|0|draco_defeated @ draco_battle|164|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_last_words, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|cleric|20261013|draco_battle|1|ignis_purified @ castle_report|146|village (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_pass_rumor, heard_treaty_lore, noticed_general_frost|
|cleric|20261014|draco_battle|1|ignis_purified @ castle_report|191|battlefield (paladin_liese, attempt 0); village (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, noticed_general_frost|
|cleric|101|无|0|ignis_purified @ castle_report|177|gorge (hydromancer_elio, attempt 0)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost, read_miner_diary, saw_white_claw|
|cleric|102|xanxus_ultimatum|0|defied_xanxus @ xanxus_ultimatum|77|village (fire_bat_dragon, attempt 0)|frost_trace_seen, heard_treaty_lore|
|cleric|103|无|0|ignis_purified @ castle_report|136|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_ignis_testimony, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|cleric|104|draco_battle|1|ignis_purified @ castle_report|215|gorge (hydromancer_elio, attempt 0)|has_assassin_crest, heard_guardian_refusal, heard_human_caused_dragon_return, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, read_miner_diary, saw_white_claw|
|cleric|105|无|0|ignis_purified @ castle_report|81|village (robin, attempt 0)|heard_human_caused_dragon_return, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost|
|cleric|106|draco_battle|1|ignis_purified @ castle_report|206|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_testimony, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal|
|mage|20261013|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|86|未到达|heard_human_caused_dragon_return|
|mage|20261014|lost_goblin_crossroads|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|75|未到达|heard_human_caused_dragon_return, heard_treaty_lore|
|mage|101|goblin_fort_second_left|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|68|未到达|heard_human_caused_dragon_return, heard_treaty_lore|
|mage|102|xanxus_ultimatum|0|defied_xanxus @ xanxus_ultimatum|78|village (paladin_liese, attempt 0)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_pass_rumor|
|mage|103|slime_king_battle|1|defied_xanxus @ xanxus_ultimatum|88|battlefield (paladin_liese, attempt 1)|heard_guardian_refusal, heard_old_soldier_ghost, heard_pass_rumor|
|mage|104|goblin_fort_fourth|1|slime_king_battle_defeat @ slime_king_battle|74|未到达|无|
|mage|105|无|0|ignis_defeated @ castle_report|85|village (none, attempt 0)|frost_trace_seen, heard_ignis_last_words, heard_xanxus_betrayal|
|mage|106|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|56|未到达|heard_human_caused_dragon_return|
|thief|20261013|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|95|未到达|heard_human_caused_dragon_return|
|thief|20261014|grave_chapel|1|combat_defeat @ grave_chapel|115|battlefield (paladin_liese, attempt 0); battlefield (paladin_liese, attempt 1)|heard_guardian_refusal, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore|
|thief|101|goblin_fort_second_left|1|draco_victory @ draco_battle|206|gorge (hydromancer_elio, attempt 1)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_pass_rumor, heard_treaty_lore, read_miner_diary, saw_white_claw|
|thief|102|xanxus_ultimatum|0|defied_xanxus @ xanxus_ultimatum|87|village (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_pass_rumor|
|thief|103|goblin_fort_fourth|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|66|未到达|无|
|thief|104|goblin_fort_second_left|1|draco_victory @ draco_battle|137|gorge (hydromancer_elio, attempt 1)|heard_guardian_refusal, heard_ignis_last_words, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, read_miner_diary, saw_white_claw|
|thief|105|无|0|ignis_defeated @ castle_report|116|village (none, attempt 0)|frost_trace_seen, heard_gald_rumor, heard_ignis_last_words, heard_treaty_lore, heard_xanxus_betrayal|
|thief|106|goblin_fort_second_left|1|defied_xanxus @ xanxus_ultimatum|144|battlefield (paladin_liese, attempt 1); village (paladin_liese, attempt 1)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_old_soldier_ghost, heard_pass_rumor|

最远地点口径：按主线章节、地图节点顺序取最大值；砦/洞窟归森林章、屋敷归王城归还章。同级支线没有唯一剧情顺序，完整到访记录见逐步日志。

最终分布：{"draco_defeated_with_ignis": 1, "ignis_defeated": 5, "draco_defeated": 2, "defied_xanxus": 7, "ignis_purified": 7, "goblin_fort_fourth_defeat": 6, "slime_king_battle_defeat": 1, "combat_defeat": 1, "draco_victory": 2}

首次死亡地点：{"ice_elemental_encounter": 1, "valley_ledge": 1, "xanxus_ultimatum": 5, "goblin_fort_fourth": 6, "village_fire_elemental": 1, "draco_battle": 4, "lost_goblin_crossroads": 1, "goblin_fort_second_left": 4, "slime_king_battle": 1, "grave_chapel": 1}

重来后分布：{"ignis_defeated": 3, "draco_defeated": 1, "ignis_purified": 4, "goblin_fort_fourth_defeat": 6, "defied_xanxus": 2, "slime_king_battle_defeat": 1, "combat_defeat": 1, "draco_victory": 2}

## 不变量检查

- 异常、非战斗死路及兜底叙述：0 项。
- 古戦場到访：16/32局。
- 城塞到访：20/32局。
- 峡谷到访：6/32局；完成峡谷：6局。
- 经礼拝堂到村后门：9/32局。
- 同一地点重来后再次死亡（仅作为循环候选，不能据此证明必死）：mage/20261013 @ goblin_fort_fourth, mage/106 @ goblin_fort_fourth, thief/20261013 @ goblin_fort_fourth, thief/20261014 @ grave_chapel, thief/103 @ goblin_fort_fourth

不变量分类：{"exceptions": 0, "noncombat_dead_ends": 0, "fallback_narrations": 0}

## 通关局重合率

通关局15局。

|集合|配对数|均值|最小|最大|
|---|---:|---:|---:|---:|
|choices|105|0.3853|0.2000|0.6912|
|locations|105|0.5578|0.3182|0.9737|

## 线索覆盖

|flag|曾取得局数|最终保留局数|
|---|---:|---:|
|frost_trace_seen|14|14|
|has_assassin_crest|1|1|
|heard_gald_rumor|2|2|
|heard_guardian_refusal|20|20|
|heard_human_caused_dragon_return|17|16|
|heard_ignis_last_words|6|6|
|heard_ignis_testimony|3|3|
|heard_old_soldier_ghost|10|10|
|heard_pass_rumor|20|20|
|heard_treaty_lore|21|21|
|heard_xanxus_betrayal|12|12|
|noticed_general_frost|8|8|
|read_miner_diary|6|6|
|saw_white_claw|6|6|

## 从未到达的地点

- `merchant_battle`：夜の路地・亡霊戦
- `alley_after`：静まり返った夜の路地
- `xanxus_phantom_battle`：Xanxusの分身

## 逐步记录

第一轮32份日志保存在提交 `b7090fc` 的 `eval/reports/playtest-2026-10-18-ch3/logs/`；当前同名日志为第二轮重跑结果。第一轮逐局统计完整保留在 [round1-summary.json](round1-summary.json)。

## 复现

```powershell
python -m scripts.playtest.explore --characters hero cleric mage thief --seeds 20261013 20261014 101 102 103 104 105 106 --steps 250 --output "D:/TRPG_Game/eval/reports/playtest-2026-10-18-ch3/summary.md"
```

剧本 SHA-256：

- dragon_rpg.json: `ceffa2d78acfb80c267741aa742f2c14340e7e1dde503c67665609e9d6ed0d5a`
- dragon_rpg_hybrid.json: `7be2601b7f75bd07ba7b631ea2832a8d32307791d1f4cfd426a917f3f1ddb363`
