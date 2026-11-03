"""Regression tests: exchange sessions, not vendor candle positions, define H5."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from scripts.audit_existing_exchange_horizons import audit_existing_horizons
from workers.nse_market.forward_maturation_engine import (
    ForwardMaturationEngine,
    registered_exchange_horizon_dates,
)

KEY = "NSE_EQ|INE002A01018"


def _history(sessions: list[str]) -> list[dict[str, object]]:
    return [
        {
            "session": session,
            "open": 100.0,
            "close": 105.0,
        }
        for session in sessions
    ]


def _forecast(open_at: str = "2026-10-26T03:45:00+00:00") -> dict[str, object]:
    return {
        "instrument_key": KEY,
        "model_id": "horizon-integrity",
        "session": "2026-10-23",
        "horizon_sessions": 5,
        "direction_probability": 0.62,
        "expected_return": 0.02,
        "recorded_at": "2026-10-23T16:00:00+00:00",
        "next_session_timing": {"open_at": open_at},
        "prospective_eligible": True,
    }


def test_exchange_registered_h5_windows_ignore_missing_vendor_sessions() -> None:
    assert registered_exchange_horizon_dates("2026-10-16", 5) == (
        "2026-10-19",
        "2026-10-21",
        "2026-10-22",
        "2026-10-23",
        "2026-10-26",
    )
    assert registered_exchange_horizon_dates("2026-10-19", 5) == (
        "2026-10-21",
        "2026-10-22",
        "2026-10-23",
        "2026-10-26",
        "2026-10-27",
    )
    assert registered_exchange_horizon_dates("2026-10-23", 5) == (
        "2026-10-26",
        "2026-10-27",
        "2026-10-28",
        "2026-10-29",
        "2026-10-30",
    )
    assert registered_exchange_horizon_dates("2026-10-30", 5) == (
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
        "2026-11-05",
        "2026-11-06",
    )


def test_muhurat_session_must_be_explicitly_considered_for_horizon() -> None:
    # Official NSE reference includes exceptional Sunday Muhurat session.
    assert registered_exchange_horizon_dates("2026-11-02", 5) == (
        "2026-11-03",
        "2026-11-04",
        "2026-11-05",
        "2026-11-06",
        "2026-11-08",
    )


def test_missing_26_27_october_candles_do_not_shift_registered_h5(
    tmp_path: Path,
) -> None:
    # Old vendor-indexed implementation would enter on October 28 and
    # exit on November 3, despite both Oct 26 and Oct 27 being open.
    observed = [
        "2026-10-23",
        "2026-10-28",
        "2026-10-29",
        "2026-10-30",
        "2026-11-02",
        "2026-11-03",
    ]
    engine = ForwardMaturationEngine(tmp_path / "no_shift.db")
    matured = engine.settle_forecasts(
        [_forecast()],
        {KEY: _history(observed)},
        require_entry_timing=True,
        require_calendar_aligned_horizon=True,
    )
    assert matured == []
    assert engine.generate_audit_summary()["total_matured_forecasts"] == 0


def test_correct_exchange_h5_settles_october_30_close(tmp_path: Path) -> None:
    observed = [
        "2026-10-23",
        "2026-10-26",
        "2026-10-27",
        "2026-10-28",
        "2026-10-29",
        "2026-10-30",
    ]
    engine = ForwardMaturationEngine(tmp_path / "correct_h5.db")
    matured = engine.settle_forecasts(
        [_forecast()],
        {KEY: _history(observed)},
        require_entry_timing=True,
        require_calendar_aligned_horizon=True,
    )
    assert len(matured) == 1
    assert matured[0].entry_session == "2026-10-26"
    assert matured[0].settlement_session == "2026-10-30"


def test_forecast_with_later_registered_entry_is_rejected(tmp_path: Path) -> None:
    observed = [
        "2026-10-23",
        "2026-10-26",
        "2026-10-27",
        "2026-10-28",
        "2026-10-29",
        "2026-10-30",
    ]
    engine = ForwardMaturationEngine(tmp_path / "wrong_entry.db")
    matured = engine.settle_forecasts(
        [_forecast("2026-10-28T03:45:00+00:00")],
        {KEY: _history(observed)},
        require_entry_timing=True,
        require_calendar_aligned_horizon=True,
    )
    assert matured == []


def test_readonly_audit_quarantines_shifted_legacy_windows(tmp_path: Path) -> None:
    path = tmp_path / "ledger.db"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE matured_forecasts (forecast_id TEXT PRIMARY KEY, "
            "forecast_session TEXT, horizon_sessions INTEGER, "
            "entry_session TEXT, settlement_session TEXT)"
        )
        db.execute(
            "INSERT INTO matured_forecasts VALUES (?, ?, ?, ?, ?)",
            ("correct", "2026-10-23", 5, "2026-10-26", "2026-10-30"),
        )
        db.execute(
            "INSERT INTO matured_forecasts VALUES (?, ?, ?, ?, ?)",
            ("shifted", "2026-10-23", 5, "2026-10-28", "2026-11-03"),
        )
    before = path.read_bytes()
    result = audit_existing_horizons(path)
    after = path.read_bytes()
    assert result["status"] == "QUARANTINE_REVIEW_REQUIRED"
    assert result["total"] == 2
    assert result["aligned"] == 1
    assert result["misaligned"] == 1
    assert result["mismatch_sample"][0]["expected_exit"] == "2026-10-30"
    assert before == after
