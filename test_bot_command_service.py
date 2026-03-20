import sys
import unittest
from pathlib import Path


BOT_ROOT = Path(__file__).resolve().parent / "bot"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from app.services.command_service import parse_command  # noqa: E402


class BotCommandServiceTests(unittest.TestCase):
    def test_parse_player_image_command_with_version(self):
        command = parse_command("@机器人 球员图 梅西 v2026-03")
        self.assertEqual(command.command_type, "player_image")
        self.assertEqual(command.keyword, "梅西")
        self.assertEqual(command.version, "2026-03")

    def test_parse_roster_command_with_page(self):
        command = parse_command("名单 Barcelona 第2页")
        self.assertEqual(command.command_type, "roster")
        self.assertEqual(command.team_name, "Barcelona")
        self.assertEqual(command.page, 2)

    def test_parse_help_when_empty(self):
        command = parse_command("")
        self.assertEqual(command.command_type, "help")
