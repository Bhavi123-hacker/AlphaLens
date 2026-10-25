"""Saved equity discovery is distinct from current provider identity permission.

No acquisition, universe expansion, estimator loading or forecast publication.
Every count refers to its own dated verified evidence, never full live coverage.
"""

import math
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from workers.providers import universe


def descriptive_risk(history: list[dict[str, Any]], exclusions: list[str]) -> dict[str, Any]:
    """Observed price risk, independent of ML eligibility; never fill a missing slot."""
    base: dict[str, Any] = {
        "state": "UNAVAILABLE",
        "daily_return_sd_20": None,
        "observed_price_drawdown_60": None,
        "observation_session": None,
        "basis": "DATED_OBSERVED_ADJUSTED_PRICE_NOT_DIVIDEND_TOTAL_RETURN",
        "calendar_basis": "OBSERVED_COHORT_GRID_NOT_COMPLETE_EXCHANGE_CALENDAR",
        "annualization": None,
    }
    if "KNOWN_CORPORATE_ACTION_LOOKBACK_EXCLUSION" in exclusions:
        return {**base, "reason": "KNOWN_CORPORATE_ACTION_LOOKBACK_EXCLUSION"}
    end = max(
        (index for index, row in enumerate(history) if row.get("close") is not None), default=-1
    )
    if end < 0:
        return {**base, "reason": "NO_SAVED_PRICES"}
    selected = history[max(0, end - 60) : end + 1]
    base["observation_session"] = selected[-1]["session"]
    if len(selected) < 21:
        return {**base, "reason": "INSUFFICIENT_21_OBSERVED_CLOSES"}
    recent = selected[-21:]
    if any(row.get("close") is None for row in recent):
        return {**base, "reason": "MISSING_OBSERVED_PRICE_SLOT"}
    dates = [datetime.fromisoformat(row["session"]).date() for row in recent]
    if dates != sorted(set(dates)) or any(
        (right - left).days > 7 for left, right in zip(dates, dates[1:], strict=False)
    ):
        return {**base, "reason": "UNQUALIFIED_OBSERVED_CALENDAR_GRID"}
    closes = [Decimal(str(row["close"])) for row in recent]
    if any(not value.is_finite() or value <= 0 for value in closes):
        return {**base, "reason": "INVALID_PRICE_EVIDENCE"}
    values = [float(right / left - 1) for left, right in zip(closes, closes[1:], strict=False)]
    mean = math.fsum(values) / len(values)
    sd = math.sqrt(math.fsum((value - mean) ** 2 for value in values) / len(values))
    drawdown = None
    if len(selected) == 61 and all(row.get("close") is not None for row in selected):
        full_dates = [datetime.fromisoformat(row["session"]).date() for row in selected]
        full = [Decimal(str(row["close"])) for row in selected]
        if (
            full_dates == sorted(set(full_dates))
            and all(
                (right - left).days <= 7
                for left, right in zip(full_dates, full_dates[1:], strict=False)
            )
            and all(value.is_finite() and value > 0 for value in full)
        ):
            peak, drawdown = full[0], 0.0
            for close in full:
                peak = max(peak, close)
                drawdown = min(drawdown, float(close / peak - 1))
    return {
        **base,
        "state": "AVAILABLE",
        "reason": None,
        "daily_return_sd_20": sd,
        "observed_price_drawdown_60": drawdown,
        "drawdown_unavailable_reason": "COMPLETE_61_CLOSE_PATH_REQUIRED"
        if drawdown is None
        else None,
    }


def identity_status(snapshot: universe.Snapshot, *, at: datetime) -> dict[str, Any]:
    if at.utcoffset() is None or snapshot.observed_at > at:
        raise ValueError("DATED_DISCOVERY_CLOCK_INVALID")
    fresh = at <= snapshot.observed_at + timedelta(hours=24)
    return {
        "state": "FRESH" if fresh else "STALE",
        "observed_at": snapshot.observed_at.isoformat(),
        "expires_at": (snapshot.observed_at + timedelta(hours=24)).isoformat(),
        "discovery_available": True,
        "current_identity_actions_available": fresh,
        "basis": "DATED_VERIFIED_MASTER_NOT_PROOF_OF_CURRENT_LISTING_OR_DATA_ACCESS",
    }


def empty_security(record: dict[str, Any]) -> dict[str, Any]:
    """A known identity can open without fictional observations or model scores."""
    return {
        "key": record["instrument_key"],
        "symbol": record["symbol"],
        "name": record["name"],
        "isin": record["isin"],
        "support_status": "SUPPORTED_EQUITY_NO_SAVED_HISTORY"
        if record["eligible_common_equity"]
        else "UNSUPPORTED_INSTRUMENT",
        "support_reason": record["classification"],
        "freshness": "UNAVAILABLE",
        "session": None,
        "received_at": None,
        "source": "NO_SAVED_PRICE_OBSERVATIONS",
        **{
            field: None
            for field in (
                "open",
                "high",
                "low",
                "close",
                "volume",
                "previous_close",
                "change",
                "change_percent",
            )
        },
    }


