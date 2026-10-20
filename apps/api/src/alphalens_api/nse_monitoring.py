"""Display-only observations. Never acquire provider data or change scheduler state."""

from __future__ import annotations

import copy
import importlib
import sys
import threading
import time
from concurrent.futures import Future
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workers.nse_market.task_observation import NAME

_LOCK = threading.Lock()
_CACHE: tuple[float, dict[str, Any]] | None = None
_QUERY: Future[dict[str, Any]] | None = None


def _query_windows() -> dict[str, Any]:
    """Existing pywin32, local Task Scheduler COM getters only; no shell or writes."""
    com = importlib.import_module("pythoncom")
    client = importlib.import_module("win32com.client")
    service = task = None
    com.CoInitialize()
    try:
        service = client.Dispatch("Schedule.Service")
        service.Connect()
        task = service.GetFolder("\\").GetTask(NAME)
        states = {0: "Unknown", 1: "Disabled", 2: "Queued", 3: "Ready", 4: "Running"}
        return {
            "state": states[int(task.State)],
            "enabled": bool(task.Enabled),
            "last_result": int(task.LastTaskResult) & 0xFFFFFFFF,
            "last_run_at": task.LastRunTime.astimezone(UTC).isoformat(),
            "next_run_at": task.NextRunTime.astimezone(UTC).isoformat(),
        }
    finally:
        # Release apartment-bound proxies before uninitializing their owning thread.
        # Otherwise pywin32 can report IUnknown release exceptions after the query.
        task = service = None
        com.CoUninitialize()


def _bounded_query() -> dict[str, Any]:
    global _QUERY
    if _QUERY is None or _QUERY.done():
        future: Future[dict[str, Any]] = Future()
        _QUERY = future

        def run() -> None:
            try:
                future.set_result(_query_windows())
            except Exception:
                # COM errors may include local details; expose only unavailable state.
                future.set_exception(ValueError("LOCAL_TASK_QUERY_UNAVAILABLE"))

        threading.Thread(target=run, name="alphalens-task-read", daemon=True).start()
    # A stalled COM call retains one daemon only; subsequent reads cannot spawn more.
    return _QUERY.result(timeout=5)


def windows_observation(saved: dict[str, Any], *, at: datetime) -> dict[str, Any]:
    """Bound one fixed, read-only local query to once per minute; save no facts."""
    global _CACHE
    fallback = dict(saved, observation_source="SAVED_WINDOWS_OBSERVATION")
    try:
        age = (at - datetime.fromisoformat(saved["observed_at"])).total_seconds()
        fallback.update(age_seconds=max(0, age), stale=age < 0 or age > 300)
    except (KeyError, ValueError, TypeError):
        fallback.update(stale=True, age_seconds=None)
    if sys.platform != "win32":
        return dict(fallback, live_query_state="UNAVAILABLE_ON_THIS_PLATFORM")
    with _LOCK:
        if _CACHE is not None and 0 <= time.monotonic() - _CACHE[0] < 60:
            result = copy.deepcopy(_CACHE[1])
        else:
            try:
                raw = _bounded_query()
                if (
                    type(raw.get("last_result")) is not int
                    or type(raw.get("enabled")) is not bool
                    or raw.get("state") not in {"Ready", "Running", "Disabled", "Queued", "Unknown"}
                ):
                    raise ValueError("WINDOWS_QUERY_SCHEMA_INVALID")
                for name in ("last_run_at", "next_run_at"):
                    if datetime.fromisoformat(raw[name]).utcoffset() is None:
                        raise ValueError("WINDOWS_QUERY_TIME_INVALID")
                result = {
                    **{
                        name: raw[name]
                        for name in (
                            "state",
                            "enabled",
                            "last_result",
                            "last_run_at",
                            "next_run_at",
                        )
                    },
                    "observed_at": datetime.now(UTC).isoformat(),
                    "observation_source": "WINDOWS_LOCAL_READ_ONLY",
                    "live_query_state": "AVAILABLE",
                    "provider_requests": 0,
                    "tasks_modified": False,
                }
            except (OSError, ValueError, KeyError, TypeError, TimeoutError):
                result = {"live_query_state": "UNAVAILABLE_OR_TIMEOUT"}
            _CACHE = (time.monotonic(), result)
    if result.get("live_query_state") != "AVAILABLE":
        return dict(fallback, **result)
    age = (datetime.now(UTC) - datetime.fromisoformat(result["observed_at"])).total_seconds()
    return dict(result, age_seconds=max(0, age), stale=age < 0 or age > 300)


def enrich(data: dict[str, Any], root: Path, *, at: datetime) -> None:
    """Separate full-cohort coverage, collection results and local task facts."""
    operations = data.setdefault("operations", {})
    saved = operations.get("windows_task", {})
    operations["windows_task_saved"] = saved
    # No local task query for unconfigured/TEST_ONLY fixture workspaces.
    operations["windows_task"] = (
        windows_observation(saved, at=at)
        if operations.get("scheduler")
        else dict(saved, stale=True, observation_source="SAVED_WINDOWS_OBSERVATION")
    )
    coverage = data.get("coverage", {})
    session = coverage.get("end")
    rows = coverage.get("per_security", [])
    if not isinstance(session, str) or not isinstance(rows, list):
        return
    verified = {r["key"] for r in rows if r.get("last") == session}
    missing = {r["key"] for r in rows if r.get("last") != session}
    missing.update(r["key"] for r in coverage.get("not_observed", []) if "key" in r)
    configured = coverage.get("configured_securities")
    pending = configured - len(verified) if type(configured) is int else len(missing)
    if pending < 0:
        raise ValueError("SESSION_COVERAGE_EXCEEDS_CONFIGURED_COHORT")
    failures = operations.get("collection", {}).get("failures", [])
    failed = {
        r.get("key")
        for r in failures
        if r.get("key") in missing
        and "PUBLICATION_PENDING" not in str(r.get("reason", r.get("state", "")))
    }
    operations["session_status"] = {
        "session": session,
        "configured_securities": coverage.get("configured_securities"),
        "updated_or_already_verified": len(verified),
        "pending_securities": pending,
        "failed_securities": len(failed),
        "failed_is_subset_of_pending": True,
        "basis": "FULL_SAVED_COHORT_NOT_LAST_BATCH_OR_SHORTLIST",
    }
    operations["monitoring_read_at"] = at.isoformat()
    scores = data.get("scores") or {}
    operations["forecast_publication"] = {
        "observation_session": scores.get("observation_session"),
        "inference_at": scores.get("generated_at"),
        "scored_securities": scores.get("scored_securities"),
        "new_forecasts_last_scoring_batch": scores.get("new_forecasts"),
        "basis": "LAST_SAVED_SCORING_BATCH_NOT_TOTAL_FORECAST_LEDGER",
    }
