# 007 第三轮平衡报告

离线真实战斗引擎，flat 防御，无外部 API，无新增依赖。
正式 N=500 / cell，seed=20261011；243 cell。先 N=16 粗筛，再 N=64 复核，锁定参数后 N=500 确认。
搜索记录见 `eval/balance/pass3-search.json`；正式矩阵与输入/代码 SHA256 见同名 JSON；连续流程逐职业逐路线结果见 `balance-2026-10-11-pass3-routes.json`。
单场与连续流程分别报告。单场仍按 proposed checkpoint 满 HP/MP/SP、两瓶聖水起步；连续流程重放同一 checkpoint 的 sources，真实战斗替换 @victory/@defeat，不再注入下一场快照。

复现：

```powershell
python -m scripts.balance.checkpoints
python -m scripts.balance.pass3 --apply eval/balance/pass3-search.json --output .tmp-test/pass3-apply.json
python -m scripts.balance.pass3 --n 500 --output .tmp-test/pass3-reconfirm.json
python -m scripts.balance.route --n 500 --routes all --output .tmp-test/pass3-routes-reconfirm.json
python -m scripts.balance.pass3_report
python -m scripts.balance.sim --check --n 500 --output .tmp-test/pass3-check.json
```

上述确认复用归档搜索参数，不覆盖归档基线。搜索复现应从 JSON 的 baseline_commit 开始，先应用本轮技能/策略/文本改动，再执行 --search --iterations 100；另外通过 --refine-elites 对纯精英模板补充100个候选，合并各组最优参数，记录在search JSON的elite_refinement中。在最终数值上重搜属于新实验。Windows 沙箱使用 --shard/--shards 分片，计算及 seed 与不分片相同。

## 1. 达标对比

`--check` 越界：pass2 原目标 **98** → pass2 按本轮目标重算 **61** → pass3 **77**。
本轮未修改 targets.json。历史对比同时包含目标、策略、技能与敌人数值的变化，不归因于单一因素。
全指标包含 heuristic 胜率/胜利剩余 HP/全部战斗回合中位数、职业差距及 Boss 普攻胜率上限；同伴均值单列验收。

| 类别 | 总数 | pass2原目标全指标 | pass2新目标全指标 | pass3全指标 | pass2仅胜率 | pass3仅胜率 |
|---|---:|---:|---:|---:|---:|---:|
| trash | 7 | 3 | 7 | 4 | 7 | 7 |
| elite | 7 | 0 | 0 | 0 | 0 | 0 |
| boss | 5 | 0 | 0 | 0 | 1 | 1 |
| scripted_loss | 1 | 1 | 1 | 1 | 1 | 1 |
| guest | 1 | 1 | 1 | 1 | 1 | 1 |

职业顺序 hero / cleric / mage / thief；guest 为 warlock。

