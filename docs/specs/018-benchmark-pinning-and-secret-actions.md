# 018 冻结 benchmark 所用的剧本 + 秘密动作不再泄露给模型

## 背景（设计负责人实跑）
1. **benchmark 漂移**：v2 dev 上同一个提示词（guard_rules，现在的默认），008 时是 92.8%，现在是 88.1%。11 条用例变差、2 条变好，其中 10 条的 prompt 哈希不同，原因是快照是**用当前剧本现场构造**的，012–017 改了动作（商店、长老的子动作、宿屋等）。冻结的 test 集如果跟着剧本变，前后实验就没法比较。
2. **秘密动作泄露**：`guard_claims` 变体没有效果（补充集 evidence_claim 的 S3 从 5/8 变成 6/8）。017 确认 planner 的 actions 里列出了条件没满足的动作（`enabled: false` + `reason`），所以模型看得到"将軍ドラコの正体を問いただす"这个动作，还会选它。这既造成误触发，也**泄露了剧情**。

## 1. 冻结剧本
- 新建 `eval/benchmark/scenario_frozen/`，放入 benchmark v2 冻结时（commit `4386cd3`）的 `dragon_rpg.json`，文件名 `dragon_rpg@4386cd3.json`。
- benchmark v2 的快照（`eval/snapshots/v2_*.json`）改为引用这个冻结版本。这些快照用到的、在当时版本里不存在的字段，按当时的剧本处理。
- **验证**：用 `guard_rules` 变体（对应当时的默认）重跑 v2 dev，必须**全部命中缓存**、得到和 `eval/reports/2026-10-11T120217862118Z-*` 完全相同的结果（S0+S1 92.78%）。如果做不到，说明还有其他漂移来源，查清楚并汇报。
- 新增 `eval/benchmark/README.md` 的说明：冻结的 benchmark 只在冻结的剧本上评测；跟随当前剧本的回归测试用 `eval/candidates/intent_v2_scenario.jsonl` 和以后新增的补充集。
- 新增一个"当前剧本版"的 v2：快照指向当前剧本（`eval/snapshots/v2cur_*.json`，内容由脚本从 v2 快照复制并改引用），标注沿用 v2，**不冻结**，标成 `label_status: needs_review`。由设计负责人之后审标注。

## 2. 秘密动作
- 动作可以声明 `secret: true`：条件不满足时，**既不在 UI 显示，也不出现在给 planner 的 actions 里**；满足时和普通动作一样。
- 下列动作设为 secret（两份剧本）：`report_with_evidence`、`purify_ignis_holy_water`、`purify_ignis_prayer`、`ask_robin_stolen_scale`、`ask_ignis_aid`、`buy_white_scale`。其他剧情动作是否需要，列出建议，不要自己加。
- 写测试：secret 动作在条件不满足时，不出现在 planner 的 messages 里，也不在 public_session 的 choices 里；满足后出现。
- `guard_claims` 变体保留，但不采用。

## 3. 子动作对 planner 是否可见
v2 dev 里「長老に邪竜の弱点を聞く」从 existing `ask_elder_weakness` 变成了 dialogue。检查：长老那里的动作现在是不是嵌套成了子动作，planner 是否看得到子动作。如果看不到，按现有的 `current_actions_for_session` 逻辑，把可执行的子动作也展开给 planner（这是 bug，属于修复）。写测试。

## 4. 实跑命令
沙箱没有网络。给出命令：冻结版 v2 dev（guard_rules）、当前版 v2 dev（default）、补充集（default）。

## 验收
两条验证命令通过；第 2、3 节的测试通过；第 1 节的验证方法写进汇报（缓存命中率、结果是否一致）。

## 汇报
按 `docs/roles/engineering.md` 的格式，回答第 1 节验证能否复现、第 3 节的结论。
