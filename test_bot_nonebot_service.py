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
    async def get_player_attribute_detail(self, uid: int, version: str | None = None):
        return {"uid": uid, "name": "Dani Olmo", "data_version": version or "2026-03"}

    async def search_player_attributes(self, keyword: str, version: str | None = None):
        return [{"uid": 24048100, "name": "Dani Olmo"}]

    async def get_player_wage_detail(self, uid: int):
        return {"wage": 0.91}

    async def get_players_by_team(self, team_name: str):
        return [{"uid": 1}, {"uid": 2}, {"uid": 3}]


class _FakeSigner:
    def build_player_png_url(self, uid: int, *, version: str | None = None, step: int = 0, theme: str | None = None):
        return f"https://example.com/player/{uid}.png"

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

    def test_handle_wage_image(self):
        reply = asyncio.run(self.service.handle_command(CommandSpec(command_type="wage_image", raw_text="", normalized_text="", keyword="Dani")))
        self.assertEqual(reply.reply_type, "image")
        self.assertIn("wage/24048100.png", reply.image_url)

    def test_handle_roster_image(self):
        reply = asyncio.run(self.service.handle_command(CommandSpec(command_type="roster_image", raw_text="", normalized_text="", team_name="Barcelona", page=2)))
        self.assertEqual(reply.reply_type, "image")
        self.assertIn("roster/Barcelona/1.png", reply.image_url)

    def test_handle_help(self):
        reply = asyncio.run(self.service.handle_text("帮助"))
        self.assertEqual(reply.reply_type, "text")
        self.assertIn("球员图", reply.text)
