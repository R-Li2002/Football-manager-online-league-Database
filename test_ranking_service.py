import unittest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import RankingMatch, RankingSeed, Team
from schemas_write import RankingMatchCreateRequest
from services import ranking_service


class RankingServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.db.add_all([
            Team(id=1, name="Alpha FC", level="超级"),
            Team(id=2, name="Beta FC", level="甲级"),
            Team(id=3, name="Gamma FC", level="乙级"),
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def row(self, payload, name):
        return next(item for item in payload.rows if item.team_name == name)

    def test_initial_points_and_first_win_use_loser_base_points(self):
        payload = ranking_service.get_rankings(self.db)
        self.assertEqual(self.row(payload, "Alpha FC").base_points, 1000)

        payload = ranking_service.create_ranking_match(
            self.db,
            "operator",
            RankingMatchCreateRequest(home_team_id=1, away_team_id=2, home_score=2, away_score=1),
            lambda *_args: None,
        )

        alpha = self.row(payload, "Alpha FC")
        beta = self.row(payload, "Beta FC")
        self.assertEqual(alpha.base_points, 1100)
        self.assertEqual(beta.base_points, 900)
        self.assertEqual(alpha.total_points, 1120)
        self.assertEqual(beta.total_points, 920)
        self.assertEqual((alpha.matches, alpha.wins, alpha.losses), (1, 1, 0))
        self.assertEqual((beta.matches, beta.wins, beta.losses), (1, 0, 1))

    def test_later_result_uses_current_base_not_total_points(self):
        now = datetime.now()
        self.db.add_all([
            RankingMatch(home_team_id=1, home_team_name="Alpha FC", away_team_id=2, away_team_name="Beta FC", home_score=2, away_score=0, played_at=now, created_at=now),
            RankingMatch(home_team_id=2, home_team_name="Beta FC", away_team_id=1, away_team_name="Alpha FC", home_score=1, away_score=0, played_at=now + timedelta(seconds=1), created_at=now),
        ])
        self.db.commit()

        payload = ranking_service.get_rankings(self.db)
        alpha = self.row(payload, "Alpha FC")
        beta = self.row(payload, "Beta FC")

        self.assertEqual(alpha.base_points, 990)
        self.assertEqual(beta.base_points, 1010)
        self.assertEqual(alpha.total_points, 1030)
        self.assertEqual(beta.total_points, 1050)

    def test_draw_changes_only_record_and_appearance_total(self):
        self.db.add_all([
            RankingSeed(team_id=1, team_name="Alpha FC", base_points=1234.5, matches=4, wins=2, draws=1, losses=1),
            RankingSeed(team_id=2, team_name="Beta FC", base_points=876.5, matches=4, wins=1, draws=1, losses=2),
        ])
        self.db.commit()

        payload = ranking_service.create_ranking_match(
            self.db,
            "operator",
            RankingMatchCreateRequest(home_team_id=1, away_team_id=2, home_score=1, away_score=1),
            lambda *_args: None,
        )

        alpha = self.row(payload, "Alpha FC")
        beta = self.row(payload, "Beta FC")
        self.assertEqual(alpha.base_points, 1234.5)
        self.assertEqual(beta.base_points, 876.5)
        self.assertEqual((alpha.matches, alpha.draws, alpha.total_points), (5, 2, 1334.5))
        self.assertEqual((beta.matches, beta.draws, beta.total_points), (5, 2, 976.5))

    def test_delete_recalculates_all_following_matches(self):
        first = ranking_service.create_ranking_match(
            self.db, "operator", RankingMatchCreateRequest(home_team_id=1, away_team_id=2, home_score=2, away_score=0), lambda *_args: None
        )
        first_id = first.matches[0].id
        ranking_service.create_ranking_match(
            self.db, "operator", RankingMatchCreateRequest(home_team_id=2, away_team_id=1, home_score=1, away_score=0), lambda *_args: None
        )

        payload = ranking_service.delete_ranking_match(self.db, "operator", first_id, lambda *_args: None)

        self.assertEqual(self.row(payload, "Alpha FC").base_points, 900)
        self.assertEqual(self.row(payload, "Beta FC").base_points, 1100)
        self.assertEqual(payload.total_matches, 1)


if __name__ == "__main__":
    unittest.main()
