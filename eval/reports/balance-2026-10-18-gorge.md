# 035 峡谷与エリオ平衡（2026-10-18）

独立战斗与经济N=500／组合，连续路线N=5000／组合，seed=20261018；四职业、真实确定性引擎、有限背包、heuristic，完全离线。

## 口径与推断

- 起点复用031的森の出口可达Lv2检查点（森林前战按胜利回放、永久品已使用、HP/MP/SP补满）。不预取城塞装备，不带其他同行者。
- 峡谷连续路线：三处潜行使用真实d20；失败立即实战，巨人/ワーム失败敌先手；第一战后营地搜寻并全恢复一次；偷取/战胜巨人共用果实标记，果实立即使用；资源与消耗品跨战继承。到village即成功。
- 村庄沿用031比较路线：慎重接近→实际判定与分支战→离开民家→village_frozen_clue；不救人。两条路线终点依spec，后续村庄内容不纳入。
- エリオ三场战斗从同一满资源检查点分别强制开战；不计其无战绕过。HP损失为开战HP减战后HP、最低0，含败北样本与治疗，避免只看胜者。
- 峡谷外逐职业逐场比较现有所有同行者，含强化火コウモリ竜和リーゼ；使用现有逐战检查点，古戦場使用同一森出口，不携带诅咒。屋敷/宿袭沿用031的最终战前检查点，商人战使用原商人检查点。自动枚举32场遭遇，仅排除必败剧情和禁用同行者的救援战。
- 配对初始种子，但同行者消耗骰序不同。经验胜率存在抽样误差，边界不能解释为精确总体概率。
- 物理普攻沿用岩石系红宝石魔像的既有方式；新敌人本体为earth，物理抗性0.6、水弱点1.5。

## 连续路线

|职业|村庄|峡谷无エリオ|差pp|峡谷带エリオ|
|---|---:|---:|---:|---:|
|hero|95.8%|99.5%|+3.7|100.0%|
|cleric|96.6%|96.2%|-0.4|99.4%|
|mage|96.2%|96.0%|-0.3|99.3%|
|thief|89.8%|99.3%|+9.5|99.9%|

## 峡谷独立战斗

|职业|战斗|无同行胜率|エリオ胜率|无同行HP损失|エリオHP损失|
|---|---|---:|---:|---:|---:|
|hero|gorge_rockfall_path|100.0%|100.0%|9.39|5.84|
|hero|gorge_giant_path|100.0%|100.0%|9.49|7.75|
|hero|gorge_worm_lair|100.0%|100.0%|8.95|4.90|

hero三场平均HP净损失 9.28 → 6.16；降低33.6%；Boss提升+0.0pp。

|cleric|gorge_rockfall_path|97.2%|100.0%|9.21|8.53|
|cleric|gorge_giant_path|98.4%|99.4%|9.24|9.14|
|cleric|gorge_worm_lair|100.0%|100.0%|8.56|5.26|

cleric三场平均HP净损失 9.00 → 7.64；降低15.1%；Boss提升+0.0pp。

cleric：HP损失降幅未达30%；无同行Boss胜率已为100%，按spec第6节的上限例外处理。

|mage|gorge_rockfall_path|100.0%|100.0%|1.45|1.19|
|mage|gorge_giant_path|99.6%|100.0%|4.06|2.44|
|mage|gorge_worm_lair|100.0%|100.0%|4.43|4.19|

mage三场平均HP净损失 3.31 → 2.61；降低21.3%；Boss提升+0.0pp。

mage：HP损失降幅未达30%；无同行Boss胜率已为100%，按spec第6节的上限例外处理。

|thief|gorge_rockfall_path|94.4%|99.0%|7.86|6.88|
|thief|gorge_giant_path|95.2%|99.8%|7.82|7.45|
|thief|gorge_worm_lair|100.0%|100.0%|5.65|2.06|

thief三场平均HP净损失 7.11 → 5.46；降低23.2%；Boss提升+0.0pp。

thief：HP损失降幅未达30%；无同行Boss胜率已为100%，按spec第6节的上限例外处理。


## 峡谷外

