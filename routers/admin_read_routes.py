from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from schemas_read import (
    AuthStatusResponse,
    LogsResponse,
    OperationAuditResponse,
    PlayerResponse,
    SchemaBootstrapStatusResponse,
    TeamInfoResponse,
    TransferLogResponse,
)
from schemas_write import AdminImportResponse
from services import auth_service, read_service


def build_admin_read_router(get_db, verify_admin, log_file: str):
    router = APIRouter()

    def require_admin(admin: str | None) -> str:
        if not admin:
            raise HTTPException(status_code=401, detail="未授权")
        return admin

    @router.get("/api/admin/check", response_model=AuthStatusResponse)
    def check_admin(admin: str = Depends(verify_admin)):
        return auth_service.get_auth_status(admin)

    @router.get("/api/admin/sea-players", response_model=list[PlayerResponse])
    def get_sea_players(db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        require_admin(admin)
        return read_service.get_sea_players(db)

    @router.get("/api/admin/transfer-logs", response_model=list[TransferLogResponse])
    def get_transfer_logs(db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        require_admin(admin)
        return read_service.get_transfer_logs(db)

    @router.get("/api/admin/team/{team_name:path}", response_model=TeamInfoResponse)
    def get_team_info(team_name: str, db: Session = Depends(get_db), admin: str = Depends(verify_admin)):
        require_admin(admin)
        return read_service.get_team_info(db, team_name)

    @router.get("/api/admin/logs", response_model=LogsResponse)
    def get_log_file(admin: str = Depends(verify_admin)):
        require_admin(admin)
        return read_service.get_recent_logs(log_file)

    @router.get("/api/admin/schema-bootstrap-status", response_model=SchemaBootstrapStatusResponse)
    def get_schema_bootstrap_status(admin: str = Depends(verify_admin)):
        require_admin(admin)
        return read_service.get_schema_bootstrap_status()

    @router.get("/api/admin/operations-audit", response_model=list[OperationAuditResponse])
    def get_operations_audit(
        limit: int = 20,
        category: str | None = None,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        require_admin(admin)
        return read_service.get_recent_operation_audits(db, limit=limit, category=category)

    @router.get("/api/admin/operations-audit/export")
    def export_operations_audit(
        category: str | None = None,
        limit: int | None = None,
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        require_admin(admin)
        csv_text = read_service.export_operation_audits_report(db, category=category, limit=limit)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        category_suffix = category or "all"
        filename = f"operation_audits_{category_suffix}_{timestamp}.csv"
        return Response(
            content="\ufeff" + csv_text,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/api/admin/import/latest", response_model=AdminImportResponse | None)
    def get_latest_formal_import(
        db: Session = Depends(get_db),
        admin: str = Depends(verify_admin),
    ):
        require_admin(admin)
        return read_service.get_latest_formal_import_response(db)

    return router
