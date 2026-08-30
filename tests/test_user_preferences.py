import unittest

from pydantic import ValidationError

from app.api.auth import PreferencesUpdate


class UserPreferencesTests(unittest.TestCase):
    def test_supported_language_is_accepted(self):
        preferences = PreferencesUpdate(preferred_language="de")

        self.assertEqual(preferences.preferred_language, "de")

    def test_unsupported_language_is_rejected(self):
        with self.assertRaises(ValidationError):
            PreferencesUpdate(preferred_language="fr")


if __name__ == "__main__":
    unittest.main()
