# 006 实验：plan 的 schema 形状与解析容错

## 背景（设计负责人在沙箱外实跑得到）
- 本地 `qwen3-swallow-8b-rl-local` 跑 v1 全部 490 条，**全部 InvalidPlan**：459 条 `unexpected action ID`，31 条 `existing action cannot include another operation`。原因是模型把所有字段都填满了（例如 kind=dialogue，却同时填了 action_id、operation、item_id）。现在的 `PLAN_SCHEMA` 是一个扁平对象，"不同 kind 下哪些字段必须为空"这条约束只写在提示词里，小模型不遵守。Gemini 遵守（InvalidPlan 0.6%）。
- 这正是研究问题的一部分：**同样的语义契约，换一种 schema 形状或解析策略，小模型能否达到可用水平？**
- 另外，Gemini 免费额度是每个模型每天 500 次。超额后返回 429，`retryDelay` 约 13 小时，运行器就照着去等了。

## A. 运行器：额度用尽时停止
- 429 的错误体里如果 `quotaId` 含 `PerDay`，或者 `retryDelay` 超过 120 秒，**不要等待**，立刻停止 live 请求，记为 `quota_exhausted`。报告里写明停在第几条、需要等多久。已有的结果正常写出。
- 写测试（伪造错误体）。

## B. 新增两个变体（只在评测里用，不改游戏默认值）
1. **`lenient`（解析容错）**：模型请求和 `default` 完全相同，所以**直接复用 default 的缓存**，不额外调用模型。解析时，先按 kind 清掉无关字段，再交给 `parse_plan`：
   - existing：只保留 action_id，其余字段清空，advance 设为 false
   - interact：清空 action_id
   - dialogue/clarify/unsupported：清空 action_id、operation、item_id；advance 设为 false；target_id 只在 dialogue 时保留
   - 记录每条被清掉的字段。另外记录 **conflict**：被清掉的字段和 kind 语义矛盾的情况，例如 kind=dialogue 却带 operation=use_item（模型其实想执行操作）。conflict 单独统计，作为"容错掩盖了误解"的风险指标。
2. **`union_schema`（判别联合 schema）**：把 `PLAN_SCHEMA` 改写成按 kind 的 `anyOf`。每个分支用 `const` 固定 kind；无关字段用 `const: ""` 或 `const: false`；`action_id`、`operation` 的取值尽量用 `enum` 列出当前快照里可用的 ID。这样约束在解码层面就生效。
   - 提示词文字不变。schema 的 `description` 沿用现有字段说明，不重写。
   - 确认 Gemini 的 `responseJsonSchema` 和 Ollama 的 `format`（或 OpenAI 兼容接口的 `json_schema`）是否都接受这种 schema。不接受时写明具体错误，并给出能用的最接近形状。
   - `enum` 按快照动态生成：这本身也是一项改动，要在报告里说明，它和"联合结构"本身的效果需要分开（能分开时，做一个"联合结构但不加 enum"的子变体 `union_schema_noenum`）。

## C. 指标
报告按变体并列：S0+S1、S3、InvalidPlan、conflict（只有 lenient 有）、延迟、token。`compare` 支持同一模型的多个变体对比。

## D. 运行
沙箱没有网络。完成后给出命令清单，由设计负责人运行：
- 本地 4 个模型（qwen3-swallow-8b-rl、qwen2.5-7b、elyza-jp-8b、qwen2.5-3b-q8）× {default, lenient, union_schema, union_schema_noenum}，在 v2 的 **dev** split 上（`eval/benchmark/intent_v2.jsonl`）。
- Gemini × 同样 4 个变体，v2 dev（Gemini 每天有 500 次额度，命令里要标明预计的请求数）。

## 不做
- 不改游戏默认的 schema 和解析。是否把某个变体设为默认，由设计负责人看过数据再决定。
- 不改提示词文字。

## 验收
- 两条验证命令通过；离线测试覆盖：额度用尽时停止、lenient 的清理规则和 conflict 判定、union schema 的生成（含按快照生成 enum）、lenient 复用 default 缓存（不产生新的 cache key）。

## 汇报要回答
1. 两个 API（Gemini 和 Ollama）是否接受 union schema；如果不接受，怎么处理的。
2. 估算每个变体需要的请求数和本地运行时间。
3. 其余按 `docs/roles/engineering.md` 的汇报格式。
