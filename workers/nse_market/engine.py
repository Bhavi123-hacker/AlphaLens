"""Incremental current-equity research capture with immutable per-request checkpoints.

The original 50-stock V2 snapshot, models and forecast ledger are read-only inputs.
Current common-equity membership is not historical membership. No import, API GET,
or preparation step acquires prices or enables scheduled collection.
"""

from __future__ import annotations

import copy
import gzip
import json
import re
import time
import uuid
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from alphalens_data.daily.storage import Store
from alphalens_data.providers.multi_contracts import Instrument
from workers.experimental_nse.acquire import (
    PERMISSION,
    digest,
    encoded,
    initialize,
    private_path,
    write_new,
)
from workers.experimental_nse_v2 import data as v2_data
from workers.experimental_nse_v2 import forward, models, pipeline
from workers.experimental_nse_v2.features import (
    LOCAL_FEATURE_NAMES,
    LOCAL_FEATURE_VERSION,
    FeatureDataset,
    build,
)
from workers.providers.daily_clock import guard
from workers.providers.store import ProviderStore
from workers.providers.upstox import Operation, Reply, UpstoxClient

FAMILY = "ALPHALENS_EXPANDED_NSE_RESEARCH_V1"
SELECTION = "ORIGINAL_50_THEN_CURRENT_VERIFIED_COMMON_EQUITIES_SORTED_ISIN_SYMBOL_V1"
START = date(2022, 1, 1)
_WORKSPACE_CACHE: dict[str, tuple[tuple[Any, ...], float, dict[str, Any]]] = {}


def _checked(path: Path, value: Any) -> str:
    body = encoded(value)
    if path.exists():
        raise FileExistsError("NSE_MARKET_IMMUTABLE_RECORD_ALREADY_EXISTS")
    # Keep atomic publication compatible with ordinary Windows MAX_PATH settings.
    temporary = path.with_name("t-" + uuid.uuid4().hex + ".tmp")
    write_new(temporary, body)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if sidecar.exists():
        if sidecar.read_text() != digest(body):
            raise ValueError("NSE_MARKET_INTERRUPTED_RECORD_HASH_CONFLICT")
    else:
        write_new(sidecar, digest(body).encode())
    temporary.replace(path)  # Readers see a complete object with its checksum.
    return digest(body)


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or path.with_suffix(path.suffix + ".sha256").is_symlink():
        raise ValueError("NSE_MARKET_SYMLINK_REJECTED")
    body = path.read_bytes()
    if digest(body) != path.with_suffix(path.suffix + ".sha256").read_text():
        raise ValueError("NSE_MARKET_IMMUTABLE_EVIDENCE_CHECKSUM_REJECTED")
    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("NSE_MARKET_OBJECT_REQUIRED")
    return value


def _pointer(root: Path, name: str, target: Path) -> None:
    temporary = private_path(root, name + "." + uuid.uuid4().hex + ".tmp")
    write_new(temporary, encoded({"path": target.relative_to(root).as_posix()}))
    temporary.replace(private_path(root, name))


def _pointed(root: Path, name: str) -> dict[str, Any]:
    value = json.loads(private_path(root, name).read_bytes())
    parts = Path(value["path"]).parts
    if not parts or any(part in {".", ".."} for part in parts):
        raise ValueError("NSE_MARKET_POINTER_REJECTED")
    return _read(private_path(root, *parts))


def _identity(value: Any) -> Instrument:
    item = Instrument.model_validate(value)
    if (
        item.provider != "upstox"
        or item.exchange != "NSE"
        or item.segment != "NSE_EQ"
        or item.instrument_type not in {"EQ", "BE", "BZ", "SM", "ST", "SZ"}
        or not item.isin
        or not re.fullmatch(r"INE[A-Z0-9]{9}", item.isin)
        or item.provider_key != "NSE_EQ|" + item.isin
    ):
        raise ValueError("VERIFIED_NSE_COMMON_EQUITY_IDENTITY_REQUIRED")
    return item


def prepare(
    root: Path,
    v2_root: Path,
    identities: list[Instrument],
    universe_evidence: dict[str, Any],
    target_count: int,
) -> dict[str, Any]:
    """Freeze a deterministic cohort before new observations; no provider calls."""
    initialize(root)
    if universe_evidence.get("verified_common_equities") is not True:
        raise ValueError("INDEPENDENT_COMMON_EQUITY_CLASSIFICATION_REQUIRED")
    instruments = [_identity(item.model_dump(mode="json")) for item in identities]
    if len({i.provider_key for i in instruments}) != len(instruments):
        raise ValueError("UNIQUE_CURRENT_EQUITY_IDENTITIES_REQUIRED")
    if not 1 <= target_count <= len(instruments):
        raise ValueError("BOUNDED_AVAILABLE_COHORT_REQUIRED")
    seed_path = private_path(root, "seed.json")
    if seed_path.exists():
        seed = _read(seed_path)
    else:
        original = v2_data.load_current(v2_root)
        seed = {
            "family": FAMILY,
            "original_v2_dataset_id": original["dataset_id"],
            "rows": original["rows"],
            "actions": original["actions"],
            "identities": original["identities"],
            "source_observed_at": original["source_observed_at"],
            "session_timing": original.get("session_timing"),
            "next_session_timing": original.get("next_session_timing"),
            "price_basis": original["price_basis"],
            "copied_at": datetime.now(UTC).isoformat(),
            "original_forecast_ledger_touched": False,
        }
        _checked(seed_path, seed)
    current = {i.provider_key: i for i in instruments}
    original_keys = {r["key"] for r in seed["rows"]}
    existing = sorted(original_keys & current.keys())
    if target_count < len(existing):
        raise ValueError("ORIGINAL_ELIGIBLE_COHORT_MUST_BE_PRESERVED")
    additional = sorted(
        (item for item in instruments if item.provider_key not in original_keys),
        key=lambda item: (str(item.isin), item.symbol),
    )
    selected = [current[key] for key in existing] + additional[: target_count - len(existing)]
    plan = {
        "family": FAMILY,
        "permission_reference": PERMISSION,
        "selection_policy": SELECTION,
        "universe_evidence": universe_evidence,
        "universe_count": len(instruments),
        "target_count": target_count,
        "identities": [i.model_dump(mode="json") for i in selected],
        "original_v2_dataset_id": seed["original_v2_dataset_id"],
        "seed_sha256": digest(seed_path.read_bytes()),
        "history_start": str(START),
        "history_end": max(r["session"] for r in seed["rows"]),
        "historical_membership": "CURRENT_FIXED_COHORT_NOT_SURVIVORSHIP_FREE",
        "scheduled_collection_enabled": False,
    }
    identifier = digest(encoded(plan))
    plan["plan_id"] = identifier
    plans = private_path(root, "plans")
    plans.mkdir(exist_ok=True)
    path = plans / (identifier + ".json")
    if path.exists():
        if _read(path) != plan:
            raise ValueError("NSE_MARKET_PLAN_REPLAY_CONFLICT")
    else:
        _checked(path, plan)
    _pointer(root, "plan-latest.json", path)
    return {**plan, "additional_history_candidates": len(selected) - len(existing)}


