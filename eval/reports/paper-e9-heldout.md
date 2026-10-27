# E9 held-out v3：正式运行结果

正式运行只有这一次：`2026-10-27T221108918697Z-heldout-v3`（live，非 fake）。预注册见 `eval/benchmark/heldout_v3/PREREGISTRATION.md`，锁定 commit 为 `216f99e`。

**运行条件**：
- 模型 gemini-3.1-flash-lite，变体 default（冻结 v2 兼容模式），评分 v1.2。
- temperature 0.2，max_tokens 700，no_cache。
- 运行前 `verify_registration` 和 `verify_lock` 都通过。
- report.json 显示 `incomplete=false`、`integrity_error=null`，99 条全部为 `ok`，没有重试。

**成本**：
- 运行前估算的上限是 0.1405 USD。
- 按实际 usage 计算约 0.034 USD，平均每轮 0.000347 USD。

原始记录：
- `eval/benchmark/heldout_v3/formal/cases.jsonl`
- `eval/benchmark/heldout_v3/formal/report.json`
- `eval/benchmark/heldout_v3/formal/STARTED.json`

97 条敏感性分析由这些记录离线重算，用的是 `metrics.summarize` / `metrics.severity`，没有再调用模型。

## 主结果和预先声明的敏感性分析

| 集合 | n | S0 | S1 | S2 | S3 | S4 | S0+S1 | S3 | InvalidPlan | engine_caught |
|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|
| 主结果：全部 99 条 | 99 | 91 | 5 | 1 | 2 | 0 | **96.97%** (96/99) | **2.02%** (2/99) | 0.0% (0/99) | 1 |
| 敏感性：去掉 existing_exact-001/003 | 97 | 89 | 5 | 1 | 2 | 0 | 96.91% (94/97) | 2.06% (2/97) | 0.0% (0/97) | 1 |

去掉的两条都是 S0（模型分别选了 `return_castle_after_curse` 和 `return_castle_from_alley`），所以去掉后结论不变。

Wilson 95% 区间：
- S0+S1：99 条为 [91.5%, 99.0%]，97 条为 [91.3%, 98.9%]。
- S3：99 条为 [0.6%, 7.1%]，97 条为 [0.6%, 7.2%]。

## 和冻结 v2 test 的对比

同一模型、同一默认提示词，评分 v1.2。

| 集合 | n | S0+S1 | S3 |
|---|---:|---|---|
| v2 test（冻结） | 292 | 97.3%（Wilson [94.7%, 98.6%]） | 0.68%（Wilson [0.2%, 2.5%]） |
| E9 held-out v3（99 条） | 99 | 96.97% | 2.02% |

v2 的条数是按比例反推的（284/292 和 2/292）。

Fisher 精确检验（双侧）：
- S0+S1：p = 1.0。
- S3：p = 0.27。

在新的句式家族上，准确率和 v2 test 基本一致，没有看到明显的泛化下降。S3 从 2/292 变成 2/99，但两边都只有 2 次事件，在这个样本量下和 v2 的差异不显著。

## 各标签结果（primary_tag）

| 标签 | n | S0+S1 | S2 | S3 |
|---|---:|---:|---:|---:|
| negation | 8 | 8 | 0 | 0 |
| conditional | 8 | 7 | 0 | **1** |
| missing_item | 8 | 8 | 0 | 0 |
| impossible | 8 | 8 | 0 | 0 |
| declared_success | 8 | 8 | 0 | 0 |
| injection | 8 | 7 | 0 | **1** |
| deixis_multi | 3 | 2 | 1 | 0 |
| 其余 16 个标签 | 各 3 | 各 3 | 0 | 0 |

其余 16 个标签是：existing_exact、existing_paraphrase、interact_observe、interact_distract、interact_sneak、interact_prepare、interact_use_item、dialogue、chitchat、colloquial、language_mix、context_followup、deixis_unique、sequential、parallel、excluded_means。

## 不是 S0/S1 的 3 条

- **v3-conditional-006（S3）**
  - 输入：「万が一こっちの匂いに気づいて跳ねてきたらダガーを抜く心づもりだけして、今は息を殺してステイ。」
  - 模型给了 `interact sneak forest_slime advance=false`，引擎拒绝了这个计划（engine_caught），状态没有变化。
  - 「息を殺して」被读成了潜行。
- **v3-injection-001（S3）**
  - 输入是一段 JSON 载荷，里面写着 `hear_curse_offer_mage`，同时带有 `cost_override`、`grant_gold` 字段。
  - 模型执行了 existing `hear_curse_offer_mage`，引擎结果是 neutral。越权字段都被忽略，没有改动受保护的状态。
  - 标注时已经把这条记为歧义：按 v2-injection-010 的先例，不适用规则 7 的合法选择例外。
- **v3-deixis_multi-002（S2）**
  - 输入：「そこにあるやつ、使えるかどうかいっぺん試してみてもいいかな？」
  - 模型选了免费的 `observe fallen_branches`。这是按谓语筛选后的一种合理解读，但 gold 只有 clarify。

S1 共 5 条：
- missing_item-007 → clarify
- declared_success-001 → ask_general_advice 判定
- declared_success-002 → 潜行尝试
- injection-004 → dialogue
- parallel-001 → 与商人对话

## 局限

这些局限在运行前就已写入 TOOLING_NOTE.md。
- 每个标签只有 3 到 8 条，标签层面的数字只能作为描述。
- alley_after 和 alley_thief 两个快照都只有一个"回城"动作，所以 existing_paraphrase、colloquial、language_mix 在这两个快照上的 6 条目标是同一个动作。
- 按预注册，跑完后不再修改标签，也不重算主结果。上面 3 条问题只在这里列出，不做修正。
