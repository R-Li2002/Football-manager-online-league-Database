import sys
import tempfile
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock


BOT_ROOT = Path(__file__).resolve().parent / "bot"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from app.clients.onebot_client import OneBotClient  # noqa: E402
from app.config import BotSettings  # noqa: E402
from app.schemas.bot_commands import PreparedReply  # noqa: E402


class BotOneBotClientTests(IsolatedAsyncioTestCase):
    async def test_dispatch_reply_degrades_image_to_text_when_image_send_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "player.png"
            image_path.write_bytes(b"png")
            client = OneBotClient(BotSettings(bot_reply_mode="onebot"))
            client._send_group_message = AsyncMock(side_effect=[RuntimeError("image send failed"), {"status": "ok"}])

            try:
                result = await client.dispatch_reply(
                    message_type="group",
                    group_id="20001",
                    user_id="30001",
                    message_id="101",
                    reply=PreparedReply(
                        reply_type="image",
                        text="Dani Olmo 球员图",
                        meta={"image_path": str(image_path), "fallback_text": "fallback text"},
                    ),
                )
            finally:
                await client.aclose()

            self.assertTrue(result["delivered"])
            self.assertEqual(result["reply_type"], "text")
            self.assertEqual(result["degraded_from"], "image")

    async def test_dispatch_reply_returns_delivered_false_when_text_send_fails(self):
        client = OneBotClient(BotSettings(bot_reply_mode="onebot"))
        client._send_group_message = AsyncMock(side_effect=RuntimeError("send failed"))

        try:
            result = await client.dispatch_reply(
                message_type="group",
                group_id="20001",
                user_id="30001",
                message_id="101",
                reply=PreparedReply(reply_type="text", text="hello"),
            )
        finally:
            await client.aclose()

        self.assertFalse(result["delivered"])
        self.assertEqual(result["reply_type"], "text")
        self.assertIn("send failed", result["error"])

    async def test_dispatch_reply_returns_delivered_false_when_image_and_fallback_both_fail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "player.png"
            image_path.write_bytes(b"png")
            client = OneBotClient(BotSettings(bot_reply_mode="onebot"))
            client._send_group_message = AsyncMock(side_effect=[RuntimeError("image send failed"), RuntimeError("fallback send failed")])

            try:
                result = await client.dispatch_reply(
                    message_type="group",
                    group_id="20001",
                    user_id="30001",
                    message_id="101",
                    reply=PreparedReply(
                        reply_type="image",
                        text="Dani Olmo 球员图",
                        meta={"image_path": str(image_path), "fallback_text": "fallback text"},
                    ),
                )
            finally:
                await client.aclose()

            self.assertFalse(result["delivered"])
            self.assertEqual(result["reply_type"], "image")
            self.assertEqual(result["degraded_from"], "image")
            self.assertIn("fallback send failed", result["fallback_error"])
