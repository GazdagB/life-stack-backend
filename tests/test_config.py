import unittest

from app.config import Settings


class SettingsTests(unittest.TestCase):
    def test_optional_banking_misconfiguration_does_not_crash_application(self):
        settings = Settings()
        settings.ENVIRONMENT = "production"
        settings.SECRET_KEY = "a" * 32
        settings.SESSION_COOKIE_SECURE = True
        settings.ALLOWED_ORIGINS = ["https://lifeos.example.com"]
        settings.ALLOWED_HOSTS = ["lifeos.example.com"]
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


if __name__ == "__main__":
    unittest.main()
