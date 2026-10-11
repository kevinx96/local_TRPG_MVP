# 006 工程交付与沙箱外运行清单

## 1. 完成内容

实现仅限评测框架。游戏默认 PLAN_SCHEMA、parse_plan、提示词、benchmark 标准答案均未修改；无新增依赖，无 live 调用。

- HTTP 429 的任意嵌套 quotaId 含 PerDay，或 retryDelay > 120 秒时，立即抛出 quota_exhausted，不重试、不等待。RequestPolicy 同时锁住后续请求。CLI 保存已有结果、停止的用例 ID、筛选后从 1 开始的序号及等待秒数；剩余用例仍可读取已有缓存。未提供等待时间时报告未知。
- cost_per_turn 按 eval/prices.json 的 USD/百万 token 单价计算。缓存 token 为 0 或未报告时，不再要求缓存单价；实际缓存 token > 0 而缓存单价未知时仍为 n/a，不编造价格。cost_reported 给出可计算费用的响应数，Markdown 保留 8 位小数。缓存重放显示原始响应的估算单次费用，不代表重放产生新账单。
- lenient 请求配置和消息与 default 相同，cache_key 直接归一为 default；只读缓存，即使误加 --live 也不会请求模型。无缓存则 default_cache_required。缺字段、额外字段和类型错误仍交给严格 parser 拒绝。
- lenient 逐条记录 cleared_fields（原始值）、conflict_fields、conflict、existing_operation。existing.operation 的出现数和恢复为 status=ok 的数量单列；恢复不等于命中 gold。raw_response 保留原文。
- union_schema / union_schema_noenum 使用按 kind 分支的 anyOf + const；原有字段 description 原样保留。两者 prompt 完全不变、继续使用严格 parser。union_schema 额外按快照限制 enum，noenum 不增加快照 enum，但保留原协议固定的 operation 词表。
- 报告与 compare 并列显示模型、变体、S0+S1、S3、InvalidPlan、conflict、existing.operation、延迟、token、USD 成本。conflict 分母为有响应的 lenient 用例，其他变体显示 n/a；清理后的失败用例也计入风险分母。

### API 接受情况与错误处理

| 接口 | 本次验证 | 真实服务是否接受 |
|---|---|---|
| Gemini responseJsonSchema | mock 验证原样传递联合 schema | 未验证：按用户要求完全离线 |
| Ollama OpenAI 兼容 json_schema | mock 验证原样传递联合 schema | 未验证：按用户要求完全离线 |
| Ollama 原生 format | mock 验证兼容接口返回 400/422 schema 错误时，原样转交原生接口 | 未验证：按用户要求完全离线 |

保留现有 Ollama 传输 fallback。它改变传输接口，不改变 schema；真实拒绝的状态码与经脱敏的完整响应体写入 cases.jsonl 的 http_errors，最终失败也写入报告 errors，成功 fallback 的错误证据随缓存保存。Gemini 或 Ollama 原生拒绝后停止本轮 live 请求，不静默改用较弱 schema 污染实验。

目前没有真实拒绝错误，不能声称某个替代联合形状已被服务接受。如果仅 const 被拒绝，最接近的候选是将 const: X 换成 enum: [X]；如果根 anyOf 被拒绝，需根据服务错误再验证其支持的对象结构。已存在的 default 扁平 schema + lenient 可作为保留原提示词的退路，但不应标成 union 实验结果。本次未新增未经服务验证的自动 schema 降级。

## 2. 改动文件

- scripts/eval/requests.py：额度停止、HTTP 错误证据。
- scripts/eval/variants.py：三个新变体、容错审计、动态联合 schema。
- scripts/eval/cache.py：lenient 共用 default key。
- scripts/eval/run.py：解析接入、停止信息、费用及风险报告。
- scripts/eval/metrics.py：conflict、existing.operation、USD 成本。
- scripts/eval/compare.py：同模型各变体并排指标。
- tests/test_schema_shape.py：新增离线回归测试。
- eval/reports/006-schema-shape-experiment.md：本报告与命令。

## 3. 验证

费用与额度问题先由两个回归测试复现失败，再实现修复。新增测试覆盖 120 秒边界、PerDay 无等待提示、短 Retry-After 不覆盖长 retryDelay、额度锁定、CLI 保存部分结果并继续读缓存、五种 kind 的清理和 conflict、结构错误不修复、default 缓存复用且零请求、快照 enum、空分支、所有 dev 快照、三个传输载荷、服务拒绝错误证据、费用缺失与零成本。

提交前验证命令：

```powershell
python -m unittest discover -s tests -q
node --check client/app.js
git diff --check
```

结果：unittest 共 306 项，OK（skipped=1）；node --check 退出码 0；git diff --check 通过。新增测试中的 HTTP 均为 mock，没有连接 Gemini 或 Ollama。原有代理测试会在本机 loopback 上使用临时 HTTP 服务。

## 4. TODO(design)

