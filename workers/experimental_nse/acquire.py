"""Bounded official historical capture for a separate private fixed-cohort study."""

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from workers.providers.daily_clock import guard
from workers.providers.store import ProviderStore
from workers.providers.upstox import Reply, UpstoxClient, instrument_master

from alphalens_api.auth.permissions import restrict, verify
from alphalens_data.errors import DataContractError
from alphalens_data.providers.multi_adapters import parse_daily
from alphalens_data.providers.multi_contracts import Instrument

FAMILY = "ALPHALENS_EXPERIMENTAL_NSE_V1"
PERMISSION = "UPSTOX_OFFICIAL_PRIVATE_RESEARCH_REPLY_17302_POST3_2026_09_01_AND_ANALYTICS_TOKEN"
COHORT = (
    "RELIANCE",
    "TCS",
    "INFY",
    "HCLTECH",
    "WIPRO",
    "TECHM",
    "HDFCBANK",
    "ICICIBANK",
    "SBIN",
    "KOTAKBANK",
    "AXISBANK",
    "ITC",
    "HINDUNILVR",
    "NESTLEIND",
    "BRITANNIA",
    "MARUTI",
    "M&M",
    "BAJAJ-AUTO",
    "SUNPHARMA",
    "CIPLA",
    "DRREDDY",
    "LT",
    "ULTRACEMCO",
    "GRASIM",
    "NTPC",
    "POWERGRID",
    "ONGC",
    "TATASTEEL",
    "HINDALCO",
    "BHARTIARTL",
)
START, END = date(2022, 1, 1), date(2026, 10, 15)


def encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def write_new(path: Path, body: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(body)
    if __import__("os").name != "nt":
        path.chmod(0o600)


def private_path(root: Path, *parts: str) -> Path:
    """Reject symlink traversal even when a checksum-pinned filename is harmless."""
    if root.is_symlink():
        raise DataContractError("EXPERIMENTAL_SYMLINK_PATH_REJECTED")
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink() or not current.resolve().is_relative_to(root.resolve()):
            raise DataContractError("EXPERIMENTAL_SYMLINK_PATH_REJECTED")
    return current


def initialize(root: Path) -> None:
    private_path(root)
    if root.exists():
        verify(root)
        return
    root.mkdir(parents=True)
    restrict(root)


def capture(root: Path, provider_root: Path, *, permission_reference: str) -> dict[str, Any]:
    """Explicit operator CLI only; no API or scheduled acquisition entry point."""
    if permission_reference != PERMISSION:
        raise DataContractError("EXPERIMENTAL_PRIVATE_SOURCE_PERMISSION_REQUIRED")
    initialize(root)
    snapshot = private_path(root, "snapshot-v1")
    if snapshot.exists():
        return replay(root)
    clock = guard()
    if date.fromisoformat(clock["session_date"]) <= END:
        raise DataContractError("EXPERIMENTAL_COMPLETED_PRIOR_DATE_REQUIRED")
    snapshot.mkdir()
    client = UpstoxClient(ProviderStore(provider_root), budget=31, retries=0)
    master_reply = client.get("instruments")
    instruments, master_meta = instrument_master(master_reply, require_reliance=False)
    write_new(snapshot / "master.json.gz", master_reply.body)
    selections: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for symbol in COHORT:
        identities = [i for i in instruments if i.symbol == symbol]
        if len(identities) != 1:
            failures.append({"symbol": symbol, "reason": "EXACT_CURRENT_IDENTITY_NOT_UNIQUE"})
            continue
        identity = identities[0]
        reply = client.get("candles", key=identity.provider_key, start=START, end=END)
        if reply.state != "ACCEPTED":
            failures.append({"symbol": symbol, "reason": reply.state, "status": reply.status})
            if reply.status in {401, 403, 429}:
                break
            continue
        candles = parse_daily(reply.body, identity, reply.received_at)
        if not candles or any(not START <= c.session <= END for c in candles):
            failures.append({"symbol": symbol, "reason": "EMPTY_OR_OUTSIDE_REQUEST_WINDOW"})
            continue
        # The request is bound to exact NSE key; Upstox daily responses do not echo identity.
        filename = identity.isin + ".json" if identity.isin else "invalid.json"
        write_new(snapshot / filename, reply.body)
        selections.append(
            {
                "identity": identity.model_dump(mode="json"),
                "filename": filename,
                "sha256": digest(reply.body),
                "received_at": reply.received_at.isoformat(),
                "server_at": reply.server_at.isoformat() if reply.server_at else None,
                "observations": len(candles),
                "start": str(candles[0].session),
                "end": str(candles[-1].session),
            }
        )
    manifest = {
        "schema": "alphalens.experimental_nse.dataset.v1",
        "family": FAMILY,
        "permission_reference": permission_reference,
        "clock": clock,
        "selection_policy": "PREDECLARED_DIVERSE_CURRENT_FIXED_COHORT_NOT_HISTORICAL_UNIVERSE",
        "requested_symbols": list(COHORT),
        "start": str(START),
        "end": str(END),
        "source": "OFFICIAL_UPSTOX_V3_HISTORICAL_DAILY",
        "price_basis": "UNKNOWN",
        "corporate_action_coverage": "UNKNOWN_NO_OVERNIGHT_RETURN_FEATURES_OR_LABELS",
        "historical_availability": "UNKNOWN_FINAL_VINTAGE_RETROSPECTIVE",
        "master": master_meta,
        "master_received_at": master_reply.received_at.isoformat(),
        "instruments": selections,
        "exclusions": failures,
        "api_calls": client.calls,
        "raw_payloads_private": True,
        "scheduled_acquisition_enabled": False,
    }
    write_new(snapshot / "manifest.json", encoded(manifest))
    return replay(root)


def replay(root: Path) -> dict[str, Any]:
    """Reparse immutable original bodies with original receipt times, no transport."""
    verify(root)
    manifest_path = private_path(root, "snapshot-v1", "manifest.json")
    if not manifest_path.is_file():
        raise DataContractError("EXPERIMENTAL_INCOMPLETE_CAPTURE_REQUIRES_REVIEW_NO_REQUESTS")
    manifest_body = manifest_path.read_bytes()
    manifest = json.loads(manifest_body)
    if manifest["family"] != FAMILY or manifest["permission_reference"] != PERMISSION:
        raise DataContractError("EXPERIMENTAL_MANIFEST_SCOPE_REJECTED")
    master_path = private_path(root, "snapshot-v1", "master.json.gz")
    if digest(master_path.read_bytes()) != manifest["master"]["master_sha256"]:
        raise DataContractError("EXPERIMENTAL_MASTER_CHECKSUM_REJECTED")
    identities, _ = instrument_master(
        Reply(
            200,
            master_path.read_bytes(),
            datetime.fromisoformat(manifest["master_received_at"]),
            "ACCEPTED",
        ),
        require_reliance=False,
    )
    rows: list[dict[str, Any]] = []
    for entry in manifest["instruments"]:
        identity = Instrument.model_validate(entry["identity"])
        if identity not in identities or identity.symbol not in COHORT:
            raise DataContractError("EXPERIMENTAL_IDENTITY_REJECTED")
        if identity.isin is None or entry["filename"] != identity.isin + ".json":
            raise DataContractError("EXPERIMENTAL_PAYLOAD_PATH_REJECTED")
        body = private_path(root, "snapshot-v1", entry["filename"]).read_bytes()
        if digest(body) != entry["sha256"]:
            raise DataContractError("EXPERIMENTAL_CANDLE_CHECKSUM_REJECTED")
        received = datetime.fromisoformat(entry["received_at"])
        candles = parse_daily(body, identity, received)
        if len(candles) != entry["observations"]:
            raise DataContractError("EXPERIMENTAL_OBSERVATION_COUNT_REJECTED")
        for candle in candles:
            if not START <= candle.session <= END:
                raise DataContractError("EXPERIMENTAL_SESSION_OUTSIDE_SCOPE")
            rows.append(
                {
                    "key": identity.provider_key,
                    "symbol": identity.symbol,
                    "isin": identity.isin,
                    "name": identity.name,
                    "session": str(candle.session),
                    "open": str(candle.open),
                    "high": str(candle.high),
                    "low": str(candle.low),
                    "close": str(candle.close),
                    "volume": candle.volume,
                    "received_at": received.isoformat(),
                    "raw_sha256": entry["sha256"],
                    "provider_candle_at": candle.event_time.isoformat(),
                }
            )
    rows.sort(key=lambda r: (r["key"], r["session"]))
    sessions = sorted({r["session"] for r in rows})
    result = {
        "dataset_id": digest(manifest_body),
        "manifest": manifest,
        "rows": rows,
        "sessions": sessions,
        "replay_api_calls": 0,
        "source_observed_at": max(
            (e["received_at"] for e in manifest["instruments"]), default=None
        ),
    }
    normalized = encoded(result)
    normalized_path = private_path(root, "snapshot-v1", "normalized.json")
    if normalized_path.exists():
        if normalized_path.read_bytes() != normalized:
            raise DataContractError("EXPERIMENTAL_REPLAY_CHANGED")
    else:
        write_new(normalized_path, normalized)
    return result
