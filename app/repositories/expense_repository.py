from datetime import datetime

from psycopg.rows import dict_row

from app.database.db import get_connection

def get_all_expenses(current_user_id):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute('SELECT * FROM expenses WHERE user_id= %s', (current_user_id,),).fetchall()

def insert_one_expense(expense, current_user_id):

    title = expense.title
    amount = expense.amount
    expense_date = expense.expense_date
    category_id = expense.category_id
    description = expense.description.strip() if expense.description else None

    if expense_date is None:
        expense_date = datetime.now().date()

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """INSERT INTO expenses (title, amount, expense_date, category_id, user_id, description)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (title, amount, expense_date, category_id, current_user_id, description),
            ).fetchall()

def update_expense(expense, expense_id, current_user_id):
    title = expense.title
    amount = expense.amount
    expense_date = expense.expense_date
    category_id = expense.category_id
    description = expense.description.strip() if expense.description else None

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
         return cur.execute(
             """UPDATE expenses
                SET title = %s, amount = %s, expense_date = %s, category_id = %s, description = %s
                WHERE id = %s AND user_id = %s
                RETURNING *""",
             (title, amount, expense_date, category_id, description, expense_id, current_user_id),
         ).fetchall()


def delete_expense(expense_id, current_user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM expenses WHERE id = %s AND user_id = %s",
                (expense_id, current_user_id),
            )
            return {"message": "Expense deleted successfully",
                    "id": expense_id
                    }
