# 048 工程汇报

状态：功能实现与补丁已交付；全量通过、真实截图和 Git 提交尚未完成，原因见验证与偏离说明。

## 1. 完成了什么

精霊の泉采用设计已决定的方案 A：只能休息一次，保留先回满、两波史莱姆及史莱姆王，最后直接前往 `forest_wolves`。`once`、`hidden_after` 与 `visible_requirements.not_flag=defeated_slime_king` 同时阻止再次休息；删除原来的已击败分支。未休息时的主动前进、岩壁、十字路、汲水、聆听行动不变。两份剧本同步，迁移可重跑。

baby 与 normal 使用相同流程；baby 玩家也只能在泉休息一次，不能在史莱姆王后再免费回满。047 的 `baby_numeric_freeze.json` 完全未改，冻结地址及数值保持一致。旧数值模拟器的历史测试另用显式的旧泉流程 fixture，避免把体验改动混进旧数值比较；该 fixture 不用于实际游戏或新增流程测试。

已讨伐判断为 `defeated_ignis OR ignis_purified`，与实际数据一致。斩杀路线由 `dragon_valley_loc` 胜利进入 `ignis_last_breath`；净化设置 `ignis_purified` 并进入同名地点。26 个行动提供 `guidance: true`，客户端仅按此布尔值显示金色和星号；服务器在两个 flag 均未成立时删除该显示字段。深色沿用主题金色，浅色媒体条件直接复用主题金色背景和主题深色文字，并覆盖悬停、焦点、禁用状态。星号带屏幕阅读器标签，复用既有「メイン」。

`current_action_choices` 保留供 UI 使用的字段，并遵守既有 visible_requirements；旧 choice 的规范化也保留该可见条件，避免 NPC 缺席备用菜单出现不可执行选项。`public_session` 白名单新增 `guidance`；模型用的 `_trim_choices`、行动解释器白名单均不包含此字段。默认提示词和冻结 benchmark 未改。

旧存档读入时由新的 `content_revision` 触发既有刷新及选项重建；已经击败史莱姆王、停在泉的存档会隐藏休息，仍可前进或离开。为让旧存档从原王都回到回城主线，原城下町返回行动在两个 flag 之一成立时转到 `festival_town`；村庄回城也使用同一分流，并设置既有 returned_to_capital，以便 hybrid 的章节锁允许这次回城。没有新增结局。

现状差异：史莱姆王原先没有胜利 `result_texts.victory`，只有败北文本；因此新增的是一条功能性过渡占位，没有可拼接的原胜利正文。引擎战斗有永久击败标记，不能仅凭地点图有环推断敌人可重复击杀。

### 恢复行动审计

执行 `python -m scripts.scenario.spring_postgame --audit`。遍历两份剧本的嵌套行动、成功/失败与 branch 分支，排除自身或父行动带 `once` / `disabled_after` 的行动，识别 `restore_full`、`restore_ratio` 和正数 HP/MP/SP effects。地点图按分支的并集保守检查环，再检查击败标记是否有被清除的路径；测试使用人工可重生循环验证审计会报警。

两份剧本结果一致：

| 地点 / 行动 | 恢复 | 成本 | 无限重复战斗环 |
|---|---|---|---|
| `inn/rest_at_inn` | 回满 | 10G | 无 |
| `village/rest_at_refuge` | 回满 | 5G | 无 |
| `goblin_fort_healing_circle/use_fort_healing_circle` | 回满后移动 | 免费 | 无 |
| `king_private_room/ask_king_rest` | 回满 | 免费，需 `king_trust` | 无 |
| `oaksdawn_chapel/pray_oaksdawn` | 回满 | 5G | 无 |
| `oaksdawn_inn/rest_oaksdawn` | 回满 | 10G | 无 |

这些地点的保守移动图可连到战斗，但 `combat.ensure_combat_started` 会排除 `combat_defeated:<地点>:<敌人>`；两份剧本没有清除此类标记的行动，因此没有发现其它免费回满加无限战斗的环。区域重试同时回滚角色、物品、flags 与成长，不能积累该区域收益。上述其它恢复点未改；建议后续若开放敌人重生，设计需重新审查两个免费恢复点。

### guidance 标记清单

以下只在已斩杀或已净化时呈现金色；各行动原有秘密、角色、条件限制继续适用。

