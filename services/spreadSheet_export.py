"""this function help's to Create's the formatted Excel """

from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from services.validator import HEADERS, calculate_totals

NAVY = "19024A"
TEAL = "197B78"
PALE = "E7F3F2"
WHITE = "FFFFFF"
INK = "298746"


# NAVY = colors.HexColor("#19024A")
# TEAL = colors.HexColor("#197B78")
# PALE = colors.HexColor("#E7F3F2")
# INK = colors.HexColor("#298746")


def workbook_gernator(rows, file_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Project_worksummary"
    sheet.sheet_view.showGridLines = False

    sheet.merge_cells("A1:G1")
    sheet["A1"] = "Project WORK SUMMARY"
    sheet["A1"].font = Font(name="Aptos Display", size=20, bold=True, color=WHITE)
    sheet["A1"].fill = PatternFill("solid", fgColor=NAVY)
    sheet["A1"].alignment = Alignment(vertical="center")
    sheet.row_dimensions[1].height = 38
    sheet.merge_cells("A2:G2")
    # sheet["A2"] = f"Prepared {date.today().strftime('%B %d, %Y')}"
    sheet["A2"].font = Font(name="Aptos", size=10, color="607585", italic=True)
    sheet.row_dimensions[2].height = 24

    # sheet["A4"] = "ACTIVITY"
    sheet["A4"].font = Font(name="Aptos", size=11, bold=True, color=TEAL)
    for column, heading in enumerate(HEADERS + ("Amount",), start=1):
        cell = sheet.cell(row=5, column=column, value=heading)
        cell.font = Font(name="Aptos", bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=NAVY)
        cell.alignment = Alignment(vertical="center")
    sheet.row_dimensions[5].height = 25

    for row_index, row in enumerate(rows, start=6):
        values = [str(row[0]), str(row[1]), str(row[2]), str(row[3]), float(row[4]), float(row[5]), float(row[4]) * float(row[5])]
        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row=row_index, column=column, value=value)
            cell.font = Font(name="Aptos", size=10, color=INK)
            cell.fill = PatternFill("solid", fgColor=WHITE if row_index % 2 == 0 else PALE)
            cell.alignment = Alignment(vertical="center")
            if column in (6, 7):
                cell.number_format = '"₹"#,##0.00;[Red]("₹"#,##0.00)'
                cell.alignment = Alignment(horizontal="right", vertical="center")
        sheet.row_dimensions[row_index].height = 22

    last_row = 5 + len(rows)
    total_row = last_row + 1
    sheet.cell(total_row, 4, "TOTAL")
    sheet.cell(total_row, 5, f"=SUM(E6:E{last_row})")
    sheet.cell(total_row, 7, f"=SUM(G6:G{last_row})")
    for column in (4, 5, 7):
        cell = sheet.cell(total_row, column)
        cell.font = Font(name="Aptos", bold=True, color=NAVY)
        cell.border = Border(top=Side(style="thin", color=TEAL))
    sheet.cell(total_row, 7).number_format = '"₹"#,##0.00'

    _, grand_total, by_client = calculate_totals(rows)
    summary_top = total_row + 3
    sheet.cell(summary_top, 1, "CLIENT TOTALS")
    sheet.cell(summary_top, 1).font = Font(name="Aptos", size=11, bold=True, color=TEAL)
    for offset, (client, amount) in enumerate(sorted(by_client.items()), start=1):
        sheet.cell(summary_top + offset, 1, client)
        sheet.cell(summary_top + offset, 2, amount).number_format = '"₹"#,##0.00'
    sheet.cell(summary_top + len(by_client) + 2, 1, "Report total")
    sheet.cell(summary_top + len(by_client) + 2, 2, grand_total).number_format = '"₹"#,##0.00'

    widths = (14, 24, 18, 38, 12, 14, 16)
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A6"
    sheet.auto_filter.ref = f"A5:G{last_row}"
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.print_title_rows = "1:5"
    sheet.print_area = f"A1:G{summary_top + len(by_client) + 2}"
    workbook.save(file_path)
