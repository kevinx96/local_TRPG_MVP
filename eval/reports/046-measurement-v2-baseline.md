# 046 测量 v2 完整基线（046b）

主通关口径：冒険完了；击败/净化 Ignis 与进入终局另列。全程离线。
终局列按 draco_battle 或任一 ending 字段统计，包含引擎记录的失败结局，不能当作主线完成率。
046b 设计决定已接受第一轮 Ignis 复现；P0b >90% 不再是复现门槛。M1 的草案上限仍保留。

| 原型 | 职业 | N | 通关率 | 草案区间 | Ignis | 终局 | Ignis回合中位数 |
|---|---|---:|---:|---|---:|---:|---:|
| P0a | hero | 500 | 0.0% | [0, 0.05] | 0.0% | 100.0% | 13 |
| P0a | cleric | 500 | 3.2% | [0, 0.05] | 3.2% | 100.0% | 10 |
| P0a | mage | 500 | 0.8% | [0, 0.15] | 0.8% | 100.0% | 5.0 |
| P0a | thief | 500 | 0.0% | [0, 0.05] | 0.0% | 100.0% | 10 |
| P0b | hero | 500 | 50.2% | [0, 0.05] | 50.2% | 100.0% | 11.0 |
| P0b | cleric | 500 | 58.0% | [0, 0.05] | 58.0% | 100.0% | 9 |
| P0b | mage | 500 | 14.0% | [0, 0.15] | 14.0% | 100.0% | 6.0 |
| P0b | thief | 500 | 33.2% | [0, 0.05] | 33.2% | 100.0% | 11 |
| P1 | hero | 500 | 52.0% | [0.15, 0.35] | 52.0% | 100.0% | 11.0 |
| P1 | cleric | 500 | 58.6% | [0.15, 0.35] | 58.6% | 100.0% | 9 |
| P1 | mage | 500 | 26.6% | [0.15, 0.35] | 26.6% | 100.0% | 5.0 |
| P1 | thief | 500 | 45.8% | [0.15, 0.35] | 45.8% | 100.0% | 8 |
| P2 | hero | 500 | 16.8% | [0.55, 0.75] | 20.0% | 89.4% | 10 |
| P2 | cleric | 500 | 17.0% | [0.55, 0.75] | 17.6% | 95.2% | 6.0 |
| P2 | mage | 500 | 2.6% | [0.55, 0.75] | 6.2% | 91.0% | 6 |
| P2 | thief | 500 | 12.6% | [0.55, 0.75] | 14.8% | 88.8% | 8 |
| P3 | hero | 500 | 2.0% | [0.8, 1] | 8.8% | 87.6% | 11 |
| P3 | cleric | 500 | 9.6% | [0.8, 1] | 11.2% | 90.8% | 6.0 |
| P3 | mage | 500 | 0.0% | [0.8, 1] | 1.8% | 91.0% | 7 |
| P3 | thief | 500 | 0.2% | [0.8, 1] | 3.0% | 89.4% | 9 |
| P2s | hero | 500 | 20.0% | None | 22.2% | 94.6% | 11 |
| P2s | cleric | 500 | 18.2% | None | 19.2% | 93.2% | 6.0 |
| P2s | mage | 500 | 2.6% | None | 5.2% | 93.0% | 6 |
| P2s | thief | 500 | 13.6% | None | 15.8% | 91.8% | 8 |
| P0g | hero | 500 | 50.2% | None | 50.2% | 100.0% | 11.0 |
| P0g | cleric | 500 | 58.0% | None | 58.0% | 100.0% | 9 |
| P0g | mage | 500 | 14.0% | None | 14.0% | 100.0% | 6.0 |
| P0g | thief | 500 | 33.2% | None | 33.2% | 100.0% | 11 |

