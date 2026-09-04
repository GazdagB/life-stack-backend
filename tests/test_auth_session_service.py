import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.config import settings
from app.services.auth_service import (
    _allowed_user,
    _authenticated_session_user_id,
    create_access_token,
    decode_access_token,
    generate_device_token,
    generate_refresh_token,
    hash_device_token,
    hash_refresh_token,
    refresh_token_expires_at,
)


class AuthSessionServiceTests(unittest.TestCase):
    def test_refresh_tokens_are_random_and_only_hashes_are_persistable(self):
        first = generate_refresh_token()
        second = generate_refresh_token()

        self.assertNotEqual(first, second)
        self.assertGreaterEqual(len(first), 64)
        self.assertEqual(len(hash_refresh_token(first)), 64)
        self.assertNotEqual(hash_refresh_token(first), first)
        self.assertEqual(hash_refresh_token(first), hash_refresh_token(first))

    def test_device_tokens_are_random_and_only_hashes_are_persisted(self):
        first = generate_device_token()
        second = generate_device_token()

        self.assertNotEqual(first, second)
        self.assertGreaterEqual(len(first), 40)
        self.assertEqual(len(hash_device_token(first)), 64)
        self.assertNotEqual(hash_device_token(first), first)

    def test_refresh_expiry_uses_configured_absolute_lifetime(self):
        before = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRES_DAYS,
        )
        expires_at = refresh_token_expires_at()
        after = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRES_DAYS,
        )

        self.assertGreaterEqual(expires_at, before)
        self.assertLessEqual(expires_at, after)

    def test_access_tokens_require_expected_issuer_and_audience(self):
        session_id = uuid4()
        payload = decode_access_token(
            create_access_token({"sub": "42", "sid": str(session_id)})
        )

        self.assertEqual(payload["sub"], "42")
        self.assertEqual(payload["iss"], settings.JWT_ISSUER)
        self.assertEqual(payload["aud"], settings.JWT_AUDIENCE)
        self.assertEqual(payload["sid"], str(session_id))

    @patch("app.services.auth_service.is_refresh_session_family_active", return_value=True)
    def test_authenticated_session_is_bound_to_active_refresh_family(self, is_active):
        session_id = uuid4()

        user_id = _authenticated_session_user_id({"sub": "42", "sid": str(session_id)})

        self.assertEqual(user_id, 42)
        self.assertEqual(is_active.call_args.args[0:2], (42, session_id))

    @patch("app.services.auth_service.is_refresh_session_family_active", return_value=False)
    def test_revoked_refresh_family_invalidates_access_token_immediately(self, _):
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as raised:
            _authenticated_session_user_id({"sub": "42", "sid": str(uuid4())})

        self.assertEqual(raised.exception.status_code, 401)

    @patch("app.services.auth_service.settings.is_email_allowed", return_value=False)
    @patch("app.services.auth_service.get_user_by_id_public", return_value={"id": 42, "email": "removed@example.com"})
    def test_removed_allowlist_member_loses_existing_access_immediately(self, _, __):
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as raised:
            _allowed_user(42)

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.detail, "Could not validate credentials")


if __name__ == "__main__":
    unittest.main()
