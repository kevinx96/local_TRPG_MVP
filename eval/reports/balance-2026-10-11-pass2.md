# 005 第二轮平衡报告

离线真实战斗引擎，flat 防御，无外部 API、无新增依赖。
正式 N=500 / cell，seed=20261011，共 344 cell / 172,000 场；墙钟 912.6 秒。
pass1 基线提交 `6abff336d6c7795cde2465e8f48eba06324c9dad`，复用 pass1 的 N=500 结果。先 N=16 粗筛、N=64 复核，再锁定参数做 N=500 确认；搜索与补充复核记录见 eval/balance/pass2-search.json。
checkpoint 仍为 proposed；每场回满 HP/MP/SP，不扣历史道具消耗，不能视作连续通关率。本轮所有 checkpoint 经真实 check_supplies 领取两瓶聖水，移除原先只对商人战的模拟注入。
因此 pass1→pass2 同时包含设计指定的技能、补给口径及数值变化；不是纯敌人数值的因果对照。另提供同一最终配置下去掉8个新技能的消融。

复现：

```powershell
python -m scripts.balance.checkpoints
python -m scripts.balance.pass2 --n 500 --output eval/reports/balance-2026-10-11-pass2.json
python -m scripts.balance.pass2_report
python -m scripts.balance.sim --check --n 500 --output .tmp-test/balance-pass2-check.json
```

## 1. 前后达标情况

`--check` 越界：**124 → 98**；targets.json 未修改。
全指标包含所有职业的胜率、胜利剩余HP均值、全部战斗（含失败）的回合中位数、职业差距和Boss普攻上限；伤害预算、同伴提升另行列出，不混入 --check 计数。

| 类别 | 总数 | pass1全指标 | pass2全指标 | pass1仅胜率 | pass2仅胜率 |
|---|---:|---:|---:|---:|---:|
| trash | 7 | 0 | 3 | 7 | 7 |
| elite | 7 | 0 | 0 | 0 | 0 |
| boss | 5 | 0 | 0 | 0 | 1 |
| scripted_loss | 1 | 1 | 1 | 1 | 1 |
| guest | 1 | 1 | 1 | 1 | 1 |

职业顺序为 hero / cleric / mage / thief；guest 为 warlock。

| 遭遇 | Lv | pass1胜率 | pass2胜率 | 职业差距前→后 | 越界前→后 | pass2回合 | pass2胜利HP |
|---|---|---|---|---|---|---|---|
| dark_forest_loc | 1 | 1.000 / 1.000 / 0.998 / 0.982 | 1.000 / 0.996 / 0.958 / 0.956 | 0.018→0.044 | 1→0 | 4.000 / 4.000 / 3.000 / 4.000 | 0.840 / 0.756 / 0.734 / 0.761 |
| lost_goblin_crossroads | 1 | 1.000 / 1.000 / 1.000 / 0.994 | 1.000 / 1.000 / 0.994 / 0.994 | 0.006→0.006 | 1→1 | 4.000 / 4.000 / 3.000 / 4.000 | 0.869 / 0.755 / 0.726 / 0.780 |
| slime_ambush_one | 1 | 1.000 / 1.000 / 1.000 / 0.990 | 1.000 / 0.992 / 0.966 / 0.976 | 0.010→0.034 | 1→1 | 4.000 / 4.000 / 3.000 / 4.000 | 0.850 / 0.770 / 0.742 / 0.772 |
| slime_ambush_two | 1 | 1.000 / 1.000 / 0.996 / 0.992 | 1.000 / 0.994 / 0.970 / 0.952 | 0.008→0.048 | 1→0 | 4.000 / 4.000 / 3.000 / 4.000 | 0.848 / 0.767 / 0.754 / 0.773 |
| goblin_fort | 1 | 1.000 / 1.000 / 0.988 / 0.992 | 1.000 / 1.000 / 0.988 / 0.992 | 0.012→0.012 | 1→1 | 4.000 / 4.000 / 3.000 / 4.000 | 0.868 / 0.758 / 0.725 / 0.766 |
| goblin_fort_chest_fight | 3 | 1.000 / 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 / 1.000 | 0.000→0.000 | 4→3 | 3.000 / 3.000 / 3.000 / 4.000 | 0.942 / 0.881 / 0.799 / 0.891 |
| village_fire_slime | 4 | 1.000 / 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 0.994 / 0.996 | 0.000→0.006 | 1→0 | 3.000 / 3.000 / 3.000 / 4.000 | 0.807 / 0.726 / 0.676 / 0.680 |
| forest_wolves | 1 | 0.996 / 0.926 / 0.870 / 0.734 | 0.996 / 0.924 / 0.776 / 0.776 | 0.262→0.220 | 9→7 | 5.000 / 7.000 / 4.000 / 5.000 | 0.706 / 0.628 / 0.648 / 0.553 |
| goblin_fort_first_second | 1 | 1.000 / 0.914 / 0.906 / 0.860 | 1.000 / 0.910 / 0.546 / 0.516 | 0.140→0.484 | 8→12 | 11.000 / 17.000 / 8.000 / 11.000 | 0.699 / 0.639 / 0.507 / 0.421 |
| goblin_fort_second_right | 1 | 1.000 / 0.954 / 0.956 / 0.870 | 1.000 / 0.960 / 0.780 / 0.798 | 0.130→0.220 | 9→7 | 5.000 / 7.000 / 5.000 / 5.000 | 0.722 / 0.631 / 0.635 / 0.567 |
| goblin_fort_second_left | 1 | 1.000 / 1.000 / 0.954 / 0.864 | 0.926 / 0.748 / 0.656 / 0.636 | 0.136→0.290 | 8→9 | 4.000 / 5.000 / 4.000 / 4.000 | 0.689 / 0.681 / 0.717 / 0.610 |
| goblin_fort_third_guards | 1 | 1.000 / 0.964 / 0.930 / 0.848 | 0.998 / 0.970 / 0.784 / 0.790 | 0.152→0.214 | 10→7 | 5.000 / 7.000 / 5.000 / 5.000 | 0.713 / 0.640 / 0.619 / 0.546 |
| village_fire_elemental | 4 | 1.000 / 1.000 / 1.000 / 0.944 | 0.970 / 0.908 / 0.880 / 0.566 | 0.056→0.404 | 8→6 | 4.000 / 5.000 / 4.000 / 6.000 | 0.605 / 0.499 / 0.549 / 0.384 |
| ice_elemental_encounter | 4 | 0.994 / 1.000 / 1.000 / 0.918 | 0.984 / 0.956 / 0.904 / 0.774 | 0.082→0.210 | 8→5 | 4.000 / 4.000 / 4.000 / 4.000 | 0.535 / 0.488 / 0.428 / 0.391 |
| slime_king_battle | 1 | 0.992 / 0.654 / 0.908 / 0.466 | 0.982 / 0.652 / 0.654 / 0.414 | 0.526→0.568 | 12→7 | 8.000 / 12.000 / 5.000 / 7.000 | 0.555 / 0.477 / 0.521 / 0.388 |
| goblin_fort_fourth | 1 | 0.988 / 0.662 / 0.652 / 0.636 | 0.988 / 0.670 / 0.628 / 0.624 | 0.352→0.364 | 10→7 | 12.000 / 15.000 / 8.000 / 11.000 | 0.645 / 0.602 / 0.571 / 0.435 |
| merchant_battle | 1 | 0.870 / 0.998 / 0.840 / 0.868 | 0.672 / 0.792 / 0.692 / 0.662 | 0.158→0.130 | 13→9 | 4.000 / 2.000 / 2.000 / 4.000 | 0.870 / 0.929 / 0.850 / 0.853 |
| frost_wolf_battle | 4 | 0.878 / 0.656 / 0.942 / 0.304 | 0.958 / 0.830 / 0.916 / 0.604 | 0.638→0.354 | 9→8 | 10.000 / 13.000 / 6.000 / 11.000 | 0.487 / 0.392 / 0.551 / 0.341 |
| dragon_valley_loc | 5 | 0.426 / 0.350 / 0.356 / 0.000 | 0.658 / 0.694 / 0.630 / 0.704 | 0.426→0.074 | 10→8 | 7.000 / 8.000 / 4.000 / 5.000 | 0.428 / 0.528 / 0.570 / 0.487 |
| xanxus_battle | 4 | 0.000 / 0.000 / 0.000 / 0.000 | 0.000 / 0.000 / 0.000 / 0.000 | 0.000→0.000 | 0→0 | 3.000 / 3.000 / 1.000 / 3.000 | — / — / — / — |
| warlock_rescue_battle | 1 | 1.000 | 1.000 | 0.000→0.000 | 0→0 | 5.000 | 1.000 |

