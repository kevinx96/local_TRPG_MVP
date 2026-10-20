# 050 技能、被动、卷轴、升级界面文案（定稿草案）

来源：Antigravity argon medium 初稿（`.agy-runs/skills-texts.md`，dispatch 试用三）。设计负责人抽查了参数（旅立ち、刃の乱舞、大いなる癒し・浄化、元素崩壊、两种卷轴），改了以下几处：
- 雷撃：初稿写成"敌全体"并编了「水辺や金属鎧の敵に有効」。实际是单体，没有这个机制，已改。
- 不滅の聖域：精简措辞。
- 被动卡片未学徽章定为「新規習得」。

## 设计负责人决定

- **刃の乱舞 + 毒使いの技 一次叠 2 层毒**：保留，作为盗贼毒流派的联动奖励。052 用模拟测数值，过强再调。
- **被动追击日志缺名字**（追い打ちの剣、竜殺しの宿命、光輪の加護、見切り反撃）：工程给追击字典补 `name`，日志显示被动名。
- **事件文案**：`_event` 按事件类型套用第 3 节的模板；`spell_learned` 的 data 补 `name`。
- 技能 JSON 里多余的 `cost: 0, cost_type: "mp"` 字段不影响结算，本次不清理。

## 1. 技能和被动表（含新增状态 `mana_veil`）

所有说明均控制在 **40 字以内**，采用常体（`〜する`／`〜になる`），不写骰子公式，以 `class_progression` 与 `host/combat.py` 的实际结算为准。

