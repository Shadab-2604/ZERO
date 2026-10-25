"""
Structured logging configuration with log rotation and credential redaction.
"""

import logging
from logging.handlers import RotatingFileHandler
import re
from app.utils.paths import get_logs_dir

# Patterns to sanitize in logs
_SENSITIVE_PATTERNS = [
    re.compile(r'(api[-_]?key["\']?\s*[:=]\s*["\']?)([^"\'\s,]+)', re.IGNORECASE),
    re.compile(r'(authorization["\']?\s*[:=]\s*["\']?Bearer\s+)([^"\'\s,]+)', re.IGNORECASE),
    re.compile(r'(password["\']?\s*[:=]\s*["\']?)([^"\'\s,]+)', re.IGNORECASE),
    re.compile(r'(secret["\']?\s*[:=]\s*["\']?)([^"\'\s,]+)', re.IGNORECASE),
]


class RedactingFormatter(logging.Formatter):
    """Custom logging formatter that strips API keys and secrets from log output."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        redacted = original
        for pattern in _SENSITIVE_PATTERNS:
            redacted = pattern.sub(r"\1[REDACTED]", redacted)
        return redacted


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Initialize root and ZERO logger with rotating file and console handlers."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger = logging.getLogger("zero")
    logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is called multiple times
    if logger.handlers:
        return logger

    formatter = RedactingFormatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file handler (5MB per file, up to 5 backups)
    log_file = get_logs_dir() / "zero.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Also route external root handlers safely
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger.info("Zero logging initialized. Level: %s", log_level)
    return logger
