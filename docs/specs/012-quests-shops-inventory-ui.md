# 012 任务日志、宿屋付费休息、背包使用、RPG 式商店

用户的要求：
- 把"回王城向国王汇报"做成给玩家的任务。
- 宿屋增加付费几 G 的休息。
- 背包里的药草等可以直接使用。
- 商店和背包改成 RPG 常见的界面，不要用对话选项的形式。

下面的设计决定和文字由设计负责人给出，日语文字**逐字使用**。两份剧本同步修改。

## A. 任务日志（クエスト）
### 引擎
- 剧本新增顶层 `quests`。每个任务由若干阶段组成，状态**完全由 flag 推导**，不额外保存：
  ```json
  {"id": "main_ignis", "title": "...", "description": "...", "kind": "main|side|mystery",
   "start_flag": "...",            // 没有这个 flag 时任务不出现；空字符串表示一开始就出现
   "stages": [{"text": "...", "done_flag": "..."}],   // 按顺序，第一个 done_flag 没满足的阶段就是当前目标
   "complete_flags": ["..."], "fail_flags": ["..."]}
  ```
- `public_session` 返回 `quests`：每个任务给出标题、描述、种类、状态（active/completed/failed），以及当前目标的文字和已完成的阶段。
- 状态变化时（出现、阶段推进、完成、失败），写一条 system log：「クエスト更新：<title>」或「クエスト達成：<title>」。
- GM 契约不变，模型不能操作任务。

### 任务内容（逐字使用）
1. `main_ignis`｜main｜「紅き邪竜の討伐」｜描述：国王エドワードから、王国を脅かす邪竜イグニスの討伐を依頼された。｜start_flag 空
   - 「闇の森を抜け、麓の村へ向かう」 done：`reached_village`
   - 「竜の谷へ向かう」 done：`entered_dragon_valley`
   - 「邪竜イグニスを倒す」 done：`defeated_ignis`
   - 「王城へ戻り、国王に報告する」 done：（完成条件）
   - complete_flags：`reported_to_king`（新 flag，`report_normally` 和 `report_with_evidence` 都要设置）
2. `side_lost_goblin`｜side｜「迷子のゴブリンの箱」｜描述：別の一族に盗まれた箱を取り戻してほしいと、迷子のゴブリンに頼まれた。｜start：`lost_goblin_quest`
   - 「ゴブリン砦の最上階へたどり着く」 done：`cleared_goblin_fort`
   - 「箱を持ち主に返す」
   - complete：`returned_lost_goblin_box`；fail：`betrayed_lost_goblin`
3. `side_robin`｜side｜「義賊ロビンの依頼」｜描述：ロビンと共に、ゴブリン砦の財宝を取り戻す。｜start：`accepted_robin_goblin_quest`
   - 「ゴブリン砦を攻略する」
   - complete：`cleared_goblin_fort`
4. `side_ian`｜side｜「砕けた氷の太刀」｜描述：イアンから、氷の太刀を砕いた元凶を追ってほしいと頼まれた。｜start：`accepted_ian_request`
   - 「元凶の手がかりを探す」
   - complete：`draco_revealed`（真相大白时完成；没有揭发就一直保持进行中，这是有意的，作为提示）
5. `mystery_frost`｜mystery｜「凍てつく謎」｜描述：炎に包まれた村に、不自然な氷が残されていた。誰の仕業だろうか。｜start：`frost_trace_seen`、`heard_ignis_last_words`、`noticed_general_frost` 中任意一个（`start_flag` 支持数组，满足任一即可）
   - 「白い氷の手がかりを集める」
   - complete：`draco_revealed`
   - 描述下方显示「手がかり：n」，n 是 scenario-v2.md 3.5 节线索 flag 的已获得数，加上持有白い竜鱗时 +1。**不要显示总数**（避免剧透）。