| 地点 | 行动 ID |
|---|---|
| `ignis_last_breath` | `return_to_castle_report` |
| `ignis_purified` | `return_to_castle_report` |
| `royal_gate` | `enter_festival_town` |
| `festival_town` | `go_report_hall`, `go_general_mansion`, `request_king_audience` |
| `castle_report` | `report_normally`, `report_with_evidence` |
| `mansion_garden` | `sneak_into_mansion`, `robin_picks_lock` |
| `mansion_corridor` | `fight_ice_sentinels`, `evade_ice_sentinels`, `pass_cleared_sentinels` |
| `mansion_study` | `take_draco_journal`, `leave_mansion_study` |
| `king_private_room` | `confide_in_king`, `leave_king_room` |
| `forge` | `return_castle_from_forge` |
| `magic_shop` | `return_castle_from_magic_shop` |
| `inn` | `return_castle_from_inn` |
| `item_shop` | `return_castle_from_item_shop` |
| `alley` | `return_castle_from_alley` |
| `alley_night` | `leave_night_alley` |
| `alley_after` | `return_castle_after_curse` |
| `castle` | `go_castle_town` |
| `castle_town` | `return_castle_from_town` |

`dragon_valley_return` 是自动战斗，无可点击行动；胜利自动到 `royal_gate`。`draco_battle` 同样为自动战斗，胜利直接结局，不虚构按钮。屋敷研究室标记取日誌及离开；王的私室标记打开心扉及离开，分别对应证据分支的关键步骤与返回报告。

### 隐藏 / 换文清单

| 地点 | 行动 | 处理 |
|---|---|---|
| `castle` | `ask_king_info`, `ask_general_advice`, `check_supplies` | 两个 postgame flag 任一成立即隐藏；对应 NPC 增加无结局 effects 的占位闲聊 |
| `forge` | `ask_blacksmith_weakness` | 两个 postgame flag 任一成立即隐藏；对应 NPC 增加无结局 effects 的占位闲聊 |
| `magic_shop` | `ask_blue_mage_rumor` | 两个 postgame flag 任一成立即隐藏；对应 NPC 增加无结局 effects 的占位闲聊 |
| `village` | `ask_elder_weakness` | 两个 postgame flag 任一成立即隐藏；对应 NPC 增加无结局 effects 的占位闲聊 |
| `village_frozen_clue`、`ian_ice_katana_aftermath` | `visit_village` | 讨伐后隐藏，新增同一目的地的 `visit_village_postgame`，只替换过时按钮文字 |
| `castle` | `ask_king_ten_years` | 保留：十年前的调查仍影响将軍真相，既有线索 flag 不变 |
| `village` | `talk_elder/ask_elder_treaty` | 保留父菜单和盟约调查，只隐藏邪竜弱点子项 |
| `castle_town` | `ask_gald_rumor` | 保留：将軍屋敷与古战场的消息仍有用途 |
| 其他搜索命中 | 装备说明中的弱点、冻结资料 / prepared 文本、已隐藏行动的关键词 | 不是尚可点击的邪竜备战提问，保留；不改道具正文或默认提示词 |

全量搜索「弱点」「討伐方法」「討伐の相談」和 `heard_dragon_weakness` 后，可点击的过时问题全部落在上表。商店、锻造、未完成支线和仍有意义的真相调查继续可用。新增闲聊只使用独立 `once` 完成标记，无奖励、判定或结局线索 effects。

## 2. 改动的文件

- `scripts/scenario/spring_postgame.py`：幂等迁移、占位清单、只读恢复环审计。
- `host/prompt/processed/dragon_rpg.json`、`dragon_rpg_hybrid.json`：同步流程、可见性、guidance、占位。
- `host/prompt/processed/scenario_pack.schema.json`：action / choice 的 guidance 布尔字段。
- `host/prompt/processed/difficulty/overlay_revision.json`：只更新内容版本；overlay 哈希与 baby 金标不变，供旧存档刷新。
- `host/scenario_context.py`、`host/state.py`：按 postgame flags 限定显示并传递 guidance。
- `client/app.js`、`styles.css`、`index.html`：渲染、状态样式和缓存键。
- `tests/test_spring_postgame.py`、`guidance_choices.test.js`：9 项新回归测试，含真实渲染函数的 4 状态 DOM 测试。
- `tests/test_balance_pass3.py`、`test_forest_cave.py`、`test_ch34_rest.py`：更新旧目的地和一次休息断言。
- `tests/spring_legacy_balance.py`、`test_class_aware_route.py`、`test_measurement_v2.py`、`test_measurement_v2b.py`：为旧数值比较显式保留旧泉 fixture；不改模拟器。
- 旧迁移相关测试（checks_e、loot_economy、oaksdawn、oaksdawn_quests、rewards_battlefield、rumbling_gorge、combat_mechanics_v2、npc_combat）：按顺序组合 048 后验证幂等，保留已有检查；`test_balance.py` 固定旧泉流程对照 checkpoint，`test_balance_pass2.py` 接受两处同目的地换文入口；`test_scenario_invariants.py` 更新泉的既有标准风险标签。
- 本汇报及 `eval/reports/screens/048/README.md`：验收证据和截图阻塞说明。
- 无新增依赖。

