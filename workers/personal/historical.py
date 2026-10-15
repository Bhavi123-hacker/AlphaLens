"""Strict and separately labelled available-path raw-price diagnostics; no research rerun."""

from collections import Counter, defaultdict
from fractions import Fraction
from typing import Any

from .analytics import observed, preference_match
from .contracts import Profile


def reduce_partition(
    rows: list[dict[str, Any]],
    sessions: list[str],
    profile: Profile,
    mode: str = "strict",
) -> list[dict[str, Any]]:
    if mode not in {"strict", "available_window", "observed_endpoints"}:
        raise ValueError("HISTORICAL_MODE_INVALID")
    histories: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        identity, day = row["security_id"], str(row["session_date"])
        if day in histories[identity]:
            raise ValueError("HISTORICAL_DUPLICATE_SECURITY_SESSION")
        histories[identity][day] = row
    results = []
    for identity, by_day in histories.items():
        latest = by_day[max(by_day)]
        if latest["analytical_type"] != "RESEARCH_EQUITY_CANDIDATE":
            continue
        points = [
            {
                "session": day,
                "close": by_day[day]["close"]
                if day in by_day and by_day[day]["quality"] in {"VALID", "DEGRADED"}
                else None,
                "volume": by_day[day]["volume"] if day in by_day else None,
            }
            for day in sessions
        ]
        isins = {r.get("isin") for r in by_day.values()}
        reasons = []
        if None in isins:
            reasons.append("DATED_ISIN_UNAVAILABLE")
        if len(isins - {None}) > 1:
            reasons.append("DATED_ISIN_CHANGED")
        if any(p["close"] is None for p in points):
            reasons.append("MISSING_OR_REJECTED_PRICE_SLOTS")
        run: list[dict[str, Any]] = []
        last_run: list[dict[str, Any]] = []
        last_isin = None
        # Latest contiguous known-identity path, never the best return.
        for point in points:
            isin = by_day.get(str(point["session"]), {}).get("isin")
            if point["close"] is None or isin is None:
                if run:
                    last_run = run
                run, last_isin = [], None
                continue
            if isin != last_isin:
                if run:
                    last_run = run
                run = []
            run.append(point)
            last_isin = isin
        selected = (run or last_run) if mode == "available_window" else points
        metrics = observed(selected)
        metrics["gross_price"] = (
            float(selected[-1]["close"]) if selected and selected[-1]["close"] is not None else None
        )
        invalid = mode == "strict" and bool(reasons) or len(selected) < 2
        if invalid:
            for field in (
                "price_return_percent",
                "maximum_drawdown_percent",
                "daily_volatility_percent",
                "mean_daily_return_over_volatility",
                "positive_period_fraction",
                "relative_volume",
            ):
                metrics[field] = None
        endpoint_exclusion = None
        if mode == "observed_endpoints":
            identity_safe = None not in isins and len(isins) == 1
            endpoint_safe = (
                len(points) >= 2
                and points[0]["close"] is not None
                and points[-1]["close"] is not None
            )
            for measure in (
                "price_return_percent",
                "maximum_drawdown_percent",
                "daily_volatility_percent",
                "mean_daily_return_over_volatility",
                "positive_period_fraction",
                "relative_volume",
            ):
                metrics[measure] = None
            if identity_safe and endpoint_safe:
                metrics["price_return_percent"] = float(
                    (Fraction(str(points[-1]["close"])) / Fraction(str(points[0]["close"])) - 1)
                    * 100
                )
            if not (identity_safe and endpoint_safe):
                endpoint_exclusion = "MISSING_DATED_ENDPOINT_OR_INCOMPATIBLE_IDENTITY"
        coverage = {
            "requested_slots": len(points),
            "valid_price_slots": sum(p["close"] is not None for p in points),
            "dated_identity_slots": sum(
                bool(by_day.get(str(p["session"]), {}).get("isin")) for p in points
            ),
            "used_contiguous_slots": len(selected),
            "used_observation_slots": metrics["observed_count"],
            "used_fraction": metrics["observed_count"] / len(points) if points else 0,
            "actual_start": selected[0]["session"] if selected else None,
            "actual_end": selected[-1]["session"] if selected else None,
            "full_requested_path": not reasons and len(selected) == len(points),
            "reasons": reasons,
        }
        results.append(
            {
                "security_id": identity,
                "symbol": latest["symbol"],
                "metrics": metrics,
                "preferences": preference_match(profile, metrics),
                "window_basis": (
                    "DATED_ENDPOINT_PRICE_MOVEMENT_WITH_INCOMPLETE_PATH_NOT_TOTAL_RETURN"
                )
                if mode == "observed_endpoints"
                else "STRICT_COMPLETE_OBSERVED_CALENDAR_PATH"
                if mode == "strict"
                else "LATEST_CONTIGUOUS_DATED_IDENTITY_PATH_NOT_FULL_PERIOD_RETURN",
                "source": "P5_CHECKSUM_VERIFIED_RAW_UNADJUSTED_ARCHIVE",
                "as_of": metrics["last_session"],
                "identity": "DATED_CANONICAL_IDENTITY_NOT_CURRENT_MASTER",
                "coverage": coverage,
                "exclusion": endpoint_exclusion
                or (
                    ";".join(reasons)
                    if mode == "strict" and reasons
                    else "FEWER_THAN_TWO_COMPATIBLE_OBSERVATIONS"
                    if len(selected) < 2
                    else None
                ),
            }
        )
    return results


