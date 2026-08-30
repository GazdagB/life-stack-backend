import json
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from psycopg.errors import ForeignKeyViolation, UniqueViolation
from psycopg.rows import dict_row

from app.database.db import get_connection
from app.services.invoice_service import calculate_invoice_items, display_status, format_invoice_number, money, validate_issue_readiness


def list_businesses(user_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                "SELECT * FROM businesses WHERE user_id = %s ORDER BY legal_name",
                (user_id,),
            ).fetchall()


def get_business(user_id: int, business_id: int, cur=None, for_update: bool = False):
    owns_cursor = cur is None
    conn = get_connection() if owns_cursor else None
    if owns_cursor:
        cur = conn.cursor(row_factory=dict_row)
    suffix = " FOR UPDATE" if for_update else ""
    business = cur.execute(
        f"SELECT * FROM businesses WHERE id = %s AND user_id = %s{suffix}",
        (business_id, user_id),
    ).fetchone()
    if owns_cursor:
        cur.close()
        conn.close()
    if business is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


def create_business(user_id: int, data):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                return cur.execute(
                    """
                    INSERT INTO businesses (
                        user_id, legal_name, jurisdiction, tax_number, vat_id,
                        registration_number, address_line1, address_line2, postal_code,
                        city, country_code, email, phone, website, bank_name, iban, bic,
                        default_currency, default_language, invoice_prefix,
                        default_payment_terms_days, tax_exemption_note,
                        invoice_accent_color, invoice_footer, invoice_template,
                        invoice_thank_you
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s
                    ) RETURNING *
                    """,
                    (user_id, *data.repository_values()),
                ).fetchone()
    except UniqueViolation as error:
        raise HTTPException(status_code=409, detail="A business with this legal name already exists") from error


def update_business(user_id: int, business_id: int, data):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            updated = cur.execute(
                """
                UPDATE businesses SET
                    legal_name=%s, jurisdiction=%s, tax_number=%s, vat_id=%s,
                    registration_number=%s, address_line1=%s, address_line2=%s,
                    postal_code=%s, city=%s, country_code=%s, email=%s, phone=%s,
                    website=%s, bank_name=%s, iban=%s, bic=%s, default_currency=%s,
                    default_language=%s, invoice_prefix=%s,
                    default_payment_terms_days=%s, tax_exemption_note=%s,
                    invoice_accent_color=%s, invoice_footer=%s,
                    invoice_template=%s, invoice_thank_you=%s,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND user_id=%s RETURNING *
                """,
                (*data.repository_values(), business_id, user_id),
            ).fetchone()
    if updated is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return updated


