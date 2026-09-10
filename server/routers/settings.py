"""Settings router — key-value store + challenge-response PIN auth."""

import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from ..database import engine
from ..models import Settings

logger = logging.getLogger("peppa.settings")

router = APIRouter(prefix="/api/settings", tags=["settings"])

SENSITIVE_KEYS = {"parent_pin", "parent_pin_salt"}
_pin_attempts: dict[str, list[float]] = {}
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW = 300
_sessions: dict[str, dict] = {}
SESSION_TTL = 86400

# Challenge 存储：{challenge: {salt, created_at}}
_challenges: dict[str, dict] = {}
CHALLENGE_TTL = 60


def _hash_pin(pin: str, salt: str) -> str:
    return hashlib.sha256((salt + pin).encode()).hexdigest()


def _create_session() -> str:
    token = secrets.token_hex(32)
    _sessions[token] = {"created_at": time.time()}
    return token


def _validate_session(token: str) -> bool:
    if not token or token not in _sessions:
        return False
    s = _sessions[token]
    if time.time() - s["created_at"] > SESSION_TTL:
        del _sessions[token]
        return False
    return True


def get_session():
    with Session(engine) as session:
        yield session


def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    if ip not in _pin_attempts:
        _pin_attempts[ip] = []
    _pin_attempts[ip] = [t for t in _pin_attempts[ip] if now - t < ATTEMPT_WINDOW]
    if len(_pin_attempts[ip]) >= MAX_ATTEMPTS:
        return False
    _pin_attempts[ip].append(now)
    return True


async def require_parent(request: Request):
    token = request.headers.get("X-Session-Token", "")
    if _validate_session(token):
        return
    raise HTTPException(401, "需要家长权限")


# ── 通用设置 ────────────────────────────────────────────────────

@router.get("", response_model=dict)
def get_settings(session: Session = Depends(get_session)):
    rows = session.exec(select(Settings)).all()
    return {r.key: r.value for r in rows if r.key not in SENSITIVE_KEYS}


@router.put("", response_model=dict)
def update_settings(body: dict, session: Session = Depends(get_session), _=Depends(require_parent)):
    for key, value in body.items():
        if key in SENSITIVE_KEYS:
            raise HTTPException(400, f"不允许通过此接口修改 {key}")
        row = session.exec(select(Settings).where(Settings.key == key)).first()
        if row:
            row.value = str(value)
        else:
            row = Settings(key=key, value=str(value))
        session.add(row)
        logger.info("Setting updated: %s", key)
    session.commit()
    return {"ok": True}


# ── PIN 状态 ────────────────────────────────────────────────────

@router.get("/pin/status", response_model=dict)
def get_pin_status(session: Session = Depends(get_session)):
    row = session.exec(select(Settings).where(Settings.key == "parent_pin")).first()
    return {"has_pin": bool(row and row.value)}


# ── 设置 PIN ────────────────────────────────────────────────────

@router.post("/pin", response_model=dict)
def set_pin(body: dict, session: Session = Depends(get_session)):
    pin = body.get("pin", "")
    if len(pin) < 4:
        raise HTTPException(400, "PIN 至少 4 位")

    salt = secrets.token_hex(16)
    pin_hash = _hash_pin(pin, salt)

    row_pin = session.exec(select(Settings).where(Settings.key == "parent_pin")).first()
    if row_pin:
        row_pin.value = pin_hash
    else:
        row_pin = Settings(key="parent_pin", value=pin_hash)
    session.add(row_pin)

    row_salt = session.exec(select(Settings).where(Settings.key == "parent_pin_salt")).first()
    if row_salt:
        row_salt.value = salt
    else:
        row_salt = Settings(key="parent_pin_salt", value=salt)
    session.add(row_salt)

    session.commit()
    token = _create_session()
    return {"ok": True, "token": token}


# ── Challenge-Response 认证 ─────────────────────────────────────

@router.post("/pin/challenge", response_model=dict)
def pin_challenge(session: Session = Depends(get_session)):
    """生成 challenge，返回 {challenge, salt}。"""
    salt_row = session.exec(select(Settings).where(Settings.key == "parent_pin_salt")).first()
    if not salt_row or not salt_row.value:
        raise HTTPException(400, "PIN 未设置")

    challenge = secrets.token_hex(32)
    _challenges[challenge] = {
        "salt": salt_row.value,
        "created_at": time.time(),
    }

    # 清理过期 challenge
    now = time.time()
    expired = [c for c, v in _challenges.items() if now - v["created_at"] > CHALLENGE_TTL]
    for c in expired:
        del _challenges[c]

    return {"challenge": challenge, "salt": salt_row.value}


@router.post("/pin/verify", response_model=dict)
def pin_verify(body: dict, request: Request, session: Session = Depends(get_session)):
    """
    验证 challenge-response proof。
    前端计算：
      h = sha256(challenge + sha256(salt + pin))
    发送 h，服务端重新计算并比对。
    """
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(ip):
        raise HTTPException(429, "尝试次数过多，请稍后再试")

    challenge = body.get("challenge", "")
    h_client = body.get("h", "")

    if not challenge or not h_client:
        raise HTTPException(400, "缺少参数")

    if challenge not in _challenges:
        raise HTTPException(400, "challenge 无效或已过期，请重试")

    stored = _challenges.pop(challenge)
    salt = stored["salt"]

    # 获取存储的 PIN hash
    pin_row = session.exec(select(Settings).where(Settings.key == "parent_pin")).first()
    if not pin_row or not pin_row.value:
        raise HTTPException(400, "PIN 未设置")

    # 服务端重算：h = sha256(challenge + sha256(salt + pin))
    # 但服务端没有明文 pin，只有 hash。
    # 换一种方式：前端发 sha256(challenge + stored_hash)，服务端直接算
    h_server = hashlib.sha256(challenge.encode() + pin_row.value.encode()).hexdigest()

    if not hmac.compare_digest(h_client, h_server):
        raise HTTPException(401, "PIN 错误")

    token = _create_session()
    return {"ok": True, "token": token}


@router.post("/pin/logout", response_model=dict)
def logout(request: Request):
    token = request.headers.get("X-Session-Token", "")
    if token in _sessions:
        del _sessions[token]
    return {"ok": True}
