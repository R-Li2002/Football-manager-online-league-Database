import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Match, Team
from services.home_service import get_home_dashboard


class HomeDashboardServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _team(self, team_id, name, level, manager):
        team = Team(id=team_id, name=name, level=level, manager=manager)
        self.db.add(team)
        return team

    def _match(self, match_id, level, round_no, home, away, score=None, status="scheduled", updated_at=None):
        match = Match(
            id=match_id,
            level=level,
            round_no=round_no,
            home_team_id=home.id,
            home_team_name=home.name,
            away_team_id=away.id,
            away_team_name=away.name,
            status=status,
            updated_at=updated_at,
        )
        if score is not None:
            match.home_score, match.away_score = score
        self.db.add(match)
        return match

    def test_dashboard_returns_league_progress_results_leaders_and_team_context(self):
        super_a = self._team(1, "Super Alpha", "超级", "Coach S")
        super_a.logo_path = "/static/uploads/teams/super-alpha.webp"
        super_b = self._team(2, "Super Beta", "超级", "Coach T")
        first_a = self._team(3, "First Alpha", "甲级", "Coach A")
        first_b = self._team(4, "First Beta", "甲级", "Coach B")
        second_a = self._team(5, "Second Alpha", "乙级", "Coach C")
        second_b = self._team(6, "Second Beta", "乙级", "Coach D")
        hidden = self._team(7, "Sea Player Club", "隐藏", "")
        self.db.flush()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        self._match(1, "超级", 1, super_a, super_b, (3, 0), "played", now - timedelta(hours=4))
        self._match(2, "甲级", 1, first_a, first_b, (2, 1), "played", now - timedelta(hours=3))
        self._match(3, "乙级", 1, second_a, second_b, (1, 0), "played", now - timedelta(hours=2))
        self._match(4, "超级", 2, super_b, super_a, (0, 1), "played", now - timedelta(hours=1))
        self._match(5, "超级", 3, super_a, super_b)
        self._match(6, "隐藏", 1, hidden, super_a, (9, 9), "played", now)
        self.db.commit()

        response = get_home_dashboard(self.db, team_id=super_a.id)

        self.assertEqual([item.scope for item in response.league_statuses], ["超级", "甲级", "乙级"])
        self.assertEqual([item.id for item in response.recent_results], [4, 3, 2, 1])
        self.assertEqual([item.level for item in response.leaders], ["超级", "甲级", "乙级"])
        self.assertEqual([item.team_name for item in response.leaders], ["Super Alpha", "First Alpha", "Second Alpha"])
        self.assertEqual(response.leaders[0].logo_path, "/static/uploads/teams/super-alpha.webp")
        self.assertIsNotNone(response.team)
        self.assertEqual(response.team.team_name, "Super Alpha")
        self.assertEqual(response.team.logo_path, "/static/uploads/teams/super-alpha.webp")
        self.assertEqual(response.team.next_match.id, 5)
        self.assertEqual(response.team.recent_result.id, 4)

    def test_dashboard_without_valid_visible_team_omits_team_context(self):
        hidden = self._team(20, "Hidden Club", "隐藏", "")
        self.db.commit()

        self.assertIsNone(get_home_dashboard(self.db).team)
        self.assertIsNone(get_home_dashboard(self.db, team_id=hidden.id).team)


if __name__ == "__main__":
    unittest.main()
