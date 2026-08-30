import datetime

from psycopg.rows import dict_row
from fastapi import HTTPException


from app.database.db import get_connection

def query_all_todos(user_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                'SELECT * FROM todos WHERE user_id = %s ORDER BY sort_order, id',
                (user_id,),
            ).fetchall()

def query_post_todo(user_id: int, todo):
    title = todo.title
    description = todo.description
    priority = todo.priority
    due_date = todo.due_date
    sort_order = todo.sort_order
    source = todo.source

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                INSERT INTO todos (
                    user_id, title, description, priority, due_date, sort_order, source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, title, description, priority, due_date, sort_order, source),
            ).fetchone()

def query_update_todo(user_id: int, todo_id: int, todo):
    updated_at = datetime.datetime.now()

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            updated_todo = cur.execute(
                """
                UPDATE todos
                SET title = %s,
                    description = %s,
                    priority = %s,
                    updated_at = %s,
                    due_date = %s,
                    status = %s,
                    sort_order = %s,
                    source = %s
                WHERE id = %s AND user_id = %s
                RETURNING *
                """,
                (
                    todo.title,
                    todo.description,
                    todo.priority,
                    updated_at,
                    todo.due_date,
                    todo.status,
                    todo.sort_order,
                    todo.source,
                    todo_id,
                    user_id,
                ),
            ).fetchone()

            if updated_todo is None:
                raise HTTPException(status_code=404, detail="Todo not found")

            return updated_todo


def query_delete_todo(user_id: int, todo_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            deleted_todo = cur.execute(
                """
                DELETE FROM todos
                WHERE id = %s AND user_id = %s
                RETURNING *
                """,
                (todo_id, user_id),
            ).fetchone()

            if deleted_todo is None:
                raise HTTPException(status_code=404, detail="Todo not found")

            return {
                "message": f"Successfully deleted todo with the id: {todo_id}",
                "todo": deleted_todo,
            }
