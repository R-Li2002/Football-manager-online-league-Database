import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    AdminUser,
    CompetitionResponsibilityAssignment,
    CompetitionRoundWorkLog,
    CompetitionRoundWorkState,
    Match,
    MatchPlayerEvent,
)
from schemas_read import WorkspaceIdentityResponse
from services import competition_work_service


class CompetitionWorkServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.identity = WorkspaceIdentityResponse(
            principal_id="admin:root",
            source="admin_account",
            account_type="administrator",
            username="root",
            display_name="root",
            is_full_admin=True,
            capabilities=["schedule.write", "suspensions.write"],
        )
        self.db.add(AdminUser(username="root", password_hash="test", role="admin"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _add_match(self, round_no, *, status="scheduled", home_score=None, away_score=None):
        match = Match(
            level="超级",
            round_no=round_no,
            home_team_name=f"Home {round_no}",
            away_team_name=f"Away {round_no}",
            status=status,
            home_score=home_score,
            away_score=away_score,
            updated_at=datetime.now(),
        )
        self.db.add(match)
        self.db.flush()
        return match

    def _add_complete_events(self, match):
        total_goals = int(match.home_score or 0) + int(match.away_score or 0)
        if total_goals:
            self.db.add(
                MatchPlayerEvent(
                    match_id=match.id,
                    team_name=match.home_team_name,
                    player_name="Scorer",
                    event_type="goal",
                    quantity=total_goals,
                    updated_at=datetime.now(),
                )
            )
        self.db.add(
            MatchPlayerEvent(
                match_id=match.id,
                team_name=match.home_team_name,
                player_name="MVP",
                event_type="mvp",
                quantity=1,
                updated_at=datetime.now(),
            )
        )

    def test_selects_latest_started_unfinished_round_pair(self):
        self._add_match(1, status="played", home_score=0, away_score=0)
        self._add_match(2)
        self._add_match(17, status="played", home_score=2, away_score=1)
        self._add_match(18, status="played", home_score=1, away_score=1)
        self.db.commit()

        summary = competition_work_service.get_competition_work_summary(self.db)
        super_summary = next(item for item in summary.levels if item.level == "超级")

        self.assertEqual(super_summary.round_start, 17)
        self.assertEqual(super_summary.total_matches, 2)
        self.assertEqual(super_summary.missing_event_count, 2)
        self.assertEqual(super_summary.missing_result_count, 0)

    def test_requires_results_events_and_suspension_confirmation_before_completion(self):
        first = self._add_match(1, status="played", home_score=2, away_score=0)
        second = self._add_match(2, status="played", home_score=1, away_score=1)
        self._add_complete_events(first)
        self._add_complete_events(second)
        self.db.commit()

        competition_work_service.assign_round_work(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
            assignee_principal_id="admin:root",
        )
        with self.assertRaisesRegex(Exception, "伤停尚未确认"):
            competition_work_service.submit_round_work(
                self.db,
                self.identity,
                level="超级",
                round_start=1,
            )

        competition_work_service.set_suspension_confirmation(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
            confirmed=True,
            note="第 1-2 轮已核对",
        )
        competition_work_service.submit_round_work(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
        )
        summary = competition_work_service.complete_round_work(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
        )
        state = self.db.query(CompetitionRoundWorkState).one()

        self.assertIsNotNone(state.completed_at)
        completed_pair = next(item for item in summary.levels if item.level == "超级")
        self.assertTrue(completed_pair.completed)

    def test_match_change_after_completion_requires_reconfirmation(self):
        match = self._add_match(1, status="played", home_score=0, away_score=0)
        self._add_complete_events(match)
        self.db.commit()
        competition_work_service.set_suspension_confirmation(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
            confirmed=True,
            note=None,
        )
        competition_work_service.assign_round_work(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
            assignee_principal_id="admin:root",
        )
        competition_work_service.submit_round_work(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
        )
        competition_work_service.complete_round_work(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
        )
        state = self.db.query(CompetitionRoundWorkState).one()
        match.updated_at = state.completed_at + timedelta(seconds=1)
        self.db.commit()

        summary = competition_work_service.get_competition_work_summary(self.db)
        pair = next(item for item in summary.levels if item.level == "超级")

        self.assertFalse(pair.completed)
        self.assertTrue(pair.changed_after_completion)

    def test_assignment_submission_review_and_history(self):
        match = self._add_match(1, status="played", home_score=0, away_score=0)
        self._add_complete_events(match)
        self.db.commit()
        competition_work_service.assign_round_work(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
            assignee_principal_id="admin:root",
        )
        competition_work_service.set_suspension_confirmation(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
            confirmed=True,
            note=None,
        )
        submitted = competition_work_service.submit_round_work(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
            note="请复核",
        )
        pending = next(item for item in submitted.levels if item.level == "超级")
        self.assertEqual(pending.workflow_status, "pending_review")
        self.assertTrue(pending.can_review)

        completed = competition_work_service.review_round_work(
            self.db,
            self.identity,
            level="超级",
            round_start=1,
            approved=True,
            note="复核通过",
        )
        pair = next(item for item in completed.levels if item.level == "超级")
        self.assertEqual(pair.workflow_status, "completed")
        self.assertEqual(
            [row.action for row in self.db.query(CompetitionRoundWorkLog).order_by(CompetitionRoundWorkLog.id).all()],
            ["assign_schedule_responsibility", "confirm_suspensions", "submit", "review_approve"],
        )

    def test_level_responsibilities_split_schedule_and_suspension_work(self):
        self._add_match(1)
        self.db.add_all([
            CompetitionResponsibilityAssignment(
                level="超级",
                responsibility_type="schedule",
                principal_id="admin:schedule-worker",
                display_name="赛程人员",
                assigned_by="admin:root",
            ),
            CompetitionResponsibilityAssignment(
                level="超级",
                responsibility_type="suspensions",
                principal_id="admin:suspension-worker",
                display_name="伤停人员",
                assigned_by="admin:root",
            ),
        ])
        self.db.commit()
        schedule_identity = WorkspaceIdentityResponse(
            principal_id="admin:schedule-worker",
            source="admin_account",
            account_type="worker",
            username="schedule-worker",
            display_name="赛程人员",
            capabilities=["schedule.write", "match_events.write"],
        )
        suspension_identity = WorkspaceIdentityResponse(
            principal_id="admin:suspension-worker",
            source="admin_account",
            account_type="worker",
            username="suspension-worker",
            display_name="伤停人员",
            capabilities=["suspensions.write"],
        )

        schedule_summary = competition_work_service.get_competition_work_summary(self.db, schedule_identity).levels[0]
        suspension_summary = competition_work_service.get_competition_work_summary(self.db, suspension_identity).levels[0]

        self.assertTrue(schedule_summary.is_my_schedule_task)
        self.assertFalse(schedule_summary.is_my_suspension_task)
        self.assertFalse(schedule_summary.can_confirm_suspensions)
        self.assertTrue(suspension_summary.is_my_suspension_task)
        self.assertTrue(suspension_summary.can_confirm_suspensions)
        self.assertTrue(competition_work_service.operator_can_manage_level(self.db, "schedule-worker", "超级", "schedule"))
        self.assertFalse(competition_work_service.operator_can_manage_level(self.db, "schedule-worker", "超级", "suspensions"))
        self.assertTrue(competition_work_service.operator_can_manage_level(self.db, "root", "甲级", "schedule"))
        with self.assertRaisesRegex(Exception, "不是该级别的伤停负责人"):
            competition_work_service.set_suspension_confirmation(
                self.db,
                schedule_identity,
                level="超级",
                round_start=1,
                confirmed=True,
                note=None,
            )

    def test_invalid_event_totals_are_reported_separately(self):
        match = self._add_match(1, status="played", home_score=1, away_score=0)
        self.db.add_all([
            MatchPlayerEvent(
                match_id=match.id,
                team_name=match.home_team_name,
                player_name="Scorer",
                event_type="goal",
                quantity=2,
            ),
            MatchPlayerEvent(
                match_id=match.id,
                team_name=match.home_team_name,
                player_name="MVP One",
                event_type="mvp",
                quantity=1,
            ),
            MatchPlayerEvent(
                match_id=match.id,
                team_name=match.away_team_name,
                player_name="MVP Two",
                event_type="mvp",
                quantity=1,
            ),
        ])
        self.db.commit()

        summary = competition_work_service.get_competition_work_summary(self.db)
        pair = next(item for item in summary.levels if item.level == "超级")

        self.assertEqual(pair.invalid_count, 1)
        self.assertIn("invalid_goal_total", pair.tasks[0].issue_codes)
        self.assertIn("invalid_mvp_total", pair.tasks[0].issue_codes)

    def test_forfeit_match_does_not_require_player_events(self):
        self._add_match(1, status="away_forfeit", home_score=2, away_score=0)
        self.db.commit()

        summary = competition_work_service.get_competition_work_summary(self.db)
        pair = next(item for item in summary.levels if item.level == "超级")

        self.assertEqual(pair.result_ready_count, 1)
        self.assertEqual(pair.event_ready_count, 1)
        self.assertEqual(pair.missing_event_count, 0)


if __name__ == "__main__":
    unittest.main()
