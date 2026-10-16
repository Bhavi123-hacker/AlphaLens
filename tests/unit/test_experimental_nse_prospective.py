"""TEST_ONLY constructed observations; no test output is real NSE research evidence."""

import json
import sqlite3
from datetime import UTC, datetime
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from workers.experimental_nse import prospective
from workers.experimental_nse.features import FEATURE_NAMES

KEY = "NSE_EQ|INE002A01018"
DECISION = datetime(2025, 1, 2, 12, tzinfo=UTC)
RECEIVED = datetime(2025, 1, 2, 11, tzinfo=UTC)
SESSIONS = ("2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09")


def score(**overrides: Any) -> dict[str, Any]:
    return {
        "key": KEY,
        "symbol": "RELIANCE",
        "session": SESSIONS[0],
        "score": 0.6,
        "vector": [0.01] * len(FEATURE_NAMES),
        "source": "TEST_ONLY_CONSTRUCTED_NOT_MARKET_DATA",
        "baseline_majority_score": 0.4,
        "baseline_momentum_score": 1.0,
        **overrides,
    }


def rows() -> list[dict[str, Any]]:
    return [
        {
            "key": KEY,
            "symbol": "RELIANCE",
            "session": session,
            "open": "100",
            "high": "110",
            "low": "90",
            "close": "101",
            "volume": 100,
        }
        for session in SESSIONS[1:]
    ]


def record(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prospective, "_utc_now", lambda: DECISION)
    result = prospective.append_forecasts(
        root, "TEST_ONLY_MODEL", "TEST_ONLY_DATA", [score()], RECEIVED
    )
    assert result["inserted"] == 1


def mature(root: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    now = datetime(2025, 1, 10, 12, tzinfo=UTC)
    monkeypatch.setattr(prospective, "_utc_now", lambda: now)
    return prospective.reconcile(root, rows(), SESSIONS, now)


def test_actual_clock_frozen_vector_idempotence_and_immutable_sql(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    again = prospective.append_forecasts(
        tmp_path, "TEST_ONLY_MODEL", "TEST_ONLY_DATA", [score()], RECEIVED
    )
    assert again["inserted"] == 0 and again["replayed"] == 1
    with sqlite3.connect(tmp_path / "experimental-prospective.sqlite3") as connection:
        raw = connection.execute("SELECT body FROM experimental_forecasts").fetchone()[0]
        body = json.loads(raw)
        assert body["recorded_at"] == DECISION.isoformat()
        assert body["source_observed_at"] == RECEIVED.isoformat()
        assert body["vector"] == score()["vector"]
        assert body["prospective_eligible"] is True
        for operation in (
            "UPDATE experimental_forecasts SET body='{}'",
            "DELETE FROM experimental_forecasts",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="IMMUTABLE_FORECAST"):
                connection.execute(operation)
    summary = prospective.summary(tmp_path)
    assert summary["forecast_count"] == summary["prospective_eligible_forecast_count"] == 1
    assert summary["matured_outcome_count"] == 0
    assert summary["balanced_accuracy"] is None


@pytest.mark.parametrize("field", ["decision_at", "recorded_at", "forecast_at"])
def test_no_caller_can_backdate_forecast(tmp_path: Path, field: str) -> None:
    with pytest.raises(ValueError, match="CALLER_FORECAST_CLOCK_FORBIDDEN"):
        prospective.append_forecasts(
            tmp_path,
            "TEST_ONLY_MODEL",
            "TEST_ONLY_DATA",
            [score(**{field: RECEIVED.isoformat()})],
            RECEIVED,
        )


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"vector": []}, "COMPLETE_FINITE"),
        ({"vector": [float("nan")] * len(FEATURE_NAMES)}, "COMPLETE_FINITE"),
        ({"feature_names": list(reversed(FEATURE_NAMES))}, "FEATURE_CONTRACT"),
        ({"feature_hash": "0" * 64}, "FEATURE_HASH"),
        ({"session": "2030-01-01"}, "OBSERVATION_AFTER_SOURCE"),
        ({"score": float("nan")}, "FINITE_UNCALIBRATED"),
        ({"baseline_majority_score": float("nan")}, "PREDECLARED_BASELINE"),
        ({"inference_at": "2030-01-01T00:00:00Z"}, "INFERENCE_SOURCE_OR_RUNTIME"),
        ({"key": "BSE_EQ|INE002A01018"}, "EXACT_NSE_KEY"),
    ],
)
def test_incomplete_or_incompatible_inputs_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: dict[str, Any], error: str
) -> None:
    monkeypatch.setattr(prospective, "_utc_now", lambda: DECISION)
    with pytest.raises(ValueError, match=error):
        prospective.append_forecasts(
            tmp_path, "TEST_ONLY_MODEL", "TEST_ONLY_DATA", [score(**change)], RECEIVED
        )


def test_conflicting_replay_never_changes_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="IMMUTABLE_FORECAST_REPLAY_CONFLICT"):
        prospective.append_forecasts(
            tmp_path, "TEST_ONLY_MODEL", "TEST_ONLY_DATA", [score(score=0.7)], RECEIVED
        )
    assert prospective.summary(tmp_path)["forecast_count"] == 1


def test_next_day_replay_preserves_original_eligibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    monkeypatch.setattr(prospective, "_utc_now", lambda: datetime(2025, 1, 3, 7, tzinfo=UTC))
    result = prospective.append_forecasts(
        tmp_path, "TEST_ONLY_MODEL", "TEST_ONLY_DATA", [score()], RECEIVED
    )
    assert result["inserted"] == 0 and result["replayed"] == 1
    assert prospective.summary(tmp_path)["eligible_forecasts"] == 1


