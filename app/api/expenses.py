from fastapi import APIRouter
from fastapi.params import Depends

from app.repositories.expense_repository import get_all_expenses, insert_one_expense, update_expense,delete_expense
from pydantic import BaseModel
from datetime import date
from decimal import Decimal

from app.services.auth_service import get_current_user_id

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
def get_all(current_user_id: int = Depends(get_current_user_id)):
    return {
        "message": "You are authenticated",
        "user_id": current_user_id,
        "expenses": get_all_expenses(current_user_id),
    }

@router.post("/")
def create_one(expense: ExpenseCreate):
    return insert_one_expense(expense)

#TODO: Add HTTP Exception if not found
@router.put("/{expense_id}")
def update(expense: ExpenseCreate,expense_id: int):
    return update_expense(expense,expense_id)

#TODO: Add HTTP Exception if not found
@router.delete("/{expense_id}")
def delete(expense_id: int):
    return delete_expense(expense_id)