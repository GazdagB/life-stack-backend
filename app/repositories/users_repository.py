from fastapi import HTTPException
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from starlette import status

from app.database.db import get_connection

def get_user_by_username_public(username: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
            """
            SELECT id, username, email, display_name, bio,
                   avatar_data IS NOT NULL AS has_avatar,
                   preferred_language,
                   created_at, updated_at
            FROM users 
            WHERE username = %s
            """,
            (username,),
            ).fetchone()

def get_user_by_username_private(username: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
            """
            SELECT id, username, email, password_hash, display_name, bio,
                   avatar_data IS NOT NULL AS has_avatar,
                   preferred_language,
                   created_at, updated_at
            FROM users 
            WHERE username = %s
            """,
            (username,),
            ).fetchone()

def get_user_by_email_public(email: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
            """
            SELECT id, username, email, display_name, bio,
                   avatar_data IS NOT NULL AS has_avatar,
                   preferred_language,
                   created_at, updated_at
            FROM users 
            WHERE email = %s
            """,
            (email,),
            ).fetchone()

def get_user_by_email_private(email: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
            """
            SELECT id, username, email, password_hash, display_name, bio,
                   avatar_data IS NOT NULL AS has_avatar,
                   preferred_language,
                   created_at, updated_at
            FROM users 
            WHERE email = %s
            """,
            (email,),
            ).fetchone()


def get_user_by_id_public(user_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
            """
            SELECT id, username, email, display_name, bio,
                   avatar_data IS NOT NULL AS has_avatar,
                   preferred_language,
                   created_at, updated_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
            ).fetchone()


def get_user_pw_hash(username: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute("""
            SELECT password_hash FROM users 
            WHERE username = %s
            """, (username,),).fetchone()

def create_user(username: str, email: str, password_hash: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
           return cur.execute("""
            INSERT INTO users (username,email,password_hash)
            VALUES (%s,%s,%s)
            RETURNING id, username, email, display_name, bio,
                      FALSE AS has_avatar, preferred_language,
                      created_at, updated_at
            """, (username,email,password_hash)).fetchone()


def update_user_password_hash(user_id: int, password_hash: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (password_hash, user_id),
            )


def update_user_profile(
    user_id: int,
    username: str,
    email: str,
    display_name: str | None,
    bio: str | None,
):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                return cur.execute(
                    """
                    UPDATE users
                    SET username = %s,
                        email = %s,
                        display_name = %s,
                        bio = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id, username, email, display_name, bio,
                              avatar_data IS NOT NULL AS has_avatar,
                              preferred_language,
                              created_at, updated_at
                    """,
                    (username, email, display_name, bio, user_id),
                ).fetchone()
    except UniqueViolation as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username or email is already in use",
        ) from error


def update_user_avatar(user_id: int, content: bytes, content_type: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                UPDATE users
                SET avatar_data = %s,
                    avatar_content_type = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, username, email, display_name, bio,
                          TRUE AS has_avatar, preferred_language,
                          created_at, updated_at
                """,
                (content, content_type, user_id),
            ).fetchone()


def delete_user_avatar(user_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                UPDATE users
                SET avatar_data = NULL,
                    avatar_content_type = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, username, email, display_name, bio,
                          FALSE AS has_avatar, preferred_language,
                          created_at, updated_at
                """,
                (user_id,),
            ).fetchone()


def update_user_language(user_id: int, preferred_language: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                UPDATE users
                SET preferred_language = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, username, email, display_name, bio,
                          avatar_data IS NOT NULL AS has_avatar,
                          preferred_language, created_at, updated_at
                """,
                (preferred_language, user_id),
            ).fetchone()


def get_user_avatar(user_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                SELECT avatar_data, avatar_content_type
                FROM users
                WHERE id = %s AND avatar_data IS NOT NULL
                """,
                (user_id,),
            ).fetchone()
