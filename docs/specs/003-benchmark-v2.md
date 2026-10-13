# 003 意图 benchmark v2

背景：v1 候选（`eval/candidates/intent_v1.jsonl`）可以当冒烟测试，但不能当正式测试集：
- 490 条里约一半只是在句首加「今は、」得到的复制，真正不同的句子约 245 条；dev 和 test 之间有大量近似句。
- 371/490 条集中在森林入口一个快照上，而且只用了勇者。
- gold 规则太死，见 `eval/benchmark/LABELING.md`（设计负责人已写好，**本任务的标注必须遵守它**）。

## 目标
产出 `eval/candidates/intent_v2.jsonl`（拟定），用于设计负责人审定后成为正式 benchmark。

## 要求

### 快照（`eval/snapshots/`，可以复用 v1 的）
- 至少 20 个快照，覆盖全部 4 个场景（王城、闇の森、村、竜の谷）中有可执行动作的地点。
- 至少用到 3 个可选职业：hero、mage、thief（各自背包不同，影响 use_item 和 missing_item 的判定）。
- 至少 5 个快照带 `recent_messages`（GM 刚问过问题、刚描述完结果），用来测省略和承接上文，例如「じゃあそれで」「さっきの方法でもう一回」。
- 森林入口这一个快照的用例不超过总数的 25%。

### 用例
- 总数 450–550 条，**每一条都要单独写**。不能用模板拼接、加前缀或替换对象名来批量生成。可以用脚本辅助检查和组装 JSON，但输入句本身要逐条写。
- 自动检查：任意两条输入的字符 3-gram Jaccard 相似度超过 0.6 的，必须属于同一 `family`（同一句式家族）；脚本输出违规列表，必须为 0。
- 标签沿用 v1 的 19 类，每类至少 20 条，另加：
  - `context_followup`：依赖 `recent_messages` 的输入
  - `deixis_unique`、`deixis_multi`：指示词指向唯一对象或多个候选（取代 v1 的 ambiguous_target）
  - `sequential`、`parallel`：顺序动作和并列动作（取代 v1 的 multi_action）
  - `excluded_means`：明确排除某种手段（「道具を使わず」「戦わずに」）
- 日语要自然：包括口语、省略、敬体和常体混用；约 10% 混入中文或英文。
- 每条字段：
  ```json
  {"id": "...", "family": "...", "snapshot": "...", "input": "...", "tags": [...], "primary_tag": "...",
   "gold": [{...首选...}, {...可接受...}], "harmful": {"operation": [...], "kind": [...], "action_id": [...]},
   "gold_note": "依据 LABELING.md 第 N 条…", "label_status": "proposed", "split": "dev|test"}
  ```
- `split`：按 `family` 分组，在各个 primary_tag 内分层，约 40% dev、60% test，用 family 的哈希确定。

### 评分
- `scripts/eval/metrics.py` 支持 LABELING.md 的严重度：S0、S1、S2、S3（S4 沿用 002 的 `unearned_change`）。
  - S0：命中 gold[0]；S1：命中 gold 里的其他答案；S3：命中 `harmful`，或者（没写 harmful 时）触发了有代价的操作而 gold 里没有任何有代价的操作；S2：其余。
  - "有代价的操作"的判定从引擎数据推导（消耗物品、SP/MP、开战、移动、需要判定），不要写死列表。
- 报告新增：S0+S1 比例、S3 比例、各标签的 S3 数、`engine_caught` 数。
- v1 文件和旧指标保持可用，不要删除。

### 实跑
沙箱没有网络，不要尝试 live。完成后汇报里给出 Gemini 和 Ollama 两条完整命令，由设计负责人运行。

## 不做
- 不改默认提示词、schema 描述和游戏逻辑。
- 不删 v1。

## 验收
- 两条验证命令通过；相似度检查违规数为 0；快照和标签分布达到上面的要求（报告里给出分布表）。
- 离线测试覆盖严重度判定（伪造 plan），包括"有代价操作"的推导。

## 汇报要回答
1. 分布表（快照 × 标签、职业、split）。
2. 你觉得最难标、最可能有争议的 15 条，附理由，并引用 LABELING.md 的条号。
3. LABELING.md 没覆盖到、你不得不自己判断的情况（这些会补进规范）。
4. 其余按 `docs/roles/engineering.md` 的汇报格式。
