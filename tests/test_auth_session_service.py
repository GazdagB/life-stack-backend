import unittest
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.services.auth_service import (
    generate_refresh_token,
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


if __name__ == "__main__":
    unittest.main()
