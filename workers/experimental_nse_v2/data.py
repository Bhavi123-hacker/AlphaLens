"""Isolated, immutable private V2 observations and conservative quality evidence."""

import json
import re
import uuid
from contextlib import suppress
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from workers.experimental_nse.acquire import (
    COHORT,
    END,
    PERMISSION,
    START,
    digest,
    encoded,
    initialize,
    private_path,
    replay,
    write_new,
)
from workers.providers.calendar import nse_timing
from workers.providers.daily_clock import guard
from workers.providers.store import ProviderStore
from workers.providers.upstox import Reply, UpstoxClient, instrument_master

from alphalens_data.daily.storage import Store
from alphalens_data.errors import DataContractError
from alphalens_data.providers.multi_adapters import parse_daily
from alphalens_data.providers.multi_contracts import Instrument

EXTRA = (
    "ADANIPORTS",
    "APOLLOHOSP",
    "ASIANPAINT",
    "BAJFINANCE",
    "BAJAJFINSV",
    "BEL",
    "BPCL",
    "COALINDIA",
    "DIVISLAB",
    "EICHERMOT",
    "HEROMOTOCO",
    "INDUSINDBK",
    "JSWSTEEL",
    "SBILIFE",
    "HDFCLIFE",
    "SHRIRAMFIN",
    "SIEMENS",
    "TITAN",
    "TRENT",
    "UPL",
)
BASIS = "UPSTOX_STAFF_CONFIRMED_SPLIT_BONUS_ADJUSTED_NOT_DIVIDEND"
FAMILY = "ALPHALENS_EXPERIMENTAL_NSE_V2"


def normalized(body: bytes, identity: Instrument, at: datetime) -> list[dict[str, Any]]:
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("V2_AWARE_SOURCE_RECEIPT_REQUIRED")
    return [
        {
            "key": identity.provider_key,
            "symbol": identity.symbol,
            "isin": identity.isin,
            "session": str(c.session),
            "open": str(c.open),
            "high": str(c.high),
            "low": str(c.low),
            "close": str(c.close),
            "volume": c.volume,
            "received_at": at.isoformat(),
            "raw_sha256": digest(body),
            "provider_candle_at": c.event_time.isoformat(),
        }
        for c in parse_daily(body, identity, at)
    ]


def action_facts(reply: Reply) -> dict[str, Any]:
    """No raw Fundamentals retention. Do not treat absent/ambiguous events as clean."""
    result: dict[str, Any] = {
        "state": reply.state,
        "received_at": reply.received_at.isoformat(),
        "source_sha256": digest(reply.body),
        "raw_retained": False,
        "complete": False,
        "hazard_dates": [],
        "events": 0,
        "unparsed_date_fields": 0,
    }
    if reply.state != "ACCEPTED" or reply.status != 200:
        return result
    try:
        data = json.loads(reply.body)
    except (ValueError, TypeError):
        data = None
    if (
        not isinstance(data, dict)
        or data.get("status") != "success"
        or not isinstance(data.get("data"), list)
    ):
        result["state"] = "ACTION_SCHEMA_UNAVAILABLE"
        return result
    dates = set()
    events = data["data"]
    for event in events:
        if (
            not isinstance(event, dict)
            or not isinstance(event.get("event_details", []), list)
            or any(not isinstance(item, dict) for item in event.get("event_details", []))
        ):
            result["state"] = "ACTION_SCHEMA_UNAVAILABLE"
            return result
        fields = [event.get("expiry_date")]
        fields.extend(
            item.get("value")
            for item in event.get("event_details", [])
            if isinstance(item, dict) and "date" in str(item.get("name", "")).lower()
        )
        for value in fields:
            if value is None or str(value).lower() in {"", "na", "n/a", "-"}:
                continue
            parsed = None
            with suppress(ValueError):
                parsed = datetime.fromisoformat(str(value).strip()).date()
            for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d %b %Y", "%d-%b-%Y", "%d %B %Y"):
                if parsed is not None:
                    break
                try:
                    parsed = datetime.strptime(str(value).strip(), pattern).date()
                    break
                except ValueError:
                    continue
            if parsed is None:
                result["unparsed_date_fields"] += 1
            else:
                dates.add(str(parsed))
    result.update(
        state="OBSERVED_ACTION_REFERENCE_NOT_EXHAUSTIVE",
        events=len(events),
        hazard_dates=sorted(dates),
    )
    return result


