难度 D3 · 执行方 Codex gpt-6.1-sol max · 理由：只动模拟与测量工具、不碰游戏代码和剧本；但横跨 route / sim / probes / metrics 多个模块，baby 要逐字节复现、回归量大；046 / 050 已留好接口，不赶时间
# 053 模拟器 v3：新泉流程、难度感知、EXP / 被动 / 新主动 / 卷轴 / 闪避与状态，以及 normal 的调参前基线

来源：
- 046（测量 v2：原型 P0a/P0b/P1/P2/P3/P2s/P0g、M1–M13、targets v2、checkpoint、试玩遥测）及 046b 汇报与基线 `eval/reports/046-measurement-v2-baseline.{json,md}`。
- 048（精霊の泉只能休息一次）、050（normal 的 EXP 等级、固定主动、被动二选一、卷轴）、051（dex 闪避、冷却、状态、护符限制、火コウモリ竜 回复挂钩），各自的「设计负责人决定」。
- `docs/design/balance-v2-decision-metrics.md`（指标定义与目标，r6）、`docs/design/skills-v2.md`（末尾「用户决定」）。
- `eval/reports/048-engineering.md` 第 6、7 节；`.tmp-test/050/050-report.txt` 第 9、13 节。

**本任务只做测量，不调任何数值。**产出是 052（数值调参）的输入：normal 下"职业 × 原型"的 M1–M13 表，以及实测的到达 Ignis 时的等级。编号上 053 在 052 之后，但执行顺序是 053 先做。

## 0. 前提与文件边界
- **前提**：047、048、050、051 已提交（HEAD ≥ `9398493`）。不满足就停下汇报。
- **可以改**：`scripts/balance/`、`eval/balance/`（只新增文件，或在 `targets.json` 里新增键）、`eval/reports/053-*`、测试（以补丁形式交付，见第 9 节）。
- **不得改**：`host/`、两份剧本包与 `difficulty/`（含 `baby_numeric_freeze.json`）、`scripts/scenario/`、`scripts/playtest/`（只运行）、`client/`、`docs/`、`eval/benchmark/`、提示词。
- **冻结的历史产物不能被覆盖**：`eval/reports/046-*`、`eval/balance/checkpoints.json`、`eval/balance/046-legacy-output.json`、`eval/balance/checkpoints_berserker.json`。现在 `measurement_v2.main` 每次运行都会重写 `checkpoints_berserker.json`：改成内容相同就不写，不同就报错。
- 引擎侧有缺口（例如缺纯函数入口）时，列进汇报，不要改 `host/`。

## 1. 现状（动手前核对，不一致写进汇报）
| 项 | 现状 |
|---|---|
| 泉的拓扑 | `rest_at_elf_spring` 带 `once`/`hidden_after: rested_at_elf_spring`，已击败史莱姆王后隐藏；休息 → 回满 → `slime_ambush_one` → `two` → `slime_king_battle`，胜利后直接到 `forest_wolves`。`wolves_back` 还能回到泉，但泉不能再休息 |
| 模拟器的假设 | `route.py`、`class_aware.Run.rest_point` 打完连战后用 `while location != 原地: fight(...)` 等待回到泉 → 在新流程下卡死（"回原地等待"）。`route_v2.MeasurementRun.rest_point` 不卡，但之后的 `continue_from_elf_spring` 在 `forest_wolves` 不可用，P2/P3 的洞窟顺序也是按"休息后仍在泉"写的 |
| 测试 | `tests/spring_legacy_balance.py` 把旧拓扑钉住，`test_balance.py`、`test_class_aware_route.py`、`test_measurement_v2.py`、`test_measurement_v2b.py` 都在用，因此现在的测量描述的是旧流程 |
| 难度 | `checkpoints.fresh_session` 不写 `difficulty`，模拟器全部是 baby。normal 要先 `apply_difficulty(pack, "normal")`、写 `session["difficulty"] = "normal"`，再 `progression.initialize(session)`（050 汇报第 13 节） |
| normal 覆盖层 | `evade_model: dex`、`enemy_accuracy_override: 100`、`divine_guard.cooldown 1`、`ice_charm.requires_target_weakness`、火コウモリ竜 `scale_from_damage` 0.75 / 1.5、`progression`（EXP 表、Lv8）、火球 / 氷の矢 的 `conditional_bonus`；`class_progression`、两种卷轴（`magic_shop`，库存 1，60G / 45G）只在 normal 有效包里存在 |
| 策略 | `sim.expected_damage` / `free_action_damage` 和 `budget.phase_moments` 用的是固定 `combat.evade` 和能力自带的命中，不调用引擎的 `combat.attack_chance` / `actor_evade`；不认识 `costs`、`free_action`、`max_uses_per_battle`、条件倍率、施加状态的价值；`PassivePicker` 只是空壳；不买卷轴 |
| 战斗摘要 | `statuses: []`、`skill_usage: {}` 是占位；M12 一律 `not_applicable` |
| 等级 | 050 只有静态估算：P0 Lv4、P1 Lv4、P2 Lv7、P3 Lv8（目标 4 / 5 / 6 / 7）；假定所有列出的战斗都胜利、不走史莱姆链、任务全部成功。normal 离线通玩四职业全部败北 |
| 046b 运行成本 | N=500、workers=12，主批次墙钟 1287 秒 |

