"""Live settlement must never omit legacy quarantine checks."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from scripts import retrain_models
from workers.nse_market import forward_maturation_engine


def test_live_settlement_rejects_misaligned_ledger_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "misaligned.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE matured_forecasts (forecast_id TEXT PRIMARY KEY, "
            "forecast_session TEXT NOT NULL, horizon_sessions INTEGER NOT NULL, "
            "entry_session TEXT NOT NULL, settlement_session TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO matured_forecasts VALUES (?, ?, ?, ?, ?)",
            ("legacy1", "2026-10-23", 5, "2026-10-28", "2026-11-03"),
        )
    before = path.read_bytes()
    # Isolate tests from any genuine Windows D: ledger in the developer worktree.
    monkeypatch.setattr(retrain_models, "repo", tmp_path)

    class EngineStub:
        db_path = path

        def generate_audit_summary(self) -> dict[str, Any]:
            return {
                "total_matured_forecasts": 1,
                "distinct_decision_dates": 1,
                "summary_by_model": {
                    "model_legacy": {
                        "settled_count": 1001,
                        "distinct_decision_dates": 127,
                        "distinct_securities": 100,
                        "date_span_days": 200,
                        "directional_hit_rate": 0.75,
                        "mean_brier_score": 0.1,
                        "mean_excess_alpha": 0.1,
                        "net_excess_alpha": 0.09,
                    }
                },
            }

        def settle_forecasts(self, *_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("Quarantined ledger must not be written")

    engine = EngineStub()
    monkeypatch.setattr(
        forward_maturation_engine,
        "ForwardMaturationEngine",
        lambda: engine,
    )

    summary = retrain_models.run_outcome_settlement(forecasts=[], histories={})
    verdict = retrain_models.evaluate_independent_acceptance(summary)

    assert summary["quarantine_status"]["quarantine_active"] is True
    assert summary["quarantine_status"]["legacy_outcomes_quarantined"] == 1
    assert summary["quarantine_status"]["qualified_acceptance_outcomes"] == 0
    assert verdict["status"] == "ACCEPTANCE_EVIDENCE_QUARANTINED"
    assert verdict["qualified_outcomes_count"] == 0
    assert verdict["accepted_models_count"] == 0
    assert path.read_bytes() == before


def test_missing_audit_schema_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "unknown-schema.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE unrecognized (payload TEXT)")
    before = path.read_bytes()
    # Isolate tests from any genuine Windows D: ledger in the developer worktree.
    monkeypatch.setattr(retrain_models, "repo", tmp_path)

    class EngineStub:
        db_path = path

        def generate_audit_summary(self) -> dict[str, Any]:
            return {"total_matured_forecasts": 42, "distinct_decision_dates": 4}

    engine = EngineStub()
    monkeypatch.setattr(
        forward_maturation_engine,
        "ForwardMaturationEngine",
        lambda: engine,
    )

    summary = retrain_models.run_outcome_settlement(forecasts=[], histories={})
    assert summary["quarantine_status"]["quarantine_active"] is True
    assert summary["quarantine_status"]["audit_status"] == "READ_ONLY_AUDIT_FAILED"
    assert summary["quarantine_status"]["qualified_acceptance_outcomes"] == 0
    assert path.read_bytes() == before


def test_legacy_quarantine_prevents_constructor_index_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protected = tmp_path / "data" / "forecasts" / "matured_outcomes_ledger.db"
    protected.parent.mkdir(parents=True)
    with sqlite3.connect(protected) as db:
        db.execute(
            "CREATE TABLE matured_forecasts (forecast_id TEXT PRIMARY KEY, "
            "forecast_session TEXT, horizon_sessions INTEGER, "
            "entry_session TEXT, settlement_session TEXT)"
        )
        db.execute(
            "INSERT INTO matured_forecasts VALUES (?, ?, ?, ?, ?)",
            ("legacy", "2026-10-23", 5, "2026-10-28", "2026-11-03"),
        )
    baseline = protected.read_bytes()
    monkeypatch.setattr(retrain_models, "repo", tmp_path)

    def forbidden_engine_construction() -> None:
        raise AssertionError("A quarantined SQLite DB must not be initialized/migrated")

    monkeypatch.setattr(
        forward_maturation_engine, "ForwardMaturationEngine", forbidden_engine_construction
    )
    summary = retrain_models.run_outcome_settlement(forecasts=[], histories={})
    verdict = retrain_models.evaluate_independent_acceptance(summary)

    assert summary["quarantine_status"]["quarantine_active"] is True
    assert summary["quarantine_status"]["legacy_outcomes_quarantined"] == 1
    assert verdict["accepted_models_count"] == 0
    assert protected.read_bytes() == baseline
