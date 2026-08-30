from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator, model_validator

from app.repositories.invoice_repository import (
    add_payment,
    create_business,
    create_client,
    create_credit_note,
    create_invoice,
    delete_client,
    delete_invoice,
    delete_payment,
    get_invoice,
    issue_invoice,
    list_businesses,
    list_clients,
    list_invoices,
    update_business,
    update_client,
    update_invoice,
    update_business_logo,
    delete_business_logo,
    delete_business,
    get_business_logo,
    get_business_signature,
    update_business_signature,
    delete_business_signature,
)
from app.services.branding_service import MAX_LOGO_BYTES, MAX_SIGNATURE_BYTES, validate_logo, validate_signature
from app.services.auth_service import get_current_user_id
from app.services.invoice_pdf_service import build_invoice_pdf

router = APIRouter(tags=["business-invoicing"])


def optional_text(value: str | None):
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class BusinessInput(BaseModel):
    legal_name: str = Field(min_length=1, max_length=200)
    jurisdiction: Literal["DE", "HU"]
    tax_number: str | None = Field(default=None, max_length=60)
    vat_id: str | None = Field(default=None, max_length=40)
    registration_number: str | None = Field(default=None, max_length=80)
    address_line1: str | None = Field(default=None, max_length=200)
    address_line2: str | None = Field(default=None, max_length=200)
    postal_code: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=120)
    country_code: str = Field(min_length=2, max_length=2)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=254)
    bank_name: str | None = Field(default=None, max_length=120)
    iban: str | None = Field(default=None, max_length=50)
    bic: str | None = Field(default=None, max_length=20)
    default_currency: Literal["EUR", "HUF"]
    default_language: Literal["DE", "HU", "EN"]
    invoice_prefix: str = Field(default="", max_length=20, pattern=r"^[A-Za-z0-9-]*$")
    default_payment_terms_days: int = Field(default=14, ge=0, le=365)
    tax_exemption_note: str | None = Field(default=None, max_length=300)
    invoice_accent_color: str = Field(default="#2563EB", pattern=r"^#[0-9A-Fa-f]{6}$")
    invoice_footer: str | None = Field(default=None, max_length=500)
    invoice_template: Literal["MODERN", "CLASSIC"] = "MODERN"
    invoice_thank_you: str | None = Field(default=None, max_length=300)

    @field_validator("legal_name", "country_code", mode="after")
    @classmethod
    def normalize_required(cls, value: str):
        return value.strip().upper() if len(value.strip()) <= 3 else value.strip()

    @field_validator("invoice_prefix", mode="after")
    @classmethod
    def normalize_invoice_prefix(cls, value: str):
        return value.strip().upper()

    @field_validator(
        "tax_number", "vat_id", "registration_number", "address_line1",
        "address_line2", "postal_code", "city", "email", "phone",
        "website", "bank_name", "iban", "bic", "tax_exemption_note",
        "invoice_footer", "invoice_thank_you", mode="after",
    )
    @classmethod
    def normalize_optional(cls, value: str | None):
        return optional_text(value)

    def repository_values(self):
        return (
            self.legal_name, self.jurisdiction, self.tax_number, self.vat_id,
            self.registration_number, self.address_line1, self.address_line2,
            self.postal_code, self.city, self.country_code.upper(), self.email,
            self.phone, self.website, self.bank_name, self.iban, self.bic, self.default_currency,
            self.default_language, self.invoice_prefix,
            self.default_payment_terms_days, self.tax_exemption_note,
            self.invoice_accent_color.upper(), self.invoice_footer,
            self.invoice_template, self.invoice_thank_you,
        )


