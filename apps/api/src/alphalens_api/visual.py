"""Read-only historical descriptive analytics, separate from P11-P14 decisions."""

import threading
import time
from collections import OrderedDict
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any, Literal

import pyarrow.parquet as pq
from fastapi import APIRouter, Query
from pydantic import JsonValue

from .artifacts import confined
from .core.domain_errors import APIError
from .credentials import credential_present
from .projection import date_rows
from .routes import Research, dates
from .schemas import Envelope, IndicatorPoint, Page
from .services import ResearchService, response

router = APIRouter(prefix="/api/v1/visual", tags=["historical visual analytics"])
FEATURES = (
    "return_1",
    "return_5",
    "return_20",
    "return_60",
    "volatility_20",
    "rsi_14",
    "distance_sma_20",
    "drawdown_20",
    "momentum_percentile_20",
    "volume_ratio_20",
)


def snapshot_rows(
    path: Path,
    columns: list[str],
    security: None,
    start: date,
    end: date,
    limit: int,
    offset: int,
    deadline: float,
) -> tuple[list[dict[str, Any]], bool]:
    # Multi-security canonical partitions are not globally ordered by identity.
    # Sort a bounded projection; preserve the older single-security reader contract.
    return date_rows(path, columns, start, end, limit, deadline)


def ratio(value: Decimal, reference: Decimal) -> float | None:
    return float(value / reference - 1) if reference > 0 else None


def describe(points: list[dict[str, Any]]) -> dict[str, Any]:
    """Adjacent slots only; raw-price curves are diagnostics, never economic returns."""
    previous: Decimal | None = None
    peak: Decimal | None = None
    base: Decimal | None = None
    interrupted = False
    curve: list[dict[str, Any]] = []
    returns: list[float] = []
    for point in points:
        close = Decimal(point["close"]) if point["close"] is not None else None
        move = ratio(close, previous) if close is not None and previous is not None else None
        if move is not None:
            returns.append(move)
        if close is not None and base is None:
            base = close
        if close is None:
            interrupted = True
        peak = max(peak, close) if peak is not None and close is not None else close or peak
        curve.append(
            {
                "session": point["session"],
                "return_1": move,
                "drawdown": ratio(close, peak) if close is not None and peak else None,
                "cumulative_return": ratio(close, base)
                if close is not None and base and not interrupted
                else None,
            }
        )
        previous = close
    bins = [0] * 20
    lower = min(returns, default=0.0)
    upper = max(returns, default=0.0)
    width = (upper - lower) / 20 if upper > lower else 0.0
    for value in returns:
        bins[min(19, int((value - lower) / width)) if width else 10] += 1
    valid = [p for p in points if p["close"] is not None]
    last = valid[-1] if valid else None
    highs = [Decimal(p["high"]) for p in points[-252:] if p.get("high") is not None]
    lows = [Decimal(p["low"]) for p in points[-252:] if p.get("low") is not None]
    return {
        "latest": last,
        "curve": curve,
        "distribution": [
            {"lower": lower + i * width, "upper": lower + (i + 1) * width, "count": count}
            for i, count in enumerate(bins)
        ],
        "observed_high": str(max(highs)) if highs else None,
        "observed_low": str(min(lows)) if lows else None,
        "range_slots": min(252, len(points)),
        "missing_slots": len(points) - len(valid),
        "interpretation": "RAW_UNADJUSTED_PRICE_DIAGNOSTICS_NOT_TOTAL_ECONOMIC_RETURNS",
        "calendar_completeness": "OBSERVED_SESSION_CALENDAR_NOT_OFFICIAL_EXCHANGE_CALENDAR",
        "benchmark_correlation": "UNAVAILABLE",
        "risk_level": "UNAVAILABLE",
        "signal_timeline": "UNAVAILABLE",
        "vwap": "UNAVAILABLE_EOD_HAS_NO_INTRADAY_WEIGHTING",
    }


