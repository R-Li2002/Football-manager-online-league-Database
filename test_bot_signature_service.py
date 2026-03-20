import hashlib
import hmac
import json
import sys
from pathlib import Path
from unittest import TestCase

from fastapi.testclient import TestClient


BOT_ROOT = Path(__file__).resolve().parent / "bot"
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from app.config import BotSettings  # noqa: E402
from app.main import create_app  # noqa: E402


class BotSignatureServiceTests(TestCase):
    def test_onebot_signature_allows_valid_signed_request(self):
        settings = BotSettings(
            heigo_base_url="http://heigo.test",
            onebot_self_id="10001",
            onebot_secret="shared-secret",
            qq_bot_allow_all_groups=True,
        )
        app = create_app(settings)
        client = TestClient(app)
        payload = {
            "post_type": "message",
            "message_type": "group",
            "message_id": 201,
            "group_id": 20001,
            "user_id": 30001,
            "raw_message": "[CQ:at,qq=10001] 帮助",
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        signature = "sha1=" + hmac.new(settings.onebot_secret.encode("utf-8"), body, hashlib.sha1).hexdigest()

        response = client.post(
            "/onebot/events",
            content=body,
            headers={"Content-Type": "application/json", "X-Signature": signature},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ack"])
        self.assertTrue(response.json()["handled"])

    def test_onebot_signature_rejects_invalid_signature(self):
        settings = BotSettings(
            heigo_base_url="http://heigo.test",
            onebot_self_id="10001",
            onebot_secret="shared-secret",
            qq_bot_allow_all_groups=True,
        )
        app = create_app(settings)
        client = TestClient(app)

        response = client.post(
            "/onebot/events",
            json={
                "post_type": "message",
                "message_type": "group",
                "message_id": 202,
                "group_id": 20001,
                "user_id": 30001,
                "raw_message": "[CQ:at,qq=10001] 帮助",
            },
            headers={"X-Signature": "sha1=deadbeef"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["ack"])
        self.assertTrue(response.json()["ignored"])
        self.assertEqual(response.json()["reason"], "invalid_signature")
