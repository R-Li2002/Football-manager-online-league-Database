import time
import unittest

from services import share_signature_service


class ShareSignatureServiceTests(unittest.TestCase):
    def test_sign_player_render_request_is_stable(self):
        signature = share_signature_service.sign_player_render_request(
            "secret-key",
            uid=24048100,
            version="2026-03",
            step=2,
            theme="dark",
            exp=1_800_000_000,
        )

        self.assertEqual(
            signature,
            share_signature_service.sign_player_render_request(
                "secret-key",
                uid=24048100,
                version="2026-03",
                step=2,
                theme="dark",
                exp=1_800_000_000,
            ),
        )

    def test_validate_player_render_signature_accepts_valid_signature(self):
        exp = int(time.time()) + 60
        signature = share_signature_service.sign_player_render_request(
            "secret-key",
            uid=24048100,
            version="2026-03",
            step=0,
            theme="dark",
            exp=exp,
        )

        result = share_signature_service.validate_player_render_signature(
            "secret-key",
            uid=24048100,
            version="2026-03",
            step=0,
            theme="dark",
            exp=exp,
            provided_signature=signature,
            now_ts=exp - 1,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.detail, "ok")

    def test_validate_wage_render_signature_accepts_valid_signature(self):
        exp = int(time.time()) + 60
        signature = share_signature_service.sign_wage_render_request(
            "secret-key",
            uid=24048100,
            theme="dark",
            exp=exp,
        )

        result = share_signature_service.validate_wage_render_signature(
            "secret-key",
            uid=24048100,
            theme="dark",
            exp=exp,
            provided_signature=signature,
            now_ts=exp - 1,
        )

        self.assertTrue(result.ok)

    def test_validate_roster_render_signature_accepts_valid_signature(self):
        exp = int(time.time()) + 60
        signature = share_signature_service.sign_roster_render_request(
            "secret-key",
            team_name="Barcelona",
            page=2,
            theme="dark",
            exp=exp,
        )

        result = share_signature_service.validate_roster_render_signature(
            "secret-key",
            team_name="Barcelona",
            page=2,
            theme="dark",
            exp=exp,
            provided_signature=signature,
            now_ts=exp - 1,
        )

        self.assertTrue(result.ok)

    def test_validate_player_render_signature_rejects_expired_url(self):
        result = share_signature_service.validate_player_render_signature(
            "secret-key",
            uid=24048100,
            version="2026-03",
            step=0,
            theme="dark",
            exp=1,
            provided_signature="anything",
            now_ts=2,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.detail, "render_url_expired")

    def test_validate_player_render_signature_rejects_invalid_signature(self):
        exp = int(time.time()) + 60
        result = share_signature_service.validate_player_render_signature(
            "secret-key",
            uid=24048100,
            version="2026-03",
            step=0,
            theme="dark",
            exp=exp,
            provided_signature="invalid",
            now_ts=exp - 1,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.detail, "invalid_signature")