def quality(rows: list[dict[str, Any]], actions: dict[str, Any]) -> dict[str, Any]:
    if not rows:
        raise ValueError("V2_NONEMPTY_GENUINE_OBSERVATIONS_REQUIRED")
    by_key: dict[str, list[dict[str, Any]]] = {}
    values: dict[tuple[Any, ...], list[str]] = {}
    excluded: dict[str, set[str]] = {}
    anomalies = []
    for row in rows:
        by_key.setdefault(row["key"], []).append(row)
        values.setdefault(
            tuple(row[n] for n in ("session", "open", "high", "low", "close", "volume")), []
        ).append(row["key"])
    for key, observations in by_key.items():
        observations.sort(key=lambda r: r["session"])
        if len({r["session"] for r in observations}) != len(observations):
            raise ValueError("V2_DUPLICATE_SECURITY_SESSION_REJECTED")
        action = actions.get(key, {})
        excluded[key] = set(action.get("hazard_dates", []))
        if action.get("state") != "OBSERVED_ACTION_REFERENCE_NOT_EXHAUSTIVE" or action.get(
            "unparsed_date_fields", 0
        ):
            excluded[key].update(r["session"] for r in observations)
            anomalies.append({"key": key, "reason": "ACTION_REFERENCE_UNAVAILABLE_OR_UNPARSED"})
        for before, after in zip(observations, observations[1:], strict=False):
            gap = max(
                abs(float(after["open"]) / float(before["close"]) - 1),
                abs(float(after["close"]) / float(before["close"]) - 1),
            )
            if gap > 0.4:
                excluded[key].add(after["session"])
                anomalies.append(
                    {
                        "key": key,
                        "session": after["session"],
                        "reason": "UNEXPLAINED_PRICE_GAP_ABOVE_40_PERCENT",
                    }
                )
    duplicate_groups = 0
    for fields, keys in values.items():
        if len(set(keys)) > 1:
            duplicate_groups += 1
            for key in keys:
                excluded[key].add(fields[0])
    sessions = sorted({r["session"] for r in rows})
    return {
        "observations": len(rows),
        "securities": len(by_key),
        "sessions": len(sessions),
        "start": sessions[0],
        "end": sessions[-1],
        "missing_cohort_slots": len(by_key) * len(sessions) - len(rows),
        "cross_security_identical_ohlcv_groups": duplicate_groups,
        "anomalies": anomalies,
        "excluded_sessions": {k: sorted(v) for k, v in excluded.items()},
        "action_coverage_complete": False,
        "official_calendar_complete": False,
        "identity": "CURRENT_FIXED_COHORT_NOT_HISTORICAL_MEMBERSHIP",
    }


def acquire(root: Path, v1_root: Path, provider_root: Path) -> dict[str, Any]:
    initialize(root)
    target = private_path(root, "dataset.json")
    if target.exists():
        return load(root)
    clock = guard()
    original = replay(v1_root)
    rows = original["rows"].copy()
    folder = private_path(root, "raw")
    folder.mkdir()
    # Preserve a self-contained exact-byte copy; V1's original snapshot never changes.
    base = private_path(root, "base-v1")
    base.mkdir()
    for path in (v1_root / "snapshot-v1").iterdir():
        if path.is_file():
            write_new(base / path.name, path.read_bytes())
    client = UpstoxClient(ProviderStore(provider_root), budget=80, retries=0)
    master_reply = client.get("instruments")
    identities, _ = instrument_master(master_reply, require_reliance=False)
    write_new(folder / "master.json.gz", master_reply.body)
    selected, failures, payloads = [], [], []
    for symbol in (*COHORT, *EXTRA):
        matches = [i for i in identities if i.symbol == symbol]
        if len(matches) != 1:
            failures.append({"symbol": symbol, "reason": "EXACT_CURRENT_IDENTITY_UNAVAILABLE"})
            continue
        identity = matches[0]
        selected.append(identity)
        if symbol in EXTRA:
            reply = client.get("candles", key=identity.provider_key, start=START, end=END)
            if reply.state != "ACCEPTED":
                failures.append({"symbol": symbol, "reason": reply.state})
                continue
            parsed = normalized(reply.body, identity, reply.received_at)
            if any(not str(START) <= r["session"] <= str(END) for r in parsed):
                raise ValueError("V2_HISTORY_OUTSIDE_DECLARED_RANGE")
            filename = str(identity.isin) + ".json"
            write_new(folder / filename, reply.body)
            payloads.append(
                {
                    "filename": filename,
                    "sha256": digest(reply.body),
                    "identity": identity.model_dump(mode="json"),
                    "received_at": reply.received_at.isoformat(),
                }
            )
            rows.extend(parsed)
    actions = {}
    for identity in selected:
        reply = client.get("actions", key=identity.provider_key)
        actions[identity.provider_key] = action_facts(reply)
        if reply.status in {401, 403, 429}:
            failures.append({"reason": reply.state, "operation": "actions"})
            break
    rows.sort(key=lambda r: (r["key"], r["session"]))
    report = quality(rows, actions)
    dataset = {
        "family": FAMILY,
        "permission_reference": PERMISSION,
        "clock": clock,
        "base_v1_dataset_id": original["dataset_id"],
        "rows": rows,
        "sessions": sorted({r["session"] for r in rows}),
        "actions": actions,
        "identities": [i.model_dump(mode="json") for i in selected],
        "price_basis": BASIS,
        "price_basis_evidence": "UPSTOX_17456_POST5_AND_17694_POST3",
        "source_observed_at": max(r["received_at"] for r in rows),
        "quality": report,
        "historical_payloads": payloads,
        "failures": failures,
        "api_calls": client.calls,
        "raw_action_payloads_retained": False,
        "base_files": {p.name: digest(p.read_bytes()) for p in base.iterdir() if p.is_file()},
        "master_sha256": digest(master_reply.body),
    }
    dataset["dataset_id"] = digest(encoded(dataset))
    body = encoded(dataset)
    write_new(target, body)
    write_new(root / "dataset.sha256", digest(body).encode())
    return load(root)


