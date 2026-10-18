# gemini-proxy

Cloudflare Worker：持有 Gemini API key，让分发出去的 exe 只带一个可撤销的 demo token。

游戏端无需改代码：`backends.gemini.base_url` 指向 `https://<worker>/v1beta`，`api_key` 填 demo token 即可（请求头仍是 `x-goog-api-key`）。

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
npx wrangler secret put GEMINI_API_KEY   # 粘贴真实 key
npx wrangler secret put DEMO_TOKEN       # 粘贴一个新随机串，例如 python -c "import secrets;print(secrets.token_urlsafe(24))"
npx wrangler deploy
```

部署后用游戏本体连一次即可验证（指纹检查会拒绝手写的 curl 请求）。`placement` 只是延迟提示；若出现 `User location is not supported`，可改用自有域名的路由或换 placement。

## 打包 demo 版

```
set DEMO_TOKEN=<同上>
python -m scripts.build_exe --demo-endpoint https://<worker>.workers.dev
```

会在 exe 旁写入只含 worker 地址和 demo token 的 `local_config.json`，并换上 demo 版 README_RUN.txt；真实 key 的审计照常执行。

## 本地开发

`.dev.vars`（已 gitignore）放假值，`UPSTREAM_BASE` 可指向本地 mock：

```
npm run check                 # wrangler types + tsc
npx wrangler dev --port 8787
```

用量查看：`npx wrangler tail`，日志是结构化 JSON（`model` / `status` / `used` / `colo`）。
