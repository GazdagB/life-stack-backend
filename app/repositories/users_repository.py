from psycopg.rows import dict_row

from app.database.db import get_connection

def get_user_by_username(username: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
            """
            SELECT id, username, email password_hash, created_at
            FROM users 
            WHERE username = %s
            """,
            (username,),
            ).fetchone()