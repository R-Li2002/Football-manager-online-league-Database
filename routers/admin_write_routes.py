import os
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy.orm import Session

from models import Match
from schemas_read import CoachAccountAdminResponse, CoachAccountPublicResponse, RankingsResponse
from schemas_read import (
    CandidateListDetailResponse,
    CandidateListMutationResponse,
    CandidateListPlayerPreviewResponse,
    CandidateListPlayersResponse,
    CandidateListPublishPreviewResponse,
    CandidateListRemovePreviewResponse,
    CandidateListSummaryResponse,
    TeamLineupResponse,
)
from schemas_write import (
    AdminActionResponse,
    AdminImportResponse,
    BatchActionResponse,
    BatchConsumeRequest,
    BatchReleaseRequest,
    BatchTransferRequest,
    ConsumeRequest,
    CoachAccountUpsertRequest,
    CoachMergeRequest,
    CoachTeamAssignmentRequest,
    CoachAssistantUpdateRequest,
    CoachLoginRequest,
    CoachPasswordChangeRequest,
    CoachQqBindingRequest,
    CoachHonorUpdateRequest,
    CoachUpdateRequest,
    CandidateListBatchRemoveRequest,
    CandidateListPlayerCommitRequest,
    CandidateListPlayerPreviewRequest,
    CandidateListUpsertRequest,
    CupGroupMatchResultUpdateRequest,
    CupGroupUpdateRequest,
    CupMatchResultUpdateRequest,
    CupMatchTeamsUpdateRequest,
    FishPlayerRequest,
    MatchBatchUpdateRequest,
    LoginResponse,
    LoginRequest,
    LogoutResponse,
    MatchUpdateRequest,
    PlayerUpdateRequest,
    RejuvenateRequest,
    RankingMatchCreateRequest,
    ScheduleImportResponse,
    SiteNoteUpdateRequest,
    SuspensionRecordUpdateRequest,
    TeamUpdateRequest,
    TeamLineupUpdateRequest,
    TeamLogoMatchApplyRequest,
    TransferRequest,
    UpdateUidRequest,
)
from services import admin_write_service, auth_service, candidate_list_service, coach_service, competition_work_service, import_upload_service, ranking_service, site_note_service, suspension_service, team_lineup_service, team_logo_match_service, team_logo_service

COACH_SESSION_COOKIE_NAME = "coach_session_token"
ADMIN_SESSION_COOKIE_NAME = "session_token"
COACH_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"}


