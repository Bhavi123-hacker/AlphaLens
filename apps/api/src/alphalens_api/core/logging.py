"""Allowlisted JSON events: arbitrary strings, secrets and exception text are omitted."""

import hashlib
import json
import logging
import os
import re
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import UUID

EVENTS = frozenset(
    {"request.completed", "request.failed", "operation.completed", "operation.failed"}
)


def server_logging_config() -> dict[str, object]:
    """Apply the same redaction boundary to Uvicorn's uncaught ASGI diagnostics."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"safe": {"()": "alphalens_api.core.logging.SafeJsonFormatter"}},
        "handlers": {
            "safe": {
                "class": "logging.StreamHandler",
                "formatter": "safe",
                "stream": "ext://sys.stderr",
            }
        },
        "loggers": {
            name: {"handlers": ["safe"], "level": "INFO", "propagate": False}
            for name in ("uvicorn", "uvicorn.error", "uvicorn.access")
        },
    }


class SafeJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = record.msg if isinstance(record.msg, str) and record.msg in EVENTS else "redacted"
        fields: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "service": "alphalens-api",
            "event": event,
            "severity": record.levelname,
        }
        request_id = getattr(record, "request_id", None)
        try:
            fields["request_id"] = str(UUID(str(request_id)))
        except (ValueError, TypeError, AttributeError):
            fields["request_id"] = None
        status_code = getattr(record, "status_code", None)
        if isinstance(status_code, int) and 100 <= status_code <= 599:
            fields["status_code"] = status_code
        duration = getattr(record, "duration_ms", None)
        if isinstance(duration, (float, int)) and 0 <= duration <= 86_400_000:
            fields["duration_ms"] = round(duration, 3)
        component = getattr(record, "component", None)
        if component in {
            "auth",
            "stocks",
            "research",
            "models",
            "backtests",
            "portfolios",
            "paper",
            "alerts",
            "daily",
            "operations",
            "health",
            "system",
            "other",
        }:
            fields["component"] = component
        run_id = getattr(record, "run_id", None)
        if isinstance(run_id, str) and re.fullmatch("[a-f0-9]{64}", run_id):
            fields["run_id"] = run_id
        operation = getattr(record, "operation", None)
        if operation in {
            "check",
            "backup",
            "restore",
            "process-alerts",
            "run-once",
            "replay",
            "resume",
            "process",
            "deliver",
            "retry",
            "verify",
            "status",
        }:
            fields["operation"] = operation
        # Do not serialize message arguments, paths, headers, extras, or exc_info.
        return json.dumps(fields, sort_keys=True)


def configure_logging(root: Path | None = None) -> logging.Logger:
    suffix = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16] if root else ""
    logger = logging.getLogger("alphalens" + suffix)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(SafeJsonFormatter())
        logger.addHandler(handler)
        if root and root.is_dir():
            from alphalens_api.auth.permissions import verify

            verify(root)
            path = root / "api.jsonl"
            if os.name != "nt":
                try:
                    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                except FileExistsError:
                    verify(path, directory=False)
                else:
                    os.close(descriptor)
            file_handler = RotatingFileHandler(path, maxBytes=2 * 1024 * 1024, backupCount=3)
            file_handler.setFormatter(SafeJsonFormatter())
            logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
