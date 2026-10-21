难度 D3 · 执行方 Codex gpt-6-astra high · 理由：要改引擎里全部致死伤害路径、遭遇修正、需求类型，两份剧本包要同步，还要经过难度过滤；验收要用模拟器反复调参才能到 70%，并跑 baby 金标回归。设计已经定了，改动集中在一场战斗里，所以定 D3 而不是 D4；涉及多个系统，所以用 astra
# 049 勇者の聖剣：ドラコ戦的暗线（分支 A 觉醒 / 分支 B 被夺）

来源：
- 用户原话（2026-10-20，摘要在 `docs/design/skills-v2-user-draft.md`「同一条消息里的其他要求」第 4 条）。**设计以原话为准，本 spec 不改。**
- `docs/design/scenario-v2.md` 第 4.4 节（ドラコ = 白竜ヴァイス，两阶段，变身时玩家不回复）、`docs/design/chapter5-v5.md` 第 4、6 节（ドラコ战支援，无支援胜率 [0.50, 0.70]，支援叠满 ≤ 0.92）。
- 047（覆盖层、`difficulty_only`）、050（EXP 等级、被动、`ignores_resistance`）、051（`survive_at_one` 审计、dex 闪避、敌人命中 100）、053（模拟器 v3、normal 会话构造、`attack_only`、开战快照）。

**执行时机：050c 和 053 合入之后才开工。**HEAD 里没有这两项就停下来汇报。

## 0. 前提、文件边界与对 baby 的处理
- **可以改**：`host/combat.py`、`host/status_effects.py`、`host/state.py`（需求类型、物品替换）、`host/difficulty.py`（只做新数值叶子的分类）、`host/scenario_context.py`（只在新日志缺字段时改）、`client/`（只在新日志或道具显示需要时改）、两份剧本包（**始终同步**）、`scenario_pack.schema.json`、`host/prompt/processed/difficulty/overlay_revision.json`、新增迁移脚本 `scripts/scenario/holy_sword_049.py`（**必须幂等**）、新增探针脚本 `scripts/balance/holy_sword_049.py`（只新增，可以调用 053 的公共函数）、`eval/balance/targets.json`（**只新增键**）、`eval/reports/049-*`、测试（用补丁交付，见第 9 节）。
- **不得改**：`baby_numeric_freeze.json`、`scripts/balance/` 里已有的文件、`scripts/playtest/`（只运行）、`eval/benchmark/`、`docs/`、提示词措辞（`gm_contract.py`、`free_actions.py` 的默认 prompt），也不改ドラコ / ヴァイス的任何现有数值。
- **难度**：先按**只在 normal**实现（理由见待确认 Q1），所有新记录都带 `"difficulty_only": ["normal"]`，靠 `apply_difficulty` 的递归过滤去掉，所以 baby 有效包里不存在它们。设计负责人如果在 Q1 选了"两档共用"，就把这些标记去掉，第 8.1 节的 baby 金标改为"只允许ドラコ战有差异，逐项列出"。

