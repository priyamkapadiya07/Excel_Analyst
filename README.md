# AI Excel Analyst 📊

A local-first, privacy-preserving intelligent Excel and CSV analysis application built with Python, Streamlit, Pandas, and Plotly.

## Completed Features

### Phase 1: File Upload & Data Inspection
- **File Ingestion & Safety:** Full support for `.xlsx`, `.xls`, and `.csv` datasets with magic byte verification, file size limits (50MB), filename sanitization, and null-byte binary checks.
- **Multi-Worksheet Support:** Auto-discovery of worksheets with interactive switching dropdown.
- **Dataset Parsing:** Encoding fallback (UTF-8, Latin1, CP1252) and delimiter sniffing.
- **Previews & Schema:** Head, Tail, Random Sample, and Full dataset views with inferred data types and memory stats.
- **Sample Datasets:** 1-click loading for Multi-sheet Sales, HR Employees, and Inventory.

### Phase 2: Data Profiling & Quality Reporting
- **Automated Health Engine (`core/data_profiler.py`):**
  - **Missing Values:** Detection of null cells with severity thresholds per column and dataset.
  - **Duplicate Records:** Identification of exact duplicated rows.
  - **Duplicate Columns & Empty Dimensions:** Detection of empty rows, fully empty columns, and duplicate column names.
  - **Whitespace Inconsistencies:** Flags leading, trailing, and double internal spaces in text columns.
  - **Case Inconsistencies:** Detects inconsistent casing (e.g., `North`, `north`, `NORTH`) and aggregates variant counts.
  - **Date Format Validation:** Identifies unparseable date strings in date-labeled or date-formatted columns.
  - **Type Mismatches:** Detects numerical or currency values mistakenly formatted as strings.
  - **Outlier Detection:** Implements statistical IQR (1.5 × IQR) fences for numerical attributes.
- **Interactive Quality Report UI:**
  - Executive Health Grade (A+ to F) and 0–100 quality score.
  - Anomaly metric counters (Missing, Duplicates, Whitespace, Casing, Dates, Outliers).
  - Severity-filtered issue catalog with descriptions and evidence samples.
  - Column-level health matrix with visual status indicators (🟢 Clean, 🟡 Warning, 🔴 Critical).
- **Automated Testing:** 24 unit and UI integration tests with PyTest and Streamlit AppTest.

### Phase 3: AI API Integration & Cleaning Question Generation
- **Privacy-Preserving Prompt Engine (`ai/prompt_builder.py`):**
  - Aggregates schema metadata and anomaly statistics.
  - Never leaks or sends entire raw datasets to AI.
- **Configurable AI Client (`ai/ai_client.py`):**
  - Integrates with Google Gemini models with structured JSON parsing.
  - Recovers gracefully from Markdown blocks or malformed inputs.
- **Dynamic Question Generator (`ai/question_generator.py`):**
  - Produces structured, non-destructive cleaning questions for every detected issue.
  - Each question offers clear options, trade-offs, and defaults (imputation, dropping, formatting, capping, or ignoring).
  - Built-in deterministic expert fallback ensures 100% offline usability without requiring an API key.
- **Streamlit Questionnaire UI:**
  - Interactive decision cards with severity indicators and rationale.
  - "Accept All Recommended Defaults" shortcut for rapid processing.
  - Saves user cleaning decisions into session state for Phase 4 execution.

### Phase 4: Data Cleaning Engine, Validation & Audit History
- **Pure Functional Cleaning Engine (`core/data_cleaner.py`):**
  - **Duplicates:** Drops exact duplicates preserving first observation.
  - **Whitespace Normalization:** Strips leading/trailing spaces and collapses repeated internal whitespace.
  - **Text Standardization:** Transforms casing into Title Case, UPPERCASE, or lowercase.
  - **Missing Value Imputation:** Imputes numeric data (median/mean/zero) and categorical data (mode/fill unknown/drop rows).
  - **Date Coercion:** Formats dates into standard YYYY-MM-DD and handles corrupted date entries cleanly.
  - **Outlier Capping:** Winsorizes numerical outliers to valid $1.5 \times \text{IQR}$ fences or removes outlier rows.
  - **Empty Dimensions:** Prunes completely blank rows and columns.
- **Data Validation & Integrity Checks (`core/data_validator.py`):**
  - Confirms non-empty datasets, alerts on excessive row pruning (>50%).
  - Automatically computes pre- vs post-cleaning improvement deltas (rows, columns, resolved missing cells, health score delta).
