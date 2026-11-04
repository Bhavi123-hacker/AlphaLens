"""Do not confuse available session dates with a reconstructed research return."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from scripts.reconstruct_calendar_aligned_research_outcomes import reconstruct_research_ledger


def test_session_dates_alone_never_claim_valid_reconstructed_outcome(tmp_path: Path) -> None:
    original = tmp_path / "legacy.db"
    derived = tmp_path / "derived.db"
    report = tmp_path / "audit.json"
    with sqlite3.connect(original) as db:
        db.execute(
            "CREATE TABLE matured_forecasts ("
            "forecast_id TEXT, model_id TEXT, instrument_key TEXT, "
            "forecast_session TEXT, horizon_sessions INTEGER, "
            "entry_session TEXT, settlement_session TEXT, "
            "realized_return REAL, benchmark_return REAL, realized_excess_alpha REAL, "
            "directional_hit INTEGER, brier_score_component REAL, record_hash TEXT)"
        )
        db.execute(
            "INSERT INTO matured_forecasts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "forecast-1", "candidate", "NSE_EQ|INE002A01018",
                "2026-10-23", 5, "2026-10-28", "2026-11-03",
                0.04, 0.01, 0.03, 1, 0.12, "signed-immutable-record",
            ),
        )
    original_bytes = original.read_bytes()

    market_root = tmp_path / "market"
    market_root.mkdir()
    pointer = market_root / "market-view-latest.json"
    pointer.write_text(json.dumps({"path": "market.json"}), encoding="utf-8")
    sessions = [
        "2026-10-23", "2026-10-26", "2026-10-27",
        "2026-10-28", "2026-10-29", "2026-10-30",
    ]
    (market_root / "market.json").write_text(
        json.dumps(
            {
                "histories": {
                    "NSE_EQ|INE002A01018": [
                        {"session": day} for day in sessions
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    result = reconstruct_research_ledger(
        legacy_ledger_path=original,
        output_ledger_path=derived,
        market_view_path=pointer,
        report_path=report,
    )
    assert result["reconstruction_counts"]["RECONSTRUCTED_CALENDAR_ALIGNED_RESEARCH_OUTCOME"] == 0
    assert result["reconstruction_counts"]["RECONSTRUCTION_PENDING_FULL_RECOMPUTATION"] == 1
    assert result["independent_acceptance_contribution"]["qualified_observations_contributed"] == 0
    assert original.read_bytes() == original_bytes
    with sqlite3.connect(derived) as db:
        status = db.execute(
            "SELECT reconstruction_status FROM reconstructed_research_outcomes"
        ).fetchone()[0]
        assert status == "RECONSTRUCTION_PENDING_FULL_RECOMPUTATION"
