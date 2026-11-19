"""
Tests for ColumnClassifier semantic profiling.
"""

import pytest
import pandas as pd
from core.column_classifier import ColumnClassifier


def test_column_classifier_identifies_roles():
    df = pd.DataFrame({
        "invoice_no": [1.0, 2.0, 3.0, 4.0],
        "customer_id": [101, 102, 103, 104],
        "customer_name": ["Acme", "Beta", "Gamma", "Delta"],
        "order_date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
        "quantity": [5, 10, 15, 20],
        "revenue": [500.0, 1000.0, 1500.0, 2000.0],
    })

    roles = ColumnClassifier.classify_dataframe(df)

    assert roles["invoice_no"] == "IDENTIFIER"
    assert roles["customer_id"] == "IDENTIFIER"
    assert roles["customer_name"] == "DIMENSION"
    assert roles["order_date"] == "TEMPORAL"
    assert roles["quantity"] == "MEASURE"
    assert roles["revenue"] == "MEASURE"

    # Business measures prioritization
    measures = ColumnClassifier.get_measure_columns(df)
    assert measures[0] == "revenue"  # revenue prioritized over quantity
    assert "invoice_no" not in measures
    assert "customer_id" not in measures
