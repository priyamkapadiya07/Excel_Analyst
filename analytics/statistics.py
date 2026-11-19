"""
Statistical analysis engine.
Provides descriptive statistics, group aggregation, correlation matrices,
top/bottom performers, and time trends without executing arbitrary code.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np


class StatisticsEngine:
    """Predefined and safe analytical operations on DataFrames."""

    @staticmethod
    def get_descriptive_stats(df: pd.DataFrame) -> Dict[str, Any]:
        """Comprehensive summary for numeric, categorical, and datetime columns."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "string", "category", "bool"]).columns.tolist()
        date_cols = [c for c in df.columns if "date" in str(c).lower() or pd.api.types.is_datetime64_any_dtype(df[c])]

        summary: Dict[str, Any] = {
            "numeric_summary": None,
            "categorical_summary": None,
            "numeric_columns": numeric_cols,
            "categorical_columns": cat_cols,
            "date_columns": date_cols,
        }

        if numeric_cols:
            desc = df[numeric_cols].describe().T
            desc["median"] = df[numeric_cols].median()
            desc["skew"] = df[numeric_cols].skew()
            summary["numeric_summary"] = desc.round(2)

        if cat_cols:
            cat_summary = []
            for c in cat_cols:
                top_val = df[c].mode().iloc[0] if not df[c].mode().empty else "N/A"
                cat_summary.append({
                    "Column": c,
                    "Unique Count": df[c].nunique(),
                    "Top Value": top_val,
                    "Top Frequency": (df[c] == top_val).sum(),
                    "Missing": df[c].isna().sum(),
                })
            summary["categorical_summary"] = pd.DataFrame(cat_summary)

        return summary

    @staticmethod
    def filter_records(
        df: pd.DataFrame,
        conditions: List[Dict[str, Any]],
        sort_by: Optional[str] = None,
        ascending: bool = False,
    ) -> pd.DataFrame:
        """
        Safely filters rows based on validated structured conditions.
        conditions example: [{'column': 'Salary', 'operator': 'high'}, {'column': 'Performance_Rating', 'operator': 'low'}]
        """
        mask = pd.Series(True, index=df.index)

        for cond in conditions:
            col = cond.get("column")
            if not col or col not in df.columns:
                continue
            op = cond.get("operator", "==")
            val = cond.get("value")

            s = df[col]
            if op in ("high", "above_median"):
                num_s = pd.to_numeric(s, errors="coerce")
                threshold = num_s.median() if pd.notna(num_s.median()) else 0
                mask = mask & (num_s >= threshold)
            elif op in ("low", "below_median"):
                num_s = pd.to_numeric(s, errors="coerce")
                threshold = num_s.median() if pd.notna(num_s.median()) else 0
                mask = mask & (num_s <= threshold)
            elif op == ">":
                num_s = pd.to_numeric(s, errors="coerce")
                mask = mask & (num_s > float(val))
            elif op == ">=":
                num_s = pd.to_numeric(s, errors="coerce")
                mask = mask & (num_s >= float(val))
            elif op == "<":
                num_s = pd.to_numeric(s, errors="coerce")
                mask = mask & (num_s < float(val))
            elif op == "<=":
                num_s = pd.to_numeric(s, errors="coerce")
                mask = mask & (num_s <= float(val))
            elif op == "==":
                mask = mask & (s.astype(str).str.strip().str.lower() == str(val).strip().lower())
            elif op == "!=":
                mask = mask & (s.astype(str).str.strip().str.lower() != str(val).strip().lower())
            elif op == "contains":
                mask = mask & (s.astype(str).str.contains(str(val), case=False, na=False))

        filtered = df[mask].copy()
        if sort_by and sort_by in filtered.columns:
            filtered = filtered.sort_values(by=sort_by, ascending=ascending)
        return filtered

    @staticmethod
    def aggregate_by_group(
        df: pd.DataFrame,
        group_col: str,
        metric_col: str,
        agg_func: str = "sum",
    ) -> pd.DataFrame:
        """Groups by a categorical column and aggregates a numeric column."""
        if group_col not in df.columns or metric_col not in df.columns:
            raise ValueError(f"Columns '{group_col}' or '{metric_col}' not found.")

        valid_funcs = {"sum": "sum", "mean": "mean", "count": "count", "min": "min", "max": "max", "median": "median"}
        func = valid_funcs.get(agg_func.lower(), "sum")

        clean_series = pd.to_numeric(df[metric_col], errors="coerce")
        temp_df = pd.DataFrame({group_col: df[group_col], metric_col: clean_series})

        grouped = temp_df.groupby(group_col)[metric_col].agg(func).reset_index()
        grouped.columns = [group_col, f"{metric_col}_{func}"]
        return grouped.sort_values(by=f"{metric_col}_{func}", ascending=False)

    @staticmethod
    def get_top_bottom_performers(
        df: pd.DataFrame,
        entity_col: str,
        metric_col: str,
        n: int = 5,
        ascending: bool = False,
    ) -> pd.DataFrame:
        """Returns top or bottom N entities by metric."""
        if entity_col not in df.columns or metric_col not in df.columns:
            raise ValueError(f"Columns '{entity_col}' or '{metric_col}' not found.")

        clean_series = pd.to_numeric(df[metric_col], errors="coerce")
        temp_df = pd.DataFrame({entity_col: df[entity_col], metric_col: clean_series})
        grouped = temp_df.groupby(entity_col)[metric_col].sum().reset_index()
        sorted_df = grouped.sort_values(by=metric_col, ascending=ascending)
        return sorted_df.head(n)

    @staticmethod
    def compute_correlation_matrix(df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], List[Dict[str, Any]]]:
        """Calculates correlation matrix and identifies top correlated pairs."""
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] < 2:
            return None, []

        corr = numeric_df.corr().round(3)

        pairs = []
        cols = corr.columns
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                c1, c2 = cols[i], cols[j]
                val = corr.loc[c1, c2]
                if not pd.isna(val):
                    pairs.append({
                        "Feature 1": c1,
                        "Feature 2": c2,
                        "Correlation": float(val),
                        "Abs_Correlation": abs(float(val)),
                    })

        pairs = sorted(pairs, key=lambda x: x["Abs_Correlation"], reverse=True)
        return corr, pairs

    @staticmethod
    def analyze_trend(
        df: pd.DataFrame,
        date_col: str,
        metric_col: str,
        period: str = "ME",  # ME: Month End, W: Weekly, D: Daily
    ) -> pd.DataFrame:
        """Resamples or aggregates numerical metric across date periods."""
        if date_col not in df.columns or metric_col not in df.columns:
            raise ValueError(f"Columns '{date_col}' or '{metric_col}' not found.")

        temp_df = pd.DataFrame({
            "date": pd.to_datetime(df[date_col], errors="coerce"),
            "metric": pd.to_numeric(df[metric_col], errors="coerce"),
        }).dropna()

        if len(temp_df) == 0:
            return pd.DataFrame(columns=["Period", "Value"])

        temp_df = temp_df.set_index("date")
        resampled = temp_df["metric"].resample(period).sum().reset_index()
        resampled.columns = ["Period", f"{metric_col}_Sum"]
        resampled["Period"] = resampled["Period"].dt.strftime("%Y-%m-%d")
        return resampled
