# 004 第一轮平衡报告

全部为离线真实战斗引擎，flat 防御，无 API 调用、无新增依赖。
正式确认 N=500 / cell，seed=20261011。调整后 405 cell / 202,500 场，墙钟 212.7 秒。
调整前复用 002 的 N=500 原始 CSV（基线 `bff766865a76dcea309928008e69720f1991e3ce`），不重新抽样；只比较 flat、相同策略及 checkpoint 口径。
小样本先 N=16 粗筛，再 N=64 复核候选；正式 N=500 不再用于选择参数。搜索记录见 `eval/balance/pass1-search.json`。

复现：

```powershell
python -m scripts.balance.checkpoints
python -m scripts.balance.pass1 --n 500 --output eval/reports/balance-2026-10-11-pass1.json
python -m scripts.balance.pass1_report
python -m scripts.balance.sim --check --n 500
python -m scripts.balance.sim --check --n 500 --skills A
```

checkpoint 仍为 proposed；各战独立回满资源、假定前序战斗获胜、不扣历史消耗，不代表连续通关率。

## 1. 前后达标情况

002 原检查口径越界 **170** 项；采用 targets.json 已有多敌职业差距 0.25 后，基线 **170** 项；调整后无新技能 **124** 项，候选 A **129** 项。未修改 targets.json。
全指标达标要求所有职业通过胜率、胜利剩余 HP、回合、职业差距、Boss 普攻上限。

| 类别 | 总数 | 原全指标 | 后全指标 | A全指标 | 原仅胜率 | 后仅胜率 | A仅胜率 |
|---|---:|---:|---:|---:|---:|---:|---:|
| trash | 7 | 0 | 0 | 0 | 6 | 7 | 7 |
| elite | 7 | 0 | 0 | 0 | 0 | 0 | 0 |
| boss | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| scripted_loss | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| guest | 1 | 1 | 1 | 1 | 1 | 1 | 1 |

### 各遭遇（heuristic；职业顺序 hero / cleric / mage / thief，guest 为 warlock）

| 遭遇 | Lv | 原胜率 | 后胜率 | 原→后职业差距 | 原→后越界项 | 后回合 | 后胜利HP |
|---|---|---|---|---|---|---|---|
| dark_forest_loc | 1 | 1.000 / 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 0.998 / 0.982 | 0.000→0.018 | 7→1 | 3.000 / 4.000 / 2.000 / 3.000 | 0.877 / 0.703 / 0.824 / 0.750 |
| lost_goblin_crossroads | 1 | 1.000 / 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 / 0.994 | 0.000→0.006 | 5→1 | 3.000 / 4.000 / 2.000 / 3.000 | 0.887 / 0.746 / 0.832 / 0.792 |
| slime_ambush_one | 1 | 1.000 / 0.990 / 0.966 / 1.000 | 1.000 / 1.000 / 1.000 / 0.990 | 0.034→0.010 | 5→1 | 3.000 / 4.000 / 2.000 / 3.000 | 0.885 / 0.705 / 0.817 / 0.755 |
| slime_ambush_two | 1 | 1.000 / 0.988 / 0.980 / 0.998 | 1.000 / 1.000 / 0.996 / 0.992 | 0.020→0.008 | 5→1 | 3.000 / 4.000 / 2.000 / 3.000 | 0.874 / 0.701 / 0.822 / 0.731 |
| goblin_fort | 1 | 1.000 / 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 0.988 / 0.992 | 0.000→0.012 | 5→1 | 3.000 / 4.000 / 2.000 / 3.000 | 0.888 / 0.737 / 0.834 / 0.788 |
| goblin_fort_chest_fight | 3 | 1.000 / 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 / 1.000 | 0.000→0.000 | 5→4 | 3.000 / 4.000 / 2.000 / 4.000 | 0.966 / 0.863 / 0.910 / 0.893 |
| village_fire_slime | 4 | 0.998 / 0.606 / 0.978 / 0.852 | 1.000 / 1.000 / 1.000 / 1.000 | 0.392→0.000 | 6→1 | 2.000 / 4.000 / 2.000 / 4.000 | 0.887 / 0.648 / 0.850 / 0.703 |
| forest_wolves | 1 | 1.000 / 0.152 / 0.616 / 0.868 | 0.996 / 0.926 / 0.870 / 0.734 | 0.848→0.262 | 8→9 | 5.000 / 9.000 / 4.000 / 6.000 | 0.691 / 0.623 / 0.648 / 0.540 |
| goblin_fort_first_second | 1 | 0.858 / 0.010 / 0.314 / 0.514 | 1.000 / 0.914 / 0.906 / 0.860 | 0.848→0.140 | 10→8 | 5.000 / 7.000 / 3.000 / 5.000 | 0.795 / 0.700 / 0.739 / 0.673 |
| goblin_fort_second_right | 1 | 1.000 / 0.934 / 0.908 / 1.000 | 1.000 / 0.954 / 0.956 / 0.870 | 0.092→0.130 | 10→9 | 4.000 / 8.000 / 3.000 / 5.000 | 0.744 / 0.637 / 0.682 / 0.583 |
| goblin_fort_second_left | 1 | 0.880 / 0.000 / 0.164 / 0.708 | 1.000 / 1.000 / 0.954 / 0.864 | 0.880→0.136 | 12→8 | 6.000 / 10.000 / 5.000 / 7.000 | 0.757 / 0.597 / 0.633 / 0.524 |
| goblin_fort_third_guards | 1 | 0.008 / 0.000 / 0.002 / 0.000 | 1.000 / 0.964 / 0.930 / 0.848 | 0.008→0.152 | 12→10 | 5.000 / 8.000 / 3.000 / 5.000 | 0.743 / 0.639 / 0.672 / 0.590 |
| village_fire_elemental | 4 | 0.332 / 0.000 / 0.202 / 0.004 | 1.000 / 1.000 / 1.000 / 0.944 | 0.332→0.056 | 8→8 | 4.000 / 9.000 / 2.000 / 7.000 | 0.790 / 0.469 / 0.771 / 0.464 |
| ice_elemental_encounter | 4 | 0.006 / 0.000 / 0.144 / 0.000 | 0.994 / 1.000 / 1.000 / 0.918 | 0.144→0.082 | 9→8 | 5.000 / 8.000 / 3.000 / 7.000 | 0.679 / 0.469 / 0.712 / 0.447 |
| slime_king_battle | 1 | 1.000 / 1.000 / 0.986 / 1.000 | 0.992 / 0.654 / 0.908 / 0.466 | 0.014→0.526 | 14→12 | 8.000 / 13.000 / 3.000 / 8.000 | 0.621 / 0.507 / 0.645 / 0.429 |
| goblin_fort_fourth | 1 | 0.396 / 0.000 / 0.078 / 0.084 | 0.988 / 0.662 / 0.652 / 0.636 | 0.396→0.352 | 13→10 | 9.000 / 12.000 / 6.000 / 9.000 | 0.684 / 0.632 / 0.675 / 0.526 |
| merchant_battle | 1 | 0.000 / 0.000 / 0.000 / 0.000 | 0.870 / 0.998 / 0.840 / 0.868 | 0.000→0.158 | 12→13 | 4.000 / 2.000 / 2.000 / 4.000 | 0.906 / 0.938 / 0.837 / 0.885 |
| frost_wolf_battle | 4 | 0.000 / 0.000 / 0.000 / 0.000 | 0.878 / 0.656 / 0.942 / 0.304 | 0.000→0.638 | 12→9 | 10.000 / 17.000 / 5.000 / 10.000 | 0.433 / 0.293 / 0.474 / 0.233 |
| dragon_valley_loc | 5 | 0.000 / 0.002 / 0.004 / 0.000 | 0.426 / 0.350 / 0.356 / 0.000 | 0.004→0.426 | 12→10 | 7.000 / 15.000 / 5.000 / 5.000 | 0.217 / 0.307 / 0.291 / — |
| xanxus_battle | 4 | 0.000 / 0.000 / 0.000 / 0.000 | 0.000 / 0.000 / 0.000 / 0.000 | 0.000→0.000 | 0→0 | 3.000 / 3.000 / 1.000 / 3.000 | — / — / — / — |
| warlock_rescue_battle | 1 | 1.000 | 1.000 | 0.000→0.000 | 0→0 | 5.000 | 1.000 |

