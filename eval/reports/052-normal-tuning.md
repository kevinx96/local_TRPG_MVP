# 052 normal 数值调参

> 当前交付状态见末尾「052a3」：数值候选已完成验收运行，触发停滞停止，仍有硬门槛待设计批准。下列052a/052a2暂停记录为历史。

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

## 052a 续跑（052a2）：dex 成长约束阻塞，未进行数值验收

基准 HEAD：`7b668259c7e2fb9f825cce332fab99f2063e9ac8`（含 050d）。本节取代上次报告的待裁定状态：HP／MP／SP 整数例外及教程 M9 豁免已批准，不能再视为阻塞。新的阻塞是勇者、魔法使い的 dex 成长。

### 1. 完成了什么

- 阅读共同规则、工程角色文档、052 spec 与续跑说明，确认 049、052a 第一部分、050d 已合入。
- 启动 HEAD normal/baby N=500、probe-n=500、seed=20261020 重测；在 L1 前置可行性检查发现新的设计冲突后，依续跑说明停止并取消未完成重测。没有完整 N500 JSON，不声称基线、M3 首测或数值验收完成，也不以旧 HEAD 的结果替代。
- 使用实际升级与闪避函数复核 Lv8 dex 可行域，并实际调用覆盖层校验验证小数被拒绝。证据：`.tmp-test/052a2/growth-feasibility.json`。
- 修复三个迁移脚本写 overlay_revision.json 时的 CRLF 转换，新增隔离测试；没有改动任何剧本数值、提示词、被动表或冻结产物。

### 2. 新的设计阻塞与 TODO(design)

052 §3.1 要求 dex 成长满足 G1 满级带宽。现有 progression.level_gains 在 Lv2–8 重复使用同一整数；`host/difficulty.py` 校验整个 level_gains 对象中属性值必须为非负整数。JSON Schema 的 progression.level_gains 仅约束对象与职业键，整数限制来自该运行时校验。实际属性升级会加上该值，而资源成长使用 int；此处阻塞来自属性校验，不能误写成 dex 被 int 截断。

| 职业 | 初始 dex | 每级 dex +0：Lv8 闪避 | 每级 dex +1：Lv8 闪避 | 要求 | 可行性 |
|---|---:|---:|---:|---|---|
| 勇者 | 5 | 2% | 12% | 6–9% | 无固定非负整数解 |
| 魔法使い | 8 | 6% | 16% | 8–11% | 无固定非负整数解 |
| 僧侶 | 8 | 6% | 16% | 5–8% | +0 可行 |
| 盗賊 | 16 | 18% | 20% | 20% | +1 以上可行；原主属性 +2 也满足 |

勇者、魔法使い每级 +2 时均为 20%；更大的非负整数只会保持上限，不可能回到各自目标区间。尝试勇者每级 dex +0.5，校验报 `Invalid mechanic setting: progression/level_gains`。

- TODO(design): 裁定勇者、魔法使い的 dex 成长：批准现有整数档位的带宽例外，或另行授权小数／按等级变化的成长机制及相应校验／数据结构改动。工程未选择任何方案。
- 不改初始 dex、闪避公式、被动或装备来绕过约束；这些不属于 L1 表列出的成长参数。前次三项资源取整豁免不自动扩展为 dex 豁免。

### 3. 改动文件与参数表

| 文件 | 改动 |
|---|---|
| scripts/scenario/levels_skills_v2.py | revision 清单用 open(..., newline="\n") 写 UTF-8 |
| scripts/scenario/combat_mechanics_v2.py | 同一清单写入点修复 |
| scripts/scenario/spring_postgame.py | 同一清单写入点修复 |
| tests/test_overlay_revision_newlines.py | 通过补丁新增；4 个迁移入口的 LF、无 BOM、内容与重复运行检查 |
| eval/reports/052-normal-tuning.md | 追加本节 |

游戏参数变更表为空：EXP、成长、敌人伤害／HP／防御、content_revision、overlay_revision 均未改变；新增 normal-only 记录 0，拆分 baby/normal 基础记录 0。未新增依赖。

### 4. 验证结果

- 原地 `python -m unittest discover -s tests -q`：954 项，FAILED (errors=39, skipped=1)，1103.746 秒。39 个错误全部为 PermissionError；细节保留在 unittest-original.log / original-test-errors.json，不能报为通过。
- `python .tmp-test/052a2/run_tests.py`：955 项，OK (skipped=1)，925.915 秒。按 spec §9 使用 050 叠加执行方式，仅替换临时目录创建与叠加测试加载；不修改断言或权限。
- 新增测试叠加执行：1 项（4 个入口子测试）通过；测试自行创建临时目录，不依赖预先存在的 gitignore 目录。直接执行因系统临时目录 PermissionError 失败，见 new-tests-direct.log。
- `node --check client/app.js`：退出码 0。
- baby 与 normal_empty 战斗金标：各 113 行逐项一致，聚合 SHA256 均为 `14d374747913957829d5162d7aa6d52dfd3ce9ec9b3f8560d1e5f96f0fd1caee`。
- baby 等级金标一致，SHA256 `7a03eb88f5f3dc7d4d5c6d89a288f7a99803fbb624a9bfa1c3eb9b84c66f63f9`。两份 baby 有效包与 HEAD 的差异键均为 `[]`（content_revision 也没有变化）；两份包、revision 清单、baby freeze、两份金标、v1 被动表的原始文件字节与开工前一致。
- 冻结 benchmark 离线重放：194/194 命中缓存，live=False，完整指标与冻结基线一致=True；不加 --live。
- normal 有效包 redundancy 检查无错误；冻结地址、数值叶分类、survive_at_one 和现有迁移幂等测试由全量叠加套件覆盖。
- explore：normal、baby 各四职业，exceptions=0、noncombat_dead_ends=0。当前仅改迁移文件写入方式，运行时包与代码和 HEAD 相同；未另跑 HEAD 对照实例，不声称新增逐轨迹 HEAD 对照已完成。
- N500 测量、053 baby 全量测量载荷复现与 workers 1/多 worker 的 N500 确定性抽查未完成；金标和静态字节证据不能替代这些测量。

### 5. 迭代、门槛及第 0 步状态

| 工作 | 本次状态 |
|---|---|
| HEAD N500 重测及与 053 的差异表 | 已启动后取消；未完成，不提供新差值 |
| F6 / P3 护送分支 / M9 测量修正 | 上次已合入，本次不修改；050d 已合入，旧数据不能当作新基线 |
| L1 EXP 与成长 | 前置检查阻塞，0 轮数值迭代 |
| L2 全遭遇伤害／HP | 未开始 |
| M3 首测、28 格表、M9 逐遭遇、M4 超限 | 本次无完整新样本；不复用旧结果作验收 |
| N500 数值验收 | 0 次，未完成；全部尚待验收硬门槛保持未认证 |

本次没有通过数值门槛，也没有提出未经测量的调参候选。从启动基线记录起的墙钟（含已取消测量与并行回归）约 30.9 分钟；各测试计时及原始日志见 verification.json。

### 6. 推断清单

1. G1 的满级按 normal Lv8 解释，带宽作用于角色基础 dex 闪避，未计装备、被动或临时加成。以未选被动的实际升级会话复核。
2. 本次‘其他迁移脚本有同样问题’按同一 overlay_revision.json 的写入点排查；holy_sword_049 已显式 LF，无需改动，并纳入测试。没有扩大为所有历史剧本写入点的换行重构。
3. 回归测试对迁移转换函数使用 identity/no-op 替身，以隔离此次文件输出行为；实际写入发生在测试自建目录中。
4. 续跑说明中的‘不提交、不写 .git’作为本任务交付方式，优先于通用提交措辞；提供含 [工程] 前缀的建议提交信息。

### 7. 偏离、已知问题与交付

- 未完成 L1/L2/M3/N500 和完整基线，原因是续跑说明要求再次遇到设计问题写报告后停止，以及 052 C8 禁止自行扩范围。不是验收通过。
- 原地测试受当前沙箱临时目录权限影响；叠加结果单列，不改权限。
- 交付 `.tmp-test/052a2/052a2.patch`（包含新增测试与报告）、`tests.patch`（已包含在主补丁，不重复应用）、`manifest.json`、`052a2-report.txt`。基于 HEAD 实际应用到独立临时目录，并逐文件核对（仅规范化 LF/CRLF）；交付文本均为 UTF-8 无 BOM。
- 未 git add、未提交、未调用付费 API、未修改 docs/ 或任何提示词。

## 052a3：L1 / L2 最佳候选与停止交付（2026-10-23）

状态：完成工程实现与离线验收运行；**数值硬门槛未全部通过，候选待设计批准例外，不标记为验收通过**。按 §7.3 连续两轮停滞规则停止，第 5 轮为交付候选。

范围：HEAD 数值基线 → L1 EXP / 按等级成长 → L2 全遭遇伤害 / HP → M3 首测 → 一次 N500 验收。没有实施 052b / 052c 的机制、技能、经济或回复修改；被动表 v1 冻结。

基准 HEAD：`dfd088d93503c03b193dded860ca1475872a9356`。上次缓存基准之后只新增文档与 `tests/test_all_skill_kinds.py`，数值来源相同，核对记录见 `.tmp-test/052a3/resume-provenance.json`。安全的 16 组分支缓存已复用；其余在本轮完成。

### 测量口径与第 0 步

前后全量均 N=500、probe-n=500、seed=20261020，28 格各 500 条（各 14000 条原型记录）。迭代 N=200 / seed=20261022；分支选择沿用 053 的每组合 N=200 规则，最终在新数值下重新选择。主报告不把 N20 冒烟或 N200 的差异当成 N500 收益。

HEAD 基线与 053 有 12 个原型×职业格发生变化，不只ドラコ：期间包含 049、050d 和已合入路线修正。基线及本轮都使用 normal 熔岩房败退回泉后立即结束洞窟路线的必要修复；否则继续打开宝箱会使测量失败。该修复有独立回归测试，baby 分支不变。

F6：HEAD 基线 P3 的 2000 条记录中，10 条未到终局均在 `valley_lava_bridge` HP=0；活着被路线截断为 0。P3 终局率 98.6–100%，通关率 6.2–14.4%。剩余差距属于战斗/资源和死亡结算口径，不能继续归因为活着没走完。完整 053 对照和失败种子见 `baseline-step-zero.json`。

M9 主口径沿用已合入的 052 修正：P2 观察到的中位等级开场，不计一次性护盾与防御姿态；报告护盾和前三回合辅助值。缺 P2 到达快照不制造数据。§2 的当前等级门槛由独立 audit 判定；原始 measurement 中冻结的 053 target 元数据不覆盖当前 spec。

所有二项率以下为点估计及 Wilson 95% 区间；解析伤害/回复比、均值和中位数不硬套二项区间。

### §2 门槛对照


| 指标 | HEAD基线 | 候选N500 | 状态/范围 |
| --- | --- | --- | --- |
| M1 硬 | 0/8 失败 | 0/8 失败 | 通过 |
| M3 硬（a首测/c收尾） | 7/21 样本组失败 | 0/15 样本组失败；max=0.4065 | 已观察样本通过 |
| M4 硬，含Q4 | 32 格超限 | 8 格超限 | 失败；清单见下 |
| M9 硬，含教程豁免/Q5 | 62 失败 / 80 观察；缺64 | 40 失败 / 80 观察；缺64 | 失败及未验证；清单见下 |
| Ignis 到达等级 硬 | 15/20 未通过 | 5/20 未通过 | 失败/无样本均不算通过 |
| M1' 严格递增/15pp | report；meets_target=False | report；meets_target=False | 软，全段；原值/当前口径详见附表或原始 JSON |
| M10 CV | report；meets_target=False | report；meets_target=False | 软，a/b；原值/当前口径详见附表或原始 JSON |
| M11 消耗 | report；meets_target=False | report；meets_target=False | 软，a/b；原值/当前口径详见附表或原始 JSON |
| M8 同伴10–20pp | report；meets_target=False | report；meets_target=False | 软，a/c；原值/当前口径详见附表或原始 JSON |
| M2 准备 | report；meets_target=False | report；meets_target=False | b 收尾；原值/当前口径详见附表或原始 JSON |
| M3' 赛跑 | report；meets_target=False | report；meets_target=False | b；原值/当前口径详见附表或原始 JSON |
| M5 经济 | report；meets_target=False | report；meets_target=False | c；原值/当前口径详见附表或原始 JSON |
| M12 技能/被动 | report；meets_target=False | report；meets_target=False | c；本段不重新穷举；原值/当前口径详见附表或原始 JSON |
| M13 等级差硬/每级软 | 见下 P0/P2 和等级探针 | 见下 P0/P2 和等级探针 | 不足2级/缺样本均列例外；每级8–15pp为软目标 |
| 原型通关率 软 | 见28格表 | 见28格表 | P1 15–35%；P2 55–75%；P3≥80% |
| P2s 软（到达等级差亦按a硬检查） | 见下比较 | 见下比较 | 通关差≤10pp，等级差≤1 |
| 职业差 软 | 见下比较 | 见下比较 | P2非mage最高最低≤20pp；mage单列 |
| ドラコ A / B、换剑价值及原键 | 未在a重验 | 未在a重验 | 按分段归052b/c；本次未跑8×2000专门验收 |
| baby 不变 硬 | 053冻结对照 | 见验证证据 | 数值载荷和记录逐字节规范化一致；原始元数据差异另列 |

### 28 格前后对照

每格分为前/后两行；通关=冒険完了，Ignis=击败/净化，终局=实际终局；回合数含到达后败北，不能把早死短回合当作击杀加速。

| 格 | 阶段 | 通关% [CI] | Ignis% [CI] | 终局% [CI] | Ignis回合中位 | 到达等级分布 | EXP p10/p50/p90 | EXP来源均值 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0a/hero | 前 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | 4 | n=17 {"5":17} | [140,145,145] | {"trash":19.118,"elite":45.882,"boss":80,"unclassified":0,"quest":0} |
| P0a/hero | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | None | n=0 {} | null | {} |
| P0a/cleric | 前 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | None | n=0 {} | null | {} |
| P0a/cleric | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | None | n=0 {} | null | {} |
| P0a/mage | 前 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | None | n=0 {} | null | {} |
| P0a/mage | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | None | n=0 {} | null | {} |
| P0a/thief | 前 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | 5 | n=9 {"4":8,"5":1} | [90,95,105] | {"trash":10,"elite":46.667,"boss":44.444,"unclassified":0,"quest":0} |
| P0a/thief | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | None | n=0 {} | null | {} |
| P0b/hero | 前 | 2.6% [1.5, 4.4] | 2.6% [1.5, 4.4] | 99.8% [98.9, 100.0] | 6.0 | n=94 {"4":90,"5":4} | [95,95,105] | {"trash":9.096,"elite":48.351,"boss":41.702,"unclassified":0,"quest":0} |
| P0b/hero | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | 3 | n=25 {"4":25} | [69,69,69] | {"trash":7.68,"elite":36,"boss":25,"unclassified":0,"quest":0} |
| P0b/cleric | 前 | 1.2% [0.6, 2.6] | 1.2% [0.6, 2.6] | 99.8% [98.9, 100.0] | 5.0 | n=58 {"4":58} | [95,95,105] | {"trash":8.19,"elite":49.655,"boss":40,"unclassified":0,"quest":0} |
| P0b/cleric | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | 4.0 | n=4 {"4":4} | [69,69,69] | {"trash":8,"elite":36,"boss":25,"unclassified":0,"quest":0} |
| P0b/mage | 前 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 99.8% [98.9, 100.0] | 4 | n=3 {"4":3} | [95,95,95] | {"trash":8.333,"elite":50,"boss":40,"unclassified":0,"quest":0} |
| P0b/mage | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | None | n=0 {} | null | {} |
| P0b/thief | 前 | 1.6% [0.8, 3.1] | 1.6% [0.8, 3.1] | 100.0% [99.2, 100.0] | 4 | n=63 {"4":61,"5":2} | [95,95,105] | {"trash":8.175,"elite":50.714,"boss":41.27,"unclassified":0,"quest":0} |
| P0b/thief | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | 1.0 | n=4 {"4":4} | [69,69,69] | {"trash":8,"elite":36,"boss":25,"unclassified":0,"quest":0} |
| P1/hero | 前 | 3.8% [2.4, 5.9] | 3.8% [2.4, 5.9] | 99.4% [98.3, 99.8] | 8.0 | n=220 {"4":164,"5":56} | [105,105,155] | {"trash":11.159,"elite":48.273,"boss":50.182,"unclassified":0,"quest":9.409} |
| P1/hero | 后 | 0.6% [0.2, 1.7] | 0.6% [0.2, 1.7] | 100.0% [99.2, 100.0] | 5 | n=209 {"4":2,"5":207} | [99,99,99] | {"trash":7.962,"elite":36,"boss":25,"unclassified":0,"quest":29.713} |
| P1/cleric | 前 | 1.0% [0.4, 2.3] | 1.0% [0.4, 2.3] | 95.8% [93.7, 97.2] | 6 | n=55 {"4":55} | [105,105,115] | {"trash":8.545,"elite":49.091,"boss":40,"unclassified":0,"quest":9.818} |
| P1/cleric | 后 | 0.4% [0.1, 1.4] | 0.4% [0.1, 1.4] | 100.0% [99.2, 100.0] | 4.0 | n=50 {"5":50} | [99,99,99] | {"trash":8,"elite":36,"boss":25,"unclassified":0,"quest":30} |
| P1/mage | 前 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | 2 | n=17 {"4":8,"5":9} | [105,155,155] | {"trash":14.412,"elite":46.765,"boss":61.176,"unclassified":0,"quest":9.412} |
| P1/mage | 后 | 0.2% [0.0, 1.1] | 0.2% [0.0, 1.1] | 100.0% [99.2, 100.0] | 2 | n=21 {"5":21} | [99,99,99] | {"trash":8.381,"elite":36,"boss":26.19,"unclassified":0,"quest":30} |
| P1/thief | 前 | 1.4% [0.7, 2.9] | 1.4% [0.7, 2.9] | 99.6% [98.6, 99.9] | 5 | n=123 {"4":104,"5":19} | [105,105,155] | {"trash":10.244,"elite":48.78,"boss":46.179,"unclassified":0,"quest":9.919} |
| P1/thief | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | 4 | n=59 {"4":8,"5":51} | [65,99,99] | {"trash":7.186,"elite":36.814,"boss":25,"unclassified":0,"quest":25.932} |
| P2/hero | 前 | 20.8% [17.5, 24.6] | 23.8% [20.3, 27.7] | 99.8% [98.9, 100.0] | 10 | n=119 {"7":119} | [315,330,340] | {"trash":20.672,"elite":117.227,"boss":159.328,"unclassified":0,"quest":29.412} |
| P2/hero | 后 | 51.6% [47.2, 56.0] | 73.8% [69.8, 77.5] | 100.0% [99.2, 100.0] | 11 | n=487 {"6":487} | [290,302,310] | {"trash":16.23,"elite":94.694,"boss":99.846,"unclassified":0,"quest":88.522} |
| P2/cleric | 前 | 8.4% [6.3, 11.2] | 9.4% [7.1, 12.3] | 100.0% [99.2, 100.0] | 8 | n=47 {"6":1,"7":46} | [315,330,340] | {"trash":21.383,"elite":119.043,"boss":158.298,"unclassified":0,"quest":29.787} |
| P2/cleric | 后 | 48.4% [44.0, 52.8] | 48.8% [44.4, 53.2] | 99.6% [98.6, 99.9] | 7 | n=333 {"6":333} | [290,302,306] | {"trash":17.177,"elite":93.045,"boss":98.949,"unclassified":0,"quest":88.919} |
| P2/mage | 前 | 1.6% [0.8, 3.1] | 5.8% [4.1, 8.2] | 99.8% [98.9, 100.0] | 8 | n=37 {"6":5,"7":32} | [275,320,335] | {"trash":21.216,"elite":111.892,"boss":145.946,"unclassified":0,"quest":29.73} |
| P2/mage | 后 | 3.0% [1.8, 4.9] | 9.4% [7.1, 12.3] | 99.8% [98.9, 100.0] | 5 | n=265 {"6":265} | [269,302,310] | {"trash":17.072,"elite":93.057,"boss":95,"unclassified":0,"quest":88.755} |
| P2/thief | 前 | 41.2% [37.0, 45.6] | 46.2% [41.9, 50.6] | 99.8% [98.9, 100.0] | 10 | n=257 {"6":25,"7":232} | [285,320,340] | {"trash":18.385,"elite":113.813,"boss":155.019,"unclassified":0,"quest":29.222} |
| P2/thief | 后 | 3.4% [2.1, 5.4] | 6.4% [4.6, 8.9] | 100.0% [99.2, 100.0] | 4 | n=231 {"6":231} | [265,294,310] | {"trash":15.152,"elite":91.429,"boss":95.887,"unclassified":0,"quest":88.571} |
| P3/hero | 前 | 14.4% [11.6, 17.7] | 32.0% [28.1, 36.2] | 99.4% [98.3, 99.8] | 11.0 | n=184 {"8":184} | [540,565,575] | {"trash":26.277,"elite":147.473,"boss":276.304,"unclassified":0,"quest":108.478} |
| P3/hero | 后 | 11.4% [8.9, 14.5] | 16.8% [13.8, 20.3] | 100.0% [99.2, 100.0] | 9 | n=223 {"7":223} | [586,637,653] | {"trash":21.758,"elite":117.417,"boss":167.601,"unclassified":0,"quest":320.179} |
| P3/cleric | 前 | 8.0% [5.9, 10.7] | 13.6% [10.9, 16.9] | 100.0% [99.2, 100.0] | 10.0 | n=76 {"8":76} | [515,565,570] | {"trash":27.237,"elite":146.25,"boss":271.579,"unclassified":0,"quest":107.763} |
| P3/cleric | 后 | 0.0% [0.0, 0.8] | 0.8% [0.3, 2.0] | 99.8% [98.9, 100.0] | 9 | n=11 {"7":11} | [615,619,670] | {"trash":22.182,"elite":120,"boss":179.545,"unclassified":0,"quest":305.455} |
| P3/mage | 前 | 6.2% [4.4, 8.7] | 30.0% [26.1, 34.2] | 100.0% [99.2, 100.0] | 7.0 | n=182 {"8":182} | [495,545,605] | {"trash":26.703,"elite":134.093,"boss":288.791,"unclassified":0,"quest":101.154} |
| P3/mage | 后 | 2.8% [1.7, 4.6] | 7.4% [5.4, 10.0] | 99.8% [98.9, 100.0] | 5 | n=89 {"7":86,"8":3} | [603,623,678] | {"trash":22.697,"elite":115.685,"boss":184.27,"unclassified":0,"quest":310.449} |
| P3/thief | 前 | 9.0% [6.8, 11.8] | 22.4% [19.0, 26.3] | 98.6% [97.1, 99.3] | 9.0 | n=180 {"8":180} | [495,550,570] | {"trash":26.611,"elite":141.333,"boss":258.667,"unclassified":0,"quest":103.889} |
| P3/thief | 后 | 0.0% [0.0, 0.8] | 2.0% [1.1, 3.6] | 100.0% [99.2, 100.0] | 4.5 | n=70 {"7":70} | [523,582,602] | {"trash":20.171,"elite":114.171,"boss":145.357,"unclassified":0,"quest":294} |
| P2s/hero | 前 | 13.8% [11.1, 17.1] | 15.4% [12.5, 18.8] | 100.0% [99.2, 100.0] | 10.0 | n=78 {"6":47,"7":31} | [250,270,300] | {"trash":20.513,"elite":63.269,"boss":160,"unclassified":0,"quest":29.231} |
| P2s/hero | 后 | 47.6% [43.3, 52.0] | 76.8% [72.9, 80.3] | 100.0% [99.2, 100.0] | 11 | n=493 {"6":493} | [230,254,274] | {"trash":16.276,"elite":48.122,"boss":100,"unclassified":0,"quest":88.296} |
| P2s/cleric | 前 | 9.2% [7.0, 12.1] | 9.6% [7.3, 12.5] | 99.8% [98.9, 100.0] | 6.0 | n=50 {"6":34,"7":16} | [240,270,290] | {"trash":21.7,"elite":59.1,"boss":157.6,"unclassified":0,"quest":30} |
| P2s/cleric | 后 | 33.4% [29.4, 37.6] | 43.6% [39.3, 48.0] | 99.6% [98.6, 99.9] | 7.0 | n=302 {"6":302} | [230,254,270] | {"trash":17.179,"elite":44.583,"boss":99.586,"unclassified":0,"quest":88.609} |
| P2s/mage | 前 | 0.8% [0.3, 2.0] | 3.8% [2.4, 5.9] | 100.0% [99.2, 100.0] | 7 | n=35 {"5":2,"6":33} | [205,240,270] | {"trash":20.857,"elite":46.714,"boss":142.857,"unclassified":0,"quest":28.857} |
| P2s/mage | 后 | 1.2% [0.6, 2.6] | 5.8% [4.1, 8.2] | 99.6% [98.6, 99.9] | 4 | n=209 {"6":209} | [222,246,266] | {"trash":17.129,"elite":41.971,"boss":97.967,"unclassified":0,"quest":87.99} |
| P2s/thief | 前 | 22.8% [19.3, 26.7] | 26.0% [22.3, 30.0] | 100.0% [99.2, 100.0] | 11 | n=151 {"5":2,"6":124,"7":25} | [240,260,280] | {"trash":18.245,"elite":53.444,"boss":157.086,"unclassified":0,"quest":29.338} |
| P2s/thief | 后 | 4.4% [2.9, 6.6] | 6.2% [4.4, 8.7] | 100.0% [99.2, 100.0] | 5 | n=217 {"6":217} | [217,238,254] | {"trash":15.134,"elite":35.281,"boss":97.12,"unclassified":0,"quest":88.203} |
| P0g/hero | 前 | 2.6% [1.5, 4.4] | 2.6% [1.5, 4.4] | 99.8% [98.9, 100.0] | 6.0 | n=94 {"4":90,"5":4} | [95,95,105] | {"trash":9.096,"elite":48.351,"boss":41.702,"unclassified":0,"quest":0} |
| P0g/hero | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | 3 | n=25 {"4":25} | [69,69,69] | {"trash":7.68,"elite":36,"boss":25,"unclassified":0,"quest":0} |
| P0g/cleric | 前 | 1.2% [0.6, 2.6] | 1.2% [0.6, 2.6] | 99.8% [98.9, 100.0] | 5.0 | n=58 {"4":58} | [95,95,105] | {"trash":8.19,"elite":49.655,"boss":40,"unclassified":0,"quest":0} |
| P0g/cleric | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | 4.0 | n=4 {"4":4} | [69,69,69] | {"trash":8,"elite":36,"boss":25,"unclassified":0,"quest":0} |
| P0g/mage | 前 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 99.8% [98.9, 100.0] | 4 | n=3 {"4":3} | [95,95,95] | {"trash":8.333,"elite":50,"boss":40,"unclassified":0,"quest":0} |
| P0g/mage | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | None | n=0 {} | null | {} |
| P0g/thief | 前 | 1.6% [0.8, 3.1] | 1.6% [0.8, 3.1] | 100.0% [99.2, 100.0] | 4 | n=63 {"4":61,"5":2} | [95,95,105] | {"trash":8.175,"elite":50.714,"boss":41.27,"unclassified":0,"quest":0} |
| P0g/thief | 后 | 0.0% [0.0, 0.8] | 0.0% [0.0, 0.8] | 100.0% [99.2, 100.0] | 1.0 | n=4 {"4":4} | [69,69,69] | {"trash":8,"elite":36,"boss":25,"unclassified":0,"quest":0} |

### 等级判定、脆弱门槛、M13 与 P2s


| 格 | 目标 | 到达n | 分布 | 目标占比 [CI] | 通过 | 距p10/p90<5 EXP（脆弱） |
| --- | --- | --- | --- | --- | --- | --- |
| P0a/hero | 4 | 0 | {} | 无样本 | False | — |
| P0a/cleric | 4 | 0 | {} | 无样本 | False | — |
| P0a/mage | 4 | 0 | {} | 无样本 | False | — |
| P0a/thief | 4 | 0 | {} | 无样本 | False | — |
| P0b/hero | 4 | 25 | {"4":25} | 100.0% [86.7, 100.0] | True | — |
| P0b/cleric | 4 | 4 | {"4":4} | 100.0% [51.0, 100.0] | True | — |
| P0b/mage | 4 | 0 | {} | 无样本 | False | — |
| P0b/thief | 4 | 4 | {"4":4} | 100.0% [51.0, 100.0] | True | — |
| P1/hero | 5 | 209 | {"4":2,"5":207} | 99.0% [96.6, 99.7] | True | Lv5=99 |
| P1/cleric | 5 | 50 | {"5":50} | 100.0% [92.9, 100.0] | True | Lv5=99 |
| P1/mage | 5 | 21 | {"5":21} | 100.0% [84.5, 100.0] | True | Lv5=99 |
| P1/thief | 5 | 59 | {"4":8,"5":51} | 86.4% [75.5, 93.0] | True | Lv5=99 |
| P2/hero | 6 | 487 | {"6":487} | 100.0% [99.2, 100.0] | True | — |
| P2/cleric | 6 | 333 | {"6":333} | 100.0% [98.9, 100.0] | True | — |
| P2/mage | 6 | 265 | {"6":265} | 100.0% [98.6, 100.0] | True | — |
| P2/thief | 6 | 231 | {"6":231} | 100.0% [98.4, 100.0] | True | — |
| P3/hero | 7 | 223 | {"7":223} | 100.0% [98.3, 100.0] | True | — |
| P3/cleric | 7 | 11 | {"7":11} | 100.0% [74.1, 100.0] | True | — |
| P3/mage | 7 | 89 | {"7":86,"8":3} | 96.6% [90.6, 98.8] | True | Lv8=679 |
| P3/thief | 7 | 70 | {"7":70} | 100.0% [94.8, 100.0] | True | — |


| 阶段 | 职业 | 比较 | 左等级中位 | P2等级中位 | 中位差 | 均值差 | 通关差pp | 等级条件通过 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 前 | hero | P0a→P2 | 5 | 7 | 2.0000 | 2.0000 | 20.8 | True |
| 前 | hero | P0b→P2 | 4.0 | 7 | 3.0000 | 2.9574 | 18.2 | True |
| 前 | hero | P2s→P2 | 6.0 | 7 | 1.0000 | 0.6026 | 7.0 | True |
| 前 | cleric | P0a→P2 | None | 7 | — | — | 8.4 | False |
| 前 | cleric | P0b→P2 | 4.0 | 7 | 3.0000 | 2.9787 | 7.2 | True |
| 前 | cleric | P2s→P2 | 6.0 | 7 | 1.0000 | 0.6587 | -0.8 | True |
| 前 | mage | P0a→P2 | None | 7 | — | — | 1.6 | False |
| 前 | mage | P0b→P2 | 4 | 7 | 3.0000 | 2.8649 | 1.6 | True |
| 前 | mage | P2s→P2 | 6 | 7 | 1.0000 | 0.9220 | 0.8 | True |
| 前 | thief | P0a→P2 | 4 | 7 | 3.0000 | 2.7916 | 41.2 | True |
| 前 | thief | P0b→P2 | 4 | 7 | 3.0000 | 2.8710 | 39.6 | True |
| 前 | thief | P2s→P2 | 6 | 7 | 1.0000 | 0.7504 | 18.4 | True |
| 后 | hero | P0a→P2 | None | 6 | — | — | 51.6 | False |
| 后 | hero | P0b→P2 | 4 | 6 | 2.0000 | 2.0000 | 51.6 | True |
| 后 | hero | P2s→P2 | 6 | 6 | 0.0000 | 0.0000 | 4.0 | True |
| 后 | cleric | P0a→P2 | None | 6 | — | — | 48.4 | False |
| 后 | cleric | P0b→P2 | 4.0 | 6 | 2.0000 | 2.0000 | 48.4 | True |
| 后 | cleric | P2s→P2 | 6.0 | 6 | 0.0000 | 0.0000 | 15.0 | True |
| 后 | mage | P0a→P2 | None | 6 | — | — | 3.0 | False |
| 后 | mage | P0b→P2 | None | 6 | — | — | 3.0 | False |
| 后 | mage | P2s→P2 | 6 | 6 | 0.0000 | 0.0000 | 1.8 | True |
| 后 | thief | P0a→P2 | None | 6 | — | — | 3.4 | False |
| 后 | thief | P0b→P2 | 4.0 | 6 | 2.0000 | 2.0000 | 3.4 | True |
| 后 | thief | P2s→P2 | 6 | 6 | 0.0000 | 0.0000 | -1.0 | True |

前：P2 非 mage 职业通关差 32.8pp；mage 1.6%。
后：P2 非 mage 职业通关差 48.2pp；mage 3.0%。

Lv8 门槛 679；P3 到达 EXP 各职业 p90 的最大值 678；严格大于：True。

固定基线 EXP ledger 搜索了 8086 个允许参数候选。常见 P0a 路径 4T+3E+2B 与 P1 路径 2T+3E+B+Q 的差为 2T+B−Q，允许边界下仍≥1，单一门槛无法把这两条具体路径同时置于 Lv4/Lv5。此为路径约束证据，不是所有可能路线和参数全局无解的证明。

### M9 全遭遇×职业前后表

单格格式：主值 / 计护盾 / 前3回合主值 / 前3回合计护盾（Lv）；前三回合只对实际观察回合平均。— 表示没有 P2 快照。T=教程只报告；Q5=可选上限+0.05，第四层不享受。状态以主值判定。

| 遭遇 | 职业 | 标准带宽 | 前：主/盾/3回合/3回合盾 | 后：主/盾/3回合/3回合盾 | 后状态 |
| --- | --- | --- | --- | --- | --- |
| bone_field | cleric | 无P2快照 | — | — | 未验证 |
| bone_field | hero | 无P2快照 | — | — | 未验证 |
| bone_field | mage | 无P2快照 | — | — | 未验证 |
| bone_field | thief | 无P2快照 | — | — | 未验证 |
| cave_crystal_corridor | cleric | [0.18,0.25] | 0.3288/0.3288/0.3288/0.3288 (Lv4) | 0.2676/0.2676/0.2676/0.2676 (Lv5) | Q5内 |
| cave_crystal_corridor | hero | [0.18,0.25] | 0.1925/0.1925/0.1645/0.1645 (Lv4) | 0.2046/0.2046/0.1642/0.1642 (Lv5) | 通过 |
| cave_crystal_corridor | mage | [0.18,0.25] | 0.5166/0.0000/0.4271/0.2549 (Lv4) | 0.3572/0.0000/0.3293/0.2103 (Lv5) | 失败 |
| cave_crystal_corridor | thief | [0.18,0.25] | 0.2500/0.2500/0.2500/0.2500 (Lv4) | 0.2599/0.2599/0.2259/0.2259 (Lv5) | Q5内 |
| cave_heat_corridor | cleric | [0.18,0.25] | 0.3988/0.3988/0.3323/0.3323 (Lv4) | 0.2193/0.2193/—/— (Lv5) | 通过 |
| cave_heat_corridor | hero | [0.18,0.25] | 0.2800/0.2800/0.2333/0.2333 (Lv4) | 0.0909/0.0909/0.0758/0.0758 (Lv5) | 失败 |
| cave_heat_corridor | mage | [0.18,0.25] | 0.6267/0.0000/0.5222/0.3133 (Lv4) | 0.2927/0.0000/0.2439/0.1464 (Lv5) | Q5内 |
| cave_heat_corridor | thief | [0.18,0.25] | 0.4091/0.4091/0.3409/0.3409 (Lv3) | 0.1705/0.1705/0.1705/0.1705 (Lv5) | 失败 |
| cave_lava_room | cleric | [0.18,0.25] | 0.3418/0.3418/0.2279/0.2279 (Lv4) | 0.3760/0.3760/0.2507/0.2507 (Lv5) | 失败 |
| cave_lava_room | hero | [0.18,0.25] | 0.2040/0.2040/0.1360/0.1360 (Lv4) | 0.2208/0.2208/0.1472/0.1472 (Lv5) | 通过 |
| cave_lava_room | mage | [0.18,0.25] | 0.5371/0.0000/0.4178/0.2387 (Lv4) | 0.5018/0.0000/0.3345/0.1673 (Lv5) | 失败 |
| cave_lava_room | thief | [0.18,0.25] | 0.2720/0.2720/0.2115/0.2115 (Lv4) | 0.3214/0.3214/—/— (Lv5) | 失败 |
| cave_prism_tree | cleric | [0.28,0.35] | 0.1581/0.1581/0.1054/0.1054 (Lv5) | 0.2379/0.2379/0.1586/0.1586 (Lv5) | 失败 |
| cave_prism_tree | hero | [0.28,0.35] | 0.1146/0.1146/0.0764/0.0764 (Lv5) | 0.1728/0.1728/0.1152/0.1152 (Lv5) | 失败 |
| cave_prism_tree | mage | [0.28,0.35] | 0.2504/0.0000/0.1669/0.0835 (Lv5) | 0.3176/0.0000/0.2117/0.1059 (Lv5) | 通过 |
| cave_prism_tree | thief | [0.28,0.35] | 0.1587/0.1587/0.1058/0.1058 (Lv4) | 0.2260/0.2260/—/— (Lv5) | 失败 |
| dark_forest_loc | cleric | [0.1,0.15] | 0.4444/0.4444/0.1830/0.1830 (Lv1) | 0.4444/0.4444/0.1830/0.1830 (Lv1) | T |
| dark_forest_loc | hero | [0.1,0.15] | 0.4000/0.4000/0.1660/0.1660 (Lv1) | 0.4000/0.4000/0.1660/0.1660 (Lv1) | T |
| dark_forest_loc | mage | [0.1,0.15] | 0.6667/0.6667/0.2744/0.2744 (Lv1) | 0.6667/0.6667/0.2744/0.2744 (Lv1) | T |
| dark_forest_loc | thief | [0.1,0.15] | 0.5714/0.5714/0.2295/0.2295 (Lv1) | 0.5714/0.5714/0.2295/0.2295 (Lv1) | T |
| draco_battle | cleric | [0.28,0.35] | 0.0902/0.0902/0.1631/0.1631 (Lv8) | 0.2807/0.2807/0.1893/0.1893 (Lv7) | 通过 |
| draco_battle | hero | [0.28,0.35] | 0.0757/0.0757/0.1490/0.1490 (Lv8) | 0.2505/0.2505/0.2589/0.2589 (Lv7) | 失败 |
| draco_battle | mage | [0.28,0.35] | 0.2160/0.0000/0.3331/0.1306 (Lv8) | 0.4688/0.0000/0.4806/0.1622 (Lv7) | 失败 |
| draco_battle | thief | [0.28,0.35] | 0.0908/0.0908/0.1642/0.1642 (Lv8) | 0.3101/0.3101/0.3197/0.3197 (Lv7) | 通过 |
| dragon_valley_loc | cleric | [0.28,0.35] | 0.1376/0.1376/0.1147/0.1147 (Lv7) | 0.2826/0.2826/0.2826/0.2826 (Lv6) | 通过 |
| dragon_valley_loc | hero | [0.28,0.35] | 0.1226/0.1226/0.1226/0.1226 (Lv7) | 0.2478/0.2478/0.2478/0.2478 (Lv6) | 失败 |
| dragon_valley_loc | mage | [0.28,0.35] | 0.3035/0.0000/0.3035/0.2023 (Lv7) | 0.4888/0.0000/—/— (Lv6) | 失败 |
| dragon_valley_loc | thief | [0.28,0.35] | 0.1387/0.1387/0.1387/0.1387 (Lv7) | 0.3100/0.3100/0.3100/0.3100 (Lv6) | 通过 |
| dragon_valley_return | cleric | 无P2快照 | — | — | 未验证 |
| dragon_valley_return | hero | 无P2快照 | — | — | 未验证 |
| dragon_valley_return | mage | 无P2快照 | — | — | 未验证 |
| dragon_valley_return | thief | 无P2快照 | — | — | 未验证 |
| forest_wolves | cleric | [0.18,0.25] | 0.1421/0.1421/—/— (Lv6) | 0.1994/0.1994/—/— (Lv6) | 通过 |
| forest_wolves | hero | [0.18,0.25] | 0.1034/0.1034/—/— (Lv6) | 0.1371/0.1371/0.1371/0.1371 (Lv6) | 失败 |
| forest_wolves | mage | [0.18,0.25] | 0.2263/0.0000/—/— (Lv6) | 0.2683/0.0000/—/— (Lv6) | 失败 |
| forest_wolves | thief | [0.18,0.25] | 0.1232/0.1232/—/— (Lv6) | 0.1875/0.1875/—/— (Lv6) | 通过 |
| frost_wolf_battle | cleric | [0.28,0.35] | 0.0874/0.0874/0.0874/0.0874 (Lv6) | 0.2848/0.2848/0.2848/0.2848 (Lv6) | 通过 |
| frost_wolf_battle | hero | [0.28,0.35] | 0.0726/0.0726/0.0726/0.0726 (Lv6) | 0.2469/0.2469/0.2469/0.2469 (Lv6) | 失败 |
| frost_wolf_battle | mage | [0.28,0.35] | 0.2263/0.0000/—/— (Lv6) | 0.4983/0.0000/—/— (Lv6) | 失败 |
| frost_wolf_battle | thief | [0.28,0.35] | 0.0882/0.0882/0.0804/0.0804 (Lv6) | 0.3125/0.3125/0.3125/0.3125 (Lv6) | 通过 |
| ghoul_marsh | cleric | 无P2快照 | — | — | 未验证 |
| ghoul_marsh | hero | 无P2快照 | — | — | 未验证 |
| ghoul_marsh | mage | 无P2快照 | — | — | 未验证 |
| ghoul_marsh | thief | 无P2快照 | — | — | 未验证 |
| goblin_fort | cleric | [0.1,0.15] | 0.1828/0.1828/—/— (Lv1) | 0.1828/0.1828/—/— (Lv1) | Q5内 |
| goblin_fort | hero | [0.1,0.15] | 0.1307/0.1307/—/— (Lv1) | 0.1225/0.1225/—/— (Lv1) | 通过 |
| goblin_fort | mage | [0.1,0.15] | 0.2742/0.2742/—/— (Lv1) | 0.2742/0.2742/—/— (Lv1) | 失败 |
| goblin_fort | thief | [0.1,0.15] | 0.1562/0.1562/—/— (Lv1) | 0.1464/0.1464/—/— (Lv1) | 通过 |
| goblin_fort_chest_fight | cleric | 无P2快照 | — | — | 未验证 |
| goblin_fort_chest_fight | hero | 无P2快照 | — | — | 未验证 |
| goblin_fort_chest_fight | mage | 无P2快照 | — | — | 未验证 |
| goblin_fort_chest_fight | thief | 无P2快照 | — | — | 未验证 |
| goblin_fort_first_second | cleric | [0.18,0.25] | 0.3656/0.3656/—/— (Lv1) | 0.2350/0.2350/—/— (Lv1) | 通过 |
| goblin_fort_first_second | hero | [0.18,0.25] | 0.2613/0.2613/—/— (Lv1) | 0.1715/0.1715/—/— (Lv1) | 失败 |
| goblin_fort_first_second | mage | [0.18,0.25] | 0.5483/0.5483/0.3656/0.3656 (Lv1) | 0.3525/0.3525/—/— (Lv1) | 失败 |
| goblin_fort_first_second | thief | [0.18,0.25] | 0.3124/0.3124/—/— (Lv1) | 0.2050/0.2050/—/— (Lv1) | 通过 |
| goblin_fort_fourth | cleric | [0.28,0.35] | 0.6539/0.6539/0.6539/0.6539 (Lv2) | 0.2910/0.2910/0.2910/0.2910 (Lv2) | 通过 |
| goblin_fort_fourth | hero | [0.28,0.35] | 0.4949/0.4949/0.4949/0.4949 (Lv2) | 0.1917/0.1917/0.1917/0.1917 (Lv2) | 失败 |
| goblin_fort_fourth | mage | [0.28,0.35] | 1.0027/0.0000/1.0027/0.6684 (Lv2) | 0.4073/0.0000/0.4073/0.2716 (Lv2) | 失败 |
| goblin_fort_fourth | thief | [0.28,0.35] | 0.5920/0.5920/0.5920/0.5920 (Lv2) | 0.3221/0.3221/0.3221/0.3221 (Lv1) | 通过 |
| goblin_fort_second_left | cleric | 无P2快照 | — | — | 未验证 |
| goblin_fort_second_left | hero | 无P2快照 | — | — | 未验证 |
| goblin_fort_second_left | mage | 无P2快照 | — | — | 未验证 |
| goblin_fort_second_left | thief | 无P2快照 | — | — | 未验证 |
| goblin_fort_second_right | cleric | [0.18,0.25] | 0.1430/0.1430/—/— (Lv2) | 0.2350/0.2350/—/— (Lv1) | 通过 |
| goblin_fort_second_right | hero | [0.18,0.25] | 0.0784/0.0784/—/— (Lv2) | 0.1715/0.1715/—/— (Lv1) | 失败 |
| goblin_fort_second_right | mage | [0.18,0.25] | 0.2193/0.0000/—/— (Lv2) | 0.3525/0.3525/—/— (Lv1) | 失败 |
| goblin_fort_second_right | thief | [0.18,0.25] | 0.1562/0.1562/—/— (Lv1) | 0.2050/0.2050/—/— (Lv1) | 通过 |
| goblin_fort_third_guards | cleric | 无P2快照 | — | — | 未验证 |
| goblin_fort_third_guards | hero | 无P2快照 | — | — | 未验证 |
| goblin_fort_third_guards | mage | 无P2快照 | — | — | 未验证 |
| goblin_fort_third_guards | thief | 无P2快照 | — | — | 未验证 |
| gorge_giant_path | cleric | 无P2快照 | — | — | 未验证 |
| gorge_giant_path | hero | 无P2快照 | — | — | 未验证 |
| gorge_giant_path | mage | 无P2快照 | — | — | 未验证 |
| gorge_giant_path | thief | 无P2快照 | — | — | 未验证 |
| gorge_rockfall_path | cleric | 无P2快照 | — | — | 未验证 |
| gorge_rockfall_path | hero | 无P2快照 | — | — | 未验证 |
| gorge_rockfall_path | mage | 无P2快照 | — | — | 未验证 |
| gorge_rockfall_path | thief | 无P2快照 | — | — | 未验证 |
| gorge_worm_lair | cleric | 无P2快照 | — | — | 未验证 |
| gorge_worm_lair | hero | 无P2快照 | — | — | 未验证 |
| gorge_worm_lair | mage | 无P2快照 | — | — | 未验证 |
| gorge_worm_lair | thief | 无P2快照 | — | — | 未验证 |
| grave_chapel | cleric | 无P2快照 | — | — | 未验证 |
| grave_chapel | hero | 无P2快照 | — | — | 未验证 |
| grave_chapel | mage | 无P2快照 | — | — | 未验证 |
| grave_chapel | thief | 无P2快照 | — | — | 未验证 |
| ice_elemental_encounter | cleric | [0.18,0.25] | 0.1284/0.1284/—/— (Lv6) | 0.1852/0.1852/—/— (Lv6) | 通过 |
| ice_elemental_encounter | hero | [0.18,0.25] | 0.1116/0.1116/—/— (Lv6) | 0.1509/0.1509/—/— (Lv6) | 失败 |
| ice_elemental_encounter | mage | [0.18,0.25] | 0.2959/0.0000/—/— (Lv6) | 0.3642/0.0000/—/— (Lv6) | 失败 |
| ice_elemental_encounter | thief | [0.18,0.25] | 0.1296/0.1296/—/— (Lv6) | 0.2031/0.2031/0.1760/0.1760 (Lv6) | 通过 |
| inn_night_ambush | cleric | 无P2快照 | — | — | 未验证 |
| inn_night_ambush | hero | 无P2快照 | — | — | 未验证 |
| inn_night_ambush | mage | 无P2快照 | — | — | 未验证 |
| inn_night_ambush | thief | 无P2快照 | — | — | 未验证 |
| lost_goblin_crossroads | cleric | 无P2快照 | — | — | 未验证 |
| lost_goblin_crossroads | hero | 无P2快照 | — | — | 未验证 |
| lost_goblin_crossroads | mage | 无P2快照 | — | — | 未验证 |
| lost_goblin_crossroads | thief | 无P2快照 | — | — | 未验证 |
| mansion_corridor | cleric | 无P2快照 | — | — | 未验证 |
| mansion_corridor | hero | 无P2快照 | — | — | 未验证 |
| mansion_corridor | mage | 无P2快照 | — | — | 未验证 |
| mansion_corridor | thief | 无P2快照 | — | — | 未验证 |
| merchant_battle | cleric | 无P2快照 | — | — | 未验证 |
| merchant_battle | hero | 无P2快照 | — | — | 未验证 |
| merchant_battle | mage | 无P2快照 | — | — | 未验证 |
| merchant_battle | thief | 无P2快照 | — | — | 未验证 |
| slime_ambush_one | cleric | [0.1,0.15] | 0.0866/0.0866/—/— (Lv5) | 0.1139/0.1139/—/— (Lv6) | 通过 |
| slime_ambush_one | hero | [0.1,0.15] | 0.0490/0.0490/—/— (Lv5) | 0.0549/0.0549/—/— (Lv6) | 失败 |
| slime_ambush_one | mage | [0.1,0.15] | 0.1371/0.0000/—/— (Lv5) | 0.1673/0.0000/—/— (Lv5) | 失败 |
| slime_ambush_one | thief | [0.1,0.15] | 0.0667/0.0667/—/— (Lv5) | 0.1023/0.1023/—/— (Lv5) | 通过 |
| slime_ambush_two | cleric | [0.1,0.15] | 0.0866/0.0866/—/— (Lv5) | 0.1139/0.1139/—/— (Lv6) | 通过 |
| slime_ambush_two | hero | [0.1,0.15] | 0.0490/0.0490/—/— (Lv5) | 0.0549/0.0549/—/— (Lv6) | 失败 |
| slime_ambush_two | mage | [0.1,0.15] | 0.1371/0.0000/—/— (Lv5) | 0.1673/0.0000/—/— (Lv5) | 失败 |
| slime_ambush_two | thief | [0.1,0.15] | 0.0667/0.0667/—/— (Lv5) | 0.1023/0.1023/—/— (Lv5) | 通过 |
| slime_king_battle | cleric | [0.28,0.35] | 0.1361/0.1361/0.1361/0.1361 (Lv5) | 0.2848/0.2848/0.2848/0.2848 (Lv6) | 通过 |
| slime_king_battle | hero | [0.28,0.35] | 0.0931/0.0931/0.0931/0.0931 (Lv5) | 0.2194/0.2194/0.2194/0.2194 (Lv6) | 失败 |
| slime_king_battle | mage | [0.28,0.35] | 0.2154/0.0000/0.2154/0.1436 (Lv5) | 0.3833/0.0000/0.3833/0.2556 (Lv6) | 失败 |
| slime_king_battle | thief | [0.28,0.35] | 0.1150/0.1150/0.1150/0.1150 (Lv5) | 0.3068/0.3068/0.3068/0.3068 (Lv5) | 通过 |
| valley_entrance | cleric | [0.18,0.25] | 0.9053/0.9053/0.4527/0.4527 (Lv7) | 0.1804/0.1804/0.1203/0.1203 (Lv6) | 通过 |
| valley_entrance | hero | [0.18,0.25] | 0.8702/0.8702/—/— (Lv7) | 0.1554/0.1554/—/— (Lv6) | 失败 |
| valley_entrance | mage | [0.18,0.25] | 1.6287/0.0000/—/— (Lv7) | 0.3194/0.0000/—/— (Lv6) | 失败 |
| valley_entrance | thief | [0.18,0.25] | 0.9124/0.9124/—/— (Lv7) | 0.1979/0.1979/—/— (Lv6) | 通过 |
| valley_ledge | cleric | 无P2快照 | — | — | 未验证 |
| valley_ledge | hero | 无P2快照 | — | — | 未验证 |
| valley_ledge | mage | 无P2快照 | — | — | 未验证 |
| valley_ledge | thief | 无P2快照 | — | — | 未验证 |
| village_fire_elemental | cleric | [0.18,0.25] | 0.1047/0.1047/—/— (Lv6) | 0.1852/0.1852/0.1852/0.1852 (Lv6) | 通过 |
| village_fire_elemental | hero | [0.18,0.25] | 0.0858/0.0858/0.0858/0.0858 (Lv6) | 0.1509/0.1509/0.1509/0.1509 (Lv6) | 失败 |
| village_fire_elemental | mage | [0.18,0.25] | 0.3012/0.0000/0.3012/0.2008 (Lv5) | 0.3642/0.0000/—/— (Lv6) | 失败 |
| village_fire_elemental | thief | [0.18,0.25] | 0.1057/0.1057/0.1057/0.1057 (Lv6) | 0.2031/0.2031/0.2031/0.2031 (Lv6) | 通过 |
| village_fire_slime | cleric | [0.1,0.15] | 0.0219/0.0219/—/— (Lv6) | 0.0285/0.0285/—/— (Lv6) | 失败 |
| village_fire_slime | hero | [0.1,0.15] | 0.0218/0.0218/0.0218/0.0218 (Lv6) | 0.0274/0.0274/—/— (Lv6) | 失败 |
| village_fire_slime | mage | [0.1,0.15] | 0.0870/0.0000/—/— (Lv6) | 0.0958/0.0000/—/— (Lv6) | 失败 |
| village_fire_slime | thief | [0.1,0.15] | 0.0221/0.0221/—/— (Lv6) | 0.0312/0.0312/—/— (Lv6) | 失败 |
| xanxus_phantom_battle | cleric | 无P2快照 | — | — | 未验证 |
| xanxus_phantom_battle | hero | 无P2快照 | — | — | 未验证 |
| xanxus_phantom_battle | mage | 无P2快照 | — | — | 未验证 |
| xanxus_phantom_battle | thief | 无P2快照 | — | — | 未验证 |

### L2 方向要求的未满足清单

共享敌人公式、职业防御/HP/闪避以及离散伤害导致同一参数不能逐格独立定位。本次没有找到全满足候选；不声称全局数学无解。以下严格列出未满足“低值到上半段 / 高值只降至上限”的格，包含已进入标准带但未落指定位置者；不将它们隐含批准。

| 遭遇 | 职业 | 前 | 后 | 方向差异 |
| --- | --- | --- | --- | --- |
| cave_crystal_corridor | cleric | 0.3288 | 0.2676 | 原高值未恰落标准上限（含仍过高/压低） |
| cave_crystal_corridor | mage | 0.5166 | 0.3572 | 原高值未恰落标准上限（含仍过高/压低） |
| cave_heat_corridor | cleric | 0.3988 | 0.2193 | 原高值未恰落标准上限（含仍过高/压低） |
| cave_heat_corridor | hero | 0.2800 | 0.0909 | 原高值未恰落标准上限（含仍过高/压低） |
| cave_heat_corridor | mage | 0.6267 | 0.2927 | 原高值未恰落标准上限（含仍过高/压低） |
| cave_heat_corridor | thief | 0.4091 | 0.1705 | 原高值未恰落标准上限（含仍过高/压低） |
| cave_lava_room | cleric | 0.3418 | 0.3760 | 原高值未恰落标准上限（含仍过高/压低） |
| cave_lava_room | mage | 0.5371 | 0.5018 | 原高值未恰落标准上限（含仍过高/压低） |
| cave_lava_room | thief | 0.2720 | 0.3214 | 原高值未恰落标准上限（含仍过高/压低） |
| cave_prism_tree | cleric | 0.1581 | 0.2379 | 原低值未达标准带内上半段 |
| cave_prism_tree | hero | 0.1146 | 0.1728 | 原低值未达标准带内上半段 |
| cave_prism_tree | thief | 0.1587 | 0.2260 | 原低值未达标准带内上半段 |
| draco_battle | cleric | 0.0902 | 0.2807 | 原低值未达标准带内上半段 |
| draco_battle | hero | 0.0757 | 0.2505 | 原低值未达标准带内上半段 |
| draco_battle | mage | 0.2160 | 0.4688 | 原低值未达标准带内上半段 |
| draco_battle | thief | 0.0908 | 0.3101 | 原低值未达标准带内上半段 |
| dragon_valley_loc | cleric | 0.1376 | 0.2826 | 原低值未达标准带内上半段 |
| dragon_valley_loc | hero | 0.1226 | 0.2478 | 原低值未达标准带内上半段 |
| dragon_valley_loc | thief | 0.1387 | 0.3100 | 原低值未达标准带内上半段 |
| forest_wolves | cleric | 0.1421 | 0.1994 | 原低值未达标准带内上半段 |
| forest_wolves | hero | 0.1034 | 0.1371 | 原低值未达标准带内上半段 |
| forest_wolves | thief | 0.1232 | 0.1875 | 原低值未达标准带内上半段 |
| frost_wolf_battle | cleric | 0.0874 | 0.2848 | 原低值未达标准带内上半段 |
| frost_wolf_battle | hero | 0.0726 | 0.2469 | 原低值未达标准带内上半段 |
| frost_wolf_battle | mage | 0.2263 | 0.4983 | 原低值未达标准带内上半段 |
| frost_wolf_battle | thief | 0.0882 | 0.3125 | 原低值未达标准带内上半段 |
| goblin_fort | cleric | 0.1828 | 0.1828 | 原高值未恰落标准上限（含仍过高/压低） |
| goblin_fort | mage | 0.2742 | 0.2742 | 原高值未恰落标准上限（含仍过高/压低） |
| goblin_fort | thief | 0.1562 | 0.1464 | 原高值未恰落标准上限（含仍过高/压低） |
| goblin_fort_first_second | cleric | 0.3656 | 0.2350 | 原高值未恰落标准上限（含仍过高/压低） |
| goblin_fort_first_second | hero | 0.2613 | 0.1715 | 原高值未恰落标准上限（含仍过高/压低） |
| goblin_fort_first_second | mage | 0.5483 | 0.3525 | 原高值未恰落标准上限（含仍过高/压低） |
| goblin_fort_first_second | thief | 0.3124 | 0.2050 | 原高值未恰落标准上限（含仍过高/压低） |
| goblin_fort_fourth | cleric | 0.6539 | 0.2910 | 原高值未恰落标准上限（含仍过高/压低） |
| goblin_fort_fourth | hero | 0.4949 | 0.1917 | 原高值未恰落标准上限（含仍过高/压低） |
| goblin_fort_fourth | mage | 1.0027 | 0.4073 | 原高值未恰落标准上限（含仍过高/压低） |
| goblin_fort_fourth | thief | 0.5920 | 0.3221 | 原高值未恰落标准上限（含仍过高/压低） |
| goblin_fort_second_right | hero | 0.0784 | 0.1715 | 原低值未达标准带内上半段 |
| goblin_fort_second_right | thief | 0.1562 | 0.2050 | 原低值未达标准带内上半段 |
| ice_elemental_encounter | cleric | 0.1284 | 0.1852 | 原低值未达标准带内上半段 |
| ice_elemental_encounter | hero | 0.1116 | 0.1509 | 原低值未达标准带内上半段 |
| ice_elemental_encounter | mage | 0.2959 | 0.3642 | 原高值未恰落标准上限（含仍过高/压低） |
| ice_elemental_encounter | thief | 0.1296 | 0.2031 | 原低值未达标准带内上半段 |
| slime_ambush_one | cleric | 0.0866 | 0.1139 | 原低值未达标准带内上半段 |
| slime_ambush_one | hero | 0.0490 | 0.0549 | 原低值未达标准带内上半段 |
| slime_ambush_one | thief | 0.0667 | 0.1023 | 原低值未达标准带内上半段 |
| slime_ambush_two | cleric | 0.0866 | 0.1139 | 原低值未达标准带内上半段 |
| slime_ambush_two | hero | 0.0490 | 0.0549 | 原低值未达标准带内上半段 |
| slime_ambush_two | thief | 0.0667 | 0.1023 | 原低值未达标准带内上半段 |
| slime_king_battle | cleric | 0.1361 | 0.2848 | 原低值未达标准带内上半段 |
| slime_king_battle | hero | 0.0931 | 0.2194 | 原低值未达标准带内上半段 |
| slime_king_battle | mage | 0.2154 | 0.3833 | 原低值未达标准带内上半段 |
| slime_king_battle | thief | 0.1150 | 0.3068 | 原低值未达标准带内上半段 |
| valley_entrance | cleric | 0.9053 | 0.1804 | 原高值未恰落标准上限（含仍过高/压低） |
| valley_entrance | hero | 0.8702 | 0.1554 | 原高值未恰落标准上限（含仍过高/压低） |
| valley_entrance | mage | 1.6287 | 0.3194 | 原高值未恰落标准上限（含仍过高/压低） |
| valley_entrance | thief | 0.9124 | 0.1979 | 原高值未恰落标准上限（含仍过高/压低） |
| village_fire_elemental | cleric | 0.1047 | 0.1852 | 原低值未达标准带内上半段 |
| village_fire_elemental | hero | 0.0858 | 0.1509 | 原低值未达标准带内上半段 |
| village_fire_elemental | mage | 0.3012 | 0.3642 | 原高值未恰落标准上限（含仍过高/压低） |
| village_fire_elemental | thief | 0.1057 | 0.2031 | 原低值未达标准带内上半段 |
| village_fire_slime | cleric | 0.0219 | 0.0285 | 原低值未达标准带内上半段 |
| village_fire_slime | hero | 0.0218 | 0.0274 | 原低值未达标准带内上半段 |
| village_fire_slime | mage | 0.0870 | 0.0958 | 原低值未达标准带内上半段 |
| village_fire_slime | thief | 0.0221 | 0.0312 | 原低值未达标准带内上半段 |

### M4 超限前后清单

包括实际路线和 P2 checkpoint 三策略；每行 n 和胜率可区分短败北与真正短战斗。Q4 仅适用于 attack_only / best_free 胜率<10%。

| 原型 | 职业 | 遭遇 | 策略 | 前 | 后 | 后状态 |
| --- | --- | --- | --- | --- | --- | --- |
| P2 | cleric | draco_battle | heuristic_v3 | 中位39；n=47；胜89.4% [77.4, 95.4] | 中位4.0；n=244；胜99.2% [97.1, 99.8] | Q4/通过/缺样本 |
| P2 | hero | cave_prism_tree | heuristic_v3 | 中位16；n=125；胜98.4% [94.4, 99.6] | 中位8.0；n=490；胜99.4% [98.2, 99.8] | Q4/通过/缺样本 |
| P2 | hero | draco_battle | heuristic_v3 | 中位20；n=119；胜87.4% [80.2, 92.2] | 中位12；n=369；胜69.9% [65.1, 74.4] | Q4/通过/缺样本 |
| P2 | thief | cave_prism_tree | heuristic_v3 | 中位15；n=241；胜93.8% [90.0, 96.2] | 中位6；n=321；胜83.5% [79.0, 87.1] | Q4/通过/缺样本 |
| P2 | thief | draco_battle | heuristic_v3 | 中位48；n=231；胜89.2% [84.5, 92.6] | 中位26.5；n=32；胜53.1% [36.4, 69.1] | 失败 |
| P2 | thief | goblin_fort_fourth | heuristic_v3 | 中位15；n=487；胜53.2% [48.7, 57.6] | 中位6.0；n=500；胜70.6% [66.5, 74.4] | Q4/通过/缺样本 |
| P2s | hero | cave_prism_tree | heuristic_v3 | 中位16；n=119；胜99.2% [95.4, 99.9] | 中位7.0；n=496；胜100.0% [99.2, 100.0] | Q4/通过/缺样本 |
| P2s | hero | draco_battle | heuristic_v3 | 中位36；n=77；胜89.6% [80.8, 94.6] | 中位13.0；n=384；胜62.0% [57.0, 66.7] | Q4/通过/缺样本 |
| P2s | thief | cave_prism_tree | heuristic_v3 | 中位16.0；n=148；胜95.9% [91.4, 98.1] | 中位6；n=323；胜85.1% [80.8, 88.6] | Q4/通过/缺样本 |
| P2s | thief | draco_battle | heuristic_v3 | 中位48.0；n=130；胜87.7% [80.9, 92.3] | 中位30；n=31；胜71.0% [53.4, 83.9] | 失败 |
| P3 | cleric | draco_battle | heuristic_v3 | 中位33.0；n=68；胜58.8% [47.0, 69.7] | 中位10；n=1；胜0.0% [0.0, 79.3] | Q4/通过/缺样本 |
| P3 | cleric | merchant_battle | heuristic_v3 | — | 中位20；n=305；胜86.6% [82.3, 89.9] | 失败 |
| P3 | hero | cave_prism_tree | heuristic_v3 | 中位19.0；n=202；胜98.0% [95.0, 99.2] | 中位8.0；n=500；胜99.0% [97.7, 99.6] | Q4/通过/缺样本 |
| P3 | hero | draco_battle | heuristic_v3 | 中位23.0；n=160；胜45.0% [37.5, 52.7] | 中位7.0；n=84；胜67.9% [57.3, 76.9] | Q4/通过/缺样本 |
| P3 | thief | cave_prism_tree | heuristic_v3 | 中位16；n=221；胜73.8% [67.6, 79.1] | 中位6.0；n=352；胜71.9% [67.0, 76.3] | Q4/通过/缺样本 |
| P3 | thief | draco_battle | heuristic_v3 | 中位28.0；n=112；胜40.2% [31.6, 49.4] | 中位2.5；n=10；胜0.0% [0.0, 27.8] | Q4/通过/缺样本 |
| checkpoint | cleric | cave_prism_tree | attack_only | 中位22.0；n=500；胜99.4% [98.3, 99.8] | 中位9.0；n=500；胜95.4% [93.2, 96.9] | Q4/通过/缺样本 |
| checkpoint | cleric | draco_battle | attack_only | 中位48.0；n=500；胜94.0% [91.6, 95.8] | 中位4.0；n=500；胜91.2% [88.4, 93.4] | Q4/通过/缺样本 |
| checkpoint | cleric | draco_battle | best_free | 中位45.0；n=500；胜58.2% [53.8, 62.4] | 中位4.0；n=500；胜89.6% [86.6, 92.0] | Q4/通过/缺样本 |
| checkpoint | cleric | draco_battle | heuristic_v3 | 中位41.0；n=500；胜96.8% [94.9, 98.0] | 中位4.0；n=500；胜99.4% [98.3, 99.8] | Q4/通过/缺样本 |
| checkpoint | hero | cave_prism_tree | attack_only | 中位24.0；n=500；胜100.0% [99.2, 100.0] | 中位11.0；n=500；胜99.6% [98.6, 99.9] | Q4/通过/缺样本 |
| checkpoint | hero | cave_prism_tree | best_free | 中位20.0；n=500；胜100.0% [99.2, 100.0] | 中位9.0；n=500；胜93.0% [90.4, 94.9] | Q4/通过/缺样本 |
| checkpoint | hero | cave_prism_tree | heuristic_v3 | 中位15.0；n=500；胜100.0% [99.2, 100.0] | 中位7.0；n=500；胜98.8% [97.4, 99.4] | Q4/通过/缺样本 |
| checkpoint | hero | draco_battle | attack_only | 中位43.0；n=500；胜64.8% [60.5, 68.9] | 中位25.0；n=500；胜45.8% [41.5, 50.2] | 失败 |
| checkpoint | hero | draco_battle | best_free | 中位41.0；n=500；胜48.8% [44.4, 53.2] | 中位15.0；n=500；胜21.6% [18.2, 25.4] | 失败 |
| checkpoint | hero | draco_battle | heuristic_v3 | 中位18.0；n=500；胜99.6% [98.6, 99.9] | 中位13.0；n=500；胜88.8% [85.7, 91.3] | Q4/通过/缺样本 |
| checkpoint | mage | cave_prism_tree | attack_only | 中位18.0；n=500；胜70.8% [66.7, 74.6] | 中位10.0；n=500；胜24.2% [20.7, 28.1] | Q4/通过/缺样本 |
| checkpoint | mage | goblin_fort_fourth | attack_only | 中位2.0；n=500；胜0.0% [0.0, 0.8]；Q4只报告 | 中位15.0；n=500；胜47.8% [43.5, 52.2] | 失败 |
| checkpoint | mage | goblin_fort_fourth | best_free | 中位2.0；n=500；胜0.0% [0.0, 0.8]；Q4只报告 | 中位15.0；n=500；胜41.8% [37.6, 46.2] | 失败 |
| checkpoint | thief | cave_prism_tree | attack_only | 中位28.0；n=500；胜80.8% [77.1, 84.0] | 中位11.0；n=500；胜7.6% [5.6, 10.3]；Q4只报告 | Q4/通过/缺样本 |
| checkpoint | thief | cave_prism_tree | best_free | 中位16.0；n=500；胜80.8% [77.1, 84.0] | 中位8.0；n=500；胜41.2% [37.0, 45.6] | Q4/通过/缺样本 |
| checkpoint | thief | cave_prism_tree | heuristic_v3 | 中位17.0；n=500；胜92.4% [89.7, 94.4] | 中位8.0；n=500；胜64.2% [59.9, 68.3] | Q4/通过/缺样本 |
| checkpoint | thief | draco_battle | attack_only | 中位35.0；n=500；胜26.0% [22.3, 30.0] | 中位8.0；n=500；胜2.8% [1.7, 4.6]；Q4只报告 | Q4/通过/缺样本 |
| checkpoint | thief | draco_battle | best_free | 中位25.0；n=500；胜12.4% [9.8, 15.6] | 中位7.0；n=500；胜0.4% [0.1, 1.4]；Q4只报告 | Q4/通过/缺样本 |
| checkpoint | thief | draco_battle | heuristic_v3 | 中位48.0；n=500；胜91.2% [88.4, 93.4] | 中位28.0；n=500；胜67.2% [63.0, 71.2] | 失败 |

### M3 首测样本表

每一行保持原测量的样本分组；同一职业/遭遇/同伴可能有多个不同回复或受伤组，不合并掩盖失败。主口径为同伴+敬虔なる心。S是解析比值，非二项率。

| 阶段 | 职业 | 遭遇 | 同伴 | n | 期望回复 | 期望来伤 | S | <0.5 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 前 | cleric | dragon_valley_loc | fire_bat_dragon | 58 | 1.6500 | 10.3400 | 0.1596 | True |
| 前 | cleric | frost_wolf_battle | fire_bat_dragon | 187 | 3.8900 | 6.1100 | 0.6367 | False |
| 前 | cleric | frost_wolf_battle | fire_bat_dragon | 70 | 4.0400 | 6.1100 | 0.6612 | False |
| 前 | cleric | frost_wolf_battle | none | 3 | 0.6900 | 6.1100 | 0.1129 | True |
| 前 | cleric | frost_wolf_battle | none | 3 | 1.6500 | 6.1100 | 0.2700 | True |
| 前 | cleric | slime_king_battle | none | 124 | 0.0000 | 5.1700 | 0.0000 | True |
| 前 | hero | dragon_valley_loc | fire_bat_dragon | 89 | 0.0000 | 9.8467 | 0.0000 | True |
| 前 | hero | dragon_valley_loc | none | 5 | 0.0000 | 9.8467 | 0.0000 | True |
| 前 | hero | frost_wolf_battle | fire_bat_dragon | 248 | 3.2000 | 5.4717 | 0.5848 | False |
| 前 | hero | frost_wolf_battle | none | 31 | 0.0000 | 5.4717 | 0.0000 | True |
| 前 | hero | slime_king_battle | none | 170 | 0.0000 | 4.5080 | 0.0000 | True |
| 前 | mage | dragon_valley_loc | fire_bat_dragon | 3 | 0.0000 | 10.3400 | 0.0000 | True |
| 前 | mage | frost_wolf_battle | fire_bat_dragon | 99 | 3.2000 | 6.1100 | 0.5237 | False |
| 前 | mage | slime_king_battle | fire_bat_dragon | 11 | 3.0000 | 5.1700 | 0.5803 | False |
| 前 | mage | slime_king_battle | none | 41 | 0.0000 | 5.1700 | 0.0000 | True |
| 前 | thief | dragon_valley_loc | fire_bat_dragon | 56 | 0.0000 | 7.5357 | 0.0000 | True |
| 前 | thief | dragon_valley_loc | none | 7 | 0.0000 | 7.5357 | 0.0000 | True |
| 前 | thief | frost_wolf_battle | fire_bat_dragon | 201 | 3.2000 | 4.1875 | 0.7642 | False |
| 前 | thief | frost_wolf_battle | none | 59 | 0.0000 | 4.1875 | 0.0000 | True |
| 前 | thief | slime_king_battle | fire_bat_dragon | 7 | 3.0000 | 3.7720 | 0.7953 | False |
| 前 | thief | slime_king_battle | none | 45 | 0.0000 | 3.7720 | 0.0000 | True |
| 后 | cleric | dragon_valley_loc | fire_bat_dragon | 4 | 1.3500 | 14.4760 | 0.0933 | True |
| 后 | cleric | frost_wolf_battle | fire_bat_dragon | 206 | 3.8300 | 12.2200 | 0.3134 | True |
| 后 | cleric | frost_wolf_battle | none | 4 | 0.6300 | 12.2200 | 0.0516 | True |
| 后 | cleric | slime_king_battle | none | 131 | 0.0000 | 9.4000 | 0.0000 | True |
| 后 | hero | dragon_valley_loc | fire_bat_dragon | 25 | 0.0000 | 13.9957 | 0.0000 | True |
| 后 | hero | frost_wolf_battle | fire_bat_dragon | 208 | 3.2000 | 11.7600 | 0.2721 | True |
| 后 | hero | frost_wolf_battle | none | 1 | 0.0000 | 11.7600 | 0.0000 | True |
| 后 | hero | slime_king_battle | none | 170 | 0.0000 | 8.8200 | 0.0000 | True |
| 后 | mage | frost_wolf_battle | fire_bat_dragon | 86 | 3.2000 | 12.2200 | 0.2619 | True |
| 后 | mage | slime_king_battle | fire_bat_dragon | 11 | 3.0000 | 9.4000 | 0.3191 | True |
| 后 | thief | dragon_valley_loc | fire_bat_dragon | 4 | 0.0000 | 10.8214 | 0.0000 | True |
| 后 | thief | frost_wolf_battle | fire_bat_dragon | 139 | 3.2000 | 9.0000 | 0.3556 | True |
| 后 | thief | frost_wolf_battle | none | 10 | 0.0000 | 9.0000 | 0.0000 | True |
| 后 | thief | slime_king_battle | fire_bat_dragon | 7 | 3.0000 | 7.3800 | 0.4065 | True |
| 后 | thief | slime_king_battle | none | 48 | 0.0000 | 7.3800 | 0.0000 | True |

### 参数全表与轮次

路径为有效 normal 值，写入位置均为两包 `difficulty_overlays.normal` 的对应 set 值；基础叙事/数值和 difficulty_only 条目未拆分，Q14 结构性做法使用 0 处。元数据仅更新 content_revision 与 overlay_revision。

| 数据路径 | 旧值 | 新值 | 允许范围/约束 | 改变轮次 |
| --- | --- | --- | --- | --- |
| progression.exp_table.4 | 90 | 54 | [54,126]；严格递增 | 1 |
| progression.exp_table.5 | 140 | 99 | [84,196]；严格递增 | 1 |
| progression.exp_table.6 | 200 | 171 | [160,360]；严格递增 | 1 |
| progression.exp_table.7 | 280 | 319 | [224,504]；严格递增 | 1 |
| progression.exp_table.8 | 380 | 679 | [304,684]；严格递增 | 1 |
| progression.exp_rewards.trash | 5 | 4 | 3–8 | 1 |
| progression.exp_rewards.elite | 15 | 12 | 10–20 | 1 |
| progression.exp_rewards.boss | 40 | 25 | 25–50 | 1 |
| progression.exp_rewards.quest | 10 | 30 | 5–30 | 1 |
| progression.exp_rewards.unclassified | 5 | 4 | 同 trash | 1 |
| progression.level_gains.hero.max_hp | 5 | 3 | Lv2–8 平均 HP 基础值15–20%，MP/SP10–15%；已批准的三个整数例外见正文 | 1,5 |
| progression.level_gains.hero.max_sp | 2 | 1 | Lv2–8 平均 HP 基础值15–20%，MP/SP10–15%；已批准的三个整数例外见正文 | 1 |
| progression.level_gains.hero.by_level.2.max_sp | null | 2 | Lv2–8 平均 HP 基础值15–20%，MP/SP10–15%；已批准的三个整数例外见正文 | 5 |
| progression.level_gains.hero.by_level.4.max_sp | null | 2 | Lv2–8 平均 HP 基础值15–20%，MP/SP10–15%；已批准的三个整数例外见正文 | 5 |
| progression.level_gains.hero.by_level.4.attributes.dex | null | 1 | 主+2/副+1；dex 依满级闪避带宽，逐级覆盖 | 1 |
| progression.level_gains.hero.by_level.6.max_sp | null | 2 | Lv2–8 平均 HP 基础值15–20%，MP/SP10–15%；已批准的三个整数例外见正文 | 5 |
| progression.level_gains.hero.by_level.6.attributes.dex | null | 1 | 主+2/副+1；dex 依满级闪避带宽，逐级覆盖 | 1 |
| progression.level_gains.hero.by_level.8.attributes.dex | null | 1 | 主+2/副+1；dex 依满级闪避带宽，逐级覆盖 | 1 |
| progression.level_gains.cleric.max_hp | 5 | 3 | Lv2–8 平均 HP 基础值15–20%，MP/SP10–15%；已批准的三个整数例外见正文 | 1 |
| progression.level_gains.mage.max_hp | 3 | 2 | Lv2–8 平均 HP 基础值15–20%，MP/SP10–15%；已批准的三个整数例外见正文 | 1 |
| progression.level_gains.mage.by_level.2.max_hp | null | 3 | Lv2–8 平均 HP 基础值15–20%，MP/SP10–15%；已批准的三个整数例外见正文 | 5 |
| progression.level_gains.mage.by_level.4.max_hp | null | 3 | Lv2–8 平均 HP 基础值15–20%，MP/SP10–15%；已批准的三个整数例外见正文 | 5 |
| progression.level_gains.mage.by_level.4.attributes.dex | null | 1 | 主+2/副+1；dex 依满级闪避带宽，逐级覆盖 | 1 |
| progression.level_gains.mage.by_level.8.attributes.dex | null | 1 | 主+2/副+1；dex 依满级闪避带宽，逐级覆盖 | 1 |
| progression.level_gains.thief.max_hp | 4 | 2 | Lv2–8 平均 HP 基础值15–20%，MP/SP10–15%；已批准的三个整数例外见正文 | 1 |
| enemies.slime.combat.basic_attack.damage | "1d6" | "4" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.ignis.hp | 168 | 149 | [100.8,252]（原有效 normal 值×0.6–1.5） | 2 |
| enemies.ignis.max_hp | 168 | 149 | [100.8,252]（原有效 normal 值×0.6–1.5） | 2 |
| enemies.ignis.skills.@id=fire_breath.damage | "1d21" | "2d4+17" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.goblin.combat.basic_attack.damage | "1d6" | "1d2+2" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.goblin_archer.combat.basic_attack.damage | "1d6" | "1" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.hobgoblin.combat.basic_attack.damage | "1d6" | "1d2+3" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.forest_wolf.combat.basic_attack.damage | "1d12" | "2d4+2" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.slime_king.hp | 80 | 93 | [48,120]（原有效 normal 值×0.6–1.5） | 2,3 |
| enemies.slime_king.max_hp | 80 | 93 | [48,120]（原有效 normal 值×0.6–1.5） | 2,3 |
| enemies.slime_king.combat.basic_attack.damage | "1d10" | "2d4+5" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.goblin_king.hp | 56 | 51 | [33.6,84]（原有效 normal 值×0.6–1.5） | 2 |
| enemies.goblin_king.max_hp | 56 | 51 | [33.6,84]（原有效 normal 值×0.6–1.5） | 2 |
| enemies.goblin_king.combat.basic_attack.damage | "1d24" | "1d2+4" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.fire_slime.combat.basic_attack.damage | "1d6" | "1d2+2" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.fire_elemental.combat.basic_attack.damage | "2d10" | "1d2+12" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2,3 |
| enemies.ice_elemental.combat.basic_attack.damage | "1d16" | "1d2+8" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.frost_dire_wolf.hp | 48 | 56 | [28.8,72]（原有效 normal 值×0.6–1.5） | 2,3 |
| enemies.frost_dire_wolf.max_hp | 48 | 56 | [28.8,72]（原有效 normal 值×0.6–1.5） | 2,3 |
| enemies.frost_dire_wolf.combat.basic_attack.damage | "1d12" | "2d4+8" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.draco_human.hp | 25 | 15 | [15,37.5]（原有效 normal 值×0.6–1.5） | 2 |
| enemies.draco_human.max_hp | 25 | 15 | [15,37.5]（原有效 normal 值×0.6–1.5） | 2 |
| enemies.draco_human.skills.@id=sword_flash.damage | "1d8+5" | "1d2+8" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.draco_human.skills.@id=ice_blade.damage | "1d8+4" | "1d2+24" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2,3 |
| enemies.draco_dragon.hp | 220 | 132 | [132,330]（原有效 normal 值×0.6–1.5） | 3 |
| enemies.draco_dragon.max_hp | 220 | 132 | [132,330]（原有效 normal 值×0.6–1.5） | 3 |
| enemies.heat_lizard.combat.basic_attack.damage | "2d5+1" | "1d2+2" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.ruby_golem.skills.@id=ruby_fist.damage | "1d12" | "1d2+5" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.sapphire_moth.combat.basic_attack.damage | "1d3" | "1" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.emerald_spider.combat.basic_attack.damage | "1d3" | "1" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.prism_tree.hp | 130 | 78 | [78,195]（原有效 normal 值×0.6–1.5） | 2,3,4 |
| enemies.prism_tree.max_hp | 130 | 78 | [78,195]（原有效 normal 值×0.6–1.5） | 2,3,4 |
| enemies.prism_tree.combat.defense | 2 | 0 | [0,4] | 3 |
| enemies.prism_tree.skills.@id=crystal_rain.damage | "1d14" | "2d4+6" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.ash_wraith.skills.@id=ash_embrace.damage | "1d64" | "1" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |
| enemies.ash_wraith.skills.@id=resentment.damage | "1d64" | "1d2+9" | 正伤害；按 M9 带宽反推；骰子 CV≤0.5 为软目标 | 2 |

### 伤害公式 CV 核对

受调整敌人的全部基础攻击/伤害技能共32条，其中实际改变的21条公式均满足裸骰子CV≤0.5；仍有7条未改公式超过0.5，作为M10软目标差距保留。它们没有在本段添加预告，预告机制属于052b。开场实际CV还含闪避和AI混合，见辅助指标M10，不与裸骰子CV混用。

| 敌人 | 路径 | 旧公式 | 新公式 | 旧CV | 新CV | 本轮改过 |
| --- | --- | --- | --- | --- | --- | --- |
| ash_wraith | combat.basic_attack.damage | 1d64 | 1d64 | 0.5684 | 0.5684 | False |
| ash_wraith | skills.@id=ash_embrace.damage | 1d64 | 1 | 0.5684 | 0.0000 | True |
| ash_wraith | skills.@id=resentment.damage | 1d64 | 1d2+9 | 0.5684 | 0.0476 | True |
| draco_dragon | combat.basic_attack.damage | 1d12+10 | 1d12+10 | 0.2092 | 0.2092 | False |
| draco_dragon | skills.@id=frozen_breath.damage | 1d12+10 | 1d12+10 | 0.2092 | 0.2092 | False |
| draco_dragon | skills.@id=white_wings.damage | 1d12+10 | 1d12+10 | 0.2092 | 0.2092 | False |
| draco_human | combat.basic_attack.damage | 1d8+5 | 1d8+5 | 0.2412 | 0.2412 | False |
| draco_human | skills.@id=ice_blade.damage | 1d8+4 | 1d2+24 | 0.2696 | 0.0196 | True |
| draco_human | skills.@id=sword_flash.damage | 1d8+5 | 1d2+8 | 0.2412 | 0.0526 | True |
| emerald_spider | combat.basic_attack.damage | 1d3 | 1 | 0.4082 | 0.0000 | True |
| fire_elemental | combat.basic_attack.damage | 2d10 | 1d2+12 | 0.3693 | 0.0370 | True |
| fire_slime | combat.basic_attack.damage | 1d6 | 1d2+2 | 0.4880 | 0.1429 | True |
| forest_wolf | combat.basic_attack.damage | 1d12 | 2d4+2 | 0.5311 | 0.2259 | True |
| frost_dire_wolf | combat.basic_attack.damage | 1d12 | 2d4+8 | 0.5311 | 0.1216 | True |
| goblin | combat.basic_attack.damage | 1d6 | 1d2+2 | 0.4880 | 0.1429 | True |
| goblin_archer | combat.basic_attack.damage | 1d6 | 1 | 0.4880 | 0.0000 | True |
| goblin_king | combat.basic_attack.damage | 1d24 | 1d2+4 | 0.5538 | 0.0909 | True |
| heat_lizard | combat.basic_attack.damage | 2d5+1 | 1d2+2 | 0.2857 | 0.1429 | True |
| hobgoblin | combat.basic_attack.damage | 1d6 | 1d2+3 | 0.4880 | 0.1111 | True |
| ice_elemental | combat.basic_attack.damage | 1d16 | 1d2+8 | 0.5423 | 0.0526 | True |
| ignis | combat.basic_attack.damage | 1d21 | 1d21 | 0.5505 | 0.5505 | False |
| ignis | skills.@id=fire_breath.damage | 1d21 | 2d4+17 | 0.5505 | 0.0719 | True |
| ignis | skills.@id=tail_sweep.damage | 1d21 | 1d21 | 0.5505 | 0.5505 | False |
| prism_tree | combat.basic_attack.damage | 1d14 | 1d14 | 0.5375 | 0.5375 | False |
| prism_tree | skills.@id=crystal_rain.damage | 1d14 | 2d4+6 | 0.5375 | 0.1437 | True |
| prism_tree | skills.@id=prism_branch.damage | 1d14 | 1d14 | 0.5375 | 0.5375 | False |
| ruby_golem | combat.basic_attack.damage | 1d12 | 1d12 | 0.5311 | 0.5311 | False |
| ruby_golem | skills.@id=ruby_fist.damage | 1d12 | 1d2+5 | 0.5311 | 0.0769 | True |
| ruby_golem | skills.@id=ruby_ray.damage | 1d12 | 1d12 | 0.5311 | 0.5311 | False |
| sapphire_moth | combat.basic_attack.damage | 1d3 | 1 | 0.4082 | 0.0000 | True |
| slime | combat.basic_attack.damage | 1d6 | 4 | 0.4880 | 0.0000 | True |
| slime_king | combat.basic_attack.damage | 1d10 | 2d4+5 | 0.5222 | 0.1581 | True |

每级成长按 Lv2–8 七次升级的平均值落实区间。勇者 SP=10/7（基础10的14.29%）；魔法使い HP=16/7（基础12的19.05%）。盗賊 HP+2 / MP+1、魔法使い SP+1 保留已批准整数例外。dex 按等级配置使满级基础闪避满足各职业区间。

prism_tree HP78 是原有效130×0.6的052a下界，防御2→0；052b 的90–110结构重做范围不提前用于本段。ヴァイス抗性保持不变。伤害保持正值，未实施0伤害候选。

### 五轮迭代与停止判定


| 轮 | 杠杆 | 改动 | 主指标失败数 | M3失败/组 | 秒 |
| --- | --- | --- | --- | --- | --- |
| r1-l1 | L1 | Bounded baseline-ledger search plus approved integer growth and by_level dex. Prediction is not engine acceptance. | {"m1_fail":0,"arrival_fail":3,"m4_fail":9,"m9_fail":60,"m9_observed":78,"m9_missing":66} | 6/22 | 221.644 |
| r2-l2 | L2 | Shared-enemy opening expectation fit with positive low-variance dice, plus bounded primary Boss HP from P2 victory durations; unfitted/missing cells remain explicit exceptions. | {"m1_fail":0,"arrival_fail":6,"m4_fail":14,"m9_fail":42,"m9_observed":80,"m9_missing":64} | 0/13 | 416.099 |
| r3-l2 | L2 | Refit two damages to observed round2 P2 snapshots; reduce HP for M4 outliers. Prism defense 2->0 within +/-2. Preserve Vaiss resistances AND defense under Q9; only reduce dragon HP220->132 within x0.6. Slime120->93 and frost72->56 project max ordinary-policy medians18 toward14. | {"m1_fail":0,"arrival_fail":5,"m4_fail":6,"m9_fail":40,"m9_observed":80,"m9_missing":64} | 0/14 | 410.85 |
| r4-l2 | L2 | Boundary check for remaining prism M4 rows: HP130x0.6=78, defense already0. This uses the 052a L2 global range; follow-up 052b structural/HP redesign remains separate. Other parameters unchanged; round3 opening search found no further improvements. | {"m1_fail":0,"arrival_fail":5,"m4_fail":7,"m9_fail":40,"m9_observed":80,"m9_missing":64} | 0/14 | 415.856 |
| r5-l1 | L1 | Round3 M9 breakdown: hero16 low/3pass, mage17high/2pass, cleric16pass and thief15pass. Tighten hero/mage HP spread within existing growth ranges: heroHP3 (15%); mageHP3 atLv2/4 else2 (average16/7=2.286,19.05%). Hero dex+1 atLv4/6/8 reaches6% final evasion; SP2 atLv2/4/6 else1 averages10/7=1.429 (14.29%). Other classes and all EXP/enemy numbers unchanged. | {"m1_fail":0,"arrival_fail":5,"m4_fail":5,"m9_fail":40,"m9_observed":80,"m9_missing":64} | 0/14 | 414.043 |


| 比较 | M9通过率变化 | M4通过率变化 | 两者均<2pp |
| --- | --- | --- | --- |
| r2-l2→r3-l2 | 2.6316pp (配对76格) | 4.1237pp (配对194格) | False |
| r3-l2→r4-l2 | 0.0000pp (配对76格) | -0.5102pp (配对196格) | True |
| r4-l2→r5-l1 | 0.0000pp (配对76格) | 1.0204pp (配对196格) | True |

停止判断对 M9 与 M4 各自的配对已观察格计算，不人为加权，也不给缺失格通过分。第4、5轮均没有任何一个主要指标改善≥2pp，触发停滞。选第5轮：与第3轮同为40个M9失败和5个到达等级未认证格，M4失败由6降到5，M1与M3保持通过。只执行一次最终验收，没有再调第6轮。

### P3 全部互斥分支（两种护送顺序）

每职业8组合（火种×商人×护送顺序）；两阶段均完整报告。055 已合入的再借动作按现有路线执行，不改剧情。证据包含动作地点、同行者和任务标记，见原始 branch_proposals 的 escort_audit；动作被尝试不等于检定必定成功。

| 阶段 | 职业 | 组合 | Ignis [CI] | 通关 [CI] | 报告成功轨迹数 | 报告后借龙成功轨迹数 | 选中 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 前 | hero | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 90 | 44 | False |
| 前 | hero | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 81 | 56 | False |
| 前 | hero | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_before_escort"} | 35.5% [29.2, 42.3] | 14.5% [10.3, 20.0] | 90 | 44 | True |
| 前 | hero | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_after_report"} | 32.0% [25.9, 38.8] | 14.5% [10.3, 20.0] | 81 | 56 | False |
| 前 | hero | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 90 | 44 | False |
| 前 | hero | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 81 | 56 | False |
| 前 | hero | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 90 | 44 | False |
| 前 | hero | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 81 | 56 | False |
| 前 | cleric | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_before_escort"} | 11.5% [7.8, 16.7] | 2.0% [0.8, 5.0] | 41 | 30 | False |
| 前 | cleric | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_after_report"} | 8.5% [5.4, 13.2] | 2.5% [1.1, 5.7] | 29 | 29 | False |
| 前 | cleric | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_before_escort"} | 14.0% [9.9, 19.5] | 8.5% [5.4, 13.2] | 41 | 30 | True |
| 前 | cleric | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_after_report"} | 10.5% [7.0, 15.5] | 6.0% [3.5, 10.2] | 29 | 29 | False |
| 前 | cleric | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 41 | 30 | False |
| 前 | cleric | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 29 | 29 | False |
| 前 | cleric | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 41 | 30 | False |
| 前 | cleric | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 29 | 29 | False |
| 前 | mage | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_before_escort"} | 28.5% [22.7, 35.1] | 4.5% [2.4, 8.3] | 24 | 9 | True |
| 前 | mage | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_after_report"} | 21.0% [15.9, 27.2] | 3.0% [1.4, 6.4] | 23 | 11 | False |
| 前 | mage | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_before_escort"} | 23.5% [18.2, 29.8] | 3.0% [1.4, 6.4] | 24 | 9 | False |
| 前 | mage | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_after_report"} | 19.5% [14.6, 25.5] | 4.0% [2.0, 7.7] | 23 | 11 | False |
| 前 | mage | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 24 | 9 | False |
| 前 | mage | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 23 | 11 | False |
| 前 | mage | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 24 | 9 | False |
| 前 | mage | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 23 | 11 | False |
| 前 | thief | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 67 | 35 | False |
| 前 | thief | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 24 | 11 | False |
| 前 | thief | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_before_escort"} | 23.5% [18.2, 29.8] | 9.5% [6.2, 14.4] | 67 | 35 | True |
| 前 | thief | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_after_report"} | 5.5% [3.1, 9.6] | 0.5% [0.1, 2.8] | 24 | 11 | False |
| 前 | thief | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 67 | 35 | False |
| 前 | thief | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 24 | 11 | False |
| 前 | thief | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 67 | 35 | False |
| 前 | thief | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 24 | 11 | False |
| 后 | hero | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 200 | 89 | False |
| 后 | hero | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 200 | 144 | False |
| 后 | hero | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_before_escort"} | 16.0% [11.6, 21.7] | 12.5% [8.6, 17.8] | 200 | 89 | True |
| 后 | hero | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_after_report"} | 15.5% [11.1, 21.2] | 9.0% [5.8, 13.8] | 200 | 144 | False |
| 后 | hero | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 200 | 89 | False |
| 后 | hero | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 200 | 144 | False |
| 后 | hero | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 200 | 89 | False |
| 后 | hero | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 200 | 144 | False |
| 后 | cleric | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 117 | 78 | False |
| 后 | cleric | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_after_report"} | 1.0% [0.3, 3.6] | 0.0% [0.0, 1.9] | 122 | 122 | True |
| 后 | cleric | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_before_escort"} | 0.5% [0.1, 2.8] | 0.0% [0.0, 1.9] | 117 | 78 | False |
| 后 | cleric | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 122 | 122 | False |
| 后 | cleric | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 117 | 78 | False |
| 后 | cleric | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 122 | 122 | False |
| 后 | cleric | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 117 | 78 | False |
| 后 | cleric | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 122 | 122 | False |
| 后 | mage | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_before_escort"} | 7.5% [4.6, 12.0] | 2.5% [1.1, 5.7] | 119 | 41 | True |
| 后 | mage | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_after_report"} | 5.0% [2.7, 9.0] | 0.5% [0.1, 2.8] | 112 | 73 | False |
| 后 | mage | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_before_escort"} | 2.5% [1.1, 5.7] | 0.0% [0.0, 1.9] | 119 | 41 | False |
| 后 | mage | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_after_report"} | 4.5% [2.4, 8.3] | 1.0% [0.3, 3.6] | 112 | 73 | False |
| 后 | mage | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 119 | 41 | False |
| 后 | mage | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 112 | 73 | False |
| 后 | mage | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 119 | 41 | False |
| 后 | mage | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 112 | 73 | False |
| 后 | thief | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 77 | 29 | False |
| 后 | thief | {"fire_seed":"accept","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 70 | 32 | False |
| 后 | thief | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_before_escort"} | 0.5% [0.1, 2.8] | 0.0% [0.0, 1.9] | 77 | 29 | False |
| 后 | thief | {"fire_seed":"accept","merchant":"pay","escort_order":"borrow_after_report"} | 2.0% [0.8, 5.0] | 0.0% [0.0, 1.9] | 70 | 32 | True |
| 后 | thief | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 77 | 29 | False |
| 后 | thief | {"fire_seed":"refuse","merchant":"betray","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 70 | 32 | False |
| 后 | thief | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_before_escort"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 77 | 29 | False |
| 后 | thief | {"fire_seed":"refuse","merchant":"pay","escort_order":"borrow_after_report"} | 0.0% [0.0, 1.9] | 0.0% [0.0, 1.9] | 70 | 32 | False |

### 辅助指标（不提前验收b/c）

M2/M8/M13 的每个胜率补 Wilson 区间；差值已有探针区间为原方法区间，不冒称 Wilson。附表记录 a 的影响，不意味着 b/c 已验收。

#### M2


| 阶段 | 原始指标 | 二项率区间补充 |
| --- | --- | --- |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"ruby_charm","critical":true,"n":500,"full":1,"without":1,"uplift":0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"adamantite_armor","critical":true,"n":500,"full":1,"without":0.99,"uplift":0.010000000000000009,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"99.0% [97.7, 99.6]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"purification","critical":true,"n":500,"full":1,"without":1,"uplift":0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"ice_iron_greatsword","critical":true,"n":500,"full":1,"without":0.99,"uplift":0.010000000000000009,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"99.0% [97.7, 99.6]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"fire_bat_dragon","critical":true,"n":500,"full":1,"without":1,"uplift":0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"fire_bat_empowered","critical":true,"n":500,"full":1,"without":1,"uplift":0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"ruby_charm","critical":true,"n":500,"full":1,"without":0.998,"uplift":0.0020000000000000018,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"99.8% [98.9, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"adamantite_armor","critical":true,"n":500,"full":1,"without":0.976,"uplift":0.02400000000000002,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"97.6% [95.9, 98.6]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"purification","critical":true,"n":500,"full":1,"without":1,"uplift":0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"ice_iron_greatsword","critical":true,"n":500,"full":1,"without":1,"uplift":0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"fire_bat_dragon","critical":true,"n":500,"full":1,"without":1,"uplift":0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"fire_bat_empowered","critical":true,"n":500,"full":1,"without":1,"uplift":0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"100.0% [99.2, 100.0]","without_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"ruby_charm","critical":true,"n":500,"full":0.78,"without":0.63,"uplift":0.15000000000000002,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.0% [74.2, 81.4]","without_wilson":"63.0% [58.7, 67.1]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"adamantite_armor","critical":true,"n":500,"full":0.78,"without":0.78,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.0% [74.2, 81.4]","without_wilson":"78.0% [74.2, 81.4]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"purification","critical":true,"n":500,"full":0.78,"without":0.78,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.0% [74.2, 81.4]","without_wilson":"78.0% [74.2, 81.4]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"ice_iron_greatsword","critical":true,"n":500,"full":0.78,"without":0.78,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.0% [74.2, 81.4]","without_wilson":"78.0% [74.2, 81.4]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"fire_bat_dragon","critical":true,"n":500,"full":0.78,"without":0.764,"uplift":0.016000000000000014,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.0% [74.2, 81.4]","without_wilson":"76.4% [72.5, 79.9]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"fire_bat_empowered","critical":true,"n":500,"full":0.78,"without":0.78,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.0% [74.2, 81.4]","without_wilson":"78.0% [74.2, 81.4]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"ruby_charm","critical":true,"n":500,"full":0.908,"without":0.866,"uplift":0.04200000000000004,"status":"proposed","source":"P2 observed"} | {"full_wilson":"90.8% [87.9, 93.0]","without_wilson":"86.6% [83.3, 89.3]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"adamantite_armor","critical":true,"n":500,"full":0.908,"without":0.85,"uplift":0.05800000000000005,"status":"proposed","source":"P2 observed"} | {"full_wilson":"90.8% [87.9, 93.0]","without_wilson":"85.0% [81.6, 87.9]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"purification","critical":true,"n":500,"full":0.908,"without":0.908,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"90.8% [87.9, 93.0]","without_wilson":"90.8% [87.9, 93.0]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"ice_iron_greatsword","critical":true,"n":500,"full":0.908,"without":0.916,"uplift":-0.008000000000000007,"status":"proposed","source":"P2 observed"} | {"full_wilson":"90.8% [87.9, 93.0]","without_wilson":"91.6% [88.8, 93.7]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"fire_bat_dragon","critical":true,"n":500,"full":0.908,"without":0.896,"uplift":0.01200000000000001,"status":"proposed","source":"P2 observed"} | {"full_wilson":"90.8% [87.9, 93.0]","without_wilson":"89.6% [86.6, 92.0]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"fire_bat_empowered","critical":true,"n":500,"full":0.908,"without":0.908,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"90.8% [87.9, 93.0]","without_wilson":"90.8% [87.9, 93.0]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"ruby_charm","critical":true,"n":500,"full":0.876,"without":0.358,"uplift":0.518,"status":"proposed","source":"P2 observed"} | {"full_wilson":"87.6% [84.4, 90.2]","without_wilson":"35.8% [31.7, 40.1]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"adamantite_armor","critical":true,"n":500,"full":0.876,"without":0.562,"uplift":0.31399999999999995,"status":"proposed","source":"P2 observed"} | {"full_wilson":"87.6% [84.4, 90.2]","without_wilson":"56.2% [51.8, 60.5]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"purification","critical":true,"n":500,"full":0.876,"without":0.876,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"87.6% [84.4, 90.2]","without_wilson":"87.6% [84.4, 90.2]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"ice_iron_greatsword","critical":true,"n":500,"full":0.876,"without":0.724,"uplift":0.15200000000000002,"status":"proposed","source":"P2 observed"} | {"full_wilson":"87.6% [84.4, 90.2]","without_wilson":"72.4% [68.3, 76.1]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"fire_bat_dragon","critical":true,"n":500,"full":0.876,"without":0.846,"uplift":0.030000000000000027,"status":"proposed","source":"P2 observed"} | {"full_wilson":"87.6% [84.4, 90.2]","without_wilson":"84.6% [81.2, 87.5]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","preparation":"fire_bat_empowered","critical":true,"n":500,"full":0.876,"without":0.876,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"87.6% [84.4, 90.2]","without_wilson":"87.6% [84.4, 90.2]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"ruby_charm","critical":true,"n":500,"full":0.782,"without":0.24,"uplift":0.542,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.2% [74.4, 81.6]","without_wilson":"24.0% [20.5, 27.9]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"adamantite_armor","critical":true,"n":500,"full":0.782,"without":0.312,"uplift":0.47000000000000003,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.2% [74.4, 81.6]","without_wilson":"31.2% [27.3, 35.4]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"purification","critical":true,"n":500,"full":0.782,"without":0.66,"uplift":0.122,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.2% [74.4, 81.6]","without_wilson":"66.0% [61.7, 70.0]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"ice_iron_greatsword","critical":true,"n":500,"full":0.782,"without":0.782,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.2% [74.4, 81.6]","without_wilson":"78.2% [74.4, 81.6]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"fire_bat_dragon","critical":true,"n":500,"full":0.782,"without":0.78,"uplift":0.0020000000000000018,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.2% [74.4, 81.6]","without_wilson":"78.0% [74.2, 81.4]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","preparation":"fire_bat_empowered","critical":true,"n":500,"full":0.782,"without":0.782,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"78.2% [74.4, 81.6]","without_wilson":"78.2% [74.4, 81.6]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"ruby_charm","critical":true,"n":500,"full":0.076,"without":0.052,"uplift":0.024,"status":"proposed","source":"P2 observed"} | {"full_wilson":"7.6% [5.6, 10.3]","without_wilson":"5.2% [3.6, 7.5]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"adamantite_armor","critical":true,"n":500,"full":0.076,"without":0.076,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"7.6% [5.6, 10.3]","without_wilson":"7.6% [5.6, 10.3]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"purification","critical":true,"n":500,"full":0.076,"without":0.076,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"7.6% [5.6, 10.3]","without_wilson":"7.6% [5.6, 10.3]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"ice_iron_greatsword","critical":true,"n":500,"full":0.076,"without":0.076,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"7.6% [5.6, 10.3]","without_wilson":"7.6% [5.6, 10.3]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"fire_bat_dragon","critical":true,"n":500,"full":0.076,"without":0.106,"uplift":-0.03,"status":"proposed","source":"P2 observed"} | {"full_wilson":"7.6% [5.6, 10.3]","without_wilson":"10.6% [8.2, 13.6]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","preparation":"fire_bat_empowered","critical":true,"n":500,"full":0.076,"without":0.076,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"7.6% [5.6, 10.3]","without_wilson":"7.6% [5.6, 10.3]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"ruby_charm","critical":true,"n":500,"full":0.148,"without":0.042,"uplift":0.10599999999999998,"status":"proposed","source":"P2 observed"} | {"full_wilson":"14.8% [12.0, 18.2]","without_wilson":"4.2% [2.8, 6.3]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"adamantite_armor","critical":true,"n":500,"full":0.148,"without":0.068,"uplift":0.07999999999999999,"status":"proposed","source":"P2 observed"} | {"full_wilson":"14.8% [12.0, 18.2]","without_wilson":"6.8% [4.9, 9.4]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"purification","critical":true,"n":500,"full":0.148,"without":0.148,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"14.8% [12.0, 18.2]","without_wilson":"14.8% [12.0, 18.2]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"ice_iron_greatsword","critical":true,"n":500,"full":0.148,"without":0.106,"uplift":0.041999999999999996,"status":"proposed","source":"P2 observed"} | {"full_wilson":"14.8% [12.0, 18.2]","without_wilson":"10.6% [8.2, 13.6]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"fire_bat_dragon","critical":true,"n":500,"full":0.148,"without":0.134,"uplift":0.013999999999999985,"status":"proposed","source":"P2 observed"} | {"full_wilson":"14.8% [12.0, 18.2]","without_wilson":"13.4% [10.7, 16.7]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","preparation":"fire_bat_empowered","critical":true,"n":500,"full":0.148,"without":0.148,"uplift":0.0,"status":"proposed","source":"P2 observed"} | {"full_wilson":"14.8% [12.0, 18.2]","without_wilson":"14.8% [12.0, 18.2]"} |


#### M8


| 阶段 | 原始指标 | 二项率区间补充 |
| --- | --- | --- |
| 前 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"robin","n":500,"without":0.122,"with_companion":0.812,"uplift":0.69,"ci95":[0.6464904027816827,0.7335095972183172]} | {"without_wilson":"12.2% [9.6, 15.4]","with_companion_wilson":"81.2% [77.5, 84.4]"} |
| 前 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"blue_robed_mage","n":500,"without":0.122,"with_companion":0.168,"uplift":0.046,"ci95":[0.008374890744437882,0.08362510925556212]} | {"without_wilson":"12.2% [9.6, 15.4]","with_companion_wilson":"16.8% [13.8, 20.3]"} |
| 前 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon","n":500,"without":0.122,"with_companion":0.404,"uplift":0.282,"ci95":[0.23125558163511592,0.332744418364884]} | {"without_wilson":"12.2% [9.6, 15.4]","with_companion_wilson":"40.4% [36.2, 44.8]"} |
| 前 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"mina","n":500,"without":0.122,"with_companion":0.21,"uplift":0.088,"ci95":[0.04393167425613113,0.13206832574386887]} | {"without_wilson":"12.2% [9.6, 15.4]","with_companion_wilson":"21.0% [17.7, 24.8]"} |
| 前 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"paladin_liese","n":500,"without":0.122,"with_companion":0.266,"uplift":0.144,"ci95":[0.099323729978813,0.18867627002118698]} | {"without_wilson":"12.2% [9.6, 15.4]","with_companion_wilson":"26.6% [22.9, 30.6]"} |
| 前 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"hydromancer_elio","n":500,"without":0.122,"with_companion":0.53,"uplift":0.408,"ci95":[0.35855728811323717,0.4574427118867628]} | {"without_wilson":"12.2% [9.6, 15.4]","with_companion_wilson":"53.0% [48.6, 57.3]"} |
| 前 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon:empowered","n":500,"without":0.122,"with_companion":0.422,"uplift":0.3,"ci95":[0.2505211771783561,0.3494788228216439]} | {"without_wilson":"12.2% [9.6, 15.4]","with_companion_wilson":"42.2% [37.9, 46.6]"} |
| 前 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"robin","n":500,"without":0,"with_companion":0.582,"uplift":0.582,"ci95":[0.5387231709680327,0.6252768290319672]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"58.2% [53.8, 62.4]"} |
| 前 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"blue_robed_mage","n":500,"without":0,"with_companion":0.002,"uplift":0.002,"ci95":[-0.0019199999999999998,0.00592]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.2% [0.0, 1.1]"} |
| 前 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon","n":500,"without":0,"with_companion":0.136,"uplift":0.136,"ci95":[0.10592316564647372,0.1660768343535263]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"13.6% [10.9, 16.9]"} |
| 前 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"mina","n":500,"without":0,"with_companion":0.024,"uplift":0.024,"ci95":[0.01057122713419567,0.03742877286580433]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"2.4% [1.4, 4.1]"} |
| 前 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"paladin_liese","n":500,"without":0,"with_companion":0.058,"uplift":0.058,"ci95":[0.037490964032587365,0.07850903596741264]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"5.8% [4.1, 8.2]"} |
| 前 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"hydromancer_elio","n":500,"without":0,"with_companion":0.334,"uplift":0.334,"ci95":[0.2926175549984221,0.3753824450015779]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"33.4% [29.4, 37.6]"} |
| 前 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon:empowered","n":500,"without":0,"with_companion":0.114,"uplift":0.114,"ci95":[0.08611471515257475,0.14188528484742524]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"11.4% [8.9, 14.5]"} |
| 前 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"robin","n":500,"without":0.046,"with_companion":0.812,"uplift":0.766,"ci95":[0.7284404240667101,0.80355957593329]} | {"without_wilson":"4.6% [3.1, 6.8]","with_companion_wilson":"81.2% [77.5, 84.4]"} |
| 前 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"blue_robed_mage","n":500,"without":0.046,"with_companion":0.048,"uplift":0.002,"ci95":[-0.014177809191001136,0.018177809191001135]} | {"without_wilson":"4.6% [3.1, 6.8]","with_companion_wilson":"4.8% [3.2, 7.0]"} |
| 前 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon","n":500,"without":0.046,"with_companion":0.184,"uplift":0.138,"ci95":[0.09965820393028382,0.1763417960697162]} | {"without_wilson":"4.6% [3.1, 6.8]","with_companion_wilson":"18.4% [15.2, 22.0]"} |
| 前 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"mina","n":500,"without":0.046,"with_companion":0.064,"uplift":0.018,"ci95":[-0.009422038209424156,0.045422038209424156]} | {"without_wilson":"4.6% [3.1, 6.8]","with_companion_wilson":"6.4% [4.6, 8.9]"} |
| 前 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"paladin_liese","n":500,"without":0.046,"with_companion":0.22,"uplift":0.174,"ci95":[0.13478782553782429,0.2132121744621757]} | {"without_wilson":"4.6% [3.1, 6.8]","with_companion_wilson":"22.0% [18.6, 25.8]"} |
| 前 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"hydromancer_elio","n":500,"without":0.046,"with_companion":0.298,"uplift":0.252,"ci95":[0.207910715619389,0.296089284380611]} | {"without_wilson":"4.6% [3.1, 6.8]","with_companion_wilson":"29.8% [26.0, 34.0]"} |
| 前 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon:empowered","n":500,"without":0.046,"with_companion":0.242,"uplift":0.196,"ci95":[0.15359399656824393,0.23840600343175608]} | {"without_wilson":"4.6% [3.1, 6.8]","with_companion_wilson":"24.2% [20.7, 28.1]"} |
| 前 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"robin","n":500,"without":0,"with_companion":0.736,"uplift":0.736,"ci95":[0.6973235442515926,0.7746764557484074]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"73.6% [69.6, 77.3]"} |
| 前 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"blue_robed_mage","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 前 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon","n":500,"without":0,"with_companion":0.942,"uplift":0.942,"ci95":[0.9214909640325873,0.9625090359674126]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"94.2% [91.8, 95.9]"} |
| 前 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"mina","n":500,"without":0,"with_companion":0.048,"uplift":0.048,"ci95":[0.029243798428392025,0.06675620157160797]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"4.8% [3.2, 7.0]"} |
| 前 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"paladin_liese","n":500,"without":0,"with_companion":0.888,"uplift":0.888,"ci95":[0.8603292269250545,0.9156707730749455]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"88.8% [85.7, 91.3]"} |
| 前 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"hydromancer_elio","n":500,"without":0,"with_companion":0.612,"uplift":0.612,"ci95":[0.5692439700698161,0.6547560299301839]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"61.2% [56.9, 65.4]"} |
| 前 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon:empowered","n":500,"without":0,"with_companion":0.998,"uplift":0.998,"ci95":[0.99408,1]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"99.8% [98.9, 100.0]"} |
| 前 | {"character":"hero","encounter":"cave_prism_tree","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"cave_prism_tree","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"cave_prism_tree","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"cave_prism_tree","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"cave_prism_tree","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"cave_prism_tree","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"cave_prism_tree","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"cave_prism_tree","companion":"robin","n":500,"without":0.996,"with_companion":0.992,"uplift":-0.004,"ci95":[-0.013605206337062994,0.0056052063370629936]} | {"without_wilson":"99.6% [98.6, 99.9]","with_companion_wilson":"99.2% [98.0, 99.7]"} |
| 前 | {"character":"cleric","encounter":"cave_prism_tree","companion":"blue_robed_mage","n":500,"without":0.996,"with_companion":1,"uplift":0.004,"ci95":[-0.001538159551912971,0.009538159551912971]} | {"without_wilson":"99.6% [98.6, 99.9]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"cave_prism_tree","companion":"fire_bat_dragon","n":500,"without":0.996,"with_companion":1,"uplift":0.004,"ci95":[-0.001538159551912971,0.009538159551912971]} | {"without_wilson":"99.6% [98.6, 99.9]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"cave_prism_tree","companion":"mina","n":500,"without":0.996,"with_companion":0.992,"uplift":-0.004,"ci95":[-0.013605206337062994,0.0056052063370629936]} | {"without_wilson":"99.6% [98.6, 99.9]","with_companion_wilson":"99.2% [98.0, 99.7]"} |
| 前 | {"character":"cleric","encounter":"cave_prism_tree","companion":"paladin_liese","n":500,"without":0.996,"with_companion":1,"uplift":0.004,"ci95":[-0.001538159551912971,0.009538159551912971]} | {"without_wilson":"99.6% [98.6, 99.9]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"cave_prism_tree","companion":"hydromancer_elio","n":500,"without":0.996,"with_companion":1,"uplift":0.004,"ci95":[-0.001538159551912971,0.009538159551912971]} | {"without_wilson":"99.6% [98.6, 99.9]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"cave_prism_tree","companion":"fire_bat_dragon:empowered","n":500,"without":0.996,"with_companion":1,"uplift":0.004,"ci95":[-0.001538159551912971,0.009538159551912971]} | {"without_wilson":"99.6% [98.6, 99.9]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"cave_prism_tree","companion":"robin","n":500,"without":0.878,"with_companion":0.882,"uplift":0.004,"ci95":[-0.03715298537421581,0.045152985374215804]} | {"without_wilson":"87.8% [84.6, 90.4]","with_companion_wilson":"88.2% [85.1, 90.7]"} |
| 前 | {"character":"mage","encounter":"cave_prism_tree","companion":"blue_robed_mage","n":500,"without":0.878,"with_companion":0.898,"uplift":0.02,"ci95":[-0.014162952663218948,0.05416295266321895]} | {"without_wilson":"87.8% [84.6, 90.4]","with_companion_wilson":"89.8% [86.8, 92.2]"} |
| 前 | {"character":"mage","encounter":"cave_prism_tree","companion":"fire_bat_dragon","n":500,"without":0.878,"with_companion":0.962,"uplift":0.084,"ci95":[0.0501376335658442,0.11786236643415582]} | {"without_wilson":"87.8% [84.6, 90.4]","with_companion_wilson":"96.2% [94.1, 97.6]"} |
| 前 | {"character":"mage","encounter":"cave_prism_tree","companion":"mina","n":500,"without":0.878,"with_companion":0.858,"uplift":-0.02,"ci95":[-0.06074085854655274,0.020740858546552745]} | {"without_wilson":"87.8% [84.6, 90.4]","with_companion_wilson":"85.8% [82.5, 88.6]"} |
| 前 | {"character":"mage","encounter":"cave_prism_tree","companion":"paladin_liese","n":500,"without":0.878,"with_companion":0.9,"uplift":0.022,"ci95":[-0.016994821751700494,0.06099482175170049]} | {"without_wilson":"87.8% [84.6, 90.4]","with_companion_wilson":"90.0% [87.1, 92.3]"} |
| 前 | {"character":"mage","encounter":"cave_prism_tree","companion":"hydromancer_elio","n":500,"without":0.878,"with_companion":0.974,"uplift":0.096,"ci95":[0.06378746013974532,0.1282125398602547]} | {"without_wilson":"87.8% [84.6, 90.4]","with_companion_wilson":"97.4% [95.6, 98.5]"} |
| 前 | {"character":"mage","encounter":"cave_prism_tree","companion":"fire_bat_dragon:empowered","n":500,"without":0.878,"with_companion":0.982,"uplift":0.104,"ci95":[0.07246374182056597,0.13553625817943402]} | {"without_wilson":"87.8% [84.6, 90.4]","with_companion_wilson":"98.2% [96.6, 99.1]"} |
| 前 | {"character":"thief","encounter":"cave_prism_tree","companion":"robin","n":500,"without":0.514,"with_companion":0.752,"uplift":0.238,"ci95":[0.18023986421612614,0.29576013578387383]} | {"without_wilson":"51.4% [47.0, 55.8]","with_companion_wilson":"75.2% [71.2, 78.8]"} |
| 前 | {"character":"thief","encounter":"cave_prism_tree","companion":"blue_robed_mage","n":500,"without":0.514,"with_companion":0.946,"uplift":0.432,"ci95":[0.3857895456050172,0.4782104543949828]} | {"without_wilson":"51.4% [47.0, 55.8]","with_companion_wilson":"94.6% [92.3, 96.3]"} |
| 前 | {"character":"thief","encounter":"cave_prism_tree","companion":"fire_bat_dragon","n":500,"without":0.514,"with_companion":0.924,"uplift":0.41,"ci95":[0.36115539671016783,0.4588446032898321]} | {"without_wilson":"51.4% [47.0, 55.8]","with_companion_wilson":"92.4% [89.7, 94.4]"} |
| 前 | {"character":"thief","encounter":"cave_prism_tree","companion":"mina","n":500,"without":0.514,"with_companion":0.648,"uplift":0.134,"ci95":[0.0739726543544486,0.1940273456455514]} | {"without_wilson":"51.4% [47.0, 55.8]","with_companion_wilson":"64.8% [60.5, 68.9]"} |
| 前 | {"character":"thief","encounter":"cave_prism_tree","companion":"paladin_liese","n":500,"without":0.514,"with_companion":0.92,"uplift":0.406,"ci95":[0.3553552032714975,0.45664479672850256]} | {"without_wilson":"51.4% [47.0, 55.8]","with_companion_wilson":"92.0% [89.3, 94.1]"} |
| 前 | {"character":"thief","encounter":"cave_prism_tree","companion":"hydromancer_elio","n":500,"without":0.514,"with_companion":0.904,"uplift":0.39,"ci95":[0.3396038968329013,0.4403961031670987]} | {"without_wilson":"51.4% [47.0, 55.8]","with_companion_wilson":"90.4% [87.5, 92.7]"} |
| 前 | {"character":"thief","encounter":"cave_prism_tree","companion":"fire_bat_dragon:empowered","n":500,"without":0.514,"with_companion":0.954,"uplift":0.44,"ci95":[0.39337292795279344,0.48662707204720657]} | {"without_wilson":"51.4% [47.0, 55.8]","with_companion_wilson":"95.4% [93.2, 96.9]"} |
| 前 | {"character":"hero","encounter":"slime_king_battle","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"slime_king_battle","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"slime_king_battle","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"slime_king_battle","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"slime_king_battle","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"slime_king_battle","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"slime_king_battle","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"slime_king_battle","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"slime_king_battle","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"slime_king_battle","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"slime_king_battle","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"slime_king_battle","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"slime_king_battle","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"slime_king_battle","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"slime_king_battle","companion":"robin","n":500,"without":0.992,"with_companion":0.996,"uplift":0.004,"ci95":[-0.0056052063370629936,0.013605206337062994]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"99.6% [98.6, 99.9]"} |
| 前 | {"character":"mage","encounter":"slime_king_battle","companion":"blue_robed_mage","n":500,"without":0.992,"with_companion":0.998,"uplift":0.006,"ci95":[-0.002758357291461098,0.014758357291461098]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"99.8% [98.9, 100.0]"} |
| 前 | {"character":"mage","encounter":"slime_king_battle","companion":"fire_bat_dragon","n":500,"without":0.992,"with_companion":0.996,"uplift":0.004,"ci95":[-0.0056052063370629936,0.013605206337062994]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"99.6% [98.6, 99.9]"} |
| 前 | {"character":"mage","encounter":"slime_king_battle","companion":"mina","n":500,"without":0.992,"with_companion":0.998,"uplift":0.006,"ci95":[-0.002758357291461098,0.014758357291461098]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"99.8% [98.9, 100.0]"} |
| 前 | {"character":"mage","encounter":"slime_king_battle","companion":"paladin_liese","n":500,"without":0.992,"with_companion":1,"uplift":0.008,"ci95":[0.00018360266269240068,0.0158163973373076]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"slime_king_battle","companion":"hydromancer_elio","n":500,"without":0.992,"with_companion":1,"uplift":0.008,"ci95":[0.00018360266269240068,0.0158163973373076]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"slime_king_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.992,"with_companion":1,"uplift":0.008,"ci95":[0.00018360266269240068,0.0158163973373076]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"slime_king_battle","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"slime_king_battle","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"slime_king_battle","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"slime_king_battle","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"slime_king_battle","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"slime_king_battle","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"slime_king_battle","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"frost_wolf_battle","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"frost_wolf_battle","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"frost_wolf_battle","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"frost_wolf_battle","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"frost_wolf_battle","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"frost_wolf_battle","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"frost_wolf_battle","companion":"robin","n":500,"without":0.998,"with_companion":1,"uplift":0.002,"ci95":[-0.0019199999999999998,0.00592]} | {"without_wilson":"99.8% [98.9, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"frost_wolf_battle","companion":"blue_robed_mage","n":500,"without":0.998,"with_companion":0.994,"uplift":-0.004,"ci95":[-0.01184,0.0038399999999999997]} | {"without_wilson":"99.8% [98.9, 100.0]","with_companion_wilson":"99.4% [98.3, 99.8]"} |
| 前 | {"character":"mage","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","n":500,"without":0.998,"with_companion":1,"uplift":0.002,"ci95":[-0.0019199999999999998,0.00592]} | {"without_wilson":"99.8% [98.9, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"frost_wolf_battle","companion":"mina","n":500,"without":0.998,"with_companion":0.996,"uplift":-0.002,"ci95":[-0.00879417314892365,0.004794173148923651]} | {"without_wilson":"99.8% [98.9, 100.0]","with_companion_wilson":"99.6% [98.6, 99.9]"} |
| 前 | {"character":"mage","encounter":"frost_wolf_battle","companion":"paladin_liese","n":500,"without":0.998,"with_companion":1,"uplift":0.002,"ci95":[-0.0019199999999999998,0.00592]} | {"without_wilson":"99.8% [98.9, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"frost_wolf_battle","companion":"hydromancer_elio","n":500,"without":0.998,"with_companion":1,"uplift":0.002,"ci95":[-0.0019199999999999998,0.00592]} | {"without_wilson":"99.8% [98.9, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"frost_wolf_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.998,"with_companion":1,"uplift":0.002,"ci95":[-0.0019199999999999998,0.00592]} | {"without_wilson":"99.8% [98.9, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"frost_wolf_battle","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"frost_wolf_battle","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"frost_wolf_battle","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"frost_wolf_battle","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"frost_wolf_battle","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"frost_wolf_battle","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","companion":"robin","n":500,"without":0.764,"with_companion":0.814,"uplift":0.05,"ci95":[0.002303716382281079,0.09769628361771893]} | {"without_wilson":"76.4% [72.5, 79.9]","with_companion_wilson":"81.4% [77.8, 84.6]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","companion":"blue_robed_mage","n":500,"without":0.764,"with_companion":0.81,"uplift":0.046,"ci95":[0.008786367313638528,0.08321363268636148]} | {"without_wilson":"76.4% [72.5, 79.9]","with_companion_wilson":"81.0% [77.3, 84.2]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","n":500,"without":0.764,"with_companion":0.78,"uplift":0.016,"ci95":[-0.03633287456580845,0.06833287456580844]} | {"without_wilson":"76.4% [72.5, 79.9]","with_companion_wilson":"78.0% [74.2, 81.4]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","companion":"mina","n":500,"without":0.764,"with_companion":0.826,"uplift":0.062,"ci95":[0.013451346850347226,0.11054865314965277]} | {"without_wilson":"76.4% [72.5, 79.9]","with_companion_wilson":"82.6% [79.0, 85.7]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","companion":"paladin_liese","n":500,"without":0.764,"with_companion":0.86,"uplift":0.096,"ci95":[0.04803941551515186,0.14396058448484814]} | {"without_wilson":"76.4% [72.5, 79.9]","with_companion_wilson":"86.0% [82.7, 88.8]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","companion":"hydromancer_elio","n":500,"without":0.764,"with_companion":0.894,"uplift":0.13,"ci95":[0.0855105704837952,0.1744894295162048]} | {"without_wilson":"76.4% [72.5, 79.9]","with_companion_wilson":"89.4% [86.4, 91.8]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","companion":"fire_bat_dragon:empowered","n":500,"without":0.764,"with_companion":0.78,"uplift":0.016,"ci95":[-0.03633287456580845,0.06833287456580844]} | {"without_wilson":"76.4% [72.5, 79.9]","with_companion_wilson":"78.0% [74.2, 81.4]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","companion":"robin","n":500,"without":0.896,"with_companion":0.902,"uplift":0.006,"ci95":[-0.029744789617083198,0.041744789617083194]} | {"without_wilson":"89.6% [86.6, 92.0]","with_companion_wilson":"90.2% [87.3, 92.5]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","companion":"blue_robed_mage","n":500,"without":0.896,"with_companion":0.948,"uplift":0.052,"ci95":[0.01855489007409436,0.08544510992590564]} | {"without_wilson":"89.6% [86.6, 92.0]","with_companion_wilson":"94.8% [92.5, 96.4]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","n":500,"without":0.896,"with_companion":0.908,"uplift":0.012,"ci95":[-0.024373755916029315,0.04837375591602931]} | {"without_wilson":"89.6% [86.6, 92.0]","with_companion_wilson":"90.8% [87.9, 93.0]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","companion":"mina","n":500,"without":0.896,"with_companion":0.93,"uplift":0.034,"ci95":[-0.0007487953511587722,0.06874879535115877]} | {"without_wilson":"89.6% [86.6, 92.0]","with_companion_wilson":"93.0% [90.4, 94.9]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","companion":"paladin_liese","n":500,"without":0.896,"with_companion":0.97,"uplift":0.074,"ci95":[0.04353911149922719,0.1044608885007728]} | {"without_wilson":"89.6% [86.6, 92.0]","with_companion_wilson":"97.0% [95.1, 98.2]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","companion":"hydromancer_elio","n":500,"without":0.896,"with_companion":0.938,"uplift":0.042,"ci95":[0.00731862126064587,0.07668137873935413]} | {"without_wilson":"89.6% [86.6, 92.0]","with_companion_wilson":"93.8% [91.3, 95.6]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","companion":"fire_bat_dragon:empowered","n":500,"without":0.896,"with_companion":0.908,"uplift":0.012,"ci95":[-0.024373755916029315,0.04837375591602931]} | {"without_wilson":"89.6% [86.6, 92.0]","with_companion_wilson":"90.8% [87.9, 93.0]"} |
| 前 | {"character":"hero","encounter":"draco_battle","companion":"robin","n":500,"without":0.056,"with_companion":0.156,"uplift":0.1,"ci95":[0.060957430354944914,0.1390425696450551]} | {"without_wilson":"5.6% [3.9, 8.0]","with_companion_wilson":"15.6% [12.7, 19.0]"} |
| 前 | {"character":"hero","encounter":"draco_battle","companion":"blue_robed_mage","n":500,"without":0.056,"with_companion":0.698,"uplift":0.642,"ci95":[0.598851443232685,0.685148556767315]} | {"without_wilson":"5.6% [3.9, 8.0]","with_companion_wilson":"69.8% [65.6, 73.7]"} |
| 前 | {"character":"hero","encounter":"draco_battle","companion":"fire_bat_dragon","n":500,"without":0.056,"with_companion":0.96,"uplift":0.904,"ci95":[0.8769869691357496,0.9310130308642505]} | {"without_wilson":"5.6% [3.9, 8.0]","with_companion_wilson":"96.0% [93.9, 97.4]"} |
| 前 | {"character":"hero","encounter":"draco_battle","companion":"mina","n":500,"without":0.056,"with_companion":0.15,"uplift":0.094,"ci95":[0.05706878998263537,0.13093121001736463]} | {"without_wilson":"5.6% [3.9, 8.0]","with_companion_wilson":"15.0% [12.1, 18.4]"} |
| 前 | {"character":"hero","encounter":"draco_battle","companion":"paladin_liese","n":500,"without":0.056,"with_companion":1,"uplift":0.944,"ci95":[0.923826288341404,0.9641737116585959]} | {"without_wilson":"5.6% [3.9, 8.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"draco_battle","companion":"hydromancer_elio","n":500,"without":0.056,"with_companion":0.952,"uplift":0.896,"ci95":[0.8680898789232825,0.9239101210767175]} | {"without_wilson":"5.6% [3.9, 8.0]","with_companion_wilson":"95.2% [93.0, 96.8]"} |
| 前 | {"character":"hero","encounter":"draco_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.056,"with_companion":0.996,"uplift":0.94,"ci95":[0.919162512585162,0.9608374874148379]} | {"without_wilson":"5.6% [3.9, 8.0]","with_companion_wilson":"99.6% [98.6, 99.9]"} |
| 前 | {"character":"cleric","encounter":"draco_battle","companion":"robin","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 前 | {"character":"cleric","encounter":"draco_battle","companion":"blue_robed_mage","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 前 | {"character":"cleric","encounter":"draco_battle","companion":"fire_bat_dragon","n":500,"without":0,"with_companion":0.914,"uplift":0.914,"ci95":[0.8894003956562766,0.9385996043437235]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"91.4% [88.6, 93.6]"} |
| 前 | {"character":"cleric","encounter":"draco_battle","companion":"mina","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 前 | {"character":"cleric","encounter":"draco_battle","companion":"paladin_liese","n":500,"without":0,"with_companion":0.678,"uplift":0.678,"ci95":[0.6370033300731611,0.718996669926839]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"67.8% [63.6, 71.7]"} |
| 前 | {"character":"cleric","encounter":"draco_battle","companion":"hydromancer_elio","n":500,"without":0,"with_companion":0.88,"uplift":0.88,"ci95":[0.8514873385365824,0.9085126614634176]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"88.0% [84.9, 90.6]"} |
| 前 | {"character":"cleric","encounter":"draco_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0,"with_companion":0.968,"uplift":0.968,"ci95":[0.9525574695501875,0.9834425304498124]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"96.8% [94.9, 98.0]"} |
| 前 | {"character":"mage","encounter":"draco_battle","companion":"robin","n":500,"without":0.086,"with_companion":0.066,"uplift":-0.02,"ci95":[-0.0537092412535759,0.013709241253575904]} | {"without_wilson":"8.6% [6.4, 11.4]","with_companion_wilson":"6.6% [4.7, 9.1]"} |
| 前 | {"character":"mage","encounter":"draco_battle","companion":"blue_robed_mage","n":500,"without":0.086,"with_companion":0.122,"uplift":0.036,"ci95":[0.0028545536456656556,0.06914544635433434]} | {"without_wilson":"8.6% [6.4, 11.4]","with_companion_wilson":"12.2% [9.6, 15.4]"} |
| 前 | {"character":"mage","encounter":"draco_battle","companion":"fire_bat_dragon","n":500,"without":0.086,"with_companion":0.256,"uplift":0.17,"ci95":[0.12381254193436135,0.21618745806563866]} | {"without_wilson":"8.6% [6.4, 11.4]","with_companion_wilson":"25.6% [22.0, 29.6]"} |
| 前 | {"character":"mage","encounter":"draco_battle","companion":"mina","n":500,"without":0.086,"with_companion":0.082,"uplift":-0.004,"ci95":[-0.03820619236325469,0.030206192363254693]} | {"without_wilson":"8.6% [6.4, 11.4]","with_companion_wilson":"8.2% [6.1, 10.9]"} |
| 前 | {"character":"mage","encounter":"draco_battle","companion":"paladin_liese","n":500,"without":0.086,"with_companion":0.148,"uplift":0.062,"ci95":[0.0237386036833966,0.1002613963166034]} | {"without_wilson":"8.6% [6.4, 11.4]","with_companion_wilson":"14.8% [12.0, 18.2]"} |
| 前 | {"character":"mage","encounter":"draco_battle","companion":"hydromancer_elio","n":500,"without":0.086,"with_companion":0.32,"uplift":0.234,"ci95":[0.18632438117800548,0.28167561882199454]} | {"without_wilson":"8.6% [6.4, 11.4]","with_companion_wilson":"32.0% [28.1, 36.2]"} |
| 前 | {"character":"mage","encounter":"draco_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.086,"with_companion":0.384,"uplift":0.298,"ci95":[0.25049002312139046,0.3455099768786095]} | {"without_wilson":"8.6% [6.4, 11.4]","with_companion_wilson":"38.4% [34.2, 42.7]"} |
| 前 | {"character":"thief","encounter":"draco_battle","companion":"robin","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 前 | {"character":"thief","encounter":"draco_battle","companion":"blue_robed_mage","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 前 | {"character":"thief","encounter":"draco_battle","companion":"fire_bat_dragon","n":500,"without":0,"with_companion":0.726,"uplift":0.726,"ci95":[0.6868664370610521,0.7651335629389479]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"72.6% [68.5, 76.3]"} |
| 前 | {"character":"thief","encounter":"draco_battle","companion":"mina","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 前 | {"character":"thief","encounter":"draco_battle","companion":"paladin_liese","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 前 | {"character":"thief","encounter":"draco_battle","companion":"hydromancer_elio","n":500,"without":0,"with_companion":0.41,"uplift":0.41,"ci95":[0.3668457341468697,0.45315426585313023]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"41.0% [36.8, 45.4]"} |
| 前 | {"character":"thief","encounter":"draco_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0,"with_companion":0.912,"uplift":0.912,"ci95":[0.8871432380139154,0.9368567619860847]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"91.2% [88.4, 93.4]"} |
| 后 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"robin","n":500,"without":0.986,"with_companion":0.998,"uplift":0.012,"ci95":[0.0009515178818885524,0.023048482118111446]} | {"without_wilson":"98.6% [97.1, 99.3]","with_companion_wilson":"99.8% [98.9, 100.0]"} |
| 后 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"blue_robed_mage","n":500,"without":0.986,"with_companion":0.84,"uplift":-0.146,"ci95":[-0.17937459867133904,-0.11262540132866095]} | {"without_wilson":"98.6% [97.1, 99.3]","with_companion_wilson":"84.0% [80.5, 87.0]"} |
| 后 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon","n":500,"without":0.986,"with_companion":0.98,"uplift":-0.006,"ci95":[-0.02217019341598054,0.010170193415980541]} | {"without_wilson":"98.6% [97.1, 99.3]","with_companion_wilson":"98.0% [96.4, 98.9]"} |
| 后 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"mina","n":500,"without":0.986,"with_companion":0.968,"uplift":-0.018,"ci95":[-0.03503092328371517,-0.0009690767162848259]} | {"without_wilson":"98.6% [97.1, 99.3]","with_companion_wilson":"96.8% [94.9, 98.0]"} |
| 后 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"paladin_liese","n":500,"without":0.986,"with_companion":0.978,"uplift":-0.008,"ci95":[-0.02463300299938514,0.008633002999385141]} | {"without_wilson":"98.6% [97.1, 99.3]","with_companion_wilson":"97.8% [96.1, 98.8]"} |
| 后 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"hydromancer_elio","n":500,"without":0.986,"with_companion":0.992,"uplift":0.006,"ci95":[-0.007003537548588656,0.019003537548588655]} | {"without_wilson":"98.6% [97.1, 99.3]","with_companion_wilson":"99.2% [98.0, 99.7]"} |
| 后 | {"character":"mage","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon:empowered","n":500,"without":0.986,"with_companion":0.998,"uplift":0.012,"ci95":[0.0009515178818885524,0.023048482118111446]} | {"without_wilson":"98.6% [97.1, 99.3]","with_companion_wilson":"99.8% [98.9, 100.0]"} |
| 后 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"robin","n":500,"without":0.626,"with_companion":0.958,"uplift":0.332,"ci95":[0.2874521202482008,0.3765478797517992]} | {"without_wilson":"62.6% [58.3, 66.7]","with_companion_wilson":"95.8% [93.7, 97.2]"} |
| 后 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"blue_robed_mage","n":500,"without":0.626,"with_companion":0.368,"uplift":-0.258,"ci95":[-0.3164280339006113,-0.1995719660993887]} | {"without_wilson":"62.6% [58.3, 66.7]","with_companion_wilson":"36.8% [32.7, 41.1]"} |
| 后 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon","n":500,"without":0.626,"with_companion":0.87,"uplift":0.244,"ci95":[0.19310500214743276,0.29489499785256723]} | {"without_wilson":"62.6% [58.3, 66.7]","with_companion_wilson":"87.0% [83.8, 89.7]"} |
| 后 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"mina","n":500,"without":0.626,"with_companion":0.788,"uplift":0.162,"ci95":[0.10764576497705208,0.21635423502294793]} | {"without_wilson":"62.6% [58.3, 66.7]","with_companion_wilson":"78.8% [75.0, 82.2]"} |
| 后 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"paladin_liese","n":500,"without":0.626,"with_companion":0.612,"uplift":-0.014,"ci95":[-0.07664802985001344,0.048648029850013444]} | {"without_wilson":"62.6% [58.3, 66.7]","with_companion_wilson":"61.2% [56.9, 65.4]"} |
| 后 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"hydromancer_elio","n":500,"without":0.626,"with_companion":0.946,"uplift":0.32,"ci95":[0.27245730196683676,0.36754269803316325]} | {"without_wilson":"62.6% [58.3, 66.7]","with_companion_wilson":"94.6% [92.3, 96.3]"} |
| 后 | {"character":"thief","encounter":"goblin_fort_fourth","companion":"fire_bat_dragon:empowered","n":500,"without":0.626,"with_companion":0.994,"uplift":0.368,"ci95":[0.3249639950897243,0.4110360049102757]} | {"without_wilson":"62.6% [58.3, 66.7]","with_companion_wilson":"99.4% [98.3, 99.8]"} |
| 后 | {"character":"hero","encounter":"cave_prism_tree","companion":"robin","n":500,"without":0.992,"with_companion":0.996,"uplift":0.004,"ci95":[-0.0056052063370629936,0.013605206337062994]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"99.6% [98.6, 99.9]"} |
| 后 | {"character":"hero","encounter":"cave_prism_tree","companion":"blue_robed_mage","n":500,"without":0.992,"with_companion":0.998,"uplift":0.006,"ci95":[-0.002758357291461098,0.014758357291461098]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"99.8% [98.9, 100.0]"} |
| 后 | {"character":"hero","encounter":"cave_prism_tree","companion":"fire_bat_dragon","n":500,"without":0.992,"with_companion":0.988,"uplift":-0.004,"ci95":[-0.016403578771171864,0.008403578771171864]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"98.8% [97.4, 99.4]"} |
| 后 | {"character":"hero","encounter":"cave_prism_tree","companion":"mina","n":500,"without":0.992,"with_companion":0.992,"uplift":0,"ci95":[-0.011098538422252743,0.011098538422252743]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"99.2% [98.0, 99.7]"} |
| 后 | {"character":"hero","encounter":"cave_prism_tree","companion":"paladin_liese","n":500,"without":0.992,"with_companion":1,"uplift":0.008,"ci95":[0.00018360266269240068,0.0158163973373076]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"cave_prism_tree","companion":"hydromancer_elio","n":500,"without":0.992,"with_companion":0.99,"uplift":-0.002,"ci95":[-0.013770469621481566,0.009770469621481566]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"99.0% [97.7, 99.6]"} |
| 后 | {"character":"hero","encounter":"cave_prism_tree","companion":"fire_bat_dragon:empowered","n":500,"without":0.992,"with_companion":0.99,"uplift":-0.002,"ci95":[-0.013770469621481566,0.009770469621481566]} | {"without_wilson":"99.2% [98.0, 99.7]","with_companion_wilson":"99.0% [97.7, 99.6]"} |
| 后 | {"character":"cleric","encounter":"cave_prism_tree","companion":"robin","n":500,"without":0.918,"with_companion":0.922,"uplift":0.004,"ci95":[-0.029293765458969546,0.03729376545896955]} | {"without_wilson":"91.8% [89.1, 93.9]","with_companion_wilson":"92.2% [89.5, 94.2]"} |
| 后 | {"character":"cleric","encounter":"cave_prism_tree","companion":"blue_robed_mage","n":500,"without":0.918,"with_companion":0.952,"uplift":0.034,"ci95":[0.004007752825419,0.063992247174581]} | {"without_wilson":"91.8% [89.1, 93.9]","with_companion_wilson":"95.2% [93.0, 96.8]"} |
| 后 | {"character":"cleric","encounter":"cave_prism_tree","companion":"fire_bat_dragon","n":500,"without":0.918,"with_companion":0.954,"uplift":0.036,"ci95":[0.005769977152461071,0.06623002284753893]} | {"without_wilson":"91.8% [89.1, 93.9]","with_companion_wilson":"95.4% [93.2, 96.9]"} |
| 后 | {"character":"cleric","encounter":"cave_prism_tree","companion":"mina","n":500,"without":0.918,"with_companion":0.944,"uplift":0.026,"ci95":[-0.004561816143875085,0.05656181614387508]} | {"without_wilson":"91.8% [89.1, 93.9]","with_companion_wilson":"94.4% [92.0, 96.1]"} |
| 后 | {"character":"cleric","encounter":"cave_prism_tree","companion":"paladin_liese","n":500,"without":0.918,"with_companion":0.922,"uplift":0.004,"ci95":[-0.028828043341925184,0.03682804334192519]} | {"without_wilson":"91.8% [89.1, 93.9]","with_companion_wilson":"92.2% [89.5, 94.2]"} |
| 后 | {"character":"cleric","encounter":"cave_prism_tree","companion":"hydromancer_elio","n":500,"without":0.918,"with_companion":0.982,"uplift":0.064,"ci95":[0.03740052864147285,0.09059947135852715]} | {"without_wilson":"91.8% [89.1, 93.9]","with_companion_wilson":"98.2% [96.6, 99.1]"} |
| 后 | {"character":"cleric","encounter":"cave_prism_tree","companion":"fire_bat_dragon:empowered","n":500,"without":0.918,"with_companion":0.98,"uplift":0.062,"ci95":[0.03507660650224661,0.08892339349775338]} | {"without_wilson":"91.8% [89.1, 93.9]","with_companion_wilson":"98.0% [96.4, 98.9]"} |
| 后 | {"character":"mage","encounter":"cave_prism_tree","companion":"robin","n":500,"without":0.952,"with_companion":0.986,"uplift":0.034,"ci95":[0.012357138643529813,0.05564286135647019]} | {"without_wilson":"95.2% [93.0, 96.8]","with_companion_wilson":"98.6% [97.1, 99.3]"} |
| 后 | {"character":"mage","encounter":"cave_prism_tree","companion":"blue_robed_mage","n":500,"without":0.952,"with_companion":0.918,"uplift":-0.034,"ci95":[-0.06500199458319211,-0.0029980054168078987]} | {"without_wilson":"95.2% [93.0, 96.8]","with_companion_wilson":"91.8% [89.1, 93.9]"} |
| 后 | {"character":"mage","encounter":"cave_prism_tree","companion":"fire_bat_dragon","n":500,"without":0.952,"with_companion":0.986,"uplift":0.034,"ci95":[0.012357138643529813,0.05564286135647019]} | {"without_wilson":"95.2% [93.0, 96.8]","with_companion_wilson":"98.6% [97.1, 99.3]"} |
| 后 | {"character":"mage","encounter":"cave_prism_tree","companion":"mina","n":500,"without":0.952,"with_companion":0.962,"uplift":0.01,"ci95":[-0.014489196014628282,0.034489196014628284]} | {"without_wilson":"95.2% [93.0, 96.8]","with_companion_wilson":"96.2% [94.1, 97.6]"} |
| 后 | {"character":"mage","encounter":"cave_prism_tree","companion":"paladin_liese","n":500,"without":0.952,"with_companion":0.962,"uplift":0.01,"ci95":[-0.015110059940598325,0.03511005994059833]} | {"without_wilson":"95.2% [93.0, 96.8]","with_companion_wilson":"96.2% [94.1, 97.6]"} |
| 后 | {"character":"mage","encounter":"cave_prism_tree","companion":"hydromancer_elio","n":500,"without":0.952,"with_companion":0.996,"uplift":0.044,"ci95":[0.02436781800359726,0.06363218199640273]} | {"without_wilson":"95.2% [93.0, 96.8]","with_companion_wilson":"99.6% [98.6, 99.9]"} |
| 后 | {"character":"mage","encounter":"cave_prism_tree","companion":"fire_bat_dragon:empowered","n":500,"without":0.952,"with_companion":1,"uplift":0.048,"ci95":[0.029243798428392025,0.06675620157160797]} | {"without_wilson":"95.2% [93.0, 96.8]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"thief","encounter":"cave_prism_tree","companion":"robin","n":500,"without":0.642,"with_companion":0.71,"uplift":0.068,"ci95":[0.012550609082639948,0.12344939091736007]} | {"without_wilson":"64.2% [59.9, 68.3]","with_companion_wilson":"71.0% [66.9, 74.8]"} |
| 后 | {"character":"thief","encounter":"cave_prism_tree","companion":"blue_robed_mage","n":500,"without":0.642,"with_companion":0.812,"uplift":0.17,"ci95":[0.12282305172122943,0.2171769482787706]} | {"without_wilson":"64.2% [59.9, 68.3]","with_companion_wilson":"81.2% [77.5, 84.4]"} |
| 后 | {"character":"thief","encounter":"cave_prism_tree","companion":"fire_bat_dragon","n":500,"without":0.642,"with_companion":0.872,"uplift":0.23,"ci95":[0.1790569228036973,0.28094307719630274]} | {"without_wilson":"64.2% [59.9, 68.3]","with_companion_wilson":"87.2% [84.0, 89.8]"} |
| 后 | {"character":"thief","encounter":"cave_prism_tree","companion":"mina","n":500,"without":0.642,"with_companion":0.67,"uplift":0.028,"ci95":[-0.032230409060134246,0.08823040906013425]} | {"without_wilson":"64.2% [59.9, 68.3]","with_companion_wilson":"67.0% [62.8, 71.0]"} |
| 后 | {"character":"thief","encounter":"cave_prism_tree","companion":"paladin_liese","n":500,"without":0.642,"with_companion":0.768,"uplift":0.126,"ci95":[0.06818870518301087,0.18381129481698913]} | {"without_wilson":"64.2% [59.9, 68.3]","with_companion_wilson":"76.8% [72.9, 80.3]"} |
| 后 | {"character":"thief","encounter":"cave_prism_tree","companion":"hydromancer_elio","n":500,"without":0.642,"with_companion":0.892,"uplift":0.25,"ci95":[0.19887589856540275,0.3011241014345973]} | {"without_wilson":"64.2% [59.9, 68.3]","with_companion_wilson":"89.2% [86.2, 91.6]"} |
| 后 | {"character":"thief","encounter":"cave_prism_tree","companion":"fire_bat_dragon:empowered","n":500,"without":0.642,"with_companion":0.91,"uplift":0.268,"ci95":[0.21960859063634952,0.3163914093636505]} | {"without_wilson":"64.2% [59.9, 68.3]","with_companion_wilson":"91.0% [88.2, 93.2]"} |
| 后 | {"character":"hero","encounter":"slime_king_battle","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"slime_king_battle","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"slime_king_battle","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"slime_king_battle","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"slime_king_battle","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"slime_king_battle","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"slime_king_battle","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"slime_king_battle","companion":"robin","n":500,"without":0.898,"with_companion":0.956,"uplift":0.058,"ci95":[0.027273380180516733,0.08872661981948327]} | {"without_wilson":"89.8% [86.8, 92.2]","with_companion_wilson":"95.6% [93.4, 97.1]"} |
| 后 | {"character":"cleric","encounter":"slime_king_battle","companion":"blue_robed_mage","n":500,"without":0.898,"with_companion":0.95,"uplift":0.052,"ci95":[0.019018475032552593,0.0849815249674474]} | {"without_wilson":"89.8% [86.8, 92.2]","with_companion_wilson":"95.0% [92.7, 96.6]"} |
| 后 | {"character":"cleric","encounter":"slime_king_battle","companion":"fire_bat_dragon","n":500,"without":0.898,"with_companion":0.964,"uplift":0.066,"ci95":[0.03489883368920414,0.09710116631079586]} | {"without_wilson":"89.8% [86.8, 92.2]","with_companion_wilson":"96.4% [94.4, 97.7]"} |
| 后 | {"character":"cleric","encounter":"slime_king_battle","companion":"mina","n":500,"without":0.898,"with_companion":0.934,"uplift":0.036,"ci95":[0.0028545536456656556,0.06914544635433434]} | {"without_wilson":"89.8% [86.8, 92.2]","with_companion_wilson":"93.4% [90.9, 95.3]"} |
| 后 | {"character":"cleric","encounter":"slime_king_battle","companion":"paladin_liese","n":500,"without":0.898,"with_companion":0.906,"uplift":0.008,"ci95":[-0.0275257263072737,0.0435257263072737]} | {"without_wilson":"89.8% [86.8, 92.2]","with_companion_wilson":"90.6% [87.7, 92.9]"} |
| 后 | {"character":"cleric","encounter":"slime_king_battle","companion":"hydromancer_elio","n":500,"without":0.898,"with_companion":0.946,"uplift":0.048,"ci95":[0.016401309177064838,0.07959869082293516]} | {"without_wilson":"89.8% [86.8, 92.2]","with_companion_wilson":"94.6% [92.3, 96.3]"} |
| 后 | {"character":"cleric","encounter":"slime_king_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.898,"with_companion":0.972,"uplift":0.074,"ci95":[0.04509528478044027,0.10290471521955973]} | {"without_wilson":"89.8% [86.8, 92.2]","with_companion_wilson":"97.2% [95.4, 98.3]"} |
| 后 | {"character":"mage","encounter":"slime_king_battle","companion":"robin","n":500,"without":0.928,"with_companion":0.962,"uplift":0.034,"ci95":[0.005052701110016291,0.06294729888998371]} | {"without_wilson":"92.8% [90.2, 94.8]","with_companion_wilson":"96.2% [94.1, 97.6]"} |
| 后 | {"character":"mage","encounter":"slime_king_battle","companion":"blue_robed_mage","n":500,"without":0.928,"with_companion":0.944,"uplift":0.016,"ci95":[-0.006152638207651884,0.038152638207651884]} | {"without_wilson":"92.8% [90.2, 94.8]","with_companion_wilson":"94.4% [92.0, 96.1]"} |
| 后 | {"character":"mage","encounter":"slime_king_battle","companion":"fire_bat_dragon","n":500,"without":0.928,"with_companion":0.99,"uplift":0.062,"ci95":[0.037470598003117785,0.08652940199688222]} | {"without_wilson":"92.8% [90.2, 94.8]","with_companion_wilson":"99.0% [97.7, 99.6]"} |
| 后 | {"character":"mage","encounter":"slime_king_battle","companion":"mina","n":500,"without":0.928,"with_companion":0.95,"uplift":0.022,"ci95":[-0.006501318944272146,0.05050131894427214]} | {"without_wilson":"92.8% [90.2, 94.8]","with_companion_wilson":"95.0% [92.7, 96.6]"} |
| 后 | {"character":"mage","encounter":"slime_king_battle","companion":"paladin_liese","n":500,"without":0.928,"with_companion":0.966,"uplift":0.038,"ci95":[0.010735632215263038,0.06526436778473696]} | {"without_wilson":"92.8% [90.2, 94.8]","with_companion_wilson":"96.6% [94.6, 97.9]"} |
| 后 | {"character":"mage","encounter":"slime_king_battle","companion":"hydromancer_elio","n":500,"without":0.928,"with_companion":0.954,"uplift":0.026,"ci95":[-0.002475376220548931,0.05447537622054893]} | {"without_wilson":"92.8% [90.2, 94.8]","with_companion_wilson":"95.4% [93.2, 96.9]"} |
| 后 | {"character":"mage","encounter":"slime_king_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.928,"with_companion":0.996,"uplift":0.068,"ci95":[0.045911398962551225,0.09008860103744878]} | {"without_wilson":"92.8% [90.2, 94.8]","with_companion_wilson":"99.6% [98.6, 99.9]"} |
| 后 | {"character":"thief","encounter":"slime_king_battle","companion":"robin","n":500,"without":0.516,"with_companion":0.64,"uplift":0.124,"ci95":[0.06470949278939687,0.18329050721060314]} | {"without_wilson":"51.6% [47.2, 56.0]","with_companion_wilson":"64.0% [59.7, 68.1]"} |
| 后 | {"character":"thief","encounter":"slime_king_battle","companion":"blue_robed_mage","n":500,"without":0.516,"with_companion":0.5,"uplift":-0.016,"ci95":[-0.07626414385743599,0.04426414385743598]} | {"without_wilson":"51.6% [47.2, 56.0]","with_companion_wilson":"50.0% [45.6, 54.4]"} |
| 后 | {"character":"thief","encounter":"slime_king_battle","companion":"fire_bat_dragon","n":500,"without":0.516,"with_companion":0.76,"uplift":0.244,"ci95":[0.1857680936716884,0.3022319063283116]} | {"without_wilson":"51.6% [47.2, 56.0]","with_companion_wilson":"76.0% [72.1, 79.5]"} |
| 后 | {"character":"thief","encounter":"slime_king_battle","companion":"mina","n":500,"without":0.516,"with_companion":0.61,"uplift":0.094,"ci95":[0.04156278260303401,0.146437217396966]} | {"without_wilson":"51.6% [47.2, 56.0]","with_companion_wilson":"61.0% [56.7, 65.2]"} |
| 后 | {"character":"thief","encounter":"slime_king_battle","companion":"paladin_liese","n":500,"without":0.516,"with_companion":0.584,"uplift":0.068,"ci95":[0.0087905717305767,0.1272094282694233]} | {"without_wilson":"51.6% [47.2, 56.0]","with_companion_wilson":"58.4% [54.0, 62.6]"} |
| 后 | {"character":"thief","encounter":"slime_king_battle","companion":"hydromancer_elio","n":500,"without":0.516,"with_companion":0.646,"uplift":0.13,"ci95":[0.06964930545001716,0.19035069454998285]} | {"without_wilson":"51.6% [47.2, 56.0]","with_companion_wilson":"64.6% [60.3, 68.7]"} |
| 后 | {"character":"thief","encounter":"slime_king_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.516,"with_companion":0.906,"uplift":0.39,"ci95":[0.3380987557151408,0.4419012442848592]} | {"without_wilson":"51.6% [47.2, 56.0]","with_companion_wilson":"90.6% [87.7, 92.9]"} |
| 后 | {"character":"hero","encounter":"frost_wolf_battle","companion":"robin","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"frost_wolf_battle","companion":"blue_robed_mage","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"frost_wolf_battle","companion":"mina","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"frost_wolf_battle","companion":"paladin_liese","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"frost_wolf_battle","companion":"hydromancer_elio","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"frost_wolf_battle","companion":"fire_bat_dragon:empowered","n":500,"without":1,"with_companion":1,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"100.0% [99.2, 100.0]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"robin","n":500,"without":0.924,"with_companion":0.93,"uplift":0.006,"ci95":[-0.025631321277675756,0.03763132127767575]} | {"without_wilson":"92.4% [89.7, 94.4]","with_companion_wilson":"93.0% [90.4, 94.9]"} |
| 后 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"blue_robed_mage","n":500,"without":0.924,"with_companion":0.946,"uplift":0.022,"ci95":[-0.007562035774253378,0.051562035774253376]} | {"without_wilson":"92.4% [89.7, 94.4]","with_companion_wilson":"94.6% [92.3, 96.3]"} |
| 后 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","n":500,"without":0.924,"with_companion":0.968,"uplift":0.044,"ci95":[0.017668147468979118,0.07033185253102088]} | {"without_wilson":"92.4% [89.7, 94.4]","with_companion_wilson":"96.8% [94.9, 98.0]"} |
| 后 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"mina","n":500,"without":0.924,"with_companion":0.918,"uplift":-0.006,"ci95":[-0.038114402914410504,0.026114402914410507]} | {"without_wilson":"92.4% [89.7, 94.4]","with_companion_wilson":"91.8% [89.1, 93.9]"} |
| 后 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"paladin_liese","n":500,"without":0.924,"with_companion":0.932,"uplift":0.008,"ci95":[-0.02434990739115698,0.04034990739115698]} | {"without_wilson":"92.4% [89.7, 94.4]","with_companion_wilson":"93.2% [90.6, 95.1]"} |
| 后 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"hydromancer_elio","n":500,"without":0.924,"with_companion":0.936,"uplift":0.012,"ci95":[-0.018376357012167555,0.042376357012167555]} | {"without_wilson":"92.4% [89.7, 94.4]","with_companion_wilson":"93.6% [91.1, 95.4]"} |
| 后 | {"character":"cleric","encounter":"frost_wolf_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.924,"with_companion":0.984,"uplift":0.06,"ci95":[0.03391253189778724,0.08608746810221275]} | {"without_wilson":"92.4% [89.7, 94.4]","with_companion_wilson":"98.4% [96.9, 99.2]"} |
| 后 | {"character":"mage","encounter":"frost_wolf_battle","companion":"robin","n":500,"without":0.348,"with_companion":0.54,"uplift":0.192,"ci95":[0.13280617656659327,0.25119382343340674]} | {"without_wilson":"34.8% [30.8, 39.1]","with_companion_wilson":"54.0% [49.6, 58.3]"} |
| 后 | {"character":"mage","encounter":"frost_wolf_battle","companion":"blue_robed_mage","n":500,"without":0.348,"with_companion":0.694,"uplift":0.346,"ci95":[0.29557457510589025,0.3964254248941097]} | {"without_wilson":"34.8% [30.8, 39.1]","with_companion_wilson":"69.4% [65.2, 73.3]"} |
| 后 | {"character":"mage","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","n":500,"without":0.348,"with_companion":0.876,"uplift":0.528,"ci95":[0.47796294387985705,0.578037056120143]} | {"without_wilson":"34.8% [30.8, 39.1]","with_companion_wilson":"87.6% [84.4, 90.2]"} |
| 后 | {"character":"mage","encounter":"frost_wolf_battle","companion":"mina","n":500,"without":0.348,"with_companion":0.384,"uplift":0.036,"ci95":[-0.019679941492149022,0.09167994149214902]} | {"without_wilson":"34.8% [30.8, 39.1]","with_companion_wilson":"38.4% [34.2, 42.7]"} |
| 后 | {"character":"mage","encounter":"frost_wolf_battle","companion":"paladin_liese","n":500,"without":0.348,"with_companion":0.522,"uplift":0.174,"ci95":[0.11529014792847352,0.23270985207152645]} | {"without_wilson":"34.8% [30.8, 39.1]","with_companion_wilson":"52.2% [47.8, 56.5]"} |
| 后 | {"character":"mage","encounter":"frost_wolf_battle","companion":"hydromancer_elio","n":500,"without":0.348,"with_companion":0.644,"uplift":0.296,"ci95":[0.23965482890778642,0.3523451710922136]} | {"without_wilson":"34.8% [30.8, 39.1]","with_companion_wilson":"64.4% [60.1, 68.5]"} |
| 后 | {"character":"mage","encounter":"frost_wolf_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.348,"with_companion":0.93,"uplift":0.582,"ci95":[0.5356315470383136,0.6283684529616863]} | {"without_wilson":"34.8% [30.8, 39.1]","with_companion_wilson":"93.0% [90.4, 94.9]"} |
| 后 | {"character":"thief","encounter":"frost_wolf_battle","companion":"robin","n":500,"without":0.298,"with_companion":0.362,"uplift":0.064,"ci95":[0.010491691383655528,0.11750830861634448]} | {"without_wilson":"29.8% [26.0, 34.0]","with_companion_wilson":"36.2% [32.1, 40.5]"} |
| 后 | {"character":"thief","encounter":"frost_wolf_battle","companion":"blue_robed_mage","n":500,"without":0.298,"with_companion":0.39,"uplift":0.092,"ci95":[0.04941717730378181,0.13458282269621819]} | {"without_wilson":"29.8% [26.0, 34.0]","with_companion_wilson":"39.0% [34.8, 43.3]"} |
| 后 | {"character":"thief","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","n":500,"without":0.298,"with_companion":0.682,"uplift":0.384,"ci95":[0.3287475563811726,0.4392524436188274]} | {"without_wilson":"29.8% [26.0, 34.0]","with_companion_wilson":"68.2% [64.0, 72.1]"} |
| 后 | {"character":"thief","encounter":"frost_wolf_battle","companion":"mina","n":500,"without":0.298,"with_companion":0.286,"uplift":-0.012,"ci95":[-0.050432044745585075,0.02643204474558507]} | {"without_wilson":"29.8% [26.0, 34.0]","with_companion_wilson":"28.6% [24.8, 32.7]"} |
| 后 | {"character":"thief","encounter":"frost_wolf_battle","companion":"paladin_liese","n":500,"without":0.298,"with_companion":0.57,"uplift":0.272,"ci95":[0.21664510084083033,0.3273548991591697]} | {"without_wilson":"29.8% [26.0, 34.0]","with_companion_wilson":"57.0% [52.6, 61.3]"} |
| 后 | {"character":"thief","encounter":"frost_wolf_battle","companion":"hydromancer_elio","n":500,"without":0.298,"with_companion":0.36,"uplift":0.062,"ci95":[0.008043807393022233,0.11595619260697776]} | {"without_wilson":"29.8% [26.0, 34.0]","with_companion_wilson":"36.0% [31.9, 40.3]"} |
| 后 | {"character":"thief","encounter":"frost_wolf_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.298,"with_companion":0.71,"uplift":0.412,"ci95":[0.35775209709916633,0.4662479029008336]} | {"without_wilson":"29.8% [26.0, 34.0]","with_companion_wilson":"71.0% [66.9, 74.8]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","companion":"robin","n":500,"without":0.846,"with_companion":0.87,"uplift":0.024,"ci95":[-0.01928999103080172,0.06728999103080172]} | {"without_wilson":"84.6% [81.2, 87.5]","with_companion_wilson":"87.0% [83.8, 89.7]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","companion":"blue_robed_mage","n":500,"without":0.846,"with_companion":0.902,"uplift":0.056,"ci95":[0.014764784822418074,0.09723521517758194]} | {"without_wilson":"84.6% [81.2, 87.5]","with_companion_wilson":"90.2% [87.3, 92.5]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","n":500,"without":0.846,"with_companion":0.876,"uplift":0.03,"ci95":[-0.011628766838052189,0.0716287668380522]} | {"without_wilson":"84.6% [81.2, 87.5]","with_companion_wilson":"87.6% [84.4, 90.2]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","companion":"mina","n":500,"without":0.846,"with_companion":0.882,"uplift":0.036,"ci95":[-0.006507547046516612,0.07850754704651661]} | {"without_wilson":"84.6% [81.2, 87.5]","with_companion_wilson":"88.2% [85.1, 90.7]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","companion":"paladin_liese","n":500,"without":0.846,"with_companion":0.912,"uplift":0.066,"ci95":[0.027790148307894925,0.10420985169210509]} | {"without_wilson":"84.6% [81.2, 87.5]","with_companion_wilson":"91.2% [88.4, 93.4]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","companion":"hydromancer_elio","n":500,"without":0.846,"with_companion":0.91,"uplift":0.064,"ci95":[0.025164629720195286,0.10283537027980472]} | {"without_wilson":"84.6% [81.2, 87.5]","with_companion_wilson":"91.0% [88.2, 93.2]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","companion":"fire_bat_dragon:empowered","n":500,"without":0.846,"with_companion":0.876,"uplift":0.03,"ci95":[-0.011628766838052189,0.0716287668380522]} | {"without_wilson":"84.6% [81.2, 87.5]","with_companion_wilson":"87.6% [84.4, 90.2]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"robin","n":500,"without":0.78,"with_companion":0.804,"uplift":0.024,"ci95":[-0.026816279530586067,0.07481627953058606]} | {"without_wilson":"78.0% [74.2, 81.4]","with_companion_wilson":"80.4% [76.7, 83.6]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"blue_robed_mage","n":500,"without":0.78,"with_companion":0.792,"uplift":0.012,"ci95":[-0.0369985073920962,0.06099850739209621]} | {"without_wilson":"78.0% [74.2, 81.4]","with_companion_wilson":"79.2% [75.4, 82.5]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","n":500,"without":0.78,"with_companion":0.782,"uplift":0.002,"ci95":[-0.049311689175978064,0.05331168917597807]} | {"without_wilson":"78.0% [74.2, 81.4]","with_companion_wilson":"78.2% [74.4, 81.6]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"mina","n":500,"without":0.78,"with_companion":0.836,"uplift":0.056,"ci95":[0.00983221454707564,0.10216778545292436]} | {"without_wilson":"78.0% [74.2, 81.4]","with_companion_wilson":"83.6% [80.1, 86.6]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"paladin_liese","n":500,"without":0.78,"with_companion":0.67,"uplift":-0.11,"ci95":[-0.16506793472493533,-0.05493206527506467]} | {"without_wilson":"78.0% [74.2, 81.4]","with_companion_wilson":"67.0% [62.8, 71.0]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"hydromancer_elio","n":500,"without":0.78,"with_companion":0.908,"uplift":0.128,"ci95":[0.08363915442148469,0.17236084557851533]} | {"without_wilson":"78.0% [74.2, 81.4]","with_companion_wilson":"90.8% [87.9, 93.0]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","companion":"fire_bat_dragon:empowered","n":500,"without":0.78,"with_companion":0.782,"uplift":0.002,"ci95":[-0.049311689175978064,0.05331168917597807]} | {"without_wilson":"78.0% [74.2, 81.4]","with_companion_wilson":"78.2% [74.4, 81.6]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","companion":"robin","n":500,"without":0.106,"with_companion":0.118,"uplift":0.012,"ci95":[-0.025622244560519553,0.04962224456051956]} | {"without_wilson":"10.6% [8.2, 13.6]","with_companion_wilson":"11.8% [9.3, 14.9]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","companion":"blue_robed_mage","n":500,"without":0.106,"with_companion":0.246,"uplift":0.14,"ci95":[0.09880812189711077,0.18119187810288925]} | {"without_wilson":"10.6% [8.2, 13.6]","with_companion_wilson":"24.6% [21.0, 28.6]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","n":500,"without":0.106,"with_companion":0.076,"uplift":-0.03,"ci95":[-0.0665051664062595,0.006505166406259498]} | {"without_wilson":"10.6% [8.2, 13.6]","with_companion_wilson":"7.6% [5.6, 10.3]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","companion":"mina","n":500,"without":0.106,"with_companion":0.102,"uplift":-0.004,"ci95":[-0.03996166224053338,0.03196166224053339]} | {"without_wilson":"10.6% [8.2, 13.6]","with_companion_wilson":"10.2% [7.8, 13.2]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","companion":"paladin_liese","n":500,"without":0.106,"with_companion":0.116,"uplift":0.01,"ci95":[-0.028636226471952242,0.048636226471952246]} | {"without_wilson":"10.6% [8.2, 13.6]","with_companion_wilson":"11.6% [9.1, 14.7]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","companion":"hydromancer_elio","n":500,"without":0.106,"with_companion":0.208,"uplift":0.102,"ci95":[0.05729513407609246,0.14670486592390752]} | {"without_wilson":"10.6% [8.2, 13.6]","with_companion_wilson":"20.8% [17.5, 24.6]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","companion":"fire_bat_dragon:empowered","n":500,"without":0.106,"with_companion":0.076,"uplift":-0.03,"ci95":[-0.0665051664062595,0.006505166406259498]} | {"without_wilson":"10.6% [8.2, 13.6]","with_companion_wilson":"7.6% [5.6, 10.3]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","companion":"robin","n":500,"without":0.134,"with_companion":0.212,"uplift":0.078,"ci95":[0.03191132304473285,0.12408867695526715]} | {"without_wilson":"13.4% [10.7, 16.7]","with_companion_wilson":"21.2% [17.8, 25.0]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","companion":"blue_robed_mage","n":500,"without":0.134,"with_companion":0.238,"uplift":0.104,"ci95":[0.060553793554453825,0.14744620644554618]} | {"without_wilson":"13.4% [10.7, 16.7]","with_companion_wilson":"23.8% [20.3, 27.7]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","n":500,"without":0.134,"with_companion":0.148,"uplift":0.014,"ci95":[-0.029145701941120206,0.0571457019411202]} | {"without_wilson":"13.4% [10.7, 16.7]","with_companion_wilson":"14.8% [12.0, 18.2]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","companion":"mina","n":500,"without":0.134,"with_companion":0.196,"uplift":0.062,"ci95":[0.01776602359568978,0.10623397640431022]} | {"without_wilson":"13.4% [10.7, 16.7]","with_companion_wilson":"19.6% [16.4, 23.3]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","companion":"paladin_liese","n":500,"without":0.134,"with_companion":0.246,"uplift":0.112,"ci95":[0.063985511338317,0.160014488661683]} | {"without_wilson":"13.4% [10.7, 16.7]","with_companion_wilson":"24.6% [21.0, 28.6]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","companion":"hydromancer_elio","n":500,"without":0.134,"with_companion":0.47,"uplift":0.336,"ci95":[0.2819762182850778,0.39002378171492225]} | {"without_wilson":"13.4% [10.7, 16.7]","with_companion_wilson":"47.0% [42.7, 51.4]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","companion":"fire_bat_dragon:empowered","n":500,"without":0.134,"with_companion":0.148,"uplift":0.014,"ci95":[-0.029145701941120206,0.0571457019411202]} | {"without_wilson":"13.4% [10.7, 16.7]","with_companion_wilson":"14.8% [12.0, 18.2]"} |
| 后 | {"character":"hero","encounter":"draco_battle","companion":"robin","n":500,"without":0.198,"with_companion":0.338,"uplift":0.14,"ci95":[0.08531787174678916,0.19468212825321085]} | {"without_wilson":"19.8% [16.5, 23.5]","with_companion_wilson":"33.8% [29.8, 38.1]"} |
| 后 | {"character":"hero","encounter":"draco_battle","companion":"blue_robed_mage","n":500,"without":0.198,"with_companion":0.266,"uplift":0.068,"ci95":[0.02096392801971375,0.11503607198028626]} | {"without_wilson":"19.8% [16.5, 23.5]","with_companion_wilson":"26.6% [22.9, 30.6]"} |
| 后 | {"character":"hero","encounter":"draco_battle","companion":"fire_bat_dragon","n":500,"without":0.198,"with_companion":0.856,"uplift":0.658,"ci95":[0.611155818398655,0.7048441816013451]} | {"without_wilson":"19.8% [16.5, 23.5]","with_companion_wilson":"85.6% [82.3, 88.4]"} |
| 后 | {"character":"hero","encounter":"draco_battle","companion":"mina","n":500,"without":0.198,"with_companion":0.274,"uplift":0.076,"ci95":[0.025579155501718936,0.12642084449828106]} | {"without_wilson":"19.8% [16.5, 23.5]","with_companion_wilson":"27.4% [23.7, 31.5]"} |
| 后 | {"character":"hero","encounter":"draco_battle","companion":"paladin_liese","n":500,"without":0.198,"with_companion":0.51,"uplift":0.312,"ci95":[0.25858154586958393,0.36541845413041607]} | {"without_wilson":"19.8% [16.5, 23.5]","with_companion_wilson":"51.0% [46.6, 55.4]"} |
| 后 | {"character":"hero","encounter":"draco_battle","companion":"hydromancer_elio","n":500,"without":0.198,"with_companion":0.882,"uplift":0.684,"ci95":[0.6375595455187523,0.7304404544812478]} | {"without_wilson":"19.8% [16.5, 23.5]","with_companion_wilson":"88.2% [85.1, 90.7]"} |
| 后 | {"character":"hero","encounter":"draco_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.198,"with_companion":0.888,"uplift":0.69,"ci95":[0.6454414069293827,0.7345585930706172]} | {"without_wilson":"19.8% [16.5, 23.5]","with_companion_wilson":"88.8% [85.7, 91.3]"} |
| 后 | {"character":"cleric","encounter":"draco_battle","companion":"robin","n":500,"without":0.96,"with_companion":0.996,"uplift":0.036,"ci95":[0.018738293658747893,0.0532617063412521]} | {"without_wilson":"96.0% [93.9, 97.4]","with_companion_wilson":"99.6% [98.6, 99.9]"} |
| 后 | {"character":"cleric","encounter":"draco_battle","companion":"blue_robed_mage","n":500,"without":0.96,"with_companion":0.984,"uplift":0.024,"ci95":[0.005716021095802527,0.042283978904197474]} | {"without_wilson":"96.0% [93.9, 97.4]","with_companion_wilson":"98.4% [96.9, 99.2]"} |
| 后 | {"character":"cleric","encounter":"draco_battle","companion":"fire_bat_dragon","n":500,"without":0.96,"with_companion":0.994,"uplift":0.034,"ci95":[0.015419475449138412,0.052580524550861596]} | {"without_wilson":"96.0% [93.9, 97.4]","with_companion_wilson":"99.4% [98.3, 99.8]"} |
| 后 | {"character":"cleric","encounter":"draco_battle","companion":"mina","n":500,"without":0.96,"with_companion":0.978,"uplift":0.018,"ci95":[-0.0030718839163366464,0.03907188391633665]} | {"without_wilson":"96.0% [93.9, 97.4]","with_companion_wilson":"97.8% [96.1, 98.8]"} |
| 后 | {"character":"cleric","encounter":"draco_battle","companion":"paladin_liese","n":500,"without":0.96,"with_companion":1,"uplift":0.04,"ci95":[0.022806218209348795,0.05719378179065121]} | {"without_wilson":"96.0% [93.9, 97.4]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"draco_battle","companion":"hydromancer_elio","n":500,"without":0.96,"with_companion":1,"uplift":0.04,"ci95":[0.022806218209348795,0.05719378179065121]} | {"without_wilson":"96.0% [93.9, 97.4]","with_companion_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"draco_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.96,"with_companion":0.994,"uplift":0.034,"ci95":[0.015419475449138412,0.052580524550861596]} | {"without_wilson":"96.0% [93.9, 97.4]","with_companion_wilson":"99.4% [98.3, 99.8]"} |
| 后 | {"character":"mage","encounter":"draco_battle","companion":"robin","n":500,"without":0.138,"with_companion":0.148,"uplift":0.01,"ci95":[-0.030957591831763186,0.05095759183176319]} | {"without_wilson":"13.8% [11.1, 17.1]","with_companion_wilson":"14.8% [12.0, 18.2]"} |
| 后 | {"character":"mage","encounter":"draco_battle","companion":"blue_robed_mage","n":500,"without":0.138,"with_companion":0.18,"uplift":0.042,"ci95":[0.0077654612637329465,0.07623453873626707]} | {"without_wilson":"13.8% [11.1, 17.1]","with_companion_wilson":"18.0% [14.9, 21.6]"} |
| 后 | {"character":"mage","encounter":"draco_battle","companion":"fire_bat_dragon","n":500,"without":0.138,"with_companion":0.256,"uplift":0.118,"ci95":[0.06929935288665542,0.16670064711334456]} | {"without_wilson":"13.8% [11.1, 17.1]","with_companion_wilson":"25.6% [22.0, 29.6]"} |
| 后 | {"character":"mage","encounter":"draco_battle","companion":"mina","n":500,"without":0.138,"with_companion":0.142,"uplift":0.004,"ci95":[-0.03789459371763296,0.04589459371763295]} | {"without_wilson":"13.8% [11.1, 17.1]","with_companion_wilson":"14.2% [11.4, 17.5]"} |
| 后 | {"character":"mage","encounter":"draco_battle","companion":"paladin_liese","n":500,"without":0.138,"with_companion":0.1,"uplift":-0.038,"ci95":[-0.07806979706054107,0.0020697970605410704]} | {"without_wilson":"13.8% [11.1, 17.1]","with_companion_wilson":"10.0% [7.7, 12.9]"} |
| 后 | {"character":"mage","encounter":"draco_battle","companion":"hydromancer_elio","n":500,"without":0.138,"with_companion":0.434,"uplift":0.296,"ci95":[0.24245717211768442,0.34954282788231555]} | {"without_wilson":"13.8% [11.1, 17.1]","with_companion_wilson":"43.4% [39.1, 47.8]"} |
| 后 | {"character":"mage","encounter":"draco_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0.138,"with_companion":0.348,"uplift":0.21,"ci95":[0.15839627174768206,0.2616037282523179]} | {"without_wilson":"13.8% [11.1, 17.1]","with_companion_wilson":"34.8% [30.8, 39.1]"} |
| 后 | {"character":"thief","encounter":"draco_battle","companion":"robin","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 后 | {"character":"thief","encounter":"draco_battle","companion":"blue_robed_mage","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 后 | {"character":"thief","encounter":"draco_battle","companion":"fire_bat_dragon","n":500,"without":0,"with_companion":0.492,"uplift":0.492,"ci95":[0.4481347906835411,0.5358652093164589]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"49.2% [44.8, 53.6]"} |
| 后 | {"character":"thief","encounter":"draco_battle","companion":"mina","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 后 | {"character":"thief","encounter":"draco_battle","companion":"paladin_liese","n":500,"without":0,"with_companion":0,"uplift":0,"ci95":[0.0,0.0]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"0.0% [0.0, 0.8]"} |
| 后 | {"character":"thief","encounter":"draco_battle","companion":"hydromancer_elio","n":500,"without":0,"with_companion":0.306,"uplift":0.306,"ci95":[0.265566042803243,0.346433957196757]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"30.6% [26.7, 34.8]"} |
| 后 | {"character":"thief","encounter":"draco_battle","companion":"fire_bat_dragon:empowered","n":500,"without":0,"with_companion":0.672,"uplift":0.672,"ci95":[0.6308066267562561,0.713193373243744]} | {"without_wilson":"0.0% [0.0, 0.8]","with_companion_wilson":"67.2% [63.0, 71.2]"} |


#### M13


| 阶段 | 原始指标 | 二项率区间补充 |
| --- | --- | --- |
| 前 | {"character":"hero","encounter":"goblin_fort_fourth","n":500,"from_level":1,"to_level":2,"before":0.078,"after":0.408,"uplift":0.33,"ci95":[0.28482369961769266,0.37517630038230737],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"7.8% [5.8, 10.5]","after_wilson":"40.8% [36.6, 45.2]"} |
| 前 | {"character":"hero","encounter":"goblin_fort_fourth","n":500,"from_level":2,"to_level":3,"before":0.408,"after":0.89,"uplift":0.482,"ci95":[0.43192756906360785,0.5320724309363921],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"40.8% [36.6, 45.2]","after_wilson":"89.0% [86.0, 91.5]"} |
| 前 | {"character":"cleric","encounter":"goblin_fort_fourth","n":500,"from_level":1,"to_level":2,"before":0.01,"after":0.136,"uplift":0.126,"ci95":[0.09584392109391573,0.15615607890608427],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"1.0% [0.4, 2.3]","after_wilson":"13.6% [10.9, 16.9]"} |
| 前 | {"character":"cleric","encounter":"goblin_fort_fourth","n":500,"from_level":2,"to_level":3,"before":0.136,"after":0.202,"uplift":0.066,"ci95":[0.019435381369365512,0.1125646186306345],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"13.6% [10.9, 16.9]","after_wilson":"20.2% [16.9, 23.9]"} |
| 前 | {"character":"mage","encounter":"goblin_fort_fourth","n":500,"from_level":1,"to_level":2,"before":0.002,"after":0.046,"uplift":0.044,"ci95":[0.026004617470451772,0.061995382529548226],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"0.2% [0.0, 1.1]","after_wilson":"4.6% [3.1, 6.8]"} |
| 前 | {"character":"mage","encounter":"goblin_fort_fourth","n":500,"from_level":2,"to_level":3,"before":0.046,"after":0.1,"uplift":0.054,"ci95":[0.02995750695656777,0.07804249304343222],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"4.6% [3.1, 6.8]","after_wilson":"10.0% [7.7, 12.9]"} |
| 前 | {"character":"thief","encounter":"goblin_fort_fourth","n":500,"from_level":1,"to_level":2,"before":0,"after":0,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"0.0% [0.0, 0.8]","after_wilson":"0.0% [0.0, 0.8]"} |
| 前 | {"character":"thief","encounter":"goblin_fort_fourth","n":500,"from_level":2,"to_level":3,"before":0,"after":0.018,"uplift":0.018,"ci95":[0.006334649426270291,0.029665350573729706],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"0.0% [0.0, 0.8]","after_wilson":"1.8% [0.9, 3.4]"} |
| 前 | {"character":"hero","encounter":"cave_prism_tree","n":500,"from_level":4,"to_level":5,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"cave_prism_tree","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"cave_prism_tree","n":500,"from_level":4,"to_level":5,"before":0.974,"after":1,"uplift":0.026,"ci95":[0.012037218208727121,0.039962781791272876],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"97.4% [95.6, 98.5]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"cave_prism_tree","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"cave_prism_tree","n":500,"from_level":4,"to_level":5,"before":0.886,"after":0.962,"uplift":0.076,"ci95":[0.04906688614281504,0.10293311385718495],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"88.6% [85.5, 91.1]","after_wilson":"96.2% [94.1, 97.6]"} |
| 前 | {"character":"mage","encounter":"cave_prism_tree","n":500,"from_level":5,"to_level":6,"before":0.962,"after":0.998,"uplift":0.036,"ci95":[0.018738293658747893,0.0532617063412521],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"96.2% [94.1, 97.6]","after_wilson":"99.8% [98.9, 100.0]"} |
| 前 | {"character":"thief","encounter":"cave_prism_tree","n":500,"from_level":3,"to_level":4,"before":0.834,"after":0.956,"uplift":0.122,"ci95":[0.08744315404431693,0.15655684595568306],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"83.4% [79.9, 86.4]","after_wilson":"95.6% [93.4, 97.1]"} |
| 前 | {"character":"thief","encounter":"cave_prism_tree","n":500,"from_level":4,"to_level":5,"before":0.956,"after":0.982,"uplift":0.026,"ci95":[0.005738706931846943,0.046261293068153055],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"95.6% [93.4, 97.1]","after_wilson":"98.2% [96.6, 99.1]"} |
| 前 | {"character":"hero","encounter":"slime_king_battle","n":500,"from_level":4,"to_level":5,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"slime_king_battle","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"slime_king_battle","n":500,"from_level":4,"to_level":5,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"slime_king_battle","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"slime_king_battle","n":500,"from_level":4,"to_level":5,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"slime_king_battle","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"slime_king_battle","n":500,"from_level":4,"to_level":5,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"slime_king_battle","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"frost_wolf_battle","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"frost_wolf_battle","n":500,"from_level":6,"to_level":7,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"frost_wolf_battle","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"frost_wolf_battle","n":500,"from_level":6,"to_level":7,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"frost_wolf_battle","n":500,"from_level":5,"to_level":6,"before":0.996,"after":1,"uplift":0.004,"ci95":[-0.001538159551912971,0.009538159551912971],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"99.6% [98.6, 99.9]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"frost_wolf_battle","n":500,"from_level":6,"to_level":7,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"frost_wolf_battle","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"thief","encounter":"frost_wolf_battle","n":500,"from_level":6,"to_level":7,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","n":500,"from_level":6,"to_level":7,"before":0.984,"after":1,"uplift":0.016,"ci95":[0.0049906079083149694,0.02700939209168503],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"98.4% [96.9, 99.2]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"hero","encounter":"dragon_valley_loc","n":500,"from_level":7,"to_level":8,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","n":500,"from_level":6,"to_level":7,"before":0.99,"after":1,"uplift":0.01,"ci95":[0.001269816025738696,0.018730183974261305],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"99.0% [97.7, 99.6]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"cleric","encounter":"dragon_valley_loc","n":500,"from_level":7,"to_level":8,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","n":500,"from_level":6,"to_level":7,"before":0.65,"after":0.764,"uplift":0.114,"ci95":[0.06849227055016524,0.15950772944983477],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"65.0% [60.7, 69.1]","after_wilson":"76.4% [72.5, 79.9]"} |
| 前 | {"character":"mage","encounter":"dragon_valley_loc","n":500,"from_level":7,"to_level":8,"before":0.764,"after":0.846,"uplift":0.082,"ci95":[0.0440294523587511,0.1199705476412489],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"76.4% [72.5, 79.9]","after_wilson":"84.6% [81.2, 87.5]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","n":500,"from_level":6,"to_level":7,"before":0.83,"after":0.912,"uplift":0.082,"ci95":[0.041669753027762366,0.12233024697223764],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"83.0% [79.5, 86.0]","after_wilson":"91.2% [88.4, 93.4]"} |
| 前 | {"character":"thief","encounter":"dragon_valley_loc","n":500,"from_level":7,"to_level":8,"before":0.912,"after":0.976,"uplift":0.064,"ci95":[0.03571723063620234,0.09228276936379766],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"91.2% [88.4, 93.4]","after_wilson":"97.6% [95.9, 98.6]"} |
| 前 | {"character":"hero","encounter":"draco_battle","n":500,"from_level":7,"to_level":8,"before":0.922,"after":0.996,"uplift":0.074,"ci95":[0.050370927590659594,0.0976290724093404],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"92.2% [89.5, 94.2]","after_wilson":"99.6% [98.6, 99.9]"} |
| 前 | {"character":"cleric","encounter":"draco_battle","n":500,"from_level":7,"to_level":8,"before":0.782,"after":0.968,"uplift":0.186,"ci95":[0.14565753798684858,0.22634246201315142],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"78.2% [74.4, 81.6]","after_wilson":"96.8% [94.9, 98.0]"} |
| 前 | {"character":"mage","encounter":"draco_battle","n":500,"from_level":7,"to_level":8,"before":0.222,"after":0.384,"uplift":0.162,"ci95":[0.11797537012909091,0.20602462987090908],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"22.2% [18.8, 26.0]","after_wilson":"38.4% [34.2, 42.7]"} |
| 前 | {"character":"thief","encounter":"draco_battle","n":500,"from_level":7,"to_level":8,"before":0.902,"after":0.912,"uplift":0.01,"ci95":[-0.024865577537077854,0.04486557753707786],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"90.2% [87.3, 92.5]","after_wilson":"91.2% [88.4, 93.4]"} |
| 后 | {"character":"hero","encounter":"goblin_fort_fourth","n":500,"from_level":1,"to_level":2,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"goblin_fort_fourth","n":500,"from_level":2,"to_level":3,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"goblin_fort_fourth","n":500,"from_level":1,"to_level":2,"before":0.9,"after":1,"uplift":0.1,"ci95":[0.07367750491509231,0.1263224950849077],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"90.0% [87.1, 92.3]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"goblin_fort_fourth","n":500,"from_level":2,"to_level":3,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"mage","encounter":"goblin_fort_fourth","n":500,"from_level":1,"to_level":2,"before":0.128,"after":0.994,"uplift":0.866,"ci95":[0.8361106036724452,0.8958893963275548],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"12.8% [10.2, 16.0]","after_wilson":"99.4% [98.3, 99.8]"} |
| 后 | {"character":"mage","encounter":"goblin_fort_fourth","n":500,"from_level":2,"to_level":3,"before":0.994,"after":0.938,"uplift":-0.056,"ci95":[-0.07834640482083938,-0.033653595179160625],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"99.4% [98.3, 99.8]","after_wilson":"93.8% [91.3, 95.6]"} |
| 后 | {"character":"thief","encounter":"goblin_fort_fourth","n":500,"from_level":1,"to_level":2,"before":0.886,"after":0.99,"uplift":0.104,"ci95":[0.07500752449216962,0.13299247550783036],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"88.6% [85.5, 91.1]","after_wilson":"99.0% [97.7, 99.6]"} |
| 后 | {"character":"hero","encounter":"cave_prism_tree","n":500,"from_level":4,"to_level":5,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"cave_prism_tree","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"cave_prism_tree","n":500,"from_level":4,"to_level":5,"before":0.97,"after":0.992,"uplift":0.022,"ci95":[0.005936806557625775,0.03806319344237422],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"97.0% [95.1, 98.2]","after_wilson":"99.2% [98.0, 99.7]"} |
| 后 | {"character":"cleric","encounter":"cave_prism_tree","n":500,"from_level":5,"to_level":6,"before":0.992,"after":0.996,"uplift":0.004,"ci95":[-0.0056052063370629936,0.013605206337062994],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"99.2% [98.0, 99.7]","after_wilson":"99.6% [98.6, 99.9]"} |
| 后 | {"character":"mage","encounter":"cave_prism_tree","n":500,"from_level":4,"to_level":5,"before":0.928,"after":0.968,"uplift":0.04,"ci95":[0.021099870111037883,0.05890012988896212],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"92.8% [90.2, 94.8]","after_wilson":"96.8% [94.9, 98.0]"} |
| 后 | {"character":"mage","encounter":"cave_prism_tree","n":500,"from_level":5,"to_level":6,"before":0.968,"after":0.99,"uplift":0.022,"ci95":[0.004122221583142818,0.039877778416857176],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"96.8% [94.9, 98.0]","after_wilson":"99.0% [97.7, 99.6]"} |
| 后 | {"character":"thief","encounter":"cave_prism_tree","n":500,"from_level":4,"to_level":5,"before":0.498,"after":0.71,"uplift":0.212,"ci95":[0.1606088533002207,0.2633911466997793],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"49.8% [45.4, 54.2]","after_wilson":"71.0% [66.9, 74.8]"} |
| 后 | {"character":"thief","encounter":"cave_prism_tree","n":500,"from_level":5,"to_level":6,"before":0.71,"after":0.826,"uplift":0.116,"ci95":[0.07104201403750823,0.16095798596249178],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"71.0% [66.9, 74.8]","after_wilson":"82.6% [79.0, 85.7]"} |
| 后 | {"character":"hero","encounter":"slime_king_battle","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"slime_king_battle","n":500,"from_level":6,"to_level":7,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"slime_king_battle","n":500,"from_level":5,"to_level":6,"before":0.888,"after":0.972,"uplift":0.084,"ci95":[0.055039406553982866,0.11296059344601714],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"88.8% [85.7, 91.3]","after_wilson":"97.2% [95.4, 98.3]"} |
| 后 | {"character":"cleric","encounter":"slime_king_battle","n":500,"from_level":6,"to_level":7,"before":0.972,"after":1,"uplift":0.028,"ci95":[0.013525020855196893,0.04247497914480311],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"97.2% [95.4, 98.3]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"mage","encounter":"slime_king_battle","n":500,"from_level":5,"to_level":6,"before":0.634,"after":0.934,"uplift":0.3,"ci95":[0.2550886154195859,0.3449113845804141],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"63.4% [59.1, 67.5]","after_wilson":"93.4% [90.9, 95.3]"} |
| 后 | {"character":"mage","encounter":"slime_king_battle","n":500,"from_level":6,"to_level":7,"before":0.934,"after":0.976,"uplift":0.042,"ci95":[0.017773769263225807,0.0662262307367742],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"93.4% [90.9, 95.3]","after_wilson":"97.6% [95.9, 98.6]"} |
| 后 | {"character":"thief","encounter":"slime_king_battle","n":500,"from_level":4,"to_level":5,"before":0.19,"after":0.736,"uplift":0.546,"ci95":[0.4969992929910726,0.5950007070089275],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"19.0% [15.8, 22.7]","after_wilson":"73.6% [69.6, 77.3]"} |
| 后 | {"character":"thief","encounter":"slime_king_battle","n":500,"from_level":5,"to_level":6,"before":0.736,"after":0.868,"uplift":0.132,"ci95":[0.08669810991038694,0.17730189008961306],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"73.6% [69.6, 77.3]","after_wilson":"86.8% [83.6, 89.5]"} |
| 后 | {"character":"hero","encounter":"frost_wolf_battle","n":500,"from_level":5,"to_level":6,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"hero","encounter":"frost_wolf_battle","n":500,"from_level":6,"to_level":7,"before":1,"after":1,"uplift":0,"ci95":[0.0,0.0],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"100.0% [99.2, 100.0]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"cleric","encounter":"frost_wolf_battle","n":500,"from_level":5,"to_level":6,"before":0.956,"after":0.988,"uplift":0.032,"ci95":[0.011427249105704963,0.05257275089429504],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"95.6% [93.4, 97.1]","after_wilson":"98.8% [97.4, 99.4]"} |
| 后 | {"character":"cleric","encounter":"frost_wolf_battle","n":500,"from_level":6,"to_level":7,"before":0.988,"after":1,"uplift":0.012,"ci95":[0.0024462275337606386,0.021553772466239362],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"98.8% [97.4, 99.4]","after_wilson":"100.0% [99.2, 100.0]"} |
| 后 | {"character":"mage","encounter":"frost_wolf_battle","n":500,"from_level":5,"to_level":6,"before":0.408,"after":0.52,"uplift":0.112,"ci95":[0.08167437343676301,0.142325626563237],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"40.8% [36.6, 45.2]","after_wilson":"52.0% [47.6, 56.3]"} |
| 后 | {"character":"mage","encounter":"frost_wolf_battle","n":500,"from_level":6,"to_level":7,"before":0.52,"after":0.86,"uplift":0.34,"ci95":[0.29626978683923244,0.3837302131607676],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"52.0% [47.6, 56.3]","after_wilson":"86.0% [82.7, 88.8]"} |
| 后 | {"character":"thief","encounter":"frost_wolf_battle","n":500,"from_level":5,"to_level":6,"before":0.544,"after":0.872,"uplift":0.328,"ci95":[0.2786445612940203,0.3773554387059797],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"54.4% [50.0, 58.7]","after_wilson":"87.2% [84.0, 89.8]"} |
| 后 | {"character":"thief","encounter":"frost_wolf_battle","n":500,"from_level":6,"to_level":7,"before":0.872,"after":0.98,"uplift":0.108,"ci95":[0.07756287806010614,0.13843712193989385],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"87.2% [84.0, 89.8]","after_wilson":"98.0% [96.4, 98.9]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","n":500,"from_level":5,"to_level":6,"before":0.768,"after":0.894,"uplift":0.126,"ci95":[0.08390924114771126,0.16809075885228875],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"76.8% [72.9, 80.3]","after_wilson":"89.4% [86.4, 91.8]"} |
| 后 | {"character":"hero","encounter":"dragon_valley_loc","n":500,"from_level":6,"to_level":7,"before":0.894,"after":0.986,"uplift":0.092,"ci95":[0.06376736003987164,0.12023263996012835],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"89.4% [86.4, 91.8]","after_wilson":"98.6% [97.1, 99.3]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","n":500,"from_level":5,"to_level":6,"before":0.74,"after":0.85,"uplift":0.11,"ci95":[0.05929929385889766,0.16070070614110235],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"74.0% [70.0, 77.7]","after_wilson":"85.0% [81.6, 87.9]"} |
| 后 | {"character":"cleric","encounter":"dragon_valley_loc","n":500,"from_level":6,"to_level":7,"before":0.85,"after":0.956,"uplift":0.106,"ci95":[0.07103916355448657,0.14096083644551344],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"85.0% [81.6, 87.9]","after_wilson":"95.6% [93.4, 97.1]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","n":500,"from_level":5,"to_level":6,"before":0.152,"after":0.264,"uplift":0.112,"ci95":[0.06765304018436237,0.15634695981563762],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"15.2% [12.3, 18.6]","after_wilson":"26.4% [22.7, 30.4]"} |
| 后 | {"character":"mage","encounter":"dragon_valley_loc","n":500,"from_level":6,"to_level":7,"before":0.264,"after":0.422,"uplift":0.158,"ci95":[0.11674873178362977,0.19925126821637024],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"26.4% [22.7, 30.4]","after_wilson":"42.2% [37.9, 46.6]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","n":500,"from_level":5,"to_level":6,"before":0.08,"after":0.136,"uplift":0.056,"ci95":[0.020808706487567753,0.09119129351243224],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"8.0% [5.9, 10.7]","after_wilson":"13.6% [10.9, 16.9]"} |
| 后 | {"character":"thief","encounter":"dragon_valley_loc","n":500,"from_level":6,"to_level":7,"before":0.136,"after":0.46,"uplift":0.324,"ci95":[0.27055503461081765,0.3774449653891824],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"13.6% [10.9, 16.9]","after_wilson":"46.0% [41.7, 50.4]"} |
| 后 | {"character":"hero","encounter":"draco_battle","n":500,"from_level":6,"to_level":7,"before":0.648,"after":0.888,"uplift":0.24,"ci95":[0.1886580125106291,0.2913419874893709],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"64.8% [60.5, 68.9]","after_wilson":"88.8% [85.7, 91.3]"} |
| 后 | {"character":"hero","encounter":"draco_battle","n":500,"from_level":7,"to_level":8,"before":0.888,"after":0.978,"uplift":0.09,"ci95":[0.0603880054633113,0.11961199453668869],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"88.8% [85.7, 91.3]","after_wilson":"97.8% [96.1, 98.8]"} |
| 后 | {"character":"cleric","encounter":"draco_battle","n":500,"from_level":6,"to_level":7,"before":0.932,"after":0.994,"uplift":0.062,"ci95":[0.0387598884518697,0.0852401115481303],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"93.2% [90.6, 95.1]","after_wilson":"99.4% [98.3, 99.8]"} |
| 后 | {"character":"cleric","encounter":"draco_battle","n":500,"from_level":7,"to_level":8,"before":0.994,"after":0.998,"uplift":0.004,"ci95":[-0.001538159551912971,0.009538159551912971],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"99.4% [98.3, 99.8]","after_wilson":"99.8% [98.9, 100.0]"} |
| 后 | {"character":"mage","encounter":"draco_battle","n":500,"from_level":6,"to_level":7,"before":0.142,"after":0.256,"uplift":0.114,"ci95":[0.07667069667709903,0.15132930332290098],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"14.2% [11.4, 17.5]","after_wilson":"25.6% [22.0, 29.6]"} |
| 后 | {"character":"mage","encounter":"draco_battle","n":500,"from_level":7,"to_level":8,"before":0.256,"after":0.346,"uplift":0.09,"ci95":[0.049801299136636216,0.13019870086336377],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"25.6% [22.0, 29.6]","after_wilson":"34.6% [30.6, 38.9]"} |
| 后 | {"character":"thief","encounter":"draco_battle","n":500,"from_level":6,"to_level":7,"before":0.946,"after":0.672,"uplift":-0.274,"ci95":[-0.31864696607788623,-0.22935303392211384],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"94.6% [92.3, 96.3]","after_wilson":"67.2% [63.0, 71.2]"} |
| 后 | {"character":"thief","encounter":"draco_battle","n":500,"from_level":7,"to_level":8,"before":0.672,"after":0.646,"uplift":-0.026,"ci95":[-0.07932238470117818,0.02732238470117818],"scope":"engine EXP growth, fixed inventory, table passives, fixed active unlocks"} | {"before_wilson":"67.2% [63.0, 71.2]","after_wilson":"64.6% [60.3, 68.7]"} |


#### M10


| 阶段 | 原始指标 | 二项率区间补充 |
| --- | --- | --- |
| 前 | {"encounter":"dark_forest_loc","character":"hero","cv":0.0,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"dark_forest_loc","character":"cleric","cv":0.0,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"dark_forest_loc","character":"mage","cv":0.0,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"dark_forest_loc","character":"thief","cv":0.0,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort","character":"hero","cv":0.5824823725107175,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort","character":"cleric","cv":0.5631363899787852,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort","character":"mage","cv":0.5631363899787852,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort","character":"thief","cv":0.7749901651618303,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_first_second","character":"hero","cv":0.41187723552395705,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_first_second","character":"cleric","cv":0.39819756008691115,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_first_second","character":"mage","cv":0.39819756008691115,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_first_second","character":"thief","cv":0.5480008011388127,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_second_right","character":"hero","cv":0.6004533434723093,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_second_right","character":"cleric","cv":0.5631363899787852,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_second_right","character":"mage","cv":0.5631363899787852,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_second_right","character":"thief","cv":0.7749901651618303,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_fourth","character":"hero","cv":0.5600208754392169,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_fourth","character":"cleric","cv":0.5032446803825485,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_fourth","character":"mage","cv":0.5032446803825485,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"goblin_fort_fourth","character":"thief","cv":0.746177296252537,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_heat_corridor","character":"hero","cv":0.3030457633656629,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_heat_corridor","character":"cleric","cv":0.27447498535523723,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_heat_corridor","character":"mage","cv":0.27447498535523723,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_heat_corridor","character":"thief","cv":0.49065338146265813,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_lava_room","character":"hero","cv":0.36914261636170925,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_lava_room","character":"cleric","cv":0.3315555428795973,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_lava_room","character":"mage","cv":0.3315555428795973,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_lava_room","character":"thief","cv":0.5079713519466731,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_crystal_corridor","character":"hero","cv":0.4082386504848663,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_crystal_corridor","character":"cleric","cv":0.33806525238667606,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_crystal_corridor","character":"mage","cv":0.33806525238667606,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_crystal_corridor","character":"thief","cv":0.5357072414301585,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_prism_tree","character":"hero","cv":0.7234554222388107,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_prism_tree","character":"cleric","cv":0.6405420552023057,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_prism_tree","character":"mage","cv":0.6405420552023057,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"cave_prism_tree","character":"thief","cv":0.9344935724308652,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_ambush_one","character":"hero","cv":0.6004533434723093,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_ambush_one","character":"cleric","cv":0.5631363899787852,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_ambush_one","character":"mage","cv":0.5631363899787852,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_ambush_one","character":"thief","cv":0.8660254037844386,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_ambush_two","character":"hero","cv":0.6004533434723093,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_ambush_two","character":"cleric","cv":0.5631363899787852,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_ambush_two","character":"mage","cv":0.5631363899787852,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_ambush_two","character":"thief","cv":0.8660254037844386,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_king_battle","character":"hero","cv":0.6750606909857941,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_king_battle","character":"cleric","cv":0.594949732122318,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_king_battle","character":"mage","cv":0.594949732122318,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"slime_king_battle","character":"thief","cv":0.8956240322017605,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"forest_wolves","character":"hero","cv":0.6771510554705836,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"forest_wolves","character":"cleric","cv":0.6032282674143735,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"forest_wolves","character":"mage","cv":0.6032282674143735,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"forest_wolves","character":"thief","cv":0.8983785299469963,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"village_fire_elemental","character":"hero","cv":0.6377145205350117,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"village_fire_elemental","character":"cleric","cv":0.6189527615647366,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"village_fire_elemental","character":"mage","cv":0.4525017708986028,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"village_fire_elemental","character":"thief","cv":0.8564394275414896,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"ice_elemental_encounter","character":"hero","cv":0.7667959695735351,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"ice_elemental_encounter","character":"cleric","cv":0.7638482604372934,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"ice_elemental_encounter","character":"mage","cv":0.6137759372331304,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"ice_elemental_encounter","character":"thief","cv":0.9922743673498738,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"frost_wolf_battle","character":"hero","cv":0.7693092581620716,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"frost_wolf_battle","character":"cleric","cv":0.7718449849879598,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"frost_wolf_battle","character":"mage","cv":0.6032282674143735,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"frost_wolf_battle","character":"thief","cv":1.0,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"valley_entrance","character":"hero","cv":0.5051983479592272,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"valley_entrance","character":"cleric","cv":0.5206696651475804,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"valley_entrance","character":"mage","cv":0.4750727168917954,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"valley_entrance","character":"thief","cv":0.6829651881734528,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"dragon_valley_loc","character":"hero","cv":0.8089313748710768,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"dragon_valley_loc","character":"cleric","cv":0.8019957045112374,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"dragon_valley_loc","character":"mage","cv":0.651126851657992,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"dragon_valley_loc","character":"thief","cv":1.0293073939636683,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"draco_battle","character":"hero","cv":0.6949432492112722,"notes":["defend"]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"draco_battle","character":"cleric","cv":0.6818694424294214,"notes":["defend"]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"draco_battle","character":"mage","cv":0.6010236031279935,"notes":["defend"]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"draco_battle","character":"thief","cv":0.9143662142547109,"notes":["defend"]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"village_fire_slime","character":"hero","cv":0.14285714285714307,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"village_fire_slime","character":"cleric","cv":0.252645576319956,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"village_fire_slime","character":"mage","cv":0.5773502691896258,"notes":[]} | 解析比/均值或原差值口径 |
| 前 | {"encounter":"village_fire_slime","character":"thief","cv":0.5773502691896257,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"dark_forest_loc","character":"hero","cv":0.0,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"dark_forest_loc","character":"cleric","cv":0.0,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"dark_forest_loc","character":"mage","cv":0.0,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"dark_forest_loc","character":"thief","cv":0.0,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort","character":"hero","cv":0.24743582965269634,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort","character":"cleric","cv":0.29247324530358465,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort","character":"mage","cv":0.29247324530358465,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort","character":"thief","cv":0.5179697702828124,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_first_second","character":"hero","cv":0.18139172280235868,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_first_second","character":"cleric","cv":0.23430507997418107,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_first_second","character":"mage","cv":0.23430507997418107,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_first_second","character":"thief","cv":0.3934506128709697,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_second_right","character":"hero","cv":0.20305866063400468,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_second_right","character":"cleric","cv":0.27742294121252153,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_second_right","character":"mage","cv":0.27742294121252153,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_second_right","character":"thief","cv":0.4943684851444637,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_fourth","character":"hero","cv":0.16109351690622614,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_fourth","character":"cleric","cv":0.23131414116370813,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_fourth","character":"mage","cv":0.23131414116370813,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"goblin_fort_fourth","character":"thief","cv":0.40531641328727935,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_heat_corridor","character":"hero","cv":0.26969925127769234,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_heat_corridor","character":"cleric","cv":0.20680981506980128,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_heat_corridor","character":"mage","cv":0.2336014853303289,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_heat_corridor","character":"thief","cv":0.43969686527576396,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_lava_room","character":"hero","cv":0.37564278809920243,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_lava_room","character":"cleric","cv":0.3315555428795973,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_lava_room","character":"mage","cv":0.3457820374040624,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_lava_room","character":"thief","cv":0.5079713519466731,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_crystal_corridor","character":"hero","cv":0.25833030540129753,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_crystal_corridor","character":"cleric","cv":0.2942364926339515,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_crystal_corridor","character":"mage","cv":0.3138493422271731,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_crystal_corridor","character":"thief","cv":0.46261276531796425,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_prism_tree","character":"hero","cv":0.5205299305472837,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_prism_tree","character":"cleric","cv":0.47443804493546976,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_prism_tree","character":"mage","cv":0.5017209199272771,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"cave_prism_tree","character":"thief","cv":0.765034241351411,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_ambush_one","character":"hero","cv":0.2041241452319315,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_ambush_one","character":"cleric","cv":0.2526455763199557,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_ambush_one","character":"mage","cv":0.29488391230979427,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_ambush_one","character":"thief","cv":0.5773502691896257,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_ambush_two","character":"hero","cv":0.2041241452319315,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_ambush_two","character":"cleric","cv":0.2526455763199557,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_ambush_two","character":"mage","cv":0.29488391230979427,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_ambush_two","character":"thief","cv":0.5773502691896257,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_king_battle","character":"hero","cv":0.28697869404074766,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_king_battle","character":"cleric","cv":0.3007083835128211,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_king_battle","character":"mage","cv":0.33783196234608803,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"slime_king_battle","character":"thief","cv":0.6119522830317891,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"forest_wolves","character":"hero","cv":0.3818813079129862,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"forest_wolves","character":"cleric","cv":0.34366672401465204,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"forest_wolves","character":"mage","cv":0.3773771152759321,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"forest_wolves","character":"thief","cv":0.6526300069150406,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"village_fire_elemental","character":"hero","cv":0.2242219482871029,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"village_fire_elemental","character":"cleric","cv":0.2648105701177324,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"village_fire_elemental","character":"mage","cv":0.2999457978254475,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"village_fire_elemental","character":"thief","cv":0.5841428589689496,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"ice_elemental_encounter","character":"hero","cv":0.2242219482871029,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"ice_elemental_encounter","character":"cleric","cv":0.2648105701177324,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"ice_elemental_encounter","character":"mage","cv":0.2999457978254475,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"ice_elemental_encounter","character":"thief","cv":0.5841428589689496,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"frost_wolf_battle","character":"hero","cv":0.27169260650224436,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"frost_wolf_battle","character":"cleric","cv":0.3007083835128211,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"frost_wolf_battle","character":"mage","cv":0.3209918382551113,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"frost_wolf_battle","character":"thief","cv":0.6055300708194983,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"valley_entrance","character":"hero","cv":0.6799781189233465,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"valley_entrance","character":"cleric","cv":0.7309998755530567,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"valley_entrance","character":"mage","cv":0.8209220690651827,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"valley_entrance","character":"thief","cv":0.8924118398849037,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"dragon_valley_loc","character":"hero","cv":0.5657400128575243,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"dragon_valley_loc","character":"cleric","cv":0.5662108157634337,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"dragon_valley_loc","character":"mage","cv":0.5184040810353837,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"dragon_valley_loc","character":"thief","cv":0.8094104905128952,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"draco_battle","character":"hero","cv":0.8913704874798946,"notes":["defend"]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"draco_battle","character":"cleric","cv":0.8659351566146412,"notes":["defend"]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"draco_battle","character":"mage","cv":0.7890698262097324,"notes":["defend"]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"draco_battle","character":"thief","cv":1.0923083043009116,"notes":["defend"]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"village_fire_slime","character":"hero","cv":0.2041241452319315,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"village_fire_slime","character":"cleric","cv":0.2526455763199557,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"village_fire_slime","character":"mage","cv":0.36115755925730747,"notes":[]} | 解析比/均值或原差值口径 |
| 后 | {"encounter":"village_fire_slime","character":"thief","cv":0.5773502691896257,"notes":[]} | 解析比/均值或原差值口径 |


#### M11


| 阶段 | 原始指标 | 二项率区间补充 |
| --- | --- | --- |
| 前 | {"archetype":"P2","character":"cleric","encounter":"cave_crystal_corridor","encounter_class":"elite","value":1.1870396675084174,"n":48} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"cave_heat_corridor","encounter_class":"elite","value":0.5007251082251083,"n":48} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"cave_lava_room","encounter_class":"elite","value":0.42015151515151505,"n":48} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"cave_prism_tree","encounter_class":"boss","value":1.359939723044986,"n":45} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"dark_forest_loc","encounter_class":"trash","value":0.5346844444444444,"n":500} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"draco_battle","encounter_class":"boss","value":5.707835757337523,"n":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"dragon_valley_loc","encounter_class":"boss","value":0.9483122923588042,"n":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"forest_wolves","encounter_class":"elite","value":0.07221503977968176,"n":48} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"frost_wolf_battle","encounter_class":"boss","value":0.2935222868217054,"n":48} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"goblin_fort","encounter_class":"trash","value":0.03755707762557078,"n":219} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"goblin_fort_first_second","encounter_class":"elite","value":0.3029430988081507,"n":289} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"goblin_fort_fourth","encounter_class":"boss","value":2.097090323525106,"n":495} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"goblin_fort_second_right","encounter_class":"elite","value":0.16065500414775777,"n":495} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"ice_elemental_encounter","encounter_class":"elite","value":0.16053779069767443,"n":48} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"slime_ambush_one","encounter_class":"trash","value":0.12041251329080276,"n":48} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"slime_ambush_two","encounter_class":"trash","value":0.10570939659755449,"n":48} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"slime_king_battle","encounter_class":"boss","value":0.9470431286549709,"n":48} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"valley_entrance","encounter_class":"elite","value":0.5096562464251588,"n":48} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"village_fire_elemental","encounter_class":"elite","value":0.10624249966000271,"n":9} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"village_fire_slime","encounter_class":"trash","value":0.020286027185466723,"n":38} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"cave_crystal_corridor","encounter_class":"elite","value":0.9609367619047618,"n":125} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"cave_heat_corridor","encounter_class":"elite","value":0.49869760000000013,"n":125} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"cave_lava_room","encounter_class":"elite","value":0.16822399999999998,"n":125} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"cave_prism_tree","encounter_class":"boss","value":1.2555229999999997,"n":125} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"dark_forest_loc","encounter_class":"trash","value":0.447726,"n":500} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"draco_battle","encounter_class":"boss","value":3.8889001188354126,"n":119} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"dragon_valley_loc","encounter_class":"boss","value":0.9612705882352939,"n":119} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"forest_wolves","encounter_class":"elite","value":0.02938548148148148,"n":125} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"frost_wolf_battle","encounter_class":"boss","value":0.14935054814814816,"n":125} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"goblin_fort","encounter_class":"trash","value":0.028823529411764703,"n":204} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"goblin_fort_first_second","encounter_class":"elite","value":0.2127345029239766,"n":285} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"goblin_fort_fourth","encounter_class":"boss","value":1.8786148296593186,"n":499} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"goblin_fort_second_right","encounter_class":"elite","value":0.05923206412825651,"n":499} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"ice_elemental_encounter","encounter_class":"elite","value":0.09210911111111111,"n":125} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"slime_ambush_one","encounter_class":"trash","value":0.015726666666666667,"n":125} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"slime_ambush_two","encounter_class":"trash","value":0.0203,"n":125} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"slime_king_battle","encounter_class":"boss","value":0.320852,"n":125} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"valley_entrance","encounter_class":"elite","value":0.30843316851851854,"n":125} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"village_fire_elemental","encounter_class":"elite","value":0.1108246913580247,"n":27} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"village_fire_slime","encounter_class":"trash","value":0.0320982905982906,"n":91} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"cave_crystal_corridor","encounter_class":"elite","value":1.4837345679012346,"n":45} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"cave_heat_corridor","encounter_class":"elite","value":0.12480580884836207,"n":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"cave_lava_room","encounter_class":"elite","value":0.358095238095238,"n":46} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"cave_prism_tree","encounter_class":"boss","value":0.9495518707482992,"n":30} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"dark_forest_loc","encounter_class":"trash","value":0.7169566666666667,"n":500} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"draco_battle","encounter_class":"boss","value":2.2507532218739112,"n":29} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"dragon_valley_loc","encounter_class":"boss","value":1.415151875685209,"n":37} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"forest_wolves","encounter_class":"elite","value":0.005416666666666667,"n":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"frost_wolf_battle","encounter_class":"boss","value":0.20501234567901233,"n":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"goblin_fort","encounter_class":"trash","value":0.027657163742690054,"n":228} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"goblin_fort_first_second","encounter_class":"elite","value":0.33541666666666664,"n":282} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"goblin_fort_fourth","encounter_class":"boss","value":1.4321783264746226,"n":486} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"goblin_fort_second_right","encounter_class":"elite","value":0.015569958847736622,"n":486} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"ice_elemental_encounter","encounter_class":"elite","value":0.03148148148148148,"n":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"slime_ambush_one","encounter_class":"trash","value":0.0,"n":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"slime_ambush_two","encounter_class":"trash","value":0.0,"n":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"slime_king_battle","encounter_class":"boss","value":0.5708571428571428,"n":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"valley_entrance","encounter_class":"elite","value":0.31298846696874183,"n":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"village_fire_elemental","encounter_class":"elite","value":0.15059583333333335,"n":8} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"village_fire_slime","encounter_class":"trash","value":0.0022904483430799217,"n":38} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"cave_crystal_corridor","encounter_class":"elite","value":1.0378127896200187,"n":249} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"cave_heat_corridor","encounter_class":"elite","value":0.9114804114804116,"n":259} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"cave_lava_room","encounter_class":"elite","value":0.30329008341056535,"n":249} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"cave_prism_tree","encounter_class":"boss","value":1.5235357864818446,"n":241} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"dark_forest_loc","encounter_class":"trash","value":0.6664314285714286,"n":500} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"draco_battle","encounter_class":"boss","value":5.337242554739423,"n":231} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"dragon_valley_loc","encounter_class":"boss","value":1.2564358940381395,"n":257} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"forest_wolves","encounter_class":"elite","value":0.09865231747584688,"n":259} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"frost_wolf_battle","encounter_class":"boss","value":0.2620950232398141,"n":258} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"goblin_fort","encounter_class":"trash","value":0.023428571428571427,"n":100} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"goblin_fort_first_second","encounter_class":"elite","value":0.24220841959972395,"n":138} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"goblin_fort_fourth","encounter_class":"boss","value":2.5509211727127536,"n":487} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"goblin_fort_second_right","encounter_class":"elite","value":0.12678105520210783,"n":494} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"ice_elemental_encounter","encounter_class":"elite","value":0.12159883720930233,"n":258} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"slime_ambush_one","encounter_class":"trash","value":0.06724806724806724,"n":259} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"slime_ambush_two","encounter_class":"trash","value":0.06864846864846864,"n":259} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"slime_king_battle","encounter_class":"boss","value":0.5885253935253938,"n":259} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"valley_entrance","encounter_class":"elite","value":0.3112362601099191,"n":258} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"village_fire_elemental","encounter_class":"elite","value":0.21499710910005035,"n":117} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"village_fire_slime","encounter_class":"trash","value":0.03499276759884282,"n":122} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"cave_crystal_corridor","encounter_class":"elite","value":0.8548340532757378,"n":463} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"cave_heat_corridor","encounter_class":"elite","value":0.2616529877609791,"n":463} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"cave_lava_room","encounter_class":"elite","value":0.46424766018718494,"n":463} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"cave_prism_tree","encounter_class":"boss","value":1.1129508639308856,"n":463} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"dark_forest_loc","encounter_class":"trash","value":0.5346844444444444,"n":500} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"draco_battle","encounter_class":"boss","value":1.01435845821604,"n":244} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"dragon_valley_loc","encounter_class":"boss","value":1.5725182195182195,"n":333} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"forest_wolves","encounter_class":"elite","value":0.2700697046803917,"n":393} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"frost_wolf_battle","encounter_class":"boss","value":1.6531516717563228,"n":387} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"goblin_fort","encounter_class":"trash","value":0.035053272450532726,"n":219} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"goblin_fort_first_second","encounter_class":"elite","value":0.10203830109973454,"n":293} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"goblin_fort_fourth","encounter_class":"boss","value":1.862468253968254,"n":500} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"goblin_fort_second_right","encounter_class":"elite","value":0.24211714285714284,"n":500} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"ice_elemental_encounter","encounter_class":"elite","value":0.3057152924594785,"n":387} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"slime_ambush_one","encounter_class":"trash","value":0.14748137967144445,"n":463} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"slime_ambush_two","encounter_class":"trash","value":0.15092663132403952,"n":463} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"slime_king_battle","encounter_class":"boss","value":2.78548596112311,"n":463} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"valley_entrance","encounter_class":"elite","value":0.11496151996151996,"n":336} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"village_fire_elemental","encounter_class":"elite","value":0.3443168527379053,"n":57} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"village_fire_slime","encounter_class":"trash","value":0.029656693517453012,"n":316} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"cave_crystal_corridor","encounter_class":"elite","value":0.4463004357993197,"n":490} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"cave_heat_corridor","encounter_class":"elite","value":0.24413839285714287,"n":490} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"cave_lava_room","encounter_class":"elite","value":0.13595553935860058,"n":490} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"cave_prism_tree","encounter_class":"boss","value":0.8234917006423105,"n":490} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"dark_forest_loc","encounter_class":"trash","value":0.447726,"n":500} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"draco_battle","encounter_class":"boss","value":2.6711453430323773,"n":369} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"dragon_valley_loc","encounter_class":"boss","value":2.2534611071533335,"n":487} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"forest_wolves","encounter_class":"elite","value":0.05909387755102041,"n":490} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"frost_wolf_battle","encounter_class":"boss","value":1.032780174927114,"n":490} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"goblin_fort","encounter_class":"trash","value":0.026421568627450983,"n":204} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"goblin_fort_first_second","encounter_class":"elite","value":0.08570701754385965,"n":285} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"goblin_fort_fourth","encounter_class":"boss","value":1.129236956521739,"n":500} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"goblin_fort_second_right","encounter_class":"elite","value":0.12276630434782608,"n":500} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"ice_elemental_encounter","encounter_class":"elite","value":0.20064839650145772,"n":490} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"slime_ambush_one","encounter_class":"trash","value":0.03087405247813411,"n":490} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"slime_ambush_two","encounter_class":"trash","value":0.0319935860058309,"n":490} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"slime_king_battle","encounter_class":"boss","value":0.8901564868804666,"n":490} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"valley_entrance","encounter_class":"elite","value":0.12705426811381637,"n":487} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"village_fire_elemental","encounter_class":"elite","value":0.26720151371807,"n":151} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"village_fire_slime","encounter_class":"trash","value":0.04465934065934066,"n":312} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"cave_crystal_corridor","encounter_class":"elite","value":1.364977181453085,"n":415} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"cave_heat_corridor","encounter_class":"elite","value":0.06416429353778752,"n":415} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"cave_lava_room","encounter_class":"elite","value":0.23216648411829136,"n":415} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"cave_prism_tree","encounter_class":"boss","value":0.4818968141233766,"n":368} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"dark_forest_loc","encounter_class":"trash","value":0.7169566666666667,"n":500} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"draco_battle","encounter_class":"boss","value":1.8442034915439167,"n":47} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"dragon_valley_loc","encounter_class":"boss","value":1.676009793351303,"n":265} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"forest_wolves","encounter_class":"elite","value":0.028068786266924568,"n":376} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"frost_wolf_battle","encounter_class":"boss","value":1.1873490990990991,"n":370} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"goblin_fort","encounter_class":"trash","value":0.02765716374269006,"n":228} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"goblin_fort_first_second","encounter_class":"elite","value":0.10236111111111111,"n":282} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"goblin_fort_fourth","encounter_class":"boss","value":1.274619906479626,"n":499} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"goblin_fort_second_right","encounter_class":"elite","value":0.039903,"n":500} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"ice_elemental_encounter","encounter_class":"elite","value":0.05585567470956212,"n":373} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"slime_ambush_one","encounter_class":"trash","value":0.0015786783497626872,"n":415} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"slime_ambush_two","encounter_class":"trash","value":0.0015450894487039066,"n":415} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"slime_king_battle","encounter_class":"boss","value":1.2471139101861994,"n":415} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"valley_entrance","encounter_class":"elite","value":0.05364814814814815,"n":270} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"village_fire_elemental","encounter_class":"elite","value":0.17830043859649128,"n":76} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"village_fire_slime","encounter_class":"trash","value":0.009604882749759076,"n":283} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"cave_crystal_corridor","encounter_class":"elite","value":0.7795376115448968,"n":326} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"cave_heat_corridor","encounter_class":"elite","value":0.44284380633530773,"n":353} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"cave_lava_room","encounter_class":"elite","value":0.3223391339538648,"n":353} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"cave_prism_tree","encounter_class":"boss","value":0.9314199235344095,"n":321} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"dark_forest_loc","encounter_class":"trash","value":0.6664314285714286,"n":500} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"draco_battle","encounter_class":"boss","value":3.846913394764957,"n":32} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"dragon_valley_loc","encounter_class":"boss","value":1.7566790352504638,"n":231} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"forest_wolves","encounter_class":"elite","value":0.14892720915448188,"n":286} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"frost_wolf_battle","encounter_class":"boss","value":1.1549202127659575,"n":282} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"goblin_fort","encounter_class":"trash","value":0.023428571428571424,"n":100} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"goblin_fort_first_second","encounter_class":"elite","value":0.1058133472367049,"n":137} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"goblin_fort_fourth","encounter_class":"boss","value":1.598035357142857,"n":500} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"goblin_fort_second_right","encounter_class":"elite","value":0.190486875,"n":500} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"ice_elemental_encounter","encounter_class":"elite","value":0.2110876047711154,"n":282} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"slime_ambush_one","encounter_class":"trash","value":0.11873873293844965,"n":353} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"slime_ambush_two","encounter_class":"trash","value":0.12083923512747875,"n":353} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"slime_king_battle","encounter_class":"boss","value":1.8475244656193666,"n":353} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"valley_entrance","encounter_class":"elite","value":0.05383441091954023,"n":232} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"village_fire_elemental","encounter_class":"elite","value":0.3917871900826446,"n":121} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"village_fire_slime","encounter_class":"trash","value":0.04997330689444783,"n":149} | 解析比/均值或原差值口径 |


#### M1'


| 阶段 | 原始指标 | 二项率区间补充 |
| --- | --- | --- |
| 前 | {"character":"cleric","lower":"P0a","upper":"P1","gap_pp":1.0,"shortfall_pp":13.999999999999998} | 解析比/均值或原差值口径 |
| 前 | {"character":"cleric","lower":"P0b","upper":"P1","gap_pp":-0.2,"shortfall_pp":15.2} | 解析比/均值或原差值口径 |
| 前 | {"character":"cleric","lower":"P1","upper":"P2","gap_pp":7.400000000000001,"shortfall_pp":7.599999999999999} | 解析比/均值或原差值口径 |
| 前 | {"character":"cleric","lower":"P2","upper":"P3","gap_pp":-0.40000000000000036,"shortfall_pp":15.4} | 解析比/均值或原差值口径 |
| 前 | {"character":"hero","lower":"P0a","upper":"P1","gap_pp":3.8,"shortfall_pp":11.2} | 解析比/均值或原差值口径 |
| 前 | {"character":"hero","lower":"P0b","upper":"P1","gap_pp":1.2,"shortfall_pp":13.799999999999999} | 解析比/均值或原差值口径 |
| 前 | {"character":"hero","lower":"P1","upper":"P2","gap_pp":17.0,"shortfall_pp":0} | 解析比/均值或原差值口径 |
| 前 | {"character":"hero","lower":"P2","upper":"P3","gap_pp":-6.4,"shortfall_pp":21.4} | 解析比/均值或原差值口径 |
| 前 | {"character":"mage","lower":"P0a","upper":"P1","gap_pp":0,"shortfall_pp":15.0} | 解析比/均值或原差值口径 |
| 前 | {"character":"mage","lower":"P0b","upper":"P1","gap_pp":0,"shortfall_pp":15.0} | 解析比/均值或原差值口径 |
| 前 | {"character":"mage","lower":"P1","upper":"P2","gap_pp":1.6,"shortfall_pp":13.4} | 解析比/均值或原差值口径 |
| 前 | {"character":"mage","lower":"P2","upper":"P3","gap_pp":4.6,"shortfall_pp":10.4} | 解析比/均值或原差值口径 |
| 前 | {"character":"thief","lower":"P0a","upper":"P1","gap_pp":1.4000000000000001,"shortfall_pp":13.599999999999998} | 解析比/均值或原差值口径 |
| 前 | {"character":"thief","lower":"P0b","upper":"P1","gap_pp":-0.2,"shortfall_pp":15.2} | 解析比/均值或原差值口径 |
| 前 | {"character":"thief","lower":"P1","upper":"P2","gap_pp":39.8,"shortfall_pp":0} | 解析比/均值或原差值口径 |
| 前 | {"character":"thief","lower":"P2","upper":"P3","gap_pp":-32.199999999999996,"shortfall_pp":47.199999999999996} | 解析比/均值或原差值口径 |
| 后 | {"character":"cleric","lower":"P0a","upper":"P1","gap_pp":0.4,"shortfall_pp":14.6} | 解析比/均值或原差值口径 |
| 后 | {"character":"cleric","lower":"P0b","upper":"P1","gap_pp":0.4,"shortfall_pp":14.6} | 解析比/均值或原差值口径 |
| 后 | {"character":"cleric","lower":"P1","upper":"P2","gap_pp":48.0,"shortfall_pp":0} | 解析比/均值或原差值口径 |
| 后 | {"character":"cleric","lower":"P2","upper":"P3","gap_pp":-48.4,"shortfall_pp":63.4} | 解析比/均值或原差值口径 |
| 后 | {"character":"hero","lower":"P0a","upper":"P1","gap_pp":0.6,"shortfall_pp":14.399999999999999} | 解析比/均值或原差值口径 |
| 后 | {"character":"hero","lower":"P0b","upper":"P1","gap_pp":0.6,"shortfall_pp":14.399999999999999} | 解析比/均值或原差值口径 |
| 后 | {"character":"hero","lower":"P1","upper":"P2","gap_pp":51.0,"shortfall_pp":0} | 解析比/均值或原差值口径 |
| 后 | {"character":"hero","lower":"P2","upper":"P3","gap_pp":-40.2,"shortfall_pp":55.2} | 解析比/均值或原差值口径 |
| 后 | {"character":"mage","lower":"P0a","upper":"P1","gap_pp":0.2,"shortfall_pp":14.799999999999999} | 解析比/均值或原差值口径 |
| 后 | {"character":"mage","lower":"P0b","upper":"P1","gap_pp":0.2,"shortfall_pp":14.799999999999999} | 解析比/均值或原差值口径 |
| 后 | {"character":"mage","lower":"P1","upper":"P2","gap_pp":2.8,"shortfall_pp":12.2} | 解析比/均值或原差值口径 |
| 后 | {"character":"mage","lower":"P2","upper":"P3","gap_pp":-0.19999999999999984,"shortfall_pp":15.2} | 解析比/均值或原差值口径 |
| 后 | {"character":"thief","lower":"P0a","upper":"P1","gap_pp":0,"shortfall_pp":15.0} | 解析比/均值或原差值口径 |
| 后 | {"character":"thief","lower":"P0b","upper":"P1","gap_pp":0,"shortfall_pp":15.0} | 解析比/均值或原差值口径 |
| 后 | {"character":"thief","lower":"P1","upper":"P2","gap_pp":3.4000000000000004,"shortfall_pp":11.6} | 解析比/均值或原差值口径 |
| 后 | {"character":"thief","lower":"P2","upper":"P3","gap_pp":-3.4000000000000004,"shortfall_pp":18.4} | 解析比/均值或原差值口径 |


#### M5


| 阶段 | 原始指标 | 二项率区间补充 |
| --- | --- | --- |
| 前 | {"character":"cleric","n":55,"healing_hp_ratio":3.537741046831956,"healing_usage":0.370510297783025,"unspent_gold_ratio":0.661879467475581} | 解析比/均值或原差值口径 |
| 前 | {"character":"hero","n":220,"healing_hp_ratio":3.9339935064935068,"healing_usage":0.44684253246753247,"unspent_gold_ratio":0.6858914480548762} | 解析比/均值或原差值口径 |
| 前 | {"character":"mage","n":17,"healing_hp_ratio":7.735994397759104,"healing_usage":0.15399159663865547,"unspent_gold_ratio":0.7042858742244741} | 解析比/均值或原差值口径 |
| 前 | {"character":"thief","n":123,"healing_hp_ratio":4.595809881175735,"healing_usage":0.3392338465509197,"unspent_gold_ratio":0.6726364761025054} | 解析比/均值或原差值口径 |
| 后 | {"character":"cleric","n":50,"healing_hp_ratio":3.313333333333333,"healing_usage":0.3509090909090909,"unspent_gold_ratio":0.650361040230197} | 解析比/均值或原差值口径 |
| 后 | {"character":"hero","n":209,"healing_hp_ratio":4.465599736017159,"healing_usage":0.2925039872408293,"unspent_gold_ratio":0.6474839309721431} | 解析比/均值或原差值口径 |
| 后 | {"character":"mage","n":21,"healing_hp_ratio":5.779220779220779,"healing_usage":0.2386904761904762,"unspent_gold_ratio":0.6421943658014954} | 解析比/均值或原差值口径 |
| 后 | {"character":"thief","n":59,"healing_hp_ratio":5.155161787365177,"healing_usage":0.2536992198009147,"unspent_gold_ratio":0.6462953711818541} | 解析比/均值或原差值口径 |


#### M3'


| 阶段 | 原始指标 | 二项率区间补充 |
| --- | --- | --- |
| 前 | {"archetype":"P0b","character":"cleric","encounter":"dragon_valley_loc","value":0.5971866002498472,"n":58,"kill_time_samples":6,"censored_defeats":52,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P0b","character":"cleric","encounter":"frost_wolf_battle","value":0.0982943051188697,"n":263,"kill_time_samples":208,"censored_defeats":55,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P0b","character":"cleric","encounter":"slime_king_battle","value":0.6558429378383541,"n":124,"kill_time_samples":8,"censored_defeats":116,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P0b","character":"hero","encounter":"dragon_valley_loc","value":0.8048235226987244,"n":94,"kill_time_samples":13,"censored_defeats":81,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P0b","character":"hero","encounter":"frost_wolf_battle","value":0.12651601407280472,"n":279,"kill_time_samples":254,"censored_defeats":25,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P0b","character":"hero","encounter":"slime_king_battle","value":0.4230965478613144,"n":170,"kill_time_samples":56,"censored_defeats":114,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P0b","character":"mage","encounter":"dragon_valley_loc","value":null,"n":3,"kill_time_samples":0,"censored_defeats":3,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P0b","character":"mage","encounter":"frost_wolf_battle","value":0.15932552957189738,"n":99,"kill_time_samples":33,"censored_defeats":66,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P0b","character":"mage","encounter":"slime_king_battle","value":0.09185185185185185,"n":52,"kill_time_samples":1,"censored_defeats":51,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P0b","character":"thief","encounter":"dragon_valley_loc","value":0.7673399525874132,"n":63,"kill_time_samples":8,"censored_defeats":55,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P0b","character":"thief","encounter":"frost_wolf_battle","value":0.10940689404459948,"n":260,"kill_time_samples":196,"censored_defeats":64,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P0b","character":"thief","encounter":"slime_king_battle","value":0.22600582039086128,"n":52,"kill_time_samples":9,"censored_defeats":43,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"cave_prism_tree","value":0.34643905406637954,"n":45,"kill_time_samples":45,"censored_defeats":0,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"draco_battle","value":0.014388086206470946,"n":47,"kill_time_samples":42,"censored_defeats":5,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"dragon_valley_loc","value":0.10945449277791179,"n":47,"kill_time_samples":47,"censored_defeats":0,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"frost_wolf_battle","value":0.005856478858959071,"n":48,"kill_time_samples":48,"censored_defeats":0,"infinite_depletion":44} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"goblin_fort_fourth","value":0.5240283048557214,"n":495,"kill_time_samples":48,"censored_defeats":447,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"cleric","encounter":"slime_king_battle","value":0.024296872175964858,"n":48,"kill_time_samples":48,"censored_defeats":0,"infinite_depletion":42} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"cave_prism_tree","value":0.555111110056153,"n":125,"kill_time_samples":123,"censored_defeats":2,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"draco_battle","value":0.0909739258429383,"n":119,"kill_time_samples":104,"censored_defeats":15,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"dragon_valley_loc","value":0.18635356526217198,"n":119,"kill_time_samples":119,"censored_defeats":0,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"frost_wolf_battle","value":0.005175207416119133,"n":125,"kill_time_samples":125,"censored_defeats":0,"infinite_depletion":110} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"goblin_fort_fourth","value":0.3866540111803471,"n":499,"kill_time_samples":125,"censored_defeats":374,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"hero","encounter":"slime_king_battle","value":0.01892578458583911,"n":125,"kill_time_samples":125,"censored_defeats":0,"infinite_depletion":110} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"cave_prism_tree","value":0.0,"n":30,"kill_time_samples":25,"censored_defeats":5,"infinite_depletion":30} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"draco_battle","value":0.0,"n":29,"kill_time_samples":8,"censored_defeats":21,"infinite_depletion":29} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"dragon_valley_loc","value":0.0,"n":37,"kill_time_samples":29,"censored_defeats":8,"infinite_depletion":37} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"frost_wolf_battle","value":0.0,"n":47,"kill_time_samples":47,"censored_defeats":0,"infinite_depletion":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"goblin_fort_fourth","value":0.0,"n":486,"kill_time_samples":47,"censored_defeats":439,"infinite_depletion":486} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"mage","encounter":"slime_king_battle","value":0.0,"n":47,"kill_time_samples":47,"censored_defeats":0,"infinite_depletion":47} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"cave_prism_tree","value":0.5230272370211103,"n":241,"kill_time_samples":226,"censored_defeats":15,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"draco_battle","value":0.1775199206869855,"n":231,"kill_time_samples":206,"censored_defeats":25,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"dragon_valley_loc","value":0.19020785853857058,"n":257,"kill_time_samples":231,"censored_defeats":26,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"frost_wolf_battle","value":0.0,"n":258,"kill_time_samples":258,"censored_defeats":0,"infinite_depletion":258} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"goblin_fort_fourth","value":1.0510104672839633,"n":487,"kill_time_samples":259,"censored_defeats":228,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 前 | {"archetype":"P2","character":"thief","encounter":"slime_king_battle","value":0.0019028663417337615,"n":259,"kill_time_samples":259,"censored_defeats":0,"infinite_depletion":226} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P0b","character":"cleric","encounter":"dragon_valley_loc","value":null,"n":4,"kill_time_samples":0,"censored_defeats":4,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P0b","character":"cleric","encounter":"frost_wolf_battle","value":0.4095470004912849,"n":210,"kill_time_samples":4,"censored_defeats":206,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P0b","character":"cleric","encounter":"slime_king_battle","value":null,"n":131,"kill_time_samples":0,"censored_defeats":131,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P0b","character":"hero","encounter":"dragon_valley_loc","value":null,"n":25,"kill_time_samples":0,"censored_defeats":25,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P0b","character":"hero","encounter":"frost_wolf_battle","value":0.3509970239658324,"n":209,"kill_time_samples":25,"censored_defeats":184,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P0b","character":"hero","encounter":"slime_king_battle","value":null,"n":170,"kill_time_samples":0,"censored_defeats":170,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P0b","character":"mage","encounter":"frost_wolf_battle","value":null,"n":86,"kill_time_samples":0,"censored_defeats":86,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P0b","character":"mage","encounter":"slime_king_battle","value":null,"n":11,"kill_time_samples":0,"censored_defeats":11,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P0b","character":"thief","encounter":"dragon_valley_loc","value":null,"n":4,"kill_time_samples":0,"censored_defeats":4,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P0b","character":"thief","encounter":"frost_wolf_battle","value":0.27131751152721545,"n":149,"kill_time_samples":4,"censored_defeats":145,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P0b","character":"thief","encounter":"slime_king_battle","value":null,"n":55,"kill_time_samples":0,"censored_defeats":55,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"cave_prism_tree","value":0.28283464751050924,"n":463,"kill_time_samples":433,"censored_defeats":30,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"draco_battle","value":0.09645768285172406,"n":244,"kill_time_samples":242,"censored_defeats":2,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"dragon_valley_loc","value":0.18484119089495232,"n":333,"kill_time_samples":244,"censored_defeats":89,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"frost_wolf_battle","value":0.06255952874756217,"n":387,"kill_time_samples":336,"censored_defeats":51,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"goblin_fort_fourth","value":0.21197979134462325,"n":500,"kill_time_samples":463,"censored_defeats":37,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"cleric","encounter":"slime_king_battle","value":0.157756589357138,"n":463,"kill_time_samples":393,"censored_defeats":70,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"cave_prism_tree","value":0.27180791840343393,"n":490,"kill_time_samples":487,"censored_defeats":3,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"draco_battle","value":0.32125644867458075,"n":369,"kill_time_samples":258,"censored_defeats":111,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"dragon_valley_loc","value":0.3501604732586009,"n":487,"kill_time_samples":369,"censored_defeats":118,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"frost_wolf_battle","value":0.13994836569065153,"n":490,"kill_time_samples":487,"censored_defeats":3,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"goblin_fort_fourth","value":0.16853154136617152,"n":500,"kill_time_samples":490,"censored_defeats":10,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"hero","encounter":"slime_king_battle","value":0.12644822688271642,"n":490,"kill_time_samples":490,"censored_defeats":0,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"cave_prism_tree","value":0.0,"n":368,"kill_time_samples":307,"censored_defeats":61,"infinite_depletion":368} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"draco_battle","value":0.0,"n":47,"kill_time_samples":15,"censored_defeats":32,"infinite_depletion":47} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"dragon_valley_loc","value":0.0,"n":265,"kill_time_samples":47,"censored_defeats":218,"infinite_depletion":265} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"frost_wolf_battle","value":0.0,"n":370,"kill_time_samples":270,"censored_defeats":100,"infinite_depletion":370} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"goblin_fort_fourth","value":0.014063345760701146,"n":499,"kill_time_samples":415,"censored_defeats":84,"infinite_depletion":384} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"mage","encounter":"slime_king_battle","value":0.0,"n":415,"kill_time_samples":376,"censored_defeats":39,"infinite_depletion":415} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"cave_prism_tree","value":0.292255658885031,"n":321,"kill_time_samples":268,"censored_defeats":53,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"draco_battle","value":0.7073235169025078,"n":32,"kill_time_samples":17,"censored_defeats":15,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"dragon_valley_loc","value":0.3210071952740998,"n":231,"kill_time_samples":32,"censored_defeats":199,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"frost_wolf_battle","value":0.07595225135579278,"n":282,"kill_time_samples":232,"censored_defeats":50,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"goblin_fort_fourth","value":0.19138425799050507,"n":500,"kill_time_samples":353,"censored_defeats":147,"infinite_depletion":0} | 解析比/均值或原差值口径 |
| 后 | {"archetype":"P2","character":"thief","encounter":"slime_king_battle","value":0.1171876884377394,"n":353,"kill_time_samples":286,"censored_defeats":67,"infinite_depletion":0} | 解析比/均值或原差值口径 |

### 硬门槛逐项例外与建议归属

以下为待批准的例外，归属仅为工程建议。没有到达样本的项保持未验证；未提前批准任何放宽。

| 门槛 | 格 | 实测 | 目标 | 建议归属 |
| --- | --- | --- | --- | --- |
| M4 | P2/thief/draco_battle/heuristic_v3 | 26.5 | "<=14" | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M4 | P3/cleric/merchant_battle/heuristic_v3 | 20 | "<=14" | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M4 | P2s/thief/draco_battle/heuristic_v3 | 30 | "<=14" | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M4 | checkpoint/mage/goblin_fort_fourth/attack_only | 15.0 | "<=14" | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M4 | checkpoint/mage/goblin_fort_fourth/best_free | 15.0 | "<=14" | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M4 | checkpoint/hero/draco_battle/attack_only | 25.0 | "<=14" | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M4 | checkpoint/hero/draco_battle/best_free | 15.0 | "<=14" | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M4 | checkpoint/thief/draco_battle/heuristic_v3 | 28.0 | "<=14" | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M9 | goblin_fort/mage | 0.27416666666666667 | [0.1,0.2] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | goblin_fort_first_second/hero | 0.1715 | [0.18,0.3] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | goblin_fort_first_second/mage | 0.35250000000000004 | [0.18,0.3] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | goblin_fort_second_right/hero | 0.17149999999999999 | [0.18,0.3] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | goblin_fort_second_right/mage | 0.3525 | [0.18,0.3] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | goblin_fort_fourth/hero | 0.1917391304347826 | [0.28,0.35] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | goblin_fort_fourth/mage | 0.40733333333333327 | [0.28,0.35] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | cave_heat_corridor/hero | 0.0909375 | [0.18,0.3] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | cave_heat_corridor/thief | 0.17045454545454544 | [0.18,0.3] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | cave_lava_room/cleric | 0.37599999999999995 | [0.18,0.3] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | cave_lava_room/mage | 0.5018181818181818 | [0.18,0.3] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | cave_lava_room/thief | 0.3214285714285714 | [0.18,0.3] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | cave_crystal_corridor/mage | 0.3571969696969697 | [0.18,0.3] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | cave_prism_tree/hero | 0.17280831473214286 | [0.28,0.39999999999999997] | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M9 | cave_prism_tree/cleric | 0.2379375 | [0.28,0.39999999999999997] | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M9 | cave_prism_tree/thief | 0.2260044642857143 | [0.28,0.39999999999999997] | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M9 | slime_ambush_one/hero | 0.054857142857142854 | [0.1,0.15] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | slime_ambush_one/mage | 0.16727272727272727 | [0.1,0.15] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | slime_ambush_two/hero | 0.054857142857142854 | [0.1,0.15] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | slime_ambush_two/mage | 0.16727272727272727 | [0.1,0.15] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | slime_king_battle/hero | 0.21942857142857145 | [0.28,0.35] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | slime_king_battle/mage | 0.38333333333333336 | [0.28,0.35] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | forest_wolves/hero | 0.13714285714285715 | [0.18,0.25] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | forest_wolves/mage | 0.26833333333333337 | [0.18,0.25] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | village_fire_elemental/hero | 0.15085714285714283 | [0.18,0.25] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | village_fire_elemental/mage | 0.36416666666666675 | [0.18,0.25] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | ice_elemental_encounter/hero | 0.15085714285714283 | [0.18,0.25] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | ice_elemental_encounter/mage | 0.36416666666666675 | [0.18,0.25] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | frost_wolf_battle/hero | 0.24685714285714289 | [0.28,0.35] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | frost_wolf_battle/mage | 0.49833333333333335 | [0.28,0.35] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | valley_entrance/hero | 0.15542857142857144 | [0.18,0.25] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | valley_entrance/mage | 0.3194444444444445 | [0.18,0.25] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | dragon_valley_loc/hero | 0.24783673469387751 | [0.28,0.35] | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M9 | dragon_valley_loc/mage | 0.48875 | [0.28,0.35] | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M9 | draco_battle/hero | 0.25052631578947365 | [0.28,0.35] | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M9 | draco_battle/mage | 0.4688461538461539 | [0.28,0.35] | 052b（Boss结构/百分比招式）；盗賊循环另归052c |
| M9 | village_fire_slime/hero | 0.027428571428571427 | [0.1,0.15] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | village_fire_slime/cleric | 0.028484848484848484 | [0.1,0.15] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | village_fire_slime/mage | 0.09583333333333334 | [0.1,0.15] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9 | village_fire_slime/thief | 0.03125 | [0.1,0.15] | 需要设计裁定（共享数值带宽及缺样本处理）；052c成长/技能改后回归 |
| M9未验证 | bone_field/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | bone_field/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | bone_field/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | bone_field/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | dragon_valley_return/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | dragon_valley_return/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | dragon_valley_return/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | dragon_valley_return/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | ghoul_marsh/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | ghoul_marsh/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | ghoul_marsh/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | ghoul_marsh/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_chest_fight/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_chest_fight/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_chest_fight/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_chest_fight/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_second_left/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_second_left/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_second_left/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_second_left/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_third_guards/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_third_guards/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_third_guards/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | goblin_fort_third_guards/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_giant_path/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_giant_path/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_giant_path/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_giant_path/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_rockfall_path/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_rockfall_path/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_rockfall_path/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_rockfall_path/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_worm_lair/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_worm_lair/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_worm_lair/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | gorge_worm_lair/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | grave_chapel/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | grave_chapel/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | grave_chapel/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | grave_chapel/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | inn_night_ambush/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | inn_night_ambush/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | inn_night_ambush/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | inn_night_ambush/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | lost_goblin_crossroads/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | lost_goblin_crossroads/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | lost_goblin_crossroads/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | lost_goblin_crossroads/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | mansion_corridor/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | mansion_corridor/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | mansion_corridor/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | mansion_corridor/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | merchant_battle/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | merchant_battle/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | merchant_battle/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | merchant_battle/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | valley_ledge/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | valley_ledge/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | valley_ledge/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | valley_ledge/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | xanxus_phantom_battle/cleric | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | xanxus_phantom_battle/hero | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | xanxus_phantom_battle/mage | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| M9未验证 | xanxus_phantom_battle/thief | null | "实际P2快照" | 需要设计裁定（零到达样本）；后续回归 |
| Ignis到达等级 | P0a/hero | {"n":0,"histogram":{}} | 4 | 需要设计裁定（EXP路径冲突/零到达样本） |
| Ignis到达等级 | P0a/cleric | {"n":0,"histogram":{}} | 4 | 需要设计裁定（EXP路径冲突/零到达样本） |
| Ignis到达等级 | P0a/mage | {"n":0,"histogram":{}} | 4 | 需要设计裁定（EXP路径冲突/零到达样本） |
| Ignis到达等级 | P0a/thief | {"n":0,"histogram":{}} | 4 | 需要设计裁定（EXP路径冲突/零到达样本） |
| Ignis到达等级 | P0b/mage | {"n":0,"histogram":{}} | 4 | 需要设计裁定（EXP路径冲突/零到达样本） |
| M13等级差 | hero/P0a→P2 | {"median_gap":null,"mean_gap":null} | "P2-P0>=2" | 需要设计裁定（等级定义/无到达样本），052b/c后回归 |
| M13等级差 | cleric/P0a→P2 | {"median_gap":null,"mean_gap":null} | "P2-P0>=2" | 需要设计裁定（等级定义/无到达样本），052b/c后回归 |
| M13等级差 | mage/P0a→P2 | {"median_gap":null,"mean_gap":null} | "P2-P0>=2" | 需要设计裁定（等级定义/无到达样本），052b/c后回归 |
| M13等级差 | mage/P0b→P2 | {"median_gap":null,"mean_gap":null} | "P2-P0>=2" | 需要设计裁定（等级定义/无到达样本），052b/c后回归 |
| M13等级差 | thief/P0a→P2 | {"median_gap":null,"mean_gap":null} | "P2-P0>=2" | 需要设计裁定（等级定义/无到达样本），052b/c后回归 |

分支A的8×2000硬门槛按spec归052b/052c重验，本段未执行，不列为通过。工程验证与数值门槛分别见下一节和本表。

### 例外、推断及偏离

TODO(design)：批准或拒绝本候选的 M9 40 个带外格、64 个缺快照格；M4 8 个超限格；Ignis 到达等级 5 个失败/无样本格。逐格证据见上述表及 `acceptance-normal-audit.json`。缺样本没有被记成通过。
TODO(design)：处理下列 M13/P2s 等级条件未通过项：[{"character":"hero","comparison":"P0a→P2","median_gap":null,"mean_gap":null},{"character":"cleric","comparison":"P0a→P2","median_gap":null,"mean_gap":null},{"character":"mage","comparison":"P0a→P2","median_gap":null,"mean_gap":null},{"character":"mage","comparison":"P0b→P2","median_gap":null,"mean_gap":null},{"character":"thief","comparison":"P0a→P2","median_gap":null,"mean_gap":null}]。
TODO(design)：L2严格方向要求仍有65个未满足观察格；是否接受共享参数下的折中，或留待后续职业/百分比机制解决。不能视作已批准例外。
TODO(design)：P0a/P1具体路线EXP顺序冲突、P0a无到达样本需决定后续策略；M9多职业共享公式的带宽冲突需设计取舍。M4剩余结构性Boss和盗賊龟缩问题按052b/c继续，本段没有越权修改技能。原型通关软目标的差距保留在28格表。

推断清单：①by_level 的 resources 按七次升级平均满足增长百分比，属性逐键覆盖并保留未指定默认值；②保留三个已批准整数例外；③L2选择正伤害、低骰子方差，HP估计参考实际胜利回合而非早死中位；④M9/M4分别以配对观察格判停滞；⑤P2未观测的遭遇不造checkpoint；⑥baby有效包保留未启用的作者覆盖层元数据，因此“只revision不同”按排除inactive authoring metadata后的实际游戏数据解释，原始差异键明列；⑦M13等级差用到达中位数并附均值，P2s同时检查两者；⑧M9方向的高值目标按精确上限单列，未假设离散误差自动豁免。

偏离/限制：未能达到所有硬门槛，依据停止规则交最佳候选和例外；原地测试因沙箱权限及未应用测试补丁未通过，叠加执行器结果另列；没有执行git add/commit，遵守本任务§9的补丁交付规定。baby测量原始JSON含运行时长、指纹、targets等元数据差异，只有规范化数值载荷/记录逐字节相同，不宣称原始整文件相同。

### 验证、运行时长与交付

全程离线、付费API调用0、新依赖0；冻结benchmark、提示词、docs、v1被动表和053checkpoint均未修改。测试补丁包含新回归和旧固定数值fixture的配置化，未弱化冻结金标。

收尾测试适配：旧迁移链补上052迁移，并按来源覆盖层顺序比较完整包；成长探针按配置累计；历史F6固定种子使用显式调参前数值夹具，保留败退后继续到ドラコ的全部断言。推断：历史路线回归应固定历史数值输入，候选的数值效果由N500验收检查。最初并行执行原地与叠加全套曾产生临时根目录枚举干扰，最终叠加全套单独执行，初次结果保留在unittest-first-overlay.log。

| 检查 | 结果 |
| --- | --- |
| original_unittest | {"command":"python -m unittest discover -s tests -q","tests":956,"seconds":760.536,"result":"FAILED (failures=27, errors=40, skipped=1)","errors":[{"kind":"ERROR","test":"test_clear_tombstone_survives_event_log_truncation_and_level_up (test_balance_pass3.BalancePass3Tests.test_clear_tombstone_survives_event_log_truncation_and_level_up)"},{"kind":"ERROR","test":"test_old_save_backfill_and_clear_event_order (test_balance_pass3.BalancePass3Tests.test_old_save_backfill_and_clear_event_order)"},{"kind":"ERROR","test":"test_route_cli_reads_custom_targets_and_returns_failure (test_balance_pass4.BalancePass4Tests.test_route_cli_reads_custom_targets_and_returns_failure)"},{"kind":"ERROR","test":"test_legacy_save_loads_at_d4_without_replaying_entry_or_milestone (test_chapter34.Chapter34Tests.test_legacy_save_loads_at_d4_without_replaying_entry_or_milestone)"},{"kind":"ERROR","test":"test_old_report_save_loads (test_chapter5.Chapter5Tests.test_old_report_save_loads)"},{"kind":"ERROR","test":"test_legacy_save_last_equipped_wins_and_is_persisted (test_equipment_slots.EquipmentSlotsTests.test_legacy_save_last_equipped_wins_and_is_persisted)"},{"kind":"ERROR","test":"test_default_table_file_is_used_by_picker_and_standalone_probe (test_measurement_v3.MeasurementV3Tests.test_default_table_file_is_used_by_picker_and_standalone_probe)"},{"kind":"ERROR","test":"test_passive_matrix_reuses_only_identical_complete_histories (test_measurement_v3.MeasurementV3Tests.test_passive_matrix_reuses_only_identical_complete_histories)"},{"kind":"ERROR","test":"test_f6_real_p3_seed_continues_after_mansion_loss (test_normal_tuning_052.Normal052Tests.test_f6_real_p3_seed_continues_after_mansion_loss)"},{"kind":"ERROR","test":"test_confirmation_survives_save_reload (test_npc_combat.NpcCombatTests.test_confirmation_survives_save_reload)"},{"kind":"ERROR","test":"test_hearth_reforges_current_armor_once_persists_after_swap_and_save_load (test_oaksdawn_quests.OaksdawnQuestsTests.test_hearth_reforges_current_armor_once_persists_after_swap_and_save_load)"},{"kind":"ERROR","test":"test_save_load_snapshots_and_no_new_baby_fields (test_progression_v2.ProgressionTests.test_save_load_snapshots_and_no_new_baby_fields)"},{"kind":"ERROR","test":"test_legacy_completed_ignis_save_loads (test_scenario_v2.ScenarioV2Tests.test_legacy_completed_ignis_save_loads)"},{"kind":"ERROR","test":"test_all_encodings_on_all_dev_snapshots_preserve_defaults_and_descriptions (test_schema_encoding.SchemaEncodingTests.test_all_encodings_on_all_dev_snapshots_preserve_defaults_and_descriptions)"},{"kind":"ERROR","test":"test_failure_shapes_and_gemini_only (test_schema_encoding.SchemaEncodingTests.test_failure_shapes_and_gemini_only)"},{"kind":"ERROR","test":"test_flat_enums_use_snapshot_ids_and_empty_snapshots_are_valid (test_schema_encoding.SchemaEncodingTests.test_flat_enums_use_snapshot_ids_and_empty_snapshots_are_valid)"},{"kind":"ERROR","test":"test_gemini_transmits_each_schema_encoding_unchanged (test_schema_encoding.SchemaEncodingTests.test_gemini_transmits_each_schema_encoding_unchanged)"},{"kind":"ERROR","test":"test_guard_still_uses_strict_parser_and_measures_matched_token_delta (test_schema_encoding.SchemaEncodingTests.test_guard_still_uses_strict_parser_and_measures_matched_token_delta)"},{"kind":"ERROR","test":"test_guard_still_uses_strict_parser_and_measures_matched_token_delta (test_schema_encoding.SchemaEncodingTests.test_guard_still_uses_strict_parser_and_measures_matched_token_delta)"},{"kind":"ERROR","test":"test_guard_suffixes_match_spec_verbatim_and_only_append (test_schema_encoding.SchemaEncodingTests.test_guard_suffixes_match_spec_verbatim_and_only_append)"},{"kind":"ERROR","test":"test_smoke_full_dev_gate_shared_policy_and_quota_stop (test_schema_encoding.SchemaEncodingTests.test_smoke_full_dev_gate_shared_policy_and_quota_stop)"},{"kind":"ERROR","test":"test_smoke_full_dev_gate_shared_policy_and_quota_stop (test_schema_encoding.SchemaEncodingTests.test_smoke_full_dev_gate_shared_policy_and_quota_stop)"},{"kind":"ERROR","test":"test_smoke_is_offline_by_default_and_saves_all_four_reports (test_schema_encoding.SchemaEncodingTests.test_smoke_is_offline_by_default_and_saves_all_four_reports)"},{"kind":"ERROR","test":"test_smoke_is_offline_by_default_and_saves_all_four_reports (test_schema_encoding.SchemaEncodingTests.test_smoke_is_offline_by_default_and_saves_all_four_reports)"},{"kind":"ERROR","test":"test_wrapped_strict_parse_and_raw_cache_replay (test_schema_encoding.SchemaEncodingTests.test_wrapped_strict_parse_and_raw_cache_replay)"},{"kind":"ERROR","test":"test_wrapped_strict_parse_and_raw_cache_replay (test_schema_encoding.SchemaEncodingTests.test_wrapped_strict_parse_and_raw_cache_replay)"},{"kind":"ERROR","test":"test_cli_quota_stops_requests_saves_results_and_replays_later_cache (test_schema_shape.SchemaShapeTests.test_cli_quota_stops_requests_saves_results_and_replays_later_cache)"},{"kind":"ERROR","test":"test_cli_quota_stops_requests_saves_results_and_replays_later_cache (test_schema_shape.SchemaShapeTests.test_cli_quota_stops_requests_saves_results_and_replays_later_cache)"},{"kind":"ERROR","test":"test_daily_quota_does_not_sleep_or_retry (test_schema_shape.SchemaShapeTests.test_daily_quota_does_not_sleep_or_retry)"},{"kind":"ERROR","test":"test_lenient_all_kinds_and_conflict_fields (test_schema_shape.SchemaShapeTests.test_lenient_all_kinds_and_conflict_fields)"},{"kind":"ERROR","test":"test_lenient_does_not_repair_bad_shape_or_relevant_values (test_schema_shape.SchemaShapeTests.test_lenient_does_not_repair_bad_shape_or_relevant_values)"},{"kind":"ERROR","test":"test_lenient_reuses_default_key_and_never_calls_on_miss (test_schema_shape.SchemaShapeTests.test_lenient_reuses_default_key_and_never_calls_on_miss)"},{"kind":"ERROR","test":"test_lenient_reuses_default_key_and_never_calls_on_miss (test_schema_shape.SchemaShapeTests.test_lenient_reuses_default_key_and_never_calls_on_miss)"},{"kind":"ERROR","test":"test_mocked_provider_union_payloads_and_error_evidence (test_schema_shape.SchemaShapeTests.test_mocked_provider_union_payloads_and_error_evidence)"},{"kind":"ERROR","test":"test_price_without_cached_rate_when_no_cached_tokens (test_schema_shape.SchemaShapeTests.test_price_without_cached_rate_when_no_cached_tokens)"},{"kind":"ERROR","test":"test_prices_cached_unknown_and_local_zero (test_schema_shape.SchemaShapeTests.test_prices_cached_unknown_and_local_zero)"},{"kind":"ERROR","test":"test_quota_threshold_daily_without_delay_and_policy_latch (test_schema_shape.SchemaShapeTests.test_quota_threshold_daily_without_delay_and_policy_latch)"},{"kind":"ERROR","test":"test_union_schemas_for_all_dev_snapshots (test_schema_shape.SchemaShapeTests.test_union_schemas_for_all_dev_snapshots)"},{"kind":"ERROR","test":"test_union_snapshot_enums_constants_and_description_preservation (test_schema_shape.SchemaShapeTests.test_union_snapshot_enums_constants_and_description_preservation)"},{"kind":"ERROR","test":"test_save_reload_stock_and_legacy_pack_refresh (test_services.ServiceTests.test_save_reload_stock_and_legacy_pack_refresh)"},{"kind":"FAIL","test":"test_idempotent_and_both_packs_match (test_checks_e.ChecksETests.test_idempotent_and_both_packs_match)"},{"kind":"FAIL","test":"test_migration_sync_idempotent_frozen_base_and_schema (test_combat_mechanics_v2.MigrationAndGoldenTests.test_migration_sync_idempotent_frozen_base_and_schema)"},{"kind":"FAIL","test":"test_awaken_once_order_resources_status_flag_and_equipment (test_holy_sword_049.HolySwordTests.test_awaken_once_order_resources_status_flag_and_equipment)"},{"kind":"FAIL","test":"test_baby_effective_diff_only_revision (test_holy_sword_049.HolySwordTests.test_baby_effective_diff_only_revision)"},{"kind":"FAIL","test":"test_field_tick_self_damage_cursed_heal (test_holy_sword_049.HolySwordTests.test_field_tick_self_damage_cursed_heal) (kind='field')"},{"kind":"FAIL","test":"test_field_tick_self_damage_cursed_heal (test_holy_sword_049.HolySwordTests.test_field_tick_self_damage_cursed_heal) (kind='tick')"},{"kind":"FAIL","test":"test_field_tick_self_damage_cursed_heal (test_holy_sword_049.HolySwordTests.test_field_tick_self_damage_cursed_heal) (kind='self')"},{"kind":"FAIL","test":"test_field_tick_self_damage_cursed_heal (test_holy_sword_049.HolySwordTests.test_field_tick_self_damage_cursed_heal) (kind='curse')"},{"kind":"FAIL","test":"test_one_hp_and_guard_priority_then_existing_guard (test_holy_sword_049.HolySwordTests.test_one_hp_and_guard_priority_then_existing_guard)"},{"kind":"FAIL","test":"test_phase_registration_persists_and_transition_does_not_trigger (test_holy_sword_049.HolySwordTests.test_phase_registration_persists_and_transition_does_not_trigger)"},{"kind":"FAIL","test":"test_apply_idempotent_and_pack_content_synchronized (test_loot_economy.LootEconomyTests.test_apply_idempotent_and_pack_content_synchronized)"},{"kind":"FAIL","test":"test_exp_observation_includes_combat_and_quest_without_double_rewards (test_measurement_v3.MeasurementV3Tests.test_exp_observation_includes_combat_and_quest_without_double_rewards)"},{"kind":"FAIL","test":"test_level_probes_use_engine_growth_skills_and_table_passives (test_measurement_v3.MeasurementV3Tests.test_level_probes_use_engine_growth_skills_and_table_passives)"},{"kind":"FAIL","test":"test_migration_idempotent_and_pack_parity (test_npc_combat.NpcCombatTests.test_migration_idempotent_and_pack_parity)"},{"kind":"FAIL","test":"test_both_packs_synchronized_idempotent_undead_and_map_geometry (test_oaksdawn.OaksdawnTests.test_both_packs_synchronized_idempotent_undead_and_map_geometry)"},{"kind":"FAIL","test":"test_icons_optional_and_both_packs_synchronized_idempotent (test_oaksdawn_quests.OaksdawnQuestsTests.test_icons_optional_and_both_packs_synchronized_idempotent)"},{"kind":"FAIL","test":"test_all_encounter_rewards_and_zero_nonvictory (test_progression_v2.ProgressionTests.test_all_encounter_rewards_and_zero_nonvictory)"},{"kind":"FAIL","test":"test_committed_progression_events_survive_log_truncation (test_progression_v2.ProgressionTests.test_committed_progression_events_survive_log_truncation)"},{"kind":"FAIL","test":"test_filtering_and_migration_script (test_progression_v2.ProgressionTests.test_filtering_and_migration_script)"},{"kind":"FAIL","test":"test_level_rewards_growth_events_and_cap (test_progression_v2.ProgressionTests.test_level_rewards_growth_events_and_cap)"},{"kind":"FAIL","test":"test_milestones_and_model_rejection (test_progression_v2.ProgressionTests.test_milestones_and_model_rejection)"},{"kind":"FAIL","test":"test_quests_once_and_main_excluded (test_progression_v2.ProgressionTests.test_quests_once_and_main_excluded)"},{"kind":"FAIL","test":"test_both_packs_map_edges_and_migration_idempotence (test_rewards_battlefield.RewardsBattlefieldTests.test_both_packs_map_edges_and_migration_idempotence)"},{"kind":"FAIL","test":"test_cloak_pickup_preserves_armor_and_only_fills_empty_slot (test_rewards_battlefield.RewardsBattlefieldTests.test_cloak_pickup_preserves_armor_and_only_fills_empty_slot)"},{"kind":"FAIL","test":"test_both_packs_synchronized_and_reapplication_preserves_existing_content (test_rumbling_gorge.RumblingGorgeTests.test_both_packs_synchronized_and_reapplication_preserves_existing_content)"},{"kind":"FAIL","test":"test_migration_idempotence_sync_freeze_and_placeholder_inventory (test_spring_postgame.SpringPostgameTests.test_migration_idempotence_sync_freeze_and_placeholder_inventory)"},{"kind":"FAIL","test":"test_migration_is_idempotent_on_both_packs (test_tutorial_slime.TutorialSlimeTests.test_migration_is_idempotent_on_both_packs)"}],"permission_errors":85} |
| overlay_unittest | {"command":"python -X utf8 .tmp-test/052a3/run_tests.py","tests":964,"seconds":529.507,"result":"OK (skipped=1)","errors":[],"permission_errors":0} |
| node_check | {"command":"node --check client/app.js","exit_code":0} |
| all_skill_kinds | {"command":"python -m unittest discover -s tests -p test_all_skill_kinds.py -q","tests":2,"result":"OK"} |
| combat_golden | {"modes":["baby","normal_empty"],"rows_each":113,"sha256":"14d374747913957829d5162d7aa6d52dfd3ce9ec9b3f8560d1e5f96f0fd1caee","unchanged":true} |
| levels_golden | {"unchanged":true,"sha256":"7a03eb88f5f3dc7d4d5c6d89a288f7a99803fbb624a9bfa1c3eb9b84c66f63f9"} |
| candidate_validation | {"packs":{"dragon_rpg.json":{"idempotent":true,"baby_numeric_equal":true,"baby_gameplay_equal_excluding_revision":true,"growth_averages":{"hero":{"max_hp":3.0,"max_mp":1.0,"max_sp":1.4285714285714286},"cleric":{"max_hp":3.0,"max_mp":2.0,"max_sp":1.0},"mage":{"max_hp":2.2857142857142856,"max_mp":3.0,"max_sp":1.0},"thief":{"max_hp":2.0,"max_mp":1.0,"max_sp":2.0}},"raw_baby_changed_keys":["meta","difficulty_overlays"],"excluded_enemies_unchanged":["tutorial_slime","xanxus"],"revision":"2026-10-23-tuning-052a"},"dragon_rpg_hybrid.json":{"idempotent":true,"baby_numeric_equal":true,"baby_gameplay_equal_excluding_revision":true,"growth_averages":{"hero":{"max_hp":3.0,"max_mp":1.0,"max_sp":1.4285714285714286},"cleric":{"max_hp":3.0,"max_mp":2.0,"max_sp":1.0},"mage":{"max_hp":2.2857142857142856,"max_mp":3.0,"max_sp":1.0},"thief":{"max_hp":2.0,"max_mp":1.0,"max_sp":2.0}},"raw_baby_changed_keys":["meta","difficulty_overlays"],"excluded_enemies_unchanged":["tutorial_slime","xanxus"],"revision":"2026-10-23-tuning-052a"}},"protected_hashes_equal":true} |
| arrival_cache_summary_matches_final_records | true |
| acceptance-baby_053_comparison | {"comparison":"Canonical UTF-8 bytes of numeric payload; raw timing, fingerprints and target metadata reported separately","measurement_checks":{"rows":true,"ignis_levels":true,"metrics":true,"cell_metrics":true,"usage":true,"checkpoint_probes":true,"p2s_comparison":true,"m3b":true},"record_checks":{"records":true,"difficulty":true,"passive_defaults":true,"damage_budget_v2":true,"preparation_probes":true,"companion_probes":true,"level_probes":true,"boss_policy_probes":true},"raw_measurement_equal":false,"differing_top_level_keys":["effective_pack_fingerprint","overlay_fingerprint","code_fingerprint","targets","fingerprints","timings","elapsed_seconds"],"n":500,"seed":20261020,"records":14000,"record_sha256":"c29e1c28e92ac6be9ad648523f959309d10f3521390f00194676d92e5c17c843"} |
| baseline-baby_053_comparison | {"comparison":"Canonical UTF-8 bytes of numeric payload; raw timing, fingerprints and target metadata reported separately","measurement_checks":{"rows":true,"ignis_levels":true,"metrics":true,"cell_metrics":true,"usage":true,"checkpoint_probes":true,"p2s_comparison":true,"m3b":true},"record_checks":{"records":true,"difficulty":true,"passive_defaults":true,"damage_budget_v2":true,"preparation_probes":true,"companion_probes":true,"level_probes":true,"boss_policy_probes":true},"raw_measurement_equal":false,"differing_top_level_keys":["effective_pack_fingerprint","code_fingerprint","targets","fingerprints","timings","elapsed_seconds"],"n":500,"seed":20261020,"records":14000,"record_sha256":"c29e1c28e92ac6be9ad648523f959309d10f3521390f00194676d92e5c17c843"} |
| baby_053_probes | {"human_berserker":{"n":500,"win_rate":0.956,"rounds_median":19.0,"expected_incoming":4.813809523809524,"expected_healing":6.0,"sustain_coverage":1.246414086457612,"sample":{"encounter":"dragon_valley_loc","encounter_class":"boss","status":"victory","rounds":20,"policy":"best_free","before":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":310.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"after_combat":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":310.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"actions":{"item:ice_charm":20},"action_specs":{"item:ice_charm":{"type":"item","id":"ice_charm","free":true,"kind":"damage"}},"consumables":{},"opening":{"expected_damage":4.813809523809524,"variance":35.82390453514739,"cv":1.243361906806332,"ratio":0.12034523809523809,"notes":[]},"expected_healing":6.0,"expected_hp_loss":91.46238095238095,"enemy_phases":19,"companion":"fire_bat_dragon","p0_choice":"item:ice_charm","statuses":[],"skill_usage":{},"after_resolution":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2,"紅竜の炎核":1},"max_hp":40,"gold":701,"healing_hp":310.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"continue":true}},"P0b + 氷鉄の大剣":{"n":500,"win_rate":0.988,"rounds_median":10.0,"expected_incoming":4.813809523809524,"expected_healing":6.0,"sustain_coverage":1.246414086457612,"sample":{"encounter":"dragon_valley_loc","encounter_class":"boss","status":"victory","rounds":12,"policy":"best_free","before":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":310.0,"equipment":["紅玉の護符","革の鎧","氷鉄の大剣"]},"after_combat":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":310.0,"equipment":["紅玉の護符","革の鎧","氷鉄の大剣"]},"actions":{"attack:basic_attack":12},"action_specs":{"attack:basic_attack":{"type":"attack","id":"basic_attack","free":true,"kind":"attack"}},"consumables":{},"opening":{"expected_damage":4.813809523809524,"variance":35.82390453514739,"cv":1.243361906806332,"ratio":0.12034523809523809,"notes":[]},"expected_healing":6.0,"expected_hp_loss":52.951904761904764,"enemy_phases":11,"companion":"fire_bat_dragon","p0_choice":"attack:basic_attack","statuses":[],"skill_usage":{},"after_resolution":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2,"紅竜の炎核":1},"max_hp":40,"gold":701,"healing_hp":310.0,"equipment":["紅玉の護符","革の鎧","氷鉄の大剣"]},"continue":true}},"无同伴":{"n":500,"win_rate":0.634,"rounds_median":20.0,"expected_incoming":4.813809523809524,"expected_healing":0.0,"sustain_coverage":0.0,"sample":{"encounter":"dragon_valley_loc","encounter_class":"boss","status":"victory","rounds":21,"policy":"best_free","before":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":310.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"after_combat":{"hp":27,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":6,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":250.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"actions":{"item:ice_charm":19,"item:healing_scroll":2},"action_specs":{"item:ice_charm":{"type":"item","id":"ice_charm","free":true,"kind":"damage"},"item:healing_scroll":{"type":"item","id":"healing_scroll","free":false,"kind":"heal"}},"consumables":{"治療の巻物":2},"opening":{"expected_damage":4.813809523809524,"variance":35.82390453514739,"cv":1.243361906806332,"ratio":0.12034523809523809,"notes":[]},"expected_healing":0.0,"expected_hp_loss":96.27619047619048,"enemy_phases":20,"companion":null,"p0_choice":"item:ice_charm","statuses":[],"skill_usage":{},"after_resolution":{"hp":27,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":6,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2,"紅竜の炎核":1},"max_hp":40,"gold":701,"healing_hp":250.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"continue":true}}} |
| determinism | {"acceptance_byte_equal":true,"n":500,"seed":20261020,"cells":["P0a/hero","P0a/mage"],"workers":[1,2],"byte_equal":true,"sha256":"132c1085aab6f7fa177b25cc078af4ce83504dea3d19a243ef0d9e7432cad648","elapsed_seconds":65.14214809999976} |
| benchmark | {"exit_code":0,"run_id":"2026-10-23T022309438719Z-intent-gemini-gemini-3.1-flash-lite-guard_rules","live":false,"total":194,"cache_hits":194,"severity":{"S0":173,"S1":12,"S2":8,"S3":1,"S4":0},"baseline":"2026-10-12T062656092753Z-intent-gemini-gemini-3.1-flash-lite-guard_rules","metrics_equal":true} |
| redundancy | {"counts":{"spring":{"supplies":1,"ice_options":7,"holy_options":4,"knows_fort_password":4,"white_dragon_scale":5,"fire_options":4,"frost_trace_seen":1,"heard_human_caused_dragon_return":1,"heard_ignis_last_words":1,"noticed_general_frost":3,"heard_treaty_lore":3,"heard_xanxus_betrayal":2,"purification_knowledge":9,"purification_means":4,"draco_journal":1,"strong_evidence":6,"has_assassin_crest":1},"fort":{"supplies":1,"ice_options":7,"holy_options":4,"knows_fort_password":4,"white_dragon_scale":5,"fire_options":4,"frost_trace_seen":1,"heard_human_caused_dragon_return":1,"heard_ignis_last_words":1,"noticed_general_frost":3,"heard_treaty_lore":3,"heard_xanxus_betrayal":2,"purification_knowledge":9,"purification_means":4,"draco_journal":1,"strong_evidence":6,"has_assassin_crest":1},"cave":{"supplies":1,"ice_options":7,"holy_options":4,"knows_fort_password":4,"white_dragon_scale":5,"fire_options":4,"frost_trace_seen":1,"heard_human_caused_dragon_return":1,"heard_ignis_last_words":1,"noticed_general_frost":3,"heard_treaty_lore":3,"heard_xanxus_betrayal":2,"purification_knowledge":9,"purification_means":4,"draco_journal":1,"strong_evidence":6,"has_assassin_crest":1}},"errors":[]} |
| playtest_normal | {"runs":4,"invariants":{"exceptions":0,"noncombat_dead_ends":0,"fallback_narrations":0},"records":[{"character":"hero","seed":20261013,"steps":77,"ending":"burning_village_defeat","invariants":{"exceptions":0,"noncombat_dead_ends":0,"fallback_narrations":0}},{"character":"cleric","seed":20261013,"steps":90,"ending":"dragon_valley_defeat","invariants":{"exceptions":0,"noncombat_dead_ends":0,"fallback_narrations":0}},{"character":"mage","seed":20261013,"steps":70,"ending":"slime_king_battle_defeat","invariants":{"exceptions":0,"noncombat_dead_ends":0,"fallback_narrations":0}},{"character":"thief","seed":20261013,"steps":73,"ending":"slime_king_battle_defeat","invariants":{"exceptions":0,"noncombat_dead_ends":0,"fallback_narrations":0}}]} |
| playtest_baby | {"runs":4,"invariants":{"exceptions":0,"noncombat_dead_ends":0,"fallback_narrations":0},"records":[{"character":"hero","seed":20261013,"steps":108,"ending":"dragon_valley_defeat","invariants":{"exceptions":0,"noncombat_dead_ends":0,"fallback_narrations":0}},{"character":"cleric","seed":20261013,"steps":153,"ending":"ignis_purified","invariants":{"exceptions":0,"noncombat_dead_ends":0,"fallback_narrations":0}},{"character":"mage","seed":20261013,"steps":73,"ending":"slime_king_battle_defeat","invariants":{"exceptions":0,"noncombat_dead_ends":0,"fallback_narrations":0}},{"character":"thief","seed":20261013,"steps":100,"ending":"draco_defeated","invariants":{"exceptions":0,"noncombat_dead_ends":0,"fallback_narrations":0}}]} |
| baby_playtest_equal_except_fingerprints | true |
| migration | {"command":"python -m scripts.scenario.normal_tuning_052 (twice)","byte_idempotent":true,"unchanged_from_frozen_candidate":true,"file_sha256":{"host\\prompt\\processed\\dragon_rpg.json":"50ac7906d0d55057acc3480e62c6b255e818bde12b37a4277b53ecb25b951deb","host\\prompt\\processed\\dragon_rpg_hybrid.json":"e4741df6a065c5ca299685f7063706b7025e24708e5c5d75c2be1b9d5fa8b4e4","host\\prompt\\processed\\difficulty\\overlay_revision.json":"c98a4cce95a8323248767da1ce7d0492fee7201ece16e71008033da2c78bb80f"}} |
| protected_files_unchanged | {"tests/fixtures/baby_combat_golden.json":"16c88410579747a97310e0302e4e4198eead97b6e6f65a74fe60b8aac5a2e5ca","tests/fixtures/baby_levels_golden.json":"23181b5de8c1bdae27572cf3d76be8cc4b0d4533ed2ad7359b60db8ce2cc46ea","host/prompt/processed/difficulty/baby_numeric_freeze.json":"4aa664923a6e8e277474d35b46c6cf4a321f36591c0b0ba7b19632a09199696a","eval/balance/passive_defaults.json":"02539b0faf59e53ab90c77217d57af03e5cfcda42dd452642393d90d99ab49ef","eval/balance/checkpoints_normal_053.json":"bda2135065964fef303736e2f497852614f48f13bca57b3b405e0b8651d76f67","eval/balance/targets.json":"2705c982577c7f707b2f7c15dcbaa55c4e3ea9f91173e3b7b985b5372aae89e1"} |
| environment_notes | "Original tests/ is not patched; original command is reported as-is. Overlay runner redirects temporary directories through Path.mkdir to avoid Windows tempfile 0700 ACL failures; no permission changes or assertion skips." |
| new_dependencies | 0 |
| paid_api_calls | 0 |


| 运行 | N | seed | 总秒 | 分阶段计时 |
| --- | --- | --- | --- | --- |
| baseline-normal | 500 | 20261020 | 2888.575 | {"workers":12,"branch_proposals":696.1779077000001,"routes":1132.8456722,"preparation_probes":140.47878409999998,"companion_probes":582.9105981999996,"level_probes":166.2542644,"boss_policy_probes":158.88578370000005} |
| baseline-baby | 500 | 20261020 | 1770.926 | {"workers":8,"routes":1143.9570876999999,"preparation_probes":67.7059713000001,"companion_probes":282.33384219999994,"level_probes":78.7547562000002,"boss_policy_probes":124.14160390000006,"human_checkpoint":60.49731259999999} |
| r1-l1 | 200 | 20261022 | 221.644 | {} |
| r2-l2 | 200 | 20261022 | 416.099 | {} |
| r3-l2 | 200 | 20261022 | 410.85 | {} |
| r4-l2 | 200 | 20261022 | 415.856 | {} |
| r5-l1 | 200 | 20261022 | 414.043 | {} |
| acceptance-normal | 500 | 20261020 | 2577.616 | {"workers":4,"branch_proposals":2.245667300000605,"routes":1597.3056157,"preparation_probes":99.41273580000052,"companion_probes":510.8633652999997,"level_probes":211.61639619999914,"boss_policy_probes":143.15143290000015} |
| acceptance-baby | 500 | 20261020 | 809.66 | {"workers":4,"routes":1.4448220999993282,"preparation_probes":0.01297580000027665,"companion_probes":349.8104321999999,"level_probes":134.69775819999995,"boss_policy_probes":235.14674279999963,"human_checkpoint":78.65818880000006} |

验收表中的 elapsed_seconds / timings 是本次恢复运行的墙钟时间，包含读取已完成缓存及补跑的耗时，不包含上轮计算缓存所耗的时间。上轮中断前的阶段计时保留在 acceptance-normal.log / acceptance-baby.log，实际复用数与补跑数见 acceptance-normal-finish.log / acceptance-baby-finish.log；输入指纹复核证据见 finish-resume-provenance.json。

两次N20冒烟仅检验可执行性：r1约24.44秒、r2约34.21秒。分片缓存runner仅包装原worker IPC，输入指纹和job参数哈希保证缓存来源；验收另用原run_jobs的单/多worker比较并对齐验收原记录。

原始产物：`.tmp-test/052a3/{baseline-normal,acceptance-normal,acceptance-baby}.json`、对应 `-records.json`、`-audit.json`、每轮参数/记录/日志。最终 checkpoint 新存 `eval/balance/checkpoints_normal_052.json`，状态为 observed；分支选择保留 proposed 状态，候选数值例外仍待设计裁定。

完整累积补丁 `.tmp-test/052a3/052a3.patch` 已包含 `tests.patch`；二者不要重复应用。manifest记录基准HEAD、文件列表、SHA256、建议提交信息和从HEAD实际应用的逐文件核对结果。建议提交信息：`[工程] 052a normal 数值候选、按等级成长与离线验收`。

## 052b：百分比招式与预告、三场 Boss、049 联动（2026-10-23）

交付状态：**实现候选，数值验收未全部通过**。按 §7.3/§4 C8 停止扩展调参，以下例外均待设计裁定；本报告不把例外视为已批准。任务派发要求只交补丁，不 git add、不提交、不写 .git。

基线为已合入的 052a3 acceptance-normal（N=500，seed=20261020），本段评估 N=500、probe-n=500、冻结被动 v1；没有重新穷举。第 0 步归因沿用上一节：F6 是可恢复的屋敷失败结局需要继续路线，现有修复及历史固定种子回归保留。

052b 的战斗表使用实际 P2 中位等级开场快照，保留开场 HP/资源，回合中位含胜败；因此低回合也可能意味着快速败北。无快照只记未验证。M9 按 2026-10-23 裁定，以每遭遇四职业平均判定，教程只报告、洞窟/砦允许上限 +0.05（goblin_fort_fourth 除外）。

最终P2 heuristic_v3探针：虹晶樹四职业回合中位12/9/7/13，Ignis为9/7/7/10，均≤14；ドラコ为12/27/11/34，僧侶与盗賊仍超限，盗賊该固定开场快照胜率为0，不能用低胜率豁免heuristic行。整路线与固定快照资源分布不同，必须分别看胜率。

### 门槛前后对照

| 指标 | 052a 调参后 | 052b 候选 | 说明 |
|---|---|---|---|
| M1 | pass | pass | 冒険完了为主口径；试玩 checkpoint 不计入原型门槛。 |
| M1' | report | report | 分别以 P0a、P0b 检查 P0→P1，避免自行合并两种 P0。 |
| M2 | report | report | 准备清单为 proposed；净化按达成目标遭遇成功计（victory/purified）。 |
| M3 | pass | pass | 可持续回复能力（未扣过量回复）/开场完整敌方每回合期望伤害；消耗品计入 M3'。 |
| M3' | report | report | 击杀回合只取胜利/净化样本；失败为右删失。耗尽按当前 HP+库存回复与净开场伤害估计；有限 MP/SP 主动回复未换算进此静态资源池，实际使用仍影响击杀回合。净伤害≤0时耗尽为无限，赛跑比0。 |
| M4 | fail | fail | 详见原始 JSON |
| M5 | report | report | 只统计到达最终 Boss 的 P1；道具使用率=消耗/(消耗+结余)，金币含开局支给。 |
| M6 | report | report | 详见原始 JSON |
| M7 | report | report | 成对普通成功/失败分支，沿真实后果打完被迫战斗后比较 resource_score；不是观察性分组，也不估整路线通关差。 |
| M8 | report | report | 每职业/每同伴/每 Boss，与同配置无同伴成对比较；负提升也保留。 |
| M9 | fail | fail | 052 acceptance: arithmetic mean of four classes per encounter; incomplete snapshots unverified; tutorial report only. |
| M10 | report | report | Engine attack_chance/actor_evade, enemy accuracy override and current statuses. Direct damage only; DoT separate. |
| M11 | report | report | 在实际轨迹每次敌方阶段按当时存活敌人精确求期望并求和；不减回复，保留防御/抗性实际作用。 |
| M12 | report | report | 95% paired CI excludes zero defines better; dead only within observed/reachable matrix. Unreached levels are unavailable, not dead. Same-group gaps use absolute P2 Ignis pp; proposed defaults await design approval. |
| M13 | report | report | Engine EXP growth with active unlocks and table passives; arrival levels exclude Ignis EXP. Missing arrivals cannot certify the gap. |

| 专项 | 前 | 后 | 状态 |
|---|---|---|---|
| 到达等级 | 见052a已批准例外 | {"report":9,"pass":19} | 按新裁定逐格检查 |
| M4 ≤14 | 6 个超限 | 17 个超限 | 含全部路线与checkpoint探针，未全部通过 |
| M9 四职业平均 | {"tutorial_report":1,"approved_optional":2,"pass":14,"fail":3,"unverified":16} | {"tutorial_report":1,"approved_optional":3,"pass":14,"fail":2,"unverified":16} | 旧数据按新口径重算 |
| 049 A 八组合 | 049已批准门槛 | 81.30%–84.95% | 通过 |
| 换剑整路线差 | 未测 | -19.20% | 软门槛失败 |
| Lv1 虹晶樹 <35% | 既有要求 | {"hero":0.0,"cleric":0.0,"mage":0.132,"thief":0.0} | 详见专项 |
| baby/normal空覆盖战斗金标 | 113项 | 113项；SHA256 14d374747913957829d5162d7aa6d52dfd3ce9ec9b3f8560d1e5f96f0fd1caee | 通过 |
| 冻结 benchmark | 194/194 | 194/194 缓存命中、严重度不变、live=false | 通过 |

### 28 格前后对照

| 原型 | 职业 | 通关 | Ignis | 终局（含失败） | Ignis回合中位 |
|---|---|---|---|---|---|
| P0a | hero | 0.00% → 0.00% | 0.00% → 0.00% | 100.00% → 100.00% | None → 3.5 |
| P0a | cleric | 0.00% → 0.00% | 0.00% → 0.00% | 100.00% → 100.00% | None → 7 |
| P0a | mage | 0.00% → 0.00% | 0.00% → 0.00% | 100.00% → 100.00% | None → None |
| P0a | thief | 0.00% → 0.00% | 0.00% → 0.00% | 100.00% → 100.00% | None → 2 |
| P0b | hero | 0.00% → 3.20% | 0.00% → 3.20% | 100.00% → 100.00% | 3 → 8 |
| P0b | cleric | 0.00% → 0.80% | 0.00% → 0.80% | 100.00% → 100.00% | 4.0 → 5.0 |
| P0b | mage | 0.00% → 0.00% | 0.00% → 0.00% | 100.00% → 100.00% | None → 2 |
| P0b | thief | 0.00% → 1.00% | 0.00% → 1.00% | 100.00% → 100.00% | 1.0 → 4.0 |
| P1 | hero | 0.60% → 21.20% | 0.60% → 21.20% | 100.00% → 100.00% | 5 → 14 |
| P1 | cleric | 0.40% → 13.40% | 0.40% → 13.40% | 100.00% → 100.00% | 4.0 → 8 |
| P1 | mage | 0.20% → 2.40% | 0.20% → 2.40% | 100.00% → 100.00% | 2 → 2.0 |
| P1 | thief | 0.00% → 3.20% | 0.00% → 3.20% | 100.00% → 100.00% | 4 → 5 |
| P2 | hero | 51.60% → 69.20% | 73.80% → 97.60% | 100.00% → 100.00% | 11 → 10.0 |
| P2 | cleric | 48.40% → 68.40% | 48.80% → 74.60% | 99.60% → 99.20% | 7 → 9.0 |
| P2 | mage | 3.00% → 49.80% | 9.40% → 55.60% | 99.80% → 100.00% | 5 → 6 |
| P2 | thief | 3.40% → 40.60% | 6.40% → 47.00% | 100.00% → 100.00% | 4 → 10 |
| P3 | hero | 11.40% → 47.40% | 16.80% → 53.20% | 100.00% → 100.00% | 9 → 15 |
| P3 | cleric | 0.00% → 13.60% | 0.80% → 14.20% | 99.80% → 100.00% | 9 → 12 |
| P3 | mage | 2.80% → 43.60% | 7.40% → 47.60% | 99.80% → 99.80% | 5 → 6.0 |
| P3 | thief | 0.00% → 11.80% | 2.00% → 18.60% | 100.00% → 99.80% | 4.5 → 11.0 |
| P2s | hero | 47.60% → 67.40% | 76.80% → 98.00% | 100.00% → 100.00% | 11 → 10 |
| P2s | cleric | 33.40% → 65.60% | 43.60% → 76.80% | 99.60% → 100.00% | 7.0 → 7 |
| P2s | mage | 1.20% → 41.40% | 5.80% → 46.80% | 99.60% → 100.00% | 4 → 6 |
| P2s | thief | 4.40% → 41.40% | 6.20% → 46.60% | 100.00% → 100.00% | 5 → 10 |
| P0g | hero | 0.00% → 3.20% | 0.00% → 3.20% | 100.00% → 100.00% | 3 → 8 |
| P0g | cleric | 0.00% → 0.80% | 0.00% → 0.80% | 100.00% → 100.00% | 4.0 → 5.0 |
| P0g | mage | 0.00% → 0.00% | 0.00% → 0.00% | 100.00% → 100.00% | None → 2 |
| P0g | thief | 0.00% → 1.00% | 0.00% → 1.00% | 100.00% → 100.00% | 1.0 → 4.0 |

| 原型 | 职业 | 通关Wilson95 前→后 | Ignis Wilson95 前→后 | 终局Wilson95 前→后 |
|---|---|---|---|---|
| P0a | hero | [0.00%, 0.76%] → [0.00%, 0.76%] | [0.00%, 0.76%] → [0.00%, 0.76%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P0a | cleric | [0.00%, 0.76%] → [0.00%, 0.76%] | [0.00%, 0.76%] → [0.00%, 0.76%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P0a | mage | [0.00%, 0.76%] → [0.00%, 0.76%] | [0.00%, 0.76%] → [0.00%, 0.76%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P0a | thief | [0.00%, 0.76%] → [0.00%, 0.76%] | [0.00%, 0.76%] → [0.00%, 0.76%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P0b | hero | [0.00%, 0.76%] → [1.98%, 5.13%] | [0.00%, 0.76%] → [1.98%, 5.13%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P0b | cleric | [0.00%, 0.76%] → [0.31%, 2.04%] | [0.00%, 0.76%] → [0.31%, 2.04%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P0b | mage | [0.00%, 0.76%] → [0.00%, 0.76%] | [0.00%, 0.76%] → [0.00%, 0.76%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P0b | thief | [0.00%, 0.76%] → [0.43%, 2.32%] | [0.00%, 0.76%] → [0.43%, 2.32%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P1 | hero | [0.20%, 1.75%] → [17.84%, 25.00%] | [0.20%, 1.75%] → [17.84%, 25.00%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P1 | cleric | [0.11%, 1.45%] → [10.69%, 16.67%] | [0.11%, 1.45%] → [10.69%, 16.67%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P1 | mage | [0.04%, 1.12%] → [1.38%, 4.15%] | [0.04%, 1.12%] → [1.38%, 4.15%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P1 | thief | [0.00%, 0.76%] → [1.98%, 5.13%] | [0.00%, 0.76%] → [1.98%, 5.13%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P2 | hero | [47.22%, 55.95%] → [65.02%, 73.09%] | [69.77%, 77.46%] → [95.85%, 98.62%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P2 | cleric | [44.05%, 52.78%] → [64.20%, 72.32%] | [44.44%, 53.17%] → [70.61%, 78.22%] | [98.55%, 99.89%] → [97.96%, 99.69%] |
| P2 | mage | [1.83%, 4.89%] → [45.44%, 54.17%] | [7.14%, 12.28%] → [51.22%, 59.90%] | [98.88%, 99.96%] → [99.24%, 100.00%] |
| P2 | thief | [2.13%, 5.38%] → [36.38%, 44.96%] | [4.57%, 8.90%] → [42.66%, 51.38%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P3 | hero | [8.90%, 14.48%] → [43.06%, 51.78%] | [13.78%, 20.33%] → [48.82%, 57.53%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P3 | cleric | [0.00%, 0.76%] → [10.87%, 16.88%] | [0.31%, 2.04%] → [11.41%, 17.53%] | [98.88%, 99.96%] → [99.24%, 100.00%] |
| P3 | mage | [1.68%, 4.64%] → [39.32%, 47.98%] | [5.42%, 10.03%] → [43.26%, 51.98%] | [98.88%, 99.96%] → [98.88%, 99.96%] |
| P3 | thief | [0.00%, 0.76%] → [9.26%, 14.92%] | [1.09%, 3.64%] → [15.43%, 22.25%] | [99.24%, 100.00%] → [98.88%, 99.96%] |
| P2s | hero | [43.26%, 51.98%] → [63.17%, 71.36%] | [72.90%, 80.29%] → [96.36%, 98.91%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P2s | cleric | [29.41%, 37.65%] → [61.33%, 69.63%] | [39.32%, 47.98%] → [72.90%, 80.29%] | [98.55%, 99.89%] → [99.24%, 100.00%] |
| P2s | mage | [0.55%, 2.59%] → [37.16%, 45.77%] | [4.07%, 8.21%] → [42.47%, 51.18%] | [98.55%, 99.89%] → [99.24%, 100.00%] |
| P2s | thief | [2.92%, 6.57%] → [37.16%, 45.77%] | [4.40%, 8.67%] → [42.27%, 50.98%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P0g | hero | [0.00%, 0.76%] → [1.98%, 5.13%] | [0.00%, 0.76%] → [1.98%, 5.13%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P0g | cleric | [0.00%, 0.76%] → [0.31%, 2.04%] | [0.00%, 0.76%] → [0.31%, 2.04%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P0g | mage | [0.00%, 0.76%] → [0.00%, 0.76%] | [0.00%, 0.76%] → [0.00%, 0.76%] | [99.24%, 100.00%] → [99.24%, 100.00%] |
| P0g | thief | [0.00%, 0.76%] → [0.43%, 2.32%] | [0.00%, 0.76%] → [0.43%, 2.32%] | [99.24%, 100.00%] → [99.24%, 100.00%] |

| 原型 | 职业 | 通关软目标 | 前→后判定 |
|---|---|---|---|
| P1 | hero | (0.15, 0.35) | 未达 → 通过 |
| P1 | cleric | (0.15, 0.35) | 未达 → 未达 |
| P1 | mage | (0.15, 0.35) | 未达 → 未达 |
| P1 | thief | (0.15, 0.35) | 未达 → 未达 |
| P2 | hero | (0.55, 0.75) | 未达 → 通过 |
| P2 | cleric | (0.55, 0.75) | 未达 → 通过 |
| P2 | mage | (0.55, 0.75) | 未达 → 未达 |
| P2 | thief | (0.55, 0.75) | 未达 → 未达 |
| P3 | hero | (0.8, 1) | 未达 → 未达 |
| P3 | cleric | (0.8, 1) | 未达 → 未达 |
| P3 | mage | (0.8, 1) | 未达 → 未达 |
| P3 | thief | (0.8, 1) | 未达 → 未达 |

P2s 与P2前后：[{"character":"hero","completion_gap_pp":4.0000000000000036,"level_gaps":{"castle":0,"cave_crystal_corridor":0,"cave_heat_corridor":0.18894009216589858,"cave_lava_room":0.12096774193548399,"cave_prism_tree":0,"dark_forest_loc":0,"draco_battle":0.11197916666666696,"dragon_valley_loc":0,"elf_spring":0.20362903225806495,"forest_exit":0.07459677419354804,"forest_wolves":0.0020408163265308588,"frost_wolf_battle":0.004032258064516014,"goblin_fort":0,"goblin_fort_first_second":0,"goblin_fort_fourth":0.21399999999999997,"goblin_fort_second_right":0.00209523809523815,"ian_ice_katana_aftermath":0,"ice_elemental_encounter":0,"royal_gate":0.8022738821138207,"slime_ambush_one":0.5271477946017109,"slime_ambush_two":0.5271477946017109,"slime_king_battle":0.6220128373930223,"valley_entrance":0,"village_fire_elemental":0.06293706293706336,"village_fire_slime":0.08024691358024683,"village_frozen_clue":0.05645161290322598},"meets_draft":true,"missing_nodes":[]},{"character":"cleric","completion_gap_pp":14.999999999999996,"level_gaps":{"castle":0,"cave_crystal_corridor":0,"cave_heat_corridor":0.17676767676767646,"cave_lava_room":0.08314087759815258,"cave_prism_tree":0,"dark_forest_loc":0,"draco_battle":0.744585651977741,"dragon_valley_loc":0,"elf_spring":0.16397228637413352,"forest_exit":0.0690690690690694,"forest_wolves":0.0050890585241729624,"frost_wolf_battle":0.0030120481927706777,"goblin_fort":0,"goblin_fort_first_second":0,"goblin_fort_fourth":0.242,"goblin_fort_second_right":0.001731343283582154,"ian_ice_katana_aftermath":0,"ice_elemental_encounter":0,"royal_gate":0,"slime_ambush_one":0.5540929473909992,"slime_ambush_two":0.5540929473909992,"slime_king_battle":0.636660198823817,"valley_entrance":0,"village_fire_elemental":0.11904761904761862,"village_fire_slime":0.06181818181818155,"village_frozen_clue":0.05722891566265087},"meets_draft":false,"missing_nodes":[]},{"character":"mage","completion_gap_pp":1.7999999999999998,"level_gaps":{"castle":0,"cave_crystal_corridor":0,"cave_heat_corridor":0.09433962264150964,"cave_lava_room":0.048850574712643535,"cave_prism_tree":0,"dark_forest_loc":0,"draco_battle":0.2758620689655169,"dragon_valley_loc":0,"elf_spring":0.09195402298850563,"forest_exit":0.10196131968145661,"forest_wolves":0.0585106382978724,"frost_wolf_battle":0.006849315068492956,"goblin_fort":0,"goblin_fort_first_second":0,"goblin_fort_fourth":0.22044088176352705,"goblin_fort_second_right":0.010147601476014678,"ian_ice_katana_aftermath":0,"ice_elemental_encounter":0,"royal_gate":0.7234042553191493,"slime_ambush_one":0.4618127683146378,"slime_ambush_two":0.4618127683146378,"slime_king_battle":0.5419609472372251,"valley_entrance":0,"village_fire_elemental":0.04166666666666696,"village_fire_slime":0.11361902834638293,"village_frozen_clue":0.09589041095890405},"meets_draft":true,"missing_nodes":[]},{"character":"thief","completion_gap_pp":0.9999999999999996,"level_gaps":{"castle":0,"cave_crystal_corridor":0,"cave_lava_room":0.4194528875379939,"cave_prism_tree":0,"dark_forest_loc":0,"draco_battle":0.41935483870967705,"dragon_valley_loc":0,"elf_spring":0.4194528875379939,"forest_exit":0.27610922451706355,"frost_wolf_battle":0.01195219123505975,"goblin_fort":0,"goblin_fort_first_second":0,"goblin_fort_fourth":0.252,"goblin_fort_second_right":0.0030389610389611743,"ian_ice_katana_aftermath":0,"ice_elemental_encounter":0.03418974976582412,"royal_gate":0.625,"slime_ambush_one":0.2606232294617561,"slime_ambush_two":0.2606232294617561,"slime_king_battle":0.40205963646383136,"valley_entrance":0,"village_fire_elemental":0.2956841138659323,"village_fire_slime":0.27783260955388833,"village_frozen_clue":0.19206860501257328},"meets_draft":true,"missing_nodes":["cave_heat_corridor","forest_wolves"]}] → [{"character":"hero","completion_gap_pp":1.7999999999999905,"level_gaps":{"castle":0,"cave_crystal_corridor":0,"cave_heat_corridor":0.46190476190476204,"cave_lava_room":0.27878787878787836,"cave_prism_tree":0,"dark_forest_loc":0,"draco_battle":0.2632653061224488,"dragon_valley_loc":0,"elf_spring":0.4747474747474749,"forest_exit":0.33333333333333304,"forest_wolves":0.07459677419354804,"frost_wolf_battle":0.020202020202019888,"goblin_fort":0,"goblin_fort_first_second":0,"goblin_fort_fourth":0.3400000000000001,"goblin_fort_second_right":0,"ian_ice_katana_aftermath":0.0020202020202022553,"ice_elemental_encounter":0.008968609865470434,"royal_gate":0.6290983606557381,"slime_ambush_one":0,"slime_ambush_two":0.19958455522971708,"slime_king_battle":0.5947091886608016,"valley_entrance":0.0020202020202022553,"village_fire_elemental":0.3311258278145699,"village_fire_slime":0.33865814696485597,"village_frozen_clue":0.2424242424242422},"meets_draft":true,"missing_nodes":[]},{"character":"cleric","completion_gap_pp":2.8000000000000025,"level_gaps":{"castle":0,"cave_crystal_corridor":0,"cave_heat_corridor":0.48241206030150785,"cave_lava_room":0.22737306843267113,"cave_prism_tree":0,"dark_forest_loc":0,"draco_battle":0.7364415773011617,"dragon_valley_loc":0,"elf_spring":0.43929359823399583,"forest_exit":0.22329220250330994,"forest_wolves":0.2251131221719458,"frost_wolf_battle":0.00731707317073127,"goblin_fort":0,"goblin_fort_first_second":0,"goblin_fort_fourth":0.3560000000000001,"goblin_fort_second_right":0,"ian_ice_katana_aftermath":0,"ice_elemental_encounter":0.009345794392523032,"royal_gate":0.46648793565683633,"slime_ambush_one":0,"slime_ambush_two":0.21141569485940348,"slime_king_battle":0.6280100783412044,"valley_entrance":0,"village_fire_elemental":0.24868421052631628,"village_fire_slime":0.21994134897360684,"village_frozen_clue":0.13932577998548812},"meets_draft":true,"missing_nodes":[]},{"character":"mage","completion_gap_pp":8.400000000000002,"level_gaps":{"castle":0,"cave_crystal_corridor":0,"cave_heat_corridor":0.3612903225806452,"cave_lava_room":0.23711340206185572,"cave_prism_tree":0,"dark_forest_loc":0,"draco_battle":0.24066900325893137,"dragon_valley_loc":0,"elf_spring":0.3814432989690726,"forest_exit":0.23710806939360207,"forest_wolves":0.07524271844660202,"frost_wolf_battle":0.01098901098901095,"goblin_fort":0,"goblin_fort_first_second":0,"goblin_fort_fourth":0.3270763052208836,"goblin_fort_second_right":0,"ian_ice_katana_aftermath":0,"ice_elemental_encounter":0.06666666666666643,"royal_gate":0.6762589928057556,"slime_ambush_one":0.002577319587628857,"slime_ambush_two":0.2009343537989814,"slime_king_battle":0.6309061058934304,"valley_entrance":0,"village_fire_elemental":0.2278481012658231,"village_fire_slime":0.24347968852612834,"village_frozen_clue":0.1654516215491828},"meets_draft":true,"missing_nodes":[]},{"character":"thief","completion_gap_pp":0.7999999999999952,"level_gaps":{"castle":0,"cave_crystal_corridor":0,"cave_lava_room":0.6489361702127656,"cave_prism_tree":0,"dark_forest_loc":0,"draco_battle":0.47646790247465987,"dragon_valley_loc":0,"elf_spring":0.6489361702127656,"forest_exit":0.4477208259119996,"frost_wolf_battle":0.02218730776264799,"goblin_fort":0,"goblin_fort_first_second":0,"goblin_fort_fourth":0.28800000000000003,"goblin_fort_second_right":0,"ian_ice_katana_aftermath":0,"ice_elemental_encounter":0.019751827298996716,"royal_gate":0.506382978723404,"slime_ambush_one":0.0026595744680850686,"slime_ambush_two":0.04048463356973997,"slime_king_battle":0.31471631205673756,"valley_entrance":0,"village_fire_elemental":0.44732891832229615,"village_fire_slime":0.4694949104496837,"village_frozen_clue":0.31857071795722103},"meets_draft":true,"missing_nodes":["cave_heat_corridor","forest_wolves"]}]

P2职业差（依Q16不计魔法使い）：48.20% → 28.60%；软目标≤20pp。

| 原型 | 职业 | 到达数/500 | 到达等级分布 前→后 | EXP 来源均值 前→后 |
|---|---|---|---|---|
| P0a | hero | 0 → 4 | {} → {"5":4} | {} → {"trash":16,"elite":36,"boss":50,"unclassified":0,"quest":0} |
| P0a | cleric | 0 → 1 | {} → {"5":1} | {} → {"trash":16,"elite":36,"boss":50,"unclassified":0,"quest":0} |
| P0a | mage | 0 → 0 | {} → {} | {} → {} |
| P0a | thief | 0 → 1 | {} → {"4":1} | {} → {"trash":8,"elite":36,"boss":25,"unclassified":0,"quest":0} |
| P0b | hero | 25 → 105 | {"4":25} → {"4":103,"5":2} | {"trash":7.68,"elite":36,"boss":25,"unclassified":0,"quest":0} → {"trash":7.542857142857143,"elite":36.68571428571428,"boss":25.476190476190474,"unclassified":0,"quest":0} |
| P0b | cleric | 4 → 54 | {"4":4} → {"4":54} | {"trash":8,"elite":36,"boss":25,"unclassified":0,"quest":0} → {"trash":6.814814814814815,"elite":39.55555555555556,"boss":25,"unclassified":0,"quest":0} |
| P0b | mage | 0 → 7 | {} → {"4":7} | {} → {"trash":6.857142857142857,"elite":36,"boss":25,"unclassified":0,"quest":0} |
| P0b | thief | 4 → 60 | {"4":4} → {"4":58,"5":2} | {"trash":8,"elite":36,"boss":25,"unclassified":0,"quest":0} → {"trash":7.6,"elite":37.6,"boss":25.833333333333332,"unclassified":0,"quest":0} |
| P1 | hero | 209 → 237 | {"4":2,"5":207} → {"4":10,"5":227} | {"trash":7.961722488038277,"elite":36,"boss":25,"unclassified":0,"quest":29.71291866028708} → {"trash":7.662447257383966,"elite":36.81012658227848,"boss":25.31645569620253,"unclassified":0,"quest":28.734177215189874} |
| P1 | cleric | 50 → 215 | {"5":50} → {"4":5,"5":210} | {"trash":8,"elite":36,"boss":25,"unclassified":0,"quest":30} → {"trash":6.865116279069768,"elite":39.12558139534884,"boss":25,"unclassified":0,"quest":29.302325581395348} |
| P1 | mage | 21 → 72 | {"5":21} → {"4":1,"5":71} | {"trash":8.380952380952381,"elite":36,"boss":26.19047619047619,"unclassified":0,"quest":30} → {"trash":9.055555555555555,"elite":37.333333333333336,"boss":29.86111111111111,"unclassified":0,"quest":29.583333333333332} |
| P1 | thief | 59 → 145 | {"4":8,"5":51} → {"4":8,"5":137} | {"trash":7.186440677966102,"elite":36.813559322033896,"boss":25,"unclassified":0,"quest":25.93220338983051} → {"trash":7.337931034482758,"elite":38.48275862068966,"boss":26.20689655172414,"unclassified":0,"quest":28.344827586206897} |
| P2 | hero | 487 → 496 | {"6":487} → {"6":496} | {"trash":16.229979466119097,"elite":94.69404517453799,"boss":99.84599589322382,"unclassified":0,"quest":88.52156057494867} → {"trash":18.427419354838708,"elite":87.7258064516129,"boss":94.90927419354838,"unclassified":0,"quest":87.94354838709677} |
| P2 | cleric | 333 → 408 | {"6":333} → {"6":408} | {"trash":17.177177177177178,"elite":93.04504504504504,"boss":98.94894894894895,"unclassified":0,"quest":88.91891891891892} → {"trash":19.49019607843137,"elite":85.6470588235294,"boss":97.48774509803921,"unclassified":0,"quest":88.8970588235294} |
| P2 | mage | 265 → 393 | {"6":265} → {"6":393} | {"trash":17.071698113207546,"elite":93.05660377358491,"boss":95,"unclassified":0,"quest":88.75471698113208} → {"trash":19.69465648854962,"elite":85.31297709923665,"boss":94.46564885496183,"unclassified":0,"quest":89.00763358778626} |
| P2 | thief | 231 → 343 | {"6":231} → {"6":343} | {"trash":15.151515151515152,"elite":91.42857142857143,"boss":95.88744588744589,"unclassified":0,"quest":88.57142857142857} → {"trash":16.291545189504372,"elite":87.00874635568513,"boss":91.98250728862973,"unclassified":0,"quest":88.42565597667638} |
| P3 | hero | 223 → 325 | {"7":223} → {"7":325} | {"trash":21.757847533632287,"elite":117.4170403587444,"boss":167.60089686098655,"unclassified":0,"quest":320.1793721973094} → {"trash":23.286153846153844,"elite":110.06769230769231,"boss":162.30769230769232,"unclassified":0,"quest":313.38461538461536} |
| P3 | cleric | 11 → 79 | {"7":11} → {"7":79} | {"trash":22.181818181818183,"elite":120,"boss":179.54545454545453,"unclassified":0,"quest":305.45454545454544} → {"trash":23.746835443037973,"elite":108.60759493670886,"boss":167.72151898734177,"unclassified":0,"quest":319.746835443038} |
| P3 | mage | 89 → 286 | {"7":86,"8":3} → {"7":286} | {"trash":22.696629213483146,"elite":115.68539325842697,"boss":184.26966292134833,"unclassified":0,"quest":310.44943820224717} → {"trash":23.524475524475523,"elite":109.3006993006993,"boss":192.13286713286712,"unclassified":0,"quest":318.041958041958} |
| P3 | thief | 70 → 192 | {"7":70} → {"7":192} | {"trash":20.17142857142857,"elite":114.17142857142858,"boss":145.35714285714286,"unclassified":0,"quest":294} → {"trash":21.541666666666668,"elite":110.5,"boss":153.90625,"unclassified":0,"quest":302.34375} |
| P2s | hero | 493 → 495 | {"6":493} → {"6":495} | {"trash":16.275862068965516,"elite":48.121703853955374,"boss":100,"unclassified":0,"quest":88.29614604462475} → {"trash":18.48080808080808,"elite":41.696969696969695,"boss":95.20202020202021,"unclassified":0,"quest":88.12121212121212} |
| P2s | cleric | 302 → 401 | {"6":302} → {"6":401} | {"trash":17.178807947019866,"elite":44.58278145695364,"boss":99.58609271523179,"unclassified":0,"quest":88.6092715231788} → {"trash":19.321695760598505,"elite":37.61596009975062,"boss":98.75311720698254,"unclassified":0,"quest":88.50374064837905} |
| P2s | mage | 209 → 347 | {"6":209} → {"6":347} | {"trash":17.129186602870814,"elite":41.97129186602871,"boss":97.96650717703349,"unclassified":0,"quest":87.99043062200957} → {"trash":19.239193083573486,"elite":34.65129682997118,"boss":98.19884726224784,"unclassified":0,"quest":88.35734870317003} |
| P2s | thief | 217 → 297 | {"6":217} → {"6":297} | {"trash":15.133640552995391,"elite":35.28110599078341,"boss":97.11981566820276,"unclassified":0,"quest":88.20276497695852} → {"trash":15.919191919191919,"elite":33.21212121212121,"boss":94.78114478114477,"unclassified":0,"quest":88.18181818181819} |
| P0g | hero | 25 → 105 | {"4":25} → {"4":103,"5":2} | {"trash":7.68,"elite":36,"boss":25,"unclassified":0,"quest":0} → {"trash":7.542857142857143,"elite":36.68571428571428,"boss":25.476190476190474,"unclassified":0,"quest":0} |
| P0g | cleric | 4 → 54 | {"4":4} → {"4":54} | {"trash":8,"elite":36,"boss":25,"unclassified":0,"quest":0} → {"trash":6.814814814814815,"elite":39.55555555555556,"boss":25,"unclassified":0,"quest":0} |
| P0g | mage | 0 → 7 | {} → {"4":7} | {} → {"trash":6.857142857142857,"elite":36,"boss":25,"unclassified":0,"quest":0} |
| P0g | thief | 4 → 60 | {"4":4} → {"4":58,"5":2} | {"trash":8,"elite":36,"boss":25,"unclassified":0,"quest":0} → {"trash":7.6,"elite":37.6,"boss":25.833333333333332,"unclassified":0,"quest":0} |

| 原型 | 职业 | 目标 | 众数 | 目标级占比/Wilson95 | 最高 | 判定 |
|---|---|---|---|---|---|---|
| P0a | hero | 4 | 5 | 0.00% [0.00%, 48.99%] | 5 | report |
| P0a | cleric | 4 | 5 | 0.00% [0.00%, 79.35%] | 5 | report |
| P0a | mage | 4 | None | 未验证 未验证 | None | report |
| P0a | thief | 4 | 4 | 100.00% [20.65%, 100.00%] | 4 | report |
| P0b | hero | 4 | 4 | 98.10% [93.32%, 99.48%] | 5 | pass |
| P0b | cleric | 4 | 4 | 100.00% [93.36%, 100.00%] | 4 | pass |
| P0b | mage | 4 | 4 | 100.00% [64.57%, 100.00%] | 4 | report |
| P0b | thief | 4 | 4 | 96.67% [88.64%, 99.08%] | 5 | pass |
| P1 | hero | 5 | 5 | 95.78% [92.41%, 97.69%] | 5 | pass |
| P1 | cleric | 5 | 5 | 97.67% [94.67%, 99.00%] | 5 | pass |
| P1 | mage | 5 | 5 | 98.61% [92.54%, 99.75%] | 5 | pass |
| P1 | thief | 5 | 5 | 94.48% [89.49%, 97.18%] | 5 | pass |
| P2 | hero | 6 | 6 | 100.00% [99.23%, 100.00%] | 6 | pass |
| P2 | cleric | 6 | 6 | 100.00% [99.07%, 100.00%] | 6 | pass |
| P2 | mage | 6 | 6 | 100.00% [99.03%, 100.00%] | 6 | pass |
| P2 | thief | 6 | 6 | 100.00% [98.89%, 100.00%] | 6 | pass |
| P3 | hero | 7 | 7 | 100.00% [98.83%, 100.00%] | 7 | pass |
| P3 | cleric | 7 | 7 | 100.00% [95.36%, 100.00%] | 7 | pass |
| P3 | mage | 7 | 7 | 100.00% [98.67%, 100.00%] | 7 | pass |
| P3 | thief | 7 | 7 | 100.00% [98.04%, 100.00%] | 7 | pass |
| P2s | hero | 6 | 6 | 100.00% [99.23%, 100.00%] | 6 | pass |
| P2s | cleric | 6 | 6 | 100.00% [99.05%, 100.00%] | 6 | pass |
| P2s | mage | 6 | 6 | 100.00% [98.91%, 100.00%] | 6 | pass |
| P2s | thief | 6 | 6 | 100.00% [98.72%, 100.00%] | 6 | pass |
| P0g | hero | 4 | 4 | 98.10% [93.32%, 99.48%] | 5 | report |
| P0g | cleric | 4 | 4 | 100.00% [93.36%, 100.00%] | 4 | report |
| P0g | mage | 4 | 4 | 100.00% [64.57%, 100.00%] | 4 | report |
| P0g | thief | 4 | 4 | 96.67% [88.64%, 99.08%] | 5 | report |

### M9 逐遭遇与单职业辅助值

缺快照（遭遇/职业）：{"merchant_battle":["hero","cleric","mage","thief"],"lost_goblin_crossroads":["hero","cleric","mage","thief"],"goblin_fort_second_left":["hero","cleric","mage","thief"],"goblin_fort_third_guards":["hero","cleric","mage","thief"],"goblin_fort_chest_fight":["hero","cleric","mage","thief"],"valley_ledge":["hero","cleric","mage","thief"],"xanxus_phantom_battle":["hero","cleric","mage","thief"],"mansion_corridor":["hero","cleric","mage","thief"],"inn_night_ambush":["hero","cleric","mage","thief"],"bone_field":["hero","cleric","mage","thief"],"ghoul_marsh":["hero","cleric","mage","thief"],"grave_chapel":["hero","cleric","mage","thief"],"gorge_rockfall_path":["hero","cleric","mage","thief"],"gorge_giant_path":["hero","cleric","mage","thief"],"gorge_worm_lair":["hero","cleric","mage","thief"],"dragon_valley_return":["hero","cleric","mage","thief"]}

| 遭遇 | 分类 | 前四职业均值 | 后四职业均值 | 后状态 | 后单职业 ratio / 含盾 / 前3轮 |
|---|---|---|---|---|---|
| bone_field | trash | 未验证 | 未验证 | unverified | [] |
| cave_crystal_corridor | elite | 27.23% | 25.42% | approved_optional | [{"character":"hero","ratio":0.22229166666666664,"with_shields":0.22229166666666664,"first_three":0.18187499999999998,"first_three_with_shields":0.18187499999999998,"observed_rounds":3},{"character":"cleric","ratio":0.25240740740740736,"with_shields":0.25240740740740736,"first_three":0.25240740740740736,"first_three_with_shields":0.25240740740740736,"observed_rounds":3},{"character":"mage","ratio":0.308989898989899,"with_shields":0.0,"first_three":0.2811111111111111,"first_three_with_shields":0.17811447811447811,"observed_rounds":3},{"character":"thief","ratio":0.23295454545454544,"with_shields":0.23295454545454544,"first_three":0.2102272727272727,"first_three_with_shields":0.2102272727272727,"observed_rounds":3}] |
| cave_heat_corridor | elite | 19.34% | 21.66% | pass | [{"character":"hero","ratio":0.15839965277777776,"with_shields":0.15839965277777776,"first_three":0.13254421296296295,"first_three_with_shields":0.13254421296296295,"observed_rounds":3},{"character":"cleric","ratio":0.24739407407407402,"with_shields":0.24739407407407402,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"mage","ratio":0.27878787878787875,"with_shields":0.0,"first_three":0.2323232323232323,"first_three_with_shields":0.13939393939393938,"observed_rounds":3},{"character":"thief","ratio":0.18181818181818182,"with_shields":0.18181818181818182,"first_three":0.18181818181818182,"first_three_with_shields":0.18181818181818182,"observed_rounds":3}] |
| cave_lava_room | elite | 35.50% | 35.50% | fail | [{"character":"hero","ratio":0.2208482142857143,"with_shields":0.2208482142857143,"first_three":0.14723214285714287,"first_three_with_shields":0.14723214285714287,"observed_rounds":3},{"character":"cleric","ratio":0.37599999999999995,"with_shields":0.37599999999999995,"first_three":0.25066666666666665,"first_three_with_shields":0.25066666666666665,"observed_rounds":3},{"character":"mage","ratio":0.5018181818181818,"with_shields":0.0,"first_three":0.33454545454545453,"first_three_with_shields":0.16727272727272727,"observed_rounds":3},{"character":"thief","ratio":0.3214285714285714,"with_shields":0.3214285714285714,"first_three":null,"first_three_with_shields":null,"observed_rounds":1}] |
| cave_prism_tree | boss | 23.86% | 32.56% | pass | [{"character":"hero","ratio":0.247236328125,"with_shields":0.247236328125,"first_three":0.16482421875,"first_three_with_shields":0.16482421875,"observed_rounds":3},{"character":"cleric","ratio":0.3182291666666667,"with_shields":0.3182291666666667,"first_three":0.21215277777777777,"first_three_with_shields":0.21215277777777777,"observed_rounds":3},{"character":"mage","ratio":0.4247159090909091,"with_shields":0.0,"first_three":0.2831439393939394,"first_three_with_shields":0.1415719696969697,"observed_rounds":3},{"character":"thief","ratio":0.31214488636363635,"with_shields":0.31214488636363635,"first_three":0.2080965909090909,"first_three_with_shields":0.2080965909090909,"observed_rounds":3}] |
| dark_forest_loc | trash | 52.06% | 52.06% | tutorial_report | [{"character":"hero","ratio":0.4,"with_shields":0.4,"first_three":0.166,"first_three_with_shields":0.166,"observed_rounds":3},{"character":"cleric","ratio":0.4444444444444444,"with_shields":0.4444444444444444,"first_three":0.18296296296296294,"first_three_with_shields":0.18296296296296294,"observed_rounds":3},{"character":"mage","ratio":0.6666666666666666,"with_shields":0.6666666666666666,"first_three":0.27444444444444444,"first_three_with_shields":0.27444444444444444,"observed_rounds":3},{"character":"thief","ratio":0.5714285714285714,"with_shields":0.5714285714285714,"first_three":0.22952380952380952,"first_three_with_shields":0.22952380952380952,"observed_rounds":3}] |
| draco_battle | boss | 32.75% | 30.59% | pass | [{"character":"hero","ratio":0.23157894736842108,"with_shields":0.23157894736842108,"first_three":0.13894736842105265,"first_three_with_shields":0.13894736842105265,"observed_rounds":3},{"character":"cleric","ratio":0.26111111111111107,"with_shields":0.26111111111111107,"first_three":0.15666666666666665,"first_three_with_shields":0.15666666666666665,"observed_rounds":3},{"character":"mage","ratio":0.4423076923076923,"with_shields":0.0,"first_three":0.2653846153846154,"first_three_with_shields":0.0,"observed_rounds":3},{"character":"thief","ratio":0.28846153846153844,"with_shields":0.28846153846153844,"first_three":0.1923076923076923,"first_three_with_shields":0.1923076923076923,"observed_rounds":3}] |
| dragon_valley_loc | boss | 33.23% | 33.56% | pass | [{"character":"hero","ratio":0.24685714285714289,"with_shields":0.24685714285714289,"first_three":0.1645714285714286,"first_three_with_shields":0.1645714285714286,"observed_rounds":3},{"character":"cleric","ratio":0.2848484848484848,"with_shields":0.2848484848484848,"first_three":0.18989898989898987,"first_three_with_shields":0.18989898989898987,"observed_rounds":3},{"character":"mage","ratio":0.49833333333333335,"with_shields":0.0,"first_three":0.33222222222222225,"first_three_with_shields":0.0,"observed_rounds":3},{"character":"thief","ratio":0.3125,"with_shields":0.3125,"first_three":0.20833333333333334,"first_three_with_shields":0.20833333333333334,"observed_rounds":3}] |
| dragon_valley_return | boss | 未验证 | 未验证 | unverified | [] |
| forest_wolves | elite | 19.81% | 18.55% | pass | [{"character":"hero","ratio":0.15542857142857142,"with_shields":0.15542857142857142,"first_three":null,"first_three_with_shields":null,"observed_rounds":1},{"character":"cleric","ratio":0.1898989898989899,"with_shields":0.1898989898989899,"first_three":null,"first_three_with_shields":null,"observed_rounds":1},{"character":"mage","ratio":0.22999999999999998,"with_shields":0.0,"first_three":null,"first_three_with_shields":null,"observed_rounds":1},{"character":"thief","ratio":0.16666666666666666,"with_shields":0.16666666666666666,"first_three":null,"first_three_with_shields":null,"observed_rounds":2}] |
| frost_wolf_battle | boss | 33.56% | 33.56% | pass | [{"character":"hero","ratio":0.24685714285714289,"with_shields":0.24685714285714289,"first_three":0.1645714285714286,"first_three_with_shields":0.1645714285714286,"observed_rounds":3},{"character":"cleric","ratio":0.2848484848484848,"with_shields":0.2848484848484848,"first_three":0.18989898989898987,"first_three_with_shields":0.18989898989898987,"observed_rounds":3},{"character":"mage","ratio":0.49833333333333335,"with_shields":0.0,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"thief","ratio":0.3125,"with_shields":0.3125,"first_three":0.20833333333333334,"first_three_with_shields":0.20833333333333334,"observed_rounds":3}] |
| ghoul_marsh | elite | 未验证 | 未验证 | unverified | [] |
| goblin_fort | trash | 18.15% | 18.15% | approved_optional | [{"character":"hero","ratio":0.12250000000000001,"with_shields":0.12250000000000001,"first_three":null,"first_three_with_shields":null,"observed_rounds":1},{"character":"cleric","ratio":0.1827777777777778,"with_shields":0.1827777777777778,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"mage","ratio":0.27416666666666667,"with_shields":0.27416666666666667,"first_three":null,"first_three_with_shields":null,"observed_rounds":1},{"character":"thief","ratio":0.1464285714285714,"with_shields":0.1464285714285714,"first_three":null,"first_three_with_shields":null,"observed_rounds":1}] |
| goblin_fort_chest_fight | trash | 未验证 | 未验证 | unverified | [] |
| goblin_fort_first_second | trash | 24.10% | 18.15% | approved_optional | [{"character":"hero","ratio":0.12250000000000001,"with_shields":0.12250000000000001,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"cleric","ratio":0.18277777777777776,"with_shields":0.18277777777777776,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"mage","ratio":0.2741666666666666,"with_shields":0.2741666666666666,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"thief","ratio":0.1464285714285714,"with_shields":0.1464285714285714,"first_three":null,"first_three_with_shields":null,"observed_rounds":2}] |
| goblin_fort_fourth | boss | 30.30% | 30.30% | pass | [{"character":"hero","ratio":0.1917391304347826,"with_shields":0.1917391304347826,"first_three":0.14202898550724638,"first_three_with_shields":0.14202898550724638,"observed_rounds":3},{"character":"cleric","ratio":0.2909523809523809,"with_shields":0.2909523809523809,"first_three":0.20888888888888885,"first_three_with_shields":0.20888888888888885,"observed_rounds":3},{"character":"mage","ratio":0.40733333333333327,"with_shields":0.0,"first_three":0.2924444444444444,"first_three_with_shields":0.15666666666666665,"observed_rounds":3},{"character":"thief","ratio":0.3221428571428571,"with_shields":0.3221428571428571,"first_three":0.23428571428571426,"first_three_with_shields":0.23428571428571426,"observed_rounds":3}] |
| goblin_fort_second_left | elite | 未验证 | 未验证 | unverified | [] |
| goblin_fort_second_right | elite | 24.10% | 21.29% | pass | [{"character":"hero","ratio":0.17966666666666664,"with_shields":0.17966666666666664,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"cleric","ratio":0.20888888888888885,"with_shields":0.20888888888888885,"first_three":null,"first_three_with_shields":null,"observed_rounds":1},{"character":"mage","ratio":0.28722222222222216,"with_shields":0.28722222222222216,"first_three":0.28722222222222216,"first_three_with_shields":0.28722222222222216,"observed_rounds":3},{"character":"thief","ratio":0.1757142857142857,"with_shields":0.1757142857142857,"first_three":null,"first_three_with_shields":null,"observed_rounds":2}] |
| goblin_fort_third_guards | elite | 未验证 | 未验证 | unverified | [] |
| gorge_giant_path | elite | 未验证 | 未验证 | unverified | [] |
| gorge_rockfall_path | trash | 未验证 | 未验证 | unverified | [] |
| gorge_worm_lair | boss | 未验证 | 未验证 | unverified | [] |
| grave_chapel | boss | 未验证 | 未验证 | unverified | [] |
| ice_elemental_encounter | elite | 22.58% | 20.40% | pass | [{"character":"hero","ratio":0.16457142857142856,"with_shields":0.16457142857142856,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"cleric","ratio":0.18040404040404037,"with_shields":0.18040404040404037,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"mage","ratio":0.2938888888888889,"with_shields":0.0,"first_three":null,"first_three_with_shields":null,"observed_rounds":1},{"character":"thief","ratio":0.17708333333333334,"with_shields":0.17708333333333334,"first_three":null,"first_three_with_shields":null,"observed_rounds":2}] |
| inn_night_ambush | elite | 未验证 | 未验证 | unverified | [] |
| lost_goblin_crossroads | trash | 未验证 | 未验证 | unverified | [] |
| mansion_corridor | elite | 未验证 | 未验证 | unverified | [] |
| merchant_battle | boss | 未验证 | 未验证 | unverified | [] |
| slime_ambush_one | trash | 10.96% | 11.39% | pass | [{"character":"hero","ratio":0.060625,"with_shields":0.060625,"first_three":null,"first_three_with_shields":null,"observed_rounds":1},{"character":"cleric","ratio":0.12533333333333332,"with_shields":0.12533333333333332,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"mage","ratio":0.16727272727272727,"with_shields":0.0,"first_three":null,"first_three_with_shields":null,"observed_rounds":1},{"character":"thief","ratio":0.10227272727272728,"with_shields":0.10227272727272728,"first_three":null,"first_three_with_shields":null,"observed_rounds":2}] |
| slime_ambush_two | trash | 10.96% | 11.39% | pass | [{"character":"hero","ratio":0.060625,"with_shields":0.060625,"first_three":null,"first_three_with_shields":null,"observed_rounds":1},{"character":"cleric","ratio":0.12533333333333332,"with_shields":0.12533333333333332,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"mage","ratio":0.16727272727272727,"with_shields":0.0,"first_three":null,"first_three_with_shields":null,"observed_rounds":1},{"character":"thief","ratio":0.10227272727272728,"with_shields":0.10227272727272728,"first_three":null,"first_three_with_shields":null,"observed_rounds":2}] |
| slime_king_battle | boss | 29.86% | 29.86% | pass | [{"character":"hero","ratio":0.21942857142857145,"with_shields":0.21942857142857145,"first_three":0.21333333333333335,"first_three_with_shields":0.21333333333333335,"observed_rounds":3},{"character":"cleric","ratio":0.2848484848484848,"with_shields":0.2848484848484848,"first_three":0.24370370370370367,"first_three_with_shields":0.24370370370370367,"observed_rounds":3},{"character":"mage","ratio":0.38333333333333336,"with_shields":0.0,"first_three":0.29814814814814816,"first_three_with_shields":0.1703703703703704,"observed_rounds":3},{"character":"thief","ratio":0.3068181818181818,"with_shields":0.3068181818181818,"first_three":0.23863636363636365,"first_three_with_shields":0.23863636363636365,"observed_rounds":3}] |
| valley_entrance | elite | 21.33% | 21.88% | pass | [{"character":"hero","ratio":0.195047619047619,"with_shields":0.195047619047619,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"cleric","ratio":0.19622895622895617,"with_shields":0.19622895622895617,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"mage","ratio":0.2896296296296296,"with_shields":0.0,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"thief","ratio":0.19444444444444442,"with_shields":0.19444444444444442,"first_three":null,"first_three_with_shields":null,"observed_rounds":1}] |
| valley_ledge | elite | 未验证 | 未验证 | unverified | [] |
| village_fire_elemental | elite | 22.58% | 18.89% | pass | [{"character":"hero","ratio":0.14628571428571427,"with_shields":0.14628571428571427,"first_three":0.14628571428571427,"first_three_with_shields":0.14628571428571427,"observed_rounds":3},{"character":"cleric","ratio":0.16141414141414137,"with_shields":0.16141414141414137,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"mage","ratio":0.28111111111111114,"with_shields":0.0,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"thief","ratio":0.16666666666666666,"with_shields":0.16666666666666666,"first_three":0.16666666666666666,"first_three_with_shields":0.16666666666666666,"observed_rounds":3}] |
| village_fire_slime | trash | 4.57% | 4.57% | fail | [{"character":"hero","ratio":0.027428571428571427,"with_shields":0.027428571428571427,"first_three":0.027428571428571427,"first_three_with_shields":0.027428571428571427,"observed_rounds":3},{"character":"cleric","ratio":0.028484848484848484,"with_shields":0.028484848484848484,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"mage","ratio":0.09583333333333334,"with_shields":0.0,"first_three":null,"first_three_with_shields":null,"observed_rounds":2},{"character":"thief","ratio":0.03125,"with_shields":0.03125,"first_three":null,"first_three_with_shields":null,"observed_rounds":2}] |
| xanxus_phantom_battle | boss | 未验证 | 未验证 | unverified | [] |

### M4 Boss 探针前后与超限

| 原型 | 遭遇 | 职业 | 策略 | 前回合/胜率 | 后回合/胜率/Wilson95 | 判定 |
|---|---|---|---|---|---|---|
| checkpoint | goblin_fort_fourth | hero | attack_only | 6.0 / 100.00% | 6.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | goblin_fort_fourth | hero | best_free | 6.0 / 100.00% | 6.0 / 99.60% / [98.55%, 99.89%] | 通过 |
| checkpoint | goblin_fort_fourth | hero | heuristic_v3 | 5.0 / 100.00% | 6.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | goblin_fort_fourth | cleric | attack_only | 6.0 / 100.00% | 7.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | goblin_fort_fourth | cleric | best_free | 6.0 / 94.60% | 7.0 / 98.80% / [97.41%, 99.45%] | 通过 |
| checkpoint | goblin_fort_fourth | cleric | heuristic_v3 | 6.0 / 100.00% | 7.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | goblin_fort_fourth | mage | attack_only | 15.0 / 47.80% | 12.0 / 55.40% / [51.02%, 59.70%] | 通过 |
| checkpoint | goblin_fort_fourth | mage | best_free | 15.0 / 41.80% | 12.0 / 53.80% / [49.42%, 58.12%] | 通过 |
| checkpoint | goblin_fort_fourth | mage | heuristic_v3 | 7.0 / 98.60% | 6.0 / 86.60% / [83.33%, 89.31%] | 通过 |
| checkpoint | goblin_fort_fourth | thief | attack_only | 6.0 / 84.60% | 6.0 / 98.80% / [97.41%, 99.45%] | 通过 |
| checkpoint | goblin_fort_fourth | thief | best_free | 6.0 / 84.60% | 6.0 / 98.80% / [97.41%, 99.45%] | 通过 |
| checkpoint | goblin_fort_fourth | thief | heuristic_v3 | 6.0 / 87.00% | 7.0 / 99.60% / [98.55%, 99.89%] | 通过 |
| checkpoint | cave_prism_tree | hero | attack_only | 11.0 / 99.60% | 30.0 / 83.40% / [79.89%, 86.40%] | 超限/沙袋 |
| checkpoint | cave_prism_tree | hero | best_free | 9.0 / 93.00% | 15.0 / 73.40% / [69.36%, 77.08%] | 超限 |
| checkpoint | cave_prism_tree | hero | heuristic_v3 | 7.0 / 98.80% | 12.0 / 98.80% / [97.41%, 99.45%] | 通过 |
| checkpoint | cave_prism_tree | cleric | attack_only | 9.0 / 95.40% | 26.0 / 52.00% / [47.62%, 56.35%] | 超限/沙袋 |
| checkpoint | cave_prism_tree | cleric | best_free | 6.0 / 90.60% | 8.0 / 71.60% / [67.49%, 75.38%] | 通过 |
| checkpoint | cave_prism_tree | cleric | heuristic_v3 | 6.0 / 95.40% | 9.0 / 89.20% / [86.17%, 91.63%] | 通过 |
| checkpoint | cave_prism_tree | mage | attack_only | 10.0 / 24.20% | 13.0 / 28.20% / [24.43%, 32.30%] | 通过 |
| checkpoint | cave_prism_tree | mage | best_free | 5.0 / 50.40% | 7.0 / 81.60% / [77.97%, 84.75%] | 通过 |
| checkpoint | cave_prism_tree | mage | heuristic_v3 | 6.0 / 95.20% | 7.0 / 89.60% / [86.62%, 91.98%] | 通过 |
| checkpoint | cave_prism_tree | thief | attack_only | 11.0 / 7.60% | 10.0 / 0.00% / [0.00%, 0.76%] | Q4只报告 |
| checkpoint | cave_prism_tree | thief | best_free | 8.0 / 41.20% | 10.0 / 0.40% / [0.11%, 1.45%] | Q4只报告 |
| checkpoint | cave_prism_tree | thief | heuristic_v3 | 8.0 / 64.20% | 13.0 / 14.80% / [11.96%, 18.18%] | 通过 |
| checkpoint | slime_king_battle | hero | attack_only | 7.0 / 100.00% | 7.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | slime_king_battle | hero | best_free | 7.0 / 99.60% | 7.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | slime_king_battle | hero | heuristic_v3 | 6.0 / 100.00% | 6.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | slime_king_battle | cleric | attack_only | 8.0 / 98.40% | 7.0 / 99.80% / [98.88%, 99.96%] | 通过 |
| checkpoint | slime_king_battle | cleric | best_free | 8.0 / 91.40% | 7.0 / 99.40% / [98.25%, 99.80%] | 通过 |
| checkpoint | slime_king_battle | cleric | heuristic_v3 | 8.0 / 97.20% | 8.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | slime_king_battle | mage | attack_only | 13.0 / 10.20% | 9.0 / 96.00% / [93.90%, 97.40%] | 通过 |
| checkpoint | slime_king_battle | mage | best_free | 9.0 / 6.60% | 9.0 / 94.60% / [92.26%, 96.26%] | 通过 |
| checkpoint | slime_king_battle | mage | heuristic_v3 | 6.0 / 92.80% | 4.0 / 99.80% / [98.88%, 99.96%] | 通过 |
| checkpoint | slime_king_battle | thief | attack_only | 11.0 / 17.80% | 13.0 / 52.80% / [48.42%, 57.14%] | 通过 |
| checkpoint | slime_king_battle | thief | best_free | 5.0 / 8.20% | 10.0 / 35.60% / [31.53%, 39.89%] | 通过 |
| checkpoint | slime_king_battle | thief | heuristic_v3 | 10.0 / 51.60% | 12.0 / 69.00% / [64.81%, 72.90%] | 通过 |
| checkpoint | frost_wolf_battle | hero | attack_only | 5.0 / 100.00% | 5.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | frost_wolf_battle | hero | best_free | 5.0 / 98.40% | 5.0 / 99.60% / [98.55%, 99.89%] | 通过 |
| checkpoint | frost_wolf_battle | hero | heuristic_v3 | 5.0 / 100.00% | 4.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | frost_wolf_battle | cleric | attack_only | 5.0 / 97.80% | 5.0 / 99.80% / [98.88%, 99.96%] | 通过 |
| checkpoint | frost_wolf_battle | cleric | best_free | 5.0 / 91.80% | 5.0 / 99.40% / [98.25%, 99.80%] | 通过 |
| checkpoint | frost_wolf_battle | cleric | heuristic_v3 | 6.0 / 98.40% | 6.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | frost_wolf_battle | mage | attack_only | 5.0 / 1.40% | 10.0 / 52.80% / [48.42%, 57.14%] | 通过 |
| checkpoint | frost_wolf_battle | mage | best_free | 4.0 / 1.20% | 10.0 / 46.60% / [42.27%, 50.98%] | 通过 |
| checkpoint | frost_wolf_battle | mage | heuristic_v3 | 5.0 / 34.80% | 6.0 / 86.20% / [82.90%, 88.95%] | 通过 |
| checkpoint | frost_wolf_battle | thief | attack_only | 2.0 / 24.80% | 7.0 / 47.80% / [43.46%, 52.18%] | 通过 |
| checkpoint | frost_wolf_battle | thief | best_free | 2.0 / 23.60% | 5.0 / 35.20% / [31.14%, 39.48%] | 通过 |
| checkpoint | frost_wolf_battle | thief | heuristic_v3 | 2.0 / 29.80% | 8.0 / 67.60% / [63.38%, 71.55%] | 通过 |
| checkpoint | dragon_valley_loc | hero | attack_only | 12.0 / 84.40% | 10.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | dragon_valley_loc | hero | best_free | 9.0 / 49.20% | 10.0 / 99.80% / [98.88%, 99.96%] | 通过 |
| checkpoint | dragon_valley_loc | hero | heuristic_v3 | 11.0 / 87.60% | 9.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| checkpoint | dragon_valley_loc | cleric | attack_only | 9.0 / 64.80% | 8.0 / 99.60% / [98.55%, 99.89%] | 通过 |
| checkpoint | dragon_valley_loc | cleric | best_free | 9.0 / 48.20% | 8.0 / 96.00% / [93.90%, 97.40%] | 通过 |
| checkpoint | dragon_valley_loc | cleric | heuristic_v3 | 8.0 / 78.20% | 7.0 / 99.40% / [98.25%, 99.80%] | 通过 |
| checkpoint | dragon_valley_loc | mage | attack_only | 2.0 / 1.20% | 8.0 / 37.20% / [33.08%, 41.52%] | 通过 |
| checkpoint | dragon_valley_loc | mage | best_free | 2.0 / 5.60% | 2.0 / 12.00% / [9.44%, 15.14%] | 通过 |
| checkpoint | dragon_valley_loc | mage | heuristic_v3 | 2.0 / 7.60% | 7.0 / 54.00% / [49.62%, 58.32%] | 通过 |
| checkpoint | dragon_valley_loc | thief | attack_only | 6.0 / 14.80% | 10.0 / 42.00% / [37.75%, 46.37%] | 通过 |
| checkpoint | dragon_valley_loc | thief | best_free | 6.0 / 11.80% | 10.0 / 36.20% / [32.11%, 40.50%] | 通过 |
| checkpoint | dragon_valley_loc | thief | heuristic_v3 | 6.0 / 14.80% | 10.0 / 42.00% / [37.75%, 46.37%] | 通过 |
| checkpoint | draco_battle | hero | attack_only | 25.0 / 45.80% | 29.0 / 61.60% / [57.26%, 65.76%] | 超限/沙袋 |
| checkpoint | draco_battle | hero | best_free | 15.0 / 21.60% | 19.0 / 33.60% / [29.60%, 37.85%] | 超限/沙袋 |
| checkpoint | draco_battle | hero | heuristic_v3 | 13.0 / 88.80% | 12.0 / 99.80% / [98.88%, 99.96%] | 通过 |
| checkpoint | draco_battle | cleric | attack_only | 4.0 / 91.20% | 29.0 / 86.20% / [82.90%, 88.95%] | 超限/沙袋 |
| checkpoint | draco_battle | cleric | best_free | 4.0 / 89.60% | 28.0 / 61.80% / [57.47%, 65.95%] | 超限/沙袋 |
| checkpoint | draco_battle | cleric | heuristic_v3 | 4.0 / 99.40% | 27.0 / 99.80% / [98.88%, 99.96%] | 超限/沙袋 |
| checkpoint | draco_battle | mage | attack_only | 5.5 / 0.00% | 14.0 / 0.00% / [0.00%, 0.76%] | Q4只报告 |
| checkpoint | draco_battle | mage | best_free | 5.0 / 0.00% | 13.0 / 0.00% / [0.00%, 0.76%] | Q4只报告 |
| checkpoint | draco_battle | mage | heuristic_v3 | 5.0 / 25.60% | 11.0 / 74.00% / [69.98%, 77.65%] | 通过 |
| checkpoint | draco_battle | thief | attack_only | 8.0 / 2.80% | 8.0 / 0.00% / [0.00%, 0.76%] | Q4只报告 |
| checkpoint | draco_battle | thief | best_free | 7.0 / 0.40% | 8.0 / 0.00% / [0.00%, 0.76%] | Q4只报告 |
| checkpoint | draco_battle | thief | heuristic_v3 | 28.0 / 67.20% | 34.0 / 0.00% / [0.00%, 0.76%] | 超限/沙袋 |
| P0a | dragon_valley_loc | cleric | best_free | None / 未验证 | 7 / 0.00% / [0.00%, 79.35%] | Q4只报告 |
| P0a | frost_wolf_battle | cleric | best_free | 1 / 0.00% | 1.5 / 6.25% / [1.11%, 28.33%] | Q4只报告 |
| P0a | slime_king_battle | cleric | best_free | 2 / 0.00% | 3 / 1.10% / [0.47%, 2.56%] | Q4只报告 |
| P0a | dragon_valley_loc | hero | best_free | None / 未验证 | 3.5 / 0.00% / [0.00%, 48.99%] | Q4只报告 |
| P0a | frost_wolf_battle | hero | best_free | None / 未验证 | 7 / 57.14% / [25.05%, 84.18%] | 通过 |
| P0a | slime_king_battle | hero | best_free | 2.0 / 0.00% | 5.0 / 2.60% / [1.53%, 4.40%] | Q4只报告 |
| P0a | frost_wolf_battle | mage | best_free | 1 / 0.00% | 1.0 / 0.00% / [0.00%, 27.75%] | Q4只报告 |
| P0a | dragon_valley_loc | thief | best_free | None / 未验证 | 2 / 0.00% / [0.00%, 79.35%] | Q4只报告 |
| P0a | frost_wolf_battle | thief | best_free | 1.0 / 0.00% | 1 / 1.20% / [0.21%, 6.51%] | Q4只报告 |
| P0a | slime_king_battle | thief | best_free | 1 / 0.00% | 3 / 4.21% / [1.65%, 10.33%] | Q4只报告 |
| P0b | dragon_valley_loc | cleric | best_free | 4.0 / 0.00% | 5.0 / 7.41% / [2.92%, 17.55%] | Q4只报告 |
| P0b | frost_wolf_battle | cleric | best_free | 2.0 / 1.90% | 2 / 20.69% / [16.22%, 26.01%] | 通过 |
| P0b | slime_king_battle | cleric | best_free | 2 / 0.00% | 3 / 0.76% / [0.13%, 4.20%] | Q4只报告 |
| P0b | dragon_valley_loc | hero | best_free | 3 / 0.00% | 8 / 15.24% / [9.60%, 23.33%] | 通过 |
| P0b | frost_wolf_battle | hero | best_free | 3 / 11.96% | 5.0 / 45.65% / [39.34%, 52.11%] | 通过 |
| P0b | slime_king_battle | hero | best_free | 2.0 / 0.00% | 6.0 / 1.76% / [0.60%, 5.06%] | Q4只报告 |
| P0b | dragon_valley_loc | mage | best_free | None / 未验证 | 2 / 0.00% / [0.00%, 35.43%] | Q4只报告 |
| P0b | frost_wolf_battle | mage | best_free | 1.0 / 0.00% | 1 / 4.76% / [2.33%, 9.50%] | Q4只报告 |
| P0b | slime_king_battle | mage | best_free | 2 / 0.00% | 4 / 0.00% / [0.00%, 25.88%] | Q4只报告 |
| P0b | dragon_valley_loc | thief | best_free | 1.0 / 0.00% | 4.0 / 8.33% / [3.61%, 18.07%] | Q4只报告 |
| P0b | frost_wolf_battle | thief | best_free | 2 / 2.68% | 2.0 / 26.75% / [21.43%, 32.85%] | 通过 |
| P0b | slime_king_battle | thief | best_free | 2 / 0.00% | 4 / 5.45% / [1.87%, 14.85%] | Q4只报告 |
| P0g | dragon_valley_loc | cleric | best_free | 4.0 / 0.00% | 5.0 / 7.41% / [2.92%, 17.55%] | Q4只报告 |
| P0g | frost_wolf_battle | cleric | best_free | 2.0 / 1.90% | 2 / 20.69% / [16.22%, 26.01%] | 通过 |
| P0g | slime_king_battle | cleric | best_free | 2 / 0.00% | 3 / 0.76% / [0.13%, 4.20%] | Q4只报告 |
| P0g | dragon_valley_loc | hero | best_free | 3 / 0.00% | 8 / 15.24% / [9.60%, 23.33%] | 通过 |
| P0g | frost_wolf_battle | hero | best_free | 3 / 11.96% | 5.0 / 45.65% / [39.34%, 52.11%] | 通过 |
| P0g | slime_king_battle | hero | best_free | 2.0 / 0.00% | 6.0 / 1.76% / [0.60%, 5.06%] | Q4只报告 |
| P0g | dragon_valley_loc | mage | best_free | None / 未验证 | 2 / 0.00% / [0.00%, 35.43%] | Q4只报告 |
| P0g | frost_wolf_battle | mage | best_free | 1.0 / 0.00% | 1 / 4.76% / [2.33%, 9.50%] | Q4只报告 |
| P0g | slime_king_battle | mage | best_free | 2 / 0.00% | 4 / 0.00% / [0.00%, 25.88%] | Q4只报告 |
| P0g | dragon_valley_loc | thief | best_free | 1.0 / 0.00% | 4.0 / 8.33% / [3.61%, 18.07%] | Q4只报告 |
| P0g | frost_wolf_battle | thief | best_free | 2 / 2.68% | 2.0 / 26.75% / [21.43%, 32.85%] | 通过 |
| P0g | slime_king_battle | thief | best_free | 2 / 0.00% | 4 / 5.45% / [1.87%, 14.85%] | Q4只报告 |
| P1 | dragon_valley_loc | cleric | heuristic_v3 | 4.0 / 4.00% | 8 / 31.16% / [25.35%, 37.64%] | 通过 |
| P1 | frost_wolf_battle | cleric | heuristic_v3 | 5 / 23.61% | 8 / 77.35% / [72.17%, 81.81%] | 通过 |
| P1 | slime_king_battle | cleric | heuristic_v3 | 3 / 0.00% | 5 / 0.00% / [0.00%, 3.81%] | 通过 |
| P1 | dragon_valley_loc | hero | heuristic_v3 | 5 / 1.44% | 14 / 44.73% / [38.53%, 51.09%] | 通过 |
| P1 | frost_wolf_battle | hero | heuristic_v3 | 4.0 / 95.00% | 4 / 98.34% / [95.81%, 99.35%] | 通过 |
| P1 | slime_king_battle | hero | heuristic_v3 | 3 / 0.00% | 6 / 3.51% / [1.62%, 7.44%] | 通过 |
| P1 | dragon_valley_loc | mage | heuristic_v3 | 2 / 4.76% | 2.0 / 16.67% / [9.80%, 26.91%] | 通过 |
| P1 | frost_wolf_battle | mage | heuristic_v3 | 2.0 / 17.95% | 2.0 / 35.42% / [29.64%, 41.65%] | 通过 |
| P1 | slime_king_battle | mage | heuristic_v3 | 2 / 0.96% | 4 / 21.05% / [16.07%, 27.08%] | 通过 |
| P1 | dragon_valley_loc | thief | heuristic_v3 | 4 / 0.00% | 5 / 11.03% / [6.91%, 17.17%] | 通过 |
| P1 | frost_wolf_battle | thief | heuristic_v3 | 4 / 39.13% | 6.0 / 67.52% / [61.28%, 73.20%] | 通过 |
| P1 | slime_king_battle | thief | heuristic_v3 | 2 / 0.00% | 3 / 6.92% / [3.91%, 11.96%] | 通过 |
| P2 | cave_prism_tree | cleric | heuristic_v3 | 7 / 93.52% | 9 / 83.02% / [79.39%, 86.12%] | 通过 |
| P2 | draco_battle | cleric | heuristic_v3 | 4.0 / 99.18% | 14 / 91.69% / [88.44%, 94.08%] | 通过 |
| P2 | dragon_valley_loc | cleric | heuristic_v3 | 7 / 73.27% | 9.0 / 91.42% / [88.30%, 93.77%] | 通过 |
| P2 | frost_wolf_battle | cleric | heuristic_v3 | 6 / 86.82% | 6 / 95.42% / [93.04%, 97.02%] | 通过 |
| P2 | goblin_fort_fourth | cleric | heuristic_v3 | 7.0 / 92.60% | 8.0 / 96.20% / [94.14%, 97.55%] | 通过 |
| P2 | slime_king_battle | cleric | heuristic_v3 | 8 / 84.88% | 9 / 91.89% / [89.11%, 94.01%] | 通过 |
| P2 | cave_prism_tree | hero | heuristic_v3 | 8.0 / 99.39% | 13.0 / 79.64% / [75.87%, 82.95%] | 通过 |
| P2 | draco_battle | hero | heuristic_v3 | 12 / 69.92% | 17.0 / 70.90% / [66.72%, 74.76%] | 超限 |
| P2 | dragon_valley_loc | hero | heuristic_v3 | 11 / 75.77% | 10.0 / 98.39% / [96.85%, 99.18%] | 通过 |
| P2 | frost_wolf_battle | hero | heuristic_v3 | 5.0 / 99.39% | 5.0 / 100.00% / [99.23%, 100.00%] | 通过 |
| P2 | goblin_fort_fourth | hero | heuristic_v3 | 6.0 / 98.00% | 7.0 / 99.20% / [97.96%, 99.69%] | 通过 |
| P2 | slime_king_battle | hero | heuristic_v3 | 6.0 / 100.00% | 6.0 / 100.00% / [99.23%, 100.00%] | 通过 |
| P2 | cave_prism_tree | mage | heuristic_v3 | 4.0 / 83.42% | 6.0 / 81.34% / [77.24%, 84.85%] | 通过 |
| P2 | draco_battle | mage | heuristic_v3 | 5 / 31.91% | 9.0 / 89.57% / [85.42%, 92.64%] | 通过 |
| P2 | dragon_valley_loc | mage | heuristic_v3 | 5 / 17.74% | 6 / 70.74% / [66.06%, 75.02%] | 通过 |
| P2 | frost_wolf_battle | mage | heuristic_v3 | 4.0 / 72.97% | 4.0 / 96.83% / [94.65%, 98.14%] | 通过 |
| P2 | goblin_fort_fourth | mage | heuristic_v3 | 5 / 83.17% | 5.0 / 85.74% / [82.40%, 88.54%] | 通过 |
| P2 | slime_king_battle | mage | heuristic_v3 | 5 / 90.60% | 5 / 96.49% / [94.29%, 97.86%] | 通过 |
| P2 | cave_prism_tree | thief | heuristic_v3 | 6 / 83.49% | 8 / 68.77% / [63.95%, 73.21%] | 通过 |
| P2 | draco_battle | thief | heuristic_v3 | 26.5 / 53.12% | 31 / 86.38% / [81.41%, 90.19%] | 超限/沙袋 |
| P2 | dragon_valley_loc | thief | heuristic_v3 | 4 / 13.85% | 10 / 68.51% / [63.42%, 73.20%] | 通过 |
| P2 | frost_wolf_battle | thief | heuristic_v3 | 5.0 / 82.27% | 5 / 92.95% / [89.88%, 95.15%] | 通过 |
| P2 | goblin_fort_fourth | thief | heuristic_v3 | 6.0 / 70.60% | 7.0 / 84.60% / [81.17%, 87.50%] | 通过 |
| P2 | slime_king_battle | thief | heuristic_v3 | 7 / 81.02% | 8 / 88.18% / [84.75%, 90.92%] | 通过 |
| P2s | cave_prism_tree | cleric | heuristic_v3 | 6 / 96.98% | 7.5 / 93.14% / [90.43%, 95.13%] | 通过 |
| P2s | draco_battle | cleric | heuristic_v3 | 4.0 / 76.61% | 5.0 / 85.42% / [81.54%, 88.60%] | 通过 |
| P2s | dragon_valley_loc | cleric | heuristic_v3 | 7.0 / 72.19% | 7 / 95.76% / [93.32%, 97.34%] | 通过 |
| P2s | frost_wolf_battle | cleric | heuristic_v3 | 6.0 / 96.39% | 6.0 / 98.78% / [97.18%, 99.48%] | 通过 |
| P2s | goblin_fort_fourth | cleric | heuristic_v3 | 7.0 / 86.60% | 8.0 / 90.60% / [87.72%, 92.86%] | 通过 |
| P2s | slime_king_battle | cleric | heuristic_v3 | 8 / 76.91% | 10 / 91.17% / [88.20%, 93.45%] | 通过 |
| P2s | cave_prism_tree | hero | heuristic_v3 | 7.0 / 100.00% | 12 / 80.81% / [77.11%, 84.03%] | 通过 |
| P2s | draco_battle | hero | heuristic_v3 | 13.0 / 61.98% | 18.0 / 68.78% / [64.54%, 72.72%] | 超限 |
| P2s | dragon_valley_loc | hero | heuristic_v3 | 11 / 77.89% | 10 / 98.99% / [97.66%, 99.57%] | 通过 |
| P2s | frost_wolf_battle | hero | heuristic_v3 | 4.0 / 99.80% | 4 / 100.00% / [99.23%, 100.00%] | 通过 |
| P2s | goblin_fort_fourth | hero | heuristic_v3 | 6.0 / 99.20% | 7.0 / 99.00% / [97.68%, 99.57%] | 通过 |
| P2s | slime_king_battle | hero | heuristic_v3 | 6.0 / 100.00% | 7 / 100.00% / [99.23%, 100.00%] | 通过 |
| P2s | cave_prism_tree | mage | heuristic_v3 | 4.0 / 94.91% | 4.0 / 95.48% / [92.88%, 97.16%] | 通过 |
| P2s | draco_battle | mage | heuristic_v3 | 5 / 20.69% | 9.0 / 88.46% / [83.73%, 91.95%] | 通过 |
| P2s | dragon_valley_loc | mage | heuristic_v3 | 4 / 13.88% | 6 / 67.44% / [62.34%, 72.15%] | 通过 |
| P2s | frost_wolf_battle | mage | heuristic_v3 | 3.0 / 78.42% | 4.0 / 99.18% / [97.61%, 99.72%] | 通过 |
| P2s | goblin_fort_fourth | mage | heuristic_v3 | 4 / 69.74% | 5.0 / 77.60% / [73.74%, 81.04%] | 通过 |
| P2s | slime_king_battle | mage | heuristic_v3 | 5.0 / 84.20% | 5.0 / 94.33% / [91.56%, 96.23%] | 通过 |
| P2s | cave_prism_tree | thief | heuristic_v3 | 6 / 85.14% | 8 / 73.99% / [69.31%, 78.19%] | 通过 |
| P2s | draco_battle | thief | heuristic_v3 | 30 / 70.97% | 32 / 88.84% / [84.15%, 92.27%] | 超限/沙袋 |
| P2s | dragon_valley_loc | thief | heuristic_v3 | 5 / 14.29% | 10 / 78.45% / [73.43%, 82.75%] | 通过 |
| P2s | frost_wolf_battle | thief | heuristic_v3 | 5 / 86.45% | 5.0 / 91.10% / [87.52%, 93.73%] | 通过 |
| P2s | goblin_fort_fourth | thief | heuristic_v3 | 6.0 / 65.80% | 7.0 / 75.20% / [71.23%, 78.78%] | 通过 |
| P2s | slime_king_battle | thief | heuristic_v3 | 7 / 76.90% | 8.0 / 86.70% / [82.90%, 89.77%] | 通过 |
| P3 | cave_prism_tree | cleric | heuristic_v3 | 7 / 89.22% | 14 / 69.57% / [65.32%, 73.50%] | 通过 |
| P3 | draco_battle | cleric | heuristic_v3 | 10 / 0.00% | 23 / 95.77% / [88.30%, 98.55%] | 超限/沙袋 |
| P3 | dragon_valley_loc | cleric | heuristic_v3 | 9 / 36.36% | 12 / 89.87% / [81.27%, 94.78%] | 通过 |
| P3 | frost_wolf_battle | cleric | heuristic_v3 | 2.0 / 4.80% | 2 / 22.16% / [18.18%, 26.73%] | 通过 |
| P3 | goblin_fort_fourth | cleric | heuristic_v3 | 7.0 / 94.60% | 7.0 / 97.40% / [95.60%, 98.47%] | 通过 |
| P3 | gorge_worm_lair | cleric | heuristic_v3 | 2 / 100.00% | 3.0 / 100.00% / [99.02%, 100.00%] | 通过 |
| P3 | grave_chapel | cleric | heuristic_v3 | 4.0 / 95.31% | 4.0 / 91.51% / [88.47%, 93.80%] | 通过 |
| P3 | slime_king_battle | cleric | heuristic_v3 | 11 / 67.86% | 12 / 87.06% / [83.79%, 89.76%] | 通过 |
| P3 | xanxus_phantom_battle | cleric | heuristic_v3 | 6 / 18.18% | 6 / 89.87% / [81.27%, 94.78%] | 通过 |
| P3 | cave_prism_tree | hero | heuristic_v3 | 8.0 / 99.00% | 23.0 / 58.60% / [54.23%, 62.84%] | 超限/沙袋 |
| P3 | draco_battle | hero | heuristic_v3 | 7.0 / 67.86% | 10.0 / 89.10% / [84.78%, 92.30%] | 通过 |
| P3 | dragon_valley_loc | hero | heuristic_v3 | 9 / 37.67% | 15 / 81.85% / [77.29%, 85.66%] | 超限 |
| P3 | frost_wolf_battle | hero | heuristic_v3 | 3.0 / 46.07% | 5 / 67.29% / [62.98%, 71.32%] | 通过 |
| P3 | goblin_fort_fourth | hero | heuristic_v3 | 5.0 / 100.00% | 6.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| P3 | gorge_worm_lair | hero | heuristic_v3 | 2 / 100.00% | 2 / 100.00% / [99.23%, 100.00%] | 通过 |
| P3 | grave_chapel | hero | heuristic_v3 | 3.0 / 99.40% | 4.0 / 99.40% / [98.25%, 99.80%] | 通过 |
| P3 | slime_king_battle | hero | heuristic_v3 | 8.0 / 100.00% | 8.0 / 100.00% / [99.24%, 100.00%] | 通过 |
| P3 | xanxus_phantom_battle | hero | heuristic_v3 | 9 / 70.40% | 8 / 95.69% / [92.90%, 97.42%] | 通过 |
| P3 | cave_prism_tree | mage | heuristic_v3 | 4 / 85.26% | 6.0 / 78.74% / [74.55%, 82.41%] | 通过 |
| P3 | draco_battle | mage | heuristic_v3 | 5 / 42.42% | 8.0 / 91.60% / [87.38%, 94.49%] | 通过 |
| P3 | dragon_valley_loc | mage | heuristic_v3 | 5 / 41.57% | 6.0 / 83.22% / [78.45%, 87.10%] | 通过 |
| P3 | dragon_valley_return | mage | heuristic_v3 | 12 / 89.19% | 7.0 / 100.00% / [98.41%, 100.00%] | 通过 |
| P3 | frost_wolf_battle | mage | heuristic_v3 | 4 / 28.94% | 5 / 77.36% / [72.83%, 81.32%] | 通过 |
| P3 | goblin_fort_fourth | mage | heuristic_v3 | 4 / 89.98% | 5.0 / 85.89% / [82.55%, 88.68%] | 通过 |
| P3 | gorge_worm_lair | mage | heuristic_v3 | 3.0 / 100.00% | 2 / 100.00% / [99.01%, 100.00%] | 通过 |
| P3 | grave_chapel | mage | heuristic_v3 | 3.0 / 94.92% | 4.0 / 99.22% / [97.74%, 99.74%] | 通过 |
| P3 | merchant_battle | mage | heuristic_v3 | 6.0 / 100.00% | 6 / 100.00% / [99.01%, 100.00%] | 通过 |
| P3 | slime_king_battle | mage | heuristic_v3 | 5 / 79.29% | 5.0 / 90.61% / [87.47%, 93.03%] | 通过 |
| P3 | xanxus_phantom_battle | mage | heuristic_v3 | 5 / 52.81% | 5.0 / 89.51% / [85.42%, 92.55%] | 通过 |
| P3 | cave_prism_tree | thief | heuristic_v3 | 6.0 / 71.88% | 13.0 / 60.41% / [55.78%, 64.86%] | 通过 |
| P3 | draco_battle | thief | heuristic_v3 | 2.5 / 0.00% | 23 / 63.44% / [53.30%, 72.51%] | 超限/沙袋 |
| P3 | dragon_valley_loc | thief | heuristic_v3 | 4.5 / 14.29% | 11.0 / 48.44% / [41.47%, 55.47%] | 通过 |
| P3 | frost_wolf_battle | thief | heuristic_v3 | 5 / 68.93% | 5.0 / 79.75% / [74.24%, 84.33%] | 通过 |
| P3 | goblin_fort_fourth | thief | heuristic_v3 | 6.0 / 74.40% | 6.0 / 92.00% / [89.29%, 94.07%] | 通过 |
| P3 | gorge_worm_lair | thief | heuristic_v3 | 1.0 / 100.00% | 1.0 / 100.00% / [98.58%, 100.00%] | 通过 |
| P3 | grave_chapel | thief | heuristic_v3 | 4.0 / 57.55% | 5.0 / 76.00% / [71.26%, 80.18%] | 通过 |
| P3 | slime_king_battle | thief | heuristic_v3 | 8.0 / 58.33% | 8.0 / 76.96% / [72.89%, 80.57%] | 通过 |
| P3 | xanxus_phantom_battle | thief | heuristic_v3 | 5.0 / 15.71% | 6.5 / 66.67% / [59.73%, 72.95%] | 通过 |

### M3 样本前后

| 职业 | 遭遇 | 原型 | 前（匹配样本组） | 后 |
|---|---|---|---|---|
| cleric | dragon_valley_loc | P0b | [{"character":"cleric","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","value":0.09325780602376348,"zero_incoming":false,"n":4,"healing":1.35,"incoming":14.476}] | {"character":"cleric","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","value":0.11047463175122753,"zero_incoming":false,"n":54,"healing":1.35,"incoming":12.219999999999997} |
| cleric | frost_wolf_battle | P0b | [{"character":"cleric","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","value":0.3134206219312603,"zero_incoming":false,"n":206,"healing":3.83,"incoming":12.219999999999997}] | {"character":"cleric","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","value":0.3134206219312603,"zero_incoming":false,"n":256,"healing":3.83,"incoming":12.219999999999997} |
| cleric | frost_wolf_battle | P0b | [{"character":"cleric","encounter":"frost_wolf_battle","companion":"none","value":0.05155482815057284,"zero_incoming":false,"n":4,"healing":0.63,"incoming":12.219999999999997}] | {"character":"cleric","encounter":"frost_wolf_battle","companion":"none","value":0.05155482815057284,"zero_incoming":false,"n":4,"healing":0.63,"incoming":12.219999999999997} |
| cleric | frost_wolf_battle | P0b | [{"character":"cleric","encounter":"frost_wolf_battle","companion":"none","value":0.05155482815057284,"zero_incoming":false,"n":4,"healing":0.63,"incoming":12.219999999999997}] | {"character":"cleric","encounter":"frost_wolf_battle","companion":"none","value":0.11047463175122753,"zero_incoming":false,"n":1,"healing":1.35,"incoming":12.219999999999997} |
| cleric | slime_king_battle | P0b | [{"character":"cleric","encounter":"slime_king_battle","companion":"none","value":0.0,"zero_incoming":false,"n":131,"healing":0,"incoming":9.399999999999999}] | {"character":"cleric","encounter":"slime_king_battle","companion":"none","value":0.0,"zero_incoming":false,"n":131,"healing":0,"incoming":9.399999999999999} |
| hero | dragon_valley_loc | P0b | [{"character":"hero","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","value":0.0,"zero_incoming":false,"n":25,"healing":0.0,"incoming":13.995714285714284}] | {"character":"hero","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","value":0.0,"zero_incoming":false,"n":102,"healing":0.0,"incoming":11.64} |
| hero | dragon_valley_loc | P0b | [] | {"character":"hero","encounter":"dragon_valley_loc","companion":"none","value":0.0,"zero_incoming":false,"n":3,"healing":0,"incoming":11.64} |
| hero | frost_wolf_battle | P0b | [{"character":"hero","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","value":0.27210884353741505,"zero_incoming":false,"n":208,"healing":3.2,"incoming":11.759999999999998}] | {"character":"hero","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","value":0.27210884353741505,"zero_incoming":false,"n":226,"healing":3.2,"incoming":11.759999999999998} |
| hero | frost_wolf_battle | P0b | [{"character":"hero","encounter":"frost_wolf_battle","companion":"none","value":0.0,"zero_incoming":false,"n":1,"healing":0,"incoming":11.759999999999998}] | {"character":"hero","encounter":"frost_wolf_battle","companion":"none","value":0.0,"zero_incoming":false,"n":4,"healing":0,"incoming":11.67} |
| hero | slime_king_battle | P0b | [{"character":"hero","encounter":"slime_king_battle","companion":"none","value":0.0,"zero_incoming":false,"n":170,"healing":0,"incoming":8.82}] | {"character":"hero","encounter":"slime_king_battle","companion":"none","value":0.0,"zero_incoming":false,"n":170,"healing":0,"incoming":8.82} |
| mage | dragon_valley_loc | P0b | [] | {"character":"mage","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","value":0.0,"zero_incoming":false,"n":7,"healing":0.0,"incoming":11.96} |
| mage | frost_wolf_battle | P0b | [{"character":"mage","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","value":0.2618657937806875,"zero_incoming":false,"n":86,"healing":3.2,"incoming":12.219999999999997}] | {"character":"mage","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","value":0.2618657937806875,"zero_incoming":false,"n":140,"healing":3.2,"incoming":12.219999999999997} |
| mage | frost_wolf_battle | P0b | [] | {"character":"mage","encounter":"frost_wolf_battle","companion":"none","value":0.0,"zero_incoming":false,"n":7,"healing":0,"incoming":12.219999999999997} |
| mage | slime_king_battle | P0b | [{"character":"mage","encounter":"slime_king_battle","companion":"fire_bat_dragon","value":0.31914893617021284,"zero_incoming":false,"n":11,"healing":3.0,"incoming":9.399999999999999}] | {"character":"mage","encounter":"slime_king_battle","companion":"fire_bat_dragon","value":0.31914893617021284,"zero_incoming":false,"n":11,"healing":3.0,"incoming":9.399999999999999} |
| thief | dragon_valley_loc | P0b | [{"character":"thief","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","value":0.0,"zero_incoming":false,"n":4,"healing":0.0,"incoming":10.821428571428571}] | {"character":"thief","encounter":"dragon_valley_loc","companion":"fire_bat_dragon","value":0.0,"zero_incoming":false,"n":58,"healing":0.0,"incoming":9.0} |
| thief | dragon_valley_loc | P0b | [] | {"character":"thief","encounter":"dragon_valley_loc","companion":"none","value":0.0,"zero_incoming":false,"n":2,"healing":0,"incoming":9.0} |
| thief | frost_wolf_battle | P0b | [{"character":"thief","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","value":0.35555555555555557,"zero_incoming":false,"n":139,"healing":3.2,"incoming":9.0}] | {"character":"thief","encounter":"frost_wolf_battle","companion":"fire_bat_dragon","value":0.35555555555555557,"zero_incoming":false,"n":190,"healing":3.2,"incoming":9.0} |
| thief | frost_wolf_battle | P0b | [{"character":"thief","encounter":"frost_wolf_battle","companion":"none","value":0.0,"zero_incoming":false,"n":10,"healing":0,"incoming":9.0}] | {"character":"thief","encounter":"frost_wolf_battle","companion":"none","value":0.0,"zero_incoming":false,"n":38,"healing":0,"incoming":9.0} |
| thief | slime_king_battle | P0b | [{"character":"thief","encounter":"slime_king_battle","companion":"fire_bat_dragon","value":0.40650406504065045,"zero_incoming":false,"n":7,"healing":3.0,"incoming":7.379999999999999}] | {"character":"thief","encounter":"slime_king_battle","companion":"fire_bat_dragon","value":0.40650406504065045,"zero_incoming":false,"n":7,"healing":3.0,"incoming":7.379999999999999} |
| thief | slime_king_battle | P0b | [{"character":"thief","encounter":"slime_king_battle","companion":"none","value":0.0,"zero_incoming":false,"n":48,"healing":0,"incoming":7.379999999999999}] | {"character":"thief","encounter":"slime_king_battle","companion":"none","value":0.0,"zero_incoming":false,"n":48,"healing":0,"incoming":7.379999999999999} |

### M3' 样本前后

| 职业 | 遭遇 | 原型 | 前（匹配样本组） | 后 |
|---|---|---|---|---|
| cleric | dragon_valley_loc | P0b | [{"archetype":"P0b","character":"cleric","encounter":"dragon_valley_loc","value":null,"n":4,"kill_time_samples":0,"censored_defeats":4,"infinite_depletion":0}] | {"archetype":"P0b","character":"cleric","encounter":"dragon_valley_loc","value":0.8097211052069554,"n":54,"kill_time_samples":4,"censored_defeats":50,"infinite_depletion":0} |
| cleric | frost_wolf_battle | P0b | [{"archetype":"P0b","character":"cleric","encounter":"frost_wolf_battle","value":0.4095470004912849,"n":210,"kill_time_samples":4,"censored_defeats":206,"infinite_depletion":0}] | {"archetype":"P0b","character":"cleric","encounter":"frost_wolf_battle","value":0.4852017215962554,"n":261,"kill_time_samples":54,"censored_defeats":207,"infinite_depletion":0} |
| cleric | slime_king_battle | P0b | [{"archetype":"P0b","character":"cleric","encounter":"slime_king_battle","value":null,"n":131,"kill_time_samples":0,"censored_defeats":131,"infinite_depletion":0}] | {"archetype":"P0b","character":"cleric","encounter":"slime_king_battle","value":0.8744186046511626,"n":131,"kill_time_samples":1,"censored_defeats":130,"infinite_depletion":0} |
| hero | dragon_valley_loc | P0b | [{"archetype":"P0b","character":"hero","encounter":"dragon_valley_loc","value":null,"n":25,"kill_time_samples":0,"censored_defeats":25,"infinite_depletion":0}] | {"archetype":"P0b","character":"hero","encounter":"dragon_valley_loc","value":0.9899157215327649,"n":105,"kill_time_samples":16,"censored_defeats":89,"infinite_depletion":0} |
| hero | frost_wolf_battle | P0b | [{"archetype":"P0b","character":"hero","encounter":"frost_wolf_battle","value":0.3509970239658324,"n":209,"kill_time_samples":25,"censored_defeats":184,"infinite_depletion":0}] | {"archetype":"P0b","character":"hero","encounter":"frost_wolf_battle","value":0.4149776284228191,"n":230,"kill_time_samples":105,"censored_defeats":125,"infinite_depletion":0} |
| hero | slime_king_battle | P0b | [{"archetype":"P0b","character":"hero","encounter":"slime_king_battle","value":null,"n":170,"kill_time_samples":0,"censored_defeats":170,"infinite_depletion":0}] | {"archetype":"P0b","character":"hero","encounter":"slime_king_battle","value":0.8440143369175628,"n":170,"kill_time_samples":3,"censored_defeats":167,"infinite_depletion":0} |
| mage | dragon_valley_loc | P0b | [] | {"archetype":"P0b","character":"mage","encounter":"dragon_valley_loc","value":null,"n":7,"kill_time_samples":0,"censored_defeats":7,"infinite_depletion":0} |
| mage | frost_wolf_battle | P0b | [{"archetype":"P0b","character":"mage","encounter":"frost_wolf_battle","value":null,"n":86,"kill_time_samples":0,"censored_defeats":86,"infinite_depletion":0}] | {"archetype":"P0b","character":"mage","encounter":"frost_wolf_battle","value":0.4189853341006109,"n":147,"kill_time_samples":7,"censored_defeats":140,"infinite_depletion":0} |
| mage | slime_king_battle | P0b | [{"archetype":"P0b","character":"mage","encounter":"slime_king_battle","value":null,"n":11,"kill_time_samples":0,"censored_defeats":11,"infinite_depletion":0}] | {"archetype":"P0b","character":"mage","encounter":"slime_king_battle","value":null,"n":11,"kill_time_samples":0,"censored_defeats":11,"infinite_depletion":0} |
| thief | dragon_valley_loc | P0b | [{"archetype":"P0b","character":"thief","encounter":"dragon_valley_loc","value":null,"n":4,"kill_time_samples":0,"censored_defeats":4,"infinite_depletion":0}] | {"archetype":"P0b","character":"thief","encounter":"dragon_valley_loc","value":0.8136992741143302,"n":60,"kill_time_samples":5,"censored_defeats":55,"infinite_depletion":0} |
| thief | frost_wolf_battle | P0b | [{"archetype":"P0b","character":"thief","encounter":"frost_wolf_battle","value":0.27131751152721545,"n":149,"kill_time_samples":4,"censored_defeats":145,"infinite_depletion":0}] | {"archetype":"P0b","character":"thief","encounter":"frost_wolf_battle","value":0.3435668004810689,"n":228,"kill_time_samples":61,"censored_defeats":167,"infinite_depletion":0} |
| thief | slime_king_battle | P0b | [{"archetype":"P0b","character":"thief","encounter":"slime_king_battle","value":null,"n":55,"kill_time_samples":0,"censored_defeats":55,"infinite_depletion":0}] | {"archetype":"P0b","character":"thief","encounter":"slime_king_battle","value":0.5824777961764261,"n":55,"kill_time_samples":3,"censored_defeats":52,"infinite_depletion":0} |
| cleric | cave_prism_tree | P2 | [{"archetype":"P2","character":"cleric","encounter":"cave_prism_tree","value":0.28283464751050924,"n":463,"kill_time_samples":433,"censored_defeats":30,"infinite_depletion":0}] | {"archetype":"P2","character":"cleric","encounter":"cave_prism_tree","value":0.48453171048069216,"n":477,"kill_time_samples":396,"censored_defeats":81,"infinite_depletion":0} |
| cleric | draco_battle | P2 | [{"archetype":"P2","character":"cleric","encounter":"draco_battle","value":0.09645768285172406,"n":244,"kill_time_samples":242,"censored_defeats":2,"infinite_depletion":0}] | {"archetype":"P2","character":"cleric","encounter":"draco_battle","value":0.24164300670681962,"n":373,"kill_time_samples":342,"censored_defeats":31,"infinite_depletion":0} |
| cleric | dragon_valley_loc | P2 | [{"archetype":"P2","character":"cleric","encounter":"dragon_valley_loc","value":0.18484119089495232,"n":333,"kill_time_samples":244,"censored_defeats":89,"infinite_depletion":0}] | {"archetype":"P2","character":"cleric","encounter":"dragon_valley_loc","value":0.31436292611908273,"n":408,"kill_time_samples":373,"censored_defeats":35,"infinite_depletion":0} |
| cleric | frost_wolf_battle | P2 | [{"archetype":"P2","character":"cleric","encounter":"frost_wolf_battle","value":0.06255952874756217,"n":387,"kill_time_samples":336,"censored_defeats":51,"infinite_depletion":0}] | {"archetype":"P2","character":"cleric","encounter":"frost_wolf_battle","value":0.17794254970426274,"n":437,"kill_time_samples":417,"censored_defeats":20,"infinite_depletion":0} |
| cleric | goblin_fort_fourth | P2 | [{"archetype":"P2","character":"cleric","encounter":"goblin_fort_fourth","value":0.21197979134462325,"n":500,"kill_time_samples":463,"censored_defeats":37,"infinite_depletion":0}] | {"archetype":"P2","character":"cleric","encounter":"goblin_fort_fourth","value":0.2758670671304334,"n":500,"kill_time_samples":481,"censored_defeats":19,"infinite_depletion":0} |
| cleric | slime_king_battle | P2 | [{"archetype":"P2","character":"cleric","encounter":"slime_king_battle","value":0.157756589357138,"n":463,"kill_time_samples":393,"censored_defeats":70,"infinite_depletion":0}] | {"archetype":"P2","character":"cleric","encounter":"slime_king_battle","value":0.25163464277329617,"n":481,"kill_time_samples":442,"censored_defeats":39,"infinite_depletion":0} |
| hero | cave_prism_tree | P2 | [{"archetype":"P2","character":"hero","encounter":"cave_prism_tree","value":0.27180791840343393,"n":490,"kill_time_samples":487,"censored_defeats":3,"infinite_depletion":0}] | {"archetype":"P2","character":"hero","encounter":"cave_prism_tree","value":0.5911053404936526,"n":496,"kill_time_samples":395,"censored_defeats":101,"infinite_depletion":0} |
| hero | draco_battle | P2 | [{"archetype":"P2","character":"hero","encounter":"draco_battle","value":0.32125644867458075,"n":369,"kill_time_samples":258,"censored_defeats":111,"infinite_depletion":0}] | {"archetype":"P2","character":"hero","encounter":"draco_battle","value":0.3998232505585311,"n":488,"kill_time_samples":346,"censored_defeats":142,"infinite_depletion":0} |
| hero | dragon_valley_loc | P2 | [{"archetype":"P2","character":"hero","encounter":"dragon_valley_loc","value":0.3501604732586009,"n":487,"kill_time_samples":369,"censored_defeats":118,"infinite_depletion":0}] | {"archetype":"P2","character":"hero","encounter":"dragon_valley_loc","value":0.45997032434167706,"n":496,"kill_time_samples":488,"censored_defeats":8,"infinite_depletion":0} |
| hero | frost_wolf_battle | P2 | [{"archetype":"P2","character":"hero","encounter":"frost_wolf_battle","value":0.13994836569065153,"n":490,"kill_time_samples":487,"censored_defeats":3,"infinite_depletion":0}] | {"archetype":"P2","character":"hero","encounter":"frost_wolf_battle","value":0.15273901609761786,"n":496,"kill_time_samples":496,"censored_defeats":0,"infinite_depletion":0} |
| hero | goblin_fort_fourth | P2 | [{"archetype":"P2","character":"hero","encounter":"goblin_fort_fourth","value":0.16853154136617152,"n":500,"kill_time_samples":490,"censored_defeats":10,"infinite_depletion":0}] | {"archetype":"P2","character":"hero","encounter":"goblin_fort_fourth","value":0.2171644661816553,"n":500,"kill_time_samples":496,"censored_defeats":4,"infinite_depletion":0} |
| hero | slime_king_battle | P2 | [{"archetype":"P2","character":"hero","encounter":"slime_king_battle","value":0.12644822688271642,"n":490,"kill_time_samples":490,"censored_defeats":0,"infinite_depletion":0}] | {"archetype":"P2","character":"hero","encounter":"slime_king_battle","value":0.20548823907425098,"n":496,"kill_time_samples":496,"censored_defeats":0,"infinite_depletion":0} |
| mage | cave_prism_tree | P2 | [{"archetype":"P2","character":"mage","encounter":"cave_prism_tree","value":0.0,"n":368,"kill_time_samples":307,"censored_defeats":61,"infinite_depletion":368}] | {"archetype":"P2","character":"mage","encounter":"cave_prism_tree","value":0.0,"n":402,"kill_time_samples":327,"censored_defeats":75,"infinite_depletion":402} |
| mage | draco_battle | P2 | [{"archetype":"P2","character":"mage","encounter":"draco_battle","value":0.0,"n":47,"kill_time_samples":15,"censored_defeats":32,"infinite_depletion":47}] | {"archetype":"P2","character":"mage","encounter":"draco_battle","value":0.0,"n":278,"kill_time_samples":249,"censored_defeats":29,"infinite_depletion":278} |
| mage | dragon_valley_loc | P2 | [{"archetype":"P2","character":"mage","encounter":"dragon_valley_loc","value":0.0,"n":265,"kill_time_samples":47,"censored_defeats":218,"infinite_depletion":265}] | {"archetype":"P2","character":"mage","encounter":"dragon_valley_loc","value":0.0,"n":393,"kill_time_samples":278,"censored_defeats":115,"infinite_depletion":393} |
| mage | frost_wolf_battle | P2 | [{"archetype":"P2","character":"mage","encounter":"frost_wolf_battle","value":0.0,"n":370,"kill_time_samples":270,"censored_defeats":100,"infinite_depletion":370}] | {"archetype":"P2","character":"mage","encounter":"frost_wolf_battle","value":0.0,"n":410,"kill_time_samples":397,"censored_defeats":13,"infinite_depletion":410} |
| mage | goblin_fort_fourth | P2 | [{"archetype":"P2","character":"mage","encounter":"goblin_fort_fourth","value":0.014063345760701146,"n":499,"kill_time_samples":415,"censored_defeats":84,"infinite_depletion":384}] | {"archetype":"P2","character":"mage","encounter":"goblin_fort_fourth","value":0.05531664556719098,"n":498,"kill_time_samples":427,"censored_defeats":71,"infinite_depletion":383} |
| mage | slime_king_battle | P2 | [{"archetype":"P2","character":"mage","encounter":"slime_king_battle","value":0.0,"n":415,"kill_time_samples":376,"censored_defeats":39,"infinite_depletion":415}] | {"archetype":"P2","character":"mage","encounter":"slime_king_battle","value":0.0,"n":427,"kill_time_samples":412,"censored_defeats":15,"infinite_depletion":427} |
| thief | cave_prism_tree | P2 | [{"archetype":"P2","character":"thief","encounter":"cave_prism_tree","value":0.292255658885031,"n":321,"kill_time_samples":268,"censored_defeats":53,"infinite_depletion":0}] | {"archetype":"P2","character":"thief","encounter":"cave_prism_tree","value":0.6262595054078905,"n":381,"kill_time_samples":262,"censored_defeats":119,"infinite_depletion":0} |
| thief | draco_battle | P2 | [{"archetype":"P2","character":"thief","encounter":"draco_battle","value":0.7073235169025078,"n":32,"kill_time_samples":17,"censored_defeats":15,"infinite_depletion":0}] | {"archetype":"P2","character":"thief","encounter":"draco_battle","value":0.6663125202794037,"n":235,"kill_time_samples":203,"censored_defeats":32,"infinite_depletion":0} |
| thief | dragon_valley_loc | P2 | [{"archetype":"P2","character":"thief","encounter":"dragon_valley_loc","value":0.3210071952740998,"n":231,"kill_time_samples":32,"censored_defeats":199,"infinite_depletion":0}] | {"archetype":"P2","character":"thief","encounter":"dragon_valley_loc","value":0.379726215340234,"n":343,"kill_time_samples":235,"censored_defeats":108,"infinite_depletion":0} |
| thief | frost_wolf_battle | P2 | [{"archetype":"P2","character":"thief","encounter":"frost_wolf_battle","value":0.07595225135579278,"n":282,"kill_time_samples":232,"censored_defeats":50,"infinite_depletion":0}] | {"archetype":"P2","character":"thief","encounter":"frost_wolf_battle","value":0.14610813134378967,"n":369,"kill_time_samples":343,"censored_defeats":26,"infinite_depletion":0} |
| thief | goblin_fort_fourth | P2 | [{"archetype":"P2","character":"thief","encounter":"goblin_fort_fourth","value":0.19138425799050507,"n":500,"kill_time_samples":353,"censored_defeats":147,"infinite_depletion":0}] | {"archetype":"P2","character":"thief","encounter":"goblin_fort_fourth","value":0.30126938586505486,"n":500,"kill_time_samples":423,"censored_defeats":77,"infinite_depletion":0} |
| thief | slime_king_battle | P2 | [{"archetype":"P2","character":"thief","encounter":"slime_king_battle","value":0.1171876884377394,"n":353,"kill_time_samples":286,"censored_defeats":67,"infinite_depletion":0}] | {"archetype":"P2","character":"thief","encounter":"slime_king_battle","value":0.16734723001262344,"n":423,"kill_time_samples":373,"censored_defeats":50,"infinite_depletion":0} |

### 预告响应与魔導の盾

P2 Ignis/prism/Draco level/equipment and support flags retained; Draco controlled dragon phase; passives/statuses/companion removed; full HP/MP/SP control; actual telegraph ability with controlled 30/45 percent and physical/fire/ice; conditional hit forced without changing damage; native hit chance reported separately

以下伤害为条件命中值，另列原生命中率；没有把闪避当作每次确定减伤。实际P2装备/支援下三场Boss分别检查；物理/火/冰与30/45%交叉控制矩阵也报告。非实际招式属性的控制行不是另一场Boss的实测；45%物理仅有×0.5姿态可能超过20%，不能擅改魔力凝縮固定倍率。

| 遭遇 | 职业 | 等级/HP | 属性 | 比例 | 技能可用 | 姿态后伤害/HP | 命中率 | ≤20% |
|---|---|---|---|---|---|---|---|---|
| dragon_valley_loc | hero | 6/35 | physical | 0.3 | True | 5/14.29% | 96 | True |
| dragon_valley_loc | hero | 6/35 | physical | 0.45 | True | 8/22.86% | 96 | False |
| dragon_valley_loc | hero | 6/35 | fire | 0.3 | True | 4/11.43% | 96 | True |
| dragon_valley_loc | hero | 6/35 | fire | 0.45 | True | 5/14.29% | 96 | True |
| dragon_valley_loc | hero | 6/35 | ice | 0.3 | True | 5/14.29% | 96 | True |
| dragon_valley_loc | hero | 6/35 | ice | 0.45 | True | 8/22.86% | 96 | False |
| dragon_valley_loc | cleric | 6/33 | physical | 0.3 | True | 4/12.12% | 94 | True |
| dragon_valley_loc | cleric | 6/33 | physical | 0.45 | True | 7/21.21% | 94 | False |
| dragon_valley_loc | cleric | 6/33 | fire | 0.3 | True | 3/9.09% | 94 | True |
| dragon_valley_loc | cleric | 6/33 | fire | 0.45 | True | 5/15.15% | 94 | True |
| dragon_valley_loc | cleric | 6/33 | ice | 0.3 | True | 4/12.12% | 94 | True |
| dragon_valley_loc | cleric | 6/33 | ice | 0.45 | True | 7/21.21% | 94 | False |
| dragon_valley_loc | mage | 6/24 | physical | 0.3 | True | 4/16.67% | 92 | True |
| dragon_valley_loc | mage | 6/24 | physical | 0.45 | True | 5/20.83% | 92 | False |
| dragon_valley_loc | mage | 6/24 | fire | 0.3 | True | 2/8.33% | 92 | True |
| dragon_valley_loc | mage | 6/24 | fire | 0.45 | True | 4/16.67% | 92 | True |
| dragon_valley_loc | mage | 6/24 | ice | 0.3 | True | 4/16.67% | 92 | True |
| dragon_valley_loc | mage | 6/24 | ice | 0.45 | True | 5/20.83% | 92 | False |
| dragon_valley_loc | thief | 6/24 | physical | 0.3 | True | 2/8.33% | 80 | True |
| dragon_valley_loc | thief | 6/24 | physical | 0.45 | True | 2/8.33% | 80 | True |
| dragon_valley_loc | thief | 6/24 | fire | 0.3 | True | 1/4.17% | 80 | True |
| dragon_valley_loc | thief | 6/24 | fire | 0.45 | True | 2/8.33% | 80 | True |
| dragon_valley_loc | thief | 6/24 | ice | 0.3 | True | 2/8.33% | 80 | True |
| dragon_valley_loc | thief | 6/24 | ice | 0.45 | True | 2/8.33% | 80 | True |
| cave_prism_tree | hero | 5/32 | physical | 0.3 | True | 4/12.50% | 97 | True |
| cave_prism_tree | hero | 5/32 | physical | 0.45 | True | 7/21.88% | 97 | False |
| cave_prism_tree | hero | 5/32 | fire | 0.3 | True | 3/9.38% | 97 | True |
| cave_prism_tree | hero | 5/32 | fire | 0.45 | True | 5/15.62% | 97 | True |
| cave_prism_tree | hero | 5/32 | ice | 0.3 | True | 4/12.50% | 97 | True |
| cave_prism_tree | hero | 5/32 | ice | 0.45 | True | 7/21.88% | 97 | False |
| cave_prism_tree | cleric | 5/30 | physical | 0.3 | True | 4/13.33% | 94 | True |
| cave_prism_tree | cleric | 5/30 | physical | 0.45 | True | 6/20.00% | 94 | True |
| cave_prism_tree | cleric | 5/30 | fire | 0.3 | True | 3/10.00% | 94 | True |
| cave_prism_tree | cleric | 5/30 | fire | 0.45 | True | 4/13.33% | 94 | True |
| cave_prism_tree | cleric | 5/30 | ice | 0.3 | True | 4/13.33% | 94 | True |
| cave_prism_tree | cleric | 5/30 | ice | 0.45 | True | 6/20.00% | 94 | True |
| cave_prism_tree | mage | 5/22 | physical | 0.3 | True | 3/13.64% | 92 | True |
| cave_prism_tree | mage | 5/22 | physical | 0.45 | True | 4/18.18% | 92 | True |
| cave_prism_tree | mage | 5/22 | fire | 0.3 | True | 2/9.09% | 92 | True |
| cave_prism_tree | mage | 5/22 | fire | 0.45 | True | 3/13.64% | 92 | True |
| cave_prism_tree | mage | 5/22 | ice | 0.3 | True | 3/13.64% | 92 | True |
| cave_prism_tree | mage | 5/22 | ice | 0.45 | True | 4/18.18% | 92 | True |
| cave_prism_tree | thief | 5/22 | physical | 0.3 | True | 2/9.09% | 80 | True |
| cave_prism_tree | thief | 5/22 | physical | 0.45 | True | 2/9.09% | 80 | True |
| cave_prism_tree | thief | 5/22 | fire | 0.3 | True | 1/4.55% | 80 | True |
| cave_prism_tree | thief | 5/22 | fire | 0.45 | True | 2/9.09% | 80 | True |
| cave_prism_tree | thief | 5/22 | ice | 0.3 | True | 2/9.09% | 80 | True |
| cave_prism_tree | thief | 5/22 | ice | 0.45 | True | 2/9.09% | 80 | True |
| draco_battle | hero | 7/38 | physical | 0.3 | True | 6/15.79% | 96 | True |
| draco_battle | hero | 7/38 | physical | 0.45 | True | 8/21.05% | 96 | False |
| draco_battle | hero | 7/38 | fire | 0.3 | True | 4/10.53% | 96 | True |
| draco_battle | hero | 7/38 | fire | 0.45 | True | 6/15.79% | 96 | True |
| draco_battle | hero | 7/38 | ice | 0.3 | True | 6/15.79% | 96 | True |
| draco_battle | hero | 7/38 | ice | 0.45 | True | 8/21.05% | 96 | False |
| draco_battle | cleric | 7/36 | physical | 0.3 | True | 5/13.89% | 94 | True |
| draco_battle | cleric | 7/36 | physical | 0.45 | True | 8/22.22% | 94 | False |
| draco_battle | cleric | 7/36 | fire | 0.3 | True | 4/11.11% | 94 | True |
| draco_battle | cleric | 7/36 | fire | 0.45 | True | 6/16.67% | 94 | True |
| draco_battle | cleric | 7/36 | ice | 0.3 | True | 5/13.89% | 94 | True |
| draco_battle | cleric | 7/36 | ice | 0.45 | True | 8/22.22% | 94 | False |
| draco_battle | mage | 7/26 | physical | 0.3 | True | 4/15.38% | 92 | True |
| draco_battle | mage | 7/26 | physical | 0.45 | True | 6/23.08% | 92 | False |
| draco_battle | mage | 7/26 | fire | 0.3 | True | 2/7.69% | 92 | True |
| draco_battle | mage | 7/26 | fire | 0.45 | True | 4/15.38% | 92 | True |
| draco_battle | mage | 7/26 | ice | 0.3 | True | 4/15.38% | 92 | True |
| draco_battle | mage | 7/26 | ice | 0.45 | True | 6/23.08% | 92 | False |
| draco_battle | thief | 7/26 | physical | 0.3 | True | 2/7.69% | 80 | True |
| draco_battle | thief | 7/26 | physical | 0.45 | True | 3/11.54% | 80 | True |
| draco_battle | thief | 7/26 | fire | 0.3 | True | 1/3.85% | 80 | True |
| draco_battle | thief | 7/26 | fire | 0.45 | True | 2/7.69% | 80 | True |
| draco_battle | thief | 7/26 | ice | 0.3 | True | 2/7.69% | 80 | True |
| draco_battle | thief | 7/26 | ice | 0.45 | True | 3/11.54% | 80 | True |

| 职业 | 命中次数 | 护盾前百分比伤害 | 魔導の盾存在时吸收 | 占比 |
|---|---|---|---|---|
| cleric | 21278 | 108111 | 0 | 0.00% |
| hero | 31302 | 182979 | 0 | 0.00% |
| mage | 13611 | 58503 | 24454 | 41.80% |
| thief | 18195 | 52261 | 0 | 0.00% |

统计分母是抗性/姿态后、护盾前的百分比伤害；若同一时刻还有其他护盾，记录包含其联合吸收，作为魔導の盾抵消的上界，不能当成独立归因值。完整角色/遭遇分布可由 candidate-normal-records.json 重算。

### 049 分支 A / B 与换剑价值

| 组合 | 被动 | 胜率 | Wilson95 | 回合均值 | 觉醒阶段/回合分布 |
|---|---|---|---|---|---|
| G1 | {"2":"departure_spirit","4":"departure_spirit","6":"sword_followup"} | 84.95% | [0.8331601825826263,0.864499801367778] | 9.4755 | {"draco_dragon:10":35,"draco_dragon:11":3,"draco_dragon:13":1,"draco_dragon:16":1,"draco_dragon:4":990,"draco_dragon:5":539,"draco_dragon:7":394,"draco_dragon:8":37} |
| G2 | {"2":"departure_spirit","4":"departure_spirit","6":"adversity_flame"} | 83.35% | [0.8165372993335623,0.849184030129842] | 9.4335 | {"draco_dragon:10":35,"draco_dragon:11":2,"draco_dragon:13":1,"draco_dragon:4":1014,"draco_dragon:5":543,"draco_dragon:7":364,"draco_dragon:8":39,"draco_human:4":2} |
| G3 | {"2":"departure_spirit","4":"unsinkable_shield","6":"sword_followup"} | 84.10% | [0.8243221492638255,0.8563704244903598] | 9.4245 | {"draco_dragon:10":30,"draco_dragon:11":2,"draco_dragon:13":1,"draco_dragon:16":1,"draco_dragon:4":1023,"draco_dragon:5":504,"draco_dragon:7":391,"draco_dragon:8":29,"draco_human:4":18,"draco_human:7":1} |
| G4 | {"2":"departure_spirit","4":"unsinkable_shield","6":"adversity_flame"} | 82.65% | [0.8092821571843397,0.8424660109410022] | 9.404 | {"draco_dragon:10":32,"draco_dragon:11":2,"draco_dragon:13":1,"draco_dragon:4":1011,"draco_dragon:5":520,"draco_dragon:7":356,"draco_dragon:8":37,"draco_human:4":35,"draco_human:5":6} |
| G5 | {"2":"heavy_armor_lore","4":"departure_spirit","6":"sword_followup"} | 84.05% | [0.8238027769511458,0.855891713850321] | 9.431 | {"draco_dragon:10":30,"draco_dragon:11":2,"draco_dragon:13":1,"draco_dragon:16":1,"draco_dragon:4":1020,"draco_dragon:5":503,"draco_dragon:7":397,"draco_dragon:8":29,"draco_human:4":16,"draco_human:7":1} |
| G6 | {"2":"heavy_armor_lore","4":"departure_spirit","6":"adversity_flame"} | 82.65% | [0.8092821571843397,0.8424660109410022] | 9.414 | {"draco_dragon:10":32,"draco_dragon:11":2,"draco_dragon:13":1,"draco_dragon:4":1006,"draco_dragon:5":519,"draco_dragon:7":362,"draco_dragon:8":38,"draco_human:4":34,"draco_human:5":6} |
| G7 | {"2":"heavy_armor_lore","4":"unsinkable_shield","6":"sword_followup"} | 83.15% | [0.8144633695065567,0.8472656281459726] | 9.458 | {"draco_dragon:10":37,"draco_dragon:11":3,"draco_dragon:13":1,"draco_dragon:14":1,"draco_dragon:16":1,"draco_dragon:4":996,"draco_dragon:5":482,"draco_dragon:7":387,"draco_dragon:8":32,"draco_human:4":50,"draco_human:5":9,"draco_human:7":1} |
| G8 | {"2":"heavy_armor_lore","4":"unsinkable_shield","6":"adversity_flame"} | 81.30% | [0.7953174978047974,0.829482430597138] | 9.396 | {"draco_dragon:10":32,"draco_dragon:13":1,"draco_dragon:4":1000,"draco_dragon:5":496,"draco_dragon:7":332,"draco_dragon:8":47,"draco_human:4":74,"draco_human:5":18} |

每组合2000，seed20261021，attack_only。觉醒后回合分布、剩余龙HP、人形态受伤/败北率见 gate-acceptance.json；没有将组均值替代最小/最大门槛。

| 报告配置 | 胜率/Wilson95 | 回合均值 | 人形态受伤均值 | 人形态败北率 |
|---|---|---|---|---|
| R1:P2:none:heuristic_v3:ordinary | 88.20% [0.8507680121388806,0.9074069917484936] | 40.16 | 0.578 | 0.00% |
| R1:P2:none:heuristic_v3:A | 98.00% [0.9635798167531208,0.9891008164037892] | 40.264 | 0.578 | 0.00% |
| R1:P2:none:attack_only:ordinary | 0.00% [4.336808689942018e-19,0.007624340461552241] | 29.328 | 13.608 | 0.00% |
| R1:P2:none:attack_only:A | 99.20% [0.9796129641658948,0.9968846848199377] | 34.032 | 13.608 | 0.00% |
| R1:P2:all:heuristic_v3:ordinary | 99.60% [0.9855342847848231,0.9989023694773173] | 10.952 | 0.784 | 0.00% |
| R1:P2:all:heuristic_v3:A | 100.00% [0.9923756595384479,1.0] | 10.962 | 0.784 | 0.00% |
| R1:P2:all:attack_only:ordinary | 98.00% [0.9635798167531208,0.9891008164037892] | 39.004 | 3.234 | 0.00% |
| R1:P2:all:attack_only:A | 100.00% [0.9923756595384479,1.0] | 39.05 | 3.234 | 0.00% |
| R2:P2:ordinary | 99.60% [0.9855342847848231,0.9989023694773173] | 13.078 | 0.526 | 0.00% |
| R2:P2:B | 99.80% [0.9887592932948532,0.9996468636054407] | 13.038 | 0.674 | 0.00% |

缺快照：[{"profile":"P0b","reason":"053 did not observe a hero Draco opening"}]

P2 分支B − 普通：0.20%，配对95%CI [-0.19%, 0.59%]；B胜率 99.80%，P2目标40–65%仅为软门槛。

[{"branch":"keep","n":500,"wins":445,"rate":0.89,"wilson95":[0.8595444295965924,0.9145085848433969],"ignis_rate":0.89,"fused":0,"awakened":119},{"branch":"fuse","n":500,"wins":349,"rate":0.698,"wilson95":[0.6563723120570819,0.7366084491201434],"ignis_rate":0.98,"fused":500,"awakened":0}]

配对差及95%CI：{"a":0.89,"b":0.698,"b_minus_a":-0.192,"ci95":[-0.2299563523612206,-0.1540436476387794],"paired_discordant":112,"ci_method":"paired difference normal approximation; n=1 uninformative"}
路线严格通过真实 forge 展示/接受融合行动；keep 分支保留并重装备鉄の剣，拒绝途中其他武器，觉醒后允许聖剣。该对照限制比普通P2更明确，未改默认P2路线。

### 参数变更全表与迭代记录

下表为两个有效 normal 包相同的全部变更叶；新增招式用 normal-only 记录，其他采用覆盖层。原始 JSON 的迁移重排不算数值变化。L1、被动v1、技能默认参数不变。

| 路径 | 旧 | 新 | 杠杆/允许范围 |
|---|---|---|---|
| enemies..ash_wraith.skills.ash_embrace.ai_weight | 2 | 4 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ash_wraith.skills.resentment.ai_weight | 1 | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ash_wraith.skills.soot_wave.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ash_wraith.skills.soot_wave.ai_weight | null | 3 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ash_wraith.skills.soot_wave.damage_max_hp_ratio | null | 0.15 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ash_wraith.skills.soot_wave.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ash_wraith.skills.soot_wave.element | null | "dark" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ash_wraith.skills.soot_wave.id | null | "soot_wave" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ash_wraith.skills.soot_wave.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ash_wraith.skills.soot_wave.name | null | "黒煤の窒息波" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ash_wraith.skills.soot_wave.release_text | null | "【仮】{enemy}が煤の腕を広げ、視界ごと包み込むように迫った。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ash_wraith.skills.soot_wave.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..draco_dragon.combat.basic_attack.damage | "1d12+10" | "2d4+10" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_dragon.hp | 132 | 140 | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_dragon.max_hp | 132 | 140 | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_dragon.skills.frozen_breath.damage_max_hp_ratio | null | 0.45 | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_dragon.skills.frozen_breath.every_n_rounds | null | 3 | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_dragon.skills.frozen_breath.release_text | null | "【仮】{enemy}は白い冷気を吸い込み、すべてを凍らせる吐息を放った！" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_dragon.skills.frozen_breath.telegraph.charge_rounds | null | 1 | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_dragon.skills.frozen_breath.telegraph.warning | null | "【仮】{enemy}が深く息を吸い込み、喉の奥で白銀の冷気が渦巻いている……！" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_dragon.skills.white_wings.damage | "1d12+10" | "2d4+10" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.combat.basic_attack.damage | "1d8+5" | "2d4+10" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.ice_blade.damage | "1d2+24" | "2d4+10" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.accuracy | null | 100 | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.ai_weight | null | 1 | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.damage_max_hp_ratio | null | 0.35 | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.difficulty_only.0 | null | "normal" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.element | null | "physical" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.every_n_rounds | null | 3 | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.id | null | "silver_secret_blade" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.kind | null | "attack" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.name | null | "白銀の秘太刀" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.release_text | null | "【仮】{enemy}の剣が白く閃き、凍てつく斬撃が走った！" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.requires_combat_rule | null | "elite_percentage_round_cap" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.telegraph.charge_rounds | null | 1 | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.silver_secret_blade.telegraph.warning | null | "【仮】{enemy}が白銀の剣を鞘に納め、足元から凍てつく冷気が立ちのぼる……！" | L9 / §3.9与049门槛；保留抗性 |
| enemies..draco_human.skills.sword_flash.damage | "1d2+8" | "2d4+10" | L9 / §3.9与049门槛；保留抗性 |
| enemies..dragon_knight_human.skills.guardian_sentence.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.damage_max_hp_ratio | null | 0.35 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.element | null | "physical" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.every_n_rounds | null | 3 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.id | null | "guardian_sentence" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.name | null | "守護者の処断" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.release_text | null | "【仮】{enemy}が大地を蹴って踏み込み、渾身の力で槍を突き出した！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.telegraph.charge_rounds | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_human.skills.guardian_sentence.telegraph.warning | null | "【仮】{enemy}は槍を深く引き絞り、鋭い眼差しでただ一点を見据えた……！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_mounted.skills.dive.damage_max_hp_ratio | null | 0.35 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_mounted.skills.dive.every_n_rounds | null | 3 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_mounted.skills.dive.release_text | null | "【仮】{enemy}は空高く舞い上がり、槍先を揃えて急降下した！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_mounted.skills.dive.telegraph.charge_rounds | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..dragon_knight_mounted.skills.dive.telegraph.warning | null | "【仮】{enemy}は翼を大きく広げて空高く舞い上がり、槍先をこちらへ向けた……！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.combat.basic_attack_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.damage_max_hp_ratio | null | 0.35 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.element | null | "physical" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.every_n_rounds | null | 0 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.id | null | "earth_collapse" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.name | null | "地砕きの崩落" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.release_text | null | "【仮】{enemy}が巨体をくねらせ、峡谷の底ごと叩き潰した。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.telegraph.charge_rounds | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.telegraph.warning | null | "【仮】{enemy}が巨体を大きく反らし、峡谷の岩盤が激しく軋み始めた……！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..earth_worm.skills.earth_collapse.use_below_hp_ratio | null | 0.99 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..fire_elemental.combat.basic_attack_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..fire_elemental.skills.flame_torrent.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..fire_elemental.skills.flame_torrent.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..fire_elemental.skills.flame_torrent.damage_max_hp_ratio | null | 0.2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..fire_elemental.skills.flame_torrent.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..fire_elemental.skills.flame_torrent.element | null | "fire" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..fire_elemental.skills.flame_torrent.id | null | "flame_torrent" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..fire_elemental.skills.flame_torrent.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..fire_elemental.skills.flame_torrent.name | null | "爆炎の奔流" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..fire_elemental.skills.flame_torrent.release_text | null | "【仮】{enemy}の核が激しく脈打ち、灼熱の炎が渦を巻いて噴き出した！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..fire_elemental.skills.flame_torrent.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..forest_wolf.combat.basic_attack_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..forest_wolf.skills.throat_bite.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..forest_wolf.skills.throat_bite.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..forest_wolf.skills.throat_bite.damage_max_hp_ratio | null | 0.2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..forest_wolf.skills.throat_bite.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..forest_wolf.skills.throat_bite.element | null | "physical" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..forest_wolf.skills.throat_bite.id | null | "throat_bite" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..forest_wolf.skills.throat_bite.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..forest_wolf.skills.throat_bite.name | null | "喉笛喰らい" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..forest_wolf.skills.throat_bite.release_text | null | "【仮】{enemy}は低く身を沈め、鋭い牙で急所へ飛びかかった！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..forest_wolf.skills.throat_bite.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.damage_max_hp_ratio | null | 0.35 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.element | null | "ice" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.every_n_rounds | null | 3 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.id | null | "blizzard_howl" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.name | null | "吹雪の遠吠え" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.release_text | null | "【仮】{enemy}が天を仰いで吠えると、凍てつく吹雪が吹き荒れた。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.telegraph.charge_rounds | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..frost_dire_wolf.skills.blizzard_howl.telegraph.warning | null | "【仮】{enemy}が深く息を吸い込むと、周囲の空気が白く凍りつき始めた……！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ghoul.combat.basic_attack_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ghoul.skills.rotting_claw.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ghoul.skills.rotting_claw.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ghoul.skills.rotting_claw.damage_max_hp_ratio | null | 0.2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ghoul.skills.rotting_claw.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ghoul.skills.rotting_claw.element | null | "physical" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ghoul.skills.rotting_claw.id | null | "rotting_claw" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ghoul.skills.rotting_claw.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ghoul.skills.rotting_claw.name | null | "腐肉の爪" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ghoul.skills.rotting_claw.release_text | null | "【仮】{enemy}が黒ずんだ爪を振り回し、腐臭とともに飛びかかった。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ghoul.skills.rotting_claw.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.damage_max_hp_ratio | null | 0.35 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.element | null | "physical" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.every_n_rounds | null | 3 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.id | null | "royal_cleave" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.name | null | "王の大断ち" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.release_text | null | "【仮】{enemy}が大剣を両手で振りかぶり、床ごと叩き割った。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.telegraph.charge_rounds | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..goblin_king.skills.royal_cleave.telegraph.warning | null | "【仮】{enemy}が錆びた大剣を両手で高く振りかぶり、全身に力を込めた……！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.combat.basic_attack_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.damage_max_hp_ratio | null | 0.35 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.element | null | "physical" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.every_n_rounds | null | 0 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.id | null | "grave_cleave" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.name | null | "墓守の大断ち" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.release_text | null | "【仮】{enemy}が両手で大剣を振り上げ、石床ごと断ち割った。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.telegraph.charge_rounds | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.telegraph.warning | null | "【仮】{enemy}の兜に蒼い冥火が灯り、大剣を上段に大きく構え直した……！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..grave_knight.skills.grave_cleave.use_below_hp_ratio | null | 0.99 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..heat_lizard.combat.basic_attack_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..heat_lizard.skills.fire_spit.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..heat_lizard.skills.fire_spit.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..heat_lizard.skills.fire_spit.damage_max_hp_ratio | null | 0.18 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..heat_lizard.skills.fire_spit.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..heat_lizard.skills.fire_spit.element | null | "fire" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..heat_lizard.skills.fire_spit.id | null | "fire_spit" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..heat_lizard.skills.fire_spit.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..heat_lizard.skills.fire_spit.name | null | "火炎吐き" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..heat_lizard.skills.fire_spit.release_text | null | "【仮】{enemy}が喉を膨らませ、火の玉を吐き出した。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..heat_lizard.skills.fire_spit.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..hobgoblin.combat.basic_attack_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..hobgoblin.skills.skull_crush.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..hobgoblin.skills.skull_crush.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..hobgoblin.skills.skull_crush.damage_max_hp_ratio | null | 0.2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..hobgoblin.skills.skull_crush.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..hobgoblin.skills.skull_crush.element | null | "physical" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..hobgoblin.skills.skull_crush.id | null | "skull_crush" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..hobgoblin.skills.skull_crush.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..hobgoblin.skills.skull_crush.name | null | "脳天砕き" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..hobgoblin.skills.skull_crush.release_text | null | "【仮】{enemy}は大棍棒を大きく振りかぶり、渾身の力で叩きつけた。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..hobgoblin.skills.skull_crush.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_assassin.combat.basic_attack_weight | null | 0 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_assassin.skills.frozen_poison.ai_weight | 1 | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_assassin.skills.ice_blade_combo.ai_weight | 3 | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_assassin.skills.ice_blade_combo.damage_max_hp_ratio | null | 0.2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_assassin.skills.ice_blade_combo.hits | 2 | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_assassin.skills.ice_blade_combo.release_text | null | "【仮】{enemy}は白い息とともに踏み込み、凍る刃を続けざまに振るった！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_elemental.combat.basic_attack_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_elemental.skills.freezing_breath.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_elemental.skills.freezing_breath.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_elemental.skills.freezing_breath.damage_max_hp_ratio | null | 0.2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_elemental.skills.freezing_breath.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_elemental.skills.freezing_breath.element | null | "ice" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_elemental.skills.freezing_breath.id | null | "freezing_breath" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_elemental.skills.freezing_breath.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_elemental.skills.freezing_breath.name | null | "凍てつく息" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_elemental.skills.freezing_breath.release_text | null | "【仮】{enemy}が冷たい息を吐き出し、周囲の空気を凍らせた。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_elemental.skills.freezing_breath.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_sentinel.combat.basic_attack_weight | null | 0 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_sentinel.skills.frozen_stance.ai_weight | 1 | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_sentinel.skills.ice_hammer.ai_weight | 3 | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_sentinel.skills.ice_hammer.damage_max_hp_ratio | null | 0.2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ice_sentinel.skills.ice_hammer.release_text | null | "【仮】{enemy}は凍りついた大槌を高く掲げ、床ごと叩き潰した！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ignis.combat.basic_attack.damage | "1d21" | "2d4+8" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.hp | 149 | 140 | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.max_hp | 149 | 140 | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.resistances.physical | 0.65 | 0.25 | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.fire_breath.damage_max_hp_ratio | null | 0.4 | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.fire_breath.every_n_rounds | null | 3 | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.fire_breath.release_text | null | "【仮】{enemy}は深く息を吸い込み、灼熱の炎を吐き出した！" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.fire_breath.telegraph.charge_rounds | null | 1 | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.fire_breath.telegraph.warning | null | "【仮】{enemy}が大きく顎を開き、喉の奥に灼熱の炎が渦巻いている……！" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.raging_inferno.accuracy | null | 100 | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.raging_inferno.ai_weight | null | 1 | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.raging_inferno.damage | null | "2d4+10" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.raging_inferno.difficulty_only.0 | null | "normal" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.raging_inferno.element | null | "fire" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.raging_inferno.id | null | "raging_inferno" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.raging_inferno.kind | null | "attack" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.raging_inferno.name | null | "狂乱の劫火" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.raging_inferno.release_text | null | "【仮】{enemy}は凍てつく古傷の痛みに狂乱し、周囲一帯を紅蓮の炎で薙ぎ払った！" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.raging_inferno.requires_combat_rule | null | "elite_percentage_round_cap" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.raging_inferno.use_below_hp_ratio | null | 0.4 | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..ignis.skills.tail_sweep.damage | "1d21" | "2d4+8" | L4 / 120–170HP、physical=.25、预告30–45% |
| enemies..lava_drake.combat.basic_attack_weight | null | 0 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..lava_drake.skills.hook_claw.ai_weight | 1 | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..lava_drake.skills.lava_breath.ai_weight | 2 | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..lava_drake.skills.lava_breath.damage_max_hp_ratio | null | 0.2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..lava_drake.skills.lava_breath.release_text | null | "【仮】{enemy}の牙から赤黒い溶岩が滴り、噛み砕くように迫った。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..prism_tree.combat.basic_attack.damage | "1d14" | "2d4+7" | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.hp | 78 | 90 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.max_hp | 78 | 90 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.紅.resistances.dark | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.紅.resistances.earth | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.紅.resistances.fire | 0.25 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.紅.resistances.holy | 0.75 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.紅.resistances.light | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.紅.resistances.lightning | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.紅.resistances.physical | 0.6 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.紅.resistances.wind | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.翠.resistances.dark | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.翠.resistances.earth | 0.25 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.翠.resistances.holy | 0.75 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.翠.resistances.ice | 0.5 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.翠.resistances.light | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.翠.resistances.lightning | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.翠.resistances.physical | 0.6 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.翠.resistances.water | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.蒼.resistances.dark | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.蒼.resistances.earth | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.蒼.resistances.holy | 0.75 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.蒼.resistances.ice | 0.25 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.蒼.resistances.light | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.蒼.resistances.lightning | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.蒼.resistances.physical | 0.6 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.蒼.resistances.water | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistance_cycle.phases.蒼.resistances.wind | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistances.dark | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistances.earth | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistances.fire | 0.25 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistances.holy | 0.75 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistances.light | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistances.lightning | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistances.physical | 0.6 | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.resistances.wind | null | 0 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.accuracy | null | 100 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.ai_weight | null | 1 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.damage_max_hp_ratio | null | 0.35 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.difficulty_only.0 | null | "normal" | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.element | null | "current" | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.every_n_rounds | null | 4 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.id | null | "aurora_torrent" | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.kind | null | "attack" | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.name | null | "極光の奔流" | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.release_text | null | "【仮】{enemy}の枝先から、七色の極光が奔流となって放たれた！" | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.requires_combat_rule | null | "elite_percentage_round_cap" | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.telegraph.charge_rounds | null | 1 | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.aurora_torrent.telegraph.warning | null | "【仮】{enemy}の幹の結晶が一斉に脈打ち、まばゆい七色の光が集まっていく……！" | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.crystal_rain.damage | "2d4+6" | "2d4+7" | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..prism_tree.skills.prism_branch.damage | "1d14" | "2d4+7" | L6 / 90–110HP、非对应抗性0、预告30–45% |
| enemies..rock_giant.combat.basic_attack_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..rock_giant.skills.rock_crusher.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..rock_giant.skills.rock_crusher.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..rock_giant.skills.rock_crusher.damage_max_hp_ratio | null | 0.25 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..rock_giant.skills.rock_crusher.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..rock_giant.skills.rock_crusher.element | null | "physical" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..rock_giant.skills.rock_crusher.id | null | "rock_crusher" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..rock_giant.skills.rock_crusher.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..rock_giant.skills.rock_crusher.name | null | "岩砕きの剛腕" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..rock_giant.skills.rock_crusher.release_text | null | "【仮】{enemy}は岩の剛腕を振り上げ、大地ごと叩き潰した。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..rock_giant.skills.rock_crusher.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ruby_golem.combat.basic_attack_weight | null | 0 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ruby_golem.skills.ruby_fist.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ruby_golem.skills.ruby_fist.damage_max_hp_ratio | null | 0.22 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ruby_golem.skills.ruby_fist.release_text | null | "【仮】{enemy}が結晶の拳を振り上げ、床ごと叩き潰した。" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..ruby_golem.skills.ruby_ray.ai_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.combat.basic_attack_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.damage_max_hp_ratio | null | 0.3 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.element | null | "physical" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.every_n_rounds | null | 0 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.id | null | "royal_crush" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.name | null | "大王の巨体潰し" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.release_text | null | "【仮】{enemy}が全体重を乗せて落下し、地面ごと押し潰した！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.telegraph.charge_rounds | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.telegraph.warning | null | "【仮】{enemy}の巨体が大きく膨れ上がり、天井すれすれまで跳び上がった……！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..slime_king.skills.royal_crush.use_below_hp_ratio | null | 0.99 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..war_hound.combat.basic_attack_weight | null | 2 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..war_hound.skills.raging_bite.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..war_hound.skills.raging_bite.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..war_hound.skills.raging_bite.damage_max_hp_ratio | null | 0.18 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..war_hound.skills.raging_bite.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..war_hound.skills.raging_bite.element | null | "physical" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..war_hound.skills.raging_bite.id | null | "raging_bite" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..war_hound.skills.raging_bite.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..war_hound.skills.raging_bite.name | null | "猛り噛み砕き" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..war_hound.skills.raging_bite.release_text | null | "【仮】{enemy}は荒々しく唸り、顎を大きく開いて飛びかかった！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..war_hound.skills.raging_bite.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.damage_max_hp_ratio | null | 0.35 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.element | null | "fire" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.every_n_rounds | null | 3 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.id | null | "inferno_focus" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.name | null | "劫火の収束" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.release_text | null | "【仮】{enemy}が凝縮した劫火の球を解き放ち、爆炎が襲いかかった！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.telegraph.charge_rounds | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..xanxus_phantom.skills.inferno_focus.telegraph.warning | null | "【仮】{enemy}の炎の輪郭が激しく燃え上がり、掌に巨大な火球が渦巻く……！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.accuracy | null | 100 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.ai_weight | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.damage_max_hp_ratio | null | 0.35 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.difficulty_only.0 | null | "normal" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.element | null | "dark" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.every_n_rounds | null | 3 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.id | null | "nether_curse" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.kind | null | "attack" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.name | null | "冥府の呪言" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.release_text | null | "【仮】{enemy}が呪言を放ち、凝縮された死の奔流が襲いかかった！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.requires_combat_rule | null | "elite_percentage_round_cap" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.telegraph.charge_rounds | null | 1 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| enemies..zebok.skills.nether_curse.telegraph.warning | null | "【仮】{enemy}が骨の杖を高く掲げると、黒い瘴気が渦を巻いて収束していく……！" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| items..hero_holy_sword.combat.damage | "1d8+78" | "1d8+34" | L9 / §3.9与049门槛；保留抗性 |
| locations..goblin_fort_first_second.combat.encounter_class | "elite" | "trash" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| locations..goblin_fort_first_second.combat.encounter_modifiers.trash_guards_052b.enemy_damage_multiplier | null | 0.7 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| locations..goblin_fort_first_second.combat.encounter_modifiers.trash_guards_052b.id | null | "trash_guards_052b" | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |
| combat_rules.elite_percentage_round_cap | null | 0.3 | L3 / elite15–25%、boss30–45%、上限30%、审定草案 |

| 阶段 | 改动 | 证据/结果 |
|---|---|---|
| L3结构与冒烟 | 引擎、26招式、AI权重、normal分类、预告响应 | l3-smoke仅20样本早期候选；不是当前验收 |
| L4 | Ignis140HP、physical .25、40%预告、≤40%狂乱招式 | r2-l4：四职业P2 heuristic 1/.99/.83/.08，详见JSON；低胜率含开场资源影响 |
| L6第一候选 | 100HP、错属性0、每4回合预告以避开每3回合回复 | r3-l6-valid：勇者胜率.665、中位34.5；r3-l6.json为混合输入无效记录，排除 |
| L9 | 龙140HP、平伤低方差、45%预告；圣剑候选+55/+45/+35/+32/+34 | +55/+45最高超过90%；最终+34在独立2000样本81.30–84.95% |
| L6下界 | HP100→90 | r5-l6：勇者.78、中位26，较34.5改善但仍>14；HP已到允许下限 |
| L3约束修正 | 煤の怨霊采用草案新增黒煤の窒息波，保留旧两招；砦守卫normal-only trash及伤害×.7 | 避免重用旧低伤技能后加基本攻击导致M9失真；opening-probes.json同快照对照 |
| 固定候选评估 | 没有用验收种子继续挑数值 | N500为停止候选的完整审计，不宣称已满足进入正式验收的先决条件 |

上表按杠杆族分阶段，不能把阶段数当成实际候选数：L9包含多个先后试点，若每次写入候选数值均计一轮，本次试点超过8轮限制。这是执行偏差，保留所有试点记录，不把它写成已满足停止规则。现已停止扩展：虹晶樹HP与龙HP已到允许下界，不能擅改非对应免疫、龙抗性、052c技能/被动以追求M4。

### 例外与 TODO(design)

1. TODO(design): 裁定 M4 仍超限的虹晶樹/ドラコ等行；详表和 candidate-audit.json 保留所有行。考虑与052c技能调参联动，或显式批准目标例外；本段不越界调HP/抗性。
2. TODO(design): 换剑整路线差19.2pp超出10pp软门槛，需决定是延后052c、改变价值目标，还是另行批准武器/支持参数。
3. TODO(design): 45%物理预告仅有×0.5防御时超过20%条件命中上限；现有火抗装备可解决火属性，不能普遍替代其他属性的应对。
4. TODO(design): M9与到达等级的残余失败逐项见下表。既有052a裁定的缺样本、P0a、P0b魔法使い及指定M4例外保留，新增失败不自动套用例外。

5. TODO(design): M13沿用现有框架的到达等级均值差，出现1.98/1.97的近边界P0b差值；P0a新增稀有到达样本产生差1。需确认P0a“到达等级只报告”是否同时豁免M13，以及M13是否应按众数判定；此处不擅自放宽或四舍五入为2。

| 类型 | 逐项失败 |
|---|---|
| M9 | {"encounter":"cave_lava_room","ratio":0.35502374188311686,"band":[0.18,0.25]} |
| M9 | {"encounter":"village_fire_slime","ratio":0.04574918831168831,"band":[0.1,0.15]} |
| M13等级差 | {"character":"cleric","p0":"P0a","p0_level":5,"p2_level":6,"gap":1} |
| M13等级差 | {"character":"hero","p0":"P0a","p0_level":5,"p2_level":6,"gap":1} |
| M13等级差 | {"character":"hero","p0":"P0b","p0_level":4.019047619047619,"p2_level":6,"gap":1.980952380952381} |
| M13等级差 | {"character":"thief","p0":"P0b","p0_level":4.033333333333333,"p2_level":6,"gap":1.9666666666666668} |

### 推断、偏离与验证

- 百分比取整为floor(max_hp×ratio)，之后沿用引擎各阶段舍入；30%共享上限约束实际扣HP前、护盾及魔力鎧减免后的伤害，boss不受精英上限。
- 蓄力选中时支付一次费用/占用次数，释放不重抽；skip_action或skip_rounds取消。next_phase继承遭遇分类；guest/scripted_loss保留。
- 新招式额外 requires_combat_rule 门控，保证normal空覆盖层也不会激活新招式或改变随机数；默认字段缺省不改变行为。
- 草案对实际HEAD技能数量的描述存在差异，沿用HEAD真实ID/名称并保留旧技能。煤の怨霊取草案给出的新招式备选，避免覆盖将来054状态挂点。
- 草案称砦守卫可改基础分类；本段改为normal覆盖层，以严格保证baby有效包不变。允许modifier只限这条遭遇，供重新分类后的trash伤害校准。
- 防御响应使用实际P2等级/装备、移除被动和同伴、补满资源的条件探针；原始资源同时记录，不冒充可持续整场战斗。
- 到达等级按末尾裁定列出的P0b/P1/P2/P3/P2s判定；P0a与研究用P0g只报告，P0b魔法使い也只报告。P2s使用与P2到达等级众数及均值差≤1，不强行要求其众数等于6。
- M9含盾、多段伤害的既有期望近似仍存在；新增精英百分比共享上限采用联合分布结算。盾统计的联合吸收上界限制见上文。
- 测试放.tmp-test/052b/tests，由tests.patch映射回tests；旧F6数值夹具明确排除052b机制，旧章节迁移检查末尾补052迁移，旧占位符测试只允许审定052b文本，分类测试同步更新敌人实例分类。没有削弱金标或改标准答案。
- 本段未新增依赖；全程离线、无付费API。默认prompt、benchmark标准答案、baby冻结表、v1被动表、strategy_v3未改。baby有效运行内容比较会剔除未生效difficulty_overlays元数据；其余内容仅content_revision变化，不把整个原始JSON声称为不变。

原始结果：`.tmp-test/052b/candidate-normal{,-records,-checkpoints}.json`、`candidate-audit.json`、`gate-acceptance.json`、`branch-report.json`、`sword-routes-500.json`、`response-probe.json`、`validation.json`。

运行时长（秒）：normal {"workers":8,"branch_proposals":1462.9304083000025,"routes":1531.4485666999972,"preparation_probes":103.08503999999812,"companion_probes":553.5923610999998,"level_probes":169.65377429999717,"boss_policy_probes":128.28002840000045}；总计 3963.5074019999993。各候选分片含输入指纹；运行中断可用同一命令恢复，指纹不符拒绝复用。

确定性抽查：{"n_per_combination":2000,"seed":20261021,"combinations":["G1","G2"],"workers":[1,8],"equal":true,"sha256":"35a51e5aea370d4e6391d6647e72812cf22f3ed8ddc2ae5fdc4cad9af02f2b32"}

baby 053复现：{"comparison":"Canonical UTF-8 bytes of numeric payload; raw timing, fingerprints and target metadata reported separately","measurement_checks":{"rows":true,"ignis_levels":true,"metrics":true,"cell_metrics":true,"usage":true,"checkpoint_probes":true,"p2s_comparison":true,"m3b":true},"record_checks":{"records":true,"difficulty":true,"passive_defaults":true,"damage_budget_v2":true,"preparation_probes":true,"companion_probes":true,"level_probes":true,"boss_policy_probes":true},"raw_measurement_equal":false,"differing_top_level_keys":["effective_pack_fingerprint","overlay_fingerprint","code_fingerprint","targets","fingerprints","timings","elapsed_seconds"],"n":500,"seed":20261020,"records":14000,"record_sha256":"c29e1c28e92ac6be9ad648523f959309d10f3521390f00194676d92e5c17c843","checkpoint_probes":{"human_berserker":{"n":500,"win_rate":0.956,"rounds_median":19.0,"expected_incoming":4.813809523809524,"expected_healing":6.0,"sustain_coverage":1.246414086457612,"sample":{"encounter":"dragon_valley_loc","encounter_class":"boss","status":"victory","rounds":20,"policy":"best_free","before":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":310.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"after_combat":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":310.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"actions":{"item:ice_charm":20},"action_specs":{"item:ice_charm":{"type":"item","id":"ice_charm","free":true,"kind":"damage"}},"consumables":{},"opening":{"expected_damage":4.813809523809524,"variance":35.82390453514739,"cv":1.243361906806332,"ratio":0.12034523809523809,"notes":[]},"expected_healing":6.0,"expected_hp_loss":91.46238095238095,"enemy_phases":19,"companion":"fire_bat_dragon","p0_choice":"item:ice_charm","statuses":[],"skill_usage":{},"after_resolution":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2,"紅竜の炎核":1},"max_hp":40,"gold":701,"healing_hp":310.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"continue":true}},"P0b + 氷鉄の大剣":{"n":500,"win_rate":0.988,"rounds_median":10.0,"expected_incoming":4.813809523809524,"expected_healing":6.0,"sustain_coverage":1.246414086457612,"sample":{"encounter":"dragon_valley_loc","encounter_class":"boss","status":"victory","rounds":12,"policy":"best_free","before":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":310.0,"equipment":["紅玉の護符","革の鎧","氷鉄の大剣"]},"after_combat":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":310.0,"equipment":["紅玉の護符","革の鎧","氷鉄の大剣"]},"actions":{"attack:basic_attack":12},"action_specs":{"attack:basic_attack":{"type":"attack","id":"basic_attack","free":true,"kind":"attack"}},"consumables":{},"opening":{"expected_damage":4.813809523809524,"variance":35.82390453514739,"cv":1.243361906806332,"ratio":0.12034523809523809,"notes":[]},"expected_healing":6.0,"expected_hp_loss":52.951904761904764,"enemy_phases":11,"companion":"fire_bat_dragon","p0_choice":"attack:basic_attack","statuses":[],"skill_usage":{},"after_resolution":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2,"紅竜の炎核":1},"max_hp":40,"gold":701,"healing_hp":310.0,"equipment":["紅玉の護符","革の鎧","氷鉄の大剣"]},"continue":true}},"无同伴":{"n":500,"win_rate":0.634,"rounds_median":20.0,"expected_incoming":4.813809523809524,"expected_healing":0.0,"sustain_coverage":0.0,"sample":{"encounter":"dragon_valley_loc","encounter_class":"boss","status":"victory","rounds":21,"policy":"best_free","before":{"hp":40,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":8,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":310.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"after_combat":{"hp":27,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":6,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2},"max_hp":40,"gold":601,"healing_hp":250.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"actions":{"item:ice_charm":19,"item:healing_scroll":2},"action_specs":{"item:ice_charm":{"type":"item","id":"ice_charm","free":true,"kind":"damage"},"item:healing_scroll":{"type":"item","id":"healing_scroll","free":false,"kind":"heal"}},"consumables":{"治療の巻物":2},"opening":{"expected_damage":4.813809523809524,"variance":35.82390453514739,"cv":1.243361906806332,"ratio":0.12034523809523809,"notes":[]},"expected_healing":0.0,"expected_hp_loss":96.27619047619048,"enemy_phases":20,"companion":null,"p0_choice":"item:ice_charm","statuses":[],"skill_usage":{},"after_resolution":{"hp":27,"mp":12,"sp":18,"level":5,"inventory":{"鉄の剣":1,"革の鎧":1,"薬草":7,"携帯食":2,"氷の護符":1,"治療の巻物":6,"スライムの核":5,"ゴブリンの飾り物":5,"生命の果実":3,"刻印のハンマー":1,"剛力の霊薬":1,"錆びた王冠":1,"鉄壁の霊薬":1,"光苔":1,"残り火の欠片":6,"焼けた溶岩石":1,"火球術の巻物":1,"紅玉の護符":1,"虹晶の欠片":1,"叡智の霊薬":1,"色水晶の欠片":2,"精霊の泉の水":1,"獣の毛皮":1,"氷の結晶":1,"魔力の果実":2,"霜の欠片":3,"白い竜鱗":1,"迅速の霊薬":1,"氷鉄の大剣":1,"煤の精":2,"紅竜の炎核":1},"max_hp":40,"gold":701,"healing_hp":250.0,"equipment":["鉄の剣","紅玉の護符","革の鎧"]},"continue":true}}}}

通玩baby对HEAD：{"summary":true,"runs":true,"max_steps":true,"workers":true,"fingerprints":false}

两份金标、冻结包、迁移链与叠加全测试/原地命令结果详见 `052b-report.txt` 与日志。原始报表的代码指纹、耗时及元数据必然改变，逐字节不变指规范化数值负载，不把整份原始JSON称为字节相同。
