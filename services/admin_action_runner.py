from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from services.admin_common import LogWriter, require_admin
from services.league_service import create_transfer_log, persist_with_team_stats
from services.operation_audit_service import AUDIT_SOURCE_ADMIN_UI, persist_admin_operation_audit


@dataclass
class AdminMutationResult:
    message: str
    log_action: str
    log_detail: str
    affected_team_ids: set[int | None] = field(default_factory=set)
    stat_scopes: Iterable[str] | None = None
    transfer_logs: list[dict[str, Any]] = field(default_factory=list)
    response_payload: dict[str, Any] = field(default_factory=dict)


def to_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return value
    return {"value": value}


def persist_admin_write_audit(
    db: Session,
    *,
    category: str,
    action: str,
    operation_label: str,
    operator: str | None,
    status: str,
    summary: str,
    request_payload: dict[str, Any] | None = None,
    response_payload: dict[str, Any] | None = None,
    extra_details: dict[str, Any] | None = None,
    bind_override=None,
) -> None:
    bind = bind_override or db.get_bind()
    if bind is None:
        return
    persist_admin_operation_audit(
        bind,
        category=category,
        action=action,
        operator=operator,
        status=status,
        summary=summary,
        source=AUDIT_SOURCE_ADMIN_UI,
        operation_label=operation_label,
        details_text=summary,
        request_payload=request_payload,
        response_payload=response_payload,
        extra_details=extra_details,
    )


def execute_admin_action(
    db: Session,
    *,
    category: str,
    action: str,
    operation_label: str,
    operator: str | None,
    request_payload: dict[str, Any] | None,
    executor: Callable[[], Any],
    response_model,
    bind_override=None,
    extra_details_getter: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
):
    try:
        raw_payload = to_payload(executor())
    except HTTPException as exc:
        db.rollback()
        failure_summary = str(exc.detail)
        persist_admin_write_audit(
            db,
            category=category,
            action=action,
            operation_label=operation_label,
            operator=operator,
            status="failed",
            summary=failure_summary,
            request_payload=request_payload,
            response_payload={"success": False, "detail": exc.detail},
            extra_details={"http_status": exc.status_code},
            bind_override=bind_override,
        )
        raise
    except Exception as exc:
        db.rollback()
        failure_summary = f"{operation_label} aborted: {type(exc).__name__}: {exc}"
        persist_admin_write_audit(
            db,
            category=category,
            action=action,
            operation_label=operation_label,
            operator=operator,
            status="failed",
            summary=failure_summary,
            request_payload=request_payload,
            response_payload={"success": False, "detail": str(exc)},
            extra_details={"exception_type": type(exc).__name__},
            bind_override=bind_override,
        )
        raise

    response = response_model.model_validate(raw_payload)
    response_payload = response.model_dump(mode="json")
    extra_details = extra_details_getter(raw_payload) if extra_details_getter else None
    summary = response_payload.get("message") or f"{operation_label} completed"
    persist_admin_write_audit(
        db,
        category=category,
        action=action,
        operation_label=operation_label,
        operator=operator,
        status="success" if response_payload.get("success", True) else "failed",
        summary=summary,
        request_payload=request_payload,
        response_payload=response_payload,
        extra_details=extra_details,
        bind_override=bind_override,
    )
    return response


def run_admin_mutation(
    db: Session,
    admin: str | None,
    write_to_log: LogWriter,
    *,
    mutator: Callable[[str], AdminMutationResult],
) -> dict[str, Any]:
    operator = require_admin(admin)
    result = mutator(operator)

    for transfer_log_payload in result.transfer_logs:
        create_transfer_log(
            db,
            operator=operator,
            **transfer_log_payload,
        )

    if result.affected_team_ids:
        persist_with_team_stats(
            db,
            affected_team_ids=result.affected_team_ids,
            stat_scopes=result.stat_scopes,
        )
    else:
        db.commit()

    write_to_log(result.log_action, result.log_detail, operator)

    payload = {"success": True, "message": result.message}
    payload.update(result.response_payload)
    return payload