### 同伴效果

仅纳入 checkpoint 实际携带蓝袍法师的 56 个职业×遭遇 cell；离队和 guest 不稀释均值。每2回合在第2、4、6…回合开始回复最大HP的15%，四舍五入。

| 遭遇 | 原平均提升pp | 后平均提升pp | 后各职业提升pp |
|---|---:|---:|---|
| dark_forest_loc | 0.00 | 1.20 | 0.000 / 0.000 / 0.800 / 4.000 |
| lost_goblin_crossroads | 1.10 | 1.45 | 0.000 / 0.000 / 2.000 / 3.800 |
| slime_ambush_one | 20.85 | 1.45 | 0.000 / 0.000 / 1.800 / 4.000 |
| slime_ambush_two | 20.75 | 1.55 | 0.000 / 0.000 / 1.000 / 5.200 |
| goblin_fort | 1.15 | 1.10 | 0.000 / 0.000 / 1.800 / 2.600 |
| goblin_fort_chest_fight | 1.00 | 0.05 | 0.000 / 0.000 / 0.000 / 0.200 |
| forest_wolves | 49.35 | 11.45 | 4.200 / 3.800 / 13.600 / 24.200 |
| goblin_fort_first_second | 36.35 | 9.25 | 3.000 / 10.200 / 8.800 / 15.000 |
| goblin_fort_second_right | 60.95 | 8.15 | 1.200 / 2.400 / 10.400 / 18.600 |
| goblin_fort_second_left | 41.95 | 13.20 | 0.800 / 1.200 / 14.000 / 36.800 |
| goblin_fort_third_guards | 0.25 | 6.20 | 0.600 / 2.600 / 6.000 / 15.600 |
| slime_king_battle | 71.70 | 26.20 | 12.000 / 55.400 / 9.600 / 27.800 |
| goblin_fort_fourth | 13.95 | 29.30 | 18.000 / 46.800 / 15.400 / 37.000 |
| merchant_battle | 0.00 | 0.15 | 0.000 / 0.600 / 0.000 / 0.000 |

同伴等权平均提升：**22.81 → 7.91 个百分点**；目标 10–20pp，未达标。逐遭遇不保证均落入该区间；杂兵胜率接近100%时有天花板效应。

## 2. 伤害预算（前→后）

