from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import io
import re
import secrets
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from auth_utils import hash_password, verify_password
from models import Coach, CoachAccount, CoachAssistant, CoachHonor, CoachReactionEvent, CoachReactionSummary, CoachSession, Team
from schemas_read import (
    CoachAccountAdminResponse,
    CoachAccountPublicResponse,
    CoachAssistantResponse,
    CoachDetailResponse,
    CoachHonorResponse,
    CoachListItemResponse,
    CoachesResponse,
    CoachReactionActionResponse,
    PlayerReactionSummaryResponse,
)
from schemas_write import (
    CoachAccountUpsertRequest,
    CoachAssistantUpdateRequest,
    CoachHonorUpdateRequest,
    CoachLoginRequest,
    CoachMergeRequest,
    CoachPasswordChangeRequest,
    CoachQqBindingRequest,
    CoachTeamAssignmentRequest,
    CoachUpdateRequest,
)
from services.admin_common import LogWriter, require_admin

LEAGUE_LEVELS = ["超级", "甲级", "乙级"]
REACTION_TYPES = {"flower", "egg"}
REACTION_COOLDOWN_SECONDS = 60
COACH_AVATAR_ROOT = Path("static") / "uploads" / "coaches"
MAX_AVATAR_BYTES = 2 * 1024 * 1024
MIN_AVATAR_DIMENSION = 240
MAX_AVATAR_DIMENSION = 2000
AVATAR_OUTPUT_SIZE = 512
ALLOWED_AVATAR_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
COACH_AVATAR_PUBLIC_PREFIX = "/static/uploads/coaches/"
COACH_SESSION_TTL = timedelta(days=14)
COACH_HONOR_COMPETITIONS = {"超级杯", "冠军杯", "联盟杯", "无铭剑杯", "足总杯", "联赛杯", "联机联赛联盟杯", "世界杯", "新人赛", "超级联赛", "甲级联赛", "乙级联赛"}
COACH_HONOR_PLACEMENTS = {"冠军", "亚军", "季军"}
COACH_TITLE_COLORS = {
    "white",
    "green",
    "blue",
    "purple",
    "orange",
    "red",
    "gold",
    "cyan",
    "pink",
    "emerald",
    "silver",
    "blackgold",
    "rainbow",
    "marquee",
    "pulse",
    "blink",
    "jump",
    "aurora",
}
COACH_ASSISTANT_LEVELS = {"全权助教", "正式助教", "实习助教"}


def _public_static_path_exists(path: str | None) -> bool:
    raw = str(path or "").strip()
    if not raw.startswith("/static/"):
        return False
    return Path(raw.lstrip("/")).exists()


def _safe_coach_avatar_path(path: str | None) -> str | None:
    raw = str(path or "").strip()
    return raw if _public_static_path_exists(raw) else None


def _validate_coach_username(username: str) -> str:
    normalized = re.sub(r"\s+", "", str(username or "").strip())
    if len(normalized) < 2 or len(normalized) > 40 or "/" in normalized or "\\" in normalized:
        raise HTTPException(status_code=400, detail="账号名需为 2-40 位，且不能包含空格或斜杠")
    return normalized


def _validate_coach_password(password: str) -> str:
    normalized = str(password or "").strip()
    if len(normalized) < 6 or len(normalized) > 80:
        raise HTTPException(status_code=400, detail="密码长度需为 6-80 位")
    return normalized


def _validate_qq_number(qq_number: str) -> str:
    normalized = re.sub(r"\s+", "", str(qq_number or ""))
    if not re.fullmatch(r"[1-9]\d{4,11}", normalized):
        raise HTTPException(status_code=400, detail="QQ号需为 5-12 位数字，且不能以 0 开头")
    return normalized


def _coach_uid_for_nickname(nickname: str) -> str:
    normalized = re.sub(r"\s+", " ", str(nickname or "").strip())
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"coach_{digest}"


def _team_sort_key(team: Team) -> tuple[int, str]:
    return (LEAGUE_LEVELS.index(team.level) if team.level in LEAGUE_LEVELS else 99, str(team.name or ""))


def _sync_coaches_from_teams(db: Session) -> int:
    teams = sorted(db.query(Team).filter(Team.level.in_(LEAGUE_LEVELS)).all(), key=_team_sort_key)
    created = 0
    now = datetime.now()
    active_uids: set[str] = set()
    for team in teams:
        nickname = str(team.manager or "").strip()
        if not nickname or nickname == "-":
            continue
        coach_uid = _coach_uid_for_nickname(nickname)
        active_uids.add(coach_uid)
        coach = db.query(Coach).filter(Coach.uid == coach_uid).first()
        if not coach:
            coach = Coach(uid=coach_uid, nickname=nickname, created_at=now)
            db.add(coach)
            created += 1
        coach.nickname = coach.nickname or nickname
        coach.team_id = team.id
        coach.team_name = team.name
        coach.level = team.level
        coach.updated_at = now
    stale_query = db.query(Coach).filter(Coach.level.in_(LEAGUE_LEVELS))
    if active_uids:
        stale_query = stale_query.filter(~Coach.uid.in_(active_uids))
    for coach in stale_query.all():
        coach.team_id = None
        coach.team_name = None
        coach.level = None
        coach.updated_at = now
    if created:
        db.commit()
    else:
        db.flush()
    return created


