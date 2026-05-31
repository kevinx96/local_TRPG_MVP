# Local LLM TRPG MVP

ローカルLLMをGMとして使う、日本語TRPGクライアントの最小実装です。HostはFastAPIでゲーム状態、セーブ、ダイス、OpenAI互換LLM呼び出しを管理し、Clientはブラウザで動きます。

## セットアップ

```powershell
python -m pip install -r requirements.txt
python -m uvicorn host.app:app --host 127.0.0.1 --port 8000 --reload
```

ブラウザで `http://127.0.0.1:8000` を開きます。

## LLM設定

`host/config.json` の `active_backend` と `backends` を編集します。

- Ollama既定値: `http://localhost:11434/v1`
- Koboldcpp例: `http://localhost:5001/v1`

どちらもOpenAI互換の `/chat/completions` を使います。

## シナリオ変換

```powershell
python -m host.scenario_converter "host\prompt\raw\疯狂之馆(最终定稿) .docx"
```

`.txt`、`.docx`、`.pdf`、`.doc` をサポートします。`.doc` はWindows上のMicrosoft Word COMで変換します。

Gemini API key は環境変数 `GEMINI_API_KEY`、または `host/gemini_api_key.txt` / `host/gemini_api_key.py` / 既存の `host/auto_tagger.py` から読みます。これらの秘密ファイルは `.gitignore` で除外されます。

## テスト

```powershell
python -m unittest discover -s tests
```

## Gitに入れないもの

- `host/models/` と `*.gguf`
- `host/saves/`
- `host/prompt/processed/`
- Gemini API key を含むローカルファイル
