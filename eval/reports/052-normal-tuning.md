# 052 normal 数值调参

## 052a：第 0 步与测量修正；数值调整因 C8 暂停

本交付不是 052a 数值验收通过。工程没有修改任何剧本数值、成长、敌人、提示词或冻结被动表。
L1 的整数范围无可行值，且入口教程 M9 四职业范围无公共解；未获得范围裁定前，遵守 C8 停止数值调整。

调参前：HEAD 35a3cced66a3fd34b3eaaf2fd223b874f97d3dc2，N=500 / probe-n=500 / seed=20261020。
测量修正后（未调参）：N=20 / probe-n=20 / seed=20261022。不把不同样本数/种子的差异宣称为调参收益。
被动表读取 053 v1，未重新穷举。原始 JSON、审计表与运行日志位于 `.tmp-test/052a/`。

### 阻塞与例外

- TODO(design): 给出盗賊 HP 成长 2.1–2.8、魔法使い SP / 盗賊 MP 成长 0.6–0.9 的整数取整规则或显式例外。引擎 `int(gains)` 不支持区间内的小数实际成长。
- TODO(design): `dark_forest_loc` 是 `tutorial: true` 的 trash，首回合 `slime_acid` 固定 8 点真实伤害，不是 scripted_loss。勇者目标绝对伤害 [2,3]、魔法使い [1.2,1.8] 无交集；需教程豁免或另定规则。
- TODO(design): 本报告所有未通过/缺样本的硬门槛均未批准例外，不代表验收通过。

### 第 0 步：HEAD 与 053

| 原型 | 职业 | 变化字段 | 通关差 pp |
|---|---|---|---:|
| P2 | hero | ['completion_rate', 'ignis_rate', 'ignis_rounds_median', 'levels_mean', 'failures'] | 0.80 |
| P2 | mage | ['completion_rate', 'failures'] | -0.20 |
| P3 | hero | ['completion_rate', 'ignis_rate', 'terminal_rate', 'ignis_rounds_median', 'failures'] | 0.20 |
| P3 | mage | ['completion_rate', 'ignis_rate', 'terminal_rate', 'failures'] | 0.60 |
| P2s | hero | ['completion_rate', 'ignis_rounds_median', 'failures'] | -1.20 |

F6 同时包含数值死亡和模拟器提前终止。旧模拟器把战败后回到安全地点、HP=1、无 game_over 的结算当成路线失败。修正仅在 normal；保留真实战败、资源消耗和零 EXP，不补胜利奖励；洞窟撤回泉、屋敷撤回城镇后按实际位置继续。

| 职业 | HEAD P3 样本 | 活着且无结束却被截断 | 真正 HP≤0 |
|---|---:|---:|---:|
| hero | 500 | 113 | 386 |
| cleric | 500 | 45 | 453 |
| mage | 500 | 160 | 336 |
| thief | 500 | 138 | 362 |

### P3 护送顺序（按 HEAD 的 055 再借规则）

先借分支在护送并报告后，满足 055 条件才尝试再次借用；后借分支在报告后首次借用。每次判定、失败和 once 限制均由引擎执行。055 改变了 §6 旧正文的‘无法再借’前提，未修改任何剧本。

