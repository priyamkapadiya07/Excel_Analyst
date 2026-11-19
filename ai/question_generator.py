"""
Cleaning Question Generator.
Synthesizes detected data quality anomalies into structured user questions
using either the LLM API or deterministic expert rules.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd
from core.data_profiler import DatasetQualityReport
from core.column_classifier import ColumnClassifier
from ai.ai_client import AIClient
from ai.prompt_builder import build_cleaning_questions_prompt


@dataclass
class QuestionOption:
    label: str
    action: str
    is_default: bool = False
    param: Optional[Any] = None


@dataclass
class CleaningQuestion:
    id: str
    issue_type: str
    column: Optional[str]
    question: str
    severity: str
    recommendation: str
    options: List[QuestionOption] = field(default_factory=list)
    user_decision: Optional[str] = None  # chosen action label or id


class QuestionGenerator:
    """Generates and validates interactive cleaning questions."""

    def __init__(self, ai_client: Optional[AIClient] = None):
        self.ai_client = ai_client or AIClient()

    @staticmethod
    def generate_rule_based_questions(report: DatasetQualityReport) -> List[CleaningQuestion]:
        """Deterministic expert fallback when AI API is unavailable or offline."""
        questions: List[CleaningQuestion] = []
        q_idx = 1

        # 1. Duplicate Rows
        if report.duplicate_rows_count > 0:
            questions.append(CleaningQuestion(
                id=f"q_{q_idx}",
                issue_type="Duplicate Rows",
                column=None,
                question=f"Found {report.duplicate_rows_count} exact duplicate rows. How should these be handled?",
                severity="high",
                recommendation="Remove duplicate rows and keep only the first occurrence.",
                options=[
                    QuestionOption("Remove duplicate rows (keep first)", "drop_duplicates", is_default=True),
                    QuestionOption("Leave duplicates unchanged", "ignore"),
                ]
            ))
            q_idx += 1

        # 2. Empty Rows / Columns
        if report.empty_rows_count > 0:
            questions.append(CleaningQuestion(
                id=f"q_{q_idx}",
                issue_type="Empty Rows",
                column=None,
                question=f"Detected {report.empty_rows_count} completely blank rows. Remove them?",
                severity="medium",
                recommendation="Drop empty rows.",
                options=[
                    QuestionOption("Drop blank rows", "drop_empty_rows", is_default=True),
                    QuestionOption("Keep blank rows", "ignore"),
                ]
            ))
            q_idx += 1

        if report.empty_columns_count > 0:
            questions.append(CleaningQuestion(
                id=f"q_{q_idx}",
                issue_type="Empty Columns",
                column=None,
                question=f"Detected {report.empty_columns_count} completely empty columns. Drop these columns?",
                severity="medium",
                recommendation="Drop completely blank columns.",
                options=[
                    QuestionOption("Drop blank columns", "drop_empty_columns", is_default=True),
                    QuestionOption("Keep blank columns", "ignore"),
                ]
            ))
            q_idx += 1

        # 3. Column issues
        for col_name, profile in report.column_profiles.items():
            for issue in profile.issues:
                if issue.issue_type == "Missing Values":
                    # Check semantic role: Is this column an identifier/key?
                    dummy_series = pd.Series([1, 2, 3])
                    is_id = ColumnClassifier.is_identifier(col_name, dummy_series)

                    if is_id:
                        # Identifiers must NEVER be imputed with median or mean
                        opts = [
                            QuestionOption("Drop rows with missing identifier", "drop_rows", is_default=True),
                            QuestionOption("Leave missing IDs unchanged", "ignore"),
                        ]
                        rec = "Dropping rows with missing identifiers is recommended to prevent corrupted entity relations."
                    else:
                        is_numeric = "int" in profile.inferred_type or "float" in profile.inferred_type
                        if is_numeric:
                            opts = [
                                QuestionOption("Impute with median value", "impute_median", is_default=True),
                                QuestionOption("Impute with mean value", "impute_mean"),
                                QuestionOption("Drop rows with missing value", "drop_rows"),
                                QuestionOption("Fill with 0", "fill_zero"),
                                QuestionOption("Leave missing values unchanged", "ignore"),
                            ]
                            rec = "Impute with median value to preserve distribution without skewing outliers."
                        else:
                            opts = [
                                QuestionOption("Fill with 'Unknown'", "fill_unknown", is_default=True),
                                QuestionOption("Fill with most frequent value (mode)", "impute_mode"),
                                QuestionOption("Drop rows with missing value", "drop_rows"),
                                QuestionOption("Leave missing values unchanged", "ignore"),
                            ]
                            rec = "Fill missing text cells with 'Unknown'."

                    questions.append(CleaningQuestion(
                        id=f"q_{q_idx}",
                        issue_type="Missing Values",
                        column=col_name,
                        question=f"Column '{col_name}' has {issue.count} missing values ({issue.percentage:.1f}%). How to proceed?",
                        severity=issue.severity,
                        recommendation=rec,
                        options=opts,
                    ))
                    q_idx += 1

                elif issue.issue_type == "Extra Whitespace":
                    questions.append(CleaningQuestion(
                        id=f"q_{q_idx}",
                        issue_type="Extra Whitespace",
                        column=col_name,
                        question=f"Column '{col_name}' has {issue.count} values with leading, trailing, or double whitespace. Standardize?",
                        severity="low",
                        recommendation="Trim whitespace and collapse multiple spaces.",
                        options=[
                            QuestionOption("Strip and normalize whitespace", "trim_whitespace", is_default=True),
                            QuestionOption("Leave whitespace unchanged", "ignore"),
                        ]
                    ))
                    q_idx += 1

                elif issue.issue_type == "Inconsistent Text Casing":
                    questions.append(CleaningQuestion(
                        id=f"q_{q_idx}",
                        issue_type="Inconsistent Text Casing",
                        column=col_name,
                        question=f"Column '{col_name}' contains inconsistent letter casing across categories. How should text be standardized?",
                        severity="medium",
                        recommendation="Convert to Proper Title Case.",
                        options=[
                            QuestionOption("Convert to Title Case (e.g. 'North')", "to_title_case", is_default=True),
                            QuestionOption("Convert to UPPERCASE", "to_upper"),
                            QuestionOption("Convert to lowercase", "to_lower"),
                            QuestionOption("Leave casing unchanged", "ignore"),
                        ]
                    ))
                    q_idx += 1

                elif issue.issue_type == "Invalid Date Format":
                    questions.append(CleaningQuestion(
                        id=f"q_{q_idx}",
                        issue_type="Invalid Date Format",
                        column=col_name,
                        question=f"Column '{col_name}' has {issue.count} unparseable date values. How should they be handled?",
                        severity="high",
                        recommendation="Coerce to standard datetime and replace invalid entries with NaT (missing).",
                        options=[
                            QuestionOption("Convert valid dates, set invalid to NaT", "coerce_dates", is_default=True),
                            QuestionOption("Drop rows with invalid dates", "drop_invalid_dates"),
                            QuestionOption("Leave unchanged as raw text", "ignore"),
                        ]
                    ))
                    q_idx += 1

                elif issue.issue_type == "Outliers":
                    questions.append(CleaningQuestion(
                        id=f"q_{q_idx}",
                        issue_type="Outliers",
                        column=col_name,
                        question=f"Column '{col_name}' has {issue.count} statistical outlier(s). What action would you prefer?",
                        severity="low",
                        recommendation="Cap values to standard 1.5 IQR fences, or keep them for verification.",
                        options=[
                            QuestionOption("Cap values at IQR boundary (Winsorize)", "cap_outliers"),
                            QuestionOption("Keep outliers unchanged (Recommended for verification)", "ignore", is_default=True),
                            QuestionOption("Drop rows containing outliers", "drop_outlier_rows"),
                        ]
                    ))
                    q_idx += 1

        return questions

    def generate_questions(self, report: DatasetQualityReport, sheet_name: str = "Sheet1") -> List[CleaningQuestion]:
        """Generate questions via AI if available, falling back gracefully to rule-based engine."""
        if self.ai_client.api_key and self.ai_client.api_key != "your_gemini_api_key_here":
            try:
                prompt = build_cleaning_questions_prompt(report, sheet_name)
                response_json = self.ai_client.generate_json_response(prompt)
                questions_data = response_json.get("questions", [])

                parsed_questions = []
                for item in questions_data:
                    options = [
                        QuestionOption(
                            label=opt.get("label", ""),
                            action=opt.get("action", "ignore"),
                            is_default=opt.get("default", False)
                        )
                        for opt in item.get("options", [])
                    ]
                    parsed_questions.append(CleaningQuestion(
                        id=item.get("id", f"q_{len(parsed_questions)+1}"),
                        issue_type=item.get("issue_type", "Quality Issue"),
                        column=item.get("column"),
                        question=item.get("question", ""),
                        severity=item.get("severity", "medium"),
                        recommendation=item.get("recommendation", ""),
                        options=options
                    ))
                if parsed_questions:
                    return parsed_questions
            except Exception:
                # Fallback on any AI API or parsing failure
                pass

        return self.generate_rule_based_questions(report)
