"""Practice history router — parent view of child's reading records."""

import json
import random
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func, col

from ..database import engine
from ..models import Attempt, DrillItem, Lesson

router = APIRouter(prefix="/api/history", tags=["history"])


def get_session():
    with Session(engine) as session:
        yield session


@router.get("", response_model=dict)
def get_practice_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Return practice history grouped by lesson, with pagination."""
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
    from datetime import datetime

    sessions = OrderedDict()

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
                "sentences": {},
                "total_attempts": 0,
            }

        s = sessions[key]
        s["total_attempts"] += 1
        s["last_time"] = date_str

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
    all_sessions = []
    for s in sessions.values():
        sentence_list = list(s["sentences"].values())
        sentence_list.sort(key=lambda x: x["time"])
        all_sessions.append({
            "lesson_id": s["lesson_id"],
            "lesson_title": s["lesson_title"],
            "date": s["date"],
            "first_time": s["first_time"],
            "last_time": s["last_time"],
            "total_attempts": s["total_attempts"],
            "unique_sentences": len(sentence_list),
            "sentences": sentence_list,
        })

    total = len(all_sessions)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": all_sessions[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/stats", response_model=dict)
def get_stats(session: Session = Depends(get_session)):
    """Return summary stats for the parent dashboard."""
    total_attempts = session.exec(select(func.count(Attempt.id))).one()
    total_lessons = session.exec(
        select(func.count(Lesson.id)).where(Lesson.enabled == True)
    ).one()

    stmt = select(Attempt.created_at)
    all_times = session.exec(stmt).all()
    unique_days = set(t.strftime("%Y-%m-%d") for t in all_times) if all_times else set()

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
    Fixed N+1: use single query to get last attempt per item.
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

    # Get last attempt per item in one query (no N+1)
    last_attempt_sq = (
        select(
            Attempt.drill_item_id,
            Attempt.audio_path,
            Attempt.created_at,
        )
        .where(Attempt.audio_path.is_not(None))
        .order_by(Attempt.created_at.desc())
    ).subquery()

    # Only keep the latest attempt per item
    latest = (
        select(
            last_attempt_sq.c.drill_item_id,
            last_attempt_sq.c.audio_path,
            func.max(last_attempt_sq.c.created_at).label("max_created"),
        )
        .group_by(last_attempt_sq.c.drill_item_id)
    ).subquery()

    # Main query
    stmt = (
        select(
            subq.c.drill_item_id,
            subq.c.avg_ratio,
            subq.c.attempt_count,
            DrillItem.text,
            DrillItem.text_zh,
            DrillItem.image_path,
            latest.c.audio_path,
        )
        .join(DrillItem, DrillItem.id == subq.c.drill_item_id)
        .outerjoin(latest, latest.c.drill_item_id == subq.c.drill_item_id)
        .where(DrillItem.enabled == True)
        .order_by(subq.c.avg_ratio)
    )
    rows = session.exec(stmt).all()

    return [
        {
            "item_id": row.drill_item_id,
            "text": row.text,
            "text_zh": row.text_zh,
            "image_path": row.image_path,
            "audio_path": row.audio_path,
            "avg_hit_ratio": round(float(row.avg_ratio), 3),
            "attempt_count": row.attempt_count,
        }
        for row in rows
    ]


@router.get("/challenge", response_model=List[dict])
def get_challenge_sentences(
    count: int = Query(5, description="Number of weak sentences to return"),
    session: Session = Depends(get_session),
):
    """Return random weak sentences for child's challenge mode.
    Fixed N+1: use single query with window function.
    """
    from sqlalchemy import desc as sa_desc
    from sqlalchemy import func as sa_func

    # Window function: row number per item ordered by time desc
    from sqlalchemy import literal_column
    row_num_stmt = (
        select(
            Attempt.drill_item_id,
            Attempt.hit_ratio,
            sa_func.row_number().over(
                partition_by=Attempt.drill_item_id,
                order_by=sa_desc(Attempt.created_at)
            ).label("rn"),
        )
        .where(Attempt.hit_ratio.is_not(None))
    ).subquery()

    # Only keep last 3 per item
    last_3_stmt = (
        select(
            row_num_stmt.c.drill_item_id,
            row_num_stmt.c.hit_ratio,
        )
        .where(row_num_stmt.c.rn <= 3)
    ).subquery()

    # Average of last 3 per item
    avg_stmt = (
        select(
            last_3_stmt.c.drill_item_id,
            sa_func.avg(last_3_stmt.c.hit_ratio).label("avg_recent"),
            sa_func.count().label("cnt"),
        )
        .group_by(last_3_stmt.c.drill_item_id)
        .having(sa_func.avg(last_3_stmt.c.hit_ratio) < 0.7)
    ).subquery()

    # Join with DrillItem
    stmt = (
        select(
            avg_stmt.c.drill_item_id,
            avg_stmt.c.avg_recent,
            avg_stmt.c.cnt,
            DrillItem.text,
            DrillItem.text_zh,
            DrillItem.image_path,
            DrillItem.tts_path,
        )
        .join(DrillItem, DrillItem.id == avg_stmt.c.drill_item_id)
        .where(DrillItem.enabled == True)
    )
    rows = session.exec(stmt).all()

    # Weight by weakness
    items_pool = []
    weights = []
    for row in rows:
        weight = max(1, int((0.7 - row.avg_recent) * 100))
        items_pool.append(row)
        weights.append(weight)

    if not items_pool:
        return []

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
            "avg_hit_ratio": round(float(row.avg_recent), 3),
        })

    random.shuffle(result)
    return result
