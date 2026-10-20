难度 D4 · 执行方 Codex gpt-6-astra high · 理由：跨引擎、两份剧本包、客户端、难度通道、会话字段和旧存档迁移的多系统改动；baby 必须逐回合不变，改错会坏玩家存档
# 050 等级与技能 v2：EXP 升级、固定主动、被动二选一、魔法使い卷轴

来源：
- `docs/design/skills-v2.md`（正式设计稿 r1）。**末尾「用户决定（2026-10-20）」覆盖正文**，冲突时以它为准。
- `docs/design/skills-v2-user-draft.md`（用户原稿，权威意图）。
- `docs/design/balance-v2-decision-metrics.md` 第 5.2–5.5 节（满级 8、EXP 战斗驱动、升级回满、Lv3/5/7 固定主动、Lv2/4/6/8 被动二选一、规则不替玩家选）。
- 047（难度覆盖层与机制开关通道）、051（冷却、状态系统、`status_defs`）及两者的「设计负责人决定」。

**本任务做机制和数据录入，不做调参。**所有数值是暂定参数（第 8 节），由 052 按模拟调。

## 0. 前提、文件边界与对 baby 的处理
- **前提**：047、051 已提交；**048（精霊の泉只能休息一次，B4）已提交**——5.2 规定零成本刷级的循环必须先堵上，EXP 才能上线。048 未提交就停下汇报（两条线都改剧本包，不能并行）。
- **可以改**：`host/`（`combat.py`、`state.py`、`status_effects.py`、`difficulty.py`、`item_mechanics.py`、`shops.py`、`scenario_context.py`、`app.py`、`free_actions.py` 的代码部分；可新增 `host/progression.py`）、`client/`（`app.js`、`index.html`、`styles.css`）、两份剧本包（**始终同步**）、`scenario_pack.schema.json`、`host/prompt/processed/difficulty/overlay_revision.json`、新增迁移脚本 `scripts/scenario/levels_skills_v2.py`（**必须幂等**）、测试（以补丁形式交付，见第 11 节）。
- **不得改**：`host/prompt/processed/difficulty/baby_numeric_freeze.json`、`scripts/balance/`、`scripts/playtest/`（只运行）、`eval/benchmark/`、`docs/`、提示词措辞（`gm_contract.py`、`free_actions.py` 的默认 prompt 字符串）。
- **对 baby（按本次派发的要求，原则同 051 的实际做法）**：
  - baby 的等级行为**逐项不变**：仍由 4 个里程碑 flag 触发 Lv2–5，`milestones.gains`、`level_skills`（渾身斬り・改 等）照旧；不出现 EXP、被动、卷轴、新技能；baby 会话**不写入任何新键**。
  - 新机制只由 normal 覆盖层里的开关启用（047 的 `MECHANIC_FIELDS` 通道）；新定义放基础包，但在 baby 有效包里**不存在**（第 2.2 节）。
  - 每项机制在汇报里写明"对 baby 的影响"（应为：无）。

## 1. 现状（动手前核对，不一致写进汇报）
| 项 | 现状 |
|---|---|
| 等级 | `milestones` 4 条（Lv2 `passed_forest_wolves`、Lv3 `cleared_goblin_fort`、Lv4 `reached_village`、Lv5 `nest_event_seen`），`state._apply_milestones` 按 flag 升级，每级加固定 `gains`，并回满 HP/MP/SP；满级 5。没有 EXP |
| 等级技能 | `characters[].level_skills` 按 `unlock_level` 解锁（`_unlock_level_skills`），多数带 `replaces`；魔法使い 的 `火球・改` 实际 `unlock_level: 2` |
| 技能清空 | `alley_night.pay_curse_price_mage` 的 `clear_skills` 清空技能并记 `skills_cleared_through_level` |
| 火球 / 氷の矢 | `effect` 文本写了"HP 100% 追加 1d6""HP ≤50% 追加 1d6"，引擎没有对应字段（未实装） |
| 051 已有 | 技能冷却 `cooldown`；`self_status`；`on_hit_status`（`chance`/`target`/`stacks`）；`cleanse`；`status_defs` 中的 `holy_mark`、`blind`、`haste`、`holy_afterglow`、`arcane_shield`、`gospel`（施加时回复增加量）、`holy_blessing`、`magic_focus`、`poison`（默认上限 3，可覆盖为 5）；`received_damage_multiplier`（与防御相乘，下限 ×0.25）；护盾 `absorb`；`after_damage`；`on_damage_followup`；`extra_actions_per_round` |
| 缺 | 双资源消耗、条件倍率、无视抗性、玩家技能的每场次数、技能型 `restore`、不消耗行动、被动框架、动态 `multi_elements`、卷轴学习、按难度隐藏实体 |
| 客户端 | 没有任何等级 / EXP 显示 |
| 遭遇分类 | 67 个地点战斗中 `encounter_class`：trash 9、elite 16、boss 11、scripted_loss 1、guest 1、**未填 29** |

## 2. 数据与难度通道
### 2.1 normal 覆盖层（本任务只写这些条目，baby 一律不动）
| 实体 / 路径 | 值 | 说明 |
|---|---|---|
| `progression` / `level_model` | `"exp"` | 开关；缺省（baby）= `"milestone"` |
| `progression` / `max_level` | 8 | |
| `progression` / `exp_table` | 第 8 节 `EXP_TABLE` | 累计 EXP，按等级键（`"2"`…`"8"`），不用数组下标 |
| `progression` / `exp_rewards` | 第 8 节 `EXP_*` | 按 `encounter_class` 和来源 |
| `progression` / `level_gains` | 第 8 节 `LEVEL_GAINS` | 每职业每级成长 |
| `characters` / `mage` / `skills.@id=fireball.conditional_bonus`、`…ice_arrow.conditional_bonus` | 第 5.1 节 | 补回未实装效果 |
| `characters` / `mage` / `skills.@id=fireball.spell_tier`、`…ice_arrow.spell_tier` | `"basic"` | 元素崩壊 计数用 |