所有 `tests/` 目标文件实际位于 `.tmp-test/048/tests/`，随 `tests.patch` / `048.patch` 导出；沙箱未允许写入正式目录。

## 3. 验证结果

- 新增测试：`python -m unittest discover -s .tmp-test/048/tests -p test_spring_postgame.py -q`：9 tests，OK。覆盖两难度三场战斗、旧存档实际读入刷新、不休息路径、两种邪竜 flag、全部地点非死路、字段进 UI 不进模型、迁移幂等、两包同步、baby 冻结、96 行占位与报告一致、恢复环检测、前端四种渲染状态。
- `python -m unittest discover -s tests -p test_difficulty_freeze.py -q`：4 tests，OK；未改 baby 金标。
- `node --check client/app.js`：退出 0。`git diff --check`：退出 0。
- 冻结重放：`python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --backend gemini --model gemini-3.1-flash-lite --variant guard_rules --split dev`：194/194 缓存命中，live=false，全部 metrics 与 `2026-10-12T062656092753Z` 参考报告一致；S0/1/2/3/4=173/12/8/1/0。证据 `.tmp-test/048/cache-replay.json`。
- 离线通玩：`python -m scripts.playtest.explore --characters hero cleric mage thief --seeds 20261013 --steps 330 --workers 1 --output .tmp-test/048/playtest/summary.md`：4 局均无异常、无非战斗死路；此种子下均为战斗败北（64/75/72/124 步），不宣称通过结局通关。报告直接写入 .tmp-test，未改或提交既有 playtest-* 报告。原 workers=4 被沙箱拒绝创建管道，已用单进程完成。
- 原命令 `python -m unittest discover -s tests -q` 已尝试，卡在旧泉模拟器的回原地等待，已终止；正式 tests/ 不可写，不能在原目录应用适配。
- 完整套件使用 `.tmp-test/048/run_tests.py` 加载测试补丁，保留原 __file__，让既有 fixture 路径与正式目录一致；不跳过新增或失败测试。旧迁移组合及最新可见性 / 风险 / 回城回归的专项复验通过。
- 最终完整套件：`python .tmp-test/048/run_tests.py --verbose`（由 run_full.py 捕获 UTF-8 日志）执行 **855 tests / 0 断言失败 / 36 errors / 1 skipped**，耗时 454.864 秒，退出 1。36 个错误块全部包含 PermissionError，来自既有 TemporaryDirectory 下的存档、目标文件与缓存读写 / 清理；逐项证据见 `.tmp-test/048/environment-errors.json` 和 `unittest-stable.log`。没有把权限错误当作通过，也没有跳过失败项。源码、数据稳定后重新跑完整套件，之前发现的迁移 / 可见性 / 入口断言均已修正。
- 截图：浏览器清单为空；`cua.createBrowserTab("iab")` 返回 `Browser is not available: iab`。没有生成伪截图，也未把 DOM 测试当作视觉验收。

日志均保存在 `.tmp-test/048/`；最终补丁用 UTF-8 无 BOM、LF。`git apply --check` 已在隔离 HEAD 文件副本通过。

## 4. TODO(design) 清单

1. 按下方逐处占位表定稿所有 96 处 `【仮】`（含两包及备用菜单副本）；定稿后同步更新迁移模板与占位数量测试。
2. 侍従只有既有支给行动，没有可复用的 NPC 实体 / npc_id。现在隐藏过时支给，不自行新增 NPC 或编造身份；需要独立讨伐后侍従对话时请提供实体规范。
3. 若以后引入敌人重生或 EXP 重复战斗，复审治疗阵和国王免费住宿的使用限制。

## 5. 推断清单

