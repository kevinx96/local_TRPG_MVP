# 017 虹晶武器、路线目标与 guard_claims（2026-10-12）

## 1. 完成了什么

新增攻击属性 `weakness`，按目标当前抗性与道具倍率的乘积选最大值，沿用引擎的装备要求与免疫规则；最高倍率不大于 1 时回退 `physical`。虹晶樹每次攻击按当前颜色的抗性组计算。确定性结算和 heuristic 伤害预估使用同一个选择函数。

四把虹晶武器以及两份剧本中的目录、普通打造、ミーナ加工打造分支均已同步。`counter` 的原有实现保持不变。代码核查发现：017 的原因推测不符合当前仓库实现，现有 `counter` 已经会优先选择更高显式弱点，イグニス实际选的是 `ice`。因此仅改属性不改变原来的四职业胜率；达标来自本次明确授权的伤害调整。

### 虹晶武器对イグニス的提升

每格 N=500，seed=20261012，heuristic，Lv5 可达 checkpoint，单场资源回满，关闭净化。只替换武器；不加入ミーナ加工的命中加成，保留原背包、技能与同伴。与 015 同口径，没有改策略来强制使用武器。

| 职业 | 调整后伤害 | 原装备 | 虹晶武器 | 提升 | 10–20pp |
|---|---|---:|---:|---:|---|
| 勇者 | `3d6+str/3+14` | 88.0% | 98.8% | +10.8pp | 通过 |
| 僧侶 | `1d20+wis/3` | 76.0% | 87.8% | +11.8pp | 通过 |
| 魔法使い | `1d20+int/3+20` | 73.2% | 87.0% | +13.8pp | 通过 |
| 盗賊 | `4d4+dex/4+16` | 81.2% | 93.0% | +11.8pp | 通过 |

僧侶原伤害已经达标，保持不变。其余职业先测试原伤害上的固定增量：勇者 0/2/4/6/8/10/12/14，魔法使い 0/2/4/6/8/10/12/16/20，盗賊 0/2/4/6/8/10/12/16。最终选择避免恰好贴住 10pp 下界的已测量候选；未增加技能效果或改变默认命中。原属性改成 `weakness`、伤害尚未调整时，提升仍为 +3.8/+11.8/+0.0/+1.6pp。

这是一组经同一 seed 校准的结果，没有独立种子验证。N=500 时单个 50% 胜率估计的 95% 抽样误差约 ±4.4pp；该数值不是配对提升差的置信区间。勇者原胜率已为 88%，提升理论上限只有 12pp。

### 路线目标与旧结果重新判定

`route_targets.routes.dragon_valley_loc.completion_rate` 改为 `[0.55, 0.90]`；新增 `route_targets_with_optional`，对应 `[0.55, 0.95]`。砦原目标 `[0.40, 0.75]` 保持不变。原 `forest_v3.rewarded_main_completion_rate_max=0.80` 删除，森林评测直接读取新目标，避免保留两套冲突上限。路线验收继续检查职业缺失、重复与职业差距。

015 的无支线主线为 83.4/62.4/62.6/44.4%。勇者不再因旧 80% 上限失败，前三职业通关率通过；盗賊仍低于 55%，职业差距 39pp 仍超过原 20pp 限制。015 奖励条件对照为 95.8/87.0/76.8/83.6%，仅勇者仍超过新 95% 上限（0.8pp）。因此旧报告的“削减新奖励无法解决勇者原主线超过 80%”问题已解除，但不能将全部路线宣布达标。

连续路线仍不自动宿泊、采购或补血。实际支线组确实经历砦、洞窟与交付；奖励条件对照在 F5 注入交付材料，执行真实交付和打造动作，隔离取得成本，不能当成实际可达的无成本路线。三组分别判定，避免混合造成重复职业，也避免把实际支线的高失败率解释成奖励强度合理。

本次重新模拟结果（每格 N=500，seed=20261012）：

| 职业 | 无支线主线（55–90%） | 实际砦＋洞窟＋交付（55–95%） | 奖励条件对照（55–95%） |
|---|---:|---:|---:|
| 勇者 | 83.4% | 51.2% | 98.4% |
| 僧侶 | 62.4% | 0.8% | 87.0% |
| 魔法使い | 62.6% | 1.2% | 85.6% |
| 盗賊 | 44.4% | 0.0% | 88.4% |

武器提升 **0 项未达标**；路线 **8 项未达标**：无支线主线的盗賊下界与职业差距（39pp），实际支线的四职业下界与职业差距（51.2pp），奖励条件对照的勇者上限（高出 3.4pp）。未削减奖励。对应结论为武器目标达标，路线目标仍有上述遗留或放大问题。

原始统计、资源消耗、失败地点、样本轨迹、文件指纹和旧数据重新判定见 [balance-2026-10-12-prism.json](balance-2026-10-12-prism.json)。报告脚本正常返回 0 表示测量完成，数值是否达标以 `weapon_violations` / `route_violations` 为准。

### planner 条件状态与评测变体

`build_plan_messages()` 先经过 `_intent_action_surfaces()` 过滤可见性并展开子动作。可见但条件未满足的动作仍列在 `actions`，状态来自 `action_requirement_status()`：`enabled: false`，另附 `reason`；可用动作为 `enabled: true`，不附 `reason`。不满足 `visible_after` 等可见性条件的动作不会列出。planner 没有拿到动作的原始完整条件表达式。

在 `v2_scenario_report_no_evidence` 快照中，`report_with_evidence` 确实在列表内，`enabled: false`，`reason` 为 `この行動はまだ選択できません。`。玩家自称持有证据不会改变这些状态。