class Meter:
    """One shared logical budget across transport instances; retries remain disabled."""

    def __init__(self, provider_root: Path, maximum: int) -> None:
        if isinstance(maximum, bool) or not 1 <= maximum <= 600:
            raise ValueError("NSE_MARKET_EXPLICIT_BOUNDED_REQUEST_BUDGET_REQUIRED")
        self.maximum = maximum
        self.calls = 0
        self.store = ProviderStore(provider_root)
        self.client = UpstoxClient(self.store, budget=min(maximum, 100), retries=0)

    def get(self, operation: Operation, **kwargs: Any) -> Reply:
        if self.calls >= self.maximum:
            raise ValueError("NSE_MARKET_RUN_REQUEST_BUDGET_EXHAUSTED")
        if self.client.calls >= self.client.budget:
            self.client = UpstoxClient(
                self.store, budget=min(self.maximum - self.calls, 100), retries=0
            )
        self.calls += 1
        return self.client.get(operation, **kwargs)


def _folder(root: Path, identity: Instrument) -> Path:
    return private_path(root, "instruments", str(identity.isin))


def _response(
    path: Path,
    reply: Reply,
    identity: Instrument,
    start: date,
    end: date,
    *,
    request: dict[str, Any] | None = None,
) -> None:
    """Checkpoint the exact historical response immediately, before actions/next stock."""
    raw = path / "candles.json"
    write_new(raw, reply.body)
    _checked(
        path / "response.json",
        {
            "identity": identity.model_dump(mode="json"),
            "received_at": reply.received_at.isoformat(),
            "server_at": reply.server_at.isoformat() if reply.server_at else None,
            "state": reply.state,
            "status": reply.status,
            "raw_sha256": digest(reply.body),
            "start": str(start),
            "end": str(end),
            **({"request": request} if request is not None else {}),
        },
    )


def _rows(folder: Path, identity: Instrument) -> list[dict[str, Any]]:
    source = _read(folder / "response.json")
    if source["identity"]["provider_key"] != identity.provider_key:
        raise ValueError("NSE_MARKET_RESPONSE_IDENTITY_MISMATCH")
    body = (folder / "candles.json").read_bytes()
    if digest(body) != source["raw_sha256"]:
        raise ValueError("NSE_MARKET_RAW_RESPONSE_CHECKSUM_REJECTED")
    normalized = folder / "normalization.json"
    if normalized.exists():
        manifest = _read(normalized)
        cached = (folder / "normalized.json.gz").read_bytes()
        if (
            manifest["version"] != "PINNED_V2_NORMALIZED_DAILY_ROWS_V1"
            or manifest["source_response_sha256"] != digest((folder / "response.json").read_bytes())
            or manifest["raw_sha256"] != digest(body)
            or manifest["identity_key"] != identity.provider_key
            or manifest["normalized_sha256"] != digest(cached)
        ):
            raise ValueError("EXPANDED_NORMALIZATION_CACHE_LINEAGE_REJECTED")
        rows: list[dict[str, Any]] = json.loads(gzip.decompress(cached))
        return rows
    rows = v2_data.normalized(body, identity, datetime.fromisoformat(source["received_at"]))
    if any(not source["start"] <= row["session"] <= source["end"] for row in rows):
        raise ValueError("NSE_MARKET_HISTORY_OUTSIDE_DECLARED_DATES")
    return rows


def _cache_normalized(folder: Path, identity: Instrument, rows: list[dict[str, Any]]) -> None:
    if not rows or (folder / "normalization.json").exists():
        return
    cached = gzip.compress(encoded(rows), compresslevel=1, mtime=0)
    path = folder / "normalized.json.gz"
    if path.exists():
        if path.read_bytes() != cached:
            raise ValueError("EXPANDED_INTERRUPTED_NORMALIZATION_CONFLICT")
    else:
        write_new(path, cached)
    _checked(
        folder / "normalization.json",
        {
            "version": "PINNED_V2_NORMALIZED_DAILY_ROWS_V1",
            "identity_key": identity.provider_key,
            "source_response_sha256": digest((folder / "response.json").read_bytes()),
            "raw_sha256": digest((folder / "candles.json").read_bytes()),
            "normalized_sha256": digest(cached),
            "observations": len(rows),
        },
    )


