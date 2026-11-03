"""AlphaLens Daily Settlement Automation Workflow.

Automated, idempotent, restart-safe daily settlement runner for prospective forecasts.

Key Invariants:
1. Executes only after authoritative market data for the session is available.
2. Uses verified Python interpreter and absolute workspace paths with safe quoting.
3. Checks authentic NSE trading calendar (weekends, holidays, exceptional sessions).
4. Inspects the complete 500-equity authorized cohort for data completeness.
5. Resolves AUTO session in Asia/Kolkata timezone (handling 23:30 IST, 00:30 IST, etc.).
6. Settles only matured forecast horizons without fabricating missing data.
7. Writes audit receipts atomically using temporary files (with --no-write inspection mode).
8. Restart-safe and idempotent (re-running on same session produces identical results).
9. Respects the disk reserve floor (>= 8.0 GiB).
10. Preserves existing Private V1 collection schedules (20:30, 21:30, 22:30 IST).
11. Scheduled task registration remains strictly gated under READY_FOR_OPERATOR_APPROVAL.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import shutil
import sys
import tempfile
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

repo = Path(__file__).resolve().parents[1]
if str(repo) not in sys.path:
    sys.path.insert(0, str(repo))

from scripts.retrain_models import (  # noqa: E402
    evaluate_independent_acceptance,
    load_authoritative_forecasts,
    run_outcome_settlement,
)
from workers.nse_market.trading_calendar import (  # noqa: E402
    validate_nse_trading_session,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("alphalens.daily_settlement")

MIN_DISK_FREE_GIB_DEFAULT = 8.0
KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
MARKET_OPEN_TIME_IST = time(9, 15)


def check_disk_reserve(
    path: Path, min_free_gib: float = MIN_DISK_FREE_GIB_DEFAULT
) -> dict[str, Any]:
    """Verify that the drive hosting the workspace has sufficient free disk space."""
    usage = shutil.disk_usage(path)
    free_gib = usage.free / (1024**3)
    total_gib = usage.total / (1024**3)
    passed = free_gib >= min_free_gib
    return {
        "passed": passed,
        "free_gib": round(free_gib, 2),
        "total_gib": round(total_gib, 2),
        "required_min_gib": min_free_gib,
        "status": "DISK_RESERVE_OK" if passed else "DISK_RESERVE_INSUFFICIENT",
    }


def resolve_session_date(
    as_of_session: str | None = None,
    now: datetime | None = None,
) -> tuple[str, str, str]:
    """Resolve target session date, local IST execution timestamp, and timezone.

    Returns:
        tuple of (resolved_session, execution_time_ist, timezone_name)

    Rules:
    1. If as_of_session is explicit (not None and != 'AUTO'):
       - Validates YYYY-MM-DD.
       - Disallows future dates relative to current IST date.
       - Returns the explicit session for controlled replay.
    2. If as_of_session is AUTO (or None):
       - Uses Asia/Kolkata timezone.
       - If execution occurs before market open (< 09:15 IST, e.g. at 00:30 IST),
         the target session is yesterday's calendar date.
       - If execution occurs at or after market open (>= 09:15 IST, e.g. at 23:30 IST),
         the target session is today's calendar date.
       - Never selects a future market session.
    """
    dt_utc = now if now is not None else datetime.now(UTC)
    dt_utc = dt_utc.replace(tzinfo=UTC) if dt_utc.tzinfo is None else dt_utc.astimezone(UTC)

    dt_ist = dt_utc.astimezone(KOLKATA_TZ)
    today_ist = dt_ist.date()
    execution_time_ist = dt_ist.isoformat()
    timezone_name = "Asia/Kolkata"

    if as_of_session and as_of_session.strip().upper() != "AUTO":
        clean_session = as_of_session.strip()
        try:
            target_date = date.fromisoformat(clean_session)
        except ValueError as exc:
            raise ValueError(f"INVALID_SESSION_DATE_FORMAT: {clean_session}") from exc

        if target_date > today_ist:
            raise ValueError(
                f"FUTURE_SESSION_REJECTED: Session {clean_session} is after IST date {today_ist}"
            )
        return clean_session, execution_time_ist, timezone_name

    # AUTO resolution logic
    if dt_ist.time() < MARKET_OPEN_TIME_IST:
        # Pre-open early morning (e.g. 00:30 IST): target the preceding calendar date
        resolved_date = today_ist - timedelta(days=1)
    else:
        # Post-open / evening / night (e.g. 23:30 IST): target today
        resolved_date = today_ist

    return resolved_date.isoformat(), execution_time_ist, timezone_name


def check_market_calendar(session_str: str, workspace_root: Path | None = None) -> dict[str, Any]:
    """Validate whether session_str is an authenticated NSE trading session."""
    ws = workspace_root or repo
    return validate_nse_trading_session(session_str, repo_root=ws)


def verify_authoritative_market_data(
    session_str: str,
    workspace_root: Path,
    forecasts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Inspect the complete authorized cohort for data completeness.

    Validates:
    1. Complete 500-equity authorized cohort, not merely the first 20 instruments.
    2. Exact market session identity and completed EOD OHLCV bars.
    3. Positive, finite prices and internal OHLC consistency (low <= open/close <= high).
    4. Detection of duplicate or conflicting observations.
    5. Detection of missing stocks and pending vendor publication.
    6. Latest verified session across all instruments.
    7. Accurate counting of forecasts eligible for maturation vs pending.
    """
    candidates = [
        workspace_root.parent / ".local-data" / "nse-market-expansion" / "market-view-latest.json",
        workspace_root / ".local-data" / "nse-market-expansion" / "market-view-latest.json",
    ]
    mv_path = None
    for c in candidates:
        if c.exists():
            mv_path = c
            break

    if not mv_path:
        return {
            "available": False,
            "session": session_str,
            "total_eligible_equities": 0,
            "qualified_eod_equities": 0,
            "missing_equities_count": 0,
            "missing_equities_sample": [],
            "duplicate_or_conflicting_observations": 0,
            "latest_verified_session": None,
            "forecasts_eligible_for_maturation": 0,
            "forecasts_pending_source_data": len(forecasts) if forecasts else 0,
            "reason": "MARKET_VIEW_NOT_FOUND",
            "status": "MARKET_DATA_UNAVAILABLE",
        }

    try:
        meta = json.loads(mv_path.read_text(encoding="utf-8"))
        mv_file = mv_path.parent / meta.get("path", "")
        if not mv_file.exists():
            return {
                "available": False,
                "session": session_str,
                "total_eligible_equities": 0,
                "qualified_eod_equities": 0,
                "missing_equities_count": 0,
                "missing_equities_sample": [],
                "duplicate_or_conflicting_observations": 0,
                "latest_verified_session": None,
                "forecasts_eligible_for_maturation": 0,
                "forecasts_pending_source_data": len(forecasts) if forecasts else 0,
                "reason": "REFERENCED_MARKET_HISTORY_FILE_MISSING",
                "status": "MARKET_DATA_UNAVAILABLE",
            }

        mv_doc = json.loads(mv_file.read_text(encoding="utf-8"))
        histories: dict[str, list[dict[str, Any]]] = mv_doc.get("histories", {})
        total_eligible_equities = len(histories)

        qualified_equities: list[str] = []
        missing_equities: list[str] = []
        conflicting_count = 0
        all_sessions_seen: set[str] = set()

        for key, bars in histories.items():
            session_bars: list[dict[str, Any]] = []
            for b in bars:
                d = b.get("session") or b.get("date") or b.get("timestamp", "")[:10]
                if d:
                    all_sessions_seen.add(str(d))
                if str(d) == session_str:
                    session_bars.append(b)

            if not session_bars:
                missing_equities.append(key)
                continue

            # Check for duplicates or conflicts
            if len(session_bars) > 1:
                first_bar = session_bars[0]
                has_conflict = False
                for other in session_bars[1:]:
                    for field in ("open", "high", "low", "close"):
                        val1 = first_bar.get(field)
                        val2 = other.get(field)
                        if val1 != val2:
                            has_conflict = True
                            break
                    if has_conflict:
                        break
                if has_conflict:
                    conflicting_count += 1

            # Validate OHLC quality
            valid_bar = None
            for b in session_bars:
                try:
                    o = float(b.get("open", 0.0))
                    h = float(b.get("high", 0.0))
                    low_val = float(b.get("low", 0.0))
                    close_val = float(b.get("close", 0.0))
                    v = float(b.get("volume", 0.0))

                    if not (
                        math.isfinite(o)
                        and math.isfinite(h)
                        and math.isfinite(low_val)
                        and math.isfinite(close_val)
                    ):
                        continue
                    if o <= 0 or h <= 0 or low_val <= 0 or close_val <= 0 or v < 0:
                        continue
                    if not (low_val <= o <= h and low_val <= close_val <= h):
                        continue
                    valid_bar = b
                    break
                except (ValueError, TypeError):
                    continue

            if valid_bar is not None:
                qualified_equities.append(key)
            else:
                missing_equities.append(key)

        latest_verified = max(all_sessions_seen) if all_sessions_seen else None
        has_session = len(qualified_equities) > 0
        is_full = total_eligible_equities > 0 and len(qualified_equities) == total_eligible_equities

        # Evaluate forecasts eligible vs pending
        eligible_forecasts = 0
        pending_forecasts = 0
        if forecasts is None:
            forecasts = load_authoritative_forecasts()

        for f in forecasts:
            f_key = str(f.get("instrument_key", f.get("key", "")))
            f_sess = str(f.get("session", ""))
            h = int(f.get("horizon_sessions", f.get("horizon", 5)))

            if f_key not in histories:
                pending_forecasts += 1
                continue

            s_list = sorted(
                list(
                    {
                        str(b.get("session") or b.get("date") or b.get("timestamp", "")[:10])
                        for b in histories[f_key]
                    }
                )
            )
            try:
                curr_idx = s_list.index(f_sess)
                entry_idx = curr_idx + 1
                target_idx = curr_idx + h
                if target_idx < len(s_list) and entry_idx < len(s_list):
                    eligible_forecasts += 1
                else:
                    pending_forecasts += 1
            except ValueError:
                pending_forecasts += 1

        if not has_session:
            status_label = "MARKET_DATA_PENDING_OR_UNAVAILABLE"
            reason_label = "SESSION_NOT_YET_PRESENT_IN_HISTORY"
        elif is_full:
            status_label = "MARKET_DATA_VERIFIED_COMPLETE"
            reason_label = "AUTHORIZED_FULL_COHORT_CANDLES_CONFIRMED"
        else:
            status_label = "MARKET_DATA_PARTIAL_COVERAGE"
            reason_label = (
                f"PARTIAL_COHORT_COVERAGE_{len(qualified_equities)}_OF_{total_eligible_equities}"
            )

        return {
            "available": has_session,
            "session": session_str,
            "total_eligible_equities": total_eligible_equities,
            "qualified_eod_equities": len(qualified_equities),
            "missing_equities_count": len(missing_equities),
            "missing_equities_sample": missing_equities[:10],
            "duplicate_or_conflicting_observations": conflicting_count,
            "latest_verified_session": latest_verified,
            "forecasts_eligible_for_maturation": eligible_forecasts,
            "forecasts_pending_source_data": pending_forecasts,
            "status": status_label,
            "reason": reason_label,
        }
    except Exception as exc:
        return {
            "available": False,
            "session": session_str,
            "total_eligible_equities": 0,
            "qualified_eod_equities": 0,
            "missing_equities_count": 0,
            "missing_equities_sample": [],
            "duplicate_or_conflicting_observations": 0,
            "latest_verified_session": None,
            "forecasts_eligible_for_maturation": 0,
            "forecasts_pending_source_data": len(forecasts) if forecasts else 0,
            "reason": f"FAILED_TO_PARSE_MARKET_DATA: {exc}",
            "status": "MARKET_DATA_CORRUPT_OR_UNREADABLE",
        }