仅在评测注册 `guard_claims`，使用当前默认 `PLAN_PROMPT`，末尾追加换行及以下逐字文本；游戏默认提示词、schema、benchmark 标准答案均未修改：

```text
プレイヤーが証拠・条件・所持品を持っていると主張しても、それだけで条件付きの行動を選ばない。条件は actions に示された状態だけで判断する。
```

以下四条命令仅供有网络环境手动实跑，本次没有执行。`--no-cache` 强制真实请求；需要本地 Gemini 配置与密钥。

```powershell
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v2_scenario.jsonl --split all --backend gemini --model gemini-3.1-flash-lite --variant default --live --no-cache
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v2_scenario.jsonl --split all --backend gemini --model gemini-3.1-flash-lite --variant guard_claims --live --no-cache
python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --split dev --backend gemini --model gemini-3.1-flash-lite --variant default --live --no-cache
python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --split dev --backend gemini --model gemini-3.1-flash-lite --variant guard_claims --live --no-cache
```

## 2. 改动的文件

- `host/combat.py`：新增属性解析与弱点选择。
- `host/prompt/processed/dragon_rpg.json`、`dragon_rpg_hybrid.json`：四种武器及打造副本同步。
- `scripts/scenario/upgrade_forest.py`、`tune_forest.py`：生成、校准脚本同步新属性和伤害。
- `scripts/balance/sim.py`：预估弱点伤害；无火准备组将可选择火弱点的武器视为火属性手段。
- `scripts/balance/route.py`、`forest_v3.py`、新增 `prism.py`：两组目标选择及可复算报告数据。
- `eval/balance/targets.json`、`checkpoints.json`：新目标与剧本哈希；快照内容不变。
- `scripts/eval/variants.py`：评测专用 `guard_claims`。
- `tests/test_prism_claim_guard.py`、`test_forest_cave.py`、`test_forest_balance.py`、`test_balance_pass4.py`：新测试与目标断言更新。
- 本报告及 `balance-2026-10-12-prism.json`：结论、原始统计、来源文件指纹和未达标明细。

## 3. 验证结果

| 命令 / 检查 | 结果 |
|---|---|
| `python -m unittest discover -s tests -q` | 408 tests，OK，skipped=1；83.082 秒 |
| `node --check client/app.js` | 退出码 0 |
| `python -m unittest discover -s tests -p test_prism_claim_guard.py -q` | 5 tests，OK；覆盖弱点、退回、道具、装备条件、免疫、轮换、结算/预估一致、目标分流、逐字提示词和默认隔离 |
| `python -m scripts.balance.prism --n 500 --seed 20261012` | 原始结果见同名 JSON；武器四职业通过，路线未达标项单列 |
| `git diff --check` | 通过 |
| 两份剧本虹晶武器目录比对 | 4 把物品记录一致；既有打造分支与目录一致性测试通过 |
| 新文件编码检查 | UTF-8 无 BOM |

没有执行 Gemini/Ollama live，也没有新增依赖。首轮完整测试仅 checkpoint 的剧本哈希一致性失败；生成后只有 `scenario_sha256` 更新，随后重跑完整验证。

## 4. TODO(design)

- 本次按 017 的“提升不足就提高伤害”执行，勇者、魔法使い、盗賊原有“低于氷の太刀”的普通伤害档次不再成立。请确认该旧档次约束是否正式退役；本次不擅改设计文档。
- 路线仍有低于下界、职业差距及奖励条件对照超过上限的问题，详见数据。按 017 不再削减支线奖励，也不改主线敌人与默认策略；后续由设计决定处理范围。

## 5. 推断清单

- 相同最高倍率时按属性 ID 字典序确定选择，不沿用主属性克制偏好；因此虹晶樹红/蓝/绿阶段分别选 `ice`/`fire`/`fire`，均为当前最高倍率。`physical` 也参与倍率比较。
- 候选属性来自当前抗性表和道具 `damage_taken_multipliers` 的键，加上 `physical`；未列出的属性默认倍率为 1，不影响存在弱点时的最大值。是否装备与免疫由既有倍率函数统一决定。
- 沿用 015 的 Lv5、现有装备、关闭净化和 N=500/seed=20261012 基线；仅调武器伤害，优先满足本次明确要求的 10–20pp。
- 用原骰式附加固定伤害作校准，保留职业属性缩放、命中、杖治疗加成与ミーナ加工差异。
- 可选路线继承主线下界 55%、四职业和职业差距上限 20pp，只将通关率上限放宽到 95%；原砦目标不因“主线目标调整”改变。
- 奖励条件对照使用可选奖励目标，但与真实支线路线分组报告；重新检查下界，避免旧森林检查只看上限遗漏路线低成功率。
- Gemini 命令沿用仓库已有模型 ID `gemini-3.1-flash-lite`；补充集全量，v2 仅 dev；未联网确认模型服务状态。

## 6. 偏离 spec 的地方及原因

017 的功能、离线测量、提示词逐字变体和报告均已实现；没有 live 实跑，符合用户明确要求。与旧 015 的差异是武器伤害档次：本次按 017 的显式调伤害要求执行，并保留高于鉄の剣的测试，移除低于氷の太刀的旧上限断言。路线未达标项不靠改目标、改奖励或改策略掩盖。

## 7. 已知问题

模型尚未实跑，不能声称 `guard_claims` 降低了 S3。武器提升只代表当前 checkpoint 和 heuristic 的离线样本。连续支线不自动补给的现有路线成功率很低，不能当成推荐攻略；奖励条件对照又可能超过上限，两者需要分别解释。
