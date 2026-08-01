import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import CupGroupTeam, CupMatch, Team
from schemas_write import CupGroupMatchResultUpdateRequest, CupGroupUpdateRequest, CupMatchResultUpdateRequest, CupMatchTeamsUpdateRequest
from services import cup_service


class CupServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        for name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"):
            self.db.add(Team(name=name, level="超级", manager=f"{name} Boss"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _team_id(self, name):
        return self.db.query(Team).filter(Team.name == name).one().id

    @staticmethod
    def _qualification_group(group_name, team_id_start, fourth_points, complete=True):
        rows = []
        points = [12, 10, 8, fourth_points, 3, 1]
        for index, value in enumerate(points, start=1):
            rows.append(cup_service.CupGroupStandingResponse(
                rank=index,
                team_id=team_id_start + index,
                team_name=f"{group_name} Team {index}",
                played=5,
                points=value,
                goal_difference=6 - index,
                goals_for=10 - index,
            ))
        matches = [SimpleNamespace(status="played") for _ in range(30 if complete else 29)]
        return SimpleNamespace(group_name=group_name, standings=rows, matches=matches)

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

    def test_group_stage_has_fixed_champions_and_league_structures(self):
        champions = cup_service.get_group_stage(self.db, "champions_cup")
        league = cup_service.get_group_stage(self.db, "league_cup")

        self.assertEqual((champions.group_count, champions.teams_per_group), (5, 6))
        self.assertEqual([group.group_name for group in champions.groups], ["A", "B", "C", "D", "E"])
        self.assertTrue(all(len(group.teams) == 6 for group in champions.groups))
        self.assertEqual((league.group_count, league.teams_per_group), (4, 6))
        self.assertEqual([group.group_name for group in league.groups], ["A", "B", "C", "D"])

    def test_champions_qualification_uses_top_three_and_best_fourth(self):
        groups = [
            self._qualification_group(group_name, index * 100, fourth_points)
            for index, (group_name, fourth_points) in enumerate(zip(("A", "B", "C", "D", "E"), (4, 7, 6, 5, 3)), start=1)
        ]

        complete, champions, league = cup_service._apply_group_qualification(self.db, "champions_cup", groups)

        self.assertTrue(complete)
        self.assertEqual(len(champions), 16)
        self.assertEqual(len(league), 4)
        best_fourth = groups[1].standings[3]
        self.assertEqual(best_fourth.qualification, "champions_knockout")
        self.assertEqual(best_fourth.qualification_label, "冠军杯淘汰赛")
        self.assertTrue(all(group.standings[3].qualification == "league_knockout" for group in groups if group.group_name != "B"))

    def test_league_qualification_combines_twelve_teams_and_four_champions_transfers(self):
        groups = [self._qualification_group(group_name, index * 1000, 4, complete=False) for index, group_name in enumerate(("A", "B", "C", "D"), start=1)]
        champions_fourths = [
            (group_name, cup_service.CupGroupStandingResponse(rank=4, team_id=9000 + index, team_name=f"Champions {group_name}", points=8 - index))
            for index, group_name in enumerate(("A", "B", "C", "D", "E"), start=1)
        ]

        with patch.object(cup_service, "_champions_fourth_rows", return_value=(champions_fourths, False)):
            complete, champions, league = cup_service._apply_group_qualification(self.db, "league_cup", groups)

        self.assertFalse(complete)
        self.assertEqual(champions, [])
        self.assertEqual(len(league), 16)
        self.assertEqual(sum(team.source_competition == "league_cup" for team in league), 12)
        self.assertEqual(sum(team.source_competition == "champions_cup" for team in league), 4)
        self.assertTrue(all(row.qualification_label.startswith("暂列") for group in groups for row in group.standings))

    def test_schedule_manager_can_save_existing_teams_into_group(self):
        team_ids = [self._team_id(name) for name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta")]
        result = cup_service.update_cup_group(
            self.db,
            "editor",
            "champions_cup",
            1,
            CupGroupUpdateRequest(team_ids=team_ids),
            lambda *_args: None,
        )

        self.assertTrue(result["success"])
        stage = cup_service.get_group_stage(self.db, "champions_cup")
        self.assertEqual(stage.assigned_team_count, 6)
        self.assertEqual([slot.team_name for slot in stage.groups[0].teams], ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"])

    def test_complete_group_generates_ten_rounds_and_thirty_home_away_matches(self):
        team_ids = [self._team_id(name) for name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta")]
        cup_service.update_cup_group(
            self.db,
            "editor",
            "champions_cup",
            1,
            CupGroupUpdateRequest(team_ids=team_ids),
            lambda *_args: None,
        )

        group = cup_service.get_group_stage(self.db, "champions_cup").groups[0]

        self.assertEqual(len(group.matches), 30)
        self.assertEqual(sorted({match.round_no for match in group.matches}), list(range(1, 11)))
        self.assertTrue(all(sum(match.round_no == round_no for match in group.matches) == 3 for round_no in range(1, 11)))
        pairings = {frozenset((match.home_team_id, match.away_team_id)) for match in group.matches}
        self.assertEqual(len(pairings), 15)
        for pairing in pairings:
            pair_matches = [match for match in group.matches if frozenset((match.home_team_id, match.away_team_id)) == pairing]
            self.assertEqual(len(pair_matches), 2)
            self.assertEqual(pair_matches[0].home_team_id, pair_matches[1].away_team_id)
            self.assertEqual(pair_matches[0].away_team_id, pair_matches[1].home_team_id)
        for first_round in range(1, 10, 2):
            first_matches = [match for match in group.matches if match.round_no == first_round]
            second_matches = [match for match in group.matches if match.round_no == first_round + 1]
            self.assertEqual(
                {(match.home_team_id, match.away_team_id) for match in first_matches},
                {(match.away_team_id, match.home_team_id) for match in second_matches},
            )

    def test_expanding_single_round_robin_preserves_score_only_once(self):
        team_ids = [self._team_id(name) for name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta")]
        cup_service.update_cup_group(
            self.db,
            "editor",
            "champions_cup",
            1,
            CupGroupUpdateRequest(team_ids=team_ids),
            lambda *_args: None,
        )
        cup_service.get_group_stage(self.db, "champions_cup")
        matches = (
            self.db.query(CupMatch)
            .filter(CupMatch.competition == "champions_cup", CupMatch.stage == "group_1")
            .order_by(CupMatch.slot_no)
            .all()
        )
        second_leg_ids = [
            match.id for match in matches
            if ((((int(match.slot_no) - 1) // 3) + 1) % 2) == 0
        ]
        self.db.query(CupMatch).filter(CupMatch.id.in_(second_leg_ids)).delete(synchronize_session=False)
        first = matches[0]
        first.home_score = 2
        first.away_score = 1
        first.status = "played"
        self.db.commit()
        first_pair = {int(first.home_team_id), int(first.away_team_id)}
        self.db.expunge_all()

        refreshed = cup_service.get_group_stage(self.db, "champions_cup").groups[0]
        pair_matches = [
            match for match in refreshed.matches
            if {match.home_team_id, match.away_team_id} == first_pair
        ]

        self.assertEqual(len(refreshed.matches), 30)
        self.assertEqual(sum(match.status == "played" for match in pair_matches), 1)
        self.assertEqual(sum((match.home_score, match.away_score) == (2, 1) for match in pair_matches), 1)

    def test_group_scores_allow_draws_and_recalculate_standings(self):
        team_ids = [self._team_id(name) for name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta")]
        cup_service.update_cup_group(
            self.db,
            "editor",
            "league_cup",
            1,
            CupGroupUpdateRequest(team_ids=team_ids),
            lambda *_args: None,
        )
        first_group = cup_service.get_group_stage(self.db, "league_cup").groups[0]
        first_match = first_group.matches[0]
        second_match = first_group.matches[1]

        cup_service.update_cup_group_match_result(
            self.db,
            "editor",
            "league_cup",
            first_match.id,
            CupGroupMatchResultUpdateRequest(home_score=2, away_score=1),
            lambda *_args: None,
        )
        cup_service.update_cup_group_match_result(
            self.db,
            "editor",
            "league_cup",
            second_match.id,
            CupGroupMatchResultUpdateRequest(home_score=0, away_score=0),
            lambda *_args: None,
        )

        refreshed = cup_service.get_group_stage(self.db, "league_cup").groups[0]
        winner = next(row for row in refreshed.standings if row.team_id == first_match.home_team_id)
        loser = next(row for row in refreshed.standings if row.team_id == first_match.away_team_id)
        drawn_home = next(row for row in refreshed.standings if row.team_id == second_match.home_team_id)
        drawn_away = next(row for row in refreshed.standings if row.team_id == second_match.away_team_id)
        self.assertEqual((winner.played, winner.wins, winner.points, winner.goal_difference), (1, 1, 3, 1))
        self.assertEqual((loser.played, loser.losses, loser.points, loser.goal_difference), (1, 1, 0, -1))
        self.assertEqual((drawn_home.draws, drawn_home.points), (1, 1))
        self.assertEqual((drawn_away.draws, drawn_away.points), (1, 1))

    def test_group_score_requires_both_sides_or_neither(self):
        team_ids = [self._team_id(name) for name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta")]
        cup_service.update_cup_group(
            self.db,
            "editor",
            "champions_cup",
            1,
            CupGroupUpdateRequest(team_ids=team_ids),
            lambda *_args: None,
        )
        match = cup_service.get_group_stage(self.db, "champions_cup").groups[0].matches[0]

        with self.assertRaisesRegex(HTTPException, "同时填写双方比分"):
            cup_service.update_cup_group_match_result(
                self.db,
                "editor",
                "champions_cup",
                match.id,
                CupGroupMatchResultUpdateRequest(home_score=1, away_score=None),
                lambda *_args: None,
            )

    def test_team_cup_outlook_tracks_two_leg_group_progress(self):
        team_ids = [self._team_id(name) for name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta")]
        cup_service.update_cup_group(
            self.db,
            "editor",
            "champions_cup",
            1,
            CupGroupUpdateRequest(team_ids=team_ids),
            lambda *_args: None,
        )
        alpha_id = self._team_id("Alpha")
        beta_id = self._team_id("Beta")

        initial = cup_service.get_team_cup_outlook(self.db, alpha_id).competitions[0]
        self.assertEqual((initial.competition, initial.phase, initial.group_name), ("champions_cup", "group", "A"))
        self.assertEqual((initial.remaining_match_count, initial.remaining_opponent_count), (10, 5))
        self.assertEqual(len(initial.opponents), 5)
        self.assertLessEqual(len(initial.next_matches), 4)

        alpha_beta_matches = (
            self.db.query(CupMatch)
            .filter(
                CupMatch.competition == "champions_cup",
                CupMatch.stage == "group_1",
                (
                    ((CupMatch.home_team_id == alpha_id) & (CupMatch.away_team_id == beta_id))
                    | ((CupMatch.home_team_id == beta_id) & (CupMatch.away_team_id == alpha_id))
                ),
            )
            .order_by(CupMatch.slot_no)
            .all()
        )
        for index, match in enumerate(alpha_beta_matches, start=1):
            cup_service.update_cup_group_match_result(
                self.db,
                "editor",
                "champions_cup",
                match.id,
                CupGroupMatchResultUpdateRequest(home_score=index, away_score=0),
                lambda *_args: None,
            )
            outlook = cup_service.get_team_cup_outlook(self.db, alpha_id).competitions[0]
            beta_progress = next(row for row in outlook.opponents if row.team_id == beta_id)
            self.assertEqual((beta_progress.played_legs, beta_progress.remaining_legs), (index, 2 - index))
            self.assertEqual(outlook.remaining_match_count, 10 - index)

        self.assertEqual(outlook.remaining_opponent_count, 4)
        self.assertTrue(outlook.qualification_label)

    def test_team_cup_outlook_reports_knockout_opponent(self):
        alpha_id = self._team_id("Alpha")
        beta_id = self._team_id("Beta")
        self.db.add(CupMatch(
            competition="wumingjian_cup",
            stage="round_of_32",
            slot_no=1,
            home_team_id=alpha_id,
            home_team_name="Alpha",
            away_team_id=beta_id,
            away_team_name="Beta",
            status="scheduled",
        ))
        self.db.commit()

        outlook = cup_service.get_team_cup_outlook(self.db, alpha_id).competitions[0]

        self.assertEqual((outlook.competition, outlook.phase), ("wumingjian_cup", "knockout"))
        self.assertEqual((outlook.remaining_match_count, outlook.remaining_opponent_count), (1, 1))
        self.assertEqual(outlook.next_matches[0].opponent_team_name, "Beta")

    def test_team_cannot_be_assigned_to_two_groups_in_same_cup(self):
        alpha = self._team_id("Alpha")
        cup_service.update_cup_group(
            self.db,
            "editor",
            "league_cup",
            1,
            CupGroupUpdateRequest(team_ids=[alpha, None, None, None, None, None]),
            lambda *_args: None,
        )

        with self.assertRaisesRegex(HTTPException, "已在 A 组"):
            cup_service.update_cup_group(
                self.db,
                "editor",
                "league_cup",
                2,
                CupGroupUpdateRequest(team_ids=[alpha, None, None, None, None, None]),
                lambda *_args: None,
            )

        self.assertEqual(self.db.query(CupGroupTeam).filter(CupGroupTeam.competition == "league_cup").count(), 1)

    def test_group_save_requires_six_slots_and_existing_visible_teams(self):
        with self.assertRaisesRegex(HTTPException, "每组必须提交 6 个球队槽位"):
            cup_service.update_cup_group(
                self.db,
                "editor",
                "champions_cup",
                1,
                CupGroupUpdateRequest(team_ids=[self._team_id("Alpha")]),
                lambda *_args: None,
            )
        with self.assertRaisesRegex(HTTPException, "请选择已有可见球队"):
            cup_service.update_cup_group(
                self.db,
                "editor",
                "champions_cup",
                1,
                CupGroupUpdateRequest(team_ids=[999999, None, None, None, None, None]),
                lambda *_args: None,
            )

    def test_reinitialize_clears_existing_bracket_data_for_every_cup(self):
        expected_slots = {"champions_cup": 15, "league_cup": 15, "wumingjian_cup": 31}
        for competition, slot_count in expected_slots.items():
            cup_service.ensure_bracket(self.db, competition)
            first = (
                self.db.query(CupMatch)
                .filter(CupMatch.competition == competition, CupMatch.stage == cup_service.get_first_stage(competition))
                .order_by(CupMatch.slot_no)
                .first()
            )
            first.home_team_id = self._team_id("Alpha")
            first.home_team_name = "Alpha"
            first.away_team_id = self._team_id("Beta")
            first.away_team_name = "Beta"
            first.home_score = 2
            first.away_score = 1
            first.winner_team_id = self._team_id("Alpha")
            first.winner_team_name = "Alpha"
            first.status = "played"
            first.notes = "existing result"
            self.db.commit()

            result = cup_service.initialize_cup_bracket(
                self.db,
                "editor",
                competition,
                lambda *_args: None,
                reset=True,
            )

            self.assertTrue(result["success"])
            matches = self.db.query(CupMatch).filter(CupMatch.competition == competition).all()
            self.assertEqual(len(matches), slot_count)
            for match in matches:
                self.assertIsNone(match.home_team_id)
                self.assertIsNone(match.away_team_id)
                self.assertIsNone(match.home_score)
                self.assertIsNone(match.away_score)
                self.assertIsNone(match.winner_team_id)
                self.assertIsNone(match.notes)
                self.assertEqual(match.status, "scheduled")

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
