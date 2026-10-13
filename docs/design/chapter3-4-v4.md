# 剧本 v4：第 3 章（炎上する村）与第 4 章（竜の谷）的地图化、Xanxus 的后续（设计负责人，2026-10-12）

原则沿用 `scenario-v2.md` 第 0 节和 `forest-v3.md`。日语正文**逐字使用**。

---

## 1. 第 3 章：设定修正与地图

### 1.1 设定修正
「麓の村」（`village`）目前的描述是"静かな村"，和村子已经烧成一片火海相矛盾。改为**村外的避难所**：
- title：麓の村・避難所
- description：村外れの石造りの集会所に、焼け出された村人たちが身を寄せ合っている。長老が人々を励まし、行商人の荷車の周りには小さな人だかりができている。
- 背景沿用 `bg_village.png`。
- 新增付费休息 `rest_at_refuge`「避難所で休ませてもらう（5G）」｜gold ≥ 5｜-5G，HP/MP/SP 全回复｜结果文：村人が分けてくれた粥をすすり、毛布にくるまって眠った。

### 1.2 第 3 章地图 `burning_village`
```
V1 村の入口 → V2 燃える大通り ──→ V3 炎の中の結氷（枢纽）─┬→ V4 凍結した路地 → V5 氷霜の巨狼 → V6 砕けた氷の太刀
                                                          ├→ V7 燃える街道（Xanxus）
                                                          └→ V8 避難所 ──→ 竜の谷へ
```
| 节点 | 地点 | 种类 |
|---|---|---|
| V1 | `village_approach` | start |
| V2 | `village_fire_slime`、`village_fire_elemental`、`burning_house`（新） | battle |
| V3 | `village_frozen_clue` | event |
| V4 | `ice_elemental_encounter` | battle |
| V5 | `frost_wolf_battle` | boss |
| V6 | `ian_ice_katana_aftermath` | event |
| V7 | `xanxus_confrontation`、`xanxus_battle`、`xanxus_ultimatum`、`warlock_rescue_battle` | event |
| V8 | `village` | rest |
- 现有的跳转保持不变，只补地图数据。V6 和 V8 都能前往竜の谷（现有动作）。V3 和 V8 之间可以往返（现有的 `visit_village` / `return_frozen_clue`）。

### 1.3 新支线 5：「燃える家の子ども」（路上的判定触发，奖励在避难所领取）
- V2 的战斗胜利之后（火史莱姆或火之精灵，任意一个），不再直接前往 V3，而是先到新地点 `burning_house`。
- **`burning_house`「燃える民家の前」**
  - description：崩れかけた民家の奥から、子どもの泣き声が聞こえる。入口は燃える梁で塞がれている。
  - 动作（任意一个成功即可救出，flag `riku_rescued` → V3）：
    - `break_burning_beam`「燃える梁を叩き壊す」｜1d20+str，DC13｜失败 HP -5，可以重试
      - 成功：梁を蹴り砕いて飛び込むと、煙の中で小さな男の子がうずくまっていた。
      - 失败：梁は思ったより重く、熱に腕を焼かれた。
    - `climb_to_window`「裏手の窓からよじ登る」｜1d20+dex，DC13｜失败 HP -3，可以重试
      - 成功：壁をよじ登って窓から入り込み、男の子を抱えて外へ飛び降りた。
      - 失败：足を滑らせ、焼けた壁にしたたかに打ちつけた。
    - `douse_with_ice`「冷気で炎を鎮める」｜条件：持有氷の護符、氷の護符(活性化済)、氷鉄の大剣、氷の太刀、氷の結晶中的任一件，或者职业是魔法使｜判定不要
      - 结果文：冷気を放つと炎が一瞬で退き、その隙に男の子を連れ出した。
    - `leave_burning_house`「先を急ぐ」→ V3，flag `riku_abandoned`｜结果文：泣き声を背に、燃える通りを駆け抜けた。
  - 观察对象 `house_beam`（燃える梁）：判定不要，文：梁の根元が焼け落ちかけている。力を込めれば折れそうだ。（作为提示，不发放东西）
- 新 NPC `riku`：長老の孫リク｜村の長老の孫。火事の夜、家に取り残されていた。
- **在避难所领取奖励**：持有 `riku_rescued` 时，V8 出现 `return_riku`「リクを長老に会わせる」｜once
  - 结果文：「リク！……よく無事で」長老は孫を抱きしめ、深く頭を下げた。「礼をさせてくれ。これは村に伝わる竜の秘薬じゃ。それと……この話も伝えておこう。昔、白き竜がこの村に霜を降らせたことがある、と」
  - 奖励：`dragon_elixir`（竜の秘薬，新物品）×2，flag `heard_treaty_lore`（scenario-v2 3.5 的线索 flag，新增一个来源）
