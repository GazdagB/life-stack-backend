from datetime import datetime, timedelta, timezone
from uuid import UUID

from psycopg.rows import dict_row

from app.database.db import get_connection


def create_refresh_session(
    user_id: int,
    family_id: UUID,
    token_hash: str,
    expires_at: datetime,
    user_agent: str | None,
):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                INSERT INTO refresh_sessions (
                    user_id,
                    family_id,
                    token_hash,
                    expires_at,
                    user_agent
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING user_id, family_id, expires_at
                """,
                (user_id, family_id, token_hash, expires_at, user_agent),
            ).fetchone()


def rotate_refresh_session(
    current_token_hash: str,
    next_token_hash: str,
    idle_days: int,
    user_agent: str | None,
):
    now = datetime.now(timezone.utc)
    idle_cutoff = now - timedelta(days=idle_days)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            session = cur.execute(
                """
                SELECT id, user_id, family_id, expires_at, last_used_at, revoked_at
                FROM refresh_sessions
                WHERE token_hash = %s
                FOR UPDATE
                """,
                (current_token_hash,),
            ).fetchone()

            if session is None:
                return None

            if session["revoked_at"] is not None:
                cur.execute(
                    """
                    UPDATE refresh_sessions
                    SET revoked_at = COALESCE(revoked_at, %s)
                    WHERE family_id = %s
                    """,
                    (now, session["family_id"]),
                )
                return None

            if session["expires_at"] <= now or session["last_used_at"] <= idle_cutoff:
                cur.execute(
                    """
                    UPDATE refresh_sessions
                    SET revoked_at = COALESCE(revoked_at, %s)
                    WHERE family_id = %s
                    """,
                    (now, session["family_id"]),
                )
                return None

            cur.execute(
                """
                UPDATE refresh_sessions
                SET revoked_at = %s,
                    last_used_at = %s
                WHERE id = %s
                """,
                (now, now, session["id"]),
            )
            cur.execute(
                """
                INSERT INTO refresh_sessions (
                    user_id,
                    family_id,
                    token_hash,
                    expires_at,
                    last_used_at,
                    user_agent
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    session["family_id"],
                    next_token_hash,
                    session["expires_at"],
                    now,
                    user_agent,
                ),
            )
            return {
                "user_id": session["user_id"],
                "expires_at": session["expires_at"],
            }


def revoke_refresh_session(token_hash: str):
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            session = cur.execute(
                """
                SELECT family_id
                FROM refresh_sessions
                WHERE token_hash = %s
                """,
                (token_hash,),
            ).fetchone()
            if session is None:
                return False

            cur.execute(
                """
                UPDATE refresh_sessions
                SET revoked_at = COALESCE(revoked_at, %s)
                WHERE family_id = %s
                """,
                (now, session["family_id"]),
            )
            return True
