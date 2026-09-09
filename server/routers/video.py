"""Video upload + processing router."""

from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter(prefix="/api/video", tags=["video"])


@router.post("/upload", response_model=dict)
async def upload_video(file: UploadFile = File(...)):
    """Upload video file and trigger processing pipeline."""
    # TODO: Phase 3 — ffmpeg + whisper + segment + tag
    return {"ok": False, "error": "Video pipeline not yet implemented (Phase 3)"}