|职业|遭遇|无同行|エリオ|现有最强|最强胜率|超出pp|
|---|---|---:|---:|---|---:|---:|
|hero|dragon_valley_loc|88.8%|93.0%|fire_bat_empowered|97.4%|-4.4|
|cleric|dragon_valley_loc|79.4%|87.0%|fire_bat_empowered|95.0%|-8.0|
|mage|dragon_valley_loc|71.6%|80.2%|fire_bat_empowered|77.6%|+2.6|
|thief|dragon_valley_loc|77.2%|86.4%|fire_bat_empowered|91.6%|-5.2|
|hero|merchant_battle|72.2%|55.4%|blue_robed_mage|72.6%|-17.2|
|cleric|merchant_battle|76.6%|70.4%|fire_bat_empowered|91.2%|-20.8|
|mage|merchant_battle|69.4%|67.6%|paladin_liese|71.0%|-3.4|
|thief|merchant_battle|68.2%|59.0%|paladin_liese|71.4%|-12.4|
|hero|dark_forest_loc|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|dark_forest_loc|100.0%|100.0%|robin|100.0%|+0.0|
|mage|dark_forest_loc|98.8%|99.8%|fire_bat_dragon|100.0%|-0.2|
|thief|dark_forest_loc|99.8%|100.0%|robin|100.0%|+0.0|
|hero|lost_goblin_crossroads|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|lost_goblin_crossroads|100.0%|100.0%|robin|100.0%|+0.0|
|mage|lost_goblin_crossroads|100.0%|100.0%|robin|100.0%|+0.0|
|thief|lost_goblin_crossroads|100.0%|100.0%|robin|100.0%|+0.0|
|hero|forest_wolves|99.6%|99.4%|robin|100.0%|-0.6|
|cleric|forest_wolves|95.6%|99.2%|fire_bat_dragon|100.0%|-0.8|
|mage|forest_wolves|94.8%|98.6%|robin|99.4%|-0.8|
|thief|forest_wolves|96.8%|99.2%|fire_bat_empowered|99.8%|-0.6|
|hero|slime_ambush_one|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|slime_ambush_one|100.0%|100.0%|robin|100.0%|+0.0|
|mage|slime_ambush_one|98.4%|99.6%|fire_bat_dragon|100.0%|-0.4|
|thief|slime_ambush_one|99.6%|99.8%|robin|100.0%|-0.2|
|hero|slime_ambush_two|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|slime_ambush_two|100.0%|100.0%|robin|100.0%|+0.0|
|mage|slime_ambush_two|97.8%|99.8%|robin|100.0%|-0.2|
|thief|slime_ambush_two|99.2%|100.0%|robin|100.0%|+0.0|
|hero|slime_king_battle|92.2%|99.8%|fire_bat_empowered|100.0%|-0.2|
|cleric|slime_king_battle|70.6%|96.2%|fire_bat_empowered|100.0%|-3.8|
|mage|slime_king_battle|63.8%|70.8%|fire_bat_empowered|95.4%|-24.6|
|thief|slime_king_battle|67.4%|97.2%|fire_bat_empowered|100.0%|-2.8|
|hero|goblin_fort|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|goblin_fort|100.0%|100.0%|robin|100.0%|+0.0|
|mage|goblin_fort|100.0%|100.0%|robin|100.0%|+0.0|
|thief|goblin_fort|100.0%|100.0%|robin|100.0%|+0.0|
|hero|goblin_fort_first_second|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|goblin_fort_first_second|99.8%|100.0%|robin|100.0%|+0.0|
|mage|goblin_fort_first_second|99.2%|99.0%|fire_bat_dragon|99.6%|-0.6|
|thief|goblin_fort_first_second|99.2%|99.8%|robin|100.0%|-0.2|
|hero|goblin_fort_second_right|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|goblin_fort_second_right|100.0%|100.0%|robin|100.0%|+0.0|
|mage|goblin_fort_second_right|100.0%|99.8%|blue_robed_mage|100.0%|-0.2|
|thief|goblin_fort_second_right|100.0%|100.0%|robin|100.0%|+0.0|
|hero|goblin_fort_second_left|95.8%|98.8%|fire_bat_dragon|100.0%|-1.2|
|cleric|goblin_fort_second_left|71.4%|90.2%|fire_bat_empowered|98.8%|-8.6|
|mage|goblin_fort_second_left|84.4%|91.8%|fire_bat_empowered|98.4%|-6.6|
|thief|goblin_fort_second_left|74.4%|86.2%|fire_bat_empowered|100.0%|-13.8|
|hero|goblin_fort_third_guards|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|goblin_fort_third_guards|100.0%|100.0%|robin|100.0%|+0.0|
|mage|goblin_fort_third_guards|100.0%|100.0%|robin|100.0%|+0.0|
|thief|goblin_fort_third_guards|100.0%|100.0%|robin|100.0%|+0.0|
|hero|goblin_fort_fourth|68.0%|73.0%|robin|85.2%|-12.2|
|cleric|goblin_fort_fourth|52.6%|58.8%|robin|77.6%|-18.8|
|mage|goblin_fort_fourth|64.2%|63.4%|robin|97.0%|-33.6|
|thief|goblin_fort_fourth|71.2%|71.2%|robin|81.8%|-10.6|
|hero|goblin_fort_chest_fight|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|goblin_fort_chest_fight|100.0%|100.0%|robin|100.0%|+0.0|
|mage|goblin_fort_chest_fight|100.0%|100.0%|robin|100.0%|+0.0|
|thief|goblin_fort_chest_fight|100.0%|100.0%|robin|100.0%|+0.0|
|hero|village_fire_slime|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|village_fire_slime|100.0%|100.0%|robin|100.0%|+0.0|
|mage|village_fire_slime|100.0%|100.0%|robin|100.0%|+0.0|
|thief|village_fire_slime|100.0%|100.0%|robin|100.0%|+0.0|
|hero|village_fire_elemental|99.2%|99.8%|robin|99.8%|+0.0|
|cleric|village_fire_elemental|93.4%|98.0%|fire_bat_empowered|98.4%|-0.4|
|mage|village_fire_elemental|91.0%|99.2%|robin|99.2%|+0.0|
|thief|village_fire_elemental|75.6%|93.0%|robin|93.8%|-0.8|
|hero|ice_elemental_encounter|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|ice_elemental_encounter|99.6%|100.0%|robin|100.0%|+0.0|
|mage|ice_elemental_encounter|99.0%|100.0%|robin|100.0%|+0.0|
|thief|ice_elemental_encounter|92.8%|97.2%|fire_bat_empowered|100.0%|-2.8|
|hero|frost_wolf_battle|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|frost_wolf_battle|100.0%|100.0%|robin|100.0%|+0.0|
|mage|frost_wolf_battle|100.0%|100.0%|robin|100.0%|+0.0|
|thief|frost_wolf_battle|100.0%|100.0%|robin|100.0%|+0.0|
|hero|draco_battle|57.2%|80.0%|fire_bat_empowered|90.2%|-10.2|
|cleric|draco_battle|56.6%|74.8%|fire_bat_empowered|83.4%|-8.6|
|mage|draco_battle|67.6%|76.4%|fire_bat_empowered|76.6%|-0.2|
|thief|draco_battle|67.2%|82.4%|fire_bat_empowered|82.0%|+0.4|
|hero|cave_heat_corridor|73.0%|86.8%|fire_bat_empowered|96.4%|-9.6|
|cleric|cave_heat_corridor|87.8%|95.8%|fire_bat_empowered|98.4%|-2.6|
|mage|cave_heat_corridor|86.0%|86.2%|fire_bat_empowered|94.6%|-8.4|
|thief|cave_heat_corridor|67.6%|84.8%|fire_bat_empowered|95.0%|-10.2|
|hero|cave_lava_room|76.0%|92.6%|fire_bat_empowered|97.4%|-4.8|
|cleric|cave_lava_room|86.8%|90.8%|fire_bat_empowered|95.2%|-4.4|
|mage|cave_lava_room|84.8%|89.2%|fire_bat_empowered|93.4%|-4.2|
|thief|cave_lava_room|82.2%|90.6%|fire_bat_empowered|96.6%|-6.0|
|hero|cave_crystal_corridor|56.2%|90.4%|fire_bat_empowered|98.4%|-8.0|
|cleric|cave_crystal_corridor|76.0%|94.0%|fire_bat_empowered|94.2%|-0.2|
|mage|cave_crystal_corridor|66.4%|81.6%|fire_bat_empowered|88.6%|-7.0|
|thief|cave_crystal_corridor|67.0%|91.6%|fire_bat_empowered|95.2%|-3.6|
|hero|cave_prism_tree|16.4%|86.2%|fire_bat_empowered|100.0%|-13.8|
|cleric|cave_prism_tree|58.4%|77.6%|fire_bat_empowered|99.8%|-22.2|
|mage|cave_prism_tree|39.0%|64.4%|fire_bat_empowered|86.4%|-22.0|
|thief|cave_prism_tree|45.4%|72.4%|fire_bat_empowered|96.2%|-23.8|
|hero|valley_entrance|84.6%|97.0%|paladin_liese|98.8%|-1.8|
|cleric|valley_entrance|86.8%|95.0%|paladin_liese|98.0%|-3.0|
|mage|valley_entrance|79.2%|92.0%|paladin_liese|96.6%|-4.6|
|thief|valley_entrance|85.8%|95.8%|paladin_liese|98.8%|-3.0|
|hero|valley_ledge|83.2%|86.8%|robin|88.2%|-1.4|
|cleric|valley_ledge|81.8%|86.0%|robin|86.6%|-0.6|
|mage|valley_ledge|78.6%|80.0%|robin|83.4%|-3.4|
|thief|valley_ledge|76.8%|87.8%|robin|88.4%|-0.6|
|hero|xanxus_phantom_battle|77.2%|89.8%|fire_bat_empowered|92.6%|-2.8|
|cleric|xanxus_phantom_battle|61.2%|85.0%|fire_bat_empowered|89.6%|-4.6|
|mage|xanxus_phantom_battle|56.8%|75.8%|fire_bat_empowered|83.6%|-7.8|
|thief|xanxus_phantom_battle|63.4%|79.8%|fire_bat_empowered|89.4%|-9.6|
|hero|mansion_corridor|78.8%|87.4%|fire_bat_empowered|94.2%|-6.8|
|cleric|mansion_corridor|78.6%|86.8%|fire_bat_dragon|90.6%|-3.8|
|mage|mansion_corridor|88.2%|85.8%|mina|89.2%|-3.4|
|thief|mansion_corridor|88.2%|93.0%|fire_bat_empowered|95.6%|-2.6|
|hero|inn_night_ambush|88.4%|92.8%|fire_bat_empowered|97.2%|-4.4|
|cleric|inn_night_ambush|82.6%|87.8%|fire_bat_empowered|94.0%|-6.2|
|mage|inn_night_ambush|80.8%|85.2%|fire_bat_empowered|89.4%|-4.2|
|thief|inn_night_ambush|92.6%|95.8%|fire_bat_dragon|97.8%|-2.0|
|hero|bone_field|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|bone_field|98.4%|99.8%|fire_bat_dragon|100.0%|-0.2|
|mage|bone_field|100.0%|99.8%|blue_robed_mage|100.0%|-0.2|
|thief|bone_field|97.8%|99.6%|fire_bat_dragon|100.0%|-0.4|
|hero|ghoul_marsh|100.0%|100.0%|robin|100.0%|+0.0|
|cleric|ghoul_marsh|100.0%|100.0%|robin|100.0%|+0.0|
|mage|ghoul_marsh|100.0%|100.0%|robin|100.0%|+0.0|
|thief|ghoul_marsh|100.0%|100.0%|robin|100.0%|+0.0|
|hero|grave_chapel|88.4%|100.0%|robin|100.0%|+0.0|
|cleric|grave_chapel|71.6%|100.0%|robin|100.0%|+0.0|
|mage|grave_chapel|80.2%|90.4%|robin|97.4%|-7.0|
|thief|grave_chapel|84.8%|100.0%|robin|100.0%|+0.0|

