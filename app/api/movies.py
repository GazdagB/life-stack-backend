from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator

from app.repositories.movie_repository import (
    create_user_movie,
    delete_user_movie,
    get_user_movie,
    get_user_movie_by_imdb_id,
    get_user_movies_by_imdb_ids,
    get_recent_rated_movies,
    get_top_rated_movies,
    get_saved_movie_keys,
    list_user_movies,
    update_user_movie,
)
from app.services.auth_service import get_current_user, get_current_user_id
from app.services.movie_catalog_service import movie_catalog
from app.services.movie_recommendation_service import (
    ai_recommendation_client,
    build_verified_recommendations,
)

router = APIRouter(prefix="/movies", tags=["movies"])


class MovieCreate(BaseModel):
    imdb_id: str = Field(pattern=r"^tt\d+$", max_length=20)
    list_status: Literal["WANT_TO_WATCH", "WATCHED"] = "WANT_TO_WATCH"


class MovieUpdate(BaseModel):
    list_status: Literal["WANT_TO_WATCH", "WATCHED"]
    personal_rating: Decimal | None = Field(default=None, ge=1, le=10, decimal_places=1)
    critique: str | None = Field(default=None, max_length=2000)
    watched_at: date | None = None

    @model_validator(mode="after")
    def validate_watched_fields(self):
        if self.list_status == "WANT_TO_WATCH":
            if self.personal_rating is not None or self.watched_at is not None:
                raise ValueError("Only watched movies can have a rating or watched date")
        self.critique = self.critique.strip() if self.critique else None
        return self


@router.get("/search")
def search_movies(
    q: str = Query(min_length=2, max_length=100),
    page: int = Query(default=1, ge=1, le=100),
    current_user_id: int = Depends(get_current_user_id),
):
    result = movie_catalog.search(q.strip(), page)
    saved_movies = get_user_movies_by_imdb_ids(
        current_user_id,
        [item["imdb_id"] for item in result["results"]],
    )
    for item in result["results"]:
        saved = saved_movies.get(item["imdb_id"])
        item["library_id"] = saved["id"] if saved else None
        item["list_status"] = saved["list_status"] if saved else None
    return result


@router.get("/catalog/{imdb_id}")
def get_catalog_movie(
    imdb_id: str,
    current_user_id: int = Depends(get_current_user_id),
):
    details = movie_catalog.details(imdb_id)
    saved = get_user_movie_by_imdb_id(current_user_id, imdb_id)
    details["library_id"] = saved["id"] if saved else None
    details["list_status"] = saved["list_status"] if saved else None
    return details


@router.get("/")
def get_movies(
    list_status: Literal["WANT_TO_WATCH", "WATCHED"] | None = None,
    current_user_id: int = Depends(get_current_user_id),
):
    return list_user_movies(current_user_id, list_status)


@router.post("/recommendations")
def recommend_movie(current_user=Depends(get_current_user)):
    rated_movies = get_recent_rated_movies(current_user["id"])
    top_rated_movies = get_top_rated_movies(
        current_user["id"],
        [movie["imdb_id"] for movie in rated_movies],
    )
    saved_movies = get_saved_movie_keys(current_user["id"])
    return build_verified_recommendations(
        rated_movies,
        saved_movies,
        ai_recommendation_client,
        movie_catalog,
        current_user.get("preferred_language") or "en",
        top_rated_movies,
    )


@router.get("/{movie_id}")
def get_movie(movie_id: int, current_user_id: int = Depends(get_current_user_id)):
    return get_user_movie(current_user_id, movie_id)


@router.post("/", status_code=201)
def add_movie(
    movie: MovieCreate,
    current_user_id: int = Depends(get_current_user_id),
):
    details = movie_catalog.details(movie.imdb_id)
    return create_user_movie(current_user_id, details, movie.list_status)


@router.put("/{movie_id}")
def update_movie(
    movie_id: int,
    movie: MovieUpdate,
    current_user_id: int = Depends(get_current_user_id),
):
    return update_user_movie(current_user_id, movie_id, movie)


@router.delete("/{movie_id}")
def delete_movie(movie_id: int, current_user_id: int = Depends(get_current_user_id)):
    return delete_user_movie(current_user_id, movie_id)
