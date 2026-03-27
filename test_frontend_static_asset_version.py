import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.frontend_routes import STATIC_ASSET_VERSION, build_frontend_router
from test_internal_share_page import _dummy_db


class FrontendStaticAssetVersionTests(unittest.TestCase):
    def test_root_page_appends_version_to_static_assets(self):
        app = FastAPI()
        app.include_router(build_frontend_router(_dummy_db))
        client = TestClient(app)

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(f'/static/app.css?v={STATIC_ASSET_VERSION}', response.text)
        self.assertIn(f'/static/js/app.core.js?v={STATIC_ASSET_VERSION}', response.text)
        self.assertIn(f'/static/app.js?v={STATIC_ASSET_VERSION}', response.text)
        self.assertNotIn("__STATIC_ASSET_VERSION__", response.text)
