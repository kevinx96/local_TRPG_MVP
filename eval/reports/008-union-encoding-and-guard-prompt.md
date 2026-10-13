# 008 工程交付与沙箱外运行清单

## 1. 完成了什么

新增六个评测变体，游戏默认提示词、schema、解析器与 benchmark 均未改动；无新增依赖，没有调用真实模型。

- `union_enum1`：沿用 006 的动态 union，将所有 const（包括 false）替换为单元素 enum。
- `union_wrapped`：将原动态 union 放入必填的 plan 属性，外层禁止多余字段；评测解析时严格检查外层再取 plan。原始响应及缓存保留包装。
- `union_ordered`：基于 union_enum1，每个分支加入完整 propertyOrdering，kind 第一。
- `flat_enum`：只改变原扁平 schema 的 action_id、operation、target_id、item_id enum，各含空字符串，保留原字段说明。
- A 的四个变体仅允许 Gemini 评测。提示词完全沿用 default，非 wrapped 变体沿用原解析路径。
- `guard_rules`、`guard_rules_short`：在 PLAN_PROMPT 末尾加一个换行后逐字追加 spec 的文字。schema、其他消息、请求配置、严格解析规则不变；测试直接从 spec 提取文字进行比对。
- 新增 `scripts.eval.schema_smoke`：按 spec 顺序跑四种写法，各取文件顺序中的前 20 条 dev，一条命令输出可用/不可用及失败形态；`--full-dev` 只对通过冒烟的变体继续完整 dev，复用前 20 条缓存。各轮保存现有格式的 JSON/Markdown 报告和 cases.jsonl，另保存总览 JSON。共用限速/额度策略，额度耗尽后仅重放缓存。
- guard 报告新增 `prompt_delta`：追加字符数，以及相同用例、快照、模型、配置的 default 缓存与本次响应之间的 input_tokens 差值均值和配对数。缺少缓存或用量数据时为 n/a，不增加任何基线请求。

## 2. 改动的文件

- `scripts/eval/variants.py`：六个变体、快照 enum、包装解包。
- `scripts/eval/run.py`：变体解包、失败分类、token 增量、可复用的单轮评测入口。
- `scripts/eval/schema_smoke.py`：四种写法的冒烟与通过后续跑命令。
- `tests/test_schema_encoding.py`：schema、提示词原文、缓存、解析、传输和冒烟流程的离线测试。
- `eval/reports/008-union-encoding-and-guard-prompt.md`：交付、估算和运行清单。

## 3. 验证结果

提交前运行：

```powershell
python -m unittest discover -s tests -q
node --check client/app.js
git diff --check
```

结果：unittest 共 324 项，38.532 秒，`OK (skipped=1)`；node 语法检查退出码 0；git diff --check 通过。五个改动文件均为 UTF-8 无 BOM。新增测试覆盖所有 v2 dev 快照的四种 schema 生成、不修改原对象和说明、空候选集、四字段 enum、Gemini payload 原样传递、wrapped 严格解包和缓存重放、B 原文追加与严格解析不变、实际 token 配对差值、失败形态、Gemini 限定、默认零模型调用、四变体流程、完整 dev 门槛及跨变体额度停止。API 传输均使用 mock；原有代理测试使用本机 loopback 临时服务。

## 4. TODO(design) 清单

- TODO(design): 沙箱外运行 A 冒烟，确认 Gemini 对各 schema 的真实支持，再按通过结果运行完整 dev。
- TODO(design): 沙箱外完成 B 与 lenient 对照，评估 S3 与正常意图准确率的取舍；本次不选择默认策略。
- TODO(design): 用 B 的真实 usage 和匹配 default 缓存替换下面的 token/费用估算。

## 5. 推断清单

