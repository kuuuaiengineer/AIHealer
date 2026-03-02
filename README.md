# AIDelusion - LINE ボイスクローン Bot

**reference_voice/** フォルダに配置した音声ファイルの声質で、ゲストが送ったテキストを読み上げて返信する Bot です。

- **カスタマーからの音声送信は不要**
- プロジェクトフォルダに `reference_voice/host.wav` を事前配置
- ゲストがテキストを送ると、その声で読み上げた音声が返る

## セットアップ

### 1. 参照音声の配置

`reference_voice/` フォルダに **host.wav**（または host.m4a / host.mp3）を配置してください。

- 30秒程度のクリアな音声を推奨
- この声質でゲストのテキストが読み上げられます

### 2. 環境変数

`.env.example` を `.env` にコピーし、各値を設定してください。

- **LINE**: [LINE Developers Console](https://developers.line.biz/) でチャネルを作成し、トークンを取得
- **Cloudinary**: [Cloudinary](https://cloudinary.com/) でアカウント作成し、認証情報を取得

### 3. 依存関係

```bash
pip install -r requirements.txt
```

### 4. ローカル実行

```bash
uvicorn main:app --reload --port 8000
```

### 5. Railway デプロイ

#### 前提条件

- GitHub アカウント
- Railway アカウント（[railway.app](https://railway.app/) で無料登録可能）

---

#### Step 1: GitHub にコードをプッシュ

1. `reference_voice/host.wav` を配置しておく（リポジトリに含めてデプロイされる）
2. [GitHub](https://github.com/) で新規リポジトリを作成
3. ローカルで以下を実行：

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

1. `reference_voice/host.wav` を配置した状態でデプロイしていることを確認
2. LINE アプリで Bot を友だち追加
3. テキストを送信 → 音声で返信されれば完了

---

#### トラブルシューティング

| 現象 | 確認ポイント |
|------|---------------|
| Webhook 検証が失敗する | 環境変数が正しく設定されているか、デプロイが完了しているか確認 |
| 音声が返ってこない | Cloudinary の認証情報、TTS モックの動作を確認 |
| デプロイが失敗する | Railway のログを確認。`nixpacks.toml` と `Procfile` がリポジトリに含まれているか確認 |

## 音声合成エンジン（TTS）

現在は **モック実装**（参照音声をそのまま返す）で、Railway のビルドを軽量化しています。実 TTS（Coqui TTS 等）を使う場合は `tts_engine.py` を置き換えてください。

## ファイル構成

| ファイル | 説明 |
|----------|------|
| `main.py` | FastAPI エンドポイント・LINE Webhook 処理 |
| `tts_engine.py` | 音声合成ロジック（モック） |
| `utils.py` | 音声変換、Cloudinary アップロード |
| `config.py` | 環境変数・パス設定 |
| `reference_voice/` | 参照音声（host.wav 等）を配置するフォルダ |
