# 028 第 1–2 章首次到达选项可见性

覆盖 36 个地点 × 4 个职业；Base / Hybrid 的 actions、条件、entry_effects 已由同步测试核对。

## 方法与边界

- 在确定性引擎上广度优先搜索最少操作路线；开场 100G + 薬草不计操作，每个选项和整场胜利各计一步。只在第 1–2 章内行进。判定枚举所有可发生结果；战斗假定获胜，不消耗药品。这是剧情可达性路线，不是生存率或推荐攻略。
- 保留移动、开战，以及它们依赖的 flag / 道具的前置动作；不为无关对话、购物和装备优化绕路。等长路线按剧本选项顺序、骰面结果顺序取首条。状态按导航相关 flag、道具、同伴、战斗阻挡去重，因此报告提供一条最短导航见证，不穷举所有等长路线的可见性差异。
- 到达后立即使用 public session 同一套过滤和脱敏函数。列出所有可见子项；职业不匹配、secret、visible_after、hidden_after 隐藏的内容不列入玩家选项。战斗自动开始的地点改列 combat_actions 指令（按入场资源，未计算抢攻伤害）；不把战斗期间隐藏的探索卡片当成可见选项。
- 专名词典来自地点标题（含「・」分段）、地图 label、NPC name / aliases、道具 name。按文字子串扫描标题、preview、risk、不可选原因；重叠名称取最长。已到过的地点、到达时满足 npc_requirements 的 NPC、当前或曾持有的道具记作已遇到。只听说过但尚未到访/见到/持有，仍列待核对；未识别别称、同名和普通词可能漏报或误报。
- 自动列出的名称只是 TODO(design) 审查候选，导航目的地、承诺奖励、NPC 请求提到的物品可能合理。没有据此修改其他剧本内容。

## アルテリア王城 (`castle`)

职业：勇者 / 僧侶。最少 0 步。

路线：`@opening`。

| 可见标题 | 类别 |
|---|---|
| 国王に邪竜の詳しい話を聞く | 可选 |
| 将軍ドラコに助言を求める | 可选 |
| 侍従から旅の支給品を受け取る | 可选 |
| 城下町へ出る | 可选 |

待核对名称：

| 名称 | 类型 | 出现于选项 |
|---|---|---|
| 聖水 | 道具 | 侍従から旅の支給品を受け取る |
| 城下町 | 地点 | 城下町へ出る |

职业：魔法使い / 盗賊。最少 0 步。

路线：`@opening`。

| 可见标题 | 类别 |
|---|---|
| 国王に邪竜の詳しい話を聞く | 可选 |
| 将軍ドラコに助言を求める | 已知但不可选 |
| 侍従から旅の支給品を受け取る | 可选 |
| 城下町へ出る | 可选 |

待核对名称：

| 名称 | 类型 | 出现于选项 |
|---|---|---|
| 聖水 | 道具 | 侍従から旅の支給品を受け取る |
| 城下町 | 地点 | 城下町へ出る |

## アルテリア城下町 (`castle_town`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 1 步。

路线：`@opening → go_castle_town`。

| 可见标题 | 类别 |
|---|---|
| 鍛冶屋へ向かう | 可选 |
| 宿屋へ向かう | 可选 |
| 魔法店へ向かう | 可选 |
| 道具屋へ向かう | 可选 |
| 路地裏へ向かう | 可选 |
| 王城へ戻る | 可选 |
| 城門を出て闇の森へ向かう | 可选 |

待核对名称：

| 名称 | 类型 | 出现于选项 |
|---|---|---|
| 鍛冶屋 | 地点 | 鍛冶屋へ向かう |
| 宿屋 | 地点 | 宿屋へ向かう |
| 魔法店 | 地点 | 魔法店へ向かう |
| 道具屋 | 地点 | 道具屋へ向かう |
| 路地裏 | 地点 | 路地裏へ向かう |
| 闇の森 | 地点 | 城門を出て闇の森へ向かう |

## 王城の鍛冶屋 (`forge`)

