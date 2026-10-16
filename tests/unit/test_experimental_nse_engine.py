"""TEST_ONLY candles exercise the separate experimental engine, not NSE results."""

import copy
import hashlib
import json
import math
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Self

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from workers.experimental_nse import models as model_module
from workers.experimental_nse.features import FEATURE_NAMES, build
from workers.experimental_nse.models import (
    load_model,
    predict_vector,
    save_model,
    score,
    train,
)

KEY = "NSE_EQ|INE002A01018"


def fixture_rows(count: int = 200) -> tuple[list[dict[str, Any]], list[str]]:
    """Explicit synthetic positive/negative OC patterns, never authentic prices."""
    end = datetime.now(UTC).date() - timedelta(days=1)
    dates = [end - timedelta(days=index) for index in range(count * 2)]
    sessions = sorted(day.isoformat() for day in dates if day.weekday() < 5)[-count:]
    rows = []
    for index, day in enumerate(sessions):
        movement = math.sin(index * 0.7) * 0.015 + math.cos(index * 0.13) * 0.003
        rows.append(
            {
                "key": KEY,
                "symbol": "TEST_ONLY",
                "session": day,
                "open": "100",
                "high": "105",
                "low": "95",
                "close": str(100 * (1 + movement)),
                "volume": 1000,
            }
        )
    return rows, sessions


def test_feature_no_lookahead_and_exact_order() -> None:
    rows, sessions = fixture_rows(80)
    original = build(rows, sessions)
    changed = copy.deepcopy(rows)
    changed[-1]["close"] = "104"
    updated = build(changed, sessions)
    for before, after in zip(original.samples[:-1], updated.samples[:-1], strict=True):
        assert before.vector == after.vector
    assert len(original.samples[0].vector) == len(FEATURE_NAMES) == 11
    assert original.samples[-1].target is None
    assert original.samples[0].target_session == sessions[24]


def test_same_session_scaling_invariant_even_across_split() -> None:
    rows, sessions = fixture_rows(80)
    adjusted = copy.deepcopy(rows)
    for index, row in enumerate(adjusted):
        factor = 0.5 if index < 40 else 4.0
        for name in ("open", "high", "low", "close"):
            row[name] = str(float(row[name]) * factor)
    left, right = build(rows, sessions), build(adjusted, sessions)
    for before, after in zip(left.samples, right.samples, strict=True):
        assert before.vector == pytest.approx(after.vector, abs=1e-14)
        assert before.target_return == pytest.approx(after.target_return)


def test_missing_session_rejects_window_and_target_without_fill() -> None:
    rows, sessions = fixture_rows(80)
    missing = sessions[40]
    dataset = build([row for row in rows if row["session"] != missing], sessions)
    available = {sample.session: sample for sample in dataset.samples}
    assert missing not in available
    assert sessions[59] not in available
    assert sessions[60] in available
    assert available[sessions[39]].target is None
    assert any(item["reason"] == "MISSING_OBSERVED_SESSION" for item in dataset.exclusions)


def test_flat_candle_has_real_zero_features_without_imputation() -> None:
    rows, sessions = fixture_rows(30)
    for row in rows:
        row.update(open="100", high="100", low="100", close="100", volume=0)
    dataset = build(rows, sessions)
    assert dataset.samples[0].vector == (0.0,) * 11
    assert dataset.samples[0].target == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("close", "NaN"),
        ("open", "0"),
        ("high", "90"),
        ("volume", True),
        ("key", "BSE|INE002A01018"),
    ],
)
def test_invalid_observation_rejected(field: str, value: Any) -> None:
    rows, sessions = fixture_rows(30)
    rows[0][field] = value
    with pytest.raises(ValueError):
        build(rows, sessions)


def test_duplicate_sessions_rejected() -> None:
    rows, sessions = fixture_rows(30)
    with pytest.raises(ValueError, match="DUPLICATE"):
        build([*rows, rows[0]], sessions)
    with pytest.raises(ValueError, match="SORTED_UNIQUE"):
        build(rows, [*sessions, sessions[0]])


@pytest.fixture(scope="module")
def trained() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[str]]:
    rows, sessions = fixture_rows()
    model, report, forecasts = train(rows, sessions, "TEST_ONLY_DATASET", datetime.now(UTC))
    assert forecasts == []  # no genuine receipt timestamp supplied to this fixture
    return model, report, rows, sessions


def test_chronological_purge_scaling_and_evaluation(trained: tuple[Any, ...]) -> None:
    model, report, rows, sessions = trained
    splits = report["splits"]
    assert splits["train"]["last_target_session"] < splits["validation"]["start"]
    assert splits["validation"]["last_target_session"] < splits["final"]["start"]
    dataset = build(rows, sessions)
    training = [sample for sample in dataset.samples if sample.session <= splits["train"]["end"]]
    expected = math.fsum(sample.vector[0] for sample in training) / len(training)
    assert model["mean"][0] == pytest.approx(expected)
    assert report["evaluation"]["final"]["candidate"]["sample_count"] > 0
    assert report["final_evaluation_used_for_selection"] is False
    assert report["independent_model_accepted"] is False


