import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import get_current_user_id


class TodoAIRouteTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_current_user_id] = lambda: 42
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("app.api.todos.list_todo_assessments")
    def test_list_is_scoped_to_authenticated_user(self, list_assessments):
        list_assessments.return_value = []

        response = self.client.get("/todos/ai-assessments")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"assessments": []})
        list_assessments.assert_called_once_with(42)

    @patch("app.api.todos.list_todo_assessments")
    @patch("app.api.todos.upsert_todo_assessments")
    @patch("app.api.todos.assess_todos")
    @patch("app.api.todos.get_todos_for_assessment")
    def test_assess_uses_selected_owned_todos_and_language(
        self,
        get_todos,
        assess,
        upsert,
        list_assessments,
    ):
        selected = [{
            "id": 3,
            "title": "Draft a note",
            "description": "",
            "due_date": None,
            "status": "not_started",
        }]
        generated = [{"todo_id": 3, "content_fingerprint": "a" * 64}]
        get_todos.return_value = selected
        assess.return_value = (generated, "ai", None)
        list_assessments.return_value = []

        response = self.client.post("/todos/ai-assess", json={"todo_ids": [3], "language": "hu"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["provider_status"], "ai")
        get_todos.assert_called_once_with(42, [3])
        assess.assert_called_once_with(selected, "hu")
        upsert.assert_called_once_with(42, generated)
        list_assessments.assert_called_once_with(42, [3])

    @patch("app.api.todos.get_todos_for_assessment", return_value=[])
    def test_unknown_selected_todo_is_not_silently_ignored(self, _get_todos):
        response = self.client.post("/todos/ai-assess", json={"todo_ids": [999], "language": "en"})

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