| 指标 | 状态 | 硬门槛 | 满足草案目标 | 说明 |
|---|---|---|---|---|
| M1 | fail | True | False | 冒険完了为主口径；试玩 checkpoint 不计入原型门槛。 |
| M1' | report | False | False | 分别以 P0a、P0b 检查 P0→P1，避免自行合并两种 P0。 |
| M2 | report | False | False | 准备清单为 proposed；净化按达成目标遭遇成功计（victory/purified）。 |
| M3 | fail | True | False | 可持续回复能力（未扣过量回复）/开场完整敌方每回合期望伤害；消耗品计入 M3'。 |
| M3' | report | False | False | 击杀回合只取胜利/净化样本；失败为右删失。耗尽按当前 HP+库存回复与净开场伤害估计；有限 MP/SP 主动回复未换算进此静态资源池，实际使用仍影响击杀回合。净伤害≤0时耗尽为无限，赛跑比0。 |
| M4 | fail | True | False |  |
| M5 | report | False | False | 只统计到达最终 Boss 的 P1；道具使用率=消耗/(消耗+结余)，金币含开局支给。 |
| M6 | report | False | False |  |
| M7 | report | False | False | 成对普通成功/失败分支，沿真实后果打完被迫战斗后比较 resource_score；不是观察性分组，也不估整路线通关差。 |
| M8 | report | False | False | 每职业/每同伴/每 Boss，与同配置无同伴成对比较；负提升也保留。 |
| M9 | fail | True | False | 开场全部敌人，未命中/防御等零伤害回合计入；保留旧预算上限接口。 |
| M10 | report | False | False | 当前仍有低命中技能；报告实际 CV。100%命中和预告机制待 050/051，不能据现状认证高 CV 技能已预告。 |
| M11 | report | False | False | 在实际轨迹每次敌方阶段按当时存活敌人精确求期望并求和；不减回复，保留防御/抗性实际作用。 |
| M12 | not_applicable | False | None | 待 050/051：新主动技能、被动二选一和冷却未实装；不将现有技能冒充新机制样本。 |
| M13 | report | False | False | 当前可做固定装备、每级成长的 ±1 checkpoint 探针；战斗 EXP 与满级8待 050/051，到达等级差只描述现状，不认证 EXP 目标。 |

完整逐配置数值、与目标差距和样本见同名 JSON 的 metrics.value；report 不表示通过。

| 存档核对后独立配置 | 胜率 | 回合中位数 | S |
|---|---:|---:|---:|
| human_berserker | 95.6% | 19.0 | 1.2464 |
| P0b + 氷鉄の大剣 | 98.8% | 10.0 | 1.2464 |
| 无同伴 | 63.4% | 20.0 | 0.0000 |

存档核对：Ignis 时鉄の剣/革の鎧/紅玉の護符；アダマンタイトの鎧在战后才装备。
独立配置采用满资源；库存按此前战斗结算和资源流水重建，不能视为完整开战遥测。

| 文档威胁对照 | M9 | CV | 状态 | 超差说明 |
|---|---:|---:|---|---|
| lost_goblin_crossroads | 10.00% | 0.8660 | pass |  |
| slime_ambush_one | 10.67% | 0.8004 | pass |  |
| slime_ambush_two | 10.67% | 0.8004 | pass |  |
| village_fire_slime | 4.19% | 1.1774 | pass |  |
| goblin_fort_second_right | 8.00% | 1.0897 | pass |  |
| forest_wolves | 16.75% | 1.1220 | pass |  |
| goblin_fort_second_left | 17.25% | 0.8956 | pass |  |
| ice_elemental_encounter | 16.21% | 0.8990 | pass |  |
| slime_king_battle | 23.00% | 0.5930 | pass |  |
| merchant_battle | 15.33% | 1.0136 | fail | 亡霊転換权重1/6，不直接造成HP伤害；文档18%/0.83近似为只在攻击发生条件下的均值/CV。真实AI的零伤害回合必须计入M9/M10。 |
| frost_wolf_battle | 9.57% | 1.1220 | pass |  |
| dragon_valley_loc | 13.82% | 1.2092 | pass |  |
| draco_battle | 15.19% | 0.6670 | fail | 護衛の構え权重1/6，零直接伤害；文档18%/0.45近似为只在攻击发生条件下的均值/CV。真实AI的防御回合必须计入M9/M10。 |
| cave_heat_corridor | 41.28% | 0.3821 | pass |  |
| cave_lava_room | 37.71% | 0.3320 | pass |  |
| cave_crystal_corridor | 30.35% | 0.5172 | pass |  |
| goblin_fort_fourth | 40.85% | 0.9436 | pass |  |