| 遭遇 | Lv | pass2胜率 | pass3胜率 | pass3回合 | pass3胜利HP | 新目标越界前→后 |
|---|---:|---|---|---|---|---|
| dark_forest_loc | 1 | 1.000 / 0.996 / 0.958 / 0.956 | 1.000 / 1.000 / 0.998 / 1.000 | 3.000 / 4.000 / 2.000 / 3.000 | 0.915 / 0.771 / 0.873 / 0.830 | 0→0 |
| lost_goblin_crossroads | 1 | 1.000 / 1.000 / 0.994 / 0.994 | 1.000 / 1.000 / 1.000 / 1.000 | 1.000 / 2.000 / 1.000 / 2.000 | 0.955 / 0.861 / 0.969 / 0.909 | 0→2 |
| slime_ambush_one | 1 | 1.000 / 0.992 / 0.966 / 0.976 | 1.000 / 1.000 / 0.998 / 0.996 | 3.000 / 4.000 / 2.000 / 3.000 | 0.918 / 0.778 / 0.876 / 0.836 | 0→0 |
| slime_ambush_two | 1 | 1.000 / 0.994 / 0.970 / 0.952 | 1.000 / 1.000 / 1.000 / 0.998 | 3.000 / 4.000 / 2.000 / 3.000 | 0.907 / 0.785 / 0.884 / 0.832 | 0→0 |
| goblin_fort | 1 | 1.000 / 1.000 / 0.988 / 0.992 | 1.000 / 1.000 / 0.998 / 0.996 | 1.000 / 2.000 / 1.000 / 2.000 | 0.966 / 0.857 / 0.962 / 0.906 | 0→2 |
| goblin_fort_chest_fight | 3 | 1.000 / 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 / 2.000 | 0.994 / 0.984 / 0.982 / 0.953 | 0→4 |
| village_fire_slime | 4 | 1.000 / 1.000 / 0.994 / 0.996 | 1.000 / 1.000 / 1.000 / 1.000 | 2.000 / 3.000 / 2.000 / 4.000 | 0.943 / 0.887 / 0.908 / 0.845 | 0→0 |
| forest_wolves | 1 | 0.996 / 0.924 / 0.776 / 0.776 | 0.976 / 0.814 / 0.832 / 0.708 | 4.000 / 7.000 / 3.000 / 4.000 | 0.715 / 0.675 / 0.732 / 0.628 | 4→6 |
| goblin_fort_first_second | 1 | 1.000 / 0.910 / 0.546 / 0.516 | 0.984 / 0.786 / 0.706 / 0.678 | 4.000 / 6.000 / 3.000 / 4.000 | 0.653 / 0.596 / 0.664 / 0.521 | 9→5 |
| goblin_fort_second_right | 1 | 1.000 / 0.960 / 0.780 / 0.798 | 1.000 / 1.000 / 0.904 / 0.798 | 6.000 / 10.000 / 4.000 / 6.000 | 0.705 / 0.612 / 0.621 / 0.496 | 4→6 |
| goblin_fort_second_left | 1 | 0.926 / 0.748 / 0.656 / 0.636 | 0.970 / 0.772 / 0.804 / 0.664 | 4.000 / 7.000 / 3.000 / 4.000 | 0.712 / 0.666 / 0.732 / 0.601 | 6→6 |
| goblin_fort_third_guards | 1 | 0.998 / 0.970 / 0.784 / 0.790 | 1.000 / 1.000 / 0.888 / 0.822 | 6.000 / 10.000 / 4.000 / 6.000 | 0.722 / 0.606 / 0.643 / 0.490 | 4→5 |
| village_fire_elemental | 4 | 0.970 / 0.908 / 0.880 / 0.566 | 0.966 / 0.798 / 0.838 / 0.556 | 3.000 / 3.000 / 2.000 / 4.000 | 0.650 / 0.570 / 0.630 / 0.413 | 4→6 |
| ice_elemental_encounter | 4 | 0.984 / 0.956 / 0.904 / 0.774 | 0.918 / 0.888 / 0.916 / 0.756 | 4.000 / 4.000 / 2.000 / 5.000 | 0.669 / 0.680 / 0.845 / 0.593 | 4→5 |
| slime_king_battle | 1 | 0.982 / 0.652 / 0.654 / 0.414 | 0.930 / 0.710 / 0.684 / 0.642 | 6.000 / 7.000 / 3.000 / 5.000 | 0.583 / 0.551 / 0.610 / 0.490 | 6→8 |
| goblin_fort_fourth | 1 | 0.988 / 0.670 / 0.628 / 0.624 | 0.968 / 0.626 / 0.540 / 0.640 | 7.000 / 8.000 / 4.000 / 6.000 | 0.581 / 0.581 / 0.592 / 0.442 | 6→8 |
| merchant_battle | 1 | 0.672 / 0.792 / 0.692 / 0.662 | 0.672 / 0.792 / 0.692 / 0.662 | 4.000 / 2.000 / 2.000 / 4.000 | 0.870 / 0.929 / 0.850 / 0.853 | 1→1 |
| frost_wolf_battle | 4 | 0.958 / 0.830 / 0.916 / 0.604 | 0.976 / 0.834 / 0.896 / 0.590 | 10.000 / 12.000 / 6.000 / 10.000 | 0.474 / 0.402 / 0.529 / 0.353 | 7→7 |
| dragon_valley_loc | 5 | 0.658 / 0.694 / 0.630 / 0.704 | 0.632 / 0.650 / 0.640 / 0.706 | 7.000 / 9.000 / 4.000 / 5.000 | 0.413 / 0.527 / 0.567 / 0.489 | 6→6 |
| xanxus_battle | 4 | 0.000 / 0.000 / 0.000 / 0.000 | 0.000 / 0.000 / 0.000 / 0.000 | 3.000 / 3.000 / 1.000 / 3.000 | — / — / — / — | 0→0 |
| warlock_rescue_battle | 1 | 1.000 | 1.000 | 5.000 | 1.000 | 0→0 |

### 同伴等权均值

| 遭遇 | 平均胜率提升 pp |
|---|---:|
| dark_forest_loc | 0.85 |
| lost_goblin_crossroads | 0.20 |
| slime_ambush_one | 0.65 |
| slime_ambush_two | 0.60 |
| goblin_fort | 0.10 |
| goblin_fort_chest_fight | 0.05 |
| forest_wolves | 6.55 |
| goblin_fort_first_second | 16.80 |
| goblin_fort_second_right | 12.00 |
| goblin_fort_second_left | 8.90 |
| goblin_fort_third_guards | 12.00 |
| slime_king_battle | 16.45 |
| goblin_fort_fourth | 32.45 |
| merchant_battle | 1.60 |

56 个实际有同伴 cell 等权均值 **7.80pp**；目标10–20pp；越界。保持每2回合回复最大 HP 的15%，与007指定描述一致。

## 2. 每场消耗品

heuristic、每次试验平均消耗；职业顺序同上，空对象表示零消耗。详细逐职业值在 JSON 的 consumables_mean。
稀有规则仅过滤 trash/elite 的消耗品：rare=true、圣/光属性（含 multi_elements），或对任一存活敌人的单次期望净伤害达到其最大HP绝对值的30%。期望使用现有模拟伤害估计，含命中/闪避/防御/抗性与多段。Boss 可使用。

