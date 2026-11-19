"""
Integration tests for Streamlit app (Phase 1 & 2).
Uses Streamlit's AppTest to test rendering and user interactions.
"""

from pathlib import Path
from streamlit.testing.v1 import AppTest
import pytest

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def test_app_initial_render():
    at = AppTest.from_file(str(APP_PATH), default_timeout=15).run()
    assert not at.exception
    # Should display headers
    markdown_texts = [m.value for m in at.markdown]
    assert any("Dataset Upload & Workspace" in text for text in markdown_texts)
    # Should display file uploader
    assert len(at.file_uploader) > 0


def test_app_load_sample_data():
    at = AppTest.from_file(str(APP_PATH), default_timeout=15).run()
    assert not at.exception

    # Find the button to load sales sample
    sample_buttons = [b for b in at.button if "Sales" in b.label]
    assert len(sample_buttons) > 0

    # Click the button
    sample_buttons[0].click().run()
    assert not at.exception

    # Verify dataset is loaded in session state
    assert at.session_state.dataset is not None
    assert at.session_state.dataset.file_name == "sales_data.xlsx"
    assert at.session_state.dataset.active_sheet == "Orders"
    assert at.session_state.dataset.total_rows == 8
    assert at.session_state.quality_report is not None


def test_app_quality_report_navigation():
    at = AppTest.from_file(str(APP_PATH), default_timeout=15).run()
    # First load sample
    sample_buttons = [b for b in at.button if "Sales" in b.label]
    sample_buttons[0].click().run()
    assert not at.exception

    # Navigate to "3. Data-Quality Report"
    at.sidebar.radio[0].set_value("3. Data-Quality Report").run()
    assert not at.exception

    markdown_texts = [m.value for m in at.markdown]
    assert any("Data Quality & Health Report" in text for text in markdown_texts)
    # Metric cards for detected anomalies should exist
    metric_labels = [m.label for m in at.metric]
    assert "Missing Cells" in metric_labels
    assert "Duplicate Rows" in metric_labels


def test_app_cleaning_assistant_navigation():
    at = AppTest.from_file(str(APP_PATH), default_timeout=15).run()
    # Load sample
    sample_buttons = [b for b in at.button if "Sales" in b.label]
    sample_buttons[0].click().run()
    assert not at.exception

    # Navigate to "4. AI Cleaning Assistant"
    at.sidebar.radio[0].set_value("4. AI Cleaning Assistant").run()
    assert not at.exception

    markdown_texts = [m.value for m in at.markdown]
    assert any("AI Cleaning Assistant" in text for text in markdown_texts)
    # Questions should be generated
    assert len(at.session_state.cleaning_questions) > 0
    # Check auto-clean button
    auto_clean_btn = [b for b in at.button if "Auto-Clean" in b.label]
    assert len(auto_clean_btn) > 0
    auto_clean_btn[0].click().run()
    assert not at.exception
    assert at.session_state.cleaned_df is not None
    assert len(at.session_state.cleaning_decisions) == len(at.session_state.cleaning_questions)


def test_app_cleaning_preview_and_execution():
    at = AppTest.from_file(str(APP_PATH), default_timeout=15).run()
    # Load sample
    sample_buttons = [b for b in at.button if "Sales" in b.label]
    sample_buttons[0].click().run()
    assert not at.exception

    # Navigate to "5. Cleaning Preview & Approval"
    at.sidebar.radio[0].set_value("5. Cleaning Preview & Approval").run()
    assert not at.exception

    # Execute cleaning pipeline
    exec_btn = [b for b in at.button if "Execute Cleaning Pipeline" in b.label]
    assert len(exec_btn) > 0
    exec_btn[0].click().run()
    assert not at.exception

    # Verify cleaned_df and validation summary are created
    assert at.session_state.cleaned_df is not None
    assert at.session_state.validation_summary is not None
    assert at.session_state.validation_summary.is_valid

    # Check reset button reverts
    reset_btn = [b for b in at.button if "Reset" in b.label]
    assert len(reset_btn) > 0
    reset_btn[0].click().run()
    assert not at.exception
    assert at.session_state.cleaned_df is None


def test_app_export_centre_navigation():
    at = AppTest.from_file(str(APP_PATH), default_timeout=15).run()
    # Load sample
    sample_buttons = [b for b in at.button if "Sales" in b.label]
    sample_buttons[0].click().run()
    assert not at.exception

    # Navigate to "8. Export Centre"
    at.sidebar.radio[0].set_value("8. Export Centre").run()
    assert not at.exception

    markdown_texts = [m.value for m in at.markdown]
    assert any("Export Centre" in text for text in markdown_texts)
    # Check download buttons exist
    assert len(at.download_button) >= 3


def test_app_data_analysis_navigation():
    at = AppTest.from_file(str(APP_PATH), default_timeout=15).run()
    # Load sample
    sample_buttons = [b for b in at.button if "Sales" in b.label]
    sample_buttons[0].click().run()
    assert not at.exception

    # Navigate to "6. Data Analysis"
    at.sidebar.radio[0].set_value("6. Data Analysis").run()
    assert not at.exception

    markdown_texts = [m.value for m in at.markdown]
    assert any("Statistical Analysis & Insights" in text for text in markdown_texts)
    subheader_texts = [s.value for s in at.subheader]
    assert any("Automated Key Takeaways" in text for text in subheader_texts)

    # Click a preset query button
    top_btn = [b for b in at.button if "Top Performers" in b.label]
    assert len(top_btn) > 0
    top_btn[0].click().run()
    assert not at.exception


def test_app_dashboard_navigation():
    at = AppTest.from_file(str(APP_PATH), default_timeout=15).run()
    # Load sample
    sample_buttons = [b for b in at.button if "Sales" in b.label]
    sample_buttons[0].click().run()
    assert not at.exception

    # Navigate to "7. Dashboard"
    at.sidebar.radio[0].set_value("7. Dashboard").run()
    assert not at.exception

    markdown_texts = [m.value for m in at.markdown]
    assert any("Interactive Dashboard" in text for text in markdown_texts)
    # Check KPI metrics are rendered
    assert len(at.metric) >= 2
