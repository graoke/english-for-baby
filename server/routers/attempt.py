"""Attempt (recording + scoring) router."""

import asyncio
import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session, select

from ..database import engine, DATA_DIR
from ..models import Attempt, DrillItem, AttemptMode

logger = logging.getLogger("peppa.attempt")

router = APIRouter(prefix="/api/attempts", tags=["attempts"])

RECORDINGS_DIR = DATA_DIR / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

# Dedicated thread pool for CPU-heavy ASR — keeps the main event loop responsive.
_executor = ThreadPoolExecutor(max_workers=4)


def get_session():
    with Session(engine) as session:
        yield session


def _run_asr(filepath: str, target_text: str) -> dict:
    """Blocking ASR + comparison. Runs in a thread pool."""
    from ..services.transcribe import transcribe
    from ..services.compare import compare

    t0 = time.time()
    logger.info("ASR start: file=%s", filepath)
    segments = transcribe(filepath)
    t_transcribe = time.time() - t0

    if segments:
        transcript = " ".join(s["text"] for s in segments)
        t1 = time.time()
        result = compare(target_text, transcript)
        t_compare = time.time() - t1
        logger.info("ASR done: transcribe=%.2fs compare=%.2fs total=%.2fs hit_ratio=%.3f",
                     t_transcribe, t_compare, time.time() - t0, result["hit_ratio"])
        return {
            "asr_text": transcript,
            "hit_words": result["hit_words"],
            "hit_ratio": result["hit_ratio"],
        }
    logger.warning("ASR returned no segments for %s (%.2fs)", filepath, time.time() - t0)
    return {"asr_text": None, "hit_words": None, "hit_ratio": None}


@router.get("", response_model=List[dict])
def list_attempts(drill_item_id: int = None, session: Session = Depends(get_session)):
    q = select(Attempt)
    if drill_item_id is not None:
        q = q.where(Attempt.drill_item_id == drill_item_id)
    attempts = session.exec(q.order_by(Attempt.created_at.desc()).limit(100)).all()
    return [
        {
            "id": a.id,
            "drill_item_id": a.drill_item_id,
            "audio_path": a.audio_path,
            "mode": a.mode,
            "asr_text": a.asr_text,
            "hit_ratio": a.hit_ratio,
            "duration_ms": a.duration_ms,
            "created_at": a.created_at.isoformat(),
        }
        for a in attempts
    ]


@router.post("", response_model=dict)
async def create_attempt(
    drill_item_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Upload recording, run comparison in background thread, save attempt.

    Children ALWAYS see confetti — the comparison result is for parents only.
    """
    t_start = time.time()
    logger.info("Upload start: drill_item_id=%d, filename=%s, size=%s",
                drill_item_id, file.filename, file.size)

    # Save recording file
    ext = Path(file.filename or "recording.webm").suffix or ".webm"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = RECORDINGS_DIR / filename
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    t_saved = time.time() - t_start
    logger.info("Saved recording: %s (%d bytes, %.2fs)", filepath, len(content), t_saved)

    # Get the drill item to find target text
    item = session.get(DrillItem, drill_item_id)
    if not item:
        logger.error("DrillItem %d not found", drill_item_id)
        raise HTTPException(404, "DrillItem not found")

    # Run ASR in a thread pool so it doesn't block the event loop
    asr_text = None
    hit_words = None
    hit_ratio = None

    try:
        loop = asyncio.get_event_loop()
        t_asr_start = time.time()
        result = await loop.run_in_executor(
            _executor, _run_asr, str(filepath), item.text
        )
        t_asr = time.time() - t_asr_start
        asr_text = result["asr_text"]
        hit_words = result["hit_words"]
        hit_ratio = result["hit_ratio"]
        logger.info("ASR pipeline done in %.2fs", t_asr)
    except Exception as e:
        logger.exception("ASR comparison failed for %s", filename)

    attempt = Attempt(
        drill_item_id=drill_item_id,
        audio_path=filename,
        mode=AttemptMode.assessed,
        asr_text=asr_text,
        hit_words=json.dumps(hit_words) if hit_words else None,
        hit_ratio=hit_ratio,
        duration_ms=0,
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)

    t_total = time.time() - t_start
    logger.info("Attempt saved: id=%d, hit_ratio=%s, total=%.2fs", attempt.id, hit_ratio, t_total)

    return {
        "id": attempt.id,
        "mode": attempt.mode,
        "hit_ratio": hit_ratio,
    }
