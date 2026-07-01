import os
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, File, Request, Response, UploadFile
from sqlalchemy.orm import Session

from schemas_read import CoachAccountAdminResponse, CoachAccountPublicResponse
from schemas_write import (
    AdminActionResponse,
    AdminImportResponse,
    BatchActionResponse,
    BatchConsumeRequest,
    BatchReleaseRequest,
    BatchTransferRequest,
    ConsumeRequest,
    CoachAccountUpsertRequest,
    CoachAssistantUpdateRequest,
    CoachLoginRequest,
    CoachPasswordChangeRequest,
    CoachHonorUpdateRequest,
    CoachUpdateRequest,
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
    ScheduleImportResponse,
    SiteNoteUpdateRequest,
    SuspensionRecordUpdateRequest,
    TeamUpdateRequest,
    TransferRequest,
    UpdateUidRequest,
)
from services import admin_write_service, auth_service, coach_service, team_logo_service

COACH_SESSION_COOKIE_NAME = "coach_session_token"
COACH_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"}


def build_admin_write_router(
    get_db,
    verify_admin,
    verify_schedule_editor,
    set_session_cookie,
    clear_session_cookie,
    write_to_log,
):
    router = APIRouter()

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

    @router.post("/api/admin/matches/import", response_model=ScheduleImportResponse)
    def import_latest_schedule(db: Session = Depends(get_db), admin: str = Depends(verify_schedule_editor)):
        return admin_write_service.import_latest_schedule(db, admin, write_to_log)

    @router.patch("/api/admin/matches/batch", response_model=AdminActionResponse)
    def batch_update_match_results(
        request: MatchBatchUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return admin_write_service.batch_update_match_results(db, admin, request, write_to_log)

    @router.patch("/api/admin/matches/{match_id}", response_model=AdminActionResponse)
    def update_match_result(
        match_id: int,
        request: MatchUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return admin_write_service.update_match_result(db, admin, match_id, request, write_to_log)

    @router.patch("/api/admin/suspensions", response_model=AdminActionResponse)
    def update_suspension_record(
        request: SuspensionRecordUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return admin_write_service.update_suspension_record(db, admin, request, write_to_log)

    @router.patch("/api/admin/site-notes/{note_key:path}", response_model=AdminActionResponse)
    def update_site_note(
        note_key: str,
        request: SiteNoteUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return admin_write_service.update_site_note(db, admin, note_key, request, write_to_log)

    @router.post("/api/admin/cups/{competition}/initialize", response_model=AdminActionResponse)
    def initialize_cup_bracket(
        competition: str,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return admin_write_service.initialize_cup_bracket(db, admin, competition, write_to_log)

    @router.patch("/api/admin/cups/matches/{match_id}/teams", response_model=AdminActionResponse)
    def update_cup_match_teams(
        match_id: int,
        request: CupMatchTeamsUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return admin_write_service.update_cup_match_teams(db, admin, match_id, request, write_to_log)

    @router.patch("/api/admin/cups/matches/{match_id}/result", response_model=AdminActionResponse)
    def update_cup_match_result(
        match_id: int,
        request: CupMatchResultUpdateRequest,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_schedule_editor),
    ):
        return admin_write_service.update_cup_match_result(db, admin, match_id, request, write_to_log)

    return router
