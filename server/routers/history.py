"""Practice history router — parent view of child's reading records."""

import json
import random
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func, col

from ..database import engine
from ..models import Attempt, DrillItem, Lesson

router = APIRouter(prefix="/api/history", tags=["history"])


def get_session():
    with Session(engine) as session:
        yield session


@router.get("", response_model=List[dict])
def get_practice_history(session: Session = Depends(get_session)):
    """Return practice history grouped by lesson.

    Each entry = one lesson session, with the sentences practiced (last attempt per sentence),
    recordings, and AI assessment.
    """
    # Fetch all attempts with joined item + lesson info
    stmt = (
        select(Attempt, DrillItem, Lesson)
        .join(DrillItem, Attempt.drill_item_id == DrillItem.id)
        .join(Lesson, DrillItem.lesson_id == Lesson.id)
        .order_by(Attempt.created_at.desc())
    )
    rows = session.exec(stmt).all()

    # Group by (lesson_id, date) to create sessions
    from collections import OrderedDict
    import json
    from datetime import datetime

    sessions = OrderedDict()  # key = (lesson_id, date_str)

    for attempt, item, lesson in rows:
        date_str = attempt.created_at.strftime("%Y-%m-%d %H:%M")
        date_day = attempt.created_at.strftime("%Y-%m-%d")
        key = (lesson.id, date_day)

        if key not in sessions:
            sessions[key] = {
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "date": date_day,
                "first_time": date_str,
                "last_time": date_str,
                "sentences": {},  # item_id -> attempt info (keep last)
                "total_attempts": 0,
            }

        s = sessions[key]
        s["total_attempts"] += 1
        s["last_time"] = date_str

        # Keep only the last attempt per sentence (item_id)
        hit_words = None
        if attempt.hit_words:
            try:
                hit_words = json.loads(attempt.hit_words)
            except Exception:
                pass

        s["sentences"][item.id] = {
            "item_id": item.id,
            "text": item.text,
            "text_zh": item.text_zh,
            "image_path": item.image_path,
            "audio_path": attempt.audio_path,
            "asr_text": attempt.asr_text,
            "hit_ratio": attempt.hit_ratio,
            "hit_words": hit_words,
            "mode": attempt.mode,
            "time": date_str,
        }

    # Convert to list and flatten sentences
    result = []
    for s in sessions.values():
        sentence_list = list(s["sentences"].values())
        # Sort by time
        sentence_list.sort(key=lambda x: x["time"])
        result.append({
            "lesson_id": s["lesson_id"],
            "lesson_title": s["lesson_title"],
            "date": s["date"],
            "first_time": s["first_time"],
            "last_time": s["last_time"],
            "total_attempts": s["total_attempts"],
            "unique_sentences": len(sentence_list),
            "sentences": sentence_list,
        })

    return result


@router.get("/stats", response_model=dict)
def get_stats(session: Session = Depends(get_session)):
    """Return summary stats for the parent dashboard."""
    total_attempts = session.exec(select(func.count(Attempt.id))).one()
    total_lessons = session.exec(
        select(func.count(Lesson.id)).where(Lesson.enabled == True)
    ).one()

    # Unique practice days
    stmt = select(Attempt.created_at)
    all_times = session.exec(stmt).all()
    unique_days = set(t.strftime("%Y-%m-%d") for t in all_times) if all_times else set()

    # Average hit ratio (scene 1 only)
    stmt2 = select(func.avg(Attempt.hit_ratio)).where(Attempt.hit_ratio.is_not(None))
    avg_hit = session.exec(stmt2).one()

    return {
        "total_attempts": total_attempts,
        "total_lessons": total_lessons,
        "practice_days": len(unique_days),
        "avg_hit_ratio": round(float(avg_hit), 3) if avg_hit else None,
    }


@router.get("/daily", response_model=List[dict])
def get_daily_stats(session: Session = Depends(get_session)):
    """Return per-day stats: sentence count and average score."""
    stmt = (
        select(
            func.date(Attempt.created_at).label("day"),
            func.count(Attempt.id).label("count"),
            func.avg(Attempt.hit_ratio).label("avg_score"),
        )
        .where(Attempt.hit_ratio.is_not(None))
        .group_by(func.date(Attempt.created_at))
        .order_by(func.date(Attempt.created_at))
    )
    rows = session.exec(stmt).all()
    return [
        {
            "date": str(row.day),
            "sentence_count": row.count,
            "avg_score": round(float(row.avg_score), 3) if row.avg_score else None,
        }
        for row in rows
    ]