def load(root: Path) -> dict[str, Any]:
    initialize(root)
    body = private_path(root, "dataset.json").read_bytes()
    if digest(body) != private_path(root, "dataset.sha256").read_text():
        raise ValueError("V2_DATASET_CHECKSUM_REJECTED")
    data = json.loads(body)
    if not isinstance(data, dict):
        raise ValueError("V2_DATASET_OBJECT_REQUIRED")
    if data["dataset_id"] != digest(encoded({k: v for k, v in data.items() if k != "dataset_id"})):
        raise ValueError("V2_DATASET_ID_REJECTED")
    for name, checksum in data["base_files"].items():
        if digest(private_path(root, "base-v1", name).read_bytes()) != checksum:
            raise ValueError("V2_BASE_SOURCE_CHECKSUM_REJECTED")
    if digest(private_path(root, "raw", "master.json.gz").read_bytes()) != data["master_sha256"]:
        raise ValueError("V2_MASTER_CHECKSUM_REJECTED")
    for entry in data["historical_payloads"]:
        if digest(private_path(root, "raw", entry["filename"]).read_bytes()) != entry["sha256"]:
            raise ValueError("V2_HISTORICAL_SOURCE_CHECKSUM_REJECTED")
    source_rows = json.loads(private_path(root, "base-v1", "normalized.json").read_bytes())["rows"]
    for entry in data["historical_payloads"]:
        identity = Instrument.model_validate(entry["identity"])
        if entry["filename"] != str(identity.isin) + ".json":
            raise ValueError("V2_SOURCE_IDENTITY_PATH_REJECTED")
        source_rows.extend(
            normalized(
                private_path(root, "raw", entry["filename"]).read_bytes(),
                identity,
                datetime.fromisoformat(entry["received_at"]),
            )
        )
    source_rows.sort(key=lambda row: (row["key"], row["session"]))
    if source_rows != data["rows"] or quality(source_rows, data["actions"]) != data["quality"]:
        raise ValueError("V2_SOURCE_NORMALIZATION_OR_QUALITY_REPLAY_CHANGED")
    return data


def timing_fact(reply: Reply, day: date) -> dict[str, Any] | None:
    body = json.loads(reply.body)
    if (
        reply.state != "ACCEPTED"
        or reply.status != 200
        or not isinstance(body, dict)
        or body.get("status") != "success"
        or not isinstance(body.get("data"), list)
        or len(body["data"]) > 32
        or any(
            not isinstance(row, dict) or not isinstance(row.get("exchange"), str)
            for row in body["data"]
        )
    ):
        raise ValueError("V2_OFFICIAL_TIMING_UNAVAILABLE")
    if not any(row.get("exchange") == "NSE" for row in body["data"]):
        return None
    timing = nse_timing(reply, day)
    return {
        "session": str(day),
        "open_at": timing["start"],
        "close_at": timing["end"],
        "source": "UPSTOX_OFFICIAL_MARKET_TIMINGS",
        "source_sha256": digest(reply.body),
        "source_received_at": reply.received_at.isoformat(),
    }


def closed_current(
    root: Path,
    provider_root: Path,
    *,
    session_date: date | None = None,
    client_factory: Any = None,
    session_reply: Reply | None = None,
) -> dict[str, Any]:
    """Manual append-only capture; prior source snapshots and pending attempts remain exact."""
    initialize(root)
    private_path(root, "capture-control", "worker.lock")
    with Store(private_path(root, "capture-control")).lock():
        return _closed_current(
            root,
            provider_root,
            session_date=session_date,
            client_factory=client_factory,
            session_reply=session_reply,
        )


