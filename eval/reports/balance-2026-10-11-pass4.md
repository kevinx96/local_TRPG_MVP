# 数值第四轮：连续流程优先

**route_targets：6/8 个职业通关率达标；1/2 条路线职业差距达标。**
**单场硬指标：pass3 36 项越界 → pass4 41 项越界。存在越界即未满足全部硬性要求，不能按全部验收通过处理。**

全部确认 N=500，seed=20261011，离线真实引擎、heuristic 策略。路线与 pass3 完全相同：主线经过森林狼；砦路线沿右路并战斗通过三层警卫，终点为第四层ゴブリン王，不冒称整个游戏通关。

## 1. 路线目标与前后对比

| 路线 | 职业 | pass3 | pass4 | 目标 | 达标 |
|---|---|---:|---:|---|---|
| dragon_valley_loc | hero | 24.8% | 80.8% | [0.55, 0.8] | 否 |
| dragon_valley_loc | cleric | 5.6% | 62.4% | [0.55, 0.8] | 是 |
| dragon_valley_loc | mage | 21.6% | 62.0% | [0.55, 0.8] | 是 |
| dragon_valley_loc | thief | 1.2% | 52.6% | [0.55, 0.8] | 否 |
| goblin_fort_fourth | hero | 23.8% | 72.6% | [0.4, 0.75] | 是 |
| goblin_fort_fourth | cleric | 5.8% | 57.0% | [0.4, 0.75] | 是 |
| goblin_fort_fourth | mage | 0.0% | 56.4% | [0.4, 0.75] | 是 |
| goblin_fort_fourth | thief | 0.0% | 68.4% | [0.4, 0.75] | 是 |

dragon_valley_loc 职业差距：23.6% → **28.2%**，上限20%。

goblin_fort_fourth 职业差距：23.8% → **16.2%**，上限20%。

路线未达标项：

- {"route":"dragon_valley_loc","character":"hero","metric":"completion_rate","value":0.808,"target":[0.55,0.8]}
- {"route":"dragon_valley_loc","character":"thief","metric":"completion_rate","value":0.526,"target":[0.55,0.8]}
- {"route":"dragon_valley_loc","character":"all","metric":"class_spread","value":0.28200000000000003,"target":[0,0.2]}

原因：锁定候选在N=64满足路线目标，但N=500扩大样本后部分职业越界；小样本筛选存在乐观偏差。本轮保持锁定参数，不用确认样本继续追调。主线进入最终Boss时升级回满HP/MP/SP，剩余差距不能全部归因于缺少休息点，还包括装备、技能和消耗品库存差异；具体失败次数见下表。

## 2. 失败点分布

每行以500次起步为分母；次数相加等于该路线失败数。

| 路线 | 职业 | pass3 失败次数 | pass4 失败次数 |
|---|---|---|---|
| dragon_valley_loc | hero | {"ice_elemental_encounter":39,"frost_wolf_battle":176,"dragon_valley_loc":148,"forest_wolves":13} | {"dragon_valley_loc":94,"ice_elemental_encounter":1,"forest_wolves":1} |
| dragon_valley_loc | cleric | {"forest_wolves":156,"ice_elemental_encounter":75,"frost_wolf_battle":207,"dragon_valley_loc":34} | {"dragon_valley_loc":127,"forest_wolves":52,"ice_elemental_encounter":7,"frost_wolf_battle":2} |
| dragon_valley_loc | mage | {"frost_wolf_battle":147,"forest_wolves":142,"dragon_valley_loc":64,"lost_goblin_crossroads":4,"ice_elemental_encounter":34,"dark_forest_loc":1} | {"dragon_valley_loc":115,"forest_wolves":53,"ice_elemental_encounter":10,"frost_wolf_battle":11,"dark_forest_loc":1} |
| dragon_valley_loc | thief | {"forest_wolves":266,"frost_wolf_battle":123,"dragon_valley_loc":20,"ice_elemental_encounter":74,"lost_goblin_crossroads":11} | {"forest_wolves":51,"ice_elemental_encounter":36,"dragon_valley_loc":145,"frost_wolf_battle":5} |
| goblin_fort_fourth | hero | {"goblin_fort_fourth":274,"goblin_fort_first_second":20,"goblin_fort_third_guards":59,"goblin_fort_second_right":28} | {"goblin_fort_fourth":137} |
| goblin_fort_fourth | cleric | {"goblin_fort_first_second":229,"goblin_fort_fourth":128,"goblin_fort_third_guards":94,"goblin_fort_second_right":20} | {"goblin_fort_fourth":213,"goblin_fort_first_second":2} |
| goblin_fort_fourth | mage | {"goblin_fort_first_second":222,"goblin_fort_third_guards":68,"goblin_fort_second_right":201,"goblin_fort":5,"dark_forest_loc":3,"goblin_fort_fourth":1} | {"goblin_fort_fourth":187,"goblin_fort_first_second":17,"goblin_fort_second_right":3,"goblin_fort_third_guards":8,"dark_forest_loc":3} |
| goblin_fort_fourth | thief | {"goblin_fort_first_second":329,"goblin_fort_second_right":136,"goblin_fort":15,"goblin_fort_third_guards":18,"dark_forest_loc":1,"goblin_fort_fourth":1} | {"goblin_fort_fourth":150,"goblin_fort_second_right":2,"goblin_fort_first_second":4,"goblin_fort_third_guards":1,"dark_forest_loc":1} |