def materialize(root: Path) -> dict[str, Any]:
    """Explicit read/validate/cache command. Never run implicitly from dashboard GET."""
    initialize(root)
    started = time.monotonic()
    count = 0
    with Store(private_path(root, "control")).lock():
        for path in private_path(root, "instruments").glob("INE*/response.json"):
            source = _read(path)
            item = _identity(source["identity"])
            rows = _rows(path.parent, item)
            _cache_normalized(path.parent, item, rows)
            count += bool(rows)
    _WORKSPACE_CACHE.pop(str(root.resolve()), None)
    return {
        "api_calls": 0,
        "normalized_instruments": count,
        "elapsed_seconds": time.monotonic() - started,
    }


def _complete(folder: Path) -> bool:
    path = folder / "completed.json"
    if not path.exists():
        return False
    record = _read(path)
    return record.get("state") == "VALIDATED_HISTORY" and record.get("observations", 0) > 0


def _archive_empty(folder: Path) -> None:
    """Retain the exact empty response and clocks; allow a later bounded new query."""
    target = folder / "history-attempts" / uuid.uuid4().hex
    target.mkdir(parents=True)
    if not target.resolve().is_relative_to(folder.resolve()):
        raise ValueError("EXPANDED_ATTEMPT_ARCHIVE_PATH_REJECTED")
    for name in (
        "candles.json",
        "response.json",
        "response.json.sha256",
        "completed.json",
        "completed.json.sha256",
    ):
        path = folder / name
        if path.exists():
            path.rename(target / name)
    _checked(
        target / "pending.json",
        {
            "state": "EMPTY_HISTORY_PUBLICATION_OR_LISTING_COVERAGE_PENDING",
            "not_a_completed_capture": True,
        },
    )


def _bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def capture(
    root: Path,
    provider_root: Path,
    *,
    max_new: int = 50,
    max_requests: int = 100,
    permission_reference: str,
    meter: Any | None = None,
) -> dict[str, Any]:
    """Manual bounded history pilot. Complete per-stock checkpoints are zero-GET replay."""
    initialize(root)
    with Store(private_path(root, "control")).lock():
        return _capture(
            root,
            provider_root,
            max_new=max_new,
            max_requests=max_requests,
            permission_reference=permission_reference,
            meter=meter,
        )


def _capture(
    root: Path,
    provider_root: Path,
    *,
    max_new: int,
    max_requests: int,
    permission_reference: str,
    meter: Any | None,
) -> dict[str, Any]:
    initialize(root)
    if permission_reference != PERMISSION:
        raise ValueError("NSE_MARKET_PRIVATE_RETENTION_PERMISSION_REQUIRED")
    if isinstance(max_new, bool) or not 1 <= max_new <= 250:
        raise ValueError("NSE_MARKET_BOUNDED_NEW_STOCK_COUNT_REQUIRED")
    if isinstance(max_requests, bool) or not 1 <= max_requests <= 600:
        raise ValueError("NSE_MARKET_EXPLICIT_BOUNDED_REQUEST_BUDGET_REQUIRED")
    plan = _pointed(root, "plan-latest.json")
    seed = _read(private_path(root, "seed.json"))
    if plan["seed_sha256"] != digest(private_path(root, "seed.json").read_bytes()):
        raise ValueError("NSE_MARKET_SEED_LINEAGE_REJECTED")
    identities = [_identity(value) for value in plan["identities"]]
    seed_keys = {row["key"] for row in seed["rows"]}
    pending = [i for i in identities if i.provider_key not in seed_keys]
    if all(_complete(_folder(root, item)) for item in pending):
        return {"state": "REPLAY", "api_calls": 0, "replayed": len(pending), **coverage(root)}
    clock = guard()
    if date.fromisoformat(clock["session_date"]) <= date.fromisoformat(plan["history_end"]):
        raise ValueError("NSE_MARKET_COMPLETED_PRIOR_HISTORY_DATE_REQUIRED")
    started, before = time.monotonic(), _bytes(root)
    transport = meter or Meter(provider_root, max_requests)
    initial_calls = transport.calls
    instruments_dir = private_path(root, "instruments")
    instruments_dir.mkdir(exist_ok=True)
    acquired, processed = 0, 0
    failures: list[dict[str, Any]] = []
    for identity in pending:
        folder = _folder(root, identity)
        if _complete(folder):
            continue
        if processed >= max_new or transport.calls - initial_calls >= max_requests:
            break
        processed += 1
        folder.mkdir(exist_ok=True)
        try:
            if (folder / "completed.json").exists():
                _archive_empty(folder)
            if not (folder / "response.json").exists():
                # Interrupted raw-only writes are retained as evidence, not overwritten.
                if (folder / "candles.json").exists():
                    failures.append(
                        {
                            "key": identity.provider_key,
                            "reason": "RAW_ONLY_CHECKPOINT_REVIEW_REQUIRED",
                        }
                    )
                    continue
                reply = transport.get(
                    "candles",
                    key=identity.provider_key,
                    start=date.fromisoformat(plan["history_start"]),
                    end=date.fromisoformat(plan["history_end"]),
                )
                if reply.state != "ACCEPTED" or reply.status != 200:
                    failures.append(
                        {
                            "key": identity.provider_key,
                            "reason": reply.state,
                            "status": reply.status,
                        }
                    )
                    if reply.status in {401, 403, 429}:
                        break
                    continue
                _response(folder, reply, identity, START, date.fromisoformat(plan["history_end"]))
            rows = _rows(folder, identity)
            if not rows:
                _archive_empty(folder)
                failures.append(
                    {
                        "key": identity.provider_key,
                        "reason": "EMPTY_HISTORY_PUBLICATION_OR_LISTING_COVERAGE_PENDING",
                    }
                )
                continue
            _cache_normalized(folder, identity, rows)
            action_path = folder / "actions.json"
            if not action_path.exists():
                if transport.calls - initial_calls >= max_requests:
                    break  # History survives interruption; resume requests only actions.
                reply = transport.get("actions", key=identity.provider_key)
                if reply.state != "ACCEPTED" or reply.status != 200:
                    attempts = folder / "action-attempts"
                    attempts.mkdir(exist_ok=True)
                    _checked(
                        attempts / (uuid.uuid4().hex + ".json"),
                        {**v2_data.action_facts(reply), "status": reply.status},
                    )
                    failures.append(
                        {
                            "key": identity.provider_key,
                            "reason": reply.state,
                            "operation": "actions",
                        }
                    )
                    if reply.status in {401, 403, 429}:
                        break
                    continue
                _checked(action_path, v2_data.action_facts(reply))
            actions = _read(action_path)
            _checked(
                folder / "completed.json",
                {
                    "key": identity.provider_key,
                    "state": "VALIDATED_HISTORY",
                    "observations": len(rows),
                    "start": rows[0]["session"],
                    "end": rows[-1]["session"],
                    "response_sha256": digest((folder / "response.json").read_bytes()),
                    "actions_sha256": digest(action_path.read_bytes()),
                    "action_coverage_complete": actions.get("complete", False),
                },
            )
            acquired += 1
        except (ValueError, KeyError, TypeError) as exc:
            reason = str(exc)
            failures.append(
                {
                    "key": identity.provider_key,
                    "reason": reason
                    if re.fullmatch(r"[A-Z0-9_]+", reason)
                    else "SOURCE_RESPONSE_VALIDATION_FAILED",
                }
            )
    result = {
        "state": "BOUNDED_CAPTURE_COMPLETE",
        "plan_id": plan["plan_id"],
        "clock": clock,
        "api_calls": transport.calls - initial_calls,
        "max_requests": max_requests,
        "newly_validated_securities": acquired,
        "failures": failures,
        "elapsed_seconds": time.monotonic() - started,
        "storage_growth_bytes": _bytes(root) - before,
        "completed_at": datetime.now(UTC).isoformat(),
        **coverage(root),
    }
    runs = private_path(root, "runs")
    runs.mkdir(exist_ok=True)
    target = runs / (uuid.uuid4().hex + ".json")
    _checked(target, result)
    _pointer(root, "capture-latest.json", target)
    return result