| 遭遇 | 平均消耗（各职业） |
|---|---|
| dark_forest_loc | {} / {"薬草":0.042} / {"薬草":0.038} / {} |
| lost_goblin_crossroads | {} / {"薬草":0.016} / {"薬草":0.012} / {} |
| slime_ambush_one | {} / {"薬草":0.05} / {"薬草":0.046} / {} |
| slime_ambush_two | {} / {"薬草":0.06} / {"薬草":0.044} / {} |
| goblin_fort | {} / {"薬草":0.018} / {"薬草":0.014} / {} |
| goblin_fort_chest_fight | {} / {} / {} / {} |
| village_fire_slime | {} / {} / {} / {} |
| forest_wolves | {"薬草":0.12} / {"薬草":0.722} / {"薬草":0.306} / {} |
| goblin_fort_first_second | {"薬草":0.174} / {"薬草":1.054} / {"薬草":0.492} / {} |
| goblin_fort_second_right | {"薬草":0.032} / {"薬草":0.98} / {"薬草":0.404} / {} |
| goblin_fort_second_left | {"薬草":0.148} / {"薬草":0.832} / {"薬草":0.344} / {} |
| goblin_fort_third_guards | {"薬草":0.038} / {"薬草":0.944} / {"薬草":0.43} / {} |
| village_fire_elemental | {"薬草":0.19} / {"薬草":0.58} / {"薬草":0.298} / {} |
| ice_elemental_encounter | {"薬草":0.212} / {"薬草":0.306} / {"薬草":0.154} / {} |
| slime_king_battle | {"聖水":2.0,"薬草":0.248} / {"聖水":2.0,"薬草":0.836} / {"聖水":2.0,"薬草":0.462} / {"聖水":2.0} |
| goblin_fort_fourth | {"聖水":1.99,"薬草":0.42} / {"聖水":1.722,"薬草":1.056} / {"聖水":1.74,"薬草":0.58} / {"聖水":1.936} |
| merchant_battle | {"聖水":2.0,"薬草":0.242} / {"聖水":2.0,"薬草":0.386} / {"聖水":2.0,"薬草":0.238} / {"聖水":2.0} |
| frost_wolf_battle | {"聖水":2.0,"薬草":0.42} / {"聖水":2.0,"薬草":1.444} / {"聖水":2.0,"薬草":0.522} / {"聖水":2.0} |
| dragon_valley_loc | {"聖水":2.0,"薬草":0.618} / {"聖水":2.0,"薬草":0.718} / {"薬草":0.464} / {"聖水":2.0} |
| xanxus_battle | {"聖水":0.262,"薬草":0.546} / {"薬草":0.818} / {"聖水":1.472} / {"聖水":0.684} |
| warlock_rescue_battle | {} |

## 3. 连续流程

全部21个 checkpoint 路线各运行 N=500 × 4个起始职业；每个分支独立起步。主线通关定义为 dragon_valley_loc 路线击败最终 Boss。战败立即终止，scripted_loss 按剧本败北效果继续；guest 使用引擎角色替换/还原。
不增加购物、休息或分支决策；按 sources 中指定的成功/失败结果重放非战斗动作，故结果是给定路线/非战斗判定条件下的通关率。恢复只来自实际动作、战斗机制、剧情效果和升级。路线不存在的宿屋或回复阵不会凭空补入。

| 职业 | 主线通关率 | 最常见失败点（次数/500） | 到达Boss人数 | 到达时平均HP/MP/SP | 平均剩余聖水 |
|---|---:|---|---:|---|---:|
| hero | 0.248 | ["frost_wolf_battle",176] | 272 | 40.000 / 12.000 / 18.000 | 0.000 |
| cleric | 0.056 | ["frost_wolf_battle",207] | 62 | 38.000 / 22.000 / 12.000 | 0.000 |
| mage | 0.216 | ["frost_wolf_battle",147] | 172 | 24.000 / 32.000 / 10.000 | 0.000 |
| thief | 0.012 | ["forest_wolves",266] | 26 | 30.000 / 10.000 / 22.000 | 0.000 |

最终 Boss 入口触发 Lv5，真实升级会补满资源；该入口均值不能代表之前没有消耗。完整背包均值、失败分布及逐战消耗保存在 routes JSON。

| 路线终点 | hero通达/完成率 | cleric | mage | thief |
|---|---:|---:|---:|---:|
| dark_forest_loc | 1.000 | 1.000 | 0.998 | 1.000 |
| lost_goblin_crossroads | 1.000 | 1.000 | 0.996 | 0.984 |
| forest_wolves | 0.962 | 0.694 | 0.698 | 0.480 |
| slime_ambush_one | 1.000 | 1.000 | 0.984 | 0.978 |
| slime_ambush_two | 1.000 | 1.000 | 0.946 | 0.934 |
| slime_king_battle | 0.882 | 0.488 | 0.436 | 0.338 |
| goblin_fort | 1.000 | 1.000 | 0.974 | 0.970 |
| goblin_fort_first_second | 0.968 | 0.536 | 0.518 | 0.312 |
| goblin_fort_second_right | 0.842 | 0.488 | 0.162 | 0.036 |
| goblin_fort_second_left | 0.790 | 0.320 | 0.218 | 0.064 |
| goblin_fort_third_guards | 0.750 | 0.364 | 0.004 | 0.002 |
| goblin_fort_fourth | 0.238 | 0.058 | 0.000 | 0.000 |
| goblin_fort_chest_fight | 0.246 | 0.048 | 0.000 | 0.000 |
| village_fire_slime | 0.948 | 0.720 | 0.672 | 0.498 |
| village_fire_elemental | 0.902 | 0.568 | 0.626 | 0.246 |
| xanxus_battle | 0.956 | 0.694 | 0.706 | 0.452 |
| warlock_rescue_battle | 0.952 | 0.728 | 0.698 | 0.436 |
| ice_elemental_encounter | 0.882 | 0.540 | 0.618 | 0.276 |
| frost_wolf_battle | 0.496 | 0.124 | 0.338 | 0.070 |
| dragon_valley_loc | 0.248 | 0.056 | 0.216 | 0.012 |
| merchant_battle | 0.672 | 0.792 | 0.692 | 0.662 |

