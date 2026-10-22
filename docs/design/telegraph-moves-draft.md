# 052b 百分比招式与蓄力预告内容（草案，供 052b 使用）

来源：Antigravity argon medium（`.agy-runs/telegraph-draft.md`，dispatch 试用七），设计负责人审阅。

## 审阅结论（优先于下面的表）

- **"附带状态"一列作废**：表里的「凍傷」「出血」「盲目」「防御低下」「攻撃低下」不是 v2 状态（v2 只有 burn、poison、weaken、paralysis、stun、blind 等，见 `status_defs`），054 spec 里也没有这些写法。"054 指定"的说法是 argon 编的。附带状态一律以 `docs/specs/054-enemy-status-hazards-items.md` 第 1.2 节为准。
- 可以采用的：招式名、预告文、放出描述、建议比例和触发方式。比例和触发方式是 proposed，052b 用模拟定最终值。
- **已有单一技能的精英**：用"沿用"方案，把现有技能改成百分比招式，`ai_weight` 约 1/3，054 的状态仍挂在这个技能上。不新增第二个技能。
- **豁免**（不加百分比招式）：goblin、goblin_archer、sapphire_moth、emerald_spider、stone_lizard、fire_wisp、wraith。
- `goblin_fort_first_second` 实际是两个杂兵，在基础包里把 `encounter_class` 改为 `trash`。非数值改动；baby 的 EXP 走里程碑，不受影响。052b 核实 baby 金标不变。
- **xanxus 本体不加预告大招**（它出现在 scripted_loss、guest、NPC 战里），只给 `xanxus_phantom` 加。
- **draco_human**：保留「氷華一閃」作普通技能（改为 `ai_weight`），另加预告大招「白銀の秘太刀」。049 分支 B 的「簒奪の聖光斬」照旧追加。
- **every_n_rounds 撞车**：war_hound、slime_king、grave_knight、earth_worm 这 4 个已经有 054 的 `every_n_rounds: 3` 技能，052b 招式改用 `ai_weight`。
- **数据一致性**（052b 处理）：
  - 用 `encounter_class` 统一判定 Boss：`dragon_valley_loc` 和 `xanxus_phantom_battle` 漏了 `boss: true`；
  - `oaksdawn_wall` 动态生成的竜騎士战、`next_phase` 刷出的二阶段敌人都要继承 boss 级别；
  - `npc_combat` 遭遇没有 `encounter_class` 的，沿用 050 的覆盖规则（通常是 elite）。
- Ignis 二阶段狂暴招「狂乱の劫火」（HP 40% 以下）作为 proposed，是否加由 052b 按 B2 赛跑结果决定。

### 1. Elite 百分比招与 Boss 预告大招草案表

> **说明**：
> - 凡沿用现有技能名改造为百分比/预告大招的条目，在招式名后标注了 `（沿用）`；若原技能名不足 4 字（如 `氷槌`、`地砕き`、`炎の息`），同时给出了 4–10 字的备选名。
> - 对于本就有 1 个常规技能的 `elite`（或想保留原技能作常规招的 `boss`），表后附注或括号中也提供了不重名的新招式名，方便在「直接把现有技能改为百分比/预告招」与「保留原技能、额外新增一招」两种实现方案间切换。
> - 被认为**不适合**加百分比招的 `elite` 同场副怪/杂兵（见第 2 节）也在表末列出了备选方案，以便全表覆盖无遗漏。

