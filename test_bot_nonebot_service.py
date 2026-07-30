import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


BOT_PLUGIN_PARENT = Path(__file__).resolve().parent / "bot_nonebot" / "src" / "plugins"
if str(BOT_PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(BOT_PLUGIN_PARENT))

from heigo_bot.config import BotSettings  # noqa: E402
from heigo_bot.models import CommandSpec  # noqa: E402
from heigo_bot.news_service import NewsItem  # noqa: E402
from heigo_bot.service import HeigoBotService, TEAM_ALIASES  # noqa: E402


class _FakeApiClient:
    async def get_teams(self):
        return [
            {"name": "A. Madrid"},
            {"name": "Bayer 04 Leverkusen"},
            {"name": "Barcelona"},
            {"name": "FC Bayern München"},
            {"name": "FC Schalke 04"},
            {"name": "Leicester City"},
            {"name": "Manchester City"},
            {"name": "Manchester United"},
            {"name": "Sporting Clube de Portugal"},
            {"name": "Tottenham Hotspur"},
        ]

    async def get_player_attribute_detail(self, uid: int, version: str | None = None):
        return {
            "uid": uid,
            "name": "Dani Olmo",
            "data_version": version or "2026-03",
            "position": "M/AM C",
            "age": 27,
            "heigo_club": "Barcelona",
        }

    async def search_player_attributes(self, keyword: str, version: str | None = None):
        return [{"uid": 24048100, "name": "Dani Olmo"}]

    async def get_player_wage_detail(self, uid: int):
        return {
            "initial_value": 7.0,
            "current_value": 7.0,
            "potential_value": 7.0,
            "final_value": 7.0,
            "initial_field": 7.0,
            "slot_type": "7M",
            "coefficient": 0.13,
            "wage": 0.91,
        }

    async def get_players_by_team(self, team_name: str):
        return [
            {"uid": 1, "name": "Player 1", "position": "GK", "age": 20, "ca": 140, "pa": 155, "wage": 0.5, "slot_type": "8M"},
            {"uid": 2, "name": "Player 2", "position": "MC", "age": 21, "ca": 141, "pa": 156, "wage": 0.51, "slot_type": ""},
            {"uid": 3, "name": "Player 3", "position": "MC", "age": 22, "ca": 142, "pa": 157, "wage": 0.52, "slot_type": ""},
        ]


class _FakeSigner:
    def build_player_png_url(self, uid: int, *, version: str | None = None, step: int = 0, theme: str | None = None):
        return f"https://example.com/player/{uid}.png?step={step}"

    def build_wage_png_url(self, uid: int, *, theme: str | None = None):
        return f"https://example.com/wage/{uid}.png"

    def build_roster_png_url(self, team_name: str, *, page: int = 1, theme: str | None = None):
        return f"https://example.com/roster/{team_name}/{page}.png"


class _FakeNewsService:
    async def get_top_news(self):
        return [
            NewsItem(title="转会窗口开启", link="https://example.com/news/1", published="06-19 09:00"),
            NewsItem(title="欧冠抽签完成", link="https://example.com/news/2", published="06-19 09:30"),
        ]

    async def get_daily(self):
        return [NewsItem(title="懂球帝早报标题", link="https://example.com/daily/1", published="06-19 08:00")]


