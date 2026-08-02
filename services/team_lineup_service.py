from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import Player, Team, TeamLineup
from schemas_read import TeamLineupResponse
from schemas_write import TeamLineupUpdateRequest
from services import workspace_service
from services.admin_common import LogWriter


FORMATION_SLOTS = {
    "4-3-3": {"gk", "def_l", "def_lc", "def_rc", "def_r", "mc_l", "mc_c", "mc_r", "am_wl", "fw_c", "am_wr"},
    "4-2-3-1": {"gk", "def_l", "def_lc", "def_rc", "def_r", "dm_l", "dm_r", "am_wl", "am_c", "am_wr", "fw_c"},
    "3-4-3": {"gk", "def_lc", "def_c", "def_rc", "mc_wl", "mc_l", "mc_r", "mc_wr", "fw_l", "fw_c", "fw_r"},
    "3-5-2": {"gk", "def_lc", "def_c", "def_rc", "dm_wl", "mc_l", "mc_c", "mc_r", "dm_wr", "fw_l", "fw_r"},
    "4-4-2": {"gk", "def_l", "def_lc", "def_rc", "def_r", "mc_wl", "mc_l", "mc_r", "mc_wr", "fw_l", "fw_r"},
}
ALL_TACTICAL_SLOTS = {
    "fw_l", "fw_c", "fw_r",
    "am_wl", "am_l", "am_c", "am_r", "am_wr",
    "mc_wl", "mc_l", "mc_c", "mc_r", "mc_wr",
    "dm_wl", "dm_l", "dm_c", "dm_r", "dm_wr",
    "def_l", "def_lc", "def_c", "def_rc", "def_r",
    "gk",
}


def _decode_picks(raw_value: str | None) -> dict[str, int]:
    try:
        payload = json.loads(raw_value or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    picks: dict[str, int] = {}
    for key, value in payload.items():
        try:
            uid = int(value)
        except (TypeError, ValueError):
            continue
        if uid > 0:
            picks[str(key)] = uid
    return picks


def _resolve_editor(
    db: Session,
    team: Team,
    admin_session_token: str | None,
    coach_session_token: str | None,
) -> tuple[bool, str | None]:
    identity = workspace_service.resolve_workspace_identity(
        db,
        admin_session_token=admin_session_token,
        coach_session_token=coach_session_token,
    )
    if not identity:
        return False, None
    if identity.is_full_admin:
        return True, identity.principal_id
    if identity.source == "coach_account" and str(identity.team_name or "").strip() == str(team.name or "").strip():
        return True, identity.principal_id
    return False, identity.principal_id


def get_team_lineup(
    db: Session,
    team_id: int,
    *,
    admin_session_token: str | None = None,
    coach_session_token: str | None = None,
) -> TeamLineupResponse:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="球队不存在")
    record = db.query(TeamLineup).filter(TeamLineup.team_id == team.id).first()
    can_edit, _ = _resolve_editor(db, team, admin_session_token, coach_session_token)
    return TeamLineupResponse(
        team_id=team.id,
        team_name=team.name,
        formation=record.formation if record else "4-3-3",
        picks=_decode_picks(record.picks_json if record else None),
        is_saved=record is not None,
        can_edit=can_edit,
        updated_by=record.updated_by if record else None,
        updated_at=record.updated_at if record else None,
    )


def save_team_lineup(
    db: Session,
    team_id: int,
    request: TeamLineupUpdateRequest,
    *,
    admin_session_token: str | None = None,
    coach_session_token: str | None = None,
    write_to_log: LogWriter | None = None,
) -> TeamLineupResponse:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="球队不存在")
    can_edit, operator = _resolve_editor(db, team, admin_session_token, coach_session_token)
    if not can_edit or not operator:
        raise HTTPException(status_code=403, detail="只有本队主教练或完整管理员可以保存阵容")

    formation = str(request.formation or "").strip()
    if formation not in FORMATION_SLOTS:
        raise HTTPException(status_code=400, detail="不支持该阵型")

    normalized_picks: dict[str, int] = {}
    for raw_key, raw_uid in (request.picks or {}).items():
        key = str(raw_key or "").strip()
        try:
            uid = int(raw_uid)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="阵容球员 UID 格式错误")
        if key not in ALL_TACTICAL_SLOTS:
            raise HTTPException(status_code=400, detail=f"场上不存在位置：{key}")
        if uid > 0:
            normalized_picks[key] = uid

    if len(normalized_picks) != 11:
        raise HTTPException(status_code=400, detail="场上必须恰好安排 11 名球员后才能保存")
    if len(set(normalized_picks.values())) != len(normalized_picks):
        raise HTTPException(status_code=400, detail="同一名球员不能占据多个位置")

    selected_uids = set(normalized_picks.values())
    if selected_uids:
        valid_uids = {
            int(uid)
            for (uid,) in db.query(Player.uid).filter(
                or_(Player.team_id == team.id, Player.team_name == team.name),
                Player.uid.in_(selected_uids),
            ).all()
        }
        if valid_uids != selected_uids:
            raise HTTPException(status_code=400, detail="阵容中包含不属于该球队的球员")

    record = db.query(TeamLineup).filter(TeamLineup.team_id == team.id).first()
    if not record:
        record = TeamLineup(team_id=team.id)
        db.add(record)
    record.formation = formation
    record.picks_json = json.dumps(normalized_picks, ensure_ascii=False, sort_keys=True)
    record.updated_by = operator
    record.updated_at = datetime.now()
    db.commit()
    db.refresh(record)

    from services.player_power_ranking_service import invalidate_power_caches

    invalidate_power_caches()

    if write_to_log:
        write_to_log("阵容", f"保存 {team.name} {formation} 首发阵容（{len(normalized_picks)} 人）", operator)

    return TeamLineupResponse(
        team_id=team.id,
        team_name=team.name,
        formation=record.formation,
        picks=_decode_picks(record.picks_json),
        is_saved=True,
        can_edit=True,
        updated_by=record.updated_by,
        updated_at=record.updated_at,
    )
