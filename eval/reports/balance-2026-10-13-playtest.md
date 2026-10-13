# 029 试玩修正后的平衡复跑

每职业 / 策略 N=500，seed=20261012，4 职业 × 5 策略，共 10,000 次连续主线模拟。
沿用 028 的职业支线选择、heuristic 战斗策略和资源口径；全程离线，不使用区域重来，以保持与旧报告可比。

| 策略 | 职业 | 028 通关率 | 029 通关率 | 差值（百分点） |
|---|---|---:|---:|---:|
| none | hero | 59.4% | 59.4% | +0.0 |
| none | cleric | 49.4% | 49.4% | +0.0 |
| none | mage | 59.0% | 59.0% | +0.0 |
| none | thief | 43.8% | 43.8% | +0.0 |
| hp70 | hero | 59.0% | 59.0% | +0.0 |
| hp70 | cleric | 48.8% | 48.8% | +0.0 |
| hp70 | mage | 54.6% | 54.6% | +0.0 |
| hp70 | thief | 40.0% | 40.0% | +0.0 |
| class_aware | hero | 63.6% | 62.6% | -1.0 |
| class_aware | cleric | 53.6% | 53.6% | +0.0 |
| class_aware | mage | 57.0% | 55.8% | -1.2 |
| class_aware | thief | 51.6% | 51.8% | +0.2 |
| hp70_real_dice | hero | 57.0% | 57.0% | +0.0 |
| hp70_real_dice | cleric | 43.2% | 43.2% | +0.0 |
| hp70_real_dice | mage | 56.6% | 56.6% | +0.0 |
| hp70_real_dice | thief | 35.2% | 35.2% | +0.0 |
| class_aware_no_quests | hero | 58.6% | 58.6% | +0.0 |
| class_aware_no_quests | cleric | 52.8% | 53.0% | +0.2 |
| class_aware_no_quests | mage | 56.0% | 55.8% | -0.2 |
| class_aware_no_quests | thief | 47.4% | 47.4% | +0.0 |

20 组中 13 组的全部聚合指标逐项一致；详细死亡地点、资源及策略选择统计见 JSON。

## 变化与口径

- 出发动作删除判定；旧模拟本就强制这一次出发成功且不消耗随机数，所以固定路线组没有对应的成功率提升。
- 森林返回点改为城下町；模拟需要休息时显式进入宿屋，并从宿屋回城下町后返回森林。检查点与关键物品可达性路线同步更新。
- 到达森の出口时即设置返回通路的可见 flag。class_aware 的 visible_key 包含全部真值 flag，因而局部策略评估的稳定种子会变化；比较包含这项变化，不能将小幅波动解释为战斗数值的平衡效果。
- 没有修改战斗伤害、HP、奖励、成长或价格。保留既有 forced / real 路线判定和已选支线，未重新寻找最优策略。
- N=500 的单组差异不足以确认新的数值目标；本报告只复跑并比较。

## 复现

```powershell
python -m scripts.balance.checkpoints
python -m scripts.balance.class_aware --n 500 --seed 20261012 --workers 20 --output eval/reports/balance-2026-10-13-playtest.json
python -m scripts.balance.playtest_report
```

输入 SHA-256 记录在本次 JSON 的 fingerprints。上一份报告为 [028 平衡报告](balance-2026-10-13-castle-town.md)。
