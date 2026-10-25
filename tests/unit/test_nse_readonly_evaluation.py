"""TEST_ONLY chronology and zero-write prospective display, no real predictions."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from test_experimental_nse_v2_forward import SESSIONS, mature, record, timing
from workers.nse_market import engine, outcomes

from alphalens_api import nse_evaluation


def context(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nse_evaluation, "_calendar", lambda root, day, at: timing(day))
    # Explicit TEST_ONLY adapter for this reader's independent calendar fixture;
    # raw-calendar/closure verification is exercised by the outcome-job tests.
    facts = {day: timing(day) for day in SESSIONS}
    for previous, following in zip(SESSIONS[:-1], SESSIONS[1:], strict=True):
        facts[previous] = {**facts[previous], "next_verified_session": following}
    monkeypatch.setattr(outcomes, "_timings", lambda root, cutoff: facts)
    folder = root / "session-links"
    folder.mkdir(parents=True)
    for previous, following in zip(SESSIONS[:-1], SESSIONS[1:], strict=True):
        engine._checked(
            folder / (previous + ".json"),
            {"next_session_timing": {**timing(following), "previous_session": previous}},
        )


def test_no_outcomes_have_null_accuracy_and_reader_never_initializes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, v2 = tmp_path / "TEST_ONLY_market", tmp_path / "TEST_ONLY_v2"
    before = set(tmp_path.rglob("*"))
    empty = nse_evaluation.read(root, v2, at=datetime(2025, 1, 2, 12, tzinfo=UTC))
    assert empty["raw_forecast_records"] == 0
    assert empty["metrics"]["score"]["accuracy"] is None
    assert set(tmp_path.rglob("*")) == before
    record(v2 / "price-only", monkeypatch)
    result = nse_evaluation.read(root, v2, at=datetime(2025, 1, 2, 13, tzinfo=UTC))
    assert result["raw_forecast_records"] == 1
    assert result["status_counts"] == {"FUTURE_ENTRY_NOT_STARTED": 1}
    assert result["matured_outcomes"] == 0


def test_metrics_require_actual_five_session_evidence_and_later_retrieval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, v2 = tmp_path / "TEST_ONLY_market", tmp_path / "TEST_ONLY_v2"
    record(v2 / "price-only", monkeypatch)
    mature(v2 / "price-only", monkeypatch)
    at = datetime(2025, 1, 11, tzinfo=UTC)
    # Ledger presence without independently inspectable session-chain evidence is insufficient.
    assert nse_evaluation.read(root, v2, at=at)["matured_outcomes"] == 0
    context(root, monkeypatch)
    before = (v2 / "price-only/experimental-v2-prospective.sqlite3").read_bytes()
    result = nse_evaluation.read(root, v2, at=at)
    assert result["matured_outcomes"] == 1
    assert result["metrics"]["score"]["accuracy"] == 1
    assert result["metrics"]["score"]["balanced_accuracy"] is None  # One class is insufficient.
    assert result["independent_acceptance"] is False
    assert before == (v2 / "price-only/experimental-v2-prospective.sqlite3").read_bytes()
    earlier = nse_evaluation.read(root, v2, at=datetime(2025, 1, 9, 12, tzinfo=UTC))
    assert earlier["matured_outcomes"] == 0
    assert earlier["metrics"]["score"]["accuracy"] is None


def test_original_and_expanded_overlap_is_not_double_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, v2 = tmp_path / "TEST_ONLY_market", tmp_path / "TEST_ONLY_v2"
    record(v2 / "price-only", monkeypatch)
    record(root / "expanded-forecasts/aa", monkeypatch)
    result = nse_evaluation.read(root, v2, at=datetime(2025, 1, 3, 12, tzinfo=UTC))
    assert result["raw_forecast_records"] == 2
    assert result["unique_decisions"] == 1
    assert result["overlapping_records"] == 1


def test_future_cutoff_and_corrupted_forecast_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ValueError):
        nse_evaluation.read(tmp_path, tmp_path, at=datetime(2100, 1, 1, tzinfo=UTC))
    v2 = tmp_path / "TEST_ONLY_v2"
    record(v2 / "price-only", monkeypatch)
    # Isolated fixture table without immutability triggers models corrupted storage.
    path = v2 / "price-only/experimental-v2-prospective.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TRIGGER experimental_forecasts_no_update")
        body: dict[str, Any] = json.loads(
            conn.execute("SELECT body FROM experimental_forecasts").fetchone()[0]
        )
        body["score"] = 0.99
        conn.execute("UPDATE experimental_forecasts SET body=?", (json.dumps(body),))
    with pytest.raises(ValueError, match="CHECKSUM"):
        nse_evaluation.read(
            tmp_path / "TEST_ONLY_market", v2, at=datetime(2025, 1, 3, 12, tzinfo=UTC)
        )