1. union_enum1、union_ordered 沿用 006 union_schema 的动态 action_id/operation enum 与空候选分支裁剪。spec 只明确 ordered 基于 1，因此 wrapped 单独基于原 union_schema，保留 const，以独立检查“顶层 anyOf”的影响。
2. flat_enum 的 action_id 只取 enabled 的动作；operation 复用 006 的候选存在性筛选。target_id 取 self、obstacles、objects、npcs 的 ID；item_id 取 objects 与 inventory 的 ID。self 来自现有协议，不额外加入角色 ID 别名。按首次出现顺序去重，各列表前置空字符串。完整可执行性继续交给引擎。
3. “可用”采取保守标准：20/20 status=ok（成功严格解析且引擎评测完成），不设语义准确率门槛。引擎正常返回 rejected 仍属于完成评测；抛出 InvalidPlan 则不通过。无响应/缓存缺失也标为不可用，同时单列无响应数，不能据此认定 API 不支持。
4. 先完成四个冒烟，再依次续跑通过的完整 dev。CLI 退出码为 0 表示四项均通过且请求的完整 dev 均收到全部响应；任一未通过或续跑不完整为 1。完整 dev 中的 InvalidPlan 是评测结果，不算缺响应。
5. 空白输出包括纯空白、单独的左花括号后只有空白，以及 wrapped 的未闭合 `{"plan": {`。空对象包括 `{}` 和 wrapped 的 `{"plan": {}}`。其他有响应的失败归“其他”；请求失败、拦截、额度停止、缓存缺失归“无响应”，具体原因保留在逐条记录。
6. B 与原提示词之间增加一个换行，不额外加末尾换行；逐字保留 spec 代码块中的内部换行、空格和标点。
7. 离线没有 Gemini tokenizer，以下按追加部分每个 Unicode 字符约 1 token 作预算假设，并假设输出 token 均值不变；这不是 Gemini 实测计数，也不是误差上界。实际 input token 差值使用匹配缓存报告，可能受服务计数规则影响。

## 6. 偏离 spec 的地方及原因

遵照用户“沙箱没有网络，不要尝试 live”的要求，未运行真实冒烟或模型对照，未声称任何新 schema 已获 Gemini 服务接受。精确 Gemini prompt token 增量无法离线获取，提供可复算估算及运行后自动统计。其余实现按 spec 完成。

## 7. 已知问题

- 20 条冒烟不能保证完整 dev 无失败，保守门槛也可能淘汰仅偶发解析失败的 schema；请结合逐条错误查看。
- flat_enum 比 union 额外约束 target_id/item_id；按 spec 保留这项差异，因此两者对照并非仅改变联合结构。
- lenient 只重放 default 缓存。缓存不足时不会补请求，需先用相同模型与 thinking 配置完成 default；本地第四个模型按本次 spec 视为已重新注册。
- 本报告费用不包含额外 default 请求、失败重试、输出长度变化或服务缓存折扣。正 cached_tokens 的价格尚未在 prices.json 核实，沿用原框架显示 n/a 的规则。

## B 的 prompt token 增量、请求数和费用估算

v2 dev 共 194 条。以仓库已有 `2026-10-11T112514831356Z-intent-gemini-gemini-3.1-flash-lite-default.json` 为基线：每条平均 input=706.0309278350516、output=83.64432989690722 token。使用 `eval/prices.json` 中 gemini-3.1-flash-lite 的输入 $0.25/百万、输出 $1.50/百万，USD，无需联网查询。

| 变体 | 精确追加字符（含分隔换行） | 每请求 prompt token 增量估算 | 冷缓存请求数 | 完整 dev 估算费用 | 相对 default 的输入增量费用 |
|---|---:|---:|---:|---:|---:|
| guard_rules | 116 | 约 +116 | 194 | $0.064209 | $0.005626 |
| guard_rules_short | 34 | 约 +34 | 194 | $0.060232 | $0.001649 |
| 合计 | — | — | 388 | $0.124441 | $0.007275 |

公式：`194 × ((706.0309278350516 + 追加 token 估算) × 0.25 + 83.64432989690722 × 1.50) / 1,000,000`。真实输出可能变化，估算不是费用上限。没有 B 的真实响应，本次实际测得的 Gemini token 增量为 n/a。运行后的 JSON/Markdown 会在匹配 default 缓存存在时给出实测差值与样本数；无缓存时可用 compare 查看完整同集报告的均值差，但不把不同样本分母直接作差。

