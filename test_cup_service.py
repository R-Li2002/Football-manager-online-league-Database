import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import CupMatch, Team
from schemas_write import CupMatchResultUpdateRequest, CupMatchTeamsUpdateRequest
from services import cup_service


class CupServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        for name in ("Alpha", "Beta", "Gamma", "Delta"):
            self.db.add(Team(name=name, level="超级", manager=f"{name} Boss"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _team_id(self, name):
        return self.db.query(Team).filter(Team.name == name).one().id

    def test_ensure_bracket_creates_all_knockout_slots(self):
        created = cup_service.ensure_bracket(self.db, "champions_cup")

        self.assertEqual(created, 15)
        self.assertEqual(self.db.query(CupMatch).filter(CupMatch.competition == "champions_cup").count(), 15)
        self.assertEqual(self.db.query(CupMatch).filter(CupMatch.stage == "round_of_16").count(), 8)
        self.assertEqual(self.db.query(CupMatch).filter(CupMatch.stage == "final").count(), 1)

    def test_wumingjian_cup_starts_from_round_of_32(self):
        created = cup_service.ensure_bracket(self.db, "wumingjian_cup")

        self.assertEqual(created, 31)
        self.assertEqual(self.db.query(CupMatch).filter(CupMatch.competition == "wumingjian_cup").count(), 31)
        self.assertEqual(
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "wumingjian_cup", CupMatch.stage == "round_of_32")
            .count(),
            16,
        )
        self.assertEqual(
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "wumingjian_cup", CupMatch.stage == "round_of_16")
            .count(),
            8,
        )

    def test_result_propagates_winner_to_next_round(self):
        cup_service.ensure_bracket(self.db, "champions_cup")
        first = (
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "champions_cup", CupMatch.stage == "round_of_16", CupMatch.slot_no == 1)
            .one()
        )
        cup_service.update_cup_match_teams(
            self.db,
            "editor",
            first.id,
            CupMatchTeamsUpdateRequest(home_team_id=self._team_id("Alpha"), away_team_id=self._team_id("Beta")),
            lambda *_args: None,
        )

        cup_service.update_cup_match_result(
            self.db,
            "editor",
            first.id,
            CupMatchResultUpdateRequest(home_score=2, away_score=1, status="played"),
            lambda *_args: None,
        )

        quarter = (
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "champions_cup", CupMatch.stage == "quarter_final", CupMatch.slot_no == 1)
            .one()
        )
        self.assertEqual(quarter.home_team_name, "Alpha")

    def test_even_slot_winner_propagates_to_next_round_away_side(self):
        cup_service.ensure_bracket(self.db, "champions_cup")
        second = (
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "champions_cup", CupMatch.stage == "round_of_16", CupMatch.slot_no == 2)
            .one()
        )
        cup_service.update_cup_match_teams(
            self.db,
            "editor",
            second.id,
            CupMatchTeamsUpdateRequest(home_team_id=self._team_id("Gamma"), away_team_id=self._team_id("Delta")),
            lambda *_args: None,
        )

        cup_service.update_cup_match_result(
            self.db,
            "editor",
            second.id,
            CupMatchResultUpdateRequest(home_score=0, away_score=3, status="played"),
            lambda *_args: None,
        )

        quarter = (
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "champions_cup", CupMatch.stage == "quarter_final", CupMatch.slot_no == 1)
            .one()
        )
        self.assertEqual(quarter.away_team_name, "Delta")

    def test_bracket_marks_winner_and_eliminated_sides(self):
        cup_service.ensure_bracket(self.db, "champions_cup")
        first = (
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "champions_cup", CupMatch.stage == "round_of_16", CupMatch.slot_no == 1)
            .one()
        )
        cup_service.update_cup_match_teams(
            self.db,
            "editor",
            first.id,
            CupMatchTeamsUpdateRequest(home_team_id=self._team_id("Alpha"), away_team_id=self._team_id("Beta")),
            lambda *_args: None,
        )
        cup_service.update_cup_match_result(
            self.db,
            "editor",
            first.id,
            CupMatchResultUpdateRequest(home_score=2, away_score=1, status="played"),
            lambda *_args: None,
        )

        bracket = cup_service.get_bracket(self.db, "champions_cup")
        match = bracket.stages[0]["matches"][0]
        self.assertEqual(match.home_advancement, "winner")
        self.assertEqual(match.away_advancement, "eliminated")

    def test_draw_result_requires_explicit_winner(self):
        cup_service.ensure_bracket(self.db, "league_cup")
        first = (
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "league_cup", CupMatch.stage == "round_of_16", CupMatch.slot_no == 1)
            .one()
        )
        cup_service.update_cup_match_teams(
            self.db,
            "editor",
            first.id,
            CupMatchTeamsUpdateRequest(home_team_id=self._team_id("Alpha"), away_team_id=self._team_id("Beta")),
            lambda *_args: None,
        )

        with self.assertRaises(HTTPException):
            cup_service.update_cup_match_result(
                self.db,
                "editor",
                first.id,
                CupMatchResultUpdateRequest(home_score=1, away_score=1, status="played"),
                lambda *_args: None,
            )

    def test_draw_result_with_away_goal_winner_propagates(self):
        cup_service.ensure_bracket(self.db, "league_cup")
        first = (
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "league_cup", CupMatch.stage == "round_of_16", CupMatch.slot_no == 1)
            .one()
        )
        cup_service.update_cup_match_teams(
            self.db,
            "editor",
            first.id,
            CupMatchTeamsUpdateRequest(home_team_id=self._team_id("Alpha"), away_team_id=self._team_id("Beta")),
            lambda *_args: None,
        )

        cup_service.update_cup_match_result(
            self.db,
            "editor",
            first.id,
            CupMatchResultUpdateRequest(
                home_score=2,
                away_score=2,
                winner_team_id=self._team_id("Beta"),
                status="played",
            ),
            lambda *_args: None,
        )

        self.db.refresh(first)
        self.assertEqual(first.winner_team_name, "Beta")
        self.assertIn("客场进球", first.notes)
        quarter = (
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "league_cup", CupMatch.stage == "quarter_final", CupMatch.slot_no == 1)
            .one()
        )
        self.assertEqual(quarter.home_team_name, "Beta")

    def test_only_round_of_16_teams_are_manually_editable(self):
        cup_service.ensure_bracket(self.db, "champions_cup")
        quarter = (
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "champions_cup", CupMatch.stage == "quarter_final", CupMatch.slot_no == 1)
            .one()
        )

        with self.assertRaises(HTTPException):
            cup_service.update_cup_match_teams(
                self.db,
                "editor",
                quarter.id,
                CupMatchTeamsUpdateRequest(home_team_id=self._team_id("Alpha"), away_team_id=self._team_id("Beta")),
                lambda *_args: None,
            )


if __name__ == "__main__":
    unittest.main()
