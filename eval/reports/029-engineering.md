# 029 工程汇报

## 1. 完成了什么

在包含 028（`fe71d04`）的现有 HEAD `ad2d57b` 上完成 029；保留 028 之后的已有提交。

- 两份剧本同步修正砦入口、迷子のゴブリン存亡与还箱状态。王被击败后不能再进入砦；死亡的ゴブリン不再出现在选项、立绘、地点说明或当前 NPC 上下文里；遗留箱只提供一次非战斗取物。
- 逐字录入 spec 的结果、判定分支、战前、设施进场和文体修正文案；替换 demo fallback。删去引擎接管后无法到达的三个旧竜の谷动作及 prepared turn：`dragon_valley_ice_amulet`、`dragon_valley_sword_attack`、`dragon_valley_defend`。
- 调整城下町往返、地图出口、设施标题、无判定出发、イアン判定、强制失败风险标签、重复 preview 和青衣同伴离队条件。
- public session 的选择沿用客户端字段白名单；动作结果额外收紧，整个返回对象递归移除六类结算字段。内部引擎数据保留。
- 新增入口快照、真实战败后的重来 API 和结束画面按钮；恢复进入时的原样，保留历史，累计重来次数并写 trace。
- 移植 app 层离线探索脚本，加入状态、文本、公开字段、路线与重来回归测试；完成八局逐步试玩记录和与 028 同口径的平衡复跑。

### public 字段

核对 `client/app.js` 的 `renderChoices`、`onChoicesClick`、`renderSession` 和立绘渲染路径后，choices 保留以下字段：

| 字段 | 用途 |
|---|---|
| `id`、`action_id` | 提交动作 ID，`id` 是旧数据的回退来源 |
| `text`、`preview`、`risk` | 选项标题、说明、风险 |
| `enabled`、`disabled_reason`、`visibility` | 可选择状态、原因和未知选项显示 |
| `children` | 嵌套选项，递归使用同一白名单 |
| `open_shop` | 保留既有商店界面标记；探索脚本也据此排除开店动作 |

真正触发商店弹窗的是 `last_action_result.open_shop` 与 `event_id`；该对象仅保留 `action_id`、`event_id`、`open_shop`。立绘继续使用 session 顶层的 `location_portrait_image`、`player_portrait_image`、`location_npc_portraits`、`dialogue_portrait_image`、`active_portrait_image`，没有新增选项立绘字段。返回对象任意深度均不得出现 `effects`、`success_effects`、`failure_effects`、`roll_bonuses`、`result_text`、`result_texts`。

### 入口快照与恢复

快照字段为 `character`、`world_state`、`flags`、`companion`、`completed_milestones`、`visited_locations`、`shop_stock`、`known_item_names`、`scene_changes`、`opening_effects_applied`、`next_dice_type`、`next_dice_dc`。`character` 包含资源、属性、技能、装备、背包与金币；当前任务由 flag、物品和里程碑推导，地点与场景由 `world_state` 保存。

不快照 `scenario_pack`、消息、系统日志、事件日志、骰子记录、trace、战斗实例或快照索引本身。重来清除 `game_over`、旧战斗、旧动作/战斗结果、临时战斗请求和自由行动/意图状态，重新生成选项；入口若为自动战斗地点，正常创建新的战斗。已知物品从快照恢复，不从保留的后续事件日志重新“学会”。

`retry_count` 保留累计；trace 的 `call_type=area_retry`，记录 `session_id`、时间、`gm_mode`、turn、区域 ID、死亡地点、恢复地点和次数。GM 叙述及系统日志采用 spec 原文。

## 2. 改动的文件