## 031经济规则

新区域三场均为可选战。复用031成本/拟合器：普通消耗品按商店最高买价，永久品不计收益，败北消耗计入成本且收益0。
最低休息0G（营地一次），另以可重复5G休息的更保守成本拟合；金币取四职业所需最大值、向上到5G并留5G余量。

|遭遇|职业|保守成本|金币|期望收益|收益/成本|
|---|---|---:|---:|---:|---:|
|gorge_rockfall_path|hero|3.76|25|25.00|6.65|
|gorge_rockfall_path|cleric|11.13|25|24.30|2.18|
|gorge_rockfall_path|mage|2.07|25|25.00|12.07|
|gorge_rockfall_path|thief|13.01|25|23.60|1.81|
|gorge_giant_path|hero|3.17|25|25.00|7.87|
|gorge_giant_path|cleric|12.06|25|24.60|2.04|
|gorge_giant_path|mage|3.83|25|24.90|6.50|
|gorge_giant_path|thief|12.94|25|23.80|1.84|
|gorge_worm_lair|hero|31.84|55|55.00|1.73|
|gorge_worm_lair|cleric|36.76|55|55.00|1.50|
|gorge_worm_lair|mage|31.87|55|55.00|1.73|
|gorge_worm_lair|thief|31.72|55|55.00|1.73|

## 结论与设计待办

- TODO(design): thief峡谷/村庄差+9.5pp，超出±5pp。

未改现有敌人、其他同行者或提示词。原始结果、检查点、敌人参数与指纹见同名JSON。

## 复现

```powershell
python -m scripts.balance.gorge --n 500 --route-n 5000 --seed 20261018 --workers 8
```

## 设计负责人复核（2026-10-18）：巨人潜行 DC 33 → 17
DC 33 对 d20 判定几乎不可能成功（只有敏捷很高的盗賊有机会），而且选项上会直接显示「DC33」，等于一个陷阱选项。改为和ワーム绕过相同的 DC17，并用同一命令重跑（上表即重跑结果）。

盗賊峡谷路线比村庄高 +9.5pp，超出 ±5pp。接受：村庄一直是盗賊最弱的路线（89.8%），峡谷的三处潜行正好发挥盗賊的特长，让每个职业各有自己擅长的路线。僧侶、魔法使い比改前更接近村庄（−0.4 / −0.3pp）。