class MarketRead:
    """Four-session bounded cache; source fingerprints checked before every reuse."""

    def __init__(self, service: ResearchService) -> None:
        self.service = service
        self.lock = threading.Lock()
        self.cache: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()

    def snapshot(self, selected: date | None) -> dict[str, Any]:
        reader = self.service.reader
        canonical = reader.manifest("canonical-manifest.json")
        feature = reader.manifest("supervised-manifest.json")
        sessions = [s["session_date"] for s in reader.calendar()["sessions"]]
        observed = [
            s["session_date"]
            for s in reader.calendar()["sessions"]
            if s["price_status"] == "SOURCE_ROWS_PRESENT"
        ]
        if not observed:
            raise APIError("OBSERVATIONS_UNAVAILABLE", "No stored market sessions exist.")
        day = str(selected) if selected else max(observed)
        if day not in observed:
            raise APIError(
                "SESSION_NOT_OBSERVED", "Select a session with stored observations.", 422
            )
        root = reader.settings.research_data_root
        if root is None:
            raise APIError("DATASET_NOT_CONFIGURED", "Historical dataset is not configured.")
        entries = [
            (confined(root, e["path"]), e["sha256"])
            for m in (canonical, feature)
            for e in m["identity"]["files"]
        ]
        fingerprints = tuple(
            (str(p), p.stat().st_size, p.stat().st_mtime_ns, h) for p, h in entries
        )
        key = (day, canonical["dataset_id"], feature["dataset_id"], fingerprints)
        # Prevent duplicate expensive cold reads; do not wait for occupied work.
        if not self.lock.acquire(blocking=False):
            raise APIError("READ_CAPACITY", "Market analytics read is occupied; retry later.", 429)
        try:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            index = sessions.index(day)
            previous = sessions[index - 1] if index else None
            start = date.fromisoformat(sessions[max(0, index - 21)])
            history: dict[str, list[dict[str, Any]]] = {}
            feature_rows: dict[str, dict[str, Any]] = {}
            deadline = time.monotonic() + reader.settings.query_timeout_seconds
            for entry in canonical["identity"]["files"]:
                with reader.budget(wait_seconds=5):
                    path = reader.verify(confined(root, entry["path"]), entry["sha256"], deadline)
                    rows, more = snapshot_rows(
                        path,
                        [
                            "security_id",
                            "session_date",
                            "symbol",
                            "isin",
                            "name",
                            "analytical_type",
                            "close",
                            "volume",
                            "quality",
                            "quality_reasons",
                        ],
                        None,
                        start,
                        date.fromisoformat(day),
                        50000,
                        0,
                        deadline,
                    )
                    if more:
                        raise APIError(
                            "RESPONSE_LIMIT", "Market partition exceeds read budget.", 422
                        )
                    for row in rows:
                        history.setdefault(row["security_id"], []).append(row)
                    if len(history) > 20000:
                        raise APIError(
                            "RESPONSE_LIMIT", "Market coverage exceeds read budget.", 422
                        )
            supported = [f for f in FEATURES if f in feature["identity"]["feature_columns"]]
            for entry in feature["identity"]["files"]:
                with reader.budget(wait_seconds=5):
                    path = reader.verify(confined(root, entry["path"]), entry["sha256"], deadline)
                    rows, more = snapshot_rows(
                        path,
                        [
                            "security_id",
                            "session_date",
                            *supported,
                            *(f + "__state" for f in supported),
                        ],
                        None,
                        date.fromisoformat(day),
                        date.fromisoformat(day),
                        20000,
                        0,
                        deadline,
                    )
                    if more:
                        raise APIError(
                            "RESPONSE_LIMIT", "Feature coverage exceeds read budget.", 422
                        )
                    for row in rows:
                        if row["security_id"] in feature_rows:
                            raise APIError(
                                "IDENTITY_CONFLICT", "Duplicate feature observation.", 409
                            )
                        feature_rows[row["security_id"]] = row
            result = build_market(
                history,
                feature_rows,
                day,
                previous,
                supported,
                sessions[max(0, index - 21) : index + 1],
            )
            result["available_sessions"] = observed
            result["latest_stored_session"] = max(observed)
            self.cache[key] = result
            while len(self.cache) > 4:
                self.cache.popitem(last=False)
            return result
        finally:
            self.lock.release()