### 同伴效果

每2回合（第2、4、6…回合开始）回复最大HP的 **15%**，沿用四舍五入。只纳入实际携带蓝袍法师的56个职业×遭遇cell，离队及guest不稀释均值。

| 遭遇 | pass1提升pp | pass2提升pp | pass2各职业提升pp |
|---|---:|---:|---|
| dark_forest_loc | 1.20 | 3.60 | 0.800 / 1.400 / 6.400 / 5.800 |
| lost_goblin_crossroads | 1.45 | 1.05 | 0.000 / 0.000 / 1.400 / 2.800 |
| slime_ambush_one | 1.45 | 3.05 | 0.200 / 1.200 / 7.200 / 3.600 |
| slime_ambush_two | 1.55 | 3.35 | 0.600 / 1.600 / 6.000 / 5.200 |
| goblin_fort | 1.10 | 1.30 | 0.000 / 0.000 / 1.600 / 3.600 |
| goblin_fort_chest_fight | 0.05 | 0.05 | 0.000 / 0.000 / 0.000 / 0.200 |
| forest_wolves | 11.45 | 10.45 | 1.600 / 7.600 / 14.400 / 18.200 |
| goblin_fort_first_second | 9.25 | 35.20 | 23.200 / 25.800 / 42.800 / 49.000 |
| goblin_fort_second_right | 8.15 | 10.45 | 4.800 / 4.600 / 14.200 / 18.200 |
| goblin_fort_second_left | 13.20 | 9.65 | 12.200 / 12.600 / 5.000 / 8.800 |
| goblin_fort_third_guards | 6.20 | 11.35 | 6.000 / 5.600 / 14.000 / 19.800 |
| slime_king_battle | 26.20 | 32.95 | 28.600 / 57.200 / 18.200 / 27.800 |
| goblin_fort_fourth | 29.30 | 51.75 | 46.800 / 62.800 / 40.400 / 57.000 |
| merchant_battle | 0.15 | 1.60 | 0.400 / 7.800 / -1.800 / 0.000 |

等权平均提升 **7.91 → 12.56pp**，目标10–20pp。

N=64回复比例复核（正式N=500前完成选择）：

| 每2回合回复比例 | 平均提升pp | 越界数 |
|---|---:|---:|
| 15% | 13.09 | 93 |
| 20% | 15.71 | 103 |
| 25% | 18.14 | 109 |

### 最终Boss

| 职业 | 胜率 | 距离目标区间[0.60,0.75] | 最常见败因 |
|---|---:|---:|---|
| hero | 0.658 | 0.0pp | ignis:1:尻尾攻撃 @ round 7 |
| cleric | 0.694 | 0.0pp | ignis:1:尻尾攻撃 @ round 5 |
| mage | 0.630 | 0.0pp | ignis:1:尻尾攻撃 @ round 3 |
| thief | 0.704 | 0.0pp | ignis:1:尻尾攻撃 @ round 4 |

