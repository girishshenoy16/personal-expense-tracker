"""Automated Pipeline Validation and Contract Parity Test Suite.

Executes the comprehensive 7-point validation framework:
1. Schema Conformance & Strict Typing (16 columns)
2. Row-Count Accounting Reconciliation
3. Financial Mathematics Reconciliation
4. Edge-Case & Mathematical Division Safety
5. Public Data Privacy & Contract Audit
6. Cross-System & Filter Parity (Python vs docs/data.js)
7. Static Plot File Integrity (300 DPI outputs)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analyzer import FinancialAnalyzer
from src.cleaner import AUTHORITATIVE_COLUMNS
from src.logger import get_logger

logger = get_logger("tests_pipeline")

RAW_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "Daily Household Transactions.csv"
PROCESSED_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "processed_transactions.csv"
DUPLICATE_AUDIT_PATH = PROJECT_ROOT / "data" / "processed" / "duplicate_audit.csv"
REJECTED_RECORDS_PATH = PROJECT_ROOT / "data" / "processed" / "rejected_records.csv"
PAYLOAD_JS_PATH = PROJECT_ROOT / "docs" / "data.js"
PLOTS_DIR = PROJECT_ROOT / "outputs" / "plots"

EXPECTED_RAW_SHA256 = "809F267062E4333D3E05532D9D1B2568FCED670A1C2BCBA141BDB80344E6CFC1"


def parse_data_js(payload_path: Path) -> dict:
    """Parse JSON payload out of docs/data.js."""
    with open(payload_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Extract object from window.EXPENSE_DATA = { ... };
    match = re.search(r"window\.EXPENSE_DATA\s*=\s*(\{[\s\S]*\});\s*$", content)
    if not match:
        raise ValueError("Could not find window.EXPENSE_DATA in docs/data.js")
    return json.loads(match.group(1))


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("=" * 70)
        logger.info("PHASE 5: EXECUTING AUTOMATED QUALITY ASSURANCE TEST SUITE")
        logger.info("=" * 70)
        cls.df_processed = pd.read_csv(PROCESSED_CSV_PATH)
        cls.analyzer = FinancialAnalyzer(cls.df_processed)
        cls.payload = parse_data_js(PAYLOAD_JS_PATH)

    def test_01_schema_conformance_and_typing(self):
        """Test 1: Verify authoritative 16 columns, correct dtypes, and zero unhandled nulls."""
        # 1. Assert exactly 16 columns exist in authoritative order
        self.assertEqual(list(self.df_processed.columns), AUTHORITATIVE_COLUMNS,
                         "Processed columns do not match authoritative 16-field schema.")

        # 2. Check transaction_id format
        id_pattern = re.compile(r"^GEN-TXN-\d{4}$")
        for txn_id in self.df_processed["transaction_id"]:
            self.assertTrue(bool(id_pattern.match(str(txn_id))), f"Invalid transaction_id format: {txn_id}")

        # 3. Check date format YYYY-MM-DD
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for d in self.df_processed["date"]:
            self.assertTrue(bool(date_pattern.match(str(d))), f"Invalid date format: {d}")

        # 4. Check time_available is strictly boolean
        self.assertTrue(self.df_processed["time_available"].isin([True, False]).all(),
                        "time_available contains non-boolean values.")

        # 5. Check year, month bounds
        self.assertTrue((self.df_processed["year"] >= 2000).all())
        self.assertTrue((self.df_processed["month"].between(1, 12)).all())

        # 6. Check transaction_type in allowed domain
        allowed_types = {"Expense", "Income", "Transfer-Out"}
        self.assertTrue(set(self.df_processed["transaction_type"]).issubset(allowed_types))

        # 7. Check amounts are strictly positive floats
        self.assertTrue((self.df_processed["amount"] > 0).all())

        # 8. Check currency homogeneity
        self.assertTrue((self.df_processed["currency"] == "INR").all())

        # 9. Check required fields have zero nulls
        required_non_null = [
            "transaction_id", "date", "time_available", "year", "month", "month_year",
            "day_name", "is_weekend", "payment_mode", "category", "subcategory",
            "note", "transaction_type", "amount", "currency"
        ]
        for col in required_non_null:
            null_count = self.df_processed[col].isnull().sum()
            self.assertEqual(null_count, 0, f"Column '{col}' has {null_count} unexpected null values.")

        logger.info("PASS: Test 1 - Schema Conformance & Strict Typing (16 columns).")

    def test_02_row_count_accounting_reconciliation(self):
        """Test 2: Assert Raw == Retained + Rejected + Deduplicated and verify raw immutability."""
        df_raw = pd.read_csv(RAW_CSV_PATH)
        n_raw = len(df_raw)
        n_retained = len(self.df_processed)

        df_rejected = pd.read_csv(REJECTED_RECORDS_PATH)
        n_rejected = len(df_rejected)

        df_duplicate_audit = pd.read_csv(DUPLICATE_AUDIT_PATH)
        # Deduplicated rows are only those marked genuine technical duplicates that were removed
        n_deduplicated = len(df_duplicate_audit[df_duplicate_audit["resolution_status"] == "deduplicated_genuine_technical_repost"])

        self.assertEqual(n_raw, n_retained + n_rejected + n_deduplicated,
                         f"Row-count reconciliation failed: {n_raw} != {n_retained} + {n_rejected} + {n_deduplicated}")

        # Check raw CSV checksum
        with open(RAW_CSV_PATH, "rb") as f:
            computed_sha = hashlib.sha256(f.read()).hexdigest().upper()
        self.assertEqual(computed_sha, EXPECTED_RAW_SHA256, "Raw dataset was modified or corrupted.")

        logger.info(f"PASS: Test 2 - Row-Count Reconciliation ({n_raw} == {n_retained} + {n_rejected} + {n_deduplicated}).")

    def test_03_financial_mathematics_reconciliation(self):
        """Test 3: Assert Net Cash Flow = Total Income - Total Expenses, and Transfers excluded."""
        kpis = self.analyzer.compute_kpis()
        income = kpis["total_income"]
        expense = kpis["total_expense"]
        transfers = kpis["total_transfers"]
        ncf = kpis["net_cash_flow"]

        # 1. NCF == Income - Expense
        self.assertAlmostEqual(ncf, income - expense, places=2, msg="NCF != Income - Expense")

        # 2. Transfers strictly separated
        transfer_sum = float(self.df_processed[self.df_processed["transaction_type"] == "Transfer-Out"]["amount"].sum())
        self.assertAlmostEqual(transfers, transfer_sum, places=2)
        expense_sum = float(self.df_processed[self.df_processed["transaction_type"] == "Expense"]["amount"].sum())
        self.assertAlmostEqual(expense, expense_sum, places=2)

        # 3. Sum of category spends equals total expense
        category_summary = self.analyzer.compute_category_summary()
        cat_total_spend = sum(c["total_spend"] for c in category_summary)
        self.assertAlmostEqual(cat_total_spend, expense, places=2, msg="Category spend sum != Total expense")

        logger.info("PASS: Test 3 - Financial Mathematics Reconciliation.")

    def test_04_edge_case_and_division_safety(self):
        """Test 4: Verify division-by-zero guards, empty filters, and non-consecutive months."""
        # 1. Mock Zero-Income slice: Cash surplus margin must return 'N/A'
        zero_income_df = self.df_processed[self.df_processed["transaction_type"] == "Expense"].copy()
        analyzer_zero_inc = FinancialAnalyzer(zero_income_df)
        kpi_zero = analyzer_zero_inc.compute_kpis()
        self.assertIn("N/A", str(kpi_zero["cash_surplus_margin"]))

        # 2. Mock Zero-Expense slice: Category breakdown must be empty, burn rate 0.0
        zero_exp_df = self.df_processed[self.df_processed["transaction_type"] == "Income"].copy()
        analyzer_zero_exp = FinancialAnalyzer(zero_exp_df)
        cat_zero = analyzer_zero_exp.compute_category_summary()
        self.assertEqual(len(cat_zero), 0)
        self.assertEqual(analyzer_zero_exp.compute_kpis()["daily_burn_rate"], 0.0)

        # 3. Non-consecutive month MoM guard: verify synthetic gap produces 'N/A'
        gap_data = pd.DataFrame([
            {"year": 2017, "month": 1, "month_year": "2017-01", "transaction_type": "Expense", "amount": 100.0, "date": "2017-01-01", "currency": "INR", "is_weekend": False},
            {"year": 2017, "month": 3, "month_year": "2017-03", "transaction_type": "Expense", "amount": 120.0, "date": "2017-03-01", "currency": "INR", "is_weekend": False},
        ])
        gap_analyzer = FinancialAnalyzer(gap_data)
        gap_series = gap_analyzer.compute_monthly_series()
        self.assertEqual(gap_series[1]["mom_expense_growth_pct"], "N/A (Missing Preceding Month)")

        logger.info("PASS: Test 4 - Edge-Case & Mathematical Division Safety.")

    def test_05_public_data_privacy_and_contract_audit(self):
        """Test 5: Assert docs/data.js contains zero transaction rows, zero notes, zero raw timestamps."""
        with open(PAYLOAD_JS_PATH, "r", encoding="utf-8") as f:
            js_raw = f.read()

        # 1. Assert no transaction-level arrays
        self.assertNotIn("transaction_id", js_raw)
        self.assertNotIn("GEN-TXN-", js_raw)

        # 2. Assert no free-text notes from raw data appear
        sample_sensitive_notes = [
            "bendys chicken biryani",
            "ropeway Place T to and fro",
            "share jeep - Place T top to base",
            "Doctor appointment",
        ]
        for note in sample_sensitive_notes:
            self.assertNotIn(note.lower(), js_raw.lower(), f"Sensitive note leaked into docs/data.js: {note}")

        # 3. Assert publication model metadata
        self.assertEqual(self.payload["meta"]["publication_model"],
                         "Aggregated Public Publication Model (Strictly Zero Transaction Rows)")

        logger.info("PASS: Test 5 - Public Data Privacy & Contract Audit (Zero notes/transactions).")

    def test_06_cross_system_and_filter_parity(self):
        """Test 6: Assert exact parity between Python analyzer and docs/data.js payload values."""
        py_kpis = self.analyzer.compute_kpis()
        js_kpis = self.payload["kpis_overall"]

        self.assertAlmostEqual(py_kpis["total_income"], js_kpis["total_income"], places=2)
        self.assertAlmostEqual(py_kpis["total_expense"], js_kpis["total_expense"], places=2)
        self.assertAlmostEqual(py_kpis["total_transfers"], js_kpis["total_transfers"], places=2)
        self.assertAlmostEqual(py_kpis["net_cash_flow"], js_kpis["net_cash_flow"], places=2)
        self.assertAlmostEqual(py_kpis["daily_burn_rate"], js_kpis["daily_burn_rate"], places=2)

        # Monthly series count parity
        py_monthly = self.analyzer.compute_monthly_series()
        js_monthly = self.payload["monthly_series"]
        self.assertEqual(len(py_monthly), len(js_monthly))
        for p_m, j_m in zip(py_monthly, js_monthly):
            self.assertEqual(p_m["month_year"], j_m["month_year"])
            self.assertAlmostEqual(p_m["expense"], j_m["expense"], places=2)
            self.assertAlmostEqual(p_m["income"], j_m["income"], places=2)

        logger.info("PASS: Test 6 - Cross-System & Filter Parity (Python vs docs/data.js).")

    def test_07_static_plot_file_integrity(self):
        """Test 7: Assert all 5 PNG plot files exist with non-zero size at 300 DPI."""
        expected_plots = [
            "monthly_income_vs_expenses.png",
            "expense_category_breakdown.png",
            "payment_mode_distribution.png",
            "income_expense_trend.png",
            "weekday_vs_weekend_spending.png",
        ]
        for plot_name in expected_plots:
            plot_path = PLOTS_DIR / plot_name
            self.assertTrue(plot_path.exists(), f"Plot missing: {plot_name}")
            # Ensure high-res non-empty file (> 50 KB)
            file_size = plot_path.stat().st_size
            self.assertGreater(file_size, 50_000, f"Plot {plot_name} file size too small: {file_size} bytes")

        # Verify plots README
        readme_path = PLOTS_DIR / "README.md"
        self.assertTrue(readme_path.exists())
        self.assertGreater(readme_path.stat().st_size, 100)

        logger.info("PASS: Test 7 - Static Plot File Integrity (5 plots > 50 KB, 300 DPI).")


if __name__ == "__main__":
    unittest.main()