- TODO(design): 沙箱外确认两个服务对 anyOf + const 的真实接受情况；遇到拒绝，用本次保存的错误体确定最接近的可接受结构。
- TODO(design): 审阅 conflict 的保守判定口径，结合 raw_response 判别“填满所有字段”和真实语义矛盾；不能仅凭清理成功选择默认策略。
- TODO(design): 运行 v2 dev 对照，分别比较 default/lenient、default/union_schema_noenum、union_schema_noenum/union_schema，再决定是否推广。此交付不改变游戏默认值。
- TODO(design): 后续若实际报告正数 cached_tokens，补齐已核实的缓存 token 单价；此前该部分费用保持未知。

## 5. 推断清单

1. existing 的“只保留 action_id，其余清空”保留判别字段 kind，清空 operation、target_id、item_id、approach、reply，并置 advance=false；union existing 分支也采用这一约束。
2. conflict 是保守风险标记：被清除的 action_id/operation/target_id/item_id 非空，或 advance=true，即计一次冲突；文本 approach/reply 被清除只做审计，不判冲突。existing.operation 即使可能与既有动作方法相符也标记风险，另外单列恢复数量，不推断模型真实意图。
3. 动态 action_id enum 只含快照 actions 中 enabled=true 的 ID。operation 没有快照专用 ID 列表，沿用协议词表并按候选对象存在性保守筛选：observe 需要 obstacles 或 objects，use_item 需要 inventory，其余三种需要 obstacles。物品效果、资源、材料特性、障碍状态等完整可行性仍由引擎判断，不在 schema 重写结算规则。
4. 动态 enum 为空时省略对应 kind 分支，避免输出非法空 enum；noenum 保留全部五个分支。因而 enum 对照同时包含这种可用分支裁剪的影响。
5. union_schema_noenum 的含义是“不添加动态 enum”，原始 operation 固定词表仍保留；interact 中排除空 operation，其他 kind 固定为空。没有添加 target_id/item_id 的额外 enum，避免扩大实验变量。
6. lenient 缓存缺失只跳过，不以 default 名义发起补请求。缺少/多出字段和错误类型不属于此次容错范围。
7. 未报告 cached_tokens 沿用现有代码按 0 计算；有正缓存量但无单价时只排除该响应的费用，其他指标仍计入，cost_reported 显示费用样本分母。429 的长 Retry-After 也按长等待停止，是对 retryDelay 的保守扩展。
8. 无硬件吞吐数据，下面按假定单条延迟给出时间区间，不把 v1 的 InvalidPlan 率换算成速度或 v2 准确率。

## 6. 偏离与限制

用户明确禁止 live 且沙箱无网络，因此“确认两个 API 真正接受”和真实模型效果/延迟留待沙箱外执行；仅完成 payload/mock 验证，没有声称通过服务端验证。无其他主动范围变更。

## 7. 已知问题与背景数据

设计负责人/用户补充的 v1 严格解析 InvalidPlan 率：qwen3-swallow-8b 100%、elyza-jp-8b 99.8%、qwen2.5-3b 99.2%。Gemini v2 的 24 条 InvalidPlan 中 20 条为 existing 携带 operation。原始缓存不在本副本，未复核，也未把这些数据当成本次 v2 dev 对照结果。

qwen2.5-7b-instruct-local **需要重新注册模型**：模型文件加载失败，Ollama 错误为 `invalid split file name`。此错误属于模型加载问题，不能计为 InvalidPlan，也不能用于判断 schema 支持。

union 动态 enum 只保证候选表面存在，不保证所选参数组合一定可执行。缓存沿用既有机制，仅缓存成功收到的原始响应；quota、请求失败和服务拦截不缓存，重跑会再次尝试这些用例。现有 Ollama 兼容接口到原生接口的 fallback 每次调用都可能多一个失败 HTTP 请求。

## 沙箱外 PowerShell 命令

所有命令在仓库根目录运行。不要加 --no-cache；default 的 v1 缓存仅在消息和配置完全相同的情况下命中，估算按 v2 冷缓存。lenient 和 default 必须使用相同模型、后端与 thinking 配置。以下代码只提供给设计负责人，本次未执行。

### 请求数与时间预算

v2 共 486 条，其中 dev=194、test=292。每个模型：

| 变体 | 评测推理次数（冷缓存） | Ollama 预热 | Gemini 预计请求 |
|---|---:|---:|---:|
| default | 194 | 1 | 194 |
| lenient | 0（重放 194 条） | 0 | 0 |
| union_schema | 194 | 1 | 194 |
| union_schema_noenum | 194 | 1 | 194 |
| 合计 | 582 | 3 | 582 |

不计失败/重试时每个本地模型 585 次生成，四模型 2340 次；当前可加载的三个模型共 1755 次。若每次都由兼容接口 fallback 原生接口，HTTP 尝试数可翻倍，模型生成数不翻倍。429/503 的短重试、拦截重跑会增加尝试数。

