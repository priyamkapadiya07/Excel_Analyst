"""
Plotly Chart Generator.
Creates responsive, interactive charts tailored to dataset dimensions.
"""

from typing import Optional, List
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


class ChartGenerator:
    """Factory for interactive Plotly charts."""

    DEFAULT_THEME = "plotly_white"
    COLOR_SEQUENCE = px.colors.qualitative.Plotly

    @classmethod
    def create_bar_chart(
        cls,
        df: pd.DataFrame,
        x_col: str,
        y_col: Optional[str] = None,
        agg_func: str = "sum",
        title: Optional[str] = None,
        orientation: str = "v",
    ) -> go.Figure:
        """Bar chart: aggregated metric or frequency count."""
        if y_col and y_col in df.columns:
            agg_df = df.groupby(x_col)[y_col].agg(agg_func).reset_index()
            fig = px.bar(
                agg_df,
                x=x_col if orientation == "v" else y_col,
                y=y_col if orientation == "v" else x_col,
                title=title or f"{y_col} ({agg_func.title()}) by {x_col}",
                template=cls.DEFAULT_THEME,
                color_discrete_sequence=cls.COLOR_SEQUENCE,
                orientation=orientation,
            )
        else:
            counts = df[x_col].value_counts().reset_index()
            counts.columns = [x_col, "Count"]
            fig = px.bar(
                counts,
                x=x_col if orientation == "v" else "Count",
                y="Count" if orientation == "v" else x_col,
                title=title or f"Count of {x_col}",
                template=cls.DEFAULT_THEME,
                color_discrete_sequence=cls.COLOR_SEQUENCE,
                orientation=orientation,
            )
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        return fig

    @classmethod
    def create_line_chart(
        cls,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Line chart for trends over time or sequence."""
        temp_df = df.sort_values(by=x_col)
        fig = px.line(
            temp_df,
            x=x_col,
            y=y_col,
            title=title or f"{y_col} over {x_col}",
            markers=True,
            template=cls.DEFAULT_THEME,
            color_discrete_sequence=cls.COLOR_SEQUENCE,
        )
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        return fig

    @classmethod
    def create_pie_chart(
        cls,
        df: pd.DataFrame,
        names_col: str,
        values_col: Optional[str] = None,
        title: Optional[str] = None,
        hole: float = 0.4,
    ) -> go.Figure:
        """Pie / Donut chart showing category proportions."""
        if values_col and values_col in df.columns:
            fig = px.pie(
                df,
                names=names_col,
                values=values_col,
                hole=hole,
                title=title or f"Share of {values_col} by {names_col}",
                template=cls.DEFAULT_THEME,
                color_discrete_sequence=cls.COLOR_SEQUENCE,
            )
        else:
            counts = df[names_col].value_counts().reset_index()
            counts.columns = [names_col, "Count"]
            fig = px.pie(
                counts,
                names=names_col,
                values="Count",
                hole=hole,
                title=title or f"Distribution of {names_col}",
                template=cls.DEFAULT_THEME,
                color_discrete_sequence=cls.COLOR_SEQUENCE,
            )
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        return fig

    @classmethod
    def create_histogram(
        cls,
        df: pd.DataFrame,
        x_col: str,
        nbins: int = 20,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Histogram for numerical distribution."""
        fig = px.histogram(
            df,
            x=x_col,
            nbins=nbins,
            marginal="box",
            title=title or f"Distribution of {x_col}",
            template=cls.DEFAULT_THEME,
            color_discrete_sequence=cls.COLOR_SEQUENCE,
        )
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        return fig

    @classmethod
    def create_scatter_plot(
        cls,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        color_col: Optional[str] = None,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Scatter plot evaluating relationship between two numerical variables."""
        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            color=color_col if color_col in df.columns else None,
            title=title or f"{y_col} vs {x_col}",
            template=cls.DEFAULT_THEME,
            color_discrete_sequence=cls.COLOR_SEQUENCE,
        )
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        return fig

    @classmethod
    def create_box_plot(
        cls,
        df: pd.DataFrame,
        y_col: str,
        x_col: Optional[str] = None,
        title: Optional[str] = None,
    ) -> go.Figure:
        """Box plot for outlier and quartile analysis across categories."""
        fig = px.box(
            df,
            x=x_col if x_col in df.columns else None,
            y=y_col,
            points="all",
            title=title or f"Box Plot of {y_col}" + (f" by {x_col}" if x_col else ""),
            template=cls.DEFAULT_THEME,
            color_discrete_sequence=cls.COLOR_SEQUENCE,
        )
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
        return fig
