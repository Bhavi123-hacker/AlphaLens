"""Read-only release evidence reconciliation regression tests."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from scripts.reconcile_release_evidence import (
    inspect_ledger_readonly,
    inspect_market_view_readonly,
    reconcile_attestation,
)
from workers.nse_market.universe_coverage_tracker import compute_universe_coverage


def test_attestation_counts_match_exchange_totals() -> None:
    repo = Path(__file__).resolve().parents[2]
    result = reconcile_attestation(
        repo / "docs" / "release" / "ALPHALENS_PRIVATE_V1_RELEASE_ATTESTATION.json"
    )
    assert result["status"] == "RECONCILED_COMMITTED_SNAPSHOT"
    assert result["catalog_total"] == 8169
    assert result["nse_catalog"] == 3214
    assert result["bse_catalog"] == 4955
    assert result["verified_retained_candles_in_attestation"] == 451468
    assert result["latest_observed_session"] == "2026-11-02"
    assert result["latest_session_stocks"] == 498
    assert result["evidence_level"] == "COMMITTED_ATTESTATION_ONLY_NOT_LIVE_DISK_VERIFIED"


def test_missing_ledger_does_not_create_sqlite_file(tmp_path: Path) -> None:
    path = tmp_path / "missing" / "ledger.db"
    result = inspect_ledger_readonly(path)
    assert result["status"] == "LOCAL_LEDGER_NOT_AVAILABLE"
    assert not path.exists()
    assert not path.parent.exists()


def test_existing_ledger_inspected_without_mutations(tmp_path: Path) -> None:
    path = tmp_path / "matured.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE matured_forecasts ("
            "forecast_id TEXT PRIMARY KEY, model_id TEXT, instrument_key TEXT, "
            "forecast_session TEXT, benchmark_source TEXT, record_hash TEXT)"
        )
        conn.execute(
            "INSERT INTO matured_forecasts VALUES (?, ?, ?, ?, ?, ?)",
            ("f1", "modelA", "NSE_EQ|INE002A01018", "2026-10-16", "ZERO_BASELINE", "hash1"),
        )
        conn.execute(
            "INSERT INTO matured_forecasts VALUES (?, ?, ?, ?, ?, ?)",
            (
                "f2",
                "modelA",
                "NSE_EQ|INE002A01018",
                "2026-10-19",
                "BROAD_MARKET_EQUAL_WEIGHTED_UNIVERSE",
                "hash2",
            ),
        )
    before = path.read_bytes()
    result = inspect_ledger_readonly(path)
    after = path.read_bytes()
    assert result["status"] == "LOCAL_LEDGER_READ_ONLY_VERIFIED"
    assert result["total_matured"] == 2
    assert result["distinct_decision_dates"] == 2
    assert result["distinct_securities"] == 1
    assert result["unqualified_benchmark_rows"] == 1
    assert result["by_model"][0]["outcomes"] == 2
    assert before == after


def test_legacy_ledger_is_readable_without_migration(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE matured_forecasts (forecast_id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO matured_forecasts VALUES ('protected')")
    result = inspect_ledger_readonly(path)
    assert result["status"] == "LEGACY_LEDGER_SCHEMA_REQUIRES_REVIEW"
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT forecast_id FROM matured_forecasts").fetchone() == (
            "protected",
        )


def test_market_view_counts_are_explicitly_snapshot_scoped(tmp_path: Path) -> None:
    folder = tmp_path / "nse-market-expansion"
    folder.mkdir()
    pointer = folder / "market-view-latest.json"
    view = folder / "snapshot.json"
    pointer.write_text(json.dumps({"path": "snapshot.json"}), encoding="utf-8")
    view.write_text(
        json.dumps(
            {
                "histories": {
                    "NSE_EQ|INE002A01018": [
                        {"session": "2026-11-02", "open": 100.0, "close": 101.0}
                    ],
                    "BSE_EQ|INE002A01018": [
                        {"session": "2026-10-30", "open": 99.0, "close": 100.0}
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    result = inspect_market_view_readonly(pointer, "2026-11-02")
    assert result["status"] == "LOCAL_MARKET_VIEW_READ_ONLY_INSPECTED"
    assert result["snapshot_scope"] == "MARKET_VIEW_ONLY_NOT_COMPLETE_DURABLE_DATABASE"
    assert result["nse_in_view"] == 1
    assert result["bse_in_view"] == 1
    assert result["session_stocks_in_view"] == 1


def test_coverage_without_local_private_data_uses_attestation(tmp_path: Path) -> None:
    root = tmp_path / "project"
    dest = root / "docs" / "release"
    dest.mkdir(parents=True)
    repo = Path(__file__).resolve().parents[2]
    attestation = repo / "docs" / "release" / "ALPHALENS_PRIVATE_V1_RELEASE_ATTESTATION.json"
    (dest / attestation.name).write_bytes(attestation.read_bytes())
    report = compute_universe_coverage(root)
    assert report.searchable.total_listings == 8169
    assert report.searchable.nse_listings == 3214
    assert report.searchable.bse_listings == 4955
    assert report.daily_store.total_candles_retained == 451468
    assert report.daily_store.latest_observed_session == "2026-11-02"
    assert report.daily_store.active_session_received == 498
    assert report.daily_store.pending_vendor_publication == 2
    assert report.features.evaluated_stocks == 315
    assert report.features.excluded_stocks == 185
    assert report.forecast_ledger.session_forecasts == 315
    assert report.searchable.status == "COMMITTED_ATTESTATION_NOT_LIVE_CATALOG"
    assert report.daily_store.status == "COMMITTED_ATTESTATION_NOT_LIVE_DAILY_STORE"
    assert report.invariants_passed
