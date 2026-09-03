import json
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from app.services.todo_ai_service import todo_fingerprint
from app.services.todo_ai_work_service import (
    TodoAIWorkClient,
    normalize_work_turn,
    validate_work_context,
)


def context(**overrides):
    value = {
        "id": 9,
        "title": "Verdi subscription cancellation letter",
        "description": "Prepare a German cancellation letter that I will sign and send.",
        "due_date": None,
        "status": "not_started",
        "classification": "PARTIALLY_AI_ACTIONABLE",
        "reason": "AI can prepare the letter.",
        "ai_steps": ["Draft the letter"],
        "assessed_human_steps": ["Sign and send it"],
        "missing_information": ["Membership number"],
        "supported_actions": ["DRAFT_TEXT", "GENERATE_PDF"],
    }
    value["assessment_fingerprint"] = todo_fingerprint(value)
    value.update(overrides)
    return value


class TodoAIWorkServiceTests(unittest.TestCase):
    def test_stale_assessment_cannot_start_work(self):
        stale = context(assessment_fingerprint="0" * 64)

        with self.assertRaises(HTTPException) as raised:
            validate_work_context(stale)

        self.assertEqual(raised.exception.status_code, 409)

    def test_draft_ready_without_content_is_safely_downgraded(self):
        result = normalize_work_turn({
            "message": "Done", "phase": "DRAFT_READY", "questions": [],
            "deliverable_title": "Letter", "deliverable_content": None,
            "human_steps": [],
        })

        self.assertEqual(result["phase"], "GATHERING_INFORMATION")

    @patch("app.services.todo_ai_work_service.httpx.post")
    def test_work_request_preloads_task_assessment_and_disables_storage(self, post: Mock):
        turn = {
            "message": "What is your membership number?",
            "phase": "GATHERING_INFORMATION",
            "questions": ["What is your membership number?"],
            "deliverable_title": None,
            "deliverable_content": None,
            "human_steps": ["Sign and send the finished letter"],
        }
        post.return_value.is_error = False
        post.return_value.json.return_value = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(turn)}]}],
        }
        client = TodoAIWorkClient(api_key="test", model="test-model")

        result = client.reply(context(), [], "de")

        self.assertEqual(result["questions"], ["What is your membership number?"])
        request = post.call_args.kwargs["json"]
        payload = json.loads(request["input"])
        self.assertFalse(request["store"])
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertIn("exactly one answerable fact", request["instructions"])
        self.assertEqual(payload["task"]["title"], "Verdi subscription cancellation letter")
        self.assertEqual(payload["assessment"]["missing_information"], ["Membership number"])
        self.assertNotIn("user_id", request["input"])


if __name__ == "__main__":
    unittest.main()
