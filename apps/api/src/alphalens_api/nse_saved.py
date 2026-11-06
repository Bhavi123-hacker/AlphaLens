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


def _history_view(service: Research, key: str) -> dict[str, Any]:
    """Copy only the requested security from the already verified display cache.

    Copying every security's 120-slot history for each detail page is needlessly
    expensive for an exhaustive catalog. The publication pointer and the same
    sixty-second checksum-verification lifetime still bound this read path.
    """
    roots = _roots(service)
    selected_root = roots[0] if roots else None
    pointer = selected_root / "market-view-latest.json" if selected_root else None
    cached = None
    if pointer is not None and selected_root is not None and pointer.is_file():
        cache_key = str(selected_root.resolve()) + ":" + str(pointer.stat().st_mtime_ns)
        with _lock:
            saved = _cache.get(cache_key)
            if saved and time.monotonic() - saved[0] < 60:
                cached = saved[1]
    value = cached if cached is not None else _view(service)
    workspace = value.get("research_workspace") or {}
    return copy.deepcopy(
        {
            **{
                name: item
                for name, item in value.items()
                if name not in {"rows", "histories", "research_workspace"}
            },
            "rows": [row for row in value["rows"] if row["key"] == key],
            "histories": {key: value["histories"].get(key, [])},
            "research_workspace": {
                "score_snapshot_current": workspace.get("score_snapshot_current"),
                "candidates": [row for row in workspace.get("candidates", []) if row["key"] == key],
                "technical_exclusions": [
                    row for row in workspace.get("technical_exclusions", []) if row["key"] == key
                ],
            },
        }
    )


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
    key: Annotated[str, Query(pattern=r"^(NSE|BSE)_EQ\|[A-Z0-9]{12}$")],
) -> Envelope[JsonValue]:
    try:
        view = _history_view(service, key)
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
    roots = _roots(service)
    try:
        snapshot = discovery.load_catalog(roots[2]) if roots is not None else None
        identity = discovery.identity_status(snapshot, at=datetime.now(UTC)) if snapshot else None
    except (OSError, ValueError, KeyError, TypeError):
        snapshot, identity = None, None
    matches = (
        [item for item in snapshot.records if item["instrument_key"] == key] if snapshot else []
    )
    if row is None:
        if not matches:
            raise APIError(
                "SAVED_SECURITY_UNAVAILABLE",
                "No verified saved identity or history is available.",
                404,
            )
        row = discovery.empty_security(matches[0])
        row["identity_status"] = identity
    # Current dated aliases never replace the captured aliases of saved prices
    # or forecasts. Only one exact verified provider key can supply this metadata.
    current_identity = None
    if snapshot is None:
        current_identity_status = "CURRENT_MASTER_CATALOG_UNAVAILABLE"
    elif not matches:
        current_identity_status = "CURRENT_MASTER_IDENTITY_NOT_FOUND"
    elif len(matches) != 1 or str(matches[0].get("classification", "")).startswith(
        "DUPLICATE_OR_AMBIGUOUS"
    ):
        current_identity_status = "CURRENT_MASTER_IDENTITY_AMBIGUOUS"
    elif not all(
        isinstance(matches[0].get(field), str) and matches[0][field].strip()
        for field in ("symbol", "name", "exchange")
    ) or not (matches[0].get("source_date") is None or isinstance(matches[0]["source_date"], str)):
        current_identity_status = "CURRENT_MASTER_IDENTITY_FIELDS_UNAVAILABLE"
    else:
        current_identity = {
            field: matches[0].get(field) for field in ("symbol", "name", "exchange", "source_date")
        }
        current_identity["snapshot_id"] = snapshot.snapshot_id
        current_identity_status = "CURRENT_MASTER_IDENTITY_AVAILABLE"
    workspace = view.get("research_workspace") or {}
    reasons = sorted(
        {item["reason"] for item in workspace.get("technical_exclusions", []) if item["key"] == key}
    )
    candidate = next((item for item in workspace.get("candidates", []) if item["key"] == key), None)
    predicted = candidate is not None
    if key.startswith("BSE_EQ|") and predicted:
        raise APIError(
            "MODEL_SEGMENT_MISMATCH", "NSE model predictions cannot be used for BSE.", 503
        )
    saved_prediction = None
    if candidate is not None:
        try:
            verified = _candidate(
                candidate, latest_snapshot=workspace.get("score_snapshot_current") is True
            )
        except (ValueError, KeyError, TypeError, ArithmeticError):
            raise APIError(
                "SAVED_STOCK_PREDICTION_INVALID",
                "Saved stock prediction could not be verified.",
                503,
            ) from None
        saved_prediction = {
            name: verified[name]
            for name in (
                "score",
                "model_id",
                "session",
                "inference_at",
                "data_freshness",
                "score_status",
                "prospective_entry_eligible",
                "forward_outcome_status",
                "independent_acceptance_status",
            )
        }
        saved_prediction.update(
            horizon_sessions=5,
            classification="EXPERIMENTAL_RESEARCH",
            matches_latest_retained_session=verified["session"] == view["latest_observed_session"],
            forecast_created_by_this_request=False,
            calibrated_probability=None,
        )
    candles = view["histories"].get(key, [])
    row = {
        **row,
        "current_identity": current_identity,
        "current_identity_status": current_identity_status,
        "support_status": row.get("support_status", "SAVED_OBSERVATIONS_AVAILABLE"),
        "availability_state": "AVAILABLE_WITH_EXPERIMENTAL_FORECAST"
        if predicted
        else "AVAILABLE_WITH_HISTORY"
        if row.get("close") is not None
        else row.get("availability_state", "HISTORY_NOT_COLLECTED"),
        "ml_status": "MODEL_NOT_VALIDATED_FOR_THIS_SEGMENT"
        if key.startswith("BSE_EQ|")
        else "DATED_SAVED_PREDICTION_AVAILABLE"
        if predicted
        else "NO_COMPATIBLE_SAVED_PREDICTION",
        "latest_feature_exclusions": reasons,
        "descriptive_risk": discovery.descriptive_risk(candles, reasons),
        "saved_prediction": saved_prediction,
        "research_status": "EXPERIMENTAL_RESEARCH",
        "data_status": "MODEL_INCOMPATIBLE"
        if key.startswith("BSE_EQ|") or row.get("support_status") == "UNSUPPORTED_INSTRUMENT"
        else "INSUFFICIENT_DATA"
        if not predicted
        else "COMPATIBLE_SAVED_MODEL_INPUTS",
        "independent_acceptance_status": "INDEPENDENT_ACCEPTANCE_PENDING",
    }
    return _envelope(
        {
            **{
                name: value
                for name, value in view.items()
                if name not in {"rows", "histories", "research_workspace"}
            },
            "security": row,
            "rows": candles,
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
        snapshot = discovery.load_catalog(roots[2])
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
    key: Annotated[str, Query(pattern=r"^(NSE|BSE)_EQ\|[A-Z0-9]{12}$")],
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
