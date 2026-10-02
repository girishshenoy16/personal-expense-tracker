"""Pytest Configuration and Reusable Test Fixtures.

Provides deterministic, reproducible synthetic datasets, temporary directories,
and shared fixtures for testing financial metrics, data cleaning, validation,
pipeline execution, reports, and logging resilience.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List

import pandas as pd
import pytest

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analyzer import FinancialAnalyzer
from src.cleaner import AUTHORITATIVE_COLUMNS

RAW_PROD_PATH = PROJECT_ROOT / "data" / "raw" / "Daily Household Transactions.csv"
PROCESSED_PROD_PATH = PROJECT_ROOT / "data" / "processed" / "processed_transactions.csv"


@pytest.fixture(scope="session")
def raw_columns() -> List[str]:
    """Canonical 8-field raw schema."""
    return ["Date", "Mode", "Category", "Subcategory", "Note", "Amount", "Income/Expense", "Currency"]


@pytest.fixture
def sample_raw_records() -> List[Dict[str, Any]]:
    """Diverse synthetic raw transaction records representing edge cases and standard transactions."""
    return [
        # 1. Standard Income
        {
            "Date": "01/01/2018 09:00:00",
            "Mode": "Saving Bank account 1",
            "Category": "Income",
            "Subcategory": "Salary",
            "Note": "Monthly Salary Credit",
            "Amount": 100000.00,
            "Income/Expense": "Income",
            "Currency": "INR",
        },
        # 2. Standard Expense (Weekday)
        {
            "Date": "03/01/2018 12:30:00",
            "Mode": "Saving Bank account 1",
            "Category": "Household",
            "Subcategory": "Rent",
            "Note": "Apartment Maintenance",
            "Amount": 25000.00,
            "Income/Expense": "Expense",
            "Currency": "INR",
        },
        # 3. Standard Expense (Weekend: 2018-01-06 is Saturday)
        {
            "Date": "06/01/2018 20:00:00",
            "Mode": "Credit Card",
            "Category": "Food",
            "Subcategory": "Dining Out",
            "Note": "Weekend Family Dinner",
            "Amount": 5000.00,
            "Income/Expense": "Expense",
            "Currency": "INR",
        },
        # 4. Standard Transfer-Out (Investment)
        {
            "Date": "10/01/2018 10:15:00",
            "Mode": "Saving Bank account 1",
            "Category": "Investment",
            "Subcategory": "Mutual Funds",
            "Note": "Equity Index SIP",
            "Amount": 20000.00,
            "Income/Expense": "Transfer-Out",
            "Currency": "INR",
        },
        # 5. Missing Subcategory (imputed to 'General')
        {
            "Date": "12/01/2018",
            "Mode": "Cash",
            "Category": "Transportation",
            "Subcategory": None,
            "Note": "Local Metro Pass",
            "Amount": 800.00,
            "Income/Expense": "Expense",
            "Currency": "INR",
        },
        # 6. Missing Note (imputed to 'No description provided')
        {
            "Date": "15/01/2018",
            "Mode": "Credit Card",
            "Category": "Utilities",
            "Subcategory": "Electricity",
            "Note": None,
            "Amount": 3200.00,
            "Income/Expense": "Expense",
            "Currency": "INR",
        },
        # 7. Missing Payment Mode & Currency (imputed to 'Cash' & 'INR')
        {
            "Date": "18/01/2018",
            "Mode": None,
            "Category": "Food",
            "Subcategory": "Snacks",
            "Note": "Evening Coffee",
            "Amount": 150.00,
            "Income/Expense": "Expense",
            "Currency": None,
        },
        # 8 & 9. Legitimate Ambiguous Recurring Duplicate Pair (Both retained)
        {
            "Date": "20/01/2018",
            "Mode": "Cash",
            "Category": "Transportation",
            "Subcategory": "Bus",
            "Note": "Daily Commute Ticket",
            "Amount": 30.00,
            "Income/Expense": "Expense",
            "Currency": "INR",
        },
        {
            "Date": "20/01/2018",
            "Mode": "Cash",
            "Category": "Transportation",
            "Subcategory": "Bus",
            "Note": "Daily Commute Ticket",
            "Amount": 30.00,
            "Income/Expense": "Expense",
            "Currency": "INR",
        },
        # 10 & 11. Genuine Technical Repost Duplicate Pair (Second row deduplicated)
        {
            "Date": "25/01/2018 14:20:10",
            "Mode": "Saving Bank account 1",
            "Category": "Services",
            "Subcategory": "Plumber",
            "Note": "Repair duplicate payment retry",
            "Amount": 650.00,
            "Income/Expense": "Expense",
            "Currency": "INR",
        },
        {
            "Date": "25/01/2018 14:20:10",
            "Mode": "Saving Bank account 1",
            "Category": "Services",
            "Subcategory": "Plumber",
            "Note": "Repair duplicate payment retry",
            "Amount": 650.00,
            "Income/Expense": "Expense",
            "Currency": "INR",
        },
        # 12. Rejected Record 1: Unparseable Date
        {
            "Date": "not_a_valid_date",
            "Mode": "Cash",
            "Category": "Food",
            "Subcategory": "Snacks",
            "Note": "Invalid Date Entry",
            "Amount": 50.00,
            "Income/Expense": "Expense",
            "Currency": "INR",
        },
        # 13. Rejected Record 2: Malformed Amount
        {
            "Date": "28/01/2018",
            "Mode": "Cash",
            "Category": "Food",
            "Subcategory": "Snacks",
            "Note": "Corrupt Amount Field",
            "Amount": "CORRUPTED_VALUE",
            "Income/Expense": "Expense",
            "Currency": "INR",
        },
        # 14. Rejected Record 3: Invalid Transaction Type
        {
            "Date": "29/01/2018",
            "Mode": "Credit Card",
            "Category": "Shopping",
            "Subcategory": "Apparel",
            "Note": "Merchant Refund Reversal",
            "Amount": 1200.00,
            "Income/Expense": "Refund",
            "Currency": "INR",
        },
    ]


@pytest.fixture
def sample_raw_csv(tmp_path: Path, sample_raw_records: List[Dict[str, Any]]) -> Path:
    """Write sample raw records to a temporary CSV file."""
    csv_file = tmp_path / "raw_transactions.csv"
    df = pd.DataFrame(sample_raw_records)
    df.to_csv(csv_file, index=False, encoding="utf-8")
    return csv_file


@pytest.fixture
def deterministic_processed_df() -> pd.DataFrame:
    """Handcrafted 8-record DataFrame with exact mathematical properties across 2 consecutive months.
    
    Properties:
    - 2 Months: 2018-01 and 2018-02
    - Total Income: 100,000 + 100,000 = 200,000.00
    - Total Expense: 25,000 + 5,000 + 33,000 + 7,000 = 70,000.00
    - Total Transfers: 20,000 + 15,000 = 35,000.00
    - Net Cash Flow: 200,000 - 70,000 = 130,000.00
    - Surplus Margin: ((200,000 - 70,000) / 200,000) * 100 = 65.0%
    - Date Span: 2018-01-05 to 2018-02-25 -> 52 calendar days
    - Daily Burn Rate: 70,000 / 52 = 1,346.15 / day
    - Weekday Spend: 25,000 (Jan 10, Wed) + 33,000 (Feb 12, Mon) = 58,000.00
    - Weekend Spend: 5,000 (Jan 14, Sun) + 7,000 (Feb 17, Sat) = 12,000.00
    """
    records = [
        {
            "transaction_id": "GEN-TXN-0001",
            "date": "2018-01-05",
            "time": "09:00:00",
            "time_available": True,
            "year": 2018,
            "month": 1,
            "month_year": "2018-01",
            "day_name": "Friday",
            "is_weekend": False,
            "payment_mode": "Saving Bank account 1",
            "category": "Income",
            "subcategory": "Salary",
            "note": "Salary credit",
            "transaction_type": "Income",
            "amount": 100000.00,
            "currency": "INR",
        },
        {
            "transaction_id": "GEN-TXN-0002",
            "date": "2018-01-10",
            "time": None,
            "time_available": False,
            "year": 2018,
            "month": 1,
            "month_year": "2018-01",
            "day_name": "Wednesday",
            "is_weekend": False,
            "payment_mode": "Saving Bank account 1",
            "category": "Household",
            "subcategory": "Rent",
            "note": "January Rent",
            "transaction_type": "Expense",
            "amount": 25000.00,
            "currency": "INR",
        },
        {
            "transaction_id": "GEN-TXN-0003",
            "date": "2018-01-14",
            "time": "19:30:00",
            "time_available": True,
            "year": 2018,
            "month": 1,
            "month_year": "2018-01",
            "day_name": "Sunday",
            "is_weekend": True,
            "payment_mode": "Credit Card",
            "category": "Food",
            "subcategory": "Dining",
            "note": "Family Dinner",
            "transaction_type": "Expense",
            "amount": 5000.00,
            "currency": "INR",
        },
        {
            "transaction_id": "GEN-TXN-0004",
            "date": "2018-01-20",
            "time": "11:00:00",
            "time_available": True,
            "year": 2018,
            "month": 1,
            "month_year": "2018-01",
            "day_name": "Saturday",
            "is_weekend": True,
            "payment_mode": "Saving Bank account 1",
            "category": "Investment",
            "subcategory": "Mutual Funds",
            "note": "Monthly SIP",
            "transaction_type": "Transfer-Out",
            "amount": 20000.00,
            "currency": "INR",
        },
        {
            "transaction_id": "GEN-TXN-0005",
            "date": "2018-02-05",
            "time": "09:00:00",
            "time_available": True,
            "year": 2018,
            "month": 2,
            "month_year": "2018-02",
            "day_name": "Monday",
            "is_weekend": False,
            "payment_mode": "Saving Bank account 1",
            "category": "Income",
            "subcategory": "Salary",
            "note": "Salary credit",
            "transaction_type": "Income",
            "amount": 100000.00,
            "currency": "INR",
        },
        {
            "transaction_id": "GEN-TXN-0006",
            "date": "2018-02-12",
            "time": None,
            "time_available": False,
            "year": 2018,
            "month": 2,
            "month_year": "2018-02",
            "day_name": "Monday",
            "is_weekend": False,
            "payment_mode": "Saving Bank account 1",
            "category": "Household",
            "subcategory": "Rent",
            "note": "February Rent",
            "transaction_type": "Expense",
            "amount": 33000.00,
            "currency": "INR",
        },
        {
            "transaction_id": "GEN-TXN-0007",
            "date": "2018-02-17",
            "time": "21:00:00",
            "time_available": True,
            "year": 2018,
            "month": 2,
            "month_year": "2018-02",
            "day_name": "Saturday",
            "is_weekend": True,
            "payment_mode": "Cash",
            "category": "Food",
            "subcategory": "Dining",
            "note": "Weekend Outing",
            "transaction_type": "Expense",
            "amount": 7000.00,
            "currency": "INR",
        },
        {
            "transaction_id": "GEN-TXN-0008",
            "date": "2018-02-25",
            "time": "16:00:00",
            "time_available": True,
            "year": 2018,
            "month": 2,
            "month_year": "2018-02",
            "day_name": "Sunday",
            "is_weekend": True,
            "payment_mode": "Saving Bank account 1",
            "category": "Investment",
            "subcategory": "PPF",
            "note": "PPF Deposit",
            "transaction_type": "Transfer-Out",
            "amount": 15000.00,
            "currency": "INR",
        },
    ]
    df = pd.DataFrame(records)
    # Ensure correct columns order
    return df[AUTHORITATIVE_COLUMNS]


@pytest.fixture
def deterministic_analyzer(deterministic_processed_df: pd.DataFrame) -> FinancialAnalyzer:
    """FinancialAnalyzer instance with known mathematical properties."""
    return FinancialAnalyzer(deterministic_processed_df)


@pytest.fixture(scope="session")
def production_processed_df() -> pd.DataFrame:
    """Production 16-field processed dataset (read-only fixture)."""
    if not PROCESSED_PROD_PATH.exists():
        pytest.skip(f"Production processed dataset not found at {PROCESSED_PROD_PATH}")
    return pd.read_csv(PROCESSED_PROD_PATH)


@pytest.fixture(scope="session")
def production_analyzer(production_processed_df: pd.DataFrame) -> FinancialAnalyzer:
    """FinancialAnalyzer instance backed by the production dataset."""
    return FinancialAnalyzer(production_processed_df)
