"""
Dynamic Dashboard Builder.
Inspects arbitrary datasets and auto-configures KPI metrics and Plotly charts,
while supporting custom visualization authoring and HTML dashboard export.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from analytics.chart_generator import ChartGenerator
from core.column_classifier import ColumnClassifier


class DashboardBuilder:
    """Dynamically plans and renders analytical dashboards for any dataset."""

    @classmethod
    def get_auto_kpis(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Automatically identify key summary metrics, prioritizing true business measures."""
        kpis = [{"label": "Total Records", "value": f"{len(df):,}"}]

        measure_cols = ColumnClassifier.get_measure_columns(df)
        identifier_cols = ColumnClassifier.get_identifier_columns(df)
        dimension_cols = ColumnClassifier.get_dimension_columns(df)

        # 1. Primary business measurement totals or averages
        for col in measure_cols[:2]:
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(s) > 0:
                clean_name = col.replace("_", " ").title()
                if s.min() >= 0 and s.max() <= 1.0:
                    kpis.append({"label": f"Avg {clean_name}", "value": f"{s.mean()*100:.1f}%"})
                else:
                    kpis.append({"label": f"Total {clean_name}", "value": f"{s.sum():,.2f}"})

        # 2. Distinct Count for Key Identifier (e.g. Unique Customers, Unique Invoices)
        if identifier_cols:
            id_col = identifier_cols[0]
            clean_id_name = id_col.replace("_", " ").title()
            kpis.append({"label": f"Unique {clean_id_name}", "value": f"{df[id_col].nunique():,}"})
        elif dimension_cols:
            dim_col = dimension_cols[0]
            clean_dim_name = dim_col.replace("_", " ").title()
            kpis.append({"label": f"Unique {clean_dim_name}", "value": f"{df[dim_col].nunique():,}"})

        return kpis[:4]

    @classmethod
    def get_recommended_charts(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Dynamically generates tailored visualizations based on semantic column classifications."""
        charts = []
        measure_cols = ColumnClassifier.get_measure_columns(df)
        dimension_cols = ColumnClassifier.get_dimension_columns(df)
        temporal_cols = ColumnClassifier.get_temporal_columns(df)

        # Fallback to general numeric if no specific measures detected
        numeric_cols = measure_cols if measure_cols else df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = dimension_cols if dimension_cols else df.select_dtypes(include=["object", "string", "category"]).columns.tolist()

        # 1. Trend Line Chart if Date column exists
        if temporal_cols and numeric_cols:
            d_col = temporal_cols[0]
            m_col = numeric_cols[0]
            fig = ChartGenerator.create_line_chart(df, d_col, m_col, title=f"Trend of {m_col.replace('_', ' ').title()} over {d_col.replace('_', ' ').title()}")
            charts.append({"type": "line", "title": f"Trend of {m_col.replace('_', ' ').title()}", "figure": fig})

        # 2. Categorical Aggregation Bar Chart
        if cat_cols and numeric_cols:
            c_col = cat_cols[0]
            m_col = numeric_cols[0]
            fig = ChartGenerator.create_bar_chart(df, c_col, m_col, agg_func="sum", title=f"{m_col.replace('_', ' ').title()} by {c_col.replace('_', ' ').title()}")
            charts.append({"type": "bar", "title": f"{m_col.replace('_', ' ').title()} by {c_col.replace('_', ' ').title()}", "figure": fig})

        # 3. Categorical Share Donut Chart
        if cat_cols:
            c_col = cat_cols[0] if len(cat_cols) == 1 else cat_cols[1]
            val_col = numeric_cols[0] if numeric_cols else None
            fig = ChartGenerator.create_pie_chart(df, c_col, val_col, title=f"Share by {c_col.replace('_', ' ').title()}")
            charts.append({"type": "pie", "title": f"Share by {c_col.replace('_', ' ').title()}", "figure": fig})

        # 4. Distribution Histogram / Boxplot
        if numeric_cols:
            m_col = numeric_cols[0] if len(numeric_cols) == 1 else numeric_cols[1]
            c_col = cat_cols[0] if cat_cols else None
            fig = ChartGenerator.create_box_plot(df, m_col, c_col, title=f"Distribution of {m_col.replace('_', ' ').title()}")
            charts.append({"type": "box", "title": f"{m_col.replace('_', ' ').title()} Distribution", "figure": fig})

        # 5. Scatter Plot if 2+ numeric columns exist
        if len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            fig = ChartGenerator.create_scatter_plot(df, x_col, y_col, title=f"{y_col.replace('_', ' ').title()} vs {x_col.replace('_', ' ').title()}")
            charts.append({"type": "scatter", "title": f"{y_col.replace('_', ' ').title()} vs {x_col.replace('_', ' ').title()}", "figure": fig})

        return charts

    @classmethod
    def export_dashboard_html(cls, title: str, kpis: List[Dict[str, Any]], figures: List[go.Figure]) -> str:
        """Assembles a standalone interactive HTML dashboard file."""
        chart_divs = "".join(fig.to_html(full_html=False, include_plotlyjs="cdn") for fig in figures)

        kpi_cards_html = "".join(
            f"""
            <div style="background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center;">
                <div style="font-size: 12px; color: #64748b; text-transform: uppercase;">{kpi['label']}</div>
                <div style="font-size: 24px; font-weight: bold; color: #1e3a8a; margin-top: 4px;">{kpi['value']}</div>
            </div>
            """
            for kpi in kpis
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f8fafc; margin: 0; padding: 24px; color: #0f172a; }}
        .header {{ margin-bottom: 24px; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .charts-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px; }}
        .chart-card {{ background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 {title}</h1>
        <p style="color: #64748b; font-size: 14px;">Interactive Analytics Dashboard</p>
    </div>
    <div class="kpi-grid">
        {kpi_cards_html}
    </div>
    <div class="charts-grid">
        {chart_divs}
    </div>
</body>
</html>
"""
        return html
