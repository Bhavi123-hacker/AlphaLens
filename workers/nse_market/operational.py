"""Guarded expanded-cohort execution. Preparation never registers a Windows task.

Recurring collection requires the exact separately recorded operator approval.
Every collecting attempt reserves its complete request ceiling before the first
provider GET. A crashed worker therefore cannot erase its daily reservation.
"""

from __future__ import annotations

import getpass
import math
import os
import re
import sys
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from alphalens_api.auth.permissions import verify
from alphalens_data.daily.storage import Store
from alphalens_data.providers.multi_contracts import Instrument
from workers.experimental_nse.acquire import PERMISSION, digest, encoded, initialize, private_path
from workers.nse_market import daily, diagnostics, engine
from workers.providers import universe
from workers.providers.credentials import load_token
from workers.providers.daily_clock import guard

SCHEDULED_PREFLIGHT_WAIT_SECONDS = 60.0


def _collection_preflight(
    config: Config,
    runs: Path,
    result: dict[str, Any],
    *,
    session: date | None,
    scheduled: bool,
) -> dict[str, Any]:
    """Called only under the kernel worker lock; no meter/reservation while waiting."""
    clock: dict[str, Any] = result["clock"]
    wait_started: float | None = None
    checks = 0
    while True:
        lower, upper = (datetime.fromisoformat(clock[key]) for key in ("lower_at", "upper_at"))
        if lower.tzinfo is None or upper.tzinfo is None or lower > upper:
            raise ValueError("EXPANDED_INDEPENDENT_CLOCK_BOUNDS_REJECTED")
        if session is not None and session > date.fromisoformat(clock["session_date"]):
            raise ValueError("EXPANDED_FUTURE_SESSION_REJECTED")
        previous = [engine._read(path) for path in runs.glob("*.started.json")]
        if any(datetime.fromisoformat(prior["clock_lower_at"]) > upper for prior in previous):
            raise ValueError("EXPANDED_INDEPENDENT_CLOCK_ROLLBACK")
        same_day = [prior for prior in previous if prior["quota_day"] == clock["session_date"]]
        if len(same_day) >= config.max_runs_per_day:
            raise ValueError("EXPANDED_DAILY_ATTEMPT_LIMIT")
        if (
            sum(prior["reserved_requests"] for prior in same_day) + config.max_requests_per_run
            > config.max_requests_per_day
        ):
            raise ValueError("EXPANDED_DAILY_REQUEST_RESERVATION_LIMIT")
        remaining = max(
            (
                (datetime.fromisoformat(prior["clock_upper_at"]) - lower).total_seconds()
                + config.cooldown_minutes * 60
                for prior in previous
            ),
            default=0.0,
        )
        elapsed = 0.0 if wait_started is None else time.monotonic() - wait_started
        if wait_started is not None:
            result["cooldown_preflight"]["elapsed_seconds"] = elapsed
            if elapsed > SCHEDULED_PREFLIGHT_WAIT_SECONDS:
                raise ValueError("EXPANDED_COOLDOWN_WAIT_TIMEOUT")
        if remaining <= 0:
            if wait_started is not None:
                result["cooldown_preflight"].update(state="SATISFIED", clock_checks=checks)
            return clock
        if not scheduled:
            raise ValueError("EXPANDED_MINIMUM_60_MINUTE_COOLDOWN")
        if wait_started is None:
            if remaining > SCHEDULED_PREFLIGHT_WAIT_SECONDS:
                raise ValueError("EXPANDED_COOLDOWN_WAIT_EXCEEDS_60_SECONDS")
            wait_started = time.monotonic()
            result["cooldown_preflight"] = {
                "state": "WAITING",
                "maximum_seconds": SCHEDULED_PREFLIGHT_WAIT_SECONDS,
                "initial_shortfall_seconds": remaining,
                "started_at": datetime.now(UTC).isoformat(),
            }
        budget = SCHEDULED_PREFLIGHT_WAIT_SECONDS - (time.monotonic() - wait_started)
        if budget <= 0 or remaining > budget:
            raise ValueError("EXPANDED_COOLDOWN_WAIT_TIMEOUT")
        diagnostics.emit(
            config.root,
            result["launch_id"],
            "COOLDOWN_WAIT",
            run_id=result["run_id"],
            wait_seconds=remaining,
        )
        # Recalculate from fresh bounds after each sleep; never assume sleeping proves eligibility.
        time.sleep(remaining)
        fresh = guard()
        checks += 1
        if datetime.fromisoformat(fresh["upper_at"]) < lower:
            raise ValueError("EXPANDED_INDEPENDENT_CLOCK_ROLLBACK")
        clock = fresh
        result["clock"] = clock
        # Recheck approval/cohort, credentials and daily accounting, including midnight.
        result["policy"] = policy(config)
        _approval(config, result["policy"])
        result["readiness"] = readiness(config)
        if not all(
            result["readiness"][key]
            for key in ("running_user_matches", "protected_credential_available")
        ):
            raise ValueError("EXPANDED_OPERATOR_OR_PROTECTED_CREDENTIAL_NOT_READY")


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    root: Path
    provider_root: Path
    v2_root: Path
    universe_root: Path | None = None
    expected_plan_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_securities: int = Field(ge=1, le=5000)
    run_user: str = Field(min_length=1, max_length=200)
    permission_reference: str = PERMISSION
    max_stocks_per_run: int = Field(default=250, ge=1, le=250)
    max_requests_per_run: int = Field(default=600, ge=1, le=600)
    max_requests_per_day: int = Field(default=1800, ge=1, le=1800)
    max_runs_per_day: int = Field(default=3, ge=1, le=3)
    cooldown_minutes: int = Field(default=60, ge=60, le=1440)
    cadence_ist: tuple[str, ...] = ("20:30", "21:30", "22:30")
    missed_trigger_at_next_login: bool = True
    recurring_acquisition_enabled: bool = False


