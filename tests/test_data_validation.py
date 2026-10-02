"""Unit Tests for Data Validation, Cleaning, Imputation, and Integrity.

Validates defensive date parsing, schema conformance, duplicate auditing,
rejected records logging, surrogate key generation, and mathematical
row-count accounting reconciliation in src/cleaner.py and src/inspect_dataset.py.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List

import pandas as pd
import pytest

from src.cleaner import AUTHORITATIVE_COLUMNS, clean_dataset, parse_date_and_time
from src.inspect_dataset import analyze_date_tokens, compute_file_sha256


@pytest.mark.unit
class TestAuthoritativeSchema:
    """Verifies schema definitions and column specifications."""

    def test_authoritative_16_column_schema_length(self):
        """Verify the authoritative schema contains exactly 16 columns."""
        assert len(AUTHORITATIVE_COLUMNS) == 16

    def test_authoritative_column_names_and_order(self):
        """Verify the exact sequence of columns in the authoritative schema."""
        expected = [
            "transaction_id",
            "date",
            "time",
            "time_available",
            "year",
            "month",
            "month_year",
            "day_name",
            "is_weekend",
            "payment_mode",
            "category",
            "subcategory",
            "note",
            "transaction_type",
            "amount",
            "currency",
        ]
        assert AUTHORITATIVE_COLUMNS == expected


@pytest.mark.unit
class TestDateTimeParsing:
    """Tests empirical date/time parsing rules across multiple format variations."""

    def test_parse_date_only_dd_mm_yyyy(self):
        """Verify standard date-only strings parse correctly."""
        iso, time_str, has_time, dt = parse_date_and_time("20/09/2018")
        assert iso == "2018-09-20"
        assert time_str is None
        assert has_time is False
        assert dt is not None
        assert dt.year == 2018
        assert dt.month == 9
        assert dt.day == 20

    def test_parse_date_with_hh_mm(self):
        """Verify date with 2-part time (HH:MM) parses and normalizes to HH:MM:00."""
        iso, time_str, has_time, dt = parse_date_and_time("05/01/2018 14:30")
        assert iso == "2018-01-05"
        assert time_str == "14:30:00"
        assert has_time is True
        assert dt is not None
        assert dt.year == 2018
        assert dt.month == 1
        assert dt.day == 5

    def test_parse_date_with_hh_mm_ss(self):
        """Verify date with 3-part time (HH:MM:SS) preserves exact seconds."""
        iso, time_str, has_time, dt = parse_date_and_time("12/03/2017 08:45:15")
        assert iso == "2017-03-12"
        assert time_str == "08:45:15"
        assert has_time is True
        assert dt is not None
        assert dt.year == 2017
        assert dt.month == 3
        assert dt.day == 12

    def test_parse_invalid_date_returns_none(self):
        """Verify invalid date strings return (None, None, False, None)."""
        iso, time_str, has_time, dt = parse_date_and_time("not-a-valid-date-value")
        assert iso is None
        assert time_str is None
        assert has_time is False
        assert dt is None

    def test_parse_missing_and_blank_date(self):
        """Verify null and empty inputs are safely handled."""
        for val in [None, "", "   ", pd.NA]:
            iso, time_str, has_time, dt = parse_date_and_time(val)
            assert iso is None
            assert time_str is None
            assert has_time is False
            assert dt is None


@pytest.mark.unit
class TestDataCleaningPipeline:
    """Tests the defensive cleaning engine with controlled synthetic data."""

    @pytest.fixture(autouse=True)
    def run_cleaner(self, tmp_path: Path, sample_raw_csv: Path):
        """Execute cleaner on the synthetic sample raw dataset into tmp_path."""
        self.processed_path = tmp_path / "processed_transactions.csv"
        self.duplicate_audit_path = tmp_path / "duplicate_audit.csv"
        self.rejected_records_path = tmp_path / "rejected_records.csv"

        self.clean_result = clean_dataset(
            raw_csv_path=sample_raw_csv,
            processed_csv_path=self.processed_path,
            duplicate_audit_path=self.duplicate_audit_path,
            rejected_records_path=self.rejected_records_path,
        )
        self.df_processed = pd.read_csv(self.processed_path)
        self.df_rejected = pd.read_csv(self.rejected_records_path)
        self.df_duplicate = pd.read_csv(self.duplicate_audit_path)

    def test_row_count_reconciliation_balance(self):
        """Verify: Raw == Retained + Rejected + Deduplicated."""
        raw_count = self.clean_result["raw_count"]
        retained = self.clean_result["retained_count"]
        rejected = self.clean_result["rejected_count"]
        deduplicated = self.clean_result["deduplicated_count"]

        assert raw_count == 14
        assert rejected == 3  # Unparseable date, corrupt amount, invalid txn type
        assert deduplicated == 1  # 1 genuine technical repost removed
        assert retained == 10  # 14 - 3 - 1 = 10
        assert raw_count == retained + rejected + deduplicated
        assert self.clean_result["is_balanced"] is True

    def test_rejected_records_reasons(self):
        """Verify each rejected record logs the appropriate reason."""
        assert len(self.df_rejected) == 3
        reasons = set(self.df_rejected["rejection_reason"])
        assert "UNPARSEABLE_DATE" in reasons
        assert "MALFORMED_AMOUNT" in reasons
        assert "INVALID_TRANSACTION_TYPE" in reasons

    def test_duplicate_audit_resolutions(self):
        """Verify duplicate audit classifies candidates into ambiguous and technical resolutions."""
        assert len(self.df_duplicate) > 0
        statuses = set(self.df_duplicate["resolution_status"])
        assert "retained_ambiguous_duplicate" in statuses
        assert "deduplicated_genuine_technical_repost" in statuses

    def test_field_imputation_defaults(self):
        """Verify imputation rules for missing subcategory, note, payment mode, and currency."""
        # Subcategory default 'General'
        imputed_subcat = self.df_processed[self.df_processed["note"] == "Local Metro Pass"]
        assert len(imputed_subcat) == 1
        assert imputed_subcat["subcategory"].iloc[0] == "General"

        # Note default 'No description provided'
        imputed_note = self.df_processed[self.df_processed["amount"] == 3200.00]
        assert len(imputed_note) == 1
        assert imputed_note["note"].iloc[0] == "No description provided"

        # Mode default 'Cash' and Currency 'INR'
        imputed_mode = self.df_processed[self.df_processed["amount"] == 150.00]
        assert len(imputed_mode) == 1
        assert imputed_mode["payment_mode"].iloc[0] == "Cash"
        assert imputed_mode["currency"].iloc[0] == "INR"

    def test_surrogate_key_formatting_and_ordering(self):
        """Verify sequential surrogate primary key generation (GEN-TXN-0001, etc.)."""
        pattern = re.compile(r"^GEN-TXN-\d{4}$")
        txn_ids = self.df_processed["transaction_id"].tolist()
        assert len(txn_ids) == len(set(txn_ids)), "Surrogate keys are not unique!"
        for tid in txn_ids:
            assert pattern.match(tid) is not None
        assert txn_ids[0] == "GEN-TXN-0001"
        assert txn_ids[-1] == f"GEN-TXN-{len(txn_ids):04d}"


@pytest.mark.unit
class TestDatasetInspectionUtilities:
    """Tests dynamic profiler utilities in src/inspect_dataset.py."""

    def test_compute_file_sha256(self, tmp_path: Path):
        """Verify deterministic SHA-256 calculation for a test file."""
        test_file = tmp_path / "hash_sample.txt"
        test_file.write_bytes(b"Antigravity Expense Tracker Test Payload")
        # Precomputed SHA-256 for the string above
        import hashlib
        expected = hashlib.sha256(b"Antigravity Expense Tracker Test Payload").hexdigest().upper()
        computed = compute_file_sha256(test_file)
        assert computed == expected

    def test_analyze_date_tokens_dd_mm_detection(self):
        """Verify empirical detection of DD/MM/YYYY format when tokens > 12."""
        sample_dates = pd.Series([
            "20/09/2018 12:04:08",
            "15/01/2018",
            "28/02/2018 09:30",
            "05/03/2018",
        ])
        profile = analyze_date_tokens(sample_dates)
        assert profile["first_token_gt_12"] >= 3
        assert profile["second_token_gt_12"] == 0
        assert "DD/MM/YYYY" in profile["inferred_order"]
        assert profile["has_timestamp_count"] == 2
