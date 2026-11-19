"""
Prompt builder for AI Cleaning Assistant.
Constructs prompt using only aggregated dataset metadata and detected issues.
Never includes complete raw dataset to ensure privacy.
"""

from typing import Dict, Any, List
import json
from core.data_profiler import DatasetQualityReport


def build_cleaning_questions_prompt(report: DatasetQualityReport, sheet_name: str) -> str:
    """Build a prompt containing only metadata, schema, and issue summaries."""
    # Summarize column metadata
    columns_summary = []
    for col, profile in report.column_profiles.items():
        columns_summary.append({
            "name": col,
            "type": profile.inferred_type,
            "missing_count": profile.missing_count,
            "missing_pct": profile.missing_percentage,
            "issues": [iss.issue_type for iss in profile.issues]
        })

    # Summarize issues without sending private raw records
    issues_payload = []
    for issue in report.all_issues:
        issues_payload.append({
            "issue_type": issue.issue_type,
            "column": issue.column,
            "severity": issue.severity,
            "count": issue.count,
            "percentage": issue.percentage,
            "sample_values": issue.sample_values[:3] if issue.sample_values else []
        })

    metadata_payload = {
        "sheet_name": sheet_name,
        "total_rows": report.total_rows,
        "total_columns": report.total_columns,
        "quality_score": report.overall_quality_score,
        "duplicate_rows": report.duplicate_rows_count,
        "empty_rows": report.empty_rows_count,
        "empty_columns": report.empty_columns_count,
        "columns": columns_summary,
        "detected_issues": issues_payload
    }

    prompt = f"""
You are an expert Data Cleaning and Data Quality Specialist.
Below is the aggregated metadata and detected quality issues for a spreadsheet dataset:

```json
{json.dumps(metadata_payload, indent=2)}
```

Generate a structured set of actionable, non-destructive cleaning decision questions for the user.
For each detected issue, explain the trade-offs and provide concrete, selectable options (e.g., drop, impute median/mean, standardize, ignore).

You MUST respond strictly with valid JSON conforming to this exact schema:
{{
  "questions": [
    {{
      "id": "q1",
      "issue_type": "Missing Values",
      "column": "Sales_Amount",
      "question": "How should missing values in 'Sales_Amount' be handled?",
      "severity": "high",
      "recommendation": "Impute with median value",
      "options": [
        {{"label": "Impute with median", "action": "impute_median", "default": true}},
        {{"label": "Impute with mean", "action": "impute_mean"}},
        {{"label": "Drop rows with missing Sales_Amount", "action": "drop_rows"}},
        {{"label": "Leave unchanged", "action": "ignore"}}
      ]
    }}
  ]
}}
Do not include any Markdown wrap or additional explanations outside the JSON object.
"""
    return prompt.strip()