def test_prior_eod_before_regular_open_can_be_prospective(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prospective, "_utc_now", lambda: datetime(2025, 1, 3, 3, tzinfo=UTC))
    prospective.append_forecasts(tmp_path, "TEST_ONLY_MODEL", "TEST_ONLY_DATA", [score()], RECEIVED)
    assert mature(tmp_path, monkeypatch)["inserted"] == 1


def test_first_version_records_replay_without_retrospective_audit_backfill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    with sqlite3.connect(tmp_path / "experimental-prospective.sqlite3") as connection:
        # Construct only the earlier TEST_ONLY schema body; never migrate a real record.
        raw = connection.execute("SELECT body FROM experimental_forecasts").fetchone()[0]
        original = json.loads(raw)
        for field in (
            "inference_at",
            "regular_session_open_assumption",
            "baseline_majority_score",
            "baseline_momentum_score",
        ):
            original.pop(field)
        legacy = json.dumps(original, sort_keys=True, separators=(",", ":"), allow_nan=False)
        connection.execute("DROP TRIGGER experimental_forecasts_no_update")
        connection.execute(
            "UPDATE experimental_forecasts SET body=?,id=?",
            (legacy, sha256(legacy.encode()).hexdigest()),
        )
    result = prospective.append_forecasts(
        tmp_path, "TEST_ONLY_MODEL", "TEST_ONLY_DATA", [score()], RECEIVED
    )
    assert result["inserted"] == 0 and result["replayed"] == 1
    with sqlite3.connect(tmp_path / "experimental-prospective.sqlite3") as connection:
        assert connection.execute("SELECT body FROM experimental_forecasts").fetchone()[0] == legacy
    assert prospective.summary(tmp_path)["legacy_missing_baseline_count"] == 1


def test_outcome_maturity_exact_ratio_and_zero_write_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    result = mature(tmp_path, monkeypatch)
    assert result["inserted"] == 1
    assert mature(tmp_path, monkeypatch)["replayed"] == 1
    with sqlite3.connect(tmp_path / "experimental-prospective.sqlite3") as connection:
        body = json.loads(
            connection.execute("SELECT body FROM experimental_outcomes").fetchone()[0]
        )
        actual = Fraction(
            int(body["target_return_numerator"]), int(body["target_return_denominator"])
        )
        assert actual == Fraction(101, 100) ** 5 - 1
        assert body["target_session"] == SESSIONS[-1]
        for operation in (
            "UPDATE experimental_outcomes SET body='{}'",
            "DELETE FROM experimental_outcomes",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="IMMUTABLE_OUTCOME"):
                connection.execute(operation)
    summary = prospective.summary(tmp_path)
    assert summary["matured_outcome_count"] == 1
    assert summary["accuracy"] == 1
    assert summary["balanced_accuracy"] is None  # Only one target class, no invented statistic.
    assert summary["metrics"]["baselines"]["baseline_majority_score"]["accuracy"] == 0
    assert summary["metrics"]["baselines"]["baseline_momentum_score"]["accuracy"] == 1


def test_missing_slot_cannot_mature(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    record(tmp_path, monkeypatch)
    now = datetime(2025, 1, 10, 12, tzinfo=UTC)
    monkeypatch.setattr(prospective, "_utc_now", lambda: now)
    assert prospective.reconcile(tmp_path, rows()[:-1], SESSIONS, now)["pending"] == 1
    assert prospective.summary(tmp_path)["matured_outcome_count"] == 0


def test_future_observation_and_early_receipt_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prospective, "_utc_now", lambda: DECISION)
    with pytest.raises(ValueError, match="SOURCE_RETRIEVAL_AFTER_FORECAST"):
        prospective.append_forecasts(
            tmp_path, "TEST_ONLY_MODEL", "TEST_ONLY_DATA", [score()], "2025-01-03T00:00:00Z"
        )
    record(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="OUTCOME_COMPLETE_PAST_SESSION_REQUIRED"):
        prospective.reconcile(tmp_path, rows(), SESSIONS, RECEIVED)


def test_mid_session_inference_is_research_not_full_prospective_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prospective, "_utc_now", lambda: datetime(2025, 1, 3, 7, tzinfo=UTC))
    prospective.append_forecasts(tmp_path, "TEST_ONLY_MODEL", "TEST_ONLY_DATA", [score()], RECEIVED)
    result = mature(tmp_path, monkeypatch)
    assert result["ineligible"] == 1 and result["inserted"] == 0
    summary = prospective.summary(tmp_path)
    assert summary["research_only_forecast_count"] == 1
    assert summary["prospective_eligible_forecast_count"] == 0


def test_source_correction_appends_revision_without_changing_first_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    mature(tmp_path, monkeypatch)
    revised = rows()
    revised[0]["close"] = "99"
    now = datetime(2025, 1, 11, 12, tzinfo=UTC)
    monkeypatch.setattr(prospective, "_utc_now", lambda: now)
    assert prospective.reconcile(tmp_path, revised, SESSIONS, now)["corrections"] == 1
    summary = prospective.summary(tmp_path)
    assert summary["matured_outcome_count"] == 1
    assert summary["outcome_revision_count"] == 2
    assert summary["correction_count"] == 1


def test_hash_verification_detects_external_corruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record(tmp_path, monkeypatch)
    with sqlite3.connect(tmp_path / "experimental-prospective.sqlite3") as connection:
        connection.execute("DROP TRIGGER experimental_forecasts_no_update")
        connection.execute("UPDATE experimental_forecasts SET body='{}'")
    with pytest.raises(ValueError, match="CHECKSUM_MISMATCH"):
        prospective.summary(tmp_path)
