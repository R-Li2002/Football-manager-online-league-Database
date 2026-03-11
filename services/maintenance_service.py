import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

MAINTENANCE_STATUS_FILE = "maintenance_status.json"
MAINTENANCE_ROOT_ENV = "HEIGO_IMPORT_ROOT"

PLAN_PROGRESS = {
    "overall_percent": 91,
    "overall_summary": "Phase 1 已完成，Phase 2 基本完成，Phase 3 进入后段。",
    "phases": [
        {
            "phase": "phase_1",
            "label": "Phase 1 低风险治理",
            "percent": 100,
            "status": "completed",
            "summary": "审计、索引、安全加固、类型化约束和基础测试都已落地。",
        },
        {
            "phase": "phase_2",
            "label": "Phase 2 数据一致性改造",
            "percent": 98,
            "status": "completed",
            "summary": "team_id、transfer_logs 团队 ID、严格导入、孤立旧球队清理和增量统计都已完成。",
        },
        {
            "phase": "phase_3",
            "label": "Phase 3 架构拆分与联机能力增强",
            "percent": 80,
            "status": "in_progress",
            "summary": "routers/services/static 已拆开，剩余重点是 migration、repository 层和规模化运维能力。",
        },
    ],
}


def resolve_maintenance_root() -> Path:
    configured_root = os.environ.get(MAINTENANCE_ROOT_ENV)
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def maintenance_status_path() -> Path:
    return resolve_maintenance_root() / MAINTENANCE_STATUS_FILE


def load_maintenance_status() -> dict[str, Any]:
    path = maintenance_status_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_formal_import_status(import_payload: dict[str, Any]) -> None:
    path = maintenance_status_path()
    status = load_maintenance_status()
    status["last_formal_import"] = import_payload
    status["updated_at"] = datetime.now().isoformat()
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def build_import_summary(import_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not import_payload:
        return {
            "available": False,
            "success": False,
            "message": "暂无正式导入记录",
            "workbook_path": "",
            "attributes_csv_path": "",
            "backup_path": None,
            "committed": False,
            "strict_mode": True,
            "executed_at": None,
            "created_total": 0,
            "updated_total": 0,
            "unchanged_total": 0,
            "skipped_total": 0,
            "cleaned_total": 0,
            "datasets": {},
        }

    datasets = import_payload.get("datasets", {})
    created_total = sum(int(item.get("created", 0)) for item in datasets.values())
    updated_total = sum(int(item.get("updated", 0)) for item in datasets.values())
    unchanged_total = sum(int(item.get("unchanged", 0)) for item in datasets.values())
    skipped_total = sum(int(item.get("skipped", 0)) for item in datasets.values())
    cleaned_total = int(datasets.get("team_cleanup", {}).get("details", {}).get("removed_count", 0))

    return {
        "available": True,
        "success": bool(import_payload.get("success")),
        "message": import_payload.get("message", ""),
        "workbook_path": import_payload.get("workbook_path", ""),
        "attributes_csv_path": import_payload.get("attributes_csv_path", ""),
        "backup_path": import_payload.get("backup_path"),
        "committed": bool(import_payload.get("committed")),
        "strict_mode": bool(import_payload.get("strict_mode", True)),
        "executed_at": load_maintenance_status().get("updated_at"),
        "created_total": created_total,
        "updated_total": updated_total,
        "unchanged_total": unchanged_total,
        "skipped_total": skipped_total,
        "cleaned_total": cleaned_total,
        "datasets": datasets,
    }


def build_maintenance_status_payload() -> dict[str, Any]:
    status = load_maintenance_status()
    return {
        "plan_progress": PLAN_PROGRESS,
        "last_formal_import": build_import_summary(status.get("last_formal_import")),
    }
