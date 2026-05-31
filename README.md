# Local LLM TRPG MVP

A minimal TRPG client powered by a local LLM as Game Master. The Host runs on FastAPI, managing game state, saves, dice rolls, and OpenAI-compatible LLM calls. The Client runs in the browser with a visual-novel-style (galgame) UI.

> **Python**: 3.9 or newer. Tested with FastAPI/Pydantic. arm64 users should prefer a native arm64 Python/Conda environment.

---

<details>
<summary>🇯🇵 日本語</summary>

ローカルLLMをGMとして使う、日本語TRPGクライアントの最小実装です。HostはFastAPIでゲーム状態、セーブ、ダイス、OpenAI互換LLM呼び出しを管理し、Clientはブラウザで動きます。

</details>

<details>
<summary>🇨🇳 中文</summary>

使用本地LLM作为GM的TRPG客户端最小实现。Host端基于FastAPI管理游戏状态、存档、骰子和OpenAI兼容的LLM调用，Client端在浏览器中运行，采用视觉小说风格（Galgame）UI。

</details>

---

## Setup

```powershell
python -m pip install -r requirements.txt
python -m host.run_server
```

The browser opens `http://127.0.0.1:8000/` automatically. To skip auto-open:

```powershell
python -m host.run_server --no-browser
```

For hot-reload during development:

```powershell
python -m host.run_server --reload
```

When a new session is created, the GM generates an opening scene automatically. The player enters their first action following the GM's narration. GM responses are displayed in full once generation is complete.

## LLM Configuration

Edit `active_backend` and `backends` in `host/config.json`.

- Ollama (default): `http://localhost:11434/v1`
- Koboldcpp example: `http://localhost:5001/v1`

Both use the OpenAI-compatible `/chat/completions` endpoint. The current default priority model is qwen3, falling back to qwen2.5 and ELYZA JP 8B.

```json
{
  "model": "qwen3-swallow-8b-rl-local",
  "fallback_models": [
    "qwen2.5-7b-instruct-local",
    "elyza-jp-8b-local"
  ]
}
```

### Remote Ollama

For a slow laptop, keep the game host/client local but point LLM calls to the main PC. Do not edit `host/config.json` for machine-specific settings; create `host/local_config.json` instead. It is ignored by git.

```json
{
  "backends": {
    "ollama": {
      "base_url": "https://ollama.your-domain.com/v1",
      "model": "qwen3-swallow-8b-rl-local",
      "fallback_models": [
        "qwen2.5-7b-instruct-local",
        "elyza-jp-8b-local"
      ],
      "api_key": "ollama"
    }
  }
}
```

Environment variables can override this without editing files:

```powershell
$env:TRPG_OLLAMA_BASE_URL = "https://ollama.your-domain.com"
$env:TRPG_OLLAMA_MODEL = "qwen3-swallow-8b-rl-local"
python -m host.run_server
```

Recommended remote setup:

1. On the main PC, make Ollama listen beyond localhost by setting `OLLAMA_HOST=127.0.0.1:11434` for a local Cloudflare Tunnel target, or `OLLAMA_HOST=0.0.0.0:11434` if you are using a private VPN such as Tailscale.
2. With your Cloudflare domain, create a Cloudflare Tunnel from `https://ollama.your-domain.com` to `http://127.0.0.1:11434` on the main PC.
3. Protect the tunnel with Cloudflare Access or a service token. Do not expose Ollama publicly without access control.
4. On the slow laptop, set `host/local_config.json` or `TRPG_OLLAMA_BASE_URL` to the Cloudflare Tunnel URL.

If Cloudflare reaches Ollama but every request returns an empty `403`, Ollama is rejecting the public-domain `Host` header. If your Cloudflare dashboard exposes `HTTP Host Header`, set it to `localhost:11434`. If that option is not visible, run the bundled local proxy on the main PC:

```powershell
python -m host.ollama_tunnel_proxy
```

Then change the Cloudflare Tunnel service URL to:

```text
http://localhost:11435
```

The public game client still uses `https://ollama.your-domain.com/v1`; only the Cloudflare origin service URL changes.

### Registering GGUF Models with Ollama

```powershell
python -m host.setup_ollama_models
ollama list
```

### Debug Logging

Enabled by default (`"debug_llm": true` in config). Logs appear in CMD/PowerShell prefixed with `[TRPG-DEBUG]`. API keys are never logged.

If you see `model not found`, register the GGUF model first or update `model` / `fallback_models` in config to match `ollama list` output.

## Scenario Format

Scenarios use the **Scenario Pack** JSON format defined in [`scenario_pack.schema.json`](host/prompt/processed/scenario_pack.schema.json).

Key structure:

```
meta          → title, summary, language, initial_scene
rules[]       → GM behavior rules
scenes[]      → id, title, description, goals, keywords, *_ids, fallback_choices
locations[]   → id, title, description, keywords
npcs[]        → id, name, description, keywords
items[]       → id, name, description, effect, keywords
clues[]       → id, title, description, keywords
fallback_choices[]  → global default choices
```

See [`dragon_rpg.json`](host/prompt/processed/dragon_rpg.json) for a complete example.

## Scenario Conversion

```powershell
python -m host.scenario_converter "host\prompt\raw\your_scenario.docx"
```

Supports `.txt`, `.docx`, `.pdf`, `.doc` (Windows COM required for `.doc`).

Gemini API key is read from env var `GEMINI_API_KEY`, or from `host/gemini_api_key.txt` / `host/gemini_api_key.py` / `host/auto_tagger.py`. These secret files are excluded via `.gitignore`.

## Tests

```powershell
python -m unittest discover -s tests
```

## License

See [LICENSE](LICENSE).
