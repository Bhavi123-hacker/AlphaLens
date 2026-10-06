"""Modest fixed baseline suite; single holdout; no tuning, signals or production use."""

import platform
from dataclasses import dataclass
from importlib.metadata import version
from typing import Any

import numpy as np
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from alphalens_data.errors import DataContractError
from alphalens_data.ingestion.contracts import Classification
from alphalens_data.ingestion.storage import stable_json
from alphalens_data.normalization import checksum
from alphalens_labels.alignment import SupervisedDataset
from alphalens_training.contracts import VERSION, TrainingConfig, feature_families
from alphalens_training.metrics import classification_metrics, comparisons, regression_metrics
from alphalens_training.split import Holdout, split


def environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        **{
            name: version(name)
            for name in ("scikit-learn", "numpy", "scipy", "skops", "threadpoolctl")
        },
    }


def pipeline(config: TrainingConfig) -> Pipeline:
    seed = config.random_seed
    classifier = config.task == "classification"
    if config.model_family == "logistic":
        estimator = LogisticRegression(
            C=1.0,
            penalty="l2",
            solver="lbfgs",
            max_iter=1000,
            tol=1e-8,
            fit_intercept=True,
            class_weight=None,
            random_state=seed,
            n_jobs=1,
        )
    elif config.model_family == "ridge":
        estimator = Ridge(alpha=1.0, fit_intercept=True, solver="svd", tol=1e-8, random_state=seed)
    elif config.model_family == "random_forest":
        factory = RandomForestClassifier if classifier else RandomForestRegressor
        estimator = factory(
            n_estimators=32,
            max_depth=4,
            min_samples_split=2,
            min_samples_leaf=3,
            max_features=1.0,
            bootstrap=True,
            oob_score=False,
            random_state=seed,
            n_jobs=1,
            criterion="gini" if classifier else "squared_error",
        )
    else:
        factory = HistGradientBoostingClassifier if classifier else HistGradientBoostingRegressor
        estimator = factory(
            loss="log_loss" if classifier else "squared_error",
            learning_rate=0.1,
            max_iter=32,
            max_leaf_nodes=7,
            max_depth=3,
            min_samples_leaf=5,
            l2_regularization=1.0,
            max_bins=255,
            categorical_features=None,
            early_stopping=False,
            random_state=seed,
        )
    steps: list[tuple[str, Any]] = [
        (
            "imputer",
            SimpleImputer(strategy="median", add_indicator=False, keep_empty_features=False),
        ),
    ]
    if config.model_family in ("logistic", "ridge"):
        steps.append(("scaler", StandardScaler(with_mean=True, with_std=True)))
    steps.append(("estimator", estimator))
    return Pipeline(steps, memory=None, verbose=False)


def run_identity(
    data: SupervisedDataset, config: TrainingConfig, model: Pipeline
) -> dict[str, Any]:
    return dict(
        code_contract_version=VERSION,
        model_version=config.model_version,
        supervised_dataset_id=data.supervised_dataset_id,
        feature_set_id=data.feature_set_id,
        label_set_id=data.label_set_id,
        feature_columns=data.feature_columns,
        feature_families={name: feature_families(config)[name] for name in data.feature_columns},
        target_columns=data.target_columns,
        metadata_columns=data.metadata_columns,
        data_classification=data.classification,
        configuration=config.model_dump(mode="json"),
        hyperparameters=model.named_steps["estimator"].get_params(deep=False),
        preprocessing_parameters={
            name: step.get_params(deep=False) for name, step in model.steps if name != "estimator"
        },
        environment=environment(),
        split_policy="SINGLE_SESSION_DATE_HOLDOUT_AVAILABILITY_PURGE_V1",
        thread_policy="ONE_THREAD_NO_SHUFFLE_NO_INTERNAL_EARLY_STOPPING",
        target_conversion="P7_EXACT_DECIMAL_TO_FLOAT64_AT_ESTIMATOR_BOUNDARY",
    )


@dataclass(frozen=True)
class TrainingResult:
    model: Pipeline
    holdout: Holdout
    manifest: dict[str, Any]
    report: dict[str, Any]


