# Local LLM TRPG

A minimal TRPG client powered by a local LLM as Game Master. The Host runs on FastAPI, managing game state, saves, dice rolls, and OpenAI-compatible LLM calls. The Client runs in the browser with a visual-novel-style (galgame) UI.

> **Python**: 3.9 or newer. Tested with FastAPI/Pydantic. arm64 users should prefer a native arm64 Python/Conda environment.

📖 **Language**: [English](#) · [日本語](README_JA.md) · [中文](README_ZH.md)

---

## Table of Contents

- [Setup](#setup)
- [LLM Configuration](#llm-configuration)
- [Remote Ollama](#remote-ollama)
- [Scenario Format](#scenario-format)
- [Scenario Editor](#scenario-editor)
- [Game Features](#game-features)
  - [Characters](#characters)
  - [Attributes & Checks](#attributes--checks)
  - [Skills](#skills)
  - [Enemies & Combat](#enemies--combat)
- [Scenario Conversion](#scenario-conversion)
- [API Overview](#api-overview)
- [Tests](#tests)
- [License](#license)

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
- Koboldcpp: `http://localhost:5001/v1`

Both use the OpenAI-compatible `/chat/completions` endpoint. The current default priority model is qwen3, falling back to qwen2.5 and ELYZA JP 8B.

```json
{
  "active_backend": "ollama",
  "backends": {
    "ollama": {
      "base_url": "http://localhost:11434/v1",
      "model": "qwen3-swallow-8b-rl-local",
      "fallback_models": [
        "qwen2.5-7b-instruct-local",
        "elyza-jp-8b-local"
      ],
      "api_key": "ollama"
    }
  },
  "temperature": 0.8,
  "max_tokens": 2048,
  "request_timeout_seconds": 1800,
  "response_format": "json_object",
  "prompting": {
    "history_messages": 4,
    "memory_max_chars": 1200,
    "action_history_max": 40,
    "action_history_item_chars": 80
  },
  "debug_llm": true,
  "demo_fallback_on_error": true
}
```

### Prompting Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `history_messages` | 4 | Number of recent messages sent to LLM |
| `memory_max_chars` | 1200 | Max characters for conversation memory summary |
| `action_history_max` | 40 | Max player action history entries |
| `action_history_item_chars` | 80 | Max characters per action history entry |

## Remote Ollama

For a slow laptop, keep the game host/client local but point LLM calls to the main PC. Do not edit `host/config.json` for machine-specific settings; create `host/local_config.json` instead. It is ignored by git and is the right place for machine-specific URLs, tokens, and model names.

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

### Remote Setup Steps

1. On the main PC, make Ollama listen beyond localhost by setting `OLLAMA_HOST=127.0.0.1:11434` for a local Cloudflare Tunnel target, or `OLLAMA_HOST=0.0.0.0:11434` if you are using a private VPN such as Tailscale.
2. With your Cloudflare domain, create a Cloudflare Tunnel from `https://ollama.your-domain.com` to `http://127.0.0.1:11434` on the main PC.
3. Protect the tunnel with Cloudflare Access or a service token. Do not expose Ollama publicly without access control.
4. On the slow laptop, set `host/local_config.json` or `TRPG_OLLAMA_BASE_URL` to the Cloudflare Tunnel URL.

If you get empty `403` responses from Ollama, the `Host` header is being rejected. Either set Cloudflare's `HTTP Host Header` to `localhost:11434`, or run the bundled proxy:

```powershell
python -m host.ollama_tunnel_proxy
```

Then change the Cloudflare Tunnel service URL to:

```text
http://localhost:11435
```

The public game client still uses `https://ollama.your-domain.com/v1`; only the Cloudflare origin service URL changes.

### Registering GGUF Models

```powershell
python -m host.setup_ollama_models
ollama list
```

If you see `model not found`, register the GGUF model first or update `model` / `fallback_models` in config to match `ollama list` output.

### Debug Logging

Enabled by default (`"debug_llm": true`). Logs appear prefixed with `[TRPG-DEBUG]`. API keys are never logged.

---

## Scenario Format

Scenarios use the **Scenario Pack** JSON format defined in [`scenario_pack.schema.json`](host/prompt/processed/scenario_pack.schema.json).

```
meta              → title, summary, language, initial_scene
rules[]           → GM behavior rules
scenes[]          → id, title, description, goals, keywords, location_ids, next_scene_ids, fallback_choices
locations[]       → id, title, description, keywords, npc_ids, item_ids, clue_ids, enemy_ids
npcs[]            → id, name, description, keywords
items[]           → id, name, description, effect, keywords
clues[]           → id, title, description, keywords
enemies[]         → id, name, description, image, hp/max_hp, mp/max_mp, sp/max_sp, attributes, skills[]
attribute_defs[]  → id, name, initial_value
characters[]      → id, name, default_name, description, image, image_female, hp/max_hp, mp/max_mp, sp/max_sp, gold, attributes{}, inventory[], equipment[], skills[]
combat_choices[]  → global combat action choices
fallback_choices[]→ global default choices
```

Entities (NPCs, items, clues, enemies) are bound to **locations**, not scenes. Each location declares which entities are present via `npc_ids`, `item_ids`, `clue_ids`, `enemy_ids`. Scenes reference locations via `location_ids` and possible transitions via `next_scene_ids`.

See [`dragon_rpg.json`](host/prompt/processed/dragon_rpg.json) for a complete example.

---

## Scenario Editor

Access the visual editor at `http://127.0.0.1:8000/editor`. All scenario JSON fields are editable through the UI:

| Section | Content |
|---------|---------|
| 基本信息 (Meta) | Title, language, summary, initial scene |
| 规则 (Rules) | GM behavioral rules |
| 场景 (Scenes) | Scene definitions, goals, location bindings, next scenes |
| Hybrid | Prepared GM turns for Semi mode (drafts with dice, choices, rewrite notes) |
| 地点 (Locations) | Locations with linked NPCs, items, clues, enemies |
| NPC | Character definitions |
| 道具 (Items) | Items with effects |
| 线索 (Clues) | Story clues |
| 敌人 (Enemies) | Enemy stats, attributes, skills |
| 属性定义 (Attributes) | Custom attribute definitions (e.g. STR, DEX, INT) |
| 角色 (Characters) | Playable characters with HP/MP/SP, attributes, inventory, equipment, skills |
| 全局选项 (Fallback) | Global default choices |
| 战斗选项 (Combat) | Global combat action choices |
| JSON | Raw JSON edit (advanced) |

---

## Game Features

### Characters

Players select a character from the scenario's character list before starting. Each character defines:

- **Basic stats**: HP, MP, SP (with max values)
- **Starting gold** and **inventory** (items with name, description, effect, quantity)
- **Equipment** (equipped item names)
- **Attributes** (see below)
- **Skills** (see below)

Example characters in `dragon_rpg.json`: Hero (balanced), Cleric (healer), Mage (magic), Thief (agility).

### Attributes & Checks

Attributes are custom-defined per scenario. The `dragon_rpg` example defines:

| ID | Name | Description |
|----|------|-------------|
| `str` | 筋力 (Strength) | Physical power |
| `dex` | 敏捷 (Dexterity) | Agility and speed |
| `int` | 知力 (Intelligence) | Magic and knowledge |
| `wis` | 感知 (Wisdom) | Perception and insight |
| `con` | 耐久 (Constitution) | Endurance and toughness |

**Attribute Checks**: The GM can set `dice_type` with an attribute modifier, e.g. `"1d20+str"`. The character's attribute value is automatically added to the d20 roll. With STR=8 and DC=10, a roll of 2+8=10 succeeds.

**Attribute Changes**: The GM can modify attributes mid-game via `state_delta.attribute_changes`:
```json
{ "attribute_changes": { "str": -2, "dex": +1 } }
```

### Skills

Characters and enemies can have skills with:
- **name**, **description**, **effect** (narrative description)
- **dice_type** (optional, e.g. `"1d20+int"` for magic-based skills)
- **cost** and **cost_type** (`"mp"` or `"sp"`)

Example: Cleric's "治癒の祈り" (Healing Prayer) — `dice_type: "1d6+int"`, `cost: 4 MP`, heals HP.

### Enemies & Combat

Enemies are defined in the scenario with full stats, attributes, and skills. They are bound to locations via `enemy_ids`.

When a scene's current location has enemies, the GM automatically switches to **combat choices** (attacking, using skills, defending, using items, fleeing) instead of the usual exploration choices.

Enemy example (`dragon_rpg.json`):
- **Slime** (HP 5, STR 4) — tutorial enemy in the dark forest
- **Ignis the Evil Dragon** (HP 30, STR 18, skills: Fire Breath, Tail Attack)

---

## GM Modes

| Mode | Description |
|------|-------------|
| **Semi** (default) | LLM receives pre-cooked prepared turns (generated via Gemini) and lightly rewrites them for consistency. Uses `*_hybrid.json` scenario packs when available; if the current turn has no prepared draft, it falls back to normal scene context. |
| **Full** | LLM receives scene context (locations, NPCs, items, enemies, clues) and generates the GM response more freely. |

Select mode from the start screen config panel.

---

## Dice System

Standard tabletop dice notation (`1d20`, `2d6`, `1d100`). Dice results include:

- `rolls[]` — individual roll values
- `total` — sum of rolls + attribute modifier (if any)
- `base_total` / `attr_mod` / `attr_key` — present when an attribute check is used

Empty or null `dice_type` defaults to `1d20`.

---

## Scenario Conversion

```powershell
python -m host.scenario_converter "host\prompt\raw\your_scenario.docx"
```

Supports `.txt`, `.docx`, `.pdf`, `.doc` (Windows COM required for `.doc`).

Gemini API key is read from env var `GEMINI_API_KEY`, or from `host/gemini_api_key.txt` / `host/gemini_api_key.py` / `host/auto_tagger.py`. These secret files are excluded via `.gitignore`.

---

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions` | POST | Create new game session |
| `/api/sessions/{id}` | GET | Get session state |
| `/api/sessions/{id}/turn` | POST | Submit player action |
| `/api/scenarios` | GET/POST | List/create scenarios |
| `/api/scenarios/{filename}` | GET/PUT | Read/update scenario |
| `/api/config` | GET/PUT | Read/update backend config |
| `/api/ollama/shutdown` | POST | Remote shutdown (via proxy) |

### Session Creation

```json
{
  "scenario_path": "host/prompt/processed/dragon_rpg.json",
  "gm_mode": "semi",
  "character_id": "hero",
  "character": {
    "name": "アルス",
    "character_image": "/static/images/char_male_hero.png"
  }
}
```

---

## Tests

```powershell
python -m unittest discover -s tests
```

---

## License

See [LICENSE](LICENSE).
