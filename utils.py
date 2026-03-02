"""
ユーティリティモジュール: ファイル変換・Cloudinaryアップロード・LINE音声取得
"""
from pathlib import Path

import httpx
from pydub import AudioSegment
import cloudinary
import cloudinary.uploader

from config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    OUTPUT_DIR,
)


LINE_DATA_API = "https://api-data.line.me/v2/bot/message"


def get_line_audio_content(message_id: str, channel_access_token: str) -> bytes:
    """
    LINE API から音声メッセージのバイナリを取得する。

    Args:
        message_id: Webhook で受信したメッセージID
        channel_access_token: LINE チャネルアクセストークン

    Returns:
        音声データのバイナリ（m4a形式）
    """
    url = f"{LINE_DATA_API}/{message_id}/content"
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            url,
            headers={"Authorization": f"Bearer {channel_access_token}"},
        )
        resp.raise_for_status()
        return resp.content


def ensure_directories() -> None:
    """必要なディレクトリが存在することを保証する。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def m4a_to_wav(input_path: Path, output_path: Path) -> Path:
    """
    m4a形式の音声ファイルをwav形式に変換する。
    pydubは内部でffmpegを使用する。

    Args:
        input_path: 入力ファイルパス（.m4a）
        output_path: 出力ファイルパス（.wav）

    Returns:
        変換後のファイルパス
    """
    return audio_to_wav(input_path, output_path, format="m4a")


def audio_to_wav(
    input_path: Path, output_path: Path, format: str | None = None
) -> Path:
    """
    音声ファイルをwav形式に変換する。
    m4a, mp3, wav 等に対応。format 省略時は拡張子から自動判定。

    Args:
        input_path: 入力ファイルパス
        output_path: 出力ファイルパス（.wav）
        format: 入力形式（"m4a", "mp3" 等）。None の場合は拡張子から判定

    Returns:
        変換後のファイルパス
    """
    if format:
        audio = AudioSegment.from_file(str(input_path), format=format)
    else:
        audio = AudioSegment.from_file(str(input_path))
    # モノラル、16kHz、16bitに正規化（多くのTTSエンジンで推奨）
    audio = audio.set_channels(1)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_sample_width(2)  # 16bit
    audio.export(str(output_path), format="wav")
    return output_path


def get_audio_duration_ms(file_path: Path) -> int:
    """
    音声ファイルの長さ（ミリ秒）を取得する。
    LINE の AudioMessage の duration に使用。

    Args:
        file_path: 音声ファイルパス

    Returns:
        長さ（ミリ秒）
    """
    audio = AudioSegment.from_file(str(file_path))
    return len(audio)


def upload_to_cloudinary(
    file_path: Path,
    resource_type: str = "video",  # 音声は "video" または "raw"
    public_id: str | None = None,
) -> str:
    """
    Cloudinaryにファイルをアップロードし、公開URLを返す。
    音声ファイルは resource_type="video" でアップロード可能。

    Args:
        file_path: アップロードするファイルのパス
        resource_type: "video"（音声含む）または "raw"
        public_id: 公開ID（省略時はファイル名ベース）

    Returns:
        アップロード後の公開URL
    """
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
    )

    result = cloudinary.uploader.upload(
        str(file_path),
        resource_type=resource_type,
        public_id=public_id or file_path.stem,
        use_filename=True,
        unique_filename=True,
    )
    return result["secure_url"]