def train(data: SupervisedDataset, config: TrainingConfig) -> TrainingResult:
    config = TrainingConfig.model_validate(config.model_dump())
    holdout = split(data, config)
    if config.task == "classification" and len(np.unique(holdout.y_train)) != 2:
        raise DataContractError("INSUFFICIENT_TRAINING_CLASSES")
    model = pipeline(config)
    identity = run_identity(data, config, model)
    run_id = checksum(stable_json(identity))
    with threadpool_limits(limits=1):
        model.fit(holdout.x_train, holdout.y_train)
        prediction = np.asarray(model.predict(holdout.x_validation), dtype="float64")
        if config.task == "classification":
            probability = np.asarray(
                model.predict_proba(holdout.x_validation)[:, 1], dtype="float64"
            )
            metrics = classification_metrics(holdout.y_validation, probability, config, prediction)
            rate = float(holdout.y_train.mean())
            majority = float(rate > 0.5)  # deterministic tie -> class 0
            naive = {
                "majority_class": classification_metrics(
                    holdout.y_validation, np.full(len(prediction), majority), config
                ),
                "training_positive_rate": classification_metrics(
                    holdout.y_validation, np.full(len(prediction), rate), config
                ),
            }
            primary, comparator = "brier_score", "training_positive_rate"
        else:
            metrics = regression_metrics(holdout.y_validation, prediction)
            naive = {
                "zero_return": regression_metrics(holdout.y_validation, np.zeros(len(prediction))),
                "training_mean": regression_metrics(
                    holdout.y_validation, np.full(len(prediction), float(holdout.y_train.mean()))
                ),
            }
            primary, comparator = "mae", "training_mean"
    beats = metrics[primary] < naive[comparator][primary]
    disclaimer = (
        "TEST_ONLY — NOT A PERFORMANCE CLAIM"
        if data.classification == Classification.TEST_ONLY
        else "RESEARCH_FIXTURE — NOT PRODUCTION-VALIDATED"
    )
    importance: dict[str, Any] = {"status": "UNAVAILABLE_FOR_HIST_GRADIENT_BOOSTING"}
    fitted = model.named_steps["estimator"]
    if hasattr(fitted, "coef_"):
        importance = dict(
            kind="SCALED_LINEAR_COEFFICIENTS", values=np.asarray(fitted.coef_).tolist()
        )
    elif hasattr(fitted, "feature_importances_"):
        importance = dict(
            kind="IMPURITY_IMPORTANCE_NOT_CAUSAL", values=fitted.feature_importances_.tolist()
        )
    importance["feature_order"] = holdout.feature_columns
    summary = dict(
        training_rows=len(holdout.y_train),
        validation_rows=len(holdout.y_validation),
        training_period=[
            holdout.train_metadata[0].session_date.isoformat(),
            holdout.train_metadata[-1].session_date.isoformat(),
        ],
        validation_period=[
            holdout.validation_metadata[0].session_date.isoformat(),
            holdout.validation_metadata[-1].session_date.isoformat(),
        ],
        excluded_rows=holdout.excluded_rows,
        exclusion_counts=holdout.exclusion_counts,
        feature_count=len(holdout.feature_columns),
        removed_constant_features=holdout.removed_features,
        training_class_distribution={str(i): int((holdout.y_train == i).sum()) for i in (0, 1)}
        if config.task == "classification"
        else None,
    )
    limitations = [
        disclaimer,
        "Single development holdout; no P9 walk-forward or final untouched test",
        "No investment performance, production acceptance or causal explanation",
        "Fundamentals unavailable; actual P7-selected P6 feature families only",
        "Corporate-action coverage not established; no costs or total investment returns",
        "Equivalent behavior in pinned environment; serialized bytes not guaranteed identical",
    ]
    report = dict(
        schema_version=VERSION,
        model_run_id=run_id,
        task=config.task,
        horizon=config.horizon,
        model_family=config.model_family,
        data_classification=data.classification,
        classification=data.classification,
        disclaimer=disclaimer,
        **summary,
        training_cutoff=config.training_cutoff.isoformat(),
        validation_knowledge_cutoff=data.training_as_of.isoformat(),
        metrics=metrics,
        naive_metrics=naive,
        comparisons=comparisons(metrics, naive),
        primary_comparison=dict(
            metric=primary,
            naive=comparator,
            result="BASELINE_BEATS_NAIVE" if beats else "BASELINE_DOES_NOT_BEAT_NAIVE",
        ),
        evidence_status="INSUFFICIENT_EVIDENCE",
        production_claims_permitted=False,
        top_k={"status": "UNAVAILABLE_P8_DISABLED"},
        diagnostics=importance,
        limitations=limitations,
    )
    manifest = dict(
        schema_version=VERSION,
        model_run_id=run_id,
        identity=identity,
        status="TEST_ONLY"
        if data.classification == Classification.TEST_ONLY
        else "VALIDATED_BASELINE",
        classification=data.classification,
        feature_order=holdout.feature_columns,
        training_summary=summary,
        trusted_artifact_boundary="LOCAL_CREATED_ARTIFACTS_ONLY",
        production_claims_permitted=False,
    )
    return TrainingResult(model=model, holdout=holdout, manifest=manifest, report=report)
