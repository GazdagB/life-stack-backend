from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FONT_NAME = "TodoWorkVera"
BOLD_FONT_NAME = "TodoWorkVeraBold"


def _register_fonts() -> None:
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return
    font_dir = Path(reportlab.__file__).resolve().parent / "fonts"
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_dir / "Vera.ttf")))
    pdfmetrics.registerFont(TTFont(BOLD_FONT_NAME, str(font_dir / "VeraBd.ttf")))


def build_todo_work_pdf(title: str, content: str, include_signature: bool = False) -> bytes:
    _register_fonts()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=24 * mm,
        rightMargin=24 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title=title,
        author="Life Stack",
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "TodoWorkHeading", parent=styles["Heading1"], fontName=BOLD_FONT_NAME,
        fontSize=15, leading=19, spaceAfter=8 * mm,
    )
    body = ParagraphStyle(
        "TodoWorkBody", parent=styles["BodyText"], fontName=FONT_NAME,
        fontSize=10.5, leading=15, spaceAfter=3 * mm,
    )
    small = ParagraphStyle(
        "TodoWorkSmall", parent=body, fontSize=7.5, leading=9,
        textColor="#666666",
    )
    story = [Paragraph(escape(title), heading)]
    for block in content.replace("\r\n", "\n").split("\n\n"):
        rendered = escape(block.strip()).replace("\n", "<br/>")
        if rendered:
            story.append(Paragraph(rendered, body))
        else:
            story.append(Spacer(1, 3 * mm))
    if include_signature:
        signature = Table(
            [[""], [Paragraph("Signature / Unterschrift", small)]],
            colWidths=[65 * mm], rowHeights=[18 * mm, 6 * mm],
            hAlign="LEFT",
        )
        signature.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (0, 0), 0.7, "#555555"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.extend([Spacer(1, 10 * mm), KeepTogether(signature)])
    story.extend([
        Spacer(1, 10 * mm),
        Paragraph("AI-prepared draft — verify all details before use.", small),
    ])
    document.build(story)
    return buffer.getvalue()
