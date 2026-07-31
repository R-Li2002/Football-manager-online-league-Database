import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Match, MatchPlayerEvent, SiteNote, Team
from services.data_status_service import get_actionable_data_statuses, get_data_status
from services.site_note_service import build_suspension_note_key, build_suspension_team_note_key


class DataStatusServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _team(self, name, level="超级"):
        team = Team(name=name, level=level)
        self.db.add(team)
        self.db.flush()
        return team

    def _match(self, round_no, status="scheduled", home_score=None, away_score=None, level="超级"):
        home = self._team(f"{level}-H-{round_no}-{self.db.query(Team).count()}", level)
        away = self._team(f"{level}-A-{round_no}-{self.db.query(Team).count()}", level)
        match = Match(
            level=level,
            round_no=round_no,
            home_team_id=home.id,
            home_team_name=home.name,
            away_team_id=away.id,
            away_team_name=away.name,
            status=status,
            home_score=home_score,
            away_score=away_score,
        )
        self.db.add(match)
        self.db.flush()
        return match

    def _event(self, match, event_type, quantity=1):
        event = MatchPlayerEvent(
            match_id=match.id,
            team_id=match.home_team_id,
            team_name=match.home_team_name,
            player_name=f"{event_type}-{match.id}",
            event_type=event_type,
            quantity=quantity,
        )
        self.db.add(event)
        return event

    def _status(self, key, scope="超级"):
        response = get_data_status(self.db)
        return next(item for item in response.items if item.key == key and item.scope == scope)

    def test_empty_database_reports_unknown_sources(self):
        response = get_data_status(self.db)
        self.assertEqual(next(item for item in response.items if item.key == "roster").status, "unknown")
        self.assertEqual(next(item for item in response.items if item.key == "attributes").status, "unknown")
        self.assertEqual(self._status("schedule").status, "unknown")

    def test_future_scheduled_rounds_do_not_create_pending_work(self):
        for round_no in range(1, 35):
            self._match(round_no)
        self.db.commit()

        schedule = self._status("schedule")
        self.assertEqual(schedule.status, "normal")
        self.assertEqual(schedule.updated_round, 0)
        self.assertEqual(schedule.issue_count, 0)
        self.assertIn("尚未产生赛果", schedule.message)

    def test_partial_active_round_is_pending(self):
        complete = self._match(1, "played", 0, 0)
        self._event(complete, "mvp")
        self._match(1)
        self.db.commit()

        schedule = self._status("schedule")
        self.assertEqual(schedule.status, "pending")
        self.assertEqual(schedule.updated_round, 0)
        self.assertEqual(schedule.issue_count, 1)

    def test_continuous_round_stops_before_incomplete_round(self):
        first = self._match(1, "played", 0, 0)
        self._event(first, "mvp")
        self._match(2, "played", None, None)
        self.db.commit()

        schedule = self._status("schedule")
        self.assertEqual(schedule.status, "error")
        self.assertEqual(schedule.updated_round, 1)

    def test_scoreless_match_with_one_mvp_is_event_complete(self):
        match = self._match(1, "played", 0, 0)
        self._event(match, "mvp")
        self.db.commit()

        ranking = self._status("player_rankings")
        self.assertEqual(ranking.status, "normal")
        self.assertEqual(ranking.updated_round, 1)

    def test_missing_mvp_is_pending_for_player_rankings(self):
        self._match(1, "played", 0, 0)
        self.db.commit()

        ranking = self._status("player_rankings")
        self.assertEqual(ranking.status, "pending")
        self.assertEqual(ranking.issue_count, 1)

    def test_goal_total_mismatch_is_player_ranking_error(self):
        match = self._match(1, "played", 1, 0)
        self._event(match, "goal", 2)
        self._event(match, "mvp")
        self.db.commit()

        self.assertEqual(self._status("schedule").status, "normal")
        self.assertEqual(self._status("player_rankings").status, "error")

    def test_non_event_resolved_statuses_are_complete(self):
        for index, status in enumerate(("postponed", "cancelled", "home_forfeit", "away_forfeit", "double_forfeit"), 1):
            self._match(index, status)
        self.db.commit()

        self.assertEqual(self._status("schedule").updated_round, 5)
        self.assertEqual(self._status("player_rankings").updated_round, 5)

    def test_suspension_round_uses_level_marker_and_team_override(self):
        match = self._match(1, "played", 0, 0)
        self._event(match, "mvp")
        teams = self.db.query(Team).filter(Team.level == "超级").all()
        self.db.add(SiteNote(key=build_suspension_note_key("超级"), text="已核对", round_no=1))
        self.db.commit()

        self.assertEqual(self._status("suspensions").status, "normal")

        self.db.add(SiteNote(key=build_suspension_team_note_key(teams[0].id), text="待更新", round_no=0))
        self.db.commit()
        suspensions = self._status("suspensions")
        self.assertEqual(suspensions.status, "stale")
        self.assertEqual(suspensions.issue_count, 1)

    def test_workspace_actionable_statuses_exclude_derived_standings(self):
        complete = self._match(1, "played", 0, 0)
        self._event(complete, "mvp")
        self._match(1)
        self.db.commit()

        full_admin = get_actionable_data_statuses(self.db, is_full_admin=True, capabilities=set())
        schedule_worker = get_actionable_data_statuses(
            self.db,
            is_full_admin=False,
            capabilities={"schedule.write"},
        )
        self.assertNotIn("standings", {item.key for item in full_admin})
        self.assertNotIn("standings", {item.key for item in schedule_worker})
        self.assertIn("schedule", {item.key for item in schedule_worker})


if __name__ == "__main__":
    unittest.main()
