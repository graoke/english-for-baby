"""Settings router — SRP-based PIN authentication."""

import hashlib
import logging
import os
import secrets
import time

import srp
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from ..database import engine
from ..models import Settings

logger = logging.getLogger("peppa.settings")

router = APIRouter(prefix="/api/settings", tags=["settings"])

# 敏感字段，不允许通过通用接口读写
SENSITIVE_KEYS = {"parent_pin", "parent_pin_salt", "parent_pin_verifier"}

# SRP 会话存储：{session_id: {salt, verifier, created_at, A, b, B}}
_srp_sessions: dict[str, dict] = {}
SRP_SESSION_TTL = 300  # 5分钟

# PIN 验证尝试记录
_pin_attempts: dict[str, list[float]] = {}
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW = 300

# Session 存储
_sessions: dict[str, dict] = {}
SESSION_TTL = 86400


def _cleanup_srp_sessions():
    """清理过期的 SRP 会话。"""
    now = time.time()
    expired = [k for k, v in _srp_sessions.items() if now - v["created_at"] > SRP_SESSION_TTL]
    for k in expired:
        del _srp_sessions[k]


def get_session():
    with Session(engine) as session:
        yield session


def _check_rate_limit(ip: str) -> bool:
    """检查是否超过尝试次数限制。"""
    now = time.time()
    if ip not in _pin_attempts:
        _pin_attempts[ip] = []
    _pin_attempts[ip] = [t for t in _pin_attempts[ip] if now - t < ATTEMPT_WINDOW]
    if len(_pin_attempts[ip]) >= MAX_ATTEMPTS:
        return False
    _pin_attempts[ip].append(now)
    return True


# ── 通用设置接口（白名单过滤）─────────────────────────────────────

@router.get("", response_model=dict)
def get_settings(session: Session = Depends(get_session)):
    """Return all settings as a dict. 敏感字段已过滤。"""
    rows = session.exec(select(Settings)).all()
    return {r.key: r.value for r in rows if r.key not in SENSITIVE_KEYS}


@router.put("", response_model=dict)
def update_settings(body: dict, session: Session = Depends(get_session)):
    """Update settings from a dict. 敏感字段不允许通过此接口修改。"""
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


# ── PIN 状态 ─────────────────────────────────────────────────────

@router.get("/pin/status", response_model=dict)
def get_pin_status(session: Session = Depends(get_session)):
    """检查是否已设置 PIN。"""
    row = session.exec(select(Settings).where(Settings.key == "parent_pin_verifier")).first()
    return {"has_pin": bool(row and row.value)}


# ── SRP 注册（设置 PIN）─────────────────────────────────────────

@router.post("/pin/register", response_model=dict)
def register_pin(body: dict, session: Session = Depends(get_session)):
    """注册 PIN。前端发送 PIN，后端生成 salt 和 verifier。"""
    pin = body.get("pin", "")
    old_pin = body.get("old_pin", "")
    
    if len(pin) < 4:
        raise HTTPException(400, "PIN 至少 4 位")
    
    # 检查是否已设置 PIN
    existing = session.exec(select(Settings).where(Settings.key == "parent_pin_verifier")).first()
    
    if existing and existing.value:
        # 已设置 PIN，需要验证旧 PIN
        old_salt_row = session.exec(select(Settings).where(Settings.key == "parent_pin_salt")).first()
        if not old_salt_row:
            raise HTTPException(500, "服务端配置错误")
        
        old_salt = bytes.fromhex(old_salt_row.value)
        old_verifier = bytes.fromhex(existing.value)
        
        # 用旧 PIN 创建 SRP 用户验证
        usr = srp.User("parent", old_pin, salt=old_salt)
        uname, A = usr.start_authentication()
        
        # 临时创建 Verifier 来验证旧 PIN
        svr = srp.Verifier("parent", old_salt, old_verifier, A)
        s, B = svr.get_challenge()
        M = usr.process_challenge(s, B)
        
        if M is None:
            raise HTTPException(401, "旧 PIN 错误")
        
        HAMK = svr.verify_session(M)
        if HAMK is None:
            raise HTTPException(401, "旧 PIN 错误")
    
    # 生成新的 salt 和 verifier
    salt, vkey = srp.create_salted_verification_key("parent", pin)
    
    # 存储
    row_salt = session.exec(select(Settings).where(Settings.key == "parent_pin_salt")).first()
    if row_salt:
        row_salt.value = salt.hex()
    else:
        row_salt = Settings(key="parent_pin_salt", value=salt.hex())
    session.add(row_salt)
    
    row_verifier = session.exec(select(Settings).where(Settings.key == "parent_pin_verifier")).first()
    if row_verifier:
        row_verifier.value = vkey.hex()
    else:
        row_verifier = Settings(key="parent_pin_verifier", value=vkey.hex())
    session.add(row_verifier)
    
    session.commit()
    logger.info("PIN registered")
    
    # 自动登录，返回 session token
    token = secrets.token_hex(32)
    _sessions[token] = {"created_at": time.time()}
    return {"ok": True, "token": token}


