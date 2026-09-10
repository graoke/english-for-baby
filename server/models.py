"""SQLModel table definitions — the four core tables + settings."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


# ---------- Enums ----------

class SourceType(str, Enum):
    manual = "manual"


class ContentType(str, Enum):
    word = "word"
    sentence = "sentence"
    passage = "passage"


class AttemptMode(str, Enum):
    assessed = "assessed"
    practice = "practice"


# ---------- lesson ----------

class Lesson(SQLModel, table=True):
    __tablename__ = "lesson"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    cover: Optional[str] = None
    page_count: int = 0
    order_no: int = 0
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


# ---------- drill_item ----------

class DrillItem(SQLModel, table=True):
    __tablename__ = "drill_item"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_type: SourceType

    # scene 1 (manual)
    lesson_id: Optional[int] = Field(default=None, foreign_key="lesson.id")
    page_no: Optional[int] = None
    content_type: Optional[ContentType] = None

    order_no: int = 0

    # shared
    text: str
    text_zh: Optional[str] = None
    image_path: Optional[str] = None
    tts_path: Optional[str] = None
    tags: Optional[str] = None  # JSON string
    difficulty: int = 1
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


# ---------- attempt ----------

class Attempt(SQLModel, table=True):
    __tablename__ = "attempt"

    id: Optional[int] = Field(default=None, primary_key=True)
    drill_item_id: int = Field(foreign_key="drill_item.id")
    audio_path: str
    mode: AttemptMode

    # scene 1 only
    asr_text: Optional[str] = None
    hit_words: Optional[str] = None  # JSON string
    hit_ratio: Optional[float] = None

    # shared
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.now)


# ---------- settings ----------

class Settings(SQLModel, table=True):
    __tablename__ = "settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)
    value: str = ""
    updated_at: datetime = Field(default_factory=datetime.now)
