import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from app.services.movie_critique_service import MovieCritiqueClient


class MovieCritiqueServiceTests(unittest.TestCase):
    @patch("app.services.movie_critique_service.httpx.post")
    def test_rewrite_preserves_privacy_and_uses_structured_output(self, post: Mock):
        post.return_value.is_error = False
        post.return_value.json.return_value = {
            "output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": '{"rewritten_critique":"A sharper, clearer review."}',
                }],
            }],
        }
        client = MovieCritiqueClient(api_key="test-key", model="test-model")

        result = client.rewrite("good but too long", "Example Movie")

        self.assertEqual(result, "A sharper, clearer review.")
        request = post.call_args.kwargs["json"]
        self.assertFalse(request["store"])
        self.assertEqual(request["model"], "test-model")
        self.assertEqual(request["text"]["format"]["type"], "json_schema")
        self.assertNotIn("user", request)

    @patch("app.services.movie_critique_service.httpx.post")
    def test_rephrase_includes_previous_suggestion_to_avoid(self, post: Mock):
        post.return_value.is_error = False
        post.return_value.json.return_value = {
            "output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": '{"rewritten_critique":"A different version."}',
                }],
            }],
        }
        client = MovieCritiqueClient(api_key="test-key", model="test-model")

        client.rewrite("My original", previous_suggestion="First version")

        payload = post.call_args.kwargs["json"]["input"]
        self.assertIn("First version", payload)

    def test_requires_api_configuration(self):
        client = MovieCritiqueClient(api_key="", model="test-model")
        client.api_key = None

        with self.assertRaises(HTTPException) as raised:
            client.rewrite("A valid critique")

        self.assertEqual(raised.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
