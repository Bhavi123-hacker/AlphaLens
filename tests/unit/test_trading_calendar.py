"""Unit tests for authentic NSE trading calendar validation."""

from __future__ import annotations

import json
from pathlib import Path

from workers.nse_market.trading_calendar import (
    CalendarSessionStatus,
    load_reference_calendar,
    validate_nse_trading_session,
)


def test_load_reference_calendar(tmp_path: Path) -> None:
    # Test valid calendar loading in an isolated temp path
    sample_cal = {
        "schema": "alphalens.nse_calendar.v1",
        "year": 2026,
        "exchange": "NSE",
        "timezone": "Asia/Kolkata",
        "sessions": [
            {"session": "2026-10-20", "status": "NON_TRADING"},
            {"session": "2026-11-08", "status": "TRADING"},
        ],
    }
    cal_file = tmp_path / "data" / "reference" / "nse_calendar_2026.json"
    cal_file.parent.mkdir(parents=True)
    cal_file.write_text(json.dumps(sample_cal), encoding="utf-8")

    loaded = load_reference_calendar(calendar_path=cal_file, repo_root=tmp_path)
    assert loaded is not None
    assert loaded["year"] == 2026
    assert len(loaded["sessions"]) == 2


def test_validate_regular_weekday() -> None:
    # 2026-11-02 is Monday
    result = validate_nse_trading_session("2026-11-02")
    assert result["is_trading_day"] is True
    assert result["status"] == CalendarSessionStatus.VERIFIED_TRADING_SESSION
    assert result["weekday"] == "Monday"


def test_validate_standard_weekend() -> None:
    # 2026-11-01 is Sunday
    result = validate_nse_trading_session("2026-11-01")
    assert result["is_trading_day"] is False
    assert result["status"] == CalendarSessionStatus.MARKET_SESSION_WEEKEND_NON_TRADING
    assert result["weekday"] == "Sunday"


def test_validate_market_holiday() -> None:
    # 2026-10-20 is Dussehra (Tuesday holiday)
    result = validate_nse_trading_session("2026-10-20")
    assert result["is_trading_day"] is False
    assert result["status"] == CalendarSessionStatus.VERIFIED_MARKET_HOLIDAY
    assert result["weekday"] == "Tuesday"


def test_validate_exceptional_weekend_session() -> None:
    # 2026-11-08 is Diwali Muhurat trading (Sunday special session)
    result = validate_nse_trading_session("2026-11-08")
    assert result["is_trading_day"] is True
    assert result["status"] == CalendarSessionStatus.EXCEPTIONAL_TRADING_SESSION
    assert result["weekday"] == "Sunday"


def test_validate_uncovered_future_year() -> None:
    # Date outside covered calendar range fails closed
    result = validate_nse_trading_session("2035-06-15")
    assert result["is_trading_day"] is False
    assert result["status"] == CalendarSessionStatus.CALENDAR_EVIDENCE_UNAVAILABLE


def test_validate_calendar_missing_fails_closed(tmp_path: Path) -> None:
    # Empty workspace root has no calendar file; must fail closed
    result = validate_nse_trading_session("2026-11-02", repo_root=tmp_path, fallback_to_repo=False)
    assert result["is_trading_day"] is False
    assert result["status"] == CalendarSessionStatus.CALENDAR_EVIDENCE_UNAVAILABLE


def test_validate_invalid_date_format() -> None:
    result = validate_nse_trading_session("invalid-date-string")
    assert result["is_trading_day"] is False
    assert result["status"] == CalendarSessionStatus.REJECTED_INVALID_DATE
