from fastapi import APIRouter
from app.repositories.expense_repository import get_all_expenses, insert_one_expense, update_expense,delete_expense
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
)
#TODO: Move out these schemas from here
class ExpenseCreate(BaseModel):
    title: str
    amount: Decimal
    expense_date: date | None
    category_id: int

@router.get("/")
def get_all():
    return get_all_expenses()

@router.post("/")
def create_one(expense: ExpenseCreate):
    return insert_one_expense(expense)

@router.put("/")
def update(expense: ExpenseCreate,expense_id):
    return update_expense(expense,expense_id)

@router.delete("/{expense_id}")
def delete(expense_id: int):
    return delete_expense(expense_id)