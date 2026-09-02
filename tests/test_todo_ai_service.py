import unittest
from unittest.mock import Mock, patch

from app.services.todo_ai_service import (
    TodoAIClient,
    assess_todos,
    enforce_safety,
    rules_assessment,
    todo_fingerprint,
)


def todo(**overrides):
    value = {
        "id": 7,
        "title": "Write a project summary",
        "description": "Summarize the decisions for the team.",
        "due_date": None,
        "status": "not_started",
    }
    value.update(overrides)
    return value


class TodoAIServiceTests(unittest.TestCase):
    def test_fingerprint_changes_when_user_visible_content_changes(self):
        original = todo_fingerprint(todo())
        changed = todo_fingerprint(todo(description="A different description"))

        self.assertNotEqual(original, changed)

    def test_cancellation_letter_is_only_partially_actionable(self):
        result = rules_assessment(todo(
            title="Verdi subscription cancellation letter",
            description="Create a Kündigung PDF that I will sign and send.",
        ))

        self.assertEqual(result["classification"], "PARTIALLY_AI_ACTIONABLE")
        self.assertIn("DRAFT_TEXT", result["supported_actions"])
        self.assertIn("GENERATE_PDF", result["supported_actions"])
        self.assertTrue(result["human_steps"])

    def test_policy_downgrades_full_ai_claim_when_human_boundary_exists(self):
        result = enforce_safety(
            todo(title="Cancel gym membership", description="Draft and send the cancellation"),
            {
                "classification": "FULLY_AI_ACTIONABLE",
                "confidence": 99,
                "reason": "I can do everything.",
                "ai_steps": ["Draft it"],
                "human_steps": [],
                "missing_information": [],
                "supported_actions": ["DRAFT_TEXT"],
            },
            "test-model",
        )

        self.assertEqual(result["classification"], "PARTIALLY_AI_ACTIONABLE")

    def test_missing_key_uses_local_rules_instead_of_crashing(self):
        assessments, status, warning = assess_todos(
            [todo()],
            "en",
            TodoAIClient(api_key="", model="test-model"),
        )

        self.assertEqual(status, "fallback")
        self.assertEqual(len(assessments), 1)
        self.assertEqual(assessments[0]["assessment_source"], "RULES")
        self.assertIn("not configured", warning)

    @patch("app.services.todo_ai_service.httpx.post")
    def test_openai_request_is_minimal_structured_and_not_stored(self, post: Mock):
        post.return_value.is_error = False
        post.return_value.json.return_value = {
            "output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": '{"assessments": [{"todo_id": 7, "classification": "FULLY_AI_ACTIONABLE", "confidence": 90, "reason": "Digital writing task.", "ai_steps": ["Draft it"], "human_steps": ["Review it"], "missing_information": [], "supported_actions": ["DRAFT_TEXT"]}]}',
                }],
            }],
        }
        client = TodoAIClient(api_key="test", model="test-model")

        result = client.assess([todo()], "de")

        self.assertEqual(len(result), 1)
        request = post.call_args.kwargs["json"]
        self.assertFalse(request["store"])
        self.assertEqual(request["text"]["format"]["type"], "json_schema")
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertIn("German", request["instructions"])
        self.assertNotIn("user_id", request["input"])


if __name__ == "__main__":
    unittest.main()