职业：勇者。最少 2 步。

路线：`@opening → go_castle_town → go_forge`。

| 可见标题 | 类别 |
|---|---|
| 店に入る | 可选 |
| 邪竜を討つ方法を聞く | 可选 |
| 鍛冶師に剣を見せる | 可选 |
| 城下町に戻る | 可选 |
| ？？？ | 未知 |
| 浮かない顔をしているが？ | 可选 |
| ？？？ | 未知 |

词典内未发现尚未遇到的名称。

职业：僧侶 / 魔法使い / 盗賊。最少 2 步。

路线：`@opening → go_castle_town → go_forge`。

| 可见标题 | 类别 |
|---|---|
| 店に入る | 可选 |
| 邪竜を討つ方法を聞く | 可选 |
| ？？？ | 未知 |
| 城下町に戻る | 可选 |
| ？？？ | 未知 |
| 浮かない顔をしているが？ | 可选 |
| ？？？ | 未知 |

词典内未发现尚未遇到的名称。

## 王城の宿屋 (`inn`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 2 步。

路线：`@opening → go_castle_town → go_inn`。

| 可见标题 | 类别 |
|---|---|
| 宿で休む（10G） | 可选 |
| イアンと会話する | 可选 |
| イアンと会話する / 強力な氷属性武器の伝説について聞く | 可选 |
| イアンと会話する / 邪竜を倒すアドバイスを求める | 可选 |
| イアンと会話する / 竜と人の昔話を聞く | 可选 |
| ロビンと会話する | 可选 |
| ロビンと会話する / パーティに勧誘する | 可选 |
| ロビンと会話する / 噂話を聞く | 可选 |
| 城下町に戻る | 可选 |

词典内未发现尚未遇到的名称。

## 王城の魔法店 (`magic_shop`)

职业：勇者 / 魔法使い / 盗賊。最少 2 步。

路线：`@opening → go_castle_town → go_magic_shop`。

| 可见标题 | 类别 |
|---|---|
| 店に入る | 可选 |
| 邪竜についての噂を聞く | 可选 |
| パーティーへ招く | 可选 |
| 城下町に戻る | 可选 |
| ？？？ | 未知 |
| 最近変わったことは？ | 可选 |

待核对名称：

| 名称 | 类型 | 出现于选项 |
|---|---|---|
| ローブ | 道具 | 店に入る |

职业：僧侶。最少 2 步。

路线：`@opening → go_castle_town → go_magic_shop`。

| 可见标题 | 类别 |
|---|---|
| 店に入る | 可选 |
| 邪竜についての噂を聞く | 可选 |
| パーティーへ招く | 可选 |
| 城下町に戻る | 可选 |
| ？？？ | 未知 |
| 最近変わったことは？ | 可选 |

词典内未发现尚未遇到的名称。

## 王城の道具屋 (`item_shop`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 2 步。

路线：`@opening → go_castle_town → go_item_shop`。

| 可见标题 | 类别 |
|---|---|
| 店に入る | 可选 |
| ペットの火コウモリ竜を借りる | 可选 |
| 城下町に戻る | 可选 |
| 何か困っていることはある？ | 可选 |
| ？？？ | 未知 |

词典内未发现尚未遇到的名称。

## 王城の路地裏・昼 (`alley`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 2 步。

路线：`@opening → go_castle_town → go_alley`。

| 可见标题 | 类别 |
|---|---|
| 城下町に戻る | 可选 |

词典内未发现尚未遇到的名称。

## 王城の路地裏・夜 (`alley_night`)

职业：勇者。最少 6 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley`。

| 可见标题 | 类别 |
|---|---|
| 怪しい商人の取引を聞く | 可选 |
| 城下町に戻る | 可选 |
| 白い鱗を買う | 可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 6 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley`。

| 可见标题 | 类别 |
|---|---|
| 怪しい商人の取引を聞く | 可选 |
| 城下町に戻る | 可选 |
| 白い鱗を買う | 可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 6 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley`。

| 可见标题 | 类别 |
|---|---|
| 怪しい商人の取引を聞く | 可选 |
| 城下町に戻る | 可选 |
| 白い鱗を買う | 可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 6 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley`。

