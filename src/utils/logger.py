"""Structured logging using loguru for Diagnostic Assistant."""

import sys
from typing import Optional

from loguru import logger as _loguru_logger


def setup_logger(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
) -> None:
    """Configure the global loguru logger.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to a log file. If None, logs only to stderr.
        rotation: Log file rotation trigger (size or time, e.g., "10 MB", "1 day").
        retention: Log file retention period (e.g., "7 days").
    """
    _loguru_logger.remove()

    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    _loguru_logger.add(sys.stderr, level=level, format=fmt, colorize=True)

    if log_file:
        _loguru_logger.add(
            log_file,
            level=level,
            format=fmt,
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
        )


def get_logger(name: str):
    """Get a named logger bound to a specific module.

    Args:
        name: Module name (typically __name__).

    Returns:
        loguru logger bound to the given name.
    """
    return _loguru_logger.bind(name=name)