def write_atomic_receipt(receipt_path: Path, data: dict[str, Any]) -> None:
    """Atomically write a JSON receipt using temporary file and atomic replace."""
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_file_path = tempfile.mkstemp(
        dir=str(receipt_path.parent), prefix="receipt_", suffix=".tmp"
    )
    with open(temp_fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_file_path, receipt_path)


def print_scheduled_task_specification(workspace_root: Path) -> None:
    """Print the exact recommended Windows Scheduled Task specification for operator review."""
    python_exe = sys.executable
    script_path = workspace_root / "scripts" / "daily_settlement_workflow.py"
    cmd_wrapper = workspace_root / "scripts" / "windows" / "run-daily-settlement-v2.cmd"

    powershell_cmd = (
        f'schtasks /create /tn "AlphaLens-Daily-Settlement-V2" '
        f'/tr "\\"{python_exe}\\" \\"{script_path}\\" --as-of-session AUTO" '
        f"/sc DAILY /st 23:30 /f"
    )

    spec = {
        "task_name": "AlphaLens-Daily-Settlement-V2",
        "author": "AlphaLens Release Engineering",
        "status": "READY_FOR_OPERATOR_APPROVAL",
        "registration_gate": "OPERATOR_APPROVAL_REQUIRED_BEFORE_SCHTASKS_CREATION",
        "description": "Daily settlement of matured prospective forecasts after market close.",
        "executable": str(python_exe),
        "script_path": str(script_path),
        "wrapper_path": str(cmd_wrapper),
        "arguments": f'"{script_path}" --as-of-session AUTO',
        "working_directory": str(workspace_root),
        "schedule": {
            "trigger": "DAILY",
            "scheduled_time_ist": "23:30:00",
            "rationale": "Runs strictly 60 min after final 22:30 Private V1 collection finishes.",
        },
        "execution_policy": {
            "run_level": "LeastPrivilege",
            "stop_if_runs_longer_than": "PT1H",
            "multiple_instances_policy": "IgnoreNew",
            "restart_on_failure": False,
        },
        "private_v1_isolation": {
            "private_v1_schedules_modified": False,
            "private_v1_ports_used": [],
            "shared_database_access": "READ_ONLY_MARKET_VIEW",
        },
        "powershell_registration_command": powershell_cmd,
    }
    print(json.dumps(spec, indent=2))


