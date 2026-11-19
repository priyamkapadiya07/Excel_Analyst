"""
Excel Exporter supporting standard and styled workbooks.
"""

from typing import Optional, Dict
import pandas as pd
from core.data_formatter import DataFormatter, ExcelFormattingOptions


class ExcelExporter:
    """Exports single or multi-sheet Excel workbooks with optional styling."""

    @classmethod
    def export(
        cls,
        df: pd.DataFrame,
        sheet_name: str = "Cleaned_Data",
        options: Optional[ExcelFormattingOptions] = None,
        multi_sheets: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> bytes:
        return DataFormatter.create_formatted_excel(
            df=df,
            sheet_name=sheet_name,
            options=options,
            multi_sheets=multi_sheets,
        )