@router.get("/weak", response_model=List[dict])
def get_weak_sentences(
    threshold: float = Query(0.7, description="Max avg hit_ratio to be considered weak"),
    session: Session = Depends(get_session),
):
    """Return sentences where the child's average score is below the threshold.

    Once a sentence's avg exceeds the threshold, it drops off this list.
    Returns the weakest attempt's audio for playback.
    """
    # Subquery: avg hit_ratio per drill_item
    subq = (
        select(
            Attempt.drill_item_id,
            func.avg(Attempt.hit_ratio).label("avg_ratio"),
            func.count(Attempt.id).label("attempt_count"),
        )
        .where(Attempt.hit_ratio.is_not(None))
        .group_by(Attempt.drill_item_id)
        .having(func.avg(Attempt.hit_ratio) < threshold)
    ).subquery()

    # Join with drill_item and lesson for text info
    stmt = (
        select(
            subq.c.drill_item_id,
            subq.c.avg_ratio,
            subq.c.attempt_count,
            DrillItem.text,
            DrillItem.text_zh,
            DrillItem.image_path,
        )
        .join(DrillItem, DrillItem.id == subq.c.drill_item_id)
        .where(DrillItem.enabled == True)
        .order_by(subq.c.avg_ratio)
    )
    rows = session.exec(stmt).all()

    result = []
    for row in rows:
        # Get the last attempt's audio for playback
        last_attempt = session.exec(
            select(Attempt)
            .where(Attempt.drill_item_id == row.drill_item_id, Attempt.hit_ratio.is_not(None))
            .order_by(Attempt.created_at.desc())
            .limit(1)
        ).first()
        result.append({
            "item_id": row.drill_item_id,
            "text": row.text,
            "text_zh": row.text_zh,
            "image_path": row.image_path,
            "avg_hit_ratio": round(float(row.avg_ratio), 3),
            "attempt_count": row.attempt_count,
            "audio_path": last_attempt.audio_path if last_attempt else None,
        })

    return result


@router.get("/challenge", response_model=List[dict])
def get_challenge_sentences(
    count: int = Query(5, description="Number of weak sentences to return"),
    threshold: float = Query(0.7, description="Max avg hit_ratio"),
    session: Session = Depends(get_session),
):
    """Return random weak sentences for child's challenge mode.

    Picks sentences with avg hit_ratio below threshold, weighted by weakness
    (lower score = higher chance of being picked).
    """
    subq = (
        select(
            Attempt.drill_item_id,
            func.avg(Attempt.hit_ratio).label("avg_ratio"),
        )
        .where(Attempt.hit_ratio.is_not(None))
        .group_by(Attempt.drill_item_id)
        .having(func.avg(Attempt.hit_ratio) < threshold)
    ).subquery()

    stmt = (
        select(subq.c.drill_item_id, subq.c.avg_ratio, DrillItem.text, DrillItem.text_zh, DrillItem.image_path, DrillItem.tts_path)
        .join(DrillItem, DrillItem.id == subq.c.drill_item_id)
        .where(DrillItem.enabled == True)
    )
    rows = session.exec(stmt).all()

    if not rows:
        return []

    # Weight by weakness: lower score = higher weight
    items_pool = []
    weights = []
    for row in rows:
        weight = max(1, int((threshold - float(row.avg_ratio)) * 100))
        items_pool.append(row)
        weights.append(weight)

    pick_count = min(count, len(items_pool))
    selected_indices = random.choices(range(len(items_pool)), weights=weights, k=pick_count)
    seen = set()
    result = []
    for idx in selected_indices:
        if idx in seen:
            continue
        seen.add(idx)
        row = items_pool[idx]
        result.append({
            "id": row.drill_item_id,
            "text": row.text,
            "text_zh": row.text_zh,
            "image_path": row.image_path,
            "tts_path": row.tts_path,
            "avg_hit_ratio": round(float(row.avg_ratio), 3),
        })

    random.shuffle(result)
    return result
