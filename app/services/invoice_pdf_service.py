from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_PATH = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
BOLD_FONT_PATH = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
FONT_NAME = "InvoiceArial"
BOLD_FONT_NAME = "InvoiceArialBold"
CLASSIC_FONT_PATH = Path("/System/Library/Fonts/Supplemental/Times New Roman.ttf")
CLASSIC_BOLD_FONT_PATH = Path("/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf")
CLASSIC_FONT_NAME = "InvoiceTimes"
CLASSIC_BOLD_FONT_NAME = "InvoiceTimesBold"

LABELS = {
    "DE": {
        "invoice": "RECHNUNG", "credit": "GUTSCHRIFT", "number": "Rechnungsnummer",
        "issue": "Ausstellungsdatum", "service": "Leistungsdatum", "due": "Fällig am",
        "bill_to": "Rechnung an", "description": "Leistung", "qty": "Menge", "unit": "Einheit",
        "unit_price": "Einzelpreis", "tax": "MwSt.", "net": "Netto", "subtotal": "Zwischensumme",
        "tax_total": "Steuer", "total": "Gesamt", "paid": "Bezahlt", "balance": "Offen",
        "tax_number": "Steuernummer", "vat_id": "USt-IdNr.", "bank": "Bankverbindung",
        "reference": "Bitte Rechnungsnummer als Verwendungszweck angeben.", "correction": "Korrekturgrund",
        "service_period": "Leistungszeitraum", "object": "Objekt", "payable": "Zahlbar bis zum",
        "payment_instruction": "Den Rechnungsbetrag bitte ich auf das unten angegebene Bankkonto zu überweisen.",
        "thank_you": "Vielen Dank für Ihren Auftrag!",
    },
    "HU": {
        "invoice": "SZÁMLA", "credit": "JÓVÁÍRÓ SZÁMLA", "number": "Számla sorszáma",
        "issue": "Kiállítás dátuma", "service": "Teljesítés dátuma", "due": "Fizetési határidő",
        "bill_to": "Vevő", "description": "Megnevezés", "qty": "Menny.", "unit": "Egység",
        "unit_price": "Egységár", "tax": "ÁFA", "net": "Nettó", "subtotal": "Nettó összesen",
        "tax_total": "ÁFA összesen", "total": "Bruttó összesen", "paid": "Fizetve", "balance": "Fizetendő",
        "tax_number": "Adószám", "vat_id": "Közösségi adószám", "bank": "Bankszámla",
        "reference": "Kérjük, az átutalás közleményében tüntesse fel a számla sorszámát.", "correction": "Módosítás oka",
        "service_period": "Teljesítési időszak", "object": "Helyszín", "payable": "Fizetési határidő",
        "payment_instruction": "Kérjük, a számla összegét az alábbi bankszámlára utalja át.",
        "thank_you": "Köszönjük a megrendelést!",
    },
    "EN": {
        "invoice": "INVOICE", "credit": "CREDIT NOTE", "number": "Invoice number",
        "issue": "Issue date", "service": "Service date", "due": "Due date",
        "bill_to": "Bill to", "description": "Description", "qty": "Qty", "unit": "Unit",
        "unit_price": "Unit price", "tax": "Tax", "net": "Net", "subtotal": "Subtotal",
        "tax_total": "Tax total", "total": "Total", "paid": "Paid", "balance": "Balance due",
        "tax_number": "Tax number", "vat_id": "VAT ID", "bank": "Bank details",
        "reference": "Please use the invoice number as the payment reference.", "correction": "Correction reason",
        "service_period": "Service period", "object": "Project", "payable": "Payable by",
        "payment_instruction": "Please transfer the invoice amount to the bank account shown below.",
        "thank_you": "Thank you for your business!",
    },
}

UNIT_LABELS = {
    "DE": {
        "service": "Leistung", "hour": "Stunde", "unit": "Einheit", "item": "Position",
        "piece": "Stück", "flat_rate": "Pauschal", "day": "Tag", "week": "Woche",
        "month": "Monat", "year": "Jahr", "kilometer": "Kilometer", "square_meter": "m²",
    },
    "HU": {
        "service": "szolgáltatás", "hour": "óra", "unit": "egység", "item": "tétel",
        "piece": "db", "flat_rate": "átalány", "day": "nap", "week": "hét",
        "month": "hónap", "year": "év", "kilometer": "kilométer", "square_meter": "m²",
    },
    "EN": {
        "service": "service", "hour": "hour", "unit": "unit", "item": "item",
        "piece": "piece", "flat_rate": "flat rate", "day": "day", "week": "week",
        "month": "month", "year": "year", "kilometer": "kilometer", "square_meter": "m²",
    },
}