def _closed_current(
    root: Path,
    provider_root: Path,
    *,
    session_date: date | None = None,
    client_factory: Any = None,
    session_reply: Reply | None = None,
) -> dict[str, Any]:
    parent = load_current(root)
    clock = guard()
    local_day = date.fromisoformat(clock["session_date"])
    today = session_date or local_day
    if today > local_day or (local_day - today).days > 31:
        raise ValueError("V2_BOUNDED_PAST_OR_CURRENT_CAPTURE_REQUIRED")
    if parent["sessions"][-1] > str(today):
        raise ValueError("V2_COLLECTION_DATE_ROLLBACK")
    expected_keys = {identity["provider_key"] for identity in parent["identities"]}
    if not 1 <= len(expected_keys) <= 50 or len(expected_keys) != len(parent["identities"]):
        raise ValueError("V2_BOUNDED_PREDECLARED_CAPTURE_COHORT_REQUIRED")
    already_observed = {row["key"] for row in parent["rows"] if row["session"] == str(today)}
    if expected_keys <= already_observed:
        return {**parent, "last_collection_api_calls": 0, "collection_replayed": True}
    resume = _read_checkpoint(root, parent["dataset_id"], today)
    if resume is not None:
        completed = private_path(root, "captures", resume["capture_id"], "current.json")
        if completed.exists() and private_path(completed.parent, "current.sha256").exists():
            retained = _replay_current(
                root, completed, private_path(completed.parent, "raw"), parent
            )
            if datetime.fromisoformat(
                retained["session_timing"]["close_at"]
            ) >= datetime.fromisoformat(clock["lower_at"]):
                raise ValueError("V2_CURRENT_SESSION_NOT_COMPLETED")
            _publish_capture(root, completed.parent)
            return {**retained, "last_collection_api_calls": 0, "collection_replayed": True}
    # Preserve the original transport's <=100-per-client ceiling. Both clients
    # reserve against the same provider quota ledger; total explicit budget110.
    factory = client_factory or UpstoxClient
    client = factory(ProviderStore(provider_root), budget=60, retries=0)
    session_reply = session_reply or client.get("timings", end=today)
    session = timing_fact(session_reply, today)
    if session is None or datetime.fromisoformat(session["close_at"]) >= datetime.fromisoformat(
        clock["lower_at"]
    ):
        raise ValueError("V2_CURRENT_SESSION_NOT_COMPLETED")
    capture_id = uuid.uuid4().hex
    captures = private_path(root, "captures")
    captures.mkdir(exist_ok=True)
    folder = private_path(root, "captures", capture_id)
    folder.mkdir()
    evidence = private_path(root, "captures", capture_id, "raw")
    evidence.mkdir()
    write_new(evidence / (str(today) + ".json"), session_reply.body)
    timing_receipts = {
        str(today): {
            "sha256": digest(session_reply.body),
            "received_at": session_reply.received_at.isoformat(),
        }
    }
    next_session = None
    closed_dates: list[str] = []
    for offset in range(1, 9):
        day = today + timedelta(days=offset)
        reply = client.get("timings", end=day)
        fact = timing_fact(reply, day)
        write_new(evidence / (str(day) + ".json"), reply.body)
        timing_receipts[str(day)] = {
            "sha256": digest(reply.body),
            "received_at": reply.received_at.isoformat(),
        }
        if fact is not None:
            next_session = {
                **fact,
                "previous_session": str(today),
                "intervening_dates_verified_closed": True,
                "closed_dates": closed_dates,
            }
            break
        closed_dates.append(str(day))
    if next_session is None:
        raise ValueError("V2_NEXT_OFFICIAL_OPEN_UNAVAILABLE")
    master_reply = client.get("instruments")
    revalidated_master_at = master_reply.received_at.isoformat()
    if resume is not None:
        if master_reply.state != "ACCEPTED" or master_reply.status != 200:
            raise DataContractError("UPSTOX_MASTER_UNAVAILABLE")
        if digest(master_reply.body) != resume["master_sha256"] or any(
            resume[field][name] != value[name]
            for field, value in (("session_timing", session), ("next_session_timing", next_session))
            for name in ("session", "open_at", "close_at")
        ):
            raise ValueError("V2_CHECKPOINT_MASTER_OR_TIMING_REVISION_REQUIRES_REVIEW")
        # Revalidate today's master, but retain the original identity evidence time
        # needed to replay already received candles without rewriting timestamps.
        master_reply = upstox_reply(master_reply.body, resume["master_received_at"])
    identities, _ = instrument_master(master_reply, require_reliance=False)
    write_new(evidence / "master.json.gz", master_reply.body)
    action_client = factory(ProviderStore(provider_root), budget=50, retries=0)
    rows, failures, receipts = parent["rows"].copy(), [], []
    actions = (resume["actions"] if resume is not None else parent["actions"]).copy()
    retained_keys = set()
    if resume is not None:
        old_evidence = private_path(root, "captures", resume["capture_id"], "raw")
        for receipt in resume["receipts"]:
            identity = Instrument.model_validate(receipt["identity"])
            if (
                identity.provider_key not in expected_keys
                or identity.provider_key in already_observed
            ):
                raise ValueError("V2_CHECKPOINT_PARENT_COHORT_CONFLICT")
            raw = private_path(old_evidence, receipt["filename"]).read_bytes()
            write_new(evidence / receipt["filename"], raw)
            rows.extend(normalized(raw, identity, datetime.fromisoformat(receipt["received_at"])))
            receipts.append(receipt)
            retained_keys.add(identity.provider_key)
    for original in parent["identities"]:
        matches = [
            i
            for i in identities
            if i.provider_key == original["provider_key"]
            and i.symbol == original["symbol"]
            and i.isin == original["isin"]
        ]
        if len(matches) != 1:
            failures.append({"key": original["provider_key"], "reason": "CURRENT_IDENTITY_CHANGED"})
            actions[original["provider_key"]] = {"state": "CURRENT_IDENTITY_CHANGED"}
            continue
        identity = matches[0]
        action_reply = action_client.get("actions", key=identity.provider_key)
        fresh_action = action_facts(action_reply)
        previous_action = actions.get(identity.provider_key, {})
        fresh_action["hazard_dates"] = sorted(
            set(previous_action.get("hazard_dates", [])) | set(fresh_action["hazard_dates"])
        )
        fresh_action["previous_reference_source_sha256"] = previous_action.get("source_sha256")
        fresh_action["includes_previous_capture_hazards"] = True
        actions[identity.provider_key] = fresh_action
        if action_reply.status in {401, 403, 429}:
            failures.append({"key": identity.provider_key, "reason": action_reply.state})
            break
        if identity.provider_key in already_observed or identity.provider_key in retained_keys:
            continue
        reply = (
            client.get("intraday_candles", key=identity.provider_key)
            if today == local_day
            else client.get("candles", key=identity.provider_key, start=today, end=today)
        )
        if reply.state != "ACCEPTED":
            failures.append({"key": identity.provider_key, "reason": reply.state})
            if reply.status in {401, 403, 429}:
                break
            continue
        try:
            parsed = normalized(reply.body, identity, reply.received_at)
        except (ValueError, TypeError, DataContractError):
            failures.append(
                {"key": identity.provider_key, "reason": "CURRENT_DAILY_CANDLE_SCHEMA_REJECTED"}
            )
            continue
        if len(parsed) != 1 or parsed[0]["session"] != str(today):
            failures.append(
                {
                    "key": identity.provider_key,
                    "reason": "CURRENT_DAILY_CANDLE_MISSING_OR_WRONG_DATE",
                }
            )
            continue
        filename = str(identity.isin) + ".json"
        write_new(evidence / filename, reply.body)
        rows.extend(parsed)
        receipts.append(
            {
                "filename": filename,
                "sha256": digest(reply.body),
                "received_at": reply.received_at.isoformat(),
                "identity": identity.model_dump(mode="json"),
            }
        )
        _write_checkpoint(
            root,
            folder,
            {
                "parent_dataset_id": parent["dataset_id"],
                "session": str(today),
                "master_sha256": digest(master_reply.body),
                "master_received_at": master_reply.received_at.isoformat(),
                "session_timing": session,
                "next_session_timing": next_session,
                "timing_receipts": timing_receipts,
                "receipts": receipts,
                "actions": actions,
            },
        )
    rows.sort(key=lambda r: (r["key"], r["session"]))
    if not receipts:
        pending = {
            "state": "PROVIDER_PUBLICATION_OR_COVERAGE_PENDING",
            "session": str(today),
            "provider_calls": client.calls + action_client.calls,
            "new_observations": 0,
            "failures": failures,
            "clock": clock,
            "source_received_at": master_reply.received_at.isoformat(),
        }
        write_new(folder / "pending.json", encoded(pending))
        return {
            **parent,
            "collection_pending": pending,
            "last_collection_api_calls": client.calls + action_client.calls,
            "collection_replayed": False,
        }
    parent_pointer = private_path(root, "current-latest.json")
    if parent_pointer.exists():
        previous = json.loads(parent_pointer.read_bytes())
        parent_capture_id = previous["capture_id"]
        parent_capture_sha256 = previous["sha256"]
    elif private_path(root, "current.json").exists():
        parent_capture_id = "LEGACY_CURRENT"
        parent_capture_sha256 = digest(private_path(root, "current.json").read_bytes())
    else:
        parent_capture_id = None
        parent_capture_sha256 = None
    result = {
        **parent,
        "parent_dataset_id": parent["dataset_id"],
        "base_dataset_id": parent.get("base_dataset_id", load(root)["dataset_id"]),
        "parent_capture_id": parent_capture_id,
        "parent_capture_sha256": parent_capture_sha256,
        "capture_id": capture_id,
        "rows": rows,
        "actions": actions,
        "sessions": sorted({r["session"] for r in rows}),
        "session_timing": session,
        "next_session_timing": next_session,
        "current_receipts": receipts,
        "timing_receipts": timing_receipts,
        "current_master_sha256": digest(master_reply.body),
        "current_master_received_at": master_reply.received_at.isoformat(),
        "current_master_revalidated_at": revalidated_master_at,
        "resumed_checkpoint_sha256": resume["checkpoint_sha256"] if resume else None,
        "resumed_candle_count": len(retained_keys),
        "source_observed_at": max(r["received_at"] for r in rows),
        "quality": quality(rows, actions),
        "current_failures": failures,
        "current_api_calls": client.calls + action_client.calls,
        "current_request_budget": 110,
        "capture_operation": "CURRENT_DAY_DAILY"
        if today == local_day
        else "HISTORICAL_DAILY_CATCHUP",
        "current_clock": clock,
        "current_finality": "PROVIDER_AFTER_SESSION_CLOSE_NOT_CERTIFIED_FINAL",
    }
    result.pop("collection_pending", None)
    result.pop("last_collection_api_calls", None)
    result.pop("collection_replayed", None)
    result.pop("dataset_id", None)
    result["dataset_id"] = digest(encoded(result))
    body = encoded(result)
    write_new(folder / "current.json", body)
    write_new(folder / "current.sha256", digest(body).encode())
    _publish_capture(root, folder)
    return {
        **load_current(root),
        "last_collection_api_calls": client.calls + action_client.calls,
        "collection_replayed": False,
    }