def refresh_coach_assignments(db: Session) -> int:
    created = _sync_coaches_from_teams(db)
    db.commit()
    return created


def sync_coaches_from_teams(db: Session, admin: str | None, write_to_log: LogWriter) -> dict[str, Any]:
    operator = require_admin(admin)
    created = refresh_coach_assignments(db)
    write_to_log("教练同步", f"从球队主教练字段同步，新增 {created} 名教练", operator)
    return {"success": True, "message": f"教练同步完成，新增 {created} 名"}


def assign_coach_team(
    db: Session,
    admin: str | None,
    coach_uid: str,
    request: CoachTeamAssignmentRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    coach = db.query(Coach).filter(Coach.uid == coach_uid).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")

    now = datetime.now()
    previous_team = db.query(Team).filter(Team.id == coach.team_id).first() if coach.team_id else None
    if request.team_id is None:
        if previous_team and str(previous_team.manager or "").strip() == coach.nickname:
            previous_team.manager = "-"
        coach.team_id = None
        coach.team_name = None
        coach.level = None
        coach.updated_at = now
        db.commit()
        write_to_log("教练球队关联", f"{coach.nickname} 已解除球队关联", operator)
        return {"success": True, "message": "已解除教练与球队的关联"}

    team = db.query(Team).filter(Team.id == request.team_id, Team.level.in_(LEAGUE_LEVELS)).first()
    if not team:
        raise HTTPException(status_code=404, detail="球队不存在或不在当前三级联赛")

    if previous_team and previous_team.id != team.id and str(previous_team.manager or "").strip() == coach.nickname:
        previous_team.manager = "-"
    for other in db.query(Coach).filter(Coach.team_id == team.id, Coach.uid != coach.uid).all():
        other.team_id = None
        other.team_name = None
        other.level = None
        other.updated_at = now
    team.manager = coach.nickname
    coach.team_id = team.id
    coach.team_name = team.name
    coach.level = team.level
    coach.updated_at = now
    db.commit()
    write_to_log("教练球队关联", f"{coach.nickname} -> {team.name}", operator)
    return {"success": True, "message": f"已将 {coach.nickname} 关联到 {team.name}"}


def merge_coach(
    db: Session,
    admin: str | None,
    source_coach_uid: str,
    request: CoachMergeRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    target_uid = str(request.target_coach_uid or "").strip()
    if not target_uid or target_uid == source_coach_uid:
        raise HTTPException(status_code=400, detail="请选择另一个教练作为合并目标")
    source = db.query(Coach).filter(Coach.uid == source_coach_uid).first()
    target = db.query(Coach).filter(Coach.uid == target_uid).first()
    if not source or not target:
        raise HTTPException(status_code=404, detail="来源教练或目标教练不存在")
    if source.team_id and target.team_id and source.team_id != target.team_id:
        raise HTTPException(status_code=400, detail="两个教练分别关联不同球队，请先确认球队归属")
    source_nickname = source.nickname
    target_nickname = target.nickname

    source_account = _get_coach_account(db, source.uid)
    target_account = _get_coach_account(db, target.uid)

    now = datetime.now()
    team_id = target.team_id or source.team_id
    if team_id:
        team = db.query(Team).filter(Team.id == team_id).first()
        if team:
            team.manager = target.nickname
            target.team_id = team.id
            target.team_name = team.name
            target.level = team.level
    for team in db.query(Team).filter(Team.manager == source.nickname).all():
        team.manager = target.nickname

    target.avatar_path = target.avatar_path or source.avatar_path
    target.title = target.title or source.title
    target.title_color = target.title_color or source.title_color
    target.bio = target.bio or source.bio
    if source.created_at and (not target.created_at or source.created_at < target.created_at):
        target.created_at = source.created_at
    target.updated_at = now

    db.query(CoachHonor).filter(CoachHonor.coach_uid == source.uid).update({CoachHonor.coach_uid: target.uid}, synchronize_session=False)
    db.query(CoachAssistant).filter(CoachAssistant.coach_uid == source.uid).update({CoachAssistant.coach_uid: target.uid}, synchronize_session=False)
    db.query(CoachReactionEvent).filter(CoachReactionEvent.coach_uid == source.uid).update({CoachReactionEvent.coach_uid: target.uid}, synchronize_session=False)

    source_summary = _get_reaction_summary(db, source.uid)
    target_summary = _get_reaction_summary(db, target.uid)
    if source_summary:
        if target_summary:
            target_summary.flowers += source_summary.flowers
            target_summary.eggs += source_summary.eggs
            target_summary.updated_at = now
            db.delete(source_summary)
        else:
            source_summary.coach_uid = target.uid
            source_summary.updated_at = now

    db.query(CoachSession).filter(CoachSession.coach_uid.in_([source.uid, target.uid])).delete(synchronize_session=False)
    if source_account:
        db.delete(source_account)

    kept_username = target_account.username if target_account else None
    db.flush()
    db.delete(source)
    db.commit()
    account_note = f"，保留登录账号 {kept_username}" if kept_username else ""
    write_to_log("教练合并", f"{source_nickname} -> {target_nickname}{account_note}", operator)
    return {"success": True, "message": f"已将 {source_nickname} 合并到 {target_nickname}{account_note}"}


def _remaining_cooldown_seconds(latest_reaction_at: datetime | None, now: datetime) -> int:
    if latest_reaction_at is None:
        return 0
    available_at = latest_reaction_at + timedelta(seconds=REACTION_COOLDOWN_SECONDS)
    return max(0, int((available_at - now).total_seconds()))


def _get_reaction_summary(db: Session, coach_uid: str) -> CoachReactionSummary | None:
    return db.query(CoachReactionSummary).filter(CoachReactionSummary.coach_uid == coach_uid).first()


def _ensure_reaction_summary(db: Session, coach_uid: str) -> CoachReactionSummary:
    summary = _get_reaction_summary(db, coach_uid)
    if summary:
        return summary
    summary = CoachReactionSummary(coach_uid=coach_uid, flowers=0, eggs=0)
    db.add(summary)
    db.flush()
    return summary


def _latest_reaction_for_visitor(db: Session, coach_uid: str, visitor_token: str) -> CoachReactionEvent | None:
    return (
        db.query(CoachReactionEvent)
        .filter(CoachReactionEvent.coach_uid == coach_uid, CoachReactionEvent.visitor_token == visitor_token)
        .order_by(CoachReactionEvent.created_at.desc(), CoachReactionEvent.id.desc())
        .first()
    )


def build_coach_reaction_summary(
    db: Session,
    coach_uid: str,
    visitor_token: str | None = None,
    now: datetime | None = None,
) -> PlayerReactionSummaryResponse:
    current_time = now or datetime.now()
    summary = _get_reaction_summary(db, coach_uid)
    latest = _latest_reaction_for_visitor(db, coach_uid, visitor_token) if visitor_token else None
    cooldown_seconds = _remaining_cooldown_seconds(latest.created_at if latest else None, current_time)
    return PlayerReactionSummaryResponse(
        flowers=summary.flowers if summary else 0,
        eggs=summary.eggs if summary else 0,
        can_react=cooldown_seconds == 0,
        cooldown_seconds=cooldown_seconds,
        next_available_at=latest.created_at + timedelta(seconds=REACTION_COOLDOWN_SECONDS) if latest and cooldown_seconds > 0 else None,
    )


def _coach_list_item(db: Session, coach: Coach, visitor_token: str | None = None) -> CoachListItemResponse:
    return CoachListItemResponse(
        uid=coach.uid,
        nickname=coach.nickname,
        team_id=coach.team_id,
        team_name=coach.team_name,
        level=coach.level,
        avatar_path=_safe_coach_avatar_path(coach.avatar_path),
        title=coach.title,
        title_color=coach.title_color or "white",
        bio=coach.bio,
        reaction_summary=build_coach_reaction_summary(db, coach.uid, visitor_token=visitor_token),
    )


def get_coaches(db: Session, visitor_token: str | None = None) -> CoachesResponse:
    refresh_coach_assignments(db)
    coaches = (
        db.query(Coach)
        .filter(Coach.level.in_(LEAGUE_LEVELS))
        .order_by(Coach.level, Coach.team_name, Coach.nickname)
        .all()
    )
    coaches = sorted(coaches, key=lambda item: (_team_sort_key(Team(name=item.team_name, level=item.level)), item.nickname))
    return CoachesResponse(
        levels=LEAGUE_LEVELS,
        coaches=[_coach_list_item(db, coach, visitor_token=visitor_token) for coach in coaches],
    )


def get_coach_detail(db: Session, coach_uid: str, visitor_token: str | None = None) -> CoachDetailResponse:
    refresh_coach_assignments(db)
    coach = db.query(Coach).filter(Coach.uid == coach_uid).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")
    honors = (
        db.query(CoachHonor)
        .filter(CoachHonor.coach_uid == coach.uid)
        .order_by(
            case((CoachHonor.edition.is_(None), 1), else_=0).asc(),
            CoachHonor.edition.asc(),
            CoachHonor.sort_order.asc(),
            CoachHonor.id.asc(),
        )
        .all()
    )
    assistants = (
        db.query(CoachAssistant)
        .filter(CoachAssistant.coach_uid == coach.uid)
        .order_by(CoachAssistant.sort_order.asc(), CoachAssistant.id.asc())
        .all()
    )
    base = _coach_list_item(db, coach, visitor_token=visitor_token)
    return CoachDetailResponse(
        **base.model_dump(),
        honors=[CoachHonorResponse.model_validate(honor) for honor in honors],
        assistants=[CoachAssistantResponse.model_validate(assistant) for assistant in assistants],
        updated_at=coach.updated_at,
    )


def _get_coach_account(db: Session, coach_uid: str) -> CoachAccount | None:
    return db.query(CoachAccount).filter(CoachAccount.coach_uid == coach_uid).first()


def _coach_account_work_permissions(account: CoachAccount | None) -> dict[str, bool]:
    return {
        "can_manage_schedule": bool(getattr(account, "can_manage_schedule", 0)) if account else False,
        "can_manage_cup_standings": bool(getattr(account, "can_manage_cup_standings", 0)) if account else False,
        "can_manage_rankings": bool(getattr(account, "can_manage_rankings", 0)) if account else False,
        "can_manage_suspensions": bool(getattr(account, "can_manage_suspensions", 0)) if account else False,
        "can_manage_candidate_lists": bool(getattr(account, "can_manage_candidate_lists", 0)) if account else False,
    }


def get_coach_account_admin_status(db: Session, admin: str | None, coach_uid: str) -> CoachAccountAdminResponse:
    require_admin(admin)
    account = _get_coach_account(db, coach_uid)
    if not account:
        return CoachAccountAdminResponse()
    return CoachAccountAdminResponse(
        exists=True,
        username=account.username,
        qq_number=account.qq_number,
        is_active=bool(account.is_active),
        must_change_password=bool(account.must_change_password),
        **_coach_account_work_permissions(account),
        last_login_at=account.last_login_at,
    )


def upsert_coach_account(
    db: Session,
    admin: str | None,
    coach_uid: str,
    request: CoachAccountUpsertRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    coach = db.query(Coach).filter(Coach.uid == coach_uid).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")
    username = _validate_coach_username(request.username)
    existing_username = db.query(CoachAccount).filter(CoachAccount.username == username).first()
    if existing_username and existing_username.coach_uid != coach_uid:
        raise HTTPException(status_code=400, detail="账号名已被其他教练使用")
    qq_collision = db.query(CoachAccount).filter(CoachAccount.qq_number == username, CoachAccount.coach_uid != coach_uid).first()
    if qq_collision:
        raise HTTPException(status_code=400, detail="该账号名已被其他教练绑定为 QQ 号")
    now = datetime.now()
    account = _get_coach_account(db, coach_uid)
    if not account:
        password = _validate_coach_password(request.password or "")
        account = CoachAccount(coach_uid=coach_uid, created_at=now)
        db.add(account)
        account.password_hash = hash_password(password)
        account.must_change_password = 1
    elif str(request.password or "").strip():
        password = _validate_coach_password(request.password or "")
        account.password_hash = hash_password(password)
        account.must_change_password = 1
    account.username = username
    account.is_active = 1 if request.is_active else 0
    account.can_manage_schedule = 1 if request.can_manage_schedule else 0
    account.can_manage_cup_standings = 1 if request.can_manage_cup_standings else 0
    account.can_manage_rankings = 1 if request.can_manage_rankings else 0
    account.can_manage_suspensions = 1 if request.can_manage_suspensions else 0
    account.can_manage_candidate_lists = 1 if request.can_manage_candidate_lists else 0
    account.updated_at = now
    db.query(CoachSession).filter(CoachSession.coach_uid == coach_uid).delete()
    db.commit()
    write_to_log("教练账号维护", f"{coach.uid} / {coach.nickname} / {username}", operator)
    return {"success": True, "message": "教练账号已保存"}


def _cleanup_expired_coach_sessions(db: Session) -> None:
    db.query(CoachSession).filter(CoachSession.expires_at <= datetime.now()).delete()
    db.flush()


def create_coach_session(db: Session, account: CoachAccount) -> str:
    token = secrets.token_hex(32)
    now = datetime.now()
    db.add(
        CoachSession(
            token=token,
            coach_uid=account.coach_uid,
            username=account.username,
            created_at=now,
            expires_at=now + COACH_SESSION_TTL,
        )
    )
    account.last_login_at = now
    db.flush()
    return token


def delete_coach_session(db: Session, session_token: str | None) -> None:
    if not session_token:
        return
    db.query(CoachSession).filter(CoachSession.token == session_token).delete()
    db.flush()


def get_coach_session_identity(db: Session, session_token: str | None) -> CoachAccountPublicResponse:
    if not session_token:
        return CoachAccountPublicResponse(authenticated=False)
    _cleanup_expired_coach_sessions(db)
    session = db.query(CoachSession).filter(CoachSession.token == session_token).first()
    if not session:
        return CoachAccountPublicResponse(authenticated=False)
    account = db.query(CoachAccount).filter(CoachAccount.coach_uid == session.coach_uid).first()
    coach = db.query(Coach).filter(Coach.uid == session.coach_uid).first()
    if not account or not coach or not account.is_active:
        return CoachAccountPublicResponse(authenticated=False)
    return CoachAccountPublicResponse(
        authenticated=True,
        coach_uid=coach.uid,
        username=account.username,
        qq_number=account.qq_number,
        nickname=coach.nickname,
        avatar_path=_safe_coach_avatar_path(coach.avatar_path),
        level=coach.level,
        team_id=coach.team_id,
        team_name=coach.team_name,
        must_change_password=bool(account.must_change_password),
        **_coach_account_work_permissions(account),
    )


def login_coach(db: Session, request: CoachLoginRequest) -> tuple[str, CoachAccountPublicResponse]:
    username = re.sub(r"\s+", "", str(request.username or ""))
    password = str(request.password or "")
    account = (
        db.query(CoachAccount)
        .filter(or_(CoachAccount.qq_number == username, CoachAccount.username == username))
        .order_by(case((CoachAccount.qq_number == username, 0), else_=1))
        .first()
    )
    if not account or not account.is_active or not verify_password(password, account.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    coach = db.query(Coach).filter(Coach.uid == account.coach_uid).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")
    _cleanup_expired_coach_sessions(db)
    token = create_coach_session(db, account)
    db.commit()
    return token, CoachAccountPublicResponse(
        authenticated=True,
        coach_uid=coach.uid,
        username=account.username,
        qq_number=account.qq_number,
        nickname=coach.nickname,
        avatar_path=_safe_coach_avatar_path(coach.avatar_path),
        level=coach.level,
        team_id=coach.team_id,
        team_name=coach.team_name,
        must_change_password=bool(account.must_change_password),
        **_coach_account_work_permissions(account),
    )


def logout_coach(db: Session, session_token: str | None) -> dict[str, bool]:
    delete_coach_session(db, session_token)
    db.commit()
    return {"success": True}


def change_own_coach_password(
    db: Session,
    session_token: str | None,
    request: CoachPasswordChangeRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    coach = _require_coach_owner(db, session_token, allow_password_change=True)
    account = db.query(CoachAccount).filter(CoachAccount.coach_uid == coach.uid).first()
    if not account or not account.is_active:
        raise HTTPException(status_code=401, detail="教练账号不可用")
    if not verify_password(str(request.current_password or ""), account.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    new_password = _validate_coach_password(request.new_password)
    if verify_password(new_password, account.password_hash):
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    account.password_hash = hash_password(new_password)
    account.must_change_password = 0
    account.updated_at = datetime.now()
    db.query(CoachSession).filter(CoachSession.coach_uid == coach.uid, CoachSession.token != session_token).delete()
    db.commit()
    write_to_log("教练密码修改", f"{coach.uid} / {coach.nickname}", f"coach:{coach.nickname}")
    return {"success": True, "message": "密码已修改"}


def bind_own_coach_qq(
    db: Session,
    session_token: str | None,
    request: CoachQqBindingRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    coach = _require_coach_owner(db, session_token, allow_qq_binding=True)
    account = _get_coach_account(db, coach.uid)
    if not account or not account.is_active:
        raise HTTPException(status_code=401, detail="教练账号不可用")
    if not verify_password(str(request.current_password or ""), account.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    qq_number = _validate_qq_number(request.qq_number)
    existing = db.query(CoachAccount).filter(CoachAccount.qq_number == qq_number, CoachAccount.coach_uid != coach.uid).first()
    if existing:
        raise HTTPException(status_code=400, detail="该 QQ 号已绑定其他教练")
    username_collision = db.query(CoachAccount).filter(CoachAccount.username == qq_number, CoachAccount.coach_uid != coach.uid).first()
    if username_collision:
        raise HTTPException(status_code=400, detail="该 QQ 号与其他教练的旧账号名冲突")
    account.qq_number = qq_number
    account.updated_at = datetime.now()
    db.query(CoachSession).filter(CoachSession.coach_uid == coach.uid, CoachSession.token != session_token).delete()
    db.commit()
    write_to_log("教练 QQ 绑定", f"{coach.uid} / {coach.nickname} / {qq_number}", f"coach:{coach.nickname}")
    return {"success": True, "message": "QQ 号已绑定，以后可直接使用 QQ 号登录"}


def unbind_coach_qq(
    db: Session,
    admin: str | None,
    coach_uid: str,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    coach = db.query(Coach).filter(Coach.uid == coach_uid).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")
    account = _get_coach_account(db, coach_uid)
    if not account or not account.qq_number:
        return {"success": True, "message": "该教练没有绑定 QQ 号"}
    previous_qq = account.qq_number
    account.qq_number = None
    account.updated_at = datetime.now()
    db.query(CoachSession).filter(CoachSession.coach_uid == coach_uid).delete()
    db.commit()
    write_to_log("教练 QQ 解绑", f"{coach.uid} / {coach.nickname} / {previous_qq}", operator)
    return {"success": True, "message": "QQ 号已解绑，相关登录会话已退出"}


def _require_coach_owner(
    db: Session,
    session_token: str | None,
    coach_uid: str | None = None,
    *,
    allow_password_change: bool = False,
    allow_qq_binding: bool = False,
) -> Coach:
    identity = get_coach_session_identity(db, session_token)
    if not identity.authenticated or not identity.coach_uid:
        raise HTTPException(status_code=401, detail="请先登录教练账号")
    if coach_uid and identity.coach_uid != coach_uid:
        raise HTTPException(status_code=403, detail="只能维护自己的教练主页")
    if identity.must_change_password and not allow_password_change:
        raise HTTPException(status_code=403, detail="首次登录必须先修改默认密码")
    if not identity.qq_number and not (allow_password_change or allow_qq_binding):
        raise HTTPException(status_code=403, detail="请先绑定 QQ 号后再使用教练功能")
    coach = db.query(Coach).filter(Coach.uid == identity.coach_uid).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")
    return coach


def update_coach_profile(
    db: Session,
    admin: str | None,
    coach_uid: str,
    request: CoachUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    return _update_coach_profile_for_operator(db, operator, coach_uid, request, write_to_log, allow_nickname=True, allow_title_color=True)


def update_own_coach_profile(
    db: Session,
    session_token: str | None,
    request: CoachUpdateRequest,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    coach = _require_coach_owner(db, session_token)
    return _update_coach_profile_for_operator(db, f"coach:{coach.nickname}", coach.uid, request, write_to_log, allow_nickname=False, allow_title_color=True)


def _update_coach_profile_for_operator(
    db: Session,
    operator: str,
    coach_uid: str,
    request: CoachUpdateRequest,
    write_to_log: LogWriter,
    *,
    allow_nickname: bool,
    allow_title_color: bool,
) -> dict[str, Any]:
    coach = db.query(Coach).filter(Coach.uid == coach_uid).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")
    nickname = str(request.nickname or "").strip()
    if allow_nickname and nickname:
        previous_nickname = coach.nickname
        coach.nickname = nickname[:80]
        if coach.team_id:
            team = db.query(Team).filter(Team.id == coach.team_id).first()
            if team and str(team.manager or "").strip() == previous_nickname:
                team.manager = coach.nickname
    coach.title = str(request.title or "").strip()[:80] or None
    if allow_title_color:
        title_color = str(request.title_color or "white").strip().lower()
        if title_color not in COACH_TITLE_COLORS:
            raise HTTPException(status_code=400, detail="称号样式无效")
        coach.title_color = title_color
    elif not coach.title_color:
        coach.title_color = "white"
    coach.bio = str(request.bio or "").strip()[:2000] or None
    coach.updated_at = datetime.now()
    db.commit()
    write_to_log("教练资料更新", f"{coach.uid} / {coach.nickname}", operator)
    return {"success": True, "message": "教练资料已保存"}


def save_coach_avatar(
    db: Session,
    admin: str | None,
    coach_uid: str,
    avatar: UploadFile,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    operator = require_admin(admin)
    return _save_coach_avatar_for_operator(db, operator, coach_uid, avatar, write_to_log)


def save_own_coach_avatar(
    db: Session,
    session_token: str | None,
    avatar: UploadFile,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    coach = _require_coach_owner(db, session_token)
    return _save_coach_avatar_for_operator(db, f"coach:{coach.nickname}", coach.uid, avatar, write_to_log)


def _save_coach_avatar_for_operator(
    db: Session,
    operator: str,
    coach_uid: str,
    avatar: UploadFile,
    write_to_log: LogWriter,
) -> dict[str, Any]:
    coach = db.query(Coach).filter(Coach.uid == coach_uid).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")
    previous_avatar_path = coach.avatar_path
    if str(avatar.content_type or "").lower() not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=400, detail="头像仅支持 JPG、PNG、WEBP")
    content = avatar.file.read(MAX_AVATAR_BYTES + 1)
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=400, detail="头像不能超过 2MB")
    try:
        from PIL import Image, ImageOps
        image = Image.open(io.BytesIO(content))
        image.verify()
        image = Image.open(io.BytesIO(content))
        image = ImageOps.exif_transpose(image).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="头像文件无法识别") from exc
    width, height = image.size
    if min(width, height) < MIN_AVATAR_DIMENSION:
        raise HTTPException(status_code=400, detail=f"头像尺寸至少 {MIN_AVATAR_DIMENSION}x{MIN_AVATAR_DIMENSION}")
    if max(width, height) > MAX_AVATAR_DIMENSION:
        raise HTTPException(status_code=400, detail=f"头像最长边不能超过 {MAX_AVATAR_DIMENSION}px")
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side)).resize((AVATAR_OUTPUT_SIZE, AVATAR_OUTPUT_SIZE))
    COACH_AVATAR_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"{coach.uid}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.webp"
    target = COACH_AVATAR_ROOT / filename
    image.save(target, format="WEBP", quality=88, method=6)
    coach.avatar_path = f"{COACH_AVATAR_PUBLIC_PREFIX}{filename}"
    coach.updated_at = datetime.now()
    db.commit()
    _delete_previous_coach_avatar(coach.uid, previous_avatar_path, keep_path=coach.avatar_path)
    write_to_log("教练头像更新", f"{coach.uid} / {coach.nickname}", operator)
    return {"success": True, "message": "头像已上传", "avatar_path": coach.avatar_path}


def _delete_previous_coach_avatar(coach_uid: str, previous_avatar_path: str | None, keep_path: str | None = None) -> None:
    if not previous_avatar_path or previous_avatar_path == keep_path:
        return
    if not previous_avatar_path.startswith(COACH_AVATAR_PUBLIC_PREFIX):
        return
    filename = previous_avatar_path.removeprefix(COACH_AVATAR_PUBLIC_PREFIX)
    if not filename.startswith(f"{coach_uid}_"):
        return
    target = (COACH_AVATAR_ROOT / filename).resolve()
    root = COACH_AVATAR_ROOT.resolve()
    if root not in target.parents:
        return
    try:
        target.unlink(missing_ok=True)
    except OSError:
        pass


def upsert_coach_honor(
    db: Session,
    admin: str | None,
    request: CoachHonorUpdateRequest,
    write_to_log: LogWriter,
    honor_id: int | None = None,
) -> dict[str, Any]:
    operator = require_admin(admin)
    return _upsert_coach_honor_for_operator(db, operator, request, write_to_log, honor_id=honor_id)


def upsert_own_coach_honor(
    db: Session,
    session_token: str | None,
    request: CoachHonorUpdateRequest,
    write_to_log: LogWriter,
    honor_id: int | None = None,
) -> dict[str, Any]:
    coach = _require_coach_owner(db, session_token)
    request.coach_uid = coach.uid
    return _upsert_coach_honor_for_operator(db, f"coach:{coach.nickname}", request, write_to_log, honor_id=honor_id, owner_uid=coach.uid)


def _normalize_honor_payload(request: CoachHonorUpdateRequest) -> tuple[int | None, str, str, str, str | None, int]:
    edition = request.edition
    if edition is not None:
        try:
            edition = int(edition)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="届数必须是数字") from exc
        if edition < 1 or edition > 999:
            raise HTTPException(status_code=400, detail="届数范围需为 1-999")
    competition = str(request.competition or "").strip()
    placement = str(request.placement or request.honor or "").strip()
    if competition not in COACH_HONOR_COMPETITIONS:
        raise HTTPException(status_code=400, detail="赛事名称不在可选范围内")
    if placement not in COACH_HONOR_PLACEMENTS:
        raise HTTPException(status_code=400, detail="名次只能选择冠军、亚军或季军")
    season = str(request.season or "").strip()[:40] or (f"第{edition}届" if edition else None)
    description = str(request.description or "").strip()[:500] or None
    sort_order = int(request.sort_order or 0)
    return edition, season, competition, placement, description, sort_order


def _upsert_coach_honor_for_operator(
    db: Session,
    operator: str,
    request: CoachHonorUpdateRequest,
    write_to_log: LogWriter,
    honor_id: int | None = None,
    owner_uid: str | None = None,
) -> dict[str, Any]:
    coach_uid = str(request.coach_uid or "").strip()
    honor = db.query(CoachHonor).filter(CoachHonor.id == honor_id).first() if honor_id else None
    if honor_id and not honor:
        raise HTTPException(status_code=404, detail="荣誉记录不存在")
    if honor:
        coach_uid = honor.coach_uid
    if owner_uid and coach_uid != owner_uid:
        raise HTTPException(status_code=403, detail="只能维护自己的荣誉")
    if not coach_uid:
        raise HTTPException(status_code=400, detail="缺少教练 UID")
    coach = db.query(Coach).filter(Coach.uid == coach_uid).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")
    edition, season, competition, placement, description, sort_order = _normalize_honor_payload(request)
    if not honor:
        honor = CoachHonor(coach_uid=coach_uid, created_at=datetime.now())
        db.add(honor)
    honor.edition = edition
    honor.season = season
    honor.competition = competition
    honor.placement = placement
    honor.honor = placement
    honor.description = description
    honor.sort_order = sort_order
    honor.updated_at = datetime.now()
    db.commit()
    write_to_log("教练荣誉维护", f"{coach.uid} / {honor.honor}", operator)
    return {"success": True, "message": "教练荣誉已保存"}


def delete_coach_honor(db: Session, admin: str | None, honor_id: int, write_to_log: LogWriter) -> dict[str, Any]:
    operator = require_admin(admin)
    return _delete_coach_honor_for_operator(db, operator, honor_id, write_to_log)


def delete_own_coach_honor(db: Session, session_token: str | None, honor_id: int, write_to_log: LogWriter) -> dict[str, Any]:
    coach = _require_coach_owner(db, session_token)
    return _delete_coach_honor_for_operator(db, f"coach:{coach.nickname}", honor_id, write_to_log, owner_uid=coach.uid)


def _delete_coach_honor_for_operator(
    db: Session,
    operator: str,
    honor_id: int,
    write_to_log: LogWriter,
    owner_uid: str | None = None,
) -> dict[str, Any]:
    honor = db.query(CoachHonor).filter(CoachHonor.id == honor_id).first()
    if not honor:
        raise HTTPException(status_code=404, detail="荣誉记录不存在")
    if owner_uid and honor.coach_uid != owner_uid:
        raise HTTPException(status_code=403, detail="只能删除自己的荣誉")
    label = honor.honor
    db.delete(honor)
    db.commit()
    write_to_log("教练荣誉删除", label, operator)
    return {"success": True, "message": "教练荣誉已删除"}


def upsert_coach_assistant(
    db: Session,
    admin: str | None,
    request: CoachAssistantUpdateRequest,
    write_to_log: LogWriter,
    assistant_id: int | None = None,
) -> dict[str, Any]:
    operator = require_admin(admin)
    return _upsert_coach_assistant_for_operator(db, operator, request, write_to_log, assistant_id=assistant_id)


def upsert_own_coach_assistant(
    db: Session,
    session_token: str | None,
    request: CoachAssistantUpdateRequest,
    write_to_log: LogWriter,
    assistant_id: int | None = None,
) -> dict[str, Any]:
    coach = _require_coach_owner(db, session_token)
    request.coach_uid = coach.uid
    return _upsert_coach_assistant_for_operator(db, f"coach:{coach.nickname}", request, write_to_log, assistant_id=assistant_id, owner_uid=coach.uid)


def _normalize_assistant_payload(request: CoachAssistantUpdateRequest) -> tuple[str, str, str | None, int]:
    name = str(request.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="助教姓名不能为空")
    if len(name) > 80:
        raise HTTPException(status_code=400, detail="助教姓名不能超过 80 字")
    level = str(request.level or "").strip()
    if level not in COACH_ASSISTANT_LEVELS:
        raise HTTPException(status_code=400, detail="助教级别只能选择全权助教、正式助教或实习助教")
    note = str(request.note or "").strip()[:300] or None
    sort_order = int(request.sort_order or 0)
    return name, level, note, sort_order


def _upsert_coach_assistant_for_operator(
    db: Session,
    operator: str,
    request: CoachAssistantUpdateRequest,
    write_to_log: LogWriter,
    assistant_id: int | None = None,
    owner_uid: str | None = None,
) -> dict[str, Any]:
    coach_uid = str(request.coach_uid or "").strip()
    assistant = db.query(CoachAssistant).filter(CoachAssistant.id == assistant_id).first() if assistant_id else None
    if assistant_id and not assistant:
        raise HTTPException(status_code=404, detail="助教记录不存在")
    if assistant:
        coach_uid = assistant.coach_uid
    if owner_uid and coach_uid != owner_uid:
        raise HTTPException(status_code=403, detail="只能维护自己的助教团队")
    if not coach_uid:
        raise HTTPException(status_code=400, detail="缺少教练 UID")
    coach = db.query(Coach).filter(Coach.uid == coach_uid).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")
    name, level, note, sort_order = _normalize_assistant_payload(request)
    if not assistant:
        assistant = CoachAssistant(coach_uid=coach_uid, created_at=datetime.now())
        db.add(assistant)
    assistant.name = name
    assistant.level = level
    assistant.note = note
    assistant.sort_order = sort_order
    assistant.updated_at = datetime.now()
    db.commit()
    write_to_log("教练助教维护", f"{coach.uid} / {assistant.name} / {assistant.level}", operator)
    return {"success": True, "message": "助教团队已保存"}


def delete_coach_assistant(db: Session, admin: str | None, assistant_id: int, write_to_log: LogWriter) -> dict[str, Any]:
    operator = require_admin(admin)
    return _delete_coach_assistant_for_operator(db, operator, assistant_id, write_to_log)


def delete_own_coach_assistant(db: Session, session_token: str | None, assistant_id: int, write_to_log: LogWriter) -> dict[str, Any]:
    coach = _require_coach_owner(db, session_token)
    return _delete_coach_assistant_for_operator(db, f"coach:{coach.nickname}", assistant_id, write_to_log, owner_uid=coach.uid)


def _delete_coach_assistant_for_operator(
    db: Session,
    operator: str,
    assistant_id: int,
    write_to_log: LogWriter,
    owner_uid: str | None = None,
) -> dict[str, Any]:
    assistant = db.query(CoachAssistant).filter(CoachAssistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="助教记录不存在")
    if owner_uid and assistant.coach_uid != owner_uid:
        raise HTTPException(status_code=403, detail="只能删除自己的助教")
    label = f"{assistant.name} / {assistant.level}"
    db.delete(assistant)
    db.commit()
    write_to_log("教练助教删除", label, operator)
    return {"success": True, "message": "助教已删除"}


def record_coach_reaction(
    db: Session,
    coach_uid: str,
    visitor_token: str,
    reaction_type: str,
    now: datetime | None = None,
) -> CoachReactionActionResponse:
    if reaction_type not in REACTION_TYPES:
        raise HTTPException(status_code=400, detail="不支持的互动类型。")
    coach = db.query(Coach).filter(Coach.uid == coach_uid).first()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")
    current_time = now or datetime.now()
    latest = _latest_reaction_for_visitor(db, coach_uid, visitor_token)
    cooldown_seconds = _remaining_cooldown_seconds(latest.created_at if latest else None, current_time)
    if cooldown_seconds > 0:
        return CoachReactionActionResponse(
            accepted=False,
            reaction_type=reaction_type,
            message=f"请等待 {cooldown_seconds} 秒后再互动。",
            summary=build_coach_reaction_summary(db, coach_uid, visitor_token=visitor_token, now=current_time),
        )
    summary = _ensure_reaction_summary(db, coach_uid)
    if reaction_type == "flower":
        summary.flowers += 1
        message = "送花成功。"
    else:
        summary.eggs += 1
        message = "踩鸡蛋成功。"
    summary.updated_at = current_time
    db.add(CoachReactionEvent(coach_uid=coach_uid, visitor_token=visitor_token, reaction_type=reaction_type, created_at=current_time))
    db.commit()
    return CoachReactionActionResponse(
        accepted=True,
        reaction_type=reaction_type,
        message=message,
        summary=build_coach_reaction_summary(db, coach_uid, visitor_token=visitor_token, now=current_time),
    )
