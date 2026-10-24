"""Authenticated saved-candle views. No transport, clock probe or persistence."""

import copy
import threading
import time
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query
from pydantic import JsonValue
from workers.nse_market import discovery, engine, saved_market
from workers.providers import universe

from .core.domain_errors import APIError
from .nse_market import _candidate, _envelope, _roots
from .routes import Research
from .schemas import Envelope

router = APIRouter(prefix="/api/v1/nse-market", tags=["private saved market observations"])
_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_lock = threading.Lock()


def _view(service: Research) -> dict[str, Any]:
    roots = _roots(service)
    if roots is None:
        raise APIError(
            "SAVED_MARKET_NOT_CONFIGURED", "Saved market observations are unavailable.", 503
        )
    root = roots[0]
    pointer = root / "market-view-latest.json"
    if not pointer.is_file():
        raise APIError(
            "SAVED_MARKET_PUBLICATION_PENDING",
            "Publish the verified saved candle view through the offline worker first.",
            503,
        )
    cache_key = str(root.resolve()) + ":" + str(pointer.stat().st_mtime_ns)
    # Ordinary reads verify the immutable projection, without rebuilding all history.
    with _lock:
        saved = _cache.get(cache_key)
        if saved and time.monotonic() - saved[0] < 60:
            return copy.deepcopy(saved[1])
        try:
            value = engine._pointed(root, "market-view-latest.json")
            published = datetime.fromisoformat(value["as_of"])
            if published.utcoffset() is None or published > datetime.now(UTC):
                raise ValueError("INVALID_SAVED_MARKET_PUBLICATION_TIME")
            # Re-evaluate display age without regenerating prices or changes.
            today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date()
            for row in value["rows"]:
                if row["session"] is not None:
                    row["age_calendar_days"] = (
                        today - datetime.fromisoformat(row["session"]).date()
                    ).days
                    if row["age_calendar_days"] > 7:
                        row["freshness"] = "STALE"
        except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
            raise APIError(
                "SAVED_MARKET_EVIDENCE_INVALID", "Saved candle evidence could not be verified.", 503
            ) from None
        # Do not retain caches from arbitrary roots indefinitely.
        _cache.clear()
        _cache[cache_key] = (time.monotonic(), value)
        return copy.deepcopy(value)


@router.get("/saved-market")
def market(
    service: Research,
    q: Annotated[str, Query(max_length=128)] = "",
    order: Literal["symbol", "gainers", "losers", "volume"] = "symbol",
    limit: Annotated[int, Query(ge=1, le=50)] = 25,
) -> Envelope[JsonValue]:
    return _envelope(saved_market.listing(_view(service), q=q, order=order, limit=limit), service)


@router.get("/saved-history")
def history(
    service: Research,
    key: Annotated[str, Query(pattern=r"^NSE_EQ\|INE[A-Z0-9]{9}$")],
) -> Envelope[JsonValue]:
    try:
        view = _view(service)
    except APIError as error:
        if error.code not in {"SAVED_MARKET_NOT_CONFIGURED", "SAVED_MARKET_PUBLICATION_PENDING"}:
            raise
        view = {
            "rows": [],
            "histories": {},
            "mode": "SAVED_COMPLETED_SESSION_NOT_LIVE",
            "latest_observed_session": None,
            "as_of": datetime.now(UTC).isoformat(),
            "price_basis": "NO_SAVED_PRICE_OBSERVATIONS",
            "provider_requests": 0,
            "configured_securities": 0,
            "latest_session_securities": 0,
        }
    row = next((row for row in view["rows"] if row["key"] == key), None)
    if row is None:
        roots = _roots(service)
        try:
            snapshot = universe.load(roots[2]) if roots is not None else None
            identity = (
                discovery.identity_status(snapshot, at=datetime.now(UTC)) if snapshot else None
            )
        except (OSError, ValueError, KeyError, TypeError):
            snapshot, identity = None, None
        record = (
            next((item for item in snapshot.records if item["instrument_key"] == key), None)
            if snapshot
            else None
        )
        if record is None:
            raise APIError(
                "SAVED_SECURITY_UNAVAILABLE",
                "No verified saved identity or history is available.",
                404,
            )
        row = discovery.empty_security(record)
        row["identity_status"] = identity
    workspace = view.get("research_workspace") or {}
    reasons = sorted(
        {item["reason"] for item in workspace.get("technical_exclusions", []) if item["key"] == key}
    )
    predicted = any(item["key"] == key for item in workspace.get("candidates", []))
    row = {
        **row,
        "support_status": row.get("support_status", "SAVED_OBSERVATIONS_AVAILABLE"),
        "ml_status": "DATED_SAVED_PREDICTION_AVAILABLE"
        if predicted
        else "NO_COMPATIBLE_SAVED_PREDICTION",
        "latest_feature_exclusions": reasons,
    }
    return _envelope(
        {
            **{
                name: value
                for name, value in view.items()
                if name not in {"rows", "histories", "research_workspace"}
            },
            "security": row,
            "rows": view["histories"].get(key, []),
            "maximum_observed_slots": 120,
        },
        service,
    )


@router.get("/universe-coverage")
def coverage(service: Research) -> Envelope[JsonValue]:
    roots = _roots(service)
    if roots is None:
        raise APIError("SAVED_MARKET_NOT_CONFIGURED", "Saved universe is unavailable.", 503)
    try:
        snapshot = universe.load(roots[2])
        view = _view(service)
        # Verify every reported model output, not a bounded UI sample.
        for candidate in (view.get("research_workspace") or {}).get("candidates", []):
            _candidate(candidate)
        data = discovery.measure(snapshot, view, at=datetime.now(UTC))
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
        raise APIError(
            "SAVED_UNIVERSE_COVERAGE_INVALID", "Saved universe coverage could not be verified.", 503
        ) from None
    return _envelope(data, service)


@router.get("/identity-history")
def identity_history(
    service: Research,
    key: Annotated[str, Query(pattern=r"^NSE_EQ\|INE[A-Z0-9]{9}$")],
) -> Envelope[JsonValue]:
    roots = _roots(service)
    if roots is None:
        raise APIError(
            "SAVED_MARKET_NOT_CONFIGURED", "Saved identity evidence is unavailable.", 503
        )
    try:
        data = discovery.identity_history(roots[2], key)
    except (OSError, ValueError, KeyError, TypeError):
        raise APIError(
            "SAVED_IDENTITY_HISTORY_INVALID", "Saved identity history could not be verified.", 503
        ) from None
    return _envelope(data, service)
