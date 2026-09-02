import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import get_current_user_id


CONTEXT = {
    "id": 3, "title": "Draft a letter", "description": "", "due_date": None,
    "status": "not_started", "assessment_fingerprint": "a" * 64,
    "classification": "PARTIALLY_AI_ACTIONABLE", "reason": "AI can draft it",
    "ai_steps": ["Draft it"], "assessed_human_steps": ["Send it"],
    "missing_information": [], "supported_actions": ["DRAFT_TEXT"],
}
SESSION = {
    "id": 11, "user_id": 42, "todo_id": 3, "content_fingerprint": "a" * 64,
    "phase": "GATHERING_INFORMATION", "questions": [], "human_steps": [],
    "deliverable_title": None, "deliverable_content": None, "model_name": "test",
}


class TodoAIWorkRouteTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_current_user_id] = lambda: 42
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("app.api.todos.list_work_messages", return_value=[])
    @patch("app.api.todos.apply_assistant_turn", return_value=SESSION)
    @patch("app.api.todos.get_or_create_work_session", return_value=SESSION)
    @patch("app.api.todos.validate_work_context")
    @patch("app.api.todos.get_todo_work_context", return_value=CONTEXT)
    @patch("app.api.todos.todo_ai_work_client")
    def test_start_preloads_owned_context_and_creates_first_ai_turn(
        self, client, get_context, validate, get_session, apply_turn, _messages,
    ):
        client.model = "test-model"
        client.reply.return_value = {
            "message": "I need one detail.", "phase": "GATHERING_INFORMATION",
            "questions": ["Which address?"], "human_steps": [],
            "deliverable_title": None, "deliverable_content": None,
        }

        response = self.client.post("/todos/3/ai-session", json={"language": "de"})

        self.assertEqual(response.status_code, 200)
        get_context.assert_called_once_with(42, 3)
        validate.assert_called_once_with(CONTEXT)
        get_session.assert_called_once_with(42, 3, "a" * 64)
        client.reply.assert_called_once_with(CONTEXT, [], "de")
        apply_turn.assert_called_once()

    @patch("app.api.todos.list_work_messages", return_value=[])
    @patch("app.api.todos.update_work_draft", return_value={**SESSION, "phase": "DRAFT_READY"})
    @patch("app.api.todos.get_work_session", return_value=SESSION)
    @patch("app.api.todos.get_todo_work_context", return_value=CONTEXT)
    def test_edited_draft_is_saved_in_user_scoped_session(
        self, get_context, get_session, update_draft, _messages,
    ):
        response = self.client.put(
            "/todos/3/ai-session/draft",
            json={"title": " Kündigung ", "content": " Letter body "},
        )

        self.assertEqual(response.status_code, 200)
        get_context.assert_called_once_with(42, 3)
        get_session.assert_called_once_with(42, 3)
        update_draft.assert_called_once_with(42, 11, "Kündigung", "Letter body")

    @patch("app.api.todos.delete_work_message")
    @patch("app.api.todos.list_work_messages", return_value=[{"role": "USER", "content": "Answer"}])
    @patch("app.api.todos.append_work_message", return_value={"id": 88})
    @patch("app.api.todos.get_work_session", return_value=SESSION)
    @patch("app.api.todos.validate_work_context")
    @patch("app.api.todos.get_todo_work_context", return_value=CONTEXT)
    @patch("app.api.todos.todo_ai_work_client")
    def test_failed_provider_turn_removes_unprocessed_user_message(
        self, client, _get_context, _validate, _get_session, _append, _messages, delete_message,
    ):
        client.reply.side_effect = HTTPException(status_code=502, detail="Unavailable")

        response = self.client.post(
            "/todos/3/ai-session/messages",
            json={"content": "Answer", "language": "en"},
        )

        self.assertEqual(response.status_code, 502)
        delete_message.assert_called_once_with(42, 88)


if __name__ == "__main__":
    unittest.main()
