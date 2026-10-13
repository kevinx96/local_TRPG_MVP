# 015 森林地图化、封印洞窟与 NPC 支线验收（2026-10-12）

## 1. 完成内容与验收口径

已实现三张地图及移动 API、F1–F5 主线、C0–C5 洞窟、虹晶樹轮换、四种虹晶武器、四条 NPC 支线、折扣和购买记录。两份剧本同步；没有调用网络、付费 API 或生图工具，没有改默认提示词。美术仅引用 016 的未来文件名，缺图显示占位。

功能验收和数值验收分开记录。数值未达到目标的项目保留失败结果，不把未达标改写为通过。原始数据见 [本次模拟](balance-2026-10-12-forest-v3.json) 与 [修改前基线](balance-2026-10-12-forest-v3-before.json)。

每格 N=500，seed=20261012，heuristic，完全离线。500 次样本在 50% 附近的 95% 抽样误差约 ±4.4pp；当前数值经过该种子校准，尚未做独立种子的外部验证。

- Lv1：初始角色 + 初始补给 + 青いローブの魔法使い；不领取途中胜利奖励。
- Lv2：通过 F4 的可达装备快照。勇者保留鉄の剣；僧侶/盗賊在 F3 取得光苔，回城交付、卖一份携帯食，以 64G 购入氷の護符；魔法使い使用职业技能。C4/C5 先完成 C3a，装备紅玉の護符。快照的每一步来源保存在 `eval/balance/checkpoints.json`。
- 单场 HP/MP/SP 回满，前置战斗假定胜利；Lv1 与 Lv2 不仅等级不同，装备与途中奖励也不同，不能把两列差异解释成纯等级因果效应。
- 虹晶武器：Lv5 イグニス快照上只替换武器，关闭净化策略，不加入ミーナ加工加成；保留原背包与技能。与当前可达装备比较，并非与裸装或初始鉄の剣比较。
- 连续路线不隐式补血、不自动购买、不自动宿泊。全支线路线确实经历砦与洞窟战斗；另设“奖励条件对照”：F5 注入交付所需材料，调用真实任务交付与打造动作取得奖励，排除取得成本后继续同一主线。条件对照不是一条实际可达的无成本路线，只用于检查奖励强度，不能与完整支线成功率混为一谈。

### 洞窟单场胜率

| 遭遇 | 等级 | 勇者 | 僧侶 | 魔法使い | 盗賊 |
|---|---|---:|---:|---:|---:|
| C1 熱気の回廊 | Lv1 | 31.0% | 1.8% | 62.6% | 3.4% |
| C1 熱気の回廊 | Lv2 | 87.4% | 89.2% | 86.2% | 76.2% |
| C3a 溶岩の小部屋 | Lv1 | 37.4% | 2.2% | 28.6% | 1.0% |
| C3a 溶岩の小部屋 | Lv2 | 84.6% | 89.0% | 85.6% | 84.2% |
| C4 水晶の回廊 | Lv1 | 1.8% | 0.2% | 7.4% | 0.2% |
| C4 水晶の回廊 | Lv2 | 77.2% | 82.8% | 75.2% | 80.6% |
| C5 虹晶樹 | Lv1 | 0.4% | 0.2% | 17.8% | 0.0% |
| C5 虹晶樹 | Lv2 | 73.6% | 74.4% | 60.4% | 65.8% |

Lv2：elite 目标 75–90%，boss 目标 60–75%；Lv1 虹晶樹目标严格低于 35%。

### 虹晶武器对イグニス的提升

| 职业 | 原装备 | 虹晶武器 | 提升 | 10–20pp 目标 |
|---|---:|---:|---:|---|
| 勇者 | 88.0% | 91.8% | +3.8pp | 未通过 |
| 僧侶 | 76.0% | 87.8% | +11.8pp | 通过 |
| 魔法使い | 73.2% | 73.2% | +0.0pp | 未通过 |
| 盗賊 | 81.2% | 82.8% | +1.6pp | 未通过 |

数值：虹晶の剣 `3d6+str/3`，虹晶の杖 `1d20+wis/3`，虹晶のオーブ `1d20+int/3`，虹晶の短剣 `4d4+dex/4`；基础命中 92%，ミーナ加工后 95%。普通攻击自动选择弱点，杖治疗 +2。