def load_current(root: Path) -> dict[str, Any]:
    """Exact private current-source replay, never transport or timestamp rewriting."""
    parent = load(root)
    pointer = private_path(root, "current-latest.json")
    if pointer.exists():
        value = json.loads(pointer.read_bytes())
        if not isinstance(value, dict) or set(value) != {"capture_id", "sha256"}:
            raise ValueError("V2_CAPTURE_POINTER_REJECTED")
        return _load_capture(root, value["capture_id"], value["sha256"], parent, set())
    return _load_legacy_current(root, parent)


def _load_legacy_current(root: Path, parent: dict[str, Any]) -> dict[str, Any]:
    path = private_path(root, "current.json")
    if not path.exists():
        return parent
    return _replay_current(root, path, private_path(root, "current-raw"), parent)


def dataset_versions(root: Path) -> set[str]:
    """Only verified immutable ancestors can underlie older saved research scores."""
    current = load_current(root)
    versions = {load(root)["dataset_id"], current["dataset_id"]}
    while current.get("capture_id"):
        previous = current.get("parent_capture_id")
        if previous == "LEGACY_CURRENT":
            current = json.loads(private_path(root, "current.json").read_bytes())
        elif previous:
            current = json.loads(
                private_path(root, "captures", previous, "current.json").read_bytes()
            )
        else:
            break
        versions.add(current["dataset_id"])
    return versions


