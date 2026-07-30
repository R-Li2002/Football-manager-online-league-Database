import unittest

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from app_factory import configure_http_delivery


class HttpDeliveryTests(unittest.TestCase):
    def build_client(self) -> TestClient:
        app = FastAPI()
        configure_http_delivery(app)

        @app.get("/payload")
        def payload():
            return PlainTextResponse("x" * 5000)

        @app.get("/static/mock.js")
        def static_mock():
            return PlainTextResponse("console.log('ok');")

        return TestClient(app)

    def test_large_response_uses_gzip_when_requested(self):
        response = self.build_client().get("/payload", headers={"Accept-Encoding": "gzip"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("content-encoding"), "gzip")

    def test_versioned_static_asset_uses_immutable_cache(self):
        response = self.build_client().get("/static/mock.js?v=0.3.66")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("cache-control"), "public, max-age=31536000, immutable")

    def test_unversioned_static_asset_uses_short_cache(self):
        response = self.build_client().get("/static/mock.js")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("cache-control"), "public, max-age=3600")


if __name__ == "__main__":
    unittest.main()
