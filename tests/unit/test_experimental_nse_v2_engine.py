"""TEST_ONLY financial/chronology and portable-model parity; not real NSE evidence."""

import copy
import hashlib
import json
import math
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from workers.experimental_nse_v2 import models as model_module
from workers.experimental_nse_v2.features import (
    FEATURE_NAMES,
    LOCAL_FEATURE_NAMES,
    LOCAL_FEATURE_VERSION,
    build,
)
from workers.experimental_nse_v2.models import (
    ALGORITHMS,
    PARAMETERS,
    _artifact,
    load_model,
    predict_vector,
    save_model,
    score,
    validate_model,
)


def rows_fixture(count: int = 180, securities: int = 2) -> tuple[list[dict[str, Any]], list[str]]:
    days = [date(2023, 1, 1) + timedelta(days=index) for index in range(count * 2)]
    sessions = [day.isoformat() for day in days if day.weekday() < 5][:count]
    rows = []
    for instrument in range(securities):
        for index, session in enumerate(sessions):
            opening = 100 + instrument * 20 + index * 0.03 + math.sin(index * 0.1)
            close = opening * (1 + 0.015 * math.sin(index * 0.7 + instrument))
            rows.append(
                {
                    "key": f"NSE_EQ|INE{instrument:09d}",
                    "symbol": f"TEST_ONLY{instrument}",
                    "session": session,
                    "open": str(opening),
                    "high": str(max(opening, close) + 1),
                    "low": str(min(opening, close) - 1),
                    "close": str(close),
                    "volume": 1000,
                }
            )
    return rows, sessions


def test_twenty_features_prior_data_only_and_target_later_entry() -> None:
    rows, sessions = rows_fixture()
    original = build(rows, sessions)
    changed = copy.deepcopy(rows)
    changed[-1]["close"] = changed[-1]["high"]
    updated = build(changed, sessions)
    before = {(sample.key, sample.session): sample for sample in original.samples}
    after = {(sample.key, sample.session): sample for sample in updated.samples}
    assert len(FEATURE_NAMES) == 20
    for identity, item in before.items():
        if identity[1] < sessions[-1]:
            assert item.vector == after[identity].vector
    sample = original.samples[0]
    assert sample.session == sessions[60]
    assert sample.target_session == sessions[65]
    mapping = {(row["key"], row["session"]): row for row in rows}
    expected = (
        float(mapping[sample.key, sessions[65]]["close"])
        / float(mapping[sample.key, sessions[61]]["open"])
        - 1
    )
    assert sample.target_return == pytest.approx(expected)
    assert original.samples[-1].target is None


def test_action_window_exclusion_preserves_calendar_and_unaffected_history() -> None:
    rows, sessions = rows_fixture()
    key = rows[0]["key"]
    dataset = build(rows, sessions, {key: [sessions[90]]})
    assert not any(
        sample.key == key and sessions[90] <= sample.session <= sessions[150]
        for sample in dataset.samples
    )
    preceding = next(
        sample for sample in dataset.samples if sample.key == key and sample.session == sessions[89]
    )
    assert preceding.target is None
    assert any(
        item["reason"] == "KNOWN_CORPORATE_ACTION_TARGET_EXCLUSION" for item in dataset.exclusions
    )
    assert dataset.sessions == tuple(sessions)


def test_missing_slot_is_never_filled_and_context_excludes_below_eighty_percent() -> None:
    rows, sessions = rows_fixture(securities=5)
    keys = {rows[0]["key"], "NSE_EQ|INE000000001"}
    missing = [row for row in rows if not (row["key"] in keys and row["session"] == sessions[90])]
    dataset = build(missing, sessions)
    assert not any(sample.session == sessions[90] for sample in dataset.samples)
    assert any(
        item["reason"] == "INSUFFICIENT_80_PERCENT_FIXED_COHORT_CONTEXT"
        for item in dataset.exclusions
    )