def delete_business(user_id: int, business_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            business = cur.execute(
                "SELECT id, legal_name FROM businesses WHERE id=%s AND user_id=%s FOR UPDATE",
                (business_id, user_id),
            ).fetchone()
            if business is None:
                raise HTTPException(status_code=404, detail="Business not found")
            invoice_count = cur.execute(
                "SELECT COUNT(*) AS count FROM invoices WHERE business_id=%s AND user_id=%s",
                (business_id, user_id),
            ).fetchone()["count"]
            if invoice_count:
                raise HTTPException(
                    status_code=409,
                    detail="Businesses with invoices cannot be deleted. Delete any drafts first; issued invoices must be preserved.",
                )
            cur.execute("DELETE FROM clients WHERE business_id=%s AND user_id=%s", (business_id, user_id))
            cur.execute("DELETE FROM businesses WHERE id=%s AND user_id=%s", (business_id, user_id))
    return {"message": "Business deleted", "id": business_id, "legal_name": business["legal_name"]}


def update_business_logo(user_id: int, business_id: int, content: bytes, content_type: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            get_business(user_id, business_id, cur)
            asset_id = cur.execute(
                """
                INSERT INTO business_brand_assets (user_id, business_id, logo_data, logo_content_type)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, business_id, content, content_type),
            ).fetchone()["id"]
            return cur.execute(
                """
                UPDATE businesses
                SET logo_asset_id=%s, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND user_id=%s
                RETURNING *
                """,
                (asset_id, business_id, user_id),
            ).fetchone()


def delete_business_logo(user_id: int, business_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            updated = cur.execute(
                """
                UPDATE businesses
                SET logo_asset_id=NULL, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND user_id=%s
                RETURNING *
                """,
                (business_id, user_id),
            ).fetchone()
    if updated is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return updated


def get_business_logo(user_id: int, business_id: int, asset_id: int | None = None):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            logo = cur.execute(
                """
                SELECT a.logo_data, a.logo_content_type
                FROM businesses b
                JOIN business_brand_assets a
                  ON a.id=COALESCE(%s, b.logo_asset_id)
                 AND a.business_id=b.id
                 AND a.user_id=b.user_id
                WHERE b.id=%s AND b.user_id=%s
                """,
                (asset_id, business_id, user_id),
            ).fetchone()
    return logo


def update_business_signature(user_id: int, business_id: int, content: bytes, content_type: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            get_business(user_id, business_id, cur)
            asset_id = cur.execute(
                """
                INSERT INTO business_signature_assets (
                    user_id, business_id, signature_data, signature_content_type
                ) VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, business_id, content, content_type),
            ).fetchone()["id"]
            return cur.execute(
                """
                UPDATE businesses
                SET signature_asset_id=%s, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND user_id=%s
                RETURNING *
                """,
                (asset_id, business_id, user_id),
            ).fetchone()


def delete_business_signature(user_id: int, business_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            updated = cur.execute(
                """
                UPDATE businesses
                SET signature_asset_id=NULL, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND user_id=%s
                RETURNING *
                """,
                (business_id, user_id),
            ).fetchone()
    if updated is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return updated


def get_business_signature(user_id: int, business_id: int, asset_id: int | None = None):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            signature = cur.execute(
                """
                SELECT a.signature_data, a.signature_content_type
                FROM businesses b
                JOIN business_signature_assets a
                  ON a.id=COALESCE(%s, b.signature_asset_id)
                 AND a.business_id=b.id
                 AND a.user_id=b.user_id
                WHERE b.id=%s AND b.user_id=%s
                """,
                (asset_id, business_id, user_id),
            ).fetchone()
    return signature


def list_clients(user_id: int, business_id: int | None = None, segment: str | None = None):
    query = "SELECT * FROM clients WHERE user_id = %s"
    params: list[object] = [user_id]
    if business_id is not None:
        query += " AND business_id = %s"
        params.append(business_id)
    if segment:
        query += " AND LOWER(segment) = LOWER(%s)"
        params.append(segment)
    query += " ORDER BY active DESC, name"
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(query, params).fetchall()


def get_client(user_id: int, client_id: int, cur=None):
    owns_cursor = cur is None
    conn = get_connection() if owns_cursor else None
    if owns_cursor:
        cur = conn.cursor(row_factory=dict_row)
    client = cur.execute(
        "SELECT * FROM clients WHERE id = %s AND user_id = %s",
        (client_id, user_id),
    ).fetchone()
    if owns_cursor:
        cur.close()
        conn.close()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def create_client(user_id: int, data):
    get_business(user_id, data.business_id)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return cur.execute(
                """
                INSERT INTO clients (
                    user_id, business_id, name, client_type, segment, contact_name,
                    email, phone, tax_number, vat_id, address_line1, address_line2,
                    postal_code, city, country_code, notes, active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, *data.repository_values()),
            ).fetchone()


def update_client(user_id: int, client_id: int, data):
    get_business(user_id, data.business_id)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            updated = cur.execute(
                """
                UPDATE clients SET
                    business_id=%s, name=%s, client_type=%s, segment=%s,
                    contact_name=%s, email=%s, phone=%s, tax_number=%s, vat_id=%s,
                    address_line1=%s, address_line2=%s, postal_code=%s, city=%s,
                    country_code=%s, notes=%s, active=%s, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND user_id=%s RETURNING *
                """,
                (*data.repository_values(), client_id, user_id),
            ).fetchone()
    if updated is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return updated


def delete_client(user_id: int, client_id: int):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                deleted = cur.execute(
                    "DELETE FROM clients WHERE id=%s AND user_id=%s RETURNING id",
                    (client_id, user_id),
                ).fetchone()
    except ForeignKeyViolation as error:
        raise HTTPException(status_code=409, detail="Clients with invoices cannot be deleted; mark the client inactive instead") from error
    if deleted is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted", "id": deleted["id"]}


def _insert_items(cur, invoice_id: int, items: list[dict]):
    cur.executemany(
        """
        INSERT INTO invoice_items (
            invoice_id, description, quantity, unit, unit_price, tax_rate,
            net_total, tax_total, gross_total, sort_order
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            (
                invoice_id, item["description"], item["quantity"], item["unit"],
                item["unit_price"], item["tax_rate"], item["net_total"],
                item["tax_total"], item["gross_total"], item["sort_order"],
            )
            for item in items
        ],
    )


def _decorate_invoice(invoice: dict):
    amount_paid = money(invoice.get("amount_paid", 0))
    balance_due = money(invoice["total"] - amount_paid)
    invoice["amount_paid"] = amount_paid
    invoice["balance_due"] = balance_due
    invoice["display_status"] = display_status(invoice)
    return invoice


def list_invoices(user_id: int, business_id: int | None = None, status: str | None = None):
    query = """
        SELECT i.*, b.legal_name AS business_name, b.jurisdiction,
               c.name AS client_name, c.segment,
               COALESCE(SUM(p.amount), 0) AS amount_paid
        FROM invoices i
        JOIN businesses b ON b.id = i.business_id
        JOIN clients c ON c.id = i.client_id
        LEFT JOIN invoice_payments p ON p.invoice_id = i.id
        WHERE i.user_id = %s
    """
    params: list[object] = [user_id]
    if business_id is not None:
        query += " AND i.business_id = %s"
        params.append(business_id)
    if status:
        query += " AND i.status = %s"
        params.append(status)
    query += " GROUP BY i.id, b.legal_name, b.jurisdiction, c.name, c.segment ORDER BY i.issue_date DESC, i.id DESC"
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return [_decorate_invoice(row) for row in cur.execute(query, params).fetchall()]


def _invoice_detail(cur, user_id: int, invoice_id: int):
    invoice = cur.execute(
        """
        SELECT i.*, b.legal_name AS business_name, b.jurisdiction,
               c.name AS client_name, c.segment,
               COALESCE((SELECT SUM(amount) FROM invoice_payments WHERE invoice_id=i.id), 0) AS amount_paid
        FROM invoices i
        JOIN businesses b ON b.id=i.business_id
        JOIN clients c ON c.id=i.client_id
        WHERE i.id=%s AND i.user_id=%s
        """,
        (invoice_id, user_id),
    ).fetchone()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice["items"] = cur.execute(
        "SELECT * FROM invoice_items WHERE invoice_id=%s ORDER BY sort_order, id",
        (invoice_id,),
    ).fetchall()
    invoice["payments"] = cur.execute(
        "SELECT * FROM invoice_payments WHERE invoice_id=%s ORDER BY payment_date DESC, id DESC",
        (invoice_id,),
    ).fetchall()
    invoice["business"] = get_business(user_id, invoice["business_id"], cur)
    invoice["client"] = get_client(user_id, invoice["client_id"], cur)
    return _decorate_invoice(invoice)


def get_invoice(user_id: int, invoice_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            return _invoice_detail(cur, user_id, invoice_id)


def _validate_parties(user_id: int, business_id: int, client_id: int, cur):
    business = get_business(user_id, business_id, cur)
    client = get_client(user_id, client_id, cur)
    if client["business_id"] != business_id:
        raise HTTPException(status_code=422, detail="The selected client belongs to a different business")
    return business, client


def create_invoice(user_id: int, data):
    calculated = calculate_invoice_items(data.items)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            _validate_parties(user_id, data.business_id, data.client_id, cur)
            invoice = cur.execute(
                """
                INSERT INTO invoices (
                    user_id, business_id, client_id, currency, language, issue_date,
                    service_date, due_date, notes, subtotal, tax_total, total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    user_id, data.business_id, data.client_id, data.currency,
                    data.language, data.issue_date, data.service_date, data.due_date,
                    data.notes, calculated["subtotal"], calculated["tax_total"], calculated["total"],
                ),
            ).fetchone()
            _insert_items(cur, invoice["id"], calculated["items"])
            return _invoice_detail(cur, user_id, invoice["id"])


def update_invoice(user_id: int, invoice_id: int, data):
    calculated = calculate_invoice_items(data.items)
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            current = cur.execute(
                "SELECT * FROM invoices WHERE id=%s AND user_id=%s FOR UPDATE",
                (invoice_id, user_id),
            ).fetchone()
            if current is None:
                raise HTTPException(status_code=404, detail="Invoice not found")
            if current["status"] != "DRAFT":
                raise HTTPException(status_code=409, detail="Issued invoices are immutable; create a credit note instead")
            _validate_parties(user_id, data.business_id, data.client_id, cur)
            cur.execute(
                """
                UPDATE invoices SET business_id=%s, client_id=%s, currency=%s,
                    language=%s, issue_date=%s, service_date=%s, due_date=%s,
                    notes=%s, subtotal=%s, tax_total=%s, total=%s,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s
                """,
                (
                    data.business_id, data.client_id, data.currency, data.language,
                    data.issue_date, data.service_date, data.due_date, data.notes,
                    calculated["subtotal"], calculated["tax_total"], calculated["total"], invoice_id,
                ),
            )
            cur.execute("DELETE FROM invoice_items WHERE invoice_id=%s", (invoice_id,))
            _insert_items(cur, invoice_id, calculated["items"])
            return _invoice_detail(cur, user_id, invoice_id)


def delete_invoice(user_id: int, invoice_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            deleted = cur.execute(
                "DELETE FROM invoices WHERE id=%s AND user_id=%s AND status='DRAFT' RETURNING id",
                (invoice_id, user_id),
            ).fetchone()
    if deleted is None:
        raise HTTPException(status_code=409, detail="Only draft invoices can be deleted")
    return {"message": "Draft invoice deleted", "id": deleted["id"]}


def _next_invoice_number(cur, business: dict, issue_date: date):
    year = issue_date.year
    next_number = business["next_invoice_number"] if business["invoice_number_year"] == year else 1
    invoice_number = format_invoice_number(business["invoice_prefix"], year, next_number)
    cur.execute(
        "UPDATE businesses SET next_invoice_number=%s, invoice_number_year=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
        (next_number + 1, year, business["id"]),
    )
    return invoice_number


def issue_invoice(user_id: int, invoice_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            invoice = cur.execute(
                "SELECT * FROM invoices WHERE id=%s AND user_id=%s FOR UPDATE",
                (invoice_id, user_id),
            ).fetchone()
            if invoice is None:
                raise HTTPException(status_code=404, detail="Invoice not found")
            if invoice["status"] != "DRAFT":
                raise HTTPException(status_code=409, detail="This invoice has already been issued")
            business = get_business(user_id, invoice["business_id"], cur, for_update=True)
            client = get_client(user_id, invoice["client_id"], cur)
            validate_issue_readiness(business, client, invoice)
            invoice_number = _next_invoice_number(cur, business, invoice["issue_date"])
            cur.execute(
                """
                UPDATE invoices SET invoice_number=%s, status='ISSUED', compliance_status='PENDING',
                    seller_snapshot=%s::jsonb, client_snapshot=%s::jsonb,
                    issued_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
                WHERE id=%s
                """,
                (invoice_number, json.dumps(business, default=str), json.dumps(client, default=str), invoice_id),
            )
            return _invoice_detail(cur, user_id, invoice_id)


def add_payment(user_id: int, invoice_id: int, data):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            invoice = cur.execute(
                "SELECT * FROM invoices WHERE id=%s AND user_id=%s FOR UPDATE",
                (invoice_id, user_id),
            ).fetchone()
            if invoice is None:
                raise HTTPException(status_code=404, detail="Invoice not found")
            if invoice["invoice_type"] != "INVOICE" or invoice["status"] not in ("ISSUED", "PARTIALLY_PAID"):
                raise HTTPException(status_code=409, detail="Payments can only be recorded against open issued invoices")
            paid = cur.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM invoice_payments WHERE invoice_id=%s",
                (invoice_id,),
            ).fetchone()["total"]
            remaining = money(invoice["total"] - paid)
            if data.amount > remaining:
                raise HTTPException(status_code=422, detail=f"Payment exceeds the outstanding balance of {remaining}")
            cur.execute(
                """
                INSERT INTO invoice_payments (invoice_id, amount, payment_date, payment_method, reference, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (invoice_id, data.amount, data.payment_date, data.payment_method, data.reference, data.notes),
            )
            new_paid = money(paid + data.amount)
            status = "PAID" if new_paid >= invoice["total"] else "PARTIALLY_PAID"
            cur.execute("UPDATE invoices SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s", (status, invoice_id))
            return _invoice_detail(cur, user_id, invoice_id)


def delete_payment(user_id: int, invoice_id: int, payment_id: int):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            invoice = cur.execute(
                "SELECT * FROM invoices WHERE id=%s AND user_id=%s FOR UPDATE",
                (invoice_id, user_id),
            ).fetchone()
            if invoice is None:
                raise HTTPException(status_code=404, detail="Invoice not found")
            deleted = cur.execute(
                "DELETE FROM invoice_payments WHERE id=%s AND invoice_id=%s RETURNING id",
                (payment_id, invoice_id),
            ).fetchone()
            if deleted is None:
                raise HTTPException(status_code=404, detail="Payment not found")
            paid = cur.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM invoice_payments WHERE invoice_id=%s",
                (invoice_id,),
            ).fetchone()["total"]
            status = "ISSUED" if paid == 0 else ("PAID" if paid >= invoice["total"] else "PARTIALLY_PAID")
            cur.execute("UPDATE invoices SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s", (status, invoice_id))
            return _invoice_detail(cur, user_id, invoice_id)


def create_credit_note(user_id: int, invoice_id: int, reason: str):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            original = cur.execute(
                "SELECT * FROM invoices WHERE id=%s AND user_id=%s FOR UPDATE",
                (invoice_id, user_id),
            ).fetchone()
            if original is None:
                raise HTTPException(status_code=404, detail="Invoice not found")
            if original["invoice_type"] != "INVOICE" or original["status"] in ("DRAFT", "CREDITED", "CANCELLED"):
                raise HTTPException(status_code=409, detail="This invoice cannot be credited")
            business = get_business(user_id, original["business_id"], cur, for_update=True)
            source_items = cur.execute(
                "SELECT * FROM invoice_items WHERE invoice_id=%s ORDER BY sort_order",
                (invoice_id,),
            ).fetchall()
            calculated = calculate_invoice_items(source_items, multiplier=-1)
            today = date.today()
            invoice_number = _next_invoice_number(cur, business, today)
            credit = cur.execute(
                """
                INSERT INTO invoices (
                    user_id, business_id, client_id, original_invoice_id, invoice_type,
                    invoice_number, status, compliance_status, currency, language,
                    issue_date, service_date, due_date, notes, correction_reason,
                    seller_snapshot, client_snapshot, subtotal, tax_total, total, issued_at
                ) VALUES (
                    %s, %s, %s, %s, 'CREDIT_NOTE', %s, 'ISSUED', 'PENDING', %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
                ) RETURNING id
                """,
                (
                    user_id, original["business_id"], original["client_id"], invoice_id,
                    invoice_number, original["currency"], original["language"], today,
                    original["service_date"], today, original["notes"], reason,
                    json.dumps(original["seller_snapshot"], default=str),
                    json.dumps(original["client_snapshot"], default=str),
                    calculated["subtotal"], calculated["tax_total"], calculated["total"],
                ),
            ).fetchone()
            _insert_items(cur, credit["id"], calculated["items"])
            cur.execute("UPDATE invoices SET status='CREDITED', updated_at=CURRENT_TIMESTAMP WHERE id=%s", (invoice_id,))
            return _invoice_detail(cur, user_id, credit["id"])