| 敌人 id | 名称 | 类别 | 招式名（4–10 字） | 类型（百分比 / 预告大招） | 建议比例（区间内） | 建议触发（ai_weight 约 1/3 或 every_n_rounds: 3） | 附带状态（只有 spec 允许的才写） | 预告文（仅预告大招，20–40 字，{enemy} 代替敌人名，要让玩家知道下回合该防御） | 放出描述（15–40 字，{enemy}） |
|---|---|---|---|---|---|---|---|---|---|
| `forest_wolf` | 森狼 | `elite` | `喉笛喰らい` | 百分比 | `15%` (`0.15`) | `ai_weight` 约 1/3 | なし（054 的 `出血` 挂普攻） | — | `{enemy}は低く身を沈め、鋭い牙で急所へ飛びかかった！` |
| `hobgoblin` | 大ゴブリン | `elite` | `脳天砕き`（沿用 054 草案） | 百分比 | `20%` (`0.20`) | `ai_weight` 约 1/3 | `気絶`（50%・1T，054 `★`） | — | `{enemy}は大棍棒を大きく振りかぶり、渾身の力で叩きつけた。` |
| `war_hound` | 猛犬 | `elite` | `猛り噛み砕き` | 百分比 | `18%` (`0.18`) | `ai_weight` 约 1/3（避开 054 的 `every_n_rounds: 3`） | なし（054 的 `出血` 挂普攻、`攻撃低下` 挂 `威嚇の遠吠え`） | — | `{enemy}は荒々しく唸り、顎を大きく開いて飛びかかった！` |
| `fire_elemental` | 火の精霊 | `elite` | `爆炎の奔流` | 百分比 | `20%` (`0.20`) | `ai_weight` 约 1/3 | `火傷`（50%・2T，若 054 未挂普攻则挂此招；已挂普攻则なし） | — | `{enemy}の核が激しく脈打ち、灼熱の炎が渦を巻いて噴き出した！` |
| `ice_elemental` | 氷の精霊 | `elite` | `凍てつく息`（沿用；新增可用 `絶対零度の波動`） | 百分比 | `20%` (`0.20`) | `ai_weight` 约 1/3 | `凍傷`（45%・2T，沿用时按 054 挂载；新增独立招则なし） | — | `{enemy}が冷たい息を吐き出し、周囲の空気を凍らせた。` |
| `heat_lizard` | 熱岩トカゲ | `elite` | `火炎吐き`（沿用；新增可用 `灼熱の体当たり`） | 百分比 | `18%` (`0.18`) | `ai_weight` 约 1/3 | `火傷`（45%・2T，沿用时按 054 挂载；新增独立招则なし） | — | `{enemy}が喉を膨らませ、火の玉を吐き出した。` |
| `fire_wisp` | 炎のウィスプ | `elite`（建议豁免，见§2） | `火の粉散らし`（沿用；新增可用 `閃熱の炸裂`） | 百分比 | `15%` (`0.15`) | `ai_weight` 约 1/3 | `火傷`（35%・2T，沿用时按 054 挂载） | — | `{enemy}がくるりと回り、熱い火の粉をまき散らした。` |
| `ruby_golem` | 紅晶ゴーレム | `elite` | `紅晶砕き`（沿用） | 百分比 | `22%` (`0.22`) | `ai_weight` 约 1/3 | なし | — | `{enemy}が結晶の拳を振り上げ、床ごと叩き潰した。` |
| `sapphire_moth` | 蒼晶の蝶 | `elite`（伴随怪，建议豁免） | `蒼鱗の粉`（沿用；新增可用 `蒼光の鱗嵐`） | 百分比 | `15%` (`0.15`) | `ai_weight` 约 1/3 | `盲目`（45%・2T，沿用时按 054 挂载） | — | `{enemy}が羽ばたき、冷たく光る鱗粉を散らした。` |
| `emerald_spider` | 翠晶の蜘蛛 | `elite`（伴随怪，建议豁免） | `翠晶の糸`（沿用；新增可用 `翠毒の牙撃`） | 百分比 | `15%` (`0.15`) | `ai_weight` 约 1/3 | `毒`（45%・3T，沿用时按 054 挂载） | — | `{enemy}が鋭く光る結晶の糸を吐きつけた。` |
| `ash_wraith` | 煤の亡霊 | `elite` | `灰の抱擁`（沿用；新增可用 `黒煤の窒息波`） | 百分比 | `18%` (`0.18`) | `ai_weight` 约 1/3 | `盲目`（50%・2T，沿用时按 054 挂载） | — | `{enemy}が煤の腕を広げ、視界ごと包み込むように迫った。` |
| `lava_drake` | 溶岩ドレイク | `elite` | `溶岩の牙`（沿用；新增可用 `噴火の尾撃`） | 百分比 | `20%` (`0.20`) | `ai_weight` 约 1/3 | `火傷`（50%・2T，沿用时按 054 挂载） | — | `{enemy}の牙から赤黒い溶岩が滴り、噛み砕くように迫った。` |
| `ice_sentinel` | 氷の番兵 | `elite` | `凍てつく大槌`（或沿用 2 字原名 `氷槌`） | 百分比 | `20%` (`0.20`) | `ai_weight` 约 1/3 | `気絶`（50%・1T，054 `★`） | — | `{enemy}は凍りついた大槌を高く掲げ、床ごと叩き潰した！`（原句：`{enemy}は凍りついた大槌を振り下ろした！`） |
| `ice_assassin` | 氷の刺客 | `elite` | `氷刃の連撃`（沿用；新增可用 `氷影の急所突き`） | 百分比 | `20%` (`0.20`) | `ai_weight` 约 1/3 | `凍傷`（45%・2T，沿用时按 054 挂载） | — | `{enemy}は白い息とともに踏み込み、凍る刃を続けざまに振るった！` |
| `ghoul` | 屍鬼 | `elite` | `腐肉の爪`（沿用；新增可用 `屍喰らいの顎`） | 百分比 | `20%` (`0.20`) | `ai_weight` 约 1/3 | `毒`（50%・3T，沿用时按 054 挂载） | — | `{enemy}が黒ずんだ爪を振り回し、腐臭とともに飛びかかった。` |
| `wraith` | 怨霊 | `elite`（伴随怪，见§2） | `嘆きの冷気`（沿用；新增可用 `怨念の凍気`） | 百分比 | `15%` (`0.15`) | `ai_weight` 约 1/3 | `凍傷`（50%・2T，沿用时按 054 挂载） | — | `{enemy}が声なき悲鳴を上げ、骨まで凍る冷気を浴びせた。` |
| `rock_giant` | 岩の巨人 | `elite` | `岩砕きの剛腕`（沿用 054 草案） | 百分比 | `25%` (`0.25`) | `ai_weight` 约 1/3 | `気絶`（50%・1T，054 `★`） | — | `{enemy}は岩の剛腕を振り上げ、大地ごと叩き潰した。` |
| `stone_lizard` | 石肌トカゲ | `elite`（伴随怪，建议豁免） | `石鱗の尾撃` | 百分比 | `15%` (`0.15`) | `ai_weight` 约 1/3 | なし（054 的 `出血` 挂普攻） | — | `{enemy}は硬い石肌の尾をしならせ、足元を強く薙ぎ払った！` |
| `zebok` | 亡霊主宰ゼボク | `boss` | `冥府の呪言` | 预告大招 | `35%` (`0.35`) | `every_n_rounds: 3` | なし（054 的 `防御低下` 挂 `死の呪い`） | `{enemy}が骨の杖を高く掲げると、黒い瘴気が渦を巻いて収束していく……！` | `{enemy}が呪言を放ち、凝縮された死の奔流が襲いかかった！` |
| `slime_king` | スライム王 | `boss` | `大王の巨体潰し` | 预告大招 | `30%` (`0.30`) | `ai_weight` 约 1/3（避开 054 `腐食の粘液` 的 `every_n_rounds: 3`） | なし（054 的 `防御低下` 挂 `腐食の粘液`） | `{enemy}の巨体が大きく膨れ上がり、天井すれすれまで跳び上がった……！` | `{enemy}が全体重を乗せて落下し、地面ごと押し潰した！` |
| `goblin_king` | ゴブリン王 | `boss` | `王の大断ち`（沿用） | 预告大招 | `35%` (`0.35`) | `every_n_rounds: 3` | なし | `{enemy}が錆びた大剣を両手で高く振りかぶり、全身に力を込めた……！` | `{enemy}が大剣を両手で振りかぶり、床ごと叩き割った。` |
| `grave_knight` | 墓守の騎士 | `boss` | `墓守の大断ち`（沿用） | 预告大招 | `35%` (`0.35`) | `ai_weight` 约 1/3（避开 054 `呪縛の剣` 的 `every_n_rounds: 3`） | なし（054 的 `出血` 挂普攻、`攻撃低下` 挂 `呪縛の剣`） | `{enemy}の兜に蒼い冥火が灯り、大剣を上段に大きく構え直した……！` | `{enemy}が両手で大剣を振り上げ、石床ごと断ち割った。` |
| `earth_worm` | 大ワーム | `boss` | `地砕きの崩落`（或沿用 3 字原名 `地砕き`） | 预告大招 | `35%` (`0.35`) | `ai_weight` 约 1/3（避开 054 `砂礫の噴射` 的 `every_n_rounds: 3`） | なし（054 的 `盲目` 挂 `砂礫の噴射`） | `{enemy}が巨体を大きく反らし、峡谷の岩盤が激しく軋み始めた……！` | `{enemy}が巨体をくねらせ、峡谷の底ごと叩き潰した。` |
| `prism_tree` | 虹晶樹 | `boss` | `極光の奔流`（或沿用 `虹光の枝`） | 预告大招 | `35%` (`0.35`) | `every_n_rounds: 3` | なし（若沿用 `虹光の枝` 则附带 054 的 `盲目` 60%・2T） | `{enemy}の幹の結晶が一斉に脈打ち、まばゆい七色の光が集まっていく……！` | `{enemy}の枝先から、七色の極光が奔流となって放たれた！` |
| `frost_dire_wolf` | 氷霜の巨狼 | `boss` | `吹雪の遠吠え`（沿用） | 预告大招 | `35%` (`0.35`) | `every_n_rounds: 3` | `凍傷`（65%・2T，054 指定） | `{enemy}が深く息を吸い込むと、周囲の空気が白く凍りつき始めた……！` | `{enemy}が天を仰いで吠えると、凍てつく吹雪が吹き荒れた。` |
| `xanxus` | 赤いローブの魔法使い・ザンザス | `boss` | `業火の審判` | 预告大招 | `40%` (`0.40`) | `every_n_rounds: 3` | なし（054 的 `火傷` 挂 `獄炎弾`、`攻撃低下` 挂 `炎の檻`） | `{enemy}が両腕を掲げると、周囲の炎が渦を巻いて一点に集まっていく……！` | `{enemy}が振り下ろした杖から、焼き尽くす業火の柱が噴き上がった！` |
| `xanxus_phantom` | ザンザスの分身 | `boss` | `劫火の収束`（或沿用 `残火の連弾`） | 预告大招 | `35%` (`0.35`) | `every_n_rounds: 3` | なし（若沿用 `残火の連弾` 则附带 054 的 `火傷` 60%・2T） | `{enemy}の炎の輪郭が激しく燃え上がり、掌に巨大な火球が渦巻く……！` | `{enemy}が凝縮した劫火の球を解き放ち、爆炎が襲いかかった！` |
| `ignis` | 邪竜イグニス | `boss` | `炎の息`（沿用，052/054 指定；4字版 `紅蓮の息吹`） | 预告大招 | `40%` (`0.40`) | `every_n_rounds: 3` | `火傷`（100%・2T，054 指定） | `{enemy}が大きく顎を開き、喉の奥に灼熱の炎が渦巻いている……！` | `{enemy}は深く息を吸い込み、灼熱の炎を吐き出した！` |
| `dragon_knight_mounted` | 竜騎士ガレスと飛竜ノクス | `boss` | `急降下突撃`（沿用） | 预告大招 | `35%` (`0.35`) | `every_n_rounds: 3` | なし（054 的 `火傷` 挂 `灰竜の息`） | `{enemy}は翼を大きく広げて空高く舞い上がり、槍先をこちらへ向けた……！` | `{enemy}は空高く舞い上がり、槍先を揃えて急降下した！` |
| `dragon_knight_human` | 竜騎士ガレス | `boss` | `守護者の処断`（或沿用 `裁きの槍`） | 预告大招 | `35%` (`0.35`) | `every_n_rounds: 3` | なし（若沿用 `裁きの槍` 则附带 054 的 `出血` 55%・2T） | `{enemy}は槍を深く引き絞り、鋭い眼差しでただ一点を見据えた……！` | `{enemy}が大地を蹴って踏み込み、渾身の力で槍を突き出した！` |
| `draco_human` | 剣聖ドラコ | `boss` | `氷華一閃`（沿用；新增可用 `白銀の秘太刀`） | 预告大招 | `35%` (`0.35`) | `every_n_rounds: 3` | `凍傷`（60%・2T，054 指定） | `{enemy}が白銀の剣を鞘に納め、足元から凍てつく冷気が立ちのぼる……！` | `{enemy}の剣が白く閃き、凍てつく斬撃が走った！` |
| `draco_dragon` | 白竜ヴァイス | `boss` | `凍てつく吐息`（沿用） | 预告大招 | `45%` (`0.45`) | `every_n_rounds: 3` | `凍傷`（100%・2T，054 指定） | `{enemy}が深く息を吸い込み、喉の奥で白銀の冷気が渦巻いている……！` | `{enemy}は白い冷気を吸い込み、すべてを凍らせる吐息を放った！` |

