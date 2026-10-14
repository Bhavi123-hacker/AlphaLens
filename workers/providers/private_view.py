"""One-instrument private transient dashboard; no retained prices or ML promotion."""

import hashlib
import json
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from alphalens_api.auth.permissions import verify
from alphalens_data.providers.multi_adapters import parse_daily
from alphalens_data.providers.multi_contracts import Instrument
from alphalens_features.research import numerical
from workers.daily.features import definitions

from .store import ProviderStore
from .upstox import KEY, UpstoxClient

_lock = threading.Lock()
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def view(
    root: Path, *, now: datetime | None = None, model_root: Path | None = None
) -> dict[str, Any]:
    verify(root)
    at = now or datetime.now(UTC)
    if at.tzinfo is None:
        raise ValueError("AWARE_PRIVATE_VIEW_REQUIRED")
    cache_key = str(root.resolve()) + str(model_root)
    with _lock:
        cached = _cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < 600:
            return cached[1]
        paths = sorted(root.glob("master-identity-*.json"))
        if not paths or paths[-1].stat().st_size > 8192:
            raise ValueError("CURRENT_MASTER_IDENTITY_REQUIRED")
        instrument = Instrument.model_validate_json(paths[-1].read_bytes())
        if (
            instrument.provider_key != KEY
            or instrument.symbol != "RELIANCE"
            or instrument.observed_at > at
        ):
            raise ValueError("CURRENT_RELIANCE_IDENTITY_REQUIRED")
        today = at.astimezone(ZoneInfo("Asia/Kolkata")).date()
        client = UpstoxClient(ProviderStore(root), budget=1)
        reply = client.get(
            "candles", start=today - timedelta(days=1827), end=today - timedelta(days=1)
        )
        if reply.state != "ACCEPTED":
            return {"state": reply.state, "rows": [], "indicators": {}, "retained": False}
        candles = parse_daily(reply.body, instrument, reply.received_at)
        if any(c.session >= today or c.session < today - timedelta(days=1827) for c in candles):
            raise ValueError("PRIVATE_VIEW_SESSION_SCOPE_REJECTED")
        # P6 formulas over provider-observed slots, descriptive only. Unknown calendar
        # gaps and action/basis evidence preclude model-ready features.
        arrays = {
            name: np.array([float(getattr(c, name)) for c in candles])
            for name in ("close", "high", "low", "volume")
        }
        indicators = {}
        selected = {"sma_20", "sma_50", "sma_200", "rsi_14", "macd_histogram", "atr_14"}
        for definition in definitions(today, at):
            if definition.feature_name not in selected:
                continue
            values = numerical(
                definition, arrays["close"], arrays["high"], arrays["low"], arrays["volume"]
            )
            indicators[definition.feature_name] = {
                "feature_name": definition.feature_name,
                "units": "INR"
                if definition.feature_name.startswith(("sma_", "macd_", "atr_"))
                else "index",
                "points": [
                    {"session": str(c.session), "value": float(v) if np.isfinite(v) else None}
                    for c, v in zip(candles, values, strict=True)
                ],
            }
        latest, prior = (
            (candles[-1] if candles else None),
            (candles[-2] if len(candles) > 1 else None),
        )
        change = latest.close - prior.close if latest and prior else None
        result = {
            "state": "AVAILABLE_PRIVATE_TRANSIENT",
            "instrument_key": KEY,
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "source": "UPSTOX_HISTORICAL_CANDLE_V3",
            "price_basis": "UNKNOWN",
            "latest_session": str(latest.session) if latest else None,
            "latest_close": str(latest.close) if latest else None,
            "change": str(change) if change is not None else None,
            "change_percent": str(change / prior.close * 100)
            if change is not None and prior
            else None,
            "received_at": reply.received_at.isoformat(),
            "retained": False,
            "scope": "ONE_INSTRUMENT_PROVIDER_OBSERVED_SLOTS_NOT_FULL_NSE",
            "official_final_close": "NOT_INDEPENDENTLY_ESTABLISHED",
            "calendar": "OBSERVED_CANDLE_DATES_NOT_AUTHORITATIVE_SESSION_CALENDAR",
            "indicators_scope": "DESCRIPTIVE_PROVIDER_SLOTS_NOT_MODEL_READY",
            "rows": [
                {
                    "session": str(c.session),
                    "open": str(c.open),
                    "high": str(c.high),
                    "low": str(c.low),
                    "close": str(c.close),
                    "volume": c.volume,
                    "quality": "DEGRADED_BASIS_ACTION_CALENDAR_UNVERIFIED",
                    "observation_status": "PROVIDER_DAILY_CANDLE",
                }
                for c in candles
            ],
            "indicators": indicators,
            "passport": {
                "identity_source": instrument.identity_evidence,
                "master_revision": instrument.revision_sha256,
                "response_checksum": candles[0].raw_sha256 if candles else None,
                "retrieval_time": reply.received_at.isoformat(),
                "publication_time": None,
                "historical_archive_joined": False,
                "current_inference": "UNAVAILABLE",
                "blockers": [
                    "PRICE_BASIS_UNKNOWN",
                    "CORPORATE_ACTIONS_UNAVAILABLE",
                    "COMPLETE_PEER_UNIVERSE_UNAVAILABLE",
                    "MODEL_ACCEPTANCE_NOT_PASSED",
                    "RETAINED_ML_DATA_USE_NOT_CLEARED",
                ],
            },
        }
        if model_root is not None:
            report_bytes = (model_root / "2026-results.json").read_bytes()
            if (
                hashlib.sha256(report_bytes).hexdigest()
                != "9243ec7c9a5a08808c0ffbb6dfa04dd20b5732707659cb2836c896b204876e42"
            ):
                raise ValueError("FROZEN_MODEL_REPORT_MISMATCH")
            reports = json.loads(report_bytes)["reports"]
            columns = reports[0]["model_identity"]["feature_columns"]
            if len(columns) != 38 or any(
                r["model_identity"]["feature_columns"] != columns for r in reports
            ):
                raise ValueError("FROZEN_FEATURE_ORDER_MISMATCH")
            registry = {d.feature_name: d for d in definitions(today, at)}
            readiness = []
            for column in columns:
                finite = False
                if column in registry and column != "momentum_percentile_20" and candles:
                    derived = numerical(
                        registry[column],
                        arrays["close"],
                        arrays["high"],
                        arrays["low"],
                        arrays["volume"],
                    )
                    finite = bool(np.isfinite(derived[-1]))
                readiness.append(
                    {
                        "column": column,
                        "descriptive_value_available": finite,
                        "model_eligible": False,
                        "exclusion": "COMPLETE_CONTEMPORANEOUS_PEER_SCOPE_MISSING"
                        if column == "momentum_percentile_20"
                        else "BASIS_ACTION_CALENDAR_AND_ML_USE_UNVERIFIED",
                    }
                )
            result["feature_readiness"] = {
                "ordered_required_columns": columns,
                "required_count": 38,
                "descriptive_available_count": sum(
                    r["descriptive_value_available"] for r in readiness
                ),
                "model_eligible_count": 0,
                "features": readiness,
                "accepted_models": [],
                "prospective_forecasts": 0,
                "top5": "UNAVAILABLE",
                "top10": "UNAVAILABLE",
                "top20": "UNAVAILABLE",
            }
        if len(_cache) >= 8:
            _cache.clear()
        _cache[cache_key] = (time.monotonic(), result)
        return result