Boss抗性仍为physical 0.65、fire 0、ice 1.75。职业武器与元素差别、原heuristic前两回合优先第一个防御技能，会影响输出窗口；未更改抗性、旧技能或策略以迎合指标。败因计数见JSON，不把有限搜索解释为无解证明。
胜率之外仍有HP/回合越界。机制解释：低命中、大伤害骰子的配置使来伤更分散，既可能早败，也可能在多次未命中后高HP获胜；治疗进一步抬高胜利条件下的剩余HP。冰弱点、聖水与新技能爆发缩短输出窗口，而回合中位数也包含早败。上述为机制推断，不能把胜率达标等同于节奏达标。

## 2. 伤害预算（前→后）

精确骰子期望，含命中、闪避、防御、抗性与AI权重；开局全敌存活、满资源，不计先手击杀、护盾、回复和后续领域/状态。亡霊転換不属于HP伤害但仍会致败。

| 遭遇 | 上限 | pass1比例 | pass2比例 | pass2越界职业数 |
|---|---:|---|---|---:|
| dark_forest_loc | 0.150 | 12.7% / 18.5% / 27.1% / 16.6% | 10.5% / 15.0% / 21.8% / 13.0% | 1 |
| lost_goblin_crossroads | 0.150 | 11.3% / 16.5% / 24.2% / 14.7% | 10.7% / 15.6% / 22.8% / 13.7% | 2 |
| slime_ambush_one | 0.150 | 12.7% / 18.5% / 27.1% / 16.6% | 10.5% / 15.0% / 21.8% / 13.0% | 1 |
| slime_ambush_two | 0.150 | 12.7% / 18.5% / 27.1% / 16.6% | 10.5% / 15.0% / 21.8% / 13.0% | 1 |
| goblin_fort | 0.150 | 11.3% / 16.5% / 24.2% / 14.7% | 10.7% / 15.6% / 22.8% / 13.7% | 2 |
| goblin_fort_chest_fight | 0.150 | 7.6% / 10.6% / 16.1% / 9.3% | 7.1% / 10.0% / 15.2% / 8.7% | 1 |
| village_fire_slime | 0.150 | 7.6% / 10.6% / 16.3% / 9.4% | 9.2% / 11.7% / 17.8% / 11.0% | 1 |
| forest_wolves | 0.250 | 14.0% / 20.0% / 29.3% / 18.0% | 15.4% / 21.2% / 31.1% / 19.9% | 1 |
| goblin_fort_first_second | 0.250 | 18.0% / 26.2% / 38.2% / 22.7% | 19.0% / 28.8% / 42.1% / 24.6% | 2 |
| goblin_fort_second_right | 0.250 | 14.0% / 20.0% / 29.3% / 18.0% | 14.0% / 20.0% / 29.3% / 18.0% | 1 |
| goblin_fort_second_left | 0.250 | 11.9% / 18.5% / 27.1% / 15.5% | 17.2% / 22.9% / 33.5% / 22.0% | 1 |
| goblin_fort_third_guards | 0.250 | 14.0% / 20.0% / 29.3% / 18.0% | 14.0% / 20.0% / 29.3% / 18.0% | 1 |
| village_fire_elemental | 0.250 | 7.6% / 10.6% / 16.3% / 9.4% | 12.6% / 15.8% / 24.1% / 15.2% | 0 |
| ice_elemental_encounter | 0.250 | 8.5% / 11.6% / 17.8% / 10.4% | 15.7% / 19.7% / 30.3% / 19.5% | 1 |
| slime_king_battle | 0.350 | 15.8% / 22.5% / 33.0% / 20.5% | 17.5% / 25.0% / 36.8% / 23.0% | 1 |
| goblin_fort_fourth | 0.350 | 15.0% / 22.9% / 33.4% / 18.9% | 33.1% / 45.7% / 67.0% / 43.1% | 3 |
| merchant_battle | 0.350 | 14.6% / 20.8% / 30.6% / 19.2% | 15.3% / 20.4% / 29.8% / 19.7% | 0 |
| frost_wolf_battle | 0.350 | 9.0% / 12.3% / 18.9% / 11.0% | 7.9% / 10.0% / 15.2% / 9.2% | 0 |
| dragon_valley_loc | 0.350 | 17.3% / 20.5% / 31.7% / 20.9% | 13.1% / 15.2% / 23.2% / 15.0% | 0 |
| xanxus_battle | — | 80.0% / 86.6% / 133.3% / 99.1% | 80.0% / 86.6% / 133.3% / 99.1% | 0 |
| warlock_rescue_battle | — | 0.5% | 0.5% | 0 |

## 3. 完整数值与结构改动

两份剧本同步；下表路径以dragon_rpg.json为准。只修改005允许的文本、机械字段和内容版本；初始属性/资源、敌人名称/描述、抗性、遭遇类别、Xanxus/warlock战斗定义与targets保持不变。

