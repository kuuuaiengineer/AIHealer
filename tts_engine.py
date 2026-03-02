"""
音声合成エンジン（ボイスクローン）モジュール

Coqui TTS (XTTS-v2) を使用して、リファレンス音声の声質でテキストを読み上げる。
日本語・英語など多言語に対応。
"""

import logging
from pathlib import Path

from config import OUTPUT_DIR

logger = logging.getLogger(__name__)

# TTS モデル（遅延読み込み）
_tts_model = None


def _get_tts_model():
    """TTS モデルを遅延読み込み。初回呼び出し時にダウンロード・読み込み。"""
    global _tts_model
    if _tts_model is None:
        try:
            from TTS.api import TTS

            # XTTS-v2: 多言語対応、3秒の音声でクローン可能
            # gpu=False で Railway 等の CPU 環境でも動作
            _tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
            logger.info("TTS model (XTTS-v2) loaded")
        except Exception as e:
            logger.exception("Failed to load TTS model: %s", e)
            raise
    return _tts_model


def _detect_language(text: str) -> str:
    """
    テキストから言語を簡易判定。
    日本語文字が含まれれば "ja"、それ以外は "en"。
    """
    for c in text:
        if "\u3040" <= c <= "\u309f" or "\u30a0" <= c <= "\u30ff" or "\u4e00" <= c <= "\u9fff":
            return "ja"
    return "en"


class TTSEngine:
    """
    音声合成エンジン（ボイスクローン）のラッパークラス。
    リファレンス音声を元に、指定テキストをその声質で合成する。
    """

    def __init__(self):
        """エンジンの初期化。モデルは初回 synthesize 時に読み込む。"""
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
            reference_wav_path: リファレンス音声（host.wav）のパス
            output_path: 出力先パス。省略時は OUTPUT_DIR/output.wav

        Returns:
            生成された音声ファイルのパス
        """
        output_path = output_path or OUTPUT_DIR / "output.wav"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        if not reference_wav_path.exists():
            logger.warning("Reference not found: %s", reference_wav_path)
            self._create_silent_wav(output_path)
            return output_path

        try:
            tts = _get_tts_model()
            language = _detect_language(text)

            tts.tts_to_file(
                text=text,
                file_path=str(output_path),
                speaker_wav=str(reference_wav_path),
                language=language,
            )
            logger.info("TTS synthesized: %s -> %s", text[:30], output_path)
        except Exception as e:
            logger.exception("TTS synthesis failed: %s", e)
            # フォールバック: リファレンスをコピー（エラー時）
            import shutil

            shutil.copy(reference_wav_path, output_path)
            logger.warning("Fallback: copied reference to %s", output_path)

        return output_path

    def _create_silent_wav(self, path: Path) -> None:
        """無音の WAV ファイルを生成（フォールバック用）。"""
        import wave

        with wave.open(str(path), "w") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b"")