> **附：`ignis` 的二阶段狂暴招备选（Spec 052 §3.4）**
> Spec 052 §3.4 提到给 `ignis`「加一个 HP 40% 以下才解锁的狂暴招（和第 4 章的净化阈值 40% 对齐）」。若工程录入时需要该技能的文本，建议：
> - 招式名：`狂乱の劫火`（5 字，`use_below_hp_ratio: 0.4`）
> - 放出描述：`{enemy}は凍てつく古傷の痛みに狂乱し、周囲一帯を紅蓮の炎で薙ぎ払った！`（除 `{enemy}` 外 31 字）

---

### 2. 不适合拥有百分比招的 `elite` 敌人及理由

在 `dragon_rpg.json` 中，`encounter_class` 是标在**遭遇（location.combat）**上的，而非敌人定义上。因此部分 `elite` 遭遇中包含了本质是杂兵、群怪或辅助副怪的敌人，建议**豁免**它们的百分比招式：

1. **`goblin`（ゴブリン）与 `goblin_archer`（ゴブリン弓兵）**（未列入上表正表）
   - **出现遭遇**：`goblin_fort_first_second`（`encounter_class: "elite"`，1 只 `goblin` + 1 只 `goblin_archer`）。
   - **不适合理由**：这两个敌人本质是第 1 章的基础杂兵（`trash`），同时还出现在 `goblin_fort`（`trash`）、`lost_goblin_crossroads`（`trash`）以及 `goblin_fort_fourth`（作为 `goblin_king` 的 Boss 战随从）。如果给 `goblin` 或 `goblin_archer` 的敌人定义加上百分比技能，会导致第 1 章所有哥布林杂兵战以及哥布林王 Boss 战里的小怪都轰出 15%–25% 最大 HP 伤害。`goblin_fort_first_second` 仅因双哨兵合流而被标为 `elite`（甚至没有精英果实掉落），不应因此把基础哥布林改成百分比怪。
