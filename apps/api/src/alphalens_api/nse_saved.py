"""Authenticated saved-candle views. No transport, clock probe or persistence."""

import copy
import threading
import time
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query
from pydantic import JsonValue
from workers.nse_market import engine, saved_market

from .core.domain_errors import APIError
from .nse_market import _envelope, _roots
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
    view = _view(service)
    row = next((row for row in view["rows"] if row["key"] == key), None)
    if row is None:
        raise APIError(
            "SAVED_SECURITY_UNAVAILABLE", "This identity has no configured saved history.", 404
        )
    return _envelope(
        {
            **{
                name: value
                for name, value in view.items()
                if name not in {"rows", "histories", "research_workspace"}
            },
            "security": row,
            "rows": view["histories"][key],
            "maximum_observed_slots": 120,
        },
        service,
    )
