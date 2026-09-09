"""Settings router — simple key-value store for app configuration."""

import logging
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import engine
from ..models import Settings

logger = logging.getLogger("peppa.settings")

router = APIRouter(prefix="/api/settings", tags=["settings"])


def get_session():
    with Session(engine) as session:
        yield session


@router.get("", response_model=dict)
def get_settings(session: Session = Depends(get_session)):
    """Return all settings as a dict."""
    rows = session.exec(select(Settings)).all()
    return {r.key: r.value for r in rows}


@router.put("", response_model=dict)
def update_settings(body: dict, session: Session = Depends(get_session)):
    """Update settings from a dict. Only provided keys are changed."""
    for key, value in body.items():
        row = session.exec(select(Settings).where(Settings.key == key)).first()
        if row:
            row.value = str(value)
        else:
            row = Settings(key=key, value=str(value))
        session.add(row)
        logger.info("Setting updated: %s = %s", key, value)
    session.commit()
    return {"ok": True}
