from pathlib import Path

from services.spreadSheet_export import workbook_gernator
from services.docsName import generate_path
from services.pdf_exporter import convert_into_pdf
from services.validator import validate_input_rows


def excel_generator(rows, output_folder, progress=None, filename_prefix="worksummary"):
    problems = validate_input_rows(rows)
    if problems:
        raise ValueError("\n".join(problems))
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    xlsx_path = generate_path(
        output_folder,
        filename_prefix,
        ".xlsx",
        companion_extensions=(".pdf",),
    )
    if progress:
        progress(25, "Preparing the  workbook…")
    workbook_gernator(rows, xlsx_path)
    if progress:
        progress(100, "Excel is ready.")
    return xlsx_path


def pdf_generator(workbook_path, rows, progress=None):
    workbook_path = Path(workbook_path)
    if not workbook_path.exists():
        raise FileNotFoundError(f" workbook  not found: {workbook_path}")
    if progress:
        progress(25, "Converting the Excel in PDF…")
    pdf_path = convert_into_pdf(workbook_path, workbook_path.parent, rows)
    if progress:
        progress(100, "PDF  is ready.")
    return pdf_path


def reports_generator(rows, output_folder, progress=None):
    """this need both reports in one operation."""
    excel_progress = None
    pdf_progress = None
    if progress:
        excel_progress = lambda value, message: progress(round(value * 0.5), message)
        pdf_progress = lambda value, message: progress(50 + round(value * 0.5), message)
    xlsx_path = excel_generator(rows, output_folder, excel_progress)
    pdf_path =pdf_generator(xlsx_path, rows, pdf_progress)
    return xlsx_path, pdf_path
