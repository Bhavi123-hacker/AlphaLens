"""Explicit private NSE observations. Bounded GETs, memory only, no archive join.

Current master identity is separate from historical identity. Quote timestamps must
not exceed local receipt; HTTP Date evidence diagnoses skew, never excuses it.
"""

import re
import threading
import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from alphalens_api.auth.permissions import verify
from alphalens_data.errors import DataContractError
from alphalens_data.providers.multi_adapters import decoded, parse_daily
from alphalens_data.providers.multi_contracts import Instrument
from alphalens_features.research import numerical
from workers.daily.features import definitions

from .calendar import nse_timing
from .search_index import InstrumentIndex
from .store import ProviderStore
from .transient import expire_after
from .upstox import Reply, UpstoxClient, instrument_master

IST = ZoneInfo("Asia/Kolkata")
TTL = 600
_lock = threading.RLock()
_masters: dict[str, tuple[float, tuple[Instrument, ...]]] = {}
_timings: dict[tuple[str, date], tuple[float, dict[str, Any]]] = {}
_snapshots: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
_indices: dict[str, tuple[str, InstrumentIndex]] = {}
_quotes: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}


def clock_evidence(reply: Reply) -> dict[str, Any]:
    return {
        "local_received_at": reply.received_at.isoformat(),
        "https_server_date": reply.server_at.isoformat() if reply.server_at else None,
        "server_minus_local_seconds": round(
            (reply.server_at - reply.received_at).total_seconds(), 6
        )
        if reply.server_at
        else None,
        "http_date_precision": "ONE_SECOND_NOT_INDEPENDENT_NTP",
        "validation": "NO_FUTURE_TIMESTAMP_TOLERANCE",
        "system_clock_synchronization": "NOT_ESTABLISHED_BY_HTTP",
    }


def master(root: Path, client: UpstoxClient, at: datetime) -> tuple[Instrument, ...]:
    verify(root)
    cache_key = str(root.resolve())
    cached = _masters.get(cache_key)
    if cached and time.monotonic() - cached[0] < TTL:
        if any(i.observed_at > at for i in cached[1]):
            raise DataContractError("FUTURE_CURRENT_MASTER_REJECTED")
        return cached[1]
    reply = client.get("instruments")
    instruments, _ = instrument_master(reply, require_reliance=False)
    if len(_masters) >= 8:
        _masters.clear()
    _masters[cache_key] = time.monotonic(), instruments
    return instruments


def selected(instruments: tuple[Instrument, ...], key: str) -> Instrument:
    if not re.fullmatch(r"NSE_EQ\|[A-Z0-9]{12}", key):
        raise DataContractError("VERIFIED_NSE_EQ_IDENTITY_REQUIRED")
    matches = [i for i in instruments if i.provider_key == key]
    if len(matches) != 1:
        raise DataContractError("CURRENT_MASTER_IDENTITY_MISSING_OR_AMBIGUOUS")
    instrument = matches[0]
    if instrument.instrument_type != "EQ" or instrument.exchange != "NSE":
        raise DataContractError("CURRENT_NSE_EQUITY_REQUIRED")
    return instrument


def resolve(instruments: tuple[Instrument, ...], aliases: list[dict[str, Any]]) -> Instrument:
    """Require the latest contemporaneous ISIN AND symbol, never a name match."""
    if not aliases:
        raise DataContractError("CANONICAL_IDENTITY_UNAVAILABLE")
    latest = max(str(a["last_observed"]) for a in aliases)
    dated = [a for a in aliases if str(a["last_observed"]) == latest]
    identities = {(a.get("isin"), a.get("symbol")) for a in dated}
    if len(identities) != 1:
        raise DataContractError("CANONICAL_IDENTITY_AMBIGUOUS")
    isin, symbol = next(iter(identities))
    if not isin or not symbol:
        raise DataContractError("CANONICAL_ISIN_AND_SYMBOL_REQUIRED")
    instrument = selected(instruments, "NSE_EQ|" + str(isin))
    if instrument.symbol != symbol:
        raise DataContractError(
            "CURRENT_AND_ARCHIVE_IDENTITY_DIFFER_CURRENT_MASTER_SELECTION_REQUIRED"
        )
    return instrument


