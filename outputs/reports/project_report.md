# Personal Expense Tracker with Data Visualization
## Authoritative Engineering & Financial Analytics Report

---

### Executive Summary

The **Personal Expense Tracker with Data Visualization** is an end-to-end financial intelligence engineering project designed to ingest, clean, audit, analyze, and visualize multi-year personal finance records. The analysis covers **1,359 calendar days** of transactional data between **2015-01-01** and **2018-09-20**, tracking cash inflows, household operational expenses, and asset transfers/investments.

The primary objective is to deliver reliable personal financial intelligence through reproducible data engineering, mathematical reconciliation, static publication-quality graphics, and an interactive static web dashboard deployed on GitHub Pages.

#### Key Executive Metrics
* **Total Cash Inflow (Income)**: **₹3,042,397.35**
* **Total Operational Outflow (Expenses)**: **₹1,957,390.53**
* **Total Capital Transfers (Investments/Transfers-Out)**: **₹1,770,780.90**
* **Net Cash Flow (NCF)**: **₹1,085,006.82**
* **Operational Cash Surplus Margin**: **35.66%**
* **Daily Average Burn Rate**: **₹1,440.32 / day** across 1,359 calendar days
* **Tracking Period**: **2015-01-01** to **2018-09-20** (1,359 calendar days / 45 months)
* **Authoritative Currency**: **INR (INR ₹)**

> [!NOTE]
> **Balance Sheet Isolation Policy**: Transfers-Out (capital movements into Public Provident Fund, Mutual Funds, Fixed Deposits, and inter-account transfers) are strictly separated from consumption expenses. Treating capital reallocations as operational consumption would artificially depress true savings and distort personal burn rate calculations.

---

### 1. Dataset Provenance & Dynamic Profiling

* **Dataset Title**: *Daily Household Transactions*
* **Dataset Author / Curator**: Prasad Patil on Kaggle
* **Dataset License**: Public Domain (CC0 1.0 Universal)
* **Canonical Raw Path**: `data/raw/Daily Household Transactions.csv`
* **Raw Integrity**: Verified read-only raw zone with SHA-256 checksum: `809F267062E4333D3E05532D9D1B2568FCED670A1C2BCBA141BDB80344E6CFC1`.

#### Raw Dataset Structure
* **Total Raw Records**: **2,461 rows**
* **Raw Fields (8)**: `Date`, `Mode`, `Category`, `Subcategory`, `Note`, `Amount`, `Income/Expense`, `Currency`
* **Empirical Date Variations**: Inspected date strings containing day-token values exceeding 12 (e.g. `20/09/2018 12:04:08`), confirming day-first ordering (`DD/MM/YYYY`) with optional timestamps. Dates were dynamically parsed without hardcoded assumptions.
* **Currency Uniformity**: 100% of non-null records recorded `INR`, verified empirically across all rows.

---

### 2. Defensive Data Cleaning & Engineering Pipeline

The data cleaning pipeline (`src/cleaner.py`) applies deterministic domain validation rules:

1. **Defensive Date & Time Parsing**:
   - Dates converted to canonical `YYYY-MM-DD`.
   - Extracted optional time string `HH:MM:SS` and derived the boolean flag `time_available` (zero artificial `00:00:00` values fabricated).
   - Extracted calendar features: `year`, `month`, `month_year` (`YYYY-MM`), `day_name`, and `is_weekend`.
2. **Conservative Duplicate Audit**:
   - 14 potential duplicate candidates sharing identical dates, modes, categories, and amounts were audited into `data/processed/duplicate_audit.csv`.
   - In accordance with personal finance domain realities (where identical recurring expenses such as transit fares or groceries frequently occur on the same date), all 14 records were verified as legitimate distinct transactions and retained with status `retained_ambiguous_duplicate`.
3. **Imputation & Categorical Hygiene**:
   - Missing subcategories were imputed with `'General'` while strictly preserving parent category boundaries.
   - Missing note values were imputed with `'No description provided'` (retained internally; excluded from public deliverables).
4. **Surrogate Sequential Identifier**:
   - Assigned deterministic surrogate primary keys (`GEN-TXN-0001` through `GEN-TXN-2461`) after sorting chronologically by date and time.