def test_duplicate_future_or_inconsistent_identity_rejected() -> None:
    rows, sessions = rows_fixture()
    with pytest.raises(ValueError, match="DUPLICATE_SECURITY_SESSION"):
        build([*rows, rows[0]], sessions)
    changed = copy.deepcopy(rows)
    changed[0]["symbol"] = "CHANGED"
    with pytest.raises(ValueError, match="IDENTITY_SYMBOL_CHANGED"):
        build(changed, sessions)
    with pytest.raises(ValueError, match="OBSERVATION_OUTSIDE_REFERENCE"):
        build(rows, sessions[:-1])


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("include_context", [True, False])
def test_portable_json_real_estimator_parity_and_secure_reload(
    algorithm: str, include_context: bool, tmp_path: Path
) -> None:
    rows, sessions = rows_fixture()
    samples = [
        sample
        for sample in build(rows, sessions, include_context=include_context).samples
        if sample.target is not None
    ]
    model = _artifact(algorithm, samples, "TEST_ONLY", "a" * 64, datetime.now(UTC), include_context)
    path = tmp_path / f"{algorithm}.json"
    checksum = save_model(path, model)
    assert load_model(path, checksum) == model
    x = np.asarray([sample.vector for sample in samples])
    y = np.asarray([sample.target for sample in samples])
    returns = np.asarray([sample.target_return for sample in samples], dtype=float)
    with threadpool_limits(limits=4):
        if algorithm in ("LOGISTIC", "RIDGE"):
            transformed = StandardScaler().fit_transform(x)
            if algorithm == "LOGISTIC":
                fitted: Any = LogisticRegression(**PARAMETERS[algorithm]).fit(transformed, y)
                expected = fitted.predict_proba(transformed)[:, 1]
            else:
                fitted = Ridge(**PARAMETERS[algorithm]).fit(transformed, returns)
                expected = 1 / (1 + np.exp(-fitted.predict(transformed) / np.std(returns)))
        elif algorithm == "RANDOM_FOREST":
            fitted = RandomForestClassifier(**PARAMETERS[algorithm]).fit(x, y)
            expected = fitted.predict_proba(x)[:, 1]
        else:
            fitted = HistGradientBoostingClassifier(**PARAMETERS[algorithm]).fit(x, y)
            expected = fitted.predict_proba(x)[:, 1]
    actual = [predict_vector(model, sample.vector)[0] for sample in samples]
    assert actual == pytest.approx(expected, abs=1e-12)
    path.write_text("{}")
    with pytest.raises(ValueError, match="CHECKSUM"):
        load_model(path, checksum)


