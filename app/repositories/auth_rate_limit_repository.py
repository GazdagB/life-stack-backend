from datetime import datetime, timedelta, timezone

from app.database.db import get_connection


def consume_auth_rate_limits(
    attempts: list[tuple[str, str, int]],
    window_seconds: int,
) -> int:
    """Consume one attempt for each scope and return the longest retry delay."""
    now = datetime.now(timezone.utc)
    window_cutoff = now - timedelta(seconds=window_seconds)
    cleanup_cutoff = now - timedelta(days=1)
    retry_after = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM auth_rate_limits WHERE window_started_at < %s",
                (cleanup_cutoff,),
            )
            for scope, key_hash, limit in attempts:
                row = cur.execute(
                    """
                    INSERT INTO auth_rate_limits (
                        scope, key_hash, attempt_count, window_started_at
                    ) VALUES (%s, %s, 1, %s)
                    ON CONFLICT (scope, key_hash) DO UPDATE SET
                        attempt_count = CASE
                            WHEN auth_rate_limits.window_started_at <= %s THEN 1
                            ELSE auth_rate_limits.attempt_count + 1
                        END,
                        window_started_at = CASE
                            WHEN auth_rate_limits.window_started_at <= %s THEN %s
                            ELSE auth_rate_limits.window_started_at
                        END
                    RETURNING attempt_count, window_started_at
                    """,
                    (scope, key_hash, now, window_cutoff, window_cutoff, now),
                ).fetchone()
                if row[0] > limit:
                    reset_at = row[1] + timedelta(seconds=window_seconds)
                    retry_after = max(
                        retry_after,
                        max(1, int((reset_at - now).total_seconds()) + 1),
                    )

    return retry_after


def clear_auth_rate_limits(keys: list[tuple[str, str]]):
    if not keys:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                "DELETE FROM auth_rate_limits WHERE scope = %s AND key_hash = %s",
                keys,
            )