1. 仍有结局用途的十年前事件、盟约、将軍屋敷消息不属于过时邪竜弱点问题；保留它们及原线索 flags。
2. 除国王、将軍、长老和两位提示 NPC 外，也给现有城中店主 / 同伴增加不影响结局的 postgame 闲聊，具体 NPC 见表；原商店和支线继续保留。
3. 提示 NPC `warlock` 与店面 `blue_robed_mage` 使用现有别名体系；沿用原噂行动的 `warlock`，不新增 NPC。
4. 不拆王都地点；旧存档回城行动按同一 postgame flags 转到 `festival_town` 并设置既有 returned_to_capital，避免金色指引循环或被 hybrid 的章节跳转检查挡住。
5. 补充金色行动包含回城后商店出口、屋敷证据及返回动作；自动战斗和结局没有可标记的按钮。
6. `once` 默认只禁用，因此泉另加隐藏标记；旧存档兼容使用已有史莱姆王 flag，未把旧玩家强制重打战斗。
7. 更新内容 revision 和对应 overlay revision 记录是旧存档获得本次流程所需；未改数值或 overlay 内容。
8. 历史数值模拟器的测试使用显式旧流程 fixture，保证数值对照可复现；实际游戏与新增测试始终使用新流程。
9. 全地点可玩性将没有按钮的强制战斗视为可推进状态；不为自动战斗新增行动。
10. 旧迁移重排其自身行动，因此 048 把新闲聊放在既有行动后；旧迁移测试在其自身迁移后再次应用 048，验证的是当前完整流程。
11. 深浅样式采用浏览器 `prefers-color-scheme`；项目当前没有全局浅色主题设置，本任务只处理指引卡片的配色。星号的无障碍标签复用现有「メイン」。
12. 休息必然启动伏击，因此风险标签复用现有「危険（戦闘）」；过渡与一次休息说明依然全部标为【仮】。

## 6. 偏离 spec 的地方及原因

- 正式 `tests/` 与 `.git` 不可写，且全量测试无法获得通过结果，因此未创建提交；按 048 brief 的明确备用方式交付 `.tmp-test/048/tests.patch` 和 `.tmp-test/048/048.patch`；不调整权限。
- 无可用浏览器，三张真实截图未完成；保留阻塞说明，DOM 检查通过并不能替代视觉验收。
- 旧模拟器与新泉流程不兼容，而 spec 明令不得修改 `scripts/balance/`；只在历史数值测试里保留旧拓扑，报告其运行限制。
- 单次现有离线脚本运行覆盖四职业、一个种子；按真实结果报告，无异常与非战斗死路，不将战斗败北称为结局通关。

## 7. 已知问题

- `scripts/balance/route.py` 与 `class_aware.py` 的自动泉休息等待回原地，配合当前剧本会无法正确退出；本任务禁止修改这些脚本。请后续专门适配其流程，当前不要对新剧本运行旧 hp70/class_aware 自动泉休息模拟。
- 全量验证未通过：沙箱中 Python `TemporaryDirectory` 产生的部分目录不可写，多项已有存档与缓存测试受影响；没有修改任何目录权限。
- 真实客户端的浅 / 深截图与视觉验收尚缺。
- 台词为占位，尚未设计定稿；侍従实体待设计提供。

## NPC 对话表

