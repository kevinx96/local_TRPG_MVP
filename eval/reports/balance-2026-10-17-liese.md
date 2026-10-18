# 033 リーゼ平衡评测

N=500／组合，seed=20261017；四职业；离线真实引擎、heuristic、有限背包、配对随机种子。
本次リーゼ：半血以下回复25%，否则2d3 holy；七种不死标签及统一holy抗性1.5。

## 口径与推断

- 古戦場三场各自从可达的森出口Lv2检查点开始，HP/MP/SP全满、无诅咒，不预取墓守外套，不执行潜行；独立强制战斗，避免只统计通关者的幸存偏差。
- HP损失=开战HP减战斗结束HP（最低0），包含死亡样本，结算奖励与自动移动前采样；这是净损失，包含职业/物品/同行者的回复。
- 城外复用既有逐战可达检查点与背包，逐战补满，不表示整章连续通关率；逐职业逐战比较胜率贡献。同行者强制切换以隔离效果，包含火コウモリ竜普通及虹晶强化两种状态。
- 不将Xanxus必败剧情战及替换玩家、禁用同行者的ワーロック救援算作普通比较。最终战采用draco_battle完整形态流程。
- 同一组合与对照共享初始随机种子；同行者会消耗不同随机数，不能解释为完全相同的逐次骰序列。经验胜率存在抽样误差，+3pp边界应结合样本量复核。

## 古戦場

|职业|战斗|无同行胜率|リーゼ胜率|提升pp|无同行HP损失|リーゼHP损失|损失降低|
|---|---|---:|---:|---:|---:|---:|---:|
|hero|bone_field|100.0%|100.0%|+0.0|7.58|4.40|41.9%|
|hero|ghoul_marsh|100.0%|100.0%|+0.0|5.09|3.53|30.6%|
|hero|grave_chapel|88.4%|100.0%|+11.6|12.22|8.30|32.1%|
|cleric|bone_field|99.4%|100.0%|+0.6|7.86|5.19|34.0%|
|cleric|ghoul_marsh|100.0%|100.0%|+0.0|5.97|4.27|28.5%|
|cleric|grave_chapel|70.6%|100.0%|+29.4|14.11|7.69|45.5%|
|mage|bone_field|100.0%|100.0%|+0.0|0.59|0.51|14.2%|
|mage|ghoul_marsh|100.0%|100.0%|+0.0|3.90|4.12|-5.6%|
|mage|grave_chapel|77.6%|94.0%|+16.4|6.45|2.50|61.2%|
|thief|bone_field|98.4%|99.6%|+1.2|6.60|4.46|32.4%|
|thief|ghoul_marsh|100.0%|100.0%|+0.0|4.76|3.33|30.0%|
|thief|grave_chapel|84.8%|100.0%|+15.2|8.02|3.81|52.4%|

三场合计平均净损失：

- hero: 8.30 → 5.41，降低34.8%。
- cleric: 9.32 → 5.72，降低38.6%。
- mage: 3.65 → 2.38，降低34.9%。
- thief: 6.46 → 3.87，降低40.1%。

## 城外（现有最强同行者 +3pp 上限）

