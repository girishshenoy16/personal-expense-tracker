"""Integration Tests for Pipeline Execution and Artifact Generation.

Verifies end-to-end data processing, intermediate CSV generation, static
Matplotlib plotting, client-side payload contract generation, and cross-system
parity using isolated temporary directories without altering production data.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

import pandas as pd
import pytest

from src.analyzer import FinancialAnalyzer
from src.cleaner import clean_dataset
from src.plotter import generate_all_plots
from src.reporter import generate_reports


@pytest.mark.integration
class TestEndToEndPipeline:
    """End-to-end integration tests using isolated temporary directories."""

    @pytest.fixture(autouse=True)
    def setup_pipeline_env(self, tmp_path: Path, sample_raw_csv: Path):
        """Execute complete pipeline in isolated temporary environment."""
        self.tmp_data_dir = tmp_path / "data"
        self.tmp_outputs_dir = tmp_path / "outputs"
        self.tmp_docs_dir = tmp_path / "docs"

        self.proc_csv = self.tmp_data_dir / "processed_transactions.csv"
        self.dup_csv = self.tmp_data_dir / "duplicate_audit.csv"
        self.rej_csv = self.tmp_data_dir / "rejected_records.csv"
        self.payload_js = self.tmp_docs_dir / "data.js"
        self.plots_dir = self.tmp_outputs_dir / "plots"
        self.reports_dir = self.tmp_outputs_dir / "reports"

        # 1. Cleaning
        self.clean_res = clean_dataset(
            raw_csv_path=sample_raw_csv,
            processed_csv_path=self.proc_csv,
            duplicate_audit_path=self.dup_csv,
            rejected_records_path=self.rej_csv,
        )

        # 2. Analysis & Payload Export
        self.analyzer = FinancialAnalyzer.from_csv(self.proc_csv)
        self.payload = self.analyzer.export_data_payload_js(self.payload_js)

        # 3. Static Plot Generation
        self.plot_files = generate_all_plots(
            processed_csv=self.proc_csv,
            plots_dir=self.plots_dir,
        )

        # 4. Reports Compilation
        self.report_res = generate_reports(
            processed_csv=self.proc_csv,
            reports_dir=self.reports_dir,
        )

    def test_pipeline_produces_all_expected_artifacts(self):
        """Verify all intermediate and final pipeline deliverables are generated on disk."""
        # Data artifacts
        assert self.proc_csv.exists()
        assert self.dup_csv.exists()
        assert self.rej_csv.exists()
        assert self.payload_js.exists()

        # Plots
        assert len(self.plot_files) == 5
        for p in self.plot_files:
            assert p.exists()
            assert p.stat().st_size > 10_000  # Non-empty high-res image

        # Reports
        assert self.report_res["report_md"].exists()
        assert self.report_res["executive_md"].exists()
        assert self.report_res["monthly_csv"].exists()
        assert self.report_res["category_csv"].exists()

    def test_payload_js_structure_and_privacy_contract(self):
        """Verify data.js adheres strictly to the aggregated public data contract."""
        with open(self.payload_js, "r", encoding="utf-8") as f:
            content = f.read()

        # Check window.EXPENSE_DATA wrapper
        match = re.search(r"window\.EXPENSE_DATA\s*=\s*(\{[\s\S]*\});\s*$", content)
        assert match is not None, "Payload missing window.EXPENSE_DATA assignment!"

        parsed_json = json.loads(match.group(1))

        # Check required schema keys
        assert "meta" in parsed_json
        assert "kpis_overall" in parsed_json
        assert "monthly_series" in parsed_json
        assert "category_summary" in parsed_json
        assert "payment_mode_summary" in parsed_json
        assert "day_type_summary" in parsed_json
        assert "filters" in parsed_json

        # Strict Privacy Standard: Zero transaction rows or notes in JS payload
        assert "transaction_id" not in content
        assert "GEN-TXN-" not in content
        assert "Monthly Salary Credit" not in content
        assert "Repair duplicate payment retry" not in content

    def test_python_analyzer_and_payload_cross_system_parity(self):
        """Verify mathematical parity between Python FinancialAnalyzer and exported payload."""
        py_kpis = self.analyzer.compute_kpis()
        js_kpis = self.payload["kpis_overall"]

        assert py_kpis["total_income"] == pytest.approx(js_kpis["total_income"], abs=0.01)
        assert py_kpis["total_expense"] == pytest.approx(js_kpis["total_expense"], abs=0.01)
        assert py_kpis["total_transfers"] == pytest.approx(js_kpis["total_transfers"], abs=0.01)
        assert py_kpis["net_cash_flow"] == pytest.approx(js_kpis["net_cash_flow"], abs=0.01)
        assert py_kpis["daily_burn_rate"] == pytest.approx(js_kpis["daily_burn_rate"], abs=0.01)

    def test_pipeline_failure_on_missing_input_file(self, tmp_path: Path):
        """Verify clean_dataset raises FileNotFoundError on non-existent raw file."""
        non_existent_file = tmp_path / "non_existent_raw.csv"
        with pytest.raises(FileNotFoundError):
            clean_dataset(
                raw_csv_path=non_existent_file,
                processed_csv_path=tmp_path / "proc.csv",
                duplicate_audit_path=tmp_path / "dup.csv",
                rejected_records_path=tmp_path / "rej.csv",
            )

    def test_analyzer_failure_on_missing_processed_file(self, tmp_path: Path):
        """Verify FinancialAnalyzer.from_csv raises FileNotFoundError when file is absent."""
        missing_csv = tmp_path / "missing_proc.csv"
        with pytest.raises(FileNotFoundError):
            FinancialAnalyzer.from_csv(missing_csv)
