"""
Data Cleaning Engine.
Executes non-destructive, atomic cleaning operations on DataFrames,
maintains audit logs, and supports undo/reset history.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
import re
from utils.cleaning_log import CleaningLogger


class DataCleaner:
    """Provides pure transformations on copies of DataFrames."""

    def __init__(self, logger: Optional[CleaningLogger] = None):
        self.logger = logger or CleaningLogger()

    # --- Atomic Operations ---

    def drop_duplicates(self, df: pd.DataFrame, subset: Optional[List[str]] = None) -> pd.DataFrame:
        df_copy = df.copy()
        before_count = len(df_copy)
        df_cleaned = df_copy.drop_duplicates(subset=subset, keep="first")
        removed = before_count - len(df_cleaned)
        if removed > 0:
            self.logger.log("drop_duplicates", f"Removed {removed} duplicate row(s)", affected_count=removed)
        return df_cleaned

    def drop_empty_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()
        before_count = len(df_copy)
        df_cleaned = df_copy.dropna(how="all")
        removed = before_count - len(df_cleaned)
        if removed > 0:
            self.logger.log("drop_empty_rows", f"Dropped {removed} completely blank row(s)", affected_count=removed)
        return df_cleaned

    def drop_empty_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df_copy = df.copy()
        before_count = len(df_copy.columns)
        df_cleaned = df_copy.dropna(how="all", axis=1)
        removed = before_count - len(df_cleaned.columns)
        if removed > 0:
            self.logger.log("drop_empty_columns", f"Dropped {removed} completely empty column(s)", affected_count=removed)
        return df_cleaned

    def trim_whitespace(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        if column not in df.columns:
            return df
        df_copy = df.copy()
        series = df_copy[column]
        if series.dtype == "object" or pd.api.types.is_string_dtype(series):
            # Clean: strip leading/trailing, collapse internal whitespace
            cleaned = series.apply(
                lambda val: re.sub(r"\s+", " ", str(val).strip()) if pd.notna(val) else val
            )
            changes = (series != cleaned).sum()
            df_copy[column] = cleaned
            if changes > 0:
                self.logger.log("trim_whitespace", f"Normalized whitespace for {changes} cells", column=column, affected_count=changes)
        return df_copy

    def standardize_text_casing(self, df: pd.DataFrame, column: str, style: str = "title") -> pd.DataFrame:
        if column not in df.columns:
            return df
        df_copy = df.copy()
        series = df_copy[column]
        if series.dtype == "object" or pd.api.types.is_string_dtype(series):
            if style == "upper":
                cleaned = series.apply(lambda val: str(val).upper() if pd.notna(val) else val)
            elif style == "lower":
                cleaned = series.apply(lambda val: str(val).lower() if pd.notna(val) else val)
            else:  # title
                cleaned = series.apply(lambda val: str(val).title() if pd.notna(val) else val)

            changes = (series != cleaned).sum()
            df_copy[column] = cleaned
            if changes > 0:
                self.logger.log("standardize_casing", f"Converted casing to {style} for {changes} cells", column=column, affected_count=changes)
        return df_copy

    def impute_missing(self, df: pd.DataFrame, column: str, strategy: str = "median") -> pd.DataFrame:
        if column not in df.columns:
            return df
        df_copy = df.copy()
        series = df_copy[column]
        missing_count = int(series.isna().sum())
        if missing_count == 0:
            return df_copy

        if strategy == "median":
            num_series = pd.to_numeric(series, errors="coerce")
            fill_val = num_series.median()
            df_copy[column] = series.fillna(fill_val)
            desc = f"Imputed {missing_count} missing cells with median ({fill_val:.2f})"
        elif strategy == "mean":
            num_series = pd.to_numeric(series, errors="coerce")
            fill_val = num_series.mean()
            df_copy[column] = series.fillna(fill_val)
            desc = f"Imputed {missing_count} missing cells with mean ({fill_val:.2f})"
        elif strategy == "mode":
            mode_series = series.mode()
            fill_val = mode_series[0] if len(mode_series) > 0 else "Unknown"
            df_copy[column] = series.fillna(fill_val)
            desc = f"Imputed {missing_count} missing cells with mode ('{fill_val}')"
        elif strategy == "fill_zero":
            df_copy[column] = series.fillna(0)
            desc = f"Filled {missing_count} missing cells with 0"
        elif strategy == "fill_unknown":
            df_copy[column] = series.fillna("Unknown")
            desc = f"Filled {missing_count} missing cells with 'Unknown'"
        elif strategy == "drop_rows":
            df_copy = df_copy.dropna(subset=[column])
            desc = f"Dropped {missing_count} rows with missing {column}"
        else:
            return df_copy

        self.logger.log("impute_missing", desc, column=column, affected_count=missing_count)
        return df_copy

    def coerce_dates(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        if column not in df.columns:
            return df
        df_copy = df.copy()
        before_series = df_copy[column]
        converted = pd.to_datetime(before_series, errors="coerce")
        # Format as standard YYYY-MM-DD string or datetime
        df_copy[column] = converted.dt.strftime("%Y-%m-%d")
        # Invalid converted to NaN
        invalid_count = int(converted.isna().sum() - before_series.isna().sum())
        self.logger.log("coerce_dates", f"Coerced dates to YYYY-MM-DD ({invalid_count} unparseable set to NaN)", column=column, affected_count=len(df_copy))
        return df_copy

    def drop_invalid_dates(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        if column not in df.columns:
            return df
        df_copy = df.copy()
        converted = pd.to_datetime(df_copy[column], errors="coerce")
        # Drop rows where original was not null but datetime coercion failed
        invalid_mask = df_copy[column].notna() & converted.isna()
        dropped = int(invalid_mask.sum())
        df_cleaned = df_copy[~invalid_mask]
        if dropped > 0:
            self.logger.log("drop_invalid_dates", f"Dropped {dropped} row(s) with invalid dates", column=column, affected_count=dropped)
        return df_cleaned

    def cap_outliers_iqr(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        if column not in df.columns or pd.api.types.is_bool_dtype(df[column]):
            return df
        df_copy = df.copy()
        num_series = pd.to_numeric(df_copy[column], errors="coerce")
        valid = num_series.dropna()
        if len(valid) < 4:
            return df_copy

        q25 = valid.quantile(0.25)
        q75 = valid.quantile(0.75)
        iqr = q75 - q25
        if iqr == 0:
            return df_copy

        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr

        outlier_mask = (num_series < lower_bound) | (num_series > upper_bound)
        capped_count = int(outlier_mask.sum())
        if capped_count > 0:
            df_copy[column] = num_series.clip(lower=lower_bound, upper=upper_bound)
            self.logger.log("cap_outliers", f"Winsorized/capped {capped_count} outlier(s) to [{lower_bound:.2f}, {upper_bound:.2f}]", column=column, affected_count=capped_count)

        return df_copy

    def drop_outlier_rows(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        if column not in df.columns or pd.api.types.is_bool_dtype(df[column]):
            return df
        df_copy = df.copy()
        num_series = pd.to_numeric(df_copy[column], errors="coerce")
        valid = num_series.dropna()
        if len(valid) < 4:
            return df_copy

        q25 = valid.quantile(0.25)
        q75 = valid.quantile(0.75)
        iqr = q75 - q25
        if iqr == 0:
            return df_copy

        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr

        outlier_mask = (num_series < lower_bound) | (num_series > upper_bound)
        dropped_count = int(outlier_mask.sum())
        df_cleaned = df_copy[~outlier_mask]
        if dropped_count > 0:
            self.logger.log("drop_outlier_rows", f"Dropped {dropped_count} row(s) containing outliers", column=column, affected_count=dropped_count)
        return df_cleaned

    # --- Batch Decision Orchestration ---

    def execute_cleaning_decisions(
        self,
        df: pd.DataFrame,
        decisions: Dict[str, Dict[str, Any]],
    ) -> pd.DataFrame:
        """
        Executes a set of user decisions on a working copy in verified logical order.
        """
        working_df = df.copy()

        # Step 1: Whitespace & Casing first (to improve grouping and duplication detection)
        for d in decisions.values():
            action = d.get("action")
            col = d.get("column")
            if action == "trim_whitespace" and col:
                working_df = self.trim_whitespace(working_df, col)
            elif action == "to_title_case" and col:
                working_df = self.standardize_text_casing(working_df, col, "title")
            elif action == "to_upper" and col:
                working_df = self.standardize_text_casing(working_df, col, "upper")
            elif action == "to_lower" and col:
                working_df = self.standardize_text_casing(working_df, col, "lower")

        # Step 2: Empty rows and columns
        for d in decisions.values():
            action = d.get("action")
            if action == "drop_empty_rows":
                working_df = self.drop_empty_rows(working_df)
            elif action == "drop_empty_columns":
                working_df = self.drop_empty_columns(working_df)

        # Step 3: Duplicate rows
        for d in decisions.values():
            action = d.get("action")
            if action == "drop_duplicates":
                working_df = self.drop_duplicates(working_df)

        # Step 4: Dates
        for d in decisions.values():
            action = d.get("action")
            col = d.get("column")
            if action == "coerce_dates" and col:
                working_df = self.coerce_dates(working_df, col)
            elif action == "drop_invalid_dates" and col:
                working_df = self.drop_invalid_dates(working_df, col)

        # Step 5: Outliers
        for d in decisions.values():
            action = d.get("action")
            col = d.get("column")
            if action == "cap_outliers" and col:
                working_df = self.cap_outliers_iqr(working_df, col)
            elif action == "drop_outlier_rows" and col:
                working_df = self.drop_outlier_rows(working_df, col)

        # Step 6: Missing values
        for d in decisions.values():
            action = d.get("action")
            col = d.get("column")
            if not col:
                continue
            if action == "impute_median":
                working_df = self.impute_missing(working_df, col, "median")
            elif action == "impute_mean":
                working_df = self.impute_missing(working_df, col, "mean")
            elif action == "impute_mode":
                working_df = self.impute_missing(working_df, col, "mode")
            elif action == "fill_zero":
                working_df = self.impute_missing(working_df, col, "fill_zero")
            elif action == "fill_unknown":
                working_df = self.impute_missing(working_df, col, "fill_unknown")
            elif action == "drop_rows":
                working_df = self.impute_missing(working_df, col, "drop_rows")

        return working_df
