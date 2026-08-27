from fastapi import APIRouter
from fastapi.params import Depends

from app.repositories.expense_repository import get_all_expenses, insert_one_expense, update_expense,delete_expense
from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal

from app.services.auth_service import get_current_user_id

router = APIRouter(
    prefix="/expenses",
    tags=["expenses"],
)
#TODO: Move out these schemas from here
class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=30)
    amount: Decimal
    expense_date: date | None
    category_id: int
    description: str | None = Field(default=None, max_length=1000)

@router.get("/")
def get_all(current_user_id: int = Depends(get_current_user_id)):
    return {
        "message": "You are authenticated",
        "user_id": current_user_id,
        "expenses": get_all_expenses(current_user_id),
    }

@router.post("/")
def create_one(
    expense: ExpenseCreate,
    current_user_id: int = Depends(get_current_user_id),
):
    return insert_one_expense(expense, current_user_id)

#TODO: Add HTTP Exception if not found
@router.put("/{expense_id}")
def update(
    expense: ExpenseCreate,
    expense_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    return update_expense(expense, expense_id, current_user_id)

#TODO: Add HTTP Exception if not found
@router.delete("/{expense_id}")
def delete(
    expense_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    return delete_expense(expense_id, current_user_id)
