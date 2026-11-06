"""Actual bounded local probes, separate from production/data-rights readiness."""

import http.client
import os
import shutil
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query, Request
from workers.alerts.store import AlertStore
from workers.daily.forward import ForwardStore

from alphalens_api.auth.store import AuthStore
from alphalens_api.core.config import Settings
from alphalens_api.core.domain_errors import APIError
from alphalens_api.health import _check_database_sync
from alphalens_api.services import ResearchService, response
from alphalens_data.daily.storage import Store

from .store import OperationsStore

router = APIRouter(prefix="/api/v1/operations", tags=["local operations"])


def probe_api(port: int) -> bool:
    """Bounded loopback process liveness; no credentials or private response data."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
    try:
        connection.request("GET", "/api/v1/health/live")
        reply = connection.getresponse()
        import json

        return reply.status == 200 and json.loads(reply.read(4096)) == {
            "status": "alive",
            "scope": "foundation_only",
        }
    except (OSError, ValueError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def inspect(settings: Settings, *, api_responding: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    components: dict[str, Any] = {}

    def add(name: str, status: str, reason: str, **details: Any) -> None:
        components[name] = {"status": status, "reason": reason, **details}

    add(
        "api",
        "HEALTHY" if api_responding else "UNAVAILABLE",
        "PROCESS_RESPONDING" if api_responding else "NO_VERIFIED_HTTP_LISTENER",
    )
    add("live_source", "BLOCKED_BY_POLICY", "NO_APPROVED_ONGOING_SOURCE")
    add("current_inference", "BLOCKED_BY_POLICY", "MODEL_AND_DATA_GATES_NOT_CLEARED")
    for name, root in (
        ("research_data", settings.research_data_root),
        ("research_runs", settings.research_run_root),
        ("research_reports", settings.research_report_root),
    ):
        add(
            name,
            "NOT_CONFIGURED"
            if root is None
            else "HEALTHY"
            if root.is_dir() and os.access(root, os.R_OK | os.X_OK)
            else "UNAVAILABLE",
            "PATH_NOT_CONFIGURED"
            if root is None
            else "PATH_ACCESSIBLE"
            if root.is_dir() and os.access(root, os.R_OK | os.X_OK)
            else "PATH_INACCESSIBLE",
        )
    if settings.auth_root is None:
        add("authentication", "NOT_CONFIGURED", "AUTH_ROOT_NOT_CONFIGURED")
    else:
        try:
            with AuthStore(settings.auth_root).connection() as c:
                account = c.execute("SELECT status FROM accounts").fetchone()
                failures = c.execute(
                    "SELECT count(*) FROM audit WHERE event_type IN "
                    "('LOGIN_FAILED','LOGIN_RATE_LIMITED','PASSWORD_VERIFICATION_FAILED') "
                    "AND event_at>=?",
                    (time.time() - 300,),
                ).fetchone()[0]
                sessions = c.execute(
                    "SELECT count(*) FROM sessions WHERE revoked_at IS NULL "
                    "AND absolute_expires>? AND last_seen>?",
                    (time.time(), time.time() - 1800),
                ).fetchone()[0]
            add(
                "authentication",
                "NOT_CONFIGURED"
                if not account
                else "BLOCKED_BY_POLICY"
                if account[0] != "ACTIVE"
                else "DEGRADED"
                if failures >= 5
                else "HEALTHY",
                "ACCOUNT_NOT_INITIALIZED"
                if not account
                else "ACCOUNT_DISABLED"
                if account[0] != "ACTIVE"
                else "AUTHENTICATION_FAILURE_BURST"
                if failures >= 5
                else "AUTH_STORE_ACCESSIBLE",
                active_sessions=sessions,
                failures_last_five_minutes=failures,
            )
        except (OSError, ValueError, sqlite3.Error):
            add("authentication", "UNAVAILABLE", "AUTH_STORE_INACCESSIBLE")
    if settings.catalog_path is None:
        add("catalog", "NOT_CONFIGURED", "CATALOG_NOT_CONFIGURED")
    else:
        try:
            with closing(ResearchService(settings).catalog.connection()) as c:
                count = c.execute("SELECT count(*) FROM securities").fetchone()[0]
            add("catalog", "HEALTHY", "VERIFIED_CATALOG_ACCESSIBLE", observed_identities=count)
        except (OSError, ValueError, sqlite3.Error, APIError):
            add("catalog", "UNAVAILABLE", "CATALOG_INACCESSIBLE_OR_INVALID")
    query_start = time.perf_counter()
    if settings.database_url is None:
        add("postgresql", "NOT_CONFIGURED", "DATABASE_NOT_CONFIGURED")
    else:
        reachable = _check_database_sync(settings.database_url.get_secret_value())
        add(
            "postgresql",
            "HEALTHY" if reachable else "UNAVAILABLE",
            "DATABASE_REACHABLE" if reachable else "DATABASE_UNAVAILABLE",
            query_ms=round((time.perf_counter() - query_start) * 1000, 3),
        )
    if settings.daily_root is None:
        add("daily_worker", "NOT_CONFIGURED", "DAILY_ROOT_NOT_CONFIGURED")
    else:
        try:
            if not settings.daily_root.is_dir():
                raise ValueError
            daily = Store(settings.daily_root)
            receipts = daily.receipts()
            pending = daily.checkpoints()
            latest = receipts[0] if receipts else None
            bad = latest and latest["state"] == "FAILED"
            add(
                "daily_worker",
                "DEGRADED" if pending or bad else "HEALTHY",
                "INTERRUPTED_OR_FAILED_RUN" if pending or bad else "RUN_STORE_ACCESSIBLE",
                run_count=len(receipts),
                successful_runs=sum(
                    r["state"] in {"COMPLETED", "COMPLETED_WITH_WARNINGS"} for r in receipts
                ),
                failed_runs=sum(r["state"] == "FAILED" for r in receipts),
                incomplete_count=len(pending),
                latest_state=latest["state"] if latest else "NOT_RUN",
                latest_session=latest["session"] if latest else None,
                latest_completed_at=latest["completed_at"] if latest else None,
                scheduling="DISABLED",
            )
        except (OSError, ValueError, KeyError):
            add("daily_worker", "UNAVAILABLE", "RUN_EVIDENCE_INACCESSIBLE_OR_INVALID")
    if (
        settings.daily_root is None
        or not (settings.daily_root / "prospective/prospective.sqlite3").is_file()
    ):
        add("prospective", "NOT_CONFIGURED", "FORECAST_STORE_NOT_INITIALIZED")
    else:
        try:
            forward = ForwardStore(settings.daily_root, test_only=settings.test_only_evidence)
            with forward.connection() as c:
                if c.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("FORECAST_STORE_INTEGRITY_FAILED")
                count = c.execute("SELECT count(*) FROM forecasts").fetchone()[0]
            add("prospective", "HEALTHY", "FORECAST_STORE_ACCESSIBLE", recorded_forecasts=count)
        except (OSError, ValueError, sqlite3.Error):
            add("prospective", "UNAVAILABLE", "FORECAST_STORE_INACCESSIBLE_OR_INVALID")
    if settings.alerts_root is None:
        add("notifications", "NOT_CONFIGURED", "ALERT_ROOT_NOT_CONFIGURED")
    else:
        try:
            with AlertStore(settings.alerts_root).connection() as c:
                total = c.execute("SELECT count(*) FROM alerts").fetchone()[0]
                failures = c.execute(
                    "SELECT count(*) FROM alerts WHERE delivery='FAILED'"
                ).fetchone()[0]
                pending_count = c.execute(
                    "SELECT count(*) FROM alerts WHERE delivery IN ('PENDING','RETRY_PENDING')"
                ).fetchone()[0]
            add(
                "notifications",
                "DEGRADED" if failures else "HEALTHY",
                "DELIVERY_FAILURE_RECORDED" if failures else "ALERT_STORE_ACCESSIBLE",
                retained_alerts=total,
                failed_deliveries=failures,
                pending_deliveries=pending_count,
            )
        except (OSError, ValueError, sqlite3.Error):
            add("notifications", "UNAVAILABLE", "ALERT_STORE_INACCESSIBLE")
    if settings.operations_root is None:
        add("operations", "NOT_CONFIGURED", "OPERATIONS_ROOT_NOT_CONFIGURED")
    else:
        try:
            history = OperationsStore(settings.operations_root).history(1)
            add(
                "operations",
                "HEALTHY",
                "OPERATIONS_STORE_ACCESSIBLE",
                recorded_probes=history["total"],
                pending_events=history["pending_alert_events"],
            )
            usage = shutil.disk_usage(settings.operations_root)
            low = usage.free < 2 * 1024**3 or usage.free / usage.total < 0.1
            add(
                "storage",
                "DEGRADED" if low else "HEALTHY",
                "LOW_STORAGE_CAPACITY" if low else "STORAGE_CAPACITY_AVAILABLE",
                free_bytes=usage.free,
                total_bytes=usage.total,
                warning_threshold="LESS_THAN_2_GIB_OR_10_PERCENT_FREE",
            )
        except (OSError, ValueError, sqlite3.Error):
            add("operations", "UNAVAILABLE", "OPERATIONS_STORE_INACCESSIBLE")
    degraded = any(
        v["status"] in {"UNAVAILABLE", "DEGRADED", "NOT_CONFIGURED"}
        for k, v in components.items()
        if k != "postgresql" or settings.database_url
    )
    for name in ("live_source", "daily_worker", "prospective"):
        components[name]["scope"] = "ORIGINAL_P19_PIPELINE_NOT_EXPANDED_NSE_WORKFLOW"
    return {
        "version": "p22.operations.v1",
        "observed_at": datetime.now(UTC).isoformat(),
        "status": "DEGRADED" if degraded else "HEALTHY",
        "components": components,
        "probe_duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "production_ready": False,
        "live_data_activation": "BLOCKED",
    }


@router.get("/status")
def status(request: Request) -> Any:
    return response(inspect(request.app.state.settings), "P22_ACTUAL_LOCAL_PROBES")


@router.get("/metrics")
def metrics(request: Request) -> Any:
    return response(request.app.state.metrics.snapshot(), "P22_CURRENT_PROCESS_MEASUREMENTS")


@router.get("/history")
def history(
    request: Request, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=5000)
) -> Any:
    root = request.app.state.settings.operations_root
    if root is None:
        raise APIError("OPERATIONS_NOT_CONFIGURED", "Recorded monitoring is not configured.")
    try:
        value = OperationsStore(root).history(limit, offset)
        if not request.app.state.settings.test_only_evidence and any(
            p["evidence"].get("classification") == "TEST_ONLY" for p in value["probes"]
        ):
            raise APIError(
                "TEST_ONLY_OPERATIONS_BLOCKED", "Test probes cannot be served as real operations."
            )
        return response(value, "P22_PERSISTED_PROBE_EVIDENCE")
    except (OSError, ValueError, sqlite3.Error):
        raise APIError(
            "OPERATIONS_UNAVAILABLE", "Recorded monitoring failed verification."
        ) from None
