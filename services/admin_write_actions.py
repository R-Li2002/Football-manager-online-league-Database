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
from services.admin_action_runner import execute_admin_action, to_payload

TRADE_LABEL = "\u4ea4\u6613"
FISH_LABEL = "\u6d77\u635e"
RELEASE_LABEL = "\u89e3\u7ea6"
CONSUME_LABEL = "\u6d88\u8d39"
REJUVENATE_LABEL = "\u8fd4\u8001"
BATCH_TRADE_LABEL = "\u6279\u91cf\u4ea4\u6613"
BATCH_CONSUME_LABEL = "\u6279\u91cf\u6d88\u8d39"
BATCH_RELEASE_LABEL = "\u6279\u91cf\u89e3\u7ea6"
UNDO_LABEL = "\u64a4\u9500"
TEAM_UPDATE_LABEL = "\u7403\u961f\u4fee\u6539"
PLAYER_UPDATE_LABEL = "\u7403\u5458\u4fee\u6539"
UID_UPDATE_LABEL = "UID\u4fee\u6539"
RECALCULATE_WAGES_LABEL = "\u91cd\u65b0\u8ba1\u7b97\u5de5\u8d44"
REBUILD_TEAM_STATS_LABEL = "\u7403\u961f\u7f13\u5b58\u91cd\u7b97"
FORMAL_IMPORT_LABEL = "\u6b63\u5f0f\u5bfc\u5165\u8054\u8d5b\u6570\u636e"


def transfer_player(
    db: Session,
    admin: str | None,
    request: TransferRequest,
    write_to_log,
) -> AdminActionResponse:
    return execute_admin_action(
        db,
        category="transfer",
        action="transfer_player",
        operation_label=TRADE_LABEL,
        operator=admin,
        request_payload=to_payload(request),
        executor=lambda: transfer_service.transfer_player(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def fish_player(
    db: Session,
    admin: str | None,
    request: FishPlayerRequest,
    write_to_log,
) -> AdminActionResponse:
    return execute_admin_action(
        db,
        category="transfer",
        action="fish_player",
        operation_label=FISH_LABEL,
        operator=admin,
        request_payload=to_payload(request),
        executor=lambda: transfer_service.fish_player(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def release_player(
    db: Session,
    admin: str | None,
    request: TransferRequest,
    write_to_log,
) -> AdminActionResponse:
    return execute_admin_action(
        db,
        category="transfer",
        action="release_player",
        operation_label=RELEASE_LABEL,
        operator=admin,
        request_payload=to_payload(request),
        executor=lambda: transfer_service.release_player(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def consume_player(
    db: Session,
    admin: str | None,
    request: ConsumeRequest,
    write_to_log,
) -> AdminActionResponse:
    return execute_admin_action(
        db,
        category="roster",
        action="consume_player",
        operation_label=CONSUME_LABEL,
        operator=admin,
        request_payload=to_payload(request),
        executor=lambda: roster_service.consume_player(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def rejuvenate_player(
    db: Session,
    admin: str | None,
    request: RejuvenateRequest,
    write_to_log,
) -> AdminActionResponse:
    return execute_admin_action(
        db,
        category="roster",
        action="rejuvenate_player",
        operation_label=REJUVENATE_LABEL,
        operator=admin,
        request_payload=to_payload(request),
        executor=lambda: roster_service.rejuvenate_player(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def batch_transfer(
    db: Session,
    admin: str | None,
    request: BatchTransferRequest,
    write_to_log,
) -> BatchActionResponse:
    return execute_admin_action(
        db,
        category="transfer",
        action="batch_transfer",
        operation_label=BATCH_TRADE_LABEL,
        operator=admin,
        request_payload=to_payload(request),
        executor=lambda: transfer_service.batch_transfer(db, admin, request, write_to_log),
        response_model=BatchActionResponse,
    )


def batch_consume(
    db: Session,
    admin: str | None,
    request: BatchConsumeRequest,
    write_to_log,
) -> BatchActionResponse:
    return execute_admin_action(
        db,
        category="roster",
        action="batch_consume",
        operation_label=BATCH_CONSUME_LABEL,
        operator=admin,
        request_payload=to_payload(request),
        executor=lambda: roster_service.batch_consume(db, admin, request, write_to_log),
        response_model=BatchActionResponse,
    )


def batch_release(
    db: Session,
    admin: str | None,
    request: BatchReleaseRequest,
    write_to_log,
) -> BatchActionResponse:
    return execute_admin_action(
        db,
        category="transfer",
        action="batch_release",
        operation_label=BATCH_RELEASE_LABEL,
        operator=admin,
        request_payload=to_payload(request),
        executor=lambda: transfer_service.batch_release(db, admin, request, write_to_log),
        response_model=BatchActionResponse,
    )


def undo_operation(
    db: Session,
    admin: str | None,
    log_id: int,
    write_to_log,
) -> AdminActionResponse:
    return execute_admin_action(
        db,
        category="transfer",
        action="undo_operation",
        operation_label=UNDO_LABEL,
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
    return execute_admin_action(
        db,
        category="roster",
        action="update_team_info",
        operation_label=TEAM_UPDATE_LABEL,
        operator=admin,
        request_payload=to_payload(request),
        executor=lambda: roster_service.update_team_info(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def update_player_info(
    db: Session,
    admin: str | None,
    request: PlayerUpdateRequest,
    write_to_log,
) -> AdminActionResponse:
    return execute_admin_action(
        db,
        category="roster",
        action="update_player_info",
        operation_label=PLAYER_UPDATE_LABEL,
        operator=admin,
        request_payload=to_payload(request),
        executor=lambda: roster_service.update_player_info(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def update_player_uid(
    db: Session,
    admin: str | None,
    request: UpdateUidRequest,
    write_to_log,
) -> AdminActionResponse:
    return execute_admin_action(
        db,
        category="roster",
        action="update_player_uid",
        operation_label=UID_UPDATE_LABEL,
        operator=admin,
        request_payload=to_payload(request),
        executor=lambda: roster_service.update_player_uid(db, admin, request, write_to_log),
        response_model=AdminActionResponse,
    )


def recalculate_wages(
    db: Session,
    admin: str | None,
    write_to_log,
) -> AdminActionResponse:
    return execute_admin_action(
        db,
        category="maintenance",
        action="recalculate_wages",
        operation_label=RECALCULATE_WAGES_LABEL,
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
    return execute_admin_action(
        db,
        category="maintenance",
        action="rebuild_team_stat_caches",
        operation_label=REBUILD_TEAM_STATS_LABEL,
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
    return execute_admin_action(
        db,
        category="import",
        action="formal_import",
        operation_label=FORMAL_IMPORT_LABEL,
        operator=admin,
        request_payload=None,
        executor=lambda: import_service.import_current_league_data(db, admin, write_to_log),
        response_model=AdminImportResponse,
        bind_override=bind,
    )
