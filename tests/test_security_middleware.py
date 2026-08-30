import unittest

from fastapi.testclient import TestClient

from app.main import app


class SecurityMiddlewareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_api_responses_include_security_headers(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["referrer-policy"], "strict-origin-when-cross-origin")

    def test_cross_site_state_change_is_blocked_before_route_execution(self):
        response = self.client.post(
            "/auth/login",
            headers={"Origin": "https://attacker.example"},
            data={"username": "someone", "password": "password"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "Cross-site request blocked"})

    def test_public_registration_is_disabled_by_default(self):
        response = self.client.post(
            "/auth/register",
            json={
                "username": "new-user",
                "email": "new-user@example.com",
                "plain_password": "correct horse battery staple",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_todos_require_authentication(self):
        response = self.client.get("/todos/")

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
