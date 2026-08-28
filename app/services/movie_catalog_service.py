from typing import Any

import httpx
from fastapi import HTTPException

from app.config import settings

OMDB_BASE_URL = "https://www.omdbapi.com/"


def _optional(value: Any) -> str | None:
    if not isinstance(value, str) or value.strip() in ("", "N/A"):
        return None
    return value.strip()


def normalize_search(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("Response") == "False":
        message = payload.get("Error", "No movies found")
        if message == "Movie not found!":
            return {"results": [], "total_results": 0}
        raise HTTPException(status_code=502, detail=f"Movie provider error: {message}")

    results = []
    for item in payload.get("Search", []):
        if item.get("Type") != "movie":
            continue
        results.append({
            "imdb_id": item.get("imdbID"),
            "title": item.get("Title"),
            "year": _optional(item.get("Year")),
            "poster_url": _optional(item.get("Poster")),
        })
    return {
        "results": results,
        "total_results": int(payload.get("totalResults", len(results))),
    }


def normalize_details(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("Response") == "False":
        message = payload.get("Error", "Movie not found")
        raise HTTPException(status_code=404, detail=message)

    ratings = [
        {"source": rating.get("Source"), "value": rating.get("Value")}
        for rating in payload.get("Ratings", [])
        if rating.get("Source") and rating.get("Value")
    ]
    return {
        "imdb_id": payload.get("imdbID"),
        "title": payload.get("Title"),
        "year": _optional(payload.get("Year")),
        "poster_url": _optional(payload.get("Poster")),
        "plot": _optional(payload.get("Plot")),
        "director": _optional(payload.get("Director")),
        "actors": _optional(payload.get("Actors")),
        "genre": _optional(payload.get("Genre")),
        "runtime": _optional(payload.get("Runtime")),
        "content_rating": _optional(payload.get("Rated")),
        "released": _optional(payload.get("Released")),
        "awards": _optional(payload.get("Awards")),
        "country": _optional(payload.get("Country")),
        "language": _optional(payload.get("Language")),
        "box_office": _optional(payload.get("BoxOffice")),
        "external_ratings": ratings,
    }


class MovieCatalog:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.OMDB_API_KEY

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise HTTPException(
                status_code=503,
                detail="Movie search is not configured. Add OMDB_API_KEY to the backend environment.",
            )
        try:
            response = httpx.get(
                OMDB_BASE_URL,
                params={"apikey": self.api_key, **params},
                timeout=8.0,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise HTTPException(
                status_code=502,
                detail="The movie provider is temporarily unavailable.",
            ) from error

    def search(self, query: str, page: int = 1) -> dict[str, Any]:
        return normalize_search(self._request({"s": query, "type": "movie", "page": page}))

    def details(self, imdb_id: str) -> dict[str, Any]:
        return normalize_details(self._request({"i": imdb_id, "plot": "full"}))

    def details_by_title(self, title: str, year: int | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"t": title, "type": "movie", "plot": "full"}
        if year is not None:
            params["y"] = year
        return normalize_details(self._request(params))


movie_catalog = MovieCatalog()
