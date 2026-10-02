"""Dataset Inspection and Dynamic Profiler Module.

Empirically inspects and profiles the raw Kaggle dataset
('Daily Household Transactions.csv') without hardcoding schema assumptions.
Audits date patterns, transaction taxonomy, amounts, currencies, missing values,
and candidate duplicates while preserving raw data integrity.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logger import get_logger

logger = get_logger("inspect_dataset")


def compute_file_sha256(filepath: Path) -> str:
    """Compute the SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest().upper()


def analyze_date_tokens(date_series: pd.Series) -> Dict[str, Any]:
    """Dynamically analyze date strings to determine empirical parsing rules."""
    sample_dates = date_series.dropna().astype(str).tolist()
    
    first_token_gt_12 = 0
    second_token_gt_12 = 0
    has_time_count = 0
    delimiters = set()
    sample_patterns = set()

    time_regex = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")

    for raw_val in sample_dates:
        clean_val = raw_val.strip()
        if time_regex.search(clean_val):
            has_time_count += 1
            
        # Extract the date part before whitespace
        date_part = clean_val.split()[0]
        for delim in ["/", "-", "."]:
            if delim in date_part:
                delimiters.add(delim)
                tokens = date_part.split(delim)
                if len(tokens) >= 3:
                    try:
                        t0 = int(tokens[0])
                        t1 = int(tokens[1])
                        if t0 > 12:
                            first_token_gt_12 += 1
                        if t1 > 12:
                            second_token_gt_12 += 1
                    except ValueError:
                        pass
        if len(sample_patterns) < 5:
            sample_patterns.add(clean_val)

    if first_token_gt_12 > 0 and second_token_gt_12 == 0:
        inferred_order = "DD/MM/YYYY (dayfirst=True supported by empirical evidence)"
    elif second_token_gt_12 > 0 and first_token_gt_12 == 0:
        inferred_order = "MM/DD/YYYY (monthfirst=True supported by empirical evidence)"
    else:
        inferred_order = f"Ambiguous/Mixed (token0 > 12: {first_token_gt_12}, token1 > 12: {second_token_gt_12})"

    return {
        "sample_count": len(sample_dates),
        "delimiters_found": list(delimiters),
        "has_timestamp_count": has_time_count,
        "has_timestamp_pct": round((has_time_count / len(sample_dates) * 100), 2) if sample_dates else 0.0,
        "first_token_gt_12": first_token_gt_12,
        "second_token_gt_12": second_token_gt_12,
        "inferred_order": inferred_order,
        "sample_examples": list(sample_patterns),
    }


