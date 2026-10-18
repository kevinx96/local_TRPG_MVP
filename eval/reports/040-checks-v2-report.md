# 040 判定 v2 工程汇报（续做完成）

本次接续上一轮未提交的实现，依据 `docs/specs/040-checks-v2.md`、`docs/design/checks-v2.md` 和 `.codex-runs/040-continue-brief.md` 完成修复与验收。改前基线为 `50b562f`；续做开始时 HEAD 为 `bd83c0f`，两者只相差后续 E 的设计文档，未将 E 的新判定纳入本次实现。

## 1. 完成了什么

- 非战斗判定使用 `max(0, (属性−10)//2)` 加职业熟练：Lv1–3 为 +2，Lv4 起为 +3；技能决定属性，职业熟练和同伴协助读取剧本数据。判定卡与实际掷骰共用计算函数，战斗技能的 `check` 保持原实现。
- 转换两份剧本的 29 个指定选项判定、6 个观察判定及自由潜行障碍；续做补齐 `ask_ian_legend`（洞察・易，DC8）、`invite_robin`（説得・中，DC10），合计 31 个带技能的选项判定。3 个 DC999 保持不变，没有新增行动或观察判定。
- 实现线索、准备、同伴、低 HP 和警戒的优势/劣势，支持通用条件列表、抵消、双骰及采用点数日志；观察的实际掷骰结果写入 `observe_check`，同一对象成功或失败后均不重复掷骰，`dice_type: none` 保持不掷骰。
- 更新日文风险文字、判定卡技能/熟练/理由、双骰高亮和变暗、成功/失败颜色；禁用极值的行动仅显示自然点数和实际成败，不播放极值特效。CSS/JS 缓存键已更新为 `20261019-checks-v2`。
- 修复未指定角色的旧开场缺少 `str` 时抛异常的问题：有效属性缺失按 0 计算属性修正值，仍独立计入已有职业熟练；未知属性名仍报错。修复前通过原测试稳定复现两份剧本的 error，新增回归测试后验证通过。
- 迁移脚本可幂等重跑；既有风险标签和轟きの峡谷迁移脚本重跑会保留 v2 数据。同步路线模拟的概率计算与随机数注入，并重新生成 checkpoints。
- 完成全部职业、三种策略的前后对比和 32 局离线通玩；原 `eval/reports/playtest-*` 已恢复。此汇报及相关产物均使用 UTF-8 无 BOM。

原警戒机制是失败后警戒值加 1，最多 3 层，每层给后续潜行 +2 DC（最多 +6）；准备则给下一次潜行 −3 DC。现在准备和警戒分别给该障碍的下一次潜行优势/劣势，尝试后消费，失败只重新设置一份警戒，不再叠 DC。

## 2. 改动的文件

- `client/app.js`
- `client/index.html`
- `client/styles.css`
- `eval/balance/checkpoints.json`
- `host/app.py`
- `host/free_actions.py`
- `host/prompt/processed/dragon_rpg.json`
- `host/prompt/processed/dragon_rpg_hybrid.json`
- `host/prompt/processed/scenario_pack.schema.json`
- `host/state.py`
- `scripts/balance/battlefield.py`
- `scripts/balance/ch3_routes.py`
- `scripts/balance/checks_v2.py`
- `scripts/balance/class_aware.py`
- `scripts/balance/gorge.py`
- `scripts/balance/route.py`
- `scripts/scenario/checks_v2.py`
- `scripts/scenario/risk_labels.py`
- `scripts/scenario/rumbling_gorge.py`
- `tests/player_dice_roll.test.js`
- `tests/test_chapter34.py`
- `tests/test_checks_v2.py`
- `tests/test_class_aware_route.py`
- `tests/test_dragon_story.py`
- `tests/test_forest_cave.py`
- `tests/test_free_actions.py`
- `tests/test_oaksdawn.py`
- `tests/test_player_dice_roll.py`
- `tests/test_rewards_battlefield.py`
- `tests/test_rumbling_gorge.py`
- `tests/test_scenario_invariants.py`
- `tests/test_state.py`
- `eval/reports/040-checks-v2-probabilities.json`
- `eval/reports/040-checks-v2-probabilities.md`
- `eval/reports/040-checks-v2-validation.json`
- `eval/reports/040-checks-v2-report.md`