5. **Row-Count Reconciliation Balance**:
   $$\text{Total Raw Records} (2,461) = \text{Retained Records} (2,461) + \text{Rejected Records} (0) + \text{Deduplicated Records} (0)$$
   **Reconciliation Status: 100% Balanced.**

---

### 3. Authoritative Processed 16-Column Schema

The processed transactional dataset (`data/processed/processed_transactions.csv`) conforms to the 16-field standard:

| # | Field Name | Data Type | Nullable | Description & Domain Rules |
| :-: | :--- | :--- | :-: | :--- |
| **1** | `transaction_id` | String | No | Deterministic sequential surrogate key (`GEN-TXN-0001`...) |
| **2** | `date` | Date (ISO) | No | Normalized calendar date (`YYYY-MM-DD`) |
| **3** | `time` | String | Yes | Extracted time (`HH:MM:SS`) if present in raw data; null otherwise |
| **4** | `time_available` | Boolean | No | `True` if time was explicitly present; `False` if absent |
| **5** | `year` | Integer | No | Extracted calendar year (`2015`–`2018`) |
| **6** | `month` | Integer | No | Extracted calendar month number (`1`–`12`) |
| **7** | `month_year` | String | No | Normalized period token (`YYYY-MM`) |
| **8** | `day_name` | String | No | Day of week (`Monday` through `Sunday`) |
| **9** | `is_weekend` | Boolean | No | `True` for Saturday and Sunday; `False` for Monday through Friday |
| **10** | `payment_mode` | String | No | Sanitized payment instrument (e.g., `Saving Bank account 1`, `Cash`) |
| **11** | `category` | String | No | Standardized primary transaction category |
| **12** | `subcategory` | String | No | Imputed `'General'` if missing; parent category preserved |
| **13** | `note` | String | No | Internal audit narrative; excluded from public web artifacts |
| **14** | `transaction_type` | String | No | Verified taxonomy: `Expense`, `Income`, `Transfer-Out` |
| **15** | `amount` | Float | No | Clean numeric currency value rounded to 2 decimal places |
| **16** | `currency` | String | No | Verified currency code (`INR`) |

---

### 4. Mathematical Formulations & Financial Logic

All financial formulas are implemented with division-by-zero guards and strict edge-case safety:

1. **Net Cash Flow (NCF)**:
   $$\text{NCF} = \sum \text{Income} - \sum \text{Expense}$$
   $$\text{NCF} = ₹3,042,397.35 - ₹1,957,390.53 = ₹1,085,006.82$$

2. **Operational Cash Surplus Margin ($M_s$)**:
   $$M_s = \frac{\sum \text{Income} - \sum \text{Expense}}{\sum \text{Income}} \times 100$$
   *Guarded against zero income: returns `N/A (Zero Income)` if income is zero.*
   $$M_s = \frac{₹1,085,006.82}{₹3,042,397.35} \times 100 = 35.66\%$$

3. **Daily Average Burn Rate ($B_d$)**:
   $$B_d = \frac{\sum \text{Expense}}{N_{\text{calendar days}}}$$
   *Uses true calendar duration ($T_{\max} - T_{\min} + 1 = 1359$ days) rather than active transaction days.*
   $$B_d = \frac{₹1,957,390.53}{1359} = ₹1,440.32 / \text{day}$$

4. **Trailing 3-Month Simple Moving Average ($\text{SMA}_3$)**:
   $$\text{SMA}_{3, t} = \frac{E_t + E_{t-1} + E_{t-2}}{3}$$
   *Guarded with consecutiveness verification: $(Y_t \cdot 12 + M_t) - (Y_{t-1} \cdot 12 + M_{t-1}) = 1$. Non-consecutive months return `null` without fabrication.*

5. **Month-over-Month Expense Growth ($G_{\text{MoM}}$)**:
   $$G_{\text{MoM}, t} = \frac{E_t - E_{t-1}}{E_{t-1}} \times 100$$
   *Guarded against non-consecutive months and zero prior-month expense ($E_{t-1} = 0$).*

---

### 5. Exploratory Data Analysis & Empirical Findings

#### Top Spending Categories
Across 27 distinct categories, the top 10 categories account for **89.00%** of all consumption expenditure:

