<div align="center">

# PERSONAL EXPENSE TRACKER WITH DATA VISUALIZATION
## Executive Summary Report

### **A Strategic Overview of Multi-Year Household Cash Flow, Spending Distribution, and Financial Health**

[![Deployment: GitHub Pages Active](https://img.shields.io/badge/Deployment-GitHub%20Pages%20Active-brightgreen.svg?logo=githubpages&logoColor=white)](https://girishshenoy16.github.io/personal-expense-tracker/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../LICENSE)
[![Dataset: CC0 1.0](https://img.shields.io/badge/Dataset-CC0_1.0_Universal-lightgrey.svg)](https://creativecommons.org/publicdomain/zero/1.0/)
[![Tests: 51 Pytest Passing](https://img.shields.io/badge/Tests-51%20Pytest%20Passing-0A9EDC.svg?logo=pytest&logoColor=white)](../../tests/)

---

**Prepared for**: Academic Mentors, Assessors & Financial Stakeholders  
**Author**: Girish Shenoy  
**Observation Window**: 2015-01-01 to 2018-09-20 (1,359 Calendar Days · 45 Calendar Months)  
**Live Interactive Dashboard**: [https://girishshenoy16.github.io/personal-expense-tracker/](https://girishshenoy16.github.io/personal-expense-tracker/)

---

</div>

## 1. Executive Scorecard

<div align="center">

| Core Financial Metric | Measured Value | Strategic Benchmark & Definition |
|:---|:---:|:---|
| **Observation Window** | **1,359 Calendar Days** | 45 calendar months (2015-01-01 to 2018-09-20) |
| **Total Cash Inflow (Income)** | **₹3,042,397.35** | Total operational household earnings and inflow |
| **Total Operational Outflow (Expenses)** | **₹1,957,390.53** | Total consumption spending on living necessities and services |
| **Capital Transfers & Investments** | **₹1,770,780.90** | Isolated capital reallocations (Mutual Funds, PPF, bank transfers) |
| **Net Cash Flow (NCF)** | **₹1,085,006.82** | Operational liquidity surplus: $\text{NCF} = \text{Income} - \text{Expenses}$ |
| **Operational Cash Surplus Margin** | **35.66%** | Savings efficiency ratio: $[(\text{Income} - \text{Expenses}) / \text{Income}] \times 100$ |
| **Daily Average Burn Rate** | **₹1,440.32 / day** | Full calendar span burn: $\text{Expenses} / 1,359 \text{ days}$ |
| **Weekday Daily Average Spend** | **₹1,432.63 / day** | Workday baseline burn: ₹1,391,087.40 across 971 calendar weekdays |
| **Weekend Daily Average Spend** | **₹1,459.54 / day** | Weekend burn: ₹566,303.13 across 388 calendar weekend days (+1.88%) |

</div>

> [!NOTE]
> **Balance Sheet Isolation Policy**: Capital transfers-out into investments (e.g. Public Provident Fund, Mutual Funds) and inter-bank transfers (₹1,770,780.90) are strictly isolated from operational living expenses. Including transfers as living expenses would distort the true household burn rate and understate savings capability.

---

## 2. Strategic Context & Problem Statement

Managing multi-year household finances requires reliable visibility into discretionary spending, fixed overheads, and true savings. Traditional expense tracking tools frequently suffer from four critical deficiencies:

1. **Conflating Investments with Consumption**: Commercial budgeting tools often treat transfers to investment vehicles (PPF, Mutual Funds) as living expenses, obscuring the true operational burn rate.
2. **Inconsistent Date Format Parsing**: Real-world transaction logs mix day-first (`DD/MM/YYYY`) and month-first (`MM/DD/YYYY`) formats, leading to corrupted monthly aggregations if parsed naively.
3. **Aggressive Deduplication Errors**: Naive deduplication routines drop legitimate recurring expenses that happen on the same calendar day (e.g., two identical transit fares).
4. **Data Privacy Hazards**: Deploying personal financial analytics online risks publishing private account descriptions, merchant narratives, or transaction IDs.

### The Engineered Solution

This project implements an end-to-end automated data pipeline that:
* **Defensively Ingests & Validates**: Audits candidate duplicates (preserving all 14 legitimate recurring rows) and standardizes 2,461 records into a clean 16-field schema with 100% accounting reconciliation.
* **Isolates Capital Transfers**: Strictly separates ₹1,770,780.90 in capital reallocations from living expenses to maintain financial accounting integrity.
* **Generates Dual Visualization Formats**: Compiles 5 publication-ready 300 DPI static figures for reports and delivers an interactive client-side dashboard on GitHub Pages.
* **Enforces Privacy by Design**: Publishes only pre-aggregated summary tables (`docs/data.js`), ensuring zero transaction-level notes, IDs, or raw rows are exposed publicly.

---

## 3. Key Financial Insights & Expenditure Dynamics

### 3.1 Cash Surplus & Financial Health
* **Substantial Surplus Efficiency**: The household achieved an **operational surplus margin of 35.66%**, retaining ₹35.66 out of every ₹100 earned.
* **Positive Cash Generation**: Cumulative net cash flow reached **₹1,085,006.82** over the 45-month period, demonstrating sustained positive cash flow throughout all major market cycles.
* **Disciplined Capital Accumulation**: In addition to operational surplus, **₹1,770,780.90** was channeled into long-term investments and savings instruments.

### 3.2 Expenditure Concentration & Pareto Analysis

<div align="center">

| Spending Category | Total Expenditure | Share of Living Expenses | Cumulative Share | Strategic Category Context |
|:---|:---:|:---:|:---:|:---|
| **Money Transfer** | ₹606,528.90 | 30.99% | 30.99% | Inter-account capital settlements and remittances |
| **Investment** | ₹271,858.00 | 13.89% | 44.88% | Direct portfolio investments and deposits |
| **Transportation** | ₹169,053.78 | 8.64% | 53.52% | Daily commuting, transit fares, and vehicle fuel |
| **Household** | ₹161,645.58 | 8.26% | 61.78% | Domestic utilities, housing supplies, and maintenance |
| **Subscription** | ₹114,587.91 | 5.85% | 67.63% | Operational household expenditures |
| **Remaining 22 Categories** | ₹633,716.36 | 32.38% | 100.00% | Healthcare, apparel, education, gifts & miscellaneous |

</div>

* **Pareto Concentration**: The top 5 spending categories account for **67.63%** of total living expenses.
* **Essential vs. Discretionary Balance**: Non-discretionary commitments (Money Transfer, Investment, Transportation, Household) represent over 60% of all outflow, while direct food and dining account for less than 5%.

### 3.3 Payment Instrument Utilization

<div align="center">

| Payment Instrument | Outflow Amount | Allocation Share | Transactions | Operational Role |
|:---|:---:|:---:|:---:|:---|
| **Saving Bank account 1** | ₹1,577,728.46 | 80.60% | 971 | Primary operating bank account for household cash flow |
| **Credit Card** | ₹205,254.01 | 10.49% | 162 | Secondary instrument for retail, online, and recurring bills |
| **Cash** | ₹173,431.00 | 8.86% | 1,039 | Everyday micro-transactions, local transit, and vendor purchases |
| **Debit Card** | ₹942.36 | 0.05% | 2 | Incidental direct POS expenditures |
| **Saving Bank account 2** | ₹34.70 | 0.00% | 2 | Dormant / minimal secondary account |

</div>

* **Single-Account Concentration**: 80.60% of all living expenses flow through **Saving Bank Account 1**, providing centralized visibility but indicating an opportunity to optimize transaction routing and credit rewards.
* **Controlled Credit Usage**: Credit card expenditure is capped at **10.49%** (₹205,372.00), indicating disciplined credit utilization without revolving debt exposure.

### 3.4 Temporal Spending Patterns
* **Predictable Daily Baseline**: The household operates at an average burn rate of **₹1,440.32/day** across all 1,359 calendar days.
* **Weekend Lifestyle Surge**: Weekend daily spending surges to **₹1,459.54/day**—a **+1.88% premium** over the weekday average of **₹1,432.63/day**. This reflects consolidated weekend shopping, dining, and family activities.

---

## 4. System Deliverables & Public Access

<div align="center">

| Deliverable | Access Location | Description & Strategic Value |
|:---|:---|:---|
| **Interactive Web Dashboard** | [Live on GitHub Pages](https://girishshenoy16.github.io/personal-expense-tracker/) | 6 KPI cards, 11 Chart.js charts, 6 slicers, paginated explorer, CSV export |
| **Dashboard Visual Preview** | [`outputs/dashboard_image.png`](../dashboard_image.png) | High-resolution visual capture of the deployed web dashboard |
| **Static Publication Suite** | [`outputs/plots/`](../plots/README.md) | 5 publication-ready 300 DPI analytical charts (`.png`) |
| **Monthly Summary Dataset** | [`outputs/reports/monthly_summary.csv`](monthly_summary.csv) | 45-month trend time-series (Inflow, Outflow, Transfers, NCF, MoM, SMA3) |
| **Category Summary Dataset** | [`outputs/reports/category_summary.csv`](category_summary.csv) | 27-category expenditure hierarchy with itemized subcategories |
| **Authoritative Engineering Report** | [`outputs/reports/project_report.md`](project_report.md) | Detailed technical report covering schemas, formulas, and audit tests |

</div>

---

## 5. Strategic Recommendations for Household Financial Governance

1. **Establish a Dedicated Weekend Discretionary Budget**:
   * *Observation*: Weekend daily burn is +1.88% higher than weekday spend, driven by dining, leisure, and weekend grocery runs.
   * *Action*: Implement a weekly weekend discretionary budget cap of ₹2,500 to prevent lifestyle inflation without compromising quality of life.

2. **Optimize Payment Instrument Rewards**:
   * *Observation*: ₹205k+ was spent across credit cards and ₹1.58M through bank accounts.
   * *Action*: Route routine utility, grocery, and fuel payments through reward-yielding credit cards with automatic full balance clearance to capture 2–4% annual rewards.

3. **Automate Surplus Capital Allocation**:
   * *Observation*: The household consistently achieves a 35.66% cash surplus margin.
   * *Action*: Automate systematic monthly transfers into diversified index funds and debt instruments on the 1st of every calendar month, ensuring liquidity surpluses are invested immediately.

4. **Maintain Strict Privacy Separation**:
   * *Observation*: Public web dashboards require strict separation from raw transactional records.
   * *Action*: Continue the zero-transaction public payload model (`docs/data.js`), ensuring personal merchant notes and account numbers remain strictly on secure local storage.

---

## 6. Verification and Quality Assurance Summary

<div align="center">

| Verification Domain | Testing Mechanism | Checks | Result |
|:---|:---|:---:|:---:|
| **Financial Formulas & Metrics** | `tests/test_financial_metrics.py` | 22 | ✅ PASS |
| **Data Cleaning & Schema Conformance** | `tests/test_data_validation.py` | 14 | ✅ PASS |
| **Logger Resilience & Security** | `tests/test_logger_resilience.py` | 6 | ✅ PASS |
| **Pipeline & Artifact Integration** | `tests/test_pipeline.py` | 5 | ✅ PASS |
| **Reports & CSV Summaries** | `tests/test_reports.py` | 4 | ✅ PASS |
| **Production Pipeline Parity** | `tests/validate_pipeline.py` | 7 | ✅ PASS |
| **Dashboard UI & Explorer** | `test_refinements.js` | 41 | ✅ PASS |
| **Chart Interactivity & Contrast** | `test_interactivity_readability.js` | 61 | ✅ PASS |
| **Headless Browser E2E** | Chrome DevTools Protocol (CDP) | Full Suite | ✅ 0 Console Errors |
| **Total Automated Quality Suite** | **Multi-Tier Automated Testing** | **160 Checks** | **100% Verified** |

</div>

---

<div align="center">

**Girish Shenoy**  
[GitHub Profile](https://github.com/girishshenoy16) · [LinkedIn Profile](https://linkedin.com/in/girishshenoys) · [Email](mailto:girishpshenoy09@gmail.com)

*Personal Expense Tracker with Data Visualization — Version 1.0 — MIT License*

</div>