def _unit_label(value: str, language: str) -> str:
    return UNIT_LABELS.get(language, UNIT_LABELS["EN"]).get(value, value)


def _register_fonts():
    registered = pdfmetrics.getRegisteredFontNames()
    if FONT_NAME not in registered:
        pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
        pdfmetrics.registerFont(TTFont(BOLD_FONT_NAME, str(BOLD_FONT_PATH)))
    if (
        CLASSIC_FONT_NAME not in registered
        and CLASSIC_FONT_PATH.exists()
        and CLASSIC_BOLD_FONT_PATH.exists()
    ):
        pdfmetrics.registerFont(TTFont(CLASSIC_FONT_NAME, str(CLASSIC_FONT_PATH)))
        pdfmetrics.registerFont(TTFont(CLASSIC_BOLD_FONT_NAME, str(CLASSIC_BOLD_FONT_PATH)))


def _address(entity: dict):
    lines = [entity.get("legal_name") or entity.get("name")]
    lines.extend(filter(None, [entity.get("address_line1"), entity.get("address_line2")]))
    city_line = " ".join(filter(None, [entity.get("postal_code"), entity.get("city")]))
    if city_line:
        lines.append(city_line)
    if entity.get("country_code"):
        lines.append(entity["country_code"])
    return "<br/>".join(escape(str(line)) for line in filter(None, lines))


def _amount(value, currency: str):
    precision = 0 if currency == "HUF" else 2
    return f"{value:,.{precision}f} {currency}".replace(",", " ")


def _tint(color, amount: float = 0.9):
    return colors.Color(
        color.red + (1 - color.red) * amount,
        color.green + (1 - color.green) * amount,
        color.blue + (1 - color.blue) * amount,
    )


def _asset_image(asset: dict | None, data_key: str, max_width, max_height):
    if not asset:
        return None
    source = BytesIO(bytes(asset[data_key]))
    image = Image(source)
    ratio = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * ratio
    image.drawHeight = image.imageHeight * ratio
    return image


def _logo(logo: dict | None):
    return _asset_image(logo, "logo_data", 42 * mm, 18 * mm)


def _signature(signature: dict | None):
    return _asset_image(signature, "signature_data", 52 * mm, 22 * mm)


def _classic_amount(value, currency: str, language: str):
    precision = 0 if currency == "HUF" else 2
    rendered = f"{value:,.{precision}f}"
    if language in ("DE", "HU"):
        rendered = rendered.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{rendered} {currency}"


