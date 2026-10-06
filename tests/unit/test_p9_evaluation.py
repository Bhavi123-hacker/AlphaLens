"""Constructed TEST_ONLY fold, OOS and adversarial leakage evidence."""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError
from scripts.build_p6_test_fixture import day, instant
from scripts.build_p8_test_fixture import prepare
from scripts.build_p9_training_snapshots import snapshots
from scripts.verify_p9_test_only import definition

from alphalens_data.canonical.models import CanonicalBatch
from alphalens_data.errors import DataContractError
from alphalens_evaluation.contracts import Fold, OOSPrediction, WalkForwardDefinition, digest
from alphalens_evaluation.diagnostics import rank_diagnostics
from alphalens_evaluation.engine import EvaluationResult, evaluate
from alphalens_evaluation.engine_config import fold_config
from alphalens_evaluation.split import fold_split
from alphalens_evaluation.storage import OOSDataset, load, save
from alphalens_features.models import FeatureDataset
from alphalens_labels.alignment import SupervisedDataset
from alphalens_training.split import split


@pytest.fixture(scope="module")
def p9_source(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[
    CanonicalBatch,
    FeatureDataset,
    dict[int, SupervisedDataset],
    dict[int, dict[str, SupervisedDataset]],
]:
    root = tmp_path_factory.mktemp("TEST_ONLY_p9")
    aligned = prepare(root)
    features = FeatureDataset.model_validate_json((root / "features.json").read_bytes())
    batch = CanonicalBatch.model_validate(
        json.loads((root / "canonical/canonical-input.json").read_bytes())["batch"]
    )
    return batch, features, aligned, snapshots(root, features)


@pytest.fixture(scope="module")
def p9_result(
    p9_source: tuple[
        CanonicalBatch,
        FeatureDataset,
        dict[int, SupervisedDataset],
        dict[int, dict[str, SupervisedDataset]],
    ],
) -> EvaluationResult:
    _, features, aligned, training = p9_source
    return evaluate(
        aligned[5],
        features,
        definition(aligned[5], features, "classification", training[5]),
        training[5],
    )


@pytest.mark.parametrize("horizon", [1, 5, 10, 20])
@pytest.mark.parametrize("task", ["classification", "regression"])
def test_fold_arena_replay_chronology_maturity_and_fairness(
    p9_source: tuple[
        CanonicalBatch,
        FeatureDataset,
        dict[int, SupervisedDataset],
        dict[int, dict[str, SupervisedDataset]],
    ],
    horizon: int,
    task: str,
) -> None:
    _, features, aligned, training = p9_source
    data = aligned[horizon]
    plan = definition(data, features, task, training[horizon])
    first, second = (
        evaluate(data, features, plan, training[horizon]),
        evaluate(data, features, plan, training[horizon]),
    )
    assert first.manifest == second.manifest and first.predictions == second.predictions
    assert (
        first.fold_metrics == second.fold_metrics
        and first.negative_control == second.negative_control
    )
    assert len(first.fold_models) == 18 and len({id(m) for m in first.fold_models.values()}) == 18
    assert OOSDataset(first.manifest, first.predictions).verify() == plan
    for fold in plan.folds:
        holdout = fold_split(data, training[horizon][fold.fold_id], plan, fold)
        assert all(
            m.label_available_at is not None
            and m.label_available_at <= fold.training_cutoff
            and m.decision_time <= fold.training_cutoff
            and m.session_date < fold.test_start
            for m in holdout.train_metadata
        )
        assert all(
            fold.test_start <= m.session_date <= fold.test_end for m in holdout.validation_metadata
        )
        fair = [r for r in first.fold_metrics if r["fold_id"] == fold.fold_id]
        assert len({r["training_rows"] for r in fair}) == 1
        assert len({r["test_rows"] for r in fair}) == 1
        assert len({tuple(r["feature_order"]) for r in fair}) == 1
        for r in fair:
            assert r["comparisons"] and len(r["naive_metrics"]) == 2
        for family in plan.model_families:
            report = next(r for r in fair if r["model_family"] == family)
            imputer = first.fold_models[report["model_run_id"]].named_steps["imputer"]
            np.testing.assert_array_equal(imputer.statistics_, np.median(holdout.x_train, axis=0))
        if horizon > 1:
            assert holdout.exclusion_counts["LABEL_NOT_MATURE"] > 0
    assert len(first.negative_control["folds"]) == 3
    assert first.negative_control["evidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert all(
        v["evidence_status"] == "INSUFFICIENT_EVIDENCE" for v in first.model_comparison.values()
    )
    if horizon > 1:
        # Departed outcome may be missing later; issuing the earlier OOS prediction
        # cannot depend on knowing that economic recovery is unavailable.
        excluded = [r for r in first.predictions if r.scoring_status == "OUTCOME_EXCLUDED"]
        assert any(r.security_id == "TEST:DEPART" for r in excluded)
        assert all(r.actual_target is None and r.outcome_reason_codes for r in excluded)


def repin(data: SupervisedDataset, rows: tuple[Any, ...]) -> SupervisedDataset:
    changed = data.model_copy(update={"rows": rows})
    return SupervisedDataset.model_validate(
        changed.model_dump()
        | {
            "supervised_dataset_id": digest(
                changed.model_dump(mode="json", exclude={"supervised_dataset_id"})
            )
        }
    )


def test_future_test_features_targets_and_later_folds_never_fit_earlier_train(
    p9_source: tuple[
        CanonicalBatch,
        FeatureDataset,
        dict[int, SupervisedDataset],
        dict[int, dict[str, SupervisedDataset]],
    ],
) -> None:
    _, features, aligned, training = p9_source
    data = aligned[5]
    plan = definition(data, features, "classification", training[5])
    original = split(data, fold_config(plan, plan.folds[0]))
    rows = []
    for row in data.rows:
        if str(row.metadata["session_date"]) >= day(52).isoformat():
            targets = dict(row.targets)
            if targets["target_forward_return_5"] is not None:
                targets.update(target_forward_return_5="-0.9", target_direction_5=0)
            row = row.model_copy(
                update={
                    "targets": targets,
                    "features": {
                        n: value * 100 if value is not None else None
                        for n, value in row.features.items()
                    },
                }
            )
        rows.append(row)
    changed = repin(data, tuple(rows))
    after = split(changed, fold_config(plan, plan.folds[0]))
    np.testing.assert_array_equal(original.x_train, after.x_train)
    np.testing.assert_array_equal(original.y_train, after.y_train)
    assert original.train_metadata == after.train_metadata
    # Public evaluator rejects modified values without matching pinned P6 evidence.
    with pytest.raises(DataContractError, match="PINNED_INPUT"):
        evaluate(changed, features, plan, training[5])


def test_embargo_is_an_additional_knowledge_delay_and_preserves_exclusions(
    p9_source: tuple[
        CanonicalBatch,
        FeatureDataset,
        dict[int, SupervisedDataset],
        dict[int, dict[str, SupervisedDataset]],
    ],
) -> None:
    _, features, aligned, training = p9_source
    plan = definition(aligned[10], features, "regression", training[10])
    delayed = plan.model_copy(update={"embargo_seconds": 4 * 86400})
    normal = split(aligned[10], fold_config(plan, plan.folds[0]))
    purged = split(aligned[10], fold_config(delayed, plan.folds[0]))
    with pytest.raises(DataContractError, match="TRAINING_KNOWLEDGE"):
        fold_split(aligned[10], training[10]["fold-1"], delayed, plan.folds[0])
    assert len(purged.y_train) < len(normal.y_train)
    assert (
        purged.exclusion_counts["FEATURE_UNAVAILABLE"]
        == normal.exclusion_counts["FEATURE_UNAVAILABLE"]
    )
    assert all(
        m.label_available_at is not None and m.label_available_at <= instant(47, 12)
        for m in purged.train_metadata
    )


def test_oos_immutable_artifacts_schema_and_tamper_rejection(
    p9_result: EvaluationResult, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    path = save(p9_result, Path("data/evaluation"))
    assert save(p9_result, Path("data/evaluation")) == path
    assert load(path).predictions == p9_result.predictions
    target = path / "oos-predictions.parquet"
    target.write_bytes(target.read_bytes() + b"tampered")
    with pytest.raises(DataContractError, match="CHECKSUM"):
        load(path)


@pytest.mark.parametrize("change", ["in_sample", "later_model", "classification", "universe"])
def test_oos_only_and_lineage_guards(p9_result: EvaluationResult, change: str) -> None:
    row = p9_result.predictions[0]
    payload = row.model_dump(mode="json", exclude={"prediction_id"})
    if change == "in_sample":
        payload["role"] = "TRAIN"
    elif change == "later_model":
        payload["model_run_id"] = p9_result.predictions[-1].model_run_id
    elif change == "classification":
        payload["classification"] = "PRODUCTION"
    else:
        payload["universe_snapshot_id"] = "0" * 64
    if change in ("in_sample", "classification"):
        with pytest.raises(ValidationError):
            OOSPrediction.model_validate(dict(prediction_id=digest(payload), **payload))
    else:
        altered = OOSPrediction.model_validate(dict(prediction_id=digest(payload), **payload))
        dataset = OOSDataset(p9_result.manifest, (altered, *p9_result.predictions[1:]))
        with pytest.raises(DataContractError):
            dataset.verify()


def test_fold_contract_disallows_shuffling_overlap_production_and_tuning(
    p9_source: tuple[
        CanonicalBatch,
        FeatureDataset,
        dict[int, SupervisedDataset],
        dict[int, dict[str, SupervisedDataset]],
    ],
) -> None:
    _, features, aligned, training = p9_source
    plan = definition(aligned[5], features, "classification", training[5])
    for update in (
        {"folds": plan.folds[::-1]},
        {"data_classification": "PRODUCTION"},
        {"selection_policy": "TUNE_ON_TEST"},
        {"window": "RANDOM"},
    ):
        with pytest.raises(ValidationError):
            WalkForwardDefinition.model_validate(plan.model_dump() | update)
    with pytest.raises(ValidationError):
        Fold(fold_id="bad", training_cutoff=instant(52), test_start=day(52), test_end=day(56))


def test_fixed_cross_sectional_diagnostics_and_tiny_sample_uncertainty(
    p9_result: EvaluationResult,
) -> None:
    plan = WalkForwardDefinition.model_validate(p9_result.manifest["identity"]["definition"])
    row = p9_result.predictions[0]
    synthetic = []
    for i in range(5):
        payload = row.model_dump(mode="json", exclude={"prediction_id"}) | {
            "security_id": f"TEST:DIAGNOSTIC{i}",
            "probability": i / 5,
            "actual_forward_return": str(i / 10),
        }
        synthetic.append(
            OOSPrediction.model_validate(dict(prediction_id=digest(payload), **payload))
        )
    diagnostic = rank_diagnostics(synthetic, plan)
    assert diagnostic["sessions"][0]["spearman_ic"] > 0.99
    assert diagnostic["sessions"][0]["top_minus_bottom_target"] == 0.4
    assert (
        rank_diagnostics(synthetic[:4], plan)["status"] == "INSUFFICIENT_CROSS_SECTIONAL_EVIDENCE"
    )
    assert all(
        r["uncertainty"]["status"] == "INSUFFICIENT_EVIDENCE"
        for r in p9_result.model_comparison.values()
    )