## 1. 现状（动手前核对，不一致写进汇报）
| 项 | 现状 |
|---|---|
| 最初的剑 | 勇者模板 `characters[hero].inventory` 里的「鉄の剣」（这条没有 `id`，按名称匹配到目录 `items[iron_sword]`）。说明文「一見質素な一振りの剣……」是伏笔。`combat`：`1d8+str/3`，命中 90，physical，slot weapon；初始装备 `["鉄の剣", "革の鎧"]`。没有商店卖，其他职业的模板里也没有 |
| 交给铁匠 | `forge.show_sword_to_blacksmith`（勇者限定，flag `showed_hero_sword`）→ `forge.accept_sword_fusion`（需要持有鉄の剣、没有氷鉄の大剣；移除鉄の剣，获得并装备氷鉄の大剣，flag `accepted_sword_fusion`） |
| 其他失去 / 不装备的途径 | ① `alley_night.accept_curse_offer_hero` 换装呪われた聖剣，`pay_curse_price_hero` 移除鉄の剣（交给商人）；② 商店能卖掉鉄の剣（`_can_sell` 不挡它）；③ `ian_ice_katana_aftermath.accept_ian_request` 给氷鉄の大剣但不移除鉄の剣（同时持有，装备哪把以引擎为准） |
| Ignis 结局 | 击杀：`dragon_valley_loc.victory_effects` 设 `defeated_ignis`。净化：`purify_ignis_*` 只设 `ignis_purified`。两者互斥，两条路都能进入ドラコ战 |
| 开战 | `castle_report.report_with_evidence`（`result_variants` 取第一条满足条件的；现在只有持有白竜の日誌的一条；hybrid 还有一条 prepared turn `report_with_evidence_neutral`）→ `draco_battle`（boss，不能逃跑，`encounter_modifiers` 6 条，`phase_allies` 有イグニス） |
| ドラコ数据（两包相同，normal 覆盖层没有ドラコ条目） | `draco_human` 剣聖ドラコ：HP 25，def 2，dex 12；剣聖の一閃 `1d8+5`、氷刃 `1d8+4` ice、護衛の構え；`next_phase: draco_dragon`。`draco_dragon` 白竜ヴァイス：HP 220，def 2，dex 10；抗性 fire 1.5 / ice 0.25 / physical 0.25 / **holy 0.25**；凍てつく吐息、白翼の薙ぎ払い 均为 `1d12+10`，雪嵐の咆哮（break_guard） |
| 致死处理 | 只有 `_resolve_attack` 读 `player_status.survive_at_one`（`before_hp > 1` 且结果 ≤ 0 → 留 1 HP）。其他扣玩家 HP 的路径不读它：`_apply_direct_formula_damage`（领域）、`status_effects` 的回合伤害、`self_damage`、诅咒治疗 |
| 阶段转换 | `_check_victory_or_defeat`：一阶段敌人倒下后换成 `next_phase` 模板，HP 回满，再执行 `_activate_phase_allies` 和 `_activate_encounter_modifiers` |
| 可复用 | `encounter_modifiers` 已支持 `enemy_defense`、`disabled_enemy_skills`、`enemy_hp_multiplier`、`received_element`、`basic_followup`、按技能名的 `damage_multiplier`；遭遇的 `start_events`（满足条件时开战记一条 warning）；`ignores_resistance`（取 `max(1.0, 原倍率)`）；`difficulty_only` |
| 缺 | 需求类型"装备中的物品"（现在只有 `has_item` / `lacks_item`）；敌人全部攻击统一乘倍率（现有的 `damage_multiplier` 只按技能名匹配）；修正给敌人追加技能；一次性"致死觉醒"触发器 |
| 模拟器的现有假设 | 旧 `checkpoints.py` 里勇者打ドラコ前都做了换剑（`accept_sword_fusion`），也就是落在分支 B。`targets.json` 里的 `draco_battle`：standard [0.5, 0.7]、no_fire < 0.3 |

## 2. 条件定义
| 分支 | 判定时机 | 条件（全部满足） |
|---|---|---|
| **A 觉醒** | 进入 `draco_battle` 开战时登记资格，战斗中触发 | `character_id: hero`；flag `defeated_ignis`；**装备中**的武器是「鉄の剣」（新需求类型 `equipped_item`，按名称或 `iron_sword` 匹配） |
| **B 被夺** | 揭发台词、开战时 | `character_id: hero`；flag `accepted_sword_fusion`。暂不看 Ignis 的结局（Q3） |
| 都不是 | — | 非勇者职业；勇者净化了 Ignis 但没交剑（Q2）；持有鉄の剣但没装备（Q4）；剑交给了商人或卖掉了（Q5）。这些情况都打**普通ドラコ** |
- A 和 B 天然互斥（换剑会移除鉄の剣）。测试要覆盖这一点。
- **非勇者**：这条暗线只属于勇者，三项条件里都有 `character_id: hero`。其他职业拿不到鉄の剣，也看不到铁匠的这两个动作。

