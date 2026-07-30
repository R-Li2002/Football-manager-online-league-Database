from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
import io

from fastapi import HTTPException, UploadFile

from schemas_read import WorkspaceIdentityResponse


PROMOTION_IMAGE_ROOT = Path("static") / "uploads" / "promotions"
PROMOTION_IMAGE_PUBLIC_PREFIX = "/static/uploads/promotions/"
MAX_PROMOTION_IMAGE_BYTES = 5 * 1024 * 1024
MIN_PROMOTION_IMAGE_DIMENSION = 128
MAX_PROMOTION_IMAGE_DIMENSION = 5000
PROMOTION_IMAGE_MAX_WIDTH = 1800
PROMOTION_IMAGE_MAX_HEIGHT = 1200
ALLOWED_PROMOTION_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def save_promotion_image(identity: WorkspaceIdentityResponse, image_file: UploadFile) -> dict[str, Any]:
    if not identity.is_full_admin:
        raise HTTPException(status_code=403, detail="只有完整管理员可以上传宣传图片")
    if str(image_file.content_type or "").lower() not in ALLOWED_PROMOTION_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="宣传图片仅支持 JPG、PNG、WEBP")
    content = image_file.file.read(MAX_PROMOTION_IMAGE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="宣传图片为空")
    if len(content) > MAX_PROMOTION_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="宣传图片不能超过 5MB")

    try:
        from PIL import Image, ImageOps

        image = Image.open(io.BytesIO(content))
        image.verify()
        image = Image.open(io.BytesIO(content))
        image = ImageOps.exif_transpose(image).convert("RGBA")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="宣传图片文件无法识别") from exc

    width, height = image.size
    if min(width, height) < MIN_PROMOTION_IMAGE_DIMENSION:
        raise HTTPException(status_code=400, detail=f"宣传图片最短边不能小于 {MIN_PROMOTION_IMAGE_DIMENSION}px")
    if max(width, height) > MAX_PROMOTION_IMAGE_DIMENSION:
        raise HTTPException(status_code=400, detail=f"宣传图片最长边不能超过 {MAX_PROMOTION_IMAGE_DIMENSION}px")

    image.thumbnail((PROMOTION_IMAGE_MAX_WIDTH, PROMOTION_IMAGE_MAX_HEIGHT))
    PROMOTION_IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:12]}.webp"
    target = PROMOTION_IMAGE_ROOT / filename
    image.save(target, format="WEBP", quality=88, method=6)
    return {
        "success": True,
        "message": "宣传图片已上传",
        "image_url": f"{PROMOTION_IMAGE_PUBLIC_PREFIX}{filename}",
        "width": image.width,
        "height": image.height,
    }
