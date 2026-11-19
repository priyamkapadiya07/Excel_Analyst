"""
Data profiling and quality analysis engine.
Detects missing values, duplicates, whitespace issues, text inconsistencies,
type mismatches, invalid dates, outliers, empty rows/columns, and category anomalies.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
import re
import pandas as pd
import numpy as np


@dataclass
class IssueDetail:
    issue_type: str
    column: Optional[str]
    severity: str  # "high", "medium", "low", "info"
    count: int
    percentage: float
    description: str
    sample_values: List[Any] = field(default_factory=list)


@dataclass
class ColumnQualityProfile:
    column_name: str
    inferred_type: str
    total_count: int
    missing_count: int
    missing_percentage: float
    unique_count: int
    issues: List[IssueDetail] = field(default_factory=list)


@dataclass
class DatasetQualityReport:
    total_rows: int
    total_columns: int
    total_cells: int
    overall_quality_score: float  # 0 to 100
    grade: str  # A+, A, B, C, D, F
    issues_summary: Dict[str, int]
    column_profiles: Dict[str, ColumnQualityProfile]
    all_issues: List[IssueDetail]
    empty_rows_count: int
    empty_columns_count: int
    duplicate_rows_count: int
    duplicate_columns_count: int


class DataProfiler:
    """
    Analyzes a pandas DataFrame to generate comprehensive data-quality insights.
    """

    @staticmethod
    def calculate_quality_score(
        total_cells: int,
        missing_count: int,
        duplicate_rows: int,
        total_rows: int,
        severe_issues_count: int,
    ) -> Tuple[float, str]:
        """Compute 0-100 quality score and letter grade."""
        if total_cells == 0 or total_rows == 0:
            return 100.0, "A+"

        # Deductions
        missing_penalty = (missing_count / total_cells) * 40.0
        dup_penalty = (duplicate_rows / total_rows) * 30.0 if total_rows > 0 else 0
        issues_penalty = min(30.0, severe_issues_count * 2.5)

        score = max(0.0, min(100.0, 100.0 - (missing_penalty + dup_penalty + issues_penalty)))

        if score >= 95:
            grade = "A+"
        elif score >= 85:
            grade = "A"
        elif score >= 75:
            grade = "B"
        elif score >= 60:
            grade = "C"
        elif score >= 45:
            grade = "D"
        else:
            grade = "F"

        return round(score, 1), grade

    @classmethod
    def detect_empty_rows_and_cols(cls, df: pd.DataFrame) -> Tuple[int, int, List[str]]:
        """Identify completely empty rows and columns."""
        empty_rows = int(df.isna().all(axis=1).sum())
        empty_cols_mask = df.isna().all(axis=0)
        empty_cols_count = int(empty_cols_mask.sum())
        empty_cols_names = list(df.columns[empty_cols_mask])
        return empty_rows, empty_cols_count, empty_cols_names

    @classmethod
    def detect_whitespace_issues(cls, series: pd.Series) -> Tuple[int, List[str]]:
        """Detect leading/trailing or multiple consecutive internal whitespaces in string data."""
        # Convert to string series ignoring actual nulls
        valid_mask = series.notna()
        str_series = series[valid_mask].astype(str)

        problematic = []
        for val in str_series:
            # Check leading/trailing space or multiple consecutive whitespace
            if val != val.strip() or re.search(r"\s{2,}", val):
                problematic.append(val)

        return len(problematic), problematic[:5]

    @classmethod
    def detect_case_inconsistencies(cls, series: pd.Series) -> Tuple[int, List[Tuple[str, List[str]]]]:
        """
        Detect inconsistent casing for text columns (e.g. 'North', 'north', 'NORTH').
        Returns count and list of (standardized_val, [observed_variants]).
        """
        valid_mask = series.notna()
        str_series = series[valid_mask].astype(str).str.strip()

        # Group by lowercase
        groups: Dict[str, Set[str]] = {}
        for val in str_series:
            low = val.lower()
            if low not in groups:
                groups[low] = set()
            groups[low].add(val)

        inconsistent_groups = [
            (low, sorted(list(variants)))
            for low, variants in groups.items()
            if len(variants) > 1
        ]

        total_inconsistent_instances = 0
        lowered_series = series[valid_mask].astype(str).str.strip().str.lower()
        for low, _ in inconsistent_groups:
            total_inconsistent_instances += int((lowered_series == low).sum())

        return total_inconsistent_instances, inconsistent_groups[:5]

    @classmethod
    def detect_outliers_iqr(cls, series: pd.Series) -> Tuple[int, float, float, List[float]]:
        """
        Detect numerical outliers using the 1.5 * IQR standard method.
        """
        if pd.api.types.is_bool_dtype(series):
            return 0, 0.0, 0.0, []
        numeric_series = pd.to_numeric(series, errors="coerce").dropna()
        if len(numeric_series) < 4:
            return 0, 0.0, 0.0, []

        q25 = numeric_series.quantile(0.25)
        q75 = numeric_series.quantile(0.75)
        iqr = q75 - q25

        if iqr == 0:
            return 0, q25, q75, []

        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr

        outliers = numeric_series[(numeric_series < lower_bound) | (numeric_series > upper_bound)]
        return len(outliers), lower_bound, upper_bound, outliers.head(5).tolist()

    @classmethod
    def detect_date_issues(cls, series: pd.Series) -> Tuple[int, List[str]]:
        """
        Detect columns that look like dates but have unparseable values.
        """
        # Only inspect object/string columns with 'date', 'time', or common date patterns
        valid_series = series.dropna().astype(str)
        if len(valid_series) == 0:
            return 0, []

        # Heuristic: does column name contain 'date' or do sample values look like dates?
        date_pattern = re.compile(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})")
        sample_matches = sum(bool(date_pattern.search(val)) for val in valid_series.head(20))

        is_likely_date_col = "date" in str(series.name).lower() or (sample_matches >= max(2, len(valid_series.head(20)) * 0.4))
        if not is_likely_date_col:
            return 0, []

        # Try parsing
        invalid_dates = []
        for val in valid_series:
            try:
                parsed = pd.to_datetime(val, errors="raise")
            except Exception:
                invalid_dates.append(val)

        return len(invalid_dates), invalid_dates[:5]

    @classmethod
    def detect_type_mismatches(cls, series: pd.Series) -> Tuple[int, str, List[str]]:
        """
        Detect numeric values stored as text (e.g., "$12.50", "1,200", "95%").
        """
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            return 0, "", []

        valid_vals = series.dropna().astype(str).str.strip()
        if len(valid_vals) == 0:
            return 0, "", []

        # Check currency / percentage / number-with-commas
        number_like_cleaned = valid_vals.str.replace(r"[\$,€,£,%]", "", regex=True).str.replace(",", "")
        numeric_converted = pd.to_numeric(number_like_cleaned, errors="coerce")
        successful_conversions = numeric_converted.notna().sum()

        if successful_conversions >= len(valid_vals) * 0.7:
            # High probability this column should be numeric
            unconverted = valid_vals[numeric_converted.isna()].tolist()
            return int(successful_conversions), "numeric", unconverted[:5]

        return 0, "", []

    @classmethod
    def profile_dataset(cls, df: pd.DataFrame) -> DatasetQualityReport:
        """
        Perform a thorough multi-dimensional data quality inspection.
        """
        total_rows, total_cols = df.shape
        total_cells = total_rows * total_cols

        all_issues: List[IssueDetail] = []
        issues_summary: Dict[str, int] = {
            "Missing Values": 0,
            "Duplicate Rows": 0,
            "Whitespace Errors": 0,
            "Case Inconsistencies": 0,
            "Outliers": 0,
            "Date Issues": 0,
            "Type Inconsistencies": 0,
            "Empty Rows / Cols": 0,
        }

        # 1. Duplicate Column Names
        col_names = [str(c) for c in df.columns]
        dup_cols = len(col_names) - len(set(col_names))
        if dup_cols > 0:
            all_issues.append(IssueDetail(
                issue_type="Duplicate Columns",
                column=None,
                severity="high",
                count=dup_cols,
                percentage=(dup_cols / total_cols * 100),
                description=f"Found {dup_cols} duplicate column names in the dataset.",
            ))

        # 2. Empty Rows & Empty Columns
        empty_rows, empty_cols, empty_col_names = cls.detect_empty_rows_and_cols(df)
        if empty_rows > 0:
            issues_summary["Empty Rows / Cols"] += empty_rows
            all_issues.append(IssueDetail(
                issue_type="Empty Rows",
                column=None,
                severity="medium",
                count=empty_rows,
                percentage=(empty_rows / total_rows * 100) if total_rows > 0 else 0,
                description=f"{empty_rows} rows are completely empty.",
            ))

        if empty_cols > 0:
            issues_summary["Empty Rows / Cols"] += empty_cols
            all_issues.append(IssueDetail(
                issue_type="Empty Columns",
                column=None,
                severity="medium",
                count=empty_cols,
                percentage=(empty_cols / total_cols * 100) if total_cols > 0 else 0,
                description=f"{empty_cols} columns are completely empty: {', '.join(empty_col_names)}.",
                sample_values=empty_col_names,
            ))

        # 3. Duplicate Rows
        dup_rows = int(df.duplicated().sum())
        if dup_rows > 0:
            issues_summary["Duplicate Rows"] = dup_rows
            all_issues.append(IssueDetail(
                issue_type="Duplicate Rows",
                column=None,
                severity="high",
                count=dup_rows,
                percentage=(dup_rows / total_rows * 100) if total_rows > 0 else 0,
                description=f"{dup_rows} exact duplicate rows detected in dataset.",
            ))

        # 4. Column-level Profiling
        column_profiles: Dict[str, ColumnQualityProfile] = {}
        total_missing_cells = 0

        for col in df.columns:
            series = df[col]
            missing_count = int(series.isna().sum())
            total_missing_cells += missing_count
            missing_pct = (missing_count / total_rows * 100) if total_rows > 0 else 0
            unique_count = int(series.nunique(dropna=True))

            profile = ColumnQualityProfile(
                column_name=str(col),
                inferred_type=str(series.dtype),
                total_count=total_rows,
                missing_count=missing_count,
                missing_percentage=round(missing_pct, 1),
                unique_count=unique_count,
            )

            # Missing values issue
            if missing_count > 0:
                issues_summary["Missing Values"] += missing_count
                severity = "high" if missing_pct > 30 else ("medium" if missing_pct > 5 else "low")
                iss = IssueDetail(
                    issue_type="Missing Values",
                    column=str(col),
                    severity=severity,
                    count=missing_count,
                    percentage=round(missing_pct, 1),
                    description=f"Column '{col}' has {missing_count} missing cells ({missing_pct:.1f}%).",
                )
                profile.issues.append(iss)
                all_issues.append(iss)

            # String/Object Column Specific Checks
            if series.dtype == "object" or pd.api.types.is_string_dtype(series):
                # Whitespace checks
                ws_count, ws_samples = cls.detect_whitespace_issues(series)
                if ws_count > 0:
                    issues_summary["Whitespace Errors"] += ws_count
                    iss = IssueDetail(
                        issue_type="Extra Whitespace",
                        column=str(col),
                        severity="low",
                        count=ws_count,
                        percentage=round(ws_count / total_rows * 100, 1) if total_rows > 0 else 0,
                        description=f"Found {ws_count} values with leading, trailing, or double whitespace.",
                        sample_values=ws_samples,
                    )
                    profile.issues.append(iss)
                    all_issues.append(iss)

                # Inconsistent text case checks
                case_count, case_groups = cls.detect_case_inconsistencies(series)
                if case_groups:
                    issues_summary["Case Inconsistencies"] += len(case_groups)
                    sample_desc = [f"'{grp[0]}': {grp[1]}" for grp in case_groups[:3]]
                    iss = IssueDetail(
                        issue_type="Inconsistent Text Casing",
                        column=str(col),
                        severity="medium",
                        count=len(case_groups),
                        percentage=round(case_count / total_rows * 100, 1) if total_rows > 0 else 0,
                        description=f"Column '{col}' contains {len(case_groups)} category variant(s) with conflicting casing.",
                        sample_values=sample_desc,
                    )
                    profile.issues.append(iss)
                    all_issues.append(iss)

                # Date parsing check
                date_err_count, date_err_samples = cls.detect_date_issues(series)
                if date_err_count > 0:
                    issues_summary["Date Issues"] += date_err_count
                    iss = IssueDetail(
                        issue_type="Invalid Date Format",
                        column=str(col),
                        severity="high",
                        count=date_err_count,
                        percentage=round(date_err_count / total_rows * 100, 1) if total_rows > 0 else 0,
                        description=f"{date_err_count} values failed date parsing.",
                        sample_values=date_err_samples,
                    )
                    profile.issues.append(iss)
                    all_issues.append(iss)

                # Potential numeric disguised as text
                mismatch_count, target_type, unconverted = cls.detect_type_mismatches(series)
                if mismatch_count > 0:
                    issues_summary["Type Inconsistencies"] += 1
                    iss = IssueDetail(
                        issue_type="Incorrect Data Type",
                        column=str(col),
                        severity="medium",
                        count=mismatch_count,
                        percentage=round(mismatch_count / total_rows * 100, 1) if total_rows > 0 else 0,
                        description=f"Column '{col}' is stored as text but {mismatch_count} values represent numerical/currency data.",
                        sample_values=unconverted,
                    )
                    profile.issues.append(iss)
                    all_issues.append(iss)

            # Numeric Outlier Checks
            if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
                outlier_count, low, high, outlier_samples = cls.detect_outliers_iqr(series)
                if outlier_count > 0:
                    issues_summary["Outliers"] += outlier_count
                    iss = IssueDetail(
                        issue_type="Outliers",
                        column=str(col),
                        severity="low",
                        count=outlier_count,
                        percentage=round(outlier_count / total_rows * 100, 1) if total_rows > 0 else 0,
                        description=f"{outlier_count} potential outlier(s) beyond [{low:.2f}, {high:.2f}].",
                        sample_values=[round(x, 2) for x in outlier_samples],
                    )
                    profile.issues.append(iss)
                    all_issues.append(iss)

            column_profiles[str(col)] = profile

        # Quality Score & Grade
        severe_count = sum(1 for iss in all_issues if iss.severity in ("high", "medium"))
        score, grade = cls.calculate_quality_score(
            total_cells=total_cells,
            missing_count=total_missing_cells,
            duplicate_rows=dup_rows,
            total_rows=total_rows,
            severe_issues_count=severe_count,
        )

        return DatasetQualityReport(
            total_rows=total_rows,
            total_columns=total_cols,
            total_cells=total_cells,
            overall_quality_score=score,
            grade=grade,
            issues_summary=issues_summary,
            column_profiles=column_profiles,
            all_issues=all_issues,
            empty_rows_count=empty_rows,
            empty_columns_count=empty_cols,
            duplicate_rows_count=dup_rows,
            duplicate_columns_count=dup_cols,
        )
