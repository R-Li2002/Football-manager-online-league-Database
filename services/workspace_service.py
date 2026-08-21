from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from auth_utils import get_session_username
from models import (
    AdminUser,
    CandidateList,
    Coach,
    CoachAccount,
    CupMatch,
    DataFeedbackReport,
    DrawSession,
    OperationAudit,
    RankingMatch,
    SeasonArchive,
)
from schemas_read import (
    WorkspaceAccountResponse,
    WorkspaceAccountsResponse,
    WorkspaceDashboardResponse,
    WorkspaceIdentityResponse,
    WorkspaceMetricResponse,
    WorkspaceRecentActionResponse,
    WorkspaceSessionResponse,
    WorkspaceTaskResponse,
)
from services import auth_service, coach_service, competition_work_service, data_status_service

CAPABILITY_LABELS = {
    "schedule.write": "赛程维护",
    "match_events.write": "比赛事件",
    "cup_standings.write": "杯赛积分榜",
    "rankings.write": "排位统计",
    "suspensions.write": "伤停维护",
    "candidate_lists.write": "候选名单",
    "daily_reports.write": "日报维护",
    "draws.write": "抽签管理",
    "archives.write": "赛季档案管理",
    "roster.write": "球员操作",
    "coach_profile.write_self": "个人中心",
    "coach_profiles.manage": "教练管理",
    "accounts.manage": "人员与权限",
    "home_promotions.manage": "主页宣传",
    "imports.execute": "正式导入",
    "system.maintain": "系统维护",
    "audit.read": "操作记录",
    "feedback.manage": "数据纠错",
}

FULL_ADMIN_CAPABILITIES = list(CAPABILITY_LABELS)
WORK_CAPABILITIES = {
    "schedule": ("schedule.write", "match_events.write"),
    "cup_standings": ("cup_standings.write",),
    "rankings": ("rankings.write",),
    "suspensions": ("suspensions.write",),
    "candidate_lists": ("candidate_lists.write",),
    "daily_reports": ("daily_reports.write",),
    "draws": ("draws.write",),
    "archives": ("archives.write",),
}


def _labels(capabilities: list[str]) -> list[str]:
    return [CAPABILITY_LABELS[item] for item in capabilities if item in CAPABILITY_LABELS]


def _admin_capabilities(role: str | None) -> list[str]:
    if auth_service.can_manage_admin(role):
        return list(FULL_ADMIN_CAPABILITIES)
    capabilities: list[str] = []
    if auth_service.can_manage_schedule(role):
        capabilities.extend(WORK_CAPABILITIES["schedule"])
    if auth_service.can_manage_cup_standings(role):
        capabilities.extend(WORK_CAPABILITIES["cup_standings"])
    if auth_service.can_manage_rankings(role):
        capabilities.extend(WORK_CAPABILITIES["rankings"])
    if auth_service.can_manage_suspensions(role):
        capabilities.extend(WORK_CAPABILITIES["suspensions"])
    if auth_service.can_manage_candidate_lists(role):
        capabilities.extend(WORK_CAPABILITIES["candidate_lists"])
    if auth_service.can_manage_daily_reports(role):
        capabilities.extend(WORK_CAPABILITIES["daily_reports"])
    if auth_service.can_manage_draws(role):
        capabilities.extend(WORK_CAPABILITIES["draws"])
    if auth_service.can_manage_archives(role):
        capabilities.extend(WORK_CAPABILITIES["archives"])
    return list(dict.fromkeys(capabilities))


def _coach_capabilities(account: CoachAccount) -> list[str]:
    capabilities = ["coach_profile.write_self"]
    if account.can_manage_schedule:
        capabilities.extend(WORK_CAPABILITIES["schedule"])
    if account.can_manage_cup_standings:
        capabilities.extend(WORK_CAPABILITIES["cup_standings"])
    if account.can_manage_rankings:
        capabilities.extend(WORK_CAPABILITIES["rankings"])
    if account.can_manage_suspensions:
        capabilities.extend(WORK_CAPABILITIES["suspensions"])
    if account.can_manage_candidate_lists:
        capabilities.extend(WORK_CAPABILITIES["candidate_lists"])
    if account.can_manage_daily_reports:
        capabilities.extend(WORK_CAPABILITIES["daily_reports"])
    if account.can_manage_draws:
        capabilities.extend(WORK_CAPABILITIES["draws"])
    if account.can_manage_archives:
        capabilities.extend(WORK_CAPABILITIES["archives"])
    return list(dict.fromkeys(capabilities))


