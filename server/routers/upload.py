"""Image upload endpoint with file type validation."""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from ..database import DATA_DIR

router = APIRouter(prefix="/api/upload", tags=["upload"])

IMAGES_DIR = DATA_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png',
    'image/gif', 'image/webp',
}

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

from .settings import require_parent


@router.post("/image", response_model=dict)
async def upload_image(file: UploadFile = File(...), _=Depends(require_parent)):
    if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"不支持的文件类型: {file.content_type}。允许: {', '.join(ALLOWED_IMAGE_TYPES)}")
    
    ext = Path(file.filename or "image.jpg").suffix.lower() or ".jpg"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件扩展名: {ext}。允许: {', '.join(ALLOWED_EXTENSIONS)}")
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "文件大小超过限制（最大 10MB）")
    
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = IMAGES_DIR / filename
    with open(filepath, "wb") as f:
        f.write(content)
    return {"filename": filename, "url": f"/data/images/{filename}"}
