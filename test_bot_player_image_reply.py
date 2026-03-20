import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock


BOT_ROOT = Path(__file__).resolve().parent / "bot"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from app.config import BotSettings  # noqa: E402
from app.schemas.bot_commands import BotCommand  # noqa: E402
from app.services.reply_service import build_reply  # noqa: E402


class BotPlayerImageReplyTests(IsolatedAsyncioTestCase):
    async def test_player_image_reply_returns_image_meta_when_render_succeeds(self):
        client = AsyncMock()
        client.get_player_attribute_detail = AsyncMock(
            return_value={
                "uid": 24048100,
                "name": "Dani Olmo",
                "data_version": "2026-03",
            }
        )

        render_service = AsyncMock()
        render_service.render_player_share = AsyncMock(
            return_value=(
                "http://heigo.test/internal/share/player/24048100?version=2026-03&step=0&theme=dark",
                SimpleNamespace(
                    file_path="output/qqbot/player-shares/Dani_Olmo_24048100_2026-03_step0.png",
                    file_name="Dani_Olmo_24048100_2026-03_step0.png",
                    mime_type="image/png",
                ),
            )
        )

        command = BotCommand(
            command_type="player_image",
            raw_text="@机器人 球员图 Dani Olmo",
            normalized_text="球员图 Dani Olmo",
            uid=24048100,
            keyword="Dani Olmo",
        )
        reply = await build_reply(command, client, BotSettings(), render_service)

        self.assertEqual(reply.reply_type, "image")
        self.assertEqual(reply.meta["uid"], 24048100)
        self.assertTrue(reply.meta["image_path"].endswith(".png"))

    async def test_wage_reply_returns_clear_message_when_detail_is_missing(self):
        client = AsyncMock()
        client.get_player_attribute_detail = AsyncMock(return_value=None)
        client.get_player_wage_detail = AsyncMock(return_value={"wage": 1.23})

        command = BotCommand(
            command_type="wage",
            raw_text="@机器人 工资 24048100",
            normalized_text="工资 24048100",
            uid=24048100,
            keyword="24048100",
        )
        reply = await build_reply(command, client, BotSettings(), render_service=None)

        self.assertEqual(reply.reply_type, "text")
        self.assertIn("未找到 UID 24048100 的球员详情", reply.text)
        client.get_player_wage_detail.assert_not_called()