| JSON路径 | 原值 | 新值 | 理由 |
|---|---|---|---|
| `/characters/0/level_skills` | `null` | `[{"id":"hero_lv3_a","name":"渾身斬り","kind":"attack","damage":"1d8+str/2","accuracy":92,"element":"physical","cost":3,"cost_type":"sp","description":"気合を込めた全力の一撃。","unlock_level":3,"effect":"敵に1d8+str/2ダメージを与える。"},{"id":"hero_lv5_b","name":"不屈の構え","kind":"defend","guard_multiplier":0.25,"survive_at_one":true,"cost":2,"cost_type":"sp","description":"構えを固め、致死ダメージにも耐え抜く。","unlock_level":5,"effect":"次に受けるダメージを4分の1にし、致死ダメージを受けてもHP1で耐える。"}]` | 005指定的正式技能、聖水或统一入口flag |
| `/characters/1/level_skills` | `null` | `[{"id":"cleric_lv3_a","name":"聖なる裁き","kind":"attack","damage":"1d8+wis/2","accuracy":92,"element":"holy","cost":3,"cost_type":"mp","description":"聖光で敵を攻撃する。","unlock_level":3,"effect":"敵に1d8+wis/2ダメージを与える。"},{"id":"cleric_lv5_b","name":"大いなる癒し","kind":"heal","healing":"2d6+wis/2","cost":14,"cost_type":"mp","description":"聖なる祈りで大きく傷を癒す。","unlock_level":5,"effect":"HPを2d6+wis/2回復する。"}]` | 005指定的正式技能、聖水或统一入口flag |
| `/characters/2/level_skills` | `null` | `[{"id":"mage_lv3_b","name":"火球","kind":"attack","damage":"1d8+int/2","accuracy":92,"element":"fire","cost":6,"cost_type":"mp","all_targets":true,"description":"火球で敵全体を攻撃する。","unlock_level":3,"effect":"敵全体に1d8+int/2ダメージを与える。"},{"id":"mage_lv5_a","name":"氷の矢","kind":"attack","damage":"2d8+int/2","accuracy":92,"element":"ice","cost":5,"cost_type":"mp","description":"氷の矢で敵を貫く。","unlock_level":5,"effect":"敵に2d8+int/2ダメージを与える。"}]` | 005指定的正式技能、聖水或统一入口flag |
| `/characters/3/level_skills` | `null` | `[{"id":"thief_lv3_b","name":"影隠れ","kind":"defend","guard_multiplier":0.25,"survive_at_one":true,"cost":2,"cost_type":"sp","description":"影に溶けて攻撃に備える。","unlock_level":3,"effect":"次に受けるダメージを4分の1にし、致死ダメージを受けてもHP1で耐える。"},{"id":"thief_lv5_a","name":"急所突き","kind":"attack","damage":"8d8+dex/2","accuracy":92,"element":"physical","cost":5,"cost_type":"sp","description":"敵の急所を正確に狙う。","unlock_level":5,"effect":"敵に8d8+dex/2ダメージを与える。"}]` | 005指定的正式技能、聖水或统一入口flag |
| `/enemies/0/combat/basic_attack/accuracy` | `95` | `60` | slime：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/0/combat/basic_attack/damage` | `"1d6"` | `"1d6+1"` | slime：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/0/combat/defense` | `0` | `1` | slime：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/0/hp` | `24` | `80` | slime：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/0/max_hp` | `24` | `80` | slime：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/combat/basic_attack/accuracy` | `86` | `55` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/combat/basic_attack/damage` | `"1d6+str/4"` | `"1d20"` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/combat/defense` | `2` | `1` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/combat/evade` | `3` | `8` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/hp` | `120` | `148` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/max_hp` | `120` | `148` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/skills/0/accuracy` | `80` | `55` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/skills/0/damage` | `"2d6+int/4"` | `"1d20"` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/skills/0/dice_type` | `"2d6+int/4"` | `"1d20"` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/skills/1/accuracy` | `90` | `55` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/skills/1/damage` | `"1d8+str/4"` | `"1d20"` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/1/skills/1/dice_type` | `"1d8+str/4"` | `"1d20"` | ignis：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/2/combat/basic_attack/accuracy` | `85` | `80` | goblin：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/2/combat/evade` | `8` | `1` | goblin：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/2/hp` | `24` | `84` | goblin：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/2/max_hp` | `24` | `84` | goblin：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/3/combat/basic_attack/accuracy` | `50` | `95` | goblin_archer：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/3/combat/basic_attack/damage` | `"1d6"` | `"1d4"` | goblin_archer：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/3/combat/evade` | `10` | `5` | goblin_archer：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/3/hp` | `8` | `56` | goblin_archer：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/3/max_hp` | `8` | `56` | goblin_archer：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/4/combat/defense` | `2` | `0` | hobgoblin：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/4/combat/evade` | `3` | `6` | hobgoblin：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/4/hp` | `32` | `96` | hobgoblin：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/4/max_hp` | `32` | `96` | hobgoblin：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/5/combat/basic_attack/accuracy` | `95` | `75` | war_hound：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/5/combat/basic_attack/damage` | `"1d4+1"` | `"1d10"` | war_hound：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/5/combat/defense` | `1` | `2` | war_hound：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/5/combat/evade` | `10` | `17` | war_hound：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/5/hp` | `44` | `76` | war_hound：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/5/max_hp` | `44` | `76` | war_hound：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/6/combat/basic_attack/accuracy` | `80` | `85` | forest_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/6/combat/basic_attack/damage` | `"1d6+1"` | `"1d8"` | forest_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/6/combat/defense` | `1` | `2` | forest_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/6/combat/evade` | `10` | `0` | forest_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/6/hp` | `40` | `88` | forest_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/6/max_hp` | `40` | `88` | forest_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/7/combat/basic_attack/accuracy` | `90` | `100` | slime_king：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/7/combat/defense` | `3` | `2` | slime_king：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/7/combat/evade` | `2` | `4` | slime_king：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/7/hp` | `38` | `96` | slime_king：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/7/max_hp` | `38` | `96` | slime_king：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/8/combat/basic_attack/accuracy` | `95` | `90` | goblin_king：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/8/combat/basic_attack/damage` | `"1d4"` | `"1d8+2"` | goblin_king：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/8/combat/defense` | `0` | `2` | goblin_king：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/8/combat/evade` | `5` | `1` | goblin_king：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/8/hp` | `48` | `64` | goblin_king：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/8/max_hp` | `48` | `64` | goblin_king：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/9/combat/basic_attack/accuracy` | `100` | `80` | zebok：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/9/combat/basic_attack/damage` | `"1d6+1"` | `"1d10"` | zebok：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/9/combat/defense` | `1` | `3` | zebok：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/9/combat/evade` | `8` | `17` | zebok：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/9/hp` | `-76` | `-96` | zebok：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/9/skills/0/accuracy` | `100` | `80` | zebok：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/9/skills/0/damage` | `"1d6+1"` | `"1d10"` | zebok：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/9/skills/2/accuracy` | `100` | `80` | zebok：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/9/skills/2/damage` | `"1d6+1"` | `"1d10"` | zebok：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/10/combat/basic_attack/accuracy` | `100` | `70` | fire_slime：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/10/combat/basic_attack/damage` | `"1d6"` | `"1d10"` | fire_slime：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/10/combat/evade` | `4` | `0` | fire_slime：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/10/hp` | `28` | `84` | fire_slime：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/10/max_hp` | `28` | `84` | fire_slime：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/11/combat/basic_attack/accuracy` | `100` | `80` | fire_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/11/combat/basic_attack/damage` | `"1d6"` | `"1d8+2"` | fire_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/11/combat/defense` | `1` | `4` | fire_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/11/combat/evade` | `8` | `11` | fire_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/11/hp` | `44` | `80` | fire_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/11/max_hp` | `44` | `80` | fire_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/12/combat/basic_attack/accuracy` | `85` | `100` | ice_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/12/combat/basic_attack/damage` | `"1d6+1"` | `"1d8+2"` | ice_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/12/combat/defense` | `0` | `1` | ice_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/12/combat/evade` | `7` | `5` | ice_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/12/hp` | `48` | `84` | ice_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/12/max_hp` | `48` | `84` | ice_elemental：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/13/combat/basic_attack/accuracy` | `90` | `60` | frost_dire_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/13/combat/basic_attack/damage` | `"1d6+1"` | `"1d10"` | frost_dire_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/13/combat/defense` | `1` | `2` | frost_dire_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/13/combat/evade` | `12` | `2` | frost_dire_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/13/hp` | `68` | `120` | frost_dire_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/enemies/13/max_hp` | `68` | `120` | frost_dire_wolf：补给改变后重新搜索胜率、HP、回合与职业差距，同时惩罚伤害预算超额 |
| `/items/23/description` | `"聖水"` | `"教会で清められた水。不死の存在を焼く。"` | 005指定的正式技能、聖水或统一入口flag |
| `/locations/0/actions/2/effects` | `[{"set_flag":"checked_supplies"}]` | `[{"set_flag":"checked_supplies"},{"branch":{"requirements":{"not_flag":"checked_supplies"},"then":[{"add_item":{"id":"holy_water","name":"聖水","quantity":2}}]}}]` | 005指定的正式技能、聖水或统一入口flag |
| `/locations/0/hybrid/prepared_turns` | `[{"id":"castle_departure_success","purpose":"choice_response","source_choice":"","player_intent":"go_dark_forest","trigger_keywords":[],"action_id":"go_dark_forest","outcome":"success","draft":{"gm_text":"城門を抜けると石畳は次第に細い獣道へ変わり、湿った土と苔の匂いが濃くなっていく。やがて木々が陽光を遮り、闇の森の入口で青いスライムが進路を塞いだ。","system_log":"","state_delta":{},"choices":[]},"rewrite_notes":["確定済みのアクション結果だけを自然な日本語で描写してください。"]},{"id":"castle_departure_failure","purpose":"choice_response","source_choice":"","player_intent":"go_dark_forest","trigger_keywords":[],"action_id":"go_dark_forest","outcome":"failure","draft":{"gm_text":"城門を出たところで装備の留め具が外れ、森へ入る前に引き返すことになった。支度を整え直せば、もう一度出発できる。","system_log":"","state_delta":{},"choices":[]},"rewrite_notes":["確定済みのアクション結果だけを自然な日本語で描写してください。"]}]` | `[{"id":"castle_departure_success","purpose":"choice_response","source_choice":"","player_intent":"go_dark_forest","trigger_keywords":[],"action_id":"go_dark_forest","outcome":"success","draft":{"gm_text":"城門を抜けると石畳は次第に細い獣道へ変わり、湿った土と苔の匂いが濃くなっていく。やがて木々が陽光を遮り、闇の森の入口で青いスライムが進路を塞いだ。","system_log":"","state_delta":{},"choices":[]},"rewrite_notes":["確定済みのアクション結果だけを自然な日本語で描写してください。"]},{"id":"castle_departure_failure","purpose":"choice_response","source_choice":"","player_intent":"go_dark_forest","trigger_keywords":[],"action_id":"go_dark_forest","outcome":"failure","draft":{"gm_text":"城門を出たところで装備の留め具が外れ、森へ入る前に引き返すことになった。支度を整え直せば、もう一度出発できる。","system_log":"","state_delta":{},"choices":[]},"rewrite_notes":["確定済みのアクション結果だけを自然な日本語で描写してください。"]},{"id":"check_supplies_neutral","purpose":"choice_response","action_id":"check_supplies","outcome":"neutral","draft":{"gm_text":"装備を確認し、聖水を2個受け取った。","system_log":"","state_delta":{},"choices":[]}},{"id":"ask_general_advice_success","purpose":"choice_response","action_id":"ask_general_advice","outcome":"success","draft":{"gm_text":"「不死の者には聖水が効く」と将軍は付け加えた。","system_log":"","state_delta":{},"choices":[]}},{"id":"ask_general_advice_failure","purpose":"choice_response","action_id":"ask_general_advice","outcome":"failure","draft":{"gm_text":"「不死の者には聖水が効く」と将軍は付け加えた。","system_log":"","state_delta":{},"choices":[]}}]` | 005指定的正式技能、聖水或统一入口flag |
| `/locations/3/actions/2/effects/0/flags_set` | `null` | `["entered_dragon_valley"]` | 005指定的正式技能、聖水或统一入口flag |
| `/locations/18/actions/0/effects/2/flags_set` | `null` | `["reached_village"]` | 005指定的正式技能、聖水或统一入口flag |
| `/locations/37/actions/1/effects/0/flags_set` | `null` | `["entered_dragon_valley"]` | 005指定的正式技能、聖水或统一入口flag |
| `/locations/40/actions/0/effects/2/flags_set` | `null` | `["entered_dragon_valley"]` | 005指定的正式技能、聖水或统一入口flag |
| `/locations/40/actions/1/effects/0/flags_set` | `null` | `["entered_dragon_valley"]` | 005指定的正式技能、聖水或统一入口flag |
| `/meta/content_revision` | `"2026-10-11-balance-pass1"` | `"2026-10-11-balance-pass2"` | 加载新版机械配置 |
| `/milestones/2/trigger_flag` | `"warlock_disappeared_at_village"` | `"reached_village"` | 005指定的正式技能、聖水或统一入口flag |
| `/milestones/3/trigger_flag` | `"accepted_ian_request"` | `"entered_dragon_valley"` | 005指定的正式技能、聖水或统一入口flag |

