"""
Tests for DataFormatter, ExcelExporter, CSVExporter, and ReportExporter (Phase 5).
"""

from io import BytesIO
import openpyxl
import pandas as pd
import pytest
from core.data_formatter import DataFormatter, ExcelFormattingOptions
from export.csv_exporter import CSVExporter
from export.excel_exporter import ExcelExporter
from export.report_exporter import ReportExporter


def test_formula_injection_sanitization():
    df = pd.DataFrame({
        "Name": ["=CMD|' /C calc'!A0", "+SUM(1,2)", "-10", "@evil", "Normal"]
    })
    safe_df = DataFormatter.sanitize_for_formula_injection(df)
    assert safe_df["Name"].iloc[0].startswith("'=")
    assert safe_df["Name"].iloc[1].startswith("'+")
    assert safe_df["Name"].iloc[2].startswith("'-")
    assert safe_df["Name"].iloc[3].startswith("'@")
    assert safe_df["Name"].iloc[4] == "Normal"


def test_csv_export():
    df = pd.DataFrame({
        "id": [1, 2],
        "city": ["Paris", "Tokyo"]
    })
    csv_bytes = CSVExporter.export(df)
    assert b"id,city" in csv_bytes
    assert b"Paris" in csv_bytes


def test_excel_export_and_formatting():
    df = pd.DataFrame({
        "Employee": ["Alice", "Bob"],
        "Salary": [75000.50, 82000.00],
        "Join_Date": ["2026-01-15", "2026-02-01"]
    })
    opts = ExcelFormattingOptions(
        theme="Modern Emerald",
        freeze_header=True,
        add_borders=True,
    )
    excel_bytes = ExcelExporter.export(df, sheet_name="Staff", options=opts)
    assert excel_bytes.startswith(b"PK\x03\x04")

    # Read back with OpenPyXL
    wb = openpyxl.load_workbook(BytesIO(excel_bytes))
    assert "Staff" in wb.sheetnames
    ws = wb["Staff"]
    assert ws.cell(row=1, column=1).value == "Employee"
    assert ws.freeze_panes == "A2"


def test_report_exporter():
    df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
    html = ReportExporter.generate_html_report(
        file_name="test.xlsx",
        sheet_name="Data",
        df=df,
        cleaning_log=[{"Action": "drop_duplicates", "Description": "Dropped 1 dup", "Affected Items": 1}]
    )
    assert "<!DOCTYPE html>" in html
    assert "test.xlsx" in html
    assert "drop_duplicates" in html
