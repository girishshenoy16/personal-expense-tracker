"""Unit Tests for Report Generation and CSV Summaries.

Validates report compilation (project report, executive summary) and
summary CSV exports in src/reporter.py using deterministic analyzer fixtures.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest

from src.analyzer import FinancialAnalyzer
from src.reporter import (
    build_executive_summary_markdown,
    build_project_report_markdown,
    export_summary_csvs,
    generate_reports,
)


@pytest.mark.unit
class TestSummaryCSVExports:
    """Tests summary CSV structure and numerical correctness."""

    def test_export_summary_csvs(self, deterministic_analyzer: FinancialAnalyzer, tmp_path: Path):
        """Verify export_summary_csvs outputs valid monthly and category CSVs."""
        m_csv, c_csv = export_summary_csvs(deterministic_analyzer, tmp_path)
        assert m_csv.exists()
        assert c_csv.exists()

        # Check monthly CSV headers and rows
        with open(m_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == [
                "year", "month", "month_year", "total_income", "total_expense",
                "total_transfers", "net_cash_flow", "mom_expense_growth_pct", "sma3_expense"
            ]
            rows = list(reader)
            assert len(rows) == 2
            # Month 1: 2018-01
            assert rows[0][0] == "2018"
            assert rows[0][2] == "2018-01"
            assert rows[0][3] == "100000.00"
            assert rows[0][4] == "30000.00"

        # Check category CSV headers and rows
        with open(c_csv, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == [
                "category", "subcategory", "total_spend", "transaction_count", "category_percentage_share"
            ]
            rows = list(reader)
            # Household (Rent) and Food (Dining)
            assert len(rows) == 2


@pytest.mark.unit
class TestMarkdownReportGeneration:
    """Tests Markdown report generation and KPI string formatting."""

    def test_build_project_report_markdown(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify project report markdown contains expected titles and formatted KPIs."""
        md = build_project_report_markdown(deterministic_analyzer)
        assert "# Personal Expense Tracker with Data Visualization" in md
        assert "Total Cash Inflow (Income)" in md
        assert "₹200,000.00" in md
        assert "Total Operational Outflow (Expenses)" in md
        assert "₹70,000.00" in md
        assert "Net Cash Flow (NCF)" in md
        assert "₹130,000.00" in md
        assert "65.0%" in md

    def test_build_executive_summary_markdown(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify executive summary markdown contains scorecard and strategic analysis."""
        md = build_executive_summary_markdown(deterministic_analyzer)
        assert "Executive Summary Report" in md
        assert "Executive Scorecard" in md
        assert "₹200,000.00" in md
        assert "65.0%" in md
        assert "Expenditure Concentration & Pareto Analysis" in md


@pytest.mark.unit
class TestReportsOrchestrator:
    """Tests the high-level generate_reports orchestrator function."""

    def test_generate_reports_in_temp_dir(self, deterministic_processed_df: pd.DataFrame, tmp_path: Path):
        """Verify generate_reports executes end-to-end to a designated output folder."""
        proc_csv = tmp_path / "processed.csv"
        deterministic_processed_df.to_csv(proc_csv, index=False, encoding="utf-8")
        reports_dir = tmp_path / "reports_out"

        result = generate_reports(processed_csv=proc_csv, reports_dir=reports_dir)
        assert result["report_md"].exists()
        assert result["report_md"].stat().st_size > 1000
        assert result["executive_md"].exists()
        assert result["executive_md"].stat().st_size > 1000
        assert result["monthly_csv"].exists()
        assert result["category_csv"].exists()
