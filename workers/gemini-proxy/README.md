# gemini-proxy

Cloudflare Worker：持有 Gemini API keys，让分发出去的 exe 只带一个可撤销的 demo token。

游戏端配置：`backends.gemini.base_url` 指向 `https://<worker>/v1beta`，`api_key` 填 demo token 即可（请求头仍是 `x-goog-api-key`）。Gemini 后端的非 Google 地址视为演示代理，支持 workers.dev、自有域名及本地 mock；直连 Google 沿用本地 key 轮换。

## 多 key 切换

`GEMINI_API_KEYS` 按逗号或换行分隔，去掉两端空白和空项后按顺序尝试；没有有效列表时退回旧的 `GEMINI_API_KEY`（单个 key）。例如 `YOUR_FIRST_GEMINI_KEY,YOUR_SECOND_GEMINI_KEY`。

游戏通过 `x-trpg-key-start` 发送本会话的起点（从 0 编号）；缺省、非整数或越界都按 0。Worker 遇到 429、401、403 或 key 无效的 400 时尝试下一个槽位，不回绕；其他 HTTP 错误直接透传。每次游戏请求只扣一次每日预算。响应头 `x-trpg-key-slot` 返回成功或最后尝试的槽位；剩余 key 全失败时返回 429 / `RESOURCE_EXHAUSTED`，槽位设为 key 数量。

游戏把槽位记在 `session["llm_worker_key_slot"][backend]`，同会话后续调用从该槽位继续，新会话及无会话调用从 0 开始。全部用尽时另存 `llm_worker_keys_exhausted` 布尔标志，避免将数量哨兵发回 Worker 后归零重试。Worker 的每 IP 限流和每日预算 429 带 `x-trpg-proxy-limit: 1`，不会把 demo token 或上游 key 标成失效。Worker 本身不保存会话状态。

## 防护

demo token 放在 exe 旁边，能被提取；指纹也能被抄。它们挡的是随手滥用，真正封顶费用的是每 IP 限流和每日预算：

| 层 | 内容 |
|---|---|
| 请求形状 | 只放行 `POST /v1beta/models/{model}:generateContent`；模型白名单（与 `host/config.json` 一致）；body 只允许 `contents` / `systemInstruction` / `generationConfig` / `safetySettings`，≤64KB；`maxOutputTokens` 截到 2048 |
| 请求来源 | `systemInstruction` 必须以游戏某个系统提示词的首行开头（`src/fingerprints.ts`），plan 请求还必须带 JSON schema；其他提示词一律 403。改了提示词措辞后运行 `python -m scripts.worker_fingerprints --write` 并重新 deploy（unittest 会检查是否过期） |
| 每 IP | Rate Limiting binding，30 次/60 秒（按 Cloudflare 节点计数，近似值） |
| 每天 | Durable Object 精确计数，`DAILY_REQUEST_LIMIT`（默认 2000，UTC 0 点重置） |
| 兜底 | 在 Google Cloud 为这个 key 设预算提醒（Billing → Budgets & alerts） |

泄露后的处理：`npx wrangler secret put DEMO_TOKEN` 换新 token，再重新打包，旧 exe 随即失效。

## 部署（只在本机执行，key 不进仓库）

```
cd workers/gemini-proxy
npm install
npx wrangler login
npx wrangler secret put GEMINI_API_KEYS  # 粘贴真实 keys，以逗号或换行分隔
npx wrangler secret put DEMO_TOKEN       # 粘贴一个新随机串，例如 python -c "import secrets;print(secrets.token_urlsafe(24))"
npx wrangler deploy
```

旧的 `GEMINI_API_KEY` 仍可用；设置 `GEMINI_API_KEYS` 后优先使用列表，无需同时配置旧 secret。

部署后用游戏本体连一次即可验证（指纹检查会拒绝手写的 curl 请求）。`placement` 只是延迟提示；若出现 `User location is not supported`，可改用自有域名的路由或换 placement。

## 打包 demo 版

```
set DEMO_TOKEN=<同上>
python -m scripts.build_exe --demo-endpoint https://<worker>.workers.dev
```

会在 exe 旁写入只含 worker 地址和 demo token 的 `local_config.json`，并换上 demo 版 README_RUN.txt；真实 key 的审计照常执行。

## 本地开发

`.dev.vars`（已 gitignore）放假值，`UPSTREAM_BASE` 可指向本地 mock。`npm run types` / `npm run check` 用已提交的 `.dev.vars.example` 假值重新生成 `Env`，不读取本机 `.dev.vars`；生成的 `worker-configuration.d.ts` 继续由 gitignore 排除。类型生成方式参照 [Wrangler types](https://developers.cloudflare.com/workers/wrangler/commands/general/#types)。

测试直接导入 TypeScript 纯函数，需 Node >=22.18 的[原生类型剥离](https://nodejs.org/api/typescript.html#type-stripping)，无需新增测试依赖。

```
npm run check                 # wrangler types + tsc
npm test                      # Node >=22.18，自带 node:test；全 mock，不联网
npx wrangler dev --port 8787
```

游戏端协议测试从仓库根目录运行：

```
python -m unittest discover -s workers/gemini-proxy/tests -p test_worker_client.py -q
```

用量查看：`npx wrangler tail`，日志是结构化 JSON（`kind` / `model` / `status` / `used` / `colo` / `slot` / `tries`）；`tries` 为本次请求实际尝试次数。日志不记录 key，上游响应流也会脱敏（含跨 chunk 的 key）。