2. **`sapphire_moth`（蒼晶の蝶）与 `emerald_spider`（翠晶の蜘蛛）**
   - **出现遭遇**：`cave_crystal_corridor`（`encounter_class: "elite"`，由 `ruby_golem` ×1 + `sapphire_moth` ×2 + `emerald_spider` ×1 共 **4 只敌人**组成）。
   - **不适合理由**：这场战斗真正的精英主怪是 `ruby_golem`（HP 34、ATK 5、DEF 3）。`sapphire_moth`（HP 14、ATK 2、DEF 0，撒鳞粉致盲）和 `emerald_spider`（HP 18、ATK 3、DEF 1，吐丝中毒）在设定和数值上都是脆弱的控制/骚扰型小虫。若 4 只同场怪全都有百分比招，玩家每回合都会被多段百分比伤害集火，既违背小虫的弱攻设定，也会让该场战斗压力失控。建议该遭遇仅由主怪 `ruby_golem` 持有百分比招 `紅晶砕き`。
3. **`stone_lizard`（石肌トカゲ）**
   - **出现遭遇**：`gorge_giant_path`（`encounter_class: "elite"`，由 `rock_giant` ×1 + `stone_lizard` ×1 组成）。
   - **不适合理由**：该遭遇的真正精英是 `rock_giant`（HP 44，且持有 25% 百分比 + 50% `気絶` 的重击 `岩砕きの剛腕`）。`stone_lizard` 只是巨人脚边伴随的普通蜥蜴（叙事：「足元では、石肌のトカゲが舌を鳴らしている」），Spec 054 也只给它分配了普攻 `出血`，不应再拥有百分比大招。