| 可见标题 | 类别 |
|---|---|
| 怪しい商人の取引を聞く | 可选 |
| 城下町に戻る | 可选 |
| 白い鱗を買う | 可选 |

词典内未发现尚未遇到的名称。

## 夜の路地・亡霊戦 (`merchant_battle`)

职业：勇者。最少 9 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley → hear_curse_offer_hero → accept_curse_offer_hero → betray_cursed_merchant`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 呪われた聖剣 | 可选 |
| 渾身斬り | 可选 |
| 神聖の庇護 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 9 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley → hear_curse_offer_cleric → accept_curse_offer_cleric → betray_cursed_merchant`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 呪われた聖杖 | 可选 |
| 治癒の祈り | 可选 |
| 聖なる守護 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 9 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley → hear_curse_offer_mage → accept_curse_offer_mage → betray_cursed_merchant`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 魔力弾 | 可选 |
| 火球 | 可选 |
| 氷の矢 | 可选 |
| 暗黒球 | 可选 |
| 亡霊召喚 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 9 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley → hear_curse_offer_thief → accept_curse_offer_thief → betray_cursed_merchant`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 呪われた短剣 | 可选 |
| 影隠れ | 可选 |
| 急所突き | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

## 静まり返った夜の路地 (`alley_after`)

职业：勇者。最少 9 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley → hear_curse_offer_hero → accept_curse_offer_hero → pay_curse_price_hero`。

| 可见标题 | 类别 |
|---|---|
| 城下町に戻る | 可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 9 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley → hear_curse_offer_cleric → accept_curse_offer_cleric → pay_curse_price_cleric`。

| 可见标题 | 类别 |
|---|---|
| 城下町に戻る | 可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 9 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley → hear_curse_offer_mage → accept_curse_offer_mage → pay_curse_price_mage`。

| 可见标题 | 类别 |
|---|---|
| 城下町に戻る | 可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 9 步。

路线：`@opening → go_castle_town → go_inn → ask_robin_rumor → return_castle_from_inn → go_alley → wait_for_night_in_alley → hear_curse_offer_thief → accept_curse_offer_thief → pay_curse_price_thief`。

| 可见标题 | 类别 |
|---|---|
| 城下町に戻る | 可选 |

词典内未发现尚未遇到的名称。

## 闇の森・入口 (`dark_forest_loc`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 2 步。

路线：`@opening → go_castle_town → go_dark_forest:success`。

| 可见标题 | 类别 |
|---|---|
| スライムと戦う | 可选 |

词典内未发现尚未遇到的名称。

## 迷い子の十字路 (`lost_goblin_crossroads`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 4 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory`。

| 可见标题 | 类别 |
|---|---|
| 箱を取り戻す手伝いを引き受ける | 可选 |
| 迷子のゴブリンを無視する | 可选 |
| 先へ進む | 可选 |
| 森の入口へ戻る | 可选 |
| ？？？ | 未知 |

词典内未发现尚未遇到的名称。

## 精霊の泉 (`elf_spring`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 5 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward`。

| 可见标题 | 类别 |
|---|---|
| 精霊の泉で休む | 可选 |
| 休まず先へ進む | 可选 |
| 泉の奥の岩壁を調べる | 可选 |
| 十字路へ戻る | 可选 |

待核对名称：

| 名称 | 类型 | 出现于选项 |
|---|---|---|
| 泉の奥 | 地点 | 泉の奥の岩壁を調べる |

## 闇の森・狼の縄張り (`forest_wolves`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 6 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → continue_from_elf_spring`。

| 可见标题 | 类别 |
|---|---|
| 森狼と戦う | 可选 |
| 携帯食で森狼を誘導する | 可选 |
| 森狼の脇を潜行して通る | 可选 |
| 泉へ戻る | 可选 |
| 見捨てて先を急ぐ | 可选 |

