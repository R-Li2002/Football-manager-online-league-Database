import sys
import tempfile
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
from types import MethodType


BOT_ROOT = Path(__file__).resolve().parent / "bot"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from app.clients.onebot_client import OneBotClient  # noqa: E402
from app.config import BotSettings  # noqa: E402
from app.schemas.bot_commands import PreparedReply  # noqa: E402


class BotOneBotClientTests(IsolatedAsyncioTestCase):
    async def test_build_image_message_uses_absolute_file_uri(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "player.png"
            image_path.write_bytes(b"png")
            client = OneBotClient(BotSettings(bot_reply_mode="onebot"))

            try:
                message = client._build_image_message(
                    PreparedReply(reply_type="image", text="hello", meta={"image_path": str(image_path)}),
                    reply_to="101",
                )
            finally:
                await client.aclose()

            self.assertEqual(message[0]["type"], "reply")
            self.assertEqual(message[1]["type"], "text")
            self.assertEqual(message[2]["type"], "image")
            self.assertTrue(message[2]["data"]["file"].startswith("file:///"))
            self.assertTrue(message[2]["data"]["file"].endswith("/player.png"))

    async def test_get_status_accepts_retcode_zero(self):
        client = OneBotClient(BotSettings(bot_reply_mode="onebot"))
        seen_actions: list[str] = []

        async def fake_post_action(self, action, params=None):
            seen_actions.append(action)
            return {
                "status": "ok",
                "retcode": 0,
                "data": {"online": True, "good": True},
            }

        client._post_action = MethodType(fake_post_action, client)

        try:
            result = await client.get_status()
        finally:
            await client.aclose()

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["online"])
        self.assertTrue(result["good"])
        self.assertEqual(seen_actions, ["get_status"])

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
