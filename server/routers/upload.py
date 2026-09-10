"""Image upload endpoint with file type validation."""

import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from ..database import DATA_DIR

router = APIRouter(prefix="/api/upload", tags=["upload"])

IMAGES_DIR = DATA_DIR / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# 允许的图片类型
ALLOWED_IMAGE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 
    'image/gif', 'image/webp', 'image/svg+xml'
}

# 允许的扩展名
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}


@router.post("/image", response_model=dict)
async def upload_image(file: UploadFile = File(...)):
    # 校验文件类型
    if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"不支持的文件类型: {file.content_type}。允许的类型: {', '.join(ALLOWED_IMAGE_TYPES)}")
    
    ext = Path(file.filename or "image.jpg").suffix.lower() or ".jpg"
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件扩展名: {ext}。允许的扩展名: {', '.join(ALLOWED_EXTENSIONS)}")
    
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = IMAGES_DIR / filename
    content = await file.read()
    
    # 校验文件大小（最大 10MB）
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "文件大小超过限制（最大 10MB）")
    
    with open(filepath, "wb") as f:
        f.write(content)
    return {"filename": filename, "url": f"/data/images/{filename}"}
