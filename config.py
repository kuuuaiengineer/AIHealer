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
TEMP_VOICE_DIR = BASE_DIR / "temp_voice"
OUTPUT_DIR = BASE_DIR / "output"
