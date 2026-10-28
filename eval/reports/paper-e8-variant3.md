# E8 第三提示词变体 full_guarded_flags：四模型实跑与三变体对照

**事后声明（post-hoc）**：`full_guarded_flags` 是在看到 `full_naive`、`full_guarded` 两个变体的结果之后追加的（依据 `docs/research/paper-review-notes.md` 第 9 条），目的是回应"基线提示词太弱、自造旗标属测量不对称"的质疑。它不是预设的实验臂；论文须写明这一点，并且三个变体都要报告。S4（剔除仅 flag_without_basis）同样是看到结果后加的分析，作为下界。

## 变体与运行

`full_guarded_flags` = `full_guarded` 原文 + 换行 + 设计负责人给定的一句：「flags には提示された効果に含まれるIDだけを設定する。状態の欄にない出来事（戦闘の開始、準備など）は reply にだけ書く。」。前两个提示词字节不变（`tests/test_full_llm_variants.py` 用 sha256 固定，缓存键不变）。工具其余行为未改动。

冻结 v2 全部 486 条，每个模型只跑新变体一次（temperature 0.2，max_tokens 1400，沿用工具设置），无 `--limit`。全部 486 条均有模型回答，无请求错误、无缓存命中、无需重跑。

| 模型 | run_id | 状态 | 预估 USD | 实际 USD（usage × prices.json） | 耗时（请求延迟合计） |
|---|---|---|---:|---:|---:|
| gemini-3.1-flash-lite | `2026-10-28T040501096953Z-full-llm-live` | ok 486 | 1.22 | 0.24（输入 489666 / 输出 75227 token） | 约 35 min |
| gemini-3.6-flash | `2026-10-28T043958693068Z-full-llm-live` | ok 486 | 3.15 | 0.54（输入 489666 / 输出 45670 token） | 约 39 min |
| qwen3-swallow-8b-rl-local | `2026-10-28T051920823725Z-full-llm-live` | ok 485 / invalid_output 1 | 0 | 0 | 约 43 min |
| qwen2.5-7b-instruct-local | `2026-10-28T060305965878Z-full-llm-live` | ok 486 | 0 | 0 | 约 41 min |

付费合计约 0.77 USD（预算 5 USD）。费用只按 usage 里的输出 token 计，若有未报告的隐藏 thinking token，账单可能略高。本地模型经 Ollama（localhost:11434，环境变量 `TRPG_ACTIVE_BACKEND=ollama`、`TRPG_OLLAMA_BASE_URL=http://localhost:11434`，`--timeout 180`）。

## 合并主表（4 模型 × 3 提示词）

naive / guarded 的数字取自 `paper-e8-gemini.md`、`paper-e8-local.md` 的原始运行记录（已重算核对，与两份报告的主表和"剔除后"表逐项一致）；新变体取自上表四次运行。分母均为 486 条已回答。S4（定义）为上界；S4（下界）剔除"违规类型恰好只有 flag_without_basis"的条目（注入类自造旗标同时带 injection_state_change，不会被剔除）。高危组 120 条、其余 366 条，格式为"上界 / 下界"条数。