## 2. 新泉流程与 legacy fixture
- 所有路线器（`route.py`、`class_aware.py`、`route_v2.py`）改成"**有待结算的战斗就打，没有就停**"，不再等待回到原地。在旧拓扑下，这个改动必须让旧输出逐字节不变（打完史莱姆王本来就回到泉）。
- 新增原型参数 `spring_rest`（取值见下表，写在数据表里，加取值不用改跑法）。泉休息最多一次；休息之后位于 `forest_wolves`，路线宏从那里继续，需要回洞窟的走 `wolves_back`。
  | 取值 | 含义 | 暂定给谁 |
  |---|---|---|
  | `first_hp70` | 第一次到泉时 HP < 70% 才休息（046b 的 HP70 规则加上"仅一次"） | P0a、P0b、P1、P0g |
  | `last_visit_once` | 最后一次离开泉之前休息一次，不看 HP（主动打史莱姆链） | P2、P3、P2s |
  | `never` | 不休息 | 探针用 |
  暂定分配见待确认 Q2。其他休息点（宿屋、避難所、温泉等）沿用 046b 的规则，不变。
- `legacy_spring_balance_pack` 从 `tests/` 移到 `scripts/balance/legacy_spring.py`（tests 里的文件改成转引用），只用来做**冻结的历史对照**；CLI 用 `--spring legacy|current` 选择，默认 `current`。实际游戏和所有新增测量一律用 `current`。
- 测试分两类，汇报里逐个测试列出归类：

| 文件 | 保留 legacy（历史对照，断言不变） | 切到新流程 |
|---|---|---|
| `test_balance.py` | `test_checkpoints_regenerate_and_classifications_match`（`checkpoints.json` 冻结为旧流程产物） | 其余测试不依赖泉，保持原样 |
| `test_class_aware_route.py` | 全部（027 的历史工具） | 新增 1 条：新流程下 `hp70` / `class_aware` 的休息在有限步内结束，不会卡死 |
| `test_measurement_v2.py` | `test_legacy_outputs_match_pre_edit_bytes`、`test_legacy_all_policy_selection_is_unchanged`、`test_document_checkpoint_and_separate_probes`、`test_instrumentation_preserves_outcomes_and_rng` | 原型参数、`LevelModel` / `PassivePicker` 合约、串行与并行一致性（按新参数更新断言） |
| `test_measurement_v2b.py` | `test_hp70_strict_free_rest_is_not_limited_to_three`（改名标明 legacy） | 新增对应测试：新流程下泉休息 ≤ 1 次、以 `forest_wolves` 结束、之后路线继续；其余集成测试改用 `current` |

## 3. 难度感知
- 所有入口（`measurement_v2`、`route_v2.run_jobs`、`probes_v2`、`reproduction_v2`、`sim`）加 `--difficulty baby|normal`，默认 `baby`。会话构造集中到一个函数（照第 1 节的 normal 构造顺序），job 元组带上难度，子进程里重新构造。
- **baby 的代码路径逐字节不变**：凡是改成调用引擎新口径的地方（命中 / 闪避、费用、冷却、状态），在 baby 下结果必须和旧公式一致；做不到一致就只在 normal 下走新口径，并在汇报里写明。
- 输出分开存放：`eval/reports/053-measurement-v3-{baby-legacy,baby,normal}.{json,md}`，JSON 记录难度、泉流程、有效包指纹、`overlay_fingerprint`、代码指纹、seed。
- 门槛（`--check`）只按 normal 判定；baby 的指标照算，状态统一为 `report`（见待确认 Q7）。

