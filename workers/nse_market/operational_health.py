"""Single saved private operational report; no acquisition, task mutation or model fit."""

from __future__ import annotations

import gzip
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workers.experimental_nse.acquire import digest, encoded, initialize, private_path
from workers.nse_market import discovery, engine, reliability
from workers.providers import universe

DIRECTORY = "operational-readiness"


def _raw_identities(master_root: Path, master: universe.Snapshot) -> dict[str, dict[str, Any]]:
    raw = private_path(master_root, "master-" + master.summary["raw_sha256"] + ".json.gz")
    body = raw.read_bytes()
    if digest(body) != master.summary["raw_sha256"]:
        raise ValueError("OPERATIONAL_MASTER_RAW_CHECKSUM_REJECTED")
    with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
        unpacked = stream.read(128_000_001)
    if len(unpacked) > 128_000_000:
        raise ValueError("OPERATIONAL_MASTER_SIZE_REJECTED")
    rows = json.loads(unpacked)
    if not isinstance(rows, list):
        raise ValueError("OPERATIONAL_MASTER_ARRAY_REQUIRED")
    return {
        row["instrument_key"]: row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("instrument_key"), str)
    }


def gaps(
    root: Path,
    master_root: Path,
    master: universe.Snapshot,
    view: dict[str, Any],
    *,
    session: str | None,
) -> dict[str, Any]:
    """Separate current master eligibility from unknown historical tradability."""
    plan = engine._pointed(root, "plan-latest.json")
    identities = plan["identities"]
    current = {row["instrument_key"]: row for row in master.records}
    raw_master = _raw_identities(master_root, master)
    accepted = {row["key"] for row in view["rows"] if session and row.get("session") == session}
    configured = {row["provider_key"] for row in identities}
    details = []
    for identity in identities:
        key = identity["provider_key"]
        if key in accepted:
            continue
        folder = private_path(root, "daily", session or "UNKNOWN", str(identity["isin"]))
        attempts = []
        for kind in ("publication-attempts", "request-attempts", "action-attempts"):
            for path in sorted((folder / kind).glob("*.json")):
                attempt = engine._read(path)
                if attempt.get("key", key) != key:
                    raise ValueError("OPERATIONAL_ATTEMPT_IDENTITY_REJECTED")
                body = bytes.fromhex(attempt["raw_hex"]) if "raw_hex" in attempt else None
                if body is not None and digest(body) != attempt["raw_sha256"]:
                    raise ValueError("OPERATIONAL_ATTEMPT_RAW_CHECKSUM_REJECTED")
                candle_count = None
                if body is not None:
                    payload = json.loads(body)
                    nested = payload.get("data") if isinstance(payload, dict) else None
                    candles = nested.get("candles") if isinstance(nested, dict) else None
                    if isinstance(candles, list):
                        candle_count = len(candles)
                attempts.append(
                    {
                        "kind": kind,
                        "received_at": attempt["received_at"],
                        "state": attempt["state"],
                        "http_status": attempt.get("status"),
                        "http_status_basis": "EXPLICIT_SAVED_FIELD"
                        if "status" in attempt
                        else "NOT_RETAINED_IN_ORIGINAL_ATTEMPT_RECEIPT",
                        "returned_candles": candle_count,
                        "raw_sha256": attempt.get("raw_sha256", attempt.get("source_sha256")),
                    }
                )
        attempts.sort(key=lambda item: item["received_at"])
        history = [
            row
            for row in view.get("histories", {}).get(key, [])
            if row.get("close") is not None and session and row["session"] <= session
        ]
        last = max(history, key=lambda row: row["session"]) if history else None
        dated_master = current.get(key)
        action_path = engine._folder(root, engine._identity(identity)) / "actions.json"
        # Current normalized action evidence is only a reference, not exhaustive
        # proof of no suspension, delisting or entitlement on the missing date.
        action = engine._read(action_path) if action_path.exists() else None
        details.append(
            {
                **(
                    reliability._missing_reason(root, session, identity)
                    if session
                    else {
                        "key": key,
                        "symbol": identity["symbol"],
                        "isin": identity["isin"],
                        "reason": "EXPECTED_SESSION_CALENDAR_UNAVAILABLE",
                    }
                ),
                "instrument_token": key,
                "provider_identity_basis": "UPSTOX_INSTRUMENT_KEY",
                "exchange_token": raw_master.get(key, {}).get("exchange_token"),
                "exchange_token_observed_at": master.observed_at.isoformat(),
                "expected_trading_session": session,
                "last_accepted_candle": last,
                "last_candle_basis": "CHECKSUM_VERIFIED_SAVED_ACCEPTED_PROJECTION",
                "provider_response_history": attempts,
                "current_master_eligible": bool(
                    dated_master and dated_master["eligible_common_equity"]
                ),
                "master_observed_at": master.observed_at.isoformat(),
                "listed_on_expected_session": None,
                "tradable_on_expected_session": None,
                "valid_candle_expected": None,
                "session_eligibility_state": "UNVERIFIED_POINT_IN_TIME_TRADABILITY",
                "corporate_action_reference": action,
                "suspension_delisting_or_identity_change_explanation": (
                    "NOT_ESTABLISHED_BY_SAVED_EVIDENCE"
                ),
                "missing_evidence": [
                    "DATED_LISTING_TRADABILITY_OR_OFFICIAL_NO_TRADE_STATUS",
                    "NONEMPTY_VALID_CANDLE_OR_SOURCE_EXPLANATION_FOR_MISSING_SESSION",
                    "EXHAUSTIVE_ACTION_AND_IDENTITY_CONTINUITY_ASSESSMENT",
                ],
            }
        )
    return {
        "configured_securities": len(configured),
        "updated_securities": len(configured & accepted) if session else None,
        "missing_securities": len(configured - accepted) if session else None,
        "raw_configured_coverage": {
            "numerator": len(configured & accepted) if session else None,
            "denominator": len(configured),
            "measurement_status": "MEASURED_CONFIGURED_COHORT" if session else "NOT_YET_MEASURABLE",
        },
        "current_master_eligible_securities": sum(
            key in current and current[key]["eligible_common_equity"] for key in configured
        ),
        "historical_session_eligible_securities": None,
        "eligible_universe_coverage": None,
        "eligible_universe_status": "UNVERIFIED_POINT_IN_TIME_TRADABILITY",
        "missing_security_details": details,
        "denominator_policy": "NO_MISSING_SECURITY_IS_REMOVED_WITHOUT_DATED_ELIGIBILITY_EVIDENCE",
    }


