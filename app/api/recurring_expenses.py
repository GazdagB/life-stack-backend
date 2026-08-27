from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator

from app.repositories.recurring_expense_repository import (
    create_recurring_expense,
    delete_recurring_expense,
    get_recurring_expenses,
    update_recurring_expense,
)
from app.services.auth_service import get_current_user_id
from app.services.recurring_forecast_service import build_recurring_coverage

router = APIRouter(
    prefix="/recurring-expenses",
    tags=["recurring-expenses"],
)


class RecurringExpenseInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0)
    category_id: int
    frequency: Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]
    start_date: date
    end_date: date | None = None
    cancellation_difficulty: Literal[
        "EASY",
        "NOTICE_REQUIRED",
        "CONTRACT_LOCKED",
        "NON_CANCELLABLE",
        "ESSENTIAL",
    ] = "EASY"
    cancellable_from: date | None = None
    cancellation_notes: str | None = Field(default=None, max_length=280)
    active: bool = True

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")
        if self.cancellable_from is not None and self.cancellable_from < self.start_date:
            raise ValueError("Earliest cancellation date cannot be before start date")
        if self.cancellable_from is not None and self.cancellation_difficulty not in (
            "NOTICE_REQUIRED",
            "CONTRACT_LOCKED",
        ):
            raise ValueError(
                "Earliest cancellation date is only valid when notice or a contract lock applies"
            )
        return self


class CoverageTotals(BaseModel):
    daily_reserve: Decimal
    weekly_reserve: Decimal
    monthly_reserve: Decimal
    horizon_total: Decimal


class CommitmentForecast(BaseModel):
    recurring_expense_id: int
    included_in_coverage: bool
    horizon_total: Decimal
    horizon_payment_count: int
    daily_reserve: Decimal
    weekly_reserve: Decimal
    monthly_reserve: Decimal
    remaining_total: Decimal | None
    remaining_payment_count: int | None
    contract_total: Decimal | None
    contract_payment_count: int | None


class RecurringCoverage(BaseModel):
    as_of: date
    through: date
    horizon_days: int
    totals: CoverageTotals
    commitments: list[CommitmentForecast]


@router.get("/")
def get_all(current_user_id: int = Depends(get_current_user_id)):
    return get_recurring_expenses(current_user_id)


@router.get("/coverage", response_model=RecurringCoverage)
def get_coverage(
    as_of: date | None = None,
    horizon_days: int = Query(default=365, ge=1, le=3660),
    current_user_id: int = Depends(get_current_user_id),
):
    return build_recurring_coverage(
        get_recurring_expenses(current_user_id),
        as_of or date.today(),
        horizon_days,
    )


@router.post("/")
def create_one(
    recurring_expense: RecurringExpenseInput,
    current_user_id: int = Depends(get_current_user_id),
):
    return create_recurring_expense(recurring_expense, current_user_id)


@router.put("/{recurring_expense_id}")
def update_one(
    recurring_expense_id: int,
    recurring_expense: RecurringExpenseInput,
    current_user_id: int = Depends(get_current_user_id),
):
    return update_recurring_expense(
        recurring_expense_id,
        recurring_expense,
        current_user_id,
    )


@router.delete("/{recurring_expense_id}")
def delete_one(
    recurring_expense_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    return delete_recurring_expense(recurring_expense_id, current_user_id)