def rank(
    rows: list[dict[str, Any]], category: str, size: int, apply_preferences: bool
) -> dict[str, Any]:
    measure = {
        "price_return": "price_return_percent",
        "risk_adjusted": "mean_daily_return_over_volatility",
        "drawdown": "maximum_drawdown_percent",
        "consistency": "positive_period_fraction",
        "low_volatility": "daily_volatility_percent",
        "volume": "relative_volume",
    }[category]
    eligible = [
        r
        for r in rows
        if r["metrics"].get(measure) is not None
        and (not apply_preferences or r["preferences"]["state"] == "MATCHES_SUPPORTED_CONSTRAINTS")
    ]
    eligible.sort(
        key=lambda r: (
            (1 if category == "low_volatility" else -1) * r["metrics"][measure],
            r["security_id"],
        )
    )
    identities = {r["security_id"] for r in eligible}
    exclusions = [
        {
            "security_id": r["security_id"],
            "reason": r.get("exclusion") or "REQUIRED_METRIC_OR_SUPPORTED_PREFERENCE_UNAVAILABLE",
            "coverage": r.get("coverage"),
        }
        for r in rows
        if r["security_id"] not in identities
    ]
    return {
        "category": category,
        "measure": measure,
        "observed_cohort": len(rows),
        "comparable_count": len(eligible),
        "leaders": eligible[:size],
        "excluded": exclusions,
        "exclusion_counts": dict(Counter(e["reason"] for e in exclusions)),
        "coverage_counts": {
            "full_requested_paths": sum(
                r.get("coverage", {}).get("full_requested_path", False) for r in rows
            ),
            "missing_dated_identity": sum(
                "DATED_ISIN_UNAVAILABLE" in r.get("coverage", {}).get("reasons", []) for r in rows
            ),
            "missing_price_paths": sum(
                "MISSING_OR_REJECTED_PRICE_SLOTS" in r.get("coverage", {}).get("reasons", [])
                for r in rows
            ),
        },
        "interpretation": (
            "HISTORICAL_HINDSIGHT_RAW_PRICE_DIAGNOSTICS_"
            "NOT_TOTAL_PROFIT_FUTURE_PREDICTIONS_OR_SHARPE"
        ),
        "cohort": "ALL_OBSERVED_ARCHIVE_EQUITY_CANDIDATES_IN_REQUESTED_WINDOW",
        "full_nse_market": False,
        "corporate_actions": "UNVERIFIED",
        "strategy_tuning": False,
    }
