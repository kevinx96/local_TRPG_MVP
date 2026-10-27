# 论文配对显著性检验（离线）

生成：`python -m scripts.eval.paired_stats --paper`（`scripts/eval/paired_stats.py`，仅标准库，不联网）。自助法 10000 次重采样，固定种子 20261027，对子 (A,B) 同一组重采样索引。

**评分口径**：所有运行都用当前评分 v1.2 重算（HEAD f9e3592; scoring/contract files last changed in dc2ab65 2026-10-20）。逐条结果取自各运行的原始模型响应（`eval/runs/<id>/cases.jsonl`；该目录已不存在的运行，则按原运行的 backend/model/变体名和匹配到的 system prompt 离线重放 `eval/cache`），再用当前的 `parse_plan`（含 existing 归一化）、当前 gold 标签（`eval/benchmark/intent_v2.jsonl`、`eval/candidates/intent_v2_scenario.jsonl`）和 `metrics.severity` 评分。因此本表的比例不同于论文各表中的 v1.1 数字，不能与它们混用；“原报告”列保留了原运行报告里的数字（当时的评分口径）以便核对。

**指标**：S0+S1 = 严重度为 S0 或 S1 的条数 / 配对可评测条数；S3 = 严重度为 S3 的条数 / 配对可评测条数。b = 仅 A 达到该指标（A 记 1、B 记 0）的条数，c = 仅 B 达到的条数；McNemar 精确 p 为对 b+c 条不一致对做 p=0.5 的二项检验（双侧）。CI 为 B−A 的比例差（百分点）的配对自助法 95% 百分位区间。S3 的“事件”是出现 S3，所以 c>b 表示 B 的 S3 更多。

## 结果

| 对比 | n | 指标 | A 率 | B 率 | 不一致 b/c | McNemar 精确 p | B−A 自助法 95% CI |
|---|---:|---|---|---|---|---|---|
| (a) E1 test: pre_guard→guard_rules | 292 | S0+S1 | 90.4% (264/292) | 94.5% (276/292) | 3/15 | 0.0075 | +4.1 pp [+1.4, +7.2] |
| (a) E1 test: pre_guard→guard_rules | 292 | S3 | 3.4% (10/292) | 1.4% (4/292) | 7/1 | 0.0703 | -2.1 pp [-4.1, -0.3] |
| (b) E1 dev: pre_guard→guard_rules | 194 | S0+S1 | 92.8% (180/194) | 95.4% (185/194) | 4/9 | 0.2668 | +2.6 pp [-1.0, +6.2] |
| (b) E1 dev: pre_guard→guard_rules | 194 | S3 | 3.6% (7/194) | 0.5% (1/194) | 7/1 | 0.0703 | -3.1 pp [-6.2, -0.5] |
| (c) E2 test: guard_rules→guard_sequence_item | 292 | S0+S1 | 94.5% (276/292) | 96.6% (282/292) | 3/9 | 0.1460 | +2.1 pp [-0.3, +4.5] |
| (c) E2 test: guard_rules→guard_sequence_item | 292 | S3 | 1.4% (4/292) | 0.7% (2/292) | 2/0 | 0.5000 | -0.7 pp [-1.7, +0.0] |
| (d) E2 dev: guard_rules→guard_sequence_item | 194 | S0+S1 | 95.4% (185/194) | 95.9% (186/194) | 5/6 | 1.0000 | +0.5 pp [-3.1, +3.6] |
| (d) E2 dev: guard_rules→guard_sequence_item | 194 | S3 | 0.5% (1/194) | 1.0% (2/194) | 1/2 | 1.0000 | +0.5 pp [-1.0, +2.6] |
| (e1) E3 Gemini dev: default→lenient | 194 | S0+S1 | 92.8% (180/194) | 92.8% (180/194) | 0/0 | 1.0000 | +0.0 pp [+0.0, +0.0] |
| (e1) E3 Gemini dev: default→lenient | 194 | S3 | 3.6% (7/194) | 3.6% (7/194) | 0/0 | 1.0000 | +0.0 pp [+0.0, +0.0] |
| (e2) E3 qwen3-swallow dev: default→union_schema | 190 | S0+S1 | 0.5% (1/190) | 34.2% (65/190) | 0/64 | 1.1e-19 | +33.7 pp [+26.8, +40.5] |
| (e2) E3 qwen3-swallow dev: default→union_schema | 190 | S3 | 2.6% (5/190) | 21.6% (41/190) | 3/39 | 5.6e-09 | +18.9 pp [+13.2, +25.3] |
| (f1) E5 补充集: default→guard_claims（均为秘密动作前） | 50 | S0+S1 | 74.0% (37/50) | 78.0% (39/50) | 2/4 | 0.6875 | +4.0 pp [-6.0, +14.0] |
| (f1) E5 补充集: default→guard_claims（均为秘密动作前） | 50 | S3 | 12.0% (6/50) | 14.0% (7/50) | 1/2 | 1.0000 | +2.0 pp [-4.0, +8.0] |
| (f2) E5 补充集: default(秘密动作前)→default(秘密动作后) | 50 | S0+S1 | 74.0% (37/50) | 82.0% (41/50) | 1/5 | 0.2188 | +8.0 pp [+0.0, +18.0] |
| (f2) E5 补充集: default(秘密动作前)→default(秘密动作后) | 50 | S3 | 12.0% (6/50) | 2.0% (1/50) | 5/0 | 0.0625 | -10.0 pp [-20.0, -2.0] |
| (f3) E5 补充集: default(16:11, 秘密动作前)→default(秘密动作后) | 50 | S0+S1 | 76.0% (38/50) | 82.0% (41/50) | 2/5 | 0.4531 | +6.0 pp [-4.0, +16.0] |
| (f3) E5 补充集: default(16:11, 秘密动作前)→default(秘密动作后) | 50 | S3 | 12.0% (6/50) | 2.0% (1/50) | 5/0 | 0.0625 | -10.0 pp [-20.0, -2.0] |
| (f4) E5 补充集 evidence_claim 子集 (f2) | 8 | S0+S1 | 37.5% (3/8) | 100.0% (8/8) | 0/5 | 0.0625 | +62.5 pp [+25.0, +87.5] |
| (f4) E5 补充集 evidence_claim 子集 (f2) | 8 | S3 | 62.5% (5/8) | 0.0% (0/8) | 5/0 | 0.0625 | -62.5 pp [-87.5, -25.0] |
| (g) 头条: pre_guard→最终 default（test） | 292 | S0+S1 | 90.4% (264/292) | 97.3% (284/292) | 1/21 | 1.1e-05 | +6.8 pp [+4.1, +9.9] |
| (g) 头条: pre_guard→最终 default（test） | 292 | S3 | 3.4% (10/292) | 0.7% (2/292) | 8/0 | 0.0078 | -2.7 pp [-4.8, -1.0] |

