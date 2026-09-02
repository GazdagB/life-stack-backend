from fastapi import HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.database.db import get_connection


def get_todo_work_context(user_id: int, todo_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            context = cur.execute(
                """
                SELECT t.id, t.title, t.description, t.due_date, t.status, t.updated_at,
                       taa.content_fingerprint AS assessment_fingerprint,
                       taa.classification, taa.confidence, taa.reason,
                       taa.ai_steps, taa.human_steps AS assessed_human_steps,
                       taa.missing_information, taa.supported_actions
                FROM todos t
                LEFT JOIN todo_ai_assessments taa
                  ON taa.todo_id = t.id AND taa.user_id = t.user_id
                WHERE t.id = %s AND t.user_id = %s
                """,
                (todo_id, user_id),
            ).fetchone()
            if context is None:
                raise HTTPException(status_code=404, detail="TODO not found")
            return context


def get_or_create_work_session(user_id: int, todo_id: int, content_fingerprint: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            session = cur.execute(
                "SELECT * FROM todo_ai_work_sessions WHERE user_id = %s AND todo_id = %s",
                (user_id, todo_id),
            ).fetchone()
            if session is None:
                return cur.execute(
                    """
                    INSERT INTO todo_ai_work_sessions (user_id, todo_id, content_fingerprint)
                    VALUES (%s, %s, %s) RETURNING *
                    """,
                    (user_id, todo_id, content_fingerprint),
                ).fetchone()
            if session["content_fingerprint"] != content_fingerprint:
                cur.execute(
                    "DELETE FROM todo_ai_work_messages WHERE session_id = %s AND user_id = %s",
                    (session["id"], user_id),
                )
                session = cur.execute(
                    """
                    UPDATE todo_ai_work_sessions SET
                        content_fingerprint = %s, phase = 'GATHERING_INFORMATION',
                        questions = '[]'::jsonb, human_steps = '[]'::jsonb,
                        deliverable_title = NULL, deliverable_content = NULL,
                        model_name = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s RETURNING *
                    """,
                    (content_fingerprint, session["id"], user_id),
                ).fetchone()
            return session


def get_work_session(user_id: int, todo_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            session = cur.execute(
                "SELECT * FROM todo_ai_work_sessions WHERE user_id = %s AND todo_id = %s",
                (user_id, todo_id),
            ).fetchone()
            if session is None:
                raise HTTPException(status_code=404, detail="AI work session not found")
            return session


def list_work_messages(user_id: int, session_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                SELECT id, role, content, created_at
                FROM todo_ai_work_messages
                WHERE session_id = %s AND user_id = %s
                ORDER BY id
                """,
                (session_id, user_id),
            ).fetchall()


def append_work_message(user_id: int, session_id: int, role: str, content: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            session_exists = cur.execute(
                "SELECT 1 FROM todo_ai_work_sessions WHERE id = %s AND user_id = %s",
                (session_id, user_id),
            ).fetchone()
            if session_exists is None:
                raise HTTPException(status_code=404, detail="AI work session not found")
            return cur.execute(
                """
                INSERT INTO todo_ai_work_messages (session_id, user_id, role, content)
                VALUES (%s, %s, %s, %s)
                RETURNING id, role, content, created_at
                """,
                (session_id, user_id, role, content),
            ).fetchone()


def delete_work_message(user_id: int, message_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM todo_ai_work_messages WHERE id = %s AND user_id = %s",
                (message_id, user_id),
            )


def apply_assistant_turn(user_id: int, session_id: int, turn: dict, model_name: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            session = cur.execute(
                """
                UPDATE todo_ai_work_sessions SET
                    phase = %s, questions = %s, human_steps = %s,
                    deliverable_title = %s, deliverable_content = %s,
                    model_name = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s RETURNING *
                """,
                (
                    turn["phase"], Jsonb(turn["questions"]), Jsonb(turn["human_steps"]),
                    turn.get("deliverable_title"), turn.get("deliverable_content"),
                    model_name, session_id, user_id,
                ),
            ).fetchone()
            if session is None:
                raise HTTPException(status_code=404, detail="AI work session not found")
            cur.execute(
                """
                INSERT INTO todo_ai_work_messages (session_id, user_id, role, content)
                VALUES (%s, %s, 'ASSISTANT', %s)
                """,
                (session_id, user_id, turn["message"]),
            )
            return session


def update_work_draft(user_id: int, session_id: int, title: str, content: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            session = cur.execute(
                """
                UPDATE todo_ai_work_sessions SET
                    deliverable_title = %s, deliverable_content = %s,
                    phase = 'DRAFT_READY', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s RETURNING *
                """,
                (title, content, session_id, user_id),
            ).fetchone()
            if session is None:
                raise HTTPException(status_code=404, detail="AI work session not found")
            return session
