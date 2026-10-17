"""Source-qualified dated private EOD marks for indicative portfolio research only."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from workers.experimental_nse_v2 import data


def read(root: Path | None, keys: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    if root is None or not keys:
        return {}
    dataset = data.load_current(root)  # Replays source hashes, identity, dates and values.
    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Kolkata")).date()
    identities = {i["provider_key"]: i for i in dataset["identities"]}
    latest = dataset["sessions"][-1]
    day = datetime.fromisoformat(latest).date()
    if day > today or (today - day).days > 7:
        return {}
    requested = set(keys)
    result = {}
    for row in dataset["rows"]:
        key = row["key"]
        if key not in requested or row["session"] != latest:
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