## 4. 策略：EXP、被动、新主动、冷却、状态、卷轴、闪避
### 4.1 EXP 与等级
- EXP 只从引擎来：战斗胜利的 `consume_combat_state_delta` + `state.apply_state_delta`、任务完成（`route_v2.fight` 现在就走这条路，核对 normal 下确实发了 EXP）。模拟器不自己加 EXP、不手工升级。
- `LevelModel` 换成观察 EXP 的实现：在每个 `MAINLINE_NODES` 和每个 Boss 开战时记录 `level`、`exp`、本节点之前的 EXP 来源分解（trash / elite / boss / unclassified / quest）。
- **到达 Ignis 时的等级**：在 `dragon_valley_loc` 开战前记录（不含 Ignis 的 EXP）。按"原型 × 职业"报告到达率、等级的均值 / 中位数 / 最小 / 最大和直方图；并和 050 的静态估算、设计目标（P0 4、P1 5、P2 6、P3 7）放在同一张表里，逐项解释差异。
- `targets.json` 新增 `ignis_level`（按设计文档 5.2 原样抄：P0 4、P1 5、P2 6、P3 7，`status: "draft"`），以及 M13 的"P0 与 P2 等级差 ≥ 2"。不改任何已有键。
- P0g：048 审计确认剧本里没有能重复的战斗。normal 下 P0g 照样跑，结果应当与 P0b 相同；"每升 1 级的资源消耗"用 P0b 路线上每升一级前后的 `resource_score` 差来估（见待确认 Q10）。

### 4.2 被动选择
- 每次战斗结算后、非战斗状态下，有 `pending_passive_choices` 就立刻选：调用 `host.progression.choose_passive(session, min(pending), passive_id)`（返回深拷贝，要接住），候选取自 `public_progression(session)["pending"][0]["options"]`。
- `PassivePicker` 三种模式：
  | 模式 | 用途 | 规则 |
  |---|---|---|
  | `first` | P0a、P0b、P1（046 规则） | 每级取数据里的选项 A |
  | `table` | P2、P3、P2s | 按 `eval/balance/passive_defaults.json`（职业 × 等级 → 选项，`status: "proposed"`）。表由工程用穷举试跑提出：在前面各级已按表选定的前提下，取 P2 路线 Ignis 胜率更高的那个；平局取 A。每一格写明依据数字 |
  | `enumerate` | M12 | 每职业 2⁴ = 16 种组合各跑一遍 P2 路线；同一 trial index 在 16 种组合间共用起始种子（共同随机数） |
- 原型参数里的 `passive_mode: battle_best` 改为 `table`（被动是永久选择，不存在"按这场战斗选"）。
- 遭遇级比较（M12 的"死选项"）：从 P2 的实测开战快照出发，对每个精英 / Boss 遭遇、每个被动等级，把这一级的 A / B 互换（其余各级按表），各跑 `--probe-n` 场。一个选项若在整个遭遇矩阵里都不比另一个好，记为死选项。可叠加被动按"之前选过 / 没选过"分开统计（skills-v2 第 0.4 节）。

### 4.3 战斗策略
- 新增策略 `heuristic_v3`，normal 下 P1 及以上使用；`attack_only`、`greedy`、`heuristic`、`best_free` 在 baby 下的输出不变。P0 在 normal 下仍用 `best_free`（定义不变：零消耗行动里期望伤害最高的那个，HP < 30% 时回复），但命中和闪避改用引擎口径。
- `heuristic_v3` 至少要满足下表。阈值都写成数据（策略参数表），在汇报里列出；这些是"模拟玩家怎么打"的工程参数，不是游戏数值。
  | 机制 | 要求 |
  |---|---|
  | 合法性 | 只从 `combat_actions` 里 `enabled` 的行动选；按目标调用 `_ability_disabled_reason` 的同等判断（`requires_target_weakness` 按目标、冷却、`max_uses_per_battle`、双资源 `costs`、`no_reapply`）。选到被服务端拒绝的行动 = 测试失败 |
  | 命中 / 闪避 | 期望伤害用 `combat.attack_chance` / `actor_evade`（dex 公式、`enemy_accuracy_override`、致盲之类的命中惩罚、被动闪避加成） |
  | 伤害 | 计入 `conditional_bonus` / `conditional_multipliers`（施放时判定）、`ignores_resistance`（取 `max(1.0, 原倍率)`）、`ignores_defense`、`multi_elements`（含 元素崩壊 的动态段）、技能与被动的追击 |
  | 状态 | 施加 DoT / 标记（毒叠层、火傷、聖印、目潰し）按"剩余回合 × 每回合期望 × 目标预计存活回合的上限"估值；减益按减少的期望受伤估值；身上有可清除的减益且累计期望伤害超过阈值时考虑 `cleanse` |
  | 防御 / 增益 | 神聖の庇護（cd 1）、聖光の剣技 的减伤、魔力凝縮（`mana_veil`）、影隠れ、神速、福音：在预计受伤高的回合（Boss 战、敌方蓄力）优先；冷却中不选 |
  | 回复 | 沿用 35% 阈值；不滅の聖域 下 治癒の祈り 消耗为 0 的情况要识别 |
  | `free_action` | 每回合同一行动最多一次；必须证明不会死循环（测试） |
  | 资源 | 大招（竜断ち、元素崩壊、神速、福音）留给 Boss / 精英；MP / SP 不够时不选 |
