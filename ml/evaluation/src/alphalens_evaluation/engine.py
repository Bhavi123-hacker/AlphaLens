"""Fresh fold models consume P7 only; P6 evidence supplies traceability, never new inputs."""

from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from alphalens_data.errors import DataContractError
from alphalens_evaluation.contracts import (
    VERSION,
    OOSPrediction,
    WalkForwardDefinition,
    digest,
    disclaimer,
)
from alphalens_evaluation.diagnostics import rank_diagnostics, stability, uncertainty
from alphalens_evaluation.engine_config import fold_config
from alphalens_evaluation.models import build_model, versions
from alphalens_evaluation.split import fold_split
from alphalens_features.models import FeatureDataset
from alphalens_labels.alignment import SupervisedDataset
from alphalens_training.contracts import TrainingConfig, verify_dataset
from alphalens_training.metrics import classification_metrics, comparisons, regression_metrics
from alphalens_training.split import Holdout


def verify_input(
    data: SupervisedDataset, features: FeatureDataset, definition: WalkForwardDefinition
) -> None:
    definition = WalkForwardDefinition.model_validate(definition.model_dump())
    verify_dataset(data, fold_config(definition, definition.folds[0]))
    features = FeatureDataset.model_validate(features.model_dump())
    if (
        data.supervised_dataset_id != definition.supervised_dataset_id
        or data.feature_set_id != definition.feature_set_id
        or data.label_set_id != definition.label_set_id
        or data.classification != definition.data_classification
        or data.horizon != definition.horizon
        or features.feature_set_id != data.feature_set_id
        or features.canonical_dataset_id != definition.canonical_dataset_id
        or features.classification != data.classification
        or digest(features.model_dump(mode="json", exclude={"feature_set_id"}))
        != features.feature_set_id
    ):
        raise DataContractError("P9_PINNED_INPUT_MISMATCH")
    keyed = {(f.session_date.isoformat(), f.security_id): f for f in features.rows}
    for row in data.rows:
        key = (str(row.metadata["session_date"]), str(row.metadata["security_id"]))
        source = keyed.get(key)
        if source is None or (
            source.canonical_dataset_id != row.metadata["feature_canonical_dataset_id"]
            or source.universe_snapshot_id != row.metadata["universe_snapshot_id"]
            or source.decision_time.isoformat().replace("+00:00", "Z")
            != str(row.metadata["decision_time"]).replace("+00:00", "Z")
            or any(source.values[n].value != row.features[n] for n in data.feature_columns)
        ):
            raise DataContractError("P9_UPSTREAM_TRACE_MISMATCH")


