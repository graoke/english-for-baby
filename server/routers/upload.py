"""Image upload endpoint."""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from ..database import DATA_DIR

router = APIRouter(prefix="/api/upload", tags=["upload"])

IMAGES_DIR = DATA_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/image", response_model=dict)
async def upload_image(file: UploadFile = File(...)):
    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = IMAGES_DIR / filename
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    return {"filename": filename, "url": f"/data/images/{filename}"}
