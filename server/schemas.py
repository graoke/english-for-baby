"""Pydantic schemas for request body validation."""

from typing import Optional, List
from pydantic import BaseModel, Field


# ── Lesson ──────────────────────────────────────────────────────

class LessonCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    cover: Optional[str] = None
    order_no: int = 0


class LessonUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    cover: Optional[str] = None
    order_no: Optional[int] = None
    enabled: Optional[bool] = None


# ── Drill Item ──────────────────────────────────────────────────

class DrillItemCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    text_zh: Optional[str] = None
    lesson_id: Optional[int] = None
    page_no: int = 0
    content_type: str = "sentence"
    source_type: str = "manual"
    image_path: Optional[str] = None
    difficulty: int = Field(1, ge=1, le=5)


class DrillItemUpdate(BaseModel):
    text: Optional[str] = Field(None, min_length=1, max_length=2000)
    text_zh: Optional[str] = None
    image_path: Optional[str] = None
    tts_path: Optional[str] = None
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    page_no: Optional[int] = None
    content_type: Optional[str] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None


class BatchLine(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    text_zh: Optional[str] = None
    difficulty: int = Field(1, ge=1, le=5)


class BatchCreateItems(BaseModel):
    lesson_id: int
    lines: List[BatchLine] = Field(..., min_length=1, max_length=200)


# ── Settings ────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    show_text: Optional[str] = None
    tts_mode: Optional[str] = None


# ── PIN ─────────────────────────────────────────────────────────

class PinSet(BaseModel):
    pin: str = Field(..., min_length=4, max_length=20)
    old_pin: Optional[str] = None


class PinVerify(BaseModel):
    challenge: str
    h: str
