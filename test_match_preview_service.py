import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import CupMatch, Match, Player, SiteNote, Team
from schemas_write import SuspensionRecordUpdateRequest
from services import match_preview_service, site_note_service, suspension_service


class MatchPreviewServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        self.home = Team(name="Alpha", level="超级", manager="Alpha Boss")
        self.away = Team(name="Beta", level="超级", manager="Beta Boss")
        self.db.add_all([self.home, self.away])
        self.db.commit()
        match_preview_service._PREVIEW_CACHE.clear()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _add_league_schedule(self):
        self.db.add_all([
            Match(
                level="超级",
                round_no=1,
                home_team_id=self.home.id,
                home_team_name=self.home.name,
                away_team_id=self.away.id,
                away_team_name=self.away.name,
                home_score=2,
                away_score=0,
                status="played",
            ),
            Match(
                level="超级",
                round_no=2,
                home_team_id=self.away.id,
                home_team_name=self.away.name,
                away_team_id=self.home.id,
                away_team_name=self.home.name,
                home_score=1,
                away_score=1,
                status="played",
            ),
        ])
        upcoming = Match(
            level="超级",
            round_no=3,
            home_team_id=self.home.id,
            home_team_name=self.home.name,
            away_team_id=self.away.id,
            away_team_name=self.away.name,
            status="scheduled",
        )
        self.db.add(upcoming)
        self.db.add_all([
            SiteNote(key=site_note_service.build_suspension_team_note_key(self.home.id), text="核对至第 2 轮", round_no=2),
            SiteNote(key=site_note_service.build_suspension_team_note_key(self.away.id), text="核对至第 2 轮", round_no=2),
        ])
        self.db.commit()
        return upcoming

    def _preview(self, fixture_type, match_id):
        with (
            patch.object(match_preview_service, "_power_payload", return_value=({}, {self.home.id: {}, self.away.id: {}})),
            patch.object(match_preview_service.player_ranking_service, "get_player_rankings", return_value=SimpleNamespace(rows=[])),
        ):
            return match_preview_service.get_match_preview(self.db, fixture_type, match_id)

    def test_league_preview_combines_probabilities_form_and_reliable_availability(self):
        upcoming = self._add_league_schedule()

        preview = self._preview("league", upcoming.id)

        self.assertEqual(preview.fixture.phase, "league")
        self.assertEqual((preview.home.team_id, preview.away.team_id), (self.home.id, self.away.id))
        self.assertAlmostEqual(
            preview.prediction.home_win_probability
            + preview.prediction.draw_probability
            + preview.prediction.away_win_probability,
            100.0,
            places=1,
        )
        self.assertEqual(preview.home.recent_form, ["W", "D"])
        self.assertEqual(preview.away.recent_form, ["L", "D"])
        self.assertTrue(preview.home.availability.reliable)
        self.assertTrue(preview.away.availability.reliable)
        self.assertTrue(preview.stakes_label)
        self.assertTrue(preview.prediction.reasons)

    def test_knockout_preview_uses_neutral_model_for_aggregate_score_fixture(self):
        self._add_league_schedule()
        cup_match = CupMatch(
            competition="champions_cup",
            stage="round_of_16",
            slot_no=1,
            home_team_id=self.home.id,
            home_team_name=self.home.name,
            away_team_id=self.away.id,
            away_team_name=self.away.name,
            status="scheduled",
        )
        self.db.add(cup_match)
        self.db.commit()

        preview = self._preview("cup", cup_match.id)

        self.assertEqual(preview.fixture.phase, "knockout")
        self.assertTrue(preview.fixture.neutral_venue)
        self.assertEqual(preview.stakes_label, "杯赛晋级战")
        self.assertIn("两回合总比分", preview.stakes_detail)

    def test_played_match_cannot_open_pre_match_intelligence(self):
        self._add_league_schedule()
        played = self.db.query(Match).filter(Match.round_no == 1).one()

        with self.assertRaises(HTTPException) as raised:
            self._preview("league", played.id)

        self.assertEqual(raised.exception.status_code, 400)

    def test_power_payload_maps_every_non_goalkeeper_in_both_teams(self):
        summary_response = SimpleNamespace(data_version="2630", items=[])
        ranking_responses = [
            SimpleNamespace(items=[
                SimpleNamespace(uid=101, heigo_power=72.15),
                SimpleNamespace(uid=106, heigo_power=55.25),
            ]),
            SimpleNamespace(items=[
                SimpleNamespace(uid=201, heigo_power=68.75),
                SimpleNamespace(uid=209, heigo_power=49.50),
            ]),
        ]
        with (
            patch.object(match_preview_service.player_power_ranking_service, "get_team_power_summaries", return_value=summary_response),
            patch.object(match_preview_service.player_power_ranking_service, "get_player_power_ranking", side_effect=ranking_responses) as ranking,
        ):
            _summaries, power_by_team = match_preview_service._power_payload(self.db, [self.home, self.away])

        self.assertEqual(power_by_team[self.home.id][106], 55.25)
        self.assertEqual(power_by_team[self.away.id][209], 49.50)
        self.assertEqual(ranking.call_count, 2)
        self.assertTrue(all(call.kwargs["limit"] == "all" for call in ranking.call_args_list))

    def test_two_match_suspension_only_marks_the_next_two_league_previews(self):
        first_upcoming = self._add_league_schedule()
        later_matches = []
        for round_no in (4, 5):
            match = Match(
                level="超级",
                round_no=round_no,
                home_team_id=self.home.id,
                home_team_name=self.home.name,
                away_team_id=self.away.id,
                away_team_name=self.away.name,
                status="scheduled",
            )
            self.db.add(match)
            later_matches.append(match)
        player = Player(uid=101, name="Suspended Star", team_id=self.home.id, team_name=self.home.name)
        self.db.add(player)
        self.db.commit()
        suspension_service.update_suspension_record(
            self.db,
            "editor",
            SuspensionRecordUpdateRequest(player_uid=player.uid, red_card_suspended=True, suspension_matches=2),
            lambda *_args: None,
        )

        round_three = self._preview("league", first_upcoming.id)
        round_four = self._preview("league", later_matches[0].id)
        round_five = self._preview("league", later_matches[1].id)

        self.assertEqual(round_three.home.availability.missing_count, 1)
        self.assertEqual(round_four.home.availability.missing_count, 1)
        self.assertIn("停赛共2场", round_four.home.availability.missing_players[0].absence_label)
        self.assertEqual(round_five.home.availability.missing_count, 0)


if __name__ == "__main__":
    unittest.main()
