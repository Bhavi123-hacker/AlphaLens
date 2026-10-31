"""Per-run independent date guard for private EOD collection, never quote acceptance."""

import hashlib
import json
import math
import time
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_data.errors import DataContractError

from . import clock_continuity
from .quote_clock import DRIFT, MAX_AGE, Calibration, combine, last_failure, precise_utc, recent


class ClockGateError(DataContractError):
    """Stable public code plus sanitized, durable clock diagnostics."""

    def __init__(
        self,
        reason: str,
        *,
        stage: str,
        context: dict[str, Any],
        code: str = "DAILY_DATE_OR_CLOCK_DISCONTINUITY",
    ) -> None:
        super().__init__(code)
        self.evidence = {"stage": stage, "reason": reason, "context": context}


def _identity(calibration: Calibration) -> str:
    values = {
        "local": calibration.local.isoformat(),
        "monotonic": calibration.monotonic,
        "bounds": [calibration.lower, calibration.upper],
        "samples": [
            [s.source, s.local.isoformat(), s.monotonic, s.lower, s.upper, s.rtt]
            for s in calibration.samples
        ],
    }
    return hashlib.sha256(json.dumps(values, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _capture() -> dict[str, Any]:
    try:
        return clock_continuity.capture()
    except (ValueError, OSError):
        raise ClockGateError(
            "CLOCK_CONTINUITY_CAPTURE_UNAVAILABLE", stage="CONTINUITY", context={}
        ) from None


def _continuity(before: dict[str, Any], after: dict[str, Any]) -> None:
    try:
        clock_continuity.validate(before, after)
    except ValueError as exc:
        # Only codes defined by our local validator are retained, never raw OS messages.
        reason = str(exc)
        if not reason.startswith("CLOCK_CONTINUITY_") or not reason.replace("_", "").isalnum():
            reason = "CLOCK_CONTINUITY_INVALID"
        raise ClockGateError(
            reason, stage="CONTINUITY", context={"before": before, "after": after}
        ) from None


def _checked_receipt(calibration: Calibration) -> dict[str, Any]:
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
            raise ValueError("DAILY_IST_DATE_BOUNDS_DISAGREE")
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        allowed = {
            "NTP_EVIDENCE_STALE_OR_LOCAL_CLOCK_DISCONTINUITY",
            "NTP_RECEIPT_INTERVAL_TOO_WIDE",
            "DAILY_IST_DATE_BOUNDS_DISAGREE",
        }
        reason = str(exc) if str(exc) in allowed else "DAILY_CLOCK_RECEIPT_INVALID"
        raise ClockGateError(
            reason,
            stage="RECEIPT",
            context={
                "local_at": local.isoformat(),
                "monotonic": mono,
                "calibration_at": calibration.local.isoformat(),
                "calibration_monotonic": calibration.monotonic,
                "calibration_age_seconds": mono - calibration.monotonic,
                "anchor_width_seconds": calibration.upper - calibration.lower,
            },
        ) from None
    return {
        "state": "INDEPENDENT_DATE_BOUNDS_AGREE",
        "local_at": local.isoformat(),
        "lower_at": lower.isoformat(),
        "upper_at": upper.isoformat(),
        "session_date": str(lower.astimezone(ist).date()),
        "authentication": evidence["authentication"],
        "quote_classification_required": False,
        "ntp_evidence": evidence,
        "calibration_monotonic": calibration.monotonic,
        "receipt_monotonic": mono,
        "calibration_id": _identity(calibration),
        "sample_monotonic_seconds": [s.monotonic for s in calibration.samples],
    }


def guard() -> dict[str, Any]:
    before = _capture()
    calibration = recent()
    if calibration is None:
        raise ClockGateError(
            "DAILY_INDEPENDENT_CLOCK_UNAVAILABLE",
            stage="ACQUISITION",
            context=last_failure(),
            code="DAILY_INDEPENDENT_CLOCK_UNAVAILABLE",
        )
    result = _checked_receipt(calibration)
    after = _capture()
    _continuity(before, after)
    result["continuity"] = after
    return result


def refresh(previous: dict[str, Any], *, maximum_wait_seconds: float) -> dict[str, Any]:
    """Renew after cooldown, within its remaining budget and the original NTP cadence.

    A new calibration must contain six observations acquired after this refresh
    began. A cached interval is never extended, relabelled, or accepted here.
    Invalid observations are not retried into acceptance.
    """
    if not math.isfinite(maximum_wait_seconds) or not 0 < maximum_wait_seconds <= 60:
        raise DataContractError("DAILY_CLOCK_REFRESH_BUDGET_EXHAUSTED")
    before = _capture()
    try:
        _continuity(previous["continuity"], before)
        old_mono = previous["calibration_monotonic"]
        if not isinstance(old_mono, (int, float)) or not math.isfinite(old_mono):
            raise ValueError
        if not isinstance(previous["calibration_id"], str):
            raise ValueError
        receipt_mono = previous["receipt_monotonic"]
        if not isinstance(receipt_mono, (int, float)) or not math.isfinite(receipt_mono):
            raise ValueError
        old_lower, old_upper = (
            datetime.fromisoformat(previous[key]) for key in ("lower_at", "upper_at")
        )
        if old_lower.tzinfo is None or old_upper.tzinfo is None or old_lower > old_upper:
            raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, DataContractError):
            raise
        raise DataContractError("DAILY_CLOCK_REFRESH_CONTEXT_MISSING") from None
    started = time.perf_counter()
    calibration = recent()
    waited = 0.0
    if calibration is not None and calibration.monotonic < old_mono:
        raise DataContractError("DAILY_CLOCK_REFRESH_REPLAYED_EVIDENCE")
    if calibration is not None and (
        calibration.monotonic == old_mono
        or any(s.monotonic <= started for s in calibration.samples)
    ):
        # Waiting a full calibration age is deliberately conservative: recent()
        # throttles from the *earlier* attempt start. Never bypass that throttle.
        waited = max(0.001, MAX_AGE - (time.perf_counter() - calibration.monotonic) + 0.001)
        if waited >= maximum_wait_seconds - (time.perf_counter() - started):
            raise DataContractError("DAILY_CLOCK_REFRESH_BUDGET_EXHAUSTED")
        time.sleep(waited)
        _continuity(before, _capture())
        calibration = recent()
    after = _capture()
    _continuity(before, after)
    elapsed = time.perf_counter() - started
    if elapsed > maximum_wait_seconds:
        raise DataContractError("DAILY_CLOCK_REFRESH_BUDGET_EXHAUSTED")
    if calibration is None:
        raise ClockGateError(
            "DAILY_INDEPENDENT_CLOCK_REFRESH_UNAVAILABLE",
            stage="REFRESH_ACQUISITION",
            context=last_failure(),
            code="DAILY_INDEPENDENT_CLOCK_REFRESH_UNAVAILABLE",
        )
    if (
        calibration.monotonic <= old_mono
        or _identity(calibration) == previous["calibration_id"]
        or len(calibration.samples) != 6
        or any(s.monotonic <= started for s in calibration.samples)
    ):
        raise DataContractError("DAILY_CLOCK_REFRESH_REPLAYED_EVIDENCE")
    try:
        recombined = combine(calibration.samples, calibration.local, calibration.monotonic)
        if recombined != calibration:
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        raise ClockGateError(
            "DAILY_REFRESH_CALIBRATION_INVALID", stage="REFRESH", context={}
        ) from None
    result = _checked_receipt(calibration)
    elapsed_since_receipt = result["receipt_monotonic"] - receipt_mono
    if elapsed_since_receipt < 0:
        raise DataContractError("DAILY_CLOCK_REFRESH_REPLAYED_EVIDENCE")
    # This projection checks continuity only. It is never accepted as a new
    # receipt: the fresh interval separately satisfies the original 100 ms cap.
    projected_lower = old_lower + timedelta(seconds=elapsed_since_receipt * (1 - DRIFT))
    projected_upper = old_upper + timedelta(seconds=elapsed_since_receipt * (1 + DRIFT))
    new_lower, new_upper = (datetime.fromisoformat(result[key]) for key in ("lower_at", "upper_at"))
    if max(projected_lower, new_lower) > min(projected_upper, new_upper):
        raise ClockGateError(
            "DAILY_REFRESH_INDEPENDENT_BOUNDS_DISAGREE",
            stage="REFRESH",
            context={
                "projected_lower_at": projected_lower.isoformat(),
                "projected_upper_at": projected_upper.isoformat(),
                "fresh_lower_at": new_lower.isoformat(),
                "fresh_upper_at": new_upper.isoformat(),
            },
        )
    final = _capture()
    _continuity(before, final)
    if time.perf_counter() - started > maximum_wait_seconds:
        raise DataContractError("DAILY_CLOCK_REFRESH_BUDGET_EXHAUSTED")
    result["continuity"] = final
    result["refresh"] = {
        "state": "NEW_OBSERVATIONS_CONTINUITY_VERIFIED",
        "previous_calibration_id": previous["calibration_id"],
        "wait_seconds": waited,
        "elapsed_seconds": elapsed,
        "maximum_seconds": maximum_wait_seconds,
    }
    return result
