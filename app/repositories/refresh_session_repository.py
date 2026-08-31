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
    device_hash: str,
):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            now = datetime.now(timezone.utc)
            cur.execute(
                """
                UPDATE refresh_sessions
                SET revoked_at = COALESCE(revoked_at, %s)
                WHERE user_id = %s
                  AND device_hash = %s
                  AND revoked_at IS NULL
                """,
                (now, user_id, device_hash),
            )
            return cur.execute(
                """
                INSERT INTO refresh_sessions (
                    user_id,
                    family_id,
                    token_hash,
                    expires_at,
                    user_agent,
                    device_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING user_id, family_id, expires_at
                """,
                (user_id, family_id, token_hash, expires_at, user_agent, device_hash),
            ).fetchone()


def rotate_refresh_session(
    current_token_hash: str,
    next_token_hash: str,
    idle_days: int,
    user_agent: str | None,
    device_hash: str,
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
                    user_agent,
                    device_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session["user_id"],
                    session["family_id"],
                    next_token_hash,
                    session["expires_at"],
                    now,
                    user_agent,
                    device_hash,
                ),
            )
            return {
                "user_id": session["user_id"],
                "family_id": session["family_id"],
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


def list_active_refresh_sessions(
    user_id: int,
    current_token_hash: str | None,
    idle_days: int,
):
    idle_cutoff = datetime.now(timezone.utc) - timedelta(days=idle_days)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                SELECT family_id,
                       expires_at,
                       last_used_at,
                       (
                           SELECT MIN(history.created_at)
                           FROM refresh_sessions AS history
                           WHERE history.user_id = refresh_sessions.user_id
                             AND history.family_id = refresh_sessions.family_id
                       ) AS created_at,
                       user_agent,
                       device_hash IS NOT NULL AS is_recognized_device,
                       COALESCE(token_hash = %s, FALSE) AS is_current
                FROM refresh_sessions
                WHERE user_id = %s
                  AND revoked_at IS NULL
                  AND expires_at > CURRENT_TIMESTAMP
                  AND last_used_at > %s
                ORDER BY last_used_at DESC
                """,
                (current_token_hash, user_id, idle_cutoff),
            ).fetchall()


def revoke_refresh_session_family(user_id: int, family_id: UUID) -> bool:
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        with conn.cursor() as cur:
            result = cur.execute(
                """
                UPDATE refresh_sessions
                SET revoked_at = COALESCE(revoked_at, %s)
                WHERE user_id = %s
                  AND family_id = %s
                  AND revoked_at IS NULL
                """,
                (now, user_id, family_id),
            )
            return result.rowcount > 0


def revoke_other_refresh_sessions(user_id: int, current_token_hash: str) -> int | None:
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            current = cur.execute(
                """
                SELECT family_id
                FROM refresh_sessions
                WHERE user_id = %s
                  AND token_hash = %s
                  AND revoked_at IS NULL
                  AND expires_at > %s
                """,
                (user_id, current_token_hash, now),
            ).fetchone()
            if current is None:
                return None

            result = cur.execute(
                """
                UPDATE refresh_sessions
                SET revoked_at = COALESCE(revoked_at, %s)
                WHERE user_id = %s
                  AND family_id <> %s
                  AND revoked_at IS NULL
                """,
                (now, user_id, current["family_id"]),
            )
            return result.rowcount


def revoke_all_refresh_sessions(user_id: int) -> int:
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        with conn.cursor() as cur:
            result = cur.execute(
                """
                UPDATE refresh_sessions
                SET revoked_at = COALESCE(revoked_at, %s)
                WHERE user_id = %s
                  AND revoked_at IS NULL
                """,
                (now, user_id),
            )
            return result.rowcount


def is_refresh_session_family_active(user_id: int, family_id: UUID, idle_days: int) -> bool:
    idle_cutoff = datetime.now(timezone.utc) - timedelta(days=idle_days)
    with get_connection() as conn:
        with conn.cursor() as cur:
            return cur.execute(
                """
                SELECT 1
                FROM refresh_sessions
                WHERE user_id = %s
                  AND family_id = %s
                  AND revoked_at IS NULL
                  AND expires_at > CURRENT_TIMESTAMP
                  AND last_used_at > %s
                LIMIT 1
                """,
                (user_id, family_id, idle_cutoff),
            ).fetchone() is not None