def _load_capture(
    root: Path,
    capture_id: Any,
    checksum: Any,
    base: dict[str, Any],
    seen: set[str],
) -> dict[str, Any]:
    if (
        not isinstance(capture_id, str)
        or re.fullmatch(r"[a-f0-9]{32}", capture_id) is None
        or capture_id in seen
        or len(seen) >= 256
        or not isinstance(checksum, str)
        or re.fullmatch(r"[a-f0-9]{64}", checksum) is None
    ):
        raise ValueError("V2_CAPTURE_CHAIN_PATH_CYCLE_OR_HASH_REJECTED")
    seen.add(capture_id)
    folder = private_path(root, "captures", capture_id)
    path = private_path(root, "captures", capture_id, "current.json")
    body = path.read_bytes()
    if digest(body) != checksum:
        raise ValueError("V2_CAPTURE_PARENT_HASH_REJECTED")
    item = json.loads(body)
    if (
        not isinstance(item, dict)
        or item.get("capture_id") != capture_id
        or item.get("base_dataset_id") != base["dataset_id"]
    ):
        raise ValueError("V2_CAPTURE_BASE_OR_ID_REJECTED")
    previous = item.get("parent_capture_id")
    if previous == "LEGACY_CURRENT":
        legacy = private_path(root, "current.json")
        if digest(legacy.read_bytes()) != item.get("parent_capture_sha256"):
            raise ValueError("V2_LEGACY_PARENT_HASH_REJECTED")
        parent = _load_legacy_current(root, base)
    elif previous is None:
        if item.get("parent_capture_sha256") is not None:
            raise ValueError("V2_BASE_PARENT_HASH_REJECTED")
        parent = base
    else:
        parent = _load_capture(root, previous, item.get("parent_capture_sha256"), base, seen)
    if parent["sessions"][-1] > item["session_timing"]["session"]:
        raise ValueError("V2_CAPTURE_SESSION_ROLLBACK")
    return _replay_current(root, path, private_path(folder, "raw"), parent)


