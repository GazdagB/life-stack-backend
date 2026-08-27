from fastapi import HTTPException
from psycopg.rows import dict_row

from app.database.db import get_connection


def get_recurring_expenses(current_user_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                SELECT *
                FROM recurring_expenses
                WHERE user_id = %s
                ORDER BY active DESC, amount DESC, id DESC
                """,
                (current_user_id,),
            ).fetchall()


def create_recurring_expense(recurring_expense, current_user_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                INSERT INTO recurring_expenses (
                    user_id,
                    title,
                    amount,
                    category_id,
                    frequency,
                    start_date,
                    end_date,
                    cancellation_difficulty,
                    cancellable_from,
                    cancellation_notes,
                    active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    current_user_id,
                    recurring_expense.title,
                    recurring_expense.amount,
                    recurring_expense.category_id,
                    recurring_expense.frequency,
                    recurring_expense.start_date,
                    recurring_expense.end_date,
                    recurring_expense.cancellation_difficulty,
                    recurring_expense.cancellable_from,
                    recurring_expense.cancellation_notes,
                    recurring_expense.active,
                ),
            ).fetchone()


def update_recurring_expense(
    recurring_expense_id: int,
    recurring_expense,
    current_user_id: int,
):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            updated = cur.execute(
                """
                UPDATE recurring_expenses
                SET title = %s,
                    amount = %s,
                    category_id = %s,
                    frequency = %s,
                    start_date = %s,
                    end_date = %s,
                    cancellation_difficulty = %s,
                    cancellable_from = %s,
                    cancellation_notes = %s,
                    active = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND user_id = %s
                RETURNING *
                """,
                (
                    recurring_expense.title,
                    recurring_expense.amount,
                    recurring_expense.category_id,
                    recurring_expense.frequency,
                    recurring_expense.start_date,
                    recurring_expense.end_date,
                    recurring_expense.cancellation_difficulty,
                    recurring_expense.cancellable_from,
                    recurring_expense.cancellation_notes,
                    recurring_expense.active,
                    recurring_expense_id,
                    current_user_id,
                ),
            ).fetchone()

            if updated is None:
                raise HTTPException(status_code=404, detail="Recurring expense not found")

            return updated


def delete_recurring_expense(recurring_expense_id: int, current_user_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            deleted = cur.execute(
                """
                DELETE FROM recurring_expenses
                WHERE id = %s AND user_id = %s
                RETURNING id
                """,
                (recurring_expense_id, current_user_id),
            ).fetchone()

            if deleted is None:
                raise HTTPException(status_code=404, detail="Recurring expense not found")

            return {
                "message": "Recurring expense deleted successfully",
                "id": deleted["id"],
            }
