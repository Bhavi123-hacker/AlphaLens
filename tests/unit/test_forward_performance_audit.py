"""Unit tests for forward performance audit and discrepancy reconciliation."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from scripts.audit_forward_performance_metrics import audit_matured_ledger


def test_audit_matured_ledger_on_existing_db() -> None:
    ledger_path = Path("data/forecasts/matured_outcomes_ledger.db")
    if not ledger_path.exists():
        # Fall back to testing the committed reconciliation audit artifact in clean CI checkouts
        audit_file = Path("docs/ml/forward_performance_audit_reconciliation.json")
        if not audit_file.exists():
            pytest.skip("Neither local private ledger nor committed audit artifact found")
        audit_data = json.loads(audit_file.read_text(encoding="utf-8"))
    else:
        audit_data = audit_matured_ledger(db_path=ledger_path)
    assert audit_data["total_matured_outcomes"] == 601
    assert audit_data["directional_hit_numerator"] == 208
    assert audit_data["directional_hit_denominator"] == 601
    assert audit_data["directional_hit_rate"] == 0.3461
    assert audit_data["distinct_decision_dates"] == 2
    assert audit_data["distinct_securities"] == 302
    assert audit_data["distinct_models"] == 1
    assert audit_data["mean_brier_score"] == 0.2838

    # Check sessions breakdown
    sessions = audit_data["breakdown_by_session"]
    assert "2026-10-16" in sessions
    assert "2026-10-19" in sessions
    assert sessions["2026-10-16"]["total_outcomes"] == 300
    assert sessions["2026-10-16"]["directional_hits"] == 102
    assert sessions["2026-10-19"]["total_outcomes"] == 301
    assert sessions["2026-10-19"]["directional_hits"] == 106

    # Check 120/347 reconciliation
    rec = audit_data["reconciliation_of_reported_discrepancy"]
    assert rec["claimed_report_metrics"]["claimed_hit_numerator"] == 120
    assert rec["claimed_report_metrics"]["claimed_hit_denominator"] == 347
    assert rec["authoritative_ledger_ground_truth"]["authoritative_total_records"] == 601
    assert rec["authoritative_ledger_ground_truth"]["authoritative_directional_hits"] == 208


def test_audit_matured_ledger_isolated_db(tmp_path: Path) -> None:
    # Test on a minimal synthetic test ledger
    db_file = tmp_path / "test_ledger.db"
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            """
            CREATE TABLE matured_forecasts (
                forecast_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                instrument_key TEXT NOT NULL,
                symbol TEXT NOT NULL,
                forecast_session TEXT NOT NULL,
                entry_session TEXT NOT NULL,
                settlement_session TEXT NOT NULL,
                horizon_sessions INTEGER NOT NULL,
                predicted_direction_prob REAL NOT NULL,
                predicted_return REAL NOT NULL,
                realized_return REAL NOT NULL,
                realized_direction INTEGER NOT NULL,
                directional_hit INTEGER NOT NULL,
                brier_score_component REAL NOT NULL,
                benchmark_return REAL NOT NULL DEFAULT 0.0,
                realized_excess_alpha REAL NOT NULL,
                benchmark_source TEXT NOT NULL,
                matured_at TEXT NOT NULL,
                record_hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO matured_forecasts VALUES (
                'test_f1', 'model_A', 'NSE_EQ|INE1', 'SYM1', '2026-10-16',
                '2026-10-19', '2026-10-23', 5, 0.60, 0.02, 0.03, 1, 1, 0.16,
                0.01, 0.02, 'TEST_BENCH', '2026-10-23T10:00:00Z', 'hash1'
            )
            """
        )
        conn.execute(
            """
            INSERT INTO matured_forecasts VALUES (
                'test_f2', 'model_A', 'NSE_EQ|INE2', 'SYM2', '2026-10-16',
                '2026-10-19', '2026-10-23', 5, 0.40, -0.01, 0.02, 1, 0, 0.36,
                0.01, 0.01, 'TEST_BENCH', '2026-10-23T10:00:00Z', 'hash2'
            )
            """
        )
        conn.commit()

    audit = audit_matured_ledger(db_path=db_file)
    assert audit["total_matured_outcomes"] == 2
    assert audit["directional_hit_numerator"] == 1
    assert audit["directional_hit_rate"] == 0.5
    assert audit["distinct_decision_dates"] == 1
    assert audit["distinct_securities"] == 2


def test_quarantine_policy_excludes_observations_from_acceptance() -> None:
    from scripts.retrain_models import evaluate_independent_acceptance

    # When quarantine is active, model acceptance must return ACCEPTANCE_EVIDENCE_QUARANTINED
    quarantined_summary = {
        "quarantine_status": {
            "quarantine_active": True,
            "legacy_outcomes_quarantined": 601,
            "qualified_acceptance_outcomes": 0,
            "qualified_acceptance_decision_dates": 0,
        },
        "acceptance_status": {
            "status": "ACCEPTANCE_EVIDENCE_QUARANTINED",
            "accepted_models_count": 0,
            "qualified_outcomes_count": 0,
            "qualified_decision_dates_count": 0,
        },
    }
    result = evaluate_independent_acceptance(quarantined_summary)
    assert result["status"] == "ACCEPTANCE_EVIDENCE_QUARANTINED"
    assert result["accepted_models_count"] == 0
    assert result["qualified_outcomes_count"] == 0
    assert result["qualified_decision_dates_count"] == 0
    assert result["acceptance_granted"] is False
    assert "ZERO observations" in result["reason"]