def snapshot(root: Path) -> dict[str, Any]:
    """Verify saved source bytes and construct the observed cohort, never fill dates."""
    plan = _pointed(root, "plan-latest.json")
    seed = _read(private_path(root, "seed.json"))
    if plan["seed_sha256"] != digest(private_path(root, "seed.json").read_bytes()):
        raise ValueError("NSE_MARKET_SEED_LINEAGE_REJECTED")
    identities = [_identity(value) for value in plan["identities"]]
    keys = {i.provider_key for i in identities}
    latest_identities = {item.provider_key: item.model_dump(mode="json") for item in identities}
    rows = [row for row in seed["rows"] if row["key"] in keys]
    seed_keys = {row["key"] for row in rows}
    actions = {key: value for key, value in seed["actions"].items() if key in keys}
    states = []
    for identity in identities:
        if identity.provider_key in seed_keys:
            states.append(
                {"key": identity.provider_key, "state": "ORIGINAL_V2_OBSERVATIONS_REUSED"}
            )
            continue
        folder = _folder(root, identity)
        if not (folder / "response.json").exists():
            states.append(
                {
                    "key": identity.provider_key,
                    "state": "EMPTY_HISTORY_PUBLICATION_OR_LISTING_COVERAGE_PENDING"
                    if (folder / "history-attempts").exists()
                    else "NOT_QUERIED",
                }
            )
            continue
        try:
            observed = _rows(folder, identity)
            if (folder / "completed.json").exists():
                completed = _read(folder / "completed.json")
                if completed["state"] == "VALIDATED_HISTORY" and (
                    completed["response_sha256"] != digest((folder / "response.json").read_bytes())
                    or completed["actions_sha256"] != digest((folder / "actions.json").read_bytes())
                ):
                    raise ValueError("NSE_MARKET_COMPLETION_CHECKSUM_REJECTED")
            rows.extend(observed)
            if (folder / "actions.json").exists():
                actions[identity.provider_key] = _read(folder / "actions.json")
            states.append(
                {
                    "key": identity.provider_key,
                    "state": "VALIDATED_HISTORY" if observed else "NO_OBSERVED_HISTORY",
                }
            )
        except (ValueError, KeyError, TypeError):
            states.append({"key": identity.provider_key, "state": "REJECTED_SOURCE_EVIDENCE"})
    daily_dir = private_path(root, "daily")
    if daily_dir.exists():
        by_slot = {(row["key"], row["session"]): row for row in rows}
        for path in sorted(daily_dir.glob("*/INE*/record.json")):
            record = _read(path)
            identity = _identity(record["identity"])
            if identity.provider_key not in keys:
                continue
            latest_identities[identity.provider_key] = identity.model_dump(mode="json")
            if record.get("response_sha256") != digest(
                (path.parent / "response.json").read_bytes()
            ):
                raise ValueError("NSE_MARKET_DAILY_RESPONSE_CHECKSUM_REJECTED")
            observed = _rows(path.parent, identity)
            if record.get("actions_sha256") != digest((path.parent / "actions.json").read_bytes()):
                raise ValueError("NSE_MARKET_DAILY_ACTION_CHECKSUM_REJECTED")
            actions[identity.provider_key] = _read(path.parent / "actions.json")
            for row in observed:
                slot = row["key"], row["session"]
                if slot in by_slot and any(
                    row[name] != by_slot[slot][name]
                    for name in ("open", "high", "low", "close", "volume")
                ):
                    raise ValueError("NSE_MARKET_REVISION_CONFLICT_REQUIRES_NEW_VERSION")
                by_slot.setdefault(slot, row)
        rows = list(by_slot.values())
    rows.sort(key=lambda row: (row["key"], row["session"]))
    # Preserve every provider payload, but do not invent a new trading session
    # from an isolated candle absent from the original observed session grid.
    seed_days = {row["session"] for row in seed["rows"]}
    calendar_states: dict[str, str] = {}
    for day in sorted({row["session"] for row in rows} - seed_days):
        calendar_path = private_path(root, "calendar", day + ".json")
        if not calendar_path.exists():
            calendar_states[day] = "OFFICIAL_SESSION_EVIDENCE_PENDING"
            continue
        calendar = _read(calendar_path)
        raw = bytes.fromhex(calendar["raw_hex"])
        if digest(raw) != calendar["raw_sha256"]:
            raise ValueError("EXPANDED_CALENDAR_RAW_CHECKSUM_REJECTED")
        fact = v2_data.timing_fact(
            Reply(200, raw, datetime.fromisoformat(calendar["received_at"]), "ACCEPTED"),
            date.fromisoformat(day),
        )
        calendar_states[day] = (
            "OFFICIAL_TRADING_SESSION" if fact is not None else "OFFICIAL_NON_TRADING_SESSION"
        )
    reported_observations = len(rows)
    quarantined = [
        {
            "key": row["key"],
            "symbol": row["symbol"],
            "session": row["session"],
            "reason": calendar_states[row["session"]],
        }
        for row in rows
        if row["session"] in calendar_states
        and calendar_states[row["session"]] != "OFFICIAL_TRADING_SESSION"
    ]
    rows = [
        row
        for row in rows
        if row["session"] not in calendar_states
        or calendar_states[row["session"]] == "OFFICIAL_TRADING_SESSION"
    ]
    latest_day = max(row["session"] for row in rows)
    latest_timing = seed.get("session_timing")
    next_timing = seed.get("next_session_timing")
    session_path = private_path(root, "session-links", latest_day + ".json")
    if session_path.exists():
        link = _read(session_path)
        latest_timing, next_timing = link["session_timing"], link["next_session_timing"]
    result = {
        "family": FAMILY,
        "plan_id": plan["plan_id"],
        "rows": rows,
        "identities": [latest_identities[item.provider_key] for item in identities],
        "actions": actions,
        "sessions": sorted({row["session"] for row in rows}),
        "states": states,
        "quality": v2_data.quality(rows, actions),
        "price_basis": seed["price_basis"],
        "source_observed_at": max(row["received_at"] for row in rows),
        "session_timing": latest_timing,
        "next_session_timing": next_timing,
    }
    result["quality"].update(
        provider_reported_observations=reported_observations,
        calendar_quarantined_observations=quarantined,
        additional_dated_calendar_states=calendar_states,
    )
    result["dataset_id"] = digest(encoded(result))
    return result