def search(
    root: Path, query: str, *, at: datetime | None = None, limit: int = 20, offset: int = 0
) -> dict[str, Any]:
    if not 1 <= limit <= 100 or not 0 <= offset <= 10000:
        raise DataContractError("CURRENT_MASTER_PAGE_BOUND_REQUIRED")
    with _lock:
        now = at or datetime.now(UTC)
        instruments = master(root, UpstoxClient(ProviderStore(root), budget=1), now)
        revision = (
            instruments[0].revision_sha256 + instruments[0].observed_at.isoformat()
            if instruments
            else "empty"
        )
        cache_key = str(root.resolve())
        indexed = _indices.get(cache_key)
        if not indexed or indexed[0] != revision:
            if len(_indices) >= 8:
                _indices.clear()
            indexed = revision, InstrumentIndex(instruments)
            _indices[cache_key] = indexed
        matches, total = indexed[1].search(query, limit, offset)
        return {
            "state": "VERIFIED_CURRENT_MASTER",
            "source": "UPSTOX_CURRENT_BOD_INSTRUMENT_JSON",
            "observed_at": instruments[0].observed_at.isoformat() if instruments else None,
            "candidate_count": len(instruments),
            "matched_count": total,
            "instruments": [i.model_dump(mode="json") for i in matches],
            "page": {"limit": limit, "offset": offset, "has_more": offset + limit < total},
            "sector_classification": "UNAVAILABLE_NOT_IN_CURRENT_IDENTITY_MASTER",
            "scope": "CURRENT_NSE_EQ_TYPE_EQ_NOT_HISTORICAL_COMMON_EQUITY_UNIVERSE",
            "market_prices_requested": False,
        }


def price(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise DataContractError("QUOTE_PRICE_INVALID")
    try:
        number = Decimal(value)
        if not number.is_finite() or number <= 0 or number > Decimal("1e12"):
            raise ValueError
        return number
    except (ValueError, InvalidOperation):
        raise DataContractError("QUOTE_PRICE_INVALID") from None


def epoch(value: Any) -> datetime:
    if isinstance(value, bool) or not re.fullmatch(r"\d{13}", str(value)):
        raise DataContractError("QUOTE_EPOCH_MILLISECONDS_INVALID")
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=int(value))


def entry(reply: Reply, instrument: Instrument) -> dict[str, Any]:
    payload = decoded(reply.body)
    values = payload.get("data")
    if payload.get("status") != "success" or not isinstance(values, dict):
        raise DataContractError("QUOTE_SCHEMA_REJECTED")
    # Full/OHLC V3 maps by exchange:symbol, not by ISIN. Verify the token inside.
    value = values.get("NSE_EQ:" + instrument.symbol)
    if not isinstance(value, dict) or value.get("instrument_token") != instrument.provider_key:
        raise DataContractError("QUOTE_IDENTITY_REJECTED")
    return value


def quote(reply: Reply, instrument: Instrument) -> dict[str, Any]:
    result: dict[str, Any] = {
        "state": reply.state,
        "clock": clock_evidence(reply),
        "is_final_eod_close": False,
    }
    if reply.state != "ACCEPTED":
        return result
    try:
        value = entry(reply, instrument)
        if value.get("symbol") != instrument.symbol:
            raise DataContractError("QUOTE_SYMBOL_REJECTED")
        stamp = datetime.fromisoformat(value["timestamp"])
        trade_at = epoch(value["last_trade_time"])
        if stamp.tzinfo is None or stamp > reply.received_at or trade_at > stamp:
            result["state"] = "QUOTE_TIME_REJECTED"
            result["reported_snapshot_at"] = stamp.isoformat()
            result["reported_last_trade_at"] = trade_at.isoformat()
            result["clock"]["quote_minus_local_seconds"] = (
                round((stamp - reply.received_at).total_seconds(), 6) if stamp.tzinfo else None
            )
            return result
        ltp = price(value["last_price"])
        previous = price(value["prev_close_price"]) if value.get("prev_close_price") else None
        change = ltp - previous if previous is not None else None
        result.update(
            {
                "state": "VALIDATED_SNAPSHOT",
                "snapshot_at": stamp.isoformat(),
                "last_trade_at": trade_at.isoformat(),
                "ltp": str(ltp),
                "previous_close": str(previous) if previous is not None else None,
                "change": str(change) if change is not None else None,
                "change_percent": str(change / previous * 100)
                if change is not None and previous is not None
                else None,
                "change_basis": "LTP_MINUS_UPSTOX_V3_PREV_CLOSE_PRICE",
                "freshness": "SAME_LOCAL_DATE_TRADE"
                if trade_at.astimezone(IST).date() == reply.received_at.astimezone(IST).date()
                else "OLDER_TRADE",
                "snapshot_age_seconds_at_receipt": (reply.received_at - stamp).total_seconds(),
                "volume": value.get("volume")
                if type(value.get("volume")) is int and value["volume"] >= 0
                else None,
            }
        )
    except (ValueError, TypeError, KeyError, OverflowError):
        result["state"] = "QUOTE_SCHEMA_OR_VALUE_REJECTED"
    return result


