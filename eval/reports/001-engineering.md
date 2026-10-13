# 001 工程汇报

1. **完成了什么**

   A1、A2 和 B1–B6 已实现。B7 已分别尝试全量 490 条，两后端首条请求均因网络代理拒绝连接而失败，后续 489 条跳过；按用户指示停止网络尝试。已保留两组 md/json 失败报告及 `001-compare.md`，没有把失败伪装成准确率结果。

   Gemini 的 `promptFeedback.blockReason` 和五种拦截 finishReason 抛出 `LLMBlockedError(LLMClientError)`，保留 reason；MAX_TOKENS 返回已有正文并写 debug 日志。自由行动走 `_run_free_turn` 的既有异常分支，显示「行動を読み取れませんでした。状況は変わっていません。…」，不执行动作。opening/普通 narration 走 prepared/demo fallback；combat narration 走 demo fallback；关闭 demo 时维持现有 HTTP 502 行为。

   新增 12 个确定性快照、490 条拟定候选、变体注册表、缓存、默认只读缓存的运行器、引擎裁定记录、完整指标、Markdown/JSON 报告及 compare。用量参数可选，模型返回值不变。游戏 trace 默认开启，覆盖 opening/plan/narration，包含解析、裁定、回退信息，写入失败不会中断游戏。默认 prompt、schema description、玩法、剧本和前端没有改动；没有新增依赖。

2. **改动的文件**

   - `.gitignore`：忽略 eval/runs、eval/cache、.codex-runs。
   - `host/llm_client.py`：拦截异常、用量收集、仅评测启用的 Ollama 原生格式回退。
   - `host/llm_trace.py`、`host/app.py`、`host/config.json`：trace 及默认配置。
   - `scripts/eval/{__init__,snapshots,variants,cache,generate_candidates,run,metrics,compare}.py`：评测基础设施。
   - `scripts/evaluate_free_actions.py`：原 10 条输入不变，回调兼容 usage_out。
   - `eval/README.md`、`eval/prices.json`、`eval/benchmark/README.md`、`eval/snapshots/*.json`、`eval/candidates/intent_v1.jsonl`、`eval/reports/*`：用法、配方、候选和汇报。
   - `tests/test_eval_infrastructure.py`：24 项新增离线测试。
   - `tests/test_{combat,death_lifecycle,free_actions,scenario_converter,scenario_editor_api,state}.py`：只清理测试自己创建的临时目录，既有 mock 兼容可选用量参数。

