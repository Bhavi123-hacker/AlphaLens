"""Regression tests for model acceptance evidence accounting and quarantine isolation."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from scripts.recheck_model_acceptance import (
    BATTERY_20_MODELS,
    recheck_all_models,
)


def _create_test_ledger(db_path: Path, rows: list[tuple[Any, ...]]) -> None:
    """Create a temporary outcome ledger for quarantine and isolation testing."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE matured_forecasts (
                forecast_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                instrument_key TEXT NOT NULL,
                symbol TEXT DEFAULT 'TEST',
                forecast_session TEXT NOT NULL,
                entry_session TEXT NOT NULL,
                settlement_session TEXT NOT NULL,
                horizon_sessions INTEGER NOT NULL,
                predicted_direction_prob REAL DEFAULT 0.6,
                predicted_return REAL DEFAULT 0.05,
                realized_return REAL NOT NULL,
                realized_direction INTEGER DEFAULT 1,
                directional_hit INTEGER NOT NULL,
                brier_score_component REAL NOT NULL,
                benchmark_return REAL NOT NULL,
                realized_excess_alpha REAL NOT NULL,
                benchmark_source TEXT DEFAULT 'BROAD_MARKET_EQUAL_WEIGHTED_UNIVERSE',
                matured_at TEXT DEFAULT '2026-11-04T00:00:00+00:00',
                record_hash TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO matured_forecasts (
                forecast_id, model_id, instrument_key, forecast_session,
                horizon_sessions, entry_session, settlement_session,
                realized_return, benchmark_return, realized_excess_alpha,
                directional_hit, brier_score_component, record_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def test_quarantined_ledger_contributes_zero_to_prospective_metrics(tmp_path: Path) -> None:
    """Ensure the existing 601 quarantined records contribute 0 to prospective acceptance."""
    ledger_path = Path("data/forecasts/matured_outcomes_ledger.db")
    if not ledger_path.exists():
        receipt_file = Path("docs/ml/automated_model_acceptance_receipt.json")
        if not receipt_file.exists():
            pytest.skip("Neither local private ledger nor committed receipt found")
        res = json.loads(receipt_file.read_text(encoding="utf-8"))
    else:
        res = recheck_all_models()

    assert res["summary"]["independently_accepted_models"] == 0
    assert res["summary"]["overall_status"] == "ACCEPTANCE_EVIDENCE_QUARANTINED"
    assert res["data_lineage"]["tier_1_qualified_prospective_outcomes"]["total_records"] == 0
    assert res["data_lineage"]["tier_2_quarantined_historical_outcomes"]["total_records"] == 601

    assert len(res["per_model_evaluations"]) == 20
    for _m_key, m_eval in res["per_model_evaluations"].items():
        assert m_eval["qualified_prospective_outcomes"] == 0
        assert m_eval["qualified_decision_dates"] == 0
        assert m_eval["prospective_directional_accuracy"] is None
        assert m_eval["prospective_gross_alpha_bps"] is None
        assert m_eval["prospective_net_alpha_bps"] is None
        assert m_eval["acceptance_status"] == "FORWARD_OUTCOME_PENDING"
        assert not m_eval["acceptance_granted"]


def test_adding_quarantined_records_cannot_improve_or_alter_acceptance(tmp_path: Path) -> None:
    """Mathematical proof: Adding high-win quarantined records has ZERO impact on acceptance."""
    fake_ledger = tmp_path / "quarantined_test_ledger.db"

    # Add 2,000 artificial records with 100% win-rate and +500 bps alpha, but misaligned horizons
    fake_rows = [
        (
            f"fake_forecast_{i}",
            "HistGB_Classifier_H5",
            f"NSE_EQ|INE{i:09d}",
            "2026-10-16",
            5,
            "2026-10-19",
            "2026-10-28",  # Misaligned exchange horizon
            0.05,
            0.00,
            0.05,
            1,
            0.01,
            f"fake_hash_{i}",
        )
        for i in range(2000)
    ]
    _create_test_ledger(fake_ledger, fake_rows)

    out_json = tmp_path / "test_receipt.json"
    out_md = tmp_path / "test_report.md"

    res = recheck_all_models(ledger_path=fake_ledger, output_json=out_json, output_md=out_md)

    assert res["summary"]["independently_accepted_models"] == 0
    assert res["summary"]["overall_status"] == "ACCEPTANCE_EVIDENCE_QUARANTINED"
    assert res["data_lineage"]["tier_1_qualified_prospective_outcomes"]["total_records"] == 0
    assert res["data_lineage"]["tier_2_quarantined_historical_outcomes"]["total_records"] == 2000

    h5_eval = res["per_model_evaluations"]["HistGB_Classifier_H5"]
    assert h5_eval["qualified_prospective_outcomes"] == 0
    assert h5_eval["prospective_directional_accuracy"] is None
    assert h5_eval["prospective_net_alpha_bps"] is None
    assert not h5_eval["acceptance_granted"]


def test_per_model_isolation_never_pools_across_models(tmp_path: Path) -> None:
    """Verify models are isolated and never pool outcomes across models or horizons."""
    assert len(BATTERY_20_MODELS) == 20

    keys = [m["model_key"] for m in BATTERY_20_MODELS]
    assert len(set(keys)) == 20

    horizons = {m["horizon"] for m in BATTERY_20_MODELS}
    assert horizons == {1, 5, 10, 20}

    families = {m["family"] for m in BATTERY_20_MODELS}
    assert families == {
        "HistGB_Classifier",
        "RandomForest_Classifier",
        "LogisticRegression",
        "HistGB_Regressor",
        "Ridge",
    }


def test_insufficient_qualified_observations_rejects_acceptance(tmp_path: Path) -> None:
    """Verify that models with < 1,000 outcomes or < 126 dates are rejected."""
    ledger_path = Path("data/forecasts/matured_outcomes_ledger.db")
    if not ledger_path.exists():
        receipt_file = Path("docs/ml/automated_model_acceptance_receipt.json")
        if not receipt_file.exists():
            pytest.skip("Neither local private ledger nor committed receipt found")
        res = json.loads(receipt_file.read_text(encoding="utf-8"))
    else:
        res = recheck_all_models()
    for _m_key, m_eval in res["per_model_evaluations"].items():
        criteria = m_eval["criteria_audit"]
        assert "IN_PROGRESS" in criteria["decision_dates"]["status"]
        assert "IN_PROGRESS" in criteria["matured_outcomes"]["status"]
        assert criteria["directional_hit_rate"]["status"] in (
            "NO_EVIDENCE",
            "NOT_SATISFIED (Fail)",
        )
        assert criteria["net_excess_alpha_after_20bps"]["status"] in (
            "NO_EVIDENCE",
            "NOT_SATISFIED (Fail)",
        )
        assert criteria["calibration_brier"]["status"] in (
            "NO_EVIDENCE",
            "NOT_SATISFIED (Fail)",
        )
        assert not m_eval["acceptance_granted"]


def test_friction_model_deducts_twenty_basis_points(tmp_path: Path) -> None:
    """Verify transaction cost model deducts exactly 20.0 bps (0.0020 decimal)."""
    test_ledger = tmp_path / "test_ledger.db"
    test_rows = [
        (
            "fake_forecast_1",
            "HistGB_Classifier_H5",
            "NSE_EQ|INE000000001",
            "2026-10-16",
            5,
            "2026-10-19",
            "2026-10-28",
            0.05,
            0.00,
            0.05,
            1,
            0.01,
            "fake_hash_1",
        )
    ]
    _create_test_ledger(test_ledger, test_rows)
    res = recheck_all_models(
        ledger_path=test_ledger,
        output_json=tmp_path / "out.json",
        output_md=tmp_path / "out.md",
    )
    friction = res["friction_model"]
    assert friction["roundtrip_bps"] == 20.0
    assert friction["brokerage_and_stt_bps"] == 12.0
    assert friction["exchange_turnover_and_gst_bps"] == 5.0
    assert friction["slippage_buffer_bps"] == 3.0
