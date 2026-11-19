"""
AI Excel Analyst - Main Streamlit Application
Phase 1: File Upload, Multi-sheet Detection, and Dataset Overview.
"""

from io import BytesIO
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
from config.settings import (
    MAX_UPLOAD_SIZE_MB,
    MAX_UPLOAD_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    DEFAULT_PREVIEW_ROWS,
)
from core.excel_reader import ExcelReader, DatasetMetadata
from core.data_profiler import DataProfiler, DatasetQualityReport, IssueDetail
from core.data_cleaner import DataCleaner
from core.data_validator import DataValidator, CleaningValidationSummary
from core.data_formatter import DataFormatter, ExcelFormattingOptions
from export.excel_exporter import ExcelExporter
from export.csv_exporter import CSVExporter
from export.report_exporter import ReportExporter
from analytics.statistics import StatisticsEngine
from analytics.insights import InsightGenerator
from analytics.chart_generator import ChartGenerator
from dashboard.dashboard_builder import DashboardBuilder
from ai.analysis_assistant import AnalysisAssistant, AnalysisIntent
from ai.question_generator import QuestionGenerator, CleaningQuestion, QuestionOption
from utils.file_validator import validate_file, sanitize_filename
from utils.cleaning_log import CleaningLogger

# Set page configuration
st.set_page_config(
    page_title="AI Excel Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for clean, professional layout
st.markdown(
    """
    <style>
    .main-header {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #555;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1f2937;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def navigate_to(page_name: str):
    """Safely navigate to another step by requesting a page redirect."""
    st.session_state.pending_nav = page_name
    st.rerun()


def init_session_state():
    """Initialize session state variables."""
    if "pending_nav" not in st.session_state:
        st.session_state.pending_nav = None
    if "dataset" not in st.session_state:
        st.session_state.dataset = None  # type: Optional[DatasetMetadata]
    if "raw_file_bytes" not in st.session_state:
        st.session_state.raw_file_bytes = None
    if "file_name" not in st.session_state:
        st.session_state.file_name = None
    if "active_sheet" not in st.session_state:
        st.session_state.active_sheet = None
    if "quality_report" not in st.session_state:
        st.session_state.quality_report = None
    if "cleaning_questions" not in st.session_state:
        st.session_state.cleaning_questions = []
    if "cleaning_decisions" not in st.session_state:
        st.session_state.cleaning_decisions = {}
    if "cleaned_df" not in st.session_state:
        st.session_state.cleaned_df = None
    if "cleaning_logger" not in st.session_state:
        st.session_state.cleaning_logger = CleaningLogger()
    if "validation_summary" not in st.session_state:
        st.session_state.validation_summary = None
    if "nav_choice" not in st.session_state:
        st.session_state.nav_choice = "1. Home & File Upload"


def load_file_content(file_bytes: bytes, file_name: str, sheet_name: str = None) -> bool:
    """Validate and parse uploaded bytes into dataset state."""
    validation = validate_file(file_name, file_bytes, max_size_bytes=MAX_UPLOAD_SIZE_BYTES)
    if not validation.is_valid:
        st.error(f"⚠️ Validation Error: {validation.error_message}")
        return False

    try:
        dataset = ExcelReader.load_dataset(
            file_bytes=file_bytes,
            file_name=file_name,
            sheet_name=sheet_name,
        )
        st.session_state.dataset = dataset
        st.session_state.raw_file_bytes = file_bytes
        st.session_state.file_name = file_name
        st.session_state.active_sheet = dataset.active_sheet
        st.session_state.quality_report = DataProfiler.profile_dataset(dataset.df)
        st.session_state.cleaning_questions = []
        st.session_state.cleaning_decisions = {}
        st.session_state.cleaned_df = None
        st.session_state.cleaning_logger = CleaningLogger()
        st.session_state.validation_summary = None
        return True
    except Exception as e:
        st.error(f"❌ Failed to parse dataset: {str(e)}")
        return False


def render_sidebar():
    """Render sidebar navigation and quick file switcher."""
    st.sidebar.title("📊 AI Excel Analyst")
    st.sidebar.markdown("Local-First Intelligent Spreadsheet Platform")
    st.sidebar.divider()

    navigation_options = [
        "1. Home & File Upload",
        "2. Dataset Overview",
        "3. Data-Quality Report",
        "4. AI Cleaning Assistant",
        "5. Cleaning Preview & Approval",
        "6. Data Analysis",
        "7. Dashboard",
        "8. Export Centre",
    ]

    # Handle pending programmatic redirection before widget instantiation
    if st.session_state.pending_nav and st.session_state.pending_nav in navigation_options:
        st.session_state.sidebar_nav_radio = st.session_state.pending_nav
        st.session_state.nav_choice = st.session_state.pending_nav
        st.session_state.pending_nav = None

    default_idx = navigation_options.index(st.session_state.nav_choice) if st.session_state.nav_choice in navigation_options else 0

    choice = st.sidebar.radio(
        "Navigation",
        options=navigation_options,
        index=default_idx,
        key="sidebar_nav_radio",
    )
    st.session_state.nav_choice = choice

    st.sidebar.divider()

    # Active dataset quick-summary badge
    if st.session_state.dataset is not None:
        ds = st.session_state.dataset
        st.sidebar.markdown(f"**Current File:** `{ds.file_name}`")
        st.sidebar.markdown(f"**Format:** `{ds.file_type.upper()}`")
        if len(ds.sheet_names) > 1:
            st.sidebar.markdown(f"**Worksheet:** `{ds.active_sheet}`")
        st.sidebar.markdown(f"**Dimensions:** {ds.total_rows:,} rows × {ds.total_columns} cols")

        if st.sidebar.button("Clear Dataset", use_container_width=True):
            st.session_state.dataset = None
            st.session_state.raw_file_bytes = None
            st.session_state.file_name = None
            st.session_state.active_sheet = None
            st.session_state.quality_report = None
            st.session_state.nav_choice = "1. Home & File Upload"
            st.rerun()

    st.sidebar.caption("Privacy: Runs locally. Data never leaves your machine without consent.")
    return choice


def render_home_upload():
    """Render upload view with drag-and-drop and sample datasets."""
    st.markdown('<div class="main-header">Dataset Upload & Workspace</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">Upload an Excel (.xlsx, .xls) or CSV file (Max size: {MAX_UPLOAD_SIZE_MB} MB).</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([3, 2], gap="large")

    with col1:
        st.subheader("Upload Your File")
        uploaded_file = st.file_uploader(
            "Choose a spreadsheet file",
            type=["xlsx", "xls", "csv"],
            help="Files are processed entirely on your local machine.",
            label_visibility="collapsed",
        )

        if uploaded_file is not None:
            # Check if newly uploaded file
            if st.session_state.file_name != uploaded_file.name:
                content = uploaded_file.getvalue()
                if load_file_content(content, uploaded_file.name):
                    st.success(f"Successfully loaded '{uploaded_file.name}'!")
                    st.rerun()

    with col2:
        st.subheader("Or Try Sample Datasets")
        st.write("Quickly test with realistic pre-packaged datasets:")

        samples_dir = Path(__file__).resolve().parent / "samples"

        sample_options = [
            ("Sales Orders & Customers (Multi-sheet XLSX)", "sales_data.xlsx"),
            ("Employees & HR Records (CSV)", "employees_data.csv"),
            ("Industrial Inventory & Suppliers (Multi-sheet XLSX)", "inventory_data.xlsx"),
        ]

        for label, filename in sample_options:
            sample_file = samples_dir / filename
            if sample_file.exists():
                if st.button(f"Load {label}", key=f"btn_{filename}", use_container_width=True):
                    with open(sample_file, "rb") as f:
                        file_bytes = f.read()
                    if load_file_content(file_bytes, filename):
                        st.success(f"Loaded sample '{filename}'!")
                        st.rerun()

    # If dataset is currently loaded, display worksheet selector and quick preview
    if st.session_state.dataset is not None:
        st.divider()
        render_worksheet_selector_and_mini_preview()


def render_worksheet_selector_and_mini_preview():
    """Worksheet switcher and quick preview on the home screen."""
    ds = st.session_state.dataset

    if len(ds.sheet_names) > 1:
        st.subheader("Worksheet Selection")
        selected_sheet = st.selectbox(
            "Select Worksheet to Analyze:",
            options=ds.sheet_names,
            index=ds.sheet_names.index(ds.active_sheet) if ds.active_sheet in ds.sheet_names else 0,
            help="This Excel workbook has multiple sheets. Select which sheet you want to inspect and clean.",
        )

        if selected_sheet != ds.active_sheet:
            with st.spinner(f"Loading sheet '{selected_sheet}'..."):
                load_file_content(
                    st.session_state.raw_file_bytes,
                    st.session_state.file_name,
                    sheet_name=selected_sheet,
                )
                st.rerun()

    st.subheader(f"Data Preview: {ds.active_sheet} ({ds.total_rows:,} rows × {ds.total_columns} columns)")
    st.dataframe(ds.df.head(DEFAULT_PREVIEW_ROWS), use_container_width=True)


def render_dataset_overview():
    """Detailed dataset overview with statistics and column inspections."""
    if st.session_state.dataset is None:
        st.warning("⚠️ No dataset loaded. Please upload a file or select a sample dataset on the Home tab.")
        return

    ds = st.session_state.dataset
    df = ds.df

    st.markdown('<div class="main-header">Dataset Overview & Schema</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">Detailed structural breakdown for <b>{ds.file_name}</b> [{ds.active_sheet}]</div>',
        unsafe_allow_html=True,
    )

    # Worksheet switcher if multi-sheet
    if len(ds.sheet_names) > 1:
        c1, _ = st.columns([1, 2])
        with c1:
            new_sheet = st.selectbox(
                "Switch Sheet:",
                options=ds.sheet_names,
                index=ds.sheet_names.index(ds.active_sheet),
                key="overview_sheet_select",
            )
            if new_sheet != ds.active_sheet:
                load_file_content(
                    st.session_state.raw_file_bytes,
                    st.session_state.file_name,
                    sheet_name=new_sheet,
                )
                st.rerun()

    # Metric KPI Cards
    total_cells = df.size
    total_missing = int(df.isna().sum().sum())
    missing_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0.0
    mem_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Total Rows", f"{len(df):,}")
    with m2:
        st.metric("Total Columns", f"{len(df.columns)}")
    with m3:
        st.metric("Missing Values", f"{total_missing:,}", f"{missing_pct:.1f}%")
    with m4:
        st.metric("Memory Usage", f"{mem_mb:.2f} MB")
    with m5:
        st.metric("Worksheets", f"{len(ds.sheet_names)}")

    st.divider()

    # Preview Controls
    col_view_opt, col_rows = st.columns([2, 1])
    with col_view_opt:
        view_mode = st.radio(
            "Preview Mode:",
            ["First Rows (Head)", "Last Rows (Tail)", "Random Sample", "Full Data"],
            horizontal=True,
        )
    with col_rows:
        num_rows = st.slider("Number of Rows:", min_value=5, max_value=min(100, max(5, len(df))), value=10)

    if view_mode == "First Rows (Head)":
        preview_df = df.head(num_rows)
    elif view_mode == "Last Rows (Tail)":
        preview_df = df.tail(num_rows)
    elif view_mode == "Random Sample":
        preview_df = df.sample(min(num_rows, len(df)), random_state=42)
    else:
        preview_df = df

    st.dataframe(preview_df, use_container_width=True)

    st.divider()

    # Column Schema Inspection Table
    st.subheader("Column Schema & Completeness")
    schema_records = []
    for col in df.columns:
        s = df[col]
        null_count = int(s.isna().sum())
        null_ratio = (null_count / len(df) * 100) if len(df) > 0 else 0.0
        unique_count = int(s.nunique(dropna=True))

        # Sample values representation
        non_null_samples = s.dropna().unique()
        samples_str = ", ".join(str(v) for v in non_null_samples[:3])
        if len(samples_str) > 50:
            samples_str = samples_str[:47] + "..."

        schema_records.append({
            "Column Name": col,
            "Inferred Type": str(s.dtype),
            "Non-Null Count": f"{len(df) - null_count:,}",
            "Missing Count": f"{null_count:,}",
            "Missing %": f"{null_ratio:.1f}%",
            "Unique Values": f"{unique_count:,}",
            "Sample Values": samples_str or "—",
        })

    schema_df = pd.DataFrame(schema_records)
    st.dataframe(schema_df, use_container_width=True, hide_index=True)


def render_data_quality_report():
    """Detailed Data Quality Assessment and Issue Breakdown."""
    if st.session_state.dataset is None:
        st.warning("⚠️ No dataset loaded. Please upload a file or select a sample dataset on the Home tab.")
        return

    ds = st.session_state.dataset

    # Ensure profile report is generated
    if st.session_state.quality_report is None:
        with st.spinner("Analyzing dataset quality..."):
            st.session_state.quality_report = DataProfiler.profile_dataset(ds.df)

    report: DatasetQualityReport = st.session_state.quality_report

    st.markdown('<div class="main-header">Data Quality & Health Report</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">Automated data hygiene audit for <b>{ds.file_name}</b> [{ds.active_sheet}]</div>',
        unsafe_allow_html=True,
    )

    # Top KPI Banner: Score & Grade
    col_score, col_grade, col_status = st.columns([1.5, 1, 3.5])

    # Grade coloring
    grade_colors = {
        "A+": "#10b981",
        "A": "#10b981",
        "B": "#3b82f6",
        "C": "#f59e0b",
        "D": "#ef4444",
        "F": "#dc2626",
    }
    color = grade_colors.get(report.grade, "#6b7280")

    with col_score:
        st.markdown(
            f"""
            <div style="background-color: #f8fafc; border: 2px solid {color}; border-radius: 10px; padding: 12px; text-align: center;">
                <div style="font-size: 0.85rem; color: #64748b; font-weight: 600;">OVERALL HEALTH</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: {color};">{report.overall_quality_score}<span style="font-size: 1.1rem; color: #94a3b8;"> / 100</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_grade:
        st.markdown(
            f"""
            <div style="background-color: #f8fafc; border: 2px solid {color}; border-radius: 10px; padding: 12px; text-align: center;">
                <div style="font-size: 0.85rem; color: #64748b; font-weight: 600;">GRADE</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: {color};">{report.grade}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_status:
        if report.grade in ("A+", "A"):
            st.success("🟢 **High Quality**: Dataset is well-structured with minimal issues. Safe for reporting.")
        elif report.grade == "B":
            st.info("🔵 **Good Quality**: Moderate formatting or missing values detected. Cleaning recommended for reliable analysis.")
        elif report.grade == "C":
            st.warning("🟡 **Fair Quality**: Notable data inconsistencies found (casing, outliers, or missing data). Automated cleaning advised.")
        else:
            st.error("🔴 **Low Quality**: Critical data defects detected (duplicates, unparseable dates, severe gaps). Requires thorough cleaning.")

        total_critical = sum(1 for iss in report.all_issues if iss.severity in ("high", "medium"))
        st.caption(f"Detected **{len(report.all_issues)} total issues** ({total_critical} require attention).")

    st.divider()

    # Issue Summary Cards
    st.subheader("Summary of Detected Anomalies")
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    with s1:
        st.metric("Missing Cells", report.issues_summary.get("Missing Values", 0))
    with s2:
        st.metric("Duplicate Rows", report.issues_summary.get("Duplicate Rows", 0))
    with s3:
        st.metric("Whitespace Errors", report.issues_summary.get("Whitespace Errors", 0))
    with s4:
        st.metric("Case Inconsistencies", report.issues_summary.get("Case Inconsistencies", 0))
    with s5:
        st.metric("Invalid Dates", report.issues_summary.get("Date Issues", 0))
    with s6:
        st.metric("Numeric Outliers", report.issues_summary.get("Outliers", 0))

    st.divider()

    # Detailed Tabs
    tab_issues, tab_columns = st.tabs(["📋 Issue Catalog & Evidence", "🧬 Column-Level Health Matrix"])

    with tab_issues:
        if not report.all_issues:
            st.success("🎉 No data quality issues detected in this worksheet!")
        else:
            # Severity Filter
            filter_col1, filter_col2 = st.columns([1, 2])
            with filter_col1:
                severity_filter = st.selectbox(
                    "Filter by Severity:",
                    ["All Severities", "High", "Medium", "Low"],
                )

            filtered_issues = report.all_issues
            if severity_filter != "All Severities":
                filtered_issues = [iss for iss in filtered_issues if iss.severity.lower() == severity_filter.lower()]

            st.write(f"Showing **{len(filtered_issues)}** issue(s):")

            for idx, issue in enumerate(filtered_issues):
                # Severity badge color
                badge_color = {
                    "high": "red",
                    "medium": "orange",
                    "low": "blue",
                }.get(issue.severity, "gray")

                col_label = f"Column: `{issue.column}`" if issue.column else "Dataset Level"
                with st.expander(f":{badge_color}[●] **{issue.issue_type}** — {col_label} ({issue.count} affected)", expanded=(issue.severity == "high")):
                    st.markdown(f"**Description:** {issue.description}")
                    st.markdown(f"**Impact:** {issue.count} instances ({issue.percentage:.1f}% of affected scope)")
                    if issue.sample_values:
                        st.markdown("**Sample Problematic Values:**")
                        st.code(str(issue.sample_values))

    with tab_columns:
        col_health_records = []
        for col_name, prof in report.column_profiles.items():
            # Determine column health icon
            high_count = sum(1 for iss in prof.issues if iss.severity == "high")
            med_count = sum(1 for iss in prof.issues if iss.severity == "medium")
            if high_count > 0:
                health_icon = "🔴 Critical"
            elif med_count > 0 or len(prof.issues) > 0:
                health_icon = "🟡 Warning"
            else:
                health_icon = "🟢 Clean"

            issue_types_str = ", ".join(set(iss.issue_type for iss in prof.issues)) or "None"

            col_health_records.append({
                "Health": health_icon,
                "Column": col_name,
                "Inferred Type": prof.inferred_type,
                "Missing %": f"{prof.missing_percentage:.1f}%",
                "Unique Values": prof.unique_count,
                "Detected Issues": issue_types_str,
            })

        health_df = pd.DataFrame(col_health_records)
        st.dataframe(health_df, use_container_width=True, hide_index=True)

    st.divider()

    # Next steps action callout
    col_nav1, col_nav2 = st.columns([3, 1])
    with col_nav1:
        st.info("💡 **Ready to fix these issues?** Proceed to the AI Cleaning Assistant to review cleaning recommendations or auto-clean with 1 click.")
    with col_nav2:
        if st.button("Continue to AI Assistant 👉", use_container_width=True, type="primary"):
            navigate_to("4. AI Cleaning Assistant")


def render_ai_cleaning_assistant():
    """Interactive AI Cleaning Assistant with simplified 1-click auto clean or custom decisions."""
    if st.session_state.dataset is None:
        st.warning("⚠️ No dataset loaded. Please upload a file or select a sample dataset on the Home tab.")
        return

    ds = st.session_state.dataset

    if st.session_state.quality_report is None:
        with st.spinner("Analyzing data quality..."):
            st.session_state.quality_report = DataProfiler.profile_dataset(ds.df)

    report = st.session_state.quality_report

    st.markdown('<div class="main-header">AI Cleaning Assistant</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">Review tailored cleaning proposals for <b>{ds.file_name}</b> [{ds.active_sheet}]. Original data remains untouched.</div>',
        unsafe_allow_html=True,
    )

    # Generate questions if not cached
    if not st.session_state.cleaning_questions:
        with st.spinner("Formulating intelligent cleaning questions..."):
            generator = QuestionGenerator()
            questions = generator.generate_questions(report, ds.active_sheet)
            st.session_state.cleaning_questions = questions

    questions: List[CleaningQuestion] = st.session_state.cleaning_questions

    if not questions:
        st.success("🎉 No actionable data cleaning issues found! Your data is already clean.")
        if st.button("Proceed to Data Analysis 👉", type="primary"):
            navigate_to("6. Data Analysis")
        return

    # Primary Action Banner: 1-Click Auto-Clean vs Customize
    st.markdown(
        f"""
        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <div style="font-size: 1.1rem; font-weight: 700; color: #166534;">
                ✨ Detected {len(questions)} Cleaning Recommendations
            </div>
            <div style="color: #15803d; font-size: 0.95rem; margin-top: 4px;">
                You can auto-apply the best-practice fixes in one click, or expand below to customize individual column decisions.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_c1, action_c2 = st.columns([2, 1])
    with action_c1:
        if st.button("✨ Auto-Clean Now & Review Preview", type="primary", use_container_width=True):
            with st.spinner("Executing recommended cleaning pipeline..."):
                for q in questions:
                    default_opt = next((opt for opt in q.options if opt.is_default), q.options[0])
                    st.session_state.cleaning_decisions[q.id] = {
                        "action": default_opt.action,
                        "label": default_opt.label,
                        "column": q.column,
                        "issue_type": q.issue_type,
                    }
                logger = CleaningLogger()
                cleaner = DataCleaner(logger=logger)
                cleaned = cleaner.execute_cleaning_decisions(ds.df, st.session_state.cleaning_decisions)
                st.session_state.cleaned_df = cleaned
                st.session_state.cleaning_logger = logger
                st.session_state.validation_summary = DataValidator.validate_cleaned_dataset(
                    ds.df, cleaned, report
                )
                navigate_to("5. Cleaning Preview & Approval")

    with action_c2:
        if st.button("Apply Custom Choices & Preview 👉", use_container_width=True):
            with st.spinner("Applying selected cleaning options..."):
                # Fill any unselected with defaults
                for q in questions:
                    if q.id not in st.session_state.cleaning_decisions:
                        default_opt = next((opt for opt in q.options if opt.is_default), q.options[0])
                        st.session_state.cleaning_decisions[q.id] = {
                            "action": default_opt.action,
                            "label": default_opt.label,
                            "column": q.column,
                            "issue_type": q.issue_type,
                        }
                logger = CleaningLogger()
                cleaner = DataCleaner(logger=logger)
                cleaned = cleaner.execute_cleaning_decisions(ds.df, st.session_state.cleaning_decisions)
                st.session_state.cleaned_df = cleaned
                st.session_state.cleaning_logger = logger
                st.session_state.validation_summary = DataValidator.validate_cleaned_dataset(
                    ds.df, cleaned, report
                )
                navigate_to("5. Cleaning Preview & Approval")

    st.divider()

    # Detailed customizable decisions in an organized layout
    st.subheader(f"🛠️ Cleaning Decision Details ({len(questions)} items)")
    st.caption("Each recommendation is configured with safe defaults. Change any option as needed:")

    for idx, q in enumerate(questions, start=1):
        severity_color = {
            "high": "red",
            "medium": "orange",
            "low": "blue",
        }.get(q.severity, "gray")

        col_badge = f"Column: `{q.column}`" if q.column else "Whole Sheet"

        with st.expander(f"{idx}. :{severity_color}[●] {q.question} ({col_badge})", expanded=(idx <= 3)):
            if q.recommendation:
                st.info(f"💡 **AI Recommendation:** {q.recommendation}")

            opt_labels = [opt.label for opt in q.options]
            default_index = 0
            for i, opt in enumerate(q.options):
                if opt.is_default:
                    default_index = i
                    break

            if q.id in st.session_state.cleaning_decisions:
                saved_action = st.session_state.cleaning_decisions[q.id].get("action")
                for i, opt in enumerate(q.options):
                    if opt.action == saved_action:
                        default_index = i
                        break

            chosen_label = st.radio(
                "Choose cleaning action:",
                options=opt_labels,
                index=default_index,
                key=f"radio_q_{q.id}",
            )

            chosen_opt = next(opt for opt in q.options if opt.label == chosen_label)
            st.session_state.cleaning_decisions[q.id] = {
                "action": chosen_opt.action,
                "label": chosen_opt.label,
                "column": q.column,
                "issue_type": q.issue_type,
            }


def render_cleaning_preview_and_approval():
    """Before-and-after comparison, cleaning log, undo/reset, and validation."""
    if st.session_state.dataset is None:
        st.warning("⚠️ No dataset loaded. Please upload a file or select a sample dataset on the Home tab.")
        return

    ds = st.session_state.dataset
    df_orig = ds.df

    st.markdown('<div class="main-header">Cleaning Preview & Approval</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">Review transformations on <b>{ds.file_name}</b> [{ds.active_sheet}]. Original data remains safe and untouched.</div>',
        unsafe_allow_html=True,
    )

    # If cleaning hasn't run yet
    if st.session_state.cleaned_df is None:
        st.info("ℹ️ Cleaning pipeline has not been executed yet on this worksheet.")

        decisions_count = len(st.session_state.cleaning_decisions)
        st.write(f"Configured decisions available: **{decisions_count}**")

        c_run1, c_run2 = st.columns([2, 1])
        with c_run1:
            if decisions_count == 0:
                st.caption("You have not chosen any custom decisions. Clicking execute will apply recommended defaults.")
        with c_run2:
            if st.button("🚀 Execute Cleaning Pipeline", use_container_width=True):
                with st.spinner("Applying non-destructive cleaning transformations..."):
                    # If empty decisions, generate defaults
                    if decisions_count == 0:
                        if not st.session_state.cleaning_questions:
                            generator = QuestionGenerator()
                            st.session_state.cleaning_questions = generator.generate_questions(st.session_state.quality_report, ds.active_sheet)
                        for q in st.session_state.cleaning_questions:
                            default_opt = next((opt for opt in q.options if opt.is_default), q.options[0])
                            st.session_state.cleaning_decisions[q.id] = {
                                "action": default_opt.action,
                                "label": default_opt.label,
                                "column": q.column,
                                "issue_type": q.issue_type,
                            }

                    logger = CleaningLogger()
                    cleaner = DataCleaner(logger=logger)
                    cleaned = cleaner.execute_cleaning_decisions(df_orig, st.session_state.cleaning_decisions)

                    st.session_state.cleaned_df = cleaned
                    st.session_state.cleaning_logger = logger
                    st.session_state.validation_summary = DataValidator.validate_cleaned_dataset(
                        df_orig, cleaned, st.session_state.quality_report
                    )
                    st.success("Cleaning pipeline executed successfully!")
                    st.rerun()
        return

    # Cleaned DataFrame exists: Show Comparison & Validation
    val: CleaningValidationSummary = st.session_state.validation_summary
    cleaned_df: pd.DataFrame = st.session_state.cleaned_df
    logger: CleaningLogger = st.session_state.cleaning_logger

    # Validation Status Banner
    if val.is_valid:
        st.success(f"✅ **Data Integrity Validated**: Transformation completed safely without structural corruption.")
    else:
        st.error(f"❌ **Validation Warning**: {', '.join(val.errors)}")

    if val.warnings:
        for w in val.warnings:
            st.warning(f"⚠️ {w}")

    # Metric Comparison Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Rows", f"{val.rows_after:,}", delta=f"{val.rows_change} rows")
    with m2:
        st.metric("Total Columns", f"{val.cols_after}", delta=f"{val.cols_change} cols")
    with m3:
        st.metric("Missing Values", f"{val.missing_after:,}", delta=f"-{val.missing_resolved} resolved", delta_color="inverse")
    with m4:
        st.metric("Health Score", f"{val.score_after}/100", delta=f"+{val.score_improvement} pts")

    st.divider()

    # Previews & Comparison
    tab_cleaned, tab_orig, tab_log = st.tabs(["✨ Cleaned Working Copy", "📄 Original Raw Dataset", "📜 Cleaning Audit Log"])

    with tab_cleaned:
        st.subheader(f"Cleaned Dataset Preview ({len(cleaned_df):,} rows × {len(cleaned_df.columns)} columns)")
        st.dataframe(cleaned_df.head(DEFAULT_PREVIEW_ROWS), use_container_width=True)

    with tab_orig:
        st.subheader(f"Original Raw Dataset ({len(df_orig):,} rows × {len(df_orig.columns)} columns)")
        st.dataframe(df_orig.head(DEFAULT_PREVIEW_ROWS), use_container_width=True)

    with tab_log:
        st.subheader("Cleaning Audit Trail")
        log_entries = logger.get_summary()
        if log_entries:
            st.dataframe(pd.DataFrame(log_entries), use_container_width=True, hide_index=True)
        else:
            st.info("No modifications were required or performed.")

    st.divider()

    # Controls: Undo / Reset / Proceed
    c_btn1, c_btn2, c_btn3 = st.columns([1.5, 1.5, 2])
    with c_btn1:
        if st.button("🔄 Reset / Revert to Original", use_container_width=True):
            st.session_state.cleaned_df = None
            st.session_state.cleaning_logger = CleaningLogger()
            st.session_state.validation_summary = None
            st.info("Reverted to original dataset.")
            st.rerun()

    with c_btn2:
        if st.button("Adjust Cleaning Choices", use_container_width=True):
            navigate_to("4. AI Cleaning Assistant")

    with c_btn3:
        if st.button("Proceed to Data Analysis 👉", type="primary", use_container_width=True):
            navigate_to("6. Data Analysis")


def render_export_centre():
    """Export Centre: Formatted Excel, CSV, and Audit Reports with Formula Injection Protection."""
    if st.session_state.dataset is None:
        st.warning("⚠️ No dataset loaded. Please upload a file or select a sample dataset on the Home tab.")
        return

    ds = st.session_state.dataset
    has_cleaned = st.session_state.cleaned_df is not None

    st.markdown('<div class="main-header">Export Centre</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">Download cleaned or original data with custom formatting and injection protection.</div>',
        unsafe_allow_html=True,
    )

    # Dataset Selection
    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        export_source = st.radio(
            "Select Version to Export:",
            ["Cleaned Working Copy" if has_cleaned else "Original Dataset (No cleaning performed yet)", "Original Raw Dataset"],
            horizontal=True,
        )

    export_df = st.session_state.cleaned_df if ("Cleaned" in export_source and has_cleaned) else ds.df
    base_filename = ds.file_name.rsplit(".", 1)[0]
    suffix_label = "cleaned" if ("Cleaned" in export_source and has_cleaned) else "raw"

    st.info(f"Target dataset: **{len(export_df):,} rows × {len(export_df.columns)} columns** [{ds.active_sheet}].")

    st.divider()

    # Export formats
    tab_excel, tab_csv, tab_report = st.tabs(["📊 Formatted Excel (.xlsx)", "📄 Delimited CSV (.csv)", "📑 HTML Audit Report (.html)"])

    # 1. Formatted Excel
    with tab_excel:
        st.subheader("Professional Excel Workbook")
        st.write("Customize visual themes, header styling, freeze panes, and column sizing:")

        c_opt1, c_opt2, c_opt3 = st.columns(3)
        with c_opt1:
            theme_choice = st.selectbox(
                "Color Theme:",
                ["Corporate Navy", "Modern Emerald", "Classic Slate", "Clean Minimal"],
            )
            freeze_hdr = st.checkbox("Freeze Header Row", value=True)
        with c_opt2:
            add_bdr = st.checkbox("Add Grid Borders", value=True)
            auto_fit = st.checkbox("Auto-fit Column Widths", value=True)
        with c_opt3:
            alt_rows = st.checkbox("Highlight Alternate Rows", value=True)
            bold_hdr = st.checkbox("Bold Header Text", value=True)

        opts = ExcelFormattingOptions(
            theme=theme_choice,
            freeze_header=freeze_hdr,
            add_borders=add_bdr,
            auto_fit_columns=auto_fit,
            highlight_alternate_rows=alt_rows,
            header_bold=bold_hdr,
        )

        with st.spinner("Generating styled Excel workbook..."):
            excel_bytes = ExcelExporter.export(
                df=export_df,
                sheet_name=ds.active_sheet,
                options=opts,
            )

        st.download_button(
            label="📥 Download Formatted Excel Workbook",
            data=excel_bytes,
            file_name=f"{base_filename}_{suffix_label}_styled.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # 2. Delimited CSV
    with tab_csv:
        st.subheader("Delimited Plain CSV")
        c_csv1, c_csv2 = st.columns(2)
        with c_csv1:
            delim_label = st.selectbox("Delimiter:", ["Comma (,)", "Semicolon (;)", "Tab (\\t)", "Pipe (|)"])
            delim_char = {
                "Comma (,)": ",",
                "Semicolon (;)": ";",
                "Tab (\\t)": "\t",
                "Pipe (|)": "|",
            }[delim_label]
        with c_csv2:
            enc_choice = st.selectbox("Character Encoding:", ["utf-8", "utf-8-sig", "latin1"])

        csv_bytes = CSVExporter.export(
            df=export_df,
            delimiter=delim_char,
            encoding=enc_choice,
            sanitize=True,
        )

        st.download_button(
            label="📥 Download CSV File",
            data=csv_bytes,
            file_name=f"{base_filename}_{suffix_label}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # 3. HTML Audit Report
    with tab_report:
        st.subheader("Executive Audit & Quality Report")
        st.write("Generate a standalone HTML report with data hygiene score, applied transformations, and data preview:")

        cleaning_log_entries = st.session_state.cleaning_logger.get_summary() if st.session_state.cleaning_logger else []
        html_report = ReportExporter.generate_html_report(
            file_name=ds.file_name,
            sheet_name=ds.active_sheet,
            df=export_df,
            report_before=st.session_state.quality_report,
            validation_summary=st.session_state.validation_summary,
            cleaning_log=cleaning_log_entries,
        )

        st.download_button(
            label="📥 Download HTML Audit Report",
            data=html_report.encode("utf-8"),
            file_name=f"{base_filename}_audit_report.html",
            mime="text/html",
            use_container_width=True,
        )

    st.divider()
    st.caption("🛡️ **Safety Protection**: All exported files automatically prefix formula trigger characters (`=`, `+`, `-`, `@`) to defend against spreadsheet formula injection attacks.")


def render_data_analysis():
    """Statistical Analysis and Natural-Language Query Engine."""
    if st.session_state.dataset is None:
        st.warning("⚠️ No dataset loaded. Please upload a file or select a sample dataset on the Home tab.")
        return

    ds = st.session_state.dataset
    has_cleaned = st.session_state.cleaned_df is not None

    st.markdown('<div class="main-header">Statistical Analysis & Insights</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">Descriptive statistics, correlations, aggregations, and AI natural-language analysis.</div>',
        unsafe_allow_html=True,
    )

    # Dataset Source Selector
    c_src, _ = st.columns([2, 1])
    with c_src:
        analysis_source = st.radio(
            "Analyze Dataset:",
            ["Cleaned Working Copy" if has_cleaned else "Original Dataset", "Original Raw Dataset"],
            horizontal=True,
        )

    target_df = st.session_state.cleaned_df if ("Cleaned" in analysis_source and has_cleaned) else ds.df
    st.caption(f"Analyzing: **{len(target_df):,} rows × {len(target_df.columns)} columns** [{ds.active_sheet}].")

    # 1. Executive Business Insights
    st.subheader("💡 Automated Key Takeaways")
    insights = InsightGenerator.generate_insights(target_df)
    for insight in insights:
        st.markdown(f"- {insight}")

    st.divider()

    # 2. Natural Language Analysis Assistant
    st.subheader("💬 Ask Questions in Natural Language")
    st.write("Type your question below (e.g. *'Top 5 customers by sales'*, *'Average salary by department'*, *'Correlation matrix'*):")

    c_query, c_ask = st.columns([4, 1])
    with c_query:
        user_query = st.text_input(
            "Natural Language Analysis Query:",
            placeholder="e.g. Show top 5 products by quantity, or average sales by region",
            label_visibility="collapsed",
        )
    with c_ask:
        ask_btn = st.button("Run Analysis", use_container_width=True)

    # Preset quick chips
    q_col1, q_col2, q_col3 = st.columns(3)
    preset_query = None
    with q_col1:
        if st.button("📌 Top Performers", use_container_width=True):
            preset_query = "top performers"
    with q_col2:
        if st.button("📊 Group Aggregation", use_container_width=True):
            preset_query = "group aggregation by category"
    with q_col3:
        if st.button("🔗 Correlation Matrix", use_container_width=True):
            preset_query = "calculate correlation matrix"

    active_query = user_query or preset_query
    if (ask_btn or preset_query) and active_query:
        assistant = AnalysisAssistant()
        with st.spinner("Interpreting query into validated analytical operation..."):
            intent, result = assistant.interpret_and_execute(active_query, target_df)

        st.success(f"**Identified Intent:** {intent.explanation} *(Operation: `{intent.operation}`)*")

        if isinstance(result, pd.DataFrame):
            st.markdown(f"**Query Results ({len(result):,} rows):**")
            st.dataframe(result, use_container_width=True)
        elif isinstance(result, dict):
            for k, v in result.items():
                if isinstance(v, pd.DataFrame):
                    st.markdown(f"**{k.replace('_', ' ').title()}:**")
                    st.dataframe(v, use_container_width=True)
        elif result is not None:
            st.write(result)

    st.divider()

    # 3. Interactive Analysis Workbench
    st.subheader("🛠️ Analytical Workbench")
    tab_desc, tab_group, tab_corr, tab_rank = st.tabs([
        "📈 Descriptive Stats",
        "🗂️ Grouping & Aggregations",
        "🔗 Correlation Analysis",
        "🏆 Top & Bottom Rankings",
    ])

    # Tab A: Descriptive Stats
    with tab_desc:
        stats = StatisticsEngine.get_descriptive_stats(target_df)
        if stats["numeric_summary"] is not None:
            st.markdown("##### Numerical Features Summary")
            st.dataframe(stats["numeric_summary"], use_container_width=True)

        if stats["categorical_summary"] is not None:
            st.markdown("##### Categorical Features Summary")
            st.dataframe(stats["categorical_summary"], use_container_width=True, hide_index=True)

    # Tab B: Grouping
    with tab_group:
        cat_options = target_df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
        num_options = target_df.select_dtypes(include=[np.number]).columns.tolist()

        if not cat_options or not num_options:
            st.info("Grouping requires at least one categorical column and one numerical column.")
        else:
            g_c1, g_c2, g_c3 = st.columns(3)
            with g_c1:
                grp_col = st.selectbox("Group By (Category):", options=cat_options, key="grp_sel_col")
            with g_c2:
                met_col = st.selectbox("Metric Column:", options=num_options, key="grp_sel_met")
            with g_c3:
                agg_func = st.selectbox("Aggregation Function:", ["sum", "mean", "count", "min", "max", "median"], key="grp_sel_func")

            res_grouped = StatisticsEngine.aggregate_by_group(target_df, grp_col, met_col, agg_func)
            st.dataframe(res_grouped, use_container_width=True, hide_index=True)

    # Tab C: Correlation
    with tab_corr:
        corr_matrix, corr_pairs = StatisticsEngine.compute_correlation_matrix(target_df)
        if corr_matrix is None:
            st.info("Correlation requires at least 2 numerical columns.")
        else:
            st.markdown("##### Correlation Matrix")
            st.dataframe(corr_matrix, use_container_width=True)
            if corr_pairs:
                st.markdown("##### Strongest Correlated Pairs")
                st.dataframe(pd.DataFrame(corr_pairs), use_container_width=True, hide_index=True)

    # Tab D: Top/Bottom
    with tab_rank:
        if not cat_options or not num_options:
            st.info("Rankings require at least one entity column and one numerical metric.")
        else:
            r_c1, r_c2, r_c3, r_c4 = st.columns(4)
            with r_c1:
                rank_ent = st.selectbox("Entity Column:", options=cat_options, key="rank_ent")
            with r_c2:
                rank_met = st.selectbox("Rank By Metric:", options=num_options, key="rank_met")
            with r_c3:
                rank_order = st.selectbox("Order:", ["Top Performers", "Bottom Performers"])
            with r_c4:
                rank_n = st.slider("Count (N):", min_value=1, max_value=20, value=5)

            is_asc = (rank_order == "Bottom Performers")
            ranked_res = StatisticsEngine.get_top_bottom_performers(target_df, rank_ent, rank_met, n=rank_n, ascending=is_asc)
            st.dataframe(ranked_res, use_container_width=True, hide_index=True)


def render_dashboard():
    """Interactive Dynamic Dashboard Generator powered by Plotly."""
    if st.session_state.dataset is None:
        st.warning("⚠️ No dataset loaded. Please upload a file or select a sample dataset on the Home tab.")
        return

    ds = st.session_state.dataset
    has_cleaned = st.session_state.cleaned_df is not None

    st.markdown('<div class="main-header">Interactive Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="sub-header">Dynamically generated interactive charts tailored to <b>{ds.file_name}</b> [{ds.active_sheet}].</div>',
        unsafe_allow_html=True,
    )

    # Dataset Source & Filtering Bar
    c_src, c_filt_col, c_filt_val = st.columns([1.5, 1.5, 2])
    with c_src:
        dash_source = st.radio(
            "Source Data:",
            ["Cleaned Working Copy" if has_cleaned else "Original Dataset", "Original Raw Dataset"],
            horizontal=True,
        )

    base_df = st.session_state.cleaned_df if ("Cleaned" in dash_source and has_cleaned) else ds.df

    # Optional interactive filter
    cat_cols = base_df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    num_cols = base_df.select_dtypes(include=[np.number]).columns.tolist()

    filtered_df = base_df
    with c_filt_col:
        filter_col = st.selectbox("Quick Filter By:", ["(None)"] + cat_cols)
    with c_filt_val:
        if filter_col != "(None)":
            unique_vals = sorted(base_df[filter_col].dropna().unique().tolist())
            selected_vals = st.multiselect("Select Values:", options=unique_vals, default=unique_vals)
            if selected_vals:
                filtered_df = base_df[base_df[filter_col].isin(selected_vals)]

    st.caption(f"Showing **{len(filtered_df):,} of {len(base_df):,} records**.")

    # 1. Dynamic KPI Metric Cards
    kpis = DashboardBuilder.get_auto_kpis(filtered_df)
    kpi_cols = st.columns(len(kpis))
    for idx, kpi in enumerate(kpis):
        with kpi_cols[idx]:
            st.metric(kpi["label"], kpi["value"])

    st.divider()

    # 2. Tabs: Auto-Generated Overview vs Custom Visualizer
    tab_auto, tab_custom = st.tabs(["📊 Auto-Generated Executive Dashboard", "🎨 Custom Visualizer & Chart Builder"])

    # --- Auto Dashboard ---
    with tab_auto:
        rec_charts = DashboardBuilder.get_recommended_charts(filtered_df)
        if not rec_charts:
            st.info("No suitable numeric or categorical fields found to plot.")
        else:
            # Render charts in a 2-column responsive layout
            for i in range(0, len(rec_charts), 2):
                row_cols = st.columns(2)
                with row_cols[0]:
                    st.plotly_chart(rec_charts[i]["figure"], use_container_width=True)
                if i + 1 < len(rec_charts):
                    with row_cols[1]:
                        st.plotly_chart(rec_charts[i + 1]["figure"], use_container_width=True)

            # Export HTML Dashboard Button
            st.divider()
            dashboard_html = DashboardBuilder.export_dashboard_html(
                f"{ds.file_name} Analytics Dashboard",
                kpis,
                [c["figure"] for c in rec_charts],
            )
            st.download_button(
                label="📥 Download Interactive HTML Dashboard",
                data=dashboard_html.encode("utf-8"),
                file_name=f"{ds.file_name.rsplit('.', 1)[0]}_dashboard.html",
                mime="text/html",
                use_container_width=True,
            )

    # --- Custom Visualizer ---
    with tab_custom:
        st.subheader("Build Your Custom Visualization")
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            chart_type = st.selectbox(
                "Chart Type:",
                ["Bar Chart", "Line Chart", "Pie / Donut Chart", "Histogram", "Scatter Plot", "Box Plot"],
            )
        with b2:
            x_var = st.selectbox("X-Axis / Category:", options=list(filtered_df.columns), key="custom_x")
        with b3:
            y_options = ["(None)"] + num_cols if chart_type in ("Bar Chart", "Pie / Donut Chart") else num_cols
            y_var = st.selectbox("Y-Axis / Metric:", options=y_options if y_options else list(filtered_df.columns), key="custom_y")
        with b4:
            agg_type = st.selectbox("Aggregation:", ["sum", "mean", "count", "min", "max", "median"], key="custom_agg")

        custom_fig = None
        try:
            if chart_type == "Bar Chart":
                custom_fig = ChartGenerator.create_bar_chart(
                    filtered_df, x_var, None if y_var == "(None)" else y_var, agg_func=agg_type
                )
            elif chart_type == "Line Chart":
                custom_fig = ChartGenerator.create_line_chart(filtered_df, x_var, y_var)
            elif chart_type == "Pie / Donut Chart":
                custom_fig = ChartGenerator.create_pie_chart(
                    filtered_df, x_var, None if y_var == "(None)" else y_var
                )
            elif chart_type == "Histogram":
                custom_fig = ChartGenerator.create_histogram(filtered_df, x_var)
            elif chart_type == "Scatter Plot":
                custom_fig = ChartGenerator.create_scatter_plot(filtered_df, x_var, y_var)
            elif chart_type == "Box Plot":
                custom_fig = ChartGenerator.create_box_plot(filtered_df, y_var, x_var)

            if custom_fig:
                st.plotly_chart(custom_fig, use_container_width=True)
        except Exception as e:
            st.error(f"Could not render chart: {str(e)}")


def main():
    init_session_state()
    selected_nav = render_sidebar()

    if selected_nav == "1. Home & File Upload":
        render_home_upload()
    elif selected_nav == "2. Dataset Overview":
        render_dataset_overview()
    elif selected_nav == "3. Data-Quality Report":
        render_data_quality_report()
    elif selected_nav == "4. AI Cleaning Assistant":
        render_ai_cleaning_assistant()
    elif selected_nav == "5. Cleaning Preview & Approval":
        render_cleaning_preview_and_approval()
    elif selected_nav == "6. Data Analysis":
        render_data_analysis()
    elif selected_nav == "7. Dashboard":
        render_dashboard()
    elif selected_nav == "8. Export Centre":
        render_export_centre()


if __name__ == "__main__":
    main()