## 对比说明与对齐情况

- (a) E1 test: pre_guard→guard_rules：A=`2026-10-11T121040703064Z-intent-gemini-gemini-3.1-flash-lite-default`，B=`2026-10-11T195057330510Z-intent-gemini-gemini-3.1-flash-lite-guard_rules`；n=292。A 是 008 的原始 pre_guard test 运行（当时以 default 名实跑），B 是 v1.2 评分后的离线重放（5.1.3 节的“后”）。
- (b) E1 dev: pre_guard→guard_rules：A=`2026-10-11T120159376587Z-intent-gemini-gemini-3.1-flash-lite-default`，B=`2026-10-11T195050287754Z-intent-gemini-gemini-3.1-flash-lite-guard_rules`；n=194。A 是 008 的原始 pre_guard dev 运行，B 是 v1.2 评分后的离线重放。
- (c) E2 test: guard_rules→guard_sequence_item：A=`2026-10-12T062915606413Z-intent-gemini-gemini-3.1-flash-lite-guard_rules`，B=`2026-10-12T062927141458Z-intent-gemini-gemini-3.1-flash-lite-guard_sequence_item`；n=292。
- (d) E2 dev: guard_rules→guard_sequence_item：A=`2026-10-12T062656092753Z-intent-gemini-gemini-3.1-flash-lite-guard_rules`，B=`2026-10-12T062704069819Z-intent-gemini-gemini-3.1-flash-lite-guard_sequence_item`；n=194。
- (e1) E3 Gemini dev: default→lenient：A=`2026-10-11T112514831356Z-intent-gemini-gemini-3.1-flash-lite-default`，B=`2026-10-11T112526523573Z-intent-gemini-gemini-3.1-flash-lite-lenient`；n=194。同一批响应，只有解析不同。
- (e2) E3 qwen3-swallow dev: default→union_schema：A=`2026-10-11T112514831499Z-intent-ollama-qwen3-swallow-8b-rl-local-default`，B=`2026-10-11T114851107708Z-intent-ollama-qwen3-swallow-8b-rl-local-union_schema`；n=190；从两端剔除（任一端未评测）的用例：v2-deixis_unique-005, v2-existing_exact-013, v2-existing_paraphrase-013, v2-language_mix-013。缓存对冻结剧本只命中 190/194（4 条地点描述漂移，两端都缺），所以 n=190 而不是论文的 194。
- (f1) E5 补充集: default→guard_claims（均为秘密动作前）：A=`2026-10-11T191145950026Z-intent-gemini-gemini-3.1-flash-lite-default`，B=`2026-10-11T191200091981Z-intent-gemini-gemini-3.1-flash-lite-guard_claims`；n=50。同一分钟先后实跑；基线 default 此时已含 guard_rules。
- (f2) E5 补充集: default(秘密动作前)→default(秘密动作后)：A=`2026-10-11T191145950026Z-intent-gemini-gemini-3.1-flash-lite-default`，B=`2026-10-11T193956473760Z-intent-gemini-gemini-3.1-flash-lite-default`；n=50。秘密动作是系统改动，两次运行的 planner 动作列表不同；采样随机性与动作列表变化混在一起。
- (f3) E5 补充集: default(16:11, 秘密动作前)→default(秘密动作后)：A=`2026-10-11T161151095000Z-intent-gemini-gemini-3.1-flash-lite-default`，B=`2026-10-11T193956473760Z-intent-gemini-gemini-3.1-flash-lite-default`；n=50。
- (f4) E5 补充集 evidence_claim 子集 (f2)：A=`2026-10-11T191145950026Z-intent-gemini-gemini-3.1-flash-lite-default`，B=`2026-10-11T193956473760Z-intent-gemini-gemini-3.1-flash-lite-default`；n=8。子集分析，事后选择，仅供参考。
- (g) 头条: pre_guard→最终 default（test）：A=`2026-10-11T121040703064Z-intent-gemini-gemini-3.1-flash-lite-default`，B=`2026-10-13T072950363331Z-intent-gemini-gemini-3.1-flash-lite-default`；n=292。论文头条的 83.6%（pre_guard，v1.1 评分）和 97.3%（最终 default，v1.2 评分）口径不同，不能配对；这里 A 取 008 的原始 pre_guard test 运行（离线重放，system prompt 为 PLAN_PROMPT_BASE），B 取 2026-10-13 的最终 default test 运行（offtopic 规则后，v1.2 之后实跑），两端都按 v1.2 重算。A 在 v1.2 下为 90.4%，即评分、标注与契约修订单独就带来 83.6%→90.4%，其余才是三次提示词修改的贡献。

