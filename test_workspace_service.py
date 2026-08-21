import unittest
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    AdminSession,
    AdminUser,
    CandidateList,
    Coach,
    CoachAccount,
    CoachSession,
    CompetitionResponsibilityAssignment,
    CompetitionRoundWorkState,
    DataFeedbackReport,
    Match,
    PlayerSuspensionRecord,
    RankingMatch,
)
from services.workspace_service import (
    get_workspace_dashboard,
    list_workspace_accounts,
    resolve_workspace_identity,
)


class WorkspaceServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.session = sessionmaker(bind=self.engine)()

        now = datetime.now(UTC)
        self.session.add_all([
            AdminUser(username="root", password_hash="unused", role="admin"),
            AdminSession(token="admin-token", username="root", created_at=now, expires_at=now + timedelta(days=1)),
            Coach(uid="coach-1", nickname="大直塞", team_name="Leicester City", level="超级"),
            CoachAccount(
                coach_uid="coach-1",
                username="coach-worker",
                qq_number="12345678",
                password_hash="unused",
                is_active=1,
                must_change_password=0,
                can_manage_schedule=1,
                can_manage_cup_standings=1,
                can_manage_rankings=1,
                can_manage_suspensions=1,
                can_manage_candidate_lists=0,
                can_manage_daily_reports=1,
                can_manage_draws=1,
                can_manage_archives=0,
            ),
            CoachSession(
                token="coach-token",
                coach_uid="coach-1",
                username="coach-worker",
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=1),
            ),
        ])
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_resolves_admin_and_coach_work_identities(self):
        admin_identity = resolve_workspace_identity(
            self.session,
            admin_session_token="admin-token",
            coach_session_token=None,
        )
        coach_identity = resolve_workspace_identity(
            self.session,
            admin_session_token=None,
            coach_session_token="coach-token",
        )

        self.assertTrue(admin_identity.is_full_admin)
        self.assertIn("accounts.manage", admin_identity.capabilities)
        self.assertEqual(coach_identity.account_type, "coach_worker")
        self.assertEqual(coach_identity.display_name, "大直塞")
        self.assertIn("schedule.write", coach_identity.capabilities)
        self.assertIn("cup_standings.write", coach_identity.capabilities)
        self.assertIn("rankings.write", coach_identity.capabilities)
        self.assertIn("suspensions.write", coach_identity.capabilities)
        self.assertNotIn("candidate_lists.write", coach_identity.capabilities)
        self.assertIn("daily_reports.write", coach_identity.capabilities)
        self.assertIn("draws.write", coach_identity.capabilities)
        self.assertNotIn("archives.write", coach_identity.capabilities)

    def test_draw_and_archive_permissions_are_independent(self):
        account = self.session.query(CoachAccount).filter(CoachAccount.coach_uid == "coach-1").one()
        account.can_manage_draws = 0
        account.can_manage_archives = 1
        self.session.commit()

        identity = resolve_workspace_identity(
            self.session,
            admin_session_token=None,
            coach_session_token="coach-token",
        )

        self.assertNotIn("draws.write", identity.capabilities)
        self.assertIn("archives.write", identity.capabilities)

    def test_unbound_coach_cannot_enter_workspace(self):
        account = self.session.query(CoachAccount).filter(CoachAccount.coach_uid == "coach-1").one()
        account.qq_number = None
        self.session.commit()

        identity = resolve_workspace_identity(
            self.session,
            admin_session_token=None,
            coach_session_token="coach-token",
        )

        self.assertIsNone(identity)

    def test_dashboard_uses_capabilities_to_build_work_summary(self):
        self.session.add_all([
            Match(level="超级", round_no=1, home_team_name="A", away_team_name="B", status="scheduled"),
            Match(level="超级", round_no=2, home_team_name="C", away_team_name="D", status="played", home_score=1, away_score=0),
            Match(level="超级", round_no=33, home_team_name="Future A", away_team_name="Future B", status="scheduled"),
            PlayerSuspensionRecord(player_uid=1, player_name="P", team_name="A", level="超级", yellow_cards=1),
            CandidateList(name="候选名单", status="draft"),
            DataFeedbackReport(issue_type="other", summary="反馈", details="详情", status="open"),
            RankingMatch(home_team_id=1, home_team_name="A", away_team_id=2, away_team_name="B", home_score=2, away_score=1),
        ])
        self.session.commit()
        identity = resolve_workspace_identity(
            self.session,
            admin_session_token="admin-token",
            coach_session_token=None,
        )

        dashboard = get_workspace_dashboard(self.session, identity)
        values = {item.key: item.value for item in dashboard.metrics}

        self.assertEqual(values["schedule"], 1)
        self.assertEqual(values["match_events"], 1)
        self.assertEqual(values["suspensions"], 1)
        self.assertEqual(values["candidate_lists"], 1)
        self.assertEqual(values["feedback"], 1)
        self.assertEqual(values["rankings"], 1)
        self.assertEqual(len(dashboard.tasks), 1)
        self.assertEqual(dashboard.tasks[0].status, "unassigned")

    def test_coach_worker_dashboard_only_counts_assigned_rounds(self):
        self.session.add_all([
            Match(level="超级", round_no=1, home_team_name="A", away_team_name="B", status="scheduled"),
            Match(level="甲级", round_no=1, home_team_name="C", away_team_name="D", status="scheduled"),
            CompetitionRoundWorkState(
                level="超级",
                round_start=1,
                round_end=2,
            ),
            CompetitionResponsibilityAssignment(
                level="超级",
                responsibility_type="schedule",
                principal_id="coach:coach-worker",
                display_name="大直塞",
                assigned_by="admin:root",
            ),
        ])
        self.session.commit()
        identity = resolve_workspace_identity(
            self.session,
            admin_session_token=None,
            coach_session_token="coach-token",
        )

        dashboard = get_workspace_dashboard(self.session, identity)
        values = {item.key: item.value for item in dashboard.metrics}

        self.assertEqual(values["schedule"], 1)
        self.assertEqual(len(dashboard.tasks), 1)
        self.assertEqual(dashboard.tasks[0].level, "超级")
        self.assertTrue(dashboard.tasks[0].is_mine)

    def test_admin_account_directory_includes_admin_and_coach_accounts(self):
        identity = resolve_workspace_identity(
            self.session,
            admin_session_token="admin-token",
            coach_session_token=None,
        )

        directory = list_workspace_accounts(self.session, identity)
        principal_ids = {item.principal_id for item in directory.items}

        self.assertIn("admin:root", principal_ids)
        self.assertIn("coach:coach-worker", principal_ids)
        coach_item = next(item for item in directory.items if item.coach_uid == "coach-1")
        self.assertIsNone(coach_item.team_id)


if __name__ == "__main__":
    unittest.main()
