import unittest
from unittest import mock
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from auth_utils import (
    create_session,
    delete_session,
    get_session_username,
    hash_legacy_password,
    hash_password,
    verify_password,
    verify_password_and_upgrade,
)
from database import Base, init_database
from migration_helpers import backfill_team_link_data
from league_settings import create_league_info_record, get_growth_age_limit, is_supported_league_info_key
from models import AdminUser, LeagueInfo, OperationAudit, Player, Team, TransferLog
from services.league_service import TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL, TEAM_STAT_SCOPE_WAGE, persist_with_team_stats, recalculate_team_stats
from services.operation_audit_service import import_legacy_admin_log_to_operation_audits
from services import read_service, wage_service
from team_links import get_players_by_team_name


class Phase1Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "phase1_test.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}", poolclass=NullPool)
        Base.metadata.create_all(bind=self.engine)
        init_database(target_engine=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_password_hash_roundtrip(self):
        password_hash = hash_password("secret-pass")
        self.assertTrue(password_hash.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password("secret-pass", password_hash))
        self.assertFalse(verify_password("wrong-pass", password_hash))

    def test_legacy_password_upgrade(self):
        admin = AdminUser(username="admin", password_hash=hash_legacy_password("legacy-pass"))
        self.db.add(admin)
        self.db.commit()

        self.assertTrue(verify_password_and_upgrade(self.db, admin, "legacy-pass"))
        self.assertTrue(admin.password_hash.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password("legacy-pass", admin.password_hash))

    def test_session_lifecycle(self):
        token = create_session(self.db, "HEIGO01")
        self.db.commit()

        self.assertEqual(get_session_username(self.db, token), "HEIGO01")
        delete_session(self.db, token)
        self.db.commit()
        self.assertIsNone(get_session_username(self.db, token))

    def test_growth_age_limit_default_and_parsing(self):
        self.assertEqual(get_growth_age_limit(self.db), 24)

        self.db.add(create_league_info_record("成长年龄上限", 26))
        self.db.commit()
        self.assertEqual(get_growth_age_limit(self.db), 26)

    def test_supported_league_info_key(self):
        self.assertTrue(is_supported_league_info_key("成长年龄上限"))
        self.assertFalse(is_supported_league_info_key("未知配置"))

    def test_sqlite_foreign_keys_enabled(self):
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(text("PRAGMA foreign_keys")).scalar_one(), 1)

    def test_foreign_key_constraints_present(self):
        inspector = inspect(self.engine)

        player_foreign_keys = inspector.get_foreign_keys("players")
        self.assertTrue(
            any(
                foreign_key.get("referred_table") == "teams"
                and "team_id" in (foreign_key.get("constrained_columns") or [])
                for foreign_key in player_foreign_keys
            )
        )

        transfer_log_foreign_keys = inspector.get_foreign_keys("transfer_logs")
        self.assertTrue(
            any(
                foreign_key.get("referred_table") == "teams"
                and "from_team_id" in (foreign_key.get("constrained_columns") or [])
                for foreign_key in transfer_log_foreign_keys
            )
        )
        self.assertTrue(
            any(
                foreign_key.get("referred_table") == "teams"
                and "to_team_id" in (foreign_key.get("constrained_columns") or [])
                for foreign_key in transfer_log_foreign_keys
            )
        )

    def test_foreign_key_enforcement_rejects_unknown_team_ids(self):
        invalid_player = Player(
            uid=99,
            name="非法球员",
            age=20,
            initial_ca=80,
            ca=80,
            pa=90,
            position="MC",
            nationality="CN",
            team_id=9999,
            team_name="不存在的球队",
            wage=1.0,
            slot_type="",
        )
        self.db.add(invalid_player)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_transfer_operation_constraint_rejects_unknown_values(self):
        invalid_log = TransferLog(
            player_uid=100,
            player_name="非法日志",
            from_team="不存在的球队",
            to_team="目标球队",
            operation="非法操作",
        )
        self.db.add(invalid_log)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_league_info_constraints_reject_invalid_key_and_type_payload(self):
        self.db.add(
            LeagueInfo(
                key="未知配置",
                category="基本信息",
                value_type="text",
                text_value="oops",
            )
        )
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        self.db.add(
            LeagueInfo(
                key="成长年龄上限",
                category="基本信息",
                value_type="text",
                text_value="not-an-integer",
            )
        )
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

        invalid_log = TransferLog(
            player_uid=100,
            player_name="非法日志",
            from_team_id=9999,
            from_team="不存在的球队",
            to_team="目标球队",
            operation="交易",
        )
        self.db.add(invalid_log)
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_team_id_backfill_and_compat_lookup(self):
        team = Team(name="测试队", manager="mgr", level="超级", wage=0)
        self.db.add(team)
        self.db.commit()

        player = Player(
            uid=1,
            name="球员A",
            age=20,
            initial_ca=100,
            ca=105,
            pa=120,
            position="MC",
            nationality="CN",
            team_name="测试队",
            wage=1.0,
            slot_type="",
        )
        self.db.add(player)
        self.db.commit()

        with self.engine.begin() as conn:
            backfill_team_link_data(conn)
        self.db.refresh(player)

        self.assertEqual(player.team_id, team.id)
        players = get_players_by_team_name(self.db, "测试队")
        self.assertEqual([item.uid for item in players], [1])

    def test_transfer_log_team_id_backfill(self):
        from_team = Team(name="原球队", manager="mgr", level="超级", wage=0)
        to_team = Team(name="新球队", manager="mgr", level="超级", wage=0)
        self.db.add_all([from_team, to_team])
        self.db.commit()

        log = TransferLog(
            player_uid=10,
            player_name="球员B",
            from_team="原球队",
            to_team="新球队",
            operation="交易",
        )
        self.db.add(log)
        self.db.commit()

        with self.engine.begin() as conn:
            backfill_team_link_data(conn)
        self.db.refresh(log)

        self.assertEqual(log.from_team_id, from_team.id)
        self.assertEqual(log.to_team_id, to_team.id)

    def test_incremental_team_stats_only_refreshes_affected_teams(self):
        alpha = Team(name="Alpha FC", manager="A", level="超级", wage=0, team_size=99)
        beta = Team(name="Beta FC", manager="B", level="超级", wage=0, team_size=77)
        self.db.add_all([alpha, beta])
        self.db.commit()

        self.db.add(
            Player(
                uid=1001,
                name="Alpha One",
                age=22,
                initial_ca=100,
                ca=102,
                pa=120,
                position="MC",
                nationality="ENG",
                team_id=alpha.id,
                team_name=alpha.name,
                wage=1.0,
                slot_type="8M",
            )
        )
        self.db.commit()

        recalculate_team_stats(self.db, affected_team_ids={alpha.id})
        self.db.refresh(alpha)
        self.db.refresh(beta)

        self.assertEqual(alpha.team_size, 1)
        self.assertEqual(beta.team_size, 77)

    def test_partial_team_stat_scopes_only_update_requested_bucket(self):
        alpha = Team(
            name="Alpha FC",
            manager="A",
            level="超级",
            wage=0,
            team_size=5,
            total_value=888,
            avg_value=444,
            avg_ca=333,
            avg_pa=222,
            total_growth=111,
        )
        self.db.add(alpha)
        self.db.commit()

        self.db.add(
            Player(
                uid=1002,
                name="Alpha Two",
                age=22,
                initial_ca=100,
                ca=102,
                pa=120,
                position="MC",
                nationality="ENG",
                team_id=alpha.id,
                team_name=alpha.name,
                wage=2.5,
                slot_type="7M",
            )
        )
        self.db.commit()

        recalculate_team_stats(self.db, affected_team_ids={alpha.id}, stat_scopes={TEAM_STAT_SCOPE_WAGE})
        self.db.refresh(alpha)

        self.assertEqual(alpha.wage, 2.5)
        self.assertEqual(alpha.final_wage, 8.0)
        self.assertEqual(alpha.team_size, 5)
        self.assertEqual(alpha.total_value, 888)

    def test_team_read_model_uses_realtime_value_stats_over_cached_columns(self):
        alpha = Team(
            name="Alpha FC",
            manager="A",
            level="超级",
            wage=3.2,
            team_size=9,
            gk_count=1,
            final_wage=8.4,
            count_8m=1,
            count_7m=0,
            count_fake=0,
            total_value=999,
            avg_value=888,
            avg_ca=777,
            avg_pa=666,
            total_growth=555,
        )
        self.db.add(alpha)
        self.db.commit()

        self.db.add(
            Player(
                uid=1003,
                name="Alpha Live",
                age=20,
                initial_ca=90,
                ca=110,
                pa=130,
                position="MC",
                nationality="ENG",
                team_id=alpha.id,
                team_name=alpha.name,
                wage=1.1,
                slot_type="8M",
            )
        )
        self.db.commit()

        teams = read_service.get_teams(self.db)
        alpha_view = next(team for team in teams if team.name == "Alpha FC")

        self.assertEqual(alpha_view.team_size, 9)
        self.assertEqual(alpha_view.final_wage, 8.4)
        self.assertNotEqual(alpha_view.total_value, 999)
        self.assertNotEqual(alpha_view.avg_ca, 777)
        self.assertNotEqual(alpha_view.total_growth, 555)
        self.assertEqual(alpha_view.stat_sources.field_modes["team_size"], "cached")
        self.assertEqual(alpha_view.stat_sources.field_modes["total_value"], "realtime")
        self.assertIn("wage", alpha_view.stat_sources.cached_fields)
        self.assertIn("avg_pa", alpha_view.stat_sources.realtime_fields)
        self.assertEqual(alpha_view.stat_sources.refresh_state.cached_read_mode, "cache_hit")
        self.assertEqual(alpha_view.stat_sources.refresh_state.realtime_read_mode, "realtime_overlay")

    def test_team_stat_sources_expose_last_cache_refresh_mode(self):
        alpha = Team(name="Alpha FC", manager="A", level="超级", wage=0)
        self.db.add(alpha)
        self.db.commit()

        self.db.add(
            Player(
                uid=1004,
                name="Alpha Refresh",
                age=21,
                initial_ca=95,
                ca=101,
                pa=122,
                position="MC",
                nationality="ENG",
                team_id=alpha.id,
                team_name=alpha.name,
                wage=1.8,
                slot_type="7M",
            )
        )
        self.db.commit()

        persist_with_team_stats(self.db, affected_team_ids={alpha.id})
        self.db.refresh(alpha)

        self.assertEqual(alpha.stats_cache_refresh_mode, TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL)
        self.assertEqual(alpha.stats_cache_refresh_scopes, "roster,wage")
        self.assertIsNotNone(alpha.stats_cache_refresh_at)

        teams = read_service.get_teams(self.db)
        alpha_view = next(team for team in teams if team.name == "Alpha FC")

        self.assertEqual(alpha_view.stat_sources.refresh_state.last_cache_refresh_mode, TEAM_CACHE_REFRESH_MODE_WRITE_INCREMENTAL)
        self.assertEqual(alpha_view.stat_sources.refresh_state.last_cache_refresh_scopes, ["roster", "wage"])
        self.assertIn("写操作增量刷新", alpha_view.stat_sources.refresh_state.last_cache_refresh_summary)

    def test_safe_full_team_rebuild_backfills_unknown_refresh_metadata(self):
        alpha = Team(name="Alpha FC", manager="A", level="超级", wage=0)
        self.db.add(alpha)
        self.db.commit()

        self.db.add(
            Player(
                uid=1005,
                name="Alpha Backfill",
                age=22,
                initial_ca=96,
                ca=103,
                pa=125,
                position="MC",
                nationality="ENG",
                team_id=alpha.id,
                team_name=alpha.name,
                wage=2.1,
                slot_type="8M",
            )
        )
        self.db.commit()

        alpha.stats_cache_refresh_mode = "unknown"
        alpha.stats_cache_refresh_scopes = ""
        alpha.stats_cache_refresh_at = None
        self.db.commit()

        result = wage_service.rebuild_team_stat_caches(self.db, "HEIGO01", lambda *_args: None)
        self.db.refresh(alpha)

        self.assertTrue(result["success"])
        self.assertEqual(alpha.stats_cache_refresh_mode, "full_recalc")
        self.assertEqual(alpha.stats_cache_refresh_scopes, "roster,wage")
        self.assertIsNotNone(alpha.stats_cache_refresh_at)


    def test_schema_bootstrap_status_reads_latest_events(self):
        bootstrap_log_path = Path(self.temp_dir.name) / "schema_bootstrap.log"
        bootstrap_log_path.write_text(
            "\n".join(
                [
                    "[2026-03-11 10:00:00] alembic_upgrade_head engine=sqlite:test detail=startup",
                    "[2026-03-11 10:05:00] manual_runtime_fallback_started engine=sqlite:test detail=operator-invoked repair",
                    "[2026-03-11 10:05:10] manual_runtime_fallback_completed engine=sqlite:test detail=operator-invoked repair",
                ]
            ),
            encoding="utf-8",
        )

        with mock.patch("services.read_service.BOOTSTRAP_LOG_PATH", bootstrap_log_path):
            status = read_service.get_schema_bootstrap_status(limit=2)

        self.assertTrue(status.file_exists)
        self.assertEqual(status.log_path, str(bootstrap_log_path))
        self.assertEqual(len(status.recent_events), 2)
        self.assertEqual(
            status.latest_event,
            "[2026-03-11 10:05:10] manual_runtime_fallback_completed engine=sqlite:test detail=operator-invoked repair",
        )

    def test_schema_bootstrap_event_is_persisted_to_operation_audits(self):
        events = self.db.query(OperationAudit).filter(OperationAudit.category == "schema_bootstrap").all()
        self.assertGreaterEqual(len(events), 1)
        latest = sorted(events, key=lambda item: (item.created_at, item.id))[-1]
        self.assertEqual(latest.action, "alembic_upgrade_head")
        self.assertEqual(latest.status, "success")

    def test_legacy_admin_log_import_is_idempotent(self):
        log_path = Path(self.temp_dir.name) / "admin_operations.log"
        log_path.write_text(
            "\n".join(
                [
                    "[2026-03-11 10:00:00] [HEIGO01] 登录: 管理员登录成功",
                    "[2026-03-11 10:01:00] [HEIGO01] 交易: 球员 A(UID:1) 从 Alpha FC 转移到 Beta FC",
                ]
            ),
            encoding="utf-8",
        )

        first_result = import_legacy_admin_log_to_operation_audits(self.engine, log_path)
        second_result = import_legacy_admin_log_to_operation_audits(self.engine, log_path)

        self.assertEqual(first_result["imported"], 2)
        self.assertEqual(second_result["imported"], 0)
        self.assertEqual(second_result["skipped"], 2)

        imported = (
            self.db.query(OperationAudit)
            .filter(OperationAudit.source == "legacy_log_file")
            .order_by(OperationAudit.id.asc())
            .all()
        )
        self.assertEqual(len(imported), 2)
        self.assertEqual(imported[0].category, "auth")
        self.assertEqual(imported[0].action, "login")
        self.assertEqual(imported[1].category, "transfer")
        self.assertEqual(imported[1].action, "transfer_player")


if __name__ == "__main__":
    unittest.main()
