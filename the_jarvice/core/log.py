"""
Logging configuration for The Jarvice.

Sets up logging with file rotation and console output.
Log files are stored in ~/.the-jarvice/logs/
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_LOG_DIR = Path.home() / ".the-jarvice" / "logs"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_MAX_SIZE_MB = 50
DEFAULT_ROTATION = "daily"

LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Mapping of string levels to logging constants
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def setup_logging(
    level: str = DEFAULT_LOG_LEVEL,
    log_dir: Optional[str] = None,
    max_size_mb: int = DEFAULT_MAX_SIZE_MB,
    rotation: str = DEFAULT_ROTATION,
    verbose: bool = False,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """Configure logging for The Jarvice.

    Sets up:
      - File handler with rotation (daily or size-based)
      - Console handler (stderr) with configurable verbosity

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Directory for log files. Defaults to ~/.the-jarvice/logs/
        max_size_mb: Maximum log file size in MB (for size-based rotation).
        rotation: Rotation strategy — "daily" (default) or "size".
        verbose: If True, set console log level to DEBUG regardless of `level`.
        log_file: Specific log file name. Defaults to "the-jarvice.log".

    Returns:
        Configured root logger for the-jarvice.
    """
    # Resolve log directory
    if log_dir:
        log_dir_path = Path(log_dir).expanduser()
    else:
        log_dir_path = DEFAULT_LOG_DIR

    log_dir_path.mkdir(parents=True, exist_ok=True)

    # Resolve log level
    numeric_level = LOG_LEVELS.get(level.upper(), logging.INFO)

    # Resolve log file
    if log_file:
        log_file_path = log_dir_path / log_file
    else:
        log_file_path = log_dir_path / "the-jarvice.log"

    # Get the jarvice logger (not root, to avoid noise)
    logger = logging.getLogger("the_jarvice")
    logger.setLevel(logging.DEBUG)  # Capture everything; handlers filter

    # Remove existing handlers to avoid duplicates on re-configuration
    logger.handlers.clear()

    # ---- File Handler ----
    if rotation == "daily":
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file_path),
            when="midnight",
            interval=1,
            backupCount=30,  # Keep 30 days
            encoding="utf-8",
        )
        file_handler.suffix = "%Y-%m-%d"
    else:
        # Size-based rotation
        max_bytes = max_size_mb * 1024 * 1024  # MB to bytes
        file_handler = RotatingFileHandler(
            filename=str(log_file_path),
            maxBytes=max_bytes,
            backupCount=5,
            encoding="utf-8",
        )

    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(file_handler)

    # ---- Console Handler ----
    console_handler = logging.StreamHandler(sys.stderr)
    if verbose:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(numeric_level)

    # Simpler format for console
    console_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    console_handler.setFormatter(logging.Formatter(console_format, datefmt=DATE_FORMAT))
    logger.addHandler(console_handler)

    # ---- Third-party noise reduction ----
    for noisy in ("urllib3", "requests", "exchangelib", "keyring", "httpcore", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logger.info("Logging initialized (level=%s, dir=%s)", level, log_dir_path)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger under the the_jarvice namespace.

    Args:
        name: Module or component name (e.g., "scraper.exchange").

    Returns:
        Logger instance.
    """
    return logging.getLogger(f"the_jarvice.{name}")


def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    """Log an exception with traceback at ERROR level.

    Args:
        logger: Logger to use.
        message: Context message.
        exc: The exception that occurred.
    """
    logger.error("%s: %s: %s", message, type(exc).__name__, exc, exc_info=True)