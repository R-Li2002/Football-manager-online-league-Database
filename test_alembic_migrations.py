import unittest
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool

from database import init_database, run_manual_runtime_fallback, run_schema_migrations

LATEST_REVISION = "20260318_000013"


class AlembicMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "alembic_test.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}", poolclass=NullPool)

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_run_schema_migrations_bootstraps_empty_database(self):
        self.assertTrue(run_schema_migrations(self.engine))

        inspector = inspect(self.engine)
        for table_name in [
            "teams",
            "players",
            "player_attributes",
            "player_attribute_versions",
            "transfer_logs",
            "admin_users",
            "admin_sessions",
            "operation_audits",
            "league_info",
            "alembic_version",
        ]:
            self.assertTrue(inspector.has_table(table_name), table_name)

        with self.engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        self.assertEqual(version, LATEST_REVISION)

    def test_run_schema_migrations_upgrades_legacy_schema(self):
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE teams (
                        id INTEGER NOT NULL PRIMARY KEY,
                        name VARCHAR,
                        manager VARCHAR,
                        level VARCHAR,
                        wage FLOAT,
                        team_size INTEGER DEFAULT 0
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE players (
                        uid INTEGER NOT NULL PRIMARY KEY,
                        name VARCHAR,
                        age INTEGER,
                        initial_ca INTEGER,
                        ca INTEGER,
                        pa INTEGER,
                        position VARCHAR,
                        nationality VARCHAR,
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
                    CREATE TABLE league_info (
                        id INTEGER NOT NULL PRIMARY KEY,
                        key VARCHAR NOT NULL UNIQUE,
                        category VARCHAR NOT NULL,
                        value VARCHAR
                    )
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE TABLE transfer_logs (
                        id INTEGER NOT NULL PRIMARY KEY,
                        player_uid INTEGER,
                        player_name VARCHAR,
                        from_team VARCHAR,
                        to_team VARCHAR,
                        operation VARCHAR,
                        ca_change INTEGER,
                        pa_change INTEGER,
                        age_change INTEGER,
                        operator VARCHAR,
                        created_at DATETIME,
                        notes VARCHAR
                    )
                    """
                )
            )
            conn.execute(text("INSERT INTO teams (id, name, manager, level, wage) VALUES (1, 'Alpha FC', 'A', '甲级', 0)"))
            conn.execute(text("INSERT INTO teams (id, name, manager, level, wage) VALUES (2, 'Beta FC', 'B', '甲级', 0)"))
            conn.execute(
                text(
                    """
                    INSERT INTO players (uid, name, age, initial_ca, ca, pa, position, nationality, team_name, wage, slot_type)
                    VALUES (1001, 'Player A', 22, 100, 110, 125, 'MC', 'ENG', 'Alpha FC', 1.2, 'О±Гы')
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO league_info (id, key, category, value)
                    VALUES (1, '成长年龄上限', '基本信息', '24')
                    """
                )
            )
            conn.execute(
                text(
                    """
                    INSERT INTO transfer_logs (id, player_uid, player_name, from_team, to_team, operation, operator)
                    VALUES (1, 1001, 'Player A', 'Alpha FC', 'Beta FC', '交易', 'admin')
                    """
                )
            )

        self.assertTrue(run_schema_migrations(self.engine))

        inspector = inspect(self.engine)
        player_columns = {column["name"] for column in inspector.get_columns("players")}
        self.assertIn("team_id", player_columns)

        player_attribute_columns = {column["name"] for column in inspector.get_columns("player_attributes")}
        self.assertIn("player_habits_raw_code", player_attribute_columns)
        self.assertIn("player_habits_high_bits", player_attribute_columns)

        player_attribute_version_columns = {column["name"] for column in inspector.get_columns("player_attribute_versions")}
        self.assertIn("player_habits_raw_code", player_attribute_version_columns)
        self.assertIn("player_habits_high_bits", player_attribute_version_columns)

        transfer_log_columns = {column["name"] for column in inspector.get_columns("transfer_logs")}
        self.assertIn("from_team_id", transfer_log_columns)
        self.assertIn("to_team_id", transfer_log_columns)

        league_info_columns = {column["name"] for column in inspector.get_columns("league_info")}
        self.assertIn("value_type", league_info_columns)
        self.assertNotIn("value", league_info_columns)

        with self.engine.connect() as conn:
            player_team_id = conn.execute(text("SELECT team_id FROM players WHERE uid = 1001")).scalar_one()
            from_team_id = conn.execute(text("SELECT from_team_id FROM transfer_logs WHERE id = 1")).scalar_one()
            to_team_id = conn.execute(text("SELECT to_team_id FROM transfer_logs WHERE id = 1")).scalar_one()
            league_info_value_type = conn.execute(text("SELECT value_type FROM league_info WHERE id = 1")).scalar_one()
            slot_type = conn.execute(text("SELECT slot_type FROM players WHERE uid = 1001")).scalar_one()
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

        self.assertEqual(player_team_id, 1)
        self.assertEqual(from_team_id, 1)
        self.assertEqual(to_team_id, 2)
        self.assertEqual(league_info_value_type, "int")
        self.assertEqual(slot_type, "伪名")
        self.assertEqual(version, LATEST_REVISION)

    def test_init_database_blocks_removed_runtime_fallback(self):
        bootstrap_log_path = Path(self.temp_dir.name) / "schema_bootstrap.log"
        with mock.patch("database.run_schema_migrations", return_value=False):
            with mock.patch("database.BOOTSTRAP_LOG_PATH", bootstrap_log_path):
                with self.assertRaises(RuntimeError):
                    init_database(self.engine)

        self.assertTrue(bootstrap_log_path.exists())
        log_text = bootstrap_log_path.read_text(encoding="utf-8")
        self.assertIn("runtime_fallback_blocked", log_text)

    def test_manual_runtime_fallback_remains_available_as_repair_tool(self):
        bootstrap_log_path = Path(self.temp_dir.name) / "schema_bootstrap.log"
        with mock.patch("database.BOOTSTRAP_LOG_PATH", bootstrap_log_path):
            run_manual_runtime_fallback(self.engine)

        inspector = inspect(self.engine)
        self.assertTrue(inspector.has_table("teams"))
        self.assertTrue(inspector.has_table("players"))
        self.assertTrue(inspector.has_table("transfer_logs"))

        log_text = bootstrap_log_path.read_text(encoding="utf-8")
        self.assertIn("manual_runtime_fallback_started", log_text)
        self.assertIn("manual_runtime_fallback_completed", log_text)


if __name__ == "__main__":
    unittest.main()
