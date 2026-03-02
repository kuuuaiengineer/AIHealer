"""
設定モジュール: 環境変数とパスの定義
Railway では環境変数で設定。ローカルでは .env を使用。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

# Cloudinary
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

# ディレクトリ（Railway では /tmp、Windows では ./data をデフォルトに）
_DEFAULT_BASE = "/tmp" if os.name != "nt" else str(Path.cwd() / "data")
BASE_DIR = Path(os.getenv("BASE_DIR", _DEFAULT_BASE))
OUTPUT_DIR = BASE_DIR / "output"

# 参照音声（プロジェクトフォルダに事前配置。カスタマーからの音声送信は不要）
_PROJECT_ROOT = Path(__file__).resolve().parent
REFERENCE_VOICE_DIR = _PROJECT_ROOT / "reference_voice"
# host.wav / host.m4a / host.mp3 のいずれかを探す
REFERENCE_VOICE_CANDIDATES = [
    REFERENCE_VOICE_DIR / "host.wav",
    REFERENCE_VOICE_DIR / "host.m4a",
    REFERENCE_VOICE_DIR / "host.mp3",
]


def get_reference_voice_path() -> Path | None:
    """配置された参照音声のパスを返す。見つからなければ None。"""
    for p in REFERENCE_VOICE_CANDIDATES:
        if p.exists():
            return p
    return None
