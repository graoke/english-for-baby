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


def _find_model_bin(root: Path) -> Path | None:
    """在 root 下递归查找 model.bin，优先返回 HF cache 子目录中的。"""
    candidates = list(root.rglob("model.bin"))
    if not candidates:
        return None
    # 优先返回最深层的（HF cache 结构），避免误判共享目录中的根级 model.bin
    candidates.sort(key=lambda p: len(p.parts), reverse=True)
    return candidates[0].parent


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        
        # 从环境变量读取模型路径
        model_path = os.environ.get("WHISPER_MODEL_PATH", "")
        
        # 判断是否使用本地已转换模型
        # 检查 model_path 本身或其子目录（HF cache）是否含 model.bin
        resolved_path = None
        if model_path:
            model_dir = Path(model_path)
            if (model_dir / "model.bin").exists():
                resolved_path = str(model_dir)
            else:
                found = _find_model_bin(model_dir)
                if found:
                    resolved_path = str(found)
        
        if resolved_path:
            logger.info("Loading whisper model from local: %s (cpu, int8)", resolved_path)
            _model = WhisperModel(resolved_path, device="cpu", compute_type="int8")
        else:
            # 传模型名，faster-whisper 会自动下载
            # download_root 指定下载目录，避免散落各处
            default_models = str(Path(__file__).parent.parent.parent / "data" / "models")
            download_root = os.environ.get("WHISPER_MODEL_PATH", default_models)
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
