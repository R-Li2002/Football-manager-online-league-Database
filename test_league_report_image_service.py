import tempfile
import unittest
from pathlib import Path

from PIL import Image

from schemas_read import (
    PlayerRankingCoverageResponse,
    PlayerRankingRowResponse,
    PlayerRankingsResponse,
    RankingStandingRowResponse,
    RankingsResponse,
    StandingRowResponse,
    StandingsPredictionSummaryResponse,
    StandingsResponse,
    SuspensionPlayerResponse,
    SuspensionProgressResponse,
    SuspensionsResponse,
    SuspensionTeamResponse,
)
from services import league_report_image_service


class LeagueReportImageServiceTests(unittest.TestCase):
    def _standings(self):
        return StandingsResponse(
            levels=["超级"],
            rows=[
                StandingRowResponse(
                    level="超级", rank=1, team_name="Nottingham Forest", played=2,
                    wins=2, draws=0, losses=0, goals_for=5, goals_against=1,
                    goal_difference=4, points=6, predicted_rank=2,
                    predicted_rank_min=1, predicted_rank_max=5,
                ),
                StandingRowResponse(
                    level="超级", rank=2, team_name="Tottenham Hotspur", played=2,
                    wins=0, draws=1, losses=1, goals_for=2, goals_against=4,
                    goal_difference=-2, points=1, predicted_rank=14,
                    predicted_rank_min=6, predicted_rank_max=18,
                ),
            ],
            prediction_summaries=[
                StandingsPredictionSummaryResponse(
                    level="超级", phase="early", phase_label="赛季初段", progress=0.0261,
                    played_match_count=8, remaining_match_count=298, total_match_count=306,
                    simulations=1200,
                )
            ],
        )

    def _suspensions(self):
        return SuspensionsResponse(
            levels=["超级"],
            teams=[
                SuspensionTeamResponse(
                    team_id=1,
                    team_name="Tottenham Hotspur",
                    level="超级",
                    two_yellows=[
                        SuspensionPlayerResponse(
                            player_uid=10, player_name="Player One", team_name="Tottenham Hotspur",
                            level="超级", yellow_cards=2,
                        )
                    ],
                    suspended=[
                        SuspensionPlayerResponse(
                            player_uid=11, player_name="Player Two", team_name="Tottenham Hotspur",
                            level="超级", red_card_suspended=True,
                        )
                    ],
                    progress=SuspensionProgressResponse(
                        state="stale", title="伤停仅核对至第 2 轮",
                        detail="赛果已更新至第 4 轮，落后 2 轮",
                    ),
                )
            ],
        )

    def _rankings(self):
        return RankingsResponse(
            initial_points=1000,
            appearance_bonus=20,
            transfer_rate=0.1,
            total_matches=3,
            rows=[
                RankingStandingRowResponse(
                    rank=1, team_id=1, team_name="Tottenham Hotspur", level="超级",
                    base_points=1120.5, total_points=1180.5, matches=3, wins=2, draws=1, losses=0,
                ),
                RankingStandingRowResponse(
                    rank=2, team_id=2, team_name="Nottingham Forest", level="甲级",
                    base_points=1088, total_points=1128, matches=2, wins=1, draws=0, losses=1,
                ),
            ],
        )

    def _player_rankings(self):
        return PlayerRankingsResponse(
            levels=["超级"],
            rows=[
                PlayerRankingRowResponse(
                    rank=1, level="超级", player_uid=10, player_name="Player One",
                    team_id=1, team_name="Tottenham Hotspur", goals=4, assists=1, mvps=1, appearances=2,
                ),
                PlayerRankingRowResponse(
                    rank=2, level="超级", player_uid=11, player_name="Player Two",
                    team_id=2, team_name="Nottingham Forest", goals=2, assists=5, mvps=0, appearances=2,
                ),
            ],
            coverage=[
                PlayerRankingCoverageResponse(
                    level="超级", played_matches=3, matches_with_events=2, matches_missing_events=1,
                    event_rows=8, goal_quantity=6, assist_quantity=6, mvp_quantity=1,
                )
            ],
        )

    def test_standings_svg_localizes_teams_and_includes_prediction(self):
        svg = league_report_image_service._build_standings_svg(self._standings(), "超级")

        self.assertIn("诺丁汉森林", svg)
        self.assertIn("托特纳姆热刺", svg)
        self.assertIn(">14</text>", svg)
        self.assertIn("6–18", svg)
        self.assertIn("90%预测区间", svg)
        self.assertIn("#16161E", svg)
        self.assertIn("#7AA2F7", svg)
        self.assertIn("HEIGO LEAGUE DATA HUB / STANDINGS", svg)

    def test_suspensions_svg_includes_players_and_progress(self):
        svg = league_report_image_service._build_suspensions_svg(self._suspensions(), "超级")

        self.assertIn("托特纳姆热刺", svg)
        self.assertIn("Player One", svg)
        self.assertIn("Player Two", svg)
        self.assertIn("伤停仅核对至第 2 轮", svg)
        self.assertIn("红牌停赛", svg)
        self.assertIn("HEIGO DISCIPLINE REPORT", svg)
        self.assertIn("#292E42", svg)

    def test_png_render_uses_separate_cached_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            standings = league_report_image_service.render_league_report_png("standings", "超级", self._standings(), temp_dir)
            standings_cached = league_report_image_service.render_league_report_png("standings", "超级", self._standings(), temp_dir)
            suspensions = league_report_image_service.render_league_report_png("suspensions", "超级", self._suspensions(), temp_dir)

            self.assertEqual(standings.cache_status, "MISS")
            self.assertEqual(standings_cached.cache_status, "HIT")
            self.assertNotEqual(standings.file_name, suspensions.file_name)
            with Image.open(standings.file_path) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.width, 1200)
                self.assertGreaterEqual(image.height, 820)
            self.assertTrue(Path(suspensions.file_path).exists())

    def test_rankings_svg_matches_rating_desk_and_localizes_teams(self):
        svg = league_report_image_service._build_rankings_svg(self._rankings())

        self.assertIn("HEIGO RATING DESK", svg)
        self.assertIn("排位积分榜", svg)
        self.assertIn("托特纳姆热刺", svg)
        self.assertIn("诺丁汉森林", svg)
        self.assertIn("1,180.5", svg)
        self.assertIn("胜 / 平 / 负", svg)

    def test_player_rankings_svg_sorts_selected_metric_and_shows_coverage(self):
        svg = league_report_image_service._build_player_rankings_svg(self._player_rankings(), "超级", "assists")

        self.assertIn("HEIGO PLAYER PERFORMANCE", svg)
        self.assertIn("超级助攻榜", svg)
        self.assertIn("还有 1 场待补球员明细", svg)
        self.assertLess(svg.index("Player Two"), svg.index("Player One"))
        self.assertIn("托特纳姆热刺", svg)

    def test_statistics_png_cache_separates_ranking_metrics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rankings = league_report_image_service.render_statistics_report_png("rankings", self._rankings(), temp_dir)
            goals = league_report_image_service.render_statistics_report_png(
                "player_rankings", self._player_rankings(), temp_dir, level="超级", metric="goals"
            )
            assists = league_report_image_service.render_statistics_report_png(
                "player_rankings", self._player_rankings(), temp_dir, level="超级", metric="assists"
            )

            self.assertNotEqual(rankings.file_name, goals.file_name)
            self.assertNotEqual(goals.file_name, assists.file_name)
            with Image.open(rankings.file_path) as image:
                self.assertEqual(image.width, 1200)
                self.assertGreaterEqual(image.height, 900)


if __name__ == "__main__":
    unittest.main()
