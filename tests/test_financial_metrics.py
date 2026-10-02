"""Unit Tests for Financial Calculation Formulas and Metrics.

Validates mathematical correctness, boundary edge cases, division safety,
and personal finance business rules implemented in src/analyzer.py.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.analyzer import FinancialAnalyzer


@pytest.mark.unit
class TestFinancialKPIs:
    """Test suite for core financial KPI formulas and accounting rules."""

    def test_inflows_outflows_transfers_separation(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify income, expenses, and transfers-out are aggregated independently."""
        kpis = deterministic_analyzer.compute_kpis()
        assert kpis["total_income"] == pytest.approx(200000.00, abs=0.01)
        assert kpis["total_expense"] == pytest.approx(70000.00, abs=0.01)
        assert kpis["total_transfers"] == pytest.approx(35000.00, abs=0.01)
        # Ensure transfers are NOT included in total expense
        assert kpis["total_expense"] + kpis["total_transfers"] == pytest.approx(105000.00, abs=0.01)

    def test_net_cash_flow_formula(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify Net Cash Flow formula: NCF = Income - Expenses."""
        kpis = deterministic_analyzer.compute_kpis()
        expected_ncf = round(200000.00 - 70000.00, 2)
        assert kpis["net_cash_flow"] == pytest.approx(expected_ncf, abs=0.01)
        assert kpis["net_cash_flow"] == pytest.approx(130000.00, abs=0.01)

    def test_cash_surplus_margin_formula(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify Operational Cash Surplus Margin: ((Income - Expenses) / Income) * 100."""
        kpis = deterministic_analyzer.compute_kpis()
        expected_margin = round(((200000.00 - 70000.00) / 200000.00) * 100.0, 2)
        assert kpis["cash_surplus_margin"] == pytest.approx(expected_margin, abs=0.01)
        assert kpis["cash_surplus_margin"] == pytest.approx(65.00, abs=0.01)

    def test_zero_income_margin_guard(self, deterministic_processed_df: pd.DataFrame):
        """Verify division-by-zero guard returns 'N/A (Zero Income)' when income is zero."""
        expense_only_df = deterministic_processed_df[deterministic_processed_df["transaction_type"] == "Expense"].copy()
        analyzer = FinancialAnalyzer(expense_only_df)
        kpis = analyzer.compute_kpis()
        assert kpis["total_income"] == 0.0
        assert kpis["cash_surplus_margin"] == "N/A (Zero Income)"

    def test_negative_surplus_margin(self, deterministic_processed_df: pd.DataFrame):
        """Verify surplus margin handles deficit situations (expenses > income) safely."""
        deficit_records = deterministic_processed_df.copy()
        # Scale up expenses to create an operational deficit
        deficit_records.loc[deficit_records["transaction_type"] == "Expense", "amount"] = 120000.00
        analyzer = FinancialAnalyzer(deficit_records)
        kpis = analyzer.compute_kpis()
        assert kpis["total_income"] == 200000.00
        # 4 expense rows * 120,000 = 480,000
        assert kpis["total_expense"] == 480000.00
        assert kpis["net_cash_flow"] == -280000.00
        assert kpis["cash_surplus_margin"] == pytest.approx(-140.00, abs=0.01)

    def test_daily_burn_rate_calendar_days_denominator(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify burn rate uses the complete calendar span (max_date - min_date + 1)."""
        kpis = deterministic_analyzer.compute_kpis()
        # 2018-01-05 to 2018-02-25 = 52 calendar days
        assert kpis["calendar_days"] == 52
        assert kpis["min_date"] == "2018-01-05"
        assert kpis["max_date"] == "2018-02-25"
        expected_burn_rate = round(70000.00 / 52, 2)
        assert kpis["daily_burn_rate"] == pytest.approx(expected_burn_rate, abs=0.01)
        assert kpis["daily_burn_rate"] == pytest.approx(1346.15, abs=0.01)

    def test_single_day_dataset_burn_rate(self):
        """Verify burn rate for a single-day transaction slice."""
        single_day_df = pd.DataFrame([
            {
                "date": "2018-05-10",
                "transaction_type": "Expense",
                "amount": 2500.00,
                "currency": "INR",
                "year": 2018,
                "month": 5,
                "month_year": "2018-05",
                "is_weekend": False,
                "category": "Household",
                "subcategory": "Groceries",
                "payment_mode": "Cash",
            }
        ])
        analyzer = FinancialAnalyzer(single_day_df)
        kpis = analyzer.compute_kpis()
        assert kpis["calendar_days"] == 1
        assert kpis["daily_burn_rate"] == 2500.00

    def test_empty_dataframe_kpi_handling(self):
        """Verify compute_kpis gracefully handles an empty DataFrame slice."""
        empty_df = pd.DataFrame(columns=["date", "transaction_type", "amount", "currency", "year", "month"])
        analyzer = FinancialAnalyzer(empty_df)
        kpis = analyzer.compute_kpis()
        assert kpis["total_income"] == 0.0
        assert kpis["total_expense"] == 0.0
        assert kpis["total_transfers"] == 0.0
        assert kpis["net_cash_flow"] == 0.0
        assert kpis["cash_surplus_margin"] == "N/A (Empty Slice)"
        assert kpis["calendar_days"] == 0
        assert kpis["daily_burn_rate"] == 0.0
        assert kpis["min_date"] is None
        assert kpis["max_date"] is None


@pytest.mark.unit
class TestDayTypeSpending:
    """Test suite for weekday vs weekend expenditure analysis."""

    def test_day_type_spending_calculation(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify weekday and weekend spending totals and distinct calendar day normalization."""
        day_type = deterministic_analyzer.compute_day_type_spending()
        
        # Total weekday expenses: Jan 10 (25,000) + Feb 12 (33,000) = 58,000
        assert day_type["weekday"]["total_spend"] == pytest.approx(58000.00, abs=0.01)
        # Total weekend expenses: Jan 14 (5,000) + Feb 17 (7,000) = 12,000
        assert day_type["weekend"]["total_spend"] == pytest.approx(12000.00, abs=0.01)

        # Calendar span 2018-01-05 (Fri) to 2018-02-25 (Sun) = 52 days
        total_days = day_type["weekday"]["distinct_calendar_days"] + day_type["weekend"]["distinct_calendar_days"]
        assert total_days == 52

        # Daily averages must equal total_spend / distinct_calendar_days
        wk_avg = round(58000.00 / day_type["weekday"]["distinct_calendar_days"], 2)
        we_avg = round(12000.00 / day_type["weekend"]["distinct_calendar_days"], 2)
        assert day_type["weekday"]["average_daily_spend"] == pytest.approx(wk_avg, abs=0.01)
        assert day_type["weekend"]["average_daily_spend"] == pytest.approx(we_avg, abs=0.01)

    def test_day_type_empty_dataframe(self):
        """Verify compute_day_type_spending returns zeroed structure on empty input."""
        empty_df = pd.DataFrame(columns=["date", "transaction_type", "amount", "is_weekend"])
        analyzer = FinancialAnalyzer(empty_df)
        res = analyzer.compute_day_type_spending()
        assert res["weekday"]["total_spend"] == 0.0
        assert res["weekday"]["distinct_calendar_days"] == 0
        assert res["weekend"]["total_spend"] == 0.0
        assert res["weekend"]["distinct_calendar_days"] == 0


@pytest.mark.unit
class TestMonthlySeriesAndMoM:
    """Test suite for monthly aggregations, MoM growth rates, and SMA3."""

    def test_monthly_series_aggregations(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify monthly grouping and Net Cash Flow calculation per month."""
        series = deterministic_analyzer.compute_monthly_series()
        assert len(series) == 2

        # Month 1: 2018-01
        m1 = series[0]
        assert m1["month_year"] == "2018-01"
        assert m1["income"] == 100000.00
        assert m1["expense"] == 30000.00  # 25,000 + 5,000
        assert m1["transfers"] == 20000.00
        assert m1["net_cash_flow"] == 70000.00
        assert m1["mom_expense_growth_pct"] == "N/A (First Month)"
        assert m1["sma3_expense"] is None

        # Month 2: 2018-02
        m2 = series[1]
        assert m2["month_year"] == "2018-02"
        assert m2["income"] == 100000.00
        assert m2["expense"] == 40000.00  # 33,000 + 7,000
        assert m2["transfers"] == 15000.00
        assert m2["net_cash_flow"] == 60000.00
        # MoM: ((40,000 - 30,000) / 30,000) * 100 = 33.33%
        assert m2["mom_expense_growth_pct"] == pytest.approx(33.33, abs=0.01)
        assert m2["sma3_expense"] is None

    def test_mom_non_consecutive_month_policy(self):
        """Verify non-consecutive calendar months produce 'N/A (Missing Preceding Month)'."""
        gap_records = pd.DataFrame([
            {"year": 2018, "month": 1, "month_year": "2018-01", "transaction_type": "Expense", "amount": 1000.0, "date": "2018-01-10"},
            {"year": 2018, "month": 3, "month_year": "2018-03", "transaction_type": "Expense", "amount": 1500.0, "date": "2018-03-10"},
        ])
        analyzer = FinancialAnalyzer(gap_records)
        series = analyzer.compute_monthly_series()
        assert len(series) == 2
        assert series[0]["mom_expense_growth_pct"] == "N/A (First Month)"
        assert series[1]["mom_expense_growth_pct"] == "N/A (Missing Preceding Month)"

    def test_mom_zero_prior_expense_guard(self):
        """Verify zero prior month expense returns 'N/A (Zero Prior Expense)'."""
        zero_prior_records = pd.DataFrame([
            {"year": 2018, "month": 1, "month_year": "2018-01", "transaction_type": "Income", "amount": 5000.0, "date": "2018-01-10"},
            {"year": 2018, "month": 2, "month_year": "2018-02", "transaction_type": "Expense", "amount": 2000.0, "date": "2018-02-10"},
        ])
        analyzer = FinancialAnalyzer(zero_prior_records)
        series = analyzer.compute_monthly_series()
        assert len(series) == 2
        assert series[1]["mom_expense_growth_pct"] == "N/A (Zero Prior Expense)"

    def test_trailing_3_month_sma_consecutive(self):
        """Verify trailing 3-month simple moving average for 3 consecutive months."""
        consecutive_records = pd.DataFrame([
            {"year": 2018, "month": 1, "month_year": "2018-01", "transaction_type": "Expense", "amount": 30000.0, "date": "2018-01-15"},
            {"year": 2018, "month": 2, "month_year": "2018-02", "transaction_type": "Expense", "amount": 45000.0, "date": "2018-02-15"},
            {"year": 2018, "month": 3, "month_year": "2018-03", "transaction_type": "Expense", "amount": 60000.0, "date": "2018-03-15"},
        ])
        analyzer = FinancialAnalyzer(consecutive_records)
        series = analyzer.compute_monthly_series()
        assert series[0]["sma3_expense"] is None
        assert series[1]["sma3_expense"] is None
        # Month 3 SMA: (30000 + 45000 + 60000) / 3 = 45000.00
        assert series[2]["sma3_expense"] == 45000.00

    def test_trailing_3_month_sma_non_consecutive_gap(self):
        """Verify SMA3 is None if any of the preceding 3 months are non-consecutive."""
        gap_records = pd.DataFrame([
            {"year": 2018, "month": 1, "month_year": "2018-01", "transaction_type": "Expense", "amount": 30000.0, "date": "2018-01-15"},
            {"year": 2018, "month": 2, "month_year": "2018-02", "transaction_type": "Expense", "amount": 45000.0, "date": "2018-02-15"},
            {"year": 2018, "month": 4, "month_year": "2018-04", "transaction_type": "Expense", "amount": 60000.0, "date": "2018-04-15"},
        ])
        analyzer = FinancialAnalyzer(gap_records)
        series = analyzer.compute_monthly_series()
        # Month 4 is preceded by Month 2, not Month 3 -> SMA3 must be None
        assert series[2]["sma3_expense"] is None


@pytest.mark.unit
class TestCategoryAndPaymentSummaries:
    """Test suite for category shares, subcategories, and payment mode distributions."""

    def test_category_summary_breakdown(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify category aggregation, percentage share calculations, and subcategory lists."""
        cats = deterministic_analyzer.compute_category_summary()
        assert len(cats) == 2

        # 1. Household: 25,000 + 33,000 = 58,000.00 (82.86%)
        household = next(c for c in cats if c["category"] == "Household")
        assert household["total_spend"] == 58000.00
        assert household["transaction_count"] == 2
        assert household["percentage_share"] == pytest.approx(82.86, abs=0.01)
        assert len(household["subcategories"]) == 1
        assert household["subcategories"][0]["subcategory"] == "Rent"
        assert household["subcategories"][0]["spend"] == 58000.00

        # 2. Food: 5,000 + 7,000 = 12,000.00 (17.14%)
        food = next(c for c in cats if c["category"] == "Food")
        assert food["total_spend"] == 12000.00
        assert food["transaction_count"] == 2
        assert food["percentage_share"] == pytest.approx(17.14, abs=0.01)

        # Sum of shares should equal 100.0%
        total_share = sum(c["percentage_share"] for c in cats)
        assert total_share == pytest.approx(100.00, abs=0.05)

    def test_category_summary_zero_expenses(self, deterministic_processed_df: pd.DataFrame):
        """Verify compute_category_summary returns empty list when no expenses exist."""
        income_only = deterministic_processed_df[deterministic_processed_df["transaction_type"] == "Income"].copy()
        analyzer = FinancialAnalyzer(income_only)
        assert analyzer.compute_category_summary() == []

    def test_payment_mode_summary(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify payment mode aggregation and expenditure shares."""
        modes = deterministic_analyzer.compute_payment_mode_summary()
        
        # Modes in deterministic dataset: Saving Bank account 1 (58,000), Cash (7,000), Credit Card (5,000)
        mode_dict = {m["payment_mode"]: m for m in modes}
        assert mode_dict["Saving Bank account 1"]["total_amount"] == 58000.00
        assert mode_dict["Cash"]["total_amount"] == 7000.00
        assert mode_dict["Credit Card"]["total_amount"] == 5000.00

        total_pct = sum(m["percentage_share"] for m in modes)
        assert total_pct == pytest.approx(100.00, abs=0.05)


@pytest.mark.unit
class TestDataFiltering:
    """Test suite for multi-dimensional dataset filtering."""

    def test_filter_by_year_and_month(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify filtering by year and month."""
        jan_2018 = deterministic_analyzer.filter_data(year=2018, month=1)
        assert len(jan_2018) == 4
        assert (jan_2018["month_year"] == "2018-01").all()

    def test_filter_by_category(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify filtering by category."""
        food_txns = deterministic_analyzer.filter_data(category="Food")
        assert len(food_txns) == 2
        assert (food_txns["category"] == "Food").all()

    def test_filter_by_transaction_type(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify filtering by transaction type."""
        transfers = deterministic_analyzer.filter_data(transaction_type="Transfer-Out")
        assert len(transfers) == 2
        assert (transfers["transaction_type"] == "Transfer-Out").all()

    def test_non_matching_filter(self, deterministic_analyzer: FinancialAnalyzer):
        """Verify non-matching filter returns an empty DataFrame."""
        empty = deterministic_analyzer.filter_data(year=1999)
        assert len(empty) == 0
