# AIDelusion - LINE ボイスクローン Bot

LINE で送った音声を元に声をクローンし、テキストをその声で読み上げて返信する Bot です。

## セットアップ

### 1. 環境変数

`.env.example` を `.env` にコピーし、各値を設定してください。

- **LINE**: [LINE Developers Console](https://developers.line.biz/) でチャネルを作成し、トークンを取得
- **Cloudinary**: [Cloudinary](https://cloudinary.com/) でアカウント作成し、認証情報を取得

### 2. 依存関係

```bash
pip install -r requirements.txt
```

### 3. ローカル実行

```bash
uvicorn main:app --reload --port 8000
```

### 4. Railway デプロイ

#### 前提条件

- GitHub アカウント
- Railway アカウント（[railway.app](https://railway.app/) で無料登録可能）

---

#### Step 1: GitHub にコードをプッシュ

1. [GitHub](https://github.com/) で新規リポジトリを作成
2. ローカルで以下を実行：

   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<あなたのユーザー名>/<リポジトリ名>.git
   git push -u origin main
   ```

   > **注意**: `.env` は `.gitignore` に含まれているため、プッシュされません。環境変数は Railway 側で設定します。

---

#### Step 2: Railway でプロジェクトを作成

1. [Railway](https://railway.app/) にログイン
2. **「New Project」** をクリック
3. **「Deploy from GitHub repo」** を選択
4. GitHub の認証を求められたら許可
5. 先ほどプッシュしたリポジトリを選択して **「Deploy Now」**

---

#### Step 3: 環境変数を設定

1. デプロイされたサービス（カード）をクリック
2. **「Variables」** タブを開く
3. **「+ New Variable」** または **「RAW Editor」** で以下を追加：

   | 変数名 | 値 |
   |--------|-----|
   | `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers Console で取得したチャネルアクセストークン |
   | `LINE_CHANNEL_SECRET` | LINE Developers Console で取得したチャネルシークレット |
   | `CLOUDINARY_CLOUD_NAME` | Cloudinary の Cloud name |
   | `CLOUDINARY_API_KEY` | Cloudinary の API Key |
   | `CLOUDINARY_API_SECRET` | Cloudinary の API Secret |

4. 保存すると自動的に再デプロイされます

---

#### Step 4: 公開 URL を取得

1. サービス画面で **「Settings」** タブを開く
2. **「Networking」** セクションまでスクロール
3. **「Generate Domain」** をクリック
4. 表示された URL（例: `aidelusion-production-xxxx.up.railway.app`）をコピー

---

#### Step 5: LINE Webhook を設定

1. [LINE Developers Console](https://developers.line.biz/console/) を開く
2. 使用するチャネル（Messaging API）を選択
3. **「Messaging API」** タブを開く
4. **「Webhook URL」** に以下を入力して **「Update」**：

   ```
   https://<Step 4で取得したドメイン>/webhook
   ```

   例: `https://aidelusion-production-xxxx.up.railway.app/webhook`

5. **「Webhook の利用」** を **「利用する」** に設定
6. **「検証」** ボタンで接続を確認（成功すると「成功」と表示されます）

---

#### Step 6: 動作確認

1. LINE アプリで Bot を友だち追加
2. 30秒程度の音声メッセージを送信 → 「音声を登録しました」と返ってくれば OK
3. 続けてテキストを送信 → 音声で返信されれば完了

---

#### トラブルシューティング

| 現象 | 確認ポイント |
|------|---------------|
| Webhook 検証が失敗する | 環境変数が正しく設定されているか、デプロイが完了しているか確認 |
| 音声が返ってこない | Cloudinary の認証情報、TTS モックの動作を確認 |
| デプロイが失敗する | Railway のログを確認。`nixpacks.toml` と `Procfile` がリポジトリに含まれているか確認 |

## 音声合成エンジン（TTS）

現在は **モック実装** です。`tts_engine.py` 内のコメントに、OpenVoice および GPT-SoVITS のセットアップ手順を記載しています。実運用時は該当部分を実装に置き換えてください。

## ファイル構成

| ファイル | 説明 |
|----------|------|
| `main.py` | FastAPI エンドポイント・LINE Webhook 処理 |
| `tts_engine.py` | 音声合成（クローン）ロジック |
| `utils.py` | m4a→wav 変換、Cloudinary アップロード、LINE 音声取得 |
| `config.py` | 環境変数・パス設定 |