技能使用独立level_skills表，保持已有Lv1技能；在真实升级时按实际等级追加，跳到Lv4/Lv5时补齐低等级技能，同ID不重复。保留旧存档不追溯成长的规则。

## 4. 仍越界项目

| 遭遇 | 职业 | 指标 | 值 | 目标 |
|---|---|---|---:|---|
| lost_goblin_crossroads | hero | hp_left | 0.869 | [0.6, 0.85] |
| slime_ambush_one | hero | hp_left | 0.850 | [0.6, 0.85] |
| goblin_fort | hero | hp_left | 0.868 | [0.6, 0.85] |
| goblin_fort_chest_fight | hero | hp_left | 0.942 | [0.6, 0.85] |
| goblin_fort_chest_fight | cleric | hp_left | 0.881 | [0.6, 0.85] |
| goblin_fort_chest_fight | thief | hp_left | 0.891 | [0.6, 0.85] |
| forest_wolves | hero | win_rate | 0.996 | [0.75, 0.9] |
| forest_wolves | hero | hp_left | 0.706 | [0.3, 0.5] |
| forest_wolves | cleric | win_rate | 0.924 | [0.75, 0.9] |
| forest_wolves | cleric | hp_left | 0.628 | [0.3, 0.5] |
| forest_wolves | mage | hp_left | 0.648 | [0.3, 0.5] |
| forest_wolves | thief | hp_left | 0.553 | [0.3, 0.5] |
| goblin_fort_first_second | hero | win_rate | 1.000 | [0.75, 0.9] |
| goblin_fort_first_second | hero | hp_left | 0.699 | [0.3, 0.5] |
| goblin_fort_first_second | hero | rounds | 11.000 | [4, 7] |
| goblin_fort_first_second | cleric | win_rate | 0.910 | [0.75, 0.9] |
| goblin_fort_first_second | cleric | hp_left | 0.639 | [0.3, 0.5] |
| goblin_fort_first_second | cleric | rounds | 17.000 | [4, 7] |
| goblin_fort_first_second | mage | win_rate | 0.546 | [0.75, 0.9] |
| goblin_fort_first_second | mage | hp_left | 0.507 | [0.3, 0.5] |
| goblin_fort_first_second | mage | rounds | 8.000 | [4, 7] |
| goblin_fort_first_second | thief | win_rate | 0.516 | [0.75, 0.9] |
| goblin_fort_first_second | thief | rounds | 11.000 | [4, 7] |
| goblin_fort_second_right | hero | win_rate | 1.000 | [0.75, 0.9] |
| goblin_fort_second_right | hero | hp_left | 0.722 | [0.3, 0.5] |
| goblin_fort_second_right | cleric | win_rate | 0.960 | [0.75, 0.9] |
| goblin_fort_second_right | cleric | hp_left | 0.631 | [0.3, 0.5] |
| goblin_fort_second_right | mage | hp_left | 0.635 | [0.3, 0.5] |
| goblin_fort_second_right | thief | hp_left | 0.567 | [0.3, 0.5] |
| goblin_fort_second_left | hero | win_rate | 0.926 | [0.75, 0.9] |
| goblin_fort_second_left | hero | hp_left | 0.689 | [0.3, 0.5] |
| goblin_fort_second_left | cleric | win_rate | 0.748 | [0.75, 0.9] |
| goblin_fort_second_left | cleric | hp_left | 0.681 | [0.3, 0.5] |
| goblin_fort_second_left | mage | win_rate | 0.656 | [0.75, 0.9] |
| goblin_fort_second_left | mage | hp_left | 0.717 | [0.3, 0.5] |
| goblin_fort_second_left | thief | win_rate | 0.636 | [0.75, 0.9] |
| goblin_fort_second_left | thief | hp_left | 0.610 | [0.3, 0.5] |
| goblin_fort_third_guards | hero | win_rate | 0.998 | [0.75, 0.9] |
| goblin_fort_third_guards | hero | hp_left | 0.713 | [0.3, 0.5] |
| goblin_fort_third_guards | cleric | win_rate | 0.970 | [0.75, 0.9] |
| goblin_fort_third_guards | cleric | hp_left | 0.640 | [0.3, 0.5] |
| goblin_fort_third_guards | mage | hp_left | 0.619 | [0.3, 0.5] |
| goblin_fort_third_guards | thief | hp_left | 0.546 | [0.3, 0.5] |
| village_fire_elemental | hero | win_rate | 0.970 | [0.75, 0.9] |
| village_fire_elemental | hero | hp_left | 0.605 | [0.3, 0.5] |
| village_fire_elemental | cleric | win_rate | 0.908 | [0.75, 0.9] |
| village_fire_elemental | mage | hp_left | 0.549 | [0.3, 0.5] |
| village_fire_elemental | thief | win_rate | 0.566 | [0.75, 0.9] |
| ice_elemental_encounter | hero | win_rate | 0.984 | [0.75, 0.9] |
| ice_elemental_encounter | hero | hp_left | 0.535 | [0.3, 0.5] |
| ice_elemental_encounter | cleric | win_rate | 0.956 | [0.75, 0.9] |
| ice_elemental_encounter | mage | win_rate | 0.904 | [0.75, 0.9] |
| slime_king_battle | hero | win_rate | 0.982 | [0.6, 0.75] |
| slime_king_battle | hero | hp_left | 0.555 | [0.15, 0.4] |
| slime_king_battle | cleric | hp_left | 0.477 | [0.15, 0.4] |
| slime_king_battle | mage | hp_left | 0.521 | [0.15, 0.4] |
| slime_king_battle | mage | rounds | 5.000 | [7, 12] |
| slime_king_battle | thief | win_rate | 0.414 | [0.6, 0.75] |
| goblin_fort_fourth | hero | win_rate | 0.988 | [0.6, 0.75] |
| goblin_fort_fourth | hero | hp_left | 0.645 | [0.15, 0.4] |
| goblin_fort_fourth | cleric | hp_left | 0.602 | [0.15, 0.4] |
| goblin_fort_fourth | cleric | rounds | 15.000 | [7, 12] |
| goblin_fort_fourth | mage | hp_left | 0.571 | [0.15, 0.4] |
| goblin_fort_fourth | thief | hp_left | 0.435 | [0.15, 0.4] |
| merchant_battle | hero | hp_left | 0.870 | [0.15, 0.4] |
| merchant_battle | hero | rounds | 4.000 | [7, 12] |
| merchant_battle | cleric | win_rate | 0.792 | [0.6, 0.75] |
| merchant_battle | cleric | hp_left | 0.929 | [0.15, 0.4] |
| merchant_battle | cleric | rounds | 2.000 | [7, 12] |
| merchant_battle | mage | hp_left | 0.850 | [0.15, 0.4] |
| merchant_battle | mage | rounds | 2.000 | [7, 12] |
| merchant_battle | thief | hp_left | 0.853 | [0.15, 0.4] |
| merchant_battle | thief | rounds | 4.000 | [7, 12] |
| frost_wolf_battle | hero | win_rate | 0.958 | [0.6, 0.75] |
| frost_wolf_battle | hero | hp_left | 0.487 | [0.15, 0.4] |
| frost_wolf_battle | cleric | win_rate | 0.830 | [0.6, 0.75] |
| frost_wolf_battle | cleric | rounds | 13.000 | [7, 12] |
| frost_wolf_battle | mage | win_rate | 0.916 | [0.6, 0.75] |
| frost_wolf_battle | mage | hp_left | 0.551 | [0.15, 0.4] |
| frost_wolf_battle | mage | rounds | 6.000 | [7, 12] |
| dragon_valley_loc | hero | hp_left | 0.428 | [0.15, 0.4] |
| dragon_valley_loc | hero | attack_only_win_rate | 0.436 | [0, 0.2] |
| dragon_valley_loc | cleric | hp_left | 0.528 | [0.15, 0.4] |
| dragon_valley_loc | cleric | attack_only_win_rate | 0.248 | [0, 0.2] |
| dragon_valley_loc | mage | hp_left | 0.570 | [0.15, 0.4] |
| dragon_valley_loc | mage | rounds | 4.000 | [7, 12] |
| dragon_valley_loc | thief | hp_left | 0.487 | [0.15, 0.4] |
| dragon_valley_loc | thief | rounds | 5.000 | [7, 12] |
| forest_wolves | all | class_spread | 0.220 | [0, 0.15] |
| goblin_fort_first_second | all | class_spread | 0.484 | [0, 0.25] |
| goblin_fort_second_right | all | class_spread | 0.220 | [0, 0.15] |
| goblin_fort_second_left | all | class_spread | 0.290 | [0, 0.15] |
| goblin_fort_third_guards | all | class_spread | 0.214 | [0, 0.15] |
| village_fire_elemental | all | class_spread | 0.404 | [0, 0.15] |
| ice_elemental_encounter | all | class_spread | 0.210 | [0, 0.15] |
| slime_king_battle | all | class_spread | 0.568 | [0, 0.15] |
| goblin_fort_fourth | all | class_spread | 0.364 | [0, 0.25] |
| frost_wolf_battle | all | class_spread | 0.354 | [0, 0.15] |

