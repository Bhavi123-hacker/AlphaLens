"""Derived local collection monitoring; separate P20 store, never outbound delivery."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workers.alerts.contracts import Event
from workers.alerts.producer import reasons
from workers.alerts.store import AlertStore
from workers.experimental_nse.acquire import digest, encoded, initialize, private_path
from workers.nse_market import engine, reliability

DIRECTORY = "operational-monitoring-alerts"


def _conditions(status: dict[str, Any]) -> list[tuple[str, str, Any]]:
    result: list[tuple[str, str, Any]] = []
    if status.get("missing_securities", 0):
        result.append(
            (
                "DATA_MISSING",
                "PARTIAL_COHORT_COVERAGE",
                {
                    "session": status.get("coverage_session"),
                    "missing": status["missing_securities"],
                    "reasons": status.get("missing_data_reasons", {}),
                },
            )
        )
    failed = status.get("last_failed_run")
    if failed:
        result.append(("PIPELINE_FAILED", "WORKER_FAILURE_RECORDED", failed))
    unfinished = status.get("reservation_runs_without_terminal_receipt", [])
    if unfinished:
        result.append(
            ("PUBLICATION_INCOMPLETE", "WORKER_TERMINAL_RECEIPT_MISSING", sorted(unfinished))
        )
    freshness = status.get("forecast_freshness", {})
    if not freshness.get("fresh_for_expected_session", False):
        result.append(
            (
                "INFERENCE_BLOCKED",
                "FORECAST_FRESHNESS_UNVERIFIED",
                {
                    "observation_session": freshness.get("observation_session"),
                    "expected_session": status.get("expected_trading_session"),
                    "coverage_session": status.get("coverage_session"),
                    "saved_predictions": freshness.get("saved_predictions", 0),
                },
            )
        )
    quota = status.get("quota", {})
    remaining, required = (
        quota.get("reserved_requests_remaining"),
        quota.get("approved_run_reservation"),
    )
    if (type(remaining) is int and type(required) is int and remaining < required) or quota.get(
        "run_slots_remaining"
    ) == 0:
        result.append(
            (
                "SOURCE_BLOCKED",
                "APPROVED_COLLECTION_QUOTA_EXHAUSTED",
                {
                    key: quota.get(key)
                    for key in (
                        "ist_day",
                        "reserved_requests_remaining",
                        "run_slots_remaining",
                        "approved_run_reservation",
                    )
                },
            )
        )
    return result


def publish(
    root: Path, status: dict[str, Any], *, at: datetime, test_only: bool = False
) -> dict[str, Any]:
    """Only a fixed child is writable; original alert stores are never inputs."""
    if at.utcoffset() is None:
        raise ValueError("AWARE_COLLECTION_ALERT_CLOCK_REQUIRED")
    folder = private_path(root, DIRECTORY)
    initialize(folder)
    alerts = AlertStore(folder)
    private_path(root, DIRECTORY, "alerts.sqlite3")
    alerts.initialize()
    source = encoded(status)
    snapshot = private_path(root, DIRECTORY, "snapshots")
    snapshot.mkdir(exist_ok=True)
    identity = digest(source)
    target = snapshot / (identity + ".json")
    if not target.exists():
        engine._checked(target, status)
    elif engine._read(target) != status:
        raise ValueError("DERIVED_MONITORING_SNAPSHOT_CONFLICT")
    engine._pointer(folder, "health-latest.json", target)
    published = 0
    for code, reason, evidence in _conditions(status):
        fingerprint = digest(encoded([code, reason, evidence]))
        event = Event(
            code=code,
            component="P19",
            evidence_ref="nse-collection:" + identity,
            evidence_sha256=identity,
            event_at=at,
            time_basis="DETECTOR_OBSERVATION_TIME",
            classification="TEST_ONLY" if test_only else "UNVERIFIED_OPERATIONAL_EVIDENCE",
            mode="TEST_ONLY" if test_only else "RECORDED",
            reasons=reasons((reason,)),
            group="NSE_COLLECTION:" + reason,
            identity=fingerprint,
        )
        published += alerts.publish("NSE_COLLECTION:" + reason, fingerprint, [event], now=at)
    return {"alerts_published": published, "provider_requests": 0, "outbound_delivery": False}


def from_terminal(root: Path, terminal: dict[str, Any]) -> dict[str, Any]:
    """Lightweight automatic check after a durable terminal; never replays archives."""
    at = datetime.now(UTC)
    outcome = terminal.get("outcome", {})
    counts: dict[str, Any] = {}
    accepted_keys: set[str] | None = None
    dataset_id = None
    if (root / "market-view-latest.json").exists():
        view = engine._pointed(root, "market-view-latest.json")
        dataset_id = view["dataset_id"]
        accepted = sum(
            row.get("session") == view["latest_observed_session"] for row in view["rows"]
        )
        counts = {
            "coverage_session": view["latest_observed_session"],
            "accepted_securities": accepted,
            "configured_securities": view["configured_securities"],
            "missing_securities": view["configured_securities"] - accepted,
        }
        accepted_keys = {
            row["key"]
            for row in view["rows"]
            if row.get("session") == view["latest_observed_session"]
        }
    # A terminal's source frame is newer than a failed derived publication.
    if outcome.get("pending_count_basis") == "FULL_CONFIGURED_COHORT_AFTER_VALIDATION":
        if outcome["session"] != counts.get("coverage_session"):
            accepted_keys = None
            dataset_id = None
        counts.update(
            coverage_session=outcome["session"],
            accepted_securities=outcome["accepted_session_securities"],
            configured_securities=outcome["configured_securities"],
            missing_securities=outcome["pending_securities"],
        )
        if "accepted_session_keys" in outcome:
            accepted_keys = set(outcome["accepted_session_keys"])
        if outcome.get("dataset_id"):
            dataset_id = outcome["dataset_id"]
    missing_reasons: dict[str, int] = {}
    missing_details = []
    failure_reasons = {row["key"]: row["reason"] for row in outcome.get("failures", [])}
    failure_reasons.update(
        {
            key: "CURRENT_IDENTITY_EXCLUDED_PENDING_REVIEW"
            for key in outcome.get("identity_exclusions_pending_review", [])
        }
    )
    if accepted_keys is not None and (root / "plan-latest.json").exists():
        plan = engine._pointed(root, "plan-latest.json")
        for item in plan["identities"]:
            if item["provider_key"] in accepted_keys:
                continue
            detail = reliability._missing_reason(
                root,
                counts["coverage_session"],
                item,
                terminal_reason=failure_reasons.get(item["provider_key"]),
            )
            missing_details.append(detail)
            missing_reasons[detail["reason"]] = missing_reasons.get(detail["reason"], 0) + 1
    elif counts.get("missing_securities"):
        missing_reasons["SOURCE_ACCEPTANCE_IDENTITIES_NOT_IN_LEGACY_RECEIPT"] = counts[
            "missing_securities"
        ]
    calendar = reliability.expected_session(root, at=at)
    scores = (
        engine._pointed(root, "scores-latest.json")
        if (root / "scores-latest.json").exists()
        else {}
    )
    policy = terminal.get("policy", {})
    day = at.astimezone(reliability.IST).date().isoformat()
    reservations = [
        engine._read(path) for path in (root / "operational/runs").glob("*.started.json")
    ]
    current = [row for row in reservations if row["quota_day"] == day]
    previous = load(root)
    prior_terminals = [
        engine._read(path)
        for pattern in ("*.done.json", "*.interrupted.json")
        for path in (root / "operational/runs").glob(pattern)
    ]
    prior_terminals.sort(key=lambda row: row["completed_at"])
    prior_failures = [
        row for row in prior_terminals if row.get("state") in {"FAILED", "INTERRUPTED"}
    ]
    prior_successes = [
        row for row in prior_terminals if row.get("outcome", {}).get("new_daily_observations", 0)
    ]
    failed = (
        terminal
        if terminal.get("state") in {"FAILED", "INTERRUPTED"}
        else prior_failures[-1]
        if prior_failures
        else previous.get("last_failed_run")
    )
    successful = (
        terminal
        if outcome.get("new_daily_observations", 0)
        else prior_successes[-1]
        if prior_successes
        else previous.get("last_successful_run")
    )
    task = (
        engine._pointed(root, "task-observation-latest.json")
        if (root / "task-observation-latest.json").exists()
        else {}
    )
    actual_attempts = (
        reliability._request_counts(Path(policy["provider_root"]))
        if policy.get("provider_root")
        else {"available": False}
    )
    task_at = datetime.fromisoformat(task["observed_at"]) if task.get("observed_at") else None
    task_fresh = (
        task_at is not None
        and task_at.utcoffset() is not None
        and 0 <= (at - task_at).total_seconds() <= 300
    )
    terminal_ids = {
        path.name.split(".")[0]
        for pattern in ("*.done.json", "*.interrupted.json")
        for path in (root / "operational/runs").glob(pattern)
    }
    data = {
        "read_at": at.isoformat(),
        "provider_requests": 0,
        "tasks_modified": False,
        "basis": "DERIVED_TERMINAL_AND_SAVED_PRESENTATION_NOT_FULL_SOURCE_REPLAY",
        **calendar,
        **counts,
        "latest_retained_session": counts.get("coverage_session"),
        "coverage_is_expected_session": calendar["expected_trading_session"] is not None
        and counts.get("coverage_session") == calendar["expected_trading_session"],
        "daily_update_success_rate": None,
        "latest_terminal": {
            key: terminal.get(key) for key in ("run_id", "state", "completed_at", "error_code")
        },
        "last_failed_run": {
            key: failed.get(key) for key in ("run_id", "state", "completed_at", "error_code")
        }
        if failed
        else None,
        "last_successful_run": {
            key: successful.get(key) for key in ("run_id", "state", "completed_at")
        }
        if successful
        else None,
        "last_success_basis": "ACCEPTED_AT_LEAST_ONE_OBSERVATION_NOT_FULL_COHORT_COMPLETION",
        "actual_api_attempts": actual_attempts,
        "next_scheduled_run": task.get("next_run_at"),
        "task_observation_at": task.get("observed_at"),
        "next_scheduled_run_verified_current": task_fresh,
        "reservation_runs_without_terminal_receipt": [
            row["run_id"] for row in reservations if row["run_id"] not in terminal_ids
        ],
        "missing_data_reasons": missing_reasons,
        "missing_security_details": missing_details,
        "forecast_freshness": {
            "observation_session": scores.get("observation_session"),
            "saved_predictions": len(scores.get("candidates", [])),
            "fresh_for_expected_session": calendar["expected_trading_session"] is not None
            and scores.get("observation_session") == calendar["expected_trading_session"]
            and dataset_id is not None
            and scores.get("dataset_id") == dataset_id,
            "matches_current_dataset": dataset_id is not None
            and scores.get("dataset_id") == dataset_id,
        },
        "quota": {
            "ist_day": day,
            "approved_run_reservation": policy.get("max_requests_per_run"),
            "reserved_requests_used": sum(row["reserved_requests"] for row in current),
            "reserved_requests_remaining": max(
                0, policy["max_requests_per_day"] - sum(row["reserved_requests"] for row in current)
            )
            if type(policy.get("max_requests_per_day")) is int
            else None,
            "run_slots_remaining": max(0, policy["max_runs_per_day"] - len(current))
            if type(policy.get("max_runs_per_day")) is int
            else None,
        },
    }
    return publish(root, data, at=at)


def load(root: Path) -> dict[str, Any]:
    folder = private_path(root, DIRECTORY)
    if not (folder / "health-latest.json").exists():
        return {}
    return engine._pointed(folder, "health-latest.json")


def listing(root: Path, *, limit: int = 20, test_only: bool = False) -> dict[str, Any]:
    folder = private_path(root, DIRECTORY)
    if not private_path(root, DIRECTORY, "alerts.sqlite3").exists():
        return {"alerts": [], "total": 0, "provider_requests": 0, "outbound_delivery": False}
    rows, total = AlertStore(folder).listing(limit=limit, test_only=test_only)
    return {"alerts": rows, "total": total, "provider_requests": 0, "outbound_delivery": False}