| 数据路径 | 名称 | 说明 | 备注（机制疑问） |
|---|---|---|---|
| `class_progression.@id=hero.actives.@id=3.skill.description` | 聖光の剣技 | 敵単体に物理と聖属性の2連撃。次の敵フェーズ終了まで被ダメージが0.75倍になる。 | `holy_blessing` 在 `_apply_utility_effects` 阶段赋予，不依赖攻击是否命中。 |
| `class_progression.@id=hero.actives.@id=5.skill.description` | 薙ぎ払い | 敵全体に物理攻撃を行う。敵が1体のみの時はダメージが1.75倍になる。 | — |
| `class_progression.@id=hero.actives.@id=7.skill.description` | 竜断ちの一太刀 | 防御と耐性を無視する必中の斬撃。竜・ボス・最大HP80以上の敵に威力1.35倍。 | 代码实现为 `max(1.0, multiplier)`，即无视 `<1` 的抗性但保留 `>1` 的弱点倍率。 |
| `class_progression.@id=hero.passives.@id=departure_spirit.tiers.@id=1.description` | 旅立ちの気概 | 戦闘の1ラウンド目、自身の攻撃が必中になり、ラウンド開始時にSPを3回復する。 | 战斗中恢复的 SP 可临时超过 `max_sp`，战斗结束时回落至上限。 |
| `class_progression.@id=hero.passives.@id=departure_spirit.tiers.@id=2.description` | 旅立ちの気概+1 | 攻撃必中と毎ラウンド開始時のSP3回復の効果が、2ラウンド目まで継続するようになる。 | 相比 Tier 1，生效回合数从第 1 回合扩展为第 1～2 回合（每回合初均 +3 SP）。 |
| `class_progression.@id=hero.passives.@id=heavy_armor_lore.tiers.@id=1.description` | 重装の心得 | 防御力1以上の鎧を装備している時、自身の防御力がさらに+1される。 | 仅判定 `slot == "armor"` 且 `defense >= 1` 的护甲。 |
| `class_progression.@id=hero.passives.@id=unsinkable_shield.tiers.@id=1.description` | 不沈の盾 | 「神聖の庇護」が行動を消費せずに発動でき、クールダウンが2ラウンドになる。 | — |
| `class_progression.@id=hero.passives.@id=sword_followup.tiers.@id=1.description` | 追い打ちの剣 | 通常攻撃や単体剣技が命中した時、1行動につき1回、必中の物理追撃を行う。 | 适用技能限定为 `power_slash`、`holy_sword_art`、`dragon_slash`；`薙ぎ払い` 不触发。 |
| `class_progression.@id=hero.passives.@id=adversity_flame.tiers.@id=1.description` | 逆境の焔 | HPが最大HPの50%未満の時、スキルの消費が半減し、スキルダメージが1.25倍になる。 | 消耗折半向上取整（`max(1, math.ceil(cost * 0.5))`），同时作用于 MP 和 SP。 |
| `class_progression.@id=hero.passives.@id=sword_saint.tiers.@id=1.description` | 剣聖の境地 | 物理攻撃時、敵の防御力と物理耐性による軽減をそれぞれ30%無視してダメージを与える。 | 对複合属性技能（如 `聖光の剣技`）仅在物理属性那一击上生效。 |
| `class_progression.@id=hero.passives.@id=dragon_destiny.tiers.@id=1.description` | 竜殺しの宿命 | 火・氷・風・闇の被ダメージ0.8倍。弱点を持つ敵への攻撃命中時、弱点属性で追撃する。 | 每次行动最多触发 1 次追击；若敌人有多个弱点，按最高倍率弱点属性追击。 |
| `class_progression.@id=cleric.actives.@id=3.skill.description` | 贖罪の印 | 敵単体に3ラウンドの間「聖印」を刻み、毎ラウンドの聖属性ダメージと追撃を誘発する。 | 本技能自身不造成直接伤害（`damage: "0"`），靠命中后赋予 `holy_mark` 生效。 |
| `class_progression.@id=cleric.actives.@id=5.skill.description` | 大いなる癒し・浄化 | HPを大きく回復して弱体を全て浄化し、余剰回復分を最大HP25%までの障壁に変える。 | 习得后替换「大いなる癒し」；先结算「溢れる慈愛」伤害，再将溢出的治疗量转为 `holy_afterglow`。 |
| `class_progression.@id=cleric.actives.@id=7.skill.description` | セラフィムの福音 | 1戦闘1回。3ラウンドの間、最大HPを2倍にして増加分を回復し、被弾時にHPを回復する。 | 赋予 `gospel`：最大 HP 翻倍并恢复等量 HP，每回合最多 2 次在受击后恢复原最大 HP 的 8%。 |
| `class_progression.@id=cleric.passives.@id=pious_heart.tiers.@id=1.description` | 敬虔なる心 | ラウンド終了時、自身のHPを最大HPの3%回復する。 | 最低恢复 1 点 HP（满血时不触发）。 |
| `class_progression.@id=cleric.passives.@id=pious_heart.tiers.@id=2.description` | 敬虔なる心+1 | ラウンド終了時のHP回復量が、最大HPの3%から5%に上昇する。 | — |
| `class_progression.@id=cleric.passives.@id=pious_heart.tiers.@id=3.description` | 敬虔なる心+2 | ラウンド終了時のHP回復量が、最大HPの5%から7%に上昇する。 | — |
| `class_progression.@id=cleric.passives.@id=overflow_mercy.tiers.@id=1.description` | 溢れる慈愛 | 回復スキルや道具の余剰回復量の75%を、ランダムな敵1体への聖属性ダメージに変える。 | 药水等恢复道具溢出也会触发；必中且无视防御，计入圣属性抗性。 |
| `class_progression.@id=cleric.passives.@id=overflow_mercy.tiers.@id=2.description` | 溢れる慈愛+1 | 余剰回復量から聖属性ダメージへの変換率が、75%から125%に上昇する。 | — |
| `class_progression.@id=cleric.passives.@id=ascetic_wisdom.tiers.@id=1.description` | 苦行の悟り | スキルの消費MPの最大50%までを、1MPにつき2SPで肩代わりして発動できる。 | 自动优先消耗 MP，仅在需要或可替代至 50% 上限时扣除 SP。 |
| `class_progression.@id=cleric.passives.@id=holy_halo.tiers.@id=1.description` | 光輪の加護 | ラウンド開始時にHPが70%を超えていれば、ランダムな敵1体に聖属性の追撃を行う。 | 判定条件为严格大于 70%（`hp > max_hp * 0.7`）。 |
| `class_progression.@id=cleric.passives.@id=immortal_sanctuary.tiers.@id=1.description` | 不滅の聖域 | 「治癒の祈り」の消費MPが0になる。使用回数の制限はない。 | 仍消耗 1 次行动，无每场或每回合次数限制。 |
| `class_progression.@id=mage.actives.@id=3.skill.description` | 魔力凝縮 | MPを回復して次の攻撃魔法の威力を1.3倍にし、次の敵フェーズ終了まで被ダメージを半減する。 | 同时赋予 `magic_focus` 与 `mana_veil`。 |
| `class_progression.@id=mage.actives.@id=5.skill.description` | 氷炎の双嵐 | 敵単体に火と氷の2連撃。敵のHPが満タンなら火、50%以下なら氷の威力が2倍になる。 | 两个条件均在施放瞬间按目标当前 HP 比例判定（而非第一击结算后）。 |
| `class_progression.@id=mage.actives.@id=7.skill.description` | 元素崩壊 | 習得済みの基本属性魔法の力を解き放ち、敵単体に最大4連撃の属性魔法攻撃を行う。 | 从已习得的基础属性（火/氷/雷/魔力）中按对目标最有效的顺序取最多 4 种依次攻击。 |
| `class_progression.@id=mage.passives.@id=mana_cycle.tiers.@id=1.description` | 魔力循環 | ラウンド開始時にMPを1回復する。1戦闘につき最大MPの20%まで回復できる。 | 单场累计上限按 `max(1, int(max_mp * 0.2))` 计算。 |
| `class_progression.@id=mage.passives.@id=mana_cycle.tiers.@id=2.description` | 魔力循環+1 | ラウンド開始時のMP回復量が2に増え、1戦闘の回復上限が最大MPの30%になる。 | 相比 Tier 1：每回合恢复 1→2，单场上限 20%→30%。 |
| `class_progression.@id=mage.passives.@id=mana_cycle.tiers.@id=3.description` | 魔力循環+2 | ラウンド開始時のMP回復量が3に増え、1戦闘の回復上限が最大MPの40%になる。 | 相比 Tier 2：每回合恢复 2→3，单场上限 30%→40%。 |
| `class_progression.@id=mage.passives.@id=arcane_guard.tiers.@id=1.description` | 魔導の盾 | 戦闘開始時に「魔導の盾」を得て、最初に受ける1回分の攻撃ダメージを無効化する。 | 持续整场直至抵消 1 次攻击伤害。 |
| `class_progression.@id=mage.passives.@id=arcane_guard.tiers.@id=2.description` | 魔導の盾+1 | 盾が消えた3ラウンド後に最大HP20%までの盾を張り直す。1戦闘につき2回まで再展開する。 | 再展开的护盾同样最多抵挡 1 次攻击，且吸收上限为最大 HP 的 20%，超额伤害穿透。 |
| `class_progression.@id=mage.passives.@id=element_resonance.tiers.@id=1.description` | 元素共鳴 | 直前の攻撃魔法と異なる属性の攻撃魔法を使うと、威力が1.15倍になりMPが1回復する。 | 「元素崩壊」不触发也不刷新记录；「氷炎の双嵐」视为 `["fire", "ice"]` 组合属性。 |
| `class_progression.@id=mage.passives.@id=mana_armor.tiers.@id=1.description` | マナ・アーマー | 攻撃による被ダメージの25%を、HPではなくMPで肩代わりして受けるようになる。 | MP 不足时仅抵扣当前剩余 MP，其余伤害仍由 HP 承受；DoT 等非攻击伤害不触发。 |
| `class_progression.@id=mage.passives.@id=omni_master.tiers.@id=1.description` | 万象の支配者 | 通常攻撃が敵の弱点属性（なければ魔力属性）になり、弱点を突いた時は威力が1.25倍になる。 | — |
| `class_progression.@id=thief.actives.@id=3.skill.description` | 目潰し投げ | 敵単体に物理攻撃を行い、2ラウンドの間「目潰し」を付与して命中率を下げる。 | `blind` 在常规敌人上降低 30% 命中，Boss 上降低 20% 命中。 |
| `class_progression.@id=thief.actives.@id=5.skill.description` | 刃の乱舞 | 敵全体に物理攻撃を行い、命中した敵それぞれに「毒」を1スタック付与する。 | 若同时拥有被动「毒使いの技」，目前代码会叠加为命中时共赋予 2 层毒（详见第 4 节）。 |
| `class_progression.@id=thief.actives.@id=7.skill.description` | 神速の影分身 | 3ラウンドの間「神速」状態になり、毎ラウンドの行動回数が+1される。 | 发动当回合立即额外获得 1 次行动；持续期间不可再次施放，结束后需冷却 3 回合。 |
| `class_progression.@id=thief.passives.@id=acrobatics.tiers.@id=1.description` | 軽業の身のこなし | 回避率+5%。敵の攻撃が空振りした時、SPを1回復する（1ラウンド最大2SPまで）。 | — |
| `class_progression.@id=thief.passives.@id=acrobatics.tiers.@id=2.description` | 軽業の身のこなし+1 | 回避率が+8%に上昇し、敵の空振りによるSP回復の上限が1ラウンド3SPに増える。 | 相比 Tier 1：闪避 +5%→+8%，每回合恢复上限 2→3 SP（单次仍为 1 SP）。 |
| `class_progression.@id=thief.passives.@id=acrobatics.tiers.@id=3.description` | 軽業の身のこなし+2 | 回避率が+10%に上昇し、敵の空振り1回につきSPが2回復する（1ラウンド最大4SPまで）。 | 相比 Tier 2：闪避 +8%→+10%，单次恢复 1→2 SP，每回合上限 3→4 SP。 |
| `class_progression.@id=thief.passives.@id=poison_craft.tiers.@id=1.description` | 毒使いの技 | 通常攻撃や攻撃スキルが命中した時、敵に「毒」を1スタック付与する（最大3スタック）。 | — |
| `class_progression.@id=thief.passives.@id=poison_craft.tiers.@id=2.description` | 毒使いの技+1 | 毒の最大スタック数が3から5に増え、より深い毒を敵に重ねられるようになる。 | 相比 Tier 1：玩家可叠毒上限从 3 层提升至 5 层。 |
| `class_progression.@id=thief.passives.@id=hidden_weapon_master.tiers.@id=1.description` | 暗器の達人 | 各戦闘で最初の1回のみ、消費アイテムを行動を消費せずに使用できる。 | 仅限 `consumable` 类道具，每场战斗限 1 次。 |
| `class_progression.@id=thief.passives.@id=counter_sight.tiers.@id=1.description` | 見切り反撃 | 敵の攻撃が空振りした時、または「影隠れ」中に被弾した時、必中の物理追撃を行う。 | 无每回合或每场次数上限。 |
| `class_progression.@id=thief.passives.@id=unseen_assassin.tiers.@id=1.description` | 無明の暗殺者 | 精鋭およびボス敵に対する直接攻撃のダメージが1.15倍になる。 | 按遭遇类型 `encounter.type in ("elite", "boss")` 判定；毒等 DoT 不享受加成。 |
| `status_defs.@id=mana_veil.description` | 凝縮の構え | 次の敵フェーズ終了まで、被ダメージが0.5倍になる。 | 句式与 `docs/design/status-texts-draft.md` 中的 `holy_blessing` 保持完全一致。 |

