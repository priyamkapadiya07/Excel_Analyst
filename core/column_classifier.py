"""
Column Semantic Profiler & Classifier.
Intelligently classifies dataset columns into semantic roles:
- IDENTIFIER: IDs, codes, invoice numbers, keys, phone numbers, postal codes.
- MEASURE: Quantitative measurements, financial totals, quantities, ratings.
- DIMENSION: Categorical attributes, categories, departments, segments, statuses.
- TEMPORAL: Dates, timestamps, periods.

Supports both AI-driven contextual classification and deterministic local heuristics.
"""

from typing import Dict, Any, List, Optional
import re
import pandas as pd
import numpy as np
from ai.ai_client import AIClient


# Common regex patterns for identifiers
IDENTIFIER_PATTERNS = [
    r"(?:^|_)id$",
    r"^id(?:_|$)",
    r"(?:^|_)no$",
    r"(?:^|_)num$",
    r"(?:^|_)number$",
    r"(?:^|_)code$",
    r"(?:^|_)ref$",
    r"(?:^|_)reference$",
    r"(?:^|_)key$",
    r"^ssn$",
    r"^zip(?:_code)?$",
    r"^postal(?:_code)?$",
    r"phone",
    r"fax",
    r"account(?:_num|_number|_no)?$",
    r"transaction(?:_id|_no|_num)?$",
    r"invoice(?:_id|_no|_num)?$",
    r"order(?:_id|_no|_num)?$",
    r"customer_id",
    r"product_id",
    r"^sku$",
    r"emp(?:loyee)?(?:_id|_no)?$",
]

# Business measure keywords (for prioritization in KPIs and charts)
MEASURE_PRIORITY_KEYWORDS = [
    "revenue", "sales", "amount", "cost", "profit", "margin",
    "price", "total", "net", "gross", "quantity", "volume",
    "salary", "budget", "spend", "balance", "discount", "fee", "rate"
]


class ColumnClassifier:
    """Classifies DataFrame columns into semantic analytical roles."""

    @classmethod
    def is_identifier(cls, col_name: str, series: pd.Series) -> bool:
        """Determines if a column is an identifier, key, or reference code."""
        c_clean = col_name.strip().lower()

        # 1. Regex name match check
        for pat in IDENTIFIER_PATTERNS:
            if re.search(pat, c_clean):
                return True

        # 2. Integer or text series with high cardinality (near 100% unique)
        non_null = series.dropna()
        if len(non_null) > 10:
            uniq_ratio = non_null.nunique() / len(non_null)
            # If virtually every row is unique and name contains key words
            if uniq_ratio > 0.95 and any(term in c_clean for term in ["key", "id", "num", "hash", "guid", "uuid"]):
                return True

        return False

    @classmethod
    def classify_column(cls, col_name: str, series: pd.Series) -> str:
        """
        Classifies a single column into:
        'IDENTIFIER', 'MEASURE', 'DIMENSION', or 'TEMPORAL'
        """
        c_clean = col_name.strip().lower()

        # Check temporal
        if (
            "date" in c_clean
            or "time" in c_clean
            or "year" in c_clean
            or "month" in c_clean
            or pd.api.types.is_datetime64_any_dtype(series)
        ):
            # Verify if parseable as dates or explicitly datetime
            if pd.api.types.is_datetime64_any_dtype(series):
                return "TEMPORAL"
            try:
                sample = series.dropna().head(20)
                if len(sample) > 0 and pd.to_datetime(sample, errors="coerce").notna().mean() > 0.7:
                    return "TEMPORAL"
            except Exception:
                pass

        # Check identifier
        if cls.is_identifier(col_name, series):
            return "IDENTIFIER"

        # Check numeric measures vs dimensions
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            # Check if it's a binary flag (0/1) or boolean masquerading as int
            non_null = series.dropna()
            unique_vals = set(non_null.unique()[:10]) if len(non_null) > 0 else set()
            if unique_vals.issubset({0, 1, 0.0, 1.0}) and len(non_null) > 5:
                return "DIMENSION"

            # Otherwise numeric is a true quantitative measure
            return "MEASURE"

        # Categorical / Text
        return "DIMENSION"

    @classmethod
    def classify_dataframe(cls, df: pd.DataFrame, use_ai: bool = False, ai_client: Optional[AIClient] = None) -> Dict[str, str]:
        """
        Returns a mapping of column_name -> semantic_role.
        Supports optional AI enhancement if available.
        """
        classification = {}
        for col in df.columns:
            classification[col] = cls.classify_column(col, df[col])

        # Optional AI refinement if LLM API is active and configured
        if use_ai and ai_client and ai_client.api_key and ai_client.api_key != "your_gemini_api_key_here":
            try:
                prompt_meta = []
                for c in df.columns:
                    sample = [str(x) for x in df[c].dropna().head(3).tolist()]
                    prompt_meta.append(f"- {c} ({df[c].dtype}): samples={sample}")
                prompt = f"""
Classify each dataset column into exactly one semantic category:
IDENTIFIER (ID, key, code, invoice number, phone, zip)
MEASURE (numeric amount, financial, revenue, cost, quantity, rating, measurement)
DIMENSION (categorical category, name, department, status, segment)
TEMPORAL (date, timestamp)

Columns:
{chr(10).join(prompt_meta)}

Respond ONLY with a JSON mapping {{"column_name": "IDENTIFIER|MEASURE|DIMENSION|TEMPORAL"}}.
"""
                ai_resp = ai_client.generate_json_response(prompt)
                valid_roles = {"IDENTIFIER", "MEASURE", "DIMENSION", "TEMPORAL"}
                for k, v in ai_resp.items():
                    if k in classification and str(v).upper() in valid_roles:
                        classification[k] = str(v).upper()
            except Exception:
                pass  # Safely retain deterministic heuristic classification

        return classification

    @classmethod
    def get_measure_columns(cls, df: pd.DataFrame) -> List[str]:
        """Returns numeric measurement columns, sorted with business metrics first."""
        roles = cls.classify_dataframe(df)
        measures = [c for c, r in roles.items() if r == "MEASURE"]

        # Sort priority business keywords first
        def priority_score(c: str) -> int:
            clean = c.lower()
            for idx, kw in enumerate(MEASURE_PRIORITY_KEYWORDS):
                if kw in clean:
                    return idx
            return 999

        return sorted(measures, key=priority_score)

    @classmethod
    def get_identifier_columns(cls, df: pd.DataFrame) -> List[str]:
        """Returns all identifier columns (IDs, invoice numbers, keys)."""
        roles = cls.classify_dataframe(df)
        return [c for c, r in roles.items() if r == "IDENTIFIER"]

    @classmethod
    def get_dimension_columns(cls, df: pd.DataFrame) -> List[str]:
        """Returns categorical dimension columns for grouping."""
        roles = cls.classify_dataframe(df)
        return [c for c, r in roles.items() if r == "DIMENSION"]

    @classmethod
    def get_temporal_columns(cls, df: pd.DataFrame) -> List[str]:
        """Returns date and timestamp columns."""
        roles = cls.classify_dataframe(df)
        return [c for c, r in roles.items() if r == "TEMPORAL"]
