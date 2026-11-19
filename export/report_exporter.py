"""
HTML Report Exporter.
Generates an executive standalone HTML report with dataset health summaries,
cleaning audit logs, and data preview.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime
from core.data_profiler import DatasetQualityReport
from core.data_validator import CleaningValidationSummary


class ReportExporter:
    """Generates professional HTML audit and quality reports."""

    @classmethod
    def generate_html_report(
        cls,
        file_name: str,
        sheet_name: str,
        df: pd.DataFrame,
        report_before: Optional[DatasetQualityReport] = None,
        validation_summary: Optional[CleaningValidationSummary] = None,
        cleaning_log: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Metrics rows
        rows_val = f"{len(df):,}"
        cols_val = f"{len(df.columns)}"
        score_val = f"{validation_summary.score_after:.1f}/100" if validation_summary else "N/A"
        missing_val = f"{df.isna().sum().sum():,}"

        # Build table previews
        preview_table_html = df.head(10).to_html(classes="table", index=False)

        # Build log table
        log_html = "<p>No cleaning operations recorded.</p>"
        if cleaning_log:
            log_df = pd.DataFrame(cleaning_log)
            log_html = log_df.to_html(classes="table", index=False)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dataset Audit Report - {file_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 30px; color: #1e293b; background-color: #f8fafc; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        h1 {{ margin-top: 0; color: #0f172a; font-size: 24px; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }}
        h2 {{ color: #1e293b; font-size: 18px; margin-top: 30px; }}
        .meta {{ color: #64748b; font-size: 13px; margin-bottom: 24px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
        .metric-card {{ background: #f1f5f9; padding: 16px; border-radius: 6px; text-align: center; }}
        .metric-value {{ font-size: 22px; font-weight: bold; color: #2563eb; }}
        .metric-label {{ font-size: 12px; color: #64748b; text-transform: uppercase; margin-top: 4px; }}
        .table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }}
        .table th, .table td {{ border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; }}
        .table th {{ background-color: #f8fafc; font-weight: 600; color: #334155; }}
        .table tr:nth-child(even) {{ background-color: #fdfdfd; }}
        @media print {{ body {{ background: white; margin: 0; }} .container {{ box-shadow: none; padding: 0; }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 AI Excel Analyst — Dataset Audit Report</h1>
        <div class="meta">
            <strong>File:</strong> {file_name} &nbsp;|&nbsp; 
            <strong>Worksheet:</strong> {sheet_name} &nbsp;|&nbsp; 
            <strong>Generated:</strong> {timestamp}
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{rows_val}</div>
                <div class="metric-label">Total Rows</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{cols_val}</div>
                <div class="metric-label">Columns</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{missing_val}</div>
                <div class="metric-label">Missing Values</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{score_val}</div>
                <div class="metric-label">Health Score</div>
            </div>
        </div>

        <h2>📜 Applied Cleaning Operations</h2>
        {log_html}

        <h2>🔍 Data Sample (First 10 Rows)</h2>
        {preview_table_html}
    </div>
</body>
</html>
"""
        return html