主线失败完整分布：

| 职业 | 失败场次及次数 |
|---|---|
| hero | {"ice_elemental_encounter":39,"frost_wolf_battle":176,"dragon_valley_loc":148,"forest_wolves":13} |
| cleric | {"forest_wolves":156,"ice_elemental_encounter":75,"frost_wolf_battle":207,"dragon_valley_loc":34} |
| mage | {"frost_wolf_battle":147,"forest_wolves":142,"dragon_valley_loc":64,"lost_goblin_crossroads":4,"ice_elemental_encounter":34,"dark_forest_loc":1} |
| thief | {"forest_wolves":266,"frost_wolf_battle":123,"dragon_valley_loc":20,"ice_elemental_encounter":74,"lost_goblin_crossroads":11} |

## 4. 改动清单

两份剧本相同字段同步。以下路径以 dragon_rpg.json 为准；JSON另存机器可读完整差分。未改玩家初始属性/资源、旧技能定义、抗性、敌人名称/描述、遭遇类别、xanxus/warlock战斗定义。

### 数值与结构

| 路径 | 原值 | 新值 | 理由 |
|---|---|---|---|
| `/characters/0/level_skills/0/name` | `"渾身斬り"` | `"渾身斬り・改"` | 同名技能替换/魔法使Lv2解锁 |
| `/characters/0/level_skills/0/replaces` | `null` | `"渾身斬り"` | 同名技能替换/魔法使Lv2解锁 |
| `/characters/2/level_skills/0/name` | `"火球"` | `"火球・改"` | 同名技能替换/魔法使Lv2解锁 |
| `/characters/2/level_skills/0/replaces` | `null` | `"火球"` | 同名技能替换/魔法使Lv2解锁 |
| `/characters/2/level_skills/0/unlock_level` | `3` | `2` | 同名技能替换/魔法使Lv2解锁 |
| `/characters/2/level_skills/1/name` | `"氷の矢"` | `"氷の矢・改"` | 同名技能替换/魔法使Lv2解锁 |
| `/characters/2/level_skills/1/replaces` | `null` | `"氷の矢"` | 同名技能替换/魔法使Lv2解锁 |
| `/characters/3/level_skills/0/name` | `"影隠れ"` | `"影隠れ・改"` | 同名技能替换/魔法使Lv2解锁 |
| `/characters/3/level_skills/0/replaces` | `null` | `"影隠れ"` | 同名技能替换/魔法使Lv2解锁 |
| `/characters/3/level_skills/1/name` | `"急所突き"` | `"急所突き・改"` | 同名技能替换/魔法使Lv2解锁 |
| `/characters/3/level_skills/1/replaces` | `null` | `"急所突き"` | 同名技能替换/魔法使Lv2解锁 |
| `/enemies/0/combat/basic_attack/accuracy` | `60` | `80` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/0/combat/basic_attack/damage` | `"1d6+1"` | `"1d6"` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/0/combat/defense` | `1` | `0` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/0/combat/evade` | `5` | `10` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/0/hp` | `80` | `20` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/0/max_hp` | `80` | `20` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/1/combat/defense` | `1` | `2` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/1/combat/evade` | `8` | `4` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/1/hp` | `148` | `152` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/1/max_hp` | `148` | `152` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/2/combat/basic_attack/accuracy` | `80` | `100` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/2/combat/defense` | `0` | `2` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/2/combat/evade` | `1` | `12` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/2/hp` | `84` | `8` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/2/max_hp` | `84` | `8` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/3/combat/basic_attack/accuracy` | `95` | `100` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/3/combat/basic_attack/damage` | `"1d4"` | `"1d6"` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/3/combat/evade` | `5` | `10` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/3/hp` | `56` | `16` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/3/max_hp` | `56` | `16` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/4/combat/basic_attack/accuracy` | `80` | `100` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/4/combat/basic_attack/damage` | `"1d6+1"` | `"1d6"` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/4/combat/defense` | `0` | `1` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/4/combat/evade` | `6` | `5` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/4/hp` | `96` | `44` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/4/max_hp` | `96` | `44` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/5/combat/evade` | `17` | `7` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/5/hp` | `76` | `28` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/5/max_hp` | `76` | `28` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/6/combat/basic_attack/accuracy` | `85` | `70` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/6/combat/basic_attack/damage` | `"1d8"` | `"1d10"` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/6/hp` | `88` | `32` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/6/max_hp` | `88` | `32` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/7/combat/basic_attack/damage` | `"1d6+1"` | `"1d10"` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/7/combat/defense` | `2` | `1` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/7/combat/evade` | `4` | `3` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/7/hp` | `96` | `80` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/7/max_hp` | `96` | `80` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/8/combat/basic_attack/accuracy` | `90` | `95` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/8/combat/basic_attack/damage` | `"1d8+2"` | `"1d10"` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/8/combat/defense` | `2` | `1` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/8/combat/evade` | `1` | `0` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/10/combat/basic_attack/accuracy` | `70` | `55` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/10/combat/basic_attack/damage` | `"1d10"` | `"1d6"` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/10/combat/defense` | `0` | `1` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/10/hp` | `84` | `28` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/10/max_hp` | `84` | `28` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/11/combat/basic_attack/accuracy` | `80` | `75` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/11/combat/basic_attack/damage` | `"1d8+2"` | `"2d10"` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/11/combat/defense` | `4` | `0` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/11/combat/evade` | `11` | `10` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/11/hp` | `80` | `32` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/11/max_hp` | `80` | `32` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/12/combat/basic_attack/accuracy` | `100` | `35` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/12/combat/basic_attack/damage` | `"1d8+2"` | `"2d12"` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/12/combat/defense` | `1` | `0` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/12/hp` | `84` | `44` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/12/max_hp` | `84` | `44` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/13/combat/basic_attack/accuracy` | `60` | `65` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/13/combat/defense` | `2` | `1` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/13/combat/evade` | `2` | `0` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/13/hp` | `120` | `124` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/enemies/13/max_hp` | `120` | `124` | 007数值搜索：胜率、HP、回合与职业差距综合越界最少 |
| `/items/2/rare` | `null` | `true` | 稀有消耗品显式标记 |
| `/items/9/rare` | `null` | `true` | 稀有消耗品显式标记 |
| `/items/10/rare` | `null` | `true` | 稀有消耗品显式标记 |
| `/items/23/rare` | `null` | `true` | 稀有消耗品显式标记 |
| `/meta/content_revision` | `"2026-10-11-balance-pass2"` | `"2026-10-11-balance-pass3"` | 使旧存档刷新到本轮剧本 |

