# 018 工程汇报

## 1. 完成了什么

- 将审定 v2 的 38 个快照固定到 `eval/benchmark/scenario_frozen/dragon_rpg@4386cd3.json`。
  冻结文件与 `git show 4386cd3:host/prompt/processed/dragon_rpg.json` 逐字节一致；
  SHA-256 为 `e83856989930a97c4963afbfbf95da0a766563336eb1107676d62310a3ffd02d`。
  局部 `.gitattributes` 固定 LF，避免 Windows 的 autocrlf 改变冻结文件。
- 增加离线生成器 `python -m scripts.eval.benchmark_v2_current`：从审定 v2 复制 486 条候选和
  38 个 `v2cur_` 快照，引用当前剧本，标签全部 `needs_review`。原标准答案未改动。
- 两份当前剧本中的六个指定动作均标记 `secret: true`。探索动作不可执行时从 planner 和
  `public_session.choices` 隐藏；状态满足后出现。嵌套秘密动作及没有可见子项的菜单也有测试。
  普通不可执行动作仍显示 disabled。直接提交动作 ID 仍由确定性引擎检查条件并拒绝。
- `purify_ignis_holy_water`、`purify_ignis_prayer` 是战斗特殊动作，现有代码已经在条件、
  敌人 HP 和消耗资源均满足时才加入 `public_session.combat.actions`。已加标记并测试两份剧本；
  它们不属于探索 planner 或 choices，不将战斗动作新增到探索界面。
- 子动作结论：现有 `_intent_action_surfaces` 已递归展开可执行叶子。当前 `ask_elder_weakness`
  是菜单父节点，其子动作 `ask_elder_treaty` 已进入 planner 且能执行、设置 `heard_treaty_lore`。
  无需新增展开代码；已加入双剧本回归测试。历史 existing 标签变化属于动作语义变化，待设计审标。
- 保留 `guard_claims`，没有采用它，也没有修改默认提示词措辞。没有新增依赖。

## 2. 改动的文件

- `host/state.py`、`host/free_actions.py`、`host/scenario_context.py`：可见性、秘密字段传递、条件原因兼容。
- `host/prompt/processed/dragon_rpg.json`、`dragon_rpg_hybrid.json`、`scenario_pack.schema.json`：六个标记及 schema。
- `scripts/eval/benchmark_v2.py`、`scripts/eval/benchmark_v2_current.py`：固定生成器与当前版复制生成器。
- `eval/benchmark/README.md`、`eval/benchmark/scenario_frozen/`、38 个原 v2 快照、38 个新 v2cur 快照、
  `eval/candidates/intent_v2_current.jsonl`：冻结规则和两套评测数据。
- `tests/test_benchmark_pinning_and_secrets.py`：7 项新增测试；`test_observe_supplement.py`、
  `test_prism_claim_guard.py`、`test_scenario_v2.py`：旧断言适配隐藏规则，当前观察测试切换 v2cur。
- `eval/balance/checkpoints.json`：重跑既有生成器，只更新 scenario_sha256，路线、装备和数值未变。
- 本汇报、`018-benchmark-pinning-evidence.json` 和三组正式离线 JSON/Markdown 报告。

## 3. 验证结果

所有评测均省略 `--live`，没有调用付费模型。命令如下：

```powershell
python -m unittest discover -s tests -q
node --check client/app.js
python -m scripts.eval.benchmark_v2_current
python -m scripts.balance.checkpoints
python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --backend gemini --model gemini-3.1-flash-lite --variant guard_rules --split dev
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v2_current.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split dev
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v2_scenario.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split all
```

全量 unittest：`Ran 415 tests in 103.599s`，`OK (skipped=1)`，退出码 0。
`node --check client/app.js` 已通过，退出码 0；`git diff --check` 通过。
新测试覆盖秘密动作隐藏／解锁／再次隐藏、嵌套组、普通 disabled 动作、战斗净化条件、长老叶子执行、
历史条件原因、冻结哈希、当前版生成幂等和标签复制不变性。

| 正式离线重放 | 缓存命中 | skipped | S0+S1（仅已命中响应） |
|---|---:|---:|---:|
| 冻结 v2 dev / guard_rules | 190/194，97.94% | 4 | 176/190，92.63% |
| 当前 v2 dev / default | 143/194，73.71% | 51 | 130/143，90.91% |
| 补充集 / default | 34/50，68.00% | 16 | 24/34，70.59% |

后两行不是完整评测结果，不应用来推断隐藏动作前后的模型质量变化。
逐条缓存命中从对应 `eval/runs/<run_id>/cases.jsonl` 的 `cache_hit` 汇总，汇总证据已提交到
`018-benchmark-pinning-evidence.json`。正式报告 run_id：

