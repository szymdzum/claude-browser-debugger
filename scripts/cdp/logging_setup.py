"""Structured logging setup for CDP CLI.

Provides JSON and text logging formats with support for --quiet and --verbose flags.
Implements FR-044, FR-045, FR-046 from spec.md.

Note: Named logging_setup.py to avoid conflicts with Python's built-in logging module.
"""

import sys
import json
import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON for machine-parseable output.

    Implements FR-044: Structured logging in JSON format.

    Example output:
        {"timestamp": "2025-10-24T23:30:00.123Z", "level": "INFO",
         "logger": "scripts.cdp.connection", "message": "Connected to Chrome",
         "extra": {"chrome_port": 9222}}
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string.

        Args:
            record: LogRecord instance

        Returns:
            JSON-formatted log entry
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data["extra"] = record.extra

        # Add function/line info for DEBUG level
        if record.levelno == logging.DEBUG:
            log_data["location"] = {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Formats log records as human-readable text.

    Implements FR-045: Human-readable logging in text format.

    Example output:
        2025-10-24 23:30:00 [INFO] scripts.cdp.connection: Connected to Chrome
    """

    def __init__(self):
        """Initialize with human-readable format string."""
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(
    format_type: str = "text",
    level: Optional[str] = None,
    quiet: bool = False,
    verbose: bool = False,
) -> None:
    """Configure logging for CDP CLI with specified format and level.

    Implements FR-044, FR-045, FR-046 from spec.md.

    Args:
        format_type: Output format - "json" or "text" (default: "text")
        level: Logging level - "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
               If None, determined by quiet/verbose flags
        quiet: Suppress all output except errors (sets level to ERROR)
        verbose: Enable debug output (sets level to DEBUG)

    Precedence for level determination:
        1. quiet flag → ERROR
        2. verbose flag → DEBUG
        3. explicit level argument → as specified
        4. default → INFO

    Note:
        If both quiet and verbose are True, quiet takes precedence.
    """
    # Determine log level with precedence
    if quiet:
        log_level = logging.ERROR
    elif verbose:
        log_level = logging.DEBUG
    elif level:
        log_level = getattr(logging, level.upper(), logging.INFO)
    else:
        log_level = logging.INFO

    # Select formatter based on format type
    formatter: Union[JSONFormatter, TextFormatter]
    if format_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add console handler with selected formatter
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set level for CDP package loggers to match root
    cdp_logger = logging.getLogger("scripts.cdp")
    cdp_logger.setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Usage:
        logger = get_logger(__name__)
        logger.info("Message")
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger, level: int, message: str, **extra_fields
) -> None:
    """Log message with extra context fields (useful for JSON logging).

    Args:
        logger: Logger instance
        level: Logging level (e.g., logging.INFO)
        message: Log message
        **extra_fields: Additional context fields for JSON output

    Example:
        log_with_context(
            logger, logging.INFO, "Connected to Chrome",
            chrome_port=9222, ws_url="ws://localhost:9222/..."
        )

    JSON output:
        {"timestamp": "...", "level": "INFO", "message": "Connected to Chrome",
         "extra": {"chrome_port": 9222, "ws_url": "ws://..."}}
    """
    if extra_fields:
        # Create LogRecord with extra dict for JSONFormatter
        record = logger.makeRecord(
            logger.name, level, "(log_with_context)", 0, message, (), None
        )
        record.extra = extra_fields
        logger.handle(record)
    else:
        logger.log(level, message)
