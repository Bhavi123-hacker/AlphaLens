"""Pure observed archive window reduction. No fitting, backtesting or strategy selection."""

from collections import defaultdict
from typing import Any

from .analytics import observed, preference_match
from .contracts import Profile


def reduce_partition(
    rows: list[dict[str, Any]], sessions: list[str], profile: Profile
) -> list[dict[str, Any]]:
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
        metrics = observed(points)
        metrics["gross_price"] = float(latest["close"]) if latest.get("close") is not None else None
        isins = {r.get("isin") for r in by_day.values()}
        if None in isins or len(isins) != 1:
            for field in (
                "price_return_percent",
                "maximum_drawdown_percent",
                "daily_volatility_percent",
                "mean_daily_return_over_volatility",
                "positive_period_fraction",
                "relative_volume",
            ):
                metrics[field] = None
        results.append(
            {
                "security_id": identity,
                "symbol": latest["symbol"],
                "metrics": metrics,
                "preferences": preference_match(profile, metrics),
                "window_basis": "EXACT_DECLARED_OBSERVED_CALENDAR_WINDOW",
                "source": "P5_CHECKSUM_VERIFIED_RAW_UNADJUSTED_ARCHIVE",
                "as_of": sessions[-1] if sessions else None,
                "identity": "DATED_CANONICAL_IDENTITY_NOT_CURRENT_MASTER",
                "exclusion": "IDENTITY_CHANGED_OR_UNAVAILABLE"
                if None in isins or len(isins) != 1
                else "INCOMPLETE_OR_REJECTED_PRICE_WINDOW"
                if metrics["missing_count"]
                else None,
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
    return {
        "category": category,
        "measure": measure,
        "observed_cohort": len(rows),
        "comparable_count": len(eligible),
        "leaders": eligible[:size],
        "excluded": [
            {
                "security_id": r["security_id"],
                "reason": r.get("exclusion")
                or "REQUIRED_METRIC_OR_SUPPORTED_PREFERENCE_UNAVAILABLE",
            }
            for r in rows
            if r["security_id"] not in identities
        ],
        "interpretation": (
            "HISTORICAL_HINDSIGHT_RAW_PRICE_DIAGNOSTICS_"
            "NOT_TOTAL_PROFIT_FUTURE_PREDICTIONS_OR_SHARPE"
        ),
        "cohort": "ALL_OBSERVED_ARCHIVE_EQUITY_CANDIDATES_IN_REQUESTED_WINDOW",
        "full_nse_market": False,
        "corporate_actions": "UNVERIFIED",
        "strategy_tuning": False,
    }
