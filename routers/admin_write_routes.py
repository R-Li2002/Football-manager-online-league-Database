from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from schemas_write import (
    AdminActionResponse,
    AdminImportResponse,
    BatchActionResponse,
    BatchConsumeRequest,
    BatchReleaseRequest,
    BatchTransferRequest,
    ConsumeRequest,
    FishPlayerRequest,
    LoginResponse,
    LoginRequest,
    LogoutResponse,
    PlayerUpdateRequest,
    RejuvenateRequest,
    TeamUpdateRequest,
    TransferRequest,
    UpdateUidRequest,
)
from services import admin_write_service, auth_service


def build_admin_write_router(
    get_db,
    verify_admin,
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

    @router.post("/api/admin/import/formal", response_model=AdminImportResponse)
    def import_current_league_data(db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        return admin_write_service.import_current_league_data(db, admin, write_to_log)

    return router
