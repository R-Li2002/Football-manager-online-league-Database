from fastapi import APIRouter, Cookie, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from schemas_read import (
    CompetitionWorkSummaryResponse,
    HomePromotionResponse,
    WorkspaceAccountsResponse,
    WorkspaceDashboardResponse,
    WorkspaceSessionResponse,
)
from schemas_write import (
    CompetitionRoundAssignmentRequest,
    CompetitionRoundConfirmationRequest,
    CompetitionRoundReviewRequest,
    CompetitionRoundSubmissionRequest,
    CompetitionResponsibilityUpdateRequest,
    HomePromotionUpsertRequest,
)
from services import competition_work_service, home_promotion_asset_service, home_promotion_service, workspace_service

ADMIN_SESSION_COOKIE_NAME = "session_token"
COACH_SESSION_COOKIE_NAME = "coach_session_token"


def build_workspace_router(get_db):
    router = APIRouter()

    def resolve_identity(
        db: Session,
        admin_session_token: str | None,
        coach_session_token: str | None,
    ):
        identity = workspace_service.resolve_workspace_identity(
            db,
            admin_session_token=admin_session_token,
            coach_session_token=coach_session_token,
        )
        if not identity:
            raise HTTPException(status_code=401, detail="请先登录工作账号")
        return identity

    @router.get("/api/workspace/session", response_model=WorkspaceSessionResponse)
    def get_workspace_session(
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return workspace_service.get_workspace_session(
            db,
            admin_session_token=admin_session_token,
            coach_session_token=coach_session_token,
        )

    @router.get("/api/workspace/dashboard", response_model=WorkspaceDashboardResponse)
    def get_workspace_dashboard(
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        if not identity.is_full_admin and len(identity.capabilities) <= 1:
            raise HTTPException(status_code=403, detail="当前教练账号没有联赛工作权限")
        return workspace_service.get_workspace_dashboard(db, identity)

    @router.get("/api/workspace/accounts", response_model=WorkspaceAccountsResponse)
    def get_workspace_accounts(
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        try:
            return workspace_service.list_workspace_accounts(db, identity)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail="只有完整管理员可以管理账号权限") from exc

    @router.get("/api/workspace/home-promotions", response_model=list[HomePromotionResponse])
    def get_workspace_home_promotions(
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return home_promotion_service.list_admin_promotions(db, identity)

    @router.post("/api/workspace/home-promotions", response_model=HomePromotionResponse)
    def create_workspace_home_promotion(
        request: HomePromotionUpsertRequest,
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return home_promotion_service.create_promotion(db, identity, request)

    @router.patch("/api/workspace/home-promotions/{promotion_id}", response_model=HomePromotionResponse)
    def update_workspace_home_promotion(
        promotion_id: int,
        request: HomePromotionUpsertRequest,
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return home_promotion_service.update_promotion(db, identity, promotion_id, request)

    @router.delete("/api/workspace/home-promotions/{promotion_id}")
    def delete_workspace_home_promotion(
        promotion_id: int,
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return home_promotion_service.delete_promotion(db, identity, promotion_id)

    @router.post("/api/workspace/home-promotions/sync-cup-champions", response_model=list[HomePromotionResponse])
    def sync_workspace_cup_champions(
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return home_promotion_service.sync_cup_champions(db, identity)

    @router.post("/api/workspace/home-promotions/sync-league-champions", response_model=list[HomePromotionResponse])
    def sync_workspace_league_champions(
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return home_promotion_service.sync_league_champions(db, identity)

    @router.post("/api/workspace/home-promotions/image")
    def upload_workspace_home_promotion_image(
        image: UploadFile = File(...),
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return home_promotion_asset_service.save_promotion_image(identity, image)

    @router.get("/api/workspace/competition-work", response_model=CompetitionWorkSummaryResponse)
    def get_competition_work(
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        if not {"schedule.write", "suspensions.write"}.intersection(identity.capabilities):
            raise HTTPException(status_code=403, detail="当前账号没有数据统计工作权限")
        return competition_work_service.get_competition_work_summary(db, identity)

    @router.patch(
        "/api/workspace/competition-responsibilities/{level}",
        response_model=CompetitionWorkSummaryResponse,
    )
    def update_competition_responsibilities(
        level: str,
        request: CompetitionResponsibilityUpdateRequest,
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return competition_work_service.set_level_responsibilities(
            db,
            identity,
            level=level,
            schedule_principal_id=request.schedule_principal_id,
            suspension_principal_id=request.suspension_principal_id,
        )

    @router.patch(
        "/api/workspace/competition-work/{level}/{round_start}/assignment",
        response_model=CompetitionWorkSummaryResponse,
    )
    def update_round_assignment(
        level: str,
        round_start: int,
        request: CompetitionRoundAssignmentRequest,
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return competition_work_service.assign_round_work(
            db,
            identity,
            level=level,
            round_start=round_start,
            assignee_principal_id=request.assignee_principal_id,
        )

    @router.patch(
        "/api/workspace/competition-work/{level}/{round_start}/suspensions",
        response_model=CompetitionWorkSummaryResponse,
    )
    def update_round_suspension_confirmation(
        level: str,
        round_start: int,
        request: CompetitionRoundConfirmationRequest,
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return competition_work_service.set_suspension_confirmation(
            db,
            identity,
            level=level,
            round_start=round_start,
            confirmed=request.confirmed,
            note=request.note,
        )

    @router.post(
        "/api/workspace/competition-work/{level}/{round_start}/submit",
        response_model=CompetitionWorkSummaryResponse,
    )
    def submit_round_work(
        level: str,
        round_start: int,
        request: CompetitionRoundSubmissionRequest,
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return competition_work_service.submit_round_work(
            db,
            identity,
            level=level,
            round_start=round_start,
            note=request.note,
        )

    @router.post(
        "/api/workspace/competition-work/{level}/{round_start}/review",
        response_model=CompetitionWorkSummaryResponse,
    )
    def review_round_work(
        level: str,
        round_start: int,
        request: CompetitionRoundReviewRequest,
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return competition_work_service.review_round_work(
            db,
            identity,
            level=level,
            round_start=round_start,
            approved=request.approved,
            note=request.note,
        )

    @router.post(
        "/api/workspace/competition-work/{level}/{round_start}/complete",
        response_model=CompetitionWorkSummaryResponse,
    )
    def complete_round_work(
        level: str,
        round_start: int,
        admin_session_token: str | None = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: str | None = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        identity = resolve_identity(db, admin_session_token, coach_session_token)
        return competition_work_service.complete_round_work(
            db,
            identity,
            level=level,
            round_start=round_start,
        )

    return router
