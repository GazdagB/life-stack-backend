import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi import Response
from fastapi.testclient import TestClient

from app.api.auth import _device_identity
from app.config import settings
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

    def test_disallowed_login_uses_same_error_as_invalid_credentials(self):
        private_user = {**CURRENT_USER, "password_hash": "stored-hash"}
        with (
            patch("app.api.auth.enforce_login_rate_limit", return_value=[]),
            patch("app.api.auth.get_user_by_username_private", return_value=private_user),
            patch("app.api.auth.verify_login_password", return_value=True),
            patch.object(settings, "is_email_allowed", return_value=False),
            patch("app.api.auth.create_refresh_session") as create_session,
        ):
            response = self.client.post(
                "/auth/login",
                data={"username": "owner", "password": "correct secure password"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Credentials incorrect"})
        create_session.assert_not_called()

    def test_allowed_account_can_login(self):
        private_user = {**CURRENT_USER, "password_hash": "stored-hash"}
        with (
            patch("app.api.auth.enforce_login_rate_limit", return_value=[]),
            patch("app.api.auth.get_user_by_username_private", return_value=private_user),
            patch("app.api.auth.verify_login_password", return_value=True),
            patch.object(settings, "is_email_allowed", return_value=True),
            patch("app.api.auth.create_refresh_session") as create_session,
        ):
            response = self.client.post(
                "/auth/login",
                data={"username": "owner", "password": "correct secure password"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], CURRENT_USER["email"])
        create_session.assert_called_once()

    def test_registration_rejects_an_email_outside_the_allowlist(self):
        with (
            patch.object(settings, "REGISTRATION_ENABLED", True),
            patch.object(settings, "is_email_allowed", return_value=False),
            patch("app.api.auth.create_user") as create_user,
        ):
            response = self.client.post(
                "/auth/register",
                json={
                    "username": "stranger",
                    "email": "stranger@example.com",
                    "plain_password": "correct horse battery staple",
                },
            )

        self.assertEqual(response.status_code, 404)
        create_user.assert_not_called()

    def test_profile_email_change_is_rejected_outside_allowlist(self):
        with (
            patch.object(settings, "is_email_allowed", return_value=False),
            patch("app.api.auth.update_user_profile") as update_profile,
        ):
            response = self.client.put(
                "/auth/profile",
                json={
                    "username": "owner",
                    "email": "stranger@example.com",
                    "display_name": None,
                    "bio": None,
                },
            )

        self.assertEqual(response.status_code, 403)
        update_profile.assert_not_called()

    def test_only_owner_receives_configured_allowlist(self):
        with (
            patch.object(settings, "ALLOWED_USER_EMAILS", ("owner@example.com", "member@example.com")),
            patch.object(settings, "is_owner_email", return_value=True),
        ):
            owner_response = self.client.get("/auth/access-policy")

        self.assertEqual(owner_response.status_code, 200)
        self.assertTrue(owner_response.json()["is_owner"])
        self.assertEqual(owner_response.json()["allowed_emails"], ["owner@example.com", "member@example.com"])

        with (
            patch.object(settings, "ALLOWED_USER_EMAILS", ("owner@example.com", "member@example.com")),
            patch.object(settings, "is_owner_email", return_value=False),
        ):
            member_response = self.client.get("/auth/access-policy")

        self.assertEqual(member_response.status_code, 200)
        self.assertFalse(member_response.json()["is_owner"])
        self.assertEqual(member_response.json()["allowed_emails"], [])

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