def test_model_schema_hash_feature_order_and_cycle_rejected() -> None:
    rows, sessions = rows_fixture()
    samples = [sample for sample in build(rows, sessions).samples if sample.target is not None]
    model = _artifact("LOGISTIC", samples, "TEST_ONLY", "a" * 64, datetime.now(UTC))
    changed = copy.deepcopy(model)
    changed["feature_names"].reverse()
    with pytest.raises(ValueError, match="CONSTRAINED"):
        validate_model(changed)
    changed = copy.deepcopy(model)
    changed["payload"]["intercept"] += 0.1
    with pytest.raises(ValueError, match="HASH"):
        validate_model(changed)
    forest = _artifact("RANDOM_FOREST", samples, "TEST_ONLY", "a" * 64, datetime.now(UTC))
    forest["payload"]["trees"][0][0] = [0, 0.1, 0, 0, 0.5]
    body = {key: value for key, value in forest.items() if key != "model_id"}
    forest["model_id"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    with pytest.raises(ValueError, match="FORWARD_ONLY"):
        validate_model(forest)


def test_backdated_inference_and_already_elapsed_entry_are_rejected() -> None:
    rows, sessions = rows_fixture()
    samples = [sample for sample in build(rows, sessions).samples if sample.target is not None]
    now = datetime.now(UTC)
    model = _artifact("LOGISTIC", samples, "TEST_ONLY", "a" * 64, now)
    with pytest.raises(ValueError, match="NONBACKDATED"):
        score(
            model,
            rows,
            sessions,
            now - timedelta(minutes=1),
            now - timedelta(minutes=2),
            now + timedelta(days=1),
            (now + timedelta(days=1)).date().isoformat(),
        )
    with pytest.raises(ValueError, match="FUTURE_ENTRY"):
        score(
            model,
            rows,
            sessions,
            datetime.now(UTC),
            now,
            now - timedelta(days=1),
            (now - timedelta(days=1)).date().isoformat(),
        )


@pytest.mark.parametrize("include_context", [True, False])
def test_fold_purge_embargo_selection_excludes_known_2026(
    monkeypatch: pytest.MonkeyPatch,
    include_context: bool,
) -> None:
    rows, sessions = rows_fixture(1200)
    offset = date(2022, 1, 3) - date.fromisoformat(sessions[0])
    shifted = [(date.fromisoformat(day) + offset).isoformat() for day in sessions]
    mapping = dict(zip(sessions, shifted, strict=True))
    for row in rows:
        row["session"] = mapping[row["session"]]
    recorded = []

    def fake_artifact(algorithm: str, samples: Any, *args: Any) -> dict[str, Any]:
        recorded.append((algorithm, tuple(samples)))
        return {"model_id": "TEST_ONLY", "algorithm": algorithm}

    def fake_predict(model: Any, vector: Any) -> tuple[float, list[float]]:
        return (0.5 + 0.01 * math.tanh(vector[1]), [])

    monkeypatch.setattr(model_module, "_artifact", fake_artifact)
    monkeypatch.setattr(model_module, "_predict", fake_predict)
    monkeypatch.setattr(model_module, "_uncertainty", lambda *args: {})
    _, report = model_module.train(
        rows,
        shifted,
        "TEST_ONLY",
        "a" * 64,
        datetime(2030, 1, 1, tzinfo=UTC),
        include_context=include_context,
    )
    assert report["actual_fit_count"] == 17
    assert len(recorded) == 17
    for fold in report["historical_folds"].values():
        first = fold["evaluation_first_decision"]
        prior = [day for day in shifted if day < first]
        assert fold["training_last_target"] < prior[-41]
        assert fold["training_last_decision"] < prior[-21]
        assert fold["classification"] == "RETROSPECTIVE_DEVELOPMENT_NOT_UNTOUCHED_TEST"
    assert "2023_2025" in report["selection_rule"]
    assert report["selected_algorithm"] == "LOGISTIC"  # predeclared fixed-order ties
    assert report["selection_is_independent_evidence"] is False
    assert report["accepted_current_rankings"] == 0


def test_companion_is_exact_local_contract_and_preserves_all_action_gates() -> None:
    rows, sessions = rows_fixture(securities=5)
    hazards = {rows[0]["key"]: [sessions[-1]], "NSE_EQ|INE000000001": [sessions[-1]]}
    primary = build(rows, sessions, hazards)
    companion = build(rows, sessions, hazards, include_context=False)
    latest_primary = [sample for sample in primary.samples if sample.session == sessions[-1]]
    latest_companion = [sample for sample in companion.samples if sample.session == sessions[-1]]
    assert latest_primary == []
    assert len(latest_companion) == 3
    assert all(len(sample.vector) == len(LOCAL_FEATURE_NAMES) == 16 for sample in latest_companion)
    assert all(sample.key not in hazards for sample in latest_companion)
    original = {(sample.key, sample.session): sample for sample in primary.samples}
    for sample in companion.samples:
        if (sample.key, sample.session) in original:
            assert sample.vector == original[sample.key, sample.session].vector[:16]
            assert sample.target_return == original[sample.key, sample.session].target_return
    assert all(sample.risk["feature_context"] == "SINGLE_SECURITY" for sample in companion.samples)
    assert all(sample.risk["fixed_cohort_context_members"] is None for sample in companion.samples)


def test_companion_model_cannot_impersonate_primary_feature_contract() -> None:
    rows, sessions = rows_fixture()
    samples = [
        sample
        for sample in build(rows, sessions, include_context=False).samples
        if sample.target is not None
    ]
    model = _artifact("LOGISTIC", samples, "TEST_ONLY", "a" * 64, datetime.now(UTC), False)
    assert model["feature_version"] == LOCAL_FEATURE_VERSION
    assert model["feature_names"] == list(LOCAL_FEATURE_NAMES)
    with pytest.raises(ValueError, match="ORDERED_V2_VECTOR"):
        predict_vector(model, [0.0] * 20)
    changed = copy.deepcopy(model)
    changed["feature_version"] = "nse.adjusted-price-context.20.v2"
    with pytest.raises(ValueError, match="CONSTRAINED"):
        validate_model(changed)


def test_companion_live_score_uses_saved_sixteen_feature_contract() -> None:
    rows, sessions = rows_fixture(securities=5)
    latest = datetime.now(UTC).date() - timedelta(days=1)
    offset = latest - date.fromisoformat(sessions[-1])
    shifted = [(date.fromisoformat(day) + offset).isoformat() for day in sessions]
    mapping = dict(zip(sessions, shifted, strict=True))
    for row in rows:
        row["session"] = mapping[row["session"]]
    hazards = {rows[0]["key"]: [shifted[-1]], "NSE_EQ|INE000000001": [shifted[-1]]}
    samples = [
        sample
        for sample in build(rows, shifted, hazards, include_context=False).samples
        if sample.target is not None
    ]
    observed = datetime.now(UTC)
    model = _artifact("LOGISTIC", samples, "TEST_ONLY", "a" * 64, observed, False)
    decision = datetime.now(UTC)
    entry = decision + timedelta(days=1)
    # TEST_ONLY calendar reference; a real forward ledger separately validates official evidence.
    from zoneinfo import ZoneInfo

    result = score(
        model,
        rows,
        shifted,
        decision,
        observed,
        entry,
        entry.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat(),
        hazards,
    )
    assert len(result) == 3
    assert all(item["feature_version"] == LOCAL_FEATURE_VERSION for item in result)
    assert all(item["feature_names"] == list(LOCAL_FEATURE_NAMES) for item in result)
    assert all(len(item["features"]) == 16 for item in result)
    assert all(item["eligible_for_prospective"] is True for item in result)


def test_frozen_training_baseline_allows_current_only_feature_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Later revised/rolling observations must not replace original train prevalence."""
    from dataclasses import replace
    from zoneinfo import ZoneInfo

    rows, sessions = rows_fixture()
    latest = datetime.now(UTC).date() - timedelta(days=1)
    offset = latest - date.fromisoformat(sessions[-1])
    shifted = [(date.fromisoformat(day) + offset).isoformat() for day in sessions]
    mapping = dict(zip(sessions, shifted, strict=True))
    for row in rows:
        row["session"] = mapping[row["session"]]
    frame = build(rows, shifted, include_context=False)
    training = [sample for sample in frame.samples if sample.target is not None]
    observed = datetime.now(UTC)
    model = _artifact("LOGISTIC", training, "TEST_ONLY", "a" * 64, observed, False)
    current = replace(
        frame, samples=tuple(sample for sample in frame.samples if sample.session == shifted[-1])
    )
    monkeypatch.setattr(model_module, "build", lambda *args, **kwargs: current)
    decision = datetime.now(UTC)
    entry = decision + timedelta(days=1)
    arguments = (
        model,
        rows,
        shifted,
        decision,
        observed,
        entry,
        entry.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat(),
    )
    with pytest.raises(ValueError, match="ORIGINAL_TRAINING_LABELS"):
        score(*arguments)
    result = score(*arguments, training_majority_score=0.37)
    assert len(result) == 2
    assert all(row["baseline_majority_score"] == 0.37 for row in result)
    with pytest.raises(ValueError, match="MAJORITY_SCORE"):
        score(*arguments, training_majority_score=1.1)
