from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import SiteNote
from schemas_read import SiteNoteResponse
from schemas_write import SiteNoteUpdateRequest
from services.admin_common import LogWriter, require_admin

LEAGUE_LEVELS = {"超级", "甲级", "乙级"}
SUSPENSION_NOTE_PREFIX = "competition.suspensions"


def build_suspension_note_key(level: str) -> str:
    clean_level = str(level or "").strip()
    if clean_level not in LEAGUE_LEVELS:
        raise HTTPException(status_code=400, detail="伤停注释仅支持超级、甲级、乙级")
    return f"{SUSPENSION_NOTE_PREFIX}.{clean_level}"


def _validate_key(note_key: str) -> str:
    clean_key = str(note_key or "").strip()
    if clean_key in {build_suspension_note_key(level) for level in LEAGUE_LEVELS}:
        return clean_key
    raise HTTPException(status_code=400, detail="不支持的注释键")


def list_site_notes(db: Session) -> list[SiteNoteResponse]:
    keys = sorted(build_suspension_note_key(level) for level in LEAGUE_LEVELS)
    rows = db.query(SiteNote).filter(SiteNote.key.in_(keys)).order_by(SiteNote.key).all()
    return [SiteNoteResponse.model_validate(row) for row in rows]


def update_site_note(
    db: Session,
    admin: str | None,
    note_key: str,
    request: SiteNoteUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, str]:
    operator = require_admin(admin)
    clean_key = _validate_key(note_key)
    text = str(request.text or "").strip()
    if len(text) > 160:
        raise HTTPException(status_code=400, detail="注释不能超过 160 个字符")

    note = db.query(SiteNote).filter(SiteNote.key == clean_key).first()
    if not note:
        note = SiteNote(key=clean_key)
        db.add(note)
    note.text = text
    note.updated_by = operator
    note.updated_at = datetime.now()
    db.commit()

    write_to_log("页面注释更新", f"{clean_key}: {text or '清空'}", operator)
    return {"success": True, "message": "注释已保存"}