class BotNoneBotServiceTests(unittest.TestCase):
    def setUp(self):
        settings = BotSettings(
            heigo_base_url="http://heigo:8080",
            heigo_render_base_url="http://heigo:8080",
            internal_render_signing_key="secret",
            heigo_render_ttl_seconds=90,
            bot_default_theme="dark",
            bot_roster_page_size=2,
            qq_bot_allowed_groups=(),
            qq_bot_allow_all_groups=False,
            bot_user_cooldown_seconds=5,
            bot_group_limit_per_minute=20,
        )
        self.service = HeigoBotService(_FakeApiClient(), _FakeSigner(), settings, _FakeNewsService())

    def test_handle_player_image(self):
        reply = asyncio.run(self.service.handle_command(CommandSpec(command_type="player_image", raw_text="", normalized_text="", keyword="Dani")))
        self.assertEqual(reply.reply_type, "image")
        self.assertIn("player/24048100.png", reply.image_url)
        self.assertIn("当前属性", reply.text)

    def test_handle_player_image_with_growth_preview_step(self):
        reply = asyncio.run(
            self.service.handle_command(CommandSpec(command_type="player_image", raw_text="", normalized_text="", keyword="Dani", step=2))
        )
        self.assertEqual(reply.reply_type, "image")
        self.assertIn("step=2", reply.image_url)
        self.assertIn("成长预览 +2", reply.text)

    def test_resolve_player_command_returns_structured_candidates(self):
        self.service.api_client.search_player_attributes = AsyncMock(
            return_value=[
                {"uid": 101, "name": "Dani Alves", "heigo_club": "Barcelona"},
                {"uid": 102, "name": "Dani Parejo", "heigo_club": "Valencia"},
            ]
        )
        command = CommandSpec(
            command_type="player_image",
            raw_text="球员图 Dani",
            normalized_text="球员图 Dani",
            keyword="Dani",
        )

        resolution = asyncio.run(self.service.resolve_player_command(command))

        self.assertIsNone(resolution.command)
        self.assertIsNone(resolution.error)
        self.assertEqual([item["uid"] for item in resolution.candidates], [101, 102])

    def test_resolve_player_command_converts_selection_to_uid_command(self):
        self.service.api_client.search_player_attributes = AsyncMock(
            return_value=[{"uid": 24048100, "name": "Dani Olmo"}]
        )
        command = CommandSpec(
            command_type="wage_image",
            raw_text="工资图 Dani",
            normalized_text="工资图 Dani",
            keyword="Dani",
        )

        resolution = asyncio.run(self.service.resolve_player_command(command))

        self.assertIsNotNone(resolution.command)
        self.assertEqual(resolution.command.uid, 24048100)
        reply = asyncio.run(self.service.handle_command(resolution.command))
        self.assertEqual(reply.reply_type, "image")
        self.assertIn("wage/24048100.png", reply.image_url)

    def test_resolve_player_command_prefers_exact_name(self):
        self.service.api_client.search_player_attributes = AsyncMock(
            return_value=[
                {"uid": 101, "name": "Dani"},
                {"uid": 102, "name": "Dani Olmo"},
            ]
        )
        command = CommandSpec(
            command_type="player_image",
            raw_text="球员图 Dani",
            normalized_text="球员图 Dani",
            keyword="Dani",
        )

        resolution = asyncio.run(self.service.resolve_player_command(command))

        self.assertEqual(resolution.command.uid, 101)
        self.assertEqual(resolution.candidates, ())

    def test_handle_wage_image(self):
        reply = asyncio.run(self.service.handle_command(CommandSpec(command_type="wage_image", raw_text="", normalized_text="", keyword="Dani")))
        self.assertEqual(reply.reply_type, "image")
        self.assertIn("wage/24048100.png", reply.image_url)

    def test_handle_wage_text(self):
        reply = asyncio.run(self.service.handle_command(CommandSpec(command_type="wage_text", raw_text="", normalized_text="", keyword="Dani")))
        self.assertEqual(reply.reply_type, "text")
        self.assertIn("工资计算", reply.text)
        self.assertIn("结果工资 7.00 × 0.13 = 0.910M", reply.text)

    def test_handle_roster_image(self):
        reply = asyncio.run(self.service.handle_command(CommandSpec(command_type="roster_image", raw_text="", normalized_text="", team_name="Barcelona", page=2)))
        self.assertEqual(reply.reply_type, "image")
        self.assertIn("roster/Barcelona/1.png", reply.image_url)
        self.assertEqual(reply.text, "Barcelona 名单图 第 1/1 页")

    def test_handle_roster_image_uses_renderer_twenty_player_page_size(self):
        self.service.api_client.get_players_by_team = AsyncMock(
            return_value=[
                {"uid": index, "name": f"Player {index}", "position": "MC", "age": 20, "ca": 140, "pa": 150}
                for index in range(1, 22)
            ]
        )

        reply = asyncio.run(
            self.service.handle_command(
                CommandSpec(
                    command_type="roster_image",
                    raw_text="",
                    normalized_text="",
                    team_name="Barcelona",
                    page=2,
                )
            )
        )

        self.assertIn("roster/Barcelona/2.png", reply.image_url)
        self.assertEqual(reply.text, "Barcelona 名单图 第 2/2 页")

    def test_handle_roster_image_supports_alias(self):
        reply = asyncio.run(self.service.handle_command(CommandSpec(command_type="roster_image", raw_text="", normalized_text="", team_name="巴萨", page=1)))
        self.assertEqual(reply.reply_type, "image")
        self.assertIn("roster/Barcelona/1.png", reply.image_url)

    def test_handle_roster_image_supports_real_name_mismatch_aliases(self):
        cases = {
            "曼联": "Manchester United",
            "药厂": "Bayer 04 Leverkusen",
            "葡体": "Sporting Clube de Portugal",
            "沙尔克": "FC Schalke 04",
            "莱斯特城": "Leicester City",
        }
        for alias, team_name in cases.items():
            with self.subTest(alias=alias):
                reply = asyncio.run(
                    self.service.handle_command(
                        CommandSpec(command_type="roster_image", raw_text="", normalized_text="", team_name=alias, page=1)
                    )
                )
                self.assertEqual(reply.reply_type, "image")
                self.assertIn(f"roster/{team_name}/1.png", reply.image_url)

    def test_handle_roster_image_supports_expanded_aliases(self):
        cases = {
            "马竞": "A. Madrid",
            "拜仁": "FC Bayern München",
            "曼城": "Manchester City",
            "托特纳姆热刺": "Tottenham Hotspur",
        }
        for alias, team_name in cases.items():
            with self.subTest(alias=alias):
                reply = asyncio.run(
                    self.service.handle_command(
                        CommandSpec(command_type="roster_image", raw_text="", normalized_text="", team_name=alias, page=1)
                    )
                )
                self.assertEqual(reply.reply_type, "image")
                self.assertIn(f"roster/{team_name}/1.png", reply.image_url)

    def test_current_team_alias_table_covers_all_fifty_four_teams(self):
        self.assertEqual(len(TEAM_ALIASES), 54)

    def test_common_chinese_aliases_cover_all_three_levels(self):
        self.service.api_client.get_teams = AsyncMock(
            return_value=[
                {"name": "Associazione Sportiva Roma"},
                {"name": "Paris Saint-Germain"},
                {"name": "Club Atlético Boca Juniors"},
                {"name": "Sportklub Sturm Graz"},
            ]
        )
        cases = {
            "罗马": "Associazione Sportiva Roma",
            "大巴黎": "Paris Saint-Germain",
            "博卡青年": "Club Atlético Boca Juniors",
            "格拉茨风暴": "Sportklub Sturm Graz",
        }
        for alias, team_name in cases.items():
            with self.subTest(alias=alias):
                resolved, error = asyncio.run(self.service._resolve_team_name(alias))
                self.assertIsNone(error)
                self.assertEqual(resolved, team_name)

    def test_handle_roster_text(self):
        reply = asyncio.run(self.service.handle_command(CommandSpec(command_type="roster_text", raw_text="", normalized_text="", team_name="Barcelona", page=1)))
        self.assertEqual(reply.reply_type, "text")
        self.assertIn("Barcelona 名单 第 1/2 页，共 3 人", reply.text)
        self.assertIn("1. Player 1 | GK | 20岁 | CA/PA 140 / 155 | 工资 0.500M | 名额 8M", reply.text)
        self.assertIn("发送“名单 Barcelona 第2页”查看下一页。", reply.text)
        self.assertNotIn("3. Player 3", reply.text)

    def test_handle_roster_text_uses_requested_page(self):
        reply = asyncio.run(self.service.handle_command(CommandSpec(command_type="roster_text", raw_text="", normalized_text="", team_name="Barcelona", page=2)))
        self.assertEqual(reply.reply_type, "text")
        self.assertIn("Barcelona 名单 第 2/2 页，共 3 人", reply.text)
        self.assertIn("3. Player 3 | MC | 22岁 | CA/PA 142 / 157 | 工资 0.520M | 名额 -", reply.text)
        self.assertNotIn("Player 1", reply.text)

    def test_settings_from_env_honors_roster_page_size(self):
        with patch.dict("os.environ", {"BOT_ROSTER_PAGE_SIZE": "16"}, clear=False):
            settings = BotSettings.from_env()
        self.assertEqual(settings.bot_roster_page_size, 16)

    def test_settings_from_env_defaults_news_broadcast_groups_to_allowed_groups(self):
        with patch.dict("os.environ", {"QQ_BOT_ALLOWED_GROUPS": "123,456", "NEWS_BROADCAST_GROUPS": ""}, clear=False):
            settings = BotSettings.from_env()
        self.assertEqual(settings.news_broadcast_groups, ("123", "456"))

    def test_settings_from_env_honors_news_schedule(self):
        with patch.dict(
            "os.environ",
            {"NEWS_DAILY_HOUR": "9", "NEWS_HEADLINE_HOURS": "12,15,18", "NEWS_BROADCAST_GROUPS": "796068353"},
            clear=False,
        ):
            settings = BotSettings.from_env()
        self.assertEqual(settings.news_daily_hour, 9)
        self.assertEqual(settings.news_headline_hours, (12, 15, 18))
        self.assertEqual(settings.news_broadcast_groups, ("796068353",))

    def test_handle_football_news(self):
        reply = asyncio.run(self.service.handle_text("新闻"))
        self.assertEqual(reply.reply_type, "text")
        self.assertIn("懂球帝足球新闻", reply.text)
        self.assertIn("转会窗口开启", reply.text)
        self.assertIn("https://example.com/news/1", reply.text)

    def test_handle_football_daily(self):
        reply = asyncio.run(self.service.handle_text("早报"))
        self.assertEqual(reply.reply_type, "text")
        self.assertIn("懂球帝早报", reply.text)
        self.assertIn("懂球帝早报标题", reply.text)

    def test_handle_help(self):
        reply = asyncio.run(self.service.handle_text("帮助"))
        self.assertEqual(reply.reply_type, "text")
        self.assertIn("球员图", reply.text)
