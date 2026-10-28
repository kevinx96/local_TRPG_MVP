# 表 3 与 E4 表的 v1.2 重算（离线）

生成：`python -m scripts.eval.paper_table3`（不联网，不调用模型）。逐格用 `scripts.eval.paired_stats.load_run` 读取原运行的模型响应（有 `eval/runs/<id>/cases.jsonl` 时读逐条记录，否则按原 backend/model/变体名与匹配的 system prompt 离线重放 `eval/cache`），再用当前 `parse_plan`（含 existing 归一化）、当前 gold 与 `metrics.summarize` 评分，即评分 v1.2。缓存缺失的条目不计入分母。

## 表 3（v2 dev，评分 v1.2）

每格为“S0+S1 / S3”，括号内为 InvalidPlan 率（IP），Flat-Lenient 列为冲突率。

| 模型 | Flat-Strict | Flat-Lenient | Union-Enum | Union-NoEnum |
|---|---|---|---|---|
| Gemini 3.1 Flash-Lite | 92.8% / 3.6%（IP 0.0%） | 92.8% / 3.6%（冲突 4.1%） | 0.0% / 0.0%（IP 100.0%） | 0.0% / 0.0%（IP 100.0%） |
| qwen3-swallow-8b-rl | 0.5% / 2.6%（IP 96.8%） | 34.7% / 3.2%（冲突 100.0%） | 34.2% / 21.6%（IP 0.0%） | 33.7% / 16.8%（IP 38.4%） |
| elyza-jp-8b | 0.0% / 0.0%（IP 100.0%） | 31.6% / 1.6%（冲突 100.0%） | 35.3% / 1.6%（IP 1.6%） | 34.2% / 2.1%（IP 0.0%） |
| qwen2.5-3b-q8 | 4.7% / 1.1%（IP 93.7%） | 25.3% / 3.2%（冲突 98.9%） | 31.6% / 20.0%（IP 0.0%） | 31.6% / 15.3%（IP 41.1%） |
| qwen2.5-7b | 24.2% / 10.0%（IP 62.1%） | 47.4% / 12.1%（冲突 100.0%） | 33.2% / 20.0%（IP 0.0%） | 33.2% / 14.7%（IP 39.5%） |

### 分母与条数

| 模型 | Flat-Strict | Flat-Lenient | Union-Enum | Union-NoEnum |
|---|---|---|---|---|
| Gemini 3.1 Flash-Lite | n=194/194；S0+S1 180，S3 7，IP 0，S4 0 | n=194/194；S0+S1 180，S3 7，IP 0，冲突 8，S4 0 | n=190/194；S0+S1 0，S3 0，IP 190，S4 0 | n=190/194；S0+S1 0，S3 0，IP 190，S4 0 |
| qwen3-swallow-8b-rl | n=190/194；S0+S1 1，S3 5，IP 184，S4 0 | n=190/194；S0+S1 66，S3 6，IP 1，冲突 190，S4 0 | n=190/194；S0+S1 65，S3 41，IP 0，S4 0 | n=190/194；S0+S1 64，S3 32，IP 73，S4 0 |
| elyza-jp-8b | n=190/194；S0+S1 0，S3 0，IP 190，S4 0 | n=190/194；S0+S1 60，S3 3，IP 0，冲突 190，S4 0 | n=190/194；S0+S1 67，S3 3，IP 3，S4 0 | n=190/194；S0+S1 65，S3 4，IP 0，S4 0 |
| qwen2.5-3b-q8 | n=190/194；S0+S1 9，S3 2，IP 178，S4 0 | n=190/194；S0+S1 48，S3 6，IP 15，冲突 188，S4 0 | n=190/194；S0+S1 60，S3 38，IP 0，S4 0 | n=190/194；S0+S1 60，S3 29，IP 78，S4 0 |
| qwen2.5-7b | n=190/194；S0+S1 46，S3 19，IP 118，S4 0 | n=190/194；S0+S1 90，S3 23，IP 9，冲突 190，S4 0 | n=190/194；S0+S1 63，S3 38，IP 0，S4 0 | n=190/194；S0+S1 63，S3 28，IP 75，S4 0 |

## 表 3（v2 dev，评分 v1.1，原运行报告）

| 模型 | Flat-Strict | Flat-Lenient | Union-Enum | Union-NoEnum |
|---|---|---|---|---|
| Gemini 3.1 Flash-Lite | 89.7% / 3.1%（IP 1.5%） | 90.7% / 3.6%（冲突 4.1%） | 0.0% / 0.0%（IP 100.0%） | 0.0% / 0.0%（IP 100.0%） |
| qwen3-swallow-8b-rl | 0.0% / 0.0%（IP 100.0%） | 15.5% / 3.1%（冲突 100.0%） | 35.6% / 21.1%（IP 0.0%） | 35.1% / 16.5%（IP 37.6%） |
| elyza-jp-8b | 0.0% / 0.0%（IP 100.0%） | 24.7% / 1.5%（冲突 100.0%） | 30.9% / 1.5%（IP 1.5%） | 30.4% / 2.1%（IP 0.0%） |
| qwen2.5-3b-q8 | 0.0% / 0.0%（IP 100.0%） | 21.6% / 3.1%（冲突 99.0%） | 33.0% / 19.6%（IP 0.0%） | 33.0% / 14.9%（IP 40.2%） |
| qwen2.5-7b | 0.0% / 0.0%（IP 100.0%） | 42.8% / 11.9%（冲突 100.0%） | 34.5% / 19.6%（IP 0.0%） | 34.5% / 14.4%（IP 38.7%） |

## E4：各模型 v1.2 下 S0+S1 最高的配置

