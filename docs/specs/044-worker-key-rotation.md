# 044 演示版 Worker 代理的多 key 切换

来源：用户（2026-10-19）：Worker 也改成 043 的形式。规则同 043：一个 key 用尽或无效就换下一个；同一个游戏会话记住失败过的 key 不再尝试，新会话重新从第一个开始。

Worker 不保存会话状态，所以"会话记忆"放在游戏端（exe），Worker 只按请求里给的起点尝试，并告诉游戏实际用了哪个槽位。

## 1. Worker（`workers/gemini-proxy`）
- 新 secret `GEMINI_API_KEYS`：多个 key，用逗号或换行分隔。没有它时退回旧的 `GEMINI_API_KEY`（视为只有一个）。`Env` 类型用 `wrangler types` 重新生成，不要手写。
- 请求头 `x-trpg-key-start`（整数，默认 0，超出范围按 0）：从这个槽位开始尝试。
- 上游返回 429、401、403，或 400 且错误为 key 无效时，换下一个槽位重发同一个请求；其他状态（5xx、404 等）直接透传，不换 key。
- 响应头 `x-trpg-key-slot`：本次实际成功（或最后尝试）的槽位号。全部槽位都失败时返回 429 / `RESOURCE_EXHAUSTED`，信息「The demo's API keys are all used up. Please try again later.」，`x-trpg-key-slot` 设为 key 的数量。
- Worker 自己的限制（每 IP 速率、每日预算）返回的 429 加响应头 `x-trpg-proxy-limit: 1`，与 key 用尽区分开。
- 每日预算按"一次游戏请求"计数，不因换 key 重试而多扣。
- 结构化日志加上 `slot` 和 `tries` 字段；**任何日志、响应里都不能出现 key 原文**。
- 指纹、schema 检查等其余行为不变。

## 2. 游戏端（`host/llm_client.py`，演示模式即配置指向 Worker 的情况）
- 发请求时带 `x-trpg-key-start`：取本会话记住的槽位（存在 `session["llm_worker_key_slot"][backend]`，没有则 0）。
- 收到响应后，把 `x-trpg-key-slot` 记回会话（只记槽位号）。新会话从 0 开始。没有会话的调用每次从 0 开始。
- 带 `x-trpg-proxy-limit: 1` 的 429 不算 key 失败，按现有方式提示玩家稍后再试；全部 key 用尽的 429 同样如实提示，不进入 043 的本地 key 轮换（演示模式本地只有 demo token）。
- 非演示模式（直接连 Google）完全沿用 043，不受影响。

## 3. 文档
- `workers/gemini-proxy/README.md`：部署步骤改成 `npx wrangler secret put GEMINI_API_KEYS`（说明分隔方式），并写明旧的 `GEMINI_API_KEY` 仍可用。三语 README 里演示版一节若提到 secret 名，同步更新。

## 4. 验收
- Worker：`npm run check` 通过。为切换逻辑加最小测试（项目里没有 Worker 测试框架的话，把切换逻辑写成可单独导入的纯函数，用 Node 自带的 `node:test` 测：第一个 key 429 → 第二个成功、`x-trpg-key-start` 起点、全部失败、5xx 不换 key、预算只扣一次、响应和日志里没有 key）。
- Python：mock HTTP 测演示模式的槽位记忆（同会话沿用、新会话归零、proxy-limit 不当作 key 失败）。
- `python -m unittest discover -s tests -q`、`node --check client/app.js`、`python -m scripts.worker_fingerprints` 通过。
- **不要部署**，不要执行 `wrangler secret put` / `wrangler deploy`，也不要读 `host/local_config.json` 里的真实 key；部署由设计负责人做。提交（`[工程]` 前缀，只 add 具体文件）。