- **Audit Logging & Reversibility (`utils/cleaning_log.py`):**
  - Tracks timestamped logs of every cleaning transformation with affected cell counts.
  - 1-click Undo / Reset button that instantly restores the pristine original data without touching saved files.
- **Comparison UI in Streamlit:**
  - Delta KPI cards showing changes in rows, columns, missing values, and score improvement.
  - Tabbed interface comparing Cleaned Working Copy, Original Raw Dataset, and Cleaning Audit Trail.

### Phase 5: Excel Formatting & Multi-Format Export Centre
- **Styling & Visual Formatting Engine (`core/data_formatter.py`):**
  - Built on OpenPyXL with 4 professional themes: *Corporate Navy*, *Modern Emerald*, *Classic Slate*, *Clean Minimal*.
  - Configurable header styling (bold, fill color, text color, height 28pt).
  - Auto-column width fitting with safety margins.
  - Frozen header panes (`A2`) for smooth row scrolling.
  - Thin grid borders and alternate zebra striping.
  - Number and date formatting rules.
- **Formula Injection Security Protection:**
  - Automated prefix escaping (`'`) for cells starting with dangerous trigger characters (`=`, `+`, `-`, `@`) in both CSV and Excel outputs to protect against CSV/formula injection vulnerabilities.
- **Multi-Format Export Centre (`export/`):**
  - **Formatted Excel (`export/excel_exporter.py`):** Produces styled `.xlsx` workbooks with user-selected themes and options.
  - **Clean CSV (`export/csv_exporter.py`):** Custom delimiters (comma, semicolon, tab, pipe) and encodings (UTF-8, UTF-8-sig, Latin-1).
  - **HTML Audit Report (`export/report_exporter.py`):** Standalone, printable responsive HTML executive summary with metrics, transformation logs, and data preview.
- **Streamlit Export UI:**
  - Version selector: Download Cleaned Working Copy or Original Raw Dataset.
  - Real-time download buttons with dynamic filename generation.

### Phase 6: Statistical Analysis & Business Insights
- **Statistical Operations Engine (`analytics/statistics.py`):**
  - **Descriptive Statistics:** Quantiles, mean, std, median, skewness for numeric series, plus uniqueness and mode frequencies for categorical attributes.
  - **Group Aggregations:** Safe grouping and multi-function reductions (`sum`, `mean`, `count`, `min`, `max`, `median`).
  - **Correlation Matrix:** Pearson correlation computations with automatic identification of top correlated variable pairs.
  - **Rankings:** Top $N$ and Bottom $N$ performer rankings by target metric.
  - **Time Trends:** Resampling of numerical metrics across date intervals.
- **Automated Business Insights (`analytics/insights.py`):**
  - Derives factual insights regarding data completeness, dominant categorical categories, distribution parameters, and strong correlations without LLM fabrication.
- **Natural Language Analysis Assistant (`ai/analysis_assistant.py`):**
  - Translates natural language queries into verified, predefined analytical intents.
  - Strict security guarantee: **never executes arbitrary AI-generated Python code**.
- **Interactive Workbench UI:**
  - Natural language query bar with quick-preset prompt chips.
  - Tabbed analytical workspace covering Descriptive Stats, Grouping, Correlation, and Rankings.

### Phase 7: Dynamic Interactive Dashboard Generation
- **Visual Chart Engine (`analytics/chart_generator.py`):**
  - Generates responsive, interactive Plotly charts with a modern palette:
    - **Bar Charts:** Vertical/horizontal counts and multi-function aggregations.
    - **Line Charts:** Trend timelines with responsive markers.
    - **Donut / Pie Charts:** Proportional category share visualizations.
    - **Histograms:** Distribution density with marginal box-plots.
    - **Scatter Plots:** Multi-variable correlation plots with color grouping.
    - **Box Plots:** Quartile breakdowns and outlier points.
- **Dynamic Dashboard Planner (`dashboard/dashboard_builder.py`):**
  - Adapts intelligently to **any dataset** (sales, HR, inventory, finance) rather than assuming fixed sales schemas.
  - Automatically identifies candidate summary KPIs (totals, averages, unique entities).
  - Infers suitable chart combinations based on schema attributes.
  - **Standalone Interactive HTML Export:** Exports the complete dashboard as an interactive offline `.html` file.
- **Streamlit Dashboard UI:**
  - Executive KPI cards.
  - Real-time slice-and-dice filter bar.
  - 2-column responsive layout of Plotly figures.
  - **Custom Chart Builder:** User-friendly wizard to pick chart type, X/Y axes, aggregations, and colors on the fly.