按每种骰子离散分布精确求期望，含命中、闪避、防御、抗性和敌人AI权重。假定敌人全存活、满资源、满HP，未计玩家先手击杀、护盾或回复。表中为每职业期望伤害/该 checkpoint 最大HP。
商人亡霊転換不记为HP伤害，但仍会致败；Xanxus领域、治疗及后续状态不在开局直接伤害预算中，剧情/guest没有预算目标。

| 遭遇 | 上限 | 前比例（四职业） | 后比例（四职业） | 后越界职业数 |
|---|---:|---|---|---:|
| dark_forest_loc | 0.150 | 10.0% / 15.6% / 22.8% / 12.9% | 12.7% / 18.5% / 27.1% / 16.6% | 3 |
| lost_goblin_crossroads | 0.150 | 14.9% / 21.2% / 31.1% / 19.3% | 11.3% / 16.5% / 24.2% / 14.7% | 2 |
| slime_ambush_one | 0.150 | 30.0% / 46.7% / 68.2% / 38.6% | 12.7% / 18.5% / 27.1% / 16.6% | 3 |
| slime_ambush_two | 0.150 | 30.0% / 46.7% / 68.2% / 38.6% | 12.7% / 18.5% / 27.1% / 16.6% | 3 |
| goblin_fort | 0.150 | 14.9% / 21.2% / 31.1% / 19.3% | 11.3% / 16.5% / 24.2% / 14.7% | 2 |
| goblin_fort_chest_fight | 0.150 | 14.9% / 21.2% / 31.1% / 19.3% | 7.6% / 10.6% / 16.1% / 9.3% | 1 |
| village_fire_slime | 0.150 | 15.0% / 21.5% / 31.5% / 19.5% | 7.6% / 10.6% / 16.3% / 9.4% | 1 |
| forest_wolves | 0.250 | 39.6% / 53.8% / 78.8% / 51.4% | 14.0% / 20.0% / 29.3% / 18.0% | 1 |
| goblin_fort_first_second | 0.250 | 54.5% / 75.0% / 110.0% / 70.7% | 18.0% / 26.2% / 38.2% / 22.7% | 2 |
| goblin_fort_second_right | 0.250 | 26.7% / 34.2% / 50.0% / 34.4% | 14.0% / 20.0% / 29.3% / 18.0% | 1 |
| goblin_fort_second_left | 0.250 | 55.0% / 85.6% / 125.4% / 71.4% | 11.9% / 18.5% / 27.1% / 15.5% | 1 |
| goblin_fort_third_guards | 0.250 | 80.0% / 102.5% / 150.0% / 103.1% | 14.0% / 20.0% / 29.3% / 18.0% | 1 |
| village_fire_elemental | 0.250 | 33.0% / 41.6% / 60.9% / 42.9% | 7.6% / 10.6% / 16.3% / 9.4% | 0 |
| ice_elemental_encounter | 0.250 | 33.0% / 41.6% / 60.9% / 42.9% | 8.5% / 11.6% / 17.8% / 10.4% | 0 |
| slime_king_battle | 0.350 | 22.5% / 29.6% / 43.3% / 29.1% | 15.8% / 22.5% / 33.0% / 20.5% | 0 |
| goblin_fort_fourth | 0.350 | 72.6% / 95.3% / 139.8% / 94.3% | 15.0% / 22.9% / 33.4% / 18.9% | 0 |
| merchant_battle | 0.350 | 69.3% / 80.9% / 118.4% / 89.6% | 14.6% / 20.8% / 30.6% / 19.2% | 0 |
| frost_wolf_battle | 0.350 | 58.5% / 70.0% / 102.7% / 76.1% | 9.0% / 12.3% / 18.9% / 11.0% | 0 |
| dragon_valley_loc | 0.350 | 34.6% / 43.3% / 63.4% / 44.9% | 17.3% / 20.5% / 31.7% / 20.9% | 0 |
| xanxus_battle | — | 140.0% / 158.7% / 233.3% / 184.0% | 80.0% / 86.6% / 133.3% / 99.1% | 0 |
| warlock_rescue_battle | — | 0.5% | 0.5% | 0 |

## 3. 完整数值与结构改动

两份剧本同步修改下列机械字段，叙事、敌人名称/描述、初始HP/MP/SP/属性、分类、Xanxus与warlock数据保持原值。以下路径以 dragon_rpg.json 为准。