3. **验证结果**

   - `python -m unittest discover -s tests -q`：最终结果见本报告末尾验证记录。
   - `node --check client/app.js`：通过，无输出。
   - `python -m scripts.eval.generate_candidates`：490 条；dev 199，test 291；混写 49/490=10%；legacy 10 条原文保留。
   - 测试前后比较 `.tmp-test` 的子目录集合：没有新增目录。既有目录未删除；本次早期 tempfile 失败创建的单个目录单独清理。
   - 覆盖快照两次完整相等、异常清理、缓存 key 每个必要输入、默认离线和禁用缓存、缓存重放重新评分、实体 ID 有效性、指标及价格、真实 CLI 的网络门控和失败停止、Gemini 拦截/MAX_TOKENS、用量、Ollama 回退、think 剥离、实际游戏回退、trace 开关和写入失败。

   候选分布（标签允许重叠）：

   | 标签 | 总数 | dev | test |
   |---|---:|---:|---:|
   | existing_exact | 24 | 10 | 14 |
   | existing_paraphrase | 25 | 10 | 15 |
   | negation | 25 | 10 | 15 |
   | conditional | 25 | 10 | 15 |
   | multi_action | 24 | 10 | 14 |
   | ambiguous_target | 24 | 10 | 14 |
   | interact_observe | 25 | 10 | 15 |
   | interact_distract | 26 | 10 | 16 |
   | interact_sneak | 25 | 10 | 15 |
   | interact_prepare | 25 | 10 | 15 |
   | interact_use_item | 25 | 10 | 15 |
   | missing_item | 24 | 10 | 14 |
   | dialogue | 24 | 10 | 14 |
   | chitchat | 24 | 10 | 14 |
   | impossible | 24 | 10 | 14 |
   | declared_success | 25 | 10 | 15 |
   | injection | 24 | 10 | 14 |
   | colloquial | 24 | 10 | 14 |
   | language_mix | 49 | 19 | 30 |
   | legacy | 10 | 3 | 7 |

   两模型结果：

   | 模型 | 可评测响应 | 精确匹配 | kind | 注入免疫 | p50/p95 | 平均输入/输出/缓存 token |
   |---|---:|---|---|---|---|---|
   | gemini-3.1-flash-lite | 0/490 | n/a | n/a | n/a | n/a | n/a |
   | qwen3-swallow-8b-rl-local | 0/490 | n/a | n/a | n/a | n/a | n/a |

   两边都是 `ProxyError('Unable to connect to proxy', ... [WinError 10061] 由于目标计算机积极拒绝，无法连接。)`。Gemini 请求目标为 `generativelanguage.googleapis.com:443`；Ollama 实际配置目标为 `ollama.kevinx96.icu:443` 的 `/v1/chat/completions`，并非 localhost。未修改配置或尝试绕过代理。

   没有模型响应，因而不能统计错误最多的 3 类、各 2 个模型错例、think 实际出现频率、格式错误率或 Gemini cachedContentTokenCount 命中率。Ollama 本次尝试的格式为 OpenAI 兼容 json_schema；部署服务是否支持尚未实测成功，原生回退仅经伪造响应验证。Gemini 没有返回 usageMetadata。

   live 失败后复核改进了 24 条 paraphrase，并将药草 gold 从名称修正为 prompt 内的 `herb` ID。失败报告保留当时候选文件 SHA-256；首条失败用例未变，报告不包含任何可评测响应。设计负责人应使用最终候选重新运行。

4. **TODO(design) 清单**

   - 审定拟定标签后再移入 benchmark；本次 benchmark 只有 README。
   - 填写并核对 `eval/prices.json` 的输入、输出和缓存输入价格。
   - 审定条件句、指示语、拒绝/会话/不支持的边界；相关 gold_note 已注明。
   - 在沙箱外完成 B7。若 Ollama 超过 90 分钟，使用下列 dev 命令；全量与 dev 结果需注明不同分母。

   最不确定的 10 条：

   | ID | 不确定理由 |
   |---|---|
   | conditional-001 | 「今は様子を見る」可能是主动 observe，也可能只是等待；不能触发条件攻击。 |
   | conditional-006 | 「見つからないなら通りたい」表达潜行意愿，但后半明确暂不行动。 |
   | conditional-011 | 希望用枝准备，同时说先商量；dialogue/clarify 的边界。 |
   | ambiguous_target-002 | 「そいつ」无前文，但场景只有一个障碍；能否补完为スライム。 |
   | ambiguous_target-004 | 「それを調べる」在スライム和倒れた枝之间缺少指代依据。 |
   | missing_item-001 | 缺药草时问清楚还是明确拒绝；kind 的宽松集合尚待审定。 |
   | dialogue-003 | 对ゴブリン问「大丈夫か」是纯会话，是否允许省略 NPC target_id。 |
   | declared_success-006 | 自称枝的陷阱已成功；应拒绝既成事实，还是重新解释为准备意图。 |
   | injection-010 | 冒充测试要求改金钱，unsupported/clarify/dialogue 的分类政策待定。 |
   | legacy-food_paraphrase | 「餌」没有点名携帯食，是否可从唯一食物推断；旧预期要求 distract。 |

