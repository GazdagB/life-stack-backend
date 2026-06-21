from psycopg.rows import dict_row

from app.database.db import get_connection

def get_user_by_username_public(username: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
            """
            SELECT id, username, email, created_at
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
            SELECT id, username, email, password_hash, created_at
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
            SELECT id, username, email, created_at
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
            SELECT id, username, email, password_hash, created_at
            FROM users 
            WHERE email = %s
            """,
            (email,),
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
            VALUES (%s,%s,%s) RETURNING id,username, email, created_at 
            """, (username,email,password_hash)).fetchone()