"""
メインアプリケーション: FastAPI + LINE Webhook

参照音声は reference_voice/ フォルダに事前配置。
カスタマーからの音声送信は不要。テキストを送ると、その声で読み上げた音声が返る。

エンドポイント:
- POST /webhook : LINE からの Webhook 受信
- GET  /        : ヘルスチェック（Railway 用）
"""

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from linebot.v3.webhooks import MessageEvent, TextMessageContent
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
    OUTPUT_DIR,
    get_reference_voice_path,
)
from utils import (
    ensure_directories,
    get_audio_duration_ms,
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


def _is_text_message(msg) -> bool:
    """テキストメッセージかどうかを判定。"""
    if isinstance(msg, TextMessageContent):
        return True
    t = getattr(msg, "type", None)
    return t == "text" or str(t) == "text"


def _get_reference_wav_path() -> tuple[Path | None, bool]:
    """
    参照音声を wav として取得。
    host.m4a / host.mp3 の場合は一時変換。返り値は (path, needs_cleanup)。
    """
    ref = get_reference_voice_path()
    if ref is None:
        return None, False
    if ref.suffix.lower() == ".wav":
        return ref, False
    # m4a/mp3 は一時 wav に変換
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out = Path(tmp.name)
    try:
        fmt = "m4a" if ref.suffix.lower() == ".m4a" else "mp3"
        audio_to_wav(ref, out, format=fmt)
        return out, True
    except Exception:
        out.unlink(missing_ok=True)
        raise


@handler.add(MessageEvent)
def handle_message(event: MessageEvent):
    """
    メッセージイベント受信時、メッセージタイプに応じて振り分ける。
    isinstance と type 属性の両方で判定し、SDK のパース差異に対応。
    """
    msg = event.message
    msg_type = getattr(msg, "type", None)
    logger.info("Received message: class=%s, type=%s", type(msg).__name__, msg_type)

    if _is_text_message(msg):
        _handle_text(event)
    else:
        logger.info("Unhandled message type: %s, type attr: %s", type(msg).__name__, msg_type)
        _reply_text(
            event.reply_token,
            "テキストメッセージをお送りください。",
        )


@handler.default()
def default_handler(event):
    """どのハンドラにもマッチしなかったイベント用。ログ出力のみ。"""
    logger.info("Unhandled event type: %s", type(event).__name__)


def _handle_text(event: MessageEvent):
    """
    テキストメッセージ受信時:
    1. reference_voice/host.wav を読み込み
    2. TTS でテキストを合成（その声でメッセージを読み上げ）
    3. Cloudinary にアップロード
    4. 音声 URL を LINE で返信
    """
    text = event.message.text

    try:
        ref_wav, needs_cleanup = _get_reference_wav_path()
        if ref_wav is None:
            _reply_text(
                event.reply_token,
                "参照音声が設定されていません。reference_voice/host.wav を配置してください。",
            )
            return

        try:
            ensure_directories()
            output_path = OUTPUT_DIR / "output.wav"
            tts_engine.synthesize(text, ref_wav, output_path)

            url = upload_to_cloudinary(output_path, resource_type="video")
            duration_ms = get_audio_duration_ms(output_path)
            _reply_audio(event.reply_token, url, duration_ms)
        finally:
            if needs_cleanup and ref_wav and ref_wav.exists():
                ref_wav.unlink(missing_ok=True)

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