def coverage(root: Path, frame: dict[str, Any] | None = None) -> dict[str, Any]:
    frame = frame if frame is not None else snapshot(root)
    actual = {row["key"] for row in frame["rows"]}
    observed: dict[str, list[str]] = {}
    for row in frame["rows"]:
        observed.setdefault(row["key"], []).append(row["session"])
    return {
        "configured_securities": len(frame["identities"]),
        "validated_historical_securities": len(actual),
        "observations": len(frame["rows"]),
        "start": frame["sessions"][0],
        "end": frame["sessions"][-1],
        "observed_sessions": len(frame["sessions"]),
        "missing_observed_cohort_slots": frame["quality"]["missing_cohort_slots"],
        "official_calendar_complete": False,
        "per_security": [
            {
                "key": key,
                "observations": len(days),
                "first": min(days),
                "last": max(days),
                "missing_observed_slots": len(frame["sessions"]) - len(days),
            }
            for key, days in sorted(observed.items())
        ],
        "not_observed": [row for row in frame["states"] if row["key"] not in actual],
        "dataset_id": frame["dataset_id"],
        "provider_queried_securities": sum(
            item["state"] != "NOT_QUERIED" for item in frame["states"]
        ),
        "provider_accessible_securities": sum(
            item["state"]
            in {"ORIGINAL_V2_OBSERVATIONS_REUSED", "VALIDATED_HISTORY", "NO_OBSERVED_HISTORY"}
            for item in frame["states"]
        ),
        "provider_reported_observations": frame["quality"]["provider_reported_observations"],
        "calendar_quarantined_observations": frame["quality"]["calendar_quarantined_observations"],
    }


def _latest_features(frame: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], Any]:
    """The frozen 16 features depend on exactly 61 slots, not the full archive."""
    sessions = frame["sessions"][-61:]
    selected = set(sessions)
    rows = [row for row in frame["rows"] if row["session"] in selected]
    names: dict[str, set[str]] = {}
    for row in rows:
        names.setdefault(row["key"], set()).add(row["symbol"])
    changed = {key for key, symbols in names.items() if len(symbols) != 1}
    rows = [row for row in rows if row["key"] not in changed]
    reasons = tuple(
        {
            "key": key,
            "session": sessions[-1],
            "reason": "DATED_SYMBOL_CHANGE_REQUIRES_FROZEN_MODEL_COMPATIBILITY_REVIEW",
        }
        for key in sorted(changed)
    )
    features = (
        build(rows, sessions, frame["quality"]["excluded_sessions"], include_context=False)
        if rows
        else FeatureDataset((), tuple(sessions), (), 0, 0)
    )
    if reasons:
        features = replace(features, exclusions=(*features.exclusions, *reasons))
    return rows, sessions, features


def score(root: Path, v2_root: Path) -> dict[str, Any]:
    """Pinned V2 price-only extrapolation; no fit, original-ledger write or acceptance."""
    initialize(root)
    with Store(private_path(root, "control")).lock():
        return _score(root, v2_root)


