from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException

MONEY = Decimal("0.01")
HUNDRED = Decimal("100")


def money(value: Any) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def calculate_invoice_items(items: list[Any], multiplier: int = 1):
    calculated = []
    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")

    for index, item in enumerate(items):
        source = item if isinstance(item, dict) else item.model_dump()
        quantity = Decimal(str(source["quantity"]))
        unit_price = money(source["unit_price"]) * multiplier
        tax_rate = Decimal(str(source["tax_rate"]))
        net_total = money(quantity * unit_price)
        item_tax = money(net_total * tax_rate / HUNDRED)
        gross_total = money(net_total + item_tax)
        calculated.append({
            "description": source["description"].strip(),
            "quantity": quantity,
            "unit": source.get("unit", "item").strip() or "item",
            "unit_price": unit_price,
            "tax_rate": tax_rate,
            "net_total": net_total,
            "tax_total": item_tax,
            "gross_total": gross_total,
            "sort_order": index,
        })
        subtotal += net_total
        tax_total += item_tax

    return {
        "items": calculated,
        "subtotal": money(subtotal),
        "tax_total": money(tax_total),
        "total": money(subtotal + tax_total),
    }


def format_invoice_number(prefix: str, year: int, sequence: int) -> str:
    normalized_prefix = prefix.strip().upper()
    if normalized_prefix:
        return f"{normalized_prefix}-{year}-{sequence:04d}"
    return f"{sequence:03d}/{year}"


def validate_issue_readiness(business: dict, client: dict, invoice: dict):
    missing = []
    required_business_fields = {
        "address_line1": "business street address",
        "postal_code": "business postal code",
        "city": "business city",
        "country_code": "business country",
    }
    required_client_fields = {
        "address_line1": "client street address",
        "postal_code": "client postal code",
        "city": "client city",
        "country_code": "client country",
    }
    for field, label in required_business_fields.items():
        if not business.get(field):
            missing.append(label)
    for field, label in required_client_fields.items():
        if not client.get(field):
            missing.append(label)
    jurisdiction = business.get("jurisdiction") or business.get("country_code")
    if jurisdiction == "DE":
        if not (business.get("tax_number") or business.get("vat_id")):
            missing.append("business tax number or VAT ID")
    elif not business.get("tax_number"):
        missing.append("business Hungarian tax number")

    if client.get("client_type") == "BUSINESS":
        if jurisdiction == "HU" and client.get("country_code") == "HU":
            if not client.get("tax_number"):
                missing.append("client Hungarian tax number")
        elif not (client.get("tax_number") or client.get("vat_id")):
            missing.append("client tax number or VAT ID")
    if invoice["total"] <= 0:
        missing.append("a positive invoice total")
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Complete the following before issuing: " + ", ".join(missing) + ".",
        )


def display_status(invoice: dict) -> str:
    if (
        invoice["status"] in ("ISSUED", "PARTIALLY_PAID")
        and invoice["balance_due"] > 0
        and invoice["due_date"] < date.today()
    ):
        return "OVERDUE"
    return invoice["status"]