## 3. 分支 A：致死觉醒（normal）
### 3.1 数据
`draco_battle.combat` 新增列表 `lethal_awakenings`（列表项可以被 `difficulty_only` 过滤；键名工程可以改，语义不能改）：
```json
{"id": "hero_holy_sword", "difficulty_only": ["normal"],
 "requirements": {"all": [{"character_id": "hero"}, {"flag": "defeated_ignis"}, {"equipped_item": "鉄の剣"}]},
 "transform_item": {"from": "鉄の剣", "to": "hero_holy_sword"},
 "restore": {"hp": "full"}, "set_flag": "holy_sword_awakened",
 "text": "【仮】…"}
```
- **资格在开战时判定一次**并记入 `combat`，之后战斗中不能换装备，所以不会变化。旧存档里如果有进行中的ドラコ战，它的 `encounter` 快照里没有这个字段，就不会觉醒，汇报里写明。

### 3.2 结算
| 规则 | 内容 |
|---|---|
| 触发 | 本场战斗中玩家**第一次**受到致死伤害：所有减免（防御、守护倍率、护盾、受伤倍率、マナ・アーマー）之后，伤害仍 ≥ 当前 HP。当前 HP 为 1 时也算 |
| 覆盖的伤害来源 | 写一个统一的钩子，所有扣玩家 HP 的路径都走它：`_resolve_attack`（含多段攻击的每一段）、`_apply_direct_formula_damage`、`status_effects` 的回合伤害。另外两条（`self_damage`、诅咒治疗）勇者在 A 条件下遇不到，也接上钩子，统一处理 |
| 效果顺序 | ① HP 锁在 1（写一条日志）→ ② 背包里装备中的「鉄の剣」原地换成 `hero_holy_sword` 并保持装备 → ③ HP 回满（只回 HP，MP / SP、状态都不动）→ ④ 设 flag `holy_sword_awakened` → ⑤ 写觉醒日志（【仮】）。同一行动后面的攻击段照常结算，打的是回满后的 HP |
| 和 `survive_at_one` 的先后 | 暂定**觉醒优先**：伤害够致死就觉醒，不消耗守护的 1 HP 保留（Q6） |
| 次数 | 每场一次。觉醒之后再受致死伤害，按现有规则处理（有 `survive_at_one` 就留 1 HP，没有就败北） |
| 阶段 | 一、二阶段都能触发；阶段转换不重置资格，也不会因为转换而触发 |
| G3 审计 | 这不是 `survive_at_one` 字段，是每场一次的触发器。051 的审计测试要把它列为"每场一次，已满足"，不能当成漏洞 |
| 日志与叙述 | 沿用现有日志类型，或者加一种 `awakening`（加的话要接进 `visual_kind` 和 `combat_result_for_llm().committed_events`）；不改提示词。模型的 state_delta 不能加 `hero_holy_sword`，也不能设 `holy_sword_awakened`（拒绝，并记 system log） |

### 3.3 新道具 `hero_holy_sword`（`difficulty_only: ["normal"]`，加在 `items`）
| 字段 | 值 |
|---|---|
| `name` | 勇者の聖剣 |
| `description` / `effect` | 【仮】（第 5 节） |
| `combat` | `kind: weapon`，`element: holy`，`damage`〔HOLY_SWORD_DAMAGE〕，`accuracy`〔HOLY_SWORD_ACC〕，`ignores_resistance`〔HOLY_SWORD_IGNORES_RES〕 |
| 其他 | `slot: weapon`、`key_item: true`、`non_removable: true`；图标暂用现有素材（`icon_dawn_sword.png`），缺的美术列进汇报 |
- 普攻改用圣剑之后，现有的追击照常叠加：追い打ちの剣（取武器骰子的一半）、霜断ちの刻印（`basic_followup`）。
- **调参范围**：为了到 70%，**只能**调上表里〔〕标出的三项，ドラコ / ヴァイス的数值一律不动。粗估：ヴァイス HP 220、holy 0.25，勇者 Lv6 觉醒后大约还能撑 3–4 回合。即使无视抗性，每次命中也要大约 60–80 伤害；不无视抗性的话要它的 4 倍（作为对比，虹晶の剣 期望约 31.5）。这个量级请在汇报里如实写出来（Q7）。

