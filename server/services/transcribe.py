"""Transcription service using faster-whisper (local)."""

import logging
import time
from typing import List, Dict, Any

logger = logging.getLogger("peppa.transcribe")

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        # small — good accuracy, already cached locally
        logger.info("Loading whisper model: small (cpu, int8)")
        _model = WhisperModel("small", device="cpu", compute_type="int8")
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