- 放弃了的情况：V8 的长老描述追加一句「長老は焼け跡を見つめ、黙り込んでいる」（只是叙述，不会让玩家无法推进）。
- 任务：「燃える家の子ども」｜描述：燃える民家に子どもが取り残されている。｜start：到达 `burning_house`（flag `found_burning_house`）｜阶段：「子どもを助け出す」（done `riku_rescued`）→「避難所の長老のもとへ連れて行く」｜complete `riku_returned`；fail `riku_abandoned`

### 1.4 新物品
| id | name | description | effect | category |
|---|---|---|---|---|
| `dragon_elixir` | 竜の秘薬 | 村に代々伝わる秘薬。竜の鱗を煎じたものだという。 | HP を最大値の 50% 回復（消耗品，战斗内外都可以用） | consumable |

---

## 2. 第 4 章：竜の谷的地下城化

### 2.1 地图 `dragon_valley`
```
D1 谷の入口 → D2 溶岩の吊り橋 ─┬→ D3 竜の巣の前 → D4 竜の巣（イグニス）
                └→ D2b 岩棚の迂回路 ─┘
```
| 节点 | 地点 | 种类 |
|---|---|---|
| D1 | `valley_entrance`（新） | battle |
| D2 | `valley_lava_bridge`（新） | event |
| D2b | `valley_ledge`（新） | battle |
| D3 | `valley_nest_gate`（新） | event |
| D4 | `dragon_valley_loc`、`ignis_last_breath`、`ignis_purified` | boss |
- 现在所有通往 `dragon_valley_loc` 的动作，改为通往 `valley_entrance`。flag `entered_dragon_valley` 改在进入 D1 时设置，Lv5 的里程碑随之移到 D1。

### 2.2 节点正文
**D1 `valley_entrance`「竜の谷・入口」**
- description：硫黄の霧が立ち込める谷の入口。霧の中で、煤をまとった人影がゆらゆらと揺れている。
- 敌人：煤の亡霊 ×2（新）
- 动作：战斗；「霧に紛れてやり過ごす」（1d20+dex，DC14，成功 → D2，失败 → 开战，敌人先手）
- 胜利 → D2

**D2 `valley_lava_bridge`「溶岩の吊り橋」**
- description：煮え立つ溶岩の川に、古い吊り橋が一本だけ架かっている。板は焦げ、縄は今にも切れそうだ。
- 动作：
  - `cross_lava_bridge`「吊り橋を渡る」｜1d20+dex，DC12｜成功 → D3；失败：HP -6，仍然到达 D3。成功文：揺れる板を一枚ずつ踏みしめ、向こう岸へたどり着いた。失败文：板が一枚抜け落ち、熱風に焼かれながら必死にしがみついて渡りきった。
  - `take_ledge_path`「岩棚の迂回路を進む」→ D2b
- 观察对象 `bridge_ropes`（焦げた縄）：1d20+wis，DC10，成功文：右側の縄はまだしっかりしている。右端を伝えば安全に渡れそうだ。→ flag `bridge_safe_side_known`；之后 `cross_lava_bridge` 的 DC 变成 6。

**D2b `valley_ledge`「岩棚の迂回路」**
- description：溶岩の川を見下ろす狭い岩棚。岩陰から、翼の生えた小型の竜が首をもたげた。
- 敌人：溶岩ドレイク ×2（新）
- 胜利 → D3（不走吊桥，用战斗代替判定）

**D3 `valley_nest_gate`「竜の巣の前」**
- description：巨大な洞穴の入口から、灼熱の風が吹きつけてくる。奥で、何か巨大なものが重く息をしている。
- 动作：「竜の巣へ踏み込む」→ D4（イグニス战）。另外根据条件发生下面的 Xanxus 事件。

### 2.3 Xanxus 的后续：火种的诅咒
**触发**：持有 `accepted_fire_seed`（在 Xanxus 那里接受了火种）的玩家第一次到达 D3 时，先进入新地点 `xanxus_at_nest`。
- **`xanxus_at_nest`「竜の巣の前・Xanxus」**
  - description：炎の中からXanxusが現れた。あなたの胸の火種が、呼応するように熱を帯びる。「よく来た。紅竜を倒したら、その心臓を我に捧げよ。火種を持つ限り、お前は我に逆らえぬ」
  - 动作（选一个）：
    - `obey_xanxus_core`「従う」｜flag `promised_core_to_xanxus` → D3。结果文：Xanxusは満足げに笑い、炎とともに消えた。
      - 后续：イグニス战胜利后进入 `ignis_last_breath` 时，紅竜の炎核**被 Xanxus 夺走**（不放进背包），追加一段文字：「約束の品はもらっていくぞ」Xanxusの声とともに、紅竜の心臓の炎が宙へ吸い上げられていった。flag `xanxus_took_core`。白竜战需要别的火属性手段（来源见 scenario-v2 3.6，不受影响）。
      - 净化路线：イグニス被净化时没有心脏可以给，Xanxus 不出现（结果文：遠くで、Xanxusの怒りに満ちた咆哮が聞こえた）。
    - `cleanse_fire_seed`「聖なる力で火種を浄化する」｜条件：持有聖水，或者职业是僧侣（MP 6）｜→ 战斗 `xanxus_phantom_battle`
      - 结果文：聖なる光が胸の火種を焼き払った。Xanxusが怒りに吠える。「小癪な……ならば力ずくで奪うまでだ！」
    - `call_warlock`「ワーロックの名を呼ぶ」｜条件：`warlock_rescue_triggered`（之前在村里被ワーロック救过）｜→ D3，flag `fire_seed_removed`、`heard_xanxus_betrayal`
      - 结果文：青い光が走り、ワーロックがあなたの前に立った。彼の杖が火種を凍らせて砕く。「Xanxus、もう白竜の手先は終わりだ」Xanxusは舌打ちし、炎の中へ消えた。ワーロックは振り返る。「あの骸骨は、白竜と密約を交わしていた。紅竜の心臓と引き換えに、王国の半分をもらう約束だったそうだ」