未新增依赖。`.tmp-test/`、无关素材/旧模型报告及通玩产生的 `eval/reports/playtest-*` 不纳入提交；`docs/`、默认 prompt、benchmark 标准答案与第三方原始资料没有改动。

## 3. 验证结果

| 命令 | 结果 |
|---|---|
| `python -X utf8 -m scripts.scenario.checks_v2` | 两份剧本迁移完成；幂等性由专项测试验证 |
| `python -X utf8 -m unittest discover -s tests -p test_checks_v2.py -q` | 11 项通过，覆盖修正值、熟练、等级、各优势/劣势来源与抵消、卡片与实际结算一致、观察一次性、迁移幂等和缺属性回归 |
| `python -m unittest discover -s tests -p test_state.py -k test_dragon_rpg_intro_actions_disable_after_use -q` | 1 项通过，含两份剧本子用例 |
| `node tests/player_dice_roll.test.js` | 17 项通过，0 failures |
| `python -X utf8 -m scripts.balance.checkpoints` | 退出码 0 |
| `python -m unittest discover -s tests -q` | 657 项，0 failures、0 errors、1 skipped，261.580 秒 |
| `node --check client/app.js` | 退出码 0 |
| `git diff --check` | 通过 |

全量测试的 1 项 skipped 是现有 `BALANCE_ENFORCE=1` 门控测试。第一次在 Windows 沙箱内执行时出现 35 个 `PermissionError`，全部与临时目录访问/清理有关；在沙箱外重跑同一离线命令后通过。未修改测试来掩盖权限错误，未联网调用真实模型或付费 API。

### 路线模拟

两轮均为 `dragon_valley_loc` 主线路线、每职业每策略 500 次、固定 seed `20261011`、`heuristic` 战斗策略。`none` 不休息，`hp70` 在现有休息点按 70% HP 阈值休息，`class_aware` 在此基础上按结算期望择路；它们是模拟器策略，不能直接视为真实玩家通关率。

改前使用上一轮完整保存的 `.tmp-test/checks-v2-before-routes.json`，已核对基线剧本与 `git show 50b562f:host/prompt/processed/dragon_rpg.json` 一致。改后四职业全部按最终数据重跑，实际使用 `--shards 4` 和 `--shard 0` 到 `--shard 3`，分别输出 `.tmp-test/040-continue-routes-hero.json`、`-cleric.json`、`-mage.json`、`-thief.json`。与以下不分片命令的参数和逐试验种子相同：

```powershell
python -X utf8 -m scripts.balance.route --n 500 --seed 20261011 --routes dragon_valley_loc --rest-policy all --output .tmp-test/040-continue-routes.json
```

| 职业 | none 改前 → 改后 | hp70 改前 → 改后 | class_aware 改前 → 改后 | class_aware 变化 |
|---|---:|---:|---:|---:|
| 勇者 | 67.4% → 67.4% | 67.2% → 67.2% | 62.4% → 60.2% | -2.2 个百分点 |
| 僧侶 | 49.0% → 49.0% | 49.2% → 49.2% | 58.6% → 49.4% | -9.2 个百分点 |
| 魔法使い | 46.6% → 46.6% | 28.8% → 28.8% | 30.4% → 30.6% | +0.2 个百分点 |
| 盗賊 | 36.6% → 36.6% | 27.2% → 27.2% | 37.8% → 33.2% | -4.6 个百分点 |

除了设计负责人已接受的僧侶回退，其他职业没有下降超过 5 个百分点。详细前后数据、样例轨迹和文件指纹见 `040-checks-v2-validation.json`。

**僧侶回退的设计决定：暂时接受 58.6% → 49.4%（−9.2 个百分点），本次不调整 DC 或其他数值。** 已确认原因是竜の谷入口潜行成功率从约 75% 降至 55%，模拟更多选择战斗；村入口慎重接近失败又会触发火の精霊战。设计负责人将在 040 之后的剧本改写 E 中添加僧侶专属路线（「祈りで亡霊を鎮める」，信仰・中）和侦察类优势，然后重新测量。

### 29 项无优势成功率

```powershell
python -X utf8 -m scripts.balance.checks_v2 --baseline .tmp-test/checks-v2-before-scenario.json --output eval/reports/040-checks-v2-probabilities
```