### 第6节文本同步（全部）

只改下列描述/结果中的数字和量词，以及指定的同伴说明。hybrid.summary、prepared_turns.draft.gm_text 是同一描述/动作结果的可见副本。

| 路径 | 原文 | 新文 |
|---|---|---|
| `/companions/1/description` | 毎ラウンド開始時にプレイヤーのHPを8回復する。 | 2ラウンドごとに、プレイヤーの最大HPの15%を回復する。 |
| `/locations/13/hybrid/prepared_turns/1/draft/gm_text` | 泉を横目に休まず進むと、茂みの左右から低い唸り声が重なった。二頭の森狼が退路と行く手を分けて塞ぎ、牙を剥いて間合いを詰めてくる。 | 泉を横目に休まず進むと、茂みの左右から低い唸り声が重なった。一頭の森狼が退路と行く手を分けて塞ぎ、牙を剥いて間合いを詰めてくる。 |
| `/locations/14/description` | 泉を通り過ぎた先で二頭の森狼が襲いかかる。 | 泉を通り過ぎた先で一頭の森狼が襲いかかる。 |
| `/locations/14/hybrid/summary` | 泉を通り過ぎた先で二頭の森狼が襲いかかる。 | 泉を通り過ぎた先で一頭の森狼が襲いかかる。 |
| `/locations/15/combat/result_texts/victory` | 最後の一匹を弾き飛ばした直後、泉の反対側で水音が三つ重なった。休む間もなく、新たな三匹のスライムが水面から這い上がり、半円を描いて包囲を狭めてくる。 | 最後の一匹を弾き飛ばした直後、泉の反対側で水音が一つ重なった。休む間もなく、新たな一匹のスライムが水面から這い上がり、半円を描いて包囲を狭めてくる。 |
| `/locations/15/description` | 三匹のスライムに包囲されている。 | 一匹のスライムに包囲されている。 |
| `/locations/15/hybrid/summary` | 三匹のスライムに包囲されている。 | 一匹のスライムに包囲されている。 |
| `/locations/16/description` | さらに三匹のスライムが泉から這い出す。 | さらに一匹のスライムが泉から這い出す。 |
| `/locations/16/hybrid/summary` | さらに三匹のスライムが泉から這い出す。 | さらに一匹のスライムが泉から這い出す。 |
| `/locations/20/description` | 通路の先を、一匹のゴブリンと二匹の弓ゴブリンが守っている。 | 通路の先を、一匹のゴブリンと一匹の弓ゴブリンが守っている。 |
| `/locations/20/hybrid/prepared_turns/0/draft/gm_text` | 一階奥の角を曲がると、中央のゴブリンが槍を構え、両脇の弓兵が木箱の上へ飛び乗った。矢じりがこちらを向き、三方向から逃げ道を封じてくる。 | 一階奥の角を曲がると、中央のゴブリンが槍を構え、両脇の弓兵が木箱の上へ飛び乗った。矢じりがこちらを向き、二方向から逃げ道を封じてくる。 |
| `/locations/20/hybrid/prepared_turns/1/draft/gm_text` | 巡回の隙を読み、積み上げられた樽の陰を抜けて三人組の背後を通過した。二階へ続く階段まで誰にも気づかれていない。 | 巡回の隙を読み、積み上げられた樽の陰を抜けて二人組の背後を通過した。二階へ続く階段まで誰にも気づかれていない。 |
| `/locations/20/hybrid/prepared_turns/2/draft/gm_text` | 身を隠した木箱が軋み、二匹の弓ゴブリンが同時に振り向いた。退路へ矢が突き刺さり、中央のゴブリンが武器を抜いて迫る。 | 身を隠した木箱が軋み、一匹の弓ゴブリンが同時に振り向いた。退路へ矢が突き刺さり、中央のゴブリンが武器を抜いて迫る。 |
| `/locations/20/hybrid/summary` | 通路の先を、一匹のゴブリンと二匹の弓ゴブリンが守っている。 | 通路の先を、一匹のゴブリンと一匹の弓ゴブリンが守っている。 |
| `/locations/23/description` | 扉を開けた瞬間、五匹の猛犬が鎖を引きちぎって襲いかかる。 | 扉を開けた瞬間、一匹の猛犬が鎖を引きちぎって襲いかかる。 |
| `/locations/23/hybrid/summary` | 扉を開けた瞬間、五匹の猛犬が鎖を引きちぎって襲いかかる。 | 扉を開けた瞬間、一匹の猛犬が鎖を引きちぎって襲いかかる。 |
| `/locations/25/hybrid/prepared_turns/1/draft/gm_text` | 即興の暗号を堂々と告げると鉄門が開いた。しかし先に待っていたのは財宝ではなく、金貨の山に座るゴブリン王と二匹の弓兵だった。 | 即興の暗号を堂々と告げると鉄門が開いた。しかし先に待っていたのは財宝ではなく、金貨の山に座るゴブリン王と一匹の弓兵だった。 |
| `/locations/25/hybrid/prepared_turns/2/draft/gm_text` | 沈黙の後、警報の鐘が鳴る。退路には三匹の大ゴブリンが立ち塞がっていた。 | 沈黙の後、警報の鐘が鳴る。退路には一匹の大ゴブリンが立ち塞がっていた。 |
| `/locations/25/hybrid/prepared_turns/3/draft/gm_text` | 暗号を知らないと答えた瞬間、小窓が勢いよく閉じた。直後に背後の隠し扉が開き、三匹の大ゴブリンが棍棒を構えて退路を塞ぐ。 | 暗号を知らないと答えた瞬間、小窓が勢いよく閉じた。直後に背後の隠し扉が開き、一匹の大ゴブリンが棍棒を構えて退路を塞ぐ。 |
| `/locations/26/combat/result_texts/victory` | 三匹の警備兵を倒すと、戦闘の衝撃で鉄門の錠が外れた。扉の先は財宝庫だ。金貨の山からゴブリン王が立ち上がり、二匹の弓兵が高台へ散って次の戦いを挑んでくる。 | 一匹の警備兵を倒すと、戦闘の衝撃で鉄門の錠が外れた。扉の先は財宝庫だ。金貨の山からゴブリン王が立ち上がり、一匹の弓兵が高台へ散って次の戦いを挑んでくる。 |
| `/locations/26/description` | 鉄門の前後を三匹の大ゴブリンに挟まれた。 | 鉄門の前後を一匹の大ゴブリンに挟まれた。 |
| `/locations/26/hybrid/summary` | 鉄門の前後を三匹の大ゴブリンに挟まれた。 | 鉄門の前後を一匹の大ゴブリンに挟まれた。 |
| `/locations/27/description` | 財宝の山の前でゴブリン王と二匹の弓兵が待ち構えている。 | 財宝の山の前でゴブリン王と一匹の弓兵が待ち構えている。 |
| `/locations/27/hybrid/summary` | 財宝の山の前でゴブリン王と二匹の弓兵が待ち構えている。 | 財宝の山の前でゴブリン王と一匹の弓兵が待ち構えている。 |

