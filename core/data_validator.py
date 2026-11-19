"""
Data validator module.
Validates cleaned dataset integrity and generates comparison metrics against original dataset.
"""

from dataclasses import dataclass
from typing import Dict, Any, Tuple
import pandas as pd
from core.data_profiler import DataProfiler, DatasetQualityReport


@dataclass
class CleaningValidationSummary:
    is_valid: bool
    warnings: list[str]
    errors: list[str]
    rows_before: int
    rows_after: int
    rows_change: int
    cols_before: int
    cols_after: int
    cols_change: int
    missing_before: int
    missing_after: int
    missing_resolved: int
    score_before: float
    score_after: float
    score_improvement: float


class DataValidator:
    """Validates transformations and compares pre/post dataset health."""

    @classmethod
    def validate_cleaned_dataset(
        cls,
        df_original: pd.DataFrame,
        df_cleaned: pd.DataFrame,
        report_before: DatasetQualityReport,
    ) -> CleaningValidationSummary:
        errors = []
        warnings = []

        # Check if accidentally emptied
        if len(df_cleaned) == 0 and len(df_original) > 0:
            errors.append("Cleaned dataset has 0 rows while original dataset contained data.")

        if len(df_cleaned.columns) == 0 and len(df_original.columns) > 0:
            errors.append("Cleaned dataset has 0 columns while original dataset contained columns.")

        # Check row drop percentage
        if len(df_original) > 0:
            drop_ratio = (len(df_original) - len(df_cleaned)) / len(df_original)
            if drop_ratio > 0.5:
                warnings.append(f"Significant row reduction: {drop_ratio*100:.1f}% of rows were removed.")

        report_after = DataProfiler.profile_dataset(df_cleaned)

        missing_before = int(df_original.isna().sum().sum())
        missing_after = int(df_cleaned.isna().sum().sum())
        missing_resolved = missing_before - missing_after

        score_improvement = round(report_after.overall_quality_score - report_before.overall_quality_score, 1)

        return CleaningValidationSummary(
            is_valid=len(errors) == 0,
            warnings=warnings,
            errors=errors,
            rows_before=len(df_original),
            rows_after=len(df_cleaned),
            rows_change=len(df_cleaned) - len(df_original),
            cols_before=len(df_original.columns),
            cols_after=len(df_cleaned.columns),
            cols_change=len(df_cleaned.columns) - len(df_original.columns),
            missing_before=missing_before,
            missing_after=missing_after,
            missing_resolved=missing_resolved,
            score_before=report_before.overall_quality_score,
            score_after=report_after.overall_quality_score,
            score_improvement=score_improvement,
        )