| 职业 | 火种/商人/护送 | n | Ignis [95%] | 通关 [95%] | 报告完成 | 再借尝试 | 入选 |
|---|---|---:|---|---|---:|---:|---|
| hero | {'fire_seed': 'accept', 'merchant': 'betray', 'escort_order': 'borrow_before_escort'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 6 | 4 | False |
| hero | {'fire_seed': 'accept', 'merchant': 'betray', 'escort_order': 'borrow_after_report'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 10 | 0 | False |
| hero | {'fire_seed': 'accept', 'merchant': 'pay', 'escort_order': 'borrow_before_escort'} | 20 | 0.25 [0.11186170140766566, 0.46870087761874407] | 0.1 [0.027866481213768224, 0.3010336452284873] | 6 | 4 | False |
| hero | {'fire_seed': 'accept', 'merchant': 'pay', 'escort_order': 'borrow_after_report'} | 20 | 0.4 [0.21880653237281708, 0.6134184992377468] | 0.3 [0.1454772448676043, 0.5189728183535235] | 10 | 0 | True |
| hero | {'fire_seed': 'refuse', 'merchant': 'betray', 'escort_order': 'borrow_before_escort'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 6 | 4 | False |
| hero | {'fire_seed': 'refuse', 'merchant': 'betray', 'escort_order': 'borrow_after_report'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 10 | 0 | False |
| hero | {'fire_seed': 'refuse', 'merchant': 'pay', 'escort_order': 'borrow_before_escort'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 6 | 4 | False |
| hero | {'fire_seed': 'refuse', 'merchant': 'pay', 'escort_order': 'borrow_after_report'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 10 | 0 | False |
| cleric | {'fire_seed': 'accept', 'merchant': 'betray', 'escort_order': 'borrow_before_escort'} | 20 | 0.2 [0.08065766257979806, 0.41601743225189364] | 0.1 [0.027866481213768224, 0.3010336452284873] | 6 | 5 | True |
| cleric | {'fire_seed': 'accept', 'merchant': 'betray', 'escort_order': 'borrow_after_report'} | 20 | 0.15 [0.052368745896216595, 0.36041886474075696] | 0 [0, 0.16112515805281938] | 4 | 0 | False |
| cleric | {'fire_seed': 'accept', 'merchant': 'pay', 'escort_order': 'borrow_before_escort'} | 20 | 0.15 [0.052368745896216595, 0.36041886474075696] | 0.1 [0.027866481213768224, 0.3010336452284873] | 6 | 5 | False |
| cleric | {'fire_seed': 'accept', 'merchant': 'pay', 'escort_order': 'borrow_after_report'} | 20 | 0.2 [0.08065766257979806, 0.41601743225189364] | 0.05 [0.008881448800795402, 0.23613119344674205] | 4 | 0 | False |
| cleric | {'fire_seed': 'refuse', 'merchant': 'betray', 'escort_order': 'borrow_before_escort'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 6 | 5 | False |
| cleric | {'fire_seed': 'refuse', 'merchant': 'betray', 'escort_order': 'borrow_after_report'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 4 | 0 | False |
| cleric | {'fire_seed': 'refuse', 'merchant': 'pay', 'escort_order': 'borrow_before_escort'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 6 | 5 | False |
| cleric | {'fire_seed': 'refuse', 'merchant': 'pay', 'escort_order': 'borrow_after_report'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 4 | 0 | False |
| mage | {'fire_seed': 'accept', 'merchant': 'betray', 'escort_order': 'borrow_before_escort'} | 20 | 0.4 [0.21880653237281708, 0.6134184992377468] | 0.25 [0.11186170140766566, 0.46870087761874407] | 2 | 1 | True |
| mage | {'fire_seed': 'accept', 'merchant': 'betray', 'escort_order': 'borrow_after_report'} | 20 | 0.1 [0.027866481213768224, 0.3010336452284873] | 0 [0, 0.16112515805281938] | 2 | 0 | False |
| mage | {'fire_seed': 'accept', 'merchant': 'pay', 'escort_order': 'borrow_before_escort'} | 20 | 0.35 [0.1811918241010821, 0.5671457233147637] | 0.05 [0.008881448800795402, 0.23613119344674205] | 2 | 1 | False |
| mage | {'fire_seed': 'accept', 'merchant': 'pay', 'escort_order': 'borrow_after_report'} | 20 | 0.05 [0.008881448800795402, 0.23613119344674205] | 0 [0, 0.16112515805281938] | 2 | 0 | False |
| mage | {'fire_seed': 'refuse', 'merchant': 'betray', 'escort_order': 'borrow_before_escort'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 2 | 1 | False |
| mage | {'fire_seed': 'refuse', 'merchant': 'betray', 'escort_order': 'borrow_after_report'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 2 | 0 | False |
| mage | {'fire_seed': 'refuse', 'merchant': 'pay', 'escort_order': 'borrow_before_escort'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 2 | 1 | False |
| mage | {'fire_seed': 'refuse', 'merchant': 'pay', 'escort_order': 'borrow_after_report'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 2 | 0 | False |
| thief | {'fire_seed': 'accept', 'merchant': 'betray', 'escort_order': 'borrow_before_escort'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 7 | 5 | False |
| thief | {'fire_seed': 'accept', 'merchant': 'betray', 'escort_order': 'borrow_after_report'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 3 | 0 | False |
| thief | {'fire_seed': 'accept', 'merchant': 'pay', 'escort_order': 'borrow_before_escort'} | 20 | 0.25 [0.11186170140766566, 0.46870087761874407] | 0.1 [0.027866481213768224, 0.3010336452284873] | 7 | 5 | True |
| thief | {'fire_seed': 'accept', 'merchant': 'pay', 'escort_order': 'borrow_after_report'} | 20 | 0.15 [0.052368745896216595, 0.36041886474075696] | 0.05 [0.008881448800795402, 0.23613119344674205] | 3 | 0 | False |
| thief | {'fire_seed': 'refuse', 'merchant': 'betray', 'escort_order': 'borrow_before_escort'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 7 | 5 | False |
| thief | {'fire_seed': 'refuse', 'merchant': 'betray', 'escort_order': 'borrow_after_report'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 3 | 0 | False |
| thief | {'fire_seed': 'refuse', 'merchant': 'pay', 'escort_order': 'borrow_before_escort'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 7 | 5 | False |
| thief | {'fire_seed': 'refuse', 'merchant': 'pay', 'escort_order': 'borrow_after_report'} | 20 | 0.0 [0, 0.16112515805281938] | 0 [0, 0.16112515805281938] | 3 | 0 | False |

### 门槛摘要（原测量 reducer 状态；尚未数值验收）

| 指标 | HEAD | 测量修正后 | 处理 |
|---|---|---|---|
| M1 | pass | fail | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M1' | report | report | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M2 | report | report | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M3 | fail | fail | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M3' | report | report | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M4 | fail | fail | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M5 | report | report | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M6 | report | report | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M7 | report | report | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M8 | report | report | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M9 | fail | fail | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M10 | report | report | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M11 | report | report | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M12 | report | report | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |
| M13 | report | report | 未调参；M4 的 Q4 例外另表；M3 留 052c 收尾 |

按052决定重核（失败格数；缺样本单列，不能认证通过）：

| 阶段 | M4 Q4后失败 | M9 Q5后失败/已测 | M9缺失 | 等级失败格 | M13等级差<2 | 职业差（排除mage） | mage P2通关 |
|---|---:|---|---:|---:|---:|---|---|
| before | 32 | 70/79 | 65 | 15 | 0 | 30.40pp; ≤20: False | 0.012 |
| after | 26 | 65/76 | 68 | 14 | 1 | 30.00pp; ≤20: False | 0 |

### 28 格前后对照

概率均附 Wilson 95% 区间。Ignis 与终局不是通关；终局包含失败结局。

| 阶段 | 原型/职业 | N | 通关 [95%] | Ignis [95%] | 终局 [95%] | Ignis 回合 |
|---|---|---:|---|---|---|---|
| before | P0a/hero | 500 | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 1.0000 [0.9923756595384479, 1] | 4 |
| before | P0a/cleric | 500 | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 1.0000 [0.9923756595384479, 1] | None |
| before | P0a/mage | 500 | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 1.0000 [0.9923756595384479, 1] | None |
| before | P0a/thief | 500 | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 1.0000 [0.9923756595384479, 1] | 5 |
| before | P0b/hero | 500 | 0.0260 [0.01525638392332725, 0.043971490834224275] | 0.0260 [0.01525638392332725, 0.043971490834224275] | 0.9980 [0.9887592932948532, 0.9996468636054407] | 6.0 |
| before | P0b/cleric | 500 | 0.0120 [0.005510995174027701, 0.025930361116447295] | 0.0120 [0.005510995174027701, 0.025930361116447295] | 0.9980 [0.9887592932948532, 0.9996468636054407] | 5.0 |
| before | P0b/mage | 500 | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 0.9980 [0.9887592932948532, 0.9996468636054407] | 4 |
| before | P0b/thief | 500 | 0.0160 [0.008129253033388314, 0.03125110853339426] | 0.0160 [0.008129253033388314, 0.03125110853339426] | 1.0000 [0.9923756595384479, 1] | 4 |
| before | P1/hero | 500 | 0.0380 [0.024460118055830385, 0.05858477253064388] | 0.0380 [0.024460118055830385, 0.05858477253064388] | 0.9940 [0.9825097478959467, 0.9979574037280398] | 8.0 |
| before | P1/cleric | 500 | 0.0100 [0.004278753896590496, 0.023193099755730702] | 0.0100 [0.004278753896590496, 0.023193099755730702] | 0.9580 [0.9366484142456699, 0.9723676898915483] | 6 |
| before | P1/mage | 500 | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 1.0000 [0.9923756595384479, 1] | 2 |
| before | P1/thief | 500 | 0.0140 [0.00679778979084349, 0.02861306913778529] | 0.0140 [0.00679778979084349, 0.02861306913778529] | 0.9960 [0.9855342847848231, 0.9989023694773173] | 5 |
| before | P2/hero | 500 | 0.2160 [0.18216774485419415, 0.25416288052796754] | 0.2440 [0.208398855460222, 0.2835048068560928] | 0.9940 [0.9825097478959467, 0.9979574037280398] | 11.0 |
| before | P2/cleric | 500 | 0.0800 [0.059298129409852594, 0.1071063165778513] | 0.0900 [0.0679425478891394, 0.11830941128933344] | 0.9940 [0.9825097478959467, 0.9979574037280398] | 8 |
| before | P2/mage | 500 | 0.0120 [0.005510995174027701, 0.025930361116447295] | 0.0460 [0.030845108370816204, 0.06807779276827323] | 0.9560 [0.9342805571276716, 0.9707660443713928] | 8.0 |
| before | P2/thief | 500 | 0.3840 [0.34240767461779237, 0.4273611723692879] | 0.4140 [0.37164260890980144, 0.45766877764958563] | 0.9320 [0.9064790772661258, 0.9509334925750932] | 10 |
| before | P3/hero | 500 | 0.0020 [0.00035313639455927543, 0.011240706705146757] | 0.2840 [0.2462377719556586, 0.32505594312373204] | 0.7740 [0.7353316422926235, 0.8084902191344461] | 12.0 |
| before | P3/cleric | 500 | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 0.0280 [0.01675097472075645, 0.04644640267494888] | 0.9100 [0.8816905887106666, 0.9320574521108606] | 13 |
| before | P3/mage | 500 | 0.0080 [0.00311531518006224, 0.020387035834105168] | 0.0820 [0.06101908946846894, 0.10935485915738875] | 0.6800 [0.6378729881233315, 0.7193822493105099] | 7.0 |
| before | P3/thief | 500 | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 0.0580 [0.0406837291117572, 0.08205618785625499] | 0.7100 [0.6687451968835135, 0.7480525801226344] | 9 |
| before | P2s/hero | 500 | 0.1260 [0.09973528894537706, 0.15796771771986404] | 0.1540 [0.1250106802783401, 0.18826536332105404] | 0.9980 [0.9887592932948532, 0.9996468636054407] | 11.0 |
| before | P2s/cleric | 500 | 0.0880 [0.06620598447492893, 0.11607647206539012] | 0.0920 [0.06968272368045207, 0.12053873813617456] | 0.9920 [0.9796129641658948, 0.9968846848199377] | 6 |
| before | P2s/mage | 500 | 0.0080 [0.00311531518006224, 0.020387035834105168] | 0.0220 [0.012328008269927582, 0.03896086121131637] | 0.9500 [0.9272318388284524, 0.9659062547561506] | 7.5 |
| before | P2s/thief | 500 | 0.2120 [0.17843950428829852, 0.24995211581755555] | 0.2420 [0.20651780855112864, 0.28141635112703234] | 0.9780 [0.9610391387886836, 0.9876719917300725] | 11.0 |
| before | P0g/hero | 500 | 0.0260 [0.01525638392332725, 0.043971490834224275] | 0.0260 [0.01525638392332725, 0.043971490834224275] | 0.9980 [0.9887592932948532, 0.9996468636054407] | 6.0 |
| before | P0g/cleric | 500 | 0.0120 [0.005510995174027701, 0.025930361116447295] | 0.0120 [0.005510995174027701, 0.025930361116447295] | 0.9980 [0.9887592932948532, 0.9996468636054407] | 5.0 |
| before | P0g/mage | 500 | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 0.0000 [4.336808689942018e-19, 0.007624340461552241] | 0.9980 [0.9887592932948532, 0.9996468636054407] | 4 |
| before | P0g/thief | 500 | 0.0160 [0.008129253033388314, 0.03125110853339426] | 0.0160 [0.008129253033388314, 0.03125110853339426] | 1.0000 [0.9923756595384479, 1] | 4 |
| after | P0a/hero | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | None |
| after | P0a/cleric | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | 5 |
| after | P0a/mage | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | None |
| after | P0a/thief | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | 4.0 |
| after | P0b/hero | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | 10.0 |
| after | P0b/cleric | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | 1.5 |
| after | P0b/mage | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | None |
| after | P0b/thief | 20 | 0.1000 [0.027866481213768224, 0.3010336452284873] | 0.1000 [0.027866481213768224, 0.3010336452284873] | 1.0000 [0.8388748419471806, 1] | 12 |
| after | P1/hero | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | 8 |
| after | P1/cleric | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | None |
| after | P1/mage | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | 2.5 |
| after | P1/thief | 20 | 0.1000 [0.027866481213768224, 0.3010336452284873] | 0.1000 [0.027866481213768224, 0.3010336452284873] | 1.0000 [0.8388748419471806, 1] | 12.0 |
| after | P2/hero | 20 | 0.2000 [0.08065766257979806, 0.41601743225189364] | 0.2500 [0.11186170140766566, 0.46870087761874407] | 1.0000 [0.8388748419471806, 1] | 11 |
| after | P2/cleric | 20 | 0.0500 [0.008881448800795402, 0.23613119344674205] | 0.0500 [0.008881448800795402, 0.23613119344674205] | 1.0000 [0.8388748419471806, 1] | 6 |
| after | P2/mage | 20 | 0.0000 [0, 0.16112515805281938] | 0.0500 [0.008881448800795402, 0.23613119344674205] | 1.0000 [0.8388748419471806, 1] | 8 |
| after | P2/thief | 20 | 0.3500 [0.1811918241010821, 0.5671457233147637] | 0.4500 [0.2581978582556243, 0.6579146575496577] | 1.0000 [0.8388748419471806, 1] | 9.5 |
| after | P3/hero | 20 | 0.3000 [0.1454772448676043, 0.5189728183535235] | 0.4000 [0.21880653237281708, 0.6134184992377468] | 1.0000 [0.8388748419471806, 1] | 10.5 |
| after | P3/cleric | 20 | 0.1000 [0.027866481213768224, 0.3010336452284873] | 0.2000 [0.08065766257979806, 0.41601743225189364] | 1.0000 [0.8388748419471806, 1] | 14.5 |
| after | P3/mage | 20 | 0.2500 [0.11186170140766566, 0.46870087761874407] | 0.4000 [0.21880653237281708, 0.6134184992377468] | 1.0000 [0.8388748419471806, 1] | 7 |
| after | P3/thief | 20 | 0.1000 [0.027866481213768224, 0.3010336452284873] | 0.2500 [0.11186170140766566, 0.46870087761874407] | 1.0000 [0.8388748419471806, 1] | 9 |
| after | P2s/hero | 20 | 0.1000 [0.027866481213768224, 0.3010336452284873] | 0.1500 [0.052368745896216595, 0.36041886474075696] | 1.0000 [0.8388748419471806, 1] | 10 |
| after | P2s/cleric | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | None |
| after | P2s/mage | 20 | 0.0000 [0, 0.16112515805281938] | 0.0500 [0.008881448800795402, 0.23613119344674205] | 1.0000 [0.8388748419471806, 1] | 10 |
| after | P2s/thief | 20 | 0.1000 [0.027866481213768224, 0.3010336452284873] | 0.1000 [0.027866481213768224, 0.3010336452284873] | 1.0000 [0.8388748419471806, 1] | 6 |
| after | P0g/hero | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | 10.0 |
| after | P0g/cleric | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | 1.5 |
| after | P0g/mage | 20 | 0.0000 [0, 0.16112515805281938] | 0.0000 [0, 0.16112515805281938] | 1.0000 [0.8388748419471806, 1] | None |
| after | P0g/thief | 20 | 0.1000 [0.027866481213768224, 0.3010336452284873] | 0.1000 [0.027866481213768224, 0.3010336452284873] | 1.0000 [0.8388748419471806, 1] | 12 |

### 到达等级与 EXP

| 阶段 | 原型/职业 | 到达数 | 分布 | 目标级占比 [95%] | EXP p10/p50/p90 | EXP 来源 | 脆弱门槛级 | 通过 |
|---|---|---:|---|---|---|---|---|---|
| before | P0a/hero | 17 | {'5': 17} | 0.0 [0, 0.1843181350088518] | [143.0, 145.0, 145.0] | {'trash': 19.11764705882353, 'elite': 45.88235294117647, 'boss': 80, 'unclassified': 0, 'quest': 0} | [5] | False |
| before | P0a/cleric | 0 | {} | None None | [None, None, None] | {} | [] | False |
| before | P0a/mage | 0 | {} | None None | [None, None, None] | {} | [] | False |
| before | P0a/thief | 9 | {'4': 8, '5': 1} | 0.8888888888888888 [0.5650002944233439, 0.9801091123614551] | [94.0, 95.0, 113.0] | {'trash': 10, 'elite': 46.666666666666664, 'boss': 44.44444444444444, 'unclassified': 0, 'quest': 0} | [4] | True |
| before | P0b/hero | 94 | {'4': 90, '5': 4} | 0.9574468085106383 [0.8956435421811827, 0.9833294518499572] | [95.0, 95.0, 105.0] | {'trash': 9.095744680851064, 'elite': 48.351063829787236, 'boss': 41.702127659574465, 'unclassified': 0, 'quest': 0} | [] | True |
| before | P0b/cleric | 58 | {'4': 58} | 1.0 [0.9378821442127971, 1] | [95.0, 95.0, 105.0] | {'trash': 8.189655172413794, 'elite': 49.6551724137931, 'boss': 40, 'unclassified': 0, 'quest': 0} | [] | True |
| before | P0b/mage | 3 | {'4': 3} | 1.0 [0.4385029682449546, 1] | [95.0, 95.0, 103.0] | {'trash': 8.333333333333334, 'elite': 50, 'boss': 40, 'unclassified': 0, 'quest': 0} | [] | True |
| before | P0b/thief | 63 | {'4': 61, '5': 2} | 0.9682539682539683 [0.8914352295339257, 0.9912504724384196] | [95.0, 95.0, 105.0] | {'trash': 8.174603174603174, 'elite': 50.714285714285715, 'boss': 41.26984126984127, 'unclassified': 0, 'quest': 0} | [] | True |
| before | P1/hero | 220 | {'4': 164, '5': 56} | 0.2545454545454545 [0.20153739997479517, 0.3159782534300895] | [105.0, 105.0, 155.0] | {'trash': 11.159090909090908, 'elite': 48.27272727272727, 'boss': 50.18181818181818, 'unclassified': 0, 'quest': 9.409090909090908} | [] | False |
| before | P1/cleric | 55 | {'4': 55} | 0.0 [0, 0.06528490111708637] | [105.0, 105.0, 115.0] | {'trash': 8.545454545454545, 'elite': 49.09090909090909, 'boss': 40, 'unclassified': 0, 'quest': 9.818181818181818} | [] | False |
| before | P1/mage | 17 | {'4': 8, '5': 9} | 0.5294117647058824 [0.30963235060004424, 0.7383489355759056] | [105.0, 155.0, 159.0] | {'trash': 14.411764705882353, 'elite': 46.76470588235294, 'boss': 61.1764705882353, 'unclassified': 0, 'quest': 9.411764705882353} | [] | False |
| before | P1/thief | 123 | {'4': 104, '5': 19} | 0.15447154471544716 [0.10117791843878991, 0.22869418497057037] | [105.0, 105.0, 155.0] | {'trash': 10.24390243902439, 'elite': 48.78048780487805, 'boss': 46.17886178861789, 'unclassified': 0, 'quest': 9.91869918699187} | [] | False |
| before | P2/hero | 122 | {'7': 122} | 0.0 [0, 0.030526178389012868] | [315.0, 330.0, 340.0] | {'trash': 20.69672131147541, 'elite': 117.29508196721312, 'boss': 160, 'unclassified': 0, 'quest': 29.42622950819672} | [] | False |
| before | P2/cleric | 45 | {'7': 45} | 0.0 [0, 0.07865159873288836] | [317.0, 330.0, 340.0] | {'trash': 21.555555555555557, 'elite': 119.33333333333333, 'boss': 160, 'unclassified': 0, 'quest': 29.77777777777778} | [] | False |
| before | P2/mage | 24 | {'7': 24} | 0.0 [1.3877787807814457e-17, 0.13797620467498017] | [315.0, 330.0, 335.0] | {'trash': 22.291666666666668, 'elite': 114.375, 'boss': 160, 'unclassified': 0, 'quest': 29.583333333333332} | [] | False |
| before | P2/thief | 225 | {'7': 225} | 0.0 [1.734723475976807e-18, 0.016786551005620237] | [315.0, 325.0, 340.0] | {'trash': 18.555555555555557, 'elite': 116.13333333333334, 'boss': 160, 'unclassified': 0, 'quest': 29.244444444444444} | [] | False |
| before | P3/hero | 156 | {'8': 156} | 0.0 [0, 0.024032931437414938] | [550.0, 565.0, 575.0] | {'trash': 26.602564102564102, 'elite': 147.8846153846154, 'boss': 280, 'unclassified': 0, 'quest': 109.67948717948718} | [] | False |
| before | P3/cleric | 21 | {'8': 21} | 0.0 [0, 0.154639018924847] | [595.0, 605.0, 610.0] | {'trash': 27.142857142857142, 'elite': 147.85714285714286, 'boss': 320, 'unclassified': 0, 'quest': 110} | [] | False |
| before | P3/mage | 56 | {'8': 56} | 0.0 [6.938893903907228e-18, 0.06419393671876342] | [590.0, 602.5, 612.5] | {'trash': 27.410714285714285, 'elite': 143.83928571428572, 'boss': 320, 'unclassified': 0, 'quest': 109.46428571428571} | [] | False |
| before | P3/thief | 57 | {'8': 57} | 0.0 [0, 0.06313883485297894] | [555.0, 565.0, 580.0] | {'trash': 28.50877192982456, 'elite': 145.52631578947367, 'boss': 280, 'unclassified': 0, 'quest': 110} | [] | False |
| before | P2s/hero | 78 | {'6': 47, '7': 31} | 0.6025641025641025 [0.4916185829131174, 0.7038813535561761] | [253.5, 270.0, 300.0] | {'trash': 20.512820512820515, 'elite': 63.26923076923077, 'boss': 160, 'unclassified': 0, 'quest': 29.23076923076923} | [] | None |
| before | P2s/cleric | 47 | {'6': 31, '7': 16} | 0.6595744680851063 [0.5167092456194193, 0.7783255615622839] | [245.0, 270.0, 290.0] | {'trash': 21.80851063829787, 'elite': 58.723404255319146, 'boss': 160, 'unclassified': 0, 'quest': 30} | [] | None |
| before | P2s/mage | 20 | {'6': 20} | 1.0 [0.8388748419471806, 1] | [240.0, 260.0, 270.5] | {'trash': 20.25, 'elite': 49.5, 'boss': 160, 'unclassified': 0, 'quest': 28} | [] | None |
| before | P2s/thief | 140 | {'6': 115, '7': 25} | 0.8214285714285714 [0.7496696703597742, 0.8760192008313173] | [240.0, 265.0, 280.0] | {'trash': 18.214285714285715, 'elite': 54.107142857142854, 'boss': 160, 'unclassified': 0, 'quest': 29.357142857142858} | [7] | None |
| before | P0g/hero | 94 | {'4': 90, '5': 4} | 0.9574468085106383 [0.8956435421811827, 0.9833294518499572] | [95.0, 95.0, 105.0] | {'trash': 9.095744680851064, 'elite': 48.351063829787236, 'boss': 41.702127659574465, 'unclassified': 0, 'quest': 0} | [] | None |
| before | P0g/cleric | 58 | {'4': 58} | 1.0 [0.9378821442127971, 1] | [95.0, 95.0, 105.0] | {'trash': 8.189655172413794, 'elite': 49.6551724137931, 'boss': 40, 'unclassified': 0, 'quest': 0} | [] | None |
| before | P0g/mage | 3 | {'4': 3} | 1.0 [0.4385029682449546, 1] | [95.0, 95.0, 103.0] | {'trash': 8.333333333333334, 'elite': 50, 'boss': 40, 'unclassified': 0, 'quest': 0} | [] | None |
| before | P0g/thief | 63 | {'4': 61, '5': 2} | 0.9682539682539683 [0.8914352295339257, 0.9912504724384196] | [95.0, 95.0, 105.0] | {'trash': 8.174603174603174, 'elite': 50.714285714285715, 'boss': 41.26984126984127, 'unclassified': 0, 'quest': 0} | [] | None |
| after | P0a/hero | 0 | {} | None None | [None, None, None] | {} | [] | False |
| after | P0a/cleric | 1 | {'5': 1} | 0.0 [0, 0.7934506856227626] | [145.0, 145.0, 145.0] | {'trash': 20, 'elite': 45, 'boss': 80, 'unclassified': 0, 'quest': 0} | [] | False |
| after | P0a/mage | 0 | {} | None None | [None, None, None] | {} | [] | False |
| after | P0a/thief | 2 | {'4': 2} | 1.0 [0.34238022750665303, 1] | [96.0, 100.0, 104.0] | {'trash': 7.5, 'elite': 52.5, 'boss': 40, 'unclassified': 0, 'quest': 0} | [] | True |
| after | P0b/hero | 2 | {'4': 2} | 1.0 [0.34238022750665303, 1] | [95.0, 95.0, 95.0] | {'trash': 10, 'elite': 45, 'boss': 40, 'unclassified': 0, 'quest': 0} | [] | True |
| after | P0b/cleric | 2 | {'4': 2} | 1.0 [0.34238022750665303, 1] | [105.0, 105.0, 105.0] | {'trash': 5, 'elite': 60, 'boss': 40, 'unclassified': 0, 'quest': 0} | [] | True |
| after | P0b/mage | 0 | {} | None None | [None, None, None] | {} | [] | False |
| after | P0b/thief | 3 | {'4': 2, '5': 1} | 0.6666666666666666 [0.2076596008020477, 0.9385080552796037] | [97.0, 105.0, 137.0] | {'trash': 11.666666666666666, 'elite': 50, 'boss': 53.333333333333336, 'unclassified': 0, 'quest': 0} | [5] | False |
| after | P1/hero | 5 | {'4': 4, '5': 1} | 0.2 [0.03622410863243014, 0.6244653702374747] | [105.0, 105.0, 145.0] | {'trash': 10, 'elite': 51, 'boss': 48, 'unclassified': 0, 'quest': 10} | [] | False |
| after | P1/cleric | 0 | {} | None None | [None, None, None] | {} | [] | False |
| after | P1/mage | 2 | {'5': 2} | 1.0 [0.34238022750665303, 1] | [155.0, 155.0, 155.0] | {'trash': 20, 'elite': 45, 'boss': 80, 'unclassified': 0, 'quest': 10} | [] | True |
| after | P1/thief | 6 | {'4': 5, '5': 1} | 0.16666666666666666 [0.030053369748306635, 0.5635028221864702] | [105.0, 105.0, 135.0] | {'trash': 10.833333333333334, 'elite': 47.5, 'boss': 46.666666666666664, 'unclassified': 0, 'quest': 10} | [] | False |
| after | P2/hero | 5 | {'7': 5} | 0.0 [0, 0.43448246478317476] | [321.0, 330.0, 330.0] | {'trash': 20, 'elite': 117, 'boss': 160, 'unclassified': 0, 'quest': 30} | [] | False |
| after | P2/cleric | 1 | {'6': 1} | 1.0 [0.20654931437723745, 1] | [275.0, 275.0, 275.0] | {'trash': 20, 'elite': 105, 'boss': 120, 'unclassified': 0, 'quest': 30} | [] | True |
| after | P2/mage | 1 | {'6': 1} | 1.0 [0.20654931437723745, 1] | [260.0, 260.0, 260.0] | {'trash': 20, 'elite': 90, 'boss': 120, 'unclassified': 0, 'quest': 30} | [] | True |
| after | P2/thief | 10 | {'6': 2, '7': 8} | 0.2 [0.05668215145437519, 0.5098375284633583] | [261.5, 317.5, 331.5] | {'trash': 20, 'elite': 108, 'boss': 148, 'unclassified': 0, 'quest': 30} | [] | False |
| after | P3/hero | 10 | {'8': 10} | 0.0 [0, 0.2775327998628892] | [532.5, 565.0, 575.0] | {'trash': 25, 'elite': 153, 'boss': 272, 'unclassified': 0, 'quest': 107} | [] | False |
| after | P3/cleric | 4 | {'8': 4} | 0.0 [0, 0.4898908364545973] | [555.0, 580.0, 608.5] | {'trash': 26.25, 'elite': 150, 'boss': 300, 'unclassified': 0, 'quest': 105} | [] | False |
| after | P3/mage | 9 | {'8': 9} | 0.0 [0, 0.2991450484195441] | [505.0, 525.0, 606.0] | {'trash': 26.11111111111111, 'elite': 126.66666666666667, 'boss': 288.8888888888889, 'unclassified': 0, 'quest': 100} | [] | False |
| after | P3/thief | 5 | {'8': 5} | 0.0 [0, 0.43448246478317476] | [491.0, 500.0, 568.0] | {'trash': 26, 'elite': 138, 'boss': 256, 'unclassified': 0, 'quest': 104} | [] | False |
| after | P2s/hero | 3 | {'7': 3} | 0.0 [5.551115123125783e-17, 0.5614970317550454] | [282.0, 290.0, 298.0] | {'trash': 20, 'elite': 80, 'boss': 160, 'unclassified': 0, 'quest': 30} | [7] | None |
| after | P2s/cleric | 0 | {} | None None | [None, None, None] | {} | [] | None |
| after | P2s/mage | 1 | {'6': 1} | 1.0 [0.20654931437723745, 1] | [200.0, 200.0, 200.0] | {'trash': 20, 'elite': 30, 'boss': 120, 'unclassified': 0, 'quest': 30} | [6] | None |
| after | P2s/thief | 5 | {'6': 2, '7': 3} | 0.4 [0.11762077423264783, 0.769275718723987] | [264.0, 280.0, 280.0] | {'trash': 18, 'elite': 66, 'boss': 160, 'unclassified': 0, 'quest': 30} | [7] | None |
| after | P0g/hero | 2 | {'4': 2} | 1.0 [0.34238022750665303, 1] | [95.0, 95.0, 95.0] | {'trash': 10, 'elite': 45, 'boss': 40, 'unclassified': 0, 'quest': 0} | [] | None |
| after | P0g/cleric | 2 | {'4': 2} | 1.0 [0.34238022750665303, 1] | [105.0, 105.0, 105.0] | {'trash': 5, 'elite': 60, 'boss': 40, 'unclassified': 0, 'quest': 0} | [] | None |
| after | P0g/mage | 0 | {} | None None | [None, None, None] | {} | [] | None |
| after | P0g/thief | 3 | {'4': 2, '5': 1} | 0.6666666666666666 [0.2076596008020477, 0.9385080552796037] | [97.0, 105.0, 137.0] | {'trash': 11.666666666666666, 'elite': 50, 'boss': 53.333333333333336, 'unclassified': 0, 'quest': 0} | [5] | None |

P0g 只报告；P2s 的硬口径是与 P2 到达等级差 ≤1，不额外要求固定 Lv6。

| 阶段 | 职业 | P2s/P2 通关差 pp | Ignis 等级均值差 |
|---|---|---:|---|
| before | hero | 9.0 | 0.6025641025641022 |
| before | cleric | 0.7999999999999994 | 0.6595744680851068 |
| before | mage | 0.4 | 1 |
| before | thief | 17.200000000000003 | 0.8214285714285712 |
| after | hero | 10.0 | 0 |
| after | cleric | 5.0 | None |
| after | mage | 0 | 0 |
| after | thief | 24.999999999999996 | 0.20000000000000018 |

### M13 到达等级差（硬门槛）

| 阶段 | 职业/P0 | P0均值 | P2均值 | 差值 | ≥2 |
|---|---|---:|---:|---:|---|
| before | cleric/P0b | 4 | 7 | 3 | True |
| before | hero/P0a | 5 | 7 | 2 | True |
| before | hero/P0b | 4.042553191489362 | 7 | 2.957446808510638 | True |
| before | mage/P0b | 4 | 7 | 3 | True |
| before | thief/P0a | 4.111111111111111 | 7 | 2.8888888888888893 | True |
| before | thief/P0b | 4.031746031746032 | 7 | 2.9682539682539684 | True |
| after | cleric/P0a | 5 | 6 | 1 | False |
| after | cleric/P0b | 4 | 6 | 2 | True |
| after | hero/P0b | 4 | 7 | 3 | True |
| after | thief/P0a | 4 | 6.8 | 2.8 | True |
| after | thief/P0b | 4.333333333333333 | 6.8 | 2.466666666666667 | True |

### M9 逐遭遇

主值为开场，不计有限护盾/玩家防御姿态；保留实际防御、闪避与装备。辅助前三回合是独立同种子 heuristic_v3 重放，战斗不足三回合记缺失，不补零。HEAD 列仍是 053 旧口径；同快照修正另见 corrected-head-m9.json。

| 阶段 | 遭遇/职业 | 分类/等级 | 主值 | 计入护盾 | 前三回合 | 范围 | Q5后通过 |
|---|---|---|---:|---|---|---|---|
| before | dark_forest_loc/hero | trash/1 | 0.400000 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | dark_forest_loc/cleric | trash/1 | 0.444444 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | dark_forest_loc/mage | trash/1 | 0.666667 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | dark_forest_loc/thief | trash/1 | 0.571429 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | goblin_fort/hero | trash/1 | 0.130667 | None | None | [0.1, 0.15]; Q5上限=0.20 | True |
| before | goblin_fort/cleric | trash/1 | 0.182778 | None | None | [0.1, 0.15]; Q5上限=0.20 | True |
| before | goblin_fort/mage | trash/1 | 0.274167 | None | None | [0.1, 0.15]; Q5上限=0.20 | False |
| before | goblin_fort/thief | trash/1 | 0.156190 | None | None | [0.1, 0.15]; Q5上限=0.20 | True |
| before | goblin_fort_first_second/hero | elite/1 | 0.261333 | None | None | [0.18, 0.25]; Q5上限=0.30 | True |
| before | goblin_fort_first_second/cleric | elite/1 | 0.365556 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | goblin_fort_first_second/mage | elite/1 | 0.548333 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | goblin_fort_first_second/thief | elite/1 | 0.312381 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | goblin_fort_second_right/hero | elite/2 | 0.078400 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | goblin_fort_second_right/cleric | elite/2 | 0.143043 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | goblin_fort_second_right/mage | elite/2 | 0.000000 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | goblin_fort_second_right/thief | elite/1 | 0.156190 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | goblin_fort_fourth/hero | boss/2 | 0.494900 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | goblin_fort_fourth/cleric | boss/2 | 0.653913 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | goblin_fort_fourth/mage | boss/2 | 0.000000 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | goblin_fort_fourth/thief | boss/2 | 0.592014 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | cave_heat_corridor/hero | elite/4 | 0.280000 | None | None | [0.18, 0.25]; Q5上限=0.30 | True |
| before | cave_heat_corridor/cleric | elite/4 | 0.398788 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | cave_heat_corridor/mage | elite/4 | 0.000000 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | cave_heat_corridor/thief | elite/3 | 0.409091 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | cave_lava_room/hero | elite/4 | 0.204000 | None | None | [0.18, 0.25]; Q5上限=0.30 | True |
| before | cave_lava_room/cleric | elite/4 | 0.341818 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | cave_lava_room/mage | elite/4 | 0.000000 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | cave_lava_room/thief | elite/4 | 0.271978 | None | None | [0.18, 0.25]; Q5上限=0.30 | True |
| before | cave_crystal_corridor/hero | elite/4 | 0.192500 | None | None | [0.18, 0.25]; Q5上限=0.30 | True |
| before | cave_crystal_corridor/cleric | elite/4 | 0.328763 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | cave_crystal_corridor/mage | elite/4 | 0.000000 | None | None | [0.18, 0.25]; Q5上限=0.30 | False |
| before | cave_crystal_corridor/thief | elite/4 | 0.250000 | None | None | [0.18, 0.25]; Q5上限=0.30 | True |
| before | cave_prism_tree/hero | boss/5 | 0.114625 | None | None | [0.28, 0.35]; Q5上限=0.40 | False |
| before | cave_prism_tree/cleric | boss/5 | 0.158139 | None | None | [0.28, 0.35]; Q5上限=0.40 | False |
| before | cave_prism_tree/mage | boss/5 | 0.000000 | None | None | [0.28, 0.35]; Q5上限=0.40 | False |
| before | cave_prism_tree/thief | boss/4 | 0.158654 | None | None | [0.28, 0.35]; Q5上限=0.40 | False |
| before | slime_ambush_one/hero | trash/5 | 0.049000 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | slime_ambush_one/cleric | trash/5 | 0.086579 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | slime_ambush_one/mage | trash/5 | 0.000000 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | slime_ambush_one/thief | trash/5 | 0.066667 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | slime_ambush_two/hero | trash/5 | 0.049000 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | slime_ambush_two/cleric | trash/5 | 0.086579 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | slime_ambush_two/mage | trash/5 | 0.000000 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | slime_ambush_two/thief | trash/5 | 0.066667 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | slime_king_battle/hero | boss/5 | 0.093100 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | slime_king_battle/cleric | boss/5 | 0.136053 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | slime_king_battle/mage | boss/5 | 0.000000 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | slime_king_battle/thief | boss/5 | 0.115000 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | forest_wolves/hero | elite/6 | 0.103444 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | forest_wolves/cleric | elite/6 | 0.142093 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | forest_wolves/mage | elite/6 | 0.000000 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | forest_wolves/thief | elite/6 | 0.123162 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | village_fire_elemental/hero | elite/6 | 0.085804 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | village_fire_elemental/cleric | elite/6 | 0.104712 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | village_fire_elemental/thief | elite/6 | 0.105662 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | ice_elemental_encounter/hero | elite/6 | 0.111611 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | ice_elemental_encounter/cleric | elite/6 | 0.128430 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | ice_elemental_encounter/mage | elite/6 | 0.000000 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | ice_elemental_encounter/thief | elite/6 | 0.129596 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | frost_wolf_battle/hero | boss/6 | 0.072593 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | frost_wolf_battle/cleric | boss/6 | 0.087442 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | frost_wolf_battle/mage | boss/6 | 0.000000 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | frost_wolf_battle/thief | boss/6 | 0.088235 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | valley_entrance/hero | elite/7 | 0.870158 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | valley_entrance/cleric | elite/7 | 0.905321 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | valley_entrance/mage | elite/7 | 0.000000 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | valley_entrance/thief | elite/7 | 0.912418 | None | None | [0.18, 0.25]; Q5上限=0.25 | False |
| before | dragon_valley_loc/hero | boss/7 | 0.122640 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | dragon_valley_loc/cleric | boss/7 | 0.137643 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | dragon_valley_loc/mage | boss/7 | 0.000000 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | dragon_valley_loc/thief | boss/7 | 0.138722 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | draco_battle/hero | boss/8 | 0.075727 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | draco_battle/cleric | boss/8 | 0.090157 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | draco_battle/mage | boss/8 | 0.000000 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | draco_battle/thief | boss/8 | 0.090774 | None | None | [0.28, 0.35]; Q5上限=0.35 | False |
| before | village_fire_slime/hero | trash/6 | 0.021778 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | village_fire_slime/cleric | trash/6 | 0.021860 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | village_fire_slime/mage | trash/6 | 0.000000 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| before | village_fire_slime/thief | trash/6 | 0.022059 | None | None | [0.1, 0.15]; Q5上限=0.15 | False |
| after | dark_forest_loc/hero | trash/1 | 0.400000 | 0.4 | 0.166 | [0.1, 0.15]; Q5上限=0.15 | False |
| after | dark_forest_loc/cleric | trash/1 | 0.444444 | 0.4444444444444444 | 0.18296296296296294 | [0.1, 0.15]; Q5上限=0.15 | False |
| after | dark_forest_loc/mage | trash/1 | 0.666667 | 0.6666666666666666 | 0.27444444444444444 | [0.1, 0.15]; Q5上限=0.15 | False |
| after | dark_forest_loc/thief | trash/1 | 0.571429 | 0.5714285714285714 | 0.22952380952380952 | [0.1, 0.15]; Q5上限=0.15 | False |
| after | goblin_fort_first_second/hero | elite/1 | 0.261333 | 0.2613333333333333 | None | [0.18, 0.25]; Q5上限=0.30 | True |
| after | goblin_fort_first_second/cleric | elite/1 | 0.365556 | 0.3655555555555555 | 0.3046296296296296 | [0.18, 0.25]; Q5上限=0.30 | False |
| after | goblin_fort_first_second/mage | elite/1 | 0.548333 | 0.5483333333333332 | 0.36555555555555547 | [0.18, 0.25]; Q5上限=0.30 | False |
| after | goblin_fort_first_second/thief | elite/1 | 0.312381 | 0.31238095238095237 | None | [0.18, 0.25]; Q5上限=0.30 | False |
| after | goblin_fort_second_right/hero | elite/1 | 0.130667 | 0.13066666666666665 | None | [0.18, 0.25]; Q5上限=0.30 | False |
| after | goblin_fort_second_right/cleric | elite/2 | 0.143043 | 0.14304347826086955 | None | [0.18, 0.25]; Q5上限=0.30 | False |
| after | goblin_fort_second_right/mage | elite/1 | 0.274167 | 0.2741666666666666 | None | [0.18, 0.25]; Q5上限=0.30 | True |
| after | goblin_fort_second_right/thief | elite/1 | 0.156190 | 0.15619047619047619 | None | [0.18, 0.25]; Q5上限=0.30 | False |
| after | goblin_fort_fourth/hero | boss/2 | 0.494900 | 0.49489999999999995 | 0.49489999999999995 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | goblin_fort_fourth/cleric | boss/2 | 0.653913 | 0.6539130434782607 | 0.6539130434782607 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | goblin_fort_fourth/mage | boss/2 | 1.002667 | 0.0 | 0.8564444444444443 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | goblin_fort_fourth/thief | boss/2 | 0.592014 | 0.5920138888888888 | 0.5920138888888888 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | cave_heat_corridor/hero | elite/4 | 0.280000 | 0.2800000000000001 | 0.2800000000000001 | [0.18, 0.25]; Q5上限=0.30 | True |
| after | cave_heat_corridor/cleric | elite/4 | 0.398788 | 0.39878787878787886 | None | [0.18, 0.25]; Q5上限=0.30 | False |
| after | cave_heat_corridor/mage | elite/3 | 0.731111 | 0.0 | None | [0.18, 0.25]; Q5上限=0.30 | False |
| after | cave_heat_corridor/thief | elite/3 | 0.409091 | 0.40909090909090917 | 0.340909090909091 | [0.18, 0.25]; Q5上限=0.30 | False |
| after | cave_lava_room/hero | elite/4 | 0.204000 | 0.204 | 0.13599999999999998 | [0.18, 0.25]; Q5上限=0.30 | True |
| after | cave_lava_room/cleric | elite/4 | 0.341818 | 0.34181818181818174 | 0.22787878787878785 | [0.18, 0.25]; Q5上限=0.30 | False |
| after | cave_lava_room/mage | elite/4 | 0.537143 | 0.0 | 0.358095238095238 | [0.18, 0.25]; Q5上限=0.30 | False |
| after | cave_lava_room/thief | elite/4 | 0.271978 | 0.27197802197802196 | 0.1813186813186813 | [0.18, 0.25]; Q5上限=0.30 | True |
| after | cave_crystal_corridor/hero | elite/4 | 0.192500 | 0.19250000000000003 | 0.1831666666666667 | [0.18, 0.25]; Q5上限=0.30 | True |
| after | cave_crystal_corridor/cleric | elite/4 | 0.328763 | 0.3287626262626262 | 0.3287626262626262 | [0.18, 0.25]; Q5上限=0.30 | False |
| after | cave_crystal_corridor/mage | elite/4 | 0.516627 | 0.0 | 0.4271031746031746 | [0.18, 0.25]; Q5上限=0.30 | False |
| after | cave_crystal_corridor/thief | elite/4 | 0.250000 | 0.25 | 0.25 | [0.18, 0.25]; Q5上限=0.30 | True |
| after | cave_prism_tree/hero | boss/5 | 0.114625 | 0.11462499999999998 | 0.07641666666666665 | [0.28, 0.35]; Q5上限=0.40 | False |
| after | cave_prism_tree/thief | boss/4 | 0.158654 | 0.15865384615384615 | 0.10576923076923077 | [0.28, 0.35]; Q5上限=0.40 | False |
| after | slime_ambush_one/hero | trash/5 | 0.049000 | 0.049 | None | [0.1, 0.15]; Q5上限=0.15 | False |
| after | slime_ambush_one/cleric | trash/4 | 0.099697 | 0.09969696969696969 | None | [0.1, 0.15]; Q5上限=0.15 | False |
| after | slime_ambush_one/mage | trash/4 | 0.156667 | 0.0 | None | [0.1, 0.15]; Q5上限=0.15 | False |
| after | slime_ambush_one/thief | trash/5 | 0.066667 | 0.06666666666666667 | None | [0.1, 0.15]; Q5上限=0.15 | False |
| after | slime_ambush_two/hero | trash/5 | 0.049000 | 0.049 | None | [0.1, 0.15]; Q5上限=0.15 | False |
| after | slime_ambush_two/cleric | trash/4 | 0.099697 | 0.09969696969696969 | 0.09969696969696969 | [0.1, 0.15]; Q5上限=0.15 | False |
| after | slime_ambush_two/mage | trash/4 | 0.156667 | 0.0 | None | [0.1, 0.15]; Q5上限=0.15 | False |
| after | slime_ambush_two/thief | trash/5 | 0.066667 | 0.06666666666666667 | None | [0.1, 0.15]; Q5上限=0.15 | False |
| after | slime_king_battle/hero | boss/5 | 0.093100 | 0.0931 | 0.0931 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | slime_king_battle/cleric | boss/4 | 0.156667 | 0.15666666666666668 | 0.15666666666666668 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | slime_king_battle/mage | boss/4 | 0.246190 | 0.0 | 0.24619047619047618 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | slime_king_battle/thief | boss/5 | 0.115000 | 0.11500000000000003 | 0.11500000000000003 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | forest_wolves/hero | elite/6 | 0.103444 | 0.10344444444444444 | None | [0.18, 0.25]; Q5上限=0.25 | False |
| after | forest_wolves/cleric | elite/5 | 0.160789 | 0.1607894736842105 | None | [0.18, 0.25]; Q5上限=0.25 | False |
| after | forest_wolves/mage | elite/5 | 0.254583 | 0.0 | None | [0.18, 0.25]; Q5上限=0.25 | False |
| after | forest_wolves/thief | elite/6 | 0.123162 | 0.12316176470588236 | None | [0.18, 0.25]; Q5上限=0.25 | False |
| after | village_fire_slime/hero | trash/6 | 0.021778 | 0.021777777777777778 | None | [0.1, 0.15]; Q5上限=0.15 | False |
| after | village_fire_slime/cleric | trash/5 | 0.024737 | 0.024736842105263154 | None | [0.1, 0.15]; Q5上限=0.15 | False |
| after | village_fire_slime/mage | trash/5 | 0.097917 | 0.0 | None | [0.1, 0.15]; Q5上限=0.15 | False |
| after | village_fire_slime/thief | trash/6 | 0.022059 | 0.022058823529411766 | 0.022058823529411766 | [0.1, 0.15]; Q5上限=0.15 | False |
| after | ice_elemental_encounter/hero | elite/6 | 0.111611 | 0.11161111111111113 | None | [0.18, 0.25]; Q5上限=0.25 | False |
| after | ice_elemental_encounter/cleric | elite/6 | 0.128430 | 0.12843023255813954 | 0.12843023255813954 | [0.18, 0.25]; Q5上限=0.25 | False |
| after | ice_elemental_encounter/mage | elite/5 | 0.332917 | 0.0 | None | [0.18, 0.25]; Q5上限=0.25 | False |
| after | ice_elemental_encounter/thief | elite/6 | 0.129596 | 0.12959558823529413 | None | [0.18, 0.25]; Q5上限=0.25 | False |
| after | frost_wolf_battle/hero | boss/6 | 0.072593 | 0.0725925925925926 | 0.0725925925925926 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | frost_wolf_battle/cleric | boss/6 | 0.087442 | 0.08744186046511628 | 0.08744186046511628 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | frost_wolf_battle/mage | boss/6 | 0.226296 | 0.0 | None | [0.28, 0.35]; Q5上限=0.35 | False |
| after | frost_wolf_battle/thief | boss/6 | 0.088235 | 0.08823529411764706 | 0.0803921568627451 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | valley_entrance/hero | elite/7 | 0.870158 | 0.8701583333333331 | None | [0.18, 0.25]; Q5上限=0.25 | False |
| after | valley_entrance/cleric | elite/6 | 1.010591 | 1.0105910852713178 | None | [0.18, 0.25]; Q5上限=0.25 | False |
| after | valley_entrance/mage | elite/6 | 1.809645 | 0.0 | None | [0.18, 0.25]; Q5上限=0.25 | False |
| after | valley_entrance/thief | elite/7 | 0.912418 | 0.9124177631578947 | None | [0.18, 0.25]; Q5上限=0.25 | False |
| after | dragon_valley_loc/hero | boss/7 | 0.122640 | 0.12263999999999997 | 0.12263999999999997 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | dragon_valley_loc/cleric | boss/6 | 0.153648 | 0.1536478405315615 | 0.1536478405315615 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | dragon_valley_loc/mage | boss/6 | 0.337206 | 0.0 | None | [0.28, 0.35]; Q5上限=0.35 | True |
| after | dragon_valley_loc/thief | boss/7 | 0.138722 | 0.13872180451127816 | 0.13872180451127816 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | draco_battle/hero | boss/8 | 0.075727 | 0.07572727272727273 | 0.14897979797979796 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | draco_battle/cleric | boss/7 | 0.099549 | 0.09954861111111109 | 0.09954861111111109 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | draco_battle/mage | boss/7 | 0.237611 | 0.0 | 0.3664259259259259 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | draco_battle/thief | boss/8 | 0.090774 | 0.09077380952380952 | 0.16418650793650794 | [0.28, 0.35]; Q5上限=0.35 | False |
| after | goblin_fort/hero | trash/1 | 0.130667 | 0.13066666666666665 | None | [0.1, 0.15]; Q5上限=0.20 | True |
| after | goblin_fort/cleric | trash/1 | 0.182778 | 0.18277777777777776 | None | [0.1, 0.15]; Q5上限=0.20 | True |
| after | goblin_fort/mage | trash/1 | 0.274167 | 0.2741666666666666 | None | [0.1, 0.15]; Q5上限=0.20 | False |
| after | goblin_fort/thief | trash/1 | 0.156190 | 0.15619047619047619 | None | [0.1, 0.15]; Q5上限=0.20 | True |
| after | village_fire_elemental/hero | elite/6 | 0.085804 | 0.08580444444444447 | 0.08580444444444447 | [0.18, 0.25]; Q5上限=0.25 | False |
| after | village_fire_elemental/thief | elite/6 | 0.105662 | 0.10566176470588239 | 0.10566176470588239 | [0.18, 0.25]; Q5上限=0.25 | False |

同一 HEAD N500 快照的口径对照：79 格中，严格基础带宽（未加Q5软例外）旧口径 4 格在带内，修正后 9 格在带内；魔法使い 的零值从 16 格变为 0 格。此差异纯属测量修正，不是敌人变弱。

| HEAD 遭遇/职业 | 旧口径 | 排除护盾/姿态 | 前三回合辅助 |
|---|---:|---:|---|
| dark_forest_loc/hero | 0.400000 | 0.400000 | 0.166 |
| dark_forest_loc/cleric | 0.444444 | 0.444444 | 0.18296296296296294 |
| dark_forest_loc/mage | 0.666667 | 0.666667 | 0.27444444444444444 |
| dark_forest_loc/thief | 0.571429 | 0.571429 | 0.22952380952380952 |
| goblin_fort/hero | 0.130667 | 0.130667 | None |
| goblin_fort/cleric | 0.182778 | 0.182778 | None |
| goblin_fort/mage | 0.274167 | 0.274167 | None |
| goblin_fort/thief | 0.156190 | 0.156190 | None |
| goblin_fort_first_second/hero | 0.261333 | 0.261333 | None |
| goblin_fort_first_second/cleric | 0.365556 | 0.365556 | None |
| goblin_fort_first_second/mage | 0.548333 | 0.548333 | 0.36555555555555547 |
| goblin_fort_first_second/thief | 0.312381 | 0.312381 | None |
| goblin_fort_second_right/hero | 0.078400 | 0.078400 | None |
| goblin_fort_second_right/cleric | 0.143043 | 0.143043 | None |
| goblin_fort_second_right/mage | 0.000000 | 0.219333 | None |
| goblin_fort_second_right/thief | 0.156190 | 0.156190 | None |
| goblin_fort_fourth/hero | 0.494900 | 0.494900 | 0.49489999999999995 |
| goblin_fort_fourth/cleric | 0.653913 | 0.653913 | 0.6539130434782607 |
| goblin_fort_fourth/mage | 0.000000 | 1.002667 | 1.0026666666666666 |
| goblin_fort_fourth/thief | 0.592014 | 0.592014 | 0.5920138888888888 |
| cave_heat_corridor/hero | 0.280000 | 0.280000 | 0.2333333333333334 |
| cave_heat_corridor/cleric | 0.398788 | 0.398788 | 0.33232323232323235 |
| cave_heat_corridor/mage | 0.000000 | 0.626667 | 0.5222222222222223 |
| cave_heat_corridor/thief | 0.409091 | 0.409091 | 0.340909090909091 |
| cave_lava_room/hero | 0.204000 | 0.204000 | 0.13599999999999998 |
| cave_lava_room/cleric | 0.341818 | 0.341818 | 0.22787878787878785 |
| cave_lava_room/mage | 0.000000 | 0.537143 | 0.4177777777777777 |
| cave_lava_room/thief | 0.271978 | 0.271978 | 0.21153846153846154 |
| cave_crystal_corridor/hero | 0.192500 | 0.192500 | 0.1645 |
| cave_crystal_corridor/cleric | 0.328763 | 0.328763 | 0.3287626262626262 |
| cave_crystal_corridor/mage | 0.000000 | 0.516627 | 0.4271031746031746 |
| cave_crystal_corridor/thief | 0.250000 | 0.250000 | 0.25 |
| cave_prism_tree/hero | 0.114625 | 0.114625 | 0.07641666666666665 |
| cave_prism_tree/cleric | 0.158139 | 0.158139 | 0.10542606516290726 |
| cave_prism_tree/mage | 0.000000 | 0.250387 | 0.16692460317460314 |
| cave_prism_tree/thief | 0.158654 | 0.158654 | 0.10576923076923077 |
| slime_ambush_one/hero | 0.049000 | 0.049000 | None |
| slime_ambush_one/cleric | 0.086579 | 0.086579 | None |
| slime_ambush_one/mage | 0.000000 | 0.137083 | None |
| slime_ambush_one/thief | 0.066667 | 0.066667 | None |
| slime_ambush_two/hero | 0.049000 | 0.049000 | None |
| slime_ambush_two/cleric | 0.086579 | 0.086579 | None |
| slime_ambush_two/mage | 0.000000 | 0.137083 | None |
| slime_ambush_two/thief | 0.066667 | 0.066667 | None |
| slime_king_battle/hero | 0.093100 | 0.093100 | 0.0931 |
| slime_king_battle/cleric | 0.136053 | 0.136053 | 0.13605263157894737 |
| slime_king_battle/mage | 0.000000 | 0.215417 | 0.21541666666666667 |
| slime_king_battle/thief | 0.115000 | 0.115000 | 0.11500000000000003 |
| forest_wolves/hero | 0.103444 | 0.103444 | None |
| forest_wolves/cleric | 0.142093 | 0.142093 | None |
| forest_wolves/mage | 0.000000 | 0.226296 | None |
| forest_wolves/thief | 0.123162 | 0.123162 | None |
| village_fire_elemental/hero | 0.085804 | 0.085804 | 0.08580444444444447 |
| village_fire_elemental/cleric | 0.104712 | 0.104712 | None |
| village_fire_elemental/thief | 0.105662 | 0.105662 | 0.10566176470588239 |
| ice_elemental_encounter/hero | 0.111611 | 0.111611 | None |
| ice_elemental_encounter/cleric | 0.128430 | 0.128430 | None |
| ice_elemental_encounter/mage | 0.000000 | 0.295926 | None |
| ice_elemental_encounter/thief | 0.129596 | 0.129596 | None |
| frost_wolf_battle/hero | 0.072593 | 0.072593 | 0.0725925925925926 |
| frost_wolf_battle/cleric | 0.087442 | 0.087442 | 0.08744186046511628 |
| frost_wolf_battle/mage | 0.000000 | 0.226296 | None |
| frost_wolf_battle/thief | 0.088235 | 0.088235 | 0.0803921568627451 |
| valley_entrance/hero | 0.870158 | 0.870158 | None |
| valley_entrance/cleric | 0.905321 | 0.905321 | 0.4526605902777778 |
| valley_entrance/mage | 0.000000 | 1.628681 | None |
| valley_entrance/thief | 0.912418 | 0.912418 | None |
| dragon_valley_loc/hero | 0.122640 | 0.122640 | 0.12263999999999997 |
| dragon_valley_loc/cleric | 0.137643 | 0.137643 | 0.11470238095238099 |
| dragon_valley_loc/mage | 0.000000 | 0.303486 | 0.3034857142857143 |
| dragon_valley_loc/thief | 0.138722 | 0.138722 | 0.13872180451127816 |
| draco_battle/hero | 0.075727 | 0.075727 | 0.14897979797979796 |
| draco_battle/cleric | 0.090157 | 0.090157 | 0.16307127882599579 |
| draco_battle/mage | 0.000000 | 0.216010 | 0.3331144781144781 |
| draco_battle/thief | 0.090774 | 0.090774 | 0.16418650793650794 |
| village_fire_slime/hero | 0.021778 | 0.021778 | 0.021777777777777778 |
| village_fire_slime/cleric | 0.021860 | 0.021860 | None |
| village_fire_slime/mage | 0.000000 | 0.087037 | None |
| village_fire_slime/thief | 0.022059 | 0.022059 | None |

M9 全矩阵尚有 65 格缺 P2 实测快照（规范范围 144 格，已测 79 格）。缺失不能当作通过，亦不借用 053 静态假想快照填补。

| 缺失遭遇 | 职业 |
|---|---|
| bone_field | cleric, hero, mage, thief |
| dragon_valley_return | cleric, hero, mage, thief |
| ghoul_marsh | cleric, hero, mage, thief |
| goblin_fort_chest_fight | cleric, hero, mage, thief |
| goblin_fort_second_left | cleric, hero, mage, thief |
| goblin_fort_third_guards | cleric, hero, mage, thief |
| gorge_giant_path | cleric, hero, mage, thief |
| gorge_rockfall_path | cleric, hero, mage, thief |
| gorge_worm_lair | cleric, hero, mage, thief |
| grave_chapel | cleric, hero, mage, thief |
| inn_night_ambush | cleric, hero, mage, thief |
| lost_goblin_crossroads | cleric, hero, mage, thief |
| mansion_corridor | cleric, hero, mage, thief |
| merchant_battle | cleric, hero, mage, thief |
| valley_ledge | cleric, hero, mage, thief |
| village_fire_elemental | mage |
| xanxus_phantom_battle | cleric, hero, mage, thief |

### M4 超限（Q4 已应用）

| 阶段 | 原型/职业/遭遇/策略 | n | 中位 | 胜率 | Q4 仅报告 | 沙袋 |
|---|---|---:|---:|---|---|---|
| before | P2/cleric/draco_battle/heuristic_v3 | 45 | 39 | 0.8888888888888888 [0.7650090300423141, 0.9515952820543282] | False | True |
| before | P2/hero/cave_prism_tree/heuristic_v3 | 125 | 16 | 0.984 [0.9435374990695339, 0.9956011998208062] | False | False |
| before | P2/hero/draco_battle/heuristic_v3 | 122 | 28.0 | 0.8852459016393442 [0.8165707956145146, 0.9304008374300164] | False | True |
| before | P2/thief/cave_prism_tree/heuristic_v3 | 241 | 15 | 0.9377593360995851 [0.8998600802973878, 0.961922074637911] | False | False |
| before | P2/thief/draco_battle/heuristic_v3 | 207 | 48 | 0.927536231884058 [0.8838959947010271, 0.9555973430420307] | False | True |
| before | P2/thief/goblin_fort_fourth/heuristic_v3 | 487 | 15 | 0.5318275154004107 [0.4874343181671261, 0.5757225310413359] | False | False |
| before | P2s/hero/cave_prism_tree/heuristic_v3 | 119 | 16 | 0.9915966386554622 [0.9539321145669224, 0.9985150569599106] | False | False |
| before | P2s/hero/draco_battle/heuristic_v3 | 77 | 43 | 0.8181818181818182 [0.7176371712788386, 0.8884874671777944] | False | True |
| before | P2s/thief/cave_prism_tree/heuristic_v3 | 148 | 16.0 | 0.9594594594594594 [0.9143814308173778, 0.9812896267203338] | False | False |
| before | P2s/thief/draco_battle/heuristic_v3 | 121 | 48 | 0.8760330578512396 [0.8055084227089188, 0.9234160937107464] | False | True |
| before | P3/cleric/dragon_valley_return/heuristic_v3 | 14 | 18.0 | 1 [0.7846891972623643, 1] | False | False |
| before | P3/hero/cave_prism_tree/heuristic_v3 | 202 | 19.0 | 0.9801980198019802 [0.9501998063661395, 0.9922731099815382] | False | True |
| before | P3/hero/draco_battle/heuristic_v3 | 53 | 22 | 0.018867924528301886 [0.0033384533882637665, 0.09942912052501235] | False | True |
| before | P3/thief/cave_prism_tree/heuristic_v3 | 221 | 16 | 0.7375565610859729 [0.675847192172072, 0.7911485325075792] | False | False |
| before | P3/thief/draco_battle/heuristic_v3 | 8 | 42.0 | 0 [0, 0.32440756488388023] | False | True |
| before | checkpoint/cleric/cave_prism_tree/attack_only | 500 | 22.0 | 0.994 [0.9825097478959467, 0.9979574037280398] | False | True |
| before | checkpoint/cleric/draco_battle/attack_only | 500 | 48.0 | 0.94 [0.9156389368747802, 0.9576516435190539] | False | True |
| before | checkpoint/cleric/draco_battle/best_free | 500 | 45.0 | 0.582 [0.5383026562362386, 0.6244469519280668] | False | True |
| before | checkpoint/cleric/draco_battle/heuristic_v3 | 500 | 41.0 | 0.968 [0.9486551309545582, 0.9802084863734289] | False | True |
| before | checkpoint/hero/cave_prism_tree/attack_only | 500 | 24.0 | 1 [0.9923756595384479, 1] | False | True |
| before | checkpoint/hero/cave_prism_tree/best_free | 500 | 20.0 | 1 [0.9923756595384479, 1] | False | True |
| before | checkpoint/hero/cave_prism_tree/heuristic_v3 | 500 | 15.0 | 1 [0.9923756595384479, 1] | False | False |
| before | checkpoint/hero/draco_battle/attack_only | 500 | 42.0 | 0.436 [0.39318560312305606, 0.47979031245602277] | False | True |
| before | checkpoint/hero/draco_battle/best_free | 500 | 38.0 | 0.33 [0.2902178997291812, 0.3723743760277467] | False | True |
| before | checkpoint/hero/draco_battle/heuristic_v3 | 500 | 27.0 | 0.99 [0.9768069002442693, 0.9957212461034096] | False | True |
| before | checkpoint/mage/cave_prism_tree/attack_only | 500 | 18.0 | 0.708 [0.6666807682036219, 0.7461475061643724] | False | False |
| before | checkpoint/thief/cave_prism_tree/attack_only | 500 | 28.0 | 0.808 [0.771179624871567, 0.8401237814041169] | False | True |
| before | checkpoint/thief/cave_prism_tree/best_free | 500 | 16.0 | 0.808 [0.771179624871567, 0.8401237814041169] | False | False |
| before | checkpoint/thief/cave_prism_tree/heuristic_v3 | 500 | 17.0 | 0.924 [0.8974035863260316, 0.9441309729625723] | False | False |
| before | checkpoint/thief/draco_battle/attack_only | 500 | 35.0 | 0.26 [0.22348572318538285, 0.3001739602361623] | False | True |
| before | checkpoint/thief/draco_battle/best_free | 500 | 25.0 | 0.124 [0.09794609113930344, 0.15578741288778383] | False | True |
| before | checkpoint/thief/draco_battle/heuristic_v3 | 500 | 48.0 | 0.912 [0.8839235279346099, 0.9337940155250711] | False | True |
| after | P2/hero/cave_prism_tree/heuristic_v3 | 5 | 17 | 1 [0.5655175352168251, 1] | False | False |
| after | P2/hero/draco_battle/heuristic_v3 | 5 | 28 | 0.8 [0.37553462976252533, 0.9637758913675698] | False | True |
| after | P2/thief/cave_prism_tree/heuristic_v3 | 7 | 16 | 1 [0.6456695649333126, 1] | False | False |
| after | P2/thief/draco_battle/heuristic_v3 | 9 | 44 | 0.7777777777777778 [0.45258896910698887, 0.9367748928821533] | False | True |
| after | P2s/hero/cave_prism_tree/heuristic_v3 | 4 | 25.0 | 1 [0.5101091635454027, 1] | False | True |
| after | P2s/hero/draco_battle/heuristic_v3 | 3 | 40 | 0.6666666666666666 [0.2076596008020477, 0.9385080552796037] | False | True |
| after | P2s/thief/cave_prism_tree/heuristic_v3 | 5 | 18 | 1 [0.5655175352168251, 1] | False | False |
| after | P2s/thief/draco_battle/heuristic_v3 | 2 | 49.5 | 1 [0.34238022750665303, 1] | False | True |
| after | P3/cleric/draco_battle/heuristic_v3 | 4 | 27.0 | 0.5 [0.15003898915214947, 0.8499610108478506] | False | True |
| after | P3/cleric/dragon_valley_loc/heuristic_v3 | 4 | 14.5 | 1 [0.5101091635454027, 1] | False | False |
| after | P3/cleric/dragon_valley_return/heuristic_v3 | 4 | 18.5 | 1 [0.5101091635454027, 1] | False | True |
| after | P3/cleric/merchant_battle/heuristic_v3 | 6 | 15.0 | 1 [0.6096657120978346, 1] | False | False |
| after | P3/hero/cave_prism_tree/heuristic_v3 | 11 | 19 | 0.9090909090909091 [0.6226415635484043, 0.9837678271141151] | False | True |
| after | P3/hero/draco_battle/heuristic_v3 | 8 | 22.5 | 0.75 [0.40927543031016883, 0.9285207872478909] | False | True |
| after | P3/mage/draco_battle/heuristic_v3 | 8 | 15.0 | 0.625 [0.30574239460262737, 0.8631557141764026] | False | False |
| after | P3/thief/cave_prism_tree/heuristic_v3 | 9 | 17 | 0.7777777777777778 [0.45258896910698887, 0.9367748928821533] | False | False |
| after | P3/thief/draco_battle/heuristic_v3 | 5 | 23 | 0.4 [0.11762077423264783, 0.769275718723987] | False | True |
| after | checkpoint/hero/cave_prism_tree/attack_only | 20 | 45.0 | 0.05 [0.008881448800795402, 0.23613119344674205] | True | True |
| after | checkpoint/hero/cave_prism_tree/best_free | 20 | 43.0 | 0.45 [0.2581978582556243, 0.6579146575496577] | False | True |
| after | checkpoint/hero/cave_prism_tree/heuristic_v3 | 20 | 24.5 | 1 [0.8388748419471806, 1] | False | True |
| after | checkpoint/hero/draco_battle/attack_only | 20 | 32.0 | 0 [0, 0.16112515805281938] | True | True |
| after | checkpoint/hero/draco_battle/best_free | 20 | 29.0 | 0 [0, 0.16112515805281938] | True | True |
| after | checkpoint/hero/draco_battle/heuristic_v3 | 20 | 38.5 | 0 [0, 0.16112515805281938] | False | True |
| after | checkpoint/thief/cave_prism_tree/attack_only | 20 | 29.0 | 0.8 [0.5839825677481064, 0.919342337420202] | False | True |
| after | checkpoint/thief/cave_prism_tree/best_free | 20 | 17.0 | 0.85 [0.6395811352592431, 0.9476312541037835] | False | False |
| after | checkpoint/thief/cave_prism_tree/heuristic_v3 | 20 | 17.0 | 1 [0.8388748419471806, 1] | False | False |
| after | checkpoint/thief/draco_battle/attack_only | 20 | 45.5 | 0.55 [0.3420853424503424, 0.7418021417443758] | False | True |
| after | checkpoint/thief/draco_battle/best_free | 20 | 31.0 | 0.35 [0.1811918241010821, 0.5671457233147637] | False | True |
| after | checkpoint/thief/draco_battle/heuristic_v3 | 20 | 49.0 | 1 [0.8388748419471806, 1] | False | True |

### M3 首测

| 阶段 | 职业/遭遇/同伴 | n | 回复 | 来伤 | S | S<0.5 |
|---|---|---:|---:|---:|---|---|
| before | cleric/dragon_valley_loc/fire_bat_dragon | 58 | 1.6500000000000001 | 10.340000000000002 | 0.15957446808510636 | True |
| before | cleric/frost_wolf_battle/fire_bat_dragon | 187 | 3.89 | 6.109999999999999 | 0.6366612111292963 | False |
| before | cleric/frost_wolf_battle/fire_bat_dragon | 70 | 4.04 | 6.109999999999999 | 0.6612111292962357 | False |
| before | cleric/frost_wolf_battle/none | 3 | 0.69 | 6.109999999999999 | 0.11292962356792144 | True |
| before | cleric/frost_wolf_battle/none | 3 | 1.6500000000000001 | 6.109999999999999 | 0.2700490998363339 | True |
| before | cleric/slime_king_battle/none | 124 | 0 | 5.17 | 0.0 | True |
| before | hero/dragon_valley_loc/fire_bat_dragon | 89 | 0.0 | 9.846666666666666 | 0.0 | True |
| before | hero/dragon_valley_loc/none | 5 | 0 | 9.846666666666666 | 0.0 | True |
| before | hero/frost_wolf_battle/fire_bat_dragon | 248 | 3.2 | 5.471666666666667 | 0.5848309473042949 | False |
| before | hero/frost_wolf_battle/none | 31 | 0 | 5.471666666666667 | 0.0 | True |
| before | hero/slime_king_battle/none | 170 | 0 | 4.508 | 0.0 | True |
| before | mage/dragon_valley_loc/fire_bat_dragon | 3 | 0.0 | 10.340000000000002 | 0.0 | True |
| before | mage/frost_wolf_battle/fire_bat_dragon | 99 | 3.2 | 6.109999999999999 | 0.5237315875613748 | False |
| before | mage/slime_king_battle/fire_bat_dragon | 11 | 3.0 | 5.17 | 0.5802707930367504 | False |
| before | mage/slime_king_battle/none | 41 | 0 | 5.17 | 0.0 | True |
| before | thief/dragon_valley_loc/fire_bat_dragon | 56 | 0.0 | 7.535714285714286 | 0.0 | True |
| before | thief/dragon_valley_loc/none | 7 | 0 | 7.535714285714286 | 0.0 | True |
| before | thief/frost_wolf_battle/fire_bat_dragon | 201 | 3.2 | 4.1875 | 0.764179104477612 | False |
| before | thief/frost_wolf_battle/none | 59 | 0 | 4.1875 | 0.0 | True |
| before | thief/slime_king_battle/fire_bat_dragon | 7 | 3.0 | 3.7720000000000002 | 0.7953340402969247 | False |
| before | thief/slime_king_battle/none | 45 | 0 | 3.7720000000000002 | 0.0 | True |
| after | cleric/dragon_valley_loc/fire_bat_dragon | 2 | 1.6500000000000001 | 10.340000000000002 | 0.15957446808510636 | True |
| after | cleric/frost_wolf_battle/fire_bat_dragon | 3 | 3.89 | 6.109999999999999 | 0.6366612111292963 | False |
| after | cleric/frost_wolf_battle/fire_bat_dragon | 3 | 4.04 | 6.109999999999999 | 0.6612111292962357 | False |
| after | cleric/frost_wolf_battle/none | 1 | 0.69 | 6.109999999999999 | 0.11292962356792144 | True |
| after | cleric/slime_king_battle/none | 8 | 0 | 5.17 | 0.0 | True |
| after | hero/dragon_valley_loc/fire_bat_dragon | 2 | 0.0 | 9.846666666666666 | 0.0 | True |
| after | hero/frost_wolf_battle/fire_bat_dragon | 9 | 3.2 | 5.471666666666667 | 0.5848309473042949 | False |
| after | hero/frost_wolf_battle/none | 1 | 0 | 5.471666666666667 | 0.0 | True |
| after | hero/slime_king_battle/none | 9 | 0 | 4.508 | 0.0 | True |
| after | mage/frost_wolf_battle/fire_bat_dragon | 3 | 3.2 | 6.109999999999999 | 0.5237315875613748 | False |
| after | mage/slime_king_battle/fire_bat_dragon | 1 | 3.0 | 5.17 | 0.5802707930367504 | False |
| after | mage/slime_king_battle/none | 3 | 0 | 5.17 | 0.0 | True |
| after | thief/dragon_valley_loc/fire_bat_dragon | 3 | 0.0 | 7.535714285714286 | 0.0 | True |
| after | thief/frost_wolf_battle/fire_bat_dragon | 7 | 3.2 | 4.1875 | 0.764179104477612 | False |
| after | thief/frost_wolf_battle/none | 2 | 0 | 4.1875 | 0.0 | True |
| after | thief/slime_king_battle/fire_bat_dragon | 1 | 3.0 | 3.7720000000000002 | 0.7953340402969247 | False |
| after | thief/slime_king_battle/none | 2 | 0 | 3.7720000000000002 | 0.0 | True |

M3b 保留在原始 JSON；分析期望伤害/回复比不是二项成功率，不人为套用 Wilson 区间。

### 参数变更全表

无游戏参数变更。L1/L2 尚未执行，未调整 EXP、成长、HP、防御或伤害；没有拆分 baby/normal 基础记录；未运行迁移，不更新 content_revision/overlay_revision。

### 迭代记录

| 阶段 | 改动 | 结果 |
|---|---|---|
| 第 0 步 | HEAD N500、冻结 v1 | 见 before-normal.json / before-baby.json |
| 测量修正 | M9 排除护盾；normal 可恢复战败继续；P3 护送分支 | 见测量修正后列；数值不变 |
| L1 前置审查 | 整数可行域检查 | C8 阻塞，0 轮数值迭代、0 次数值验收 |

### 推断与限制

- MP/SP 的 10–15% 依每级固定成长结构解释为初始上限的百分比；如果设计意指当前上限复利增长，需另行引擎任务。
- P3 同时枚举火种、商人、护送顺序的联合分支，同分按显式枚举顺序取第一项，沿用 053 决策口径。
- 辅助前三回合采用实际剩余敌人和实际状态；不到三回合就结束的样本不填平均值。
- 不虚构 P2 未到达的遭遇快照；缺样本不能认证 M9 全覆盖。
- raw 测量文件包含墙钟、代码/输入指纹，跨版本或跨运行不可能逐字节相同；baby 数值载荷与原始轨迹另做确定性字节比较，保留原始文件。
- 本交付没有完成 L1、L2 和数值验收；应在设计明确整数与教程例外后继续 052a。

### 验证与运行时长

最终叠加回归：Ran 952 tests in 950.197s /  / OK (skipped=1)。原地 unittest 因沙箱临时目录权限出现39个错误（941项、1跳过），未冒称通过。node语法检查通过；冻结benchmark194/194缓存命中、指标不变。

baby战斗两种模式113项金标、等级金标与冻结快照通过。HEAD与053的N500路线、探针、数值载荷相同，raw文件含时间/指纹/049目标元数据而不同；候选与HEAD另有84条抽样轨迹一致，详见verification.json。

normal四职业离线通玩exceptions=0、noncombat_dead_ends=0；四人均死亡，不是数值验收。workers1/2的两格N500记录一致。

各运行耗时（秒）：{"normal HEAD 全量": 5318.8683392, "baby HEAD 全量": 3209.0739409, "normal 修正后冒烟": 544.9307968000012}。详细命令、哈希与偏离项见`.tmp-test/052a/052a-report.txt`。

### 第0步逐轨迹差异定位

以原型、职业、seed配对HEAD与053共14000条路线；首个不同战斗的统计如下。此表不把ドラコ之后的结局传播误归为前段数值变化。

```json
{
  "paired_trials": 14000,
  "changed_trials": 495,
  "first_differing_battle_counts": {
    "non_battle_fields_only": 32,
    "valley_entrance": 90,
    "frost_wolf_battle": 38,
    "draco_battle": 48,
    "gorge_giant_path": 45,
    "ghoul_marsh": 50,
    "grave_chapel": 130,
    "xanxus_battle": 33,
    "dragon_valley_return": 1,
    "bone_field": 2,
    "dragon_valley_loc": 26
  },
  "all_first_battle_differences_at_draco": false
}
```

### 第0步额外发现：050c 文案改变了技能类型推断

HEAD 与053的变化并非仅在ドラコ。配对14000条路线有495条记录不同，其中463条首先在战斗中出现差异，32条只在非战斗字段（例如快照里的文案、判定探针）不同。28格统计有5格变化，见第0步表与 `head-vs-053-traces.json`。

已复现的具体原因：`host/combat.py::_ability_kind()` 在缺少显式 `kind` 时扫描名称/描述，遇到「防御」即推断为 `defend`。050c 文案落定后，两条正常攻击技能都触发了这条规则：

| 技能 | 053描述 | HEAD描述中的词 | 显式kind | 053推断 | HEAD推断 |
|---|---|---|---|---|---|
| dragon_slash（竜断ち） | 占位文案 | 防御と耐性を無視 | 无 | attack | defend |
| arcane_lance（魔力の槍） | 占位文案 | 防御力を無視 | 无 | attack | defend |

复现命令：`python -X utf8 .tmp-test/052a/pack_diff.py`，证据 `ability-kind-audit.json`。例如 P2/hero seed=14414081804636198878 在 valley_entrance 从两次竜断ち改为两次聖剣術；P3/mage seed=8023274666211617057 在 xanxus_battle 从魔力の槍改为普通攻击。`trace-diff-details.json` 保存逐字段证据。

这是已经存在于本次初始HEAD的问题，不是052改动引入。它影响勇者/法师策略选择，故不能把所有新基线变化归给049。当前基线如实保留此行为；本交付不修改引擎或050c文案。建议独立工程修复显式技能类型后重跑normal基线，再继续L1/L2。其余差异仍按完整逐轨迹表呈现，不把全部495条笼统归为同一原因。

### 运行期间的上游文档提交

测量基准始终为 `35a3cced66a3fd34b3eaaf2fd223b874f97d3dc2`。运行期间HEAD变为 `dfea0e7aeeb06eaaf50485a31e88d0c6f470343c`，仅新增以下文档修改：`docs/design/content054-texts-draft.md`, `docs/roles/dispatch-policy.md`。代码、测试与剧本均未改变；补丁以最新HEAD导出，manifest同时记录测量基准与补丁基准。未回退或修改这些上游文档。