def test_secure_model_reload_parity_and_immutability(
    tmp_path: Path, trained: tuple[Any, ...]
) -> None:
    model, _, rows, sessions = trained
    path = tmp_path / "test-only-model.json"
    checksum = save_model(path, model)
    reloaded = load_model(path, checksum)
    vector = build(rows, sessions).samples[-1].vector
    assert predict_vector(model, vector) == predict_vector(reloaded, vector)
    assert save_model(path, model) == checksum
    with pytest.raises(ValueError, match="CHECKSUM"):
        load_model(path, "0" * 64)
    altered = copy.deepcopy(model)
    altered["intercept"] += 1
    body = {key: value for key, value in altered.items() if key != "model_id"}
    altered["model_id"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    with pytest.raises(ValueError, match="IMMUTABLE"):
        save_model(path, altered)


def test_feature_order_nan_and_arbitrary_model_types_rejected(trained: tuple[Any, ...]) -> None:
    model, _, rows, sessions = trained
    altered = copy.deepcopy(model)
    altered["feature_names"] = list(reversed(FEATURE_NAMES))
    with pytest.raises(ValueError, match="CONTRACT"):
        predict_vector(altered, [0.0] * 11)
    with pytest.raises(ValueError, match="FINITE"):
        predict_vector(model, [float("nan")] * 11)
    altered = copy.deepcopy(model)
    altered["python_type"] = "unsafe.object"
    with pytest.raises(ValueError, match="SCHEMA"):
        predict_vector(altered, build(rows, sessions).samples[-1].vector)


def test_json_scores_match_independent_sklearn_inference(trained: tuple[Any, ...]) -> None:
    """TEST_ONLY coefficient export preserves sklearn scaler/logistic arithmetic."""
    model, _, rows, sessions = trained
    vectors = np.asarray([sample.vector for sample in build(rows, sessions).samples])
    scaler = StandardScaler()
    scaler.mean_ = np.asarray(model["mean"])
    scaler.scale_ = np.asarray(model["scale"])
    scaler.var_ = scaler.scale_**2
    scaler.n_features_in_ = 11
    estimator = LogisticRegression()
    estimator.classes_ = np.asarray([0, 1])
    estimator.coef_ = np.asarray([model["coefficients"]])
    estimator.intercept_ = np.asarray([model["intercept"]])
    estimator.n_features_in_ = 11
    independent = estimator.predict_proba(scaler.transform(vectors))[:, 1]
    portable = [predict_vector(model, vector)[0] for vector in vectors.tolist()]
    assert portable == pytest.approx(independent, abs=1e-14)


def test_current_score_identity_and_no_backdating(trained: tuple[Any, ...]) -> None:
    model, _, rows, sessions = trained
    now = datetime.now(UTC)
    scored = score(model, rows, sessions, now, now - timedelta(seconds=1))
    assert len(scored) == 1
    assert scored[0]["key"] == KEY
    assert scored[0]["symbol"] == "TEST_ONLY"
    assert scored[0]["session"] == sessions[-1]
    assert scored[0]["accepted_prediction"] is False
    assert scored[0]["score_label"] == "UNCALIBRATED_LOGISTIC_MODEL_SCORE"
    assert 0 <= scored[0]["baseline_majority_score"] <= 1
    assert scored[0]["baseline_momentum_score"] in (0.0, 1.0)
    with pytest.raises(ValueError, match="NONBACKDATED"):
        score(model, rows, sessions, now - timedelta(minutes=1), now - timedelta(minutes=2))
    with pytest.raises(ValueError, match="NONBACKDATED"):
        score(model, rows, sessions, now + timedelta(minutes=1), now)
    with pytest.raises(ValueError, match="NONBACKDATED"):
        score(model, rows, sessions, datetime.now(UTC) + timedelta(seconds=1), now)
    with pytest.raises(ValueError, match="PRECEDE"):
        score(model, rows, sessions, now, now + timedelta(seconds=1))


def test_same_day_scores_require_elapsed_session_evidence(
    trained: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    model, _, rows, sessions = trained
    now = datetime.now(UTC)
    today = now.astimezone(__import__("zoneinfo").ZoneInfo("Asia/Kolkata")).date().isoformat()
    current = copy.deepcopy(rows)
    current.append({**current[-1], "session": today})
    reference = [*sessions, today]
    with pytest.raises(ValueError, match="COMPLETED_PRIOR_SESSION"):
        score(model, current, reference, now, now - timedelta(seconds=1))
    # This constructed clock isolates same-day proof validation from wall-clock hour.
    later = datetime.fromisoformat(today + "T20:00:00+05:30").astimezone(UTC)
    model = copy.deepcopy(model)
    model["trained_at"] = (later - timedelta(days=1)).isoformat()
    model["model_id"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in model.items() if key != "model_id"},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()

    class Clock(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Self:
            return cls.fromtimestamp(later.timestamp(), tz=tz)

    monkeypatch.setattr(model_module, "datetime", Clock)
    end = datetime.fromisoformat(today + "T15:30:00+05:30")
    scored = score(
        model, current, reference, later, later - timedelta(seconds=1), completed_session_end=end
    )
    assert len(scored) == 1 and scored[0]["session"] == today
    with pytest.raises(ValueError, match="COMPLETED_PRIOR_SESSION"):
        score(
            model,
            current,
            reference,
            later,
            later - timedelta(seconds=1),
            completed_session_end=later + timedelta(seconds=1),
        )


def test_future_data_and_stale_data_rejected(trained: tuple[Any, ...]) -> None:
    model, _, rows, sessions = trained
    now = datetime.now(UTC)
    future = copy.deepcopy(rows)
    future[-1]["session"] = (date.today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="PRIOR_SESSION"):
        score(model, future, [*sessions[:-1], future[-1]["session"]], now, now)
    with pytest.raises(ValueError, match="STALE"):
        score(model, rows[:-10], sessions[:-10], now, now)