- 冻结：`2026-10-11T192820099149Z-intent-gemini-gemini-3.1-flash-lite-guard_rules`
- 当前：`2026-10-11T193307632107Z-intent-gemini-gemini-3.1-flash-lite-default`
- 补充：`2026-10-11T193307651016Z-intent-gemini-gemini-3.1-flash-lite-default`

### 第 1 节是否精确复现：指定冻结版本下不能，来源已查清

1. 仅固定剧本时命中 140/194。原因是后来的 `_session_requirement_passes` 检查把 50 条用例里
   原有属性／物品不足的具体 `reason` 变成通用文本。保留现有 `choice_requirement_status` 的具体原因后，
   命中 190/194。此改动没有放宽条件，也没有改写原因文本，新增测试固定该兼容行为。
2. 剩余 4 条共用 `v2_goblin_fort_first_second_mage`：
   `v2-existing_exact-013`、`v2-existing_paraphrase-013`、`v2-deixis_unique-005`、`v2-language_mix-013`。
   `4386cd3` 的描述是「通路の先を、一匹のゴブリンと二匹の弓ゴブリンが守っている。」；
   commit `4e7c15e` 已改为「通路の先を、一匹のゴブリンと一匹の弓ゴブリンが守っている。」。
   008 报告使用的是后者，因此报告与指定冻结提交本身不是同一剧本基线。
3. 控制变量对照：从 `f41af9d` 读取 008 时剧本，只在内存中的 session 修改上述 location.description，
   用当前 `evaluate_case`、`guard_rules` 和本地缓存重新计算全部 194 条 dev，再以当前 `summarize`
   逐字段比较参考报告的 `metrics`。结果 **194/194 缓存命中，所有 metrics 完全相同**，
   S0=168、S1=12、S2=13、S3=1、S4=0，S0+S1=180/194=92.7835%。
   这是诊断对照，不是正式冻结版成绩；冻结剧本和快照没有应用描述替换。

需要补跑真实模型时，在有网络环境给相应评测命令显式加 `--live`；本次没有执行。

## 4. TODO(design) 清单

- 审核 `intent_v2_current.jsonl` 的所有沿用标签，尤其长老父动作变为菜单后的 existing 答案。
- 决定 `4386cd3` 基线与 008 实跑基线如何分别命名／保存；本次遵守指定 commit，不修改冻结叙事。
- 仅建议考虑额外秘密动作，未自行加标记：`give_correct_password`（未掌握口令）、`fort_shortcut`
  （未解锁的隐藏路线）、`forge_prism_weapon`（未获得虹晶素材时提前揭露武器来源）。

## 5. 推断清单

- “benchmark v2 快照”按 `eval/benchmark/intent_v2.jsonl` 实际引用的 38 个快照界定。
  `v2_scenario_*` 虽符合宽泛通配符，但属于明确要求跟随当前剧本的补充集，保持当前引用。
- 当前候选文件采用 `intent_v2_current.jsonl`；用例 ID 改为 `v2cur-`，与快照 `v2cur_` 一起区分来源。
  只改 ID、引用、label_status，其余标签、输入、划分和 gold_note 原样复制。
- `secret` 的条件采用既有 `action_requirement_status`，包括 once、disabled_after 和资源条件；
  不再可执行时重新隐藏。仅影响 UI/planner 可见性，直接动作请求仍走原有确定性拒绝逻辑。
- 有秘密动作的场景在 public_session 中重建引擎 choices，避免旧 choices 或模型恢复的菜单泄露秘密；
  子项过滤完为空的组也隐藏。
- 战斗净化沿用现有 combat.actions 的可见性约束，不添加到探索 planner。
- 恢复具体条件原因是修复缓存漂移的一部分；局部 LF 属性是 Windows 下逐字节冻结所需。

## 6. 偏离 spec 的地方及原因

- 第 1 节的“全部命中且同为 92.78%”在同时保留指定 `4386cd3` 时不成立。按 spec 的异常处理要求，
  查清两项漂移并保留证据；没有更换指定剧本或挪用其他缓存响应。正式结果如上。
- 第 3 节没有增加新的展开逻辑，因为原逻辑已正确展开子动作；按要求增加测试并报告实际语义变化。
- 两个净化动作的可见面是战斗菜单，测试其真实界面；不会为满足文字描述而将它们加入探索 choices。

## 7. 已知问题

- 当前候选标签尚未审定；当前集和补充集的缺失响应仍需日后显式 live 补齐。
- 冻结剧本能固定数据，但后续引擎、提示词或请求 schema 的变更仍可能改变哈希，应继续做离线对照。
- Windows 沙箱内 `tempfile.TemporaryDirectory` 曾产生 PermissionError；最终全量验证使用已获自动批准的
  沙箱外本地运行，不启用 live。