| 范围 | 文件 |
|---|---|
| 运行时 | `host/area_retry.py`、`host/state.py`、`host/app.py`、`host/combat.py`、`host/maps.py`、`host/scenario_context.py` |
| 客户端 | `client/app.js`、`client/index.html` |
| 剧本与迁移 | `host/prompt/processed/dragon_rpg.json`、`dragon_rpg_hybrid.json`；`scripts/scenario/playtest_fixes.py`、`risk_labels.py` |
| 路线与生成数据 | `scripts/balance/checkpoints.py`、`class_aware.py`、`forest_v3.py`；`scripts/scenario/key_items.py`、`redundancy.py`；`eval/balance/checkpoints.json`、`eval/scenario/key_items.json` |
| 验证工具 | `scripts/playtest/explore.py`、`audit.py`；`scripts/balance/playtest_report.py` |
| 测试 | `tests/test_area_retry.py`、`test_playtest_fixes.py`、`test_castle_town.py`、`test_dragon_story.py` |
| 报告 | 本文；`playtest-2026-10-13.md/.json`、同名目录内八份逐步 Markdown、`playtest-2026-10-13-audit.json`、`balance-2026-10-13-playtest.md/.json` |

没有新增依赖。用户原有的 `.claude/launch.json` 修改未纳入提交。没有改动默认提示词、benchmark 标准答案、设计文档、密钥或第三方 raw 资料。

## 3. 验证结果

| 命令 | 输出摘要 |
|---|---|
| `python -m unittest discover -s tests -q` | `Ran 521 tests`；`OK (skipped=1)` |
| `node --check client/app.js` | 退出码 0 |
| `python -m scripts.playtest.explore` | 8 局；无异常、非战斗死路或 2.1 兜底文本 |
| `python -m scripts.playtest.audit` | 两份剧本扫描完成；清单见下节与审计 JSON |
| `python -m scripts.balance.checkpoints` | 检查点重新生成，既有可达性测试通过 |
| `python -m scripts.scenario.key_items` | 关键物品路线重新生成，既有冗余/可达性测试通过 |
| `python -m scripts.balance.class_aware --n 500 --seed 20261012 --workers 20 --output eval/reports/balance-2026-10-13-playtest.json` | 4 职业 × 5 策略 × 500，共 10,000 次离线模拟 |
| `python -m scripts.balance.playtest_report` | 与 028 的 N、seed、职业支线一致性检查通过，生成逐组比较 |
| `git diff --check` | 通过 |

回归覆盖双方剧本的入口封闭、ゴブリン消失/箱内物品、设施进场、同伴条件文本、无叙述例外清单、递归私有字段剔除、城下町返回与地图显示、迁移幂等、八局探索，以及开局/跨图/子图快照、完整状态恢复、历史保留、重复重来、无地图地点、剧情结局和 scripted_loss 排除。

[试玩报告](playtest-2026-10-13.md)：3 局 `ignis_purified`、2 局 `ignis_defeated`、2 局重来后战败、1 局达到 150 步上限。首次死亡共 4 局，地点各为 `goblin_fort_fourth`、`village_fire_elemental`、`dragon_valley_loc`、`frost_wolf_battle`；其中重来后 2 局抵达剧情结局、2 局再次战败。

[平衡报告](balance-2026-10-13-playtest.md)：20 组中 13 组所有聚合指标逐项相同，通关率变化范围为 −1.2 至 +0.2 个百分点。固定路线的出发原来已强制成功，所以删除判定没有额外提高这些组的通关率。到达森の出口即设置返回 flag，改变了 class_aware 局部评估使用的可见状态哈希/稳定种子；不能把这些小幅变化归因为战斗数值调整。本次没有调整伤害、HP、奖励、成长或价格。

## 4. TODO(design) 清单及文本审计

### 4.1 不移动地点且没有任何准备文本

TODO(design)：以下五项仅在 `dragon_rpg.json` 中缺少 `result_text(s)` 或匹配的 prepared draft；hybrid 包已有文本。本次没有代写，测试明确列为例外。

| 地点 | 动作 | 分支 |
|---|---|---|
| `castle` | `ask_king_info` | neutral |
| `forge` | `ask_blacksmith_weakness` | neutral |
| `forge` | `show_sword_to_blacksmith` | neutral |
| `forge` | `accept_sword_fusion` | neutral |
| `inn` | `ask_robin_rumor` | neutral |

另有以下双方共有的机制例外，全部列入测试，不另写叙述：