## 3. 抵达路线最终 Boss 时的资源

只统计抵达者，不包含途中死亡者；HP/MP/SP 是绝对值，未人为回满。主线进入竜の谷仍由既有Lv5里程碑回满。本轮补充砦终点Boss的到达统计；pass3只记录竜の谷，因此砦没有历史资源均值。

| 路线 | 职业 | 到达次数 前→后 | HP/MP/SP 前→后 | pass4 背包均值 |
|---|---|---|---|---|
| dragon_valley_loc | hero | 272 → 498 | 40.000/12.000/18.000 → 40.000/12.000/18.000 | {"携帯食":2,"氷鉄の大剣":2,"治療の巻物":3.612,"薬草":3,"革の鎧":1} |
| dragon_valley_loc | cleric | 62 → 439 | 38.000/22.000/12.000 → 38.000/22.000/12.000 | {"ローブ":1,"携帯食":2,"氷鉄の大剣":1,"治療の巻物":3.271,"聖なる杖":1,"薬草":3.934} |
| dragon_valley_loc | mage | 172 → 425 | 24.000/32.000/10.000 → 24.000/32.000/10.000 | {"携帯食":2,"氷鉄の大剣":1,"治療の巻物":3.656,"薬草":2.845,"魔導書":1,"魔法のローブ":1} |
| dragon_valley_loc | thief | 26 → 408 | 30.000/10.000/22.000 → 30.000/10.000/22.000 | {"ダガー":1,"携帯食":2,"氷鉄の大剣":1,"治療の巻物":3.154,"盗賊道具":1,"薬草":1.949,"革の鎧":1} |
| goblin_fort_fourth | hero | 未记录 → 500 | 未记录/未抵达 → 17.618/8.000/1.016 | {"携帯食":2,"氷鉄の大剣":1,"治療の巻物":4.994,"聖水":2,"薬草":5,"革の鎧":1} |
| goblin_fort_fourth | cleric | 未记录 → 498 | 未记录/未抵达 → 14.139/14.000/8.000 | {"ローブ":1,"携帯食":2,"治療の巻物":4.735,"聖なる杖":1,"聖水":2,"薬草":5.95} |
| goblin_fort_fourth | mage | 未记录 → 469 | 未记录/未抵达 → 9.689/2.081/6.000 | {"携帯食":2,"治療の巻物":4.991,"聖水":2,"薬草":4.78,"魔導書":1,"魔法のローブ":1} |
| goblin_fort_fourth | thief | 未记录 → 492 | 未记录/未抵达 → 11.311/6.000/1.508 | {"ダガー":1,"携帯食":2,"治療の巻物":4.943,"盗賊道具":1,"聖水":2,"薬草":3.909,"革の鎧":1} |

## 4. 回复点、补给与搜索

