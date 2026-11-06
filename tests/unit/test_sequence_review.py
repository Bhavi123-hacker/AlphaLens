"""TEST_ONLY report correction and independent timing protection; no market inference."""

import copy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse.acquire import digest, initialize, write_new
from workers.nse_market import engine, sequence, sequence_review


def fixture_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, dict[str, Any]]:
    root, source = tmp_path / "TEST_ONLY_model", tmp_path / "TEST_ONLY_source"
    initialize(root)
    initialize(source)
    now = datetime.now(UTC)
    yesterday = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = yesterday + timedelta(days=2)
    key, session = "TEST_ONLY_SECURITY", yesterday.date().isoformat()
    model = {"protocol_sha256": "TEST_ONLY_PINNED_PROTOCOL"}
    model_sha = engine._checked(root / "model.json", model)
    report = {
        "family": "ALPHALENS_SEQUENCE_BENCHMARK_V1",
        "protocol_sha256": model["protocol_sha256"],
        "model_sha256": model_sha,
        "accepted_rankings": 0,
        "prospective_forecasts": 0,
        "matured_prospective_outcomes": 0,
        "completed_at": (now - timedelta(seconds=5)).isoformat(),
        "current_scores": [
            {
                "key": key,
                "symbol": "TEST_ONLY",
                "session": session,
                "observed_price": "100",
                "score": 0.51,
                "model_sha256": model_sha,
                "inference_at": (yesterday + timedelta(hours=16)).isoformat(),
                "source_observed_at": (yesterday + timedelta(hours=12)).isoformat(),
                "forecast_created": False,
                "classification": "EXPERIMENTAL_ML",
                "calibration_status": "NOT_ESTABLISHED",
            }
        ],
        "comparisons": {
            "RIDGE": {
                "metrics": {
                    "brier_score": 0.4,
                    "calibration_bins": [0.1],
                    "probability_calibration_established": False,
                    "balanced_accuracy": 0.49,
                },
                "return_errors": {"mae": 0.2},
            },
            "LSTM": {"metrics": {"brier_score": 0.2, "balanced_accuracy": 0.51}},
        },
    }
    engine._checked(root / "report.json", report)
    engine._checked(root / "historical-predictions.json", {"model_sha256": model_sha, "rows": []})
    body = b"# TEST_ONLY exact executing source snapshot\n"
    write_new(root / "executing-source.py", body)
    engine._checked(root / "executing-source.json", {"sha256": digest(body)})
    frame = {
        "dataset_id": "TEST_ONLY_DATASET",
        "sessions": [session],
        "session_timing": {
            "session": session,
            "close_at": (yesterday + timedelta(hours=10)).isoformat(),
        },
        "next_session_timing": {
            "session": tomorrow.date().isoformat(),
            "open_at": (tomorrow + timedelta(hours=9)).isoformat(),
        },
        "rows": [{"key": key, "session": session, "symbol": "TEST_ONLY", "close": "100"}],
    }
    clock = {
        "lower_at": now.isoformat(),
        "upper_at": (now + timedelta(seconds=1)).isoformat(),
        "state": "TEST_ONLY_INDEPENDENT_CLOCK",
    }
    monkeypatch.setattr(sequence_review, "guard", lambda: clock)
    monkeypatch.setattr(engine, "snapshot", lambda _: copy.deepcopy(frame))
    return root, source, frame


def test_correction_preserves_models_scores_original_report_and_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, source, _ = fixture_review(tmp_path, monkeypatch)
    names = ("report.json", "model.json", "historical-predictions.json", "executing-source.py")
    before = {name: (root / name).read_bytes() for name in names}
    result = sequence_review.review(root, source)
    original = engine._read(root / "report.json")
    assert result["current_scores"] == original["current_scores"]
    assert result["comparisons"]["LSTM"] == original["comparisons"]["LSTM"]
    assert result["comparisons"]["RIDGE"]["return_errors"] == {"mae": 0.2}
    assert not any(
        name in result["comparisons"]["RIDGE"]["metrics"]
        for name in sequence_review.PROBABILITY_FIELDS
    )
    assert result["engineering_review"]["timing_attestation"]["forecast_records_created"] == 0
    assert (
        result["engineering_review"]["timing_attestation"]["original_process_executed_this_guard"]
        is False
    )
    assert result["original_report_sha256"] == digest(before["report.json"])
    assert all((root / name).read_bytes() == content for name, content in before.items())
    corrected_bytes = (root / "report-final.json").read_bytes()

    def no_new_attestation() -> dict[str, Any]:
        raise AssertionError("Idempotent replay must preserve original attestation")

    monkeypatch.setattr(sequence_review, "guard", no_new_attestation)
    assert sequence_review.review(root, source) == result
    assert (root / "report-final.json").read_bytes() == corrected_bytes


@pytest.mark.parametrize("fault", ["already_entered", "wrong_price", "future_report", "duplicate"])
def test_invalid_timing_or_identity_cannot_create_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    root, source, frame = fixture_review(tmp_path, monkeypatch)
    if fault == "already_entered":
        frame["next_session_timing"]["open_at"] = (
            datetime.now(UTC) - timedelta(hours=1)
        ).isoformat()
    if fault == "wrong_price":
        frame["rows"][0]["close"] = "999"
    if fault in {"future_report", "duplicate"}:
        original = engine._read(root / "report.json")
        if fault == "future_report":
            original["completed_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        else:
            original["current_scores"] *= 2
        # Replace only TEST_ONLY fixture evidence before exercising the correction.
        (root / "report.json").unlink()
        (root / "report.json.sha256").unlink()
        engine._checked(root / "report.json", original)
    with pytest.raises(ValueError, match="SEQUENCE_REVIEW"):
        sequence_review.review(root, source)
    assert not (root / "report-final.json").exists()


def test_review_rejects_any_undeclared_metric_or_score_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, source, _ = fixture_review(tmp_path, monkeypatch)
    corrected = sequence_review.review(root, source)
    original = engine._read(root / "report.json")
    altered = copy.deepcopy(corrected)
    altered["current_scores"][0]["score"] = 0.99
    with pytest.raises(ValueError, match="UNDECLARED"):
        sequence_review.validate_correction(original, altered)
    altered = copy.deepcopy(corrected)
    altered["comparisons"]["RIDGE"]["metrics"]["balanced_accuracy"] = 0.9
    with pytest.raises(ValueError, match="UNDECLARED"):
        sequence_review.validate_correction(original, altered)


def test_future_runs_withhold_current_scores_when_future_entry_or_clock_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, frame = fixture_review(tmp_path, monkeypatch)
    now = datetime.now(UTC)
    frame["source_observed_at"] = (
        datetime.fromisoformat(frame["session_timing"]["close_at"]) + timedelta(hours=1)
    ).isoformat()
    clock = {
        "lower_at": now.isoformat(),
        "upper_at": (now + timedelta(seconds=1)).isoformat(),
        "session_date": now.date().isoformat(),
    }
    monkeypatch.setattr(sequence, "guard", lambda: clock)
    assert sequence.current_timing(frame)["eligible"] is True
    frame["next_session_timing"]["open_at"] = (now - timedelta(hours=1)).isoformat()
    assert sequence.current_timing(frame)["eligible"] is False

    def missing_clock() -> dict[str, Any]:
        raise ValueError("TEST_ONLY_CLOCK_UNAVAILABLE")

    monkeypatch.setattr(sequence, "guard", missing_clock)
    assert sequence.current_timing(frame)["eligible"] is False
