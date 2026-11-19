"""
Tests for DataProfiler module (Phase 2).
"""

import pandas as pd
import numpy as np
import pytest
from core.data_profiler import DataProfiler


def test_detect_empty_rows_and_cols():
    df = pd.DataFrame({
        "A": [1, None, 3, None],
        "B": [None, None, None, None],  # Completely empty column
        "C": ["x", None, "z", None],
    })
    # Add a completely empty row (index 1 and index 3 have nulls in A, B, C)
    empty_rows, empty_cols, empty_col_names = DataProfiler.detect_empty_rows_and_cols(df)
    assert empty_rows == 2  # Row 1 and Row 3 are all null
    assert empty_cols == 1
    assert empty_col_names == ["B"]


def test_detect_whitespace_issues():
    series = pd.Series(["clean", " leading", "trailing ", "double  space", None, "ok"])
    count, samples = DataProfiler.detect_whitespace_issues(series)
    assert count == 3
    assert len(samples) == 3


def test_detect_case_inconsistencies():
    series = pd.Series(["North", "north", "NORTH", "South", "East", "east"])
    count, groups = DataProfiler.detect_case_inconsistencies(series)
    assert len(groups) == 2  # 'north' and 'east'
    assert count == 5  # 3 'north' variants + 2 'east' variants


def test_detect_outliers_iqr():
    # 10 values around 10-20, plus an outlier at 1000
    series = pd.Series([10, 11, 12, 12, 13, 14, 15, 16, 17, 18, 1000])
    outlier_count, low, high, samples = DataProfiler.detect_outliers_iqr(series)
    assert outlier_count >= 1
    assert 1000 in samples


def test_detect_date_issues():
    series = pd.Series(["2026-01-01", "2026-01-02", "not_a_date", "2026-01-05"], name="Order_Date")
    count, invalid_samples = DataProfiler.detect_date_issues(series)
    assert count == 1
    assert "not_a_date" in invalid_samples


def test_detect_type_mismatches():
    series = pd.Series(["$12.50", "$34.00", "$99.99", "$120.00", "not_a_number"])
    count, target_type, unconverted = DataProfiler.detect_type_mismatches(series)
    assert count == 4
    assert target_type == "numeric"
    assert "not_a_number" in unconverted


def test_profile_dataset_overall():
    df = pd.DataFrame({
        "ID": [1, 2, 2, 3],  # Duplicate row 2
        "Name": [" Alice", "Bob", "Bob", "Charlie"],
        "City": ["London", "london", "london", "Paris"],
        "Salary": [50000, 60000, 60000, 999999],  # 999999 outlier
        "Join_Date": ["2026-01-01", "2026-02-01", "2026-02-01", "invalid_date"],
        "Notes": [None, None, None, None]  # Empty col
    })

    report = DataProfiler.profile_dataset(df)
    assert report.total_rows == 4
    assert report.total_columns == 6
    assert report.duplicate_rows_count == 1
    assert report.empty_columns_count == 1
    assert report.issues_summary["Duplicate Rows"] == 1
    assert report.issues_summary["Whitespace Errors"] >= 1
    assert report.issues_summary["Case Inconsistencies"] >= 1
    assert report.issues_summary["Date Issues"] >= 1
    assert report.issues_summary["Outliers"] >= 1
    assert 0 <= report.overall_quality_score <= 100
    assert report.grade in ["A+", "A", "B", "C", "D", "F"]