## 注意事项

- p 值与 CI 未做多重比较校正；本表共 11 个对比、22 行，单个 p 接近 0.05 的结果不应单独当作显著证据。
- 每个配置只采样一次（temperature 0.2），配对检验只覆盖“同一批用例上的差异”，不含采样随机性；不同运行之间的差异混有采样噪声。
- E5（f 组）n=50，标签状态为 proposed，且 f4 是事后选取的子集（n=8），仅供参考。
- E5 的 3 条原 InvalidPlan（existing 带多余字段）在 v1.2 归一化后可执行，其引擎裁定在当前剧本包上重算；严重度只由 plan、gold 和 harmful 决定（该集合每条都有 harmful），各运行 S4 均为 0。

## 运行来源与回放核对

| run id | variant / split | 来源 | 匹配的 system prompt | 缓存命中 | 原报告 S0+S1 / S3 | v1.2 重算 S0+S1 / S3（全部可评测条） |
|---|---|---|---|---|---|---|
| `2026-10-11T121040703064Z-intent-gemini-gemini-3.1-flash-lite-default` | default / test | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 687.8 vs report 687.8 (as defined in variants.py: 292 hits; pre_guard (PLAN_PROMPT_BASE): 292 hits; guard_rules (PRE_SEQUENCE): 177 hits; legacy default (+offtopic): 292 hits) | 292/292 | 83.6% / 2.1% | 90.4% / 3.4%（n=292） |
| `2026-10-11T120159376587Z-intent-gemini-gemini-3.1-flash-lite-default` | default / dev | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 706.0 vs report 706.0 (pre_guard (PLAN_PROMPT_BASE): 194 hits; guard_rules (PRE_SEQUENCE): 109 hits) | 194/194 | 89.7% / 3.1% | 92.8% / 3.6%（n=194） |
| `2026-10-12T062915606413Z-intent-gemini-gemini-3.1-flash-lite-guard_rules` | guard_rules / test | stored cases.jsonl | n/a (stored responses) | n/a | 94.5% / 1.4% | 94.5% / 1.4%（n=292） |
| `2026-10-12T062656092753Z-intent-gemini-gemini-3.1-flash-lite-guard_rules` | guard_rules / dev | stored cases.jsonl | n/a (stored responses) | n/a | 95.4% / 0.5% | 95.4% / 0.5%（n=194） |
| `2026-10-11T112514831356Z-intent-gemini-gemini-3.1-flash-lite-default` | default / dev | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 706.0 vs report 706.0 (pre_guard (PLAN_PROMPT_BASE): 194 hits; guard_rules (PRE_SEQUENCE): 109 hits) | 194/194 | 89.7% / 3.1% | 92.8% / 3.6%（n=194） |
| `2026-10-11T112514831499Z-intent-ollama-qwen3-swallow-8b-rl-local-default` | default / dev | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 836.5 vs report 833.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) | 190/194 | 0.0% / 0.0% | 0.5% / 2.6%（n=190） |
| `2026-10-11T191145950026Z-intent-gemini-gemini-3.1-flash-lite-default` | default / all | stored cases.jsonl（3 条因计划变化重新裁定） | n/a (stored responses) | n/a | 64.0% / 12.0% | 74.0% / 12.0%（n=50） |
| `2026-10-11T161151095000Z-intent-gemini-gemini-3.1-flash-lite-default` | default / all | stored cases.jsonl（3 条因计划变化重新裁定） | n/a (stored responses) | n/a | 66.0% / 12.0% | 76.0% / 12.0%（n=50） |
| `2026-10-11T195057330510Z-intent-gemini-gemini-3.1-flash-lite-guard_rules` | guard_rules / test | stored cases.jsonl | n/a (stored responses) | n/a | 94.5% / 1.4% | 94.5% / 1.4%（n=292） |
| `2026-10-11T195050287754Z-intent-gemini-gemini-3.1-flash-lite-guard_rules` | guard_rules / dev | stored cases.jsonl | n/a (stored responses) | n/a | 95.4% / 0.5% | 95.4% / 0.5%（n=194） |
| `2026-10-12T062927141458Z-intent-gemini-gemini-3.1-flash-lite-guard_sequence_item` | guard_sequence_item / test | stored cases.jsonl | n/a (stored responses) | n/a | 96.6% / 0.7% | 96.6% / 0.7%（n=292） |
| `2026-10-12T062704069819Z-intent-gemini-gemini-3.1-flash-lite-guard_sequence_item` | guard_sequence_item / dev | stored cases.jsonl | n/a (stored responses) | n/a | 95.9% / 1.0% | 95.9% / 1.0%（n=194） |
| `2026-10-11T112526523573Z-intent-gemini-gemini-3.1-flash-lite-lenient` | lenient / dev | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 706.0 vs report 706.0 (pre_guard (PLAN_PROMPT_BASE): 194 hits; guard_rules (PRE_SEQUENCE): 109 hits) | 194/194 | 90.7% / 3.6% | 92.8% / 3.6%（n=194） |
| `2026-10-11T114851107708Z-intent-ollama-qwen3-swallow-8b-rl-local-union_schema` | union_schema / dev | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 836.5 vs report 833.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) | 190/194 | 35.6% / 21.1% | 34.2% / 21.6%（n=190） |
| `2026-10-11T191200091981Z-intent-gemini-gemini-3.1-flash-lite-guard_claims` | guard_claims / all | stored cases.jsonl（3 条因计划变化重新裁定） | n/a (stored responses) | n/a | 68.0% / 14.0% | 78.0% / 14.0%（n=50） |
| `2026-10-11T193956473760Z-intent-gemini-gemini-3.1-flash-lite-default` | default / all | stored cases.jsonl（3 条因计划变化重新裁定） | n/a (stored responses) | n/a | 68.0% / 2.0% | 82.0% / 2.0%（n=50） |
| `2026-10-13T072950363331Z-intent-gemini-gemini-3.1-flash-lite-default` | default / test | stored cases.jsonl | n/a (stored responses) | n/a | 97.3% / 0.7% | 97.3% / 0.7%（n=292） |
