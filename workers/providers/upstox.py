"""Bounded backend-only Upstox GET transport using the existing P28 quota ledger.

No orders/account APIs, arbitrary URLs, redirects, payload logging or automatic
collection activation. Returned market bodies stay in memory unless a separate
usage contract explicitly permits storage.
"""

import gzip
import hashlib
import io
import json
import re
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from http.client import HTTPSConnection
from pathlib import Path
from socket import gaierror
from ssl import SSLError
from typing import Any, Literal
from urllib.parse import quote

from alphalens_data.errors import DataContractError
from alphalens_data.providers.multi_adapters import parse_daily, upstox_instruments
from alphalens_data.providers.multi_contracts import Instrument

from .credentials import load_token, token_metadata
from .quote_clock import Calibration, precise_utc, recent
from .store import ProviderStore

MASTER_HOST = "assets.upstox.com"
MASTER_PATH = "/market-quote/instruments/exchange/NSE.json.gz"
KEY = "NSE_EQ|INE002A01018"
Operation = Literal[
    "instruments", "candles", "quote", "ohlc", "holidays", "timings", "profile", "ratios", "actions"
]


@dataclass(frozen=True)
class Reply:
    status: int
    body: bytes
    received_at: datetime
    state: str
    error_code: str | None = None
    server_at: datetime | None = None
    clock_required: bool = False
    calibration: Calibration | None = None
    received_monotonic: float | None = None
    capture_span: float = 0.0
    precise_received_at: datetime | None = None