共享模板约束：slime覆盖三场，goblin/hobgoblin覆盖不同等级、数量的遭遇；单一模板不能分别拟合每个checkpoint。护甲、元素抗性、有限MP/SP和同伴周期回复共同造成职业差别。

## 5. 正式技能效果

使用最终敌人、同伴与补给配置，仅移除8个新技能；不回退成长或旧技能。消融计算全部heuristic与Boss attack_only；其他类别没有普攻胜率上限，不重复计算。正式--check矩阵仍覆盖全部162cell。

| 遭遇 | 无新技能平均胜率 | 正式技能平均胜率 | 越界无→有 |
|---|---:|---:|---|
| dark_forest_loc | 0.978 | 0.978 | 0→0 |
| lost_goblin_crossroads | 0.997 | 0.997 | 1→1 |
| slime_ambush_one | 0.984 | 0.984 | 1→1 |
| slime_ambush_two | 0.979 | 0.979 | 0→0 |
| goblin_fort | 0.995 | 0.995 | 1→1 |
| goblin_fort_chest_fight | 1.000 | 1.000 | 3→3 |
| village_fire_slime | 0.998 | 0.998 | 0→0 |
| forest_wolves | 0.868 | 0.868 | 7→7 |
| goblin_fort_first_second | 0.743 | 0.743 | 12→12 |
| goblin_fort_second_right | 0.885 | 0.885 | 7→7 |
| goblin_fort_second_left | 0.742 | 0.742 | 9→9 |
| goblin_fort_third_guards | 0.885 | 0.885 | 7→7 |
| village_fire_elemental | 0.817 | 0.831 | 6→6 |
| ice_elemental_encounter | 0.891 | 0.904 | 4→5 |
| slime_king_battle | 0.675 | 0.675 | 7→7 |
| goblin_fort_fourth | 0.728 | 0.728 | 7→7 |
| merchant_battle | 0.705 | 0.705 | 9→9 |
| frost_wolf_battle | 0.833 | 0.827 | 9→8 |
| dragon_valley_loc | 0.435 | 0.671 | 10→8 |
| xanxus_battle | 0.000 | 0.000 | 0→0 |
| warlock_rescue_battle | 1.000 | 1.000 | 0→0 |

