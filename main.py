"""Main Pipeline Orchestrator for Personal Expense Tracker with Data Visualization.

Executes all core modular operational modules sequentially:
1. Initialize centralized logging (src/logger.py)
2. Dynamic raw dataset inspection & dynamic profiling (src/inspect_dataset.py)
3. Defensive data cleaning & 16-field processed zone generation (src/cleaner.py)
4. Financial analytics & pre-aggregated web payload export (src/analyzer.py)
5. Static publication-grade 300 DPI plots generation (src/plotter.py)
6. Automated pipeline & contract parity test validation (tests/validate_pipeline.py)
7. Authoritative project report & summary CSV generation (src/reporter.py)

Measures execution duration, provides informative console feedback, and exits
with code 0 on complete success or code 1 on failure.
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analyzer import run_analysis
from src.cleaner import clean_dataset
from src.inspect_dataset import profile_raw_dataset
from src.logger import get_logger
from src.plotter import generate_all_plots
from src.reporter import generate_reports

logger = get_logger("orchestrator")

# Canonical paths
RAW_CSV_PATH = PROJECT_ROOT / "data" / "raw" / "Daily Household Transactions.csv"
PROCESSED_CSV_PATH = PROJECT_ROOT / "data" / "processed" / "processed_transactions.csv"
DUPLICATE_AUDIT_PATH = PROJECT_ROOT / "data" / "processed" / "duplicate_audit.csv"
REJECTED_RECORDS_PATH = PROJECT_ROOT / "data" / "processed" / "rejected_records.csv"
PAYLOAD_JS_PATH = PROJECT_ROOT / "docs" / "data.js"
PLOTS_DIR = PROJECT_ROOT / "outputs" / "plots"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"


def run_pipeline() -> int:
    """Execute the end-to-end data pipeline sequentially."""
    start_time = time.time()
    logger.info("=" * 75)
    logger.info("PERSONAL EXPENSE TRACKER - END-TO-END PIPELINE EXECUTION")
    logger.info(f"Root Directory: {PROJECT_ROOT}")
    logger.info("=" * 75)

    try:
        # -------------------------------------------------------------
        # Step 1: Raw Dataset Inspection & Dynamic Profiling
        # -------------------------------------------------------------
        logger.info("\n>>> [STEP 1/6] Executing Raw Dataset Dynamic Profiling (src/inspect_dataset.py)...")
        profile_res = profile_raw_dataset(RAW_CSV_PATH)
        logger.info(f"Step 1 Complete: {profile_res['raw_row_count']:,} raw records profiled. Checksum verified.")

        # -------------------------------------------------------------
        # Step 2: Defensive Cleaning & 16-Column Export
        # -------------------------------------------------------------
        logger.info("\n>>> [STEP 2/6] Executing Defensive Cleaning Pipeline (src/cleaner.py)...")
        clean_res = clean_dataset(
            raw_csv_path=RAW_CSV_PATH,
            processed_csv_path=PROCESSED_CSV_PATH,
            duplicate_audit_path=DUPLICATE_AUDIT_PATH,
            rejected_records_path=REJECTED_RECORDS_PATH,
        )
        logger.info(f"Step 2 Complete: {clean_res['retained_count']:,} clean records exported. "
                    f"Row reconciliation balanced 100%.")

        # -------------------------------------------------------------
        # Step 3: Financial Analytics & Pre-Aggregated Payload Export
        # -------------------------------------------------------------
        logger.info("\n>>> [STEP 3/6] Executing Financial Analytics Engine (src/analyzer.py)...")
        payload = run_analysis(
            processed_csv=PROCESSED_CSV_PATH,
            payload_js_path=PAYLOAD_JS_PATH,
        )
        logger.info(f"Step 3 Complete: Pre-aggregated public payload exported to {PAYLOAD_JS_PATH.name}.")

        # -------------------------------------------------------------
        # Step 4: Static Analytical Visualizations (300 DPI)
        # -------------------------------------------------------------
        logger.info("\n>>> [STEP 4/6] Generating Static Analytical Plots Suite (src/plotter.py)...")
        plots = generate_all_plots(
            processed_csv=PROCESSED_CSV_PATH,
            plots_dir=PLOTS_DIR,
        )
        logger.info(f"Step 4 Complete: {len(plots)} publication-quality PNG charts rendered at 300 DPI.")

        # -------------------------------------------------------------
        # Step 5: Automated QA Test Suite Validation
        # -------------------------------------------------------------
        logger.info("\n>>> [STEP 5/6] Running Automated Quality Assurance Suite (tests/validate_pipeline.py)...")
        from tests.validate_pipeline import TestPipeline
        suite = unittest.TestLoader().loadTestsFromTestCase(TestPipeline)
        runner = unittest.TextTestRunner(verbosity=2)
        test_result = runner.run(suite)

        if not test_result.wasSuccessful():
            err_msg = f"Test validation suite failed with {len(test_result.failures)} failures and {len(test_result.errors)} errors."
            logger.error(err_msg)
            return 1

        logger.info("Step 5 Complete: All 7 automated validation test assertions passed.")

        # -------------------------------------------------------------
        # Step 6: Authoritative Project Report & Summary CSV Compilation
        # -------------------------------------------------------------
        logger.info("\n>>> [STEP 6/6] Compiling Authoritative Reports & Summary CSVs (src/reporter.py)...")
        rep_res = generate_reports(
            processed_csv=PROCESSED_CSV_PATH,
            reports_dir=REPORTS_DIR,
        )
        logger.info(f"Step 6 Complete: Project report and summary CSVs generated at outputs/reports/.")

        # -------------------------------------------------------------
        # Pipeline Completion Summary
        # -------------------------------------------------------------
        total_duration = time.time() - start_time
        logger.info("=" * 75)
        logger.info("PIPELINE COMPLETED SUCCESSFULLY (EXIT CODE 0)")
        logger.info(f"Total Execution Time: {total_duration:.2f} seconds")
        logger.info(f"Clean Data:     {PROCESSED_CSV_PATH}")
        logger.info(f"Duplicate Log:  {DUPLICATE_AUDIT_PATH}")
        logger.info(f"Web Payload:    {PAYLOAD_JS_PATH}")
        logger.info(f"Plots Suite:    {PLOTS_DIR}")
        logger.info(f"Reports Suite:  {rep_res['report_md']}")
        logger.info(f"Project Logs:   {PROJECT_ROOT / 'logs' / 'project.log'}")
        logger.info("=" * 75)
        return 0

    except Exception as exc:
        logger.exception(f"Unhandled exception during pipeline execution: {exc}")
        sys.stderr.write(f"\n[FATAL ERROR] Pipeline terminated prematurely: {exc}\n")
        return 1


if __name__ == "__main__":
    exit_code = run_pipeline()
    sys.exit(exit_code)
