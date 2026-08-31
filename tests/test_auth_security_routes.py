import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi import Response
from fastapi.testclient import TestClient

from app.api.auth import _device_identity
from app.main import app
from app.services.auth_service import get_current_user


CURRENT_USER = {
    "id": 7,
    "username": "owner",
    "email": "owner@example.com",
    "display_name": None,
    "bio": None,
    "has_avatar": False,
    "preferred_language": "en",
}


class AuthSecurityRouteTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_device_identity_reuses_an_opaque_httponly_cookie(self):
        response = Response()

        token, device_hash = _device_identity(response, "stable-browser-token")

        self.assertEqual(token, "stable-browser-token")
        self.assertEqual(len(device_hash), 64)
        cookie = response.headers["set-cookie"]
        self.assertIn("device_id=stable-browser-token", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=strict", cookie)
        self.assertIn("Path=/", cookie)

    @patch("app.api.auth.list_active_refresh_sessions")
    def test_sessions_are_scoped_to_authenticated_user(self, list_sessions):
        family_id = uuid4()
        now = datetime.now(timezone.utc)
        list_sessions.return_value = [{
            "family_id": family_id,
            "expires_at": now + timedelta(days=30),
            "last_used_at": now,
            "created_at": now,
            "user_agent": "Test browser",
            "is_current": True,
            "is_recognized_device": True,
        }]

        response = self.client.get(
            "/auth/sessions",
            cookies={"refresh_session": "current-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["family_id"], str(family_id))
        self.assertTrue(response.json()[0]["is_current"])
        self.assertEqual(list_sessions.call_args.args[0], CURRENT_USER["id"])

    @patch("app.api.auth.revoke_refresh_session_family")
    @patch("app.api.auth.list_active_refresh_sessions", return_value=[])
    def test_user_cannot_revoke_a_session_not_in_their_list(self, _, revoke_family):
        response = self.client.delete(f"/auth/sessions/{uuid4()}")

        self.assertEqual(response.status_code, 404)
        revoke_family.assert_not_called()

    @patch("app.api.auth.revoke_other_refresh_sessions", return_value=2)
    def test_revoke_others_preserves_current_family(self, revoke_others):
        response = self.client.post(
            "/auth/sessions/revoke-others",
            cookies={"refresh_session": "current-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["revoked_count"], 2)
        self.assertEqual(revoke_others.call_args.args[0], CURRENT_USER["id"])

    @patch("app.api.auth.revoke_other_refresh_sessions", return_value=3)
    @patch("app.api.auth.clear_successful_login_limits")
    @patch("app.api.auth.enforce_login_rate_limit", return_value=[("login_account", "key")])
    @patch("app.api.auth.update_user_password_hash")
    @patch("app.api.auth.get_password_hash", return_value="new-hash")
    @patch("app.api.auth.verify_login_password", side_effect=[True, False])
    @patch("app.api.auth.get_user_password_hash_by_id", return_value="old-hash")
    def test_password_change_reauthenticates_and_revokes_other_sessions(
        self,
        get_hash,
        verify_password,
        hash_password,
        update_hash,
        enforce_limit,
        clear_limits,
        revoke_others,
    ):
        response = self.client.post(
            "/auth/change-password",
            cookies={"refresh_session": "current-token"},
            json={
                "current_password": "correct current password",
                "new_password": "a different secure password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["revoked_sessions"], 3)
        get_hash.assert_called_once_with(CURRENT_USER["id"])
        self.assertEqual(verify_password.call_count, 2)
        hash_password.assert_called_once_with("a different secure password")
        update_hash.assert_called_once_with(CURRENT_USER["id"], "new-hash")
        self.assertEqual(revoke_others.call_args.args[0], CURRENT_USER["id"])
        enforce_limit.assert_called_once()
        clear_limits.assert_called_once_with([("login_account", "key")])

    @patch("app.api.auth.enforce_login_rate_limit", return_value=[("login_account", "key")])
    @patch("app.api.auth.get_user_password_hash_by_id", return_value="old-hash")
    @patch("app.api.auth.verify_login_password", return_value=False)
    def test_password_change_rejects_incorrect_current_password(self, _, __, ___):
        response = self.client.post(
            "/auth/change-password",
            json={
                "current_password": "wrong password",
                "new_password": "a different secure password",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Current password is incorrect")


if __name__ == "__main__":
    unittest.main()