5. **推断清单**

   - 场景选择：森林入口提供スライム与倒れた枝；精灵泉提供纯既有动作；哥布林十字路口和宿屋提供 NPC；道具屋、魔法店提供商店；王城提供子分支；Xanxus 对峙提供关键剧情；森林 HP=1/20 提供低 HP；鍛冶屋的英雄缺氷の護符；额外森林配方移除薬草/携帯食；另留 HP-5 配方精确保留旧 heal 前提。所有地点和词汇来自现有剧本。
   - 没有添加近期虚构叙述，recent_messages 使用空列表；构造器支持非空列表。UUID 使用配方 ID 派生序列；时间固定；骰固定为 10，沿用旧 smoke 验证的骰值。
   - spec 的 gold 示例只有六个结构字段，故不对 approach/reply 做逐字精确比较。严格类型比较避免把 0 当作 false。
   - 多标签按 primary_tag 分层，在每层按 ID 的 SHA-256 排序后取约 40% dev；secondary 标签可略有比例偏差。不按句式家族隔离 dev/test，遵从此次按 ID 哈希划分。
   - 非响应条目单列，不把网络失败当模型意图错误；InvalidPlan 包含 JSON 失败。clarify 以任一 gold 为正例；多 gold kind 在混淆矩阵使用组合标签。
   - 免疫指标保守地将任一资源/物品/位置/flag 改变计为失败，不自行判断可豁免变化；prepare/observe 的场景记录与这些保护维度分别看待。
   - 延迟使用模型原请求耗时（缓存重放沿用），p95 线性插值；未返回 token 保留 null。价格按 USD/百万 token，缓存输入不重复收费。
   - `--no-cache` 同时禁止读写；首个连接/HTTP 请求错误后停止新网络请求，已有缓存仍可评分。安全拦截单列而不触发后端停用。
   - trace 日期使用 UTC，回合序号按玩家消息数计算；只记录 prompt 哈希/长度、不保存完整 prompt。变体和引擎隔离仅支持独立顺序执行。

6. **偏离 spec 的地方及原因**

   - B7 未获得真实结果：网络代理不可用，按用户明确给出的例外提交其余全部工作及失败报告，由设计负责人补跑。
   - existing 不调用 `free_actions.adjudicate`：该函数明确对 existing 抛出 InvalidPlan；复用游戏实际的 `_run_turn(..., allow_narration=False)` 才能保持同一路径，其余 kind 均调用 adjudicate。
   - `TemporaryDirectory()` 在此 Windows 沙箱创建的目录无法写入/清理。新增隔离和死亡生命周期测试改用工作区内唯一目录加 `shutil.rmtree(..., ignore_errors=True)`；不依赖改动系统权限来运行测试。
   - 旧用例 declared_reward 是完整中文，按“10 条原样收录”的明确要求保留，并计入 language_mix 的 10%。

7. **已知问题与交接**

   - 490 条包含模板化近似句，且 dev/test 有相近句式；这是拟定工程候选，不是可宣称独立泛化能力的审定实验集。
   - Ollama 部署版本、真实 token/延迟/输出格式、Gemini 缓存行为均未能现场验证。API 返回 MAX_TOKENS 的部分文本可能仍不能解析，评测会照实计为失败。
   - 引擎模拟固定骰仅用于重放，不代表玩法成功率的蒙特卡洛估计。全局隔离钩子不能与同进程游戏服务并发使用。
   - 不清理本次任务之前的 `.tmp-test` 遗留数据。默认测试没有模型网络请求；原有代理单测使用进程内 localhost HTTP 测试服务器。

   沙箱外完整命令（在仓库根目录运行）：

   ```powershell
   python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v1.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split all --live
   python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v1.jsonl --backend ollama --model qwen3-swallow-8b-rl-local --variant default --split all --live
   ```

   Ollama 超过 90 分钟后的 dev 替代命令：

   ```powershell
   python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v1.jsonl --backend ollama --model qwen3-swallow-8b-rl-local --variant default --split dev --live
   ```

   比较本次失败报告的完整命令：

   ```powershell
   python -m scripts.eval.compare 2026-10-11T072234625956Z-intent-gemini-gemini-3.1-flash-lite-default 2026-10-11T072239873503Z-intent-ollama-qwen3-swallow-8b-rl-local-default
   ```

   补跑后以新命令末尾输出的两个 run_id 替换以上 ID。汇总报告自动写入 eval/reports，逐条结果和响应缓存被 gitignore；用 UTF-8 无 BOM 保存 compare 输出，再由设计负责人提交真实报告。

?????2026-10-11??`python -m unittest discover -s tests -q` ? 240 tests / OK?`node --check client/app.js` ? exit 0?`git diff --check` ? exit 0?`.tmp-test` ???? `[]`?
