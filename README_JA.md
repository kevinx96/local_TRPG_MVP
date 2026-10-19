# 紅き邪竜イグニス — AI GM TRPG

📖 **言語**: [English](README.md) · [日本語](#) · [中文](README_ZH.md)

ビジュアルノベル風のブラウザ画面で遊ぶ、一人用の日本語TRPGです。LLM（Gemini）がGMを務めますが、結果を決めることはありません。プレイヤーの自由入力を決められた形式の「行動案」に解釈するだけで、HP・アイテム・フラグ・位置・ダイス・戦闘・報酬といった数値はすべて決定的なゲームエンジンが管理します。

研究用の実験環境も兼ねています。裁定をエンジンに任せたとき、少ないプロンプトでLLMをどこまで正確かつ安全にGMとして働かせられるか、がテーマです。[論文草稿](docs/research/paper-draft.md)（中国語）を参照してください。

> **Python** 3.9以上。ゲーム内のテキストはすべて日本語です。

---

## 目次

- [特徴](#特徴)
- [はじめかた](#はじめかた)
- [設定](#設定)
- [ゲームの内容](#ゲームの内容)
- [構成](#構成)
- [研究と評価](#研究と評価)
- [開発](#開発)
- [API概要](#api概要)
- [ライセンス](#ライセンス)

---

## 特徴

- **エンジン裁定型のGM**：モデルが埋める行動案のフィールドには、エンジンが列挙したIDしか入りません。エンジンはセッションの複製の上で裁定し、正当な結果だけを反映します。どの実験でも不正な状態変化（S4）は0件です。
- **思い込みではなく測定で**：審査済みの日本語意図ベンチマーク486件、凍結シナリオとキャッシュ再生による評価。凍結testでは、Gemini 3.1 Flash-Liteの許容プラン率97.3%、有害な誤発動率0.68%。
- **モデルなしでも遊べる**：裁定が決定的なので、ゲーム全体をオフラインで通しプレイできます。自動探索による32局の通しプレイを、ソフトロック・状態の矛盾・テキスト漏れの回帰テストとして使っています。
- **一本の冒険として完結**：4職業、5章構成、城塞都市、属性と対策の仲間がそれぞれ異なる3本の第3章ルート、6人の仲間、エピローグ付きの複数エンディング。

## はじめかた

### ソースから

```powershell
python -m pip install -r requirements.txt
python -m host.run_server
```

ブラウザで `http://127.0.0.1:8000/` が開きます。開かない場合は `--no-browser`、別ポートは `--port 8010`、開発中は `--reload`。シナリオエディタは `/editor` です。

### Windows用exe

ローカルでビルドします。APIキーは同梱されず、同梱モジュールをすべて展開して確認する監査が走ります。

```powershell
python -m scripts.build_exe                     # dist/LocalTRPG/LocalTRPG.exe と zip
python -m scripts.build_exe --with-local-config # 自分の host/local_config.json も同梱（個人利用のみ）
```

### 配布用デモ版

キーなしで他人に渡すには、[`workers/gemini-proxy`](workers/gemini-proxy/README.md) のCloudflare Workerを先にデプロイします（キーを預かり、このゲームのリクエストだけを通し、IPごと・1日ごとの上限で費用を抑えます）。

```powershell
$env:DEMO_TOKEN = "<Workerのデモトークン>"
python -m scripts.build_exe --demo-endpoint https://<your-worker>.workers.dev
```

## 設定

既定のモデルはGemini 3.1 Flash-Liteです。個人設定は `host/local_config.json` に書きます（gitの管理外。配布版では `LocalTRPG.exe` と同じフォルダ）。キーは絶対にコミットしないでください。

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

キーは順番に試し、上限到達や認証失敗となったキーは同じセッションではスキップします。新しいセッションでは最初のキーから再開します。従来の `api_key` も使えますが、`api_keys` が優先されます。`api_keys` リストを設定していない場合は、カンマ区切りの `GEMINI_API_KEYS` を指定でき、単一のキーより優先されます。

環境変数での上書き：`GEMINI_API_KEYS`、`GEMINI_API_KEY`、`TRPG_LLM_BASE_URL`、`TRPG_LLM_MODEL`、`TRPG_LLM_API_KEY`、`TRPG_ACTIVE_BACKEND`、`TRPG_LOCAL_CONFIG`。

- 通常のプレイは主モデルと予備モデル1つを、それぞれ15秒のタイムアウトで試します。自由行動の解釈は1回だけです。
- モデルに接続できなくてもゲームは続きます。選択肢と戦闘はエンジンが裁定し、用意された描写はそのまま表示され、それ以外は一行の正直な通知になります。
- Ollamaによるローカルモデルは研究の比較用にだけ残しており、ゲームの設定画面には出ません。

## ゲームの内容

### キャラクター

| 職業 | HP / MP | 特徴 |
|---|---|---|
| 勇者 | 20 / 8 | バランス型。鍛冶屋で氷鉄の大剣を打ってもらえる |
| 僧侶 | 18 / 14 | 回復と聖なる魔法 |
| 魔法使い | 12 / 20 | 攻撃魔法 |
| 盗賊 | 14 / 6 | 潜行判定と素早さ |

### 物語の構成

```
王都 ─ 闇の森 ─┬─ 炎上する麓の村 ─────────────────────┐
               ├─ 霧の古戦場 ─(村の裏手)──────────────┤
               └─ 洞窟の水路 ─ 城塞都市オークスドーン ─┬─ 霧の古戦場
                                                      └─ 地鳴りの峡谷 ─(避難所の裏手)─┘
                                                                    └→ 竜の谷 → 王都に凱旋
```

| 第3章のルート | 属性 | 対策の仲間 |
|---|---|---|
| 麓の村 | 火＋氷 | 火コウモリ竜／ミーナ |
| 霧の古戦場 | 不死（光に弱い） | 聖騎士リーゼ |
| 地鳴りの峡谷 | 土（物理に強く、水に弱い） | 水術士エリオ |

寄り道のルートは最終的に麓の村へ合流するので、主要な出来事を見逃すことはありません。十分な証拠を集めて将軍ドラコの正体を暴けば、真のエンディングへ。ルート・手がかり・最終決戦の助力をまとめた[攻略メモ](docs/design/walkthrough-2026-10-18.md)（中国語、ネタバレあり）もあります。

### システム

- **選択肢と自由入力**：選択肢を選ぶか、好きな行動を書き込みます。選択肢には危険度が表示されます。まだ見たこともない何かが必要な選択肢は「？？？」と表示され、その文面はブラウザにも送られません。
- **ターン制戦闘**：エンジンがすべて裁定します。アニメーションとダメージ表示付きで、1行動の演出は1.4秒以内、スキップ可能です。
- **装備部位**：武器・防具・補助を1つずつ。あとで手に入れた装備は、空いている部位に自動で装着されます。
- **仲間**（同時に1人）：ロビン（HPが最も高い敵へ援護射撃）、ワーロック（2ラウンドごとに回復）、火コウモリ竜（火の攻撃と回復）、ミーナ（氷の魔法）、リーゼ（HPが半分を切ると回復、それ以外は不死を優先して光の一撃）、エリオ（水の刃と、被ダメージを半減する水の帳）。
- **経済**：魔物は売れる戦利品を落とします。精鋭や任意のボスは能力を永続的に上げる霊薬・果実を落とし、潜行で横をすり抜けながら盗むこともできます。拠点ごとに収集の依頼があります。
- **エリアのやり直し**：敗北したら、倒れたエリアの入口からやり直せます。
- **地図、クエスト、商店、休息**、選択を反映した**エピローグ**。

## 構成

| パス | 内容 |
|---|---|
| `host/` | FastAPIサーバー、エンジン（`state.py`、`combat.py`、`free_actions.py`、`shops.py`、`maps.py`）、LLMクライアントとGM契約 |
| `client/` | 素のJSによるビジュアルノベル風UI、戦闘演出、アイテムアイコン |
| `host/prompt/processed/` | シナリオパック `dragon_rpg.json` と `dragon_rpg_hybrid.json`（常に両方を同時に編集）、スキーマ |
| `scripts/scenario/` | 内容を作る冪等なシナリオ移行スクリプト |
| `scripts/balance/`、`scripts/playtest/` | バランスシミュレーションとオフライン探索 |
| `eval/` | ベンチマーク、候補、レポート |
| `workers/gemini-proxy/` | デモ版用のCloudflare Workerキープロキシ |

**自由行動の流れ**：エンジンが簡潔な文脈（行動・障害物・対象・所持品・直近の変化）を組み立てる → 厳格なJSONスキーマで1回だけモデルを呼ぶ → 厳格に解析 → セッションの複製の上で裁定 → エンジンの結果から描写。モデルの出力が状態を直接書き換えることはありません。

**GMモード**：*Semi*（既定）はhybridパックの用意されたターンを軽く書き直し、*Full*は場面の文脈からより自由に描写します。どちらでも結果はエンジンが決めます。

## 研究と評価

- 論文草稿：[`docs/research/paper-draft.md`](docs/research/paper-draft.md)。プロンプトの変更とその測定結果：[`docs/design/prompt-log.md`](docs/design/prompt-log.md)。
- ベンチマークv2：審査済み486件（dev 194／test 292、文型ファミリーで分割）、重大度S0–S4、凍結シナリオ `f41af9d` とキャッシュ再生。[`eval/benchmark/README.md`](eval/benchmark/README.md) を参照。

```powershell
# キャッシュを再生するだけでAPI費用はかかりません。キャッシュにない分も呼ぶ場合は --live を付けます。
python -m scripts.eval.run --suite intent --cases eval/benchmark/intent_v2.jsonl --backend gemini --model gemini-3.1-flash-lite --variant default --split test
```

有料のAPI呼び出しは `--live` を明示したときだけ行われます。

## 開発

役割と共通ルールは [`AGENTS.md`](AGENTS.md) にあります。設計責任者（方針、プロンプト、物語の文面、美術の選定、受け入れ）と工程責任者（コード、テスト、評価、データ入力）の二役で、作業は `docs/specs/` の仕様書として書きます。

コミット前に必ず：

```powershell
python -m unittest discover -s tests -q
node --check client/app.js
```

便利なツール：

```powershell
python -m scripts.playtest.explore      # オフライン通しプレイの回帰テスト（LLMなし）
python -m scripts.balance.checkpoints   # シナリオ編集後にバランスのチェックポイントを再生成
python -m scripts.worker_fingerprints   # プロキシのプロンプト指紋が最新か確認
```

美術の候補と採用状況は `assets/manifest.json` で管理しています。

## API概要

| エンドポイント | メソッド | 説明 |
|---|---|---|
| `/api/sessions` | POST | セッション作成（オープニングを生成） |
| `/api/sessions/{id}` | GET | セッションの状態 |
| `/api/sessions/{id}/turn` | POST | 選択肢または自由入力の行動 |
| `/api/sessions/{id}/combat/actions` | POST | エンジンが裁定する戦闘行動1回 |
| `/api/sessions/{id}/combat/resolve` | POST | 終わった戦闘を1回だけ描写 |
| `/api/sessions/{id}/retry` | POST | 敗北後、エリアの入口からやり直す |
| `/api/sessions/{id}/map/move` | POST | 地図のノードをクリックして移動 |
| `/api/sessions/{id}/items/use` | POST | 背嚢のアイテムを使う・装備する |
| `/api/sessions/{id}/shops/{shop}` | GET | 商店の品揃えと価格 |
| `/api/sessions/{id}/shops/{shop}/buy` · `/sell` | POST | 売買 |
| `/api/scenarios`、`/api/scenarios/{file}` | GET/POST/PUT | シナリオパックの一覧・作成・取得・更新 |
| `/api/config` | GET/PUT | バックエンド設定 |

## ライセンス

[LICENSE](LICENSE) を参照してください。