- 以上路径加进 `MECHANIC_FIELDS`，各配校验器（整对象 `set`，同 051 的 `evade_formula` 写法）：`exp_table` 必须严格递增且覆盖 2…`max_level`；`exp_rewards` 的值为非负整数；`level_gains` 必须覆盖四职业。
- 基础包新增空的 `"progression": {}`（覆盖层要求父对象存在）。不加任何数值键，baby 冻结快照不变。
- `content_revision` 更新，`overlay_revision.json` 同步（047 规则）。

### 2.2 只在 normal 存在的定义（新增，基础包）
047 不允许覆盖层新增实体；051 汇报指出只靠界面隐藏不够。本任务的做法：
- 列表里的记录可带 `"difficulty_only": ["normal"]`。`apply_difficulty(pack, mode)` 在生成有效包时**递归删除** `mode` 不在列表里的记录（顶层实体和嵌套列表项，例如商店的 `items` 条目）。baby 有效包因此与改动前一致，冻结快照、`shops.py`、`scenario_context`、模型上下文都不用另做过滤。
- 用到它的：新顶层 `class_progression`（四职业的主动 / 被动定义）、卷轴道具、`magic_shop` 的新上架条目。
- 这些记录的数值即 normal 值（baby 永远读不到），052 可直接改基础包里的这些记录；把这条规则写进 `host/difficulty.py` 的模块文档字符串。它们的数值叶子按 047 规则归类（`NUMERIC_FIELDS` 或 `NON_BALANCE_FIELDS`），`test_no_unclassified_numeric_leaves` 必须通过。
- 新状态定义（第 4 节的 `mana_veil`）照 051 的做法放共享的 `status_defs`（惰性，无引用）。
- 不改共享的敌人记录（例如不给敌人加 `tags`）；竜断ち 的"龙"目标表写在技能定义里。

### 2.3 `class_progression` 结构（键名工程可调，语义不变）
```json
{"id": "hero", "difficulty_only": ["normal"],
 "actives": [{"level": 3, "skill": {"id": "holy_sword_art", "name": "聖光の剣技", "...": "..."}}],
 "passive_groups": [{"level": 2, "options": ["departure_spirit", "heavy_armor_lore"]}],
 "passives": [{"id": "departure_spirit", "name": "旅立ちの気概", "stackable": true,
               "tiers": [{"tier": 1, "description": "…", "effects": {}}, {"tier": 2, "...": "..."}]}]}
```
- exp 模式下 `level_skills` **完全不读**；Lv1 技能仍取 `characters[].skills`。
- 可叠加被动的规则照 skills-v2 第 0.4 节：阶数 = 已选次数；名称后缀 `+1`、`+2`；被动栏只显示一条。

## 3. 等级与 EXP（normal）
| 规则 | 内容 |
|---|---|
| EXP 来源 | 战斗胜利（含杂兵、可重复的战斗，每次都给）；任务完成。逃跑、败北、绕过、隐密 / 交涉跳过：0 |
| 战斗 EXP | 按遭遇的 `encounter_class` 一次性发放（不是按敌人个数）：trash / elite / boss 取 `exp_rewards`；`scripted_loss`、`guest` 为 0；未填分类按 `EXP_UNCLASSIFIED`（暂定同 trash）；`npc_combat` 遭遇按它自己的分类 |
| 任务 EXP | 除 `main_ignis` 外，任务状态变为完成时发 `EXP_QUEST`，每个任务一次 |
| 发放时机 | 战斗在结算（`_victory_delta` / 结算提交）时发；任务在完成时发。全部由引擎结算，**模型的 state_delta 不能改 `exp`、`level`、`passives`、`learned_spells`**（拒绝并记 system log） |
| 升级 | 累计 EXP 达到 `exp_table[n]` 即升到 n；一次可连升多级，逐级应用 `level_gains` 并各记一条 `level_up` 事件；每次升级回满 HP/MP/SP（决定 13）；满级后 EXP 照记，显示为 MAX |
| 里程碑 | exp 模式下 `_apply_milestones` 不再升级（flag 照常设置，`completed_milestones` 不再增长） |
| 获得主动 | 到达 3 / 5 / 7 级时把 `actives` 中对应技能加入 `skills`；`replaces` 只用于 大いなる癒し・浄化（exp 模式下旧 大いなる癒し 本来就不会出现，只为迁移存档时替换） |
| 被动选择 | 到达 2 / 4 / 6 / 8 级时把该级加入 `pending_passive_choices`；选择见第 6 节 |
| 技能清空（魔法使い の呪い） | 照现有规则：清空当时已有的技能并记 `skills_cleared_through_level`；之后升到更高等级照常获得主动。`learned_spells`、被动的处理见待确认 Q11，暂定：`learned_spells` 一并清空、被动保留 |

## 4. 各职业主动与被动（normal）
记号：`B` 见 skills-v2 第 0.1 节；"复用"列写 051 / 现有能力，"新增"列写本任务要做的引擎能力。`〔名〕` 是第 8 节的暂定参数。

### 4.1 勇者
| 等级 | 名称 | 消耗 | 效果 | 复用 | 新增 |
|---|---|---|---|---|---|
| 1 | 渾身斬り | 3 SP | 维持现状 | — | — |
| 1 | 神聖の庇護 | 0，cd 1 | 维持（cd 1 已在 051 覆盖层） | `cooldown` | — |
| 3 | 聖光の剣技 | 2 MP | physical + holy 各 1 段，`1d6+str/4`，命中 92；无论命中与否，本回合敌方阶段受伤 ×0.75 | `multi_elements`、`self_status: holy_blessing` | — |
| 5 | 薙ぎ払い | 3 SP | 全体，`1d6+str/4`，命中 90；场上只剩 1 名敌人时 ×(1+〔HERO_SWEEP_SINGLE〕) | `all_targets` | 条件倍率 `single_enemy` |
| 7 | 竜断ちの一太刀 | 7 SP + 5 MP | 单体，`2d10+str/2+5`，命中 100，**无视防御且无视抗性**（用户决定 5）；目标是 Boss、在〔DRAGON_IDS〕中、或最大 HP ≥〔DRAGON_SLASH_HP〕时 ×〔DRAGON_SLASH_MULT〕。不是 `true_damage`（弱体、护盾、防御姿态照常） | `ignores_defense` | 双资源 `costs`、`ignores_resistance`、条件倍率 `target_boss / target_id_in / target_max_hp_gte` |