- **`xanxus_phantom_battle`「Xanxusの分身」**（新敌人，boss，`flee_allowed: false`）
  - description：Xanxusが自らの炎を分けて作り出した分身。本体ほどの力はない。
  - 胜利：flag `fire_seed_removed`、`heard_xanxus_betrayal`，背包里的火种被移除 → D3。结果文：分身が崩れ落ちる間際、Xanxusの声が響いた。「白竜め……約束が違うではないか……」
  - 败北：HP 1，回到 D3，火种保持不变，仍然受 `obey_xanxus_core` 的约束（视为已承诺）。败北文：炎に呑まれ、気がつくと巣の前に倒れていた。胸の火種は、まだ脈打っている。
- `heard_xanxus_betrayal` 加入 scenario-v2 3.5 的线索 flag 列表。
- **没有接受火种、但曾被ワーロック救过的玩家**：第一次到达 D3 时，ワーロック短暂现身（`warlock_at_nest` 事件，只有文字，自动设置 `heard_xanxus_betrayal`）。文：青い光とともにワーロックが現れた。「先へ進む前に伝えておく。Xanxusは白竜と密約を交わしていた。紅竜の心臓と引き換えに、王国の半分をもらう約束だったそうだ。……気をつけろ」そう言い残し、彼は再び姿を消した。
- 任务：「火種の呪い」｜描述：Xanxusに植え付けられた火種が、胸の中で脈打っている。｜start `accepted_fire_seed`｜阶段：「火種を取り除く方法を探す」｜complete `fire_seed_removed`；fail `xanxus_took_core`

### 2.4 新敌人（名字、说明、技能名照此；数值由工程设定）
| id | name | description | 特征 | 技能 |
|---|---|---|---|---|
| `ash_wraith` | 煤の亡霊 | 竜の炎に焼かれた者たちの怨念が、煤となって漂う亡霊。 | dark/fire；holy 弱点；物理抗性 0.5 | 「煤の抱擁」（附带"窒息"：每回合少量伤害）、「怨嗟」 |
| `lava_drake` | 溶岩ドレイク | 竜の谷に棲む小型の竜。イグニスの眷属とされる。 | fire；ice 弱点；闪避中等 | 「溶岩の吐息」（火属性）、「鉤爪」 |
| `xanxus_phantom` | Xanxusの分身 | Xanxusが自らの炎を分けて作り出した分身。 | fire；ice/holy 弱点 | 「火炎旋渦」「隕石召喚」（沿用本体的技能名，伤害比本体低得多） |

---

## 3. 数值目标
- D1、D2b：elite（多敌人）。`xanxus_phantom_battle`：boss，Lv5 下胜率 [0.60, 0.75]。
- 加了 D1/D2 以后，イグニス战之前的消耗增加。避难所的付费休息（5G）是有意给出的应对手段。不要为了维持原来的通关率，去削弱イグニス本身。
- 主线连续通关率按 017 的新目标判定（[0.55, 0.90]；完成可选内容的路线最高 0.95）。

## 4. 美术需求（第 1–2 节实现以后再生成）
| 文件 | 内容 |
|---|---|
| `enemy_ash_wraith.png` | 煤の亡霊：由煤灰和余烬构成的人形怨灵，脸部是空洞，身体下半消散成烟 |
| `enemy_lava_drake.png` | 溶岩ドレイク：イグニス的小型眷属，红黑熔岩鳞，四肢加翼，体型如马 |
| `enemy_xanxus_phantom.png` | Xanxusの分身：以 `npc_xanxus.png` 为参考，半透明的火焰质感分身 |
| `npc_riku.png` | 長老の孫リク：七八岁的男孩，脸上有煤灰，抱着长老给的护身符 |
| `bg_lava_bridge.png` | 熔岩河上的破旧吊桥 |
| `bg_dragon_nest.png` | 竜の巣の入口：巨大的洞穴，灼热的风，骸骨和财宝散落 |
| `bg_burning_house.png` | 燃烧中的民家，入口被燃烧的梁堵住 |
| `bg_hot_spring.png` | 地底の温泉（forest-v3 遗留：现在暂用水晶洞窟背景） |
