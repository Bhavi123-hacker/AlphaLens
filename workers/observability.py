"""Finite worker logging bridge; no data library imports API or emits payloads."""

import os
import time
from pathlib import Path


def completed(
    component: str, operation: str, started: float, status: int = 200, run_id: str | None = None
) -> None:
    from alphalens_api.core.logging import configure_logging

    value = os.environ.get("ALPHALENS_OPERATIONS_ROOT")
    try:
        logger = configure_logging(Path(value) if value else None)
    except (OSError, ValueError):
        logger = configure_logging()
    logger.info(
        "operation.completed",
        extra={
            "component": component,
            "operation": operation,
            "duration_ms": (time.perf_counter() - started) * 1000,
            "status_code": status,
            "run_id": run_id,
        },
    )
