"""Prediction quality only: fixture evidence never establishes investment performance."""

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)

from alphalens_training.contracts import TrainingConfig
from alphalens_training.split import Matrix


def classification_metrics(
    actual: Matrix, probability: Matrix, config: TrainingConfig, predicted: Matrix | None = None
) -> dict[str, Any]:
    predicted = (probability >= 0.5).astype("float64") if predicted is None else predicted
    both = len(np.unique(actual)) == 2
    counts = confusion_matrix(actual, predicted, labels=[0, 1])
    recalls = [float(counts[i, i] / counts[i].sum()) for i in (0, 1) if counts[i].sum()]
    calibration: dict[str, Any] = {"status": "UNAVAILABLE_TOO_FEW_ROWS", "bins": []}
    if len(actual) >= config.calibration_minimum_rows:
        bins = []
        for index in range(config.calibration_bins):
            lo, hi = index / config.calibration_bins, (index + 1) / config.calibration_bins
            mask = (probability >= lo) & (
                probability <= hi if index == config.calibration_bins - 1 else probability < hi
            )
            bins.append(
                dict(
                    lower=lo,
                    upper=hi,
                    count=int(mask.sum()),
                    mean_probability=float(probability[mask].mean()) if mask.any() else None,
                    observed_positive_rate=float(actual[mask].mean()) if mask.any() else None,
                )
            )
        calibration = {"status": "DESCRIPTIVE_ONLY_NO_CALIBRATOR_FIT", "bins": bins}
    return dict(
        sample_count=len(actual),
        class_distribution={"0": int((actual == 0).sum()), "1": int((actual == 1).sum())},
        positive_rate=float(actual.mean()),
        accuracy=float(accuracy_score(actual, predicted)),
        balanced_accuracy=float(np.mean(recalls)),
        precision=float(precision_score(actual, predicted, zero_division=0)),
        recall=float(recall_score(actual, predicted, zero_division=0)),
        f1=float(f1_score(actual, predicted, zero_division=0)),
        roc_auc=float(roc_auc_score(actual, probability)) if both else None,
        pr_auc_average_precision=float(average_precision_score(actual, probability))
        if both
        else None,
        auc_status="AVAILABLE" if both else "UNAVAILABLE_SINGLE_CLASS",
        log_loss=float(
            log_loss(actual, np.column_stack((1 - probability, probability)), labels=[0, 1])
        ),
        brier_score=float(brier_score_loss(actual, probability)),
        confusion_counts={
            "tn": int(counts[0, 0]),
            "fp": int(counts[0, 1]),
            "fn": int(counts[1, 0]),
            "tp": int(counts[1, 1]),
        },
        calibration=calibration,
    )


def regression_metrics(actual: Matrix, predicted: Matrix) -> dict[str, Any]:
    r2_available = len(actual) >= 2 and bool(np.ptp(actual))
    return dict(
        sample_count=len(actual),
        mae=float(mean_absolute_error(actual, predicted)),
        rmse=float(np.sqrt(mean_squared_error(actual, predicted))),
        r2=float(r2_score(actual, predicted)) if r2_available else None,
        r2_status="AVAILABLE" if r2_available else "UNAVAILABLE_CONSTANT_OR_SHORT_TARGET",
    )


def comparisons(metrics: dict[str, Any], naive: dict[str, dict[str, Any]]) -> dict[str, Any]:
    lower_is_better = {"mae", "rmse", "brier_score", "log_loss"}
    names = lower_is_better | {
        "r2",
        "accuracy",
        "balanced_accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "pr_auc_average_precision",
    }
    return {
        baseline: {
            name: dict(
                model_metric=metrics[name],
                naive_metric=values[name],
                delta=metrics[name] - values[name]
                if metrics[name] is not None and values[name] is not None
                else None,
                better_direction="LOWER" if name in lower_is_better else "HIGHER",
            )
            for name in sorted(names & metrics.keys())
        }
        for baseline, values in naive.items()
    }
