import unittest
from datetime import date
from decimal import Decimal
from io import BytesIO

from fastapi import HTTPException
from PIL import Image as PillowImage

from app.services.invoice_pdf_service import build_invoice_pdf
from app.services.invoice_service import calculate_invoice_items, display_status, format_invoice_number, validate_issue_readiness


class InvoiceServiceTests(unittest.TestCase):
    def test_calculates_money_with_line_level_tax_rounding(self):
        result = calculate_invoice_items([
            {"description": "IT support", "quantity": Decimal("2.5"), "unit": "hour", "unit_price": Decimal("80"), "tax_rate": Decimal("27")},
            {"description": "Hosting", "quantity": Decimal("1"), "unit": "month", "unit_price": Decimal("10"), "tax_rate": Decimal("27")},
        ])

        self.assertEqual(result["subtotal"], Decimal("210.00"))
        self.assertEqual(result["tax_total"], Decimal("56.70"))
        self.assertEqual(result["total"], Decimal("266.70"))

    def test_issue_requires_legal_party_details(self):
        with self.assertRaises(HTTPException) as raised:
            validate_issue_readiness(
                {"invoice_prefix": "GS", "country_code": "HU"},
                {"client_type": "BUSINESS", "country_code": "HU"},
                {"total": Decimal("100.00")},
            )
        self.assertEqual(raised.exception.status_code, 422)
        self.assertIn("business Hungarian tax number", raised.exception.detail)
        self.assertIn("client Hungarian tax number", raised.exception.detail)

    def test_german_business_can_issue_with_vat_id_instead_of_tax_number(self):
        validate_issue_readiness(
            {
                "jurisdiction": "DE",
                "vat_id": "DE123456789",
                "address_line1": "Musterstraße 1",
                "postal_code": "10115",
                "city": "Berlin",
                "country_code": "DE",
                "invoice_prefix": "",
            },
            {
                "client_type": "BUSINESS",
                "vat_id": "DE987654321",
                "address_line1": "Kundenweg 2",
                "postal_code": "10117",
                "city": "Berlin",
                "country_code": "DE",
            },
            {"total": Decimal("100.00")},
        )

    def test_formats_invoice_number_without_prefix_as_sequence_and_year(self):
        self.assertEqual(format_invoice_number("", 2026, 49), "049/2026")

    def test_preserves_legacy_prefixed_invoice_number_format(self):
        self.assertEqual(format_invoice_number("gs", 2026, 49), "GS-2026-0049")

    def test_hungarian_vat_id_does_not_replace_supplier_tax_number(self):
        with self.assertRaises(HTTPException) as raised:
            validate_issue_readiness(
                {
                    "jurisdiction": "HU",
                    "vat_id": "HU12345678",
                    "address_line1": "Fő utca 1.",
                    "postal_code": "1011",
                    "city": "Budapest",
                    "country_code": "HU",
                    "invoice_prefix": "GS",
                },
                {
                    "client_type": "PRIVATE",
                    "address_line1": "Minta utca 2.",
                    "postal_code": "1012",
                    "city": "Budapest",
                    "country_code": "HU",
                },
                {"total": Decimal("100.00")},
            )

        self.assertIn("business Hungarian tax number", raised.exception.detail)

    def test_open_invoice_becomes_overdue_after_due_date(self):
        invoice = {
            "status": "ISSUED",
            "balance_due": Decimal("10.00"),
            "due_date": date(2020, 1, 1),
        }
        self.assertEqual(display_status(invoice), "OVERDUE")

    def test_builds_localized_invoice_pdf(self):
        party = {
            "legal_name": "Gazd Systems",
            "name": "Teszt Ügyfél Kft.",
            "address_line1": "Fő utca 1.",
            "postal_code": "1011",
            "city": "Budapest",
            "country_code": "HU",
            "tax_number": "12345678-2-41",
            "vat_id": None,
            "bank_name": "Test Bank",
            "iban": "HU00 0000 0000 0000 0000 0000 0000",
            "bic": "TESTHUHB",
            "tax_exemption_note": None,
            "website": "https://gazd.example",
            "invoice_accent_color": "#0F766E",
            "invoice_footer": "Reliable systems, clearly delivered.",
        }
        invoice = {
            "invoice_number": "GS-2026-0001",
            "invoice_type": "INVOICE",
            "language": "HU",
            "currency": "HUF",
            "issue_date": date(2026, 8, 28),
            "service_date": date(2026, 8, 28),
            "due_date": date(2026, 9, 5),
            "seller_snapshot": party,
            "client_snapshot": {**party, "legal_name": None, "name": "Teszt Ügyfél Kft."},
            "business": party,
            "client": party,
            "items": [{
                "description": "Rendszerüzemeltetés",
                "quantity": Decimal("1"),
                "unit": "hó",
                "unit_price": Decimal("100000"),
                "tax_rate": Decimal("27"),
                "net_total": Decimal("100000"),
            }],
            "subtotal": Decimal("100000"),
            "tax_total": Decimal("27000"),
            "total": Decimal("127000"),
            "amount_paid": Decimal("0"),
            "balance_due": Decimal("127000"),
            "correction_reason": None,
            "notes": "Köszönjük a megrendelést.",
        }

        logo_buffer = BytesIO()
        PillowImage.new("RGB", (240, 80), "#0F766E").save(logo_buffer, format="PNG")
        logo = {"logo_data": logo_buffer.getvalue(), "logo_content_type": "image/png"}
        pdf = build_invoice_pdf(invoice, logo)

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 10_000)

        signature_buffer = BytesIO()
        PillowImage.new("RGBA", (360, 100), (0, 0, 0, 0)).save(signature_buffer, format="PNG")
        classic_invoice = {
            **invoice,
            "seller_snapshot": {
                **party,
                "invoice_template": "CLASSIC",
                "invoice_thank_you": "Köszönjük a megrendelést!",
            },
        }
        classic_pdf = build_invoice_pdf(
            classic_invoice,
            logo,
            {"signature_data": signature_buffer.getvalue(), "signature_content_type": "image/png"},
        )

        self.assertTrue(classic_pdf.startswith(b"%PDF"))
        self.assertGreater(len(classic_pdf), 10_000)


if __name__ == "__main__":
    unittest.main()
