import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


BOT_ROOT = Path(__file__).resolve().parent / "bot"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from app.config import BotSettings  # noqa: E402
from app.main import create_app  # noqa: E402


class BotHealthRouteTests(unittest.TestCase):
    def test_health_reports_config_summary_in_echo_mode(self):
        settings = BotSettings(
            heigo_base_url="http://heigo.test",
            bot_reply_mode="echo_response",
            onebot_access_token="token",
            onebot_secret="secret",
            onebot_self_id="10001",
            internal_share_token="share-token",
            qq_bot_allowed_groups=("100", "200"),
        )
        app = create_app(settings)
        client = TestClient(app)

        with patch("app.clients.heigo_client.HeigoClient.get_health", new=AsyncMock(return_value={"status": "ok"})):
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["reply_mode"], "echo_response")
        self.assertEqual(payload["onebot_api"], "disabled")
        self.assertTrue(payload["config"]["onebot_access_token_configured"])
        self.assertTrue(payload["config"]["onebot_secret_configured"])
        self.assertTrue(payload["config"]["onebot_self_id_configured"])
        self.assertTrue(payload["config"]["internal_share_token_configured"])
        self.assertEqual(payload["config"]["allowed_group_count"], 2)

    def test_health_returns_503_when_heigo_health_is_not_ok(self):
        settings = BotSettings(heigo_base_url="http://heigo.test")
        app = create_app(settings)
        client = TestClient(app)

        with patch("app.clients.heigo_client.HeigoClient.get_health", new=AsyncMock(return_value={"status": "degraded"})):
            response = client.get("/health")

        self.assertEqual(response.status_code, 503)
        detail = response.json()["detail"]
        self.assertEqual(detail["status"], "error")
        self.assertEqual(detail["heigo_api"], "degraded")

    def test_health_returns_503_when_onebot_is_offline(self):
        settings = BotSettings(
            heigo_base_url="http://heigo.test",
            bot_reply_mode="onebot",
        )
        app = create_app(settings)
        client = TestClient(app)

        with patch("app.clients.heigo_client.HeigoClient.get_health", new=AsyncMock(return_value={"status": "ok"})):
            with patch(
                "app.clients.onebot_client.OneBotClient.get_status",
                new=AsyncMock(return_value={"status": "ok", "online": False, "good": False}),
            ):
                response = client.get("/health")

        self.assertEqual(response.status_code, 503)
        detail = response.json()["detail"]
        self.assertEqual(detail["status"], "error")
        self.assertEqual(detail["onebot_api"], "offline")
        self.assertFalse(detail["onebot_status"]["online"])
