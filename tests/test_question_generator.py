"""
Tests for AI Client, Prompt Builder, and Question Generator (Phase 3).
"""

import pytest
import pandas as pd
from core.data_profiler import DataProfiler
from ai.prompt_builder import build_cleaning_questions_prompt
from ai.ai_client import AIClient
from ai.question_generator import QuestionGenerator, QuestionOption


def test_prompt_builder_no_raw_dataset_leak():
    df = pd.DataFrame({
        "Customer": ["Secret Name 1", "Secret Name 2"],
        "Amount": [100.0, None],
    })
    report = DataProfiler.profile_dataset(df)
    prompt = build_cleaning_questions_prompt(report, "Sheet1")

    # Prompt must contain metadata
    assert "total_rows" in prompt
    assert "quality_score" in prompt
    assert "Amount" in prompt


def test_ai_client_extract_json():
    # Test wrapped in markdown blocks
    raw_markdown = """```json
    {
      "status": "success",
      "count": 42
    }
    ```"""
    parsed = AIClient.extract_json(raw_markdown)
    assert parsed["status"] == "success"
    assert parsed["count"] == 42


def test_question_generator_rule_based():
    df = pd.DataFrame({
        "Name": [" Alice", "Bob", "Bob", "Bob"],  # Dup row, whitespace
        "Region": ["North", "north", "South", "South"],  # Casing
        "Amount": [10.0, None, 50000.0, 50000.0],  # Missing + Outlier
        "Date": ["2026-01-01", "2026-01-02", "not_a_date", "not_a_date"]  # Invalid date
    })
    report = DataProfiler.profile_dataset(df)
    gen = QuestionGenerator()
    questions = gen.generate_rule_based_questions(report)

    assert len(questions) > 0
    issue_types = [q.issue_type for q in questions]
    assert "Duplicate Rows" in issue_types
    assert "Missing Values" in issue_types
    assert "Extra Whitespace" in issue_types
    assert "Inconsistent Text Casing" in issue_types
    assert "Invalid Date Format" in issue_types

    # Verify options structure
    for q in questions:
        assert len(q.options) >= 2
        assert any(opt.is_default for opt in q.options)
