"""
Tests for edge cases, unusual schemas, safety, and formula injection handling (Phase 8).
"""

import pytest
import pandas as pd
import numpy as np

from core.data_profiler import DataProfiler
from core.data_cleaner import DataCleaner
from core.data_validator import DataValidator
from core.data_formatter import DataFormatter
from analytics.statistics import StatisticsEngine
from dashboard.dashboard_builder import DashboardBuilder


def test_empty_dataframe_handling():
    empty_df = pd.DataFrame()
    report = DataProfiler.profile_dataset(empty_df)
    assert report.total_rows == 0
    assert report.total_columns == 0
    assert report.overall_quality_score == 100.0

    kpis = DashboardBuilder.get_auto_kpis(empty_df)
    assert len(kpis) >= 1

    charts = DashboardBuilder.get_recommended_charts(empty_df)
    assert charts == []


def test_all_null_dataframe():
    null_df = pd.DataFrame({
        "A": [None, None, None],
        "B": [np.nan, np.nan, np.nan],
    })
    report = DataProfiler.profile_dataset(null_df)
    assert report.empty_rows_count == 3
    assert report.empty_columns_count == 2

    cleaner = DataCleaner()
    cleaned = cleaner.drop_empty_rows(null_df)
    assert len(cleaned) == 0


def test_unusual_column_names():
    weird_df = pd.DataFrame({
        "  Leading Space  ": [1, 2, 3],
        "Special@Chars#$!": ["a", "b", "c"],
        "123_Numeric_Start": [10.5, 20.2, 30.1],
        "Unicode_日本語_🌟": [True, False, True],
    })
    report = DataProfiler.profile_dataset(weird_df)
    assert report.total_columns == 4

    stats = StatisticsEngine.get_descriptive_stats(weird_df)
    assert "123_Numeric_Start" in stats["numeric_summary"].index

    cleaner = DataCleaner()
    cleaned = cleaner.trim_whitespace(weird_df, "Special@Chars#$!")
    assert len(cleaned) == 3


def test_formula_injection_defense():
    nasty_df = pd.DataFrame({
        "Text": ["=HYPERLINK('http://evil.com')", "-2+3+cmd|' /C calc'!A0", "+1+1", "@SUM(A1:A10)", "Normal string"],
        "Number": [10, -5, 20, 0, 99],
    })
    safe_df = DataFormatter.sanitize_for_formula_injection(nasty_df)
    # Numbers should not be altered
    assert safe_df["Number"].iloc[1] == -5
    # Text starting with formula characters must be safely quoted
    assert safe_df["Text"].iloc[0].startswith("'=")
    assert safe_df["Text"].iloc[1].startswith("'-")
    assert safe_df["Text"].iloc[2].startswith("'+")
    assert safe_df["Text"].iloc[3].startswith("'@")
    assert safe_df["Text"].iloc[4] == "Normal string"