---

## 2. 卷轴表

道具说明控制在 **20～50 字**，带道具风味并点明仅「魔法使い」可解读；习得技能说明控制在 **40 字以内**（常体）。

| 数据路径 | 说明 |
|---|---|
| `items.@id=spellbook_lightning.description` | 蒼い電光の術式が記された古い羊皮紙。魔法使いにしか解読できない。解析すると「雷撃」を習得する。 |
| `items.@id=spellbook_lightning.learn_skill.description` | 雷光を走らせ、敵単体に雷属性の魔法攻撃を行う。 |
| `items.@id=spellbook_arcane_lance.description` | 純粋魔力を槍と化す秘術が刻まれた巻物。魔法使いにしか解読できない。解析すると「魔力の槍」を習得する。 |
| `items.@id=spellbook_arcane_lance.learn_skill.description` | 防御力を無視する純粋魔力の槍で、敵単体に魔力属性の魔法攻撃を行う。 |

---

## 3. 事件、界面、错误信息表

涵盖 `host/progression.py`、`host/combat.py`、`client/app.js`、`client/index.html` 中所有带 `【仮】` 的占位文本。

| 文件 / 位置 | 现占位 | 新文案 | 可用变量 |
|---|---|---|---|
| `host/progression.py:49` (`_event` / `skill_gained`) | `【仮】{name}` | `新たなスキル「{name}」を習得した！` | `{skill_id}`, `{name}` |
| `host/progression.py:123` (`_event` / `exp_gained`) | `【仮】` | `経験値を{amount}獲得した。` | `{amount}`, `{source}`, `{total}`, `{next}` |
| `host/progression.py:141` (`_event` / `passive_choice_pending`) | `【仮】` | `Lv{level}のパッシブスキルが選択可能になった。` | `{level}`, `{options}`（列表） |
| `host/progression.py:142` (`_event` / `level_up`) | `【仮】` | `レベルが{level}に上がった！` | `{level}`, `{levels_gained}`, `{gains_per_level}`, `{exp}`, `{new_skills}`, `{passive_choice_level}` |
| `host/progression.py:217` (`_event` / `passive_chosen`) | `【仮】{name}` | `パッシブ「{name}」を習得した！` | `{level}`, `{passive_id}`, `{name}` |
| `host/progression.py:249` (`_event` / `spell_learned`) | `【仮】` | `術式を解読し、「{name}」を習得した！`（若不改 `data` 则用：`術式巻物を解読し、新たな魔法を習得した！`） | 当前 `data` 仅有 `{skill_id}`, `{item_id}`；建议在 `learn_spellbook` 的 `data` 中补入 `"name": skill["name"]` |
| `host/progression.py:200` (`choose_passive`) | `【仮】このレベルのパッシブは選択できません。` | `このレベルのパッシブは現在選択できません。` | 无 |
| `host/progression.py:204, 210` (`choose_passive`) | `【仮】このパッシブは選択できません。` | `そのパッシブは選択できません。` | 无 |
| `host/progression.py:223` (`learn_spellbook`) | `【仮】この道具は解析できません。` | `この道具は解読できる術式巻物ではない。` | 无 |
| `host/progression.py:225` (`learn_spellbook`) | `【仮】戦闘中は解析できません。` | `戦闘中は術式巻物を解読できない。` | 无 |
| `host/progression.py:228` (`learn_spellbook`) | `【仮】魔法使いにしか解読できない術式だ。` | `魔法使いにしか解読できない術式だ。` | 无（去掉 `【仮】` 即可，原句已很自然） |
| `host/progression.py:230` (`learn_spellbook`) | `【仮】この術式はすでに身につけている。` | `この術式はすでに習得している。` | 无 |
| `host/progression.py:239` (`learn_spellbook`) | `【仮】道具が見つかりません。` | `対象の道具を所持していません。` | 无 |
| `host/combat.py:694` (`_passive_round_end` / `敬虔なる心`) | `【仮】` | `敬虔なる心の祈りでHPが{amount}回復した。` | `healed`（即 `data["amount"]`）、`actor["name"]` |
| `host/combat.py:734` (`_ability_disabled_reason`) | `【仮】リソースが不足しています。` | `リソースが不足しています。` | 无（与 `host/combat.py:450, 1924` 既有文案一致） |
| `host/combat.py:737` (`_ability_disabled_reason`) | `【仮】この戦闘ではこれ以上使用できません。` | `この戦闘ではこれ以上使用できません。` | 无 |
| `host/combat.py:878` (`_player_skill` / `kind == "restore"`) | `"【仮】" + resolved_skill["name"]` | `{name}で{resource}を{amount}回復した。` | `resolved_skill["name"]`, `restored` (`{amount}`), `resource.upper()` (`{resource}`, 默认 `"MP"`), `detail` (`{formula}`) |
| `client/app.js:757` (`ITEM_TYPE_LABELS.spellbook`) | `【仮】術式巻物` | `術式巻物` | 无 |
| `client/app.js:850, 856` (`renderPassiveNotice`) | `【仮】パッシブ未選択` | `未選択のパッシブがあります` | `pending`（待选等级数组） |
| `client/app.js:850, 856` (`renderPassiveNotice`) | `【仮】戦闘終了後に選択できます。` | `戦闘終了後に選択できます。` | `inCombat` |
| `client/app.js:874` (`openPassiveModal`) | `` `【仮】Lv${group.level} パッシブを選ぶ` `` | `` `Lv${group.level} パッシブ選択` `` | `${group.level}` |
| `client/app.js:885` (`openPassiveModal`) | `【仮】未修得` | `新規習得` | `opt.current_tier`（此处为 `current_tier === 0` 时的徽章） |
| `client/index.html:329` (`#passive-modal`) | `【仮】この選択は取り消せません。` | `一度選んだパッシブは変更できません。` | 无 |

