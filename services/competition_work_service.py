from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import (
    AdminUser,
    Coach,
    CoachAccount,
    CompetitionResponsibilityAssignment,
    CompetitionRoundWorkLog,
    CompetitionRoundWorkState,
    Match,
    MatchPlayerEvent,
    PlayerSuspensionRecord,
)
from schemas_read import (
    CompetitionWorkLogResponse,
    CompetitionRoundWorkSummaryResponse,
    CompetitionWorkSummaryResponse,
    CompetitionWorkTaskResponse,
    WorkspaceIdentityResponse,
)
from services import auth_service
from services.operation_audit_service import AUDIT_SOURCE_ADMIN_UI, persist_admin_operation_audit


LEAGUE_LEVELS = ("超级", "甲级", "乙级")
FORFEIT_STATUSES = {"home_forfeit", "away_forfeit", "double_forfeit"}
NON_EVENT_RESOLVED_STATUSES = {"postponed", "cancelled", *FORFEIT_STATUSES}
WORKFLOW_STATUS_LABELS = {
    "unassigned": "待任命",
    "in_progress": "处理中",
    "pending_review": "待复核",
    "completed": "已完成",
}
WORK_LOG_ACTION_LABELS = {
    "assign": "分配负责人",
    "unassign": "取消分配",
    "submit": "提交复核",
    "review_approve": "复核通过",
    "review_reject": "退回修改",
    "confirm_suspensions": "确认伤停",
    "reopen_suspensions": "取消伤停确认",
    "assign_schedule_responsibility": "任命赛程与事件负责人",
    "assign_suspension_responsibility": "任命伤停负责人",
}
RESPONSIBILITY_TYPES = {"schedule", "suspensions"}


def get_round_pair_start(round_no: int | None) -> int:
    numeric_round = int(round_no or 0)
    if numeric_round <= 0:
        return 0
    return numeric_round if numeric_round % 2 == 1 else numeric_round - 1


def _round_label(round_start: int, round_end: int) -> str:
    return f"第 {round_start}-{round_end} 轮" if round_end != round_start else f"第 {round_start} 轮"


def _operator(identity: WorkspaceIdentityResponse) -> str:
    return identity.username if identity.source == "admin_account" else identity.principal_id


def _workflow_status(
    state: CompetitionRoundWorkState | None,
    *,
    has_schedule_owner: bool,
    completion_ready: bool,
    changed_after_submission: bool,
    completed: bool,
) -> str:
    if completed:
        return "completed"
    if state and state.submitted_at and completion_ready and not changed_after_submission:
        return "pending_review"
    if has_schedule_owner:
        return "in_progress"
    return "unassigned"


def _append_work_log(
    db: Session,
    state: CompetitionRoundWorkState,
    identity: WorkspaceIdentityResponse,
    *,
    action: str,
    from_status: str,
    to_status: str,
    detail: str = "",
) -> None:
    db.add(
        CompetitionRoundWorkLog(
            state_id=state.id,
            level=state.level,
            round_start=state.round_start,
            action=action,
            operator_principal_id=identity.principal_id,
            operator_display_name=identity.display_name,
            from_status=from_status,
            to_status=to_status,
            detail=detail or None,
            created_at=datetime.now(),
        )
    )


def _resolve_assignable_principal(
    db: Session,
    principal_id: str,
    responsibility_type: str = "schedule",
) -> tuple[str, str]:
    normalized = str(principal_id or "").strip()
    if normalized.startswith("admin:"):
        username = normalized.split(":", 1)[1]
        account = db.query(AdminUser).filter(AdminUser.username == username).first()
        role = auth_service.normalize_admin_role(account.role) if account else None
        allowed = (
            auth_service.can_manage_schedule(role)
            if responsibility_type == "schedule"
            else auth_service.can_manage_suspensions(role)
        )
        if account and allowed:
            return normalized, account.username
    if normalized.startswith("coach:"):
        username = normalized.split(":", 1)[1]
        row = (
            db.query(CoachAccount, Coach)
            .join(Coach, Coach.uid == CoachAccount.coach_uid)
            .filter(CoachAccount.username == username)
            .first()
        )
        permission_field = "can_manage_schedule" if responsibility_type == "schedule" else "can_manage_suspensions"
        if row and row[0].is_active and bool(getattr(row[0], permission_field, 0)):
            return normalized, row[1].nickname or row[0].username
    raise HTTPException(status_code=400, detail="负责人账号不存在、未启用或没有比赛维护权限")


