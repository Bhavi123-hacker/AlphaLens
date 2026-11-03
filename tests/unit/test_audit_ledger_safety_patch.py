"""Regression tests for immutable ledger upgrades and authenticated benchmark windows."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from workers.nse_market.forward_maturation_engine import ForwardMaturationEngine

SESSIONS = [
    "2026-10-01",
    "2026-10-02",
    "2026-10-05",
    "2026-10-06",
    "2026-10-07",
    "2026-10-08",
]


def _forecast(key: str, horizon: int = 5) -> dict[str, object]:
    return {
        "instrument_key": key,
        "model_id": "model-v1",
        "session": SESSIONS[0],
        "horizon_sessions": horizon,
        "direction_probability": 0.6,
        "expected_return": 0.02,
        "recorded_at": "2026-10-01T16:00:00+00:00",
        "next_session_timing": {"open_at": "2026-10-02T03:45:00+00:00"},
        "prospective_eligible": True,
    }


def _history(
    key: str, entry_open: float = 100.0, exit_close: float = 105.0
) -> list[dict[str, object]]:
    candles: list[dict[str, object]] = []
    for i, session in enumerate(SESSIONS):
        candles.append({
            "session": session,
            "open": entry_open if i == 1 else 100.0,
            "close": exit_close if i == 5 else 100.0,
            "key": key,
        })
    return candles


def test_legacy_schema_is_not_dropped_or_rewritten(tmp_path: Path) -> None:
    """An incompatible ledger must fail closed without erasing original outcomes."""
    path = tmp_path / "legacy_matured.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE matured_forecasts "
            "(forecast_id TEXT PRIMARY KEY, realized_return REAL NOT NULL)"
        )
        conn.execute(
            "INSERT INTO matured_forecasts VALUES (?, ?)",
            ("protected_forecast", 0.123),
        )

    with pytest.raises(RuntimeError, match="LEGACY_MATURED_LEDGER_SCHEMA_MIGRATION_REQUIRED"):
        ForwardMaturationEngine(path)

    with sqlite3.connect(path) as conn:
        assert conn.execute(
            "SELECT forecast_id, realized_return FROM matured_forecasts"
        ).fetchall() == [("protected_forecast", 0.123)]


def test_strict_settlement_excludes_missing_benchmark(tmp_path: Path) -> None:
    """A single-stock history is not an adequate market-wide benchmark."""
    key = "NSE_EQ|INE002A01018"
    engine = ForwardMaturationEngine(tmp_path / "strict.sqlite3")
    settled = engine.settle_forecasts(
        [_forecast(key)],
        {key: _history(key)},
        require_entry_timing=True,
        require_qualified_benchmark=True,
    )
    assert settled == []
    assert engine.generate_audit_summary()["total_matured_forecasts"] == 0


def test_explicit_index_benchmark_matches_next_open_to_exit_close(tmp_path: Path) -> None:
    """Use the benchmark's entry OPEN, not entry CLOSE, for H5 returns."""
    key = "NSE_EQ|INE002A01018"
    engine = ForwardMaturationEngine(tmp_path / "index.sqlite3")
    benchmark = _history("NSE_INDEX|Nifty 50", entry_open=200.0, exit_close=210.0)
    settled = engine.settle_forecasts(
        [_forecast(key)],
        {key: _history(key, entry_open=100.0, exit_close=105.0)},
        benchmark_history=benchmark,
        require_entry_timing=True,
        require_qualified_benchmark=True,
    )
    assert len(settled) == 1
    assert settled[0].realized_return == pytest.approx(0.05)
    assert settled[0].benchmark_return == pytest.approx(0.05)
    assert settled[0].realized_excess_alpha == pytest.approx(0.0, abs=1e-9)
    assert settled[0].benchmark_source == "EXPLICIT_BENCHMARK_INDEX"


def test_h1_qualified_universe_benchmark_uses_same_day_open_close(tmp_path: Path) -> None:
    """An H1 window enters and exits on T+1, not T+2."""
    histories: dict[str, list[dict[str, object]]] = {}
    for i in range(35):
        key = f"NSE_EQ|INE{i:07d}01"
        candles = _history(key)
        candles[1]["open"] = 100.0
        candles[1]["close"] = 110.0
        histories[key] = candles

    first_key = next(iter(histories))
    engine = ForwardMaturationEngine(tmp_path / "h1.sqlite3")
    settled = engine.settle_forecasts(
        [_forecast(first_key, horizon=1)],
        histories,
        require_entry_timing=True,
        require_qualified_benchmark=True,
    )
    assert len(settled) == 1
    assert settled[0].realized_return == pytest.approx(0.10)
    assert settled[0].benchmark_return == pytest.approx(0.10)
    assert settled[0].benchmark_source == "BROAD_MARKET_EQUAL_WEIGHTED_UNIVERSE"
