"""Centralized logging configuration for Personal Expense Tracker.

Provides resilient, size-based rotating file handlers for general application
milestones (logs/project.log) and critical errors (logs/errors.log), console
streaming, privacy redaction of sensitive narratives/notes, and an automatic
sys.stderr fallback mechanism in the event of file I/O or permission failures.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import sys
from typing import Optional

# Default log rotation configuration
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
PROJECT_LOG_FILE = LOG_DIR / "project.log"
ERRORS_LOG_FILE = LOG_DIR / "errors.log"
MAX_BYTES = 5_242_880  # 5 MB
BACKUP_COUNT = 3
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

# Sensitive data patterns for privacy masking
SENSITIVE_PATTERNS = [
    # Card / Account numbers (e.g., 12-16 digits with or without dashes/spaces)
    (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "[REDACTED_ACCOUNT]"),
    # Sensitive personal/merchant narrative indicators in free-text notes
    (re.compile(r"(?i)\b(?:note|narrative|memo|comment|description):\s*['\"]?[^'\";\n]+['\"]?"), "[REDACTED_NOTE]"),
]


def mask_sensitive_data(message: str) -> str:
    """Sanitize sensitive financial descriptions, account numbers, or personal notes."""
    if not isinstance(message, str):
        message = str(message)
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


def _sanitize_arg(arg: Any) -> Any:
    if isinstance(arg, str):
        return mask_sensitive_data(arg)
    if isinstance(arg, dict):
        return {k: _sanitize_arg(v) for k, v in arg.items()}
    if isinstance(arg, (list, tuple)):
        sanitized = [_sanitize_arg(x) for x in arg]
        return tuple(sanitized) if isinstance(arg, tuple) else sanitized
    return arg


class SensitiveDataFilter(logging.Filter):
    """Logging filter that redacts sensitive personal data from all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_sensitive_data(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: _sanitize_arg(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(_sanitize_arg(a) for a in record.args)
        return True


class ResilientRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler with explicit fallback to sys.stderr on I/O or permission failure.
    
    Ensures pipeline operations never crash due to logging failures, and never
    silently conceal log messages or underlying exceptions.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except Exception:
            self.handleError(record)

    def handleError(self, record: logging.LogRecord) -> None:
        """Fallback mechanism to write directly to sys.stderr on file failure."""
        try:
            exc_type, exc_value, _ = sys.exc_info()
            err_name = exc_type.__name__ if exc_type else "UnknownError"
            formatted_msg = self.format(record)
            fallback_line = (
                f"[LOGGING_FALLBACK_STDERR] [HandlerError: {err_name}] "
                f"[TargetFile: {self.baseFilename}] {formatted_msg}\n"
            )
            sys.stderr.write(fallback_line)
            sys.stderr.flush()
        except Exception:
            # Prevent secondary recursion in stderr fallback
            pass


def get_logger(name: str = "expense_tracker") -> logging.Logger:
    """Retrieve or initialize the centralized project logger.
    
    Args:
        name: Subsystem or module name (e.g. 'cleaner', 'analyzer').
        
    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Resolve log level from environment variable
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(log_level)

    # Ensure log directory exists
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        sys.stderr.write(f"[LOGGING_INIT_ERROR] Failed to create log directory {LOG_DIR}: {e}\n")

    formatter = logging.Formatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DATE_FORMAT)
    privacy_filter = SensitiveDataFilter()

    # 1. Console Stream Handler (sys.stdout, level INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(privacy_filter)
    logger.addHandler(console_handler)

    # 2. Resilient Rotating File Handler for project.log (level INFO)
    try:
        project_handler = ResilientRotatingFileHandler(
            filename=str(PROJECT_LOG_FILE),
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        project_handler.setLevel(logging.INFO)
        project_handler.setFormatter(formatter)
        project_handler.addFilter(privacy_filter)
        logger.addHandler(project_handler)
    except Exception as e:
        sys.stderr.write(f"[LOGGING_INIT_ERROR] Could not initialize project.log handler: {e}\n")

    # 3. Resilient Rotating File Handler for errors.log (level ERROR)
    try:
        error_handler = ResilientRotatingFileHandler(
            filename=str(ERRORS_LOG_FILE),
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler.addFilter(privacy_filter)
        logger.addHandler(error_handler)
    except Exception as e:
        sys.stderr.write(f"[LOGGING_INIT_ERROR] Could not initialize errors.log handler: {e}\n")

    # Prevent propagation to root logger to avoid double logging
    logger.propagate = False
    return logger
