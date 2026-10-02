"""Static Analytical Plotting Engine.

Generates 5 publication-ready 300 DPI Matplotlib PNG visualizations in outputs/plots/:
1. monthly_income_vs_expenses.png - Grouped bar chart comparing monthly inflow vs outflow.
2. expense_category_breakdown.png - Horizontal bar chart ranking spending categories with %.
3. payment_mode_distribution.png - Expenditure distribution across payment channels.
4. income_expense_trend.png - Time-series trend with 3-month trailing SMA.
5. weekday_vs_weekend_spending.png - Normalized average daily spend on weekdays vs weekends.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Dict, List, Optional

import matplotlib
# Use non-interactive backend for headless server execution
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analyzer import FinancialAnalyzer
from src.logger import get_logger

logger = get_logger("plotter")

# Visual Styling Palette (PowerBI / Executive Theme)
COLOR_INCOME = "#10b981"    # Emerald
COLOR_EXPENSE = "#ef4444"   # Crimson
COLOR_TRANSFERS = "#3b82f6" # Cobalt Blue
COLOR_SMA = "#f59e0b"       # Amber
COLOR_PRIMARY = "#0f172a"   # Navy Slate
COLOR_GRID = "#e2e8f0"      # Light border
COLOR_BAR = "#64748b"       # Slate

# Global plot styling parameters
plt.rcParams.update({
    "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans", "sans-serif"],
    "font.family": "sans-serif",
    "axes.edgecolor": "#cbd5e1",
    "axes.linewidth": 0.8,
    "grid.color": COLOR_GRID,
    "grid.linestyle": "--",
    "grid.alpha": 0.7,
})


def format_currency(x, pos):
    """Format tick labels into readable thousands/lakhs."""
    if x >= 1_000_000:
        return f"₹{x*1e-6:.1f}M"
    elif x >= 1_000:
        return f"₹{x*1e-3:.0f}K"
    else:
        return f"₹{x:.0f}"


def plot_monthly_income_vs_expenses(monthly_df: pd.DataFrame, output_path: Path) -> None:
    """Generate grouped bar chart comparing monthly income and expenses."""
    fig, ax = plt.subplots(figsize=(14, 6), dpi=300)

    x = range(len(monthly_df))
    width = 0.38

    rects1 = ax.bar([i - width/2 for i in x], monthly_df["income"], width, label="Total Income", color=COLOR_INCOME, alpha=0.9)
    rects2 = ax.bar([i + width/2 for i in x], monthly_df["expense"], width, label="Total Expense", color=COLOR_EXPENSE, alpha=0.9)

    ax.set_title("Monthly Total Income vs. Total Expenses (Consumption)", fontsize=14, fontweight="bold", pad=15, color=COLOR_PRIMARY)
    ax.set_ylabel("Amount (INR)", fontsize=11, fontweight="bold", color=COLOR_PRIMARY)
    ax.set_xticks(list(x))
    ax.set_xticklabels(monthly_df["month_year"], rotation=45, ha="right", fontsize=9)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_currency))
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", zorder=0)
    ax.legend(frameon=True, facecolor="#ffffff", edgecolor="#cbd5e1", fontsize=10)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved plot: {output_path.name}")


def plot_expense_category_breakdown(category_list: List[Dict], output_path: Path) -> None:
    """Generate horizontal bar chart of top expense categories with % share."""
    fig, ax = plt.subplots(figsize=(10, 7), dpi=300)

    # Sort ascending for horizontal bar display (highest on top)
    sorted_cats = sorted(category_list, key=lambda c: c["total_spend"], reverse=False)
    categories = [c["category"] for c in sorted_cats]
    spends = [c["total_spend"] for c in sorted_cats]
    shares = [c["percentage_share"] for c in sorted_cats]

    bars = ax.barh(categories, spends, color=COLOR_BAR, height=0.6, alpha=0.85)

    # Annotate bars with amount and percentage
    max_spend = max(spends) if spends else 1
    for bar, spend, share in zip(bars, spends, shares):
        ax.text(
            bar.get_width() + (max_spend * 0.015),
            bar.get_y() + bar.get_height() / 2,
            f"₹{spend:,.0f} ({share:.1f}%)",
            va="center",
            ha="left",
            fontsize=9,
            fontweight="semibold",
            color=COLOR_PRIMARY,
        )

    ax.set_title("Expense Category Breakdown & Expenditure Share (%)", fontsize=14, fontweight="bold", pad=15, color=COLOR_PRIMARY)
    ax.set_xlabel("Total Spend (INR)", fontsize=11, fontweight="bold", color=COLOR_PRIMARY)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_currency))
    ax.set_xlim(left=0, right=max_spend * 1.25)
    ax.grid(axis="x", zorder=0)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved plot: {output_path.name}")


def plot_payment_mode_distribution(mode_list: List[Dict], output_path: Path) -> None:
    """Generate bar chart showing expenditure volume by payment mode."""
    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)

    modes = [m["payment_mode"] for m in mode_list]
    amounts = [m["total_amount"] for m in mode_list]
    counts = [m["transaction_count"] for m in mode_list]

    bars = ax.bar(modes, amounts, color="#0284c7", width=0.55, alpha=0.9)

    max_amt = max(amounts) if amounts else 1
    for bar, amt, cnt in zip(bars, amounts, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max_amt * 0.015),
            f"₹{amt:,.0f}\n({cnt:,} txns)",
            va="bottom",
            ha="center",
            fontsize=8.5,
            fontweight="semibold",
            color=COLOR_PRIMARY,
        )

    ax.set_title("Expenditure Distribution by Payment Mode", fontsize=14, fontweight="bold", pad=15, color=COLOR_PRIMARY)
    ax.set_ylabel("Total Outflow (INR)", fontsize=11, fontweight="bold", color=COLOR_PRIMARY)
    ax.set_xticks(range(len(modes)))
    ax.set_xticklabels(modes, rotation=35, ha="right", fontsize=9.5)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_currency))
    ax.set_ylim(bottom=0, top=max_amt * 1.2)
    ax.grid(axis="y", zorder=0)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved plot: {output_path.name}")


def plot_income_expense_trend(monthly_df: pd.DataFrame, output_path: Path) -> None:
    """Generate time-series line chart featuring 3-month trailing SMA."""
    fig, ax = plt.subplots(figsize=(14, 6), dpi=300)

    x = range(len(monthly_df))
    ax.plot(x, monthly_df["income"], marker="o", markersize=4, label="Monthly Income", color=COLOR_INCOME, linewidth=2.0)
    ax.plot(x, monthly_df["expense"], marker="s", markersize=4, label="Monthly Expense", color=COLOR_EXPENSE, linewidth=2.0)
    
    # Plot SMA line where not null
    sma_series = monthly_df["sma3_expense"]
    ax.plot(x, sma_series, linestyle="--", label="3-Month Trailing SMA (Expense)", color=COLOR_SMA, linewidth=2.2)

    ax.set_title("Income & Expense Trajectory with 3-Month Trailing Moving Average", fontsize=14, fontweight="bold", pad=15, color=COLOR_PRIMARY)
    ax.set_ylabel("Amount (INR)", fontsize=11, fontweight="bold", color=COLOR_PRIMARY)
    ax.set_xticks(list(x))
    ax.set_xticklabels(monthly_df["month_year"], rotation=45, ha="right", fontsize=9)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_currency))
    ax.set_ylim(bottom=0)
    ax.grid(True, zorder=0)
    ax.legend(frameon=True, facecolor="#ffffff", edgecolor="#cbd5e1", fontsize=10, loc="upper right")

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved plot: {output_path.name}")


def plot_weekday_vs_weekend_spending(day_type_data: Dict, output_path: Path) -> None:
    """Generate comparative bar chart for weekday vs weekend average daily spend."""
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)

    categories = ["Weekday Spending", "Weekend Spending"]
    avg_spends = [
        day_type_data["weekday"]["average_daily_spend"],
        day_type_data["weekend"]["average_daily_spend"],
    ]
    tot_spends = [
        day_type_data["weekday"]["total_spend"],
        day_type_data["weekend"]["total_spend"],
    ]
    day_counts = [
        day_type_data["weekday"]["distinct_calendar_days"],
        day_type_data["weekend"]["distinct_calendar_days"],
    ]

    colors = ["#3b82f6", "#f97316"]
    bars = ax.bar(categories, avg_spends, color=colors, width=0.45, alpha=0.9)

    max_avg = max(avg_spends) if avg_spends else 1
    for bar, avg_s, tot_s, cnt in zip(bars, avg_spends, tot_spends, day_counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max_avg * 0.02),
            f"₹{avg_s:,.2f} / day\n(Total: ₹{tot_s:,.0f} across {cnt} days)",
            va="bottom",
            ha="center",
            fontsize=9.5,
            fontweight="semibold",
            color=COLOR_PRIMARY,
        )

    ax.set_title("Normalized Average Daily Spending: Weekdays vs. Weekends", fontsize=13, fontweight="bold", pad=15, color=COLOR_PRIMARY)
    ax.set_ylabel("Average Daily Spend (INR)", fontsize=11, fontweight="bold", color=COLOR_PRIMARY)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_currency))
    ax.set_ylim(bottom=0, top=max_avg * 1.25)
    ax.grid(axis="y", zorder=0)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved plot: {output_path.name}")


def generate_all_plots(processed_csv: Path, plots_dir: Path) -> List[Path]:
    """Generate all 5 publication-ready static charts in plots_dir."""
    logger.info("=" * 70)
    logger.info("PHASE 4: GENERATING STATIC PUBLICATION PLOTS SUITE (300 DPI)")
    logger.info("=" * 70)

    plots_dir.mkdir(parents=True, exist_ok=True)
    analyzer = FinancialAnalyzer.from_csv(processed_csv)

    monthly_records = analyzer.compute_monthly_series()
    monthly_df = pd.DataFrame(monthly_records)

    category_summary = analyzer.compute_category_summary()
    payment_mode_summary = analyzer.compute_payment_mode_summary()
    day_type_data = analyzer.compute_day_type_spending()

    plot_paths = [
        plots_dir / "monthly_income_vs_expenses.png",
        plots_dir / "expense_category_breakdown.png",
        plots_dir / "payment_mode_distribution.png",
        plots_dir / "income_expense_trend.png",
        plots_dir / "weekday_vs_weekend_spending.png",
    ]

    plot_monthly_income_vs_expenses(monthly_df, plot_paths[0])
    plot_expense_category_breakdown(category_summary, plot_paths[1])
    plot_payment_mode_distribution(payment_mode_summary, plot_paths[2])
    plot_income_expense_trend(monthly_df, plot_paths[3])
    plot_weekday_vs_weekend_spending(day_type_data, plot_paths[4])

    logger.info("All 5 static plots successfully generated and saved at 300 DPI.")
    return plot_paths


if __name__ == "__main__":
    p_csv = PROJECT_ROOT / "data" / "processed" / "processed_transactions.csv"
    p_dir = PROJECT_ROOT / "outputs" / "plots"
    generate_all_plots(p_csv, p_dir)
