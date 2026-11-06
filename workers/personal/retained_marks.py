"""Source-qualified dated private EOD marks for indicative portfolio research only."""

import copy
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from workers.experimental_nse_v2 import data

_lock = threading.Lock()
_cache: dict[str, tuple[float, Any, dict[str, dict[str, Any]]]] = {}
TTL_SECONDS = 60


def _fingerprint(root: Path) -> tuple[Any, ...]:
    if root.is_symlink():
        raise ValueError("PRIVATE_EOD_MARK_SYMLINK_REJECTED")
    watched = {
        "dataset.json",
        "dataset.sha256",
        "current.json",
        "current.sha256",
        "current-latest.json",
    }
    entries = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if (
            relative.parts[0] not in {"raw", "current-raw", "base-v1", "captures"}
            and str(relative) not in watched
        ):
            continue
        if path.is_symlink():
            raise ValueError("PRIVATE_EOD_MARK_SYMLINK_REJECTED")
        if path.is_file():
            stat = path.stat()
            entries.append((str(relative), stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size))
    return tuple(sorted(entries))


def read(root: Path | None, keys: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    if root is None or not keys:
        return {}
    # Only source-verified dated EOD marks enter this expiring private cache.
    # No uncertain quotes, ML inputs, accepted valuations or alert services use it.
    fingerprint = (
        _fingerprint(root),
        datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date(),
    )
    identity = str(root.resolve())
    with _lock:
        existing = _cache.get(identity)
        if (
            existing
            and 0 <= time.monotonic() - existing[0] < TTL_SECONDS
            and existing[1] == fingerprint
        ):
            marks = existing[2]
        else:
            marks = _read(root)
            if len(_cache) >= 4 and identity not in _cache:
                _cache.pop(next(iter(_cache)))
            _cache[identity] = (time.monotonic(), fingerprint, marks)
        age = max(0.0, time.monotonic() - _cache[identity][0])
        return {
            key: {
                **copy.deepcopy(marks[key]),
                "cache_ttl_seconds": TTL_SECONDS,
                "cache_age_seconds": age,
            }
            for key in keys
            if key in marks
        }


def _read(root: Path) -> dict[str, dict[str, Any]]:
    dataset = data.load_current(root)  # Replays source hashes, identity, dates and values.
    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date()
    identities = {i["provider_key"]: i for i in dataset["identities"]}
    latest = dataset["sessions"][-1]
    day = datetime.fromisoformat(latest).date()
    if day > today or (today - day).days > 7:
        return {}
    result = {}
    for row in dataset["rows"]:
        key = row["key"]
        if row["session"] != latest:
            continue
        identity = identities.get(key)
        if (
            identity is None
            or key != "NSE_EQ|" + row["isin"]
            or row["isin"] != identity["isin"]
            or row["symbol"] != identity["symbol"]
            or latest in dataset["quality"]["excluded_sessions"].get(key, [])
        ):
            continue
        result[key] = {
            "instrument_key": key,
            "symbol": row["symbol"],
            "quote": {"state": "NO_INTRADAY_QUOTE_USED"},
            "latest_close": row["close"],
            "latest_session": latest,
            "source": "UPSTOX_PRIVATE_RETAINED_DAILY_CANDLE",
            "price_basis": data.BASIS,
            "source_observed_at": row["received_at"],
            "raw_sha256": row["raw_sha256"],
            "dataset_id": dataset["dataset_id"],
            "mark_basis": "RETAINED_ADJUSTED_EOD_INDICATIVE_UNRECONCILED_ACTIONS",
            "rows": [],  # No raw-price technical or volume contract is implied.
            "cache_ttl_seconds": 0,
            "financial_accepted_valuation": False,
        }
    return result