| JSON路径 | 原值 | 新值 | 理由 |
|---|---|---|---|
| `/characters/1/combat/basic_attack/damage` | `"1d4+str/4"` | `"1d8+wis/4"` | 聖なる杖期望7.5=Lv1鉄の剣8.5−1；holy属性（原本已holy） |
| `/companions/1/round_start_effects/0/amount` | `"8"` | `null` | 原同伴提升22.81pp，按设计改为每2回合15%最大HP |
| `/companions/1/round_start_effects/0/every_n_rounds` | `null` | `2` | 原同伴提升22.81pp，按设计改为每2回合15%最大HP |
| `/companions/1/round_start_effects/0/max_hp_ratio` | `null` | `0.15` | 原同伴提升22.81pp，按设计改为每2回合15%最大HP |
| `/enemies/0/combat/basic_attack/accuracy` | `80` | `95` | slime：原越界 hp_left, rounds；联合搜索全部共用此敌人的遭遇 |
| `/enemies/0/combat/basic_attack/damage` | `"1d4+str/4"` | `"1d6"` | slime：原越界 hp_left, rounds；联合搜索全部共用此敌人的遭遇 |
| `/enemies/0/hp` | `5` | `24` | slime：原越界 hp_left, rounds；联合搜索全部共用此敌人的遭遇 |
| `/enemies/0/max_hp` | `5` | `24` | slime：原越界 hp_left, rounds；联合搜索全部共用此敌人的遭遇 |
| `/enemies/2/combat/basic_attack/damage` | `"1d4+dex/4"` | `"1d6"` | goblin：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/2/hp` | `15` | `24` | goblin：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/2/max_hp` | `15` | `24` | goblin：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/3/combat/basic_attack/accuracy` | `88` | `50` | goblin_archer：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/3/combat/basic_attack/damage` | `"1d6+dex/5"` | `"1d6"` | goblin_archer：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/3/combat/defense` | `0` | `1` | goblin_archer：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/3/hp` | `12` | `8` | goblin_archer：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/3/max_hp` | `12` | `8` | goblin_archer：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/4/combat/basic_attack/accuracy` | `82` | `80` | hobgoblin：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/4/combat/basic_attack/damage` | `"1d8+str/4"` | `"1d6+1"` | hobgoblin：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/4/hp` | `30` | `32` | hobgoblin：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/4/max_hp` | `30` | `32` | hobgoblin：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/5/combat/basic_attack/accuracy` | `88` | `95` | war_hound：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/5/combat/basic_attack/damage` | `"1d4+str/4"` | `"1d4+1"` | war_hound：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/5/combat/defense` | `0` | `1` | war_hound：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/5/hp` | `10` | `44` | war_hound：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/5/max_hp` | `10` | `44` | war_hound：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/6/combat/basic_attack/accuracy` | `88` | `80` | forest_wolf：原越界 class_spread, hp_left, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/6/combat/basic_attack/damage` | `"1d6+str/4"` | `"1d6+1"` | forest_wolf：原越界 class_spread, hp_left, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/6/hp` | `18` | `40` | forest_wolf：原越界 class_spread, hp_left, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/6/max_hp` | `18` | `40` | forest_wolf：原越界 class_spread, hp_left, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/7/combat/basic_attack/accuracy` | `82` | `90` | slime_king：原越界 attack_only_win_rate, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/7/combat/basic_attack/damage` | `"1d8+str/4"` | `"1d6+1"` | slime_king：原越界 attack_only_win_rate, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/7/combat/defense` | `2` | `3` | slime_king：原越界 attack_only_win_rate, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/8/combat/basic_attack/accuracy` | `88` | `95` | goblin_king：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/8/combat/basic_attack/damage` | `"1d10+str/4"` | `"1d4"` | goblin_king：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/8/combat/defense` | `3` | `0` | goblin_king：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/8/hp` | `55` | `48` | goblin_king：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/8/max_hp` | `55` | `48` | goblin_king：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/9/combat/basic_attack/accuracy` | `88` | `100` | zebok：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/9/combat/basic_attack/damage` | `"1d6+int/4"` | `"1d6+1"` | zebok：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/9/combat/defense` | `0` | `1` | zebok：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/9/hp` | `-100` | `-76` | zebok：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/9/skills/0/accuracy` | `82` | `100` | zebok：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/9/skills/0/damage` | `"7d4"` | `"1d6+1"` | zebok：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/9/skills/2/accuracy` | `85` | `100` | zebok：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/9/skills/2/damage` | `"2d6+int"` | `"1d6+1"` | zebok：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/10/combat/basic_attack/accuracy` | `86` | `100` | fire_slime：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/10/combat/basic_attack/damage` | `"1d6+int/4"` | `"1d6"` | fire_slime：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/10/combat/defense` | `1` | `0` | fire_slime：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/10/hp` | `24` | `28` | fire_slime：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/10/max_hp` | `24` | `28` | fire_slime：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/11/combat/basic_attack/accuracy` | `88` | `100` | fire_elemental：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/11/combat/basic_attack/damage` | `"1d8+int/4"` | `"1d6"` | fire_elemental：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/11/combat/defense` | `2` | `1` | fire_elemental：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/11/hp` | `48` | `44` | fire_elemental：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/11/max_hp` | `48` | `44` | fire_elemental：原越界 class_spread, hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/12/combat/basic_attack/accuracy` | `88` | `85` | ice_elemental：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/12/combat/basic_attack/damage` | `"1d8+int/4"` | `"1d6+1"` | ice_elemental：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/12/combat/defense` | `3` | `0` | ice_elemental：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/12/hp` | `52` | `48` | ice_elemental：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/12/max_hp` | `52` | `48` | ice_elemental：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/13/combat/basic_attack/damage` | `"2d8+str/4"` | `"1d6+1"` | frost_dire_wolf：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/13/combat/defense` | `5` | `1` | frost_dire_wolf：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/13/hp` | `140` | `68` | frost_dire_wolf：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/enemies/13/max_hp` | `140` | `68` | frost_dire_wolf：原越界 hp_left, rounds, win_rate；联合搜索全部共用此敌人的遭遇 |
| `/items` | `无holy_water` | `{"id": "holy_water", "name": "聖水", "description": "聖水", "combat": {"kind": "damage", "damage": "36", "accuracy": 100, "element": "holy", "consumable": true}}` | TODO(design): 聖水占位；仅商人checkpoint 2个；保证两次命中可抵消负HP，未接发放动作 |
| `/locations/14/combat/enemy_ids` | `["forest_wolf","forest_wolf"]` | `["forest_wolf"]` | 多敌期望伤害超预算；先减数量并保留敌人种类，再搜索个体伤害/命中 |
| `/locations/15/combat/enemy_ids` | `["slime","slime","slime"]` | `["slime"]` | 多敌期望伤害超预算；先减数量并保留敌人种类，再搜索个体伤害/命中 |
| `/locations/16/combat/enemy_ids` | `["slime","slime","slime"]` | `["slime"]` | 多敌期望伤害超预算；先减数量并保留敌人种类，再搜索个体伤害/命中 |
| `/locations/20/combat/enemy_ids` | `["goblin","goblin_archer","goblin_archer"]` | `["goblin","goblin_archer"]` | 多敌期望伤害超预算；先减数量并保留敌人种类，再搜索个体伤害/命中 |
| `/locations/23/combat/enemy_ids` | `["war_hound","war_hound","war_hound","war_hound","war_hound"]` | `["war_hound"]` | 多敌期望伤害超预算；先减数量并保留敌人种类，再搜索个体伤害/命中 |
| `/locations/26/combat/enemy_ids` | `["hobgoblin","hobgoblin","hobgoblin"]` | `["hobgoblin"]` | 多敌期望伤害超预算；先减数量并保留敌人种类，再搜索个体伤害/命中 |
| `/locations/27/combat/enemy_ids` | `["goblin_king","goblin_archer","goblin_archer"]` | `["goblin_king","goblin_archer"]` | 多敌期望伤害超预算；先减数量并保留敌人种类，再搜索个体伤害/命中 |
| `/meta/content_revision` | `"2026-09-08-death-game-over"` | `"2026-10-11-balance-pass1"` | 内容版本升级，使旧存档加载新机械配置；旧flag不补发成长 |
| `/milestones` | `无milestones` | `新增lv2–lv5；详细gains见下表与同名JSON changes` | 按每级基础HP25%、MP/SP15%、主+2副+1实现成长；四舍五入 |

| 职业 | 每次HP/MP/SP上限增量 | 主/副属性 |
|---|---|---|
| hero | 5 / 1 / 2 | {'str': 2, 'end': 1} |
| cleric | 5 / 2 / 1 | {'wis': 2, 'int': 1} |
| mage | 3 / 3 / 1 | {'int': 2, 'wis': 1} |
| thief | 4 / 1 / 2 | {'dex': 2, 'str': 1} |

## 4. 仍越界项目

下列为正式N=500全部越界，不能理解为本次搜索证明数值无解。

| 遭遇 | 职业 | 指标 | 值 | 目标 |
|---|---|---|---:|---|
| dark_forest_loc | hero | hp_left | 0.877 | [0.6, 0.85] |
| lost_goblin_crossroads | hero | hp_left | 0.887 | [0.6, 0.85] |
| slime_ambush_one | hero | hp_left | 0.885 | [0.6, 0.85] |
| slime_ambush_two | hero | hp_left | 0.874 | [0.6, 0.85] |
| goblin_fort | hero | hp_left | 0.888 | [0.6, 0.85] |
| goblin_fort_chest_fight | hero | hp_left | 0.966 | [0.6, 0.85] |
| goblin_fort_chest_fight | cleric | hp_left | 0.863 | [0.6, 0.85] |
| goblin_fort_chest_fight | mage | hp_left | 0.910 | [0.6, 0.85] |
| goblin_fort_chest_fight | thief | hp_left | 0.893 | [0.6, 0.85] |
| village_fire_slime | hero | hp_left | 0.887 | [0.6, 0.85] |
| forest_wolves | hero | win_rate | 0.996 | [0.75, 0.9] |
| forest_wolves | hero | hp_left | 0.691 | [0.3, 0.5] |
| forest_wolves | cleric | win_rate | 0.926 | [0.75, 0.9] |
| forest_wolves | cleric | hp_left | 0.623 | [0.3, 0.5] |
| forest_wolves | cleric | rounds | 9.000 | [4, 7] |
| forest_wolves | mage | hp_left | 0.648 | [0.3, 0.5] |
| forest_wolves | thief | win_rate | 0.734 | [0.75, 0.9] |
| forest_wolves | thief | hp_left | 0.540 | [0.3, 0.5] |
| goblin_fort_first_second | hero | win_rate | 1.000 | [0.75, 0.9] |
| goblin_fort_first_second | hero | hp_left | 0.795 | [0.3, 0.5] |
| goblin_fort_first_second | cleric | win_rate | 0.914 | [0.75, 0.9] |
| goblin_fort_first_second | cleric | hp_left | 0.700 | [0.3, 0.5] |
| goblin_fort_first_second | mage | win_rate | 0.906 | [0.75, 0.9] |
| goblin_fort_first_second | mage | hp_left | 0.739 | [0.3, 0.5] |
| goblin_fort_first_second | mage | rounds | 3.000 | [4, 7] |
| goblin_fort_first_second | thief | hp_left | 0.673 | [0.3, 0.5] |
| goblin_fort_second_right | hero | win_rate | 1.000 | [0.75, 0.9] |
| goblin_fort_second_right | hero | hp_left | 0.744 | [0.3, 0.5] |
| goblin_fort_second_right | cleric | win_rate | 0.954 | [0.75, 0.9] |
| goblin_fort_second_right | cleric | hp_left | 0.637 | [0.3, 0.5] |
| goblin_fort_second_right | cleric | rounds | 8.000 | [4, 7] |
| goblin_fort_second_right | mage | win_rate | 0.956 | [0.75, 0.9] |
| goblin_fort_second_right | mage | hp_left | 0.682 | [0.3, 0.5] |
| goblin_fort_second_right | mage | rounds | 3.000 | [4, 7] |
| goblin_fort_second_right | thief | hp_left | 0.583 | [0.3, 0.5] |
| goblin_fort_second_left | hero | win_rate | 1.000 | [0.75, 0.9] |
| goblin_fort_second_left | hero | hp_left | 0.757 | [0.3, 0.5] |
| goblin_fort_second_left | cleric | win_rate | 1.000 | [0.75, 0.9] |
| goblin_fort_second_left | cleric | hp_left | 0.597 | [0.3, 0.5] |
| goblin_fort_second_left | cleric | rounds | 10.000 | [4, 7] |
| goblin_fort_second_left | mage | win_rate | 0.954 | [0.75, 0.9] |
| goblin_fort_second_left | mage | hp_left | 0.633 | [0.3, 0.5] |
| goblin_fort_second_left | thief | hp_left | 0.524 | [0.3, 0.5] |
| goblin_fort_third_guards | hero | win_rate | 1.000 | [0.75, 0.9] |
| goblin_fort_third_guards | hero | hp_left | 0.743 | [0.3, 0.5] |
| goblin_fort_third_guards | cleric | win_rate | 0.964 | [0.75, 0.9] |
| goblin_fort_third_guards | cleric | hp_left | 0.639 | [0.3, 0.5] |
| goblin_fort_third_guards | cleric | rounds | 8.000 | [4, 7] |
| goblin_fort_third_guards | mage | win_rate | 0.930 | [0.75, 0.9] |
| goblin_fort_third_guards | mage | hp_left | 0.672 | [0.3, 0.5] |
| goblin_fort_third_guards | mage | rounds | 3.000 | [4, 7] |
| goblin_fort_third_guards | thief | hp_left | 0.590 | [0.3, 0.5] |
| village_fire_elemental | hero | win_rate | 1.000 | [0.75, 0.9] |
| village_fire_elemental | hero | hp_left | 0.790 | [0.3, 0.5] |
| village_fire_elemental | cleric | win_rate | 1.000 | [0.75, 0.9] |
| village_fire_elemental | cleric | rounds | 9.000 | [4, 7] |
| village_fire_elemental | mage | win_rate | 1.000 | [0.75, 0.9] |
| village_fire_elemental | mage | hp_left | 0.771 | [0.3, 0.5] |
| village_fire_elemental | mage | rounds | 2.000 | [4, 7] |
| village_fire_elemental | thief | win_rate | 0.944 | [0.75, 0.9] |
| ice_elemental_encounter | hero | win_rate | 0.994 | [0.75, 0.9] |
| ice_elemental_encounter | hero | hp_left | 0.679 | [0.3, 0.5] |
| ice_elemental_encounter | cleric | win_rate | 1.000 | [0.75, 0.9] |
| ice_elemental_encounter | cleric | rounds | 8.000 | [4, 7] |
| ice_elemental_encounter | mage | win_rate | 1.000 | [0.75, 0.9] |
| ice_elemental_encounter | mage | hp_left | 0.712 | [0.3, 0.5] |
| ice_elemental_encounter | mage | rounds | 3.000 | [4, 7] |
| ice_elemental_encounter | thief | win_rate | 0.918 | [0.75, 0.9] |
| slime_king_battle | hero | win_rate | 0.992 | [0.6, 0.75] |
| slime_king_battle | hero | hp_left | 0.621 | [0.15, 0.4] |
| slime_king_battle | hero | attack_only_win_rate | 0.936 | [0, 0.2] |
| slime_king_battle | cleric | hp_left | 0.507 | [0.15, 0.4] |
| slime_king_battle | cleric | rounds | 13.000 | [7, 12] |
| slime_king_battle | mage | win_rate | 0.908 | [0.6, 0.75] |
| slime_king_battle | mage | hp_left | 0.645 | [0.15, 0.4] |
| slime_king_battle | mage | rounds | 3.000 | [7, 12] |
| slime_king_battle | thief | win_rate | 0.466 | [0.6, 0.75] |
| slime_king_battle | thief | hp_left | 0.429 | [0.15, 0.4] |
| slime_king_battle | thief | attack_only_win_rate | 0.288 | [0, 0.2] |
| goblin_fort_fourth | hero | win_rate | 0.988 | [0.6, 0.75] |
| goblin_fort_fourth | hero | hp_left | 0.684 | [0.15, 0.4] |
| goblin_fort_fourth | hero | attack_only_win_rate | 0.942 | [0, 0.2] |
| goblin_fort_fourth | cleric | hp_left | 0.632 | [0.15, 0.4] |
| goblin_fort_fourth | cleric | attack_only_win_rate | 0.304 | [0, 0.2] |
| goblin_fort_fourth | mage | hp_left | 0.675 | [0.15, 0.4] |
| goblin_fort_fourth | mage | rounds | 6.000 | [7, 12] |
| goblin_fort_fourth | thief | hp_left | 0.526 | [0.15, 0.4] |
| goblin_fort_fourth | thief | attack_only_win_rate | 0.528 | [0, 0.2] |
| merchant_battle | hero | win_rate | 0.870 | [0.6, 0.75] |
| merchant_battle | hero | hp_left | 0.906 | [0.15, 0.4] |
| merchant_battle | hero | rounds | 4.000 | [7, 12] |
| merchant_battle | cleric | win_rate | 0.998 | [0.6, 0.75] |
| merchant_battle | cleric | hp_left | 0.938 | [0.15, 0.4] |
| merchant_battle | cleric | rounds | 2.000 | [7, 12] |
| merchant_battle | mage | win_rate | 0.840 | [0.6, 0.75] |
| merchant_battle | mage | hp_left | 0.837 | [0.15, 0.4] |
| merchant_battle | mage | rounds | 2.000 | [7, 12] |
| merchant_battle | thief | win_rate | 0.868 | [0.6, 0.75] |
| merchant_battle | thief | hp_left | 0.885 | [0.15, 0.4] |
| merchant_battle | thief | rounds | 4.000 | [7, 12] |
| frost_wolf_battle | hero | win_rate | 0.878 | [0.6, 0.75] |
| frost_wolf_battle | hero | hp_left | 0.433 | [0.15, 0.4] |
| frost_wolf_battle | cleric | rounds | 17.000 | [7, 12] |
| frost_wolf_battle | mage | win_rate | 0.942 | [0.6, 0.75] |
| frost_wolf_battle | mage | hp_left | 0.474 | [0.15, 0.4] |
| frost_wolf_battle | mage | rounds | 5.000 | [7, 12] |
| frost_wolf_battle | thief | win_rate | 0.304 | [0.6, 0.75] |
| frost_wolf_battle | thief | attack_only_win_rate | 0.300 | [0, 0.2] |
| dragon_valley_loc | hero | win_rate | 0.426 | [0.6, 0.75] |
| dragon_valley_loc | hero | attack_only_win_rate | 0.306 | [0, 0.2] |
| dragon_valley_loc | cleric | win_rate | 0.350 | [0.6, 0.75] |
| dragon_valley_loc | cleric | rounds | 15.000 | [7, 12] |
| dragon_valley_loc | mage | win_rate | 0.356 | [0.6, 0.75] |
| dragon_valley_loc | mage | rounds | 5.000 | [7, 12] |
| dragon_valley_loc | thief | win_rate | 0.000 | [0.6, 0.75] |
| dragon_valley_loc | thief | hp_left | — | [0.15, 0.4] |
| dragon_valley_loc | thief | rounds | 5.000 | [7, 12] |
| forest_wolves | all | class_spread | 0.262 | [0, 0.15] |
| goblin_fort_third_guards | all | class_spread | 0.152 | [0, 0.15] |
| slime_king_battle | all | class_spread | 0.526 | [0, 0.15] |
| goblin_fort_fourth | all | class_spread | 0.352 | [0, 0.25] |
| merchant_battle | all | class_spread | 0.158 | [0, 0.15] |
| frost_wolf_battle | all | class_spread | 0.638 | [0, 0.15] |
| dragon_valley_loc | all | class_spread | 0.426 | [0, 0.15] |

机制/结构限制：
- 同一 slime 同时用于森林入口与连续波次，同一 goblin/hobgoblin 用于不同等级/人数遭遇；调模板会牵动多场，不引入专属敌人变体。
- 杂兵的短回合、同伴周期回复与剩余HP上限相互制约：勇者有护甲且输出较高，降低来伤以满足低HP职业预算，会让勇者剩余HP超过85%。N=32局部增伤复查增加了其他职业/预算越界，因此未采用；这不是全空间无解证明。
- 勇者 checkpoint 已换氷鉄の大剣，元素敌人抗性和职业输出不同；霜狼对勇者冰剑免疫。只改敌人HP/防御无法同时消除元素免疫或职业解法差距。
- Boss 前两回合启用护盾的既有 heuristic 与普攻上限存在张力；商人还存在亡霊転換、诅咒装备及圣水耗尽后普通伤害反向加深负HP。
- 商人只有两枚直接伤害聖水的通用解法：两次命中即结束时，常见胜利回合为2或4，难满足7–12回合；若负HP增加到两瓶总伤害之外，非圣职业又失去稳定终结手段。需要设计审定持续圣属性解法、物品作用或战斗结构，未在本轮擅自扩展。
- 砦与狼/史莱姆为互斥森林分支；现有村庄flag依赖蓝袍同行、谷入口flag依赖接受イアン。未经设计决定，不新增路线或强行给所有checkpoint统一等级。
- 同伴说明仍写每回合8HP，多敌叙述仍可能提原数量；本任务禁止修改叙事，已留TODO(design)。

## 5. 技能候选A效果

Lv3/Lv5每职业各A、B，共16个候选，使用现有技能字段和已有日语名称；完整效果见 `eval/balance/skill_candidates.json`。同名仅为候选占位，尚未加入剧本。

| 遭遇 | 无技能胜率均值 | A胜率均值 | 无→A越界项 |
|---|---:|---:|---|
| dark_forest_loc | 0.995 | 0.995 | 1→1 |
| lost_goblin_crossroads | 0.998 | 0.998 | 1→1 |
| slime_ambush_one | 0.998 | 0.998 | 1→1 |
| slime_ambush_two | 0.997 | 0.997 | 1→1 |
| goblin_fort | 0.995 | 0.995 | 1→1 |
| goblin_fort_chest_fight | 1.000 | 1.000 | 4→4 |
| village_fire_slime | 1.000 | 1.000 | 1→3 |
| forest_wolves | 0.881 | 0.881 | 9→9 |
| goblin_fort_first_second | 0.920 | 0.920 | 8→8 |
| goblin_fort_second_right | 0.945 | 0.945 | 9→9 |
| goblin_fort_second_left | 0.955 | 0.955 | 8→8 |
| goblin_fort_third_guards | 0.935 | 0.935 | 10→10 |
| village_fire_elemental | 0.986 | 1.000 | 8→9 |
| ice_elemental_encounter | 0.978 | 0.999 | 8→9 |
| slime_king_battle | 0.755 | 0.755 | 12→12 |
| goblin_fort_fourth | 0.735 | 0.735 | 10→10 |
| merchant_battle | 0.894 | 0.894 | 13→13 |
| frost_wolf_battle | 0.695 | 0.809 | 9→10 |
| dragon_valley_loc | 0.283 | 0.320 | 10→10 |
| xanxus_battle | 0.000 | 0.000 | 0→0 |
| warlock_rescue_battle | 1.000 | 1.000 | 0→0 |

## 6. TODO(design) 与发放候选

- 审定16项技能候选（A为输出、B为守护/回复/范围输出），名称、成本、伤害与最终解锁；不将A自动转正。
- 聖水名称/描述均占位，伤害36、holy、命中100（实际仍扣敌闪避）、消耗品。两枚理论命中总伤害108，可覆盖原ゼボク−100HP；仅模拟发放，不代表保证获胜。
- 发放候选1：`castle/check_supplies`，出发前按所有职业一次性免费领取2枚；该地点是所有职业起点。
- 发放候选2：`castle/ask_general_advice`，与既有将军对话后免费领取2枚；同样各职业可达，需确保领取不会被跳过。
- 发放候选3：`alley_night` 的既有职业商人对话，在 `betray_cursed_merchant` 之前统一赠2枚；这是所有职业进入商人战前必经地点，赠予动机需设计确认。
- 审定互斥路线里程碑的补足规则、村庄/谷入口缺失的通用flag；审定数值改动与剩余目标冲突，更新同伴和人数叙述。

## 7. 推断、偏离与已知限制

- Lv2选 defeated_slime_king，狼支线采用引擎已有 combat_defeated:forest_wolves:forest_wolf 作同一里程碑替代flag；Lv3选 cleared_goblin_fort；Lv4选 warlock_disappeared_at_village；Lv5选 accepted_ian_request。后两者最接近节点但并非覆盖全部路线，明确保留设计TODO。
- 新角色按到达节点的等级差累计每级增量，例如砦首次到Lv3累计两级；低级节点迟到不重复成长。旧存档已有flag的最高节点以下只消费不补发，后续仅发更高节点的新增等级。该跨分支解释需设计复核。
- 基础值取原角色模板，每级HP25%、MP/SP15%均采用floor(x+0.5)，避免Python银行家舍入；同伴回复也采用该规则，首次第2回合。
- 杖的“期望减1”解释为Lv1未计命中/抗性/防御的公式均值，wis随成长提高；未改变初始角色资源与属性。
- 搜索目标使用真实引擎所有适用越界项及区间距离加权，固定种子；不是全空间最优证明。正式N=500仍有抽样误差，建议设计审定后独立种子再验证。
- 伤害预算以开局全敌存活为统一可复现口径；对状态/领域注明未覆盖，不能替代真实胜率。
- 发放候选均为现有地点/动作，魔法店/道具屋虽可达但不是商人战必经，因此未声称全路线都会取得。
- 偏离：通用入口flag需设计决定，当前严格使用已有flag；部分预算/目标仍越界，未改机制、抗性、初始属性、剧情战或targets来强行通过。
- 同名JSON保留完整正式矩阵、预算、变更和输入代码SHA256。

## 8. 工程交付与验证

- 引擎：`host/state.py`、`host/combat.py`、`host/scenario_context.py`；数据：两份dragon_rpg剧本与scenario_pack.schema.json。
- 模拟：`scripts/balance/checkpoints.py`、`sim.py`、`budget.py`、`pass1.py`、`pass1_report.py`；候选、搜索记录与checkpoint位于eval/balance，正式结果为本报告及同名JSON。
- 测试：`tests/test_balance_pass.py`新增10项，`tests/test_dragon_story.py`同步已授权数值断言；文档为`docs/api-free-actions.md`和`eval/balance/README.md`。无新增依赖。
- `python -m unittest discover -s tests -q`：288项，287通过、1项按原有BALANCE_ENFORCE条件跳过。
- `node --check client/app.js`、`git diff --check`：通过。
- `python -m scripts.balance.sim --check --n 500`：退出1，124项越界；加`--skills A`：退出1，129项越界。数值未全达标，不把退出1隐去。
- 两份剧本逐字段核对：叙事、初始资源/属性、敌人名字/描述、Xanxus/warlock、分类及targets未改；全部正式cell的N、总场数、输入/代码SHA256和越界计数复核通过。
- 提交按工程前缀，具体提交号见最终汇报。
