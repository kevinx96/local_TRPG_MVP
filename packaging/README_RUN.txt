Local TRPG — 起動方法

1. このフォルダの local_config.example.json を local_config.json という名前でコピーし、
   "api_key" に自分の Gemini API キーを書き込んでください。
   （環境変数 GEMINI_API_KEY を設定しても構いません）
2. LocalTRPG.exe を起動すると、ブラウザで http://127.0.0.1:8000/ が開きます。
3. 黒いウィンドウ（サーバー）を閉じるとゲームも終了します。

セーブデータは saves フォルダ、ログは debug フォルダに保存されます。
API キーは exe には含まれていません。local_config.json を他人に渡さないでください。