class UpstoxClient:
    def __init__(
        self,
        store: ProviderStore,
        *,
        budget: int = 4,
        retries: int = 0,
        calibrate_quotes: bool = False,
    ) -> None:
        if not 1 <= budget <= 100 or not 0 <= retries <= 2:
            raise DataContractError("BOUNDED_UPSTOX_BUDGET_REQUIRED")
        self.store = store
        self.budget = budget
        self.retries = retries
        self.calls = 0
        self.calibrate_quotes = calibrate_quotes

    def get(
        self,
        operation: Operation,
        *,
        key: str = KEY,
        start: date | None = None,
        end: date | None = None,
        keys: tuple[str, ...] | None = None,
    ) -> Reply:
        selected = keys or (key,)
        if keys is not None and (
            operation not in {"quote", "ohlc"}
            or not 1 <= len(keys) <= (500 if operation == "quote" else 50)
            or len(set(keys)) != len(keys)
        ):
            raise DataContractError("BOUNDED_QUOTE_COHORT_REQUIRED")
        if any(not re.fullmatch(r"NSE_EQ\|[A-Z0-9]{12}", k) for k in selected):
            raise DataContractError("EXACT_NSE_EQ_KEY_REQUIRED")
        if not re.fullmatch(r"NSE_EQ\|[A-Z0-9]{12}", key):
            raise DataContractError("EXACT_NSE_EQ_KEY_REQUIRED")
        host = "api.upstox.com"
        if operation == "instruments":
            host, path = MASTER_HOST, MASTER_PATH
        elif operation == "candles":
            if start is None or end is None or start > end or (end - start).days > 3650:
                raise DataContractError("UPSTOX_DATE_SCOPE_INVALID")
            path = f"/v3/historical-candle/{quote(key, safe='')}/days/1/{end}/{start}"
        elif operation == "quote":
            path = f"/v3/market-quote/quotes?instrument_key={quote(','.join(selected), safe='')}"
        elif operation == "ohlc":
            path = (
                f"/v3/market-quote/ohlc?instrument_key={quote(','.join(selected), safe='')}"
                "&interval=1d"
            )
        elif operation == "holidays":
            path = "/v2/market/holidays"
        elif operation in {"profile", "ratios", "actions"}:
            suffix = {"profile": "profile", "ratios": "key-ratios", "actions": "corporate-actions"}[
                operation
            ]
            path = f"/v2/fundamentals/{key.split('|')[1]}/{suffix}"
        elif operation == "timings":
            if end is None:
                raise DataContractError("UPSTOX_TIMINGS_DATE_REQUIRED")
            path = f"/v2/market/timings/{end}"
        else:
            raise DataContractError("UPSTOX_ENDPOINT_NOT_ALLOWED")
        clock_required = operation == "quote" and self.calibrate_quotes
        calibration = recent() if clock_required else None
        if clock_required and calibration is None:
            return Reply(
                0, b"", datetime.now(UTC), "CLOCK_CALIBRATION_UNAVAILABLE", clock_required=True
            )
        secret = load_token() if operation != "instruments" else None
        headers = {"Accept": "application/json", "User-Agent": "AlphaLens-local-research"}
        if secret:
            headers["Authorization"] = "Bearer " + secret
        request_id = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
        reply = Reply(0, b"", datetime.now(UTC), "NOT_REQUESTED")
        for attempt in range(1, self.retries + 2):
            if self.calls >= self.budget:
                raise DataContractError("UPSTOX_RUN_BUDGET_EXHAUSTED")
            self.store.reserve("upstox", request_id, attempt, time.time())
            self.calls += 1
            connection = HTTPSConnection(host, timeout=60 if operation == "instruments" else 15)
            status = 0
            retry_after: int | None = None
            try:
                if operation == "instruments":
                    # Official static mechanism, no credential/header on CDN or proxy.
                    connection.request("GET", path, headers=headers)
                    response = connection.getresponse()
                    status = response.status
                    body = response.read(20_000_001)
                    limit = 20_000_000
                else:
                    connection.request("GET", path, headers=headers)
                    response = connection.getresponse()
                    status = response.status
                    retry_header = response.getheader("Retry-After", "")
                    if retry_header.isdecimal():
                        retry_after = int(retry_header)
                    limit = 2_000_000
                    body = response.read(limit + 1)
                state = (
                    "RESPONSE_LIMIT"
                    if len(body) > limit
                    else "AUTH_REJECTED"
                    if status == 401
                    else "PERMISSION_OR_SEGMENT_REJECTED"
                    if status == 403
                    else "RATE_LIMITED"
                    if status == 429
                    else "PROVIDER_OUTAGE"
                    if status >= 500
                    else "REDIRECT_REJECTED"
                    if 300 <= status < 400
                    else "ACCEPTED"
                    if status == 200
                    else "REQUEST_REJECTED"
                )
                if secret and secret.encode() in body:
                    state = "UNSAFE_PROVIDER_ECHO_REJECTED"
                capture_start = time.perf_counter()
                received_at = datetime.now(UTC)
                precise_received_at = precise_utc() if clock_required else received_at
                received_monotonic = time.perf_counter()
                server_at = None
                try:
                    server_at = parsedate_to_datetime(response.getheader("Date", ""))
                    if server_at.tzinfo is None:
                        server_at = None
                except (ValueError, TypeError, AttributeError):
                    pass
                reply = Reply(
                    status,
                    body if state == "ACCEPTED" else b"",
                    received_at,
                    state,
                    server_at=server_at,
                    clock_required=clock_required,
                    calibration=calibration,
                    received_monotonic=received_monotonic,
                    capture_span=received_monotonic - capture_start,
                    precise_received_at=precise_received_at,
                )
            except (TimeoutError, gaierror, SSLError) as exc:
                state = (
                    "NETWORK_TIMEOUT"
                    if isinstance(exc, TimeoutError)
                    else ("DNS_UNAVAILABLE" if isinstance(exc, gaierror) else "TLS_REJECTED")
                )
                reply = Reply(0, b"", datetime.now(UTC), state)
            except Exception:
                # Never expose exception arguments, request headers or response messages.
                reply = Reply(0, b"", datetime.now(UTC), "NETWORK_UNAVAILABLE")
            finally:
                connection.close()
                self.store.finish("upstox", request_id, attempt, time.time(), status, retry_after)
            if reply.state not in {
                "NETWORK_UNAVAILABLE",
                "NETWORK_TIMEOUT",
                "DNS_UNAVAILABLE",
                "PROVIDER_OUTAGE",
                "RATE_LIMITED",
            }:
                break
            if attempt <= self.retries:
                # Respect longer server deadlines by stopping; never truncate Retry-After.
                delay = max(2**attempt, retry_after or 0)
                if delay > 30:
                    break
                time.sleep(delay)
        return reply


def instrument_master(
    reply: Reply, *, require_reliance: bool = True
) -> tuple[tuple[Instrument, ...], dict[str, Any]]:
    if reply.state != "ACCEPTED":
        raise DataContractError("UPSTOX_MASTER_UNAVAILABLE")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(reply.body)) as stream:
            native = stream.read(128_000_001)
        if len(native) > 128_000_000:
            raise ValueError
        data = json.loads(native)
        if not isinstance(data, list) or len(data) > 500000:
            raise ValueError
        selected = [
            r
            for r in data
            if isinstance(r, dict)
            and r.get("segment") == "NSE_EQ"
            and r.get("exchange") == "NSE"
            and r.get("instrument_type") == "EQ"
        ]
        sha = hashlib.sha256(reply.body).hexdigest()
        instruments = tuple(
            i.model_copy(update={"revision_sha256": sha})
            for i in upstox_instruments(json.dumps(selected).encode(), reply.received_at)
        )
        reliance = [i for i in instruments if i.provider_key == KEY]
        matching = [r for r in selected if r.get("instrument_key") == KEY]
        reliance_verified = (
            len(reliance) == 1 and reliance[0].symbol == "RELIANCE" and len(matching) == 1
        )
        if require_reliance and not reliance_verified:
            raise ValueError
        return instruments, {
            "nse_eq_type_eq_candidates": len(instruments),
            "eligible_historical_common_equities": None,
            "eligibility": "CURRENT_MASTER_CANDIDATES_NOT_HISTORICAL_UNIVERSE",
            "reliance_identity_verified": reliance_verified,
            "security_type_supplied": bool(matching)
            and isinstance(matching[0].get("security_type"), str),
            "master_sha256": sha,
        }
    except (ValueError, TypeError, OSError, KeyError):
        raise DataContractError("UPSTOX_MASTER_REJECTED") from None