---

## 4. 中文简短说明

### 4.1 最没把握的几条文案

1. **`竜断ちの一太刀`（`class_progression.@id=hero.actives.@id=7.skill.description`）**
   - 机制包含 4 个信息点：必中、无视防御与抗性、单次高威力物理斩击、对龙/Boss/高血量（最大 HP ≥ 80）敌人 1.35 倍。受 40 字上限约束，草稿写成了「防御と耐性を無視する必中の斬撃。竜・ボス・最大HP80以上の敵に威力1.35倍。」（38 字）。如果觉得在技能说明里直接写「最大HP80以上」略显生硬，可改为「竜や強敵に威力1.35倍」，但会牺牲一部分数值透明度。
2. **`魔導の盾+1`（`class_progression.@id=mage.passives.@id=arcane_guard.tiers.@id=2.description`）**
   - Tier 2 再展开的护盾与开场护盾不同：不仅有「破盾后每 3 回合再展开、单场最多 2 次」的限制，还多了「最多吸收最大 HP 20%」的容量上限。浓缩进 40 字内写成了「盾が消えた3ラウンド後に最大HP20%までの盾を張り直す。1戦闘につき2回まで再展開する。」（40 字），字数刚好卡满。
3. **`host/progression.py` 的 `_event` 模板方式**
   - 目前 `_event(result, event_type, data)` 是把所有事件共用一行 `"message": "【仮】" + str(data.get("name", ""))`。工程合入第 3 表的 6 条事件文案时，需要改成按 `event_type` 映射各自的模板字符串，且 `spell_learned` 的 `data` 目前只传了 `{"skill_id": skill["id"], "item_id": item_id}`，未传 `"name": skill["name"]`——若想显示习得的魔法名，需在 `progression.py:249` 顺手加上 `"name": skill["name"]`。
