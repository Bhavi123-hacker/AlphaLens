"""Explicit bounded quote batches; no universe polling or retained observations."""

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alphalens_data.errors import DataContractError

from .store import ProviderStore
from .transient import expire_after
from .upstox import UpstoxClient
from .upstox_terminal import TTL, _lock, _quotes, _snapshots, master, quote, selected

LOCAL_LIMIT = 50
DOCUMENTED_QUOTE_LIMIT = 500


def plan(keys: tuple[str, ...]) -> dict[str, Any]:
    if not 1 <= len(keys) <= LOCAL_LIMIT or len(set(keys)) != len(keys):
        raise DataContractError("ONE_TO_FIFTY_DISTINCT_VERIFIED_EQUITIES_REQUIRED")
    return {
        "selected_count": len(keys),
        "local_limit": LOCAL_LIMIT,
        "documented_quote_batch_limit": DOCUMENTED_QUOTE_LIMIT,
        "quote_batches": 1,
        "maximum_provider_gets": 2,
        "historical_series_requests": 0,
        "full_universe_polling": False,
    }


def cached(root: Path, keys: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    """Never fetch. Consumers must leave missing/expired marks unavailable."""
    now = time.monotonic()
    prefix = str(root.resolve())
    result = {}
    with _lock:
        for key in keys:
            for cache in (_snapshots, _quotes):
                entry = cache.get((prefix, key))
                if entry and now - entry[0] < TTL:
                    result[key] = {
                        **entry[1],
                        "cache_age_seconds": now - entry[0],
                        "cache_ttl_seconds": TTL,
                    }
                    break
    return result


def load(root: Path, keys: tuple[str, ...]) -> dict[str, Any]:
    planning = plan(keys)
    with _lock:
        client = UpstoxClient(ProviderStore(root), budget=2)
        identities = master(root, client, datetime.now(UTC))
        instruments = [selected(identities, key) for key in keys]
        existing = cached(root, keys)
        missing = tuple(key for key in keys if key not in existing)
        if missing:
            reply = client.get("quote", keys=missing)
            stamp = time.monotonic()
            for instrument in instruments:
                if instrument.provider_key not in missing:
                    continue
                item = {
                    "cache_age_seconds": 0,
                    "cache_ttl_seconds": TTL,
                    "instrument_key": instrument.provider_key,
                    "symbol": instrument.symbol,
                    "identity": instrument.model_dump(mode="json"),
                    "quote": quote(reply, instrument),
                    "source": "UPSTOX_FULL_QUOTE_V3",
                    "price_basis": "UNKNOWN",
                    "retained": False,
                    "latest_session": None,
                    "latest_close": None,
                    "rows": [],
                    "indicators": {},
                    "received_at": reply.received_at.isoformat(),
                }
                key = (str(root.resolve()), instrument.provider_key)
                if len(_quotes) >= 500:
                    _quotes.clear()
                _quotes[key] = stamp, item
                expire_after(_quotes, key, stamp, _lock, TTL)
                existing[instrument.provider_key] = item
        return {
            "state": "SELECTED_WATCHLIST_OBSERVATIONS",
            "plan": planning,
            "api_calls_this_request": client.calls,
            "queried_count": len(existing),
            "observed_count": sum(
                x["quote"]["state"] == "VALIDATED_SNAPSHOT" or x.get("latest_close") is not None
                for x in existing.values()
            ),
            "selected_count": len(keys),
            "valid_quote_count": sum(
                x["quote"]["state"] == "VALIDATED_SNAPSHOT" for x in existing.values()
            ),
            "items": [
                {
                    **{
                        field: existing[key].get(field)
                        for field in (
                            "instrument_key",
                            "symbol",
                            "identity",
                            "quote",
                            "source",
                            "latest_session",
                            "latest_close",
                            "change_percent",
                            "cache_age_seconds",
                            "cache_ttl_seconds",
                        )
                    },
                    "daily_volume": existing[key].get("rows", [])[-1].get("volume")
                    if existing[key].get("rows")
                    else None,
                    "technical": {
                        name: feature["points"][-1]["value"] if feature.get("points") else None
                        for name, feature in existing[key].get("indicators", {}).items()
                    },
                }
                for key in keys
            ],
            "retained": False,
            "full_nse_coverage": False,
            "cache_ttl_seconds": TTL,
            "cache_age_seconds": max(
                (item["cache_age_seconds"] for item in existing.values()), default=0
            ),
        }