|职业|战斗|无同行|リーゼ|现有最强|最强胜率|超出pp|
|---|---|---:|---:|---|---:|---:|
|hero|dark_forest_loc|100.0%|100.0%|robin|100.0%|+0.0|
|hero|lost_goblin_crossroads|100.0%|100.0%|robin|100.0%|+0.0|
|hero|forest_wolves|99.8%|100.0%|blue_robed_mage|100.0%|+0.0|
|hero|slime_ambush_one|100.0%|100.0%|robin|100.0%|+0.0|
|hero|slime_ambush_two|100.0%|100.0%|robin|100.0%|+0.0|
|hero|slime_king_battle|92.8%|98.8%|fire_bat_dragon|100.0%|-1.2|
|hero|goblin_fort|100.0%|100.0%|robin|100.0%|+0.0|
|hero|goblin_fort_first_second|100.0%|100.0%|robin|100.0%|+0.0|
|hero|goblin_fort_second_right|100.0%|100.0%|robin|100.0%|+0.0|
|hero|goblin_fort_second_left|95.6%|99.4%|fire_bat_dragon|100.0%|-0.6|
|hero|goblin_fort_third_guards|100.0%|100.0%|robin|100.0%|+0.0|
|hero|goblin_fort_fourth|73.6%|76.4%|robin|87.2%|-10.8|
|hero|goblin_fort_chest_fight|100.0%|100.0%|robin|100.0%|+0.0|
|hero|cave_heat_corridor|70.4%|93.2%|fire_bat_empowered|95.4%|-2.2|
|hero|cave_lava_room|77.8%|94.0%|fire_bat_empowered|98.2%|-4.2|
|hero|cave_crystal_corridor|51.0%|87.8%|fire_bat_empowered|96.6%|-8.8|
|hero|cave_prism_tree|17.8%|83.2%|fire_bat_empowered|100.0%|-16.8|
|hero|village_fire_slime|100.0%|100.0%|robin|100.0%|+0.0|
|hero|village_fire_elemental|99.4%|100.0%|robin|100.0%|+0.0|
|hero|ice_elemental_encounter|100.0%|100.0%|robin|100.0%|+0.0|
|hero|frost_wolf_battle|100.0%|100.0%|robin|100.0%|+0.0|
|hero|valley_entrance|85.2%|98.6%|robin|97.4%|+1.2|
|hero|valley_ledge|80.0%|87.0%|robin|89.0%|-2.0|
|hero|xanxus_phantom_battle|74.8%|94.6%|fire_bat_empowered|93.2%|+1.4|
|hero|dragon_valley_loc|90.0%|95.6%|fire_bat_empowered|97.8%|-2.2|
|hero|draco_battle|58.2%|64.6%|fire_bat_empowered|89.6%|-25.0|
|cleric|dark_forest_loc|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|lost_goblin_crossroads|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|forest_wolves|92.4%|99.6%|robin|100.0%|-0.4|
|cleric|slime_ambush_one|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|slime_ambush_two|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|slime_king_battle|70.2%|89.4%|fire_bat_empowered|100.0%|-10.6|
|cleric|goblin_fort|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|goblin_fort_first_second|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|goblin_fort_second_right|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|goblin_fort_second_left|70.0%|83.4%|fire_bat_empowered|99.8%|-16.4|
|cleric|goblin_fort_third_guards|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|goblin_fort_fourth|54.0%|65.4%|robin|81.6%|-16.2|
|cleric|goblin_fort_chest_fight|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|cave_heat_corridor|84.0%|96.8%|fire_bat_empowered|98.0%|-1.2|
|cleric|cave_lava_room|85.6%|90.8%|fire_bat_empowered|95.2%|-4.4|
|cleric|cave_crystal_corridor|73.2%|93.6%|fire_bat_empowered|93.4%|+0.2|
|cleric|cave_prism_tree|58.0%|78.2%|fire_bat_empowered|100.0%|-21.8|
|cleric|village_fire_slime|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|village_fire_elemental|94.6%|99.6%|robin|99.8%|-0.2|
|cleric|ice_elemental_encounter|99.8%|100.0%|robin|100.0%|+0.0|
|cleric|frost_wolf_battle|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|valley_entrance|83.6%|97.6%|robin|97.4%|+0.2|
|cleric|valley_ledge|79.4%|85.0%|robin|86.2%|-1.2|
|cleric|xanxus_phantom_battle|54.6%|87.6%|fire_bat_empowered|86.2%|+1.4|
|cleric|dragon_valley_loc|79.2%|89.0%|fire_bat_empowered|95.0%|-6.0|
|cleric|draco_battle|59.0%|62.2%|fire_bat_empowered|86.4%|-24.2|
|mage|dark_forest_loc|98.4%|100.0%|robin|100.0%|+0.0|
|mage|lost_goblin_crossroads|100.0%|100.0%|robin|100.0%|+0.0|
|mage|forest_wolves|94.0%|99.0%|robin|99.4%|-0.4|
|mage|slime_ambush_one|99.4%|99.8%|fire_bat_dragon|100.0%|-0.2|
|mage|slime_ambush_two|99.0%|100.0%|robin|100.0%|+0.0|
|mage|slime_king_battle|69.2%|63.8%|fire_bat_empowered|93.4%|-29.6|
|mage|goblin_fort|100.0%|100.0%|robin|100.0%|+0.0|
|mage|goblin_fort_first_second|98.4%|99.4%|robin|100.0%|-0.6|
|mage|goblin_fort_second_right|100.0%|100.0%|robin|100.0%|+0.0|
|mage|goblin_fort_second_left|77.6%|85.6%|fire_bat_empowered|97.4%|-11.8|
|mage|goblin_fort_third_guards|100.0%|100.0%|robin|100.0%|+0.0|
|mage|goblin_fort_fourth|63.0%|63.4%|robin|97.4%|-34.0|
|mage|goblin_fort_chest_fight|100.0%|100.0%|robin|100.0%|+0.0|
|mage|cave_heat_corridor|84.6%|93.0%|fire_bat_empowered|95.4%|-2.4|
|mage|cave_lava_room|81.4%|87.6%|fire_bat_empowered|93.6%|-6.0|
|mage|cave_crystal_corridor|66.4%|72.6%|fire_bat_empowered|89.8%|-17.2|
|mage|cave_prism_tree|42.6%|41.0%|fire_bat_empowered|84.2%|-43.2|
|mage|village_fire_slime|100.0%|100.0%|robin|100.0%|+0.0|
|mage|village_fire_elemental|88.2%|96.4%|robin|99.2%|-2.8|
|mage|ice_elemental_encounter|99.2%|99.6%|robin|100.0%|-0.4|
|mage|frost_wolf_battle|100.0%|100.0%|robin|100.0%|+0.0|
|mage|valley_entrance|84.0%|98.0%|robin|97.4%|+0.6|
|mage|valley_ledge|78.0%|79.8%|robin|82.0%|-2.2|
|mage|xanxus_phantom_battle|57.8%|78.6%|fire_bat_empowered|83.6%|-5.0|
|mage|dragon_valley_loc|69.4%|67.2%|fire_bat_empowered|79.2%|-12.0|
|mage|draco_battle|70.6%|68.0%|fire_bat_empowered|74.8%|-6.8|
|thief|dark_forest_loc|99.6%|100.0%|robin|100.0%|+0.0|
|thief|lost_goblin_crossroads|100.0%|100.0%|robin|100.0%|+0.0|
|thief|forest_wolves|97.6%|98.6%|robin|99.6%|-1.0|
|thief|slime_ambush_one|99.8%|100.0%|robin|100.0%|+0.0|
|thief|slime_ambush_two|99.6%|100.0%|robin|100.0%|+0.0|
|thief|slime_king_battle|70.6%|89.2%|fire_bat_empowered|100.0%|-10.8|
|thief|goblin_fort|100.0%|100.0%|robin|100.0%|+0.0|
|thief|goblin_fort_first_second|99.4%|99.8%|robin|100.0%|-0.2|
|thief|goblin_fort_second_right|100.0%|100.0%|robin|100.0%|+0.0|
|thief|goblin_fort_second_left|70.6%|87.0%|fire_bat_empowered|100.0%|-13.0|
|thief|goblin_fort_third_guards|100.0%|100.0%|robin|100.0%|+0.0|
|thief|goblin_fort_fourth|69.8%|78.0%|robin|84.8%|-6.8|
|thief|goblin_fort_chest_fight|100.0%|100.0%|robin|100.0%|+0.0|
|thief|cave_heat_corridor|64.8%|85.8%|fire_bat_empowered|92.8%|-7.0|
|thief|cave_lava_room|79.6%|87.8%|fire_bat_empowered|96.0%|-8.2|
|thief|cave_crystal_corridor|69.4%|82.0%|fire_bat_empowered|93.4%|-11.4|
|thief|cave_prism_tree|38.2%|54.6%|fire_bat_empowered|97.0%|-42.4|
|thief|village_fire_slime|100.0%|100.0%|robin|100.0%|+0.0|
|thief|village_fire_elemental|74.4%|89.4%|robin|92.6%|-3.2|
|thief|ice_elemental_encounter|91.8%|98.8%|fire_bat_empowered|100.0%|-1.2|
|thief|frost_wolf_battle|100.0%|100.0%|robin|100.0%|+0.0|
|thief|valley_entrance|85.2%|98.0%|robin|97.0%|+1.0|
|thief|valley_ledge|78.4%|87.6%|robin|87.4%|+0.2|
|thief|xanxus_phantom_battle|66.8%|86.6%|fire_bat_empowered|91.4%|-4.8|
|thief|dragon_valley_loc|77.6%|88.8%|fire_bat_empowered|92.4%|-3.6|
|thief|draco_battle|65.0%|69.2%|fire_bat_empowered|84.0%|-14.8|

## 未达标与设计待办

全部可计算目标通过；基准零HP损失的单场无法计算相对降幅。

只调リーゼ自己的回复比例与伤害骰；未改现有敌人（不死标签及holy统一除外）或其他同行者数值。原始每组统计见同名JSON。
调参过程与候选比较见 [调参记录](balance-2026-10-17-liese-tuning.md)。

## 复现

```powershell
python -m scripts.balance.liese --n 500 --seed 20261017
```

指纹：

- scripts\balance\liese.py: `a82f8680a353f07384ca41257d1880d9bae20798d129cc92d9ec1e7e0505fffb`
- host\prompt\processed\dragon_rpg.json: `2e50142ec0692038bd0a3c5fa92f53be10ba32c5ff60272577616337b97099da`
- host\combat.py: `3a6eda0c623a4edaedbad2e9e2f087917c6e70b488386f0a9dccdd5c89ec6609`