| NPC | 地点 | 未讨伐选项 | 已讨伐选项 | 新台词数 |
|---|---|---|---|---|
| 国王 (`king`) | `castle` | `ask_king_ten_years`, `ask_king_info` | `postgame_chat_king`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| 将軍ドラコ (`general`) | `castle` | `ask_general_advice` | `postgame_chat_general`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| 行商人ガルド (`gald`) | `castle_town` | `ask_gald_rumor`, `ask_gald_extra` | `postgame_chat_gald`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| 行商人ガルド (`gald`) | `festival_town` | `open_gald_capital_shop` | `postgame_chat_gald`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| 鍛冶師ローベルト (`blacksmith`) | `forge` | `open_forge_shop`, `ask_blacksmith_weakness`, `show_sword_to_blacksmith`, `accept_sword_fusion`, `activate_ice_charm`, `forge_ice_charm`, `ask_robert_hammer`, `return_robert_hammer`, `dig_forge_scrap` | `postgame_chat_blacksmith`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| 青いローブの魔法使い (`warlock`) | `magic_shop` | `ask_blue_mage_rumor`, `invite_blue_mage`, `ask_seal_lore` | `postgame_chat_warlock`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| ミーナ (`mina`) | `magic_shop` | `ask_mina_missing`, `report_mina_safe` | `postgame_chat_mina`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| イアン (`ian`) | `inn` | `rest_at_inn`, `ask_ian` | `postgame_chat_ian`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| ロビン (`robin`) | `inn` | `ask_robin`, `accept_robin_goblin_quest`, `robin_archery` | `postgame_chat_robin`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| サラ (`sarah`) | `item_shop` | `open_sarah_shop`, `borrow_fire_bat_dragon`, `ask_sarah_request`, `give_moss_to_sarah`, `accept_sarah_scarf`, `deliver_sarah_scarf`, `help_sarah_shelves` | `postgame_chat_sarah`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| 怪しい商人 (`suspicious_merchant`) | `alley_night` | `hear_curse_offer_hero`, `accept_curse_offer_hero`, `hear_curse_offer_cleric`, `accept_curse_offer_cleric`, `hear_curse_offer_mage`, `accept_curse_offer_mage`, `hear_curse_offer_thief`, `accept_curse_offer_thief`, `pay_curse_price_hero`, `pay_curse_price_cleric`, `pay_curse_price_mage`, `pay_curse_price_thief`, `betray_cursed_merchant`, `buy_white_scale`, `see_through_merchant` | `postgame_chat_suspicious_merchant`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| 長老 (`elder`) | `village` | `talk_elder`, `rest_at_refuge`, `ask_elder_legend` | `postgame_chat_elder`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| 道具屋の店主 (`shopkeeper`) | `village` | `open_village_shop` | `postgame_chat_shopkeeper`；保留相关商店/支线 | 1 段结果 + 1 按钮 |
| 侍従（无 NPC 实体） | `castle` | `check_supplies` | 隐藏已过时支给；TODO(design)：没有可复用 npc_id，未新增实体 | 0 |

## 占位表

两份剧本逐处列出；相同文本的多处副本分别计数。