### UI
- SYSTEM MENU 增加「クエスト」区块（放在所持品上方，或者用标签页切换，选一种在汇报里说明）。
- 每个任务一张卡片：种类标签（メイン / サブ / 謎，main 用 `--gold`，side 用 `--blue`，mystery 用 `--purple`）、标题、当前目标（前面加 ▶）、已完成阶段用 `--text-dim` 加删除线显示。已完成或失败的任务折叠到列表下方，带「達成」（`--green`）或「失敗」（`--red`）标签。
- 任务状态变化时，屏幕右上角弹出 3 秒提示：「クエスト更新」或「クエスト達成」+ 标题，风格沿用现有面板（`--panel` 背景，`--gold` 描边）。

## B. 宿屋的付费休息
- 王城の宿屋新增动作 `rest_at_inn`「宿で休む（10G）」｜preview：温かい食事と寝台で疲れを癒す｜条件：gold ≥ 10｜效果：-10G，HP/MP/SP 全回复。
  - 结果文：温かいスープと清潔な寝台で、一晩ぐっすりと眠った。体の疲れがすっかり抜けている。
- 先检查 009 在哪里加了"宿屋全回复"（汇报里说明）。如果和这个动作重复，以这个付费版本为准。连续流程模拟里，把住宿当作可选的付费恢复。

## C. 背包：战斗外使用道具
- 新接口 `POST /api/sessions/{id}/items/use`，body `{"item_id": "..."}`。只允许 `combat.kind` 为 `heal` 或 `restore` 的物品在战斗外使用：效果和战斗中相同，按实际缺少的量回复。满值时拒绝，并且不消耗道具（提示文：「これ以上回復する必要はない。」）。战斗中、游戏结束后都拒绝（战斗中走现有的战斗道具行动）。
- 使用时写 system log：「<item>を使った。HPが<n>回復した。」（MP 的写法相同）。
- 不调用 LLM。

## D. 商店
### 数据与引擎
- 剧本新增顶层 `shops`：
  ```json
  {"id": "sarah_shop", "location_id": "item_shop", "keeper_npc": "sarah", "title": "サラの道具屋",
   "greeting": "...", "buy_line": "...", "sell_line": "...", "poor_line": "...",
   "items": [{"item_id": "herb", "price": 10, "stock": 3}],   // stock 为 null 表示不限量
   "buys": true}
  ```
- 库存保存在会话里。新接口：`GET /api/sessions/{id}/shops/{shop_id}`、`POST .../buy {"item_id", "quantity"}`、`POST .../sell {"item_id", "quantity"}`。卖出价为买入价的一半（向下取整）；没有标价的物品按 5G 收购；`key_item: true` 的物品不能卖。
- 在商店所在地点加一个动作「店に入る」（`open_shop: <shop_id>`），前端收到后打开商店界面。自由输入"薬草を買いたい"一类，按现有的 existing 机制对应到这个动作即可，不新增 planner 操作。
- **移除**现有用 children 实现的购买选项（`sarah_shop`、`blue_mage_shop`、`buy_equipment` 以及村里的 `buy_ice_amulet`），改为商店数据。原来的价格和库存都要保留，商品清单合并 scenario-v2.md 4.7 节。`forge_ice_charm`（制作）和 `buy_white_scale`（剧情交易）**保留为动作**，不放进商店。
- 物品新增可选字段 `category`：`consumable` / `equipment` / `material` / `key`，以及 `key_item: true`。`白い竜鱗`、`紅竜の炎核`、`火種` 设为 key；`氷の結晶` 设为 material。其余按现有的 `combat.kind` 推导，推导规则写进汇报。
- 冗余检查（`redundancy.py`）要识别商店来源。

