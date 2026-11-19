"""
Tests for Excel and CSV reader module.
"""

from io import BytesIO
from pathlib import Path
import pytest
import pandas as pd
from core.excel_reader import ExcelReader, DatasetMetadata

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def test_read_csv_comma_delimited():
    csv_bytes = b"id,name,age\n1,Alice,30\n2,Bob,25\n"
    dataset = ExcelReader.read_csv(csv_bytes, file_name="test.csv")
    assert dataset.file_type == "csv"
    assert dataset.total_rows == 2
    assert dataset.total_columns == 3
    assert list(dataset.df.columns) == ["id", "name", "age"]


def test_read_csv_semicolon_delimited():
    csv_bytes = b"id;product;price\n101;Widget;9.99\n102;Gadget;19.99\n"
    dataset = ExcelReader.read_csv(csv_bytes, file_name="test_semi.csv")
    assert dataset.total_rows == 2
    assert dataset.total_columns == 3
    assert "product" in dataset.df.columns


def test_read_samples_employees_csv():
    emp_path = SAMPLES_DIR / "employees_data.csv"
    assert emp_path.exists()
    with open(emp_path, "rb") as f:
        file_bytes = f.read()

    dataset = ExcelReader.load_dataset(file_bytes, "employees_data.csv")
    assert dataset.file_type == "csv"
    assert dataset.total_rows == 7
    assert "Department" in dataset.df.columns
    assert "Salary" in dataset.df.columns


def test_read_samples_sales_excel_multi_sheet():
    sales_path = SAMPLES_DIR / "sales_data.xlsx"
    assert sales_path.exists()
    with open(sales_path, "rb") as f:
        file_bytes = f.read()

    sheets = ExcelReader.inspect_excel_sheets(file_bytes)
    assert set(sheets) == {"Orders", "Returns", "Customers"}

    # Default loads first sheet
    dataset = ExcelReader.load_dataset(file_bytes, "sales_data.xlsx")
    assert dataset.file_type == "xlsx"
    assert dataset.active_sheet == "Orders"
    assert dataset.total_rows == 8
    assert "Order_ID" in dataset.df.columns

    # Load specific sheet: Returns
    returns_dataset = ExcelReader.load_dataset(file_bytes, "sales_data.xlsx", sheet_name="Returns")
    assert returns_dataset.active_sheet == "Returns"
    assert returns_dataset.total_rows == 3
    assert "Refund_Amount" in returns_dataset.df.columns


def test_read_invalid_sheet_name():
    sales_path = SAMPLES_DIR / "sales_data.xlsx"
    with open(sales_path, "rb") as f:
        file_bytes = f.read()

    with pytest.raises(ValueError, match="not found in workbook"):
        ExcelReader.load_dataset(file_bytes, "sales_data.xlsx", sheet_name="NonExistentSheet")


def test_read_corrupted_excel():
    corrupted_bytes = b"PK\x03\x04" + b"garbage_data_not_valid_zip"
    with pytest.raises(ValueError, match="Failed to parse Excel file"):
        ExcelReader.read_excel(corrupted_bytes, "corrupted.xlsx")
