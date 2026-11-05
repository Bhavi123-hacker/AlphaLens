"""Unit and Integration Tests for Windows One-Click Operations and Daily Pipeline.

Tests:
1. start_alphalens: API already running (process reuse).
2. start_alphalens: API stopped, starts successfully.
3. start_alphalens: API startup failure / timeout.
4. start_alphalens: Database unavailable / integrity failure.
5. start_alphalens: Invalid virtualenv / missing dependencies.
6. daily_pipeline: Exchange holiday safe skip (exit 0).
7. daily_pipeline: Storage capacity / database unavailable failure.
8. daily_pipeline: Missing EOD market view failure.
9. daily_pipeline: Duplicate invocation lock prevention.
10. daily_pipeline: Stale lock recovery.
11. daily_pipeline: Complete successful 15-stage execution.
12. daily_pipeline: Safe retry / idempotency.
13. daily_pipeline: 601 quarantined outcomes isolation.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.daily_pipeline_orchestrator import (
    PipelineLock,
    main as pipeline_main,
    run_pipeline,
)
from scripts.start_alphalens import (
    check_python_environment,
    main as start_main,
)


# --- 1. START_ALPHALENS TESTS ---


def test_start_alphalens_api_already_running():
    """Verify that if API is already running, it reuses the instance and exits 0."""
    with (
        patch("scripts.start_alphalens.is_api_responding", return_value=True),
        patch("scripts.start_alphalens.check_database_and_integrity", return_value={"local_setup": "PASSED"}),
        patch("webbrowser.open") as mock_browser,
    ):
        exit_code = start_main(["--no-browser"])
        assert exit_code == 0
        mock_browser.assert_not_called()


def test_start_alphalens_api_stopped_starts_successfully():
    """Verify that if API is stopped, it spawns daemon, polls health, and exits 0."""
    call_count = 0

    def mock_probe(port=8041, timeout_sec=1.5):
        nonlocal call_count
        call_count += 1
        return call_count > 1  # False first, then True

    with (
        patch("scripts.start_alphalens.is_api_responding", side_effect=mock_probe),
        patch("scripts.start_alphalens.check_database_and_integrity", return_value={"local_setup": "PASSED"}),
        patch("scripts.start_alphalens.start_api_daemon", return_value=MagicMock()),
        patch("time.sleep"),
    ):
        exit_code = start_main(["--no-browser", "--timeout", "5"])
        assert exit_code == 0
        assert call_count >= 2


def test_start_alphalens_startup_failure_timeout():
    """Verify that if API fails to start within timeout, it reports error and exits 3."""
    with (
        patch("scripts.start_alphalens.is_api_responding", return_value=False),
        patch("scripts.start_alphalens.check_database_and_integrity", return_value={"local_setup": "PASSED"}),
        patch("scripts.start_alphalens.start_api_daemon", return_value=MagicMock()),
        patch("time.sleep"),
    ):
        exit_code = start_main(["--no-browser", "--timeout", "1"])
        assert exit_code == 3


def test_start_alphalens_database_unavailable():
    """Verify that if database check fails, it aborts with exit code 2."""
    with patch("scripts.start_alphalens.check_database_and_integrity", side_effect=RuntimeError("DB_CONNECTION_REFUSED")):
        exit_code = start_main(["--no-browser"])
        assert exit_code == 2


def test_start_alphalens_environment_check():
    """Verify python environment check catches missing dependencies."""
    # Current environment should pass
    check_python_environment()

    # Artificially test failure on missing package
    with patch("builtins.__import__", side_effect=ImportError("No module named 'fake_pkg'")):
        with pytest.raises(RuntimeError, match="Missing required packages"):
            check_python_environment()


# --- 2. DAILY PIPELINE ORCHESTRATOR TESTS ---


def test_daily_pipeline_holiday_safe_skip():
    """Verify that exchange holidays are cleanly skipped with exit code 0."""
    # Republic Day 2026-01-26 is a verified exchange holiday
    res = run_pipeline(session_override="2026-01-26", dry_run=True)
    assert res.get("status") == "SESSION_SKIPPED_HOLIDAY"
    assert res.get("session") == "2026-01-26"
    assert len(res.get("stages", [])) == 2
    assert res["stages"][1]["status"] == "SKIPPED_HOLIDAY"


def test_daily_pipeline_storage_unavailable_fails_stage_1(tmp_path):
    """Verify stage 1 fails if storage free space is below 8 GiB."""
    with patch("scripts.daily_settlement_workflow.check_disk_reserve") as mock_disk:
        mock_disk.return_value = {
            "passed": False,
            "free_gib": 2.1,
            "total_gib": 250.0,
            "required_min_gib": 8.0,
            "status": "DISK_RESERVE_INSUFFICIENT",
        }
        with pytest.raises(RuntimeError, match="Storage capacity insufficient"):
            run_pipeline(session_override="2026-11-04", dry_run=True, skip_holiday_check=True)


def test_daily_pipeline_missing_market_view_fails_stage_3():
    """Verify stage 3 fails if market-view pointer target is missing."""
    with patch("pathlib.Path.read_text", side_effect=FileNotFoundError("market-view-latest.json")):
        with pytest.raises(FileNotFoundError):
            run_pipeline(session_override="2026-11-04", dry_run=True, skip_holiday_check=True)


def test_daily_pipeline_duplicate_invocation_lock(tmp_path):
    """Verify PipelineLock detects an active process and prevents concurrent runs."""
    lock_file = tmp_path / "test_pipeline.lock"
    payload = {"pid": os.getpid(), "started_at": "2026-11-05T12:00:00Z"}
    lock_file.write_text(json.dumps(payload), encoding="utf-8")

    with patch("scripts.daily_pipeline_orchestrator.LOCK_FILE", lock_file):
        with pytest.raises(RuntimeError, match="Another daily pipeline process"):
            with PipelineLock(lock_file):
                pass


def test_daily_pipeline_stale_lock_recovery(tmp_path):
    """Verify PipelineLock automatically cleans up a stale lock from a dead PID."""
    lock_file = tmp_path / "test_pipeline.lock"
    # Use PID 99999999 which does not exist
    payload = {"pid": 99999999, "started_at": "2026-11-05T12:00:00Z"}
    lock_file.write_text(json.dumps(payload), encoding="utf-8")

    with patch("scripts.daily_pipeline_orchestrator.LOCK_FILE", lock_file):
        with PipelineLock(lock_file) as lock:
            assert lock.lock_path.exists()
            content = json.loads(lock.lock_path.read_text(encoding="utf-8"))
            assert content["pid"] == os.getpid()

    # On exit, lock should be cleanly deleted
    assert not lock_file.exists()


def test_daily_pipeline_complete_execution_and_report_generation():
    """Verify all 15 stages complete successfully on valid session 2026-11-04."""
    report = run_pipeline(session_override="2026-11-04", dry_run=True, skip_holiday_check=True)
    assert report.get("overall_status") == "SUCCESS"
    assert report.get("session") == "2026-11-04"
    assert len(report.get("stages", [])) == 15

    for s in report["stages"]:
        assert s["status"] == "PASSED", f"Stage {s['stage']} ({s['name']}) did not pass!"

    report_path = REPO_ROOT / "docs" / "operations" / "daily_pipeline_runs" / "pipeline_report_2026-11-04.json"
    assert report_path.exists()


def test_daily_pipeline_preserves_601_quarantine():
    """Verify stage 13 explicitly ensures 0 acceptance credit awarded to 601 quarantined outcomes."""
    report = run_pipeline(session_override="2026-11-04", dry_run=True, skip_holiday_check=True)
    stage_13 = report["stages"][12]
    assert stage_13["name"] == "Preserve 601 Legacy Quarantine"
    assert stage_13["status"] == "PASSED"
    assert stage_13["details"]["acceptance_credit_awarded"] == 0
    assert stage_13["details"]["total_legacy_outcomes"] == 601
    assert stage_13["details"]["status"] == "QUARANTINE_REVIEW_REQUIRED"


def test_daily_pipeline_idempotency_and_safe_retry():
    """Verify pipeline can be rerun multiple times without data corruption or state collision."""
    report1 = run_pipeline(session_override="2026-11-04", dry_run=True, skip_holiday_check=True)
    report2 = run_pipeline(session_override="2026-11-04", dry_run=True, skip_holiday_check=True)
    assert report1["overall_status"] == "SUCCESS"
    assert report2["overall_status"] == "SUCCESS"
    assert len(report1["stages"]) == 15
    assert len(report2["stages"]) == 15