def build_market(
    history: dict[str, list[dict[str, Any]]],
    features: dict[str, dict[str, Any]],
    day: str,
    previous: str | None,
    supported: list[str],
    slots: list[str] | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for security, values in history.items():
        by_day = {str(v["session_date"]): v for v in values}
        if len(by_day) != len(values):
            raise APIError("IDENTITY_CONFLICT", "Duplicate canonical market observation.", 409)
        current = by_day.get(day)
        if current is None or current["analytical_type"] != "RESEARCH_EQUITY_CANDIDATE":
            continue
        prior = by_day.get(previous or "")
        comparable = (
            prior is not None
            and current["close"] is not None
            and prior["close"] is not None
            and current["quality"] in {"VALID", "DEGRADED"}
            and prior["quality"] in {"VALID", "DEGRADED"}
        )
        close = current["close"]
        change = Decimal(close) - Decimal(prior["close"]) if comparable and prior else None
        record: dict[str, Any] = {
            "security_id": security,
            "symbol": current["symbol"],
            "name": current["name"],
            "isin": current["isin"],
            "session": day,
            "close": str(close) if close else None,
            "volume": current["volume"],
            "quality": current["quality"],
            "quality_reasons": current["quality_reasons"],
            "change": str(change) if change is not None else None,
            "return_1": ratio(Decimal(close), Decimal(prior["close"]))
            if comparable and prior
            else None,
            "sparkline": [
                {
                    "session": slot,
                    "close": str(by_day[slot]["close"])
                    if slot in by_day
                    and by_day[slot]["close"] is not None
                    and by_day[slot]["quality"] in {"VALID", "DEGRADED"}
                    else None,
                }
                for slot in (slots or sorted(by_day))
            ],
            "inference_eligibility": "UNAVAILABLE",
            "risk_level": "UNAVAILABLE",
        }
        feat = features.get(security, {})
        record["feature_states"] = {f: feat.get(f + "__state", "UNAVAILABLE") for f in supported}
        for f in supported:
            if f != "return_1":
                record[f] = (
                    feat.get(f) if feat.get(f + "__state") in {"AVAILABLE", "DEGRADED"} else None
                )
        rows.append(record)
    rows.sort(key=lambda r: (-abs(r["return_1"] or 0), r["security_id"]))
    valid = [r["return_1"] for r in rows if r["return_1"] is not None]
    return {
        "session": day,
        "previous_observed_calendar_session": previous,
        "rows": rows,
        "coverage": len(rows),
        "comparable": len(valid),
        "uncomparable": len(rows) - len(valid),
        "advancing": sum(v > 0 for v in valid),
        "declining": sum(v < 0 for v in valid),
        "unchanged": sum(v == 0 for v in valid),
        "mean_raw_return": sum(valid) / len(valid) if valid else None,
        "sector_mapping": "UNAVAILABLE",
        "index_cohort": "UNAVAILABLE",
        "market_cap": "UNAVAILABLE",
        "new_52_week_highs_lows": "UNAVAILABLE_FULL_UNIVERSE_LOOKBACK",
        "interpretation": "DESCRIPTIVE_HISTORICAL_COHORT_NOT_CURRENT_RECOMMENDATIONS",
        "coverage_semantics": "OBSERVED_RESEARCH_EQUITY_CANDIDATES_NOT_COMPLETE_NSE_UNIVERSE",
    }


@router.get("/market")
def market(
    service: Research,
    session: date | None = None,
    limit: int = Query(500, ge=1, le=500),
    offset: int = Query(0, ge=0, le=20000),
) -> Envelope[JsonValue]:
    result = service.visual_market.snapshot(session)
    rows = result["rows"]
    return service.response(
        {**result, "rows": rows[offset : offset + limit]},
        "CHECKSUM_VERIFIED_P5_P6_HISTORICAL_DESCRIPTIVE_ANALYTICS",
        as_of=date.fromisoformat(result["session"]),
        page=Page(limit=limit, offset=offset, total=len(rows), has_more=offset + limit < len(rows)),
    )


@router.get("/stocks/{security_id}/statistics")
def statistics(
    security_id: str, service: Research, start: date | None = None, end: date | None = None
) -> Envelope[JsonValue]:
    dates(start, end)
    identity = service.catalog.security(security_id)
    last = end or date.fromisoformat(identity["last_observed"])
    first = start or last - timedelta(days=366)
    history = service.history(security_id, first, last, 10000, 0)
    if history.page and history.page.has_more:
        raise APIError("RESPONSE_LIMIT", "Narrow the statistics interval.", 422)
    return service.response(
        describe([p.model_dump(mode="json") for p in history.data]),
        "P5_RAW_PRICE_DESCRIPTIVE_ANALYTICS",
        as_of=history.as_of_session,
    )


@router.get("/stocks/{security_id}/bands")
def bands(
    security_id: str,
    service: Research,
    start: date | None = None,
    end: date | None = None,
    side: Literal["upper", "lower"] = "upper",
    limit: int = Query(500, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
) -> Envelope[JsonValue]:
    dates(start, end)
    mean = service.indicators(security_id, "sma_20", start, end, limit, offset)
    width = service.indicators(security_id, "bollinger_width_20", start, end, limit, offset)
    if not isinstance(mean.data, dict) or not isinstance(width.data, dict):
        raise APIError("ARTIFACT_INVALID", "Band inputs are invalid.")
    mean_points = (
        [IndicatorPoint.model_validate(p) for p in mean.data["points"]]
        if isinstance(mean.data["points"], list)
        else []
    )
    width_points = (
        [IndicatorPoint.model_validate(p) for p in width.data["points"]]
        if isinstance(width.data["points"], list)
        else []
    )
    means = {p.session: p for p in mean_points}
    points = []
    for point in width_points:
        center = means.get(point.session)
        value = None
        if center and center.value is not None and point.value is not None:
            value = center.value * (1 + (1 if side == "upper" else -1) * point.value / 2)
        item = point.model_dump(mode="json")
        points.append(
            {**item, "value": value, "state": point.state if value is not None else "UNAVAILABLE"}
        )
    return service.response(
        {
            "feature": {
                "feature_name": "bollinger_" + side + "_20",
                "formula": "Stored P6 SMA20 +/- 2 sample stdev, reconstructed from width20",
                "registry": "p6.features.v1",
                "derived_view_only": True,
            },
            "units": "INR_RAW_PRICE",
            "points": points,
        },
        "P6_STORED_BAND_INPUTS",
        page=mean.page,
    )


@router.get("/backtests/{backtest_id}/trades")
def backtest_trades(
    backtest_id: str,
    service: Research,
    limit: int = Query(500, ge=1, le=500),
    offset: int = Query(0, ge=0, le=10000),
) -> Envelope[JsonValue]:
    # Resolve the audited ID first; caller paths never become filesystem paths.
    service.backtests(backtest_id, None, None, 1, 0)
    run = next(
        r
        for r in service.reader.report("backtesting/real-research-economic-audit.json")["runs"]
        if r["backtest_id"] == backtest_id
    )
    root = service.reader.settings.research_run_root
    if root is None:
        raise APIError("ARTIFACTS_NOT_CONFIGURED", "Research artifacts are not configured.")
    rows = []
    seen = 0
    more = False
    with service.reader.budget() as deadline:
        path = service.reader.verify(
            confined(root, f"p10/{backtest_id}/trades.parquet"),
            run["stored_evidence_sha256"]["trades.parquet"],
            deadline,
        )
        for batch in pq.ParquetFile(path).iter_batches(batch_size=512):
            if time.monotonic() > deadline:
                raise APIError("QUERY_TIMEOUT", "Trade diagnostics exceeded read budget.", 504)
            for row in batch.to_pylist():
                if seen >= offset:
                    rows.append(row)
                seen += 1
                if len(rows) > limit:
                    more = True
                    break
            if more:
                break
    rows = rows[:limit]
    returns = [float(Fraction(str(r["net_return"]))) for r in rows if r["net_return"] is not None]
    counts = {
        "positive": sum(v > 0 for v in returns),
        "negative": sum(v < 0 for v in returns),
        "flat": sum(v == 0 for v in returns),
        "unresolved": len(rows) - len(returns),
    }
    lower, upper = min(returns, default=0), max(returns, default=0)
    width = (upper - lower) / 15 if upper > lower else 0
    bins = [0] * 15
    for value in returns:
        bins[min(14, int((value - lower) / width)) if width else 7] += 1
    return service.response(
        {
            "trades": rows,
            "counts": counts,
            "distribution": [
                {"lower": lower + i * width, "upper": lower + (i + 1) * width, "count": n}
                for i, n in enumerate(bins)
            ],
            "scope": "BOUNDED_PAGE_CLOSED_TRADE_DIAGNOSTICS_NOT_FULL_STRATEGY_ECONOMICS",
        },
        "CHECKSUM_VERIFIED_P10_STORED_TRADES",
        backtest_id,
        page=Page(limit=limit, offset=offset, has_more=more),
    )


@router.get("/providers")
def providers(service: Research) -> Envelope[JsonValue]:
    return response(
        {
            "mode": "DISABLED",
            "acquisition_enabled": False,
            "providers": [
                {
                    "name": name,
                    "configured": credential_present()
                    if name == "Alpha Vantage" and service.reader.settings.environment != "test"
                    else False,
                    "account_status": "NSE_COVERAGE_NOT_VERIFIED"
                    if name == "Alpha Vantage"
                    else "NOT_CONFIGURED",
                    "rights_status": "NOT_CLEARED",
                    "state": "BLOCKED_BY_POLICY",
                }
                for name in ("Alpha Vantage", "Upstox", "Groww")
            ],
            "capabilities": {
                key: {"state": "UNAVAILABLE", "reason": reason}
                for key, reason in {
                    "quote": "NO_APPROVED_LIVE_PROVIDER",
                    "ltp": "NO_APPROVED_LIVE_PROVIDER",
                    "ohlc": "HISTORICAL_API_ONLY_NO_LIVE_ADAPTER",
                    "market_status": "NO_VERIFIED_LIVE_CALENDAR",
                    "instrument_lookup": "HISTORICAL_IDENTITIES_ONLY",
                    "market_depth": "NO_LEVEL_2_EVIDENCE",
                    "option_chain": "NO_DERIVATIVES_EVIDENCE",
                    "open_interest": "NO_DERIVATIVES_EVIDENCE",
                    "greeks": "NO_VERIFIED_OPTION_INPUTS",
                    "intraday": "EOD_ARCHIVE_ONLY",
                }.items()
            },
            "configuration_policy": "OPERATOR_PRIVATE_CONFIG_ONLY_NO_CREDENTIALS_IN_API_OR_GIT",
        },
        "DISABLED_FUTURE_PROVIDER_CAPABILITY_CONTRACT",
    )
