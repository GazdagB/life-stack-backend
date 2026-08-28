import unittest

from app.services.movie_catalog_service import normalize_details, normalize_search


class MovieCatalogServiceTests(unittest.TestCase):
    def test_normalizes_every_available_rating_source(self):
        result = normalize_details({
            "Response": "True",
            "imdbID": "tt0133093",
            "Title": "The Matrix",
            "Year": "1999",
            "Poster": "N/A",
            "Plot": "A hacker discovers the truth.",
            "Director": "Lana Wachowski, Lilly Wachowski",
            "Actors": "Keanu Reeves",
            "Genre": "Action, Sci-Fi",
            "Runtime": "136 min",
            "Rated": "R",
            "Ratings": [
                {"Source": "Internet Movie Database", "Value": "8.7/10"},
                {"Source": "Rotten Tomatoes", "Value": "83%"},
                {"Source": "Metacritic", "Value": "73/100"},
            ],
        })

        self.assertIsNone(result["poster_url"])
        self.assertEqual(len(result["external_ratings"]), 3)
        self.assertEqual(result["external_ratings"][1]["source"], "Rotten Tomatoes")

    def test_empty_search_is_a_successful_empty_result(self):
        self.assertEqual(
            normalize_search({"Response": "False", "Error": "Movie not found!"}),
            {"results": [], "total_results": 0},
        )


if __name__ == "__main__":
    unittest.main()