def _score(root: Path, v2_root: Path) -> dict[str, Any]:
    frame = snapshot(root)
    model_root = v2_root / "price-only"
    evaluation = pipeline.verified(model_root / "evaluation.json")
    model = models.load_model(model_root / "model.json", evaluation["model_sha256"])
    if (
        model["feature_version"] != LOCAL_FEATURE_VERSION
        or tuple(model["feature_names"]) != LOCAL_FEATURE_NAMES
        or model["protocol_id"] != pipeline.protocol_id(True)
        or model["model_id"] != evaluation["model_id"]
    ):
        raise ValueError("PINNED_ORIGINAL_V2_PRICE_ONLY_MODEL_REQUIRED")
    if (root / "scores-latest.json").exists():
        previous = _pointed(root, "scores-latest.json")
        if (
            previous["dataset_id"] == frame["dataset_id"]
            and previous["model_id"] == model["model_id"]
        ):
            return {**previous, "replayed": True, "new_forecasts": 0}
    clock = guard()
    timing, following = frame.get("session_timing"), frame.get("next_session_timing")
    latest = frame["sessions"][-1]
    if not timing or not following or timing["session"] != latest:
        raise ValueError("EXPANDED_LATEST_OFFICIAL_SESSION_AND_FUTURE_ENTRY_TIMING_REQUIRED")
    if datetime.fromisoformat(following["open_at"]) <= datetime.fromisoformat(clock["upper_at"]):
        raise ValueError("EXPANDED_FORECAST_ENTRY_MUST_FOLLOW_INDEPENDENT_CLOCK_BOUND")
    decision = datetime.now(UTC)
    baseline = pipeline.verified(model_root / "training-baseline.json")
    if baseline["model_id"] != model["model_id"] or baseline["dataset_id"] != model["dataset_id"]:
        raise ValueError("ORIGINAL_FROZEN_TRAINING_BASELINE_LINEAGE_REQUIRED")
    majority = float(baseline["majority_score"])
    latest_rows, latest_sessions, features = _latest_features(frame)
    candidates = (
        models.score(
            model,
            latest_rows,
            latest_sessions,
            decision,
            datetime.fromisoformat(frame["source_observed_at"]),
            datetime.fromisoformat(following["open_at"]),
            following["session"],
            frame["quality"]["excluded_sessions"],
            completed_session_end=datetime.fromisoformat(timing["close_at"]),
            training_majority_score=majority,
        )
        if latest_rows
        else []
    )
    seed = _read(private_path(root, "seed.json"))
    original_keys = {row["key"] for row in seed["rows"]}
    identities = {item["provider_key"]: item for item in frame["identities"]}
    source_rows = {(row["key"], row["session"]): row for row in frame["rows"]}
    for item in candidates:
        item.update(
            training_dataset_id=model["dataset_id"],
            dataset_id=frame["dataset_id"],
            identity=identities[item["key"]],
            source_sha256=source_rows[item["key"], item["session"]]["raw_sha256"],
            decision_clock=clock,
            session_timing=timing,
            next_session_timing=following,
            feature_names=list(LOCAL_FEATURE_NAMES),
            applicability=(
                "ORIGINAL_TRAINING_COHORT"
                if item["key"] in original_keys
                else "OUT_OF_TRAINING_COHORT_EXTRAPOLATION_UNVALIDATED"
            ),
            classification="EXPERIMENTAL_UNVALIDATED",
            warning="EXPERIMENTAL — NOT INDEPENDENTLY VALIDATED; NO_DEMONSTRATED_EDGE",
        )
    # Separate ledgers, each <=100 according to the unchanged V2 safety contract.
    # No attempt is made to expand or bypass the original accepted ranking service.
    forecasts = 0
    existing_forecasts = 0
    # Stable hash shards prevent ranking-order changes from moving a security's
    # forecast into a different ledger on the next date or after cohort expansion.
    shards: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        shards.setdefault(digest(candidate["key"].encode())[:2], []).append(candidate)
    for shard, observations in sorted(shards.items()):
        ledger = private_path(root, "expanded-forecasts", shard)
        ledger.mkdir(parents=True, exist_ok=True)
        existing: dict[tuple[str, str], dict[str, Any]] = {}
        if (ledger / "experimental-v2-prospective.sqlite3").exists():
            with forward._connection(ledger) as connection:
                for row in connection.execute(
                    "SELECT * FROM experimental_forecasts WHERE model_id=?", (model["model_id"],)
                ):
                    saved = forward._verified(row)
                    existing[saved["key"], saved["session"]] = saved
        unseen: list[dict[str, Any]] = []
        for observation in observations:
            prior = existing.get((observation["key"], observation["session"]))
            observation["prospective_record_already_frozen"] = prior is not None
            if prior is None:
                unseen.append(observation)
            else:
                # A larger discovery cohort cannot rewrite the earlier decision,
                # source, ranks, input snapshot or its original recorded clock.
                existing_forecasts += 1
                observation["original_forecast_recorded_at"] = prior["recorded_at"]
                observation["current_score_matches_frozen_vector"] = (
                    prior["feature_hash"] == observation["feature_hash"]
                )
        if not unseen:
            continue
        written = forward.append_forecasts(
            ledger,
            model_id=model["model_id"],
            dataset_id=frame["dataset_id"],
            protocol_id=model["protocol_id"],
            scores=unseen,
            source_observed_at=frame["source_observed_at"],
        )
        forecasts += written["inserted"]
    result = {
        "family": FAMILY,
        "dataset_id": frame["dataset_id"],
        "model_id": model["model_id"],
        "model_sha256": evaluation["model_sha256"],
        "feature_version": LOCAL_FEATURE_VERSION,
        "generated_at": decision.isoformat(),
        "observation_session": latest,
        "source": "UPSTOX_OFFICIAL_HISTORICAL_CANDLES",
        "forecast_horizon": "NEXT_OPEN_TO_FIFTH_OBSERVED_CLOSE_PRICE_COMPONENT",
        "classification": "EXPERIMENTAL_UNVALIDATED",
        "calibration_status": "NOT_ESTABLISHED",
        "edge_status": "NO_DEMONSTRATED_EDGE",
        "original_evaluation": evaluation,
        "candidates": candidates,
        "scored_securities": len(candidates),
        "coverage_snapshot": coverage(root, frame),
        "new_forecasts": forecasts,
        "existing_forecasts_preserved": existing_forecasts,
        "expanded_global_prospective_rank_evaluation": (
            "PENDING_SEPARATELY_REGISTERED_COHORT_SELECTION_PROTOCOL_AND_MATURED_OUTCOMES"
        ),
        "exclusions": [
            item
            for item in features.exclusions
            if item["session"] == latest and item["reason"] != "TARGET_UNMATURED"
        ],
        "original_forecasts_modified": False,
        "accepted_current_rankings": 0,
        "applicability": "EXPANDED_CURRENT_COHORT_EXTRAPOLATION_NOT_ORIGINAL_EVALUATION",
        "corporate_action_coverage_complete": False,
        "historical_pit_membership": False,
        "decision_clock": clock,
    }
    directory = private_path(root, "scores")
    directory.mkdir(exist_ok=True)
    target = directory / (uuid.uuid4().hex + ".json")
    _checked(target, result)
    _pointer(root, "scores-latest.json", target)
    from workers.nse_market.forward_cohort import freeze_current

    freeze_current(root)
    publish_workspace(root)
    return result


