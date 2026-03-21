import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import httpx


BOT_ROOT = Path(__file__).resolve().parent / "bot"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from app.config import BotSettings  # noqa: E402
from app.main import create_app  # noqa: E402


class BotCallbackRouteTests(unittest.TestCase):
    def test_callback_returns_echo_payload_for_allowed_group(self):
        settings = BotSettings(
            heigo_base_url="http://heigo.test",
            onebot_self_id="10001",
            qq_bot_allow_all_groups=True,
        )
        app = create_app(settings)
        client = TestClient(app)
        response = client.post(
            "/onebot/events",
            json={
                "post_type": "message",
                "message_type": "group",
                "message_id": 101,
                "group_id": 20001,
                "user_id": 30001,
                "raw_message": "[CQ:at,qq=10001] 帮助",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ack"])
        self.assertTrue(payload["handled"])

    def test_callback_returns_204_in_onebot_mode(self):
        settings = BotSettings(
            heigo_base_url="http://heigo.test",
            onebot_self_id="10001",
            qq_bot_allow_all_groups=True,
            bot_reply_mode="onebot",
        )
        app = create_app(settings)
        client = TestClient(app)
        response = client.post(
            "/onebot/events",
            json={
                "post_type": "message",
                "message_type": "group",
                "message_id": 104,
                "group_id": 20001,
                "user_id": 30001,
                "raw_message": "[CQ:at,qq=10001] 帮助",
            },
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.text, "")

    def test_callback_rejects_non_whitelisted_group(self):
        settings = BotSettings(
            heigo_base_url="http://heigo.test",
            onebot_self_id="10001",
            qq_bot_allowed_groups=("group-allow",),
        )
        app = create_app(settings)
        client = TestClient(app)
        response = client.post(
            "/onebot/events",
            json={
                "post_type": "message",
                "message_type": "group",
                "message_id": 102,
                "group_id": "group-deny",
                "user_id": 30001,
                "raw_message": "[CQ:at,qq=10001] 帮助",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ack"])
        self.assertTrue(payload["ignored"])
        self.assertEqual(payload["reason"], "group_not_allowed")

    def test_callback_acks_and_degrades_when_handler_raises(self):
        settings = BotSettings(
            heigo_base_url="http://heigo.test",
            onebot_self_id="10001",
            qq_bot_allow_all_groups=True,
        )
        app = create_app(settings)
        client = TestClient(app)

        with patch("app.routers.onebot_routes.build_reply", new=AsyncMock(side_effect=httpx.ConnectError("heigo down"))):
            response = client.post(
                "/onebot/events",
                json={
                    "post_type": "message",
                    "message_type": "group",
                    "message_id": 103,
                    "group_id": 20001,
                    "user_id": 30001,
                    "raw_message": "[CQ:at,qq=10001] 帮助",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ack"])
        self.assertFalse(payload["handled"])
        self.assertEqual(payload["reason"], "heigo_request_error")
        self.assertEqual(payload["reply"]["reply_type"], "text")
        self.assertIn("HEIGO", payload["reply"]["text"])
