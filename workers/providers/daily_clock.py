"""Per-run independent date guard for private EOD collection, never quote acceptance."""

import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_data.errors import DataContractError

from .quote_clock import precise_utc, recent


def guard() -> dict[str, Any]:
    calibration = recent()
    if calibration is None:
        raise DataContractError("DAILY_INDEPENDENT_CLOCK_UNAVAILABLE")
    local, mono = precise_utc(), time.perf_counter()
    try:
        evidence = calibration.receipt(local, mono)
        lower, upper = (
            datetime.fromisoformat(evidence[k]) for k in ("receipt_lower_at", "receipt_upper_at")
        )
        ist = ZoneInfo("Asia/Kolkata")
        if (
            not lower.astimezone(ist).date()
            == local.astimezone(ist).date()
            == upper.astimezone(ist).date()
        ):
            raise ValueError
    except (ValueError, TypeError, KeyError, OverflowError):
        raise DataContractError("DAILY_DATE_OR_CLOCK_DISCONTINUITY") from None
    return {
        "state": "INDEPENDENT_DATE_BOUNDS_AGREE",
        "local_at": local.isoformat(),
        "lower_at": lower.isoformat(),
        "upper_at": upper.isoformat(),
        "session_date": str(lower.astimezone(ist).date()),
        "authentication": evidence["authentication"],
        "quote_classification_required": False,
    }