## 沙箱外 PowerShell 命令清单（本次未执行）

在仓库根目录执行，使用已有本地 API 配置，不要加 `--no-cache`。

### Gemini A：一条命令完成四种冒烟

```powershell
python -m scripts.eval.schema_smoke --cases eval/benchmark/intent_v2.jsonl --model gemini-3.1-flash-lite --rpm 14 --live
```

冷缓存最多 80 次模型请求（不计重试），每种前 20 条。全部结果会打印中文分类；查看 `eval/reports/*-schema-smoke.json` 对应的各轮报告及 `eval/runs/<run_id>/cases.jsonl`。

需要自动对可用项续跑完整 dev 时：

```powershell
python -m scripts.eval.schema_smoke --cases eval/benchmark/intent_v2.jsonl --model gemini-3.1-flash-lite --rpm 14 --full-dev --live
```

冷缓存总请求为 `80 + 174 × 通过变体数`，最多 776；已经完成冒烟后再执行此命令会重放那 80 条，新增最多 696 次。额度耗尽后不再请求，等待额度恢复后执行同一命令续用缓存。

### Gemini B：两个变体的完整 v2 dev

```powershell
$common = @('--suite', 'intent', '--cases', 'eval/benchmark/intent_v2.jsonl',
    '--split', 'dev', '--backend', 'gemini', '--model', 'gemini-3.1-flash-lite', '--rpm', '14')
$runIds = @()
foreach ($variant in @('guard_rules', 'guard_rules_short')) {
    $output = @(python -m scripts.eval.run @common --variant $variant --live)
    $exitCode = $LASTEXITCODE
    $output
    if ($exitCode -ne 0) { break }
    $runIds += $output[-1]
}
if ($runIds.Count -eq 2) {
    python -m scripts.eval.compare '2026-10-11T112514831356Z-intent-gemini-gemini-3.1-flash-lite-default' @runIds
}
```

B 冷缓存共 388 次；如果同一天仅执行 A 冒烟与 B，则共 468 次，按 spec 的每天 500 次额度尚余 32 次供其他用量/重试。不要在同一天再无条件追加 A 完整 dev；以实际剩余额度为准。

### 本地四模型：两个 guard + lenient，完整 v2 dev

```powershell
$models = @('qwen3-swallow-8b-rl-local', 'elyza-jp-8b-local',
    'qwen2.5-3b-instruct-q8-0-local', 'qwen2.5-7b-instruct-local')
foreach ($model in $models) {
    $common = @('--suite', 'intent', '--cases', 'eval/benchmark/intent_v2.jsonl',
        '--split', 'dev', '--backend', 'ollama', '--model', $model,
        '--base-url', 'http://localhost:11434', '--timeout', '120')
    $runIds = @()
    foreach ($variant in @('guard_rules', 'guard_rules_short', 'lenient')) {
        $runArgs = $common + @('--variant', $variant)
        if ($variant -ne 'lenient') { $runArgs += '--live' }
        $output = @(python -m scripts.eval.run @runArgs)
        $exitCode = $LASTEXITCODE
        $output
        if ($exitCode -ne 0) { break }
        $runIds += $output[-1]
    }
    if ($runIds.Count -eq 3) { python -m scripts.eval.compare @runIds }
}
```

每个模型两个 guard 共 388 次评测生成，另有两个进程各一次预热；四模型共 1552 次评测生成 + 8 次预热。lenient 不产生模型请求，报告必须确认 responses/total=194/194；退出码 0 本身不代表缓存完整。

若某本地模型 default 缓存未完成，先在该模型相同配置下补齐（冷缓存额外 194 次生成 + 1 次预热），然后重跑上述命令，guard 将直接复用已有缓存并重算 token 差值：

```powershell
$model = 'qwen2.5-7b-instruct-local' # 改成缺缓存的模型
python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --split dev --backend ollama --model $model --variant default --base-url http://localhost:11434 --timeout 120 --live
```
