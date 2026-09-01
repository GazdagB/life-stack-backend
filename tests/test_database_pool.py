import unittest
from unittest.mock import patch

from app.database import db


class DatabasePoolTests(unittest.TestCase):
    @patch.object(db, "connection_pool")
    def test_get_connection_opens_and_borrows_from_pool(self, connection_pool):
        connection_context = object()
        connection_pool.closed = True
        connection_pool.connection.return_value = connection_context

        result = db.get_connection()

        self.assertIs(result, connection_context)
        connection_pool.open.assert_called_once_with(wait=False)
        connection_pool.connection.assert_called_once_with(
            timeout=db.settings.DB_POOL_TIMEOUT_SECONDS
        )

    @patch.object(db, "connection_pool")
    def test_open_pool_is_idempotent(self, connection_pool):
        connection_pool.closed = False

        db.open_connection_pool()

        connection_pool.open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
