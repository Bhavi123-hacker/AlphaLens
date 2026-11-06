"""Explicit bounded incremental research capture; never schedules or trains.

The previous independently bounded IST date is a query boundary, not an assertion
that the date was an NSE session. Actual provider candle dates alone extend the
observed-cohort grid. Existing source rows and the training snapshot never change.
"""

import json
import os
import re
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from workers.providers.calendar import nse_timing
from workers.providers.daily_clock import guard
from workers.providers.store import ProviderStore
from workers.providers.upstox import Reply, UpstoxClient, instrument_master

from alphalens_data.errors import DataContractError
from alphalens_data.providers.multi_adapters import parse_daily
from alphalens_data.providers.multi_contracts import Instrument

from .acquire import (
    FAMILY,
    PERMISSION,
    digest,
    encoded,
    initialize,
    private_path,
    replay,
    write_new,
)


def _id(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
        raise DataContractError("EXPERIMENTAL_REFRESH_PATH_REJECTED")
    return value


def _checked(path: Path, expected: str) -> bytes:
    if path.is_symlink():
        raise DataContractError("EXPERIMENTAL_REFRESH_LINK_REJECTED")
    body = path.read_bytes()
    if digest(body) != expected:
        raise DataContractError("EXPERIMENTAL_REFRESH_CHECKSUM_REJECTED")
    return body


def _new_rows(folder: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    completed = manifest.get("completed_session_evidence")
    if completed is not None:
        timing_reply = Reply(
            200,
            _checked(folder / "timings.json", completed["sha256"]),
            datetime.fromisoformat(completed["received_at"]),
            "ACCEPTED",
        )
        timing = nse_timing(timing_reply, date.fromisoformat(manifest["end"]))
        if (
            timing != completed["timing"]
            or datetime.fromisoformat(timing["end"])
            >= datetime.fromisoformat(manifest["clock"]["lower_at"])
            or not timing["session_elapsed"]
        ):
            raise DataContractError("EXPERIMENTAL_COMPLETED_SESSION_EVIDENCE_REJECTED")
    body = _checked(private_path(folder, "master.json.gz"), manifest["master_sha256"])
    identities, _ = instrument_master(
        Reply(200, body, datetime.fromisoformat(manifest["master_received_at"]), "ACCEPTED"),
        require_reliance=False,
    )
    rows = []
    for entry in manifest["instruments"]:
        identity = Instrument.model_validate(entry["identity"])
        if identity not in identities or entry["filename"] != str(identity.isin) + ".json":
            raise DataContractError("EXPERIMENTAL_REFRESH_IDENTITY_REJECTED")
        payload = _checked(private_path(folder, entry["filename"]), entry["sha256"])
        received = datetime.fromisoformat(entry["received_at"])
        candles = parse_daily(payload, identity, received)
        if len(candles) != entry["observations"] or not candles:
            raise DataContractError("EXPERIMENTAL_REFRESH_CANDLE_COUNT_REJECTED")
        for candle in candles:
            if not manifest["start"] <= str(candle.session) <= manifest["end"]:
                raise DataContractError("EXPERIMENTAL_REFRESH_CANDLE_DATE_REJECTED")
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
    return rows


def _merge(
    parent: dict[str, Any], manifest: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    if manifest["parent_dataset_id"] != parent["dataset_id"]:
        raise DataContractError("EXPERIMENTAL_REFRESH_PARENT_REJECTED")
    original = {row["key"]: (row["symbol"], row["isin"]) for row in parent["rows"]}
    if any(original.get(row["key"]) != (row["symbol"], row["isin"]) for row in rows):
        raise DataContractError("EXPERIMENTAL_REFRESH_COHORT_CHANGED")
    original_pairs = {(row["key"], row["session"]) for row in parent["rows"]}
    if any((row["key"], row["session"]) in original_pairs for row in rows):
        raise DataContractError("EXPERIMENTAL_REFRESH_CANNOT_REVISE_ORIGINAL_ROWS")
    merged = sorted([*parent["rows"], *rows], key=lambda row: (row["key"], row["session"]))
    pairs = {(row["key"], row["session"]) for row in merged}
    if len(pairs) != len(merged):
        raise DataContractError("EXPERIMENTAL_REFRESH_DUPLICATE_SESSION")
    summary = {**parent["manifest"]}
    summary["end"] = manifest["end"]
    summary["api_calls"] = parent["manifest"]["api_calls"] + manifest["api_calls"]
    summary["exclusions"] = [*parent["manifest"]["exclusions"], *manifest["exclusions"]]
    summary["correction_coverage"] = "INCREMENTAL_NEW_DATES_ONLY_NO_HISTORICAL_CORRECTION_CHECK"
    summary["instruments"] = [
        {
            **entry,
            "observations": sum(row["key"] == entry["identity"]["provider_key"] for row in merged),
            "end": max(
                row["session"] for row in merged if row["key"] == entry["identity"]["provider_key"]
            ),
        }
        for entry in parent["manifest"]["instruments"]
    ]
    result: dict[str, Any] = {
        "manifest": summary,
        "rows": merged,
        "sessions": sorted({row["session"] for row in merged}),
        "source_observed_at": max(
            [
                parent["source_observed_at"],
                *(entry["received_at"] for entry in manifest["instruments"]),
            ]
        ),
        "parent_dataset_id": parent["dataset_id"],
        "refresh_id": manifest["refresh_id"],
        "replay_api_calls": 0,
    }
    result["dataset_id"] = digest(encoded(result))
    if manifest.get("completed_session_evidence") is not None:
        result["completed_session"] = manifest["completed_session_evidence"]["timing"]
        result["dataset_id"] = digest(
            encoded({k: v for k, v in result.items() if k != "dataset_id"})
        )
    return result


def current_dataset(root: Path) -> dict[str, Any]:
    """Verify the entire append-only refresh chain and reparse source bodies, zero GETs."""
    initialize(root)
    current = replay(root)
    pointer_path = private_path(root, "data-latest.json")
    if not pointer_path.exists():
        return current
    pointer = json.loads(pointer_path.read_bytes())
    chain = []
    visited: set[str] = set()
    while pointer is not None:
        refresh_id = _id(pointer["refresh_id"])
        if refresh_id in visited:
            raise DataContractError("EXPERIMENTAL_REFRESH_CHAIN_CYCLE")
        visited.add(refresh_id)
        folder = private_path(root, "refreshes", refresh_id)
        receipt = json.loads(
            _checked(private_path(folder, "receipt.json"), pointer["receipt_sha256"])
        )
        manifest = json.loads(
            _checked(private_path(folder, "manifest.json"), receipt["manifest_sha256"])
        )
        if (
            manifest["refresh_id"] != refresh_id
            or manifest["family"] != FAMILY
            or manifest["permission_reference"] != PERMISSION
        ):
            raise DataContractError("EXPERIMENTAL_REFRESH_SCOPE_REJECTED")
        normalized = _checked(private_path(folder, "normalized.json"), receipt["normalized_sha256"])
        chain.append((folder, manifest, normalized))
        pointer = manifest["previous_refresh"]
    for folder, manifest, normalized in reversed(chain):
        current = _merge(current, manifest, _new_rows(folder, manifest))
        if encoded(current) != normalized:
            raise DataContractError("EXPERIMENTAL_REFRESH_REPLAY_CHANGED")
    return current


def refresh(
    root: Path,
    provider_root: Path,
    *,
    permission_reference: str,
    retry_pending: bool = False,
    include_completed_today: bool = False,
) -> dict[str, Any]:
    """One explicit bounded operation; repeat completed/pending dates makes no GETs.

    retry_pending is an operator-requested publication recheck, never an automatic
    polling loop. This does not examine historical corrections or extend a task.
    """
    if permission_reference != PERMISSION:
        raise DataContractError("EXPERIMENTAL_PRIVATE_SOURCE_PERMISSION_REQUIRED")
    clock = guard()
    end = date.fromisoformat(clock["session_date"]) - timedelta(days=not include_completed_today)
    parent = current_dataset(root)
    latest = date.fromisoformat(parent["sessions"][-1])
    last_by_key: dict[str, date] = {}
    for row in parent["rows"]:
        day = date.fromisoformat(row["session"])
        last_by_key[row["key"]] = max(day, last_by_key.get(row["key"], day))
    if latest >= end and (not retry_pending or min(last_by_key.values()) >= end):
        return {**parent, "refresh_state": "UP_TO_DATE_ZERO_REQUEST_REPLAY"}
    if (end - min(last_by_key.values())).days > 30:
        raise DataContractError("EXPERIMENTAL_REFRESH_CATCHUP_OVER_30_DAYS")
    pending_path = private_path(root, "refresh-pending.json")
    if pending_path.exists() and not retry_pending:
        pending = json.loads(pending_path.read_bytes())
        if pending["end"] == str(end) and pending["parent_dataset_id"] == parent["dataset_id"]:
            return {
                **parent,
                "refresh_state": "PUBLICATION_OR_OBSERVED_COVERAGE_PENDING_ZERO_REQUEST_REPLAY",
                "pending": pending,
            }
    originals = [
        Instrument.model_validate(entry["identity"]) for entry in parent["manifest"]["instruments"]
    ]
    if not 1 <= len(originals) <= 30 or len({item.provider_key for item in originals}) != len(
        originals
    ):
        raise DataContractError("EXPERIMENTAL_BOUNDED_ORIGINAL_COHORT_REQUIRED")
    refresh_id = uuid4().hex
    folder = private_path(root, "refreshes", refresh_id)
    folder.mkdir(parents=True)
    client = UpstoxClient(
        ProviderStore(provider_root), budget=32 if include_completed_today else 31, retries=0
    )
    completed = None
    if include_completed_today:
        timing_reply = client.get("timings", end=end)
        timing = nse_timing(timing_reply, end)
        if not timing["session_elapsed"] or datetime.fromisoformat(
            timing["end"]
        ) >= datetime.fromisoformat(clock["lower_at"]):
            raise DataContractError("EXPERIMENTAL_OFFICIAL_SESSION_NOT_COMPLETED")
        write_new(private_path(folder, "timings.json"), timing_reply.body)
        completed = {
            "sha256": digest(timing_reply.body),
            "timing": timing,
            "received_at": timing_reply.received_at.isoformat(),
        }
    master_reply = client.get("instruments")
    identities, _ = instrument_master(master_reply, require_reliance=False)
    write_new(private_path(folder, "master.json.gz"), master_reply.body)
    selections: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for original in originals:
        instrument_start = last_by_key[original.provider_key] + timedelta(days=1)
        if instrument_start > end:
            continue
        matches = [
            item
            for item in identities
            if (item.provider_key, item.symbol, item.isin)
            == (original.provider_key, original.symbol, original.isin)
        ]
        if len(matches) != 1:
            exclusions.append(
                {
                    "key": original.provider_key,
                    "reason": "EXACT_CURRENT_IDENTITY_CHANGED_OR_UNAVAILABLE",
                }
            )
            continue
        identity = matches[0]
        reply = client.get("candles", key=identity.provider_key, start=instrument_start, end=end)
        if reply.state != "ACCEPTED":
            exclusions.append(
                {"key": identity.provider_key, "reason": reply.state, "status": reply.status}
            )
            if reply.status in {401, 403, 429}:
                break
            continue
        candles = parse_daily(reply.body, identity, reply.received_at)
        if not candles:
            exclusions.append(
                {
                    "key": identity.provider_key,
                    "reason": "PUBLICATION_OR_NONSESSION_NO_OBSERVED_CANDLE",
                }
            )
            continue  # Empty market payload is not retained as a completed session.
        if any(not instrument_start <= candle.session <= end for candle in candles):
            raise DataContractError("EXPERIMENTAL_REFRESH_RESPONSE_OUTSIDE_WINDOW")
        filename = str(identity.isin) + ".json"
        write_new(private_path(folder, filename), reply.body)
        selections.append(
            {
                "identity": identity.model_dump(mode="json"),
                "filename": filename,
                "sha256": digest(reply.body),
                "received_at": reply.received_at.isoformat(),
                "observations": len(candles),
            }
        )
    previous = (
        json.loads(private_path(root, "data-latest.json").read_bytes())
        if private_path(root, "data-latest.json").exists()
        else None
    )
    manifest = {
        "schema": "alphalens.experimental_nse.refresh.v1",
        "family": FAMILY,
        "permission_reference": permission_reference,
        "refresh_id": refresh_id,
        "parent_dataset_id": parent["dataset_id"],
        "previous_refresh": previous,
        "start": str(min(last_by_key.values()) + timedelta(days=1)),
        "end": str(end),
        "clock": clock,
        "master_sha256": digest(master_reply.body),
        "master_received_at": master_reply.received_at.isoformat(),
        "instruments": selections,
        "exclusions": exclusions,
        "api_calls": client.calls,
        "calendar": "OBSERVED_COHORT_DATES_NOT_OFFICIAL_COMPLETE_CALENDAR",
        "completed_session_evidence": completed,
    }
    manifest_body = encoded(manifest)
    write_new(private_path(folder, "manifest.json"), manifest_body)
    merged = _merge(parent, manifest, _new_rows(folder, manifest))
    normalized_body = encoded(merged)
    write_new(private_path(folder, "normalized.json"), normalized_body)
    receipt_body = encoded(
        {"manifest_sha256": digest(manifest_body), "normalized_sha256": digest(normalized_body)}
    )
    write_new(private_path(folder, "receipt.json"), receipt_body)
    pointer = {"refresh_id": refresh_id, "receipt_sha256": digest(receipt_body)}
    temporary = private_path(root, "data-latest-" + uuid4().hex + ".json")
    write_new(temporary, encoded(pointer))
    os.replace(temporary, private_path(root, "data-latest.json"))
    # A receipt for the queried date also prevents repeat downloads on holidays or
    # publication delay. Explicit retry may recheck, retaining every prior receipt.
    pending = {
        "end": str(end),
        "parent_dataset_id": merged["dataset_id"],
        "exclusions": exclusions,
        "refresh_id": refresh_id,
    }
    temporary_pending = private_path(root, "refresh-pending-" + uuid4().hex + ".json")
    write_new(temporary_pending, encoded(pending))
    os.replace(temporary_pending, pending_path)
    return {
        **merged,
        "refresh_state": (
            "BOUNDED_INCREMENTAL_CAPTURE_COMPLETE"
            if selections
            else "PUBLICATION_OR_NONSESSION_PENDING"
        ),
        "refresh_api_calls": client.calls,
    }
