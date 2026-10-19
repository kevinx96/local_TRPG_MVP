# 043 多个 API key 自动切换

来源：用户（2026-10-19）：一个 key 用光后要能自动换下一个。每个会话里，第一个 key 失败过就记住，本会话不再试它；新会话重新从第一个开始试。example 里列两个假 key。

## 1. 配置
- `backends.<name>.api_keys`：key 列表，按顺序尝试。旧的单个 `api_key` 继续支持（视为只有一个 key 的列表）；两者同时存在时 `api_keys` 优先。
- 环境变量：`GEMINI_API_KEY` 照旧（单个）；新增 `GEMINI_API_KEYS`（逗号分隔），优先于单个。
- `host/local_config.example.json` 改用 `api_keys`，列两个占位：`"YOUR_FIRST_GEMINI_KEY"`、`"YOUR_SECOND_GEMINI_KEY"`。README 三语里配置示例同步改成 `api_keys` 并加一句说明（设计负责人之后会再润色，先按事实写）。

## 2. 切换规则
- **算作"key 失败"、要换下一个 key 的**：HTTP 429（含 RESOURCE_EXHAUSTED）、401、403，以及 400 且错误为 API key 无效（API_KEY_INVALID 等）。用同一个模型立即换下一个 key 重试同一个请求。
- **不算 key 失败的**：超时、连接错误、5xx、404 模型不存在等，仍按现有的模型备用（fallback_models）规则处理，不标记 key。
- 顺序：当前可用的第一个 key 先试；key 失败就标记并换下一个；所有 key 都失败后报现有的 LLMClientError（错误信息里说明"全部 key 都已用尽或无效"，不含 key 本身）。
- **会话记忆**：失败的 key 记在会话里（存 key 在列表里的序号加一个短哈希，例如 sha256 前 8 位，防止用户改了配置顺序后记错；**不存 key 原文**）。同一会话后续所有调用（叙述、自由行动、战斗结算）都跳过已标记的 key。新会话从头开始。
- 没有会话的调用（剧本转换、评测脚本等）：每次调用从第一个 key 开始，按同样规则切换，不跨调用记忆。

## 3. 安全
- key 原文不写进会话存档、trace、debug 日志、客户端响应。`/api/config` 的读取接口对 `api_keys` 每一项都要遮蔽（同现有 `api_key` 的处理）；写入接口支持列表。
- `scripts/build_exe.py` 的 `_secrets()` 审计要把 `api_keys` 里的每个 key 也加入检查。
- Worker 代理（演示版）不改。

## 4. 验收
- 单元测试（不联网，mock HTTP）：第一个 key 返回 429 → 自动用第二个成功；同会话下一次调用直接用第二个；新会话又从第一个开始；所有 key 都 429 时报错且信息不含 key；5xx/超时不标记 key、走模型备用；会话存档、trace、`/api/config` 输出里搜不到 key 原文；只有旧 `api_key` 的配置照常工作；`GEMINI_API_KEYS` 环境变量。
- `python -m unittest discover -s tests -q`、`node --check client/app.js` 通过，提交（`[工程]` 前缀，只 add 具体文件）。不要读取或打印 `host/local_config.json` 里的真实 key。
