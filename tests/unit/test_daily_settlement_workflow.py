"""Unit tests for AlphaLens daily prospective outcome settlement automation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.daily_settlement_workflow import (
    check_disk_reserve,
    check_market_calendar,
    execute_daily_settlement,
    print_scheduled_task_specification,
    verify_authoritative_market_data,
    write_atomic_receipt,
)


def test_check_disk_reserve_pass(tmp_path: Path) -> None:
    result = check_disk_reserve(tmp_path, min_free_gib=0.001)
    assert result["passed"] is True
    assert result["status"] == "DISK_RESERVE_OK"
    assert result["free_gib"] > 0


def test_check_disk_reserve_fail(tmp_path: Path) -> None:
    # Require an unreachably huge amount of free disk space
    result = check_disk_reserve(tmp_path, min_free_gib=10_000_000.0)
    assert result["passed"] is False
    assert result["status"] == "DISK_RESERVE_INSUFFICIENT"


def test_check_market_calendar_weekend() -> None:
    # 2026-11-01 is Sunday
    sunday = check_market_calendar("2026-11-01")
    assert sunday["is_trading_day"] is False
    assert sunday["status"] == "MARKET_SESSION_WEEKEND_NON_TRADING"
    assert sunday["weekday"] == "Sunday"

    # 2026-10-31 is Saturday
    saturday = check_market_calendar("2026-10-31")
    assert saturday["is_trading_day"] is False
    assert saturday["status"] == "MARKET_SESSION_WEEKEND_NON_TRADING"


def test_check_market_calendar_weekday() -> None:
    # 2026-11-02 is Monday
    monday = check_market_calendar("2026-11-02")
    assert monday["is_trading_day"] is True
    assert monday["status"] == "TRADING_DAY_CONFIRMED"
    assert monday["weekday"] == "Monday"


def test_check_market_calendar_invalid() -> None:
    invalid = check_market_calendar("not-a-date")
    assert invalid["is_trading_day"] is False
    assert invalid["status"] == "REJECTED_INVALID_DATE"


def test_verify_authoritative_market_data_missing(tmp_path: Path) -> None:
    res = verify_authoritative_market_data("2026-11-02", tmp_path)
    assert res["available"] is False
    assert res["status"] == "MARKET_DATA_UNAVAILABLE"


def test_write_atomic_receipt(tmp_path: Path) -> None:
    receipt_file = tmp_path / "sub" / "receipt.json"
    data = {"status": "SUCCESS", "records": 42}
    write_atomic_receipt(receipt_file, data)

    assert receipt_file.exists()
    loaded = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert loaded == data


def test_print_scheduled_task_specification(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    print_scheduled_task_specification(tmp_path)
    captured = capsys.readouterr().out
    spec = json.loads(captured)
    assert spec["task_name"] == "AlphaLens-Daily-Settlement-V2"
    assert spec["status"] == "UNREGISTERED_PENDING_OPERATOR_APPROVAL"
    assert spec["schedule"]["scheduled_time_ist"] == "23:30:00"
    assert "20:30" in spec["schedule"]["rationale"]


def test_execute_daily_settlement_insufficient_disk(tmp_path: Path) -> None:
    receipt = execute_daily_settlement(
        as_of_session="2026-11-02",
        min_free_gib=10_000_000.0,
        workspace_root=tmp_path,
    )
    assert receipt["status"] == "ABORTED_DISK_RESERVE_INSUFFICIENT"
    assert receipt["settlement_performed"] is False


def test_execute_daily_settlement_weekend(tmp_path: Path) -> None:
    receipt = execute_daily_settlement(
        as_of_session="2026-11-01",
        min_free_gib=0.001,
        workspace_root=tmp_path,
    )
    assert receipt["status"] == "MARKET_SESSION_WEEKEND_NON_TRADING"
    assert receipt["settlement_performed"] is False


def test_execute_daily_settlement_market_data_missing(tmp_path: Path) -> None:
    # Empty workspace root has no market data files
    receipt = execute_daily_settlement(
        as_of_session="2026-11-02",
        min_free_gib=0.001,
        workspace_root=tmp_path,
    )
    assert receipt["status"] == "MARKET_DATA_UNAVAILABLE"
    assert receipt["settlement_performed"] is False


def test_execute_daily_settlement_dry_run_with_mocked_data(tmp_path: Path) -> None:
    with (
        patch("scripts.daily_settlement_workflow.verify_authoritative_market_data") as mock_data,
        patch("scripts.daily_settlement_workflow.check_disk_reserve") as mock_disk,
    ):
        mock_disk.return_value = {"passed": True, "free_gib": 50.0}
        mock_data.return_value = {
            "available": True,
            "status": "MARKET_DATA_VERIFIED",
            "session": "2026-11-02",
        }

        receipt = execute_daily_settlement(
            as_of_session="2026-11-02",
            dry_run=True,
            workspace_root=tmp_path,
        )
        assert receipt["status"] == "DRY_RUN_SUCCESS"
        assert receipt["dry_run"] is True
        assert receipt["settlement_performed"] is False
        assert (tmp_path / "docs" / "ml" / "daily_settlement_receipt_2026-11-02.json").exists()
