"""Bounded configured-cohort EOD orchestration, manual until separately approved.

No scheduler registration is performed. An official date fact precedes capture;
actual nonempty daily observations establish source availability, not a promised
publication time. Missing candles remain pending, never manufactured as closes.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from alphalens_data.daily.storage import Store
from alphalens_data.providers.multi_contracts import Instrument
from workers.experimental_nse.acquire import PERMISSION, digest, initialize, private_path
from workers.experimental_nse_v2 import data as v2_data
from workers.experimental_nse_v2 import forward
from workers.nse_market import engine
from workers.providers.daily_clock import guard
from workers.providers.upstox import Reply


def _timing(root: Path, day: date, meter: Any) -> dict[str, Any] | None:
    folder = private_path(root, "calendar")
    folder.mkdir(exist_ok=True)
    path = folder / (str(day) + ".json")
    if path.exists():
        record = engine._read(path)
        # Dates further than seven days need fresh official schedule evidence.
        age = (datetime.now(UTC) - datetime.fromisoformat(record["received_at"])).total_seconds()
        fact_at_capture = record.get("fact")
        completed_when_observed = isinstance(fact_at_capture, dict) and datetime.fromisoformat(
            fact_at_capture["close_at"]
        ) < datetime.fromisoformat(record["received_at"])
        if age > 7 * 86400 and not completed_when_observed:
            raise ValueError("EXPANDED_DATED_CALENDAR_REFRESH_REQUIRES_NEW_REVISION")
        reply = Reply(
            200,
            bytes.fromhex(record["raw_hex"]),
            datetime.fromisoformat(record["received_at"]),
            "ACCEPTED",
        )
    else:
        reply = meter.get("timings", end=day)
        fact = v2_data.timing_fact(reply, day)
        engine._checked(
            path,
            {
                "received_at": reply.received_at.isoformat(),
                "raw_hex": reply.body.hex(),
                "raw_sha256": digest(reply.body),
                "fact": fact,
            },
        )
    return v2_data.timing_fact(reply, day)


def run(
    root: Path,
    provider_root: Path,
    v2_root: Path,
    *,
    session: date,
    max_stocks: int = 50,
    max_requests: int = 110,
    collect: bool = False,
    permission_reference: str,
    meter: Any | None = None,
    clock_evidence: dict[str, Any] | None = None,
    identity_overrides: dict[str, Instrument] | None = None,
) -> dict[str, Any]:
    """One bounded session catch-up batch. No unattended activation or old forecasts."""
    initialize(root)
    if permission_reference != PERMISSION:
        raise ValueError("NSE_MARKET_PRIVATE_RETENTION_PERMISSION_REQUIRED")
    if isinstance(max_stocks, bool) or not 1 <= max_stocks <= 250:
        raise ValueError("EXPLICIT_BOUNDED_DAILY_STOCK_SCOPE_REQUIRED")
    if isinstance(max_requests, bool) or not 1 <= max_requests <= 600:
        raise ValueError("EXPLICIT_BOUNDED_DAILY_REQUEST_SCOPE_REQUIRED")
    with Store(private_path(root, "control")).lock():
        return _run(
            root,
            provider_root,
            v2_root,
            session,
            max_stocks,
            max_requests,
            collect,
            meter=meter,
            clock_evidence=clock_evidence,
            identity_overrides=identity_overrides,
        )


def _run(
    root: Path,
    provider_root: Path,
    v2_root: Path,
    session: date,
    max_stocks: int,
    max_requests: int,
    collect: bool,
    *,
    meter: Any | None = None,
    clock_evidence: dict[str, Any] | None = None,
    identity_overrides: dict[str, Instrument] | None = None,
) -> dict[str, Any]:
    clock = clock_evidence or guard()
    today = date.fromisoformat(clock["session_date"])
    if session > today or (today - session).days > 31:
        raise ValueError("DAILY_BOUNDED_31_DAY_NONFUTURE_SESSION_REQUIRED")
    plan = engine._pointed(root, "plan-latest.json")
    frame = engine.snapshot(root)
    identities = [engine._identity(item) for item in plan["identities"]]
    identity_exclusions = []
    if identity_overrides is not None:
        identity_exclusions = [
            item.provider_key for item in identities if item.provider_key not in identity_overrides
        ]
        identities = [
            identity_overrides[item.provider_key]
            for item in identities
            if item.provider_key in identity_overrides
        ]
    observed = {row["key"] for row in frame["rows"] if row["session"] == str(session)}
    latest_by_key: dict[str, str] = {}
    for row in frame["rows"]:
        latest_by_key[row["key"]] = max(latest_by_key.get(row["key"], ""), row["session"])
    pending = sorted(
        (item for item in identities if item.provider_key not in observed),
        key=lambda item: (latest_by_key.get(item.provider_key, "9999"), item.provider_key),
        reverse=True,
    )
    proposed = {
        "state": "DRY_RUN",
        "session": str(session),
        "clock": clock,
        "configured_securities": len(plan["identities"]),
        "current_identity_eligible_securities": len(identities),
        "identity_exclusions_pending_review": identity_exclusions,
        "already_observed": len(observed),
        "pending_securities": len(pending),
        "max_stocks": max_stocks,
        "max_requests": max_requests,
        "maximum_candle_action_gets": min(max_stocks, len(pending)) * 2,
        "session_timing_gets_upper_bound": 39,
        "api_calls": 0,
        "scheduled_collection_enabled": False,
        "permission_reference": PERMISSION,
        "cadence_approval": "EXPLICIT_OPERATOR_APPROVAL_REQUIRED_BEFORE_RECURRING_COLLECTION",
    }
    if not collect:
        return proposed
    if not pending:
        return {**proposed, "state": "REPLAY", "api_calls": 0, "reconciliation": reconcile(root)}
    meter = meter or engine.Meter(provider_root, max_requests)
    timing = _timing(root, session, meter)
    if timing is None:
        return {**proposed, "state": "NON_TRADING_SESSION", "api_calls": meter.calls}
    if datetime.fromisoformat(timing["close_at"]) >= datetime.fromisoformat(clock["lower_at"]):
        return {**proposed, "state": "SESSION_NOT_COMPLETED", "api_calls": meter.calls}
    following = None
    closed: list[str] = []
    for offset in range(1, 9):
        day = session + timedelta(days=offset)
        fact = _timing(root, day, meter)
        if fact is not None:
            following = {
                **fact,
                "previous_session": str(session),
                "intervening_dates_verified_closed": True,
                "closed_dates": closed,
            }
            break
        closed.append(str(day))
    if following is None:
        raise ValueError("NEXT_OFFICIAL_OPEN_UNAVAILABLE")
    links = private_path(root, "session-links")
    links.mkdir(exist_ok=True)
    link_path = links / (str(session) + ".json")
    if not link_path.exists():
        engine._checked(link_path, {"session_timing": timing, "next_session_timing": following})
    records = private_path(root, "daily", str(session))
    records.mkdir(parents=True, exist_ok=True)
    retained, failures = 0, []
    for identity in pending[:max_stocks]:
        folder = records / str(identity.isin)
        folder.mkdir(exist_ok=True)
        if not (folder / "response.json").exists():
            if meter.calls >= max_requests:
                break
            previous = latest_by_key.get(identity.provider_key)
            start = date.fromisoformat(previous) + timedelta(days=1) if previous else session
            start = min(start, session)
            if (session - start).days > 30:
                # Long suspensions/unknown early history require explicit repair;
                # do not silently download an unbounded archive from a daily run.
                start = session
            reply = meter.get("candles", key=identity.provider_key, start=start, end=session)
            if reply.state != "ACCEPTED" or reply.status != 200:
                failures.append({"key": identity.provider_key, "reason": reply.state})
                if reply.status in {401, 403, 429}:
                    break
                continue
            # Empty publication responses are retryable, not frozen final absence.
            observations = v2_data.normalized(reply.body, identity, reply.received_at)
            if (
                not observations
                or not any(row["session"] == str(session) for row in observations)
                or any(not str(start) <= row["session"] <= str(session) for row in observations)
            ):
                failures.append(
                    {
                        "key": identity.provider_key,
                        "reason": "PUBLICATION_PENDING_OR_SINGLE_SESSION_INCOMPLETE",
                    }
                )
                continue
            if datetime.fromisoformat(timing["close_at"]) >= reply.received_at:
                raise ValueError("CANDLE_RETRIEVED_BEFORE_OFFICIAL_CLOSE")
            for day in sorted({row["session"] for row in observations}):
                fact = _timing(root, date.fromisoformat(day), meter)
                if fact is None or datetime.fromisoformat(fact["close_at"]) >= reply.received_at:
                    raise ValueError("CATCHUP_CANDLE_OFFICIAL_COMPLETED_SESSION_REQUIRED")
            engine._response(folder, reply, identity, start, session)
            engine._cache_normalized(folder, identity, observations)
        action_path = folder / "actions.json"
        if not action_path.exists():
            if meter.calls >= max_requests:
                break
            reply = meter.get("actions", key=identity.provider_key)
            if reply.state != "ACCEPTED" or reply.status != 200:
                attempts = folder / "action-attempts"
                attempts.mkdir(exist_ok=True)
                engine._checked(
                    attempts / (uuid.uuid4().hex + ".json"),
                    {**v2_data.action_facts(reply), "status": reply.status},
                )
                failures.append({"key": identity.provider_key, "reason": reply.state})
                if reply.status in {401, 403, 429}:
                    break
                continue
            engine._checked(action_path, v2_data.action_facts(reply))
        record_path = folder / "record.json"
        if not record_path.exists():
            engine._checked(
                record_path,
                {
                    "identity": identity.model_dump(mode="json"),
                    "response_sha256": digest((folder / "response.json").read_bytes()),
                    "actions_sha256": digest(action_path.read_bytes()),
                    "session_timing": timing,
                },
            )
        retained += 1
    current = engine.snapshot(root)
    reconciliation = reconcile(root, current)
    # Current source evidence may support an upcoming entry. Historical catch-up
    # after an opening is never converted into a backdated forecast.
    scoring: dict[str, Any] = {"state": "NO_FUTURE_ENTRY", "new_forecasts": 0}
    if current["sessions"][-1] == str(session) and datetime.fromisoformat(
        following["open_at"]
    ) > datetime.fromisoformat(clock["upper_at"]):
        scoring = engine._score(root, v2_root)
    result = {
        **proposed,
        "state": "CAPTURED" if not failures else "PARTIAL_OR_PUBLICATION_PENDING",
        "api_calls": meter.calls,
        "new_daily_observations": retained,
        "failures": failures,
        "reconciliation": reconciliation,
        "scoring": {k: scoring.get(k) for k in ("state", "scored_securities", "new_forecasts")},
        "completed_at": datetime.now(UTC).isoformat(),
    }
    runs = private_path(root, "daily-runs")
    runs.mkdir(exist_ok=True)
    path = runs / (uuid.uuid4().hex + ".json")
    engine._checked(path, result)
    engine._pointer(root, "daily-latest.json", path)
    return result


def reconcile(root: Path, frame: dict[str, Any] | None = None) -> dict[str, int]:
    """Append to expanded hash-shard ledgers only; original 31 remain untouched."""
    frame = frame if frame is not None else engine.snapshot(root)
    timings: dict[str, dict[str, Any]] = {}
    seed = engine._read(private_path(root, "seed.json"))
    links = [engine._read(path) for path in private_path(root, "session-links").glob("*.json")]
    if seed.get("session_timing") and seed.get("next_session_timing"):
        links.insert(
            0,
            {
                "session_timing": seed["session_timing"],
                "next_session_timing": seed["next_session_timing"],
            },
        )
    for link in links:
        current, following = link["session_timing"], link["next_session_timing"]
        timings[current["session"]] = {
            **current,
            "next_verified_session": following["session"],
            "next_verified_open_at": following["open_at"],
            "intervening_dates_verified_closed": True,
            "verified_closed_dates": following["closed_dates"],
        }
        timings.setdefault(following["session"], following)
    retrieved = datetime.fromisoformat(frame["source_observed_at"])
    cutoff = retrieved.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
    prior_rows = [row for row in frame["rows"] if row["session"] < cutoff]
    # Each shard owns only a few securities. The evaluator still receives the
    # complete common session clock, but unrelated prices cannot affect it.
    # Validate all shard forecast bodies before deriving the bounded key set.
    by_key: dict[str, list[dict[str, Any]]] = {}
    for row in prior_rows:
        by_key.setdefault(row["key"], []).append(row)
    result: dict[str, int] = {}
    for folder in private_path(root, "expanded-forecasts").glob("*"):
        if folder.is_dir():
            ledger = folder / "experimental-v2-prospective.sqlite3"
            if not ledger.exists():
                continue
            with sqlite3.connect(ledger.resolve().as_uri() + "?mode=ro", uri=True) as connection:
                connection.row_factory = sqlite3.Row
                keys = {
                    forward._verified(record)["key"]
                    for record in connection.execute("SELECT * FROM experimental_forecasts")
                }
            selected_rows = [row for key in sorted(keys) for row in by_key.get(key, [])]
            values = forward.reconcile(
                folder,
                selected_rows,
                frame["sessions"],
                source_observed_at=frame["source_observed_at"],
                excluded_sessions=frame["quality"]["excluded_sessions"],
                official_timings=timings,
                require_official_sessions=True,
            )
            for key, value in values.items():
                result[key] = result.get(key, 0) + value
    if private_path(root, "global-cohort-latest.json").exists():
        from workers.nse_market.forward_cohort import reconcile as reconcile_global

        result.update(reconcile_global(root))
    return result