def _replay_current(
    root: Path, path: Path, evidence: Path, parent: dict[str, Any]
) -> dict[str, Any]:
    body = path.read_bytes()
    if digest(body) != private_path(path.parent, "current.sha256").read_text():
        raise ValueError("V2_CURRENT_CHECKSUM_REJECTED")
    data = json.loads(body)
    if not isinstance(data, dict) or data.get("parent_dataset_id") != parent["dataset_id"]:
        raise ValueError("V2_CURRENT_PARENT_REJECTED")
    if data["dataset_id"] != digest(encoded({k: v for k, v in data.items() if k != "dataset_id"})):
        raise ValueError("V2_CURRENT_DATASET_ID_REJECTED")
    facts = {}
    for day, receipt in data["timing_receipts"].items():
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("V2_TIMING_DATE_REJECTED")
        raw = private_path(evidence, day + ".json").read_bytes()
        if digest(raw) != receipt["sha256"]:
            raise ValueError("V2_TIMING_CHECKSUM_REJECTED")
        facts[day] = timing_fact(
            Reply(200, raw, datetime.fromisoformat(receipt["received_at"]), "ACCEPTED"),
            date.fromisoformat(day),
        )
    observation, following = data["session_timing"], data["next_session_timing"]
    if (
        following["session"] <= observation["session"]
        or following.get("intervening_dates_verified_closed") is not True
    ):
        raise ValueError("V2_CONSECUTIVE_SESSION_CHAIN_REJECTED")
    if facts.get(observation["session"]) != observation:
        raise ValueError("V2_OBSERVATION_TIMING_REPLAY_CHANGED")
    if {
        k: v
        for k, v in following.items()
        if k not in {"previous_session", "intervening_dates_verified_closed", "closed_dates"}
    } != facts.get(following["session"]):
        raise ValueError("V2_NEXT_TIMING_REPLAY_CHANGED")
    between = []
    day = date.fromisoformat(observation["session"]) + timedelta(days=1)
    while day < date.fromisoformat(following["session"]):
        if str(day) not in facts or facts[str(day)] is not None:
            raise ValueError("V2_INTERVENING_CLOSED_SESSION_EVIDENCE_REQUIRED")
        between.append(str(day))
        day += timedelta(days=1)
    if (
        following["closed_dates"] != between
        or following["previous_session"] != observation["session"]
    ):
        raise ValueError("V2_CONSECUTIVE_SESSION_CHAIN_REJECTED")
    raw_master = private_path(evidence, "master.json.gz").read_bytes()
    if digest(raw_master) != data["current_master_sha256"]:
        raise ValueError("V2_CURRENT_MASTER_CHECKSUM_REJECTED")
    identities, _ = instrument_master(
        Reply(
            200, raw_master, datetime.fromisoformat(data["current_master_received_at"]), "ACCEPTED"
        ),
        require_reliance=False,
    )
    rows = parent["rows"].copy()
    for receipt in data["current_receipts"]:
        identity = Instrument.model_validate(receipt["identity"])
        if identity not in identities or receipt["filename"] != str(identity.isin) + ".json":
            raise ValueError("V2_CURRENT_IDENTITY_REJECTED")
        raw = private_path(evidence, receipt["filename"]).read_bytes()
        if digest(raw) != receipt["sha256"]:
            raise ValueError("V2_CURRENT_RAW_CHECKSUM_REJECTED")
        parsed = normalized(raw, identity, datetime.fromisoformat(receipt["received_at"]))
        if len(parsed) != 1 or parsed[0]["session"] != observation["session"]:
            raise ValueError("V2_CURRENT_RAW_DATE_REJECTED")
        rows.extend(parsed)
    rows.sort(key=lambda row: (row["key"], row["session"]))
    if (
        rows != data["rows"]
        or quality(rows, data["actions"]) != data["quality"]
        or max(row["received_at"] for row in rows) != data["source_observed_at"]
    ):
        raise ValueError("V2_CURRENT_NORMALIZATION_REPLAY_CHANGED")
    if datetime.fromisoformat(data["source_observed_at"]) > datetime.now(UTC):
        raise ValueError("V2_CURRENT_FUTURE_RECEIPT_REJECTED")
    return data


def collected_timings(root: Path) -> dict[str, dict[str, Any]]:
    """Return genuine dated timing facts from the verified capture ancestry only."""
    current = load_current(root)  # Verifies every ancestor and raw timing checksum.
    output: dict[str, dict[str, Any]] = {}
    closed: set[str] = set()

    def collect(item: dict[str, Any], evidence: Path) -> None:
        for day, receipt in item.get("timing_receipts", {}).items():
            raw = private_path(evidence, day + ".json").read_bytes()
            if digest(raw) != receipt["sha256"]:
                raise ValueError("V2_TIMING_CHECKSUM_REJECTED")
            fact = timing_fact(
                Reply(200, raw, datetime.fromisoformat(receipt["received_at"]), "ACCEPTED"),
                date.fromisoformat(day),
            )
            if fact is None:
                if day in output:
                    raise ValueError("V2_TIMING_REVISION_REQUIRES_EXPLICIT_REVIEW")
                closed.add(day)
                continue
            if day in closed:
                raise ValueError("V2_TIMING_REVISION_REQUIRES_EXPLICIT_REVIEW")
            previous = output.get(day)
            if previous is not None and any(
                previous[field] != fact[field] for field in ("open_at", "close_at")
            ):
                raise ValueError("V2_TIMING_REVISION_REQUIRES_EXPLICIT_REVIEW")
            output[day] = {**(previous or {}), **fact}
        observation = item.get("session_timing")
        following = item.get("next_session_timing")
        if observation is not None and following is not None:
            day = observation["session"]
            previous_link = output[day].get("next_verified_session")
            if previous_link is not None and previous_link != following["session"]:
                raise ValueError("V2_TIMING_REVISION_REQUIRES_EXPLICIT_REVIEW")
            output[day] = {
                **output[day],
                "next_verified_session": following["session"],
                "next_verified_open_at": following["open_at"],
                "intervening_dates_verified_closed": following["intervening_dates_verified_closed"],
                "verified_closed_dates": following["closed_dates"],
            }

    ancestry: list[tuple[dict[str, Any], Path]] = []
    item = current
    while item.get("capture_id"):
        capture_id = item["capture_id"]
        folder = private_path(root, "captures", capture_id)
        ancestry.append((item, private_path(folder, "raw")))
        previous = item.get("parent_capture_id")
        if previous == "LEGACY_CURRENT":
            item = json.loads(private_path(root, "current.json").read_bytes())
        elif previous is None:
            item = {}
        else:
            item = json.loads(private_path(root, "captures", previous, "current.json").read_bytes())
    if item.get("timing_receipts"):
        ancestry.append((item, private_path(root, "current-raw")))
    for evidence_item, evidence in reversed(ancestry):
        collect(evidence_item, evidence)
    return output


