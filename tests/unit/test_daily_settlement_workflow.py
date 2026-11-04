"""Unit tests for AlphaLens daily prospective outcome settlement automation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from scripts.daily_settlement_workflow import (
    check_disk_reserve,
    check_market_calendar,
    execute_daily_settlement,
    print_scheduled_task_specification,
    resolve_session_date,
    verify_authoritative_market_data,
    write_atomic_receipt,
)

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")


def test_resolve_session_date_2330_ist() -> None:
    # 23:30 IST on 2026-11-03 corresponds to 18:00 UTC on 2026-11-03
    dt_2330_ist = datetime(2026, 11, 3, 23, 30, tzinfo=KOLKATA_TZ)
    session, exec_ist, tz_name = resolve_session_date(as_of_session="AUTO", now=dt_2330_ist)
    assert session == "2026-11-03"
    assert "2026-11-03T23:30:00" in exec_ist
    assert tz_name == "Asia/Kolkata"


def test_resolve_session_date_0030_ist() -> None:
    # 00:30 IST on 2026-11-04 is before market open; target must resolve to preceding day
    dt_0030_ist = datetime(2026, 11, 4, 0, 30, tzinfo=KOLKATA_TZ)
    session, exec_ist, tz_name = resolve_session_date(as_of_session="AUTO", now=dt_0030_ist)
    assert session == "2026-11-03"
    assert "2026-11-04T00:30:00" in exec_ist
    assert tz_name == "Asia/Kolkata"


def test_resolve_session_date_utc_ist_boundary() -> None:
    # 18:30 UTC on 2026-11-03 is 00:00 IST on 2026-11-04 (midnight boundary)
    dt_utc = datetime(2026, 11, 3, 18, 30, tzinfo=UTC)
    session, exec_ist, tz_name = resolve_session_date(as_of_session="AUTO", now=dt_utc)
    # Midnight in IST is before 09:15 open, so target session must be 2026-11-03
    assert session == "2026-11-03"


def test_resolve_session_date_explicit_historical() -> None:
    # Historical replay override
    dt_now = datetime(2026, 11, 3, 12, 0, tzinfo=KOLKATA_TZ)
    session, exec_ist, tz_name = resolve_session_date(as_of_session="2026-10-16", now=dt_now)
    assert session == "2026-10-16"


def test_resolve_session_date_rejects_future_session() -> None:
    # A date in the future relative to the current IST date must be rejected
    dt_now = datetime(2026, 11, 3, 12, 0, tzinfo=KOLKATA_TZ)
    with pytest.raises(ValueError, match="FUTURE_SESSION_REJECTED"):
        resolve_session_date(as_of_session="2026-11-10", now=dt_now)


def test_check_disk_reserve_pass(tmp_path: Path) -> None:
    result = check_disk_reserve(tmp_path, min_free_gib=0.001)
    assert result["passed"] is True
    assert result["status"] == "DISK_RESERVE_OK"
    assert result["free_gib"] > 0


def test_check_disk_reserve_fail(tmp_path: Path) -> None:
    result = check_disk_reserve(tmp_path, min_free_gib=10_000_000.0)
    assert result["passed"] is False
    assert result["status"] == "DISK_RESERVE_INSUFFICIENT"


def test_check_market_calendar_weekend() -> None:
    sunday = check_market_calendar("2026-11-01")
    assert sunday["is_trading_day"] is False
    assert sunday["status"] == "MARKET_SESSION_WEEKEND_NON_TRADING"


def test_check_market_calendar_holiday() -> None:
    holiday = check_market_calendar("2026-10-20")
    assert holiday["is_trading_day"] is False
    assert holiday["status"] == "VERIFIED_MARKET_HOLIDAY"


def test_check_market_calendar_weekday() -> None:
    monday = check_market_calendar("2026-11-02")
    assert monday["is_trading_day"] is True
    assert monday["status"] == "VERIFIED_TRADING_SESSION"


def test_check_market_calendar_invalid() -> None:
    invalid = check_market_calendar("not-a-date")
    assert invalid["is_trading_day"] is False
    assert invalid["status"] == "REJECTED_INVALID_DATE"


def test_verify_authoritative_market_data_missing(tmp_path: Path) -> None:
    res = verify_authoritative_market_data("2026-11-02", tmp_path, forecasts=[])
    assert res["available"] is False
    assert res["status"] == "MARKET_DATA_UNAVAILABLE"


def test_verify_authoritative_market_data_full_cohort_inspection(tmp_path: Path) -> None:
    # Build a simulated market view with complete cohort
    mv_dir = tmp_path / ".local-data" / "nse-market-expansion"
    mv_dir.mkdir(parents=True)
    hist_file = mv_dir / "market_view_test.json"

    # 10 instruments, 8 valid, 1 with corrupt prices, 1 missing session
    histories: dict[str, list[dict[str, Any]]] = {}
    for i in range(8):
        histories[f"NSE_EQ|INST_{i}"] = [
            {
                "session": "2026-11-02",
                "open": 100.0,
                "high": 105.0,
                "low": 98.0,
                "close": 102.0,
                "volume": 1000,
            }
        ]
    histories["NSE_EQ|CORRUPT"] = [
        {
            "session": "2026-11-02",
            "open": 100.0,
            "high": 90.0,
            "low": 110.0,
            "close": 95.0,
            "volume": 1000,
        }  # low > high
    ]
    histories["NSE_EQ|MISSING"] = [
        {
            "session": "2026-11-01",
            "open": 50.0,
            "high": 55.0,
            "low": 48.0,
            "close": 52.0,
            "volume": 500,
        }
    ]

    hist_file.write_text(json.dumps({"histories": histories}), encoding="utf-8")
    latest_meta = {"path": "market_view_test.json"}
    (mv_dir / "market-view-latest.json").write_text(json.dumps(latest_meta), encoding="utf-8")

    res = verify_authoritative_market_data("2026-11-02", tmp_path, forecasts=[])
    assert res["total_eligible_equities"] == 10
    assert res["qualified_eod_equities"] == 8
    assert res["missing_equities_count"] == 2
    assert "NSE_EQ|CORRUPT" in res["missing_equities_sample"]
    assert "NSE_EQ|MISSING" in res["missing_equities_sample"]
    assert res["status"] == "MARKET_DATA_PARTIAL_COVERAGE"


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
    assert spec["status"] == "READY_FOR_OPERATOR_APPROVAL"
    assert spec["schedule"]["scheduled_time_ist"] == "23:30:00"
    assert "schtasks /create" in spec["powershell_registration_command"]
    assert "--as-of-session AUTO" in spec["arguments"]


def test_execute_daily_settlement_insufficient_disk(tmp_path: Path) -> None:
    receipt = execute_daily_settlement(
        as_of_session="2026-11-02",
        min_free_gib=10_000_000.0,
        workspace_root=tmp_path,
        now=datetime(2026, 11, 2, 23, 30, tzinfo=KOLKATA_TZ),
    )
    assert receipt["status"] == "ABORTED_DISK_RESERVE_INSUFFICIENT"
    assert receipt["settlement_performed"] is False


def test_execute_daily_settlement_weekend(tmp_path: Path) -> None:
    receipt = execute_daily_settlement(
        as_of_session="2026-11-01",
        min_free_gib=0.001,
        workspace_root=tmp_path,
        now=datetime(2026, 11, 1, 23, 30, tzinfo=KOLKATA_TZ),
    )
    assert receipt["status"] == "MARKET_SESSION_WEEKEND_NON_TRADING"
    assert receipt["settlement_performed"] is False


def test_execute_daily_settlement_no_write_mode(tmp_path: Path) -> None:
    with (
        patch("scripts.daily_settlement_workflow.verify_authoritative_market_data") as mock_data,
        patch("scripts.daily_settlement_workflow.check_disk_reserve") as mock_disk,
    ):
        mock_disk.return_value = {"passed": True, "free_gib": 50.0}
        mock_data.return_value = {
            "available": True,
            "status": "MARKET_DATA_VERIFIED_COMPLETE",
            "session": "2026-11-02",
            "total_eligible_equities": 500,
            "qualified_eod_equities": 500,
            "missing_equities_count": 0,
        }

        receipt = execute_daily_settlement(
            as_of_session="2026-11-02",
            no_write=True,
            workspace_root=tmp_path,
            now=datetime(2026, 11, 2, 23, 30, tzinfo=KOLKATA_TZ),
        )
        assert receipt["status"] == "FORENSIC_INSPECTION_NO_WRITE"
        assert receipt["no_write"] is True
        assert receipt["settlement_performed"] is False
        # Receipt file must NOT be written when no_write=True
        receipt_file = tmp_path / "docs" / "ml" / "daily_settlement_receipt_2026-11-02.json"
        assert not receipt_file.exists()


def test_quarantined_live_settlement_reports_hold_not_success(tmp_path: Path) -> None:
    with (
        patch("scripts.daily_settlement_workflow.verify_authoritative_market_data") as market,
        patch("scripts.daily_settlement_workflow.check_disk_reserve") as disk,
        patch("scripts.daily_settlement_workflow.run_outcome_settlement") as settlement,
    ):
        disk.return_value = {"passed": True, "free_gib": 65.0}
        market.return_value = {
            "available": True,
            "status": "MARKET_DATA_VERIFIED_COMPLETE",
            "session": "2026-11-02",
        }
        settlement.return_value = {
            "total_matured_forecasts": 601,
            "quarantine_status": {
                "quarantine_active": True,
                "legacy_outcomes_quarantined": 601,
                "qualified_acceptance_outcomes": 0,
                "qualified_acceptance_decision_dates": 0,
            },
            "acceptance_status": {"status": "ACCEPTANCE_EVIDENCE_QUARANTINED"},
        }

        receipt = execute_daily_settlement(
            as_of_session="2026-11-02",
            workspace_root=tmp_path,
            min_free_gib=0.001,
            now=datetime(2026, 11, 2, 23, 30, tzinfo=KOLKATA_TZ),
        )
        assert receipt["status"] == "SETTLEMENT_HELD_QUARANTINED"
        assert receipt["settlement_performed"] is False
        assert receipt["acceptance_evaluation"]["accepted_models_count"] == 0
        assert receipt["acceptance_evaluation"]["qualified_outcomes_count"] == 0
        assert settlement.call_count == 1
        file = tmp_path / "docs" / "ml" / "daily_settlement_receipt_2026-11-02.json"
        written_receipt = json.loads(file.read_text(encoding="utf-8"))
        assert written_receipt["status"] == "SETTLEMENT_HELD_QUARANTINED"
