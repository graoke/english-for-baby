"""Lessons CRUD router."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import engine
from ..models import Lesson, DrillItem

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


def get_session():
    with Session(engine) as session:
        yield session


@router.get("", response_model=List[dict])
def list_lessons(session: Session = Depends(get_session)):
    lessons = session.exec(
        select(Lesson).where(Lesson.enabled == True).order_by(Lesson.order_no)
    ).all()
    return [
        {
            "id": l.id,
            "title": l.title,
            "cover": l.cover,
            "page_count": l.page_count,
            "order_no": l.order_no,
            "enabled": l.enabled,
        }
        for l in lessons
    ]


@router.post("", response_model=dict)
def create_lesson(body: dict, session: Session = Depends(get_session)):
    lesson = Lesson(
        title=body["title"],
        cover=body.get("cover"),
        set_id=body.get("set_id"),
        order_no=body.get("order_no", 0),
    )
    session.add(lesson)
    session.commit()
    session.refresh(lesson)
    return {"id": lesson.id, "title": lesson.title}


@router.get("/{lesson_id}", response_model=dict)
def get_lesson(lesson_id: int, session: Session = Depends(get_session)):
    lesson = session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    items = session.exec(
        select(DrillItem)
        .where(DrillItem.lesson_id == lesson_id, DrillItem.enabled == True)
        .order_by(DrillItem.page_no)
    ).all()
    return {
        "id": lesson.id,
        "title": lesson.title,
        "cover": lesson.cover,
        "page_count": lesson.page_count,
        "items": [
            {
                "id": i.id,
                "page_no": i.page_no,
                "content_type": i.content_type,
                "text": i.text,
                "text_zh": i.text_zh,
                "image_path": i.image_path,
                "tts_path": i.tts_path,
                "difficulty": i.difficulty,
            }
            for i in items
        ],
    }


@router.put("/{lesson_id}", response_model=dict)
def update_lesson(lesson_id: int, body: dict, session: Session = Depends(get_session)):
    lesson = session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    for key in ("title", "cover", "order_no", "enabled", "set_id"):
        if key in body:
            setattr(lesson, key, body[key])
    session.add(lesson)
    session.commit()
    return {"ok": True}


@router.post("/{lesson_id}/recount", response_model=dict)
def recount_lesson(lesson_id: int, session: Session = Depends(get_session)):
    """Recalculate page_count from actual enabled items."""
    lesson = session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    count = len(session.exec(
        select(DrillItem).where(DrillItem.lesson_id == lesson_id, DrillItem.enabled == True)
    ).all())
    lesson.page_count = count
    session.add(lesson)
    session.commit()
    return {"ok": True, "page_count": count}


@router.delete("/{lesson_id}")
def delete_lesson(lesson_id: int, session: Session = Depends(get_session)):
    lesson = session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    lesson.enabled = False
    session.add(lesson)
    session.commit()
    return {"ok": True}