| 等级 | 选项 A | 选项 B | 新增 |
|---|---|---|---|
| 2 | 旅立ちの気概（可叠加）第 1 阶：战斗第 1 回合玩家攻击命中视为 100%，回合开始 SP +3（可超上限，战斗结束截回） | 重装の心得：穿着 defense ≥ 1 的防具时防具 defense +1（G2：对百分比招式无效） | 被动触发 `round_start`；命中覆盖；防具修正 |
| 4 | 旅立ちの気概 +1：第 1–2 回合 | 不沈の盾：神聖の庇護 不消耗行动，冷却改为〔UNSINKABLE_CD〕 | `free_action`；被动改写技能字段 |
| 6 | 追い打ちの剣：普攻和单体剑技（渾身斬り、聖光の剣技、竜断ち；不含 薙ぎ払い）命中后追击：武器骰子减半（鉄の剣 1d8→`1d4`，不加属性），命中 100，physical，每次行动 1 次 | 逆境の焔：HP < 〔ADVERSITY_HP〕 时技能消耗 ×0.5（向上取整）、技能伤害 ×〔ADVERSITY_DMG〕 | 触发 `after_hit`；条件消耗 / 伤害修正 |
| 8 | 剣聖の境地：physical / 武器攻击无视敌人〔SWORD_SAINT_X〕的平坦防御；物理抗性 r < 1 时改为 r + (1−r)×〔SWORD_SAINT_X〕 | 竜殺しの宿命：受到 fire / ice / wind / dark 伤害 ×〔DRAGONSLAYER_TAKEN〕（含百分比招式）；普攻和攻击技能命中有弱点（倍率 > 1）的目标后追加 `element: weakness`、`1d4+str/6`、命中 100，每次行动 1 次 | 防御 / 抗性修正；受伤属性修正；`after_hit` 追击 |

### 4.2 僧侶
| 等级 | 名称 | 消耗 | 效果 | 复用 | 新增 |
|---|---|---|---|---|---|
| 1 | 治癒の祈り / 聖なる守護 | 4 MP / 6 MP | 维持 | — | — |
| 3 | 贖罪の印 | 2 SP | 单体，命中 95，无直接伤害；命中后施加 `holy_mark`〔ATONEMENT_N〕回合 | `on_hit_status`、`holy_mark`（DoT + `on_damage_followup`） | 无伤害技能的命中判定后施加状态（现在 `on_hit_status` 要求 damage > 0） |
| 5 | 大いなる癒し・浄化 | 14 MP | `healing: 2d6+wis/2`；清除自身全部可清除减益；溢出量 → `holy_afterglow` 护盾（上限最大 HP 25%）；同一溢出量同时触发 溢れる慈愛 | `cleanse`、`holy_afterglow` | 溢出量计算；**护盾吸收量必须由技能传入**（见下） |
| 7 | セラフィムの福音 | 12 MP，每场 1 次 | 自身 `gospel`〔GOSPEL_N〕回合：最大 HP ×2，**同时回复增加量**（用户决定 1，051 的 `gospel` 已如此实现）；受攻击伤害后回复原最大 HP 的〔GOSPEL_HEAL〕，每回合最多 2 次；结束截回 | `gospel`、`after_damage` | 玩家技能 `max_uses_per_battle` |

**聖なる余光 的护盾量（必须处理）**：051 的定义是 `shield.amount: 0`，`status_effects.apply` 取 `min(amount, max_hp × max_hp_ratio)`，不传 `amount` 时护盾为 0。施加时必须传入吸收量 = 实际溢出量。注意 `apply` 是 `{**definition, **spec}` 浅合并：spec 里只写 `modifiers.shield.amount` 会把定义里的 `max_hp_ratio: 0.25` 整个顶掉——要么传完整的 `{"amount": 溢出量, "max_hp_ratio": 0.25}`，要么把 `modifiers` 改成深合并（改了要证明 051 的现有测试和 baby 金标不变）。测试：溢出时护盾 > 0；溢出很大时 ≤ 最大 HP 的 25%；无溢出时不施加。状态说明文用 `docs/design/status-texts-draft.md` 的定稿是另一个 D1 任务，**本任务不改说明文**。

| 等级 | 选项 A | 选项 B | 新增 |
|---|---|---|---|
| 2 | 敬虔なる心（可叠加，职业例外）第 1 阶：回合结束回复最大 HP〔PIOUS_1〕；小数累积，满 1 才回复；HP 为 0 不触发 | 溢れる慈愛（可叠加）第 1 阶：治疗技能和回复道具的溢出量 ×〔OVERFLOW_1〕作为 holy 伤害打随机一名存活敌人（命中 100，计抗性和防御）；敬虔なる心、福音 的回复不算来源 | 触发 `round_end`、`heal_overflow` |
| 4 | 敬虔なる心 +1：〔PIOUS_2〕 | 苦行の悟り：MP 技能先用 SP 抵扣，〔ASCETIC_RATE〕，最多抵扣 MP 消耗的 50%（向下取整） | 消耗计算钩子 |
| 6 | 溢れる慈愛 +1：比例〔OVERFLOW_2〕（之前没选过则获得第 1 阶） | **光輪の加護**（用户决定 2）：每回合开始时自身 HP >〔HALO_HP_RATIO〕，对〔HALO_TARGET〕降下 holy 追击〔HALO_DAMAGE〕，命中 100；不触发 聖印 的追击 | 触发 `round_start`（HP 条件） |
| 8 | 不滅の聖域（用户决定 6）：治癒の祈り 的 MP 消耗为 0，不设次数上限，仍占行动 | 敬虔なる心 下一阶：第 3 阶〔PIOUS_3〕 | 消耗覆盖 |