## 4. 分支 B：ドラコ持有圣剑（normal）
| 项 | 实现 |
|---|---|
| 开战前台词 | `report_with_evidence.result_variants` 在**最前面**加两条：「B 且持有日誌」「B」（`difficulty_only: ["normal"]`）。台词在现有揭发文后面追加一句【仮】，意思是"他已经拿到了对自己威胁最大的武器"。持有日誌的那条要保留原来的日誌句子。hybrid 的 `report_with_evidence_neutral` prepared turn 也要按同样条件出变体，否则要证明 `result_variants` 在 hybrid 模式下优先。三种模式（确定性、hybrid、LLM）下这句话都要出现 |
| 开战提示 | `draco_battle.combat.start_events` 加一条（条件同 B，`difficulty_only`），提示「ドラコは勇者の聖剣を装備している」【仮】 |
| 人形态加强 | `encounter_modifiers` 加一条 `id: draco_holy_sword`，`enemy_ids: ["draco_human"]`，条件同 B。新字段：`enemy_damage_multiplier: 1.3`（这个敌人所有直接攻击的伤害 ×1.3，包括普攻、技能、新技能；不影响 HP、防御、命中，见 Q8）；`extra_enemy_skills: [〔DRACO_HOLY_SKILL〕]` |
| 新技能〔DRACO_HOLY_SKILL〕 | 暂定 `{"id": "stolen_holy_blade", "name": "【仮】聖剣の一閃", "kind": "attack", "damage": "1d8+5", "accuracy": 90, "element": "holy", "ai_weight": 2}`（×1.3 在这之后乘） |
| 不变的部分 | 二阶段ヴァイス不变；国王修正（禁用護衛の構え、def −4）照常作用在 `draco_human` 上；`announced_modifiers` 照常把修正的 `text` 记进日志（这条修正的 `text` 用开战提示同一句话，或者留空，二选一并写明，不要重复显示） |
- 新数值叶子（`enemy_damage_multiplier`、新技能的骰子和命中、圣剑的三项）按 047 的规则归类，`test_no_unclassified_numeric_leaves` 要通过。

## 5. 占位文本（全部【仮】，由设计负责人定稿）
| 位置 | 暂定 |
|---|---|
| A：HP 锁定日志 | 「【仮】致命の一撃――だが、あなたは倒れなかった。」 |
| A：觉醒日志 | 「【仮】鉄の剣が白く輝き、勇者の聖剣へと姿を変えた。傷がふさがっていく。」 |
| A：`hero_holy_sword` 说明 / effect | 「【仮】眠っていた力を取り戻した、勇者のための剣。」／「【仮】通常攻撃が光属性になる」 |
| B：揭发台词追加句 | 「【仮】……もっとも、貴様の剣ならすでに我が手にある。我を脅かしうる唯一の刃だ」 |
| B：开战提示 | 「【仮】ドラコは勇者の聖剣を装備している。」 |
| B：新技能名 | 「【仮】聖剣の一閃」 |

