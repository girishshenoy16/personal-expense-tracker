"""Financial Analytics Engine and Aggregated Data Payload Generator.

Calculates mathematically rigorous personal finance KPIs (Income, Expenses,
Transfers-Out, Net Cash Flow, Burn Rate, Day-type analytics, Category Concentration,
and MoM Growth with consecutive-month checks and division-by-zero guards).
Exports the verified pre-aggregated public data contract payload (docs/data.js).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logger import get_logger

logger = get_logger("analyzer")


class FinancialAnalyzer:
    """Core analytical engine for processed transactions."""

    def __init__(self, processed_df: pd.DataFrame):
        self.df = processed_df.copy()
        # Ensure dates are datetime objects for temporal span calculations
        self.df["date_dt"] = pd.to_datetime(self.df["date"])

    @classmethod
    def from_csv(cls, csv_path: Path) -> FinancialAnalyzer:
        if not csv_path.exists():
            raise FileNotFoundError(f"Processed file not found: {csv_path}")
        df = pd.read_csv(csv_path)
        return cls(df)

    def filter_data(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        category: Optional[str] = None,
        payment_mode: Optional[str] = None,
        transaction_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """Filter dataset defensively across given dimensions."""
        filtered = self.df
        if year is not None:
            filtered = filtered[filtered["year"] == year]
        if month is not None:
            filtered = filtered[filtered["month"] == month]
        if category is not None:
            filtered = filtered[filtered["category"] == category]
        if payment_mode is not None:
            filtered = filtered[filtered["payment_mode"] == payment_mode]
        if transaction_type is not None:
            filtered = filtered[filtered["transaction_type"] == transaction_type]
        return filtered

    def compute_kpis(self, subset_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Compute core financial KPIs on a dataset subset."""
        target_df = self.df if subset_df is None else subset_df

        if target_df.empty:
            return {
                "total_income": 0.0,
                "total_expense": 0.0,
                "total_transfers": 0.0,
                "net_cash_flow": 0.0,
                "cash_surplus_margin": "N/A (Empty Slice)",
                "calendar_days": 0,
                "daily_burn_rate": 0.0,
                "min_date": None,
                "max_date": None,
                "currency": "INR",
            }

        # 1. Inflows, Outflows & Capital Transfers
        income_rows = target_df[target_df["transaction_type"] == "Income"]
        expense_rows = target_df[target_df["transaction_type"] == "Expense"]
        transfer_rows = target_df[target_df["transaction_type"] == "Transfer-Out"]

        total_income = round(float(income_rows["amount"].sum()), 2)
        total_expense = round(float(expense_rows["amount"].sum()), 2)
        total_transfers = round(float(transfer_rows["amount"].sum()), 2)

        # 2. Net Cash Flow (NCF = I - E)
        net_cash_flow = round(total_income - total_expense, 2)

        # 3. Operational Cash Surplus Margin (Ms = (I - E) / I)
        if total_income > 0:
            margin_val = round(((total_income - total_expense) / total_income) * 100.0, 2)
            cash_surplus_margin: Any = margin_val
        else:
            cash_surplus_margin = "N/A (Zero Income)"

        # 4. Daily Average Burn Rate (Bd = E / N_calendar_days)
        min_date = target_df["date_dt"].min()
        max_date = target_df["date_dt"].max()
        calendar_days = int((max_date - min_date).days) + 1 if pd.notna(min_date) and pd.notna(max_date) else 0

        if calendar_days > 0:
            daily_burn_rate = round(total_expense / calendar_days, 2)
        else:
            daily_burn_rate = 0.0

        currency = str(target_df["currency"].iloc[0]) if not target_df.empty else "INR"

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "total_transfers": total_transfers,
            "net_cash_flow": net_cash_flow,
            "cash_surplus_margin": cash_surplus_margin,
            "calendar_days": calendar_days,
            "daily_burn_rate": daily_burn_rate,
            "min_date": min_date.strftime("%Y-%m-%d") if pd.notna(min_date) else None,
            "max_date": max_date.strftime("%Y-%m-%d") if pd.notna(max_date) else None,
            "currency": currency,
        }

    def compute_day_type_spending(self, subset_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Compute weekday vs weekend spending using verified unique calendar day counts."""
        target_df = self.df if subset_df is None else subset_df

        if target_df.empty:
            return {
                "weekday": {"total_spend": 0.0, "distinct_calendar_days": 0, "average_daily_spend": 0.0},
                "weekend": {"total_spend": 0.0, "distinct_calendar_days": 0, "average_daily_spend": 0.0},
            }

        min_date = target_df["date_dt"].min()
        max_date = target_df["date_dt"].max()
        all_dates_range = pd.date_range(start=min_date, end=max_date, freq="D")
        
        # Count distinct calendar weekdays and weekend days in this span
        total_calendar_weekdays = int((all_dates_range.weekday < 5).sum())
        total_calendar_weekend_days = int((all_dates_range.weekday >= 5).sum())

        expense_df = target_df[target_df["transaction_type"] == "Expense"]
        weekday_expenses = expense_df[~expense_df["is_weekend"]]
        weekend_expenses = expense_df[expense_df["is_weekend"]]

        total_weekday_spend = round(float(weekday_expenses["amount"].sum()), 2)
        total_weekend_spend = round(float(weekend_expenses["amount"].sum()), 2)

        avg_weekday_spend = round(total_weekday_spend / total_calendar_weekdays, 2) if total_calendar_weekdays > 0 else 0.0
        avg_weekend_spend = round(total_weekend_spend / total_calendar_weekend_days, 2) if total_calendar_weekend_days > 0 else 0.0

        return {
            "weekday": {
                "total_spend": total_weekday_spend,
                "distinct_calendar_days": total_calendar_weekdays,
                "average_daily_spend": avg_weekday_spend,
            },
            "weekend": {
                "total_spend": total_weekend_spend,
                "distinct_calendar_days": total_calendar_weekend_days,
                "average_daily_spend": avg_weekend_spend,
            },
        }

    def compute_monthly_series(self, subset_df: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
        """Compute monthly financial run-rates, MoM growth, and trailing 3-month SMA."""
        target_df = self.df if subset_df is None else subset_df

        if target_df.empty:
            return []

        # Group by year, month, month_year, transaction_type
        pivot_df = target_df.pivot_table(
            index=["year", "month", "month_year"],
            columns="transaction_type",
            values="amount",
            aggfunc="sum",
            fill_value=0.0,
        ).reset_index()

        for col in ["Expense", "Income", "Transfer-Out"]:
            if col not in pivot_df.columns:
                pivot_df[col] = 0.0

        # Sort chronologically by year, month
        pivot_df = pivot_df.sort_values(by=["year", "month"]).reset_index(drop=True)

        monthly_records: List[Dict[str, Any]] = []
        for idx, row in pivot_df.iterrows():
            curr_year = int(row["year"])
            curr_month = int(row["month"])
            curr_my = str(row["month_year"])
            inc = round(float(row["Income"]), 2)
            exp = round(float(row["Expense"]), 2)
            trf = round(float(row["Transfer-Out"]), 2)
            ncf = round(inc - exp, 2)

            # Month-over-Month (MoM) Growth calculation
            # Must check that previous month is strictly consecutive
            mom_growth: Any = "N/A (First Month)"
            if idx > 0:
                prev_row = pivot_df.iloc[idx - 1]
                prev_year = int(prev_row["year"])
                prev_month = int(prev_row["month"])
                prev_exp = float(prev_row["Expense"])

                # Check consecutiveness: (curr_year*12 + curr_month) - (prev_year*12 + prev_month) == 1
                is_consecutive = ((curr_year * 12 + curr_month) - (prev_year * 12 + prev_month)) == 1

                if not is_consecutive:
                    mom_growth = "N/A (Missing Preceding Month)"
                elif prev_exp > 0:
                    mom_growth = round(((exp - prev_exp) / prev_exp) * 100.0, 2)
                else:
                    mom_growth = "N/A (Zero Prior Expense)"

            # Trailing 3-month simple moving average (SMA3)
            sma3: Optional[float] = None
            if idx >= 2:
                row_m1 = pivot_df.iloc[idx - 1]
                row_m2 = pivot_df.iloc[idx - 2]
                # Check consecutiveness of last 3 months
                c1 = ((curr_year * 12 + curr_month) - (int(row_m1["year"]) * 12 + int(row_m1["month"]))) == 1
                c2 = ((int(row_m1["year"]) * 12 + int(row_m1["month"])) - (int(row_m2["year"]) * 12 + int(row_m2["month"]))) == 1
                if c1 and c2:
                    sma3 = round((exp + float(row_m1["Expense"]) + float(row_m2["Expense"])) / 3.0, 2)

            monthly_records.append({
                "year": curr_year,
                "month": curr_month,
                "month_year": curr_my,
                "income": inc,
                "expense": exp,
                "transfers": trf,
                "net_cash_flow": ncf,
                "mom_expense_growth_pct": mom_growth,
                "sma3_expense": sma3,
            })

        return monthly_records

    def compute_category_summary(self, subset_df: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
        """Compute category spending totals, subcategory distributions, and percentage share."""
        target_df = self.df if subset_df is None else subset_df
        expense_df = target_df[target_df["transaction_type"] == "Expense"]

        total_expense = float(expense_df["amount"].sum())
        if total_expense == 0.0 or expense_df.empty:
            return []

        grouped = expense_df.groupby("category").agg(
            total_spend=("amount", "sum"),
            transaction_count=("amount", "count"),
        ).reset_index()

        grouped["percentage_share"] = (grouped["total_spend"] / total_expense * 100.0).round(2)
        grouped["total_spend"] = grouped["total_spend"].round(2)
        grouped = grouped.sort_values(by="total_spend", ascending=False).reset_index(drop=True)

        category_list: List[Dict[str, Any]] = []
        for _, row in grouped.iterrows():
            cat_name = str(row["category"])
            cat_sub_df = expense_df[expense_df["category"] == cat_name]
            sub_grouped = cat_sub_df.groupby("subcategory").agg(
                spend=("amount", "sum"),
                count=("amount", "count"),
            ).reset_index()
            sub_grouped["spend"] = sub_grouped["spend"].round(2)
            sub_grouped = sub_grouped.sort_values(by="spend", ascending=False)
            
            sub_list = [
                {"subcategory": str(s_row["subcategory"]), "spend": float(s_row["spend"]), "count": int(s_row["count"])}
                for _, s_row in sub_grouped.iterrows()
            ]

            category_list.append({
                "category": cat_name,
                "total_spend": float(row["total_spend"]),
                "transaction_count": int(row["transaction_count"]),
                "percentage_share": float(row["percentage_share"]),
                "subcategories": sub_list,
            })

        return category_list

    def compute_payment_mode_summary(self, subset_df: Optional[pd.DataFrame] = None) -> List[Dict[str, Any]]:
        """Compute payment mode spending distributions."""
        target_df = self.df if subset_df is None else subset_df
        expense_df = target_df[target_df["transaction_type"] == "Expense"]

        total_expense = float(expense_df["amount"].sum())
        if total_expense == 0.0 or expense_df.empty:
            return []

        grouped = expense_df.groupby("payment_mode").agg(
            total_amount=("amount", "sum"),
            transaction_count=("amount", "count"),
        ).reset_index()

        grouped["percentage_share"] = (grouped["total_amount"] / total_expense * 100.0).round(2)
        grouped["total_amount"] = grouped["total_amount"].round(2)
        grouped = grouped.sort_values(by="total_amount", ascending=False).reset_index(drop=True)

        mode_list = [
            {
                "payment_mode": str(r["payment_mode"]),
                "total_amount": float(r["total_amount"]),
                "transaction_count": int(r["transaction_count"]),
                "percentage_share": float(r["percentage_share"]),
            }
            for _, r in grouped.iterrows()
        ]
        return mode_list

    def export_data_payload_js(self, output_js_path: Path) -> Dict[str, Any]:
        """Export the pre-aggregated public data contract payload to docs/data.js.
        
        Strict Privacy Standard: Zero individual transaction rows, zero notes, zero timestamps.
        """
        logger.info(f"Generating pre-aggregated public data payload for {output_js_path}...")

        overall_kpis = self.compute_kpis()
        day_type_metrics = self.compute_day_type_spending()
        monthly_series = self.compute_monthly_series()
        category_summary = self.compute_category_summary()
        payment_mode_summary = self.compute_payment_mode_summary()

        available_years = sorted(self.df["year"].unique().tolist())
        available_categories = sorted(self.df[self.df["transaction_type"] == "Expense"]["category"].unique().tolist())
        available_payment_modes = sorted(self.df["payment_mode"].unique().tolist())

        payload: Dict[str, Any] = {
            "meta": {
                "project_title": "Personal Expense Tracker with Data Visualization",
                "dataset_source": "Daily Household Transactions (Kaggle)",
                "currency": overall_kpis["currency"],
                "currency_symbol": "₹" if overall_kpis["currency"] == "INR" else overall_kpis["currency"],
                "min_date": overall_kpis["min_date"],
                "max_date": overall_kpis["max_date"],
                "total_calendar_days": overall_kpis["calendar_days"],
                "publication_model": "Aggregated Public Publication Model (Strictly Zero Transaction Rows)",
            },
            "kpis_overall": {
                "total_income": overall_kpis["total_income"],
                "total_expense": overall_kpis["total_expense"],
                "total_transfers": overall_kpis["total_transfers"],
                "net_cash_flow": overall_kpis["net_cash_flow"],
                "cash_surplus_margin": overall_kpis["cash_surplus_margin"],
                "daily_burn_rate": overall_kpis["daily_burn_rate"],
                "avg_weekday_spend": day_type_metrics["weekday"]["average_daily_spend"],
                "avg_weekend_spend": day_type_metrics["weekend"]["average_daily_spend"],
            },
            "monthly_series": monthly_series,
            "category_summary": category_summary,
            "payment_mode_summary": payment_mode_summary,
            "day_type_summary": day_type_metrics,
            "filters": {
                "available_years": available_years,
                "available_categories": available_categories,
                "available_payment_modes": available_payment_modes,
                "available_transaction_types": ["Expense", "Income", "Transfer-Out"],
            },
        }

        # Write to docs/data.js as window.EXPENSE_DATA for client-side inclusion
        output_js_path.parent.mkdir(parents=True, exist_ok=True)
        json_str = json.dumps(payload, indent=2)
        js_content = f"// Pre-Aggregated Public Data Contract Payload\n// Generated deterministically by src/analyzer.py\n// STRICT PRIVACY GUARANTEE: Zero transaction rows, zero notes, zero timestamps.\nwindow.EXPENSE_DATA = {json_str};\n"

        with open(output_js_path, "w", encoding="utf-8") as f:
            f.write(js_content)

        file_size_kb = output_js_path.stat().st_size / 1024.0
        logger.info(f"Successfully generated {output_js_path} ({file_size_kb:.2f} KB).")

        return payload


def run_analysis(processed_csv: Path, payload_js_path: Path) -> Dict[str, Any]:
    """Run complete financial analysis and export data payload."""
    analyzer = FinancialAnalyzer.from_csv(processed_csv)
    kpis = analyzer.compute_kpis()
    logger.info("FINANCIAL METRICS OVERVIEW:")
    logger.info(f"  Total Inflow (Income):        {kpis['currency']} {kpis['total_income']:,.2f}")
    logger.info(f"  Total Outflow (Expenses):     {kpis['currency']} {kpis['total_expense']:,.2f}")
    logger.info(f"  Transfers-Out (Investments):  {kpis['currency']} {kpis['total_transfers']:,.2f}")
    logger.info(f"  Net Cash Flow (NCF):          {kpis['currency']} {kpis['net_cash_flow']:,.2f}")
    logger.info(f"  Operational Surplus Margin:   {kpis['cash_surplus_margin']}%")
    logger.info(f"  Daily Average Burn Rate:      {kpis['currency']} {kpis['daily_burn_rate']:,.2f}/day ({kpis['calendar_days']} calendar days)")
    
    payload = analyzer.export_data_payload_js(payload_js_path)
    return payload


if __name__ == "__main__":
    processed_p = PROJECT_ROOT / "data" / "processed" / "processed_transactions.csv"
    payload_p = PROJECT_ROOT / "docs" / "data.js"
    run_analysis(processed_p, payload_p)