| Rank | Category | Total Spend (₹) | Transaction Count | % of Expenses |
| :-: | :--- | :-: | :-: | :-: |
| 1 | Money Transfer | ₹606,528.90 | 43 | 30.99% |
| 2 | Investment | ₹271,858.00 | 103 | 13.89% |
| 3 | Transportation | ₹169,053.78 | 307 | 8.64% |
| 4 | Household | ₹161,645.58 | 176 | 8.26% |
| 5 | Subscription | ₹114,587.91 | 143 | 5.85% |
| 6 | Food | ₹96,403.10 | 907 | 4.93% |
| 7 | Public Provident Fund | ₹90,000.00 | 8 | 4.60% |
| 8 | Other | ₹87,025.28 | 114 | 4.45% |
| 9 | Family | ₹78,582.20 | 71 | 4.01% |
| 10 | Health | ₹66,252.75 | 94 | 3.38% |

#### Payment Mode Distribution
Transactions span 5 distinct payment modes:

| Rank | Payment Mode | Total Spend (₹) | Transaction Count | % of Expenses |
| :-: | :--- | :-: | :-: | :-: |
| 1 | Saving Bank account 1 | ₹1,577,728.46 | 971 | 80.60% |
| 2 | Credit Card | ₹205,254.01 | 162 | 10.49% |
| 3 | Cash | ₹173,431.00 | 1,039 | 8.86% |
| 4 | Debit Card | ₹942.36 | 2 | 0.05% |
| 5 | Saving Bank account 2 | ₹34.70 | 2 | 0.00% |

#### Temporal Behavior: Weekday vs. Weekend
* **Weekday Daily Average**: **₹1,432.63** across 971 calendar weekdays (Total: ₹1,391,087.40)
* **Weekend Daily Average**: **₹1,459.54** across 388 calendar weekend days (Total: ₹566,303.13)
* **Weekend Uptick**: Daily expenditure on weekends is **+1.88% higher** than on weekdays.

---

### 6. Static Analytical Plots Suite (`outputs/plots/`)

Generated deterministically by `src/plotter.py` at **300 DPI**:

1. `monthly_income_vs_expenses.png` — Grouped bar comparison of income and expenses across 45 months.
2. `expense_category_breakdown.png` — Pareto horizontal bar chart ranking top spending categories.
3. `payment_mode_distribution.png` — Two-panel figure showing expense amount and transaction frequency per mode.
4. `income_expense_trend.png` — Multi-line trajectory showing Income, Expense, and 3-month trailing SMA.
5. `weekday_vs_weekend_spending.png` — Side-by-side bar chart showing total spend and daily average spend.
6. `README.md` — Complete plot documentation and visual specifications.

---

### 7. Interactive Power BI-Style Web Dashboard (`docs/`)

* **Core Files**: `docs/index.html`, `docs/style.css`, `docs/app.js`, `docs/data.js`
* **Charting Engine**: **Chart.js 4.4.4** (loaded via CDN)
* **Architecture**: 100% static, client-side, zero-backend runtime dependency, ready for GitHub Pages.
* **Component Architecture**:
  - **6 Reactive KPI Cards**: Total Income, Total Expenses, Total Invested, Net Savings Rate, Avg Monthly Spend, Top Category.
  - **11 Interactive Chart.js Charts**: Trend, Type Donut, Top Categories, Payment Mode, Weekend, Net Savings, YoY, Investment Donut, Day of Week, Frequency vs Value Bubble, Cumulative Net Position.
  - **Slicers & Controls**: Year, Month, Type, Category, Mode, Day filters, Reset button, and Total Period / Monthly Avg toggle.
  - **Auto-Generated Insights**: Dynamic analytical findings.
  - **Category Drill-Down**: Subcategory breakdown table with percentage of category.
  - **Aggregated Data Explorer**: Centered 5-record table, centered Previous/Next pagination, centered scaling note, and filter-aware aggregated CSV export.
  - **Public Data Privacy**: Consumes `docs/data.js` (`window.EXPENSE_DATA`). Strictly zero transaction-level records, zero notes, zero transaction IDs.

---

### 8. Quality Assurance & Automated Testing Verification

