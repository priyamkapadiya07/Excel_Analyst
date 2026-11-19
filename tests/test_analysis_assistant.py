"""
Tests for AnalysisAssistant (Phase 6).
"""

import pytest
import pandas as pd
from ai.analysis_assistant import AnalysisAssistant, AnalysisIntent


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "Department": ["HR", "Engineering", "Engineering", "Sales"],
        "Salary": [60000, 100000, 120000, 80000],
        "Hire_Date": ["2023-01-01", "2022-05-01", "2021-03-01", "2024-02-01"]
    })


def test_assistant_top_performers(sample_df):
    assistant = AnalysisAssistant()
    intent, result = assistant.interpret_and_execute("Show top 2 departments by salary", sample_df)
    assert intent.operation == "top_performers"
    assert len(result) == 2


def test_assistant_group_aggregation(sample_df):
    assistant = AnalysisAssistant()
    intent, result = assistant.interpret_and_execute("Average salary by department", sample_df)
    assert intent.operation == "group_aggregation"
    assert "Salary_mean" in result.columns


def test_assistant_correlation(sample_df):
    assistant = AnalysisAssistant()
    intent, result = assistant.interpret_and_execute("Calculate correlation", sample_df)
    assert intent.operation == "correlation"


def test_assistant_complex_filter_query():
    df = pd.DataFrame({
        "Emp_ID": ["E1", "E2", "E3", "E4"],
        "Salary": [50000, 95000, 60000, 110000],
        "Performance_Rating": [4.5, 3.2, 4.8, 3.1],
    })
    assistant = AnalysisAssistant()
    intent, result = assistant.interpret_and_execute(
        "show me those employee whose performance is low but salary is high", df
    )
    assert intent.operation == "filter_records"
    assert isinstance(result, pd.DataFrame)
    # E2 and E4 have low performance (<= median 3.85) and high salary (>= median 77500)
    assert len(result) >= 1
    assert all(result["Performance_Rating"] <= 4.0)
    assert all(result["Salary"] >= 90000)