def _read_checkpoint(root: Path, parent_id: str, day: date) -> dict[str, Any] | None:
    pointer = private_path(root, "capture-control", "checkpoint-latest.json")
    if not pointer.exists():
        return None
    index = json.loads(pointer.read_bytes())
    capture = index.get("capture_id")
    filename = index.get("filename")
    if (
        not isinstance(capture, str)
        or not re.fullmatch(r"[0-9a-f]{32}", capture)
        or not isinstance(filename, str)
        or not re.fullmatch(r"checkpoint-[0-9a-f]{32}\.json", filename)
    ):
        raise ValueError("V2_CHECKPOINT_PATH_REJECTED")
    folder = private_path(root, "captures", capture)
    body = private_path(folder, filename).read_bytes()
    if digest(body) != index.get("sha256"):
        raise ValueError("V2_CHECKPOINT_CHECKSUM_REJECTED")
    saved = json.loads(body)
    if saved.get("parent_dataset_id") != parent_id or saved.get("session") != str(day):
        return None
    evidence = private_path(folder, "raw")
    master = private_path(evidence, "master.json.gz").read_bytes()
    if digest(master) != saved["master_sha256"]:
        raise ValueError("V2_CHECKPOINT_MASTER_REJECTED")
    identities, _ = instrument_master(
        upstox_reply(master, saved["master_received_at"]), require_reliance=False
    )
    for session, receipt in saved["timing_receipts"].items():
        raw = private_path(evidence, session + ".json").read_bytes()
        if digest(raw) != receipt["sha256"]:
            raise ValueError("V2_CHECKPOINT_TIMING_REJECTED")
        timing_fact(upstox_reply(raw, receipt["received_at"]), date.fromisoformat(session))
    keys = set()
    for receipt in saved["receipts"]:
        identity = Instrument.model_validate(receipt["identity"])
        if (
            identity not in identities
            or receipt["filename"] != str(identity.isin) + ".json"
            or identity.provider_key in keys
        ):
            raise ValueError("V2_CHECKPOINT_IDENTITY_REJECTED")
        keys.add(identity.provider_key)
        raw = private_path(evidence, receipt["filename"]).read_bytes()
        if digest(raw) != receipt["sha256"]:
            raise ValueError("V2_CHECKPOINT_CANDLE_CHECKSUM_REJECTED")
        parsed = normalized(raw, identity, datetime.fromisoformat(receipt["received_at"]))
        if len(parsed) != 1 or parsed[0]["session"] != str(day):
            raise ValueError("V2_CHECKPOINT_CANDLE_DATE_REJECTED")
    return {**saved, "checkpoint_sha256": digest(body), "capture_id": capture}


def upstox_reply(body: bytes, received_at: str) -> Reply:
    at = datetime.fromisoformat(received_at)
    if at.tzinfo is None or at > datetime.now(UTC):
        raise ValueError("V2_CHECKPOINT_RECEIPT_CLOCK_REJECTED")
    return Reply(200, body, at, "ACCEPTED")


def _write_checkpoint(root: Path, folder: Path, value: dict[str, Any]) -> None:
    """Append a flushed immutable checkpoint, then atomically replace its private pointer."""
    import os

    evidence = private_path(folder, "raw")
    files = [
        "master.json.gz",
        *(day + ".json" for day in value["timing_receipts"]),
        *(receipt["filename"] for receipt in value["receipts"]),
    ]
    for filename in files:
        with private_path(evidence, filename).open("r+b") as stream:
            stream.flush()
            os.fsync(stream.fileno())
    filename = "checkpoint-" + uuid.uuid4().hex + ".json"
    body = encoded(value)
    path = private_path(folder, filename)
    with path.open("xb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    if os.name != "nt":
        path.chmod(0o600)
    temporary = private_path(root, "capture-control", "checkpoint-" + uuid.uuid4().hex + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(
            encoded({"capture_id": folder.name, "filename": filename, "sha256": digest(body)})
        )
        stream.flush()
        os.fsync(stream.fileno())
    if os.name != "nt":
        temporary.chmod(0o600)
    temporary.replace(private_path(root, "capture-control", "checkpoint-latest.json"))


def _publish_capture(root: Path, folder: Path) -> None:
    import os

    pointer = private_path(root, "current-latest-" + uuid.uuid4().hex + ".tmp")
    write_new(
        pointer,
        encoded(
            {
                "capture_id": folder.name,
                "sha256": digest(private_path(folder, "current.json").read_bytes()),
            }
        ),
    )
    for path in (
        private_path(folder, "current.json"),
        private_path(folder, "current.sha256"),
        pointer,
    ):
        with path.open("r+b") as stream:
            stream.flush()
            os.fsync(stream.fileno())
    pointer.replace(private_path(root, "current-latest.json"))