The automated Quality Assurance suite consists of **51 Pytest assertions** across 5 specialized test modules, alongside the **7-point end-to-end pipeline validation suite** (`tests/validate_pipeline.py`) and **102 client-side dashboard checks**, achieving a **100% pass rate (160/160 verified)**:

#### Automated Pytest Test Suite (`python -m pytest` — 51/51 Passed)
* **`tests/test_financial_metrics.py` (22 Tests)**: Validates Income, Expense, and Transfer-Out separation, Net Cash Flow ($NCF = I - E$), Cash Surplus Margin ($M_s$), Calendar-Day Burn Rate ($B_d$), Weekday vs Weekend spending, consecutive MoM growth rates, Trailing 3-Month Moving Average ($SMA_3$), Pareto category concentration shares, payment instrument distributions, and multi-dimensional filter isolation.
* **`tests/test_data_validation.py` (14 Tests)**: Validates 16-field authoritative schema definition, empirical DD/MM/YYYY date and time parsing, duplicate classification (ambiguous vs technical repost), missing value imputation defaults (`General`, `No description provided`, `Cash`, `INR`), sequential surrogate key formatting (`GEN-TXN-0001`...), SHA-256 raw file hashing, and mathematical row-count accounting reconciliation balance ($N_{raw} = N_{retained} + N_{rejected} + N_{dedup}$).
* **`tests/test_logger_resilience.py` (6 Tests)**: Validates regex redaction for 13-16 digit account/card numbers, free-text narrative note masking (`[REDACTED_NOTE]`), recursive argument sanitization, file logging output, error-level routing, and graceful `sys.stderr` fallback upon simulated disk I/O lock.
* **`tests/test_pipeline.py` (5 Tests)**: Validates end-to-end execution across isolated temporary directories (`tmp_path`), artifact generation (`processed_transactions.csv`, `duplicate_audit.csv`, `rejected_records.csv`, `data.js`, 5 plots, 4 report deliverables), pre-aggregated privacy contract compliance, and cross-system calculation parity between Python and JavaScript.
* **`tests/test_reports.py` (4 Tests)**: Validates monthly and category summary CSV exports, project report markdown compilation, executive summary scorecard compilation, and directory orchestrator execution.

#### Standalone End-to-End Pipeline Validation Suite (`tests/validate_pipeline.py` — 7/7 Passed)
* **Test 1 — Schema Conformance & Strict Typing**: PASSED (16 columns, correct dtypes, 0 unhandled nulls)
* **Test 2 — Row-Count Accounting Reconciliation**: PASSED (2,461 raw == 2,461 retained + 0 rejected + 0 deduplicated)
* **Test 3 — Financial Mathematics Reconciliation**: PASSED (NCF == Income - Expense, Transfers isolated)
* **Test 4 — Edge-Case & Mathematical Division Safety**: PASSED (Zero-income, zero-expense, non-consecutive guards)
* **Test 5 — Public Data Privacy & Contract Audit**: PASSED (Zero transaction IDs or private notes in web payload)
* **Test 6 — Cross-System & Filter Parity**: PASSED (Python analyzer matches `docs/data.js` to 2 decimal places)
* **Test 7 — Static Plot File Integrity**: PASSED (5 plots > 50 KB, 300 DPI, README verified)

#### Dashboard Client-Side & UI Verification (102 Checks Passed)
* **41/41 Passed** in `test_refinements.js` (pagination navigation, 5-row page size, CSV export parity).
* **61/61 Passed** in `test_interactivity_readability.js` (Chart.js interactions, tooltips, slicers).
* **Live Headless Edge CDP**: 0 console errors, 0 failed network requests, zero horizontal overflow across 1400px, 768px, and 375px viewports.

---

### 9. Tested Environment & Dependency Specifications

* **Python Runtime**: Python 3.11+
* **Tested Package Versions (`venv`)**:
  - `pytest==9.1.1`
  - `pandas==3.0.6`
  - `matplotlib==3.11.2`
  - `numpy==2.4.6`
  - `pillow==12.3.0`
  - `python-dateutil==2.9.0.post0`
  - `pip==26.2.1`

---

*Report generated deterministically on 2026-09-28 20:34:46 by `src/reporter.py`.*
