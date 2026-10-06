from pathlib import Path
import re
from typing import Any
from uuid import uuid4

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.settings import settings


def generate_excel_spreadsheet(
    filename: str,
    headers: list[str],
    rows: list[list[Any]],
    sheet_name: str = "JARVIS Data",
    include_summary_row: bool = True,
) -> Path:
    """
    Generate a styled Excel spreadsheet (.xlsx) with headers, cell formats, auto-width, and summary formulas.
    """
    out_dir = settings.generated_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^\w\-_]", "_", filename.replace(".xlsx", ""))[:40]
    out_filename = f"{safe_name}_{uuid4().hex[:6]}.xlsx"
    dest_path = out_dir / out_filename

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name[:30]

    # Styles
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="64FFDA")
    data_font = Font(name="Segoe UI", size=10, color="1E293B")
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    summary_font = Font(name="Segoe UI", size=11, bold=True, color="0284C7")
    summary_fill = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    # 1. Write Headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[1].height = 28

    # 2. Write Data Rows
    for r_idx, row_data in enumerate(rows, 2):
        is_alt = (r_idx % 2 == 0)
        for c_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.font = data_font
            cell.border = thin_border
            if is_alt:
                cell.fill = alt_fill

            # Format numeric / currency alignment
            if isinstance(val, (int, float)):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[r_idx].height = 20

    # 3. Summary Row (if numeric columns exist and requested)
    if include_summary_row and rows:
        sum_row_idx = len(rows) + 2
        sum_cell_label = ws.cell(row=sum_row_idx, column=1, value="TOTAL / SUMMARY")
        sum_cell_label.font = summary_font
        sum_cell_label.fill = summary_fill
        sum_cell_label.border = thin_border

        for c_idx in range(2, len(headers) + 1):
            cell = ws.cell(row=sum_row_idx, column=c_idx)
            cell.font = summary_font
            cell.fill = summary_fill
            cell.border = thin_border
            # Check if column is numeric
            col_vals = [r[c_idx - 1] for r in rows if len(r) >= c_idx and isinstance(r[c_idx - 1], (int, float))]
            if len(col_vals) > len(rows) // 2:
                col_letter = get_column_letter(c_idx)
                cell.value = f"=SUM({col_letter}2:{col_letter}{sum_row_idx - 1})"
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.value = ""

    # 4. Auto-fit Column Widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    wb.save(str(dest_path))
    return dest_path