- 王城宿屋现有 `rest_at_inn`：扣1G但无回复 → 扣1G并 `restore_full`，补齐现有休息语义。两条确认路线都不经过宿屋，因此不把通关率变化归功于它。
- 精霊の泉、砦回复阵保留已有 `restore_full`；泉会转入史莱姆支线，砦回复阵位于左路，不能偷偷插入既定右路。
- 战斗奖励只加入已有的薬草、治療の巻物，回复量、稀有标记、使用策略不变；每个敌人分别发奖，多敌场按数量累计。商店价格和库存未改。
- N=16粗筛回复品数量与敌人数值，N=32/64复核候选；最后锁定参数才运行N=500。搜索主要分数为路线通关区间/职业差距的越界距离平方和，单场完整矩阵独立核验。
- 已保存搜索记录 `245` 个候选评价，选中 `variance-4`；参数和分阶段分数见 `eval/balance/pass4-search.json`。
- 只增加回复品的候选收益见顶，尤其砦魔法使的MP不会被HP回复品恢复。降低敌方HP可减少累计消耗，但会抬高单场胜率/普攻胜率；这种冲突如实列于第5节，没有放宽单场目标。

## 5. 单场胜率变化与硬指标

HP余量、回合数仍保存在确认JSON；默认不判定，加 `--check-resource-metrics` 可恢复两项检查。pass3也按本轮同一硬指标口径重算，避免用删去软指标造成的数量下降充当数值改进。