### 4.3 魔法使い
| 等级 | 名称 | 消耗 | 效果 | 复用 | 新增 |
|---|---|---|---|---|---|
| 1 | 火球 | 5 MP | 现有 + 目标 HP 满时追加 `1d6`（第 5.1 节） | — | `conditional_bonus` |
| 1 | 氷の矢 | 3 MP | 现有 + 目标 HP ≤ 50% 时追加 `1d6` | — | 同上 |
| 3 | 魔力凝縮 | 3 SP，0 MP | 回复 MP `int/3+2`；获得 `magic_focus`（下一次攻击法术 ×〔FOCUS_X〕）；**本回合受伤 ×〔MEDITATE_GUARD〕**（用户决定 4） | `magic_focus`、`received_damage_multiplier` | 技能型 `kind: restore`；新状态 `mana_veil`（暂定名「凝縮の構え」【仮】，`received_damage_multiplier: 0.5`，`expires: enemy_phase_end`，增益，不可浄化） |
| 5 | 氷炎の双嵐 | 7 MP | 同一目标 fire、ice 各 1 段，`1d6+int/6`，命中 92；**施放时判定一次**：满血 → 火段 ×2；HP ≤ 50% → 冰段 ×2；与抗性相乘 | `multi_elements` | 每段条件倍率（施放时快照） |
| 7 | 元素崩壊 | 18 MP | 见第 5.3 节 | — | 动态 `multi_elements` |

| 等级 | 选项 A | 选项 B | 新增 |
|---|---|---|---|
| 2 | 魔力循環（可叠加）第 1 阶：回合开始 MP +〔MANA_CYCLE_1〕，本场累计上限最大 MP 的〔MANA_CYCLE_CAP_1〕 | 魔導の盾（可叠加）第 1 阶：战斗开始获得 1 层 `arcane_shield`（完全抵消下一次攻击伤害，不含持续伤害） | `battle_start`、`round_start` |
| 4 | 元素共鳴：本次攻击法术的元素与本场上一次攻击法术不同 → ×〔RESONANCE_X〕并返还 1 MP；本场第一次不触发；元素崩壊 不触发、也不更新"上一次" | 魔力循環 +1：〔MANA_CYCLE_2〕/〔MANA_CYCLE_CAP_2〕 | 记录上一次法术元素 |
| 6 | マナ・アーマー：受到攻击伤害的〔MANA_ARMOR〕改扣 MP（1:1，四舍五入），MP 不足的部分照扣 HP | 魔導の盾 +1：护盾被打掉后每〔SHIELD_REGAIN_EVERY〕回合重获，每场最多〔SHIELD_REGAIN_MAX〕次，重获的护盾传 `{"block_one_attack": true, "max_hp_ratio": 0.2}`（最多吸收最大 HP 20%） | 受伤分流；护盾重获 |
| 8 | 万象の支配者：普攻元素改为 `weakness`，目标没有弱点时用 arcane（不退回 physical）；打中弱点 ×〔OMNI_WEAK〕 | 魔力循環 下一阶：〔MANA_CYCLE_3〕/〔MANA_CYCLE_CAP_3〕 | 普攻元素覆盖、回退元素 |

"攻击法术" = 带 `spell_tier` 的魔法使い攻击技能；道具、普攻、大地の杖 的 裂地尖刺 不算。

### 4.4 盗賊
| 等级 | 名称 | 消耗 | 效果 | 复用 | 新增 |
|---|---|---|---|---|---|
| 1 | 影隠れ / 急所突き | 2 SP / 4 SP | 维持 | — | — |
| 3 | 目潰し投げ | 2 MP | `1d4+dex/4`，命中 95，physical；命中后 `blind`〔BLIND_N〕回合（−30，Boss −20），再施放刷新 | `on_hit_status`、`blind` | — |
| 5 | 刃の乱舞 | 4 SP | 全体，`1d4+dex/4`，命中 95；每个命中目标 +1 层 `poison` | `all_targets`、`on_hit_status.stacks` | — |
| 7 | 神速の影分身 | 8 SP + 4 MP | 自身 `haste`〔HASTE_N〕回合（含施放回合，施放回合立即 +1 行动）；持续中不能重放；结束后冷却 3 回合 ＝ 从施放起 `cooldown: 5` | `haste`（`no_reapply`、立即加行动）、`cooldown` | 双资源 `costs` |

| 等级 | 选项 A | 选项 B | 新增 |
|---|---|---|---|
| 2 | 軽業の身のこなし（可叠加）第 1 阶：闪避 +〔ACRO_EVADE_1〕（不受基础上限 20% 限制，计入总上限 40%）；敌人攻击落空时 SP +1，每回合最多〔ACRO_SP_CAP_1〕 | 毒使いの技（可叠加）第 1 阶：普攻和攻击技能命中附加 1 层 `poison`，上限 3 | 被动闪避加成；`after_enemy_miss` |
| 4 | 暗器の達人：每场第一次使用消耗品不消耗行动 | 軽業 +1：闪避合计〔ACRO_EVADE_2〕，SP 每回合最多〔ACRO_SP_CAP_2〕 | `free_action`（每场 1 次） |
| 6（推断） | 見切り反撃：敌人攻击落空，或 影隠れ 生效时命中盗賊 → 自动短剑追击 `1d6`（不加 DEX），命中 100，physical；**不设触发上限**（用户决定 3） | 毒使いの技 +1：毒上限 3 → 5（之前没选过则获得第 1 阶） | `after_enemy_miss` / `after_guarded_hit` 追击 |
| 8（推断） | 無明の暗殺者：对精英和 Boss 的直接伤害 ×〔ASSASSIN_X〕（不含持续伤害） | 軽業 下一阶：闪避合计〔ACRO_EVADE_3〕，落空 SP +2，每回合最多〔ACRO_SP_CAP_3〕 | 按遭遇分类的伤害修正 |

