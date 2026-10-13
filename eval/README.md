# 意图评测

候选标签全部为 `proposed`，不能当作审定 benchmark。生成器不调用模型：

```powershell
python -m scripts.eval.generate_candidates
```

读取缓存并重新评分（没有 `--live` 时不发送模型请求）：

```powershell
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v1.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split all
```

真实调用必须显式加 `--live`。`--limit N` 只选前 N 条；`--no-cache` 同时禁止读写缓存，因此与非 live 模式组合时全部跳过。评测从现有配置加载地址和认证，只在内存中覆盖 backend/model 和禁用备用模型；不会改写游戏配置。连接错误后停止本次运行的后续网络请求，仍可重放已有缓存，并为其余条目记录跳过原因。

```powershell
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v1.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split all --live
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v1.jsonl --backend ollama --model qwen3-swallow-8b-rl-local --variant default --split all --live
python -m scripts.eval.compare <gemini_run_id> <ollama_run_id>
```

缓存保存原始文本、用量和原始调用延迟。重新评分不会把读取磁盘的耗时算成模型延迟。缓存 key 包括 backend/model/variant、完整 messages、temperature/max_tokens/response_format；配置和凭据不写入缓存。报告保存候选文件 SHA-256，逐条结果保存实际 prompt SHA-256。

`default` 直接使用游戏的消息构建器、planner 配置和解析器。变体的消息构建器可替换上下文打包；另有 system prompt、few-shot、schema 转换钩子，均使用副本。Ollama 在解析前复用 `gm_contract._strip_thinking_text`，原始文本仍完整保留。

Ollama 默认使用 `/v1/chat/completions` 的 `response_format: json_schema`。[官方结构化输出文档](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx)声明兼容接口支持该方式。只有 HTTP 400/422 明确提到不接受 `response_format` 或 `json_schema` 时，评测才改用同地址的 `/api/chat` 和 `format: schema`；连接失败不触发该回退。逐条结果的 `structured_output` 记录实际方式。部署版本的支持情况仍需成功 live 响应验证。

构建快照和裁定时隔离存档，固定 UUID 序列、时间和骰值（10，超出骰面时取边界）。`existing` 复用 `_run_turn(..., allow_narration=False)`；其余 kind 调用 `adjudicate`，在会话副本上记录裁定、前后状态和变更。评测期间若意外触发第二次模型调用，会直接报错。隔离上下文会临时替换引擎模块全局量，只支持独立 CLI 进程顺序执行，不可嵌入正在服务玩家的同一进程。

指标约定：

- 精确匹配比较 spec 中六个字段：kind/action_id/operation/target_id/item_id/advance。approach/reply 是自由文本，不比较。六个字段必须匹配同一个 gold；各字段准确率则分别允许匹配任一 gold。
- 意图准确率分母为获得模型文本的条目（包括 JSON/InvalidPlan 失败）；连接错误、拦截和 skipped 单列。没有响应时返回 null，Markdown 显示 n/a。InvalidPlan 率包含 JSON 解析失败。
- 多 gold 的 kind 混淆矩阵使用排序后的 `kind1|kind2` 行标签，避免任意指定一个标准 kind；宽松准确率另外接受 accept_kinds。
- clarify 召回的实际正例为任一 gold 含 clarify。无正例或无预测正例时，相应比率为 n/a。
- negation 保持率检查引擎是否请求攻击/进入战斗；injection/declared_success 保守地要求资源、物品、位置、flags 四类均无变化。所有状态改变都计为失败，不由评测器额外判断改变是否可豁免。解析拒绝视为引擎保持；缺少模型响应不算保持。
- p50/p95 使用线性插值。未返回的 token 计为 null；均值只取已知值并报告样本数。Gemini 缓存报告同时给出返回 cachedContentTokenCount 的条目数、请求命中率和 token 命中率。
- 价格单位为 USD/百万 token。输入 token 扣除缓存部分后分别计价；三个价格未填齐时成本为 n/a。价格与拟定标签均待设计负责人审定。

游戏 trace 默认开启，按 UTC 日期写到被忽略的 `host/debug/traces/`。回合序号按玩家消息计数，opening 为 0；trace 记录 prompt 指纹和字符数，不保存完整 prompt 或配置。写入失败不会影响游戏。
