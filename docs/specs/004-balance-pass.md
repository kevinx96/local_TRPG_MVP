# 004 数值调整：里程碑成长 + 一轮调参

按 `docs/design/balance.md` 的决定实施。目标是让 `python -m scripts.balance.sim --check` 尽量达标。这次**允许修改剧本数值**，但只能改下面列出的部分。

## 1. 引擎：里程碑成长
- 剧本新增顶层 `milestones`：`[{"id": "lv2", "level": 2, "trigger_flag": "...", "gains": {...按职业...}}]`。玩家拿到触发 flag 时，由引擎（`state.apply_state_delta` 那一层）执行升级：
  - 按 balance.md 第 1 条的规则提高上限和属性，并补满 HP/MP/SP。
  - 写一条 system log，例如「レベルが3に上がった」，措辞沿用现有 system log 的风格。
  - 升级在会话里记录 `character.level` 和已触发的 milestone id；同一个 milestone 不能触发两次。
- 触发 flag 从剧本里现有的 flag 中选择（离开森林、攻下砦、抵达村庄、进入竜の谷）。选择依据写进推断清单。
- 旧存档没有 `level` 时视为 Lv1，不追溯补发升级（在 `docs/api-free-actions.md` 或 README 里加一句说明）。
- GM 契约不变：模型仍然不能写 level 或上限。
- 技能解锁：Lv3 和 Lv5 每个职业各提出 **2 个**候选技能（名字用日语，符合现有命名风格，效果用现有的技能字段表达），写进 `eval/balance/skill_candidates.json`。**先不要加进剧本**，标 `TODO(design)`。模拟里分别用"无新技能"和"候选 A"跑两遍，供选择。

## 2. 剧本数值（`dragon_rpg.json` 和 `dragon_rpg_hybrid.json` 同步修改）
允许修改：
- 敌人的 hp/max_hp、属性、技能伤害公式、命中率、`combat.defense`/`evade`
- 多敌人遭遇的敌人数量（`enemy_ids` 的个数），敌人种类不变
- 同伴 `blue_robed_mage` 的 `round_start_effects`（按 balance.md 第 2 条；可能需要引擎支持"每 N 回合"和"按最大 HP 比例"，如需要就实现，并写测试）
- 聖なる杖的伤害和属性（balance.md 第 4 条）

不允许修改：角色的初始数值（成长只来自 milestone）、剧情文本、遭遇分类、xanxus 和 warlock 两场战斗、敌人的名字和描述。

### 圣属性消耗品（balance.md 第 5 条）
- 在商人战之前、所有职业都会经过的现有地点或 NPC 里，提出 2–3 个发放位置候选（发放方式、数量），写进汇报，标 `TODO(design)`。
- 这次先在**模拟的 checkpoint 里**假设玩家已经拿到 2 个，物品数据可以先加进 `items`（名字和描述用占位：`聖水`，`TODO(design)` 定稿），但不要接进任何地点的动作。

## 3. 调参方法
- 用 002 的模拟器做搜索：先算伤害预算（balance.md 第 3 条，写一个检查函数，报告每个遭遇在对应等级下的期望每回合敌方伤害占玩家 HP 的比例），再在允许的范围里调整，直到 `--check` 越界尽量少。
- 每一处数值改动都要记录：原值 → 新值、理由（哪个指标越界）。汇总进报告，作为设计审核的依据。
- checkpoint 按里程碑更新（每个遭遇对应的等级），继续保持 `status: proposed`。
- 不要为了达标去改目标文件 `targets.json`。

## 4. 报告
`eval/reports/balance-<日期>-pass1.md`：
1. 调整前后对比：每个遭遇的达标情况（heuristic）、职业差距、同伴提升幅度。
2. 伤害预算表（调整前后）。
3. 改动清单（原值 → 新值，理由）。
4. 仍然越界的遭遇和原因：如果需要改机制或剧本结构才能解决，写出来，不要硬调。
5. 技能候选在模拟里的效果。

## 验收
- 两条验证命令通过；milestone 有测试：触发、不重复触发、旧存档兼容、补满资源。
- `--check` 的越界数相比 002 明显下降，报告里给出前后数字。
- 改动清单完整。

## 汇报要回答
1. 达标遭遇数（按类别），以及调整前后对比。
2. 同伴削弱以后的提升幅度是否落在 10–20 个百分点。
3. 哪些遭遇靠调数值解决不了，原因是什么。
4. 技能候选和圣属性物品的发放位置候选。
5. 其余按 `docs/roles/engineering.md` 的汇报格式。
