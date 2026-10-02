"""Defensive Data Cleaning and Processed Zone Pipeline.

Implements empirical date/time parsing, surrogate ID generation, feature engineering,
evidence-based duplicate auditing, missing value imputation, and row-count reconciliation.
Outputs the authoritative 16-field processed dataset.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logger import get_logger

logger = get_logger("cleaner")

# Authoritative 16-column schema
AUTHORITATIVE_COLUMNS = [
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

ALLOWED_TRANSACTION_TYPES = {"Expense", "Income", "Transfer-Out"}
TIME_REGEX = re.compile(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b")


def parse_date_and_time(raw_date_str: Any) -> Tuple[Optional[str], Optional[str], bool, Optional[datetime]]:
    """Parse raw date string using empirical DD/MM/YYYY rules.
    
    Returns:
        (iso_date, formatted_time, time_available, datetime_obj)
    """
    if pd.isna(raw_date_str) or not str(raw_date_str).strip():
        return None, None, False, None

    date_str = str(raw_date_str).strip()
    
    # Check for timestamp
    time_match = TIME_REGEX.search(date_str)
    extracted_time = None
    time_available = False

    if time_match:
        time_part = time_match.group(1)
        # Normalize to HH:MM:SS
        parts = time_part.split(":")
        if len(parts) == 2:
            extracted_time = f"{int(parts[0]):02d}:{int(parts[1]):02d}:00"
        elif len(parts) == 3:
            extracted_time = f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}"
        time_available = True
        
        # Remove time component for date parsing
        clean_date_part = date_str[:time_match.start()].strip() + " " + date_str[time_match.end():].strip()
        clean_date_part = clean_date_part.strip()
    else:
        clean_date_part = date_str

    try:
        # DD/MM/YYYY parsing based on Phase 2 empirical findings
        parsed_dt = pd.to_datetime(clean_date_part, dayfirst=True)
        iso_date = parsed_dt.strftime("%Y-%m-%d")
        return iso_date, extracted_time, time_available, parsed_dt.to_pydatetime()
    except Exception:
        return None, None, False, None


def clean_dataset(
    raw_csv_path: Path,
    processed_csv_path: Path,
    duplicate_audit_path: Path,
    rejected_records_path: Path,
) -> Dict[str, Any]:
    """Execute defensive cleaning pipeline and produce audited outputs."""
    if not raw_csv_path.exists():
        err_msg = f"Raw dataset missing: {raw_csv_path}"
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)

    logger.info("=" * 70)
    logger.info("PHASE 3: DEFENSIVE DATA CLEANING & PROCESSED ZONE GENERATION")
    logger.info("=" * 70)

    # 1. Ingest raw dataset
    df_raw = pd.read_csv(raw_csv_path)
    raw_row_count = len(df_raw)
    logger.info(f"Ingested raw dataset with {raw_row_count:,} records.")

    # Tracking lists for reconciliation
    clean_rows: List[Dict[str, Any]] = []
    rejected_rows: List[Dict[str, Any]] = []
    duplicate_audit_rows: List[Dict[str, Any]] = []

    # 2. Duplicate Candidate Audit
    # Identify exact duplicate candidate groups across raw columns
    duplicate_mask = df_raw.duplicated(keep=False)
    candidate_indices = df_raw[duplicate_mask].index.tolist()

    # Track seen duplicate candidate signatures
    seen_candidate_signatures: Dict[Tuple, int] = {}
    deduplicated_indices = set()

    for idx, row in df_raw.iterrows():
        try:
            amt_sig_val: Any = float(row.get("Amount", 0.0)) if pd.notna(row.get("Amount")) else 0.0
        except (ValueError, TypeError):
            amt_sig_val = str(row.get("Amount", ""))

        raw_sig = (
            str(row.get("Date", "")),
            str(row.get("Mode", "")),
            str(row.get("Category", "")),
            str(row.get("Subcategory", "")),
            str(row.get("Note", "")),
            amt_sig_val,
            str(row.get("Income/Expense", "")),
            str(row.get("Currency", "")),
        )

        is_duplicate_candidate = idx in candidate_indices

        if is_duplicate_candidate:
            iso_date, extracted_time, time_avail, _ = parse_date_and_time(row.get("Date"))
            raw_note = str(row.get("Note", "")).strip() if pd.notna(row.get("Note")) else ""

            # Evaluation of conclusive evidence:
            # Genuine technical reposts require sub-second timestamps or explicit re-entry note narratives
            has_subsecond_time = time_avail and extracted_time and len(extracted_time.split(":")) == 3
            has_repost_note = any(w in raw_note.lower() for w in ["retry", "duplicate", "double entry", "repost"])

            if raw_sig in seen_candidate_signatures:
                first_seen_idx = seen_candidate_signatures[raw_sig]
                if has_subsecond_time and has_repost_note:
                    # Conclusive technical duplicate: remove second occurrence
                    res_status = "deduplicated_genuine_technical_repost"
                    evidence_reason = "Identical timestamp down to second and explicit retry context"
                    deduplicated_indices.add(idx)
                else:
                    # Ambiguous recurring transaction: retain
                    res_status = "retained_ambiguous_duplicate"
                    evidence_reason = "Lacks sub-second timestamp or represents plausible recurring everyday expense"
                
                duplicate_audit_rows.append({
                    "raw_row_index": idx,
                    "date": row.get("Date"),
                    "mode": row.get("Mode"),
                    "category": row.get("Category"),
                    "subcategory": row.get("Subcategory"),
                    "note": row.get("Note"),
                    "amount": row.get("Amount"),
                    "transaction_type": row.get("Income/Expense"),
                    "currency": row.get("Currency"),
                    "paired_with_row": first_seen_idx,
                    "resolution_status": res_status,
                    "evidence_reason": evidence_reason,
                })
            else:
                seen_candidate_signatures[raw_sig] = idx
                # First occurrence of candidate cluster
                duplicate_audit_rows.append({
                    "raw_row_index": idx,
                    "date": row.get("Date"),
                    "mode": row.get("Mode"),
                    "category": row.get("Category"),
                    "subcategory": row.get("Subcategory"),
                    "note": row.get("Note"),
                    "amount": row.get("Amount"),
                    "transaction_type": row.get("Income/Expense"),
                    "currency": row.get("Currency"),
                    "paired_with_row": idx,
                    "resolution_status": "retained_ambiguous_duplicate",
                    "evidence_reason": "Baseline candidate row in recurring duplicate cluster",
                })

        # Skip rows marked as genuine technical duplicates
        if idx in deduplicated_indices:
            continue

        # 3. Defensive Field Validation & Cleaning
        # A. Date & Time
        iso_date, extracted_time, time_avail, dt_obj = parse_date_and_time(row.get("Date"))
        if not iso_date or not dt_obj:
            rejected_rows.append({
                "raw_row_index": idx,
                "raw_date": row.get("Date"),
                "raw_amount": row.get("Amount"),
                "rejection_reason": "UNPARSEABLE_DATE",
            })
            continue

        # B. Amount
        raw_amt = row.get("Amount")
        try:
            amt_float = float(raw_amt)
            if pd.isna(amt_float) or pd.isnull(amt_float):
                raise ValueError("Amount is NaN")
            cleaned_amount = round(amt_float, 2)
        except Exception:
            rejected_rows.append({
                "raw_row_index": idx,
                "raw_date": row.get("Date"),
                "raw_amount": row.get("Amount"),
                "rejection_reason": "MALFORMED_AMOUNT",
            })
            continue

        # C. Transaction Type
        raw_txn_type = str(row.get("Income/Expense", "")).strip()
        if raw_txn_type not in ALLOWED_TRANSACTION_TYPES:
            rejected_rows.append({
                "raw_row_index": idx,
                "raw_date": row.get("Date"),
                "raw_amount": row.get("Amount"),
                "rejection_reason": "INVALID_TRANSACTION_TYPE",
            })
            continue

        # D. Category & Subcategory Hygiene
        raw_cat = str(row.get("Category", "")).strip()
        cleaned_category = raw_cat.title() if raw_cat else "Uncategorized"

        raw_subcat = row.get("Subcategory")
        if pd.isna(raw_subcat) or not str(raw_subcat).strip():
            cleaned_subcategory = "General"
        else:
            cleaned_subcategory = str(raw_subcat).strip()

        # E. Payment Mode
        raw_mode = row.get("Mode")
        cleaned_mode = str(raw_mode).strip() if pd.notna(raw_mode) and str(raw_mode).strip() else "Cash"

        # F. Note Imputation
        raw_note = row.get("Note")
        if pd.isna(raw_note) or not str(raw_note).strip():
            cleaned_note = "No description provided"
        else:
            cleaned_note = str(raw_note).strip()

        # G. Currency
        raw_curr = row.get("Currency")
        cleaned_currency = str(raw_curr).strip() if pd.notna(raw_curr) and str(raw_curr).strip() else "INR"

        # H. Temporal Derivations
        year = int(dt_obj.year)
        month = int(dt_obj.month)
        month_year = f"{year:04d}-{month:02d}"
        day_name = dt_obj.strftime("%A")
        is_weekend = bool(dt_obj.weekday() >= 5)

        clean_rows.append({
            "raw_row_index": idx,
            "date": iso_date,
            "time": extracted_time,
            "time_available": time_avail,
            "year": year,
            "month": month,
            "month_year": month_year,
            "day_name": day_name,
            "is_weekend": is_weekend,
            "payment_mode": cleaned_mode,
            "category": cleaned_category,
            "subcategory": cleaned_subcategory,
            "note": cleaned_note,
            "transaction_type": raw_txn_type,
            "amount": cleaned_amount,
            "currency": cleaned_currency,
        })

    # 4. Sorting & Surrogate Key Generation
    df_clean = pd.DataFrame(clean_rows)
    if not df_clean.empty:
        # Sort chronologically by date and time (nulls last)
        df_clean["time_sort"] = df_clean["time"].fillna("99:99:99")
        df_clean = df_clean.sort_values(by=["date", "time_sort", "raw_row_index"]).reset_index(drop=True)
        df_clean = df_clean.drop(columns=["time_sort", "raw_row_index"])

        # Generate surrogate transaction_id: GEN-TXN-0001
        df_clean["transaction_id"] = [f"GEN-TXN-{i+1:04d}" for i in range(len(df_clean))]

        # Reorder into authoritative 16-field schema
        df_clean = df_clean[AUTHORITATIVE_COLUMNS]
    else:
        df_clean = pd.DataFrame(columns=AUTHORITATIVE_COLUMNS)


    # 5. Export Processed CSVs
    processed_csv_path.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(processed_csv_path, index=False, encoding="utf-8")
    logger.info(f"Exported authoritative processed dataset to {processed_csv_path} ({len(df_clean):,} records).")

    # Duplicate audit export
    df_duplicate_audit = pd.DataFrame(duplicate_audit_rows)
    df_duplicate_audit.to_csv(duplicate_audit_path, index=False, encoding="utf-8")
    logger.info(f"Exported duplicate audit log to {duplicate_audit_path} ({len(df_duplicate_audit)} records).")

    # Rejected records export
    df_rejected = pd.DataFrame(rejected_rows, columns=["raw_row_index", "raw_date", "raw_amount", "rejection_reason"])
    df_rejected.to_csv(rejected_records_path, index=False, encoding="utf-8")
    logger.info(f"Exported rejected records log to {rejected_records_path} ({len(df_rejected)} records).")

    # 6. Row-Count Accounting Reconciliation
    retained_count = len(df_clean)
    rejected_count = len(df_rejected)
    deduplicated_count = len(deduplicated_indices)
    reconciled_sum = retained_count + rejected_count + deduplicated_count
    balanced = (raw_row_count == reconciled_sum)

    logger.info("-" * 70)
    logger.info("ROW-COUNT RECONCILIATION SUMMARY:")
    logger.info(f"  Raw Source Records:        {raw_row_count:,}")
    logger.info(f"  Retained Clean Records:    {retained_count:,}")
    logger.info(f"  Rejected Records:          {rejected_count:,}")
    logger.info(f"  Deduplicated Records:      {deduplicated_count:,}")
    logger.info(f"  Reconciliation Balance:    {reconciled_sum:,} == {raw_row_count:,} ({'BALANCED 100%' if balanced else 'MISMATCH ERROR'})")
    logger.info("-" * 70)

    if not balanced:
        err_msg = f"Fatal row-count reconciliation failure: Raw={raw_row_count}, Sum={reconciled_sum}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    # Validate schema conformity
    if list(df_clean.columns) != AUTHORITATIVE_COLUMNS:
        err_msg = f"Schema mismatch: Expected {AUTHORITATIVE_COLUMNS}, got {list(df_clean.columns)}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    logger.info("PHASE 3 COMPLETE - Authoritative dataset generated and verified.")
    return {
        "raw_count": raw_row_count,
        "retained_count": retained_count,
        "rejected_count": rejected_count,
        "deduplicated_count": deduplicated_count,
        "is_balanced": balanced,
        "columns": list(df_clean.columns),
    }


if __name__ == "__main__":
    raw_p = PROJECT_ROOT / "data" / "raw" / "Daily Household Transactions.csv"
    processed_p = PROJECT_ROOT / "data" / "processed" / "processed_transactions.csv"
    dup_p = PROJECT_ROOT / "data" / "processed" / "duplicate_audit.csv"
    rej_p = PROJECT_ROOT / "data" / "processed" / "rejected_records.csv"
    clean_dataset(raw_p, processed_p, dup_p, rej_p)
