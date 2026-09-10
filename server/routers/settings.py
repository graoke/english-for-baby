"""Settings router — simple key-value store for app configuration."""

import logging
from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/pin/status", response_model=dict)
def get_pin_status(session: Session = Depends(get_session)):
    """检查是否已设置 PIN。"""
    row = session.exec(select(Settings).where(Settings.key == "parent_pin")).first()
    return {"has_pin": bool(row and row.value)}


@router.post("/pin", response_model=dict)
def set_pin(body: dict, session: Session = Depends(get_session)):
    """设置 PIN。"""
    pin = body.get("pin", "")
    if len(pin) < 4:
        raise HTTPException(400, "PIN 至少 4 位")
    
    row = session.exec(select(Settings).where(Settings.key == "parent_pin")).first()
    if row:
        row.value = pin
    else:
        row = Settings(key="parent_pin", value=pin)
    session.add(row)
    session.commit()
    logger.info("PIN set")
    return {"ok": True}


@router.post("/pin/verify", response_model=dict)
def verify_pin(body: dict, session: Session = Depends(get_session)):
    """验证 PIN。"""
    pin = body.get("pin", "")
    row = session.exec(select(Settings).where(Settings.key == "parent_pin")).first()
    
    if not row or not row.value:
        # 没有设置 PIN，直接通过
        return {"ok": True}
    
    if row.value == pin:
        return {"ok": True}
    else:
        raise HTTPException(401, "PIN 错误")