| 遭遇 | 职业 | heuristic 前→后 | 普攻 前→后 | HP均值 | 回合中位数 |
|---|---|---|---|---:|---:|
| dark_forest_loc | hero | 1.000 → 1.000 | 1.000 → 1.000 | 0.915 | 3.0 |
| dark_forest_loc | cleric | 1.000 → 1.000 | 0.994 → 0.994 | 0.771 | 4.0 |
| dark_forest_loc | mage | 0.998 → 0.998 | 0.852 → 0.852 | 0.873 | 2.0 |
| dark_forest_loc | thief | 1.000 → 1.000 | 0.994 → 0.994 | 0.830 | 3.0 |
| lost_goblin_crossroads | hero | 1.000 → 1.000 | 1.000 → 1.000 | 0.996 | 1.0 |
| lost_goblin_crossroads | cleric | 1.000 → 1.000 | 0.998 → 1.000 | 0.994 | 1.0 |
| lost_goblin_crossroads | mage | 1.000 → 1.000 | 0.942 → 1.000 | 0.993 | 1.0 |
| lost_goblin_crossroads | thief | 1.000 → 1.000 | 1.000 → 1.000 | 0.986 | 1.0 |
| slime_ambush_one | hero | 1.000 → 1.000 | 1.000 → 1.000 | 0.918 | 3.0 |
| slime_ambush_one | cleric | 1.000 → 1.000 | 0.992 → 0.992 | 0.786 | 4.0 |
| slime_ambush_one | mage | 0.998 → 0.998 | 0.868 → 0.868 | 0.877 | 2.0 |
| slime_ambush_one | thief | 0.996 → 0.998 | 0.998 → 0.998 | 0.844 | 3.0 |
| slime_ambush_two | hero | 1.000 → 1.000 | 1.000 → 1.000 | 0.907 | 3.0 |
| slime_ambush_two | cleric | 1.000 → 1.000 | 0.986 → 0.986 | 0.792 | 4.0 |
| slime_ambush_two | mage | 1.000 → 1.000 | 0.830 → 0.830 | 0.884 | 2.0 |
| slime_ambush_two | thief | 0.998 → 1.000 | 0.998 → 0.998 | 0.842 | 3.0 |
| goblin_fort | hero | 1.000 → 1.000 | 1.000 → 1.000 | 0.995 | 1.0 |
| goblin_fort | cleric | 1.000 → 1.000 | 0.996 → 1.000 | 0.991 | 1.0 |
| goblin_fort | mage | 0.998 → 1.000 | 0.944 → 1.000 | 0.987 | 1.0 |
| goblin_fort | thief | 0.996 → 1.000 | 1.000 → 1.000 | 0.989 | 1.0 |
| goblin_fort_chest_fight | hero | 1.000 → 1.000 | 1.000 → 1.000 | 0.999 | 1.0 |
| goblin_fort_chest_fight | cleric | 1.000 → 1.000 | 1.000 → 1.000 | 0.999 | 1.0 |
| goblin_fort_chest_fight | mage | 1.000 → 1.000 | 0.998 → 1.000 | 0.995 | 1.0 |
| goblin_fort_chest_fight | thief | 1.000 → 1.000 | 1.000 → 1.000 | 0.993 | 1.0 |
| village_fire_slime | hero | 1.000 → 1.000 | 1.000 → 1.000 | 0.943 | 2.0 |
| village_fire_slime | cleric | 1.000 → 1.000 | 1.000 → 1.000 | 0.887 | 3.0 |
| village_fire_slime | mage | 1.000 → 1.000 | 0.988 → 0.988 | 0.908 | 2.0 |
| village_fire_slime | thief | 1.000 → 1.000 | 1.000 → 1.000 | 0.850 | 4.0 |
| forest_wolves | hero | 0.976 → 0.998 | 0.938 → 0.998 | 0.887 | 2.0 |
| forest_wolves | cleric | 0.814 → 0.966 | 0.578 → 0.952 | 0.804 | 3.0 |
| forest_wolves | mage | 0.832 → 0.930 | 0.150 → 0.698 | 0.905 | 2.0 |
| forest_wolves | thief | 0.708 → 0.978 | 0.562 → 0.958 | 0.833 | 2.0 |
| goblin_fort_first_second | hero | 0.984 → 1.000 | 0.958 → 1.000 | 0.923 | 2.0 |
| goblin_fort_first_second | cleric | 0.786 → 0.996 | 0.610 → 0.988 | 0.830 | 3.0 |
| goblin_fort_first_second | mage | 0.706 → 0.994 | 0.070 → 0.952 | 0.842 | 2.0 |
| goblin_fort_first_second | thief | 0.678 → 0.998 | 0.720 → 1.000 | 0.863 | 2.0 |
| goblin_fort_second_right | hero | 1.000 → 1.000 | 0.996 → 1.000 | 0.980 | 2.0 |
| goblin_fort_second_right | cleric | 1.000 → 1.000 | 0.526 → 1.000 | 0.923 | 2.0 |
| goblin_fort_second_right | mage | 0.904 → 1.000 | 0.030 → 0.996 | 0.989 | 1.0 |
| goblin_fort_second_right | thief | 0.798 → 1.000 | 0.668 → 1.000 | 0.955 | 2.0 |
| goblin_fort_second_left | hero | 0.970 → 0.978 | 0.926 → 0.926 | 0.742 | 4.0 |
| goblin_fort_second_left | cleric | 0.772 → 0.808 | 0.496 → 0.496 | 0.703 | 7.0 |
| goblin_fort_second_left | mage | 0.804 → 0.828 | 0.126 → 0.126 | 0.771 | 3.0 |
| goblin_fort_second_left | thief | 0.664 → 0.770 | 0.542 → 0.542 | 0.719 | 5.0 |
| goblin_fort_third_guards | hero | 1.000 → 1.000 | 0.998 → 1.000 | 0.980 | 2.0 |
| goblin_fort_third_guards | cleric | 1.000 → 1.000 | 0.586 → 1.000 | 0.924 | 2.0 |
| goblin_fort_third_guards | mage | 0.888 → 1.000 | 0.032 → 0.998 | 0.993 | 1.0 |
| goblin_fort_third_guards | thief | 0.822 → 1.000 | 0.712 → 1.000 | 0.946 | 2.0 |
| village_fire_elemental | hero | 0.966 → 0.996 | 0.966 → 0.966 | 0.726 | 3.0 |
| village_fire_elemental | cleric | 0.798 → 0.948 | 0.428 → 0.428 | 0.643 | 4.0 |
| village_fire_elemental | mage | 0.838 → 0.892 | 0.114 → 0.114 | 0.705 | 2.0 |
| village_fire_elemental | thief | 0.556 → 0.772 | 0.492 → 0.492 | 0.654 | 5.0 |
| ice_elemental_encounter | hero | 0.918 → 0.998 | 0.000 → 0.000 | 0.747 | 3.0 |
| ice_elemental_encounter | cleric | 0.888 → 0.994 | 0.666 → 0.810 | 0.724 | 3.0 |
| ice_elemental_encounter | mage | 0.916 → 0.988 | 0.388 → 0.488 | 0.854 | 2.0 |
| ice_elemental_encounter | thief | 0.756 → 0.932 | 0.768 → 0.874 | 0.708 | 4.0 |
| slime_king_battle | hero | 0.930 → 0.952 | 0.098 → 0.098 | 0.642 | 6.0 |
| slime_king_battle | cleric | 0.710 → 0.772 | 0.000 → 0.000 | 0.632 | 7.0 |
| slime_king_battle | mage | 0.684 → 0.716 | 0.000 → 0.000 | 0.659 | 3.0 |
| slime_king_battle | thief | 0.642 → 0.762 | 0.002 → 0.002 | 0.638 | 6.0 |
| goblin_fort_fourth | hero | 0.968 → 0.722 | 0.004 → 0.156 | 0.712 | 5.0 |
| goblin_fort_fourth | cleric | 0.626 → 0.638 | 0.000 → 0.006 | 0.714 | 5.0 |
| goblin_fort_fourth | mage | 0.540 → 0.654 | 0.000 → 0.000 | 0.697 | 3.0 |
| goblin_fort_fourth | thief | 0.640 → 0.776 | 0.000 → 0.050 | 0.698 | 5.0 |
| merchant_battle | hero | 0.672 → 0.672 | 0.000 → 0.000 | 0.870 | 4.0 |
| merchant_battle | cleric | 0.792 → 0.792 | 0.000 → 0.000 | 0.929 | 2.0 |
| merchant_battle | mage | 0.692 → 0.692 | 0.000 → 0.000 | 0.850 | 2.0 |
| merchant_battle | thief | 0.662 → 0.662 | 0.000 → 0.000 | 0.853 | 4.0 |
| frost_wolf_battle | hero | 0.976 → 1.000 | 0.000 → 0.000 | 0.808 | 4.0 |
| frost_wolf_battle | cleric | 0.834 → 1.000 | 0.026 → 0.790 | 0.755 | 4.0 |
| frost_wolf_battle | mage | 0.896 → 1.000 | 0.002 → 0.372 | 0.827 | 2.0 |
| frost_wolf_battle | thief | 0.590 → 1.000 | 0.066 → 0.832 | 0.829 | 4.0 |
| dragon_valley_loc | hero | 0.632 → 0.836 | 0.398 → 0.280 | 0.652 | 9.0 |
| dragon_valley_loc | cleric | 0.650 → 0.722 | 0.212 → 0.132 | 0.668 | 10.0 |
| dragon_valley_loc | mage | 0.640 → 0.704 | 0.148 → 0.080 | 0.730 | 5.0 |
| dragon_valley_loc | thief | 0.706 → 0.770 | 0.000 → 0.000 | 0.716 | 7.0 |
| xanxus_battle | hero | 0.000 → 0.000 | 0.000 → 0.000 | — | 3.0 |
| xanxus_battle | cleric | 0.000 → 0.000 | 0.000 → 0.000 | — | 3.0 |
| xanxus_battle | mage | 0.000 → 0.000 | 0.000 → 0.000 | — | 1.0 |
| xanxus_battle | thief | 0.000 → 0.000 | 0.000 → 0.000 | — | 3.0 |
| warlock_rescue_battle | warlock | 1.000 → 1.000 | 0.932 → 0.932 | 1.000 | 5.0 |

