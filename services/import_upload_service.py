from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from services.import_service import resolve_import_root

UPLOAD_RULES = {
    "roster": ({".xlsx", ".xlsm"}, 20 * 1024 * 1024, Path(".")),
    "attributes": ({".csv", ".xlsx"}, 100 * 1024 * 1024, Path(".")),
    "schedule": ({".xlsx", ".xlsm"}, 20 * 1024 * 1024, Path("schedules")),
}
UPLOAD_CHUNK_SIZE = 1024 * 1024


def _safe_upload_name(filename: str, category: str) -> str:
    source = Path(filename or "").name
    suffix = Path(source).suffix.lower()
    stem = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", Path(source).stem, flags=re.UNICODE).strip("._")
    stem = stem[:80] or category
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stem}__web_{timestamp}_{uuid4().hex[:8]}{suffix}"


async def save_import_upload(upload: UploadFile, category: str) -> Path:
    if category not in UPLOAD_RULES:
        raise HTTPException(status_code=400, detail="不支持的上传类型")
    allowed_suffixes, max_size, relative_dir = UPLOAD_RULES[category]
    filename = Path(upload.filename or "").name
    suffix = Path(filename).suffix.lower()
    if not filename or suffix not in allowed_suffixes:
        allowed_text = " / ".join(sorted(allowed_suffixes))
        raise HTTPException(status_code=400, detail=f"文件格式不支持，请上传 {allowed_text}")

    target_dir = (resolve_import_root() / relative_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / _safe_upload_name(filename, category)
    temp_path = target_dir / f".{target_path.name}.uploading"
    total_size = 0
    first_chunk = True
    try:
        with temp_path.open("wb") as output:
            while True:
                chunk = await upload.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                if first_chunk and suffix in {".xlsx", ".xlsm"} and not chunk.startswith(b"PK"):
                    raise HTTPException(status_code=400, detail="Excel 文件内容无效或已损坏")
                first_chunk = False
                total_size += len(chunk)
                if total_size > max_size:
                    raise HTTPException(status_code=413, detail=f"文件超过 {max_size // (1024 * 1024)} MB 限制")
                output.write(chunk)
        if total_size == 0:
            raise HTTPException(status_code=400, detail="上传文件为空")
        os.replace(temp_path, target_path)
        return target_path
    finally:
        await upload.close()
        if temp_path.exists():
            temp_path.unlink()
