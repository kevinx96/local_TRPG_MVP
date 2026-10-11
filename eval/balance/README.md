# 离线战斗模拟

所有命令只调用确定性游戏引擎，不读取 LLM 配置、不发送模型请求，无新增依赖。

```powershell
# 从剧本动作、跳转和奖励重新推导 proposed checkpoint
python -m scripts.balance.checkpoints

# 默认 21 遭遇、所有可选职业、heuristic、N=500、flat
python -m scripts.balance.sim --output .tmp-test/balance.json

# 自选矩阵；guest 遭遇自动替换为 player_character_id，且只计算一次
python -m scripts.balance.sim --encounters forest_wolves slime_king_battle --characters hero mage --policies all --n 500 --seed 20261011 --defense-mode ratio

# 无 checkpoint 的初始模板、无同伴，探索成长（仅修改模拟会话）
python -m scripts.balance.sim --encounter forest_wolves --character hero --checkpoint none --no-companion --stat-scaling '{\"hp_mult\":1.5,\"attr_add\":{\"str\":2},\"skill_unlocks\":[]}'

# 全部 targets 约束；任一越界退出码为 1
python -m scripts.balance.sim --check --n 500 --output .tmp-test/balance-check.json

# 004：候选A只加入模拟会话，按checkpoint等级解锁；默认none
python -m scripts.balance.sim --check --n 500 --skills A --output .tmp-test/balance-skills-a.json

# 004：无新技能/候选A/无同伴完整对照与伤害预算
python -m scripts.balance.pass1 --n 500 --output eval/reports/balance-2026-10-11-pass1.json
python -m scripts.balance.pass1_report

# 可指定独立scenario/checkpoint快照；搜索只输出参数，不写剧本
python -m scripts.balance.pass1 --search --n 16 --iterations 80 --output .tmp-test/balance-search.json
python -m scripts.balance.pass1 --refine .tmp-test/balance-search.json --output .tmp-test/balance-refined.json

# B6 完整报告、CSV 与执行元数据；8 个独立进程
python -m scripts.balance.report --n 500 --seed 20261011 --workers 8
```

`--scenario`、`--checkpoint` 都可指定路径；后者也可填 `none`。`--check` 自动补算 heuristic 和 attack_only，检查闭区间胜率、胜利剩余 HP 均值、全战斗回合中位数、职业胜率差、boss 普攻胜率上限。无胜利时 HP 指标为 `null`，视为该约束未满足。仅选择部分职业时，职业差距只覆盖本次选择的职业。

上例 JSON 转义适用于 Windows PowerShell 的原生程序参数传递；使用 PowerShell 7 新版参数传递或直接调用 Python `main([...])` 时，传标准 JSON 即可。

`stat_scaling` 的 `attr_add` 使用角色已有的属性键；`skill_unlocks` 是已有角色技能或物品授予技能的 ID 列表。不会创造技能定义，也不修改原剧本。防御覆盖同时作用于敌我双方；领域直接伤害、持续状态伤害沿用引擎原本不经过防御的机制。

随机种子按（全局 seed、遭遇 ID、实际角色 ID、试验序号）生成，策略、公式、同伴和缩放共用这组种子。策略不会访问 RNG；相同参数可复现统计结果，不承诺跨 Python 版本 RNG 实现一致。guest 的首次回合效果也使用同一个 RNG。

checkpoint 每条均为 `proposed`，每个职业保存装备、物品、金币、同伴以及逐步 action/combat delta 来源。路线选择及未知消耗见 JSON 的 `notes`。每场独立回满 HP/MP/SP，未估算先前战斗的道具消耗；因此结果是所列装备条件下的单战强度，不是完整通关概率。

004还保存里程碑等级、已处理节点、成长后的上限和属性；商人checkpoint额外假定持有2个聖水，尚无游戏内发放动作。多敌职业差距使用targets已有的0.25，单敌仍为0.15。`budget.incoming_damage_budget`按开局全敌存活计算期望伤害/最大HP，含骰子分布、命中、抗性、防御和AI权重，状态/领域限制另列。候选A数据在`skill_candidates.json`，不写入角色模板。

缩放搜索按 hp_mult 升序、再按统一属性增加升序，找到第一个胜率落在目标区间的点即停止，无命中时穷尽全部 63 点。CSV 保留所有已测点和消耗/战败原因；只匹配胜率，不暗示其他 targets 约束也通过。报告进程缓存位于 `.tmp-test/balance-runs/<输入和代码指纹>/`；恢复运行时元数据中的 `elapsed_seconds` 是本次续跑墙钟时间，`cached_jobs` 标识复用了多少任务，worker 累计时间覆盖全部完成任务。

默认单元测试跳过数值强制检查；设置 `BALANCE_ENFORCE=1` 才启用。当前数值预计会使该测试失败，模拟器本身的离线测试仍正常运行。

```powershell
$env:BALANCE_ENFORCE = '1'
python -m unittest discover -s tests -p test_balance.py -q
Remove-Item Env:BALANCE_ENFORCE
```
