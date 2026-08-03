import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


BOT_PLUGIN_PARENT = Path(__file__).resolve().parent / "bot_nonebot" / "src" / "plugins"
if str(BOT_PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(BOT_PLUGIN_PARENT))

from heigo_bot.parser import parse_command  # noqa: E402


class BotNoneBotParserTests(unittest.TestCase):
    def test_parse_player_image_command_with_version(self):
        command = parse_command("球员图 梅西 v2026-03")
        self.assertEqual(command.command_type, "player_image")
        self.assertEqual(command.keyword, "梅西")
        self.assertEqual(command.version, "2026-03")

    def test_parse_player_image_command_with_growth_step(self):
        command = parse_command("球员图 梅西 +2 v2026-03")
        self.assertEqual(command.command_type, "player_image")
        self.assertEqual(command.keyword, "梅西")
        self.assertEqual(command.step, 2)
        self.assertEqual(command.version, "2026-03")

    def test_parse_roster_command(self):
        command = parse_command("名单 Barcelona")
        self.assertEqual(command.command_type, "roster_text")
        self.assertEqual(command.team_name, "Barcelona")
        self.assertEqual(command.page, 1)

    def test_parse_roster_command_with_page(self):
        command = parse_command("名单 Barcelona 第2页")
        self.assertEqual(command.command_type, "roster_text")
        self.assertEqual(command.team_name, "Barcelona")
        self.assertEqual(command.page, 2)

    def test_parse_roster_image_command_with_short_page(self):
        command = parse_command("名单图 巴萨 2页")
        self.assertEqual(command.command_type, "roster_image")
        self.assertEqual(command.team_name, "巴萨")
        self.assertEqual(command.page, 2)

    def test_parse_roster_command_with_p_page_suffix(self):
        command = parse_command("名单 巴萨 p3")
        self.assertEqual(command.command_type, "roster_text")
        self.assertEqual(command.team_name, "巴萨")
        self.assertEqual(command.page, 3)

    def test_parse_help_when_empty(self):
        command = parse_command("")
        self.assertEqual(command.command_type, "help")

    def test_parse_wage_text_command(self):
        command = parse_command("工资 梅西")
        self.assertEqual(command.command_type, "wage_text")
        self.assertEqual(command.keyword, "梅西")

    def test_parse_wage_image_command(self):
        command = parse_command("工资图 梅西")
        self.assertEqual(command.command_type, "wage_image")
        self.assertEqual(command.keyword, "梅西")

    def test_parse_football_news_command(self):
        for text in ("新闻", "足球新闻", "懂球帝", "懂球帝新闻"):
            with self.subTest(text=text):
                command = parse_command(text)
                self.assertEqual(command.command_type, "football_news")

    def test_parse_football_daily_command(self):
        for text in ("早报", "足球早报", "懂球帝早报"):
            with self.subTest(text=text):
                command = parse_command(text)
                self.assertEqual(command.command_type, "football_daily")

    def test_parse_heigo_daily_report_command(self):
        for text in ("联赛日报", "HEIGO日报", "今日联赛"):
            with self.subTest(text=text):
                command = parse_command(text)
                self.assertEqual(command.command_type, "heigo_daily_report")
                self.assertIsNone(command.report_date)
                self.assertEqual(command.date_error, "")

    def test_parse_heigo_daily_report_requested_date(self):
        cases = {
            "联赛日报 2026-08-02": "2026-08-02",
            "联赛日报 2026年8月2日": "2026-08-02",
            "8月2日联赛日报": "2026-08-02",
        }
        with patch("heigo_bot.parser._business_today", return_value=date(2026, 8, 3)):
            for text, expected in cases.items():
                with self.subTest(text=text):
                    command = parse_command(text)
                    self.assertEqual(command.command_type, "heigo_daily_report")
                    self.assertEqual(command.report_date, expected)
                    self.assertEqual(command.date_error, "")

    def test_parse_heigo_daily_report_relative_date(self):
        cases = {
            "昨天联赛日报": "2026-08-02",
            "前天 HEIGO日报": "2026-08-01",
        }
        with patch("heigo_bot.parser._business_today", return_value=date(2026, 8, 3)):
            for text, expected in cases.items():
                with self.subTest(text=text):
                    command = parse_command(text)
                    self.assertEqual(command.report_date, expected)
                    self.assertEqual(command.date_error, "")

    def test_parse_heigo_daily_report_month_day_across_year(self):
        with patch("heigo_bot.parser._business_today", return_value=date(2026, 1, 2)):
            command = parse_command("联赛日报 12月31日")
        self.assertEqual(command.report_date, "2025-12-31")
        self.assertEqual(command.date_error, "")

    def test_parse_heigo_daily_report_rejects_invalid_or_future_date(self):
        with patch("heigo_bot.parser._business_today", return_value=date(2026, 8, 3)):
            invalid = parse_command("联赛日报 2月30日")
            future = parse_command("联赛日报 2026-08-04")
        self.assertIsNone(invalid.report_date)
        self.assertIn("日期无效", invalid.date_error)
        self.assertIsNone(future.report_date)
        self.assertIn("不能晚于今天", future.date_error)

    def test_parse_league_standings_commands(self):
        cases = {
            "积分榜": "超级",
            "超级积分榜": "超级",
            "积分榜 甲级": "甲级",
            "乙级联赛积分榜": "乙级",
            "联赛排名 甲": "甲级",
        }
        for text, level in cases.items():
            with self.subTest(text=text):
                command = parse_command(text)
                self.assertEqual(command.command_type, "league_standings")
                self.assertEqual(command.level, level)
                self.assertEqual(command.level_error, "")

    def test_parse_league_suspension_commands(self):
        cases = {
            "伤停": "超级",
            "超级伤停": "超级",
            "甲级伤停统计": "甲级",
            "联赛伤停 乙级": "乙级",
            "乙级伤停榜": "乙级",
        }
        for text, level in cases.items():
            with self.subTest(text=text):
                command = parse_command(text)
                self.assertEqual(command.command_type, "league_suspensions")
                self.assertEqual(command.level, level)
                self.assertEqual(command.level_error, "")

    def test_parse_league_report_rejects_unknown_level(self):
        command = parse_command("冠军杯积分榜")

        self.assertEqual(command.command_type, "league_standings")
        self.assertIsNone(command.level)
        self.assertIn("超级、甲级、乙级", command.level_error)

    def test_parse_rating_ranking_commands(self):
        for text in ("排位", "排位榜", "排位排行榜", "排位积分榜"):
            with self.subTest(text=text):
                command = parse_command(text)
                self.assertEqual(command.command_type, "rating_rankings")
                self.assertIsNone(command.level)

    def test_parse_player_ranking_commands(self):
        cases = {
            "球员数据榜": ("超级", "goals"),
            "甲级射手榜": ("甲级", "goals"),
            "助攻榜 乙级": ("乙级", "assists"),
            "超级最佳球员榜": ("超级", "mvps"),
            "MVP榜 甲": ("甲级", "mvps"),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                command = parse_command(text)
                self.assertEqual(command.command_type, "player_rankings")
                self.assertEqual((command.level, command.metric), expected)
                self.assertEqual(command.level_error, "")

    def test_parse_player_ranking_rejects_unknown_level(self):
        command = parse_command("冠军杯助攻榜")

        self.assertEqual(command.command_type, "player_rankings")
        self.assertIsNone(command.level)
        self.assertIn("超级、甲级、乙级", command.level_error)

    def test_parse_roster_image_command(self):
        command = parse_command("名单图 Barcelona")
        self.assertEqual(command.command_type, "roster_image")
        self.assertEqual(command.team_name, "Barcelona")
        self.assertEqual(command.page, 1)