| 编号 | 文本位置 | 用途 | 出现条件 | 占位原文 | 建议长度 |
|---|---|---|---|---|---|
| P001 | `dragon_rpg.json/locations/castle/actions/postgame_chat_king/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】国王と討伐後の話をする。 | 10–24 字 |
| P002 | `dragon_rpg.json/locations/castle/actions/postgame_chat_king/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P003 | `dragon_rpg.json/locations/castle/actions/postgame_chat_general/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】将軍ドラコと討伐後の話をする。 | 10–24 字 |
| P004 | `dragon_rpg.json/locations/castle/actions/postgame_chat_general/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P005 | `dragon_rpg.json/locations/castle_town/actions/postgame_chat_gald/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】行商人ガルドと討伐後の話をする。 | 10–24 字 |
| P006 | `dragon_rpg.json/locations/castle_town/actions/postgame_chat_gald/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P007 | `dragon_rpg.json/locations/forge/actions/postgame_chat_blacksmith/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】鍛冶師ローベルトと討伐後の話をする。 | 10–24 字 |
| P008 | `dragon_rpg.json/locations/forge/actions/postgame_chat_blacksmith/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P009 | `dragon_rpg.json/locations/inn/actions/postgame_chat_ian/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】イアンと討伐後の話をする。 | 10–24 字 |
| P010 | `dragon_rpg.json/locations/inn/actions/postgame_chat_ian/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P011 | `dragon_rpg.json/locations/inn/actions/postgame_chat_robin/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】ロビンと討伐後の話をする。 | 10–24 字 |
| P012 | `dragon_rpg.json/locations/inn/actions/postgame_chat_robin/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P013 | `dragon_rpg.json/locations/village/actions/postgame_chat_elder/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】長老と討伐後の話をする。 | 10–24 字 |
| P014 | `dragon_rpg.json/locations/village/actions/postgame_chat_elder/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P015 | `dragon_rpg.json/locations/village/actions/postgame_chat_shopkeeper/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】道具屋の店主と討伐後の話をする。 | 10–24 字 |
| P016 | `dragon_rpg.json/locations/village/actions/postgame_chat_shopkeeper/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P017 | `dragon_rpg.json/locations/magic_shop/actions/postgame_chat_warlock/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】青いローブの魔法使いと討伐後の話をする。 | 10–24 字 |
| P018 | `dragon_rpg.json/locations/magic_shop/actions/postgame_chat_warlock/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P019 | `dragon_rpg.json/locations/magic_shop/actions/postgame_chat_mina/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】ミーナと討伐後の話をする。 | 10–24 字 |
| P020 | `dragon_rpg.json/locations/magic_shop/actions/postgame_chat_mina/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P021 | `dragon_rpg.json/locations/item_shop/actions/postgame_chat_sarah/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】サラと討伐後の話をする。 | 10–24 字 |
| P022 | `dragon_rpg.json/locations/item_shop/actions/postgame_chat_sarah/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P023 | `dragon_rpg.json/locations/alley_night/actions/postgame_chat_suspicious_merchant/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】怪しい商人と討伐後の話をする。 | 10–24 字 |
| P024 | `dragon_rpg.json/locations/alley_night/actions/postgame_chat_suspicious_merchant/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P025 | `dragon_rpg.json/locations/elf_spring/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】精霊の泉では一度だけ休める。 | 20–60 字 |
| P026 | `dragon_rpg.json/locations/elf_spring/choices/0/preview` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】泉で休めるのは一度だけで、休息中に襲われる恐れがある。 | 20–60 字 |
| P027 | `dragon_rpg.json/locations/elf_spring/hybrid/summary` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】精霊の泉では一度だけ休める。 | 20–60 字 |
| P028 | `dragon_rpg.json/locations/elf_spring/actions/rest_at_elf_spring/preview` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】泉で休めるのは一度だけで、休息中に襲われる恐れがある。 | 20–60 字 |
| P029 | `dragon_rpg.json/locations/slime_king_battle/combat/result_texts/victory` | 过渡 | 史莱姆王胜利后 | 【仮】泉でのひと休みを終え、先へ進む。 | 20–60 字 |
| P030 | `dragon_rpg.json/locations/village_frozen_clue/actions/visit_village_postgame/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】長老のいる村へ向かう。 | 10–24 字 |
| P031 | `dragon_rpg.json/locations/ian_ice_katana_aftermath/actions/visit_village_postgame/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】長老のいる村へ向かう。 | 10–24 字 |
| P032 | `dragon_rpg.json/locations/festival_town/actions/postgame_chat_gald/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】行商人ガルドと討伐後の話をする。 | 10–24 字 |
| P033 | `dragon_rpg.json/locations/festival_town/actions/postgame_chat_gald/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P034 | `dragon_rpg.json/maps/forest/nodes/F3/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】精霊の泉では一度だけ休める。 | 20–60 字 |
| P035 | `dragon_rpg.json/status_defs/burn/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】火傷による持続ダメージを受ける。 | 20–60 字 |
| P036 | `dragon_rpg.json/status_defs/poison/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】層ごとに持続ダメージ。重ねると残り時間を更新する。 | 20–60 字 |
| P037 | `dragon_rpg.json/status_defs/weaken/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】与えるダメージが0.75倍になる。 | 20–60 字 |
| P038 | `dragon_rpg.json/status_defs/paralysis/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】25%の確率で行動できない。リソースは消費しない。 | 20–60 字 |
| P039 | `dragon_rpg.json/status_defs/stun/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】次の行動を失い、その後2ラウンドは気絶を防ぐ。 | 20–60 字 |
| P040 | `dragon_rpg.json/status_defs/holy_mark/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】聖属性の持続ダメージと、攻撃命中時の聖属性追撃。 | 20–60 字 |
| P041 | `dragon_rpg.json/status_defs/blind/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】命中率が下がる。ボスと冒険者への効果は20%。 | 20–60 字 |
| P042 | `dragon_rpg.json/status_defs/haste/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】毎ラウンドの行動回数が1増える。持続中は重ねられない。 | 20–60 字 |
| P043 | `dragon_rpg.json/status_defs/holy_afterglow/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】次の敵フェーズ終了まで攻撃ダメージを吸収する。上限は最大HPの25%。 | 20–60 字 |
| P044 | `dragon_rpg.json/status_defs/arcane_shield/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】一度だけ攻撃ダメージを防ぐ。 | 20–60 字 |
| P045 | `dragon_rpg.json/status_defs/gospel/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】最大HPが2倍になり、増加分を回復する。攻撃を受けると元の最大HPの8%を回復する。毎ラウンド2回まで。 | 20–60 字 |
| P046 | `dragon_rpg.json/status_defs/holy_blessing/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】この敵フェーズの被ダメージが0.75倍になる。 | 20–60 字 |
| P047 | `dragon_rpg.json/status_defs/magic_focus/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】次の攻撃魔法のダメージが1.3倍になる。 | 20–60 字 |
| P048 | `dragon_rpg.json/status_defs/suffocation/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】ラウンド終了時に1ダメージ。浄化で解除できる。 | 20–60 字 |
| P049 | `dragon_rpg_hybrid.json/locations/castle/actions/postgame_chat_king/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】国王と討伐後の話をする。 | 10–24 字 |
| P050 | `dragon_rpg_hybrid.json/locations/castle/actions/postgame_chat_king/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P051 | `dragon_rpg_hybrid.json/locations/castle/actions/postgame_chat_general/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】将軍ドラコと討伐後の話をする。 | 10–24 字 |
| P052 | `dragon_rpg_hybrid.json/locations/castle/actions/postgame_chat_general/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P053 | `dragon_rpg_hybrid.json/locations/castle_town/actions/postgame_chat_gald/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】行商人ガルドと討伐後の話をする。 | 10–24 字 |
| P054 | `dragon_rpg_hybrid.json/locations/castle_town/actions/postgame_chat_gald/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P055 | `dragon_rpg_hybrid.json/locations/forge/actions/postgame_chat_blacksmith/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】鍛冶師ローベルトと討伐後の話をする。 | 10–24 字 |
| P056 | `dragon_rpg_hybrid.json/locations/forge/actions/postgame_chat_blacksmith/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P057 | `dragon_rpg_hybrid.json/locations/inn/actions/postgame_chat_ian/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】イアンと討伐後の話をする。 | 10–24 字 |
| P058 | `dragon_rpg_hybrid.json/locations/inn/actions/postgame_chat_ian/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P059 | `dragon_rpg_hybrid.json/locations/inn/actions/postgame_chat_robin/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】ロビンと討伐後の話をする。 | 10–24 字 |
| P060 | `dragon_rpg_hybrid.json/locations/inn/actions/postgame_chat_robin/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P061 | `dragon_rpg_hybrid.json/locations/village/actions/postgame_chat_elder/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】長老と討伐後の話をする。 | 10–24 字 |
| P062 | `dragon_rpg_hybrid.json/locations/village/actions/postgame_chat_elder/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P063 | `dragon_rpg_hybrid.json/locations/village/actions/postgame_chat_shopkeeper/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】道具屋の店主と討伐後の話をする。 | 10–24 字 |
| P064 | `dragon_rpg_hybrid.json/locations/village/actions/postgame_chat_shopkeeper/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P065 | `dragon_rpg_hybrid.json/locations/magic_shop/actions/postgame_chat_warlock/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】青いローブの魔法使いと討伐後の話をする。 | 10–24 字 |
| P066 | `dragon_rpg_hybrid.json/locations/magic_shop/actions/postgame_chat_warlock/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P067 | `dragon_rpg_hybrid.json/locations/magic_shop/actions/postgame_chat_mina/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】ミーナと討伐後の話をする。 | 10–24 字 |
| P068 | `dragon_rpg_hybrid.json/locations/magic_shop/actions/postgame_chat_mina/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P069 | `dragon_rpg_hybrid.json/locations/item_shop/actions/postgame_chat_sarah/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】サラと討伐後の話をする。 | 10–24 字 |
| P070 | `dragon_rpg_hybrid.json/locations/item_shop/actions/postgame_chat_sarah/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P071 | `dragon_rpg_hybrid.json/locations/alley_night/actions/postgame_chat_suspicious_merchant/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】怪しい商人と討伐後の話をする。 | 10–24 字 |
| P072 | `dragon_rpg_hybrid.json/locations/alley_night/actions/postgame_chat_suspicious_merchant/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P073 | `dragon_rpg_hybrid.json/locations/elf_spring/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】精霊の泉では一度だけ休める。 | 20–60 字 |
| P074 | `dragon_rpg_hybrid.json/locations/elf_spring/choices/0/preview` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】泉で休めるのは一度だけで、休息中に襲われる恐れがある。 | 20–60 字 |
| P075 | `dragon_rpg_hybrid.json/locations/elf_spring/hybrid/summary` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】精霊の泉では一度だけ休める。 | 20–60 字 |
| P076 | `dragon_rpg_hybrid.json/locations/elf_spring/actions/rest_at_elf_spring/preview` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】泉で休めるのは一度だけで、休息中に襲われる恐れがある。 | 20–60 字 |
| P077 | `dragon_rpg_hybrid.json/locations/slime_king_battle/combat/result_texts/victory` | 过渡 | 史莱姆王胜利后 | 【仮】泉でのひと休みを終え、先へ進む。 | 20–60 字 |
| P078 | `dragon_rpg_hybrid.json/locations/village_frozen_clue/actions/visit_village_postgame/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】長老のいる村へ向かう。 | 10–24 字 |
| P079 | `dragon_rpg_hybrid.json/locations/ian_ice_katana_aftermath/actions/visit_village_postgame/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】長老のいる村へ向かう。 | 10–24 字 |
| P080 | `dragon_rpg_hybrid.json/locations/festival_town/actions/postgame_chat_gald/text` | 按钮 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】行商人ガルドと討伐後の話をする。 | 10–24 字 |
| P081 | `dragon_rpg_hybrid.json/locations/festival_town/actions/postgame_chat_gald/result_text` | 对话 | 讨伐或净化后（同时遵守 NPC 在场、原有解锁条件） | 【仮】邪竜の脅威が去った後の話をする。 | 20–60 字 |
| P082 | `dragon_rpg_hybrid.json/maps/forest/nodes/F3/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】精霊の泉では一度だけ休める。 | 20–60 字 |
| P083 | `dragon_rpg_hybrid.json/status_defs/burn/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】火傷による持続ダメージを受ける。 | 20–60 字 |
| P084 | `dragon_rpg_hybrid.json/status_defs/poison/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】層ごとに持続ダメージ。重ねると残り時間を更新する。 | 20–60 字 |
| P085 | `dragon_rpg_hybrid.json/status_defs/weaken/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】与えるダメージが0.75倍になる。 | 20–60 字 |
| P086 | `dragon_rpg_hybrid.json/status_defs/paralysis/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】25%の確率で行動できない。リソースは消費しない。 | 20–60 字 |
| P087 | `dragon_rpg_hybrid.json/status_defs/stun/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】次の行動を失い、その後2ラウンドは気絶を防ぐ。 | 20–60 字 |
| P088 | `dragon_rpg_hybrid.json/status_defs/holy_mark/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】聖属性の持続ダメージと、攻撃命中時の聖属性追撃。 | 20–60 字 |
| P089 | `dragon_rpg_hybrid.json/status_defs/blind/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】命中率が下がる。ボスと冒険者への効果は20%。 | 20–60 字 |
| P090 | `dragon_rpg_hybrid.json/status_defs/haste/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】毎ラウンドの行動回数が1増える。持続中は重ねられない。 | 20–60 字 |
| P091 | `dragon_rpg_hybrid.json/status_defs/holy_afterglow/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】次の敵フェーズ終了まで攻撃ダメージを吸収する。上限は最大HPの25%。 | 20–60 字 |
| P092 | `dragon_rpg_hybrid.json/status_defs/arcane_shield/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】一度だけ攻撃ダメージを防ぐ。 | 20–60 字 |
| P093 | `dragon_rpg_hybrid.json/status_defs/gospel/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】最大HPが2倍になり、増加分を回復する。攻撃を受けると元の最大HPの8%を回復する。毎ラウンド2回まで。 | 20–60 字 |
| P094 | `dragon_rpg_hybrid.json/status_defs/holy_blessing/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】この敵フェーズの被ダメージが0.75倍になる。 | 20–60 字 |
| P095 | `dragon_rpg_hybrid.json/status_defs/magic_focus/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】次の攻撃魔法のダメージが1.3倍になる。 | 20–60 字 |
| P096 | `dragon_rpg_hybrid.json/status_defs/suffocation/description` | 一次休息说明 | 泉/地图说明；休息按钮只在未休息且未击败史莱姆王时 | 【仮】ラウンド終了時に1ダメージ。浄化で解除できる。 | 20–60 字 |

占位总数：96。

## 补丁与合入清单

- 完整补丁：`.tmp-test/048/048.patch`（对本次 HEAD 的干净 checkout）。
- 测试补丁：`.tmp-test/048/tests.patch`（当前工作区代码已在，只需测试补丁落地）。
- 合入清单：`.tmp-test/048/files.json`；32 个文件，其中 20 个测试目标文件。
- 推荐提交信息：`[工程] 限制精霊の泉休息并补全讨伐后指引`。未生成 commit ID。
- 不合入 `.tmp-test/` 运行日志、原 playtest-* 报告、密钥或 raw 资料。