词典内未发现尚未遇到的名称。

## 精霊の泉・第一波 (`slime_ambush_one`)

职业：勇者。最少 6 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 鉄の剣 | 可选 |
| 渾身斬り | 可选 |
| 神聖の庇護 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 6 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 聖なる杖 | 可选 |
| 治癒の祈り | 可选 |
| 聖なる守護 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 6 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 魔力弾 | 可选 |
| 火球 | 可选 |
| 氷の矢 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 6 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| ダガー | 可选 |
| 影隠れ | 可选 |
| 急所突き | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

## 精霊の泉・第二波 (`slime_ambush_two`)

职业：勇者。最少 7 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring → @victory`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 鉄の剣 | 可选 |
| 渾身斬り | 可选 |
| 神聖の庇護 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 7 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring → @victory`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 聖なる杖 | 可选 |
| 治癒の祈り | 可选 |
| 聖なる守護 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 7 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring → @victory`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 魔力弾 | 可选 |
| 火球 | 可选 |
| 氷の矢 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 7 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring → @victory`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| ダガー | 可选 |
| 影隠れ | 可选 |
| 急所突き | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

## 精霊の泉・スライム王 (`slime_king_battle`)

职业：勇者。最少 8 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring → @victory → @victory`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 鉄の剣 | 可选 |
| 渾身斬り | 可选 |
| 神聖の庇護 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 8 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring → @victory → @victory`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 聖なる杖 | 可选 |
| 治癒の祈り | 可选 |
| 聖なる守護 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 8 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring → @victory → @victory`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 魔力弾 | 可选 |
| 火球 | 可选 |
| 氷の矢 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 8 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → rest_at_elf_spring → @victory → @victory`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| ダガー | 可选 |
| 影隠れ | 可选 |
| 急所突き | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

## 闇の森・出口 (`forest_exit`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 7 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → continue_from_elf_spring → distract_forest_wolves`。

| 可见标题 | 类别 |
|---|---|
| 森を出て麓の村へ向かう | 可选 |
| 宿屋へ向かう | 可选 |
| 狼の縄張りへ戻る | 可选 |

待核对名称：

| 名称 | 类型 | 出现于选项 |
|---|---|---|
| 麓の村 | 地点 | 森を出て麓の村へ向かう |
| 宿屋 | 地点 | 宿屋へ向かう |

## ゴブリン砦・一階前半 (`goblin_fort`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 4 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest`。

| 可见标题 | 类别 |
|---|---|
| 見張りのゴブリンと戦う | 可选 |
| 見張りを迂回する | 可选 |

词典内未发现尚未遇到的名称。

## ゴブリン砦・一階後半 (`goblin_fort_first_second`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 5 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success`。

| 可见标题 | 类别 |
|---|---|
| 三人のゴブリンと戦う | 可选 |
| 三人組を迂回する | 可选 |

词典内未发现尚未遇到的名称。

## ゴブリン砦・二階分岐 (`goblin_fort_second_choice`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 6 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success`。

| 可见标题 | 类别 |
|---|---|
| 右の通路を探索する | 可选 |
| 左の通路を探索する | 可选 |

待核对名称：

| 名称 | 类型 | 出现于选项 |
|---|---|---|
| 右の通路 | 地点 | 右の通路を探索する |

## ゴブリン砦・二階右 (`goblin_fort_second_right`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 7 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right`。

| 可见标题 | 类别 |
|---|---|
| 大ゴブリンと戦う | 可选 |
| 大ゴブリンを尾行して迂回する | 可选 |

词典内未发现尚未遇到的名称。

## ゴブリン砦・二階左 (`goblin_fort_second_left`)

职业：勇者。最少 7 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_left`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 鉄の剣 | 可选 |
| 渾身斬り | 可选 |
| 神聖の庇護 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 7 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_left`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 聖なる杖 | 可选 |
| 治癒の祈り | 可选 |
| 聖なる守護 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 7 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_left`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 魔力弾 | 可选 |
| 火球 | 可选 |
| 氷の矢 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 7 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_left`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| ダガー | 可选 |
| 影隠れ | 可选 |
| 急所突き | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