- 开店动作 6 项：`forge/open_forge_shop`、`village/open_village_shop`、`village/open_gald_shop`、`magic_shop/open_magic_shop`、`item_shop/open_sarah_shop`、`festival_town/open_gald_capital_shop`；直接打开商店界面。
- 不可达成功分支 3 项：`xanxus_confrontation` 下 `bluff_xanxus`、`ambush_xanxus`、`flee_from_xanxus` 的 success；1d20/DC999 且关闭暴击，实际只会走已有文本的失败分支。
- `game_over` 自带结束文本、free_action 走现有自由行动叙述管线，不作为缺文。扫描结果没有额外的 `silent` 例外。

### 4.2 敌人数量扫描

两份剧本各得到相同的 6 处候选。逐项核对 encounter 后，**确认的剩余数量不符为 0**；未改任何候选文本。正则只筛出显式数量词，不能证明所有自然语言都不存在不符。

| 候选位置 | 自动比较与人工核对 |
|---|---|
| `slime_ambush_one.combat.result_texts.victory` | 两个“一匹”分别指刚击败的敌人和下一波新敌人；每波各一只，不能相加作为本场数量 |
| `goblin_fort_third_gate/password_bluff_success` | “ゴブリン王と一匹の弓兵”合计 2，符合四层王战；警备战是失败分支 |
| `goblin_fort_third_gate/password_bluff_failure` | “一匹の大ゴブリン”符合失败分支警备战；四层王战是成功分支 |
| `goblin_fort_third_guards.combat.result_texts.victory` | 一名刚击败的警备兵与下一场的王、弓兵，属于连续两场遭遇 |
| `goblin_fort_fourth.description` | 王与一名弓兵合计 2；显式“一匹”仅修饰弓兵 |
| `xanxus_ultimatum/warlock_rescue` | “二人の魔法使い”包括客串操作角色ワーロック和敌方 Xanxus，enemy_ids 只有敌方一人 |

### 4.3 仍为です・ます体的地の文

TODO(design)：两份剧本以下 13 个地点的 `combat.result_texts.defeat` 仍使用“……で力尽きました。冒険はここで終わりを迎えます。”，保留原文：

`dark_forest_loc`、`lost_goblin_crossroads`、`forest_wolves`、`slime_ambush_one`、`slime_ambush_two`、`slime_king_battle`、`goblin_fort`、`goblin_fort_first_second`、`goblin_fort_second_right`、`goblin_fort_second_left`、`goblin_fort_third_guards`、`goblin_fort_fourth`、`goblin_fort_chest_fight`。

TODO(design)：仅 hybrid 包的 `dragon_valley_loc.hybrid.prepared_turns.dragon_valley_opening.draft.gm_text` 仍有“姿を現します”“漏れ出ています”“いよいよ決戦の時です！”。此条不在 spec 允许删除的三个旧动作内，未自行改写。

扫描剔除了「」和『』内的人物对白后检查敬体句尾；full 包 13 条，hybrid 包 14 条，去重后 14 处。具体全文和字段路径见 [审计 JSON](playtest-2026-10-13-audit.json)。

### 4.4 重来后的再次死亡

TODO(design)：`hero / seed 20261014` 首次第 81 步、重来后第 100 步均死于 `goblin_fort_fourth`。砦入口快照 HP 为 17/20。首次走左侧并使用法阵，重来后走右侧、经过警备战。这里只标为重复死亡候选；两条路线不同，不能据此证明入口状态必死或无法离开，也没有自行调整恢复量或数值。逐步记录为 [hero-20261014.md](playtest-2026-10-13/hero-20261014.md)。

## 5. 推断清单

