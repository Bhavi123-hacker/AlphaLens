"""Bounded configured-cohort EOD orchestration, manual until separately approved.

No scheduler registration is performed. An official date fact precedes capture;
actual nonempty daily observations establish source availability, not a promised
publication time. Missing candles remain pending, never manufactured as closes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from alphalens_data.daily.storage import Store
from alphalens_data.providers.multi_contracts import Instrument
from workers.experimental_nse.acquire import PERMISSION, digest, initialize, private_path
from workers.experimental_nse_v2 import data as v2_data
from workers.nse_market import engine, saved_market
from workers.providers.daily_clock import guard
from workers.providers.upstox import Operation, Reply


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
        key=lambda item: (
            _attempted_target(root, session, item),
            latest_by_key.get(item.provider_key, "9999"),
            item.provider_key,
        ),
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
        "pending_before_run": len(plan["identities"]) - len(observed),
        "eligible_pending_before_run": len(pending),
        "pending_count_basis": "CURRENT_IDENTITY_ELIGIBLE_BEFORE_RUN",
        "selection_policy": "UNATTEMPTED_TARGET_FIRST_THEN_DATED_HISTORY_AND_STABLE_KEY",
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
        # A failed presentation stage must be recoverable after the final source
        # batch. Reuse verified observations without another provider request.
        recovered_scoring = _recover_scoring(root, v2_root, frame, session, clock)
        return {
            **proposed,
            **_session_counts(frame, plan, session, identity_exclusions),
            "state": "REPLAY",
            "api_calls": 0,
            "scoring": recovered_scoring,
            "reconciliation": reconcile(root),
            "market_view": _publish_market(root, frame, only_if_changed=True),
        }
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
            if (folder / "candles.json").exists():
                # An interrupted raw write without its immutable receipt cannot
                # be adopted or overwritten. Isolate it and let other keys run.
                failures.append(
                    {"key": identity.provider_key, "reason": "ORPHAN_RAW_RESPONSE_RECEIPT_MISSING"}
                )
                continue
            if meter.calls >= max_requests:
                break
            previous = latest_by_key.get(identity.provider_key)
            start = date.fromisoformat(previous) + timedelta(days=1) if previous else session
            start = min(start, session)
            if (session - start).days > 30:
                # Long suspensions/unknown early history require explicit repair;
                # do not silently download an unbounded archive from a daily run.
                start = session
            # Historical V3 directs current-day retrieval to Intraday V3. Reuse
            # the already-qualified V2 routing rule, with one candle GET only.
            # The independent date guard, not the local UTC date, owns "today".
            current_day = session == today
            operation: Operation = "intraday_candles" if current_day else "candles"
            request = {
                "operation": operation,
                "unit": "days",
                "interval": 1,
                "instrument_key": identity.provider_key,
                "target_session": str(session),
                "from_date": None if current_day else str(start),
                "to_date": None if current_day else str(session),
                "current_day_only": current_day,
            }
            if current_day:
                # A current-day response cannot establish missing older bars.
                # Preserve those gaps; do not describe them as a caught-up range.
                start = session
                reply = meter.get(operation, key=identity.provider_key)
            else:
                reply = meter.get(operation, key=identity.provider_key, start=start, end=session)
            if reply.state != "ACCEPTED" or reply.status != 200:
                _failed_request(folder, identity.provider_key, reply, reply.state)
                failures.append({"key": identity.provider_key, "reason": reply.state})
                if reply.status in {401, 403, 429}:
                    break
                continue
            # Empty publication responses are retryable, not frozen final absence.
            try:
                observations = v2_data.normalized(reply.body, identity, reply.received_at)
            except (ValueError, TypeError, KeyError, ArithmeticError):
                reason = "CANDLE_SCHEMA_OR_QUALITY_REJECTED"
                _failed_request(folder, identity.provider_key, reply, reason)
                failures.append({"key": identity.provider_key, "reason": reason})
                continue
            if (
                not observations
                or (current_day and len(observations) != 1)
                or not any(row["session"] == str(session) for row in observations)
                or any(not str(start) <= row["session"] <= str(session) for row in observations)
            ):
                attempts = folder / "publication-attempts"
                attempts.mkdir(exist_ok=True)
                engine._checked(
                    attempts / (uuid.uuid4().hex + ".json"),
                    {
                        "state": "PUBLICATION_PENDING_OR_SINGLE_SESSION_INCOMPLETE",
                        "session": str(session),
                        "key": identity.provider_key,
                        "received_at": reply.received_at.isoformat(),
                        "raw_sha256": digest(reply.body),
                        "raw_hex": reply.body.hex(),
                        "completed_capture": False,
                        "status": reply.status,
                        "server_at": reply.server_at.isoformat() if reply.server_at else None,
                        "request": request,
                    },
                )
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
            engine._response(folder, reply, identity, start, session, request=request)
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
        scoring = _score_checkpointed(root, v2_root, current, session)
    # Recover a prior partial-batch publication even if every new reply is empty.
    # Reuse the already validated frame; publication never triggers acquisition.
    market_view = _publish_market(root, current, only_if_changed=not retained)
    result = {
        **proposed,
        **_session_counts(current, plan, session, identity_exclusions),
        "state": "CAPTURED" if not failures else "PARTIAL_OR_PUBLICATION_PENDING",
        "api_calls": meter.calls,
        "new_daily_observations": retained,
        "failures": failures,
        "reconciliation": reconciliation,
        "market_view": market_view,
        "scoring": {k: scoring.get(k) for k in ("state", "scored_securities", "new_forecasts")},
        "completed_at": datetime.now(UTC).isoformat(),
    }
    runs = private_path(root, "daily-runs")
    runs.mkdir(exist_ok=True)
    path = runs / (uuid.uuid4().hex + ".json")
    engine._checked(path, result)
    engine._pointer(root, "daily-latest.json", path)
    return result


def _score_checkpointed(
    root: Path, v2_root: Path, frame: dict[str, Any], session: date
) -> dict[str, Any]:
    """Durable stage intent makes a source-complete inference interruption resumable.

    Receipt files are separate from source inputs and never change the dataset ID.
    The existing scorer owns strict actual-time and append-only forecast checks.
    """
    folder = private_path(root, "score-publication-attempts")
    folder.mkdir(exist_ok=True)
    name = str(session) + "-" + frame["dataset_id"]
    started, done = folder / (name + ".started.json"), folder / (name + ".done.json")
    if not started.exists():
        engine._checked(
            started,
            {
                "dataset_id": frame["dataset_id"],
                "session": str(session),
                "started_at": datetime.now(UTC).isoformat(),
            },
        )
    else:
        intent = engine._read(started)
        if intent["dataset_id"] != frame["dataset_id"] or intent["session"] != str(session):
            raise ValueError("DAILY_SCORING_RECOVERY_INTENT_MISMATCH")
    result = engine._score(root, v2_root)
    if result.get("replayed"):
        # The score pointer is published before cohort/workspace materialization.
        # An interruption there must resume those stages before marking this
        # attempt complete. freeze_current rechecks actual future-entry timing;
        # it never converts an elapsed entry into a prospective declaration.
        from workers.nse_market.forward_cohort import freeze_current

        cohort = freeze_current(root)
        if cohort.get("replayed"):
            # A crash may also separate the immutable declaration from its
            # pointer. Restore only the receipt for this exact score snapshot.
            engine._pointer(
                root,
                "global-cohort-latest.json",
                private_path(root, "global-cohorts", cohort["declaration_id"] + ".json"),
            )
        engine.publish_workspace(root)
    if not done.exists():
        engine._checked(
            done,
            {
                "dataset_id": frame["dataset_id"],
                "session": str(session),
                "completed_at": datetime.now(UTC).isoformat(),
                "new_forecasts": result.get("new_forecasts", 0),
            },
        )
    return result


def _recover_scoring(
    root: Path, v2_root: Path, frame: dict[str, Any], session: date, clock: dict[str, Any]
) -> dict[str, Any]:
    """Retry an explicitly interrupted stage, with zero repeated provider GETs."""
    folder = private_path(root, "score-publication-attempts")
    name = str(session) + "-" + frame["dataset_id"]
    started, done = folder / (name + ".started.json"), folder / (name + ".done.json")
    if not started.exists():
        return {"state": "NO_INTERRUPTED_SCORING_STAGE", "new_forecasts": 0}
    intent = engine._read(started)
    if intent["dataset_id"] != frame["dataset_id"] or intent["session"] != str(session):
        raise ValueError("DAILY_SCORING_RECOVERY_INTENT_MISMATCH")
    if done.exists():
        completed = engine._read(done)
        if completed["dataset_id"] != frame["dataset_id"] or completed["session"] != str(session):
            raise ValueError("DAILY_SCORING_RECOVERY_COMPLETION_MISMATCH")
        return {"state": "NO_INTERRUPTED_SCORING_STAGE", "new_forecasts": 0}
    following = frame.get("next_session_timing")
    if (
        frame["sessions"][-1] != str(session)
        or not following
        or datetime.fromisoformat(following["open_at"]) <= datetime.fromisoformat(clock["upper_at"])
    ):
        return {"state": "NO_FUTURE_ENTRY", "new_forecasts": 0}
    return {**_score_checkpointed(root, v2_root, frame, session), "recovered_stage": True}


def _attempted_target(root: Path, session: date, identity: Instrument) -> bool:
    """Do not let a repeatedly empty/failed key starve an unqueried session key."""
    folder = private_path(root, "daily", str(session), str(identity.isin))
    if any(
        (folder / name).exists()
        for name in ("response.json", "candles.json", "actions.json", "record.json")
    ):
        return True
    return any(
        next((folder / name).glob("*.json"), None) is not None
        for name in ("publication-attempts", "request-attempts", "action-attempts")
    )


def _failed_request(folder: Path, key: str, reply: Reply, state: str) -> None:
    """Private bounded transport evidence; never store exception text or headers."""
    attempts = folder / "request-attempts"
    attempts.mkdir(exist_ok=True)
    engine._checked(
        attempts / (uuid.uuid4().hex + ".json"),
        {
            "key": key,
            "state": state,
            "status": reply.status,
            "received_at": reply.received_at.isoformat(),
            "raw_sha256": digest(reply.body),
            "completed_capture": False,
            "raw_retained": False,
        },
    )


def _session_counts(
    frame: dict[str, Any], plan: dict[str, Any], session: date, excluded: list[str]
) -> dict[str, Any]:
    """Terminal counts cover every configured key, including excluded identities."""
    configured = {item["provider_key"] for item in plan["identities"]}
    accepted = {row["key"] for row in frame["rows"] if row["session"] == str(session)} & configured
    missing_excluded = sorted(set(excluded) - accepted)
    return {
        "accepted_session_securities": len(accepted),
        "dataset_id": frame.get("dataset_id"),
        "accepted_session_keys": sorted(accepted),
        "pending_securities": len(configured - accepted),
        "identity_excluded_missing_securities": len(missing_excluded),
        "identity_excluded_missing_keys": missing_excluded,
        "pending_count_basis": "FULL_CONFIGURED_COHORT_AFTER_VALIDATION",
    }


def _publish_market(
    root: Path, frame: dict[str, Any], *, only_if_changed: bool = False
) -> dict[str, Any]:
    """Recover a missing/stale derived view; source and forecasts remain immutable."""
    try:
        if only_if_changed and (root / "market-view-latest.json").exists():
            view = engine._pointed(root, "market-view-latest.json")
            scores = (
                engine._pointed(root, "scores-latest.json")
                if (root / "scores-latest.json").exists()
                else None
            )
            embedded = (view.get("research_workspace") or {}).get("scores")
            if view["dataset_id"] == frame["dataset_id"] and embedded == scores:
                return {"state": "UNCHANGED_VERIFIED_DATASET", "provider_requests": 0}
        return saved_market.publish(root, frame, at=datetime.now(UTC))
    except (ValueError, OSError, KeyError, TypeError):
        # Never overwrite corrupt evidence or hide failed recovery from operators.
        return {"state": "FAILED", "error_code": "SAVED_MARKET_PUBLICATION_FAILED"}


def reconcile(root: Path, frame: dict[str, Any] | None = None) -> dict[str, int]:
    """Retry expanded outcomes using raw-calendar-backed source qualification."""
    from workers.nse_market.outcomes import reconcile as reconcile_saved

    return reconcile_saved(root, frame)
