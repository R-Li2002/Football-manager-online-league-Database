import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from main1 import (
    get_session_cookie_secure_mode,
    request_uses_https,
    should_use_secure_session_cookie,
)


def build_request(*, scheme: str = "http", forwarded_proto: str | None = None):
    headers = {}
    if forwarded_proto is not None:
        headers["x-forwarded-proto"] = forwarded_proto
    return SimpleNamespace(headers=headers, url=SimpleNamespace(scheme=scheme))


class AdminSessionCookieTests(unittest.TestCase):
    def test_cookie_secure_mode_defaults_to_auto(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SESSION_COOKIE_SECURE", None)
            self.assertEqual(get_session_cookie_secure_mode(), "auto")

    def test_auto_mode_disables_secure_cookie_for_http_direct_access(self):
        with patch.dict(os.environ, {"SESSION_COOKIE_SECURE": "auto"}, clear=False):
            self.assertFalse(should_use_secure_session_cookie(build_request(scheme="http")))

    def test_auto_mode_enables_secure_cookie_for_https_forwarded_requests(self):
        with patch.dict(os.environ, {"SESSION_COOKIE_SECURE": "auto"}, clear=False):
            request = build_request(scheme="http", forwarded_proto="https")
            self.assertTrue(request_uses_https(request))
            self.assertTrue(should_use_secure_session_cookie(request))

    def test_explicit_true_overrides_request_scheme(self):
        with patch.dict(os.environ, {"SESSION_COOKIE_SECURE": "true"}, clear=False):
            self.assertTrue(should_use_secure_session_cookie(build_request(scheme="http")))

    def test_explicit_false_overrides_request_scheme(self):
        with patch.dict(os.environ, {"SESSION_COOKIE_SECURE": "false"}, clear=False):
            self.assertFalse(should_use_secure_session_cookie(build_request(scheme="https")))
