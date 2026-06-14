from fastapi import APIRouter
from app.repositories.expense_repository import get_all_expenses, insert_one_expense
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
def get_expenses():
    return get_all_expenses()

@router.post("/")
def create_expense(expense: ExpenseCreate):
    return insert_one_expense(expense)