4. **`client/app.js:885` 的 `【仮】未修得`**
   - 日语 TRPG 常用字里，我们在其他地方统一用了「習得」（而非「修得」）。当 `current_tier === 0` 时，弹窗卡片右上角标签写 `新規習得` 或 `未習得` 都通顺，我优先推荐 `新規習得`（与升級时的 `Tier 1 → 2` 形成更直观的对比）。

---

### 4.2 实际参数 / 代码实现与 `docs/design/skills-v2.md` 的出入（按数据路径列出）

核对 `host/prompt/processed/dragon_rpg.json`（由 `scripts/scenario/levels_skills_v2.py` 生成）及 `host/combat.py`、`host/progression.py` 后，发现以下需要注意的差异或实现细节（其中部分是 `skills-v2.md` 末尾「用户决定」或 `050` 末尾「设计负责人决定」已覆盖但正文未同步，部分是代码实现层面的细节）：

1. **`class_progression.@id=hero.actives.@id=7.skill`（`竜断ちの一太刀`）**
   - `skills-v2.md` §1.1 正文写「属性抗性照常生效」，文末「用户决定 5」改为「同时无视抗性」，`050` Q2 决定进一步明确为 `max(1.0, 原倍率)`（即无视 `<1` 的抗性、保留 `>1` 的弱点倍率）。代码已按 `050` Q2 实现。
   - 此外，JSON 中该技能在拥有 `"costs": {"sp": 7, "mp": 5}` 的同时，还残留了构建器默认生成的 `"cost": 0, "cost_type": "mp"`（不影响 `_skill_costs` 优先读取 `costs`，但属于冗余字段）。