def configured(path: Path) -> Config:
    if path.is_symlink():
        raise ValueError("EXPANDED_CONFIG_SYMLINK_REJECTED")
    verify(path, directory=False)
    result = Config.model_validate_json(path.read_bytes())
    for root in (result.root, result.provider_root, result.v2_root):
        if not root.is_absolute() or root.is_symlink():
            raise ValueError("ABSOLUTE_PROTECTED_LOCAL_ROOT_REQUIRED")
        verify(root)
    if result.universe_root is not None:
        if not result.universe_root.is_absolute() or result.universe_root.is_symlink():
            raise ValueError("ABSOLUTE_PROTECTED_UNIVERSE_ROOT_REQUIRED")
        verify(result.universe_root)
    if result.permission_reference != PERMISSION:
        raise ValueError("EXPANDED_PRIVATE_SOURCE_SCOPE_MISMATCH")
    if result.max_requests_per_day < result.max_requests_per_run:
        raise ValueError("DAILY_REQUEST_CEILING_BELOW_RUN_CEILING")
    if result.cadence_ist != ("20:30", "21:30", "22:30"):
        raise ValueError("EXACT_DECLARED_RECURRING_CADENCE_REQUIRED")
    return result


def policy(config: Config) -> dict[str, Any]:
    plan = engine._pointed(config.root, "plan-latest.json")
    if (
        plan["plan_id"] != config.expected_plan_id
        or len(plan["identities"]) != config.expected_securities
    ):
        raise ValueError("EXPANDED_EXACT_PREAPPROVED_COHORT_MISMATCH")
    values = config.model_dump(mode="json", exclude={"recurring_acquisition_enabled"})
    values.update(
        cohort_sha256=digest(encoded(plan["identities"])),
        original_reliance_task_modified=False,
        stock_requests_upper_bound_per_session=2 * config.expected_securities,
        session_timing_requests_upper_bound_per_run=70,
        instrument_master_refresh_requests_upper_bound_per_run=1,
        complete_session_batches=math.ceil(config.expected_securities / config.max_stocks_per_run),
        day_reservations_allow_complete_batches=(
            math.ceil(config.expected_securities / config.max_stocks_per_run)
            <= config.max_runs_per_day
            and math.ceil(config.expected_securities / config.max_stocks_per_run)
            * config.max_requests_per_run
            <= config.max_requests_per_day
            and config.max_requests_per_run >= 2 * config.max_stocks_per_run + 71
        ),
        new_model_training=False,
        accepted_ml_publication=False,
        whole_universe_acquisition_enabled=False,
        automatic_session_selection="LATEST_OFFICIALLY_COMPLETED_NSE_SESSION_MAX_31_CALENDAR_DAYS",
        bounded_catchup="LAST_OBSERVED_PLUS_ONE_TO_TARGET_MAX_31_DAYS_PER_INSTRUMENT",
    )
    values["policy_sha256"] = digest(encoded(values))
    return values


def _approval(config: Config, evidence: dict[str, Any]) -> None:
    if not config.recurring_acquisition_enabled:
        raise ValueError("EXPLICIT_EXPANDED_RECURRING_OPERATOR_APPROVAL_REQUIRED")
    receipt = engine._read(private_path(config.root, "operational", "collection-approval.json"))
    approved = datetime.fromisoformat(receipt["approved_at"])
    if (
        receipt.get("policy_sha256") != evidence["policy_sha256"]
        or receipt.get("approved_by") != "LOCAL_OPERATOR_EXPLICIT_USER_APPROVAL"
        or approved.tzinfo is None
        or approved > datetime.now(UTC)
    ):
        raise ValueError("EXACT_CADENCE_QUOTA_COHORT_APPROVAL_RECEIPT_REQUIRED")