def metrics_for(
    holdout: Holdout,
    predicted: np.ndarray[Any, Any],
    probability: np.ndarray[Any, Any] | None,
    config: TrainingConfig,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    mask = np.isfinite(holdout.y_validation)
    actual = holdout.y_validation[mask]
    predicted = predicted[mask]
    probability = probability[mask] if probability is not None else None
    if not len(actual):
        return (
            dict(
                sample_count=0, status="INSUFFICIENT_ACCEPTED_OUTCOMES", brier_score=None, mae=None
            ),
            {},
            False,
        )
    if config.task == "classification":
        if probability is None:
            raise DataContractError("CLASSIFICATION_PROBABILITY_REQUIRED")
        metrics = classification_metrics(actual, probability, config, predicted)
        rate = float(holdout.y_train.mean())
        naive = {
            "majority_class": classification_metrics(
                actual, np.full(len(actual), float(rate > 0.5)), config
            ),
            "training_positive_rate": classification_metrics(
                actual, np.full(len(actual), rate), config
            ),
        }
        beats = metrics["brier_score"] < naive["training_positive_rate"]["brier_score"]
    else:
        metrics = regression_metrics(actual, predicted)
        naive = {
            "zero_return": regression_metrics(actual, np.zeros(len(actual))),
            "training_mean": regression_metrics(
                actual, np.full(len(actual), float(holdout.y_train.mean()))
            ),
        }
        beats = metrics["mae"] < naive["training_mean"]["mae"]
    return metrics, naive, bool(beats)


@dataclass(frozen=True)
class EvaluationResult:
    manifest: dict[str, Any]
    fold_metrics: list[dict[str, Any]]
    model_comparison: dict[str, Any]
    predictions: tuple[OOSPrediction, ...]
    stability_report: dict[str, Any]
    negative_control: dict[str, Any]
    fold_models: dict[str, Pipeline]


def evaluate(
    data: SupervisedDataset,
    features: FeatureDataset,
    definition: WalkForwardDefinition,
    training_data: dict[str, SupervisedDataset],
) -> EvaluationResult:
    verify_input(data, features, definition)
    initial_config = fold_config(definition, definition.folds[0])
    arena = {
        family: {
            "estimator": build_model(family, initial_config)
            .named_steps["estimator"]
            .get_params(deep=False),
            "preprocessing": {
                name: step.get_params(deep=False)
                for name, step in build_model(family, initial_config).steps
                if name != "estimator"
            },
            "output_container": "PANDAS" if family == "lightgbm" else "NUMPY",
        }
        for family in definition.model_families
    }
    identity = dict(
        definition=definition.model_dump(mode="json"),
        resolved_arena=arena,
        environment=versions(),
        canonical_input_id=features.canonical_input_id,
        preprocessing="P8_TRAIN_MEDIAN_LINEAR_SCALER_TRAIN_CONSTANT_REMOVAL",
        configuration_policy="FIXED_32_TREES_NO_SEARCH_NO_EVAL_SET",
        prediction_policy="ALL_FEATURE_ELIGIBLE_TEST_ROWS_SCORE_ONLY_P7_ELIGIBLE_OUTCOMES",
        schema_version=VERSION,
    )
    evaluation_id = digest(identity)
    reports: list[dict[str, Any]] = []
    oos: list[OOSPrediction] = []
    models: dict[str, Pipeline] = {}
    model_manifests: dict[str, Any] = {}
    controls: list[dict[str, Any]] = []
    keyed = {
        (str(r.metadata["session_date"]), str(r.metadata["security_id"])): r for r in data.rows
    }
    for fold in definition.folds:
        config = fold_config(definition, fold)
        try:
            holdout = fold_split(data, training_data[fold.fold_id], definition, fold)
            if definition.task == "classification" and len(np.unique(holdout.y_train)) != 2:
                raise DataContractError("INSUFFICIENT_TRAINING_CLASSES")
        except DataContractError as exc:
            if (
                not str(exc).startswith("INSUFFICIENT")
                and str(exc) != "NO_NONCONSTANT_TRAIN_FEATURES"
            ):
                raise
            reports.extend(
                dict(
                    fold_id=fold.fold_id,
                    model_family=family,
                    status="INSUFFICIENT_EVIDENCE",
                    reason=str(exc),
                )
                for family in definition.model_families
            )
            continue
        for family in definition.model_families:
            model = build_model(family, config)
            parameters = model.named_steps["estimator"].get_params(deep=False)
            model_identity = dict(
                evaluation_id=evaluation_id,
                fold=fold.model_dump(mode="json"),
                effective_training_cutoff=config.training_cutoff.isoformat(),
                model_family=family,
                training_supervised_dataset_id=training_data[fold.fold_id].supervised_dataset_id,
                training_label_set_id=training_data[fold.fold_id].label_set_id,
                training_feature_set_id=training_data[fold.fold_id].feature_set_id,
                hyperparameters=parameters,
                preprocessing={
                    n: v.get_params(deep=False) for n, v in model.steps if n != "estimator"
                },
                training_row_digest=digest(
                    [m.model_dump(mode="json") for m in holdout.train_metadata]
                ),
                feature_order=holdout.feature_columns,
                configuration=config.model_dump(mode="json"),
                schema_version=definition.model_contract_version,
            )
            run_id = digest(model_identity)
            with threadpool_limits(limits=1):
                model.fit(holdout.x_train, holdout.y_train)
                predicted = np.asarray(model.predict(holdout.x_validation), dtype="float64").ravel()
                probability = (
                    np.asarray(model.predict_proba(holdout.x_validation)[:, 1], dtype="float64")
                    if definition.task == "classification"
                    else None
                )
            metrics, naive, beats = metrics_for(holdout, predicted, probability, config)
            models[run_id] = model
            model_manifests[run_id] = model_identity
            report = dict(
                fold_id=fold.fold_id,
                model_run_id=run_id,
                model_family=family,
                status="EVALUATED",
                training_rows=len(holdout.y_train),
                training_target_mean=float(holdout.y_train.mean()),
                test_rows=len(holdout.y_validation),
                scored_test_rows=int(np.isfinite(holdout.y_validation).sum()),
                outcome_exclusions=dict(
                    Counter(
                        reason for m in holdout.validation_metadata for reason in m.reason_codes
                    )
                ),
                training_period=[
                    holdout.train_metadata[0].session_date.isoformat(),
                    holdout.train_metadata[-1].session_date.isoformat(),
                ],
                test_period=[fold.test_start.isoformat(), fold.test_end.isoformat()],
                training_cutoff=config.training_cutoff.isoformat(),
                feature_order=holdout.feature_columns,
                removed_features=holdout.removed_features,
                exclusion_counts=holdout.exclusion_counts,
                excluded_rows=holdout.excluded_rows,
                metrics=metrics,
                naive_metrics=naive,
                comparisons=comparisons(metrics, naive),
                beats_naive=beats,
            )
            reports.append(report)
            for index, meta in enumerate(holdout.validation_metadata):
                row = keyed[meta.session_date.isoformat(), meta.security_id]
                payload = dict(
                    evaluation_id=evaluation_id,
                    role="FOLD_TEST",
                    security_id=meta.security_id,
                    session_date=meta.session_date.isoformat(),
                    decision_time=meta.model_dump(mode="json")["decision_time"],
                    prediction_available_at=meta.model_dump(mode="json")["decision_time"],
                    fold_id=fold.fold_id,
                    model_run_id=run_id,
                    model_family=family,
                    task=definition.task,
                    horizon=definition.horizon,
                    prediction=float(predicted[index]),
                    probability=float(probability[index]) if probability is not None else None,
                    actual_target=float(holdout.y_validation[index])
                    if np.isfinite(holdout.y_validation[index])
                    else None,
                    actual_forward_return=str(
                        row.targets[f"target_forward_return_{definition.horizon}"]
                    )
                    if row.targets[f"target_forward_return_{definition.horizon}"] is not None
                    else None,
                    scoring_status="SCORABLE"
                    if meta.training_eligibility == "TRAINING_ELIGIBLE"
                    else "OUTCOME_EXCLUDED",
                    outcome_reason_codes=meta.reason_codes,
                    target_available_at=meta.model_dump(mode="json")["label_available_at"],
                    feature_set_id=data.feature_set_id,
                    label_set_id=data.label_set_id,
                    supervised_dataset_id=data.supervised_dataset_id,
                    canonical_input_id=features.canonical_input_id,
                    feature_canonical_dataset_id=meta.feature_canonical_dataset_id,
                    universe_snapshot_id=meta.universe_snapshot_id,
                    classification=data.classification.value,
                    production_claims_permitted=False,
                )
                oos.append(
                    OOSPrediction.model_validate(dict(prediction_id=digest(payload), **payload))
                )
        # Shuffle training targets only. Untouched test outcomes remain the evaluation reference.
        control = build_model(definition.model_families[0], config)
        shuffled = np.random.default_rng(definition.random_seed).permutation(holdout.y_train)
        with threadpool_limits(limits=1):
            control.fit(holdout.x_train, shuffled)
            cp = np.asarray(control.predict(holdout.x_validation), dtype="float64").ravel()
            prob = (
                np.asarray(control.predict_proba(holdout.x_validation)[:, 1], dtype="float64")
                if definition.task == "classification"
                else None
            )
        cm, cn, cb = metrics_for(holdout, cp, prob, config)
        controls.append(
            dict(
                fold_id=fold.fold_id,
                model_family=definition.model_families[0],
                metrics=cm,
                naive_metrics=cn,
                beats_naive=cb,
                shuffled_training_target_digest=digest(shuffled.tolist()),
            )
        )
    oos.sort(key=lambda r: (r.session_date, r.security_id, r.model_family))
    comparison: dict[str, Any] = {}
    for family in definition.model_families:
        rows = [r for r in oos if r.model_family == family and r.scoring_status == "SCORABLE"]
        fold_reports = [
            r for r in reports if r["model_family"] == family and r["status"] == "EVALUATED"
        ]
        primary = "brier_score" if definition.task == "classification" else "mae"
        comparison[family] = dict(
            status="TEST_ONLY_CANDIDATE"
            if rows and data.classification.value == "TEST_ONLY"
            else "INSUFFICIENT_EVIDENCE",
            evidence_status="INSUFFICIENT_EVIDENCE",
            comparison_status="DOES_NOT_BEAT_NAIVE"
            if fold_reports and not any(r["beats_naive"] for r in fold_reports)
            else "INSUFFICIENT_EVIDENCE",
            primary_comparison_metric=primary,
            ranking=rank_diagnostics(rows, definition),
            uncertainty=uncertainty(
                [
                    r["metrics"][primary]
                    for r in fold_reports
                    if r["metrics"].get(primary) is not None
                ],
                len({r.session_date for r in rows}),
                definition,
            ),
            production_claims_permitted=False,
        )
        if rows:
            actual = np.asarray([r.actual_target for r in rows], dtype="float64")
            predicted = np.asarray([r.prediction for r in rows], dtype="float64")
            train_means = {r["fold_id"]: r["training_target_mean"] for r in fold_reports}
            naive_values = np.asarray([train_means[r.fold_id] for r in rows], dtype="float64")
            cfg = fold_config(definition, definition.folds[0])
            if definition.task == "classification":
                probability = np.asarray([r.probability for r in rows], dtype="float64")
                aggregate = classification_metrics(actual, probability, cfg, predicted)
                naive_aggregate = {
                    "majority_class": classification_metrics(
                        actual, (naive_values > 0.5).astype("float64"), cfg
                    ),
                    "training_positive_rate": classification_metrics(actual, naive_values, cfg),
                }
            else:
                aggregate = regression_metrics(actual, predicted)
                naive_aggregate = {
                    "zero_return": regression_metrics(actual, np.zeros(len(actual))),
                    "training_mean": regression_metrics(actual, naive_values),
                }
            comparison[family].update(
                aggregate_oos_metrics=aggregate,
                naive_metrics=naive_aggregate,
                comparisons=comparisons(aggregate, naive_aggregate),
            )
    manifest = dict(
        schema_version=VERSION,
        evaluation_id=evaluation_id,
        identity=identity,
        data_classification=data.classification.value,
        disclaimer=disclaimer(data.classification),
        oos_prediction_dataset_id=digest([r.model_dump(mode="json") for r in oos]),
        prediction_role="FOLD_TEST",
        fold_models=model_manifests,
        prediction_count=len(oos),
        production_claims_permitted=False,
        limitations=[
            "Expanding outer folds; no hyperparameter tuning or final untouched market test",
            "Fixture candidate does not establish predictive or investment value",
            "Regime diagnostics unavailable unless approved market-context inputs exist",
            "Corporate-action coverage and real historical universe not established",
            "Equivalent predictions/metrics in pinned environment; model bytes may differ",
        ],
    )
    negative = dict(
        method="SEEDED_TRAIN_TARGET_PERMUTATION_FIRST_PREDEFINED_FAMILY_EACH_FOLD",
        folds=controls,
        evidence_status="INSUFFICIENT_EVIDENCE",
        production_claims_permitted=False,
        disclaimer=disclaimer(data.classification),
        conclusion="Neither apparent success nor failure on fixtures validates a market signal",
    )
    return EvaluationResult(
        manifest, reports, comparison, tuple(oos), stability(reports, definition), negative, models
    )
