from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from repositories.operation_audit_repository import get_latest_operation_audit, list_operation_audits, list_recent_operation_audits
from repositories.transfer_log_repository import list_recent_transfer_logs
from schemas_read import DataFeedbackReportResponse, LogsResponse, OperationAuditResponse, SchemaBootstrapStatusResponse
from schemas_write import AdminImportResponse
from services.data_feedback_service import get_data_feedback_reports
from services.operation_audit_service import export_operation_audits_csv


def get_transfer_logs(db: Session):
    return list_recent_transfer_logs(db, limit=100)


def get_recent_logs(log_file: str, limit: int = 200) -> LogsResponse:
    if not log_file:
        return LogsResponse(logs="")
    try:
        with open(log_file, "r", encoding="utf-8") as log_stream:
            content = log_stream.read()
    except FileNotFoundError:
        return LogsResponse(logs="")

    lines = content.strip().split("\n")
    recent_lines = lines[-limit:] if len(lines) > limit else lines
    return LogsResponse(logs="\n".join(recent_lines))


def get_schema_bootstrap_status(log_path: str | Path, limit: int = 5) -> SchemaBootstrapStatusResponse:
    resolved_log_path = Path(log_path)
    if not resolved_log_path.exists():
        return SchemaBootstrapStatusResponse(
            log_path=str(resolved_log_path),
            file_exists=False,
            latest_event=None,
            recent_events=[],
        )

    with resolved_log_path.open("r", encoding="utf-8", errors="replace") as log_stream:
        lines = [line.strip() for line in log_stream.readlines() if line.strip()]

    recent_events = lines[-limit:] if len(lines) > limit else lines
    latest_event = recent_events[-1] if recent_events else None
    return SchemaBootstrapStatusResponse(
        log_path=str(resolved_log_path),
        file_exists=True,
        latest_event=latest_event,
        recent_events=recent_events,
    )


def expand_operation_audit_details(details: dict | None) -> dict:
    if not isinstance(details, dict):
        return {}

    response_payload = details.get("response")
    if not isinstance(response_payload, dict):
        return details

    merged = dict(response_payload)
    merged.update(details)
    return merged


def build_operation_audit_response(record) -> OperationAuditResponse:
    details = expand_operation_audit_details(record.details)
    return OperationAuditResponse(
        id=record.id,
        category=record.category,
        action=record.action,
        operation_label=details.get("operation_label") if isinstance(details, dict) else None,
        status=record.status,
        source=record.source,
        operator=record.operator,
        summary=record.summary,
        details=details,
        created_at=record.created_at,
    )


def get_recent_operation_audits(db: Session, limit: int = 20, category: str | None = None) -> list[OperationAuditResponse]:
    return [build_operation_audit_response(record) for record in list_recent_operation_audits(db, limit=limit, category=category)]


def get_latest_formal_import_summary(db: Session) -> dict | None:
    record = get_latest_operation_audit(db, category="import", action="formal_import", source="admin_ui")
    if not record:
        record = get_latest_operation_audit(db, category="import", action="formal_import")
    if not record:
        return None
    return expand_operation_audit_details(record.details) or None


def get_latest_formal_import_response(db: Session) -> Optional[AdminImportResponse]:
    details = get_latest_formal_import_summary(db)
    if not details:
        return None
    return AdminImportResponse.model_validate(details)


def export_operation_audits_report(db: Session, category: str | None = None, limit: int | None = None) -> str:
    records = list_operation_audits(db, category=category, limit=limit)
    return export_operation_audits_csv(records)


def get_recent_data_feedback_reports(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[DataFeedbackReportResponse]:
    return get_data_feedback_reports(db, status=status, limit=limit)