def resolve_workspace_identity(
    db: Session,
    *,
    admin_session_token: str | None,
    coach_session_token: str | None,
) -> WorkspaceIdentityResponse | None:
    admin_username = get_session_username(db, admin_session_token)
    if admin_username:
        admin = db.query(AdminUser).filter(AdminUser.username == admin_username).first()
        if admin:
            role = auth_service.normalize_admin_role(admin.role)
            capabilities = _admin_capabilities(role)
            return WorkspaceIdentityResponse(
                principal_id=f"admin:{admin.username}",
                source="admin_account",
                account_type="administrator" if auth_service.can_manage_admin(role) else "worker",
                username=admin.username,
                display_name=admin.username,
                role=role,
                is_full_admin=auth_service.can_manage_admin(role),
                capabilities=capabilities,
                capability_labels=_labels(capabilities),
            )

    coach_identity = coach_service.get_coach_session_identity(db, coach_session_token)
    if (
        not coach_identity.authenticated
        or coach_identity.must_change_password
        or not coach_identity.qq_number
        or not coach_identity.coach_uid
        or not coach_identity.username
    ):
        return None
    account = db.query(CoachAccount).filter(CoachAccount.coach_uid == coach_identity.coach_uid).first()
    if not account:
        return None
    capabilities = _coach_capabilities(account)
    has_work = any(item != "coach_profile.write_self" for item in capabilities)
    return WorkspaceIdentityResponse(
        principal_id=f"coach:{account.username}",
        source="coach_account",
        account_type="coach_worker" if has_work else "coach",
        username=account.username,
        qq_number=account.qq_number,
        display_name=coach_identity.nickname or account.username,
        coach_uid=coach_identity.coach_uid,
        team_name=coach_identity.team_name,
        capabilities=capabilities,
        capability_labels=_labels(capabilities),
    )


def get_workspace_session(
    db: Session,
    *,
    admin_session_token: str | None,
    coach_session_token: str | None,
) -> WorkspaceSessionResponse:
    identity = resolve_workspace_identity(
        db,
        admin_session_token=admin_session_token,
        coach_session_token=coach_session_token,
    )
    return WorkspaceSessionResponse(authenticated=identity is not None, identity=identity)


def _metric(key: str, label: str, value: int, detail: str, target_tab: str, target_subtab: str | None = None):
    return WorkspaceMetricResponse(
        key=key,
        label=label,
        value=int(value or 0),
        detail=detail,
        target_tab=target_tab,
        target_subtab=target_subtab,
    )


