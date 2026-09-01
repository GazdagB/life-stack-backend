import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import get_current_user_id


def movie(identifier: int, genre: str):
    return {
        "id": identifier,
        "user_id": 42,
        "imdb_id": f"tt{identifier:07d}",
        "title": f"Movie {identifier}",
        "year": "2024",
        "poster_url": None,
        "genre": genre,
        "runtime": "100 min",
        "list_status": "WATCHED",
        "personal_rating": 8,
        "watched_at": "2026-08-20",
    }


class MovieInsightsRouteTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_current_user_id] = lambda: 42
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    @patch("app.api.movies.list_user_movies")
    def test_insights_are_scoped_to_authenticated_user(self, list_user_movies):
        list_user_movies.return_value = [movie(1, "Drama")]

        response = self.client.get("/movies/insights")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_watched"], 1)
        list_user_movies.assert_called_once_with(42, "WATCHED")

    @patch("app.api.movies.list_user_movies")
    def test_category_filter_is_case_insensitive(self, list_user_movies):
        list_user_movies.return_value = [movie(1, "Drama, Crime"), movie(2, "Comedy")]

        response = self.client.get("/movies/?list_status=WATCHED&category=drama")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [1])
        self.assertEqual(response.json()[0]["categories"], ["Crime", "Drama"])
        list_user_movies.assert_called_once_with(42, "WATCHED")


if __name__ == "__main__":
    unittest.main()
