import unittest
from datetime import date
from decimal import Decimal

from app.services.movie_insights_service import (
    build_movie_insights,
    normalize_categories,
    parse_release_year,
    parse_runtime_minutes,
)


def watched_movie(identifier: int, title: str, **overrides):
    movie = {
        "id": identifier,
        "imdb_id": f"tt{identifier:07d}",
        "title": title,
        "list_status": "WATCHED",
        "year": None,
        "poster_url": None,
        "genre": None,
        "runtime": None,
        "personal_rating": None,
        "watched_at": None,
    }
    movie.update(overrides)
    return movie


class MovieInsightsServiceTests(unittest.TestCase):
    def test_normalizes_categories_and_removes_missing_values(self):
        self.assertEqual(
            normalize_categories(" Drama, Sci-Fi, drama, N/A, Science Fiction "),
            ["Drama", "Sci-Fi"],
        )

    def test_parses_runtime_and_first_release_year(self):
        self.assertEqual(parse_runtime_minutes("136 min"), 136)
        self.assertIsNone(parse_runtime_minutes("N/A"))
        self.assertEqual(parse_release_year("2019–2022"), 2019)
        self.assertIsNone(parse_release_year("Unknown"))

    def test_builds_categories_and_all_requested_superlatives(self):
        movies = [
            watched_movie(
                1, "Older Favourite", year="1972", genre="Drama, Crime",
                runtime="175 min", personal_rating=Decimal("9.5"),
                watched_at=date(2026, 1, 2),
            ),
            watched_movie(
                2, "Recent Favourite", year="2025", genre="Drama, Sci-Fi",
                runtime="120 min", personal_rating=Decimal("9.5"),
                watched_at=date(2026, 8, 20),
            ),
            {**watched_movie(3, "Queue Item"), "list_status": "WANT_TO_WATCH"},
        ]

        result = build_movie_insights(movies)

        self.assertEqual(result["total_watched"], 2)
        self.assertEqual(result["categories"][0], {"name": "Drama", "count": 2})
        self.assertEqual(result["superlatives"]["longest"]["value"], 175)
        self.assertEqual(
            [movie["title"] for movie in result["superlatives"]["highest_rated"]["movies"]],
            ["Older Favourite", "Recent Favourite"],
        )
        self.assertEqual(result["superlatives"]["oldest_release"]["value"], 1972)
        self.assertEqual(result["superlatives"]["newest_release"]["value"], 2025)
        self.assertEqual(result["superlatives"]["recently_watched"]["value"], "2026-08-20")

    def test_returns_null_superlatives_when_metadata_is_missing(self):
        result = build_movie_insights([watched_movie(1, "Unknown")])

        self.assertEqual(result["total_watched"], 1)
        self.assertEqual(result["categories"], [])
        self.assertTrue(all(value is None for value in result["superlatives"].values()))


if __name__ == "__main__":
    unittest.main()