### 连续主线：修改前 → 修改后

| 职业 | 修改前 | 新主线，无支线奖励 | 实际走砦＋洞窟＋交付 | 奖励条件对照 |
|---|---:|---:|---:|---:|---:|
| 勇者 | 83.4% | 83.4% | 50.0% | 95.8% |
| 僧侶 | 62.4% | 62.4% | 0.8% | 87.0% |
| 魔法使い | 62.6% | 62.6% | 1.2% | 76.8% |
| 盗賊 | 44.4% | 44.4% | 0.0% | 83.6% |

实际支线路线低成功率包含取得奖励的成本，不能据此宣布奖励强度合格。奖励条件对照揭示勇者、僧侶、盗賊超过 80%；勇者即使取消全部新奖励也已经超限。原奖励数量与正文保持设计给定值，待设计裁定原主线基线与固定奖励的冲突。

### 最终数值门禁

共 7 项未通过：

| 指标 | 职业 | 实测 | 目标 |
|---|---|---:|---|
| 虹晶武器提升 | 勇者 | +3.8pp | 10–20pp |
| 虹晶武器提升 | 魔法使い | +0.0pp | 10–20pp |
| 虹晶武器提升 | 盗賊 | +1.6pp | 10–20pp |
| 无奖励主线基线 | 勇者 | 83.4% | ≤80% |
| 奖励条件对照 | 勇者 | 95.8% | ≤80% |
| 奖励条件对照 | 僧侶 | 87.0% | ≤80% |
| 奖励条件对照 | 盗賊 | 83.6% | ≤80% |

### 新敌人数值

| 敌人 | HP | 防御 / 回避 | 主攻击 | 命中 |
|---|---:|---|---|---:|
| 熱岩トカゲ | 18 | 1 / 5 | `2d5+1` | 86% |
| 炎のウィスプ | 12 | 0 / 30 | `1d7` | 100% |
| 紅晶ゴーレム | 33 | 2 / 0 | `1d12` | 75% |
| 蒼晶の蝶 | 9 | 0 / 30 | `1d3` | 85% |
| 翠晶の蜘蛛 | 12 | 0 / 10 | `1d3` | 85% |
| 虹晶樹 | 130 | 2 / 0 | `1d14` | 78% |

虹晶樹每三回合用 `1d6` 回复代替攻击；枝打ち与結晶の雨均为 `1d14`、78% 命中。轮换既定抗性维持 0.25、弱点维持 1.5，额外物理抗性 0.6、聖抗性 0.75；翠阶段额外冰抗性 0.5。其他新敌人火抗性：トカゲ 0.25、ウィスプ 0.8、ゴーレム 0.35；紅晶の拳与熱線均为 `1d12`、75% 命中。

## 2. 完整森林连接表

以下是地点移动；接任务、交物品、观察、休息等没有改变地点的动作另列说明。地图只调用表中已有动作，并继续检查当前地点、战斗状态、flag 与动作条件。

