import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


class HealthRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_liveness_does_not_query_the_database(self):
        with patch("app.api.health.get_connection") as get_connection:
            response = self.client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        get_connection.assert_not_called()

    @patch("app.api.health.get_connection")
    def test_readiness_returns_503_without_leaking_database_details(self, get_connection):
        get_connection.side_effect = RuntimeError("sensitive connection failure")

        response = self.client.get("/readyz")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn("sensitive", response.text)

    @patch("app.api.health.get_connection")
    def test_readiness_checks_the_database(self, get_connection):
        connection = MagicMock()
        cursor = MagicMock()
        get_connection.return_value.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        response = self.client.get("/readyz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready"})
        cursor.execute.assert_called_once_with("SELECT 1")


if __name__ == "__main__":
    unittest.main()