# ── SRP 认证（验证 PIN）─────────────────────────────────────────

@router.post("/pin/start", response_model=dict)
def pin_start(body: dict):
    """SRP 认证第一步：前端发送 A，后端返回 salt 和 B。"""
    _cleanup_srp_sessions()
    
    A_hex = body.get("A", "")
    if not A_hex:
        raise HTTPException(400, "缺少 A")
    
    A = int(A_hex, 16)
    
    # 生成 session_id
    session_id = secrets.token_hex(16)
    
    # 从数据库读取 salt 和 verifier
    with Session(engine) as session:
        salt_row = session.exec(select(Settings).where(Settings.key == "parent_pin_salt")).first()
        verifier_row = session.exec(select(Settings).where(Settings.key == "parent_pin_verifier")).first()
    
    if not salt_row or not verifier_row:
        raise HTTPException(400, "PIN 未设置")
    
    salt = bytes.fromhex(salt_row.value)
    verifier = bytes.fromhex(verifier_row.value)
    
    # 创建 SRP Verifier
    svr = srp.Verifier("parent", salt, verifier, A)
    s, B = svr.get_challenge()
    
    if s is None or B is None:
        raise HTTPException(400, "SRP 挑战生成失败")
    
    # 存储会话状态
    _srp_sessions[session_id] = {
        "svr": svr,
        "A": A,
        "created_at": time.time(),
    }
    
    return {
        "session_id": session_id,
        "salt": s.hex(),
        "B": hex(B),
    }


@router.post("/pin/verify", response_model=dict)
def pin_verify(body: dict, request: Request):
    """SRP 认证第二步：前端发送 M，后端验证并返回 HAMK 和 session token。"""
    ip = request.client.host if request.client else "unknown"
    
    if not _check_rate_limit(ip):
        raise HTTPException(429, "尝试次数过多，请稍后再试")
    
    session_id = body.get("session_id", "")
    M_hex = body.get("M", "")
    
    if not session_id or not M_hex:
        raise HTTPException(400, "缺少参数")
    
    if session_id not in _srp_sessions:
        raise HTTPException(400, "会话已过期，请重试")
    
    srp_data = _srp_sessions[session_id]
    svr = srp_data["svr"]
    A = srp_data["A"]
    
    M = bytes.fromhex(M_hex)
    HAMK = svr.verify_session(M)
    
    # 清理会话
    del _srp_sessions[session_id]
    
    if HAMK is None:
        raise HTTPException(401, "PIN 错误")
    
    # 验证成功，创建 session token
    token = secrets.token_hex(32)
    _sessions[token] = {"created_at": time.time()}
    
    return {
        "ok": True,
        "HAMK": HAMK.hex(),
        "token": token,
    }


@router.post("/pin/logout", response_model=dict)
def logout(request: Request):
    """登出，销毁 session。"""
    token = request.headers.get("X-Session-Token", "")
    if token in _sessions:
        del _sessions[token]
    return {"ok": True}
