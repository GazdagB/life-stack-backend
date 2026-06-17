import datetime

import psycopg
from psycopg.rows import dict_row
from fastapi import HTTPException


from app.database.db import get_connection

def query_all_todos():
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute('SELECT * FROM todos').fetchall()

def query_post_todo(todo):
    title = todo.title
    description = todo.description
    priority = todo.priority
    due_date = todo.due_date
    sort_order = todo.sort_order
    source = todo.source

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return  cur.execute("""INSERT INTO todos (title,description, priority, due_date, sort_order, source) VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""", (title,description,priority,due_date,sort_order, source)).fetchall()

#TODO: Add HTTP Exception if not found

def query_update_todo(todo_id, todo):
    updated_at = datetime.datetime.now()

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
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
                WHERE id = %s
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
                ),
            ).fetchone()


def query_delete_todo(todo_id):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            deleted_todo = cur.execute(
                """
                DELETE FROM todos
                WHERE id = %s
                RETURNING *
                """,
                [todo_id],
            ).fetchone()

            if deleted_todo is None:
                raise HTTPException(status_code=404, detail="Todo not found")

            return {
                "message": f"Successfully deleted todo with the id: {todo_id}",
                "todo": deleted_todo,
            }