### 商店列表与台词（逐字使用）
| shop_id | 地点 | 店主 | title | greeting | buy_line | sell_line | poor_line |
|---|---|---|---|---|---|---|---|
| `sarah_shop` | item_shop | sarah | サラの道具屋 | いらっしゃいませ！今日は何をお探しですか？ | ありがとう！大事に使ってね。 | わあ、いいの？ちゃんと買い取るね。 | うーん、お金が足りないみたい……。 |
| `magic_shop` | magic_shop | blue_robed_mage | 青のローブ魔法店 | ……魔道具なら一通り揃っている。 | 扱いには気をつけてくれ。 | 悪くない品だ。引き取ろう。 | 代金が足りないようだ。 |
| `forge_shop` | forge | blacksmith | ローベルト鍛冶店 | ……用件は。 | 手入れは怠るな。 | ……預かろう。 | 金が足りん。 |
| `village_shop` | village | shopkeeper | 麓の村の道具屋 | こんな時でも店は開けてるよ。気をつけてな。 | 無事を祈ってるよ。 | 助かるよ、引き取ろう。 | すまんが、それじゃ足りないな。 |

`village_shop` 的地点 `village` 如果在当前路线上已经无法到达（村子已经烧毁），汇报里说明，并提出放在哪里更合适，不要自己决定。

### 商店界面（布局由设计负责人指定）
- 模态窗口，和 SYSTEM MENU 同样的结构和风格（深色背景、金色标题、右上角 ✕）。
- **头部**：左边店主的小头像（现有立绘裁成圆形，64px）+ 店名（金色标题），下面一行是店主台词（买东西、卖东西、钱不够时换成对应台词）；右边是持有金币，样式沿用 SYSTEM MENU 的 GOLD 块。
- **标签**：「購入」「売却」两个标签（选中的那个下面加金色线）。
- **左栏（列表，约 60% 宽）**：每行一个商品，依次是物品名、一行效果概要（`--text-dim`）、价格（`--gold`，例如「10 G」）、库存徽章（「在庫 2」或「∞」，样式沿用现有的数量徽章）。点击某一行就选中它（`--gold-glow` 描边）。买不起的行，价格变成 `--red`；售罄的行整体变暗，并显示「売り切れ」。
- **右栏（详情，约 40%）**：所选物品的名称、描述、效果、当前持有数量（「所持：n」），底部是数量调节（− n +，上限取库存、金币能买的数量、持有数中的最小值）和主按钮「購入する」/「売却する」（金色按钮，沿用现有主按钮样式）。按不了时，在按钮下方用一行小字说明原因。
- 卖出页只列可以卖的物品；重要物品不出现在列表里。
- 窄屏（< 768px）时两栏改成上下排列。

### 背包界面（改造 SYSTEM MENU 的「所持品」）
- 按 category 分组：「消耗品」「装備」「素材」「重要」，每组一个小标题。
- 每行：物品名、数量徽章、装备中的显示「装備中」标签（`--green`），重要物品显示「重要」标签（`--gold`）。点开以后，显示描述和效果（沿用现有的展开方式），可以在战斗外使用的物品，在展开区里显示「使う」按钮。使用后列表即时刷新，并弹出提示。

## E. 验收产物
- 如果条件允许，加一个截图脚本（例如用已有的依赖，或者纯 Python 起服务后用浏览器截图）。不能加新依赖的话就不做，汇报里说明，由设计负责人在浏览器里亲自查看。
- 测试：任务状态推导（每个任务的出现、推进、完成和失败）、休息（钱够、钱不够）、使用道具（正常、满值、战斗中）、商店（买、卖、库存、钱不够、重要物品不能卖、存档后库存保持）。
- 旧存档：没有商店库存数据时按初始库存处理，没有 `reported_to_king` 也不报错。

## 不做
- 装备的切换、卸下（以后再做）。
- 不改默认提示词。

## 汇报要回答
1. 每家商店的最终商品清单（物品、价格、库存）。
2. 009 的"宿屋全回复"实际加在了哪里。
3. category 的推导规则。
4. `village_shop` 的可达性问题。
5. 其余按 `docs/roles/engineering.md` 的汇报格式。
