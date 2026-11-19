"""
Excel and CSV reader module.
Supports XLSX, XLS, and CSV files, multi-worksheet inspection,
encoding detection, and dataset extraction.
"""

from dataclasses import dataclass, field
from io import BytesIO, StringIO
from typing import Any, Dict, List, Optional, Tuple, Union
import csv
import pandas as pd


@dataclass
class SheetMetadata:
    name: str
    row_count: int
    column_count: int
    columns: List[str]


@dataclass
class DatasetMetadata:
    file_name: str
    file_type: str
    sheet_names: List[str]
    active_sheet: str
    df: pd.DataFrame
    sheets_info: Dict[str, SheetMetadata] = field(default_factory=dict)

    @property
    def total_rows(self) -> int:
        return len(self.df)

    @property
    def total_columns(self) -> int:
        return len(self.df.columns)


class ExcelReader:
    """
    Robust reader for Excel and CSV files with multi-sheet support,
    encoding recovery, and structure parsing.
    """

    ENCODINGS_TO_TRY = ["utf-8", "utf-8-sig", "latin1", "cp1252", "iso-8859-1"]
    COMMON_DELIMITERS = [",", ";", "\t", "|"]

    @classmethod
    def detect_csv_dialect(cls, file_content: bytes) -> Tuple[str, str]:
        """
        Detect encoding and delimiter for a CSV file.
        Returns (encoding, delimiter).
        """
        detected_encoding = "utf-8"
        text_sample = ""

        # Find workable encoding
        for encoding in cls.ENCODINGS_TO_TRY:
            try:
                text_sample = file_content[:8192].decode(encoding)
                detected_encoding = encoding
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if not text_sample:
            # Fallback with error replacement
            detected_encoding = "latin1"
            text_sample = file_content[:8192].decode("latin1", errors="replace")

        # Sniff delimiter
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(text_sample, delimiters="".join(cls.COMMON_DELIMITERS))
            delimiter = dialect.delimiter
        except Exception:
            # Heuristic count fallback
            counts = {d: text_sample.count(d) for d in cls.COMMON_DELIMITERS}
            delimiter = max(counts, key=counts.get) if counts else ","
            if counts.get(delimiter, 0) == 0:
                delimiter = ","

        return detected_encoding, delimiter

    @classmethod
    def inspect_excel_sheets(cls, file_bytes: bytes) -> List[str]:
        """
        Return the list of sheet names in an Excel file without loading entire data.
        """
        excel_file = pd.ExcelFile(BytesIO(file_bytes))
        return excel_file.sheet_names

    @classmethod
    def read_csv(
        cls,
        file_bytes: bytes,
        file_name: str = "dataset.csv",
        **pandas_kwargs,
    ) -> DatasetMetadata:
        """
        Read CSV bytes into a DatasetMetadata object.
        """
        encoding, delimiter = cls.detect_csv_dialect(file_bytes)

        try:
            df = pd.read_csv(
                BytesIO(file_bytes),
                encoding=encoding,
                sep=delimiter,
                engine="python",
                **pandas_kwargs,
            )
        except Exception as e:
            # Fallback with lenient options
            try:
                df = pd.read_csv(
                    BytesIO(file_bytes),
                    encoding="latin1",
                    on_bad_lines="skip",
                    **pandas_kwargs,
                )
            except Exception as inner_e:
                raise ValueError(f"Failed to parse CSV file: {str(e)} (fallback error: {str(inner_e)})")

        sheet_name = "CSV_Data"
        # Standardize column headers as strings
        df.columns = [str(col).strip() if col is not None else f"Column_{i}" for i, col in enumerate(df.columns)]

        sheet_meta = SheetMetadata(
            name=sheet_name,
            row_count=len(df),
            column_count=len(df.columns),
            columns=list(df.columns),
        )

        return DatasetMetadata(
            file_name=file_name,
            file_type="csv",
            sheet_names=[sheet_name],
            active_sheet=sheet_name,
            df=df,
            sheets_info={sheet_name: sheet_meta},
        )

    @classmethod
    def read_excel(
        cls,
        file_bytes: bytes,
        file_name: str = "dataset.xlsx",
        sheet_name: Optional[Union[str, int]] = None,
        file_type: str = "xlsx",
        **pandas_kwargs,
    ) -> DatasetMetadata:
        """
        Read Excel bytes into DatasetMetadata, optionally selecting a specific sheet.
        """
        try:
            excel_file = pd.ExcelFile(BytesIO(file_bytes))
            sheet_names = excel_file.sheet_names

            if not sheet_names:
                raise ValueError("Excel file contains no worksheets.")

            target_sheet = sheet_names[0]
            if sheet_name is not None:
                if isinstance(sheet_name, int):
                    if 0 <= sheet_name < len(sheet_names):
                        target_sheet = sheet_names[sheet_name]
                    else:
                        raise ValueError(f"Sheet index {sheet_name} out of bounds.")
                elif isinstance(sheet_name, str):
                    if sheet_name in sheet_names:
                        target_sheet = sheet_name
                    else:
                        raise ValueError(f"Sheet '{sheet_name}' not found in workbook. Available: {sheet_names}")

            # Read target sheet
            df = pd.read_excel(excel_file, sheet_name=target_sheet, **pandas_kwargs)
            # Ensure column names are strings
            df.columns = [str(col).strip() if col is not None else f"Column_{i}" for i, col in enumerate(df.columns)]

            # Build metadata for all sheets
            sheets_info: Dict[str, SheetMetadata] = {}
            for s_name in sheet_names:
                if s_name == target_sheet:
                    sheets_info[s_name] = SheetMetadata(
                        name=s_name,
                        row_count=len(df),
                        column_count=len(df.columns),
                        columns=list(df.columns),
                    )
                else:
                    # Parse header only to be lightweight
                    try:
                        s_df = pd.read_excel(excel_file, sheet_name=s_name, nrows=1)
                        s_cols = [str(c).strip() for c in s_df.columns]
                        sheets_info[s_name] = SheetMetadata(
                            name=s_name,
                            row_count=0,  # lazy / unread
                            column_count=len(s_cols),
                            columns=s_cols,
                        )
                    except Exception:
                        sheets_info[s_name] = SheetMetadata(
                            name=s_name,
                            row_count=0,
                            column_count=0,
                            columns=[],
                        )

            return DatasetMetadata(
                file_name=file_name,
                file_type=file_type,
                sheet_names=sheet_names,
                active_sheet=target_sheet,
                df=df,
                sheets_info=sheets_info,
            )
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Failed to parse Excel file '{file_name}': {str(e)}")

    @classmethod
    def load_dataset(
        cls,
        file_bytes: bytes,
        file_name: str,
        sheet_name: Optional[str] = None,
    ) -> DatasetMetadata:
        """
        Unified loader that detects file extension and delegates appropriately.
        """
        from utils.file_validator import sanitize_filename
        clean_name = sanitize_filename(file_name)
        lower_name = clean_name.lower()

        if lower_name.endswith(".csv"):
            return cls.read_csv(file_bytes=file_bytes, file_name=clean_name)
        elif lower_name.endswith(".xlsx"):
            return cls.read_excel(
                file_bytes=file_bytes,
                file_name=clean_name,
                sheet_name=sheet_name,
                file_type="xlsx",
            )
        elif lower_name.endswith(".xls"):
            return cls.read_excel(
                file_bytes=file_bytes,
                file_name=clean_name,
                sheet_name=sheet_name,
                file_type="xls",
            )
        else:
            raise ValueError(f"Unsupported file format for '{file_name}'.")