def _responsibility_for(
    db: Session,
    level: str,
    responsibility_type: str,
) -> CompetitionResponsibilityAssignment | None:
    return (
        db.query(CompetitionResponsibilityAssignment)
        .filter(
            CompetitionResponsibilityAssignment.level == level,
            CompetitionResponsibilityAssignment.responsibility_type == responsibility_type,
        )
        .first()
    )


def identity_has_level_responsibility(
    identity: WorkspaceIdentityResponse,
    assignment: CompetitionResponsibilityAssignment | None,
) -> bool:
    return bool(identity.is_full_admin or (assignment and assignment.principal_id == identity.principal_id))


def operator_can_manage_level(
    db: Session,
    operator: str,
    level: str,
    responsibility_type: str,
) -> bool:
    principal_id = operator if str(operator).startswith("coach:") else f"admin:{operator}"
    if principal_id.startswith("admin:"):
        username = principal_id.split(":", 1)[1]
        admin = db.query(AdminUser).filter(AdminUser.username == username).first()
        if admin and auth_service.can_manage_admin(auth_service.normalize_admin_role(admin.role)):
            return True
    assignment = _responsibility_for(db, level, responsibility_type)
    return bool(assignment and assignment.principal_id == principal_id)


def _state_for_pair(db: Session, level: str, round_start: int) -> CompetitionRoundWorkState | None:
    return (
        db.query(CompetitionRoundWorkState)
        .filter(
            CompetitionRoundWorkState.level == level,
            CompetitionRoundWorkState.round_start == round_start,
        )
        .first()
    )


