难度 D3 · 执行方 Codex gpt-6.1-sol high · 理由：论文补实验的评测工具（Full-LLM 对照的合法性判定、新 test 集流水线、IAA 表和 κ），跨评测框架和引擎；实跑另由主对话安排。

# 056 论文补实验：Full-LLM GM 对照、新留出 test 集、标注一致性

背景：论文草稿 `docs/research/paper-draft.md`。审稿意见要求补三块实验，用户已同意实跑，预算 5000 日元以内。本 spec 只做**工具和离线验证**。所有付费调用由主对话在工具完成后另行执行，工具必须默认不联网，只有显式加 `--live` 才发请求。

文件边界：只改 `scripts/eval/`、`eval/`（新文件）、`tests/`（新测试走补丁）。不改 `host/`、`client/`、剧本和提示词默认措辞。另一条工程线（052d）正在改游戏文件。

## E8 Full-LLM GM 对照（"不用引擎裁定会怎样"）

**目的**：衡量 LLM 直接写状态时，非法状态变化（S4）有多严重。对照组是本文架构，按构造 S4 = 0。

- **用例**：冻结 benchmark v2 的全部 486 条（dev + test），用冻结剧本快照。报告时分两组：高危组（injection、declared_success、impossible、missing_item、negation、conditional）和其余组。不要只挑高危用例，以免选择偏倚。
- **条件**：给模型的上下文和本文 planner 相同（行动者、地点、可选动作及 enabled / reason、背包、NPC、最近对话），再加上**当前完整状态**（hp、sp、inventory 及数量、flags、location）。要求模型输出 JSON：`{"reply": str, "state_after": {"hp", "sp", "inventory", "flags", "location"}}`。准备两种提示词：
  - `full_naive`：只说明"你是 GM，根据玩家输入更新状态"；
  - `full_guarded`：加上和本文同等强度的规则（不替玩家宣称成功、没有的道具不能用、否定和条件句不执行、注入不服从、需要判定的行动给出判定）。这样对照才公平，不是稻草人。
  提示词用日语，措辞由设计负责人审定（先写【仮】，汇报里列出）。
- **合法结果集**：对每条用例，用引擎对 gold 的所有可接受 plan 做结算，判定骰强制为成功和失败各一次，再加上"不变"（dialogue / clarify / unsupported 时），得到合法的 `state_after` 集合。
- **S4 判定**：模型给的 `state_after` 在受保护字段（hp、sp、inventory、flags、location）上不等于合法集合里的任何一个，就算 S4。另外细分记录：资源凭空增加、未持有物品被消耗或获得、flag 无依据改变、移动到不可达地点、注入或宣称成功被照办。逐条记录违规类型。
- **模型**：
  - Gemini 3.1 Flash-Lite（本文主模型）；
  - Gemini 3.6 Flash（更强的模型，检验结论是否只属于弱模型）；
  - 本地 qwen3-swallow-8b-rl、qwen2.5-7b-instruct（Ollama）。
- **输出**：每个模型 × 提示词的 S4 率、各类违规条数、高危组 / 其余组分开统计，以及和本文架构的对照表。缓存和 run 格式沿用现有评测框架。

## E9 新留出 test 集（回答"是否对着 test 调了评分"）

**目的**：评分 v1.2 是在第一次 test 运行之后定的。用一个从没见过的新集，在**冻结的** v1.2 评分和最终默认提示词下只跑一次。

- **冻结**：开始生成新集之前，先记录评分代码和提示词的 commit 与文件哈希，写入 `eval/benchmark/heldout_v3/PREREGISTRATION.md`（预注册），内容包括：模型、变体、评分版本、主指标、"只跑一次"的承诺。之后这两样都不能再改。
- **生成**：约 100 条，使用冻结剧本快照。覆盖 v2 的 23 个主标签，每类至少 3 条，高危类多一些。句式家族要与 v2 的 486 条隔离（新的表达和新的家族 id），用 v2 的相似度检查排重。工具只负责生成"待写输入"的槽位表（标签 × 快照 × 家族说明）。输入句由写作线（argon）起草，标签由设计负责人按 `eval/benchmark/LABELING.md` 审定。和 v2 的流程一致，论文里如实写明。
- **锁定**：标签审定后锁定文件哈希，再跑。跑完不改标签；发现错误只能在报告里列出，不能回改后重算主结果。
- **工具**：槽位表生成、相似度排重、锁定和哈希校验、按预注册参数只跑一次的执行入口（检测到已有正式结果就拒绝重跑）。

## IAA 标注一致性

- 从 486 条里按固定种子（20261027）随机抽 50 条，分层覆盖 dev / test 和主要标签。
- 生成一个**本地单文件 HTML 盲标页**，放在 `eval/iaa/`，日语界面。每条显示：玩家输入、快照上下文（可选动作及是否可用和原因、背包、NPC、地点）。不显示 gold，顺序打乱。标注者选择 kind，再按 kind 选 action_id / operation / target_id / item_id，以及 advance。页面能保存进度（localStorage），并导出 JSON。
- 再写一个计算脚本：kind 的 Cohen's κ；主字段（kind + action_id 或 operation + target / item）完全一致率；按 S0–S4 规则把人类标签当作"模型输出"喂进评分器，看它和 gold 判成 S0 / S1 的一致率。分歧逐条列出。
- 附一份简短的标注说明（日语），概括 `LABELING.md` 的要点，不给例子答案。

## 验收

- 所有工具在 fake 后端上离线跑通，有单元测试。E8 的合法集合判定要有手工构造的正例和反例测试。
- 默认不联网，联网必须加 `--live`，并在启动时打印预计调用次数和预计费用（按 `eval/prices.json`）。
- `python -m unittest discover -s tests -q`、`node --check client/app.js` 通过；测试不得依赖事先存在的 gitignore 目录。
- 汇报：每个实验的执行命令（实跑用）、预计调用次数和费用、【仮】提示词全文。

**沙箱写权限**：不能写 `.git`，也不能在 `tests/` 新建文件。交付 `.tmp-test/056/056.patch`、`manifest.json`、报告。不提交，不改权限。
