from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import CupMatch, Team
from repositories.team_repository import get_team_by_id, list_visible_teams
from schemas_read import CupBracketResponse, CupMatchResponse
from schemas_write import CupMatchResultUpdateRequest, CupMatchTeamsUpdateRequest
from services.admin_common import LogWriter, require_admin

CUP_DEFINITIONS = {
    "champions_cup": {
        "title": "冠军杯",
        "trophy_url": "/static/images/trophy/champion.png",
        "theme": "champion",
    },
    "league_cup": {
        "title": "联盟杯",
        "trophy_url": "/static/images/trophy/league.png",
        "theme": "league",
    },
    "wumingjian_cup": {
        "title": "无铭剑杯",
        "trophy_url": "/static/images/trophy/FA.png",
        "theme": "wumingjian",
    },
}

CUP_STAGES_16 = [
    ("round_of_16", "1/8淘汰赛", 8),
    ("quarter_final", "1/4淘汰赛", 4),
    ("semi_final", "半决赛", 2),
    ("final", "决赛", 1),
]

CUP_STAGES_32 = [
    ("round_of_32", "1/16淘汰赛（上方主场）", 16),
    ("round_of_16", "1/8淘汰赛（下方主场）", 8),
    ("quarter_final", "1/4淘汰赛（上方主场）", 4),
    ("semi_final", "半决赛", 2),
    ("final", "决赛", 1),
]

VISIBLE_LEVEL = "隐藏"
VALID_STATUSES = {"scheduled", "played"}


def get_cup_stages(competition: str) -> list[tuple[str, str, int]]:
    return CUP_STAGES_32 if competition == "wumingjian_cup" else CUP_STAGES_16


def get_first_stage(competition: str) -> str:
    return get_cup_stages(competition)[0][0]


def normalize_competition(competition: str) -> str:
    key = str(competition or "").strip()
    aliases = {
        "champion": "champions_cup",
        "champion_cup": "champions_cup",
        "champions": "champions_cup",
        "冠军杯": "champions_cup",
        "league": "league_cup",
        "联盟杯": "league_cup",
        "fa": "wumingjian_cup",
        "FA": "wumingjian_cup",
        "wumingjian": "wumingjian_cup",
        "wumingjian_cup": "wumingjian_cup",
        "无铭剑杯": "wumingjian_cup",
    }
    key = aliases.get(key, key)
    if key not in CUP_DEFINITIONS:
        raise HTTPException(status_code=404, detail="杯赛不存在")
    return key