## 6. TODO(design)

- TODO(design): 建议将商人战单列目标：现有两瓶聖水的通用解法要求两次命中，胜利通常2或4回合。建议回合[2,5]、胜利HP[0.50,1.00]，胜率目标仍保留[0.60,0.75]；或另行设计持续圣属性解法。未改targets。
- TODO(design): 建议把杂兵回合改为[1,4]并区分消耗强力道具的胜利HP（可放宽至1.00），同时单独报告道具消耗。现在一瓶固定36伤害会秒杀低HP敌人，单战满补给要求敌人HP明显提高才能满足下限，可能扭曲连续冒险。
- TODO(design): 建议对proposed checkpoint增加跨战斗消耗路线对照；两瓶聖水在每场都存在且策略直接按伤害优先使用，不能外推为全流程通关表现。本轮严格执行指定补给，不擅自新增保留物品的策略。
- TODO(design): 建议同伴10–20pp继续按有同伴的56cell等权均值验收；杂兵接近100%存在天花板，不要求每场单独达到10pp。
- TODO(design): 同伴旧叙述仍写每回合8HP，历史多敌叙述可能与004的数量调整不一致；需设计统一文本。005未授权修改这些叙述。
- TODO(design): 新技能和旧技能有同名（渾身斬り、影隠れ、火球、氷の矢、急所突き），新防御技能位于旧技能之后，既有heuristic常选择旧技能。建议另行审定替换/升级关系与策略；本轮保留指定名字、原技能与原策略。

