import shutil
import subprocess
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape

from services.validator import calculate_totals


NAVY = colors.HexColor("#19024A")
TEAL = colors.HexColor("#197B78")
PALE = colors.HexColor("#E7F3F2")
INK = colors.HexColor("#298746")


def _register_fonts():
   
    font_folder = Path(r"C:\Windows\Fonts")
    regular_path = font_folder / "arial.ttf"
    bold_path = font_folder / "arialbd.ttf"
    if regular_path.exists() and bold_path.exists():
        if "ProjectSans" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("ProjectSans", str(regular_path)))
            pdfmetrics.registerFont(TTFont("ProjectSans-Bold", str(bold_path)))
        return "ProjectSans", "ProjectSans-Bold"
    return "Helvetica", "Helvetica-Bold"


def find_libreoffice():
    for command in ("soffice", "libreoffice"):
        found = shutil.which(command)
        if found:
            return found
    candidates = (
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    )
    return next((str(path) for path in candidates if path.exists()), None)


def _write_pdf(rows, pdf_path):
    """helps to Create a matching report when threre is no LibreOffice."""
    regular_font, bold_font = _register_fonts()
    page_size = landscape(letter)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontName=bold_font,
        fontSize=19, leading=23, textColor=colors.white, alignment=TA_LEFT,
    )
    body_style = ParagraphStyle(
        "ReportBody", parent=styles["BodyText"], fontName=regular_font,
        fontSize=8, leading=10, textColor=INK,
    )
    story = []
    title_bar = Table([[Paragraph("Project WORK SUMMARY", title_style)]], colWidths=[10 * inch])
    title_bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([title_bar, Spacer(1, 8)])
    story.append(Spacer(1, 14))
    # story.append(Paragraph("ACTIVITY", ParagraphStyle(
    #     "SectionHeading", parent=styles["Heading2"], textColor=TEAL,
    #     fontName=bold_font, fontSize=10, leading=13,
    # )))

    data = [["Date", "Client", "Category", "Description", "Hours", "Rate", "Amount"]]
    for row in rows:
        description = Paragraph(escape(str(row[3])), body_style)
        client = Paragraph(escape(str(row[1])), body_style)
        category = Paragraph(escape(str(row[2])), body_style)
        data.append([
            str(row[0]), client, category, description,
            f"{float(row[4]):,.2f}", f"₹{float(row[5]):,.2f}",
            f"₹{float(row[4]) * float(row[5]):,.2f}",
        ])
    total_hours, total_amount, by_client = calculate_totals(rows)
    data.append(["", "", "", "TOTAL", f"{total_hours:,.2f}", "", f"₹{total_amount:,.2f}"])
    table = Table(data, colWidths=[0.85*inch, 1.45*inch, 1.1*inch, 3.2*inch, 0.7*inch, 0.85*inch, 0.95*inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), bold_font),
        ("FONTNAME", (0, 1), (-1, -1), regular_font),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, PALE]),
        ("LINEBELOW", (3, -1), (-1, -1), 0.8, TEAL),
        ("FONTNAME", (3, -1), (-1, -1), bold_font),
        ("TEXTCOLOR", (3, -1), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -2), 0.25, colors.HexColor("#DCE5E4")),
    ]))
    story.extend([table, Spacer(1, 18)])
    story.append(Paragraph("CLIENT TOTALS", ParagraphStyle(
        "ClientHeading", parent=styles["Heading2"], textColor=TEAL,
        fontName=bold_font, fontSize=10, leading=13,
    )))
    summary_data = [["Client", "Amount"]]
    summary_data.extend([[name, f"₹{amount:,.2f}"] for name, amount in sorted(by_client.items())])
    summary = Table(summary_data, colWidths=[3.0*inch, 1.5*inch], hAlign="LEFT")
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), bold_font),
        ("FONTNAME", (0, 1), (-1, -1), regular_font),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#DCE5E4")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary)

    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFont(regular_font, 8)
        canvas.setFillColor(colors.HexColor("#506576"))
        canvas.drawRightString(page_size[0] - 0.5*inch, 0.3*inch, f"Page {doc.page}")
        canvas.restoreState()

    document = BaseDocTemplate(
        str(pdf_path), pagesize=page_size,
        leftMargin=0.5*inch, rightMargin=0.5*inch,
        topMargin=0.5*inch, bottomMargin=0.55*inch,
        title="Project_worksummary",
    )
    body_frame = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        id="body",
    )
    document.addPageTemplates([
        PageTemplate(id="report", frames=[body_frame], onPage=draw_page)
    ])
    document.build(story)


def convert_into_pdf(workbook_path, output_dir, rows=None):
    executable = find_libreoffice()
    workbook_path = Path(workbook_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{workbook_path.stem}.pdf"
    if not executable:
        if rows is None:
            raise RuntimeError("LibreOffice was not found")
        _write_pdf(rows, pdf_path)
        return pdf_path

    command = [executable, "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(workbook_path)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if result.returncode != 0 or not pdf_path.exists():
        detail = (result.stderr or result.stdout).strip()
        if rows is None:
            raise RuntimeError(detail or "could not create the PDF file.")
        _write_pdf(rows, pdf_path)
    return pdf_path