def readiness(config: Config) -> dict[str, Any]:
    credential = False
    try:
        load_token()  # Protected current-user read only; never retain or print it.
        credential = True
    except (ValueError, OSError, RuntimeError):
        pass
    return {
        "platform": sys.platform,
        "running_user_matches": getpass.getuser() == config.run_user,
        "protected_credential_available": credential,
        "windows_interactive_task_required": True,
        "logged_in_operator_and_machine_required": True,
        "registered_by_this_workflow": False,
    }


def run(
    config: Config, *, session: date | None = None, collect: bool = False, scheduled: bool = False
) -> dict[str, Any]:
    initialize(config.root)
    with Store(private_path(config.root, "operational-control")).lock():
        return _run(config, session, collect=collect, scheduled=scheduled)


def _run(config: Config, session: date | None, *, collect: bool, scheduled: bool) -> dict[str, Any]:
    folder = private_path(config.root, "operational")
    folder.mkdir(exist_ok=True)
    runs = private_path(config.root, "operational", "runs")
    runs.mkdir(exist_ok=True)
    identifier = uuid.uuid4().hex
    result: dict[str, Any] = {
        "run_id": identifier,
        "started_at": datetime.now(UTC).isoformat(),
        "state": "STARTED",
        "source_requests_last_run": 0,
        "collection_requested": collect or scheduled,
        "scheduled": scheduled,
        "automatic_acquisition_enabled": False,
        "worker_pid": os.getpid(),
        "worker_parent_pid": os.getppid(),
        "launch_id": diagnostics.launch_id(),
    }
    try:
        engine._checked(runs / (identifier + ".attempt.json"), result)
        diagnostics.emit(config.root, result["launch_id"], "WORKER_STARTED", run_id=identifier)
        result["stage"] = "PREFLIGHT"
        evidence = policy(config)
        result["policy"] = evidence
        clock = guard()
        result["clock"] = clock
        if session is not None and session > date.fromisoformat(clock["session_date"]):
            raise ValueError("EXPANDED_FUTURE_SESSION_REJECTED")
        if scheduled:
            _approval(config, evidence)
        ready = readiness(config)
        result["readiness"] = ready
        if collect or scheduled:
            if not ready["running_user_matches"] or not ready["protected_credential_available"]:
                raise ValueError("EXPANDED_OPERATOR_OR_PROTECTED_CREDENTIAL_NOT_READY")
            clock = _collection_preflight(
                config, runs, result, session=session, scheduled=scheduled
            )
            engine._checked(
                runs / (identifier + ".started.json"),
                {
                    **result,
                    "quota_day": clock["session_date"],
                    "clock_lower_at": clock["lower_at"],
                    "clock_upper_at": clock["upper_at"],
                    "reserved_requests": config.max_requests_per_run,
                },
            )
        result["stage"] = "IDENTITY_VALIDATION" if collect or scheduled else "DRY_RUN"
        diagnostics.emit(
            config.root, result["launch_id"], "STAGE", run_id=identifier, stage=result["stage"]
        )
        if collect or scheduled:
            result["source_requests_last_run"] = None
            result["reserved_request_ceiling"] = config.max_requests_per_run
        meter = (
            engine.Meter(config.provider_root, config.max_requests_per_run)
            if collect or scheduled
            else None
        )
        identity_overrides = None
        if meter is not None:
            identity_overrides, result["identity_validation"] = _refresh_identities(
                config, meter, clock
            )
        if session is None:
            if not (collect or scheduled):
                result.update(
                    state="DRY_RUN",
                    automatic_session_selection="OFFICIAL_LOOKUP_PENDING_AT_COLLECTION_TIME",
                    source_requests_last_run=0,
                )
                result["completed_at"] = datetime.now(UTC).isoformat()
                target = runs / (identifier + ".done.json")
                engine._checked(target, result)
                engine._pointer(config.root, "operational-latest.json", target)
                diagnostics.emit(
                    config.root,
                    result["launch_id"],
                    "WORKER_FINISHED",
                    run_id=identifier,
                    stage="DRY_RUN",
                    exit_code=0,
                )
                return result
            result["stage"] = "SESSION_SELECTION"
            diagnostics.emit(
                config.root, result["launch_id"], "STAGE", run_id=identifier, stage=result["stage"]
            )
            session = _latest_completed(config.root, clock, meter)
        result["stage"] = "EOD_CAPTURE_AND_RESEARCH"
        diagnostics.emit(
            config.root, result["launch_id"], "STAGE", run_id=identifier, stage=result["stage"]
        )
        outcome = daily.run(
            config.root,
            config.provider_root,
            config.v2_root,
            session=session,
            max_stocks=config.max_stocks_per_run,
            max_requests=config.max_requests_per_run,
            collect=collect or scheduled,
            permission_reference=config.permission_reference,
            meter=meter,
            clock_evidence=clock,
            identity_overrides=identity_overrides,
        )
        result.update(
            state=outcome["state"],
            outcome=outcome,
            source_requests_last_run=outcome.get("api_calls", 0),
            automatic_acquisition_enabled=scheduled,
        )
    except KeyboardInterrupt:
        result.update(
            state="INTERRUPTED",
            error_code="CONTROL_INTERRUPT_OBSERVED",
            completed_at=datetime.now(UTC).isoformat(),
        )
        diagnostics.emit(
            config.root,
            result["launch_id"],
            "WORKER_INTERRUPTED",
            run_id=identifier,
            stage=result.get("stage"),
            code="CONTROL_INTERRUPT_OBSERVED",
        )
        target = runs / (identifier + ".interrupted.json")
        engine._checked(target, result)
        engine._pointer(config.root, "operational-latest.json", target)
        raise
    except (ValueError, OSError, KeyError, TypeError) as exc:
        reason = str(exc)
        result.update(
            state="FAILED",
            error_code=reason
            if re.fullmatch(r"[A-Z0-9_]+", reason)
            else "EXPANDED_OPERATIONAL_STAGE_FAILED",
            message=(
                "Update was not completed. Saved observations and forecasts remain preserved; "
                "check the reported guard before retrying."
            ),
        )
    result["completed_at"] = datetime.now(UTC).isoformat()
    target = runs / (identifier + ".done.json")
    engine._checked(target, result)
    engine._pointer(config.root, "operational-latest.json", target)
    diagnostics.emit(
        config.root,
        result["launch_id"],
        "WORKER_FINISHED",
        run_id=identifier,
        stage=result.get("stage"),
        code=result.get("error_code"),
        exit_code=1 if result["state"] == "FAILED" else 0,
    )
    return result


