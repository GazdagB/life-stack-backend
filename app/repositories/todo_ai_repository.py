from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.database.db import get_connection


def get_todos_for_assessment(user_id: int, todo_ids: list[int] | None, limit: int = 30):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if todo_ids:
                return cur.execute(
                    """
                    SELECT id, title, description, due_date, status, updated_at
                    FROM todos
                    WHERE user_id = %s AND id = ANY(%s)
                    ORDER BY priority, due_date NULLS LAST, id
                    LIMIT %s
                    """,
                    (user_id, todo_ids, limit),
                ).fetchall()
            return cur.execute(
                """
                SELECT id, title, description, due_date, status, updated_at
                FROM todos
                WHERE user_id = %s AND status NOT IN ('completed', 'canceled')
                ORDER BY priority, due_date NULLS LAST, id
                LIMIT %s
                """,
                (user_id, limit),
            ).fetchall()


def upsert_todo_assessments(user_id: int, assessments: list[dict]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            for assessment in assessments:
                cur.execute(
                    """
                    INSERT INTO todo_ai_assessments (
                        user_id, todo_id, content_fingerprint, classification,
                        confidence, reason, ai_steps, human_steps,
                        missing_information, supported_actions, assessment_source,
                        model_name
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, todo_id) DO UPDATE SET
                        content_fingerprint = EXCLUDED.content_fingerprint,
                        classification = EXCLUDED.classification,
                        confidence = EXCLUDED.confidence,
                        reason = EXCLUDED.reason,
                        ai_steps = EXCLUDED.ai_steps,
                        human_steps = EXCLUDED.human_steps,
                        missing_information = EXCLUDED.missing_information,
                        supported_actions = EXCLUDED.supported_actions,
                        assessment_source = EXCLUDED.assessment_source,
                        model_name = EXCLUDED.model_name,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        user_id,
                        assessment["todo_id"],
                        assessment["content_fingerprint"],
                        assessment["classification"],
                        assessment["confidence"],
                        assessment["reason"],
                        Jsonb(assessment["ai_steps"]),
                        Jsonb(assessment["human_steps"]),
                        Jsonb(assessment["missing_information"]),
                        Jsonb(assessment["supported_actions"]),
                        assessment["assessment_source"],
                        assessment.get("model_name"),
                    ),
                )


def list_todo_assessments(user_id: int, todo_ids: list[int] | None = None):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            params: list[object] = [user_id]
            todo_filter = ""
            if todo_ids:
                todo_filter = " AND taa.todo_id = ANY(%s)"
                params.append(todo_ids)
            return cur.execute(
                """
                SELECT taa.*, t.title, t.description, t.due_date, t.status,
                       t.updated_at AS todo_updated_at
                FROM todo_ai_assessments taa
                JOIN todos t ON t.id = taa.todo_id AND t.user_id = taa.user_id
                WHERE taa.user_id = %s
                """ + todo_filter + " ORDER BY taa.updated_at DESC",
                params,
            ).fetchall()
