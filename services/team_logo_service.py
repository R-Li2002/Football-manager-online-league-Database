from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import io

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from models import Coach, Team
from services.admin_common import LogWriter, require_admin
from services.coach_service import get_coach_session_identity

TEAM_LOGO_ROOT = Path("static") / "uploads" / "teams"
TEAM_LOGO_PUBLIC_PREFIX = "/static/uploads/teams/"
MAX_TEAM_LOGO_BYTES = 2 * 1024 * 1024
MIN_TEAM_LOGO_DIMENSION = 128
MAX_TEAM_LOGO_DIMENSION = 2400
TEAM_LOGO_OUTPUT_SIZE = 512
ALLOWED_TEAM_LOGO_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def save_team_logo(
    db: Session,
    admin: str | None,
    team_id: int,
    logo: UploadFile,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    return _save_team_logo_for_operator(db, operator, team_id, logo, write_to_log)


def save_own_team_logo(
    db: Session,
    session_token: str | None,
    logo: UploadFile,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    identity = get_coach_session_identity(db, session_token)
    if not identity.authenticated or not identity.coach_uid:
        raise HTTPException(status_code=401, detail="请先登录教练账号")
    if identity.must_change_password:
        raise HTTPException(status_code=403, detail="首次登录必须先修改默认密码")
    if not identity.qq_number:
        raise HTTPException(status_code=403, detail="请先绑定 QQ 号后再使用教练功能")
    coach = db.query(Coach).filter(Coach.uid == identity.coach_uid).first()
    if not coach or not coach.team_id:
        raise HTTPException(status_code=403, detail="当前教练未绑定联赛球队")
    return _save_team_logo_for_operator(db, f"coach:{coach.nickname}", coach.team_id, logo, write_to_log)


def _save_team_logo_for_operator(
    db: Session,
    operator: str,
    team_id: int,
    logo: UploadFile,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="球队不存在")

    previous_logo_path = team.logo_path
    if str(logo.content_type or "").lower() not in ALLOWED_TEAM_LOGO_TYPES:
        raise HTTPException(status_code=400, detail="队徽仅支持 JPG、PNG、WEBP")
    content = logo.file.read(MAX_TEAM_LOGO_BYTES + 1)
    if len(content) > MAX_TEAM_LOGO_BYTES:
        raise HTTPException(status_code=400, detail="队徽不能超过 2MB")

    try:
        from PIL import Image, ImageOps

        image = Image.open(io.BytesIO(content))
        image.verify()
        image = Image.open(io.BytesIO(content))
        image = ImageOps.exif_transpose(image).convert("RGBA")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="队徽文件无法识别") from exc

    width, height = image.size
    if min(width, height) < MIN_TEAM_LOGO_DIMENSION:
        raise HTTPException(status_code=400, detail=f"队徽尺寸至少 {MIN_TEAM_LOGO_DIMENSION}x{MIN_TEAM_LOGO_DIMENSION}")
    if max(width, height) > MAX_TEAM_LOGO_DIMENSION:
        raise HTTPException(status_code=400, detail=f"队徽最长边不能超过 {MAX_TEAM_LOGO_DIMENSION}px")

    alpha_bbox = image.getchannel("A").getbbox()
    if alpha_bbox:
        image = image.crop(alpha_bbox)

    image.thumbnail((TEAM_LOGO_OUTPUT_SIZE, TEAM_LOGO_OUTPUT_SIZE))
    canvas = Image.new("RGBA", (TEAM_LOGO_OUTPUT_SIZE, TEAM_LOGO_OUTPUT_SIZE), (255, 255, 255, 0))
    left = (TEAM_LOGO_OUTPUT_SIZE - image.width) // 2
    top = (TEAM_LOGO_OUTPUT_SIZE - image.height) // 2
    canvas.alpha_composite(image, (left, top))

    TEAM_LOGO_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{team.id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.webp"
    target = TEAM_LOGO_ROOT / filename
    canvas.save(target, format="WEBP", quality=90, method=6)

    team.logo_path = f"{TEAM_LOGO_PUBLIC_PREFIX}{filename}"
    db.commit()
    _delete_previous_team_logo(team.id, previous_logo_path, keep_path=team.logo_path)
    write_to_log("球队队徽更新", f"{team.id} / {team.name}", operator)
    return {"success": True, "message": "队徽已上传", "team_id": team.id, "logo_path": team.logo_path}


def _delete_previous_team_logo(team_id: int, previous_logo_path: str | None, keep_path: str | None = None) -> None:
    if not previous_logo_path or previous_logo_path == keep_path:
        return
    if not previous_logo_path.startswith(TEAM_LOGO_PUBLIC_PREFIX):
        return
    filename = previous_logo_path.removeprefix(TEAM_LOGO_PUBLIC_PREFIX)
    if not filename.startswith(f"{team_id}_"):
        return
    target = (TEAM_LOGO_ROOT / filename).resolve()
    root = TEAM_LOGO_ROOT.resolve()
    if root not in target.parents:
        return
    try:
        target.unlink(missing_ok=True)
    except OSError:
        pass
