import json

from fastapi import HTTPException
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from app.database.db import get_connection


def list_user_movies(user_id: int, list_status: str | None = None):
    query = "SELECT * FROM user_movies WHERE user_id = %s"
    params: list[object] = [user_id]
    if list_status:
        query += " AND list_status = %s"
        params.append(list_status)
    query += " ORDER BY COALESCE(watched_at, created_at::date) DESC, updated_at DESC"
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(query, params).fetchall()


def get_user_movie(user_id: int, movie_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            movie = cur.execute(
                "SELECT * FROM user_movies WHERE id = %s AND user_id = %s",
                (movie_id, user_id),
            ).fetchone()
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found in your library")
    return movie


def get_user_movie_by_imdb_id(user_id: int, imdb_id: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                "SELECT * FROM user_movies WHERE imdb_id = %s AND user_id = %s",
                (imdb_id, user_id),
            ).fetchone()


def get_user_movies_by_imdb_ids(user_id: int, imdb_ids: list[str]):
    if not imdb_ids:
        return {}
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            movies = cur.execute(
                "SELECT id, imdb_id, list_status FROM user_movies WHERE user_id = %s AND imdb_id = ANY(%s)",
                (user_id, imdb_ids),
            ).fetchall()
    return {movie["imdb_id"]: movie for movie in movies}


def get_recent_rated_movies(user_id: int, limit: int = 10):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                SELECT imdb_id, title, year, genre, director, personal_rating, critique, watched_at, updated_at
                FROM user_movies
                WHERE user_id = %s
                  AND list_status = 'WATCHED'
                  AND personal_rating IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            ).fetchall()


def get_top_rated_movies(
    user_id: int,
    exclude_imdb_ids: list[str] | None = None,
    limit: int = 5,
):
    excluded = exclude_imdb_ids or []
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                SELECT imdb_id, title, year, genre, director, personal_rating, critique, watched_at, updated_at
                FROM user_movies
                WHERE user_id = %s
                  AND list_status = 'WATCHED'
                  AND personal_rating IS NOT NULL
                  AND NOT (imdb_id = ANY(%s))
                ORDER BY personal_rating DESC,
                         COALESCE(watched_at, created_at::date) DESC,
                         updated_at DESC
                LIMIT %s
                """,
                (user_id, excluded, limit),
            ).fetchall()


def get_saved_movie_keys(user_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                SELECT imdb_id, title, year
                FROM user_movies
                WHERE user_id = %s
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()


def create_user_movie(user_id: int, details: dict, list_status: str):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                return cur.execute(
                    """
                    INSERT INTO user_movies (
                        user_id, imdb_id, title, year, poster_url, plot, director,
                        actors, genre, runtime, content_rating, released, awards,
                        country, language, box_office, external_ratings, list_status, watched_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s,
                        CASE WHEN %s = 'WATCHED' THEN CURRENT_DATE ELSE NULL END)
                    RETURNING *
                    """,
                    (
                        user_id, details["imdb_id"], details["title"], details["year"],
                        details["poster_url"], details["plot"], details["director"],
                        details["actors"], details["genre"], details["runtime"],
                        details["content_rating"], details["released"], details["awards"],
                        details["country"], details["language"], details["box_office"],
                        json.dumps(details["external_ratings"]),
                        list_status, list_status,
                    ),
                ).fetchone()
    except UniqueViolation as error:
        raise HTTPException(status_code=409, detail="This movie is already in your library") from error


def update_user_movie(user_id: int, movie_id: int, data):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            movie = cur.execute(
                """
                UPDATE user_movies
                SET list_status = %s,
                    personal_rating = %s,
                    critique = %s,
                    watched_at = CASE
                        WHEN %s = 'WATCHED' THEN COALESCE(%s, watched_at, CURRENT_DATE)
                        ELSE NULL
                    END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                RETURNING *
                """,
                (
                    data.list_status, data.personal_rating, data.critique,
                    data.list_status, data.watched_at, movie_id, user_id,
                ),
            ).fetchone()
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found in your library")
    return movie


def delete_user_movie(user_id: int, movie_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            deleted = cur.execute(
                "DELETE FROM user_movies WHERE id = %s AND user_id = %s RETURNING id",
                (movie_id, user_id),
            ).fetchone()
    if deleted is None:
        raise HTTPException(status_code=404, detail="Movie not found in your library")
    return {"message": "Movie removed from your library", "id": deleted["id"]}
