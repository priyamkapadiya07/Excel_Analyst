"""
Tests for StatisticsEngine and InsightGenerator (Phase 6).
"""

import pytest
import pandas as pd
import numpy as np
from analytics.statistics import StatisticsEngine
from analytics.insights import InsightGenerator


@pytest.fixture
def sample_sales_df():
    return pd.DataFrame({
        "Customer": ["Acme", "Globex", "Initech", "Umbrella", "Stark", "Wayne"],
        "Region": ["North", "South", "North", "East", "West", "North"],
        "Sales": [1000.0, 2500.0, 1500.0, 4000.0, 3200.0, 5000.0],
        "Quantity": [10, 25, 15, 40, 32, 50],
        "Order_Date": ["2026-01-05", "2026-01-15", "2026-02-10", "2026-02-20", "2026-03-05", "2026-03-15"],
    })


def test_descriptive_stats(sample_sales_df):
    stats = StatisticsEngine.get_descriptive_stats(sample_sales_df)
    assert stats["numeric_summary"] is not None
    assert "Sales" in stats["numeric_summary"].index
    assert "Quantity" in stats["numeric_summary"].index
    assert stats["categorical_summary"] is not None


def test_aggregate_by_group(sample_sales_df):
    grouped = StatisticsEngine.aggregate_by_group(sample_sales_df, "Region", "Sales", "sum")
    assert "Region" in grouped.columns
    assert "Sales_sum" in grouped.columns
    # Region North has 3 rows: 1000 + 1500 + 5000 = 7500
    north_sales = grouped[grouped["Region"] == "North"]["Sales_sum"].iloc[0]
    assert north_sales == 7500.0


def test_top_bottom_performers(sample_sales_df):
    top3 = StatisticsEngine.get_top_bottom_performers(sample_sales_df, "Customer", "Sales", n=3, ascending=False)
    assert len(top3) == 3
    assert top3["Customer"].iloc[0] == "Wayne"  # 5000.0

    bottom2 = StatisticsEngine.get_top_bottom_performers(sample_sales_df, "Customer", "Sales", n=2, ascending=True)
    assert len(bottom2) == 2
    assert bottom2["Customer"].iloc[0] == "Acme"  # 1000.0


def test_correlation_matrix(sample_sales_df):
    corr, pairs = StatisticsEngine.compute_correlation_matrix(sample_sales_df)
    assert corr is not None
    assert len(pairs) > 0
    # Perfect linear relation between Sales and Quantity (100x)
    assert pairs[0]["Correlation"] == 1.0


def test_insight_generator(sample_sales_df):
    insights = InsightGenerator.generate_insights(sample_sales_df)
    assert len(insights) >= 2
    assert any("Data Completeness" in i for i in insights)