### Phase 8: Integration Testing & Edge Case Polish
- **Full-Lifecycle End-to-End Integration Tests (`tests/test_end_to_end_integration.py`):**
  - Multi-sheet Sales Orders (`sales_data.xlsx`)
  - Human Resources & Salaries (`employees_data.csv`)
  - Industrial Stock & Suppliers (`inventory_data.xlsx`)
  - End-to-end verification covering ingestion $\rightarrow$ profiling $\rightarrow$ question generation $\rightarrow$ non-destructive cleaning $\rightarrow$ validation $\rightarrow$ formatting $\rightarrow$ statistics & NL queries $\rightarrow$ interactive dashboarding $\rightarrow$ multi-format export.
- **Robust Safety & Edge Case Suite (`tests/test_safety_and_edge_cases.py`):**
  - Completely empty DataFrames (0 rows, 0 cols).
  - 100% null columns and empty rows.
  - Column headers with special characters, unicode, spaces, and numbers.
  - Verification of formula injection defenses across all export pathways.
  - Safe boolean and numerical dtype boundaries in NumPy 2.x and Pandas 3.x.

---

## Architecture Overview

```
Excel_Analyst/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
├── config/
│   └── settings.py         # App configurations and constants
├── core/
│   ├── excel_reader.py     # Multi-format spreadsheet reader
│   ├── data_profiler.py    # Data profiling & health audit engine
│   ├── data_cleaner.py     # Functional data cleaning engine
│   ├── data_validator.py   # Transformation validation & comparison
│   └── data_formatter.py   # OpenPyXL visual formatting engine
├── ai/
│   ├── ai_client.py        # Configurable LLM client with JSON extraction
│   ├── prompt_builder.py   # Privacy-first metadata prompt builder
│   ├── question_generator.py # Interactive cleaning decision generator
│   └── analysis_assistant.py # Safe NL-to-predefined query assistant
├── analytics/
│   ├── statistics.py       # Core statistical computation engine
│   ├── insights.py         # Automated business insight extractor
│   └── chart_generator.py  # Plotly chart creation factory
├── dashboard/
│   └── dashboard_builder.py # Dynamic dashboard engine & HTML export
├── export/
│   ├── excel_exporter.py   # Formatted Excel exporter
│   ├── csv_exporter.py     # Safe CSV exporter
│   └── report_exporter.py  # Standalone HTML report generator
├── utils/
│   ├── file_validator.py   # File validation, size, & magic-byte check
│   └── cleaning_log.py     # Cleaning operation audit logger
├── samples/
│   ├── generate_sample_data.py # Sample generator
│   ├── sales_data.xlsx     # Multi-sheet sample
│   ├── employees_data.csv   # CSV sample
│   └── inventory_data.xlsx # Inventory sample
└── tests/
    ├── test_file_validator.py  # Validator unit tests
    ├── test_excel_reader.py    # Reader & parser tests
    ├── test_data_profiler.py   # Profiler unit tests
    ├── test_question_generator.py # AI & Question generator tests
    ├── test_data_cleaner.py    # Cleaner & validator tests
    ├── test_exporters.py       # Exporter & formatter tests
    ├── test_statistics.py      # Statistical engine tests
    ├── test_analysis_assistant.py # NL query assistant tests
    ├── test_dashboard.py       # Chart & dashboard tests
    ├── test_safety_and_edge_cases.py # Safety & edge case tests
    ├── test_end_to_end_integration.py # E2E multi-domain tests
    └── test_app.py             # Streamlit AppTest integration tests
```

---

## Quickstart

### 1. Environment Setup
```bash
# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Tests
```bash
pytest tests/
```

### 3. Launch Application
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Roadmap

- [x] **PHASE 1:** Project setup, file upload, multi-sheet reading, and dataset overview.
- [x] **PHASE 2:** Data profiling and quality reports (anomalies, missing values, duplicates, outliers).
- [x] **PHASE 3:** AI API integration and question generation.
- [x] **PHASE 4:** Data cleaning engine, validation, and undo history.
- [x] **PHASE 5:** Excel formatting and export center (styled XLSX, CSV, HTML).
- [x] **PHASE 6:** Statistical analysis and natural-language business insights.
- [x] **PHASE 7:** Dynamic dashboard generation with interactive Plotly visuals.
- [x] **PHASE 8:** End-to-end integration testing and final polish.
