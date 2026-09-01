import re
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from typing import Callable


_MISSING_VALUES = {"", "n/a", "na", "none", "unknown", "-"}
_CATEGORY_ALIASES = {
    "science fiction": "Sci-Fi",
    "sci fi": "Sci-Fi",
}


def normalize_categories(genre: str | None) -> list[str]:
    if not genre:
        return []

    categories: dict[str, str] = {}
    for raw_category in genre.split(","):
        category = raw_category.strip()
        normalized = category.casefold()
        if normalized in _MISSING_VALUES:
            continue
        display_name = _CATEGORY_ALIASES.get(normalized, category)
        categories.setdefault(display_name.casefold(), display_name)
    return sorted(categories.values(), key=str.casefold)


def parse_runtime_minutes(runtime: str | None) -> int | None:
    if not runtime:
        return None
    match = re.search(r"(\d+)\s*min\b", runtime, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def parse_release_year(year: str | None) -> int | None:
    if not year:
        return None
    match = re.search(r"\b(?:18|19|20|21)\d{2}\b", year)
    return int(match.group(0)) if match else None


def parse_watched_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def enrich_movie(movie: dict) -> dict:
    return {**movie, "categories": normalize_categories(movie.get("genre"))}


def enrich_movies(movies: list[dict]) -> list[dict]:
    return [enrich_movie(movie) for movie in movies]


def _movie_summary(movie: dict) -> dict:
    return {
        "id": movie["id"],
        "imdb_id": movie["imdb_id"],
        "title": movie["title"],
        "year": movie.get("year"),
        "poster_url": movie.get("poster_url"),
        "runtime": movie.get("runtime"),
        "personal_rating": movie.get("personal_rating"),
        "watched_at": movie.get("watched_at"),
        "categories": movie.get("categories", []),
    }


def _superlative(
    movies: list[dict],
    value_getter: Callable[[dict], object | None],
    select_value: Callable[[list], object],
    serialize_value: Callable[[object], object] = lambda value: value,
) -> dict | None:
    candidates = [(movie, value_getter(movie)) for movie in movies]
    candidates = [(movie, value) for movie, value in candidates if value is not None]
    if not candidates:
        return None

    winning_value = select_value([value for _, value in candidates])
    winners = [
        _movie_summary(movie)
        for movie, value in candidates
        if value == winning_value
    ]
    winners.sort(key=lambda movie: (movie["title"].casefold(), movie["id"]))
    return {"value": serialize_value(winning_value), "movies": winners}


def build_movie_insights(movies: list[dict]) -> dict:
    watched_movies = enrich_movies([
        movie for movie in movies if movie.get("list_status") == "WATCHED"
    ])
    category_counts = Counter(
        category
        for movie in watched_movies
        for category in movie["categories"]
    )

    return {
        "total_watched": len(watched_movies),
        "categories": [
            {"name": name, "count": count}
            for name, count in sorted(
                category_counts.items(),
                key=lambda item: (-item[1], item[0].casefold()),
            )
        ],
        "superlatives": {
            "longest": _superlative(
                watched_movies,
                lambda movie: parse_runtime_minutes(movie.get("runtime")),
                max,
            ),
            "highest_rated": _superlative(
                watched_movies,
                lambda movie: Decimal(str(movie["personal_rating"]))
                if movie.get("personal_rating") is not None else None,
                max,
                float,
            ),
            "oldest_release": _superlative(
                watched_movies,
                lambda movie: parse_release_year(movie.get("year")),
                min,
            ),
            "newest_release": _superlative(
                watched_movies,
                lambda movie: parse_release_year(movie.get("year")),
                max,
            ),
            "recently_watched": _superlative(
                watched_movies,
                lambda movie: parse_watched_date(movie.get("watched_at")),
                max,
                lambda value: value.isoformat(),
            ),
        },
    }
