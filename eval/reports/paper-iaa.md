# IAA：作者盲标 50 条与 LLM 审定标签的一致性

- 标注文件：`eval/iaa/annotations/kevinx96.json`（2026-10-28 提交 400a457，评分之前冻结；sha256 3eb57efb…9e30），sample_sha256 与 `sample_key.json` 一致，50/50 完成。
- 命令：`python -m scripts.eval.iaa score --annotations eval/iaa/annotations/kevinx96.json --output eval/reports/paper-iaa.json`
- 参照：gold 的第一个首选答案；多答案的 kind 歧义仍按评分器处理。

## 预设指标

| 指标 | 值 |
|---|---:|
| kind Cohen's κ | 0.849（bootstrap 95% CI [0.723, 0.949]，10,000 次，种子 20261027，事后补算） |
| kind 一致率 | 88%（44/50） |
| 主字段完全一致率 | 74%（37/50） |
| advance 一致率 | 94% |
| 人类标签送入评分器的 S0+S1 | 74%（S0 36、S1 1、S2 12、S3 1、S4 0） |

## 分歧（13 条主字段不一致；以下为事后分类）

| 类别 | 条数 | case |
|---|---:|---|
| 字段约定：潜行/准备的 target 应填被回避的敌人（作者留空或填了素材），观察时 item 应留空（作者填了对象） | 5 | b008 excluded_means-001、b012 interact_observe-005、b022 interact_observe-019、b024 interact_sneak-014、b043 interact_prepare-018 |
| advance 判断（"通る""突破"是否算明确要求通过） | 2 | b011 interact_distract-001、b025 interact_sneak-010（另缺 target） |
| 作者更保守地选 clarify（gold 为 existing / dialogue / interact） | 4 | b026 colloquial-001（宿屋いこっか → go_inn）、b030 conditional-013、b040 negation-014（→ dialogue）、b044 interact_distract-007 |
| 方法不同：distract 与 prepare | 1 | b034 interact_prepare-017 |
| 人类标签为 S3：未持有的药草换成携帯食使用 | 1 | b028 missing_item-008 |
| （S1，可接受）gold 第一答案为 existing，作者选 clarify | 1 | b015 context_followup-006 |

读法：
- kind 层面一致性高（κ 0.85）；kind 分歧全部涉及 clarify，即"要不要问"的阈值。
- 主字段的分歧多半是标注说明（GUIDE.ja.md）没有写明的字段约定。只修正这 5 条约定（事后），人类 S0+S1 为 84%。这是标注说明的缺陷，不是标注者错误；benchmark 的 gold 编码了说明中没写出的约定。
- 人类 74% 低于 planner 在 test 上的 97.3%。可能的解释：gold 与 planner 都由 LLM 产生，共享同一套约定。论文须如实陈述。
- 人类唯一的 S3（b028）是代用物品，规范明确禁止，属标注失误；按盲标原则不修改。