## ゴブリン砦・回復法陣 (`goblin_fort_healing_circle`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 8 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_left → @victory`。

| 可见标题 | 类别 |
|---|---|
| 回復法陣を使う | 可选 |

词典内未发现尚未遇到的名称。

## ゴブリン砦・三階鉄門 (`goblin_fort_third_gate`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 8 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success`。

| 可见标题 | 类别 |
|---|---|
| 暗号を答える | 可选 |
| 暗号を適当に作る | 可选 |
| 暗号を知らないと正直に言う | 可选 |

词典内未发现尚未遇到的名称。

## ゴブリン砦・三階警備戦 (`goblin_fort_third_guards`)

职业：勇者。最少 9 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → invent_goblin_password:critical_failure`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 鉄の剣 | 可选 |
| 渾身斬り | 可选 |
| 神聖の庇護 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 9 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → invent_goblin_password:critical_failure`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 聖なる杖 | 可选 |
| 治癒の祈り | 可选 |
| 聖なる守護 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 9 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → invent_goblin_password:critical_failure`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 魔力弾 | 可选 |
| 火球 | 可选 |
| 氷の矢 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 9 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → invent_goblin_password:critical_failure`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| ダガー | 可选 |
| 影隠れ | 可选 |
| 急所突き | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

## ゴブリン砦・四階財宝庫 (`goblin_fort_fourth`)

职业：勇者。最少 9 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → give_correct_password`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 鉄の剣 | 可选 |
| 渾身斬り | 可选 |
| 神聖の庇護 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 9 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → give_correct_password`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 聖なる杖 | 可选 |
| 治癒の祈り | 可选 |
| 聖なる守護 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 9 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → give_correct_password`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 魔力弾 | 可选 |
| 火球 | 可选 |
| 氷の矢 | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 9 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → give_correct_password`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| ダガー | 可选 |
| 影隠れ | 可选 |
| 急所突き | 可选 |
| 薬草 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

## ゴブリン砦・奪還した箱 (`goblin_fort_chest_choice`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 10 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → give_correct_password → @victory`。

| 可见标题 | 类别 |
|---|---|
| 迷子のゴブリンに箱を返す | 可选 |
| ゴブリンの箱を奪う | 可选 |

词典内未发现尚未遇到的名称。

## ゴブリン砦・箱の争奪 (`goblin_fort_chest_fight`)

职业：勇者。最少 11 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → give_correct_password → @victory → steal_lost_goblin_box`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 鉄の剣 | 可选 |
| 渾身斬り・改 | 可选 |
| 神聖の庇護 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 11 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → give_correct_password → @victory → steal_lost_goblin_box`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 聖なる杖 | 可选 |
| 治癒の祈り | 可选 |
| 聖なる守護 | 可选 |
| 聖なる裁き | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 11 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → give_correct_password → @victory → steal_lost_goblin_box`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 魔力弾 | 可选 |
| 火球・改 | 可选 |
| 氷の矢 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 11 步。

路线：`@opening → go_castle_town → go_inn → invite_robin:success → accept_robin_goblin_quest → fort_first_bypass:success → fort_second_bypass:success → explore_fort_right → bypass_hobgoblin:success → give_correct_password → @victory → steal_lost_goblin_box`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| ダガー | 可选 |
| 影隠れ・改 | 可选 |
| 急所突き | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

## 泉の奥・封印の岩壁 (`cave_seal`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 6 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall`。

| 可见标题 | 类别 |
|---|---|
| 魔法陣を解読する | 可选 |
| 泉の精霊に祈る | 可选 |
| 力ずくで岩壁を砕く | 可选 |
| ？？？ | 未知 |
| 泉へ戻る | 可选 |

词典内未发现尚未遇到的名称。