- TODO(design): 审定已达Lv5旧存档的新技能迁移；自动补发需要区分历史clear_skills等剧情效果，本轮未追溯补发。

- TODO(design): 当前proposed路线的多敌砦战发生于Lv1，Lv3全体火球在这组checkpoint中缺少多敌施展窗口；如需验证范围攻击的定位，请审定后续多敌遭遇或路线。

## 7. 推断、偏离与已知限制

- 将“商人战之前的遭遇”解释为主路线出发先check_supplies；所有非guest checkpoint因此持有2瓶，后期也不假设历史消耗。来源是实际动作重放，不额外注入。
- 现有村庄入口为forest_exit→village_approach；竜の谷有village、post_xanxus、ian_clearing接受/拒绝共4条入口。只补flags_set，不改入口文本或增设路线。
- 新技能作为增量技能保留Lv1技能；原候选ID沿用，以unlock_level表示门槛，未将同名技能隐式替换。技能/物品名与提示文字按005定稿，技能一句描述为005授权撰写。
- 将军成功与失败结果都加指定提示，均不发物品；check_supplies沿用once，并在物品效果中加not_flag条件，防直接重复执行造成补发。
- 搜索按共享敌人分组，以越界数量、区间距离及伤害预算超额评分；有限搜索不是全局最优。正式N=500是确认样本，闭区间附近有抽样不确定性，约70%胜率的标准误差约2pp。
- 旧存档没有level仍视为Lv1且不追溯成长；已到Lv5的旧存档不会自动补发新技能，需要设计审定迁移方式，当前交付按新游戏路径验证。
- 未改变数值目标、玩家初始数值、抗性、原技能、AI策略或剧情战定义；部分目标仍越界，属于未达到的数值目标，不伪报全通过。

## 8. 工程交付与验证

- 引擎host/state.py；两份dragon_rpg剧本及schema；checkpoint与模拟技能还原；pass2搜索、正式矩阵、消融和本报告生成器；对应离线测试与README。无新增依赖。
- 文件清单：`host/state.py`；`host/prompt/processed/dragon_rpg.json`、`dragon_rpg_hybrid.json`、`scenario_pack.schema.json`。
- 模拟代码：`scripts/balance/checkpoints.py`、`sim.py`、`pass2.py`、`pass2_report.py`；测试：`tests/test_balance_pass2.py`、`tests/test_dragon_story.py`。
- 评测文件：`eval/balance/README.md`、`checkpoints.json`、`pass2-search.json`；报告：`eval/reports/balance-2026-10-11-pass2.md`及同名JSON。
- `python -m unittest discover -s tests -q`：295项，294通过、1项按原有BALANCE_ENFORCE条件跳过；`node --check client/app.js`与`git diff --check`通过。
- `python -m scripts.balance.sim --check --n 500`：98项越界，预期退出码1；相比pass1的124项下降。
- 正式runner调用sim.main的--check入口，保留真实退出码及矩阵，随后计算同伴/技能对照，避免重复运行同一检查。
- 两份剧本的本轮机械差分一致；初始资源/属性/旧技能、敌人名称/描述/抗性、剧情战与targets均经对照核验。JSON保留正式矩阵、技能消融、伤害预算、完整变更、败因和输入/代码SHA256。

## 9. 目标合理性建议

下列只是交由设计负责人审定的建议，未修改targets.json。理由与机制限制详见第4、6节。

| 项目 | 建议 | 依据 |
|---|---|---|
| 商人回合/胜利HP | 单列回合[2,5]、HP[0.50,1.00] | 两瓶聖水的通用解法是两次命中，强行拉长会失去可靠终结手段 |
| 杂兵回合/胜利HP | 回合[1,4]；消耗强力道具时允许HP上限1.00 | 固定36伤害聖水会一击结束弱敌；应额外报告道具消耗 |
| 同伴提升 | 保持56个有同伴cell等权平均10–20pp | 杂兵100%胜率的天花板使逐遭遇要求不合理 |
| 连续流程 | 增加扣除历史消耗的路线评测，暂不设新数值阈值 | 当前满资源、两瓶聖水的独立战斗不能代表连续闯关 |