| 节点 | 动作 / 结算 | 去向 |
|---|---|---|
| F1 `dark_forest_loc` | スライム战斗胜利；自由行动诱导/潜行成功；`pass_cleared_forest` | F2 |
| F2 `lost_goblin_crossroads` | `help_lost_goblin` | 留在 F2，接任务 |
| F2 | `ignore_lost_goblin` 引出的战斗胜利 | 留在 F2 |
| F2 | `crossroads_forward` | F3 |
| F2 | `enter_goblin_fort`（已接箱子任务） | 砦一层 |
| F2 | `fort_shortcut`（箱子处理完毕且已经通过 F4） | F5 |
| F2 | `crossroads_back` | F1 |
| F3 `elf_spring` | `rest_at_elf_spring`（未打败スライム王） | 袭击第一波 |
| 袭击第一波 | 战斗胜利 | 第二波 |
| 袭击第二波 | 战斗胜利 | スライム王 |
| スライム王 | 战斗胜利 | F3 |
| F3 | 王已败后再次 `rest_at_elf_spring` | 留在 F3，全回复 |
| F3 | `continue_from_elf_spring` | F4，先遭遇，尚不开战 |
| F3 | `inspect_spring_wall` | C0 |
| F3 | `spring_back` | F2 |
| F4 `forest_wolves` | `fight_forest_wolves` 后胜利；`distract_forest_wolves` / `sneak_forest_wolves` 成功 | F5，救下ガルド，触发 Lv2 |
| F4 | `abandon_gald` | F5，放弃ガルド，触发 Lv2 |
| F4 | `pass_cleared_wolves` | F5 |
| F4 | `wolves_back` | F3 |
| F5 `forest_exit` | `leave_forest_for_village` | `village_approach` |
| F5 | `return_inn_after_forest` | `inn` |
| F5 | `exit_back` | F4 |
| 砦 `goblin_fort` | 胜利 / `fort_first_bypass` 成功 | `goblin_fort_first_second` |
| `goblin_fort_first_second` | 胜利 / `fort_second_bypass` 成功 | `goblin_fort_second_choice` |
| `goblin_fort_second_choice` | `explore_fort_right` / `explore_fort_left` | `goblin_fort_second_right` / `goblin_fort_second_left` |
| `goblin_fort_second_right` | 胜利 / `bypass_hobgoblin` 成功 | `goblin_fort_third_gate` |
| `goblin_fort_second_left` | 胜利 | `goblin_fort_healing_circle` |
| `goblin_fort_healing_circle` | `use_fort_healing_circle` | `goblin_fort_third_gate` |
| `goblin_fort_third_gate` | `give_correct_password` / `invent_goblin_password` 成功 | `goblin_fort_fourth` |
| `goblin_fort_third_gate` | `invent_goblin_password` 失败 / `admit_no_password` | `goblin_fort_third_guards` |
| `goblin_fort_third_guards` | 胜利 | `goblin_fort_fourth` |
| `goblin_fort_fourth` | 胜利（获得刻印のハンマー） | `goblin_fort_chest_choice` |
| `goblin_fort_chest_choice` | `return_lost_goblin_box` | F2 |
| `goblin_fort_chest_choice` | `steal_lost_goblin_box` | `goblin_fort_chest_fight` |
| `goblin_fort_chest_fight` | 胜利 | F2 |
| C0 `cave_seal` | `decode_seal` / `pray_at_seal` / `force_seal` 成功；`pour_holy_water_on_seal`；封印已破后的 `enter_open_cave` | C1 |
| C0 | 上述判定失败 | 留在 C0，扣 SP 或 HP |
| C0 | `leave_seal` | F3 |
| C1 `cave_heat_corridor` | `fight_heat` 后胜利；`sneak_heat` 成功；`pass_heat_corridor` | C2 |
| C1 | `sneak_heat` 失败 | 留在 C1，开战 |
| C1 | `heat_back` | C0 |
| C2 `cave_fork` | `cave_left` / `cave_right` / `fork_back` | C3a / C3b / C1 |
| C3a `cave_lava_room` | 战斗胜利；`open_lava_chest` | 留在 C3a，宝箱只能领取一次 |
| C3a | `lava_back` / `lava_forward` | C2 / C4 |
| C3b `cave_hot_spring` | `rest_hot_spring`、与ミーナ交谈/同行/等候 | 留在 C3b |
| C3b | `hot_spring_back` / `hot_spring_forward` | C2 / C4 |
| C4 `cave_crystal_corridor` | `fight_crystal` 后胜利；`sneak_crystal` 成功；`pass_crystal_corridor` | C5 |
| C4 | `sneak_crystal` 失败 | 留在 C4，敌人先手开战 |
| C4 | `crystal_back` | C2 |
| C5 `cave_prism_tree` | 胜利，获得虹晶の欠片 | 留在 C5，开放回程 |
| C5 | `leave_prism_tree` / `prism_back` | F3 / C4 |
| C1 / C3a / C4 / C5 | 战败 | HP=1，返回 F3，不 game over，可重试 |

## 3. 文件与验证

