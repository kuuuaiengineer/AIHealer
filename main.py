"""
メインアプリケーション: FastAPI + LINE Webhook

エンドポイント:
- POST /webhook : LINE からの Webhook 受信
- GET  /        : ヘルスチェック（Railway 用）
"""

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from linebot.v3.webhooks import (
    MessageEvent,
    AudioMessageContent,
    TextMessageContent,
    FileMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    AudioMessage,
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhook import WebhookHandler

from config import (
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    TEMP_VOICE_DIR,
    OUTPUT_DIR,
)
from utils import (
    ensure_directories,
    get_audio_duration_ms,
    get_line_audio_content,
    audio_to_wav,
    upload_to_cloudinary,
)
from tts_engine import TTSEngine

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AIDelusion - LINE Voice Clone Bot")

# LINE Bot 設定
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# TTS エンジン（シングルトン）
tts_engine = TTSEngine()


@app.on_event("startup")
def startup():
    """起動時にディレクトリを確保。"""
    ensure_directories()


@app.get("/")
def health():
    """ヘルスチェック（Railway 用）。"""
    return {"status": "ok", "service": "AIDelusion"}


@app.post("/webhook")
async def webhook(request: Request):
    """LINE Webhook エンドポイント。"""
    import asyncio

    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    try:
        # handler.handle は同期のため、イベントループをブロックしないようスレッドで実行
        await asyncio.to_thread(handler.handle, body.decode(), signature)
    except InvalidSignatureError:
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.exception("Webhook handler error: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature or body")

    return "OK"


def _is_audio_message(msg) -> bool:
    """音声メッセージかどうかを判定。SDK の型・type 属性の両方に対応。"""
    if isinstance(msg, AudioMessageContent):
        return True
    t = getattr(msg, "type", None)
    return t == "audio" or str(t) == "audio"


def _is_text_message(msg) -> bool:
    """テキストメッセージかどうかを判定。"""
    if isinstance(msg, TextMessageContent):
        return True
    t = getattr(msg, "type", None)
    return t == "text" or str(t) == "text"


def _is_file_message(msg) -> bool:
    """ファイルメッセージかどうかを判定。m4a 等の音声ファイル送信時に type=file になる。"""
    if isinstance(msg, FileMessageContent):
        return True
    t = getattr(msg, "type", None)
    return t == "file" or str(t) == "file"


def _get_audio_extension_from_file_message(msg) -> str:
    """FileMessageContent から音声ファイルの拡張子を取得。"""
    name = getattr(msg, "file_name", None) or getattr(msg, "fileName", None) or ""
    if isinstance(name, str) and "." in name:
        ext = "." + name.rsplit(".", 1)[-1].lower()
        if ext in (".m4a", ".mp3", ".wav", ".aac", ".mp4", ".ogg"):
            return ext
    return ".m4a"


@handler.add(MessageEvent)
def handle_message(event: MessageEvent):
    """
    メッセージイベント受信時、メッセージタイプに応じて振り分ける。
    isinstance と type 属性の両方で判定し、SDK のパース差異に対応。
    """
    msg = event.message
    msg_type = getattr(msg, "type", None)
    logger.info("Received message: class=%s, type=%s", type(msg).__name__, msg_type)

    if _is_audio_message(msg):
        _handle_audio(event, input_suffix=".m4a")
    elif _is_file_message(msg):
        # m4a 等をファイルとして送った場合は type=file になる
        ext = _get_audio_extension_from_file_message(msg)
        _handle_audio(event, input_suffix=ext)
    elif _is_text_message(msg):
        _handle_text(event)
    else:
        logger.info("Unhandled message type: %s, type attr: %s", type(msg).__name__, msg_type)
        _reply_text(
            event.reply_token,
            "音声またはテキストメッセージをお送りください。",
        )


@handler.default()
def default_handler(event):
    """どのハンドラにもマッチしなかったイベント用。ログ出力のみ。"""
    logger.info("Unhandled event type: %s", type(event).__name__)


def _handle_audio(event: MessageEvent, input_suffix: str = ".m4a"):
    """
    音声メッセージ受信時:
    1. LINE からバイナリを取得
    2. 音声ファイル → wav に変換
    3. temp_voice/user_id.wav として保存（リファレンス音声登録）

    input_suffix: 拡張子（.m4a, .mp3 等）。m4a 送信時は .m4a、ファイル送信時は fileName から取得
    """
    user_id = event.source.user_id
    message_id = event.message.id

    try:
        ensure_directories()
        audio_bytes = get_line_audio_content(message_id, LINE_CHANNEL_ACCESS_TOKEN)

        # 一時ファイルに保存（拡張子で pydub が形式を判定）
        with tempfile.NamedTemporaryFile(suffix=input_suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            input_path = Path(tmp.name)

        ref_path = TEMP_VOICE_DIR / f"{user_id}.wav"
        audio_to_wav(input_path, ref_path, format=None)
        input_path.unlink(missing_ok=True)

        logger.info("Saved reference voice: %s", ref_path)

        reply_text = "音声を登録しました。テキストを送ると、その声で読み上げます。"
    except Exception as e:
        logger.exception("Audio processing error: %s", e)
        reply_text = "音声の処理に失敗しました。もう一度お試しください。"

    _reply_text(event.reply_token, reply_text)


def _handle_text(event: MessageEvent):
    """
    テキストメッセージ受信時:
    1. user_id.wav を読み込み
    2. TTS でテキストを合成
    3. Cloudinary にアップロード
    4. 音声 URL を LINE で返信
    """
    user_id = event.source.user_id
    text = event.message.text
    ref_path = TEMP_VOICE_DIR / f"{user_id}.wav"

    try:
        if not ref_path.exists():
            _reply_text(
                event.reply_token,
                "先に30秒程度の音声メッセージを送ってください。声を登録します。",
            )
            return

        ensure_directories()
        output_path = OUTPUT_DIR / "output.wav"
        tts_engine.synthesize(text, ref_path, output_path)

        url = upload_to_cloudinary(output_path, resource_type="video")
        duration_ms = get_audio_duration_ms(output_path)
        _reply_audio(event.reply_token, url, duration_ms)

    except Exception as e:
        logger.exception("TTS/reply error: %s", e)
        _reply_text(event.reply_token, "音声の生成に失敗しました。もう一度お試しください。")


def _reply_text(reply_token: str, text: str) -> None:
    """テキストで返信。"""
    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=text)])
        )


def _reply_audio(reply_token: str, audio_url: str, duration_ms: int) -> None:
    """音声で返信。LINE は HTTPS の音声 URL を要求。"""
    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[AudioMessage(original_content_url=audio_url, duration=duration_ms)],
            )
        )