## 熱気の回廊 (`cave_heat_corridor`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 7 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success`。

| 可见标题 | 类别 |
|---|---|
| 戦う | 可选 |
| 岩陰を伝って抜ける | 可选 |
| 封印の岩壁へ戻る | 可选 |

词典内未发现尚未遇到的名称。

## 分かれ道 (`cave_fork`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 8 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success → sneak_heat:success`。

| 可见标题 | 类别 |
|---|---|
| 左の通路へ進む | 可选 |
| 右の通路へ進む | 可选 |
| 熱気の回廊へ戻る | 可选 |

待核对名称：

| 名称 | 类型 | 出现于选项 |
|---|---|---|
| 右の通路 | 地点 | 右の通路へ進む |

## 溶岩の小部屋 (`cave_lava_room`)

职业：勇者。最少 9 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success → sneak_heat:success → cave_left`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 鉄の剣 | 可选 |
| 渾身斬り | 可选 |
| 神聖の庇護 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 9 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success → sneak_heat:success → cave_left`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 聖なる杖 | 可选 |
| 治癒の祈り | 可选 |
| 聖なる守護 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 9 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success → sneak_heat:success → cave_left`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 魔力弾 | 可选 |
| 火球 | 可选 |
| 氷の矢 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 9 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success → sneak_heat:success → cave_left`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| ダガー | 可选 |
| 影隠れ | 可选 |
| 急所突き | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

## 地底の温泉 (`cave_hot_spring`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 9 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success → sneak_heat:success → cave_right`。

| 可见标题 | 类别 |
|---|---|
| 温泉で休む | 可选 |
| 分かれ道へ戻る | 可选 |
| 奥へ進む | 可选 |
| 少女に話しかける | 可选 |

词典内未发现尚未遇到的名称。

## 水晶の回廊 (`cave_crystal_corridor`)

职业：勇者 / 僧侶 / 魔法使い / 盗賊。最少 10 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success → sneak_heat:success → cave_right → hot_spring_forward`。

| 可见标题 | 类别 |
|---|---|
| 戦う | 可选 |
| 水晶の共鳴が収まるまで息を潜める | 可选 |
| 分かれ道へ戻る | 可选 |

词典内未发现尚未遇到的名称。

## 虹晶樹の間 (`cave_prism_tree`)

职业：勇者。最少 11 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success → sneak_heat:success → cave_right → hot_spring_forward → sneak_crystal:success`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 鉄の剣 | 可选 |
| 渾身斬り | 可选 |
| 神聖の庇護 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：僧侶。最少 11 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success → sneak_heat:success → cave_right → hot_spring_forward → sneak_crystal:success`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 聖なる杖 | 可选 |
| 治癒の祈り | 可选 |
| 聖なる守護 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：魔法使い。最少 11 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success → sneak_heat:success → cave_right → hot_spring_forward → sneak_crystal:success`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| 魔力弾 | 可选 |
| 火球 | 可选 |
| 氷の矢 | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

职业：盗賊。最少 11 步。

路线：`@opening → go_castle_town → go_dark_forest:success → attack_slime → @victory → crossroads_forward → inspect_spring_wall → decode_seal:success → sneak_heat:success → cave_right → hot_spring_forward → sneak_crystal:success`。

到达即进入战斗；下表为战斗指令。

| 可见标题 | 类别 |
|---|---|
| ダガー | 可选 |
| 影隠れ | 可选 |
| 急所突き | 可选 |
| 薬草 | 可选 |
| 治療の巻物 | 可选 |
| 防御 | 可选 |
| 逃走 | 已知但不可选 |

词典内未发现尚未遇到的名称。

## 待设计审查

共 14 个「地点 × 名称」候选（职业间去重）。
TODO(design): 逐项判断是否属于合理的目的地/任务预告，或需要 secret / visible_after 等叙事门槛；本任务只修正 spec 指定的 ask_seal_lore。

Scenario SHA-256: `517c50c09208279b64cf143e708b824a03b0a30b2ce5c74a3c13a22b1615522c`