class ClientInput(BaseModel):
    business_id: int
    name: str = Field(min_length=1, max_length=200)
    client_type: Literal["BUSINESS", "PRIVATE"] = "BUSINESS"
    segment: str = Field(min_length=1, max_length=80)
    contact_name: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=50)
    tax_number: str | None = Field(default=None, max_length=60)
    vat_id: str | None = Field(default=None, max_length=40)
    address_line1: str | None = Field(default=None, max_length=200)
    address_line2: str | None = Field(default=None, max_length=200)
    postal_code: str | None = Field(default=None, max_length=20)
    city: str | None = Field(default=None, max_length=120)
    country_code: str = Field(min_length=2, max_length=2)
    notes: str | None = Field(default=None, max_length=1000)
    active: bool = True

    def repository_values(self):
        return (
            self.business_id, self.name.strip(), self.client_type, self.segment.strip(),
            optional_text(self.contact_name), optional_text(self.email), optional_text(self.phone),
            optional_text(self.tax_number), optional_text(self.vat_id), optional_text(self.address_line1),
            optional_text(self.address_line2), optional_text(self.postal_code), optional_text(self.city),
            self.country_code.strip().upper(), optional_text(self.notes), self.active,
        )


class InvoiceItemInput(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0, decimal_places=3)
    unit: str = Field(default="service", min_length=1, max_length=30)
    unit_price: Decimal = Field(ge=0, decimal_places=2)
    tax_rate: Decimal = Field(ge=0, le=100, decimal_places=2)


