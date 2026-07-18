import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from auth import get_current_user
from storage.b2 import build_key, upload_bytes

router = APIRouter(prefix="/pipeline/uploads", tags=["uploads"])


class UploadResponse(BaseModel):
    url: str
    key: str
    content_type: str
    size: int


@router.post("/image", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    _ = user
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")

    suffix = os.path.splitext(file.filename or "")[1].lower() or ".png"
    key = build_key("uploads", "references", f"{uuid.uuid4().hex}{suffix}")
    url = upload_bytes(content, key, content_type)
    return UploadResponse(url=url, key=key, content_type=content_type, size=len(content))
