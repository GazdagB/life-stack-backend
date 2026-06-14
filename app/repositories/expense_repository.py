from datetime import datetime

from psycopg.rows import dict_row

from app.database.db import get_connection

def get_all_expenses():
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute('SELECT * FROM expenses').fetchall()

def insert_one_expense(expense):

    title = expense.title
    amount = expense.amount
    expense_date = expense.expense_date
    category_id = expense.category_id

    if expense_date is None:
        expense_date = datetime.now().date()

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute("""INSERT INTO expenses (title, amount,expense_date,category_id) VALUES (%s, %s, %s, %s) RETURNING *""", (title,amount,expense_date, category_id)).fetchall()

def update(expense,expense_id):
    title = expense.title
    amount = expense.amount
    expense_date = expense.expense_date
    category_id = expense.category_id

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
         return cur.execute("""UPDATE expenses SET title = %s,amount = %s, expense_date = %s, category_id = %s WHERE id = %s RETURNING *""",(title,amount,expense_date,category_id,expense_id)).fetchall()