### 4.5 共通引擎能力（新增，全部数据驱动，不为单个技能写死）
| 能力 | 要点 |
|---|---|
| `costs: {"sp": n, "mp": m}` | 两项都够才能用；灰显原因单份【仮】；`cost_reduction`、逆境の焔、苦行の悟り 作用于各项 |
| `conditional_multipliers` / `conditional_bonus` | 条件：`target_hp_full`、`target_hp_ratio_lte`、`single_enemy`、`target_boss`、`target_id_in`、`target_max_hp_gte`、`self_hp_ratio_lt`；在掷骰前、施放时判定 |
| `ignores_resistance` | 暂定：抗性倍率固定 1.0（见待确认 Q2） |
| 玩家 `max_uses_per_battle` | 服务端拒绝、灰显，计数在战斗状态里 |
| 技能 `kind: restore` | 复用道具的 restore 结算 |
| `free_action` | 使用后不减 `actions_remaining` |
| 被动框架 | 触发器：`battle_start`、`round_start`、`round_end`、`after_hit`、`after_enemy_miss`、`after_guarded_hit`、`after_damage_taken`、`heal_overflow`；静态修正：命中、闪避、防御、抗性、受伤、造成伤害、消耗、技能字段改写。被动追击带 `status_followup` 标记，不再引发 聖印 追击和其他被动 |
| 服务端校验 | 冷却、次数、双资源、`free_action` 与 051 一样在服务端拒绝；自由行动路径映射到技能时给同样原因 |

## 5. 魔法使い：法术补完与卷轴
### 5.1 补回 火球 / 氷の矢（只在 normal 覆盖层）
- 火球：`conditional_bonus: [{"if": "target_hp_full", "damage": "1d6"}]`；氷の矢：`[{"if": "target_hp_ratio_lte", "ratio": 0.5, "damage": "1d6"}]`。追加伤害并入同一次伤害结算（同元素、同抗性、同防御），不是第二段。
- baby 的 火球 / 氷の矢 不变（文本照旧，baby 不补效果）。

### 5.2 卷轴（`difficulty_only: ["normal"]`）
| 道具 ID | 名称 | 学会 | 学会的法术 | 售价 | 上架 |
|---|---|---|---|---|---|
| `spellbook_lightning` | 雷撃の術式巻物 | 雷撃 | 敌方全体，`1d4+int/4`，命中 90，lightning，5 MP，`spell_tier: basic` | 〔PRICE_LIGHTNING〕 | 青のローブ魔法店（`magic_shop`），库存 1 |
| `spellbook_arcane_lance` | 魔力の槍の術式巻物 | 魔力の槍 | 单体，`1d6+int/2`，命中 95，arcane，`ignores_defense`，4 MP，`spell_tier: basic` | 〔PRICE_ARCANE〕 | 同上 |

- 风刃 / 水弾 是否加入见待确认 Q7；本任务不做。
- 字段：`category: "spellbook"`、`learn_skill: {…法术定义…}`、`learnable_by: ["mage"]`、`consumable: true`、战斗中不可用、`sell_price` =〔SPELLBOOK_SELL〕。
- 交互：持有物品栏里对卷轴显示「解析する」（只在非战斗时）。新接口 `POST /api/sessions/{id}/items/learn {item_id}`（或扩展 `items/use`，二选一，写明）。引擎确定性结算：消耗 1 卷，写入 `skills` 和 `learned_spells`，记 `spell_learned` 事件。不经过模型、不做判定。
- 拒绝（服务端与界面同源，按钮灰显并显示原因，文字【仮】）：
  - 非魔法使い：「【仮】魔法使いにしか解読できない術式だ。」
  - 已学会：「【仮】この術式はすでに身につけている。」（仍可卖出）
- `magic_shop` 现有条目（大地の杖、治療の巻物、火球術の巻物）不动；一次性的 火球術の巻物 不是 spellbook。

### 5.3 元素崩壊（Lv7，18 MP）
- `multi_elements` 在施放时由 `learned_spells`（初始 火球、氷の矢 + 卷轴法术，按学会顺序；只含 `spell_tier: basic`）的元素生成，每元素 1 段，`1d4+int/5`，命中 95。
- 最多〔BURST_MAX_HITS〕段：超过时按对目标的抗性倍率从高到低选，同倍率按学会顺序。
- 只有 2 种时约 1.7 B 是有意的（skills-v2 第 3.3 节）。

## 6. 被动选择 UI 与叙述钩子
### 6.1 引擎与接口
- `pending_passive_choices`：待选等级的升序列表。`public_session` 在 exp 模式下返回 `progression` 块：`level`、`exp`、`exp_to_next`（满级为 null）、`passives`（名称含后缀、说明）、`pending`（每个待选等级的两个选项：名称、选后名称、`current_description` → `next_description`）。baby 不返回此块。
- `POST /api/sessions/{id}/passives/choose {level, passive_id}`：只接受最小的待选等级、该组内的选项、非战斗时；成功后更新 `passives`、`passive_history`，记 `passive_chosen` 事件；非法请求 400，原因用日文【仮】。
- 给 046 / 052 模拟：同一逻辑提供纯函数入口 `choose_passive(session, level, passive_id)`，在汇报里写明模拟如何调用（不改 `scripts/balance/`）。

### 6.2 客户端
- 状态栏显示「Lv N」和 EXP 条（仅 exp 模式）。
- 有待选时：升级的战斗结算显示完后自动弹出选择框；状态栏显示「パッシブを選ぶ（N）」按钮可随时重开（战斗中禁用，提示【仮】）。
- 选择框：标题「【仮】Lv{N} パッシブを選ぶ」；两张卡片，顺序固定为数据里的 A、B，**不标推荐、不排序、不暗示优劣**（决定 17）；可叠加选项显示「敬虔なる心 → 敬虔なる心+1：…」；点卡片后出确认「【仮】この選択は取り消せません。」+「決定」/「戻る」。
- **关闭（×、Esc、点外部）= 稍后再选**：选择保留在 `pending_passive_choices`，跨存档保留；**不自动替玩家选，也不阻止继续游戏**；待选期间该级被动不生效。连升多级时按等级依次选。这一处理见待确认 Q9。
- 窄屏可用；更新 `?v=` 缓存键；`node --check client/app.js` 通过。

