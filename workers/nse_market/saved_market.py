"""Bounded descriptive views of verified private candles, with no acquisition.

Changes compare adjacent observed cohort sessions only. The observed grid is not
an independently complete exchange calendar and prices are not streaming quotes.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from workers.experimental_nse.acquire import private_path


def project(frame: dict[str, Any], *, at: datetime) -> dict[str, Any]:
    if at.utcoffset() is None:
        raise ValueError("AWARE_SAVED_MARKET_CLOCK_REQUIRED")
    today = at.astimezone(ZoneInfo("Asia/Kolkata")).date()
    sessions = frame["sessions"]
    if not sessions or sessions != sorted(set(sessions)):
        raise ValueError("ORDERED_OBSERVED_SESSIONS_REQUIRED")
    latest = sessions[-1]
    session_set = set(sessions)
    if date.fromisoformat(latest) > today:
        raise ValueError("FUTURE_SAVED_MARKET_SESSION_REJECTED")
    by_key: dict[str, dict[str, dict[str, Any]]] = {}
    for row in frame["rows"]:
        if row["session"] not in session_set:
            raise ValueError("UNQUALIFIED_SAVED_MARKET_SESSION")
        values = [Decimal(str(row[field])) for field in ("open", "high", "low", "close")]
        if any(not value.is_finite() or value <= 0 for value in values):
            raise ValueError("INVALID_SAVED_MARKET_PRICE")
        opened, high, low, close = values
        if low > min(opened, close) or high < max(opened, close) or high < low:
            raise ValueError("INVALID_SAVED_MARKET_OHLC")
        if type(row["volume"]) is not int or row["volume"] < 0:
            raise ValueError("INVALID_SAVED_MARKET_VOLUME")
        received = datetime.fromisoformat(row["received_at"])
        if received.utcoffset() is None or received > at:
            raise ValueError("INVALID_SAVED_MARKET_RECEIPT")
        observations = by_key.setdefault(row["key"], {})
        if row["session"] in observations:
            raise ValueError("DUPLICATE_SAVED_MARKET_SLOT")
        observations[row["session"]] = row
    result = []
    histories = {}
    positions = {session: index for index, session in enumerate(sessions)}
    for identity in frame["identities"]:
        key = identity["provider_key"]
        observations = by_key.get(key, {})
        day = max(observations, default=None)
        row = observations.get(day) if day else None
        previous_day = sessions[positions[day] - 1] if day and positions[day] > 0 else None
        previous = observations.get(previous_day) if previous_day else None
        previous_close = Decimal(str(previous["close"])) if previous else None
        change = Decimal(str(row["close"])) - previous_close if row and previous_close else None
        age = (today - date.fromisoformat(day)).days if day else None
        freshness = (
            "UNAVAILABLE"
            if row is None
            else "STALE"
            if day != latest or (age is not None and age > 7)
            else "DATED_COMPLETED_SESSION"
        )
        result.append(
            {
                "key": key,
                "symbol": identity["symbol"],
                "name": identity.get("name"),
                "session": day,
                "freshness": freshness,
                "age_calendar_days": age,
                "previous_session": previous_day if previous else None,
                "previous_close": str(previous_close) if previous_close is not None else None,
                "change": str(change) if change is not None else None,
                "change_percent": str(change / previous_close * 100)
                if change is not None and previous_close
                else None,
                **{
                    field: row[field] if row else None
                    for field in ("open", "high", "low", "close", "volume")
                },
                "received_at": row["received_at"] if row else None,
                "source": "UPSTOX_OFFICIAL_HISTORICAL_CANDLES",
                "change_basis": "ADJACENT_OBSERVED_COHORT_SESSIONS_NOT_TOTAL_RETURN",
            }
        )
        histories[key] = [
            {
                "session": session,
                **{
                    field: observations.get(session, {}).get(field)
                    for field in ("open", "high", "low", "close", "volume")
                },
            }
            for session in sessions[-120:]
        ]
    return {
        "dataset_id": frame["dataset_id"],
        "as_of": at.isoformat(),
        "latest_observed_session": latest,
        "source_observed_at": frame["source_observed_at"],
        "mode": "SAVED_COMPLETED_SESSION_NOT_LIVE",
        "price_basis": frame["price_basis"],
        "calendar_complete": False,
        "provider_requests": 0,
        "configured_securities": len(result),
        "latest_session_securities": sum(row["session"] == latest for row in result),
        "rows": result,
        "histories": histories,
    }


def listing(view: dict[str, Any], *, q: str, order: str, limit: int) -> dict[str, Any]:
    if order not in {"symbol", "gainers", "losers", "volume"} or not 1 <= limit <= 50:
        raise ValueError("BOUNDED_SAVED_MARKET_VIEW_REQUIRED")
    rows = [
        row
        for row in view["rows"]
        if q.casefold()
        in " ".join(str(row.get(field) or "") for field in ("symbol", "name", "key")).casefold()
    ]
    if order != "symbol":
        rows = [
            row
            for row in rows
            if row["freshness"] == "DATED_COMPLETED_SESSION"
            and (order == "volume" or row["change_percent"] is not None)
        ]
        if order == "volume":
            rows.sort(key=lambda row: (-row["volume"], row["key"]))
        else:
            direction = 1 if order == "losers" else -1
            rows = [row for row in rows if Decimal(row["change_percent"]) * direction < 0]
            rows.sort(key=lambda row: (direction * Decimal(row["change_percent"]), row["key"]))
    else:
        rows.sort(key=lambda row: (row["symbol"], row["key"]))
    return {
        **{
            key: value
            for key, value in view.items()
            if key not in {"rows", "histories", "research_workspace"}
        },
        "order": order,
        "total": len(rows),
        "rows": rows[:limit],
    }


def publish(root: Path, frame: dict[str, Any], *, at: datetime) -> dict[str, Any]:
    """Explicit derived publication after source validation; never called by a GET."""
    from . import engine

    value = project(frame, at=at)
    value["basis"] = "CHECKSUM_VERIFIED_SAVED_SOURCE_PROJECTION_AS_OF_PUBLICATION"
    # New candles do not imply new compatible future-entry forecasts. Keep dated
    # scores alongside contemporaneous coverage without rescanning on every GET.
    scores = (
        engine._pointed(root, "scores-latest.json")
        if (root / "scores-latest.json").is_file()
        else None
    )
    if scores is not None:
        _, _, features = engine._latest_features(frame)
        covered = engine.coverage(root, frame)
        covered.update(
            technical_feature_eligible_securities=sum(
                sample.session == frame["sessions"][-1] for sample in features.samples
            ),
            experimental_scored_securities=len(scores["candidates"]),
            independently_accepted_securities=0,
        )
        value["research_workspace"] = {
            "state": "AVAILABLE",
            "coverage": covered,
            "scores": scores,
            "candidates": scores["candidates"],
            "classification": "EXPERIMENTAL_UNVALIDATED",
            "accepted_current_rankings": 0,
            "score_snapshot_current": scores["dataset_id"] == frame["dataset_id"],
            "current_feature_date": frame["sessions"][-1],
            "technical_exclusions": [
                item
                for item in features.exclusions
                if item["session"] == frame["sessions"][-1] and item["reason"] != "TARGET_UNMATURED"
            ],
            "saved_view_published_at": at.isoformat(),
            "workspace_basis": value["basis"],
        }
    folder = private_path(root, "market-views")
    folder.mkdir(exist_ok=True)
    target = folder / (uuid4().hex + ".json")
    engine._checked(target, value)
    engine._pointer(root, "market-view-latest.json", target)
    return {
        "state": "SAVED_MARKET_VIEW_PUBLISHED",
        "configured_securities": len(value["rows"]),
        "latest_observed_session": value["latest_observed_session"],
        "provider_requests": 0,
    }


def workspace(root: Path) -> dict[str, Any] | None:
    """Read immutable derived evidence as published; never rescan the raw archive."""
    from . import engine

    if not (root / "market-view-latest.json").is_file():
        return None
    value = engine._pointed(root, "market-view-latest.json")
    result: dict[str, Any] | None = value.get("research_workspace")
    if result is None:
        return None
    published = datetime.fromisoformat(value["as_of"])
    if (
        published.utcoffset() is None
        or published > datetime.now(UTC)
        or result["coverage"]["dataset_id"] != value["dataset_id"]
    ):
        raise ValueError("SAVED_WORKSPACE_PUBLICATION_LINEAGE_REJECTED")
    result["operations"] = engine._operations(root)
    return result
