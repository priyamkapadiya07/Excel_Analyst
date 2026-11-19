"""
Excel Data Formatter module.
Applies professional visual formatting, styling, borders, conditional highlighting,
and auto-column sizing using OpenPyXL, while keeping formatting distinct from data cleaning.
"""

from dataclasses import dataclass
from io import BytesIO
from typing import Optional, List, Dict, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd


@dataclass
class ExcelFormattingOptions:
    theme: str = "Corporate Navy"  # Corporate Navy, Modern Emerald, Classic Slate, Clean Minimal
    header_bold: bool = True
    freeze_header: bool = True
    auto_fit_columns: bool = True
    add_borders: bool = True
    number_format: str = "#,##0.00"
    date_format: str = "yyyy-mm-dd"
    highlight_alternate_rows: bool = True


THEME_COLORS = {
    "Corporate Navy": {"header_fill": "1E3A8A", "header_font": "FFFFFF", "alt_fill": "F0F4F8"},
    "Modern Emerald": {"header_fill": "065F46", "header_font": "FFFFFF", "alt_fill": "ECFDF5"},
    "Classic Slate": {"header_fill": "334155", "header_font": "FFFFFF", "alt_fill": "F8FAFC"},
    "Clean Minimal": {"header_fill": "E2E8F0", "header_font": "1E293B", "alt_fill": "FFFFFF"},
}


class DataFormatter:
    """Formats pandas DataFrames into styled Excel workbooks."""

    @staticmethod
    def sanitize_for_formula_injection(df: pd.DataFrame) -> pd.DataFrame:
        """
        Prevents formula injection in exported spreadsheets by prefixing single quote
        to string cells starting with dangerous trigger characters (=, +, -, @).
        """
        df_safe = df.copy()
        for col in df_safe.columns:
            if df_safe[col].dtype == "object" or pd.api.types.is_string_dtype(df_safe[col]):
                df_safe[col] = df_safe[col].apply(
                    lambda val: f"'{val}"
                    if isinstance(val, str) and val.startswith(("=", "+", "-", "@"))
                    else val
                )
        return df_safe

    @classmethod
    def create_formatted_excel(
        cls,
        df: pd.DataFrame,
        sheet_name: str = "Data",
        options: Optional[ExcelFormattingOptions] = None,
        multi_sheets: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> bytes:
        """
        Creates an OpenPyXL workbook with user-specified styling, headers,
        borders, and column adjustments.
        """
        opts = options or ExcelFormattingOptions()
        theme = THEME_COLORS.get(opts.theme, THEME_COLORS["Corporate Navy"])

        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        sheets_to_process = multi_sheets or {sheet_name: df}

        thin_side = Side(border_style="thin", color="D1D5DB")
        table_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        for s_title, current_df in sheets_to_process.items():
            safe_df = cls.sanitize_for_formula_injection(current_df)
            ws = wb.create_sheet(title=s_title[:31])  # Excel max sheet name is 31 chars

            # 1. Write headers
            headers = [str(c) for c in safe_df.columns]
            ws.append(headers)

            # Style header row
            header_font = Font(name="Calibri", size=11, bold=opts.header_bold, color=theme["header_font"])
            header_fill = PatternFill(start_color=theme["header_fill"], end_color=theme["header_fill"], fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                if opts.add_borders:
                    cell.border = table_border

            ws.row_dimensions[1].height = 28

            # 2. Write data rows
            alt_fill = PatternFill(start_color=theme["alt_fill"], end_color=theme["alt_fill"], fill_type="solid")

            for row_idx, row_data in enumerate(safe_df.itertuples(index=False), start=2):
                ws.append(list(row_data))
                ws.row_dimensions[row_idx].height = 20

                is_alt_row = (row_idx % 2 == 1) and opts.highlight_alternate_rows

                for col_idx, val in enumerate(row_data, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    cell.font = Font(name="Calibri", size=10)
                    if opts.add_borders:
                        cell.border = table_border

                    if is_alt_row:
                        cell.fill = alt_fill

                    # Number & date formatting
                    if isinstance(val, (int, float)) and not pd.isna(val):
                        cell.alignment = Alignment(horizontal="right", vertical="center")
                        cell.number_format = opts.number_format
                    elif isinstance(val, (pd.Timestamp, pd.DatetimeIndex)) or "date" in str(safe_df.columns[col_idx-1]).lower():
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                        cell.number_format = opts.date_format
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="center")

            # 3. Freeze Header Row
            if opts.freeze_header:
                ws.freeze_panes = "A2"

            # 4. Auto-fit column widths
            if opts.auto_fit_columns:
                for col_idx, col in enumerate(safe_df.columns, start=1):
                    max_len = max(
                        [len(str(val)) for val in safe_df[col].dropna().values[:100]] + [len(str(col))]
                    )
                    col_letter = get_column_letter(col_idx)
                    ws.column_dimensions[col_letter].width = min(40, max(12, max_len + 4))

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
