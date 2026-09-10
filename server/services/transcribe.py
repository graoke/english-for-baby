"""Transcription service using faster-whisper (local)."""

import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("peppa.transcribe")

_model = None

# 默认模型路径（相对于项目根目录）
DEFAULT_WHISPER_PATH = str(Path(__file__).parent.parent.parent / "data" / "models" / "whisper")


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        
        # 从环境变量读取模型路径
        model_path = os.environ.get("WHISPER_MODEL_PATH", "")
        
        # 判断是否使用本地已转换模型
        use_local = False
        if model_path:
            model_dir = Path(model_path)
            # 只有目录存在且非空（有模型文件）才用本地路径
            if model_dir.exists() and any(model_dir.iterdir()):
                use_local = True
        
        if use_local:
            logger.info("Loading whisper model from local: %s (cpu, int8)", model_path)
            _model = WhisperModel(model_path, device="cpu", compute_type="int8")
        else:
            # 传模型名，faster-whisper 会自动下载
            # download_root 指定下载目录，避免散落各处
            download_root = str(Path(__file__).parent.parent.parent / "data" / "models")
            Path(download_root).mkdir(parents=True, exist_ok=True)
            logger.info("Loading whisper model: small (cpu, int8), download_root=%s", download_root)
            _model = WhisperModel("small", device="cpu", compute_type="int8", download_root=download_root)
        
        logger.info("Whisper model loaded")
    return _model


def transcribe(audio_path: str, language: str = "en") -> List[Dict[str, Any]]:
    """Transcribe audio file and return segments with timestamps.

    Returns list of {"text": str, "start": float, "end": float}.
    """
    t0 = time.time()
    model = _get_model()
    segments, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=5,
        word_timestamps=False,
    )
    results = []
    for seg in segments:
        results.append({
            "text": seg.text.strip(),
            "start": seg.start,
            "end": seg.end,
        })
    elapsed = time.time() - t0
    logger.info("Transcribed %s in %.2fs → %r", audio_path, elapsed, " ".join(r["text"] for r in results)[:80])
    return results
