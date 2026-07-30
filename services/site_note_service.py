from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import SiteNote, Team
from schemas_read import SiteNoteResponse
from schemas_write import SiteNoteUpdateRequest
from services.admin_common import LogWriter, require_admin

LEAGUE_LEVELS = {"超级", "甲级", "乙级"}
SUSPENSION_NOTE_PREFIX = "competition.suspensions"
SUSPENSION_TEAM_NOTE_PREFIX = f"{SUSPENSION_NOTE_PREFIX}.team"


def build_suspension_note_key(level: str) -> str:
    clean_level = str(level or "").strip()
    if clean_level not in LEAGUE_LEVELS:
        raise HTTPException(status_code=400, detail="伤停注释仅支持超级、甲级、乙级")
    return f"{SUSPENSION_NOTE_PREFIX}.{clean_level}"


def build_suspension_team_note_key(team_id: int) -> str:
    clean_team_id = int(team_id or 0)
    if clean_team_id <= 0:
        raise HTTPException(status_code=400, detail="球队伤停备注缺少有效球队")
    return f"{SUSPENSION_TEAM_NOTE_PREFIX}.{clean_team_id}"


def _team_id_from_note_key(note_key: str) -> int | None:
    prefix = f"{SUSPENSION_TEAM_NOTE_PREFIX}."
    if not note_key.startswith(prefix):
        return None
    raw_team_id = note_key[len(prefix):]
    if not raw_team_id.isdigit():
        raise HTTPException(status_code=400, detail="球队伤停备注键无效")
    return int(raw_team_id)


def get_suspension_note_level(db: Session, note_key: str) -> str:
    clean_key = str(note_key or "").strip()
    for level in LEAGUE_LEVELS:
        if clean_key == build_suspension_note_key(level):
            return level
    team_id = _team_id_from_note_key(clean_key)
    if team_id is not None:
        team = db.query(Team).filter(Team.id == team_id, Team.level.in_(LEAGUE_LEVELS)).first()
        if not team:
            raise HTTPException(status_code=400, detail="球队伤停备注仅支持当前联赛球队")
        return team.level
    raise HTTPException(status_code=400, detail="不支持的注释键")


def list_site_notes(db: Session) -> list[SiteNoteResponse]:
    level_keys = sorted(build_suspension_note_key(level) for level in LEAGUE_LEVELS)
    rows = (
        db.query(SiteNote)
        .filter(
            (SiteNote.key.in_(level_keys))
            | (SiteNote.key.like(f"{SUSPENSION_TEAM_NOTE_PREFIX}.%"))
        )
        .order_by(SiteNote.key)
        .all()
    )
    visible_rows = []
    for row in rows:
        try:
            get_suspension_note_level(db, row.key)
        except HTTPException:
            continue
        visible_rows.append(SiteNoteResponse.model_validate(row))
    return visible_rows


def update_site_note(
    db: Session,
    admin: str | None,
    note_key: str,
    request: SiteNoteUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, str]:
    operator = require_admin(admin)
    clean_key = str(note_key or "").strip()
    get_suspension_note_level(db, clean_key)
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