def ensure_bracket(db: Session, competition: str) -> int:
    competition = normalize_competition(competition)
    created = 0
    for stage, _label, count in get_cup_stages(competition):
        existing_slots = {
            slot
            for (slot,) in db.query(CupMatch.slot_no)
            .filter(CupMatch.competition == competition, CupMatch.stage == stage)
            .all()
        }
        for slot_no in range(1, count + 1):
            if slot_no in existing_slots:
                continue
            db.add(
                CupMatch(
                    competition=competition,
                    stage=stage,
                    slot_no=slot_no,
                    status="scheduled",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            )
            created += 1
    if created:
        db.commit()
    return created


def get_bracket(db: Session, competition: str) -> CupBracketResponse:
    competition = normalize_competition(competition)
    ensure_bracket(db, competition)
    matches = (
        db.query(CupMatch)
        .filter(CupMatch.competition == competition)
        .order_by(CupMatch.stage, CupMatch.slot_no)
        .all()
    )
    matches_by_stage = {(match.stage, match.slot_no): match for match in matches}
    definition = CUP_DEFINITIONS[competition]
    stages: list[dict[str, Any]] = []
    for stage, label, count in get_cup_stages(competition):
        stages.append(
            {
                "key": stage,
                "label": label,
                "matches": [_cup_match_response(matches_by_stage[(stage, slot_no)]) for slot_no in range(1, count + 1)],
            }
        )
    return CupBracketResponse(
        competition=competition,
        title=definition["title"],
        trophy_url=definition["trophy_url"],
        stages=stages,
    )


def _visible_team(db: Session, team_id: int | None) -> Team | None:
    if team_id is None:
        return None
    team = get_team_by_id(db, team_id)
    if not team or team.level == VISIBLE_LEVEL:
        raise HTTPException(status_code=400, detail="请选择已有可见球队")
    return team


def _set_team(match: CupMatch, side: str, team: Team | None) -> None:
    setattr(match, f"{side}_team_id", team.id if team else None)
    setattr(match, f"{side}_team_name", team.name if team else None)


def _stage_index(competition: str, stage: str) -> int:
    stages = get_cup_stages(competition)
    for index, (key, _label, _count) in enumerate(stages):
        if key == stage:
            return index
    raise HTTPException(status_code=400, detail="杯赛阶段无效")


def _next_slot(match: CupMatch) -> tuple[str, int, str] | None:
    stages = get_cup_stages(match.competition)
    index = _stage_index(match.competition, match.stage)
    if index >= len(stages) - 1:
        return None
    next_stage = stages[index + 1][0]
    next_slot_no = (match.slot_no + 1) // 2
    side = "home" if match.slot_no % 2 == 1 else "away"
    return next_stage, next_slot_no, side


def _team_advancement(match: CupMatch, side: str) -> str:
    team_id = getattr(match, f"{side}_team_id")
    if match.status != "played" or not team_id or not match.winner_team_id:
        return "pending"
    return "winner" if int(team_id) == int(match.winner_team_id) else "eliminated"


def _cup_match_response(match: CupMatch) -> CupMatchResponse:
    return CupMatchResponse(
        id=match.id,
        competition=match.competition,
        stage=match.stage,
        slot_no=match.slot_no,
        home_team_id=match.home_team_id,
        home_team_name=match.home_team_name,
        away_team_id=match.away_team_id,
        away_team_name=match.away_team_name,
        home_score=match.home_score,
        away_score=match.away_score,
        winner_team_id=match.winner_team_id,
        winner_team_name=match.winner_team_name,
        home_advancement=_team_advancement(match, "home"),
        away_advancement=_team_advancement(match, "away"),
        status=match.status,
        notes=match.notes,
        updated_at=match.updated_at,
    )


def _clear_winner(match: CupMatch) -> None:
    match.winner_team_id = None
    match.winner_team_name = None
    match.status = "scheduled"


def _set_match_winner(match: CupMatch, winner_team_id: int) -> None:
    if int(winner_team_id) == int(match.home_team_id):
        match.winner_team_id = match.home_team_id
        match.winner_team_name = match.home_team_name
        return
    if int(winner_team_id) == int(match.away_team_id):
        match.winner_team_id = match.away_team_id
        match.winner_team_name = match.away_team_name
        return
    raise HTTPException(status_code=400, detail="晋级球队必须是本场对阵双方之一")


def _clear_downstream(db: Session, competition: str, stage: str, slot_no: int, side: str | None = None) -> None:
    match = (
        db.query(CupMatch)
        .filter(CupMatch.competition == competition, CupMatch.stage == stage, CupMatch.slot_no == slot_no)
        .first()
    )
    if not match:
        return
    if side:
        _set_team(match, side, None)
    match.home_score = None
    match.away_score = None
    _clear_winner(match)
    match.updated_at = datetime.now()
    next_target = _next_slot(match)
    if next_target:
        _clear_downstream(db, competition, *next_target)


def _propagate_winner(db: Session, match: CupMatch) -> None:
    next_target = _next_slot(match)
    if not next_target:
        return
    next_stage, next_slot_no, side = next_target
    next_match = (
        db.query(CupMatch)
        .filter(CupMatch.competition == match.competition, CupMatch.stage == next_stage, CupMatch.slot_no == next_slot_no)
        .first()
    )
    if not next_match:
        return
    old_team_id = getattr(next_match, f"{side}_team_id")
    if old_team_id != match.winner_team_id:
        _clear_downstream(db, match.competition, next_stage, next_slot_no, side)
    team = _visible_team(db, match.winner_team_id) if match.winner_team_id else None
    _set_team(next_match, side, team)
    next_match.updated_at = datetime.now()


def initialize_cup_bracket(
    db: Session,
    admin: str | None,
    competition: str,
    write_to_log: LogWriter,
    *,
    reset: bool = False,
) -> dict[str, Any]:
    operator = require_admin(admin)
    competition = normalize_competition(competition)
    created = ensure_bracket(db, competition)
    title = CUP_DEFINITIONS[competition]["title"]
    if not reset:
        write_to_log("杯赛初始化", f"{title} 初始化，新增 {created} 个槽位", operator)
        message = f"{title} 淘汰赛已初始化" if created else f"{title} 淘汰赛已存在，无需重复初始化"
        return {"success": True, "message": message}

    matches = db.query(CupMatch).filter(CupMatch.competition == competition).all()
    cleared = 0
    updated_at = datetime.now()
    for match in matches:
        if any(
            value is not None
            for value in (
                match.home_team_id,
                match.home_team_name,
                match.away_team_id,
                match.away_team_name,
                match.home_score,
                match.away_score,
                match.winner_team_id,
                match.winner_team_name,
                match.notes,
            )
        ) or match.status != "scheduled":
            cleared += 1
        match.home_team_id = None
        match.home_team_name = None
        match.away_team_id = None
        match.away_team_name = None
        match.home_score = None
        match.away_score = None
        match.winner_team_id = None
        match.winner_team_name = None
        match.status = "scheduled"
        match.notes = None
        match.updated_at = updated_at
    db.commit()
    write_to_log(
        "杯赛初始化",
        f"{title} 重新初始化，重置 {len(matches)} 个槽位，清除 {cleared} 个已有对阵",
        operator,
    )
    return {
        "success": True,
        "message": f"{title} 已重新初始化，共重置 {len(matches)} 个对阵槽位",
    }


def update_cup_match_teams(
    db: Session,
    admin: str | None,
    match_id: int,
    request: CupMatchTeamsUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    match = db.query(CupMatch).filter(CupMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="杯赛对阵不存在")
    if match.stage != get_first_stage(match.competition):
        raise HTTPException(status_code=400, detail="只能手动编辑杯赛首轮球队，后续轮次由晋级自动生成")
    home = _visible_team(db, request.home_team_id)
    away = _visible_team(db, request.away_team_id)
    if home and away and home.id == away.id:
        raise HTTPException(status_code=400, detail="同一场对阵不能选择相同球队")
    _set_team(match, "home", home)
    _set_team(match, "away", away)
    match.home_score = None
    match.away_score = None
    match.notes = str(request.notes or "").strip() or None
    _clear_winner(match)
    match.updated_at = datetime.now()
    next_target = _next_slot(match)
    if next_target:
        _clear_downstream(db, match.competition, *next_target)
    db.commit()
    write_to_log("杯赛球队编辑", f"{CUP_DEFINITIONS[match.competition]['title']} {match.stage} #{match.slot_no}", operator)
    return {"success": True, "message": "杯赛对阵球队已保存"}


def update_cup_match_result(
    db: Session,
    admin: str | None,
    match_id: int,
    request: CupMatchResultUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    match = db.query(CupMatch).filter(CupMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="杯赛对阵不存在")
    if not match.home_team_id or not match.away_team_id:
        raise HTTPException(status_code=400, detail="请先选择双方球队")
    status = str(request.status or "").strip().lower() or "scheduled"
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="比赛状态仅支持 scheduled 或 played")
    home_score = request.home_score
    away_score = request.away_score
    if status == "played":
        if home_score is None or away_score is None:
            raise HTTPException(status_code=400, detail="已赛比赛必须填写比分")
        if home_score < 0 or away_score < 0:
            raise HTTPException(status_code=400, detail="比分不能为负数")
        if home_score == away_score:
            if not request.winner_team_id:
                raise HTTPException(status_code=400, detail="总比分相同，请按客场进球规则选择晋级球队")
            _set_match_winner(match, int(request.winner_team_id))
        else:
            _set_match_winner(match, match.home_team_id if home_score > away_score else match.away_team_id)
    else:
        next_target = _next_slot(match)
        if next_target:
            _clear_downstream(db, match.competition, *next_target)
        _clear_winner(match)
    match.home_score = home_score
    match.away_score = away_score
    match.status = status
    notes = str(request.notes or "").strip()
    if status == "played" and home_score == away_score and not notes:
        notes = "总比分相同，按客场进球规则晋级"
    match.notes = notes or None
    match.updated_at = datetime.now()
    if status == "played":
        _propagate_winner(db, match)
    db.commit()
    write_to_log("杯赛比分编辑", f"{CUP_DEFINITIONS[match.competition]['title']} {match.stage} #{match.slot_no}", operator)
    return {"success": True, "message": "杯赛比分已保存"}


def list_cup_team_options(db: Session) -> list[dict[str, Any]]:
    return [
        {"id": team.id, "name": team.name, "manager": team.manager, "level": team.level}
        for team in sorted(list_visible_teams(db, VISIBLE_LEVEL), key=lambda item: (item.level, item.name))
    ]