## 5. 仍越界的项目

| 遭遇 | 职业 | 指标 | 实测 | 目标 |
|---|---|---|---:|---|
| lost_goblin_crossroads | hero | hp_left | 0.955 | [0.6, 0.95] |
| lost_goblin_crossroads | mage | hp_left | 0.969 | [0.6, 0.95] |
| goblin_fort | hero | hp_left | 0.966 | [0.6, 0.95] |
| goblin_fort | mage | hp_left | 0.962 | [0.6, 0.95] |
| goblin_fort_chest_fight | hero | hp_left | 0.994 | [0.6, 0.95] |
| goblin_fort_chest_fight | cleric | hp_left | 0.984 | [0.6, 0.95] |
| goblin_fort_chest_fight | mage | hp_left | 0.982 | [0.6, 0.95] |
| goblin_fort_chest_fight | thief | hp_left | 0.953 | [0.6, 0.95] |
| forest_wolves | hero | win_rate | 0.976 | [0.75, 0.9] |
| forest_wolves | hero | hp_left | 0.715 | [0.35, 0.7] |
| forest_wolves | mage | hp_left | 0.732 | [0.35, 0.7] |
| forest_wolves | mage | rounds | 3.000 | [4, 7] |
| forest_wolves | thief | win_rate | 0.708 | [0.75, 0.9] |
| goblin_fort_first_second | hero | win_rate | 0.984 | [0.75, 0.9] |
| goblin_fort_first_second | mage | win_rate | 0.706 | [0.75, 0.9] |
| goblin_fort_first_second | mage | rounds | 3.000 | [4, 7] |
| goblin_fort_first_second | thief | win_rate | 0.678 | [0.75, 0.9] |
| goblin_fort_second_right | hero | win_rate | 1.000 | [0.75, 0.9] |
| goblin_fort_second_right | hero | hp_left | 0.705 | [0.35, 0.7] |
| goblin_fort_second_right | cleric | win_rate | 1.000 | [0.75, 0.9] |
| goblin_fort_second_right | cleric | rounds | 10.000 | [4, 7] |
| goblin_fort_second_right | mage | win_rate | 0.904 | [0.75, 0.9] |
| goblin_fort_second_left | hero | win_rate | 0.970 | [0.75, 0.9] |
| goblin_fort_second_left | hero | hp_left | 0.712 | [0.35, 0.7] |
| goblin_fort_second_left | mage | hp_left | 0.732 | [0.35, 0.7] |
| goblin_fort_second_left | mage | rounds | 3.000 | [4, 7] |
| goblin_fort_second_left | thief | win_rate | 0.664 | [0.75, 0.9] |
| goblin_fort_third_guards | hero | win_rate | 1.000 | [0.75, 0.9] |
| goblin_fort_third_guards | hero | hp_left | 0.722 | [0.35, 0.7] |
| goblin_fort_third_guards | cleric | win_rate | 1.000 | [0.75, 0.9] |
| goblin_fort_third_guards | cleric | rounds | 10.000 | [4, 7] |
| village_fire_elemental | hero | win_rate | 0.966 | [0.75, 0.9] |
| village_fire_elemental | hero | rounds | 3.000 | [4, 7] |
| village_fire_elemental | cleric | rounds | 3.000 | [4, 7] |
| village_fire_elemental | mage | rounds | 2.000 | [4, 7] |
| village_fire_elemental | thief | win_rate | 0.556 | [0.75, 0.9] |
| ice_elemental_encounter | hero | win_rate | 0.918 | [0.75, 0.9] |
| ice_elemental_encounter | mage | win_rate | 0.916 | [0.75, 0.9] |
| ice_elemental_encounter | mage | hp_left | 0.845 | [0.35, 0.7] |
| ice_elemental_encounter | mage | rounds | 2.000 | [4, 7] |
| slime_king_battle | hero | win_rate | 0.930 | [0.6, 0.75] |
| slime_king_battle | hero | hp_left | 0.583 | [0.15, 0.5] |
| slime_king_battle | hero | rounds | 6.000 | [7, 12] |
| slime_king_battle | cleric | hp_left | 0.551 | [0.15, 0.5] |
| slime_king_battle | mage | hp_left | 0.610 | [0.15, 0.5] |
| slime_king_battle | mage | rounds | 3.000 | [7, 12] |
| slime_king_battle | thief | rounds | 5.000 | [7, 12] |
| goblin_fort_fourth | hero | win_rate | 0.968 | [0.6, 0.75] |
| goblin_fort_fourth | hero | hp_left | 0.581 | [0.15, 0.5] |
| goblin_fort_fourth | cleric | hp_left | 0.581 | [0.15, 0.5] |
| goblin_fort_fourth | mage | win_rate | 0.540 | [0.6, 0.75] |
| goblin_fort_fourth | mage | hp_left | 0.592 | [0.15, 0.5] |
| goblin_fort_fourth | mage | rounds | 4.000 | [7, 12] |
| goblin_fort_fourth | thief | rounds | 6.000 | [7, 12] |
| merchant_battle | cleric | win_rate | 0.792 | [0.6, 0.75] |
| frost_wolf_battle | hero | win_rate | 0.976 | [0.6, 0.75] |
| frost_wolf_battle | cleric | win_rate | 0.834 | [0.6, 0.75] |
| frost_wolf_battle | mage | win_rate | 0.896 | [0.6, 0.75] |
| frost_wolf_battle | mage | hp_left | 0.529 | [0.15, 0.5] |
| frost_wolf_battle | mage | rounds | 6.000 | [7, 12] |
| frost_wolf_battle | thief | win_rate | 0.590 | [0.6, 0.75] |
| dragon_valley_loc | hero | attack_only_win_rate | 0.398 | [0, 0.2] |
| dragon_valley_loc | cleric | attack_only_win_rate | 0.212 | [0, 0.2] |
| dragon_valley_loc | cleric | hp_left | 0.527 | [0.15, 0.5] |
| dragon_valley_loc | mage | hp_left | 0.567 | [0.15, 0.5] |
| dragon_valley_loc | mage | rounds | 4.000 | [7, 12] |
| dragon_valley_loc | thief | rounds | 5.000 | [7, 12] |
| forest_wolves | all | class_spread | 0.268 | [0, 0.15] |
| goblin_fort_first_second | all | class_spread | 0.306 | [0, 0.25] |
| goblin_fort_second_right | all | class_spread | 0.202 | [0, 0.15] |
| goblin_fort_second_left | all | class_spread | 0.306 | [0, 0.15] |
| goblin_fort_third_guards | all | class_spread | 0.178 | [0, 0.15] |
| village_fire_elemental | all | class_spread | 0.410 | [0, 0.15] |
| ice_elemental_encounter | all | class_spread | 0.162 | [0, 0.15] |
| slime_king_battle | all | class_spread | 0.288 | [0, 0.15] |
| goblin_fort_fourth | all | class_spread | 0.428 | [0, 0.25] |
| frost_wolf_battle | all | class_spread | 0.386 | [0, 0.15] |

