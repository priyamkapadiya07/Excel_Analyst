"""
End-to-End Integration Tests for AI Excel Analyst (Phase 8).
Validates the complete workflow across different domains:
1. Sales Data (Multi-sheet XLSX)
2. Employees Data (CSV)
3. Inventory Data (Multi-sheet XLSX)
Covers upload -> profiling -> questions -> cleaning -> validation -> formatting -> analytics -> dashboard -> export.
"""

from io import BytesIO
from pathlib import Path
import pytest
import pandas as pd
import openpyxl

from core.excel_reader import ExcelReader
from core.data_profiler import DataProfiler
from ai.question_generator import QuestionGenerator
from core.data_cleaner import DataCleaner
from core.data_validator import DataValidator
from core.data_formatter import DataFormatter, ExcelFormattingOptions
from export.excel_exporter import ExcelExporter
from export.csv_exporter import CSVExporter
from export.report_exporter import ReportExporter
from analytics.statistics import StatisticsEngine
from analytics.insights import InsightGenerator
from ai.analysis_assistant import AnalysisAssistant
from dashboard.dashboard_builder import DashboardBuilder

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def test_e2e_sales_pipeline():
    # 1. Load Sales Multi-sheet
    sales_file = SAMPLES_DIR / "sales_data.xlsx"
    with open(sales_file, "rb") as f:
        file_bytes = f.read()

    dataset = ExcelReader.load_dataset(file_bytes, "sales_data.xlsx", sheet_name="Orders")
    assert dataset.total_rows == 8
    df_orig = dataset.df

    # 2. Profile Quality
    report = DataProfiler.profile_dataset(df_orig)
    assert report.overall_quality_score < 100
    assert report.duplicate_rows_count >= 1

    # 3. Generate Questions
    gen = QuestionGenerator()
    questions = gen.generate_rule_based_questions(report)
    assert len(questions) > 0

    # Build decisions using defaults
    decisions = {}
    for q in questions:
        default_opt = next((opt for opt in q.options if opt.is_default), q.options[0])
        decisions[q.id] = {
            "action": default_opt.action,
            "column": q.column,
            "issue_type": q.issue_type,
        }

    # 4. Clean Data
    cleaner = DataCleaner()
    cleaned_df = cleaner.execute_cleaning_decisions(df_orig, decisions)
    assert len(cleaned_df) <= len(df_orig)

    # 5. Validate Integrity
    val = DataValidator.validate_cleaned_dataset(df_orig, cleaned_df, report)
    assert val.is_valid
    assert val.score_after >= val.score_before

    # 6. Statistical Analysis & NL Query
    stats = StatisticsEngine.get_descriptive_stats(cleaned_df)
    assert stats["numeric_summary"] is not None
    insights = InsightGenerator.generate_insights(cleaned_df)
    assert len(insights) > 0

    assistant = AnalysisAssistant()
    intent, result = assistant.interpret_and_execute("Top 3 customers by sales", cleaned_df)
    assert intent.operation == "top_performers"
    assert len(result) <= 3

    # 7. Dashboard Generation
    kpis = DashboardBuilder.get_auto_kpis(cleaned_df)
    assert len(kpis) >= 2
    charts = DashboardBuilder.get_recommended_charts(cleaned_df)
    assert len(charts) >= 2

    dash_html = DashboardBuilder.export_dashboard_html("Sales Dashboard", kpis, [c["figure"] for c in charts])
    assert "<!DOCTYPE html>" in dash_html

    # 8. Export in Multiple Formats
    excel_bytes = ExcelExporter.export(cleaned_df, sheet_name="Orders", options=ExcelFormattingOptions(theme="Corporate Navy"))
    assert excel_bytes.startswith(b"PK\x03\x04")

    csv_bytes = CSVExporter.export(cleaned_df)
    assert b"Order_ID" in csv_bytes

    report_html = ReportExporter.generate_html_report("sales_data.xlsx", "Orders", cleaned_df, report, val)
    assert "<!DOCTYPE html>" in report_html


def test_e2e_employees_csv_pipeline():
    # Load Employees CSV
    emp_file = SAMPLES_DIR / "employees_data.csv"
    with open(emp_file, "rb") as f:
        file_bytes = f.read()

    dataset = ExcelReader.load_dataset(file_bytes, "employees_data.csv")
    assert dataset.file_type == "csv"
    df_orig = dataset.df

    report = DataProfiler.profile_dataset(df_orig)
    assert report.total_rows == 7

    # Questions & Cleaning
    gen = QuestionGenerator()
    questions = gen.generate_rule_based_questions(report)
    decisions = {
        q.id: {"action": next(opt.action for opt in q.options if opt.is_default), "column": q.column}
        for q in questions
    }

    cleaner = DataCleaner()
    df_clean = cleaner.execute_cleaning_decisions(df_orig, decisions)

    # Validation
    val = DataValidator.validate_cleaned_dataset(df_orig, df_clean, report)
    assert val.is_valid

    # Analysis
    grouped = StatisticsEngine.aggregate_by_group(df_clean, "Department", "Salary", "mean")
    assert "Salary_mean" in grouped.columns

    # Formatted Excel Export
    excel_bytes = ExcelExporter.export(df_clean, sheet_name="Employees", options=ExcelFormattingOptions(theme="Modern Emerald"))
    wb = openpyxl.load_workbook(BytesIO(excel_bytes))
    assert "Employees" in wb.sheetnames


def test_e2e_inventory_multi_sheet_pipeline():
    inv_file = SAMPLES_DIR / "inventory_data.xlsx"
    with open(inv_file, "rb") as f:
        file_bytes = f.read()

    # Load Suppliers sheet
    dataset = ExcelReader.load_dataset(file_bytes, "inventory_data.xlsx", sheet_name="Suppliers")
    assert dataset.active_sheet == "Suppliers"
    assert "Supplier_Name" in dataset.df.columns

    # Load Current_Stock sheet
    stock_ds = ExcelReader.load_dataset(file_bytes, "inventory_data.xlsx", sheet_name="Current_Stock")
    assert stock_ds.active_sheet == "Current_Stock"
    report = DataProfiler.profile_dataset(stock_ds.df)
    assert report.duplicate_rows_count >= 1

    cleaner = DataCleaner()
    cleaned_stock = cleaner.drop_duplicates(stock_ds.df)
    assert len(cleaned_stock) < len(stock_ds.df)
