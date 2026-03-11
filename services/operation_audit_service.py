import csv
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text

from operation_audit_store import persist_operation_audit

AUDIT_SOURCE_ADMIN_UI = "admin_ui"
AUDIT_SOURCE_LEGACY_LOG = "legacy_log_file"
OPERATION_AUDIT_TABLE = "operation_audits"
LOG_LINE_RE = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+\[(?P<operator>[^\]]+)\]\s+(?P<operation>[^:]+):\s*(?P<details>.*)$"
)

ADMIN_OPERATION_MAP: dict[str, tuple[str, str]] = {
    "登录": ("auth", "login"),
    "登出": ("auth", "logout"),
    "交易": ("transfer", "transfer_player"),
    "海捞": ("transfer", "fish_player"),
    "解约": ("transfer", "release_player"),
    "批量交易": ("transfer", "batch_transfer"),
    "批量解约": ("transfer", "batch_release"),
    "撤销": ("transfer", "undo_operation"),
    "消费": ("roster", "consume_player"),
    "返老": ("roster", "rejuvenate_player"),
    "批量消费": ("roster", "batch_consume"),
    "球队修改": ("roster", "update_team_info"),
    "球员修改": ("roster", "update_player_info"),
    "UID修改": ("roster", "update_player_uid"),
    "重新计算工资": ("maintenance", "recalculate_wages"),
    "球队缓存重算": ("maintenance", "rebuild_team_stat_caches"),
    "正式导入联赛数据": ("import", "formal_import"),
    "正式导入失败": ("import", "formal_import"),
}


def infer_admin_operation_metadata(operation_label: str) -> tuple[str, str]:
    return ADMIN_OPERATION_MAP.get(operation_label, ("admin_write", operation_label.strip().replace(" ", "_").lower() or "unknown"))


def persist_admin_operation_audit(
    target_bind,
    *,
    category: str,
    action: str,
    operator: str | None,
    status: str,
    summary: str,
    source: str = AUDIT_SOURCE_ADMIN_UI,
    operation_label: str | None = None,
    details_text: str | None = None,
    request_payload: dict[str, Any] | None = None,
    response_payload: dict[str, Any] | None = None,
    extra_details: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> bool:
    details: dict[str, Any] = {}
    if operation_label:
        details["operation_label"] = operation_label
    if details_text:
        details["details_text"] = details_text
    if request_payload:
        details["request"] = request_payload
    if response_payload:
        details["response"] = response_payload
    if extra_details:
        details.update(extra_details)

    return persist_operation_audit(
        target_bind,
        category=category,
        action=action,
        status=status,
        source=source,
        operator=operator,
        summary=summary,
        details=details,
        created_at=created_at,
    )


def persist_admin_log_file_event(
    target_bind,
    *,
    operation_label: str,
    operator: str | None,
    details_text: str,
    source: str = AUDIT_SOURCE_LEGACY_LOG,
    created_at: datetime | None = None,
    status: str | None = None,
    extra_details: dict[str, Any] | None = None,
) -> bool:
    category, action = infer_admin_operation_metadata(operation_label)
    normalized_status = status or ("failed" if "失败" in operation_label else "success")
    return persist_admin_operation_audit(
        target_bind,
        category=category,
        action=action,
        operator=operator,
        status=normalized_status,
        source=source,
        summary=details_text,
        operation_label=operation_label,
        details_text=details_text,
        extra_details=extra_details,
        created_at=created_at,
    )


def parse_legacy_admin_log_line(line: str) -> dict[str, Any] | None:
    match = LOG_LINE_RE.match(line.strip())
    if not match:
        return None

    timestamp = datetime.strptime(match.group("timestamp"), "%Y-%m-%d %H:%M:%S")
    operation_label = match.group("operation").strip()
    operator = match.group("operator").strip() or None
    details_text = match.group("details").strip()
    category, action = infer_admin_operation_metadata(operation_label)
    return {
        "timestamp": timestamp,
        "operation_label": operation_label,
        "operator": operator,
        "details_text": details_text,
        "category": category,
        "action": action,
        "status": "failed" if "失败" in operation_label else "success",
    }


def import_legacy_admin_log_to_operation_audits(target_bind, log_path: str | Path) -> dict[str, int]:
    if target_bind is None:
        return {"imported": 0, "skipped": 0}

    path = Path(log_path)
    if not path.exists():
        return {"imported": 0, "skipped": 0}

    with path.open("r", encoding="utf-8", errors="replace") as log_file:
        parsed_lines = [parsed for parsed in (parse_legacy_admin_log_line(line) for line in log_file) if parsed]

    if not parsed_lines:
        return {"imported": 0, "skipped": 0}

    with target_bind.connect() as conn:
        if not inspect(conn).has_table(OPERATION_AUDIT_TABLE):
            return {"imported": 0, "skipped": 0}
        rows = conn.execute(
            text(
                """
                SELECT created_at, operator, action
                FROM operation_audits
                WHERE category != 'schema_bootstrap'
                """
            )
        ).fetchall()

    existing_signatures = {
        (
            created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(created_at, "strftime") else str(created_at).split(".")[0],
            operator or "",
            action,
        )
        for created_at, operator, action in rows
    }

    imported = 0
    skipped = 0
    for parsed in parsed_lines:
        created_at_text = parsed["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        signature = (
            created_at_text,
            parsed["operator"] or "",
            parsed["action"],
        )
        if signature in existing_signatures:
            skipped += 1
            continue
        persist_admin_log_file_event(
            target_bind,
            operation_label=parsed["operation_label"],
            operator=parsed["operator"],
            details_text=parsed["details_text"],
            source=AUDIT_SOURCE_LEGACY_LOG,
            created_at=parsed["timestamp"],
            status=parsed["status"],
            extra_details={"legacy_log_path": str(path)},
        )
        existing_signatures.add(signature)
        imported += 1

    return {"imported": imported, "skipped": skipped}


def export_operation_audits_csv(records: list[Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "created_at",
            "category",
            "action",
            "operation_label",
            "status",
            "source",
            "operator",
            "summary",
            "details_json",
        ]
    )
    for record in records:
        details_json = getattr(record, "details_json", None)
        if details_json is None:
            details_json = ""
        details = getattr(record, "details", None)
        operation_label = details.get("operation_label", "") if isinstance(details, dict) else ""
        writer.writerow(
            [
                getattr(record, "id", ""),
                getattr(record, "created_at", "") or "",
                getattr(record, "category", ""),
                getattr(record, "action", ""),
                operation_label,
                getattr(record, "status", ""),
                getattr(record, "source", ""),
                getattr(record, "operator", "") or "",
                getattr(record, "summary", ""),
                details_json,
            ]
        )
    return output.getvalue()