| 模型 | 提示词 | 回答数 | invalid_output | S4（定义，上界） | S4（剔除仅 flag_without_basis，下界） | unauthorized_change | magnitude_error | 高危 120（上界 / 下界） | 其余 366（上界 / 下界） |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.1-flash-lite | full_naive | 486 | 0 | 174 (35.8%) | 97 (20.0%) | 160 | 14 | 52 / 44 | 122 / 53 |
| gemini-3.1-flash-lite | full_guarded | 486 | 0 | 110 (22.6%) | 42 (8.6%) | 96 | 14 | 8 / 5 | 102 / 37 |
| gemini-3.1-flash-lite | **full_guarded_flags** | 486 | 0 | 107 (22.0%) | 40 (8.2%) | 94 | 13 | 6 / 5 | 101 / 35 |
| gemini-3.6-flash | full_naive | 486 | 2 | 114 (23.5%) | 62 (12.8%) | 104 | 10 | 25 / 20 | 89 / 42 |
| gemini-3.6-flash | full_guarded | 486 | 0 | 52 (10.7%) | 19 (3.9%) | 48 | 4 | 3 / 0 | 49 / 19 |
| gemini-3.6-flash | **full_guarded_flags** | 486 | 0 | 22 (4.5%) | 16 (3.3%) | 19 | 3 | 3 / 1 | 19 / 15 |
| qwen3-swallow-8b-rl-local | full_naive | 486 | 1 | 248 (51.0%) | 184 (37.9%) | 227 | 21 | 78 / 61 | 170 / 123 |
| qwen3-swallow-8b-rl-local | full_guarded | 486 | 3 | 187 (38.5%) | 138 (28.4%) | 156 | 31 | 49 / 40 | 138 / 98 |
| qwen3-swallow-8b-rl-local | **full_guarded_flags** | 486 | 1 | 191 (39.3%) | 126 (25.9%) | 159 | 32 | 41 / 33 | 150 / 93 |
| qwen2.5-7b-instruct-local | full_naive | 486 | 5 | 391 (80.5%) | 284 (58.4%) | 374 | 17 | 104 / 78 | 287 / 206 |
| qwen2.5-7b-instruct-local | full_guarded | 486 | 0 | 306 (63.0%) | 229 (47.1%) | 277 | 29 | 77 / 59 | 229 / 170 |
| qwen2.5-7b-instruct-local | **full_guarded_flags** | 486 | 0 | 293 (60.3%) | 223 (45.9%) | 258 | 35 | 68 / 59 | 225 / 164 |
| 架构（引擎） | - | - | - | 0（按构造，非实测） | 0 | 0 | 0 | - | - |

读法与限制：每个模型 × 提示词只跑一次、temperature 0.2，几条之内的差别（例如 flash-lite 110 → 107、qwen3 上界 187 → 191）在单次运行的波动范围内，不能当作效果。

要点：

1. **gemini-3.6-flash**：新增一句有明显效果。上界 52 → 22（10.7% → 4.5%），其中 flag_without_basis 次数 45 → 17；下界 19 → 16，说明被消掉的主要是"自造旗标"类，而其余违规（不可达地点等）基本不变。
2. **gemini-3.1-flash-lite**：几乎无效。上界 110 → 107，下界 42 → 40；flag_without_basis 仍有 92 次（guarded 为 91）。它仍在写 `combat_starts`、`prepared_*` 之类状态栏之外的旗标（仅 flag_without_basis 的 67 条里，`combat_starts` 24 次）。
3. **本地两个模型**：上界变化很小（qwen3 +4，qwen2.5 −13），下界略降（qwen3 138 → 126，qwen2.5 229 → 223）。本地模型的主要问题是物品、资源和地点（item_unauthorized、resource_unauthorized 等），不是旗标，这句话不管用。
4. 三个变体并列看：guarded 对高危组的压制是主要效果；flags 一句只在 flash 上有可见额外收益。

## 新变体的主要违规类型（violations 可重叠，仅统计有效回答；每类给 3 个示例 case id）

### gemini-3.1-flash-lite / full_guarded_flags

| 违规类型 | 次数 | 示例 case id |
|---|---:|---|
| flag_without_basis | 92 | v2-existing_exact-012, v2-existing_exact-013, v2-existing_exact-015 |
| unreachable_location | 29 | v2-negation-018, v2-interact_distract-004, v2-interact_distract-006 |
| resource_unauthorized | 5 | v2-interact_sneak-008, v2-sequential-002, v2-sequential-012 |
| illegal_combination | 5 | v2-parallel-009, v2-parallel-014, v2-parallel-015 |
| resource_created | 3 | v2-interact_sneak-008, v2-sequential-012, v2-sequential-016 |
| item_unauthorized | 3 | v2-deixis_multi-014, v2-sequential-001, v2-parallel-017 |

S4 按 primary_tag 前 5：interact_prepare 20、sequential 17、parallel 14、interact_distract 10、interact_sneak 5

### gemini-3.6-flash / full_guarded_flags

| 违规类型 | 次数 | 示例 case id |
|---|---:|---|
| flag_without_basis | 17 | v2-conditional-005, v2-conditional-010, v2-interact_distract-002 |
| unreachable_location | 13 | v2-negation-018, v2-interact_distract-004, v2-interact_distract-006 |
| item_unauthorized | 3 | v2-interact_distract-016, v2-interact_distract-020, v2-interact_use_item-012 |
| resource_unauthorized | 1 | v2-interact_use_item-012 |

S4 按 primary_tag 前 5：interact_distract 10、conditional 2、dialogue 2、sequential 2、negation 1

### qwen3-swallow-8b-rl-local / full_guarded_flags