class InvoiceInput(BaseModel):
    business_id: int
    client_id: int
    currency: Literal["EUR", "HUF"]
    language: Literal["DE", "HU", "EN"]
    issue_date: date
    service_date: date
    due_date: date
    notes: str | None = Field(default=None, max_length=2000)
    items: list[InvoiceItemInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.due_date < self.issue_date:
            raise ValueError("Due date cannot be before the issue date")
        self.notes = optional_text(self.notes)
        return self


class PaymentInput(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    payment_date: date
    payment_method: Literal["BANK_TRANSFER", "CASH", "CARD", "OTHER"] = "BANK_TRANSFER"
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class CreditNoteInput(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.get("/businesses/")
def get_businesses(current_user_id: int = Depends(get_current_user_id)):
    return list_businesses(current_user_id)


@router.post("/businesses/", status_code=201)
def add_business(data: BusinessInput, current_user_id: int = Depends(get_current_user_id)):
    return create_business(current_user_id, data)


@router.put("/businesses/{business_id}")
def edit_business(business_id: int, data: BusinessInput, current_user_id: int = Depends(get_current_user_id)):
    return update_business(current_user_id, business_id, data)


@router.delete("/businesses/{business_id}")
def remove_business(business_id: int, current_user_id: int = Depends(get_current_user_id)):
    return delete_business(current_user_id, business_id)


@router.post("/businesses/{business_id}/logo")
async def upload_business_logo(
    business_id: int,
    logo: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user_id),
):
    content = await logo.read(MAX_LOGO_BYTES + 1)
    content_type = validate_logo(content)
    return update_business_logo(current_user_id, business_id, content, content_type)


@router.get("/businesses/{business_id}/logo")
def read_business_logo(business_id: int, current_user_id: int = Depends(get_current_user_id)):
    logo = get_business_logo(current_user_id, business_id)
    if logo is None:
        raise HTTPException(status_code=404, detail="Business logo not found")
    return Response(
        content=logo["logo_data"],
        media_type=logo["logo_content_type"],
        headers={"Cache-Control": "private, no-cache"},
    )


@router.delete("/businesses/{business_id}/logo")
def remove_business_logo(business_id: int, current_user_id: int = Depends(get_current_user_id)):
    return delete_business_logo(current_user_id, business_id)


@router.post("/businesses/{business_id}/signature")
async def upload_business_signature(
    business_id: int,
    signature: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user_id),
):
    content = await signature.read(MAX_SIGNATURE_BYTES + 1)
    content_type = validate_signature(content)
    return update_business_signature(current_user_id, business_id, content, content_type)


@router.get("/businesses/{business_id}/signature")
def read_business_signature(business_id: int, current_user_id: int = Depends(get_current_user_id)):
    signature = get_business_signature(current_user_id, business_id)
    if signature is None:
        raise HTTPException(status_code=404, detail="Business signature not found")
    return Response(
        content=signature["signature_data"],
        media_type=signature["signature_content_type"],
        headers={"Cache-Control": "private, no-cache"},
    )


@router.delete("/businesses/{business_id}/signature")
def remove_business_signature(business_id: int, current_user_id: int = Depends(get_current_user_id)):
    return delete_business_signature(current_user_id, business_id)


@router.get("/clients/")
def get_clients(
    business_id: int | None = None,
    segment: str | None = Query(default=None, max_length=80),
    current_user_id: int = Depends(get_current_user_id),
):
    return list_clients(current_user_id, business_id, segment)


@router.post("/clients/", status_code=201)
def add_client(data: ClientInput, current_user_id: int = Depends(get_current_user_id)):
    return create_client(current_user_id, data)


@router.put("/clients/{client_id}")
def edit_client(client_id: int, data: ClientInput, current_user_id: int = Depends(get_current_user_id)):
    return update_client(current_user_id, client_id, data)


@router.delete("/clients/{client_id}")
def remove_client(client_id: int, current_user_id: int = Depends(get_current_user_id)):
    return delete_client(current_user_id, client_id)


@router.get("/invoices/")
def get_invoices(
    business_id: int | None = None,
    status: Literal["DRAFT", "ISSUED", "PARTIALLY_PAID", "PAID", "CREDITED", "CANCELLED"] | None = None,
    current_user_id: int = Depends(get_current_user_id),
):
    return list_invoices(current_user_id, business_id, status)


@router.post("/invoices/", status_code=201)
def add_invoice(data: InvoiceInput, current_user_id: int = Depends(get_current_user_id)):
    return create_invoice(current_user_id, data)


@router.get("/invoices/{invoice_id}")
def invoice_detail(invoice_id: int, current_user_id: int = Depends(get_current_user_id)):
    return get_invoice(current_user_id, invoice_id)


@router.put("/invoices/{invoice_id}")
def edit_invoice(invoice_id: int, data: InvoiceInput, current_user_id: int = Depends(get_current_user_id)):
    return update_invoice(current_user_id, invoice_id, data)


@router.delete("/invoices/{invoice_id}")
def remove_invoice(invoice_id: int, current_user_id: int = Depends(get_current_user_id)):
    return delete_invoice(current_user_id, invoice_id)


@router.post("/invoices/{invoice_id}/issue")
def issue(invoice_id: int, current_user_id: int = Depends(get_current_user_id)):
    return issue_invoice(current_user_id, invoice_id)


@router.post("/invoices/{invoice_id}/payments", status_code=201)
def record_payment(invoice_id: int, data: PaymentInput, current_user_id: int = Depends(get_current_user_id)):
    return add_payment(current_user_id, invoice_id, data)


@router.delete("/invoices/{invoice_id}/payments/{payment_id}")
def remove_payment(invoice_id: int, payment_id: int, current_user_id: int = Depends(get_current_user_id)):
    return delete_payment(current_user_id, invoice_id, payment_id)


@router.post("/invoices/{invoice_id}/credit", status_code=201)
def credit(invoice_id: int, data: CreditNoteInput, current_user_id: int = Depends(get_current_user_id)):
    return create_credit_note(current_user_id, invoice_id, data.reason.strip())


@router.get("/invoices/{invoice_id}/pdf")
def download_pdf(invoice_id: int, current_user_id: int = Depends(get_current_user_id)):
    invoice = get_invoice(current_user_id, invoice_id)
    if invoice["status"] == "DRAFT":
        raise HTTPException(status_code=409, detail="Issue the invoice before downloading its PDF")
    snapshot = invoice.get("seller_snapshot") or {}
    logo_asset_id = snapshot.get("logo_asset_id")
    signature_asset_id = snapshot.get("signature_asset_id")
    logo = get_business_logo(current_user_id, invoice["business_id"], logo_asset_id) if logo_asset_id else None
    signature = get_business_signature(current_user_id, invoice["business_id"], signature_asset_id) if signature_asset_id else None
    pdf = build_invoice_pdf(invoice, logo, signature)
    safe_number = (invoice["invoice_number"] or "invoice").replace("/", "-")
    filename = f"{safe_number}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
