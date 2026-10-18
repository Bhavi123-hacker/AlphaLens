"""Bounded saved-stock comparison metrics, never a new fit or acceptance decision."""

import math
from typing import Any


def comparison(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"state": "NO_COMPATIBLE_HISTORICAL_PAIRS", "sample_count": 0}
    actual = [row["actual_price_component_return"] for row in rows]
    predicted = [row["ridge_return_estimate"] for row in rows]
    if any(type(x) not in {int, float} or not math.isfinite(x) for x in actual + predicted):
        raise ValueError("FINITE_COMPATIBLE_RETURN_PAIRS_REQUIRED")
    errors = [a - p for a, p in zip(actual, predicted, strict=True)]
    n = len(rows)
    classifier = {}
    for name in rows[0]["scores"]:
        labels = [int(value > 0) for value in actual]
        scores = [row["scores"][name] for row in rows]
        if any(not math.isfinite(x) or not 0 <= x <= 1 for x in scores):
            raise ValueError("FINITE_CLASSIFIER_SCORE_REQUIRED")
        recalls = [
            sum(
                int(score >= 0.5) == label
                for score, label in zip(scores, labels, strict=True)
                if label == target
            )
            / labels.count(target)
            for target in (0, 1)
            if target in labels
        ]
        classifier[name] = {
            "balanced_accuracy": math.fsum(recalls) / 2 if len(recalls) == 2 else None,
            "positive_count": sum(labels),
            "negative_count": n - sum(labels),
            "calibration_status": "NOT_ESTABLISHED",
        }
    return {
        "state": "KNOWN_PERIOD_DEVELOPMENT_NOT_PROSPECTIVE",
        "sample_count": n,
        "start": rows[0]["decision_session"],
        "end": rows[-1]["decision_session"],
        "scope": "RETURNED_STOCK_HISTORY_WINDOW_NOT_WHOLE_MODEL_EVALUATION",
        "regression_target": "NEXT_OBSERVED_OPEN_TO_FIFTH_OBSERVED_CLOSE_PRICE_COMPONENT",
        "ridge_return_mae": math.fsum(abs(x) for x in errors) / n,
        "ridge_return_rmse": math.sqrt(math.fsum(x * x for x in errors) / n),
        "zero_return_baseline_mae": math.fsum(abs(x) for x in actual) / n,
        "zero_return_baseline_rmse": math.sqrt(math.fsum(x * x for x in actual) / n),
        "classifiers": classifier,
        "independent_acceptance": False,
        "overlapping_targets_not_independent_samples": True,
    }