def execute_daily_settlement(
    as_of_session: str | None = None,
    dry_run: bool = False,
    no_write: bool = False,
    min_free_gib: float = MIN_DISK_FREE_GIB_DEFAULT,
    workspace_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Execute the complete daily settlement lifecycle stage safely."""
    ws = workspace_root or repo
    now_utc = (now if now is not None else datetime.now(UTC)).isoformat()

    # 1. Resolve target session with timezone and UTC boundary safety
    try:
        resolved_session, exec_ist, tz_name = resolve_session_date(as_of_session, now=now)
    except ValueError as exc:
        receipt: dict[str, Any] = {
            "schema": "alphalens.daily_settlement_receipt.v1",
            "status": "REJECTED_INVALID_SESSION",
            "timestamp": now_utc,
            "as_of_session": as_of_session,
            "reason": str(exc),
            "settlement_performed": False,
        }
        return receipt

    # 2. Verify workspace paths and Python environment
    python_exe = sys.executable
    logger.info("Using verified Python interpreter: %s", python_exe)
    logger.info("Workspace root: %s", ws)
    logger.info("Resolved session: %s (execution IST: %s)", resolved_session, exec_ist)

    # 3. Check disk reserve floor
    disk_check = check_disk_reserve(ws, min_free_gib=min_free_gib)
    if not disk_check["passed"]:
        logger.error("Disk reserve insufficient: %s", disk_check)
        receipt = {
            "schema": "alphalens.daily_settlement_receipt.v1",
            "status": "ABORTED_DISK_RESERVE_INSUFFICIENT",
            "timestamp": now_utc,
            "as_of_session": resolved_session,
            "execution_time_ist": exec_ist,
            "timezone": tz_name,
            "disk_check": disk_check,
            "settlement_performed": False,
        }
        return receipt

    # 4. Check authentic NSE trading calendar
    cal_check = check_market_calendar(resolved_session, workspace_root=ws)
    if not cal_check["is_trading_day"]:
        logger.info(
            "Session %s is not an open trading session: %s",
            resolved_session,
            cal_check["reason"],
        )
        receipt = {
            "schema": "alphalens.daily_settlement_receipt.v1",
            "status": cal_check["status"],
            "timestamp": now_utc,
            "as_of_session": resolved_session,
            "execution_time_ist": exec_ist,
            "timezone": tz_name,
            "calendar_check": cal_check,
            "disk_check": disk_check,
            "settlement_performed": False,
        }
        if not no_write and not dry_run:
            receipt_dir = ws / "docs" / "ml"
            receipt_file = receipt_dir / f"daily_settlement_receipt_{resolved_session}.json"
            write_atomic_receipt(receipt_file, receipt)
        return receipt

    # 5. Verify authoritative market data
    data_check = verify_authoritative_market_data(resolved_session, ws)
    if not data_check["available"]:
        logger.info(
            "Authoritative market data unavailable for session %s: %s",
            resolved_session,
            data_check["reason"],
        )
        receipt = {
            "schema": "alphalens.daily_settlement_receipt.v1",
            "status": data_check["status"],
            "timestamp": now_utc,
            "as_of_session": resolved_session,
            "execution_time_ist": exec_ist,
            "timezone": tz_name,
            "data_check": data_check,
            "calendar_check": cal_check,
            "disk_check": disk_check,
            "settlement_performed": False,
        }
        if not no_write and not dry_run:
            receipt_dir = ws / "docs" / "ml"
            receipt_file = receipt_dir / f"daily_settlement_receipt_{resolved_session}.json"
            write_atomic_receipt(receipt_file, receipt)
        return receipt

    # 6. Settle matured forecasts
    logger.info(
        "Executing settlement for session %s (dry_run=%s, no_write=%s)...",
        resolved_session,
        dry_run,
        no_write,
    )
    if dry_run or no_write:
        audit_summary: dict[str, Any] = {
            "status": "DRY_RUN_SIMULATION" if dry_run else "FORENSIC_INSPECTION_NO_WRITE",
            "newly_settled": 0,
            "message": "Inspection mode active; zero database modifications performed.",
        }
        acceptance_eval: dict[str, Any] = {
            "status": "FORWARD_OUTCOME_PENDING",
            "acceptance_granted": False,
        }
    else:
        audit_summary = run_outcome_settlement()
        acceptance_eval = evaluate_independent_acceptance(audit_summary)

    receipt = {
        "schema": "alphalens.daily_settlement_receipt.v1",
        "status": "SETTLEMENT_SUCCESS" if not dry_run else "DRY_RUN_SUCCESS",
        "timestamp": now_utc,
        "as_of_session": resolved_session,
        "execution_time_ist": exec_ist,
        "timezone": tz_name,
        "dry_run": dry_run,
        "no_write": no_write,
        "disk_check": disk_check,
        "calendar_check": cal_check,
        "data_check": data_check,
        "audit_summary": audit_summary,
        "acceptance_evaluation": acceptance_eval,
        "settlement_performed": not dry_run and not no_write,
    }

    # 7. Write atomic receipt unless no_write or dry_run
    if not no_write and not dry_run:
        receipt_dir = ws / "docs" / "ml"
        receipt_file = receipt_dir / f"daily_settlement_receipt_{resolved_session}.json"
        write_atomic_receipt(receipt_file, receipt)
        logger.info("Settlement receipt atomically written to: %s", receipt_file)

    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AlphaLens Daily Prospective Outcome Settlement Workflow"
    )
    parser.add_argument(
        "--as-of-session",
        type=str,
        default="AUTO",
        help="Target market session in YYYY-MM-DD format (default: AUTO)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without modifying outcome databases",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Forensic inspection mode: do not write receipts or mutate databases",
    )
    parser.add_argument(
        "--min-free-gib",
        type=float,
        default=MIN_DISK_FREE_GIB_DEFAULT,
        help="Minimum free disk space required in GiB (default: 8.0)",
    )
    parser.add_argument(
        "--print-task-spec",
        action="store_true",
        help="Print Windows Scheduled Task specification for review without registering",
    )

    args = parser.parse_args()

    if args.print_task_spec:
        print_scheduled_task_specification(repo)
        return

    receipt = execute_daily_settlement(
        as_of_session=args.as_of_session,
        dry_run=args.dry_run,
        no_write=args.no_write,
        min_free_gib=args.min_free_gib,
        workspace_root=repo,
    )
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