共有 17 项新增越界，其中 14 项胜率、3 项Boss普攻上限。本轮胜率越界均为高于上限：缩短战斗、增加回复奖励解决了连续消耗，却使部分独立满资源战斗过易。低HP的霜狼更容易被普攻击败；累积的回复品又提高后续Boss胜率。因此单场区间确实被部分候选改动破坏，本轮没有实现这项硬性要求，不能只凭砦路线达标接受全部数值。

全部硬指标越界（“新增”指pass3同口径下该cell/指标原本达标）：

| 遭遇 | 职业 | 指标 | 值 | 目标 | 状态 |
|---|---|---|---:|---|---|
| forest_wolves | hero | win_rate | 0.998 | [0.75, 0.9] | 既有 |
| forest_wolves | cleric | win_rate | 0.966 | [0.75, 0.9] | 新增 |
| forest_wolves | mage | win_rate | 0.930 | [0.75, 0.9] | 新增 |
| forest_wolves | thief | win_rate | 0.978 | [0.75, 0.9] | 既有 |
| goblin_fort_first_second | hero | win_rate | 1.000 | [0.75, 0.9] | 既有 |
| goblin_fort_first_second | cleric | win_rate | 0.996 | [0.75, 0.9] | 新增 |
| goblin_fort_first_second | mage | win_rate | 0.994 | [0.75, 0.9] | 既有 |
| goblin_fort_first_second | thief | win_rate | 0.998 | [0.75, 0.9] | 既有 |
| goblin_fort_second_right | hero | win_rate | 1.000 | [0.75, 0.9] | 既有 |
| goblin_fort_second_right | cleric | win_rate | 1.000 | [0.75, 0.9] | 既有 |
| goblin_fort_second_right | mage | win_rate | 1.000 | [0.75, 0.9] | 既有 |
| goblin_fort_second_right | thief | win_rate | 1.000 | [0.75, 0.9] | 新增 |
| goblin_fort_second_left | hero | win_rate | 0.978 | [0.75, 0.9] | 既有 |
| goblin_fort_third_guards | hero | win_rate | 1.000 | [0.75, 0.9] | 既有 |
| goblin_fort_third_guards | cleric | win_rate | 1.000 | [0.75, 0.9] | 既有 |
| goblin_fort_third_guards | mage | win_rate | 1.000 | [0.75, 0.9] | 新增 |
| goblin_fort_third_guards | thief | win_rate | 1.000 | [0.75, 0.9] | 新增 |
| village_fire_elemental | hero | win_rate | 0.996 | [0.75, 0.9] | 既有 |
| village_fire_elemental | cleric | win_rate | 0.948 | [0.75, 0.9] | 新增 |
| ice_elemental_encounter | hero | win_rate | 0.998 | [0.75, 0.9] | 既有 |
| ice_elemental_encounter | cleric | win_rate | 0.994 | [0.75, 0.9] | 新增 |
| ice_elemental_encounter | mage | win_rate | 0.988 | [0.75, 0.9] | 既有 |
| ice_elemental_encounter | thief | win_rate | 0.932 | [0.75, 0.9] | 新增 |
| slime_king_battle | hero | win_rate | 0.952 | [0.6, 0.75] | 既有 |
| slime_king_battle | cleric | win_rate | 0.772 | [0.6, 0.75] | 新增 |
| slime_king_battle | thief | win_rate | 0.762 | [0.6, 0.75] | 新增 |
| goblin_fort_fourth | thief | win_rate | 0.776 | [0.6, 0.75] | 新增 |
| merchant_battle | cleric | win_rate | 0.792 | [0.6, 0.75] | 既有 |
| frost_wolf_battle | hero | win_rate | 1.000 | [0.6, 0.75] | 既有 |
| frost_wolf_battle | cleric | win_rate | 1.000 | [0.6, 0.75] | 既有 |
| frost_wolf_battle | cleric | attack_only_win_rate | 0.790 | [0, 0.2] | 新增 |
| frost_wolf_battle | mage | win_rate | 1.000 | [0.6, 0.75] | 既有 |
| frost_wolf_battle | mage | attack_only_win_rate | 0.372 | [0, 0.2] | 新增 |
| frost_wolf_battle | thief | win_rate | 1.000 | [0.6, 0.75] | 既有 |
| frost_wolf_battle | thief | attack_only_win_rate | 0.832 | [0, 0.2] | 新增 |
| dragon_valley_loc | hero | win_rate | 0.836 | [0.6, 0.75] | 新增 |
| dragon_valley_loc | hero | attack_only_win_rate | 0.280 | [0, 0.2] | 既有 |
| dragon_valley_loc | thief | win_rate | 0.770 | [0.6, 0.75] | 新增 |
| goblin_fort_second_left | all | class_spread | 0.208 | [0, 0.15] | 既有 |
| village_fire_elemental | all | class_spread | 0.224 | [0, 0.15] | 既有 |
| slime_king_battle | all | class_spread | 0.236 | [0, 0.15] | 既有 |