def get_workspace_dashboard(db: Session, identity: WorkspaceIdentityResponse) -> WorkspaceDashboardResponse:
    capabilities = set(identity.capabilities)
    metrics: list[WorkspaceMetricResponse] = []
    competition_levels = (
        competition_work_service.get_competition_work_summary(db, identity).levels
        if {"schedule.write", "suspensions.write"}.intersection(capabilities)
        else []
    )
    schedule_levels = competition_levels if identity.is_full_admin else [item for item in competition_levels if item.is_my_schedule_task]
    suspension_levels = competition_levels if identity.is_full_admin else [item for item in competition_levels if item.is_my_suspension_task]
    if "schedule.write" in capabilities:
        pending_matches = sum(item.missing_result_count for item in schedule_levels)
        missing_events = sum(item.missing_event_count for item in schedule_levels)
        invalid_matches = sum(item.invalid_count for item in schedule_levels)
        metrics.append(_metric("schedule", "当前轮次待录结果", pending_matches, "当前工作轮次尚未确认结果的比赛", "competition", "schedule"))
        metrics.append(_metric("match_events", "当前轮次待补事件", missing_events, "当前工作轮次缺少进球、助攻或最佳球员", "competition", "schedule"))
        metrics.append(_metric("data_issues", "比赛数据异常", invalid_matches, "比分与比赛事件不一致的比赛", "competition", "schedule"))
    if "cup_standings.write" in capabilities:
        pending_cup_matches = (
            db.query(func.count(CupMatch.id))
            .filter(CupMatch.stage.like("group_%"), CupMatch.status != "played")
            .scalar()
            or 0
        )
        metrics.append(_metric("cup_standings", "杯赛待录比分", pending_cup_matches, "按小组逐对录入主客场比分，积分榜自动计算", "competition", "schedule"))
    if "rankings.write" in capabilities:
        ranking_match_count = db.query(func.count(RankingMatch.id)).scalar() or 0
        metrics.append(_metric("rankings", "排位比赛", ranking_match_count, "录入比分后基础分与场次总分实时重算", "competition", "rating"))
    if "suspensions.write" in capabilities:
        pending_confirmations = sum(
            1 for item in suspension_levels if item.total_matches > 0 and not item.suspension_confirmed
        )
        metrics.append(_metric("suspensions", "待确认轮次伤停", pending_confirmations, "当前工作轮次尚未确认伤停状态的级别", "competition", "suspensions"))
    if "candidate_lists.write" in capabilities:
        active_lists = db.query(func.count(CandidateList.id)).filter(CandidateList.archived_at.is_(None)).scalar() or 0
        metrics.append(_metric("candidate_lists", "候选名单", active_lists, "当前未归档的候选名单", "database", "candidates"))
    if "draws.write" in capabilities:
        active_draws = db.query(func.count(DrawSession.id)).filter(DrawSession.status.in_(["draft", "locked", "drawing", "completed"])).scalar() or 0
        metrics.append(_metric("draws", "抽签任务", active_draws, "尚未发布或作废的杯赛与乐透抽签", "draws"))
    if "archives.write" in capabilities:
        draft_archives = db.query(func.count(SeasonArchive.id)).filter(SeasonArchive.status == "draft").scalar() or 0
        metrics.append(_metric("archives", "赛季档案草稿", draft_archives, "尚未确认封存的赛季档案版本", "admin", "archives"))
    if identity.is_full_admin:
        open_feedback = db.query(func.count(DataFeedbackReport.id)).filter(DataFeedbackReport.status == "open").scalar() or 0
        metrics.append(_metric("feedback", "待处理纠错", open_feedback, "公开页面提交且尚未关闭的反馈", "admin", "feedback"))
        account_count = db.query(func.count(CoachAccount.id)).scalar() or 0
        metrics.append(_metric("accounts", "教练账号", account_count, "已经创建的教练登录账号", "admin", "accounts"))

    visible_tasks = [
        item
        for item in competition_levels
        if item.total_matches > 0
        and not item.completed
        and (identity.is_full_admin or item.is_mine)
    ]
    tasks = [
        WorkspaceTaskResponse(
            level=item.level,
            round_start=item.round_start,
            round_label=item.round_label,
            status=item.workflow_status,
            status_label=item.workflow_status_label,
            assignee_principal_id=item.schedule_principal_id,
            assignee_display_name=(
                f"赛程：{item.schedule_display_name or '未任命'} / 伤停：{item.suspension_display_name or '未任命'}"
                if identity.is_full_admin
                else item.schedule_display_name if item.is_my_schedule_task else item.suspension_display_name
            ),
            is_mine=item.is_mine,
            responsibility_labels=(
                (["赛程与比赛事件"] if item.is_my_schedule_task or identity.is_full_admin else [])
                + (["伤停"] if item.is_my_suspension_task or identity.is_full_admin else [])
            ),
            pending_count=(
                (item.missing_result_count + item.missing_event_count + item.invalid_count)
                * int(identity.is_full_admin or item.is_my_schedule_task)
                + int(not item.suspension_confirmed)
                * int(identity.is_full_admin or item.is_my_suspension_task)
            ),
            target_subtab="suspensions" if item.is_my_suspension_task and not item.is_my_schedule_task else "schedule",
        )
        for item in visible_tasks
    ]

    operator = identity.username if identity.source == "admin_account" else identity.principal_id
    recent_rows = (
        db.query(OperationAudit)
        .filter(OperationAudit.operator == operator)
        .order_by(OperationAudit.created_at.desc(), OperationAudit.id.desc())
        .limit(8)
        .all()
    )
    recent_actions = [
        WorkspaceRecentActionResponse(
            id=row.id,
            summary=row.summary,
            status=row.status,
            category=row.category,
            created_at=row.created_at,
        )
        for row in recent_rows
    ]
    data_statuses = data_status_service.get_actionable_data_statuses(
        db,
        is_full_admin=identity.is_full_admin,
        capabilities=capabilities,
    )
    return WorkspaceDashboardResponse(
        identity=identity,
        metrics=metrics,
        tasks=tasks,
        data_statuses=data_statuses,
        recent_actions=recent_actions,
    )


def list_workspace_accounts(db: Session, identity: WorkspaceIdentityResponse) -> WorkspaceAccountsResponse:
    if not identity.is_full_admin:
        raise PermissionError("accounts.manage required")
    items: list[WorkspaceAccountResponse] = []
    for admin in db.query(AdminUser).order_by(AdminUser.username.asc()).all():
        role = auth_service.normalize_admin_role(admin.role)
        capabilities = _admin_capabilities(role)
        items.append(
            WorkspaceAccountResponse(
                principal_id=f"admin:{admin.username}",
                source="admin_account",
                account_type="administrator" if auth_service.can_manage_admin(role) else "worker",
                username=admin.username,
                display_name=admin.username,
                is_active=True,
                role=role,
                capabilities=capabilities,
            )
        )
    coach_rows = (
        db.query(Coach, CoachAccount)
        .outerjoin(CoachAccount, CoachAccount.coach_uid == Coach.uid)
        .order_by(Coach.level.asc(), Coach.team_name.asc(), Coach.nickname.asc())
        .all()
    )
    for coach, account in coach_rows:
        capabilities = _coach_capabilities(account) if account else ["coach_profile.write_self"]
        has_work = any(item != "coach_profile.write_self" for item in capabilities)
        items.append(
            WorkspaceAccountResponse(
                principal_id=f"coach:{account.username}" if account else f"coach-profile:{coach.uid}",
                source="coach_account",
                account_type="coach_worker" if has_work else "coach",
                username=account.username if account else None,
                qq_number=account.qq_number if account else None,
                display_name=coach.nickname,
                coach_uid=coach.uid,
                team_id=coach.team_id,
                team_name=coach.team_name,
                level=coach.level,
                is_active=bool(account.is_active) if account else False,
                must_change_password=bool(account.must_change_password) if account else False,
                capabilities=capabilities,
                last_login_at=account.last_login_at if account else None,
            )
        )
    return WorkspaceAccountsResponse(items=items)
