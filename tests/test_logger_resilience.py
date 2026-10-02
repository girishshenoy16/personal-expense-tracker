"""Test suite for validating logger privacy masking, error logging, and stderr fallback resilience."""

from __future__ import annotations

import io
import logging
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pytest

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.logger import (
    ResilientRotatingFileHandler,
    SensitiveDataFilter,
    get_logger,
    mask_sensitive_data,
)


@pytest.mark.unit
class TestLoggerResilience(unittest.TestCase):
    """Unit test suite for centralized logging security and fault-tolerance."""

    def setUp(self):
        # Reset handlers for a clean test logger
        self.test_logger = get_logger("test_resilience_logger")

    def test_mask_sensitive_data_account_numbers(self):
        """Verify 13-16 digit account/card numbers are masked."""
        raw_msg = "Card payment processed: 4111 2222 3333 4444 approved"
        masked = mask_sensitive_data(raw_msg)
        self.assertNotIn("4111 2222 3333 4444", masked)
        self.assertIn("[REDACTED_ACCOUNT]", masked)

    def test_mask_sensitive_data_notes_narratives(self):
        """Verify sensitive note/narrative indicators are redacted."""
        raw_msg = "Transaction logged. Note: 'Doctor appointment copay personal' Amount: 50.0"
        masked = mask_sensitive_data(raw_msg)
        self.assertNotIn("Doctor appointment copay personal", masked)
        self.assertIn("[REDACTED_NOTE]", masked)

    def test_sensitive_data_filter_dict_and_tuple_args(self):
        """Verify SensitiveDataFilter redacts sensitive fields passed as args."""
        filt = SensitiveDataFilter()
        record_tuple = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=45,
            msg="User transaction: %s",
            args=("Note: confidential doctor memo",),
            exc_info=None,
        )
        filt.filter(record_tuple)
        self.assertIn("[REDACTED_NOTE]", record_tuple.args[0])

        record_dict = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=55,
            msg="User record: %(info)s",
            args=({"info": "Card: 5555 6666 7777 8888"},),
            exc_info=None,
        )
        filt.filter(record_dict)
        self.assertIn("[REDACTED_ACCOUNT]", record_dict.args["info"])

    def test_logger_privacy_filter_in_file_output(self):
        """Verify log messages written to project.log have sensitive content redacted."""
        test_msg = "Payment recorded. note: secret personal narrative"
        self.test_logger.info(test_msg)

        log_file = PROJECT_ROOT / "logs" / "project.log"
        self.assertTrue(log_file.exists())

        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("secret personal narrative", content)
        self.assertIn("[REDACTED_NOTE]", content)

    def test_logger_stderr_fallback_on_io_failure(self):
        """Simulate file handler failure and verify graceful sys.stderr fallback."""
        captured_stderr = io.StringIO()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=80,
            msg="Simulated mission-critical event during disk failure",
            args=(),
            exc_info=None,
        )

        handler = ResilientRotatingFileHandler(
            filename=str(PROJECT_ROOT / "logs" / "project.log"),
            maxBytes=1000,
            backupCount=1,
            encoding="utf-8",
        )

        # Mock super().emit to raise an OSError simulating disk I/O lock
        with patch.object(logging.handlers.RotatingFileHandler, "emit", side_effect=OSError("Disk write I/O failure")):
            with patch("sys.stderr", captured_stderr):
                # Must NOT raise an unhandled exception
                handler.emit(record)

        stderr_output = captured_stderr.getvalue()
        self.assertIn("[LOGGING_FALLBACK_STDERR]", stderr_output)
        self.assertIn("Simulated mission-critical event during disk failure", stderr_output)
        self.assertIn("OSError", stderr_output)

    def test_logger_error_level_routing(self):
        """Verify error messages are routed without crashing."""
        error_msg = "Critical simulated failure event: Note: sensitive transaction error"
        self.test_logger.error(error_msg)
        err_log_file = PROJECT_ROOT / "logs" / "errors.log"
        self.assertTrue(err_log_file.exists())


if __name__ == "__main__":
    unittest.main()