## 6. 剧本完整改动清单

两份剧本相同字段同步修改；未改文本、角色、技能、里程碑、敌人种类与数量、xanxus/warlock战。

| 对象 / JSON路径 | 原值 | 新值 | 原因 |
|---|---|---|---|
| slime `/enemies/0/rewards/items` | [] | [{"name":"薬草","quantity":2},{"name":"治療の巻物","quantity":1}] | 增加跨战斗HP补给；保持回复品原效果 |
| ignis `/enemies/1/combat/basic_attack/damage` | "1d20" | "1d21" | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| ignis `/enemies/1/hp` | 152 | 168 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| ignis `/enemies/1/max_hp` | 152 | 168 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| ignis `/enemies/1/skills/0/damage` | "1d20" | "1d21" | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| ignis `/enemies/1/skills/0/dice_type` | "1d20" | "1d21" | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| ignis `/enemies/1/skills/1/damage` | "1d20" | "1d21" | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| ignis `/enemies/1/skills/1/dice_type` | "1d20" | "1d21" | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin `/enemies/2/combat/basic_attack/accuracy` | 100 | 75 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin `/enemies/2/combat/defense` | 2 | 0 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin `/enemies/2/combat/evade` | 12 | 0 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin `/enemies/2/hp` | 8 | 4 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin `/enemies/2/max_hp` | 8 | 4 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin `/enemies/2/rewards/items` | [] | [{"name":"治療の巻物","quantity":1}] | 增加跨战斗HP补给；保持回复品原效果 |
| goblin_archer `/enemies/3/combat/basic_attack/accuracy` | 100 | 90 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin_archer `/enemies/3/combat/defense` | 1 | 0 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin_archer `/enemies/3/combat/evade` | 10 | 0 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin_archer `/enemies/3/hp` | 16 | 8 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin_archer `/enemies/3/max_hp` | 16 | 8 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin_archer `/enemies/3/rewards/items` | [] | [{"name":"治療の巻物","quantity":2}] | 增加跨战斗HP补给；保持回复品原效果 |
| hobgoblin `/enemies/4/combat/basic_attack/accuracy` | 100 | 60 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| hobgoblin `/enemies/4/combat/defense` | 1 | 0 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| hobgoblin `/enemies/4/combat/evade` | 5 | 0 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| hobgoblin `/enemies/4/hp` | 44 | 12 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| hobgoblin `/enemies/4/max_hp` | 44 | 12 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| hobgoblin `/enemies/4/rewards/items` | [] | [{"name":"薬草","quantity":1}] | 增加跨战斗HP补给；保持回复品原效果 |
| forest_wolf `/enemies/6/combat/basic_attack/accuracy` | 70 | 60 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| forest_wolf `/enemies/6/combat/basic_attack/damage` | "1d10" | "1d12" | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| forest_wolf `/enemies/6/combat/defense` | 2 | 0 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| forest_wolf `/enemies/6/hp` | 32 | 16 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| forest_wolf `/enemies/6/max_hp` | 32 | 16 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin_king `/enemies/8/combat/basic_attack/accuracy` | 95 | 50 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin_king `/enemies/8/combat/basic_attack/damage` | "1d10" | "1d24" | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin_king `/enemies/8/combat/defense` | 1 | 0 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin_king `/enemies/8/hp` | 64 | 56 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| goblin_king `/enemies/8/max_hp` | 64 | 56 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| fire_slime `/enemies/10/rewards/items` | [] | [{"name":"治療の巻物","quantity":2}] | 增加跨战斗HP补给；保持回复品原效果 |
| ice_elemental `/enemies/12/combat/basic_attack/accuracy` | 35 | 75 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| ice_elemental `/enemies/12/combat/basic_attack/damage` | "2d12" | "1d16" | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| ice_elemental `/enemies/12/combat/evade` | 5 | 0 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| ice_elemental `/enemies/12/hp` | 44 | 28 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| ice_elemental `/enemies/12/max_hp` | 44 | 28 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| frost_dire_wolf `/enemies/13/combat/basic_attack/accuracy` | 65 | 60 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| frost_dire_wolf `/enemies/13/combat/basic_attack/damage` | "1d10" | "1d12" | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| frost_dire_wolf `/enemies/13/combat/defense` | 1 | 0 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| frost_dire_wolf `/enemies/13/hp` | 124 | 48 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| frost_dire_wolf `/enemies/13/max_hp` | 124 | 48 | 路线优先搜索所选敌人数值；减少资源累计消耗并控制通关率/职业差距，单场代价见第5节 |
| inn `/locations/2/actions/0/children/2/effects` | [{"gold_change":-1}] | [{"gold_change":-1},{"restore_full":true}] | 补齐宿屋已有休息语义 |