### 6.3 叙述钩子（引擎决定，模型只叙述）
| 事件 kind | 何时 | data |
|---|---|---|
| `exp_gained` | 胜利结算 / 任务完成 | `amount`、`source`、`total`、`next` |
| `level_up`（现有 kind） | 每升一级 | 现有字段 + `exp`、`new_skills`、`passive_choice_level` |
| `skill_gained` | 获得 Lv3/5/7 主动 | `skill_id`、`name` |
| `passive_choice_pending` | 到达偶数级 | `level`、两个选项名 |
| `passive_chosen` | 玩家确认 | `level`、`passive_id`、`name`（含后缀） |
| `spell_learned` | 解析卷轴 | `skill_id`、`item_id` |
- 战斗中发生的事件经现有 `combat_result_for_llm().committed_events` 交给模型；非战斗事件走现有事件记录。事件 `text` 用日文【仮】。
- **不改提示词，不新增模型上下文字段**（新主动自然出现在已有的技能列表里）。模型输出的 state_delta 中 `exp`、`level`、`passives`、`learned_spells`、`pending_passive_choices` 一律拒绝。

## 7. 会话字段与旧存档迁移
### 7.1 新字段（全部只在 exp 模式下写入）
| 位置 | 字段 | 类型 | 说明 |
|---|---|---|---|
| `character` | `exp` | int | 累计 EXP |
| `character` | `passives` | `[{id, tier}]` | 每个被动一条 |
| `character` | `passive_history` | `{"2": id, …}` | 各级的选择 |
| `character` | `learned_spells` | `[skill_id]` | 学会顺序；新建魔法使い = `["fireball","ice_arrow"]` |
| `session` | `pending_passive_choices` | `[int]` | |
| `session` | `progression_revision` | str | 迁移标记，`"050"` |
| `combat`（战斗内，结束清除） | `passive_state` | dict | 再生小数、魔力循環 累计、上次法术元素、护盾重获次数、本回合 SP 回复数、每场次数等 |
- `area_snapshots` 与 `combat.original_character` 里的角色副本同样处理（沿用现有 load 循环）。
- 更新会话相关的 schema / 文档字符串（如有）。

### 7.2 迁移规则
| 存档 | 处理 |
|---|---|
| 无 `difficulty`（047 前）→ baby | 不写任何新字段；加载、刷新、继续游玩与改动前逐项一致（测试） |
| baby（047 后） | 同上 |
| normal，050 前创建（里程碑等级 L） | 刷新到 050 的 `content_revision` 时、**不在战斗中**才迁移（战斗中则在结算后）：保留 L、属性和上限（不追溯成长）；`exp = exp_table[L]`（L=1 为 0）；移除 `level_skills` 来源的技能并恢复被替换的 Lv1 技能，再授予 ≤ L 的新主动；≤ L 的偶数级进入 `pending_passive_choices`；魔法使い `learned_spells` = 当前拥有的基础法术；写 `progression_revision`。幂等。见待确认 Q8 |
| normal，050 后创建 | 正常 |
- 旧存档缺任何新键时都按"不存在 = 默认"处理，不能抛错；`difficulty` 缺省仍视为 baby（047）。

## 8. 暂定参数（052 调；本任务只录入）
| 参数 | 暂定值 | 来源 |
|---|---|---|
| `EXP_TABLE`（累计） | Lv2 20 / Lv3 50 / Lv4 90 / Lv5 140 / Lv6 200 / Lv7 280 / Lv8 380 | 5.2 目标：P0 到 Ignis Lv4、P2 Lv6、P3 Lv7 |
| `EXP_TRASH` / `EXP_ELITE` / `EXP_BOSS` | 5 / 15 / 40 | 5.2 比例 1:3:8 |
| `EXP_UNCLASSIFIED` | 同 trash | Q5 |
| `EXP_QUEST` | 10 | 5.2 |
| `LEVEL_GAINS` | 每级 = 现在 `milestones` 的每级 gains（四职业各自），Lv2–8 相同 | skills-v2 0.1 按 +17.5% HP 算，052 统一 |
| `HERO_SWEEP_SINGLE` | 0.75 | 第 1.1 节 |
| `DRAGON_IDS` | `ignis`、`draco_dragon`、`dragon_knight_mounted`（`lava_drake` 待确认 Q3） | |
| `DRAGON_SLASH_MULT` / `DRAGON_SLASH_HP` | 1.35 / 80 | |
| `UNSINKABLE_CD` | 2 | H2 |
| `ADVERSITY_HP` / `ADVERSITY_DMG` | 0.5 / 1.25 | |
| `SWORD_SAINT_X` | 0.30 | |
| `DRAGONSLAYER_TAKEN` | 0.8 | |
| `ATONEMENT_N` | 3 | |
| `GOSPEL_N` / `GOSPEL_HEAL` | 3 / 0.08 | |
| `PIOUS_1/2/3` | 3% / 5% / 7% | 第 2.3 节 |
| `OVERFLOW_1/2` | 0.75 / 1.25 | |
| `ASCETIC_RATE` | 2 SP = 1 MP | C4 |
| `HALO_HP_RATIO` | 0.70 | 用户决定 2，未给数 |
| `HALO_DAMAGE` / `HALO_TARGET` | `1d3`，holy / 随机一名存活敌人 | 按 C5 ≤ +15% 估；Q1 |
| `FOCUS_X` / `MEDITATE_GUARD` | 1.3 / 0.5 | |
| `MEDITATE_RESTORE` | `int/3+2` | |
| `RESONANCE_X` | 1.15 | |
| `MANA_ARMOR` | 0.25 | |
| `MANA_CYCLE_1/2/3`、`MANA_CYCLE_CAP_1/2/3` | +1/+2/+3 MP，20%/30%/40% | |
| `SHIELD_REGAIN_EVERY` / `SHIELD_REGAIN_MAX` | 3 / 2 | |
| `OMNI_WEAK` | 1.25 | |
| `BURST_MAX_HITS` | 4 | |
| `BLIND_N` / `HASTE_N` | 2 / 3 | |
| `ACRO_EVADE_1/2/3`、`ACRO_SP_CAP_1/2/3` | 5/8/10%，2/3/4 | |
| `ASSASSIN_X` | 1.15 | |
| `PRICE_LIGHTNING` / `PRICE_ARCANE` / `SPELLBOOK_SELL` | 60G / 45G / 售价的 50% | skills-v2 3.2（40–60G） |