- 引擎：`host/maps.py`、`host/app.py`、`host/world_state.py`、`host/state.py`、`host/combat.py`、`host/free_actions.py`、`host/shops.py`、`host/quests.py`、`host/scenario_context.py`、`host/prompt/processed/scenario_pack.schema.json`。
- 前端：`client/app.js`、`client/styles.css`、`client/index.html`（静态资源版本 `20261012-forest-v3`）。
- 数据：`host/prompt/processed/dragon_rpg.json`、`dragon_rpg_hybrid.json`、`eval/balance/checkpoints.json`、`eval/balance/targets.json`、`eval/scenario/key_items.json`。
- 生成与评测：`scripts/scenario/upgrade_forest.py`、`upgrade_sidequests.py`、`tune_forest.py`、`key_items.py`、`redundancy.py`，并为 `upgrade_purification.py` 加入已迁移剧本保护；`scripts/balance/checkpoints.py`、`sim.py`、`forest_v3.py`，`scripts/screenshot_services.py`。
- 新测试：`tests/test_maps.py`、`test_forest_cave.py`、`test_forest_sidequests.py`、`test_forest_balance.py`；同步修改旧路线/商店/素材检查的断言。

| 命令 | 结果 |
|---|---|
| `python -m unittest discover -s tests -q` | 403 tests，OK，skipped=1；约 71 秒 |
| `node --check client/app.js` | 退出码 0 |
| `python -m scripts.scenario.redundancy` | spring / fort / cave 三路线，`errors: []` |
| `python -m scripts.scenario.redundancy --scenario host/prompt/processed/dragon_rpg_hybrid.json` | 三路线，`errors: []` |
| `python -m scripts.screenshot_services --output .codex-runs/forest-v3-ui` | 九个场景的自动检查通过；新增五张截图均人工查看 |
| `python -m scripts.balance.forest_v3 --n 500 --check` | 数值门禁不通过；未达标项见上表及 JSON `violations` |
| `git diff --check` | 通过 |
| C4 潜行失败单独检查 | 启动战斗时执行一次敌人先手阶段，并清除请求 flag |

测试在默认无网络、无模型调用模式执行；Windows 现有测试会写系统临时目录，执行时使用受审批的本机权限。两份剧本的新版地图、敌人、支线和物品数据保持同步。

末次勇者武器平均伤害调整后，单独复算受影响的勇者武器对照、实际支线路线与奖励条件对照，其余有效结果复用；原始 JSON 记录该增量复算与文件指纹。伤害档次以相同职业属性下的骰式期望比较，在 Lv2/Lv5 均满足鉄の剣 < 虹晶武器 < 氷の太刀。

截图及自动检查：[森林全屏地图](forest-v3-ui/forest-map.png)、[砦小地图](forest-v3-ui/fort-map.png)、[洞窟小地图](forest-v3-ui/cave-map.png)、[虹晶樹战](forest-v3-ui/prism-battle.png)、[手机宽度地图](forest-v3-ui/forest-mobile.png)、[检查记录](forest-v3-ui/checks.json)。

## 4. TODO(design)

1. 近路与必经里程碑冲突：F2→F5 会绕开“主线上必经的 F4”。目前近路要求先通过 F4，再允许使用；请确认这一条件，或另行指定跳级规则。
2. 虹晶武器对已有装备/技能的比较基线未明确。当前按可达 Lv5 checkpoint 比较；普通攻击档次限制下，不能保证四职业均提升 10–20pp。魔法使い仍优先使用更强的「氷の矢・改」。是否允许增加技能伤害效果已提请裁定，尚未获得答复，故未加入该效果。
3. 勇者未加入新奖励的连续主线基线已为 83.4%，超过 80%。削减新奖励无法消除这一基线超限。需要设计明确是否调整原主线或验收基线；本任务没有擅改原主线敌人。
4. 新支线固定奖励（8 折、MP回復薬×2、アダマンタイトの鎧）与连续路线强度上限一起评估，详见数值表。任何未达标仍记录为失败；没有借助取得奖励途中的高失败率隐藏奖励本身的强度。
5. Lv2 推荐配装、回城采购和同伴路线为工程提出的可达快照，请审定其是否代表目标玩家；全部支线连续不补给的路线不是推荐攻略。

## 5. 推断清单