def _source_fingerprint(root: Path) -> str:
    """Bind saved summaries to source bytes without repeating candle parsing."""
    selected = [
        private_path(root, "seed.json"),
        private_path(root, "seed.json.sha256"),
        private_path(root, "plan-latest.json"),
    ]
    for folder in ("instruments", "daily", "calendar", "session-links", "plans"):
        selected.extend(
            path
            for path in private_path(root, folder).rglob("*")
            if path.is_file()
            and path.suffix in {".json", ".sha256"}
            and "history-attempts" not in path.parts
            and "action-attempts" not in path.parts
            and "publication-attempts" not in path.parts
        )
    return digest(
        encoded(
            {
                path.relative_to(root).as_posix(): digest(path.read_bytes())
                for path in sorted(set(selected))
            }
        )
    )


def publish_workspace(root: Path) -> dict[str, Any]:
    """Publish saved checksummed capture+inference summaries, no source acquisition."""
    scores = _pointed(root, "scores-latest.json")
    if scores.get("coverage_snapshot") is not None:
        covered = scores["coverage_snapshot"]
    else:
        captured = _pointed(root, "capture-latest.json")
        if captured.get("dataset_id") != scores["dataset_id"]:
            raise ValueError("MATCHING_CAPTURE_AND_SCORE_SNAPSHOT_REQUIRED_FOR_PUBLISH")
        fields = (
            "configured_securities",
            "validated_historical_securities",
            "observations",
            "start",
            "end",
            "observed_sessions",
            "missing_observed_cohort_slots",
            "official_calendar_complete",
            "per_security",
            "not_observed",
            "dataset_id",
            "provider_queried_securities",
            "provider_accessible_securities",
            "provider_reported_observations",
            "calendar_quarantined_observations",
        )
        covered = {key: captured[key] for key in fields if key in captured}
    covered = dict(covered)
    covered.update(
        technical_feature_eligible_securities=len(scores["candidates"]),
        experimental_scored_securities=len(scores["candidates"]),
        independently_accepted_securities=0,
    )
    value = {
        "state": "AVAILABLE",
        "coverage": covered,
        "scores": scores,
        "candidates": scores["candidates"],
        "classification": "EXPERIMENTAL_UNVALIDATED",
        "accepted_current_rankings": 0,
        "automatic_acquisition_enabled": False,
        "permission_reference": PERMISSION,
        "storage_bytes": _bytes(root),
        "technical_exclusions": scores["exclusions"],
        "current_feature_date": scores["observation_session"],
        "score_snapshot_current": True,
    }
    if private_path(root, "global-cohort-latest.json").exists():
        from workers.nse_market.forward_cohort import summary

        value["prospective_cohort"] = summary(root)
    folder = private_path(root, "workspace-snapshots")
    folder.mkdir(exist_ok=True)
    target = folder / (uuid.uuid4().hex + ".json")
    _checked(target, {"source_fingerprint": _source_fingerprint(root), "value": value})
    _pointer(root, "workspace-latest.json", target)
    _WORKSPACE_CACHE.pop(str(root.resolve()), None)
    return {
        "state": "SAVED_WORKSPACE_PUBLISHED",
        "api_calls": 0,
        "observations": covered["observations"],
        "scored_securities": len(scores["candidates"]),
    }


