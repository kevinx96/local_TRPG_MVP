# 052 后技能说明更新（定稿草案）

来源：Antigravity argon medium（`.agy-runs/skills-texts-v2.md`，dispatch 试用九），设计负责人审阅。数值依据 `docs/design/skills-final-numbers-052.md`（052c3 最终表）。

## 设计负责人决定

- **雷撃 是敌方全体**：设计（skills-v2 第 160 行，050 spec）本来就是全体。050 实现成了单体，052c 改回全体。试用三时设计负责人照当时的剧本把 argon 写的"全体"改成了"单体"，那次改错了，这次以设计为准。
- **神聖の庇護、影隠れ 是 baby 也用的基础技能**，说明文字两档共用。所以说明里**不写冷却**，只写两档都成立的效果。冷却由界面根据技能数据统一显示（见工程任务 052d）。
- 影隠れ 的旧说明「2ターン敵の標的にならない」两档都不对（实际是被ダメージ ×0.25，且引擎默认 `survive_at_one` 为真），这次一起改正。
- **魔力循環+2（第 3 阶）和第 2 阶数值相同**，是 052c 上调前两阶时漏掉的。改为 `amount: 4, cap_ratio: 0.5`（延续逐阶 +1 / +10% 的节奏）。说明是「ラウンド開始時のMP回復量が4に増え、1戦闘の回復上限が最大MPの50%になる。」。这一阶在 Lv8，大多在 Ignis 之后才拿到，不另做模拟。
- 火球、氷の矢 的条件加成只在 normal 有，基础说明没法写，这次不改。
- 只改了骰子公式或消耗的条目，说明不用动（说明本来就不写公式和消耗）。

## 改动表

| 数据路径 | 名称 | 旧说明 | 新说明 | 变化 |
|---|---|---|---|---|
| `characters.@id=hero.skills.@id=divine_guard.description` | 神聖の庇護 | 盾を構えて次の攻撃に備える。致死ダメージも耐え抜く。 | 被ダメージを半減し、致死ダメージもHP1で耐える。 | normal 难度新增冷却 1 回合（`cooldown: 1`），并补入实际结算的伤害半减说明（39字） |
| `characters.@id=thief.skills.@id=hide_in_shadow.description` | 影隠れ | 影に溶けて気配を消す。2ターン敵の標的にならない。 | 影に溶けて身を隠し、被ダメージを0.25倍にする。致死ダメージもHP1で耐える。 | 实际结算为受击伤害 0.25 倍（`guard_multiplier: 0.25`，旧文案仍为未改写的旧机制），且 normal 难度新增冷却 1 回合（`cooldown: 1`）（39字） |
| `class_progression.@id=hero.actives.@id=5.skill.description` | 薙ぎ払い | 敵全体に物理攻撃を行う。敵が1体のみの時はダメージが1.75倍になる。 | 敵全体に物理攻撃を行う。敵が1体のみの時はダメージが1.8倍になる。 | 对单目标伤害倍率 `1.75倍 → 1.8倍`（34字） |
| `class_progression.@id=hero.passives.@id=adversity_flame.tiers.@id=1.description` | 逆境の焔 | HPが最大HPの50%未満の時、スキルの消費が半減し、スキルダメージが1.25倍になる。 | HPが50%未満の時、スキルの消費が半減し、スキルダメージが1.3倍になる。 | 技能伤害倍率 `1.25倍 → 1.3倍`，并精简至 40 字以内（38字） |
| `class_progression.@id=hero.passives.@id=sword_saint.tiers.@id=1.description` | 剣聖の境地 | 物理攻撃時、敵の防御力と物理耐性による軽減をそれぞれ30%無視してダメージを与える。 | 物理攻撃時、敵の防御力と物理耐性の軽減をそれぞれ40%無視してダメージを与える。 | 物理防御与物理耐性穿透率 `30% → 40%`（40字） |
| `class_progression.@id=cleric.passives.@id=holy_halo.tiers.@id=1.description` | 光輪の加護 | ラウンド開始時にHPが70%を超えていれば、ランダムな敵1体に聖属性の追撃を行う。 | ラウンド開始時にHPが60%を超えていれば、ランダムな敵1体に聖属性で追撃する。 | 触发 HP 阈值 `70% → 60%`（另追击骰子 `1d3+wis/8 → 1d4+wis/8`，按规则不写入说明）（40字） |
| `class_progression.@id=mage.passives.@id=mana_cycle.tiers.@id=1.description` | 魔力循環 | ラウンド開始時にMPを1回復する。1戦闘につき最大MPの20%まで回復できる。 | ラウンド開始時にMPを2回復する。1戦闘につき最大MPの30%まで回復できる。 | 每回合恢复 MP `1 → 2`，每场战斗恢复上限 `最大MP的20% → 30%`（39字） |
| `class_progression.@id=mage.passives.@id=mana_cycle.tiers.@id=2.description` | 魔力循環+1 | ラウンド開始時のMP回復量が2に増え、1戦闘の回復上限が最大MPの30%になる。 | ラウンド開始時のMP回復量が3に増え、1戦闘の回復上限が最大MPの40%になる。 | 每回合恢复 MP `2 → 3`，每场战斗恢复上限 `最大MP的30% → 40%`（40字） |
| `class_progression.@id=mage.passives.@id=mana_armor.tiers.@id=1.description` | マナ・アーマー | 攻撃による被ダメージの25%を、HPではなくMPで肩代わりして受けるようになる。 | 攻撃の被ダメージの20%をMPで肩代わりする。1戦闘につき最大HPの50%まで。 | 吸收率 `25% → 20%`，新增每场战斗吸收上限 `最大HP的50%`（`mana_armor_cap_ratio: 0.5`）（40字） |
| `items.@id=spellbook_lightning.learn_skill.description` | 雷撃 | 雷光を走らせ、敵単体に雷属性の魔法攻撃を行う。 | 雷光を走らせ、敵全体に雷属性の魔法攻撃を行う。 | 攻击范围由单体改为敌全体（新增 `"all_targets": true`，威力 `1d8+int/3 → 1d4+int/4`）（23字） |
| `class_progression.@id=mage.passives.@id=mana_cycle.tiers.@id=3.description` | 魔力循環+2 | （与 +1 相同） | ラウンド開始時のMP回復量が4に増え、1戦闘の回復上限が最大MPの50%になる。 | 数值修正：3 / 40% → 4 / 50% |