## 7. TODO(design)、推断和限制

- TODO(design): 霜狼战前没有可用的既有休息动作；需要在凍結した村或氷の精霊战后审定新动作及文本，本轮不擅自添加。
- TODO(design): 竜の谷前没有现成休息动作，但进入时Lv5已全回复；若仍需独立休息点，请审定イアン战后地点的新动作。
- TODO(design): 保持现有右路砦战斗序列是否代表目标路线？若要使用现成回复阵，需要设计审定左路替代方案；Lv2技能在砦前仍不可用，未改里程碑。
- TODO(design): 审定尚未满足的单场硬指标与路线目标之间的冲突。满资源单场上限约束会压低多次连续精英/Boss流程成功率；这只是当前路线/策略下的实测权衡，未证明允许参数空间无解。
- 推断：哥布林砦通关指pass3的 `goblin_fort_fourth` 终点；每条路线分别约束职业差距，不把两个不同难度路线混成一组。
- 推断：回复品获取允许从原本空奖励列表增加已有回复品；无新增道具，按敌人模板发放；宿屋的回复使用已有 `restore_full`，含HP/MP/SP。
- 推断：保留checkpoint的固定非战斗判定、同伴和装备选择，不自行添加购物、休息或更换路线；结果不代表所有玩家路径。
- 推断：spec未指定粗筛N、搜索分数、候选网格和并列规则；采用N=16/32/64、越界距离平方和、固定搜索seed与有限候选网格。两个最终候选的路线分数均为0时，先取单场越界项较少者，再比较单场越界距离；这不是证明硬指标存在可行解。
- 推断：沿用pass3已有的每cell seed=20261011便于前后对照；只需确认目标文件列出的两条路线，其余分支仍用完整21场单场矩阵检查。
- 偏离/未完成目标：存在的硬指标越界已完整列出；未改目标掩盖问题，也未声称全部达标。未新增设计专属动作。
- 已知限制：稀有治療の巻物只在Boss可用；HP回复品不恢复MP/SP。单场checkpoint继承全部历史奖励且不扣历史消耗，可能高估实际到达Boss的库存。
- N=500是每cell的蒙特卡洛确认，最大标准误约2.24个百分点，不保证换seed仍落在边界内。小N使用相同seed的前缀，N=500包含筛选样本，不是独立留出集。