P2s 与 P2：

```json
[
  {
    "character": "hero",
    "completion_gap_pp": 3.2,
    "level_gaps": {
      "castle": 0,
      "dark_forest_loc": 0,
      "draco_battle": 0,
      "dragon_valley_loc": 0,
      "elf_spring": 0,
      "forest_exit": 0,
      "ian_ice_katana_aftermath": 0,
      "royal_gate": 0,
      "valley_entrance": 0,
      "village_frozen_clue": 0
    },
    "meets_draft": true,
    "missing_nodes": []
  },
  {
    "character": "cleric",
    "completion_gap_pp": 1.1999999999999984,
    "level_gaps": {
      "castle": 0,
      "dark_forest_loc": 0,
      "draco_battle": 0,
      "dragon_valley_loc": 0,
      "elf_spring": 0,
      "forest_exit": 0,
      "ian_ice_katana_aftermath": 0,
      "royal_gate": 0,
      "valley_entrance": 0,
      "village_frozen_clue": 0
    },
    "meets_draft": true,
    "missing_nodes": []
  },
  {
    "character": "mage",
    "completion_gap_pp": 0.0,
    "level_gaps": {
      "castle": 0,
      "dark_forest_loc": 0,
      "draco_battle": 0,
      "dragon_valley_loc": 0,
      "elf_spring": 0,
      "forest_exit": 0,
      "ian_ice_katana_aftermath": 0,
      "royal_gate": 0,
      "valley_entrance": 0,
      "village_frozen_clue": 0
    },
    "meets_draft": true,
    "missing_nodes": []
  },
  {
    "character": "thief",
    "completion_gap_pp": 1.0000000000000009,
    "level_gaps": {
      "castle": 0,
      "dark_forest_loc": 0,
      "draco_battle": 0,
      "dragon_valley_loc": 0,
      "elf_spring": 0,
      "forest_exit": 0,
      "ian_ice_katana_aftermath": 0,
      "royal_gate": 0,
      "valley_entrance": 0,
      "village_frozen_clue": 0
    },
    "meets_draft": true,
    "missing_nodes": []
  }
]
```

P0g：当前没有能保留收益的重复战斗；不清除 defeated flags，EXP 每级资源成本待 050/051。

P2/P3 支线清单为 proposed；P3 采用可连通、非互斥的一条全支线提案，不强制判定成功。
P2 包含ガルド、リク、完整洞窟、ゴブリン砦、净化线索；P3 另加城镇交付、ミーナ、旧戦場、オークスドーン、峡谷、屋敷、商人、ロビン和三组收集交付。
P2s 对有绕行选项的战斗优先尝试绕行，失败仍承受真实战斗；同伴不是强制借用成功。

遥测详见 046b-save-telemetry.json / .md：17 个可观察战斗结算、14 次判定；较早的4场缺回合数，完整动作记录缺失。

N=500，探针每格 N=500，seed=20261020，workers=12。
全量主批次墙钟 1286.67 秒；分阶段及补充复核 {'routes': 463.7995603999989, 'preparation_probes': 35.30835649999972, 'companion_probes': 329.3586361999987, 'level_probes': 106.88321969999924, 'boss_policy_probes': 196.00977969999985, 'p2s_final': 185.80203919999985, 'human_checkpoint_initial': 148.5667711999995, 'human_checkpoint_calibrated': 61.50779420000072, 'finalization': 62.74208110000109}。补充批次可能与主批次重叠，不将各项直接相加。
