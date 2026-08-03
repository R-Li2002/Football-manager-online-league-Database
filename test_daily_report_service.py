import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import CupMatch, DailyReportNarrativeTemplate, Match, MatchPlayerEvent, PlayerSuspensionRecord, Team
from schemas_read import WorkspaceIdentityResponse
from schemas_write import DailyReportNarrativeTemplateUpsertRequest, DailyReportUpdateRequest
from services import daily_report_service, team_name_service


class DailyReportServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.identity = WorkspaceIdentityResponse(
            principal_id="admin:root",
            source="admin_account",
            account_type="administrator",
            username="root",
            display_name="Root",
            is_full_admin=True,
            capabilities=["system.maintain"],
        )

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _add_shootout(self):
        match = Match(
            season_label="test",
            level="甲级",
            round_no=3,
            home_team_name="Brighton & Hove Albion",
            away_team_name="Como 1907",
            home_score=8,
            away_score=5,
            status="played",
            created_at=datetime(2026, 8, 2, 20, 0),
            updated_at=datetime(2026, 8, 2, 20, 0),
        )
        self.db.add(match)
        self.db.flush()
        self.db.add_all([
            MatchPlayerEvent(match_id=match.id, team_name="Como 1907", player_name="Hero", event_type="goal", quantity=3),
            MatchPlayerEvent(match_id=match.id, team_name="Como 1907", player_name="Hero", event_type="mvp", quantity=1),
            MatchPlayerEvent(match_id=match.id, team_name="Brighton & Hove Albion", player_name="Winner", event_type="goal", quantity=2),
        ])
        self.db.add(PlayerSuspensionRecord(
            player_uid=999001,
            player_name="Suspended Player",
            team_name="Como 1907",
            level="甲级",
            yellow_cards=2,
            updated_at=datetime(2026, 8, 2, 21, 0),
        ))
        self.db.commit()

    def test_build_report_uses_shootout_and_losing_hattrick_narratives(self):
        self._add_shootout()
        with patch.object(daily_report_service, "_power_values", return_value={}), patch.object(daily_report_service, "_upcoming_power_lines", return_value=[]):
            report = daily_report_service.build_daily_report(self.db, "2026-08-02")

        self.assertEqual(report.match_count, 1)
        self.assertEqual(report.goal_count, 13)
        self.assertEqual(report.suspension_count, 1)
        self.assertIn("布莱顿 8:5 科莫", report.content)
        self.assertIn("13 球", report.content)
        self.assertIn("Hero 帽子戏法仍难救主", report.content)
        self.assertIn("Suspended Player", report.content)
        self.assertIn("【焦点头版】", report.content)
        self.assertIn("【帽子戏法", report.focus_content)
        self.assertIn("布莱顿 8:5 科莫", report.focus_content)
        self.assertIn("Hero 帽子戏法仍难救主", report.focus_content)
        self.assertTrue(report.image_url.startswith("/api/daily-report/image"))

    def test_home_and_away_legs_are_grouped_but_scores_stay_separate(self):
        self.db.add_all([
            Match(
                season_label="test", level="甲级", round_no=3,
                home_team_name="Alpha", away_team_name="Beta",
                home_score=2, away_score=1, status="played",
                created_at=datetime(2026, 8, 2, 18, 0), updated_at=datetime(2026, 8, 2, 18, 0),
            ),
            Match(
                season_label="test", level="甲级", round_no=4,
                home_team_name="Beta", away_team_name="Alpha",
                home_score=0, away_score=3, status="played",
                created_at=datetime(2026, 8, 2, 19, 0), updated_at=datetime(2026, 8, 2, 19, 0),
            ),
        ])
        self.db.commit()

        with patch.object(daily_report_service, "_power_values", return_value={}), patch.object(daily_report_service, "_upcoming_power_lines", return_value=[]):
            report = daily_report_service.build_daily_report(self.db, "2026-08-02")

        self.assertEqual(report.match_count, 2)
        self.assertEqual(report.fixture_group_count, 1)
        self.assertIn("第3轮 Alpha 2:1 Beta；第4轮 Beta 0:3 Alpha", report.content)
        self.assertIn("Alpha两战全胜：首回合主场以 2:1 一球险胜", report.content)
        self.assertIn("次回合反客为主以 3:0 大比分取胜", report.content)
        self.assertIn("完成双杀", report.content)
        self.assertEqual(report.content.count("Alpha vs Beta"), 1)

    def test_cup_home_and_away_legs_are_grouped(self):
        self.db.add_all([
            CupMatch(
                competition="champions_cup", stage="group_1", slot_no=1,
                home_team_name="Alpha", away_team_name="Beta",
                home_score=1, away_score=0, status="played",
                created_at=datetime(2026, 8, 2, 18, 0), updated_at=datetime(2026, 8, 2, 18, 0),
            ),
            CupMatch(
                competition="champions_cup", stage="group_1", slot_no=4,
                home_team_name="Beta", away_team_name="Alpha",
                home_score=2, away_score=2, status="played",
                created_at=datetime(2026, 8, 2, 19, 0), updated_at=datetime(2026, 8, 2, 19, 0),
            ),
        ])
        self.db.commit()

        with patch.object(daily_report_service, "_power_values", return_value={}), patch.object(daily_report_service, "_upcoming_power_lines", return_value=[]):
            report = daily_report_service.build_daily_report(self.db, "2026-08-02")

        self.assertEqual(report.match_count, 2)
        self.assertEqual(report.fixture_group_count, 1)
        self.assertIn("A组第1轮 Alpha 1:0 Beta；A组第2轮 Beta 2:2 Alpha", report.content)
        self.assertIn("Alpha两回合保持不败：首回合主场以 1:0 一球险胜", report.content)
        self.assertIn("次回合 2:2 握手言和", report.content)

    def test_current_top_two_team_makes_an_ordinary_match_front_page(self):
        teams = [Team(name=f"Team {index}", manager="", level="超级") for index in range(1, 8)]
        self.db.add_all(teams)
        self.db.flush()
        self.db.add(Match(
            season_label="test", level="超级", round_no=1,
            home_team_id=teams[0].id, home_team_name=teams[0].name,
            away_team_id=teams[1].id, away_team_name=teams[1].name,
            home_score=1, away_score=0, status="played",
            created_at=datetime(2026, 8, 2, 18, 0), updated_at=datetime(2026, 8, 2, 18, 0),
        ))
        self.db.commit()

        with patch.object(daily_report_service, "_power_values", return_value={}), patch.object(daily_report_service, "_upcoming_power_lines", return_value=[]):
            report = daily_report_service.build_daily_report(self.db, "2026-08-02")

        self.assertEqual(report.focus_count, 1)
        self.assertIn("Team 1 vs Team 2", report.focus_content)

    def test_focus_selection_reserves_title_and_relegation_stories(self):
        candidates = [
            {"line": f"Story {index}", "focus_line": f"Focus {index}", "focus_score": 300 - index, "sort_order": index, "tags": ["大胜"], "kind": "cup"}
            for index in range(7)
        ]
        candidates.extend([
            {"line": "Title story", "focus_line": "Title focus", "focus_score": 80, "sort_order": 20, "tags": ["争冠"], "kind": "league"},
            {"line": "Relegation story", "focus_line": "Relegation focus", "focus_score": 65, "sort_order": 21, "tags": ["保级"], "kind": "league"},
        ])

        selected = daily_report_service._select_focus_stories(candidates)

        self.assertEqual(len(selected), 6)
        self.assertIn("Title story", {story["line"] for story in selected})
        self.assertIn("Relegation story", {story["line"] for story in selected})

    def test_late_prediction_turns_competitor_result_into_key_match_keyword(self):
        match = SimpleNamespace(
            home_team_name="Alpha",
            away_team_name="Beta",
            home_score=2,
            away_score=1,
            status="played",
        )
        focus_teams = {
            "甲级": {
                "title": set(),
                "promotion": {"alpha", "beta"},
                "relegation": set(),
                "phase": "run_in",
                "critical": True,
            }
        }

        score, tags = daily_report_service._focus_score(
            match,
            level="甲级",
            stats=[],
            power_values={},
            focus_teams=focus_teams,
        )

        self.assertGreaterEqual(score, 85)
        self.assertIn("升级关键战", tags)

    def test_legacy_published_focus_is_compacted_to_two_sentences_per_story(self):
        content = (
            "今日共更新 2 场比赛。\n\n【焦点头版】\n"
            "甲级联赛｜Alpha vs Beta：第1轮 Alpha 5:1 Beta；第2轮 Beta 0:2 Alpha。"
            "Alpha 两战全胜。Alpha 大胜 Beta。Player A 上演帽子戏法。\n\n"
            "【常规战报】\nGamma 1:1 Delta。"
        )

        compact = daily_report_service._extract_focus_content(content)

        self.assertIn("Alpha 两战全胜", compact)
        self.assertNotIn("Player A 上演帽子戏法", compact)
        self.assertNotIn("Gamma 1:1 Delta", compact)

    def test_all_current_league_teams_have_common_chinese_names(self):
        self.assertEqual(len(team_name_service.COMMON_CHINESE_TEAM_NAMES), 54)
        self.assertTrue(all(team_name_service.COMMON_CHINESE_TEAM_NAMES.values()))
        self.assertEqual(team_name_service.common_chinese_team_name("Man Utd"), "曼联")
        self.assertEqual(team_name_service.common_chinese_team_name("Benfica"), "本菲卡")
        localized = team_name_service.localize_team_names_in_text(
            "Brighton & Hove Albion 8:5 Como 1907；Man Utd 2:0 AS Roma"
        )
        self.assertEqual(localized, "布莱顿 8:5 科莫；曼联 2:0 罗马")

    def test_published_manual_report_overrides_generated_report(self):
        self._add_shootout()
        with patch.object(daily_report_service, "_power_values", return_value={}), patch.object(daily_report_service, "_upcoming_power_lines", return_value=[]):
            draft = daily_report_service.generate_workspace_report(self.db, self.identity, "2026-08-02")
            published = daily_report_service.update_workspace_report(
                self.db,
                self.identity,
                "2026-08-02",
                DailyReportUpdateRequest(title=draft.title, content="人工终稿内容", publish=True),
            )
            public = daily_report_service.get_public_report(self.db, "2026-08-02")

        self.assertEqual(published.status, "published")
        self.assertEqual(public.content, "人工终稿内容")
        self.assertEqual(public.fingerprint, published.fingerprint)

    def test_public_published_report_localizes_legacy_english_team_names(self):
        self._add_shootout()
        with patch.object(daily_report_service, "_power_values", return_value={}), patch.object(daily_report_service, "_upcoming_power_lines", return_value=[]):
            daily_report_service.update_workspace_report(
                self.db,
                self.identity,
                "2026-08-02",
                DailyReportUpdateRequest(
                    title="HEIGO 联赛日报｜8月2日",
                    content="今日赛果。\n\n【焦点头版】\nBrighton & Hove Albion 8:5 Como 1907。",
                    publish=True,
                ),
            )
            public = daily_report_service.get_public_report(self.db, "2026-08-02")

        self.assertIn("布莱顿 8:5 科莫", public.content)
        self.assertNotIn("Brighton & Hove Albion", public.content)

    def test_double_forfeit_does_not_invent_a_winner(self):
        self.db.add(Match(
            season_label="test",
            level="超级",
            round_no=4,
            home_team_name="Team Alpha",
            away_team_name="Team Beta",
            home_score=0,
            away_score=0,
            status="double_forfeit",
            created_at=datetime(2026, 8, 2, 20, 0),
            updated_at=datetime(2026, 8, 2, 20, 0),
        ))
        self.db.commit()

        with patch.object(daily_report_service, "_power_values", return_value={}), patch.object(daily_report_service, "_upcoming_power_lines", return_value=[]):
            report = daily_report_service.build_daily_report(self.db, "2026-08-02")

        self.assertIn("Team Alpha 与 Team Beta 本场均被判负", report.content)
        self.assertNotIn("比赛胜方", report.content)

    def test_away_win_reports_winner_first_score(self):
        self.db.add(Match(
            season_label="test",
            level="甲级",
            round_no=5,
            home_team_name="Home FC",
            away_team_name="Away FC",
            home_score=1,
            away_score=5,
            status="played",
            created_at=datetime(2026, 8, 2, 20, 0),
            updated_at=datetime(2026, 8, 2, 20, 0),
        ))
        self.db.commit()

        with patch.object(daily_report_service, "_power_values", return_value={}), patch.object(daily_report_service, "_upcoming_power_lines", return_value=[]):
            report = daily_report_service.build_daily_report(self.db, "2026-08-02")

        self.assertIn("Away FC 5:1", report.content)
        self.assertIn("Home FC", report.content)
        self.assertNotIn("Away FC 1:5", report.content)

    def test_template_crud_and_placeholder_validation(self):
        created = daily_report_service.create_template(
            self.db,
            self.identity,
            DailyReportNarrativeTemplateUpsertRequest(
                category="narrow_win",
                name="自定义险胜",
                template_text="{winner} {score} 险胜 {loser}。",
                is_active=True,
                sort_order=5,
            ),
        )
        self.assertEqual(created.name, "自定义险胜")
        self.assertTrue(self.db.query(DailyReportNarrativeTemplate).filter_by(id=created.id).first())

        with self.assertRaisesRegex(Exception, "不支持的占位符"):
            daily_report_service.create_template(
                self.db,
                self.identity,
                DailyReportNarrativeTemplateUpsertRequest(
                    category="narrow_win",
                    name="错误话术",
                    template_text="{unknown_field}",
                ),
            )

    def test_disabling_every_template_in_category_stops_that_narrative(self):
        daily_report_service.create_template(
            self.db,
            self.identity,
            DailyReportNarrativeTemplateUpsertRequest(
                category="narrow_win",
                name="停用险胜",
                template_text="{winner} {score} 险胜 {loser}。",
                is_active=False,
            ),
        )
        daily_report_service.create_template(
            self.db,
            self.identity,
            DailyReportNarrativeTemplateUpsertRequest(
                category="regular_win",
                name="保留其他类别",
                template_text="{winner} 击败 {loser}。",
                is_active=True,
            ),
        )

        pool = daily_report_service._template_pool(self.db)

        self.assertEqual(daily_report_service._render_template(pool, "narrow_win", {"winner": "A", "loser": "B", "score": "1:0"}, "test"), "")
        self.assertTrue(daily_report_service._render_template(pool, "regular_win", {"winner": "A", "loser": "B"}, "test"))


if __name__ == "__main__":
    unittest.main()
