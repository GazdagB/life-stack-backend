import unittest
from unittest.mock import MagicMock, patch

from app.repositories.todo_ai_work_repository import append_work_message


class TodoAIWorkRepositoryTests(unittest.TestCase):
    @patch("app.repositories.todo_ai_work_repository.get_connection")
    def test_append_checks_owned_session_then_inserts_message(self, get_connection):
        connection = MagicMock()
        cursor = MagicMock()
        get_connection.return_value.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value = cursor
        session_query = MagicMock()
        insert_query = MagicMock()
        session_query.fetchone.return_value = {"exists": 1}
        inserted = {"id": 88, "role": "USER", "content": "My answer"}
        insert_query.fetchone.return_value = inserted
        cursor.execute.side_effect = [session_query, insert_query]

        result = append_work_message(42, 11, "USER", "My answer")

        self.assertEqual(result, inserted)
        self.assertEqual(cursor.execute.call_count, 2)
        insert_sql, insert_params = cursor.execute.call_args_list[1].args
        self.assertIn("INSERT INTO todo_ai_work_messages", insert_sql)
        self.assertEqual(insert_params, (11, 42, "USER", "My answer"))


if __name__ == "__main__":
    unittest.main()