def build_admin_write_router(
    get_db,
    verify_admin,
    verify_schedule_editor,
    verify_schedule_manager,
    verify_cup_standings_manager,
    verify_ranking_manager,
    verify_suspension_manager,
    verify_candidate_list_manager,
    set_session_cookie,
    clear_session_cookie,
    write_to_log,
):
    router = APIRouter()

    @router.post("/api/admin/rankings/matches", response_model=RankingsResponse)
    def create_ranking_match(
        request: RankingMatchCreateRequest,
        db: Session = Depends(get_db),
        operator: str = Depends(verify_ranking_manager),
    ):
        return ranking_service.create_ranking_match(db, operator, request, write_to_log)

    @router.delete("/api/admin/rankings/matches/{match_id}", response_model=RankingsResponse)
    def delete_ranking_match(
        match_id: int,
        db: Session = Depends(get_db),
        operator: str = Depends(verify_ranking_manager),
    ):
        return ranking_service.delete_ranking_match(db, operator, match_id, write_to_log)

    def require_level_responsibility(db: Session, operator: str, level: str, responsibility_type: str) -> None:
        if level in competition_work_service.LEAGUE_LEVELS and not competition_work_service.operator_can_manage_level(
            db,
            operator,
            level,
            responsibility_type,
        ):
            label = "赛程与比赛事件" if responsibility_type == "schedule" else "伤停"
            raise HTTPException(status_code=403, detail=f"当前账号不是 {level} 的{label}负责人")

    @router.post("/api/admin/login", response_model=LoginResponse)
    def admin_login(request: LoginRequest, http_request: Request, response: Response, db: Session = Depends(get_db)):
        return auth_service.login_admin(
            db,
            request.username,
            request.password,
            http_request,
            response,
            set_session_cookie=set_session_cookie,
            write_to_log=write_to_log,
        )

    @router.post("/api/admin/logout", response_model=LogoutResponse)
    def admin_logout(
        http_request: Request,
        response: Response,
        session_token: Optional[str] = Cookie(None),
        db: Session = Depends(get_db),
    ):
        return auth_service.logout_admin(
            db,
            http_request,
            response,
            session_token,
            clear_session_cookie=clear_session_cookie,
            write_to_log=write_to_log,
        )

    @router.post("/api/admin/transfer", response_model=AdminActionResponse)
    def transfer_player(request: TransferRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.transfer_player(db, admin, request, write_to_log)

    @router.post("/api/admin/fish", response_model=AdminActionResponse)
    def fish_player(request: FishPlayerRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.fish_player(db, admin, request, write_to_log)

    @router.post("/api/admin/sea-fish", response_model=AdminActionResponse)
    def fish_sea_player(request: TransferRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.fish_sea_player(db, admin, request, write_to_log)

    @router.post("/api/admin/release", response_model=AdminActionResponse)
    def release_player(request: TransferRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.release_player(db, admin, request, write_to_log)

    @router.post("/api/admin/consume", response_model=AdminActionResponse)
    def consume_player(request: ConsumeRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.consume_player(db, admin, request, write_to_log)

    @router.post("/api/admin/rejuvenate", response_model=AdminActionResponse)
    def rejuvenate_player(request: RejuvenateRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.rejuvenate_player(db, admin, request, write_to_log)

    @router.post("/api/admin/batch-transfer", response_model=BatchActionResponse)
    def batch_transfer(request: BatchTransferRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.batch_transfer(db, admin, request, write_to_log)

    @router.post("/api/admin/batch-consume", response_model=BatchActionResponse)
    def batch_consume(request: BatchConsumeRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.batch_consume(db, admin, request, write_to_log)

    @router.post("/api/admin/batch-release", response_model=BatchActionResponse)
    def batch_release(request: BatchReleaseRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.batch_release(db, admin, request, write_to_log)

    @router.post("/api/admin/undo/{log_id}", response_model=AdminActionResponse)
    def undo_operation(log_id: int, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.undo_operation(db, admin, log_id, write_to_log)

    @router.post("/api/admin/team/update", response_model=AdminActionResponse)
    def update_team_info(request: TeamUpdateRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.update_team_info(db, admin, request, write_to_log)

    @router.post("/api/admin/player/update", response_model=AdminActionResponse)
    def update_player_info(request: PlayerUpdateRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.update_player_info(db, admin, request, write_to_log)

    @router.post("/api/admin/player/update-uid", response_model=AdminActionResponse)
    def update_player_uid(request: UpdateUidRequest, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.update_player_uid(db, admin, request, write_to_log)

    @router.post("/api/admin/recalculate-wages", response_model=AdminActionResponse)
    def recalculate_wages(db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.recalculate_wages(db, admin, write_to_log)

    @router.post("/api/admin/team-stats/rebuild-cache", response_model=AdminActionResponse)
    def rebuild_team_stat_caches(db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.rebuild_team_stat_caches(db, admin, write_to_log)

    @router.post("/api/admin/coaches/sync", response_model=AdminActionResponse)
    def sync_coaches_from_teams(db: Session = Depends(get_db), admin: str = Depends(verify_schedule_editor)):
        return coach_service.sync_coaches_from_teams(db, admin, write_to_log)

    @router.get("/api/admin/coaches/{coach_uid}/account", response_model=CoachAccountAdminResponse)
    def get_coach_account_admin_status(
        coach_uid: str,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        return coach_service.get_coach_account_admin_status(db, admin, coach_uid)

    @router.post("/api/admin/coaches/{coach_uid}/account", response_model=AdminActionResponse)
    def upsert_coach_account(
        coach_uid: str,
        request: CoachAccountUpsertRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        return coach_service.upsert_coach_account(db, admin, coach_uid, request, write_to_log)

    @router.patch("/api/admin/coaches/{coach_uid}/team", response_model=AdminActionResponse)
    def assign_coach_team(
        coach_uid: str,
        request: CoachTeamAssignmentRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        return coach_service.assign_coach_team(db, admin, coach_uid, request, write_to_log)

    @router.post("/api/admin/coaches/{coach_uid}/merge", response_model=AdminActionResponse)
    def merge_coach(
        coach_uid: str,
        request: CoachMergeRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        return coach_service.merge_coach(db, admin, coach_uid, request, write_to_log)

    @router.delete("/api/admin/coaches/{coach_uid}/qq", response_model=AdminActionResponse)
    def unbind_coach_qq(
        coach_uid: str,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        return coach_service.unbind_coach_qq(db, admin, coach_uid, write_to_log)

    @router.patch("/api/admin/coaches/{coach_uid}", response_model=AdminActionResponse)
    def update_coach_profile(
        coach_uid: str,
        request: CoachUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return coach_service.update_coach_profile(db, admin, coach_uid, request, write_to_log)

    @router.post("/api/admin/coaches/{coach_uid}/avatar")
    def upload_coach_avatar(
        coach_uid: str,
        avatar: UploadFile = File(...),
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return coach_service.save_coach_avatar(db, admin, coach_uid, avatar, write_to_log)

    @router.post("/api/admin/teams/{team_id}/logo")
    def upload_team_logo(
        team_id: int,
        logo: UploadFile = File(...),
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return team_logo_service.save_team_logo(db, admin, team_id, logo, write_to_log)

    @router.get("/api/admin/team-logo-match/overview")
    def get_team_logo_match_overview(
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        return team_logo_match_service.get_match_overview(db, admin)

    @router.get("/api/admin/team-logo-match/search")
    def search_team_logo_candidates(
        q: str,
        team_id: int,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        return team_logo_match_service.search_fclogo(db, admin, team_id, q)

    @router.post("/api/admin/team-logo-match/apply")
    def apply_team_logo_candidate(
        request: TeamLogoMatchApplyRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        return team_logo_match_service.apply_fclogo_candidate(db, admin, request, write_to_log)

    @router.post("/api/admin/team-logo-match/upload")
    def upload_team_logo_candidate(
        team_id: int = Form(...),
        confirmed: bool = Form(False),
        logo: UploadFile = File(...),
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        return team_logo_match_service.upload_local_team_logo(db, admin, team_id, logo, write_to_log, confirmed=confirmed)

    @router.patch("/api/teams/{team_id}/lineup", response_model=TeamLineupResponse)
    def save_team_lineup(
        team_id: int,
        request: TeamLineupUpdateRequest,
        admin_session_token: Optional[str] = Cookie(None, alias=ADMIN_SESSION_COOKIE_NAME),
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return team_lineup_service.save_team_lineup(
            db,
            team_id,
            request,
            admin_session_token=admin_session_token,
            coach_session_token=coach_session_token,
            write_to_log=write_to_log,
        )

    @router.get("/api/admin/candidate-lists", response_model=list[CandidateListSummaryResponse])
    def admin_list_candidate_lists(
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.list_admin_candidate_lists(db)

    @router.get("/api/admin/candidate-lists/{list_id}", response_model=CandidateListDetailResponse)
    def admin_get_candidate_list(
        list_id: int,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.get_candidate_list(db, list_id)

    @router.get("/api/admin/candidate-lists/{list_id}/players", response_model=CandidateListPlayersResponse)
    def admin_get_candidate_list_players(
        list_id: int,
        version: str | None = None,
        limit: int = 500,
        offset: int = 0,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.get_candidate_list_players(db, list_id, version=version, limit=limit, offset=offset)

    @router.post("/api/admin/candidate-lists", response_model=CandidateListMutationResponse)
    def admin_create_candidate_list(
        request: CandidateListUpsertRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.create_candidate_list(db, admin, request)

    @router.patch("/api/admin/candidate-lists/{list_id}", response_model=CandidateListMutationResponse)
    def admin_update_candidate_list(
        list_id: int,
        request: CandidateListUpsertRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.update_candidate_list(db, admin, list_id, request)

    @router.post("/api/admin/candidate-lists/{list_id}/publish-preview", response_model=CandidateListPublishPreviewResponse)
    def admin_candidate_list_publish_preview(
        list_id: int,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.publish_preview(db, list_id)

    @router.post("/api/admin/candidate-lists/{list_id}/publish", response_model=CandidateListMutationResponse)
    def admin_publish_candidate_list(
        list_id: int,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.publish_candidate_list(db, admin, list_id)

    @router.post("/api/admin/candidate-lists/{list_id}/unpublish", response_model=CandidateListMutationResponse)
    def admin_unpublish_candidate_list(
        list_id: int,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.unpublish_candidate_list(db, admin, list_id)

    @router.post("/api/admin/candidate-lists/{list_id}/archive", response_model=CandidateListMutationResponse)
    def admin_archive_candidate_list(
        list_id: int,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.archive_candidate_list(db, admin, list_id)

    @router.post("/api/admin/candidate-lists/{list_id}/duplicate", response_model=CandidateListMutationResponse)
    def admin_duplicate_candidate_list(
        list_id: int,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.duplicate_candidate_list(db, admin, list_id)

    @router.post("/api/admin/candidate-lists/{list_id}/lock", response_model=CandidateListMutationResponse)
    def admin_lock_candidate_list(
        list_id: int,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.lock_candidate_list(db, admin, list_id)

    @router.post("/api/admin/candidate-lists/{list_id}/unlock", response_model=CandidateListMutationResponse)
    def admin_unlock_candidate_list(
        list_id: int,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.unlock_candidate_list(db, admin, list_id)

    @router.post("/api/admin/candidate-lists/{list_id}/players/preview", response_model=CandidateListPlayerPreviewResponse)
    def admin_preview_candidate_list_players(
        list_id: int,
        request: CandidateListPlayerPreviewRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.preview_candidate_list_players(db, list_id, request)

    @router.post("/api/admin/candidate-lists/{list_id}/players/commit", response_model=CandidateListMutationResponse)
    def admin_commit_candidate_list_players(
        list_id: int,
        request: CandidateListPlayerCommitRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.commit_candidate_list_players(db, admin, list_id, request)

    @router.post("/api/admin/candidate-lists/{list_id}/players/remove-preview", response_model=CandidateListRemovePreviewResponse)
    def admin_preview_candidate_list_player_removals(
        list_id: int,
        request: CandidateListBatchRemoveRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.preview_candidate_list_player_removals(db, list_id, request)

    @router.post("/api/admin/candidate-lists/{list_id}/players/batch-remove", response_model=CandidateListMutationResponse)
    def admin_remove_candidate_list_players(
        list_id: int,
        request: CandidateListBatchRemoveRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_candidate_list_manager),
    ):
        return candidate_list_service.remove_candidate_list_players(db, admin, list_id, request)

    @router.post("/api/admin/coach-honors", response_model=AdminActionResponse)
    def create_coach_honor(
        request: CoachHonorUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return coach_service.upsert_coach_honor(db, admin, request, write_to_log)

    @router.patch("/api/admin/coach-honors/{honor_id}", response_model=AdminActionResponse)
    def update_coach_honor(
        honor_id: int,
        request: CoachHonorUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return coach_service.upsert_coach_honor(db, admin, request, write_to_log, honor_id=honor_id)

    @router.delete("/api/admin/coach-honors/{honor_id}", response_model=AdminActionResponse)
    def delete_coach_honor(honor_id: int, db: Session = Depends(get_db), admin: str = Depends(verify_schedule_editor)):
        return coach_service.delete_coach_honor(db, admin, honor_id, write_to_log)

    @router.post("/api/admin/coach-assistants", response_model=AdminActionResponse)
    def create_coach_assistant(
        request: CoachAssistantUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return coach_service.upsert_coach_assistant(db, admin, request, write_to_log)

    @router.patch("/api/admin/coach-assistants/{assistant_id}", response_model=AdminActionResponse)
    def update_coach_assistant(
        assistant_id: int,
        request: CoachAssistantUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return coach_service.upsert_coach_assistant(db, admin, request, write_to_log, assistant_id=assistant_id)

    @router.delete("/api/admin/coach-assistants/{assistant_id}", response_model=AdminActionResponse)
    def delete_coach_assistant(assistant_id: int, db: Session = Depends(get_db), admin: str = Depends(verify_schedule_editor)):
        return coach_service.delete_coach_assistant(db, admin, assistant_id, write_to_log)

    @router.post("/api/coach/login", response_model=CoachAccountPublicResponse)
    def coach_login(request: CoachLoginRequest, response: Response, db: Session = Depends(get_db)):
        token, payload = coach_service.login_coach(db, request)
        response.set_cookie(
            key=COACH_SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            secure=COACH_COOKIE_SECURE,
            max_age=int(coach_service.COACH_SESSION_TTL.total_seconds()),
            path="/",
        )
        return payload

    @router.post("/api/coach/logout")
    def coach_logout(
        response: Response,
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        payload = coach_service.logout_coach(db, coach_session_token)
        response.delete_cookie(key=COACH_SESSION_COOKIE_NAME, path="/")
        return payload

    @router.get("/api/coach/check", response_model=CoachAccountPublicResponse)
    def coach_check(
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.get_coach_session_identity(db, coach_session_token)

    @router.patch("/api/coach/me", response_model=AdminActionResponse)
    def update_own_coach_profile(
        request: CoachUpdateRequest,
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.update_own_coach_profile(db, coach_session_token, request, write_to_log)

    @router.patch("/api/coach/me/password", response_model=AdminActionResponse)
    def change_own_coach_password(
        request: CoachPasswordChangeRequest,
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.change_own_coach_password(db, coach_session_token, request, write_to_log)

    @router.patch("/api/coach/me/qq", response_model=AdminActionResponse)
    def bind_own_coach_qq(
        request: CoachQqBindingRequest,
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.bind_own_coach_qq(db, coach_session_token, request, write_to_log)

    @router.post("/api/coach/me/avatar")
    def upload_own_coach_avatar(
        avatar: UploadFile = File(...),
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.save_own_coach_avatar(db, coach_session_token, avatar, write_to_log)

    @router.post("/api/coach/me/team-logo")
    def upload_own_team_logo(
        logo: UploadFile = File(...),
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return team_logo_service.save_own_team_logo(db, coach_session_token, logo, write_to_log)

    @router.post("/api/coach/me/honors", response_model=AdminActionResponse)
    def create_own_coach_honor(
        request: CoachHonorUpdateRequest,
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.upsert_own_coach_honor(db, coach_session_token, request, write_to_log)

    @router.patch("/api/coach/me/honors/{honor_id}", response_model=AdminActionResponse)
    def update_own_coach_honor(
        honor_id: int,
        request: CoachHonorUpdateRequest,
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.upsert_own_coach_honor(db, coach_session_token, request, write_to_log, honor_id=honor_id)

    @router.delete("/api/coach/me/honors/{honor_id}", response_model=AdminActionResponse)
    def delete_own_coach_honor(
        honor_id: int,
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.delete_own_coach_honor(db, coach_session_token, honor_id, write_to_log)

    @router.post("/api/coach/me/assistants", response_model=AdminActionResponse)
    def create_own_coach_assistant(
        request: CoachAssistantUpdateRequest,
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.upsert_own_coach_assistant(db, coach_session_token, request, write_to_log)

    @router.patch("/api/coach/me/assistants/{assistant_id}", response_model=AdminActionResponse)
    def update_own_coach_assistant(
        assistant_id: int,
        request: CoachAssistantUpdateRequest,
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.upsert_own_coach_assistant(db, coach_session_token, request, write_to_log, assistant_id=assistant_id)

    @router.delete("/api/coach/me/assistants/{assistant_id}", response_model=AdminActionResponse)
    def delete_own_coach_assistant(
        assistant_id: int,
        coach_session_token: Optional[str] = Cookie(None, alias=COACH_SESSION_COOKIE_NAME),
        db: Session = Depends(get_db),
    ):
        return coach_service.delete_own_coach_assistant(db, coach_session_token, assistant_id, write_to_log)

    @router.post("/api/admin/import/formal", response_model=AdminImportResponse)
    def import_current_league_data(db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.import_current_league_data(db, admin, write_to_log)

    @router.post("/api/admin/import/upload/roster", response_model=AdminImportResponse)
    async def upload_and_import_roster(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        if not admin:
            raise HTTPException(status_code=401, detail="未授权")
        path = await import_upload_service.save_import_upload(file, "roster")
        return admin_write_service.import_current_league_data(db, admin, write_to_log, workbook_path=path)

    @router.post("/api/admin/import/upload/attributes", response_model=AdminImportResponse)
    async def upload_and_import_attributes(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        if not admin:
            raise HTTPException(status_code=401, detail="未授权")
        path = await import_upload_service.save_import_upload(file, "attributes")
        return admin_write_service.import_player_attributes_data(db, admin, path, write_to_log)

    @router.post("/api/admin/matches/import", response_model=ScheduleImportResponse)
    def import_latest_schedule(db: Session = Depends(get_db), admin: str = Depends(verify_schedule_manager)):
        return admin_write_service.import_latest_schedule(db, admin, write_to_log)

    @router.post("/api/admin/matches/import/upload", response_model=ScheduleImportResponse)
    async def upload_and_import_schedule(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_manager),
    ):
        path = await import_upload_service.save_import_upload(file, "schedule")
        return admin_write_service.import_latest_schedule(db, admin, write_to_log, schedule_path=path)

    @router.patch("/api/admin/matches/batch", response_model=AdminActionResponse)
    def batch_update_match_results(
        request: MatchBatchUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_manager),
    ):
        match_ids = [item.match_id for item in request.matches]
        levels = {
            item.level
            for item in db.query(Match).filter(Match.id.in_(match_ids)).all()
            if item.level
        }
        for level in levels:
            require_level_responsibility(db, admin, level, "schedule")
        return admin_write_service.batch_update_match_results(db, admin, request, write_to_log)

    @router.patch("/api/admin/matches/{match_id}", response_model=AdminActionResponse)
    def update_match_result(
        match_id: int,
        request: MatchUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_manager),
    ):
        match = db.query(Match).filter(Match.id == match_id).first()
        if match:
            require_level_responsibility(db, admin, match.level, "schedule")
        return admin_write_service.update_match_result(db, admin, match_id, request, write_to_log)

    @router.patch("/api/admin/suspensions", response_model=AdminActionResponse)
    def update_suspension_record(
        request: SuspensionRecordUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_suspension_manager),
    ):
        level = suspension_service.get_suspension_request_level(db, request)
        require_level_responsibility(db, admin, level, "suspensions")
        return admin_write_service.update_suspension_record(db, admin, request, write_to_log)

    @router.patch("/api/admin/site-notes/{note_key:path}", response_model=AdminActionResponse)
    def update_site_note(
        note_key: str,
        request: SiteNoteUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_suspension_manager),
    ):
        level = site_note_service.get_suspension_note_level(db, note_key)
        require_level_responsibility(db, admin, level, "suspensions")
        return admin_write_service.update_site_note(db, admin, note_key, request, write_to_log)

    @router.post("/api/admin/cups/{competition}/initialize", response_model=AdminActionResponse)
    def initialize_cup_bracket(
        competition: str,
        reset: bool = False,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_manager),
    ):
        return admin_write_service.initialize_cup_bracket(
            db,
            admin,
            competition,
            write_to_log,
            reset=reset,
        )

    @router.patch("/api/admin/cups/matches/{match_id}/teams", response_model=AdminActionResponse)
    def update_cup_match_teams(
        match_id: int,
        request: CupMatchTeamsUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_manager),
    ):
        return admin_write_service.update_cup_match_teams(db, admin, match_id, request, write_to_log)

    @router.put("/api/admin/cups/{competition}/groups/{group_no}", response_model=AdminActionResponse)
    def update_cup_group(
        competition: str,
        group_no: int,
        request: CupGroupUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_manager),
    ):
        return admin_write_service.update_cup_group(db, admin, competition, group_no, request, write_to_log)

    @router.patch("/api/admin/cups/{competition}/group-matches/{match_id}", response_model=AdminActionResponse)
    def update_cup_group_match_result(
        competition: str,
        match_id: int,
        request: CupGroupMatchResultUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_cup_standings_manager),
    ):
        return admin_write_service.update_cup_group_match_result(db, admin, competition, match_id, request, write_to_log)

    @router.patch("/api/admin/cups/matches/{match_id}/result", response_model=AdminActionResponse)
    def update_cup_match_result(
        match_id: int,
        request: CupMatchResultUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_manager),
    ):
        return admin_write_service.update_cup_match_result(db, admin, match_id, request, write_to_log)

    return router
