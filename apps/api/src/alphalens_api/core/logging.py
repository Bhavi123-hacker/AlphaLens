"""Allowlisted JSON events: arbitrary strings, secrets and exception text are omitted."""

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

EVENTS = frozenset({"request.completed", "request.failed"})


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
        # Do not serialize message arguments, paths, headers, extras, or exc_info.
        return json.dumps(fields, sort_keys=True)


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("alphalens")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(SafeJsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
