"""Private educational display only; never a verified quote or financial input."""

import threading
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_data.providers.multi_contracts import Instrument

from .quote_clock import MAX_AGE, MAX_WIDTH
from .upstox import Reply

STATE = "INDICATIVE_PROVIDER_QUOTE_TIME_UNCERTAIN"


def uncertain_quote(
    reply: Reply, instrument: Instrument, strict: dict[str, Any]
) -> dict[str, Any] | None:
    # Local import avoids making the strict validator depend on this display policy.
    from .upstox_terminal import clock_evidence, entry, epoch, price

    if (
        strict.get("state") != "QUOTE_TIME_REJECTED"
        or reply.state != "ACCEPTED"
        or reply.status != 200
        or not reply.clock_required
        or instrument.provider != "upstox"
        or instrument.exchange != "NSE"
        or instrument.segment != "NSE_EQ"
        or instrument.instrument_type != "EQ"
        or not instrument.isin
        or instrument.provider_key != "NSE_EQ|" + instrument.isin
    ):
        return None
    try:
        clock = clock_evidence(reply)
        evidence = clock["calibration"]
        if evidence["state"] != "BOUNDED_INDEPENDENT_NTP_ASSUMPTION":
            return None
        lower, upper = (
            datetime.fromisoformat(evidence[k]) for k in ("receipt_lower_at", "receipt_upper_at")
        )
        value = entry(reply, instrument)
        if value.get("symbol") != instrument.symbol:
            return None
        generated = datetime.fromisoformat(value["timestamp"])
        traded = epoch(value["last_trade_time"])
        if (
            generated.tzinfo is None
            or not lower < generated <= upper
            or traded > generated
            or not 0 <= (upper - lower).total_seconds() <= MAX_WIDTH
            or (upper - generated).total_seconds() > MAX_AGE
        ):
            return None
        ltp = price(value["last_price"])
        previous = (
            price(value["prev_close_price"]) if value.get("prev_close_price") is not None else None
        )
        delta = ltp - previous if previous is not None else None
        ist = ZoneInfo("Asia/Kolkata")
        return {
            "state": STATE,
            "display_only": True,
            "strict_verified": False,
            "financial_input_eligible": False,
            "is_final_eod_close": False,
            "usage": "AUTHENTICATED_PRIVATE_EDUCATIONAL_DISPLAY_ONLY",
            "source": "UPSTOX_FULL_QUOTE_V3",
            "instrument_key": instrument.provider_key,
            "clock": clock,
            "raw_provider_timestamp": value["timestamp"],
            "raw_last_trade_time": value["last_trade_time"],
            "snapshot_at": generated.isoformat(),
            "last_trade_at": traded.isoformat(),
            "ltp": str(ltp),
            "previous_close": str(previous) if previous is not None else None,
            "change": str(delta) if delta is not None else None,
            "change_percent": str(delta / previous * 100)
            if delta is not None and previous is not None
            else None,
            "change_basis": "LTP_MINUS_UPSTOX_V3_PREV_CLOSE_PRICE",
            "freshness": "SAME_LOCAL_DATE_TRADE"
            if traded.astimezone(ist).date()
            == lower.astimezone(ist).date()
            == upper.astimezone(ist).date()
            else "OLDER_TRADE",
            "timing_uncertainty_seconds": (upper - lower).total_seconds(),
            "restrictions": [
                "NO_ML_FEATURES_OR_PREDICTIONS",
                "NO_CURRENT_RANKINGS_OR_SIGNALS",
                "NO_PORTFOLIO_VALUATION_OR_REVIEWS",
                "NO_ALERT_EVALUATION",
                "NO_RETAINED_EOD_INGESTION",
                "NO_EXECUTION_OR_PUBLIC_REDISTRIBUTION",
            ],
        }
    except (ValueError, TypeError, KeyError, OverflowError):
        return None


def visible(value: dict[str, Any] | None, age: float) -> dict[str, Any] | None:
    from .upstox_terminal import display_quote

    if value is None:
        return None
    result = display_quote(value, age)
    return result if result["state"] == STATE else None


def expire_field(item: dict[str, Any], lock: Any) -> None:
    """Passive removal of the display-only payload; retains independent EOD charts."""
    value = item.get("indicative_quote")
    if value is None:
        return
    evidence = value["clock"]["calibration"]
    remaining = (
        MAX_AGE
        - evidence["evidence_age_seconds"]
        - (time.perf_counter() - evidence["receipt_perf_counter"])
    )

    def purge() -> None:
        with lock:
            if item.get("indicative_quote") is value:
                item["indicative_quote"] = None

    timer = threading.Timer(max(0, remaining), purge)
    timer.daemon = True
    timer.start()