def _latest_completed(root: Path, clock: dict[str, Any], meter: Any) -> date:
    today = date.fromisoformat(clock["session_date"])
    lower = datetime.fromisoformat(clock["lower_at"])
    for offset in range(32):
        candidate = today - timedelta(days=offset)
        fact = daily._timing(root, candidate, meter)
        if fact is not None and datetime.fromisoformat(fact["close_at"]) < lower:
            return candidate
    raise ValueError("BOUNDED_OFFICIAL_COMPLETED_SESSION_LOOKUP_UNAVAILABLE")


def _refresh_identities(
    config: Config, meter: Any, clock: dict[str, Any]
) -> tuple[dict[str, Instrument], dict[str, Any]]:
    root = config.universe_root or config.root.parent / "nse-universe"
    current = universe.load(root)
    upper = datetime.fromisoformat(clock["upper_at"])
    age = (upper - current.observed_at).total_seconds()
    if age < 0:
        raise ValueError("CURRENT_IDENTITY_OBSERVATION_AFTER_INDEPENDENT_CLOCK")
    calls = meter.calls
    if age > 86400:
        current = universe.refresh(root, config.provider_root, client=meter)
    if (datetime.now(UTC) - current.observed_at).total_seconds() > 86400:
        raise ValueError("DAILY_FRESH_OFFICIAL_IDENTITY_MASTER_REQUIRED")
    latest = {item.provider_key: item for item in current.eligible}
    plan = engine._pointed(config.root, "plan-latest.json")
    selected: dict[str, Instrument] = {}
    excluded: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    for previous in plan["identities"]:
        key = previous["provider_key"]
        identity = latest.get(key)
        if identity is None:
            excluded.append(
                {
                    "key": key,
                    "reason": "ABSENT_OR_RECLASSIFIED_CURRENT_COMMON_EQUITY_REQUIRES_REVIEW",
                }
            )
            continue
        selected[key] = identity
        if any(
            previous.get(field) != getattr(identity, field)
            for field in ("symbol", "series", "instrument_type")
        ):
            changed.append(
                {
                    "key": key,
                    "previous_symbol": previous["symbol"],
                    "current_symbol": identity.symbol,
                    "current_series": identity.series,
                    "historical_identity_not_rewritten": True,
                }
            )
    return selected, {
        "master_snapshot_id": current.snapshot_id,
        "master_observed_at": current.observed_at.isoformat(),
        "metadata_gets": meter.calls - calls,
        "configured_keys": len(plan["identities"]),
        "still_eligible_keys": len(selected),
        "excluded": excluded,
        "changed": changed,
        "new_unapproved_keys_added": 0,
    }
