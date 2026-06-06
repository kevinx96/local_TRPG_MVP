# Local LLM TRPG

ローカルLLMをGMとして使う、日本語TRPGクライアントの最小実装です。HostはFastAPIでゲーム状態、セーブ、ダイス、OpenAI互換LLM呼び出しを管理し、Clientはブラウザで動作します（ビジュアルノベル風UI）。

> **Python**: 3.9以上必須。FastAPI/Pydanticで動作確認済み。arm64環境では、ネイティブarm64のPython/Conda環境を推奨します。

📖 **言語**: [English](README.md) · [日本語](#) · [中文](README_ZH.md)

---

## 目次

- [セットアップ](#セットアップ)
- [LLM設定](#llm設定)
- [リモートOllama](#リモートollama)
- [シナリオ形式](#シナリオ形式)
- [シナリオエディタ](#シナリオエディタ)
- [ゲーム機能](#ゲーム機能)
  - [キャラクター](#キャラクター)
  - [属性と判定](#属性と判定)
  - [スキル](#スキル)
  - [敵と戦闘](#敵と戦闘)
- [シナリオ変換](#シナリオ変換)
- [API概要](#api概要)
- [テスト](#テスト)
- [ライセンス](#ライセンス)

---

## セットアップ

```powershell
python -m pip install -r requirements.txt
python -m host.run_server
```

ブラウザが自動で `http://127.0.0.1:8000/` を開きます。自動起動を止めるには：

```powershell
python -m host.run_server --no-browser
```

開発時のホットリロード：

```powershell
python -m host.run_server --reload
```

セッション作成時、GMが自動でオープニングシーンを生成します。プレイヤーはGMのナレーションに続けて最初の行動を入力します。GM応答は生成完了後に全文表示されます。

## LLM設定

`host/config.json` の `active_backend` と `backends` を編集します。

- Ollama（デフォルト）: `http://localhost:11434/v1`
- Koboldcpp: `http://localhost:5001/v1`

どちらもOpenAI互換の `/chat/completions` エンドポイントを使用します。現在のデフォルト優先順は qwen3、フォールバックとして qwen2.5 と ELYZA JP 8B です。

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

### プロンプトパラメータ

| パラメータ | デフォルト | 説明 |
|-----------|---------|------|
| `history_messages` | 4 | LLMに送信する直近メッセージ数 |
| `memory_max_chars` | 1200 | 会話要約の最大文字数 |
| `action_history_max` | 40 | プレイヤー行動履歴の最大エントリ数 |
| `action_history_item_chars` | 80 | 行動履歴1エントリの最大文字数 |

## リモートOllama

低スペックのノートPCでは、ゲームのホスト/クライアントは手元で動かし、LLM呼び出しのみメインPCに向けます。マシン固有の設定は `host/config.json` を直接編集せず、`host/local_config.json` を作成してください。これはgit管理外で、端末固有のURL、トークン、モデル名を書く場所です。

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

ファイルを編集せず、環境変数で上書きすることもできます：

```powershell
$env:TRPG_OLLAMA_BASE_URL = "https://ollama.your-domain.com"
$env:TRPG_OLLAMA_MODEL = "qwen3-swallow-8b-rl-local"
python -m host.run_server
```

### リモート設定手順

1. メインPCで、Cloudflare Tunnelのローカル転送先として使う場合は `OLLAMA_HOST=127.0.0.1:11434`、TailscaleなどのプライベートVPNで使う場合は `OLLAMA_HOST=0.0.0.0:11434` を設定します。
2. CloudflareドメインからメインPCの `http://127.0.0.1:11434` へ向けるCloudflare Tunnelを作成します。
3. Cloudflare Accessまたはサービストークンで保護します。アクセス制御なしでOllamaを公開しないでください。
4. 低スペック側のPCでは `host/local_config.json` または `TRPG_OLLAMA_BASE_URL` をCloudflare TunnelのURLに設定します。

空の `403` レスポンスが返る場合、Ollamaが公開ドメインの `Host` ヘッダーを拒否しています。Cloudflareの `HTTP Host Header` を `localhost:11434` に設定するか、同梱のプロキシを起動：

```powershell
python -m host.ollama_tunnel_proxy
```

その後、Cloudflare TunnelのサービスURLを以下に変更してください：

```text
http://localhost:11435
```

公開側のゲームクライアントは引き続き `https://ollama.your-domain.com/v1` を使用します。変更するのはCloudflareのorigin service URLだけです。

### GGUFモデルの登録

```powershell
python -m host.setup_ollama_models
ollama list
```

`model not found` が表示された場合は、まずGGUFモデルを登録するか、`ollama list` の出力に合わせて設定内の `model` / `fallback_models` を更新してください。

### デバッグログ

デフォルトで有効（`"debug_llm": true`）。`[TRPG-DEBUG]` プレフィックス付きで表示されます。APIキーはログに出力されません。

---

## シナリオ形式

シナリオは [`scenario_pack.schema.json`](host/prompt/processed/scenario_pack.schema.json) で定義された **Scenario Pack** JSON形式を使用します。

```
meta              → title, summary, language, initial_scene
rules[]           → GM行動ルール
scenes[]          → id, title, description, goals, keywords, location_ids, next_scene_ids, fallback_choices
locations[]       → id, title, description, keywords, npc_ids, item_ids, clue_ids, enemy_ids
npcs[]            → id, name, description, keywords
items[]           → id, name, description, effect, keywords
clues[]           → id, title, description, keywords
enemies[]         → id, name, description, image, hp/max_hp, mp/max_mp, sp/max_sp, attributes, skills[]
attribute_defs[]  → id, name, initial_value
characters[]      → id, name, default_name, description, image, image_female, hp/max_hp, mp/max_mp, sp/max_sp, gold, attributes{}, inventory[], equipment[], skills[]
combat_choices[]  → 戦闘時の行動選択肢
fallback_choices[]→ グローバルなデフォルト選択肢
```

エンティティ（NPC、アイテム、手がかり、敵）は **地点（Locations）** に紐付けられます。各地点は `npc_ids`、`item_ids`、`clue_ids`、`enemy_ids` で存在するエンティティを宣言します。シーンは `location_ids` で地点を参照し、`next_scene_ids` で遷移可能なシーンを示します。

完全な例は [`dragon_rpg.json`](host/prompt/processed/dragon_rpg.json) を参照してください。

---

## シナリオエディタ

`http://127.0.0.1:8000/editor` でビジュアルエディタにアクセスできます。全フィールドをUIから編集可能：

| セクション | 内容 |
|---------|------|
| 基本情報 | タイトル、言語、概要、初期シーン |
| ルール | GM行動ルール |
| シーン | シーン定義、目標、地点紐付け、遷移先 |
| Hybrid | Fullモード用の事前準備GMターン（下書き、ダイス、選択肢、修正指示） |
| 地点 | NPC・アイテム・手がかり・敵が紐付いた地点 |
| NPC | ノンプレイヤーキャラクター定義 |
| 道具 | 効果付きアイテム |
| 手がかり | 物語の手がかり |
| 敵 | 敵のステータス、属性、スキル |
| 属性定義 | カスタム属性定義（筋力、敏捷など） |
| キャラクター | プレイアブルキャラクター（HP/MP/SP、属性、所持品、装備、スキル） |
| グローバル選択肢 | デフォルト選択肢 |
| 戦闘選択肢 | 戦闘時の行動選択肢 |
| JSON | 生JSON編集（上級者向け） |

---

## ゲーム機能

### キャラクター

プレイヤーはゲーム開始前にシナリオのキャラクター一覧から選択します。各キャラクターは以下を定義：

- **基本ステータス**: HP、MP、SP（最大値付き）
- **初期ゴールド**と**所持品**（名前、説明、効果、数量）
- **装備**（装備中のアイテム名）
- **属性**（後述）
- **スキル**（後述）

`dragon_rpg.json` のキャラクター例：勇者（バランス型）、僧侶（回復役）、魔法使い（攻撃魔法）、盗賊（敏捷型）。

### 属性と判定

属性はシナリオごとにカスタム定義されます。`dragon_rpg` の例：

| ID | 名前 | 説明 |
|----|------|------|
| `str` | 筋力 | 物理的な力 |
| `dex` | 敏捷 | 素早さと器用さ |
| `int` | 知力 | 魔法と知識 |
| `wis` | 感知 | 知覚と洞察 |
| `con` | 耐久 | 持久力とタフさ |

**属性判定**: GMは `dice_type` に属性修飾子を付加できます（例: `"1d20+str"`）。キャラクターの属性値が自動でd20ロールに加算されます。筋力8でDC10の場合、2+8=10で成功となります。

**属性変化**: GMは `state_delta.attribute_changes` でゲーム中に属性値を変更できます：
```json
{ "attribute_changes": { "str": -2, "dex": +1 } }
```

### スキル

キャラクターと敵は以下の要素を持つスキルを持てます：
- **名前**、**説明**、**効果**（ナラティブ説明）
- **dice_type**（オプション、例: `"1d20+int"` で魔法系スキル）
- **コスト**と**コストタイプ**（`"mp"` または `"sp"`）

例：僧侶の「治癒の祈り」 — `dice_type: "1d6+int"`, `cost: 4 MP`、HPを回復。

### 敵と戦闘

敵はシナリオ内で完全なステータス、属性、スキル付きで定義されます。`enemy_ids` で地点に紐付けられます。

シーンの現在地点に敵が存在する場合、GMは自動で通常の探索選択肢ではなく**戦闘選択肢**（攻撃、スキル使用、防御、アイテム使用、逃走）に切り替えます。

敵の例（`dragon_rpg.json`）:
- **スライム**（HP 5, 筋力 4）— 闇の森のチュートリアル敵
- **邪竜イグニス**（HP 30, 筋力 18, スキル: 炎の息、尻尾攻撃）

---

## GMモード

| モード | 説明 |
|------|------|
| **Semi**（デフォルト） | LLMがシーンコンテキスト（地点、NPC、アイテム、敵、手がかり）を受け取り、自由に即興生成。 |
| **Full** | LLMがGeminiで生成された事前準備ターンを受け取り、現在の状態に合わせて最小限の修正のみ行う。`*_hybrid.json` シナリオパックを使用。 |

スタート画面の設定パネルからモードを選択できます。

---

## ダイスシステム

標準TRPGダイス記法（`1d20`、`2d6`、`1d100`）。ダイス結果は以下を含みます：

- `rolls[]` — 個別の出目
- `total` — 出目の合計 + 属性修飾子（あれば）
- `base_total` / `attr_mod` / `attr_key` — 属性判定時に付加

空またはnullの `dice_type` はデフォルトで `1d20` となります。

---

## シナリオ変換

```powershell
python -m host.scenario_converter "host\prompt\raw\your_scenario.docx"
```

`.txt`、`.docx`、`.pdf`、`.doc`（`.doc`はWindows COMが必要）に対応。

Gemini APIキーは環境変数 `GEMINI_API_KEY`、または `host/gemini_api_key.txt` / `host/gemini_api_key.py` / `host/auto_tagger.py` から読み取られます。これらのsecretファイルは `.gitignore` で除外されています。

---

## API概要

| エンドポイント | メソッド | 説明 |
|----------|--------|------|
| `/api/sessions` | POST | 新規ゲームセッション作成 |
| `/api/sessions/{id}` | GET | セッション状態取得 |
| `/api/sessions/{id}/turn` | POST | プレイヤー行動送信 |
| `/api/scenarios` | GET/POST | シナリオ一覧/作成 |
| `/api/scenarios/{filename}` | GET/PUT | シナリオ読込/保存 |
| `/api/config` | GET/PUT | バックエンド設定読込/更新 |
| `/api/ollama/shutdown` | POST | リモートシャットダウン（プロキシ経由） |

### セッション作成

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

## テスト

```powershell
python -m unittest discover -s tests
```

---

## ライセンス

[LICENSE](LICENSE) を参照。
