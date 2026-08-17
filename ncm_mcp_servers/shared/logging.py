"""Structured logging configuration for NCM MCP Servers.

Provides JSON-formatted log output for containerized deployments
and human-readable output for local development.

Usage:
    from ncm_mcp_servers.shared.logging import get_logger
    logger = get_logger("ncm_fleet")
    logger.info("Server started", extra={"port": 3001})
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON for container environments."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Include any extra fields passed via extra={}
        for key in record.__dict__:
            if key not in logging.LogRecord(
                "", 0, "", 0, "", (), None
            ).__dict__ and key not in ("message", "msg"):
                log_entry[key] = record.__dict__[key]
        return json.dumps(log_entry, default=str)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter for local development."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )


def get_logger(
    name: str,
    level: Optional[str] = None,
) -> logging.Logger:
    """Get a configured logger for an NCM MCP server component.

    Args:
        name: Logger name (e.g., "ncm_fleet", "ncm_monitoring").
        level: Log level override. Defaults to LOG_LEVEL env var or INFO.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(f"ncm_mcp.{name}")

    if logger.handlers:
        return logger

    log_level = level or os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    handler = logging.StreamHandler(sys.stdout)

    log_format = os.environ.get("LOG_FORMAT", "auto").lower()
    if log_format == "json" or (
        log_format == "auto" and not sys.stdout.isatty()
    ):
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(HumanFormatter())

    logger.addHandler(handler)
    logger.propagate = False

    return logger