- 未提供的 action ID、intent_keywords、preview、判定失败提示、地图错误提示沿用现有词汇；新增动作一般以按钮文字作为 preview/关键词。已提供的地点、物品、敌人、NPC、任务与结果正文逐字录入。
- 增加 F5→F4→F3、F3→F2→F1 与洞窟回程动作，支撑 Lv2 返回洞窟、打完王后接回ミーナ；王已败后泉休息不再次进入已清空的袭击。
- 使用 `passed_forest_wolves` 触发 Lv2；完成砦并通过 F4 才可用近路，近路未开启前不参与地图相邻可见性计算。
- 多地点节点按任一地点已访问来显示；最具体子地图优先。封印入口发现前保持问号，访问后显示锁；地图移动边按有向动作执行，显示相邻性按无向连接判断。
- C1/C4 潜行成功记录对应通过 flag，后续允许直行，但不发放胜利奖励。ガルド的放弃选项按无骰移动实现。
- C1/C3a/C4 败北复用“気がつくと泉のほとりに倒れていた。”；C5 使用文档完整败北文。洞窟败北保持可重试。
- 温泉的 50% 回复向下取整并受最大值上限约束；一次性物品/观察用 flag 防重复领取。紅玉の護符与任务奖励鎧自动装备。
- 冰系凍え降低命中 15、持续两回合；火傷与毒每回合伤害 1、持续两回合。新敌人 HP/伤害/命中/闪避/额外抗性详见最终 JSON 与 `tune_forest.py`，既定轮换属性倍率保持 0.25/1.5。
- `counter` 优先沿用主属性克制关系，同倍率时保留该元素；存在更高显式弱点时选最高倍率，兼顾イグニス的冰弱点与虹晶樹轮换。确定性引擎和 heuristic 的预估保持一致。
- ミーナ每两回合随机选存活敌人造成 1d6 冰伤；同行替换现有同伴，不叠加。她的加工小加成为武器命中 +3；僧侣虹晶杖治疗 +2。
- 店铺折扣按整数向下取整，最低 1G；卖价取现有商店当前最低买价的一半，避免折扣与ガルド低价产生套利。`on_purchase_flag` 只在成功购买后设置，可设在店铺或单一商品上。
- “已经买过鎧”使用购买 flag，即使后来出售仍给 100G；旧会话仍持有鎧时也按替代奖励处理。任务完成 flag 可使未接过的サラ任务直接显示为已完成。
- NPC 的出现按地点条件过滤；请求和交付沿用现有商店页面的动作结构；ガルド王城对话放入现有城下町探索子动作。
- 图片缺失采用现有颜色变量的虚线占位；图片 URL 保持未来约定名称，不修改素材清单来伪造已有素材。
- 评测使用确定性成功判定建立前置装备快照；连续模式只沿用预设非战斗判定结果，战斗由引擎实际结算。模拟不是任意自由文本 GM 交互的成功率。

## 6. 偏离与已知问题

- 为保留 F4 必经里程碑，近路增加前置通过 F4 的条件，属于上列待裁定的冲突处理。
- 数值目标的未达标项见原始报告 `violations` 与数值表。功能验收通过不等于全部数值目标通过。
- 没有生成美术。截图里洞窟背景和新敌人显示占位，待合入 `art/016` 后由正常 URL 加载；当前浏览器会在失效图片占位左上角同时显示缺图图标。
- 已有旧存档若买过鎧又卖掉，且没有保留购买 flag，不能凭空重建购买事实；仍持有鎧的旧存档可识别。地图访问记录从已有位置历史和事件记录恢复。
- 没有新增依赖；截图使用本机已有 Chromium/Edge 和原截图脚本，自动化不访问外网。
- 两份剧本原有的旧物品 `effect` 文案和イグニス描述差异保留；本次新增内容与战斗数值同步，没有顺手改动旧正文。

## 7. 提交

1. `70a86fd` `[工程] 实现地图可见性、访问记录和地图移动界面`
2. `fb3025c` `[工程] 重构森林主线并加入封印洞窟与虹晶武器`
3. `8b473e9` `[工程] 接入四条 NPC 支线、商店折扣与购买记录`
4. 本报告所在提交：`[工程] 校准洞窟数值并完成地图支线离线验收`
