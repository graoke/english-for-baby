"""Drill items CRUD router."""

import json
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import engine, DATA_DIR
from ..models import DrillItem, Lesson, SourceType, ContentType

logger = logging.getLogger("peppa.items")

router = APIRouter(prefix="/api/items", tags=["items"])


def get_session():
    with Session(engine) as session:
        yield session


@router.get("", response_model=List[dict])
def list_items(lesson_id: int = None, session: Session = Depends(get_session)):
    q = select(DrillItem).where(DrillItem.enabled == True)
    if lesson_id is not None:
        q = q.where(DrillItem.lesson_id == lesson_id)
    items = session.exec(q.order_by(DrillItem.page_no)).all()
    return [
        {
            "id": i.id,
            "lesson_id": i.lesson_id,
            "page_no": i.page_no,
            "content_type": i.content_type,
            "source_type": i.source_type,
            "text": i.text,
            "text_zh": i.text_zh,
            "image_path": i.image_path,
            "tts_path": i.tts_path,
            "difficulty": i.difficulty,
        }
        for i in items
    ]


@router.post("", response_model=dict)
def create_item(body: dict, session: Session = Depends(get_session)):
    item = DrillItem(
        source_type=body.get("source_type", SourceType.manual),
        lesson_id=body.get("lesson_id"),
        page_no=body.get("page_no", 0),
        content_type=body.get("content_type", ContentType.sentence),
        text=body["text"],
        text_zh=body.get("text_zh"),
        image_path=body.get("image_path"),
        difficulty=body.get("difficulty", 1),
    )
    session.add(item)

    # update lesson page_count
    if item.lesson_id:
        lesson = session.get(Lesson, item.lesson_id)
        if lesson:
            lesson.page_count += 1
            session.add(lesson)

    session.commit()
    session.refresh(item)
    logger.info("Item created: id=%d, text=%r", item.id, item.text[:30])
    return {"id": item.id, "page_no": item.page_no}


@router.post("/batch", response_model=dict)
def batch_create_items(body: dict, session: Session = Depends(get_session)):
    """Batch create items from multiline text. body: {lesson_id, lines: [{text, text_zh?}]}"""
    lesson_id = body["lesson_id"]
    lines = body["lines"]

    lesson = session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    start_no = lesson.page_count
    created = []
    for i, line in enumerate(lines):
        item = DrillItem(
            source_type=SourceType.manual,
            lesson_id=lesson_id,
            page_no=start_no + i + 1,
            content_type=ContentType.sentence,
            text=line["text"],
            text_zh=line.get("text_zh"),
            difficulty=line.get("difficulty", 1),
        )
        session.add(item)
        created.append(item.id)

    lesson.page_count = start_no + len(lines)
    session.add(lesson)
    session.commit()

    logger.info("Batch created %d items for lesson %d", len(created), lesson_id)
    return {"created": len(created), "item_ids": created}


@router.put("/{item_id}", response_model=dict)
def update_item(item_id: int, body: dict, session: Session = Depends(get_session)):
    item = session.get(DrillItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    for key in ("text", "text_zh", "image_path", "tts_path", "difficulty",
                "page_no", "content_type", "enabled", "tags"):
        if key in body:
            if key == "tags" and isinstance(body[key], (list, dict)):
                setattr(item, key, json.dumps(body[key]))
            else:
                setattr(item, key, body[key])
    session.add(item)
    session.commit()
    logger.info("Item updated: id=%d", item_id)
    return {"ok": True}


@router.delete("/{item_id}")
def delete_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(DrillItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    item.enabled = False
    session.add(item)

    # update lesson page_count
    if item.lesson_id:
        lesson = session.get(Lesson, item.lesson_id)
        if lesson and lesson.page_count > 0:
            lesson.page_count -= 1
            session.add(lesson)

    session.commit()
    logger.info("Item deleted: id=%d", item_id)
    return {"ok": True}


@router.post("/{item_id}/generate-tts", response_model=dict)
async def generate_tts(item_id: int, session: Session = Depends(get_session)):
    """Generate TTS audio for a single drill item using edge-tts."""
    item = session.get(DrillItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")

    from ..services.tts import generate_tts as do_tts

    audio_dir = DATA_DIR / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_path = str(audio_dir / f"item_{item_id}.mp3")

    logger.info("TTS start: item_id=%d, text=%r", item_id, item.text[:30])
    try:
        await do_tts(item.text, out_path)
        item.tts_path = f"item_{item_id}.mp3"
        session.add(item)
        session.commit()
        logger.info("TTS done: item_id=%d, path=%s", item_id, item.tts_path)
    except Exception as e:
        logger.exception("TTS failed for item %d", item_id)
        raise

    return {"ok": True, "tts_path": item.tts_path}


@router.post("/lesson/{lesson_id}/generate-tts", response_model=dict)
async def generate_lesson_tts(lesson_id: int, session: Session = Depends(get_session)):
    """Generate TTS for all items in a lesson."""
    lesson = session.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")

    items = session.exec(
        select(DrillItem).where(DrillItem.lesson_id == lesson_id, DrillItem.enabled == True)
    ).all()

    from ..services.tts import generate_tts as do_tts

    audio_dir = DATA_DIR / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Batch TTS start: lesson_id=%d, %d items", lesson_id, len(items))
    generated = 0
    for item in items:
        try:
            out_path = str(audio_dir / f"item_{item.id}.mp3")
            await do_tts(item.text, out_path)
            item.tts_path = f"item_{item.id}.mp3"
            session.add(item)
            generated += 1
        except Exception as e:
            logger.exception("TTS failed for item %d", item.id)

    session.commit()
    logger.info("Batch TTS done: lesson_id=%d, generated=%d/%d", lesson_id, generated, len(items))
    return {"ok": True, "generated": generated}