2. **`class_progression.@id=hero.passives.@id=sword_followup.tiers.@id=1` 等全部被动追击（`追い打ちの剣` / `竜殺しの宿命` / `溢れる慈愛` / `光輪の加護` / `見切り反撃`）**
   - 这些被动在 `class_progression` 中的追击字典（`hit_followup`、`weakness_followup`、`round_attack`、`counter_attack`）均未设置 `"name"` 字段；而 `host/combat.py` 的 `_passive_attack` 在调用 `_resolve_attack` 时也未传入 `display_name`。这会导致战斗日志中所有被动追击（除ハードコード了 `溢れる慈愛` 吗？不，`溢れる慈愛` 在 `combat.py:609` 传了 `"name": "溢れる慈愛"`，但其余 4 个被动均未传 `name`）在日志里都会显示为 **`「攻撃が…にXダメージ」`** 而不是被动名称。建议工程在合入文案时给这 4 个追击字典补上 `"name"`。
3. **`class_progression.@id=cleric.actives.@id=7.skill`（`セラフィムの福音`）**
   - `skills-v2.md` §2.1 正文写发动时当前 HP「默认：不提高（只扩容）」，文末「用户决定 1」改为「发动时 HP 上限提高，同时回复与提高量相等的 HP」。代码与 `status_defs.@id=gospel` 已按「用户决定 1」实现，说明文案按实际代码撰写。
