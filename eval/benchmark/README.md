# 审定 benchmark

本目录仅接收设计负责人审定的标准答案。`intent_v2.jsonl` 为审定的冻结标签，不随当前剧本更新。

冻结的 benchmark 只在冻结的剧本上评测。v2 引用的 38 个 `eval/snapshots/v2_*.json` 快照固定使用
`scenario_frozen/dragon_rpg@f41af9d.json`，内容逐字节取自 commit `f41af9d`，也就是 008（提示词变更的依据）实跑时使用的剧本。
缺失于历史剧本的字段使用引擎对该历史数据的缺省处理，不从当前剧本补入。
`scripts.eval.benchmark_v2` 生成的 v2 快照也使用此路径，避免重新生成时解除冻结。

跟随当前剧本的回归测试使用 `eval/candidates/intent_v2_scenario.jsonl` 和以后新增的补充集。
补充集自己的 `v2_scenario_*.json` 快照继续引用当前剧本；它们不属于冻结的 `intent_v2.jsonl`。

另有当前剧本版 `eval/candidates/intent_v2_current.jsonl`，**不冻结**，486 条标签沿用审定 v2，
全部标为 `label_status: needs_review`，供设计负责人复审。其 38 个 `v2cur_*.json` 快照
只改 ID 和剧本引用，其余字段从冻结 v2 快照复制；用例只改 ID、快照 ID 和 label_status。
生成命令（不调用模型）：

```powershell
python -m scripts.eval.benchmark_v2_current
```

离线重放命令（在仓库根目录运行；缓存未命中会 skipped，不会联网）：

```powershell
python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --backend gemini --model gemini-3.1-flash-lite --variant guard_rules --split dev
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v2_current.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split dev
python -m scripts.eval.run --suite intent --cases eval/candidates/intent_v2_scenario.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split all
```

需要在有网络环境补跑真实响应时，显式给对应命令加 `--live`，才会在缓存未命中时调用 API。
`guard_claims` 仅保留作实验变体，不是默认值。

冻结版本的选定（设计负责人，2026-10-12）：018 先按 `4386cd3` 冻结，但 008 实跑时剧本已经改过地点描述，只命中 190/194。改为冻结 `f41af9d` 后，离线重放 dev 194/194、test 292/292 全部命中缓存，S0+S1 分别为 92.78% 和 84.59%，和 `docs/design/prompt-log.md` 的数字完全一致。今后冻结 benchmark 上的所有对比都以这一版为基线。