def ohlc(reply: Reply, instrument: Instrument) -> dict[str, Any]:
    result: dict[str, Any] = {
        "state": reply.state,
        "interval": "1d",
        "current": None,
        "previous": None,
    }
    if reply.state != "ACCEPTED":
        return result
    try:
        value = entry(reply, instrument)
        for target, name in (("current", "live_ohlc"), ("previous", "prev_ohlc")):
            row = value.get(name)
            if row is None:
                continue
            stamp = epoch(row["ts"])
            if stamp > reply.received_at:
                raise DataContractError("OHLC_FUTURE_TIMESTAMP_REJECTED")
            prices = {k: price(row[k]) for k in ("open", "high", "low", "close")}
            if (
                not prices["low"]
                <= min(prices["open"], prices["close"])
                <= max(prices["open"], prices["close"])
                <= prices["high"]
            ):
                raise DataContractError("OHLC_RANGE_REJECTED")
            volume = row["volume"]
            if isinstance(volume, bool) or not isinstance(volume, int) or volume < 0:
                raise DataContractError("OHLC_VOLUME_REJECTED")
            result[target] = {
                **{k: str(v) for k, v in prices.items()},
                "volume": volume,
                "start_at": stamp.isoformat(),
                "session": str(stamp.astimezone(IST).date()),
            }
        if (
            result["current"]
            and result["previous"]
            and (result["previous"]["session"] >= result["current"]["session"])
        ):
            raise DataContractError("OHLC_SESSION_ORDER_REJECTED")
        result["state"] = "VALIDATED_PROVIDER_OHLC"
    except (ValueError, TypeError, KeyError, OverflowError):
        result.update(state="OHLC_SCHEMA_OR_TIME_REJECTED", current=None, previous=None)
    return result


def market(root: Path, client: UpstoxClient, now: datetime) -> dict[str, Any]:
    today = now.astimezone(IST).date()
    key = str(root.resolve()), today
    cached = _timings.get(key)
    if cached and time.monotonic() - cached[0] < TTL:
        result = dict(cached[1])
    else:
        reply = client.get("timings", end=today)
        try:
            result = nse_timing(reply, today)
        except (ValueError, KeyError, TypeError):
            result = {"state": "SESSION_STATUS_UNAVAILABLE", "session": str(today)}
        _timings[key] = time.monotonic(), result
    if "start" in result:
        start, end = (datetime.fromisoformat(result[k]) for k in ("start", "end"))
        result["state"] = "OPEN" if start <= now < end else "CLOSED" if now >= end else "PRE_OPEN"
    return result