- “区域”沿用地图要求与现有地图选择规则：同一地点同时属于父图和子图时，重来优先选子图；进入子图仍保存父图原入口快照。只在真正从该图外进入时覆盖该图快照。
- 无地图地点使用 `location:<location_id>` 保存最近一次抵达状态，叙述中的区域名称使用已有地点标题。开局按一次入图处理，开场物资生效后刷新快照。
- 入口快照在地点迁移、entry_effects、物品 flag、可见动作及任务变更全部应用后保存，自动开战之前保存。恢复不回满 HP，也不回滚历史、累计重来次数或随机流。
- 真实战败由引擎添加 `game_over.combat_defeat` 标记，并验证战斗结果及 scripted_loss；避免根据结局文案或 ending 名称猜测。
- 没有快照的旧存档不凭空重建过去的入口状态；进入新的区域后才开始获得快照。新 API 对当前不可重来的请求返回 409，不存在的会话返回 404。
- 死亡ゴブリン沿用现有 `combat_defeated:lost_goblin_crossroads:goblin`；空箱主人状态使用既有 `resolved_lost_goblin_box`。取物沿用箱内的「縮小の銃」和 `stole_shrinking_gun` 标记，保持既有奖励/任务判断。
- ゴブリン消失后的十字路说明置空；财宝箱地点使用 spec 箱子叙述的第一句作为状态说明，避免保留 NPC 在场文字，没有补写新叙事。
- “到过森の出口”复用 `returned_from_forest`，改为进入该地点时设置；升级旧存档时从 `visited_locations` 补回。删除返回动作中重复设 flag 后，它继续使用既有纯导航静默机制。
- capital 地图新增两个 `exit` 节点，位置为 `(90,94)` 与 `(10,94)`，沿用已有地图样式；`location_ids=[]`，以免把远处森林/村庄误划进首都区域。`known_after` 复用返回通路 flag 控制节点名称显示。
- 两份包中原本缺少 spec 指定 prepared turn 的，按现有绑定方式新增；已有的则替换原文。三个旧竜の谷 prepared turn 对应的非引擎动作一并移除，避免保留无法使用的旧选项。
- 8 局采用现有默认 semi 模式和日期种子 20261013/20261014；每次战斗指令、战斗结算、重来各算一步。每局仅首次真实战败重来一次；保留选项尝试次数和随机流。API 接口被直接调用，未经过 HTTP 网络栈。
- 离线 LLM 地址设为不可达本地端口，并在请求适配器直接抛出连接失败，再禁止 requests 网络，确保不受用户本地模型服务影响。状态、战斗与探索选择随机数分别固定。
- “最远地点”以主线章节和地图节点顺序排序；同章支线没有唯一叙事顺序，所以同时记录全部到访地点。
- 平衡复跑保持 028 的 N/seed/职业支线和原休息机会，通过显式进出宿屋适应新路线。关键物品可达性 witness 不再先杀死ゴブリン又要求其还箱；改为保留其存活的合法路线，不改物品来源标准或阈值。
- 扩展公开结果的递归剔除覆盖战斗 special、自由行动结果等嵌套位置；入口快照不下发客户端。任务与地点显示从恢复状态重新计算。

## 6. 偏离 spec 的地方及原因

- 结束画面原有按钮在 028 中实际为「タイトルへ戻る」。本次保留该按钮与行为，按 spec 新增「このエリアの入口からやり直す」，未把旧按钮改成正文泛称的「新しい冒険」。
- 没有新增功能范围或调整数值目标。缺文、敬体及重复死亡候选按要求留清单；删除三个旧竜の谷动作属于 spec 明确允许的处理。
- 全量 unittest 与多进程模拟在当前 Windows 沙箱下遇到临时目录权限/命名管道限制，使用已获自动批准的完整本机权限运行；仍禁用真实模型及付费 API。未改用户配置绕过测试。

## 7. 已知问题

- 八个固定种子覆盖的是默认 semi 路径，不能证明所有状态都可达或绝无死路；full 模式仍依赖模型叙述，五项数据缺文已明确列出。
- 有 1 局达到 150 步上限，没有抵达结局；另有 1 个重复死亡候选尚不能判定为必死循环。
- 旧存档缺少历史入口快照时不能立即重来；不捏造历史 HP/库存。
- 当前环境没有可连接的浏览器，未进行实际结束画面点击/视觉验收。API 行为和显隐所依赖的公开状态有测试，客户端语法检查通过。
- 数量词和文体审计是确定性候选扫描加人工核对，不是完整的自然语言一致性证明。