参数写在数据里（覆盖层或 normal-only 记录），引擎不写死；汇报里列出每个参数的数据路径。

## 9. 不做什么
- 不调任何数值（第 8 节只录入）；不改 baby；不改敌人、遭遇分类、Ignis；不做 052 的模拟。
- 不做 风刃 / 水弾、伏笔线索 EXP、Ignis 前的等级上限（待确认）。
- 不改状态说明文（`status-texts-draft.md` 是另一个 D1 任务）；不新增美术（被动没有动画）。
- 不改 `scripts/balance/`、`scripts/playtest/`、`eval/benchmark/`、`docs/`、提示词。

## 10. 验收
### 10.1 baby 不变（最重要）
- **战斗金标**：051 的 `tests/fixtures/baby_combat_golden.json`（113 组 × 200 = 22600 场，seed 20261011）在 baby 和"normal 但覆盖层为空"下逐项一致，聚合 SHA256 仍为 `14d374747913957829d5162d7aa6d52dfd3ce9ec9b3f8560d1e5f96f0fd1caee`。
- **等级金标（新增）**：动手前在 HEAD 上生成 baby 会话的固定脚本：四职业各走 4 个里程碑 flag、`level_skills` 解锁、魔法使い 的 `clear_skills`、存档再加载；记录角色、技能、事件（去时间戳）的哈希。完成后 baby 逐项一致。
- 047 冻结快照测试通过，`baby_numeric_freeze.json` 未改动；baby 有效包与改动前相比只有 `content_revision` 和惰性的 `status_defs` / 空 `progression` 不同（测试列出差异键）。

### 10.2 单元测试（新增）
- 每个主动技能一条以上：消耗（含双资源）、命中、伤害公式、条件倍率边界（满血 / 50% / 单敌 / Boss / 龙 / 最大 HP 80）、状态施加、冷却与每场次数、服务端拒绝。
- 每个被动每一阶一条以上：触发时机、上限（魔力循環 累计、軽業 每回合 SP、魔導の盾 重获次数与 20%）、叠加阶数与名称后缀、"之前没选过则获得第 1 阶"、見切り反撃 一回合多次触发、不滅の聖域 消耗为 0、光輪の加護 HP 阈值两侧、追击不连锁。
- **聖なる余光**：溢出时护盾 > 0；溢出超过 25% 时被截断；无溢出不施加；同一溢出量同时触发 溢れる慈愛。
- EXP / 等级：各分类的 EXP；逃跑 / 败北 / 绕过为 0；可重复战斗每次都给；任务一次；连升多级（回满、逐级成长、逐级事件、多个待选被动）；满级；exp 模式下里程碑不升级；模型 state_delta 改 `exp` 等被拒。
- 被动选择接口：只接受最小待选级、组内选项、非战斗；关闭后保留；存档往返保留。
- 卷轴：魔法使い 学会、消耗、`learned_spells` 顺序；非魔法使い 与已学会被拒（服务端）；战斗中不可用；baby 有效包里不存在卷轴和上架条目；元素崩壊 2 / 3 / 4 / 5 种时的段数与挑选。
- `difficulty_only` 过滤：顶层与嵌套记录；baby / normal；`apply_difficulty` 仍为纯函数。
- 迁移：047 前存档、baby 存档、050 前的 normal 存档（L = 1 / 3 / 5，战斗中与非战斗）、迁移幂等；剧本迁移脚本幂等、两份剧本同步。
- 051 的 `survive_at_one` 审计在 normal 有效包仍通过。

### 10.3 回归与检查
- 冻结 benchmark 重放 194/194 不变（`--variant guard_rules --split dev`，不加 `--live`）。
- 离线通玩（`scripts/playtest/explore.py`，只运行）baby、normal 各四职业：exceptions=0、noncombat_dead_ends=0；baby 结果与 HEAD 基线一致；输出放 `.tmp-test/050/playtest-*`，不改 `eval/reports/playtest-*`。
- `python -m unittest discover -s tests -q`、`node --check client/app.js` 通过（沙箱内按 051 的方式：原测试 + 测试补丁一起跑，并如实写明原地命令的结果）。
- **浏览器检查**：normal 新开局，战斗胜利升到 Lv2 → 自动弹出选择框 → 关闭 → 状态栏按钮重开 → 选择 → 确认；再到 Lv3 获得主动；魔法使い 在物品栏解析卷轴、非魔法使い 看到灰显原因；桌面和窄屏各截一张，放 `.tmp-test/050/screens/`。没有可用浏览器就如实写明并留下截图脚本，**不得伪造截图**；设计负责人会另行在浏览器复查。

## 11. 交付（沙箱）
- Codex 沙箱**不能写 `.git`，也不能在 `tests/` 下新建文件**。测试与夹具写在 `.tmp-test/050/tests/`，用 051 同样的执行器叠加运行。
- 交付到 `.tmp-test/050/`：
  - `050.patch`：相对 HEAD 的完整补丁（代码 + 剧本 + 测试）；
  - `tests.patch`：只含测试与夹具；
  - `manifest.json`：`base_commit`、`files`、`patch_sha256`、`commit_message`（`[工程]` 前缀）；
  - `050-report.txt`：汇报（第 12 节）。
- 在仓库内独立临时目录从 HEAD 实际应用补丁并逐文件核对；文件 UTF-8 无 BOM。**不要提交，不要 `git add`。**

## 12. 汇报
1. 对 baby 的影响表（每项机制，预期全为"无"），以及两份金标的对比结果。
2. 实际写入覆盖层的条目和 `difficulty_only` 记录清单；每个第 8 节参数的数据路径。
3. 每个技能 / 被动的实现状态：完成 / 部分 / 未做，及复用了哪些 051 能力。
4. 29 个未分类遭遇的清单（地点、敌人）和按 `EXP_UNCLASSIFIED` 发放的结果；按现有 checkpoint 路线估算的四原型到达 Ignis 时的等级（只估算，不调）。
5. 050 前 normal 存档的迁移结果样例（L = 1 / 3 / 5）。
6. 占位文本清单（【仮】：事件文本、选择框、灰显原因、`mana_veil` 名称与说明）。
7. `scripts/balance/` 需要跟进的缺口（EXP、被动选择策略、卷轴购买、双资源、`free_action`、新条件倍率），以及 `choose_passive` 的调用方式。
8. 推断清单与偏离 spec 的地方；截图路径或无法截图的原因。

