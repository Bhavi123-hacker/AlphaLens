"""Portable fixtures for local read-only AlphaLens release inspection."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from scripts.check_local_release import (
    daily_receipt_status,
    inspect,
    ledger_status,
    market_view_status,
)


def test_market_view_reads_all_equity_histories_without_editing(tmp_path: Path) -> None:
    pointer = tmp_path / "market-view-latest.json"
    view = tmp_path / "market-views" / "snapshot.json"
    view.parent.mkdir()
    data = {
        "histories": {
            "NSE_EQ|AAA": [
                {"session": "2026-11-02"},
                {"session": "2026-11-03"},
            ],
            "NSE_EQ|BBB": [{"date": "2026-11-02"}],
            "NSE_EQ|CCC": [{"timestamp": "2026-11-03T15:30:00+05:30"}],
            "NSE_INDEX|Nifty 50": [{"session": "2026-11-03"}],
        }
    }
    pointer.write_text(json.dumps({"path": "market-views/snapshot.json"}), encoding="utf-8")
    view.write_text(json.dumps(data), encoding="utf-8")
    before = (pointer.read_bytes(), view.read_bytes())

    result = market_view_status(pointer)
    assert result["status"] == "SAVED_MARKET_VIEW_INSPECTED"
    assert result["latest_observation_session"] == "2026-11-03"
    assert result["equities_with_latest_session"] == 2
    assert result["equities_with_any_history"] == 3
    assert result["data_verified_as_authorized"] is False
    assert (pointer.read_bytes(), view.read_bytes()) == before


def test_pointer_cannot_escape_market_view_directory(tmp_path: Path) -> None:
    pointer = tmp_path / "market-view-latest.json"
    pointer.write_text(json.dumps({"path": "../secrets.json"}), encoding="utf-8")
    assert market_view_status(pointer)["status"] == "POINTER_OUTSIDE_APPROVED_DIRECTORY"


def test_quarantined_sqlite_ledger_is_byte_identical(tmp_path: Path) -> None:
    path = tmp_path / "matured_outcomes_ledger.db"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE matured_forecasts (forecast_id TEXT, "
            "forecast_session TEXT, horizon_sessions INTEGER, "
            "entry_session TEXT, settlement_session TEXT)"
        )
        db.execute(
            "INSERT INTO matured_forecasts VALUES (?, ?, ?, ?, ?)",
            ("legacy", "2026-10-23", 5, "2026-10-28", "2026-11-03"),
        )
    before = path.read_bytes()
    result = ledger_status(path)
    assert result["status"] == "QUARANTINE_REVIEW_REQUIRED"
    assert result["misaligned"] == 1
    assert result["independent_acceptance_unlocked"] is False
    assert path.read_bytes() == before


def test_full_inspection_avoids_remote_and_windows_actions(tmp_path: Path) -> None:
    # No paid-provider transport is ever imported or used.
    result = inspect(tmp_path, check_tasks=False)
    assert result["provider_requests_made"] == 0
    assert result["file_writes_performed"] == 0
    assert "tasks" not in result
    assert result["full_universe"] == "FULL_UNIVERSE_V2_GATED"


def test_daily_pointer_uses_checked_receipt_not_pointer_fields(tmp_path: Path) -> None:
    pointer = tmp_path / "daily-latest.json"
    receipt = tmp_path / "daily" / "receipt.json"
    receipt.parent.mkdir()
    body = json.dumps(
        {
            "session": "2026-11-03",
            "state": "COMPLETE",
            "completed_at": "2026-11-04T08:16:59Z",
        }
    ).encode()
    receipt.write_bytes(body)
    receipt.with_suffix(".json.sha256").write_text(hashlib.sha256(body).hexdigest())
    pointer.write_text(json.dumps({"path": "daily/receipt.json"}))

    result = daily_receipt_status(pointer)
    assert result["state"] == "COMPLETE"
    assert result["session"] == "2026-11-03"
    assert result["checksum_verified"] is True

    receipt.write_bytes(b'{"state":"TAMPERED"}')
    assert daily_receipt_status(pointer)["status"] == "RECEIPT_SHA256_MISMATCH"
