# 离线试玩回归（summary）

12局，职业：hero, cleric, mage, thief；种子：20261013, 20261014, 102；每局最多330步。战斗每个指令和结算各占一步。
首次战斗死亡后重来一次，选择次数及随机流继续累计。选项、判定和战斗的随机数均固定。
首次死亡包含剧情导致的死亡结局；剧情必败但仍能继续的战斗不计死亡，冒険完了也不计死亡。
037第二轮：路线轮换使用20261013、20261014、102、101、103、104、105、106的顺序，循环村／古戦場／峡谷；仅交换101与102的优先路线，让第一轮能到达第三章的魔法使い/102走峡谷。运行仍按原种子列表，子集映射固定。村优先种子如从洞窟先到城塞，则从古戦場入口返回森林出口走村。古戦場和峡谷保留现行城塞访问、招募与路线内策略，其余仍按选项使用次数、章节推进偏好及固定随机数选择。
实际路线以village_approach／bone_field／gorge_entrance首次进入为准，old_battlefield仅作为城塞通道时不算走古戦場。重来分别记attempt，同行者记录路线入口和全程变化，不以最终同行者代替。
线索flag从凱旋の間告发条件与既有mystery任务读取；曾取得与最终保留分别统计。选择重合率只取实际剧本选项的（地点ID、选项ID）集合，排除无判定、无一次性标记且效果只有移动/背景的纯移动；不含战斗指令。
通关以剧本的冒険完了结局为准。Jaccard取所有通关局的无序两两组合，包含同一局重来前的经历；没有足够通关局时返回null。空集合对定义为1。
LLM 配置指向 127.0.0.1:1，并在请求适配器直接模拟连接失败；禁止真实网络。