## 6. 测量：70% 门槛（用 053 的模拟器）
### 6.1 门槛探针 G（只用 normal）
| 项 | 设定 |
|---|---|
| 会话 | 用 053 的 normal 会话构造（`apply_difficulty(pack, "normal")` → `session["difficulty"] = "normal"` → `progression.initialize`） |
| 等级 | 通过引擎升到 Lv6（把 `exp` 设成 `exp_table["6"] = 200`，按 `level_gains` 逐级升，回满）。预期：HP 45、MP 13、SP 20、STR 22、DEX 5、INT 5、WIS 5、END 15；dex 闪避 2%；鉄の剣 `1d8+7`。以引擎实际读数为准，和预期不一致的写出来 |
| 被动 | Lv2 / 4 / 6 三组，全部 2³ = 8 种组合（`choose_passive`），组合之间共用随机数 |
| 装备 / 状态 | 鉄の剣 + 革の鎧，没有饰品，不带消耗品；没有同伴；flags 只有 `defeated_ignis`（不设 `king_trust`、Robin、Mina、Robert、护符、`ignis_ally`）；HP / MP / SP 全满 |
| 策略 | `attack_only`（053 的 normal 口径：引擎的命中和闪避），只用普攻 |
| 样本 | 每种组合 N = 2000，seed 20261021，`--workers 1` 和 N 个 worker 的结果要逐字节一致 |
| **门槛** | 两个阶段合计（打倒ヴァイス才算赢）：8 种组合里**最低的那个**胜率点估计 ≥ 0.70，同时报告 Wilson 95% 区间（Q9） |
| 同时报告 | 觉醒发生在第几阶段、第几回合的分布；没触发觉醒就赢 / 输的比例；觉醒后剩余回合数；ヴァイス剩余 HP 的分布 |

### 6.2 报告项（不设门槛）
| 编号 | 配置 | 报告 |
|---|---|---|
| R1 | 053 normal 的 `draco_battle` 开战快照（P2 中位等级、P0b 两份），勇者武器换成鉄の剣，加 `defeated_ignis`；`heuristic_v3` 和 `attack_only`；支援分"无"和"全部" | 胜率、回合数；和普通ドラコ（同一快照，不给觉醒资格）对比的差值。标出超过 chapter5-v5 上限 0.92 的格（Q10） |
| R2 | 同样的快照，勇者装备氷鉄の大剣并设 `accepted_sword_fusion`（分支 B），对照组不设这个 flag；`heuristic_v3`，standard 准备 | 胜率差、人形态阶段受到的伤害、人形态阶段的败北率（Q11） |
| R3 | 053 各原型的勇者实际落在哪个分支（A / B / 都不是） | 表格；以及 053 normal 基线里ドラコ那一格的变化 |
- `targets.json` 只新增键：`draco_battle_holy_sword`（`status: "draft"`，`attack_only_lv6_min_win_rate: 0.70`，判定口径按 6.1）。不改原有的 `draco_battle` 各项；A 路线和 no_fire < 0.3 的冲突写进汇报（Q10）。

## 7. 不做什么
- 不改ドラコ / ヴァイス的现有数值、其他支援、结局文本（觉醒后的结局要不要变体见 Q12）。
- 不给其他职业做对应的暗线；不改铁匠、商人、商店的现有动作（鉄の剣能不能卖见 Q5）。
- 不新增美术；不改提示词；不调 053 的策略参数。

## 8. 验收
### 8.1 baby 不变
- 051 的战斗金标（`tests/fixtures/baby_combat_golden.json`）在 baby 下、以及"normal 但覆盖层为空"时逐项一致，聚合 SHA256 和 050 记录的一致；050 的等级金标一致。
- 047 冻结快照通过，`baby_numeric_freeze.json` 没有改动；baby 有效包与改动前相比只有 `content_revision` 不同（用测试列出差异键）。

### 8.2 单元测试（新增）
- 分支判定：A / B / 都不是，包括第 2 节的每一种情况（非勇者、净化、持有但没装备、交给商人、卖掉、同时持有氷鉄の大剣）；A 和 B 互斥。
- 觉醒：第一次致死伤害锁 1 HP → 换剑 → 回满，一场一次；每条伤害来源都会触发（敌人攻击、多段攻击的中间一段、领域、回合伤害）；当前 HP = 1 时触发；先于 `survive_at_one`（按 Q6 的结论写）；阶段转换前后都能触发；觉醒后普攻是 holy 并用圣剑的数值；追い打ちの剣、霜断ちの刻印 照常叠加；第二次致死按现有规则；其他战斗不触发。
- B：两条揭发台词变体的优先顺序；开战提示；人形态全部攻击 ×1.3；追加的 holy 技能会出现在 AI 的候选里；国王修正仍然生效；二阶段不受影响。
- 模型 state_delta 加 `hero_holy_sword` 或设 `holy_sword_awakened` 被拒绝。
- `equipped_item` 需求类型：按名称和 id 匹配；没装备时为假。
- G3 审计在 normal 有效包通过；`difficulty_only` 让 baby 有效包里没有任何新记录；迁移脚本幂等；两份剧本同步。

