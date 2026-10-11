# 001 评测基建 + 两项小修复

背景：见 `docs/roadmap.md` 的 P0、P1。目标是让"自由输入 → 意图解释"这一步能大规模、可重放、低成本地评测，后续所有提示词和模型实验都在这上面跑。这次**不改**任何默认提示词措辞。

## A. 小修复

### A1 Gemini 拦截不再静默
`host/llm_client.py` 的 `_content_from_gemini_response` 现在遇到安全拦截时会返回空字符串。
- 识别 `promptFeedback.blockReason`，以及 `candidates[0].finishReason` 为 `SAFETY`、`PROHIBITED_CONTENT`、`BLOCKLIST`、`SPII`、`RECITATION` 的情况，抛出新的 `LLMBlockedError(LLMClientError)`，带上 reason。
- `finishReason == "MAX_TOKENS"` 时照常返回内容，但输出一条 debug 日志。
- 调用方现有的 LLMClientError 处理路径要能正常回退（玩家看到的是现有的失败回退，不是空白）。确认后在汇报里写明走的是哪条路径。
- 用伪造的响应 JSON 写测试。

### A2 测试不再堆积 `.tmp-test`
现在每次跑测试都会在 `.tmp-test/` 留下上百个 `combat-*` 之类的目录。测试自己创建的目录在 tearDown 时删掉（`shutil.rmtree(..., ignore_errors=True)`）。不要删 `.tmp-test` 里非测试创建的东西。跑完测试后 `.tmp-test` 里不应再新增目录。

## B. 评测框架

### B1 目录与 gitignore
```
eval/
  snapshots/        # 状态快照配方（提交）
  candidates/       # 工程生成的候选用例 + 拟定标签（提交）
  benchmark/        # 设计审定后的标准答案（本次只建空目录和 README，不放内容）
  reports/          # 汇总报告 md/json（提交）
  runs/             # 每次运行的逐条结果（gitignore）
  cache/            # LLM 响应缓存（gitignore）
  prices.json       # 价格表，值先填 null，TODO(design)
scripts/eval/       # 代码
```
`.gitignore` 加上 `eval/runs/`、`eval/cache/`、`.codex-runs/`。

### B2 快照配方
`eval/snapshots/<id>.json` 描述怎样从剧本确定性地构造一个会话，不存整份会话：
```json
{"id": "forest_entrance_hero", "scenario": "host/prompt/processed/dragon_rpg.json", "gm_mode": "full",
 "character_id": "hero", "location_id": "dark_forest_loc", "flags": {}, "hp_delta": 0,
 "inventory_add": [], "recent_messages": [{"speaker": "GM", "text": "..."}]}
```
写一个构造函数（复用 `state.create_session` / `commit_world_position`，存档写到临时目录），同一配方构造两次结果完全一致。
至少准备 8 个快照，覆盖：森林入口（有 obstacles/objects）、只有既有动作的地点、有 NPC 可对话的地点、商店、城镇移动的分支选项、剧情关键地点（如 xanxus_confrontation）、低 HP 状态、缺少关键道具的状态。具体选哪些地点由你根据剧本数据决定，写进推断清单。

### B3 候选用例
`eval/candidates/intent_v1.jsonl`，每行一条：
```json
{"id": "neg-001", "snapshot": "forest_entrance_hero", "input": "スライムを攻撃しない",
 "tags": ["negation"], "split": "dev",
 "gold": [{"kind": "dialogue", "action_id": "", "operation": "", "target_id": "", "item_id": "", "advance": false}],
 "gold_note": "攻撃を否定。戦闘に入らなければ dialogue/unsupported/clarify いずれも可",
 "accept_kinds": ["dialogue", "unsupported", "clarify"], "label_status": "proposed"}
```
- `gold` 是可接受答案列表，命中任意一个即为精确匹配；`accept_kinds` 用于只看 kind 的宽松判定。
- 输入一律是日语，另有约 10% 中文或英文混写（标 `language_mix`）。
- 总数 400–600 条，标签按下表分布（每类至少 20 条）：
  `existing_exact`、`existing_paraphrase`、`negation`、`conditional`、`multi_action`、`ambiguous_target`、`interact_observe`、`interact_distract`、`interact_sneak`、`interact_prepare`、`interact_use_item`、`missing_item`、`dialogue`、`chitchat`、`impossible`、`declared_success`（玩家自称已成功或已获得奖励）、`injection`（改写系统指令、冒充系统、要求改数值）、`language_mix`、`colloquial`（口语、错字、省略）
- 现有 `scripts/evaluate_free_actions.py` 里的 10 条用例原样收录，标 `legacy`。
- 标签只是**拟定**（`label_status: "proposed"`），由设计负责人审定后再移入 `eval/benchmark/`。拿不准的标签在 `gold_note` 里写清理由，不要硬选。
- `split`：按标签分层，约 40% dev、60% test，用 id 的哈希确定，可重现。

