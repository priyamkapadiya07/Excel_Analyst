"""
Tests for ChartGenerator and DashboardBuilder (Phase 7).
"""

import pytest
import pandas as pd
import numpy as np
from analytics.chart_generator import ChartGenerator
from dashboard.dashboard_builder import DashboardBuilder


@pytest.fixture
def sales_df():
    return pd.DataFrame({
        "Customer": ["Acme", "Globex", "Initech", "Umbrella", "Stark"],
        "Region": ["North", "South", "North", "East", "West"],
        "Sales": [1200.0, 3400.0, 1800.0, 5000.0, 2900.0],
        "Quantity": [10, 25, 15, 45, 30],
        "Date": ["2026-01-01", "2026-01-15", "2026-02-01", "2026-02-15", "2026-03-01"]
    })


def test_chart_generator_types(sales_df):
    bar_fig = ChartGenerator.create_bar_chart(sales_df, "Region", "Sales")
    assert bar_fig is not None

    line_fig = ChartGenerator.create_line_chart(sales_df, "Date", "Sales")
    assert line_fig is not None

    pie_fig = ChartGenerator.create_pie_chart(sales_df, "Region", "Sales")
    assert pie_fig is not None

    hist_fig = ChartGenerator.create_histogram(sales_df, "Sales")
    assert hist_fig is not None

    scatter_fig = ChartGenerator.create_scatter_plot(sales_df, "Quantity", "Sales")
    assert scatter_fig is not None

    box_fig = ChartGenerator.create_box_plot(sales_df, "Sales", "Region")
    assert box_fig is not None


def test_dashboard_builder_auto_kpis_and_charts(sales_df):
    kpis = DashboardBuilder.get_auto_kpis(sales_df)
    assert len(kpis) >= 2
    assert any("Total Records" in k["label"] for k in kpis)

    charts = DashboardBuilder.get_recommended_charts(sales_df)
    assert len(charts) >= 3

    html = DashboardBuilder.export_dashboard_html(
        "Sales Analytics Dashboard",
        kpis,
        [c["figure"] for c in charts]
    )
    assert "<!DOCTYPE html>" in html
    assert "Sales Analytics Dashboard" in html
    assert "plotly" in html.lower()