def profile_raw_dataset(raw_csv_path: Path) -> Dict[str, Any]:
    """Run dynamic inspection on the raw CSV and return a comprehensive audit profile."""
    if not raw_csv_path.exists():
        err_msg = f"Raw dataset not found at expected path: {raw_csv_path}"
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)

    logger.info("=" * 70)
    logger.info("PHASE 2: EMPIRICAL DATASET INSPECTION & DYNAMIC PROFILING")
    logger.info("=" * 70)

    # 1. Physical file metadata
    file_bytes = raw_csv_path.stat().st_size
    file_sha256 = compute_file_sha256(raw_csv_path)
    logger.info(f"File Path: {raw_csv_path}")
    logger.info(f"File Size: {file_bytes:,} bytes")
    logger.info(f"SHA-256 Checksum: {file_sha256}")

    # 2. Raw Ingestion
    df_raw = pd.read_csv(raw_csv_path)
    raw_row_count, raw_col_count = df_raw.shape
    raw_columns = list(df_raw.columns)
    logger.info(f"Raw Dimensions: {raw_row_count:,} rows x {raw_col_count} columns")
    logger.info(f"Raw Column Headers: {raw_columns}")
    logger.info(f"Raw Data Types:\n{df_raw.dtypes.to_string()}")

    # 3. Missing Value Audit
    null_counts = df_raw.isnull().sum()
    null_percentages = (null_counts / raw_row_count * 100).round(2)
    missing_summary = pd.DataFrame({"Missing_Count": null_counts, "Missing_Pct": null_percentages})
    logger.info(f"Missing Value Audit:\n{missing_summary.to_string()}")

    # 4. Date Structure Analysis
    date_analysis = {}
    if "Date" in df_raw.columns:
        date_analysis = analyze_date_tokens(df_raw["Date"])
        logger.info(f"Date Token Analysis:\n"
                    f"  Total records: {date_analysis['sample_count']}\n"
                    f"  Delimiters detected: {date_analysis['delimiters_found']}\n"
                    f"  Records with timestamp: {date_analysis['has_timestamp_count']} ({date_analysis['has_timestamp_pct']}%)\n"
                    f"  First token > 12 count: {date_analysis['first_token_gt_12']}\n"
                    f"  Second token > 12 count: {date_analysis['second_token_gt_12']}\n"
                    f"  Inferred Date Order: {date_analysis['inferred_order']}\n"
                    f"  Sample Raw Dates: {date_analysis['sample_examples']}")

    # 5. Transaction Types (Income/Expense Column)
    txn_type_dist = {}
    if "Income/Expense" in df_raw.columns:
        txn_type_counts = df_raw["Income/Expense"].value_counts(dropna=False)
        txn_type_dist = txn_type_counts.to_dict()
        logger.info(f"Transaction Type Breakdown:\n{txn_type_counts.to_string()}")

    # 6. Amount Distribution & Anomaly Audit
    amount_stats = {}
    if "Amount" in df_raw.columns:
        # Check numeric conversion safely
        amt_numeric = pd.to_numeric(df_raw["Amount"], errors="coerce")
        nan_amounts = amt_numeric.isna().sum()
        zero_amounts = (amt_numeric == 0).sum()
        negative_amounts = (amt_numeric < 0).sum()
        positive_amounts = (amt_numeric > 0).sum()

        amount_stats = {
            "total_records": len(df_raw),
            "non_numeric_count": int(nan_amounts),
            "zero_amount_count": int(zero_amounts),
            "negative_amount_count": int(negative_amounts),
            "positive_amount_count": int(positive_amounts),
            "min_amount": float(amt_numeric.min()) if not amt_numeric.empty else 0.0,
            "max_amount": float(amt_numeric.max()) if not amt_numeric.empty else 0.0,
            "mean_amount": float(amt_numeric.mean()) if not amt_numeric.empty else 0.0,
            "median_amount": float(amt_numeric.median()) if not amt_numeric.empty else 0.0,
        }
        logger.info(f"Amount Statistical Profile:\n"
                    f"  Positive: {positive_amounts:,}, Zero: {zero_amounts}, "
                    f"Negative: {negative_amounts}, Non-numeric: {nan_amounts}\n"
                    f"  Min: {amount_stats['min_amount']:,.2f}, Max: {amount_stats['max_amount']:,.2f}, "
                    f"Median: {amount_stats['median_amount']:,.2f}, Mean: {amount_stats['mean_amount']:,.2f}")

    # 7. Payment Mode Distribution
    mode_dist = {}
    if "Mode" in df_raw.columns:
        mode_counts = df_raw["Mode"].value_counts(dropna=False)
        mode_dist = mode_counts.to_dict()
        logger.info(f"Payment Mode Distribution:\n{mode_counts.to_string()}")

    # 8. Currency Homogeneity
    currency_dist = {}
    if "Currency" in df_raw.columns:
        curr_counts = df_raw["Currency"].value_counts(dropna=False)
        currency_dist = curr_counts.to_dict()
        logger.info(f"Currency Homogeneity:\n{curr_counts.to_string()}")

    # 9. Candidate Duplicate Detection (Identical across all raw columns)
    exact_duplicates_mask = df_raw.duplicated(keep=False)
    candidate_duplicates_df = df_raw[exact_duplicates_mask]
    total_duplicate_rows = len(candidate_duplicates_df)
    unique_duplicate_clusters = df_raw.duplicated(keep="first").sum()

    logger.info(f"Candidate Duplicate Inspection:\n"
                f"  Total rows involved in duplicate clusters: {total_duplicate_rows}\n"
                f"  Unique redundant duplicate candidates (if exact duplicate deletion applied): {unique_duplicate_clusters}")
    
    if unique_duplicate_clusters > 0:
        logger.info(f"Sample duplicate candidate pairs:\n{candidate_duplicates_df.head(6).to_string()}")

    profile_result = {
        "file_sha256": file_sha256,
        "file_bytes": file_bytes,
        "raw_row_count": raw_row_count,
        "raw_col_count": raw_col_count,
        "raw_columns": raw_columns,
        "date_analysis": date_analysis,
        "transaction_type_dist": txn_type_dist,
        "amount_stats": amount_stats,
        "mode_dist": mode_dist,
        "currency_dist": currency_dist,
        "candidate_duplicate_count": int(unique_duplicate_clusters),
        "total_duplicate_cluster_rows": int(total_duplicate_rows),
    }

    logger.info("=" * 70)
    logger.info("PHASE 2 INSPECTION COMPLETE - Empirical findings recorded.")
    logger.info("=" * 70)

    return profile_result


if __name__ == "__main__":
    raw_path = PROJECT_ROOT / "data" / "raw" / "Daily Household Transactions.csv"
    profile_raw_dataset(raw_path)
