import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

from fastapi import HTTPException

from app.services.movie_recommendation_service import (
    AIRecommendationClient,
    build_preference_payload,
    build_verified_recommendations,
    extract_structured_output,
)


def rated_movie(number: int):
    return {
        "title": f"Rated {number}",
        "year": "2020",
        "genre": "Drama",
        "director": "A Director",
        "personal_rating": Decimal("8.5"),
        "critique": "Thoughtful and precise.",
    }


class FakeAIClient:
    def generate_candidates(self, rated_movies, saved_movies, language="en", all_time_favorites=None):
        return [
            {"title": "Already Saved", "year": 2020, "reason": "First", "matched_preferences": ["Drama"]},
            {"title": "Fresh Film", "year": 2021, "reason": "A careful thematic match.", "matched_preferences": ["Drama", "Character-driven"]},
            {"title": "Backup", "year": 2022, "reason": "Backup", "matched_preferences": ["Drama"]},
            {"title": "Fourth", "year": 2023, "reason": "Fourth", "matched_preferences": ["Drama"]},
            {"title": "Fifth", "year": 2024, "reason": "Fifth", "matched_preferences": ["Drama"]},
            {"title": "Sixth", "year": 2025, "reason": "Sixth", "matched_preferences": ["Drama"]},
        ]


class FakeCatalog:
    def details_by_title(self, title, year=None):
        imdb_ids = {
            "Already Saved": "tt0000001",
            "Fresh Film": "tt0000002",
            "Backup": "tt0000003",
            "Fourth": "tt0000004",
            "Fifth": "tt0000005",
            "Sixth": "tt0000006",
        }
        imdb_id = imdb_ids[title]
        return {"imdb_id": imdb_id, "title": title, "external_ratings": []}


class MovieRecommendationServiceTests(unittest.TestCase):
    def test_payload_limits_profile_and_strips_identity(self):
        payload = build_preference_payload(
            [rated_movie(index) for index in range(12)],
            [{"title": "Saved", "year": "2024", "imdb_id": "tt1"}],
        )
        self.assertEqual(len(payload["recent_ratings_newest_first"]), 10)
        self.assertNotIn("user_id", payload)
        self.assertEqual(payload["recent_ratings_newest_first"][0]["personal_rating"], 8.5)
        self.assertEqual(payload["recent_ratings_newest_first"][0]["signal_weight"], 1.0)
        self.assertEqual(payload["recent_ratings_newest_first"][9]["signal_weight"], 0.55)

    def test_payload_keeps_lower_weight_all_time_anchors_separate(self):
        payload = build_preference_payload(
            [rated_movie(1), rated_movie(2), rated_movie(3)],
            [],
            [rated_movie(20), rated_movie(21)],
        )

        self.assertEqual(len(payload["all_time_favorites"]), 2)
        self.assertEqual(payload["all_time_favorites"][0]["signal_weight"], 0.35)

    def test_extracts_structured_responses_output(self):
        result = extract_structured_output({
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": '{"candidates": []}'}],
            }],
        })
        self.assertEqual(result, {"candidates": []})

    def test_requires_three_rated_movies_before_api_call(self):
        client = AIRecommendationClient(api_key="test", model="test")
        with self.assertRaises(HTTPException) as raised:
            client.generate_candidates([rated_movie(1), rated_movie(2)], [])
        self.assertEqual(raised.exception.status_code, 422)

    @patch("app.services.movie_recommendation_service.httpx.post")
    def test_openai_request_disables_storage_and_uses_structured_output(self, post: Mock):
        post.return_value.status_code = 200
        post.return_value.is_error = False
        post.return_value.json.return_value = {
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": '{"candidates": []}'}],
            }],
        }
        client = AIRecommendationClient(api_key="test", model="test-model")

        client.generate_candidates(
            [rated_movie(1), rated_movie(2), rated_movie(3)],
            [],
        )

        request = post.call_args.kwargs["json"]
        self.assertFalse(request["store"])
        self.assertEqual(request["model"], "test-model")
        self.assertEqual(request["text"]["format"]["type"], "json_schema")
        self.assertTrue(request["text"]["format"]["strict"])

    @patch("app.services.movie_recommendation_service.httpx.post")
    def test_requests_recommendation_copy_in_selected_language(self, post: Mock):
        post.return_value.status_code = 200
        post.return_value.is_error = False
        post.return_value.json.return_value = {
            "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"candidates": []}'}]}],
        }
        client = AIRecommendationClient(api_key="test", model="test-model")

        client.generate_candidates(
            [rated_movie(1), rated_movie(2), rated_movie(3)],
            [],
            "de",
        )

        instructions = post.call_args.kwargs["json"]["instructions"]
        self.assertIn("German", instructions)
        self.assertIn("canonical/original movie titles", instructions)

    @patch("app.services.movie_recommendation_service.httpx.post")
    def test_reports_billing_quota_separately_from_rate_limits(self, post: Mock):
        post.return_value.status_code = 429
        post.return_value.is_error = True
        post.return_value.json.return_value = {
            "error": {"type": "insufficient_quota", "code": "insufficient_quota"},
        }
        client = AIRecommendationClient(api_key="test", model="test-model")

        with self.assertRaises(HTTPException) as raised:
            client.generate_candidates(
                [rated_movie(1), rated_movie(2), rated_movie(3)],
                [],
            )

        self.assertEqual(raised.exception.status_code, 402)
        self.assertIn("credits", raised.exception.detail)

    def test_skips_existing_candidate_and_returns_four_verified_matches(self):
        result = build_verified_recommendations(
            [rated_movie(1), rated_movie(2), rated_movie(3)],
            [{"title": "Already Saved", "year": "2020", "imdb_id": "tt0000001"}],
            FakeAIClient(),
            FakeCatalog(),
        )
        recommendations = result["recommendations"]
        self.assertEqual(len(recommendations), 4)
        self.assertEqual(recommendations[0]["title"], "Fresh Film")
        self.assertEqual(recommendations[0]["recommendation_reason"], "A careful thematic match.")
        self.assertEqual(len(recommendations[0]["based_on"]), 3)


if __name__ == "__main__":
    unittest.main()