4. **`fire_wisp`（炎のウィスプ）**
   - **出现遭遇**：`cave_lava_room`（`encounter_class: "elite"`，`fire_wisp` ×3 同场）。
   - **不适合理由**：设定上是漂浮的小火球（HP 16、ATK 3、DEF 0），依靠 3 只群聚构成威胁，且 Spec 054 已给 `火の粉散らし` 挂了 `火傷`。3 只小火球轮流轰出最大生命值百分比重击在表现力和机制上都不协调，建议维持固定骰子伤害 + `火傷`。
5. **`wraith`（怨霊）**（视数值测试结果可豁免）
   - **出现遭遇**：`ghoul_marsh`（`encounter_class: "elite"`，玩家未持有诅咒物品时为 `ghoul` ×1 + `wraith` ×1 同场，且该遭遇禁用了ワーロック的同行治疗 `disable_companion_healing: ["blue_robed_mage"]`）。
   - **不适合理由**：`ghoul` 是该遭遇的常驻主怪，而 `wraith` 是未持诅咒物时的额外惩罚加怪。在禁用同行治疗的前提下，若 `ghoul`（带毒）与 `wraith`（带冻伤）同时具备百分比伤害，双怪同场的容错率会偏低；建议仅让主怪 `ghoul` 改为百分比招，`wraith` 保持常规伤害 + `凍傷`。

