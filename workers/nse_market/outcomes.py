"""Offline prospective maturation from saved, source-verified evidence only.

The daily worker already reconciles after capture and on replay. This shared job
also supports an explicit offline retry without another market-data request.
Original forecasts and the separate original V2 ledger are never written.
"""

from __future__ import annotations

import re
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from alphalens_api.auth.permissions import verify
from alphalens_data.daily.storage import Store
from workers.experimental_nse.acquire import digest, private_path
from workers.experimental_nse.features import candle
from workers.experimental_nse_v2 import data, forward
from workers.experimental_nse_v2.features import HORIZON, TARGET_VERSION
from workers.nse_market import engine
from workers.providers.upstox import Reply


def _calendar(root: Path, day: str, cutoff: datetime) -> tuple[bool, dict[str, Any] | None]:
    path = private_path(root, "calendar", day + ".json")
    if not path.exists():
        return False, None
    record = engine._read(path)
    raw = bytes.fromhex(record["raw_hex"])
    received = forward._at(record["received_at"])
    if digest(raw) != record["raw_sha256"]:
        raise ValueError("OUTCOME_CALENDAR_RAW_CHECKSUM_REJECTED")
    if received > cutoff:
        return False, None
    return True, data.timing_fact(Reply(200, raw, received, "ACCEPTED"), date.fromisoformat(day))


def _timings(root: Path, cutoff: datetime) -> dict[str, dict[str, Any]]:
    """Raw official responses support every session and intervening closure."""
    timings: dict[str, dict[str, Any]] = {}
    cache: dict[str, tuple[bool, dict[str, Any] | None]] = {}

    def fact(day: str) -> tuple[bool, dict[str, Any] | None]:
        if day not in cache:
            cache[day] = _calendar(root, day, cutoff)
        return cache[day]

    for path in sorted(private_path(root, "session-links").glob("*.json")):
        link = engine._read(path)
        current, following = link["session_timing"], link["next_session_timing"]
        previous, next_day = current["session"], following["session"]
        if (
            path.stem != previous
            or following.get("previous_session") != previous
            or following.get("intervening_dates_verified_closed") is not True
            or not previous < next_day
            or (date.fromisoformat(next_day) - date.fromisoformat(previous)).days > 7
        ):
            raise ValueError("OUTCOME_CONSECUTIVE_SESSION_LINK_REJECTED")
        elapsed = (date.fromisoformat(next_day) - date.fromisoformat(previous)).days
        closed = [str(date.fromisoformat(previous) + timedelta(days=i)) for i in range(1, elapsed)]
        if following.get("closed_dates") != closed:
            raise ValueError("OUTCOME_EXHAUSTIVE_CLOSED_DATE_LIST_REQUIRED")
        available, before = fact(previous)
        next_available, after = fact(next_day)
        if not available or not next_available:
            continue
        if before is None or after is None:
            raise ValueError("OUTCOME_OPEN_SESSION_RAW_EVIDENCE_REJECTED")
        for claimed, actual in ((current, before), (following, after)):
            if any(
                claimed.get(name) != actual[name]
                for name in (
                    "session",
                    "open_at",
                    "close_at",
                    "source",
                    "source_sha256",
                    "source_received_at",
                )
            ):
                raise ValueError("OUTCOME_SESSION_LINK_RAW_LINEAGE_REJECTED")
        closed_available = True
        for day in closed:
            received, open_session = fact(day)
            if received and open_session is not None:
                raise ValueError("OUTCOME_CLAIMED_CLOSURE_IS_OPEN_SESSION")
            closed_available = closed_available and received
        if not closed_available:
            continue
        timings[previous] = {
            **before,
            "next_verified_session": next_day,
            "next_verified_open_at": after["open_at"],
            "intervening_dates_verified_closed": True,
            "verified_closed_dates": closed,
        }
        timings.setdefault(next_day, after)
    # Catch-up candles may cover a day for which no daily target run occurred.
    # Its raw official calendar response can still prove an adjacent edge; a
    # missing redundant summary must not permanently strand genuine outcomes.
    # Preserve and validate every existing summary above, and derive only from
    # complete raw evidence available at this source cutoff. No files are written.
    for path in sorted(private_path(root, "calendar").glob("*.json")):
        day = date.fromisoformat(path.stem).isoformat()
        available, observed = fact(day)
        if available and observed is not None:
            timings.setdefault(day, observed)
    days = sorted(timings)
    for previous, next_day in zip(days, days[1:], strict=False):
        elapsed = (date.fromisoformat(next_day) - date.fromisoformat(previous)).days
        if not 0 < elapsed <= 7:
            continue
        closed = [str(date.fromisoformat(previous) + timedelta(days=i)) for i in range(1, elapsed)]
        if not all(fact(day) == (True, None) for day in closed):
            continue
        current = timings[previous]
        if current.get("next_verified_session", next_day) != next_day:
            raise ValueError("OUTCOME_RAW_CONSECUTIVE_CHAIN_CONFLICT")
        timings[previous] = {
            **current,
            "next_verified_session": next_day,
            "next_verified_open_at": timings[next_day]["open_at"],
            "intervening_dates_verified_closed": True,
            "verified_closed_dates": closed,
        }
    return timings


