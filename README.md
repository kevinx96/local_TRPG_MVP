# Local LLM TRPG MVP

ローカルLLMをGMとして使う、日本語TRPGクライアントの最小実装です。HostはFastAPIでゲーム状態、セーブ、ダイス、OpenAI互換LLM呼び出しを管理し、Clientはブラウザで動きます。

## セットアップ

```powershell
python -m pip install -r requirements.txt
python -m host.run_server
```

起動するとブラウザで `http://127.0.0.1:8000/` を自動的に開きます。自動起動したくない場合:

```powershell
python -m host.run_server --no-browser
```

開発中に自動リロードしたい場合:

```powershell
python -m host.run_server --reload
```

## LLM設定

`host/config.json` の `active_backend` と `backends` を編集します。

- Ollama既定値: `http://localhost:11434/v1`
- Koboldcpp例: `http://localhost:5001/v1`

どちらもOpenAI互換の `/chat/completions` を使います。既定では `Llama-3-ELYZA-JP-8B-q4_k_m` を優先し、失敗した場合は qwen 系モデルへフォールバックします。

```json
{
  "model": "Llama-3-ELYZA-JP-8B-q4_k_m",
  "fallback_models": [
    "qwen2.5-7b-instruct-q4_k_m",
    "qwen2.5:7b-instruct"
  ]
}
```

LLM通信のデバッグログは既定で有効です。

```json
{
  "debug_llm": true
}
```

CMD/PowerShellには `[TRPG-DEBUG]` で始まるログが出ます。API keyは出力しません。

Ollamaで `model not found` が出る場合は、先にGGUFモデルをOllamaへ登録するか、`host/config.json` の `model` / `fallback_models` を `ollama list` に出ている名前へ変更してください。Koboldcppを使う場合も同じ順序で ELYZA を優先し、qwen をfallbackとして試します。

```powershell
ollama pull qwen2.5:7b-instruct
ollama list
```

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