---

## 待设计负责人确认
- **Q0 两档共用 vs normal-only**：047「设计负责人决定」写的是"技能与被动、等级/EXP、新道具两档共用，不做开关"；本次派发要求 baby 等级行为完全不变、新机制只在 normal。本 spec 按派发写（与 051 的实际做法一致）。请确认，并决定是否回改 047 的那条决定。
- **Q1 光輪の加護**：X（暂定 70%）、追击伤害（暂定 `1d3` holy）、目标是"随机一名"还是"敌方全体"（用户原话"对敌方降下一道圣光追击"，暂定随机一名）。
- **Q2 竜断ち"无视抗性"的含义**：暂定抗性倍率固定 1.0，即对免疫（×0）也打满、对弱点（>1）也不加成。是否改为"只忽略 <1 的部分、保留弱点"？另外 ×1.35 是否保留（skills-v2 正文是在"抗性照常"的前提下给的）。
- **Q3** 溶岩ドレイク 是否算龙（skills-v2 第 1.1 节注）。
- **Q4 Ignis 前的等级上限**：5.2 写"Ignis 之前最多到 7"，是硬上限还是数值目标？Ignis 有击杀和净化两条结局 flag（`defeated_ignis`、`ignis_purified`）。本任务暂不做硬上限。
- **Q5 EXP 分配**：29 个地点战斗没有 `encounter_class`，暂定按 trash；EXP 按遭遇发放而不按敌人个数；哪些任务给 EXP（暂定除 `main_ignis` 外全部）；伏笔线索链的 EXP 没有数据定义，本任务不做。
- **Q6 推断的等级分组**：万象の支配者 组 Lv8、見切り反撃 组 Lv6、無明の暗殺者 组 Lv8 是 skills-v2 按节奏推断的（原稿没写等级）。
- **Q7** 风刃 / 水弾 卷轴是否加入（加入后 元素崩壊 仍按最多 4 段）；雷撃 是否改为 Lv1 初始法术或保证在砦之前可得（M7，删掉 火球・改 后 P0 魔法使い 没有群体攻击）。
- **Q8 050 前创建的 normal 存档**：暂定保留等级、`exp` 取当前等级门槛、旧 `level_skills` 换成新主动、补发待选被动。是否接受，或者直接视为 baby / 要求重开？
- **Q9 关闭被动选择框**：暂定"稍后再选，不自动选、不阻止游戏，待选期间不生效"。是否要在下一场战斗前强制选择？
- **Q10 既有等级技能**：exp 模式下 不屈の構え 删除（X1，影响勇者 5.5 应对手段"边缘"）；不沈の盾 下冷却 1 → 2（H2，暂定 2）。
- **Q11 魔法使い の呪い（`clear_skills`）** 在 exp 模式下：`learned_spells` 是否一并清空（暂定是，可再买卷轴重学）、被动是否保留（暂定保留）、之后的 Lv5/7 主动是否照常获得（暂定是）。
- **Q12 名称**：魔力凝縮 / 瞑想 二选一（暂用 魔力凝縮）；新状态 `mana_veil` 的日文名（暂定「凝縮の構え」）。
- **Q13 成长表**：现有里程碑 gains（如勇者每级 +5 HP，约 +25%）与 skills-v2 第 0.1 节按 +17.5% 换算的技能消耗不一致；Lv6–8 暂按同样的 gains。由 052 统一，确认即可。
- **Q14 风险（不需要现在决定，052 会测）**：不滅の聖域 无上限 + 敬虔なる心 第 3 阶会让 M3 在 Lv8 失控；見切り反撃 无上限有 M6 风险；C6（僧侶 技能回复单场已超 R3）。均按用户决定实现。

## 设计负责人决定（2026-10-21）

| # | 决定 |
|---|---|
| Q0 | 以本 spec 为准：baby 不变，新技能、被动、EXP、卷轴只在 normal。047 那条措辞随后改（设计侧，不在本任务）。 |
| Q1 | 光輪の加護：X = 70%，追击 `1d3+wis/8` holy、`accuracy: 100`，目标是随机一名存活敌人。数值由 052 调。 |
| Q2 | 竜断ち 的"无视抗性"：抗性倍率取 `max(1.0, 原倍率)`。减伤、免疫一律视为 1.0，弱点照常加成。对 Boss / dragon 标签 / 最大 HP ≥ 80 的 ×1.35 保留。 |
| Q3 | 溶岩ドレイク 带 `dragon` 标签。 |
| Q4 | 不做硬上限，"Ignis 之前最多 7 级"只是数值目标。 |
| Q5 | 按暂定执行：无 encounter_class 的按杂兵；EXP 按遭遇发；任务 EXP 除 main_ignis 外都给；伏笔线索链不发 EXP。 |
| Q6 | 按推断执行：万象 组 Lv8、見切り 组 Lv6、無明 组 Lv8（已在 skills-v2 记为推断，用户可改）。 |
| Q7 | 本任务只做 雷撃、魔力の槍 两种卷轴；风刃、水弾 留给后续内容 spec。雷撃 保持卷轴获得，青のローブ魔法店在砦之前可到达即可，052 用 M7 验证。 |
| Q8 | 接受。 |
| Q9 | 接受"稍后再选、不阻止游戏"。另加一点：状态栏常驻"被动未选择"提示，直到选完。 |
| Q10 | 接受。 |
| Q11 | 接受（已学法术清空，被动保留，之后的主动照常获得）。 |
| Q12 | 用 魔力凝縮（用户决定 4）；mana_veil 名为「凝縮の構え」。 |
| Q13 | Lv6–8 沿用现有成长幅度，052 统一处理。 |
| Q14 | 风险记录在案，052 用模拟测；本任务不加上限（不滅の聖域 不设上限、見切り反撃 不设上限是用户决定）。 |
