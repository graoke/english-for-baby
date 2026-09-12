"""FastAPI entry point for the children's English reading practice app."""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

from .database import init_db, DATA_DIR
from .routers import lessons, items, attempt, upload, history, settings

# ── Logging setup ──────────────────────────────────────────────
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("peppa")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    logger.info("Database initialized, DATA_DIR=%s", DATA_DIR)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Peppa Reader",
    description="Children's English reading practice web application",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — read origins from env, fallback to dev defaults
import os
_cors_env = os.environ.get("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else [
    "http://localhost:5174", "http://127.0.0.1:5174",
    "https://localhost:5174", "https://127.0.0.1:5174",
    "https://192.168.1.104:5174",
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:80", "http://127.0.0.1:80",
    "http://localhost:8001", "http://127.0.0.1:8001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(lessons.router)
app.include_router(items.router)
app.include_router(attempt.router)
app.include_router(upload.router)
app.include_router(history.router)
app.include_router(settings.router)

# Serve static files (audio, images only — recordings require auth)
for subdir in ("audio", "images"):
    d = DATA_DIR / subdir
    d.mkdir(parents=True, exist_ok=True)
    app.mount(f"/data/{subdir}", StaticFiles(directory=str(d)), name=subdir)


@app.get("/data/recordings/{filename}")
async def serve_recording(filename: str, request: Request):
    """Stream a recording file — requires parent auth (header or query param token)."""
    from fastapi import HTTPException
    # Accept auth via X-Session-Token header OR ?token= query param
    token = request.headers.get("X-Session-Token", "") or request.query_params.get("token", "")
    if not settings._validate_session(token):
        raise HTTPException(401, "需要家长权限")
    filepath = DATA_DIR / "recordings" / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(404, "Recording not found")
    # Prevent path traversal
    if filepath.resolve().parent != (DATA_DIR / "recordings").resolve():
        raise HTTPException(403, "Forbidden")
    import mimetypes
    media_type = mimetypes.guess_type(filename)[0] or "audio/webm"
    def iterfile():
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                yield chunk
    return StreamingResponse(iterfile(), media_type=media_type)


@app.get("/api/health")
def health():
    return {"status": "ok"}