def _ledgers(root: Path) -> list[tuple[Path, list[dict[str, Any]]]]:
    result = []
    for folder in sorted(private_path(root, "expanded-forecasts").glob("*")):
        path = private_path(
            root, "expanded-forecasts", folder.name, "experimental-v2-prospective.sqlite3"
        )
        if not path.exists():
            continue
        verify(folder)
        verify(path, directory=False)
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
            forecasts = [
                forward._verified(row)
                for row in conn.execute("SELECT * FROM experimental_forecasts")
            ]
            for row in conn.execute("SELECT * FROM experimental_outcomes"):
                forward._verified(row)
        result.append((folder, forecasts))
    return result


def _ready(
    forecast: dict[str, Any],
    frame: dict[str, Any],
    timings: dict[str, dict[str, Any]],
    slots: dict[tuple[str, str], dict[str, Any]],
    positions: dict[str, int],
) -> str:
    if forecast.get("prospective_eligible") is not True:
        return "INELIGIBLE_ORIGINAL_FORECAST"
    if forecast.get("target_version") != TARGET_VERSION or forecast.get("horizon") != HORIZON:
        return "UNSUPPORTED_ORIGINAL_TARGET_OR_HORIZON"
    retrieved = forward._at(frame["source_observed_at"])
    opening = forward._at(forecast["next_session_timing"]["open_at"])
    if (
        not forward._at(forecast["source_observed_at"])
        <= forward._at(forecast["inference_at"])
        <= forward._at(forecast["recorded_at"])
        < opening
    ):
        return "INELIGIBLE_ORIGINAL_CHRONOLOGY"
    if retrieved <= forward._at(forecast["recorded_at"]):
        return "LATER_SOURCE_RETRIEVAL_REQUIRED"
    index = positions.get(forecast["session"])
    required = frame["sessions"][index + 1 : index + 6] if index is not None else []
    if len(required) != 5 or required[0] != forecast["next_session_timing"]["session"]:
        return "FIVE_COMPLETE_SUBSEQUENT_SESSION_SLOTS_REQUIRED"
    previous = forecast["session"]
    if forecast["key"] not in frame["quality"]["excluded_sessions"]:
        return "ACTION_AND_QUALITY_ASSESSMENT_REQUIRED"
    hazards = frame["quality"]["excluded_sessions"][forecast["key"]]
    for day in required:
        fact, preceding = timings.get(day), timings.get(previous)
        if (
            not fact
            or not preceding
            or preceding.get("next_verified_session") != day
            or forward._at(fact["close_at"]) >= retrieved
        ):
            return "OFFICIAL_RAW_SESSION_AND_CLOSURE_CHAIN_REQUIRED"
        if previous == forecast["session"] and forward._at(fact["open_at"]) != opening:
            return "FROZEN_ENTRY_TIMING_REVISION_REQUIRES_REVIEW"
        row = slots.get((forecast["key"], day))
        if row is None:
            return "MISSING_SECURITY_TARGET_PRICE_SLOT"
        if row["symbol"] != forecast["symbol"]:
            return "SECURITY_IDENTITY_CONTINUITY_UNRESOLVED"
        if not forward._at(fact["close_at"]) < forward._at(row["received_at"]) <= retrieved:
            return "COMPLETED_SOURCE_PUBLICATION_REQUIRED"
        if day in hazards:
            return "KNOWN_ACTION_OR_QUALITY_EXCLUSION"
        previous = day
    return "READY_SOURCE_QUALIFIED_PRICE_REFERENCE_ONLY"


def prepare(
    root: Path, frame: dict[str, Any]
) -> tuple[dict[str, Any], list[tuple[Path, list[dict[str, Any]]]], dict[str, dict[str, Any]]]:
    """Zero-write preflight shared by preview, standalone retry and daily worker."""
    retrieved = forward._at(frame["source_observed_at"])
    if retrieved > datetime.now(UTC):
        raise ValueError("OUTCOME_SOURCE_RETRIEVAL_IN_FUTURE")
    sessions = frame["sessions"]
    if sessions != sorted(set(sessions)):
        raise ValueError("OUTCOME_SORTED_UNIQUE_SESSION_GRID_REQUIRED")
    ledgers = _ledgers(root)
    timings = _timings(root, retrieved) if ledgers else {}
    slots = {}
    for row in frame["rows"]:
        candle(row)
        key = (row["key"], row["session"])
        if key in slots:
            raise ValueError("OUTCOME_DUPLICATE_SECURITY_PRICE_SLOT")
        slots[key] = row
    positions = {day: i for i, day in enumerate(sessions)}
    reasons: dict[str, int] = {}
    ready = 0
    for _, forecasts in ledgers:
        for forecast in forecasts:
            status = _ready(forecast, frame, timings, slots, positions)
            reasons[status] = reasons.get(status, 0) + 1
            ready += status == "READY_SOURCE_QUALIFIED_PRICE_REFERENCE_ONLY"
    return (
        {
            "provider_requests": 0,
            "forecast_writes": 0,
            "eligible_price_references": ready,
            "expanded_ledgers": len(ledgers),
            "status_counts": reasons,
            "official_session_facts": len(timings),
            "source_observed_at": retrieved.isoformat(),
            "independent_acceptance": False,
            "limitations": [
                "PRICE_COMPONENT_NOT_DIVIDEND_TOTAL_RETURN",
                "INDEPENDENT_IDENTITY_ACTION_AND_ECONOMIC_REVIEW_REQUIRED",
            ],
        },
        ledgers,
        timings,
    )


