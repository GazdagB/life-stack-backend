import unittest
from unittest.mock import patch

from fastapi import HTTPException
from passlib.context import CryptContext

from app.services.auth_service import (
    get_password_hash,
    password_hash_needs_upgrade,
    verify_login_password,
)
from app.services.login_security_service import (
    enforce_login_rate_limit,
    login_rate_limit_keys,
)


class LoginSecurityServiceTests(unittest.TestCase):
    def test_rate_limit_keys_are_normalized_and_do_not_expose_identity(self):
        first = login_rate_limit_keys("203.0.113.10", " Balazs ")
        second = login_rate_limit_keys("203.0.113.10", "balazs")

        self.assertEqual(first, second)
        self.assertEqual({scope for scope, _ in first}, {"login_ip", "login_account"})
        self.assertTrue(all(len(key_hash) == 64 for _, key_hash in first))
        self.assertNotIn("balazs", "".join(key_hash for _, key_hash in first))

    @patch("app.services.login_security_service.consume_auth_rate_limits", return_value=42)
    def test_rejected_login_has_retry_after_header(self, consume):
        with self.assertRaises(HTTPException) as raised:
            enforce_login_rate_limit("203.0.113.10", "balazs")

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.headers, {"Retry-After": "42"})
        self.assertEqual(consume.call_args.args[1], 900)

    def test_password_verification_uses_dummy_hash_for_unknown_users(self):
        password_hash = get_password_hash("correct horse battery staple")

        self.assertTrue(password_hash.startswith("$argon2"))
        self.assertTrue(verify_login_password("correct horse battery staple", password_hash))
        self.assertFalse(verify_login_password("incorrect", password_hash))
        self.assertFalse(verify_login_password("incorrect", None))
        self.assertFalse(verify_login_password("x" * 73, password_hash))

    def test_legacy_bcrypt_hashes_remain_valid_for_login_upgrade(self):
        legacy_hash = CryptContext(schemes=["bcrypt"]).hash("correct horse battery staple")

        self.assertTrue(verify_login_password("correct horse battery staple", legacy_hash))
        self.assertTrue(password_hash_needs_upgrade(legacy_hash))


if __name__ == "__main__":
    unittest.main()