- 状态的发生与结算从引擎读，模拟器不自己算。战斗摘要填上 `statuses`（按一方 × 状态 ID：施加次数、结算伤害、清除次数）和 `skill_usage`（按技能：次数、命中、伤害、消耗、因冷却 / 次数被灰显的回合数）。

### 4.4 卷轴
- 只有魔法使い 买。暂定：P1 及以上，在路线本来就经过王都的时候，如果金币够就进 `magic_shop` 买，顺序 雷撃（60G）→ 魔力の槍（45G），买完立刻 `progression.learn_spell`；P0a、P0b 不买（P0b 的 3 次交互预算已经用完）。见待确认 Q4。
- 进店、买、学都通过引擎（`trade`、`learn_spell`），会被拒绝的情况（非魔法使い、已学会、库存 0）测试覆盖。记录买到的时间点（所在节点、等级）和之后的使用次数。
- P3 魔法使い 如果走了接受诅咒的分支（`clear_skills`），已学法术会被清空（050 决定 Q11），卷轴库存 1 买不回来：照实模拟，在汇报里单列。

## 5. 指标在 normal 下的口径
| 指标 | normal 下的变化 |
|---|---|
| M1、M1' | 不变；按 normal 判定门槛 |
| M2、M8、M13 的探针 | checkpoint 改为从 P2 的实测开战快照生成（取到达该 Boss 时的中位等级样本，被动按 `table`，装备与库存按 P2 规则），存为 `eval/balance/checkpoints_normal_053.json`，记来源和指纹；`checkpoints.json` 不动（见待确认 Q8、Q9）。M13 的 ±1 级用引擎的升级路径（`level_gains`、Lv3/5/7 主动、偶数级按表选被动） |
| M3 | 可持续回复 = 火コウモリ竜（期望火伤 × 比例，对火抗目标为 0）+ 被动再生（敬虔なる心，决定 18）。另报 M3b：再加上零消耗、可重复的技能治疗按实际使用率折算（不滅の聖域）。见待确认 Q5 |
| M9、M10 | 用引擎命中口径（敌方命中 100 − 玩家闪避）；状态伤害不计入每回合直接伤害，单列 |
| M11 | 在实际轨迹上计入状态结算伤害 |
| M12 | 从 `not_applicable` 改为实算：P2 的 Boss 战技能回合占比、单个主动占全部技能的比例、死选项（第 4.2 节）、同组价值差（暂定 = 两个选项的 P2 路线 Ignis 胜率差，见待确认 Q6）。baby 仍为 `not_applicable` |
| M4–M7 | 不变 |

## 6. 输出给 052 的表
`053-measurement-v3-normal.md` 至少包含（数字全部来自本次运行，**调参前**）：
1. 原型 × 职业：通关率、Ignis 胜率、终局率、Ignis 回合中位数、到达 Ignis 的等级（中位数 / 分布）、EXP 来源分解、和目标的差距。
2. 原型 × 职业 × M1–M13：值、目标、状态（`pass` / `fail` / `report` / `not_applicable`），不能算的写原因。
3. 被动：`passive_defaults.json` 的每一格及依据；16 组合的 P2 结果；死选项清单；同组价值差。
4. 技能使用（M12、M6）、状态统计、卷轴购买时间点与使用次数。
5. 与 baby（当前流程）的对照列，以及 normal 下仍然不能表达的机制清单。

## 7. 不做什么
- 不调任何数值：剧本、覆盖层、`targets.json` 已有的值、经济、敌人都不动；不为了"让 normal 能通关"改路线或策略参数。
- 不新增原型；原型的支线集合只按第 4 节改参数（泉休息、卷轴、被动模式）。
- 不做 G2 百分比招式、陷阱 / 落石（剧本里还没有 `hazard`，遇到也不处理，列进汇报）。
- 不改 `host/`，不调用 LLM，不联网。