4. **`class_progression.@id=cleric.passives.@id=holy_halo.tiers.@id=1.effects.round_attack`（`光輪の加護`）**
   - `skills-v2.md` §2.2 表格原缺 Lv6 选项 B，文末「用户决定 2」补入概念；`050` §8 参数表初稿写 `HALO_DAMAGE = 1d3`，文末「设计负责人决定 Q1」定为 `hp_ratio_gt: 0.7`、`damage: "1d3+wis/8"`、`target: "random_enemy"`。JSON 与代码已按 Q1 决定实现。
5. **`class_progression.@id=cleric.passives.@id=immortal_sanctuary.tiers.@id=1.effects`（`不滅の聖域`）**
   - `skills-v2.md` §2.2 正文写「每回合第一次施放 治癒の祈り 不消耗 MP…建议每场最多 3 次」，文末「用户决定 6」改为「基础治疗的 MP 消耗为 0，不设每场次数上限；仍然占用行动」。代码实现为 `free_skills: ["healing_prayer"]`（始终 0 MP），说明文案已按实际代码撰写。
6. **`class_progression.@id=mage.passives.@id=element_resonance.tiers.@id=1.effects.resonance`（`元素共鳴`）**
   - `skills-v2.md` §3.4 写「本次攻击法术的元素和本场上一次攻击法术的元素不同时」。在 `host/combat.py:586` 中，元素比较使用的是列表 `elements = ability.get("multi_elements") or [ability.get("element")]`。因此双属性法术 `氷炎の双嵐`（`["fire", "ice"]`）与单属性 `火球`（`["fire"]`）或 `氷の矢`（`["ice"]`）互相切换时，均会被判定为「属性不同」并触发共鸣。
7. **`class_progression.@id=thief.actives.@id=7.skill`（`神速の影分身`）**
   - `skills-v2.md` §4.1 写「持续 3 回合…结束后 cooldown: 3」。在 JSON 中配置为 `"cooldown": 5`：因为 `combat.py` 从施放后的下一回合末开始每回合扣减冷却，施放回合 `r` 加上 `r+1, r+2` 共 3 回合处于 `神速` 状态，`r+3, r+4, r+5` 共 3 回合处于冷却，到 `r+6` 可再次使用，实际体感与设计文档一致。同样残留了冗余字段 `"cost": 0, "cost_type": "mp"`。
8. **`class_progression.@id=thief.actives.@id=5.skill` + `class_progression.@id=thief.passives.@id=poison_craft.tiers.@id=1..2`（`刃の乱舞` 与 `毒使いの技` 叠加问题）**
   - `刃の乱舞` 自身带有 `on_hit_status: {"id": "poison", "stacks": 1}`（在 `_resolve_attack` 命中时赋予 1 层毒），而被动 `毒使いの技` 在 `_passive_hit` 中对所有命中的普攻和攻击技能再赋予 1 层毒。两者在 `host/combat.py` 中没有互斥，导致习得 `毒使いの技` 后使用 `刃の乱舞` 命中敌人会**一次叠 2 层毒**。若设计意图是单次命中只叠 1 层（或保持 2 层作为联动奖励），可在验收时留意。