---

### 3. 补充说明：最没把握的敌人 & 剧本数据与 Spec 的不一致点

#### （1）最没把握的几个敌人

1. **`xanxus`（赤いローブの魔法使い・ザンザス）**
   - `xanxus` 在剧本中共用于三类战斗：
     - `xanxus_battle`（第 3 章初见，`encounter_class: "scripted_loss"`，必败战，HP 9999、ATK 55）；
     - `warlock_rescue_battle`（ワーロック救出战，`encounter_class: "guest"`，通过 `encounter_modifiers` 将 HP 乘 0.05、攻击乘 0.25）；
     - NPC 自由开战（`xanxus.npc_combat`，在 `xanxus_confrontation` / `xanxus_ultimatum` / `xanxus_at_nest` 对峙时玩家主动攻击他，可正面击败拿成就）。
   - **纠结原因**：如果给 `xanxus` 本体加上 `every_n_rounds: 3` 的预告大招（蓄力 1 回合、造成 40% 最大 HP 伤害），在 `xanxus_battle`（必败战）中他原本靠 ATK 55 平 A 两三刀秒杀玩家，一旦触发蓄力预告反而会白白浪费 1 回合不攻击、下一回合也只打 40% HP，拖慢必败战节奏；而在 `warlock_rescue_battle`（`guest`）中，`encounter_modifiers` 的 `enemy_attack_multiplier: 0.25` 不会缩放 `damage_max_hp_ratio`。因此**不确定是否应该豁免 `xanxus` 本体的预告大招（只给 `xanxus_phantom` 预告大招），或者在 `scripted_loss` 下禁用其预告技能**。
2. **已有单一 `ai_weight: 1` 技能的 `elite`（如 `ice_elemental`、`heat_lizard`、`lava_drake`、`ice_assassin`、`ghoul` 等）是「沿用改造」还是「新增第 2 技能」**
   - 这些精英目前在 `dragon_rpg.json` 中都只有 1 个 `ai_weight: 1` 的技能，且 Spec 054 §1.2 都指定把异常状态挂在这个现有技能上。
   - 如果直接**沿用**现有技能改为百分比招（并降低触发率至约 1/3），则该精英每次放技能都是「百分比伤害 + 异常状态」二合一；如果是**保留原技能作为普通异常状态招，额外新增第 2 个技能作为纯百分比招**，则技能池更丰富但敌人 JSON 会有 2 个技能。我在表中同时给出了「沿用」与「新增」两套命名，具体取舍需设计负责人拍板。
3. **`draco_human`（剣聖ドラコ）的 `氷華一閃`**
   - 目前 `draco_human` 只有 `氷華一閃` 一个技能（`every_n_rounds: 2`），且 Spec 054 把 `凍傷`（60%・2T）挂在 `氷華一閃` 上。如果直接将 `氷華一閃` 改为 `every_n_rounds: 3` 的预告大招，那么他在非蓄力回合就只剩普攻 `白銀の剣`；若希望他在普通回合也能放冰属性剑技，则需要保留 `氷華一閃`（改为 `ai_weight`）并采用表中的新招名 `白銀の秘太刀` 作为预告大招。

#### （2）剧本数据（`dragon_rpg.json`）中漏标 `encounter_class` 或与 Spec 冲突的地方

