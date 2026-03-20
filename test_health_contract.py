import unittest
from unittest.mock import patch

from fastapi import HTTPException

from main1 import app, health_check, shutdown_app_state


def tearDownModule():
    shutdown_app_state()


class HealthContractTests(unittest.TestCase):
    def test_health_route_is_registered_once(self):
        health_routes = [
            route
            for route in app.router.routes
            if getattr(route, "path", None) == "/health" and "GET" in getattr(route, "methods", set())
        ]
        self.assertEqual(len(health_routes), 1)

    def test_health_returns_documented_contract(self):
        self.assertEqual(health_check(), {"status": "ok", "database": "ok"})

    def test_health_returns_503_when_database_is_unreachable(self):
        with patch("main1.engine.connect", side_effect=RuntimeError("db down")):
            with self.assertRaises(HTTPException) as exc_info:
                health_check()

        self.assertEqual(exc_info.exception.status_code, 503)
        self.assertEqual(exc_info.exception.detail["status"], "error")
        self.assertEqual(exc_info.exception.detail["database"], "unreachable")
