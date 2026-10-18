"""TEST_ONLY compatible return pairs; no real market performance claim."""

import math

import pytest
from workers.nse_market.stock_metrics import comparison


def test_return_metrics_compare_same_targets_and_preserve_uncalibrated_classification() -> None:
    rows = [
        {
            "decision_session": "2025-01-01",
            "actual_price_component_return": 0.10,
            "ridge_return_estimate": 0.08,
            "scores": {"TEST_ONLY": 0.6},
        },
        {
            "decision_session": "2025-01-02",
            "actual_price_component_return": -0.05,
            "ridge_return_estimate": -0.01,
            "scores": {"TEST_ONLY": 0.6},
        },
    ]
    result = comparison(rows)
    assert result["sample_count"] == 2
    assert result["ridge_return_mae"] == pytest.approx(0.03)
    assert result["ridge_return_rmse"] == pytest.approx(math.sqrt(0.001))
    assert result["zero_return_baseline_mae"] == pytest.approx(0.075)
    assert result["classifiers"]["TEST_ONLY"]["balanced_accuracy"] == 0.5
    assert result["independent_acceptance"] is False
    assert result["overlapping_targets_not_independent_samples"] is True
    rows[0]["ridge_return_estimate"] = float("nan")
    with pytest.raises(ValueError):
        comparison(rows)


def test_missing_history_and_single_class_never_invent_a_balanced_accuracy() -> None:
    assert comparison([])["sample_count"] == 0
    result = comparison(
        [
            {
                "decision_session": "2025-01-01",
                "actual_price_component_return": 0.1,
                "ridge_return_estimate": 0,
                "scores": {"TEST_ONLY": 0.9},
            }
        ]
    )
    assert result["classifiers"]["TEST_ONLY"]["balanced_accuracy"] is None
