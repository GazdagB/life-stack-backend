from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.repositories.net_worth_repository import (
    create_net_worth_item, delete_net_worth_item, get_net_worth_history,
    list_net_worth_items, snapshot_all_items, update_net_worth_item,
)
from app.services.auth_service import get_current_user_id
from app.services.net_worth_service import calculate_net_worth_summary


router = APIRouter(prefix="/net-worth", tags=["net-worth"])

ItemKind = Literal["ASSET", "LIABILITY"]
ItemCategory = Literal[
    "CASH", "BANK", "INVESTMENT", "PROPERTY", "VEHICLE",
    "BUSINESS", "LOAN", "CREDIT_CARD", "OTHER",
]


class NetWorthItemInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: ItemKind
    category: ItemCategory
    current_value: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    ownership_percent: Decimal = Field(default=Decimal("100"), gt=0, le=100)
    linked_bank_account_id: int | None = None
    notes: str | None = Field(default=None, max_length=500)
    active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name cannot be blank")
        return normalized

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized.isalpha():
            raise ValueError("Currency must be a three-letter code")
        return normalized


@router.get("/items")
def get_items(user_id: int = Depends(get_current_user_id)):
    return list_net_worth_items(user_id)


@router.post("/items")
def create_item(item: NetWorthItemInput, user_id: int = Depends(get_current_user_id)):
    return create_net_worth_item(user_id, item)


@router.put("/items/{item_id}")
def update_item(item_id: int, item: NetWorthItemInput, user_id: int = Depends(get_current_user_id)):
    return update_net_worth_item(user_id, item_id, item)


@router.delete("/items/{item_id}")
def delete_item(item_id: int, user_id: int = Depends(get_current_user_id)):
    return delete_net_worth_item(user_id, item_id)


@router.get("/summary")
def get_summary(
    currency: str = Query(default="EUR", min_length=3, max_length=3),
    user_id: int = Depends(get_current_user_id),
):
    return calculate_net_worth_summary(list_net_worth_items(user_id), currency.upper())


@router.get("/history")
def get_history(
    currency: str = Query(default="EUR", min_length=3, max_length=3),
    days: int = Query(default=365, ge=1, le=3650),
    user_id: int = Depends(get_current_user_id),
):
    points = get_net_worth_history(user_id, currency.upper(), date.today() - timedelta(days=days))
    return [
        {**point, "net_worth": point["assets"] - point["liabilities"]}
        for point in points
    ]


@router.post("/snapshots")
def create_snapshot(
    recorded_on: date | None = None,
    user_id: int = Depends(get_current_user_id),
):
    snapshot_date = recorded_on or date.today()
    if snapshot_date > date.today():
        raise HTTPException(status_code=422, detail="Snapshot date cannot be in the future")
    return snapshot_all_items(user_id, snapshot_date)