延迟取自 Flat-Strict 原运行报告（194 次请求的 p50 / p95，与评分无关）；成本同原报告。

| 模型 | 最佳配置 | n | S0+S1 | S3 | p50 / p95（Flat-Strict 请求） | 每回合成本 |
|---|---|---:|---|---|---|---|
| Gemini 3.1 Flash-Lite | Flat-Strict | 194 | 92.8%（180） | 3.6%（7） | 1.00 / 1.23 s | $0.000302 |
| qwen2.5-7b | Flat-Lenient | 190 | 47.4%（90） | 12.1%（23） | 4.59 / 5.29 s | 0 |
| elyza-jp-8b | Union-Enum | 190 | 35.3%（67） | 1.6%（3） | 4.23 / 5.12 s | 0 |
| qwen3-swallow-8b-rl | Flat-Lenient | 190 | 34.7%（66） | 3.2%（6） | 5.95 / 10.36 s | 0 |
| qwen2.5-3b-q8 | Union-NoEnum | 190 | 31.6%（60） | 15.3%（29） | 3.97 / 4.51 s | 0 |

## 与配对检验报告的核对

`eval/reports/paper-paired-stats.md` 运行表中与本网格重合的 4 个运行，其 v1.2 S0+S1 / S3 / n 与本表逐一一致。

## 运行来源

| 模型 | 列 | run id | 来源 | 匹配的 system prompt |
|---|---|---|---|---|
| Gemini 3.1 Flash-Lite | Flat-Strict | `2026-10-11T112514831356Z-intent-gemini-gemini-3.1-flash-lite-default` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 706.0 vs report 706.0 (pre_guard (PLAN_PROMPT_BASE): 194 hits; guard_rules (PRE_SEQUENCE): 109 hits) |
| Gemini 3.1 Flash-Lite | Flat-Lenient | `2026-10-11T112526523573Z-intent-gemini-gemini-3.1-flash-lite-lenient` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 706.0 vs report 706.0 (pre_guard (PLAN_PROMPT_BASE): 194 hits; guard_rules (PRE_SEQUENCE): 109 hits) |
| Gemini 3.1 Flash-Lite | Union-Enum | `2026-10-11T112538606761Z-intent-gemini-gemini-3.1-flash-lite-union_schema` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 708.3 vs report 706.0 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| Gemini 3.1 Flash-Lite | Union-NoEnum | `2026-10-11T113141950061Z-intent-gemini-gemini-3.1-flash-lite-union_schema_noenum` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 708.3 vs report 706.0 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen3-swallow-8b-rl | Flat-Strict | `2026-10-11T112514831499Z-intent-ollama-qwen3-swallow-8b-rl-local-default` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 836.5 vs report 833.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen3-swallow-8b-rl | Flat-Lenient | `2026-10-11T114837268186Z-intent-ollama-qwen3-swallow-8b-rl-local-lenient` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 836.5 vs report 833.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen3-swallow-8b-rl | Union-Enum | `2026-10-11T114851107708Z-intent-ollama-qwen3-swallow-8b-rl-local-union_schema` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 836.5 vs report 833.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen3-swallow-8b-rl | Union-NoEnum | `2026-10-11T121149336492Z-intent-ollama-qwen3-swallow-8b-rl-local-union_schema_noenum` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 836.5 vs report 833.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| elyza-jp-8b | Flat-Strict | `2026-10-11T122755485947Z-intent-ollama-elyza-jp-8b-local-default` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 824.4 vs report 821.7 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| elyza-jp-8b | Flat-Lenient | `2026-10-11T124207361839Z-intent-ollama-elyza-jp-8b-local-lenient` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 824.4 vs report 821.7 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| elyza-jp-8b | Union-Enum | `2026-10-11T124213992341Z-intent-ollama-elyza-jp-8b-local-union_schema` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 824.4 vs report 821.7 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| elyza-jp-8b | Union-NoEnum | `2026-10-11T125600553788Z-intent-ollama-elyza-jp-8b-local-union_schema_noenum` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 824.4 vs report 821.7 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen2.5-3b-q8 | Flat-Strict | `2026-10-11T130923957822Z-intent-ollama-qwen2.5-3b-instruct-q8-0-local-default` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 832.5 vs report 829.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen2.5-3b-q8 | Flat-Lenient | `2026-10-11T132243419395Z-intent-ollama-qwen2.5-3b-instruct-q8-0-local-lenient` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 832.5 vs report 829.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen2.5-3b-q8 | Union-Enum | `2026-10-11T132250297569Z-intent-ollama-qwen2.5-3b-instruct-q8-0-local-union_schema` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 832.5 vs report 829.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen2.5-3b-q8 | Union-NoEnum | `2026-10-11T133323873595Z-intent-ollama-qwen2.5-3b-instruct-q8-0-local-union_schema_noenum` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 832.5 vs report 829.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen2.5-7b | Flat-Strict | `2026-10-11T134405010054Z-intent-ollama-qwen2.5-7b-instruct-local-default` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 832.5 vs report 829.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen2.5-7b | Flat-Lenient | `2026-10-11T135915630752Z-intent-ollama-qwen2.5-7b-instruct-local-lenient` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 832.5 vs report 829.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen2.5-7b | Union-Enum | `2026-10-11T135922712080Z-intent-ollama-qwen2.5-7b-instruct-local-union_schema` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 832.5 vs report 829.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
| qwen2.5-7b | Union-NoEnum | `2026-10-11T141110622073Z-intent-ollama-qwen2.5-7b-instruct-local-union_schema_noenum` | cache replay | pre_guard (PLAN_PROMPT_BASE); cached input-token mean 832.5 vs report 829.9 (pre_guard (PLAN_PROMPT_BASE): 190 hits) |
