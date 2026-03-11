from typing import Any, Callable

from fastapi import HTTPException
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
    PlayerUpdateRequest,
    RejuvenateRequest,
    TeamUpdateRequest,
    TransferRequest,
    UpdateUidRequest,
)
from services import import_service, roster_service, transfer_service, wage_service
from services.operation_audit_service import AUDIT_SOURCE_ADMIN_UI, persist_admin_operation_audit


def _to_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return value
    return {"value": value}


def _persist_admin_write_audit(
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


def _execute_admin_action(
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
        raw_payload = _to_payload(executor())
    except HTTPException as exc:
        failure_summary = str(exc.detail)
        _persist_admin_write_audit(
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
        failure_summary = f"{operation_label}异常中断: {type(exc).__name__}: {exc}"
        _persist_admin_write_audit(
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
    summary = response_payload.get("message") or f"{operation_label}已执行"
    _persist_admin_write_audit(
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


def transfer_player(
    db: Session,
    admin: str | None,
    request: TransferRequest,
    write_to_log,
) -> AdminActionResponse:
    return _execute_admin_action(
        db,
        category="transfer",
        action="transfer_player",
        operation_label="交易",
        operator=admin,
        request_payload=_to_payload(request),
        executor=lambda: transfer_service.transfer_player(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def fish_player(
    db: Session,
    admin: str | None,
    request: FishPlayerRequest,
    write_to_log,
) -> AdminActionResponse:
    return _execute_admin_action(
        db,
        category="transfer",
        action="fish_player",
        operation_label="海捞",
        operator=admin,
        request_payload=_to_payload(request),
        executor=lambda: transfer_service.fish_player(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def release_player(
    db: Session,
    admin: str | None,
    request: TransferRequest,
    write_to_log,
) -> AdminActionResponse:
    return _execute_admin_action(
        db,
        category="transfer",
        action="release_player",
        operation_label="解约",
        operator=admin,
        request_payload=_to_payload(request),
        executor=lambda: transfer_service.release_player(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def consume_player(
    db: Session,
    admin: str | None,
    request: ConsumeRequest,
    write_to_log,
) -> AdminActionResponse:
    return _execute_admin_action(
        db,
        category="roster",
        action="consume_player",
        operation_label="消费",
        operator=admin,
        request_payload=_to_payload(request),
        executor=lambda: roster_service.consume_player(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def rejuvenate_player(
    db: Session,
    admin: str | None,
    request: RejuvenateRequest,
    write_to_log,
) -> AdminActionResponse:
    return _execute_admin_action(
        db,
        category="roster",
        action="rejuvenate_player",
        operation_label="返老",
        operator=admin,
        request_payload=_to_payload(request),
        executor=lambda: roster_service.rejuvenate_player(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def batch_transfer(
    db: Session,
    admin: str | None,
    request: BatchTransferRequest,
    write_to_log,
) -> BatchActionResponse:
    return _execute_admin_action(
        db,
        category="transfer",
        action="batch_transfer",
        operation_label="批量交易",
        operator=admin,
        request_payload=_to_payload(request),
        executor=lambda: transfer_service.batch_transfer(db, admin, request, write_to_log),
        response_model=BatchActionResponse,
    )


def batch_consume(
    db: Session,
    admin: str | None,
    request: BatchConsumeRequest,
    write_to_log,
) -> BatchActionResponse:
    return _execute_admin_action(
        db,
        category="roster",
        action="batch_consume",
        operation_label="批量消费",
        operator=admin,
        request_payload=_to_payload(request),
        executor=lambda: roster_service.batch_consume(db, admin, request, write_to_log),
        response_model=BatchActionResponse,
    )


def batch_release(
    db: Session,
    admin: str | None,
    request: BatchReleaseRequest,
    write_to_log,
) -> BatchActionResponse:
    return _execute_admin_action(
        db,
        category="transfer",
        action="batch_release",
        operation_label="批量解约",
        operator=admin,
        request_payload=_to_payload(request),
        executor=lambda: transfer_service.batch_release(db, admin, request, write_to_log),
        response_model=BatchActionResponse,
    )


def undo_operation(
    db: Session,
    admin: str | None,
    log_id: int,
    write_to_log,
) -> AdminActionResponse:
    return _execute_admin_action(
        db,
        category="transfer",
        action="undo_operation",
        operation_label="撤销",
        operator=admin,
        request_payload={"log_id": log_id},
        executor=lambda: transfer_service.undo_operation(db, admin, log_id, write_to_log),
        response_model=AdminActionResponse,
    )


def update_team_info(
    db: Session,
    admin: str | None,
    request: TeamUpdateRequest,
    write_to_log,
) -> AdminActionResponse:
    return _execute_admin_action(
        db,
        category="roster",
        action="update_team_info",
        operation_label="球队修改",
        operator=admin,
        request_payload=_to_payload(request),
        executor=lambda: roster_service.update_team_info(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def update_player_info(
    db: Session,
    admin: str | None,
    request: PlayerUpdateRequest,
    write_to_log,
) -> AdminActionResponse:
    return _execute_admin_action(
        db,
        category="roster",
        action="update_player_info",
        operation_label="球员修改",
        operator=admin,
        request_payload=_to_payload(request),
        executor=lambda: roster_service.update_player_info(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def update_player_uid(
    db: Session,
    admin: str | None,
    request: UpdateUidRequest,
    write_to_log,
) -> AdminActionResponse:
    return _execute_admin_action(
        db,
        category="roster",
        action="update_player_uid",
        operation_label="UID修改",
        operator=admin,
        request_payload=_to_payload(request),
        executor=lambda: roster_service.update_player_uid(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def recalculate_wages(
    db: Session,
    admin: str | None,
    write_to_log,
) -> AdminActionResponse:
    return _execute_admin_action(
        db,
        category="maintenance",
        action="recalculate_wages",
        operation_label="重新计算工资",
        operator=admin,
        request_payload=None,
        executor=lambda: wage_service.recalculate_wages(db, admin, write_to_log),
        response_model=AdminActionResponse,
        extra_details_getter=lambda payload: payload.get("audit_details"),
    )


def rebuild_team_stat_caches(
    db: Session,
    admin: str | None,
    write_to_log,
) -> AdminActionResponse:
    return _execute_admin_action(
        db,
        category="maintenance",
        action="rebuild_team_stat_caches",
        operation_label="球队缓存重算",
        operator=admin,
        request_payload=None,
        executor=lambda: wage_service.rebuild_team_stat_caches(db, admin, write_to_log),
        response_model=AdminActionResponse,
        extra_details_getter=lambda payload: payload.get("audit_details"),
    )


def import_current_league_data(
    db: Session,
    admin: str | None,
    write_to_log,
) -> AdminImportResponse:
    bind = db.get_bind()
    return _execute_admin_action(
        db,
        category="import",
        action="formal_import",
        operation_label="正式导入联赛数据",
        operator=admin,
        request_payload=None,
        executor=lambda: import_service.import_current_league_data(db, admin, write_to_log),
        response_model=AdminImportResponse,
        bind_override=bind,
    )
