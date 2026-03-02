"""
音声合成エンジン（ボイスクローン）モジュール

参照音声を元にテキストを読み上げる。
現在はモック実装（参照音声をそのまま返す）。実 TTS は TTS パッケージ等で置き換え可能。
"""

import logging
from pathlib import Path

from config import OUTPUT_DIR

logger = logging.getLogger(__name__)


class TTSEngine:
    """
    音声合成エンジンのラッパークラス。
    参照音声を元に、指定テキストをその声質で合成する。
    """

    def __init__(self):
        pass

    def synthesize(
        self,
        text: str,
        reference_wav_path: Path,
        output_path: Path | None = None,
    ) -> Path:
        """
        テキストをリファレンス音声の声質で合成する。

        Args:
            text: 読み上げるテキスト
            reference_wav_path: リファレンス音声（reference_voice/host.wav）のパス
            output_path: 出力先パス

        Returns:
            生成された音声ファイルのパス
        """
        output_path = output_path or OUTPUT_DIR / "output.wav"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # モック: 参照音声をそのままコピー（Railway のビルド軽量化のため）
        # 実 TTS を使う場合は Coqui TTS 等をここに置き換え
        import shutil

        if reference_wav_path.exists():
            shutil.copy(reference_wav_path, output_path)
            logger.info("TTS mock: copied reference to %s", output_path)
        else:
            self._create_silent_wav(output_path)
            logger.warning("TTS mock: reference not found, created silent wav")

        return output_path

    def _create_silent_wav(self, path: Path) -> None:
        """無音の WAV を生成。"""
        import wave

        with wave.open(str(path), "w") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"")
