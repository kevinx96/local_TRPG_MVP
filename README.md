# 紅き邪竜イグニス — an AI-GM TRPG

📖 **Language**: [English](#) · [日本語](README_JA.md) · [中文](README_ZH.md)

A single-player Japanese tabletop RPG with a visual-novel browser interface. An LLM (Gemini) acts as the Game Master, but it never decides outcomes: it only turns the player's free text into a constrained "plan", and a deterministic engine owns every number — HP, items, flags, position, dice, combat and rewards.

The project is also a research testbed: how accurately and safely can a small prompt budget turn an LLM into a GM when the engine does the adjudicating? See the [paper draft](docs/research/paper-draft.md) (Chinese).

> **Python** 3.9+. All in-game text is Japanese.

---

## Contents

- [Highlights](#highlights)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [The game](#the-game)
- [Architecture](#architecture)
- [Research and evaluation](#research-and-evaluation)
- [Development](#development)
- [API overview](#api-overview)
- [License](#license)

---

## Highlights

- **Engine-adjudicated GM.** The model fills a plan whose fields can only be engine-listed IDs; the engine resolves it on a copy of the session and commits only legal results. Illegal state changes (S4) are zero in every experiment.
- **Measured, not assumed.** A reviewed 486-case Japanese intent benchmark with a frozen scenario and cached replay. On the frozen test split Gemini 3.1 Flash-Lite reaches 97.3% acceptable plans with a 0.68% harmful-misfire rate.
- **Playable without the model.** Because adjudication is deterministic, the whole game can be played through offline; an automated explorer runs 32 playthroughs as a regression test for soft locks, contradictions and leaked text.
- **A full adventure.** Four classes, five chapters, a fortress town, three chapter-3 routes with their own element and counter companion, six companions, multiple endings with epilogues.

## Quick start

### From source

```powershell
python -m pip install -r requirements.txt
python -m host.run_server
```

The browser opens `http://127.0.0.1:8000/`. Use `--no-browser` to skip that, `--port 8010` for another port, or `--reload` while developing. The scenario editor is at `/editor`.

### Windows executable

Build locally — the API key is never bundled, and an audit unpacks every bundled module to make sure:

```powershell
python -m scripts.build_exe                     # dist/LocalTRPG/LocalTRPG.exe + zip
python -m scripts.build_exe --with-local-config # also copy your host/local_config.json (personal use only)
```

### Shareable demo build

To hand the game to others without a key, deploy the Cloudflare Worker proxy in [`workers/gemini-proxy`](workers/gemini-proxy/README.md) (it holds the key, accepts only this game's requests, and caps cost with per-IP and daily limits), then:

```powershell
$env:DEMO_TOKEN = "<the worker's demo token>"
python -m scripts.build_exe --demo-endpoint https://<your-worker>.workers.dev
```

## Configuration

Gemini 3.1 Flash-Lite is the default model. Put personal settings in `host/local_config.json` (git-ignored; next to `LocalTRPG.exe` in the packaged build). Never commit keys.

```json
{
  "active_backend": "gemini",
  "backends": {
    "gemini": {
      "model": "gemini-3.1-flash-lite",
      "fallback_models": ["gemini-3.5-flash-lite", "gemini-3.6-flash"],
      "api_keys": ["YOUR_FIRST_GEMINI_KEY", "YOUR_SECOND_GEMINI_KEY"]
    }
  }
}
```

Keys are tried in order; a key rejected for quota or authentication is skipped for the rest of that session, and a new session starts from the first key. The legacy `api_key` still works; `api_keys` takes precedence. `GEMINI_API_KEYS` accepts comma-separated keys and takes precedence over a single key when no `api_keys` list is configured.

Environment overrides: `GEMINI_API_KEYS`, `GEMINI_API_KEY`, `TRPG_LLM_BASE_URL`, `TRPG_LLM_MODEL`, `TRPG_LLM_API_KEY`, `TRPG_ACTIVE_BACKEND`, `TRPG_LOCAL_CONFIG`.

- Gameplay tries the primary model and one fallback with a 15-second timeout; free-action interpretation makes a single attempt.
- If the model is unreachable the game keeps going: choices and combat are engine-resolved, prepared narration still shows, and anything else gets an honest one-line notice.
- Local models through Ollama are kept for research baselines only and are hidden from game settings.

## The game

### Characters

| Class | HP / MP | Strength |
|---|---|---|
| 勇者 Hero | 20 / 8 | balanced; can fuse an ice greatsword at the forge |
| 僧侶 Cleric | 18 / 14 | healing and holy magic |
| 魔法使い Mage | 12 / 20 | attack magic |
| 盗賊 Thief | 14 / 6 | stealth checks and speed |

### Story structure

```
Capital ─ Dark Forest ─┬─ Burning village ──────────────────┐
                       ├─ Misty old battlefield ─(village)──┤
                       └─ Cave waterway ─ Fortress Oaksdawn ─┬─ Misty old battlefield
                                                             └─ Rumbling gorge ─(village)─┘
                                                                          └→ Dragon Valley → Return to the capital
```

| Chapter-3 route | Element | Counter companion |
|---|---|---|
| Burning village | fire + ice | fire-bat dragon / Mina |
| Misty old battlefield | undead (weak to light) | paladin Liese |
| Rumbling gorge | earth (resists physical, weak to water) | hydromancer Elio |

The optional routes merge back into the village, so no main event is missed. Expose General Draco with enough evidence for the true ending. A spoiler-heavy [walkthrough](docs/design/walkthrough-2026-10-18.md) (Chinese) covers routes, clues and the final fight's helpers.

### Systems

- **Choices and free input.** Pick a choice or type anything. Choices show their risk; options that need something you have never seen appear as 「？？？」, and their text is not even sent to the browser.
- **Turn-based combat** fully resolved by the engine, with animations, damage numbers and a skippable 1.4-second action budget.
- **Equipment slots**: weapon / armor / aid, one each. Gear found later fills an empty slot automatically.
- **Companions** (one at a time): Robin (covering fire at the highest-HP foe), Warlock (heals every 2 rounds), fire-bat dragon (fire damage and healing), Mina (ice magic), Liese (heals under half HP, otherwise light damage, undead first), Elio (water blades and a damage-halving veil).
- **Economy**: monsters drop sellable loot; elites and optional bosses drop permanent stat boosts that can also be stolen by sneaking past; collection quests in each hub.
- **Area retry**: after a defeat, restart from the entrance of the area you died in.
- **Maps, quests, shops, rests, epilogues** that reflect your choices.

## Architecture

| Path | Contents |
|---|---|
| `host/` | FastAPI server, engine (`state.py`, `combat.py`, `free_actions.py`, `shops.py`, `maps.py`), LLM client and GM contract |
| `client/` | Vanilla-JS visual-novel UI, battle effects, item icons |
| `host/prompt/processed/` | Scenario packs `dragon_rpg.json` and `dragon_rpg_hybrid.json` (always edited together), schema |
| `scripts/scenario/` | Idempotent scenario migrations that author content |
| `scripts/balance/`, `scripts/playtest/` | Balance simulations and the offline explorer |
| `eval/` | Benchmark, candidates, reports |
| `workers/gemini-proxy/` | Cloudflare Worker key proxy for demo builds |

**Free action flow**: the engine builds a compact context (actions, obstacles, objects, inventory, recent changes) → one model call with a strict JSON schema → strict parsing → adjudication on a session copy → narration from engine results. A model output can never write state directly.

**GM modes**: *Semi* (default) lightly rewrites prepared turns from the hybrid pack; *Full* lets the model narrate more freely from scene context. In both, outcomes come from the engine.

## Research and evaluation

- Paper draft: [`docs/research/paper-draft.md`](docs/research/paper-draft.md); every prompt change and its measured effect: [`docs/design/prompt-log.md`](docs/design/prompt-log.md).
- Benchmark v2: 486 reviewed cases (dev 194 / test 292, split by sentence family), severity S0–S4, frozen scenario `f41af9d` with cached replay. See [`eval/benchmark/README.md`](eval/benchmark/README.md).

```powershell
# Replays the cache; adds no API cost. Add --live to call the API on cache misses.
python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split test
```

Paid API calls only happen with an explicit `--live`.

## Development

Roles and shared rules are in [`AGENTS.md`](AGENTS.md): a design lead (direction, prompts, story text, art selection, acceptance) and an engineering lead (code, tests, evaluation, data entry). Tasks are written as specs in `docs/specs/`.

Before every commit:

```powershell
python -m unittest discover -s tests -q
node --check client/app.js
```

Useful tools:

```powershell
python -m scripts.playtest.explore      # offline playthrough regression (no LLM)
python -m scripts.balance.checkpoints   # regenerate balance checkpoints after scenario edits
python -m scripts.worker_fingerprints   # check the proxy's prompt fingerprints are current
```

Art candidates and approvals are tracked in `assets/manifest.json`.

## API overview

| Endpoint | Method | Description |
|---|---|---|
| `/api/sessions` | POST | Create a session (generates the opening) |
| `/api/sessions/{id}` | GET | Session state |
| `/api/sessions/{id}/turn` | POST | Choice or free-text action |
| `/api/sessions/{id}/combat/actions` | POST | One engine-resolved combat action |
| `/api/sessions/{id}/combat/resolve` | POST | Narrate a finished battle once |
| `/api/sessions/{id}/retry` | POST | Restart from the area entrance after a defeat |
| `/api/sessions/{id}/map/move` | POST | Move by clicking a map node |
| `/api/sessions/{id}/items/use` | POST | Use or equip an item from the bag |
| `/api/sessions/{id}/shops/{shop}` | GET | Shop stock and prices |
| `/api/sessions/{id}/shops/{shop}/buy` · `/sell` | POST | Trade |
| `/api/scenarios`, `/api/scenarios/{file}` | GET/POST/PUT | List, create, read, update scenario packs |
| `/api/config` | GET/PUT | Backend configuration |

## License

See [LICENSE](LICENSE).