def _classic_invoice_pdf(invoice: dict, logo: dict | None, signature: dict | None) -> bytes:
    seller = invoice.get("seller_snapshot") or invoice["business"]
    client = invoice.get("client_snapshot") or invoice["client"]
    language = invoice.get("language", "DE")
    labels = LABELS.get(language, LABELS["EN"])
    classic_font = CLASSIC_FONT_NAME if CLASSIC_FONT_NAME in pdfmetrics.getRegisteredFontNames() else FONT_NAME
    classic_bold = CLASSIC_BOLD_FONT_NAME if CLASSIC_BOLD_FONT_NAME in pdfmetrics.getRegisteredFontNames() else BOLD_FONT_NAME
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=22 * mm, leftMargin=24 * mm,
        topMargin=18 * mm, bottomMargin=16 * mm,
        title=invoice.get("invoice_number") or "Invoice", author=seller["legal_name"],
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("ClassicBody", parent=styles["BodyText"], fontName=classic_font, fontSize=10.5, leading=13)
    small = ParagraphStyle("ClassicSmall", parent=body, fontSize=8.5, leading=10.5)
    strong = ParagraphStyle("ClassicStrong", parent=body, fontName=classic_bold)
    heading = ParagraphStyle("ClassicHeading", parent=strong, fontSize=16, leading=19, alignment=TA_RIGHT)
    center = ParagraphStyle("ClassicCenter", parent=body, alignment=TA_CENTER)
    center_strong = ParagraphStyle("ClassicCenterStrong", parent=strong, alignment=TA_CENTER)
    right = ParagraphStyle("ClassicRight", parent=body, alignment=TA_RIGHT)
    story = []

    brand_logo = _asset_image(logo, "logo_data", 40 * mm, 27 * mm)
    identity = Paragraph(f"<b>{escape(str(seller['legal_name']))}</b>", ParagraphStyle("ClassicIdentity", parent=strong, fontSize=15, leading=17))
    brand_table = Table([[identity, brand_logo or ""]], colWidths=[105 * mm, 54 * mm])
    brand_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    story.extend([brand_table, Spacer(1, 7 * mm)])

    seller_location = " ".join(filter(None, [seller.get("postal_code"), seller.get("city")]))
    seller_line = ", ".join(filter(None, [seller_location, seller.get("address_line1")]))
    seller_contact = " | ".join(filter(None, [seller.get("phone"), seller.get("email"), seller.get("website")]))
    letterhead = Table([
        [Paragraph(f"<b>{escape(seller_line)}</b>", body), Paragraph(f"<b>{escape(seller_contact)}</b>", right)],
    ], colWidths=[82 * mm, 77 * mm])
    letterhead.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LINEBELOW", (0, 0), (-1, -1), 1, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.extend([letterhead, Spacer(1, 5 * mm), Paragraph(_address(client), body), Spacer(1, 7 * mm)])

    title = labels["credit"] if invoice["invoice_type"] == "CREDIT_NOTE" else labels["invoice"]
    story.extend([Paragraph(title.title(), heading), Spacer(1, 3 * mm)])
    number_date = Table([
        [Paragraph(f"<b>{labels['number']}: {escape(str(invoice['invoice_number']))}</b>", body), Paragraph(f"<b>{labels['issue']}: {invoice['issue_date'].strftime('%d.%m.%Y')}</b>", right)],
    ], colWidths=[83 * mm, 76 * mm])
    number_date.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1, colors.black), ("TOPPADDING", (0, 0), (-1, -1), 3)]))
    service_period = Table([
        [Paragraph(f"<b>{labels['service_period']}: {invoice['service_date'].strftime('%d.%m.%Y')}</b>", body)],
    ], colWidths=[159 * mm])
    service_period.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1, colors.black), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.extend([number_date, service_period, Spacer(1, 5 * mm)])

    object_parts = [client.get("address_line1")]
    object_parts.append(" ".join(filter(None, [client.get("postal_code"), client.get("city")])))
    object_text = ", ".join(filter(None, object_parts))
    rows = [[labels["description"], f"{labels['qty']}/{labels['unit']}", f"{labels['unit_price']}/{invoice['currency']}", f"{labels['net']}/{invoice['currency']}"]]
    if object_text:
        rows.append([Paragraph(f"<b>{labels['object']}:</b> {escape(object_text)}", small), "", "", ""])
    for item in invoice["items"]:
        rows.append([
            Paragraph(escape(str(item["description"])), body),
            f"{item['quantity']:g} {escape(_unit_label(str(item['unit']), language))}",
            _classic_amount(item["unit_price"], invoice["currency"], language),
            _classic_amount(item["net_total"], invoice["currency"], language),
        ])
    items_table = Table(rows, repeatRows=1, colWidths=[78 * mm, 28 * mm, 27 * mm, 26 * mm])
    items_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), classic_font), ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("SPAN", (0, 1), (-1, 1)) if object_text else ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, 0), 5), ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 6), ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
    ]))
    story.extend([items_table, Spacer(1, 5 * mm)])

    totals = Table([
        [Paragraph(f"<b>{labels['subtotal']}</b>", strong), Paragraph(f"<b>{_classic_amount(invoice['subtotal'], invoice['currency'], language)}</b>", right)],
        [Paragraph(labels["tax_total"], body), Paragraph(_classic_amount(invoice["tax_total"], invoice["currency"], language), right)],
        [Paragraph(f"<b>{labels['total']}</b>", strong), Paragraph(f"<b>{_classic_amount(invoice['total'], invoice['currency'], language)}</b>", right)],
    ], colWidths=[118 * mm, 41 * mm])
    totals.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.7, colors.black),
        ("LINEBELOW", (0, 2), (-1, 2), 1.2, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.extend([totals, Spacer(1, 6 * mm)])
    story.append(Paragraph(f"{labels['payable']}: {invoice['due_date'].strftime('%d.%m.%Y')}", body))
    story.extend([Spacer(1, 4 * mm), Paragraph(labels["payment_instruction"], center), Spacer(1, 10 * mm)])
    thank_you = seller.get("invoice_thank_you") or labels["thank_you"]
    story.append(Paragraph(escape(str(thank_you)), ParagraphStyle("ClassicThanks", parent=center, fontSize=12, leading=15)))
    signature_image = _signature(signature)
    if signature_image:
        signature_table = Table([[signature_image]], colWidths=[159 * mm])
        signature_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 4)]))
        story.append(signature_table)
    else:
        story.append(Spacer(1, 9 * mm))

    tax_identity = " | ".join(filter(None, [
        f"{labels['tax_number']}: {seller['tax_number']}" if seller.get("tax_number") else None,
        f"{labels['vat_id']}: {seller['vat_id']}" if seller.get("vat_id") else None,
        seller.get("phone"),
    ]))
    if tax_identity:
        story.append(Paragraph(escape(tax_identity), center_strong))
    bank_lines = [seller.get("bank_name"), seller.get("iban"), seller.get("bic")]
    if any(bank_lines):
        story.extend([Spacer(1, 3 * mm), Paragraph(f"<b>{labels['bank']}</b>", center_strong), Paragraph(escape(" | ".join(filter(None, bank_lines))), center_strong)])
    if seller.get("invoice_footer"):
        story.extend([Spacer(1, 3 * mm), Paragraph(escape(str(seller["invoice_footer"])).replace("\n", "<br/>"), small)])

    def page_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(classic_font, 7)
        canvas.drawRightString(188 * mm, 7 * mm, f"{invoice['invoice_number']} | {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return buffer.getvalue()


def build_invoice_pdf(invoice: dict, logo: dict | None = None, signature: dict | None = None) -> bytes:
    _register_fonts()
    seller = invoice.get("seller_snapshot") or invoice["business"]
    if seller.get("invoice_template") == "CLASSIC":
        return _classic_invoice_pdf(invoice, logo, signature)
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=21 * mm,
        title=invoice.get("invoice_number") or "Invoice",
        author=(invoice.get("seller_snapshot") or invoice["business"])["legal_name"],
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("InvoiceBody", parent=styles["BodyText"], fontName=FONT_NAME, fontSize=9.5, leading=13)
    small = ParagraphStyle("InvoiceSmall", parent=body, fontSize=8, leading=11, textColor=colors.HexColor("#64748b"))
    try:
        accent = colors.HexColor(seller.get("invoice_accent_color") or "#2563EB")
    except ValueError:
        accent = colors.HexColor("#2563EB")
    accent_tint = _tint(accent)
    heading = ParagraphStyle("InvoiceHeading", parent=styles["Title"], fontName=BOLD_FONT_NAME, fontSize=24, leading=28, textColor=accent, alignment=TA_RIGHT)
    strong = ParagraphStyle("InvoiceStrong", parent=body, fontName=BOLD_FONT_NAME)
    right = ParagraphStyle("InvoiceRight", parent=body, alignment=TA_RIGHT)
    right_strong = ParagraphStyle("InvoiceRightStrong", parent=strong, alignment=TA_RIGHT, fontSize=11)

    language = invoice.get("language", "EN")
    labels = LABELS.get(language, LABELS["EN"])
    client = invoice.get("client_snapshot") or invoice["client"]
    title = labels["credit"] if invoice["invoice_type"] == "CREDIT_NOTE" else labels["invoice"]
    story = []

    seller_details = _address(seller)
    if seller.get("tax_number"):
        seller_details += f"<br/>{labels['tax_number']}: {escape(str(seller['tax_number']))}"
    if seller.get("vat_id"):
        seller_details += f"<br/>{labels['vat_id']}: {escape(str(seller['vat_id']))}"
    contact_details = " | ".join(filter(None, [seller.get("website"), seller.get("email"), seller.get("phone")]))
    if contact_details:
        seller_details += f"<br/>{escape(contact_details)}"
    brand = _logo(logo) or Paragraph(escape(seller["legal_name"]), ParagraphStyle("Brand", parent=heading, alignment=0, fontSize=17))
    header = Table([
        [brand, Paragraph(title, heading)],
        [Paragraph(seller_details, small), Paragraph(f"<b>{labels['number']}</b><br/>{invoice['invoice_number']}", right)],
    ], colWidths=[95 * mm, 63 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 1), (-1, 1), 1.2, accent), ("BOTTOMPADDING", (0, 1), (-1, 1), 8)]))
    story.extend([header, Spacer(1, 10 * mm)])

    client_details = _address(client)
    if client.get("tax_number"):
        client_details += f"<br/>{labels['tax_number']}: {escape(str(client['tax_number']))}"
    if client.get("vat_id"):
        client_details += f"<br/>{labels['vat_id']}: {escape(str(client['vat_id']))}"
    meta = Table([
        [Paragraph(labels["bill_to"], strong), Paragraph(labels["issue"], small), Paragraph(invoice["issue_date"].strftime("%Y-%m-%d"), right)],
        [Paragraph(client_details, body), Paragraph(labels["service"], small), Paragraph(invoice["service_date"].strftime("%Y-%m-%d"), right)],
        ["", Paragraph(labels["due"], small), Paragraph(invoice["due_date"].strftime("%Y-%m-%d"), right)],
    ], colWidths=[94 * mm, 34 * mm, 30 * mm])
    meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("SPAN", (0, 0), (0, 0)), ("SPAN", (0, 1), (0, 2)), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.extend([meta, Spacer(1, 9 * mm)])

    rows = [[labels["description"], labels["qty"], labels["unit"], labels["unit_price"], labels["tax"], labels["net"]]]
    for item in invoice["items"]:
        rows.append([
            Paragraph(escape(str(item["description"])), body), f"{item['quantity']:g}", escape(_unit_label(str(item["unit"]), language)),
            _amount(item["unit_price"], invoice["currency"]), f"{item['tax_rate']:g}%",
            _amount(item["net_total"], invoice["currency"]),
        ])
    items_table = Table(rows, repeatRows=1, colWidths=[64 * mm, 15 * mm, 18 * mm, 25 * mm, 14 * mm, 28 * mm])
    items_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), BOLD_FONT_NAME), ("FONTNAME", (0, 1), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("BACKGROUND", (0, 0), (-1, 0), accent_tint),
        ("TEXTCOLOR", (0, 0), (-1, 0), accent), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([items_table, Spacer(1, 6 * mm)])

    totals = [
        [labels["subtotal"], _amount(invoice["subtotal"], invoice["currency"])],
        [labels["tax_total"], _amount(invoice["tax_total"], invoice["currency"])],
        [labels["total"], _amount(invoice["total"], invoice["currency"])],
    ]
    if invoice.get("amount_paid", 0) > 0:
        totals.extend([
            [labels["paid"], _amount(invoice["amount_paid"], invoice["currency"])],
            [labels["balance"], _amount(invoice["balance_due"], invoice["currency"])],
        ])
    totals_table = Table(totals, colWidths=[42 * mm, 38 * mm], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (0, 2), (-1, 2), 1.1, accent),
        ("FONTNAME", (0, 2), (-1, 2), BOLD_FONT_NAME), ("FONTSIZE", (0, 2), (-1, 2), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([totals_table, Spacer(1, 9 * mm)])

    if invoice.get("correction_reason"):
        story.extend([Paragraph(f"<b>{labels['correction']}:</b> {escape(str(invoice['correction_reason']))}", body), Spacer(1, 4 * mm)])
    if invoice.get("notes"):
        story.extend([Paragraph(escape(str(invoice["notes"])).replace("\n", "<br/>"), body), Spacer(1, 4 * mm)])
    bank_parts = [seller.get("bank_name"), seller.get("iban"), seller.get("bic")]
    if any(bank_parts):
        story.append(Paragraph(f"<b>{labels['bank']}:</b> " + " | ".join(filter(None, bank_parts)), body))
        story.append(Paragraph(labels["reference"], small))
    if seller.get("tax_exemption_note"):
        story.extend([Spacer(1, 3 * mm), Paragraph(escape(str(seller["tax_exemption_note"])), small)])
    signature_image = _signature(signature)
    if seller.get("invoice_thank_you") or signature_image:
        modern_center = ParagraphStyle("ModernSignature", parent=body, alignment=TA_CENTER)
        story.extend([Spacer(1, 6 * mm), Paragraph(escape(str(seller.get("invoice_thank_you") or labels["thank_you"])), modern_center)])
        if signature_image:
            signature_table = Table([[signature_image]], colWidths=[158 * mm])
            signature_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 4)]))
            story.append(signature_table)
    if seller.get("invoice_footer"):
        footer_box = Table([[Paragraph(escape(str(seller["invoice_footer"])).replace("\n", "<br/>"), small)]], colWidths=[158 * mm])
        footer_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), accent_tint),
            ("BOX", (0, 0), (-1, -1), 0.7, accent),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.extend([Spacer(1, 5 * mm), footer_box])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(accent)
        canvas.line(18 * mm, 13 * mm, 192 * mm, 13 * mm)
        canvas.setFont(FONT_NAME, 7)
        canvas.setFillColor(colors.HexColor("#64748b"))
        footer_identity = " | ".join(filter(None, [seller["legal_name"], seller.get("website"), seller.get("email")]))
        canvas.drawString(18 * mm, 8.5 * mm, footer_identity[:95])
        canvas.drawRightString(192 * mm, 8.5 * mm, f"{invoice['invoice_number']}  |  {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