|职业|种子|首次死亡|重来次数|结局|步数|第三章路线（入口同行者）|线索flag|
|---|---:|---|---:|---|---:|---|---|
|hero|20261013|valley_ledge|1|dragon_valley_defeat @ dragon_valley_loc|108|village (none, attempt 0)|frost_trace_seen, heard_human_caused_dragon_return, heard_xanxus_betrayal, noticed_general_frost|
|hero|20261014|grave_chapel|1|draco_victory @ draco_battle|177|battlefield (paladin_liese, attempt 0); battlefield (paladin_liese, attempt 1)|heard_guardian_refusal, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, noticed_general_frost|
|hero|102|valley_ledge|1|ignis_purified @ castle_report|130|gorge (hydromancer_elio, attempt 0)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, read_miner_diary, saw_white_claw|
|cleric|20261013|draco_battle|1|ignis_purified @ castle_report|157|village (fire_bat_dragon, attempt 0)|frost_trace_seen, has_assassin_crest, heard_human_caused_dragon_return, heard_treaty_lore, heard_xanxus_betrayal, noticed_general_frost|
|cleric|20261014|valley_entrance|1|ignis_purified @ castle_report|167|battlefield (paladin_liese, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_ignis_testimony, heard_old_soldier_ghost, heard_pass_rumor, heard_treaty_lore, noticed_general_frost|
|cleric|102|ice_elemental_encounter|1|dragon_valley_defeat @ valley_ledge|103|gorge (hydromancer_elio, attempt 0)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_pass_rumor, heard_treaty_lore, noticed_general_frost, read_miner_diary, saw_white_claw|
|mage|20261013|slime_ambush_two|1|slime_king_battle_defeat @ slime_king_battle|73|未到达|heard_human_caused_dragon_return|
|mage|20261014|slime_king_battle|1|goblin_fort_fourth_defeat @ goblin_fort_fourth|76|未到达|heard_human_caused_dragon_return|
|mage|102|无|0|draco_defeated @ draco_battle|124|gorge (hydromancer_elio, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_last_words, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, read_miner_diary, saw_white_claw|
|thief|20261013|ice_elemental_encounter|1|dragon_valley_defeat @ dragon_valley_loc|118|village (none, attempt 0); village (none, attempt 1)|frost_trace_seen, heard_human_caused_dragon_return, heard_xanxus_betrayal|
|thief|20261014|无|0|draco_defeated @ draco_battle|140|battlefield (paladin_liese, attempt 0)|heard_guardian_refusal, heard_human_caused_dragon_return, heard_ignis_last_words, heard_old_soldier_ghost, heard_pass_rumor, heard_xanxus_betrayal|
|thief|102|dragon_valley_loc|1|draco_victory @ draco_battle|148|gorge (hydromancer_elio, attempt 0)|frost_trace_seen, heard_guardian_refusal, heard_human_caused_dragon_return, heard_pass_rumor, heard_treaty_lore, heard_xanxus_betrayal, read_miner_diary, saw_white_claw|

最远地点口径：按主线章节、地图节点顺序取最大值；砦/洞窟归森林章、屋敷归王城归还章。同级支线没有唯一剧情顺序，完整到访记录见逐步日志。

最终分布：{"dragon_valley_defeat": 3, "draco_victory": 2, "ignis_purified": 3, "slime_king_battle_defeat": 1, "goblin_fort_fourth_defeat": 1, "draco_defeated": 2}

首次死亡地点：{"valley_ledge": 2, "grave_chapel": 1, "draco_battle": 1, "valley_entrance": 1, "ice_elemental_encounter": 2, "slime_ambush_two": 1, "slime_king_battle": 1, "dragon_valley_loc": 1}

重来后分布：{"dragon_valley_defeat": 3, "draco_victory": 2, "ignis_purified": 3, "slime_king_battle_defeat": 1, "goblin_fort_fourth_defeat": 1}

## 不变量检查

- 异常、非战斗死路及兜底叙述：0 项。
- 古戦場到访：6/12局。
- 城塞到访：7/12局。
- 峡谷到访：4/12局；完成峡谷：4局。
- 经礼拝堂到村后门：3/12局。
- 同一地点重来后再次死亡（仅作为循环候选，不能据此证明必死）：

不变量分类：{"exceptions": 0, "noncombat_dead_ends": 0, "fallback_narrations": 0}

各职业实际路线覆盖：{"hero": {"village": 1, "battlefield": 1, "gorge": 1}, "cleric": {"village": 1, "battlefield": 1, "gorge": 1}, "mage": {"village": 0, "battlefield": 0, "gorge": 1}, "thief": {"village": 1, "battlefield": 1, "gorge": 1}}

## 通关局重合率

通关局5局。

|集合|配对数|均值|最小|最大|
|---|---:|---:|---:|---:|
|choices|10|0.3323|0.2812|0.4471|
|locations|10|0.5148|0.4242|0.5806|

## 线索覆盖

|flag|曾取得局数|最终保留局数|
|---|---:|---:|
|frost_trace_seen|6|5|
|has_assassin_crest|1|1|
|heard_gald_rumor|0|0|
|heard_guardian_refusal|7|7|
|heard_human_caused_dragon_return|10|10|
|heard_ignis_last_words|2|2|
|heard_ignis_testimony|1|1|
|heard_old_soldier_ghost|3|3|
|heard_pass_rumor|7|7|
|heard_treaty_lore|7|7|
|heard_xanxus_betrayal|7|7|
|noticed_general_frost|5|5|
|read_miner_diary|4|4|
|saw_white_claw|4|4|

## 从未到达的地点

- `merchant_battle`：夜の路地・亡霊戦
- `alley_after`：静まり返った夜の路地
- `goblin_fort_chest_fight`：ゴブリン砦・箱の争奪
- `village_fire_slime`：炎上する麓の村・ファイアスライム戦
- `cave_crystal_corridor`：水晶の回廊
- `cave_prism_tree`：虹晶樹の間
- `dragon_valley_return`：竜の谷・帰路

## 逐步记录

- [hero-20261013.md](logs/hero-20261013.md)
- [hero-20261014.md](logs/hero-20261014.md)
- [hero-102.md](logs/hero-102.md)
- [cleric-20261013.md](logs/cleric-20261013.md)
- [cleric-20261014.md](logs/cleric-20261014.md)
- [cleric-102.md](logs/cleric-102.md)
- [mage-20261013.md](logs/mage-20261013.md)
- [mage-20261014.md](logs/mage-20261014.md)
- [mage-102.md](logs/mage-102.md)
- [thief-20261013.md](logs/thief-20261013.md)
- [thief-20261014.md](logs/thief-20261014.md)
- [thief-102.md](logs/thief-102.md)

## 复现

```powershell
python -m scripts.playtest.explore --characters hero cleric mage thief --seeds 20261013 20261014 102 --steps 330 --output "eval/reports/041-playtest/summary.md"
```

剧本 SHA-256：

- dragon_rpg.json: `9c042cf5e4c7eff0a3a7b430d01c03002e0fb37cc853adf99c0d7fa01eacb56f`
- dragon_rpg_hybrid.json: `1b305ee971b17df94967fe3cabe710a1cf9d9521a03b44aab7ca5eacefbbf3b4`