def measure(snapshot: universe.Snapshot, view: dict[str, Any], *, at: datetime) -> dict[str, Any]:
    """Measure identity, price, feature and score denominators independently."""
    state = identity_status(snapshot, at=at)
    supported = {row["instrument_key"] for row in snapshot.records if row["eligible_common_equity"]}
    observed = {row["key"]: row for row in view["rows"] if row["key"] in supported}
    priced = {key for key, row in observed.items() if row["close"] is not None}
    latest = view["latest_observed_session"]
    recent = {key for key in priced if observed[key]["session"] == latest}
    workspace = view.get("research_workspace") or {}
    scores = workspace.get("scores") or {}
    candidates = {
        row["key"]: row for row in workspace.get("candidates", []) if row["key"] in supported
    }
    today = at.astimezone(ZoneInfo("Asia/Kolkata")).date()
    eligible = {
        key
        for key, row in candidates.items()
        if 0 <= (today - datetime.fromisoformat(row["session"]).date()).days <= 7
        and type(row.get("risk", {}).get("return_daily_sd_20")) in {int, float}
        and 0 <= row["risk"]["return_daily_sd_20"] < float("inf")
    }
    feature_exclusions: dict[str, set[str]] = {}
    for row in workspace.get("technical_exclusions", []):
        if row["key"] in supported:
            feature_exclusions.setdefault(row["key"], set()).add(row["reason"])
    feature_count = workspace.get("coverage", {}).get("technical_feature_eligible_securities")
    return {
        "identity": state,
        "master_snapshot_id": snapshot.snapshot_id,
        "supported_equities": len(supported),
        "searchable_equities": len(supported),
        "available_saved_prices": len(priced),
        "latest_retained_session": latest,
        "latest_session_prices": len(recent),
        "configured_collection_securities": view["configured_securities"],
        "latest_retained_session_coverage_fraction": (
            view["latest_session_securities"] / view["configured_securities"]
            if view["configured_securities"]
            else None
        ),
        "daily_update_success_rate": None,
        "daily_update_success_rate_reason": (
            "RETAINED_SESSION_COVERAGE_IS_NOT_RUN_SUCCESS_OR_EXPECTED_SESSION_COVERAGE"
        ),
        "sufficient_ml_features_latest_session": feature_count,
        "feature_session": workspace.get("current_feature_date"),
        "saved_compatible_predictions": len(candidates),
        "prediction_observation_session": scores.get("observation_session"),
        "prediction_generated_at": scores.get("generated_at"),
        "latest_session_predictions": sum(row["session"] == latest for row in candidates.values()),
        "dated_ranking_eligible_predictions": len(eligible),
        "top_n_returnable": {str(n): min(n, len(eligible)) for n in (5, 10, 20)},
        "ranking_scope": "ALL_ELIGIBLE_SAVED_PREDICTIONS_BEFORE_TOP_N_PAGINATION",
        "ranking_security_cap": None,
        "accepted_ml_predictions": 0,
        "exclusions": {
            "no_saved_price": len(supported - priced),
            "price_not_on_latest_retained_session": len(priced - recent),
            "no_saved_compatible_prediction": len(supported - candidates.keys()),
            "saved_prediction_ineligible_for_dated_ranking": len(candidates.keys() - eligible),
        },
        "latest_feature_exclusion_reasons": dict(
            sorted(
                Counter(
                    reason for reasons in feature_exclusions.values() for reason in reasons
                ).items()
            )
        ),
        "unsupported_master_records": snapshot.summary.get("exclusion_counts", {}),
        "limitations": [
            "Dated master discovery does not establish present-day listing or delisting status",
            "Feature and score counts have different dates and cannot be added",
            "Risk policy is experimental; calibrated probability and independent acceptance absent",
            "Overlapping exclusion categories are not a partition",
            "Expanded live collection remains disabled pending exact policy approval",
        ],
        "provider_requests": 0,
    }


def identity_history(root: Path, key: str) -> dict[str, Any]:
    observations = []
    unverified = []
    for path in root.glob("snapshot-*.json"):
        snapshot_id = path.stem.removeprefix("snapshot-")
        try:
            snapshot = universe.load(root, snapshot_id=snapshot_id)
            identity_status(snapshot, at=datetime.now(UTC))
        except (OSError, ValueError, KeyError, TypeError):
            # A failed historical derivation is visible, never promoted into a
            # listing transition or repaired by modifying its original evidence.
            unverified.append(
                {"snapshot_id": snapshot_id, "reason": "SAVED_MASTER_VERIFICATION_FAILED"}
            )
            continue
        record = next((row for row in snapshot.records if row["instrument_key"] == key), None)
        observations.append(
            {
                "snapshot_id": snapshot.snapshot_id,
                "observed_at": snapshot.observed_at.isoformat(),
                "record": record,
                "presence": "OBSERVED" if record is not None else "ABSENT_NOT_VERIFIED_DELISTING",
            }
        )
    observations.sort(key=lambda row: (row["observed_at"], row["snapshot_id"]))
    return {
        "key": key,
        "observations": observations,
        "unverified_snapshots": sorted(unverified, key=lambda row: row["snapshot_id"]),
        "complete_snapshot_history": not unverified,
        "historical_membership_established": False,
        "absence_is_not_verified_delisting": True,
        "provider_requests": 0,
    }