def workspace(root: Path, v2_root: Path | None = None) -> dict[str, Any]:
    """Saved source evidence only. No provider, fitting, forecasting or implicit refresh."""
    if not (root / "plan-latest.json").exists():
        return {"state": "NOT_CONFIGURED", "candidates": [], "accepted_current_rankings": 0}
    pointers = [
        private_path(root, name)
        for name in (
            "plan-latest.json",
            "capture-latest.json",
            "scores-latest.json",
            "daily-latest.json",
            "workspace-latest.json",
            "operational-latest.json",
            "global-cohort-latest.json",
            "task-registration-latest.json",
            "task-observation-latest.json",
        )
    ]
    cache_key = tuple(
        (str(path), path.stat().st_mtime_ns, path.stat().st_size)
        if path.exists()
        else (str(path), None)
        for path in pointers
    )
    cached = _WORKSPACE_CACHE.get(str(root.resolve()))
    if cached is not None and cached[0] == cache_key and time.monotonic() - cached[1] < 60:
        return copy.deepcopy(cached[2])
    if private_path(root, "workspace-latest.json").exists():
        published = _pointed(root, "workspace-latest.json")
        if published["source_fingerprint"] == _source_fingerprint(root):
            value = published["value"]
            value["operations"] = _operations(root)
            _WORKSPACE_CACHE[str(root.resolve())] = (cache_key, time.monotonic(), value)
            return copy.deepcopy(value)
    frame = snapshot(root)
    result = coverage(root, frame)
    _, _, features = _latest_features(frame)
    latest = frame["sessions"][-1]
    scores = (
        _pointed(root, "scores-latest.json") if (root / "scores-latest.json").exists() else None
    )
    result.update(
        technical_feature_eligible_securities=sum(
            sample.session == latest for sample in features.samples
        ),
        experimental_scored_securities=len(scores["candidates"]) if scores else 0,
        independently_accepted_securities=0,
    )
    value = {
        "state": "AVAILABLE",
        "coverage": result,
        "scores": scores,
        "candidates": scores["candidates"] if scores else [],
        "classification": "EXPERIMENTAL_UNVALIDATED",
        "accepted_current_rankings": 0,
        "automatic_acquisition_enabled": False,
        "permission_reference": PERMISSION,
        "storage_bytes": _bytes(root),
        "technical_exclusions": [
            item
            for item in features.exclusions
            if item["session"] == latest and item["reason"] != "TARGET_UNMATURED"
        ],
        "current_feature_date": latest,
        "score_snapshot_current": scores is not None
        and scores["dataset_id"] == frame["dataset_id"],
        "operations": _operations(root),
    }
    _WORKSPACE_CACHE[str(root.resolve())] = (cache_key, time.monotonic(), value)
    return copy.deepcopy(value)


def _operations(root: Path) -> dict[str, Any]:
    if not private_path(root, "operational-latest.json").exists():
        return {"state": "NOT_CONFIGURED", "automatic_acquisition_enabled": False}
    saved = _pointed(root, "operational-latest.json")
    fields = (
        "state",
        "started_at",
        "completed_at",
        "source_requests_last_run",
        "error_code",
        "message",
        "automatic_acquisition_enabled",
        "scheduled",
        "reserved_request_ceiling",
        "source_publication_complete",
        "new_forecasts",
        "pending_forecasts",
        "matured_outcomes",
    )
    value = {key: saved[key] for key in fields if key in saved}
    value["last_completed"] = {
        key: saved.get(key)
        for key in (
            "run_id",
            "state",
            "started_at",
            "completed_at",
            "source_requests_last_run",
            "error_code",
            "stage",
        )
    }
    outcome = saved.get("outcome", {})
    value["collection"] = {
        key: outcome[key]
        for key in (
            "session",
            "already_observed",
            "pending_securities",
            "new_daily_observations",
            "identity_exclusions_pending_review",
            "failures",
        )
        if key in outcome
    }
    reservations = [_read(path) for path in (root / "operational/runs").glob("*.started.json")]
    runs = root / "operational/runs"
    attempts = {
        path.name.split(".")[0]: _read(path)
        for pattern in ("*.started.json", "*.attempt.json")
        for path in runs.glob(pattern)
    }
    terminal = {
        path.name.split(".")[0]
        for pattern in ("*.done.json", "*.interrupted.json")
        for path in runs.glob(pattern)
    }
    unfinished = [
        {
            "run_id": key,
            "started_at": attempt.get("started_at", attempt.get("clock_upper_at")),
            "state": "INCOMPLETE_NO_TERMINAL_RECEIPT",
            "actual_get_attempts": None,
            "reserved_get_attempts": next(
                (r["reserved_requests"] for r in reservations if r.get("run_id") == key), 0
            ),
            "worker_pid": attempt.get("worker_pid"),
        }
        for key, attempt in attempts.items()
        if key not in terminal
    ]
    value["unfinished_attempts_total"] = len(unfinished)
    value["unfinished_attempts"] = sorted(
        unfinished, key=lambda r: r["started_at"] or "", reverse=True
    )[:20]
    value["read_at"] = datetime.now(UTC).isoformat()
    from zoneinfo import ZoneInfo

    quota_day = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    today = [run for run in reservations if run["quota_day"] == quota_day]
    value["reservations"] = {
        "quota_day": quota_day,
        "collecting_attempts": len(today),
        "reserved_get_attempts": sum(run["reserved_requests"] for run in today),
        "reservations_are_not_actual_gets": True,
    }
    policy = saved.get("policy", {})
    value["budget"] = {
        key: policy[key]
        for key in (
            "expected_securities",
            "max_stocks_per_run",
            "max_requests_per_run",
            "max_requests_per_day",
            "max_runs_per_day",
            "cooldown_minutes",
            "cadence_ist",
            "missed_trigger_at_next_login",
            "policy_sha256",
        )
        if key in policy
    }
    if private_path(root, "task-registration-latest.json").exists():
        registration = _pointed(root, "task-registration-latest.json")
        verified = datetime.fromisoformat(registration["verified_at"])
        if verified.utcoffset() is None or verified > datetime.now(UTC):
            raise ValueError("SCHEDULER_VERIFICATION_TIME_REJECTED")
        if registration["state"] == "REGISTERED_ENABLED_LAST_VERIFIED":
            approval = _read(private_path(root, "operational", "collection-approval.json"))
            if (
                registration["policy_sha256"] != policy.get("policy_sha256")
                or registration["policy_sha256"] != approval["policy_sha256"]
                or approval["approved_by"] != "LOCAL_OPERATOR_EXPLICIT_USER_APPROVAL"
                or registration["fixed_scope"] != policy["expected_securities"]
                or not registration["least_privilege"]
                or not registration["interactive_token"]
            ):
                raise ValueError("SCHEDULER_REGISTRATION_APPROVAL_POLICY_MISMATCH")
        value["scheduler"] = registration
    if (root / "task-observation-latest.json").exists():
        from workers.nse_market.task_observation import validate

        observation = _pointed(root, "task-observation-latest.json")
        validate(observation, str(policy.get("policy_sha256", "")))
        value["windows_task"] = observation
    return value
