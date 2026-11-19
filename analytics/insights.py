"""
Automated business insights generator.
Derives verifiable factual takeaways from statistical summaries without hallucination.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from analytics.statistics import StatisticsEngine
from core.column_classifier import ColumnClassifier


class InsightGenerator:
    """Generates concise, factual bulleted business insights."""

    @classmethod
    def generate_insights(cls, df: pd.DataFrame) -> List[str]:
        insights = []

        # 1. Dataset Dimensions & Completeness
        total_cells = df.size
        total_missing = int(df.isna().sum().sum())
        completeness = ((total_cells - total_missing) / total_cells * 100) if total_cells > 0 else 100.0
        insights.append(f"📊 **Data Completeness**: Dataset contains {len(df):,} records across {len(df.columns)} fields with {completeness:.1f}% overall cell completeness.")

        # 2. Key Business Measures (Bypassing identifiers like invoice_no, customer_id)
        measure_cols = ColumnClassifier.get_measure_columns(df)
        if len(measure_cols) > 0:
            for col in measure_cols[:2]:
                s = pd.to_numeric(df[col], errors="coerce").dropna()
                if len(s) > 0:
                    clean_name = col.replace("_", " ").title()
                    insights.append(
                        f"📈 **{clean_name}**: Averages {s.mean():,.2f} with a median of {s.median():,.2f} (ranging from {s.min():,.2f} to {s.max():,.2f})."
                    )

        # 3. Categorical Dominance / Dimensions
        dimension_cols = ColumnClassifier.get_dimension_columns(df)
        for col in dimension_cols[:2]:
            counts = df[col].dropna().value_counts()
            if len(counts) > 0:
                clean_dim = col.replace("_", " ").title()
                top_name = counts.index[0]
                top_pct = (counts.iloc[0] / len(df) * 100)
                insights.append(
                    f"🏷️ **{clean_dim} Distribution**: Leading category is '{top_name}' representing {top_pct:.1f}% of observations ({counts.iloc[0]:,} items)."
                )

        # 4. Key Identifiers Distinct Count
        id_cols = ColumnClassifier.get_identifier_columns(df)
        if id_cols:
            primary_id = id_cols[0]
            clean_id = primary_id.replace("_", " ").title()
            insights.append(
                f"🔑 **Unique Entities**: {clean_id} spans {df[primary_id].nunique():,} distinct values across {len(df):,} transactions."
            )

        # 5. Correlations across real business measures
        clean_df = df[[c for c in measure_cols if c in df.columns]] if len(measure_cols) >= 2 else df
        corr, pairs = StatisticsEngine.compute_correlation_matrix(clean_df)
        if pairs:
            top_pair = pairs[0]
            if top_pair["Abs_Correlation"] >= 0.5:
                direction = "positive" if top_pair["Correlation"] > 0 else "negative"
                insights.append(
                    f"🔗 **Strong Correlation**: Detected strong {direction} relationship between `{top_pair['Feature 1']}` and `{top_pair['Feature 2']}` ($r = {top_pair['Correlation']:.2f}$).",
                )

        return insights
