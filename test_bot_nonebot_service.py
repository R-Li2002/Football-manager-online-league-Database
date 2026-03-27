import asyncio
import sys
import unittest
from pathlib import Path


BOT_PLUGIN_PARENT = Path(__file__).resolve().parent / "bot_nonebot" / "src" / "plugins"
if str(BOT_PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(BOT_PLUGIN_PARENT))

from heigo_bot.config import BotSettings  # noqa: E402
from heigo_bot.models import CommandSpec  # noqa: E402
from heigo_bot.service import HeigoBotService  # noqa: E402


class _FakeApiClient:
    async def get_teams(self):
        return [
            {"name": "A. Madrid"},
            {"name": "Bayer 04"},
            {"name": "Barcelona"},
            {"name": "FC Bayern"},
            {"name": "Man City"},
            {"name": "Man UFC"},
            {"name": "Sporting CP"},
            {"name": "Tottenham"},
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


class BotNoneBotServiceTests(unittest.TestCase):
    def setUp(self):
        settings = BotSettings(
            heigo_base_url="http://heigo:8080",
            heigo_render_base_url="http://heigo:8080",
            internal_render_signing_key="secret",
            heigo_render_ttl_seconds=90,
            bot_default_theme="dark",
            bot_roster_page_size=16,
            qq_bot_allowed_groups=(),
            qq_bot_allow_all_groups=False,
            bot_user_cooldown_seconds=5,
            bot_group_limit_per_minute=20,
        )
        self.service = HeigoBotService(_FakeApiClient(), _FakeSigner(), settings)

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

    def test_handle_roster_image_supports_alias(self):
        reply = asyncio.run(self.service.handle_command(CommandSpec(command_type="roster_image", raw_text="", normalized_text="", team_name="巴萨", page=1)))
        self.assertEqual(reply.reply_type, "image")
        self.assertIn("roster/Barcelona/1.png", reply.image_url)

    def test_handle_roster_image_supports_real_name_mismatch_aliases(self):
        cases = {
            "曼联": "Man UFC",
            "药厂": "Bayer 04",
            "葡体": "Sporting CP",
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
            "拜仁": "FC Bayern",
            "曼城": "Man City",
            "托特纳姆热刺": "Tottenham",
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

    def test_handle_roster_text(self):
        reply = asyncio.run(self.service.handle_command(CommandSpec(command_type="roster_text", raw_text="", normalized_text="", team_name="Barcelona", page=1)))
        self.assertEqual(reply.reply_type, "text")
        self.assertIn("Barcelona 名单 第 1/1 页", reply.text)
        self.assertIn("1. Player 1 | GK | 20岁 | CA/PA 140 / 155 | 工资 0.500M | 名额 8M", reply.text)

    def test_handle_help(self):
        reply = asyncio.run(self.service.handle_text("帮助"))
        self.assertEqual(reply.reply_type, "text")
        self.assertIn("球员图", reply.text)
