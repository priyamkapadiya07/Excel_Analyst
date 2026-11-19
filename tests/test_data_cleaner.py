"""
Tests for DataCleaner, CleaningLogger, and DataValidator (Phase 4).
"""

import pytest
import pandas as pd
import numpy as np
from core.data_cleaner import DataCleaner
from core.data_validator import DataValidator
from core.data_profiler import DataProfiler
from utils.cleaning_log import CleaningLogger


def test_cleaner_drop_duplicates_and_empty():
    df = pd.DataFrame({
        "A": [1, 1, None, 2],
        "B": ["x", "x", None, "y"],
        "C": [None, None, None, None]  # Completely empty col
    })
    # Row 2 is completely empty
    logger = CleaningLogger()
    cleaner = DataCleaner(logger)

    cleaned = cleaner.drop_empty_rows(df)
    assert len(cleaned) == 3

    cleaned = cleaner.drop_empty_columns(cleaned)
    assert "C" not in cleaned.columns

    cleaned = cleaner.drop_duplicates(cleaned)
    assert len(cleaned) == 2
    assert len(logger.entries) == 3


def test_cleaner_whitespace_and_casing():
    df = pd.DataFrame({
        "City": [" London ", "NEW YORK  ", "tokyo", None]
    })
    cleaner = DataCleaner()
    df_clean = cleaner.trim_whitespace(df, "City")
    assert df_clean["City"].iloc[0] == "London"
    assert df_clean["City"].iloc[1] == "NEW YORK"

    df_clean = cleaner.standardize_text_casing(df_clean, "City", "title")
    assert df_clean["City"].iloc[1] == "New York"
    assert df_clean["City"].iloc[2] == "Tokyo"


def test_cleaner_impute_missing():
    df = pd.DataFrame({
        "Val": [10.0, 20.0, None, 30.0],
        "Cat": ["A", None, "B", "A"]
    })
    cleaner = DataCleaner()
    df_med = cleaner.impute_missing(df, "Val", "median")
    assert df_med["Val"].iloc[2] == 20.0

    df_mode = cleaner.impute_missing(df, "Cat", "mode")
    assert df_mode["Cat"].iloc[1] == "A"


def test_cleaner_outliers_and_dates():
    df = pd.DataFrame({
        "Amount": [10, 11, 12, 10, 11, 12, 500],  # 500 outlier
        "Date": ["2026-01-01", "2026-01-02", "bad_date", "2026-01-04", "2026-01-05", "2026-01-06", "2026-01-07"]
    })
    cleaner = DataCleaner()
    df_capped = cleaner.cap_outliers_iqr(df, "Amount")
    assert df_capped["Amount"].max() < 500

    df_dates = cleaner.coerce_dates(df, "Date")
    assert pd.isna(df_dates["Date"].iloc[2])


def test_validator_before_after():
    df_orig = pd.DataFrame({
        "A": [1, 1, None, 4],
        "B": ["foo", "foo", "bar", None]
    })
    report_orig = DataProfiler.profile_dataset(df_orig)

    cleaner = DataCleaner()
    df_clean = cleaner.drop_duplicates(df_orig)
    df_clean = cleaner.impute_missing(df_clean, "A", "median")
    df_clean = cleaner.impute_missing(df_clean, "B", "fill_unknown")

    summary = DataValidator.validate_cleaned_dataset(df_orig, df_clean, report_orig)
    assert summary.is_valid
    assert summary.rows_after == 3
    assert summary.missing_after == 0
    assert summary.missing_resolved == 2
    assert summary.score_after >= summary.score_before