### 8.3 回归
- 冻结 benchmark 重放 194/194 不变（`--variant guard_rules --split dev`，不加 `--live`）。
- 离线通玩（`scripts/playtest/explore.py`，只运行）baby、normal 各跑四职业：exceptions = 0，noncombat_dead_ends = 0；baby 和 HEAD 基线一致；输出放 `.tmp-test/049/`。
- 053 的 baby 复现测试照样通过；normal 基线只允许ドラコ那一格变化（列出来）。
- `python -m unittest discover -s tests -q`、`node --check client/app.js` 通过；改了客户端就更新 `?v=` 缓存键。

## 9. 交付（沙箱，同 050 / 053）
- 测试和夹具写在 `.tmp-test/049/tests/`，用 050 的叠加执行器运行，并如实写明在仓库原地运行命令的结果。
- 交付到 `.tmp-test/049/`：`049.patch`（相对 HEAD 的完整补丁）、`tests.patch`、`manifest.json`（`base_commit`、`files`、`patch_sha256`、`commit_message`，用 `[工程]` 前缀）、`049-report.txt`。
- 在仓库里另开一个临时目录，从 HEAD 实际应用补丁并逐文件核对；文件用 UTF-8 无 BOM。**不要提交，不要 `git add`。**

## 10. 汇报
1. 第 1 节现状核对（尤其是：一共有哪些路径会失去或不装备鉄の剣，以及ドラコ在 normal 下的有效数值）。
2. 门槛结果：8 种组合 × 胜率 / 区间 / 回合数，觉醒时机的分布；最终的〔HOLY_SWORD_*〕取值，以及调参过程（每一轮试过的值和对应胜率）。
3. R1–R3 表。
4. 对 baby 的影响（预期：无），两份金标的比对结果。
5. 【仮】文本清单；缺的美术。
6. 揭发台词在三种模式下的实际显示截图或日志片段；觉醒、开战提示在战斗 UI 里的截图（放 `.tmp-test/049/screens/`。没有浏览器就写明原因，**不得伪造**）。
7. 推断清单、偏离 spec 的地方。

---