## 8. 验收
### 8.1 baby 复现
| 项 | 命令 / 配置 | 要求 |
|---|---|---|
| 试玩配置 | `human_berserker`，baby，N=500，seed 20261020 | 胜率 95.6%、回合中位数 19、S = 1.2464。预期逐项相等；容差：胜率 ±1.0pp（473–483 / 500 胜）、中位数 ±1 回合、S ±0.005。任何非零差异都要定位到具体改动并写进汇报 |
| 另两个探针 | `P0b + 氷鉄の大剣`、`无同伴` | 98.8% / 10 / 1.2464、63.4% / 20 / 0；容差同上 |
| 旧流程原型表 | `--difficulty baby --spring legacy`，N=500，seed 20261020 | 28 格的通关率、Ignis 胜率与 046b 基线相比每格 ≤ 2pp；超出的格逐项归因到 047–050 的内容改动（附证据），无法归因 = 不通过 |
| 旧工具字节一致 | `sim --check`、`route hp70`、`class_aware backbone`（legacy） | 与 `046-legacy-output.json` 逐字节一致 |
| 当前流程 baby | `--difficulty baby --spring current` | 新的 baby 基线；每格相对 046b 的差异列表，说明是泉流程造成的 |

### 8.2 确定性
- 同一 seed、同一输入跑两遍：输出 JSON 除计时字段外逐字节一致（baby 和 normal 都要测）。
- `--workers 1` 与 `--workers N` 逐字节一致。
- 被动穷举、A / B 互换使用共同随机数；种子规则写进 JSON。

### 8.3 运行成本
| 运行 | 预算 |
|---|---|
| 新增单元测试合计 | ≤ 90 秒 |
| 冒烟：`measurement_v2 --difficulty normal --n 2 --probe-n 2 --workers 1` | ≤ 5 分钟 |
| 全量 baby（legacy 或 current 任一），N=500，workers=12 | ≤ 25 分钟 |
| 全量 normal，N=500、probe-n 500（被动穷举每组合 N=200），workers=12 | ≤ 60 分钟 |
- 汇报里给出各阶段的墙钟。沙箱不允许多进程时，如实写明，交付 N=100 的串行结果和全量命令，由设计侧重跑。

### 8.4 测试（新增）
- 新泉流程：三种 `spring_rest` 取值；休息 ≤ 1 次；路线不卡死；`wolves_back` 回洞窟。
- 难度：baby / normal 会话构造；normal 有效包里有卷轴、`class_progression`；子进程里难度不丢。
- EXP / 等级：各节点等级记录与引擎一致；EXP 来源分解相加等于总量。
- 被动：三种模式；`choose_passive` 只在非战斗时调用；16 组合枚举；共同随机数。
- 策略：`heuristic_v3` 不会选服务端拒绝的行动（冷却、护符非冰弱点目标、次数、双资源）；`free_action` 不循环；命中口径与 `combat.attack_chance` 一致；状态与技能使用统计。
- 卷轴：魔法使い 买到并学会；非魔法使い 不买；库存 1；金币不够不买。
- baby 不变：上面 8.1 的旧工具字节一致测试继续通过。
- 两条验证命令都要通过：
  ```
  python -m unittest discover -s tests -q
  node --check client/app.js
  ```
- 全程离线：不调用任何付费 API，不加 `--live`。

## 9. 交付（沙箱）
- 与 050 相同：Codex 沙箱不能写 `.git`，也不能在 `tests/` 下新建文件。测试和夹具写在 `.tmp-test/053/tests/`，用 050 同样的叠加执行器运行，并如实写明原地命令的结果。
- 交付到 `.tmp-test/053/`：`053.patch`（相对 HEAD 的完整补丁）、`tests.patch`（只含测试与夹具）、`manifest.json`（`base_commit`、`files`、`patch_sha256`、`commit_message`，`[工程]` 前缀）、`053-report.txt`。
- 在仓库内独立临时目录从 HEAD 实际应用补丁并逐文件核对；文件 UTF-8 无 BOM。**不要提交，不要 `git add`。**

