import unittest
from unittest.mock import MagicMock, patch

from app.repositories.bank_repository import mark_connection_synced


class BankRepositoryTests(unittest.TestCase):
    @patch("app.repositories.bank_repository.get_connection")
    def test_successful_sync_uses_unambiguous_postgres_parameters(self, get_connection):
        cursor = MagicMock()
        connection = MagicMock()
        get_connection.return_value.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        mark_connection_synced(user_id=7, connection_id=42)

        query, parameters = cursor.execute.call_args.args
        self.assertIn("last_synced_at = CURRENT_TIMESTAMP", query)
        self.assertNotIn("CASE", query)
        self.assertEqual(parameters, (42, 7))

    @patch("app.repositories.bank_repository.get_connection")
    def test_failed_sync_records_error_without_changing_last_success(self, get_connection):
        cursor = MagicMock()
        connection = MagicMock()
        get_connection.return_value.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor

        mark_connection_synced(user_id=7, connection_id=42, error="Provider unavailable")

        query, parameters = cursor.execute.call_args.args
        self.assertNotIn("last_synced_at", query)
        self.assertIn("status = 'ERROR'", query)
        self.assertEqual(parameters, ("Provider unavailable", 42, 7))


if __name__ == "__main__":
    unittest.main()