按设计第6节：29项等权、章节等级，使用剧本每级属性成长（主属性+2、次属性+1），不计装备、线索、同伴、准备与伤势。自然1失败、20成功；按数值判定计算，不把行动可选条件计入概率。
`borrow_fire_bat_dragon`禁用极值，但这张表中的属性与DC使其数值成功率与上述口径相同。

|职业|改前平均|改前仅1失败|v2平均|v2仅1失败|v2 ≤40%|
|---|---:|---:|---:|---:|---:|
|勇者|59.66%|1|55.86%|0|0|
|僧侶|80.17%|11|58.79%|0|0|
|魔法使い|78.28%|8|57.59%|0|0|
|盗賊|80.86%|13|67.76%|1|0|

|行动|技能|等级|DC|勇者|僧侶|魔法使い|盗賊|
|---|---|---:|---:|---:|---:|---:|---:|
|ask_general_advice|運動|1|10|70%|55%|55%|55%|
|ask_blue_mage_rumor|洞察|1|10|55%|70%|55%|55%|
|borrow_fire_bat_dragon|説得|1|10|65%|70%|55%|55%|
|ignore_lost_goblin|洞察|1|10|55%|70%|55%|55%|
|fort_first_bypass|隠密|2|10|55%|55%|55%|85%|
|fort_second_bypass|隠密|2|12|45%|45%|45%|75%|
|bypass_hobgoblin|隠密|2|12|45%|45%|45%|75%|
|invent_goblin_password|はったり|2|12|45%|55%|65%|55%|
|decode_seal|魔法学|2|10|55%|65%|85%|55%|
|pray_at_seal|信仰|2|10|55%|75%|55%|55%|
|force_seal|運動|2|12|65%|45%|45%|45%|
|sneak_heat|隠密|2|10|55%|55%|55%|85%|
|sneak_crystal|知覚|2|10|65%|65%|65%|55%|
|approach_burning_village_carefully|知覚|3|10|65%|70%|70%|55%|
|inspect_frost_core|調査|3|10|55%|70%|90%|55%|
|bypass_ice_elemental|魔法学|3|10|55%|70%|90%|55%|
|break_burning_beam|運動|3|10|80%|55%|55%|55%|
|climb_to_window|軽業|3|10|55%|55%|55%|90%|
|sneak_through_ash|隠密|3|10|55%|55%|55%|90%|
|sneak_bone_field|隠密|3|10|55%|55%|55%|90%|
|sneak_ghoul_marsh|隠密|3|12|45%|45%|45%|80%|
|recruit_liese_persuade|説得|3|10|65%|80%|60%|55%|
|recruit_elio_persuade|説得|3|10|65%|80%|60%|55%|
|sneak_gorge_rockfall_path|隠密|3|10|55%|55%|55%|90%|
|sneak_gorge_giant_path|隠密|3|12|45%|45%|45%|80%|
|sneak_gorge_worm_lair|隠密|3|12|45%|45%|45%|80%|
|cross_lava_bridge|軽業|4|12|45%|45%|45%|90%|
|evade_ice_sentinels|知覚|4|12|60%|65%|65%|45%|
|sneak_into_mansion|隠密|5|12|45%|45%|45%|95%|

v2 平均取整为 56%、59%、58%、68%，与设计表一致；仅自然 1 失败分别为 0、0、0、1 项，成功率 ≤40% 均为 0 项。续做新增分配的两个既有判定单独转换，不混入设计第 6 节的原 29 项等权对照表。

### 32 局离线通玩

执行 `python -m scripts.playtest.explore`：4 职业 × 默认 8 个种子，最多 250 步，32/32 局执行完毕，退出码 0。默认预算下 20 局通关、11 局结束于战斗失败或其他未通关结局、1 局触及步数上限；异常 0、非战斗死路 0、兜底叙述 0。

| 职业 | 执行局数 | 通关局数 | 异常 | 非战斗死路 |
|---|---:|---:|---:|---:|
| 勇者 | 8 | 6 | 0 | 0 |
| 僧侶 | 8 | 4 | 0 | 0 |
| 魔法使い | 8 | 5 | 0 | 0 |
| 盗賊 | 8 | 5 | 0 | 0 |

触及上限的是勇者 seed `104`：250 步时已进入竜の巣的战斗，轨迹仍正常推进。额外以同种子和 `--steps 300` 复跑，在第 262 步以 `ignis_defeated` 通关，三项不变量仍均为 0；已核对前 250 步的选项记录与原运行一致。此补跑单独记入验收 JSON，不改写上表默认 32 局的统计。

