import sys
import unittest
from pathlib import Path


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

    def test_parse_roster_image_command(self):
        command = parse_command("名单图 Barcelona")
        self.assertEqual(command.command_type, "roster_image")
        self.assertEqual(command.team_name, "Barcelona")
        self.assertEqual(command.page, 1)