def _get_or_create_state(db: Session, level: str, round_start: int) -> CompetitionRoundWorkState:
    state = _state_for_pair(db, level, round_start)
    if state:
        return state
    state = CompetitionRoundWorkState(
        level=level,
        round_start=round_start,
        round_end=round_start + 1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(state)
    db.flush()
    return state


def _event_totals(events: list[MatchPlayerEvent]) -> tuple[int, int, int]:
    goals = sum(int(item.quantity or 0) for item in events if item.event_type in {"goal", "own_goal"})
    assists = sum(int(item.quantity or 0) for item in events if item.event_type == "assist")
    mvps = sum(int(item.quantity or 0) for item in events if item.event_type == "mvp")
    return goals, assists, mvps


def evaluate_match_readiness(match: Match, events: list[MatchPlayerEvent]) -> tuple[bool, bool, list[str], list[str]]:
    issue_codes: list[str] = []
    issue_messages: list[str] = []
    status = str(match.status or "scheduled")

    if status == "scheduled":
        issue_codes.append("missing_result")
        issue_messages.append("尚未录入比赛结果")
        return False, False, issue_codes, issue_messages

    if status in NON_EVENT_RESOLVED_STATUSES:
        return True, True, issue_codes, issue_messages

    if status != "played":
        issue_codes.append("invalid_status")
        issue_messages.append(f"无法识别比赛状态：{status}")
        return False, False, issue_codes, issue_messages

    if match.home_score is None or match.away_score is None:
        issue_codes.append("invalid_score")
        issue_messages.append("已赛比赛缺少完整比分")
        return False, False, issue_codes, issue_messages

    result_ready = True
    score_goals = int(match.home_score or 0) + int(match.away_score or 0)
    event_goals, assists, mvps = _event_totals(events)

    if event_goals < score_goals:
        issue_codes.append("missing_events")
        issue_messages.append(f"还缺少 {score_goals - event_goals} 个进球事件")
    elif event_goals > score_goals:
        issue_codes.append("invalid_goal_total")
        issue_messages.append(f"进球事件共 {event_goals} 个，超过总比分 {score_goals}")

    if assists > event_goals:
        issue_codes.append("invalid_assist_total")
        issue_messages.append("助攻数量不能超过已录入进球数量")

    if mvps == 0:
        issue_codes.append("missing_events")
        issue_messages.append("缺少本场最佳球员")
    elif mvps > 1:
        issue_codes.append("invalid_mvp_total")
        issue_messages.append("每场比赛只能有一名最佳球员")

    return result_ready, not issue_codes, list(dict.fromkeys(issue_codes)), issue_messages


def _latest_pair_update(
    matches: list[Match],
    events_by_match: dict[int, list[MatchPlayerEvent]],
    _suspension_records: list[PlayerSuspensionRecord],
) -> datetime | None:
    timestamps = [item.updated_at for item in matches if item.updated_at]
    timestamps.extend(
        event.updated_at
        for match in matches
        for event in events_by_match.get(match.id, [])
        if event.updated_at
    )
    return max(timestamps) if timestamps else None


def _build_pair_summary(
    *,
    level: str,
    round_start: int,
    matches: list[Match],
    events_by_match: dict[int, list[MatchPlayerEvent]],
    suspension_records: list[PlayerSuspensionRecord],
    state: CompetitionRoundWorkState | None,
    identity: WorkspaceIdentityResponse | None = None,
    history: list[CompetitionRoundWorkLog] | None = None,
    responsibilities: dict[str, CompetitionResponsibilityAssignment] | None = None,
) -> CompetitionRoundWorkSummaryResponse:
    round_end = round_start + 1
    result_ready_count = 0
    event_ready_count = 0
    missing_result_count = 0
    missing_event_count = 0
    invalid_count = 0
    tasks: list[CompetitionWorkTaskResponse] = []

    for match in matches:
        result_ready, event_ready, issue_codes, issue_messages = evaluate_match_readiness(
            match,
            events_by_match.get(match.id, []),
        )
        result_ready_count += int(result_ready)
        event_ready_count += int(event_ready)
        missing_result_count += int("missing_result" in issue_codes)
        missing_event_count += int("missing_events" in issue_codes)
        invalid_count += int(any(code.startswith("invalid_") for code in issue_codes))
        if issue_codes:
            tasks.append(
                CompetitionWorkTaskResponse(
                    match_id=match.id,
                    level=match.level,
                    round_no=match.round_no,
                    home_team_name=match.home_team_name,
                    away_team_name=match.away_team_name,
                    home_score=match.home_score,
                    away_score=match.away_score,
                    status=match.status,
                    issue_codes=issue_codes,
                    issue_messages=issue_messages,
                )
            )

    suspension_confirmed = bool(state and state.suspension_confirmed_at)
    completion_ready = bool(
        matches
        and result_ready_count == len(matches)
        and event_ready_count == len(matches)
        and invalid_count == 0
        and suspension_confirmed
    )
    latest_update = _latest_pair_update(matches, events_by_match, suspension_records)
    changed_after_completion = bool(
        state
        and state.completed_at
        and latest_update
        and latest_update > state.completed_at
    )
    completed = bool(state and state.completed_at and not changed_after_completion and completion_ready)
    changed_after_submission = bool(
        state
        and state.submitted_at
        and latest_update
        and latest_update > state.submitted_at
    )
    responsibility_map = responsibilities or {}
    schedule_assignment = responsibility_map.get("schedule")
    suspension_assignment = responsibility_map.get("suspensions")
    workflow_status = _workflow_status(
        state,
        has_schedule_owner=bool(schedule_assignment),
        completion_ready=completion_ready,
        changed_after_submission=changed_after_submission,
        completed=completed,
    )
    is_my_schedule_task = bool(identity and schedule_assignment and schedule_assignment.principal_id == identity.principal_id)
    is_my_suspension_task = bool(identity and suspension_assignment and suspension_assignment.principal_id == identity.principal_id)
    is_mine = bool(is_my_schedule_task or is_my_suspension_task)
    can_submit = bool(
        identity
        and "schedule.write" in identity.capabilities
        and completion_ready
        and schedule_assignment
        and workflow_status not in {"pending_review", "completed"}
        and (is_my_schedule_task or identity.is_full_admin)
    )
    can_review = bool(identity and identity.is_full_admin and workflow_status == "pending_review")
    can_confirm_suspensions = bool(
        identity
        and "suspensions.write" in identity.capabilities
        and suspension_assignment
        and (is_my_suspension_task or identity.is_full_admin)
    )

    return CompetitionRoundWorkSummaryResponse(
        level=level,
        round_start=round_start,
        round_end=round_end,
        round_label=_round_label(round_start, round_end),
        workflow_status=workflow_status,
        workflow_status_label=WORKFLOW_STATUS_LABELS[workflow_status],
        schedule_principal_id=schedule_assignment.principal_id if schedule_assignment else None,
        schedule_display_name=schedule_assignment.display_name if schedule_assignment else None,
        suspension_principal_id=suspension_assignment.principal_id if suspension_assignment else None,
        suspension_display_name=suspension_assignment.display_name if suspension_assignment else None,
        is_my_schedule_task=is_my_schedule_task,
        is_my_suspension_task=is_my_suspension_task,
        can_confirm_suspensions=can_confirm_suspensions,
        assignee_principal_id=schedule_assignment.principal_id if schedule_assignment else None,
        assignee_display_name=schedule_assignment.display_name if schedule_assignment else None,
        assigned_at=schedule_assignment.assigned_at if schedule_assignment else None,
        assigned_by=schedule_assignment.assigned_by if schedule_assignment else None,
        submitted_at=state.submitted_at if state else None,
        submitted_by=state.submitted_by if state else None,
        changed_after_submission=changed_after_submission,
        is_mine=is_mine,
        can_submit=can_submit,
        can_review=can_review,
        total_matches=len(matches),
        result_ready_count=result_ready_count,
        event_ready_count=event_ready_count,
        missing_result_count=missing_result_count,
        missing_event_count=missing_event_count,
        invalid_count=invalid_count,
        suspension_confirmed=suspension_confirmed,
        suspension_confirmed_at=state.suspension_confirmed_at if state else None,
        suspension_confirmed_by=state.suspension_confirmed_by if state else None,
        completion_ready=completion_ready,
        completed=completed,
        completed_at=state.completed_at if state else None,
        completed_by=state.completed_by if state else None,
        changed_after_completion=changed_after_completion,
        note=str(state.note or "") if state else "",
        tasks=tasks,
        history=[
            CompetitionWorkLogResponse(
                id=row.id,
                action=row.action,
                action_label=WORK_LOG_ACTION_LABELS.get(row.action, row.action),
                operator_principal_id=row.operator_principal_id,
                operator_display_name=row.operator_display_name,
                from_status=row.from_status,
                to_status=row.to_status,
                detail=str(row.detail or ""),
                created_at=row.created_at,
            )
            for row in (history or [])
        ],
    )


def _select_active_pair(
    pairs: dict[int, list[Match]],
    states: dict[int, CompetitionRoundWorkState],
    events_by_match: dict[int, list[MatchPlayerEvent]],
    suspension_records: list[PlayerSuspensionRecord],
    level: str,
) -> int:
    pair_starts = sorted(pairs)
    if not pair_starts:
        return 1

    started = [
        pair_start
        for pair_start in pair_starts
        if pair_start in states
        or any(
            match.status != "scheduled" or match.home_score is not None or match.away_score is not None
            for match in pairs[pair_start]
        )
    ]
    unfinished_started: list[int] = []
    for pair_start in started:
        summary = _build_pair_summary(
            level=level,
            round_start=pair_start,
            matches=pairs[pair_start],
            events_by_match=events_by_match,
            suspension_records=suspension_records,
            state=states.get(pair_start),
        )
        if not summary.completed:
            unfinished_started.append(pair_start)
    if unfinished_started:
        return max(unfinished_started)

    completed_starts = [pair_start for pair_start, state in states.items() if state.completed_at]
    if completed_starts:
        latest_completed = max(completed_starts)
        return next((item for item in pair_starts if item > latest_completed), latest_completed)
    if started:
        return max(started)
    return pair_starts[0]


def get_competition_work_summary(
    db: Session,
    identity: WorkspaceIdentityResponse | None = None,
) -> CompetitionWorkSummaryResponse:
    matches = db.query(Match).filter(Match.level.in_(LEAGUE_LEVELS)).order_by(Match.level, Match.round_no, Match.id).all()
    match_ids = [item.id for item in matches]
    events = db.query(MatchPlayerEvent).filter(MatchPlayerEvent.match_id.in_(match_ids)).all() if match_ids else []
    events_by_match: dict[int, list[MatchPlayerEvent]] = defaultdict(list)
    for event in events:
        events_by_match[event.match_id].append(event)

    states = db.query(CompetitionRoundWorkState).all()
    states_by_level: dict[str, dict[int, CompetitionRoundWorkState]] = defaultdict(dict)
    for state in states:
        states_by_level[state.level][state.round_start] = state
    suspensions = db.query(PlayerSuspensionRecord).filter(PlayerSuspensionRecord.level.in_(LEAGUE_LEVELS)).all()
    suspensions_by_level: dict[str, list[PlayerSuspensionRecord]] = defaultdict(list)
    for item in suspensions:
        suspensions_by_level[item.level].append(item)

    responsibility_rows = db.query(CompetitionResponsibilityAssignment).all()
    responsibilities_by_level: dict[str, dict[str, CompetitionResponsibilityAssignment]] = defaultdict(dict)
    for item in responsibility_rows:
        responsibilities_by_level[item.level][item.responsibility_type] = item

    matches_by_level_pair: dict[str, dict[int, list[Match]]] = defaultdict(lambda: defaultdict(list))
    for match in matches:
        matches_by_level_pair[match.level][get_round_pair_start(match.round_no)].append(match)

    summaries: list[CompetitionRoundWorkSummaryResponse] = []
    for level in LEAGUE_LEVELS:
        pairs = matches_by_level_pair[level]
        pair_start = _select_active_pair(
            pairs,
            states_by_level[level],
            events_by_match,
            suspensions_by_level[level],
            level,
        )
        active_state = states_by_level[level].get(pair_start)
        active_history = (
            db.query(CompetitionRoundWorkLog)
            .filter(CompetitionRoundWorkLog.state_id == active_state.id)
            .order_by(CompetitionRoundWorkLog.created_at.desc(), CompetitionRoundWorkLog.id.desc())
            .limit(10)
            .all()
            if active_state
            else []
        )
        summaries.append(
            _build_pair_summary(
                level=level,
                round_start=pair_start,
                matches=pairs.get(pair_start, []),
                events_by_match=events_by_match,
                suspension_records=suspensions_by_level[level],
                state=active_state,
                identity=identity,
                history=active_history,
                responsibilities=responsibilities_by_level[level],
            )
        )
    return CompetitionWorkSummaryResponse(levels=summaries)


def set_level_responsibilities(
    db: Session,
    identity: WorkspaceIdentityResponse,
    *,
    level: str,
    schedule_principal_id: str | None,
    suspension_principal_id: str | None,
) -> CompetitionWorkSummaryResponse:
    if not identity.is_full_admin:
        raise HTTPException(status_code=403, detail="只有完整管理员可以任命级别负责人")
    if level not in LEAGUE_LEVELS:
        raise HTTPException(status_code=400, detail="联赛级别无效")

    current_summary = get_competition_work_summary(db, identity)
    current = next((item for item in current_summary.levels if item.level == level), None)
    state = _get_or_create_state(db, level, current.round_start if current else 1)
    changes: list[str] = []
    for responsibility_type, requested_principal, label, action in (
        ("schedule", schedule_principal_id, "赛程与比赛事件", "assign_schedule_responsibility"),
        ("suspensions", suspension_principal_id, "伤停", "assign_suspension_responsibility"),
    ):
        existing = _responsibility_for(db, level, responsibility_type)
        old_name = existing.display_name if existing else "未任命"
        old_principal = existing.principal_id if existing else None
        if requested_principal:
            principal_id, display_name = _resolve_assignable_principal(db, requested_principal, responsibility_type)
            if existing:
                existing.principal_id = principal_id
                existing.display_name = display_name
                existing.assigned_by = identity.principal_id
                existing.assigned_at = datetime.now()
                existing.updated_at = datetime.now()
            else:
                db.add(
                    CompetitionResponsibilityAssignment(
                        level=level,
                        responsibility_type=responsibility_type,
                        principal_id=principal_id,
                        display_name=display_name,
                        assigned_by=identity.principal_id,
                        assigned_at=datetime.now(),
                        updated_at=datetime.now(),
                    )
                )
            new_name = display_name
            new_principal = principal_id
        else:
            if existing:
                db.delete(existing)
            new_name = "未任命"
            new_principal = None
        if old_principal != new_principal:
            changes.append(f"{label}：{old_name} → {new_name}")
            _append_work_log(
                db,
                state,
                identity,
                action=action,
                from_status=current.workflow_status if current else "unassigned",
                to_status="in_progress" if schedule_principal_id else "unassigned",
                detail=f"{old_name} → {new_name}",
            )
            if responsibility_type == "schedule" and not (current and current.completed):
                state.submitted_at = None
                state.submitted_by = None
                state.completed_at = None
                state.completed_by = None
    state.updated_at = datetime.now()
    db.commit()
    if changes:
        persist_admin_operation_audit(
            db.get_bind(),
            category="competition",
            action="set_level_responsibilities",
            operator=_operator(identity),
            status="success",
            summary=f"已更新 {level} 数据统计职责",
            source=AUDIT_SOURCE_ADMIN_UI,
            operation_label="任命级别负责人",
            details_text="；".join(changes),
            request_payload={
                "level": level,
                "schedule_principal_id": schedule_principal_id,
                "suspension_principal_id": suspension_principal_id,
            },
        )
    return get_competition_work_summary(db, identity)


def assign_round_work(
    db: Session,
    identity: WorkspaceIdentityResponse,
    *,
    level: str,
    round_start: int,
    assignee_principal_id: str | None,
) -> CompetitionWorkSummaryResponse:
    suspension_assignment = _responsibility_for(db, level, "suspensions")
    return set_level_responsibilities(
        db,
        identity,
        level=level,
        schedule_principal_id=assignee_principal_id,
        suspension_principal_id=suspension_assignment.principal_id if suspension_assignment else None,
    )


def set_suspension_confirmation(
    db: Session,
    identity: WorkspaceIdentityResponse,
    *,
    level: str,
    round_start: int,
    confirmed: bool,
    note: str | None,
) -> CompetitionWorkSummaryResponse:
    if level not in LEAGUE_LEVELS or get_round_pair_start(round_start) != round_start:
        raise HTTPException(status_code=400, detail="联赛级别或轮次范围无效")
    suspension_assignment = _responsibility_for(db, level, "suspensions")
    if "suspensions.write" not in identity.capabilities or not identity_has_level_responsibility(identity, suspension_assignment):
        raise HTTPException(status_code=403, detail="当前账号不是该级别的伤停负责人")
    operator = _operator(identity)
    state = _get_or_create_state(db, level, round_start)
    schedule_assignment = _responsibility_for(db, level, "schedule")
    from_status = "pending_review" if state.submitted_at else ("in_progress" if schedule_assignment else "unassigned")
    if state.completed_at:
        state.completed_at = None
        state.completed_by = None
    state.submitted_at = None
    state.submitted_by = None
    state.suspension_confirmed_at = datetime.now() if confirmed else None
    state.suspension_confirmed_by = operator if confirmed else None
    state.note = str(note or "").strip() or None
    state.updated_at = datetime.now()
    _append_work_log(
        db,
        state,
        identity,
        action="confirm_suspensions" if confirmed else "reopen_suspensions",
        from_status=from_status,
        to_status="in_progress" if schedule_assignment else "unassigned",
        detail=str(note or "").strip(),
    )
    db.commit()
    persist_admin_operation_audit(
        db.get_bind(),
        category="competition",
        action="confirm_round_suspensions" if confirmed else "reopen_round_suspensions",
        operator=operator,
        status="success",
        summary=f"{level}{_round_label(round_start, round_start + 1)}伤停{'已确认' if confirmed else '已取消确认'}",
        source=AUDIT_SOURCE_ADMIN_UI,
        operation_label="轮次伤停确认",
        details_text=f"level={level}; round_start={round_start}; confirmed={confirmed}",
        request_payload={"level": level, "round_start": round_start, "confirmed": confirmed, "note": note},
    )
    return get_competition_work_summary(db, identity)


def invalidate_current_round_suspension_confirmation(db: Session, level: str) -> None:
    summary = get_competition_work_summary(db)
    current = next((item for item in summary.levels if item.level == level), None)
    if not current:
        return
    state = _state_for_pair(db, level, current.round_start)
    if not state or not state.suspension_confirmed_at:
        return
    state.suspension_confirmed_at = None
    state.suspension_confirmed_by = None
    state.completed_at = None
    state.completed_by = None
    state.submitted_at = None
    state.submitted_by = None
    state.updated_at = datetime.now()


def submit_round_work(
    db: Session,
    identity: WorkspaceIdentityResponse,
    *,
    level: str,
    round_start: int,
    note: str | None = None,
) -> CompetitionWorkSummaryResponse:
    if "schedule.write" not in identity.capabilities:
        raise HTTPException(status_code=403, detail="当前账号没有赛程维护权限")
    if level not in LEAGUE_LEVELS or get_round_pair_start(round_start) != round_start:
        raise HTTPException(status_code=400, detail="联赛级别或轮次范围无效")

    all_matches = db.query(Match).filter(Match.level == level).all()
    pair_matches = [item for item in all_matches if get_round_pair_start(item.round_no) == round_start]
    match_ids = [item.id for item in pair_matches]
    events = db.query(MatchPlayerEvent).filter(MatchPlayerEvent.match_id.in_(match_ids)).all() if match_ids else []
    events_by_match: dict[int, list[MatchPlayerEvent]] = defaultdict(list)
    for event in events:
        events_by_match[event.match_id].append(event)
    suspensions = db.query(PlayerSuspensionRecord).filter(PlayerSuspensionRecord.level == level).all()
    state = _state_for_pair(db, level, round_start)
    responsibilities = {
        item.responsibility_type: item
        for item in db.query(CompetitionResponsibilityAssignment)
        .filter(CompetitionResponsibilityAssignment.level == level)
        .all()
    }
    summary = _build_pair_summary(
        level=level,
        round_start=round_start,
        matches=pair_matches,
        events_by_match=events_by_match,
        suspension_records=suspensions,
        state=state,
        identity=identity,
        responsibilities=responsibilities,
    )
    if not summary.completion_ready:
        problems = []
        if summary.missing_result_count:
            problems.append(f"{summary.missing_result_count} 场缺少结果")
        if summary.missing_event_count:
            problems.append(f"{summary.missing_event_count} 场缺少球员事件")
        if summary.invalid_count:
            problems.append(f"{summary.invalid_count} 场数据异常")
        if not summary.suspension_confirmed:
            problems.append("伤停尚未确认")
        raise HTTPException(status_code=409, detail="本轮尚不能提交复核：" + "；".join(problems or ["没有可确认的比赛"]))

    state = state or _get_or_create_state(db, level, round_start)
    schedule_assignment = responsibilities.get("schedule")
    if not schedule_assignment:
        raise HTTPException(status_code=409, detail="请先任命该级别的赛程与比赛事件负责人")
    if schedule_assignment.principal_id != identity.principal_id and not identity.is_full_admin:
        raise HTTPException(status_code=403, detail="只有该级别的赛程与比赛事件负责人可以提交复核")
    if summary.workflow_status == "pending_review":
        raise HTTPException(status_code=409, detail="本轮已经提交复核")
    if summary.completed:
        raise HTTPException(status_code=409, detail="本轮已经完成")
    operator = _operator(identity)
    state.submitted_at = datetime.now()
    state.submitted_by = identity.principal_id
    state.note = str(note or "").strip() or state.note
    state.completed_at = None
    state.completed_by = None
    state.updated_at = datetime.now()
    _append_work_log(
        db,
        state,
        identity,
        action="submit",
        from_status="in_progress",
        to_status="pending_review",
        detail=str(note or "").strip(),
    )
    db.commit()
    persist_admin_operation_audit(
        db.get_bind(),
        category="competition",
        action="submit_round_work",
        operator=operator,
        status="success",
        summary=f"已提交复核 {level}{_round_label(round_start, round_start + 1)}",
        source=AUDIT_SOURCE_ADMIN_UI,
        operation_label="提交轮次复核",
        details_text=f"level={level}; round_start={round_start}",
        request_payload={"level": level, "round_start": round_start, "note": note},
    )
    return get_competition_work_summary(db, identity)


def review_round_work(
    db: Session,
    identity: WorkspaceIdentityResponse,
    *,
    level: str,
    round_start: int,
    approved: bool,
    note: str | None = None,
) -> CompetitionWorkSummaryResponse:
    if not identity.is_full_admin:
        raise HTTPException(status_code=403, detail="只有完整管理员可以复核轮次任务")
    if level not in LEAGUE_LEVELS or get_round_pair_start(round_start) != round_start:
        raise HTTPException(status_code=400, detail="联赛级别或轮次范围无效")
    summary = get_competition_work_summary(db, identity)
    current = next((item for item in summary.levels if item.level == level and item.round_start == round_start), None)
    if not current or current.workflow_status != "pending_review":
        raise HTTPException(status_code=409, detail="本轮当前不处于待复核状态")
    state = _state_for_pair(db, level, round_start)
    if not state:
        raise HTTPException(status_code=409, detail="本轮工作状态不存在")

    operator = _operator(identity)
    clean_note = str(note or "").strip()
    if approved:
        state.completed_at = datetime.now()
        state.completed_by = identity.principal_id
        action = "review_approve"
        to_status = "completed"
        operation_action = "complete_round_work"
        operation_label = "复核轮次完成"
        operation_summary = f"已复核通过 {level}{_round_label(round_start, round_start + 1)}"
    else:
        state.submitted_at = None
        state.submitted_by = None
        state.completed_at = None
        state.completed_by = None
        action = "review_reject"
        to_status = "in_progress"
        operation_action = "reject_round_work"
        operation_label = "退回轮次修改"
        operation_summary = f"已退回 {level}{_round_label(round_start, round_start + 1)}"
    if clean_note:
        state.note = clean_note
    state.updated_at = datetime.now()
    _append_work_log(
        db,
        state,
        identity,
        action=action,
        from_status="pending_review",
        to_status=to_status,
        detail=clean_note,
    )
    db.commit()
    persist_admin_operation_audit(
        db.get_bind(),
        category="competition",
        action=operation_action,
        operator=operator,
        status="success",
        summary=operation_summary,
        source=AUDIT_SOURCE_ADMIN_UI,
        operation_label=operation_label,
        details_text=f"level={level}; round_start={round_start}; approved={approved}",
        request_payload={"level": level, "round_start": round_start, "approved": approved, "note": note},
    )
    return get_competition_work_summary(db, identity)


def complete_round_work(
    db: Session,
    identity: WorkspaceIdentityResponse,
    *,
    level: str,
    round_start: int,
) -> CompetitionWorkSummaryResponse:
    return review_round_work(
        db,
        identity,
        level=level,
        round_start=round_start,
        approved=True,
    )
