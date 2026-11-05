"""Automated tests for AlphaLens historical market data integrity."""

import json
from pathlib import Path
import pytest


def test_data_integrity_audit_file_exists():
    path = Path("release/alphalens_stock_coverage_audit.json")
    assert path.exists(), "Stock coverage audit JSON must exist"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_securities"] == 500
    assert data["total_candles"] == 60000
    assert data["unique_sessions_count"] == 120
    assert data["session_min"] == "2026-05-12"
    assert data["session_max"] == "2026-11-04"
    assert data["ohlc_violations_count"] == 0
    assert data["negative_prices_count"] == 0
    assert data["invalid_volumes_count"] == 0
    assert data["duplicate_candles_count"] == 0


def test_special_isin_ine029l01018_handling():
    path = Path("release/alphalens_stock_coverage_audit.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    kicl = [s for s in data["securities"] if s["isin"] == "INE029L01018"]
    assert len(kicl) == 1
    record = kicl[0]
    assert record["symbol"] == "KICL"
    assert record["total_candles"] == 120
    assert record["valid_candles"] == 115
    assert record["null_candles"] == 5
    assert record["ohlc_violations"] == 0
    assert record["duplicate_count"] == 0


def test_ohlc_geometric_rules():
    """Verify standard candlestick geometry rules."""
    def validate_bar(o, h, l, c):
        return h >= o and h >= c and l <= o and l <= c and h >= l and o > 0 and l > 0

    assert validate_bar(100.0, 105.0, 95.0, 102.0)
    assert not validate_bar(100.0, 90.0, 85.0, 95.0)  # High < Open
    assert not validate_bar(100.0, 105.0, 110.0, 102.0) # Low > Open
    assert not validate_bar(-10.0, 10.0, -15.0, 5.0)   # Negative price
