"""Read-only collection diagnosis from qualified saved evidence; never acquires data."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from workers.experimental_nse.acquire import digest
from workers.experimental_nse_v2.data import timing_fact
from workers.nse_market import engine
from workers.providers.store import ProviderStore
from workers.providers.upstox import Reply

IST = ZoneInfo("Asia/Kolkata")


def expected_session(root: Path, *, at: datetime) -> dict[str, Any]:
    """Do not extrapolate an exchange calendar from weekdays or observed prices."""
    if at.utcoffset() is None:
        raise ValueError("AWARE_STATUS_CLOCK_REQUIRED")
    today = at.astimezone(IST).date()
    missing: list[str] = []
    latest: str | None = None
    for offset in range(32):
        day = today - timedelta(days=offset)
        path = root / "calendar" / (str(day) + ".json")
        if not path.exists():
            missing.append(str(day))
            continue
        record = engine._read(path)
        raw = bytes.fromhex(record["raw_hex"])
        received = datetime.fromisoformat(record["received_at"])
        if digest(raw) != record["raw_sha256"] or received.utcoffset() is None or received > at:
            raise ValueError("STATUS_CALENDAR_EVIDENCE_REJECTED")
        fact = timing_fact(Reply(200, raw, received, "ACCEPTED"), day)
        if fact is None:
            # A distant future no-session response is not a permanent holiday fact.
            if (at - received).total_seconds() > 7 * 86400 and received.date() < day:
                missing.append(str(day))
            continue
        if datetime.fromisoformat(fact["close_at"]) < at:
            latest = str(day)
            break
    return {
        "expected_trading_session": latest if not missing else None,
        "latest_saved_completed_session_fact": latest,
        "missing_calendar_dates": missing,
        "basis": "SAVED_OFFICIAL_CALENDAR_ONLY_LOCAL_OBSERVATION_TIME_NOT_COLLECTION_CLEARANCE",
        "calendar_complete_to_latest_fact": latest is not None and not missing,
    }


def _missing_reason(root: Path, session: str, identity: dict[str, Any]) -> dict[str, Any]:
    folder = root / "daily" / session / str(identity["isin"])
    attempts = [engine._read(path) for path in (folder / "publication-attempts").glob("*.json")]
    attempts.sort(key=lambda row: row["received_at"])
    reason = "NOT_QUERIED_FOR_SESSION_NO_ACCEPTED_SOURCE_RECORD"
    if (folder / "response.json").exists():
        engine._read(folder / "response.json")
        reason = (
            "REJECTED_OR_INCOMPLETE_ACCEPTANCE_REQUIRES_REVIEW"
            if (folder / "record.json").exists()
            else "ACCEPTANCE_RECORD_PENDING"
            if (folder / "actions.json").exists()
            else "ACTION_EVIDENCE_PENDING"
        )
    elif attempts:
        reason = attempts[-1]["state"]
    return {
        "key": identity["provider_key"],
        "symbol": identity["symbol"],
        "isin": identity["isin"],
        "reason": reason,
        "saved_publication_attempts": len(attempts),
        "latest_publication_attempt_at": attempts[-1]["received_at"] if attempts else None,
    }


def _request_counts(provider_root: Path | None) -> dict[str, Any]:
    if provider_root is None:
        return {"available": False, "reason": "PROVIDER_ROOT_NOT_SUPPLIED"}
    shared = ProviderStore(provider_root)._quota_store("upstox")
    # Query the existing store in read-only mode. Never initialize or reserve it.
    counts: dict[str, int] = {}
    outcomes: dict[str, int] = {}
    with closing(shared.connection(readonly=True)) as connection:
        for stamp, outcome in connection.execute(
            "SELECT reserved_at,outcome FROM attempts WHERE provider='upstox' ORDER BY reserved_at"
        ):
            day = datetime.fromtimestamp(stamp, IST).date().isoformat()
            counts[day] = counts.get(day, 0) + 1
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
    return {
        "available": True,
        "shared_actual_api_attempts_total": sum(counts.values()),
        "shared_actual_api_attempts_by_ist_day": counts,
        "shared_outcomes": outcomes,
        "pending_intents_are_not_proof_of_http_completion": True,
        "basis": "SHARED_ACCOUNT_ATTEMPT_LEDGER_INCLUDES_OTHER_CLIENTS",
    }


def report(
    root: Path,
    *,
    at: datetime,
    provider_root: Path | None = None,
    task_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate saved source lineage and summarize it without publishing or writing."""
    calendar = expected_session(root, at=at)
    frame = engine.snapshot(root)
    plan = engine._pointed(root, "plan-latest.json")
    identities = plan["identities"]
    latest = max(frame["sessions"], default=None)
    target = calendar["expected_trading_session"] or latest
    accepted = {row["key"] for row in frame["rows"] if row["session"] == target}
    latest_accepted = {row["key"] for row in frame["rows"] if row["session"] == latest}
    missing = (
        [
            _missing_reason(root, target, item)
            for item in identities
            if item["provider_key"] not in accepted
        ]
        if target
        else []
    )
    reasons: dict[str, int] = {}
    for row in missing:
        reasons[row["reason"]] = reasons.get(row["reason"], 0) + 1
    runs = root / "operational" / "runs"
    terminals = [
        engine._read(path)
        for pattern in ("*.done.json", "*.interrupted.json")
        for path in runs.glob(pattern)
    ]
    terminals.sort(key=lambda row: row["completed_at"])
    successful = [
        row for row in terminals if row.get("outcome", {}).get("new_daily_observations", 0)
    ]
    reservations = [engine._read(path) for path in runs.glob("*.started.json")]
    by_day: dict[str, int] = {}
    for reservation in reservations:
        day = reservation["quota_day"]
        by_day[day] = by_day.get(day, 0) + reservation["reserved_requests"]
    terminal_ids = {row["run_id"] for row in terminals}
    unknown_runs = [row["run_id"] for row in reservations if row["run_id"] not in terminal_ids]
    scores = (
        engine._pointed(root, "scores-latest.json")
        if (root / "scores-latest.json").exists()
        else {}
    )
    task = task_observation
    if task is None and (root / "task-observation-latest.json").exists():
        task = engine._pointed(root, "task-observation-latest.json")
    task = task or {}
    observed = datetime.fromisoformat(task["observed_at"]) if task.get("observed_at") else None
    stale = (
        observed is None
        or observed.utcoffset() is None
        or not 0 <= (at - observed).total_seconds() <= 300
    )
    counts = _request_counts(provider_root)
    return {
        "read_at": at.isoformat(),
        "provider_requests": 0,
        "tasks_modified": False,
        **calendar,
        "latest_retained_session": latest,
        "latest_retained_session_accepted_securities": len(latest_accepted),
        "coverage_session": target,
        "coverage_is_expected_session": calendar["expected_trading_session"] is not None,
        "configured_securities": len(identities),
        "accepted_securities": len(accepted),
        "missing_securities": len(missing),
        "missing_data_reasons": reasons,
        "missing_security_details": missing,
        "session_coverage_fraction": len(accepted) / len(identities) if identities else None,
        "daily_update_success_rate": None,
        "daily_update_success_rate_missing_evidence": (
            "COMPLETE_EXPECTED_SESSION_AND_RUN_SERIES_REQUIRED"
        ),
        "last_successful_run": {
            key: successful[-1].get(key) for key in ("run_id", "completed_at", "state")
        }
        if successful
        else None,
        "last_success_basis": "ACCEPTED_AT_LEAST_ONE_OBSERVATION_NOT_FULL_COHORT_COMPLETION",
        "latest_terminal": {
            key: terminals[-1].get(key)
            for key in ("run_id", "completed_at", "state", "error_code", "stage")
        }
        if terminals
        else None,
        "actual_api_attempts": counts,
        "terminal_reported_actual_attempts": sum(
            row.get("source_requests_last_run") or 0 for row in terminals
        ),
        "terminal_runs_with_unknown_actual_attempts": [
            row["run_id"] for row in terminals if row.get("source_requests_last_run") is None
        ],
        "reserved_quota_by_ist_day": by_day,
        "reservation_total": sum(by_day.values()),
        "reservation_runs_without_terminal_receipt": unknown_runs,
        "windows_task": task,
        "task_observation_stale": stale,
        "next_scheduled_run": task.get("next_run_at"),
        "next_scheduled_run_verified_current": not stale,
        "forecast_freshness": {
            "observation_session": scores.get("observation_session"),
            "created_at": scores.get(
                "generated_at", scores.get("created_at", scores.get("scored_at"))
            ),
            "saved_predictions": len(scores.get("candidates", [])),
            "matches_latest_retained_session": scores.get("observation_session") == latest,
            "matches_current_dataset": scores.get("dataset_id") == frame["dataset_id"],
            "fresh_for_expected_session": calendar["expected_trading_session"] is not None
            and scores.get("observation_session") == calendar["expected_trading_session"]
            and scores.get("dataset_id") == frame["dataset_id"],
        },
    }