```powershell
python -X utf8 -m scripts.playtest.explore --characters hero --seeds 104 --steps 300 --output .tmp-test/040-hero104-extended/summary.md
```

曾尝试 `--workers 2`，被 Windows 沙箱的多进程管道权限拒绝，在任何通玩局启动前退出；随后使用默认串行命令完成全部 32 局。包装脚本先备份原报告，运行后把本次结果保留在 `.tmp-test/checks-v2-playtest/`，并在 `finally` 中恢复原报告；已用 Git 差异确认 `eval/reports/playtest-*` 未留改动。本次验收摘要保存在 `040-checks-v2-validation.json`，不提交临时通玩日志。

## 4. TODO(design) 清单

- 后续 E 添加僧侶的「祈りで亡霊を鎮める」（信仰・中）专属路线和侦察类优势，再测僧侶通关率。此项是续做说明指定的后续设计工作，不阻塞 040 提交。
- 上一轮遗漏的 `ask_ian_legend` / `invite_robin` 分配已由设计负责人定稿并实现；039 的禁用极值显示和成败颜色 TODO 已解决。

## 5. 推断清单

- 剧本字段采用角色的 `check_proficiencies` 数组与同伴的 `check_assistance`（`skills` / `reason`）对象；属性和同伴 ID 均沿用现有数据。职业表从角色模板读取，同伴仅在当前入队时生效。
- 理由短句沿用现有日文名词及设计示例：同伴统一为「名称の助言」，桥线索为「焦げた縄」，准备为「遮蔽の準備」，警戒为「相手の警戒」。这部分是未逐字指定的实现措辞，没有修改默认模型提示词。
- 同类来源不叠加为更多骰子；理由去重。优势和劣势抵消时仍在日志中保留理由，但卡片不显示有效优势/劣势标签，实际只掷一颗。
- 双骰同点取第一颗作为 `selected_index`；极值按被采用的点数判断。UI 使用服务端记录的采用结果。
- 带骰观察成功和失败均消费该对象的一次判定，并将结果记录为对象场景状态中的 `observe_check`；无骰观察仍遵循原有 `once` 规则。
- 缺属性按 0 处理仅放宽有效属性的缺失；不接受不存在的属性名。熟练加值独立于属性值，缺属性但已有职业熟练时仍加熟练。
- 成功率使用剧本完整逐级属性成长（主属性 +2、次属性 +1），对 29 项等权，不把行动可选条件当作概率 0；不计装备、同伴、线索、准备、伤势。禁用极值的借龙行动在这些输入下恰好与表格自然 1/20 口径给出相同数值。
- 两个补充判定放在独立的迁移映射中，避免改变指定的 29 项成功率对照集合。它们没有新增行动，技能与 DC 均直接使用续做说明。
- 原有迁移脚本重建旧选项时，需要依据 `checks_v2_v040` 标记重应用 v2，以维持跨脚本幂等；迁移后的技能风险文字也由同一格式函数生成。
- 沿用上一轮的路线终点、500 次和固定种子以便比较；四个职业分片互不改变逐试验种子。基线复用已有完整结果，最终数据全部重新跑改后模拟。

## 6. 偏离 spec 的地方及原因

- 按续做说明，僧侶下降超过原 spec 的 5 个百分点阈值仍继续完成验收；这是设计负责人的明确例外，其他职业继续执行原阈值。
- 原表遗漏的两个既有判定按续做说明补成洞察・易和説得・中，因此转换的选项数从 29 增为 31；原 29 项统计口径不变。
- 全量测试因 Windows 沙箱临时目录权限需要在沙箱外验证；通玩使用默认串行方式。没有据此修改项目实现或跳过原测试。

## 7. 已知问题

- 僧侶 `class_aware` 通关率仍有设计已接受的 −9.2 个百分点回退，等待后续 E 的路线/优势设计与再测。本次没有自行调整数值。
- 固定种子的 500 次路线模拟及 32 局离线探索是本次验收范围，不代表穷举全部玩家输入和路径；实际模型调用未纳入离线验收。
- 默认 250 步上限会截断勇者 seed `104` 的正常战斗过程；300 步预算补跑已在 262 步通关，没有发现死路。
- 本次验收未发现尚未解决的工程错误；原先缺属性的两处 error 与报告编码损坏均已解决。