有限搜索未证明剩余约束无解。共享 goblin/hobgoblin/archer 模板同时参与不同等级、数量和类别的战斗；职业防御、治疗、元素输出及MP/SP差异会使统一敌人数值难以同时拟合。胜利条件下剩余HP和包含早败的回合中位数并非同一批样本。70%胜率在N=500下标准误差约2pp，区间边缘有抽样波动。

## 6. TODO(design)

- TODO(design): 砦系列 checkpoint 的首次战斗至 goblin_fort_fourth 均为Lv1；Lv2触发仍在击败史莱姆王/森林出口等既有flag之后，砦通关再到Lv3。火球・改提前Lv2已实现，但该路线仍无提前使用窗口，未改触发条件。
- TODO(design): forest_wolves 的动作结果仍有「茂みの左右」「唸り声が重なった」「退路と行く手を分けて塞ぎ」，一头狼的空间描写需审定。
- TODO(design): slime_ambush_one 仍有「包囲されている」；胜利结果中的「水音が一つ重なった」「半円を描いて包囲を狭めてくる」和 slime_ambush_two 胜利的「仲間の残骸」需审定。
- TODO(design): goblin_fort_first_second 开战结果仍有「中央」「両脇の弓兵」；失败结果仍有「一匹…同時に振り向いた」，不改非数字措辞。
- TODO(design): goblin_fort_third_guards 仍有「鉄門の前後を…挟まれた」；胜利结果的一匹弓兵「高台へ散って」需审定。
- TODO(design): 本次授权限于地点描述/结果，保留动作 UI/intent_keywords 的「三人のゴブリンと戦う」「三人組を迂回する」及 continue_from_elf_spring.preview 的「二頭の森狼」。location.enemy_ids 仍为历史列表，实际战斗以 combat.enemy_ids 为准；如需全量同步请另定范围。
- TODO(design): checkpoint 仍为 proposed，连续流程未设阈值；请审定路线、补给和同伴选择是否代表实际玩家。剩余数值越界见第5节。

