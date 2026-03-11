from sqlalchemy import inspect, text

from domain_types import (
    coerce_league_info_storage,
    expected_category,
    is_supported_league_info_key,
    league_info_key_category_check_sql,
    league_info_key_check_sql,
    league_info_key_type_check_sql,
    league_info_payload_check_sql,
    league_info_value_type_check_sql,
    normalize_transfer_operation,
    serialize_league_info_value,
    transfer_operation_check_sql,
)


def _create_league_info_indexes(conn) -> None:
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_league_info_key ON league_info (key)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_league_info_category ON league_info (category)"))


def _create_player_indexes(conn) -> None:
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_players_uid ON players (uid)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_players_name ON players (name)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_players_team_id ON players (team_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_players_team_name ON players (team_name)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_players_team_name_name ON players (team_name, name)"))


def _create_team_indexes(conn) -> None:
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_teams_id ON teams (id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_teams_name ON teams (name)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_teams_stats_cache_refresh_at ON teams (stats_cache_refresh_at)"))


def _create_transfer_log_indexes(conn) -> None:
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transfer_logs_id ON transfer_logs (id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transfer_logs_player_uid ON transfer_logs (player_uid)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transfer_logs_created_at ON transfer_logs (created_at)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transfer_logs_operation ON transfer_logs (operation)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transfer_logs_operation_created_at ON transfer_logs (operation, created_at)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transfer_logs_from_team_id ON transfer_logs (from_team_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_transfer_logs_to_team_id ON transfer_logs (to_team_id)"))


def _has_foreign_key(inspector, table_name: str, column_name: str, referred_table: str) -> bool:
    for foreign_key in inspector.get_foreign_keys(table_name):
        constrained_columns = foreign_key.get("constrained_columns") or []
        if column_name in constrained_columns and foreign_key.get("referred_table") == referred_table:
            return True
    return False


def _has_check_constraint(inspector, table_name: str, constraint_name: str, sql_fragment: str) -> bool:
    normalized_fragment = sql_fragment.replace('"', "").replace(" ", "")
    for check in inspector.get_check_constraints(table_name):
        sql_text = (check.get("sqltext") or "").replace('"', "").replace(" ", "")
        if check.get("name") == constraint_name:
            return True
        if normalized_fragment and normalized_fragment in sql_text:
            return True
    return False


def _rebuild_players_with_foreign_key(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE players__new (
                uid INTEGER NOT NULL PRIMARY KEY,
                name VARCHAR,
                age INTEGER,
                initial_ca INTEGER,
                ca INTEGER,
                pa INTEGER,
                position VARCHAR,
                nationality VARCHAR,
                team_id INTEGER REFERENCES teams (id) ON DELETE SET NULL,
                team_name VARCHAR,
                wage FLOAT,
                slot_type VARCHAR
            )
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO players__new (
                uid, name, age, initial_ca, ca, pa, position, nationality, team_id, team_name, wage, slot_type
            )
            SELECT
                uid, name, age, initial_ca, ca, pa, position, nationality, team_id, team_name, wage, slot_type
            FROM players
            """
        )
    )
    conn.execute(text("DROP TABLE players"))
    conn.execute(text("ALTER TABLE players__new RENAME TO players"))
    _create_player_indexes(conn)


def _load_normalized_league_info_rows(conn, use_legacy_value_column: bool) -> list[dict]:
    if use_legacy_value_column:
        rows = conn.execute(text("SELECT id, key, category, value FROM league_info ORDER BY id")).mappings().all()
    else:
        rows = conn.execute(
            text(
                """
                SELECT id, key, category, value_type, int_value, float_value, text_value
                FROM league_info
                ORDER BY id
                """
            )
        ).mappings().all()

    normalized_rows = []
    for row in rows:
        key = row["key"]
        if not is_supported_league_info_key(key):
            raise RuntimeError(f"Unsupported league_info key during migration: {key}")

        try:
            raw_value = row["value"] if use_legacy_value_column else serialize_league_info_value(
                row["value_type"], row["int_value"], row["float_value"], row["text_value"]
            )
            value_type, int_value, float_value, text_value = coerce_league_info_storage(key, raw_value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid league_info value for key {key}: {exc}") from exc

        normalized_rows.append(
            {
                "id": row["id"],
                "key": key,
                "category": expected_category(key),
                "value_type": value_type,
                "int_value": int_value,
                "float_value": float_value,
                "text_value": text_value,
            }
        )

    return normalized_rows


def _rebuild_league_info_with_constraints(conn, use_legacy_value_column: bool) -> None:
    rows = _load_normalized_league_info_rows(conn, use_legacy_value_column)
    conn.execute(
        text(
            f"""
            CREATE TABLE league_info__new (
                id INTEGER NOT NULL PRIMARY KEY,
                key VARCHAR NOT NULL UNIQUE,
                category VARCHAR NOT NULL,
                value_type VARCHAR NOT NULL,
                int_value INTEGER,
                float_value FLOAT,
                text_value VARCHAR,
                CONSTRAINT ck_league_info_key CHECK ({league_info_key_check_sql()}),
                CONSTRAINT ck_league_info_value_type CHECK ({league_info_value_type_check_sql()}),
                CONSTRAINT ck_league_info_payload CHECK ({league_info_payload_check_sql()}),
                CONSTRAINT ck_league_info_key_type CHECK ({league_info_key_type_check_sql()}),
                CONSTRAINT ck_league_info_key_category CHECK ({league_info_key_category_check_sql()})
            )
            """
        )
    )
    if rows:
        conn.execute(
            text(
                """
                INSERT INTO league_info__new (
                    id, key, category, value_type, int_value, float_value, text_value
                ) VALUES (
                    :id, :key, :category, :value_type, :int_value, :float_value, :text_value
                )
                """
            ),
            rows,
        )
    conn.execute(text("DROP TABLE league_info"))
    conn.execute(text("ALTER TABLE league_info__new RENAME TO league_info"))
    _create_league_info_indexes(conn)


def _load_normalized_transfer_log_rows(conn) -> list[dict]:
    rows = conn.execute(
        text(
            """
            SELECT
                id, player_uid, player_name, from_team_id, from_team, to_team_id, to_team, operation,
                ca_change, pa_change, age_change, operator, created_at, notes
            FROM transfer_logs
            ORDER BY id
            """
        )
    ).mappings().all()

    normalized_rows = []
    for row in rows:
        try:
            operation = normalize_transfer_operation(row["operation"])
        except ValueError as exc:
            raise RuntimeError(f"Invalid transfer_logs.operation for log {row['id']}: {exc}") from exc

        normalized_rows.append(
            {
                "id": row["id"],
                "player_uid": row["player_uid"],
                "player_name": row["player_name"],
                "from_team_id": row["from_team_id"],
                "from_team": row["from_team"],
                "to_team_id": row["to_team_id"],
                "to_team": row["to_team"],
                "operation": operation,
                "ca_change": row["ca_change"],
                "pa_change": row["pa_change"],
                "age_change": row["age_change"],
                "operator": row["operator"],
                "created_at": row["created_at"],
                "notes": row["notes"],
            }
        )

    return normalized_rows


def _rebuild_transfer_logs_with_constraints(conn) -> None:
    rows = _load_normalized_transfer_log_rows(conn)
    conn.execute(
        text(
            f"""
            CREATE TABLE transfer_logs__new (
                id INTEGER NOT NULL PRIMARY KEY,
                player_uid INTEGER,
                player_name VARCHAR,
                from_team_id INTEGER REFERENCES teams (id) ON DELETE SET NULL,
                from_team VARCHAR,
                to_team_id INTEGER REFERENCES teams (id) ON DELETE SET NULL,
                to_team VARCHAR,
                operation VARCHAR NOT NULL,
                ca_change INTEGER,
                pa_change INTEGER,
                age_change INTEGER,
                operator VARCHAR,
                created_at DATETIME,
                notes VARCHAR,
                CONSTRAINT ck_transfer_logs_operation CHECK ({transfer_operation_check_sql()})
            )
            """
        )
    )
    if rows:
        conn.execute(
            text(
                """
                INSERT INTO transfer_logs__new (
                    id, player_uid, player_name, from_team_id, from_team, to_team_id, to_team, operation,
                    ca_change, pa_change, age_change, operator, created_at, notes
                ) VALUES (
                    :id, :player_uid, :player_name, :from_team_id, :from_team, :to_team_id, :to_team, :operation,
                    :ca_change, :pa_change, :age_change, :operator, :created_at, :notes
                )
                """
            ),
            rows,
        )
    conn.execute(text("DROP TABLE transfer_logs"))
    conn.execute(text("ALTER TABLE transfer_logs__new RENAME TO transfer_logs"))
    _create_transfer_log_indexes(conn)


def _backfill_player_team_ids(conn) -> None:
    conn.execute(
        text(
            """
            UPDATE players
            SET team_id = (
                SELECT teams.id
                FROM teams
                WHERE teams.name = players.team_name
            )
            WHERE (team_id IS NULL OR team_id = 0)
              AND team_name IS NOT NULL
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE players
            SET team_id = NULL
            WHERE team_id IS NOT NULL
              AND team_id NOT IN (SELECT id FROM teams)
            """
        )
    )


def _backfill_transfer_log_team_ids(conn) -> None:
    conn.execute(
        text(
            """
            UPDATE transfer_logs
            SET from_team_id = (
                SELECT teams.id
                FROM teams
                WHERE teams.name = transfer_logs.from_team
            )
            WHERE (from_team_id IS NULL OR from_team_id = 0)
              AND from_team IS NOT NULL
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE transfer_logs
            SET to_team_id = (
                SELECT teams.id
                FROM teams
                WHERE teams.name = transfer_logs.to_team
            )
            WHERE (to_team_id IS NULL OR to_team_id = 0)
              AND to_team IS NOT NULL
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE transfer_logs
            SET from_team_id = NULL
            WHERE from_team_id IS NOT NULL
              AND from_team_id NOT IN (SELECT id FROM teams)
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE transfer_logs
            SET to_team_id = NULL
            WHERE to_team_id IS NOT NULL
              AND to_team_id NOT IN (SELECT id FROM teams)
            """
        )
    )


def backfill_team_link_data(conn) -> None:
    inspector = inspect(conn)
    if inspector.has_table("players"):
        _backfill_player_team_ids(conn)
    if inspector.has_table("transfer_logs"):
        _backfill_transfer_log_team_ids(conn)


def upgrade_team_cache_schema(conn) -> None:
    inspector = inspect(conn)
    if not inspector.has_table("teams"):
        return

    team_columns = {column["name"] for column in inspector.get_columns("teams")}
    if "stats_cache_refresh_mode" not in team_columns:
        conn.execute(text("ALTER TABLE teams ADD COLUMN stats_cache_refresh_mode VARCHAR"))
        conn.execute(text("UPDATE teams SET stats_cache_refresh_mode = 'unknown' WHERE stats_cache_refresh_mode IS NULL"))
    if "stats_cache_refresh_scopes" not in team_columns:
        conn.execute(text("ALTER TABLE teams ADD COLUMN stats_cache_refresh_scopes VARCHAR"))
        conn.execute(text("UPDATE teams SET stats_cache_refresh_scopes = '' WHERE stats_cache_refresh_scopes IS NULL"))
    if "stats_cache_refresh_at" not in team_columns:
        conn.execute(text("ALTER TABLE teams ADD COLUMN stats_cache_refresh_at DATETIME"))
    _create_team_indexes(conn)


def upgrade_league_info_schema(conn) -> None:
    inspector = inspect(conn)
    if not inspector.has_table("league_info"):
        return

    league_info_columns = {column["name"] for column in inspector.get_columns("league_info")}
    uses_legacy_value_column = "value" in league_info_columns
    has_typed_columns = {"value_type", "int_value", "float_value", "text_value"} <= league_info_columns
    needs_league_info_checks = not all(
        [
            _has_check_constraint(inspector, "league_info", "ck_league_info_key", league_info_key_check_sql()),
            _has_check_constraint(
                inspector,
                "league_info",
                "ck_league_info_value_type",
                league_info_value_type_check_sql(),
            ),
            _has_check_constraint(
                inspector,
                "league_info",
                "ck_league_info_payload",
                league_info_payload_check_sql(),
            ),
            _has_check_constraint(
                inspector,
                "league_info",
                "ck_league_info_key_type",
                league_info_key_type_check_sql(),
            ),
            _has_check_constraint(
                inspector,
                "league_info",
                "ck_league_info_key_category",
                league_info_key_category_check_sql(),
            ),
        ]
    )

    if conn.engine.dialect.name == "sqlite" and (uses_legacy_value_column or not has_typed_columns or needs_league_info_checks):
        _rebuild_league_info_with_constraints(conn, use_legacy_value_column=uses_legacy_value_column)
    else:
        _create_league_info_indexes(conn)


def upgrade_players_team_schema(conn, with_backfill: bool = True) -> None:
    inspector = inspect(conn)
    if not inspector.has_table("players"):
        return

    player_columns = {column["name"] for column in inspector.get_columns("players")}
    if "team_id" not in player_columns:
        conn.execute(text("ALTER TABLE players ADD COLUMN team_id INTEGER"))

    if with_backfill:
        _backfill_player_team_ids(conn)

    if conn.engine.dialect.name == "sqlite" and not _has_foreign_key(inspector, "players", "team_id", "teams"):
        _rebuild_players_with_foreign_key(conn)
    else:
        _create_player_indexes(conn)


def upgrade_transfer_logs_schema(conn, with_backfill: bool = True) -> None:
    inspector = inspect(conn)
    if not inspector.has_table("transfer_logs"):
        return

    transfer_log_columns = {column["name"] for column in inspector.get_columns("transfer_logs")}
    if "from_team_id" not in transfer_log_columns:
        conn.execute(text("ALTER TABLE transfer_logs ADD COLUMN from_team_id INTEGER"))
    if "to_team_id" not in transfer_log_columns:
        conn.execute(text("ALTER TABLE transfer_logs ADD COLUMN to_team_id INTEGER"))

    if with_backfill:
        _backfill_transfer_log_team_ids(conn)

    needs_from_fk = not _has_foreign_key(inspector, "transfer_logs", "from_team_id", "teams")
    needs_to_fk = not _has_foreign_key(inspector, "transfer_logs", "to_team_id", "teams")
    needs_operation_check = not _has_check_constraint(
        inspector,
        "transfer_logs",
        "ck_transfer_logs_operation",
        transfer_operation_check_sql(),
    )
    if conn.engine.dialect.name == "sqlite" and (needs_from_fk or needs_to_fk or needs_operation_check):
        _rebuild_transfer_logs_with_constraints(conn)
    else:
        _create_transfer_log_indexes(conn)


def upgrade_runtime_schema(conn) -> None:
    upgrade_team_cache_schema(conn)
    upgrade_league_info_schema(conn)
    upgrade_players_team_schema(conn)
    upgrade_transfer_logs_schema(conn)


def initialize_runtime_fallback_schema(active_engine, metadata) -> None:
    metadata.create_all(bind=active_engine)
    with active_engine.begin() as conn:
        upgrade_runtime_schema(conn)
