"""
CSV Exporter with formula-injection protection and customizable encoding/delimiter.
"""

from typing import Optional
from io import StringIO, BytesIO
import pandas as pd
from core.data_formatter import DataFormatter


class CSVExporter:
    """Exports DataFrames to CSV format safely."""

    @classmethod
    def export(
        cls,
        df: pd.DataFrame,
        delimiter: str = ",",
        encoding: str = "utf-8",
        sanitize: bool = True,
    ) -> bytes:
        export_df = DataFormatter.sanitize_for_formula_injection(df) if sanitize else df
        buffer = StringIO()
        export_df.to_csv(buffer, sep=delimiter, index=False, encoding=encoding)
        return buffer.getvalue().encode(encoding)