def build(
    root: Path,
    v2_root: Path,
    master_root: Path,
    *,
    at: datetime,
    qualification: dict[str, Any] | None = None,
    task_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from alphalens_api import nse_evaluation
    from workers.nse_market import model_review

    if at.utcoffset() is None or at > datetime.now(UTC):
        raise ValueError("AWARE_OPERATIONAL_HEALTH_CLOCK_REQUIRED")
    bindings_before = source_bindings(root, v2_root, master_root)
    master = universe.load(master_root)
    view = engine._pointed(root, "market-view-latest.json")
    scores = engine._pointed(root, "scores-latest.json")
    calendar = reliability.expected_session(root, at=at)
    target = calendar["expected_trading_session"]
    coverage = gaps(root, master_root, master, view, session=target)
    evaluation = nse_evaluation.read(root, v2_root, at=at)
    review = model_review.registry(
        Path(__file__).resolve().parents[2], private_root=root.parent.absolute()
    )
    terminal = (
        engine._pointed(root, "operational-latest.json")
        if (root / "operational-latest.json").exists()
        else {}
    )
    saved_collection = (
        engine._pointed(root / "operational-monitoring-alerts", "health-latest.json")
        if (root / "operational-monitoring-alerts/health-latest.json").exists()
        else {}
    )
    source_clocks = [
        view.get("as_of"),
        scores.get("generated_at"),
        terminal.get("completed_at"),
        saved_collection.get("read_at"),
        master.observed_at.isoformat(),
    ]
    if any(
        datetime.fromisoformat(stamp).utcoffset() is None or datetime.fromisoformat(stamp) > at
        for stamp in source_clocks
        if stamp is not None
    ):
        raise ValueError("OPERATIONAL_SOURCE_AFTER_REPORT_CUTOFF")
    qualification_path = private_path(root, DIRECTORY, "qualification-latest.json")
    if qualification is None and qualification_path.exists():
        qualification = engine._pointed(root / DIRECTORY, "qualification-latest.json")
    if qualification is not None:
        qualification = validate_qualification(qualification)
    qualification = qualification or {}
    if qualification:
        qualification = validate_qualification(qualification)
        stamp = datetime.fromisoformat(qualification["observed_at"])
        if stamp > at:
            raise ValueError("OPERATIONAL_QUALIFICATION_CLOCK_REJECTED")
    quota = _quota(root, terminal.get("policy", {}), at=at)
    predicted = len(scores.get("candidates", []))
    bindings_after = source_bindings(root, v2_root, master_root)
    return {
        "observed_at": at.isoformat(),
        "classification": "PRIVATE_EXPERIMENTAL_RESEARCH",
        "provider_requests": 0,
        "task_changes": 0,
        "model_operations": 0,
        "latest_trading_session": target,
        "calendar": calendar,
        "latest_retained_session": view["latest_observed_session"],
        "source_dataset_id": view["dataset_id"],
        "score_snapshot_sha256": digest(encoded(scores)),
        "ledger_signature": ledger_signature(root, v2_root),
        "source_roots": {
            "v2_root": str(v2_root.absolute()),
            "master_root": str(master_root.absolute()),
        },
        "source_bindings": bindings_before,
        "build_inputs_changed": bindings_before != bindings_after,
        "qualification_sha256": digest(encoded(qualification)) if qualification else None,
        "universe": discovery.measure(master, view, at=at),
        "coverage": coverage,
        "predictions": {
            "genuine_saved_predictions": predicted,
            "observation_session": scores.get("observation_session"),
            "created_at": scores.get("generated_at"),
            "fresh_for_expected_session": target is not None
            and scores.get("observation_session") == target
            and scores.get("dataset_id") == view["dataset_id"],
            "classification": "EXPERIMENTAL_RESEARCH",
        },
        "forecasts": {
            name: evaluation.get(name)
            for name in (
                "raw_forecast_records",
                "unique_decisions",
                "matured_outcomes",
                "measurement_status",
                "status_counts",
                "metrics",
                "uncertainty",
            )
        },
        "model_acceptance": {
            name: review.get(name) for name in ("model_count", "accepted_models", "verdict_counts")
        },
        "collector_runtime": qualification.get(
            "collector_runtime", {"status": "BLOCKED_SECURITY", "reason": "AUDIT_NOT_ATTACHED"}
        ),
        "security": qualification.get(
            "security", {"status": "BLOCKED_SECURITY", "reason": "AUDIT_NOT_ATTACHED"}
        ),
        "qualification_observed_at": qualification.get("observed_at"),
        "provider_quota": quota,
        "quota_observation_at": at.isoformat(),
        "collection_snapshot": {
            "observed_at": saved_collection.get("read_at"),
            "actual_api_attempts": saved_collection.get("actual_api_attempts"),
            "last_failed_run": saved_collection.get("last_failed_run"),
            "last_successful_run": saved_collection.get("last_successful_run"),
            "last_success_basis": saved_collection.get("last_success_basis"),
            "basis": "SAVED_COLLECTION_REPORT_NOT_CURRENT_PROVIDER_PROBE",
        },
        "scheduler": task_observation or saved_collection.get("windows_task") or {},
        "last_scheduler_terminal": {
            key: terminal.get(key) for key in ("run_id", "state", "completed_at", "error_code")
        },
        "last_successful_data_publication": {
            "published_at": view.get("as_of"),
            "session": view["latest_observed_session"],
            "basis": "CHECKSUM_VERIFIED_DERIVED_PUBLICATION_NOT_FULL_COHORT_SUCCESS",
            "securities": view["latest_session_securities"],
        },
        "no_scheduler_exit_implies_collection_success": True,
        "public_deployment": "BLOCKED_APPROVAL",
        "public_market_data_rights": "BLOCKED_EXTERNAL_DATA",
    }


def _quota(root: Path, policy: dict[str, Any], *, at: datetime) -> dict[str, Any]:
    day = at.astimezone(reliability.IST).date().isoformat()
    runs = [engine._read(path) for path in (root / "operational/runs").glob("*.started.json")]
    today = [row for row in runs if row["quota_day"] == day]
    used = sum(row["reserved_requests"] for row in today)
    return {
        "ist_day": day,
        "approved_daily_reservation": policy.get("max_requests_per_day"),
        "approved_run_reservation": policy.get("max_requests_per_run"),
        "reserved_requests_used": used,
        "reserved_requests_remaining": max(0, policy["max_requests_per_day"] - used)
        if type(policy.get("max_requests_per_day")) is int
        else None,
        "run_slots_remaining": max(0, policy["max_runs_per_day"] - len(today))
        if type(policy.get("max_runs_per_day")) is int
        else None,
        "unused_capacity_authorizes_new_run": False,
        "basis": "CHECKSUM_VERIFIED_CURRENT_IST_DAY_RESERVATIONS",
    }


def ledger_signature(root: Path, v2_root: Path) -> str:
    """Detect append/checkpoint changes without opening or hashing live databases."""
    files = [v2_root / "price-only/experimental-v2-prospective.sqlite3"]
    files += sorted((root / "expanded-forecasts").glob("*/experimental-v2-prospective.sqlite3"))
    stamps = []
    for path in files:
        for item in (path, path.with_name(path.name + "-wal")):
            if any(parent.is_symlink() for parent in (item, *item.parents)):
                raise ValueError("OPERATIONAL_LEDGER_SYMLINK_REJECTED")
            if item.exists():
                stat = item.stat()
                stamps.append([str(item.absolute()), stat.st_size, stat.st_mtime_ns])
    return digest(encoded(stamps))


def source_bindings(root: Path, v2_root: Path, master_root: Path) -> dict[str, str]:
    """Small immutable receipts/pointers detect changes without replaying prices."""
    paths = [
        private_path(root, name)
        for name in (
            "market-view-latest.json",
            "scores-latest.json",
            "plan-latest.json",
            "operational-latest.json",
            "operational/config.json",
            "operational/collection-approval.json",
            "operational-monitoring-alerts/health-latest.json",
            "task-registration-latest.json",
            "task-observation-latest.json",
        )
    ]
    paths.append(private_path(master_root, "latest.json"))
    for folder, pattern in (
        ("calendar", "*.json"),
        ("session-links", "*.json"),
        ("operational", "*.json"),
        ("operational/runs", "*.started.json"),
    ):
        paths.extend(sorted(private_path(root, folder).glob(pattern)))
    bindings = {}
    for path in paths:
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("OPERATIONAL_SOURCE_BINDING_SYMLINK_REJECTED")
        bindings[str(path.absolute())] = digest(path.read_bytes()) if path.exists() else "ABSENT"
    bindings["ledger_signature"] = ledger_signature(root, v2_root)
    return bindings


def validate_qualification(value: dict[str, Any]) -> dict[str, Any]:
    """Allow only explicitly reviewed operator facts into the authenticated report."""
    allowed = {
        "collector_runtime": {
            "active_python",
            "active_dependency_advisories",
            "candidate_python",
            "candidate_dependency_advisories",
            "candidate_fingerprint_sha256",
            "cutover_status",
            "original_runtime_retained",
        },
        "security": {
            "container_high",
            "container_critical",
            "container_commit",
            "secret_findings_reviewed",
            "secret_findings_unexpected",
            "application_dependency_advisories",
            "evidence_status",
        },
    }
    if set(value) != {"observed_at", *allowed}:
        raise ValueError("OPERATIONAL_QUALIFICATION_FIELDS_REJECTED")
    stamp = datetime.fromisoformat(value["observed_at"])
    if stamp.utcoffset() is None:
        raise ValueError("OPERATIONAL_QUALIFICATION_CLOCK_REJECTED")
    for group, names in allowed.items():
        record = value[group]
        if not isinstance(record, dict) or set(record) - names:
            raise ValueError("OPERATIONAL_QUALIFICATION_FIELDS_REJECTED")
        for key, fact in record.items():
            if key.endswith(("advisories", "high", "critical", "reviewed", "unexpected")):
                valid = type(fact) is int and fact >= 0
            elif key == "original_runtime_retained":
                valid = type(fact) is bool
            else:
                valid = isinstance(fact, str) and 0 < len(fact) <= 500 and "\n" not in fact
            if not valid:
                raise ValueError("OPERATIONAL_QUALIFICATION_VALUE_REJECTED")
    return value


def publish(
    root: Path,
    data: dict[str, Any],
    *,
    qualification: dict[str, Any] | None = None,
) -> None:
    folder = private_path(root, DIRECTORY)
    initialize(folder)
    if qualification is not None:
        allowed = validate_qualification(qualification)
        target = folder / ("qualification-" + digest(encoded(allowed)) + ".json")
        if not target.exists():
            engine._checked(target, allowed)
        engine._pointer(folder, "qualification-latest.json", target)
    target = folder / ("health-" + digest(encoded(data)) + ".json")
    if not target.exists():
        engine._checked(target, data)
    engine._pointer(folder, "health-latest.json", target)


def load(root: Path, *, at: datetime) -> dict[str, Any]:
    folder = private_path(root, DIRECTORY)
    if not (folder / "health-latest.json").exists():
        return {"status": "UNAVAILABLE", "reason": "NO_UNIFIED_REPORT_PUBLISHED"}
    value = engine._pointed(folder, "health-latest.json")
    observed = datetime.fromisoformat(value["observed_at"])
    if observed.utcoffset() is None or observed > at:
        raise ValueError("OPERATIONAL_HEALTH_SNAPSHOT_CLOCK_REJECTED")
    view = engine._pointed(root, "market-view-latest.json")
    scores = engine._pointed(root, "scores-latest.json")
    roots = value.get("source_roots", {})
    v2_root = Path(roots.get("v2_root", root.parent / "experimental-nse-v2"))
    master_root = Path(roots.get("master_root", root.parent / "nse-universe"))
    current_bindings = source_bindings(root, v2_root, master_root)
    current_calendar = reliability.expected_session(root, at=at)
    current_day = at.astimezone(reliability.IST).date().isoformat()
    snapshot_day = value.get("provider_quota", {}).get(
        "ist_day", observed.astimezone(reliability.IST).date().isoformat()
    )
    current_qualification = (
        engine._pointed(folder, "qualification-latest.json")
        if (folder / "qualification-latest.json").exists()
        else None
    )
    qualification_changed = value.get("qualification_sha256") != (
        digest(encoded(current_qualification)) if current_qualification is not None else None
    )
    value["source_changed_since_report"] = (
        value["source_dataset_id"] != view["dataset_id"]
        or value["score_snapshot_sha256"] != digest(encoded(scores))
        or value["ledger_signature"] != ledger_signature(root, v2_root)
        or value.get("source_bindings") != current_bindings
        or value.get("build_inputs_changed", False)
        or qualification_changed
    )
    value["ist_day_changed_since_report"] = current_day != snapshot_day
    value["expected_session_changed_since_report"] = (
        value.get("latest_trading_session") != current_calendar["expected_trading_session"]
    )
    value["current_expected_session_observation"] = current_calendar
    value["quota_stale"] = (
        value["ist_day_changed_since_report"] or value["source_changed_since_report"]
    )
    value["snapshot_age_seconds"] = (at - observed).total_seconds()
    value["snapshot_stale"] = (
        value["snapshot_age_seconds"] > 86400
        or value["source_changed_since_report"]
        or value["ist_day_changed_since_report"]
        or value["expected_session_changed_since_report"]
    )
    value["qualification_stale"] = (
        value.get("qualification_observed_at") is None
        or qualification_changed
        or (at - datetime.fromisoformat(value["qualification_observed_at"])).total_seconds() > 86400
    )
    return value


def after_terminal(root: Path) -> None:
    """Only refresh an explicitly configured derived report; never activate a job."""
    folder = private_path(root, DIRECTORY)
    if not (folder / "qualification-latest.json").exists():
        return
    qualification = engine._pointed(folder, "qualification-latest.json")
    published = (
        engine._pointed(folder, "health-latest.json")
        if (folder / "health-latest.json").exists()
        else {}
    )
    roots = published.get("source_roots", {})
    data = build(
        root,
        Path(roots.get("v2_root", root.parent / "experimental-nse-v2")),
        Path(roots.get("master_root", root.parent / "nse-universe")),
        at=datetime.now(UTC),
        qualification=qualification,
    )
    publish(root, data)