## 10. 汇报
1. 8.1 的复现表（三个探针、28 格对照、字节一致结果），以及每个非零差异的归因。
2. 当前流程 baby 与 046b 的差异表。
3. 第 6 节的 normal 表（全部）。
4. 到达 Ignis 等级：实测 vs 050 静态估算 vs 目标，并解释差在哪里（史莱姆链、判定失败、任务没做成、绕战）。
5. `passive_defaults.json` 全表与依据；`heuristic_v3` 的策略参数表；卷轴购买规则的实际效果。
6. 第 2 节的测试归类清单（每个测试一行）。
7. 各阶段运行时长；串行 / 并行、两次重跑的一致性结果。
8. 引擎侧缺口（需要 `host/` 提供但本任务不能改的东西）；策略没模拟到的机制及其对结果的可能影响。
9. 推断清单、偏离 spec 的地方。

---

## 待设计负责人确认
- **Q1 被动默认选择**：P0a / P0b / P1 取选项 A（沿用 046）；P2 / P3 / P2s 用工程穷举提出的固定表（`proposed`，设计审定后才作为门槛依据）。P0 是不是也会选被动？暂定会选（弹窗自动出现，选 A），而不是"关掉不选"（050 Q9 允许关掉）。
- **Q2 泉休息时机**：暂定 P0a / P0b / P1 / P0g 用 `first_hp70`，P2 / P3 / P2s 用 `last_visit_once`（主动打史莱姆链，拿 EXP 和 鉄壁の霊薬）。史莱姆链约 50 EXP，会直接影响到达 Ignis 的等级，所以这条要先定。
- **Q3 P3 的范围**：是否做全部可选任务（050 的 Lv8 估算假定 9 个任务全部成功）；互斥分支怎么选（现在是"火种接受后净化、商人背叛"）；判定失败要不要重试；"每店每种商品买 1 件"是否保留。
- **Q4 卷轴**：哪些原型会买（暂定 P1 起，P0b 不买）；顺序（暂定 雷撃 → 魔力の槍）；和其他准备品冲突时谁优先。
- **Q5 M3 的口径**：主口径 = 同伴 + 被动再生（敬虔なる心）；零消耗可重复的技能治疗（不滅の聖域）只进 M3b 报告——还是也算进主口径？福音 算不算？
- **Q6 M12 的"整体价值"和"更优"**：暂定整体价值 = P2 路线 Ignis 胜率，"同组差 ≤ 10%"按绝对 pp 计；遭遇级"更优"按点估计还是要求统计上显著？
- **Q7 门槛范围**：硬门槛（M1、M3、M4、M9）只对 normal 判定，baby 一律只报告——确认。
- **Q8 normal 的 checkpoint**：用 P2 实测开战快照（中位等级）替代固定等级，供 M2 / M8 / M13 使用。是否还需要 P0b 版本（normal 下的"莽夫配置"按什么等级、什么库存）？
- **Q9 旧 `checkpoints.json`**：冻结为旧流程的历史产物（只在 legacy 下再生成）、新流程另出文件——确认。
- **Q10 P0g**：剧本没有可重复战斗，normal 下 P0g 与 P0b 相同；"每升 1 级的资源消耗"用 P0b 路线估算——接受，还是等以后有可重复战斗再测？

## 设计负责人决定（2026-10-21）

| # | 决定 |
|---|---|
| Q1 | P0/P1 取 A（不跳过选择）；P2/P3/P2s 用工程穷举提出的表，作为 proposed 记入汇报，052 前由设计审定。 |
| Q2 | 按暂定：P0a/P0b/P1/P0g 用 `first_hp70`，P2/P3/P2s 用 `last_visit_once`。 |
| Q3 | P3 做全部可选任务。互斥分支按"对本职业 Ignis 胜率更有利"的一侧走，汇报列出选择。判定失败不重试，除非引擎本身允许重复尝试（沿用 046 规则）。"每店每种买 1 件"保留。 |
| Q4 | 卷轴从 P1 起购买，P0b 不买；先雷撃后魔力の槍。冲突时先买原型原有的准备品清单，余钱再买卷轴。诅咒清空法术照实模拟，单列。 |
| Q5 | M3 主口径 = 同伴 + 敬虔なる心。不滅の聖域（占用行动）和 福音（每战一次）只进 M3b。 |
| Q6 | 整体价值 = P2 路线 Ignis 胜率，同组差按绝对 pp。遭遇级"更优"要求 95% 置信区间不含 0；点估计也报告。 |
| Q7 | 确认：硬门槛只对 normal 判定，baby 只报告。 |
| Q8 | 需要。normal 另出 P0b（莽夫）开战快照，与 P2 中位快照并列。 |
| Q9 | 确认：旧 `checkpoints.json` 冻结，新流程另出文件。 |
| Q10 | 接受。 |