def probe(root: Path) -> dict[str, Any]:
    store = ProviderStore(root)
    if not root.exists():
        store.initialize()
    client = UpstoxClient(store, budget=3)
    receipt: dict[str, Any] = {
        "schema": "p30.upstox.validation.v1",
        "credential_readback": True,
        "token": token_metadata(load_token()),
        "requested_instruments": 1,
        "instrument_key": KEY,
        "exchange": "NSE",
        "segment": "NSE_EQ",
        "requests": [],
        "market_payloads_retained": False,
        "collection_enabled": False,
        "scheduler_enabled": False,
        "ml_inference": "BLOCKED_INDEPENDENT_EVIDENCE",
        "orders": "UNSUPPORTED",
    }
    instruments: tuple[Instrument, ...] = ()
    master = client.get("instruments")
    receipt["requests"].append(
        {
            "operation": "instruments",
            "http_status": master.status,
            "state": master.state,
            "received_at": master.received_at.isoformat(),
        }
    )
    if master.state == "ACCEPTED":
        instruments, summary = instrument_master(master)
        receipt.update(summary)
    today = datetime.now(UTC).astimezone(__import__("zoneinfo").ZoneInfo("Asia/Kolkata")).date()
    candle = client.get("candles", start=today - timedelta(days=14), end=today - timedelta(days=1))
    receipt["requests"].append(
        {
            "operation": "candles",
            "http_status": candle.status,
            "state": candle.state,
            "received_at": candle.received_at.isoformat(),
        }
    )
    receipt["authentication"] = "ACCEPTED" if candle.state == "ACCEPTED" else candle.state
    if candle.state == "ACCEPTED" and instruments:
        identity = next(i for i in instruments if i.provider_key == KEY)
        rows = parse_daily(candle.body, identity, candle.received_at)
        receipt.update(
            {
                "valid_candles": len(rows),
                "sessions": [str(r.session) for r in rows],
                "latest_provider_daily_session": str(rows[-1].session) if rows else None,
                "ohlcv_schema": "VALIDATED_DECIMAL_RANGE_INTEGER_VOLUME",
                "timezone": "Asia/Kolkata",
                "price_basis": "UNKNOWN",
                "publication_time": "NOT_SUPPLIED",
                "official_final_close": "NOT_ESTABLISHED",
                "candle_response_sha256": hashlib.sha256(candle.body).hexdigest(),
            }
        )
    if candle.status not in {401, 403, 429}:
        quote_reply = client.get("quote")
        entry: dict[str, Any] = {
            "operation": "quote",
            "http_status": quote_reply.status,
            "state": quote_reply.state,
            "received_at": quote_reply.received_at.isoformat(),
        }
        if quote_reply.state == "ACCEPTED":
            data = json.loads(quote_reply.body)
            values = list(data.get("data", {}).values())
            if (
                data.get("status") != "success"
                or len(values) != 1
                or values[0].get("instrument_token") != KEY
            ):
                entry["state"] = "QUOTE_IDENTITY_OR_SCHEMA_REJECTED"
            else:
                stamp = datetime.fromisoformat(values[0]["timestamp"])
                if stamp.tzinfo is None or stamp > quote_reply.received_at:
                    entry["state"] = "QUOTE_TIME_REJECTED"
                else:
                    entry["snapshot_at"] = stamp.isoformat()
                    entry["is_final_eod_close"] = False
        receipt["requests"].append(entry)
    receipt["api_calls"] = client.calls
    receipt["verified_at"] = datetime.now(UTC).isoformat()
    # Only sanitized receipt is retained. No raw provider bodies or prices here.
    with (root / ("validation-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f") + ".json")).open(
        "x", encoding="utf-8"
    ) as stream:
        json.dump(receipt, stream, indent=2)
    return receipt


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(probe(args.root), indent=2))
        return 0
    except Exception:
        print(json.dumps({"state": "UPSTOX_VALIDATION_BLOCKED", "sensitive_output": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
