"""TEST_ONLY constructed chronology/native-model checks, never real empirical evidence."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from scripts.run_tejhq_research import evaluate_selected, export_series

from alphalens_data.normalization import checksum
from alphalens_data.research import ResearchProfile, calendar
from alphalens_evaluation.contracts import Fold
from alphalens_evaluation.models import build_model
from alphalens_evaluation.research import ResearchMatrix, evaluate_fold, fit_with_resources, masks
from alphalens_training.contracts import TrainingConfig


def matrix() -> ResearchMatrix:
    observed: set[date] = set()
    for year in (2021, 2022, 2026):
        start = date(year, 1, 4)
        observed.update(
            start + timedelta(days=i)
            for i in range(70)
            if (start + timedelta(days=i)).weekday() < 5
        )
    sessions = calendar(observed, ResearchProfile())
    rows = []
    features = []
    dates = sessions.dates
    for i, d in enumerate(dates[:-2]):
        for s in range(8):
            v = np.sin(i / 5 + s / 8)
            rows.append(
                dict(
                    security_id=f"TEST_ONLY_{s}",
                    session_date=d,
                    decision_time=sessions.availability(d),
                    canonical_record_id=checksum(f"TEST_ONLY:{d}:{s}".encode()),
                    target_return_1=str(v / 100),
                    target_direction_1=int(v > 0),
                    label_available_at_1=sessions.availability(dates[i + 1]),
                    training_eligible_1=True,
                    outcome_reasons_1=[],
                )
            )
            features.append([v, np.cos(i / 5 + s / 8)])
    schema = pa.schema(
        [
            ("security_id", pa.string()),
            ("session_date", pa.date32()),
            ("decision_time", pa.timestamp("us", tz="UTC")),
            ("canonical_record_id", pa.string()),
            ("target_return_1", pa.string()),
            ("target_direction_1", pa.int8()),
            ("label_available_at_1", pa.timestamp("us", tz="UTC")),
            ("training_eligible_1", pa.bool_()),
            ("outcome_reasons_1", pa.list_(pa.string())),
        ]
    )
    return ResearchMatrix(
        np.asarray(features),
        pa.Table.from_pylist(rows, schema=schema),
        ("return_1", "return_5"),
        checksum(b"TEST_ONLY_CONSTRUCTED"),
        1,
        sessions,
    )


def test_fold_purge_chronology_and_final_holdout_isolation() -> None:
    data = matrix()
    fold = Fold(
        fold_id="2022",
        training_cutoff=datetime(2022, 1, 1, tzinfo=UTC),
        test_start=date(2022, 1, 4),
        test_end=date(2022, 3, 31),
    )
    train, test = masks(data, fold)
    train_days = data.metadata.column("session_date").take(pa.array(train)).to_pylist()
    test_days = data.metadata.column("session_date").take(pa.array(test)).to_pylist()
    available = data.metadata.column("label_available_at_1").take(pa.array(train)).to_pylist()
    assert all(d.year == 2021 for d in train_days)
    assert all(d.year == 2022 for d in test_days)
    assert max(available) <= fold.training_cutoff - timedelta(days=1)
    assert not any(d.year == 2026 for d in train_days + test_days)


def test_final_period_cannot_run_without_precommitted_candidate_lock(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="REQUIRES_CANDIDATE_LOCK"):
        evaluate_selected(tmp_path, tmp_path, 2026)


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_parallel_forest_fit_preserves_exact_trees_and_serial_predictions(task: str) -> None:
    # TEST_ONLY nonlinear, correlated and widely scaled synthetic inputs.
    rng = np.random.default_rng(1729)
    x = rng.normal(size=(1200, 38))
    x[:, 20:] *= 100000
    y = x[:, 0] + np.sin(x[:, 1]) + rng.normal(size=len(x)) / 5
    if task == "classification":
        y = (y > 0).astype("float64")
    config = TrainingConfig(
        task=task,
        model_family="logistic" if task == "classification" else "ridge",
        horizon=1,
        training_cutoff=datetime(2022, 1, 1, tzinfo=UTC),
        validation_start=date(2022, 1, 4),
        validation_end=date(2022, 3, 31),
    )
    serial, parallel = (build_model("random_forest", config) for _ in range(2))
    fit_with_resources(serial, x.copy(), y, 1)
    fit_with_resources(parallel, x.copy(), y, 4)
    assert (
        serial.named_steps["estimator"].get_params()
        == parallel.named_steps["estimator"].get_params()
    )
    assert parallel.named_steps["estimator"].n_jobs == 1
    for a, b in zip(
        serial.named_steps["estimator"].estimators_,
        parallel.named_steps["estimator"].estimators_,
        strict=True,
    ):
        assert a.random_state == b.random_state
        np.testing.assert_array_equal(
            a.tree_.__getstate__()["nodes"], b.tree_.__getstate__()["nodes"]
        )
        np.testing.assert_array_equal(a.tree_.value, b.tree_.value)
    np.testing.assert_array_equal(serial.predict(x), parallel.predict(x))
    if task == "classification":
        np.testing.assert_array_equal(serial.predict_proba(x), parallel.predict_proba(x))


@pytest.mark.parametrize(
    "task, family",
    [
        ("classification", f)
        for f in [
            "logistic",
            "random_forest",
            "hist_gradient_boosting",
            "lightgbm",
            "catboost",
            "xgboost",
        ]
    ]
    + [
        ("regression", f)
        for f in [
            "ridge",
            "random_forest",
            "hist_gradient_boosting",
            "lightgbm",
            "catboost",
            "xgboost",
        ]
    ],
)
def test_native_arena_research_lineage_restart_and_oos_only(
    tmp_path: Path, task: str, family: str
) -> None:
    data = matrix()
    fold = Fold(
        fold_id="2022",
        training_cutoff=datetime(2022, 1, 1, tzinfo=UTC),
        test_start=date(2022, 1, 4),
        test_end=date(2022, 3, 31),
    )
    original_features = data.features.copy()
    first = evaluate_fold(data, fold, task, family, tmp_path)  # type: ignore[arg-type]
    np.testing.assert_array_equal(data.features, original_features)
    repeated = evaluate_fold(data, fold, task, family, tmp_path)  # type: ignore[arg-type]
    assert first == repeated
    assert first["final_vintage"] == "FINAL_VINTAGE_RESEARCH_ASSUMPTION"
    assert first["metrics"]["sample_count"] > 100
    p = pq.ParquetFile(tmp_path / first["oos_file"])
    assert p.schema_arrow.metadata[b"role"] == b"FOLD_TEST"
    assert all(d.year == 2022 for d in p.read(columns=["session_date"]).column(0).to_pylist())
    if task == "classification" and family == "logistic":
        # Export the actual frozen OOS file, never reconstruct model predictions.
        output = tmp_path.parent / "export"
        (output / "p9").mkdir(parents=True)
        import shutil

        shutil.copytree(tmp_path, output / "p9", dirs_exist_ok=True)
        receipt = export_series(output, [dict(first, phase="TEST_ONLY")], [], data.sessions.profile)
        series = pq.ParquetFile(output / receipt["files"][0]["path"])
        assert series.metadata.num_rows == p.metadata.num_rows
        assert series.schema_arrow.metadata[b"role"] == b"FOLD_TEST"
        assert series.read(columns=["score"]).column(0) == p.read(columns=["score"]).column(0)


def test_interrupted_final_attempt_cannot_be_silently_refitted(tmp_path: Path) -> None:
    import json

    data = matrix()
    fold = Fold(
        fold_id="2026",
        training_cutoff=datetime(2026, 1, 1, tzinfo=UTC),
        test_start=date(2026, 1, 4),
        test_end=date(2026, 3, 31),
    )
    (tmp_path / "classification-1-logistic-2026.attempt.json").write_text(json.dumps({}))
    with pytest.raises(ValueError, match="FINAL_HOLDOUT_ATTEMPT_INCOMPLETE"):
        evaluate_fold(data, fold, "classification", "logistic", tmp_path)
