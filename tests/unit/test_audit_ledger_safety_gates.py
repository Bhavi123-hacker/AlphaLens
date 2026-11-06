"""Regression tests for non-destructive outcome-ledger and benchmark safety."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from workers.nse_market.forward_maturation_engine import ForwardMaturationEngine


def _forecast(key: str, *, horizon: int = 1) -> dict[str, object]:
    return {
        "instrument_key": key,
        "model_id": "test_model",
        "session": "2026-10-01",
        "horizon_sessions": horizon,
        "direction_probability": 0.60,
        "expected_return": 0.03,
        "recorded_at": "2026-10-01T16:00:00+00:00",
        "next_session_timing": {"open_at": "2026-10-02T03:45:00+00:00"},
        "prospective_eligible": True,
    }


def test_legacy_schema_migration_never_drops_original_rows(tmp_path: Path) -> None:
    db = tmp_path / "legacy.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE matured_forecasts (forecast_id TEXT PRIMARY KEY, realized_return REAL)"
        )
        conn.execute("INSERT INTO matured_forecasts VALUES (?, ?)", ("original", 0.03))
        conn.commit()

    with pytest.raises(RuntimeError, match="LEGACY_MATURED_LEDGER_SCHEMA_MIGRATION_REQUIRED"):
        ForwardMaturationEngine(db)

    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT forecast_id, realized_return FROM matured_forecasts").fetchone()
        assert row == ("original", 0.03)


def test_live_settlement_rejects_missing_qualified_benchmark(tmp_path: Path) -> None:
    key = "NSE_EQ|INE002A01018"
    histories = {
        key: [
            {"session": "2026-10-01", "open": 100.0, "close": 101.0},
            {"session": "2026-10-02", "open": 100.0, "close": 105.0},
        ]
    }
    engine = ForwardMaturationEngine(tmp_path / "missing_benchmark.db")
    matured = engine.settle_forecasts(
        [_forecast(key)],
        histories,
        require_entry_timing=True,
        require_qualified_benchmark=True,
    )
    assert matured == []
    assert engine.generate_audit_summary()["total_matured_forecasts"] == 0


def test_one_session_broad_market_uses_entry_open_to_same_day_close(
    tmp_path: Path,
) -> None:
    histories: dict[str, list[dict[str, object]]] = {}
    for i in range(35):
        key = f"NSE_EQ|INE{i:09d}"
        histories[key] = [
            {"session": "2026-10-01", "open": 100.0, "close": 101.0},
            {"session": "2026-10-02", "open": 100.0, "close": 105.0},
        ]

    key = "NSE_EQ|INE000000000"
    engine = ForwardMaturationEngine(tmp_path / "market_benchmark.db")
    matured = engine.settle_forecasts([_forecast(key)], histories, require_qualified_benchmark=True)
    assert len(matured) == 1
    assert matured[0].benchmark_source == "BROAD_MARKET_EQUAL_WEIGHTED_UNIVERSE"
    assert matured[0].realized_return == pytest.approx(0.05)
    assert matured[0].benchmark_return == pytest.approx(0.05)
    assert matured[0].realized_excess_alpha == pytest.approx(0.0)


def test_explicit_index_benchmark_uses_entry_open_not_entry_close(
    tmp_path: Path,
) -> None:
    key = "NSE_EQ|INE002A01018"
    histories = {
        key: [
            {"session": "2026-10-01", "open": 100.0, "close": 101.0},
            {"session": "2026-10-02", "open": 100.0, "close": 105.0},
        ]
    }
    benchmark = [
        {"session": "2026-10-01", "open": 100.0, "close": 100.0},
        {"session": "2026-10-02", "open": 90.0, "close": 99.0},
    ]
    engine = ForwardMaturationEngine(tmp_path / "index_benchmark.db")
    matured = engine.settle_forecasts(
        [_forecast(key)],
        histories,
        benchmark_history=benchmark,
        require_qualified_benchmark=True,
    )
    assert len(matured) == 1
    assert matured[0].benchmark_source == "EXPLICIT_BENCHMARK_INDEX"
    assert matured[0].benchmark_return == pytest.approx(0.10)
    assert matured[0].realized_excess_alpha == pytest.approx(-0.05)