def reconcile(root: Path, frame: dict[str, Any] | None = None) -> dict[str, int]:
    """Caller owns the existing daily lock; SQLite append transactions are replay-safe."""
    frame = frame if frame is not None else engine.snapshot(root)
    preview, ledgers, timings = prepare(root, frame)
    ineligible = sum(
        count
        for reason, count in preview["status_counts"].items()
        if reason.startswith(("INELIGIBLE_", "UNSUPPORTED_"))
    )
    pending = (
        sum(preview["status_counts"].values()) - preview["eligible_price_references"] - ineligible
    )
    result: dict[str, int] = {
        "inserted": 0,
        "replayed": 0,
        "pending": pending,
        "ineligible": ineligible,
        "corrections": 0,
        "unscorable": 0,
    }
    if not preview["eligible_price_references"]:
        return result
    cutoff = forward._at(frame["source_observed_at"]).astimezone(forward.IST).date().isoformat()
    by_key: dict[str, list[dict[str, Any]]] = {}
    for row in frame["rows"]:
        if row["session"] < cutoff and row["session"] not in frame["quality"][
            "excluded_sessions"
        ].get(row["key"], []):
            fact = timings.get(row["session"])
            if fact and forward._at(fact["close_at"]) < forward._at(row["received_at"]):
                by_key.setdefault(row["key"], []).append(row)
    slots = {(row["key"], row["session"]): row for row in frame["rows"]}
    positions = {day: index for index, day in enumerate(frame["sessions"])}
    for folder, forecasts in ledgers:
        eligible_ids = {
            forward._hash(forecast)
            for forecast in forecasts
            if _ready(forecast, frame, timings, slots, positions)
            == "READY_SOURCE_QUALIFIED_PRICE_REFERENCE_ONLY"
        }
        if not eligible_ids:
            continue
        keys = {forecast["key"] for forecast in forecasts}
        selected = [row for key in sorted(keys) for row in by_key.get(key, [])]
        values = forward.reconcile(
            folder,
            selected,
            frame["sessions"],
            frame["source_observed_at"],
            frame["quality"]["excluded_sessions"],
            official_timings=timings,
            require_official_sessions=True,
            forecast_ids=eligible_ids,
        )
        for name, value in values.items():
            result[name] = result.get(name, 0) + value
    if private_path(root, "global-cohort-latest.json").exists():
        from workers.nse_market.forward_cohort import reconcile as global_reconcile

        result.update(global_reconcile(root))
    return result


def run(root: Path, *, append: bool = False) -> dict[str, Any]:
    """Default preview writes nothing. Explicit append uses the same lock as daily.run."""
    if not root.is_dir():
        raise ValueError("EXISTING_SAVED_NSE_MARKET_ROOT_REQUIRED")
    verify(root)
    if not append:
        result, _, _ = prepare(root, engine.snapshot(root))
        return {**result, "mode": "READ_ONLY_PREVIEW", "outcome_writes": 0}
    with Store(private_path(root, "control")).lock():
        receipt: dict[str, Any] = {
            "job_id": uuid.uuid4().hex,
            "started_at": datetime.now(UTC).isoformat(),
            "provider_requests": 0,
            "forecast_writes": 0,
        }
        try:
            receipt["result"] = reconcile(root)
            receipt["state"] = "COMPLETED"
            return receipt
        except Exception as exc:
            code = str(exc)
            receipt.update(
                state="FAILED",
                error_code=code
                if isinstance(exc, ValueError)
                and code.startswith(("OUTCOME_", "V2_", "PROSPECTIVE_", "NSE_"))
                and re.fullmatch(r"[A-Z][A-Z0-9_]{1,120}", code)
                else "OFFLINE_OUTCOME_RECONCILIATION_FAILED",
            )
            raise
        finally:
            receipt["completed_at"] = datetime.now(UTC).isoformat()
            directory = private_path(root, "outcome-jobs")
            directory.mkdir(exist_ok=True)
            engine._checked(directory / (receipt["job_id"] + ".json"), receipt)
