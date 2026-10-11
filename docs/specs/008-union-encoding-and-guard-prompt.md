# 008 union schema 的其他写法 + 防误触发提示词变体

## 背景（设计负责人实跑，v2 dev 194 条，见 `eval/reports/006-gemini-compare.md`）
- Gemini 3.1 Flash-Lite 用 `union_schema` 和 `union_schema_noenum` 时 **100% InvalidPlan**：128 条在 `{` 之后一直输出空白，直到 token 用完；66 条只返回 `{ }`。输出 token 从 84 涨到约 460。说明 Gemini 的约束解码不接受这种 schema 结构（顶层 `anyOf` + `const`）。
- `lenient`：S0+S1 从 89.7% 升到 90.7%，InvalidPlan 降到 0；但 S3 从 3.1% 升到 3.6%，conflict 为 4.1%。

## A. union schema 的替代写法（只给 Gemini 评测用）
依次试下面几种写法，每种先在 dev 的前 20 条上冒烟测试；能用的才跑全部 dev：
1. `union_enum1`：`const: x` 全部改成 `enum: [x]`
2. `union_wrapped`：顶层是 `{"plan": {anyOf: [...]}}`，解析时取出 `plan`
3. `union_ordered`：在 1 的基础上，每个分支加 `propertyOrdering`，让 kind 排在第一个
4. `flat_enum`：保持现在的扁平 schema，只给 `action_id`、`operation`、`target_id`、`item_id` 加上按快照生成的 `enum`（每个都包含空字符串）。这一项用来区分"联合结构"和"枚举约束"各自的作用。

变体注册方式和 006 相同。冒烟测试要能在一条命令里跑完 4 种写法，并输出"可用/不可用"和失败形态（空白输出、空对象、其他）。

## B. 防误触发提示词变体（措辞由设计负责人提供，照抄，不要改）
Gemini 在 v1 和 v2 上都稳定出现三种 S3：否定被理解成"改用别的手段"、缺少道具时自行替换、条件句被立即执行。新增两个变体，都是在默认 `PLAN_PROMPT` 的末尾追加文字：

`guard_rules`：
```
否定・待機・条件だけの入力は代わりの行動を求めていない。費用や危険のある操作を選ばず dialogue にする。
「〜したら」「〜なら」の条件付き行動は今は実行しない。
inventory にない物は使わない。別の物で代用しない。
```

`guard_rules_short`：
```
否定・条件・未所持の物を含む入力では、費用のかかる操作を選ばない。
```

两个变体都只改提示词，schema 和解析不变。报告里要给出两者相对 default 的 prompt token 增量。

## C. 运行
沙箱没有网络。完成后给出命令清单：
- Gemini：A 的冒烟测试命令；B 的两个变体在 v2 dev 上的完整运行。
- 本地 4 个模型（qwen3-swallow-8b-rl、elyza-jp-8b、qwen2.5-3b-q8、qwen2.5-7b，最后这个已经重新注册，可以用）：B 的两个变体加上 `lenient`，v2 dev。

## 不做
不改游戏默认的提示词、schema 和解析。

## 验收
两条验证命令通过；每种 schema 写法的生成都有测试；B 的两个变体确实只在 `PLAN_PROMPT` 末尾追加了文字（用测试比对）。

## 汇报
按 `docs/roles/engineering.md` 的格式。另外估算 B 部分 Gemini 的请求数和费用（用 `eval/prices.json`）。
