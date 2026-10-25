"""Offline whole-master incremental capacity proposal; never collect or activate.

Existing reservations remain 250 securities / 600 GETs per run, 1,800 per day.
Response-dependent calls are bounded explicitly instead of called exact outcomes.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from workers.experimental_nse.acquire import digest, encoded, private_path
from workers.experimental_nse_v2 import data as v2_data
from workers.providers import universe
from workers.providers.upstox import Reply

from . import discovery, engine

STOCKS_PER_RUN = 250
RESERVED_PER_RUN = 600
RESERVED_PER_DAY = 1800
RUNS_PER_DAY = 3
METADATA_BOUND_PER_RUN = 71


def _dates(first: date, last: date) -> list[str]:
    return [
        (first + timedelta(days=offset)).isoformat() for offset in range((last - first).days + 1)
    ]


def calendar_cache(root: Path, *, at: datetime) -> dict[str, dict[str, Any] | None]:
    result = {}
    for path in private_path(root, "calendar").glob("*.json"):
        day = date.fromisoformat(path.stem)
        record = engine._read(path)
        received = datetime.fromisoformat(record["received_at"])
        if received.utcoffset() is None or received > at:
            raise ValueError("CALENDAR_CACHE_CLOCK_REJECTED")
        raw = bytes.fromhex(record["raw_hex"])
        if digest(raw) != record["raw_sha256"]:
            raise ValueError("CALENDAR_CACHE_RAW_HASH_REJECTED")
        fact = v2_data.timing_fact(Reply(200, raw, received, "ACCEPTED"), day)
        completed_when_observed = (
            fact is not None and datetime.fromisoformat(fact["close_at"]) < received
        )
        if (at - received).total_seconds() > 7 * 86400 and not completed_when_observed:
            continue
        result[str(day)] = fact
    return result


def partial_cache(root: Path, key: str, session: date, *, at: datetime) -> dict[str, bool]:
    """Only target-session checkpoints count; no cross-session action-cache assumption."""
    if not re.fullmatch(r"NSE_EQ\|INE[A-Z0-9]{9}", key):
        raise ValueError("EXACT_ORDINARY_EQUITY_KEY_REQUIRED")
    folder = private_path(root, "daily", str(session), key.removeprefix("NSE_EQ|"))
    result = {"candle": False, "actions": False}
    if (folder / "response.json").is_file():
        response = engine._read(folder / "response.json")
        identity = engine._identity(response["identity"])
        received = datetime.fromisoformat(response["received_at"])
        if identity.provider_key != key or received.utcoffset() is None or received > at:
            raise ValueError("PARTIAL_CANDLE_CACHE_IDENTITY_OR_CLOCK_REJECTED")
        rows = engine._rows(folder, identity)
        result["candle"] = any(row["session"] == str(session) for row in rows)
    if (folder / "actions.json").is_file():
        actions = engine._read(folder / "actions.json")
        received = datetime.fromisoformat(actions["received_at"])
        if received.utcoffset() is None or received > at:
            raise ValueError("PARTIAL_ACTION_CACHE_CLOCK_REJECTED")
        result["actions"] = (
            actions.get("state") == "OBSERVED_ACTION_REFERENCE_NOT_EXHAUSTIVE"
            and actions.get("unparsed_date_fields") == 0
        )
    return result


def plan(
    master: universe.Snapshot,
    view: dict[str, Any],
    *,
    session: date,
    at: datetime,
    calendars: dict[str, dict[str, Any] | None],
    checkpoints: dict[str, dict[str, bool]] | None = None,
) -> dict[str, Any]:
    identity = discovery.identity_status(master, at=at)
    today = at.astimezone(ZoneInfo("Asia/Kolkata")).date()
    if session > today or (today - session).days > 31:
        raise ValueError("BOUNDED_NONFUTURE_TARGET_SESSION_REQUIRED")
    fact = calendars.get(str(session))
    if str(session) in calendars and fact is None:
        raise ValueError("TARGET_IS_A_VERIFIED_NON_TRADING_DATE")
    if fact is not None and datetime.fromisoformat(fact["close_at"]) >= at:
        raise ValueError("TARGET_SESSION_NOT_COMPLETED")
    stocks = {row["instrument_key"]: row for row in master.records if row["eligible_common_equity"]}
    latest = {row["key"]: row["session"] for row in view["rows"] if row.get("close") is not None}
    configured = {row["key"] for row in view["rows"]}
    pending = [key for key in stocks if latest.get(key, "") < str(session)]
    # Keep approved identities first, then oldest evidence, then stable ISIN. No score selection.
    pending.sort(
        key=lambda key: (key not in configured, latest.get(key, ""), stocks[key]["isin"], key)
    )
    required_dates = {str(session)}
    for offset in range(1, 9):
        day = str(session + timedelta(days=offset))
        required_dates.add(day)
        if day in calendars and calendars[day] is not None:
            break
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(pending), STOCKS_PER_RUN):
        keys = pending[offset : offset + STOCKS_PER_RUN]
        rows = []
        for key in keys:
            previous = date.fromisoformat(latest[key]) if key in latest else None
            start = previous + timedelta(days=1) if previous else session
            if (session - start).days > 30:
                start = session
            required_dates.update(_dates(start, session))
            cache = (checkpoints or {}).get(key, {})
            rows.append(
                {
                    "key": key,
                    "symbol": stocks[key]["symbol"],
                    "start": str(start),
                    "end": str(session),
                    "existing_approved_cohort": key in configured,
                    "candle_gets": int(not cache.get("candle", False)),
                    "action_gets_if_candle_valid": int(not cache.get("actions", False)),
                    "history_bootstrap_required": key not in latest,
                    "acquisition_authorized_by_this_plan": False,
                }
            )
        number = len(batches)
        batches.append(
            {
                "batch": number + 1,
                "earliest_capacity_day": number // RUNS_PER_DAY + 1,
                "capacity_slot": number % RUNS_PER_DAY + 1,
                "securities": rows,
                "candle_gets": sum(row["candle_gets"] for row in rows),
                "action_gets_if_all_candles_valid": sum(
                    row["action_gets_if_candle_valid"] for row in rows
                ),
                "metadata_gets_upper_bound": METADATA_BOUND_PER_RUN,
                "reserved_gets": RESERVED_PER_RUN,
            }
        )
    missing_dates = sorted(required_dates - calendars.keys())
    candle_calls = sum(batch["candle_gets"] for batch in batches)
    action_calls = sum(batch["action_gets_if_all_candles_valid"] for batch in batches)
    new_keys = sum(key not in configured for key in pending)
    full_batches = math.ceil(len(stocks) / STOCKS_PER_RUN)
    signature = {
        "master_snapshot_id": master.snapshot_id,
        "dataset_id": view["dataset_id"],
        "session": str(session),
        "batches": batches,
        "missing_calendar_dates": missing_dates,
    }
    return {
        **signature,
        "plan_id": digest(encoded(signature)),
        "as_of": at.isoformat(),
        "status": "BLOCKED_APPROVAL" if new_keys else "VERIFIED_COMPLETE",
        "activation_enabled": False,
        "actual_provider_requests": 0,
        "master_identity": identity,
        "planning_clock_only_not_collection_clock_qualification": True,
        "target_session_qualified_by_saved_calendar": fact is not None,
        "target_session_evidence_status": "VERIFIED_COMPLETE"
        if fact is not None
        else "BLOCKED_EXTERNAL_DATA",
        "supported_equities": len(stocks),
        "already_observed_target_or_later": len(stocks) - len(pending),
        "pending_securities": len(pending),
        "new_unapproved_securities": new_keys,
        "known_success_path_candle_gets": candle_calls,
        "action_gets_if_all_candles_valid": action_calls,
        "stock_gets_success_path": candle_calls + action_calls,
        "verified_calendar_cache_dates": len(calendars),
        "missing_calendar_gets_upper_bound_first_day": len(missing_dates),
        "master_refresh_gets_if_expired": int(not identity["current_identity_actions_available"]),
        "reserved_gets_all_pending_batches": len(batches) * RESERVED_PER_RUN,
        "minimum_capacity_days_for_pending_batches": math.ceil(len(batches) / RUNS_PER_DAY),
        "full_universe_daily_reservation": full_batches * RESERVED_PER_RUN,
        "full_universe_minimum_daily_batches": full_batches,
        "existing_policy": {
            "stocks_per_run": STOCKS_PER_RUN,
            "reserved_gets_per_run": RESERVED_PER_RUN,
            "reserved_gets_per_day": RESERVED_PER_DAY,
            "maximum_runs_per_day": RUNS_PER_DAY,
        },
        "same_day_full_universe_supported": full_batches <= RUNS_PER_DAY,
        "new_history_bootstrap_stock_gets_lower_bound": 2
        * sum(key not in latest for key in pending),
        "limitations": [
            (
                "Success-path counts assume nonempty valid candles; empty responses "
                "cost a candle GET and do not create an action GET"
            ),
            (
                "71 metadata GETs per run is the unchanged conservative "
                "calendar/master ceiling, not measured calls"
            ),
            (
                "Calendar cache savings are conditional on unchanged valid schedules; "
                "future facts expire under existing rules"
            ),
            "Whole-master daily coverage cannot be promised by rotating over multiple days",
            (
                "New-history daily requests collect one target slot and do not "
                "establish a 61-session ML lookback"
            ),
            (
                "Bootstrap counts are lower bounds: exact date ranges, chunking, "
                "permissions, storage and quota require separate approval"
            ),
            (
                "Capacity slots share the existing reservation pool; this plan grants "
                "no additional slots or unused-budget entitlement"
            ),
            (
                "No provider bulk candle endpoint or reusable cross-session "
                "corporate-action cache is assumed"
            ),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--universe-root", required=True, type=Path)
    parser.add_argument("--session", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    at = datetime.now(UTC)
    master = universe.load(args.universe_root)
    view = engine._pointed(args.root, "market-view-latest.json")
    checkpoints = {
        row["instrument_key"]: partial_cache(args.root, row["instrument_key"], args.session, at=at)
        for row in master.records
        if row["eligible_common_equity"]
    }
    print(
        json.dumps(
            plan(
                master,
                view,
                session=args.session,
                at=at,
                calendars=calendar_cache(args.root, at=at),
                checkpoints=checkpoints,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