本地单个 live 变体约 `(194 × 单条平均秒数 + 1 次预热秒数) / 60` 分钟，另加引擎评测开销。若平均为 10/30/60 秒，则各 live 变体约 32/97/194 分钟，每模型三个 live 变体合计约 1.6/4.9/9.7 小时，四模型约 6.5/19.5/39 小时。lenient 只有本地解析、引擎与 I/O，保守预留 1–5 分钟，不包含模型时间。各 schema 的真实速度可能不同，应在首批报告中用各自延迟更新估算。这里使用 120 秒本地 timeout 给较慢模型余量。

Gemini 按 spec 提供的每日 500 次、默认 14 RPM 规划：每个 194 条 live 变体仅限流下限约 13.8 分钟，三个约 41.4 分钟，另加更慢的模型请求与重试。冷缓存总计 582 次，建议第一天 388 次、额度重置后 194 次；已有当天用量要另行扣除。

### 本地四模型 × 四变体

```powershell
$models = @(
    'qwen3-swallow-8b-rl-local',
    'elyza-jp-8b-local',
    'qwen2.5-3b-instruct-q8-0-local'
)
# 第四个模型：需要重新注册模型（invalid split file name）。
# 修复并确认可加载后，取消下一行注释，再运行同一循环：
# $models = @('qwen2.5-7b-instruct-local')

foreach ($model in $models) {
    $runIds = @()
    foreach ($variant in @('default', 'lenient', 'union_schema', 'union_schema_noenum')) {
        $runArgs = @('--suite', 'intent', '--cases', 'eval/benchmark/intent_v2.jsonl',
            '--split', 'dev', '--backend', 'ollama', '--model', $model,
            '--variant', $variant, '--base-url', 'http://localhost:11434', '--timeout', '120')
        if ($variant -ne 'lenient') { $runArgs += '--live' }
        $output = @(python -m scripts.eval.run @runArgs)
        $exitCode = $LASTEXITCODE
        $output
        if ($exitCode -ne 0) { break } # 检查报告的错误后再继续，避免连续失败请求。
        $runIds += $output[-1]
    }
    if ($runIds.Count -eq 4) { python -m scripts.eval.compare @runIds }
}
```

若只想先确认某个联合 schema 的服务接受情况，在该变体的参数中临时添加 `--limit 1`；之后去掉重跑，成功的一条复用缓存，不增加评测生成总量，但本地每个新进程可能再预热一次。mock 通过不能替代这一步。

### Gemini × 四变体，按额度分批

```powershell
# 第一天：default 194 次 + union_schema 194 次，lenient 0 次，共 388 次。
# 假定当天尚有至少 388 次余额；若发生 quota_exhausted，命令停止，等待报告提示后重跑即可续用缓存。
$model = 'gemini-3.1-flash-lite'
$common = @('--suite', 'intent', '--cases', 'eval/benchmark/intent_v2.jsonl',
    '--split', 'dev', '--backend', 'gemini', '--model', $model, '--rpm', '14')
foreach ($variant in @('default', 'lenient', 'union_schema')) {
    $runArgs = $common + @('--variant', $variant)
    if ($variant -ne 'lenient') { $runArgs += '--live' }
    python -m scripts.eval.run @runArgs
    if ($LASTEXITCODE -ne 0) { break }
}
```

```powershell
# 额度重置后单独执行：union_schema_noenum 194 次；不要在第一段后当天直接连跑。
python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --split dev --backend gemini --model gemini-3.1-flash-lite --variant union_schema_noenum --rpm 14 --live
```

### 复算成本、重放容错与比较

default 跑完后可随时不带 --live 重跑同一命令以复算成本；lenient 本身就是离线重放。不需要复制或重命名 default 缓存文件。

收集每次控制台最后一行输出的 run_id。跨日比较时，以下命令会取同一模型、v2 dev、各变体最新且完整收到 194 条响应的报告；部分失败报告应另行查看，不混为完整对照。

```powershell
$model = 'gemini-3.1-flash-lite' # 或上面的某个本地模型名
$reports = @(Get-ChildItem eval/reports -Filter '*.json' | ForEach-Object {
    Get-Content -Raw -Encoding UTF8 $_.FullName | ConvertFrom-Json
} | Where-Object {
    $_.model -eq $model -and $_.split -eq 'dev' -and
    $_.cases -match 'intent_v2.jsonl$' -and $_.metrics.total -eq 194 -and $_.metrics.evaluated -eq 194
})
$runIds = @()
foreach ($variant in @('default', 'lenient', 'union_schema', 'union_schema_noenum')) {
    $latest = $reports | Where-Object { $_.variant -eq $variant } | Sort-Object run_id | Select-Object -Last 1
    if ($null -ne $latest) { $runIds += $latest.run_id }
}
if ($runIds.Count -eq 4) { python -m scripts.eval.compare @runIds }
else { Write-Output '四个变体尚未全部完成；先检查对应报告的 errors、quota_exhausted 和 skipped。' }
```