def snapshot(
    root: Path,
    *,
    keys: tuple[str, ...] = (),
    aliases: list[dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Up to three selected equities. Shared quote/OHLC, one candle GET per equity."""
    at = now or datetime.now(UTC)
    if at.tzinfo is None or (aliases is None and not 1 <= len(keys) <= 3):
        raise DataContractError("BOUNDED_AWARE_PRIVATE_SNAPSHOT_REQUIRED")
    if aliases is None and (
        len(set(keys)) != len(keys)
        or any(not re.fullmatch(r"NSE_EQ\|[A-Z0-9]{12}", key) for key in keys)
    ):
        raise DataContractError("VERIFIED_UNIQUE_NSE_EQ_SELECTION_REQUIRED")
    with _lock:
        client = UpstoxClient(ProviderStore(root), budget=7)
        instruments = master(root, client, at)
        chosen = (
            (resolve(instruments, aliases),)
            if aliases is not None
            else tuple(selected(instruments, key) for key in keys)
        )
        if len({i.provider_key for i in chosen}) != len(chosen):
            raise DataContractError("DUPLICATE_PRIVATE_COHORT_REJECTED")
        root_key = str(root.resolve())
        pending = [
            i
            for i in chosen
            if not (cached := _snapshots.get((root_key, i.provider_key)))
            or time.monotonic() - cached[0] >= TTL
        ]
        if pending:
            current = datetime.now(UTC) if now is None else at
            timing = market(root, client, current)
            quote_reply = client.get("quote", keys=tuple(i.provider_key for i in pending))
            # Stop after credential/permission/quota rejection; no speculative retries.
            stop = quote_reply.state in {
                "AUTH_REJECTED",
                "PERMISSION_OR_SEGMENT_REJECTED",
                "RATE_LIMITED",
            }
            ohlc_reply = (
                Reply(0, b"", current, "NOT_REQUESTED_AFTER_PROVIDER_REJECTION")
                if stop
                else client.get("ohlc", keys=tuple(i.provider_key for i in pending))
            )
            for instrument in pending:
                item = build(instrument, timing, quote_reply, ohlc_reply, client, stop, current)
                if len(_snapshots) >= 24:
                    _snapshots.clear()
                _snapshots[(root_key, instrument.provider_key)] = time.monotonic(), item
                expire_after(
                    _snapshots,
                    (root_key, instrument.provider_key),
                    _snapshots[(root_key, instrument.provider_key)][0],
                    _lock,
                    TTL,
                )
        # Return copied envelopes; cache age is observed each read, never fixed at zero.
        items = []
        for instrument in chosen:
            stored_at, item = _snapshots[(root_key, instrument.provider_key)]
            if datetime.fromisoformat(item["received_at"]) > at and now is not None:
                raise DataContractError("CACHED_SNAPSHOT_CLOCK_REGRESSION_REJECTED")
            items.append(
                {
                    **item,
                    "cache_age_seconds": round(time.monotonic() - stored_at, 2),
                    "cache_ttl_seconds": TTL,
                    "streaming": False,
                }
            )
        if len(items) > 1:
            # A selected-cohort summary uses a bounded comparison window. Single
            # stock requests retain the full five-year in-memory chart window.
            items = [
                {
                    **item,
                    "rows": item["rows"][-120:],
                    "indicators": {
                        name: {**values, "points": values["points"][-200:]}
                        for name, values in item["indicators"].items()
                    },
                    "chart_window": "LAST_120_PROVIDER_OBSERVATIONS_COHORT_SUMMARY",
                }
                for item in items
            ]
        return {
            "state": "SELECTED_PRIVATE_WATCHLIST",
            "items": items,
            "queried_count": len(items),
            "full_nse_coverage": False,
            "retained": False,
            "api_calls_this_request": client.calls,
        }


def build(
    instrument: Instrument,
    timing: dict[str, Any],
    quote_reply: Reply,
    ohlc_reply: Reply,
    client: UpstoxClient,
    stop: bool,
    current: datetime,
) -> dict[str, Any]:
    today = current.astimezone(IST).date()
    end = today if timing.get("state") == "CLOSED" else today - timedelta(days=1)
    begin = today - timedelta(days=1827)
    reply = (
        Reply(0, b"", current, "NOT_REQUESTED_AFTER_PROVIDER_REJECTION")
        if stop
        else client.get("candles", key=instrument.provider_key, start=begin, end=end)
    )
    candles = (
        parse_daily(reply.body, instrument, reply.received_at) if reply.state == "ACCEPTED" else ()
    )
    if any(c.session < begin or c.session > end for c in candles):
        raise DataContractError("PRIVATE_CANDLE_SCOPE_REJECTED")
    arrays = {
        k: np.array([float(getattr(c, k)) for c in candles])
        for k in ("close", "high", "low", "volume")
    }
    indicators = {}
    names = {
        "sma_20",
        "sma_50",
        "sma_100",
        "sma_200",
        "ema_12",
        "ema_26",
        "rsi_14",
        "macd_histogram",
        "macd",
        "macd_signal",
        "atr_14",
        "volatility_20",
        "return_5",
        "return_20",
        "return_60",
        "drawdown_20",
        "volume_ratio_20",
        "distance_sma_20",
    }
    for definition in definitions(today, reply.received_at):
        name = definition.feature_name
        if name not in names or not candles:
            continue
        values = numerical(
            definition, arrays["close"], arrays["high"], arrays["low"], arrays["volume"]
        )
        indicators[name] = {
            "units": "index"
            if name in {"rsi_14", "volume_ratio_20"}
            else "fraction"
            if name.startswith(("return_", "volatility_", "drawdown_", "distance_"))
            else "INR",
            "points": [
                {"session": str(c.session), "value": float(v) if np.isfinite(v) else None}
                for c, v in zip(candles, values, strict=True)
            ],
        }
    if candles:
        registry = {d.feature_name: d for d in definitions(today, reply.received_at)}
        means = numerical(
            registry["sma_20"], arrays["close"], arrays["high"], arrays["low"], arrays["volume"]
        )
        widths = numerical(
            registry["bollinger_width_20"],
            arrays["close"],
            arrays["high"],
            arrays["low"],
            arrays["volume"],
        )
        for side, sign in (("upper", 1), ("lower", -1)):
            values = means + sign * widths * means / 2
            indicators[f"bollinger_{side}_20"] = {
                "units": "INR",
                "points": [
                    {"session": str(c.session), "value": float(v) if np.isfinite(v) else None}
                    for c, v in zip(candles, values, strict=True)
                ],
            }
    latest = candles[-1] if candles else None
    prior = candles[-2] if len(candles) > 1 else None
    delta = latest.close - prior.close if latest and prior else None
    q = quote(quote_reply, instrument)
    sessions = ohlc(ohlc_reply, instrument)
    return {
        "state": "AVAILABLE_PRIVATE_TRANSIENT"
        if candles
        else "NO_PROVIDER_CANDLES"
        if reply.state == "ACCEPTED"
        else reply.state,
        "identity": instrument.model_dump(mode="json"),
        "instrument_key": instrument.provider_key,
        "symbol": instrument.symbol,
        "source": "UPSTOX_HISTORICAL_CANDLE_V3",
        "exchange": "NSE",
        "segment": "NSE_EQ",
        "price_basis": "UNKNOWN",
        "retained": False,
        "received_at": reply.received_at.isoformat(),
        "latest_session": str(latest.session) if latest else None,
        "latest_close": str(latest.close) if latest else None,
        "change": str(delta) if delta is not None else None,
        "change_percent": str(delta / prior.close * 100) if delta is not None and prior else None,
        "change_basis": "LATEST_PROVIDER_DAILY_CANDLE_MINUS_PREVIOUS_RETURNED_CANDLE",
        "quote": q,
        "session_ohlc": sessions,
        "market": timing,
        "current_session_status": "MARKET_CLOSED_EOD_CANDLE_PENDING"
        if timing.get("state") == "CLOSED" and (not latest or latest.session < today)
        else "PROVIDER_EOD_CANDLE_AVAILABLE"
        if latest and latest.session == today
        else "CURRENT_SESSION_EOD_NOT_AVAILABLE",
        "official_final_close": "NOT_INDEPENDENTLY_ESTABLISHED",
        "calendar": "OBSERVED_CANDLE_DATES_MISSING_EXCHANGE_SESSIONS_UNVERIFIED",
        "rows": [
            {
                "session": str(c.session),
                **{k: str(getattr(c, k)) for k in ("open", "high", "low", "close")},
                "volume": c.volume,
            }
            for c in candles
        ],
        "indicators": indicators,
        "passport": {
            "identity_source": instrument.identity_evidence,
            "master_revision": instrument.revision_sha256,
            "retrieval_time": reply.received_at.isoformat(),
            "publication_time": None,
            "historical_archive_joined": False,
            "current_inference": "UNAVAILABLE",
            "blockers": [
                "PRICE_BASIS_UNKNOWN",
                "CORPORATE_ACTIONS_UNAVAILABLE",
                "MISSING_SESSIONS_UNVERIFIED",
                "RETAINED_ML_DATA_USE_NOT_CLEARED",
                "MODEL_ACCEPTANCE_NOT_PASSED",
            ],
        },
    }
