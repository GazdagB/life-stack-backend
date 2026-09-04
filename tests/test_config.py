import unittest
from unittest.mock import patch

from app.config import Settings, _email_allowlist_setting


class SettingsTests(unittest.TestCase):
    def test_optional_banking_misconfiguration_does_not_crash_application(self):
        settings = Settings()
        settings.ENVIRONMENT = "production"
        settings.SECRET_KEY = "a" * 32
        settings.SESSION_COOKIE_SECURE = True
        settings.ALLOWED_ORIGINS = ["https://lifeos.example.com"]
        settings.ALLOWED_HOSTS = ["lifeos.example.com"]
        settings.ALLOWED_USER_EMAILS = ("owner@example.com",)
        settings.ENABLE_BANKING_APP_ID = "bank-app-id"
        settings.ENABLE_BANKING_PRIVATE_KEY = "private-key"
        settings.ENABLE_BANKING_PRIVATE_KEY_PATH = None
        settings.BANK_DATA_ENCRYPTION_KEY = None
        settings.ENABLE_BANKING_REDIRECT_URL = "http://localhost/callback"

        settings.validate()

        self.assertEqual(
            settings.banking_configuration_error(),
            "BANK_DATA_ENCRYPTION_KEY is not configured",
        )

    def test_production_fails_closed_without_private_email_allowlist(self):
        settings = Settings()
        settings.ENVIRONMENT = "production"
        settings.SECRET_KEY = "a" * 32
        settings.SESSION_COOKIE_SECURE = True
        settings.ALLOWED_ORIGINS = ["https://lifeos.example.com"]
        settings.ALLOWED_HOSTS = ["lifeos.example.com"]
        settings.ALLOWED_USER_EMAILS = ()

        with self.assertRaisesRegex(RuntimeError, "ALLOWED_USER_EMAILS"):
            settings.validate()

    def test_allowlist_is_case_insensitive_and_first_address_is_owner(self):
        settings = Settings()
        settings.ENVIRONMENT = "production"
        settings.ALLOWED_USER_EMAILS = ("owner@example.com", "member@example.com")

        self.assertTrue(settings.is_email_allowed(" OWNER@EXAMPLE.COM "))
        self.assertTrue(settings.is_owner_email("Owner@example.com"))
        self.assertFalse(settings.is_owner_email("member@example.com"))
        self.assertFalse(settings.is_email_allowed("stranger@example.com"))

    def test_allowlist_rejects_duplicate_and_malformed_addresses(self):
        with patch.dict("os.environ", {"ALLOWED_USER_EMAILS": "owner@example.com,OWNER@example.com"}):
            with self.assertRaisesRegex(RuntimeError, "duplicate"):
                _email_allowlist_setting("ALLOWED_USER_EMAILS")
        with patch.dict("os.environ", {"ALLOWED_USER_EMAILS": "not-an-email"}):
            with self.assertRaisesRegex(RuntimeError, "invalid address"):
                _email_allowlist_setting("ALLOWED_USER_EMAILS")


if __name__ == "__main__":
    unittest.main()