## 待设计负责人确认
- **Q1 baby 还是 normal**：建议**只在 normal**。理由：① 047 在 2026-10-21 改过决定，新道具、新机制只在 normal；勇者の聖剣 是新道具，致死觉醒是新机制。② 70% 门槛是按 normal 的 Lv6、dex 闪避、敌人命中 100 定的，baby 满级是 Lv5，没法照同一口径测。③ 分支 B 会让 baby 里换过剑的勇者打ドラコ变难，破坏冻结的平衡（[0.50, 0.70]）。反方理由：这是剧情内容；048 的精灵之泉改动也算剧情结构，两档都生效了。如果要两档共用，baby 需要另外给一套数值（baby 到不了 Lv6），而且要明确批准"调整 baby"。
- **Q2 净化了 Ignis 的勇者**：用户原话写的是"已斩杀邪竜"，暂定净化路线**不觉醒**（打普通ドラコ，有イグニス援护）。确认，还是净化路线也觉醒？
- **Q3 分支 B 要不要看 Ignis 结局**：原话里 B 只写了"把剑交给铁匠"。暂定击杀、净化两条路线都生效。
- **Q4 持有但没装备**（例如拿了イアン的氷鉄の大剣并装备上）：按原话"仍装备"，暂定**不觉醒**，B 也不生效，打普通ドラコ。要不要给玩家提示（例如铁匠或剑本身给一句暗示）？
- **Q5 剑交给了商人（呪いの代価）或者卖掉了**：暂定两个分支都不生效。ドラコ是否也算"拿到了"商人那把剑？鉄の剣要不要改成不能卖，来保护这条暗线？
- **Q6 和 神聖の庇護 的先后**：暂定觉醒优先（守护状态下受到致死伤害也觉醒）。另一种做法是守护先保留 1 HP、不触发觉醒，那样玩家可以把觉醒"留着"。
- **Q7 调参的手段**：要到 70%，圣剑每次命中要很大的伤害（第 3.3 节的粗估）。建议 `ignores_resistance: true`，这样白竜的 holy 0.25 不会减伤，和"对他威胁最大的武器"的设定一致；数值只调圣剑本身。可以接受这个量级吗？还是要换别的手段（例如觉醒后ヴァイス的 holy 抗性失效）？
- **Q8 "强 30%"的含义**：用户原话是"攻击强 30%"，暂定只把人形态所有攻击的伤害 ×1.3，HP、防御、命中不变。
- **Q9 门槛口径**：暂定取 8 种被动组合里最低的那个（"也要有 70%"理解为下限）；没有支援、没有同伴，鉄の剣 + 革の鎧。备选：只看 053 的 `first`（A/A/A）或 `table` 组合；或者用 053 的 P2 开战快照。要不要设上限（例如 ≤ 0.85）？
- **Q10 和现有目标的冲突**：A 路线下 `heuristic` 胜率预计会超过 standard 的 [0.50, 0.70]，没有火属性手段也能赢（no_fire < 0.3 会不成立），加上全部支援还可能超过 0.92。暂定 A 路线不受这三条约束，只看新键 `draco_battle_holy_sword`。确认？
- **Q11 分支 B 的目标**：原话没给胜率。暂定只报告与普通ドラコ的差值，不设门槛。需要目标吗（例如人形态阶段的败北率上限）？
- **Q12 剧情细节**（本 spec 不擅自决定）：ドラコ怎样从铁匠那里拿到剑；铁匠ローベルト（以及 048b 的讨伐后台词）要不要提这件事；觉醒后结局要不要变体；「勇者の聖剣」以外的正式文本（第 5 节）。

## 设计负责人决定（2026-10-21，技术口径）

| # | 决定 |
|---|---|
| Q6 | 觉醒优先于 神聖の庇護 的 `survive_at_one`。 |
| Q7 | 圣剑 `ignores_resistance: true`，伤害量级按 70% 门槛调，接受很大的数值（觉醒武器）。只调圣剑，不改ドラコ。 |
| Q8 | "强 30%"只指伤害 ×1.3，HP、防御、命中不变。 |
| Q9 | 8 种被动组合取最低 ≥ 0.70，无同伴、无支援；上限：取最高的组合 ≤ 0.90，超过的话汇报。 |
| Q10 | A 路线只看新键 `draco_battle_holy_sword`，不受 standard、no_fire 和 0.92 上限约束。 |
| Q11 | 分支 B 不设胜率门槛，只报告与普通人形态的差值，052 再看。 |

Q1–Q5、Q12（剧情和难度范围）待用户决定。

## 用户决定（2026-10-21）

| # | 决定 |
|---|---|
| Q1 | 只在 normal 生效。baby 不变。 |
| Q2 | 净化 Ignis 的勇者不觉醒（按原稿）。 |
| Q3 | 分支 B 不看 Ignis 结局，击杀、净化都生效。 |
| Q4 / Q5 | 鉄の剣 卖掉、交给诅咒商人、持有但没装备，两个分支都不生效。鉄の剣 设为不能卖，道具说明加一句暗示它有特别的意义（【仮】，文案后补）。 |
| 分支 B 影响 | 大多数勇者会去锻冶屋换剑而进入分支 B，用户接受，作为玩家的取舍。052 按此调ドラコ和换剑的价值。 |
| Q12 | 剧情细节（ドラコ怎么拿到剑、铁匠和讨伐后台词、结局变体）先用【仮】，之后由写作线补。 |
