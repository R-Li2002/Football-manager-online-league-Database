import os
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from import_data import run_import
from schemas_write import AdminImportResponse, ImportDatasetSummaryResponse
from services.admin_common import LogWriter, require_admin

IMPORT_ROOT_ENV = "HEIGO_IMPORT_ROOT"
BACKUP_ROOT_ENV = "HEIGO_BACKUP_ROOT"


def resolve_import_root() -> Path:
    configured_root = os.environ.get(IMPORT_ROOT_ENV)
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def resolve_backup_root(engine: Engine, import_root: Path) -> Path:
    configured_root = os.environ.get(BACKUP_ROOT_ENV)
    if configured_root:
        return Path(configured_root).expanduser().resolve()

    if engine.dialect.name == "sqlite":
        database_path = engine.url.database
        if database_path and database_path != ":memory:":
            source_path = Path(database_path)
            if not source_path.is_absolute():
                source_path = (Path(__file__).resolve().parents[1] / source_path).resolve()
            return source_path.parent / "backups"

    return import_root


def backup_sqlite_database(engine: Engine, backup_root: Path) -> str | None:
    if engine.dialect.name != "sqlite":
        return None

    database_path = engine.url.database
    if not database_path or database_path == ":memory:":
        return None

    source_path = Path(database_path)
    if not source_path.is_absolute():
        source_path = (Path(__file__).resolve().parents[1] / source_path).resolve()
    if not source_path.exists():
        return None

    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_root / f"fm_league_backup_{timestamp}.db"

    with sqlite3.connect(str(source_path)) as source_conn, sqlite3.connect(str(backup_path)) as backup_conn:
        source_conn.backup(backup_conn)

    return str(backup_path)


def import_current_league_data(db: Session, admin: str | None, write_to_log: LogWriter) -> AdminImportResponse:
    admin = require_admin(admin)
    root_dir = resolve_import_root()
    bind = db.get_bind()
    backup_root = resolve_backup_root(bind, root_dir)

    db.rollback()
    db.close()

    try:
        backup_path = backup_sqlite_database(bind, backup_root)
        report = run_import(
            dry_run=False,
            strict_mode=True,
            target_engine=bind,
            root_dir=root_dir,
        )
    except Exception as exc:
        write_to_log("正式导入失败", f"unexpected_error={exc}", admin)
        return AdminImportResponse(success=False, message=f"正式导入异常中断: {exc}")

    datasets = {
        name: ImportDatasetSummaryResponse.model_validate(summary)
        for name, summary in report.to_dict()["datasets"].items()
    }
    cleanup_summary = datasets.get("team_cleanup")
    attribute_summary = datasets.get("player_attributes")
    imported_attribute_version = attribute_summary.details.get("data_version") if attribute_summary else None
    removed_count = cleanup_summary.details.get("removed_count", 0) if cleanup_summary else 0

    if report.has_errors or not report.committed:
        message = "正式导入未提交，请先修复源数据或检查导入报告。"
        write_to_log(
            "正式导入失败",
            f"workbook={Path(report.workbook_path).name}; committed={report.committed}; backup={backup_path or 'none'}",
            admin,
        )
        return AdminImportResponse(
            success=False,
            message=message,
            committed=report.committed,
            strict_mode=report.strict_mode,
            workbook_path=report.workbook_path,
            attributes_csv_path=report.attributes_csv_path,
            backup_path=backup_path,
            warnings=report.warnings,
            datasets=datasets,
        )

    message = f"已正式导入 {Path(report.workbook_path).name}"
    if removed_count:
        message += f"，并清理 {removed_count} 支过期孤立球队"
    if backup_path:
        message += "。导入前备份已创建"

    write_to_log(
        "正式导入联赛数据",
        f"workbook={Path(report.workbook_path).name}; backup={backup_path or 'none'}; cleaned_teams={removed_count}",
        admin,
    )
    return AdminImportResponse(
        success=True,
        message=message,
        committed=report.committed,
        strict_mode=report.strict_mode,
        workbook_path=report.workbook_path,
        attributes_csv_path=report.attributes_csv_path,
        backup_path=backup_path,
        warnings=report.warnings,
        datasets=datasets,
    )