## 8. 实现、验证和复现

- 新增route_targets与完整cell检查，缺失/重复职业也判失败；`route --check`统一运行目标文件列出的两条路线，禁止分片直接验收。
- `sim --check-resource-metrics`显式恢复HP/回合判定；新增离线测试覆盖配置读取、边界、职业差距、缺失cell、CLI、真实休息/发奖、砦Boss资源记录。无新增依赖。
- 既有氷の護符追击测试原先依赖哥布林存活到追加攻击；降低HP后首击已击杀。该测试固定目标HP=100以验证追击机制，不再依赖当前平衡数值。
- 全量测试曾在沙箱内遭遇TemporaryDirectory的WinError 5；最终使用获准的本地沙箱外测试执行，见下面实际验证记录。
- python -m unittest discover -s tests -q: Ran 331 tests in 33.120s; OK (skipped=1), exit 0.
- node --check client/app.js: exit 0.
- git diff --check: exit 0.
- python -m scripts.balance.route --check --n 500: 8 route cells; 3 violations; exit 1.
- python -m scripts.balance.sim --check --n 500 (four disjoint encounter shards): 162 cells; merged 41 hard violations; exit 1.
- Both scenario mechanical deltas match (48 fields); protected fields and all route steps unchanged.

```powershell
python -m scripts.balance.checkpoints
python -m scripts.balance.route --check --n 500 --output eval/reports/balance-2026-10-11-pass4-routes.json
python -m scripts.balance.sim --check --n 500 --output eval/reports/balance-2026-10-11-pass4.json
python -m unittest discover -s tests -q
node --check client/app.js
python -m scripts.balance.pass4_report
```

搜索候选参数可从pass4-search.json导出为name/parameters数组，使用 `python -m scripts.balance.pass4 --n 16 --candidates <文件> --output <结果>` 重放；加 `--single-check` 同时复核单场。支持独立分片，默认单进程兼容Windows沙箱。
