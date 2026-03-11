from pathlib import Path

from sqlalchemy import inspect, text

import models  # noqa: F401 - ensures ORM models are registered before create_all
from database import BOOTSTRAP_LOG_PATH, engine, init_database
from domain_types import LEGACY_SLOT_TYPE_MOJIBAKE_VALUES

CORE_TABLES = [
    "teams",
    "players",
    "player_attributes",
    "transfer_logs",
    "admin_users",
    "admin_sessions",
    "operation_audits",
    "league_info",
]


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _read_latest_bootstrap_event(log_path: Path) -> str:
    if not log_path.exists():
        return "missing"

    lines = [line.strip() for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return "empty"
    return lines[-1]


def main():
    init_database()
    inspector = inspect(engine)
    print("== HEIGO Schema Audit ==")

    with engine.connect() as conn:
        if inspector.has_table("alembic_version"):
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            print(f"- alembic_version: {version}")
        else:
            print("- alembic_version: missing")

        print(f"- schema_bootstrap_log: {BOOTSTRAP_LOG_PATH}")
        print(f"- latest_bootstrap_event: {_read_latest_bootstrap_event(BOOTSTRAP_LOG_PATH)}")
        if inspector.has_table("players"):
            legacy_slot_literals = ", ".join(_sql_literal(value) for value in LEGACY_SLOT_TYPE_MOJIBAKE_VALUES)
            legacy_slot_type_count = conn.execute(
                text(f"SELECT COUNT(*) FROM players WHERE slot_type IN ({legacy_slot_literals})")
            ).scalar_one()
            print(f"- legacy_slot_type_rows: {legacy_slot_type_count}")

        for table in CORE_TABLES:
            if not inspector.has_table(table):
                print(f"- {table}: missing")
                continue

            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            indexes = inspector.get_indexes(table)
            foreign_keys = inspector.get_foreign_keys(table)
            checks = inspector.get_check_constraints(table)
            index_names = ", ".join(index["name"] for index in indexes) or "none"
            foreign_key_names = ", ".join(
                f"{','.join(foreign_key.get('constrained_columns') or [])}->{foreign_key.get('referred_table')}"
                for foreign_key in foreign_keys
            ) or "none"
            check_names = ", ".join(check.get("name") or "<unnamed>" for check in checks) or "none"
            print(
                f"- {table}: rows={count}; indexes={index_names}; foreign_keys={foreign_key_names}; checks={check_names}"
            )

        print("\n== Key Findings ==")
        print("- players now carry both team_id and team_name, and team_id is enforced with a real foreign key.")
        print("- players.team_name is still preserved for API and export compatibility during migration.")
        print("- transfer_logs now carry from_team_id/to_team_id with real foreign keys while preserving from_team/to_team for historical compatibility.")
        print("- transfer_logs.operation is now guarded by a database CHECK constraint against unsupported operation values.")
        print("- admin_sessions is now persistent and supports restart-safe authentication.")
        print("- transfer_logs now have runtime indexes for created_at and operation lookups.")
        print("- operation_audits now persist schema bootstrap events, all admin write actions, formal import results, and imported legacy admin_operations.log history for backend-side operations auditing.")
        print("- league_info now stores typed values with key/category/type CHECK constraints instead of a single weakly typed value column.")
        print("- team aggregate refreshes now support affected-team incremental recalculation instead of always rescanning every visible team.")
        print("- team stat refreshes are now split into roster, wage, and value buckets so selected write paths can refresh only the necessary aggregates.")
        print("- value-oriented team metrics are now treated as realtime read aggregations, while roster and wage metrics remain persisted team caches.")
        print("- /api/teams now surfaces stat_sources metadata so callers can see which team fields are cached and which are realtime overlays.")
        print("- teams now persist the latest cache refresh mode/timestamp/scopes so the admin debug view can distinguish cache hits, realtime overlays, and recent write-driven refreshes.")
        print("- startup now requires Alembic upgrade head; automatic runtime fallback has been removed from normal app boot.")
        print("- runtime_schema_repair.py remains available as an operator-invoked emergency repair path, and every bootstrap/repair attempt is logged to schema_bootstrap.log.")
        print("- legacy text cleanup now normalizes historical fake-slot values to 伪名 and enables UTF-8 local startup output.")
        print("- import_data.py now defaults to strict workbook validation against 信息总览 + 联赛名单, while legacy fallback remains opt-in for older files.")


if __name__ == "__main__":
    main()