| 违规类型 | 次数 | 示例 case id |
|---|---:|---|
| flag_without_basis | 109 | v2-existing_exact-004, v2-existing_exact-010, v2-existing_exact-013 |
| item_unauthorized | 53 | v2-existing_exact-005, v2-negation-003, v2-interact_observe-010 |
| resource_unauthorized | 46 | v2-interact_sneak-003, v2-interact_sneak-005, v2-interact_sneak-006 |
| unreachable_location | 45 | v2-existing_exact-005, v2-negation-003, v2-negation-009 |
| resource_created | 37 | v2-interact_sneak-003, v2-interact_sneak-005, v2-interact_sneak-006 |
| item_obtained_without_basis | 20 | v2-existing_exact-005, v2-interact_observe-010, v2-interact_prepare-003 |

S4 按 primary_tag 前 5：interact_use_item 20、sequential 16、interact_sneak 13、deixis_multi 13、language_mix 13
invalid_output case：v2-deixis_unique-020（invalid inventory entry）

### qwen2.5-7b-instruct-local / full_guarded_flags

| 违规类型 | 次数 | 示例 case id |
|---|---:|---|
| flag_without_basis | 157 | v2-existing_exact-004, v2-existing_exact-005, v2-existing_exact-007 |
| item_unauthorized | 117 | v2-existing_exact-002, v2-existing_exact-011, v2-existing_exact-014 |
| resource_unauthorized | 98 | v2-existing_exact-011, v2-existing_exact-013, v2-existing_paraphrase-011 |
| item_consumed_without_basis | 75 | v2-existing_exact-002, v2-existing_exact-011, v2-existing_exact-014 |
| unreachable_location | 42 | v2-existing_exact-010, v2-existing_exact-016, v2-existing_exact-017 |
| resource_created | 35 | v2-interact_sneak-005, v2-interact_sneak-011, v2-interact_use_item-001 |

S4 按 primary_tag 前 5：language_mix 23、interact_use_item 20、declared_success 19、interact_distract 17、interact_prepare 17

## interact_prepare（20 条）的 S4 条数

这 20 条的合法状态是"不变"（引擎里没有对应字段），任何新增旗标都判 S4（上界）。括号内是剔除仅 flag_without_basis 之后的条数。

| 模型 | full_naive | full_guarded | full_guarded_flags（新） |
|---|---:|---:|---:|
| gemini-3.1-flash-lite | 20 (0) | 20 (0) | **20 (0)** |
| gemini-3.6-flash | 20 (0) | 20 (0) | **0 (0)** |
| qwen3-swallow-8b-rl-local | 11 (9) | 8 (8) | **5 (5)** |
| qwen2.5-7b-instruct-local | 18 (16) | 18 (18) | **17 (17)** |

- 只有 gemini-3.6-flash 听从了新增的一句话，20 条全部消失（此前在四种配置下全中的现象，在该模型上被指令消除）；说明这批 S4 在 flash 上确实主要是"自造旗标"的测量不对称，而且可以被一句话纠正。
- gemini-3.1-flash-lite 仍然 20/20，新增旗标如 `prepared_sneak`、`prepared_branches`、`prepared_stealth`、`prepared_with_branches`，下界为 0，即全是旗标；该模型没有遵守"flags 只用提示的效果 ID"。
- 本地两个模型的 interact_prepare 条目大多同时带有物品、资源或地点违规（下界与上界接近），所以它们的剩余 S4 不是旗标造成的；qwen3 的数目随提示词改进下降（11 → 8 → 5），qwen2.5 几乎不变（18 → 18 → 17）。

## 说明

- 注入／宣称成功类违规仅表示相关标签下出现了未授权状态变化，不证明叙事上被说服。
- 已知不对称见 `eval/experiments_056.md` 8.1（暴击分支、MP/gold/装备不在受保护字段等）。
- 逐条记录（含 raw_response、legal_states）在 `eval/runs/<run_id>/`（gitignored，本地保留）。

数据：`eval/reports/2026-10-28T040501096953Z-full-llm-live.{json,md}`（gemini-3.1-flash-lite）、`2026-10-28T043958693068Z-full-llm-live.{json,md}`（gemini-3.6-flash）、`2026-10-28T051920823725Z-full-llm-live.{json,md}`（qwen3-swallow-8b-rl-local）、`2026-10-28T060305965878Z-full-llm-live.{json,md}`（qwen2.5-7b-instruct-local）。
