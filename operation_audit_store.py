import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text

AUDIT_TABLE_NAME = "operation_audits"


def _json_default(value: Any):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def serialize_audit_details(details: dict[str, Any] | None) -> str:
    return json.dumps(details or {}, ensure_ascii=False, sort_keys=True, default=_json_default)


def persist_operation_audit(
    target_bind,
    *,
    category: str,
    action: str,
    status: str,
    summary: str,
    operator: str | None = None,
    source: str = "system",
    details: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> bool:
    if target_bind is None:
        return False

    created_at = created_at or datetime.now()
    details_json = serialize_audit_details(details)
    created_at_param = created_at
    if getattr(target_bind.dialect, "name", "") == "sqlite":
        created_at_param = created_at.isoformat(sep=" ")

    with target_bind.begin() as conn:
        if not inspect(conn).has_table(AUDIT_TABLE_NAME):
            return False
        conn.execute(
            text(
                """
                INSERT INTO operation_audits (
                    category, action, status, source, operator, summary, details_json, created_at
                ) VALUES (
                    :category, :action, :status, :source, :operator, :summary, :details_json, :created_at
                )
                """
            ),
            {
                "category": category,
                "action": action,
                "status": status,
                "source": source,
                "operator": operator,
                "summary": summary,
                "details_json": details_json,
                "created_at": created_at_param,
            },
        )
    return True