1. **Spec 052 与 Spec 054 的 `every_n_rounds: 3` 触发器冲突（涉及 3 个 Boss + 1 个 Elite）**
   - 引擎在选择敌人技能时，会按 `skills` 列表顺序选取第一个满足条件的 `every_n_rounds` 技能。
   - Spec 054 §1.2 明确要求为 **`war_hound`**（`威嚇の遠吠え`）、**`slime_king`**（`腐食の粘液`）、**`grave_knight`**（`呪縛の剣`）、**`earth_worm`**（`砂礫の噴射`）各**新增一个 `every_n_rounds: 3` 的状态技能**。
   - 如果这 4 个敌人在 Spec 052b 中的百分比招 / Boss 预告大招也使用 `every_n_rounds: 3`，两个 `every_n_rounds: 3` 技能会在第 3、6、9 回合完全撞车，导致排在后面的技能永远放不出来！因此我在上表中将这 4 个敌人的 052b 招式全部建议为 **`ai_weight` 约 1/3**（或者将其中一个改为 `every_n_rounds: 4`）。
2. **`oaksdawn_wall` 的竜騎士ガレス战（含二阶段 `dragon_knight_human`）未走标准 `combat.encounter_class`**
   - 在 `dragon_valley_return` 中，`dragon_knight_mounted` 有完整的 `"boss": true, "encounter_class": "boss"`（单阶段）。
   - 但在 `oaksdawn_wall`（当玩家背负 `town_blood` 罪名与ガレス开战，唯一能触发二阶段 `next_phase: "dragon_knight_human"` 的路径）中，`location.combat.enemy_ids` 为空，战斗是通过 action 上的 `"dragon_knight": true` 特殊字段在后端动态生成的。工程在按 `encounter_class == "boss"` 做倍率/属性缩放时，需要确保这条特殊触发路径以及通过 `next_phase` 刷出的 `dragon_knight_human`（及 `draco_dragon`）也能正确继承 `"boss"` 级别的缩放。
3. **`npc_combat` 触发的战斗均无 `encounter_class` 字段**
   - 包括 `xanxus` 在 `xanxus_confrontation` / `xanxus_ultimatum` / `xanxus_at_nest` 的正面交锋，以及城镇强力 NPC（如 `npc_walter` 守護団長、`npc_liese` 聖騎士、`npc_warlock`、`npc_robin` 等），它们的 `npc_combat.encounter` 下都没有标 `encounter_class`。若 052b 缩放脚本按 `location.combat.encounter_class` 扫描，这些 `npc_combat` 专属敌人（`npc_*`）和 `xanxus` 的正面战会被漏掉或需要单独指定类别。
4. **`boss` 布尔字段与 `encounter_class: "boss"` 存在多处不一致**
   - `dragon_valley_loc.combat`（红龙 `ignis`）：标了 `"encounter_class": "boss"`，但 `combat` 对象上**漏标了 `"boss": true`**（仅在 `ignis` 敌人定义上有 `"boss": true`）。
   - `xanxus_phantom_battle.combat`（`xanxus_phantom`）：标了 `"encounter_class": "boss"`，但 `combat` 对象和 `xanxus_phantom` 敌人定义上**都没有 `"boss": true`**（若前端或逃跑/免疫逻辑读取 `boss` 布尔值，会导致分身不被识别为 Boss）。
   - `xanxus_battle` 与 `warlock_rescue_battle`：`combat` 上标了 `"boss": true`，但 `encounter_class` 分别是 `"scripted_loss"` 和 `"guest"`。
5. **`goblin_fort_first_second` 标了 `encounter_class: "elite"` 但实为双杂兵遭遇**
   - 如第 2 节所述，该地点是哥布林要塞一二层交界的双哨兵（`goblin` + `goblin_archer`），既无精英专属敌人，也无精英果实奖励（`one_time_reward`），却标了 `"encounter_class": "elite"`。如果 052b 脚本按 `encounter_class == "elite"` 自动拔高该场敌人的基础属性，会把全局的 `goblin` 和 `goblin_archer` 都当成精英放大，污染第 1 章的 `trash` 遭遇。建议将该地点的 `encounter_class` 改回 `"trash"`，或在缩放脚本中排除跨类别复用的 `trash` 敌人。