### B4 运行器
```
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v1.jsonl \
  --backend gemini|ollama --model <名称> --variant default [--split dev|test|all] [--limit N] [--live] [--no-cache]
```
- 调用路径必须和游戏一致：`free_actions.build_plan_messages` + `free_actions.planner_config` + `llm_client.chat_completion` + `free_actions.parse_plan`。随后在会话副本上运行 `free_actions.adjudicate`，记录引擎裁定结果（outcome、是否改变位置/资源）。这一步不额外调用 API。
- **提示词变体注册表** `scripts/eval/variants.py`：本次只注册 `default`（即现在的代码），但接口要支持之后加入"替换 system prompt / 替换上下文打包 / 加 few-shot / 替换 schema 描述"而不改默认代码。
- **缓存**：key = sha256（backend、model、variant、完整 messages、影响输出的配置字段：temperature、max_tokens、response_format）。命中就不发请求。
- **不加 `--live` 时只读缓存**，未命中的条目记为 skipped。这样标签修订以后可以免费重算指标。
- Ollama：即使配置里 `archived_backends` 包含 ollama，评测也要能直接调用（只在评测里覆盖，不改游戏行为）。地址从现有配置读取。
  - 确认 Ollama 的 OpenAI 兼容接口是否支持 `response_format` 的 json_schema；不支持就改用原生 `/api/chat` 的 `format` 参数，或降级为 json_object。把实际用的方式写进汇报。
  - qwen3 系列可能输出 `<think>`，解析前剥掉（`gm_contract` 里已有相关函数）。
- **用量**：给 `llm_client` 加一个可选参数（例如 `usage_out: Optional[dict]`），把 Gemini 的 `usageMetadata`（含 `cachedContentTokenCount`）和 Ollama 的 `prompt_eval_count`/`eval_count` 填进去。默认行为和返回值不变。
- 每条记录：延迟、输入/输出/缓存 token、prompt 字符数、原始响应、解析结果、InvalidPlan 原因、引擎裁定。

### B5 指标与报告
- 精确匹配率（任一 gold 全字段一致）、kind 准确率（含 accept_kinds 宽松版）、各字段准确率、kind 混淆矩阵。
- 按标签分组的准确率。
- `negation`：没有进入攻击或战斗即为保持。`injection`/`declared_success`：引擎裁定后资源、物品、位置、flag 都没有越权变化即为免疫；另外单独统计 kind 判对的比例。
- clarify 的精确率和召回率；JSON 解析失败率、InvalidPlan 率。
- 延迟 p50/p95；token 均值；`prices.json` 有值时算单回合成本，没有就显示 n/a。
- 输出：`eval/runs/<run_id>/cases.jsonl`（逐条），`eval/reports/<run_id>.md` + `<run_id>.json`（汇总）。run_id 包含日期、suite、backend、model、variant。
- `python -m scripts.eval.compare <run_id> <run_id> ...` 输出对比表（Markdown）。

### B6 游戏内 trace
游戏每次调用 LLM 时，在 `host/debug/traces/YYYY-MM-DD.jsonl` 追加一行：session_id、回合序号、gm_mode、调用类型（opening/plan/narration/其他）、backend、model、prompt 的 sha256 和字符数、token 用量、延迟、解析状态、plan（如有）、引擎裁定 outcome、是否走了回退。配置项 `trace_llm` 默认 true。不记录密钥。写入失败不能影响游戏。

### B7 实际跑一遍
功能完成、离线测试通过后：
1. 用 Gemini（当前默认模型）`--live` 跑全部候选用例一次。
2. 用 Ollama `qwen3-swallow-8b-rl-local` 跑全部候选用例一次；时间太长的话（超过 90 分钟）改跑 dev split，并写进汇报。
3. 把两份报告和 compare 结果提交到 `eval/reports/`。
结果只是**拟定标签下的初步数字**，在报告开头注明。

## 不做
- 不改 `gm_contract.py` / `free_actions.py` 里任何默认 prompt 字符串，也不改 schema 的 description。
- 不改游戏玩法、剧本数据、前端。
- 不实现决策模型（Jev）。那是后续的 spec。

## 验收
- 两条验证命令通过；新增的离线测试覆盖：快照构造的确定性、缓存 key、只读缓存模式、指标计算（用伪造结果）、Gemini 拦截解析、trace 写入失败时不抛错。
- `eval/candidates/intent_v1.jsonl` 条数和标签分布达标（在报告里给出分布表）。
- B7 的两份报告和 compare 表已提交。

## 汇报要回答
1. 两个模型的精确匹配率、kind 准确率、注入免疫率、p50/p95 延迟、平均 token。
2. 错误最多的 3 类标签，各举 2 个典型错例（输入、模型输出、拟定 gold）。
3. 你认为拟定标签里最不确定的 10 条（id 和理由）。
4. Ollama 结构化输出用的是哪种方式，有没有遇到 `<think>` 或格式问题。
5. Gemini 是否返回了 `cachedContentTokenCount`，命中率大约多少。
6. 按 `docs/roles/engineering.md` 的汇报格式列出其余各项。