- TODO(design): 同伴等权提升7.80pp，低于10pp下限。本轮保持007指定15%描述和对应实际效果；请审定后续同伴/战斗节奏调整。

## 7. 推断、偏离与已知问题

- 推断：按每个 checkpoint 的 sources 作为一条独立路线；dragon_valley_loc 是主线通关，其他终点完成率仅表示完成该分支，不称为整个游戏通关。非战斗判定沿用 checkpoint 固定结果。
- 推断：稀有伤害阈值使用现有策略的单次期望净伤害，任一敌人达线就保留；不将多敌总伤害相加后与某一敌人HP比较。聖水和三种巻物标记 rare=true。
- 推断：同名升级按 replaces 关联旧名字，保留旧技能所在顺序并去重；同ID的旧pass2新技能刷新为新版。没有旧技能时也发放指定升级技能。
- 推断：clear_skills 记录当时等级并持久化 skills_cleared_through_level，以免事件240条截断后重新补发；旧事件按level_up顺序恢复清除时等级。只有清除记录、没有升级记录时保守视为清到当前等级。旧存档缺level仍Lv1，不追溯成长。
- 已知限制：如果旧事件中清除记录已被截断、且旧档没有持久化标记，就无法重建该历史。未自行推断剧情flag来永久禁用技能。
- 偏离：没有范围外改动；数值目标未全部达标，完整保留越界结果。未新增依赖、未联网。

## 8. 工程交付与验证

- 引擎：host/state.py；剧本：两份dragon_rpg JSON及schema；模拟：scripts/balance/sim.py、route.py、pass3.py、pass3_report.py；checkpoint及搜索结果、报告；测试：test_balance_pass3.py，并更新pass2技能断言和剧情版本断言。
- `python -m unittest discover -s tests -q`：315项，314通过，1项按既有BALANCE_ENFORCE条件跳过。Windows沙箱创建临时目录后无法读写，已在放宽沙箱权限后用相同离线命令通过，未修改既有测试来规避。
- `node --check client/app.js`、`git diff --check`：通过。两份剧本按记录ID核对，本轮103处变更完全一致；受保护字段与targets未改。
- `python -m scripts.balance.sim --check --n 500`：77项越界，退出码1；与正式矩阵逐cell完全一致。--check非零表示上述数值目标越界，不等于单元测试失败。
- 连续流程对最终Boss胜利导致的剧情结束标记按胜利处理，回归测试覆盖；最终路线文件全部用修正后的代码重新运行N=500。
